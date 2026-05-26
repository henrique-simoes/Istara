"""Tests for Interfaces API routes — screens, design chat, Figma, handoff, configure."""

import json
import uuid
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.models.database import async_session, init_db
from app.core.auth import create_token
from app.models.design_screen import DesignBrief, DesignDecision, DesignScreen
from app.models.finding import Insight, Recommendation
from app.models.interface_config import ProjectInterfaceConfig
from app.models.project import Project
from app.services.design_evidence import build_seeded_prompt, resolve_seed_findings


@pytest.fixture(autouse=True)
def reset_settings():
    original_team_mode = settings.team_mode
    original_jwt_secret = settings.jwt_secret
    original_stitch_api_key = settings.stitch_api_key
    original_figma_api_token = settings.figma_api_token
    original_runtime_profile = settings.istara_runtime_profile
    original_mock_enabled = settings.interfaces_mock_endpoints_enabled
    yield
    settings.team_mode = original_team_mode
    settings.jwt_secret = original_jwt_secret
    settings.stitch_api_key = original_stitch_api_key
    settings.figma_api_token = original_figma_api_token
    settings.istara_runtime_profile = original_runtime_profile
    settings.interfaces_mock_endpoints_enabled = original_mock_enabled


@pytest.fixture
def auth_headers():
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    token = create_token("user1", "testuser", "admin")
    return {"Authorization": f"Bearer {token}"}


async def _seed_project(name: str = "Interfaces Test Project") -> Project:
    project = Project(id=str(uuid.uuid4()), name=f"{name} {uuid.uuid4()}")
    async with async_session() as db:
        db.add(project)
        await db.commit()
        await db.refresh(project)
    return project


async def _seed_interface_config(
    project_id: str,
    *,
    stitch_api_key: str = "",
    figma_api_token: str = "",
) -> ProjectInterfaceConfig:
    config = ProjectInterfaceConfig(project_id=project_id)
    config.set_stitch_api_key(stitch_api_key)
    config.set_figma_api_token(figma_api_token)
    async with async_session() as db:
        await db.merge(config)
        await db.commit()
        saved = await db.get(ProjectInterfaceConfig, project_id)
        assert saved is not None
        return saved


async def _seed_recommendation(project_id: str, text: str | None = None) -> Recommendation:
    rec = Recommendation(
        id=str(uuid.uuid4()),
        project_id=project_id,
        text=text or "Reduce too many options in onboarding to improve decision speed",
        insight_ids="[]",
        phase="deliver",
        priority="high",
        effort="medium",
    )
    async with async_session() as db:
        db.add(rec)
        await db.commit()
        await db.refresh(rec)
    return rec


async def _seed_insight(project_id: str) -> Insight:
    insight = Insight(
        id=str(uuid.uuid4()),
        project_id=project_id,
        text="Users struggle to understand the current onboarding sequence",
        fact_ids="[]",
        phase="define",
        impact="high",
    )
    async with async_session() as db:
        db.add(insight)
        await db.commit()
        await db.refresh(insight)
    return insight


@pytest.mark.asyncio
async def test_seeded_design_prompt_marks_provisional_research_context():
    """Design generation prompts must not turn provisional findings into trusted context."""
    await init_db()
    project = await _seed_project("Seed Prompt Validity")
    rec = await _seed_recommendation(project.id)

    async with async_session() as db:
        seed_findings, missing = await resolve_seed_findings(
            db,
            project.id,
            [rec.id],
        )

    prompt = build_seeded_prompt("Create a calmer onboarding screen", seed_findings)

    assert missing == []
    assert seed_findings[0].research_validity is not None
    assert seed_findings[0].research_validity["status"] == "provisional"
    assert seed_findings[0].research_validity["report_allowed"] is False
    assert seed_findings[0].to_dict()["research_validity"]["status"] == "provisional"
    assert f"[recommendation:{rec.id} provisional]" in prompt
    assert "candidate context only" in prompt
    assert "not accepted report evidence" in prompt


@pytest.mark.asyncio
async def test_interfaces_screens_returns_list(auth_headers):
    """GET /api/interfaces/screens returns screen list."""
    await init_db()
    project = await _seed_project("Screens List")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/interfaces/screens?project_id={project.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_interfaces_screens_surface_research_spine_state(auth_headers):
    """Screens must show whether their research seeds are accepted or provisional."""
    await init_db()
    project = await _seed_project("Screen Validity")
    rec = await _seed_recommendation(project.id)
    screen = DesignScreen(
        id=str(uuid.uuid4()),
        project_id=project.id,
        title="Seeded screen",
        description="Uses a provisional recommendation",
        prompt="Design an onboarding screen",
        device_type="DESKTOP",
        source_findings=json.dumps([rec.id]),
    )
    async with async_session() as db:
        db.add(screen)
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        listed = await ac.get(
            f"/api/interfaces/screens?project_id={project.id}",
            headers=auth_headers,
        )
        fetched = await ac.get(
            f"/api/interfaces/screens/{screen.id}",
            headers=auth_headers,
        )

    assert listed.status_code == 200
    payload = next(item for item in listed.json() if item["id"] == screen.id)
    assert payload["source_findings"] == [rec.id]
    assert payload["source_finding_details"][0]["id"] == rec.id
    assert payload["source_finding_details"][0]["research_validity"]["status"] == "provisional"
    assert payload["research_validity"]["report_allowed"] is False
    assert fetched.status_code == 200
    assert fetched.json()["research_validity"]["blocked_source_ids"] == [rec.id]


@pytest.mark.asyncio
async def test_interfaces_screens_require_project_id_for_project_facing_api(auth_headers):
    """Project-facing Interfaces screens never fall back to global lists."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/interfaces/screens", headers=auth_headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "project_id is required"


@pytest.mark.asyncio
async def test_interfaces_requires_auth():
    """Interfaces endpoints require authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/interfaces/screens")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_interfaces_status_returns_response(auth_headers):
    """GET /api/interfaces/status returns interface status."""
    await init_db()
    project = await _seed_project("Interfaces Status")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/interfaces/status?project_id={project.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["scope"] == "project"


@pytest.mark.asyncio
async def test_interfaces_status_requires_project_id_for_project_facing_api(auth_headers):
    """Project-facing Interfaces status never exposes global counts."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/interfaces/status", headers=auth_headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "project_id is required"


@pytest.mark.asyncio
async def test_interfaces_status_is_project_scoped(auth_headers):
    """Interfaces status counts artifacts and credentials in the active project only."""
    await init_db()
    project_a = await _seed_project("Interfaces Status A")
    project_b = await _seed_project("Interfaces Status B")
    await _seed_interface_config(project_a.id, figma_api_token="figma-project-a")
    async with async_session() as db:
        db.add(
            DesignScreen(
                id=str(uuid.uuid4()),
                project_id=project_a.id,
                title="Project A Screen",
                prompt="A",
                device_type="DESKTOP",
            )
        )
        db.add(
            DesignScreen(
                id=str(uuid.uuid4()),
                project_id=project_b.id,
                title="Project B Screen",
                prompt="B",
                device_type="DESKTOP",
            )
        )
        db.add(
            DesignBrief(
                id=str(uuid.uuid4()),
                project_id=project_a.id,
                title="Project A Brief",
                content="A",
            )
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response_a = await ac.get(
            f"/api/interfaces/status?project_id={project_a.id}",
            headers=auth_headers,
        )
        response_b = await ac.get(
            f"/api/interfaces/status?project_id={project_b.id}",
            headers=auth_headers,
        )

    assert response_a.status_code == 200
    assert response_a.json()["screens_count"] == 1
    assert response_a.json()["briefs_count"] == 1
    assert response_a.json()["figma_configured"] is True
    assert response_b.status_code == 200
    assert response_b.json()["screens_count"] == 1
    assert response_b.json()["briefs_count"] == 0
    assert response_b.json()["figma_configured"] is False


@pytest.mark.asyncio
async def test_mock_generate_rejects_cross_project_seed(auth_headers):
    """Mock generation must not link findings from another project."""
    await init_db()
    target = await _seed_project("Target")
    other = await _seed_project("Other")
    rec = await _seed_recommendation(other.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/interfaces/mock/generate",
            headers=auth_headers,
            json={
                "project_id": target.id,
                "prompt": "Create a dashboard",
                "seed_finding_ids": [rec.id],
            },
        )

    assert response.status_code == 422
    assert rec.id in response.json()["detail"]


@pytest.mark.asyncio
async def test_handoff_briefs_hydrate_evidence_payload(auth_headers):
    """Brief listing returns the source objects that HandoffTab renders."""
    await init_db()
    project = await _seed_project("Brief")
    insight = await _seed_insight(project.id)
    rec = await _seed_recommendation(project.id)
    brief = DesignBrief(
        id=str(uuid.uuid4()),
        project_id=project.id,
        title="Evidence Brief",
        content="Brief content",
        source_insight_ids=json.dumps([insight.id]),
        source_recommendation_ids=json.dumps([rec.id]),
    )
    async with async_session() as db:
        db.add(brief)
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/interfaces/handoff/briefs?project_id={project.id}",
            headers=auth_headers,
        )

    assert response.status_code == 200
    payload = response.json()["briefs"][0]
    assert payload["source_findings"][0]["id"] == insight.id
    assert payload["source_findings"][0]["research_validity"]["status"] == "provisional"
    assert payload["recommendations"][0]["id"] == rec.id
    assert payload["recommendations"][0]["research_validity"]["report_allowed"] is False
    assert payload["research_validity"]["report_allowed"] is False
    assert payload["ux_laws"]


@pytest.mark.asyncio
async def test_handoff_briefs_require_project_id_for_project_facing_api(auth_headers):
    """Project-facing handoff brief lists never fall back to global admin data."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/interfaces/handoff/briefs", headers=auth_headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "project_id is required"


@pytest.mark.asyncio
async def test_handoff_brief_generation_creates_hydrated_brief(auth_headers):
    """Brief generation creates a persisted handoff brief with resolved evidence."""
    await init_db()
    project = await _seed_project("Brief Generation")
    insight = await _seed_insight(project.id)
    rec = await _seed_recommendation(project.id)
    existing_brief = DesignBrief(
        id=str(uuid.uuid4()),
        project_id=project.id,
        title="Earlier Brief",
        content="Existing brief content",
        source_insight_ids="[]",
        source_recommendation_ids="[]",
    )
    async with async_session() as db:
        db.add(existing_brief)
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/interfaces/handoff/brief",
            headers=auth_headers,
            json={"project_id": project.id},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["brief_id"]
    assert payload["brief"]["source_findings"][0]["id"] == insight.id
    assert payload["brief"]["recommendations"][0]["id"] == rec.id


@pytest.mark.asyncio
async def test_handoff_dev_spec_resolves_source_findings(auth_headers):
    """Developer specs include deterministic content and resolved evidence."""
    await init_db()
    project = await _seed_project("Dev Spec")
    rec = await _seed_recommendation(project.id)
    screen = DesignScreen(
        id=str(uuid.uuid4()),
        project_id=project.id,
        title="Onboarding Screen",
        description="Screen description",
        prompt="Design a simpler onboarding screen",
        device_type="DESKTOP",
        html_content="<main><h1>Welcome</h1></main>",
        source_findings=json.dumps([rec.id]),
    )
    async with async_session() as db:
        db.add(screen)
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/interfaces/handoff/dev-spec",
            headers=auth_headers,
            json={"screen_id": screen.id},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert "Developer Spec" in payload["content"]
    assert "(provisional)" in payload["content"]
    assert payload["dev_spec"]["source_findings"][0]["id"] == rec.id
    assert payload["dev_spec"]["source_findings"][0]["research_validity"]["status"] == "provisional"
    assert payload["dev_spec"]["research_validity"]["report_allowed"] is False


@pytest.mark.asyncio
async def test_figma_import_creates_design_screen(auth_headers, monkeypatch):
    """Configured Figma import persists an inspectable DesignScreen record."""
    await init_db()
    project = await _seed_project("Figma Import")
    await _seed_interface_config(project.id, figma_api_token="figma-test-token")

    from app.services.figma_service import figma_service

    monkeypatch.setattr(figma_service, "get_file", AsyncMock(return_value={"name": "Checkout"}))
    monkeypatch.setattr(
        figma_service,
        "get_components",
        AsyncMock(return_value={"meta": {"components": [{"name": "Button", "key": "btn"}]}}),
    )
    monkeypatch.setattr(
        figma_service,
        "get_styles",
        AsyncMock(return_value={"meta": {"styles": [{"name": "Primary", "key": "pri", "style_type": "FILL"}]}}),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/interfaces/figma/import",
            headers=auth_headers,
            json={
                "project_id": project.id,
                "figma_url": "https://www.figma.com/design/ABC123/Checkout",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["screens_imported"] == 1
    assert payload["screens"][0]["figma_file_key"] == "ABC123"


@pytest.mark.asyncio
async def test_figma_components_endpoint_matches_frontend_helper(auth_headers, monkeypatch):
    """The frontend components helper has a real backend endpoint."""
    await init_db()
    project = await _seed_project("Figma Components")
    await _seed_interface_config(project.id, figma_api_token="figma-test-token")

    from app.services.figma_service import figma_service

    monkeypatch.setattr(
        figma_service,
        "get_components",
        AsyncMock(return_value={"meta": {"components": [{"name": "Card", "key": "card"}]}}),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/interfaces/figma/components/ABC123?project_id={project.id}",
            headers=auth_headers,
        )

    assert response.status_code == 200
    assert response.json()["components"][0]["name"] == "Card"


@pytest.mark.asyncio
async def test_interfaces_configuration_is_project_scoped(auth_headers):
    """Figma/Stitch credentials are stored per project and do not mutate global settings."""
    await init_db()
    project_a = await _seed_project("Interface Config A")
    project_b = await _seed_project("Interface Config B")
    settings.figma_api_token = ""
    settings.stitch_api_key = ""

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        configure_response = await ac.post(
            "/api/interfaces/configure/figma",
            headers=auth_headers,
            json={"project_id": project_a.id, "api_token": "figma-project-a"},
        )
        status_a = await ac.get(
            f"/api/interfaces/status?project_id={project_a.id}",
            headers=auth_headers,
        )
        status_b = await ac.get(
            f"/api/interfaces/status?project_id={project_b.id}",
            headers=auth_headers,
        )

    assert configure_response.status_code == 200
    assert configure_response.json()["project_id"] == project_a.id
    assert settings.figma_api_token == ""
    assert settings.stitch_api_key == ""
    assert status_a.json()["figma_configured"] is True
    assert status_b.json()["figma_configured"] is False


@pytest.mark.asyncio
async def test_figma_file_helpers_require_project_id(auth_headers):
    """Figma account reads require an active project and project-owned credentials."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            "/api/interfaces/figma/components/ABC123",
            headers=auth_headers,
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "project_id is required"


@pytest.mark.asyncio
async def test_mock_endpoints_are_blocked_in_public_profile(auth_headers):
    """Public runtime profile disables mock endpoints unless explicitly enabled."""
    await init_db()
    project = await _seed_project("Public Mock")
    settings.istara_runtime_profile = "public"
    settings.interfaces_mock_endpoints_enabled = False

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/interfaces/mock/generate",
            headers=auth_headers,
            json={"project_id": project.id, "prompt": "Mock screen"},
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_query_style_evidence_chain_includes_design_nodes(auth_headers):
    """Query-style evidence-chain callers receive the extended chain within the active project."""
    await init_db()
    project = await _seed_project("Evidence Chain")
    rec = await _seed_recommendation(project.id)
    screen = DesignScreen(
        id=str(uuid.uuid4()),
        project_id=project.id,
        title="Evidence Screen",
        description="",
        prompt="",
        device_type="DESKTOP",
        source_findings=json.dumps([rec.id]),
    )
    decision = DesignDecision(
        id=str(uuid.uuid4()),
        project_id=project.id,
        text="Decision text",
        recommendation_ids=json.dumps([rec.id]),
        screen_ids=json.dumps([screen.id]),
    )
    async with async_session() as db:
        db.add(screen)
        db.add(decision)
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/findings/evidence-chain?finding_type=recommendation&finding_id={rec.id}&project_id={project.id}",
            headers=auth_headers,
        )

    assert response.status_code == 200
    chain = response.json()["chain"]
    assert chain["design_decision"][0]["id"] == decision.id
    assert chain["design_screen"][0]["id"] == screen.id
