from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.core.auth import create_token
from app.main import app
from app.models.database import init_db


@pytest.fixture(autouse=True)
def reset_settings():
    original_team_mode = settings.team_mode
    original_jwt_secret = settings.jwt_secret
    yield
    settings.team_mode = original_team_mode
    settings.jwt_secret = original_jwt_secret


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
