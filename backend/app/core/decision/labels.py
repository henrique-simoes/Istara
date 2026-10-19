"""Human labels for decider calibration, from reconciliation decisions.

Only a researcher's own review counts. Synthetic benchmark reconciliation, debate and adversarial
review are model or test outputs, and a decider calibrated on them would be grading itself
against machines (research doc section 6).

Mapping v1 is binary: it says whether the item a decider judged turned out acceptable to the
researcher. The review UI records accept / reject / revise only, so v1 cannot recover the
four-way class (grounded evidence, speculative inference, factual hallucination, methodological
violation); that needs a richer review control and a v2 mapping. A mapping change starts new trust
scopes, so history is never silently relabelled.
"""

from __future__ import annotations

LABEL_MAPPING_VERSION = "v1"
HUMAN_REVIEW_SOURCE = "human_review"
_V1_LABELS = {"accepted": 1, "rejected": 0, "revised": 0}


def label_from_reconciliation(decision_type: str, source: str) -> int | None:
    """1 when the researcher accepted the item, 0 when they rejected or revised it, else None.

    ``needs_human_review`` and every non-human source give no label.
    """
    if (source or "").strip().lower() != HUMAN_REVIEW_SOURCE:
        return None
    return _V1_LABELS.get((decision_type or "").strip().lower())


def positive_probability(distribution: dict[str, float], positive: frozenset[str]) -> float:
    """Probability mass the decider put on the outcomes that mean "acceptable"."""
    if not distribution:
        raise ValueError("distribution must not be empty")
    unknown = positive - set(distribution)
    if unknown:
        raise ValueError("positive outcomes not in the distribution: " + ", ".join(sorted(unknown)))
    return sum(p for name, p in distribution.items() if name in positive)
