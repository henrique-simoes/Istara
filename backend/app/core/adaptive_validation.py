"""Adaptive Validation — chooses a validation method per context.

The choice is constrained by the project's assurance mode (``app.core.assurance``) and learns only
from human-verified outcomes: whether a method's verdict matched the researcher's task review
(Thompson sampling over those counts). Run counts and mean consensus are still recorded for
Ensemble Health, but self-agreement never rewards a method (AV-1).
"""

import inspect
import logging
import math
import random
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from app.core.assurance import thompson_choice
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
            str(identity).strip().casefold() for identity in identities if str(identity).strip()
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
        self,
        project_id: str,
        skill_name: str = "",
        agent_id: str = "",
        *,
        allowed: Sequence[str] | None = None,
        rng: random.Random | None = None,
    ) -> str:
        """Choose a validation method among those the project's assurance mode allows.

        Learning uses only human-verified outcomes (did the method's verdict match the researcher's
        review?), via Thompson sampling. Self-agreement between samples is never a reward (AV-1):
        copies of one model agree most and would always win. Without human outcomes the choice is
        the compute-aware default, as before assurance modes existed.
        """
        choices = [m for m in (allowed or AVAILABLE_METHODS) if m in AVAILABLE_METHODS]
        if not choices:
            return DEFAULT_METHOD
        if len(choices) == 1:
            return choices[0]
        counts = await self._human_counts(project_id, skill_name, agent_id)
        learned = thompson_choice(choices, counts, rng or random.Random())
        if learned is not None:
            logger.debug("Adaptive: %s from human-verified outcomes %s", learned, counts)
            return learned
        compute_default = await _compute_aware_default_method(project_id)
        if compute_default in choices:
            return compute_default
        return DEFAULT_METHOD if DEFAULT_METHOD in choices else choices[0]

    async def _human_counts(
        self, project_id: str, skill_name: str, agent_id: str
    ) -> dict[str, tuple[int, int]]:
        """(agree, disagree) per method for this context, else for the whole project."""
        try:
            from sqlalchemy import select

            from app.models.method_metric import MethodMetric

            async with async_session() as db:
                query = select(MethodMetric).where(MethodMetric.project_id == project_id)
                scoped = query
                if skill_name:
                    scoped = scoped.where(MethodMetric.skill_name == skill_name)
                if agent_id:
                    scoped = scoped.where(MethodMetric.agent_id == agent_id)
                rows = (await db.execute(scoped)).scalars().all()
                scoped_has_outcomes = any(
                    (r.human_agree_count or 0) + (r.human_disagree_count or 0) for r in rows
                )
                if not scoped_has_outcomes:
                    rows = (await db.execute(query)).scalars().all()
        except Exception as exc:
            logger.warning("Adaptive human-outcome lookup failed: %s", exc)
            return {}
        counts: dict[str, tuple[int, int]] = {}
        for row in rows:
            agree, disagree = counts.get(row.method, (0, 0))
            counts[row.method] = (
                agree + (row.human_agree_count or 0),
                disagree + (row.human_disagree_count or 0),
            )
        return {method: c for method, c in counts.items() if sum(c) > 0}

    async def record_human_outcome(
        self,
        project_id: str,
        skill_name: str,
        agent_id: str,
        method: str,
        agreed: bool,
    ) -> None:
        """Record whether a method's verdict matched the researcher's review (AV-1 signal)."""
        if method not in AVAILABLE_METHODS:
            return
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
                if metric is None:
                    metric = MethodMetric(
                        id=str(uuid.uuid4()),
                        project_id=project_id,
                        skill_name=skill_name,
                        agent_id=agent_id,
                        method=method,
                        total_runs=0,
                        human_agree_count=0,
                        human_disagree_count=0,
                    )
                    db.add(metric)
                if agreed:
                    metric.human_agree_count = (metric.human_agree_count or 0) + 1
                else:
                    metric.human_disagree_count = (metric.human_disagree_count or 0) + 1
                await db.commit()
        except Exception as exc:
            logger.warning("Failed to record human-verified validation outcome: %s", exc)

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
                        metric.avg_consensus_score * (metric.total_runs - 1) + consensus_score
                    ) / metric.total_runs
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
                        "human_agree_count": m.human_agree_count or 0,
                        "human_disagree_count": m.human_disagree_count or 0,
                    }
                    for m in metrics
                ]
        except Exception:
            return []


# Singleton
adaptive_selector = AdaptiveSelector()
