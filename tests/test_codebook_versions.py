"""Tests for Codebook Versions API routes — list, latest, create."""

import json
import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.models.codebook_version import CodebookVersion
from app.models.database import async_session, init_db
from app.models.project import Project
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
async def test_codebook_versions_list_returns_response(auth_headers):
    """GET /api/codebook-versions/{project_id} returns versions."""
    await init_db()
    project_id = f"codebook-list-{uuid.uuid4().hex[:8]}"
    version_id = str(uuid.uuid4())
    async with async_session() as db:
        db.add_all(
            [
                Project(id=project_id, name="Codebook Versions List"),
                CodebookVersion(
                    id=version_id,
                    project_id=project_id,
                    version="1.0.0",
                    codes_json=json.dumps(
                        [
                            {
                                "code_id": "invite-friction",
                                "brief_definition": "Team invitation flow creates research friction.",
                            }
                        ]
                    ),
                    change_log="Initial governed codebook.",
                    created_by="researcher-a",
                    methodology="codebook_ta",
                ),
            ]
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/codebook-versions/{project_id}", headers=auth_headers
        )

    assert response.status_code == 200
    payload = response.json()
    assert [item["id"] for item in payload] == [version_id]
    assert payload[0]["codes"][0]["code_id"] == "invite-friction"


@pytest.mark.asyncio
async def test_codebook_versions_requires_auth():
    """Codebook versions requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/codebook-versions/test-project")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_codebook_versions_latest_returns_response(auth_headers):
    """GET /api/codebook-versions/{project_id}/latest returns latest version."""
    await init_db()
    project_id = f"codebook-latest-{uuid.uuid4().hex[:8]}"
    older_id = str(uuid.uuid4())
    latest_id = str(uuid.uuid4())
    async with async_session() as db:
        db.add_all(
            [
                Project(id=project_id, name="Codebook Versions Latest"),
                CodebookVersion(
                    id=older_id,
                    project_id=project_id,
                    version="1.0.0",
                    codes_json=json.dumps([{"code_id": "older-code"}]),
                    change_log="Initial codebook.",
                    created_by="researcher-a",
                    methodology="codebook_ta",
                    created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                ),
                CodebookVersion(
                    id=latest_id,
                    project_id=project_id,
                    version="1.1.0",
                    codes_json=json.dumps([{"code_id": "latest-code"}]),
                    change_log="Revision after calibration.",
                    created_by="researcher-a",
                    methodology="codebook_ta",
                    created_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
                ),
            ]
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/codebook-versions/{project_id}/latest", headers=auth_headers
        )

    assert response.status_code == 200
    assert response.json()["id"] == latest_id
