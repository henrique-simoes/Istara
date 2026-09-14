"""Agent-contract governance contract tests.

Covers the consolidation of agent instructions into AGENTS.md + CLAUDE.md:
CLAUDE.md is an active governance doc (not a legacy wrapper), retired docs
are gone from the integrity surface, and the release workflow triggers both
contracts. The governance scripts themselves must pass on the current tree.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from scripts.check_ci_governance import FORBIDDEN_SNIPPETS, REQUIRED_SNIPPETS
from scripts.check_integrity import ACTIVE_GOVERNANCE_DOCS, LEGACY_COMPASS_DOCS
from scripts.public_repo_quality_audit import RETIRED_ROOT_FILES

ROOT = Path(__file__).resolve().parent.parent

RETIRED_DOC_NAMES = {"CHANGE_CHECKLIST.md", "SYSTEM_CHANGE_MATRIX.md", "DOCUMENTATION.md"}


def _names(paths: list[Path]) -> set[str]:
    return {path.name for path in paths}


def test_active_governance_docs_include_both_agent_contracts():
    active = _names(ACTIVE_GOVERNANCE_DOCS)
    assert {"AGENTS.md", "CLAUDE.md"} <= active


def test_retired_governance_docs_are_not_active():
    active = _names(ACTIVE_GOVERNANCE_DOCS)
    assert not (RETIRED_DOC_NAMES & active)


def test_claude_md_is_not_a_legacy_wrapper_or_retired_file():
    assert "CLAUDE.md" not in {path.name for path in LEGACY_COMPASS_DOCS}
    assert "CLAUDE.md" not in RETIRED_ROOT_FILES


def test_release_workflow_triggers_both_agent_contracts():
    snippets = REQUIRED_SNIPPETS[".github/workflows/build-installers.yml"]
    assert snippets["active agent contract release trigger"] == "AGENTS.md"
    assert snippets["Claude agent contract release trigger"] == "CLAUDE.md"
    assert "documentation map release trigger" not in snippets


def test_forbidden_snippets_do_not_ban_claude_md():
    for file_snippets in FORBIDDEN_SNIPPETS.values():
        assert "CLAUDE.md" not in file_snippets.values()


@pytest.mark.parametrize("script", ["check_integrity.py", "check_ci_governance.py"])
def test_governance_scripts_pass_on_current_tree(script: str) -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=120,
    )
    assert result.returncode == 0, (
        f"{script} failed:\n{result.stdout}\n{result.stderr}"
    )
