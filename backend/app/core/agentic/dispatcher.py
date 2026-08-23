"""Engine selection and common accounting for agentic invocations.

Every product call site enters through one of the five verbs (master plan
§5.1): ``chat_turn``, ``completion``, ``structured``, ``ensemble``, ``embed``
(plus the W1 ``react`` task seam). The dispatcher only resolves the engine,
executes, and records — it never contains business logic and never silently
switches engines.

Every verb records exactly one usage-ledger row per dispatch (§5.5) — success,
error, abort, endpoint-resolution failure, and legacy-executor failure alike —
so the accounting contract has no silent gaps.

Engine resolution order (first match wins):
  1. per-call override (``engine=`` — benchmark harness / A2A envelope metadata)
  2. request header ``x-istara-agent-engine`` (the pi_replacement predicate)
  3. project setting ``agentic_engine`` (``projects.agentic_engine``, W1)
  4. ``settings.agentic_engine_default`` ("legacy" until the owner flips it)
"""

from __future__ import annotations

import logging
import time
from typing import Any, Awaitable, Callable

from app.config import settings
from app.core.pi_replacement import PI_ENGINE_VALUES
from app.core.pi_runtime.endpoints import DEFAULT_ENDPOINT_ID
from app.core.pi_runtime.engine import PiExecutionService

from .legacy import legacy_executor as _real_legacy_executor
from .types import (
    AgenticDispatchError,
    EngineChoice,
    EnsembleResult,
    StructuredResult,
    TurnParams,
    TurnResult,
)
from .usage_ledger import record_agentic_usage

logger = logging.getLogger(__name__)

LegacyExecutor = Callable[..., Awaitable[dict[str, Any]]]


def _header_engine(request: Any | None) -> str | None:
    """Level-2 selection: the existing reversible request-header predicate."""
    if request is None:
        return None
    header_name = (settings.pi_replacement_request_header or "").strip() or "x-istara-agent-engine"
    headers = getattr(request, "headers", None) or {}
    value = (headers.get(header_name) or "").strip().lower()
    return value or None


def _as_choice(candidate: str | None) -> EngineChoice:
    return "pi" if (candidate or "").strip().lower() in PI_ENGINE_VALUES else "legacy"


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if content is None:
        return ""
    return str(content)


def _request_text(system: str | None, messages: list[dict[str, Any]], extra: str | None = None) -> str:
    parts = [system or ""]
    parts.extend(_content_text(m.get("content")) for m in messages or [])
    if extra:
        parts.append(extra)
    return "\n".join(part for part in parts if part)


class AgenticDispatcher:
    """Single entry point for every agentic-loop / model invocation in Istara."""

    def __init__(self, *, pi_service: PiExecutionService | None = None,
                 legacy_executor: LegacyExecutor | None = None,
                 embeddings_gateway: Any | None = None) -> None:
        self._pi = pi_service or PiExecutionService()
        # The production default binds the REAL legacy plane; tests inject a stub.
        self._legacy = legacy_executor if legacy_executor is not None else _real_legacy_executor
        # W8: Pi embeds go through the EmbeddingsGateway sharing the engine's
        # own PiModelManager (one identity plane); tests inject a stub.
        self._embeddings_gateway = embeddings_gateway

    # ── engine resolution ────────────────────────────────────────────────
    def resolve_engine(self, *, engine: EngineChoice | None = None, request: Any | None = None,
                       project_engine: str | None = None) -> EngineChoice:
        """Synchronous resolution when the project setting is already known."""
        if engine is not None:
            return engine
        header = _header_engine(request)
        if header:
            return _as_choice(header)
        if project_engine:
            return _as_choice(project_engine)
        return _as_choice(getattr(settings, "agentic_engine_default", "legacy"))

    async def _project_engine(self, project_id: str | None) -> str | None:
        """Level-3 selection: the project's persisted ``agentic_engine`` column.

        A storage miss falls through to the global default (today's behavior)
        rather than blocking the call; the lookup is read-only.
        """
        if not project_id:
            return None
        try:
            from sqlalchemy import select

            from app.models.database import async_session
            from app.models.project import Project

            async with async_session() as db:
                value = await db.scalar(select(Project.agentic_engine).where(Project.id == project_id))
            return (value or "").strip() or None
        except Exception:  # pragma: no cover - storage unavailable: use default
            logger.debug("agentic dispatcher: project engine lookup failed for %s", project_id)
            return None

    async def _resolve(self, *, project_id: str | None, engine: EngineChoice | None,
                       request: Any | None) -> EngineChoice:
        if engine is not None:
            return engine
        header = _header_engine(request)
        if header:
            return _as_choice(header)
        project_engine = await self._project_engine(project_id)
        if project_engine:
            return _as_choice(project_engine)
        return _as_choice(getattr(settings, "agentic_engine_default", "legacy"))

    # ── verbs ────────────────────────────────────────────────────────────
    async def chat_turn(self, *, project_id: str, agent_id: str, session_key: str | None,
                        session_id: str | None = None,
                        system_prompt: str, messages: list[dict[str, Any]], user_text: str,
                        tool_executor: Any = None, tool_names: list[str] | None = None,
                        tools: list[dict[str, Any]] | None = None, params: TurnParams | None = None,
                        stream_cb: Any = None, steering_binding: Any = None,
                        engine: EngineChoice | None = None, request: Any | None = None,
                        task_id: str | None = None, spine_phase: str | None = None) -> TurnResult:
        """One governed chat turn. Pi: engine.run_chat_turn; legacy: chat.py's ReAct loop."""
        params = params or TurnParams()
        started = time.perf_counter()
        selected = await self._resolve(project_id=project_id, engine=engine, request=request)
        try:
            if selected == "pi":
                outcome = await self._collect_pi_stream(
                    purpose="chat_turn", project_id=project_id, agent_id=agent_id, session_key=session_key,
                    system_prompt=system_prompt, messages=messages, user_text=user_text,
                    tool_executor=tool_executor, tool_names=tool_names, params=params,
                    stream_cb=stream_cb, steering_binding=steering_binding,
                )
            else:
                outcome = await self._legacy_outcome(
                    "chat_turn", purpose="chat_turn", project_id=project_id, agent_id=agent_id,
                    system=system_prompt, messages=messages, user_text=user_text,
                    tool_executor=tool_executor, tool_names=tool_names, tools=tools,
                    params=params, stream_cb=stream_cb,
                )
        except Exception as exc:
            await self._record_failure(engine=selected, purpose="chat_turn", project_id=project_id,
                                       agent_id=agent_id, params=params, started=started,
                                       task_id=task_id, spine_phase=spine_phase,
                                       session_id=session_id, exc=exc)
            raise
        await self._record_outcome(engine=selected, purpose="chat_turn", project_id=project_id,
                                   agent_id=agent_id, params=params, started=started, outcome=outcome,
                                   task_id=task_id, spine_phase=spine_phase, session_id=session_id,
                                   request_text=_request_text(system_prompt, messages, extra=user_text))
        return TurnResult(text=outcome.get("text", ""), usage=outcome.get("usage") or {},
                          stop_reason=outcome.get("stop_reason"), endpoint_id=outcome.get("endpoint_id"),
                          status=outcome.get("status", "success"), tool_calls=outcome.get("tool_calls") or [], model=outcome.get("model"))

    async def completion(self, *, purpose: str, project_id: str, system: str | None,
                         messages: list[dict[str, Any]], params: TurnParams, agent_id: str = "istara-main",
                         engine: EngineChoice | None = None, request: Any | None = None,
                         task_id: str | None = None, spine_phase: str | None = None) -> TurnResult:
        started = time.perf_counter()
        selected = await self._resolve(project_id=project_id, engine=engine, request=request)
        try:
            if selected == "pi":
                outcome = await self._pi.run_completion(purpose=purpose, project_id=project_id, agent_id=agent_id,
                                                        system=system or "", messages=messages, params=params)
            else:
                outcome = await self._legacy_outcome("completion", purpose=purpose, project_id=project_id,
                                                     agent_id=agent_id, system=system, messages=messages, params=params)
        except Exception as exc:
            await self._record_failure(engine=selected, purpose=purpose, project_id=project_id,
                                       agent_id=agent_id, params=params, started=started,
                                       task_id=task_id, spine_phase=spine_phase, exc=exc)
            raise
        await self._record_outcome(engine=selected, purpose=purpose, project_id=project_id,
                                   agent_id=agent_id, params=params, started=started, outcome=outcome,
                                   task_id=task_id, spine_phase=spine_phase,
                                   request_text=_request_text(system, messages))
        return TurnResult(text=outcome.get("text", ""), usage=outcome.get("usage") or {},
                          stop_reason=outcome.get("stop_reason"), endpoint_id=outcome.get("endpoint_id"),
                          status=outcome.get("status", "success"), tool_calls=outcome.get("tool_calls") or [], model=outcome.get("model"))

    async def structured(self, *, purpose: str, project_id: str, system: str | None,
                         messages: list[dict[str, Any]], schema: dict[str, Any], params: TurnParams,
                         agent_id: str = "istara-main", engine: EngineChoice | None = None,
                         request: Any | None = None, repair: bool = True,
                         task_id: str | None = None, spine_phase: str | None = None) -> StructuredResult:
        started = time.perf_counter()
        selected = await self._resolve(project_id=project_id, engine=engine, request=request)
        try:
            if selected == "pi":
                outcome = await self._pi.run_structured(purpose=purpose, project_id=project_id, agent_id=agent_id,
                                                        system=system or "", messages=messages, schema=schema,
                                                        params=params, repair=repair)
            else:
                outcome = await self._legacy_outcome("structured", purpose=purpose, project_id=project_id,
                                                     agent_id=agent_id, system=system, messages=messages,
                                                     schema=schema, params=params)
        except Exception as exc:
            await self._record_failure(engine=selected, purpose=purpose, project_id=project_id,
                                       agent_id=agent_id, params=params, started=started,
                                       task_id=task_id, spine_phase=spine_phase, exc=exc)
            raise
        await self._record_outcome(engine=selected, purpose=purpose, project_id=project_id,
                                   agent_id=agent_id, params=params, started=started, outcome=outcome,
                                   task_id=task_id, spine_phase=spine_phase,
                                   request_text=_request_text(system, messages))
        return StructuredResult(text=outcome.get("text", ""), value=outcome.get("value") or {},
                                usage=outcome.get("usage") or {}, stop_reason=outcome.get("stop_reason"),
                                endpoint_id=outcome.get("endpoint_id"), status=outcome.get("status", "success"))

    async def react(self, *, purpose: str, project_id: str, agent_id: str, session_key: str | None,
                    system: str, messages: list[dict[str, Any]], user_text: str, tool_executor: Any,
                    tool_names: list[str], params: TurnParams,
                    tools: list[dict[str, Any]] | None = None,
                    extra_tools: list[dict[str, Any]] | None = None,
                    steering_binding: Any = None,
                    engine: EngineChoice | None = None,
                    request: Any | None = None, task_id: str | None = None,
                    spine_phase: str | None = None) -> TurnResult:
        started = time.perf_counter()
        selected = await self._resolve(project_id=project_id, engine=engine, request=request)
        try:
            if selected != "pi":
                outcome = await self._legacy_outcome("react", purpose=purpose, project_id=project_id, agent_id=agent_id,
                                                     system=system, messages=messages, user_text=user_text,
                                                     tool_executor=tool_executor,
                                                     tool_names=tool_names,
                                                     tools=tools, params=params)
            else:
                outcome = await self._pi.run_react(purpose=purpose, project_id=project_id, agent_id=agent_id,
                                                   session_key=session_key, system=system, messages=messages,
                                                   user_text=user_text, tool_executor=tool_executor,
                                                   tool_names=tool_names, params=params,
                                                   steering_binding=steering_binding,
                                                   extra_tools=extra_tools)
        except Exception as exc:
            await self._record_failure(engine=selected, purpose=purpose, project_id=project_id,
                                       agent_id=agent_id, params=params, started=started,
                                       task_id=task_id, spine_phase=spine_phase, exc=exc)
            raise
        await self._record_outcome(engine=selected, purpose=purpose, project_id=project_id,
                                   agent_id=agent_id, params=params, started=started, outcome=outcome,
                                   task_id=task_id, spine_phase=spine_phase,
                                   request_text=_request_text(system, messages, extra=user_text))
        return TurnResult(text=outcome.get("text", ""), usage=outcome.get("usage") or {},
                          stop_reason=outcome.get("stop_reason"), endpoint_id=outcome.get("endpoint_id"),
                          status=outcome.get("status", "success"), tool_calls=outcome.get("tool_calls") or [], model=outcome.get("model"))

    async def ensemble(self, *, purpose: str, project_id: str, messages: list[dict[str, Any]],
                       n: int, distinct: bool = False, system: str | None = None,
                       temperatures: list[float] | None = None, params: TurnParams | None = None,
                       minimum_n: int | None = None,
                       agent_id: str = "istara-main", engine: EngineChoice | None = None,
                       request: Any | None = None, task_id: str | None = None,
                       spine_phase: str | None = None) -> EnsembleResult:
        """N samples — distinct Pi endpoints (W7 dual-coder) or self-MoA on one."""
        params = params or TurnParams()
        started = time.perf_counter()
        selected = await self._resolve(project_id=project_id, engine=engine, request=request)
        try:
            if selected == "pi":
                outcome = await self._pi.run_ensemble(purpose=purpose, project_id=project_id, agent_id=agent_id,
                                                      system=system or "", messages=messages, n=n, distinct=distinct,
                                                      temperatures=temperatures, params=params)
            else:
                outcome = await self._legacy_outcome("ensemble", purpose=purpose, project_id=project_id,
                                                     agent_id=agent_id, system=system, messages=messages,
                                                     n=n, distinct=distinct, temperatures=temperatures,
                                                     params=params, minimum_n=minimum_n)
        except Exception as exc:
            await self._record_failure(engine=selected, purpose=purpose, project_id=project_id,
                                       agent_id=agent_id, params=params, started=started,
                                       task_id=task_id, spine_phase=spine_phase, exc=exc)
            raise
        await self._record_outcome(engine=selected, purpose=purpose, project_id=project_id,
                                   agent_id=agent_id, params=params, started=started, outcome=outcome,
                                   task_id=task_id, spine_phase=spine_phase,
                                   request_text=_request_text(system, messages))
        samples = [
            TurnResult(text=sample.get("text", ""), usage=sample.get("usage") or {},
                       stop_reason=sample.get("stop_reason"), endpoint_id=sample.get("endpoint_id"),
                       status=sample.get("status", "success"), tool_calls=sample.get("tool_calls") or [])
            for sample in outcome.get("samples") or []
        ]
        return EnsembleResult(samples=samples, endpoint_ids=list(outcome.get("endpoint_ids") or []),
                              usage=outcome.get("usage") or {}, status=outcome.get("status", "success"))

    async def embed(self, *, texts: list[str], project_id: str | None = None,
                    params: TurnParams | None = None, agent_id: str = "istara-main",
                    engine: EngineChoice | None = None, request: Any | None = None,
                    task_id: str | None = None, spine_phase: str | None = None) -> list[list[float]]:
        """Legacy: the registry embed path. Pi: the W8 EmbeddingsGateway."""
        params = params or TurnParams()
        started = time.perf_counter()
        selected = await self._resolve(project_id=project_id, engine=engine, request=request)
        if selected == "pi":
            # Pi embeds run through the gateway under Pi identity management.
            # A gateway failure raises and records its one error row — the
            # dispatch never leaks onto the legacy plane or donated compute.
            try:
                outcome = await self._embed_gateway().embed(list(texts), model=params.model)
            except Exception as exc:
                await self._record_failure(engine=selected, purpose="embed", project_id=project_id or "",
                                           agent_id=agent_id, params=params, started=started,
                                           task_id=task_id, spine_phase=spine_phase, exc=exc)
                raise
            await self._record_outcome(engine=selected, purpose="embed", project_id=project_id or "",
                                       agent_id=agent_id, params=params, started=started, outcome=outcome,
                                       task_id=task_id, spine_phase=spine_phase,
                                       request_text="\n".join(_content_text(t) for t in texts))
            return list(outcome.get("embeddings") or [])
        try:
            outcome = await self._legacy_outcome("embed", texts=texts, project_id=project_id, params=params)
        except Exception as exc:
            await self._record_failure(engine=selected, purpose="embed", project_id=project_id or "",
                                       agent_id=agent_id, params=params, started=started,
                                       task_id=task_id, spine_phase=spine_phase, exc=exc)
            raise
        await self._record_outcome(engine=selected, purpose="embed", project_id=project_id or "",
                                   agent_id=agent_id, params=params, started=started, outcome=outcome,
                                   task_id=task_id, spine_phase=spine_phase,
                                   request_text="\n".join(_content_text(t) for t in texts))
        return list(outcome.get("embeddings") or [])

    # ── internals ────────────────────────────────────────────────────────
    def _embed_gateway(self) -> Any:
        """Lazy W8 gateway bound to the engine's own PiModelManager."""
        if self._embeddings_gateway is None:
            from app.core.pi_runtime.embeddings_gateway import EmbeddingsGateway

            self._embeddings_gateway = EmbeddingsGateway(manager=self._pi.model_manager())
        return self._embeddings_gateway

    def steering_binding(self, *, agent_id: str, project_id: str,
                         session_key: str | None = None) -> Any:
        """Build a Pi steering binding for one governed turn (W3 L10).

        Engine-neutral: the legacy path ignores it, the Pi path wires the
        turn's steer/follow-up/abort queues through it (H-5).
        """
        return self._pi.steering_binding(agent_id=agent_id, project_id=project_id,
                                         session_key=session_key)

    async def _record_outcome(self, *, engine: str, purpose: str, project_id: str, agent_id: str,
                              params: TurnParams, started: float, outcome: dict[str, Any],
                              task_id: str | None, spine_phase: str | None,
                              session_id: str | None = None, request_text: str = "") -> None:
        await record_agentic_usage(engine=engine, purpose=purpose, project_id=project_id, agent_id=agent_id,
                                   outcome=outcome,
                                   # Phase 6 provenance: the serving model wins when the
                                   # bridge resolved it (params may carry no selection).
                                   model=outcome.get("model") or params.model, started_at=started,
                                   session_id=session_id, task_id=task_id, spine_phase=spine_phase,
                                   request_text=request_text,
                                   response_text=_content_text(outcome.get("text")))

    async def _record_failure(self, *, engine: str, purpose: str, project_id: str, agent_id: str,
                              params: TurnParams, started: float, task_id: str | None,
                              spine_phase: str | None, session_id: str | None = None,
                              exc: Exception = RuntimeError("unknown")) -> None:
        # Exception paths (endpoint-resolution failure, unbound or raising
        # legacy executor, worker crashes) still produce their one row: zeroed
        # exact accounting with outcome=error and the exception type preserved.
        await record_agentic_usage(engine=engine, purpose=purpose, project_id=project_id, agent_id=agent_id,
                                   outcome={"status": "error"}, model=params.model, started_at=started,
                                   session_id=session_id, task_id=task_id, spine_phase=spine_phase,
                                   error_type=type(exc).__name__)

    async def _collect_pi_stream(self, *, purpose: str, project_id: str, agent_id: str,
                                 session_key: str | None, system_prompt: str,
                                 messages: list[dict[str, Any]], user_text: str,
                                 tool_executor: Any, tool_names: list[str] | None,
                                 params: TurnParams, stream_cb: Any, steering_binding: Any) -> dict[str, Any]:
        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []
        terminal: dict[str, Any] | None = None
        async for event in self._pi.run_chat_turn(
            project_id=project_id, agent_id=agent_id, system_prompt=system_prompt, history=messages,
            user_text=user_text, tool_executor=tool_executor or _no_tool_executor, session_key=session_key,
            endpoint_id=params.endpoint_id or DEFAULT_ENDPOINT_ID, allowed_tools=tool_names,
            steering=steering_binding, params=params,
        ):
            if stream_cb is not None:
                maybe = stream_cb(event)
                if hasattr(maybe, "__await__"):
                    await maybe
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
            "error": (terminal or {}).get("error") if status not in ("success", "aborted") else None,
        }

    async def _legacy_outcome(self, verb: str, **kwargs: Any) -> dict[str, Any]:
        if self._legacy is None:
            raise AgenticDispatchError(f"legacy_engine_not_bound:{verb}")
        return await self._legacy(verb=verb, **kwargs)


async def _no_tool_executor(name: str, args: dict[str, Any], project_id: str, agent_id: str) -> dict[str, Any]:
    return {"ok": False, "error": "tool_not_allowed"}


# Module singleton, mirroring the ollama/llm_router idiom (master plan §5.1):
# Pi through the real PiExecutionService, legacy through the real legacy plane.
agentic = AgenticDispatcher()
