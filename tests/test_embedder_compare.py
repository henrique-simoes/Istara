"""The default-embedder decision follows the rule fixed before the numbers existed (DEC-15).

A candidate qualifies when it is significantly better than the shipped baseline on hybrid nDCG@10
overall and on the Spanish questions, and not significantly worse on any English style (paired
sign-flip randomization, Holm across candidates within each comparison). Among qualifiers the
highest overall mean wins; when the top two do not differ significantly the preferred model wins.
"""

from __future__ import annotations

import random

STYLES = {**{f"L{i}": "lexical" for i in range(30)}, **{f"P{i}": "paraphrase" for i in range(30)}}
STYLES.update({f"F{i}": "fact" for i in range(12)})
STYLES.update({f"ES{i}": "spanish" for i in range(40)})


def _report(score):
    """An `evaluate`-shaped report whose hybrid per-question nDCG@10 comes from ``score(qid)``."""
    per_question = {qid: {"ndcg@10": score(qid)} for qid in STYLES}
    return {
        "systems": {
            "hybrid": {"per_question": per_question},
            "vector": {"per_question": per_question},
        }
    }


def _noise(seed):
    rng = random.Random(seed)
    return {qid: rng.uniform(-0.05, 0.05) for qid in STYLES}


def test_a_candidate_better_overall_and_in_spanish_wins():
    from app.evals.embedder_compare import compare

    base = _noise(1)
    good = _noise(2)
    reports = {
        "shipped": _report(lambda q: 0.5 + base[q] - (0.3 if q.startswith("ES") else 0)),
        "multilingual": _report(lambda q: 0.6 + good[q]),
    }
    result = compare(reports, STYLES, baseline="shipped", prefer="multilingual")
    assert result["qualifying"] == ["multilingual"]
    assert result["winner"] == "multilingual"
    assert result["candidates"]["multilingual"]["overall"]["holm_p"] < 0.05


def test_an_english_regression_disqualifies_a_candidate():
    from app.evals.embedder_compare import compare

    base = _noise(3)
    reports = {
        "shipped": _report(lambda q: 0.6 + base[q] - (0.4 if q.startswith("ES") else 0)),
        # Much better in Spanish and overall, but lexical questions fall.
        "trade-off": _report(
            lambda q: 0.9 if q.startswith("ES") else (0.3 if q.startswith("L") else 0.8)
        ),
    }
    result = compare(reports, STYLES, baseline="shipped", prefer=None)
    assert result["candidates"]["trade-off"]["regressions"] == ["lexical"]
    assert result["qualifying"] == [] and result["winner"] == "shipped"


def test_the_preferred_model_wins_a_statistical_tie_at_the_top():
    from app.evals.embedder_compare import compare

    base, a, b = _noise(4), _noise(5), _noise(6)
    reports = {
        "shipped": _report(lambda q: 0.4 + base[q]),
        "slightly-higher": _report(lambda q: 0.705 + a[q]),
        "preferred": _report(lambda q: 0.70 + b[q]),
    }
    result = compare(reports, STYLES, baseline="shipped", prefer="preferred")
    assert set(result["qualifying"]) == {"slightly-higher", "preferred"}
    assert result["top_two_differ"] is False
    assert result["winner"] == "preferred"


def test_no_qualifier_keeps_the_shipped_default():
    from app.evals.embedder_compare import compare

    base, other = _noise(7), _noise(8)
    reports = {
        "shipped": _report(lambda q: 0.5 + base[q]),
        "same": _report(lambda q: 0.5 + other[q]),
    }
    result = compare(reports, STYLES, baseline="shipped", prefer="same")
    assert result["qualifying"] == [] and result["winner"] == "shipped"
