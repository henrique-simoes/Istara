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
