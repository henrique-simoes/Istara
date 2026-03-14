"""Project CRUD API routes."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.versioning import ProjectVersioning
from app.models.database import get_db
from app.models.project import Project, ProjectPhase

router = APIRouter()


class ProjectCreate(BaseModel):
    """Request body for creating a project."""

    name: str
    description: str = ""
    phase: ProjectPhase = ProjectPhase.DISCOVER
    company_context: str = ""
    project_context: str = ""
    guardrails: str = ""


class ProjectUpdate(BaseModel):
    """Request body for updating a project."""

    name: str | None = None
    description: str | None = None
    phase: ProjectPhase | None = None
    company_context: str | None = None
    project_context: str | None = None
    guardrails: str | None = None


class ProjectResponse(BaseModel):
    """Project response schema."""

    id: str
    name: str
    description: str
    phase: ProjectPhase
    company_context: str
    project_context: str
    guardrails: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


@router.get("/projects", response_model=list[ProjectResponse])
async def list_projects(db: AsyncSession = Depends(get_db)):
    """List all projects."""
    result = await db.execute(select(Project).order_by(Project.updated_at.desc()))
    return result.scalars().all()


@router.post("/projects", response_model=ProjectResponse, status_code=201)
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_db)):
    """Create a new project."""
    project_id = str(uuid.uuid4())

    project = Project(
        id=project_id,
        name=data.name,
        description=data.description,
        phase=data.phase,
        company_context=data.company_context,
        project_context=data.project_context,
        guardrails=data.guardrails,
    )

    db.add(project)
    await db.commit()
    await db.refresh(project)

    # Initialize version control for the project
    versioning = ProjectVersioning(project_id)
    versioning.init()
    versioning.save_json("project.json", {
        "name": data.name,
        "description": data.description,
        "phase": data.phase.value,
    }, message=f"Create project: {data.name}")

    return project


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Get a project by ID."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a project."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    await db.commit()
    await db.refresh(project)

    # Version the change
    versioning = ProjectVersioning(project_id)
    versioning.save_json("project.json", {
        "name": project.name,
        "description": project.description,
        "phase": project.phase.value,
        "company_context": project.company_context,
        "project_context": project.project_context,
        "guardrails": project.guardrails,
    }, message=f"Update project: {', '.join(update_data.keys())}")

    return project


@router.delete("/projects/{project_id}", status_code=204)
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a project and all its data."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await db.delete(project)
    await db.commit()


@router.get("/projects/{project_id}/versions")
async def get_project_versions(project_id: str, limit: int = 50):
    """Get version history for a project."""
    versioning = ProjectVersioning(project_id)
    history = versioning.get_history(limit=limit)
    return [
        {
            "commit_hash": v.commit_hash,
            "message": v.message,
            "author": v.author,
            "timestamp": v.timestamp.isoformat(),
            "files_changed": v.files_changed,
        }
        for v in history
    ]
