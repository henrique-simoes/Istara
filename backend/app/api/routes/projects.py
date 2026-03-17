"""Project CRUD API routes."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
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


@router.post("/projects/{project_id}/export")
async def export_project(project_id: str, export_path: str | None = None, db: AsyncSession = Depends(get_db)):
    """Export a project to a standalone folder on the user's computer.

    If export_path is not provided, exports to ~/ReClaw-Projects/{project_name}/
    """
    import json
    import shutil
    from pathlib import Path

    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Determine export path
    safe_name = "".join(c if c.isalnum() or c in "-_ " else "" for c in project.name).strip()
    if not export_path:
        export_path = str(Path.home() / "ReClaw-Projects" / safe_name)

    export_dir = Path(export_path)
    export_dir.mkdir(parents=True, exist_ok=True)

    # Export project metadata
    project_data = {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "phase": project.phase.value if project.phase else "discover",
        "company_context": project.company_context,
        "project_context": project.project_context,
        "guardrails": project.guardrails,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
    (export_dir / "project.json").write_text(json.dumps(project_data, indent=2))

    # Export findings
    from app.models.finding import Nugget, Fact, Insight, Recommendation
    findings_dir = export_dir / "findings"
    findings_dir.mkdir(exist_ok=True)

    for model, name in [(Nugget, "nuggets"), (Fact, "facts"), (Insight, "insights"), (Recommendation, "recommendations")]:
        res = await db.execute(select(model).where(model.project_id == project_id))
        items = res.scalars().all()
        data = []
        for item in items:
            d = {c.name: getattr(item, c.name) for c in item.__table__.columns}
            for k, v in d.items():
                if hasattr(v, "isoformat"):
                    d[k] = v.isoformat()
            data.append(d)
        (findings_dir / f"{name}.json").write_text(json.dumps(data, indent=2))

    # Export tasks
    from app.models.task import Task
    res = await db.execute(select(Task).where(Task.project_id == project_id))
    tasks = res.scalars().all()
    tasks_data = []
    for t in tasks:
        d = {c.name: getattr(t, c.name) for c in t.__table__.columns}
        for k, v in d.items():
            if hasattr(v, "isoformat"):
                d[k] = v.isoformat()
            elif hasattr(v, "value"):
                d[k] = v.value
        tasks_data.append(d)
    (export_dir / "tasks.json").write_text(json.dumps(tasks_data, indent=2))

    # Export chat messages
    from app.models.message import Message
    res = await db.execute(
        select(Message).where(Message.project_id == project_id).order_by(Message.created_at.asc())
    )
    messages = res.scalars().all()
    msgs_data = [
        {"id": m.id, "role": m.role, "content": m.content, "agent_id": m.agent_id, "created_at": m.created_at.isoformat() if m.created_at else None}
        for m in messages
    ]
    (export_dir / "messages.json").write_text(json.dumps(msgs_data, indent=2))

    # Copy uploaded files
    uploads_src = Path(settings.upload_dir) / project_id
    if uploads_src.exists():
        uploads_dest = export_dir / "files"
        if uploads_dest.exists():
            shutil.rmtree(uploads_dest)
        shutil.copytree(uploads_src, uploads_dest)

    # Create a README
    readme = f"""# {project.name}

Exported from ReClaw on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}

## Contents
- `project.json` — Project metadata and context
- `findings/` — Research findings (nuggets, facts, insights, recommendations)
- `tasks.json` — Kanban tasks
- `messages.json` — Chat history
- `files/` — Uploaded research files

## Re-importing
To import this project back into ReClaw, use the import feature or copy the files folder.
"""
    (export_dir / "README.md").write_text(readme)

    return {
        "exported": True,
        "path": str(export_dir),
        "files_count": len(list(export_dir.rglob("*"))),
    }
