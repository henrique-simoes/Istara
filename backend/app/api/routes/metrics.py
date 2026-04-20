"""Metrics API — quantitative research data for the dashboard."""

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.finding import Nugget, Fact, Insight, Recommendation
from app.models.task import Task, TaskStatus
from app.models.message import Message
from app.models.method_metric import MethodMetric

router = APIRouter()


@router.get("/metrics/{project_id}")
async def get_project_metrics(project_id: str, db: AsyncSession = Depends(get_db)):
    """Get quantitative metrics for a project's research progress."""

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
                    Recommendation.id == project_id, Recommendation.phase == phase
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
async def get_validation_metrics(project_id: str, db: AsyncSession = Depends(get_db)):
    """Get validation and consensus metrics for a project.

    Returns per-method adaptive validation stats from MethodMetric,
    plus per-task validation_method and consensus_score for completed tasks.
    """

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
            "description": "3+ models with Fleiss' Kappa (Wang et al., 2025)",
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

    methods_by_id = {}
    for m in method_stats:
        if m.method not in methods_by_id:
            methods_by_id[m.method] = {
                "method": m.method,
                "skill_name": m.skill_name or "",
                "agent_id": m.agent_id or "",
                "total_runs": m.total_runs,
                "success_count": m.success_count,
                "fail_count": m.fail_count,
                "avg_consensus_score": round(m.avg_consensus_score, 3),
                "success_rate": round(m.success_count / max(m.total_runs, 1), 3),
                "last_used": m.last_used.isoformat() if m.last_used else None,
                "weight": round(m.weight, 3),
            }

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
        "method_stats": list(methods_by_id.values()),
        "recent_validations": recent_validations,
        "confidence_thresholds": {
            "nugget": 0.70,
            "fact": 0.65,
            "insight": 0.55,
            "recommendation": 0.50,
        },
    }


@router.get("/metrics/{project_id}/model-intelligence")
async def get_model_intelligence(project_id: str, limit: int = 50):
    """Get model intelligence data: leaderboard, error taxonomy, tool success, latency.

    Aggregates data from ModelSkillStats (production + autoresearch) and
    TelemetrySpan (operational traces) to help users choose the best models
    for each skill and understand error patterns.
    """
    from app.core.telemetry import telemetry_recorder
    return await telemetry_recorder.get_model_intelligence(project_id, limit=limit)
