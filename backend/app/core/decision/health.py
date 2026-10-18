"""Error structure across evaluators on human-labelled items (pure; research doc section 7)."""

from __future__ import annotations

from itertools import combinations
from typing import Any

from app.core.decision.ensemble import dawid_skene, effective_evaluators, error_correlation, yules_q

MIN_SHARED_ITEMS = 10


def error_structure(verdicts: dict[str, dict[str, int]], labels: dict[str, int]) -> dict[str, Any]:
    """Pairwise error correlation and Yule's Q, J_eff and Dawid-Skene on labelled items."""
    names = sorted(verdicts)
    pairs = []
    correlations = []
    for a, b in combinations(names, 2):
        shared = sorted(set(verdicts[a]) & set(verdicts[b]) & set(labels))
        if len(shared) < MIN_SHARED_ITEMS:
            continue
        errors_a = [verdicts[a][s] != labels[s] for s in shared]
        errors_b = [verdicts[b][s] != labels[s] for s in shared]
        rho = error_correlation(errors_a, errors_b)
        q = yules_q([not e for e in errors_a], [not e for e in errors_b])
        pairs.append({"a": a, "b": b, "n": len(shared), "error_correlation": rho, "yules_q": q})
        if rho is not None:
            correlations.append(rho)
    accuracy = {
        name: sum(verdicts[name][s] == labels[s] for s in verdicts[name] if s in labels)
        / max(1, sum(1 for s in verdicts[name] if s in labels))
        for name in names
    }
    report: dict[str, Any] = {
        "evaluators": names,
        "labelled_items": len(labels),
        "accuracy_vs_human": accuracy,
        "pairs": pairs,
        "mean_error_correlation": sum(correlations) / len(correlations) if correlations else None,
        "effective_evaluators": (
            effective_evaluators(len(names), sum(correlations) / len(correlations))
            if correlations
            else None
        ),
        "dawid_skene": None,
    }
    if len(names) >= 3 and labels:
        items = [{name: verdicts[name][s] for name in names if s in verdicts[name]} for s in labels]
        result = dawid_skene([item for item in items if item], classes=2)
        report["dawid_skene"] = {
            "panel_size": len(names),
            "converged": result.converged,
            "confusion": result.confusion,
            "note": "three binary evaluators are barely identifiable; read with the panel size",
        }
    return report
