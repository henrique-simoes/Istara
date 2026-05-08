"""Central authorization helpers for team-mode RBAC/ReBAC checks.

This module is intentionally small and explicit. It is the server-side policy
layer for global roles, project relationships, and project operation checks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.project import Project
from app.models.project_member import ProjectMember

ProjectRole = Literal["viewer", "researcher", "project_admin"]
GlobalRole = Literal["viewer", "researcher", "admin"]

GLOBAL_ROLE_RANK: dict[str, int] = {
    "viewer": 0,
    "researcher": 1,
    "admin": 2,
}

PROJECT_ROLE_RANK: dict[str, int] = {
    "viewer": 0,
    "researcher": 1,
    "member": 1,  # legacy role name
    "project_admin": 2,
    "admin": 2,  # legacy project-level admin role
}

NORMALIZED_PROJECT_ROLE: dict[str, ProjectRole] = {
    "viewer": "viewer",
    "researcher": "researcher",
    "member": "researcher",
    "project_admin": "project_admin",
    "admin": "project_admin",
}


@dataclass(frozen=True)
class Subject:
    """Authenticated request subject."""

    id: str
    username: str
    role: str


def get_subject(request: Request) -> Subject:
    """Return the authenticated subject attached by security middleware."""
    user = getattr(request.state, "user", None) or {}
    return Subject(
        id=str(user.get("id") or user.get("sub") or ""),
        username=str(user.get("username") or ""),
        role=str(user.get("role") or "viewer"),
    )


def is_global_admin(subject: Subject) -> bool:
    return subject.role == "admin"


def global_role_rank(role: str | None) -> int:
    return GLOBAL_ROLE_RANK.get((role or "").strip(), -1)


def has_global_role(subject: Subject, min_role: GlobalRole = "viewer") -> bool:
    if not settings.team_mode:
        return True
    return global_role_rank(subject.role) >= global_role_rank(min_role)


def normalize_project_role(role: str | None) -> ProjectRole:
    return NORMALIZED_PROJECT_ROLE.get((role or "").strip(), "viewer")


def project_role_rank(role: str | None) -> int:
    return PROJECT_ROLE_RANK.get((role or "").strip(), -1)


def require_global_admin(request: Request) -> Subject:
    """Require a global admin subject."""
    subject = get_subject(request)
    if not is_global_admin(subject):
        raise HTTPException(status_code=403, detail="Global admin access required.")
    return subject


def require_global_role(request: Request, min_role: GlobalRole = "viewer") -> Subject:
    """Require an authenticated global role at or above ``min_role``.

    In local desktop mode every request runs as the built-in local admin. In
    team mode the security middleware has already authenticated the request and
    attached the user context; this helper enforces the requested role tier.
    """
    subject = get_subject(request)
    if not has_global_role(subject, min_role):
        role_label = "authenticated user" if min_role == "viewer" else f"global {min_role}"
        raise HTTPException(status_code=403, detail=f"{role_label.capitalize()} access required.")
    return subject


async def get_project_role(
    db: AsyncSession,
    project_id: str,
    user_id: str,
) -> ProjectRole | None:
    """Return the user's normalized project role, if they are a member."""
    if not user_id:
        return None
    result = await db.execute(
        select(ProjectMember.role).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    role = result.scalar_one_or_none()
    if role is None:
        return None
    return normalize_project_role(role)


async def can_access_project(
    db: AsyncSession,
    request: Request,
    project_id: str,
    *,
    min_role: ProjectRole = "viewer",
) -> bool:
    """Return whether the request subject has project access at min_role."""
    if not settings.team_mode:
        return True

    subject = get_subject(request)
    if is_global_admin(subject):
        return True

    role = await get_project_role(db, project_id, subject.id)
    if role is None:
        return False
    return project_role_rank(role) >= project_role_rank(min_role)


async def can_admin_project(db: AsyncSession, request: Request, project_id: str) -> bool:
    """Return whether the subject can administer project-scoped settings."""
    return await can_access_project(db, request, project_id, min_role="project_admin")


async def require_project_access(
    db: AsyncSession,
    request: Request,
    project_id: str,
    *,
    min_role: ProjectRole = "viewer",
    conceal_unrelated: bool = True,
) -> Subject:
    """Require access to a project at the requested project role.

    Unknown or uninvited projects use 404 by default to avoid project
    enumeration. Visible projects with insufficient role use 403.
    """
    subject = get_subject(request)
    if not settings.team_mode or is_global_admin(subject):
        return subject

    role = await get_project_role(db, project_id, subject.id)
    if role is None:
        status = 404 if conceal_unrelated else 403
        raise HTTPException(status_code=status, detail="Project not found")

    if project_role_rank(role) < project_role_rank(min_role):
        raise HTTPException(status_code=403, detail="Insufficient project permissions.")
    return subject


async def get_visible_project_or_404(
    db: AsyncSession,
    request: Request,
    project_id: str,
    *,
    min_role: ProjectRole = "viewer",
) -> Project:
    """Load a project and enforce visibility/role semantics."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await require_project_access(db, request, project_id, min_role=min_role)
    return project
