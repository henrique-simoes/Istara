"""Task CRUD and Kanban API routes."""

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.document import Document
from app.models.task import Task, TaskStatus
from app.models.task_review import TaskReviewEvent
from app.core.agent import agent as agent_orchestrator
from app.core.permissions import get_subject, get_visible_project_or_404, is_global_admin, require_project_access

LOCK_EXPIRY_MINUTES = 30
TASK_PRIORITIES = {"urgent", "high", "medium", "low"}

router = APIRouter()


def _dedupe_text_list(values: list[str]) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for value in values:
        item = str(value or "").strip()
        if item and item not in seen:
            cleaned.append(item)
            seen.add(item)
    return cleaned


async def _ensure_documents_in_project(
    db: AsyncSession,
    project_id: str,
    document_ids: list[str],
    *,
    field_name: str,
) -> list[str]:
    ids = _dedupe_text_list(document_ids)
    if not ids:
        return []

    rows = (
        await db.execute(select(Document.id, Document.project_id).where(Document.id.in_(ids)))
    ).all()
    project_by_id = {row[0]: row[1] for row in rows}

    missing = [doc_id for doc_id in ids if doc_id not in project_by_id]
    foreign = [doc_id for doc_id in ids if project_by_id.get(doc_id) != project_id]
    if missing or foreign:
        raise HTTPException(status_code=404, detail=f"{field_name} contains unknown documents for this project.")

    return ids


class TaskCreate(BaseModel):
    """Request body for creating a task."""

    project_id: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=20000)
    skill_name: str = Field(default="", max_length=100)
    user_context: str = Field(default="", max_length=50000)
    input_document_ids: list[str] = Field(default_factory=list, max_length=200)
    output_document_ids: list[str] = Field(default_factory=list, max_length=200)
    urls: list[str] = Field(default_factory=list, max_length=100)
    instructions: str = Field(default="", max_length=50000)
    labels: list[dict | str] = Field(default_factory=list, max_length=100)
    priority: str = "medium"
    agent_id: str | None = Field(default=None, max_length=100)

    @field_validator("project_id", "title", "skill_name", "user_context", "instructions", "priority", "agent_id", mode="before")
    @classmethod
    def _strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return str(value).strip()

    @field_validator("description", mode="before")
    @classmethod
    def _strip_description(cls, value: str | None) -> str:
        return str(value or "").strip()

    @field_validator("priority")
    @classmethod
    def _validate_priority(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in TASK_PRIORITIES:
            raise ValueError("priority must be one of: urgent, high, medium, low")
        return normalized

    @field_validator("input_document_ids", "output_document_ids", "urls", mode="after")
    @classmethod
    def _normalize_lists(cls, value: list[str]) -> list[str]:
        return _dedupe_text_list(value)


class TaskUpdate(BaseModel):
    """Request body for updating a task."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=20000)
    status: TaskStatus | None = None
    skill_name: str | None = Field(default=None, max_length=100)
    agent_notes: str | None = Field(default=None, max_length=50000)
    user_context: str | None = Field(default=None, max_length=50000)
    progress: float | None = Field(default=None, ge=0, le=1)
    position: int | None = Field(default=None, ge=0, le=1000000)
    agent_id: str | None = Field(default=None, max_length=100)
    priority: str | None = None
    input_document_ids: list[str] | None = Field(default=None, max_length=200)
    output_document_ids: list[str] | None = Field(default=None, max_length=200)
    urls: list[str] | None = Field(default=None, max_length=100)
    instructions: str | None = Field(default=None, max_length=50000)
    labels: list[dict | str] | None = Field(default=None, max_length=100)
    what_to_review: str | None = Field(default=None, max_length=5000)

    @field_validator("title", "description", "skill_name", "agent_notes", "user_context", "agent_id", "priority", "instructions", "what_to_review", mode="before")
    @classmethod
    def _strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return str(value).strip()

    @field_validator("priority")
    @classmethod
    def _validate_priority(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized not in TASK_PRIORITIES:
            raise ValueError("priority must be one of: urgent, high, medium, low")
        return normalized

    @field_validator("input_document_ids", "output_document_ids", "urls", mode="after")
    @classmethod
    def _normalize_lists(cls, value: list[str] | None) -> list[str] | None:
        return _dedupe_text_list(value) if value is not None else None


class TaskResponse(BaseModel):
    """Task response schema."""

    id: str
    project_id: str
    agent_id: str | None = None
    title: str
    description: str
    status: TaskStatus
    skill_name: str
    agent_notes: str
    user_context: str
    progress: float
    position: int
    priority: str = "medium"
    input_document_ids: list[str] = []
    output_document_ids: list[str] = []
    urls: list[str] = []
    instructions: str = ""
    labels: list[dict | str] = []
    review_state: str = "none"
    what_to_review: str = ""
    review_cycle_count: int = 0
    failure_streak: int = 0
    approval_streak: int = 0
    last_review_outcome: str | None = None
    last_reviewed_by: str | None = None
    last_reviewed_at: datetime | None = None
    last_review_feedback: str = ""
    next_agent_action: str | None = None
    human_feedback_score: float | None = None
    review_severity: str | None = None
    review_failure_category: str | None = None
    locked_by: str | None = None
    locked_at: datetime | None = None
    lock_expires_at: datetime | None = None
    validation_method: str | None = None
    validation_result: str | None = None
    consensus_score: float | None = None
    health: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def _parse_json(cls, data):
        """Parse JSON string fields from ORM model."""
        import json as _json

        for field in ("input_document_ids", "output_document_ids", "urls", "labels"):
            val = getattr(data, field, None) if hasattr(data, "__dict__") else data.get(field)
            if isinstance(val, str):
                try:
                    parsed = _json.loads(val)
                except Exception:
                    parsed = []
                if hasattr(data, "__dict__"):
                    object.__setattr__(data, field, parsed)
                else:
                    data[field] = parsed
        return data


class ReviewApproveRequest(BaseModel):
    """Human approval request for moving a task to Done."""

    reviewed_by: str = Field(default="local", max_length=100)
    note: str = Field(default="", max_length=5000)

    @field_validator("reviewed_by", "note", mode="before")
    @classmethod
    def _strip_text(cls, value: str | None) -> str:
        return str(value or "").strip()


class ReviewRevisionRequest(BaseModel):
    """Human request to send reviewed work back to agents."""

    what_to_review: str = Field(max_length=5000)
    next_status: TaskStatus = TaskStatus.BACKLOG
    reviewed_by: str = Field(default="local", max_length=100)
    severity: str | None = Field(default=None, max_length=30)
    failure_category: str | None = Field(default=None, max_length=80)
    labels: list[dict | str] | None = Field(default=None, max_length=100)
    skill_name: str | None = Field(default=None, max_length=100)
    input_document_ids: list[str] | None = Field(default=None, max_length=200)
    urls: list[str] | None = Field(default=None, max_length=100)

    @field_validator("what_to_review", "reviewed_by", "severity", "failure_category", "skill_name", mode="before")
    @classmethod
    def _strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return str(value).strip()

    @field_validator("input_document_ids", "urls", mode="after")
    @classmethod
    def _normalize_lists(cls, value: list[str] | None) -> list[str] | None:
        return _dedupe_text_list(value) if value is not None else None


async def _get_task_or_404(db: AsyncSession, task_id: str) -> Task:
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


async def _approve_task(
    db: AsyncSession,
    task: Task,
    reviewed_by: str = "local",
    note: str = "",
) -> TaskReviewEvent:
    from app.core.task_review import APPROVED, diagnose_review_event, record_task_review_event

    event = await record_task_review_event(
        db,
        task,
        outcome=APPROVED,
        next_status=TaskStatus.DONE,
        next_review_state="approved",
        what_to_review=note,
        created_by=reviewed_by,
        quality_score=1.0,
    )
    await diagnose_review_event(db, event.id)
    return event


@router.get("/tasks", response_model=list[TaskResponse])
async def list_tasks(
    request: Request,
    project_id: str | None = None,
    status: TaskStatus | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List tasks, optionally filtered by project and/or status."""
    query = select(Task).order_by(Task.position, Task.created_at)

    if project_id:
        await get_visible_project_or_404(db, request, project_id, min_role="viewer")
        query = query.where(Task.project_id == project_id)
    else:
        subject = get_subject(request)
        if not is_global_admin(subject):
            raise HTTPException(status_code=422, detail="project_id is required")
    if status:
        query = query.where(Task.status == status)

    result = await db.execute(query)
    tasks = result.scalars().all()

    from app.core.telemetry import telemetry_recorder

    for task in tasks:
        task.health = await telemetry_recorder.get_task_health(task.id)

    return tasks


@router.post("/tasks", response_model=TaskResponse, status_code=201)
async def create_task(data: TaskCreate, request: Request, db: AsyncSession = Depends(get_db)):
    """Create a new task with intelligent agent routing."""
    import logging as _log

    await get_visible_project_or_404(db, request, data.project_id, min_role="researcher")
    input_document_ids = await _ensure_documents_in_project(
        db,
        data.project_id,
        data.input_document_ids,
        field_name="input_document_ids",
    )
    output_document_ids = await _ensure_documents_in_project(
        db,
        data.project_id,
        data.output_document_ids,
        field_name="output_document_ids",
    )

    # Get max position for ordering
    result = await db.execute(
        select(Task.position)
        .where(Task.project_id == data.project_id)
        .order_by(Task.position.desc())
        .limit(1)
    )
    max_pos = result.scalar() or 0

    # Route task to best agent if no explicit assignment
    agent_id = data.agent_id
    if not agent_id:
        try:
            from app.core.task_router import route_task

            routing = await route_task(
                db,
                data.title,
                data.description or "",
                data.skill_name or None,
            )
            agent_id = routing["primary_agent_id"]
            _log.getLogger(__name__).info(
                f"Auto-routed task '{data.title}' → {agent_id} ({routing['routing_reason']})"
            )
        except Exception as e:
            _log.getLogger(__name__).warning(f"Task routing failed, defaulting to istara-main: {e}")
            agent_id = "istara-main"

    task = Task(
        id=str(uuid.uuid4()),
        project_id=data.project_id,
        title=data.title,
        description=data.description,
        skill_name=data.skill_name,
        user_context=data.user_context,
        instructions=data.instructions,
        priority=data.priority,
        agent_id=agent_id,
        position=max_pos + 1,
        input_document_ids=json.dumps(input_document_ids),
        output_document_ids=json.dumps(output_document_ids),
        urls=json.dumps(data.urls),
        labels=json.dumps(data.labels),
    )

    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Get a task by ID."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await require_project_access(db, request, task.project_id, min_role="viewer")

    from app.core.telemetry import telemetry_recorder

    task.health = await telemetry_recorder.get_task_health(task.id)

    return task


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    data: TaskUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Update a task (including status changes for Kanban moves)."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await require_project_access(db, request, task.project_id, min_role="researcher")

    update_data = data.model_dump(exclude_unset=True)
    if update_data.get("status") == TaskStatus.DONE:
        raise HTTPException(
            status_code=409,
            detail="Use the human review approval endpoint to mark tasks done.",
        )
    for doc_field in ("input_document_ids", "output_document_ids"):
        if doc_field in update_data and update_data[doc_field] is not None:
            update_data[doc_field] = await _ensure_documents_in_project(
                db,
                task.project_id,
                update_data[doc_field],
                field_name=doc_field,
            )
    # Serialize list fields to JSON strings for the ORM
    for json_field in ("input_document_ids", "output_document_ids", "urls", "labels"):
        if json_field in update_data and isinstance(update_data[json_field], list):
            update_data[json_field] = json.dumps(update_data[json_field])
    for field, value in update_data.items():
        setattr(task, field, value)

    await db.commit()
    await db.refresh(task)

    # If an agent was assigned, wake the orchestrator to pick up the task immediately
    if "agent_id" in update_data and update_data["agent_id"]:
        agent_orchestrator.wake()

    return task


@router.post("/tasks/{task_id}/move", response_model=TaskResponse)
async def move_task(
    task_id: str,
    status: TaskStatus,
    request: Request,
    position: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Move a task to a different Kanban column."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await require_project_access(db, request, task.project_id, min_role="researcher")

    if status == TaskStatus.DONE:
        if task.status != TaskStatus.IN_REVIEW:
            raise HTTPException(status_code=409, detail="Only tasks in review can be approved as done.")
        event = await _approve_task(db, task, reviewed_by="local", note="Approved via Kanban move.")
        if position is not None:
            task.position = position
        await db.commit()
        await db.refresh(task)
        return task

    if task.status == TaskStatus.DONE and status != TaskStatus.DONE:
        raise HTTPException(
            status_code=409,
            detail="Flag Done work as not successful before sending it back to agents.",
        )

    task.status = status
    if position is not None:
        task.position = position
    if status == TaskStatus.IN_REVIEW and task.review_state in ("none", ""):
        task.review_state = "awaiting_review"
    if status in (TaskStatus.BACKLOG, TaskStatus.IN_PROGRESS) and task.review_state in ("needs_revision", "system_failed"):
        task.next_agent_action = "resume_in_progress" if status == TaskStatus.IN_PROGRESS else "return_to_backlog"

    await db.commit()
    await db.refresh(task)
    return task


@router.post("/tasks/{task_id}/verify")
async def verify_task(task_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Verify a task's output quality before marking as done.

    On successful verification (IN_REVIEW → DONE):
    1. Triggers autonomous MECE reporting sub-agent via A2A messaging
    2. Extracts user preferences from chat history for memory learning
    """
    task = (await db.execute(select(Task).where(Task.id == task_id))).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await require_project_access(db, request, task.project_id, min_role="researcher")

    issues = []
    if not task.agent_notes or len(task.agent_notes) < 20:
        issues.append("Agent notes are empty or too brief")
    if "Error:" in (task.agent_notes or ""):
        issues.append("Agent notes contain error messages")
    if "No files provided" in (task.agent_notes or ""):
        issues.append("Task failed due to missing files")
    if task.progress < 1.0:
        issues.append(f"Task progress incomplete ({task.progress})")

    verified = len(issues) == 0

    event = None
    if verified and task.status == TaskStatus.IN_REVIEW:
        event = await _approve_task(db, task, reviewed_by="local", note="Approved via legacy verify endpoint.")
        await db.commit()

    return {
        "task_id": task_id,
        "verified": verified,
        "issues": issues,
        "status": task.status.value,
        "review_state": task.review_state,
        "review_event_id": event.id if event else None,
    }


@router.post("/tasks/{task_id}/review/approve")
async def approve_task_review(
    task_id: str,
    request: Request,
    data: ReviewApproveRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Human approval: move an IN_REVIEW task to DONE and record reward signal."""
    task = await _get_task_or_404(db, task_id)
    await require_project_access(db, request, task.project_id, min_role="researcher")
    if task.status != TaskStatus.IN_REVIEW:
        raise HTTPException(status_code=409, detail="Only tasks in review can be approved as done.")
    body = data or ReviewApproveRequest()
    event = await _approve_task(db, task, body.reviewed_by, body.note)
    await db.commit()
    await db.refresh(task)
    return {"task": TaskResponse.model_validate(task).model_dump(mode="json"), "event": event.to_dict()}


@router.post("/tasks/{task_id}/review/request-revision")
async def request_task_revision(
    task_id: str,
    data: ReviewRevisionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Human rejection/reopen: send reviewed work back to backlog or in progress."""
    task = await _get_task_or_404(db, task_id)
    await require_project_access(db, request, task.project_id, min_role="researcher")
    if task.status not in (TaskStatus.IN_REVIEW, TaskStatus.DONE):
        raise HTTPException(status_code=409, detail="Only tasks in review or done can be flagged for revision.")
    if data.next_status not in (TaskStatus.BACKLOG, TaskStatus.IN_PROGRESS):
        raise HTTPException(status_code=422, detail="Rejected work must go to backlog or in progress.")
    if not data.what_to_review.strip() and not data.failure_category:
        raise HTTPException(status_code=422, detail="What to Review is required when requesting revision.")

    if data.labels is not None:
        task.set_labels(data.labels)
    if data.skill_name is not None:
        task.skill_name = data.skill_name
    if data.input_document_ids is not None:
        task.set_input_document_ids(
            await _ensure_documents_in_project(
                db,
                task.project_id,
                data.input_document_ids,
                field_name="input_document_ids",
            )
        )
    if data.urls is not None:
        task.set_urls(data.urls)

    previous_status = task.status
    next_review_state = "rejected_after_done" if previous_status == TaskStatus.DONE else "needs_revision"

    from app.core.task_review import record_task_review_event, diagnose_review_event

    event = await record_task_review_event(
        db,
        task,
        outcome=next_review_state,
        next_status=data.next_status,
        next_review_state=next_review_state,
        what_to_review=data.what_to_review,
        created_by=data.reviewed_by,
        failure_category=data.failure_category,
        severity=data.severity,
    )
    await diagnose_review_event(db, event.id)
    await db.commit()
    await db.refresh(task)
    if data.next_status == TaskStatus.IN_PROGRESS or task.agent_id == "istara-main":
        agent_orchestrator.wake()
    return {"task": TaskResponse.model_validate(task).model_dump(mode="json"), "event": event.to_dict()}


@router.get("/tasks/{task_id}/review-events")
async def get_task_review_events(task_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """List review/reward events for a task."""
    task = await _get_task_or_404(db, task_id)
    await require_project_access(db, request, task.project_id, min_role="viewer")
    result = await db.execute(
        select(TaskReviewEvent)
        .where(TaskReviewEvent.task_id == task_id)
        .order_by(TaskReviewEvent.created_at.desc())
    )
    return {"events": [event.to_dict() for event in result.scalars().all()]}


@router.get("/tasks/{task_id}/atomic-path")
async def get_task_atomic_path(task_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Return the task's compact atomic research path."""
    task = await _get_task_or_404(db, task_id)
    await require_project_access(db, request, task.project_id, min_role="viewer")
    from app.core.task_review import build_atomic_snapshot

    return await build_atomic_snapshot(db, task)


@router.get("/tasks/{task_id}/quality-summary")
async def get_task_quality_summary(task_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Return concise task quality and review metrics for cards/modals."""
    task = await _get_task_or_404(db, task_id)
    await require_project_access(db, request, task.project_id, min_role="viewer")
    validation = {}
    if task.validation_result:
        try:
            validation = json.loads(task.validation_result)
        except Exception:
            validation = {}
    result = await db.execute(
        select(TaskReviewEvent)
        .where(TaskReviewEvent.task_id == task_id)
        .order_by(TaskReviewEvent.created_at.desc())
        .limit(5)
    )
    events = [event.to_dict() for event in result.scalars().all()]
    return {
        "task_id": task.id,
        "status": task.status.value,
        "review_state": task.review_state,
        "review_cycle_count": task.review_cycle_count,
        "failure_streak": task.failure_streak,
        "approval_streak": task.approval_streak,
        "human_feedback_score": task.human_feedback_score,
        "review_failure_category": task.review_failure_category,
        "review_severity": task.review_severity,
        "validation_method": task.validation_method,
        "consensus_score": task.consensus_score,
        "validation": validation,
        "recent_review_events": events,
    }


@router.post("/tasks/{task_id}/reports")
async def create_report_from_task(task_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Create a lightweight report record from a human-approved Done task."""
    task = await _get_task_or_404(db, task_id)
    await require_project_access(db, request, task.project_id, min_role="researcher")
    if task.status != TaskStatus.DONE or task.review_state != "approved":
        raise HTTPException(status_code=409, detail="Only human-approved Done tasks can be sent to Reports.")

    from app.core.task_review import build_atomic_snapshot
    from app.models.project_report import ProjectReport

    snapshot = await build_atomic_snapshot(db, task)
    finding_ids: list[str] = []
    for key in ("nuggets", "facts", "insights", "recommendations"):
        finding_ids.extend([item["id"] for item in snapshot.get(key, {}).get("items", [])])

    report = ProjectReport(
        id=str(uuid.uuid4()),
        project_id=task.project_id,
        title=f"Task Report: {task.title[:240]}",
        layer=2,
        report_type="task_review",
        scope=task.id,
        content_json=json.dumps({
            "task_id": task.id,
            "task_title": task.title,
            "agent_notes": task.agent_notes,
            "atomic_path": snapshot,
            "review_state": task.review_state,
        }),
        executive_summary=(task.agent_notes or task.description or task.title)[:2000],
        finding_ids_json=json.dumps(finding_ids),
        source_document_ids_json=json.dumps(task.get_output_document_ids()),
        status="draft",
    )
    db.add(report)
    await db.commit()
    return {"report": report.to_dict()}


@router.post("/tasks/{task_id}/attach")
async def attach_document(
    task_id: str,
    document_id: str,
    request: Request,
    direction: Literal["input", "output"] = "input",
    db: AsyncSession = Depends(get_db),
):
    """Attach a document to a task as input or output."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await require_project_access(db, request, task.project_id, min_role="researcher")
    await _ensure_documents_in_project(db, task.project_id, [document_id], field_name="document_id")

    if direction == "output":
        ids = task.get_output_document_ids()
        if document_id not in ids:
            ids.append(document_id)
            task.set_output_document_ids(ids)
    else:
        ids = task.get_input_document_ids()
        if document_id not in ids:
            ids.append(document_id)
            task.set_input_document_ids(ids)

    await db.commit()
    await db.refresh(task)
    return {
        "task_id": task_id,
        "document_id": document_id,
        "direction": direction,
        "attached": True,
    }


@router.post("/tasks/{task_id}/detach")
async def detach_document(
    task_id: str,
    document_id: str,
    request: Request,
    direction: Literal["input", "output"] = "input",
    db: AsyncSession = Depends(get_db),
):
    """Detach a document from a task."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await require_project_access(db, request, task.project_id, min_role="researcher")
    await _ensure_documents_in_project(db, task.project_id, [document_id], field_name="document_id")

    if direction == "output":
        ids = task.get_output_document_ids()
        if document_id in ids:
            ids.remove(document_id)
            task.set_output_document_ids(ids)
    else:
        ids = task.get_input_document_ids()
        if document_id in ids:
            ids.remove(document_id)
            task.set_input_document_ids(ids)

    await db.commit()
    return {
        "task_id": task_id,
        "document_id": document_id,
        "direction": direction,
        "detached": True,
    }


@router.post("/tasks/{task_id}/lock")
async def lock_task(
    task_id: str,
    request: Request,
    user_id: str = "local",
    db: AsyncSession = Depends(get_db),
):
    """Lock a task for exclusive editing by a user or agent."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await require_project_access(db, request, task.project_id, min_role="researcher")

    now = datetime.now(timezone.utc)

    # Check if already locked by someone else (and not expired)
    if task.locked_by and task.locked_by != user_id:
        expires = task.lock_expires_at
        if expires and expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires and expires > now:
            raise HTTPException(
                status_code=409,
                detail=f"Task locked by {task.locked_by} until {task.lock_expires_at.isoformat()}",
            )

    task.locked_by = user_id
    task.locked_at = now
    task.lock_expires_at = now + timedelta(minutes=LOCK_EXPIRY_MINUTES)
    await db.commit()

    return {
        "task_id": task_id,
        "locked_by": user_id,
        "locked_at": task.locked_at.isoformat(),
        "lock_expires_at": task.lock_expires_at.isoformat(),
    }


@router.post("/tasks/{task_id}/unlock")
async def unlock_task(
    task_id: str,
    request: Request,
    user_id: str = "local",
    force: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Unlock a task. Only the lock owner or force=True (admin) can unlock."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await require_project_access(db, request, task.project_id, min_role="researcher")

    if task.locked_by and task.locked_by != user_id and not force:
        raise HTTPException(status_code=403, detail="Only the lock owner or an admin can unlock.")

    task.locked_by = None
    task.locked_at = None
    task.lock_expires_at = None
    await db.commit()

    return {"task_id": task_id, "unlocked": True}


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(task_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Delete a task."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await require_project_access(db, request, task.project_id, min_role="researcher")

    await db.delete(task)
    await db.commit()
