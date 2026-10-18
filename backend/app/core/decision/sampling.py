"""Blind random audit sampling and trust-scope keys.

Humans review what a decider routes to them, plus a random share of what it did not route (rate
rho, owner decision DEC-4: 10%). The draw is a deterministic hash of the item, independent of the
decider's answer, so it is reproducible and cannot be steered by the model. Each labelled item
carries its inclusion probability so calibration can be re-weighted (Horvitz-Thompson); without the
audit, labels would come only from uncertain items and calibration would be biased.
"""

from __future__ import annotations

import hashlib
import json

AUDIT_RATE = 0.10
_HASH_SPACE = float(2**64)


def audit_draw(
    project_id: str, subject_id: str, rate: float, salt: str = "decider-audit-v1"
) -> tuple[bool, float]:
    """``(sampled, propensity)``: whether the item joins the audit, and the rate it was drawn at."""
    if not 0.0 < rate <= 1.0:
        raise ValueError("rate must lie in (0, 1]")
    digest = hashlib.sha256(f"{salt}\x1f{project_id}\x1f{subject_id}".encode()).digest()
    uniform = int.from_bytes(digest[:8], "big") / _HASH_SPACE
    return uniform < rate, rate


def inclusion_weight(routed: bool, audit_sampled: bool, rate: float) -> float | None:
    """Horvitz-Thompson weight for a labelled item; None when the item could not be labelled.

    Routed items always reach a human (probability 1). Non-routed items reach one only through
    the audit (probability ``rate``).
    """
    if routed:
        return 1.0
    if audit_sampled:
        return 1.0 / rate
    return None


def scope_key(
    *,
    project_id: str,
    provider: str,
    served_model: str,
    question_set_id: str,
    question_set_version: str,
    task_family: str,
    language: str,
    label_mapping_version: str,
) -> str:
    """Stable id of a trust scope.

    Any change of project, model version, questions, task, language or label mapping is a new
    scope that must earn trust again. Scopes are project-scoped: one project's reviews never earn a
    decider routing power in another (self-improvement governance contract).
    """
    parts = {
        "project_id": project_id,
        "provider": provider,
        "served_model": served_model.strip().casefold(),
        "question_set_id": question_set_id,
        "question_set_version": question_set_version,
        "task_family": task_family,
        "language": language.strip().casefold(),
        "label_mapping_version": label_mapping_version,
    }
    if any(not value for value in parts.values()):
        raise ValueError("every scope field is required")
    canonical = json.dumps(parts, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()[:32]
