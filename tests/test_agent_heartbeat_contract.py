"""Heartbeat interval contract tests for agent create/update APIs."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.core.auth import create_token
from app.main import app
from app.models.database import init_db


@pytest.fixture(autouse=True)
def reset_settings():
    original_jwt_secret = settings.jwt_secret
    yield
    settings.jwt_secret = original_jwt_secret


@pytest.fixture
def auth_headers():
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    token = create_token("user1", "testuser", "admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
@pytest.mark.parametrize("heartbeat_interval", [9, 3601])
async def test_agent_create_rejects_heartbeat_outside_contract(auth_headers, heartbeat_interval):
    """Agent creation must reject intervals outside the UI and worker contract."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/agents",
            headers=auth_headers,
            json={
                "name": "Invalid Heartbeat Agent",
                "role": "custom",
                "system_prompt": "Should never be created.",
                "capabilities": ["chat"],
                "heartbeat_interval": heartbeat_interval,
                "project_id": "heartbeat-contract-project",
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_agent_update_rejects_heartbeat_outside_contract(auth_headers):
    """Agent updates must enforce the same heartbeat bounds as creation."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        created = await ac.post(
            "/api/agents",
            headers=auth_headers,
            json={
                "name": "Heartbeat Update Agent",
                "role": "custom",
                "system_prompt": "Temporary validation target.",
                "capabilities": ["chat"],
                "project_id": "heartbeat-update-project",
            },
        )
        assert created.status_code == 201
        agent_id = created.json()["id"]
        try:
            response = await ac.patch(
                f"/api/agents/{agent_id}?project_id=heartbeat-update-project",
                headers=auth_headers,
                json={"heartbeat_interval": 3601},
            )
        finally:
            await ac.delete(
                f"/api/agents/{agent_id}?project_id=heartbeat-update-project",
                headers=auth_headers,
            )

    assert response.status_code == 422
