"""Task review service.

This module turns human task review into a durable reward signal. It keeps
the API route thin and gives agents/telemetry/meta systems one place to
record review outcomes.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.finding import Fact, Insight, Nugget, Recommendation
from app.models.project_report import ProjectReport
from app.models.task import Task, TaskStatus
from app.models.task_review import TaskReviewEvent

logger = logging.getLogger(__name__)


APPROVED = "approved"
NEEDS_REVISION = "needs_revision"
REJECTED_AFTER_DONE = "rejected_after_done"
SYSTEM_FAILED = "system_failed"


def _status_value(status: TaskStatus | str | None) -> str:
    if isinstance(status, TaskStatus):
        return status.value
    return status or ""


def classify_review_feedback(feedback: str, labels: list[Any] | None = None) -> tuple[str, str]:
    """Deterministically classify review feedback for fast, local metrics.

    LLM diagnosis can refine this later. This small classifier prevents the
    reward pipeline from depending on model availability.
    """
    text = f"{feedback or ''} {' '.join(str(l) for l in labels or [])}".lower()
    checks = [
        ("missing_evidence", ("evidence", "source", "quote", "citation", "unsupported", "nugget")),
        ("ignored_user_instructions", ("ignored", "instruction", "asked", "didn't follow", "did not follow")),
        ("wrong_skill", ("wrong skill", "different skill", "rerun skill", "method")),
        ("wrong_agent", ("wrong agent", "specialist", "assign")),
        ("hallucination_or_unsupported_claim", ("hallucinat", "made up", "fabricat", "unsupported")),
        ("bad_synthesis", ("synthesis", "shallow", "summary", "pattern")),
        ("insufficient_documents", ("document", "file", "missing input", "upload")),
        ("url_or_tool_failure", ("url", "website", "browser", "fetch", "tool")),
        ("validation_false_positive", ("validation", "consensus", "said it was good")),
        ("user_changed_requirements", ("changed", "new idea", "new requirement", "later", "instead")),
        ("unclear_task", ("unclear", "ambiguous", "clarify")),
    ]
    for category, needles in checks:
        if any(needle in text for needle in needles):
            severity = "major" if category in {"hallucination_or_unsupported_claim", "validation_false_positive"} else "moderate"
            return category, severity
    return "other", "moderate" if feedback else "minor"


def feedback_score(outcome: str, severity: str | None = None, failure_category: str | None = None) -> float:
    """Map human review to a bounded quality/reward score."""
    if outcome == APPROVED:
        return 1.0
    if failure_category == "user_changed_requirements":
        return 0.65
    severity_scores = {
        "minor": 0.45,
        "moderate": 0.25,
        "major": 0.1,
        "critical": 0.0,
    }
    return severity_scores.get(severity or "moderate", 0.25)


async def build_atomic_snapshot(db: AsyncSession, task: Task) -> dict:
    """Collect a compact task-specific atomic research path snapshot."""
    docs = (
        await db.execute(select(Document).where(Document.task_id == task.id).limit(50))
    ).scalars().all()
    nuggets = (
        await db.execute(
            select(Nugget)
            .where(Nugget.project_id == task.project_id, Nugget.task_id == task.id)
            .order_by(Nugget.created_at.desc())
            .limit(25)
        )
    ).scalars().all()
    facts = (
        await db.execute(
            select(Fact)
            .where(Fact.project_id == task.project_id, Fact.task_id == task.id)
            .order_by(Fact.created_at.desc())
            .limit(25)
        )
    ).scalars().all()
    insights = (
        await db.execute(
            select(Insight)
            .where(Insight.project_id == task.project_id, Insight.task_id == task.id)
            .order_by(Insight.created_at.desc())
            .limit(25)
        )
    ).scalars().all()
    recommendations = (
        await db.execute(
            select(Recommendation)
            .where(Recommendation.project_id == task.project_id, Recommendation.task_id == task.id)
            .order_by(Recommendation.created_at.desc())
            .limit(25)
        )
    ).scalars().all()
    reports = (
        await db.execute(
            select(ProjectReport)
            .where(ProjectReport.project_id == task.project_id)
            .order_by(ProjectReport.updated_at.desc())
            .limit(10)
        )
    ).scalars().all()
    try:
        from app.models.code_application import CodeApplication
        from app.models.research_validity import CodingRun
        from app.services.finding_validity_service import finding_research_validity_map

        code_applications = (
            await db.execute(
                select(CodeApplication)
                .where(CodeApplication.project_id == task.project_id, CodeApplication.task_id == task.id)
                .order_by(CodeApplication.created_at.desc())
                .limit(25)
            )
        ).scalars().all()
        coding_runs = (
            await db.execute(
                select(CodingRun)
                .where(CodingRun.project_id == task.project_id, CodingRun.task_id == task.id)
                .order_by(CodingRun.created_at.desc())
                .limit(5)
            )
        ).scalars().all()
        validity_by_id = await finding_research_validity_map(
            db,
            project_id=task.project_id,
            findings=[*nuggets, *facts, *insights, *recommendations],
        )
    except Exception:
        code_applications = []
        coding_runs = []
        validity_by_id = {}

    def preview(rows):
        items = []
        for row in rows[:5]:
            item = {
                "id": row.id,
                "text": getattr(row, "text", getattr(row, "title", ""))[:220],
            }
            validity = validity_by_id.get(str(row.id))
            if validity:
                item["research_validity"] = validity
            items.append(item)
        return items

    return {
        "documents": {"count": len(docs), "items": [{"id": d.id, "title": d.title} for d in docs[:5]]},
        "nuggets": {"count": len(nuggets), "items": preview(nuggets)},
        "facts": {"count": len(facts), "items": preview(facts)},
        "insights": {"count": len(insights), "items": preview(insights)},
        "recommendations": {"count": len(recommendations), "items": preview(recommendations)},
        "reports": {"count": len(reports), "items": [{"id": r.id, "title": r.title} for r in reports[:5]]},
        "research_validity": {
            "coding_run_count": len(coding_runs),
            "code_application_count": len(code_applications),
            "accepted_code_application_count": len(
                [row for row in code_applications if row.promotion_status == "accepted"]
            ),
            "latest_coding_run": coding_runs[0].to_dict() if coding_runs else None,
            "blocked_or_review_items": [
                {
                    "id": row.id,
                    "code_id": row.code_id,
                    "promotion_status": row.promotion_status,
                    "reliability_status": row.reliability_status,
                    "review_status": row.review_status,
                }
                for row in code_applications[:5]
                if row.promotion_status != "accepted" or row.review_status == "pending"
            ],
        },
    }


def build_context_snapshot(task: Task, extra: dict | None = None) -> dict:
    return {
        "title": task.title,
        "description": (task.description or "")[:1000],
        "skill_name": task.skill_name,
        "priority": task.priority,
        "labels": task.get_labels() if hasattr(task, "get_labels") else [],
        "input_document_ids": task.get_input_document_ids() if hasattr(task, "get_input_document_ids") else [],
        "output_document_ids": task.get_output_document_ids() if hasattr(task, "get_output_document_ids") else [],
        "urls": task.get_urls() if hasattr(task, "get_urls") else [],
        "review_cycle_count": task.review_cycle_count or 0,
        "failure_streak": task.failure_streak or 0,
        **(extra or {}),
    }


async def record_task_review_event(
    db: AsyncSession,
    task: Task,
    *,
    outcome: str,
    next_status: TaskStatus,
    next_review_state: str,
    what_to_review: str = "",
    created_by: str = "local",
    failure_category: str | None = None,
    severity: str | None = None,
    quality_score: float | None = None,
    context_extra: dict | None = None,
    diagnosis_status: str = "pending",
) -> TaskReviewEvent:
    """Create a review event and update task summary counters.

    Caller is responsible for committing the session, then calling
    ``record_review_side_effects`` after commit. The side effects open their
    own database sessions; running them before commit can make SQLite wait on
    the review transaction's write lock.
    """
    previous_status = _status_value(task.status)
    previous_review_state = task.review_state or "none"
    labels = task.get_labels() if hasattr(task, "get_labels") else []
    inferred_category, inferred_severity = classify_review_feedback(what_to_review, labels)
    failure_category = failure_category or (None if outcome == APPROVED else inferred_category)
    severity = severity or (None if outcome == APPROVED else inferred_severity)
    score = quality_score if quality_score is not None else feedback_score(outcome, severity, failure_category)
    now = datetime.now(timezone.utc)

    if outcome == APPROVED:
        task.approval_streak = (task.approval_streak or 0) + 1
        task.failure_streak = 0
        task.next_agent_action = None
    else:
        task.failure_streak = (task.failure_streak or 0) + 1
        task.approval_streak = 0
        task.next_agent_action = "resume_in_progress" if next_status == TaskStatus.IN_PROGRESS else "return_to_backlog"
        task.what_to_review = what_to_review

    task.status = next_status
    task.review_state = next_review_state
    task.last_review_outcome = outcome
    task.last_reviewed_by = created_by
    task.last_reviewed_at = now
    task.last_review_feedback = what_to_review
    task.human_feedback_score = score
    task.review_severity = severity
    task.review_failure_category = failure_category
    task.review_cycle_count = (task.review_cycle_count or 0) + 1

    atomic_snapshot = await build_atomic_snapshot(db, task)
    event = TaskReviewEvent(
        id=str(uuid.uuid4()),
        task_id=task.id,
        project_id=task.project_id,
        agent_id=task.agent_id or "",
        skill_name=task.skill_name or "",
        previous_status=previous_status,
        next_status=next_status.value,
        previous_review_state=previous_review_state,
        next_review_state=next_review_state,
        outcome=outcome,
        what_to_review=what_to_review,
        feedback_summary=(what_to_review or "")[:500],
        context_snapshot=json.dumps(build_context_snapshot(task, context_extra)),
        atomic_snapshot=json.dumps(atomic_snapshot),
        validation_method=task.validation_method,
        consensus_score=task.consensus_score,
        quality_score=score,
        failure_category=failure_category,
        severity=severity,
        human_feedback_score=score,
        failure_streak_after=task.failure_streak or 0,
        review_cycle_after=task.review_cycle_count or 0,
        trace_id=str(uuid.uuid4())[:36],
        created_by=created_by,
        diagnosis_status=diagnosis_status,
        diagnosis_json=json.dumps({}),
        created_at=now,
        updated_at=now,
    )
    db.add(event)
    return event


async def record_review_side_effects(event: TaskReviewEvent, score: float | None = None) -> None:
    """Best-effort telemetry/model/learning side effects."""
    score = event.quality_score if score is None else score
    if score is None:
        score = 0.0
    try:
        from app.core.telemetry import telemetry_recorder

        operation = {
            APPROVED: "task_review_approved",
            NEEDS_REVISION: "task_review_rejected",
            REJECTED_AFTER_DONE: "task_reopened_after_done",
            SYSTEM_FAILED: "task_system_failed",
        }.get(event.outcome, "task_review_event")
        await telemetry_recorder.record_span(
            trace_id=event.trace_id,
            operation=operation,
            skill_name=event.skill_name,
            model_name=event.model_name or "unknown",
            agent_id=event.agent_id,
            project_id=event.project_id,
            task_id=event.task_id,
            status="success" if event.outcome == APPROVED else "degraded",
            quality_score=score,
            consensus_score=event.consensus_score,
            error_type=event.failure_category,
            source="production",
        )
        research_status = "success" if event.outcome == APPROVED else "degraded"
        await telemetry_recorder.record_research_validity_event(
            trace_id=event.trace_id,
            operation="human_review.decision",
            project_id=event.project_id,
            task_id=event.task_id,
            status=research_status,
            skill_name=event.skill_name or "",
            agent_id=event.agent_id or "",
            quality_score=score,
            consensus_score=event.consensus_score,
            error_type=event.failure_category,
            source="production",
        )
        await telemetry_recorder.record_research_validity_event(
            trace_id=event.trace_id,
            operation="kanban.status_transition",
            project_id=event.project_id,
            task_id=event.task_id,
            status=research_status,
            skill_name=event.skill_name or "",
            agent_id=event.agent_id or "",
            quality_score=score,
            consensus_score=event.consensus_score,
            error_type=event.failure_category,
            source="production",
        )
        if event.skill_name:
            await telemetry_recorder.record_model_performance(
                event.skill_name,
                event.model_name or "unknown",
                event.temperature or 0.3,
                quality=score,
                success=event.outcome == APPROVED,
                project_id=event.project_id,
            )
    except Exception as exc:
        logger.debug(f"Review telemetry side effect failed: {exc}")

    if event.agent_id and event.outcome != APPROVED:
        try:
            from app.core.agent_learning import agent_learning

            await agent_learning.record_user_feedback(
                event.agent_id,
                f"Task review feedback ({event.failure_category or 'other'}): {event.feedback_summary}",
                context=f"task_id={event.task_id}; skill={event.skill_name}; outcome={event.outcome}",
                project_id=event.project_id,
            )
        except Exception as exc:
            logger.debug(f"Review learning side effect failed: {exc}")

    if event.skill_name:
        try:
            from app.skills.skill_manager import skill_manager

            skill_manager.record_execution(
                event.skill_name,
                event.outcome == APPROVED,
                score,
                project_id=event.project_id,
            )
        except Exception as exc:
            logger.debug(f"Review skill-manager side effect failed: {exc}")

    if event.outcome == APPROVED and event.skill_name:
        try:
            from app.core.report_manager import report_manager
            from app.models.database import async_session

            async with async_session() as report_db:
                await report_manager.route_approved_task_findings(
                    event.project_id,
                    event.task_id,
                    event.skill_name,
                    report_db,
                    consensus_score=event.consensus_score,
                )
        except Exception as exc:
            logger.debug(f"Approved task report-routing side effect failed: {exc}")


async def record_kanban_status_transition(
    *,
    project_id: str,
    task_id: str,
    previous_status: str,
    next_status: str,
    trace_id: str | None = None,
) -> None:
    """Record content-free task status movement for research-validity audits."""
    if previous_status == next_status:
        return
    try:
        from app.core.telemetry import telemetry_recorder

        await telemetry_recorder.record_research_validity_event(
            trace_id=trace_id or str(uuid.uuid4())[:36],
            operation="kanban.status_transition",
            project_id=project_id,
            task_id=task_id,
            status="success",
            source="production",
        )
    except Exception as exc:
        logger.debug(f"Kanban transition telemetry side effect failed: {exc}")


async def diagnose_review_event(db: AsyncSession, event_id: str) -> None:
    """Populate deterministic diagnosis for an event.

    This is intentionally local and fast for now. The API is async so a later
    LLM-based diagnosis can enrich the same event without changing callers.
    """
    event = await db.get(TaskReviewEvent, event_id)
    if not event:
        return
    diagnosis = {
        "primary_failure_category": event.failure_category or "none",
        "severity": event.severity or "none",
        "recommended_next_action": "approve" if event.outcome == APPROVED else "revise_with_feedback",
        "should_switch_skill": event.failure_category in {"wrong_skill", "bad_synthesis"},
        "should_switch_agent": event.failure_category in {"wrong_agent", "routing_issue"},
        "should_trigger_ensemble": event.failure_category in {"validation_false_positive", "hallucination_or_unsupported_claim"},
        "should_propose_skill_update": event.failure_streak_after >= 2 and bool(event.skill_name),
        "learning_summary": event.feedback_summary[:500],
    }
    event.diagnosis_status = "complete"
    event.diagnosis_json = json.dumps(diagnosis)
    event.updated_at = datetime.now(timezone.utc)
