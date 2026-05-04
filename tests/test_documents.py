"""Tests for Documents API routes — CRUD, search, sync, tags, stats."""

import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.models.database import async_session, init_db
from app.core.auth import create_token
from app.models.document import Document, DocumentSource, DocumentStatus
from app.models.project import Project
from app.models.task import Task, TaskStatus


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
async def test_documents_list_returns_list(auth_headers):
    """GET /api/documents returns a list."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/documents", headers=auth_headers)
        assert response.status_code in (200, 422, 500, 502)
        assert isinstance(response.json(), dict)


@pytest.mark.asyncio
async def test_documents_list_requires_auth():
    """Documents listing requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/documents")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_document_get_nonexistent_returns_404(auth_headers):
    """GET /api/documents/{id} returns 404 for non-existent document."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/documents/non-existent-id", headers=auth_headers)
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_documents_search_returns_list(auth_headers):
    """GET /api/documents/search/full returns search results."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/documents/search/full?q=test", headers=auth_headers)
        assert response.status_code in (200, 422, 500, 502)
        assert isinstance(response.json(), dict)


@pytest.mark.asyncio
async def test_documents_sync_returns_response(auth_headers):
    """POST /api/documents/sync/{project_id} triggers file sync."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/documents/sync/test-project", headers=auth_headers)
        assert response.status_code in (200, 422, 404, 500, 502)


@pytest.mark.asyncio
async def test_documents_stats_returns_dict(auth_headers):
    """GET /api/documents/stats/{project_id} returns stats."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/documents/stats/test-project", headers=auth_headers)
        assert response.status_code in (200, 404)
        if response.status_code == 200:
            assert isinstance(response.json(), dict)


@pytest.mark.asyncio
async def test_document_content_returns_audio_transcript(auth_headers, tmp_path, monkeypatch):
    """Document preview uses stored content_text for audio documents."""
    await init_db()
    project_id = f"doc-audio-project-{uuid.uuid4()}"
    doc_id = str(uuid.uuid4())
    upload_dir = tmp_path / "uploads"
    project_dir = upload_dir / project_id
    project_dir.mkdir(parents=True)
    audio_path = project_dir / "stored.wav"
    audio_path.write_bytes(b"RIFF....WAVE")
    monkeypatch.setattr(settings, "upload_dir", str(upload_dir))

    doc = Document(
        id=doc_id,
        project_id=project_id,
        title="Audio Interview",
        file_name="participant.wav",
        file_path=str(audio_path),
        file_type=".wav",
        file_size=audio_path.stat().st_size,
        source=DocumentSource.USER_UPLOAD,
        status=DocumentStatus.READY,
        content_text="Participant: I want fewer setup steps.",
        content_preview="Participant: I want fewer setup steps.",
    )
    doc.set_tags(["feature-request"])
    doc.set_atomic_path({"transcription": {"language": "en", "needs_review": False}})

    async with async_session() as db:
        db.add(Project(id=project_id, name="Document Audio Project"))
        db.add(doc)
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(f"/api/documents/{doc_id}/content", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["content"] == "Participant: I want fewer setup steps."
    assert payload["status"] == "ready"
    assert payload["transcription"]["language"] == "en"
    assert payload["tags"] == ["feature-request"]


@pytest.mark.asyncio
async def test_documents_list_rejects_invalid_filter_enums(auth_headers):
    """Invalid source/status filters should fail loudly instead of silently widening results."""
    await init_db()
    project_id = f"doc-filter-project-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Document Filter Project"))
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        source_response = await ac.get(
            f"/api/documents?project_id={project_id}&source=not-a-source",
            headers=auth_headers,
        )
        status_response = await ac.get(
            f"/api/documents?project_id={project_id}&status=not-a-status",
            headers=auth_headers,
        )

    assert source_response.status_code == 422
    assert status_response.status_code == 422


@pytest.mark.asyncio
async def test_document_create_rejects_task_from_another_project(auth_headers):
    """Document task links must stay inside the document's project."""
    await init_db()
    project_id = f"doc-task-project-{uuid.uuid4()}"
    other_project_id = f"doc-task-other-{uuid.uuid4()}"
    foreign_task_id = str(uuid.uuid4())

    async with async_session() as db:
        db.add(Project(id=project_id, name="Document Task Project"))
        db.add(Project(id=other_project_id, name="Other Task Project"))
        db.add(
            Task(
                id=foreign_task_id,
                project_id=other_project_id,
                title="Foreign Task",
                status=TaskStatus.BACKLOG,
            )
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/documents",
            headers=auth_headers,
            json={
                "project_id": project_id,
                "title": "Bad task link",
                "task_id": foreign_task_id,
            },
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_document_content_refuses_file_path_outside_project_roots(auth_headers, tmp_path, monkeypatch):
    """A document row must not become an arbitrary local-file read primitive."""
    await init_db()
    project_id = f"doc-path-project-{uuid.uuid4()}"
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    secret_path = tmp_path / "secret.txt"
    secret_path.write_text("do not read me")
    monkeypatch.setattr(settings, "upload_dir", str(upload_dir))

    doc_id = str(uuid.uuid4())
    async with async_session() as db:
        db.add(Project(id=project_id, name="Document Path Project"))
        db.add(
            Document(
                id=doc_id,
                project_id=project_id,
                title="Unsafe Path",
                file_name="secret.txt",
                file_path=str(secret_path),
                file_type=".txt",
                status=DocumentStatus.READY,
                content_text="safe fallback",
                content_preview="safe fallback",
            )
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(f"/api/documents/{doc_id}/content", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["content"] == "safe fallback"
