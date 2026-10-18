"""The System One wire contract (``POST /v1/systemone``) as Istara uses it.

TypeSafe's JEV defines the contract (https://docs.typesafe.ai/api, read 2026-10-17), and open-weight
decision models serve the same shape (llama.cpp ``/v1/systemone``; Kev, Laya, OpenJev). This module
is pure: it builds request bodies, validates responses strictly, and turns every failure into a
``not_runnable`` outcome with a reason. It never invents a verdict.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

SYSTEMONE_PATH = "/v1/systemone"
MAX_CHOICE_OPTIONS = 255
MIN_SCORE_LEVELS = 2
MAX_SCORE_LEVELS = 10
PROBABILITY_SUM_TOLERANCE = 1e-6
REVERSED_SUFFIX = "__reversed"
NOUL_TRUE = "true"
NOUL_FALSE = "false"
_ALIAS_SUFFIXES = ("-latest", "-preview", "-stable")
_RETRY_AFTER_CAP_S = 60.0


class ContractViolation(ValueError):
    """A response that does not satisfy the contract; ``reason`` is a stable code."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True)
class Choice:
    """Pick one option. ``options`` maps option name to its description (criteria)."""

    instructions: Any
    options: Mapping[str, Any]

    def __post_init__(self) -> None:
        count = len(self.options)
        if not 2 <= count <= MAX_CHOICE_OPTIONS:
            raise ValueError(f"a choice needs 2..{MAX_CHOICE_OPTIONS} options, got {count}")
        if any(not isinstance(name, str) or not name for name in self.options):
            raise ValueError("choice option names must be non-empty strings")


@dataclass(frozen=True)
class Score:
    """Rate along ordered levels, lowest first."""

    instructions: Any
    levels: Sequence[Any]

    def __post_init__(self) -> None:
        if not MIN_SCORE_LEVELS <= len(self.levels) <= MAX_SCORE_LEVELS:
            raise ValueError(f"a score needs {MIN_SCORE_LEVELS}..{MAX_SCORE_LEVELS} levels")


@dataclass(frozen=True)
class Noul:
    """A yes/no question; the answer is the probability of yes."""

    instructions: Any
    true_criterion: Any = None
    false_criterion: Any = None


def _question_body(question: Choice | Score | Noul) -> dict[str, Any]:
    if isinstance(question, Choice):
        return {
            "type": "choice",
            "instructions": question.instructions,
            "criteria": dict(question.options),
        }
    if isinstance(question, Score):
        return {
            "type": "score",
            "instructions": question.instructions,
            "criteria": list(question.levels),
        }
    body: dict[str, Any] = {"type": "noul", "instructions": question.instructions}
    criteria = {}
    if question.true_criterion is not None:
        criteria["true"] = question.true_criterion
    if question.false_criterion is not None:
        criteria["false"] = question.false_criterion
    if criteria:
        body["criteria"] = criteria
    return body


def build_request(
    state: Any, questions: Mapping[str, Choice | Score | Noul], model: str
) -> dict[str, Any]:
    """The JSON body for one ``/v1/systemone`` call. Question ids are not sent to the model."""
    if not isinstance(state, (str, Mapping, list)):
        raise ValueError("state must be a string, an object or an array")
    if not questions:
        raise ValueError("at least one question is required")
    if any(not isinstance(qid, str) or not qid for qid in questions):
        raise ValueError("question ids must be non-empty strings")
    if not model:
        raise ValueError("model is required")
    return {
        "state": state,
        "model": model,
        "questions": {qid: _question_body(q) for qid, q in questions.items()},
    }


def with_reversed_choices(
    questions: Mapping[str, Choice | Score | Noul]
) -> dict[str, Choice | Score | Noul]:
    """Add, for every choice, the same question with its options in reverse order.

    The reversed copy is keyed ``<id>__reversed``. Both are answered in one request, so position
    bias can be measured and merged (``app.core.decision.merge_order_flip``).
    """
    expanded: dict[str, Choice | Score | Noul] = dict(questions)
    for qid, question in questions.items():
        if isinstance(question, Choice):
            reversed_options = dict(reversed(list(question.options.items())))
            expanded[qid + REVERSED_SUFFIX] = Choice(question.instructions, reversed_options)
    return expanded


def is_alias_model_id(model: str) -> bool:
    """Moving aliases (``jev-latest``, ``jev-preview``) change behaviour without a code change."""
    name = model.strip().casefold()
    return name == "latest" or name.endswith(_ALIAS_SUFFIXES)


@dataclass
class DecisionOutcome:
    """One decider call. ``answers`` maps question id to a distribution over its outcomes."""

    status: str
    reason: str | None = None
    endpoint_id: str = ""
    requested_model: str = ""
    served_model: str | None = None
    alias_requested: bool = False
    answers: dict[str, dict[str, float]] = field(default_factory=dict)
    provider_confidence: dict[str, float | None] = field(default_factory=dict)
    usage: dict[str, int] = field(default_factory=dict)
    attempts: int = 0
    latency_s: float = 0.0

    @property
    def ok(self) -> bool:
        return self.status == "ok"


def not_runnable(reason: str, **fields: Any) -> DecisionOutcome:
    return DecisionOutcome(status="not_runnable", reason=reason, **fields)


def _distribution(raw: Any, expected: Sequence[str], qid: str) -> dict[str, float]:
    if not isinstance(raw, Mapping):
        raise ContractViolation("missing_probabilities", qid)
    if set(raw) != set(expected):
        raise ContractViolation("probability_keys_mismatch", qid)
    values: dict[str, float] = {}
    for key in expected:
        value = raw[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ContractViolation("probability_not_numeric", qid)
        value = float(value)
        if not math.isfinite(value) or value < 0.0:
            raise ContractViolation("probability_out_of_range", qid)
        values[key] = value
    if abs(sum(values.values()) - 1.0) > PROBABILITY_SUM_TOLERANCE:
        raise ContractViolation("probabilities_do_not_sum_to_one", qid)
    return values


def _confidence(answer: Mapping[str, Any]) -> float | None:
    value = answer.get("confidence")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) else None


def _parse_answer(
    qid: str, question: Choice | Score | Noul, answer: Any
) -> tuple[dict[str, float], Any]:
    if not isinstance(answer, Mapping):
        raise ContractViolation("missing_answer", qid)
    expected_type = _question_body(question)["type"]
    if answer.get("type") != expected_type:
        raise ContractViolation("answer_type_mismatch", qid)
    if isinstance(question, Choice):
        dist = _distribution(answer.get("probabilities"), list(question.options), qid)
        return dist, _confidence(answer)
    if isinstance(question, Score):
        keys = [str(i) for i in range(len(question.levels))]
        return _distribution(answer.get("probabilities"), keys, qid), _confidence(answer)
    p_yes = answer.get("noul")
    if isinstance(p_yes, bool) or not isinstance(p_yes, (int, float)):
        raise ContractViolation("missing_probabilities", qid)
    p_yes = float(p_yes)
    if not math.isfinite(p_yes) or not 0.0 <= p_yes <= 1.0:
        raise ContractViolation("probability_out_of_range", qid)
    return {NOUL_TRUE: p_yes, NOUL_FALSE: 1.0 - p_yes}, None


def parse_response(body: Any, questions: Mapping[str, Choice | Score | Noul]) -> DecisionOutcome:
    """Validate a 200 response strictly; any gap raises :class:`ContractViolation`.

    Every requested question must be answered with its type and a full probability vector. A
    decider that cannot return the vector cannot be calibrated, so it is not admissible.
    """
    if not isinstance(body, Mapping):
        raise ContractViolation("malformed_body")
    served = body.get("model")
    if not isinstance(served, str) or not served.strip():
        raise ContractViolation("missing_served_model")
    answers = body.get("answers")
    if not isinstance(answers, Mapping):
        raise ContractViolation("missing_answers")
    outcome = DecisionOutcome(status="ok", served_model=served.strip())
    for qid, question in questions.items():
        dist, confidence = _parse_answer(qid, question, answers.get(qid))
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


def check_served_identity(requested: str, served: str) -> str | None:
    """Reason code when the served model breaks provenance, else None.

    A pinned request must be served by exactly that model (spine rule: the requested model is not
    evidence of the model that ran). An alias request is allowed to resolve to a versioned id,
    which is recorded; the trust gate refuses alias scopes later.
    """
    if is_alias_model_id(requested):
        return None
    if requested.strip().casefold() != served.strip().casefold():
        return "served_model_mismatch"
    return None


HTTP_REASONS = {
    401: "unauthorized",
    403: "forbidden",
    404: "endpoint_not_found",
    413: "body_too_large",
    415: "unsupported_encoding",
    422: "validation_failed",
}
RETRYABLE_STATUSES = frozenset({429, 503, 529})


def http_failure_reason(status: int, body: Any) -> str:
    """Stable reason code for a non-200 response."""
    if status == 400:
        text = str(body or "")
        return "max_tokens_exceeded" if "max_tokens_exceeded" in text else "bad_request"
    if status in RETRYABLE_STATUSES:
        return "rate_limited" if status == 429 else "overloaded"
    return HTTP_REASONS.get(status, f"http_{status}")


_SECONDS = re.compile(r"^\s*\d+(\.\d+)?\s*$")


def retry_delay(
    attempt: int,
    retry_after: str | None,
    *,
    base_s: float = 0.5,
    cap_s: float = 8.0,
    now: datetime | None = None,
) -> float:
    """Seconds to wait before retry ``attempt`` (1-based).

    ``retry-after`` wins when present (seconds or an HTTP date), capped at 60 s. Otherwise the
    delay doubles from ``base_s`` up to ``cap_s``.
    """
    if retry_after:
        if _SECONDS.match(retry_after):
            return min(_RETRY_AFTER_CAP_S, float(retry_after))
        try:
            when = parsedate_to_datetime(retry_after)
        except (TypeError, ValueError):
            when = None
        if when is not None:
            if when.tzinfo is None:
                when = when.replace(tzinfo=UTC)
            seconds = (when - (now or datetime.now(UTC))).total_seconds()
            return min(_RETRY_AFTER_CAP_S, max(0.0, seconds))
    return min(cap_s, base_s * (2 ** max(0, attempt - 1)))
