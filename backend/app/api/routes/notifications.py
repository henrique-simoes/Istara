"""Notification CRUD, read-status management, and preference API routes."""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.notification import Notification, NotificationPreference

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic request models
# ---------------------------------------------------------------------------


class MarkAllReadRequest(BaseModel):
    """Optional body for mark-all-read — can scope to a project."""

    project_id: str | None = None


class PreferenceItem(BaseModel):
    """A single notification preference entry."""

    category: str
    show_toast: bool = True
    show_center: bool = True
    email_forward: bool = False


class UpdatePreferencesRequest(BaseModel):
    """Request body for bulk-updating notification preferences."""

    preferences: list[PreferenceItem]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/notifications")
async def list_notifications(
    category: str | None = None,
    agent_id: str | None = None,
    project_id: str | None = None,
    severity: str | None = None,
    read: bool | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
    date_from: str | None = None,
    date_to: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Paginated notification list with optional filters."""
    query = select(Notification).order_by(Notification.created_at.desc())

    if category:
        query = query.where(Notification.category == category)
    if agent_id:
        query = query.where(Notification.agent_id == agent_id)
    if project_id:
        query = query.where(Notification.project_id == project_id)
    if severity:
        query = query.where(Notification.severity == severity)
    if read is not None:
        query = query.where(Notification.read.is_(read))
    if search:
        like_pattern = f"%{search}%"
        query = query.where(
            Notification.title.ilike(like_pattern)
            | Notification.message.ilike(like_pattern)
        )
    if date_from:
        try:
            dt_from = datetime.fromisoformat(date_from)
            query = query.where(Notification.created_at >= dt_from)
        except ValueError:
            pass
    if date_to:
        try:
            dt_to = datetime.fromisoformat(date_to)
            query = query.where(Notification.created_at <= dt_to)
        except ValueError:
            pass

    # Total count for pagination
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    notifications = [n.to_dict() for n in result.scalars().all()]

    return {
        "notifications": notifications,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/notifications/unread-count")
async def unread_count(db: AsyncSession = Depends(get_db)):
    """Return the number of unread notifications."""
    count = (
        await db.execute(
            select(func.count(Notification.id)).where(Notification.read.is_(False))
        )
    ).scalar() or 0
    return {"count": count}


@router.post("/notifications/{notification_id}/read")
async def mark_read(notification_id: str, db: AsyncSession = Depends(get_db)):
    """Mark a single notification as read."""
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.read = True
    await db.commit()
    return {"success": True}


@router.post("/notifications/read-all")
async def mark_all_read(
    data: MarkAllReadRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Mark all unread notifications as read, optionally scoped to a project."""
    stmt = (
        update(Notification)
        .where(Notification.read.is_(False))
    )
    if data and data.project_id:
        stmt = stmt.where(Notification.project_id == data.project_id)

    stmt = stmt.values(read=True)
    result = await db.execute(stmt)
    await db.commit()

    return {"success": True, "count": result.rowcount}


@router.delete("/notifications/{notification_id}", status_code=204)
async def delete_notification(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a single notification."""
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    await db.delete(notification)
    await db.commit()


@router.get("/notifications/preferences")
async def get_preferences(db: AsyncSession = Depends(get_db)):
    """Get all notification preferences."""
    result = await db.execute(
        select(NotificationPreference).order_by(NotificationPreference.category)
    )
    prefs = [p.to_dict() for p in result.scalars().all()]
    return {"preferences": prefs}


@router.put("/notifications/preferences")
async def update_preferences(
    data: UpdatePreferencesRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create or update notification preferences by category."""
    updated: list[dict] = []

    for item in data.preferences:
        # Check if preference for this category already exists
        result = await db.execute(
            select(NotificationPreference).where(
                NotificationPreference.category == item.category
            )
        )
        pref = result.scalar_one_or_none()

        if pref:
            pref.show_toast = item.show_toast
            pref.show_center = item.show_center
            pref.email_forward = item.email_forward
        else:
            pref = NotificationPreference(
                category=item.category,
                show_toast=item.show_toast,
                show_center=item.show_center,
                email_forward=item.email_forward,
            )
            db.add(pref)

        await db.flush()
        updated.append(pref.to_dict())

    await db.commit()
    return {"preferences": updated}
