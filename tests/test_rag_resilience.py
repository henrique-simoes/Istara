"""RAG resilience tests for degraded compute environments."""

import pytest
from app.config import settings
from app.core import rag
from app.core.embeddings import TextChunk
from app.core.keyword_index import KeywordIndex


@pytest.mark.asyncio
async def test_ingest_chunks_preserves_keyword_index_when_embeddings_fail(tmp_path, monkeypatch):
    """Document ingestion should remain searchable when vector compute is offline."""
    monkeypatch.setattr(settings, "data_dir", str(tmp_path / "data"))
    monkeypatch.setattr(settings, "lance_db_path", str(tmp_path / "lance"))

    async def fail_embed_chunks(chunks):
        raise RuntimeError("No compute nodes available for batch embedding")

    monkeypatch.setattr(rag, "embed_chunks", fail_embed_chunks)

    project_id = "rag-degraded-ingest"
    chunks = [
        TextChunk(
            text="Participants struggle with onboarding setup and workspace invites.",
            source="interview.txt",
            page=1,
        )
    ]

    vector_count = await rag.ingest_chunks(project_id, chunks)

    assert vector_count == 0
    keyword_hits = await KeywordIndex(project_id).search("onboarding setup", top_k=3)
    assert keyword_hits
    assert keyword_hits[0].source == "interview.txt"


@pytest.mark.asyncio
async def test_retrieve_context_falls_back_to_keyword_search(tmp_path, monkeypatch):
    """Chat and agents should still retrieve evidence when embeddings are unavailable."""
    monkeypatch.setattr(settings, "data_dir", str(tmp_path / "data"))
    monkeypatch.setattr(settings, "lance_db_path", str(tmp_path / "lance"))

    async def fail_embed_text(text):
        raise RuntimeError("No compute nodes available for embedding")

    monkeypatch.setattr(rag, "embed_text", fail_embed_text)

    project_id = "rag-keyword-fallback"
    await KeywordIndex(project_id).add_chunks(
        [
            TextChunk(
                text="The checkout interview shows strong demand for clearer billing previews.",
                source="checkout-notes.md",
                page=2,
            )
        ]
    )

    context = await rag.retrieve_context(project_id, "clearer billing previews", top_k=3)

    assert context.has_context
    assert context.retrieved[0].source == "checkout-notes.md"
    assert "billing previews" in context.context_text
