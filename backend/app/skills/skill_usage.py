"""Usage and health mixin for the skill manager."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from app.core.checkpoint import atomic_write

logger = logging.getLogger(__name__)


class SkillUsageMixin:
    def record_execution(self, skill_name: str, success: bool, quality_score: float = 0.0) -> None:
        """Record a skill execution for usage tracking."""
        from app.core.autoresearch_isolation import is_autoresearch_active

        if is_autoresearch_active():
            return
        stats = self._usage_stats.setdefault(
            skill_name,
            {
                "executions": 0,
                "successes": 0,
                "failures": 0,
                "total_quality": 0.0,
                "utility_score": 0.5,
                "last_used": None,
            },
        )
        stats["executions"] += 1
        if success:
            stats["successes"] += 1
            stats["utility_score"] = stats.get("utility_score", 0.5) * 0.9 + 0.1
        else:
            stats["failures"] += 1
            stats["utility_score"] = stats.get("utility_score", 0.5) * 0.9
        stats["total_quality"] += quality_score
        stats["last_used"] = datetime.now(timezone.utc).isoformat()

        self._save_stats()
        if stats["executions"] >= 10 and stats["utility_score"] < 0.3:
            self._notify_low_utility_skill(skill_name, stats)

    def _notify_low_utility_skill(self, skill_name: str, stats: dict) -> None:
        try:
            import asyncio
            from app.api.websocket import broadcast_suggestion

            if stats["utility_score"] < 0.2:
                defn = self._definitions.get(skill_name)
                if defn:
                    self.update_skill(
                        skill_name,
                        {"lifecycle": "deprecated"},
                        "Auto-deprecated after chronically low utility",
                    )
                    logger.warning(
                        "Skill '%s' auto-deprecated (utility=%.2f after %s runs)",
                        skill_name,
                        stats["utility_score"],
                        stats["executions"],
                    )

            loop = asyncio.get_event_loop()
            if loop.is_running():
                message = (
                    f"Skill '{skill_name}' has low utility "
                    f"({stats['utility_score']:.0%} after {stats['executions']} runs). "
                    + (
                        "It has been auto-deprecated."
                        if stats["utility_score"] < 0.2
                        else "Consider reviewing or replacing it."
                    )
                )
                asyncio.ensure_future(broadcast_suggestion(message, ""))
        except Exception:
            pass

    def get_usage_stats(self, skill_name: str | None = None) -> dict:
        """Get usage statistics for one or all skills."""
        if skill_name:
            stats = self._usage_stats.get(skill_name, {})
            if stats and stats.get("executions", 0) > 0:
                stats["avg_quality"] = stats["total_quality"] / stats["executions"]
                stats["success_rate"] = stats["successes"] / stats["executions"]
            stats.setdefault("utility_score", 0.5)
            return stats
        return self._usage_stats

    def _save_stats(self) -> None:
        self.ensure_definitions_dir()
        atomic_write(self._stats_file, json.dumps(self._usage_stats, indent=2))

    def get_skill_health(self, name: str) -> dict:
        """Get health score for a skill."""
        defn = self._definitions.get(name)
        if not defn:
            return {"status": "not_found"}

        stats = self._usage_stats.get(name, {})
        executions = stats.get("executions", 0)
        success_rate = stats.get("successes", 0) / max(executions, 1)
        avg_quality = stats.get("total_quality", 0) / max(executions, 1)

        completeness = 1.0
        if not defn.data.get("plan_prompt"):
            completeness -= 0.2
        if not defn.data.get("execute_prompt"):
            completeness -= 0.3
        if not defn.data.get("output_schema"):
            completeness -= 0.2
        if not defn.data.get("description"):
            completeness -= 0.1
        if len(defn.data.get("execute_prompt", "")) < 100:
            completeness -= 0.1
        if len(defn.data.get("output_schema", "")) < 50:
            completeness -= 0.1

        health_score = (
            success_rate * 0.4 + avg_quality * 0.3 + completeness * 0.3
            if executions > 0
            else completeness * 0.3
        )
        return {
            "name": name,
            "version": defn.version,
            "enabled": defn.enabled,
            "executions": executions,
            "success_rate": round(success_rate, 2),
            "avg_quality": round(avg_quality, 2),
            "completeness": round(completeness, 2),
            "health_score": round(health_score, 2),
            "last_used": stats.get("last_used"),
            "pending_proposals": len(
                [p for p in self._proposals if p.skill_name == name and p.status == "pending"]
            ),
        }

    def get_all_health(self) -> list[dict]:
        """Get health scores for all skills."""
        return [self.get_skill_health(name) for name in self._definitions]
