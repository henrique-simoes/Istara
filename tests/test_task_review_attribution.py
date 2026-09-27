"""K1: a Done approval or revision request is attributed to the signed-in reviewer.

The approve and request-revision routes took `reviewed_by` from the request body, so the review
record named whoever the client claimed; Kanban moves and the legacy verify route recorded "local".
"""

from __future__ import annotations

import app.core.agentic  # noqa: F401  (import-order guard)

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.models.database import async_session, init_db


async def _task_in_review():
    from app.models.project import Project
    from app.models.task import Task, TaskStatus

    await init_db()
    project_id, task_id = str(uuid.uuid4()), str(uuid.uuid4())
    async with async_session() as db:
        db.add(Project(id=project_id, name="Attribution"))
        db.add(Task(id=task_id, project_id=project_id, title="Plan interviews",
                    status=TaskStatus.IN_REVIEW, review_state="awaiting_review",
                    agent_notes="Drafted the interview guide and a recruiting plan in detail.",
                    progress=1.0))
        await db.commit()
    return project_id, task_id


async def _events(task_id):
    from app.models.task_review import TaskReviewEvent

    async with async_session() as db:
        return (
            (await db.execute(select(TaskReviewEvent).where(TaskReviewEvent.task_id == task_id)))
            .scalars()
            .all()
        )


async def _team_reviewer(monkeypatch):
    """A real researcher account in team mode (the token is checked against the user table)."""
    from app.config import settings
    from app.core.auth import create_token, hash_password
    from app.core.field_encryption import hash_field
    from app.models.user import User

    monkeypatch.setattr(settings, "team_mode", True)
    if not settings.jwt_secret:
        monkeypatch.setattr(settings, "jwt_secret", "test-suite-secret")
    username = f"rev-{uuid.uuid4().hex[:8]}"
    async with async_session() as db:
        db.add(User(id=f"user-{username}", username=username, email=f"{username}@example.invalid",
                    email_hash=hash_field(f"{username}@example.invalid"),
                    password_hash=hash_password("synthetic-pass-123"), role="admin",
                    display_name=username))
        await db.commit()
    token = create_token(f"user-{username}", username, "admin", mfa_verified=True)
    return username, {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_local_mode_never_records_the_client_supplied_name(admin_auth_headers):
    project_id, task_id = await _task_in_review()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            f"/api/tasks/{task_id}/review/approve?project_id={project_id}",
            headers=admin_auth_headers,
            json={"reviewed_by": "someone-else", "note": "ok"},
        )
    assert response.status_code == 200, response.text
    assert [e.created_by for e in await _events(task_id)] == ["local"]


@pytest.mark.asyncio
async def test_team_approval_names_the_signed_in_reviewer(monkeypatch):
    project_id, task_id = await _task_in_review()
    username, headers = await _team_reviewer(monkeypatch)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            f"/api/tasks/{task_id}/review/approve?project_id={project_id}",
            headers=headers,
            json={"reviewed_by": "someone-else", "note": "ok"},
        )
    assert response.status_code == 200, response.text
    assert [e.created_by for e in await _events(task_id)] == [username]


@pytest.mark.asyncio
async def test_team_revision_request_names_the_signed_in_reviewer(monkeypatch):
    project_id, task_id = await _task_in_review()
    username, headers = await _team_reviewer(monkeypatch)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            f"/api/tasks/{task_id}/review/request-revision?project_id={project_id}",
            headers=headers,
            json={"what_to_review": "Add screener questions.", "reviewed_by": "someone-else"},
        )
    assert response.status_code == 200, response.text
    assert [e.created_by for e in await _events(task_id)] == [username]
