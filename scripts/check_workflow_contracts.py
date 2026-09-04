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
  6. (F-6 regression) ci.yml's governance badge-sync writeback is restricted
     to the release branch `main`: CI never pushes a generated commit to
     `testing` (or any other triggering branch), so `testing` HEAD stays a
     stable, reproducible source for the exact-SHA human promotion gate and
     the no-direct-push contract.
  7. (F-5-r2 regression) promote-testing.yml's fail-closed required-checks
     step lists Actions runs via `gh api .../actions/runs`, which requires the
     Actions read scope on the workflow token; the explicit `permissions`
     block must therefore bind `actions: read`, or a normal runner 403s and
     the only promotion path can never reach PR creation.
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


def read(name: str, root: Path = ROOT) -> str:
    path = root / ".github" / "workflows" / name
    if not path.exists():
        raise FileNotFoundError(f"missing workflow: {name}")
    return path.read_text(encoding="utf-8")


def check_ci(issues: list[str], root: Path = ROOT) -> None:
    ci = read("ci.yml", root=root)
    if not re.search(r"branches:\s*\[[^\]]*\btesting\b", ci):
        issues.append("ci.yml: must trigger on the `testing` integration branch")
    if "check_feature_obligations.py" not in ci:
        issues.append("ci.yml: missing feature-obligation classifier job/step")
    if "check_qa_capabilities.py" not in ci:
        issues.append("ci.yml: missing QA capabilities check")
    if "istara-security-scorecard" not in ci:
        issues.append("ci.yml: missing security scorecard artifact upload")
    # F-6 regression contract: CI-generated badge-sync writebacks are restricted
    # to the release branch (`main`). A writeback that follows the triggering
    # branch (`${{ github.ref_name }}`) would push a generated commit to
    # `testing` during/after QA evidence, move HEAD, and invalidate the
    # exact-SHA human promotion gate.
    if re.search(r"git push\s+origin\s+HEAD:\$\{\{\s*github\.ref_name\s*\}\}", ci):
        issues.append(
            "ci.yml: badge-sync writeback pushes to the triggering branch "
            "(`${{ github.ref_name }}`); on `testing` this would mutate the "
            "promotion source — the writeback must target `main`"
        )
    if "github.ref_name == 'main'" not in ci:
        issues.append(
            "ci.yml: badge-sync writeback must be gated to the release branch "
            "(`if: github.event_name == 'push' && github.ref_name == 'main'`)"
        )
    if re.search(r"git push\b[^\n]*\btesting\b", ci):
        issues.append(
            "ci.yml: no CI step may push a generated commit to `testing` "
            "(no-direct-push / reproducible-source contract)"
        )


def check_qa_artifact(issues: list[str], root: Path = ROOT) -> None:
    qa = read("qa-artifact.yml", root=root)
    if "testing" not in qa:
        issues.append("qa-artifact.yml: must trigger on the `testing` branch")
    if "docker" not in qa.lower():
        issues.append("qa-artifact.yml: must build a disposable Docker QA artifact")
    if "digest" not in qa.lower() or (
        "sha256" not in qa.lower() and "image_digest" not in qa.lower()
    ):
        issues.append("qa-artifact.yml: manifest must record an immutable image digest")
    if "actions/upload-artifact" not in qa:
        issues.append("qa-artifact.yml: must upload sanitized QA evidence artifacts")
    if "if: failure()" in qa and "continue-on-error" in qa:
        issues.append("qa-artifact.yml: failed runs must not publish a green manifest")


def check_promote(issues: list[str], root: Path = ROOT) -> None:
    promo = read("promote-testing.yml", root=root)
    if "workflow_dispatch" not in promo:
        issues.append("promote-testing.yml: must be manual dispatch (no auto-trigger)")
    if "environment" not in promo:
        issues.append(
            "promote-testing.yml: missing protected environment (human approval gate)"
        )
    if "gh pr create" not in promo:
        issues.append("promote-testing.yml: must create the promotion PR via gh")
    if "gh pr merge" in promo or "--auto" in promo:
        issues.append("promote-testing.yml: must never auto-merge")
    if "source_sha" not in promo:
        issues.append(
            "promote-testing.yml: must bind the exact source SHA (anti-replay)"
        )
    if "fail" not in promo.lower() and "exit 1" not in promo:
        issues.append("promote-testing.yml: changed-SHA replay must fail closed")
    # F-5-r2 regression contract: the required-checks step calls
    # `gh api .../actions/runs` and must exist (anchor), and the explicit
    # `permissions` block must bind the Actions read scope. `actions: write`
    # implies read and is accepted; without any `actions` scope the workflow
    # token cannot list runs and the fail-closed check 403s on a normal runner.
    if "actions/runs" not in promo:
        issues.append(
            "promote-testing.yml: missing the required-checks "
            "`gh api .../actions/runs` verification step"
        )
    perm = re.search(r"^permissions:\s*\n((?:[ \t]+[^\n]*\n)+)", promo, re.MULTILINE)
    if not perm or not re.search(r"[ \t]+actions:\s*(read|write)\b", perm.group(1)):
        issues.append(
            "promote-testing.yml: must bind `actions: read` (the required-checks "
            "step lists Actions runs via `gh api .../actions/runs`, which needs "
            "the Actions read scope on the workflow token)"
        )


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
