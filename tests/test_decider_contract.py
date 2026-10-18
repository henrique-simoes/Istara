"""System One wire contract (CF-SPEC-1, Phase 1): request building and strict response validation.

Request and response fixtures follow TypeSafe's API reference (https://docs.typesafe.ai/api, read
2026-10-17). Every malformed response must become a stable reason code, never a verdict.
"""

from datetime import UTC, datetime

from app.core.decider.contract import (
    NOUL_FALSE,
    NOUL_TRUE,
    Choice,
    ContractViolation,
    Noul,
    Score,
    build_request,
    check_served_identity,
    http_failure_reason,
    is_alias_model_id,
    parse_response,
    retry_delay,
    with_reversed_choices,
)

QUESTIONS = {
    "department": Choice(
        "Which team should handle this?",
        {"billing": "Invoices, payments, refunds", "sales": "Pricing and contracts"},
    ),
    "severity": Score("How severe is the issue?", ["Minor", "Moderate", "Severe"]),
    "is_urgent": Noul("Does this need same-day attention?"),
}

DOCUMENTED_RESPONSE = {
    "model": "jev-1.13.0",
    "answers": {
        "department": {
            "type": "choice",
            "choice": "billing",
            "probabilities": {"billing": 0.9, "sales": 0.1},
            "confidence": 0.8,
        },
        "severity": {
            "type": "score",
            "score": 0.6,
            "legend": {"0": "Minor", "1": "Moderate", "2": "Severe"},
            "probabilities": {"0": 0.4, "1": 0.6, "2": 0.0},
            "confidence": 0.7,
        },
        "is_urgent": {"type": "noul", "noul": 0.3},
    },
    "usage": {"input_tokens": 280, "output_tokens": 40},
}


def _reason(body, questions=QUESTIONS) -> str:
    try:
        parse_response(body, questions)
    except ContractViolation as violation:
        return violation.reason
    return "accepted"


def _with_answer(qid: str, answer) -> dict:
    answers = dict(DOCUMENTED_RESPONSE["answers"])
    answers[qid] = answer
    return {**DOCUMENTED_RESPONSE, "answers": answers}


def test_build_request_matches_the_documented_shape():
    body = build_request("The invoice total doesn't match.", QUESTIONS, "jev-1.13.0")
    assert body["model"] == "jev-1.13.0"
    assert body["questions"]["department"] == {
        "type": "choice",
        "instructions": "Which team should handle this?",
        "criteria": {"billing": "Invoices, payments, refunds", "sales": "Pricing and contracts"},
    }
    assert body["questions"]["severity"]["criteria"] == ["Minor", "Moderate", "Severe"]
    assert body["questions"]["is_urgent"] == {
        "type": "noul",
        "instructions": "Does this need same-day attention?",
    }
    noul = build_request("x", {"q": Noul("Is it?", "yes means A", "no means B")}, "m")
    assert noul["questions"]["q"]["criteria"] == {"true": "yes means A", "false": "no means B"}


def test_question_limits_follow_the_api_reference():
    for bad in (
        lambda: Choice("one option", {"a": None}),
        lambda: Choice("too many", {f"o{i}": None for i in range(256)}),
        lambda: Score("one level", ["only"]),
        lambda: Score("eleven", [str(i) for i in range(11)]),
        lambda: build_request(3.14, QUESTIONS, "m"),
        lambda: build_request("x", {}, "m"),
        lambda: build_request("x", QUESTIONS, ""),
    ):
        try:
            bad()
        except ValueError:
            continue
        raise AssertionError("expected ValueError")


def test_reversed_choices_reverse_option_order_only_for_choices():
    expanded = with_reversed_choices(QUESTIONS)
    assert list(expanded["department__reversed"].options) == ["sales", "billing"]
    assert "severity__reversed" not in expanded and "is_urgent__reversed" not in expanded


def test_documented_response_parses_into_full_distributions():
    outcome = parse_response(DOCUMENTED_RESPONSE, QUESTIONS)
    assert outcome.ok and outcome.served_model == "jev-1.13.0"
    assert outcome.answers["department"] == {"billing": 0.9, "sales": 0.1}
    assert outcome.answers["severity"] == {"0": 0.4, "1": 0.6, "2": 0.0}
    assert outcome.answers["is_urgent"] == {NOUL_TRUE: 0.3, NOUL_FALSE: 0.7}
    assert outcome.provider_confidence == {"department": 0.8, "severity": 0.7, "is_urgent": None}
    assert outcome.usage == {"input_tokens": 280, "output_tokens": 40}


def test_incomplete_or_malformed_responses_are_never_verdicts():
    choice = DOCUMENTED_RESPONSE["answers"]["department"]
    assert _reason([]) == "malformed_body"
    assert _reason({**DOCUMENTED_RESPONSE, "model": ""}) == "missing_served_model"
    assert _reason({"model": "jev-1.13.0"}) == "missing_answers"
    assert _reason(_with_answer("department", None)) == "missing_answer"
    assert _reason(_with_answer("department", {**choice, "type": "score"})) == "answer_type_mismatch"
    no_vector = {"type": "choice", "choice": "billing", "confidence": 0.8}
    assert _reason(_with_answer("department", no_vector)) == "missing_probabilities"
    extra = {**choice, "probabilities": {"billing": 0.9, "sales": 0.05, "other": 0.05}}
    assert _reason(_with_answer("department", extra)) == "probability_keys_mismatch"
    short = {**choice, "probabilities": {"billing": 0.9, "sales": 0.05}}
    assert _reason(_with_answer("department", short)) == "probabilities_do_not_sum_to_one"
    negative = {**choice, "probabilities": {"billing": 1.1, "sales": -0.1}}
    assert _reason(_with_answer("department", negative)) == "probability_out_of_range"
    text = {**choice, "probabilities": {"billing": "0.9", "sales": 0.1}}
    assert _reason(_with_answer("department", text)) == "probability_not_numeric"
    assert _reason(_with_answer("is_urgent", {"type": "noul", "noul": 1.5})) == (
        "probability_out_of_range"
    )
    assert _reason(_with_answer("is_urgent", {"type": "noul"})) == "missing_probabilities"


def test_served_identity_rules():
    assert check_served_identity("jev-1.13.0", "jev-1.13.0") is None
    assert check_served_identity("jev-1.13.0", "jev-1.14.0") == "served_model_mismatch"
    assert check_served_identity("jev-latest", "jev-1.13.0") is None
    assert is_alias_model_id("jev-latest") and is_alias_model_id("jev-preview")
    assert not is_alias_model_id("jev-1.13.0") and not is_alias_model_id("kev-4b")


def test_http_failures_map_to_stable_reasons():
    assert http_failure_reason(400, '{"error": "max_tokens_exceeded"}') == "max_tokens_exceeded"
    assert http_failure_reason(400, "nope") == "bad_request"
    assert http_failure_reason(401, "") == "unauthorized"
    assert http_failure_reason(413, "") == "body_too_large"
    assert http_failure_reason(415, "") == "unsupported_encoding"
    assert http_failure_reason(422, "") == "validation_failed"
    assert http_failure_reason(429, "") == "rate_limited"
    assert http_failure_reason(529, "") == "overloaded"
    assert http_failure_reason(500, "") == "http_500"


def test_retry_delay_honours_retry_after_then_backs_off():
    assert retry_delay(1, "2") == 2.0
    assert retry_delay(1, "3600") == 60.0
    now = datetime(2026, 10, 17, 12, 0, 0, tzinfo=UTC)
    assert retry_delay(1, "Sat, 17 Oct 2026 12:00:05 GMT", now=now) == 5.0
    assert retry_delay(1, "Sat, 17 Oct 2026 11:59:00 GMT", now=now) == 0.0
    assert [retry_delay(a, None) for a in (1, 2, 3, 4, 5, 6)] == [0.5, 1.0, 2.0, 4.0, 8.0, 8.0]
    assert retry_delay(2, "not a date") == 1.0
