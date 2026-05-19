"""Source-level contracts for project-scoped simulation harness calls."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read_repo(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_simulation_skill_harness_passes_active_project_scope() -> None:
    api_client = read_repo("tests/simulation/lib/api-client.mjs")
    scenario_06 = read_repo("tests/simulation/scenarios/06-skill-execution.mjs")
    scenario_20 = read_repo("tests/simulation/scenarios/20-all-skills-comprehensive.mjs")
    scenario_22 = read_repo("tests/simulation/scenarios/22-architecture-evaluation.mjs")
    scenario_41 = read_repo("tests/simulation/scenarios/41-skill-creation.mjs")

    assert "function projectScopedQuery(projectId, surface, extra = {})" in api_client
    assert "project_id is required for ${surface}" in api_client
    assert "health: (projectId) =>" in api_client
    assert "skillHealth: (name, projectId)" in api_client
    assert "all: (projectId, limit = 50)" in api_client
    assert "creationProposals" in api_client
    assert "all: (projectId, limit = 20)" in api_client

    assert "/api/skills/health/all?project_id=${encodeURIComponent(projectId)}" in scenario_06
    assert "[skipped] No active project id; scoped endpoint not called" in scenario_06
    assert "/api/skills/health/all?project_id=${encodeURIComponent(projectId)}" in scenario_20
    assert "/api/skills/proposals/all?project_id=${encodeURIComponent(projectId)}" in scenario_20
    assert "/api/skills/proposals/all?project_id=${encodeURIComponent(evalProjectId)}" in scenario_22
    assert "`/api/skills/health/all?${projectQuery}`" in scenario_22

    assert "No active project id; scoped endpoint not called" in scenario_41
    for path in (
        "/api/skills/creation-proposals/pending",
        "/api/skills/creation-proposals/all",
        "/api/skills/creation-proposals/nonexistent/reject",
        "/api/skills/creation-proposals/nonexistent/approve",
        "/api/skills/health/all",
    ):
        assert f'fetchProjectScoped(\n      "{path}"' in scenario_41
