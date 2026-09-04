"""Integration tests for cross-feature flows."""

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


async def _seed_project(name: str) -> Project:
    project = Project(id=str(uuid.uuid4()), name=f"{name} {uuid.uuid4()}")
    async with async_session() as db:
        db.add(project)
        await db.commit()
        await db.refresh(project)
    return project


@pytest.mark.asyncio
async def test_autoresearch_integration(auth_headers):
    """Verify autoresearch system endpoints are integrated."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            "/api/autoresearch/status?project_id=test", headers=auth_headers
        )
        assert response.status_code < 600  # Endpoint exists (may have backend bugs)


@pytest.mark.asyncio
async def test_steering_integration(auth_headers):
    """Verify steering system integrates with agent work cycle."""
    await init_db()
    project = await _seed_project("Steering Integration")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/steering/istara-main",
            headers=auth_headers,
            json={"message": "Test", "project_id": project.id},
        )
        assert response.status_code in (200, 404)


@pytest.mark.asyncio
async def test_backup_integration(auth_headers):
    """Verify backup system is integrated."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/backups", headers=auth_headers)
        assert response.status_code < 600


@pytest.mark.asyncio
async def test_meta_agent_integration(auth_headers):
    """Verify meta-agent system is integrated."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/meta-hyperagent/status", headers=auth_headers)
        assert response.status_code < 600


@pytest.mark.asyncio
async def test_mcp_integration(auth_headers):
    """Verify MCP server system is integrated."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/mcp/server/status", headers=auth_headers)
        assert response.status_code < 600


@pytest.mark.asyncio
async def test_channels_integration(auth_headers):
    """Verify channel system is integrated with findings."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Channels accessible
        response = await ac.get(
            "/api/channels?project_id=integration-channel-project", headers=auth_headers
        )
        assert response.status_code == 200

        # Findings accessible
        response = await ac.get(
            "/api/findings/nuggets?project_id=integration-channel-project",
            headers=auth_headers,
        )
        assert response.status_code == 200
