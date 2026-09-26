"""G3 graph-assisted retrieval (DEC-2): expansion follows hit -> nugget -> fact -> sibling nugget ->
chunk, fuses by reciprocal rank, stays off by default, and ships only by the pre-registered rule."""

from __future__ import annotations

import random
from types import SimpleNamespace as Row

import pytest

from app.core import graph_expansion as gx
from app.evals.graph_eval import binary_ndcg, expansion_decision, theme_coverage

NUGGETS = {
    "n1": "The receipt is in my apron pocket, then the van.",
    "n2": "Thermal paper fades before the quarter closes.",
    "n3": "Payroll runs Thursday night and money lands Friday.",
}
FACTS = [["n1", "n2"], ["n3"]]


def test_siblings_come_from_facts_shared_with_a_quoted_nugget():
    hits = ["P1: The receipt is in my apron pocket, then the van. By Friday it is a rumour."]
    assert gx.sibling_nugget_texts(hits, NUGGETS, FACTS) == [NUGGETS["n2"]]
    assert gx.sibling_nugget_texts(["nothing quoted here"], NUGGETS, FACTS) == []


def test_rrf_keeps_the_top_hit_and_admits_graph_chunks():
    a, b, c = Row(text="alpha"), Row(text="bravo"), Row(text="charlie")
    fused = gx.rrf_fuse([a, b], [c], k=60, top_k=3)
    assert fused[0] is a and {r.text for r in fused} == {"alpha", "bravo", "charlie"}


async def test_expansion_adds_the_chunk_that_contains_a_sibling(monkeypatch):
    async def rows(project_id):
        return NUGGETS, FACTS

    async def search(project_id, text, top_k=3):
        return [Row(text=f"P2 said: {text} It was a mess.", retrieval_mode="keyword")]

    monkeypatch.setattr(gx, "_graph_rows", rows)
    hit = Row(text="P1: The receipt is in my apron pocket, then the van.", retrieval_mode="hybrid")
    out = await gx.expand_results("p", [hit], top_k=5, rrf_k=60, search=search)
    assert out[0] is hit
    assert any("Thermal paper fades" in r.text and r.retrieval_mode == "graph" for r in out)


async def test_retrieval_does_not_expand_unless_enabled(monkeypatch):
    from app.config import settings
    from app.core import rag

    called = []

    async def fake_expand(*args, **kwargs):
        called.append(True)
        return args[1]

    monkeypatch.setattr(gx, "expand_results", fake_expand)
    assert settings.rag_graph_expansion is False
    hit = [Row(text="x")]
    assert await rag._maybe_expand("p", hit, 5) == hit and called == []
    monkeypatch.setattr(settings, "rag_graph_expansion", True)
    await rag._maybe_expand("p", hit, 5)
    assert called == [True]


def test_theme_coverage_and_binary_ndcg():
    quotes = ["alpha beta gamma delta epsilon zeta", "eta theta iota kappa lambda mu"]
    assert theme_coverage(["x alpha beta gamma delta epsilon zeta y"], quotes) == 0.5
    assert binary_ndcg(["no", "has eta theta iota kappa lambda mu"], quotes[1:]) == pytest.approx(
        0.6309, abs=1e-3
    )


def _noise(seed, n):
    rng = random.Random(seed)
    return [rng.uniform(-0.02, 0.02) for _ in range(n)]


def test_the_rule_ships_a_clear_coverage_gain_without_guard_losses():
    ids = [f"q{i}" for i in range(30)]
    off = {q: 0.3 + e for q, e in zip(ids, _noise(1, 30), strict=True)}
    on = {q: 0.5 + e for q, e in zip(ids, _noise(2, 30), strict=True)}
    styles = {f"g{i}": ("lexical" if i % 2 else "paraphrase") for i in range(40)}
    guard = {"off": dict.fromkeys(styles, 0.7), "on": dict.fromkeys(styles, 0.7)}
    assert expansion_decision(off, on, styles, guard)["ships"] is True


def test_the_rule_refuses_when_a_single_hop_style_gets_worse():
    ids = [f"q{i}" for i in range(30)]
    off = {q: 0.3 + e for q, e in zip(ids, _noise(1, 30), strict=True)}
    on = {q: 0.5 + e for q, e in zip(ids, _noise(2, 30), strict=True)}
    styles = {f"g{i}": "lexical" for i in range(40)}
    guard = {
        "off": {q: 0.8 + e for q, e in zip(styles, _noise(3, 40), strict=True)},
        "on": {q: 0.5 + e for q, e in zip(styles, _noise(4, 40), strict=True)},
    }
    decision = expansion_decision(off, on, styles, guard)
    assert decision["guard_regressions"] == ["lexical"] and decision["ships"] is False
