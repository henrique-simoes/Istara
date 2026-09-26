"""Link a finding to the findings that support it by meaning, never by position (G1, 2026-09-26).

A skill's facts rarely name the nuggets behind them, and insights and recommendations name their
support as text. Storage used to fill the gap with the most recent rows (the last five nuggets, the
last three facts, the last two insights), which wrote provenance that had nothing to do with the
claim. Links now go to the candidates from the same run whose text is closest in meaning to the
claim (or to the support texts the skill named), above a floor; with nothing close enough there is
no link, and the chain shows the gap.
"""

from __future__ import annotations

import math
import re
from collections.abc import Sequence

MIN_COSINE = 0.55
MIN_OVERLAP = 0.3
_WORD = re.compile(r"[a-z0-9']{4,}")


def _words(text: str) -> set[str]:
    """Content words, with a plural "s" dropped so "receipts" meets "receipt"."""
    return {
        w[:-1] if w.endswith("s") and len(w) > 4 else w
        for w in _WORD.findall(str(text or "").lower())
    }


def lexical_score(query: str, candidate: str) -> float:
    """Share of the query's content words that the candidate contains."""
    words = _words(query)
    return len(words & _words(candidate)) / len(words) if words else 0.0


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


# text -> document vector for this process: a run links many claims to the same candidates, and
# embedding every candidate once per claim made a grouped skill run six times slower (G1).
_DOC_VECTORS: dict[str, list[float]] = {}
_DOC_VECTORS_MAX = 20000


async def _document_vectors(texts: list[str]) -> list[list[float]]:
    from app.core.embeddings import TextChunk, embed_chunks

    missing = [t for t in dict.fromkeys(texts) if t not in _DOC_VECTORS]
    if missing:
        if len(_DOC_VECTORS) + len(missing) > _DOC_VECTORS_MAX:
            _DOC_VECTORS.clear()
        embedded = await embed_chunks([TextChunk(text=t, source="finding") for t in missing])
        for text, item in zip(missing, embedded, strict=True):
            _DOC_VECTORS[text] = item.vector
    return [_DOC_VECTORS[t] for t in texts]


async def _semantic_scores(
    queries: list[str], candidates: list[tuple[str, str]]
) -> dict[str, float]:
    from app.core.embeddings import embed_text

    docs = await _document_vectors([text for _, text in candidates])
    best: dict[str, float] = {}
    for query in queries:
        vector = await embed_text(query, role="query")
        for (cid, _), doc in zip(candidates, docs, strict=True):
            best[cid] = max(best.get(cid, 0.0), _cosine(vector, doc))
    return best


def _lexical_scores(queries: list[str], candidates: list[tuple[str, str]]) -> dict[str, float]:
    return {cid: max(lexical_score(q, text) for q in queries) for cid, text in candidates}


async def supporting_ids(
    queries: Sequence[str], candidates: Sequence[tuple[str, str]], *, k: int
) -> list[str]:
    """Ids of up to ``k`` candidates (``(id, text)``) closest in meaning to any query."""
    queries = [q for q in queries if str(q or "").strip()]
    candidates = [(cid, text) for cid, text in candidates if str(text or "").strip()]
    if not queries or not candidates:
        return []
    try:
        scores, floor = await _semantic_scores(queries, candidates), MIN_COSINE
    except Exception:
        scores, floor = _lexical_scores(queries, candidates), MIN_OVERLAP
    ranked = sorted((s, cid) for cid, s in scores.items() if s >= floor)
    return [cid for _, cid in reversed(ranked)][:k]


async def _indexes(queries: Sequence[str], texts: Sequence[str], k: int) -> list[int]:
    candidates = [(str(i), t) for i, t in enumerate(texts)]
    return [int(i) for i in await supporting_ids(queries, candidates, k=k)]


async def plan_links(output) -> dict[str, list[list[int]]]:
    """Which earlier findings each fact, insight and recommendation rests on, by index.

    Computed from the skill's output before storage opens a write transaction: embedding writes its
    own usage rows, and doing it while the findings transaction held SQLite's write lock made every
    embed wait for the lock (a grouped skill run went from 99 s to 560 s).
    """
    nuggets = [str(n.get("text", "")) for n in output.nuggets or []]
    facts = [str(f.get("text", "")) for f in output.facts or []]
    insights = [str(i.get("text", "")) for i in output.insights or []]
    return {
        "facts": [await _indexes([t], nuggets, 5) for t in facts],
        "insights": [
            await _indexes(i.get("supporting_facts") or [i.get("text", "")], facts, 3)
            for i in output.insights or []
        ],
        "recommendations": [
            await _indexes(r.get("supporting_insights") or [r.get("text", "")], insights, 2)
            for r in output.recommendations or []
        ],
    }
