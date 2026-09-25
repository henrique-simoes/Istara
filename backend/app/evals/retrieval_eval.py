"""Retrieval evaluation harness (measurements 1-3): span-graded qrels over a sandbox index.

Istara had no relevance judgments anywhere: every retrieval check asserted presence, and the
autoresearch "precision@k" rose with the fusion weights it tuned (F3). This module is the
reusable measurement:

* **Qrels.** ``tests/evals/retrieval/harbor-ledger-qrels.json`` holds researcher questions over
  the synthetic Harbor Ledger corpus. Judgments are SPAN-based: each question names exact
  answer-bearing strings (grade 2), and topically related strings (grade 1: the rest of the
  question's theme bank, or listed related spans). A chunk's grade is the highest grade of any
  span occurrence it carries at least half of. Because judgments attach to source spans, not to
  chunk ids, they stay valid when the corpus is re-chunked (measurement 2).
* **Sandbox index.** Every configuration is indexed from the corpus files through Istara's own
  ``process_file`` chunkers, BM25 index and vector store, rooted in a scratch directory. No
  project index is touched and no process-wide setting is mutated.
* **Systems.** ``bm25`` (FTS5), ``vector`` (cosine, no threshold), ``hybrid`` (production
  ``rag.hybrid_search`` with explicit weights and RRF k).
* **Metrics.** nDCG@k with graded gains 2^g - 1 (Järvelin & Kekäläinen 2002), Recall@k over
  answer-bearing span occurrences, MRR@k to the first answer-bearing chunk, Success@k. Means come
  with percentile bootstrap 95% intervals (Efron & Tibshirani 1993). Systems and settings are
  compared with a two-sided paired randomization test over questions (Smucker, Allan & Carterette,
  CIKM 2007).
* **Pooling.** The top-k of every system per question is pooled TREC-style (Voorhees & Harman
  2005). The pool is what an assessor or judge panel labels, and the report states how many of
  the index's answer-bearing chunks the pool caught (pool recall).

Run: ``python -m app.evals.retrieval_eval --help`` (from ``backend/``).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import random
import shutil
import tempfile
import time
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_QRELS = REPO_ROOT / "tests" / "evals" / "retrieval" / "harbor-ledger-qrels.json"
EVAL_PROJECT = "retrieval-eval"
SYSTEMS = ("bm25", "vector", "hybrid")
_SPAN_MIN_SHARE = 0.5


class BenchmarkUnavailableError(RuntimeError):
    """The qrels or corpus cannot be found or no longer matches: fail closed, never guess."""


# ── configuration ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RetrievalConfig:
    chunk_size: int = 1200
    chunk_overlap: int = 180
    vector_weight: float = 0.7
    keyword_weight: float = 0.3
    rrf_k: int = 60
    top_k: int = 10

    @classmethod
    def from_settings(cls, **overrides: Any) -> RetrievalConfig:
        from app.config import settings

        base = cls(
            chunk_size=int(settings.rag_chunk_size),
            chunk_overlap=int(settings.rag_chunk_overlap),
            vector_weight=float(settings.rag_hybrid_vector_weight),
            keyword_weight=float(settings.rag_hybrid_keyword_weight),
            rrf_k=int(getattr(settings, "rag_rrf_k", 60)),
        )
        return replace(base, **overrides)

    @property
    def chunking(self) -> tuple[int, int]:
        return (self.chunk_size, self.chunk_overlap)


# ── qrels ──────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Question:
    id: str
    style: str
    theme: str | None
    text: str
    targets: tuple[str, ...]
    related: tuple[str, ...]


@dataclass(frozen=True)
class SpanOccurrence:
    path: str
    start: int
    end: int
    grade: int


@dataclass
class Qrels:
    name: str
    corpus_dir: Path
    files: dict[str, str]
    questions: list[Question]
    occurrences: dict[str, list[SpanOccurrence]] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path | str = DEFAULT_QRELS, corpus_dir: Path | str | None = None) -> Qrels:
        path = Path(path)
        if not path.exists():
            raise BenchmarkUnavailableError(f"qrels not found: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        corpus = Path(corpus_dir) if corpus_dir else REPO_ROOT / data["corpus"]
        if not corpus.exists():
            raise BenchmarkUnavailableError(f"benchmark corpus not found: {corpus}")
        files = {
            str(p.relative_to(corpus)): p.read_text(encoding="utf-8")
            for p in sorted(corpus.glob(data.get("corpus_glob", "**/*")))
            if p.is_file()
        }
        banks: dict[str, list[str]] = data.get("theme_banks", {})
        questions = [
            Question(
                id=q["id"],
                style=q["style"],
                theme=q.get("theme"),
                text=q["text"],
                targets=tuple(q["targets"]),
                related=tuple(
                    [
                        s
                        for s in banks.get(q.get("related_theme") or "", [])
                        if s not in q["targets"]
                    ]
                    + list(q.get("related", []))
                ),
            )
            for q in data["questions"]
        ]
        qrels = cls(name=data["name"], corpus_dir=corpus, files=files, questions=questions)
        qrels._index_occurrences()
        return qrels

    def _index_occurrences(self) -> None:
        missing = []
        for question in self.questions:
            found: list[SpanOccurrence] = []
            for grade, spans in ((2, question.targets), (1, question.related)):
                for span in spans:
                    hits = list(self._find_all(span))
                    if grade == 2 and not hits:
                        missing.append((question.id, span[:60]))
                    found.extend(SpanOccurrence(p, s, s + len(span), grade) for p, s in hits)
            self.occurrences[question.id] = found
        if missing:
            raise BenchmarkUnavailableError(f"qrels targets missing from the corpus: {missing[:5]}")

    def _find_all(self, span: str) -> Iterable[tuple[str, int]]:
        for path, text in self.files.items():
            start = text.find(span)
            while start >= 0:
                yield path, start
                start = text.find(span, start + 1)

    def answer_occurrences(self, question: Question) -> list[SpanOccurrence]:
        return [o for o in self.occurrences[question.id] if o.grade == 2]


def span_grade(qrels: Qrels, question: Question, path: str, start: int, end: int) -> int:
    """Grade of the text ``[start, end)`` of corpus file ``path`` for ``question`` (0, 1 or 2).

    The highest grade of any judged span occurrence of which the text carries at least half.
    """
    best = 0
    if start < 0:
        return best
    for occurrence in qrels.occurrences[question.id]:
        if occurrence.path != path or occurrence.grade <= best:
            continue
        overlap = min(end, occurrence.end) - max(start, occurrence.start)
        if overlap >= _SPAN_MIN_SHARE * (occurrence.end - occurrence.start):
            best = occurrence.grade
    return best


# ── sandbox index ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class IndexedChunk:
    path: str
    start: int
    end: int
    text: str

    @property
    def key(self) -> tuple[str, int, int]:
        return (self.path, self.start, self.end)


class SandboxIndex:
    """One corpus, one chunking configuration, indexed in a scratch directory."""

    def __init__(self, qrels: Qrels, config: RetrievalConfig, root: Path, *, embed: bool) -> None:
        self.qrels = qrels
        self.config = config
        self.root = Path(root)
        self.embed = embed
        self.chunks: list[IndexedChunk] = []
        self._by_key: dict[tuple[str, int, int], IndexedChunk] = {}
        self._grade_cache: dict[tuple[str, tuple[str, int, int]], int] = {}

    @property
    def store(self):
        from app.core.rag import VectorStore

        return VectorStore(EVAL_PROJECT, root=self.root)

    async def build(self) -> SandboxIndex:
        from app.core.file_processor import process_file

        records = []
        for rel, text in self.qrels.files.items():
            processed = process_file(
                self.qrels.corpus_dir / rel,
                chunk_size=self.config.chunk_size,
                chunk_overlap=self.config.chunk_overlap,
            )
            if processed.error:
                continue
            cursor = 0
            for chunk in processed.chunks:
                position = text.find(chunk.text, cursor)
                if position < 0:
                    position = text.find(chunk.text)
                start, end = (position, position + len(chunk.text)) if position >= 0 else (-1, -1)
                if position >= 0:
                    cursor = position + 1
                chunk.source = rel
                chunk.metadata = {
                    **(chunk.metadata or {}),
                    "start_offset": start,
                    "end_offset": end,
                }
                records.append(chunk)
                indexed = IndexedChunk(rel, start, end, chunk.text)
                self.chunks.append(indexed)
                self._by_key[indexed.key] = indexed
        await self.store.keyword_index().add_chunks(records)
        if self.embed:
            from app.core.rag import embed_chunks

            embedded = await embed_chunks(records)
            await self.store.add_chunks(embedded)
        return self

    def grade(self, question: Question, chunk: IndexedChunk) -> int:
        cache_key = (question.id, chunk.key)
        if cache_key not in self._grade_cache:
            self._grade_cache[cache_key] = span_grade(
                self.qrels, question, chunk.path, chunk.start, chunk.end
            )
        return self._grade_cache[cache_key]

    def ideal_grades(self, question: Question) -> list[int]:
        return sorted((self.grade(question, c) for c in self.chunks), reverse=True)

    def _resolve(self, source: str, start: int | None, end: int | None, text: str):
        if start is not None and end is not None:
            hit = self._by_key.get((source, int(start), int(end)))
            if hit:
                return hit
        for chunk in self.chunks:  # rows without offsets: fall back to exact text
            if chunk.path == source and chunk.text == text:
                return chunk
        return None

    async def search(self, system: str, query: str, k: int) -> list[IndexedChunk]:
        from app.core import rag

        if system == "bm25":
            rows = await self.store.keyword_index().search(query, top_k=k)
            hits = [self._resolve(r.source, r.start_offset, r.end_offset, r.text) for r in rows]
        elif system in ("vector", "hybrid"):
            if not self.embed:
                raise BenchmarkUnavailableError(f"{system} needs an embedder (run with embed=True)")
            # Embeddings go through ``embed_text``/``embed_chunks`` like every other consumer,
            # so they inherit the W8 embeddings dispatch instead of calling the dispatcher here.
            query_vector = await rag.embed_text(query)
            if system == "vector":
                rows = await self.store.search(query_vector, top_k=k, score_threshold=0.0)
            else:
                rows = await rag.hybrid_search(
                    EVAL_PROJECT,
                    query,
                    query_vector,
                    top_k=k,
                    store=self.store,
                    vector_weight=self.config.vector_weight,
                    keyword_weight=self.config.keyword_weight,
                    rrf_k=self.config.rrf_k,
                )
            hits = [self._resolve(r.source, r.start_offset, r.end_offset, r.text) for r in rows]
        else:
            raise ValueError(f"unknown system {system}")
        seen: set[tuple[str, int, int]] = set()
        ranked = []
        for hit in hits:
            if hit is not None and hit.key not in seen:
                seen.add(hit.key)
                ranked.append(hit)
        return ranked[:k]


# ── metrics ────────────────────────────────────────────────────────────────


def dcg(grades: Sequence[int], k: int) -> float:
    return sum((2**g - 1) / math.log2(i + 2) for i, g in enumerate(grades[:k]))


def ndcg(grades: Sequence[int], ideal: Sequence[int], k: int) -> float:
    best = dcg(ideal, k)
    return dcg(grades, k) / best if best > 0 else 0.0


def question_metrics(
    index: SandboxIndex, question: Question, ranked: Sequence[IndexedChunk], k: int
) -> dict[str, float]:
    grades = [index.grade(question, c) for c in ranked[:k]]
    answers = index.qrels.answer_occurrences(question)
    covered = 0
    for occurrence in answers:
        for chunk in ranked[:k]:
            if chunk.path == occurrence.path:
                overlap = min(chunk.end, occurrence.end) - max(chunk.start, occurrence.start)
                if overlap >= _SPAN_MIN_SHARE * (occurrence.end - occurrence.start):
                    covered += 1
                    break
    first = next((i for i, g in enumerate(grades) if g == 2), None)
    return {
        f"ndcg@{k}": ndcg(grades, index.ideal_grades(question), k),
        f"recall@{k}": covered / len(answers) if answers else 0.0,
        f"mrr@{k}": 1.0 / (first + 1) if first is not None else 0.0,
        f"success@{k}": 1.0 if first is not None else 0.0,
    }


def bootstrap_ci(
    values: Sequence[float], *, resamples: int = 10_000, seed: int = 20260925, alpha: float = 0.05
) -> tuple[float, float]:
    if not values:
        return (0.0, 0.0)
    rng = random.Random(seed)
    n = len(values)
    means = sorted(sum(rng.choice(values) for _ in range(n)) / n for _ in range(resamples))
    low = means[int((alpha / 2) * resamples)]
    high = means[min(resamples - 1, int((1 - alpha / 2) * resamples))]
    return (low, high)


def paired_randomization_test(
    a: Sequence[float], b: Sequence[float], *, permutations: int = 20_000, seed: int = 20260925
) -> float:
    """Two-sided p-value for mean(a - b) != 0, by random sign flips of per-question differences."""
    diffs = [x - y for x, y in zip(a, b, strict=True)]
    if not diffs:
        return 1.0
    observed = abs(sum(diffs) / len(diffs))
    rng = random.Random(seed)
    extreme = 0
    for _ in range(permutations):
        flipped = sum(d if rng.random() < 0.5 else -d for d in diffs) / len(diffs)
        if abs(flipped) >= observed - 1e-12:
            extreme += 1
    return (extreme + 1) / (permutations + 1)


def holm_adjust(p_values: dict[str, float]) -> dict[str, float]:
    """Holm-Bonferroni step-down adjustment for a family of comparisons."""
    ordered = sorted(p_values.items(), key=lambda kv: kv[1])
    m = len(ordered)
    adjusted: dict[str, float] = {}
    running = 0.0
    for i, (name, p) in enumerate(ordered):
        running = max(running, min(1.0, (m - i) * p))
        adjusted[name] = running
    return adjusted


def summarize(per_question: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    metrics = next(iter(per_question.values())).keys() if per_question else []
    out: dict[str, dict[str, float]] = {}
    for metric in metrics:
        values = [row[metric] for row in per_question.values()]
        low, high = bootstrap_ci(values)
        out[metric] = {
            "mean": round(sum(values) / len(values), 4),
            "ci95_low": round(low, 4),
            "ci95_high": round(high, 4),
        }
    return out


# ── evaluation ─────────────────────────────────────────────────────────────


@dataclass
class SystemRun:
    system: str
    per_question: dict[str, dict[str, float]]
    ranked: dict[str, list[IndexedChunk]]


async def run_system(index: SandboxIndex, system: str, questions: Sequence[Question]) -> SystemRun:
    k = index.config.top_k
    per_question: dict[str, dict[str, float]] = {}
    ranked: dict[str, list[IndexedChunk]] = {}
    for question in questions:
        hits = await index.search(system, question.text, k)
        ranked[question.id] = hits
        per_question[question.id] = question_metrics(index, question, hits, k)
    return SystemRun(system, per_question, ranked)


def pool_report(index: SandboxIndex, runs: Sequence[SystemRun]) -> dict[str, Any]:
    """TREC-style pool: union of every system's top-k per question, and how complete it is."""
    sizes, recalls = [], []
    for question in index.qrels.questions:
        pool = {c.key for run in runs for c in run.ranked.get(question.id, [])}
        answer_chunks = {c.key for c in index.chunks if index.grade(question, c) == 2}
        sizes.append(len(pool))
        if answer_chunks:
            recalls.append(len(pool & answer_chunks) / len(answer_chunks))
    return {
        "depth": index.config.top_k,
        "systems": [r.system for r in runs],
        "mean_pool_size": round(sum(sizes) / max(1, len(sizes)), 2),
        "mean_pool_recall_of_answer_chunks": round(sum(recalls) / max(1, len(recalls)), 4),
    }


def compare(a: SystemRun, b: SystemRun, metric: str) -> dict[str, float]:
    ids = sorted(set(a.per_question) & set(b.per_question))
    xs = [a.per_question[i][metric] for i in ids]
    ys = [b.per_question[i][metric] for i in ids]
    diffs = [x - y for x, y in zip(xs, ys, strict=True)]
    low, high = bootstrap_ci(diffs)
    return {
        "mean_difference": round(sum(diffs) / max(1, len(diffs)), 4),
        "ci95_low": round(low, 4),
        "ci95_high": round(high, 4),
        "p_value": round(paired_randomization_test(xs, ys), 5),
        "n": len(ids),
    }


async def evaluate(
    qrels: Qrels,
    config: RetrievalConfig,
    *,
    systems: Sequence[str] = SYSTEMS,
    embed: bool = True,
    root: Path | None = None,
) -> dict[str, Any]:
    """Measurement 1: one configuration, every system, with CIs, per-style breakdown and pool."""
    own_root = root is None
    root = Path(root or tempfile.mkdtemp(prefix="istara-retrieval-eval-"))
    started = time.monotonic()
    try:
        index = await SandboxIndex(qrels, config, root, embed=embed).build()
        runs = [await run_system(index, system, qrels.questions) for system in systems]
        styles = sorted({q.style for q in qrels.questions})
        report: dict[str, Any] = {
            "benchmark": qrels.name,
            "questions": len(qrels.questions),
            "styles": {s: sum(1 for q in qrels.questions if q.style == s) for s in styles},
            "config": asdict(config),
            "chunks": len(index.chunks),
            "embed": embed,
            "systems": {},
        }
        for run in runs:
            report["systems"][run.system] = {
                "overall": summarize(run.per_question),
                "by_style": {
                    style: summarize(
                        {
                            qid: m
                            for qid, m in run.per_question.items()
                            if next(q for q in qrels.questions if q.id == qid).style == style
                        }
                    )
                    for style in styles
                },
                "per_question": run.per_question,
            }
        metric = f"ndcg@{config.top_k}"
        report["comparisons"] = {
            f"{a.system}_vs_{b.system}": compare(a, b, metric)
            for i, a in enumerate(runs)
            for b in runs[i + 1 :]
        }
        report["pool"] = pool_report(index, runs)
        report["seconds"] = round(time.monotonic() - started, 1)
        return report
    finally:
        if own_root:
            shutil.rmtree(root, ignore_errors=True)


class RetrievalObjective:
    """F3's objective: mean nDCG@k of the production hybrid on the qrels, per candidate config.

    One sandbox per chunking configuration, cached for the objective's lifetime and deleted on
    ``close``. Weights and RRF k change without re-indexing; chunk size and overlap re-index.
    """

    def __init__(self, qrels: Qrels, *, system: str = "hybrid", embed: bool = True) -> None:
        self.qrels = qrels
        self.system = system
        self.embed = embed
        self._root = Path(tempfile.mkdtemp(prefix="istara-rag-objective-"))
        self._indices: dict[tuple[int, int], SandboxIndex] = {}

    async def index_for(self, config: RetrievalConfig) -> SandboxIndex:
        cached = self._indices.get(config.chunking)
        if cached is None:
            root = self._root / f"c{config.chunk_size}-o{config.chunk_overlap}"
            cached = await SandboxIndex(self.qrels, config, root, embed=self.embed).build()
            self._indices[config.chunking] = cached
        cached.config = config  # same chunks; weights/RRF k from the candidate
        return cached

    async def per_question(self, config: RetrievalConfig) -> dict[str, dict[str, float]]:
        index = await self.index_for(config)
        return (await run_system(index, self.system, self.qrels.questions)).per_question

    async def score(self, config: RetrievalConfig) -> float:
        rows = await self.per_question(config)
        metric = f"ndcg@{config.top_k}"
        return sum(r[metric] for r in rows.values()) / max(1, len(rows))

    def close(self) -> None:
        shutil.rmtree(self._root, ignore_errors=True)


# ── measurement 2: one-factor-at-a-time ablations with paired tests ──────


DEFAULT_ABLATIONS: dict[str, list[Any]] = {
    "chunk_size": [400, 800, 1600, 2400],
    "chunk_overlap": [0, 400],
    "vector_weight": [0.3, 0.5, 0.9],
    "rrf_k": [10, 30, 100],
}


async def ablate(
    qrels: Qrels,
    base: RetrievalConfig,
    *,
    factors: dict[str, list[Any]] | None = None,
    system: str = "hybrid",
    embed: bool = True,
) -> dict[str, Any]:
    """Vary one factor at a time around ``base``, re-indexing whenever chunking changes.

    Every variant is compared with the baseline on per-question nDCG@k by a paired
    randomization test; p-values are Holm-adjusted across the family.
    """
    objective = RetrievalObjective(qrels, system=system, embed=embed)
    metric = f"ndcg@{base.top_k}"
    try:
        baseline_rows = await objective.per_question(base)
        variants: dict[str, dict[str, Any]] = {}
        raw_p: dict[str, float] = {}
        for factor, values in (factors or DEFAULT_ABLATIONS).items():
            for value in values:
                overrides: dict[str, Any] = {factor: value}
                if factor == "vector_weight":
                    overrides["keyword_weight"] = round(1.0 - value, 4)
                candidate = replace(base, **overrides)
                rows = await objective.per_question(candidate)
                ids = sorted(baseline_rows)
                xs = [rows[i][metric] for i in ids]
                ys = [baseline_rows[i][metric] for i in ids]
                name = f"{factor}={value}"
                diffs = [x - y for x, y in zip(xs, ys, strict=True)]
                low, high = bootstrap_ci(diffs)
                raw_p[name] = paired_randomization_test(xs, ys)
                variants[name] = {
                    "config": asdict(candidate),
                    "summary": summarize(rows),
                    "delta_vs_baseline": {
                        "mean": round(sum(diffs) / len(diffs), 4),
                        "ci95_low": round(low, 4),
                        "ci95_high": round(high, 4),
                    },
                    "chunks": len((await objective.index_for(candidate)).chunks),
                }
        adjusted = holm_adjust(raw_p)
        for name, row in variants.items():
            row["p_value"] = round(raw_p[name], 5)
            row["p_holm"] = round(adjusted[name], 5)
        return {
            "benchmark": qrels.name,
            "system": system,
            "metric": metric,
            "baseline": {"config": asdict(base), "summary": summarize(baseline_rows)},
            "variants": variants,
        }
    finally:
        objective.close()


# ── measurement 3: budget recall ──────────────────────────────────────────


async def budget_recall(
    qrels: Qrels,
    base: RetrievalConfig,
    *,
    windows: Sequence[int] = (2048, 4096, 8192, 16384, 32768, 131072),
    retrieve_k: int = 5,
    surplus_level: str = "moderate",
    embed: bool = True,
) -> dict[str, Any]:
    """Of the answer-bearing spans hybrid retrieval puts in the chat top-k, how many survive the
    RAG token budget and compression into the prompt, per context window?

    The RAG budget is ``BudgetCoordinator.allocate(window).rag_tokens`` (5% of the window, at most
    4,000 tokens), and the prompt text is ``rag.build_compressed_rag_context``, the chat path.
    A span survives when at least half of it is present verbatim in the prompt block.
    """
    from app.core.budget_coordinator import BudgetCoordinator
    from app.core.rag import RAGContext, RetrievalResult, build_compressed_rag_context

    system = "hybrid" if embed else "bm25"
    objective = RetrievalObjective(qrels, system=system, embed=embed)
    try:
        index = await objective.index_for(replace(base, top_k=retrieve_k))
        rows: list[dict[str, Any]] = []
        for window in windows:
            rag_tokens = BudgetCoordinator().allocate(window).rag_tokens
            retrieved_spans = kept_spans = 0
            for question in qrels.questions:
                hits = await index.search(system, question.text, retrieve_k)
                spans = [
                    (h, o)
                    for h in hits
                    for o in qrels.answer_occurrences(question)
                    if o.path == h.path
                    and min(h.end, o.end) - max(h.start, o.start)
                    >= _SPAN_MIN_SHARE * (o.end - o.start)
                ]
                if not spans:
                    continue
                results = [
                    RetrievalResult(text=h.text, source=h.path, page=None, score=1.0 / (60 + i))
                    for i, h in enumerate(hits, 1)
                ]
                text, _ = await build_compressed_rag_context(
                    EVAL_PROJECT,
                    RAGContext(question.text, results, ""),
                    question.text,
                    rag_tokens,
                    surplus_level,
                )
                for _hit, occurrence in spans:
                    retrieved_spans += 1
                    span_text = qrels.files[occurrence.path][occurrence.start : occurrence.end]
                    if _survives(span_text, text):
                        kept_spans += 1
            rows.append(
                {
                    "window_tokens": window,
                    "rag_budget_tokens": rag_tokens,
                    "answer_spans_retrieved": retrieved_spans,
                    "answer_spans_in_prompt": kept_spans,
                    "budget_recall": round(kept_spans / retrieved_spans, 4)
                    if retrieved_spans
                    else None,
                }
            )
        return {
            "benchmark": qrels.name,
            "system": system,
            "retrieve_k": retrieve_k,
            "surplus_level": surplus_level,
            "windows": rows,
        }
    finally:
        objective.close()


def _survives(span: str, prompt: str) -> bool:
    if span in prompt:
        return True
    # Compression may drop words; count the longest contiguous run of the span's words kept.
    words = span.split()
    best = run = 0
    for word in words:
        run = run + 1 if word in prompt else 0
        best = max(best, run)
    return best >= _SPAN_MIN_SHARE * len(words)


# ── CLI ────────────────────────────────────────────────────────────────────


async def _main(args: argparse.Namespace) -> dict[str, Any]:
    qrels = Qrels.load(args.qrels, args.corpus)
    base = RetrievalConfig.from_settings(top_k=args.k)
    if args.mode == "evaluate":
        systems = [s for s in args.systems.split(",") if s]
        return await evaluate(qrels, base, systems=systems, embed=not args.no_embed)
    if args.mode == "ablate":
        return await ablate(
            qrels, base, embed=not args.no_embed, system="hybrid" if not args.no_embed else "bm25"
        )
    return await budget_recall(qrels, base, embed=not args.no_embed)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("mode", choices=["evaluate", "ablate", "budget"])
    parser.add_argument("--qrels", default=str(DEFAULT_QRELS))
    parser.add_argument("--corpus", default=None)
    parser.add_argument("--systems", default=",".join(SYSTEMS))
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument(
        "--no-embed", action="store_true", help="BM25 only (no embedder available, e.g. CI)"
    )
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    report = asyncio.run(_main(args))
    text = json.dumps(report, indent=1, default=str)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text if not args.out else f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
