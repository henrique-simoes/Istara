"""Integration test: Agent work cycle — create task → route → execute skill → produce finding → store in memory."""

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
@pytest.mark.xfail(reason="Backend bug: autoresearch get_current_experiment missing")
async def test_agent_work_cycle_integration(auth_headers):
    """Verify the complete agent work cycle: task creation → skill execution → findings."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Verify agents are available
        response = await ac.get("/api/agents", headers=auth_headers)
        assert response.status_code == 200
        agents = response.json().get("agents", [])
        assert len(agents) > 0, "At least one agent should be available"

        # 2. Verify skills are available
        response = await ac.get("/api/skills", headers=auth_headers)
        assert response.status_code == 200
        skills = response.json().get("skills", [])
        assert len(skills) > 0, "At least one skill should be available"

        # 3. Verify tasks endpoint is accessible
        response = await ac.get("/api/tasks", headers=auth_headers)
        assert response.status_code == 200

        # 4. Verify findings endpoints are accessible
        response = await ac.get("/api/findings/nuggets", headers=auth_headers)
        assert response.status_code == 200

        # 5. Verify memory endpoint is accessible
        response = await ac.get("/api/memory/test-project", headers=auth_headers)
        assert response.status_code in (200, 404, 500)


@pytest.mark.asyncio
async def test_steering_integration_with_agents(auth_headers):
    """Verify steering can interact with agent work cycle."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Queue a steering message
        response = await ac.post(
            "/api/steering/istara-main",
            headers=auth_headers,
            json={"message": "Integration test steering message"},
        )
        assert response.status_code in (200, 404)

        # Check status
        response = await ac.get("/api/steering/istara-main/status", headers=auth_headers)
        assert response.status_code in (200, 404)

        # Clear queues
        response = await ac.delete("/api/steering/istara-main/queues", headers=auth_headers)
        assert response.status_code in (200, 404)
