"""Tests for Surveys API routes — integrations, links, sync, responses."""

import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.models.database import async_session, init_db
from app.core.auth import create_token
from app.models.project import Project


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


async def _seed_project(name: str | None = None) -> Project:
    project = Project(id=str(uuid.uuid4()), name=name or f"Survey Project {uuid.uuid4()}")
    async with async_session() as db:
        db.add(project)
        await db.commit()
        await db.refresh(project)
    return project


@pytest.mark.asyncio
async def test_surveys_integrations_returns_list(auth_headers):
    """GET /api/surveys/integrations returns a list."""
    await init_db()
    project = await _seed_project()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/surveys/integrations?project_id={project.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), dict)


@pytest.mark.asyncio
async def test_surveys_integrations_require_project_id_for_project_facing_api(auth_headers):
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/surveys/integrations", headers=auth_headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "project_id is required"


@pytest.mark.asyncio
async def test_surveys_integrations_requires_auth():
    """Surveys integrations requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/surveys/integrations")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_surveys_links_returns_list(auth_headers):
    """GET /api/surveys/links returns survey links."""
    await init_db()
    project = await _seed_project()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/surveys/links?project_id={project.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), dict)


@pytest.mark.asyncio
async def test_surveys_links_require_project_id_for_project_facing_api(auth_headers):
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/surveys/links", headers=auth_headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "project_id is required"


@pytest.mark.asyncio
async def test_demo_survey_link_sync_and_responses_do_not_call_platform(auth_headers, monkeypatch):
    """Simulation/demo survey integrations stay local and deterministic."""
    await init_db()
    project = await _seed_project("Survey Demo")
    project_id = project.id

    def fail_adapter(_integration):
        raise AssertionError("demo integrations must not instantiate a platform adapter")

    monkeypatch.setattr("app.api.routes.surveys._get_adapter", fail_adapter)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        integration_response = await ac.post(
            "/api/surveys/integrations",
            headers=auth_headers,
            json={
                "platform": "typeform",
                "name": "SIM: Scenario 55",
                "config": {"token": "sim-token"},
                "project_id": project_id,
            },
        )
        assert integration_response.status_code == 201
        integration_id = integration_response.json()["id"]

        link_response = await ac.post(
            "/api/surveys/links",
            headers=auth_headers,
            json={
                "integration_id": integration_id,
                "project_id": project_id,
                "external_survey_id": "sim-survey-001",
                "external_survey_name": "Demo Survey",
            },
        )
        assert link_response.status_code == 201
        link_id = link_response.json()["id"]

        sync_response = await ac.post(
            f"/api/surveys/links/{link_id}/sync?project_id={project_id}",
            headers=auth_headers,
        )
        responses_response = await ac.get(
            f"/api/surveys/links/{link_id}/responses?project_id={project_id}",
            headers=auth_headers,
        )

    assert sync_response.status_code == 200
    assert sync_response.json()["demo"] is True
    assert sync_response.json()["project_id"] == project_id
    assert sync_response.json()["responses_fetched"] == 0
    assert responses_response.status_code == 200
    assert responses_response.json()["demo"] is True
    assert responses_response.json()["project_id"] == project_id
    assert responses_response.json()["responses"] == []


@pytest.mark.asyncio
async def test_survey_detail_actions_require_active_project_scope(auth_headers, monkeypatch):
    await init_db()
    project_a = await _seed_project("Survey Scope A")
    project_b = await _seed_project("Survey Scope B")

    def fail_adapter(_integration):
        raise AssertionError("wrong-project and missing-project checks must run before adapters")

    monkeypatch.setattr("app.api.routes.surveys._get_adapter", fail_adapter)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        integration_response = await ac.post(
            "/api/surveys/integrations",
            headers=auth_headers,
            json={
                "platform": "typeform",
                "name": "SIM: Scoped Survey",
                "config": {"token": "sim-token"},
                "project_id": project_a.id,
            },
        )
        delete_integration_response = await ac.post(
            "/api/surveys/integrations",
            headers=auth_headers,
            json={
                "platform": "typeform",
                "name": "SIM: Delete Survey",
                "config": {"token": "sim-token"},
                "project_id": project_a.id,
            },
        )
        integration_id = integration_response.json()["id"]
        delete_integration_id = delete_integration_response.json()["id"]

        link_response = await ac.post(
            "/api/surveys/links",
            headers=auth_headers,
            json={
                "integration_id": integration_id,
                "project_id": project_a.id,
                "external_survey_id": "survey-a",
                "external_survey_name": "Survey A",
            },
        )
        link_id = link_response.json()["id"]

        missing_surveys = await ac.get(
            f"/api/surveys/integrations/{integration_id}/surveys",
            headers=auth_headers,
        )
        wrong_surveys = await ac.get(
            f"/api/surveys/integrations/{integration_id}/surveys?project_id={project_b.id}",
            headers=auth_headers,
        )
        missing_create = await ac.post(
            f"/api/surveys/integrations/{integration_id}/create",
            headers=auth_headers,
            json={"title": "Wrong scope", "questions": []},
        )
        wrong_create = await ac.post(
            f"/api/surveys/integrations/{integration_id}/create?project_id={project_b.id}",
            headers=auth_headers,
            json={"title": "Wrong scope", "questions": []},
        )
        missing_sync = await ac.post(
            f"/api/surveys/links/{link_id}/sync",
            headers=auth_headers,
        )
        wrong_sync = await ac.post(
            f"/api/surveys/links/{link_id}/sync?project_id={project_b.id}",
            headers=auth_headers,
        )
        correct_sync = await ac.post(
            f"/api/surveys/links/{link_id}/sync?project_id={project_a.id}",
            headers=auth_headers,
        )
        missing_responses = await ac.get(
            f"/api/surveys/links/{link_id}/responses",
            headers=auth_headers,
        )
        wrong_responses = await ac.get(
            f"/api/surveys/links/{link_id}/responses?project_id={project_b.id}",
            headers=auth_headers,
        )
        correct_responses = await ac.get(
            f"/api/surveys/links/{link_id}/responses?project_id={project_a.id}",
            headers=auth_headers,
        )
        missing_delete = await ac.delete(
            f"/api/surveys/integrations/{delete_integration_id}",
            headers=auth_headers,
        )
        wrong_delete = await ac.delete(
            f"/api/surveys/integrations/{delete_integration_id}?project_id={project_b.id}",
            headers=auth_headers,
        )
        correct_delete = await ac.delete(
            f"/api/surveys/integrations/{delete_integration_id}?project_id={project_a.id}",
            headers=auth_headers,
        )

    assert integration_response.status_code == 201
    assert delete_integration_response.status_code == 201
    assert link_response.status_code == 201
    assert missing_surveys.status_code == 400
    assert wrong_surveys.status_code == 404
    assert missing_create.status_code == 400
    assert wrong_create.status_code == 404
    assert missing_sync.status_code == 400
    assert wrong_sync.status_code == 404
    assert correct_sync.status_code == 200
    assert correct_sync.json()["project_id"] == project_a.id
    assert missing_responses.status_code == 400
    assert wrong_responses.status_code == 404
    assert correct_responses.status_code == 200
    assert correct_responses.json()["project_id"] == project_a.id
    assert missing_delete.status_code == 400
    assert missing_delete.json()["detail"] == "project_id is required"
    assert wrong_delete.status_code == 404
    assert correct_delete.status_code == 204
