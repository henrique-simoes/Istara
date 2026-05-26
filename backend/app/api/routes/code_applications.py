"""Code Application API — view and review code-to-source traceability records."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import get_subject, require_project_access
from app.models.code_application import CodeApplication
from app.models.database import get_db
from app.services.research_validity_service import create_reconciliation_decision

router = APIRouter(prefix="/code-applications")


class ReviewAction(BaseModel):
    review_status: str  # "approved" | "rejected" | "modified"
    reviewed_by: str | None = None
    rationale: str | None = None
    accepted_code_id: str | None = None


def _require_project_id(project_id: str | None) -> str:
    scoped_project_id = (project_id or "").strip()
    if not scoped_project_id:
        raise HTTPException(status_code=400, detail="project_id is required")
    return scoped_project_id


@router.get("/{project_id}")
async def get_project_code_applications(
    project_id: str,
    request: Request,
    status: str | None = None,
    task_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get all code applications for a project, optionally filtered by review status."""
    await require_project_access(db, request, project_id, min_role="viewer")

    query = select(CodeApplication).where(
        CodeApplication.project_id == project_id
    )
    if status:
        query = query.where(CodeApplication.review_status == status)
    if task_id:
        query = query.where(CodeApplication.task_id == task_id)
    query = query.order_by(CodeApplication.created_at.desc())

    result = await db.execute(query)
    return [ca.to_dict() for ca in result.scalars().all()]


@router.get("/{project_id}/pending")
async def get_pending_reviews(
    project_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Get code applications pending human review."""
    await require_project_access(db, request, project_id, min_role="viewer")

    result = await db.execute(
        select(CodeApplication).where(
            CodeApplication.project_id == project_id,
            CodeApplication.review_status == "pending",
        ).order_by(CodeApplication.confidence.asc())  # Lowest confidence first
    )
    return [ca.to_dict() for ca in result.scalars().all()]


@router.patch("/{application_id}/review")
async def review_code_application(
    application_id: str,
    action: ReviewAction,
    request: Request,
    project_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Review a code application (approve/reject/modify)."""
    scoped_project_id = _require_project_id(project_id)
    await require_project_access(db, request, scoped_project_id, min_role="researcher")
    result = await db.execute(
        select(CodeApplication).where(
            CodeApplication.id == application_id,
            CodeApplication.project_id == scoped_project_id,
        )
    )
    ca = result.scalar_one_or_none()
    if not ca:
        raise HTTPException(status_code=404, detail="Code application not found")

    if action.review_status not in ("approved", "rejected", "modified"):
        raise HTTPException(status_code=400, detail="Invalid review status")

    subject = get_subject(request)
    decision_type = {
        "approved": "accepted",
        "rejected": "rejected",
        "modified": "revised",
    }[action.review_status]
    try:
        decision = await create_reconciliation_decision(
            db,
            project_id=scoped_project_id,
            code_application_id=ca.id,
            decision_type=decision_type,
            decided_by=subject.username or subject.id or action.reviewed_by or "local-user",
            rationale=action.rationale or "",
            accepted_code_id=action.accepted_code_id,
            source="human_review",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return decision["code_application"]


@router.post("/{project_id}/bulk-approve")
async def bulk_approve_high_confidence(
    project_id: str,
    request: Request,
    min_confidence: float = Query(default=0.9, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
):
    """Bulk-approve pending applications only when confidence and reliability agree."""
    await require_project_access(db, request, project_id, min_role="researcher")

    result = await db.execute(
        select(CodeApplication).where(
            CodeApplication.project_id == project_id,
            CodeApplication.review_status == "pending",
            CodeApplication.confidence >= min_confidence,
            CodeApplication.promotion_status == "accepted",
            CodeApplication.reliability_status.in_(("accepted", "reliable", "passed")),
        )
    )
    applications = result.scalars().all()
    now = datetime.now(timezone.utc)
    count = 0
    for ca in applications:
        ca.review_status = "approved"
        ca.reviewed_by = "auto:high-confidence"
        ca.reviewed_at = now
        count += 1

    await db.commit()
    return {"approved_count": count, "min_confidence": min_confidence}
