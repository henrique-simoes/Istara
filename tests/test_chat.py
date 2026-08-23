"""Tests for Chat API routes — POST /api/chat and GET /api/chat/history."""

import pytest
import uuid
from pydantic import ValidationError
from sqlalchemy import select
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.api.routes.chat import ChatRequest
from app.config import settings
from app.models.agent import Agent
from app.models.database import async_session, init_db
from app.models.project import Project
from app.models.session import ChatSession
from app.core.auth import create_token


@pytest.fixture(autouse=True)
def reset_settings():
    """Reset settings after each test."""
    original_team_mode = settings.team_mode
    original_jwt_secret = settings.jwt_secret
    yield
    settings.team_mode = original_team_mode
    settings.jwt_secret = original_jwt_secret


@pytest.mark.asyncio
async def test_chat_history_returns_messages():
    """GET /api/chat/history/{project_id} returns messages for a project."""
    await init_db()
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    token = create_token("user1", "testuser", "admin")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            "/api/chat/history/test-project-123",
            headers={"Authorization": f"Bearer {token}"},
        )
        # Should return 200 even if no messages exist
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_chat_history_requires_auth():
    """GET /api/chat/history requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/chat/history/some-project")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_chat_rejects_without_auth():
    """POST /api/chat requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/chat",
            json={"message": "hello", "project_id": "test-project"},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_chat_rejects_missing_project():
    """POST /api/chat returns 404 for non-existent project."""
    await init_db()
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    token = create_token("user1", "testuser", "admin")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/chat",
            json={"message": "hello", "project_id": "non-existent-project-xyz"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_chat_requires_message_field():
    """POST /api/chat validates required message field."""
    await init_db()
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    token = create_token("user1", "testuser", "admin")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Missing message field — Pydantic validation error
        response = await ac.post(
            "/api/chat",
            json={"project_id": "some-project"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_requires_project_id_field():
    """POST /api/chat validates required project_id field."""
    await init_db()
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    token = create_token("user1", "testuser", "admin")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/chat",
            json={"message": "hello"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_rejects_blank_message_before_project_lookup():
    """POST /api/chat rejects blank messages at the request contract."""
    await init_db()
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    token = create_token("user1", "testuser", "admin")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/chat",
            json={"message": "   ", "project_id": "some-project"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_rejects_session_with_cross_project_agent_before_llm():
    """Chat must not compose prompts from a session's stale foreign agent id."""
    await init_db()
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    token = create_token("user1", "testuser", "admin")
    project_id = str(uuid.uuid4())
    hidden_project_id = str(uuid.uuid4())
    hidden_agent_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    async with async_session() as db:
        db.add_all(
            [
                Project(id=project_id, name="Chat Agent Project A"),
                Project(id=hidden_project_id, name="Chat Agent Project B"),
                Agent(
                    id=hidden_agent_id,
                    name="Hidden Agent",
                    system_prompt="Hidden prompt should never be loaded",
                    scope="project",
                    project_id=hidden_project_id,
                ),
                ChatSession(
                    id=session_id,
                    project_id=project_id,
                    title="Stale hidden agent session",
                    agent_id=hidden_agent_id,
                ),
            ]
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/chat",
            json={
                "message": "hello",
                "project_id": project_id,
                "session_id": session_id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Agent not found"


def test_chat_request_preserves_provider_native_effort_levels():
    request = ChatRequest.model_validate(
        {"message": "hello", "project_id": "project-1", "thinking_mode": "xhigh"}
    )

    assert request.thinking_mode == "xhigh"


@pytest.mark.asyncio
async def test_chat_model_catalog_and_usage_are_project_scoped():
    await init_db()
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    token = create_token("user1", "testuser", "admin")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        catalog = await ac.get(
            "/api/chat/model-catalog?project_id=test-project-123",
            headers={"Authorization": f"Bearer {token}"},
        )
        usage = await ac.get(
            "/api/chat/usage/test-project-123",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert catalog.status_code == 200
    assert catalog.json()["total_models"] > 1000
    assert usage.status_code == 200
    assert usage.json()["total_tokens"] == 0


@pytest.mark.asyncio
async def test_chat_blocked_when_provider_is_contract_stub(monkeypatch):
    """Interactive legacy chat fails closed when ONLY a stub plane exists.

    The QA contract stack and connectivity-acceptance stacks set
    LLM_PROVIDER_CONTRACT_STUB=true; POST /api/chat must then return an
    actionable SSE error before any session/message side effect instead of
    streaming canned qa-contract-response text (CF-SPEC-1 ITEM-002, Phase 6
    refinement: a configured non-stub source exempts the deployment).
    monkeypatching the pi plane empty makes "no non-stub source" deterministic
    even on machines whose keychain can resolve the default endpoint.
    """
    from tests.test_model_source import _FakeManager
    from app.core.agentic import model_source as _ms

    monkeypatch.setattr(_ms, "_pi_manager", lambda: _FakeManager([]))

    await init_db()
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    token = create_token("user1", "testuser", "admin")
    project_id = str(uuid.uuid4())
    async with async_session() as db:
        db.add(Project(id=project_id, name="Stub Provider Project"))
        await db.commit()

    original_stub = settings.llm_provider_contract_stub
    settings.llm_provider_contract_stub = True
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                "/api/chat",
                json={"message": "hello", "project_id": project_id},
                headers={"Authorization": f"Bearer {token}"},
            )
    finally:
        settings.llm_provider_contract_stub = original_stub

    assert response.status_code == 200
    assert "provider_stub_chat_blocked" in response.text
    assert "qa-contract-response" not in response.text

    # Fail-closed means fail BEFORE side effects: no session or message rows.
    from app.models.message import Message as _Message
    from app.models.session import ChatSession as _ChatSession

    async with async_session() as verify_db:
        sessions = (
            await verify_db.execute(
                select(_ChatSession).where(_ChatSession.project_id == project_id)
            )
        ).scalars().all()
        messages = (
            await verify_db.execute(
                select(_Message).where(_Message.project_id == project_id)
            )
        ).scalars().all()
    assert sessions == []
    assert messages == []


@pytest.mark.asyncio
async def test_chat_stub_guard_exempts_pi_engine():
    """On a stub-marked plane, a Pi-selected turn is NOT stub-blocked.

    The guard exists for the legacy (local Ollama-compatible) plane only;
    Pi turns go to configured cloud endpoints, so they must pass through
    (CF-SPEC-1 ITEM-002, refined during Mac Studio deploy smoke).
    """
    from app.api.routes.chat import _resolve_chat_engine

    await init_db()
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    token = create_token("user1", "testuser", "admin")
    project_id = str(uuid.uuid4())
    async with async_session() as db:
        db.add(Project(id=project_id, name="Stub Exempt Pi Project"))
        await db.commit()

    original_stub = settings.llm_provider_contract_stub
    original_flag = settings.pi_replacement_enabled
    settings.llm_provider_contract_stub = True
    settings.pi_replacement_enabled = False
    try:
        # Header selects pi -> resolution returns pi -> route must not block.
        resolved = await _resolve_chat_engine(
            _engine_request_stub({"x-istara-agent-engine": "pi"}), project_id, _engine_db_stub(None)
        )
        assert resolved == "pi"
        assert not (original_stub and resolved != "pi")

        transport = ASGITransport(app=app)
        settings_copy = settings
        settings_copy.llm_provider_contract_stub = True
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                "/api/chat",
                json={"message": "hello", "project_id": project_id},
                headers={"Authorization": f"Bearer {token}", "x-istara-agent-engine": "pi"},
            )
        assert response.status_code == 200
        assert "provider_stub_chat_blocked" not in response.text
    finally:
        settings.llm_provider_contract_stub = original_stub
        settings.pi_replacement_enabled = original_flag


def _engine_db_stub(project_value):
    class _StubDb:
        def __init__(self):
            self.scalar_calls = 0

        async def scalar(self, _stmt):
            self.scalar_calls += 1
            return project_value

    return _StubDb()


def _engine_request_stub(headers=None):
    class _StubRequest:
        def __init__(self):
            self.headers = headers or {}

    return _StubRequest()


@pytest.mark.asyncio
async def test_resolve_chat_engine_precedence():
    """Chat engine resolution: operator flag > header > project > global default.

    Locks CF-SPEC-1 ITEM-001 so the UI's Agentic Core selection actually
    routes the turn and per-request overrides stay dispatcher-compatible.
    """
    from app.api.routes.chat import _resolve_chat_engine

    original_flag = settings.pi_replacement_enabled
    original_default = settings.agentic_engine_default
    try:
        settings.pi_replacement_enabled = True
        db = _engine_db_stub("legacy")
        assert (
            await _resolve_chat_engine(
                _engine_request_stub({"x-istara-agent-engine": "legacy"}), "p1", db
            )
            == "pi"
        )
        assert db.scalar_calls == 0
        settings.pi_replacement_enabled = False

        db = _engine_db_stub("legacy")
        assert (
            await _resolve_chat_engine(
                _engine_request_stub({"x-istara-agent-engine": "PI-candidate"}), "p1", db
            )
            == "pi"
        )
        assert db.scalar_calls == 0

        db = _engine_db_stub("pi")
        assert (
            await _resolve_chat_engine(
                _engine_request_stub({"x-istara-agent-engine": "not-an-engine"}), "p1", db
            )
            == "legacy"
        )
        assert db.scalar_calls == 0

        db = _engine_db_stub("pi")
        assert await _resolve_chat_engine(_engine_request_stub(), "p1", db) == "pi"
        assert db.scalar_calls == 1

        settings.agentic_engine_default = "pi"
        assert await _resolve_chat_engine(_engine_request_stub(), "p1", _engine_db_stub(None)) == "pi"

        settings.agentic_engine_default = "legacy"
        assert await _resolve_chat_engine(_engine_request_stub(), "p1", _engine_db_stub("")) == "legacy"
    finally:
        settings.pi_replacement_enabled = original_flag
        settings.agentic_engine_default = original_default
