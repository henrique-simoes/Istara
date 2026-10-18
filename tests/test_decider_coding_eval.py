"""Decider-coder research arm metrics (CF-SPEC-1, Phase 8, DEC-6). Pure, no decider call."""

import asyncio
import math
from types import SimpleNamespace

from app.evals.decider_coding_eval import _fleiss_binary, ask_decider, code_question, evaluate

CODEBOOK = [
    {"code": "cost", "definition": "Talks about price.", "include": ["fees"], "exclude": ["tax"]},
    {"code": "speed", "definition": "Talks about time.", "include": ["slow"], "exclude": []},
]
UNITS = [
    {"id": "u1", "text": "Fees", "gold": ["cost"], "coders": {"a": ["cost"], "b": ["cost"]}},
    {"id": "u2", "text": "It is slow", "gold": ["speed"], "coders": {"a": ["speed"], "b": []}},
    {
        "id": "u3",
        "text": "Fees and slow",
        "gold": ["cost", "speed"],
        "coders": {"a": ["cost"], "b": ["cost", "speed"]},
    },
    {"id": "u4", "text": "Nice colours", "gold": [], "coders": {"a": [], "b": ["speed"]}},
]


def test_fleiss_binary_matches_hand_values():
    assert _fleiss_binary([[1, 1], [0, 0], [1, 1], [0, 0]]) == 1.0
    assert _fleiss_binary([[1], [0]]) is None
    # Two raters, one disagreement in four items: p_bar = 0.75; 3 ones and 5 zeros of 8 votes,
    # so p_e = (3/8)^2 + (5/8)^2 = 34/64 and kappa = (0.75 - 34/64) / (1 - 34/64) = 7/15.
    assert math.isclose(_fleiss_binary([[1, 1], [0, 0], [1, 0], [0, 0]]), 7 / 15)


def test_perfect_decider_scores_and_is_never_counted_in_the_gate():
    probabilities = {
        (u["id"], c["code"]): (0.95 if c["code"] in u["gold"] else 0.05)
        for u in UNITS
        for c in CODEBOOK
    }
    report = evaluate(UNITS, CODEBOOK, probabilities)
    assert report["items"] == 8 and report["decider_accuracy"] == 1.0
    assert report["counted_in_reliability_gate"] is False
    assert report["per_code"]["cost"]["accuracy"] == 1.0
    assert report["per_code"]["cost"]["coverage_at_risk_0.10"] == 1.0
    assert set(report["coders"]) == {"a", "b"}
    assert report["kappa_inflation"] is not None


def test_codebook_becomes_one_yes_no_question_per_code_and_failures_are_counted():
    question = code_question(CODEBOOK[0])
    assert "`cost`" in question.instructions and "fees" in question.true_criterion
    assert question.false_criterion == "Excludes: tax"

    class Client:
        async def decide(self, state, questions):
            if state["evidence_unit"] == "Nice colours":
                return SimpleNamespace(ok=False)
            return SimpleNamespace(
                ok=True, answers={code: {"true": 0.8, "false": 0.2} for code in questions}
            )

    probabilities, failed = asyncio.run(ask_decider(Client(), UNITS, CODEBOOK))
    assert failed == ["u4"] and len(probabilities) == 6
