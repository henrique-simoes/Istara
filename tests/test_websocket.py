"""WebSocket flow tests — verify auth, connection, and event structure."""

import json
import uuid

import pytest
from app.config import settings
from app.core.auth import create_token
from app.models.agent import Agent
from app.models.database import async_session, init_db
from app.models.project import Project
from app.models.project_member import ProjectMember


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


@pytest.mark.asyncio
async def test_websocket_project_subscription_requires_membership():
    """Project websocket subscriptions must be authorized before connection accept."""
    await init_db()
    settings.team_mode = True
    visible_project_id = f"ws-visible-{uuid.uuid4()}"
    hidden_project_id = f"ws-hidden-{uuid.uuid4()}"
    user_id = f"ws-user-{uuid.uuid4()}"

    async with async_session() as db:
        db.add_all(
            [
                Project(id=visible_project_id, name="Visible websocket project"),
                Project(id=hidden_project_id, name="Hidden websocket project"),
                ProjectMember(
                    id=str(uuid.uuid4()),
                    project_id=visible_project_id,
                    user_id=user_id,
                    role="viewer",
                    added_by="test",
                ),
            ]
        )
        await db.commit()

        from app.api.websocket import _can_subscribe_to_project

        user_context = {"id": user_id, "username": "researcher", "role": "researcher"}
        admin_context = {"id": "admin", "username": "admin", "role": "admin"}

        assert await _can_subscribe_to_project(db, user_context, visible_project_id) is True
        assert await _can_subscribe_to_project(db, user_context, hidden_project_id) is False
        assert await _can_subscribe_to_project(db, admin_context, hidden_project_id) is True
        assert await _can_subscribe_to_project(db, user_context, None) is False
        assert await _can_subscribe_to_project(db, admin_context, None) is True


@pytest.mark.asyncio
async def test_websocket_resolves_project_from_agent_id():
    """Agent realtime events inherit the owning project before fan-out."""
    await init_db()
    project_id = f"ws-agent-project-{uuid.uuid4()}"
    agent_id = f"ws-agent-{uuid.uuid4()}"

    async with async_session() as db:
        db.add(Project(id=project_id, name="Websocket agent project"))
        db.add(Agent(id=agent_id, name="Realtime Agent", scope="project", project_id=project_id))
        await db.commit()

    from app.api.websocket import ConnectionManager

    manager = ConnectionManager()
    resolved = await manager._resolve_project_id({"agent_id": agent_id, "thought": "project work"})

    assert resolved == project_id


@pytest.mark.asyncio
async def test_project_bound_websocket_events_without_scope_are_not_broadcast():
    """Malformed project-content events must not fall back to global broadcast."""
    from app.api.websocket import ConnectionManager

    class FakeWebSocket:
        def __init__(self) -> None:
            self.sent: list[dict] = []

        async def send_text(self, message: str) -> None:
            self.sent.append(json.loads(message))

    project_ws = FakeWebSocket()
    global_ws = FakeWebSocket()
    manager = ConnectionManager()
    manager._connections = [
        {"websocket": project_ws, "user_context": {"id": "u1"}, "active_project_id": "project-a"},
        {"websocket": global_ws, "user_context": {"id": "admin"}, "active_project_id": None},
    ]

    await manager.broadcast("agent_thinking", {"agent_id": "missing-agent", "thought": "hidden"})

    assert project_ws.sent == []
    assert global_ws.sent == []


@pytest.mark.asyncio
async def test_websocket_broadcast_rechecks_project_membership():
    """Project event fan-out must stop after a user loses project access."""
    await init_db()
    settings.team_mode = True
    project_id = f"ws-revoke-project-{uuid.uuid4()}"
    user_id = f"ws-revoke-user-{uuid.uuid4()}"
    member_id = str(uuid.uuid4())

    async with async_session() as db:
        db.add(Project(id=project_id, name="Revoked websocket project"))
        db.add(
            ProjectMember(
                id=member_id,
                project_id=project_id,
                user_id=user_id,
                role="viewer",
                added_by="test",
            )
        )
        await db.commit()

    from app.api.websocket import ConnectionManager

    class FakeWebSocket:
        def __init__(self) -> None:
            self.sent: list[dict] = []

        async def send_text(self, message: str) -> None:
            self.sent.append(json.loads(message))

    project_ws = FakeWebSocket()
    manager = ConnectionManager()

    async def skip_persist(_event_type: str, _data: dict) -> None:
        return None

    manager._persist_notification = skip_persist  # type: ignore[method-assign]
    manager._connections = [
        {
            "websocket": project_ws,
            "user_context": {"id": user_id, "username": "researcher", "role": "researcher"},
            "active_project_id": project_id,
        }
    ]

    await manager.broadcast(
        "file_processed",
        {"filename": "visible.txt", "chunks": 1, "project_id": project_id},
    )
    assert [event["data"]["filename"] for event in project_ws.sent] == ["visible.txt"]

    async with async_session() as db:
        member = await db.get(ProjectMember, member_id)
        assert member is not None
        await db.delete(member)
        await db.commit()

    await manager.broadcast(
        "file_processed",
        {"filename": "hidden.txt", "chunks": 1, "project_id": project_id},
    )

    assert [event["data"]["filename"] for event in project_ws.sent] == ["visible.txt"]
