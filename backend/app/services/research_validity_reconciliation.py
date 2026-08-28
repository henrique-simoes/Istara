"""Reconciliation decisions, traceability graph, and task research-validity assessment."""

from __future__ import annotations

import logging

from datetime import UTC, datetime
from typing import Any
import json
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.research_validity import (
    DEFAULT_RELIABILITY_THRESHOLD,
    QUALITATIVE_CODING_PROTOCOL,
    build_qualitative_coding_prompt,
    evaluate_reliability_gate,
    graph_edge_metadata,
    item_level_promotion_statuses,
)
from app.core.telemetry import telemetry_recorder
from app.models.code_application import CodeApplication
from app.models.research_validity import (
    CodingRun,
    CodingRunCoder,
    EvidenceUnit,
    ReconciliationDecision,
    ResearchEvidenceEdge,
)

from app.services.research_validity_schemas import ACCEPTED_PROMOTION_STATUSES, RECONCILED_CODE_APPLICATION_STATUSES, _json_list_value


logger = logging.getLogger(__name__)


async def _task_finding_support_diagnostics(
    db: AsyncSession,
    *,
    project_id: str,
    task_id: str,
    code_rows: list[CodeApplication],
) -> dict:
    """Check item-level finding support instead of accepting a whole task in bulk."""
    from app.models.finding import Fact, Insight, Nugget, Recommendation

    accepted_evidence_unit_ids = {
        row.evidence_unit_id
        for row in code_rows
        if _is_reconciled_code_application(row) and row.evidence_unit_id
    }
    nuggets = (
        (
            await db.execute(
                select(Nugget).where(Nugget.project_id == project_id, Nugget.task_id == task_id)
            )
        )
        .scalars()
        .all()
    )
    facts = (
        (
            await db.execute(
                select(Fact).where(Fact.project_id == project_id, Fact.task_id == task_id)
            )
        )
        .scalars()
        .all()
    )
    insights = (
        (
            await db.execute(
                select(Insight).where(Insight.project_id == project_id, Insight.task_id == task_id)
            )
        )
        .scalars()
        .all()
    )
    recommendations = (
        (
            await db.execute(
                select(Recommendation).where(
                    Recommendation.project_id == project_id,
                    Recommendation.task_id == task_id,
                )
            )
        )
        .scalars()
        .all()
    )

    accepted_nugget_ids: set[str] = set()
    if accepted_evidence_unit_ids:
        edge_rows = (
            (
                await db.execute(
                    select(ResearchEvidenceEdge.source_id).where(
                        ResearchEvidenceEdge.project_id == project_id,
                        ResearchEvidenceEdge.task_id == task_id,
                        ResearchEvidenceEdge.source_type == "nugget",
                        ResearchEvidenceEdge.relation == "grounded_in",
                        ResearchEvidenceEdge.evidence_unit_id.in_(accepted_evidence_unit_ids),
                    )
                )
            )
            .scalars()
            .all()
        )
        accepted_nugget_ids = set(edge_rows)

    accepted_fact_ids: set[str] = set()
    accepted_insight_ids: set[str] = set()
    accepted_recommendation_ids: set[str] = set()
    unsupported: list[dict[str, str]] = []

    for row in nuggets:
        if row.id not in accepted_nugget_ids:
            unsupported.append(
                {
                    "type": "nugget",
                    "id": row.id,
                    "reason": "no accepted coded evidence unit is linked to this source nugget",
                }
            )

    for row in facts:
        nugget_ids = _json_list_value(row.nugget_ids)
        if not nugget_ids:
            unsupported.append(
                {"type": "fact", "id": row.id, "reason": "fact has no linked nuggets"}
            )
            continue
        missing = [nid for nid in nugget_ids if nid not in accepted_nugget_ids]
        if missing:
            unsupported.append(
                {
                    "type": "fact",
                    "id": row.id,
                    "reason": "fact depends on unaccepted nugget(s): " + ", ".join(missing[:5]),
                }
            )
        else:
            accepted_fact_ids.add(row.id)

    for row in insights:
        fact_ids = _json_list_value(row.fact_ids)
        if not fact_ids:
            unsupported.append(
                {
                    "type": "insight",
                    "id": row.id,
                    "reason": "insight has no linked facts",
                }
            )
            continue
        missing = [fid for fid in fact_ids if fid not in accepted_fact_ids]
        if missing:
            unsupported.append(
                {
                    "type": "insight",
                    "id": row.id,
                    "reason": "insight depends on unaccepted fact(s): " + ", ".join(missing[:5]),
                }
            )
        else:
            accepted_insight_ids.add(row.id)

    for row in recommendations:
        insight_ids = _json_list_value(row.insight_ids)
        if not insight_ids:
            unsupported.append(
                {
                    "type": "recommendation",
                    "id": row.id,
                    "reason": "recommendation has no linked insights",
                }
            )
            continue
        missing = [iid for iid in insight_ids if iid not in accepted_insight_ids]
        if missing:
            unsupported.append(
                {
                    "type": "recommendation",
                    "id": row.id,
                    "reason": "recommendation depends on unaccepted insight(s): "
                    + ", ".join(missing[:5]),
                }
            )
        else:
            accepted_recommendation_ids.add(row.id)

    return {
        "accepted_evidence_unit_ids": sorted(accepted_evidence_unit_ids),
        "accepted_nugget_ids": sorted(accepted_nugget_ids),
        "accepted_fact_ids": sorted(accepted_fact_ids),
        "accepted_insight_ids": sorted(accepted_insight_ids),
        "accepted_recommendation_ids": sorted(accepted_recommendation_ids),
        "unsupported_findings": unsupported,
        "unsupported_finding_count": len(unsupported),
    }


def task_validation_payload_with_coding_run(
    existing_validation_result: str | None,
    coding_run: dict,
) -> str:
    """Merge coding-run status into task validation metadata."""
    try:
        payload = json.loads(existing_validation_result or "{}")
        if not isinstance(payload, dict):
            payload = {}
    except Exception:
        payload = {}
    payload["research_validity"] = {
        "coding_run_id": coding_run.get("id"),
        "promotion_status": coding_run.get("promotion_status"),
        "reliability_method": coding_run.get("reliability_method"),
        "kappa": coding_run.get("kappa"),
        "alpha": coding_run.get("alpha"),
        "rater_count": coding_run.get("rater_count"),
        "distinct_model_count": coding_run.get("distinct_model_count"),
        "fallback_reason": coding_run.get("fallback_reason"),
    }
    return json.dumps(payload)


def mark_task_provisional_skill_artifacts(task: Any) -> None:
    """Block skill-created artifacts that have not entered accepted Spine gates."""
    task.review_state = (
        task.review_state
        if task.review_state and task.review_state != "none"
        else "awaiting_review"
    )
    task.what_to_review = task.what_to_review or (
        "Skill-generated research artifacts are provisional: exact raw-source "
        "evidence units, coding reliability, reconciliation, and Done approval "
        "are required before they can become report evidence."
    )
    try:
        validation_payload = json.loads(task.validation_result or "{}")
        if not isinstance(validation_payload, dict):
            validation_payload = {}
    except Exception:
        validation_payload = {}
    current = validation_payload.get("research_validity", {})
    validation_payload["research_validity"] = {
        **(current if isinstance(current, dict) else {}),
        "status": "provisional",
        "promotion_status": "blocked",
        "report_allowed": False,
        "reason": "skill_output_missing_exact_source_span_or_accepted_coding_run",
    }
    task.validation_result = json.dumps(validation_payload)


def add_agent_initial_code_applications(
    db: AsyncSession,
    *,
    project_id: str,
    task_id: str,
    tags: list,
    evidence_unit_id: str | None,
    source_document_id: str | None,
    source_text: str,
    source_location: str,
    start_offset: int | None,
    end_offset: int | None,
    agent_id: str,
    confidence: float,
    reasoning: str,
) -> int:
    """Persist lower-assurance skill-provided codes before governed coding."""
    count = 0
    for tag in tags[:5]:
        if not isinstance(tag, str) or not tag.strip():
            continue
        db.add(
            CodeApplication(
                id=str(uuid.uuid4()),
                project_id=project_id,
                task_id=task_id,
                code_id=tag,
                evidence_unit_id=evidence_unit_id,
                source_document_id=source_document_id,
                source_text=source_text,
                source_location=source_location,
                start_offset=start_offset,
                end_offset=end_offset,
                coder_id=agent_id,
                coder_type="llm",
                route_evidence_json=json.dumps(
                    {
                        "route_kind": "agent_initial_code_application",
                        "agent_id": agent_id,
                        "task_id": task_id,
                    }
                ),
                confidence=confidence,
                reasoning=reasoning,
                reliability_status="needs_human_review",
                reconciliation_status="unreconciled",
                promotion_status="needs_human_review",
            )
        )
        count += 1
    return count


def _code_application_state(row: CodeApplication) -> dict:
    return {
        "code_id": row.code_id,
        "review_status": row.review_status,
        "reliability_status": row.reliability_status,
        "reconciliation_status": row.reconciliation_status,
        "promotion_status": row.promotion_status,
    }


async def _refresh_coding_run_reconciliation_status(
    db: AsyncSession,
    *,
    project_id: str,
    coding_run_id: str | None,
) -> None:
    if not coding_run_id:
        return
    run = await db.get(CodingRun, coding_run_id)
    if not run or run.project_id != project_id:
        return
    code_rows = (
        (
            await db.execute(
                select(CodeApplication).where(
                    CodeApplication.project_id == project_id,
                    CodeApplication.coding_run_id == coding_run_id,
                )
            )
        )
        .scalars()
        .all()
    )
    unresolved_count = sum(1 for row in code_rows if _is_unresolved_code_application(row))
    accepted_count = sum(1 for row in code_rows if _is_reconciled_code_application(row))
    if (
        unresolved_count == 0
        and accepted_count > 0
        and run.promotion_status not in ACCEPTED_PROMOTION_STATUSES
    ):
        run.promotion_status = "accepted_after_reconciliation"
        run.fallback_reason = "Human reconciliation accepted evidence after low agreement."
    elif unresolved_count == 0 and code_rows and accepted_count == 0:
        run.promotion_status = "rejected_after_reconciliation"
        run.fallback_reason = "Human reconciliation rejected all coded evidence."


def _is_unresolved_code_application(row: CodeApplication) -> bool:
    if (
        row.promotion_status == "rejected"
        or row.reconciliation_status == "rejected"
        or row.review_status == "rejected"
    ):
        return False
    return not _is_reconciled_code_application(row)


def _is_reconciled_code_application(row: CodeApplication) -> bool:
    """Return whether an application has both reliability and reconciliation.

    A passing Fleiss/alpha run is not a human decision. Keep report support
    fail-closed until the application carries the durable reconciliation state
    written by ``create_reconciliation_decision``.
    """
    return (
        row.promotion_status in ACCEPTED_PROMOTION_STATUSES
        and row.reconciliation_status in RECONCILED_CODE_APPLICATION_STATUSES
    )


async def create_reconciliation_decision(
    db: AsyncSession,
    *,
    project_id: str,
    code_application_id: str,
    decision_type: str,
    decided_by: str,
    rationale: str = "",
    accepted_code_id: str | None = None,
    source: str = "human_review",
) -> dict:
    """Persist a reconciliation decision and mirror it onto the code application."""
    normalized_decision = (decision_type or "").strip().lower()
    if normalized_decision not in {
        "accepted",
        "rejected",
        "revised",
        "needs_human_review",
    }:
        raise ValueError("Unsupported reconciliation decision type.")
    result = await db.execute(
        select(CodeApplication).where(
            CodeApplication.id == code_application_id,
            CodeApplication.project_id == project_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise LookupError("Code application not found.")

    previous_state = _code_application_state(row)
    if normalized_decision == "accepted":
        row.review_status = "approved"
        row.reconciliation_status = "accepted"
        row.promotion_status = "accepted"
        if row.reliability_status not in ("accepted", "reliable", "passed"):
            row.reliability_status = "human_reconciled"
    elif normalized_decision == "rejected":
        row.review_status = "rejected"
        row.reconciliation_status = "rejected"
        row.promotion_status = "rejected"
        row.reliability_status = "rejected"
    elif normalized_decision == "revised" and accepted_code_id:
        row.code_id = accepted_code_id
        row.review_status = "approved"
        row.reconciliation_status = "reconciled"
        row.promotion_status = "accepted"
        row.reliability_status = "human_reconciled"
    else:
        row.review_status = "modified"
        row.reconciliation_status = "revised"
        row.promotion_status = "needs_reconciliation"
        row.reliability_status = "needs_human_review"

    row.reviewed_by = decided_by or "local-user"
    row.reviewed_at = datetime.now(UTC)
    resolved_state = _code_application_state(row)
    try:
        route_evidence = json.loads(row.route_evidence_json or "{}")
    except json.JSONDecodeError:
        route_evidence = {}

    decision = ReconciliationDecision(
        id=str(uuid.uuid4()),
        project_id=project_id,
        task_id=row.task_id,
        coding_run_id=row.coding_run_id,
        evidence_unit_id=row.evidence_unit_id,
        code_application_id=row.id,
        decision_type=normalized_decision,
        source=source,
        accepted_code_id=(
            accepted_code_id or row.code_id if row.promotion_status == "accepted" else ""
        ),
        rationale=rationale,
        decided_by=row.reviewed_by or "",
        previous_state_json=json.dumps(previous_state),
        resolved_state_json=json.dumps(resolved_state),
        route_evidence_json=json.dumps(route_evidence),
    )
    db.add(decision)
    db.add(
        ResearchEvidenceEdge(
            id=str(uuid.uuid4()),
            project_id=project_id,
            source_type="code_application",
            source_id=row.id,
            relation="reconciled_by",
            target_type="reconciliation_decision",
            target_id=decision.id,
            evidence_unit_id=row.evidence_unit_id,
            coding_run_id=row.coding_run_id,
            task_id=row.task_id,
            codebook_version_id=row.codebook_version_id,
            reliability_status=row.reliability_status,
            metadata_json=json.dumps(
                graph_edge_metadata(
                    retrieval_mode="graph+hybrid",
                    review_status=row.review_status,
                    reliability_status=row.reliability_status,
                    route_evidence=route_evidence,
                )
            ),
        )
    )
    await _refresh_coding_run_reconciliation_status(
        db,
        project_id=project_id,
        coding_run_id=row.coding_run_id,
    )
    await db.commit()
    await db.refresh(row)
    await db.refresh(decision)
    await telemetry_recorder.record_research_validity_event(
        trace_id=uuid.uuid4().hex[:36],
        operation="reconciliation_decision.create",
        project_id=project_id,
        task_id=row.task_id,
        status="success",
        route_id=row.route_id,
        donor_id=row.donor_id,
        coding_run_id=row.coding_run_id or "",
        evidence_unit_id=row.evidence_unit_id or "",
        codebook_version_id=row.codebook_version_id or "",
    )
    payload = decision.to_dict()
    payload["code_application"] = row.to_dict()
    return payload


async def _load_traceability_findings(
    db: AsyncSession,
    *,
    project_id: str,
    finding_ids: set[str],
    task_ids: set[str],
    finding_id: str | None,
) -> tuple[list[dict], dict[str, dict]]:
    from app.models.finding import Fact, Insight, Nugget, Recommendation

    finding_models = (
        ("nugget", Nugget),
        ("fact", Fact),
        ("insight", Insight),
        ("recommendation", Recommendation),
    )
    rows: list[dict] = []
    by_id: dict[str, dict] = {}
    for finding_type, model_cls in finding_models:
        query = select(model_cls).where(model_cls.project_id == project_id)
        if finding_ids:
            query = query.where(model_cls.id.in_(finding_ids))
        elif task_ids:
            query = query.where(model_cls.task_id.in_(task_ids))
        elif finding_id:
            query = query.where(model_cls.id == finding_id)
        else:
            continue
        result = await db.execute(query)
        for row in result.scalars().all():
            payload = {
                "id": row.id,
                "type": finding_type,
                "task_id": getattr(row, "task_id", None),
                "phase": getattr(row, "phase", ""),
                "confidence": getattr(row, "confidence", None),
            }
            rows.append(payload)
            by_id[row.id] = payload
    return rows, by_id


async def build_evidence_graph_traceability(
    db: AsyncSession,
    *,
    project_id: str,
    report_id: str | None = None,
    task_id: str | None = None,
    finding_id: str | None = None,
    coding_run_id: str | None = None,
    limit: int = 50,
) -> dict:
    """Build a GraphRAG-ready traceability answer from stored evidence-chain data."""
    from app.models.project_report import ProjectReport

    capped_limit = max(1, min(limit, 100))
    report_query = (
        select(ProjectReport)
        .where(ProjectReport.project_id == project_id)
        .order_by(ProjectReport.updated_at.desc())
        .limit(capped_limit)
    )
    if report_id:
        report_query = select(ProjectReport).where(
            ProjectReport.project_id == project_id,
            ProjectReport.id == report_id,
        )
    report_rows = list((await db.execute(report_query)).scalars().all())

    report_finding_ids: set[str] = set()
    report_index: list[dict] = []
    for report in report_rows:
        finding_ids = _json_list_value(report.finding_ids_json)
        if finding_id and finding_id not in finding_ids and not report_id:
            continue
        report_finding_ids.update(finding_ids)
        report_index.append(
            {
                **report.to_dict(),
                "finding_ids": finding_ids,
                "source_document_ids": _json_list_value(report.source_document_ids_json),
                "codebook_version_id": report.codebook_version_id,
            }
        )

    seed_task_ids = {task_id} if task_id else set()
    findings, finding_by_id = await _load_traceability_findings(
        db,
        project_id=project_id,
        finding_ids=report_finding_ids,
        task_ids=seed_task_ids,
        finding_id=finding_id,
    )
    task_ids = {row["task_id"] for row in findings if row.get("task_id")}
    if task_id:
        task_ids.add(task_id)

    normalized_coding_run_id = str(coding_run_id or "").strip() or None
    code_query = select(CodeApplication).where(CodeApplication.project_id == project_id)
    if normalized_coding_run_id:
        # Project-level benchmark coding runs intentionally have no task_id.
        # An explicit run scope keeps their source-grounded applications
        # observable without broadening the default project trace.
        code_query = code_query.where(
            CodeApplication.coding_run_id == normalized_coding_run_id
        )
        if task_ids:
            code_query = code_query.where(CodeApplication.task_id.in_(task_ids))
    elif task_ids:
        code_query = code_query.where(CodeApplication.task_id.in_(task_ids))
    elif finding_id or report_id or task_id:
        code_query = code_query.where(CodeApplication.task_id == "__no_task_match__")
    code_rows = list((await db.execute(code_query)).scalars().all())
    code_applications = [row.to_dict() for row in code_rows[: capped_limit * 10]]
    unresolved = [row for row in code_rows if _is_unresolved_code_application(row)]

    run_ids = {row.coding_run_id for row in code_rows if row.coding_run_id}
    if normalized_coding_run_id:
        run_ids.add(normalized_coding_run_id)
    coding_runs: list[dict] = []
    if run_ids:
        run_rows = (
            (
                await db.execute(
                    select(CodingRun)
                    .where(CodingRun.project_id == project_id, CodingRun.id.in_(run_ids))
                    .order_by(CodingRun.created_at.desc())
                )
            )
            .scalars()
            .all()
        )
        coding_runs = [run.to_dict() for run in run_rows]

    task_gates: dict[str, dict] = {}
    for scoped_task_id in sorted(task_ids):
        task_gates[scoped_task_id] = await assess_task_research_validity(
            db,
            project_id=project_id,
            task_id=scoped_task_id,
        )

    decision_query = select(ReconciliationDecision).where(
        ReconciliationDecision.project_id == project_id
    )
    if normalized_coding_run_id:
        decision_query = decision_query.where(
            ReconciliationDecision.coding_run_id == normalized_coding_run_id
        )
        if task_ids:
            decision_query = decision_query.where(
                ReconciliationDecision.task_id.in_(task_ids)
            )
    elif task_ids:
        decision_query = decision_query.where(ReconciliationDecision.task_id.in_(task_ids))
    elif run_ids:
        decision_query = decision_query.where(ReconciliationDecision.coding_run_id.in_(run_ids))
    decisions = list(
        (
            await db.execute(
                decision_query.order_by(ReconciliationDecision.created_at.desc()).limit(
                    capped_limit * 5
                )
            )
        )
        .scalars()
        .all()
    )

    edge_query = select(ResearchEvidenceEdge).where(ResearchEvidenceEdge.project_id == project_id)
    if normalized_coding_run_id:
        edge_query = edge_query.where(
            ResearchEvidenceEdge.coding_run_id == normalized_coding_run_id
        )
        if task_ids:
            edge_query = edge_query.where(ResearchEvidenceEdge.task_id.in_(task_ids))
    elif task_ids:
        edge_query = edge_query.where(ResearchEvidenceEdge.task_id.in_(task_ids))
    elif run_ids:
        edge_query = edge_query.where(ResearchEvidenceEdge.coding_run_id.in_(run_ids))
    edges = list(
        (
            await db.execute(
                edge_query.order_by(ResearchEvidenceEdge.created_at.desc()).limit(capped_limit * 10)
            )
        )
        .scalars()
        .all()
    )

    report_dependencies: list[dict] = []
    for report in report_index:
        report_findings = [
            finding_by_id[fid] for fid in report["finding_ids"] if fid in finding_by_id
        ]
        report_task_ids = sorted({row["task_id"] for row in report_findings if row.get("task_id")})
        report_unresolved = [
            row.to_dict()
            for row in unresolved
            if row.task_id and row.task_id in set(report_task_ids)
        ]
        missing_task_gates = [
            tid
            for tid in report_task_ids
            if tid not in task_gates or "report_allowed" not in task_gates.get(tid, {})
        ]
        report_allowed = (
            bool(report_task_ids)
            and not missing_task_gates
            and all(bool(task_gates[tid].get("report_allowed")) for tid in report_task_ids)
        )
        report_dependencies.append(
            {
                "report_id": report["id"],
                "title": report["title"],
                "layer": report["layer"],
                "finding_ids": report["finding_ids"],
                "task_ids": report_task_ids,
                "finding_count": len(report_findings),
                "low_agreement_dependency_count": len(report_unresolved),
                "missing_task_gate_count": len(missing_task_gates),
                "missing_task_gate_ids": missing_task_gates,
                "report_allowed_by_research_validity": report_allowed,
                "blocked_code_applications": report_unresolved,
            }
        )

    task_dependencies = [
        {
            "task_id": scoped_task_id,
            "report_gate": task_gates.get(scoped_task_id, {}),
            "code_application_count": sum(1 for row in code_rows if row.task_id == scoped_task_id),
            "unresolved_code_application_count": sum(
                1 for row in unresolved if row.task_id == scoped_task_id
            ),
            "accepted_code_application_count": sum(
                1
                for row in code_rows
                if row.task_id == scoped_task_id
                and _is_reconciled_code_application(row)
            ),
        }
        for scoped_task_id in sorted(task_ids)
    ]

    return {
        "project_id": project_id,
        "filters": {
            "report_id": report_id,
            "task_id": task_id,
            "finding_id": finding_id,
            "coding_run_id": normalized_coding_run_id,
            "limit": capped_limit,
        },
        "retrieval_mode": "graph+hybrid",
        "contract": {
            "graph_role": "synthesis_and_traceability",
            "hybrid_rag_role": "exact_evidence_backfill",
            "promotion_rule": (
                "graph_traceability_cannot_bypass_coding_reliability_reconciliation_or_done_gates"
            ),
        },
        "reports": report_index,
        "findings": findings,
        "task_dependencies": task_dependencies,
        "report_dependencies": report_dependencies,
        "coding_runs": coding_runs,
        "code_applications": code_applications,
        "reconciliation_decisions": [decision.to_dict() for decision in decisions],
        "evidence_graph_edges": [edge.to_dict() for edge in edges],
        "low_agreement_dependencies": [row.to_dict() for row in unresolved],
        "summary": {
            "report_count": len(report_index),
            "finding_count": len(findings),
            "task_count": len(task_dependencies),
            "coding_run_count": len(coding_runs),
            "code_application_count": len(code_applications),
            "reconciliation_decision_count": len(decisions),
            "evidence_graph_edge_count": len(edges),
            "low_agreement_dependency_count": len(unresolved),
            "blocked_report_count": sum(
                1
                for report in report_dependencies
                if report["low_agreement_dependency_count"] > 0
                or not report["report_allowed_by_research_validity"]
            ),
        },
    }


async def assess_task_research_validity(
    db: AsyncSession,
    *,
    project_id: str,
    task_id: str,
) -> dict:
    """Return whether task-bound findings may flow into reports."""
    from app.models.finding import Fact, Insight, Nugget, Recommendation

    latest_run_result = await db.execute(
        select(CodingRun)
        .where(CodingRun.project_id == project_id, CodingRun.task_id == task_id)
        .order_by(CodingRun.created_at.desc())
        .limit(1)
    )
    latest_run = latest_run_result.scalar_one_or_none()
    code_rows = (
        (
            await db.execute(
                select(CodeApplication).where(
                    CodeApplication.project_id == project_id,
                    CodeApplication.task_id == task_id,
                )
            )
        )
        .scalars()
        .all()
    )
    task_finding_count = 0
    for model_cls in (Nugget, Fact, Insight, Recommendation):
        rows = (
            (
                await db.execute(
                    select(model_cls.id).where(
                        model_cls.project_id == project_id,
                        model_cls.task_id == task_id,
                    )
                )
            )
            .scalars()
            .all()
        )
        task_finding_count += len(rows)
    accepted_count = sum(1 for row in code_rows if _is_reconciled_code_application(row))
    unresolved_count = sum(1 for row in code_rows if _is_unresolved_code_application(row))
    base = {
        "latest_coding_run": latest_run.to_dict() if latest_run else None,
        "code_application_count": len(code_rows),
        "task_finding_count": task_finding_count,
        "accepted_code_application_count": accepted_count,
        "unresolved_code_application_count": unresolved_count,
    }

    if task_finding_count == 0 and not code_rows:
        return {
            **base,
            "report_allowed": False,
            "reason": (
                "Task has no accepted/reconciled evidence or Research Spine artifacts to report."
            ),
        }
    if unresolved_count:
        return {
            **base,
            "report_allowed": False,
            "reason": f"Task has {unresolved_count} unreconciled code application(s).",
        }
    if (
        latest_run
        and code_rows
        and latest_run.promotion_status not in ACCEPTED_PROMOTION_STATUSES
    ):
        return {
            **base,
            "report_allowed": False,
            "reason": (
                "Latest task coding run is not accepted "
                f"({latest_run.promotion_status or latest_run.status})."
            ),
        }
    accepted_document_rows = [
        row
        for row in code_rows
        if _is_reconciled_code_application(row) and row.source_document_id
    ]
    if accepted_document_rows:
        from app.models.document import Document

        source_document_ids = {str(row.source_document_id) for row in accepted_document_rows}
        current_documents = (
            (
                await db.execute(
                    select(Document).where(
                        Document.project_id == project_id,
                        Document.id.in_(source_document_ids),
                    )
                )
            )
            .scalars()
            .all()
        )
        current_by_id = {document.id: document for document in current_documents}
        evidence_unit_ids = {
            str(row.evidence_unit_id)
            for row in accepted_document_rows
            if row.evidence_unit_id
        }
        units = (
            (
                await db.execute(
                    select(EvidenceUnit).where(
                        EvidenceUnit.project_id == project_id,
                        EvidenceUnit.id.in_(evidence_unit_ids),
                    )
                )
            )
            .scalars()
            .all()
            if evidence_unit_ids
            else []
        )
        unit_by_id = {unit.id: unit for unit in units}
        stale_source_rows = []
        for row in accepted_document_rows:
            document = current_by_id.get(str(row.source_document_id))
            unit = unit_by_id.get(str(row.evidence_unit_id or ""))
            try:
                unit_metadata = json.loads(unit.metadata_json or "{}") if unit else {}
            except (json.JSONDecodeError, TypeError):
                unit_metadata = {}
            unit_version = unit_metadata.get("document_version")
            version_is_current = False
            if document is not None:
                try:
                    version_is_current = unit_version is None or int(unit_version) == int(
                        document.version or 1
                    )
                except (TypeError, ValueError):
                    version_is_current = False
            if document is None or not version_is_current:
                stale_source_rows.append(row)
        if stale_source_rows:
            return {
                **base,
                "report_allowed": False,
                "stale_source_code_application_count": len(stale_source_rows),
                "reason": (
                    f"Task has {len(stale_source_rows)} accepted code application(s) "
                    "grounded in a deleted or superseded source document."
                ),
            }
    support = await _task_finding_support_diagnostics(
        db,
        project_id=project_id,
        task_id=task_id,
        code_rows=list(code_rows),
    )
    base_with_support = {**base, **support}
    if task_finding_count and not code_rows:
        return {
            **base_with_support,
            "report_allowed": False,
            "reason": "Task has reportable findings but no coded evidence applications.",
        }
    if code_rows and accepted_count == 0:
        return {
            **base_with_support,
            "report_allowed": False,
            "reason": "Task has code applications but no accepted/reconciled coded evidence.",
        }
    if task_finding_count and support["unsupported_finding_count"]:
        unsupported_ids = [
            f"{row['type']}:{row['id']}" for row in support["unsupported_findings"][:5]
        ]
        return {
            **base_with_support,
            "report_allowed": False,
            "reason": (
                f"Task has {support['unsupported_finding_count']} finding(s) without "
                "accepted/reconciled source evidence: " + ", ".join(unsupported_ids)
            ),
        }
    return {
        **base_with_support,
        "report_allowed": True,
        "reason": "Task has no pending research-validity blocker.",
    }
