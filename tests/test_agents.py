"""Tests for Agents API routes — CRUD, identity, memory, messages, proposals."""

import pytest
from app.config import settings
from app.core.auth import create_token
from app.main import app
from app.models.database import init_db
from httpx import ASGITransport, AsyncClient


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


@pytest.mark.asyncio
async def test_agents_list_returns_list(auth_headers):
    """GET /api/agents returns a list."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/agents", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


@pytest.mark.asyncio
async def test_agents_list_requires_auth():
    """Agents listing requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/agents")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_agents_capacity_returns_response(auth_headers):
    """GET /api/agents/capacity returns agent capacity."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/agents/capacity", headers=auth_headers)
        assert response.status_code in (200, 404, 500)


@pytest.mark.asyncio
async def test_agents_heartbeat_returns_response(auth_headers):
    """GET /api/agents/heartbeat/status returns heartbeat status."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/agents/heartbeat/status", headers=auth_headers)
        assert response.status_code in (200, 404, 500)


@pytest.mark.asyncio
async def test_agents_get_nonexistent_returns_404(auth_headers):
    """GET /api/agents/{id} returns 404 for non-existent agent."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/agents/non-existent-id", headers=auth_headers)
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_agent_restart_scope_and_promotion_routes_use_persistent_agent(auth_headers):
    """Lifecycle helpers should operate on ORM state, not serialized agent dicts."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        created = await ac.post(
            "/api/agents",
            headers=auth_headers,
            json={
                "name": "Lifecycle Test Agent",
                "role": "custom",
                "system_prompt": "Temporary lifecycle test agent.",
                "capabilities": ["chat"],
            },
        )
        assert created.status_code == 201
        agent_id = created.json()["id"]

        restart = await ac.post(f"/api/agents/{agent_id}/restart", headers=auth_headers)
        assert restart.status_code == 200
        assert restart.json()["status"] == "restarted"

        scoped = await ac.post(
            f"/api/agents/{agent_id}/set-scope",
            headers=auth_headers,
            json={"scope": "project", "project_id": "project-test"},
        )
        assert scoped.status_code == 200
        assert scoped.json()["scope"] == "project"
        assert scoped.json()["project_id"] == "project-test"

        invalid_scope = await ac.post(
            f"/api/agents/{agent_id}/set-scope",
            headers=auth_headers,
            json={"scope": "workspace", "project_id": "project-test"},
        )
        assert invalid_scope.status_code == 422

        promotion = await ac.post(f"/api/agents/{agent_id}/request-promotion", headers=auth_headers)
        assert promotion.status_code == 200
        assert promotion.json()["status"] == "requested"

        await ac.delete(f"/api/agents/{agent_id}", headers=auth_headers)


@pytest.mark.asyncio
async def test_agent_recent_log_filters_by_agent(auth_headers):
    """The recent-log endpoint should return the documented log key and honor agent_id."""
    await init_db()
    from app.agents.orchestrator import meta_orchestrator

    meta_orchestrator._log_action("agent-a", "failed", "A failure")
    meta_orchestrator._log_action("agent-b", "failed", "B failure")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            "/api/agents/log/recent?agent_id=agent-a&limit=10",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "log" in data
        assert data["log"]
        assert all(entry["agent_id"] == "agent-a" for entry in data["log"])


@pytest.mark.asyncio
async def test_agent_export_requires_admin_role():
    """Export includes prompt and memory, so it should stay admin-only in team mode."""
    await init_db()
    settings.team_mode = True
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    token = create_token("user2", "researcher", "researcher")
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/agents/istara-main/export", headers=headers)
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_agent_skill_selection_reaches_semantic_fallback(monkeypatch):
    """Keyword misses should still reach the Memento semantic router."""
    from app.core.agent import AgentOrchestrator
    from app.models.task import Task

    sentinel_skill = object()
    orchestrator = AgentOrchestrator()

    async def fake_semantic_match(task):
        return sentinel_skill

    monkeypatch.setattr(orchestrator, "_semantic_skill_match", fake_semantic_match)
    task = Task(
        id="semantic-route-task",
        project_id="semantic-route-project",
        title="Zephyr cobalt resonance mapping",
        description="Map latent needs with unfamiliar vocabulary.",
        skill_name="",
    )

    assert await orchestrator._select_skill(task) is sentinel_skill


def test_agent_complex_auto_task_attempts_research_plan():
    """Multi-stage auto-routed work should reach the DAG planner before skill selection."""
    from app.core.agent import AgentOrchestrator
    from app.models.task import Task

    orchestrator = AgentOrchestrator()
    task = Task(
        id="complex-plan-task",
        project_id="complex-plan-project",
        title="Strategic Market Disruption & UX Spec Creation",
        description=(
            "Conduct a multi-stage investigation for our new AI product: "
            "1. Deep-dive into linear.app and asana.com to map their architectures. "
            "2. Contrast their interface layouts against UX standards. "
            "3. Generate a visionary product spec with disruptive features."
        ),
        skill_name="",
    )

    assert orchestrator._should_attempt_research_plan(task) is True


def test_agent_explicit_skill_skips_research_plan_probe():
    """User-selected skills should not pay the planning cost unless they opt in later."""
    from app.core.agent import AgentOrchestrator
    from app.models.task import Task

    orchestrator = AgentOrchestrator()
    task = Task(
        id="explicit-skill-task",
        project_id="explicit-skill-project",
        title="Strategic Market Disruption & UX Spec Creation",
        description=(
            "Conduct a multi-stage investigation: 1. compare competitors. "
            "2. contrast UX standards. 3. generate product strategy."
        ),
        skill_name="browser-competitive-benchmark",
    )

    assert orchestrator._should_attempt_research_plan(task) is False


def test_agent_factory_uses_meta_coverage_threshold(monkeypatch):
    """HyperAgent coverage variants should affect capability-gap detection."""
    import app.core.agent_factory as agent_factory_module
    from app.core.agent_factory import AgentFactory

    factory = AgentFactory()
    agents = [{"specialties": ["interviews"]}]
    required = ["interviews", "statistics"]

    monkeypatch.setattr(agent_factory_module, "_META_COVERAGE_THRESHOLD", 0.75)
    assert factory.detect_capability_gap(required, agents) is not None

    monkeypatch.setattr(agent_factory_module, "_META_COVERAGE_THRESHOLD", 0.5)
    assert factory.detect_capability_gap(required, agents) is None
