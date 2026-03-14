"""Chat API route — streaming LLM responses with RAG augmentation."""

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ollama import ollama
from app.core.rag import build_augmented_prompt, retrieve_context
from app.models.database import get_db
from app.models.message import Message
from app.models.project import Project

router = APIRouter()


class ChatRequest(BaseModel):
    """Chat request body."""

    message: str
    project_id: str
    include_history: bool = True
    max_history: int = 20


class ChatMessage(BaseModel):
    """Chat message response."""

    id: str
    role: str
    content: str
    created_at: datetime


@router.post("/chat")
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Send a message and get a streaming response with RAG augmentation.

    The response is streamed as Server-Sent Events (SSE).
    """
    # Verify project exists
    result = await db.execute(select(Project).where(Project.id == request.project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Save user message
    user_msg = Message(
        id=str(uuid.uuid4()),
        project_id=request.project_id,
        role="user",
        content=request.message,
    )
    db.add(user_msg)
    await db.commit()

    # Retrieve context via RAG
    rag_context = await retrieve_context(request.project_id, request.message)

    # Build system prompt with context layers
    system_prompt = build_augmented_prompt(
        query=request.message,
        rag_context=rag_context,
        project_context=project.project_context or None,
        company_context=project.company_context or None,
    )

    # Build message history
    messages = []
    if request.include_history:
        history_result = await db.execute(
            select(Message)
            .where(Message.project_id == request.project_id)
            .order_by(Message.created_at.desc())
            .limit(request.max_history)
        )
        history = list(reversed(history_result.scalars().all()))

        for msg in history:
            if msg.role in ("user", "assistant"):
                messages.append({"role": msg.role, "content": msg.content})

    # Add current message if not already in history
    if not messages or messages[-1]["content"] != request.message:
        messages.append({"role": "user", "content": request.message})

    async def generate():
        """Stream the LLM response as SSE events."""
        full_response = []

        try:
            async for chunk in ollama.chat_stream(
                messages=messages,
                system=system_prompt,
            ):
                full_response.append(chunk)
                event_data = json.dumps({"type": "chunk", "content": chunk})
                yield f"data: {event_data}\n\n"

            # Save assistant response
            assistant_content = "".join(full_response)
            assistant_msg = Message(
                id=str(uuid.uuid4()),
                project_id=request.project_id,
                role="assistant",
                content=assistant_content,
            )
            db.add(assistant_msg)
            await db.commit()

            # Send completion event with sources
            sources = [
                {"source": r.source, "score": r.score, "page": r.page}
                for r in rag_context.retrieved
            ]
            done_data = json.dumps({
                "type": "done",
                "message_id": assistant_msg.id,
                "sources": sources,
            })
            yield f"data: {done_data}\n\n"

        except Exception as e:
            error_data = json.dumps({"type": "error", "message": str(e)})
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/chat/history/{project_id}")
async def get_chat_history(
    project_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[ChatMessage]:
    """Get chat history for a project."""
    result = await db.execute(
        select(Message)
        .where(Message.project_id == project_id)
        .order_by(Message.created_at.asc())
        .limit(limit)
    )
    messages = result.scalars().all()

    return [
        ChatMessage(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            created_at=msg.created_at,
        )
        for msg in messages
    ]
