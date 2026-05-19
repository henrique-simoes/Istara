"""API routes for multi-channel adapter management — full CRUD."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import (
    ProjectRole,
    get_active_project_or_404,
    require_project_access,
)
from app.models.channel_instance import ChannelInstance
from app.models.database import get_db
from app.services import channel_service

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class CreateChannelRequest(BaseModel):
    platform: str  # telegram|slack|whatsapp|google_chat
    name: str
    config: dict = {}
    project_id: str | None = None


class UpdateChannelRequest(BaseModel):
    name: str | None = None
    config: dict | None = None
    project_id: str | None = None


class SendMessageRequest(BaseModel):
    channel_id: str
    text: str
    metadata: dict | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


def _require_project_id(project_id: str | None) -> str:
    scoped_project_id = (project_id or "").strip()
    if not scoped_project_id:
        raise HTTPException(status_code=400, detail="project_id is required")
    return scoped_project_id


async def _get_project_channel_or_404(
    db: AsyncSession,
    request: Request,
    instance_id: str,
    project_id: str | None,
    *,
    min_role: ProjectRole,
) -> tuple[str, ChannelInstance]:
    scoped_project_id = _require_project_id(project_id)
    await require_project_access(db, request, scoped_project_id, min_role=min_role)
    instance = await channel_service.get_channel_instance(db, instance_id)
    if instance is None or instance.project_id != scoped_project_id:
        raise HTTPException(
            status_code=404,
            detail=f"Channel instance '{instance_id}' not found",
        )
    return scoped_project_id, instance


@router.get("/channels")
async def list_channels(
    request: Request,
    platform: Optional[str] = Query(None, description="Filter by platform"),
    project_id: Optional[str] = Query(None, description="Filter by project"),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List all channel instances, optionally filtered by platform."""
    scoped_project_id = _require_project_id(project_id)
    await require_project_access(db, request, scoped_project_id, min_role="viewer")
    instances = await channel_service.list_channel_instances(
        db, platform=platform, project_id=scoped_project_id
    )
    return [inst.to_dict() for inst in instances]


@router.post("/channels")
async def create_channel(
    body: CreateChannelRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new channel instance."""
    scoped_project_id = _require_project_id(body.project_id)
    await get_active_project_or_404(
        db, request, scoped_project_id, min_role="project_admin"
    )
    try:
        instance = await channel_service.create_channel_instance(
            db,
            platform=body.platform,
            name=body.name,
            config=body.config,
            project_id=scoped_project_id,
        )
        return instance.to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/channels/{instance_id}")
async def get_channel(
    instance_id: str,
    request: Request,
    project_id: Optional[str] = Query(None, description="Active project"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get details of a single channel instance."""
    _, instance = await _get_project_channel_or_404(
        db, request, instance_id, project_id, min_role="viewer"
    )
    return instance.to_dict()


@router.patch("/channels/{instance_id}")
async def update_channel(
    instance_id: str,
    body: UpdateChannelRequest,
    request: Request,
    project_id: Optional[str] = Query(None, description="Active project"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update a channel instance."""
    scoped_project_id, _ = await _get_project_channel_or_404(
        db, request, instance_id, project_id, min_role="project_admin"
    )
    if body.project_id is not None and body.project_id != scoped_project_id:
        raise HTTPException(
            status_code=400,
            detail="project_id cannot move a channel across projects",
        )
    try:
        instance = await channel_service.update_channel_instance(
            db,
            instance_id=instance_id,
            name=body.name,
            config=body.config,
            project_id=body.project_id,
            scope_project_id=scoped_project_id,
        )
        return instance.to_dict()
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Channel instance '{instance_id}' not found",
        )


@router.delete("/channels/{instance_id}")
async def delete_channel(
    instance_id: str,
    request: Request,
    project_id: Optional[str] = Query(None, description="Active project"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a channel instance (stops it first if running)."""
    scoped_project_id, _ = await _get_project_channel_or_404(
        db, request, instance_id, project_id, min_role="project_admin"
    )
    deleted = await channel_service.delete_channel_instance(
        db, instance_id, project_id=scoped_project_id
    )
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Channel instance '{instance_id}' not found",
        )
    return {"status": "deleted", "instance_id": instance_id}


@router.post("/channels/{instance_id}/start")
async def start_channel(
    instance_id: str,
    request: Request,
    project_id: Optional[str] = Query(None, description="Active project"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Start a channel instance (instantiate adapter and begin polling/listening)."""
    scoped_project_id, _ = await _get_project_channel_or_404(
        db, request, instance_id, project_id, min_role="project_admin"
    )
    await get_active_project_or_404(
        db, request, scoped_project_id, min_role="project_admin"
    )
    try:
        result = await channel_service.start_channel_instance(
            db, instance_id, project_id=scoped_project_id
        )
        return result
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Channel instance '{instance_id}' not found",
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/channels/{instance_id}/stop")
async def stop_channel(
    instance_id: str,
    request: Request,
    project_id: Optional[str] = Query(None, description="Active project"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Stop a running channel instance."""
    scoped_project_id, _ = await _get_project_channel_or_404(
        db, request, instance_id, project_id, min_role="project_admin"
    )
    try:
        result = await channel_service.stop_channel_instance(
            db, instance_id, project_id=scoped_project_id
        )
        return result
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Channel instance '{instance_id}' not found",
        )


@router.get("/channels/{instance_id}/health")
async def health_check_channel(
    instance_id: str,
    request: Request,
    project_id: Optional[str] = Query(None, description="Active project"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Run a health check on a channel instance."""
    scoped_project_id, _ = await _get_project_channel_or_404(
        db, request, instance_id, project_id, min_role="project_admin"
    )
    try:
        return await channel_service.health_check_instance(
            db, instance_id, project_id=scoped_project_id
        )
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Channel instance '{instance_id}' not found",
        )


@router.get("/channels/{instance_id}/messages")
async def get_channel_messages(
    instance_id: str,
    request: Request,
    project_id: Optional[str] = Query(None, description="Active project"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Get message history for a channel instance."""
    scoped_project_id, _ = await _get_project_channel_or_404(
        db, request, instance_id, project_id, min_role="viewer"
    )
    return await channel_service.get_message_history(
        db,
        instance_id,
        project_id=scoped_project_id,
        limit=limit,
        offset=offset,
    )


@router.get("/channels/{instance_id}/conversations")
async def get_channel_conversations(
    instance_id: str,
    request: Request,
    project_id: Optional[str] = Query(None, description="Active project"),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Get conversations for a channel instance."""
    scoped_project_id, _ = await _get_project_channel_or_404(
        db, request, instance_id, project_id, min_role="viewer"
    )
    return await channel_service.get_conversations(
        db, instance_id, project_id=scoped_project_id
    )


@router.post("/channels/{instance_id}/send")
async def send_channel_message(
    instance_id: str,
    body: SendMessageRequest,
    request: Request,
    project_id: Optional[str] = Query(None, description="Active project"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Send a manual message through a channel instance."""
    scoped_project_id, _ = await _get_project_channel_or_404(
        db, request, instance_id, project_id, min_role="project_admin"
    )
    try:
        return await channel_service.send_message(
            db,
            instance_id=instance_id,
            channel_id=body.channel_id,
            text=body.text,
            metadata=body.metadata,
            project_id=scoped_project_id,
        )
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Channel instance '{instance_id}' not found",
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
