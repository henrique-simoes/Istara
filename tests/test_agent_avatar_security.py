"""Agent avatar upload hardening tests."""

import json
import uuid

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.api.routes import agents as agents_routes
from app.config import settings
from app.core.auth import create_token
from app.main import app
from app.models.agent import Agent, AgentRole, AgentState, HeartbeatStatus
from app.models.database import async_session, init_db
from app.models.project import Project


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


async def _seed_project_agent(agent_id: str) -> str:
    project = Project(id=str(uuid.uuid4()), name=f"Avatar Project {uuid.uuid4()}")
    agent = Agent(
        id=agent_id,
        name=f"Avatar Agent {uuid.uuid4()}",
        role=AgentRole.CUSTOM,
        system_prompt="Avatar upload test agent",
        capabilities=json.dumps(["chat"]),
        specialties=json.dumps([]),
        scope="project",
        project_id=project.id,
        state=AgentState.IDLE,
        heartbeat_status=HeartbeatStatus.STOPPED,
    )
    async with async_session() as db:
        db.add(project)
        db.add(agent)
        await db.commit()
    return project.id


@pytest.mark.asyncio
async def test_avatar_upload_uses_server_chosen_extension_and_storage_root(
    tmp_path,
    monkeypatch,
    auth_headers,
):
    await init_db()
    agent_id = f"agent..id-{uuid.uuid4()}"
    project_id = await _seed_project_agent(agent_id)
    monkeypatch.setattr(settings, "agent_avatars_dir", str(tmp_path / "avatars"))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            f"/api/agents/{agent_id}/avatar?project_id={project_id}",
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
):
    await init_db()
    agent_id = f"agent-id-{uuid.uuid4()}"
    project_id = await _seed_project_agent(agent_id)
    monkeypatch.setattr(settings, "agent_avatars_dir", str(tmp_path / "avatars"))
    monkeypatch.setattr(settings, "avatar_max_bytes", 4)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            f"/api/agents/{agent_id}/avatar?project_id={project_id}",
            headers=auth_headers,
            files={"file": ("avatar.png", b"12345", "image/png")},
        )

    assert response.status_code == 413


def test_avatar_path_resolution_rejects_outside_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "agent_avatars_dir", str(tmp_path / "avatars"))

    with pytest.raises(HTTPException) as exc:
        agents_routes._resolve_avatar_path(str(tmp_path / "outside.png"))

    assert exc.value.status_code == 403
