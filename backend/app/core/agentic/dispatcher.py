"""Engine selection and common accounting for agentic invocations.

No product call site uses this in W1; later migration waves are required to
enter through here so Pi and legacy paths share a measurable seam.
"""

from __future__ import annotations

import time
from typing import Any, Awaitable, Callable

from app.config import settings
from app.core.pi_replacement import PI_ENGINE_VALUES
from app.core.pi_runtime.engine import PiExecutionService

from .types import AgenticDispatchError, EngineChoice, StructuredResult, TurnParams, TurnResult
from .usage_ledger import record_agentic_usage

LegacyExecutor = Callable[..., Awaitable[dict[str, Any]]]


class AgenticDispatcher:
    def __init__(self, *, pi_service: PiExecutionService | None = None, legacy_executor: LegacyExecutor | None = None) -> None:
        self._pi = pi_service or PiExecutionService()
        self._legacy = legacy_executor

    def resolve_engine(self, *, engine: EngineChoice | None = None, request_engine: str | None = None,
                       project_engine: str | None = None) -> EngineChoice:
        if engine is not None:
            return engine
        candidate = (request_engine or project_engine or getattr(settings, "agentic_engine_default", "legacy")).lower()
        return "pi" if candidate in PI_ENGINE_VALUES else "legacy"

    async def completion(self, *, purpose: str, project_id: str, system: str | None,
                         messages: list[dict[str, Any]], params: TurnParams, agent_id: str = "istara-main",
                         engine: EngineChoice | None = None) -> TurnResult:
        started = time.perf_counter()
        selected = self.resolve_engine(engine=engine)
        if selected == "pi":
            outcome = await self._pi.run_completion(purpose=purpose, project_id=project_id, agent_id=agent_id,
                                                    system=system or "", messages=messages, params=params)
        else:
            outcome = await self._legacy_outcome("completion", purpose=purpose, project_id=project_id,
                                                 agent_id=agent_id, system=system, messages=messages, params=params)
        await record_agentic_usage(engine=selected, purpose=purpose, project_id=project_id, agent_id=agent_id,
                                   outcome=outcome, model=params.model, started_at=started)
        return TurnResult(text=outcome.get("text", ""), usage=outcome.get("usage") or {},
                          stop_reason=outcome.get("stop_reason"), endpoint_id=outcome.get("endpoint_id"),
                          status=outcome.get("status", "success"), tool_calls=outcome.get("tool_calls") or [])

    async def structured(self, *, purpose: str, project_id: str, system: str | None,
                         messages: list[dict[str, Any]], schema: dict[str, Any], params: TurnParams,
                         agent_id: str = "istara-main", engine: EngineChoice | None = None) -> StructuredResult:
        started = time.perf_counter()
        selected = self.resolve_engine(engine=engine)
        if selected == "pi":
            outcome = await self._pi.run_structured(purpose=purpose, project_id=project_id, agent_id=agent_id,
                                                    system=system or "", messages=messages, schema=schema, params=params)
        else:
            outcome = await self._legacy_outcome("structured", purpose=purpose, project_id=project_id, agent_id=agent_id,
                                                 system=system, messages=messages, schema=schema, params=params)
        await record_agentic_usage(engine=selected, purpose=purpose, project_id=project_id, agent_id=agent_id,
                                   outcome=outcome, model=params.model, started_at=started)
        return StructuredResult(text=outcome.get("text", ""), value=outcome.get("value") or {},
                                usage=outcome.get("usage") or {}, stop_reason=outcome.get("stop_reason"),
                                endpoint_id=outcome.get("endpoint_id"), status=outcome.get("status", "success"))

    async def react(self, *, purpose: str, project_id: str, agent_id: str, session_key: str | None,
                    system: str, messages: list[dict[str, Any]], user_text: str, tool_executor: Any,
                    tool_names: list[str], params: TurnParams, engine: EngineChoice | None = None) -> TurnResult:
        selected = self.resolve_engine(engine=engine)
        if selected != "pi":
            outcome = await self._legacy_outcome("react", purpose=purpose, project_id=project_id, agent_id=agent_id,
                                                 system=system, messages=messages, user_text=user_text, params=params)
        else:
            outcome = await self._pi.run_react(purpose=purpose, project_id=project_id, agent_id=agent_id,
                                               session_key=session_key, system=system, messages=messages,
                                               user_text=user_text, tool_executor=tool_executor, tool_names=tool_names, params=params)
        await record_agentic_usage(engine=selected, purpose=purpose, project_id=project_id, agent_id=agent_id,
                                   outcome=outcome, model=params.model)
        return TurnResult(text=outcome.get("text", ""), usage=outcome.get("usage") or {},
                          stop_reason=outcome.get("stop_reason"), endpoint_id=outcome.get("endpoint_id"),
                          status=outcome.get("status", "success"), tool_calls=outcome.get("tool_calls") or [])

    async def _legacy_outcome(self, verb: str, **kwargs: Any) -> dict[str, Any]:
        if self._legacy is None:
            raise AgenticDispatchError(f"legacy_engine_not_bound:{verb}")
        return await self._legacy(verb=verb, **kwargs)
