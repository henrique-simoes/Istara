"""Adaptive Validation — learns the best validation method per context.

Tracks method performance per project/skill/agent combination and uses
weighted scoring with exponential decay (recency bias, half-life 30 days)
to recommend the most effective validation strategy.
"""

import inspect
import logging
import math
import uuid
from datetime import UTC, datetime

from app.models.database import async_session

logger = logging.getLogger(__name__)

AVAILABLE_METHODS = ["self_moa", "dual_run", "adversarial_review", "full_ensemble", "debate_rounds"]
DEFAULT_METHOD = "self_moa"
HALF_LIFE_DAYS = 30


async def _pi_model_identities(project_id: str | None) -> set[str]:
    """Read the project-scoped Pi catalog without resolving provider secrets."""
    try:
        from app.core.agentic import agentic

        manager = agentic.model_manager()
        ensure_projection = getattr(manager, "ensure_db_projection", None)
        if callable(ensure_projection):
            result = ensure_projection()
            if inspect.isawaitable(result):
                await result
        identities = manager.available_model_identities(project_id=project_id)
        return {
            str(identity).strip().casefold()
            for identity in identities
            if str(identity).strip()
        }
    except Exception as exc:
        logger.debug("Adaptive validation Pi catalog lookup failed: %s", exc)
        return set()


async def _compute_aware_default_method(project_id: str | None) -> str:
    """Choose the natural validation method from currently available compute.

    Istara's architecture treats Self-MoA as the constrained fallback. When the
    project has multiple project-admitted Pi model identities, validation should
    use the multi-model path without a benchmark or caller forcing a specific
    node.  The catalog is identity-only here; provider secrets are materialized
    later by the dispatcher during the governed call.
    """
    distinct_models = await _pi_model_identities(project_id)

    if len(distinct_models) >= 3:
        return "full_ensemble"
    if len(distinct_models) >= 2:
        return "dual_run"
    return DEFAULT_METHOD


def _recency_weight(last_used: datetime) -> float:
    """Exponential decay weight based on recency (half-life = 30 days)."""
    from app.core.datetime_utils import ensure_utc
    days_ago = (datetime.now(UTC) - ensure_utc(last_used)).total_seconds() / 86400
    return math.exp(-0.693 * days_ago / HALF_LIFE_DAYS)


def _sample_confidence_weight(total_runs: int) -> float:
    """Conservatively down-weight methods with little evidence."""
    if total_runs <= 0:
        return 0.0
    return min(1.0, math.sqrt(total_runs / 5))


class AdaptiveSelector:
    """Selects the best validation method based on historical performance."""

    async def select_method(
        self, project_id: str, skill_name: str = "", agent_id: str = ""
    ) -> str:
        """Select the best validation method for the given context."""
        compute_default = await _compute_aware_default_method(project_id)
        if compute_default != DEFAULT_METHOD:
            logger.debug(
                "Adaptive: selected '%s' from the project-scoped Pi catalog for project=%s",
                compute_default,
                project_id,
            )
            return compute_default

        try:
            from sqlalchemy import select

            from app.models.method_metric import MethodMetric

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
                    sample_confidence = _sample_confidence_weight(m.total_runs)
                    score = (
                        (success_rate * 0.5 + m.avg_consensus_score * 0.5)
                        * recency
                        * m.weight
                        * sample_confidence
                    )
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
            from sqlalchemy import select

            from app.models.method_metric import MethodMetric

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
                    metric.last_used = datetime.now(UTC)
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
            try:
                from app.core.improvement_governance import improvement_governance

                await improvement_governance.record_feature_evidence(
                    feature="ensemble_model_and_llm_orchestration",
                    source_system="adaptive_validation",
                    source_id=f"{project_id}:{skill_name}:{agent_id}:{method}",
                    project_id=project_id,
                    agent_id=agent_id,
                    summary="Adaptive ensemble validation outcome recorded.",
                    evidence={
                        "passed": success,
                        "method": method,
                        "skill_name": skill_name,
                        "consensus_score": consensus_score,
                    },
                    metrics_after={
                        "consensus_score": consensus_score,
                        "success": success,
                    },
                    confidence=max(0.0, min(1.0, float(consensus_score))),
                )
            except Exception:
                pass

        except Exception as e:
            logger.warning(f"Failed to record adaptive outcome: {e}")

    async def get_stats(self, project_id: str) -> list[dict]:
        """Get adaptive learning stats for a project."""
        try:
            from sqlalchemy import select

            from app.models.method_metric import MethodMetric

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
                        "sample_confidence_weight": round(
                            _sample_confidence_weight(m.total_runs), 4
                        ),
                    }
                    for m in metrics
                ]
        except Exception:
            return []


# Singleton
adaptive_selector = AdaptiveSelector()
