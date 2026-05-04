"""Scheduled task CRUD API routes."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.scheduler import CronParser, ScheduledTask
from app.core.security_middleware import require_admin_from_request
from app.models.database import get_db

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class ScheduleCreate(BaseModel):
    """Request body for creating a scheduled task."""

    name: str = Field(min_length=1, max_length=120)
    cron_expression: str = Field(min_length=1, max_length=100)
    project_id: str = Field(min_length=1, max_length=100)
    skill_name: str = Field(default="", max_length=100)
    description: str = Field(default="", max_length=1000)


class ScheduleUpdate(BaseModel):
    """Request body for updating a scheduled task."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    cron_expression: str | None = Field(default=None, min_length=1, max_length=100)
    skill_name: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
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
    is_running: bool = False
    last_run: datetime | None = None
    next_run: datetime | None = None
    loop_type: str = "cron"
    interval_seconds: int | None = None
    execution_count: int = 0
    last_status: str = ""
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/schedules", response_model=ScheduleResponse, status_code=201)
async def create_schedule(data: ScheduleCreate, request: Request, db: AsyncSession = Depends(get_db)):
    """Create a new scheduled task."""
    require_admin_from_request(request)
    name = data.name.strip()
    project_id = data.project_id.strip()
    skill_name = data.skill_name.strip()
    description = data.description.strip()
    cron_expression = data.cron_expression.strip()
    if not name or not project_id:
        raise HTTPException(status_code=422, detail="name and project_id are required")

    # Validate cron expression
    try:
        CronParser.parse(cron_expression)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    now = datetime.now(timezone.utc)
    try:
        next_run = CronParser.next_run_after(cron_expression, now)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    task = ScheduledTask(
        id=str(uuid.uuid4()),
        name=name,
        description=description,
        cron_expression=cron_expression,
        skill_name=skill_name,
        project_id=project_id,
        next_run=next_run,
        loop_type="cron",
    )

    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.get("/schedules", response_model=list[ScheduleResponse])
async def list_schedules(
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List all scheduled tasks, optionally filtered by project."""
    require_admin_from_request(request)
    query = select(ScheduledTask).order_by(ScheduledTask.created_at)
    if project_id:
        query = query.where(ScheduledTask.project_id == project_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/schedules/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(schedule_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Get a scheduled task by ID."""
    require_admin_from_request(request)
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
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Update a scheduled task (enable/disable, change cron, etc.)."""
    require_admin_from_request(request)
    result = await db.execute(
        select(ScheduledTask).where(ScheduledTask.id == schedule_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Scheduled task not found")

    update_data = data.model_dump(exclude_unset=True)
    for key in ("name", "cron_expression", "skill_name", "description"):
        if key in update_data and isinstance(update_data[key], str):
            update_data[key] = update_data[key].strip()
            if key in {"name", "cron_expression"} and not update_data[key]:
                raise HTTPException(status_code=422, detail=f"{key} cannot be empty")

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
    elif update_data.get("enabled") is True and not task.next_run:
        try:
            update_data["next_run"] = CronParser.next_run_after(
                task.cron_expression,
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
async def delete_schedule(schedule_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Delete a scheduled task."""
    require_admin_from_request(request)
    result = await db.execute(
        select(ScheduledTask).where(ScheduledTask.id == schedule_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Scheduled task not found")

    await db.delete(task)
    await db.commit()
