"""Task CRUD and Kanban API routes."""

import json
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.task import Task, TaskStatus
from app.core.agent import agent as agent_orchestrator

LOCK_EXPIRY_MINUTES = 30

router = APIRouter()


class TaskCreate(BaseModel):
    """Request body for creating a task."""

    project_id: str
    title: str
    description: str = ""
    skill_name: str = ""
    user_context: str = ""
    input_document_ids: list[str] = []
    output_document_ids: list[str] = []
    urls: list[str] = []
    instructions: str = ""
    priority: str = "medium"
    agent_id: str | None = None


class TaskUpdate(BaseModel):
    """Request body for updating a task."""

    title: str | None = None
    description: str | None = None
    status: TaskStatus | None = None
    skill_name: str | None = None
    agent_notes: str | None = None
    user_context: str | None = None
    progress: float | None = None
    position: int | None = None
    agent_id: str | None = None
    priority: str | None = None
    input_document_ids: list[str] | None = None
    output_document_ids: list[str] | None = None
    urls: list[str] | None = None
    instructions: str | None = None


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
    locked_by: str | None = None
    locked_at: datetime | None = None
    lock_expires_at: datetime | None = None
    validation_method: str | None = None
    validation_result: str | None = None
    consensus_score: float | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def _parse_json(cls, data):
        """Parse JSON string fields from ORM model."""
        import json as _json

        for field in ("input_document_ids", "output_document_ids", "urls"):
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


@router.get("/tasks", response_model=list[TaskResponse])
async def list_tasks(
    project_id: str | None = None,
    status: TaskStatus | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List tasks, optionally filtered by project and/or status."""
    query = select(Task).order_by(Task.position, Task.created_at)

    if project_id:
        query = query.where(Task.project_id == project_id)
    if status:
        query = query.where(Task.status == status)

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/tasks", response_model=TaskResponse, status_code=201)
async def create_task(data: TaskCreate, db: AsyncSession = Depends(get_db)):
    """Create a new task."""
    # Get max position for ordering
    result = await db.execute(
        select(Task.position)
        .where(Task.project_id == data.project_id)
        .order_by(Task.position.desc())
        .limit(1)
    )
    max_pos = result.scalar() or 0

    task = Task(
        id=str(uuid.uuid4()),
        project_id=data.project_id,
        title=data.title,
        description=data.description,
        skill_name=data.skill_name,
        user_context=data.user_context,
        instructions=data.instructions,
        priority=data.priority,
        agent_id=data.agent_id,
        position=max_pos + 1,
        input_document_ids=json.dumps(data.input_document_ids),
        output_document_ids=json.dumps(data.output_document_ids),
        urls=json.dumps(data.urls),
    )

    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """Get a task by ID."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a task (including status changes for Kanban moves)."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = data.model_dump(exclude_unset=True)
    # Serialize list fields to JSON strings for the ORM
    for json_field in ("input_document_ids", "output_document_ids", "urls"):
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
    position: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Move a task to a different Kanban column."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = status
    if position is not None:
        task.position = position

    await db.commit()
    await db.refresh(task)
    return task


@router.post("/tasks/{task_id}/verify")
async def verify_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """Verify a task's output quality before marking as done."""
    task = (await db.execute(select(Task).where(Task.id == task_id))).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

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

    if verified and task.status == TaskStatus.IN_REVIEW:
        task.status = TaskStatus.DONE
        await db.commit()

    return {
        "task_id": task_id,
        "verified": verified,
        "issues": issues,
        "status": task.status.value,
    }


@router.post("/tasks/{task_id}/attach")
async def attach_document(
    task_id: str,
    document_id: str,
    direction: str = "input",
    db: AsyncSession = Depends(get_db),
):
    """Attach a document to a task as input or output."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

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
    return {"task_id": task_id, "document_id": document_id, "direction": direction, "attached": True}


@router.post("/tasks/{task_id}/detach")
async def detach_document(
    task_id: str,
    document_id: str,
    direction: str = "input",
    db: AsyncSession = Depends(get_db),
):
    """Detach a document from a task."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

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
    return {"task_id": task_id, "document_id": document_id, "direction": direction, "detached": True}


@router.post("/tasks/{task_id}/lock")
async def lock_task(
    task_id: str,
    user_id: str = "local",
    db: AsyncSession = Depends(get_db),
):
    """Lock a task for exclusive editing by a user or agent."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    now = datetime.now(timezone.utc)

    # Check if already locked by someone else (and not expired)
    if task.locked_by and task.locked_by != user_id:
        if task.lock_expires_at and task.lock_expires_at > now:
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
    user_id: str = "local",
    force: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Unlock a task. Only the lock owner or force=True (admin) can unlock."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.locked_by and task.locked_by != user_id and not force:
        raise HTTPException(status_code=403, detail="Only the lock owner or an admin can unlock.")

    task.locked_by = None
    task.locked_at = None
    task.lock_expires_at = None
    await db.commit()

    return {"task_id": task_id, "unlocked": True}


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a task."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    await db.delete(task)
    await db.commit()
