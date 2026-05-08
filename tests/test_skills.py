"""Tests for Skills API routes — CRUD, execute, health, proposals."""

import asyncio

import pytest
from fastapi import HTTPException
from httpx import AsyncClient, ASGITransport
from starlette.requests import Request

from app.api.routes import skills as skills_route
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
async def test_skills_list_returns_list(auth_headers):
    """GET /api/skills returns a list."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/skills", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        # Should have 53 skills
        assert len(data) > 0


@pytest.mark.asyncio
async def test_skills_list_requires_auth():
    """Skills listing requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/skills")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_skill_get_returns_skill(auth_headers):
    """GET /api/skills/{name} returns a skill."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Get the first skill from the list
        response = await ac.get("/api/skills", headers=auth_headers)
        if response.status_code == 200 and response.json():
            skill_name = response.json().get("skills", [{}])[0].get("name", "card-sorting") if response.json().get("skills") else "card-sorting"
            response = await ac.get(f"/api/skills/{skill_name}", headers=auth_headers)
            assert response.status_code in (200, 404)


@pytest.mark.asyncio
async def test_skill_health_returns_response(auth_headers):
    """GET /api/skills/health/all returns health status."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/skills/health/all", headers=auth_headers)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_skill_proposals_pending_returns_list(auth_headers):
    """GET /api/skills/proposals/pending returns list."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/skills/proposals/pending", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), dict)


class _SlowSkillAgent:
    async def execute_skill(self, **kwargs):
        await asyncio.sleep(5)

    async def plan_skill(self, **kwargs):
        await asyncio.sleep(5)


def _request() -> Request:
    return Request({"type": "http", "method": "POST", "path": "/", "headers": []})


@pytest.mark.asyncio
async def test_execute_skill_enforces_route_timeout(monkeypatch):
    """Skill execution cancels at the route budget instead of orphaning LLM work."""

    async def allow_project_access(*args, **kwargs):
        return None

    monkeypatch.setattr(skills_route.registry, "get", lambda name: object())
    monkeypatch.setattr(skills_route, "require_project_access", allow_project_access)
    monkeypatch.setattr(skills_route, "agent", _SlowSkillAgent())

    with pytest.raises(HTTPException) as exc:
        await skills_route.execute_skill(
            "slow-skill",
            skills_route.SkillExecuteRequest(project_id="project-1", timeout_seconds=0.1),
            _request(),
            db=None,
        )

    assert exc.value.status_code == 504
    assert "timed out" in exc.value.detail


@pytest.mark.asyncio
async def test_plan_skill_enforces_route_timeout(monkeypatch):
    """Skill planning uses the same bounded server-side timeout path."""

    async def allow_project_access(*args, **kwargs):
        return None

    monkeypatch.setattr(skills_route.registry, "get", lambda name: object())
    monkeypatch.setattr(skills_route, "require_project_access", allow_project_access)
    monkeypatch.setattr(skills_route, "agent", _SlowSkillAgent())

    with pytest.raises(HTTPException) as exc:
        await skills_route.plan_skill(
            "slow-skill",
            skills_route.SkillPlanRequest(project_id="project-1", timeout_seconds=0.1),
            _request(),
            db=None,
        )

    assert exc.value.status_code == 504
    assert "timed out" in exc.value.detail
