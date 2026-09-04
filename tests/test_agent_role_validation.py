"""Focused request validation coverage for manual agent creation."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.core.auth import create_token
from app.main import app
from app.models.database import async_session, init_db
from app.models.project import Project
from app.models.project_member import ProjectMember


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


async def _seed_project_member(project_id: str) -> None:
    async with async_session() as db:
        db.add(Project(id=project_id, name="Agent role validation project"))
        db.add(
            ProjectMember(
                id=str(uuid.uuid4()),
                project_id=project_id,
                user_id="user1",
                role="project_admin",
                added_by="test",
            )
        )
        await db.commit()


@pytest.mark.asyncio
async def test_agent_create_rejects_unknown_role_with_validation_error(auth_headers):
    """Unsupported role values must be a client validation error, not a 500."""
    await init_db()
    project_id = f"agent-role-validation-{uuid.uuid4()}"
    await _seed_project_member(project_id)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/agents",
            headers=auth_headers,
            json={
                "name": "Invalid Role Agent",
                "role": "researcher",
                "system_prompt": "The role is intentionally unsupported.",
                "project_id": project_id,
            },
        )

    assert response.status_code == 422
    assert any(error.get("loc", [None])[-1] == "role" for error in response.json()["detail"])
