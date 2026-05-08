"""Chat session management API routes."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.session import ChatSession, InferencePreset, INFERENCE_PRESETS
from app.models.message import Message
from app.core.permissions import require_project_access
from app.core.llm_thinking import ThinkingMode, normalize_thinking_mode

router = APIRouter()


class CreateSessionRequest(BaseModel):
    project_id: str = Field(..., min_length=1, max_length=36)
    title: str = Field(default="New Chat", min_length=1, max_length=255)
    agent_id: str | None = Field(default=None, max_length=255)
    model_override: str | None = Field(default=None, max_length=255)
    inference_preset: InferencePreset = InferencePreset.MEDIUM
    thinking_mode: ThinkingMode = "server_default"

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("Title cannot be blank")
        return title


class UpdateSessionRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    agent_id: str | None = Field(default=None, max_length=255)
    model_override: str | None = Field(default=None, max_length=255)
    inference_preset: InferencePreset | None = None
    custom_temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    custom_max_tokens: int | None = Field(default=None, ge=1, le=65536)
    custom_context_window: int | None = Field(default=None, ge=512, le=262144)
    thinking_mode: ThinkingMode | None = None
    starred: bool | None = None
    archived: bool | None = None

    @field_validator("title")
    @classmethod
    def normalize_optional_title(cls, value: str | None) -> str | None:
        if value is None:
            return value
        title = value.strip()
        if not title:
            raise ValueError("Title cannot be blank")
        return title


@router.get("/sessions/{project_id}")
async def list_sessions(
    project_id: str,
    request: Request,
    include_archived: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """List all chat sessions for a project."""
    await require_project_access(db, request, project_id, min_role="viewer")
    query = select(ChatSession).where(ChatSession.project_id == project_id)
    if not include_archived:
        query = query.where(ChatSession.archived == False)
    query = query.order_by(ChatSession.starred.desc(), ChatSession.last_message_at.desc().nullslast())
    result = await db.execute(query)
    sessions = result.scalars().all()
    return {"sessions": [s.to_dict() for s in sessions]}


@router.post("/sessions", status_code=201)
async def create_session(data: CreateSessionRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Create a new chat session."""
    await require_project_access(db, request, data.project_id, min_role="researcher")

    session = ChatSession(
        id=str(uuid.uuid4()),
        project_id=data.project_id,
        title=data.title,
        agent_id=data.agent_id,
        model_override=data.model_override,
        inference_preset=data.inference_preset,
        thinking_mode=normalize_thinking_mode(data.thinking_mode),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session.to_dict()


@router.get("/sessions/detail/{session_id}")
async def get_session(session_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Get a specific session with its messages."""
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await require_project_access(db, request, session.project_id, min_role="viewer")

    # Get messages
    msg_result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
    )
    messages = msg_result.scalars().all()

    data = session.to_dict()
    data["messages"] = [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "agent_id": m.agent_id,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in messages
    ]
    return data


@router.patch("/sessions/{session_id}")
async def update_session(
    session_id: str,
    data: UpdateSessionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Update a chat session."""
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await require_project_access(db, request, session.project_id, min_role="researcher")

    updates = data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        if key == "thinking_mode":
            value = normalize_thinking_mode(value)
        setattr(session, key, value)

    await db.commit()
    await db.refresh(session)
    return session.to_dict()


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(session_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Delete a chat session and its messages."""
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await require_project_access(db, request, session.project_id, min_role="researcher")

    # Clean up DAG nodes (no FK constraint on session_id)
    from app.models.context_dag import ContextDAGNode
    await db.execute(
        delete(ContextDAGNode).where(ContextDAGNode.session_id == session_id)
    )

    await db.delete(session)
    await db.commit()


@router.post("/sessions/{session_id}/star")
async def toggle_star(session_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Toggle starred status."""
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await require_project_access(db, request, session.project_id, min_role="researcher")

    session.starred = not session.starred
    await db.commit()
    return {"starred": session.starred}


@router.get("/inference-presets")
async def get_inference_presets():
    """Get available hardware/inference presets."""
    return {"presets": INFERENCE_PRESETS}


@router.get("/sessions/{project_id}/ensure-default")
async def ensure_default_session(project_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Ensure a default session exists for a project. Returns or creates one."""
    await require_project_access(db, request, project_id, min_role="researcher")
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.project_id == project_id, ChatSession.archived == False)
        .order_by(ChatSession.last_message_at.desc().nullslast(), ChatSession.created_at.desc())
        .limit(1)
    )
    session = result.scalar_one_or_none()

    if not session:
        session = ChatSession(
            id=str(uuid.uuid4()),
            project_id=project_id,
            title="General",
            inference_preset=InferencePreset.MEDIUM,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

    return session.to_dict()
