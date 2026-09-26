"""Pick the default embedder by the rule fixed before the numbers existed (DEC-15, 2026-09-26).

Inputs are ``retrieval_eval evaluate`` reports, one per arm (model and prompt scheme), on the same
qrels. A candidate qualifies when it is significantly better than the shipped baseline on hybrid
nDCG@10 overall and on the Spanish questions, and not significantly worse on any English style;
each comparison is a paired sign-flip randomization test on per-question nDCG@10, Holm-adjusted
across candidates. Among qualifiers the highest overall mean wins; when the top two do not differ
significantly, the preferred model wins. With no qualifier the baseline stays. Vector-only nDCG@10
is reported beside it.

    python -m app.evals.embedder_compare --baseline nomic-raw --prefer embeddinggemma \\
        nomic-raw=/out/nomic-raw.json embeddinggemma=/out/embeddinggemma.json ...
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from app.evals.stats import holm_adjust, paired_randomization_test

ALPHA = 0.05
ENGLISH_STYLES = ("lexical", "paraphrase", "fact")


def _scores(report: Mapping[str, Any], system: str, ids: Sequence[str]) -> list[float]:
    per_question = report["systems"][system]["per_question"]
    return [float(per_question[qid]["ndcg@10"]) for qid in ids]


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _test(
    reports: Mapping[str, Any], arm: str, other: str, ids: Sequence[str], system: str = "hybrid"
) -> dict[str, float]:
    a, b = _scores(reports[arm], system, ids), _scores(reports[other], system, ids)
    return {
        "mean": round(_mean(a), 4),
        "delta": round(_mean(a) - _mean(b), 4),
        "p": paired_randomization_test(a, b),
    }


def compare(
    reports: Mapping[str, Mapping[str, Any]],
    styles: Mapping[str, str],
    *,
    baseline: str,
    prefer: str | None,
) -> dict[str, Any]:
    """Apply DEC-15 to ``reports`` (arm -> report); ``styles`` maps question id -> style."""
    ids = sorted(styles)
    by_style = {s: [q for q in ids if styles[q] == s] for s in {*styles.values()}}
    candidates = [arm for arm in reports if arm != baseline]
    families: dict[str, dict[str, dict[str, float]]] = {"overall": {}, "spanish": {}}
    families.update({style: {} for style in ENGLISH_STYLES if by_style.get(style)})
    for arm in candidates:
        families["overall"][arm] = _test(reports, arm, baseline, ids)
        families["spanish"][arm] = _test(reports, arm, baseline, by_style.get("spanish", []))
        for style in ENGLISH_STYLES:
            if style in families:
                families[style][arm] = _test(reports, arm, baseline, by_style[style])
    for family in families.values():
        adjusted = holm_adjust({arm: row["p"] for arm, row in family.items()})
        for arm, row in family.items():
            row["holm_p"] = adjusted[arm]

    def better(family: str, arm: str) -> bool:
        row = families[family][arm]
        return row["delta"] > 0 and row["holm_p"] < ALPHA

    result: dict[str, Any] = {"baseline": baseline, "prefer": prefer, "candidates": {}}
    for arm in candidates:
        regressions = [
            style
            for style in ENGLISH_STYLES
            if style in families
            and families[style][arm]["delta"] < 0
            and families[style][arm]["holm_p"] < ALPHA
        ]
        result["candidates"][arm] = {
            "overall": families["overall"][arm],
            "spanish": families["spanish"][arm],
            "english": {s: families[s][arm] for s in ENGLISH_STYLES if s in families},
            "vector_overall": _test(reports, arm, baseline, ids, system="vector"),
            "regressions": regressions,
            "qualifies": better("overall", arm) and better("spanish", arm) and not regressions,
        }
    qualifying = sorted(
        (arm for arm in candidates if result["candidates"][arm]["qualifies"]),
        key=lambda arm: families["overall"][arm]["mean"],
        reverse=True,
    )
    result["qualifying"] = qualifying
    result["baseline_mean"] = round(_mean(_scores(reports[baseline], "hybrid", ids)), 4)
    winner = qualifying[0] if qualifying else baseline
    result["top_two_differ"] = None
    if len(qualifying) >= 2:
        first, second = qualifying[:2]
        p = paired_randomization_test(
            _scores(reports[first], "hybrid", ids), _scores(reports[second], "hybrid", ids)
        )
        result["top_two_differ"] = p < ALPHA
        result["top_two_p"] = p
        if not result["top_two_differ"] and prefer in (first, second):
            winner = prefer
    result["winner"] = winner
    return result


def main(argv: Sequence[str] | None = None) -> int:
    from app.evals.retrieval_eval import DEFAULT_QRELS, Qrels

    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("arms", nargs="+", help="name=path/to/evaluate-report.json")
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--prefer", default=None)
    parser.add_argument("--qrels", default=str(DEFAULT_QRELS))
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    reports = {}
    for spec in args.arms:
        name, _, path = spec.partition("=")
        reports[name] = json.loads(Path(path).read_text(encoding="utf-8"))
    styles = {q.id: q.style for q in Qrels.load(args.qrels).questions}
    result = compare(reports, styles, baseline=args.baseline, prefer=args.prefer)
    text = json.dumps(result, indent=1)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
