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
from dataclasses import dataclass
from typing import Any, AsyncIterator, Awaitable, Callable

from app.core.telemetry import telemetry_recorder

from .endpoints import (
    DEFAULT_ENDPOINT_ID,
    PiEndpointResolver,
    PiRuntimeTurnError,
    ResolvedPiEndpoint,
)
from .supervisor import PiRuntimeSupervisor, get_supervisor
from .tools import build_tool_catalog

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
    """Bind a live Pi turn to a project-scoped steering queue."""

    agent_id: str
    project_id: str
    manager: Any  # app.core.steering.SteeringManager (duck-typed to avoid a cycle)


def _session_revision(history: list[dict[str, Any]], endpoint: ResolvedPiEndpoint) -> str:
    digest = hashlib.sha256()
    digest.update(json.dumps(history or [], sort_keys=True, default=str).encode("utf-8"))
    digest.update(endpoint.endpoint_id.encode("utf-8"))
    digest.update(endpoint.model.encode("utf-8"))
    return digest.hexdigest()[:16]


def _bind_payload(endpoint: ResolvedPiEndpoint) -> dict[str, Any]:
    payload = {
        "endpoint_id": endpoint.endpoint_id,
        "provider_kind": endpoint.provider_kind,
        "base_url": endpoint.base_url,
        "model": endpoint.model,
        "api_key": endpoint.api_key,
        "timeout_ms": endpoint.timeout_ms,
        "max_retries": endpoint.max_retries,
    }
    # Test-only deterministic provider: never set by the production resolver.
    if endpoint.provider_kind == "faux" and endpoint.faux_responses is not None:
        payload["faux_responses"] = list(endpoint.faux_responses)
    return payload


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
    ) -> None:
        self._resolver = resolver or PiEndpointResolver()
        self._supervisor = supervisor

    def _sup(self) -> PiRuntimeSupervisor:
        return self._supervisor or get_supervisor()

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
        endpoint_id: str,
        allowed_tools: list[str] | None,
        steering: SteeringBinding | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Drive one governed Pi turn, yielding normalized events.

        Resolves the private endpoint first, so a resolver/Keychain miss raises
        ``PiEndpointResolutionError`` before any worker/provider work.
        """
        endpoint = self._resolver.resolve(endpoint_id)
        catalog = build_tool_catalog(allowed_tools)
        key = session_key or f"pi-{operation}-{uuid.uuid4().hex}"
        revision = _session_revision(history, endpoint)
        sup = self._sup()

        async def tool_handler(name: str, args: dict[str, Any]) -> dict[str, Any]:
            # Authority round-trip: authenticated scope is re-injected here; the
            # model cannot set project_id/agent_id.
            result = await tool_executor(name, args, project_id, agent_id)
            return _normalize_tool_result(result)

        await sup.ensure_started()
        await sup.open_session(
            key,
            system_prompt=system_prompt,
            history=history,
            revision=revision,
            catalog=catalog,
        )
        terminal: dict[str, Any] | None = None
        steer_task: asyncio.Task | None = None
        steering_bound = False
        try:
            await sup.bind_provider(key, _bind_payload(endpoint))
            if steering is not None:
                steering_bound = True
                await steering.manager.mark_working(steering.agent_id, project_id=steering.project_id)
                steer_task = asyncio.create_task(self._pump_steering(sup, key, steering))
            async for frame in sup.run_turn(key, user_text, tool_handler):
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
                    await steering.manager.mark_idle(steering.agent_id, project_id=steering.project_id)
                except Exception:  # pragma: no cover - teardown best effort
                    logger.debug("pi-runtime: steering mark_idle failed")
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
        ups to ``turn.follow_up``; an external abort (``is_working`` cleared)
        maps to ``turn.abort`` — the worker then emits exactly one ``run.aborted``.
        """
        mgr = steering.manager
        aid, pid = steering.agent_id, steering.project_id
        try:
            while True:
                for msg in await mgr.get_steering(aid, project_id=pid):
                    await sup.steer(session_key, getattr(msg, "message", str(msg)))
                for msg in await mgr.get_follow_up(aid, project_id=pid):
                    await sup.follow_up(session_key, getattr(msg, "message", str(msg)))
                status = mgr.get_status(aid, project_id=pid)
                if not status.get("is_working"):
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
    ) -> AsyncIterator[dict[str, Any]]:
        """Drive one governed Pi chat turn, yielding normalized SSE events."""
        async for event in self._drive_turn(
            operation="pi_runtime_chat_turn",
            project_id=project_id,
            agent_id=agent_id,
            system_prompt=system_prompt,
            history=history,
            user_text=user_text,
            tool_executor=tool_executor,
            session_key=session_key,
            endpoint_id=endpoint_id,
            allowed_tools=allowed_tools,
            steering=steering,
        ):
            yield event

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

    def steering_binding(self, *, agent_id: str, project_id: str) -> SteeringBinding:
        """Build a steering binding from the process-wide steering manager."""
        from app.core.steering import steering_manager

        return SteeringBinding(agent_id=agent_id, project_id=project_id, manager=steering_manager)

    async def _record_turn_telemetry(
        self,
        endpoint: ResolvedPiEndpoint,
        project_id: str,
        agent_id: str,
        terminal: dict[str, Any] | None,
        operation: str,
    ) -> None:
        status = "success" if (terminal and terminal.get("type") == "done") else "error"
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
        }
    if ftype == "run.failed":
        return {"type": "error", "error": frame.get("error", "pi_runtime_error")}
    if ftype == "run.aborted":
        return {"type": "aborted"}
    return None
