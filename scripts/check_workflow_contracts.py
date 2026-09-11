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
  6. (F-6 regression, W4 M-13 form) ci.yml contains NO `git push` at all:
     every CI job is read-only, so CI can never push a generated commit to
     `testing` (or any other branch). The README version-badge writeback
     lives in its own narrow workflow, `badge-sync.yml`, which must trigger
     only on `main` (the release branch), never on `testing`/`staging`, so
     `testing` HEAD stays a stable, reproducible source for the exact-SHA
     human promotion gate and the no-direct-push contract.
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


_JOB_ID_RE = re.compile(r"^  ([a-zA-Z0-9_-]+):\s*$", re.MULTILINE)


def job_section(text: str, job: str) -> str:
    """Return the text of one top-level workflow job ("" when absent)."""
    match = re.search(rf"^  {re.escape(job)}:\s*$", text, re.MULTILINE)
    if not match:
        return ""
    rest = text[match.end():]
    next_job = _JOB_ID_RE.search(rest)
    return rest[: next_job.start()] if next_job else rest


def installs_npm_ci(section: str, surface: str) -> bool:
    """True when one step in a job section runs ``npm ci`` in ``surface``.

    Steps are split on the workflow's six-space ``- `` step marker; the
    ``working-directory`` and ``run`` legs must live in the same step, because
    a directory set in one step does not carry into another (F-CI-R1-2: the
    install must be in the job that runs the suite, not merely somewhere in
    the workflow).
    """
    for step in re.split(r"^      - ", section, flags=re.MULTILINE)[1:]:
        if re.search(
            rf"working-directory:\s*{re.escape(surface)}\s*$", step, re.MULTILINE
        ) and "npm ci" in step:
            return True
    return False


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
    # F-6 regression contract, W4 M-13 form: no CI job writes to any branch.
    # The `governance` job is a REQUIRED check and must be read-only
    # (`contents: read`); the README badge writeback lives in badge-sync.yml.
    if "git push" in ci:
        issues.append(
            "ci.yml: no CI job may push to any branch (M-13: governance is a "
            "required check and must be read-only; badge sync lives in "
            "badge-sync.yml)"
        )
    if not re.search(r"^  release-gate:\s*$", ci, re.MULTILINE):
        issues.append(
            "ci.yml: missing the fail-closed `release-gate` aggregator job "
            "(fails on failure, cancellation, and unexplained skip)"
        )
    if "python scripts/check_required_checks.py" not in ci:
        issues.append(
            "ci.yml: missing the required-checks manifest contract check (M-20)"
        )
    if re.search(r"git push\b[^\n]*\btesting\b", ci):
        issues.append(
            "ci.yml: no CI step may push a generated commit to `testing` "
            "(no-direct-push / reproducible-source contract)"
        )
    # F-CI-R1-2 regression contract: `backend-test` runs the full backend
    # suite, which includes the pi lockstep diff-proof acceptance
    # (tests/pi_compat/test_bump_diff_proof.py
    # ::test_verify_accepts_current_repository_state).
    # `scripts/pi_bump_diff_proof.py verify` fails closed when either bundled
    # surface — pi-runtime or labs/pi-replacement — has no installed
    # @earendil-works packages, so the job must `npm ci` BOTH surfaces before
    # the suite. Installing only pi-runtime left the full-suite step red on a
    # surface-not-built gate failure; the gate is never weakened or skipped.
    backend_test = job_section(ci, "backend-test")
    for surface in ("pi-runtime", "labs/pi-replacement"):
        if not installs_npm_ci(backend_test, surface):
            issues.append(
                f"ci.yml: backend-test must `npm ci` {surface} before the "
                "full-suite step — the pi lockstep diff-proof gate fails "
                "closed when either bundled surface is unbuilt (F-CI-R1-2)"
            )


def check_badge_sync(issues: list[str], root: Path = ROOT) -> None:
    """Badge-sync is the ONLY CI-generated write path — narrow and main-only."""
    badge = read("badge-sync.yml", root=root)
    if "branches: [main]" not in badge:
        issues.append(
            "badge-sync.yml: must trigger on push to `main` only "
            "(branches: [main]) — the promotion source `testing` must stay "
            "reproducible (no-direct-push / F-6 contract)"
        )
    if re.search(r"branches:\s*\[[^\]]*\btesting\b", badge) or re.search(
        r"branches:\s*\[[^\]]*\bstaging\b", badge
    ):
        issues.append(
            "badge-sync.yml: must never trigger on `testing`/`staging` — the "
            "promotion source must stay reproducible (no-direct-push contract)"
        )
    if re.search(r"git push\b[^\n]*\btesting\b", badge):
        issues.append("badge-sync.yml: the writeback must never push to `testing`")
    if "git push origin HEAD:main" not in badge:
        issues.append("badge-sync.yml: badge writeback must push only to `main`")
    if "contents: write" not in badge:
        issues.append(
            "badge-sync.yml: must declare the narrow `contents: write` permission"
        )
    if "[skip ci]" not in badge:
        issues.append(
            "badge-sync.yml: the generated commit must carry `[skip ci]` so it "
            "does not retrigger the full CI graph"
        )
    if "github.ref_name == 'main'" not in badge:
        issues.append(
            "badge-sync.yml: the writeback step must be gated to the release "
            "branch (`if: github.event_name == 'push' && github.ref_name == 'main'`)"
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
    for name in ("ci.yml", "badge-sync.yml", "qa-artifact.yml", "promote-testing.yml"):
        if not (WORKFLOWS / name).exists():
            issues.append(f"missing workflow: {name}")
    if not issues:
        try:
            check_ci(issues)
            check_badge_sync(issues)
            check_qa_artifact(issues)
            check_promote(issues)
        except FileNotFoundError as exc:
            issues.append(str(exc))

    for name in ("ci.yml", "badge-sync.yml", "qa-artifact.yml", "promote-testing.yml"):
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
