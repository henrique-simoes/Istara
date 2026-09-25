"""A file uploaded through the product is ingested once (found on the live lane, 2026-09-25).

Every project's upload directory is also a watched directory, so each upload was indexed twice:
by the upload route and by the file watcher reacting to the new file, seconds apart. The keyword
index replaces rows, the vector store appended them: after uploading the 67-file Harbor Ledger
corpus the vector store held 2,134 rows for 1,097 distinct spans (1,037 spans twice, 0-35 s
apart). Duplicate passages crowd retrieval's top-k and the prompt's RAG budget. The upload route
owns the whole ingestion of its files (Document, evidence units, both indices), so the watcher
leaves them alone, and the route creates the research tasks the watcher used to create.
"""

from __future__ import annotations

import hashlib
import math
import re
import uuid

import pytest

from app.config import settings
from app.core import rag
from app.core.embeddings import EmbeddedChunk


def _vec(text: str) -> list[float]:
    v = [0.0] * 64
    for token in re.findall(r"\w+", text.lower()):
        v[int(hashlib.md5(token.encode()).hexdigest(), 16) % 64] += 1.0
    norm = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / norm for x in v]


@pytest.fixture
def indices(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", str(tmp_path / "data"))
    monkeypatch.setattr(settings, "keyword_index_dir", None)
    monkeypatch.setattr(settings, "lance_db_path", str(tmp_path / "lance"))
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))

    async def _embed_chunks(chunks, batch_size: int = 32):
        return [EmbeddedChunk(chunk=c, vector=_vec(c.text)) for c in chunks]

    async def _embed_text(text):
        return _vec(text)

    monkeypatch.setattr(rag, "embed_chunks", _embed_chunks)
    monkeypatch.setattr(rag, "embed_text", _embed_text)
    monkeypatch.setattr("app.core.embeddings.embed_chunks", _embed_chunks)
    monkeypatch.setattr("app.core.embeddings.embed_text", _embed_text)
    monkeypatch.setattr("app.core.file_watcher.embed_chunks", _embed_chunks, raising=False)
    return tmp_path


TURNS = "\n\n".join(
    f"Interviewer: What happened in week {i}?\n\nP{i % 5 + 1}: The receipt upload failed at the "
    f"counter and I retried {i} times before giving up on the scanner."
    for i in range(30)
)


async def _project(name: str) -> str:
    from app.models.database import async_session, init_db
    from app.models.project import Project

    project_id = f"{name}-{uuid.uuid4().hex[:8]}"
    await init_db()
    async with async_session() as db:
        db.add(Project(id=project_id, name=name))
        await db.commit()
    return project_id


async def _upload(project_id: str) -> dict:
    from httpx import ASGITransport, AsyncClient

    from app.core.auth import create_token
    from app.main import app

    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    headers = {"Authorization": f"Bearer {create_token('u1', 'tester', 'admin')}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/files/upload/{project_id}",
            headers=headers,
            files={"file": ("receipts-notes.md", TURNS.encode(), "text/markdown")},
        )
    assert response.status_code == 200, response.text
    return response.json()


async def test_the_watcher_leaves_files_uploaded_through_the_product_alone(indices, monkeypatch):
    from app.core.file_watcher import FileWatcher

    project_id = await _project("single-ingest")
    upload_dir = indices / "uploads" / project_id
    upload_dir.mkdir(parents=True)
    saved = upload_dir / f"{uuid.uuid4()}.md"
    saved.write_text(TURNS, encoding="utf-8")

    writes: list[str] = []
    original = rag.VectorStore.add_chunks

    async def _spy(self, chunks):
        writes.append(self.project_id)
        return await original(self, chunks)

    monkeypatch.setattr(rag.VectorStore, "add_chunks", _spy)
    result = await FileWatcher()._process_file(saved, project_id)
    assert result is None
    assert writes == [], "the watcher indexed a file the upload route already ingests"


async def test_an_upload_is_indexed_once_and_still_creates_its_research_tasks(indices):
    from sqlalchemy import select

    from app.core.keyword_index import KeywordIndex
    from app.models.database import async_session
    from app.models.task import Task

    project_id = await _project("upload-tasks")
    body = await _upload(project_id)

    assert await rag.VectorStore(project_id).count() == await KeywordIndex(project_id).count()
    async with async_session() as db:
        tasks = (
            (await db.execute(select(Task).where(Task.project_id == project_id))).scalars().all()
        )
    assert [t.skill_name for t in tasks] == ["research-synthesis"], [
        (t.skill_name, t.title) for t in tasks
    ]
    assert body["saved_as"] in tasks[0].description
