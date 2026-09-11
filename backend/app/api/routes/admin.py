"""Admin dashboard API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.compute_registry import compute_registry
from app.core.field_encryption import safe_decrypt_field
from app.core.permissions import require_global_admin
from app.models.agent import Agent
from app.models.connection_string import ConnectionString
from app.models.database import get_db
from app.models.document import Document
from app.models.finding import Fact, Insight, Nugget, Recommendation
from app.models.llm_server import LLMServer
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task, TaskStatus
from app.models.telemetry_span import TelemetrySpan
from app.models.user import User, UserRole

router = APIRouter(prefix="/admin")


async def _count(db: AsyncSession, model, *conditions) -> int:
    query = select(func.count()).select_from(model)
    if conditions:
        query = query.where(*conditions)
    return int((await db.execute(query)).scalar() or 0)


def _admin_compute_stats_payload() -> dict:
    stats = compute_registry.get_stats(project_id=None)
    return {
        "scope": "global_admin",
        "project_id": None,
        **stats,
    }


@router.get("/overview")
async def admin_overview(request: Request, db: AsyncSession = Depends(get_db)):
    """Return global operational metrics for admin-only dashboard cards."""
    require_global_admin(request)

    tasks_by_status = {}
    for status in TaskStatus:
        tasks_by_status[status.value] = await _count(db, Task, Task.status == status)

    connection_strings = {
        "user_invites": await _count(
            db, ConnectionString, ConnectionString.token_type == "user_invite"
        ),
        "compute_donations": await _count(
            db, ConnectionString, ConnectionString.token_type == "compute_donation"
        ),
        "active": await _count(db, ConnectionString, ConnectionString.is_active.is_(True)),
        "redeemed": await _count(db, ConnectionString, ConnectionString.is_redeemed.is_(True)),
    }

    compute_stats = _admin_compute_stats_payload()
    relay_nodes = [
        node
        for node in compute_stats.get("nodes", [])
        if node.get("source") in {"relay", "browser"}
    ]
    telemetry_spans = await _count(db, TelemetrySpan)
    llm_requests = await _count(db, TelemetrySpan, TelemetrySpan.operation == "llm_request")

    return {
        "users": {
            "total": await _count(db, User),
            "admins": await _count(db, User, User.role == UserRole.ADMIN),
            "researchers": await _count(db, User, User.role == UserRole.RESEARCHER),
            "viewers": await _count(db, User, User.role == UserRole.VIEWER),
        },
        "projects": {
            "total": await _count(db, Project),
            "memberships": await _count(db, ProjectMember),
        },
        "research": {
            "documents": await _count(db, Document),
            "nuggets": await _count(db, Nugget),
            "facts": await _count(db, Fact),
            "insights": await _count(db, Insight),
            "recommendations": await _count(db, Recommendation),
        },
        "tasks": {
            "total": await _count(db, Task),
            "by_status": tasks_by_status,
        },
        "agents": {
            "total": await _count(db, Agent),
        },
        "compute": {
            "llm_servers": await _count(db, LLMServer),
            "healthy_llm_servers": await _count(db, LLMServer, LLMServer.is_healthy.is_(True)),
            "total_nodes": compute_stats.get("total_nodes", 0),
            "alive_nodes": compute_stats.get("alive_nodes", 0),
            "reachable_nodes": compute_stats.get("reachable_nodes", 0),
            "hardware_node_count": compute_stats.get("hardware_node_count", 0),
            "total_ram_gb": compute_stats.get("total_ram_gb", 0),
            "available_ram_gb": compute_stats.get("available_ram_gb", 0),
            "relay_nodes": len(relay_nodes),
            "online_relay_nodes": len(
                [node for node in relay_nodes if node.get("online") or node.get("is_reachable")]
            ),
        },
        "usage": {
            "telemetry_spans": telemetry_spans,
            "llm_requests": llm_requests,
            "token_metrics_status": "not_collected_yet",
            "compute_donation_metrics_status": "partial_runtime_only",
        },
        "connection_strings": connection_strings,
    }


@router.get("/compute/stats")
async def admin_compute_stats(request: Request):
    """Return global compute capacity only for global admins."""
    require_global_admin(request)
    return _admin_compute_stats_payload()


@router.get("/projects")
async def admin_projects(request: Request, db: AsyncSession = Depends(get_db)):
    """List all projects with member and activity counts."""
    require_global_admin(request)

    projects = (
        (await db.execute(select(Project).order_by(Project.updated_at.desc()))).scalars().all()
    )
    rows = []
    for project in projects:
        rows.append(
            {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "phase": project.phase.value
                if hasattr(project.phase, "value")
                else str(project.phase),
                "is_paused": project.is_paused,
                "owner_id": project.owner_id,
                "watch_folder_path": project.watch_folder_path,
                "created_at": project.created_at.isoformat() if project.created_at else None,
                "updated_at": project.updated_at.isoformat() if project.updated_at else None,
                "member_count": await _count(
                    db, ProjectMember, ProjectMember.project_id == project.id
                ),
                "task_count": await _count(db, Task, Task.project_id == project.id),
                "document_count": await _count(db, Document, Document.project_id == project.id),
                "finding_count": (
                    await _count(db, Nugget, Nugget.project_id == project.id)
                    + await _count(db, Fact, Fact.project_id == project.id)
                    + await _count(db, Insight, Insight.project_id == project.id)
                    + await _count(db, Recommendation, Recommendation.project_id == project.id)
                ),
            }
        )
    return {"projects": rows}


@router.get("/users")
async def admin_users(request: Request, db: AsyncSession = Depends(get_db)):
    """List all users with project access counts."""
    require_global_admin(request)

    users = (await db.execute(select(User).order_by(User.created_at.desc()))).scalars().all()
    rows = []
    for user in users:
        rows.append(
            {
                "id": user.id,
                "username": user.username,
                "email": safe_decrypt_field(user.email),
                "display_name": user.display_name,
                "role": user.role.value if hasattr(user.role, "value") else str(user.role),
                "project_count": await _count(db, ProjectMember, ProjectMember.user_id == user.id),
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            }
        )
    return {"users": rows}


@router.get("/access")
async def admin_access(request: Request, db: AsyncSession = Depends(get_db)):
    """List project memberships for admin access review."""
    require_global_admin(request)

    result = await db.execute(select(ProjectMember).order_by(ProjectMember.added_at.desc()))
    memberships = result.scalars().all()
    project_ids = {member.project_id for member in memberships}
    user_ids = {member.user_id for member in memberships}
    projects = {}
    users = {}
    if project_ids:
        project_rows = (
            (await db.execute(select(Project).where(Project.id.in_(project_ids)))).scalars().all()
        )
        projects = {project.id: project for project in project_rows}
    if user_ids:
        user_rows = (await db.execute(select(User).where(User.id.in_(user_ids)))).scalars().all()
        users = {user.id: user for user in user_rows}

    return {
        "memberships": [
            {
                **member.to_dict(),
                "project_name": projects.get(member.project_id).name
                if member.project_id in projects
                else "",
                "username": users.get(member.user_id).username if member.user_id in users else "",
                "user_email": safe_decrypt_field(users.get(member.user_id).email)
                if member.user_id in users
                else "",
            }
            for member in memberships
        ]
    }


@router.get("/connection-strings")
async def admin_connection_strings(request: Request, db: AsyncSession = Depends(get_db)):
    """List user invite and compute donation strings separately."""
    require_global_admin(request)

    result = await db.execute(select(ConnectionString).order_by(ConnectionString.created_at.desc()))
    strings = [conn.to_dict() for conn in result.scalars().all()]
    return {
        "user_invites": [conn for conn in strings if conn.get("token_type") == "user_invite"],
        "compute_donations": [
            conn for conn in strings if conn.get("token_type") == "compute_donation"
        ],
    }
