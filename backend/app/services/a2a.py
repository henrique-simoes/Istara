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


def _message_metadata(message: A2AMessage) -> dict:
    try:
        if isinstance(message.extra_data, str):
            parsed = json.loads(message.extra_data or "{}")
            return parsed if isinstance(parsed, dict) else {}
        if isinstance(message.extra_data, dict):
            return message.extra_data
    except (json.JSONDecodeError, TypeError):
        return {}
    return {}


def _metadata_text(metadata: dict, *keys: str) -> str | None:
    for key in keys:
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _message_project_id(message: A2AMessage) -> str | None:
    return _metadata_text(_message_metadata(message), "project_id", "projectId")


def _message_task_id(message: A2AMessage) -> str | None:
    return _metadata_text(_message_metadata(message), "task_id", "taskId")


def _message_to_dict(message: A2AMessage, project_id: str | None = None) -> dict:
    payload = message.to_dict()
    resolved_project_id = project_id or _message_project_id(message)
    if resolved_project_id:
        payload["project_id"] = resolved_project_id
        metadata = payload.get("metadata")
        if isinstance(metadata, dict):
            metadata.setdefault("project_id", resolved_project_id)
    return payload


def _project_scoped_fetch_limit(limit: int) -> int:
    return min(max(limit * 10, 200), 1000)


async def _filter_messages_by_project(
    db: AsyncSession,
    messages: list[A2AMessage],
    project_id: str,
) -> list[A2AMessage]:
    resolved_project_ids = await _resolve_message_project_ids(db, messages)
    return [
        message
        for message in messages
        if resolved_project_ids.get(str(message.id)) == project_id
    ]


async def _resolve_message_project_ids(
    db: AsyncSession,
    messages: list[A2AMessage],
) -> dict[str, str]:
    """Resolve message project identity from metadata, then task fallback."""
    resolved: dict[str, str] = {}
    task_ids = {
        task_id
        for message in messages
        if _message_project_id(message) is None
        for task_id in [_message_task_id(message)]
        if task_id
    }
    for message in messages:
        message_project_id = _message_project_id(message)
        if message_project_id:
            resolved[str(message.id)] = message_project_id

    task_project_ids: dict[str, str] = {}
    if task_ids:
        from app.models.task import Task

        result = await db.execute(
            select(Task.id, Task.project_id).where(Task.id.in_(task_ids))
        )
        task_project_ids = {
            str(task_id): str(task_project_id)
            for task_id, task_project_id in result.all()
            if task_project_id
        }

    for message in messages:
        if str(message.id) in resolved:
            continue
        task_id = _message_task_id(message)
        if task_id and task_project_ids.get(task_id):
            resolved[str(message.id)] = task_project_ids[task_id]

    return resolved


async def _agent_scope_project_id(db: AsyncSession, agent_id: str) -> str | None:
    from app.models.agent import Agent

    result = await db.execute(
        select(Agent.project_id, Agent.scope).where(Agent.id == agent_id)
    )
    row = result.first()
    if not row:
        return None
    project_id, scope = row
    if scope == "project" and project_id:
        return str(project_id)
    return None


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
    - finding, request, broadcast, a2a_task
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
        "finding",         # Research finding broadcast/notification
        "request",         # Generic request preserved for legacy agents
        "broadcast",       # Explicit all-agent announcement
        "a2a_task",        # JSON-RPC task envelope
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

    result = _message_to_dict(msg)

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
    project_id: str | None = None,
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

    fetch_limit = _project_scoped_fetch_limit(limit) if project_id else limit
    query = query.order_by(A2AMessage.created_at.desc()).limit(fetch_limit)
    result = await db.execute(query)
    messages = list(result.scalars().all())
    if project_id:
        messages = await _filter_messages_by_project(db, messages, project_id)
        return [_message_to_dict(m, project_id=project_id) for m in messages[:limit]]
    return [_message_to_dict(m) for m in messages[:limit]]


async def get_project_inbox(
    db: AsyncSession,
    agent_id: str,
    limit: int = 50,
    unread_only: bool = True,
) -> list[dict]:
    """Get project-resolved inbox messages for background agent processing.

    Global/unresolvable messages are excluded from autonomous processing. Project-scoped
    agents only receive messages for their own project; universal agents may receive
    multiple projects, with every returned message carrying a resolved project_id.
    """
    query = select(A2AMessage).where(
        or_(
            A2AMessage.to_agent_id == agent_id,
            A2AMessage.to_agent_id == None,  # broadcasts
            A2AMessage.from_agent_id == agent_id,
        )
    )
    if unread_only:
        query = query.where(A2AMessage.read == False)

    query = query.order_by(A2AMessage.created_at.desc()).limit(
        _project_scoped_fetch_limit(limit)
    )
    result = await db.execute(query)
    messages = list(result.scalars().all())
    resolved_project_ids = await _resolve_message_project_ids(db, messages)
    scoped_agent_project_id = await _agent_scope_project_id(db, agent_id)

    inbox: list[dict] = []
    for message in messages:
        resolved_project_id = resolved_project_ids.get(str(message.id))
        if not resolved_project_id:
            continue
        if scoped_agent_project_id and resolved_project_id != scoped_agent_project_id:
            continue
        inbox.append(_message_to_dict(message, project_id=resolved_project_id))
        if len(inbox) >= limit:
            break

    return inbox


async def get_conversation(
    db: AsyncSession,
    agent_a: str,
    agent_b: str,
    *,
    project_id: str,
    limit: int = 50,
) -> list[dict]:
    """Get messages between two specific agents."""
    query = select(A2AMessage).where(
        or_(
            (A2AMessage.from_agent_id == agent_a) & (A2AMessage.to_agent_id == agent_b),
            (A2AMessage.from_agent_id == agent_b) & (A2AMessage.to_agent_id == agent_a),
        )
    ).order_by(A2AMessage.created_at.desc()).limit(_project_scoped_fetch_limit(limit))

    result = await db.execute(query)
    messages = await _filter_messages_by_project(db, list(result.scalars().all()), project_id)
    return [_message_to_dict(m, project_id=project_id) for m in messages[:limit]]


async def get_conversation_thread(
    db: AsyncSession,
    context_id: str,
    *,
    project_id: str,
    limit: int = 20,
) -> list[dict]:
    """Get all messages in a conversation thread by context_id.

    context_id groups related A2A messages into a multi-turn thread.
    Messages are returned in chronological order (oldest first).
    """
    # Context ID is stored in extra_data JSON as "context_id"
    # We query all messages and filter by context_id in extra_data
    query = select(A2AMessage).order_by(A2AMessage.created_at.asc()).limit(
        _project_scoped_fetch_limit(limit)
    )
    result = await db.execute(query)
    thread = []
    for msg in result.scalars().all():
        try:
            extra = json.loads(msg.extra_data or "{}") if isinstance(msg.extra_data, str) else (msg.extra_data or {})
            if extra.get("context_id") == context_id or msg.id == context_id:
                thread.append(msg)
        except Exception:
            continue
    thread = await _filter_messages_by_project(db, thread, project_id)
    return [_message_to_dict(m, project_id=project_id) for m in thread[:limit]]


async def get_full_log(
    db: AsyncSession,
    limit: int = 100,
    project_id: str | None = None,
) -> list[dict]:
    """Get the full A2A message log."""
    fetch_limit = _project_scoped_fetch_limit(limit) if project_id else limit
    query = select(A2AMessage).order_by(A2AMessage.created_at.desc()).limit(fetch_limit)
    result = await db.execute(query)
    messages = list(result.scalars().all())
    if project_id:
        messages = await _filter_messages_by_project(db, messages, project_id)
        return [_message_to_dict(m, project_id=project_id) for m in messages[:limit]]
    return [_message_to_dict(m) for m in messages[:limit]]


async def mark_read(
    db: AsyncSession,
    message_id: str,
    project_id: str | None = None,
) -> bool:
    """Mark a message as read."""
    result = await db.execute(
        select(A2AMessage).where(A2AMessage.id == message_id)
    )
    msg = result.scalar_one_or_none()
    if not msg:
        return False
    if project_id:
        scoped = await _filter_messages_by_project(db, [msg], project_id)
        if not scoped:
            return False
    msg.read = True
    await db.commit()
    return True
