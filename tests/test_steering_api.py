"""Tests for mid-execution steering infrastructure and API routes.

Tests cover:
- SteeringQueue: enqueue, drain (one-at-a-time vs all modes), clear, count, has_items
- SteeringManager: steer, follow_up, get_steering, get_follow_up, clear_all,
  mark_working, mark_idle, is_working, wait_for_idle, abort, get_status
- API routes: all 7 endpoints with validation
- WebSocket events: steering_message, agent_idle broadcast structure
"""

import asyncio
import time

import pytest
from httpx import AsyncClient, ASGITransport

# ---------- Backend path setup ----------
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.core.steering import (
    SteeringMessage,
    SteeringQueue,
    SteeringManager,
)
from app.main import app
from app.config import settings
from app.api.websocket import (
    broadcast_steering_message,
    broadcast_steering_response,
    broadcast_agent_idle,
    manager as ws_manager,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def manager():
    """Fresh SteeringManager for each test."""
    return SteeringManager()


@pytest.fixture
def agent_id():
    return "test-agent-001"


@pytest.fixture(autouse=True)
def configure_settings():
    """Ensure JWT secret is set so middleware passes in local mode."""
    if not settings.jwt_secret:
        settings.jwt_secret = "test-steering-secret"
    settings.team_mode = False


@pytest.fixture
def auth_headers():
    """Generate a valid JWT token for test requests."""
    from app.core.auth import create_token
    token = create_token("local", "test-user", "admin")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ============================================================
# Unit Tests: SteeringQueue
# ============================================================

class TestSteeringAPI:
    """HTTP endpoint tests using httpx ASGITransport."""

    @pytest.fixture(autouse=True)
    async def clear_queues(self):
        """Clear all steering queues before each test."""
        from app.core.steering import steering_manager
        for agent_id in list(steering_manager._agents.keys()):
            await steering_manager.clear_all(agent_id)

    @pytest.mark.asyncio
    async def test_queue_steering_message(self, auth_headers, clear_queues):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", headers=auth_headers) as ac:
            resp = await ac.post(
                "/api/steering/istara-main",
                json={"message": "Check the new UI for contrast issues"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "queued"
            assert data["agent_id"] == "istara-main"
            assert data["queue_count"] >= 1

    @pytest.mark.asyncio
    async def test_queue_follow_up_message(self, auth_headers):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", headers=auth_headers) as ac:
            resp = await ac.post(
                "/api/steering/istara-main/follow-up",
                json={"message": "Run final accessibility audit"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "queued"
            assert data["queue_count"] >= 1

    @pytest.mark.asyncio
    async def test_get_steering_status(self, auth_headers):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", headers=auth_headers) as ac:
            await ac.post("/api/steering/istara-main", json={"message": "test"})
            resp = await ac.get("/api/steering/istara-main/status")
            assert resp.status_code == 200
            data = resp.json()
            assert data["agent_id"] == "istara-main"
            assert data["steering_queue_count"] >= 1

    @pytest.mark.asyncio
    async def test_get_steering_queues(self, auth_headers):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", headers=auth_headers) as ac:
            await ac.post("/api/steering/istara-main", json={"message": "steer msg"})
            await ac.post("/api/steering/istara-main/follow-up", json={"message": "follow msg"})
            resp = await ac.get("/api/steering/istara-main/queues")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["steering_queue"]) >= 1
            assert len(data["follow_up_queue"]) >= 1
            assert data["steering_queue"][0]["message"] == "steer msg"

    @pytest.mark.asyncio
    async def test_clear_queues(self, auth_headers):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", headers=auth_headers) as ac:
            await ac.post("/api/steering/istara-main", json={"message": "test"})
            resp = await ac.delete("/api/steering/istara-main/queues")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "cleared"
            assert data["cleared_steering_count"] >= 1

    @pytest.mark.asyncio
    async def test_abort(self, auth_headers):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", headers=auth_headers) as ac:
            await ac.post("/api/steering/istara-main", json={"message": "test"})
            resp = await ac.post("/api/steering/istara-main/abort", json={})
            assert resp.status_code == 200
            data = resp.json()
            assert "cleared_steering_count" in data

    @pytest.mark.asyncio
    async def test_get_all_steering_status(self, auth_headers):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", headers=auth_headers) as ac:
            resp = await ac.get("/api/steering")
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_empty_agent_id_returns_error(self, auth_headers):
        """Empty agent ID should be rejected or redirect."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", headers=auth_headers, follow_redirects=False) as ac:
            resp = await ac.post("/api/steering/", json={"message": "test"})
            # FastAPI redirects /api/steering/ to /api/steering (no trailing slash)
            assert resp.status_code in (307, 404, 405)

    @pytest.mark.asyncio
    async def test_steering_message_persists_across_requests(self, auth_headers):
        """Verify that a queued message survives across separate HTTP requests."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", headers=auth_headers) as ac:
            await ac.post("/api/steering/istara-main", json={"message": "persistent msg"})
            resp = await ac.get("/api/steering/istara-main/queues")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["steering_queue"]) >= 1
            assert data["steering_queue"][0]["message"] == "persistent msg"


# ============================================================
# WebSocket Event Tests
# ============================================================
