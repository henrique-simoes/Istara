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
        "frontend/src/lib/api.ts",
        "frontend/src/stores/computeStore.ts",
        "relay/lib/connection.mjs",
        "tests/compute_cases/api_routes.py",
        "tests/compute_cases/routing.py",
        "tests/compute_cases/stats_websocket.py",
        "tests/test_project_scope_contracts.py",
    ]
    result = evaluate_matrix(matrix, changed_paths=changed_paths)

    assert result.passed is True
    assert result.scorecard["auth_security_change_detected"] is True
    assert result.scorecard["triggered_paths"] == sorted(changed_paths)


def test_security_benchmark_detects_llm_server_security_paths() -> None:
    matrix = load_matrix(ROOT / "security" / "control_matrix.json")

    changed_paths = [
        "backend/app/api/routes/llm_servers.py",
        "tests/test_llm_servers.py",
        "tests/test_project_scope_contracts.py",
    ]
    result = evaluate_matrix(matrix, changed_paths=changed_paths)

    assert result.passed is True
    assert result.scorecard["auth_security_change_detected"] is True
    assert result.scorecard["triggered_paths"] == sorted(changed_paths)


def test_security_benchmark_detects_mcp_project_scope_paths() -> None:
    matrix = load_matrix(ROOT / "security" / "control_matrix.json")

    changed_paths = [
        "backend/app/api/routes/mcp.py",
        "backend/app/mcp/server.py",
        "backend/app/models/mcp_server_config.py",
        "frontend/src/components/integrations/MCPServerSetup.tsx",
        "frontend/src/components/integrations/MCPTab.tsx",
        "backend/app/services/mcp_security.py",
        "frontend/src/lib/api.ts",
        "frontend/src/stores/integrationsStore.ts",
        "tests/test_mcp.py",
        "tests/test_project_scope_contracts.py",
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
        "backend/app/services/channel_service.py",
        "backend/app/services/deployment_service.py",
        "backend/app/services/inbound_processor.py",
        "frontend/src/components/integrations/ChannelConversationsPanel.tsx",
        "frontend/src/components/integrations/ChannelInstanceCard.tsx",
        "frontend/src/components/integrations/ChannelMessagesPanel.tsx",
        "frontend/src/components/integrations/ChannelSetupWizard.tsx",
        "frontend/src/components/integrations/ConversationTranscript.tsx",
        "frontend/src/components/integrations/DeploymentDashboard.tsx",
        "frontend/src/components/integrations/DeploymentWizard.tsx",
        "frontend/src/components/integrations/DeploymentsTab.tsx",
        "frontend/src/components/integrations/IntegrationsOverview.tsx",
        "frontend/src/components/integrations/MessagingTab.tsx",
        "frontend/src/components/integrations/SurveySetupWizard.tsx",
        "frontend/src/components/integrations/SurveysTab.tsx",
        "frontend/src/lib/api.ts",
        "tests/real_user_benchmark/lib/integration-discovery.mjs",
        "tests/simulation/scenarios/58-research-deployment.mjs",
        "tests/test_channel_inbound.py",
        "tests/test_channels.py",
        "tests/test_deployments.py",
        "tests/test_project_scope_contracts.py",
        "tests/test_surveys.py",
    ]
    result = evaluate_matrix(matrix, changed_paths=changed_paths)

    assert result.passed is True
    assert result.scorecard["auth_security_change_detected"] is True
    assert result.scorecard["triggered_paths"] == sorted(changed_paths)


def test_security_benchmark_detects_report_project_scope_paths() -> None:
    matrix = load_matrix(ROOT / "security" / "control_matrix.json")

    changed_paths = [
        "backend/app/api/routes/reports.py",
        "backend/app/core/report_manager.py",
        "backend/app/core/reporting_worker.py",
        "tests/test_research_integrity_reports.py",
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
        "frontend/src/components/notifications/NotificationListTab.tsx",
        "frontend/src/components/notifications/NotificationsView.tsx",
        "frontend/src/lib/notificationApi.ts",
        "frontend/src/stores/notificationStore.ts",
        "tests/test_notifications.py",
    ]
    result = evaluate_matrix(matrix, changed_paths=changed_paths)

    assert result.passed is True
    assert result.scorecard["auth_security_change_detected"] is True
    assert result.scorecard["triggered_paths"] == sorted(changed_paths)


def test_security_benchmark_detects_permission_request_project_scope_paths() -> None:
    matrix = load_matrix(ROOT / "security" / "control_matrix.json")

    changed_paths = [
        "backend/app/api/routes/permission_requests.py",
        "frontend/src/components/admin/AdminDashboard.tsx",
        "frontend/src/components/settings/ProjectSettingsView.tsx",
        "frontend/src/lib/api.ts",
        "tests/test_project_rbac.py",
        "tests/test_project_scope_contracts.py",
    ]
    result = evaluate_matrix(matrix, changed_paths=changed_paths)

    assert result.passed is True
    assert result.scorecard["auth_security_change_detected"] is True
    assert result.scorecard["triggered_paths"] == sorted(changed_paths)


def test_security_benchmark_detects_realtime_project_scope_paths() -> None:
    matrix = load_matrix(ROOT / "security" / "control_matrix.json")

    changed_paths = [
        "backend/app/api/websocket.py",
        "frontend/src/hooks/useWebSocket.ts",
        "tests/test_websocket.py",
    ]
    result = evaluate_matrix(matrix, changed_paths=changed_paths)

    assert result.passed is True
    assert result.scorecard["auth_security_change_detected"] is True
    assert result.scorecard["triggered_paths"] == sorted(changed_paths)


def test_security_benchmark_detects_loop_project_scope_paths() -> None:
    matrix = load_matrix(ROOT / "security" / "control_matrix.json")

    changed_paths = [
        "backend/app/api/routes/loops.py",
        "backend/app/api/routes/scheduler.py",
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
        "backend/app/api/routes/a2a.py",
        "backend/app/core/agent_lifecycle.py",
        "backend/app/core/sub_agent_worker.py",
        "backend/app/services/a2a.py",
        "backend/app/skills/system_actions.py",
        "frontend/src/lib/api.ts",
        "frontend/src/components/agents/AgentsView.tsx",
        "frontend/src/stores/agentStore.ts",
        "tests/test_agents.py",
        "tests/test_project_scope_contracts.py",
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


def test_security_benchmark_detects_findings_project_scope_paths() -> None:
    matrix = load_matrix(ROOT / "security" / "control_matrix.json")

    changed_paths = [
        "backend/app/api/routes/findings.py",
        "frontend/src/components/common/SearchModal.tsx",
        "frontend/src/components/findings/AtomicDrilldown.tsx",
        "frontend/src/components/findings/FindingsView.tsx",
        "frontend/src/components/agents/AgentTimeline.tsx",
        "frontend/src/lib/api.ts",
        "tests/test_findings.py",
        "tests/test_project_scope_contracts.py",
    ]
    result = evaluate_matrix(matrix, changed_paths=changed_paths)

    assert result.passed is True
    assert result.scorecard["auth_security_change_detected"] is True
    assert result.scorecard["triggered_paths"] == sorted(changed_paths)


def test_security_benchmark_detects_research_integrity_project_scope_paths() -> None:
    matrix = load_matrix(ROOT / "security" / "control_matrix.json")

    changed_paths = [
        "backend/app/api/routes/code_applications.py",
        "backend/app/api/routes/codebooks.py",
        "frontend/src/components/findings/CodeReviewQueue.tsx",
        "frontend/src/lib/researchIntegrityApi.ts",
        "tests/test_code_applications.py",
        "tests/test_codebooks.py",
        "tests/test_project_scope_contracts.py",
    ]
    result = evaluate_matrix(matrix, changed_paths=changed_paths)

    assert result.passed is True
    assert result.scorecard["auth_security_change_detected"] is True
    assert result.scorecard["triggered_paths"] == sorted(changed_paths)


def test_security_benchmark_detects_task_project_scope_paths() -> None:
    matrix = load_matrix(ROOT / "security" / "control_matrix.json")

    changed_paths = [
        "backend/app/api/routes/tasks.py",
        "frontend/src/components/kanban/KanbanBoard.tsx",
        "frontend/src/components/kanban/TaskEditor.tsx",
        "frontend/src/components/agents/AgentTimeline.tsx",
        "frontend/src/lib/api.ts",
        "frontend/src/stores/taskStore.ts",
        "tests/test_project_rbac.py",
        "tests/test_project_scope_contracts.py",
        "tests/test_tasks.py",
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
        "backend/app/core/agent_learning.py",
        "backend/app/skills/skill_usage.py",
        "frontend/src/components/meta/MetaHyperagentView.tsx",
        "frontend/src/lib/types.ts",
        "tests/test_meta_hyperagent.py",
        "tests/test_agent_learning_scope.py",
    ]
    result = evaluate_matrix(matrix, changed_paths=changed_paths)

    assert result.passed is True
    assert result.scorecard["auth_security_change_detected"] is True
    assert result.scorecard["triggered_paths"] == sorted(changed_paths)


def test_security_benchmark_detects_self_evolution_project_scope_paths() -> None:
    matrix = load_matrix(ROOT / "security" / "control_matrix.json")

    changed_paths = [
        "backend/app/api/routes/agents.py",
        "backend/app/agents/devops_agent.py",
        "backend/app/core/self_evolution.py",
        "frontend/src/lib/api.ts",
        "tests/test_agent_learning_scope.py",
        "tests/test_project_scope_contracts.py",
    ]
    result = evaluate_matrix(matrix, changed_paths=changed_paths)

    assert result.passed is True
    assert result.scorecard["auth_security_change_detected"] is True
    assert result.scorecard["triggered_paths"] == sorted(changed_paths)


def test_security_benchmark_detects_background_process_project_scope_paths() -> None:
    matrix = load_matrix(ROOT / "security" / "control_matrix.json")

    changed_paths = [
        "backend/app/main.py",
        "backend/app/agents/orchestrator.py",
        "backend/app/api/routes/scheduler.py",
        "backend/app/core/scheduler.py",
        "backend/app/core/agent_learning.py",
        "tests/test_project_scope_contracts.py",
        "tests/test_agent_learning_scope.py",
    ]
    result = evaluate_matrix(matrix, changed_paths=changed_paths)

    assert result.passed is True
    assert result.scorecard["auth_security_change_detected"] is True
    assert result.scorecard["triggered_paths"] == sorted(changed_paths)


def test_security_benchmark_detects_context_hierarchy_project_scope_paths() -> None:
    matrix = load_matrix(ROOT / "security" / "control_matrix.json")

    changed_paths = [
        "backend/app/api/routes/context_hierarchy.py",
        "backend/app/core/context_hierarchy.py",
        "backend/app/main.py",
        "frontend/src/components/common/ContextPreview.tsx",
        "tests/test_context_hierarchy.py",
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
