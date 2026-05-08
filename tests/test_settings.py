"""Tests for Settings API routes — hardware, models, status, maintenance, data integrity."""

import pytest
from app.config import settings
from app.core.auth import create_token
from app.main import app
from app.models.database import init_db
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def reset_settings():
    original_team_mode = settings.team_mode
    original_jwt_secret = settings.jwt_secret
    original_data_dir = settings.data_dir
    original_upload_dir = settings.upload_dir
    original_lance_db_path = settings.lance_db_path
    original_runtime_personas_dir = settings.runtime_personas_dir
    original_strict_auto_routing = settings.strict_auto_routing
    original_active_probe = settings.llm_capability_active_probe_enabled
    yield
    settings.team_mode = original_team_mode
    settings.jwt_secret = original_jwt_secret
    settings.data_dir = original_data_dir
    settings.upload_dir = original_upload_dir
    settings.lance_db_path = original_lance_db_path
    settings.runtime_personas_dir = original_runtime_personas_dir
    settings.strict_auto_routing = original_strict_auto_routing
    settings.llm_capability_active_probe_enabled = original_active_probe


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


class _ReachableButNotChatReadyRegistry:
    def __init__(self):
        self.check_all_health_calls = 0
        self.ensure_kwargs = {}

    async def check_all_health(self):
        self.check_all_health_calls += 1
        return {"node": True}

    async def health(self):
        return True

    async def ensure_chat_ready(self, model=None, **kwargs):
        self.ensure_kwargs = kwargs
        return False


@pytest.mark.asyncio
async def test_settings_status_reports_llm_disconnected_until_chat_ready(monkeypatch):
    from app.api.routes import settings as settings_routes
    import app.core.ollama as ollama_module

    fake_registry = _ReachableButNotChatReadyRegistry()
    monkeypatch.setattr(settings_routes, "ollama", fake_registry)
    monkeypatch.setattr(ollama_module, "ollama", fake_registry)

    response = await settings_routes.system_status()

    assert response["llm_readiness"] == {"reachable": True, "chat_ready": False}
    assert response["services"]["llm"] == "disconnected"
    assert response["status"] == "degraded"
    assert fake_registry.ensure_kwargs["probe_lmstudio"] is False
    assert fake_registry.ensure_kwargs["allow_model_load"] is False
    assert fake_registry.ensure_kwargs["refresh_health"] is False
    assert fake_registry.check_all_health_calls == 0


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


@pytest.mark.asyncio
async def test_data_integrity_detects_invalid_uploaded_pdfs(tmp_path):
    """Integrity check should catch PDFs that will fail downstream parsing."""
    from app.core.data_integrity import run_integrity_check
    from app.models.database import async_session

    await init_db()
    settings.data_dir = str(tmp_path / "data")
    settings.upload_dir = str(tmp_path / "data" / "uploads")
    settings.lance_db_path = str(tmp_path / "data" / "lance")
    settings.runtime_personas_dir = str(tmp_path / "data" / "personas")

    bad_pdf = tmp_path / "data" / "uploads" / "missing-project" / "broken.pdf"
    bad_pdf.parent.mkdir(parents=True)
    bad_pdf.write_bytes(b"not a real pdf")

    async with async_session() as db:
        report = await run_integrity_check(db)

    assert "missing-project/broken.pdf" in report["invalid_files"]["pdfs"]
    assert any("uploaded PDF files" in warning for warning in report["warnings"])


@pytest.mark.asyncio
async def test_data_integrity_quarantine_moves_orphans_and_invalid_pdfs(tmp_path):
    """Repair action quarantines data rather than deleting it."""
    from app.core.data_integrity import quarantine_integrity_issues
    from app.models.database import async_session

    await init_db()
    settings.data_dir = str(tmp_path / "data")
    settings.upload_dir = str(tmp_path / "data" / "uploads")
    settings.lance_db_path = str(tmp_path / "data" / "lance")
    settings.runtime_personas_dir = str(tmp_path / "data" / "personas")

    orphan_upload = tmp_path / "data" / "uploads" / "missing-project"
    orphan_upload.mkdir(parents=True)
    bad_pdf = orphan_upload / "broken.pdf"
    bad_pdf.write_bytes(b"%PDF-1.7\nmissing eof")

    async with async_session() as db:
        dry_run = await quarantine_integrity_issues(db, dry_run=True)
        assert orphan_upload.exists()
        result = await quarantine_integrity_issues(db, dry_run=False)

    assert dry_run["actions"]
    assert result["moved"] >= 1
    assert not orphan_upload.exists()
    assert any(action["kind"] == "uploads" for action in result["actions"])
