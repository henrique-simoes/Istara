"""Retrieval evaluation (measurement 1) and the autoresearch RAG objective built on it (F3).

F3 (2026-09-25 map): the RAG tuning loop scored ``0.6 x mean(fused score) + 0.4 x coverage``.
The fused Reciprocal Rank Fusion score is proportional to the weights it tuned, so raising the
weights raised the score whatever was retrieved (Goodhart's law in one line). It had no relevance
labels, chunk-size mutations never re-indexed, and every mutation was a ``setattr`` on the
process-wide settings. The fix optimises nDCG@10 on span-graded qrels (TREC-style judgments,
Voorhees & Harman 2005), on a sandbox index rebuilt per chunking, with the candidate passed
explicitly.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import uuid

import pytest

from app.config import settings
from app.core import rag
from app.core.embeddings import EmbeddedChunk


def _ev():
    from app.evals import retrieval_eval

    return retrieval_eval


def _stats():
    from app.evals import stats

    return stats


# ── metric maths ─────────────────────────────────────────────────────────


def test_ndcg_matches_hand_computation():
    ev = _stats()
    grades = [2, 0, 1]
    ideal = [2, 2, 1, 0]
    dcg = 3 / math.log2(2) + 0 + 1 / math.log2(4)
    idcg = 3 / math.log2(2) + 3 / math.log2(3) + 1 / math.log2(4)
    assert ev.ndcg(grades, ideal, 3) == pytest.approx(dcg / idcg)
    assert ev.ndcg([0, 0], [0, 0], 2) == 0.0


def test_bootstrap_interval_brackets_the_mean_and_randomization_test_behaves():
    ev = _stats()
    values = [0.1, 0.4, 0.35, 0.8, 0.5, 0.6, 0.2, 0.9]
    low, high = ev.bootstrap_ci(values)
    assert low <= sum(values) / len(values) <= high
    assert ev.paired_randomization_test(values, values) == 1.0
    better = [v + 0.3 for v in values]
    assert ev.paired_randomization_test(better, values) < 0.01
    adjusted = ev.holm_adjust({"a": 0.01, "b": 0.02, "c": 0.5})
    assert adjusted == {"a": 0.03, "b": 0.04, "c": 0.5}


# ── the shipped benchmark ────────────────────────────────────────────────


def test_shipped_qrels_load_and_every_target_occurs_in_the_corpus():
    ev = _ev()
    qrels = ev.Qrels.load()
    assert len(qrels.questions) >= 50
    assert {q.style for q in qrels.questions} >= {"lexical", "paraphrase", "fact"}
    assert all(qrels.answer_occurrences(q) for q in qrels.questions)


async def test_bm25_evaluation_on_the_shipped_benchmark(tmp_path, monkeypatch):
    """CI-safe lane: BM25 only (the QA/CI embedder is a hash stub, so vector scores are noise)."""
    ev = _ev()
    monkeypatch.setattr(settings, "data_dir", str(tmp_path / "data"))
    qrels = ev.Qrels.load()
    report = await ev.evaluate(
        qrels,
        ev.RetrievalConfig.from_settings(),
        systems=["bm25"],
        embed=False,
        root=tmp_path / "sandbox",
    )
    overall = report["systems"]["bm25"]["overall"]
    assert 0.0 < overall["ndcg@10"]["mean"] <= 1.0
    assert overall["ndcg@10"]["ci95_low"] <= overall["ndcg@10"]["mean"]
    lexical = report["systems"]["bm25"]["by_style"]["lexical"]["mrr@10"]["mean"]
    paraphrase = report["systems"]["bm25"]["by_style"]["paraphrase"]["mrr@10"]["mean"]
    assert lexical > paraphrase, "BM25 should find the lexical questions' answers more often"
    assert report["pool"]["mean_pool_size"] > 0


# ── F3: the tuning objective measures relevance, re-indexes, mutates nothing ─


def _embed_vec(text: str) -> list[float]:
    v = [0.0] * 32
    for token in re.findall(r"\w+", text.lower()):
        v[int(hashlib.md5(token.encode()).hexdigest(), 16) % 32] += 1.0
    norm = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / norm for x in v]


@pytest.fixture
def tiny_benchmark(tmp_path, monkeypatch):
    """A three-document corpus and qrels, ingested both as a benchmark and as a project."""
    monkeypatch.setattr(settings, "data_dir", str(tmp_path / "data"))
    monkeypatch.setattr(settings, "keyword_index_dir", None)
    monkeypatch.setattr(settings, "lance_db_path", str(tmp_path / "lance"))

    async def _chunks(chunks, batch_size=32):
        return [EmbeddedChunk(c, _embed_vec(c.text)) for c in chunks]

    async def _text(text):
        return _embed_vec(text)

    monkeypatch.setattr(rag, "embed_chunks", _chunks)
    monkeypatch.setattr(rag, "embed_text", _text)
    monkeypatch.setattr("app.core.embeddings.embed_text", _text)
    corpus = tmp_path / "corpus"
    (corpus / "sources").mkdir(parents=True)
    docs = {
        "sources/a.txt": ("Owners chase late invoices by phone every Friday afternoon. " * 30),
        "sources/b.txt": ("Receipts fade on thermal paper before the quarter closes. " * 30),
        "sources/c.txt": ("Payroll lands Thursday while client payments arrive Friday. " * 30),
    }
    for rel, text in docs.items():
        (corpus / rel).write_text(text, encoding="utf-8")
    qrels = {
        "version": 1,
        "name": "tiny",
        "corpus": str(corpus),
        "corpus_glob": "sources/**/*",
        "theme_banks": {},
        "questions": [
            {
                "id": "q1",
                "style": "lexical",
                "theme": None,
                "text": "invoices phone Friday",
                "targets": ["Owners chase late invoices by phone every Friday afternoon."],
                "related_theme": None,
                "related": [],
            },
            {
                "id": "q2",
                "style": "lexical",
                "theme": None,
                "text": "thermal paper receipts",
                "targets": ["Receipts fade on thermal paper before the quarter closes."],
                "related_theme": None,
                "related": [],
            },
            {
                "id": "q3",
                "style": "paraphrase",
                "theme": None,
                "text": "wages before money arrives",
                "targets": ["Payroll lands Thursday while client payments arrive Friday."],
                "related_theme": None,
                "related": [],
            },
        ],
    }
    qrels_path = tmp_path / "qrels.json"
    qrels_path.write_text(json.dumps(qrels), encoding="utf-8")
    if hasattr(settings, "retrieval_benchmark_qrels"):  # absent before the fix
        monkeypatch.setattr(settings, "retrieval_benchmark_qrels", str(qrels_path))
        monkeypatch.setattr(settings, "retrieval_benchmark_corpus", str(corpus))
    return corpus, docs


async def _runner_for(project_id: str, corpus, docs):
    from app.core.autoresearch_runners.rag_params import RAGParamsRunner
    from app.core.file_processor import chunk_text

    # The project index the OLD objective read (same documents, production chunking).
    for rel, text in docs.items():
        await rag.ingest_chunks(project_id, chunk_text(text, source=rel))
    runner = RAGParamsRunner()
    runner.bind_project(project_id)
    return runner


async def test_scaling_both_weights_cannot_change_the_objective(tiny_benchmark):
    corpus, docs = tiny_benchmark
    project_id = f"f3-{uuid.uuid4().hex[:6]}"
    runner = await _runner_for(project_id, corpus, docs)
    baseline = await runner.measure_baseline(project_id)
    revert = await runner.apply_mutation(
        project_id,
        {"params": {"rag_hybrid_vector_weight": 0.875, "rag_hybrid_keyword_weight": 0.375}},
    )
    scaled = await runner.measure(project_id)
    await revert()
    # RRF ranking is invariant when both weights are multiplied by the same factor (1.25), so an
    # objective about relevance cannot move. The fused-score objective rose with the weights.
    assert scaled == pytest.approx(baseline)
    getattr(runner, "close", lambda: None)()


async def test_candidate_never_touches_process_wide_settings(tiny_benchmark):
    corpus, docs = tiny_benchmark
    project_id = f"f3g-{uuid.uuid4().hex[:6]}"
    runner = await _runner_for(project_id, corpus, docs)
    await runner.measure_baseline(project_id)
    before = settings.rag_hybrid_vector_weight
    revert = await runner.apply_mutation(project_id, {"params": {"rag_hybrid_vector_weight": 0.31}})
    during = settings.rag_hybrid_vector_weight  # what every other project would read now
    await runner.measure(project_id)
    await revert()
    assert during == before
    getattr(runner, "close", lambda: None)()


async def test_a_chunk_size_candidate_is_measured_on_a_reindexed_sandbox(tiny_benchmark):
    corpus, docs = tiny_benchmark
    project_id = f"f3c-{uuid.uuid4().hex[:6]}"
    runner = await _runner_for(project_id, corpus, docs)
    await runner.measure_baseline(project_id)
    revert = await runner.apply_mutation(project_id, {"params": {"rag_chunk_size": 400}})
    await runner.measure(project_id)
    await revert()
    objective = runner.objective
    sizes = {chunking: len(index.chunks) for chunking, index in objective._indices.items()}
    assert len(sizes) == 2, sizes
    assert (
        sizes[(400, settings.rag_chunk_overlap)]
        > sizes[(settings.rag_chunk_size, settings.rag_chunk_overlap)]
    )
    runner.close()


async def test_without_a_benchmark_the_loop_fails_closed(tiny_benchmark, monkeypatch, tmp_path):
    ev = _ev()
    corpus, docs = tiny_benchmark
    project_id = f"f3n-{uuid.uuid4().hex[:6]}"
    runner = await _runner_for(project_id, corpus, docs)
    monkeypatch.setattr(settings, "retrieval_benchmark_qrels", str(tmp_path / "missing.json"))
    with pytest.raises(ev.BenchmarkUnavailableError):
        await runner.measure_baseline(project_id)
