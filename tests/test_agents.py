"""Tests for Agents API routes — CRUD, identity, memory, messages, proposals."""

import json
import uuid

import pytest
from sqlalchemy import delete

from app.config import settings
from app.core.auth import create_token
from app.main import app
from app.models.agent import A2AMessage
from app.models.database import async_session, init_db
from httpx import ASGITransport, AsyncClient
from types import SimpleNamespace


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
async def test_agents_capacity_reports_real_pressure_and_ram(monkeypatch):
    from app.services import agent_service

    monkeypatch.setattr(
        agent_service.governor,
        "get_status",
        lambda: {
            "active_agents": 1,
            "budget": {"max_concurrent_agents": 2},
            "pressure": "normal",
        },
    )
    monkeypatch.setattr(
        agent_service,
        "detect_hardware",
        lambda: SimpleNamespace(total_ram_gb=36.0, available_ram_gb=7.4, cpu_cores=14),
    )

    capacity = await agent_service.check_capacity()

    assert capacity["pressure"] == "normal"
    assert capacity["ram_total_gb"] == 36.0
    assert capacity["ram_available_gb"] == 7.4
    assert capacity["can_create"] is True


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
async def test_a2a_accepts_system_message_type_contract(auth_headers):
    """A2A validation should allow message types emitted by Istara scenarios and JSON-RPC."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        created_a = await ac.post(
            "/api/agents",
            headers=auth_headers,
            json={
                "name": "A2A Contract Alpha",
                "role": "custom",
                "system_prompt": "Temporary A2A contract test agent.",
                "capabilities": ["a2a_messaging"],
            },
        )
        created_b = await ac.post(
            "/api/agents",
            headers=auth_headers,
            json={
                "name": "A2A Contract Beta",
                "role": "custom",
                "system_prompt": "Temporary A2A contract test recipient.",
                "capabilities": ["a2a_messaging"],
            },
        )
        assert created_a.status_code == 201
        assert created_b.status_code == 201
        agent_a = created_a.json()["id"]
        agent_b = created_b.json()["id"]

        try:
            for message_type in ("finding", "request", "broadcast", "a2a_task"):
                response = await ac.post(
                    f"/api/agents/{agent_a}/messages",
                    headers=auth_headers,
                    json={
                        "to_agent_id": None if message_type == "broadcast" else agent_b,
                        "message_type": message_type,
                        "content": f"Contract probe for {message_type}",
                        "project_id": "a2a-contract-project",
                    },
                )
                assert response.status_code == 200
                assert response.json()["message_type"] == message_type

            invalid = await ac.post(
                f"/api/agents/{agent_a}/messages",
                headers=auth_headers,
                json={
                    "to_agent_id": agent_b,
                    "message_type": "not_allowed",
                    "content": "Invalid message type should be a client error.",
                    "project_id": "a2a-contract-project",
                },
            )
            assert invalid.status_code == 400
        finally:
            await ac.delete(f"/api/agents/{agent_a}", headers=auth_headers)
            await ac.delete(f"/api/agents/{agent_b}", headers=auth_headers)


@pytest.mark.asyncio
async def test_a2a_log_filters_by_project_id(auth_headers):
    """Project-scoped A2A logs should not include unrelated project or global messages."""
    await init_db()
    project_a = f"cf56-project-a-{uuid.uuid4()}"
    project_b = f"cf56-project-b-{uuid.uuid4()}"
    message_ids = [str(uuid.uuid4()) for _ in range(3)]
    message_a = "CF56 project A A2A message"
    message_b = "CF56 project B A2A message"
    message_global = "CF56 global A2A message"

    async with async_session() as db:
        db.add_all(
            [
                A2AMessage(
                    id=message_ids[0],
                    from_agent_id="agent-a",
                    to_agent_id="agent-b",
                    message_type="a2a_task",
                    content=message_a,
                    extra_data=json.dumps({"project_id": project_a}),
                ),
                A2AMessage(
                    id=message_ids[1],
                    from_agent_id="agent-a",
                    to_agent_id="agent-b",
                    message_type="a2a_task",
                    content=message_b,
                    extra_data=json.dumps({"project_id": project_b}),
                ),
                A2AMessage(
                    id=message_ids[2],
                    from_agent_id="agent-a",
                    to_agent_id="agent-b",
                    message_type="a2a_task",
                    content=message_global,
                    extra_data=json.dumps({}),
                ),
            ]
        )
        await db.commit()

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get(
                f"/api/agents/a2a/log?project_id={project_a}&limit=20",
                headers=auth_headers,
            )
            assert response.status_code == 200
            contents = [message["content"] for message in response.json()["messages"]]
            assert message_a in contents
            assert message_b not in contents
            assert message_global not in contents

            unscoped = await ac.get("/api/agents/a2a/log?limit=20", headers=auth_headers)
            assert unscoped.status_code == 422
    finally:
        async with async_session() as db:
            await db.execute(delete(A2AMessage).where(A2AMessage.id.in_(message_ids)))
            await db.commit()


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


@pytest.mark.asyncio
async def test_agent_research_plan_parses_dag_dependencies(monkeypatch):
    """The planner should preserve ordered steps and dependency edges from LLM JSON."""
    from types import SimpleNamespace

    import app.core.agent_research as agent_research_module
    from app.core.agent import AgentOrchestrator
    from app.models.task import Task

    captured = {}

    async def fake_chat(*_args, **kwargs):
        captured.update(kwargs)
        return {
            "message": {
                "content": (
                    '{"steps": ['
                    '{"id": "step_1", "description": "Analyze transcripts", '
                    '"skill_name": "user-interviews", "depends_on": []}, '
                    '{"id": "step_2", "description": "Synthesize recommendations", '
                    '"skill_name": null, "depends_on": ["step_1"]}'
                    "]}"
                )
            }
        }

    monkeypatch.setattr(agent_research_module.ollama, "chat", fake_chat)

    from app.core.agent_skill_tools import SkillCandidate

    async def fake_rank_skill_candidates(**_kwargs):
        return [
            SkillCandidate(
                name="user-interviews",
                display_name="User Interviews",
                description="Analyze interview transcripts.",
                phase="discover",
                score=1.0,
            )
        ]

    monkeypatch.setattr(
        "app.core.agent_skill_tools.rank_skill_candidates",
        fake_rank_skill_candidates,
    )

    task = Task(
        id="plan-parse-task",
        project_id="plan-parse-project",
        title="Comprehensive UX Analysis",
        description=(
            "Analyze user interview transcripts, identify survey issues, contrast "
            "competitors, and synthesize recommendations."
        ),
        skill_name="",
    )

    plan = await AgentOrchestrator()._create_research_plan(
        task,
        SimpleNamespace(id="plan-parse-project"),
        SimpleNamespace(has_context=False, context_text=""),
    )

    assert plan is not None
    assert captured["response_format"]["type"] == "json_schema"
    assert captured["thinking_mode"] == "off"
    assert [step.id for step in plan.steps] == ["step_1", "step_2"]
    assert plan.steps[1].depends_on == ["step_1"]
    assert plan.steps[0].skill_name == "user-interviews"


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


@pytest.mark.asyncio
async def test_manual_skill_execute_survives_poisoned_storage_session(monkeypatch):
    """A storage transaction failure should not rewrite a good manual skill result."""
    from app.core.agent import AgentOrchestrator
    from app.models.database import async_session
    from app.models.project import Project
    from app.models.task import Task
    from app.skills.base import BaseSkill, SkillInput, SkillOutput, SkillPhase, SkillType
    from app.skills.registry import registry

    await init_db()
    project_id = "manual-skill-storage-isolation-project"
    duplicate_task_id = "manual-skill-storage-duplicate-task"

    async with async_session() as db:
        if await db.get(Project, project_id) is None:
            db.add(
                Project(
                    id=project_id,
                    name="Manual skill storage isolation",
                    project_context="Test project context",
                )
            )
        if await db.get(Task, duplicate_task_id) is None:
            db.add(
                Task(
                    id=duplicate_task_id,
                    project_id=project_id,
                    title="Existing task",
                )
            )
        await db.commit()

    class StorageIsolationSkill(BaseSkill):
        @property
        def name(self) -> str:
            return "storage-isolation-test"

        @property
        def display_name(self) -> str:
            return "Storage Isolation Test"

        @property
        def description(self) -> str:
            return "Returns a valid output while persistence is forced to fail."

        @property
        def phase(self) -> SkillPhase:
            return SkillPhase.DISCOVER

        @property
        def skill_type(self) -> SkillType:
            return SkillType.QUALITATIVE

        async def plan(self, skill_input: SkillInput) -> dict:
            return {"steps": ["run"]}

        async def execute(self, skill_input: SkillInput) -> SkillOutput:
            return SkillOutput(
                success=True,
                summary="Valid skill output",
                nuggets=[{"text": "A valid piece of evidence", "source": "test", "tags": ["valid"]}],
                facts=[{"text": "A valid fact"}],
            )

    original_skill = registry._skills.get("storage-isolation-test")
    registry._skills["storage-isolation-test"] = StorageIsolationSkill()

    async def poisoned_store(self, db, project_id_arg, output, task):
        db.add(
            Task(
                id=duplicate_task_id,
                project_id=project_id_arg,
                title="Duplicate task that forces rollback",
            )
        )
        await db.commit()

    monkeypatch.setattr(AgentOrchestrator, "_store_findings", poisoned_store)

    try:
        output = await AgentOrchestrator().execute_skill(
            "storage-isolation-test",
            project_id,
            user_context="Run the storage isolation test.",
        )
    finally:
        if original_skill is None:
            registry._skills.pop("storage-isolation-test", None)
        else:
            registry._skills["storage-isolation-test"] = original_skill

    assert output.success is True
    assert output.summary == "Valid skill output"
    assert output.errors == []
