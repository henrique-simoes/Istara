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

class TestSteeringQueue:
    """Tests for SteeringQueue — mirrors pi-mono's PendingMessageQueue."""

    def test_enqueue_and_has_items(self):
        q = SteeringQueue()
        assert q.has_items() is False
        q.enqueue(SteeringMessage(message="test"))
        assert q.has_items() is True

    def test_drain_one_at_a_time(self):
        q = SteeringQueue(mode="one-at-a-time")
        q.enqueue(SteeringMessage(message="first"))
        q.enqueue(SteeringMessage(message="second"))
        q.enqueue(SteeringMessage(message="third"))

        drained = q.drain()
        assert len(drained) == 1
        assert drained[0].message == "first"
        assert q.count() == 2

        drained = q.drain()
        assert len(drained) == 1
        assert drained[0].message == "second"
        assert q.count() == 1

    def test_drain_all_mode(self):
        q = SteeringQueue(mode="all")
        for i in range(5):
            q.enqueue(SteeringMessage(message=f"msg-{i}"))

        drained = q.drain()
        assert len(drained) == 5
        assert q.count() == 0

    def test_drain_empty_returns_empty_list(self):
        q = SteeringQueue()
        assert q.drain() == []

    def test_clear_returns_all_messages(self):
        q = SteeringQueue()
        q.enqueue(SteeringMessage(message="a"))
        q.enqueue(SteeringMessage(message="b"))
        cleared = q.clear()
        assert len(cleared) == 2
        assert q.count() == 0

    def test_count(self):
        q = SteeringQueue()
        assert q.count() == 0
        q.enqueue(SteeringMessage(message="x"))
        assert q.count() == 1
        q.enqueue(SteeringMessage(message="y"))
        assert q.count() == 2
        q.drain()
        assert q.count() == 1

    def test_mode_change_affects_drain(self):
        q = SteeringQueue(mode="one-at-a-time")
        for i in range(3):
            q.enqueue(SteeringMessage(message=f"m{i}"))
        q.mode = "all"
        drained = q.drain()
        assert len(drained) == 3

    def test_timestamp_is_set_automatically(self):
        q = SteeringQueue()
        before = time.time()
        q.enqueue(SteeringMessage(message="timed"))
        after = time.time()
        msgs = q.drain()
        assert before <= msgs[0].timestamp <= after


# ============================================================
# Unit Tests: SteeringManager
# ============================================================

class TestSteeringManager:
    """Tests for the global SteeringManager singleton."""

    def test_steer_and_get_steering(self, manager, agent_id):
        manager.steer(agent_id, "Check accessibility")
        manager.steer(agent_id, "Also run UX audit")
        msgs = manager.get_steering(agent_id)
        # Default mode is one-at-a-time
        assert len(msgs) == 1
        assert msgs[0].message == "Check accessibility"

    def test_follow_up_and_get_follow_up(self, manager, agent_id):
        manager.follow_up(agent_id, "Run a final review")
        manager.follow_up(agent_id, "Then generate report")
        msgs = manager.get_follow_up(agent_id)
        assert len(msgs) == 1
        assert msgs[0].message == "Run a final review"

    def test_clear_steering(self, manager, agent_id):
        manager.steer(agent_id, "a")
        manager.steer(agent_id, "b")
        cleared = manager.clear_steering(agent_id)
        assert len(cleared) == 2
        assert manager.get_steering(agent_id) == []

    def test_clear_follow_up(self, manager, agent_id):
        manager.follow_up(agent_id, "x")
        cleared = manager.clear_follow_up(agent_id)
        assert len(cleared) == 1

    def test_clear_all(self, manager, agent_id):
        manager.steer(agent_id, "s1")
        manager.follow_up(agent_id, "f1")
        cleared = manager.clear_all(agent_id)
        assert len(cleared["steering"]) == 1
        assert len(cleared["follow_up"]) == 1

    def test_mark_working_and_is_working(self, manager, agent_id):
        assert manager.is_working(agent_id) is False
        manager.mark_working(agent_id)
        assert manager.is_working(agent_id) is True

    def test_mark_idle(self, manager, agent_id):
        manager.mark_working(agent_id)
        manager.mark_idle(agent_id)
        assert manager.is_working(agent_id) is False

    @pytest.mark.asyncio
    async def test_wait_for_idle_returns_true_when_already_idle(self, manager, agent_id):
        manager.mark_idle(agent_id)
        result = await manager.wait_for_idle(agent_id, timeout=1.0)
        assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_idle_waits_for_working_agent(self, manager, agent_id):
        manager.mark_working(agent_id)

        async def idle_after_delay():
            await asyncio.sleep(0.1)
            manager.mark_idle(agent_id)

        task = asyncio.create_task(idle_after_delay())
        result = await manager.wait_for_idle(agent_id, timeout=2.0)
        await task
        assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_idle_times_out(self, manager, agent_id):
        manager.mark_working(agent_id)
        result = await manager.wait_for_idle(agent_id, timeout=0.1)
        assert result is False

    def test_abort_clears_queues_and_resets_state(self, manager, agent_id):
        manager.steer(agent_id, "s1")
        manager.follow_up(agent_id, "f1")
        manager.mark_working(agent_id)

        cleared = manager.abort(agent_id)
        assert len(cleared["steering"]) == 1
        assert len(cleared["follow_up"]) == 1
        assert manager.is_working(agent_id) is False

    def test_get_status(self, manager, agent_id):
        manager.steer(agent_id, "test")
        manager.follow_up(agent_id, "follow")
        manager.mark_working(agent_id)

        status = manager.get_status(agent_id)
        assert status["agent_id"] == agent_id
        assert status["is_working"] is True
        assert status["steering_queue_count"] == 1
        assert status["follow_up_queue_count"] == 1
        assert status["has_queued_messages"] is True

    def test_get_all_status(self, manager):
        manager.steer("agent-a", "msg1")
        manager.steer("agent-b", "msg2")
        all_status = manager.get_all_status()
        assert "agent-a" in all_status
        assert "agent-b" in all_status
        assert all_status["agent-a"]["steering_queue_count"] == 1

    def test_auto_creates_state_for_unknown_agent(self, manager):
        msgs = manager.get_steering("brand-new-agent")
        assert msgs == []

    def test_steer_with_metadata(self, manager, agent_id):
        manager.steer(agent_id, "test", source="extension", metadata={"ext": "mcp"})
        msgs = manager.get_steering(agent_id)
        assert msgs[0].source == "extension"
        assert msgs[0].metadata == {"ext": "mcp"}


# ============================================================
# API Route Tests
# ============================================================

class TestSteeringAPI:
    """HTTP endpoint tests using httpx ASGITransport."""

    @pytest.fixture(autouse=True)
    def clear_queues(self):
        """Clear all steering queues before each test."""
        from app.core.steering import steering_manager
        for agent_id in list(steering_manager._agents.keys()):
            steering_manager.clear_all(agent_id)

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

class TestSteeringWebSocketEvents:
    """Tests for steering-related WebSocket broadcast functions."""

    @pytest.mark.asyncio
    async def test_broadcast_steering_message_structure(self):
        """Verify the steering_message event has the correct payload structure."""
        received = []
        original = ws_manager.broadcast

        async def capture(event_type, data):
            received.append((event_type, data))

        ws_manager.broadcast = capture
        try:
            await broadcast_steering_message("istara-main", "Check contrast", source="user")
            assert len(received) == 1
            assert received[0][0] == "steering_message"
            assert received[0][1]["agent_id"] == "istara-main"
            assert received[0][1]["message"] == "Check contrast"
            assert received[0][1]["source"] == "user"
            assert received[0][1]["direction"] == "queued"
        finally:
            ws_manager.broadcast = original

    @pytest.mark.asyncio
    async def test_broadcast_steering_response_structure(self):
        """Verify the steering response event has the correct payload."""
        received = []
        original = ws_manager.broadcast

        async def capture(event_type, data):
            received.append((event_type, data))

        ws_manager.broadcast = capture
        try:
            await broadcast_steering_response("istara-main", "Found 3 contrast issues")
            assert len(received) == 1
            assert received[0][0] == "steering_message"
            assert received[0][1]["agent_id"] == "istara-main"
            assert received[0][1]["response"] == "Found 3 contrast issues"
            assert received[0][1]["direction"] == "response"
        finally:
            ws_manager.broadcast = original

    @pytest.mark.asyncio
    async def test_broadcast_agent_idle_structure(self):
        """Verify the agent_idle event has the correct payload."""
        received = []
        original = ws_manager.broadcast

        async def capture(event_type, data):
            received.append((event_type, data))

        ws_manager.broadcast = capture
        try:
            await broadcast_agent_idle("istara-main")
            assert len(received) == 1
            assert received[0][0] == "agent_idle"
            assert received[0][1]["agent_id"] == "istara-main"
        finally:
            ws_manager.broadcast = original
