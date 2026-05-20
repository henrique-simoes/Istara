"""Source-level contracts for project-scoped test harnesses."""

from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read_repo(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


SIMULATION_SCOPE_FILES = [
    *sorted((REPO_ROOT / "tests/simulation/scenarios").glob("*.mjs")),
    REPO_ROOT / "tests/simulation/lib/api-client.mjs",
    REPO_ROOT / "tests/e2e_test.py",
]


def test_interfaces_tab_label_uses_configuration_copy() -> None:
    source = read_repo("frontend/src/components/interfaces/InterfacesView.tsx")

    assert '{ id: "figma", icon: ExternalLink, label: "Configuration" }' in source
    assert 'label: "Figma"' not in source


def test_simulation_harness_does_not_fall_back_to_fake_or_first_project_ids() -> None:
    forbidden = [
        "ctx.projectId ||",
        "projectId ||",
        '"sim-project-001"',
        "project_id: projectId ||",
        'project_id": project_id if project_id else',
        "if (list.length > 0) projectId =",
        "projects[0].id",
    ]

    offenders: list[str] = []
    for path in SIMULATION_SCOPE_FILES:
        source = path.read_text(encoding="utf-8")
        for marker in forbidden:
            if marker in source:
                offenders.append(f"{path.relative_to(REPO_ROOT)} contains {marker!r}")

    assert offenders == []


def test_simulation_harness_by_id_task_agent_document_calls_are_project_scoped() -> None:
    unscoped_call = re.compile(
        r"(?:api\.(?:get|patch|delete|put|post)\(`|fetch\(`http://localhost:8000)"
        r"(?P<path>/api/(?:tasks|agents|documents)/[^`\"?]+)`"
    )
    path_scoped_prefixes = (
        "/api/documents/tags/",
        "/api/documents/stats/",
        "/api/documents/sync/",
    )

    offenders: list[str] = []
    for path in sorted((REPO_ROOT / "tests/simulation/scenarios").glob("*.mjs")):
        source = path.read_text(encoding="utf-8")
        for match in unscoped_call.finditer(source):
            api_path = match.group("path")
            if "${" not in api_path:
                continue
            if api_path.startswith(path_scoped_prefixes):
                continue
            if api_path.startswith("/api/agents/") and "/messages" in api_path:
                continue
            line = source.count("\n", 0, match.start()) + 1
            offenders.append(f"{path.relative_to(REPO_ROOT)}:{line}: {api_path}")

    assert offenders == []


def test_voice_transcription_tests_and_ui_require_explicit_project_id() -> None:
    chat_api = read_repo("frontend/src/lib/chatApi.ts")
    voice_hook = read_repo("frontend/src/hooks/useVoiceRecorder.ts")
    e2e = read_repo("tests/e2e_test.py")
    voice_scenario = read_repo("tests/simulation/scenarios/77-voice-transcription.mjs")

    assert 'formData.append("project_id", projectId);' in chat_api
    assert "const scopedProjectId = projectId.trim();" in voice_hook
    assert 'setError("Select a project before transcribing audio.");' in voice_hook
    assert '"project_id": project_id if project_id else "0"' not in e2e
    assert '"project_id": project_id,' in e2e
    assert 'form.append("project_id", ctx.projectId);' in voice_scenario
