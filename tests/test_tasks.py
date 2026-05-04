"""Tests for Tasks API routes — CRUD, move, attach/detach, lock/unlock."""

import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.models.database import async_session, init_db
from app.core.auth import create_token
from app.models.document import Document, DocumentStatus
from app.models.project import Project
from app.models.task import Task, TaskStatus


@pytest.fixture(autouse=True)
def reset_settings():
    original_team_mode = settings.team_mode
    original_jwt_secret = settings.jwt_secret
    yield
    settings.team_mode = original_team_mode
    settings.jwt_secret = original_jwt_secret


@pytest.fixture
def auth_headers():
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    token = create_token("user1", "testuser", "admin")
    return {"Authorization": f"Bearer {token}"}


async def _seed_project(name: str = "Tasks Test Project") -> Project:
    project = Project(id=str(uuid.uuid4()), name=f"{name} {uuid.uuid4()}")
    async with async_session() as db:
        db.add(project)
        await db.commit()
        await db.refresh(project)
    return project


async def _seed_document(project_id: str, title: str = "Task Document") -> Document:
    doc = Document(
        id=str(uuid.uuid4()),
        project_id=project_id,
        title=title,
        file_name=f"{title.lower().replace(' ', '-')}.txt",
        file_type=".txt",
        status=DocumentStatus.READY,
        content_text="Document evidence",
    )
    async with async_session() as db:
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
    return doc


async def _seed_task(project_id: str, title: str = "Seeded Task") -> Task:
    task = Task(id=str(uuid.uuid4()), project_id=project_id, title=title, status=TaskStatus.BACKLOG)
    async with async_session() as db:
        db.add(task)
        await db.commit()
        await db.refresh(task)
    return task


@pytest.mark.asyncio
async def test_tasks_list_returns_list(auth_headers):
    """GET /api/tasks returns a list."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/tasks", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_tasks_list_requires_auth():
    """Tasks listing requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/tasks")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_task_move_nonexistent_returns_404(auth_headers):
    """POST /api/tasks/{id}/move returns 404 for non-existent task."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/tasks/non-existent-id/move", headers=auth_headers, json={"position": 0})
        assert response.status_code in (404, 422)


@pytest.mark.asyncio
async def test_task_lock_nonexistent_returns_404(auth_headers):
    """POST /api/tasks/{id}/lock returns 404 for non-existent task."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/tasks/non-existent-id/lock", headers=auth_headers)
        assert response.status_code in (404, 422)


@pytest.mark.asyncio
async def test_task_unlock_nonexistent_returns_404(auth_headers):
    """POST /api/tasks/{id}/unlock returns 404 for non-existent task."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/tasks/non-existent-id/unlock", headers=auth_headers)
        assert response.status_code in (404, 422)


@pytest.mark.asyncio
async def test_human_approval_moves_review_task_to_done(auth_headers):
    """Only a human review action moves an In Review task to Done."""
    await init_db()
    project = await _seed_project("Review Flow")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        created = await ac.post(
            "/api/tasks",
            headers=auth_headers,
            json={"project_id": project.id, "title": "Approve reviewed work"},
        )
        assert created.status_code == 201
        task_id = created.json()["id"]

        moved = await ac.post(
            f"/api/tasks/{task_id}/move?status=in_review",
            headers=auth_headers,
        )
        assert moved.status_code == 200
        assert moved.json()["status"] == "in_review"
        assert moved.json()["review_state"] == "awaiting_review"

        approved = await ac.post(
            f"/api/tasks/{task_id}/review/approve",
            headers=auth_headers,
            json={"reviewed_by": "tester", "note": "Looks correct."},
        )
        assert approved.status_code == 200
        payload = approved.json()
        assert payload["task"]["status"] == "done"
        assert payload["task"]["review_state"] == "approved"
        assert payload["event"]["outcome"] == "approved"


@pytest.mark.asyncio
async def test_done_task_revision_returns_to_backlog_with_feedback(auth_headers):
    """A Done task can be flagged later and must leave Done for agent action."""
    await init_db()
    project = await _seed_project("Revision Flow")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        created = await ac.post(
            "/api/tasks",
            headers=auth_headers,
            json={"project_id": project.id, "title": "Reopen wrong work"},
        )
        task_id = created.json()["id"]
        await ac.post(f"/api/tasks/{task_id}/move?status=in_review", headers=auth_headers)
        await ac.post(f"/api/tasks/{task_id}/review/approve", headers=auth_headers, json={})

        revised = await ac.post(
            f"/api/tasks/{task_id}/review/request-revision",
            headers=auth_headers,
            json={
                "what_to_review": "The synthesis missed the pricing evidence; rerun with the pricing document.",
                "next_status": "backlog",
                "failure_category": "missing_evidence",
                "labels": [{"name": "pricing", "color": "#2563eb", "kind": "task"}],
            },
        )
        assert revised.status_code == 200
        payload = revised.json()
        assert payload["task"]["status"] == "backlog"
        assert payload["task"]["review_state"] == "rejected_after_done"
        assert payload["task"]["failure_streak"] == 1
        assert payload["event"]["next_status"] == "backlog"
        assert payload["event"]["failure_category"] == "missing_evidence"


@pytest.mark.asyncio
async def test_revision_cannot_send_task_back_to_review(auth_headers):
    """Rejected work must return to backlog or in progress, not In Review."""
    await init_db()
    project = await _seed_project("Invalid Revision Target")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        created = await ac.post(
            "/api/tasks",
            headers=auth_headers,
            json={"project_id": project.id, "title": "Invalid revision target"},
        )
        task_id = created.json()["id"]
        await ac.post(f"/api/tasks/{task_id}/move?status=in_review", headers=auth_headers)
        response = await ac.post(
            f"/api/tasks/{task_id}/review/request-revision",
            headers=auth_headers,
            json={"what_to_review": "Needs more evidence.", "next_status": "in_review"},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_patch_cannot_mark_task_done(auth_headers):
    """Generic task patching cannot bypass the human review approval path."""
    await init_db()
    project = await _seed_project("Patch Done Bypass")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        created = await ac.post(
            "/api/tasks",
            headers=auth_headers,
            json={"project_id": project.id, "title": "No patch done bypass"},
        )
        task_id = created.json()["id"]
        response = await ac.patch(
            f"/api/tasks/{task_id}",
            headers=auth_headers,
            json={"status": "done"},
        )
        assert response.status_code == 409


@pytest.mark.asyncio
async def test_task_create_rejects_foreign_input_document(auth_headers):
    """Task inputs must belong to the same project as the task."""
    await init_db()
    project = await _seed_project("Task Project")
    other_project = await _seed_project("Other Document Project")
    foreign_doc = await _seed_document(other_project.id, "Foreign Evidence")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/tasks",
            headers=auth_headers,
            json={
                "project_id": project.id,
                "title": "Analyze local documents only",
                "input_document_ids": [foreign_doc.id],
            },
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_task_attach_rejects_foreign_document(auth_headers):
    """Attach/detach endpoints must not link documents from another project."""
    await init_db()
    project = await _seed_project("Attach Project")
    other_project = await _seed_project("Foreign Attach Project")
    task = await _seed_task(project.id)
    foreign_doc = await _seed_document(other_project.id, "Attach Foreign Evidence")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            f"/api/tasks/{task.id}/attach?document_id={foreign_doc.id}&direction=input",
            headers=auth_headers,
        )

    assert response.status_code == 404
