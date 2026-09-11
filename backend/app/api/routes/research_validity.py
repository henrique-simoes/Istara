"""Research-validity API: evidence units, coding runs, and graph traceability."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_project_access
from app.core.research_validity import (
    DEFAULT_RELIABILITY_THRESHOLD,
    QUALITATIVE_CODING_PROTOCOL,
    RESEARCH_VALIDITY_CONTRACT,
    research_validity_telemetry_contract,
    telemetry_operation_names,
)
from app.core.telemetry import telemetry_recorder
from app.models.code_application import CodeApplication
from app.models.database import get_db
from app.models.research_validity import (
    CodingRun,
    EvidenceUnit,
    ReconciliationDecision,
    ResearchEvidenceEdge,
)
from app.services.research_validity_service import (
    build_evidence_graph_traceability,
    run_independent_coding_run,
)

router = APIRouter(prefix="/research-validity")


class StartCodingRunRequest(BaseModel):
    task_id: str | None = None
    evidence_unit_ids: list[str] | None = None
    codebook_version_id: str | None = None
    threshold: float = Field(default=DEFAULT_RELIABILITY_THRESHOLD, ge=0.0, le=1.0)
    # A governed Research Spine run requires the full independent multi-model
    # path. Lower-assurance one/two-coder math remains available internally for
    # diagnostics, but cannot be selected through the promotion-capable API.
    max_coders: int = Field(default=3, ge=3, le=5)
    limit: int = Field(default=50, ge=1, le=200)


@router.get("/contract")
async def get_research_validity_contract() -> dict:
    """Return the non-negotiable research-validity contract and protocol."""
    return {
        "contract": RESEARCH_VALIDITY_CONTRACT,
        "qualitative_coding_protocol": QUALITATIVE_CODING_PROTOCOL,
        "telemetry_operations": telemetry_operation_names(),
        "telemetry_contract": research_validity_telemetry_contract(),
    }


@router.get("/{project_id}/evidence-units")
async def list_evidence_units(
    project_id: str,
    request: Request,
    task_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List project-scoped evidence units for research review and traceability."""
    await require_project_access(db, request, project_id, min_role="viewer")
    query = select(EvidenceUnit).where(EvidenceUnit.project_id == project_id)
    if task_id:
        query = query.where(EvidenceUnit.task_id == task_id)
    result = await db.execute(
        query.order_by(EvidenceUnit.source_id, EvidenceUnit.unit_index)
        .offset(max(0, offset))
        .limit(max(1, min(limit, 500)))
    )
    return [unit.to_dict() for unit in result.scalars().all()]


@router.get("/{project_id}/coding-runs")
async def list_coding_runs(
    project_id: str,
    request: Request,
    task_id: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List project coding/reliability runs without exposing source content."""
    await require_project_access(db, request, project_id, min_role="viewer")
    query = select(CodingRun).where(CodingRun.project_id == project_id)
    if task_id:
        query = query.where(CodingRun.task_id == task_id)
    result = await db.execute(
        query.order_by(CodingRun.created_at.desc()).limit(max(1, min(limit, 200)))
    )
    return [run.to_dict() for run in result.scalars().all()]


@router.post("/{project_id}/coding-runs")
async def start_coding_run(
    project_id: str,
    payload: StartCodingRunRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Start a governed independent coding run for project evidence units."""
    subject = await require_project_access(db, request, project_id, min_role="researcher")
    if payload.task_id:
        from app.models.task import Task

        task = await db.get(Task, payload.task_id)
        if not task or task.project_id != project_id:
            raise HTTPException(status_code=404, detail="Task not found")
    return await run_independent_coding_run(
        db,
        project_id=project_id,
        task_id=payload.task_id,
        evidence_unit_ids=payload.evidence_unit_ids,
        codebook_version_id=payload.codebook_version_id,
        threshold=payload.threshold,
        max_coders=payload.max_coders,
        limit=payload.limit,
        created_by=subject.username or subject.id,
    )


@router.get("/{project_id}/evidence-graph")
async def list_evidence_graph_edges(
    project_id: str,
    request: Request,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List evidence graph edges used for GraphRAG traceability."""
    await require_project_access(db, request, project_id, min_role="viewer")
    result = await db.execute(
        select(ResearchEvidenceEdge)
        .where(ResearchEvidenceEdge.project_id == project_id)
        .order_by(ResearchEvidenceEdge.created_at.desc())
        .limit(max(1, min(limit, 500)))
    )
    return [edge.to_dict() for edge in result.scalars().all()]


@router.get("/{project_id}/traceability")
async def get_evidence_graph_traceability(
    project_id: str,
    request: Request,
    report_id: str | None = None,
    task_id: str | None = None,
    finding_id: str | None = None,
    coding_run_id: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Answer GraphRAG traceability questions from validated evidence-chain rows."""
    await require_project_access(db, request, project_id, min_role="viewer")
    trace = await build_evidence_graph_traceability(
        db,
        project_id=project_id,
        report_id=report_id,
        task_id=task_id,
        finding_id=finding_id,
        coding_run_id=coding_run_id,
        limit=limit,
    )
    await telemetry_recorder.record_research_validity_event(
        trace_id=f"graph-trace-{project_id[:12]}",
        operation="evidence_graph.traceability",
        project_id=project_id,
        task_id=task_id,
        coding_run_id=coding_run_id,
        status="success",
        retrieval_mode="graph+hybrid",
    )
    return trace


@router.get("/{project_id}/telemetry-audit")
async def get_research_validity_telemetry_audit(
    project_id: str,
    request: Request,
    limit: int = 500,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Summarize project research-validity telemetry as content-free audit handles."""
    await require_project_access(db, request, project_id, min_role="viewer")
    return await telemetry_recorder.get_research_validity_audit(project_id, limit=limit)


@router.get("/{project_id}/reconciliation-decisions")
async def list_reconciliation_decisions(
    project_id: str,
    request: Request,
    task_id: str | None = None,
    coding_run_id: str | None = None,
    evidence_unit_id: str | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List project-scoped disagreement resolution decisions."""
    await require_project_access(db, request, project_id, min_role="viewer")
    query = select(ReconciliationDecision).where(ReconciliationDecision.project_id == project_id)
    if task_id:
        query = query.where(ReconciliationDecision.task_id == task_id)
    if coding_run_id:
        query = query.where(ReconciliationDecision.coding_run_id == coding_run_id)
    if evidence_unit_id:
        query = query.where(ReconciliationDecision.evidence_unit_id == evidence_unit_id)
    result = await db.execute(
        query.order_by(ReconciliationDecision.created_at.desc()).limit(max(1, min(limit, 500)))
    )
    return [decision.to_dict() for decision in result.scalars().all()]


@router.get("/{project_id}/summary")
async def get_research_validity_summary(
    project_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return counts and gate status for the corrected research pipeline."""
    await require_project_access(db, request, project_id, min_role="viewer")
    evidence_count = await db.scalar(
        select(func.count()).select_from(EvidenceUnit).where(EvidenceUnit.project_id == project_id)
    )
    coding_run_count = await db.scalar(
        select(func.count()).select_from(CodingRun).where(CodingRun.project_id == project_id)
    )
    pending_review_count = await db.scalar(
        select(func.count())
        .select_from(CodeApplication)
        .where(
            CodeApplication.project_id == project_id,
            CodeApplication.review_status == "pending",
        )
    )
    accepted_count = await db.scalar(
        select(func.count())
        .select_from(CodeApplication)
        .where(
            CodeApplication.project_id == project_id,
            CodeApplication.review_status == "approved",
            CodeApplication.promotion_status == "accepted",
            CodeApplication.reconciliation_status.in_(("accepted", "reconciled")),
        )
    )
    low_consensus_count = await db.scalar(
        select(func.count())
        .select_from(CodeApplication)
        .where(
            CodeApplication.project_id == project_id,
            CodeApplication.promotion_status.in_(
                ("needs_reconciliation", "needs_human_review", "blocked")
            ),
        )
    )
    reconciliation_decision_count = await db.scalar(
        select(func.count())
        .select_from(ReconciliationDecision)
        .where(ReconciliationDecision.project_id == project_id)
    )

    return {
        "project_id": project_id,
        "evidence_unit_count": evidence_count or 0,
        "coding_run_count": coding_run_count or 0,
        "pending_review_count": pending_review_count or 0,
        "accepted_code_application_count": accepted_count or 0,
        "low_consensus_or_blocked_count": low_consensus_count or 0,
        "reconciliation_decision_count": reconciliation_decision_count or 0,
        "report_gate": "accepted_reconciled_evidence_from_approved_done_tasks_only",
    }
