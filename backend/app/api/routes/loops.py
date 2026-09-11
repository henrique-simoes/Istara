"""Loop management, execution history, and health dashboard API routes."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.datetime_utils import ensure_utc
from app.core.permissions import get_active_project_or_404, require_project_access
from app.core.scheduler import CronParser, ScheduledTask
from app.models.agent import Agent, AgentState
from app.models.database import get_db
from app.services import agent_service
from app.services.loop_execution_service import (
    get_execution_stats,
)
from app.services.loop_execution_service import (
    list_executions as list_recorded_executions,
)

logger = logging.getLogger(__name__)

router = APIRouter()
LOOP_MEMORY_KEY = "loop_config"
VALID_EXECUTION_STATUSES = {"success", "failure", "running", "skipped"}
SOURCE_TYPE_ALIASES = {
    "agent": ["agent", "agent_loop"],
    "agent_loop": ["agent", "agent_loop"],
    "schedule": ["schedule", "scheduled", "scheduled_task"],
    "scheduled": ["schedule", "scheduled", "scheduled_task"],
    "scheduled_task": ["schedule", "scheduled", "scheduled_task"],
    "custom": ["custom"],
}


# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------


class UpdateLoopConfigRequest(BaseModel):
    """Request body for updating an agent's loop configuration."""

    loop_interval_seconds: int | None = Field(default=None, ge=10, le=86_400)
    paused: bool | None = None
    skills_to_run: list[str] | None = Field(default=None, max_length=25)
    project_filter: str | None = Field(default=None, max_length=100)


class CreateCustomLoopRequest(BaseModel):
    """Request body for creating a custom loop (backed by a ScheduledTask)."""

    name: str = Field(min_length=1, max_length=120)
    skill_name: str = Field(min_length=1, max_length=100)
    project_id: str = Field(min_length=1, max_length=100)
    cron_expression: str | None = Field(default=None, max_length=100)
    interval_seconds: int | None = Field(default=None, ge=60, le=86_400)
    description: str = Field(default="", max_length=1000)


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
        return "error"
    return "active"


def _schedule_loop_status(task: ScheduledTask) -> str:
    """Derive a loop status string from a scheduled task."""
    if not task.enabled:
        return "paused"
    if task.is_running:
        return "active"
    if task.last_status == "failure":
        return "error"
    if task.last_run and task.next_run:
        now = datetime.now(UTC)
        next_utc = ensure_utc(task.next_run)
        if next_utc < now:
            return "behind_schedule"
    return "active"


def _agent_memory(agent: Agent) -> dict:
    try:
        return json.loads(agent.memory or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}


def _normalize_skills(skills: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for skill in skills:
        value = str(skill).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized


def _normalize_source_type(source_type: str | None) -> list[str] | None:
    if source_type is None or not source_type.strip():
        return None
    aliases = SOURCE_TYPE_ALIASES.get(source_type.strip())
    if aliases is None:
        allowed = ", ".join(sorted(SOURCE_TYPE_ALIASES))
        raise HTTPException(status_code=422, detail=f"source_type must be one of: {allowed}")
    return aliases


def _parse_filter_datetime(value: str | None, *, end_of_day: bool = False) -> datetime | None:
    if value is None or not value.strip():
        return None
    raw = value.strip()
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid date filter: {raw}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    parsed = ensure_utc(parsed)
    if end_of_day and len(raw) == 10:
        parsed = parsed + timedelta(days=1)
    return parsed


def _schedule_source_type(task: ScheduledTask) -> Literal["schedule", "custom"]:
    return "custom" if task.loop_type == "custom" else "schedule"


def _schedule_to_dict(task: ScheduledTask) -> dict:
    source_type = _schedule_source_type(task)
    return {
        "id": task.id,
        "name": task.name,
        "description": task.description,
        "cron_expression": task.cron_expression,
        "skill_name": task.skill_name,
        "project_id": task.project_id,
        "enabled": task.enabled,
        "is_running": task.is_running,
        "last_run": ensure_utc(task.last_run).isoformat() if task.last_run else None,
        "next_run": ensure_utc(task.next_run).isoformat() if task.next_run else None,
        "loop_status": _schedule_loop_status(task),
        "source_type": source_type,
        "source_id": task.id,
        "source_name": task.name,
        "loop_type": task.loop_type,
        "interval_seconds": task.interval_seconds,
        "execution_count": task.execution_count or 0,
        "last_status": task.last_status or "",
        "created_at": ensure_utc(task.created_at).isoformat() if task.created_at else None,
    }


def _loop_config_for_agent(agent: Agent) -> dict:
    memory = _agent_memory(agent)
    stored = memory.get(LOOP_MEMORY_KEY)
    if not isinstance(stored, dict):
        stored = {}
    skills = stored.get("skills_to_run")
    project_filter = stored.get("project_filter")
    return {
        "id": agent.id,
        "agent_id": agent.id,
        "name": agent.name,
        "scope": agent.scope or "universal",
        "project_id": agent.project_id or "",
        "loop_interval_seconds": agent.heartbeat_interval_seconds or 60,
        "paused": agent.state == AgentState.PAUSED,
        "state": agent.state.value if agent.state else "idle",
        "loop_status": _agent_loop_status(agent),
        "skills_to_run": skills if isinstance(skills, list) else [],
        "project_filter": project_filter if isinstance(project_filter, str) else "",
        "last_cycle_at": agent.last_heartbeat_at.isoformat() if agent.last_heartbeat_at else None,
        "cycle_count": agent.executions or 0,
        "last_heartbeat_at": agent.last_heartbeat_at.isoformat()
        if agent.last_heartbeat_at
        else None,
        "executions": agent.executions or 0,
        "error_count": agent.error_count or 0,
    }


async def _require_loop_project_scope(
    db: AsyncSession,
    request: Request,
    project_id: str | None,
    *,
    min_role: Literal["viewer", "researcher", "project_admin"] = "viewer",
) -> str:
    scoped_project_id = project_id.strip() if project_id else None
    if not scoped_project_id:
        raise HTTPException(status_code=400, detail="project_id is required")
    await require_project_access(db, request, scoped_project_id, min_role=min_role)
    return scoped_project_id


async def _require_active_loop_project_scope(
    db: AsyncSession,
    request: Request,
    project_id: str | None,
    *,
    min_role: Literal["viewer", "researcher", "project_admin"] = "researcher",
) -> str:
    scoped_project_id = project_id.strip() if project_id else None
    if not scoped_project_id:
        raise HTTPException(status_code=400, detail="project_id is required")
    project = await get_active_project_or_404(
        db,
        request,
        scoped_project_id,
        min_role=min_role,
    )
    return project.id


def _agent_matches_project(agent: Agent, project_id: str | None) -> bool:
    if project_id is None:
        return True
    config = _loop_config_for_agent(agent)
    return (agent.project_id or "") == project_id or config["project_filter"] == project_id


async def _load_loop_agents(db: AsyncSession, project_id: str | None) -> list[Agent]:
    query = select(Agent).where(Agent.is_active.is_(True)).order_by(Agent.created_at)
    if project_id is not None:
        query = query.where((Agent.project_id == project_id) | (Agent.memory.contains(project_id)))
    result = await db.execute(query)
    agents = result.scalars().all()
    if project_id is None:
        return list(agents)
    return [agent for agent in agents if _agent_matches_project(agent, project_id)]


def _schedule_query_for_project(project_id: str | None):
    query = select(ScheduledTask).order_by(ScheduledTask.created_at)
    if project_id is not None:
        query = query.where(ScheduledTask.project_id == project_id)
    return query


async def _project_loop_source_ids(db: AsyncSession, project_id: str | None) -> list[str] | None:
    if project_id is None:
        return None
    agents = await _load_loop_agents(db, project_id)
    schedule_result = await db.execute(
        select(ScheduledTask.id).where(ScheduledTask.project_id == project_id)
    )
    schedule_ids = list(schedule_result.scalars().all())
    return [*[agent.id for agent in agents], *schedule_ids]


async def _load_loop_agent_for_project(
    db: AsyncSession,
    request: Request,
    agent_id: str,
    project_id: str | None,
    *,
    min_role: Literal["viewer", "researcher", "project_admin"] = "viewer",
) -> tuple[Agent, str | None]:
    scoped_project_id = await _require_loop_project_scope(
        db,
        request,
        project_id,
        min_role=min_role,
    )
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent or not agent.is_active:
        raise HTTPException(status_code=404, detail="Agent not found")
    if not _agent_matches_project(agent, scoped_project_id):
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent, scoped_project_id


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/loops/overview")
async def loops_overview(
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Consolidated overview: agents with loop configs, schedules, and health summary."""
    scoped_project_id = await _require_loop_project_scope(db, request, project_id)
    agents = await _load_loop_agents(db, scoped_project_id)

    agent_dicts = []
    for a in agents:
        d = a.to_dict()
        d.update(_loop_config_for_agent(a))
        agent_dicts.append(d)

    # Schedules
    sched_result = await db.execute(_schedule_query_for_project(scoped_project_id))
    schedules = sched_result.scalars().all()
    sched_dicts = [_schedule_to_dict(s) for s in schedules]

    # Health summary
    all_statuses = [d["loop_status"] for d in agent_dicts] + [d["loop_status"] for d in sched_dicts]
    health_summary = {
        "active": sum(1 for s in all_statuses if s == "active"),
        "paused": sum(1 for s in all_statuses if s == "paused"),
        "behind_schedule": sum(1 for s in all_statuses if s == "behind_schedule"),
        "error": sum(1 for s in all_statuses if s == "error"),
        "stopped": sum(1 for s in all_statuses if s == "stopped"),
        "total": len(all_statuses),
    }
    since_24h = datetime.now(UTC) - timedelta(hours=24)
    source_ids = await _project_loop_source_ids(db, scoped_project_id)
    recent_executions = await list_recorded_executions(
        db,
        project_id=scoped_project_id,
        source_ids=source_ids,
        started_from=since_24h,
        page_size=1,
    )
    total_24h = recent_executions["total"]
    execution_stats = await get_execution_stats(
        db,
        project_id=scoped_project_id,
        source_ids=source_ids,
    )
    success_rate = (execution_stats.get("success_rate", 0.0) or 0.0) / 100

    return {
        "active_loops": health_summary["active"],
        "paused_loops": health_summary["paused"],
        "behind_schedule": health_summary["behind_schedule"],
        "total_executions_24h": total_24h,
        "success_rate": round(success_rate, 4),
        "agents": agent_dicts,
        "schedules": sched_dicts,
        "health_summary": health_summary,
    }


@router.get("/loops/agents")
async def list_loop_agents(
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List all agents with their loop configurations."""
    scoped_project_id = await _require_loop_project_scope(db, request, project_id)
    agents = await _load_loop_agents(db, scoped_project_id)
    return {"agents": [_loop_config_for_agent(agent) for agent in agents]}


@router.get("/loops/agents/{agent_id}/config")
async def get_loop_config(
    agent_id: str,
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get loop configuration for a specific agent."""
    agent_model, _ = await _load_loop_agent_for_project(db, request, agent_id, project_id)
    return _loop_config_for_agent(agent_model)


@router.patch("/loops/agents/{agent_id}/config")
async def update_loop_config(
    agent_id: str,
    data: UpdateLoopConfigRequest,
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Update an agent's loop configuration (interval, paused state, skills)."""
    agent, scoped_project_id = await _load_loop_agent_for_project(
        db,
        request,
        agent_id,
        project_id,
        min_role="researcher",
    )

    if data.loop_interval_seconds is not None:
        if data.loop_interval_seconds < 10 or data.loop_interval_seconds > 86_400:
            raise HTTPException(
                status_code=422,
                detail="loop_interval_seconds must be between 10 and 86400",
            )

    if data.paused is not None:
        if data.paused is False:
            await _require_active_loop_project_scope(
                db,
                request,
                scoped_project_id,
                min_role="researcher",
            )
        if data.paused and agent.state != AgentState.PAUSED:
            agent.state = AgentState.PAUSED
        elif not data.paused and agent.state == AgentState.PAUSED:
            agent.state = AgentState.IDLE

    if data.loop_interval_seconds is not None:
        agent.heartbeat_interval_seconds = data.loop_interval_seconds

    if data.skills_to_run is not None or data.project_filter is not None:
        memory = _agent_memory(agent)
        loop_config = memory.get(LOOP_MEMORY_KEY)
        if not isinstance(loop_config, dict):
            loop_config = {}
        if data.skills_to_run is not None:
            loop_config["skills_to_run"] = _normalize_skills(data.skills_to_run)
        if data.project_filter is not None:
            next_project_filter = data.project_filter.strip()
            if scoped_project_id:
                owns_agent = (agent.project_id or "") == scoped_project_id
                if next_project_filter and next_project_filter != scoped_project_id:
                    raise HTTPException(
                        status_code=403, detail="Cannot move loop outside active project"
                    )
                if not owns_agent and next_project_filter != scoped_project_id:
                    raise HTTPException(
                        status_code=403, detail="Cannot clear project filter for shared agent loop"
                    )
            loop_config["project_filter"] = next_project_filter
        memory[LOOP_MEMORY_KEY] = loop_config
        agent.memory = json.dumps(memory)

    agent.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(agent)

    response = _loop_config_for_agent(agent)
    response["updated"] = True
    return response


@router.post("/loops/agents/{agent_id}/pause")
async def pause_agent_loop(
    agent_id: str,
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Pause an agent's loop."""
    await _load_loop_agent_for_project(db, request, agent_id, project_id, min_role="researcher")
    if not await agent_service.set_agent_state(db, agent_id, AgentState.PAUSED):
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"agent_id": agent_id, "status": "paused"}


@router.post("/loops/agents/{agent_id}/resume")
async def resume_agent_loop(
    agent_id: str,
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Resume an agent's loop."""
    await _require_active_loop_project_scope(
        db,
        request,
        project_id,
        min_role="researcher",
    )
    await _load_loop_agent_for_project(db, request, agent_id, project_id, min_role="researcher")
    if not await agent_service.set_agent_state(db, agent_id, AgentState.IDLE):
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"agent_id": agent_id, "status": "resumed"}


@router.get("/loops/executions")
async def list_executions(
    request: Request,
    project_id: str | None = None,
    source_type: str | None = None,
    source_id: str | None = None,
    status: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Paginated execution history across agents and schedules."""
    scoped_project_id = await _require_loop_project_scope(db, request, project_id)
    if status and status not in VALID_EXECUTION_STATUSES:
        allowed = ", ".join(sorted(VALID_EXECUTION_STATUSES))
        raise HTTPException(status_code=422, detail=f"status must be one of: {allowed}")

    source_ids = await _project_loop_source_ids(db, scoped_project_id)
    result = await list_recorded_executions(
        db,
        source_types=_normalize_source_type(source_type),
        source_id=source_id,
        source_ids=source_ids,
        project_id=scoped_project_id,
        status=status,
        started_from=_parse_filter_datetime(from_date),
        started_to=_parse_filter_datetime(to_date, end_of_day=True),
        page=page,
        page_size=page_size,
    )
    total = result["total"]
    total_pages = max(1, (total + result["page_size"] - 1) // result["page_size"])

    return {
        "executions": result["items"],
        "total": total,
        "page": result["page"],
        "page_size": result["page_size"],
        "total_pages": total_pages,
    }


@router.get("/loops/executions/stats")
async def execution_stats(
    request: Request,
    project_id: str | None = None,
    source_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Aggregated execution statistics."""
    scoped_project_id = await _require_loop_project_scope(db, request, project_id)
    source_ids = await _project_loop_source_ids(db, scoped_project_id)
    stats = await get_execution_stats(
        db,
        source_id=source_id,
        source_ids=source_ids,
        project_id=scoped_project_id,
    )
    return {
        "total": stats["total"],
        "success": stats["success_count"],
        "failure": stats["failure_count"],
        "running": stats["running_count"],
        "skipped": stats["skipped_count"],
        "avg_duration_ms": stats["avg_duration_ms"],
        "success_rate": stats["success_rate"] / 100 if stats["success_rate"] else 0.0,
        "success_rate_percent": stats["success_rate"],
    }


@router.get("/loops/health")
async def loops_health(
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Loop health dashboard — unified status for all loop sources."""
    scoped_project_id = await _require_loop_project_scope(db, request, project_id)
    health_items: list[dict] = []
    now = datetime.now(UTC)

    # Agents
    for a in await _load_loop_agents(db, scoped_project_id):
        interval = a.heartbeat_interval_seconds or 60
        last_exec = ensure_utc(a.last_heartbeat_at) if a.last_heartbeat_at else None

        behind_by: float | None = None
        if last_exec:
            expected_next = last_exec.timestamp() + interval
            if now.timestamp() > expected_next:
                behind_by = round(now.timestamp() - expected_next, 1)

        health_items.append(
            {
                "source_type": "agent",
                "source_id": a.id,
                "source_name": a.name,
                "project_id": a.project_id or "",
                "status": _agent_loop_status(a),
                "interval_seconds": interval,
                "last_execution_at": last_exec.isoformat() if last_exec else None,
                "next_expected_at": (
                    datetime.fromtimestamp(last_exec.timestamp() + interval, tz=UTC).isoformat()
                    if last_exec
                    else None
                ),
                "behind_by_seconds": behind_by,
                "last_status": "failure" if a.error_count else "",
            }
        )

    # Schedules
    sched_result = await db.execute(_schedule_query_for_project(scoped_project_id))
    for s in sched_result.scalars().all():
        last_exec = ensure_utc(s.last_run) if s.last_run else None
        next_run = ensure_utc(s.next_run) if s.next_run else None

        behind_by = None
        if next_run and next_run < now:
            behind_by = round((now - next_run).total_seconds(), 1)

        health_items.append(
            {
                "source_type": _schedule_source_type(s),
                "source_id": s.id,
                "source_name": s.name,
                "project_id": s.project_id,
                "status": _schedule_loop_status(s),
                "interval_seconds": s.interval_seconds,
                "last_execution_at": last_exec.isoformat() if last_exec else None,
                "next_expected_at": next_run.isoformat() if next_run else None,
                "behind_by_seconds": behind_by,
                "cron_expression": s.cron_expression,
                "skill_name": s.skill_name,
                "last_status": s.last_status or "",
                "execution_count": s.execution_count or 0,
            }
        )

    return {"health": health_items}


@router.post("/loops/custom", status_code=201)
async def create_custom_loop(
    data: CreateCustomLoopRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Create a custom loop as a ScheduledTask with loop_type metadata."""
    name = data.name.strip()
    skill_name = data.skill_name.strip()
    project_id = data.project_id.strip()
    description = data.description.strip()
    if not name or not skill_name or not project_id:
        raise HTTPException(status_code=422, detail="name, skill_name, and project_id are required")
    project_id = await _require_active_loop_project_scope(
        db,
        request,
        project_id,
        min_role="researcher",
    )

    # Determine cron expression: explicit or derived from interval
    cron_expr = data.cron_expression.strip() if data.cron_expression else None
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

    now = datetime.now(UTC)
    try:
        next_run = CronParser.next_run_after(cron_expr, now)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    task = ScheduledTask(
        id=str(uuid.uuid4()),
        name=name,
        description=description,
        cron_expression=cron_expr,
        skill_name=skill_name,
        project_id=project_id,
        next_run=next_run,
        loop_type="custom",
        interval_seconds=data.interval_seconds,
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
        "loop_type": task.loop_type,
        "interval_seconds": task.interval_seconds,
        "next_run": ensure_utc(task.next_run).isoformat() if task.next_run else None,
        "created_at": ensure_utc(task.created_at).isoformat() if task.created_at else None,
    }
