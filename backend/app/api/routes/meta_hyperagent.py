"""Meta-Hyperagent API routes — parameter tuning proposals and variants."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.core.meta_hyperagent import meta_hyperagent

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class RejectRequest(BaseModel):
    reason: str = ""


class ToggleRequest(BaseModel):
    enabled: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _persist_env(key: str, value: str) -> None:
    """Update a key in the .env file (reuses settings.py pattern)."""
    env_path = Path(".env")
    if not env_path.exists():
        env_path.write_text(f"{key}={value}\n")
        return

    lines = env_path.read_text().splitlines(keepends=True)
    found = False
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f"{key}=") or stripped.startswith(f"{key} ="):
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)
    if not found:
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines[-1] += "\n"
        new_lines.append(f"{key}={value}\n")
    env_path.write_text("".join(new_lines))


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/meta-hyperagent/status")
async def meta_hyperagent_status():
    """Get meta-hyperagent status overview."""
    return {
        "enabled": settings.meta_hyperagent_enabled,
        "experimental": True,
        "pending_proposals": len(meta_hyperagent.get_pending_proposals()),
        "active_variants": len(meta_hyperagent.get_active_variants()),
        "observation_interval_hours": settings.meta_hyperagent_observation_interval_hours,
        "variant_observation_hours": settings.meta_hyperagent_variant_observation_hours,
    }


@router.get("/meta-hyperagent/proposals")
async def list_proposals(limit: int = 50):
    """List all meta-hyperagent proposals."""
    return {
        "proposals": meta_hyperagent.get_all_proposals(limit=limit),
        "pending_count": len(meta_hyperagent.get_pending_proposals()),
    }


@router.post("/meta-hyperagent/proposals/{proposal_id}/approve")
async def approve_proposal(proposal_id: str):
    """Approve a pending proposal and apply it as an active variant."""
    result = await meta_hyperagent.apply_proposal(proposal_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"status": "applied", "variant": result}


@router.post("/meta-hyperagent/proposals/{proposal_id}/reject")
async def reject_proposal(proposal_id: str, body: RejectRequest | None = None):
    """Reject a pending proposal with optional reason."""
    reason = body.reason if body else ""
    result = meta_hyperagent.reject_proposal(proposal_id, reason=reason)
    if result is None:
        raise HTTPException(status_code=404, detail="Proposal not found or not pending")
    return {"status": "rejected", "proposal": result}


@router.get("/meta-hyperagent/variants")
async def list_variants(limit: int = 50):
    """List all meta-hyperagent variants."""
    return {
        "variants": meta_hyperagent.get_all_variants(limit=limit),
        "active_count": len(meta_hyperagent.get_active_variants()),
    }


@router.post("/meta-hyperagent/variants/{variant_id}/revert")
async def revert_variant(variant_id: str):
    """Revert an active variant to its original value."""
    result = await meta_hyperagent.revert_variant(variant_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"status": "reverted", "variant": result}


@router.post("/meta-hyperagent/variants/{variant_id}/confirm")
async def confirm_variant(variant_id: str):
    """Confirm an active variant — persist the override permanently."""
    result = await meta_hyperagent.confirm_variant(variant_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"status": "confirmed", "variant": result}


@router.get("/meta-hyperagent/observations")
async def get_observations(limit: int = 10):
    """Get recent observation snapshots."""
    return {
        "observations": meta_hyperagent.get_recent_observations(limit=limit),
    }


@router.post("/meta-hyperagent/toggle")
async def toggle_meta_hyperagent(body: ToggleRequest):
    """Enable or disable the meta-hyperagent (persists to .env)."""
    settings.meta_hyperagent_enabled = body.enabled
    _persist_env("META_HYPERAGENT_ENABLED", str(body.enabled).lower())

    if body.enabled:
        # Start the observation loop if not already running
        import asyncio
        if not meta_hyperagent._running:
            meta_hyperagent.load_confirmed_overrides()
            asyncio.create_task(meta_hyperagent.start_observation_loop())
    else:
        meta_hyperagent.stop()

    return {
        "enabled": settings.meta_hyperagent_enabled,
        "message": f"Meta-hyperagent {'enabled' if body.enabled else 'disabled'}",
    }
