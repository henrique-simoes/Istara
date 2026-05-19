"""Mid-execution steering API routes.

Allows users to inject steering messages to agents while they're working,
inspired by pi-mono's steer()/followUp() message queue pattern.

Endpoints:
- POST /api/steering/{agent_id}           — Queue steering message
- POST /api/steering/{agent_id}/follow-up — Queue follow-up message
- POST /api/steering/{agent_id}/abort     — Abort current task, clear queues
- GET  /api/steering/{agent_id}/status    — Get steering queues + agent state
- GET  /api/steering/{agent_id}/queues    — Get queued message contents
- DELETE /api/steering/{agent_id}/queues  — Clear all queues
- GET  /api/steering/{agent_id}/idle      — SSE: wait until agent is idle
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_project_access
from app.core.security_middleware import require_admin_from_request
from app.core.steering import SteeringMode, steering_manager
from app.models.agent import Agent
from app.models.database import get_db
from app.models.project import Project
from app.services.agent_service import SYSTEM_AGENTS

router = APIRouter()
logger = logging.getLogger(__name__)
SYSTEM_AGENT_IDS = {str(agent["id"]) for agent in SYSTEM_AGENTS}


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class SteeringMessageRequest(BaseModel):
    message: str
    project_id: str
    source: str = "user"
    mode: SteeringMode = "one-at-a-time"


class FollowUpMessageRequest(BaseModel):
    message: str
    project_id: str
    source: str = "user"
    mode: SteeringMode = "one-at-a-time"


class SteeringStatusResponse(BaseModel):
    agent_id: str
    project_id: str
    is_working: bool
    steering_queue_count: int
    follow_up_queue_count: int
    steering_mode: SteeringMode
    follow_up_mode: SteeringMode
    has_queued_messages: bool


class QueuedMessageResponse(BaseModel):
    message: str
    source: str
    timestamp: float
    metadata: dict


class SteeringQueuesResponse(BaseModel):
    agent_id: str
    project_id: str
    steering_queue: list[QueuedMessageResponse]
    follow_up_queue: list[QueuedMessageResponse]


class SteeringAbortResponse(BaseModel):
    agent_id: str
    project_id: str
    cleared_steering_count: int
    cleared_follow_up_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_project_id(project_id: str | None) -> str:
    scoped_project_id = (project_id or "").strip()
    if not scoped_project_id:
        raise HTTPException(status_code=400, detail="project_id is required")
    return scoped_project_id


async def _validate_agent_id(agent_id: str) -> None:
    """Validate that the agent_id is a non-empty string."""
    if not agent_id or not agent_id.strip():
        raise HTTPException(status_code=400, detail="Agent ID is required")


async def _require_steering_project(
    db: AsyncSession,
    request: Request,
    project_id: str | None,
    *,
    min_role: str = "viewer",
) -> Project:
    require_admin_from_request(request)
    scoped_project_id = _require_project_id(project_id)
    result = await db.execute(select(Project).where(Project.id == scoped_project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await require_project_access(db, request, scoped_project_id, min_role=min_role)
    return project


async def _require_steerable_agent(
    db: AsyncSession,
    agent_id: str,
    project_id: str,
) -> None:
    await _validate_agent_id(agent_id)
    agent = await db.get(Agent, agent_id)
    if agent:
        if (agent.scope or "universal") == "project" and (agent.project_id or "") != project_id:
            raise HTTPException(status_code=404, detail="Agent not found")
        return
    if agent_id not in SYSTEM_AGENT_IDS:
        raise HTTPException(status_code=404, detail="Agent not found")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/steering/{agent_id}", response_model=dict)
async def queue_steering_message(
    agent_id: str,
    body: SteeringMessageRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Queue a steering message to be injected after the current skill execution."""
    project = await _require_steering_project(
        db,
        request,
        body.project_id,
        min_role="researcher",
    )
    await _require_steerable_agent(db, agent_id, project.id)
    await steering_manager.steer(
        agent_id,
        body.message,
        source=body.source,
        project_id=project.id,
        mode=body.mode,
    )
    status = steering_manager.get_status(agent_id, project_id=project.id)
    return {
        "status": "queued",
        "agent_id": agent_id,
        "project_id": project.id,
        "queue_count": status["steering_queue_count"],
        "message": "Steering message queued. Will be delivered after current skill completes.",
    }


@router.post("/steering/{agent_id}/follow-up", response_model=dict)
async def queue_follow_up_message(
    agent_id: str,
    body: FollowUpMessageRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Queue a follow-up message to be injected when the agent would otherwise stop.

    Follow-up messages are only processed when the agent has no more pending work.
    """
    project = await _require_steering_project(
        db,
        request,
        body.project_id,
        min_role="researcher",
    )
    await _require_steerable_agent(db, agent_id, project.id)
    await steering_manager.follow_up(
        agent_id,
        body.message,
        source=body.source,
        project_id=project.id,
        mode=body.mode,
    )
    status = steering_manager.get_status(agent_id, project_id=project.id)
    return {
        "status": "queued",
        "agent_id": agent_id,
        "project_id": project.id,
        "queue_count": status["follow_up_queue_count"],
        "message": "Follow-up message queued. Will be delivered when agent finishes all work.",
    }


@router.post("/steering/{agent_id}/abort", response_model=SteeringAbortResponse)
async def abort_agent_work(
    agent_id: str,
    request: Request,
    project_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Abort the agent's current work and clear all steering queues.

    This is the programmatic equivalent of pressing Escape in pi-mono.
    Queued messages are returned so the caller can restore them to the editor.
    """
    project = await _require_steering_project(db, request, project_id, min_role="researcher")
    await _require_steerable_agent(db, agent_id, project.id)
    cleared = await steering_manager.abort(agent_id, project_id=project.id)

    # Also signal the orchestrator to stop current task
    if agent_id == "istara-main":
        from app.core.agent import agent as agent_orchestrator
        agent_orchestrator.stop()

    return SteeringAbortResponse(
        agent_id=agent_id,
        project_id=project.id,
        cleared_steering_count=len(cleared.get("steering", [])),
        cleared_follow_up_count=len(cleared.get("follow_up", [])),
    )


@router.get("/steering/{agent_id}/status", response_model=SteeringStatusResponse)
async def get_steering_status(
    agent_id: str,
    request: Request,
    project_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Get steering status for an agent."""
    project = await _require_steering_project(db, request, project_id, min_role="viewer")
    await _require_steerable_agent(db, agent_id, project.id)
    status = steering_manager.get_status(agent_id, project_id=project.id)
    return SteeringStatusResponse(**status)


@router.get("/steering/{agent_id}/queues", response_model=SteeringQueuesResponse)
async def get_steering_queues(
    agent_id: str,
    request: Request,
    project_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Get the contents of both steering queues."""
    project = await _require_steering_project(db, request, project_id, min_role="viewer")
    await _require_steerable_agent(db, agent_id, project.id)
    queues = steering_manager.get_queues(agent_id, project_id=project.id)

    return SteeringQueuesResponse(
        agent_id=agent_id,
        project_id=project.id,
        steering_queue=[
            QueuedMessageResponse(
                message=msg.message,
                source=msg.source,
                timestamp=msg.timestamp,
                metadata=msg.metadata,
            )
            for msg in queues["steering"]
        ],
        follow_up_queue=[
            QueuedMessageResponse(
                message=msg.message,
                source=msg.source,
                timestamp=msg.timestamp,
                metadata=msg.metadata,
            )
            for msg in queues["follow_up"]
        ],
    )


@router.delete("/steering/{agent_id}/queues", response_model=dict)
async def clear_steering_queues(
    agent_id: str,
    request: Request,
    project_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Clear all steering and follow-up queues for an agent."""
    project = await _require_steering_project(db, request, project_id, min_role="researcher")
    await _require_steerable_agent(db, agent_id, project.id)
    cleared = await steering_manager.clear_all(agent_id, project_id=project.id)
    return {
        "status": "cleared",
        "agent_id": agent_id,
        "project_id": project.id,
        "cleared_steering_count": len(cleared.get("steering", [])),
        "cleared_follow_up_count": len(cleared.get("follow_up", [])),
    }


@router.get("/steering/{agent_id}/idle")
async def wait_for_agent_idle(
    agent_id: str,
    request: Request,
    project_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """SSE endpoint: waits until the agent finishes all work.

    Useful for frontend to know when to hide the steering input
    and show the agent as idle again.

    Streams one event: {"agent_id": "...", "status": "idle"}
    """
    project = await _require_steering_project(db, request, project_id, min_role="viewer")
    await _require_steerable_agent(db, agent_id, project.id)
    from fastapi.responses import StreamingResponse

    async def event_stream():
        result = await steering_manager.wait_for_idle(agent_id, timeout=300.0, project_id=project.id)
        status = "idle" if result else "timeout"
        yield (
            f"data: {{\"agent_id\": \"{agent_id}\", \"project_id\": "
            f"\"{project.id}\", \"status\": \"{status}\"}}\n\n"
        )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/steering", response_model=dict)
async def get_all_steering_status(
    request: Request,
    project_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Get steering status for all agents."""
    project = await _require_steering_project(db, request, project_id, min_role="viewer")
    return steering_manager.get_all_status(project_id=project.id)
