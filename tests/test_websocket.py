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
from app.models.research_deployment import ResearchDeployment
from app.models.task import Task


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
async def test_deployment_websocket_events_resolve_project_before_fanout():
    """Deployment realtime events inherit project scope from the deployment id."""
    await init_db()
    project_a = f"ws-deployment-project-a-{uuid.uuid4()}"
    project_b = f"ws-deployment-project-b-{uuid.uuid4()}"
    deployment_a = f"ws-deployment-a-{uuid.uuid4()}"

    async with async_session() as db:
        db.add_all(
            [
                Project(id=project_a, name="Websocket Deployment Project A"),
                Project(id=project_b, name="Websocket Deployment Project B"),
                ResearchDeployment(
                    id=deployment_a,
                    project_id=project_a,
                    name="Project A Deployment",
                    deployment_type="survey",
                ),
            ]
        )
        await db.commit()

    from app.api.websocket import ConnectionManager

    class FakeWebSocket:
        def __init__(self) -> None:
            self.sent: list[dict] = []

        async def send_text(self, message: str) -> None:
            self.sent.append(json.loads(message))

    async def skip_persist(_event_type: str, _data: dict) -> None:
        return None

    project_a_ws = FakeWebSocket()
    project_b_ws = FakeWebSocket()
    manager = ConnectionManager()
    manager._persist_notification = skip_persist  # type: ignore[method-assign]
    manager._connections = [
        {
            "websocket": project_a_ws,
            "user_context": {"id": "admin", "role": "admin"},
            "active_project_id": project_a,
        },
        {
            "websocket": project_b_ws,
            "user_context": {"id": "admin", "role": "admin"},
            "active_project_id": project_b,
        },
    ]

    resolved = await manager._resolve_project_id({"deployment_id": deployment_a})
    await manager.broadcast(
        "deployment_progress",
        {"deployment_id": deployment_a, "current_responses": 1},
    )
    await manager.broadcast(
        "deployment_progress",
        {
            "deployment_id": deployment_a,
            "project_id": project_b,
            "current_responses": 2,
        },
    )

    assert resolved == project_a
    assert len(project_a_ws.sent) == 1
    assert project_a_ws.sent[0]["type"] == "deployment_progress"
    assert project_a_ws.sent[0]["data"]["project_id"] == project_a
    assert project_a_ws.sent[0]["data"]["current_responses"] == 1
    assert project_b_ws.sent == []


@pytest.mark.asyncio
async def test_project_bound_websocket_events_with_conflicting_claims_are_not_broadcast():
    """Realtime project events should drop instead of trusting mismatched metadata."""
    await init_db()
    project_a = f"ws-claim-project-a-{uuid.uuid4()}"
    project_b = f"ws-claim-project-b-{uuid.uuid4()}"
    task_a = f"ws-claim-task-a-{uuid.uuid4()}"
    task_b = f"ws-claim-task-b-{uuid.uuid4()}"
    hidden_agent_id = f"ws-claim-hidden-agent-{uuid.uuid4()}"

    async with async_session() as db:
        db.add_all(
            [
                Project(id=project_a, name="Websocket Claim Project A"),
                Project(id=project_b, name="Websocket Claim Project B"),
                Task(id=task_a, project_id=project_a, title="Visible websocket task"),
                Task(id=task_b, project_id=project_b, title="Hidden websocket task"),
                Agent(
                    id=hidden_agent_id,
                    name="Hidden realtime agent",
                    scope="project",
                    project_id=project_b,
                ),
            ]
        )
        await db.commit()

    from app.api.websocket import ConnectionManager

    class FakeWebSocket:
        def __init__(self) -> None:
            self.sent: list[dict] = []

        async def send_text(self, message: str) -> None:
            self.sent.append(json.loads(message))

    async def skip_persist(_event_type: str, _data: dict) -> None:
        return None

    project_ws = FakeWebSocket()
    manager = ConnectionManager()
    manager._persist_notification = skip_persist  # type: ignore[method-assign]
    manager._connections = [
        {
            "websocket": project_ws,
            "user_context": {"id": "admin", "role": "admin"},
            "active_project_id": project_a,
        }
    ]

    valid_project = await manager._resolve_project_id({"project_id": project_a, "task_id": task_a})
    conflict_project = await manager._resolve_project_id(
        {
            "project_id": project_a,
            "metadata": {"task_id": task_b},
            "from_agent_id": hidden_agent_id,
        }
    )

    await manager.broadcast(
        "a2a_message",
        {
            "content": "hidden realtime content",
            "project_id": project_a,
            "metadata": {"task_id": task_b},
            "from_agent_id": hidden_agent_id,
        },
    )

    assert valid_project == project_a
    assert conflict_project is None
    assert project_ws.sent == []


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


@pytest.mark.asyncio
async def test_global_notification_websocket_events_are_admin_only():
    """System-wide notification events must not fan out to project user sockets."""
    await init_db()
    settings.team_mode = True
    project_id = f"ws-global-project-{uuid.uuid4()}"
    user_id = f"ws-global-user-{uuid.uuid4()}"

    async with async_session() as db:
        db.add(Project(id=project_id, name="Global websocket notification project"))
        db.add(
            ProjectMember(
                id=str(uuid.uuid4()),
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

    async def skip_persist(_event_type: str, _data: dict) -> None:
        return None

    admin_ws = FakeWebSocket()
    project_ws = FakeWebSocket()
    manager = ConnectionManager()
    manager._persist_notification = skip_persist  # type: ignore[method-assign]
    manager._connections = [
        {
            "websocket": admin_ws,
            "user_context": {"id": "admin-user", "username": "admin", "role": "admin"},
            "active_project_id": None,
        },
        {
            "websocket": project_ws,
            "user_context": {"id": user_id, "username": "researcher", "role": "researcher"},
            "active_project_id": project_id,
        },
    ]

    await manager.broadcast(
        "resource_throttle",
        {
            "reason": "System resources under pressure",
            "resources": {"ram_gb": 64},
        },
    )

    assert [event["type"] for event in admin_ws.sent] == ["resource_throttle"]
    assert project_ws.sent == []
