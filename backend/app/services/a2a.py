"""Agent-to-Agent (A2A) communication protocol."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import A2AMessage

logger = logging.getLogger(__name__)


async def send_message(
    db: AsyncSession,
    from_agent_id: str,
    to_agent_id: str | None,
    message_type: str,
    content: str,
    metadata: dict | None = None,
) -> dict:
    """Send an A2A message between agents."""
    msg = A2AMessage(
        id=str(uuid.uuid4()),
        from_agent_id=from_agent_id,
        to_agent_id=to_agent_id,
        message_type=message_type,
        content=content,
        extra_data=json.dumps(metadata or {}),
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    result = msg.to_dict()

    # Broadcast via WebSocket
    try:
        from app.api.websocket import manager as ws_manager
        await ws_manager.broadcast("a2a_message", result)
    except Exception:
        pass

    logger.info(f"A2A: {from_agent_id} -> {to_agent_id or 'broadcast'}: {message_type}")
    return result


async def send_task_request(
    db: AsyncSession,
    from_agent_id: str,
    to_agent_id: str,
    task_title: str,
    task_description: str,
    project_id: str,
    skill_name: str | None = None,
    priority: str = "medium",
) -> dict:
    """Send a task request via A2A — creates a task assigned to the target agent."""
    from app.models.task import Task, TaskStatus
    import uuid as _uuid

    # Create the task assigned to the target agent
    task = Task(
        id=str(_uuid.uuid4()),
        project_id=project_id,
        title=task_title,
        description=task_description,
        skill_name=skill_name,
        agent_id=to_agent_id,
        priority=priority,
        status=TaskStatus.BACKLOG,
    )
    db.add(task)

    # Send the A2A notification
    msg_result = await send_message(
        db=db,
        from_agent_id=from_agent_id,
        to_agent_id=to_agent_id,
        message_type="task_request",
        content=f"New task assigned: {task_title}",
        metadata={
            "task_id": task.id,
            "project_id": project_id,
            "skill_name": skill_name,
        },
    )

    await db.commit()
    logger.info(f"Task request: {from_agent_id} -> {to_agent_id}: {task_title}")
    return {"task_id": task.id, "message": msg_result}


async def get_messages(
    db: AsyncSession,
    agent_id: str,
    limit: int = 50,
    unread_only: bool = False,
) -> list[dict]:
    """Get messages for an agent (sent to it or broadcast)."""
    query = select(A2AMessage).where(
        or_(
            A2AMessage.to_agent_id == agent_id,
            A2AMessage.to_agent_id == None,  # broadcasts
            A2AMessage.from_agent_id == agent_id,
        )
    )
    if unread_only:
        query = query.where(A2AMessage.read == False)

    query = query.order_by(A2AMessage.created_at.desc()).limit(limit)
    result = await db.execute(query)
    return [m.to_dict() for m in result.scalars().all()]


async def get_conversation(
    db: AsyncSession,
    agent_a: str,
    agent_b: str,
    limit: int = 50,
) -> list[dict]:
    """Get messages between two specific agents."""
    query = select(A2AMessage).where(
        or_(
            (A2AMessage.from_agent_id == agent_a) & (A2AMessage.to_agent_id == agent_b),
            (A2AMessage.from_agent_id == agent_b) & (A2AMessage.to_agent_id == agent_a),
        )
    ).order_by(A2AMessage.created_at.desc()).limit(limit)

    result = await db.execute(query)
    return [m.to_dict() for m in result.scalars().all()]


async def get_conversation_thread(
    db: AsyncSession,
    context_id: str,
    limit: int = 20,
) -> list[dict]:
    """Get all messages in a conversation thread by context_id.

    context_id groups related A2A messages into a multi-turn thread.
    Messages are returned in chronological order (oldest first).
    """
    # Context ID is stored in extra_data JSON as "context_id"
    # We query all messages and filter by context_id in extra_data
    query = select(A2AMessage).order_by(A2AMessage.created_at.asc()).limit(limit * 3)
    result = await db.execute(query)
    thread = []
    for msg in result.scalars().all():
        try:
            extra = json.loads(msg.extra_data or "{}") if isinstance(msg.extra_data, str) else (msg.extra_data or {})
            if extra.get("context_id") == context_id or msg.id == context_id:
                thread.append(msg.to_dict())
        except Exception:
            continue
    return thread[:limit]


async def get_full_log(db: AsyncSession, limit: int = 100) -> list[dict]:
    """Get the full A2A message log."""
    query = select(A2AMessage).order_by(A2AMessage.created_at.desc()).limit(limit)
    result = await db.execute(query)
    return [m.to_dict() for m in result.scalars().all()]


async def mark_read(db: AsyncSession, message_id: str) -> bool:
    """Mark a message as read."""
    result = await db.execute(
        select(A2AMessage).where(A2AMessage.id == message_id)
    )
    msg = result.scalar_one_or_none()
    if not msg:
        return False
    msg.read = True
    await db.commit()
    return True
