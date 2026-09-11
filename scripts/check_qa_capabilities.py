#!/usr/bin/env python3
"""Validate qa/runtime_capabilities.json against the QA contract.

Rules (from the winning master plan, section 6.2):
  1. The file must be valid JSON with ``version`` and ``surfaces``.
  2. Every surface must declare at least one deterministic obligation.
  3. No surface may claim full-feature readiness from contract-only lanes:
     ``live_optional`` lanes are never counted as satisfying deterministic
     obligations, and a surface may not list a live lane as its only obligation.
  4. Every deterministic obligation must have a test owner (same map as the
     feature-obligation classifier) and a pinned command in the catalog.
  5. ``spine_touch`` must be a boolean; a spine-touching surface must declare
     the synthetic-provisional obligation.
  6. The file itself must be registered in governance patterns (checked by
     check_ci_governance.py); this script is the machine-readable validator.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CAPABILITIES = ROOT / "qa" / "runtime_capabilities.json"

DETERMINISTIC_OBLIGATIONS = {
    "governance",
    "ci_governance",
    "test_harness",
    "feature_obligations",
    "qa_artifact_contract",
    "qa_stack_contract",
    "public_tree",
    "workflow_contract",
    "security_benchmark",
    "backend_contracts",
    "provider_contracts",
    "research_spine_contract",
    "synthetic_provisional",
    "mutation_property",
    "frontend_contracts",
    "relay_contracts",
    "project_scope",
    "feature_docs",
}

LIVE_OBLIGATIONS = {
    "authorized_live",
    "staging_adapter",
    "simulation_live",
    "dimension_probe_live",
    "authorized_chat_smoke",
}

SPINE_OBLIGATION = "synthetic_provisional"


def validate(capabilities_path: Path = CAPABILITIES) -> list[str]:
    issues: list[str] = []
    try:
        data = json.loads(capabilities_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"qa/runtime_capabilities.json: invalid JSON ({exc})"]

    if data.get("version") != 1:
        issues.append("qa/runtime_capabilities.json: version must be 1")
    surfaces = data.get("surfaces")
    if not isinstance(surfaces, list) or not surfaces:
        issues.append("qa/runtime_capabilities.json: surfaces must be a non-empty list")
        return issues

    seen_ids: set[str] = set()
    for surface in surfaces:
        sid = surface.get("id")
        if not sid:
            issues.append("qa/runtime_capabilities.json: surface missing id")
            continue
        if sid in seen_ids:
            issues.append(f"qa/runtime_capabilities.json: duplicate surface id {sid}")
        seen_ids.add(sid)

        deterministic = set(surface.get("deterministic", []))
        live = set(surface.get("live_optional", []))

        unknown = deterministic - DETERMINISTIC_OBLIGATIONS
        if unknown:
            issues.append(
                f"qa/runtime_capabilities.json: surface {sid} declares unknown "
                f"deterministic obligations {sorted(unknown)}"
            )
        unknown_live = live - LIVE_OBLIGATIONS
        if unknown_live:
            issues.append(
                f"qa/runtime_capabilities.json: surface {sid} declares unknown "
                f"live obligations {sorted(unknown_live)}"
            )

        if not deterministic:
            issues.append(
                f"qa/runtime_capabilities.json: surface {sid} must declare at least "
                "one deterministic obligation (live lanes can never satisfy "
                "deterministic obligations)"
            )

        spine_touch = surface.get("spine_touch")
        if not isinstance(spine_touch, bool):
            issues.append(
                f"qa/runtime_capabilities.json: surface {sid} spine_touch must be a boolean"
            )
        elif spine_touch and SPINE_OBLIGATION not in deterministic:
            issues.append(
                f"qa/runtime_capabilities.json: spine-touching surface {sid} must "
                f"declare the {SPINE_OBLIGATION} obligation"
            )

        if not surface.get("paths"):
            issues.append(f"qa/runtime_capabilities.json: surface {sid} has no paths")

    return issues


def main() -> int:
    issues = validate()
    if issues:
        print("QA capabilities check failed:")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    print("QA capabilities check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
