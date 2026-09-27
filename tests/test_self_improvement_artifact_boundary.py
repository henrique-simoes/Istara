"""E1: self-improvement never creates or edits research artifacts.

The governance contract says telemetry, ReasoningBank, autoresearch, Meta-Hyperagent, the DGM-H
archive and self-evolution "may not create report evidence". Today none of them touches a
research model; nothing stopped a future change from doing so. This guard reads each module's
syntax tree and fails if one imports a research-artifact model module or names one of its
classes, so a new path from self-improvement into findings, evidence, coding, codebooks or
reports has to go through the spine instead.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1] / "backend" / "app"
SELF_IMPROVEMENT_MODULES = sorted(
    [
        *(BACKEND / "core").glob("autoresearch_*.py"),
        *(BACKEND / "core" / "autoresearch_runners").glob("*.py"),
        *(BACKEND / "core").glob("improvement_governance*.py"),
        *(BACKEND / "core").glob("dgmh_archive*.py"),
        BACKEND / "core" / "meta_hyperagent.py",
        BACKEND / "core" / "reasoning_bank.py",
        BACKEND / "core" / "self_evolution.py",
        BACKEND / "core" / "self_improvement_policy.py",
    ]
)
RESEARCH_MODEL_MODULES = {
    "app.models.finding",
    "app.models.research_validity",
    "app.models.code_application",
    "app.models.codebook",
    "app.models.codebook_version",
    "app.models.project_report",
}
RESEARCH_CLASSES = {
    "Nugget",
    "Fact",
    "Insight",
    "Recommendation",
    "EvidenceUnit",
    "CodingRun",
    "CodingRunCoder",
    "ResearchEvidenceEdge",
    "ReconciliationDecision",
    "CodeApplication",
    "ProjectReport",
}


def _violations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in RESEARCH_MODEL_MODULES:
            found.append(f"line {node.lineno}: from {node.module} import ...")
        elif isinstance(node, ast.Import):
            found += [
                f"line {node.lineno}: import {alias.name}"
                for alias in node.names
                if alias.name in RESEARCH_MODEL_MODULES
            ]
        elif isinstance(node, ast.Name) and node.id in RESEARCH_CLASSES:
            found.append(f"line {node.lineno}: {node.id}")
    return found


def test_the_guard_covers_every_self_improvement_module():
    names = {p.name for p in SELF_IMPROVEMENT_MODULES}
    assert {"reasoning_bank.py", "self_evolution.py", "meta_hyperagent.py"} <= names
    assert "autoresearch_engine.py" in names and "skill_prompt.py" in names
    assert all(p.exists() for p in SELF_IMPROVEMENT_MODULES)


@pytest.mark.parametrize("path", SELF_IMPROVEMENT_MODULES, ids=lambda p: p.name)
def test_self_improvement_module_never_touches_research_artifacts(path):
    assert _violations(path) == []


def test_the_guard_catches_an_artifact_write(tmp_path):
    offender = tmp_path / "offender.py"
    offender.write_text(
        "from app.models.finding import Nugget\n"
        "def promote(db):\n"
        "    db.add(Nugget(text='learned'))\n",
        encoding="utf-8",
    )
    assert len(_violations(offender)) == 2
