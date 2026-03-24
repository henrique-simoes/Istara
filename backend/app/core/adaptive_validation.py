"""Adaptive Validation — learns the best validation method per context.

Tracks method performance per project/skill/agent combination and uses
weighted scoring with exponential decay (recency bias, half-life 30 days)
to recommend the most effective validation strategy.
"""

import logging
import math
import time
import uuid
from datetime import datetime, timezone

from app.models.database import async_session

logger = logging.getLogger(__name__)

AVAILABLE_METHODS = ["self_moa", "dual_run", "adversarial_review", "full_ensemble", "debate_rounds"]
DEFAULT_METHOD = "self_moa"
HALF_LIFE_DAYS = 30


def _recency_weight(last_used: datetime) -> float:
    """Exponential decay weight based on recency (half-life = 30 days)."""
    days_ago = (datetime.now(timezone.utc) - last_used).total_seconds() / 86400
    return math.exp(-0.693 * days_ago / HALF_LIFE_DAYS)


class AdaptiveSelector:
    """Selects the best validation method based on historical performance."""

    async def select_method(
        self, project_id: str, skill_name: str = "", agent_id: str = ""
    ) -> str:
        """Select the best validation method for the given context."""
        try:
            from app.models.method_metric import MethodMetric
            from sqlalchemy import select

            async with async_session() as db:
                # Query metrics for this context (project + skill + agent)
                query = select(MethodMetric).where(
                    MethodMetric.project_id == project_id,
                )
                if skill_name:
                    query = query.where(MethodMetric.skill_name == skill_name)
                if agent_id:
                    query = query.where(MethodMetric.agent_id == agent_id)

                result = await db.execute(query)
                metrics = result.scalars().all()

                if not metrics:
                    # No history — fall back to project-level metrics
                    result = await db.execute(
                        select(MethodMetric).where(
                            MethodMetric.project_id == project_id,
                            MethodMetric.total_runs > 0,
                        )
                    )
                    metrics = result.scalars().all()

                if not metrics:
                    return DEFAULT_METHOD

                # Score each method with recency-weighted success rate
                method_scores: dict[str, float] = {}
                for m in metrics:
                    if m.total_runs == 0:
                        continue
                    success_rate = m.success_count / m.total_runs
                    recency = _recency_weight(m.last_used)
                    score = (success_rate * 0.5 + m.avg_consensus_score * 0.5) * recency * m.weight
                    if m.method in method_scores:
                        method_scores[m.method] = max(method_scores[m.method], score)
                    else:
                        method_scores[m.method] = score

                if not method_scores:
                    return DEFAULT_METHOD

                best = max(method_scores, key=method_scores.get)
                logger.debug(
                    f"Adaptive: selected '{best}' for project={project_id} "
                    f"skill={skill_name} (scores: {method_scores})"
                )
                return best

        except Exception as e:
            logger.warning(f"Adaptive selection failed: {e}")
            return DEFAULT_METHOD

    async def record_outcome(
        self,
        project_id: str,
        skill_name: str,
        agent_id: str,
        method: str,
        consensus_score: float,
        success: bool,
    ) -> None:
        """Record the outcome of a validation run for future learning."""
        try:
            from app.models.method_metric import MethodMetric
            from sqlalchemy import select

            async with async_session() as db:
                result = await db.execute(
                    select(MethodMetric).where(
                        MethodMetric.project_id == project_id,
                        MethodMetric.skill_name == skill_name,
                        MethodMetric.agent_id == agent_id,
                        MethodMetric.method == method,
                    )
                )
                metric = result.scalars().first()

                if metric:
                    # Update existing
                    metric.total_runs += 1
                    if success:
                        metric.success_count += 1
                    else:
                        metric.fail_count += 1
                    # Running average of consensus score
                    metric.avg_consensus_score = (
                        (metric.avg_consensus_score * (metric.total_runs - 1) + consensus_score)
                        / metric.total_runs
                    )
                    metric.last_used = datetime.now(timezone.utc)
                else:
                    # Create new
                    metric = MethodMetric(
                        id=str(uuid.uuid4()),
                        project_id=project_id,
                        skill_name=skill_name,
                        agent_id=agent_id,
                        method=method,
                        success_count=1 if success else 0,
                        fail_count=0 if success else 1,
                        avg_consensus_score=consensus_score,
                        total_runs=1,
                        weight=1.0,
                    )
                    db.add(metric)

                await db.commit()

        except Exception as e:
            logger.warning(f"Failed to record adaptive outcome: {e}")

    async def get_stats(self, project_id: str) -> list[dict]:
        """Get adaptive learning stats for a project."""
        try:
            from app.models.method_metric import MethodMetric
            from sqlalchemy import select

            async with async_session() as db:
                result = await db.execute(
                    select(MethodMetric).where(MethodMetric.project_id == project_id)
                )
                metrics = result.scalars().all()

                return [
                    {
                        "method": m.method,
                        "skill_name": m.skill_name,
                        "agent_id": m.agent_id,
                        "total_runs": m.total_runs,
                        "success_rate": m.success_count / m.total_runs if m.total_runs > 0 else 0,
                        "avg_consensus_score": round(m.avg_consensus_score, 4),
                        "last_used": m.last_used.isoformat(),
                        "recency_weight": round(_recency_weight(m.last_used), 4),
                    }
                    for m in metrics
                ]
        except Exception:
            return []


# Singleton
adaptive_selector = AdaptiveSelector()
