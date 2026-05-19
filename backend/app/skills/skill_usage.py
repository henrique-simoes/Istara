"""Usage and health mixin for the skill manager."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from app.core.checkpoint import atomic_write

logger = logging.getLogger(__name__)


class SkillUsageMixin:
    def _empty_usage_stats(self) -> dict:
        return {
            "executions": 0,
            "successes": 0,
            "failures": 0,
            "total_quality": 0.0,
            "utility_score": 0.5,
            "last_used": None,
        }

    def _update_usage_stats(self, stats: dict, success: bool, quality_score: float) -> None:
        stats.setdefault("executions", 0)
        stats.setdefault("successes", 0)
        stats.setdefault("failures", 0)
        stats.setdefault("total_quality", 0.0)
        stats.setdefault("utility_score", 0.5)
        stats["executions"] += 1
        if success:
            stats["successes"] += 1
            stats["utility_score"] = stats.get("utility_score", 0.5) * 0.9 + 0.1
        else:
            stats["failures"] += 1
            stats["utility_score"] = stats.get("utility_score", 0.5) * 0.9
        stats["total_quality"] += quality_score
        stats["last_used"] = datetime.now(timezone.utc).isoformat()

    def _usage_stats_with_rates(self, stats: dict) -> dict:
        result = dict(stats)
        executions = result.get("executions", 0)
        if executions > 0:
            result["avg_quality"] = result.get("total_quality", 0.0) / executions
            result["success_rate"] = result.get("successes", 0) / executions
        result.setdefault("utility_score", 0.5)
        return result

    def record_execution(
        self,
        skill_name: str,
        success: bool,
        quality_score: float = 0.0,
        project_id: str | None = None,
    ) -> None:
        """Record a skill execution for usage tracking."""
        from app.core.autoresearch_isolation import is_autoresearch_active

        if is_autoresearch_active():
            return
        stats = self._usage_stats.setdefault(skill_name, self._empty_usage_stats())
        self._update_usage_stats(stats, success, quality_score)

        scoped_project_id = str(project_id or "").strip()
        scoped_stats = None
        if scoped_project_id:
            projects = stats.setdefault("projects", {})
            scoped_stats = projects.setdefault(scoped_project_id, self._empty_usage_stats())
            self._update_usage_stats(scoped_stats, success, quality_score)

        self._save_stats()
        if stats["executions"] >= 10 and stats["utility_score"] < 0.3:
            self._notify_low_utility_skill(
                skill_name,
                stats,
                allow_lifecycle_change=True,
            )
        if scoped_project_id and scoped_stats and scoped_stats["executions"] >= 10 and scoped_stats["utility_score"] < 0.3:
            self._notify_low_utility_skill(
                skill_name,
                scoped_stats,
                project_id=scoped_project_id,
            )

    def _notify_low_utility_skill(
        self,
        skill_name: str,
        stats: dict,
        project_id: str | None = None,
        *,
        allow_lifecycle_change: bool = False,
    ) -> None:
        try:
            import asyncio
            from app.api.websocket import broadcast_suggestion

            if allow_lifecycle_change and stats["utility_score"] < 0.2:
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
                scoped_project_id = str(project_id or "").strip()
                if scoped_project_id:
                    asyncio.ensure_future(broadcast_suggestion(message, scoped_project_id))
        except Exception:
            pass

    def get_usage_stats(self, skill_name: str | None = None, project_id: str | None = None) -> dict:
        """Get usage statistics for one or all skills."""
        scoped_project_id = str(project_id or "").strip()
        if skill_name:
            aggregate = self._usage_stats.get(skill_name, {})
            stats = aggregate
            if scoped_project_id:
                stats = (aggregate.get("projects") or {}).get(scoped_project_id, {})
            return self._usage_stats_with_rates(stats)
        if scoped_project_id:
            project_stats: dict[str, dict] = {}
            for name, aggregate in self._usage_stats.items():
                scoped = (aggregate.get("projects") or {}).get(scoped_project_id)
                if scoped:
                    project_stats[name] = self._usage_stats_with_rates(scoped)
            return project_stats
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
