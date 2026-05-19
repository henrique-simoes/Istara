"""Tests for Findings API routes — nuggets, facts, insights, recommendations."""

import json
import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.models.database import async_session, init_db
from app.core.auth import create_token
from app.models.design_screen import DesignDecision
from app.models.finding import Fact, Insight, Nugget, Recommendation
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


# ---------------------------------------------------------------------------
# Nuggets
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_nuggets_list_returns_list(auth_headers):
    """GET /api/findings/nuggets returns a list."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/findings/nuggets?project_id=test-project", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_nuggets_requires_auth():
    """Nuggets endpoint requires authentication."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/findings/nuggets")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_nugget_creation_normalizes_integrity_fields(auth_headers):
    """New and legacy nuggets expose source_location and tags for research integrity."""
    await init_db()
    project_id = f"findings-project-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Findings Integrity Project"))
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/findings/nuggets",
            headers=auth_headers,
            json={
                "project_id": project_id,
                "text": "Participants want clearer onboarding.",
                "source": "interview-01",
            },
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["source_location"] == "interview-01"
    assert payload["tags"] == ["untagged"]


# ---------------------------------------------------------------------------
# Facts
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_facts_list_returns_list(auth_headers):
    """GET /api/findings/facts returns a list."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/findings/facts?project_id=test-project", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_facts_requires_auth():
    """Facts endpoint requires authentication."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/findings/facts")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Insights
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_insights_list_returns_list(auth_headers):
    """GET /api/findings/insights returns a list."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/findings/insights?project_id=test-project", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_recommendations_list_returns_list(auth_headers):
    """GET /api/findings/recommendations returns a list."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/findings/recommendations?project_id=test-project", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_findings_list_routes_require_project_id_even_for_admin(auth_headers):
    """Project-facing findings lists must not fall back to global admin reads."""
    await init_db()
    paths = [
        "/api/findings/nuggets",
        "/api/findings/facts",
        "/api/findings/insights",
        "/api/findings/recommendations",
        "/api/findings/design-decisions",
    ]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        for path in paths:
            response = await ac.get(path, headers=auth_headers)
            assert response.status_code == 422
            assert response.json()["detail"] == "project_id is required"


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_findings_summary_returns_dict(auth_headers):
    """GET /api/findings/summary/{project_id} returns a dict."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/findings/summary/test-project", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), dict)


# ---------------------------------------------------------------------------
# Evidence Chain
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_evidence_chain_returns_list(auth_headers):
    """GET /api/findings/{type}/{id}/evidence-chain returns a list or appropriate error."""
    await init_db()
    project_id = f"evidence-empty-project-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Evidence Empty Project"))
        await db.commit()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/findings/nuggets/non-existent-id/evidence-chain?project_id={project_id}",
            headers=auth_headers,
        )
        # 200 if endpoint returns empty list, 400 if ID validation fails
        assert response.status_code in (200, 400, 404)
        if response.status_code == 200:
            assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_findings_by_id_routes_require_matching_active_project(auth_headers):
    await init_db()
    project_a = f"findings-project-a-{uuid.uuid4()}"
    project_b = f"findings-project-b-{uuid.uuid4()}"
    nugget_id = str(uuid.uuid4())
    fact_id = str(uuid.uuid4())
    insight_id = str(uuid.uuid4())
    rec_id = str(uuid.uuid4())
    design_decision_id = str(uuid.uuid4())
    delete_ids = {
        "nuggets": str(uuid.uuid4()),
        "facts": str(uuid.uuid4()),
        "insights": str(uuid.uuid4()),
        "recommendations": str(uuid.uuid4()),
        "design-decisions": str(uuid.uuid4()),
    }

    async with async_session() as db:
        db.add_all(
            [
                Project(id=project_a, name="Project A"),
                Project(id=project_b, name="Project B"),
                Nugget(
                    id=nugget_id,
                    project_id=project_a,
                    text="Project A nugget",
                    source="interview-a",
                ),
                Fact(
                    id=fact_id,
                    project_id=project_a,
                    text="Project A fact",
                    nugget_ids=json.dumps([]),
                ),
                Insight(
                    id=insight_id,
                    project_id=project_a,
                    text="Project A insight",
                    fact_ids=json.dumps([fact_id]),
                ),
                Recommendation(
                    id=rec_id,
                    project_id=project_a,
                    text="Project A recommendation",
                    insight_ids=json.dumps([insight_id]),
                ),
                DesignDecision(
                    id=design_decision_id,
                    project_id=project_a,
                    text="Project A design decision",
                    recommendation_ids=json.dumps([rec_id]),
                ),
                Nugget(
                    id=delete_ids["nuggets"],
                    project_id=project_a,
                    text="Delete nugget",
                    source="interview-a",
                ),
                Fact(
                    id=delete_ids["facts"],
                    project_id=project_a,
                    text="Delete fact",
                    nugget_ids=json.dumps([]),
                ),
                Insight(
                    id=delete_ids["insights"],
                    project_id=project_a,
                    text="Delete insight",
                    fact_ids=json.dumps([]),
                ),
                Recommendation(
                    id=delete_ids["recommendations"],
                    project_id=project_a,
                    text="Delete recommendation",
                    insight_ids=json.dumps([]),
                ),
                DesignDecision(
                    id=delete_ids["design-decisions"],
                    project_id=project_a,
                    text="Delete design decision",
                ),
            ]
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        missing_scope = await ac.get(
            f"/api/findings/fact/{fact_id}/evidence-chain",
            headers=auth_headers,
        )
        wrong_scope = await ac.get(
            f"/api/findings/fact/{fact_id}/evidence-chain?project_id={project_b}",
            headers=auth_headers,
        )
        correct_scope = await ac.get(
            f"/api/findings/fact/{fact_id}/evidence-chain?project_id={project_a}",
            headers=auth_headers,
        )
        query_missing_scope = await ac.get(
            f"/api/findings/evidence-chain?finding_type=fact&finding_id={fact_id}",
            headers=auth_headers,
        )
        query_correct_scope = await ac.get(
            f"/api/findings/evidence-chain?finding_type=fact&finding_id={fact_id}&project_id={project_a}",
            headers=auth_headers,
        )
        extended_wrong_scope = await ac.get(
            f"/api/findings/design_decision/{design_decision_id}/evidence-chain-extended?project_id={project_b}",
            headers=auth_headers,
        )
        extended_correct_scope = await ac.get(
            f"/api/findings/design_decision/{design_decision_id}/evidence-chain-extended?project_id={project_a}",
            headers=auth_headers,
        )
        link_missing_scope = await ac.patch(
            f"/api/findings/fact/{fact_id}/link",
            headers=auth_headers,
            json={"link_id": nugget_id, "link_type": "nugget"},
        )
        link_wrong_scope = await ac.patch(
            f"/api/findings/fact/{fact_id}/link?project_id={project_b}",
            headers=auth_headers,
            json={"link_id": nugget_id, "link_type": "nugget"},
        )
        link_correct_scope = await ac.patch(
            f"/api/findings/fact/{fact_id}/link?project_id={project_a}",
            headers=auth_headers,
            json={"link_id": nugget_id, "link_type": "nugget"},
        )

        assert missing_scope.status_code == 422
        assert missing_scope.json()["detail"] == "project_id is required"
        assert wrong_scope.status_code == 404
        assert correct_scope.status_code == 200
        assert correct_scope.json()["chain"]["fact"][0]["id"] == fact_id
        assert query_missing_scope.status_code == 422
        assert query_correct_scope.status_code == 200
        assert extended_wrong_scope.status_code == 404
        assert extended_correct_scope.status_code == 200
        assert extended_correct_scope.json()["chain"]["design_decision"][0]["id"] == design_decision_id
        assert link_missing_scope.status_code == 422
        assert link_wrong_scope.status_code == 404
        assert link_correct_scope.status_code == 200

        for plural, record_id in delete_ids.items():
            missing_delete = await ac.delete(
                f"/api/findings/{plural}/{record_id}",
                headers=auth_headers,
            )
            wrong_delete = await ac.delete(
                f"/api/findings/{plural}/{record_id}?project_id={project_b}",
                headers=auth_headers,
            )
            correct_delete = await ac.delete(
                f"/api/findings/{plural}/{record_id}?project_id={project_a}",
                headers=auth_headers,
            )

            assert missing_delete.status_code == 422
            assert wrong_delete.status_code == 404
            assert correct_delete.status_code == 204


@pytest.mark.asyncio
async def test_evidence_chain_filters_linked_findings_to_project(auth_headers):
    """Evidence-chain traversal must ignore stale links to another project."""
    await init_db()
    project_id = f"evidence-project-{uuid.uuid4()}"
    other_project_id = f"other-evidence-project-{uuid.uuid4()}"
    in_scope_nugget_id = str(uuid.uuid4())
    out_of_scope_nugget_id = str(uuid.uuid4())
    fact_id = str(uuid.uuid4())

    async with async_session() as db:
        db.add_all([
            Project(id=project_id, name="Evidence Project"),
            Project(id=other_project_id, name="Other Evidence Project"),
            Nugget(
                id=in_scope_nugget_id,
                project_id=project_id,
                text="In-scope evidence",
                source="interview-a",
            ),
            Nugget(
                id=out_of_scope_nugget_id,
                project_id=other_project_id,
                text="Out-of-scope evidence",
                source="interview-b",
            ),
            Fact(
                id=fact_id,
                project_id=project_id,
                text="Only the in-scope nugget should be returned.",
                nugget_ids=json.dumps([in_scope_nugget_id, out_of_scope_nugget_id]),
            ),
        ])
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/findings/fact/{fact_id}/evidence-chain?project_id={project_id}",
            headers=auth_headers,
        )

    assert response.status_code == 200
    nuggets = response.json()["chain"]["nugget"]
    assert [nugget["id"] for nugget in nuggets] == [in_scope_nugget_id]
