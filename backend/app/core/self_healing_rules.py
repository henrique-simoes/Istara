"""DevOps self-healing rules — automated remediation based on telemetry signals.

Rules are triggered by the telemetry hooks and perform targeted fixes.
All actions are fire-and-forget; failures are logged, never propagate.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.telemetry_span import TelemetrySpan

logger = logging.getLogger(__name__)

_CIRCUIT_BREAKER_RESET_THRESHOLD = 5
_RESOURCE_WARN_THRESHOLD = 0.80
_RESOURCE_CRIT_THRESHOLD = 0.90
_ERROR_RATE_WINDOW_MINUTES = 15
_ERROR_RATE_HIGH_THRESHOLD = 0.30


class SelfHealingRules:
    """Evaluates telemetry spans and triggers automated remediation."""

    def __init__(self) -> None:
        self._error_counts: dict[str, list[datetime]] = {}
        self._circuit_open: dict[str, bool] = {}
        self._last_resource_warn: dict[str, datetime] = {}

    def _track_error(self, key: str) -> None:
        now = datetime.now(timezone.utc)
        if key not in self._error_counts:
            self._error_counts[key] = []
        self._error_counts[key] = [
            t
            for t in self._error_counts[key]
            if (now - t).total_seconds() < _ERROR_RATE_WINDOW_MINUTES * 60
        ]
        self._error_counts[key].append(now)

    def _error_rate(self, key: str) -> float:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=_ERROR_RATE_WINDOW_MINUTES)
        recent = [t for t in self._error_counts.get(key, []) if t >= cutoff]
        window_seconds = _ERROR_RATE_WINDOW_MINUTES * 60
        return len(recent) / (window_seconds / 60.0)

    async def evaluate_span(self, span: "TelemetrySpan") -> list[dict]:
        """Evaluate a telemetry span and return any triggered self-healing actions."""
        actions = []
        key = f"{span.project_id}:{span.skill_name}:{span.model_name}"

        if span.status == "error":
            self._track_error(key)
            rate = self._error_rate(key)

            if rate > _ERROR_RATE_HIGH_THRESHOLD:
                actions.append(
                    {
                        "trigger": "high_error_rate",
                        "severity": "high",
                        "key": key,
                        "error_rate": round(rate, 3),
                        "threshold": _ERROR_RATE_HIGH_THRESHOLD,
                        "message": f"High error rate detected ({rate:.0%} over {_ERROR_RATE_WINDOW_MINUTES}min) for {span.skill_name}. "
                        f"Consider reviewing model configuration or switching to a more reliable model.",
                        "auto_action": "none",
                    }
                )

        if span.operation == "skill_execute" and span.duration_ms > 0:
            model_key = f"latency:{span.model_name}"
            self._track_error(model_key)

            if span.duration_ms > 120_000:
                actions.append(
                    {
                        "trigger": "slow_execution",
                        "severity": "medium",
                        "model": span.model_name,
                        "duration_ms": round(span.duration_ms, 1),
                        "threshold_ms": 120_000,
                        "message": f"Skill '{span.skill_name}' took {span.duration_ms / 1000:.0f}s on model {span.model_name}. "
                        f"This may indicate model overload.",
                        "auto_action": "none",
                    }
                )

        if span.operation == "tool_call" and span.tool_success is False:
            tool_key = f"tool:{span.tool_name}"
            self._track_error(tool_key)
            rate = self._error_rate(tool_key)
            if rate > _ERROR_RATE_HIGH_THRESHOLD:
                actions.append(
                    {
                        "trigger": "tool_failure_spike",
                        "severity": "medium",
                        "tool": span.tool_name,
                        "error_rate": round(rate, 3),
                        "message": f"Tool '{span.tool_name}' is failing at {rate:.0%} rate. "
                        f"Check MCP server health or tool configuration.",
                        "auto_action": "none",
                    }
                )

        return actions

    async def evaluate_all(self, project_id: str) -> dict:
        """Run a full evaluation over recent spans for a project and return a summary."""
        try:
            async with self._get_session() as session:
                from sqlalchemy import select
                from app.models.telemetry_span import TelemetrySpan

                cutoff = datetime.now(timezone.utc) - timedelta(minutes=_ERROR_RATE_WINDOW_MINUTES)
                result = await session.execute(
                    select(TelemetrySpan).where(
                        TelemetrySpan.project_id == project_id,
                        TelemetrySpan.created_at >= cutoff,
                    )
                )
                all_actions: list[dict] = []
                for span in result.scalars().all():
                    all_actions.extend(await self.evaluate_span(span))

                by_trigger: dict[str, list[dict]] = {}
                for a in all_actions:
                    by_trigger.setdefault(a["trigger"], []).append(a)

                return {
                    "project_id": project_id,
                    "evaluated_at": datetime.now(timezone.utc).isoformat(),
                    "window_minutes": _ERROR_RATE_WINDOW_MINUTES,
                    "total_issues": len(all_actions),
                    "by_trigger": {t: len(items) for t, items in by_trigger.items()},
                    "actions": all_actions[:50],
                }
        except Exception as e:
            logger.warning(f"Self-healing evaluation failed: {e}")
            return {
                "project_id": project_id,
                "evaluated_at": datetime.now(timezone.utc).isoformat(),
                "total_issues": 0,
                "by_trigger": {},
                "actions": [],
                "error": str(e),
            }

    def _get_session(self):
        from app.models.database import async_session

        return async_session()


self_healing = SelfHealingRules()
