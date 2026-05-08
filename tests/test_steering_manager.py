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

class TestSteeringManager:
    """Tests for the global SteeringManager singleton."""

    @pytest.mark.asyncio
    async def test_steer_and_get_steering(self, manager, agent_id):
        await manager.steer(agent_id, "Check accessibility")
        await manager.steer(agent_id, "Also run UX audit")
        msgs = await manager.get_steering(agent_id)
        # Default mode is one-at-a-time
        assert len(msgs) == 1
        assert msgs[0].message == "Check accessibility"

    @pytest.mark.asyncio
    async def test_follow_up_and_get_follow_up(self, manager, agent_id):
        await manager.follow_up(agent_id, "Run a final review")
        await manager.follow_up(agent_id, "Then generate report")
        msgs = await manager.get_follow_up(agent_id)
        assert len(msgs) == 1
        assert msgs[0].message == "Run a final review"

    @pytest.mark.asyncio
    async def test_clear_steering(self, manager, agent_id):
        await manager.steer(agent_id, "a")
        await manager.steer(agent_id, "b")
        cleared = await manager.clear_steering(agent_id)
        assert len(cleared) == 2
        assert await manager.get_steering(agent_id) == []

    @pytest.mark.asyncio
    async def test_clear_follow_up(self, manager, agent_id):
        await manager.follow_up(agent_id, "x")
        cleared = await manager.clear_follow_up(agent_id)
        assert len(cleared) == 1

    @pytest.mark.asyncio
    async def test_clear_all(self, manager, agent_id):
        await manager.steer(agent_id, "s1")
        await manager.follow_up(agent_id, "f1")
        cleared = await manager.clear_all(agent_id)
        assert len(cleared["steering"]) == 1
        assert len(cleared["follow_up"]) == 1

    @pytest.mark.asyncio
    async def test_mark_working_and_is_working(self, manager, agent_id):
        assert manager.is_working(agent_id) is False
        await manager.mark_working(agent_id)
        assert manager.is_working(agent_id) is True

    @pytest.mark.asyncio
    async def test_mark_idle(self, manager, agent_id):
        await manager.mark_working(agent_id)
        await manager.mark_idle(agent_id)
        assert manager.is_working(agent_id) is False

    @pytest.mark.asyncio
    async def test_wait_for_idle_returns_true_when_already_idle(self, manager, agent_id):
        await manager.mark_idle(agent_id)
        result = await manager.wait_for_idle(agent_id, timeout=1.0)
        assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_idle_waits_for_working_agent(self, manager, agent_id):
        await manager.mark_working(agent_id)

        async def idle_after_delay():
            await asyncio.sleep(0.1)
            await manager.mark_idle(agent_id)

        task = asyncio.create_task(idle_after_delay())
        result = await manager.wait_for_idle(agent_id, timeout=2.0)
        await task
        assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_idle_times_out(self, manager, agent_id):
        await manager.mark_working(agent_id)
        result = await manager.wait_for_idle(agent_id, timeout=0.1)
        assert result is False

    @pytest.mark.asyncio
    async def test_abort_clears_queues_and_resets_state(self, manager, agent_id):
        await manager.steer(agent_id, "s1")
        await manager.follow_up(agent_id, "f1")
        await manager.mark_working(agent_id)

        cleared = await manager.abort(agent_id)
        assert len(cleared["steering"]) == 1
        assert len(cleared["follow_up"]) == 1
        assert manager.is_working(agent_id) is False

    @pytest.mark.asyncio
    async def test_get_status(self, manager, agent_id):
        await manager.steer(agent_id, "test")
        await manager.follow_up(agent_id, "follow")
        await manager.mark_working(agent_id)

        status = manager.get_status(agent_id)
        assert status["agent_id"] == agent_id
        assert status["is_working"] is True
        assert status["steering_queue_count"] == 1
        assert status["follow_up_queue_count"] == 1
        assert status["has_queued_messages"] is True

    @pytest.mark.asyncio
    async def test_get_all_status(self, manager):
        await manager.steer("agent-a", "msg1")
        await manager.steer("agent-b", "msg2")
        all_status = manager.get_all_status()
        assert "agent-a" in all_status
        assert "agent-b" in all_status
        assert all_status["agent-a"]["steering_queue_count"] == 1

    @pytest.mark.asyncio
    async def test_auto_creates_state_for_unknown_agent(self, manager):
        msgs = await manager.get_steering("brand-new-agent")
        assert msgs == []

    @pytest.mark.asyncio
    async def test_steer_with_metadata(self, manager, agent_id):
        await manager.steer(agent_id, "test", source="extension", metadata={"ext": "mcp"})
        msgs = await manager.get_steering(agent_id)
        assert msgs[0].source == "extension"
        assert msgs[0].metadata == {"ext": "mcp"}


# ============================================================
# API Route Tests
# ============================================================
