"""Tests for Findings API routes — nuggets, facts, insights, recommendations."""

import pytest
import uuid
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


# ---------------------------------------------------------------------------
# Nuggets
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_nuggets_list_returns_list(auth_headers):
    """GET /api/findings/nuggets returns a list."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/findings/nuggets", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_nuggets_requires_auth():
    """Nuggets endpoint requires authentication."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/findings/nuggets")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_nugget_creation_normalizes_integrity_fields(auth_headers):
    """New and legacy nuggets expose source_location and tags for research integrity."""
    await init_db()
    project_id = f"findings-project-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Findings Integrity Project"))
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/findings/nuggets",
            headers=auth_headers,
            json={
                "project_id": project_id,
                "text": "Participants want clearer onboarding.",
                "source": "interview-01",
            },
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["source_location"] == "interview-01"
    assert payload["tags"] == ["untagged"]


# ---------------------------------------------------------------------------
# Facts
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_facts_list_returns_list(auth_headers):
    """GET /api/findings/facts returns a list."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/findings/facts", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_facts_requires_auth():
    """Facts endpoint requires authentication."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/findings/facts")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Insights
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_insights_list_returns_list(auth_headers):
    """GET /api/findings/insights returns a list."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/findings/insights", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_recommendations_list_returns_list(auth_headers):
    """GET /api/findings/recommendations returns a list."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/findings/recommendations", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_findings_summary_returns_dict(auth_headers):
    """GET /api/findings/summary/{project_id} returns a dict."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/findings/summary/test-project", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), dict)


# ---------------------------------------------------------------------------
# Evidence Chain
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_evidence_chain_returns_list(auth_headers):
    """GET /api/findings/{type}/{id}/evidence-chain returns a list or appropriate error."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/findings/nuggets/non-existent-id/evidence-chain", headers=auth_headers)
        # 200 if endpoint returns empty list, 400 if ID validation fails
        assert response.status_code in (200, 400, 404)
        if response.status_code == 200:
            assert isinstance(response.json(), list)
