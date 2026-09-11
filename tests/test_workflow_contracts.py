"""Workflow contract regression tests (scripts/check_workflow_contracts.py).

Covers the F-6 regression contract: CI-generated badge-sync writebacks are
restricted to the release branch (`main`) and never mutate `testing`, so
`testing` HEAD stays a stable, reproducible source for the exact-SHA human
promotion gate (no-direct-push contract).

Covers the F-5-r2 regression contract: promote-testing.yml's fail-closed
required-checks step lists Actions runs via `gh api .../actions/runs`, so the
workflow's explicit `permissions` block must bind `actions: read` — without
it the check 403s on a normal runner and the only promotion path can never
reach PR creation.
"""

from __future__ import annotations

from pathlib import Path

from scripts.check_workflow_contracts import (
    ROOT,
    WORKFLOWS,
    check_badge_sync,
    check_ci,
    check_promote,
    check_qa_artifact,
    main,
)

REAL_CI = (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")
REAL_PROMOTE = (WORKFLOWS / "promote-testing.yml").read_text(encoding="utf-8")
REAL_BADGE = (WORKFLOWS / "badge-sync.yml").read_text(encoding="utf-8")


def _write_promote(text: str, tmp_path: Path) -> Path:
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "promote-testing.yml").write_text(text, encoding="utf-8")
    return tmp_path


def _promote_issues(text: str, tmp_path: Path) -> list[str]:
    issues: list[str] = []
    check_promote(issues, root=_write_promote(text, tmp_path))
    return issues


def _write_ci(text: str, tmp_path: Path) -> Path:
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "ci.yml").write_text(text, encoding="utf-8")
    (wf / "badge-sync.yml").write_text(REAL_BADGE, encoding="utf-8")
    (wf / "qa-artifact.yml").write_text("placeholder", encoding="utf-8")
    (wf / "promote-testing.yml").write_text("placeholder", encoding="utf-8")
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
    check_badge_sync(issues, root=ROOT)
    check_qa_artifact(issues, root=ROOT)
    check_promote(issues, root=ROOT)
    assert issues == []


def test_cli_exit_zero_on_real_workflows():
    assert main() == 0


def test_ci_rejects_any_git_push(tmp_path):
    # M-13 regression: ci.yml is a required check and must be read-only. A
    # writeback inside CI — even one targeting `main` — reintroduces a push
    # path from the required graph; badge sync lives in badge-sync.yml.
    bad = REAL_CI.replace(
        "      - name: Check integrity",
        "      - name: badge writeback (forbidden)\n        run: git push origin HEAD:main",
    )
    issues = _ci_issues(bad, tmp_path)
    assert any("no CI job may push to any branch" in issue for issue in issues)


def test_ci_rejects_direct_push_to_testing(tmp_path):
    # Any CI step pushing a generated commit to `testing` violates the
    # no-direct-push / reproducible-source contract.
    bad = REAL_CI.replace(
        "      - name: Check integrity",
        "      - name: forbidden push\n        run: git push origin HEAD:testing",
    )
    issues = _ci_issues(bad, tmp_path)
    assert any("testing" in issue and "push" in issue for issue in issues)


def test_ci_rejects_missing_release_gate_aggregator(tmp_path):
    # The fail-closed aggregator is load-bearing (D.1/D.9): without it, a
    # cancelled or unexpectedly skipped required job could yield a
    # misleading green.
    bad = REAL_CI.replace("  release-gate:", "  final-gate:")
    issues = _ci_issues(bad, tmp_path)
    assert any("release-gate" in issue for issue in issues)


def test_ci_rejects_missing_required_checks_contract(tmp_path):
    # Removing the M-20 contract check lets required-check semantics rot
    # silently.
    bad = REAL_CI.replace("python scripts/check_required_checks.py", "true")
    issues = _ci_issues(bad, tmp_path)
    assert any("required-checks manifest contract" in issue for issue in issues)


def test_ci_backend_test_installs_both_pi_surfaces(tmp_path):
    # F-CI-R1-2: the full suite includes the pi lockstep diff-proof acceptance
    # (`scripts/pi_bump_diff_proof.py verify`), which fails closed unless BOTH
    # bundled surfaces have installed @earendil-works packages. backend-test
    # must therefore `npm ci` pi-runtime AND labs/pi-replacement.
    issues = _ci_issues(REAL_CI, tmp_path)
    assert issues == []


def test_ci_rejects_missing_labs_replacement_install(tmp_path):
    bad = REAL_CI.replace(
        "      - name: Install labs/pi-replacement dependencies (pi diff-proof surface)\n"
        "        working-directory: labs/pi-replacement\n"
        "        run: npm ci\n",
        "",
    )
    assert bad != REAL_CI, "the labs/pi-replacement install step moved or was renamed"
    issues = _ci_issues(bad, tmp_path)
    assert any("labs/pi-replacement" in issue for issue in issues)


def test_ci_pi_surface_install_must_be_in_backend_test(tmp_path):
    # A step elsewhere in the workflow does not build node_modules for the
    # job that runs the suite: the install must live in backend-test itself.
    bad = REAL_CI.replace(
        "      - name: Install labs/pi-replacement dependencies (pi diff-proof surface)\n"
        "        working-directory: labs/pi-replacement\n"
        "        run: npm ci\n",
        "",
    ).replace(
        "      - name: Run backend mutation gate",
        "      - name: misplaced labs install\n"
        "        working-directory: labs/pi-replacement\n"
        "        run: npm ci\n"
        "      - name: Run backend mutation gate",
    )
    issues = _ci_issues(bad, tmp_path)
    assert any("labs/pi-replacement" in issue for issue in issues)


def test_badge_sync_rejects_testing_trigger(tmp_path):
    # F-6 regression: badge sync triggering on `testing` would push generated
    # commits to the promotion source.
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    bad = REAL_BADGE.replace("branches: [main]", "branches: [main, testing]")
    (wf / "badge-sync.yml").write_text(bad, encoding="utf-8")
    issues: list[str] = []
    check_badge_sync(issues, root=tmp_path)
    assert any("never trigger on `testing`/`staging`" in issue for issue in issues)


def test_badge_sync_rejects_testing_writeback(tmp_path):
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    bad = REAL_BADGE.replace(
        "git push origin HEAD:main", "git push origin HEAD:testing"
    )
    (wf / "badge-sync.yml").write_text(bad, encoding="utf-8")
    issues: list[str] = []
    check_badge_sync(issues, root=tmp_path)
    assert any("never push to `testing`" in issue for issue in issues)


def test_badge_sync_requires_skip_ci_commit(tmp_path):
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    bad = REAL_BADGE.replace("[skip ci]", "")
    (wf / "badge-sync.yml").write_text(bad, encoding="utf-8")
    issues: list[str] = []
    check_badge_sync(issues, root=tmp_path)
    assert any("[skip ci]" in issue for issue in issues)


def test_badge_sync_requires_main_gate(tmp_path):
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    bad = REAL_BADGE.replace(
        "if: github.event_name == 'push' && github.ref_name == 'main'",
        "if: github.event_name == 'push'",
    )
    (wf / "badge-sync.yml").write_text(bad, encoding="utf-8")
    issues: list[str] = []
    check_badge_sync(issues, root=tmp_path)
    assert any("release branch" in issue for issue in issues)


def test_real_promote_passes_actions_read_regression(tmp_path):
    # The real promote-testing.yml binds `actions: read` and keeps the
    # required-checks `gh api .../actions/runs` verification step.
    issues = _promote_issues(REAL_PROMOTE, tmp_path)
    assert issues == []


def test_promote_rejects_missing_actions_read(tmp_path):
    # Reintroducing the F-5-r2 regression: dropping `actions: read` from the
    # explicit permissions leaves the Actions-runs listing unauthorized.
    bad = REAL_PROMOTE.replace("  actions: read\n", "")
    issues = _promote_issues(bad, tmp_path)
    assert any("actions: read" in issue for issue in issues)


def test_promote_rejects_missing_actions_runs_check(tmp_path):
    # Removing the required-checks API call silently disables the green-checks
    # gate; the permission contract must stay anchored to a real check.
    bad = REAL_PROMOTE.replace("/actions/runs", "/workflows")
    issues = _promote_issues(bad, tmp_path)
    assert any("actions/runs" in issue for issue in issues)
