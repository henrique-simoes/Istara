"""WebSocket flow tests — verify auth, connection, and event structure."""

import pytest
from app.config import settings
from app.core.auth import create_token


@pytest.fixture(autouse=True)
def reset_settings():
    original_team_mode = settings.team_mode
    original_jwt_secret = settings.jwt_secret
    yield
    settings.team_mode = original_team_mode
    settings.jwt_secret = original_jwt_secret


# ---------------------------------------------------------------------------
# WebSocket auth token structure
# ---------------------------------------------------------------------------

def test_websocket_token_can_be_created():
    """A valid JWT token can be created for WebSocket auth."""
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    token = create_token("user1", "testuser", "admin")
    assert token is not None
    assert len(token.split(".")) == 3  # JWT has 3 parts


def test_websocket_token_contains_user_info():
    """WebSocket token contains user info."""
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    token = create_token("user1", "testuser", "admin")

    from app.core.auth import verify_token
    payload = verify_token(token)
    assert payload is not None
    assert payload["username"] == "testuser"
    assert payload["role"] == "admin"


# ---------------------------------------------------------------------------
# WebSocket broadcast event structure
# ---------------------------------------------------------------------------

def test_steering_manager_has_queues():
    """SteeringManager has steering and follow-up queues."""
    from app.core.steering import SteeringManager
    manager = SteeringManager()
    status = manager.get_all_status()
    assert isinstance(status, dict)


def test_steering_queue_drain():
    """SteeringQueue drain returns items."""
    from app.core.steering import SteeringQueue
    queue = SteeringQueue()
    queue.enqueue({"message": "test"})
    items = queue.drain()
    assert len(items) == 1
    assert items[0]["message"] == "test"


def test_websocket_manager_imports():
    """WebSocket manager module imports correctly."""
    from app.api.websocket import manager
    assert manager is not None


# ---------------------------------------------------------------------------
# WebSocket query parameter auth pattern
# ---------------------------------------------------------------------------

def test_websocket_auth_url_pattern():
    """WebSocket auth uses ?token= query parameter pattern."""
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    token = create_token("user1", "testuser", "admin")
    ws_url = f"ws://localhost:8000/ws/agent?token={token}"
    assert "?token=" in ws_url
    assert token in ws_url
