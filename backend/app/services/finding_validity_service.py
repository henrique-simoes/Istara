"""Content-free reportability status for visible findings."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.design_screen import DesignDecision
from app.models.finding import Fact, Insight, Nugget, Recommendation
from app.models.task import Task, TaskStatus
from app.services.research_validity_service import assess_task_research_validity


PROVISIONAL_DESIGN_DECISION_RATIONALE = (
    "Provisional Research Spine candidate: this design decision is not reportable "
    "until every linked recommendation or insight traces to accepted/reconciled "
    "evidence and a human-approved Done task."
)


def parse_json_list(raw: Any) -> list:
    if isinstance(raw, list):
        return raw
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    return parsed if isinstance(parsed, list) else []


async def ensure_project_link_ids(
    db: AsyncSession,
    *,
    project_id: str,
    model,
    ids: list[str],
    field_name: str,
) -> list[str]:
    """Return project-local IDs or reject links that would bypass project scope."""
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw_id in ids:
        item = str(raw_id or "").strip()
        if item and item not in seen:
            cleaned.append(item)
            seen.add(item)
    if not cleaned:
        return []

    rows = await db.execute(
        select(model.id).where(model.project_id == project_id, model.id.in_(cleaned))
    )
    found = {str(row_id) for row_id in rows.scalars().all()}
    missing = [item for item in cleaned if item not in found]
    if missing:
        raise HTTPException(
            status_code=422, detail=f"{field_name} contains unknown records for this project."
        )
    return cleaned


def provisional_design_decision_rationale(rationale: str) -> str:
    """Append the Research Spine provisional marker to visible design decisions."""
    clean = (rationale or "").strip()
    if PROVISIONAL_DESIGN_DECISION_RATIONALE in clean:
        return clean
    if clean:
        return f"{clean}\n\n{PROVISIONAL_DESIGN_DECISION_RATIONALE}"
    return PROVISIONAL_DESIGN_DECISION_RATIONALE


def provisional_finding_validity(
    task_id: str | None = None, reason: str | None = None
) -> dict[str, Any]:
    return {
        "status": "provisional",
        "report_allowed": False,
        "task_id": task_id,
        "done_approved": False,
        "reason": reason
        or "Finding is provisional until linked to accepted coded evidence and a human-approved Done task.",
        "policy": "finding_visibility_does_not_bypass_coding_reliability_review_or_done_report_gates",
    }


async def chain_research_validity_diagnostics(
    db: AsyncSession,
    *,
    project_id: str,
    chain: dict[str, list],
) -> dict[str, Any]:
    """Attach content-free task validity gates to an evidence chain."""
    model_by_type = {
        "nugget": Nugget,
        "fact": Fact,
        "insight": Insight,
        "recommendation": Recommendation,
    }
    task_ids: set[str] = set()
    finding_task_ids: dict[str, str] = {}
    taskless_finding_ids: list[str] = []
    for finding_type, model in model_by_type.items():
        ids = [
            str(getattr(item, "id", "") or (item.get("id") if isinstance(item, dict) else ""))
            for item in chain.get(finding_type, [])
        ]
        ids = [item_id for item_id in ids if item_id]
        if not ids:
            continue
        rows = await db.execute(
            select(model.id, model.task_id).where(
                model.project_id == project_id,
                model.id.in_(ids),
            )
        )
        for finding_id, task_id in rows.all():
            if task_id:
                task_ids.add(task_id)
                finding_task_ids[str(finding_id)] = str(task_id)
            else:
                taskless_finding_ids.append(str(finding_id))

    task_rows = await db.execute(
        select(Task.id, Task.status, Task.review_state).where(
            Task.project_id == project_id,
            Task.id.in_(task_ids),
        )
    )
    done_approved_by_task = {
        task_id: status == TaskStatus.DONE and review_state == "approved"
        for task_id, status, review_state in task_rows.all()
    }
    task_gates = {}
    for task_id in sorted(task_ids):
        gate = await assess_task_research_validity(db, project_id=project_id, task_id=task_id)
        done_approved = done_approved_by_task.get(task_id, False)
        gate_allowed = bool(gate.get("report_allowed", False)) and done_approved
        task_gates[task_id] = {
            **gate,
            "done_approved": done_approved,
            "report_allowed": gate_allowed,
            "report_block_reason": _chain_report_block_reason(gate, done_approved),
        }
    report_allowed = (
        bool(task_gates)
        and not taskless_finding_ids
        and all(gate.get("report_allowed", False) for gate in task_gates.values())
    )
    report_block_reason = None
    if taskless_finding_ids:
        report_block_reason = (
            "Evidence chain contains taskless or legacy/unverified findings that "
            "are not attached to a human-approved Done task."
        )
    elif not task_gates:
        report_block_reason = (
            "Evidence chain has no governed task gate, so it cannot be report evidence."
        )
    elif not report_allowed:
        report_block_reason = "One or more linked task gates blocks report evidence."

    return {
        "task_ids": sorted(task_ids),
        "finding_task_ids": finding_task_ids,
        "taskless_finding_ids": taskless_finding_ids,
        "task_gates": task_gates,
        "report_allowed": report_allowed,
        "report_block_reason": report_block_reason,
        "policy": "evidence_chain_visibility_does_not_bypass_coding_reliability_review_or_done_report_gates",
    }


async def finding_research_validity_map(
    db: AsyncSession,
    *,
    project_id: str,
    findings: list[Any],
) -> dict[str, dict[str, Any]]:
    """Map visible findings to their current research-validity gate state."""
    task_ids = sorted(
        {
            str(getattr(item, "task_id", "") or "")
            for item in findings
            if str(getattr(item, "task_id", "") or "").strip()
        }
    )
    task_status: dict[str, bool] = {}
    if task_ids:
        task_rows = await db.execute(
            select(Task.id, Task.status, Task.review_state).where(
                Task.project_id == project_id,
                Task.id.in_(task_ids),
            )
        )
        task_status = {
            str(task_id): status == TaskStatus.DONE and review_state == "approved"
            for task_id, status, review_state in task_rows.all()
        }

    gate_by_task: dict[str, dict[str, Any]] = {}
    for task_id in task_ids:
        gate = await assess_task_research_validity(db, project_id=project_id, task_id=task_id)
        done_approved = task_status.get(task_id, False)
        report_allowed = bool(gate.get("report_allowed", False)) and done_approved
        gate_by_task[task_id] = {
            "status": "accepted" if report_allowed else "provisional",
            "report_allowed": report_allowed,
            "task_id": task_id,
            "done_approved": done_approved,
            "reason": _finding_gate_reason(gate, done_approved, report_allowed),
            "code_application_count": gate.get("code_application_count", 0),
            "accepted_code_application_count": gate.get("accepted_code_application_count", 0),
            "policy": "finding_visibility_does_not_bypass_coding_reliability_review_or_done_report_gates",
        }

    validity_by_finding: dict[str, dict[str, Any]] = {}
    for item in findings:
        finding_id = str(getattr(item, "id", "") or "")
        task_id = str(getattr(item, "task_id", "") or "").strip() or None
        if finding_id:
            validity_by_finding[finding_id] = (
                gate_by_task.get(task_id) if task_id else provisional_finding_validity(task_id=None)
            )
    return validity_by_finding


async def design_decision_research_validity_map(
    db: AsyncSession,
    *,
    project_id: str,
    decisions: list[DesignDecision],
) -> dict[str, dict[str, Any]]:
    """Gate design decisions by the accepted status of their source findings.

    Interfaces may transform accepted research into design artifacts, but the
    design artifact itself must not become report-traceable when its linked
    recommendation/insight inputs are still provisional.
    """
    source_ids_by_decision: dict[str, list[str]] = {
        str(decision.id): _parse_json_string_list(decision.recommendation_ids)
        for decision in decisions
    }
    source_ids = sorted({item for items in source_ids_by_decision.values() for item in items})
    if not source_ids:
        return {
            str(decision.id): _design_decision_provisional(
                source_ids=[],
                reason=(
                    "Design decision has no linked accepted recommendation or insight "
                    "to trace through the Research Spine."
                ),
            )
            for decision in decisions
        }

    resolved_by_id: dict[str, Any] = {}
    for model in (Insight, Recommendation):
        rows = await db.execute(
            select(model).where(
                model.project_id == project_id,
                model.id.in_(source_ids),
            )
        )
        for row in rows.scalars().all():
            resolved_by_id[str(row.id)] = row

    source_validity = await finding_research_validity_map(
        db,
        project_id=project_id,
        findings=list(resolved_by_id.values()),
    )

    validity_by_decision: dict[str, dict[str, Any]] = {}
    for decision_id, linked_ids in source_ids_by_decision.items():
        missing_ids = [item for item in linked_ids if item not in resolved_by_id]
        accepted_ids = [
            item
            for item in linked_ids
            if bool(source_validity.get(item, {}).get("report_allowed", False))
        ]
        blocked_ids = [
            item for item in linked_ids if item in resolved_by_id and item not in accepted_ids
        ]
        if not linked_ids:
            validity_by_decision[decision_id] = _design_decision_provisional(
                source_ids=[],
                reason=(
                    "Design decision has no linked accepted recommendation or insight "
                    "to trace through the Research Spine."
                ),
            )
            continue
        if missing_ids or blocked_ids:
            validity_by_decision[decision_id] = _design_decision_provisional(
                source_ids=linked_ids,
                accepted_source_ids=accepted_ids,
                blocked_source_ids=blocked_ids,
                missing_source_ids=missing_ids,
                reason=(
                    "Design decision remains provisional until every linked "
                    "recommendation/insight is accepted or reconciled through a "
                    "human-approved Done task."
                ),
            )
            continue
        validity_by_decision[decision_id] = {
            "status": "accepted",
            "report_allowed": True,
            "done_approved": True,
            "reason": "All linked source findings are accepted through the Research Spine.",
            "source_finding_ids": linked_ids,
            "accepted_source_ids": accepted_ids,
            "blocked_source_ids": [],
            "missing_source_ids": [],
            "policy": "design_decision_visibility_requires_accepted_spine_sources",
        }
    return validity_by_decision


def _finding_gate_reason(gate: dict[str, Any], done_approved: bool, report_allowed: bool) -> str:
    if report_allowed:
        return "Accepted for reporting."
    if not gate.get("report_allowed", False):
        return str(gate.get("reason") or "Finding is blocked by the research-validity gate.")
    if not done_approved:
        return (
            "Finding is linked to accepted coded evidence but its task is not human-approved Done."
        )
    return "Finding is provisional."


def _chain_report_block_reason(gate: dict[str, Any], done_approved: bool) -> str:
    if not gate.get("report_allowed", False):
        return str(gate.get("reason") or "Evidence chain is blocked by the research-validity gate.")
    if not done_approved:
        return "Task is not a human-approved Done task."
    return "Task is reportable."


def _parse_json_string_list(raw: Any) -> list[str]:
    parsed = parse_json_list(raw)
    if not isinstance(parsed, list):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for item in parsed:
        value = str(item).strip() if item is not None else ""
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _design_decision_provisional(
    *,
    source_ids: list[str],
    reason: str,
    accepted_source_ids: list[str] | None = None,
    blocked_source_ids: list[str] | None = None,
    missing_source_ids: list[str] | None = None,
) -> dict[str, Any]:
    payload = provisional_finding_validity(reason=reason)
    payload.update(
        {
            "source_finding_ids": source_ids,
            "accepted_source_ids": accepted_source_ids or [],
            "blocked_source_ids": blocked_source_ids or [],
            "missing_source_ids": missing_source_ids or [],
            "policy": "design_decision_visibility_requires_accepted_spine_sources",
        }
    )
    return payload
