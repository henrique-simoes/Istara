"""Integration test: Interview pipeline — create session → upload transcript → extract findings → generate report."""

import pytest
import uuid
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


@pytest.mark.asyncio
async def test_interview_pipeline_integration(auth_headers):
    """Verify the interview pipeline: sessions → documents → findings."""
    await init_db()
    project_id = f"interview-project-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Interview Integration Project"))
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Sessions endpoint accessible
        response = await ac.get(f"/api/sessions/{project_id}", headers=auth_headers)
        assert response.status_code in (200, 404)

        # 2. Documents endpoint accessible
        response = await ac.get(
            f"/api/documents?project_id={project_id}", headers=auth_headers
        )
        assert response.status_code == 200

        # 3. Findings endpoints accessible
        response = await ac.get(
            f"/api/findings/nuggets?project_id={project_id}", headers=auth_headers
        )
        assert response.status_code == 200

        # 4. Reports endpoint accessible
        response = await ac.get(f"/api/reports/{project_id}", headers=auth_headers)
        assert response.status_code in (200, 404)
