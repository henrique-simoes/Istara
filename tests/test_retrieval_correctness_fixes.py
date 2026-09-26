"""Regression tests for four retrieval/persona defects found by the September 2026 evaluation.

Each test fails on the code before the fix and passes after it:

* re-ingesting a file must not accumulate duplicate chunks (sources are stored as the full path,
  deletes used the basename);
* keyword (BM25) search must rank every query term, not only an exact phrase, and must keep
  two-character research tokens such as "UX" and participant ids;
* the first self-evolution promotion into a persona file must not replace the agent's persona
  with a one-section overlay;
* the compressed chat/interface RAG context must carry source labels and the untrusted-content
  wrapper, and report only the sources that reached the prompt.
"""

from pathlib import Path

import pytest

from app.config import settings
from app.core import rag
from app.core.embeddings import TextChunk
from app.core.keyword_index import KeywordIndex, _fts_terms


def _use_tmp_indices(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", str(tmp_path / "data"))
    monkeypatch.setattr(settings, "keyword_index_dir", None)
    monkeypatch.setattr(settings, "lance_db_path", str(tmp_path / "lance"))


@pytest.mark.asyncio
async def test_delete_file_source_removes_rows_stored_under_the_full_path(tmp_path, monkeypatch):
    _use_tmp_indices(tmp_path, monkeypatch)
    project_id = "reingest-dedup"
    upload = tmp_path / "uploads" / project_id / "3f2c-interview.txt"
    index = KeywordIndex(project_id)
    # process_file stores the full path; an older row may carry only the basename.
    await index.add_chunks([
        TextChunk(text="Participants struggle with onboarding.", source=str(upload), page=1),
        TextChunk(text="Legacy row for the same upload.", source=upload.name, page=1),
    ])
    assert await index.count() == 2

    await rag.VectorStore(project_id).delete_file_source(upload)

    assert await index.count() == 0


@pytest.mark.asyncio
async def test_keyword_search_returns_non_adjacent_matches_after_the_phrase_hit(tmp_path, monkeypatch):
    _use_tmp_indices(tmp_path, monkeypatch)
    index = KeywordIndex("bm25-or")
    await index.add_chunks([
        TextChunk(text="Billing previews were confusing during checkout.", source="a.md", page=1),
        TextChunk(text="The checkout page hid the previews behind a billing tab.", source="b.md", page=1),
        TextChunk(text="Unrelated note about workspace invites.", source="c.md", page=1),
    ])

    hits = await index.search("billing previews", top_k=5)
    sources = [h.source for h in hits]

    assert sources[0] == "a.md"          # the exact phrase still ranks first
    assert "b.md" in sources              # ...but no longer suppresses the other match
    assert "c.md" not in sources


@pytest.mark.asyncio
async def test_keyword_search_keeps_two_character_research_tokens(tmp_path, monkeypatch):
    _use_tmp_indices(tmp_path, monkeypatch)
    index = KeywordIndex("bm25-short")
    await index.add_chunks([
        TextChunk(text="P1 said the UX of the export flow was slow.", source="p1.md", page=1),
        TextChunk(text="P2 liked the dashboard.", source="p2.md", page=1),
    ])

    assert "ux" in _fts_terms("what did P1 say about UX")
    assert "the" not in _fts_terms("what did P1 say about the UX")
    hits = await index.search("UX", top_k=3)
    assert [h.source for h in hits] == ["p1.md"]


def test_first_promotion_seeds_the_overlay_from_the_source_persona(tmp_path, monkeypatch):
    from app.core import agent_identity, self_evolution

    source_dir = tmp_path / "source"
    runtime_dir = tmp_path / "runtime"
    (source_dir / "agent-x").mkdir(parents=True)
    (source_dir / "agent-x" / "CORE.md").write_text(
        "# Agent X\n\n## Identity\nA careful researcher.\n\n## Values\n- rigor\n", encoding="utf-8"
    )
    monkeypatch.setattr(agent_identity, "SOURCE_PERSONAS_DIR", source_dir)
    monkeypatch.setattr(settings, "runtime_personas_dir", str(runtime_dir))

    assert self_evolution._append_to_persona_file(
        "agent-x", "CORE.md", "## Learned Preferences", "prefers concise summaries"
    )

    overlay = (runtime_dir / "agent-x" / "CORE.md").read_text(encoding="utf-8")
    assert "## Identity" in overlay and "A careful researcher." in overlay
    assert "## Learned Preferences" in overlay and "- prefers concise summaries" in overlay
    assert agent_identity.persona_file_path("agent-x", "CORE.md") == runtime_dir / "agent-x" / "CORE.md"


@pytest.mark.asyncio
async def test_compressed_rag_context_is_labelled_wrapped_and_cites_only_kept_chunks(monkeypatch):
    async def no_telemetry(**_kwargs):
        return None

    monkeypatch.setattr("app.core.prompt_compressor.record_protected_compression_telemetry", no_telemetry)
    results = [
        rag.RetrievalResult(text="Billing previews confused every participant. " * 20, source="interviews/p1.md", page=2, score=0.016),
        rag.RetrievalResult(text="Unrelated appendix text about fonts. " * 40, source="appendix.md", page=9, score=0.004),
    ]
    context = rag.RAGContext(query="billing previews", retrieved=results, context_text="")

    text, included = await rag.build_compressed_rag_context("p", context, "billing previews", 120, "moderate")

    assert included, "at least the most relevant chunk must be kept"
    assert included[0].source == "interviews/p1.md"
    assert "[Source: interviews/p1.md, page 2" in text
    assert "untrusted" in text.lower()
    # every cited source is present in the prompt text, and nothing else is cited
    for result in included:
        assert f"[Source: {result.source}" in text
    assert len(included) <= len(results)
