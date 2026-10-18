"""Decider-coder research arm (CF-SPEC-1, Phase 8; owner decision DEC-6; research doc §13).

Can a typed decision model *code*? On a corpus with human gold codes, the decider answers one
yes/no question per (evidence unit, code), built from the codebook's definition, inclusion and
exclusion criteria. This module reports, per code and overall:

* calibration of P(code applies) against gold: ECE and binary Brier;
* selective coding: the risk–coverage curve and the coverage reachable at a risk ceiling;
* error structure with each LLM coder: error correlation (phi) and Yule's Q on the same items;
* agreement: Fleiss' kappa over the LLM coders **without** and **with** the decider as a rater,
  which measures how much a non-independent rater inflates reliability (research doc §13, item 2).

The decider's codes are a research measurement. They are never written as code applications and
never counted in the Research Spine's reliability gate; changing the gate is a separate owner
decision taken from this evidence. Running it calls a decider (live, metered, possibly hosted), so
it needs the owner's permission and the project's opt-in (``open_decider`` enforces the latter).

Corpus JSON::

    {"codebook": [{"code", "definition", "include": [...], "exclude": [...]}],
     "units": [{"id", "text", "gold": [codes], "coders": {"<coder>": [codes]}}]}

    python -m app.evals.decider_coding_eval --corpus corpus.json --project <id> \\
        --endpoint <decider id> --out decider_coding.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from app.core.decision.calibration import brier_score, expected_calibration_error, risk_coverage
from app.core.decision.ensemble import error_correlation, yules_q

DEFAULT_TAU = 0.5
RISK_CEILING = 0.10


def code_question(code: Mapping[str, Any]) -> Any:
    """One yes/no question for a code, from its definition and criteria (research doc §13)."""
    from app.core.decider.contract import Noul

    include = "; ".join(code.get("include") or [])
    exclude = "; ".join(code.get("exclude") or [])
    return Noul(
        f"Does the evidence unit express the code `{code['code']}`?",
        true_criterion=f"{code.get('definition', '')} Includes: {include}".strip(),
        false_criterion=f"Excludes: {exclude}" if exclude else None,
    )


async def ask_decider(client: Any, units: Sequence[Mapping[str, Any]], codebook: Sequence[Any]):
    """``{(unit_id, code): P(applies)}``; a unit whose call fails is left out and counted."""
    questions = {code["code"]: code_question(code) for code in codebook}
    probabilities: dict[tuple[str, str], float] = {}
    failed: list[str] = []
    for unit in units:
        outcome = await client.decide({"evidence_unit": unit["text"]}, questions)
        if not outcome.ok:
            failed.append(unit["id"])
            continue
        for code in questions:
            probabilities[(unit["id"], code)] = outcome.answers[code]["true"]
    return probabilities, failed


def _fleiss_binary(ratings: Sequence[Sequence[int]]) -> float | None:
    """Fleiss' kappa for binary ratings, one row of rater votes per item."""
    rows = [row for row in ratings if row]
    if not rows or len({len(row) for row in rows}) != 1 or len(rows[0]) < 2:
        return None
    n = len(rows[0])
    p_items = []
    totals = [0, 0]
    for row in rows:
        ones = sum(row)
        zeros = n - ones
        totals[0] += zeros
        totals[1] += ones
        p_items.append((ones * (ones - 1) + zeros * (zeros - 1)) / (n * (n - 1)))
    p_bar = sum(p_items) / len(rows)
    grand = len(rows) * n
    p_e = sum((t / grand) ** 2 for t in totals)
    if p_e >= 1.0:
        return None
    return (p_bar - p_e) / (1.0 - p_e)


def _coverage_at_risk(curve: list[tuple[float, float, float]], ceiling: float) -> float:
    return max((coverage for _, coverage, risk in curve if risk <= ceiling), default=0.0)


def evaluate(
    units: Sequence[Mapping[str, Any]],
    codebook: Sequence[Mapping[str, Any]],
    probabilities: Mapping[tuple[str, str], float],
    *,
    tau: float = DEFAULT_TAU,
) -> dict[str, Any]:
    """Pure: metrics of the decider's codes against gold and against the LLM coders."""
    codes = [code["code"] for code in codebook]
    coders = sorted({name for unit in units for name in (unit.get("coders") or {})})
    items = [(u, c) for u in units for c in codes if (u["id"], c) in probabilities]
    if not items:
        return {"items": 0, "note": "no decider answers to evaluate"}

    def gold(unit, code) -> int:
        return int(code in set(unit.get("gold") or []))

    per_code: dict[str, Any] = {}
    for code in codes:
        rows = [(probabilities[(u["id"], code)], gold(u, code)) for u, c in items if c == code]
        if not rows:
            continue
        confidences = [max(p, 1.0 - p) for p, _ in rows]
        correct = [(p >= tau) == bool(y) for p, y in rows]
        curve = risk_coverage(confidences, correct)
        per_code[code] = {
            "items": len(rows),
            "positives": sum(y for _, y in rows),
            "ece": expected_calibration_error(confidences, correct),
            "brier": brier_score([[1.0 - p, p] for p, _ in rows], [y for _, y in rows]),
            "accuracy": sum(correct) / len(correct),
            f"coverage_at_risk_{RISK_CEILING:.2f}": _coverage_at_risk(curve, RISK_CEILING),
        }

    decider_votes = [int(probabilities[(u["id"], c)] >= tau) for u, c in items]
    gold_labels = [gold(u, c) for u, c in items]
    decider_errors = [v != g for v, g in zip(decider_votes, gold_labels)]
    coder_votes = {
        name: [int(c in set((u.get("coders") or {}).get(name, []))) for u, c in items]
        for name in coders
    }
    structure = {}
    for name, votes in coder_votes.items():
        coder_errors = [v != g for v, g in zip(votes, gold_labels)]
        structure[name] = {
            "accuracy": 1.0 - sum(coder_errors) / len(coder_errors),
            "error_correlation_with_decider": error_correlation(decider_errors, coder_errors),
            "yules_q_with_decider": yules_q(
                [not e for e in decider_errors], [not e for e in coder_errors]
            ),
        }
    without = [[coder_votes[n][i] for n in coders] for i in range(len(items))]
    with_decider = [row + [decider_votes[i]] for i, row in enumerate(without)]
    kappa_without = _fleiss_binary(without) if len(coders) >= 2 else None
    kappa_with = _fleiss_binary(with_decider) if coders else None
    return {
        "items": len(items),
        "tau": tau,
        "per_code": per_code,
        "decider_accuracy": 1.0 - sum(decider_errors) / len(decider_errors),
        "coders": structure,
        "fleiss_kappa_llm_coders": kappa_without,
        "fleiss_kappa_with_decider": kappa_with,
        "kappa_inflation": (
            kappa_with - kappa_without
            if kappa_with is not None and kappa_without is not None
            else None
        ),
        "counted_in_reliability_gate": False,
    }


async def run(corpus_path: str, project_id: str, endpoint_id: str) -> dict[str, Any]:
    from app.core.decider.access import open_decider

    with open(corpus_path, encoding="utf-8") as handle:
        corpus = json.load(handle)
    client = await open_decider(endpoint_id, project_id)
    probabilities, failed = await ask_decider(client, corpus["units"], corpus["codebook"])
    report = evaluate(corpus["units"], corpus["codebook"], probabilities)
    report.update(
        {
            "endpoint_id": endpoint_id,
            "failed_units": failed,
            "generated_at": datetime.now(UTC).isoformat(),
        }
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    report = asyncio.run(run(args.corpus, args.project, args.endpoint))
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
