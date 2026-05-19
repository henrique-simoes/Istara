"""Tests for Projects API routes — CRUD, members, versions, pause/resume."""

import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.models.database import init_db
from app.core.auth import create_token
from app.models.database import async_session
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


# ---------------------------------------------------------------------------
# Project Listing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_projects_list_returns_list(auth_headers):
    """GET /api/projects returns a list."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/projects", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_projects_list_requires_auth():
    """Projects listing requires authentication."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/projects")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Project Get/Pause/Resume
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_project_get_nonexistent_returns_404(auth_headers):
    """GET /api/projects/{id} returns 404 for non-existent project."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/projects/non-existent-id", headers=auth_headers)
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_project_pause_nonexistent_returns_404(auth_headers):
    """POST /api/projects/{id}/pause returns 404 for non-existent project."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/projects/non-existent-id/pause", headers=auth_headers)
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_project_resume_nonexistent_returns_404(auth_headers):
    """POST /api/projects/{id}/resume returns 404 for non-existent project."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/projects/non-existent-id/resume", headers=auth_headers)
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_project_pause_stops_project_background_work(auth_headers, monkeypatch):
    """Pausing a project should stop project-owned autonomous/background workers."""
    await init_db()
    project_id = f"pause-background-{uuid.uuid4().hex[:8]}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Pause Background Project"))
        await db.commit()

    class FakeMetaHyperagent:
        def __init__(self):
            self.stopped = None

        def is_running_for_project(self, candidate_project_id):
            return candidate_project_id == project_id

        def stop(self, project_id=None):
            self.stopped = project_id

    class FakeAutoresearchEngine:
        is_running = True
        active_project_id = project_id

        def __init__(self):
            self.stopped = False

        def get_current_experiment(self):
            return None

        def request_stop(self):
            self.stopped = True

    fake_meta = FakeMetaHyperagent()
    fake_engine = FakeAutoresearchEngine()

    async def fake_stop_channels(db, candidate_project_id):
        assert candidate_project_id == project_id
        return 2

    monkeypatch.setattr("app.core.meta_hyperagent.meta_hyperagent", fake_meta)
    monkeypatch.setattr("app.core.autoresearch_engine.autoresearch_engine", fake_engine)
    monkeypatch.setattr(
        "app.services.channel_service.stop_project_channel_instances",
        fake_stop_channels,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(f"/api/projects/{project_id}/pause", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["stopped"] == {
        "meta_hyperagent": True,
        "autoresearch": True,
        "channels": 2,
    }
    assert fake_meta.stopped == project_id
    assert fake_engine.stopped is True


# ---------------------------------------------------------------------------
# Project Versions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_project_versions_returns_list(auth_headers):
    """GET /api/projects/{id}/versions returns a list."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/projects/test-id/versions", headers=auth_headers)
        assert response.status_code in (200, 404)
        if response.status_code == 200:
            assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_link_folder_rejects_filesystem_root(auth_headers):
    """Folder linking should not allow broad system roots as project watch folders."""
    await init_db()
    project = Project(id=f"link-root-project-{uuid.uuid4().hex[:8]}", name="Link Root Project")
    async with async_session() as db:
        db.add(project)
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            f"/api/projects/{project.id}/link-folder",
            headers=auth_headers,
            json={"folder_path": "/"},
        )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_link_folder_persists_resolved_directory(auth_headers, tmp_path):
    """Valid linked folders should be persisted as the project watch folder."""
    await init_db()
    project = Project(id=f"link-valid-project-{uuid.uuid4().hex[:8]}", name="Link Valid Project")
    linked_dir = tmp_path / "research-files"
    linked_dir.mkdir()
    async with async_session() as db:
        db.add(project)
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            f"/api/projects/{project.id}/link-folder",
            headers=auth_headers,
            json={"folder_path": str(linked_dir)},
        )

    assert response.status_code == 200
    assert response.json()["watch_folder_path"] == str(linked_dir.resolve())
