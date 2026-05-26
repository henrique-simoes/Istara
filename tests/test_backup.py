"""Tests for Backup API routes — list, create, restore, verify, config, estimate."""

import io
import json
import tarfile
import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.models.backup import BackupRecord
from app.models.database import async_session, init_db
from app.core.auth import create_token
from app.core.backup_manager import BackupManager


@pytest.fixture(autouse=True)
def reset_settings():
    original_team_mode = settings.team_mode
    original_jwt_secret = settings.jwt_secret
    original_file_encryption_enabled = settings.file_encryption_enabled
    original_file_encryption_key = settings.file_encryption_key
    original_file_encryption_key_file = settings.file_encryption_key_file
    original_file_encryption_keychain_service = settings.file_encryption_keychain_service
    yield
    settings.team_mode = original_team_mode
    settings.jwt_secret = original_jwt_secret
    settings.file_encryption_enabled = original_file_encryption_enabled
    settings.file_encryption_key = original_file_encryption_key
    settings.file_encryption_key_file = original_file_encryption_key_file
    settings.file_encryption_keychain_service = original_file_encryption_keychain_service


@pytest.fixture
def auth_headers():
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    token = create_token("user1", "testuser", "admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_backups_list_returns_list(auth_headers):
    """GET /api/backups returns a list."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/backups", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), dict)


@pytest.mark.asyncio
async def test_backups_list_requires_auth():
    """Backups listing requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/backups")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_backups_config_returns_response(auth_headers):
    """GET /api/backups/config returns backup configuration."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/backups/config", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), dict)


@pytest.mark.asyncio
async def test_backup_config_rejects_out_of_range_values(auth_headers):
    """Invalid scheduler values should fail validation before touching .env."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/backups/config",
            json={"backup_interval_hours": 0},
            headers=auth_headers,
        )
    assert response.status_code == 422


def _backup_tar_bytes(members: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name, content in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
    buffer.seek(0)
    return buffer.read()


@pytest.mark.asyncio
async def test_upload_restore_accepts_valid_manifest_only_archive(auth_headers, tmp_path, monkeypatch):
    """Upload restore should call the real restore path and not a missing method."""
    await init_db()
    monkeypatch.setattr(settings, "backup_dir", str(tmp_path / "backups"))
    archive = _backup_tar_bytes(
        {
            "manifest.json": json.dumps(
                {"version": "1.0", "checksums": {}, "components": {}}
            ).encode(),
        }
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/backups/upload-restore",
            files={"file": ("restore.tar.gz", archive, "application/gzip")},
            headers=auth_headers,
        )

    assert response.status_code == 200
    assert response.json()["status"] == "restored"


@pytest.mark.asyncio
async def test_upload_restore_rejects_path_traversal_archive(auth_headers, tmp_path, monkeypatch):
    """Restore must reject archives that try to write outside the extraction dir."""
    await init_db()
    monkeypatch.setattr(settings, "backup_dir", str(tmp_path / "backups"))
    archive = _backup_tar_bytes({"../escape.txt": b"nope"})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/backups/upload-restore",
            files={"file": ("restore.tar.gz", archive, "application/gzip")},
            headers=auth_headers,
        )

    assert response.status_code == 400
    assert "Unsafe archive member path" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_restore_accepts_encrypted_backup_archive(auth_headers, tmp_path, monkeypatch):
    """Encrypted .tar.gz.enc archives restore when the configured key is present."""
    from app.core.file_encryption import encrypt_bytes, resolve_file_encryption_key

    await init_db()
    monkeypatch.setattr(settings, "backup_dir", str(tmp_path / "backups"))
    monkeypatch.setattr(settings, "file_encryption_enabled", True)
    monkeypatch.setattr(settings, "file_encryption_key", "")
    monkeypatch.setattr(settings, "file_encryption_key_file", str(tmp_path / "file-encryption.key"))
    monkeypatch.setattr(settings, "file_encryption_keychain_service", "")
    resolve_file_encryption_key(create=True)

    archive = _backup_tar_bytes(
        {
            "manifest.json": json.dumps(
                {"version": "1.0", "checksums": {}, "components": {}}
            ).encode(),
        }
    )
    encrypted_archive = encrypt_bytes(archive)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/backups/upload-restore",
            files={"file": ("restore.tar.gz.enc", encrypted_archive, "application/octet-stream")},
            headers=auth_headers,
        )

    assert response.status_code == 200
    assert response.json()["status"] == "restored"


@pytest.mark.asyncio
async def test_backup_download_rejects_record_filename_traversal(auth_headers, tmp_path, monkeypatch):
    """A poisoned backup record must not let download escape backup_dir."""
    await init_db()
    monkeypatch.setattr(settings, "backup_dir", str(tmp_path / "backups"))
    backup_id = str(uuid.uuid4())
    async with async_session() as db:
        db.add(
            BackupRecord(
                id=backup_id,
                filename="../secret.tar.gz",
                backup_type="full",
                status="completed",
            )
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(f"/api/backups/{backup_id}/download", headers=auth_headers)

    assert response.status_code == 404


def test_backup_copy_excludes_secret_and_local_model_artifacts(tmp_path):
    src = tmp_path / "src"
    dest = tmp_path / "dest"
    src.mkdir()
    (src / "notes.txt").write_text("safe", encoding="utf-8")
    (src / ".env").write_text("TOKEN=secret", encoding="utf-8")
    (src / "private.pem").write_text("secret", encoding="utf-8")
    model_dir = src / "LLMs"
    model_dir.mkdir()
    (model_dir / "model.gguf").write_bytes(b"large local model")

    checksums: dict[str, str] = {}
    BackupManager()._copy_dir(
        str(src),
        str(dest),
        "archive",
        checksums,
        "full",
        {},
    )

    assert (dest / "notes.txt").exists()
    assert not (dest / ".env").exists()
    assert not (dest / "private.pem").exists()
    assert not (dest / "LLMs").exists()
    assert sorted(checksums) == ["archive/notes.txt"]
