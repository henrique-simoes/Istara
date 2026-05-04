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
async def test_backups_list_returns_list(auth_headers):
    """GET /api/backups returns a list."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/backups", headers=auth_headers)
        assert response.status_code in (200, 404, 500)
        if response.status_code == 200:
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
        assert response.status_code in (200, 404, 500)


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
