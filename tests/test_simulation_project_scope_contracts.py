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


def test_simulation_agent_and_meta_harnesses_pass_active_project_scope() -> None:
    scenario_44 = read_repo("tests/simulation/scenarios/44-agent-factory.mjs")
    scenario_52 = read_repo("tests/simulation/scenarios/52-meta-hyperagent.mjs")
    scenario_73 = read_repo("tests/simulation/scenarios/73-a2a-debate-and-reports.mjs")

    assert "No active project id; scoped endpoint not called" in scenario_44
    assert "project_id=${encodeURIComponent(projectId)}" in scenario_44
    assert 'apiGetProjectScoped("/api/agents"' in scenario_44
    for path in (
        "/api/agents/creation-proposals/pending",
        "/api/agents/creation-proposals/all",
        "/api/agents/creation-proposals/nonexistent/approve",
        "/api/agents/creation-proposals/nonexistent/reject",
    ):
        assert f'fetchProjectScoped("{path}"' in scenario_44
    assert 'fetch("http://localhost:8000/api/agents/creation-proposals' not in scenario_44

    assert "No active project id; scoped endpoint not called" in scenario_52
    assert "project_id=${encodeURIComponent(projectId)}" in scenario_52
    for path in (
        "/api/meta-hyperagent/status",
        "/api/meta-hyperagent/toggle",
        "/api/meta-hyperagent/proposals",
        "/api/meta-hyperagent/variants",
        "/api/meta-hyperagent/observations",
        "/api/meta-hyperagent/proposals/nonexistent/approve",
        "/api/meta-hyperagent/proposals/nonexistent/reject",
        "/api/meta-hyperagent/variants/nonexistent/revert",
    ):
        assert f'"{path}"' in scenario_52
    assert 'api.get("/api/meta-hyperagent/' not in scenario_52
    assert 'api.post("/api/meta-hyperagent/' not in scenario_52

    assert "/api/agents?include_system=true&project_id=${encodeURIComponent(projectId)}" in scenario_73
    assert "/api/agents/creation-proposals/all?project_id=${encodeURIComponent(projectId)}&limit=5" in scenario_73


def test_simulation_loop_harness_passes_active_project_scope() -> None:
    scenario_49 = read_repo("tests/simulation/scenarios/49-loops-schedule.mjs")

    assert "No active project id; scoped endpoint not called" in scenario_49
    assert "project_id=${encodeURIComponent(projectId)}" in scenario_49

    for path in (
        "/api/loops/overview",
        "/api/loops/agents",
        "/api/loops/health",
        "/api/loops/executions",
        "/api/loops/executions/stats",
        "/api/schedules",
    ):
        assert f'apiGetProjectScoped("{path}"' in scenario_49

    for path in (
        "/api/schedules",
        "/api/loops/custom",
    ):
        assert f'apiPostProjectScoped("{path}"' in scenario_49

    assert "apiGetProjectScoped(`/api/loops/agents/${testAgentId}/config`" in scenario_49
    assert "apiPostProjectScoped(`/api/loops/agents/${testAgentId}/pause`" in scenario_49
    assert "apiPostProjectScoped(`/api/loops/agents/${testAgentId}/resume`" in scenario_49
    assert "fetchProjectScoped(url, \"PATCH /api/loops/agents/{id}/config updates interval\"" in scenario_49
    assert "fetchProjectScoped(`/api/schedules/${testScheduleId}`" in scenario_49

    for path in (
        "api.get(\"/api/loops",
        "api.post(\"/api/loops",
        "api.get(\"/api/schedules",
        "api.post(\"/api/schedules",
        "fetch(`http://localhost:8000/api/loops",
        "fetch(\"http://localhost:8000/api/loops",
        "fetch(`http://localhost:8000/api/schedules",
        "fetch(\"http://localhost:8000/api/schedules",
    ):
        assert path not in scenario_49


def test_simulation_scheduler_smoke_harnesses_pass_active_project_scope() -> None:
    scenario_01 = read_repo("tests/simulation/scenarios/01-health-check.mjs")
    scenario_22 = read_repo("tests/simulation/scenarios/22-architecture-evaluation.mjs")
    scenario_30 = read_repo("tests/simulation/scenarios/30-event-wiring-audit.mjs")

    for scenario in (scenario_01, scenario_22, scenario_30):
        assert "No active project id; scoped endpoint not called" in scenario

    assert "project_id=${encodeURIComponent(activeProjectId)}" in scenario_01
    assert 'api.get(projectScopedPath("/api/schedules"))' in scenario_01
    assert 'api.get("/api/schedules")' not in scenario_01

    assert "project_id=${encodeURIComponent(evalProjectId)}" in scenario_22
    assert "fetch(`http://localhost:8000/api/schedules?${projectQuery}`" in scenario_22
    assert 'fetch("http://localhost:8000/api/schedules"' not in scenario_22
    assert "fetch(`http://localhost:8000/api/schedules`" not in scenario_22

    assert "project_id=${encodeURIComponent(activeProjectId)}" in scenario_30
    assert 'api.get(projectScopedPath("/api/schedules"))' in scenario_30
    assert 'api.get("/api/schedules")' not in scenario_30
