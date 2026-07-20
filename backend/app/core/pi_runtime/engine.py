"""PiExecutionService — the single facade that owns Pi runtime semantics.

A route hands the service the *already authorized* context (project, agent,
system prompt with protected blocks, history) plus an authority ``tool_executor``
and a user turn. The service resolves the private endpoint, drives the real
pi-agent-core Agent in the worker, executes every tool call in Python with the
authenticated project/agent scope re-injected (model-supplied scope fields are
ignored), and yields normalized events. It never consults ``ComputeRegistry``.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from typing import Any, AsyncIterator, Awaitable, Callable

from app.core.telemetry import telemetry_recorder

from .endpoints import DEFAULT_ENDPOINT_ID, PiEndpointResolver, ResolvedPiEndpoint
from .supervisor import PiRuntimeSupervisor, get_supervisor
from .tools import build_tool_catalog

logger = logging.getLogger(__name__)

# (tool_name, params, project_id, agent_id) -> {"result": ...} | {"error": ...}
ToolExecutor = Callable[[str, dict[str, Any], str, str], Awaitable[dict[str, Any]]]


def _session_revision(history: list[dict[str, Any]], endpoint: ResolvedPiEndpoint) -> str:
    digest = hashlib.sha256()
    digest.update(json.dumps(history or [], sort_keys=True, default=str).encode("utf-8"))
    digest.update(endpoint.endpoint_id.encode("utf-8"))
    digest.update(endpoint.model.encode("utf-8"))
    return digest.hexdigest()[:16]


def _bind_payload(endpoint: ResolvedPiEndpoint) -> dict[str, Any]:
    return {
        "endpoint_id": endpoint.endpoint_id,
        "provider_kind": endpoint.provider_kind,
        "base_url": endpoint.base_url,
        "model": endpoint.model,
        "api_key": endpoint.api_key,
        "timeout_ms": endpoint.timeout_ms,
        "max_retries": endpoint.max_retries,
    }


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
    ) -> AsyncIterator[dict[str, Any]]:
        """Drive one governed Pi chat turn. Raises ``PiEndpointResolutionError``
        before any worker/provider work when the endpoint cannot be resolved.
        """
        endpoint = self._resolver.resolve(endpoint_id)
        catalog = build_tool_catalog(allowed_tools)
        key = session_key or f"pi-chat-{uuid.uuid4().hex}"
        revision = _session_revision(history, endpoint)
        sup = self._sup()

        async def tool_handler(name: str, args: dict[str, Any]) -> dict[str, Any]:
            # Authority round-trip: authenticated scope is re-injected here; the
            # model cannot set project_id/agent_id.
            result = await tool_executor(name, args, project_id, agent_id)
            if isinstance(result, dict) and "error" in result and "result" not in result:
                return {"ok": False, "error": str(result.get("error"))}
            if isinstance(result, dict) and "result" in result:
                return {"ok": True, "result": result.get("result")}
            return {"ok": True, "result": result}

        await sup.ensure_started()
        await sup.open_session(
            key,
            system_prompt=system_prompt,
            history=history,
            revision=revision,
            catalog=catalog,
        )
        terminal: dict[str, Any] | None = None
        try:
            await sup.bind_provider(key, _bind_payload(endpoint))
            async for frame in sup.run_turn(key, user_text, tool_handler):
                event = _map_frame(frame, endpoint)
                if event is None:
                    continue
                if event["type"] in ("done", "error", "aborted"):
                    terminal = event
                yield event
        finally:
            try:
                await sup.close_session(key)
            except Exception:  # pragma: no cover - teardown best effort
                logger.debug("pi-runtime: session close failed for %s", key)
            await self._record_turn_telemetry(endpoint, project_id, agent_id, terminal)

    async def _record_turn_telemetry(
        self,
        endpoint: ResolvedPiEndpoint,
        project_id: str,
        agent_id: str,
        terminal: dict[str, Any] | None,
    ) -> None:
        status = "success" if (terminal and terminal["type"] == "done") else "error"
        usage = (terminal or {}).get("usage") or {}
        identity = endpoint.telemetry_identity()  # endpoint_id / provider_kind / model only
        try:
            await telemetry_recorder.record_span(
                trace_id=f"pi-{uuid.uuid4().hex}",
                operation="pi_runtime_chat_turn",
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
