"""Meta-Hyperagent API routes — parameter tuning proposals and variants."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.config import settings
from app.core.improvement_governance import improvement_governance
from app.core.meta_hyperagent import meta_hyperagent
from app.core.security_middleware import get_user_from_request, require_admin_from_request

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


async def _sync_governance_applied(proposal_id: str, request: Request, variant: dict) -> None:
    """Reflect a HyperAgent UI approval in the system-wide governance ledger."""
    try:
        user = get_user_from_request(request)
        proposal = await improvement_governance.get_proposal_by_source(
            source_system="hyperagent",
            source_id=proposal_id,
        )
        if proposal is None:
            return
        if proposal.status in {"draft", "proposed"}:
            await improvement_governance.approve_proposal(
                proposal.id,
                reviewer_id=user.get("id", ""),
                note="Approved via Meta-Hyperagent UI",
            )
        proposal = await improvement_governance.get_proposal_by_source(
            source_system="hyperagent",
            source_id=proposal_id,
        )
        if proposal and proposal.status == "approved":
            await improvement_governance.apply_proposal(
                proposal.id,
                actor_id=user.get("id", ""),
                evidence={"variant_id": variant.get("id"), "source_ui": "meta_hyperagent"},
            )
    except Exception as exc:
        logger.debug(f"Meta-hyperagent governance apply sync skipped: {exc}")


async def _sync_governance_rejected(proposal_id: str, request: Request, reason: str) -> None:
    try:
        user = get_user_from_request(request)
        proposal = await improvement_governance.get_proposal_by_source(
            source_system="hyperagent",
            source_id=proposal_id,
        )
        if proposal and proposal.status in {"draft", "proposed", "approved"}:
            await improvement_governance.reject_proposal(
                proposal.id,
                reviewer_id=user.get("id", ""),
                reason=reason,
            )
    except Exception as exc:
        logger.debug(f"Meta-hyperagent governance reject sync skipped: {exc}")


async def _sync_governance_reverted(variant: dict, request: Request) -> None:
    try:
        user = get_user_from_request(request)
        proposal_id = str(variant.get("proposal_id", ""))
        proposal = await improvement_governance.get_proposal_by_source(
            source_system="hyperagent",
            source_id=proposal_id,
        )
        if proposal and proposal.status == "applied":
            await improvement_governance.revert_proposal(
                proposal.id,
                actor_id=user.get("id", ""),
                reason="Reverted via Meta-Hyperagent UI",
            )
    except Exception as exc:
        logger.debug(f"Meta-hyperagent governance revert sync skipped: {exc}")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/meta-hyperagent/status")
async def meta_hyperagent_status(request: Request):
    """Get meta-hyperagent status overview."""
    require_admin_from_request(request)
    recent_observations = meta_hyperagent.get_recent_observations(limit=1)
    return {
        "enabled": settings.meta_hyperagent_enabled,
        "running": meta_hyperagent.is_running,
        "experimental": True,
        "pending_proposals": len(meta_hyperagent.get_pending_proposals()),
        "active_variants": len(meta_hyperagent.get_active_variants()),
        "recent_observations": len(meta_hyperagent.get_recent_observations(limit=100)),
        "last_observed_at": recent_observations[-1].get("timestamp") if recent_observations else None,
        "reasoning_bank": recent_observations[-1].get("reasoning_bank", {}) if recent_observations else {},
        "observation_interval_hours": settings.meta_hyperagent_observation_interval_hours,
        "variant_observation_hours": settings.meta_hyperagent_variant_observation_hours,
    }


@router.get("/meta-hyperagent/proposals")
async def list_proposals(request: Request, limit: int = 50):
    """List all meta-hyperagent proposals."""
    require_admin_from_request(request)
    return {
        "proposals": meta_hyperagent.get_all_proposals(limit=limit),
        "pending_count": len(meta_hyperagent.get_pending_proposals()),
    }


@router.post("/meta-hyperagent/proposals/{proposal_id}/approve")
async def approve_proposal(proposal_id: str, request: Request):
    """Approve a pending proposal and apply it as an active variant."""
    require_admin_from_request(request)
    result = await meta_hyperagent.apply_proposal(proposal_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    await _sync_governance_applied(proposal_id, request, result)
    return {"status": "applied", "variant": result}


@router.post("/meta-hyperagent/proposals/{proposal_id}/reject")
async def reject_proposal(proposal_id: str, request: Request, body: RejectRequest | None = None):
    """Reject a pending proposal with optional reason."""
    require_admin_from_request(request)
    reason = body.reason if body else ""
    result = meta_hyperagent.reject_proposal(proposal_id, reason=reason)
    if result is None:
        raise HTTPException(status_code=404, detail="Proposal not found or not pending")
    await _sync_governance_rejected(proposal_id, request, reason)
    return {"status": "rejected", "proposal": result}


@router.get("/meta-hyperagent/variants")
async def list_variants(request: Request, limit: int = 50):
    """List all meta-hyperagent variants."""
    require_admin_from_request(request)
    return {
        "variants": meta_hyperagent.get_all_variants(limit=limit),
        "active_count": len(meta_hyperagent.get_active_variants()),
    }


@router.post("/meta-hyperagent/variants/{variant_id}/revert")
async def revert_variant(variant_id: str, request: Request):
    """Revert an active variant to its original value."""
    require_admin_from_request(request)
    result = await meta_hyperagent.revert_variant(variant_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    await _sync_governance_reverted(result, request)
    return {"status": "reverted", "variant": result}


@router.post("/meta-hyperagent/variants/{variant_id}/confirm")
async def confirm_variant(variant_id: str, request: Request):
    """Confirm an active variant — persist the override permanently."""
    require_admin_from_request(request)
    result = await meta_hyperagent.confirm_variant(variant_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"status": "confirmed", "variant": result}


@router.get("/meta-hyperagent/observations")
async def get_observations(request: Request, limit: int = 10):
    """Get recent observation snapshots."""
    require_admin_from_request(request)
    observations = meta_hyperagent.get_recent_observations(limit=limit)
    return {
        "observations": observations,
        "count": len(observations),
        "last_observed_at": observations[-1].get("timestamp") if observations else None,
    }


@router.post("/meta-hyperagent/toggle")
async def toggle_meta_hyperagent(body: ToggleRequest, request: Request):
    """Enable or disable the meta-hyperagent (persists to .env)."""
    require_admin_from_request(request)
    settings.meta_hyperagent_enabled = body.enabled
    _persist_env("META_HYPERAGENT_ENABLED", str(body.enabled).lower())

    if body.enabled:
        meta_hyperagent.start()
    else:
        meta_hyperagent.stop()

    return {
        "enabled": settings.meta_hyperagent_enabled,
        "message": f"Meta-hyperagent {'enabled' if body.enabled else 'disabled'}",
    }
