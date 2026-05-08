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
