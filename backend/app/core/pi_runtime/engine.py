"""PiExecutionService — the single facade that owns Pi runtime semantics.

A route or service hands the facade the *already authorized* context (project,
agent, system prompt with protected blocks, history) plus an authority
``tool_executor`` and a user turn. The service resolves the private endpoint,
drives the real pi-agent-core Agent in the worker, executes every tool call in
Python with the authenticated project/agent scope re-injected (model-supplied
scope fields are ignored), and yields normalized events. It never consults
``ComputeRegistry``.

The facade exposes one seam per governed surface so no route reinvents runtime
semantics (Plan C D-C5):

* ``run_chat_turn``      — streaming chat turn (SSE),
* ``run_delegation``     — A2A orchestrator-dispatched delegated work,
* ``run_channel_turn``   — an in-process ``pi_local`` channel reply,
* ``run_autoresearch_turn`` — one bounded governed Autoresearch turn that yields
  a *candidate proposal only* (no promotion, no background loop).

Steering is bridged into a live turn: while a turn is active, queued steering /
follow-up messages drain into ``turn.steer`` / ``turn.follow_up`` and an abort
maps to ``turn.abort`` (exactly one terminal event).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, replace
from typing import Any, AsyncIterator, Awaitable, Callable

from app.core.telemetry import telemetry_recorder

from .endpoints import (
    DEFAULT_ENDPOINT_ID,
    PiEndpointResolver,
    PiRuntimeTurnError,
    ResolvedPiEndpoint,
)
from .model_manager import PiModelManager
from .supervisor import PiRuntimeSupervisor, get_supervisor
from .tools import build_tool_catalog, catalog_tool_names

logger = logging.getLogger(__name__)

# (tool_name, params, project_id, agent_id) -> {"result": ...} | {"error": ...}
ToolExecutor = Callable[[str, dict[str, Any], str, str], Awaitable[dict[str, Any]]]

# ── Route/seam-scoped tool subsets ────────────────────────────────────────
# Delegation runs another agent's work item: task/document/finding/memory
# reasoning, but no outbound agent messaging and no external network fetch
# (a delegate must not spawn further delegation or reach the internet).
DELEGATION_TOOLS: tuple[str, ...] = (
    "create_task",
    "list_tasks",
    "move_task",
    "update_task",
    "search_documents",
    "get_document_content",
    "search_findings",
    "search_memory",
    "list_project_files",
    "attach_document",
    "context_expand",
    "context_grep",
)
# A channel reply is conversational: read the project and optionally open a task,
# never message other agents or reach the network.
CHANNEL_TOOLS: tuple[str, ...] = (
    "search_documents",
    "get_document_content",
    "search_findings",
    "search_memory",
    "list_tasks",
    "create_task",
    "context_expand",
    "context_grep",
)
# Governed Autoresearch is read-only / proposal-only: it may inspect the project
# to shape a hypothesis but may not mutate any state — the proposal is persisted
# by Python behind the human governance gate, not by the model.
AUTORESEARCH_TOOLS: tuple[str, ...] = (
    "search_documents",
    "get_document_content",
    "search_findings",
    "search_memory",
    "list_tasks",
    "list_project_files",
    "context_expand",
    "context_grep",
)


@dataclass(frozen=True)
class SteeringBinding:
    """Bind a live Pi turn to a project-scoped steering queue.

    Keyed ``(agent_id, project_id, session_key)``: each live turn marks and
    polls its own binding, so concurrent turns of the same agent never clear
    each other's working flag (no spurious aborts). ``session_key`` may be
    None at construction; the engine fills in the resolved session key when
    the turn starts.
    """

    agent_id: str
    project_id: str
    manager: Any  # app.core.steering.SteeringManager (duck-typed to avoid a cycle)
    session_key: str | None = None


def _session_revision(history: list[dict[str, Any]], endpoint: ResolvedPiEndpoint) -> str:
    digest = hashlib.sha256()
    digest.update(json.dumps(history or [], sort_keys=True, default=str).encode("utf-8"))
    digest.update(endpoint.endpoint_id.encode("utf-8"))
    digest.update(endpoint.model.encode("utf-8"))
    return digest.hexdigest()[:16]


def _bind_payload(endpoint: ResolvedPiEndpoint, params: Any = None) -> dict[str, Any]:
    payload = {
        "endpoint_id": endpoint.endpoint_id,
        "provider_kind": endpoint.provider_kind,
        "base_url": endpoint.base_url,
        "model": endpoint.model,
        "api_key": endpoint.api_key,
        "timeout_ms": endpoint.timeout_ms,
        "max_retries": endpoint.max_retries,
    }
    bind_params = _turn_bind_params(params, endpoint)
    if bind_params:
        # Canonical generation/retry knobs (worker-validated keys only:
        # temperature, max_tokens, thinking_level, timeout_ms, max_retries).
        payload["params"] = bind_params
    if endpoint.provider_kind == "faux" and endpoint.faux_responses is not None:
        # Test-only deterministic provider: never set by the production resolver.
        payload["faux_responses"] = list(endpoint.faux_responses)
        payload["faux_forced_tool_calls"] = list(endpoint.faux_forced_tool_calls or ())
    else:
        # Real endpoints carry their trustworthy pricing so the worker prices
        # usage and the per-run cost ceiling fails closed (never $0-priced).
        payload["pricing"] = {
            "input_per_mtok": endpoint.cost_input_per_mtok,
            "output_per_mtok": endpoint.cost_output_per_mtok,
            "cache_read_per_mtok": endpoint.cost_cache_read_per_mtok,
            "cache_write_per_mtok": endpoint.cost_cache_write_per_mtok,
        }
    return payload


def _turn_bind_params(params: Any, endpoint: ResolvedPiEndpoint) -> dict[str, Any]:
    """Map TurnParams onto the worker's provider params (master plan §5.3).

    Only explicitly-set knobs are forwarded; everything else keeps the
    endpoint/worker defaults so a bare turn behaves exactly as before.
    """
    if params is None:
        return {}
    mapped: dict[str, Any] = {}
    temperature = getattr(params, "temperature", None)
    if temperature is not None:
        mapped["temperature"] = float(temperature)
    max_tokens = getattr(params, "max_tokens", None)
    if max_tokens:
        mapped["max_tokens"] = int(max_tokens)
    thinking_mode = getattr(params, "thinking_mode", None)
    if thinking_mode:
        mapped["thinking_level"] = str(thinking_mode)
    timeout_s = getattr(params, "timeout_s", None)
    if timeout_s:
        mapped["timeout_ms"] = int(float(timeout_s) * 1000)
    return mapped


def _normalize_tool_result(result: Any) -> dict[str, Any]:
    """Map an authority ``execute_tool`` result onto the worker's ok/error shape."""
    if isinstance(result, dict):
        if "success" in result:
            if result.get("success"):
                return {"ok": True, "result": result.get("result")}
            return {"ok": False, "error": str(result.get("error") or "tool_failed")}
        if "error" in result and "result" not in result:
            return {"ok": False, "error": str(result.get("error"))}
        if "result" in result:
            return {"ok": True, "result": result.get("result")}
    return {"ok": True, "result": result}


class PiExecutionService:
    def __init__(
        self,
        *,
        resolver: PiEndpointResolver | None = None,
        supervisor: PiRuntimeSupervisor | None = None,
        model_manager: PiModelManager | None = None,
    ) -> None:
        self._resolver = resolver or PiEndpointResolver()
        self._supervisor = supervisor
        self._model_manager = model_manager

    def _sup(self) -> PiRuntimeSupervisor:
        return self._supervisor or get_supervisor()

    def _manager(self) -> PiModelManager:
        # The manager is the engine's endpoint authority (§5.2): static settings
        # endpoints, local serving, and (on refresh) persisted LLMServer rows —
        # never ComputeRegistry or donor capacity.
        if self._model_manager is None:
            self._model_manager = PiModelManager(resolver=self._resolver)
        return self._model_manager

    def model_manager(self) -> PiModelManager:
        """Public accessor for the engine's endpoint authority (W8).

        The embeddings gateway and the UX-parity surfaces share the exact
        manager the engine resolves through, so catalog/projection state is
        one identity plane rather than parallel instances.
        """
        return self._manager()

    # ── shared turn driver ───────────────────────────────────────────────
    async def _drive_turn(
        self,
        *,
        operation: str,
        project_id: str,
        agent_id: str,
        system_prompt: str,
        history: list[dict[str, Any]],
        user_text: str,
        tool_executor: ToolExecutor,
        session_key: str | None,
        endpoint_id: str | None,
        allowed_tools: list[str] | None,
        steering: SteeringBinding | None = None,
        output_schema: dict[str, Any] | None = None,
        tool_choice: Any = None,
        max_turns: int | None = None,
        model: str | None = None,
        min_context: int = 0,
        require_vision: bool = False,
        turn_params: Any = None,
        extra_tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Drive one governed Pi turn, yielding normalized events.

        Resolves the private endpoint through the PiModelManager first, so a
        resolution/capability miss raises ``PiEndpointResolutionError`` before
        any worker/provider work.
        """
        manager = self._manager()
        await manager.ensure_db_projection()
        if endpoint_id is None and model is None and min_context <= 0 and not require_vision:
            endpoint_id = DEFAULT_ENDPOINT_ID
        endpoint = manager.resolve(
            endpoint_id=endpoint_id, model=model,
            require_vision=require_vision, min_context=min_context,
        )
        catalog = build_tool_catalog(allowed_tools, extra_tools=extra_tools)
        catalog_names = catalog_tool_names(allowed_tools, extra_tools=extra_tools)
        key = session_key or f"pi-{operation}-{uuid.uuid4().hex}"
        revision = _session_revision(history, endpoint)
        sup = self._sup()

        async def tool_handler(name: str, args: dict[str, Any]) -> dict[str, Any]:
            # Authority round-trip: authenticated scope is re-injected here; the
            # model cannot set project_id/agent_id. The Python-side allowlist is
            # enforced against the run's catalog: a compromised or buggy worker
            # requesting an out-of-catalog tool gets a structured rejection and
            # an audit row, never an executed tool (B-12).
            if name not in catalog_names:
                logger.warning("pi-runtime: rejected out-of-catalog tool %s for %s", name, operation)
                await self._record_tool_rejection(endpoint, project_id, agent_id, name, operation)
                return {"ok": False, "error": "tool_not_allowed", "tool": name}
            result = await tool_executor(name, args, project_id, agent_id)
            return _normalize_tool_result(result)

        await sup.ensure_started()
        terminal: dict[str, Any] | None = None
        steer_task: asyncio.Task | None = None
        steering_bound = False
        session_opened = False
        try:
            # The full turn — including the session open — lives inside
            # try/finally so a failed open never leaks a session queue (B-7).
            await sup.open_session(
                key,
                system_prompt=system_prompt,
                history=history,
                revision=revision,
                catalog=catalog,
            )
            session_opened = True
            await sup.bind_provider(key, _bind_payload(endpoint, turn_params))
            if steering is not None:
                # Bind this turn's own (agent_id, project_id, session_key) key —
                # the pump polls its own binding, never a global slot (B-5).
                steering = replace(steering, session_key=steering.session_key or key)
                steering_bound = True
                await steering.manager.mark_working(
                    steering.agent_id, project_id=steering.project_id, session_key=steering.session_key
                )
                steer_task = asyncio.create_task(self._pump_steering(sup, key, steering))
            async for frame in sup.run_turn(
                key, user_text, tool_handler,
                output_schema=output_schema, tool_choice=tool_choice, max_turns=max_turns,
            ):
                event = _map_frame(frame, endpoint)
                if event is None:
                    continue
                if event["type"] in ("done", "error", "aborted"):
                    terminal = event
                yield event
        finally:
            if steer_task is not None:
                steer_task.cancel()
                try:
                    await steer_task
                except (asyncio.CancelledError, Exception):  # pragma: no cover - teardown
                    pass
            if steering_bound:
                try:
                    await steering.manager.mark_idle(
                        steering.agent_id, project_id=steering.project_id, session_key=steering.session_key
                    )
                except Exception:  # pragma: no cover - teardown best effort
                    logger.debug("pi-runtime: steering mark_idle failed")
            if session_opened:
                try:
                    await sup.close_session(key)
                except Exception:  # pragma: no cover - teardown best effort
                    logger.debug("pi-runtime: session close failed for %s", key)
            await self._record_turn_telemetry(endpoint, project_id, agent_id, terminal, operation)

    async def _pump_steering(
        self, sup: PiRuntimeSupervisor, session_key: str, steering: SteeringBinding
    ) -> None:
        """While a turn is live, drain the steering queues into the worker.

        Queued steering messages map to ``turn.steer`` (delivered once), follow
        ups to ``turn.follow_up``; an external abort (this turn's own
        ``(agent_id, project_id, session_key)`` binding cleared) maps to
        ``turn.abort`` — the worker then emits exactly one ``run.aborted``.
        Another concurrent turn of the same agent finishing must never read as
        an abort here: only this binding's working flag is polled.
        """
        mgr = steering.manager
        aid, pid = steering.agent_id, steering.project_id
        try:
            while True:
                for msg in await mgr.get_steering(aid, project_id=pid):
                    await sup.steer(session_key, getattr(msg, "message", str(msg)))
                for msg in await mgr.get_follow_up(aid, project_id=pid):
                    await sup.follow_up(session_key, getattr(msg, "message", str(msg)))
                if not mgr.is_binding_working(aid, project_id=pid, session_key=steering.session_key):
                    await sup.abort(session_key)
                    return
                await asyncio.sleep(0.05)
        except asyncio.CancelledError:  # pragma: no cover - teardown
            raise
        except Exception:  # pragma: no cover - defensive
            logger.debug("pi-runtime: steering pump error")

    async def _collect_turn(self, **kwargs: Any) -> dict[str, Any]:
        """Run a governed turn to completion and return a normalized result."""
        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []
        terminal: dict[str, Any] | None = None
        async for event in self._drive_turn(**kwargs):
            etype = event["type"]
            if etype == "content":
                text_parts.append(event.get("text", ""))
            elif etype == "tool_call":
                tool_calls.append({"tool": event.get("tool"), "params": event.get("params", {})})
            elif etype in ("done", "error", "aborted"):
                terminal = event
        status = "success" if (terminal and terminal.get("type") == "done") else (
            "aborted" if (terminal and terminal.get("type") == "aborted") else "error"
        )
        return {
            "text": "".join(text_parts).strip(),
            "tool_calls": tool_calls,
            "status": status,
            "usage": (terminal or {}).get("usage", {}),
            "stop_reason": (terminal or {}).get("stop_reason"),
            "endpoint_id": (terminal or {}).get("endpoint_id"),
            "model": (terminal or {}).get("model"),
            "structured": (terminal or {}).get("structured"),
            "error": (terminal or {}).get("error") if status not in ("success", "aborted") else None,
        }

    # ── Chat seam (streaming) ────────────────────────────────────────────
    async def run_chat_turn(
        self,
        *,
        project_id: str,
        agent_id: str,
        system_prompt: str,
        history: list[dict[str, Any]],
        user_text: str,
        tool_executor: ToolExecutor,
        session_key: str | None = None,
        endpoint_id: str = DEFAULT_ENDPOINT_ID,
        allowed_tools: list[str] | None = None,
        steering: SteeringBinding | None = None,
        params: Any = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Drive one governed Pi chat turn, yielding normalized SSE events."""
        effective_endpoint_id = getattr(params, "endpoint_id", None)
        if effective_endpoint_id is None and not (
            getattr(params, "model", None)
            or getattr(params, "min_context", 0)
            or getattr(params, "require_vision", False)
        ):
            effective_endpoint_id = endpoint_id
        async for event in self._drive_turn(
            operation="pi_runtime_chat_turn",
            project_id=project_id,
            agent_id=agent_id,
            system_prompt=system_prompt,
            history=history,
            user_text=user_text,
            tool_executor=tool_executor,
            session_key=session_key,
            endpoint_id=effective_endpoint_id,
            allowed_tools=allowed_tools,
            steering=steering,
            model=getattr(params, "model", None),
            min_context=getattr(params, "min_context", 0) or 0,
            require_vision=bool(getattr(params, "require_vision", False)),
            turn_params=params,
            max_turns=getattr(params, "max_turns", None),
        ):
            yield event

    # ── W1 generic execution API ────────────────────────────────────────
    async def run_completion(
        self, *, purpose: str, project_id: str, agent_id: str, system: str,
        messages: list[dict[str, Any]], params: Any,
    ) -> dict[str, Any]:
        """Run one no-tool completion through the Pi worker.

        The last message is the prompt; preceding messages remain server-owned
        history.  A failed terminal remains an outcome rather than fabricated
        output, allowing the dispatcher to preserve Pi's fail-closed rule.
        Every TurnParams knob is honored: endpoint/model/capability admission
        via the PiModelManager, generation knobs via the bind params.
        """
        history, text = _split_messages(messages)
        return await self._collect_turn(
            operation=f"pi_completion:{purpose}", project_id=project_id, agent_id=agent_id,
            system_prompt=system, history=history, user_text=text,
            tool_executor=_no_tools, session_key=None, endpoint_id=getattr(params, "endpoint_id", None),
            allowed_tools=[],
            model=getattr(params, "model", None),
            min_context=getattr(params, "min_context", 0) or 0,
            require_vision=bool(getattr(params, "require_vision", False)),
            turn_params=params,
            max_turns=getattr(params, "max_turns", None),
        )

    async def run_react(
        self, *, purpose: str, project_id: str, agent_id: str, session_key: str | None,
        system: str, messages: list[dict[str, Any]], user_text: str, tool_executor: ToolExecutor,
        tool_names: list[str], params: Any, steering_binding: SteeringBinding | None = None,
        extra_tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Bounded task-shaped ReAct seam; Python keeps the final tool allowlist.

        Hard turn budget defaults to 8 (legacy MAX_TOOL_ITERATIONS parity).
        ``extra_tools`` injects per-run dynamic tools (W3's ranked ``run_skill``)
        into the session catalog; each must still be named in ``tool_names`` or
        the allowlist filter drops it.
        """
        return await self._collect_turn(
            operation=f"pi_react:{purpose}", project_id=project_id, agent_id=agent_id,
            system_prompt=system, history=messages, user_text=user_text, tool_executor=tool_executor,
            session_key=session_key, endpoint_id=getattr(params, "endpoint_id", None),
            allowed_tools=list(tool_names), steering=steering_binding,
            model=getattr(params, "model", None),
            min_context=getattr(params, "min_context", 0) or 0,
            require_vision=bool(getattr(params, "require_vision", False)),
            turn_params=params,
            max_turns=getattr(params, "max_turns", None) or 8,
            extra_tools=extra_tools,
        )

    async def run_structured(
        self, *, purpose: str, project_id: str, agent_id: str, system: str,
        messages: list[dict[str, Any]], schema: dict[str, Any], params: Any,
        repair: bool = True,
    ) -> dict[str, Any]:
        """Return a schema-validated object via the forced structured contract.

        Protocol v2: the worker mechanically translates ``schema`` for its
        ``emit_structured_output`` capture tool, forces the provider to call
        exactly that tool, and reports the captured (never executed, never
        round-tripped) arguments on ``run.completed.structured``. This seam
        then revalidates the captured object against the ORIGINAL schema — the
        worker-side TypeBox translation is a model-side aid, Python
        revalidation is the contract.

        Fail-closed rules: free-form JSON text is never accepted as structured
        output; a missing/incorrect forced call surfaces as the typed
        ``structured_output_missing`` failure; an unsupported schema fails
        before any model call; exactly one bounded repair is allowed, and a
        second invalid result raises a typed ``PiRuntimeTurnError`` instead of
        returning an error-shaped artifact as if it were a success.

        ``repair=False`` disables the bounded repair retry (W5 skill factory:
        the caller runs its own multi-stage repair fallback chain, so a
        transport-level repair would double-repair). The first invalid or
        missing result then raises immediately.
        """
        _assert_supported_output_schema(schema)
        repair_instruction = (
            "The previous response did not produce a valid structured object. "
            "Call the emit_structured_output tool exactly once with an object matching this schema: "
            + json.dumps(schema, sort_keys=True)
        )
        prompt = list(messages)
        for attempt in range(2 if repair else 1):
            history, text = _split_messages(prompt)
            result = await self._collect_turn(
                operation=f"pi_structured:{purpose}", project_id=project_id, agent_id=agent_id,
                system_prompt=system, history=history, user_text=text,
                tool_executor=_no_tools, session_key=None,
                endpoint_id=getattr(params, "endpoint_id", None),
                allowed_tools=[], output_schema=schema,
                max_turns=getattr(params, "max_turns", None),
                model=getattr(params, "model", None),
                min_context=getattr(params, "min_context", 0) or 0,
                require_vision=bool(getattr(params, "require_vision", False)),
                turn_params=params,
            )
            if result["status"] != "success":
                error = result.get("error") or "pi_runtime_error"
                if repair and attempt == 0 and error.startswith("structured_output_missing"):
                    # A missing forced call is an invalid result: exactly one
                    # bounded repair, then the typed failure below.
                    prompt = [*messages, {"role": "user", "content": repair_instruction}]
                    continue
                raise PiRuntimeTurnError(result["status"], error)
            try:
                value = _validate_structured_value(result.get("structured"), schema)
            except ValueError as exc:
                if repair and attempt == 0:
                    prompt = [*messages, {"role": "user", "content": repair_instruction}]
                    continue
                raise PiRuntimeTurnError("error", f"structured_output_invalid:{exc}") from exc
            return {**result, "value": value}
        raise AssertionError("unreachable")

    async def run_ensemble(
        self, *, purpose: str, project_id: str, agent_id: str, system: str,
        messages: list[dict[str, Any]], n: int, distinct: bool = False,
        temperatures: list[float] | None = None, params: Any = None,
    ) -> dict[str, Any]:
        """N sampled completions (master plan §5.1 ensemble, W7 consumer).

        ``distinct=True`` draws n identity-distinct endpoints from the
        PiModelManager (fail-closed when fewer than n exist — one endpoint is
        never silently reused as "two"); ``distinct=False`` is self-MoA: n
        samples on one admitted endpoint. Samples run sequentially, each as its
        own governed turn, so per-sample usage stays exact.
        """
        manager = self._manager()
        await manager.ensure_db_projection()
        model = getattr(params, "model", None)
        require_vision = bool(getattr(params, "require_vision", False))
        min_context = getattr(params, "min_context", 0) or 0
        if distinct:
            endpoints = manager.resolve_distinct(
                n, model=model, require_vision=require_vision, min_context=min_context
            )
        else:
            endpoint = manager.resolve(
                endpoint_id=getattr(params, "endpoint_id", None), model=model,
                require_vision=require_vision, min_context=min_context,
            )
            endpoints = [endpoint] * n
        samples: list[dict[str, Any]] = []
        if params is None:
            from app.core.agentic.types import TurnParams

            params = TurnParams()
        for index, endpoint in enumerate(endpoints):
            sample_params = params
            if temperatures and index < len(temperatures) and temperatures[index] is not None:
                sample_params = replace(sample_params, temperature=float(temperatures[index]))
            sample_params = replace(sample_params, endpoint_id=endpoint.endpoint_id)
            samples.append(await self.run_completion(
                purpose=f"{purpose}#{index}", project_id=project_id, agent_id=agent_id,
                system=system, messages=messages, params=sample_params,
            ))
        usage = {
            "input_tokens": sum((s.get("usage") or {}).get("input_tokens", (s.get("usage") or {}).get("input", 0)) or 0 for s in samples),
            "output_tokens": sum((s.get("usage") or {}).get("output_tokens", (s.get("usage") or {}).get("output", 0)) or 0 for s in samples),
            "turn_count": len(samples),
        }
        usage["total_tokens"] = usage["input_tokens"] + usage["output_tokens"]
        return {
            "samples": samples,
            "endpoint_ids": [endpoint.endpoint_id for endpoint in endpoints],
            "usage": usage,
            "status": "success" if all(s.get("status") == "success" for s in samples) else "error",
        }

    # ── A2A delegation seam ──────────────────────────────────────────────
    async def run_delegation(
        self,
        *,
        project_id: str,
        agent_id: str,
        system_prompt: str,
        task_text: str,
        tool_executor: ToolExecutor,
        history: list[dict[str, Any]] | None = None,
        session_key: str | None = None,
        endpoint_id: str = DEFAULT_ENDPOINT_ID,
        allowed_tools: list[str] | None = None,
    ) -> dict[str, Any]:
        """Execute one delegated work item through the real Pi Agent.

        The A2A route gate chain runs *before* this hook (admission, project
        scope, persistence, audit); this only drives the already-admitted work.
        Uses a delegation-safe tool subset; results persist through the caller's
        authority ``tool_executor``. Reports/promotions stay behind their gates.
        """
        return await self._collect_turn(
            operation="pi_runtime_delegation",
            project_id=project_id,
            agent_id=agent_id,
            system_prompt=system_prompt,
            history=history or [],
            user_text=task_text,
            tool_executor=tool_executor,
            session_key=session_key,
            endpoint_id=endpoint_id,
            allowed_tools=list(allowed_tools) if allowed_tools is not None else list(DELEGATION_TOOLS),
        )

    # ── Channel (pi_local) seam ──────────────────────────────────────────
    async def run_channel_turn(
        self,
        *,
        project_id: str,
        agent_id: str,
        system_prompt: str,
        inbound_text: str,
        tool_executor: ToolExecutor,
        history: list[dict[str, Any]] | None = None,
        session_key: str | None = None,
        endpoint_id: str = DEFAULT_ENDPOINT_ID,
        allowed_tools: list[str] | None = None,
    ) -> dict[str, Any]:
        """Produce one in-process ``pi_local`` channel reply via the real loop.

        Replaces the old canned response. Ownership/pause/cross-project/stop
        semantics live above this seam and are unchanged.
        """
        return await self._collect_turn(
            operation="pi_runtime_channel_turn",
            project_id=project_id,
            agent_id=agent_id,
            system_prompt=system_prompt,
            history=history or [],
            user_text=inbound_text,
            tool_executor=tool_executor,
            session_key=session_key,
            endpoint_id=endpoint_id,
            allowed_tools=list(allowed_tools) if allowed_tools is not None else list(CHANNEL_TOOLS),
        )

    # ── Governed Autoresearch seam ───────────────────────────────────────
    async def run_autoresearch_turn(
        self,
        *,
        project_id: str,
        agent_id: str,
        system_prompt: str,
        objective: str,
        tool_executor: ToolExecutor,
        loop_type: str,
        target: str,
        session_key: str | None = None,
        endpoint_id: str = DEFAULT_ENDPOINT_ID,
    ) -> dict[str, Any]:
        """Run one bounded governed Autoresearch turn and return a *candidate
        proposal only*.

        Read-only/proposal-only tool subset, no background loop, no promotion,
        no filesystem mutation. The proposal is always ``governance_required``
        and never ``report_evidence`` — human gates are unchanged (AC-5).

        Fails closed: a non-success terminal (``error``/``aborted``) raises
        ``PiRuntimeTurnError`` instead of fabricating a candidate proposal from a
        failed or partially-streamed turn (RF3-2).
        """
        result = await self._collect_turn(
            operation="pi_runtime_autoresearch",
            project_id=project_id,
            agent_id=agent_id,
            system_prompt=system_prompt,
            history=[],
            user_text=objective,
            tool_executor=tool_executor,
            session_key=session_key,
            endpoint_id=endpoint_id,
            allowed_tools=list(AUTORESEARCH_TOOLS),
        )
        if result["status"] != "success":
            # Reject the terminal before any candidate artifact is built — a
            # failed/aborted turn must never yield a governed proposal.
            raise PiRuntimeTurnError(result["status"], result.get("error"))
        return {
            "status": "candidate_proposal",
            "loop_type": loop_type,
            "target": target,
            "project_id": project_id,
            "production_mutation_allowed": False,
            "background_task_started": False,
            "proposal": {
                "hypothesis": result["text"]
                or "Pi produced no governed autoresearch hypothesis for this turn.",
                "governance_required": True,
                "report_evidence": False,
                "promotion": "blocked_pending_human_review",
            },
            "runtime": {
                "engine": "pi",
                "turn_status": result["status"],
                "tool_calls": [tc["tool"] for tc in result["tool_calls"]],
                "endpoint_id": result["endpoint_id"],
            },
        }

    def steering_binding(
        self, *, agent_id: str, project_id: str, session_key: str | None = None
    ) -> SteeringBinding:
        """Build a steering binding from the process-wide steering manager.

        ``session_key`` is optional: when omitted the engine binds the resolved
        session key at turn start, so each live turn owns a distinct
        ``(agent_id, project_id, session_key)`` binding.
        """
        from app.core.steering import steering_manager

        return SteeringBinding(
            agent_id=agent_id, project_id=project_id, manager=steering_manager, session_key=session_key
        )

    async def _record_tool_rejection(
        self,
        endpoint: ResolvedPiEndpoint,
        project_id: str,
        agent_id: str,
        tool_name: str,
        operation: str,
    ) -> None:
        """Audit row for a rejected out-of-catalog tool call (B-12).

        A compromised worker must leave a durable trace: every allowlist
        rejection lands in the telemetry span store with the endpoint identity
        only (never URL/key material), mirroring ``_record_turn_telemetry``.
        """
        identity = endpoint.telemetry_identity()  # endpoint_id / provider_kind / model only
        try:
            await telemetry_recorder.record_span(
                trace_id=f"pi-{uuid.uuid4().hex}",
                operation=operation,
                model_name=endpoint.model,
                agent_id=agent_id,
                project_id=project_id,
                duration_ms=0.0,
                status="error",
                error_type="tool_not_allowed",
                error_message=f"out-of-catalog tool rejected: {tool_name}",
                event_kind="pi_tool_authority_rejection",
                route_id=json.dumps(identity, sort_keys=True),
                tool_name=tool_name,
                tool_success=False,
                source="pi-runtime",
            )
        except Exception:  # pragma: no cover - audit is never load-bearing
            logger.debug("pi-runtime: tool rejection audit record failed")

    async def _record_turn_telemetry(
        self,
        endpoint: ResolvedPiEndpoint,
        project_id: str,
        agent_id: str,
        terminal: dict[str, Any] | None,
        operation: str,
    ) -> None:
        status = "success" if (terminal and terminal.get("type") == "done") else (
            "aborted" if (terminal and terminal.get("type") == "aborted") else "error"
        )
        usage = (terminal or {}).get("usage") or {}
        identity = endpoint.telemetry_identity()  # endpoint_id / provider_kind / model only
        try:
            await telemetry_recorder.record_span(
                trace_id=f"pi-{uuid.uuid4().hex}",
                operation=operation,
                model_name=endpoint.model,
                agent_id=agent_id,
                project_id=project_id,
                duration_ms=0.0,
                status=status,
                event_kind="pi_runtime_turn",
                route_id=json.dumps(
                    {**identity, "usage": usage, "stop_reason": (terminal or {}).get("stop_reason")},
                    sort_keys=True,
                ),
                source="pi-runtime",
            )
        except Exception:  # pragma: no cover - telemetry is never load-bearing
            logger.debug("pi-runtime: telemetry record failed")


def _map_frame(frame: dict[str, Any], endpoint: ResolvedPiEndpoint) -> dict[str, Any] | None:
    ftype = frame.get("type")
    if ftype == "run.started":
        return {"type": "run_started", "run_id": frame.get("run_id")}
    if ftype == "assistant.delta":
        return {"type": "content", "text": frame.get("text", "")}
    if ftype == "thinking.delta":
        return {"type": "thinking", "text": frame.get("text", "")}
    if ftype == "tool.call":
        return {"type": "tool_call", "tool": frame.get("name"), "params": frame.get("arguments") or {}}
    if ftype == "run.completed":
        return {
            "type": "done",
            "usage": frame.get("usage") or {},
            "stop_reason": frame.get("stop_reason"),
            "endpoint_id": endpoint.endpoint_id,
            "model": endpoint.model,
            # Present only on forced structured-output runs (protocol v2): the
            # worker-captured emit_structured_output arguments. Never parsed
            # from free-form text.
            "structured": frame.get("structured"),
        }
    if ftype == "run.failed":
        return {"type": "error", "error": frame.get("error", "pi_runtime_error")}
    if ftype == "run.aborted":
        return {"type": "aborted"}
    return None


async def _no_tools(name: str, args: dict[str, Any], project_id: str, agent_id: str) -> dict[str, Any]:
    return {"ok": False, "error": "tool_not_allowed"}


def _split_messages(messages: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
    if not messages:
        return [], ""
    history = list(messages[:-1])
    last = messages[-1]
    return history, str(last.get("content") or "")


def _validate_structured_value(value: Any, schema: dict[str, Any]) -> dict[str, Any]:
    """Validate the worker-captured structured object against the ORIGINAL schema.

    ``value`` is never free-form text: it is the object the worker captured
    from the forced ``emit_structured_output`` call. A missing capture or a
    schema violation is a typed ``ValueError``; callers repair once, then fail
    closed.
    """
    if value is None:
        raise ValueError("structured_output_missing")
    if not isinstance(value, dict):
        raise ValueError("not_object")
    try:
        import jsonschema
        jsonschema.validate(value, schema)
    except ImportError:
        required = schema.get("required", [])
        if any(key not in value for key in required):
            raise ValueError("missing_required_property")
    except Exception as exc:
        raise ValueError("schema_validation_failed") from exc
    return value


# Keep in sync with SUPPORTED_NODE_KEYS / SUPPORTED_TYPES in
# pi-runtime/src/structured.mjs — both sides reject the same constructs so an
# unforceable schema fails closed no matter which side sees it first.
_SCHEMA_NODE_KEYS = frozenset({
    "type", "properties", "required", "additionalProperties", "items", "enum",
    "const", "description", "title", "minimum", "maximum", "exclusiveMinimum",
    "exclusiveMaximum", "multipleOf", "minLength", "maxLength", "pattern",
    "minItems", "maxItems", "uniqueItems", "minProperties", "maxProperties",
})
_SCHEMA_TYPES = frozenset({"object", "string", "number", "integer", "boolean", "array", "null"})


def _find_unsupported_schema_construct(node: Any, path: str = "$") -> str | None:
    """Return a ``<path>:<detail>`` reason when ``node`` falls outside the
    mechanically translatable JSON Schema subset, else None."""
    if not isinstance(node, dict):
        return f"{path}:not_a_schema_object"
    for key in node:
        if key not in _SCHEMA_NODE_KEYS:
            return f"{path}:{key}"
    if "const" in node or "enum" in node:
        if "enum" in node and (not isinstance(node["enum"], list) or not node["enum"]):
            return f"{path}:enum"
        return None
    raw = node.get("type")
    types = [raw] if isinstance(raw, str) else list(raw) if isinstance(raw, list) else []
    if not types:
        return f"{path}:missing_type"
    for t in types:
        if not isinstance(t, str) or t not in _SCHEMA_TYPES:
            return f"{path}:type:{t}"
    if "object" in types:
        props = node.get("properties", {})
        if not isinstance(props, dict):
            return f"{path}:properties"
        required = node.get("required", [])
        if not isinstance(required, list) or any(not isinstance(name, str) for name in required):
            return f"{path}:required"
        additional = node.get("additionalProperties")
        if additional is not None and not isinstance(additional, bool):
            return f"{path}:additionalProperties"
        for name, sub in props.items():
            bad = _find_unsupported_schema_construct(sub, f"{path}.properties.{name}")
            if bad:
                return bad
    if "array" in types:
        items = node.get("items")
        if not isinstance(items, dict):
            return f"{path}:items"
        bad = _find_unsupported_schema_construct(items, f"{path}.items")
        if bad:
            return bad
    return None


def _assert_supported_output_schema(schema: dict[str, Any]) -> None:
    """Fail closed BEFORE any model call when the schema cannot be forced."""
    bad = _find_unsupported_schema_construct(schema)
    if bad is not None:
        raise PiRuntimeTurnError("error", f"structured_output_schema_unsupported:{bad}")
    root_type = schema.get("type")
    root_types = [root_type] if isinstance(root_type, str) else list(root_type or [])
    if "enum" not in schema and "const" not in schema and "object" not in root_types:
        raise PiRuntimeTurnError("error", "structured_output_schema_unsupported:$:root_not_object")
