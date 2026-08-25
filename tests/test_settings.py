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
    _audio_fields = (
        "audio_model_provider",
        "audio_model",
        "audio_model_endpoint_id",
        "audio_model_credential_ref",
        "audio_model_mode",
        "audio_model_languages",
        "audio_model_diarization",
        "audio_model_timestamps",
        "audio_model_speaker_count",
        "audio_model_review_threshold",
    )
    original_audio = {name: getattr(settings, name) for name in _audio_fields}
    yield
    settings.team_mode = original_team_mode
    settings.jwt_secret = original_jwt_secret
    settings.data_dir = original_data_dir
    settings.upload_dir = original_upload_dir
    settings.lance_db_path = original_lance_db_path
    settings.runtime_personas_dir = original_runtime_personas_dir
    settings.strict_auto_routing = original_strict_auto_routing
    settings.llm_capability_active_probe_enabled = original_active_probe
    for name, value in original_audio.items():
        setattr(settings, name, value)


@pytest.fixture
def auth_headers():
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    token = create_token("user1", "testuser", "admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def researcher_headers():
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    token = create_token("user2", "researcher", "researcher")
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
        assert "runtime" in response.json()
        assert "provider" not in response.json()
        assert "config" not in response.json()


@pytest.mark.asyncio
async def test_security_integrity_is_admin_only_and_never_exposes_key(
    auth_headers, researcher_headers
):
    from app.core.field_encryption import decrypt_field, reset_encryption_health_for_tests
    from app.core.telemetry import telemetry_recorder

    reset_encryption_health_for_tests()
    telemetry_recorder.reset_write_health_for_tests()
    decrypt_field("ENC:tampered")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        denied = await ac.get("/api/settings/security-integrity", headers=researcher_headers)
        response = await ac.get("/api/settings/security-integrity", headers=auth_headers)
    assert denied.status_code == 403
    assert response.status_code == 200
    payload = response.json()["field_encryption"]
    assert payload["decryption_failures"] == 1
    assert payload["healthy"] is False
    assert "key" not in str(payload).lower()
    assert response.json()["telemetry_writes"]["healthy"] is True


class _CachedNode:
    def __init__(self, *, reachable: bool, ready: bool):
        self.reachable = reachable
        self.ready = ready

    def to_dict(self):
        return {
            "is_reachable": self.reachable,
            "is_ready": self.ready,
        }


class _PassiveCachedRegistry:
    def __init__(self):
        self._nodes = {
            "node": _CachedNode(reachable=True, ready=False),
        }

    async def check_all_health(self):  # pragma: no cover - must not be called
        raise AssertionError("status must not probe registry health")

    async def health(self):  # pragma: no cover - must not be called
        raise AssertionError("status must not probe provider health")

    async def ensure_chat_ready(self, model=None, **kwargs):  # pragma: no cover
        raise AssertionError("status must not probe chat readiness")


@pytest.mark.asyncio
async def test_settings_status_uses_cached_llm_readiness_without_probes(monkeypatch):
    from app.api.routes import settings as settings_routes

    fake_registry = _PassiveCachedRegistry()
    monkeypatch.setattr(settings_routes, "ollama", fake_registry)
    monkeypatch.setattr(
        settings_routes,
        "detect_runtime_freshness",
        lambda: {"frontend": {"stale": True, "status": "stale"}},
    )

    response = await settings_routes.system_status()

    assert response["llm_readiness"] == {"reachable": True, "chat_ready": False}
    assert response["services"]["llm"] == "connected"
    assert response["status"] == "degraded"
    assert response["runtime"]["frontend"]["stale"] is True
    assert "provider" not in response
    assert "config" not in response


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
async def test_model_management_migration_status_admin_plan_shape_no_secrets(auth_headers):
    """GET /api/settings/model-management/migration-status: dry-run plan shape,
    counts, rollback readiness, and never any secret material."""
    import json
    import uuid

    from app.core.field_encryption import encrypt_field
    from app.models.database import async_session
    from app.models.llm_server import LLMServer
    from sqlalchemy import select

    await init_db()
    row_id = f"mig-shape-{uuid.uuid4().hex[:8]}"
    async with async_session() as db:
        # The settings test DB file persists across runs; sweep stale rows from
        # earlier runs so ordering and counts stay deterministic.
        stale = list((await db.execute(select(LLMServer).where(LLMServer.id.like("mig-shape-%")))).scalars())
        for row in stale:
            await db.delete(row)
        db.add(LLMServer(
            id=row_id,
            name="Compat shape",
            provider_type="openai_compat",
            host="https://llm.invalid/v1",
            api_key=encrypt_field("super-secret-key-value"),
            is_local=False,
            is_relay=False,
        ))
        await db.commit()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            "/api/settings/model-management/migration-status", headers=auth_headers
        )
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "dry_run"
    assert body["delete_source_rows"] is False
    assert set(body["counts"]) == {"projected", "legacy_only", "blocked"}
    assert body["rollback"]["available"] is True
    assert body["rollback"]["source_rows_retained"] is True
    assert body["mappings"][0]["source_id"] == row_id
    assert body["mappings"][0]["canonical_endpoint_id"] == f"pi-llm-{row_id}"
    # Secret-free contract: the encrypted API key never surfaces, and no
    # mapping/checksum material can contain it.
    assert "api_key" not in body
    assert "super-secret-key-value" not in json.dumps(body)


@pytest.mark.asyncio
async def test_settings_status_is_public_but_redacted_in_team_mode():
    """Settings status stays public for UI health checks but omits sensitive details."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/settings/status")
        assert response.status_code == 200
        body = response.json()
        assert body["team_mode"] is True
        assert "llm_readiness" in body
        assert "provider" not in body
        assert "config" not in body


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "/api/settings/hardware",
        "/api/settings/models",
        "/api/settings/maintenance",
        "/api/settings/integrations-status",
        "/api/settings/vector-health",
        "/api/settings/data-integrity",
        "/api/settings/model-management/migration-status",
        "/api/settings/audio-model",
    ],
)
async def test_settings_infrastructure_metadata_requires_global_admin_in_team_mode(
    path, researcher_headers
):
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(path, headers=researcher_headers)
        assert response.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "/api/settings/model?model_name=test-model",
        "/api/settings/provider?provider=ollama",
    ],
)
async def test_settings_llm_mutations_require_global_admin_in_team_mode(
    path, researcher_headers
):
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(path, headers=researcher_headers)
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_settings_hardware_returns_response(auth_headers):
    """GET /api/settings/hardware returns hardware info."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/settings/hardware", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert "hardware" in body
    assert "recommendation" in body


@pytest.mark.asyncio
async def test_settings_models_returns_response(auth_headers):
    """GET /api/settings/models returns model list."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/settings/models", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert "models" in body
    assert "active_model" in body


@pytest.mark.asyncio
async def test_settings_data_integrity_returns_response(auth_headers):
    """GET /api/settings/data-integrity returns integrity check."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/settings/data-integrity", headers=auth_headers)
    assert response.status_code == 200
    assert {"status", "checks", "orphans", "invalid_files", "warnings"}.issubset(response.json())


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


@pytest.mark.asyncio
async def test_settings_audio_model_unconfigured_fails_closed(auth_headers):
    """GET /api/settings/audio-model with no profile -> 200 configured:false."""
    await init_db()
    settings.audio_model_provider = ""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/settings/audio-model", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is False
    assert body["profile"] is None
    assert body["fallback"] == "unavailable"
    assert body["research_data_status"] == "provisional_until_review"
    assert "credential_ref" not in body


@pytest.mark.asyncio
async def test_settings_audio_model_valid_profile_is_secret_free(auth_headers, monkeypatch):
    """Configured local profile -> 200 with runtime-grounded capabilities, no secrets."""
    await init_db()
    settings.audio_model_provider = "local_whisper"
    settings.audio_model = "whisper-base"
    settings.audio_model_endpoint_id = "audio-local"
    settings.audio_model_credential_ref = "keychain://istara/whisper"
    settings.audio_model_mode = "local"
    settings.audio_model_speaker_count = "unknown"
    monkeypatch.setattr(
        "app.core.transcription.transcription_dependency_status",
        lambda: {
            "whisper_available": True,
            "ffmpeg_available": True,
            "ffmpeg_path": "/usr/bin/ffmpeg",
        },
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/settings/audio-model", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is True
    profile = body["profile"]
    assert profile["provider"] == "local_whisper"
    assert profile["model"] == "whisper-base"
    assert profile["mode"] == "local"
    assert profile["has_credential"] is True
    assert profile["dispatch_available"] is True
    assert profile["capabilities"] == {
        "interview_audio": True, "microphone_chat": True, "channel_audio": True,
    }
    # Secret-free projection: credential references and URLs never surface.
    assert "credential_ref" not in body
    assert "credential_ref" not in profile
    assert "keychain://" not in response.text


@pytest.mark.asyncio
async def test_settings_audio_model_capabilities_reflect_runtime(auth_headers, monkeypatch):
    """Whisper unavailable at runtime -> local profile advertises no capabilities."""
    await init_db()
    settings.audio_model_provider = "local_whisper"
    settings.audio_model = "whisper-base"
    settings.audio_model_endpoint_id = "audio-local"
    settings.audio_model_mode = "local"
    monkeypatch.setattr(
        "app.core.transcription.transcription_dependency_status",
        lambda: {"whisper_available": False, "ffmpeg_available": False, "ffmpeg_path": None},
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/settings/audio-model", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is True
    assert body["profile"]["dispatch_available"] is True
    assert body["profile"]["capabilities"] == {
        "interview_audio": False, "microphone_chat": False, "channel_audio": False,
    }


@pytest.mark.asyncio
async def test_settings_audio_model_unsupported_provider_fails_closed(auth_headers):
    """Unsupported provider -> typed 503 (never a crash, never a fallback)."""
    await init_db()
    settings.audio_model_provider = "pi"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/settings/audio-model", headers=auth_headers)
    assert response.status_code == 503
    body = response.json()
    assert body["configured"] is False
    assert body["profile"] is None
    assert body["fallback"] == "unavailable"
    assert body["error"] == {"type": "audio_profile_invalid", "reason": "unsupported_provider"}
    assert body["research_data_status"] == "provisional_until_review"


@pytest.mark.asyncio
async def test_settings_audio_model_invalid_mode_fails_closed(auth_headers):
    """local_whisper with remote mode -> typed 503."""
    await init_db()
    settings.audio_model_provider = "local_whisper"
    settings.audio_model = "whisper-base"
    settings.audio_model_endpoint_id = "audio-local"
    settings.audio_model_mode = "remote"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/settings/audio-model", headers=auth_headers)
    assert response.status_code == 503
    body = response.json()
    assert body["configured"] is False
    assert body["error"] == {"type": "audio_profile_invalid", "reason": "local_whisper_remote_mode"}
