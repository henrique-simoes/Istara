"""Project-scope guards shared by agent API routes."""

from __future__ import annotations

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.permissions import get_subject, is_global_admin, require_project_access
from app.models.agent import Agent


def clean_project_id(project_id: str | None) -> str | None:
    cleaned = (project_id or "").strip()
    return cleaned or None


def is_team_non_admin(request: Request) -> bool:
    return settings.team_mode and not is_global_admin(get_subject(request))


def agent_project_id(agent: Agent) -> str | None:
    return clean_project_id(agent.project_id)


async def load_agent_or_404(db: AsyncSession, agent_id: str) -> Agent:
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


async def require_agent_project_access(
    db: AsyncSession,
    request: Request,
    agent: Agent,
    *,
    project_id: str | None = None,
    min_role: str = "viewer",
) -> str | None:
    """Require the active project context allowed to see this agent."""
    scoped_project_id = clean_project_id(project_id)
    owned_project_id = agent_project_id(agent)
    if scoped_project_id and owned_project_id and scoped_project_id != owned_project_id:
        raise HTTPException(status_code=404, detail="Agent not found")

    subject = get_subject(request)
    if not settings.team_mode or is_global_admin(subject):
        return scoped_project_id or owned_project_id

    if not scoped_project_id:
        raise HTTPException(status_code=400, detail="project_id is required")

    await require_project_access(db, request, scoped_project_id, min_role=min_role)
    return scoped_project_id


async def require_agent_by_id(
    db: AsyncSession,
    request: Request,
    agent_id: str,
    *,
    project_id: str | None = None,
    min_role: str = "viewer",
) -> Agent:
    agent = await load_agent_or_404(db, agent_id)
    await require_agent_project_access(
        db,
        request,
        agent,
        project_id=project_id,
        min_role=min_role,
    )
    return agent


async def require_project_owned_agent(
    db: AsyncSession,
    request: Request,
    agent_id: str,
    project_id: str | None,
    *,
    min_role: str = "project_admin",
) -> Agent:
    scoped_project_id = clean_project_id(project_id)
    if not scoped_project_id:
        raise HTTPException(status_code=400, detail="project_id is required")
    await require_project_access(db, request, scoped_project_id, min_role=min_role)
    agent = await require_agent_by_id(
        db,
        request,
        agent_id,
        project_id=scoped_project_id,
        min_role=min_role,
    )
    if agent_project_id(agent) != scoped_project_id:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


async def require_agent_collection_scope(
    db: AsyncSession,
    request: Request,
    project_id: str | None,
    *,
    min_role: str = "viewer",
) -> str | None:
    scoped_project_id = clean_project_id(project_id)
    subject = get_subject(request)
    if scoped_project_id:
        await require_project_access(db, request, scoped_project_id, min_role=min_role)
    elif settings.team_mode and not is_global_admin(subject):
        raise HTTPException(status_code=400, detail="project_id is required")
    return scoped_project_id


def redact_global_agent_state_for_project_view(agent: dict, request: Request) -> dict:
    if not is_team_non_admin(request) or agent.get("project_id"):
        return agent
    redacted = dict(agent)
    redacted["memory"] = {}
    redacted["current_task"] = ""
    return redacted


def filter_agent_dicts_for_project(
    agents: list[dict],
    project_id: str | None,
    request: Request,
) -> list[dict]:
    if project_id:
        agents = [
            agent
            for agent in agents
            if agent.get("scope", "universal") == "universal"
            or agent.get("project_id") == project_id
        ]
    return [redact_global_agent_state_for_project_view(agent, request) for agent in agents]


def entry_project_id(entry: dict) -> str | None:
    for key in ("project_id", "projectId", "active_project_id"):
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    metadata = entry.get("metadata") or entry.get("extra_data")
    if isinstance(metadata, dict):
        for key in ("project_id", "projectId", "active_project_id"):
            value = metadata.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def filter_work_log(
    log: list[dict],
    *,
    project_id: str | None,
    agent_id: str | None,
    limit: int,
) -> list[dict]:
    if project_id:
        log = [entry for entry in log if entry_project_id(entry) == project_id]
    if agent_id:
        log = [entry for entry in log if entry.get("agent_id") == agent_id]
    return log[-limit:]
