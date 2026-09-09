#!/usr/bin/env python3
"""Verify the required-checks manifest matches the CI workflow job graph (M-20).

Stdlib only (no PyYAML dependency — the governance job installs no packages),
matching the conventions of ``scripts/check_ci_governance.py`` and
``scripts/check_feature_obligations.py``.

The manifest ``testing/required-checks.json`` is the single source consumed
verbatim by the owner-gated main branch-protection change (M-07). This checker
keeps the three layers honest and in lockstep:

  1. every manifest required context is a real job in ``ci.yml``;
  2. every job in ``ci.yml`` is either required or an explicitly conditional
     context — renaming a job fails until the manifest is updated (M-20);
  3. the ``release-gate`` aggregator needs EXACTLY the required contexts and
     runs ``if: always()`` — it fails closed on failure, cancellation, and
     unexplained skip (D.1/D.9);
  4. the independence rule holds: no job may ``needs:`` a job whose failure
     is not a true precondition. The only retained non-aggregator edge is
     ``ui-journeys -> qa-contract-render`` (a stack that does not render
     cannot start); no quality gate gates another quality gate (M-06);
  5. no required job carries a job-level ``continue-on-error`` — a check that
     cannot fail for its stated reason is a defect, not coverage (D.9).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "testing" / "required-checks.json"
WORKFLOW = ".github/workflows/ci.yml"

# The only retained non-aggregator needs edge (master plan D.1).
ALLOWED_NEEDS_EDGES: dict[str, set[str]] = {
    "ui-journeys": {"qa-contract-render"},
}

JOB_ID_RE = re.compile(r"^  ([a-zA-Z0-9_-]+):\s*$")
FLOW_LIST_RE = re.compile(r"^\s*needs:\s*\[([^\]]*)\]\s*$")


def parse_jobs(text: str) -> dict[str, dict[str, object]]:
    """Parse top-level job ids with their needs/if/continue-on-error.

    Understands the YAML subset the workflow is constrained to: job ids at
    two-space indent under a top-level ``jobs:`` key, and job-level
    ``needs:``/``if:``/``continue-on-error:`` at four-space indent (block or
    flow lists). Locked by ``tests/test_required_checks.py``.
    """
    jobs: dict[str, dict[str, object]] = {}
    in_jobs = False
    current: str | None = None
    collecting_needs = False
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent == 0:
            in_jobs = line.strip() == "jobs:"
            current = None
            collecting_needs = False
            continue
        if not in_jobs:
            continue
        job_match = JOB_ID_RE.match(line)
        if job_match:
            current = job_match.group(1)
            jobs[current] = {"needs": [], "if": "", "continue_on_error": False}
            collecting_needs = False
            continue
        if current is None:
            continue
        stripped = line.strip()
        # Job-level attributes live at exactly four-space indent; anything
        # deeper belongs to steps and must not bleed into the job record
        # (step-level `if:`/`continue-on-error:` are explicitly allowed).
        if indent == 4:
            collecting_needs = False
            flow = FLOW_LIST_RE.match(line)
            if flow:
                jobs[current]["needs"] = [
                    item.strip().strip("'\"")
                    for item in flow.group(1).split(",")
                    if item.strip()
                ]
            elif stripped.startswith("needs:"):
                collecting_needs = True
            elif stripped.startswith("if:"):
                jobs[current]["if"] = stripped[3:].strip()
            elif stripped.startswith("continue-on-error:"):
                value = stripped.split(":", 1)[1].strip().lower()
                jobs[current]["continue_on_error"] = value == "true"
        elif indent > 4 and collecting_needs and stripped.startswith("- "):
            jobs[current]["needs"].append(stripped[2:].strip().strip("'\""))
        elif indent > 4 and collecting_needs and not stripped.startswith("- "):
            collecting_needs = False
    return jobs


def load_manifest(root: Path = ROOT) -> dict:
    path = root / "testing" / "required-checks.json"
    if not path.exists():
        raise FileNotFoundError(f"missing required-checks manifest: {path}")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("version") != 1:
        raise ValueError("testing/required-checks.json: unsupported manifest version")
    return manifest


def check_required_checks(issues: list[str], root: Path = ROOT) -> None:
    try:
        manifest = load_manifest(root)
    except FileNotFoundError as exc:
        issues.append(str(exc))
        return
    except (ValueError, json.JSONDecodeError) as exc:
        issues.append(f"required-checks.json: invalid manifest ({exc})")
        return
    workflow_path = root / ".github" / "workflows" / "ci.yml"
    if not workflow_path.exists():
        issues.append(f"{WORKFLOW}: missing workflow file")
        return
    jobs = parse_jobs(workflow_path.read_text(encoding="utf-8"))
    if not jobs:
        issues.append(f"{WORKFLOW}: could not parse any jobs")
        return

    required: list[str] = manifest.get("required_contexts", [])
    conditional: dict[str, dict] = manifest.get("conditional_contexts", {})

    if not required:
        issues.append("required-checks.json: required_contexts must not be empty")
    if len(set(required)) != len(required):
        issues.append("required-checks.json: required_contexts contains duplicates")

    # 1. Every required context is a real job.
    for context in required:
        if context not in jobs:
            issues.append(
                f"required-checks.json: required context `{context}` is not a job in {WORKFLOW}"
            )

    # 2. Every job is required or explicitly conditional (rename rot, M-20).
    for job in jobs:
        if job not in required and job not in conditional:
            issues.append(
                f"{WORKFLOW}: job `{job}` is not listed in required-checks.json "
                "(required_contexts or conditional_contexts) — update the manifest "
                "in the same change as the workflow"
            )

    # Conditional contexts must be genuinely conditional.
    for name, meta in conditional.items():
        if not isinstance(meta, dict) or not meta.get("reason"):
            issues.append(
                f"required-checks.json: conditional context `{name}` needs a reason"
            )
        if name in required:
            issues.append(
                f"required-checks.json: `{name}` is listed both required and conditional"
            )
        if name not in jobs:
            issues.append(
                f"required-checks.json: conditional context `{name}` is not a job in {WORKFLOW}"
            )

    # 3. The release-gate aggregator needs exactly the required contexts.
    if "release-gate" not in jobs:
        issues.append(f"{WORKFLOW}: missing `release-gate` fail-closed aggregator")
    else:
        gate = jobs["release-gate"]
        gate_needs = set(gate["needs"])  # type: ignore[arg-type]
        # The aggregator cannot need itself: the `release-gate` context is
        # required at the branch-protection boundary (its own status is what
        # gates the merge), but its needs list covers the other required
        # contexts only.
        expected_gate_needs = set(required) - {"release-gate"}
        if gate_needs != expected_gate_needs:
            missing = sorted(expected_gate_needs - gate_needs)
            extra = sorted(gate_needs - expected_gate_needs)
            if missing:
                issues.append(
                    f"release-gate: needs is missing required contexts {missing}"
                )
            if extra:
                issues.append(
                    f"release-gate: needs lists non-required contexts {extra} "
                    "(conditional contexts must not gate the aggregator)"
                )
        if "always()" not in str(gate.get("if", "")):
            issues.append(
                "release-gate: must run `if: always()` so it fails closed on "
                "failure, cancellation, and unexplained skip"
            )
        if gate.get("continue_on_error"):
            issues.append("release-gate: must not set continue-on-error")

    # 4. Independence rule (M-06): only allowed needs edges survive.
    for job, meta in jobs.items():
        needs = set(meta["needs"])  # type: ignore[arg-type]
        if job == "release-gate":
            continue
        allowed = ALLOWED_NEEDS_EDGES.get(job, set())
        unexpected = needs - allowed
        if unexpected:
            issues.append(
                f"{WORKFLOW}: job `{job}` needs {sorted(unexpected)} — no job may "
                "needs: a job whose failure is not a true precondition; the only "
                "retained non-aggregator edge is ui-journeys -> qa-contract-render"
            )

    # 5. No job-level continue-on-error anywhere in the required graph.
    for job, meta in jobs.items():
        if meta.get("continue_on_error"):
            issues.append(
                f"{WORKFLOW}: job `{job}` sets job-level continue-on-error — a "
                "check that cannot fail for its stated reason is a defect, not "
                "coverage (step-level advisory exemptions are allowed)"
            )


def main() -> int:
    issues: list[str] = []
    try:
        check_required_checks(issues)
    except FileNotFoundError as exc:
        issues.append(str(exc))
    except (ValueError, json.JSONDecodeError) as exc:
        issues.append(f"required-checks.json: invalid manifest ({exc})")

    if issues:
        print("Required-checks contract failed:")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    print(
        "Required-checks contract passed: "
        f"{len(load_manifest()['required_contexts'])} required contexts, "
        "release-gate aggregator, and job graph are in lockstep."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
