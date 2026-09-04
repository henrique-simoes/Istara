"""Istara legacy-loop semantics under Pi Model Management authority.

The legacy engine choice preserves Istara's bounded Python ReAct loop and its
tool-execution behavior. It does *not* select a second provider plane: model,
endpoint, credentials, retries, limits, and usage remain owned by the injected
``PiExecutionService``. The Pi engine choice instead runs pi-agent-core's own
loop. Thus both user-visible modes are first-class while provider authority is
singular and fail-closed.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from .types import AgenticDispatchError, TurnParams

logger = logging.getLogger(__name__)

# Matches chat.py's MAX_TOOL_ITERATIONS for the legacy ReAct loop.
LEGACY_MAX_TOOL_ITERATIONS = 8


def _provider_service(kwargs: dict[str, Any]) -> Any:
    service = kwargs.get("provider_service")
    if service is not None:
        return service
    # Direct executor callers still use the same singleton Pi authority as
    # production seams. Dispatcher calls always inject their own service so a
    # custom/test manager cannot be split from the legacy loop.
    from app.core.pi_runtime.seams import get_pi_execution_service

    return get_pi_execution_service()


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
    outcome = {
        "text": message.get("content", "") or "",
        "usage": usage,
        "stop_reason": data.get("done_reason")
        or data.get("finish_reason")
        or ("tool_calls" if message.get("tool_calls") else "stop"),
        "tool_calls": list(message.get("tool_calls") or []),
        "status": "success",
    }
    if data.get("truncated"):
        # F-12: partial answer after budget exhaustion — explicit, never silent.
        outcome["truncated"] = True
    route = data.get("_istara_route")
    if isinstance(route, dict):
        outcome["route_evidence"] = route
        if route.get("node_id"):
            # The serving registry node IS the legacy endpoint identity; without it
            # downstream ensemble/dispatcher layers fall back to a "legacy" placeholder
            # that hides the real route (F-11 route truth).
            outcome["endpoint_id"] = str(route["node_id"])
    return outcome


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


def _server_model_names(server: Any) -> set[str]:
    """Return the model identities advertised by one legacy compute server."""
    names: set[str] = set()
    for attr in ("loaded_models", "models", "model_names"):
        raw = getattr(server, attr, None)
        if isinstance(raw, (list, tuple, set)):
            names.update(str(item).strip() for item in raw if str(item).strip())
    capabilities = getattr(server, "model_capabilities", None)
    if isinstance(capabilities, dict):
        names.update(str(name).strip() for name in capabilities if str(name).strip())
    default_model = getattr(server, "default_model", None) or getattr(server, "model", None)
    if default_model:
        names.add(str(default_model).strip())
    return names


def _diverse_legacy_routes(servers: list[Any]) -> list[tuple[Any, str]]:
    """Choose one stable route per distinct advertised model identity."""
    selected: list[tuple[Any, str]] = []
    seen_models: set[str] = set()
    for server in servers:
        models = sorted(_server_model_names(server), key=str.casefold)
        model = next(
            (candidate for candidate in models if candidate.casefold() not in seen_models),
            "",
        )
        if not model:
            continue
        seen_models.add(model.casefold())
        selected.append((server, model))
    return selected


def _legacy_endpoint_id(server: Any, data: dict[str, Any]) -> str:
    route = data.get("_istara_route") if isinstance(data, dict) else None
    if isinstance(route, dict):
        identity = route.get("node_id") or route.get("server_id") or route.get("route_id")
        if identity:
            return str(identity)
    return str(getattr(server, "node_id", None) or getattr(server, "name", None) or "legacy")


async def _completion(kwargs: dict[str, Any]) -> dict[str, Any]:
    return await _provider_service(kwargs).run_completion(
        purpose=str(kwargs.get("purpose") or "legacy_completion"),
        project_id=str(kwargs.get("project_id") or ""),
        agent_id=str(kwargs.get("agent_id") or "istara-main"),
        system=str(kwargs.get("system") or ""),
        messages=list(kwargs.get("messages") or []),
        params=_params(kwargs),
    )


async def _structured(kwargs: dict[str, Any]) -> dict[str, Any]:
    return await _provider_service(kwargs).run_structured(
        purpose=str(kwargs.get("purpose") or "legacy_structured"),
        project_id=str(kwargs.get("project_id") or ""),
        agent_id=str(kwargs.get("agent_id") or "istara-main"),
        system=str(kwargs.get("system") or ""),
        messages=list(kwargs.get("messages") or []),
        schema=kwargs.get("schema") or {},
        params=_params(kwargs),
        repair=bool(kwargs.get("repair", True)),
    )


_DEFAULT_TEXT_FALLBACK_FOLLOWUP = (
    "Now respond to the user based on this result. Do not call another tool unless necessary."
)

# Text-fallback extraction (mirrors chat.py's baseline regex pair). Routes may
# inject their own extractor via TurnParams.tool_call_extractor.
_TOOL_CALL_BLOCK_RE = re.compile(
    r'```(?:json)?\s*(\{\s*"tool"\s*:.+?\})\s*```',
    re.DOTALL,
)
_TOOL_CALL_INLINE_RE = re.compile(
    r'(\{\s*"tool"\s*:\s*"[a-z_]+".*?\})',
    re.DOTALL,
)


def _default_extract_tool_call(text: str) -> tuple[dict[str, Any] | None, str, str]:
    """Extract a ``{"tool": ..., "params": ...}`` call from raw LLM text."""
    match = _TOOL_CALL_BLOCK_RE.search(text)
    if not match:
        match = _TOOL_CALL_INLINE_RE.search(text)
    if not match:
        return None, text, ""
    try:
        call = json.loads(match.group(1))
        if "tool" not in call:
            return None, text, ""
        return call, text[: match.start()].strip(), text[match.end() :].strip()
    except (json.JSONDecodeError, IndexError):
        return None, text, ""


async def _emit(stream_cb: Any, event: dict[str, Any]) -> None:
    """Forward one stream event, tolerating sync and async callbacks."""
    if stream_cb is None:
        return
    maybe = stream_cb(event)
    if hasattr(maybe, "__await__"):
        await maybe


async def _react_loop(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Istara's Python ReAct loop over Pi-managed raw provider turns.

    Tool execution deliberately remains here, outside pi-agent-core. Pi Model
    Management owns provider/model selection, secrets, limits, retries and
    accounting for every turn. ``text_fallback`` still suppresses raw streaming
    because its machine-readable tool block must be parsed before display.
    """
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
    stream_tokens = bool(getattr(params, "stream_tokens", False)) and stream_cb is not None
    text_fallback = bool(getattr(params, "text_fallback", False))
    extractor = getattr(params, "tool_call_extractor", None) or _default_extract_tool_call
    followup = getattr(params, "text_fallback_followup", None) or _DEFAULT_TEXT_FALLBACK_FOLLOWUP
    allowed_names = set(kwargs.get("tool_names") or []) or None

    history = list(kwargs.get("messages") or [])
    user_text = kwargs.get("user_text")
    if user_text:
        history = [*history, {"role": "user", "content": user_text}]

    text_parts: list[str] = []
    tool_calls_seen: list[dict[str, Any]] = []
    provider_service = _provider_service(kwargs)
    served_endpoint_id: str | None = None
    configured_model: str | None = None
    served_model: str | None = None
    # Accumulate every turn's usage so a fully-reported multi-turn tool loop
    # reports cumulative input/output/total tokens and its real turn count, not
    # just the final turn's usage. Exactness is all-or-nothing: if the whole run
    # reported none — or only some turns reported and at least one did not —
    # ``_accumulate_usage`` leaves the accounting absent so the ledger estimates
    # the complete dispatch rather than persist a partial subset as exact.
    turn_usages: list[dict[str, Any]] = []
    estimation_requests: list[str] = []
    estimation_responses: list[str] = []

    def _outcome(stop: str, *, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        outcome: dict[str, Any] = {
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
        if extra:
            outcome.update(extra)
        if served_endpoint_id:
            outcome["endpoint_id"] = served_endpoint_id
            # ``model`` remains the configured/request identity for ordinary
            # callers.  Only the explicit provider receipt may populate
            # ``served_model``; treating the configured label as a receipt
            # would let a proxy masquerade as an independent Research Spine
            # rater.
            outcome["model"] = configured_model
            # Keep the provider receipt distinct from the configured model.
            # ``AgenticDispatcher`` and Research Spine evidence consumers use
            # this field to decide whether the serving identity was actually
            # proven; putting it only in ``route_evidence`` silently downgrades
            # a valid legacy-loop receipt to an unverified route.
            outcome["served_model"] = served_model
            outcome["route_evidence"] = {
                "plane": "pi-managed",
                "endpoint_id": served_endpoint_id,
                "model": served_model,
                "requested_model": configured_model,
                "served_model": served_model,
                "bridge": "provider-only",
                "loop": "istara",
            }
        return outcome

    for iteration in range(budget + 1):
        estimation_requests.append(
            _estimation_trace(system=kwargs.get("system"), messages=history, response={})[
                "request_texts"
            ][0]
        )
        provider_outcome = await provider_service.run_provider_turn(
            purpose=str(kwargs.get("purpose") or "legacy_react"),
            project_id=project_id,
            agent_id=agent_id,
            system=kwargs.get("system"),
            messages=history,
            tools=None if text_fallback else tools,
            params=params,
            stream_cb=(stream_cb if stream_tokens and not text_fallback else None),
        )
        if provider_outcome.get("status") != "success":
            raise AgenticDispatchError(
                str(provider_outcome.get("error") or "pi_provider_turn_failed")
            )
        served_endpoint_id = str(provider_outcome.get("endpoint_id") or "") or None
        configured_model = str(provider_outcome.get("model") or params.model or "") or None
        served_model = str(provider_outcome.get("served_model") or "") or None
        turn_usages.append(provider_outcome.get("usage") or {})
        message = {
            "role": "assistant",
            "content": provider_outcome.get("text") or "",
            "tool_calls": list(provider_outcome.get("tool_calls") or []),
        }
        estimation_responses.append(json.dumps(message, sort_keys=True, default=str))
        turn_text = str(message.get("content") or "")
        raw_calls = list(message.get("tool_calls") or [])

        if text_fallback:
            tool_call, text_before, _ = extractor(turn_text)
            if tool_call and iteration < budget and tool_executor is not None:
                if text_before:
                    text_parts.append(text_before)
                    await _emit(stream_cb, {"type": "content", "text": text_before + "\n\n"})
                name = str(tool_call.get("tool") or "")
                arguments = tool_call.get("params") or {}
                if not isinstance(arguments, dict):
                    arguments = {}
                tool_calls_seen.append({"tool": name, "params": arguments})
                await _emit(stream_cb, {"type": "tool_call", "tool": name, "params": arguments})
                result = await tool_executor(name, arguments, project_id, agent_id)
                if isinstance(result, dict):
                    result_text = result.get("result", result.get("error", "Unknown result"))
                else:
                    result_text = str(result)
                history.append(
                    {
                        "role": "assistant",
                        "content": (
                            text_before + f"\n\n[Tool: {name}]"
                            if text_before
                            else f"[Tool: {name}]"
                        ),
                    }
                )
                history.append(
                    {
                        "role": "user",
                        "content": f"[Tool result for {name}]:\n{result_text}\n\n{followup}",
                    }
                )
                continue
            if tool_call and getattr(params, "suppress_budget_exhausted_text", False):
                # The caller renders its own fallback answer for a budget-ended
                # tool call; the raw tail (with the machine block) never streams.
                return _outcome("turn_budget_exceeded", extra={"budget_exhausted_tool_call": True})
            final_text = (
                turn_text.strip() if getattr(params, "final_text_strip", False) else turn_text
            )
            if final_text or not getattr(params, "final_text_strip", False):
                text_parts.append(final_text)
                await _emit(stream_cb, {"type": "content", "text": final_text})
            stop = "turn_budget_exceeded" if tool_call else "stop"
            return _outcome(stop)

        # Hallucinated-tool filtering for the W2 streaming chat surfaces
        # (chat.py semantics): names outside the advertised catalog never
        # execute; their user-visible argument text is recovered when enabled.
        extracted_text = ""
        if stream_tokens and allowed_names is not None and raw_calls:
            real_calls: list[dict[str, Any]] = []
            for call in raw_calls:
                name, arguments = _tool_call_parts(call)
                if name in allowed_names:
                    real_calls.append(call)
                elif getattr(params, "hallucination_text_extract", True):
                    logger.info(
                        "Hallucinated tool call '%s' — extracting text from arguments", name
                    )
                    extracted = arguments.get(
                        "text", arguments.get("content", arguments.get("response", ""))
                    )
                    if extracted:
                        extracted_text += str(extracted)
            raw_calls = real_calls

        if not raw_calls or iteration >= budget or tool_executor is None:
            text_parts.append(turn_text + extracted_text)
            if stream_tokens:
                # Tokens already streamed; only mined hallucination text remains.
                if extracted_text:
                    await _emit(stream_cb, {"type": "content", "text": extracted_text})
            elif turn_text and stream_cb is not None:
                await _emit(stream_cb, {"type": "content", "text": turn_text})
            stop = "turn_budget_exceeded" if raw_calls and iteration >= budget else "stop"
            return _outcome(stop)

        if turn_text.strip():
            text_parts.append(turn_text)
        if stream_tokens and turn_text.strip():
            # Pre-tool text boundary: the old SSE chunk was response_text+"\n\n".
            await _emit(stream_cb, {"type": "turn_separator", "text": "\n\n"})
        history.append(message)
        for call in raw_calls:
            name, arguments = _tool_call_parts(call)
            tool_calls_seen.append({"tool": name, "params": arguments})
            await _emit(stream_cb, {"type": "tool_call", "tool": name, "params": arguments})
            result = await tool_executor(name, arguments, project_id, agent_id)
            history.append(
                {
                    "role": "tool",
                    "tool_call_id": call.get("id"),
                    "name": name,
                    "content": json.dumps(result, default=str),
                }
            )
    raise AssertionError("unreachable")


async def _embed(kwargs: dict[str, Any]) -> dict[str, Any]:
    params = _params(kwargs)
    gateway = kwargs.get("embeddings_gateway")
    if gateway is None:
        from app.core.pi_runtime.embeddings_gateway import EmbeddingsGateway

        gateway = EmbeddingsGateway(manager=_provider_service(kwargs).model_manager())
    return await gateway.embed(list(kwargs.get("texts") or []), model=params.model)


async def _ensemble(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Run ensemble samples through Pi's identity-distinct model authority.

    Engine choice cannot change the research raters. A legacy-mode caller keeps
    its surrounding Istara semantics, while selection and execution of every
    independent model are delegated to Pi Model Management exactly as in Pi
    mode. When an older caller asks for an optional spare, the governed minimum
    is used so three admitted models remain sufficient for a three-rater gate.
    """
    # Keep the legacy adapter's validation identical to PiExecutionService.
    # ``n=0`` must not become a one-sample success: an empty/invalid ensemble
    # cannot provide independent judgments for the Research Spine.  Validate
    # before calling the shared provider service so custom services cannot
    # accidentally bypass this fail-closed boundary.
    from app.core.pi_runtime.endpoints import PiEndpointResolutionError

    raw_n = kwargs.get("n", 1)
    if not isinstance(raw_n, int) or isinstance(raw_n, bool) or raw_n < 1:
        raise PiEndpointResolutionError("ensemble_width_must_be_positive")
    raw_minimum_n = kwargs.get("minimum_n")
    if raw_minimum_n is not None and (
        not isinstance(raw_minimum_n, int) or isinstance(raw_minimum_n, bool) or raw_minimum_n < 1
    ):
        raise PiEndpointResolutionError("ensemble_minimum_width_must_be_positive")
    n = raw_n
    if kwargs.get("distinct"):
        n = max(1, min(raw_minimum_n if raw_minimum_n is not None else n, n))
    return await _provider_service(kwargs).run_ensemble(
        purpose=str(kwargs.get("purpose") or "legacy_ensemble"),
        project_id=str(kwargs.get("project_id") or ""),
        agent_id=str(kwargs.get("agent_id") or "istara-main"),
        system=str(kwargs.get("system") or ""),
        messages=list(kwargs.get("messages") or []),
        n=n,
        distinct=bool(kwargs.get("distinct")),
        temperatures=kwargs.get("temperatures"),
        params=_params(kwargs),
    )


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
