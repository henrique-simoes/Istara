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


def test_interfaces_status_screens_and_handoff_require_active_project_scope() -> None:
    api = read_repo("frontend/src/lib/api.ts")
    store = read_repo("frontend/src/stores/interfacesStore.ts")
    screens_tab = read_repo("frontend/src/components/interfaces/ScreensGalleryTab.tsx")
    handoff_tab = read_repo("frontend/src/components/interfaces/HandoffTab.tsx")
    screens_route = read_repo("backend/app/api/routes/interfaces_screens.py")
    integrations_route = read_repo("backend/app/api/routes/interfaces_integrations.py")

    assert "status: (projectId: string)" in api
    assert "/api/interfaces/status?project_id=${encodeURIComponent(projectId)}" in api
    assert "list: (projectId: string)" in api
    assert "/api/interfaces/screens?project_id=${encodeURIComponent(projectId)}" in api
    assert "/api/interfaces/handoff/briefs?project_id=${encodeURIComponent(projectId)}" in api

    assert "if (!projectId)" in store
    assert "set({ status: null, error: null });" in store
    assert "set({ screens: [], selectedScreenId: null, loading: true, error: null });" in store
    assert "set({ briefs: [] });" in store

    assert "const scopedScreens = activeProjectId" in screens_tab
    assert "screens.filter((screen: any) => screen.project_id === activeProjectId)" in screens_tab
    assert "selectedScreen && selectedScreen.project_id === activeProjectId" in screens_tab

    assert "const scopedScreens = activeProjectId" in handoff_tab
    assert "screens.filter((screen: any) => screen.project_id === activeProjectId)" in handoff_tab
    assert "const scopedBriefs = activeProjectId" in handoff_tab
    assert "briefs.filter((brief: any) => brief.project_id === activeProjectId)" in handoff_tab
    assert "disabled={!activeProjectId || generatingBrief}" in handoff_tab

    assert "scoped_project_id = require_project_id(project_id)" in screens_route
    assert "await require_project_access(db, request, scoped_project_id, min_role=\"viewer\")" in screens_route
    assert "DesignScreen.project_id == scoped_project_id" in screens_route

    assert "scoped_project_id = require_project_id(project_id)" in integrations_route
    assert "DesignBrief.project_id == scoped_project_id" in integrations_route
    assert "DesignScreen.project_id == scoped_project_id" in integrations_route
    assert "scope\": \"project\"" in integrations_route


def test_interfaces_configuration_credentials_are_project_owned() -> None:
    api = read_repo("frontend/src/lib/api.ts")
    figma_tab = read_repo("frontend/src/components/interfaces/FigmaTab.tsx")
    onboarding = read_repo("frontend/src/components/interfaces/InterfacesOnboarding.tsx")
    common = read_repo("backend/app/api/routes/interfaces_common.py")
    integrations_route = read_repo("backend/app/api/routes/interfaces_integrations.py")
    config_model = read_repo("backend/app/models/interface_config.py")
    database = read_repo("backend/app/models/database.py")

    assert "stitch: (data: { api_key: string; project_id: string })" in api
    assert "figma: (data: { api_token: string; project_id: string })" in api
    assert "interfacesApi.figma.designSystem(fileKey.trim(), activeProjectId)" in figma_tab
    assert "disabled={!figmaUrl.trim() || !activeProjectId || importing}" in figma_tab
    assert "project_id: activeProjectId" in figma_tab
    assert "project_id: activeProjectId" in onboarding

    assert "await require_project_access(db, request, scoped_project_id, min_role=\"project_admin\")" in common
    assert "get_or_create_project_interface_config" in integrations_route
    assert "config.set_stitch_api_key(data.api_key)" in integrations_route
    assert "config.set_figma_api_token(data.api_token)" in integrations_route
    assert "_persist_env" not in integrations_route
    assert "settings.figma_api_token" not in integrations_route
    assert "settings.stitch_api_key" not in integrations_route

    assert "__tablename__ = \"project_interface_configs\"" in config_model
    assert "stitch_api_key_encrypted" in config_model
    assert "figma_api_token_encrypted" in config_model
    assert "encrypt_field" in config_model
    assert "decrypt_field" in config_model
    assert "\"app.models.interface_config\"" in database


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


def test_integrations_subtabs_defensively_filter_by_active_project() -> None:
    messaging = read_repo("frontend/src/components/integrations/MessagingTab.tsx")
    surveys = read_repo("frontend/src/components/integrations/SurveysTab.tsx")
    mcp_tab = read_repo("frontend/src/components/integrations/MCPTab.tsx")
    store = read_repo("frontend/src/stores/integrationsStore.ts")

    assert "const scopedChannelInstances = activeProjectId" in messaging
    assert "channelInstances.filter((c) => c.project_id === activeProjectId)" in messaging
    assert "const selectedInstance = scopedChannelInstances.find" in messaging
    assert "scopedChannelInstances.map((instance)" in messaging
    assert "channelInstances.map((instance)" not in messaging

    assert "const scopedSurveyIntegrations = activeProjectId" in surveys
    assert "surveyIntegrations.filter((integration) => integration.project_id === activeProjectId)" in surveys
    assert "scopedSurveyIntegrations.map((integration)" in surveys
    assert "surveyIntegrations.map((integration)" not in surveys

    assert "const scopedMCPClients = activeProjectId" in mcp_tab
    assert "mcpClients.filter((client) => client.project_id === activeProjectId)" in mcp_tab
    assert "scopedMCPClients.map((client)" in mcp_tab
    assert "mcpClients.map((client)" not in mcp_tab

    assert "set({ channelInstances: [], selectedInstanceId: null, channelLoading: true, error: null });" in store
    assert "set({ deploymentsList: [], selectedDeploymentId: null, deploymentLoading: true, error: null });" in store
    assert "set({ surveyIntegrations: [], surveyLoading: true, error: null });" in store
    assert "set({ mcpClients: [], mcpLoading: true, error: null });" in store


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
        "backend/app/api/routes/mcp.py": 'raise HTTPException(status_code=400, detail="project_id is required")',
    }

    for path, required_error in route_contracts.items():
        source = read_repo(path)
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


def test_agent_creation_proposals_require_active_project_scope() -> None:
    api = read_repo("frontend/src/lib/api.ts")
    view = read_repo("frontend/src/components/agents/AgentsView.tsx")
    route = read_repo("backend/app/api/routes/agents.py")
    factory = read_repo("backend/app/core/agent_factory.py")
    orchestrator = read_repo("backend/app/agents/orchestrator.py")
    governance = read_repo("backend/app/core/improvement_governance_evidence.py")
    meta = read_repo("backend/app/core/meta_hyperagent.py")

    assert "creationProposals: {" in api
    assert "all: (projectId: string, limit = 20)" in api
    assert "/api/agents/creation-proposals/all?project_id=${encodeURIComponent(projectId)}" in api
    assert "approve: (id: string, projectId: string)" in api
    assert "reject: (id: string, projectId: string" in api

    assert "agentsApi.creationProposals.all(activeProjectId)" in view
    assert "agentsApi.creationProposals.approve(p.id, activeProjectId)" in view
    assert "agentsApi.creationProposals.reject(p.id, activeProjectId)" in view
    assert "if (!activeProjectId)" in view

    assert "create: (data: {" in api
    assert "}, projectId: string)" in api
    assert "project_id: projectId" in api
    assert "createAgent: async (data, projectId)" in read_repo("frontend/src/stores/agentStore.ts")
    assert "useProjectStore" in read_repo("frontend/src/components/agents/CreateAgentWizard.tsx")

    assert "async def _require_agent_proposal_project_scope" in route
    assert 'raise HTTPException(status_code=400, detail="project_id is required")' in route
    assert "await require_project_access(db, request, scoped_project_id, min_role=min_role)" in route
    assert "await require_project_access(db, request, scoped_project_id, min_role=\"project_admin\")" in route
    assert "scope=\"project\"" in route
    assert "factory.get_pending_proposals(project_id=scoped_project_id)" in route
    assert "factory.get_all_proposals(limit, project_id=scoped_project_id)" in route
    assert "factory.approve_proposal(proposal_id, project_id=scoped_project_id)" in route
    assert "factory.reject_proposal(" in route and "project_id=scoped_project_id" in route
    assert "project_id=scoped_project_id" in route

    assert "project_id: str" in factory
    assert "project_id: str = \"\"" in factory
    assert "str(proposal.get(\"project_id\") or \"\") == scoped_project_id" in factory
    assert "project_id=task.project_id" in orchestrator
    assert '"project_id": task.project_id' in orchestrator
    assert "register_agent_creation_proposal(" in governance
    assert "project_id=scoped_project_id" in governance
    assert "factory.get_pending_proposals(project_id=scoped_project_id)" in meta


def test_meta_hyperagent_surfaces_require_active_project_scope() -> None:
    api = read_repo("frontend/src/lib/api.ts")
    view = read_repo("frontend/src/components/meta/MetaHyperagentView.tsx")
    route = read_repo("backend/app/api/routes/meta_hyperagent.py")
    core = read_repo("backend/app/core/meta_hyperagent.py")
    main = read_repo("backend/app/main.py")
    usage = read_repo("backend/app/skills/skill_usage.py")

    assert "status: (projectId: string)" in api
    assert "/api/meta-hyperagent/status?project_id=${encodeURIComponent(projectId)}" in api
    assert "proposals: (projectId: string)" in api
    assert "toggle: (enabled: boolean, projectId: string)" in api

    assert 'import { useProjectStore } from "@/stores/projectStore";' in view
    assert "const { activeProjectId } = useProjectStore();" in view
    assert "if (!activeProjectId)" in view
    assert "metaApi.status(activeProjectId)" in view
    assert "metaApi.proposals(activeProjectId)" in view
    assert "metaApi.toggle(!status.enabled, activeProjectId)" in view

    assert "async def _require_admin_project_scope" in route
    assert 'raise HTTPException(status_code=400, detail="project_id is required")' in route
    assert "await get_visible_project_or_404(db, request, scoped_project_id, min_role=\"viewer\")" in route
    assert "meta_hyperagent.get_pending_proposals(project_id=scoped_project_id)" in route
    assert "meta_hyperagent.start(project_id=scoped_project_id)" in route
    assert "project_id=project_id" in route

    assert "project_id: str = \"\"" in core
    assert "async def observe_cycle(self, project_id: str | None = None)" in core
    assert "reasoning_bank.summary(\n                project_id=scoped_project_id" in core
    assert "skill_manager.get_usage_stats(project_id=scoped_project_id)" in core
    assert "self._matches_project(p, scoped_project_id)" in core
    assert "register_meta_proposal(\n                        asdict(proposal),\n                        project_id=scoped_project_id" in core

    assert "Meta-Hyperagent is project-scoped" in main
    assert "mh.start()" not in main
    assert "project_id: str | None = None" in usage
    assert "projects = stats.setdefault(\"projects\", {})" in usage


def test_skills_surfaces_require_active_project_scope() -> None:
    api = read_repo("frontend/src/lib/api.ts")
    view = read_repo("frontend/src/components/skills/SkillsView.tsx")
    route = read_repo("backend/app/api/routes/skills.py")
    proposals = read_repo("backend/app/skills/skill_proposals.py")
    creation = read_repo("backend/app/skills/skill_creation.py")
    models = read_repo("backend/app/skills/skill_models.py")
    usage = read_repo("backend/app/skills/skill_usage.py")
    execution = read_repo("backend/app/core/agent_execution.py")
    governance = read_repo("backend/app/core/improvement_governance_evidence.py")

    assert "health: (projectId: string)" in api
    assert "/api/skills/health/all?project_id=${encodeURIComponent(projectId)}" in api
    assert "all: (projectId: string, limit = 50)" in api
    assert "/api/skills/proposals/all?project_id=${encodeURIComponent(projectId)}" in api
    assert "approve: (id: string, projectId: string)" in api
    assert "all: (projectId: string, limit = 20)" in api
    assert "/api/skills/creation-proposals/all?project_id=${encodeURIComponent(projectId)}" in api

    assert 'const { activeProjectId, canWriteActiveProject } = useProjectStore();' in view
    assert "projectId ? skillsApi.health(projectId)" in view
    assert "skillsApi.proposals.all(activeProjectId)" in view
    assert "skillsApi.creationProposals.all(activeProjectId)" in view
    assert "skillsApi.proposals.approve(id, activeProjectId)" in view
    assert "skillsApi.creationProposals.approve(id, activeProjectId)" in view
    assert "}, [activeProjectId, fetchCreationProposals, fetchProposals, fetchSkills]);" in view

    assert "async def _require_skill_project_scope" in route
    assert 'raise HTTPException(status_code=400, detail="project_id is required")' in route
    assert "await require_project_access(db, request, scoped_project_id, min_role=min_role)" in route
    assert "skill_manager.get_pending_proposals(project_id=scoped_project_id)" in route
    assert "skill_manager.get_all_proposals(limit, project_id=scoped_project_id)" in route
    assert "skill_manager.get_pending_creation_proposals(project_id=scoped_project_id)" in route
    assert "skill_manager.get_all_creation_proposals(" in route and "project_id=scoped_project_id" in route
    assert "skill_manager.approve_proposal(proposal_id, project_id=scoped_project_id)" in route
    assert "skill_manager.approve_creation_proposal(" in route and "project_id=scoped_project_id" in route

    assert "project_id: str = \"\"" in models
    assert "proposal.project_id == scoped_project_id" in proposals
    assert "proposal.project_id == scoped_project_id" in creation
    assert "def get_skill_health(self, name: str, project_id: str | None = None)" in usage
    assert "skill_manager.get_skill_health(skill.name, project_id=task.project_id)" in execution
    assert "project_id=task.project_id" in execution
    assert "async def register_skill_update_proposal(" in governance
    assert "project_id=scoped_project_id" in governance


def test_chat_sessions_require_active_project_scope() -> None:
    sessions_api = read_repo("frontend/src/lib/sessionsApi.ts")
    session_store = read_repo("frontend/src/stores/sessionStore.ts")
    chat_store = read_repo("frontend/src/stores/chatStore.ts")
    chat_view = read_repo("frontend/src/components/chat/ChatView.tsx")
    sidebar = read_repo("frontend/src/components/chat/ChatSessionsSidebar.tsx")
    context_dag = read_repo("frontend/src/components/memory/ContextDAGView.tsx")
    route = read_repo("backend/app/api/routes/sessions.py")

    assert "get: (sessionId: string, projectId: string)" in sessions_api
    assert "`/api/sessions/detail/${sessionId}?${projectQuery(projectId)}`" in sessions_api
    assert "update: (sessionId: string, projectId: string, data: Record<string, unknown>)" in sessions_api
    assert "delete: (sessionId: string, projectId: string)" in sessions_api
    assert "star: (sessionId: string, projectId: string)" in sessions_api

    assert 'const ACTIVE_SESSION_KEY_PREFIX = "istara-active-session:";' in session_store
    assert "function activeSessionKey(projectId: string): string" in session_store
    assert "activeSessionId: null" in session_store
    assert "const isProjectSwitch = get().projectId !== projectId;" in session_store
    assert "{ projectId, sessions: [], activeSessionId: null, loading: true }" in session_store
    assert "const hasCurrent = !isProjectSwitch && current" in session_store
    assert "const savedId = getSavedSessionId(projectId);" in session_store
    assert "sessionsApi.update(id, projectId, data)" in session_store
    assert "sessionsApi.delete(id, projectId)" in session_store
    assert "sessionsApi.star(id, projectId)" in session_store

    assert "sessionsApi.get(sessionId, projectId)" in chat_store
    assert 'set({ messages: [], streamingContent: "", error: null });' in chat_store
    assert "set({ messages: [], error: e.message });" in chat_store

    assert "updateSession(activeProjectId, activeSessionId, data)" in chat_view
    assert "const scopedSessions = sessions.filter((s) => s.project_id === projectId);" in sidebar
    assert "selectSession(projectId, session.id)" in sidebar
    assert "deleteSession(projectId, session.id)" in sidebar
    assert "toggleStar(projectId, session.id)" in sidebar

    assert "const scopedSessions = activeProjectId" in context_dag
    assert "sessions.filter((session) => session.project_id === activeProjectId)" in context_dag
    assert "const scopedActiveSessionId = scopedSessions.some" in context_dag
    assert "selectSession(activeProjectId, e.target.value)" in context_dag

    assert "def require_project_id(project_id: str | None) -> str:" in route
    assert 'raise HTTPException(status_code=400, detail="project_id is required")' in route
    assert "async def require_active_project_session" in route
    assert "ChatSession.project_id == scoped_project_id" in route
    assert "Message.project_id == scoped_project_id" in route


def test_agent_detail_status_and_log_routes_require_active_project_scope() -> None:
    view = read_repo("frontend/src/components/agents/AgentsView.tsx")
    visuals = read_repo("frontend/src/components/agents/AgentVisuals.tsx")
    api = read_repo("frontend/src/lib/api.ts")
    route = read_repo("backend/app/api/routes/agents.py")
    scope = read_repo("backend/app/api/agent_project_scope.py")

    assert "async def require_agent_project_access" in scope
    assert 'raise HTTPException(status_code=400, detail="project_id is required")' in scope
    assert "await require_agent_project_access(" in scope
    assert "def redact_global_agent_state_for_project_view" in scope
    assert 'redacted["memory"] = {}' in scope
    assert 'redacted["current_task"] = ""' in scope
    assert "await require_agent_by_id(db, request, agent_id, project_id=project_id)" in route
    assert "async def get_orchestrator_status(request: Request)" in route
    assert "require_admin_from_request(request)" in route

    assert "recentLog: (agentId?: string, limit = 50, projectId?: string | null)" in api
    assert "getIdentity: (id: string, projectId?: string | null)" in api
    assert "avatarUrl: (id: string, projectId?: string | null)" in api
    assert "heartbeat: (projectId?: string | null)" in api
    assert "messages: (id: string, projectId: string, limit = 50)" in api

    assert "agentsApi.recentLog(agentId, 5, activeProjectId)" in view
    assert "agentsApi.getIdentity(agent.id, activeProjectId)" in view
    assert "agentsApi.avatarUrl(agent.id, activeProjectId)" in visuals


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


def test_governed_evolution_requires_active_project_scope() -> None:
    view = read_repo("frontend/src/components/settings/GovernedEvolutionView.tsx")
    governance_api = read_repo("frontend/src/lib/improvementGovernanceApi.ts")
    archive_api = read_repo("frontend/src/lib/dgmhArchiveApi.ts")
    api = read_repo("frontend/src/lib/api.ts")
    governance_route = read_repo("backend/app/api/routes/improvement_governance.py")
    archive_route = read_repo("backend/app/api/routes/dgmh_archive.py")
    reasoning_route = read_repo("backend/app/api/routes/reasoning_bank.py")
    reasoning_core = read_repo("backend/app/core/reasoning_bank.py")
    archive_core = read_repo("backend/app/core/dgmh_archive.py")

    assert "if (!projectId)" in view
    assert "improvementGovernance.summary(projectId)" in view
    assert "improvementGovernance.proposals({ project_id: projectId" in view
    assert "dgmhArchive.variants({ project_id: projectId" in view
    assert "reasoningBank.summary(projectId)" in view
    assert "reasoningBank.memories({ project_id: projectId" in view
    assert "Select a project to view governed evolution." in view

    assert "summary: (projectId: string)" in governance_api
    assert "proposals: (params: {" in governance_api
    assert "project_id: string;" in governance_api
    assert "sandboxEvaluation: (id: string, projectId: string" in governance_api
    assert "summary: (projectId: string)" in archive_api
    assert "variants: (params: {" in archive_api
    assert "project_id: string;" in archive_api
    assert "approve: (id: string, projectId: string" in archive_api
    assert "summary: (projectId: string)" in api
    assert "memories: (params: { project_id: string" in api

    for route in (governance_route, archive_route, reasoning_route):
        assert "async def _require_admin_project_scope" in route
        assert 'raise HTTPException(status_code=400, detail="project_id is required")' in route
        assert "await get_visible_project_or_404(db, request, scoped_project_id" in route

    assert "include_global=False" in reasoning_route
    assert "include_global: bool = True" in reasoning_core
    assert "DGMHArchiveVariant.project_id == safe_project_id" in archive_core
    assert "DGMHArchiveVariant.project_id == project_id" in archive_core


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
