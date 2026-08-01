"""Deterministic industry scoring (CF-324): BFCL AST match + τ-bench action match.

No judge model involved — these scorers compare captured outputs against published
ground truth from the scenario's ``expected`` metadata:

- **BFCL** (prompt mode): extract the first JSON ``{"name", "arguments"}`` object from
  the output and compare against ``ground_truth`` = ``[{func_name: {arg: [allowed]}}]``.
  Strict match (official BFCL semantics): the function name must match AND every
  ground-truth argument must be present with an allowed value. ``name_accuracy`` and
  ``argument_validity`` subscores feed metric axis 1.
- **τ-bench adapted**: extract ``{"action": ...}`` and check membership in the
  expected action sequence (first-action correctness).

Everything is pure/offline (stdlib only), unit-tested, and safe at T0.
"""

from __future__ import annotations

import json
import re
from typing import Any

_JSON_OBJECT = re.compile(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", re.DOTALL)
_FENCE = re.compile(r"```(?:json)?\s*|\s*```")


def extract_json_call(text: str) -> dict[str, Any] | None:
    """Extract the first parseable JSON object containing a ``name`` or ``action`` key."""
    if not text:
        return None
    cleaned = _FENCE.sub("", text)
    candidates = [cleaned.strip(), *_JSON_OBJECT.findall(cleaned)]
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(value, dict) and ("name" in value or "action" in value):
            return value
    return None


def _normalise(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip().lower()
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, (list, dict)):
        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    return value


def score_bfcl(ground_truth: Any, output_text: str) -> dict[str, Any]:
    """Strict BFCL prompt-mode score with name/argument subscores."""
    parsed = extract_json_call(output_text)
    result = {
        "score": 0.0, "name_accuracy": 0.0, "argument_validity": 0.0,
        "parsed": parsed, "error": None,
    }
    if parsed is None:
        result["error"] = "no_json_call_extracted"
        return result
    if not isinstance(ground_truth, list) or not ground_truth:
        result["error"] = "missing_ground_truth"
        return result
    truth = ground_truth[0]
    truth_name, truth_args = next(iter(truth.items()))
    name = str(parsed.get("name", ""))
    if name != truth_name:
        # BFCL allows module-prefixed mismatches only when the suffix matches.
        if not (truth_name.endswith(f".{name}") or name.endswith(f".{truth_name}")):
            result["error"] = "wrong_function"
            return result
    result["name_accuracy"] = 1.0
    given = parsed.get("arguments") or parsed.get("parameters") or {}
    if not isinstance(given, dict):
        result["error"] = "arguments_not_object"
        return result
    checks = []
    for arg, allowed in truth_args.items():
        allowed_set = {_normalise(v) for v in (allowed if isinstance(allowed, list) else [allowed])}
        checks.append(_normalise(given.get(arg)) in allowed_set)
    if checks and all(checks):
        result["argument_validity"] = 1.0
        result["score"] = 1.0
    else:
        result["argument_validity"] = sum(checks) / len(checks) if checks else 0.0
        result["error"] = "argument_mismatch"
    return result


def score_tau(expected_actions: list[str], output_text: str) -> dict[str, Any]:
    """τ-bench adapted first-action score."""
    parsed = extract_json_call(output_text)
    result = {"score": 0.0, "action_match": 0.0, "parsed": parsed, "error": None}
    if parsed is None:
        result["error"] = "no_json_action_extracted"
        return result
    action = str(parsed.get("action", ""))
    if action and action in (expected_actions or []):
        result["score"] = 1.0
        result["action_match"] = 1.0
    else:
        result["error"] = f"unexpected_action:{action or 'none'}"
    return result


def score_industry_record(scenario_expected: dict[str, Any], output_text: str) -> dict[str, Any] | None:
    """Route one scenario's expected metadata to the right scorer (None if not scorable)."""
    if "bfcl_ground_truth" in scenario_expected:
        return {"kind": "bfcl", **score_bfcl(scenario_expected["bfcl_ground_truth"], output_text)}
    if "tau_expected_actions" in scenario_expected:
        return {"kind": "tau", **score_tau(scenario_expected["tau_expected_actions"], output_text)}
    return None
