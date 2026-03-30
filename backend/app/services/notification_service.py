"""Notification service — persistence, queries, and preference management."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import async_session
from app.models.notification import Notification, NotificationPreference

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Event-type -> notification metadata mapping
# ---------------------------------------------------------------------------

EVENT_METADATA: dict[str, dict[str, Any] | None] = {
    "agent_status": {
        "category": "agent_status",
        "severity": "info",
        "title_template": "Agent {status}",
    },
    "task_progress": {
        "category": "task_progress",
        "severity": "info",
        "title_template": "Task progress",
    },
    "finding_created": {
        "category": "finding_created",
        "severity": "success",
        "title_template": "New findings",
    },
    "file_processed": {
        "category": "file_processed",
        "severity": "info",
        "title_template": "File processed",
    },
    "suggestion": {
        "category": "suggestion",
        "severity": "info",
        "title_template": "Suggestion",
        "action_type": "navigate",
        "action_target": "chat",
    },
    "resource_throttle": {
        "category": "resource_throttle",
        "severity": "warning",
        "title_template": "Resource constraint",
    },
    "task_queue_update": {
        "category": "task_progress",
        "severity": "info",
        "title_template": "Task queue updated",
    },
    "document_created": {
        "category": "document",
        "severity": "info",
        "title_template": "Document created",
    },
    "document_updated": {
        "category": "document",
        "severity": "info",
        "title_template": "Document updated",
    },
    "scheduled_reminder": {
        "category": "scheduled_reminder",
        "severity": "info",
        "title_template": "Scheduled reminder",
    },
    "loop_execution": {
        "category": "loop_execution",
        "severity": "info",
        "title_template": "Loop executed",
    },
    "update_available": {
        "category": "system",
        "severity": "info",
        "title_template": "Software Update Available",
        "action_type": "navigate",
        "action_target": "settings",
    },
    "update_started": {
        "category": "system",
        "severity": "warning",
        "title_template": "Istara is updating",
    },
    "update_failed": {
        "category": "system",
        "severity": "error",
        "title_template": "Update failed",
    },
    # Skip — would be recursive
    "notification_created": None,
    # Skip — too frequent
    "heartbeat_batch": None,
    # Skip — internal
    "pong": None,
    "ping": None,
    "connected": None,
}


# ---------------------------------------------------------------------------
# Persist notification
# ---------------------------------------------------------------------------

async def persist_notification(event_type: str, data: dict) -> Optional[Notification]:
    """Map an event type + data to a Notification record and persist it.

    Returns the created Notification, or None if the event type is skipped.
    """
    meta = EVENT_METADATA.get(event_type)
    if meta is None:
        # Explicitly skipped or unknown — do not persist
        return None

    title_template = meta.get("title_template", event_type)
    try:
        title = title_template.format(**data)
    except (KeyError, IndexError):
        title = title_template

    message = data.get("message", "") or data.get("details", "") or ""
    if not message and data:
        # Build a brief message from the data keys
        parts = []
        for key in ("status", "filename", "finding_type", "reason", "title"):
            if key in data:
                parts.append(f"{key}={data[key]}")
        message = ", ".join(parts[:3])

    notification = Notification(
        id=str(uuid.uuid4()),
        type=event_type,
        title=title,
        message=str(message)[:2000],
        category=meta.get("category", "system"),
        agent_id=data.get("agent_id"),
        project_id=data.get("project_id"),
        severity=meta.get("severity", "info"),
        read=False,
        action_type=meta.get("action_type", ""),
        action_target=meta.get("action_target", ""),
        metadata_json=json.dumps(data, default=str),
        created_at=datetime.now(timezone.utc),
    )

    async with async_session() as db:
        db.add(notification)
        await db.commit()

    return notification


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

async def list_notifications(
    db: AsyncSession,
    *,
    category: Optional[str] = None,
    agent_id: Optional[str] = None,
    project_id: Optional[str] = None,
    severity: Optional[str] = None,
    read: Optional[bool] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> dict:
    """Paginated notification query with filters.

    Returns ``{"items": [...], "total": int, "page": int, "page_size": int}``.
    """
    q = select(Notification).order_by(Notification.created_at.desc())

    if category:
        q = q.where(Notification.category == category)
    if agent_id:
        q = q.where(Notification.agent_id == agent_id)
    if project_id:
        q = q.where(Notification.project_id == project_id)
    if severity:
        q = q.where(Notification.severity == severity)
    if read is not None:
        q = q.where(Notification.read == read)
    if search:
        pattern = f"%{search}%"
        q = q.where(
            Notification.title.ilike(pattern) | Notification.message.ilike(pattern)
        )
    if date_from:
        q = q.where(Notification.created_at >= date_from)
    if date_to:
        q = q.where(Notification.created_at <= date_to)

    # Count query
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Paginate
    offset = (max(page, 1) - 1) * page_size
    q = q.offset(offset).limit(page_size)

    result = await db.execute(q)
    items = [n.to_dict() for n in result.scalars().all()]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def mark_read(db: AsyncSession, notification_id: str) -> bool:
    """Mark a single notification as read. Returns True if found."""
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    notif = result.scalar_one_or_none()
    if not notif:
        return False
    notif.read = True
    await db.commit()
    return True


async def mark_all_read(db: AsyncSession, project_id: Optional[str] = None) -> int:
    """Mark all unread notifications as read. Returns count updated."""
    stmt = update(Notification).where(Notification.read.is_(False))
    if project_id:
        stmt = stmt.where(Notification.project_id == project_id)
    stmt = stmt.values(read=True)
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount  # type: ignore[return-value]


async def delete_notification(db: AsyncSession, notification_id: str) -> bool:
    """Delete a notification by id. Returns True if found and deleted."""
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    notif = result.scalar_one_or_none()
    if not notif:
        return False
    await db.delete(notif)
    await db.commit()
    return True


async def get_unread_count(db: AsyncSession, project_id: Optional[str] = None) -> int:
    """Count unread notifications, optionally filtered by project."""
    q = select(func.count(Notification.id)).where(Notification.read.is_(False))
    if project_id:
        q = q.where(Notification.project_id == project_id)
    result = await db.execute(q)
    return result.scalar() or 0


# ---------------------------------------------------------------------------
# Preferences
# ---------------------------------------------------------------------------

async def get_preferences(db: AsyncSession) -> list[dict]:
    """Return all notification preferences."""
    result = await db.execute(
        select(NotificationPreference).order_by(NotificationPreference.category)
    )
    return [p.to_dict() for p in result.scalars().all()]


async def update_preference(
    db: AsyncSession,
    category: str,
    *,
    show_toast: bool = True,
    show_center: bool = True,
    email_forward: bool = False,
) -> dict:
    """Create or update a notification preference for a category."""
    result = await db.execute(
        select(NotificationPreference).where(NotificationPreference.category == category)
    )
    pref = result.scalar_one_or_none()

    if pref:
        pref.show_toast = show_toast
        pref.show_center = show_center
        pref.email_forward = email_forward
        pref.updated_at = datetime.now(timezone.utc)
    else:
        pref = NotificationPreference(
            id=str(uuid.uuid4()),
            category=category,
            show_toast=show_toast,
            show_center=show_center,
            email_forward=email_forward,
        )
        db.add(pref)

    await db.commit()
    return pref.to_dict()
