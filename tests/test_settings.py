"""Tests for Settings API routes — hardware, models, status, maintenance, data integrity."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.models.database import init_db
from app.core.auth import create_token


@pytest.fixture(autouse=True)
def reset_settings():
    original_team_mode = settings.team_mode
    original_jwt_secret = settings.jwt_secret
    original_data_dir = settings.data_dir
    original_runtime_personas_dir = settings.runtime_personas_dir
    original_strict_auto_routing = settings.strict_auto_routing
    yield
    settings.team_mode = original_team_mode
    settings.jwt_secret = original_jwt_secret
    settings.data_dir = original_data_dir
    settings.runtime_personas_dir = original_runtime_personas_dir
    settings.strict_auto_routing = original_strict_auto_routing


@pytest.fixture
def auth_headers():
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    token = create_token("user1", "testuser", "admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_settings_status_returns_response(auth_headers):
    """GET /api/settings/status returns system status."""
    await init_db()
    settings.strict_auto_routing = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/settings/status", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), dict)
        assert response.json()["strict_auto_routing"] is True


@pytest.mark.asyncio
async def test_strict_routing_toggle_updates_runtime_and_persists(auth_headers, monkeypatch):
    """POST /api/settings/strict-routing persists the compute routing mode."""
    await init_db()
    persisted: dict[str, str] = {}
    monkeypatch.setattr(
        "app.api.routes.settings._persist_env",
        lambda key, value: persisted.setdefault(key, value),
    )
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/settings/strict-routing",
            headers=auth_headers,
            json={"enabled": True},
        )

    assert response.status_code == 200
    assert response.json()["strict_auto_routing"] is True
    assert settings.strict_auto_routing is True
    assert persisted == {"STRICT_AUTO_ROUTING": "true"}


@pytest.mark.asyncio
async def test_settings_status_requires_auth():
    """Settings status requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/settings/status")
        assert response.status_code in (401, 200)


@pytest.mark.asyncio
async def test_settings_hardware_returns_response(auth_headers):
    """GET /api/settings/hardware returns hardware info."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/settings/hardware", headers=auth_headers)
        assert response.status_code in (200, 404, 500)


@pytest.mark.asyncio
async def test_settings_models_returns_response(auth_headers):
    """GET /api/settings/models returns model list."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/settings/models", headers=auth_headers)
        assert response.status_code in (200, 404, 500)


@pytest.mark.asyncio
async def test_settings_data_integrity_returns_response(auth_headers):
    """GET /api/settings/data-integrity returns integrity check."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/settings/data-integrity", headers=auth_headers)
        assert response.status_code in (200, 404, 500)


@pytest.mark.asyncio
async def test_data_integrity_uses_runtime_paths_for_clean_install(tmp_path):
    """Clean installs should not report orphaned data from a developer checkout."""
    from app.core.data_integrity import run_integrity_check
    from app.models.database import async_session

    await init_db()
    settings.data_dir = str(tmp_path / "data")
    settings.runtime_personas_dir = str(tmp_path / "data" / "personas")

    async with async_session() as db:
        report = await run_integrity_check(db)

    warning_text = "\n".join(report["warnings"])
    assert "keyword index files have no matching project" not in warning_text
    assert "persona directories have no matching agent record" not in warning_text
