"""Loop management, execution history, and health dashboard API routes."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.datetime_utils import ensure_utc
from app.core.scheduler import CronParser, ScheduledTask
from app.models.agent import Agent, AgentState
from app.models.database import get_db
from app.services import agent_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------


class UpdateLoopConfigRequest(BaseModel):
    """Request body for updating an agent's loop configuration."""

    loop_interval_seconds: int | None = None
    paused: bool | None = None
    skills_to_run: list[str] | None = None
    project_filter: str | None = None


class CreateCustomLoopRequest(BaseModel):
    """Request body for creating a custom loop (backed by a ScheduledTask)."""

    name: str
    skill_name: str
    project_id: str
    cron_expression: str | None = None
    interval_seconds: int | None = None
    description: str = ""


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _agent_loop_status(agent: Agent) -> str:
    """Derive a loop status string from agent state and heartbeat."""
    if agent.state == AgentState.PAUSED:
        return "paused"
    if agent.state == AgentState.STOPPED:
        return "stopped"
    if agent.state == AgentState.ERROR:
        return "behind"
    return "active"


def _schedule_loop_status(task: ScheduledTask) -> str:
    """Derive a loop status string from a scheduled task."""
    if not task.enabled:
        return "paused"
    if task.is_running:
        return "active"
    if task.last_run and task.next_run:
        now = datetime.now(timezone.utc)
        next_utc = ensure_utc(task.next_run)
        if next_utc < now:
            return "behind"
    return "active"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/loops/overview")
async def loops_overview(db: AsyncSession = Depends(get_db)):
    """Consolidated overview: agents with loop configs, schedules, and health summary."""
    # Agents
    agent_result = await db.execute(
        select(Agent).where(Agent.is_active.is_(True)).order_by(Agent.created_at)
    )
    agents = agent_result.scalars().all()

    agent_dicts = []
    for a in agents:
        d = a.to_dict()
        d["loop_status"] = _agent_loop_status(a)
        agent_dicts.append(d)

    # Schedules
    sched_result = await db.execute(
        select(ScheduledTask).order_by(ScheduledTask.created_at)
    )
    schedules = sched_result.scalars().all()
    sched_dicts = [
        {
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "cron_expression": s.cron_expression,
            "skill_name": s.skill_name,
            "project_id": s.project_id,
            "enabled": s.enabled,
            "is_running": s.is_running,
            "last_run": s.last_run.isoformat() if s.last_run else None,
            "next_run": s.next_run.isoformat() if s.next_run else None,
            "loop_status": _schedule_loop_status(s),
        }
        for s in schedules
    ]

    # Health summary
    all_statuses = [d["loop_status"] for d in agent_dicts] + [
        d["loop_status"] for d in sched_dicts
    ]
    health_summary = {
        "active": sum(1 for s in all_statuses if s == "active"),
        "paused": sum(1 for s in all_statuses if s == "paused"),
        "behind": sum(1 for s in all_statuses if s == "behind"),
        "stopped": sum(1 for s in all_statuses if s == "stopped"),
        "total": len(all_statuses),
    }

    return {
        "agents": agent_dicts,
        "schedules": sched_dicts,
        "health_summary": health_summary,
    }


@router.get("/loops/agents")
async def list_loop_agents(db: AsyncSession = Depends(get_db)):
    """List all agents with their loop configurations."""
    agents = await agent_service.list_agents(db)
    for a in agents:
        a["loop_interval_seconds"] = a.get("heartbeat_interval_seconds", 60)
        a["loop_status"] = (
            "paused" if a.get("state") == "paused"
            else "stopped" if a.get("state") == "stopped"
            else "behind" if a.get("state") == "error"
            else "active"
        )
    return {"agents": agents}


@router.get("/loops/agents/{agent_id}/config")
async def get_loop_config(agent_id: str, db: AsyncSession = Depends(get_db)):
    """Get loop configuration for a specific agent."""
    agent = await agent_service.get_agent(db, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return {
        "agent_id": agent_id,
        "name": agent["name"],
        "loop_interval_seconds": agent.get("heartbeat_interval_seconds", 60),
        "paused": agent.get("state") == "paused",
        "state": agent.get("state", "idle"),
        "last_heartbeat_at": agent.get("last_heartbeat_at"),
        "executions": agent.get("executions", 0),
        "error_count": agent.get("error_count", 0),
    }


@router.patch("/loops/agents/{agent_id}/config")
async def update_loop_config(
    agent_id: str,
    data: UpdateLoopConfigRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update an agent's loop configuration (interval, paused state, skills)."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    updates: dict = {}

    if data.loop_interval_seconds is not None:
        updates["heartbeat_interval_seconds"] = data.loop_interval_seconds

    if data.paused is not None:
        if data.paused and agent.state != AgentState.PAUSED:
            agent.state = AgentState.PAUSED
        elif not data.paused and agent.state == AgentState.PAUSED:
            agent.state = AgentState.IDLE

    if data.loop_interval_seconds is not None:
        agent.heartbeat_interval_seconds = data.loop_interval_seconds

    agent.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(agent)

    return {
        "agent_id": agent_id,
        "loop_interval_seconds": agent.heartbeat_interval_seconds,
        "paused": agent.state == AgentState.PAUSED,
        "state": agent.state.value if agent.state else "idle",
        "updated": True,
    }


@router.post("/loops/agents/{agent_id}/pause")
async def pause_agent_loop(agent_id: str, db: AsyncSession = Depends(get_db)):
    """Pause an agent's loop."""
    if not await agent_service.set_agent_state(db, agent_id, AgentState.PAUSED):
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"agent_id": agent_id, "status": "paused"}


@router.post("/loops/agents/{agent_id}/resume")
async def resume_agent_loop(agent_id: str, db: AsyncSession = Depends(get_db)):
    """Resume an agent's loop."""
    if not await agent_service.set_agent_state(db, agent_id, AgentState.IDLE):
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"agent_id": agent_id, "status": "resumed"}


@router.get("/loops/executions")
async def list_executions(
    source_type: str | None = None,
    source_id: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Paginated execution history across agents and schedules.

    Combines agent execution counts with scheduled task run history
    into a unified timeline.
    """
    executions: list[dict] = []

    # Agent executions
    if source_type is None or source_type == "agent":
        agent_query = select(Agent).where(Agent.is_active.is_(True))
        if source_id:
            agent_query = agent_query.where(Agent.id == source_id)
        agent_result = await db.execute(agent_query.order_by(Agent.updated_at.desc()))
        for a in agent_result.scalars().all():
            agent_status = a.state.value if a.state else "idle"
            if status and agent_status != status:
                continue
            executions.append({
                "source_type": "agent",
                "source_id": a.id,
                "source_name": a.name,
                "status": agent_status,
                "executions": a.executions,
                "error_count": a.error_count,
                "last_execution_at": a.last_heartbeat_at.isoformat() if a.last_heartbeat_at else None,
                "updated_at": a.updated_at.isoformat() if a.updated_at else None,
            })

    # Scheduled task executions
    if source_type is None or source_type == "schedule":
        sched_query = select(ScheduledTask)
        if source_id:
            sched_query = sched_query.where(ScheduledTask.id == source_id)
        sched_result = await db.execute(sched_query.order_by(ScheduledTask.created_at.desc()))
        for s in sched_result.scalars().all():
            sched_status = _schedule_loop_status(s)
            if status and sched_status != status:
                continue
            executions.append({
                "source_type": "schedule",
                "source_id": s.id,
                "source_name": s.name,
                "status": sched_status,
                "last_execution_at": s.last_run.isoformat() if s.last_run else None,
                "next_run": s.next_run.isoformat() if s.next_run else None,
                "cron_expression": s.cron_expression,
                "skill_name": s.skill_name,
            })

    # Pagination
    total = len(executions)
    start = (page - 1) * page_size
    end = start + page_size

    return {
        "executions": executions[start:end],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/loops/executions/stats")
async def execution_stats(
    source_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Aggregated execution statistics."""
    # Agent stats
    agent_query = select(
        func.count(Agent.id).label("total_agents"),
        func.sum(Agent.executions).label("total_executions"),
        func.sum(Agent.error_count).label("total_errors"),
    ).where(Agent.is_active.is_(True))
    if source_id:
        agent_query = agent_query.where(Agent.id == source_id)
    agent_row = (await db.execute(agent_query)).one()

    # Schedule stats
    sched_query = select(
        func.count(ScheduledTask.id).label("total_schedules"),
    )
    if source_id:
        sched_query = sched_query.where(ScheduledTask.id == source_id)
    sched_row = (await db.execute(sched_query)).one()

    active_sched_count = (await db.execute(
        select(func.count(ScheduledTask.id)).where(ScheduledTask.enabled.is_(True))
    )).scalar() or 0

    return {
        "total_agents": agent_row.total_agents or 0,
        "total_agent_executions": agent_row.total_executions or 0,
        "total_agent_errors": agent_row.total_errors or 0,
        "total_schedules": sched_row.total_schedules or 0,
        "active_schedules": active_sched_count,
    }


@router.get("/loops/health")
async def loops_health(db: AsyncSession = Depends(get_db)):
    """Loop health dashboard — unified status for all loop sources."""
    health_items: list[dict] = []
    now = datetime.now(timezone.utc)

    # Agents
    agent_result = await db.execute(
        select(Agent).where(Agent.is_active.is_(True)).order_by(Agent.created_at)
    )
    for a in agent_result.scalars().all():
        interval = a.heartbeat_interval_seconds or 60
        last_exec = ensure_utc(a.last_heartbeat_at) if a.last_heartbeat_at else None

        behind_by: float | None = None
        if last_exec:
            expected_next = last_exec.timestamp() + interval
            if now.timestamp() > expected_next:
                behind_by = round(now.timestamp() - expected_next, 1)

        health_items.append({
            "source_type": "agent",
            "source_id": a.id,
            "source_name": a.name,
            "status": _agent_loop_status(a),
            "interval_seconds": interval,
            "last_execution_at": last_exec.isoformat() if last_exec else None,
            "next_expected_at": (
                datetime.fromtimestamp(last_exec.timestamp() + interval, tz=timezone.utc).isoformat()
                if last_exec else None
            ),
            "behind_by_seconds": behind_by,
        })

    # Schedules
    sched_result = await db.execute(
        select(ScheduledTask).order_by(ScheduledTask.created_at)
    )
    for s in sched_result.scalars().all():
        last_exec = ensure_utc(s.last_run) if s.last_run else None
        next_run = ensure_utc(s.next_run) if s.next_run else None

        behind_by = None
        if next_run and next_run < now:
            behind_by = round((now - next_run).total_seconds(), 1)

        health_items.append({
            "source_type": "schedule",
            "source_id": s.id,
            "source_name": s.name,
            "status": _schedule_loop_status(s),
            "interval_seconds": None,
            "last_execution_at": last_exec.isoformat() if last_exec else None,
            "next_expected_at": next_run.isoformat() if next_run else None,
            "behind_by_seconds": behind_by,
        })

    return {"health": health_items}


@router.post("/loops/custom", status_code=201)
async def create_custom_loop(
    data: CreateCustomLoopRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a custom loop as a ScheduledTask with loop_type metadata."""
    # Determine cron expression: explicit or derived from interval
    cron_expr = data.cron_expression
    if not cron_expr and data.interval_seconds:
        # Convert a simple interval into a cron-like expression.
        # For intervals that map cleanly to minutes, use */N.
        mins = max(1, data.interval_seconds // 60)
        if mins <= 59:
            cron_expr = f"*/{mins} * * * *"
        else:
            # Hourly+ intervals: run at minute 0 every N hours
            hours = max(1, mins // 60)
            cron_expr = f"0 */{hours} * * *"

    if not cron_expr:
        raise HTTPException(
            status_code=422,
            detail="Provide either cron_expression or interval_seconds",
        )

    # Validate the cron expression
    try:
        CronParser.parse(cron_expr)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    now = datetime.now(timezone.utc)
    try:
        next_run = CronParser.next_run_after(cron_expr, now)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    task = ScheduledTask(
        id=str(uuid.uuid4()),
        name=data.name,
        description=data.description,
        cron_expression=cron_expr,
        skill_name=data.skill_name,
        project_id=data.project_id,
        next_run=next_run,
    )

    db.add(task)
    await db.commit()
    await db.refresh(task)

    return {
        "id": task.id,
        "name": task.name,
        "description": task.description,
        "cron_expression": task.cron_expression,
        "skill_name": task.skill_name,
        "project_id": task.project_id,
        "enabled": task.enabled,
        "next_run": task.next_run.isoformat() if task.next_run else None,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }
