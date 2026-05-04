"""Agent avatar upload hardening tests."""

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.api.routes import agents as agents_routes
from app.config import settings
from app.core.auth import create_token
from app.main import app
from app.models.database import init_db


@pytest.fixture(autouse=True)
def reset_settings():
    original_team_mode = settings.team_mode
    original_jwt_secret = settings.jwt_secret
    original_avatars_dir = settings.agent_avatars_dir
    original_avatar_max_bytes = settings.avatar_max_bytes
    yield
    settings.team_mode = original_team_mode
    settings.jwt_secret = original_jwt_secret
    settings.agent_avatars_dir = original_avatars_dir
    settings.avatar_max_bytes = original_avatar_max_bytes


@pytest.fixture
def auth_headers():
    settings.team_mode = True
    settings.jwt_secret = "test-secret"
    token = create_token("admin1", "admin", "admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def fake_agent_service(monkeypatch):
    updated: dict[str, str] = {}

    async def fake_get_agent(db, agent_id: str):
        return {"id": agent_id, "avatar_path": updated.get("avatar_path")}

    async def fake_update_agent(db, agent_id: str, updates: dict):
        updated.update(updates)
        return {"id": agent_id, **updated}

    monkeypatch.setattr(agents_routes.agent_service, "get_agent", fake_get_agent)
    monkeypatch.setattr(agents_routes.agent_service, "update_agent", fake_update_agent)
    return updated


@pytest.mark.asyncio
async def test_avatar_upload_uses_server_chosen_extension_and_storage_root(
    tmp_path,
    monkeypatch,
    auth_headers,
    fake_agent_service,
):
    await init_db()
    monkeypatch.setattr(settings, "agent_avatars_dir", str(tmp_path / "avatars"))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/agents/agent..id/avatar",
            headers=auth_headers,
            files={"file": ("../../evil.php", b"avatar-bytes", "image/png")},
        )

    assert response.status_code == 200
    avatar_path = response.json()["avatar_path"]
    assert avatar_path.endswith(".png")
    assert not avatar_path.endswith(".php")
    stored = agents_routes._resolve_avatar_path(avatar_path)
    stored.relative_to((tmp_path / "avatars").resolve())
    assert stored.read_bytes() == b"avatar-bytes"


@pytest.mark.asyncio
async def test_avatar_upload_rejects_oversized_file(
    tmp_path,
    monkeypatch,
    auth_headers,
    fake_agent_service,
):
    await init_db()
    monkeypatch.setattr(settings, "agent_avatars_dir", str(tmp_path / "avatars"))
    monkeypatch.setattr(settings, "avatar_max_bytes", 4)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/agents/agent-id/avatar",
            headers=auth_headers,
            files={"file": ("avatar.png", b"12345", "image/png")},
        )

    assert response.status_code == 413


def test_avatar_path_resolution_rejects_outside_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "agent_avatars_dir", str(tmp_path / "avatars"))

    with pytest.raises(HTTPException) as exc:
        agents_routes._resolve_avatar_path(str(tmp_path / "outside.png"))

    assert exc.value.status_code == 403
