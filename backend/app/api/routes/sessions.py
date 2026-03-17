"""Chat session management API routes."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.session import ChatSession, InferencePreset, INFERENCE_PRESETS
from app.models.message import Message

router = APIRouter()


class CreateSessionRequest(BaseModel):
    project_id: str
    title: str = "New Chat"
    agent_id: str | None = None
    model_override: str | None = None
    inference_preset: str = "medium"


class UpdateSessionRequest(BaseModel):
    title: str | None = None
    agent_id: str | None = None
    model_override: str | None = None
    inference_preset: str | None = None
    custom_temperature: float | None = None
    custom_max_tokens: int | None = None
    custom_context_window: int | None = None
    starred: bool | None = None
    archived: bool | None = None


@router.get("/sessions/{project_id}")
async def list_sessions(project_id: str, include_archived: bool = False, db: AsyncSession = Depends(get_db)):
    """List all chat sessions for a project."""
    query = select(ChatSession).where(ChatSession.project_id == project_id)
    if not include_archived:
        query = query.where(ChatSession.archived == False)
    query = query.order_by(ChatSession.starred.desc(), ChatSession.last_message_at.desc().nullslast())
    result = await db.execute(query)
    sessions = result.scalars().all()
    return {"sessions": [s.to_dict() for s in sessions]}


@router.post("/sessions", status_code=201)
async def create_session(data: CreateSessionRequest, db: AsyncSession = Depends(get_db)):
    """Create a new chat session."""
    preset = InferencePreset.MEDIUM
    try:
        preset = InferencePreset(data.inference_preset)
    except ValueError:
        pass

    session = ChatSession(
        id=str(uuid.uuid4()),
        project_id=data.project_id,
        title=data.title,
        agent_id=data.agent_id,
        model_override=data.model_override,
        inference_preset=preset,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session.to_dict()


@router.get("/sessions/detail/{session_id}")
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific session with its messages."""
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

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
async def update_session(session_id: str, data: UpdateSessionRequest, db: AsyncSession = Depends(get_db)):
    """Update a chat session."""
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    updates = data.model_dump(exclude_unset=True)
    if "inference_preset" in updates:
        try:
            updates["inference_preset"] = InferencePreset(updates["inference_preset"])
        except ValueError:
            pass

    for key, value in updates.items():
        setattr(session, key, value)

    await db.commit()
    await db.refresh(session)
    return session.to_dict()


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a chat session and its messages."""
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await db.delete(session)
    await db.commit()


@router.post("/sessions/{session_id}/star")
async def toggle_star(session_id: str, db: AsyncSession = Depends(get_db)):
    """Toggle starred status."""
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.starred = not session.starred
    await db.commit()
    return {"starred": session.starred}


@router.get("/inference-presets")
async def get_inference_presets():
    """Get available hardware/inference presets."""
    return {"presets": INFERENCE_PRESETS}


@router.get("/sessions/{project_id}/ensure-default")
async def ensure_default_session(project_id: str, db: AsyncSession = Depends(get_db)):
    """Ensure a default session exists for a project. Returns or creates one."""
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.project_id == project_id, ChatSession.archived == False)
        .order_by(ChatSession.created_at.asc())
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
