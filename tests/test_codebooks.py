"""Tests for Codebooks API routes — CRUD for codebooks and codes."""

import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.models.codebook import Code, Codebook
from app.models.database import async_session, init_db
from app.models.project import Project
from app.core.auth import create_token


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


@pytest.mark.asyncio
async def test_codebooks_list_requires_project_scope(auth_headers):
    """GET /api/codebooks requires an explicit active project."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/codebooks", headers=auth_headers)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_codebooks_list_returns_project_codebooks(auth_headers):
    """GET /api/codebooks?project_id=... returns only active-project codebooks."""
    await init_db()
    project_id = str(uuid.uuid4())
    other_project_id = str(uuid.uuid4())
    visible_id = str(uuid.uuid4())
    hidden_id = str(uuid.uuid4())
    async with async_session() as db:
        db.add_all(
            [
                Project(id=project_id, name="Codebook List A"),
                Project(id=other_project_id, name="Codebook List B"),
                Codebook(id=visible_id, project_id=project_id, name="Visible Codebook"),
                Codebook(id=hidden_id, project_id=other_project_id, name="Hidden Codebook"),
            ]
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            "/api/codebooks",
            params={"project_id": project_id},
            headers=auth_headers,
        )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [visible_id]


@pytest.mark.asyncio
async def test_codebooks_requires_auth():
    """Codebooks requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/codebooks")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_codebook_and_code_by_id_routes_require_matching_project_id(auth_headers):
    """By-id codebook and code routes require the caller's active project."""
    await init_db()
    settings.team_mode = True
    project_id = str(uuid.uuid4())
    other_project_id = str(uuid.uuid4())
    codebook_id = str(uuid.uuid4())
    code_id = str(uuid.uuid4())

    async with async_session() as db:
        db.add_all(
            [
                Project(id=project_id, name="Codebook Scope A"),
                Project(id=other_project_id, name="Codebook Scope B"),
                Codebook(
                    id=codebook_id,
                    project_id=project_id,
                    name="Scoped Codebook",
                ),
                Code(
                    id=code_id,
                    codebook_id=codebook_id,
                    name="Scoped Code",
                ),
            ]
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        stale_codebook = await ac.get(
            f"/api/codebooks/{codebook_id}",
            params={"project_id": other_project_id},
            headers=auth_headers,
        )
        active_codebook = await ac.get(
            f"/api/codebooks/{codebook_id}",
            params={"project_id": project_id},
            headers=auth_headers,
        )
        stale_code_create = await ac.post(
            "/api/codes",
            params={"project_id": other_project_id},
            json={"codebook_id": codebook_id, "name": "Wrong Project"},
            headers=auth_headers,
        )
        stale_code_update = await ac.patch(
            f"/api/codes/{code_id}",
            params={"project_id": other_project_id},
            json={"name": "Wrong Project"},
            headers=auth_headers,
        )

    assert stale_codebook.status_code == 404
    assert active_codebook.status_code == 200
    assert active_codebook.json()["project_id"] == project_id
    assert stale_code_create.status_code == 404
    assert stale_code_update.status_code == 404
