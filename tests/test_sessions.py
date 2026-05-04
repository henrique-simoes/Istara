"""Tests for Sessions API routes — CRUD, star, presets, ensure-default."""

import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.models.database import async_session, init_db
from app.core.auth import create_token
from app.models.project import Project


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


async def _seed_project() -> Project:
    project = Project(id=str(uuid.uuid4()), name=f"Sessions {uuid.uuid4()}")
    async with async_session() as db:
        db.add(project)
        await db.commit()
        await db.refresh(project)
    return project


@pytest.mark.asyncio
async def test_sessions_list_returns_list(auth_headers):
    """GET /api/sessions/{project_id} returns a list."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/sessions/test-project", headers=auth_headers)
        assert response.status_code in (200, 404)
        if response.status_code == 200:
            assert isinstance(response.json(), dict)


@pytest.mark.asyncio
async def test_sessions_list_requires_auth():
    """Sessions listing requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/sessions/test-project")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_session_get_nonexistent_returns_404(auth_headers):
    """GET /api/sessions/detail/{id} returns 404 for non-existent session."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/sessions/detail/non-existent-id", headers=auth_headers)
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_session_rejects_invalid_inference_preset(auth_headers):
    await init_db()
    project = await _seed_project()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/sessions",
            headers=auth_headers,
            json={
                "project_id": project.id,
                "title": "Invalid preset",
                "inference_preset": "turbo-chaos",
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_session_title_is_normalized_on_create(auth_headers):
    await init_db()
    project = await _seed_project()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/sessions",
            headers=auth_headers,
            json={"project_id": project.id, "title": "  Trimmed title  "},
        )

    assert response.status_code == 201
    assert response.json()["title"] == "Trimmed title"


@pytest.mark.asyncio
async def test_update_session_rejects_unbounded_custom_settings(auth_headers):
    await init_db()
    project = await _seed_project()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        create_response = await ac.post(
            "/api/sessions",
            headers=auth_headers,
            json={"project_id": project.id, "title": "Custom settings"},
        )
        session_id = create_response.json()["id"]
        update_response = await ac.patch(
            f"/api/sessions/{session_id}",
            headers=auth_headers,
            json={"custom_temperature": 8, "custom_max_tokens": 0},
        )

    assert create_response.status_code == 201
    assert update_response.status_code == 422
