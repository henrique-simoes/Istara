"""OpenAI Decisions wire translation (CF-SPEC-1, Phase 8). Pure, no network.

The request follows OpenAI's guide (named questions in an array; choices as value + description;
levels as label + description, lowest first; predicates for yes/no). Answers must map back to the
same canonical distributions the System One parser produces, and a refusal or a partial vector is
a contract violation.
"""

from app.core.decider.contract import Choice, ContractViolationError, Noul, Score
from app.core.decider.openai_decisions import (
    build_decisions_request,
    parse_decisions_response,
    served_matches,
)

QUESTIONS = {
    "relation": Choice("Relation?", {"supports": "states it", "contradicts": "opposite"}),
    "quality": Score("Quality?", ["poor", "fair", "good"]),
    "grounded": Noul("Exact span?", true_criterion="verbatim", false_criterion="paraphrase"),
}


def _body(**overrides):
    answers = [
        {
            "type": "choice",
            "name": "relation",
            "choice": "supports",
            "probabilities": [
                {"value": "supports", "probability": 0.8},
                {"value": "contradicts", "probability": 0.2},
            ],
            "confidence": 0.7,
        },
        {
            "type": "score",
            "name": "quality",
            "score": 1.5,
            "probabilities": [
                {"value": 0, "label": "poor", "probability": 0.1},
                {"value": 1, "label": "fair", "probability": 0.3},
                {"value": 2, "label": "good", "probability": 0.6},
            ],
            "confidence": 0.6,
        },
        {"type": "predicate", "name": "grounded", "probability": 0.9},
    ]
    body = {"model": "gpt-6-luna", "answers": answers, "usage": {"input_tokens": 40}}
    body.update(overrides)
    return body


def test_request_matches_the_documented_shape():
    body = build_decisions_request({"claim": "c"}, QUESTIONS, "gpt-6-luna")
    assert body["model"] == "gpt-6-luna" and body["input"] == '{"claim": "c"}'
    by_name = {q["name"]: q for q in body["questions"]}
    assert by_name["relation"]["choices"][0] == {"value": "supports", "description": "states it"}
    assert [lv["label"] for lv in by_name["quality"]["levels"]] == ["poor", "fair", "good"]
    assert by_name["grounded"]["type"] == "predicate"
    assert "True when: verbatim" in by_name["grounded"]["instructions"]


def test_answers_map_to_canonical_distributions():
    outcome = parse_decisions_response(_body(), QUESTIONS)
    assert outcome.ok and outcome.served_model == "gpt-6-luna"
    assert outcome.answers["relation"] == {"supports": 0.8, "contradicts": 0.2}
    assert outcome.answers["quality"] == {"0": 0.1, "1": 0.3, "2": 0.6}
    assert abs(outcome.answers["grounded"]["false"] - 0.1) < 1e-12
    assert outcome.provider_confidence["relation"] == 0.7 and outcome.usage == {"input_tokens": 40}


def _violation(body) -> str:
    try:
        parse_decisions_response(body, QUESTIONS)
    except ContractViolationError as error:
        return error.reason
    return "accepted"


def test_refusals_and_partial_vectors_are_violations_never_verdicts():
    body = _body()
    body["answers"][2] = {"type": "refusal", "name": "grounded"}
    assert _violation(body) == "refused"
    body = _body()
    body["answers"][0]["probabilities"].pop()
    assert _violation(body) == "probability_keys_mismatch"
    body = _body()
    body["answers"].pop(1)
    assert _violation(body) == "missing_answer"
    assert _violation(_body(model="")) == "missing_served_model"


def test_dated_snapshot_counts_as_the_requested_model():
    assert served_matches("gpt-6-luna", "gpt-6-luna-2026-10-06")
    assert not served_matches("gpt-6-luna", "gpt-6-sol")
