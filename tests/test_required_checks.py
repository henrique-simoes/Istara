"""Required-checks contract tests (scripts/check_required_checks.py, M-20).

Locks the three layers in lockstep: the committed manifest
(``testing/required-checks.json``), the ``ci.yml`` job graph, and the
fail-closed ``release-gate`` aggregator. Also locks the stdlib job-graph
parser (indent-aware: step-level ``if:``/``continue-on-error:`` must never
bleed into job-level records) and the M-06 independence rule.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from scripts.check_required_checks import (
    ROOT,
    check_required_checks,
    load_manifest,
    main,
    parse_jobs,
)

REAL_CI = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")


def _write_project(tmp_path: Path, manifest: dict, ci: str) -> Path:
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / "testing").mkdir(parents=True)
    (tmp_path / "testing" / "required-checks.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text(ci, encoding="utf-8")
    return tmp_path


def _real_manifest() -> dict:
    return json.loads((ROOT / "testing" / "required-checks.json").read_text("utf-8"))


def _minimal_ci(jobs: dict[str, list[str] | None]) -> str:
    lines = ["name: CI", "on: [push]", "", "jobs:"]
    for job, needs in jobs.items():
        lines.append(f"  {job}:")
        lines.append("    runs-on: ubuntu-latest")
        if job == "release-gate":
            lines.append("    if: always()")
        if needs:
            lines.append("    needs:")
            lines.extend(f"      - {n}" for n in needs)
        lines.append("    steps:")
        lines.append("      - run: echo hi")
        lines.append("")
    return "\n".join(lines)


# ── Real repository state ────────────────────────────────────────────────────


def test_real_manifest_matches_real_workflow():
    issues: list[str] = []
    check_required_checks(issues)
    assert issues == []


def test_real_manifest_has_expected_required_contexts():
    manifest = _real_manifest()
    assert manifest["required_contexts"][0] == "hygiene"
    assert "release-gate" in manifest["required_contexts"]
    # Every required context must carry a recorded reason (reviewability).
    for context in manifest["required_contexts"]:
        assert context in manifest["required_context_reasons"]


def test_real_manifest_desktop_is_conditional_not_required():
    manifest = _real_manifest()
    assert "desktop-check" not in manifest["required_contexts"]
    conditional = manifest["conditional_contexts"]["desktop-check"]
    assert conditional["required"] is False
    assert "owner" in conditional["reason"].lower()


def test_cli_exit_zero_on_real_repo():
    assert main() == 0


# ── Parser locks ────────────────────────────────────────────────────────────


def test_parser_captures_block_and_flow_needs():
    ci = _minimal_ci(
        {
            "render": None,
            "journeys": ["render"],
            "release-gate": ["render", "journeys"],
        }
    )
    jobs = parse_jobs(ci)
    assert jobs["journeys"]["needs"] == ["render"]
    assert jobs["release-gate"]["needs"] == ["render", "journeys"]
    assert jobs["release-gate"]["if"] == "always()"


def test_parser_ignores_step_level_attributes():
    ci = _minimal_ci({"advisory": None}) + (
        "  advisory:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - name: advisory step\n"
        "        if: always()\n"
        "        continue-on-error: true\n"
        "        run: echo advisory\n"
    )
    jobs = parse_jobs(ci)
    assert jobs["advisory"]["continue_on_error"] is False
    assert jobs["advisory"]["if"] == ""


def test_real_ci_parses_seventeen_jobs_with_single_retained_edge():
    jobs = parse_jobs(REAL_CI)
    assert len(jobs) == 17
    edges = {job: set(meta["needs"]) for job, meta in jobs.items() if meta["needs"]}
    assert edges == {
        "ui-journeys": {"qa-contract-render"},
        "release-gate": set(load_manifest()["required_contexts"]) - {"release-gate"},
    }


# ── Contract failures (each rule must be able to fail) ──────────────────────


def test_rename_job_without_manifest_update_fails(tmp_path):
    manifest = _real_manifest()
    ci = REAL_CI.replace("  backend-format:", "  backend-fmt:")
    root = _write_project(tmp_path, manifest, ci)
    issues: list[str] = []
    check_required_checks(issues, root=root)
    assert any("backend-fmt" in issue and "not listed" in issue for issue in issues)
    assert any("`backend-format` is not a job" in issue for issue in issues)


def test_removing_required_context_from_aggregator_fails(tmp_path):
    manifest = _real_manifest()
    ci = REAL_CI.replace("      - backend-test\n", "")
    root = _write_project(tmp_path, manifest, ci)
    issues: list[str] = []
    check_required_checks(issues, root=root)
    assert any(
        "release-gate: needs is missing required contexts ['backend-test']" in issue
        for issue in issues
    )


def test_conditional_context_in_aggregator_fails(tmp_path):
    manifest = _real_manifest()
    manifest["conditional_contexts"]["desktop-check"]["required"] = False
    ci = REAL_CI.replace(
        "      - ui-journeys\n    steps:",
        "      - ui-journeys\n      - desktop-check\n    steps:",
    )
    root = _write_project(tmp_path, manifest, ci)
    issues: list[str] = []
    check_required_checks(issues, root=root)
    assert any("non-required contexts ['desktop-check']" in issue for issue in issues)


def test_new_needs_edge_between_quality_gates_fails(tmp_path):
    # M-06 root cause: a quality gate gating another quality gate. Reintroducing
    # `needs: [backend-format]` on backend-test must fail the contract.
    manifest = _real_manifest()
    ci = REAL_CI.replace(
        "  backend-test:\n    runs-on: ubuntu-latest\n    timeout-minutes: 90\n    defaults:",
        "  backend-test:\n    runs-on: ubuntu-latest\n    timeout-minutes: 90\n    needs: [backend-format]\n    defaults:",
    )
    root = _write_project(tmp_path, manifest, ci)
    issues: list[str] = []
    check_required_checks(issues, root=root)
    assert any(
        "job `backend-test` needs ['backend-format']" in issue for issue in issues
    )


def test_aggregator_without_always_fails(tmp_path):
    manifest = _real_manifest()
    ci = REAL_CI.replace("    if: always()\n    needs:", "    needs:")
    root = _write_project(tmp_path, manifest, ci)
    issues: list[str] = []
    check_required_checks(issues, root=root)
    assert any("must run `if: always()`" in issue for issue in issues)


def test_job_level_continue_on_error_fails(tmp_path):
    manifest = _real_manifest()
    ci = REAL_CI.replace(
        "  backend-test:\n    runs-on: ubuntu-latest",
        "  backend-test:\n    continue-on-error: true\n    runs-on: ubuntu-latest",
    )
    root = _write_project(tmp_path, manifest, ci)
    issues: list[str] = []
    check_required_checks(issues, root=root)
    assert any(
        "job `backend-test` sets job-level continue-on-error" in issue
        for issue in issues
    )


def test_missing_manifest_fails_closed(tmp_path):
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text(
        REAL_CI, encoding="utf-8"
    )
    issues: list[str] = []
    check_required_checks(issues, root=tmp_path)
    assert any("missing required-checks manifest" in issue for issue in issues)


def test_unparseable_workflow_fails_closed(tmp_path):
    root = _write_project(tmp_path, _real_manifest(), "not: a: workflow:")
    issues: list[str] = []
    check_required_checks(issues, root=root)
    assert any("could not parse any jobs" in issue for issue in issues)
