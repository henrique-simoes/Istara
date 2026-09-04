"""Deployment API routes — create, manage, and analyze research deployments."""

from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import ProjectRole, get_active_project_or_404, require_project_access
from app.models.channel_conversation import ChannelConversation
from app.models.database import get_db
from app.models.research_deployment import ResearchDeployment
from app.services import deployment_service

router = APIRouter()


def _require_project_id(project_id: str | None) -> str:
    scoped_project_id = (project_id or "").strip()
    if not scoped_project_id:
        raise HTTPException(status_code=400, detail="project_id is required")
    return scoped_project_id


async def _get_active_project_deployment_or_404(
    db: AsyncSession,
    request: Request,
    deployment_id: str,
    project_id: str | None,
    *,
    min_role: ProjectRole,
) -> ResearchDeployment:
    scoped_project_id = _require_project_id(project_id)
    await require_project_access(db, request, scoped_project_id, min_role=min_role)
    result = await db.execute(
        select(ResearchDeployment).where(
            ResearchDeployment.id == deployment_id,
            ResearchDeployment.project_id == scoped_project_id,
        )
    )
    deployment = result.scalar_one_or_none()
    if deployment is None:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return deployment


async def _get_project_deployment_conversation_or_404(
    db: AsyncSession,
    deployment: ResearchDeployment,
    conversation_id: str,
) -> ChannelConversation:
    conversation = await deployment_service.get_conversation(
        db,
        conversation_id,
        deployment_id=deployment.id,
        project_id=deployment.project_id,
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class QuestionSchema(BaseModel):
    text: str
    type: str = "open"  # open | scale | multiple_choice | yes_no
    expected_insight: str = ""
    follow_up_triggers: list[str] = []


class DeploymentCreate(BaseModel):
    project_id: str
    name: str
    deployment_type: str = "interview"  # interview | survey | diary_study
    questions: list[QuestionSchema] = []
    channel_instance_ids: list[str] = []
    config: dict | None = None
    target_responses: int = 0


class DeploymentResponse(BaseModel):
    id: str
    project_id: str
    name: str
    deployment_type: str
    questions: list[dict]
    config: dict
    channel_instance_ids: list[str]
    state: str
    target_responses: int
    current_responses: int
    created_at: datetime | None
    updated_at: datetime | None

    model_config = {"from_attributes": True}

    @classmethod
    def from_model(cls, d: ResearchDeployment) -> "DeploymentResponse":
        return cls(
            id=d.id,
            project_id=d.project_id,
            name=d.name,
            deployment_type=d.deployment_type,
            questions=json.loads(d.questions_json) if d.questions_json else [],
            config=json.loads(d.config_json) if d.config_json else {},
            channel_instance_ids=(
                json.loads(d.channel_instance_ids_json) if d.channel_instance_ids_json else []
            ),
            state=d.state,
            target_responses=d.target_responses,
            current_responses=d.current_responses,
            created_at=d.created_at,
            updated_at=d.updated_at,
        )


class HandleResponseRequest(BaseModel):
    conversation_id: str
    message_text: str


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@router.post("/deployments", response_model=DeploymentResponse, status_code=201)
async def create_deployment(
    data: DeploymentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Create a new research deployment."""
    scoped_project_id = _require_project_id(data.project_id)
    await get_active_project_or_404(db, request, scoped_project_id, min_role="researcher")

    questions = [q.model_dump() for q in data.questions]
    try:
        deployment = await deployment_service.create_deployment(
            db=db,
            project_id=scoped_project_id,
            name=data.name,
            deployment_type=data.deployment_type,
            questions=questions,
            channel_instance_ids=data.channel_instance_ids,
            config=data.config,
            target_responses=data.target_responses,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return DeploymentResponse.from_model(deployment)


@router.get("/deployments", response_model=list[DeploymentResponse])
async def list_deployments(
    request: Request,
    project_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List deployments for the active project."""
    project_id = _require_project_id(project_id)
    await require_project_access(db, request, project_id, min_role="viewer")

    deployments = await deployment_service.list_deployments(db, project_id=project_id)
    return [DeploymentResponse.from_model(d) for d in deployments]


@router.get("/deployments/overview")
async def deployment_overview(
    request: Request,
    project_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Cross-deployment summary for a project."""
    project_id = _require_project_id(project_id)
    await require_project_access(db, request, project_id, min_role="viewer")
    return await deployment_service.get_deployment_overview(db, project_id)


@router.get("/deployments/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(
    deployment_id: str,
    request: Request,
    project_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get a single deployment by ID."""
    deployment = await _get_active_project_deployment_or_404(
        db, request, deployment_id, project_id, min_role="viewer"
    )
    return DeploymentResponse.from_model(deployment)


@router.delete("/deployments/{deployment_id}", status_code=204)
async def delete_deployment(
    deployment_id: str,
    request: Request,
    project_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Delete a deployment and its project-owned conversation history."""
    deployment = await _get_active_project_deployment_or_404(
        db, request, deployment_id, project_id, min_role="researcher"
    )
    deleted = await deployment_service.delete_deployment(
        db,
        deployment_id,
        project_id=deployment.project_id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


@router.get("/deployments/{deployment_id}/analytics")
async def deployment_analytics(
    deployment_id: str,
    request: Request,
    project_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Full analytics for a deployment — response rates, per-question stats, completion times."""
    deployment = await _get_active_project_deployment_or_404(
        db, request, deployment_id, project_id, min_role="viewer"
    )

    analytics = await deployment_service.get_deployment_analytics(
        db,
        deployment_id,
        project_id=deployment.project_id,
    )
    if not analytics:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return analytics


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


@router.post("/deployments/{deployment_id}/activate")
async def activate_deployment(
    deployment_id: str,
    request: Request,
    project_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Activate a deployment — starts accepting participant responses."""
    deployment = await _get_active_project_deployment_or_404(
        db, request, deployment_id, project_id, min_role="researcher"
    )
    await get_active_project_or_404(db, request, deployment.project_id, min_role="researcher")

    try:
        result = await deployment_service.activate_deployment(
            db,
            deployment_id,
            project_id=deployment.project_id,
        )

        # Broadcast progress update
        try:
            from app.api.websocket import broadcast_deployment_progress

            analytics = await deployment_service.get_deployment_analytics(
                db,
                deployment_id,
                project_id=deployment.project_id,
            )
            await broadcast_deployment_progress(deployment_id, analytics)
        except Exception:
            pass  # Never block activation on broadcast failure

        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/deployments/{deployment_id}/pause")
async def pause_deployment(
    deployment_id: str,
    request: Request,
    project_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Pause a deployment — stops sending new questions to participants."""
    deployment = await _get_active_project_deployment_or_404(
        db, request, deployment_id, project_id, min_role="researcher"
    )

    try:
        return await deployment_service.pause_deployment(
            db,
            deployment_id,
            project_id=deployment.project_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/deployments/{deployment_id}/complete")
async def complete_deployment(
    deployment_id: str,
    request: Request,
    project_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Complete a deployment — marks it finished and triggers final analysis."""
    deployment = await _get_active_project_deployment_or_404(
        db, request, deployment_id, project_id, min_role="researcher"
    )

    try:
        result = await deployment_service.complete_deployment(
            db,
            deployment_id,
            project_id=deployment.project_id,
        )

        # Broadcast final progress
        try:
            from app.api.websocket import broadcast_deployment_progress

            analytics = await deployment_service.get_deployment_analytics(
                db,
                deployment_id,
                project_id=deployment.project_id,
            )
            await broadcast_deployment_progress(deployment_id, analytics)
        except Exception:
            pass

        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ---------------------------------------------------------------------------
# Response handling
# ---------------------------------------------------------------------------


@router.post("/deployments/{deployment_id}/respond")
async def handle_response(
    deployment_id: str,
    data: HandleResponseRequest,
    request: Request,
    project_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Process a participant response and return the next action.

    Returns:
    - action: next_question | ask_followup | complete | error
    - question: (if next_question or ask_followup) the text to send
    - thank_you: (if complete) the closing message
    """
    deployment = await _get_active_project_deployment_or_404(
        db, request, deployment_id, project_id, min_role="researcher"
    )
    await get_active_project_or_404(db, request, deployment.project_id, min_role="researcher")
    await _get_project_deployment_conversation_or_404(db, deployment, data.conversation_id)

    result = await deployment_service.handle_response(
        db=db,
        deployment_id=deployment_id,
        conversation_id=data.conversation_id,
        message_text=data.message_text,
        project_id=deployment.project_id,
    )

    # Broadcast events based on the action
    try:
        from app.api.websocket import (
            broadcast_deployment_finding,
            broadcast_deployment_progress,
            broadcast_deployment_response,
        )

        await broadcast_deployment_response(
            deployment_id,
            data.conversation_id,
            {"action": result.get("action"), "text": data.message_text[:200]},
        )

        if result.get("nugget_id"):
            await broadcast_deployment_finding(
                deployment_id,
                "nugget",
                {"nugget_id": result["nugget_id"]},
            )

        if result.get("action") == "complete":
            analytics = await deployment_service.get_deployment_analytics(
                db,
                deployment_id,
                project_id=deployment.project_id,
            )
            await broadcast_deployment_progress(deployment_id, analytics)
    except Exception:
        pass  # Never block response handling on broadcast failure

    return result


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------


@router.get("/deployments/{deployment_id}/conversations")
async def list_conversations(
    deployment_id: str,
    request: Request,
    project_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List all conversations for a deployment."""
    deployment = await _get_active_project_deployment_or_404(
        db, request, deployment_id, project_id, min_role="viewer"
    )

    conversations = await deployment_service.list_conversations(
        db,
        deployment_id,
        project_id=deployment.project_id,
    )
    return [c.to_dict() for c in conversations]


@router.get("/deployments/{deployment_id}/conversations/{conversation_id}")
async def get_conversation(
    deployment_id: str,
    conversation_id: str,
    request: Request,
    project_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get a single conversation detail."""
    deployment = await _get_active_project_deployment_or_404(
        db, request, deployment_id, project_id, min_role="viewer"
    )

    conversation = await _get_project_deployment_conversation_or_404(
        db, deployment, conversation_id
    )
    return conversation.to_dict()


@router.get("/deployments/{deployment_id}/conversations/{conversation_id}/transcript")
async def get_conversation_transcript(
    deployment_id: str,
    conversation_id: str,
    request: Request,
    project_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get the full message transcript for a conversation."""
    deployment = await _get_active_project_deployment_or_404(
        db, request, deployment_id, project_id, min_role="viewer"
    )

    conversation = await _get_project_deployment_conversation_or_404(
        db, deployment, conversation_id
    )
    transcript = await deployment_service.get_conversation_transcript(
        db,
        conversation_id,
        deployment_id=deployment.id,
        project_id=deployment.project_id,
    )
    return {
        "deployment_id": deployment_id,
        "conversation_id": conversation_id,
        "participant_id": conversation.participant_id,
        "participant_name": conversation.participant_name,
        "state": conversation.state,
        "messages": transcript,
        "message_count": len(transcript),
    }
