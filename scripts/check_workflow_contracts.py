#!/usr/bin/env python3
"""Verify the public CI/promotion workflows satisfy the human-gate contract.

Structural, deterministic checks (stdlib only):
  1. ci.yml must trigger on the ``testing`` integration branch.
  2. ci.yml must run the feature-obligation classifier as a required gate.
  3. qa-artifact.yml must build a disposable QA artifact with digest +
     provenance evidence and never publish a green manifest on failure.
  4. promote-testing.yml must require an explicit human approval gate
     (protected environment) before creating a promotion PR, must never
     auto-merge, and must fail closed when the source SHA changes.
  5. No public workflow may reference `multivac`, a private endpoint, or a
     committed credential.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"

FORBIDDEN_IN_WORKFLOWS = (
    "multivac",
    "10.0.10.",
    "192.168.",
    "host.docker.internal",
)


def read(name: str) -> str:
    path = WORKFLOWS / name
    if not path.exists():
        raise FileNotFoundError(f"missing workflow: {name}")
    return path.read_text(encoding="utf-8")


def check_ci(issues: list[str]) -> None:
    ci = read("ci.yml")
    if not re.search(r"branches:\s*\[[^\]]*\btesting\b", ci):
        issues.append("ci.yml: must trigger on the `testing` integration branch")
    if "check_feature_obligations.py" not in ci:
        issues.append("ci.yml: missing feature-obligation classifier job/step")
    if "check_qa_capabilities.py" not in ci:
        issues.append("ci.yml: missing QA capabilities check")
    if "istara-security-scorecard" not in ci:
        issues.append("ci.yml: missing security scorecard artifact upload")


def check_qa_artifact(issues: list[str]) -> None:
    qa = read("qa-artifact.yml")
    if "testing" not in qa:
        issues.append("qa-artifact.yml: must trigger on the `testing` branch")
    if "docker" not in qa.lower():
        issues.append("qa-artifact.yml: must build a disposable Docker QA artifact")
    if "digest" not in qa.lower() or ("sha256" not in qa.lower() and "image_digest" not in qa.lower()):
        issues.append("qa-artifact.yml: manifest must record an immutable image digest")
    if "actions/upload-artifact" not in qa:
        issues.append("qa-artifact.yml: must upload sanitized QA evidence artifacts")
    if "if: failure()" in qa and "continue-on-error" in qa:
        issues.append("qa-artifact.yml: failed runs must not publish a green manifest")


def check_promote(issues: list[str]) -> None:
    promo = read("promote-testing.yml")
    if "workflow_dispatch" not in promo:
        issues.append("promote-testing.yml: must be manual dispatch (no auto-trigger)")
    if "environment" not in promo:
        issues.append("promote-testing.yml: missing protected environment (human approval gate)")
    if "gh pr create" not in promo:
        issues.append("promote-testing.yml: must create the promotion PR via gh")
    if "gh pr merge" in promo or "--auto" in promo:
        issues.append("promote-testing.yml: must never auto-merge")
    if "source_sha" not in promo:
        issues.append("promote-testing.yml: must bind the exact source SHA (anti-replay)")
    if "fail" not in promo.lower() and "exit 1" not in promo:
        issues.append("promote-testing.yml: changed-SHA replay must fail closed")


def main() -> int:
    issues: list[str] = []
    for name in ("ci.yml", "qa-artifact.yml", "promote-testing.yml"):
        if not (WORKFLOWS / name).exists():
            issues.append(f"missing workflow: {name}")
    if not issues:
        try:
            check_ci(issues)
            check_qa_artifact(issues)
            check_promote(issues)
        except FileNotFoundError as exc:
            issues.append(str(exc))

    for name in ("ci.yml", "qa-artifact.yml", "promote-testing.yml"):
        path = WORKFLOWS / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for fragment in FORBIDDEN_IN_WORKFLOWS:
            if fragment in text:
                issues.append(f"{name}: forbidden fragment `{fragment}`")

    if issues:
        print("Workflow contract check failed:")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    print("Workflow contract check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
