from types import SimpleNamespace

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.core.auth import create_token
from app.main import app
from app.models.database import init_db


@pytest.mark.asyncio
async def test_update_check_redacts_transport_failures(monkeypatch):
    """Settings must never expose resolver/host details from the update transport."""
    from app.api.routes import updates as updates_routes

    class FailingUpdateClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, *_args, **_kwargs):
            raise OSError("[Errno -3] Temporary failure in name resolution")

    updates_routes._update_cache.clear()
    monkeypatch.setattr(httpx, "AsyncClient", lambda *_args, **_kwargs: FailingUpdateClient())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/updates/check")

    assert response.status_code == 200
    body = response.json()
    assert body["error_code"] == "update_check_unavailable"
    assert body["error"] == "Update check is unavailable. Check the network connection and try again."
    assert "Errno" not in response.text
    assert "name resolution" not in response.text


@pytest.fixture(autouse=True)
def reset_settings():
    original_team_mode = settings.team_mode
    original_jwt_secret = settings.jwt_secret
    original_network_token = settings.network_access_token
    original_bind_host = settings.bind_host
    yield
    settings.team_mode = original_team_mode
    settings.jwt_secret = original_jwt_secret
    settings.network_access_token = original_network_token
    settings.bind_host = original_bind_host


@pytest.mark.asyncio
async def test_local_update_apply_requires_explicit_confirmation(tmp_path, monkeypatch):
    await init_db()
    settings.team_mode = False

    install_dir = tmp_path / "istara"
    (install_dir / ".git").mkdir(parents=True)
    monkeypatch.setattr("app.api.routes.updates.get_install_dir", lambda: install_dir)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/updates/apply")

    assert response.status_code == 400
    assert "Explicit confirmation required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_local_update_apply_accepts_matching_confirmation(tmp_path, monkeypatch):
    await init_db()
    settings.team_mode = False

    install_dir = tmp_path / "istara"
    (install_dir / ".git").mkdir(parents=True)
    scheduled_coroutines = []

    def fake_create_task(coro):
        scheduled_coroutines.append(getattr(getattr(coro, "cr_code", None), "co_name", None))
        coro.close()
        return SimpleNamespace()

    monkeypatch.setattr("app.api.routes.updates.get_install_dir", lambda: install_dir)
    monkeypatch.setattr("app.api.routes.updates.asyncio.create_task", fake_create_task)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/updates/apply", json={"confirm": "APPLY_UPDATE"})

    assert response.status_code == 200
    assert response.json()["status"] == "updating"
    assert "_run_update" in scheduled_coroutines


@pytest.mark.asyncio
async def test_local_update_prepare_requires_explicit_confirmation(monkeypatch):
    await init_db()
    settings.team_mode = False

    async def fail_if_called(*args, **kwargs):
        raise AssertionError("backup should not run without confirmation")

    monkeypatch.setattr("app.core.backup_manager.backup_manager.create_backup", fail_if_called)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/updates/prepare")

    assert response.status_code == 400
    assert "Explicit confirmation required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_team_update_apply_requires_admin_even_with_confirmation(tmp_path, monkeypatch):
    await init_db()
    settings.team_mode = True
    settings.jwt_secret = settings.jwt_secret or "test-secret"

    install_dir = tmp_path / "istara"
    (install_dir / ".git").mkdir(parents=True)
    monkeypatch.setattr("app.api.routes.updates.get_install_dir", lambda: install_dir)
    token = create_token("researcher-id", "researcher", "researcher")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/updates/apply",
            json={"confirm": "APPLY_UPDATE"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin required to apply updates"


@pytest.mark.asyncio
async def test_local_update_apply_rejects_remote_client_even_with_confirmation(tmp_path, monkeypatch):
    await init_db()
    settings.team_mode = False
    settings.network_access_token = "network-secret"
    settings.bind_host = "0.0.0.0"

    install_dir = tmp_path / "istara"
    (install_dir / ".git").mkdir(parents=True)
    monkeypatch.setattr("app.api.routes.updates.get_install_dir", lambda: install_dir)

    transport = ASGITransport(app=app, client=("203.0.113.10", 50000))
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/updates/apply",
            json={"confirm": "APPLY_UPDATE"},
            headers={"X-Access-Token": "network-secret"},
        )

    assert response.status_code == 403
    assert "Localhost access required" in response.json()["detail"]
