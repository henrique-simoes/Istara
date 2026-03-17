"""Scheduled task CRUD API routes."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.scheduler import CronParser, ScheduledTask
from app.models.database import get_db

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class ScheduleCreate(BaseModel):
    """Request body for creating a scheduled task."""

    name: str
    cron_expression: str
    project_id: str
    skill_name: str = ""
    description: str = ""


class ScheduleUpdate(BaseModel):
    """Request body for updating a scheduled task."""

    name: str | None = None
    cron_expression: str | None = None
    skill_name: str | None = None
    description: str | None = None
    enabled: bool | None = None


class ScheduleResponse(BaseModel):
    """Scheduled task response schema."""

    id: str
    name: str
    description: str
    cron_expression: str
    skill_name: str
    project_id: str
    enabled: bool
    last_run: datetime | None = None
    next_run: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/schedules", response_model=ScheduleResponse, status_code=201)
async def create_schedule(data: ScheduleCreate, db: AsyncSession = Depends(get_db)):
    """Create a new scheduled task."""
    # Validate cron expression
    try:
        CronParser.parse(data.cron_expression)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    now = datetime.now(timezone.utc)
    try:
        next_run = CronParser.next_run_after(data.cron_expression, now)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    task = ScheduledTask(
        id=str(uuid.uuid4()),
        name=data.name,
        description=data.description,
        cron_expression=data.cron_expression,
        skill_name=data.skill_name,
        project_id=data.project_id,
        next_run=next_run,
    )

    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.get("/schedules", response_model=list[ScheduleResponse])
async def list_schedules(
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List all scheduled tasks, optionally filtered by project."""
    query = select(ScheduledTask).order_by(ScheduledTask.created_at)
    if project_id:
        query = query.where(ScheduledTask.project_id == project_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/schedules/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(schedule_id: str, db: AsyncSession = Depends(get_db)):
    """Get a scheduled task by ID."""
    result = await db.execute(
        select(ScheduledTask).where(ScheduledTask.id == schedule_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Scheduled task not found")
    return task


@router.patch("/schedules/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: str,
    data: ScheduleUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a scheduled task (enable/disable, change cron, etc.)."""
    result = await db.execute(
        select(ScheduledTask).where(ScheduledTask.id == schedule_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Scheduled task not found")

    update_data = data.model_dump(exclude_unset=True)

    # If cron expression is changing, validate and recalculate next_run
    if "cron_expression" in update_data:
        try:
            CronParser.parse(update_data["cron_expression"])
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        try:
            update_data["next_run"] = CronParser.next_run_after(
                update_data["cron_expression"],
                datetime.now(timezone.utc),
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    for field, value in update_data.items():
        setattr(task, field, value)

    await db.commit()
    await db.refresh(task)
    return task


@router.delete("/schedules/{schedule_id}", status_code=204)
async def delete_schedule(schedule_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a scheduled task."""
    result = await db.execute(
        select(ScheduledTask).where(ScheduledTask.id == schedule_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Scheduled task not found")

    await db.delete(task)
    await db.commit()
