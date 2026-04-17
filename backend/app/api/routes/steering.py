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

import asyncio
import logging
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.steering import SteeringMode, steering_manager

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class SteeringMessageRequest(BaseModel):
    message: str
    source: str = "user"
    mode: SteeringMode = "one-at-a-time"


class FollowUpMessageRequest(BaseModel):
    message: str
    source: str = "user"
    mode: SteeringMode = "one-at-a-time"


class SteeringStatusResponse(BaseModel):
    agent_id: str
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
    steering_queue: list[QueuedMessageResponse]
    follow_up_queue: list[QueuedMessageResponse]


class SteeringAbortResponse(BaseModel):
    agent_id: str
    cleared_steering_count: int
    cleared_follow_up_count: int


# ---------------------------------------------------------------------------
# Helper: validate agent ID format
# ---------------------------------------------------------------------------

async def _validate_agent_id(agent_id: str) -> None:
    """Validate that the agent_id is a non-empty string.

    Unlike other routes, steering doesn't require the agent to exist
    in the database — it's a pure in-memory queue keyed by agent_id.
    The agent orchestrator picks up messages when it checks the queue.
    """
    if not agent_id or not agent_id.strip():
        raise HTTPException(status_code=400, detail="Agent ID is required")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/steering/{agent_id}", response_model=dict)
async def queue_steering_message(agent_id: str, body: SteeringMessageRequest):
    """Queue a steering message to be injected after the current skill execution."""
    await _validate_agent_id(agent_id)
    await steering_manager.steer(agent_id, body.message, source=body.source)
    return {
        "status": "queued",
        "agent_id": agent_id,
        "queue_count": len(steering_manager._get_or_create(agent_id).steering_queue),
        "message": "Steering message queued. Will be delivered after current skill completes.",
    }


@router.post("/steering/{agent_id}/follow-up", response_model=dict)
async def queue_follow_up_message(agent_id: str, body: FollowUpMessageRequest):
    """Queue a follow-up message to be injected when the agent would otherwise stop.

    Follow-up messages are only processed when the agent has no more pending work.
    """
    await _validate_agent_id(agent_id)
    await steering_manager.follow_up(agent_id, body.message, source=body.source)
    return {
        "status": "queued",
        "agent_id": agent_id,
        "queue_count": len(steering_manager._get_or_create(agent_id).follow_up_queue),
        "message": "Follow-up message queued. Will be delivered when agent finishes all work.",
    }


@router.post("/steering/{agent_id}/abort", response_model=SteeringAbortResponse)
async def abort_agent_work(agent_id: str):
    """Abort the agent's current work and clear all steering queues.

    This is the programmatic equivalent of pressing Escape in pi-mono.
    Queued messages are returned so the caller can restore them to the editor.
    """
    await _validate_agent_id(agent_id)
    cleared = await steering_manager.abort(agent_id)

    # Also signal the orchestrator to stop current task
    if agent_id == "istara-main":
        from app.core.agent import agent as agent_orchestrator
        agent_orchestrator.stop()

    return SteeringAbortResponse(
        agent_id=agent_id,
        cleared_steering_count=len(cleared.get("steering", [])),
        cleared_follow_up_count=len(cleared.get("follow_up", [])),
    )


@router.get("/steering/{agent_id}/status", response_model=SteeringStatusResponse)
async def get_steering_status(agent_id: str):
    """Get steering status for an agent."""
    await _validate_agent_id(agent_id)
    status = steering_manager.get_status(agent_id)
    return SteeringStatusResponse(**status)


@router.get("/steering/{agent_id}/queues", response_model=SteeringQueuesResponse)
async def get_steering_queues(agent_id: str):
    """Get the contents of both steering queues."""
    await _validate_agent_id(agent_id)
    state = steering_manager._get_or_create(agent_id)

    return SteeringQueuesResponse(
        agent_id=agent_id,
        steering_queue=[
            QueuedMessageResponse(
                message=msg.message,
                source=msg.source,
                timestamp=msg.timestamp,
                metadata=msg.metadata,
            )
            for msg in state.steering_queue
        ],
        follow_up_queue=[
            QueuedMessageResponse(
                message=msg.message,
                source=msg.source,
                timestamp=msg.timestamp,
                metadata=msg.metadata,
            )
            for msg in state.follow_up_queue
        ],
    )


@router.delete("/steering/{agent_id}/queues", response_model=dict)
async def clear_steering_queues(agent_id: str):
    """Clear all steering and follow-up queues for an agent."""
    await _validate_agent_id(agent_id)
    cleared = await steering_manager.clear_all(agent_id)
    return {
        "status": "cleared",
        "agent_id": agent_id,
        "cleared_steering_count": len(cleared.get("steering", [])),
        "cleared_follow_up_count": len(cleared.get("follow_up", [])),
    }


@router.get("/steering/{agent_id}/idle")
async def wait_for_agent_idle(agent_id: str):
    """SSE endpoint: waits until the agent finishes all work.

    Useful for frontend to know when to hide the steering input
    and show the agent as idle again.

    Streams one event: {"agent_id": "...", "status": "idle"}
    """
    from fastapi.responses import StreamingResponse

    async def event_stream():
        await _validate_agent_id(agent_id)
        result = await steering_manager.wait_for_idle(agent_id, timeout=300.0)
        status = "idle" if result else "timeout"
        yield f"data: {{\"agent_id\": \"{agent_id}\", \"status\": \"{status}\"}}\n\n"

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
async def get_all_steering_status():
    """Get steering status for all agents."""
    return steering_manager.get_all_status()
