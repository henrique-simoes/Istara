"""Project permission request workflow."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_middleware import write_audit_entry
from app.core.permissions import get_subject, is_global_admin, require_project_access
from app.models.database import get_db
from app.models.permission_request import PermissionRequest

router = APIRouter()


class PermissionRequestCreate(BaseModel):
    project_id: str = Field(min_length=1, max_length=100)
    action: str = Field(min_length=1, max_length=120)
    title: str = Field(default="", max_length=255)
    details: str = Field(default="", max_length=4000)
    payload_summary: str = Field(default="", max_length=4000)


class PermissionRequestReview(BaseModel):
    status: str = Field(pattern="^(approved|rejected)$")
    review_note: str = Field(default="", max_length=4000)


def _history_event(actor_id: str, actor_username: str, event: str, note: str = "") -> dict:
    return {
        "event": event,
        "actor_user_id": actor_id,
        "actor_username": actor_username,
        "note": note,
        "at": datetime.now(UTC).isoformat(),
    }


async def _get_permission_request(db: AsyncSession, request_id: str) -> PermissionRequest:
    result = await db.execute(select(PermissionRequest).where(PermissionRequest.id == request_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Permission request not found")
    return item


async def _get_project_permission_request(
    db: AsyncSession,
    request_id: str,
    project_id: str,
) -> PermissionRequest:
    result = await db.execute(
        select(PermissionRequest).where(
            PermissionRequest.id == request_id,
            PermissionRequest.project_id == project_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Permission request not found")
    return item


def _require_project_id(project_id: str | None) -> str:
    scoped_project_id = (project_id or "").strip()
    if not scoped_project_id:
        raise HTTPException(status_code=400, detail="project_id is required")
    return scoped_project_id


@router.post("/permission-requests", status_code=201)
async def create_permission_request(
    data: PermissionRequestCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Create a project-admin approval request for a gated action."""
    scoped_project_id = _require_project_id(data.project_id)
    subject = await require_project_access(
        db,
        request,
        scoped_project_id,
        min_role="viewer",
        conceal_unrelated=True,
    )
    title = data.title.strip() or data.action.strip().replace("_", " ").title()
    now = datetime.now(UTC)
    history = [_history_event(subject.id, subject.username, "created")]
    item = PermissionRequest(
        id=str(uuid.uuid4()),
        project_id=scoped_project_id,
        requester_user_id=subject.id,
        requester_username=subject.username,
        action=data.action.strip(),
        title=title,
        details=data.details.strip(),
        payload_summary=data.payload_summary.strip(),
        status="pending",
        history_json=json.dumps(history),
        created_at=now,
        updated_at=now,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    await write_audit_entry(
        user_id=subject.id,
        method=request.method,
        path=request.url.path,
        status_code=201,
        project_id=item.project_id,
        event_type="permission_request.created",
        details=json.dumps({"id": item.id, "action": item.action})[:2000],
    )

    return item.to_dict()


@router.get("/permission-requests")
async def list_permission_requests(
    request: Request,
    project_id: str | None = None,
    status: str | None = None,
    mine: bool = False,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List permission requests visible to admins, project admins, or requesters."""
    subject = get_subject(request)
    query = select(PermissionRequest).order_by(PermissionRequest.created_at.desc())

    if status:
        query = query.where(PermissionRequest.status == status)

    scoped_project_id = (project_id or "").strip()
    if scoped_project_id:
        if is_global_admin(subject):
            pass
        elif mine:
            await require_project_access(db, request, scoped_project_id, min_role="viewer")
            query = query.where(PermissionRequest.requester_user_id == subject.id)
        else:
            await require_project_access(db, request, scoped_project_id, min_role="project_admin")
        query = query.where(PermissionRequest.project_id == scoped_project_id)
    elif is_global_admin(subject):
        pass
    else:
        raise HTTPException(status_code=400, detail="project_id is required")

    result = await db.execute(query.limit(min(max(limit, 1), 250)).offset(max(offset, 0)))
    items = result.scalars().all()
    return {"requests": [item.to_dict() for item in items], "count": len(items)}


@router.patch("/permission-requests/{request_id}")
async def review_permission_request(
    request_id: str,
    data: PermissionRequestReview,
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Approve or reject a permission request."""
    subject = get_subject(request)
    scoped_project_id = (project_id or "").strip()
    if scoped_project_id:
        item = await _get_project_permission_request(db, request_id, scoped_project_id)
        subject = await require_project_access(
            db,
            request,
            scoped_project_id,
            min_role="project_admin",
            conceal_unrelated=True,
        )
    elif is_global_admin(subject):
        item = await _get_permission_request(db, request_id)
    else:
        raise HTTPException(status_code=400, detail="project_id is required")
    item.status = data.status
    item.reviewer_user_id = subject.id
    item.reviewer_username = subject.username
    item.review_note = data.review_note.strip()
    item.reviewed_at = datetime.now(UTC)
    item.updated_at = item.reviewed_at
    try:
        history = json.loads(item.history_json or "[]")
        if not isinstance(history, list):
            history = []
    except json.JSONDecodeError:
        history = []
    history.append(_history_event(subject.id, subject.username, data.status, item.review_note))
    item.history_json = json.dumps(history)
    await db.commit()
    await db.refresh(item)

    await write_audit_entry(
        user_id=subject.id,
        method=request.method,
        path=request.url.path,
        status_code=200,
        project_id=item.project_id,
        event_type=f"permission_request.{data.status}",
        details=json.dumps({"id": item.id, "action": item.action})[:2000],
    )

    return item.to_dict()
