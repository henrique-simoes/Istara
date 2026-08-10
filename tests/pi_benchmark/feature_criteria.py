"""Feature-criteria compiler (task B0-6, master plan §10.2/§10.3, axis 2).

Compiles ``docs/features/inventory.json`` (the living feature inventory) into per-feature
*executable criteria*: for each of the six axis-2 criteria (reachable, project_scoped,
expected_action, engine_behavior, evidence_emitted, graceful_failure) it decides whether
the criterion is machine-derivable from the inventory's own signals (an API route to
reach it, a test that proves evidence, …). A feature all of whose in-scope criteria are
derivable is ``criteria: "auto"``; any feature with at least one non-derivable criterion
is ``criteria: "manual"`` — **counted and reported, never skipped** (acceptance A8).

The compiler is offline (tier T0): it emits the criteria *plan* (which criteria apply and
auto-vs-manual) with scores left ``null`` for the live T2 runner to fill in. Importing or
running it touches no backend, DB, network, or model.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

# The six axis-2 criteria, in schema order (see metrics-schema.json $defs.feature_criteria_scores).
CRITERIA: tuple[str, ...] = (
    "reachable",
    "project_scoped",
    "expected_action",
    "engine_behavior",
    "evidence_emitted",
    "graceful_failure",
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = _REPO_ROOT / "docs" / "features" / "inventory.json"


@dataclass(frozen=True)
class FeatureCriteria:
    """Compiled criteria plan for one feature."""

    feature_id: str
    # Per-criterion derivability: True == machine-derivable (auto), False == manual.
    derivable: dict[str, bool]

    @property
    def criteria(self) -> str:
        """`auto` iff every in-scope criterion is derivable, else `manual`."""
        return "auto" if all(self.derivable.values()) else "manual"

    def to_metrics_block(self) -> dict[str, Any]:
        """A schema-valid ``metrics.feature_integration`` block with scores unset (null).

        Every in-scope criterion is present with a ``null`` score (the T2 runner fills it
        in); this makes the compiled plan directly embeddable in a run record.
        """
        return {
            "feature_id": self.feature_id,
            "criteria": self.criteria,
            "criteria_scores": {name: None for name in CRITERIA},
        }


def _derivability(feature: dict[str, Any]) -> dict[str, bool]:
    """Decide which criteria are machine-derivable from a feature's inventory signals.

    Signals used (all already in the inventory):
    * ``api_refs`` — a backend route exists, so reachability, project scope, the expected
      action, engine-behavior comparison, and a graceful-failure probe are all derivable.
    * ``test_refs`` — a test already proves the feature emits evidence.
    A pure-UI/shell feature with no ``api_refs`` has no route-level probe, so those
    criteria are manual; a feature with no ``test_refs`` has manual evidence.
    """
    has_api = bool(feature.get("api_refs"))
    has_test = bool(feature.get("test_refs"))
    return {
        "reachable": has_api,
        "project_scoped": has_api,
        "expected_action": has_api,
        "engine_behavior": has_api,
        "evidence_emitted": has_test,
        "graceful_failure": has_api,
    }


@lru_cache(maxsize=1)
def _inventory() -> dict[str, Any]:
    with INVENTORY_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def compile_features(inventory: dict[str, Any] | None = None) -> list[FeatureCriteria]:
    """Compile every feature in the inventory into a :class:`FeatureCriteria` plan.

    Exactly one entry per inventory feature — no feature is dropped, so the axis-2 matrix
    denominator equals the inventory count (acceptance A8).
    """
    data = inventory if inventory is not None else _inventory()
    features = data.get("features") or []
    compiled: list[FeatureCriteria] = []
    seen: set[str] = set()
    for feature in features:
        feature_id = str(feature.get("id") or "").strip()
        if not feature_id or feature_id in seen:
            continue
        seen.add(feature_id)
        compiled.append(FeatureCriteria(feature_id=feature_id, derivable=_derivability(feature)))
    return compiled


def coverage_summary(compiled: list[FeatureCriteria] | None = None) -> dict[str, int]:
    """Roll-up of the compiled matrix: total, auto, manual (all counted, none skipped)."""
    compiled = compiled if compiled is not None else compile_features()
    auto = sum(1 for c in compiled if c.criteria == "auto")
    return {"total": len(compiled), "auto": auto, "manual": len(compiled) - auto}
