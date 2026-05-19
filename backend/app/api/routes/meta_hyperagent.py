"""Meta-Hyperagent API routes — parameter tuning proposals and variants."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.improvement_governance import improvement_governance
from app.core.meta_hyperagent import meta_hyperagent
from app.core.permissions import get_active_project_or_404, get_visible_project_or_404
from app.core.security_middleware import get_user_from_request, require_admin_from_request
from app.models.database import get_db

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


def _require_project_id(project_id: str | None) -> str:
    scoped_project_id = (project_id or "").strip()
    if not scoped_project_id:
        raise HTTPException(status_code=400, detail="project_id is required")
    return scoped_project_id


async def _require_admin_project_scope(
    db: AsyncSession,
    request: Request,
    project_id: str | None,
) -> str:
    """Require global admin plus an explicit, visible project scope."""
    require_admin_from_request(request)
    scoped_project_id = _require_project_id(project_id)
    await get_visible_project_or_404(db, request, scoped_project_id, min_role="viewer")
    return scoped_project_id


async def _require_admin_active_project_scope(
    db: AsyncSession,
    request: Request,
    project_id: str | None,
) -> str:
    """Require global admin plus an explicit, unpaused visible project."""
    require_admin_from_request(request)
    scoped_project_id = _require_project_id(project_id)
    await get_active_project_or_404(db, request, scoped_project_id, min_role="viewer")
    return scoped_project_id


async def _sync_governance_applied(
    proposal_id: str,
    project_id: str,
    request: Request,
    variant: dict,
) -> None:
    """Reflect a HyperAgent UI approval in the project governance ledger."""
    try:
        user = get_user_from_request(request)
        proposal = await improvement_governance.get_proposal_by_source(
            source_system="hyperagent",
            source_id=proposal_id,
            project_id=project_id,
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
            project_id=project_id,
        )
        if proposal and proposal.status == "approved":
            await improvement_governance.apply_proposal(
                proposal.id,
                actor_id=user.get("id", ""),
                evidence={"variant_id": variant.get("id"), "source_ui": "meta_hyperagent"},
            )
    except Exception as exc:
        logger.debug(f"Meta-hyperagent governance apply sync skipped: {exc}")


async def _sync_governance_rejected(
    proposal_id: str,
    project_id: str,
    request: Request,
    reason: str,
) -> None:
    try:
        user = get_user_from_request(request)
        proposal = await improvement_governance.get_proposal_by_source(
            source_system="hyperagent",
            source_id=proposal_id,
            project_id=project_id,
        )
        if proposal and proposal.status in {"draft", "proposed", "approved"}:
            await improvement_governance.reject_proposal(
                proposal.id,
                reviewer_id=user.get("id", ""),
                reason=reason,
            )
    except Exception as exc:
        logger.debug(f"Meta-hyperagent governance reject sync skipped: {exc}")


async def _sync_governance_reverted(
    variant: dict,
    project_id: str,
    request: Request,
) -> None:
    try:
        user = get_user_from_request(request)
        proposal_id = str(variant.get("proposal_id", ""))
        proposal = await improvement_governance.get_proposal_by_source(
            source_system="hyperagent",
            source_id=proposal_id,
            project_id=project_id,
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
async def meta_hyperagent_status(
    request: Request,
    project_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Get meta-hyperagent status overview."""
    scoped_project_id = await _require_admin_project_scope(db, request, project_id)
    recent_observations = meta_hyperagent.get_recent_observations(
        limit=1,
        project_id=scoped_project_id,
    )
    enabled_for_project = (
        settings.meta_hyperagent_enabled
        and meta_hyperagent.is_running_for_project(scoped_project_id)
    )
    return {
        "enabled": enabled_for_project,
        "configured_enabled": settings.meta_hyperagent_enabled,
        "running": meta_hyperagent.is_running_for_project(scoped_project_id),
        "project_id": scoped_project_id,
        "active_project_id": meta_hyperagent.active_project_id,
        "experimental": True,
        "pending_proposals": len(
            meta_hyperagent.get_pending_proposals(project_id=scoped_project_id)
        ),
        "active_variants": len(
            meta_hyperagent.get_active_variants(project_id=scoped_project_id)
        ),
        "recent_observations": len(
            meta_hyperagent.get_recent_observations(
                limit=100,
                project_id=scoped_project_id,
            )
        ),
        "last_observed_at": recent_observations[-1].get("timestamp") if recent_observations else None,
        "reasoning_bank": recent_observations[-1].get("reasoning_bank", {}) if recent_observations else {},
        "observation_interval_hours": settings.meta_hyperagent_observation_interval_hours,
        "variant_observation_hours": settings.meta_hyperagent_variant_observation_hours,
    }


@router.get("/meta-hyperagent/proposals")
async def list_proposals(
    request: Request,
    project_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List all meta-hyperagent proposals."""
    scoped_project_id = await _require_admin_project_scope(db, request, project_id)
    return {
        "project_id": scoped_project_id,
        "proposals": meta_hyperagent.get_all_proposals(
            limit=limit,
            project_id=scoped_project_id,
        ),
        "pending_count": len(
            meta_hyperagent.get_pending_proposals(project_id=scoped_project_id)
        ),
    }


@router.post("/meta-hyperagent/proposals/{proposal_id}/approve")
async def approve_proposal(
    proposal_id: str,
    request: Request,
    project_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Approve a pending proposal and apply it as an active variant."""
    scoped_project_id = await _require_admin_active_project_scope(db, request, project_id)
    result = await meta_hyperagent.apply_proposal(
        proposal_id,
        project_id=scoped_project_id,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    await _sync_governance_applied(proposal_id, scoped_project_id, request, result)
    return {"status": "applied", "variant": result}


@router.post("/meta-hyperagent/proposals/{proposal_id}/reject")
async def reject_proposal(
    proposal_id: str,
    request: Request,
    body: RejectRequest | None = None,
    project_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Reject a pending proposal with optional reason."""
    scoped_project_id = await _require_admin_project_scope(db, request, project_id)
    reason = body.reason if body else ""
    result = meta_hyperagent.reject_proposal(
        proposal_id,
        reason=reason,
        project_id=scoped_project_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Proposal not found or not pending")
    await _sync_governance_rejected(proposal_id, scoped_project_id, request, reason)
    return {"status": "rejected", "proposal": result}


@router.get("/meta-hyperagent/variants")
async def list_variants(
    request: Request,
    project_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List all meta-hyperagent variants."""
    scoped_project_id = await _require_admin_project_scope(db, request, project_id)
    return {
        "project_id": scoped_project_id,
        "variants": meta_hyperagent.get_all_variants(
            limit=limit,
            project_id=scoped_project_id,
        ),
        "active_count": len(
            meta_hyperagent.get_active_variants(project_id=scoped_project_id)
        ),
    }


@router.post("/meta-hyperagent/variants/{variant_id}/revert")
async def revert_variant(
    variant_id: str,
    request: Request,
    project_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Revert an active variant to its original value."""
    scoped_project_id = await _require_admin_project_scope(db, request, project_id)
    result = await meta_hyperagent.revert_variant(
        variant_id,
        project_id=scoped_project_id,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    await _sync_governance_reverted(result, scoped_project_id, request)
    return {"status": "reverted", "variant": result}


@router.post("/meta-hyperagent/variants/{variant_id}/confirm")
async def confirm_variant(
    variant_id: str,
    request: Request,
    project_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Confirm an active variant — persist the override permanently."""
    scoped_project_id = await _require_admin_active_project_scope(db, request, project_id)
    result = await meta_hyperagent.confirm_variant(
        variant_id,
        project_id=scoped_project_id,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"status": "confirmed", "variant": result}


@router.get("/meta-hyperagent/observations")
async def get_observations(
    request: Request,
    project_id: str | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get recent observation snapshots."""
    scoped_project_id = await _require_admin_project_scope(db, request, project_id)
    observations = meta_hyperagent.get_recent_observations(
        limit=limit,
        project_id=scoped_project_id,
    )
    return {
        "project_id": scoped_project_id,
        "observations": observations,
        "count": len(observations),
        "last_observed_at": observations[-1].get("timestamp") if observations else None,
    }


@router.post("/meta-hyperagent/toggle")
async def toggle_meta_hyperagent(
    body: ToggleRequest,
    request: Request,
    project_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Enable or disable the meta-hyperagent (persists to .env)."""
    if body.enabled:
        scoped_project_id = await _require_admin_active_project_scope(db, request, project_id)
    else:
        scoped_project_id = await _require_admin_project_scope(db, request, project_id)
    settings.meta_hyperagent_enabled = body.enabled
    _persist_env("META_HYPERAGENT_ENABLED", str(body.enabled).lower())

    if body.enabled:
        meta_hyperagent.start(project_id=scoped_project_id)
    else:
        meta_hyperagent.stop(project_id=scoped_project_id)

    return {
        "enabled": body.enabled,
        "project_id": scoped_project_id,
        "message": f"Meta-hyperagent {'enabled' if body.enabled else 'disabled'}",
    }
