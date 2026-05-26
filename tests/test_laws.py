"""Tests for UX Laws API routes — list, compliance, radar, match, by-heuristic."""

import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.models.database import init_db
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
async def test_laws_list_returns_list(auth_headers):
    """GET /api/laws returns a list of UX laws."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/laws", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 30


@pytest.mark.asyncio
async def test_laws_list_requires_auth():
    """Laws listing requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/laws")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_laws_compliance_returns_response(auth_headers):
    """GET /api/laws/compliance/{project_id} returns compliance data."""
    await init_db()
    project_id = f"law-compliance-{uuid.uuid4()}"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(f"/api/laws/compliance/{project_id}", headers=auth_headers)
    assert response.status_code == 200
    assert "by_law" in response.json()


@pytest.mark.asyncio
async def test_laws_radar_returns_response(auth_headers):
    """GET /api/laws/compliance/{project_id}/radar returns radar data."""
    await init_db()
    project_id = f"law-radar-{uuid.uuid4()}"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(f"/api/laws/compliance/{project_id}/radar", headers=auth_headers)
    assert response.status_code == 200
    assert {"categories", "category_scores", "detailed_axes"}.issubset(response.json())


@pytest.mark.asyncio
async def test_laws_phrase_matching_detects_multiword_keywords(auth_headers):
    """Keyword matcher should respect phrase keywords such as hard-to-click targets."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            "/api/laws/match",
            params={"query": "The small tap target is hard to click on mobile.", "top_k": 3},
            headers=auth_headers,
        )
        assert response.status_code == 200
        law_ids = [item["law_id"] for item in response.json()]
        assert "fitts-law" in law_ids


@pytest.mark.asyncio
async def test_laws_compliance_scores_tagged_findings(auth_headers):
    """Compliance profile should be evaluated when project findings have ux-law tags."""
    await init_db()
    project_id = f"law-proj-{uuid.uuid4()}"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        created = await ac.post(
            "/api/findings/nuggets",
            json={
                "project_id": project_id,
                "text": "The primary button is too small and hard to tap.",
                "source": "ux-audit",
                "tags": ["ux-law:fitts-law"],
            },
            headers=auth_headers,
        )
        assert created.status_code == 201

        response = await ac.get(f"/api/laws/compliance/{project_id}", headers=auth_headers)
        assert response.status_code == 200
        profile = response.json()
        assert profile["evaluated"] is True
        assert profile["evidence_count"] == 1
        assert profile["law_tag_count"] == 1
        fitts = next(item for item in profile["by_law"] if item["law_id"] == "fitts-law")
        assert fitts["violation_count"] == 1
        assert created.json()["id"] in fitts["finding_ids"]


@pytest.mark.asyncio
async def test_laws_match_rejects_unbounded_top_k(auth_headers):
    """Match endpoint has a bounded top_k to protect request cost."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            "/api/laws/match",
            params={"query": "button", "top_k": 999},
            headers=auth_headers,
        )
        assert response.status_code == 422
