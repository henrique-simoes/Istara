"""Tests for Code Applications API routes — list, pending, review, and fail-closed bulk action."""

import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.models.code_application import CodeApplication
from app.models.project import Project
from app.models.database import async_session, init_db
from app.core.auth import create_token


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
        response = await ac.get(f"/api/code-applications/{project_id}", headers=auth_headers)

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
        db.add(
            Project(id=project_id, name="Code Applications Run Filter")
        )
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
        response = await ac.get(f"/api/code-applications/{project_id}/pending", headers=auth_headers)

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
async def test_code_apps_review_rejects_stale_application_ids_from_other_projects(auth_headers):
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
