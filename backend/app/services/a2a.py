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
    """Send an A2A message between agents.

    SECURITY: Validates message types against allowed enum values.
    Only whitelisted message types are permitted to prevent injection attacks.
    
    Allowed Types (per phase-alpha protocol):
    - consult, report, alert, delegate, debate_request, debate_response
    - collaboration_request, collaboration_response
    - task_request, status, response
    """
    # Validate message_type against allowed whitelist
    ALLOWED_MESSAGE_TYPES = {
        "consult",      # Request information/expertise
        "report",       # Send findings/status
        "alert",        # Urgent notification  
        "delegate",     # Assign task to other agent
        "debate_request",  # Multi-agent debate initiation
        "debate_response", # Debate round response
        "collaboration_request",   # Joint work request
        "collaboration_response",  # Joint work agreement/response
        "task_request",    # Task assignment via A2A
        "status",          # Agent status update
        "response",        # Response to previous message
    }

    # Normalize type (lowercase) for consistent validation
    normalized_type = message_type.lower().strip()
    
    if normalized_type not in ALLOWED_MESSAGE_TYPES:
        raise ValueError(
            f"Invalid message_type '{message_type}'. "
            f"Must be one of: {', '.join(sorted(ALLOWED_MESSAGE_TYPES))}"
        )

    msg = A2AMessage(
        id=str(uuid.uuid4()),
        from_agent_id=from_agent_id,
        to_agent_id=to_agent_id,
        message_type=normalized_type,  # Store normalized type
        content=content,
        extra_data=json.dumps(metadata or {}),
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    result = msg.to_dict()

    # Broadcast via WebSocket (if available)
    try:
        from app.api.websocket import manager as ws_manager
        await ws_manager.broadcast("a2a_message", result)
    except Exception:
        pass

    logger.info(
        f"A2A: {from_agent_id} -> {to_agent_id or 'broadcast'}: "
        f"{message_type} [{normalized_type}]"
    )
    return result


async def validate_delegate_message(msg: dict) -> tuple[bool, str]:
    """Validate a delegate message from JSON-RPC call before creating A2AMessage.

    Args:
        msg: The incoming JSON-RPC request object (must be dict)

    Returns:
        (is_valid, error_message_if_invalid)
    """
    if not isinstance(msg, dict):
        return False, "Delegate message must be a JSON object"

    # Required fields for delegate operation
    if "from" not in msg:
        return False, "Missing 'from' field in delegate message"
    if "to" not in msg:
        return False, "Missing 'to' field in delegate message"
    if "request" not in msg:
        return False, "Missing 'request' field in delegate message"

    from_agent = msg["from"]
    to_agent = msg["to"]
    request = msg["request"]

    # Validate agent IDs (UUID format)
    import re as _re_module
    
    if not _re_module.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', from_agent.replace('"', '')):
        return False, f"Invalid 'from' agent_id: {from_agent}"
        
    if not _re_module.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', to_agent.replace('"', '')):
        return False, f"Invalid 'to' agent_id: {to_agent}"

    # Validate request structure
    if "title" not in request:
        return False, "Delegate request missing 'title'"
    if "description" not in request:
        return False, "Delegate request missing 'description'"
    if "project_id" not in request:
        return False, "Delegate request missing 'project_id'"

    return True, "valid"


async def validate_message(message_type: str, body: dict) -> tuple[bool, str]:
    """Validate any A2A message type-specific validation before persistence.

    Centralized validation point for all message types.
    Extend this function as new message_types are added.

    Args:
        message_type: The normalized message type string
        body: The message body dict

    Returns:
        (is_valid, error_description)
    """
    if not isinstance(body, dict):
        return False, f"Body for '{message_type}' must be a JSON object"

    # Message-type specific validations
    if message_type == "delegate":
        is_valid, reason = await validate_delegate_message(body)
        return (is_valid, reason if not is_valid else None)

    if message_type == "task_request":
        if "skill_name" not in body:
            return False, "task_request requires 'skill_name'"
        if "priority" not in body and "agent_id" in body:
            # Priority required when requesting from specific agent
            return False, "task_request requires 'priority' when targeting specific agent"

    if message_type == "report":
        if "content" not in body:
            return False, "report requires 'content'"

    if message_type == "alert":
        # Alerts should have priority metadata  
        pass  # Currently allow all alerts with optional severity

    return True, None



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
