"""Tests for Loops/Scheduler API routes — overview, agents, executions, health, custom."""

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
            f"/api/schedules/{schedule['id']}",
            headers=auth_headers,
            json={"enabled": False},
        )
        assert paused.status_code == 200
        assert paused.json()["enabled"] is False

        deleted = await ac.delete(f"/api/schedules/{schedule['id']}", headers=auth_headers)
        assert deleted.status_code == 204

        missing = await ac.get(f"/api/schedules/{schedule['id']}", headers=auth_headers)
        assert missing.status_code == 404


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
            f"/api/schedules/{schedule['id']}",
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
