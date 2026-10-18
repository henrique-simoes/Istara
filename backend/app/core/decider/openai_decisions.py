"""The OpenAI Decisions wire contract (``POST /v1/decisions``, public beta) as Istara uses it.

Read from OpenAI's guide (developers.openai.com/api/docs/guides/decisions, 2026-10-18). A request
carries ``model``, ``input`` (a string here) and a ``questions`` array whose items are named and
typed ``predicate``, ``choice`` (``choices``: value + description) or ``score`` (``levels``: label +
description, lowest first). The response's ``answers`` array echoes each name; ``choice`` and
``score`` return a probability for every option or level, ``predicate`` returns the probability
that the condition holds. This module maps those to Istara's question types and canonical
distributions, so the rest of the decider layer is protocol-neutral. A refusal, a missing answer
or a partial vector is a contract violation, never a verdict.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from typing import Any

from app.core.decider.contract import (
    NOUL_FALSE,
    NOUL_TRUE,
    PROBABILITY_SUM_TOLERANCE,
    Choice,
    ContractViolationError,
    DecisionOutcome,
    Noul,
    Score,
)

DECISIONS_PATH = "/v1/decisions"


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _question(qid: str, question: Choice | Score | Noul) -> dict[str, Any]:
    if isinstance(question, Choice):
        return {
            "type": "choice",
            "name": qid,
            "instructions": _text(question.instructions),
            "choices": [
                {"value": name, "description": _text(description)}
                for name, description in question.options.items()
            ],
        }
    if isinstance(question, Score):
        return {
            "type": "score",
            "name": qid,
            "instructions": _text(question.instructions),
            "levels": [
                {"label": _text(level), "description": _text(level)} for level in question.levels
            ],
        }
    instructions = _text(question.instructions)
    if question.true_criterion is not None:
        instructions += f"\nTrue when: {_text(question.true_criterion)}"
    if question.false_criterion is not None:
        instructions += f"\nFalse when: {_text(question.false_criterion)}"
    return {"type": "predicate", "name": qid, "instructions": instructions}


def build_decisions_request(
    state: Any, questions: Mapping[str, Choice | Score | Noul], model: str
) -> dict[str, Any]:
    """The JSON body for one ``/v1/decisions`` call. The state becomes the ``input`` text."""
    if not questions:
        raise ValueError("at least one question is required")
    if not model:
        raise ValueError("model is required")
    return {
        "model": model,
        "input": _text(state),
        "questions": [_question(qid, question) for qid, question in questions.items()],
    }


def _probability(value: Any, qid: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractViolationError("probability_not_numeric", qid)
    value = float(value)
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ContractViolationError("probability_out_of_range", qid)
    return value


def _vector(raw: Any, expected: list[str], qid: str) -> dict[str, float]:
    if not isinstance(raw, list):
        raise ContractViolationError("missing_probabilities", qid)
    dist: dict[str, float] = {}
    for item in raw:
        if not isinstance(item, Mapping) or "value" not in item:
            raise ContractViolationError("missing_probabilities", qid)
        dist[str(item["value"])] = _probability(item.get("probability"), qid)
    if set(dist) != set(expected):
        raise ContractViolationError("probability_keys_mismatch", qid)
    if abs(sum(dist.values()) - 1.0) > PROBABILITY_SUM_TOLERANCE:
        raise ContractViolationError("probabilities_do_not_sum_to_one", qid)
    return {key: dist[key] for key in expected}


def _confidence(answer: Mapping[str, Any]) -> float | None:
    value = answer.get("confidence")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) else None


def _parse_answer(
    qid: str, question: Choice | Score | Noul, answer: Any
) -> tuple[dict[str, float], float | None]:
    if not isinstance(answer, Mapping):
        raise ContractViolationError("missing_answer", qid)
    kind = answer.get("type")
    if kind == "refusal":
        raise ContractViolationError("refused", qid)
    if isinstance(question, Choice):
        if kind != "choice":
            raise ContractViolationError("answer_type_mismatch", qid)
        dist = _vector(answer.get("probabilities"), list(question.options), qid)
        return dist, _confidence(answer)
    if isinstance(question, Score):
        if kind != "score":
            raise ContractViolationError("answer_type_mismatch", qid)
        keys = [str(i) for i in range(len(question.levels))]
        return _vector(answer.get("probabilities"), keys, qid), _confidence(answer)
    if kind != "predicate":
        raise ContractViolationError("answer_type_mismatch", qid)
    p_true = _probability(answer.get("probability"), qid)
    return {NOUL_TRUE: p_true, NOUL_FALSE: 1.0 - p_true}, None


def parse_decisions_response(
    body: Any, questions: Mapping[str, Choice | Score | Noul]
) -> DecisionOutcome:
    """Validate a 200 response strictly into a canonical :class:`DecisionOutcome`."""
    if not isinstance(body, Mapping):
        raise ContractViolationError("malformed_body")
    served = body.get("model")
    if not isinstance(served, str) or not served.strip():
        raise ContractViolationError("missing_served_model")
    answers = body.get("answers")
    if not isinstance(answers, list):
        raise ContractViolationError("missing_answers")
    by_name = {a.get("name"): a for a in answers if isinstance(a, Mapping)}
    outcome = DecisionOutcome(status="ok", served_model=served.strip())
    for qid, question in questions.items():
        dist, confidence = _parse_answer(qid, question, by_name.get(qid))
        outcome.answers[qid] = dist
        outcome.provider_confidence[qid] = confidence
    usage = body.get("usage")
    if isinstance(usage, Mapping):
        outcome.usage = {
            key: int(usage[key])
            for key in ("input_tokens", "output_tokens")
            if isinstance(usage.get(key), int) and not isinstance(usage.get(key), bool)
        }
    return outcome


def served_matches(requested: str, served: str) -> bool:
    """OpenAI may answer a model name with a dated snapshot (``<name>-<date>``); that counts."""
    requested, served = requested.strip().casefold(), served.strip().casefold()
    return served == requested or served.startswith(requested + "-")
