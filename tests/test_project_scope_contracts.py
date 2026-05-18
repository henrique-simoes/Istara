"""Source-level contracts for project-scoped views.

These tests complement API and browser tests by catching the common failure mode
where a project-facing view accidentally calls a global/list endpoint without
the active project id.
"""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read_repo(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_interfaces_tab_label_uses_configuration_copy() -> None:
    source = read_repo("frontend/src/components/interfaces/InterfacesView.tsx")

    assert '{ id: "figma", icon: ExternalLink, label: "Configuration" }' in source
    assert 'label: "Figma"' not in source


def test_integrations_overview_recent_activity_is_project_scoped() -> None:
    source = read_repo("frontend/src/components/integrations/IntegrationsOverview.tsx")

    assert "const { activeProjectId } = useProjectStore();" in source
    assert "fetchChannels(undefined, activeProjectId)" in source
    assert "fetchDeployments(activeProjectId)" in source
    assert "fetchSurveyIntegrations(activeProjectId)" in source
    assert "fetchMCPClients(activeProjectId)" in source
    assert "const scopedChannels = activeProjectId" in source
    assert "const scopedDeployments = activeProjectId" in source
    assert "const scopedSurveyIntegrations = activeProjectId" in source
    assert "const scopedMCPClients = activeProjectId" in source
    assert ": [];" in source
    assert "...scopedChannels.slice(0, 3)" in source
    assert "...scopedDeployments.slice(0, 3)" in source
    assert "...channelInstances.slice(0, 3)" not in source
    assert "...deploymentsList.slice(0, 3)" not in source


def test_integrations_deployments_tab_is_project_scoped() -> None:
    source = read_repo("frontend/src/components/integrations/DeploymentsTab.tsx")

    assert 'import { useProjectStore } from "@/stores/projectStore";' in source
    assert "const { activeProjectId } = useProjectStore();" in source
    assert "fetchDeployments(activeProjectId)" in source
    assert "const scopedDeployments = activeProjectId" in source
    assert "deploymentsList.filter((d) => d.project_id === activeProjectId)" in source
    assert "const selectedDeployment = scopedDeployments.find" in source
    assert "scopedDeployments.map((deployment)" in source
    assert "scopedDeployments.length === 0" in source
    assert "deploymentsList.map" not in source
    assert "deploymentsList.reduce" not in source
    assert "fetchDeployments();" not in source


def test_integrations_store_and_api_accept_project_filters() -> None:
    store = read_repo("frontend/src/stores/integrationsStore.ts")
    api = read_repo("frontend/src/lib/api.ts")

    assert "fetchChannels: (platform?: string, projectId?: string | null) => Promise<void>;" in store
    assert "fetchDeployments: (projectId?: string | null) => Promise<void>;" in store
    assert "fetchSurveyIntegrations: (projectId?: string | null) => Promise<void>;" in store
    assert "fetchMCPClients: (projectId?: string | null) => Promise<void>;" in store
    assert "if (!projectId)" in store
    assert "const list = await channels.list(platform, projectId);" in store
    assert "const list = await deployments.list(projectId);" in store
    assert "const list = await surveys.integrations.list(projectId);" in store
    assert "const list = await mcp.clients.list(projectId);" in store

    assert 'if (projectId) query.set("project_id", projectId);' in api
    assert "return get<ResearchDeployment[]>(`/api/deployments${params}`)" in api
    assert "const suffix = projectId ? `?project_id=${encodeURIComponent(projectId)}` : \"\";" in api
    assert 'get<any>(`/api/mcp/clients${suffix}`)' in api


def test_backend_project_owned_integration_lists_require_scope_for_non_admins() -> None:
    route_contracts = {
        "backend/app/api/routes/channels.py": 'raise HTTPException(status_code=400, detail="project_id is required")',
        "backend/app/api/routes/deployments.py": 'raise HTTPException(status_code=400, detail="project_id is required")',
        "backend/app/api/routes/surveys.py": 'raise HTTPException(status_code=400, detail="project_id is required")',
    }

    for path, required_error in route_contracts.items():
        source = read_repo(path)
        assert "elif not is_global_admin(subject):" in source
        assert required_error in source


def test_autoresearch_project_surfaces_require_active_project_scope() -> None:
    api = read_repo("frontend/src/lib/api.ts")
    store = read_repo("frontend/src/stores/autoresearchStore.ts")
    dashboard = read_repo("frontend/src/components/autoresearch/ExperimentDashboard.tsx")
    history = read_repo("frontend/src/components/autoresearch/ExperimentHistory.tsx")
    leaderboard = read_repo("frontend/src/components/autoresearch/LeaderboardTab.tsx")
    route = read_repo("backend/app/api/routes/autoresearch.py")
    engine = read_repo("backend/app/core/autoresearch_engine.py")

    assert "autoresearch.status(projectId)" in store
    assert "autoresearch.leaderboard(projectId)" in store
    assert "project_id: params.project_id" in store
    assert "fetchStatus(activeProjectId)" in dashboard
    assert "fetchExperiments({ project_id: activeProjectId, limit: 20 })" in dashboard
    assert "project_id: activeProjectId" in dashboard
    assert "stopLoop(activeProjectId)" in dashboard
    assert "params.project_id = activeProjectId" in history
    assert "fetchLeaderboard(activeProjectId)" in leaderboard

    assert "status: (projectId: string)" in api
    assert "/api/autoresearch/status?project_id=" in api
    assert 'p.set("project_id", params.project_id);' in api
    assert "/api/autoresearch/leaderboard?project_id=" in api
    assert "/api/autoresearch/stop?project_id=" in api

    assert "async def _require_project_scope" in route
    assert 'raise HTTPException(status_code=400, detail="project_id is required")' in route
    assert "operational_metrics\": await _build_operational_metrics(db, project_id)" in route
    assert "return await engine.get_leaderboard(project_id=project_id)" in route
    assert "await engine.get_experiments(" in route and "project_id=project_id" in route
    assert "Task.project_id == project_id" in route
    assert "ResearchDeployment.project_id == project_id" in route
    assert "TelemetrySpan.project_id == project_id" in route
    assert "ScheduledTask.project_id == project_id" in route

    assert '"project_id": project_id' in engine
    assert "AutoresearchExperiment.project_id == project_id" in engine
    assert "TelemetrySpan.project_id == project_id" in engine


def test_agents_a2a_project_view_passes_active_project_id() -> None:
    view = read_repo("frontend/src/components/agents/AgentsView.tsx")
    store = read_repo("frontend/src/stores/agentStore.ts")
    api = read_repo("frontend/src/lib/api.ts")
    route = read_repo("backend/app/api/routes/agents.py")

    assert "const { activeProjectId } = useProjectStore();" in view
    assert "fetchA2ALog(activeProjectId)" in view
    assert "fetchAgents(activeProjectId || undefined)" in view
    assert "if (!projectId)" in store
    assert "fetchA2ALog: async (projectId) =>" in store
    assert "if (!projectId)" in store
    assert "const data = await agentsApi.a2aLog(projectId, 100);" in store
    assert "a2aLog: (projectId: string, limit = 100)" in api
    assert 'params.set("project_id", projectId);' in api
    assert 'raise HTTPException(status_code=400, detail="project_id is required")' in route
    assert "await require_project_access(db, request, project_id, min_role=\"viewer\")" in route
    assert "await require_project_access(db, request, project_id, min_role=\"viewer\")" in route
    assert "messages = await a2a.get_full_log(db, limit, project_id=project_id)" in route


def test_loops_views_and_api_require_active_project_scope() -> None:
    loops_view = read_repo("frontend/src/components/loops/LoopsView.tsx")
    overview_tab = read_repo("frontend/src/components/loops/LoopOverviewTab.tsx")
    agent_tab = read_repo("frontend/src/components/loops/AgentLoopsTab.tsx")
    schedules_tab = read_repo("frontend/src/components/loops/SchedulesTab.tsx")
    custom_tab = read_repo("frontend/src/components/loops/CustomLoopsTab.tsx")
    history_tab = read_repo("frontend/src/components/loops/ExecutionHistoryTab.tsx")
    store = read_repo("frontend/src/stores/loopsStore.ts")
    api = read_repo("frontend/src/lib/api.ts")
    route = read_repo("backend/app/api/routes/loops.py")
    service = read_repo("backend/app/services/loop_execution_service.py")

    assert "const { activeProjectId } = useProjectStore();" in loops_view
    assert "fetchOverview(activeProjectId)" in loops_view
    assert "fetchHealth(activeProjectId)" in loops_view

    assert "const { activeProjectId } = useProjectStore();" in overview_tab
    assert "fetchHealth(activeProjectId)" in overview_tab
    assert "fetchOverview(activeProjectId)" in overview_tab

    assert "const { activeProjectId } = useProjectStore();" in agent_tab
    assert "fetchAgentLoops(activeProjectId)" in agent_tab
    assert "fetchAgents(activeProjectId || undefined)" in agent_tab
    assert "updateAgentConfig(agent.id, data, activeProjectId)" in agent_tab
    assert "pauseAgent(agent.id, activeProjectId)" in agent_tab
    assert "resumeAgent(agent.id, activeProjectId)" in agent_tab

    assert "fetchSchedules(activeProjectId)" in schedules_tab
    assert "project_id: activeProjectId" in schedules_tab
    assert "updateSchedule(schedule.id, { enabled: !schedule.enabled }, activeProjectId)" in schedules_tab
    assert "deleteSchedule(schedule.id, activeProjectId)" in schedules_tab
    assert "Select project..." not in schedules_tab

    assert "fetchHealth(activeProjectId)" in custom_tab
    assert "project_id: activeProjectId" in custom_tab
    assert "Select project..." not in custom_tab

    assert "fetchExecutions(1, activeProjectId)" in history_tab
    assert "fetchExecutions(executionPage - 1, activeProjectId)" in history_tab
    assert "fetchExecutions(executionPage + 1, activeProjectId)" in history_tab

    assert "fetchOverview: async (projectId) =>" in store
    assert "if (!projectId)" in store
    assert "const data = await loopsApi.overview(projectId)" in store
    assert "const data = await loopsApi.health(projectId)" in store
    assert "project_id: projectId" in store
    assert "await get().fetchSchedules(data.project_id)" in store
    assert "await get().fetchHealth(data.project_id)" in store

    assert "overview: (projectId: string)" in api
    assert "/api/loops/overview?project_id=" in api
    assert "agents: (projectId: string)" in api
    assert "/api/loops/agents?project_id=" in api
    assert "schedules: (projectId: string)" in api
    assert "/api/schedules?project_id=" in api
    assert "executionStats: (projectId: string" in api
    assert "health: (projectId: string)" in api

    assert "async def _require_loop_project_scope" in route
    assert 'raise HTTPException(status_code=400, detail="project_id is required")' in route
    assert "await require_project_access(db, request, scoped_project_id, min_role=min_role)" in route
    assert "ScheduledTask.project_id == project_id" in route
    assert "source_ids=source_ids" in route
    assert '"project_id": s.project_id' in route
    assert "source_ids: Optional[list[str]] = None" in service
    assert "LoopExecution.source_id.in_(source_ids) if source_ids else false()" in service


def test_websocket_project_events_are_active_project_filtered() -> None:
    hook = read_repo("frontend/src/hooks/useWebSocket.ts")
    websocket = read_repo("backend/app/api/websocket.py")

    assert 'import { useProjectStore } from "@/stores/projectStore";' in hook
    assert "if (activeProjectId) params.set(\"project_id\", activeProjectId);" in hook
    assert "active_project_id=active_project_id.strip() if active_project_id else None" in websocket
    assert "async def _resolve_project_id" in websocket
    assert "record.get(\"active_project_id\") == project_id" in websocket
    assert "if not self._connection_can_receive(record, project_id):" in websocket


def test_notifications_are_active_project_scoped() -> None:
    sidebar = read_repo("frontend/src/components/layout/Sidebar.tsx")
    view = read_repo("frontend/src/components/notifications/NotificationsView.tsx")
    list_tab = read_repo("frontend/src/components/notifications/NotificationListTab.tsx")
    store = read_repo("frontend/src/stores/notificationStore.ts")
    navigation = read_repo("frontend/src/lib/navigation.ts")
    route = read_repo("backend/app/api/routes/notifications.py")

    assert "const { activeProjectId } = useProjectStore();" in sidebar
    assert "fetchUnreadCount(activeProjectId)" in sidebar
    assert "setInterval(() => fetchUnreadCount(activeProjectId), 30_000)" in sidebar

    assert "const { activeProjectId } = useProjectStore();" in view
    assert "fetchNotifications(1, activeProjectId)" in view
    assert "fetchUnreadCount(activeProjectId)" in view

    assert "const { activeProjectId } = useProjectStore();" in list_tab
    assert "fetchNotifications(1, activeProjectId)" in list_tab
    assert "markAllRead(activeProjectId)" in list_tab
    assert "fetchNotifications(page - 1, activeProjectId)" in list_tab
    assert "fetchNotifications(page + 1, activeProjectId)" in list_tab
    assert "All projects" not in list_tab

    assert "fetchNotifications: async (page = 1, projectId) =>" in store
    assert "if (!projectId)" in store
    assert "params.project_id = projectId" in store
    assert "notification.project_id !== activeProjectId" in store

    assert '"backup",\n  "notifications",' in navigation
    assert "async def _require_notification_project_scope" in route
    assert 'raise HTTPException(status_code=400, detail="project_id is required")' in route
    assert "query = query.where(Notification.project_id == scoped_project_id)" in route
    assert "stmt = stmt.where(Notification.project_id == scoped_project_id)" in route
