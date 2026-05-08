"""API routes for multi-channel adapter management — full CRUD."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import get_subject, is_global_admin, require_project_access
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


async def _require_channel_admin(
    db: AsyncSession,
    request: Request,
    instance: ChannelInstance,
) -> None:
    subject = get_subject(request)
    if is_global_admin(subject):
        return
    if not instance.project_id:
        raise HTTPException(status_code=403, detail="Global admin access required.")
    await require_project_access(db, request, instance.project_id, min_role="project_admin")


async def _get_channel_for_admin(
    db: AsyncSession,
    request: Request,
    instance_id: str,
) -> ChannelInstance:
    instance = await channel_service.get_channel_instance(db, instance_id)
    if instance is None:
        raise HTTPException(status_code=404, detail=f"Channel instance '{instance_id}' not found")
    await _require_channel_admin(db, request, instance)
    return instance


@router.get("/channels")
async def list_channels(
    request: Request,
    platform: Optional[str] = Query(None, description="Filter by platform"),
    project_id: Optional[str] = Query(None, description="Filter by project"),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List all channel instances, optionally filtered by platform."""
    subject = get_subject(request)
    if project_id:
        await require_project_access(db, request, project_id, min_role="project_admin")
    elif not is_global_admin(subject):
        raise HTTPException(status_code=400, detail="project_id is required")
    instances = await channel_service.list_channel_instances(db, platform=platform)
    if project_id:
        instances = [inst for inst in instances if inst.project_id == project_id]
    return [inst.to_dict() for inst in instances]


@router.post("/channels")
async def create_channel(
    body: CreateChannelRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new channel instance."""
    subject = get_subject(request)
    if is_global_admin(subject):
        pass
    elif body.project_id:
        await require_project_access(db, request, body.project_id, min_role="project_admin")
    else:
        raise HTTPException(status_code=400, detail="project_id is required")
    try:
        instance = await channel_service.create_channel_instance(
            db,
            platform=body.platform,
            name=body.name,
            config=body.config,
            project_id=body.project_id,
        )
        return instance.to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/channels/{instance_id}")
async def get_channel(
    instance_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get details of a single channel instance."""
    instance = await _get_channel_for_admin(db, request, instance_id)
    return instance.to_dict()


@router.patch("/channels/{instance_id}")
async def update_channel(
    instance_id: str,
    body: UpdateChannelRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update a channel instance."""
    instance = await _get_channel_for_admin(db, request, instance_id)
    if body.project_id and body.project_id != instance.project_id:
        await require_project_access(db, request, body.project_id, min_role="project_admin")
    try:
        instance = await channel_service.update_channel_instance(
            db,
            instance_id=instance_id,
            name=body.name,
            config=body.config,
            project_id=body.project_id,
        )
        return instance.to_dict()
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Channel instance '{instance_id}' not found")


@router.delete("/channels/{instance_id}")
async def delete_channel(
    instance_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a channel instance (stops it first if running)."""
    await _get_channel_for_admin(db, request, instance_id)
    deleted = await channel_service.delete_channel_instance(db, instance_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Channel instance '{instance_id}' not found")
    return {"status": "deleted", "instance_id": instance_id}


@router.post("/channels/{instance_id}/start")
async def start_channel(
    instance_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Start a channel instance (instantiate adapter and begin polling/listening)."""
    await _get_channel_for_admin(db, request, instance_id)
    try:
        result = await channel_service.start_channel_instance(db, instance_id)
        return result
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Channel instance '{instance_id}' not found")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/channels/{instance_id}/stop")
async def stop_channel(
    instance_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Stop a running channel instance."""
    await _get_channel_for_admin(db, request, instance_id)
    try:
        result = await channel_service.stop_channel_instance(db, instance_id)
        return result
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Channel instance '{instance_id}' not found")


@router.get("/channels/{instance_id}/health")
async def health_check_channel(
    instance_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Run a health check on a channel instance."""
    await _get_channel_for_admin(db, request, instance_id)
    try:
        return await channel_service.health_check_instance(db, instance_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Channel instance '{instance_id}' not found")


@router.get("/channels/{instance_id}/messages")
async def get_channel_messages(
    instance_id: str,
    request: Request,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Get message history for a channel instance."""
    await _get_channel_for_admin(db, request, instance_id)
    return await channel_service.get_message_history(db, instance_id, limit=limit, offset=offset)


@router.get("/channels/{instance_id}/conversations")
async def get_channel_conversations(
    instance_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Get conversations for a channel instance."""
    await _get_channel_for_admin(db, request, instance_id)
    return await channel_service.get_conversations(db, instance_id)


@router.post("/channels/{instance_id}/send")
async def send_channel_message(
    instance_id: str,
    body: SendMessageRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Send a manual message through a channel instance."""
    await _get_channel_for_admin(db, request, instance_id)
    try:
        return await channel_service.send_message(
            db,
            instance_id=instance_id,
            channel_id=body.channel_id,
            text=body.text,
            metadata=body.metadata,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Channel instance '{instance_id}' not found")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
