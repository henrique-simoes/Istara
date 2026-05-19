"""Improvement Governance API - proposals, evidence, approval, and rollback."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.improvement_governance import improvement_governance
from app.core.permissions import get_visible_project_or_404
from app.core.security_middleware import (
    get_user_from_request,
    require_admin_from_request,
)
from app.models.database import get_db

router = APIRouter(prefix="/improvement-governance")


class ImprovementProposalCreateRequest(BaseModel):
    source_system: str = "manual"
    source_id: str = ""
    project_id: str = ""
    agent_id: str = ""
    title: str = Field(..., min_length=1, max_length=255)
    summary: str = ""
    rationale: str = ""
    affected_surfaces: list[str] = Field(default_factory=list)
    risk_level: str | None = None
    approval_policy: str | None = None
    before_state: dict = Field(default_factory=dict)
    proposed_change: dict = Field(default_factory=dict)
    rollback_plan: dict = Field(default_factory=dict)
    evidence: list = Field(default_factory=list)
    metrics_before: dict = Field(default_factory=dict)
    metrics_after: dict = Field(default_factory=dict)
    reasoning_memory_ids: list[str] = Field(default_factory=list)
    improvement_score: float | None = None
    confidence: float = Field(default=0.5, ge=0, le=1)


class ProposalDecisionRequest(BaseModel):
    note: str = ""
    reason: str = ""


class ProposalApplyRequest(BaseModel):
    evidence: dict = Field(default_factory=dict)


class ProposalEvaluationRequest(BaseModel):
    metrics_before: dict = Field(default_factory=dict)
    metrics_after: dict = Field(default_factory=dict)
    passed: bool | None = None
    evidence: dict = Field(default_factory=dict)


class ProposalSandboxEvaluationRequest(BaseModel):
    evidence: dict = Field(default_factory=dict)


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


async def _get_project_proposal_or_404(
    proposal_id: str,
    project_id: str,
    db: AsyncSession,
):
    proposal = await improvement_governance.get_proposal(proposal_id, db=db)
    if proposal is None or proposal.project_id != project_id:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return proposal


@router.get("/proposals")
async def list_proposals(
    request: Request,
    project_id: str | None = Query(default=None),
    source_system: str | None = Query(default=None),
    status: str | None = Query(default=None),
    affected_surface: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List improvement proposals. Admin-only because proposals can expose system internals."""
    scoped_project_id = await _require_admin_project_scope(db, request, project_id)
    proposals = await improvement_governance.list_proposals(
        project_id=scoped_project_id,
        source_system=source_system,
        status=status,
        affected_surface=affected_surface,
        limit=limit,
        offset=offset,
        db=db,
    )
    return {"proposals": proposals, "count": len(proposals), "limit": limit, "offset": offset}


@router.get("/proposals/{proposal_id}")
async def get_proposal(
    proposal_id: str,
    request: Request,
    project_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Get one improvement proposal."""
    scoped_project_id = await _require_admin_project_scope(db, request, project_id)
    proposal = await _get_project_proposal_or_404(proposal_id, scoped_project_id, db)
    return {"proposal": proposal.to_dict()}


@router.post("/proposals")
async def create_proposal(
    body: ImprovementProposalCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Create a manual or integration-origin improvement proposal."""
    scoped_project_id = await _require_admin_project_scope(db, request, body.project_id)
    user = get_user_from_request(request)
    data = body.model_dump()
    data["project_id"] = scoped_project_id
    proposal = await improvement_governance.create_proposal(
        **data,
        created_by=user.get("id", ""),
        db=db,
    )
    await db.commit()
    await db.refresh(proposal)
    return {"proposal": proposal.to_dict()}


@router.post("/proposals/{proposal_id}/approve")
async def approve_proposal(
    proposal_id: str,
    request: Request,
    body: ProposalDecisionRequest | None = None,
    project_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Approve a proposal so it can be applied through its owning subsystem."""
    scoped_project_id = await _require_admin_project_scope(db, request, project_id)
    await _get_project_proposal_or_404(proposal_id, scoped_project_id, db)
    user = get_user_from_request(request)
    result = await improvement_governance.approve_proposal(
        proposal_id,
        reviewer_id=user.get("id", ""),
        note=body.note if body else "",
        db=db,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    await db.commit()
    return result


@router.post("/proposals/{proposal_id}/apply")
async def apply_proposal(
    proposal_id: str,
    request: Request,
    body: ProposalApplyRequest | None = None,
    project_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Mark an approved proposal as applied after its subsystem applies it."""
    scoped_project_id = await _require_admin_project_scope(db, request, project_id)
    await _get_project_proposal_or_404(proposal_id, scoped_project_id, db)
    user = get_user_from_request(request)
    result = await improvement_governance.apply_proposal(
        proposal_id,
        actor_id=user.get("id", ""),
        evidence=body.evidence if body else {},
        db=db,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    await db.commit()
    return result


@router.post("/proposals/{proposal_id}/reject")
async def reject_proposal(
    proposal_id: str,
    request: Request,
    body: ProposalDecisionRequest | None = None,
    project_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Reject a pending proposal."""
    scoped_project_id = await _require_admin_project_scope(db, request, project_id)
    await _get_project_proposal_or_404(proposal_id, scoped_project_id, db)
    user = get_user_from_request(request)
    result = await improvement_governance.reject_proposal(
        proposal_id,
        reviewer_id=user.get("id", ""),
        reason=body.reason if body else "",
        db=db,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    await db.commit()
    return result


@router.post("/proposals/{proposal_id}/revert")
async def revert_proposal(
    proposal_id: str,
    request: Request,
    body: ProposalDecisionRequest | None = None,
    project_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Mark an applied proposal as reverted after its rollback path is executed."""
    scoped_project_id = await _require_admin_project_scope(db, request, project_id)
    await _get_project_proposal_or_404(proposal_id, scoped_project_id, db)
    user = get_user_from_request(request)
    result = await improvement_governance.revert_proposal(
        proposal_id,
        actor_id=user.get("id", ""),
        reason=body.reason if body else "",
        db=db,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    await db.commit()
    return result


@router.post("/proposals/{proposal_id}/quarantine")
async def quarantine_proposal(
    proposal_id: str,
    request: Request,
    body: ProposalDecisionRequest | None = None,
    project_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Quarantine a suspicious proposal or memory-linked change."""
    scoped_project_id = await _require_admin_project_scope(db, request, project_id)
    await _get_project_proposal_or_404(proposal_id, scoped_project_id, db)
    user = get_user_from_request(request)
    result = await improvement_governance.quarantine_proposal(
        proposal_id,
        actor_id=user.get("id", ""),
        reason=body.reason if body else "",
        db=db,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    await db.commit()
    return result


@router.post("/proposals/{proposal_id}/evaluation")
async def record_evaluation(
    proposal_id: str,
    body: ProposalEvaluationRequest,
    request: Request,
    project_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Append evaluation evidence to a proposal."""
    scoped_project_id = await _require_admin_project_scope(db, request, project_id)
    await _get_project_proposal_or_404(proposal_id, scoped_project_id, db)
    result = await improvement_governance.record_evaluation(
        proposal_id,
        metrics_before=body.metrics_before,
        metrics_after=body.metrics_after,
        passed=body.passed,
        evidence=body.evidence,
        db=db,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    await db.commit()
    return result


@router.post("/proposals/{proposal_id}/sandbox-evaluation")
async def record_sandbox_evaluation(
    proposal_id: str,
    body: ProposalSandboxEvaluationRequest,
    request: Request,
    project_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Run and persist local sandbox checks before apply."""
    scoped_project_id = await _require_admin_project_scope(db, request, project_id)
    await _get_project_proposal_or_404(proposal_id, scoped_project_id, db)
    result = await improvement_governance.record_sandbox_evaluation(
        proposal_id,
        evidence=body.evidence,
        db=db,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    await db.commit()
    return result


@router.get("/summary")
async def governance_summary(
    request: Request,
    project_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Return aggregate governance counts for dashboards and telemetry."""
    scoped_project_id = await _require_admin_project_scope(db, request, project_id)
    return await improvement_governance.summary(project_id=scoped_project_id)


@router.get("/feature-contract")
async def feature_contract(request: Request):
    """Return the feature evidence matrix enforced by the improvement contract."""
    require_admin_from_request(request)
    return {"features": improvement_governance.feature_contract_matrix()}
