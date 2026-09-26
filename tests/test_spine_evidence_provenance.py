"""Source evidence stays source evidence, and every source chunk traces to an evidence unit.

F5 (2026-09-25 map): skill artifacts (LLM output) and agent "private" notes were ingested into the
project's source evidence index at confidence 1.0, so they could confirm claims through
``self_check.verify_claim``. Notes were shared with every retrieval, read back by a vector top-k
then a substring filter, which let other rows crowd them out and let agent ``a1`` match ``a10``.
Contract: evidence units come from raw source spans (AGENTS.md; research-validity contract,
"Hard Rules"); W3C PROV separates an entity's generation (wasGeneratedBy an agent) from a source
(wasDerivedFrom). PoisonedRAG (Zou et al. 2024) shows why injected text in the retrieval corpus
steers verification.

Measurement 5: no production path set ``evidence_unit_id`` on a retrieved chunk, and
``retrieval_metadata_for_unit`` had no callers. Coverage was 0%.

F7: the file watcher deleted a file's rows from BOTH indices and re-added only vectors.
F15: with file encryption on, knowledge sync indexed ciphertext, and the chat
``search_documents`` tool matched ``ILIKE`` against ciphertext.
F17 (part): a backslash path never matched its own rows on delete; a 0.0 threshold was "unset".
"""

from __future__ import annotations

import hashlib
import math
import re
import uuid
from types import SimpleNamespace

import pytest

from app.config import settings
from app.core import rag
from app.core.embeddings import EmbeddedChunk, TextChunk


def _vec(text: str) -> list[float]:
    """Deterministic bag-of-words embedding: overlapping words give real cosine similarity."""
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
    # Every module that bound the embedder at import time sees the same deterministic one, so a
    # test fails on its assertion, never on an unrelated network call.
    monkeypatch.setattr("app.core.embeddings.embed_chunks", _embed_chunks)
    monkeypatch.setattr("app.core.embeddings.embed_text", _embed_text)
    monkeypatch.setattr("app.core.file_watcher.embed_chunks", _embed_chunks, raising=False)
    return tmp_path


async def _source_rows(project_id: str) -> list[dict]:
    store = rag.VectorStore(project_id)
    if not store._ensure_table():
        return []
    return store.db.open_table(store.table_name).search().limit(10_000).to_list()


# ── F5: derived text never confirms a claim ──────────────────────────────


async def test_claim_verification_never_sees_agent_notes_or_skill_artifacts(indices, monkeypatch):
    from app.core.agent_memory import agent_memory
    from app.core.self_check import verify_claim

    project_id = f"f5-{uuid.uuid4().hex[:8]}"
    claim = "Checkout abandonment is caused by shipping fees"
    await rag.ingest_chunks(
        project_id,
        [
            TextChunk(
                text="P2 said the checkout page loads slowly on mobile data.",
                source="/uploads/p/interview-02.md",
            )
        ],
    )
    # An agent note and a skill artifact that assert the claim, written through the real paths
    # (the note) and as a pre-fix build stored artifacts (source-table row, ``skill:`` source).
    await agent_memory.write_note("istara-main", project_id, f"{claim}, obviously.")
    legacy = TextChunk(
        text=f"{claim} (thematic analysis artifact).", source="skill:thematic-analysis:report.md"
    )
    await rag.VectorStore(project_id).add_chunks([EmbeddedChunk(legacy, _vec(legacy.text))])

    prompts: list[str] = []

    async def _structured(**kwargs):
        prompts.append(kwargs["messages"][0]["content"])
        return SimpleNamespace(
            status="success",
            value={
                "confidence": "HIGH",
                "supporting": ["any"],
                "contradicting": [],
                "notes": "",
            },
        )

    monkeypatch.setattr("app.core.agentic.agentic", SimpleNamespace(structured=_structured))

    await verify_claim(claim, project_id)

    assert prompts, "the source document is still consulted"
    sources = prompts[0].split("## Source Documents", 1)[1].split("## Instructions", 1)[0]
    assert "interview-02.md" in sources
    assert "shipping fees" not in sources, "model output confirmed its own claim"
    assert "agent:" not in sources and "skill:" not in sources


async def test_agent_notes_are_scoped_exactly_and_not_crowded_out(indices):
    from app.core.agent_memory import agent_memory

    project_id = f"notes-{uuid.uuid4().hex[:8]}"
    await rag.ingest_chunks(
        project_id,
        [
            TextChunk(
                text=f"Onboarding invites confuse participant P{i} during setup.",
                source=f"/uploads/p/interview-{i:02d}.md",
            )
            for i in range(30)
        ],
    )
    await agent_memory.write_note("a1", project_id, "Onboarding invites need a reminder email.")
    await agent_memory.write_note("a10", project_id, "Onboarding invites of agent ten.")

    ranked = await agent_memory.read_notes("a1", project_id, query="onboarding invites", limit=3)
    assert [n["text"] for n in ranked] == ["Onboarding invites need a reminder email."]

    listed = await agent_memory.get_all_notes(project_id, "a1")
    assert [n["text"] for n in listed] == ["Onboarding invites need a reminder email."]

    evidence = await rag.retrieve_context(project_id, "onboarding invites reminder", top_k=10)
    assert all(not rag.is_derived_source(r.source) for r in evidence.retrieved)


async def test_skill_artifacts_go_to_the_derived_index_whole_and_once(indices):
    from app.core.agent import AgentOrchestrator
    from app.models.database import async_session, init_db
    from app.models.project import Project
    from app.models.task import Task, TaskStatus
    from app.skills.base import SkillOutput

    project_id = f"artifacts-{uuid.uuid4().hex[:8]}"
    body = "## Theme: invoice chasing\n" + ("Owners chase invoices by phone. " * 180) + "END-MARKER"
    await init_db()
    async with async_session() as db:
        task = Task(
            id=str(uuid.uuid4()),
            project_id=project_id,
            title="Synthesize invoices",
            skill_name="thematic-analysis",
            status=TaskStatus.IN_PROGRESS,
        )
        db.add_all([Project(id=project_id, name="Artifacts"), task])
        await db.commit()
        output = SkillOutput(success=True, summary="s", artifacts={"themes.md": body})
        orchestrator = AgentOrchestrator()
        await orchestrator._store_findings(db, project_id, output, task)
        derived = rag.VectorStore(project_id, table_name=rag.DERIVED_TABLE)
        first = derived.db.open_table(derived.table_name).count_rows()
        await orchestrator._store_findings(db, project_id, output, task)
        second = derived.db.open_table(derived.table_name).count_rows()

    assert first == second > 2, "re-running the skill replaces its rows instead of duplicating"
    rows = derived.db.open_table(derived.table_name).search().limit(1000).to_list()
    assert any("END-MARKER" in row["text"] for row in rows), "no silent 2,000-character cut"
    assert not [r for r in await _source_rows(project_id) if "chase invoices" in r["text"]]


# ── Measurement 5: every uploaded source chunk carries its evidence unit ──


async def test_uploaded_chunks_carry_their_evidence_unit_and_coverage_is_one(indices):
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import select

    from app.core.auth import create_token
    from app.main import app
    from app.models.database import async_session, init_db
    from app.models.project import Project
    from app.models.research_validity import EvidenceUnit

    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    headers = {"Authorization": f"Bearer {create_token('u1', 'tester', 'admin')}"}
    project_id = f"prov-{uuid.uuid4().hex[:8]}"
    turns = "\n\n".join(
        f"Interviewer: What happened in week {i}?\n\nP{i % 5 + 1}: The receipt upload failed at "
        f"the counter and I retried {i} times before giving up on the scanner."
        for i in range(40)
    )
    await init_db()
    async with async_session() as db:
        db.add(Project(id=project_id, name="Provenance"))
        await db.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/files/upload/{project_id}",
            headers=headers,
            files={"file": ("receipts-interview.md", turns.encode(), "text/markdown")},
        )
        assert response.status_code == 200, response.text
        stats = (await client.get(f"/api/memory/{project_id}/stats", headers=headers)).json()

    doc_id = response.json()["doc_id"]
    async with async_session() as db:
        units = {
            u.id: u
            for u in (
                await db.execute(
                    select(EvidenceUnit).where(EvidenceUnit.source_document_id == doc_id)
                )
            ).scalars()
        }
    rows = await _source_rows(project_id)
    assert rows and units
    for row in rows:
        unit = units.get(row["evidence_unit_id"])
        assert unit is not None, "every source chunk names a real evidence unit of its document"
        assert row["source_document_id"] == doc_id
        assert row["start_offset"] < unit.end_offset and unit.start_offset < row["end_offset"]
    assert stats["provenance"]["coverage"] == 1.0
    hits = await rag.retrieve_context(project_id, "receipt upload failed at the counter", top_k=5)
    assert hits.retrieved and all(r.evidence_unit_id for r in hits.retrieved)
    assert rag.provenance_share(hits.retrieved) == 1.0


# ── F7: the watcher keeps BM25 rows ───────────────────────────────────────


async def test_file_watcher_reindex_keeps_keyword_rows(indices):
    from app.core.file_watcher import FileWatcher
    from app.core.keyword_index import KeywordIndex
    from app.models.database import async_session, init_db
    from app.models.project import Project

    project_id = f"watch-{uuid.uuid4().hex[:8]}"
    watched = indices / "watched"
    watched.mkdir()
    note = watched / "field-notes.md"
    note.write_text("P3 photographs receipts with the tablet camera at close.\n")
    await init_db()
    async with async_session() as db:
        db.add(Project(id=project_id, name="Watched"))
        await db.commit()

    watcher = FileWatcher()
    await watcher._process_file(note, project_id)
    note.write_text("P3 photographs receipts with the tablet camera. Glare ruins every scan.\n")
    watcher._processed_files.clear()
    await watcher._process_file(note, project_id)

    hits = await KeywordIndex(project_id).search("glare scan", top_k=5)
    assert hits and "Glare ruins" in hits[0].text
    assert await KeywordIndex(project_id).count() == await rag.VectorStore(project_id).count()


# ── F15: no ciphertext in the index; search works under encryption ────────


async def _encrypted_document(project_id: str, text: str, monkeypatch):
    from cryptography.fernet import Fernet

    from app.core.file_encryption import protect_document_text
    from app.models.database import async_session, init_db
    from app.models.document import Document, DocumentStatus
    from app.models.project import Project

    monkeypatch.setattr(settings, "file_encryption_enabled", True)
    monkeypatch.setattr(settings, "file_encryption_key", Fernet.generate_key().decode())
    await init_db()
    async with async_session() as db:
        db.add(Project(id=project_id, name="Encrypted"))
        db.add(
            Document(
                id=str(uuid.uuid4()),
                project_id=project_id,
                title="Receipts",
                file_name="gone.md",
                file_path="/nowhere/gone.md",
                status=DocumentStatus.READY,
                content_text=protect_document_text(text),
            )
        )
        await db.commit()


async def test_knowledge_sync_indexes_plaintext_not_ciphertext(indices, monkeypatch):
    from app.core.file_encryption import TEXT_PREFIX
    from app.core.keyword_index import KeywordIndex
    from app.models.database import async_session
    from app.services.knowledge_sync import KnowledgeSyncService

    project_id = f"enc-{uuid.uuid4().hex[:8]}"
    await _encrypted_document(
        project_id, "Bookkeepers photograph receipts at month end.", monkeypatch
    )
    async with async_session() as db:
        await KnowledgeSyncService().sync_project(project_id, db)

    hits = await KeywordIndex(project_id).search("photograph receipts", top_k=3)
    assert hits and "Bookkeepers photograph receipts" in hits[0].text
    assert not [r for r in await _source_rows(project_id) if r["text"].startswith(TEXT_PREFIX)]


async def test_chat_search_documents_matches_encrypted_content(indices, monkeypatch):
    from app.skills.system_actions import _exec_search_documents

    project_id = f"encsearch-{uuid.uuid4().hex[:8]}"
    await _encrypted_document(
        project_id, "The reconciliation screen hides the variance column.", monkeypatch
    )
    answer = await _exec_search_documents({"query": "variance column"}, project_id, "istara-main")
    assert "Found 1 document" in answer


# ── F17 (part): backslash paths and an explicit zero threshold ────────────


async def test_delete_by_source_removes_a_windows_style_path(indices):
    project_id = f"win-{uuid.uuid4().hex[:8]}"
    source = "C:\\Users\\research\\interview.md"
    chunk = TextChunk(text="Windows path chunk about receipts.", source=source)
    await rag.ingest_chunks(project_id, [chunk])
    await rag.VectorStore(project_id).delete_by_source(source)
    assert await rag.VectorStore(project_id).count() == 0


async def test_zero_score_threshold_is_a_value_not_unset(indices):
    project_id = f"zero-{uuid.uuid4().hex[:8]}"
    await rag.ingest_chunks(
        project_id,
        [
            TextChunk(text="alpha beta gamma delta epsilon zeta eta theta", source="/u/a.md"),
            TextChunk(text="receipts", source="/u/b.md"),
        ],
    )
    query = _vec("receipts alpha kappa lambda mu nu xi omicron pi rho")
    everything = await rag.VectorStore(project_id).search(query, top_k=10, score_threshold=0.0)
    assert {r.source for r in everything} == {"/u/a.md", "/u/b.md"}
