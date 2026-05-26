"""Tests for Findings API routes — nuggets, facts, insights, recommendations."""

import json
import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from app.main import app
from app.config import settings
from app.models.database import async_session, init_db
from app.core.auth import create_token
from app.models.design_screen import DesignDecision, DesignScreen
from app.models.code_application import CodeApplication
from app.models.finding import Fact, Insight, Nugget, Recommendation
from app.models.project import Project
from app.models.research_validity import EvidenceUnit, ResearchEvidenceEdge
from app.models.task import Task, TaskStatus


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


def _add_accepted_nugget_support(
    db,
    *,
    project_id: str,
    task_id: str,
    nugget_id: str,
    source_text: str,
) -> None:
    evidence_unit_id = str(uuid.uuid4())
    db.add(
        EvidenceUnit(
            id=evidence_unit_id,
            project_id=project_id,
            task_id=task_id,
            source_id=f"task:{task_id}:nugget:{nugget_id}",
            stable_id=f"test-unit:{evidence_unit_id}",
            unit_index=0,
            unit_type="source_span",
            source_type="test_fixture",
            method="test",
            phase="discover",
            source_text=source_text,
        )
    )
    db.add(
        ResearchEvidenceEdge(
            id=str(uuid.uuid4()),
            project_id=project_id,
            source_type="nugget",
            source_id=nugget_id,
            relation="grounded_in",
            target_type="evidence_unit",
            target_id=evidence_unit_id,
            evidence_unit_id=evidence_unit_id,
            task_id=task_id,
        )
    )
    db.add(
        CodeApplication(
            id=str(uuid.uuid4()),
            project_id=project_id,
            task_id=task_id,
            code_id="accepted-research-evidence",
            evidence_unit_id=evidence_unit_id,
            source_text=source_text,
            promotion_status="accepted",
            reliability_status="accepted",
            reconciliation_status="accepted",
        )
    )


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
    assert payload["research_validity"]["status"] == "provisional"
    assert payload["research_validity"]["report_allowed"] is False

    async with async_session() as db:
        units = (
            await db.execute(
                select(EvidenceUnit).where(
                    EvidenceUnit.project_id == project_id,
                    EvidenceUnit.source_id == f"nugget:{payload['id']}",
                )
            )
        ).scalars().all()
        edges = (
            await db.execute(
                select(ResearchEvidenceEdge).where(
                    ResearchEvidenceEdge.project_id == project_id,
                    ResearchEvidenceEdge.source_type == "nugget",
                    ResearchEvidenceEdge.source_id == payload["id"],
                    ResearchEvidenceEdge.relation == "grounded_in",
                )
            )
        ).scalars().all()

    assert len(units) == 1
    assert units[0].source_text == "Participants want clearer onboarding."
    assert units[0].source_type == "manual_finding"
    assert units[0].unit_type == "candidate_atom"
    assert units[0].to_dict()["metadata"]["candidate_only"] is True
    assert units[0].task_id is None
    assert len(edges) == 1
    assert edges[0].evidence_unit_id == units[0].id


@pytest.mark.asyncio
async def test_manual_atomic_chain_creation_rejects_cross_project_links(auth_headers):
    """Manual Atomic artifacts cannot link evidence from outside the active project."""
    await init_db()
    project_id = f"manual-link-project-{uuid.uuid4()}"
    foreign_project_id = f"manual-link-foreign-{uuid.uuid4()}"
    foreign_nugget_id = str(uuid.uuid4())
    foreign_fact_id = str(uuid.uuid4())
    foreign_insight_id = str(uuid.uuid4())
    foreign_rec_id = str(uuid.uuid4())
    foreign_screen_id = str(uuid.uuid4())

    async with async_session() as db:
        db.add(Project(id=project_id, name="Manual Link Project"))
        db.add(Project(id=foreign_project_id, name="Foreign Manual Link Project"))
        db.add(
            Nugget(
                id=foreign_nugget_id,
                project_id=foreign_project_id,
                text="Foreign nugget",
                source="foreign",
            )
        )
        db.add(Fact(id=foreign_fact_id, project_id=foreign_project_id, text="Foreign fact"))
        db.add(
            Insight(
                id=foreign_insight_id,
                project_id=foreign_project_id,
                text="Foreign insight",
            )
        )
        db.add(
            Recommendation(
                id=foreign_rec_id,
                project_id=foreign_project_id,
                text="Foreign recommendation",
            )
        )
        db.add(
            DesignScreen(
                id=foreign_screen_id,
                project_id=foreign_project_id,
                title="Foreign screen",
                description="Foreign screen",
                prompt="Foreign screen",
            )
        )
        await db.commit()

    cases = [
        (
            "/api/findings/facts",
            {"project_id": project_id, "text": "Fact", "nugget_ids": [foreign_nugget_id]},
            "nugget_ids",
        ),
        (
            "/api/findings/insights",
            {"project_id": project_id, "text": "Insight", "fact_ids": [foreign_fact_id]},
            "fact_ids",
        ),
        (
            "/api/findings/recommendations",
            {"project_id": project_id, "text": "Recommendation", "insight_ids": [foreign_insight_id]},
            "insight_ids",
        ),
        (
            "/api/findings/design-decisions",
            {
                "project_id": project_id,
                "text": "Decision",
                "recommendation_ids": [foreign_rec_id],
                "screen_ids": [foreign_screen_id],
            },
            "recommendation_ids",
        ),
    ]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        for url, payload, field_name in cases:
            response = await ac.post(url, headers=auth_headers, json=payload)
            assert response.status_code == 422
            assert field_name in response.json()["detail"]


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


@pytest.mark.asyncio
async def test_evidence_chain_includes_research_validity_gate(auth_headers):
    """Evidence-chain diagnostics must show when linked task evidence is not reportable."""
    await init_db()
    project_id = f"evidence-validity-project-{uuid.uuid4()}"
    task_id = str(uuid.uuid4())
    nugget_id = str(uuid.uuid4())
    fact_id = str(uuid.uuid4())

    async with async_session() as db:
        db.add(Project(id=project_id, name="Evidence Validity Project"))
        db.add(
            Task(
                id=task_id,
                project_id=project_id,
                title="Blocked evidence chain",
                status=TaskStatus.IN_REVIEW,
                review_state="awaiting_review",
            )
        )
        db.add(
            Nugget(
                id=nugget_id,
                project_id=project_id,
                task_id=task_id,
                text="Participant could not find the invite flow.",
                source="interview-a",
            )
        )
        db.add(
            Fact(
                id=fact_id,
                project_id=project_id,
                task_id=task_id,
                text="Invite flow discovery failed.",
                nugget_ids=json.dumps([nugget_id]),
            )
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        blocked = await ac.get(
            f"/api/findings/fact/{fact_id}/evidence-chain?project_id={project_id}",
            headers=auth_headers,
        )

    assert blocked.status_code == 200
    diagnostics = blocked.json()["diagnostics"]["research_validity"]
    assert diagnostics["task_ids"] == [task_id]
    assert diagnostics["report_allowed"] is False
    assert "no coded evidence applications" in diagnostics["task_gates"][task_id]["report_block_reason"]

    async with async_session() as db:
        _add_accepted_nugget_support(
            db,
            project_id=project_id,
            task_id=task_id,
            nugget_id=nugget_id,
            source_text="Participant could not find the invite flow.",
        )
        await db.commit()

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        still_blocked = await ac.get(
            f"/api/findings/fact/{fact_id}/evidence-chain?project_id={project_id}",
            headers=auth_headers,
        )

    assert still_blocked.status_code == 200
    still_blocked_gate = still_blocked.json()["diagnostics"]["research_validity"]
    assert still_blocked_gate["report_allowed"] is False
    assert still_blocked_gate["task_gates"][task_id]["report_block_reason"] == "Task is not a human-approved Done task."

    async with async_session() as db:
        task = await db.get(Task, task_id)
        task.status = TaskStatus.DONE
        task.review_state = "approved"
        await db.commit()

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        allowed = await ac.get(
            f"/api/findings/fact/{fact_id}/evidence-chain?project_id={project_id}",
            headers=auth_headers,
        )

    assert allowed.status_code == 200
    assert allowed.json()["diagnostics"]["research_validity"]["report_allowed"] is True


@pytest.mark.asyncio
async def test_evidence_chain_blocks_taskless_legacy_findings(auth_headers):
    """Taskless Atomic Research rows remain provisional even when chain links exist."""
    await init_db()
    project_id = f"evidence-taskless-project-{uuid.uuid4()}"
    nugget_id = str(uuid.uuid4())
    fact_id = str(uuid.uuid4())

    async with async_session() as db:
        db.add(Project(id=project_id, name="Evidence Taskless Project"))
        db.add(
            Nugget(
                id=nugget_id,
                project_id=project_id,
                text="Participant could not find account recovery.",
                source="legacy-import",
            )
        )
        db.add(
            Fact(
                id=fact_id,
                project_id=project_id,
                text="Account recovery is hard to discover.",
                nugget_ids=json.dumps([nugget_id]),
            )
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/findings/fact/{fact_id}/evidence-chain?project_id={project_id}",
            headers=auth_headers,
        )

    assert response.status_code == 200
    gate = response.json()["diagnostics"]["research_validity"]
    assert gate["task_ids"] == []
    assert set(gate["taskless_finding_ids"]) == {nugget_id, fact_id}
    assert gate["report_allowed"] is False
    assert "taskless or legacy/unverified findings" in gate["report_block_reason"]


@pytest.mark.asyncio
async def test_finding_lists_surface_provisional_validity_until_reportable(auth_headers):
    """Finding lists must not make agent/task outputs look accepted before gates pass."""
    await init_db()
    project_id = f"finding-validity-list-project-{uuid.uuid4()}"
    task_id = str(uuid.uuid4())
    nugget_id = str(uuid.uuid4())

    async with async_session() as db:
        db.add(Project(id=project_id, name="Finding Validity List Project"))
        db.add(
            Task(
                id=task_id,
                project_id=project_id,
                title="Provisional agent finding",
                status=TaskStatus.IN_REVIEW,
                review_state="awaiting_review",
            )
        )
        db.add(
            Nugget(
                id=nugget_id,
                project_id=project_id,
                task_id=task_id,
                text="Participant stalled when asked to invite a teammate.",
                source="interview-a",
            )
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        provisional = await ac.get(
            f"/api/findings/nuggets?project_id={project_id}",
            headers=auth_headers,
        )

    assert provisional.status_code == 200
    provisional_gate = next(
        row["research_validity"] for row in provisional.json() if row["id"] == nugget_id
    )
    assert provisional_gate["status"] == "provisional"
    assert provisional_gate["report_allowed"] is False
    assert "no coded evidence applications" in provisional_gate["reason"]

    async with async_session() as db:
        task = await db.get(Task, task_id)
        task.status = TaskStatus.DONE
        task.review_state = "approved"
        _add_accepted_nugget_support(
            db,
            project_id=project_id,
            task_id=task_id,
            nugget_id=nugget_id,
            source_text="Participant stalled when asked to invite a teammate.",
        )
        await db.commit()

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        accepted = await ac.get(
            f"/api/findings/nuggets?project_id={project_id}",
            headers=auth_headers,
        )

    assert accepted.status_code == 200
    accepted_gate = next(row["research_validity"] for row in accepted.json() if row["id"] == nugget_id)
    assert accepted_gate["status"] == "accepted"
    assert accepted_gate["report_allowed"] is True
    assert accepted_gate["done_approved"] is True
    assert accepted_gate["accepted_code_application_count"] == 1


@pytest.mark.asyncio
async def test_design_decisions_remain_provisional_until_source_findings_are_reportable(auth_headers):
    """Design decisions cannot look accepted while linked source findings are provisional."""
    await init_db()
    project_id = f"design-provisional-{uuid.uuid4()}"
    rec_id = f"rec-{uuid.uuid4()}"
    decision_id = f"decision-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Design Provisional Project"))
        db.add(
            Recommendation(
                id=rec_id,
                project_id=project_id,
                text="Reduce setup friction in the invite flow.",
                insight_ids=json.dumps([]),
            )
        )
        db.add(
            DesignDecision(
                id=decision_id,
                project_id=project_id,
                text="Use a guided teammate invite panel.",
                recommendation_ids=json.dumps([rec_id]),
            )
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/findings/design-decisions?project_id={project_id}",
            headers=auth_headers,
        )

    assert response.status_code == 200
    gate = next(row["research_validity"] for row in response.json() if row["id"] == decision_id)
    assert gate["status"] == "provisional"
    assert gate["report_allowed"] is False
    assert gate["source_finding_ids"] == [rec_id]
    assert gate["blocked_source_ids"] == [rec_id]
    assert gate["policy"] == "design_decision_visibility_requires_accepted_spine_sources"


@pytest.mark.asyncio
async def test_design_decisions_accept_only_from_done_source_findings(auth_headers):
    """Design decisions become accepted only when linked findings pass task/report gates."""
    await init_db()
    project_id = f"design-accepted-{uuid.uuid4()}"
    task_id = f"task-{uuid.uuid4()}"
    nugget_id = f"nugget-{uuid.uuid4()}"
    fact_id = f"fact-{uuid.uuid4()}"
    insight_id = f"insight-{uuid.uuid4()}"
    rec_id = f"rec-{uuid.uuid4()}"
    decision_id = f"decision-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Design Accepted Project"))
        db.add(
            Task(
                id=task_id,
                project_id=project_id,
                title="Approve invite-flow recommendation",
                status=TaskStatus.DONE,
                review_state="approved",
            )
        )
        db.add(
            Nugget(
                id=nugget_id,
                project_id=project_id,
                task_id=task_id,
                text="Participants stalled when inviting teammates.",
                source="interview",
            )
        )
        db.add(
            Fact(
                id=fact_id,
                project_id=project_id,
                task_id=task_id,
                text="Invite flow stalls during teammate setup.",
                nugget_ids=json.dumps([nugget_id]),
            )
        )
        db.add(
            Insight(
                id=insight_id,
                project_id=project_id,
                task_id=task_id,
                text="Team setup needs guided invite support.",
                fact_ids=json.dumps([fact_id]),
            )
        )
        db.add(
            Recommendation(
                id=rec_id,
                project_id=project_id,
                task_id=task_id,
                text="Reduce setup friction in the invite flow.",
                insight_ids=json.dumps([insight_id]),
            )
        )
        _add_accepted_nugget_support(
            db,
            project_id=project_id,
            task_id=task_id,
            nugget_id=nugget_id,
            source_text="Participants stalled when inviting teammates.",
        )
        db.add(
            DesignDecision(
                id=decision_id,
                project_id=project_id,
                text="Use a guided teammate invite panel.",
                recommendation_ids=json.dumps([rec_id]),
            )
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/findings/design-decisions?project_id={project_id}",
            headers=auth_headers,
        )

    assert response.status_code == 200
    gate = next(row["research_validity"] for row in response.json() if row["id"] == decision_id)
    assert gate["status"] == "accepted"
    assert gate["report_allowed"] is True
    assert gate["accepted_source_ids"] == [rec_id]
    assert gate["blocked_source_ids"] == []
