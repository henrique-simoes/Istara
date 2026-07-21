"""Real legacy-engine executor for the AgenticDispatcher (master plan §5.1).

Every verb drives the SAME legacy plane the 87 inventory call sites use today
(``app.core.ollama.ollama`` — the ComputeRegistry-backed client), with the same
parameter names and message shapes, so dispatcher-routed legacy traffic is
byte-compatible with the unmigrated baseline. Imports are deferred so importing
the dispatcher never initializes the legacy plane.

The executor never falls back to Pi, and the dispatcher never falls back to
this executor: a selected engine executes or raises (fail-closed both ways).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.core.llm_schema_adapter import openai_json_schema_response_format, parse_json_object

from .types import AgenticDispatchError, TurnParams

logger = logging.getLogger(__name__)

# Matches chat.py's MAX_TOOL_ITERATIONS for the legacy ReAct loop.
LEGACY_MAX_TOOL_ITERATIONS = 8


def _ollama() -> Any:
    from app.core.ollama import ollama  # ComputeRegistry-backed legacy plane

    return ollama


def _params(kwargs: dict[str, Any]) -> TurnParams:
    params = kwargs.get("params")
    return params if isinstance(params, TurnParams) else TurnParams()


def _normalize_chat(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize one legacy ``chat`` response without reinterpreting content.

    ``usage`` is populated ONLY when the provider actually reported token counts
    (an ``usage`` block or ollama's ``prompt_eval_count``/``eval_count``). When
    the provider reports nothing, ``usage`` is left absent (an empty dict) rather
    than fabricated as an exact zero: the dispatcher's ledger treats a non-empty
    usage dict as provider-reported and never runs its ``count_tokens``
    estimator, so a fabricated zero block would persist a bogus exact-zero row
    instead of an estimated one.
    """
    message = data.get("message") or {}
    provider_usage = data.get("usage") or {}
    reported = bool(provider_usage) or ("prompt_eval_count" in data) or ("eval_count" in data)
    if reported:
        input_tokens = provider_usage.get("prompt_tokens", data.get("prompt_eval_count", 0)) or 0
        output_tokens = provider_usage.get("completion_tokens", data.get("eval_count", 0)) or 0
        usage: dict[str, Any] = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": provider_usage.get("total_tokens", input_tokens + output_tokens),
            # Provider-reported usage is exact, never silently estimated.
            "estimate": False,
        }
    else:
        # Absent provider usage: leave it out so the ledger estimates from text.
        usage = {}
    return {
        "text": message.get("content", "") or "",
        "usage": usage,
        "stop_reason": data.get("done_reason")
        or ("tool_calls" if message.get("tool_calls") else "stop"),
        "tool_calls": list(message.get("tool_calls") or []),
        "status": "success",
    }


def _estimation_trace(
    *, system: str | None, messages: list[dict[str, Any]], response: dict[str, Any]
) -> dict[str, Any]:
    """Return ephemeral, content-bearing inputs for ledger-owned estimation.

    The trace is carried only inside the in-process outcome and is never stored;
    ``usage_ledger`` converts it to counts before persistence.  Serializing the
    complete message objects keeps tool-call arguments and tool results in the
    estimate instead of reducing a provider turn to visible text alone.
    """
    request = json.dumps(
        {"system": system or "", "messages": messages},
        sort_keys=True,
        default=str,
    )
    return {
        "request_texts": [request],
        "response_texts": [json.dumps(response, sort_keys=True, default=str)],
        "turns": 1,
    }


def _accumulate_usage(usages: list[dict[str, Any]], *, turns: int | None = None) -> dict[str, Any]:
    """Sum provider-reported usage across the turns/samples of one dispatch.

    Exactness is all-or-nothing across the whole dispatch: the summed total is
    exact (``estimate=False``) ONLY when EVERY turn/sample reported provider
    usage. When NONE reported — or the run is *mixed* (some turns reported and at
    least one did not) — this returns an empty dict so the dispatcher ledger
    produces one governed ``count_tokens`` estimate over the complete
    request/response text and flags the row ``estimate=True``, instead of
    persisting the reported subset as an exact total while silently dropping the
    unreported turns. That preserves the ledger's contract that exact and
    estimated numbers are never mixed, and extends ``_normalize_chat``'s per-turn
    all-or-nothing rule to the aggregate: a mixed run is accounted exactly like a
    fully-absent one (governed text estimate), never as a partial exact total.

    ``turns`` records the real multi-turn count on the exact path (defaults to
    the number of reported turns) so a fully-reported legacy tool loop is never
    accounted as a single turn.
    """
    reported = [usage for usage in usages if usage]
    # Mixed (some reported, some absent) or fully-absent → defer to the ledger's
    # governed estimator rather than claim exactness for an incomplete aggregate.
    if not reported or len(reported) < len(usages):
        return {}
    input_tokens = sum(int(usage.get("input_tokens", 0) or 0) for usage in reported)
    output_tokens = sum(int(usage.get("output_tokens", 0) or 0) for usage in reported)
    total_tokens = sum(int(usage.get("total_tokens", 0) or 0) for usage in reported)
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens or (input_tokens + output_tokens),
        "turns": turns if turns is not None else len(reported),
        "estimate": False,
    }


def _tool_call_parts(call: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Split an OpenAI-shaped legacy tool call into (name, arguments)."""
    function = call.get("function") or {}
    name = function.get("name") or call.get("name") or ""
    raw_args = function.get("arguments", call.get("arguments", {}))
    if isinstance(raw_args, str):
        try:
            raw_args = json.loads(raw_args or "{}")
        except json.JSONDecodeError:
            raw_args = {}
    return name, raw_args if isinstance(raw_args, dict) else {}


async def _completion(kwargs: dict[str, Any]) -> dict[str, Any]:
    params = _params(kwargs)
    messages = list(kwargs.get("messages") or [])
    data = await _ollama().chat(
        messages,
        model=params.model,
        system=kwargs.get("system"),
        temperature=params.temperature if params.temperature is not None else 0.7,
        max_tokens=params.max_tokens,
        min_context=params.min_context,
        thinking_mode=params.thinking_mode,
        project_id=kwargs.get("project_id"),
    )
    outcome = _normalize_chat(data)
    outcome["usage_estimation"] = _estimation_trace(
        system=kwargs.get("system"), messages=messages, response=data.get("message") or {}
    )
    return outcome


async def _structured(kwargs: dict[str, Any]) -> dict[str, Any]:
    params = _params(kwargs)
    schema = kwargs.get("schema") or {}
    messages = list(kwargs.get("messages") or [])
    data = await _ollama().chat(
        messages,
        model=params.model,
        system=kwargs.get("system"),
        temperature=params.temperature if params.temperature is not None else 0.7,
        max_tokens=params.max_tokens,
        min_context=params.min_context,
        thinking_mode=params.thinking_mode,
        project_id=kwargs.get("project_id"),
        response_format=openai_json_schema_response_format(
            name=str(kwargs.get("purpose") or "istara_output"), schema=schema
        ),
    )
    outcome = _normalize_chat(data)
    outcome["usage_estimation"] = _estimation_trace(
        system=kwargs.get("system"), messages=messages, response=data.get("message") or {}
    )
    value = parse_json_object(outcome["text"])
    if value is None:
        outcome["status"] = "error"
        outcome["error"] = "legacy_structured_unparsed"
        return outcome
    outcome["value"] = value
    return outcome


async def _react_loop(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Legacy ReAct loop mirroring chat.py: chat -> tool_calls -> execute -> chat."""
    params = _params(kwargs)
    project_id = kwargs.get("project_id") or ""
    agent_id = kwargs.get("agent_id") or "istara-main"
    tool_executor = kwargs.get("tool_executor")
    tools = kwargs.get("tools")
    budget = (
        params.max_turns
        if params.max_turns and params.max_turns > 0
        else LEGACY_MAX_TOOL_ITERATIONS
    )
    stream_cb = kwargs.get("stream_cb")

    history = list(kwargs.get("messages") or [])
    user_text = kwargs.get("user_text")
    if user_text:
        history = [*history, {"role": "user", "content": user_text}]

    text_parts: list[str] = []
    tool_calls_seen: list[dict[str, Any]] = []
    # Accumulate every turn's usage so a fully-reported multi-turn tool loop
    # reports cumulative input/output/total tokens and its real turn count, not
    # just the final turn's usage. Exactness is all-or-nothing: if the whole run
    # reported none — or only some turns reported and at least one did not —
    # ``_accumulate_usage`` leaves the accounting absent so the ledger estimates
    # the complete dispatch rather than persist a partial subset as exact.
    turn_usages: list[dict[str, Any]] = []
    estimation_requests: list[str] = []
    estimation_responses: list[str] = []
    for iteration in range(budget + 1):
        estimation_requests.append(
            _estimation_trace(system=kwargs.get("system"), messages=history, response={})[
                "request_texts"
            ][0]
        )
        data = await _ollama().chat(
            history,
            model=params.model,
            system=kwargs.get("system"),
            temperature=params.temperature if params.temperature is not None else 0.7,
            max_tokens=params.max_tokens,
            tools=tools,
            min_context=params.min_context,
            thinking_mode=params.thinking_mode,
            project_id=project_id,
        )
        outcome = _normalize_chat(data)
        turn_usages.append(outcome["usage"])
        message = data.get("message") or {}
        estimation_responses.append(json.dumps(message, sort_keys=True, default=str))
        raw_calls = list(message.get("tool_calls") or [])
        if not raw_calls or iteration >= budget or tool_executor is None:
            text_parts.append(outcome["text"])
            if stream_cb is not None and outcome["text"]:
                maybe = stream_cb({"type": "content", "text": outcome["text"]})
                if hasattr(maybe, "__await__"):
                    await maybe
            stop = (
                "turn_budget_exceeded"
                if raw_calls and iteration >= budget
                else outcome["stop_reason"]
            )
            return {
                "text": "".join(text_parts).strip(),
                "usage": _accumulate_usage(turn_usages, turns=len(turn_usages)),
                "usage_estimation": {
                    "request_texts": estimation_requests,
                    "response_texts": estimation_responses,
                    "turns": len(turn_usages),
                },
                "stop_reason": stop,
                "tool_calls": tool_calls_seen,
                "status": "success",
            }
        if outcome["text"].strip():
            text_parts.append(outcome["text"])
        history.append(message)
        for call in raw_calls:
            name, arguments = _tool_call_parts(call)
            tool_calls_seen.append({"tool": name, "params": arguments})
            if stream_cb is not None:
                maybe = stream_cb({"type": "tool_call", "tool": name, "params": arguments})
                if hasattr(maybe, "__await__"):
                    await maybe
            result = await tool_executor(name, arguments, project_id, agent_id)
            history.append({"role": "tool", "content": json.dumps(result, default=str)})
    raise AssertionError("unreachable")


async def _embed(kwargs: dict[str, Any]) -> dict[str, Any]:
    params = _params(kwargs)
    vectors = await _ollama().embed_batch(
        list(kwargs.get("texts") or []), model=params.model, project_id=kwargs.get("project_id")
    )
    return {"embeddings": vectors, "usage": {"estimate": False}, "status": "success"}


async def _ensemble(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Legacy ensemble: n sequential samples on the legacy plane (validation.py behavior)."""
    n = int(kwargs.get("n") or 1)
    temperatures = kwargs.get("temperatures") or []
    samples: list[dict[str, Any]] = []
    for index in range(n):
        call_kwargs = dict(kwargs)
        if index < len(temperatures) and temperatures[index] is not None:
            call_kwargs["params"] = _with_temperature(_params(kwargs), float(temperatures[index]))
        samples.append(await _completion(call_kwargs))
    return {
        "samples": samples,
        "endpoint_ids": [sample.get("endpoint_id") or "legacy" for sample in samples],
        "usage": _sum_usage(samples),
        "usage_estimation": {
            "request_texts": [
                text
                for sample in samples
                for text in (sample.get("usage_estimation") or {}).get("request_texts", [])
            ],
            "response_texts": [
                text
                for sample in samples
                for text in (sample.get("usage_estimation") or {}).get("response_texts", [])
            ],
            "turns": len(samples),
        },
        "status": "success" if all(s.get("status") == "success" for s in samples) else "error",
    }


def _with_temperature(params: TurnParams, temperature: float) -> TurnParams:
    from dataclasses import replace

    return replace(params, temperature=temperature)


def _sum_usage(samples: list[dict[str, Any]]) -> dict[str, Any]:
    # Cumulative across every sample, one "turn" per sample; exact only when
    # EVERY sample reported provider usage. Absent when no sample reported — or
    # when the ensemble is mixed (some reported, some did not) — so the ledger
    # estimates the complete dispatch rather than persist a partial subset as
    # exact or a fabricated exact-zero row (mirrors the ReAct loop).
    return _accumulate_usage([s.get("usage") or {} for s in samples], turns=len(samples))


_VERBS = {
    "completion": _completion,
    "structured": _structured,
    "react": _react_loop,
    "chat_turn": _react_loop,
    "embed": _embed,
    "ensemble": _ensemble,
}


async def legacy_executor(verb: str, **kwargs: Any) -> dict[str, Any]:
    """Dispatcher-bound legacy executor: the real legacy plane, fail-closed."""
    handler = _VERBS.get(verb)
    if handler is None:
        raise AgenticDispatchError(f"legacy_verb_unknown:{verb}")
    return await handler(kwargs)
