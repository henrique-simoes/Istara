"""Contracts for project-scoped integration harness requests.

The simulation and benchmark harnesses should exercise the same active-project
API boundary as the UI. Creation payloads may carry ``project_id`` in the body,
but by-id reads, actions, syncs, and cleanup calls must keep the active project
in the URL so stale ids cannot accidentally exercise global behavior.
"""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

HARNESS_FILES = (
    "tests/simulation/scenarios/53-channel-lifecycle.mjs",
    "tests/simulation/scenarios/55-survey-integration.mjs",
    "tests/simulation/scenarios/57-mcp-client-registry.mjs",
    "tests/simulation/scenarios/58-research-deployment.mjs",
    "tests/simulation/scenarios/68-data-security.mjs",
    "tests/real_user_benchmark/lib/integration-discovery.mjs",
)

PROJECT_SCOPED_DYNAMIC_ENDPOINTS = (
    "/api/channels/${",
    "/api/deployments/${",
    "/api/surveys/links/${",
    "/api/surveys/integrations/${",
    "/api/mcp/clients/${",
)

PROJECT_SCOPED_COLLECTION_ENDPOINTS = (
    "/api/channels",
    "/api/deployments",
    "/api/surveys/links",
    "/api/surveys/integrations",
    "/api/mcp/clients",
    "/api/mcp/featured",
)

SCOPE_TOKENS = (
    "project_id",
    "projectQuery",
    "ProjectQuery",
    "projectQuerySuffix",
    "projectScopeQuery",
)

BODY_SCOPED_CREATES = (
    'api.post("/api/channels"',
    'api.post("/api/deployments"',
    'api.post("/api/surveys/links"',
    'api.post("/api/surveys/integrations"',
    'api.post("/api/mcp/clients"',
    'api.post("/api/mcp/featured/mcp-brasil/connect"',
)


def _api_lines(source: str) -> list[tuple[int, str]]:
    lines: list[tuple[int, str]] = []
    for line_number, line in enumerate(source.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            continue
        if "/api/" in stripped and ("api." in stripped or "fetch(" in stripped):
            lines.append((line_number, stripped))
    return lines


def _has_project_scope(line: str) -> bool:
    return any(token in line for token in SCOPE_TOKENS)


def _is_body_scoped_create(line: str) -> bool:
    return any(pattern in line for pattern in BODY_SCOPED_CREATES)


def test_integration_simulation_by_id_calls_keep_active_project_scope() -> None:
    offenders: list[str] = []

    for relative_path in HARNESS_FILES:
        source = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        for line_number, line in _api_lines(source):
            if not any(
                endpoint in line for endpoint in PROJECT_SCOPED_DYNAMIC_ENDPOINTS
            ):
                continue
            if _is_body_scoped_create(line) or _has_project_scope(line):
                continue
            offenders.append(f"{relative_path}:{line_number}: {line}")

    assert offenders == []


def test_integration_simulation_project_lists_keep_active_project_scope() -> None:
    offenders: list[str] = []

    for relative_path in HARNESS_FILES:
        source = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        for line_number, line in _api_lines(source):
            if _is_body_scoped_create(line):
                continue
            if not any(
                endpoint in line for endpoint in PROJECT_SCOPED_COLLECTION_ENDPOINTS
            ):
                continue
            if "/api/mcp/server/status" in line:
                continue
            if _has_project_scope(line):
                continue
            offenders.append(f"{relative_path}:{line_number}: {line}")

    assert offenders == []
