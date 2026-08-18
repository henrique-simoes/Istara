"""Workflow contract regression tests (scripts/check_workflow_contracts.py).

Covers the F-6 regression contract: CI-generated badge-sync writebacks are
restricted to the release branch (`main`) and never mutate `testing`, so
`testing` HEAD stays a stable, reproducible source for the exact-SHA human
promotion gate (no-direct-push contract).
"""

from __future__ import annotations

from pathlib import Path

from scripts.check_workflow_contracts import (
    ROOT,
    WORKFLOWS,
    check_ci,
    check_promote,
    check_qa_artifact,
    main,
)

REAL_CI = (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")


def _write_ci(text: str, tmp_path: Path) -> Path:
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "ci.yml").write_text(text, encoding="utf-8")
    return tmp_path


def _ci_issues(text: str, tmp_path: Path) -> list[str]:
    issues: list[str] = []
    check_ci(issues, root=_write_ci(text, tmp_path))
    return issues


def test_real_ci_passes_badge_sync_regression(tmp_path):
    issues = _ci_issues(REAL_CI, tmp_path)
    assert issues == []


def test_real_workflows_pass_full_contract():
    issues: list[str] = []
    check_ci(issues, root=ROOT)
    check_qa_artifact(issues, root=ROOT)
    check_promote(issues, root=ROOT)
    assert issues == []


def test_cli_exit_zero_on_real_workflows():
    assert main() == 0


def test_ci_rejects_writeback_to_triggering_branch(tmp_path):
    # Reintroducing the generic `${{ github.ref_name }}` writeback is the F-6
    # regression: on a `testing` push it would auto-commit to `testing`.
    bad = REAL_CI.replace(
        "git push origin HEAD:main", "git push origin HEAD:${{ github.ref_name }}"
    )
    issues = _ci_issues(bad, tmp_path)
    assert any("ref_name" in issue and "writeback" in issue for issue in issues)


def test_ci_rejects_writeback_without_main_gate(tmp_path):
    # Removing the `main`-only gate would re-enable badge sync on `testing`.
    bad = REAL_CI.replace(
        "if: github.event_name == 'push' && github.ref_name == 'main'",
        "if: github.event_name == 'push'",
    )
    issues = _ci_issues(bad, tmp_path)
    assert any("release branch" in issue for issue in issues)


def test_ci_rejects_direct_push_to_testing(tmp_path):
    # Any CI step pushing a generated commit to `testing` violates the
    # no-direct-push / reproducible-source contract.
    bad = REAL_CI.replace("git push origin HEAD:main", "git push origin HEAD:testing")
    issues = _ci_issues(bad, tmp_path)
    assert any("testing" in issue and "push" in issue for issue in issues)


def test_ci_rejects_writeback_with_disabled_gate(tmp_path):
    # A disabled/removed `main`-only gate must fail closed: the writeback can no
    # longer be proven to stay on the release branch.
    bad = REAL_CI.replace(
        "if: github.event_name == 'push' && github.ref_name == 'main'",
        "if: false",
    )
    issues = _ci_issues(bad, tmp_path)
    assert any("release branch" in issue for issue in issues)
