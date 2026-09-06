"""Tests for project report and presentation API resilience."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.core.auth import create_token
from app.main import app
from app.models.database import async_session, init_db
from app.models.project_report import ProjectReport


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
async def test_slide_instructions_fallback_when_llm_unavailable(auth_headers):
    """Reports menu should still produce slide instructions when the LLM is down."""
    await init_db()
    report_id = str(uuid.uuid4())
    async with async_session() as db:
        db.add(
            ProjectReport(
                id=report_id,
                project_id="reports-fallback",
                title="Fallback Report",
                executive_summary="Users cannot find exported reports quickly.",
            )
        )
        await db.commit()

    transport = ASGITransport(app=app)
    with patch(
        "app.api.routes.presentation.agentic.completion",
        new=AsyncMock(side_effect=RuntimeError("LLM unavailable")),
    ):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get(
                f"/api/presentation/reports/{report_id}/slide-instructions?project_id=reports-fallback",
                headers=auth_headers,
            )

    assert response.status_code == 200
    body = response.json()
    assert body["report_id"] == report_id
    assert body["project_id"] == "reports-fallback"
    assert "SYSTEM PROMPT" in body["instructions"]


@pytest.mark.asyncio
async def test_slide_instructions_require_active_project_scope(auth_headers):
    """Report-id-only slide generation must not bypass the active project."""
    await init_db()
    report_id = str(uuid.uuid4())
    async with async_session() as db:
        db.add(
            ProjectReport(
                id=report_id,
                project_id="reports-active-scope",
                title="Scoped Report",
                executive_summary="Scoped report summary.",
            )
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        missing_scope = await ac.get(
            f"/api/presentation/reports/{report_id}/slide-instructions",
            headers=auth_headers,
        )
        wrong_scope = await ac.get(
            f"/api/presentation/reports/{report_id}/slide-instructions?project_id=other-project",
            headers=auth_headers,
        )
        right_scope = await ac.get(
            f"/api/presentation/reports/{report_id}/slide-instructions?project_id=reports-active-scope",
            headers=auth_headers,
        )

    assert missing_scope.status_code == 400
    assert missing_scope.json()["detail"] == "project_id is required"
    assert wrong_scope.status_code == 404
    assert wrong_scope.json()["detail"] == "Report not found"
    assert right_scope.status_code == 200
    assert right_scope.json()["project_id"] == "reports-active-scope"


@pytest.mark.asyncio
async def test_slide_instructions_caching_and_persistence(auth_headers):
    """Slide instructions must be persisted to the DB and returned from cache on subsequent calls."""
    await init_db()
    report_id = str(uuid.uuid4())
    async with async_session() as db:
        db.add(
            ProjectReport(
                id=report_id,
                project_id="reports-caching",
                title="Caching Report",
                executive_summary="Executive summary for caching test.",
            )
        )
        await db.commit()

    transport = ASGITransport(app=app)
    mock_turn = AsyncMock()
    mock_turn.text = "Generated high-impact slide instructions."
    
    with patch("app.api.routes.presentation.agentic.completion", return_value=mock_turn) as mock_comp:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # 1. First call: generates and caches
            r1 = await ac.get(
                f"/api/presentation/reports/{report_id}/slide-instructions?project_id=reports-caching",
                headers=auth_headers,
            )
            assert r1.status_code == 200
            assert r1.json()["cached"] is False
            assert r1.json()["instructions"] == "Generated high-impact slide instructions."
            assert mock_comp.call_count == 1

            # Verify persisted in database
            async with async_session() as db:
                saved = await db.get(ProjectReport, report_id)
                assert saved.slide_instructions == "Generated high-impact slide instructions."

            # 2. Second call: returns cached without calling LLM
            r2 = await ac.get(
                f"/api/presentation/reports/{report_id}/slide-instructions?project_id=reports-caching",
                headers=auth_headers,
            )
            assert r2.status_code == 200
            assert r2.json()["cached"] is True
            assert r2.json()["instructions"] == "Generated high-impact slide instructions."
            assert mock_comp.call_count == 1  # Not called again!

            # 3. Call with regenerate=True: re-runs generation
            mock_turn.text = "Regenerated fresh slide instructions."
            r3 = await ac.get(
                f"/api/presentation/reports/{report_id}/slide-instructions?project_id=reports-caching&regenerate=true",
                headers=auth_headers,
            )
            assert r3.status_code == 200
            assert r3.json()["cached"] is False
            assert r3.json()["instructions"] == "Regenerated fresh slide instructions."
            assert mock_comp.call_count == 2

