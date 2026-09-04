"""Notification CRUD, read-status management, and preference API routes."""

from __future__ import annotations

import logging
import math
from datetime import datetime
from typing import Iterable

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_project_access
from app.core.security_middleware import require_admin_from_request
from app.models.database import get_db
from app.models.notification import Notification, NotificationPreference

logger = logging.getLogger(__name__)

router = APIRouter()

ALLOWED_CATEGORIES = {
    "agent_status",
    "agent_promotion",
    "task_progress",
    "finding_created",
    "file_processed",
    "suggestion",
    "resource_throttle",
    "scheduled_reminder",
    "document",
    "loop_execution",
    "system",
}
ALLOWED_SEVERITIES = {"info", "warning", "error", "success"}


# ---------------------------------------------------------------------------
# Pydantic request models
# ---------------------------------------------------------------------------


class MarkAllReadRequest(BaseModel):
    """Project scope body for mark-all-read."""

    project_id: str | None = Field(default=None, max_length=36)


class PreferenceItem(BaseModel):
    """A single notification preference entry."""

    category: str = Field(min_length=1, max_length=50)
    show_toast: bool = True
    show_center: bool = True
    email_forward: bool = False


class UpdatePreferencesRequest(BaseModel):
    """Request body for bulk-updating notification preferences."""

    preferences: list[PreferenceItem] = Field(default_factory=list, max_length=50)


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _merge_filter_values(*values: str | None) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for value in values:
        for item in _split_csv(value):
            if item not in seen:
                seen.add(item)
                merged.append(item)
    return merged


def _validate_values(values: Iterable[str], allowed: set[str], label: str) -> list[str]:
    normalized = [value.strip() for value in values if value.strip()]
    invalid = [value for value in normalized if value not in allowed]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {label}: {', '.join(invalid)}",
        )
    return normalized


def _parse_iso_datetime(value: str | None, label: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid {label}") from exc


async def _require_notification_project_scope(
    db: AsyncSession,
    request: Request,
    project_id: str | None,
    *,
    min_role: str = "viewer",
) -> str:
    """Return the required active project id for project-facing notification APIs."""
    scoped_project_id = project_id.strip() if project_id else ""
    if not scoped_project_id:
        raise HTTPException(status_code=400, detail="project_id is required")

    await require_project_access(db, request, scoped_project_id, min_role=min_role)
    return scoped_project_id


async def _get_project_notification_or_404(
    db: AsyncSession,
    request: Request,
    notification_id: str,
    project_id: str | None,
    *,
    min_role: str,
) -> Notification:
    scoped_project_id = await _require_notification_project_scope(
        db,
        request,
        project_id,
        min_role=min_role,
    )
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.project_id == scoped_project_id,
        )
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/notifications")
async def list_notifications(
    request: Request,
    category: str | None = None,
    categories: str | None = None,
    agent_id: str | None = None,
    project_id: str | None = None,
    severity: str | None = None,
    severities: str | None = None,
    read: bool | None = None,
    unread_only: bool = False,
    search: str | None = Query(default=None, max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    date_from: str | None = None,
    date_to: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Paginated notification list with optional filters."""
    scoped_project_id = await _require_notification_project_scope(db, request, project_id)

    query = select(Notification).order_by(Notification.created_at.desc())
    query = query.where(Notification.project_id == scoped_project_id)

    category_values = _validate_values(
        _merge_filter_values(category, categories),
        ALLOWED_CATEGORIES,
        "notification category",
    )
    severity_values = _validate_values(
        _merge_filter_values(severity, severities),
        ALLOWED_SEVERITIES,
        "notification severity",
    )
    dt_from = _parse_iso_datetime(date_from or from_date, "date_from")
    dt_to = _parse_iso_datetime(date_to or to_date, "date_to")

    if category_values:
        query = query.where(Notification.category.in_(category_values))
    if agent_id:
        query = query.where(Notification.agent_id == agent_id)
    if severity_values:
        query = query.where(Notification.severity.in_(severity_values))
    if unread_only:
        if read is True:
            raise HTTPException(status_code=400, detail="read=true conflicts with unread_only=true")
        read = False
    if read is not None:
        query = query.where(Notification.read.is_(read))
    if search:
        like_pattern = f"%{search}%"
        query = query.where(
            Notification.title.ilike(like_pattern) | Notification.message.ilike(like_pattern)
        )
    if dt_from:
        query = query.where(Notification.created_at >= dt_from)
    if dt_to:
        query = query.where(Notification.created_at <= dt_to)

    # Total count for pagination
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0
    total_pages = max(1, math.ceil(total / page_size))

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    notifications = [n.to_dict() for n in result.scalars().all()]

    return {
        "notifications": notifications,
        "total": total,
        "total_pages": total_pages,
        "page": page,
        "page_size": page_size,
    }


@router.get("/notifications/unread-count")
async def unread_count(
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Return the number of unread notifications."""
    scoped_project_id = await _require_notification_project_scope(db, request, project_id)
    query = select(func.count(Notification.id)).where(Notification.read.is_(False))
    query = query.where(Notification.project_id == scoped_project_id)
    count = (await db.execute(query)).scalar() or 0
    return {"count": count}


@router.post("/notifications/{notification_id}/read")
async def mark_read(
    notification_id: str,
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Mark a single notification as read."""
    notification = await _get_project_notification_or_404(
        db,
        request,
        notification_id,
        project_id,
        min_role="viewer",
    )

    notification.read = True
    await db.commit()
    return {"success": True}


@router.post("/notifications/read-all")
async def mark_all_read(
    request: Request,
    data: MarkAllReadRequest | None = Body(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Mark all unread notifications as read for the active project."""
    scoped_project_id = await _require_notification_project_scope(
        db,
        request,
        data.project_id if data else None,
    )

    stmt = (
        update(Notification)
        .where(Notification.read.is_(False))
        .where(Notification.project_id == scoped_project_id)
    )

    stmt = stmt.values(read=True)
    result = await db.execute(stmt)
    await db.commit()

    return {"success": True, "count": result.rowcount}


@router.delete("/notifications/{notification_id}", status_code=204)
async def delete_notification(
    notification_id: str,
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Delete a single notification."""
    notification = await _get_project_notification_or_404(
        db,
        request,
        notification_id,
        project_id,
        min_role="researcher",
    )

    await db.delete(notification)
    await db.commit()


@router.get("/notifications/preferences")
async def get_preferences(request: Request, db: AsyncSession = Depends(get_db)):
    """Get all notification preferences."""
    require_admin_from_request(request)
    result = await db.execute(
        select(NotificationPreference).order_by(NotificationPreference.category)
    )
    prefs = [p.to_dict() for p in result.scalars().all()]
    return {"preferences": prefs}


@router.put("/notifications/preferences")
async def update_preferences(
    data: UpdatePreferencesRequest | list[PreferenceItem],
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Create or update notification preferences by category."""
    require_admin_from_request(request)
    updated: list[dict] = []
    preferences = data if isinstance(data, list) else data.preferences

    if not preferences:
        raise HTTPException(status_code=400, detail="At least one preference is required")

    categories = _validate_values(
        (item.category for item in preferences),
        ALLOWED_CATEGORIES,
        "notification category",
    )
    if len(categories) != len(set(categories)):
        raise HTTPException(status_code=400, detail="Duplicate notification preference category")

    for item in preferences:
        # Check if preference for this category already exists
        result = await db.execute(
            select(NotificationPreference).where(NotificationPreference.category == item.category)
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
