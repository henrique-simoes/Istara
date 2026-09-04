"""Metrics API — quantitative research data for the dashboard."""

import math

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_project_access
from app.core.adaptive_validation import _sample_confidence_weight
from app.models.database import get_db
from app.models.finding import Nugget, Fact, Insight, Recommendation
from app.models.task import Task, TaskStatus
from app.models.message import Message
from app.models.method_metric import MethodMetric

router = APIRouter()


def _wilson_interval(success_count: int, total_runs: int, z: float = 1.96) -> tuple[float, float]:
    """Return a conservative Wilson score interval for a binomial success rate."""
    if total_runs <= 0:
        return 0.0, 0.0
    phat = success_count / total_runs
    z2 = z * z
    denominator = 1 + z2 / total_runs
    center = (phat + z2 / (2 * total_runs)) / denominator
    margin = z * math.sqrt((phat * (1 - phat) + z2 / (4 * total_runs)) / total_runs) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)


def _aggregate_method_metrics(method_stats: list[MethodMetric]) -> list[dict]:
    grouped: dict[str, dict] = {}
    for metric in method_stats:
        total_runs = max(
            int(metric.total_runs or 0),
            int(metric.success_count or 0) + int(metric.fail_count or 0),
        )
        row = grouped.setdefault(
            metric.method,
            {
                "method": metric.method,
                "contexts": set(),
                "total_runs": 0,
                "success_count": 0,
                "fail_count": 0,
                "weighted_consensus_sum": 0.0,
                "weighted_weight_sum": 0.0,
                "last_used": None,
            },
        )
        if metric.skill_name or metric.agent_id:
            row["contexts"].add((metric.skill_name or "", metric.agent_id or ""))
        row["total_runs"] += total_runs
        row["success_count"] += int(metric.success_count or 0)
        row["fail_count"] += int(metric.fail_count or 0)
        row["weighted_consensus_sum"] += float(metric.avg_consensus_score or 0.0) * total_runs
        row["weighted_weight_sum"] += float(metric.weight or 0.0) * max(total_runs, 1)
        if metric.last_used and (row["last_used"] is None or metric.last_used > row["last_used"]):
            row["last_used"] = metric.last_used

    rows = []
    for method, row in grouped.items():
        total_runs = row["total_runs"]
        success_count = row["success_count"]
        ci_low, ci_high = _wilson_interval(success_count, total_runs)
        sample_confidence = _sample_confidence_weight(total_runs)
        rows.append(
            {
                "method": method,
                "skill_name": "",
                "agent_id": "",
                "context_count": len(row["contexts"]),
                "total_runs": total_runs,
                "success_count": success_count,
                "fail_count": row["fail_count"],
                "avg_consensus_score": round(row["weighted_consensus_sum"] / total_runs, 3)
                if total_runs
                else 0.0,
                "success_rate": round(success_count / total_runs, 3) if total_runs else 0.0,
                "success_rate_ci_low": round(ci_low, 3),
                "success_rate_ci_high": round(ci_high, 3),
                "sample_confidence_weight": round(sample_confidence, 3),
                "rigor_status": "stable_sample" if total_runs >= 5 else "insufficient_sample",
                "last_used": row["last_used"].isoformat() if row["last_used"] else None,
                "weight": round(row["weighted_weight_sum"] / max(total_runs, 1), 3),
            }
        )

    return sorted(rows, key=lambda r: (-r["total_runs"], r["method"]))


@router.get("/metrics/{project_id}")
async def get_project_metrics(
    project_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Get quantitative metrics for a project's research progress."""
    await require_project_access(db, request, project_id, min_role="viewer")

    nugget_count = (
        await db.execute(select(func.count(Nugget.id)).where(Nugget.project_id == project_id))
    ).scalar() or 0
    fact_count = (
        await db.execute(select(func.count(Fact.id)).where(Fact.project_id == project_id))
    ).scalar() or 0
    insight_count = (
        await db.execute(select(func.count(Insight.id)).where(Insight.project_id == project_id))
    ).scalar() or 0
    rec_count = (
        await db.execute(
            select(func.count(Recommendation.id)).where(Recommendation.project_id == project_id)
        )
    ).scalar() or 0

    total_tasks = (
        await db.execute(select(func.count(Task.id)).where(Task.project_id == project_id))
    ).scalar() or 0
    done_tasks = (
        await db.execute(
            select(func.count(Task.id)).where(
                Task.project_id == project_id, Task.status == TaskStatus.DONE
            )
        )
    ).scalar() or 0
    in_progress = (
        await db.execute(
            select(func.count(Task.id)).where(
                Task.project_id == project_id, Task.status == TaskStatus.IN_PROGRESS
            )
        )
    ).scalar() or 0

    msg_count = (
        await db.execute(select(func.count(Message.id)).where(Message.project_id == project_id))
    ).scalar() or 0

    avg_confidence_result = await db.execute(
        select(func.avg(Insight.confidence)).where(Insight.project_id == project_id)
    )
    avg_confidence = avg_confidence_result.scalar() or 0

    phases = {}
    for phase in ["discover", "define", "develop", "deliver"]:
        n = (
            await db.execute(
                select(func.count(Nugget.id)).where(
                    Nugget.project_id == project_id, Nugget.phase == phase
                )
            )
        ).scalar() or 0
        f = (
            await db.execute(
                select(func.count(Fact.id)).where(
                    Fact.project_id == project_id, Fact.phase == phase
                )
            )
        ).scalar() or 0
        i = (
            await db.execute(
                select(func.count(Insight.id)).where(
                    Insight.project_id == project_id, Insight.phase == phase
                )
            )
        ).scalar() or 0
        r = (
            await db.execute(
                select(func.count(Recommendation.id)).where(
                    Recommendation.project_id == project_id, Recommendation.phase == phase
                )
            )
        ).scalar() or 0
        phases[phase] = {
            "nuggets": n,
            "facts": f,
            "insights": i,
            "recommendations": r,
            "total": n + f + i + r,
        }

    task_completion_rate = round(done_tasks / max(total_tasks, 1) * 100, 1)

    return {
        "project_id": project_id,
        "findings": {
            "nuggets": nugget_count,
            "facts": fact_count,
            "insights": insight_count,
            "recommendations": rec_count,
            "total": nugget_count + fact_count + insight_count + rec_count,
        },
        "tasks": {
            "total": total_tasks,
            "done": done_tasks,
            "in_progress": in_progress,
            "completion_rate": task_completion_rate,
        },
        "quality": {
            "avg_confidence": round(avg_confidence, 2),
            "messages": msg_count,
        },
        "by_phase": phases,
    }


@router.get("/metrics/{project_id}/validation")
async def get_validation_metrics(
    project_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Get validation and consensus metrics for a project.

    Returns per-method adaptive validation stats from MethodMetric,
    plus per-task validation_method and consensus_score for completed tasks.
    """
    await require_project_access(db, request, project_id, min_role="viewer")

    VALIDATION_METHODS = [
        {
            "id": "self_moa",
            "name": "Self-MoA",
            "description": "Same model, temperature variation (Li et al., 2025)",
        },
        {"id": "dual_run", "name": "Dual Run", "description": "Two models, same prompt comparison"},
        {
            "id": "adversarial_review",
            "name": "Adversarial Review",
            "description": "One model critiques another (Du et al., 2024)",
        },
        {
            "id": "full_ensemble",
            "name": "Full Ensemble",
            "description": "3+ models with composite agreement and categorical kappa when labels exist",
        },
        {
            "id": "debate_rounds",
            "name": "Debate Rounds",
            "description": "Iterative refinement between models (Du et al., 2024)",
        },
    ]

    method_stats = (
        (
            await db.execute(
                select(MethodMetric)
                .where(MethodMetric.project_id == project_id)
                .order_by(MethodMetric.method, MethodMetric.last_used.desc())
            )
        )
        .scalars()
        .all()
    )

    aggregated_method_stats = _aggregate_method_metrics(method_stats)

    validated_tasks = (
        (
            await db.execute(
                select(Task)
                .where(Task.project_id == project_id, Task.validation_method.isnot(None))
                .order_by(Task.updated_at.desc())
                .limit(50)
            )
        )
        .scalars()
        .all()
    )

    recent_validations = [
        {
            "task_id": t.id,
            "task_title": t.title,
            "skill_name": t.skill_name,
            "validation_method": t.validation_method,
            "consensus_score": round(t.consensus_score, 3) if t.consensus_score else None,
            "status": t.status.value if hasattr(t.status, "value") else str(t.status),
            "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        }
        for t in validated_tasks
    ]

    return {
        "project_id": project_id,
        "methods": VALIDATION_METHODS,
        "method_stats": aggregated_method_stats,
        "recent_validations": recent_validations,
        "confidence_thresholds": {
            "nugget": 0.70,
            "fact": 0.65,
            "insight": 0.55,
            "recommendation": 0.50,
        },
        "statistical_notes": {
            "agreement_score": "Consensus score is a composite agreement signal; kappa is included only when categorical labels can be extracted.",
            "success_rate": "Success rates aggregate all method contexts and include Wilson 95% confidence intervals.",
            "sample_weighting": "Adaptive selection down-weights methods with fewer than five observed runs.",
        },
    }


@router.get("/metrics/{project_id}/model-intelligence")
async def get_model_intelligence(
    project_id: str,
    request: Request,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Get model intelligence data: leaderboard, error taxonomy, tool success, latency.

    Aggregates data from ModelSkillStats (production + autoresearch) and
    TelemetrySpan (operational traces) to help users choose the best models
    for each skill and understand error patterns.
    """
    await require_project_access(db, request, project_id, min_role="viewer")

    from app.core.telemetry import telemetry_recorder

    return await telemetry_recorder.get_model_intelligence(project_id, limit=limit)
