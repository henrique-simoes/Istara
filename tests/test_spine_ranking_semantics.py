"""Ranking semantics: every score a reader sees means what it says, on one scale.

F12 (2026-09-25 map): Reciprocal Rank Fusion is ordinal (Cormack, Clarke & Büttcher, SIGIR
2009). The fused value ranks results and is not a relevance probability. The best possible chunk
fuses to about 0.016, yet the model read ``relevance: 0.02`` and the chat tool printed
``score: 0.02``. Findings search gave every ILIKE-matched provisional finding ``score = 1.0``
beside RAG hits at about 0.01, so model-written findings always outranked raw source evidence,
and it deduped by ``(text, source)``, collapsing distinct evidence units. RAG compression
discarded the hybrid order for raw query-token overlap. Prompt-RAG sorted cosine and Jaccard
scores together whenever an embedding failed part-way.

F17: unbounded ``top_k`` from the LLM (``search_memory``) and the findings route; whole-table
pandas loads to paginate the Memory view; dead code (``MetaHyperagent._apply_parameter``, a
module-global mutator); ``_select_skill`` concatenating a NULL description; the legacy ReAct loop
executing tools outside the session's advertised catalog on non-streaming and text-fallback turns
(the Pi plane already rejects them with ``tool_not_allowed``).
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.config import settings
from app.core import rag


def _hit(text: str, source: str, rank: int, **kwargs) -> rag.RetrievalResult:
    return rag.RetrievalResult(
        text=text, source=source, page=None, score=0.7 / (60 + rank), **kwargs
    )


# ── F12: the model sees a rank, not the fused value ──────────────────────


async def test_prompt_labels_carry_rank_not_the_fused_value(monkeypatch):
    async def _noop(**kwargs):
        return None

    monkeypatch.setattr(
        "app.core.telemetry.telemetry_recorder.record_research_validity_event", _noop
    )
    hits = [
        _hit("Receipts vanish at the counter.", "/u/p01.md", 1),
        _hit("Glare ruins receipt scans.", "/u/p02.md", 2),
    ]
    text, _ = await rag.build_compressed_rag_context(
        "p1", rag.RAGContext("q", hits, ""), "receipts", 409, "moderate"
    )
    assert "relevance:" not in text
    assert "rank 1" in text and "rank 2" in text
    retrieved = rag.format_context_part(1, hits[0])
    assert "rank 1" in retrieved and "0.01" not in retrieved


async def test_search_memory_tool_bounds_top_k_and_reports_rank(monkeypatch):
    from app.skills.system_actions import _exec_search_memory

    captured: dict = {}

    async def _retrieve(project_id, query, top_k=None, **kwargs):
        captured["top_k"] = top_k
        return rag.RAGContext(query, [_hit("Receipts vanish.", "/u/p01.md", 1)], "")

    monkeypatch.setattr("app.core.rag.retrieve_context", _retrieve)
    answer = await _exec_search_memory({"query": "receipts", "top_k": 100_000}, "p1", "a")
    assert 1 <= captured["top_k"] <= 20
    assert "#1" in answer and "score:" not in answer


# ── F12: findings search keeps source evidence on its own scale ──────────


async def test_provisional_findings_never_outrank_source_evidence():
    from app.models.database import async_session, init_db
    from app.models.finding import Nugget
    from app.models.project import Project
    from app.services.finding_search import search_project_findings

    project_id = f"fs-{uuid.uuid4().hex[:8]}"
    await init_db()
    async with async_session() as db:
        db.add(Project(id=project_id, name="Findings search"))
        db.add(
            Nugget(
                id=str(uuid.uuid4()),
                project_id=project_id,
                text="Receipts vanish at the counter (model-written nugget)",
                source="task-output",
            )
        )
        await db.commit()
        same_text = "Receipts vanish at the counter"
        retrieved = [
            _hit(same_text, "/u/p01.md", 1, evidence_unit_id="eu-1", start_offset=0, end_offset=30),
            _hit(
                same_text, "/u/p01.md", 2, evidence_unit_id="eu-2", start_offset=900, end_offset=930
            ),
        ]
        results = await search_project_findings(db, project_id, "receipts vanish", 10, retrieved)

    kinds = [r["kind"] for r in results]
    assert kinds[:2] == ["source_evidence", "source_evidence"], results
    assert {r.get("evidence_unit_id") for r in results[:2]} == {"eu-1", "eu-2"}
    finding = next(r for r in results if r["kind"] == "finding")
    assert finding["review_status"] == "provisional"
    assert finding.get("score") is None, "no fabricated score on a different scale"


async def test_findings_search_route_bounds_top_k(admin_token):
    from httpx import ASGITransport, AsyncClient

    from app.main import app
    from app.models.database import init_db

    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/findings/search/any-project",
            params={"query": "x", "top_k": 100_000},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert response.status_code == 422


# ── F12: compression keeps the hybrid order ──────────────────────────────


def test_rag_compression_keeps_retrieval_order():
    from app.core.prompt_compressor import compress_rag_chunks_indexed

    ranked = [
        "P04: the scanner blurs everything when the lights are on.",  # rank 1, few query words
        "Unrelated paragraph about payroll timing and overdrafts.",
        "Receipt receipt receipt scanning scanning glare glare counter counter.",  # word soup
    ]
    kept, _ = compress_rag_chunks_indexed(ranked, "receipt scanning glare counter", 409, "high")
    assert [index for index, _ in kept] == [0, 1, 2]


# ── F12: Prompt-RAG never sorts two scales together ──────────────────────


async def test_partial_embedding_failure_falls_back_to_one_keyword_scale(monkeypatch):
    from app.core import prompt_rag

    calls = {"n": 0}

    async def _flaky_embed(text):
        calls["n"] += 1
        if calls["n"] <= 2:  # the query and the first section embed identically (cosine 1.0)
            return [1.0, 0.0, 0.0]
        raise RuntimeError("embedding endpoint went away")

    query = "zzqx vvkw no overlap with any persona section"
    keyword_only = await prompt_rag.compose_dynamic_prompt(
        "istara-main", query, max_tokens=2400, use_embeddings=False
    )
    monkeypatch.setattr("app.core.embeddings.embed_text", _flaky_embed)
    mixed = await prompt_rag.compose_dynamic_prompt(
        "istara-main", query, max_tokens=2400, use_embeddings=True
    )
    assert mixed == keyword_only


# ── F17: Memory view pagination without whole-table loads ────────────────


async def test_memory_listing_and_stats_do_not_load_the_whole_table(
    tmp_path, monkeypatch, admin_token
):
    import lancedb.table
    from httpx import ASGITransport, AsyncClient

    from app.core.embeddings import EmbeddedChunk, TextChunk
    from app.main import app
    from app.models.database import async_session, init_db
    from app.models.project import Project

    monkeypatch.setattr(settings, "lance_db_path", str(tmp_path / "lance"))
    monkeypatch.setattr(settings, "data_dir", str(tmp_path / "data"))
    monkeypatch.setattr(settings, "keyword_index_dir", None)
    project_id = f"page-{uuid.uuid4().hex[:8]}"
    chunks = [TextChunk(text=f"chunk {i}", source=f"/u/doc-{i % 2}.md") for i in range(5)]
    await rag.VectorStore(project_id).add_chunks(
        [EmbeddedChunk(chunk=c, vector=[float(i), 1.0, 0.5]) for i, c in enumerate(chunks)]
    )
    await init_db()
    async with async_session() as db:
        db.add(Project(id=project_id, name="Paging"))
        await db.commit()

    def _whole_table(*args, **kwargs):
        raise AssertionError("whole-table load")

    monkeypatch.setattr(lancedb.table.LanceTable, "to_pandas", _whole_table)
    headers = {"Authorization": f"Bearer {admin_token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        page = (
            await client.get(
                f"/api/memory/{project_id}", params={"page": 2, "page_size": 2}, headers=headers
            )
        ).json()
        stats = (await client.get(f"/api/memory/{project_id}/stats", headers=headers)).json()

    assert "error" not in page, page
    assert page["total"] == 5 and len(page["chunks"]) == 2
    assert {s["name"]: s["count"] for s in page["sources"]} == {"/u/doc-0.md": 3, "/u/doc-1.md": 2}
    assert stats["vector_dimensions"] == 3
    assert {s["name"]: s["chunk_count"] for s in stats["sources"]} == {
        "/u/doc-0.md": 3,
        "/u/doc-1.md": 2,
    }


# ── F17: dead code and small defects ─────────────────────────────────────


def test_module_global_parameter_mutator_is_gone():
    from app.core.meta_hyperagent import MetaHyperagent

    assert not hasattr(MetaHyperagent, "_apply_parameter")


async def test_select_skill_accepts_a_null_description(monkeypatch):
    from app.core.agent import AgentOrchestrator
    from app.skills.registry import load_default_skills

    load_default_skills()
    orchestrator = AgentOrchestrator()

    async def _no_semantic(task):
        return None

    monkeypatch.setattr(orchestrator, "_semantic_skill_match", _no_semantic)
    task = SimpleNamespace(
        skill_name="",
        title="Run a usability study",
        description=None,
        project_id="p1",
        agent_id=None,
    )
    skill = await orchestrator._select_skill(task)
    assert skill is not None and skill.name == "usability-testing"


@pytest.mark.parametrize("text_fallback", [False, True])
async def test_legacy_loop_never_executes_a_tool_outside_the_catalog(monkeypatch, text_fallback):
    from app.core.agentic import legacy
    from app.core.agentic.types import TurnParams

    executed: list[str] = []

    async def _executor(name, arguments, project_id, agent_id):
        executed.append(name)
        return {"success": True, "result": "done"}

    turns = iter(
        [
            {
                "text": '```json\n{"tool": "create_task", "params": {"title": "x"}}\n```'
                if text_fallback
                else "",
                "tool_calls": []
                if text_fallback
                else [
                    {"id": "c1", "function": {"name": "create_task", "arguments": '{"title": "x"}'}}
                ],
            },
            {"text": "final answer", "tool_calls": []},
        ]
    )

    class _Provider:
        async def run_provider_turn(self, **kwargs):
            return {
                "status": "success",
                "usage": {},
                "endpoint_id": "e",
                "model": "m",
                "served_model": "m",
                **next(turns),
            }

    await legacy._react_loop(
        {
            "project_id": "p1",
            "agent_id": "a",
            "messages": [],
            "user_text": "hi",
            "tools": [{"type": "function", "function": {"name": "search_memory"}}],
            "tool_names": ["search_memory"],
            "tool_executor": _executor,
            "provider_service": _Provider(),
            "params": TurnParams(text_fallback=text_fallback, max_turns=3),
        }
    )
    assert "create_task" not in executed
