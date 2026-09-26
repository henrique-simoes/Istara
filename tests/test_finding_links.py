"""Findings link to the findings that support them by meaning, never by position (G1, 2026-09-26).

Before: a fact with no nugget ids was linked to the last five nuggets stored, an insight to the last
three facts, a recommendation to the last two insights, whatever they said."""

from __future__ import annotations

from app.core import finding_links

NUGGETS = [
    ("n-receipt", "The receipt is in my apron pocket, then the van, then the laundry."),
    ("n-payroll", "Payroll hits Thursday and client payments land Friday."),
    ("n-fraud", "Ninety percent of fraud alerts are noise; I cleared forty before lunch."),
]


async def test_links_follow_meaning_and_ignore_order(monkeypatch):
    async def semantic(queries, candidates):
        raise RuntimeError("no embedder in this test")

    monkeypatch.setattr(finding_links, "_semantic_scores", semantic)
    ids = await finding_links.supporting_ids(
        ["Receipts end up lost in pockets, vans and laundry before anyone records them."],
        NUGGETS,
        k=5,
    )
    assert ids == ["n-receipt"]


async def test_nothing_close_enough_means_no_link(monkeypatch):
    async def semantic(queries, candidates):
        return {cid: 0.2 for cid, _ in candidates}

    monkeypatch.setattr(finding_links, "_semantic_scores", semantic)
    claim = ["Owners want better tax exports."]
    assert await finding_links.supporting_ids(claim, NUGGETS, k=5) == []


async def test_semantic_scores_rank_and_cap(monkeypatch):
    async def semantic(queries, candidates):
        return {"n-receipt": 0.9, "n-payroll": 0.7, "n-fraud": 0.56}

    monkeypatch.setattr(finding_links, "_semantic_scores", semantic)
    assert await finding_links.supporting_ids(["q"], NUGGETS, k=2) == ["n-receipt", "n-payroll"]


def test_storage_no_longer_links_by_recency():
    import inspect

    from app.core import agent_research

    source = inspect.getsource(agent_research)
    for stale in ("created_nugget_ids[-5:]", "created_fact_ids[-3:]", "created_insight_ids[-2:]"):
        assert stale not in source
    assert "supporting_ids(" in source


async def test_candidates_are_embedded_once_in_one_batch(monkeypatch):
    from app.core import embeddings

    batches = []

    async def embed_chunks(chunks, **kwargs):
        batches.append([c.text for c in chunks])
        return [type("E", (), {"vector": [1.0, float(len(c.text))]})() for c in chunks]

    async def embed_text(text, role="query"):
        return [1.0, 60.0]

    monkeypatch.setattr(embeddings, "embed_chunks", embed_chunks)
    monkeypatch.setattr(embeddings, "embed_text", embed_text)
    finding_links._DOC_VECTORS.clear()
    for claim in ("first claim", "second claim", "third claim"):
        await finding_links.supporting_ids([claim], NUGGETS, k=1)
    assert len(batches) == 1 and len(batches[0]) == 3
