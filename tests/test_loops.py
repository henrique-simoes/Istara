"""Tests for Loops/Scheduler API routes — overview, agents, executions, health, custom."""

import json
from datetime import datetime, timedelta, timezone
import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.config import settings
from app.core.scheduler import ScheduledTask, scheduler
from app.core.auth import create_token
from app.models.database import async_session, init_db
from app.models.agent import Agent, AgentRole, AgentState
from app.models.loop_execution import LoopExecution
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.services.loop_execution_service import record_execution


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


@pytest.fixture
def researcher_headers():
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    token = create_token("researcher-loops", "researcher", "researcher")
    return {"Authorization": f"Bearer {token}"}


async def _seed_project_member(project_id: str, user_id: str, role: str) -> None:
    async with async_session() as db:
        db.add(Project(id=project_id, name=f"Loops {project_id}"))
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


async def _seed_loop_scope_fixture(user_id: str) -> dict[str, str]:
    visible_project_id = f"project-visible-{uuid.uuid4()}"
    hidden_project_id = f"project-hidden-{uuid.uuid4()}"
    visible_schedule_id = str(uuid.uuid4())
    hidden_schedule_id = str(uuid.uuid4())
    visible_agent_id = str(uuid.uuid4())
    hidden_agent_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    async with async_session() as db:
        db.add_all([
            Project(id=visible_project_id, name="Visible Loops Project"),
            Project(id=hidden_project_id, name="Hidden Loops Project"),
            ProjectMember(
                id=str(uuid.uuid4()),
                project_id=visible_project_id,
                user_id=user_id,
                role="researcher",
                added_by="test",
            ),
            Agent(
                id=visible_agent_id,
                name="Visible Loop Agent",
                role=AgentRole.CUSTOM,
                state=AgentState.IDLE,
                scope="project",
                project_id=visible_project_id,
                memory=json.dumps({"loop_config": {"skills_to_run": ["visible-skill"]}}),
            ),
            Agent(
                id=hidden_agent_id,
                name="Hidden Loop Agent",
                role=AgentRole.CUSTOM,
                state=AgentState.IDLE,
                scope="project",
                project_id=hidden_project_id,
                memory=json.dumps({"loop_config": {"skills_to_run": ["hidden-skill"]}}),
            ),
            ScheduledTask(
                id=visible_schedule_id,
                name="Visible Project Schedule",
                description="",
                cron_expression="0 * * * *",
                skill_name="visible_skill",
                project_id=visible_project_id,
                next_run=now + timedelta(hours=1),
            ),
            ScheduledTask(
                id=hidden_schedule_id,
                name="Hidden Project Schedule",
                description="",
                cron_expression="0 * * * *",
                skill_name="hidden_skill",
                project_id=hidden_project_id,
                next_run=now + timedelta(hours=1),
            ),
            LoopExecution(
                id=str(uuid.uuid4()),
                source_type="schedule",
                source_id=visible_schedule_id,
                source_name="Visible Project Schedule",
                status="success",
                started_at=now - timedelta(minutes=10),
                finished_at=now - timedelta(minutes=9),
                duration_ms=60000,
                metadata_json=json.dumps({"project_id": visible_project_id}),
            ),
            LoopExecution(
                id=str(uuid.uuid4()),
                source_type="schedule",
                source_id=hidden_schedule_id,
                source_name="Hidden Project Schedule",
                status="failure",
                started_at=now - timedelta(minutes=8),
                finished_at=now - timedelta(minutes=7),
                duration_ms=60000,
                metadata_json=json.dumps({"project_id": hidden_project_id}),
            ),
        ])
        await db.commit()
    return {
        "visible_project_id": visible_project_id,
        "hidden_project_id": hidden_project_id,
        "visible_schedule_id": visible_schedule_id,
        "hidden_schedule_id": hidden_schedule_id,
        "visible_agent_id": visible_agent_id,
        "hidden_agent_id": hidden_agent_id,
    }


@pytest.mark.asyncio
async def test_loops_overview_returns_response(auth_headers):
    """GET /api/loops/overview returns loop overview."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/loops/overview", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert "active_loops" in body
        assert "paused_loops" in body
        assert "behind_schedule" in body
        assert "total_executions_24h" in body
        assert 0 <= body["success_rate"] <= 1


@pytest.mark.asyncio
async def test_loops_overview_requires_auth():
    """Loops overview requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/loops/overview")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_project_member_loop_surfaces_require_active_project_scope(researcher_headers):
    """Non-admin loop surfaces must not fall back to global data."""
    await init_db()
    settings.team_mode = True
    ids = await _seed_loop_scope_fixture("researcher-loops")

    visible_project_id = ids["visible_project_id"]
    hidden_project_id = ids["hidden_project_id"]
    visible_schedule_id = ids["visible_schedule_id"]
    hidden_schedule_id = ids["hidden_schedule_id"]
    visible_agent_id = ids["visible_agent_id"]
    hidden_agent_id = ids["hidden_agent_id"]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        no_scope = await ac.get("/api/loops/overview", headers=researcher_headers)
        assert no_scope.status_code == 400
        assert no_scope.json()["detail"] == "project_id is required"

        hidden_scope = await ac.get(
            f"/api/loops/overview?project_id={hidden_project_id}",
            headers=researcher_headers,
        )
        assert hidden_scope.status_code == 404

        overview = await ac.get(
            f"/api/loops/overview?project_id={visible_project_id}",
            headers=researcher_headers,
        )
        assert overview.status_code == 200
        body = overview.json()
        assert {item["id"] for item in body["schedules"]} == {visible_schedule_id}
        assert {item["agent_id"] for item in body["agents"]} == {visible_agent_id}
        assert visible_schedule_id in {item["id"] for item in body["schedules"]}
        assert hidden_schedule_id not in {item["id"] for item in body["schedules"]}
        assert hidden_agent_id not in {item["agent_id"] for item in body["agents"]}
        assert body["total_executions_24h"] == 1

        health = await ac.get(
            f"/api/loops/health?project_id={visible_project_id}",
            headers=researcher_headers,
        )
        assert health.status_code == 200
        health_sources = {item["source_id"] for item in health.json()["health"]}
        assert visible_schedule_id in health_sources
        assert visible_agent_id in health_sources
        assert hidden_schedule_id not in health_sources
        assert hidden_agent_id not in health_sources

        agents = await ac.get(
            f"/api/loops/agents?project_id={visible_project_id}",
            headers=researcher_headers,
        )
        assert agents.status_code == 200
        assert {item["agent_id"] for item in agents.json()["agents"]} == {visible_agent_id}

        executions = await ac.get(
            f"/api/loops/executions?project_id={visible_project_id}",
            headers=researcher_headers,
        )
        assert executions.status_code == 200
        execution_ids = {item["source_id"] for item in executions.json()["executions"]}
        assert execution_ids == {visible_schedule_id}

        stats = await ac.get(
            f"/api/loops/executions/stats?project_id={visible_project_id}",
            headers=researcher_headers,
        )
        assert stats.status_code == 200
        assert stats.json()["total"] == 1
        assert stats.json()["success"] == 1
        assert stats.json()["failure"] == 0


@pytest.mark.asyncio
async def test_loops_health_returns_response(auth_headers):
    """GET /api/loops/health returns scheduler health."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/loops/health", headers=auth_headers)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_loops_executions_returns_list(auth_headers):
    """GET /api/loops/executions returns execution history."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/loops/executions", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), dict)
        assert "executions" in response.json()


@pytest.mark.asyncio
async def test_agent_loop_config_persists_skills_and_project_filter(auth_headers):
    """Agent loop config should round-trip the fields exposed in the UI."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        created = await ac.post(
            "/api/agents",
            headers=auth_headers,
            json={
                "name": "Loop Config Test Agent",
                "role": "custom",
                "system_prompt": "Temporary loop config test agent.",
                "capabilities": ["skill_execution"],
                "project_id": "project-test",
            },
        )
        assert created.status_code == 201
        agent_id = created.json()["id"]

        update = await ac.patch(
            f"/api/loops/agents/{agent_id}/config",
            headers=auth_headers,
            json={
                "loop_interval_seconds": 120,
                "skills_to_run": ["thematic-analysis", " thematic-analysis ", "card-sorting"],
                "project_filter": "project-test",
            },
        )
        assert update.status_code == 200
        updated = update.json()
        assert updated["agent_id"] == agent_id
        assert updated["loop_interval_seconds"] == 120
        assert updated["skills_to_run"] == ["thematic-analysis", "card-sorting"]
        assert updated["project_filter"] == "project-test"

        fetched = await ac.get(f"/api/loops/agents/{agent_id}/config", headers=auth_headers)
        assert fetched.status_code == 200
        config = fetched.json()
        assert config["agent_id"] == agent_id
        assert config["skills_to_run"] == ["thematic-analysis", "card-sorting"]
        assert config["project_filter"] == "project-test"

        listed = await ac.get("/api/loops/agents", headers=auth_headers)
        assert listed.status_code == 200
        matching = [item for item in listed.json()["agents"] if item["agent_id"] == agent_id]
        assert matching
        assert matching[0]["id"] == agent_id

        invalid = await ac.patch(
            f"/api/loops/agents/{agent_id}/config",
            headers=auth_headers,
            json={"loop_interval_seconds": 5},
        )
        assert invalid.status_code == 422

        await ac.delete(f"/api/agents/{agent_id}", headers=auth_headers)


@pytest.mark.asyncio
async def test_custom_loop_persists_as_custom_health_item(auth_headers):
    """Custom loops should round-trip as custom scheduled tasks with interval metadata."""
    await init_db()
    transport = ASGITransport(app=app)
    project_id = f"project-{uuid.uuid4()}"
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        created = await ac.post(
            "/api/loops/custom",
            headers=auth_headers,
            json={
                "name": "Custom UX Pulse",
                "skill_name": "ux_evaluation",
                "project_id": project_id,
                "interval_seconds": 300,
                "description": "Run UX checks every five minutes.",
            },
        )
        assert created.status_code == 201
        custom = created.json()
        assert custom["loop_type"] == "custom"
        assert custom["interval_seconds"] == 300

        health = await ac.get("/api/loops/health", headers=auth_headers)
        assert health.status_code == 200
        matching = [
            item for item in health.json()["health"]
            if item["source_id"] == custom["id"]
        ]
        assert matching
        assert matching[0]["source_type"] == "custom"
        assert matching[0]["interval_seconds"] == 300


@pytest.mark.asyncio
async def test_schedule_crud_and_cron_validation(auth_headers):
    """Schedules use the real scheduler CRUD contract and fail fast on bad cron."""
    await init_db()
    transport = ASGITransport(app=app)
    project_id = f"project-{uuid.uuid4()}"
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        invalid = await ac.post(
            "/api/schedules",
            headers=auth_headers,
            json={
                "name": "Invalid Schedule",
                "cron_expression": "60 * * * *",
                "project_id": project_id,
                "skill_name": "ux_evaluation",
            },
        )
        assert invalid.status_code == 422

        created = await ac.post(
            "/api/schedules",
            headers=auth_headers,
            json={
                "name": "Hourly Research Review",
                "cron_expression": "0 * * * *",
                "project_id": project_id,
                "skill_name": "ux_evaluation",
                "description": "Hourly pulse",
            },
        )
        assert created.status_code == 201
        schedule = created.json()
        assert schedule["project_id"] == project_id
        assert schedule["loop_type"] == "cron"
        assert schedule["enabled"] is True

        listed = await ac.get(f"/api/schedules?project_id={project_id}", headers=auth_headers)
        assert listed.status_code == 200
        assert any(item["id"] == schedule["id"] for item in listed.json())

        paused = await ac.patch(
            f"/api/schedules/{schedule['id']}?project_id={project_id}",
            headers=auth_headers,
            json={"enabled": False},
        )
        assert paused.status_code == 200
        assert paused.json()["enabled"] is False

        deleted = await ac.delete(
            f"/api/schedules/{schedule['id']}?project_id={project_id}",
            headers=auth_headers,
        )
        assert deleted.status_code == 204

        missing = await ac.get(
            f"/api/schedules/{schedule['id']}?project_id={project_id}",
            headers=auth_headers,
        )
        assert missing.status_code == 404


@pytest.mark.asyncio
async def test_schedule_detail_actions_require_active_project_scope(auth_headers):
    await init_db()
    project_a = f"schedule-active-{uuid.uuid4()}"
    project_b = f"schedule-other-{uuid.uuid4()}"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        created = await ac.post(
            "/api/schedules",
            headers=auth_headers,
            json={
                "name": "Scoped Schedule",
                "cron_expression": "0 * * * *",
                "project_id": project_a,
                "skill_name": "ux_evaluation",
            },
        )
        assert created.status_code == 201
        schedule = created.json()

        unscoped = await ac.get(f"/api/schedules/{schedule['id']}", headers=auth_headers)
        assert unscoped.status_code == 400
        assert unscoped.json()["detail"] == "project_id is required"

        wrong_project = await ac.get(
            f"/api/schedules/{schedule['id']}?project_id={project_b}",
            headers=auth_headers,
        )
        assert wrong_project.status_code == 404

        wrong_update = await ac.patch(
            f"/api/schedules/{schedule['id']}?project_id={project_b}",
            headers=auth_headers,
            json={"enabled": False},
        )
        assert wrong_update.status_code == 404

        scoped = await ac.get(
            f"/api/schedules/{schedule['id']}?project_id={project_a}",
            headers=auth_headers,
        )
        assert scoped.status_code == 200
        assert scoped.json()["project_id"] == project_a

        wrong_delete = await ac.delete(
            f"/api/schedules/{schedule['id']}?project_id={project_b}",
            headers=auth_headers,
        )
        assert wrong_delete.status_code == 404

        still_exists = await ac.get(
            f"/api/schedules/{schedule['id']}?project_id={project_a}",
            headers=auth_headers,
        )
        assert still_exists.status_code == 200


@pytest.mark.asyncio
async def test_researcher_can_manage_project_schedule(researcher_headers):
    await init_db()
    settings.team_mode = True
    project_id = f"project-{uuid.uuid4()}"
    await _seed_project_member(project_id, "researcher-loops", "researcher")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        created = await ac.post(
            "/api/schedules",
            headers=researcher_headers,
            json={
                "name": "Researcher Weekly Review",
                "cron_expression": "0 9 * * 1",
                "project_id": project_id,
                "skill_name": "ux_evaluation",
            },
        )
        assert created.status_code == 201
        schedule = created.json()

        updated = await ac.patch(
            f"/api/schedules/{schedule['id']}?project_id={project_id}",
            headers=researcher_headers,
            json={"enabled": False},
        )
        assert updated.status_code == 200
        assert updated.json()["enabled"] is False


@pytest.mark.asyncio
async def test_execution_history_uses_persisted_records_and_aliases(auth_headers):
    """Execution history should return persisted rows with table-ready fields."""
    await init_db()
    schedule_id = str(uuid.uuid4())
    started = datetime.now(timezone.utc) - timedelta(seconds=5)
    finished = datetime.now(timezone.utc)
    await record_execution(
        source_type="schedule",
        source_id=schedule_id,
        source_name="History Contract Check",
        status="failure",
        started_at=started,
        finished_at=finished,
        error_message="boom",
        findings_count=2,
        metadata={"schedule_id": schedule_id},
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            "/api/loops/executions?source_type=scheduled&status=failure",
            headers=auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        match = [item for item in body["executions"] if item["source_id"] == schedule_id]
        assert match
        execution = match[0]
        assert execution["id"]
        assert execution["source_type"] == "schedule"
        assert execution["started_at"]
        assert execution["duration_ms"] is not None
        assert execution["error_message"] == "boom"
        assert execution["findings_count"] == 2

        stats = await ac.get(
            f"/api/loops/executions/stats?source_id={schedule_id}",
            headers=auth_headers,
        )
        assert stats.status_code == 200
        assert stats.json()["failure"] == 1


@pytest.mark.asyncio
async def test_scheduler_records_missing_skill_as_failure(auth_headers):
    """A due schedule with an unknown skill should fail once and then disable itself."""
    await init_db()
    schedule_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    async with async_session() as db:
        db.add(ScheduledTask(
            id=schedule_id,
            name="Missing Skill Schedule",
            description="",
            cron_expression="* * * * *",
            skill_name="missing-skill-for-loop-test",
            project_id=f"project-{uuid.uuid4()}",
            next_run=now - timedelta(minutes=1),
        ))
        await db.commit()

    await scheduler._tick()

    async with async_session() as db:
        task = (await db.execute(
            select(ScheduledTask).where(ScheduledTask.id == schedule_id)
        )).scalar_one()
        assert task.is_running is False
        assert task.enabled is False
        assert task.next_run is None
        assert task.execution_count >= 1
        assert task.last_status == "failure"
        execution = (await db.execute(
            select(LoopExecution).where(LoopExecution.source_id == schedule_id)
        )).scalars().first()
        assert execution is not None
        assert execution.status == "failure"

    await scheduler._tick()

    async with async_session() as db:
        task = (await db.execute(
            select(ScheduledTask).where(ScheduledTask.id == schedule_id)
        )).scalar_one()
        executions = (await db.execute(
            select(LoopExecution).where(LoopExecution.source_id == schedule_id)
        )).scalars().all()
        assert task.execution_count == 1
        assert len(executions) == 1


@pytest.mark.asyncio
async def test_scheduler_skips_paused_project_without_running_skill(auth_headers):
    """Due schedules for paused projects do not mutate or run skills."""
    await init_db()
    project_id = str(uuid.uuid4())
    schedule_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    async with async_session() as db:
        db.add(Project(id=project_id, name="Paused schedule project", is_paused=True))
        db.add(ScheduledTask(
            id=schedule_id,
            name="Paused Project Schedule",
            description="",
            cron_expression="* * * * *",
            skill_name="missing-skill-that-should-not-run",
            project_id=project_id,
            next_run=now - timedelta(minutes=1),
        ))
        await db.commit()

    await scheduler._tick()

    async with async_session() as db:
        task = (await db.execute(
            select(ScheduledTask).where(ScheduledTask.id == schedule_id)
        )).scalar_one()
        execution = (await db.execute(
            select(LoopExecution).where(LoopExecution.source_id == schedule_id)
        )).scalars().first()

    assert task.enabled is True
    assert task.last_status == ""
    assert task.execution_count == 0
    assert execution is None
