"""Code Application API — view and review code-to-source traceability records."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.code_application import CodeApplication
from app.models.database import get_db

router = APIRouter(prefix="/code-applications")


class ReviewAction(BaseModel):
    review_status: str  # "approved" | "rejected" | "modified"
    reviewed_by: str = "user"


@router.get("/{project_id}")
async def get_project_code_applications(
    project_id: str,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get all code applications for a project, optionally filtered by review status."""
    query = select(CodeApplication).where(
        CodeApplication.project_id == project_id
    )
    if status:
        query = query.where(CodeApplication.review_status == status)
    query = query.order_by(CodeApplication.created_at.desc())

    result = await db.execute(query)
    return [ca.to_dict() for ca in result.scalars().all()]


@router.get("/{project_id}/pending")
async def get_pending_reviews(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get code applications pending human review."""
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
    db: AsyncSession = Depends(get_db),
):
    """Review a code application (approve/reject/modify)."""
    result = await db.execute(
        select(CodeApplication).where(CodeApplication.id == application_id)
    )
    ca = result.scalar_one_or_none()
    if not ca:
        raise HTTPException(status_code=404, detail="Code application not found")

    if action.review_status not in ("approved", "rejected", "modified"):
        raise HTTPException(status_code=400, detail="Invalid review status")

    ca.review_status = action.review_status
    ca.reviewed_by = action.reviewed_by
    ca.reviewed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(ca)
    return ca.to_dict()


@router.post("/{project_id}/bulk-approve")
async def bulk_approve_high_confidence(
    project_id: str,
    min_confidence: float = 0.9,
    db: AsyncSession = Depends(get_db),
):
    """Bulk-approve all pending code applications above a confidence threshold."""
    result = await db.execute(
        select(CodeApplication).where(
            CodeApplication.project_id == project_id,
            CodeApplication.review_status == "pending",
            CodeApplication.confidence >= min_confidence,
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
