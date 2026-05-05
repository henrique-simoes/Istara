"""DGM-H archive API - lineage, selection, evaluation, and rollback."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dgmh_archive import ARCHIVE_STATUS, dgmh_archive
from app.core.security_middleware import get_user_from_request, require_admin_from_request
from app.models.database import get_db

router = APIRouter(prefix="/dgmh-archive")


class DGMHVariantCreateRequest(BaseModel):
    source_system: str = "manual"
    source_id: str = ""
    project_id: str = ""
    agent_id: str = ""
    governance_proposal_id: str = ""
    parent_id: str = ""
    target_system: str = ""
    mutation_kind: str = "proposal"
    mutation_surface: str = "evaluation"
    artifact_kind: str = "proposal_variant"
    artifact_ref: str = ""
    title: str = Field(..., min_length=1, max_length=255)
    summary: str = ""
    mutation: dict = Field(default_factory=dict)
    rollback_plan: dict = Field(default_factory=dict)
    evidence: list = Field(default_factory=list)
    metrics_before: dict = Field(default_factory=dict)
    metrics_after: dict = Field(default_factory=dict)
    reasoning_memory_ids: list[str] = Field(default_factory=list)
    score: float | None = None
    confidence: float = Field(default=0.5, ge=0, le=1)
    status: str = "candidate"


class DGMHVariantEvaluationRequest(BaseModel):
    metrics_before: dict = Field(default_factory=dict)
    metrics_after: dict = Field(default_factory=dict)
    passed: bool | None = None
    evidence: dict = Field(default_factory=dict)
    score: float | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


class DGMHVariantStatusRequest(BaseModel):
    reason: str = ""


class DGMHVariantApplyRequest(BaseModel):
    evidence: dict = Field(default_factory=dict)


@router.get("/variants")
async def list_variants(
    request: Request,
    project_id: str | None = Query(default=None),
    source_system: str | None = Query(default=None),
    status: str | None = Query(default=None),
    target_system: str | None = Query(default=None),
    mutation_surface: str | None = Query(default=None),
    artifact_kind: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List DGM-H archive variants. Admin-only because variants expose system internals."""
    require_admin_from_request(request)
    variants = await dgmh_archive.list_variants(
        project_id=project_id,
        source_system=source_system,
        status=status,
        target_system=target_system,
        mutation_surface=mutation_surface,
        artifact_kind=artifact_kind,
        limit=limit,
        offset=offset,
        db=db,
    )
    return {"variants": variants, "count": len(variants), "limit": limit, "offset": offset}


@router.post("/variants")
async def create_variant(
    body: DGMHVariantCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Create a manual DGM-H candidate variant."""
    require_admin_from_request(request)
    variant = await dgmh_archive.register_variant(**body.model_dump(), db=db)
    await db.commit()
    await db.refresh(variant)
    return {"variant": variant.to_dict()}


@router.get("/variants/{variant_id}")
async def get_variant(variant_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Get one DGM-H archive variant."""
    require_admin_from_request(request)
    variant = await dgmh_archive.get_variant(variant_id, db=db)
    if variant is None:
        raise HTTPException(status_code=404, detail="DGM-H archive variant not found")
    return {"variant": variant.to_dict()}


@router.get("/variants/{variant_id}/lineage")
async def get_lineage(variant_id: str, request: Request):
    """Return a variant's archive lineage."""
    require_admin_from_request(request)
    result = await dgmh_archive.lineage(variant_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/variants/{variant_id}/evaluation")
async def record_evaluation(
    variant_id: str,
    body: DGMHVariantEvaluationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Append measured evidence to a DGM-H archive variant."""
    require_admin_from_request(request)
    result = await dgmh_archive.record_evaluation(
        variant_id,
        metrics_before=body.metrics_before,
        metrics_after=body.metrics_after,
        passed=body.passed,
        evidence=body.evidence,
        score=body.score,
        confidence=body.confidence,
        db=db,
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    await db.commit()
    return result


@router.post("/variants/{variant_id}/approve")
async def approve_variant(
    variant_id: str,
    request: Request,
    body: DGMHVariantStatusRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Approve a DGM-H candidate for application through its owning subsystem."""
    require_admin_from_request(request)
    user = get_user_from_request(request)
    result = await dgmh_archive.set_variant_status(
        variant_id,
        status=ARCHIVE_STATUS["approved"],
        actor_id=user.get("id", ""),
        reason=body.reason if body else "",
        db=db,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    await db.commit()
    return result


@router.post("/variants/{variant_id}/apply")
async def apply_variant(
    variant_id: str,
    request: Request,
    body: DGMHVariantApplyRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Mark an approved archive variant as active after the subsystem applies it."""
    require_admin_from_request(request)
    user = get_user_from_request(request)
    result = await dgmh_archive.apply_variant(
        variant_id,
        actor_id=user.get("id", ""),
        evidence=body.evidence if body else {},
        db=db,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    await db.commit()
    return result


@router.post("/variants/{variant_id}/confirm")
async def confirm_variant(
    variant_id: str,
    request: Request,
    body: DGMHVariantStatusRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Confirm a variant after observed production improvement."""
    require_admin_from_request(request)
    user = get_user_from_request(request)
    result = await dgmh_archive.set_variant_status(
        variant_id,
        status=ARCHIVE_STATUS["confirmed"],
        actor_id=user.get("id", ""),
        reason=body.reason if body else "",
        db=db,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    await db.commit()
    return result


@router.post("/variants/{variant_id}/revert")
async def revert_variant(
    variant_id: str,
    request: Request,
    body: DGMHVariantStatusRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Mark a variant reverted after its rollback plan is executed."""
    require_admin_from_request(request)
    user = get_user_from_request(request)
    result = await dgmh_archive.set_variant_status(
        variant_id,
        status=ARCHIVE_STATUS["reverted"],
        actor_id=user.get("id", ""),
        reason=body.reason if body else "",
        db=db,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    await db.commit()
    return result


@router.post("/variants/{variant_id}/quarantine")
async def quarantine_variant(
    variant_id: str,
    request: Request,
    body: DGMHVariantStatusRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Quarantine a suspicious archive variant or reasoning trace."""
    require_admin_from_request(request)
    user = get_user_from_request(request)
    result = await dgmh_archive.set_variant_status(
        variant_id,
        status=ARCHIVE_STATUS["quarantined"],
        actor_id=user.get("id", ""),
        reason=body.reason if body else "",
        db=db,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    await db.commit()
    return result


@router.get("/select-parent")
async def select_parent(
    request: Request,
    target_system: str = "",
    artifact_kind: str = "",
    mutation_surface: str = "",
    project_id: str = "",
    db: AsyncSession = Depends(get_db),
):
    """Select the best archive parent using UCB-style exploration."""
    require_admin_from_request(request)
    parent = await dgmh_archive.select_parent(
        target_system=target_system,
        artifact_kind=artifact_kind,
        mutation_surface=mutation_surface,
        project_id=project_id,
        db=db,
    )
    return {"parent": parent}


@router.get("/summary")
async def archive_summary(request: Request, project_id: str | None = Query(default=None)):
    """Return aggregate DGM-H archive counts for dashboards and telemetry."""
    require_admin_from_request(request)
    return await dgmh_archive.summary(project_id=project_id)


# Route coverage hints: /dgmh-archive/variants /dgmh-archive/variants/{variant_id}
# /dgmh-archive/variants/{variant_id}/lineage /dgmh-archive/variants/{variant_id}/evaluation
# /dgmh-archive/variants/{variant_id}/approve /dgmh-archive/variants/{variant_id}/apply
# /dgmh-archive/variants/{variant_id}/confirm /dgmh-archive/variants/{variant_id}/revert
# /dgmh-archive/variants/{variant_id}/quarantine /dgmh-archive/select-parent /dgmh-archive/summary
