"""Tests for Files API routes — upload, list, stats, content."""

import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.models.database import async_session, init_db
from app.core.auth import create_token
from app.models.document import Document, DocumentSource, DocumentStatus
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


@pytest.mark.asyncio
async def test_files_list_returns_list(auth_headers):
    """GET /api/files/{project_id} returns a list."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/files/test-project", headers=auth_headers)
        assert response.status_code in (200, 404)
        if response.status_code == 200:
            assert isinstance(response.json(), dict)


@pytest.mark.asyncio
async def test_files_list_requires_auth():
    """Files listing requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/files/test-project")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_files_stats_returns_response(auth_headers):
    """GET /api/files/{project_id}/stats returns file stats."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/files/test-project/stats", headers=auth_headers)
        assert response.status_code in (200, 404)


@pytest.mark.asyncio
async def test_audio_file_content_returns_stored_transcript(auth_headers, tmp_path, monkeypatch):
    """Audio previews expose the transcript persisted by background processing."""
    await init_db()
    project_id = f"audio-project-{uuid.uuid4()}"
    upload_dir = tmp_path / "uploads"
    project_dir = upload_dir / project_id
    project_dir.mkdir(parents=True)
    audio_path = project_dir / "stored-audio.wav"
    audio_path.write_bytes(b"RIFF....WAVE")
    monkeypatch.setattr(settings, "upload_dir", str(upload_dir))

    doc = Document(
        id=str(uuid.uuid4()),
        project_id=project_id,
        title="Interview Audio",
        file_name="interview.wav",
        file_path=str(audio_path),
        file_type=".wav",
        file_size=audio_path.stat().st_size,
        source=DocumentSource.USER_UPLOAD,
        status=DocumentStatus.READY,
        content_text="Participant: Eu preciso de busca melhor.",
        content_preview="Participant: Eu preciso de busca melhor.",
    )
    doc.set_tags(["feature-request", "interview"])
    doc.set_atomic_path(
        {
            "transcription": {
                "language": "pt",
                "confidence": 0.91,
                "icr_confidence": "high",
                "needs_review": False,
                "tags": ["feature-request", "interview"],
            }
        }
    )

    async with async_session() as db:
        db.add(Project(id=project_id, name="Audio Project"))
        db.add(doc)
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        content_response = await ac.get(
            f"/api/files/{project_id}/content/{audio_path.name}",
            headers=auth_headers,
        )
        list_response = await ac.get(f"/api/files/{project_id}", headers=auth_headers)

    assert content_response.status_code == 200
    payload = content_response.json()
    assert payload["content"] == "Participant: Eu preciso de busca melhor."
    assert payload["document_status"] == "ready"
    assert payload["transcription"]["language"] == "pt"
    assert "feature-request" in payload["tags"]

    listed = list_response.json()["files"][0]
    assert listed["display_name"] == "interview.wav"
    assert listed["has_transcript"] is True
    assert listed["transcription_language"] == "pt"


@pytest.mark.asyncio
async def test_linked_folder_media_can_be_served_and_previewed(auth_headers, tmp_path, monkeypatch):
    """Files linked from a project watch folder should use the same preview/serve path as uploads."""
    await init_db()
    project_id = f"linked-files-{uuid.uuid4()}"
    upload_dir = tmp_path / "uploads"
    linked_dir = tmp_path / "linked"
    upload_dir.mkdir()
    linked_dir.mkdir()
    image_path = linked_dir / "screen.png"
    image_bytes = b"\x89PNG\r\n\x1a\n"
    image_path.write_bytes(image_bytes)
    monkeypatch.setattr(settings, "upload_dir", str(upload_dir))

    doc = Document(
        id=str(uuid.uuid4()),
        project_id=project_id,
        title="Linked Screen",
        file_name=image_path.name,
        file_path=str(image_path),
        file_type=".png",
        file_size=len(image_bytes),
        source=DocumentSource.PROJECT_FILE,
        status=DocumentStatus.READY,
    )

    async with async_session() as db:
        db.add(Project(id=project_id, name="Linked File Project", watch_folder_path=str(linked_dir)))
        db.add(doc)
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        content_response = await ac.get(
            f"/api/files/{project_id}/content/{image_path.name}",
            headers=auth_headers,
        )
        serve_response = await ac.get(
            f"/api/files/{project_id}/serve/{image_path.name}",
            headers=auth_headers,
        )

    assert content_response.status_code == 200
    payload = content_response.json()
    assert payload["media_url"] == f"/api/files/{project_id}/serve/{image_path.name}"
    assert payload["document_id"] == doc.id
    assert serve_response.status_code == 200
    assert serve_response.content == image_bytes
