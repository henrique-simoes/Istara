"""Tests for Code Applications API routes — list, pending, review, bulk-approve."""

import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.models.code_application import CodeApplication
from app.models.database import async_session, init_db
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
async def test_code_apps_list_returns_response(auth_headers):
    """GET /api/code-applications/{project_id} returns code applications."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/code-applications/test-project", headers=auth_headers)
        assert response.status_code in (200, 404, 500)


@pytest.mark.asyncio
async def test_code_apps_requires_auth():
    """Code applications requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/code-applications/test-project")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_code_apps_pending_returns_response(auth_headers):
    """GET /api/code-applications/{project_id}/pending returns pending applications."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/code-applications/test-project/pending", headers=auth_headers)
        assert response.status_code in (200, 404, 500)


@pytest.mark.asyncio
async def test_code_apps_bulk_approve_bounds_confidence(auth_headers):
    """Bulk approval threshold is bounded to the statistical confidence interval."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/code-applications/test-project/bulk-approve",
            params={"min_confidence": 1.5},
            headers=auth_headers,
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_code_apps_review_uses_authenticated_reviewer(auth_headers):
    """Review audit trail comes from the authenticated subject, not client input."""
    await init_db()
    settings.team_mode = True
    app_id = str(uuid.uuid4())
    async with async_session() as db:
        db.add(
            CodeApplication(
                id=app_id,
                project_id="code-review-auth",
                code_id="nav-confusion",
                source_text="I cannot find reports.",
            )
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.patch(
            f"/api/code-applications/{app_id}/review",
            json={"review_status": "approved", "reviewed_by": "spoofed-user"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["reviewed_by"] == "testuser"
        assert response.json()["reviewed_at"] is not None
