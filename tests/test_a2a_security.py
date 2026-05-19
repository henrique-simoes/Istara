"""Security tests for the public A2A JSON-RPC endpoint."""

import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.config import settings
from app.core.auth import create_token
from app.api.routes.a2a import _a2a_rate_limiter, _a2a_replay_cache, _a2a_tasks_send_rate_limiter
from app.main import app
from app.core.audit_middleware import AuditLog
from app.models.agent import A2AMessage, Agent
from app.models.database import async_session, init_db
from app.models.project import Project
from app.models.project_member import ProjectMember


@pytest.fixture(autouse=True)
def reset_settings():
    original_team_mode = settings.team_mode
    original_jwt_secret = settings.jwt_secret
    original_network_access_token = settings.network_access_token
    original_agent_card_auth = settings.a2a_agent_card_auth_required_team_mode
    original_a2a_rate = settings.a2a_rate_limit_per_minute
    original_a2a_tasks_rate = settings.a2a_tasks_send_rate_limit_per_minute
    _a2a_rate_limiter.clear()
    _a2a_tasks_send_rate_limiter.clear()
    _a2a_replay_cache.clear()
    yield
    settings.team_mode = original_team_mode
    settings.jwt_secret = original_jwt_secret
    settings.network_access_token = original_network_access_token
    settings.a2a_agent_card_auth_required_team_mode = original_agent_card_auth
    settings.a2a_rate_limit_per_minute = original_a2a_rate
    settings.a2a_tasks_send_rate_limit_per_minute = original_a2a_tasks_rate
    _a2a_rate_limiter.clear()
    _a2a_tasks_send_rate_limiter.clear()
    _a2a_replay_cache.clear()


async def _clear_a2a_messages() -> None:
    async with async_session() as db:
        await db.execute(delete(A2AMessage))
        await db.commit()


async def _seed_a2a_project(user_id: str = "researcher-a2a", role: str = "researcher") -> str:
    project_id = f"a2a-security-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="A2A Security Project"))
        db.add(
            ProjectMember(
                id=str(uuid.uuid4()),
                project_id=project_id,
                user_id=user_id,
                role=role,
                added_by="test",
            )
        )
        await db.commit()
    return project_id


@pytest.mark.asyncio
async def test_a2a_tasks_send_requires_authentication_in_team_mode():
    """Team-mode JSON-RPC writes must not bypass the /api auth middleware."""
    await init_db()
    await _clear_a2a_messages()
    settings.team_mode = True

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/a2a",
            json={
                "jsonrpc": "2.0",
                "method": "tasks/send",
                "params": {"message": {"text": "persist me without auth"}},
                "id": "auth-required",
            },
        )

    async with async_session() as db:
        stored = (
            (await db.execute(select(A2AMessage).where(A2AMessage.content.like("%persist me%"))))
            .scalars()
            .all()
        )

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Authentication required for A2A JSON-RPC."
    assert stored == []


@pytest.mark.asyncio
async def test_a2a_tasks_send_allows_authenticated_researcher_and_records_actor():
    """Authenticated researchers can submit bounded A2A tasks with actor traceability."""
    await init_db()
    await _clear_a2a_messages()
    settings.team_mode = True
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    token = create_token("researcher-a2a", "researcher", "researcher")
    project_id = await _seed_a2a_project()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/a2a",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "jsonrpc": "2.0",
                "method": "tasks/send",
                "params": {
                    "from": "external-client",
                    "to": "istara-main",
                    "message": {
                        "text": "Review this bounded task",
                        "metadata": {"source": "security-test", "project_id": project_id},
                    },
                },
                "id": "researcher-submit",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["result"]["status"] == "submitted"

    async with async_session() as db:
        message = (
            await db.execute(select(A2AMessage).where(A2AMessage.id == payload["result"]["id"]))
        ).scalar_one()

    metadata = json.loads(message.extra_data)
    assert metadata["source"] == "security-test"
    assert metadata["project_id"] == project_id
    assert metadata["submitted_by_user_id"] == "researcher-a2a"
    assert metadata["submitted_by_username"] == "researcher"


@pytest.mark.asyncio
async def test_a2a_tasks_send_requires_project_scope():
    """A2A task writes must name a project so messages cannot become global content."""
    await init_db()
    await _clear_a2a_messages()
    settings.team_mode = True
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    token = create_token("researcher-a2a", "researcher", "researcher")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/a2a",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "jsonrpc": "2.0",
                "method": "tasks/send",
                "params": {"message": {"text": "No project should not persist"}},
                "id": "missing-project",
            },
        )

    async with async_session() as db:
        stored = (
            (
                await db.execute(
                    select(A2AMessage).where(A2AMessage.content == "No project should not persist")
                )
            )
            .scalars()
            .all()
        )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "project_id is required for A2A tasks/send."
    assert stored == []


@pytest.mark.asyncio
async def test_a2a_rejects_oversized_body_before_persistence():
    """A2A request bodies have a hard cap to prevent memory and log abuse."""
    await init_db()
    await _clear_a2a_messages()
    settings.team_mode = True
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    token = create_token("researcher-a2a", "researcher", "researcher")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/a2a",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "jsonrpc": "2.0",
                "method": "tasks/send",
                "params": {"message": {"text": "x" * (70 * 1024)}},
                "id": "oversized",
            },
        )

    async with async_session() as db:
        count = len((await db.execute(select(A2AMessage))).scalars().all())

    assert response.status_code == 413
    assert response.json()["error"]["message"] == "A2A request body too large."
    assert count == 0


@pytest.mark.asyncio
async def test_agent_card_requires_authentication_in_team_mode_by_default():
    await init_db()
    settings.team_mode = True
    settings.a2a_agent_card_auth_required_team_mode = True
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    token = create_token("researcher-a2a", "researcher", "researcher")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        denied = await ac.get("/.well-known/agent.json")
        allowed = await ac.get(
            "/.well-known/agent.json",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert denied.status_code == 401
    assert allowed.status_code == 200
    assert allowed.json()["name"] == "Istara"


@pytest.mark.asyncio
async def test_a2a_tasks_send_rejects_exact_replay_and_preserves_single_message():
    await init_db()
    await _clear_a2a_messages()
    settings.team_mode = True
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    token = create_token("researcher-a2a", "researcher", "researcher")
    project_id = await _seed_a2a_project()
    payload = {
        "jsonrpc": "2.0",
        "method": "tasks/send",
        "params": {"message": {"text": "Only persist once", "metadata": {"project_id": project_id}}},
        "id": "replay-me",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        first = await ac.post("/a2a", headers={"Authorization": f"Bearer {token}"}, json=payload)
        second = await ac.post("/a2a", headers={"Authorization": f"Bearer {token}"}, json=payload)

    async with async_session() as db:
        stored = (
            (await db.execute(select(A2AMessage).where(A2AMessage.content == "Only persist once")))
            .scalars()
            .all()
        )
        audit_events = (
            (
                await db.execute(
                    select(AuditLog).where(AuditLog.event_type == "a2a.tasks_send.accepted")
                )
            )
            .scalars()
            .all()
        )

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["error"]["message"] == "A2A replay detected."
    assert len(stored) == 1
    assert audit_events


@pytest.mark.asyncio
async def test_a2a_tasks_send_has_dedicated_rate_limit():
    await init_db()
    await _clear_a2a_messages()
    settings.team_mode = True
    settings.a2a_tasks_send_rate_limit_per_minute = 1
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    token = create_token("researcher-a2a", "researcher", "researcher")
    project_id = await _seed_a2a_project()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        first = await ac.post(
            "/a2a",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "jsonrpc": "2.0",
                "method": "tasks/send",
                "params": {"message": {"text": "first", "metadata": {"project_id": project_id}}},
                "id": "rate-1",
            },
        )
        second = await ac.post(
            "/a2a",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "jsonrpc": "2.0",
                "method": "tasks/send",
                "params": {"message": {"text": "second", "metadata": {"project_id": project_id}}},
                "id": "rate-2",
            },
        )

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["error"]["message"] == "A2A tasks/send rate limit exceeded."


@pytest.mark.asyncio
async def test_a2a_agent_discover_requires_authorized_project_scope():
    """A2A discovery must not expose project agents as a global catalog."""
    await init_db()
    settings.team_mode = True
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    token = create_token("researcher-a2a", "researcher", "researcher")
    project_id = await _seed_a2a_project()
    hidden_project_id = await _seed_a2a_project(user_id=f"other-{uuid.uuid4()}")
    visible_agent_id = f"visible-agent-{uuid.uuid4()}"
    hidden_agent_id = f"hidden-agent-{uuid.uuid4()}"
    universal_agent_id = f"universal-agent-{uuid.uuid4()}"

    async with async_session() as db:
        db.add_all(
            [
                Agent(
                    id=visible_agent_id,
                    name="Visible project agent",
                    scope="project",
                    project_id=project_id,
                    current_task="visible work",
                    memory='{"note":"visible"}',
                ),
                Agent(
                    id=hidden_agent_id,
                    name="Hidden project agent",
                    scope="project",
                    project_id=hidden_project_id,
                    current_task="hidden work",
                    memory='{"note":"hidden"}',
                ),
                Agent(
                    id=universal_agent_id,
                    name="Universal support agent",
                    scope="universal",
                    project_id="",
                    current_task="system diagnostics",
                    memory='{"note":"system"}',
                ),
            ]
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        missing_scope = await ac.post(
            "/a2a",
            headers={"Authorization": f"Bearer {token}"},
            json={"jsonrpc": "2.0", "method": "agent/discover", "params": {}, "id": "discover-missing"},
        )
        hidden_scope = await ac.post(
            "/a2a",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "jsonrpc": "2.0",
                "method": "agent/discover",
                "params": {"project_id": hidden_project_id},
                "id": "discover-hidden",
            },
        )
        visible_scope = await ac.post(
            "/a2a",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "jsonrpc": "2.0",
                "method": "agent/discover",
                "params": {"project_id": project_id},
                "id": "discover-visible",
            },
        )

    assert missing_scope.status_code == 400
    assert missing_scope.json()["error"]["message"] == "project_id is required for A2A agent/discover."
    assert hidden_scope.status_code == 404

    assert visible_scope.status_code == 200
    agents = visible_scope.json()["result"]["agents"]
    by_id = {agent["id"]: agent for agent in agents}
    assert visible_agent_id in by_id
    assert universal_agent_id in by_id
    assert hidden_agent_id not in by_id
    assert by_id[universal_agent_id]["current_task"] == ""
    assert by_id[universal_agent_id]["memory"] == {}
