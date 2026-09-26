"""Graph-assisted retrieval: widen hybrid hits through the evidence graph (G3, DEC-2).

A hybrid hit is a chunk of a source document. The nuggets quoting that chunk belong to facts, and a
fact groups nuggets from other sources about the same thing. Expansion follows that path — hit ->
nuggets it contains -> their facts -> sibling nuggets -> the chunks that contain those nuggets — and
fuses the new chunks with the hits by reciprocal rank. It answers thematic questions ("what do
participants say about X?") whose evidence is spread across sources.

Research Spine: expansion only chooses which raw source chunks reach the prompt. The chunks it adds
are source text found by the product's own keyword index, wrapped by the same untrusted-content
formatter; nuggets and facts steer the choice but are never quoted as evidence. Off unless
``settings.rag_graph_expansion`` is on (DEC-2 decides the default).
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from typing import Any

_WS = re.compile(r"\s+")
MIN_NUGGET_CHARS = 20


def _norm(text: str) -> str:
    return _WS.sub(" ", str(text or "")).strip().casefold()


def _ids(raw: object) -> list[str]:
    try:
        values = json.loads(raw) if isinstance(raw, str) and raw.strip() else raw
    except (json.JSONDecodeError, TypeError):
        values = [raw]
    return [str(v) for v in values or [] if v] if isinstance(values, (list, tuple)) else []


def sibling_nugget_texts(
    hit_texts: Sequence[str], nuggets: dict[str, str], facts: Sequence[list[str]]
) -> list[str]:
    """Nuggets sharing a fact with a nugget quoted in a hit: texts, in hit order, deduplicated."""
    in_hits = [_norm(t) for t in hit_texts]
    quoted = [
        nid
        for chunk in in_hits
        for nid, text in nuggets.items()
        if len(text) >= MIN_NUGGET_CHARS and _norm(text) in chunk
    ]
    seen, out = set(quoted), []
    for nid in dict.fromkeys(quoted):
        for members in facts:
            if nid not in members:
                continue
            for sibling in members:
                if sibling not in seen and sibling in nuggets:
                    seen.add(sibling)
                    out.append(nuggets[sibling])
    return out


def rrf_fuse(primary: Sequence[Any], secondary: Sequence[Any], k: int, top_k: int) -> list[Any]:
    """Reciprocal-rank fusion of two ranked lists of results, keyed by chunk text."""
    scores: dict[str, float] = {}
    first: dict[str, Any] = {}
    for ranked in (primary, secondary):
        for rank, result in enumerate(ranked, 1):
            key = _norm(result.text)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
            first.setdefault(key, result)
    order = sorted(scores, key=lambda key: -scores[key])
    return [first[key] for key in order[:top_k]]


async def _graph_rows(project_id: str) -> tuple[dict[str, str], list[list[str]]]:
    from sqlalchemy import select

    from app.models.database import async_session
    from app.models.finding import Fact, Nugget

    async with async_session() as db:
        nuggets = (
            await db.execute(select(Nugget.id, Nugget.text).where(Nugget.project_id == project_id))
        ).all()
        facts = (
            await db.execute(select(Fact.nugget_ids).where(Fact.project_id == project_id))
        ).all()
    return {n.id: n.text or "" for n in nuggets}, [_ids(f.nugget_ids) for f in facts]


async def _chunk_containing(project_id: str, text: str, search) -> Any | None:
    for result in await search(project_id, text, top_k=3):
        if _norm(text) in _norm(result.text):
            return result
    return None


async def expand_results(
    project_id: str, results: list[Any], *, top_k: int, rrf_k: int, search
) -> list[Any]:
    """Hybrid ``results`` fused with the chunks reached through the evidence graph."""
    if not results:
        return results
    nuggets, facts = await _graph_rows(project_id)
    siblings = sibling_nugget_texts([r.text for r in results], nuggets, facts)
    added = []
    for text in siblings[: top_k * 2]:
        chunk = await _chunk_containing(project_id, text, search)
        if chunk is not None:
            chunk.retrieval_mode = "graph"
            added.append(chunk)
    return rrf_fuse(results, added, rrf_k, top_k) if added else results
