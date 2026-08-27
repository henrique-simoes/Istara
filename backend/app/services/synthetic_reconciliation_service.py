"""Benchmark-only reconciliation receipts that never satisfy human gates."""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.research_validity import graph_edge_metadata
from app.models.code_application import CodeApplication
from app.models.research_validity import (
    CodingRun,
    ReconciliationDecision,
    ResearchEvidenceEdge,
)

SYNTHETIC_RECONCILIATION_SOURCE = "benchmark_synthetic"
_ALLOWED_DECISIONS = {"accepted", "rejected", "revised", "needs_human_review"}


def _code_application_state(row: CodeApplication) -> dict[str, str]:
    return {
        "code_id": row.code_id,
        "review_status": row.review_status,
        "reliability_status": row.reliability_status,
        "reconciliation_status": row.reconciliation_status,
        "promotion_status": row.promotion_status,
    }


def _route_evidence_for(row: CodeApplication) -> dict[str, Any]:
    try:
        route_evidence = json.loads(row.route_evidence_json or "{}")
    except (json.JSONDecodeError, TypeError):
        route_evidence = {}
    if not isinstance(route_evidence, dict) or not route_evidence:
        raise ValueError(f"Code application {row.id} is missing route evidence provenance.")
    served_model = str(
        route_evidence.get("model") or route_evidence.get("served_model") or ""
    ).strip()
    served_outcome = str(route_evidence.get("outcome") or "").strip().lower()
    try:
        served_request_count = float(route_evidence.get("served_request_count", 0))
    except (TypeError, ValueError):
        served_request_count = 0.0
    if (
        not served_model
        or served_model != str(row.model_name or "").strip()
        or not (served_outcome == "served" or served_request_count > 0)
    ):
        raise ValueError(f"Code application {row.id} is missing route evidence provenance.")
    return route_evidence


def _validate_application(row: CodeApplication, coding_run_id: str) -> dict[str, Any]:
    if not all(
        (
            row.evidence_unit_id,
            row.coding_run_id == coding_run_id,
            str(row.source_text or "").strip(),
            str(row.source_location or "").strip(),
            str(row.coder_id or "").strip(),
            str(row.model_name or "").strip(),
            str(row.route_id or "").strip(),
        )
    ):
        raise ValueError(
            f"Code application {row.id} is missing source, coder, model, or route provenance."
        )
    return _route_evidence_for(row)


def _validate_coverage(
    decisions: list[dict[str, Any]],
    row_by_id: dict[str, CodeApplication],
) -> list[str]:
    requested_ids = [str(item.get("code_application_id") or "").strip() for item in decisions]
    if any(not item_id for item_id in requested_ids) or len(set(requested_ids)) != len(requested_ids):
        raise ValueError("Synthetic decisions must contain unique code application ids.")
    if set(requested_ids) != set(row_by_id):
        raise ValueError(
            "Synthetic reconciliation must cover exactly every application in the coding run."
        )
    return requested_ids


async def _existing_receipts(
    db: AsyncSession,
    *,
    project_id: str,
    coding_run_id: str,
    diagnostic_id: str,
) -> dict[str, ReconciliationDecision]:
    result = await db.execute(
        select(ReconciliationDecision).where(
            ReconciliationDecision.project_id == project_id,
            ReconciliationDecision.coding_run_id == coding_run_id,
            ReconciliationDecision.source == SYNTHETIC_RECONCILIATION_SOURCE,
            ReconciliationDecision.decided_by == f"benchmark-synthetic:{diagnostic_id}",
        )
    )
    return {row.code_application_id: row for row in result.scalars().all() if row.code_application_id}


def _validate_retry_payload(
    decisions: list[dict[str, Any]],
    existing: dict[str, ReconciliationDecision],
    row_by_id: dict[str, CodeApplication],
) -> list[dict[str, Any]]:
    if set(existing) != set(row_by_id) or len(existing) != len(row_by_id):
        raise ValueError("Synthetic diagnostic already has an incomplete receipt set.")
    for item in decisions:
        application_id = item["code_application_id"]
        expected_type = str(item.get("decision_type") or "").strip().lower()
        expected_code = str(item.get("accepted_code_id") or "").strip()
        receipt = existing[application_id]
        if receipt.decision_type != expected_type or receipt.accepted_code_id != expected_code:
            raise ValueError("Synthetic diagnostic already has a different decision payload.")
    return [existing[item["code_application_id"]].to_dict() for item in decisions]


def _build_receipt(
    row: CodeApplication,
    item: dict[str, Any],
    *,
    coding_run_id: str,
    diagnostic_id: str,
    route_evidence: dict[str, Any],
) -> tuple[ReconciliationDecision, ResearchEvidenceEdge]:
    decision_type = str(item.get("decision_type") or "").strip().lower()
    if decision_type not in _ALLOWED_DECISIONS:
        raise ValueError(f"Unsupported synthetic reconciliation decision type: {decision_type}.")
    accepted_code_id = str(item.get("accepted_code_id") or "").strip()
    if decision_type == "revised" and not accepted_code_id:
        raise ValueError("Synthetic revised decisions require accepted_code_id.")
    receipt_evidence = {
        **route_evidence,
        "source": SYNTHETIC_RECONCILIATION_SOURCE,
        "diagnostic_id": diagnostic_id,
        "accepted_reportable": False,
        "human_review_required": True,
        "coding_run_id": coding_run_id,
    }
    decision_id = str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"istara:synthetic-reconciliation:{row.project_id}:{coding_run_id}:{diagnostic_id}:{row.id}",
        )
    )
    decision = ReconciliationDecision(
        id=decision_id,
        project_id=row.project_id,
        task_id=row.task_id,
        coding_run_id=coding_run_id,
        evidence_unit_id=row.evidence_unit_id,
        code_application_id=row.id,
        decision_type=decision_type,
        source=SYNTHETIC_RECONCILIATION_SOURCE,
        accepted_code_id=accepted_code_id,
        rationale=(
            str(item.get("rationale") or "").strip()
            or "Synthetic benchmark diagnostic; human reconciliation remains required."
        ),
        decided_by=f"benchmark-synthetic:{diagnostic_id}",
        previous_state_json=json.dumps(_code_application_state(row)),
        resolved_state_json=json.dumps(_code_application_state(row)),
        route_evidence_json=json.dumps(receipt_evidence),
    )
    edge = ResearchEvidenceEdge(
        id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{decision_id}:edge")),
        project_id=row.project_id,
        source_type="code_application",
        source_id=row.id,
        relation="reconciled_by",
        target_type="reconciliation_decision",
        target_id=decision.id,
        evidence_unit_id=row.evidence_unit_id,
        coding_run_id=coding_run_id,
        task_id=row.task_id,
        codebook_version_id=row.codebook_version_id,
        reliability_status=row.reliability_status,
        metadata_json=json.dumps(
            graph_edge_metadata(
                retrieval_mode="graph+hybrid",
                review_status=row.review_status,
                reliability_status=row.reliability_status,
                route_evidence=receipt_evidence,
            )
            | {
                "source": SYNTHETIC_RECONCILIATION_SOURCE,
                "accepted_reportable": False,
                "human_review_required": True,
            }
        ),
    )
    return decision, edge


async def create_synthetic_reconciliation_decisions(
    db: AsyncSession,
    *,
    project_id: str,
    coding_run_id: str,
    decisions: list[dict[str, Any]],
    diagnostic_id: str,
) -> list[dict[str, Any]]:
    """Persist benchmark receipts without changing human/reportability state."""
    normalized_run_id = (coding_run_id or "").strip()
    normalized_diagnostic_id = (diagnostic_id or "").strip()
    if not normalized_run_id or not normalized_diagnostic_id:
        raise ValueError("coding_run_id and diagnostic_id are required.")
    if not decisions:
        raise ValueError("At least one synthetic reconciliation decision is required.")
    run = await db.scalar(
        select(CodingRun).where(
            CodingRun.id == normalized_run_id,
            CodingRun.project_id == project_id,
        )
    )
    if not run:
        raise LookupError("Coding run not found.")
    rows = list(
        (
            await db.execute(
                select(CodeApplication).where(
                    CodeApplication.project_id == project_id,
                    CodeApplication.coding_run_id == normalized_run_id,
                )
            )
        )
        .scalars()
        .all()
    )
    row_by_id = {row.id: row for row in rows}
    _validate_coverage(decisions, row_by_id)
    created: list[ReconciliationDecision] = []
    existing = await _existing_receipts(
        db,
        project_id=project_id,
        coding_run_id=normalized_run_id,
        diagnostic_id=normalized_diagnostic_id,
    )
    if existing:
        return _validate_retry_payload(decisions, existing, row_by_id)
    for item in decisions:
        row = row_by_id[item["code_application_id"]]
        route_evidence = _validate_application(row, normalized_run_id)
        decision, edge = _build_receipt(
            row,
            item,
            coding_run_id=normalized_run_id,
            diagnostic_id=normalized_diagnostic_id,
            route_evidence=route_evidence,
        )
        db.add(decision)
        db.add(edge)
        created.append(decision)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing = await _existing_receipts(
            db,
            project_id=project_id,
            coding_run_id=normalized_run_id,
            diagnostic_id=normalized_diagnostic_id,
        )
        if existing:
            return _validate_retry_payload(decisions, existing, row_by_id)
        raise
    for decision in created:
        await db.refresh(decision)
    return [decision.to_dict() for decision in created]
