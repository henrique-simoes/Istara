"""Agent Hooks — composable lifecycle hooks for the agent execution loop.

Provides 6 lifecycle events that allow telemetry, validation, and other
concerns to be added without modifying the agent loop directly.

All hooks are async and fire-and-forget (using asyncio.create_task).
If a hook fails, it is logged and ignored — never blocking the agent.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


class AgentHooks:
    """Composable lifecycle hooks for the agent execution loop.

    Events:
        pre_task: Before skill execution begins
        post_task: After skill execution, before validation
        post_validation: After validation, with consensus scores
        on_completion: After task is marked done
        on_error: When a skill or validation fails
    """

    def __init__(self) -> None:
        self._hooks: dict[str, list[Callable[..., Coroutine]]] = defaultdict(list)

    def register(self, event: str, callback: Callable[..., Coroutine]) -> None:
        """Register an async callback for a lifecycle event."""
        if event not in ("pre_task", "post_task", "post_validation", "on_completion", "on_error"):
            raise ValueError(
                f"Unknown hook event: {event}. Must be one of: pre_task, post_task, post_validation, on_completion, on_error"
            )
        self._hooks[event].append(callback)

    async def fire(self, event: str, context: dict[str, Any]) -> None:
        """Fire all registered callbacks for an event. Non-blocking."""
        callbacks = self._hooks.get(event, [])
        for callback in callbacks:
            try:
                asyncio.create_task(callback(context))
            except Exception as e:
                logger.warning(f"Hook {event}.{callback.__name__} failed: {e}")


# Global singleton
agent_hooks = AgentHooks()


def register_builtin_hooks() -> None:
    """Register built-in telemetry hooks on module import."""
    from app.config import settings
    from app.core.telemetry import telemetry_recorder

    async def _pre_task_hook(context: dict) -> None:
        """Record span at task start (opt-in)."""
        if not settings.telemetry_enabled:
            context["_start_time"] = time.monotonic()
            return
        context["_start_time"] = time.monotonic()
        await telemetry_recorder.record_span(
            trace_id=context.get("trace_id", uuid.uuid4().hex[:36]),
            operation="skill_execute",
            skill_name=context.get("skill_name", ""),
            model_name=context.get("model_name", ""),
            agent_id=context.get("agent_id", ""),
            project_id=context.get("project_id", ""),
            task_id=context.get("task_id"),
            temperature=context.get("temperature"),
            status="started",
            source="production",
        )

    async def _post_task_hook(context: dict) -> None:
        """Record span after skill execution, write ModelSkillStats (opt-in)."""
        if not settings.telemetry_enabled:
            return
        start = context.pop("_start_time", None)
        duration = (time.monotonic() - start) * 1000 if start else 0.0
        success = context.get("success", False)
        quality = context.get("quality_score")

        await telemetry_recorder.record_span(
            trace_id=context.get("trace_id", uuid.uuid4().hex[:36]),
            operation="skill_execute",
            skill_name=context.get("skill_name", ""),
            model_name=context.get("model_name", ""),
            agent_id=context.get("agent_id", ""),
            project_id=context.get("project_id", ""),
            task_id=context.get("task_id"),
            temperature=context.get("temperature"),
            duration_ms=duration,
            status="success" if success else "error",
            quality_score=quality,
            source="production",
        )

        await telemetry_recorder.record_model_performance(
            skill_name=context.get("skill_name", ""),
            model_name=context.get("model_name", ""),
            temperature=context.get("temperature", 0.7),
            quality=quality or 0.5,
            success=success,
        )

    async def _post_validation_hook(context: dict) -> None:
        """Record validation outcome span (opt-in)."""
        if not settings.telemetry_enabled:
            return
        await telemetry_recorder.record_span(
            trace_id=context.get("trace_id", uuid.uuid4().hex[:36]),
            operation="validation",
            skill_name=context.get("skill_name", ""),
            model_name=context.get("model_name", ""),
            agent_id=context.get("agent_id", ""),
            project_id=context.get("project_id", ""),
            task_id=context.get("task_id"),
            duration_ms=context.get("validation_duration_ms", 0),
            status="success" if context.get("validation_passed", False) else "degraded",
            consensus_score=context.get("consensus_score"),
            quality_score=context.get("validation_quality"),
            source="production",
        )

    async def _on_error_hook(context: dict) -> None:
        """Record error span (opt-in)."""
        if not settings.telemetry_enabled:
            return
        await telemetry_recorder.record_span(
            trace_id=context.get("trace_id", uuid.uuid4().hex[:36]),
            operation=context.get("operation", "skill_execute"),
            skill_name=context.get("skill_name", ""),
            model_name=context.get("model_name", ""),
            agent_id=context.get("agent_id", ""),
            project_id=context.get("project_id", ""),
            task_id=context.get("task_id"),
            status="error",
            error_type=context.get("error_type", "other"),
            error_message=str(context.get("error_message", ""))[:500],
            source="production",
        )

    async def _on_completion_hook(context: dict) -> None:
        """Record completion span (opt-in)."""
        if not settings.telemetry_enabled:
            return
        duration = context.get("total_duration_ms", 0)
        await telemetry_recorder.record_span(
            trace_id=context.get("trace_id", uuid.uuid4().hex[:36]),
            operation="skill_execute",
            skill_name=context.get("skill_name", ""),
            model_name=context.get("model_name", ""),
            agent_id=context.get("agent_id", ""),
            project_id=context.get("project_id", ""),
            task_id=context.get("task_id"),
            duration_ms=duration,
            status="success",
            quality_score=context.get("final_quality"),
            source="production",
        )

    agent_hooks.register("pre_task", _pre_task_hook)
    agent_hooks.register("post_task", _post_task_hook)
    agent_hooks.register("post_validation", _post_validation_hook)
    agent_hooks.register("on_error", _on_error_hook)
    agent_hooks.register("on_completion", _on_completion_hook)
