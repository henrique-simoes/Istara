"""Metrics API — quantitative research data for the dashboard."""

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.finding import Nugget, Fact, Insight, Recommendation
from app.models.task import Task, TaskStatus
from app.models.message import Message

router = APIRouter()


@router.get("/metrics/{project_id}")
async def get_project_metrics(project_id: str, db: AsyncSession = Depends(get_db)):
    """Get quantitative metrics for a project's research progress."""

    # Count findings by type
    nugget_count = (await db.execute(select(func.count(Nugget.id)).where(Nugget.project_id == project_id))).scalar() or 0
    fact_count = (await db.execute(select(func.count(Fact.id)).where(Fact.project_id == project_id))).scalar() or 0
    insight_count = (await db.execute(select(func.count(Insight.id)).where(Insight.project_id == project_id))).scalar() or 0
    rec_count = (await db.execute(select(func.count(Recommendation.id)).where(Recommendation.project_id == project_id))).scalar() or 0

    # Task stats
    total_tasks = (await db.execute(select(func.count(Task.id)).where(Task.project_id == project_id))).scalar() or 0
    done_tasks = (await db.execute(select(func.count(Task.id)).where(Task.project_id == project_id, Task.status == TaskStatus.DONE))).scalar() or 0
    in_progress = (await db.execute(select(func.count(Task.id)).where(Task.project_id == project_id, Task.status == TaskStatus.IN_PROGRESS))).scalar() or 0

    # Message count
    msg_count = (await db.execute(select(func.count(Message.id)).where(Message.project_id == project_id))).scalar() or 0

    # Average confidence across insights
    avg_confidence_result = await db.execute(
        select(func.avg(Insight.confidence)).where(Insight.project_id == project_id)
    )
    avg_confidence = avg_confidence_result.scalar() or 0

    # Findings by phase
    phases = {}
    for phase in ["discover", "define", "develop", "deliver"]:
        n = (await db.execute(select(func.count(Nugget.id)).where(Nugget.project_id == project_id, Nugget.phase == phase))).scalar() or 0
        f = (await db.execute(select(func.count(Fact.id)).where(Fact.project_id == project_id, Fact.phase == phase))).scalar() or 0
        i = (await db.execute(select(func.count(Insight.id)).where(Insight.project_id == project_id, Insight.phase == phase))).scalar() or 0
        r = (await db.execute(select(func.count(Recommendation.id)).where(Recommendation.project_id == project_id, Recommendation.phase == phase))).scalar() or 0
        phases[phase] = {"nuggets": n, "facts": f, "insights": i, "recommendations": r, "total": n + f + i + r}

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
