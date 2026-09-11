"""Tests for DGM-H archive evolution and API contracts."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.core.auth import create_token
from app.core.dgmh_archive import dgmh_archive
from app.core.improvement_governance import improvement_governance
from app.main import app
from app.models.database import async_session, init_db
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


async def create_project(project_id: str, name: str = "DGM-H Test Project") -> None:
    async with async_session() as db:
        db.add(Project(id=project_id, name=name))
        await db.commit()


@pytest.mark.asyncio
async def test_governance_proposals_create_and_sync_dgmh_archive_variants():
    await init_db()
    source_id = f"dgmh_governance_{uuid.uuid4().hex[:12]}"
    target_system = f"dgmh-target-{uuid.uuid4().hex[:8]}"

    proposal = await improvement_governance.create_proposal(
        source_system="manual",
        source_id=source_id,
        project_id="project-dgmh-governance",
        title="Tune routing threshold",
        summary="Measure and promote a routing parameter change.",
        affected_surfaces=["configs", "orchestration"],
        proposed_change={
            "target_system": target_system,
            "parameter_path": "task_router.min_confidence",
        },
        rollback_plan={"strategy": "restore previous threshold"},
        metrics_before={"score": 0.6},
        metrics_after={"score": 0.72},
        improvement_score=0.12,
        confidence=0.8,
    )

    variants = await dgmh_archive.list_variants(
        source_system="manual",
        project_id="project-dgmh-governance",
        target_system=target_system,
    )
    variant = next(
        item for item in variants if item["governance_proposal_id"] == proposal.id
    )
    assert variant["status"] == "candidate"
    assert variant["score"] == 0.12
    assert variant["root_id"] == variant["id"]

    approved = await improvement_governance.approve_proposal(
        proposal.id, reviewer_id="tester"
    )
    assert approved["proposal"]["status"] == "approved"
    synced = await dgmh_archive.get_variant(variant["id"])
    assert synced is not None
    assert synced.status == "approved"

    applied = await improvement_governance.apply_proposal(
        proposal.id,
        actor_id="tester",
        evidence={"verification": "unit"},
    )
    assert applied["proposal"]["status"] == "applied"
    synced = await dgmh_archive.get_variant(variant["id"])
    assert synced is not None
    assert synced.status == "active"

    evaluated = await improvement_governance.record_evaluation(
        proposal.id,
        metrics_before={"score": 0.6},
        metrics_after={"score": 0.75},
        passed=True,
        evidence={"samples": [0.73, 0.77]},
    )
    assert evaluated["proposal"]["evaluation_runs"]
    synced = await dgmh_archive.get_variant(variant["id"])
    assert synced is not None
    assert synced.get_evaluation()
    assert synced.score == pytest.approx(0.15)

    reverted = await improvement_governance.revert_proposal(
        proposal.id,
        actor_id="tester",
        reason="rollback test",
    )
    assert reverted["proposal"]["status"] == "reverted"
    synced = await dgmh_archive.get_variant(variant["id"])
    assert synced is not None
    assert synced.status == "reverted"


@pytest.mark.asyncio
async def test_dgmh_archive_selects_parents_with_ucb_style_scores():
    await init_db()
    target = f"parent-select-{uuid.uuid4().hex[:8]}"

    high = await dgmh_archive.register_variant(
        source_system="test",
        source_id=f"high-{uuid.uuid4().hex[:8]}",
        target_system=target,
        mutation_surface="configs",
        artifact_kind="parameter_variant",
        title="High scoring variant",
        score=0.4,
        confidence=0.9,
    )
    low = await dgmh_archive.register_variant(
        source_system="test",
        source_id=f"low-{uuid.uuid4().hex[:8]}",
        target_system=target,
        mutation_surface="configs",
        artifact_kind="parameter_variant",
        title="Lower scoring variant",
        score=0.1,
        confidence=0.9,
    )

    parent = await dgmh_archive.select_parent(
        target_system=target,
        mutation_surface="configs",
        artifact_kind="parameter_variant",
    )

    assert parent is not None
    assert parent["id"] == high.id
    assert low.parent_id == high.id


@pytest.mark.asyncio
async def test_dgmh_archive_api_contract_and_admin_guard(auth_headers):
    await init_db()
    settings.team_mode = True
    target = f"api-dgmh-{uuid.uuid4().hex[:8]}"
    project_id = f"dgmh-api-{uuid.uuid4().hex[:8]}"
    other_project_id = f"dgmh-api-other-{uuid.uuid4().hex[:8]}"
    await create_project(project_id)
    await create_project(other_project_id, "Other DGM-H Test Project")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        missing_scope = await ac.get("/api/dgmh-archive/variants", headers=auth_headers)
        assert missing_scope.status_code == 400
        assert missing_scope.json()["detail"] == "project_id is required"

        unknown_project = await ac.post(
            "/api/dgmh-archive/variants",
            headers=auth_headers,
            json={
                "project_id": "missing-dgmh-project",
                "title": "Unknown project archive candidate",
            },
        )
        assert unknown_project.status_code == 404

        created = await ac.post(
            "/api/dgmh-archive/variants",
            headers=auth_headers,
            json={
                "source_system": "manual",
                "source_id": f"api-{uuid.uuid4().hex[:8]}",
                "project_id": project_id,
                "target_system": target,
                "mutation_surface": "configs",
                "artifact_kind": "parameter_variant",
                "title": "Manual archive candidate",
                "mutation": {
                    "parameter_path": "agent.max_parallel_tasks",
                    "proposed_value": 4,
                },
                "rollback_plan": {"strategy": "restore previous value"},
                "score": 0.08,
                "confidence": 0.7,
            },
        )
        assert created.status_code == 200
        variant_id = created.json()["variant"]["id"]

        approved = await ac.post(
            f"/api/dgmh-archive/variants/{variant_id}/approve?project_id={project_id}",
            headers=auth_headers,
            json={"reason": "reviewed"},
        )
        assert approved.status_code == 200
        assert approved.json()["variant"]["status"] == "approved"

        applied = await ac.post(
            f"/api/dgmh-archive/variants/{variant_id}/apply?project_id={project_id}",
            headers=auth_headers,
            json={"evidence": {"command": "pytest tests/test_dgmh_archive.py"}},
        )
        assert applied.status_code == 200
        assert applied.json()["variant"]["status"] == "active"

        listed = await ac.get(
            f"/api/dgmh-archive/variants?project_id={project_id}&target_system={target}",
            headers=auth_headers,
        )
        assert listed.status_code == 200
        assert any(item["id"] == variant_id for item in listed.json()["variants"])

        other_listed = await ac.get(
            f"/api/dgmh-archive/variants?project_id={other_project_id}&target_system={target}",
            headers=auth_headers,
        )
        assert other_listed.status_code == 200
        assert all(item["id"] != variant_id for item in other_listed.json()["variants"])

        summary = await ac.get(
            f"/api/dgmh-archive/summary?project_id={project_id}", headers=auth_headers
        )
        assert summary.status_code == 200
        assert summary.json()["total"] >= 1

        wrong_scope = await ac.post(
            f"/api/dgmh-archive/variants/{variant_id}/confirm?project_id={other_project_id}",
            headers=auth_headers,
            json={"reason": "wrong project"},
        )
        assert wrong_scope.status_code == 404

    token = create_token("user2", "researcher", "researcher")
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        blocked = await ac.get(
            "/api/dgmh-archive/summary",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert blocked.status_code == 403
