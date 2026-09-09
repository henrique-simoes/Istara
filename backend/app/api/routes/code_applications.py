import json
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.permissions import get_subject, require_project_access
from app.models.code_application import CodeApplication
from app.models.database import get_db
from app.models.research_validity import (
    EvidenceUnit,
    ReconciliationDecision,
    ResearchEvidenceEdge,
)
from app.services.research_validity_service import (
    create_reconciliation_decision,
)
from app.services.synthetic_reconciliation_service import (
    SYNTHETIC_RECONCILIATION_SOURCE,
    create_synthetic_reconciliation_decisions,
)

router = APIRouter(prefix="/code-applications")


class CreateCodeApplicationRequest(BaseModel):
    code_id: str
    codebook_version_id: str | None = None
    source_document_id: str | None = None
    source_text: str
    source_location: str = ""
    source_type: str = "document"
    start_offset: int | None = None
    end_offset: int | None = None
    task_id: str | None = None
    reasoning: str = ""
    speaker: str = ""


class ReviewAction(BaseModel):
    review_status: str  # "approved" | "rejected" | "modified"
    reviewed_by: str | None = None
    rationale: str | None = None
    accepted_code_id: str | None = None


class SyntheticReconciliationAction(BaseModel):
    code_application_id: str
    decision_type: str
    rationale: str | None = None
    accepted_code_id: str | None = None


class SyntheticReconciliationRequest(BaseModel):
    coding_run_id: str
    diagnostic_id: str
    decisions: list[SyntheticReconciliationAction]


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
    coding_run_id: str | None = None,
    source_document_id: str | None = None,
    code_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get project code applications, optionally scoped to one coding run, document, or code."""
    await require_project_access(db, request, project_id, min_role="viewer")

    query = select(CodeApplication).where(CodeApplication.project_id == project_id)
    if status:
        query = query.where(CodeApplication.review_status == status)
    if task_id:
        query = query.where(CodeApplication.task_id == task_id)
    if coding_run_id:
        query = query.where(CodeApplication.coding_run_id == coding_run_id)
    if source_document_id:
        query = query.where(CodeApplication.source_document_id == source_document_id)
    if code_id:
        query = query.where(CodeApplication.code_id == code_id)
    query = query.order_by(CodeApplication.created_at.desc())

    result = await db.execute(query)
    return [ca.to_dict() for ca in result.scalars().all()]


@router.post("/{project_id}")
async def create_code_application(
    project_id: str,
    payload: CreateCodeApplicationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Create a human qualitative code application grounded in the Research Spine."""
    await require_project_access(db, request, project_id, min_role="researcher")
    subject = get_subject(request)
    username = subject.username or subject.id or "human_researcher"

    unit_id = str(uuid.uuid4())
    evidence_unit = EvidenceUnit(
        id=unit_id,
        project_id=project_id,
        task_id=payload.task_id,
        source_document_id=payload.source_document_id,
        source_id=payload.source_document_id or "manual_span",
        stable_id=f"eu-{uuid.uuid4().hex[:8]}",
        unit_type="span",
        source_type=payload.source_type,
        method="manual_qualitative_coding",
        speaker=payload.speaker,
        source_text=payload.source_text,
        source_location=payload.source_location,
        start_offset=payload.start_offset,
        end_offset=payload.end_offset,
        metadata_json=json.dumps(
            {
                "coder": username,
                "created_via": "qualitative_coding_studio",
            }
        ),
    )
    db.add(evidence_unit)

    app_id = str(uuid.uuid4())
    ca = CodeApplication(
        id=app_id,
        project_id=project_id,
        task_id=payload.task_id,
        codebook_version_id=payload.codebook_version_id,
        code_id=payload.code_id,
        evidence_unit_id=unit_id,
        source_document_id=payload.source_document_id,
        source_text=payload.source_text,
        source_location=payload.source_location,
        start_offset=payload.start_offset,
        end_offset=payload.end_offset,
        coder_id=username,
        coder_type="human",
        model_name="human",
        confidence=1.0,
        reasoning=payload.reasoning or "Manual qualitative coding by researcher",
        reliability_status="reconciled",
        reconciliation_status="reconciled",
        promotion_status="accepted",
        review_status="approved",
        reviewed_by=username,
        reviewed_at=datetime.now(UTC),
    )
    db.add(ca)

    edge = ResearchEvidenceEdge(
        id=str(uuid.uuid4()),
        project_id=project_id,
        source_type="evidence_unit",
        source_id=unit_id,
        relation="coded_as",
        target_type="code_application",
        target_id=app_id,
        evidence_unit_id=unit_id,
        task_id=payload.task_id,
        codebook_version_id=payload.codebook_version_id,
        reliability_status="reconciled",
        metadata_json=json.dumps({"coder_type": "human"}),
    )
    db.add(edge)

    rec_decision = ReconciliationDecision(
        id=str(uuid.uuid4()),
        project_id=project_id,
        task_id=payload.task_id,
        evidence_unit_id=unit_id,
        code_application_id=app_id,
        decision_type="human_coding",
        source="human_review",
        accepted_code_id=payload.code_id,
        rationale=payload.reasoning or "Direct qualitative coding by researcher",
        decided_by=username,
    )
    db.add(rec_decision)

    await db.commit()
    await db.refresh(ca)
    return ca.to_dict()


@router.delete("/{application_id}")
async def delete_code_application(
    application_id: str,
    request: Request,
    project_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Delete a code application and its evidence links."""
    await require_project_access(db, request, project_id, min_role="researcher")
    result = await db.execute(
        select(CodeApplication).where(
            CodeApplication.id == application_id,
            CodeApplication.project_id == project_id,
        )
    )
    ca = result.scalar_one_or_none()
    if not ca:
        raise HTTPException(status_code=404, detail="Code application not found")

    await db.execute(
        delete(ResearchEvidenceEdge).where(
            ResearchEvidenceEdge.project_id == project_id,
            ResearchEvidenceEdge.target_id == application_id,
        )
    )
    await db.execute(
        delete(ReconciliationDecision).where(
            ReconciliationDecision.project_id == project_id,
            ReconciliationDecision.code_application_id == application_id,
        )
    )
    await db.delete(ca)
    await db.commit()
    return {"deleted": True, "id": application_id}


@router.get("/{project_id}/pending")
async def get_pending_reviews(
    project_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Get code applications pending human review."""
    await require_project_access(db, request, project_id, min_role="viewer")

    result = await db.execute(
        select(CodeApplication)
        .where(
            CodeApplication.project_id == project_id,
            CodeApplication.review_status == "pending",
        )
        .order_by(CodeApplication.confidence.asc())  # Lowest confidence first
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


@router.post("/{project_id}/synthetic-reconciliation")
async def synthetic_reconciliation(
    project_id: str,
    payload: SyntheticReconciliationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Record isolated benchmark receipts without satisfying human gates."""
    await require_project_access(db, request, project_id, min_role="researcher")
    if not settings.research_validity_synthetic_reconciliation_enabled:
        raise HTTPException(status_code=404, detail="Synthetic reconciliation is disabled.")
    if request.headers.get("x-istara-synthetic-reconciliation") != "benchmark-v1":
        raise HTTPException(
            status_code=403, detail="Synthetic benchmark opt-in header is required."
        )
    try:
        decisions = await create_synthetic_reconciliation_decisions(
            db,
            project_id=project_id,
            coding_run_id=payload.coding_run_id,
            diagnostic_id=payload.diagnostic_id,
            decisions=[item.model_dump() for item in payload.decisions],
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "source": SYNTHETIC_RECONCILIATION_SOURCE,
        "coding_run_id": payload.coding_run_id,
        "diagnostic_id": payload.diagnostic_id,
        "accepted_reportable": False,
        "human_review_required": True,
        "decisions": decisions,
    }


@router.post("/{project_id}/bulk-approve")
async def bulk_approve_high_confidence(
    project_id: str,
    request: Request,
    min_confidence: float = Query(default=0.9, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
):
    """Reject bulk acceptance because it bypasses per-application reconciliation.

    Confidence and inter-coder reliability identify candidates for review; they
    do not constitute the durable human reconciliation decision required by the
    Research Spine. Keep this compatibility route explicit and side-effect free
    so older clients cannot silently promote research evidence.
    """
    await require_project_access(db, request, project_id, min_role="researcher")
    raise HTTPException(
        status_code=422,
        detail=(
            "Bulk approval is disabled: confidence and reliability are review "
            "signals only; each code application requires explicit reconciliation."
        ),
    )
