"""Project CRUD API routes."""

import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.permissions import (
    get_project_role,
    get_subject,
    get_visible_project_or_404,
    is_global_admin,
    normalize_project_role,
    require_global_admin,
    require_project_access,
)
from app.core.versioning import ProjectVersioning
from app.models.database import get_db
from app.models.project import Project, ProjectPhase

logger = logging.getLogger(__name__)

router = APIRouter()


def _global_agentic_engine() -> str:
    """Return the normalized global engine without an eager Pi import."""
    from app.core.pi_replacement import PI_ENGINE_VALUES

    value = str(getattr(settings, "agentic_engine_default", "legacy") or "").strip().lower()
    return "pi" if value in PI_ENGINE_VALUES else "legacy"


def _embed_model() -> str:
    """Canonical embedding model identity (safe metadata: name only).

    Mirrors ``app.core.embeddings._embed_model_name`` and the settings route;
    the W8 vector-space invariant keeps the rules in lockstep.
    """
    from app.core.pi_runtime.embedding_profile import get_active_embedding_profile

    return get_active_embedding_profile().model_id


def _validate_watch_folder(folder_path: str) -> Path:
    folder = Path(folder_path).expanduser()
    try:
        resolved = folder.resolve()
    except OSError as exc:
        raise HTTPException(status_code=400, detail=f"Folder cannot be resolved: {exc}") from exc

    if not resolved.exists():
        raise HTTPException(status_code=400, detail=f"Folder does not exist: {folder_path}")
    if not resolved.is_dir():
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {folder_path}")

    if resolved == Path(resolved.anchor):
        raise HTTPException(status_code=400, detail="Project folder cannot be a filesystem root.")

    try:
        home = Path.home().resolve()
        if resolved == home:
            raise HTTPException(
                status_code=400, detail="Project folder cannot be the whole home directory."
            )
    except RuntimeError:
        pass

    return resolved


async def _stop_project_background_work(project_id: str, db: AsyncSession) -> dict:
    """Best-effort shutdown for project-owned autonomous/background work."""
    stopped = {
        "meta_hyperagent": False,
        "autoresearch": False,
        "channels": 0,
    }

    try:
        from app.core.meta_hyperagent import meta_hyperagent

        if meta_hyperagent.is_running_for_project(project_id):
            meta_hyperagent.stop(project_id=project_id)
            stopped["meta_hyperagent"] = True
    except Exception:
        logger.exception("Failed to stop Meta-Hyperagent for paused project %s", project_id)

    try:
        from app.core.autoresearch_engine import autoresearch_engine

        current = autoresearch_engine.get_current_experiment()
        active_project_id = str(getattr(autoresearch_engine, "active_project_id", "") or "") or (
            str(current.get("project_id") or "") if current else ""
        )
        if autoresearch_engine.is_running and active_project_id == project_id:
            autoresearch_engine.request_stop()
            stopped["autoresearch"] = True
    except Exception:
        logger.exception("Failed to stop AutoResearch for paused project %s", project_id)

    try:
        from app.services.channel_service import stop_project_channel_instances

        stopped["channels"] = await stop_project_channel_instances(db, project_id)
    except Exception:
        logger.exception("Failed to stop channels for paused project %s", project_id)

    return stopped


class ProjectCreate(BaseModel):
    """Request body for creating a project."""

    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=10000)
    phase: ProjectPhase = ProjectPhase.DISCOVER
    company_context: str = Field(default="", max_length=50000)
    project_context: str = Field(default="", max_length=50000)
    guardrails: str = Field(default="", max_length=50000)

    @field_validator("name", mode="before")
    @classmethod
    def _strip_required_text(cls, value: str) -> str:
        return str(value or "").strip()

    @field_validator(
        "description", "company_context", "project_context", "guardrails", mode="before"
    )
    @classmethod
    def _strip_optional_text(cls, value: str | None) -> str:
        return str(value or "").strip()


class ProjectUpdate(BaseModel):
    """Request body for updating a project."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    phase: ProjectPhase | None = None
    company_context: str | None = Field(default=None, max_length=50000)
    project_context: str | None = Field(default=None, max_length=50000)
    guardrails: str | None = Field(default=None, max_length=50000)
    # W8 UX parity: per-project engine selector (None/"" = inherit global default).
    agentic_engine: str | None = Field(default=None, max_length=32)

    @field_validator(
        "name", "description", "company_context", "project_context", "guardrails", mode="before"
    )
    @classmethod
    def _strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return str(value).strip()

    @field_validator("agentic_engine", mode="before")
    @classmethod
    def _validate_engine(cls, value: str | None) -> str | None:
        if value is None:
            return None
        engine = str(value).strip().lower()
        if not engine:
            return None  # inherit the global default
        from app.core.pi_replacement import PI_ENGINE_VALUES

        if engine != "legacy" and engine not in PI_ENGINE_VALUES:
            raise ValueError(f"unknown agentic engine: {engine}")
        return engine


class LinkFolderRequest(BaseModel):
    folder_path: str = Field(min_length=1, max_length=2000)

    @field_validator("folder_path", mode="before")
    @classmethod
    def _strip_path(cls, value: str) -> str:
        return str(value or "").strip()


class ProjectResponse(BaseModel):
    """Project response schema."""

    id: str
    name: str
    description: str
    phase: ProjectPhase
    company_context: str
    project_context: str
    guardrails: str
    is_paused: bool = False
    owner_id: str = ""
    watch_folder_path: str | None = None
    agentic_engine: str | None = None
    global_agentic_engine: str = "legacy"
    embed_model: str = "nomic-embed-text"
    current_user_project_role: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


async def _project_response(
    project: Project,
    request: Request,
    db: AsyncSession,
) -> dict:
    subject = get_subject(request)
    role = (
        "project_admin"
        if is_global_admin(subject)
        else await get_project_role(db, project.id, subject.id)
    )
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "phase": project.phase,
        "company_context": project.company_context,
        "project_context": project.project_context,
        "guardrails": project.guardrails,
        "is_paused": project.is_paused,
        "owner_id": project.owner_id,
        "watch_folder_path": project.watch_folder_path,
        "agentic_engine": project.agentic_engine,
        "global_agentic_engine": _global_agentic_engine(),
        "embed_model": _embed_model(),
        "current_user_project_role": role,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    }


@router.get("/projects", response_model=list[ProjectResponse])
async def list_projects(request: Request, db: AsyncSession = Depends(get_db)):
    """List visible projects.

    Global admins see every project. Team-mode non-admins see only projects
    they were explicitly invited to via ProjectMember.
    """
    from app.models.project_member import ProjectMember

    subject = get_subject(request)
    query = select(Project).order_by(Project.updated_at.desc())
    if settings.team_mode and not is_global_admin(subject):
        query = (
            select(Project)
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(ProjectMember.user_id == subject.id)
            .order_by(Project.updated_at.desc())
        )
    result = await db.execute(query)
    return [await _project_response(project, request, db) for project in result.scalars().all()]


@router.post("/projects", response_model=ProjectResponse, status_code=201)
async def create_project(data: ProjectCreate, request: Request, db: AsyncSession = Depends(get_db)):
    """Create a new project. Global admin only in team mode."""
    from app.models.project_member import ProjectMember

    subject = get_subject(request)
    if settings.team_mode:
        require_global_admin(request)

    project_id = str(uuid.uuid4())

    project = Project(
        id=project_id,
        name=data.name,
        description=data.description,
        phase=data.phase,
        company_context=data.company_context,
        project_context=data.project_context,
        guardrails=data.guardrails,
        owner_id=subject.id,
    )

    db.add(project)
    if subject.id:
        db.add(
            ProjectMember(
                id=str(uuid.uuid4()),
                project_id=project_id,
                user_id=subject.id,
                role="project_admin",
                added_by=subject.id,
            )
        )
    await db.commit()
    await db.refresh(project)

    # Initialize version control for the project
    versioning = ProjectVersioning(project_id)
    versioning.init()
    versioning.save_json(
        "project.json",
        {
            "name": data.name,
            "description": data.description,
            "phase": data.phase.value,
        },
        message=f"Create project: {data.name}",
    )

    # Auto-register file watcher for the project's upload directory
    upload_dir = str(Path(settings.upload_dir) / project_id)
    Path(upload_dir).mkdir(parents=True, exist_ok=True)
    file_watcher = getattr(request.app.state, "file_watcher", None)
    if file_watcher:
        file_watcher.add_watch(upload_dir, project_id)

    return await _project_response(project, request, db)


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Get a project by ID."""
    project = await get_visible_project_or_404(db, request, project_id)
    return await _project_response(project, request, db)


@router.patch("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    data: ProjectUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Update a project. Requires project admin or global admin."""
    project = await get_visible_project_or_404(db, request, project_id, min_role="project_admin")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    await db.commit()
    await db.refresh(project)

    # Version the change
    versioning = ProjectVersioning(project_id)
    versioning.save_json(
        "project.json",
        {
            "name": project.name,
            "description": project.description,
            "phase": project.phase.value,
            "company_context": project.company_context,
            "project_context": project.project_context,
            "guardrails": project.guardrails,
        },
        message=f"Update project: {', '.join(update_data.keys())}",
    )

    return await _project_response(project, request, db)


@router.post("/projects/{project_id}/pause")
async def pause_project(project_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Pause a project — agents and loops stop executing for this project."""
    project = await get_visible_project_or_404(db, request, project_id, min_role="project_admin")
    project.is_paused = True
    await db.commit()
    stopped = await _stop_project_background_work(project_id, db)
    return {"status": "paused", "project_id": project_id, "stopped": stopped}


@router.post("/projects/{project_id}/resume")
async def resume_project(project_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Resume a paused project."""
    project = await get_visible_project_or_404(db, request, project_id, min_role="project_admin")
    project.is_paused = False
    await db.commit()
    return {"status": "resumed", "project_id": project_id}


@router.post("/projects/{project_id}/link-folder")
async def link_folder(
    project_id: str,
    data: LinkFolderRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Link an external folder to a project for automatic file monitoring.
    Supports any local folder — Google Drive, Dropbox, or plain directories."""
    await require_project_access(db, request, project_id, min_role="project_admin")
    folder = _validate_watch_folder(data.folder_path)

    project = await get_visible_project_or_404(db, request, project_id, min_role="project_admin")

    project.watch_folder_path = str(folder)
    await db.commit()

    # Register with file watcher
    file_watcher = getattr(request.app.state, "file_watcher", None)
    if file_watcher:
        file_watcher.add_watch(str(folder), project_id)
        logger.info(f"Linked external folder for project {project_id}: {folder}")

    return {
        "status": "linked",
        "project_id": project_id,
        "watch_folder_path": str(folder),
    }


@router.post("/projects/{project_id}/unlink-folder")
async def unlink_folder(project_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Remove the external folder link from a project.
    Existing documents are kept, but new files won't be monitored."""
    project = await get_visible_project_or_404(db, request, project_id, min_role="project_admin")

    old_path = project.watch_folder_path
    project.watch_folder_path = None
    await db.commit()

    # Remove from file watcher
    file_watcher = getattr(request.app.state, "file_watcher", None)
    if file_watcher and old_path:
        file_watcher.remove_watch(old_path)
        logger.info(f"Unlinked external folder for project {project_id}: {old_path}")

    return {"status": "unlinked", "project_id": project_id}


@router.delete("/projects/{project_id}", status_code=204)
async def delete_project(project_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Delete a project and all its data. Admin only."""
    require_global_admin(request)
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Clean up entities that lack FK cascade (no ForeignKey constraint)
    from app.core.scheduler import ScheduledTask
    from app.models.context_dag import ContextDAGNode
    from app.models.session import ChatSession

    # Delete orphaned scheduled tasks for this project
    await db.execute(delete(ScheduledTask).where(ScheduledTask.project_id == project_id))
    # Delete orphaned DAG nodes for sessions belonging to this project
    session_ids_result = await db.execute(
        select(ChatSession.id).where(ChatSession.project_id == project_id)
    )
    session_ids = [row[0] for row in session_ids_result.fetchall()]
    if session_ids:
        await db.execute(delete(ContextDAGNode).where(ContextDAGNode.session_id.in_(session_ids)))

    await db.delete(project)
    await db.commit()


@router.get("/projects/{project_id}/versions")
async def get_project_versions(
    project_id: str, request: Request, limit: int = 50, db: AsyncSession = Depends(get_db)
):
    """Get version history for a project."""
    await get_visible_project_or_404(db, request, project_id)
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
async def export_project(
    project_id: str,
    request: Request,
    export_path: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Export a project to a standalone folder on the user's computer.

    If export_path is not provided, exports to ~/Istara-Projects/{project_name}/
    """
    import json
    import shutil
    from pathlib import Path

    project = await get_visible_project_or_404(db, request, project_id, min_role="project_admin")

    # Determine export path
    safe_name = "".join(c if c.isalnum() or c in "-_ " else "" for c in project.name).strip()
    if not export_path:
        export_path = str(Path.home() / "Istara-Projects" / safe_name)

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
        "exported_at": datetime.now(UTC).isoformat(),
    }
    (export_dir / "project.json").write_text(json.dumps(project_data, indent=2))

    # Export findings
    from app.models.finding import Fact, Insight, Nugget, Recommendation

    findings_dir = export_dir / "findings"
    findings_dir.mkdir(exist_ok=True)

    for model, name in [
        (Nugget, "nuggets"),
        (Fact, "facts"),
        (Insight, "insights"),
        (Recommendation, "recommendations"),
    ]:
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
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "agent_id": m.agent_id,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in messages
    ]
    (export_dir / "messages.json").write_text(json.dumps(msgs_data, indent=2))

    # Export documents
    from app.models.document import Document

    res = await db.execute(select(Document).where(Document.project_id == project_id))
    documents = res.scalars().all()
    docs_data = [d.to_dict() for d in documents]
    (export_dir / "documents.json").write_text(json.dumps(docs_data, indent=2))

    # Export sessions
    from app.models.session import ChatSession

    res = await db.execute(select(ChatSession).where(ChatSession.project_id == project_id))
    chat_sessions = res.scalars().all()
    sessions_data = []
    for s in chat_sessions:
        d = {c.name: getattr(s, c.name) for c in s.__table__.columns}
        for k, v in d.items():
            if hasattr(v, "isoformat"):
                d[k] = v.isoformat()
            elif hasattr(v, "value"):
                d[k] = v.value
        sessions_data.append(d)
    (export_dir / "sessions.json").write_text(json.dumps(sessions_data, indent=2))

    # Export codebooks
    from app.models.codebook import Codebook

    res = await db.execute(select(Codebook).where(Codebook.project_id == project_id))
    codebooks = res.scalars().all()
    codebooks_data = []
    for cb in codebooks:
        d = {c.name: getattr(cb, c.name) for c in cb.__table__.columns}
        for k, v in d.items():
            if hasattr(v, "isoformat"):
                d[k] = v.isoformat()
            elif hasattr(v, "value"):
                d[k] = v.value
        codebooks_data.append(d)
    (export_dir / "codebooks.json").write_text(json.dumps(codebooks_data, indent=2))

    # Copy uploaded files
    uploads_src = Path(settings.upload_dir) / project_id
    if uploads_src.exists():
        uploads_dest = export_dir / "files"
        if uploads_dest.exists():
            shutil.rmtree(uploads_dest)
        shutil.copytree(uploads_src, uploads_dest)

    # Create a README
    readme = f"""# {project.name}

Exported from Istara on {datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")}

## Contents
- `project.json` — Project metadata and context
- `findings/` — Research findings (nuggets, facts, insights, recommendations)
- `documents.json` — All project documents with metadata, tags, and atomic paths
- `tasks.json` — Kanban tasks
- `messages.json` — Chat history
- `sessions.json` — Chat sessions and inference presets
- `codebooks.json` — Qualitative codebooks
- `files/` — Uploaded research files

## Re-importing
To import this project back into Istara, use the import feature or copy the files folder.
"""
    (export_dir / "README.md").write_text(readme)

    return {
        "exported": True,
        "path": str(export_dir),
        "files_count": len(list(export_dir.rglob("*"))),
    }


# ── Project Members ──────────────────────────────────────────────────


class AddMemberRequest(BaseModel):
    user_id: str
    role: str = "researcher"  # project_admin | researcher | viewer


class UpdateMemberRoleRequest(BaseModel):
    role: str


@router.get("/projects/{project_id}/members")
async def list_project_members(
    project_id: str, request: Request, db: AsyncSession = Depends(get_db)
):
    """List all members of a project with their last active time."""
    from app.models.project_member import ProjectMember
    from app.models.user import User

    await require_project_access(db, request, project_id, min_role="viewer")

    result = await db.execute(select(ProjectMember).where(ProjectMember.project_id == project_id))
    members = result.scalars().all()

    # Enrich with user info
    user_ids = [m.user_id for m in members]
    users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
    users_by_id = {u.id: u for u in users_result.scalars().all()}

    return {
        "members": [
            {
                **m.to_dict(),
                "username": users_by_id[m.user_id].username
                if m.user_id in users_by_id
                else "unknown",
                "email": users_by_id[m.user_id].email if m.user_id in users_by_id else "",
                "display_name": getattr(users_by_id.get(m.user_id), "display_name", "") or "",
            }
            for m in members
        ]
    }


@router.post("/projects/{project_id}/members")
async def add_project_member(
    project_id: str, data: AddMemberRequest, request: Request, db: AsyncSession = Depends(get_db)
):
    """Add a server user to this project. Global or project admin only."""
    from app.models.project_member import ProjectMember
    from app.models.user import User

    subject = get_subject(request)
    await get_visible_project_or_404(db, request, project_id, min_role="project_admin")
    role = normalize_project_role(data.role)

    # Verify user exists on this server
    user = await db.get(User, data.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found on this server")

    # Check not already a member
    existing = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == data.user_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="User is already a member of this project")

    # Get current user ID for added_by
    member = ProjectMember(
        id=str(uuid.uuid4()),
        project_id=project_id,
        user_id=data.user_id,
        role=role,
        added_by=subject.id,
    )
    db.add(member)
    await db.commit()

    return {"added": True, "member_id": member.id, "user_id": data.user_id, "role": role}


@router.delete("/projects/{project_id}/members/{user_id}")
async def remove_project_member(
    project_id: str, user_id: str, request: Request, db: AsyncSession = Depends(get_db)
):
    """Remove a user from a project. Global or project admin only."""
    from app.models.project_member import ProjectMember

    await get_visible_project_or_404(db, request, project_id, min_role="project_admin")

    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found in this project")

    await db.delete(member)
    await db.commit()

    return {"removed": True, "user_id": user_id}


@router.patch("/projects/{project_id}/members/{user_id}")
async def update_member_role(
    project_id: str,
    user_id: str,
    data: UpdateMemberRoleRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Change a member's project-level role. Global or project admin only."""
    from app.models.project_member import ProjectMember

    await get_visible_project_or_404(db, request, project_id, min_role="project_admin")
    role = normalize_project_role(data.role)

    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found in this project")

    member.role = role
    await db.commit()

    return {"updated": True, "user_id": user_id, "role": role}
