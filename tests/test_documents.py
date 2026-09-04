"""Tests for Documents API routes — CRUD, search, sync, tags, stats."""

import pytest
import uuid
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from app.main import app
from app.config import settings
from app.models.database import async_session, init_db
from app.core.auth import create_token
from app.models.document import Document, DocumentSource, DocumentStatus
from app.models.project import Project
from app.models.research_validity import EvidenceUnit
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
    """GET /api/documents returns a list for an explicit active project."""
    await init_db()
    project_id = f"doc-list-project-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Document List Project"))
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(f"/api/documents?project_id={project_id}", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), dict)


@pytest.mark.asyncio
async def test_documents_list_requires_active_project(auth_headers):
    """Document library listing must not silently fall back to a global list."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/documents", headers=auth_headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "project_id is required"


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
    project_id = f"doc-missing-project-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Missing Document Project"))
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/documents/non-existent-id?project_id={project_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_documents_search_returns_list(auth_headers):
    """GET /api/documents/search/full returns search results."""
    await init_db()
    project_id = f"doc-search-project-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Document Search Project"))
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/documents/search/full?project_id={project_id}&q=test",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), dict)


@pytest.mark.asyncio
async def test_documents_sync_returns_response(auth_headers):
    """POST /api/documents/sync/{project_id} triggers file sync."""
    await init_db()
    project_id = f"doc-sync-empty-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Document Sync Empty Project"))
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(f"/api/documents/sync/{project_id}", headers=auth_headers)

    assert response.status_code == 200
    assert {"synced", "total"}.issubset(response.json())


@pytest.mark.asyncio
async def test_documents_sync_registers_file_created_in_linked_external_folder(
    auth_headers, tmp_path
):
    """Scenario-29 regression: a file created in a linked external folder must
    be registered by the next sync (same-host topology)."""
    await init_db()
    project_id = f"doc-sync-linked-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Document Sync Linked Project"))
        await db.commit()

    external_dir = tmp_path / "linked-external"
    external_dir.mkdir()
    external_name = f"external-test-{uuid.uuid4().hex[:8]}.txt"
    (external_dir / external_name).write_text("External folder test content")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        link = await ac.post(
            f"/api/projects/{project_id}/link-folder",
            headers=auth_headers,
            json={"folder_path": str(external_dir)},
        )
        assert link.status_code == 200, link.text
        first = await ac.post(f"/api/documents/sync/{project_id}", headers=auth_headers)
        assert first.status_code == 200, first.text
        assert first.json()["synced"] >= 1, first.json()
        before_total = first.json()["total"]
        second = await ac.post(f"/api/documents/sync/{project_id}", headers=auth_headers)
        assert second.status_code == 200, second.text
        assert second.json()["synced"] == 0, second.json()
        assert second.json()["total"] == before_total, second.json()


@pytest.mark.asyncio
async def test_document_create_registers_raw_source_evidence_units(auth_headers):
    """Document creation must enter the Research Spine as raw source units."""
    await init_db()
    project_id = f"doc-spine-create-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Document Spine Create Project"))
        await db.commit()

    source_text = (
        "Participant: Export is hidden behind too many menus.\n\n"
        "Moderator: What did you expect to happen next?"
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/documents",
            headers=auth_headers,
            json={
                "project_id": project_id,
                "title": "Interview Note",
                "file_name": "interview-note.txt",
                "file_type": ".txt",
                "content_text": source_text,
            },
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["research_spine"]["artifact_state"] == "raw_source"
    assert payload["research_spine"]["source_evidence_units"] >= 2
    assert payload["research_spine"]["report_allowed"] is False

    async with async_session() as db:
        units = (
            await db.execute(
                select(EvidenceUnit).where(EvidenceUnit.source_document_id == payload["id"])
            )
        ).scalars().all()

    assert len(units) == payload["research_spine"]["source_evidence_units"]
    assert {unit.unit_type for unit in units} == {"source_span"}
    assert all(unit.source_id.startswith(f"document:{payload['id']}:v1") for unit in units)
    assert any("Export is hidden" in unit.source_text for unit in units)


@pytest.mark.asyncio
async def test_documents_sync_dedupes_by_resolved_path_not_filename(
    auth_headers, tmp_path, monkeypatch
):
    """Linked-folder sync must not ignore different files that share a basename."""
    await init_db()
    monkeypatch.setattr(settings, "lance_db_path", str(tmp_path / "lance"))

    project_id = f"doc-sync-project-{uuid.uuid4()}"
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_dir.mkdir()
    second_dir.mkdir()
    first_file = first_dir / "same-name.txt"
    second_file = second_dir / "same-name.txt"
    first_file.write_text("", encoding="utf-8")
    second_file.write_text("", encoding="utf-8")

    existing_doc = Document(
        id=str(uuid.uuid4()),
        project_id=project_id,
        title="Existing Same Name",
        file_name=first_file.name,
        file_path=str(first_file),
        file_type=".txt",
        file_size=0,
        source=DocumentSource.PROJECT_FILE,
        status=DocumentStatus.READY,
    )

    async with async_session() as db:
        db.add(Project(id=project_id, name="Document Sync Project", watch_folder_path=str(second_dir)))
        db.add(existing_doc)
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(f"/api/documents/sync/{project_id}", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["synced"] == 1

    async with async_session() as db:
        result = await db.execute(
            select(Document).where(
                Document.project_id == project_id,
                Document.file_name == "same-name.txt",
            )
        )
        docs = result.scalars().all()

    assert len(docs) == 2
    assert str(second_file.resolve()) in {Path(doc.file_path).resolve().as_posix() for doc in docs}


@pytest.mark.asyncio
async def test_documents_sync_registers_raw_source_evidence_units(
    auth_headers, tmp_path, monkeypatch
):
    """Folder sync must not leave imported text outside the Research Spine."""
    await init_db()
    monkeypatch.setattr(settings, "lance_db_path", str(tmp_path / "lance"))

    project_id = f"doc-sync-spine-{uuid.uuid4()}"
    watch_dir = tmp_path / "watch"
    watch_dir.mkdir()
    source_file = watch_dir / "support-notes.txt"
    source_file.write_text(
        "Participant: The search filter resets every time.\n\n"
        "Observer: The participant repeated the workaround twice.",
        encoding="utf-8",
    )

    async with async_session() as db:
        db.add(Project(id=project_id, name="Document Sync Spine Project", watch_folder_path=str(watch_dir)))
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(f"/api/documents/sync/{project_id}", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["synced"] == 1

    async with async_session() as db:
        doc = (
            await db.execute(select(Document).where(Document.project_id == project_id))
        ).scalar_one()
        units = (
            await db.execute(select(EvidenceUnit).where(EvidenceUnit.source_document_id == doc.id))
        ).scalars().all()

    assert len(units) >= 2
    assert all(unit.unit_type == "source_span" for unit in units)


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
        response = await ac.get(
            f"/api/documents/{doc_id}/content?project_id={project_id}",
            headers=auth_headers,
        )

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
async def test_document_id_routes_require_active_project_match(auth_headers):
    """ID-based document routes must stay bound to the caller's active project."""
    await init_db()
    project_id = f"doc-bound-project-{uuid.uuid4()}"
    other_project_id = f"doc-bound-other-{uuid.uuid4()}"
    doc_id = str(uuid.uuid4())

    async with async_session() as db:
        db.add(Project(id=project_id, name="Document Bound Project"))
        db.add(Project(id=other_project_id, name="Other Document Bound Project"))
        db.add(
            Document(
                id=doc_id,
                project_id=project_id,
                title="Project Document",
                file_name="project.txt",
                file_type=".txt",
                status=DocumentStatus.READY,
                content_text="project only",
                content_preview="project only",
            )
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        get_response = await ac.get(
            f"/api/documents/{doc_id}?project_id={other_project_id}",
            headers=auth_headers,
        )
        content_response = await ac.get(
            f"/api/documents/{doc_id}/content?project_id={other_project_id}",
            headers=auth_headers,
        )
        update_response = await ac.patch(
            f"/api/documents/{doc_id}?project_id={other_project_id}",
            headers=auth_headers,
            json={"title": "Wrong Context"},
        )
        delete_response = await ac.delete(
            f"/api/documents/{doc_id}?project_id={other_project_id}",
            headers=auth_headers,
        )

    assert get_response.status_code == 404
    assert content_response.status_code == 404
    assert update_response.status_code == 404
    assert delete_response.status_code == 404

    async with async_session() as db:
        doc = await db.get(Document, doc_id)
    assert doc is not None
    assert doc.title == "Project Document"


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
        response = await ac.get(
            f"/api/documents/{doc_id}/content?project_id={project_id}",
            headers=auth_headers,
        )

    assert response.status_code == 200
    assert response.json()["content"] == "safe fallback"


@pytest.mark.asyncio
async def test_delete_managed_upload_removes_file_and_prevents_sync_resurrection(
    auth_headers, tmp_path, monkeypatch
):
    """Deleting an uploaded document must remove its managed file before folder sync sees it."""
    await init_db()
    upload_dir = tmp_path / "uploads"
    project_id = f"delete-upload-{uuid.uuid4()}"
    project_dir = upload_dir / project_id
    project_dir.mkdir(parents=True)
    uploaded_file = project_dir / "safe-upload.txt"
    uploaded_file.write_text("participant notes", encoding="utf-8")
    monkeypatch.setattr(settings, "upload_dir", str(upload_dir))
    doc_id = str(uuid.uuid4())

    async with async_session() as db:
        db.add(Project(id=project_id, name="Delete Upload Project"))
        db.add(
            Document(
                id=doc_id,
                project_id=project_id,
                title="Safe Upload",
                file_name="safe-upload.txt",
                file_path=str(uploaded_file),
                file_type=".txt",
                file_size=uploaded_file.stat().st_size,
                source=DocumentSource.USER_UPLOAD,
                status=DocumentStatus.READY,
            )
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        delete_response = await ac.delete(
            f"/api/documents/{doc_id}?project_id={project_id}", headers=auth_headers
        )
        sync_response = await ac.post(
            f"/api/documents/sync/{project_id}", headers=auth_headers
        )

    assert delete_response.status_code == 204
    assert not uploaded_file.exists()
    assert sync_response.status_code == 200
    assert sync_response.json()["synced"] == 0

    async with async_session() as db:
        assert await db.get(Document, doc_id) is None
        remaining = (
            await db.execute(select(Document).where(Document.project_id == project_id))
        ).scalars().all()
    assert remaining == []


@pytest.mark.asyncio
async def test_delete_project_file_never_removes_external_watch_file(
    auth_headers, tmp_path, monkeypatch
):
    """Deleting a linked-folder document must not delete the user's external source file."""
    await init_db()
    upload_dir = tmp_path / "uploads"
    watch_dir = tmp_path / "watch"
    upload_dir.mkdir()
    watch_dir.mkdir()
    project_id = f"delete-project-file-{uuid.uuid4()}"
    external_file = watch_dir / "research.txt"
    external_file.write_text("keep this source", encoding="utf-8")
    monkeypatch.setattr(settings, "upload_dir", str(upload_dir))
    doc_id = str(uuid.uuid4())

    async with async_session() as db:
        db.add(
            Project(
                id=project_id,
                name="Delete Linked File Project",
                watch_folder_path=str(watch_dir),
            )
        )
        db.add(
            Document(
                id=doc_id,
                project_id=project_id,
                title="Linked Research",
                file_name=external_file.name,
                file_path=str(external_file),
                file_type=".txt",
                file_size=external_file.stat().st_size,
                source=DocumentSource.PROJECT_FILE,
                status=DocumentStatus.READY,
            )
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.delete(
            f"/api/documents/{doc_id}?project_id={project_id}", headers=auth_headers
        )

    assert response.status_code == 204
    assert external_file.exists()
