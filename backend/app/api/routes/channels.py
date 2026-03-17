"""API routes for multi-channel adapter management."""

import logging

from fastapi import APIRouter, HTTPException

from app.channels.base import channel_router

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/channels")
async def list_channels() -> list[dict]:
    """List all registered channel adapters with their status."""
    return channel_router.list_adapters()


@router.post("/channels/{name}/start")
async def start_channel(name: str) -> dict:
    """Start a specific channel adapter."""
    try:
        await channel_router.start_adapter(name)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Channel adapter '{name}' not found")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"status": "started", "channel": name}


@router.post("/channels/{name}/stop")
async def stop_channel(name: str) -> dict:
    """Stop a specific channel adapter."""
    try:
        await channel_router.stop_adapter(name)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Channel adapter '{name}' not found")
    return {"status": "stopped", "channel": name}
