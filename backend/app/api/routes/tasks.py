"""Task CRUD and Kanban API routes."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.task import Task, TaskStatus

router = APIRouter()


class TaskCreate(BaseModel):
    """Request body for creating a task."""

    project_id: str
    title: str
    description: str = ""
    skill_name: str = ""
    user_context: str = ""


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


class TaskResponse(BaseModel):
    """Task response schema."""

    id: str
    project_id: str
    title: str
    description: str
    status: TaskStatus
    skill_name: str
    agent_notes: str
    user_context: str
    progress: float
    position: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


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
        position=max_pos + 1,
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
    for field, value in update_data.items():
        setattr(task, field, value)

    await db.commit()
    await db.refresh(task)
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


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a task."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    await db.delete(task)
    await db.commit()
