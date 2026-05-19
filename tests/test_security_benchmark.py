from __future__ import annotations

import copy
from pathlib import Path

from scripts.security_benchmark import evaluate_matrix, load_matrix

ROOT = Path(__file__).resolve().parent.parent


def test_security_benchmark_current_matrix_passes_release_gate() -> None:
    matrix = load_matrix(ROOT / "security" / "control_matrix.json")

    result = evaluate_matrix(matrix)

    assert result.passed is True
    assert result.scorecard["status"] == "pass"
    assert result.scorecard["score_percent"] >= 98
    assert result.scorecard["counts"]["partial"] == 0
    assert result.scorecard["minimum_score_percent"] >= 98
    assert (
        result.scorecard["score_percent"] >= result.scorecard["minimum_score_percent"]
    )
    assert result.scorecard["blocked_controls"] == []


def test_security_benchmark_detects_auth_security_changed_path() -> None:
    matrix = load_matrix(ROOT / "security" / "control_matrix.json")

    result = evaluate_matrix(matrix, changed_paths=["backend/app/api/routes/auth.py"])

    assert result.passed is True
    assert result.scorecard["auth_security_change_detected"] is True
    assert result.scorecard["triggered_paths"] == ["backend/app/api/routes/auth.py"]


def test_security_benchmark_detects_compute_project_scope_paths() -> None:
    matrix = load_matrix(ROOT / "security" / "control_matrix.json")

    changed_paths = [
        "backend/app/api/routes/compute.py",
        "backend/app/core/compute_registry_routing.py",
        "frontend/src/components/common/ComputePoolView.tsx",
        "frontend/src/stores/computeStore.ts",
        "relay/lib/connection.mjs",
        "tests/compute_cases/routing.py",
    ]
    result = evaluate_matrix(matrix, changed_paths=changed_paths)

    assert result.passed is True
    assert result.scorecard["auth_security_change_detected"] is True
    assert result.scorecard["triggered_paths"] == sorted(changed_paths)


def test_security_benchmark_detects_mcp_project_scope_paths() -> None:
    matrix = load_matrix(ROOT / "security" / "control_matrix.json")

    changed_paths = [
        "backend/app/models/mcp_server_config.py",
        "frontend/src/components/integrations/MCPTab.tsx",
        "frontend/src/stores/integrationsStore.ts",
        "tests/test_mcp.py",
    ]
    result = evaluate_matrix(matrix, changed_paths=changed_paths)

    assert result.passed is True
    assert result.scorecard["auth_security_change_detected"] is True
    assert result.scorecard["triggered_paths"] == sorted(changed_paths)


def test_security_benchmark_detects_integration_project_scope_paths() -> None:
    matrix = load_matrix(ROOT / "security" / "control_matrix.json")

    changed_paths = [
        "backend/app/api/routes/channels.py",
        "backend/app/api/routes/deployments.py",
        "backend/app/api/routes/surveys.py",
        "frontend/src/components/integrations/MessagingTab.tsx",
        "frontend/src/components/integrations/SurveysTab.tsx",
        "tests/test_channels.py",
        "tests/test_surveys.py",
    ]
    result = evaluate_matrix(matrix, changed_paths=changed_paths)

    assert result.passed is True
    assert result.scorecard["auth_security_change_detected"] is True
    assert result.scorecard["triggered_paths"] == sorted(changed_paths)


def test_security_benchmark_detects_interfaces_project_scope_paths() -> None:
    matrix = load_matrix(ROOT / "security" / "control_matrix.json")

    changed_paths = [
        "backend/app/api/routes/interfaces_common.py",
        "backend/app/api/routes/interfaces_integrations.py",
        "backend/app/api/routes/interfaces_screens.py",
        "backend/app/models/interface_config.py",
        "backend/app/services/stitch_service.py",
        "backend/alembic/versions/016_project_interface_configs.py",
        "frontend/src/components/interfaces/FigmaTab.tsx",
        "frontend/src/components/interfaces/HandoffTab.tsx",
        "frontend/src/stores/interfacesStore.ts",
        "tests/test_interfaces.py",
    ]
    result = evaluate_matrix(matrix, changed_paths=changed_paths)

    assert result.passed is True
    assert result.scorecard["auth_security_change_detected"] is True
    assert result.scorecard["triggered_paths"] == sorted(changed_paths)


def test_security_benchmark_detects_notification_project_scope_paths() -> None:
    matrix = load_matrix(ROOT / "security" / "control_matrix.json")

    changed_paths = [
        "backend/app/api/routes/notifications.py",
        "frontend/src/components/notifications/NotificationsView.tsx",
        "frontend/src/stores/notificationStore.ts",
        "tests/test_notifications.py",
    ]
    result = evaluate_matrix(matrix, changed_paths=changed_paths)

    assert result.passed is True
    assert result.scorecard["auth_security_change_detected"] is True
    assert result.scorecard["triggered_paths"] == sorted(changed_paths)


def test_security_benchmark_detects_loop_project_scope_paths() -> None:
    matrix = load_matrix(ROOT / "security" / "control_matrix.json")

    changed_paths = [
        "backend/app/api/routes/loops.py",
        "backend/app/services/loop_execution_service.py",
        "frontend/src/components/loops/LoopOverviewTab.tsx",
        "frontend/src/stores/loopsStore.ts",
        "tests/test_loops.py",
    ]
    result = evaluate_matrix(matrix, changed_paths=changed_paths)

    assert result.passed is True
    assert result.scorecard["auth_security_change_detected"] is True
    assert result.scorecard["triggered_paths"] == sorted(changed_paths)


def test_security_benchmark_detects_agent_project_scope_paths() -> None:
    matrix = load_matrix(ROOT / "security" / "control_matrix.json")

    changed_paths = [
        "backend/app/api/agent_project_scope.py",
        "backend/app/api/routes/agents.py",
        "frontend/src/lib/api.ts",
        "frontend/src/components/agents/AgentsView.tsx",
        "frontend/src/stores/agentStore.ts",
        "tests/test_agents.py",
    ]
    result = evaluate_matrix(matrix, changed_paths=changed_paths)

    assert result.passed is True
    assert result.scorecard["auth_security_change_detected"] is True
    assert result.scorecard["triggered_paths"] == sorted(changed_paths)


def test_security_benchmark_detects_chat_session_project_scope_paths() -> None:
    matrix = load_matrix(ROOT / "security" / "control_matrix.json")

    changed_paths = [
        "backend/app/api/routes/chat.py",
        "backend/app/api/routes/sessions.py",
        "frontend/src/components/chat/ChatSessionsSidebar.tsx",
        "frontend/src/components/chat/ChatView.tsx",
        "frontend/src/components/memory/ContextDAGView.tsx",
        "frontend/src/lib/sessionsApi.ts",
        "frontend/src/stores/chatStore.ts",
        "frontend/src/stores/sessionStore.ts",
        "tests/test_sessions.py",
    ]
    result = evaluate_matrix(matrix, changed_paths=changed_paths)

    assert result.passed is True
    assert result.scorecard["auth_security_change_detected"] is True
    assert result.scorecard["triggered_paths"] == sorted(changed_paths)


def test_security_benchmark_detects_document_project_scope_paths() -> None:
    matrix = load_matrix(ROOT / "security" / "control_matrix.json")

    changed_paths = [
        "backend/app/api/routes/documents.py",
        "frontend/src/components/documents/DocumentsView.tsx",
        "frontend/src/lib/api.ts",
        "frontend/src/stores/documentStore.ts",
        "tests/test_documents.py",
    ]
    result = evaluate_matrix(matrix, changed_paths=changed_paths)

    assert result.passed is True
    assert result.scorecard["auth_security_change_detected"] is True
    assert result.scorecard["triggered_paths"] == sorted(changed_paths)


def test_security_benchmark_detects_memory_context_project_scope_paths() -> None:
    matrix = load_matrix(ROOT / "security" / "control_matrix.json")

    changed_paths = [
        "backend/app/api/routes/context_dag.py",
        "backend/app/api/routes/memory.py",
        "frontend/src/components/memory/ContextDAGView.tsx",
        "frontend/src/components/memory/MemoryView.tsx",
        "frontend/src/lib/contextDagApi.ts",
        "frontend/src/lib/memoryApi.ts",
        "tests/test_context_dag.py",
        "tests/test_memory.py",
    ]
    result = evaluate_matrix(matrix, changed_paths=changed_paths)

    assert result.passed is True
    assert result.scorecard["auth_security_change_detected"] is True
    assert result.scorecard["triggered_paths"] == sorted(changed_paths)


def test_security_benchmark_detects_governed_evolution_project_scope_paths() -> None:
    matrix = load_matrix(ROOT / "security" / "control_matrix.json")

    changed_paths = [
        "backend/app/api/routes/dgmh_archive.py",
        "backend/app/api/routes/improvement_governance.py",
        "backend/app/api/routes/reasoning_bank.py",
        "backend/app/core/dgmh_archive.py",
        "backend/app/core/reasoning_bank.py",
        "frontend/src/components/settings/GovernedEvolutionView.tsx",
        "frontend/src/lib/dgmhArchiveApi.ts",
        "frontend/src/lib/improvementGovernanceApi.ts",
        "tests/test_dgmh_archive.py",
        "tests/test_improvement_governance.py",
        "tests/test_reasoning_bank.py",
    ]
    result = evaluate_matrix(matrix, changed_paths=changed_paths)

    assert result.passed is True
    assert result.scorecard["auth_security_change_detected"] is True
    assert result.scorecard["triggered_paths"] == sorted(changed_paths)


def test_security_benchmark_detects_meta_hyperagent_project_scope_paths() -> None:
    matrix = load_matrix(ROOT / "security" / "control_matrix.json")

    changed_paths = [
        "backend/app/api/routes/meta_hyperagent.py",
        "backend/app/core/meta_hyperagent.py",
        "backend/app/skills/skill_usage.py",
        "frontend/src/components/meta/MetaHyperagentView.tsx",
        "frontend/src/lib/types.ts",
        "tests/test_meta_hyperagent.py",
    ]
    result = evaluate_matrix(matrix, changed_paths=changed_paths)

    assert result.passed is True
    assert result.scorecard["auth_security_change_detected"] is True
    assert result.scorecard["triggered_paths"] == sorted(changed_paths)


def test_security_benchmark_detects_context_hierarchy_project_scope_paths() -> None:
    matrix = load_matrix(ROOT / "security" / "control_matrix.json")

    changed_paths = [
        "backend/app/api/routes/context_hierarchy.py",
        "backend/app/main.py",
    ]
    result = evaluate_matrix(matrix, changed_paths=changed_paths)

    assert result.passed is True
    assert result.scorecard["auth_security_change_detected"] is True
    assert result.scorecard["triggered_paths"] == sorted(changed_paths)


def test_security_benchmark_blocks_failed_control() -> None:
    matrix = load_matrix(ROOT / "security" / "control_matrix.json")
    modified = copy.deepcopy(matrix)
    modified["controls"][0]["status"] = "fail"

    result = evaluate_matrix(modified)

    assert result.passed is False
    assert any(
        control["id"] == modified["controls"][0]["id"]
        for control in result.scorecard["blocked_controls"]
    )


def test_security_benchmark_blocks_high_severity_partial_control() -> None:
    matrix = load_matrix(ROOT / "security" / "control_matrix.json")
    modified = copy.deepcopy(matrix)
    modified["controls"][0]["status"] = "partial"
    modified["controls"][0]["severity"] = "high"

    result = evaluate_matrix(modified)

    assert result.passed is False
    assert any(
        control["reason"] == "critical/high partial control"
        for control in result.scorecard["blocked_controls"]
    )


def test_security_benchmark_requires_evidence_for_pass_controls() -> None:
    matrix = load_matrix(ROOT / "security" / "control_matrix.json")
    modified = copy.deepcopy(matrix)
    modified["controls"][0]["evidence"] = []

    result = evaluate_matrix(modified)

    assert result.passed is False
    assert "pass controls require evidence" in result.scorecard["validation_issues"][0]
