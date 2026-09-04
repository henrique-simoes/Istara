"""Tests for Sessions API routes — CRUD, star, presets, ensure-default."""

import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.models.database import async_session, init_db
from app.core.auth import create_token
from app.models.agent import Agent
from app.models.project import Project
from app.models.session import ChatSession
from app.models.message import Message


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


async def _seed_project() -> Project:
    project = Project(id=str(uuid.uuid4()), name=f"Sessions {uuid.uuid4()}")
    async with async_session() as db:
        db.add(project)
        await db.commit()
        await db.refresh(project)
    return project


async def _seed_session(project_id: str, title: str = "Scoped session") -> ChatSession:
    session = ChatSession(id=str(uuid.uuid4()), project_id=project_id, title=title)
    async with async_session() as db:
        db.add(session)
        await db.commit()
        await db.refresh(session)
    return session


async def _seed_message(
    project_id: str, session_id: str, content: str = "hello"
) -> Message:
    message = Message(
        id=str(uuid.uuid4()),
        project_id=project_id,
        session_id=session_id,
        role="user",
        content=content,
    )
    async with async_session() as db:
        db.add(message)
        await db.commit()
        await db.refresh(message)
    return message


async def _seed_agent(
    agent_id: str,
    *,
    project_id: str = "",
    scope: str = "universal",
    is_active: bool = True,
) -> Agent:
    agent = Agent(
        id=agent_id,
        name=f"Agent {agent_id}",
        system_prompt=f"Prompt for {agent_id}",
        scope=scope,
        project_id=project_id,
        is_active=is_active,
    )
    async with async_session() as db:
        db.add(agent)
        await db.commit()
        await db.refresh(agent)
    return agent


@pytest.mark.asyncio
async def test_sessions_list_returns_list(auth_headers):
    """GET /api/sessions/{project_id} returns a list."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/sessions/test-project", headers=auth_headers)
        assert response.status_code in (200, 404)
        if response.status_code == 200:
            assert isinstance(response.json(), dict)


@pytest.mark.asyncio
async def test_sessions_list_requires_auth():
    """Sessions listing requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/sessions/test-project")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_session_get_nonexistent_returns_404(auth_headers):
    """GET /api/sessions/detail/{id} returns 404 for non-existent session."""
    await init_db()
    project = await _seed_project()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/sessions/detail/non-existent-id?project_id={project.id}",
            headers=auth_headers,
        )
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_session_detail_requires_active_project_id(auth_headers):
    """Session detail requires the caller's active project id."""
    await init_db()
    project = await _seed_project()
    session = await _seed_session(project.id)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/sessions/detail/{session.id}", headers=auth_headers
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "project_id is required"


@pytest.mark.asyncio
async def test_session_detail_rejects_cross_project_active_scope(auth_headers):
    """An active project id cannot retrieve another project's session/messages."""
    await init_db()
    project_a = await _seed_project()
    project_b = await _seed_project()
    session = await _seed_session(project_a.id, title="Project A chat")
    await _seed_message(project_a.id, session.id, content="project A only")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        wrong_project = await ac.get(
            f"/api/sessions/detail/{session.id}?project_id={project_b.id}",
            headers=auth_headers,
        )
        right_project = await ac.get(
            f"/api/sessions/detail/{session.id}?project_id={project_a.id}",
            headers=auth_headers,
        )

    assert wrong_project.status_code == 404
    assert right_project.status_code == 200
    assert right_project.json()["project_id"] == project_a.id
    assert [m["content"] for m in right_project.json()["messages"]] == [
        "project A only"
    ]


@pytest.mark.asyncio
async def test_create_session_rejects_invalid_inference_preset(auth_headers):
    await init_db()
    project = await _seed_project()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/sessions",
            headers=auth_headers,
            json={
                "project_id": project.id,
                "title": "Invalid preset",
                "inference_preset": "turbo-chaos",
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_session_model_override_rejects_embedding_only_models(auth_headers):
    """Embedding transports cannot be persisted as chat session overrides."""
    await init_db()
    project = await _seed_project()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        create_response = await ac.post(
            "/api/sessions",
            headers=auth_headers,
            json={
                "project_id": project.id,
                "title": "Embedding override",
                "model_override": "istara-qa-contract-embed:latest",
            },
        )
        valid_create = await ac.post(
            "/api/sessions",
            headers=auth_headers,
            json={
                "project_id": project.id,
                "title": "Valid override",
                "model_override": "qwen3:7b",
            },
        )
        update_response = await ac.patch(
            f"/api/sessions/{valid_create.json()['id']}?project_id={project.id}",
            headers=auth_headers,
            json={"model_override": "nomic-embed-text:latest"},
        )

    assert create_response.status_code == 422
    assert valid_create.status_code == 201
    assert update_response.status_code == 422


@pytest.mark.asyncio
async def test_session_title_is_normalized_on_create(auth_headers):
    await init_db()
    project = await _seed_project()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/sessions",
            headers=auth_headers,
            json={"project_id": project.id, "title": "  Trimmed title  "},
        )

    assert response.status_code == 201
    assert response.json()["title"] == "Trimmed title"


@pytest.mark.asyncio
async def test_create_session_rejects_cross_project_agent(auth_headers):
    """Session creation cannot attach a project agent from another project."""
    await init_db()
    project_a = await _seed_project()
    project_b = await _seed_project()
    owned_agent = await _seed_agent(
        f"owned-agent-{uuid.uuid4()}",
        project_id=project_a.id,
        scope="project",
    )
    hidden_agent = await _seed_agent(
        f"hidden-agent-{uuid.uuid4()}",
        project_id=project_b.id,
        scope="project",
    )
    universal_agent = await _seed_agent(f"universal-agent-{uuid.uuid4()}")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        hidden_response = await ac.post(
            "/api/sessions",
            headers=auth_headers,
            json={
                "project_id": project_a.id,
                "title": "Wrong agent",
                "agent_id": hidden_agent.id,
            },
        )
        owned_response = await ac.post(
            "/api/sessions",
            headers=auth_headers,
            json={
                "project_id": project_a.id,
                "title": "Owned agent",
                "agent_id": owned_agent.id,
            },
        )
        universal_response = await ac.post(
            "/api/sessions",
            headers=auth_headers,
            json={
                "project_id": project_a.id,
                "title": "Universal agent",
                "agent_id": universal_agent.id,
            },
        )

    assert hidden_response.status_code == 404
    assert hidden_response.json()["detail"] == "Agent not found"
    assert owned_response.status_code == 201
    assert owned_response.json()["agent_id"] == owned_agent.id
    assert universal_response.status_code == 201
    assert universal_response.json()["agent_id"] == universal_agent.id


@pytest.mark.asyncio
async def test_update_session_rejects_unbounded_custom_settings(auth_headers):
    await init_db()
    project = await _seed_project()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        create_response = await ac.post(
            "/api/sessions",
            headers=auth_headers,
            json={"project_id": project.id, "title": "Custom settings"},
        )
        session_id = create_response.json()["id"]
        update_response = await ac.patch(
            f"/api/sessions/{session_id}?project_id={project.id}",
            headers=auth_headers,
            json={"custom_temperature": 8, "custom_max_tokens": 0},
        )

    assert create_response.status_code == 201
    assert update_response.status_code == 422


@pytest.mark.asyncio
async def test_update_session_agent_assignment_is_bound_to_active_project(auth_headers):
    """Session updates reject stale cross-project agent ids and allow clearing."""
    await init_db()
    project_a = await _seed_project()
    project_b = await _seed_project()
    session = await _seed_session(project_a.id, title="Project A chat")
    owned_agent = await _seed_agent(
        f"owned-update-agent-{uuid.uuid4()}",
        project_id=project_a.id,
        scope="project",
    )
    hidden_agent = await _seed_agent(
        f"hidden-update-agent-{uuid.uuid4()}",
        project_id=project_b.id,
        scope="project",
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        wrong_scope = await ac.patch(
            f"/api/sessions/{session.id}?project_id={project_a.id}",
            headers=auth_headers,
            json={"agent_id": hidden_agent.id},
        )
        owned = await ac.patch(
            f"/api/sessions/{session.id}?project_id={project_a.id}",
            headers=auth_headers,
            json={"agent_id": owned_agent.id},
        )
        cleared = await ac.patch(
            f"/api/sessions/{session.id}?project_id={project_a.id}",
            headers=auth_headers,
            json={"agent_id": None},
        )

    assert wrong_scope.status_code == 404
    assert wrong_scope.json()["detail"] == "Agent not found"
    assert owned.status_code == 200
    assert owned.json()["agent_id"] == owned_agent.id
    assert cleared.status_code == 200
    assert cleared.json()["agent_id"] is None


@pytest.mark.asyncio
async def test_session_thinking_mode_round_trips(auth_headers):
    await init_db()
    project = await _seed_project()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        create_response = await ac.post(
            "/api/sessions",
            headers=auth_headers,
            json={
                "project_id": project.id,
                "title": "Thinking",
                "thinking_mode": "off",
            },
        )
        session_id = create_response.json()["id"]
        update_response = await ac.patch(
            f"/api/sessions/{session_id}?project_id={project.id}",
            headers=auth_headers,
            json={"thinking_mode": "on"},
        )
        invalid_response = await ac.patch(
            f"/api/sessions/{session_id}?project_id={project.id}",
            headers=auth_headers,
            json={"thinking_mode": "show_raw_thoughts"},
        )

    assert create_response.status_code == 201
    assert create_response.json()["thinking_mode"] == "off"
    assert update_response.status_code == 200
    assert update_response.json()["thinking_mode"] == "on"
    assert invalid_response.status_code == 422


@pytest.mark.asyncio
async def test_session_mutations_require_active_project_id(auth_headers):
    """Session mutation endpoints reject session-id-only calls."""
    await init_db()
    project = await _seed_project()
    session = await _seed_session(project.id)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        patch_response = await ac.patch(
            f"/api/sessions/{session.id}",
            headers=auth_headers,
            json={"title": "No active project"},
        )
        star_response = await ac.post(
            f"/api/sessions/{session.id}/star", headers=auth_headers
        )
        delete_response = await ac.delete(
            f"/api/sessions/{session.id}", headers=auth_headers
        )

    assert patch_response.status_code == 400
    assert star_response.status_code == 400
    assert delete_response.status_code == 400


@pytest.mark.asyncio
async def test_session_mutations_reject_cross_project_active_scope(auth_headers):
    """A stale session id from project A cannot be changed while project B is active."""
    await init_db()
    project_a = await _seed_project()
    project_b = await _seed_project()
    session = await _seed_session(project_a.id, title="Project A chat")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        patch_response = await ac.patch(
            f"/api/sessions/{session.id}?project_id={project_b.id}",
            headers=auth_headers,
            json={"title": "Cross-project edit"},
        )
        star_response = await ac.post(
            f"/api/sessions/{session.id}/star?project_id={project_b.id}",
            headers=auth_headers,
        )
        delete_response = await ac.delete(
            f"/api/sessions/{session.id}?project_id={project_b.id}",
            headers=auth_headers,
        )
        detail_response = await ac.get(
            f"/api/sessions/detail/{session.id}?project_id={project_a.id}",
            headers=auth_headers,
        )

    assert patch_response.status_code == 404
    assert star_response.status_code == 404
    assert delete_response.status_code == 404
    assert detail_response.status_code == 200
    assert detail_response.json()["title"] == "Project A chat"
    assert detail_response.json()["starred"] is False
