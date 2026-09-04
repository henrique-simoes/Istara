"""Tests for Context DAG API routes — structure, health, expand, grep, node, compact."""

import asyncio
import json
import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.models.context_dag import ContextDAGNode
from app.models.database import async_session, init_db
from app.models.message import Message
from app.models.project import Project
from app.models.session import ChatSession
from app.core.auth import create_token
from app.core.context_dag import context_dag


@pytest.fixture(autouse=True)
def reset_settings():
    original_team_mode = settings.team_mode
    original_jwt_secret = settings.jwt_secret
    yield
    settings.team_mode = original_team_mode
    settings.jwt_secret = original_jwt_secret


@pytest.fixture
def auth_headers():
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    token = create_token("user1", "testuser", "admin")
    return {"Authorization": f"Bearer {token}"}


async def _seed_session_with_dag() -> tuple[Project, ChatSession, Message, ContextDAGNode]:
    now = datetime.now(timezone.utc)
    project = Project(id=str(uuid.uuid4()), name=f"DAG {uuid.uuid4()}")
    session = ChatSession(
        id=str(uuid.uuid4()),
        project_id=project.id,
        title="DAG session",
    )
    message = Message(
        id=str(uuid.uuid4()),
        project_id=project.id,
        session_id=session.id,
        role="user",
        content="The participant mentioned pricing friction.",
        created_at=now,
    )
    node = ContextDAGNode(
        id=str(uuid.uuid4()),
        session_id=session.id,
        depth=0,
        summary_text="Pricing friction discussion",
        message_ids=json.dumps([message.id]),
        child_node_ids="[]",
        token_count=12,
        original_token_count=48,
        message_count=1,
        time_range_start=now,
        time_range_end=now,
    )
    async with async_session() as db:
        db.add_all([project, session, message, node])
        await db.commit()
        await db.refresh(project)
        await db.refresh(session)
        await db.refresh(message)
        await db.refresh(node)
    return project, session, message, node


@pytest.mark.asyncio
async def test_context_dag_structure_requires_active_project_id(auth_headers):
    """GET /api/context-dag/{session_id} requires the caller's active project id."""
    await init_db()
    project, session, _, _ = await _seed_session_with_dag()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        missing_project = await ac.get(f"/api/context-dag/{session.id}", headers=auth_headers)
        unknown_session = await ac.get(
            "/api/context-dag/test-session",
            headers=auth_headers,
            params={"project_id": project.id},
        )

    assert missing_project.status_code == 400
    assert missing_project.json()["detail"] == "project_id is required"
    assert unknown_session.status_code == 404


@pytest.mark.asyncio
async def test_context_dag_requires_auth():
    """Context DAG requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            "/api/context-dag/test-session",
            params={"project_id": "test-project"},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_context_dag_health_returns_response(auth_headers):
    """GET /api/context-dag/{session_id}/health returns health info."""
    await init_db()
    project = Project(id=str(uuid.uuid4()), name=f"DAG {uuid.uuid4()}")
    async with async_session() as db:
        db.add(project)
        await db.commit()
        await db.refresh(project)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            "/api/context-dag/test-session/health",
            headers=auth_headers,
            params={"project_id": project.id},
        )
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_context_dag_structure_matches_frontend_contract(auth_headers):
    await init_db()
    project, session, _, node = await _seed_session_with_dag()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/context-dag/{session.id}",
            headers=auth_headers,
            params={"project_id": project.id},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["stats"]["dag_enabled"] == settings.dag_enabled
    assert payload["stats"]["max_depth"] == 0
    assert payload["nodes"][0]["id"] == node.id
    assert payload["nodes"][0]["summary_text"] == "Pricing friction discussion"
    assert payload["nodes"][0]["child_node_ids"] == []


@pytest.mark.asyncio
async def test_context_dag_expand_returns_normalized_items(auth_headers):
    await init_db()
    project, session, message, node = await _seed_session_with_dag()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            f"/api/context-dag/{session.id}/expand",
            headers=auth_headers,
            params={"project_id": project.id},
            json={"node_id": node.id},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["depth"] == 0
    assert payload["items"][0]["id"] == message.id
    assert payload["items"][0]["type"] == "message"
    assert payload["items"][0]["content"] == message.content


@pytest.mark.asyncio
async def test_context_dag_node_access_is_scoped_to_requested_session(auth_headers):
    await init_db()
    visible_project, visible_session, _, _ = await _seed_session_with_dag()
    _, hidden_session, _, hidden_node = await _seed_session_with_dag()
    assert visible_session.id != hidden_session.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        expand_response = await ac.post(
            f"/api/context-dag/{visible_session.id}/expand",
            headers=auth_headers,
            params={"project_id": visible_project.id},
            json={"node_id": hidden_node.id},
        )
        details_response = await ac.get(
            f"/api/context-dag/{visible_session.id}/node/{hidden_node.id}",
            headers=auth_headers,
            params={"project_id": visible_project.id},
        )

    assert expand_response.status_code == 404
    assert details_response.status_code == 404


@pytest.mark.asyncio
async def test_context_dag_rejects_stale_cross_project_session_id(auth_headers):
    """The active project id must match the requested session's project."""
    await init_db()
    active_project, _, _, _ = await _seed_session_with_dag()
    _, hidden_session, _, hidden_node = await _seed_session_with_dag()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        structure_response = await ac.get(
            f"/api/context-dag/{hidden_session.id}",
            headers=auth_headers,
            params={"project_id": active_project.id},
        )
        node_response = await ac.get(
            f"/api/context-dag/{hidden_session.id}/node/{hidden_node.id}",
            headers=auth_headers,
            params={"project_id": active_project.id},
        )

    assert structure_response.status_code == 404
    assert node_response.status_code == 404


@pytest.mark.asyncio
async def test_context_dag_compaction_tasks_are_deduplicated_and_drained(monkeypatch):
    """Background compaction must be owned by the DAG lifecycle."""
    started = asyncio.Event()
    release = asyncio.Event()

    async def fake_compact(session_id: str) -> None:
        started.set()
        await release.wait()

    monkeypatch.setattr(context_dag, "compact_if_needed", fake_compact)

    first = context_dag.schedule_compaction("session-1")
    await started.wait()
    assert context_dag.schedule_compaction("session-1") is first

    release.set()
    await context_dag.drain_compaction_tasks()
    assert not context_dag._compaction_tasks
