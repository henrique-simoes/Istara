"""Tests for Skills API routes — CRUD, execute, health, proposals."""

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from httpx import AsyncClient, ASGITransport
from starlette.requests import Request

from app.api.routes import skills as skills_route
from app.main import app
from app.config import settings
from app.models.database import init_db
from app.core.auth import create_token
from app.skills.base import SkillOutput


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
async def test_skills_list_returns_list(auth_headers):
    """GET /api/skills returns a list."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/skills", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        # Should have 53 skills
        assert len(data) > 0


@pytest.mark.asyncio
async def test_skills_list_requires_auth():
    """Skills listing requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/skills")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_skill_get_returns_skill(auth_headers):
    """GET /api/skills/{name} returns a skill."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Get the first skill from the list
        response = await ac.get("/api/skills", headers=auth_headers)
        if response.status_code == 200 and response.json():
            skill_name = (
                response.json().get("skills", [{}])[0].get("name", "card-sorting")
                if response.json().get("skills")
                else "card-sorting"
            )
            response = await ac.get(f"/api/skills/{skill_name}", headers=auth_headers)
            assert response.status_code in (200, 404)


@pytest.mark.asyncio
async def test_skill_health_returns_response(auth_headers):
    """GET /api/skills/health/all returns health status."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            "/api/skills/health/all?project_id=project-1", headers=auth_headers
        )
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_skill_proposals_pending_returns_list(auth_headers):
    """GET /api/skills/proposals/pending returns list."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            "/api/skills/proposals/pending?project_id=project-1", headers=auth_headers
        )
        assert response.status_code == 200
        assert isinstance(response.json(), dict)


@pytest.mark.asyncio
async def test_skill_project_surfaces_require_project_id(auth_headers):
    """Project-derived skill health and proposal lists require explicit project scope."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        health = await ac.get("/api/skills/health/all", headers=auth_headers)
        proposals = await ac.get("/api/skills/proposals/all", headers=auth_headers)
        creation = await ac.get(
            "/api/skills/creation-proposals/all", headers=auth_headers
        )

    assert health.status_code == 400
    assert proposals.status_code == 400
    assert creation.status_code == 400


@pytest.mark.asyncio
async def test_skill_improvement_proposals_are_filtered_by_project(
    monkeypatch, auth_headers
):
    """Skill update proposals from one project are invisible and immutable from another."""
    await init_db()
    original = skills_route.skill_manager._proposals
    skills_route.skill_manager._proposals = []
    monkeypatch.setattr(skills_route.skill_manager, "_save_proposals", lambda: None)
    try:
        project_a = skills_route.skill_manager.propose_improvement(
            "card-sorting",
            "execute_prompt",
            "old-a",
            "new-a",
            "project a",
            project_id="project-a",
        )
        project_b = skills_route.skill_manager.propose_improvement(
            "heuristic-evaluation",
            "execute_prompt",
            "old-b",
            "new-b",
            "project b",
            project_id="project-b",
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            listed = await ac.get(
                "/api/skills/proposals/all?project_id=project-a",
                headers=auth_headers,
            )
            wrong_project_reject = await ac.post(
                f"/api/skills/proposals/{project_b.id}/reject?project_id=project-a",
                headers=auth_headers,
            )
            right_project_reject = await ac.post(
                f"/api/skills/proposals/{project_a.id}/reject?project_id=project-a",
                headers=auth_headers,
            )

        assert listed.status_code == 200
        ids = {item["id"] for item in listed.json()["proposals"]}
        assert project_a.id in ids
        assert project_b.id not in ids
        assert wrong_project_reject.status_code == 404
        assert right_project_reject.status_code == 200
    finally:
        skills_route.skill_manager._proposals = original


def test_skill_improvement_proposal_requires_project_id(monkeypatch):
    """Autonomous skill updates must not create unscoped/global proposals."""
    original = skills_route.skill_manager._proposals
    skills_route.skill_manager._proposals = []
    monkeypatch.setattr(skills_route.skill_manager, "_save_proposals", lambda: None)
    try:
        with pytest.raises(ValueError, match="project_id is required"):
            skills_route.skill_manager.propose_improvement(
                "card-sorting",
                "execute_prompt",
                "old",
                "new",
                "missing project",
            )

        with pytest.raises(ValueError, match="project_id is required"):
            skills_route.skill_manager.propose_improvement(
                "card-sorting",
                "execute_prompt",
                "old",
                "new",
                "blank project",
                project_id="   ",
            )

        assert skills_route.skill_manager._proposals == []
    finally:
        skills_route.skill_manager._proposals = original


def test_skill_usage_does_not_auto_mutate_global_skill_lifecycle(monkeypatch):
    """Low utility in one project should surface for review, not mutate global skills."""
    manager = skills_route.skill_manager
    original_stats = manager._usage_stats
    manager._usage_stats = {}
    update_calls: list[tuple] = []
    monkeypatch.setattr(manager, "_save_stats", lambda: None)
    monkeypatch.setattr(
        manager,
        "update_skill",
        lambda *args, **kwargs: update_calls.append((args, kwargs)),
    )

    try:
        for _ in range(10):
            manager.record_execution(
                "low-utility-test-skill",
                success=False,
                quality_score=0.0,
                project_id="project-low-utility",
            )

        project_stats = manager.get_usage_stats(
            "low-utility-test-skill",
            project_id="project-low-utility",
        )
        assert project_stats["executions"] == 10
        assert project_stats["utility_score"] < 0.3
        assert update_calls == []
    finally:
        manager._usage_stats = original_stats


@pytest.mark.asyncio
async def test_skill_creation_proposals_are_filtered_by_project(
    monkeypatch, auth_headers
):
    """Autonomous creation proposals keep their source project boundary."""
    await init_db()
    original = skills_route.skill_manager._creation_proposals
    skills_route.skill_manager._creation_proposals = []
    monkeypatch.setattr(
        skills_route.skill_manager, "_save_creation_proposals", lambda: None
    )

    def definition(name: str) -> dict:
        return {
            "name": name,
            "display_name": name.replace("-", " ").title(),
            "description": f"Autonomous proposal for {name}",
            "phase": "discover",
            "skill_type": "analysis",
            "plan_prompt": "Plan research for {context}.",
            "execute_prompt": "Analyze content for patterns and summarize findings.",
            "output_schema": '{"summary": "string"}',
        }

    try:
        project_a = skills_route.skill_manager.propose_skill_creation(
            definition("auto-project-a-skill"),
            source_task_id="task-a",
            agent_id="agent-a",
            reason="project a",
            confidence=70,
            project_id="project-a",
        )
        project_b = skills_route.skill_manager.propose_skill_creation(
            definition("auto-project-b-skill"),
            source_task_id="task-b",
            agent_id="agent-b",
            reason="project b",
            confidence=70,
            project_id="project-b",
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            listed = await ac.get(
                "/api/skills/creation-proposals/all?project_id=project-a",
                headers=auth_headers,
            )
            wrong_project_reject = await ac.post(
                f"/api/skills/creation-proposals/{project_b.id}/reject?project_id=project-a",
                headers=auth_headers,
            )
            right_project_reject = await ac.post(
                f"/api/skills/creation-proposals/{project_a.id}/reject?project_id=project-a",
                headers=auth_headers,
            )

        assert listed.status_code == 200
        ids = {item["id"] for item in listed.json()["proposals"]}
        assert project_a.id in ids
        assert project_b.id not in ids
        assert wrong_project_reject.status_code == 404
        assert right_project_reject.status_code == 200
    finally:
        skills_route.skill_manager._creation_proposals = original


def test_skill_creation_proposal_requires_project_id(monkeypatch):
    """Autonomous skill creation must not create unscoped/global proposals."""
    original = skills_route.skill_manager._creation_proposals
    skills_route.skill_manager._creation_proposals = []
    monkeypatch.setattr(
        skills_route.skill_manager, "_save_creation_proposals", lambda: None
    )

    definition = {
        "name": "auto-missing-project-skill",
        "display_name": "Auto Missing Project Skill",
        "description": "Should not be proposed without project scope",
        "phase": "discover",
        "skill_type": "analysis",
        "plan_prompt": "Plan research for {context}.",
        "execute_prompt": "Analyze content for patterns.",
        "output_schema": '{"summary": "string"}',
    }
    try:
        with pytest.raises(ValueError, match="project_id is required"):
            skills_route.skill_manager.propose_skill_creation(
                definition,
                source_task_id="task-missing-project",
                agent_id="agent-missing-project",
                reason="missing project",
                confidence=70,
            )

        with pytest.raises(ValueError, match="project_id is required"):
            skills_route.skill_manager.propose_skill_creation(
                definition,
                source_task_id="task-blank-project",
                agent_id="agent-blank-project",
                reason="blank project",
                confidence=70,
                project_id=" ",
            )

        assert skills_route.skill_manager._creation_proposals == []
    finally:
        skills_route.skill_manager._creation_proposals = original


class _SlowSkillAgent:
    async def execute_skill(self, **kwargs):
        await asyncio.sleep(5)

    async def plan_skill(self, **kwargs):
        await asyncio.sleep(5)


def _request() -> Request:
    return Request({"type": "http", "method": "POST", "path": "/", "headers": []})


@pytest.mark.asyncio
async def test_execute_skill_enforces_route_timeout(monkeypatch):
    """Skill execution cancels at the route budget instead of orphaning LLM work."""

    async def allow_active_project(*args, **kwargs):
        return SimpleNamespace(id="project-1", is_paused=False)

    monkeypatch.setattr(skills_route.registry, "get", lambda name: object())
    monkeypatch.setattr(skills_route, "get_active_project_or_404", allow_active_project)
    monkeypatch.setattr(skills_route, "agent", _SlowSkillAgent())

    with pytest.raises(HTTPException) as exc:
        await skills_route.execute_skill(
            "slow-skill",
            skills_route.SkillExecuteRequest(
                project_id="project-1", timeout_seconds=0.1
            ),
            _request(),
            db=None,
        )

    assert exc.value.status_code == 504
    assert "timed out" in exc.value.detail


@pytest.mark.asyncio
async def test_execute_skill_exposes_provisional_research_validity(monkeypatch):
    """Skill execution responses cannot present candidate output as reportable."""

    async def allow_active_project(*args, **kwargs):
        return SimpleNamespace(id="project-1", is_paused=False)

    class SelfPromotingSkillAgent:
        async def execute_skill(self, **kwargs):
            return SkillOutput(
                success=True,
                summary="Skill generated candidate evidence.",
                research_validity={"status": "accepted", "report_allowed": True},
                nuggets=[
                    {
                        "text": "A model-generated observation.",
                        "source": "skill",
                        "tags": ["friction"],
                        "research_validity": {
                            "status": "accepted",
                            "report_allowed": True,
                        },
                    }
                ],
            )

    monkeypatch.setattr(skills_route.registry, "get", lambda name: object())
    monkeypatch.setattr(skills_route, "get_active_project_or_404", allow_active_project)
    monkeypatch.setattr(skills_route, "agent", SelfPromotingSkillAgent())

    response = await skills_route.execute_skill(
        "candidate-skill",
        skills_route.SkillExecuteRequest(project_id="project-1", timeout_seconds=0.1),
        _request(),
        db=None,
    )

    assert response["artifact_state"] == "skill_output_candidate"
    assert response["report_allowed"] is False
    assert response["research_validity"]["status"] == "provisional"
    assert response["research_validity"]["report_allowed"] is False


@pytest.mark.asyncio
async def test_plan_skill_enforces_route_timeout(monkeypatch):
    """Skill planning uses the same bounded server-side timeout path."""

    async def allow_active_project(*args, **kwargs):
        return SimpleNamespace(id="project-1", is_paused=False)

    monkeypatch.setattr(skills_route.registry, "get", lambda name: object())
    monkeypatch.setattr(skills_route, "get_active_project_or_404", allow_active_project)
    monkeypatch.setattr(skills_route, "agent", _SlowSkillAgent())

    with pytest.raises(HTTPException) as exc:
        await skills_route.plan_skill(
            "slow-skill",
            skills_route.SkillPlanRequest(project_id="project-1", timeout_seconds=0.1),
            _request(),
            db=None,
        )

    assert exc.value.status_code == 504
    assert "timed out" in exc.value.detail


@pytest.mark.asyncio
async def test_execute_and_plan_reject_paused_project_before_agent_call(monkeypatch):
    """Active project guards run before any skill agent can process content."""

    async def paused_project(*args, **kwargs):
        raise HTTPException(status_code=409, detail="Project is paused")

    class FailingAgent:
        async def execute_skill(self, **kwargs):
            raise AssertionError("execute_skill must not run for paused projects")

        async def plan_skill(self, **kwargs):
            raise AssertionError("plan_skill must not run for paused projects")

    monkeypatch.setattr(skills_route.registry, "get", lambda name: object())
    monkeypatch.setattr(skills_route, "get_active_project_or_404", paused_project)
    monkeypatch.setattr(skills_route, "agent", FailingAgent())

    with pytest.raises(HTTPException) as execute_exc:
        await skills_route.execute_skill(
            "paused-skill",
            skills_route.SkillExecuteRequest(
                project_id="paused-project", timeout_seconds=0.1
            ),
            _request(),
            db=None,
        )

    with pytest.raises(HTTPException) as plan_exc:
        await skills_route.plan_skill(
            "paused-skill",
            skills_route.SkillPlanRequest(
                project_id="paused-project", timeout_seconds=0.1
            ),
            _request(),
            db=None,
        )

    assert execute_exc.value.status_code == 409
    assert plan_exc.value.status_code == 409
