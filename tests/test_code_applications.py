"""Tests for Code Applications API routes — list, pending, review, and fail-closed bulk action."""

import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from app.main import app
from app.config import settings
from app.models.code_application import CodeApplication
from app.models.research_validity import CodingRun, ReconciliationDecision
from app.models.project import Project
from app.models.database import async_session, init_db
from app.core.auth import create_token


@pytest.fixture(autouse=True)
def reset_settings():
    original_team_mode = settings.team_mode
    original_jwt_secret = settings.jwt_secret
    original_synthetic_reconciliation = (
        settings.research_validity_synthetic_reconciliation_enabled
    )
    yield
    settings.team_mode = original_team_mode
    settings.jwt_secret = original_jwt_secret
    settings.research_validity_synthetic_reconciliation_enabled = (
        original_synthetic_reconciliation
    )


@pytest.fixture
def auth_headers():
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    token = create_token("user1", "testuser", "admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_code_apps_list_returns_response(auth_headers):
    """GET /api/code-applications/{project_id} returns code applications."""
    await init_db()
    project_id = f"code-list-{uuid.uuid4().hex[:8]}"
    other_project_id = f"code-list-other-{uuid.uuid4().hex[:8]}"
    visible_id = str(uuid.uuid4())
    hidden_id = str(uuid.uuid4())
    async with async_session() as db:
        db.add_all(
            [
                Project(id=project_id, name="Code Applications List"),
                Project(id=other_project_id, name="Other Code Applications"),
                CodeApplication(
                    id=visible_id,
                    project_id=project_id,
                    code_id="visible-code",
                    source_text="Visible project evidence.",
                ),
                CodeApplication(
                    id=hidden_id,
                    project_id=other_project_id,
                    code_id="hidden-code",
                    source_text="Hidden project evidence.",
                ),
            ]
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/code-applications/{project_id}", headers=auth_headers
        )

    assert response.status_code == 200
    payload = response.json()
    assert [item["id"] for item in payload] == [visible_id]


@pytest.mark.asyncio
async def test_code_apps_list_can_scope_to_coding_run(auth_headers):
    """Benchmark reconciliation proof must not mix applications from runs."""
    await init_db()
    project_id = f"code-run-filter-{uuid.uuid4().hex[:8]}"
    run_a = f"run-a-{uuid.uuid4().hex[:8]}"
    run_b = f"run-b-{uuid.uuid4().hex[:8]}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Code Applications Run Filter"))
        db.add_all(
            [
                CodeApplication(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    coding_run_id=run_a,
                    code_id="run-a-code",
                    source_text="Run A evidence.",
                ),
                CodeApplication(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    coding_run_id=run_b,
                    code_id="run-b-code",
                    source_text="Run B evidence.",
                ),
            ]
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/code-applications/{project_id}",
            params={"coding_run_id": run_a},
            headers=auth_headers,
        )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["coding_run_id"] == run_a


@pytest.mark.asyncio
async def test_code_apps_requires_auth():
    """Code applications requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/code-applications/test-project")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_code_apps_pending_returns_response(auth_headers):
    """GET /api/code-applications/{project_id}/pending returns pending applications."""
    await init_db()
    project_id = f"code-pending-{uuid.uuid4().hex[:8]}"
    pending_id = str(uuid.uuid4())
    approved_id = str(uuid.uuid4())
    async with async_session() as db:
        db.add_all(
            [
                Project(id=project_id, name="Code Applications Pending"),
                CodeApplication(
                    id=pending_id,
                    project_id=project_id,
                    code_id="pending-code",
                    source_text="Needs human review.",
                    review_status="pending",
                    confidence=0.72,
                ),
                CodeApplication(
                    id=approved_id,
                    project_id=project_id,
                    code_id="approved-code",
                    source_text="Already approved.",
                    review_status="approved",
                    confidence=0.94,
                ),
            ]
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/code-applications/{project_id}/pending", headers=auth_headers
        )

    assert response.status_code == 200
    payload = response.json()
    assert [item["id"] for item in payload] == [pending_id]


@pytest.mark.asyncio
async def test_code_apps_bulk_approve_bounds_confidence(auth_headers):
    """Bulk approval threshold is bounded to the statistical confidence interval."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/code-applications/test-project/bulk-approve",
            params={"min_confidence": 1.5},
            headers=auth_headers,
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_code_apps_bulk_approve_requires_reliability_gate(auth_headers):
    """Bulk approval cannot bypass explicit Research Spine reconciliation."""
    await init_db()
    settings.team_mode = True
    project_id = f"code-bulk-reliability-{uuid.uuid4().hex[:8]}"
    blocked_id = str(uuid.uuid4())
    accepted_id = str(uuid.uuid4())
    async with async_session() as db:
        db.add_all(
            [
                CodeApplication(
                    id=blocked_id,
                    project_id=project_id,
                    code_id="nav-confusion",
                    source_text="I cannot find reports.",
                    confidence=0.97,
                    promotion_status="blocked",
                    reliability_status="unknown",
                ),
                CodeApplication(
                    id=accepted_id,
                    project_id=project_id,
                    code_id="team-invite-friction",
                    source_text="Inviting my team was confusing.",
                    confidence=0.96,
                    promotion_status="accepted",
                    reliability_status="accepted",
                ),
            ]
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            f"/api/code-applications/{project_id}/bulk-approve",
            params={"min_confidence": 0.9},
            headers=auth_headers,
        )

    assert response.status_code == 422
    assert "explicit reconciliation" in response.json()["detail"]

    async with async_session() as db:
        blocked = await db.get(CodeApplication, blocked_id)
        accepted = await db.get(CodeApplication, accepted_id)
    assert blocked.review_status == "pending"
    assert accepted.review_status == "pending"
    assert accepted.reconciliation_status == "unreconciled"


@pytest.mark.asyncio
async def test_code_apps_review_uses_authenticated_reviewer(auth_headers):
    """Review audit trail comes from the authenticated subject, not client input."""
    await init_db()
    settings.team_mode = True
    app_id = str(uuid.uuid4())
    async with async_session() as db:
        db.add(
            CodeApplication(
                id=app_id,
                project_id="code-review-auth",
                code_id="nav-confusion",
                source_text="I cannot find reports.",
            )
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.patch(
            f"/api/code-applications/{app_id}/review",
            params={"project_id": "code-review-auth"},
            json={"review_status": "approved", "reviewed_by": "spoofed-user"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["reviewed_by"] == "testuser"
        assert response.json()["reviewed_at"] is not None


@pytest.mark.asyncio
async def test_code_apps_review_rejects_stale_application_ids_from_other_projects(
    auth_headers,
):
    """Review by-id route must bind the application id to the active project."""
    await init_db()
    settings.team_mode = True
    app_id = str(uuid.uuid4())
    project_id = f"review-project-{uuid.uuid4()}"
    other_project_id = f"review-other-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(
            CodeApplication(
                id=app_id,
                project_id=project_id,
                code_id="checkout-friction",
                source_text="The checkout flow is confusing.",
            )
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        stale_response = await ac.patch(
            f"/api/code-applications/{app_id}/review",
            params={"project_id": other_project_id},
            json={"review_status": "approved"},
            headers=auth_headers,
        )
        active_response = await ac.patch(
            f"/api/code-applications/{app_id}/review",
            params={"project_id": project_id},
            json={"review_status": "rejected"},
            headers=auth_headers,
        )

    assert stale_response.status_code == 404
    assert active_response.status_code == 200
    assert active_response.json()["project_id"] == project_id
    assert active_response.json()["review_status"] == "rejected"


@pytest.mark.asyncio
async def test_synthetic_reconciliation_is_disabled_by_default(auth_headers):
    await init_db()
    project_id = f"synthetic-off-{uuid.uuid4().hex[:8]}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Synthetic off"))
        await db.commit()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            f"/api/code-applications/{project_id}/synthetic-reconciliation",
            json={"coding_run_id": "missing", "diagnostic_id": "diag", "decisions": []},
            headers={
                **auth_headers,
                "x-istara-synthetic-reconciliation": "benchmark-v1",
            },
        )
    assert response.status_code == 404
    assert response.json()["detail"] == "Synthetic reconciliation is disabled."


@pytest.mark.asyncio
async def test_synthetic_reconciliation_records_provenance_without_human_promotion(
    auth_headers,
):
    await init_db()
    settings.team_mode = True
    settings.research_validity_synthetic_reconciliation_enabled = True
    project_id = f"synthetic-on-{uuid.uuid4().hex[:8]}"
    run_id = f"synthetic-run-{uuid.uuid4().hex[:8]}"
    task_id = f"synthetic-task-{uuid.uuid4().hex[:8]}"
    app_id = str(uuid.uuid4())
    async with async_session() as db:
        db.add(Project(id=project_id, name="Synthetic on"))
        db.add(
            CodingRun(
                id=run_id,
                project_id=project_id,
                task_id=task_id,
                status="completed",
                promotion_status="accepted",
            )
        )
        db.add(
            CodeApplication(
                id=app_id,
                project_id=project_id,
                task_id=task_id,
                coding_run_id=run_id,
                evidence_unit_id=str(uuid.uuid4()),
                code_id="checkout-friction",
                source_text="The checkout flow is confusing.",
                source_location="interview-1:12",
                coder_id="coder-1",
                model_name="model-a",
                route_id="route-a",
                route_evidence_json='{"served_model":"model-a","endpoint_id":"ep-a","outcome":"served"}',
            )
        )
        await db.commit()

    request_payload = {
        "coding_run_id": run_id,
        "diagnostic_id": "diag-1",
        "decisions": [
            {
                "code_application_id": app_id,
                "decision_type": "accepted",
                "rationale": "benchmark coverage receipt",
            }
        ],
    }
    headers = {**auth_headers, "x-istara-synthetic-reconciliation": "benchmark-v1"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            f"/api/code-applications/{project_id}/synthetic-reconciliation",
            json=request_payload,
            headers=headers,
        )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "benchmark_synthetic"
    assert body["accepted_reportable"] is False
    assert body["human_review_required"] is True
    assert body["decisions"][0]["decided_by"] == "benchmark-synthetic:diag-1"
    assert body["decisions"][0]["source"] == "benchmark_synthetic"

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        retry = await ac.post(
            f"/api/code-applications/{project_id}/synthetic-reconciliation",
            json=request_payload,
            headers=headers,
        )
        conflict = await ac.post(
            f"/api/code-applications/{project_id}/synthetic-reconciliation",
            json={
                **request_payload,
                "decisions": [
                    {"code_application_id": app_id, "decision_type": "rejected"}
                ],
            },
            headers=headers,
        )
    assert retry.status_code == 200
    assert retry.json()["decisions"][0]["id"] == body["decisions"][0]["id"]
    assert conflict.status_code == 422
    assert "different decision payload" in conflict.json()["detail"]

    async with async_session() as db:
        row = await db.get(CodeApplication, app_id)
        receipts = (
            await db.scalars(
                select(ReconciliationDecision).where(
                    ReconciliationDecision.code_application_id == app_id
                )
            )
        ).all()
        receipt = receipts[0]
    assert row.review_status == "pending"
    assert row.reconciliation_status == "unreconciled"
    assert row.promotion_status == "blocked"
    assert receipt.source == "benchmark_synthetic"
    assert len(receipts) == 1

    # A benchmark receipt must not unlock the production Research Spine gate.
    # Ask the same validity service used by report promotion instead of only
    # checking the stored row fields, so this test catches an accidental
    # synthetic-to-reportable bypass.
    from app.services.research_validity_service import assess_task_research_validity

    async with async_session() as db:
        validity = await assess_task_research_validity(
            db,
            project_id=project_id,
            task_id=task_id,
        )
    assert validity["report_allowed"] is False
    assert validity["unresolved_code_application_count"] == 1
    assert "unreconciled" in validity["reason"]


@pytest.mark.asyncio
async def test_synthetic_reconciliation_requires_explicit_header(auth_headers):
    await init_db()
    settings.research_validity_synthetic_reconciliation_enabled = True
    project_id = f"synthetic-header-{uuid.uuid4().hex[:8]}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Synthetic header"))
        await db.commit()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            f"/api/code-applications/{project_id}/synthetic-reconciliation",
            json={"coding_run_id": "missing", "diagnostic_id": "diag", "decisions": []},
            headers=auth_headers,
        )
    assert response.status_code == 403
    assert "opt-in header" in response.json()["detail"]


@pytest.mark.asyncio
async def test_synthetic_reconciliation_requires_complete_run_and_provenance(
    auth_headers,
):
    await init_db()
    settings.research_validity_synthetic_reconciliation_enabled = True
    project_id = f"synthetic-scope-{uuid.uuid4().hex[:8]}"
    run_id = f"synthetic-run-{uuid.uuid4().hex[:8]}"
    app_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
    async with async_session() as db:
        db.add(Project(id=project_id, name="Synthetic scope"))
        db.add(CodingRun(id=run_id, project_id=project_id, status="completed"))
        db.add_all(
            [
                CodeApplication(
                    id=app_ids[0],
                    project_id=project_id,
                    coding_run_id=run_id,
                    evidence_unit_id=str(uuid.uuid4()),
                    code_id="code-a",
                    source_text="Evidence A.",
                    source_location="source-a:1",
                    coder_id="coder-a",
                    model_name="model-a",
                    route_id="route-a",
                    route_evidence_json='{"served_model":"model-a","served_request_count":"1"}',
                ),
                CodeApplication(
                    id=app_ids[1],
                    project_id=project_id,
                    coding_run_id=run_id,
                    evidence_unit_id=str(uuid.uuid4()),
                    code_id="code-b",
                    source_text="Evidence B.",
                    source_location="source-b:1",
                    coder_id="coder-b",
                    model_name="model-b",
                    route_id="route-b",
                    route_evidence_json="{}",
                ),
            ]
        )
        await db.commit()
    transport = ASGITransport(app=app)
    headers = {**auth_headers, "x-istara-synthetic-reconciliation": "benchmark-v1"}
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        incomplete = await ac.post(
            f"/api/code-applications/{project_id}/synthetic-reconciliation",
            json={
                "coding_run_id": run_id,
                "diagnostic_id": "diag-scope",
                "decisions": [
                    {"code_application_id": app_ids[0], "decision_type": "accepted"}
                ],
            },
            headers=headers,
        )
    assert incomplete.status_code == 422
    assert "exactly every application" in incomplete.json()["detail"]

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        missing_provenance = await ac.post(
            f"/api/code-applications/{project_id}/synthetic-reconciliation",
            json={
                "coding_run_id": run_id,
                "diagnostic_id": "diag-scope",
                "decisions": [
                    {"code_application_id": app_ids[0], "decision_type": "accepted"},
                    {"code_application_id": app_ids[1], "decision_type": "accepted"},
                ],
            },
            headers=headers,
        )
    assert missing_provenance.status_code == 422
    assert "route evidence provenance" in missing_provenance.json()["detail"]
