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


def test_permission_requests_bind_project_settings_to_active_project_scope() -> None:
    route = read_repo("backend/app/api/routes/permission_requests.py")
    api = read_repo("frontend/src/lib/api.ts")
    project_settings = read_repo("frontend/src/components/settings/ProjectSettingsView.tsx")
    admin_dashboard = read_repo("frontend/src/components/admin/AdminDashboard.tsx")

    assert "async def _get_project_permission_request" in route
    assert "PermissionRequest.id == request_id" in route
    assert "PermissionRequest.project_id == project_id" in route
    assert "project_id: str | None = None" in route
    assert 'raise HTTPException(status_code=400, detail="project_id is required")' in route
    assert "project_id or mine=true is required" not in route
    assert "elif is_global_admin(subject):\n        item = await _get_permission_request" in route

    assert "review: (id: string, data: { status: \"approved\" | \"rejected\"; review_note?: string }, projectId?: string)" in api
    assert "project_id=${encodeURIComponent(projectId)}" in api
    assert "/api/permission-requests/${id}${suffix}" in api

    assert "permissionRequests.list({ project_id: activeProjectId, status: \"pending\" })" in project_settings
    assert "permissionRequests.review(id, { status }, activeProjectId)" in project_settings
    assert "permissionRequests.list({ status: \"pending\" })" in admin_dashboard
    assert "permissionRequests.review(id, { status });" in admin_dashboard


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
    assert "setLoaded(false);" in source
    assert "let cancelled = false;" in source
    assert "if (!cancelled) setLoaded(true);" in source
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
    wizard = read_repo("frontend/src/components/integrations/DeploymentWizard.tsx")
    dashboard = read_repo("frontend/src/components/integrations/DeploymentDashboard.tsx")
    transcript = read_repo("frontend/src/components/integrations/ConversationTranscript.tsx")
    api = read_repo("frontend/src/lib/api.ts")

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
    assert "if (!activeProjectId || !deploymentType) return;" in wizard
    assert "fetchChannels(undefined, activeProjectId)" in wizard
    assert "channelInstances.filter((c) => c.is_active && c.project_id === activeProjectId)" in wizard
    assert "project_id: activeProjectId" in wizard
    assert "deploymentsApi.analytics(deployment.id, projectId)" in dashboard
    assert "deploymentsApi.conversations(deployment.id, projectId)" in dashboard
    assert "deploymentsApi.activate(deployment.id, projectId)" in dashboard
    assert "projectId={projectId}" in dashboard
    assert "deploymentsApi.transcript(deploymentId, conversationId, projectId)" in transcript
    assert "list: (projectId: string)" in api
    assert "get: (id: string, projectId: string)" in api
    assert "activate: (id: string, projectId: string)" in api
    assert "analytics: (id: string, projectId: string)" in api
    assert "/api/deployments/${id}?project_id=${encodeURIComponent(projectId)}" in api
    assert "/api/deployments/${id}/analytics?project_id=${encodeURIComponent(projectId)}" in api
    assert "/api/deployments/${deploymentId}/conversations/${conversationId}/transcript?project_id=${encodeURIComponent(projectId)}" in api


def test_backend_deployments_enforce_project_owned_channels_and_conversations() -> None:
    route = read_repo("backend/app/api/routes/deployments.py")
    service = read_repo("backend/app/services/deployment_service.py")
    inbound = read_repo("backend/app/services/inbound_processor.py")

    assert "async def _get_active_project_deployment_or_404" in route
    assert 'raise HTTPException(status_code=400, detail="project_id is required")' in route
    assert 'raise HTTPException(status_code=404, detail="Deployment not found")' in route
    assert "ResearchDeployment.id == deployment_id" in route
    assert "ResearchDeployment.project_id == scoped_project_id" in route
    assert "await require_project_access(db, request, scoped_project_id, min_role=min_role)" in route and "await get_active_project_or_404(\n        db, request, scoped_project_id, min_role=\"researcher\"" in route
    assert "async def _get_deployment_or_404" not in route
    assert "validate_channel_instances_for_project" in service
    assert "instance.project_id != project_id" in service
    assert "channel_instance_ids_json=json.dumps(scoped_channel_instance_ids)" in service
    assert "async def get_deployment(\n    db: AsyncSession,\n    deployment_id: str,\n    *,\n    project_id: str," in service
    assert "async def list_deployments(\n    db: AsyncSession,\n    *,\n    project_id: str," in service
    assert "async def activate_deployment(\n    db: AsyncSession,\n    deployment_id: str,\n    *,\n    project_id: str," in service
    assert "async def handle_response(\n    db: AsyncSession,\n    deployment_id: str,\n    conversation_id: str,\n    message_text: str,\n    *,\n    project_id: str," in service
    assert "deployment_service.activate_deployment(\n            db,\n            deployment_id,\n            project_id=deployment.project_id," in route
    assert "deployment_service.get_deployment_analytics(\n        db,\n        deployment_id,\n        project_id=deployment.project_id," in route
    assert "_get_project_deployment_conversation_or_404" in route
    assert "deployment_service.get_conversation(\n        db,\n        conversation_id,\n        deployment_id=deployment.id,\n        project_id=deployment.project_id," in route
    assert "conversation.project_id != deployment.project_id" in service
    assert "ResearchDeployment.project_id == project_id" in service
    assert "ChannelConversation.project_id == project_id" in service
    assert "ChannelMessage.project_id == deployment.project_id" in service
    assert "ChannelMessage.project_id == conversation.project_id" in service
    assert "ResearchDeployment.project_id == instance.project_id" in inbound
    assert "if instance.id in channel_ids:" in inbound


def test_research_integrity_by_id_routes_require_active_project_scope() -> None:
    codebooks_route = read_repo("backend/app/api/routes/codebooks.py")
    code_apps_route = read_repo("backend/app/api/routes/code_applications.py")
    api = read_repo("frontend/src/lib/researchIntegrityApi.ts")
    review_queue = read_repo("frontend/src/components/findings/CodeReviewQueue.tsx")

    assert "async def _get_project_codebook_or_404" in codebooks_route
    assert "async def _get_project_code_or_404" in codebooks_route
    assert 'raise HTTPException(status_code=400, detail="project_id is required")' in codebooks_route
    assert "Codebook.id == codebook_id, Codebook.project_id == scoped_project_id" in codebooks_route
    assert ".join(Codebook, Codebook.id == Code.codebook_id)" in codebooks_route
    assert "Code.id == code_id, Codebook.project_id == scoped_project_id" in codebooks_route
    assert "project_id: str | None = Query(default=None)" in codebooks_route

    assert "def _require_project_id(project_id: str | None) -> str:" in code_apps_route
    assert 'raise HTTPException(status_code=400, detail="project_id is required")' in code_apps_route
    assert "project_id: str | None = Query(default=None)" in code_apps_route
    assert "CodeApplication.id == application_id" in code_apps_route
    assert "CodeApplication.project_id == scoped_project_id" in code_apps_route
    assert "await require_project_access(db, request, scoped_project_id, min_role=\"researcher\")" in code_apps_route

    assert "review: (applicationId: string, reviewStatus: string, projectId: string" in api
    assert "/api/code-applications/${applicationId}/review?project_id=${encodeURIComponent(projectId)}" in api
    assert "codeAppApi.review(applicationId, status, projectId)" in review_queue
    assert "}, [projectId]);" in review_queue


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

    assert "const filterByProject = <T extends ProjectOwned>" in store
    assert "const dedupeProjectMCPClients = (items: MCPServerConfig[], projectId: string): MCPServerConfig[]" in store
    assert "const scoped = filterByProject(list, projectId);" in store
    assert "const scoped = dedupeProjectMCPClients(list, projectId);" in store
    assert "set({ channelInstances: [], selectedInstanceId: null, channelLoading: true, error: null });" in store
    assert "set({ deploymentsList: [], selectedDeploymentId: null, deploymentLoading: true, error: null });" in store
    assert "set({ surveyIntegrations: [], surveyLoading: true, error: null });" in store
    assert "set({ mcpClients: [], mcpLoading: true, error: null });" in store


def test_integrations_survey_detail_actions_require_active_project_scope() -> None:
    api = read_repo("frontend/src/lib/api.ts")
    surveys = read_repo("frontend/src/components/integrations/SurveysTab.tsx")
    setup = read_repo("frontend/src/components/integrations/SurveySetupWizard.tsx")
    route = read_repo("backend/app/api/routes/surveys.py")

    assert "delete: (id: string, projectId: string)" in api
    assert "surveys: (id: string, projectId: string)" in api
    assert "createSurvey: (id: string, data: any, projectId: string)" in api
    assert "sync: (id: string, projectId: string)" in api
    assert "responses: (id: string, projectId: string)" in api
    assert "/api/surveys/integrations/${id}?project_id=${encodeURIComponent(projectId)}" in api
    assert "/api/surveys/integrations/${id}/surveys?project_id=${encodeURIComponent(projectId)}" in api
    assert "/api/surveys/integrations/${id}/create?project_id=${encodeURIComponent(projectId)}" in api
    assert "/api/surveys/links/${id}/sync?project_id=${encodeURIComponent(projectId)}" in api
    assert "/api/surveys/links/${id}/responses?project_id=${encodeURIComponent(projectId)}" in api

    assert "if (!activeProjectId) return;" in surveys
    assert "setLinkedSurveys([]);" in surveys
    assert "links.filter((link) => link.project_id === activeProjectId)" in surveys
    assert "surveysApi.links.sync(linkId, activeProjectId)" in surveys
    assert "surveysApi.integrations.delete(id, activeProjectId)" in surveys
    assert "fetchSurveyIntegrations(activeProjectId)" in surveys

    assert "if (!selectedPlatform || !activeProjectId) return;" in setup
    assert "project_id: activeProjectId" in setup
    assert "disabled={testing || !activeProjectId}" in setup

    assert "async def _get_project_integration_or_404" in route
    assert "async def _get_project_link_or_404" in route
    assert "integration.project_id != scoped_project_id" in route
    assert "link.project_id != scoped_project_id" in route
    assert route.count('project_id: str | None = Query(None, description="Active project")') >= 5


def test_integrations_mcp_detail_actions_require_active_project_scope() -> None:
    api = read_repo("frontend/src/lib/api.ts")
    mcp_tab = read_repo("frontend/src/components/integrations/MCPTab.tsx")
    setup = read_repo("frontend/src/components/integrations/MCPServerSetup.tsx")
    route = read_repo("backend/app/api/routes/mcp.py")
    service = read_repo("backend/app/services/mcp_client_manager.py")
    server = read_repo("backend/app/mcp/server.py")
    security = read_repo("backend/app/services/mcp_security.py")

    assert "list: async (projectId: string): Promise<MCPServerConfig[]>" in api
    assert "delete: (id: string, projectId: string)" in api
    assert "discover: (id: string, projectId: string)" in api
    assert "tools: (id: string, projectId: string)" in api
    assert "call: (id: string, toolName: string, args: any, projectId: string)" in api
    assert "health: (id: string, projectId: string)" in api
    assert "allTools: async (projectId: string): Promise<any[]>" in api
    assert "list: (projectId: string)" in api
    assert "get: (id: string, projectId: string)" in api
    assert "connect: (id: string, envVars: Record<string, string> | undefined, projectId: string)" in api
    assert "/api/mcp/clients?project_id=${encodeURIComponent(projectId)}" in api
    assert "/api/mcp/clients/${id}?project_id=${encodeURIComponent(projectId)}" in api
    assert "/api/mcp/clients/${id}/discover?project_id=${encodeURIComponent(projectId)}" in api
    assert "/api/mcp/clients/${id}/tools?project_id=${encodeURIComponent(projectId)}" in api
    assert "/api/mcp/clients/${id}/call?project_id=${encodeURIComponent(projectId)}" in api
    assert "/api/mcp/clients/${id}/health?project_id=${encodeURIComponent(projectId)}" in api

    assert "if (!activeProjectId) return;" in mcp_tab
    assert "mcpApi.clients.discover(clientId, activeProjectId)" in mcp_tab
    assert "mcpApi.clients.delete(clientId, activeProjectId)" in mcp_tab
    assert "fetchMCPClients(activeProjectId)" in mcp_tab

    assert "projectId: string | null;" in setup
    assert "if (!projectId) return;" in setup
    assert "project_id: projectId" in setup
    assert "mcpApi.clients.discover(server.id, projectId)" in setup
    assert "mcpApi.clients.delete(serverId, projectId)" in setup
    assert "disabled={!url.trim() || !projectId || testing}" in setup
    assert "disabled={!url.trim() || !projectId || saving}" in setup

    assert "async def _get_project_client_or_404" in route
    assert "server.project_id != scoped_project_id" in route
    assert route.count('project_id: str | None = Query(None, description="Active project")') >= 5
    assert "await _get_project_client_or_404(\n        db, request, server_id, project_id" in route
    assert "removed = await unregister_server(db, server_id, project_id=scoped_project_id)" in route
    assert "source_id=f\"register:{server.id}\",\n            project_id=project_id," in route
    assert "source_id=f\"discover:{server_id}\",\n            project_id=scoped_project_id," in route
    assert "source_id=f\"call:{server_id}:{data.tool_name}\",\n            project_id=scoped_project_id," in route
    assert route.count("db=db,") >= 6

    assert "async def register_server(" in service and "project_id: str," in service
    assert "async def discover_tools(" in service and "project_id: str," in service
    assert "async def call_tool(" in service and "project_id: str," in service
    assert "async def health_check(" in service and "project_id: str," in service
    assert "async def unregister_server(" in service and "project_id: str," in service
    assert "async def list_servers(" in service and "project_id: str," in service
    assert "async def list_all_tools(db: AsyncSession, *, project_id: str)" in service
    assert "MCPServerConfig.project_id == scoped_project_id" in service

    assert "PROJECT_SCOPED_TOOLS" in security
    assert "project_id is required for" in security
    assert "No projects are allowed for" in security
    assert "allowed_ids = json.loads(policy.allowed_project_ids_json or \"[]\")" in server
    assert 'return {"projects": [], "count": 0}' in server
    assert "query = query.where(Project.id.in_(allowed_ids))" in server
    assert 'async def get_deployment_status(project_id: str)' in server
    assert ".where(ResearchDeployment.project_id == pid)" in server
    assert "async def search_memory(project_id: str, query: str" in server
    assert 'retrieve_context(\n                    args["project_id"]' in server
    assert 'return {"error": "Project is paused", "project_id": args["project_id"]}' in server


def test_integrations_messaging_detail_panels_require_active_project_scope() -> None:
    api = read_repo("frontend/src/lib/api.ts")
    messaging = read_repo("frontend/src/components/integrations/MessagingTab.tsx")
    messages_panel = read_repo("frontend/src/components/integrations/ChannelMessagesPanel.tsx")
    conversations_panel = read_repo("frontend/src/components/integrations/ChannelConversationsPanel.tsx")
    instance_card = read_repo("frontend/src/components/integrations/ChannelInstanceCard.tsx")
    setup_wizard = read_repo("frontend/src/components/integrations/ChannelSetupWizard.tsx")
    route = read_repo("backend/app/api/routes/channels.py")
    service = read_repo("backend/app/services/channel_service.py")

    assert "get: (id: string, projectId: string)" in api
    assert "update: (id: string, data: Record<string, any>, projectId: string)" in api
    assert "delete: (id: string, projectId: string)" in api
    assert "start: (id: string, projectId: string)" in api
    assert "stop: (id: string, projectId: string)" in api
    assert "health: (id: string, projectId: string)" in api
    assert "messages: (id: string, projectId: string" in api
    assert "conversations: (id: string, projectId: string)" in api
    assert "send: (id: string, data: { channel_id: string; text: string; metadata?: any }, projectId: string)" in api
    assert "list: (platform: string | undefined, projectId: string)" in api
    assert "channelProjectQuery(projectId)" in api

    assert "selectedInstance && activeProjectId" in messaging
    assert "projectId={activeProjectId}" in messaging
    assert "channelsApi.messages(channelId, projectId)" in messages_panel
    assert "channelsApi.conversations(channelId, projectId)" in conversations_panel
    assert "channelsApi.start(instance.id, projectId)" in instance_card
    assert "channelsApi.stop(instance.id, projectId)" in instance_card
    assert "channelsApi.start(instance.id, activeProjectId)" in setup_wizard
    assert "channelsApi.health(instance.id, activeProjectId)" in setup_wizard
    assert "channelsApi.delete(instanceId, activeProjectId)" in setup_wizard

    assert "async def _get_project_channel_or_404" in route
    assert "scoped_project_id = _require_project_id(project_id)" in route and "await get_active_project_or_404(\n        db, request, scoped_project_id, min_role=\"project_admin\"" in route
    assert "await require_project_access(db, request, scoped_project_id, min_role=min_role)" in route
    assert "instance is None or instance.project_id != scoped_project_id" in route
    assert "project_id: Optional[str] = Query(None, description=\"Active project\")" in route
    assert "project_id=scoped_project_id" in route

    assert "async def list_channel_instances(" in service and "project_id: str," in service
    assert "async def start_channel_instance(" in service and "project_id: str," in service
    assert "Project.is_paused.is_(False)" in service
    assert 'raise RuntimeError("Project is paused or not found")' in service
    assert "project_id does not match channel instance" in service
    assert "async def stop_channel_instance(" in service and "project_id: str," in service
    assert "async def health_check_instance(" in service and "project_id: str," in service
    assert "async def get_message_history(" in service and "project_id: str," in service
    assert "async def get_conversations(" in service and "project_id: str," in service
    assert "async def send_message(" in service and "project_id: str," in service
    assert "ChannelInstance.project_id == scoped_project_id" in service
    assert "ChannelMessage.project_id == scoped_project_id" in service
    assert "ChannelConversation.project_id == scoped_project_id" in service
    assert "resolved_project_id = (project_id or instance.project_id or \"\").strip()" in service
    assert "if not resolved_project_id:" in service
    assert "project_id=resolved_project_id" in service


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
    assert "const scoped = filterByProject(list, projectId);" in store
    assert "const scoped = dedupeProjectMCPClients(list, projectId);" in store

    assert 'query.set("project_id", projectId);' in api
    assert "return get<ResearchDeployment[]>(`/api/deployments${params}`)" in api
    assert "list: async (projectId: string): Promise<SurveyIntegration[]>" in api
    assert "list: (projectId: string) =>\n      get<SurveyLink[]>(`/api/surveys/links?project_id=${encodeURIComponent(projectId)}`)" in api
    assert "list: async (projectId: string): Promise<MCPServerConfig[]>" in api
    assert 'get<any>(`/api/mcp/clients?project_id=${encodeURIComponent(projectId)}`)' in api


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


def test_findings_search_and_lists_require_active_project_scope() -> None:
    api = read_repo("frontend/src/lib/api.ts")
    modal = read_repo("frontend/src/components/common/SearchModal.tsx")
    route = read_repo("backend/app/api/routes/findings.py")

    api_markers = ("nuggets: (projectId: string)", "facts: (projectId: string)", "insights: (projectId: string)", "recommendations: (projectId: string)", "/api/findings/nuggets?project_id=${encodeURIComponent(projectId)}", "evidenceChain: (findingType: string, findingId: string, projectId: string)", "/api/findings/${findingType}/${findingId}/evidence-chain?project_id=${encodeURIComponent(projectId)}", "linkEvidence: (findingType: string, findingId: string, linkId: string, linkType: string, projectId: string)", "/api/findings/${findingType}/${findingId}/link?project_id=${encodeURIComponent(projectId)}", 'delete: (type: "nugget" | "fact" | "insight" | "recommendation", id: string, projectId: string)')
    assert all(marker in api for marker in api_markers)

    modal_markers = ("if (!query.trim() || !activeProjectId) return;", "findingsApi.nuggets(activeProjectId)", "findingsApi.facts(activeProjectId)", "findingsApi.insights(activeProjectId)", "findingsApi.recommendations(activeProjectId)")
    assert all(marker in modal for marker in modal_markers)
    assert "findingsApi.nuggets()" not in modal
    assert "Search across all projects" not in modal

    route_markers = ("async def _require_project_scope", 'raise HTTPException(status_code=422, detail="project_id is required")', "Nugget.project_id == scoped_project_id", "Fact.project_id == scoped_project_id", "Insight.project_id == scoped_project_id", "Recommendation.project_id == scoped_project_id", "DesignDecision.project_id == scoped_project_id", "Nugget.project_id == project_id", "Fact.project_id == project_id", "Insight.project_id == project_id", "Recommendation.project_id == project_id", "DesignScreen.project_id == project_id", "async def _get_project_record_or_404", "model.id == record_id", "model.project_id == scoped_project_id", 'project_id: str | None = Query(None, description="Active project")', "Global findings search requires admin access")
    assert all(marker in route for marker in route_markers)

    drilldown = read_repo("frontend/src/components/findings/AtomicDrilldown.tsx")
    timeline = read_repo("frontend/src/components/agents/AgentTimeline.tsx")
    assert all(marker in drilldown for marker in ("findingsApi.evidenceChain(type, id, projectId)", "findingsApi.linkEvidence(activeFinding.type, activeFinding.id, linkId, linkInfo.linkType, projectId)"))
    assert "findingsApi.delete(entry.type, id, activeProjectId)" in timeline


def test_task_kanban_requires_active_project_scope() -> None:
    api = read_repo("frontend/src/lib/api.ts")
    store = read_repo("frontend/src/stores/taskStore.ts")
    kanban = read_repo("frontend/src/components/kanban/KanbanBoard.tsx")
    editor = read_repo("frontend/src/components/kanban/TaskEditor.tsx")
    timeline = read_repo("frontend/src/components/agents/AgentTimeline.tsx")
    route = read_repo("backend/app/api/routes/tasks.py")

    assert "list: (projectId: string, status?: string)" in api
    assert "new URLSearchParams({ project_id: projectId })" in api
    assert "const taskScopeParams = (projectId: string" in api
    assert "get: (id: string, projectId: string)" in api
    assert "update: (id: string, data: Record<string, unknown>, projectId: string)" in api
    assert "move: (id: string, status: string, projectId: string" in api
    assert "delete: (id: string, projectId: string)" in api
    assert "approve: (taskId: string, projectId: string" in api
    assert "qualitySummary: (taskId: string, projectId: string)" in api
    assert "createReport: (taskId: string, projectId: string)" in api
    assert "lock: (taskId: string, projectId: string" in api
    assert "unlock: (taskId: string, projectId: string" in api
    assert "/api/tasks/${id}?${taskScopeParams(projectId)}" in api
    assert "/api/tasks/${id}/move?${taskScopeParams(projectId" in api
    assert "/api/tasks/${taskId}/review/approve?${taskScopeParams(projectId)}" in api
    assert "fetchTasks: (projectId: string) => Promise<void>;" in store
    assert "moveTask: (taskId: string, status: TaskStatus, projectId: string) => Promise<void>;" in store
    assert "updateTask: (taskId: string, data: Record<string, unknown>, projectId: string) => Promise<void>;" in store
    assert "deleteTask: (taskId: string, projectId: string) => Promise<void>;" in store
    assert "if (!projectId)" in store
    assert "set({ tasks: [], loading: false, error: null });" in store
    assert "data.filter((task) => task.project_id === projectId)" in store
    assert "tasksApi.move(taskId, status, projectId)" in store
    assert "tasksApi.update(taskId, data, projectId)" in store
    assert "if (activeProjectId) fetchTasks(activeProjectId);" in kanban
    assert "projectId={activeProjectId}" in kanban
    assert "moveTask(task.id, status === \"done\" ? \"in_review\" : status, activeProjectId)" in kanban
    assert "moveTask(taskId, newStatus, activeProjectId)" in kanban
    assert "deleteTask(deleteConfirm, activeProjectId)" in kanban
    assert "activeProjectId !== task.project_id" in editor
    assert "tasksApi.qualitySummary(task.id, activeProjectId)" in editor
    assert "approveTask(task.id, activeProjectId" in editor
    assert "tasksApi.createReport(task.id, activeProjectId)" in editor
    assert "tasksApi.list(activeProjectId)" in timeline
    assert "tasksApi.delete(id, activeProjectId)" in timeline

    assert "def _require_project_id(project_id: str | None) -> str:" in route
    assert "async def _get_project_task_or_404" in route
    assert "async def _get_authorized_project_task_or_404" in route
    assert 'raise HTTPException(status_code=422, detail="project_id is required")' in route
    assert "await get_visible_project_or_404(db, request, scoped_project_id, min_role=\"viewer\")" in route
    assert "await get_visible_project_or_404(db, request, scoped_project_id, min_role=min_role)" in route
    assert "select(Task).where(Task.id == task_id, Task.project_id == project_id)" in route
    assert "return await _get_project_task_or_404(db, task_id, scoped_project_id)" in route
    assert "Task.project_id == scoped_project_id" in route
    assert "is_global_admin" not in route


def test_compute_pool_requires_active_project_scope() -> None:
    api = read_repo("frontend/src/lib/api.ts")
    store = read_repo("frontend/src/stores/computeStore.ts")
    view = read_repo("frontend/src/components/common/ComputePoolView.tsx")
    route = read_repo("backend/app/api/routes/compute.py")
    admin_route = read_repo("backend/app/api/routes/admin.py")
    node_invocation = read_repo("backend/app/core/compute_node_invocation.py")
    chat_stream_body = node_invocation.split("    async def chat_stream(", 1)[1].split(
        "    async def embed(",
        1,
    )[0]

    assert "nodes: (projectId: string)" in api
    assert "stats: (projectId: string)" in api
    assert "modelWarnings: (projectId: string)" in api
    assert "/api/compute/stats?project_id=${encodeURIComponent(projectId)}" in api
    assert "/api/compute/nodes?project_id=${encodeURIComponent(projectId)}" in api
    assert "/api/compute/model-warnings?project_id=${encodeURIComponent(projectId)}" in api

    assert "fetchStats: (projectId?: string | null) => Promise<void>;" in store
    assert "if (!projectId)" in store
    assert "set({ stats: null, loading: false, error: null });" in store
    assert "const data = await compute.stats(projectId);" in store
    assert "const data = await compute.nodes(projectId);" in store

    assert "fetchStats(activeProjectId)" in view
    assert "computeApi.modelWarnings(activeProjectId)" in view
    assert "node.health_state || node.state" in view
    assert "NOT_READY_NODE_STATES.has(readinessState)" in view
    assert "node.is_healthy && (!readinessState || READY_NODE_STATES.has(readinessState))" in view

    assert "def _require_project_id(project_id: str | None) -> str:" in route
    assert 'raise HTTPException(status_code=400, detail="project_id is required")' in route
    assert "await get_visible_project_or_404(db, request, scoped_project_id, min_role=\"viewer\")" in route
    assert "compute_registry.get_stats(project_id=scoped_project_id)" in route
    assert "compute_registry.get_warnings(project_id=scoped_project_id)" in route
    assert "current_user_context_for_payload" in route
    assert "jwt_user_context = await current_user_context_for_payload(db, jwt_payload)" in route
    assert 'authenticated_role = str(jwt_payload.get("role", ""))' not in route
    assert "user = await db.get(User, user_id)" in route
    assert "authorized_project_count" in route
    assert "is_global_admin" not in route
    assert "all nodes for global admins" not in route
    assert "project_id = self._authorized_project_for_content_dispatch(project_id)" in chat_stream_body

    assert 'computeStats: () => get<any>("/api/admin/compute/stats")' in api
    assert '@router.get("/compute/stats")' in admin_route
    assert "async def admin_compute_stats(request: Request):" in admin_route
    assert "require_global_admin(request)" in admin_route
    assert "compute_registry.get_stats(project_id=None)" in admin_route


def test_llm_server_inventory_and_health_checks_require_global_admin_access() -> None:
    route = read_repo("backend/app/api/routes/llm_servers.py")
    settings_route = read_repo("backend/app/api/routes/settings.py")
    settings_view = read_repo("frontend/src/components/common/SettingsView.tsx")
    assert (
        'async def list_llm_servers(request: Request, db: AsyncSession = Depends(get_db)):\n'
        '    """List all registered LLM servers."""\n'
        '    require_global_role(request, "admin")'
    ) in route
    assert (
        "async def health_check_server(\n"
        "    server_id: str, request: Request, db: AsyncSession = Depends(get_db)\n"
        "):\n"
        '    """Run a health check on a specific LLM server."""\n'
        '    require_global_role(request, "admin")'
    ) in route
    assert route.count('require_global_role(request, "admin")') >= 6
    status_body = settings_route.split('@router.get("/settings/status")', 1)[1]; assert 'def _cached_llm_readiness() -> tuple[bool, bool]:' in settings_route
    assert all(marker not in status_body for marker in ("await ollama.health()", '"provider": settings.llm_provider', '"config": {'))
    assert all(marker in settings_route for marker in ("async def get_hardware_info(request: Request):", "async def get_models(request: Request):", "async def maintenance_status(request: Request):", "async def integrations_status(request: Request):", "async def vector_health(request: Request):", "async def check_data_integrity(request: Request, db: AsyncSession = Depends(get_db)):", "async def switch_model(model_name: str, request: Request):", "async def switch_provider(provider: str, request: Request):"))
    assert all(marker in settings_view for marker in ("const capabilities = useRoleCapabilities();", "const canManageInfrastructure = capabilities.canManageLlmInfrastructure;", "canManageInfrastructure ? settingsApi.hardware() : Promise.resolve(null)", "canManageInfrastructure ? settingsApi.models() : Promise.resolve(null)", "const canManageLLMServers = !teamMode || user?.role === \"admin\";", "Global admin access is required to manage shared provider endpoints."))

def test_autoresearch_project_surfaces_require_active_project_scope() -> None:
    api = read_repo("frontend/src/lib/api.ts"); store = read_repo("frontend/src/stores/autoresearchStore.ts")
    dashboard = read_repo("frontend/src/components/autoresearch/ExperimentDashboard.tsx"); history = read_repo("frontend/src/components/autoresearch/ExperimentHistory.tsx")
    leaderboard = read_repo("frontend/src/components/autoresearch/LeaderboardTab.tsx"); route = read_repo("backend/app/api/routes/autoresearch.py")
    engine = read_repo("backend/app/core/autoresearch_engine.py"); runner_base = read_repo("backend/app/core/autoresearch_runners/__init__.py"); question_bank = read_repo("backend/app/core/autoresearch_runners/question_bank.py")

    assert all(
        marker in store
        for marker in ("autoresearch.status(projectId)", "autoresearch.leaderboard(projectId)", "project_id: params.project_id")
    )
    assert all(
        marker in dashboard
        for marker in ("fetchStatus(activeProjectId)", "fetchExperiments({ project_id: activeProjectId, limit: 20 })", "project_id: activeProjectId", "stopLoop(activeProjectId)")
    )
    assert "params.project_id = activeProjectId" in history
    assert "fetchLeaderboard(activeProjectId)" in leaderboard

    assert all(
        marker in api
        for marker in ("status: (projectId: string)", "/api/autoresearch/status?project_id=", 'p.set("project_id", params.project_id);', "/api/autoresearch/leaderboard?project_id=", "/api/autoresearch/stop?project_id=")
    )

    assert all(
        marker in route
        for marker in ("async def _require_project_scope", 'raise HTTPException(status_code=400, detail="project_id is required")', "operational_metrics\": await _build_operational_metrics(db, project_id)", "return await engine.get_leaderboard(project_id=project_id)", "Task.project_id == project_id", "ResearchDeployment.project_id == project_id", "TelemetrySpan.project_id == project_id", "ScheduledTask.project_id == project_id")
    )
    assert "await engine.get_experiments(" in route and "project_id=project_id" in route
    assert all(
        marker in engine
        for marker in ('"project_id": project_id', 'bind_project(project_id)', "AutoresearchExperiment.project_id == project_id", "TelemetrySpan.project_id == project_id")
    )
    assert all(marker in runner_base for marker in ("def bind_project(self, project_id: str) -> None:", 'raise RuntimeError("project_id is required for autoresearch runner")'))
    assert all(marker in question_bank for marker in ("ResearchDeployment.project_id == project_id", "project_id=self.require_project_id()"))


def test_agents_a2a_project_view_passes_active_project_id() -> None:
    view = read_repo("frontend/src/components/agents/AgentsView.tsx")
    store = read_repo("frontend/src/stores/agentStore.ts")
    api = read_repo("frontend/src/lib/api.ts")
    route = read_repo("backend/app/api/routes/agents.py")
    a2a_route = read_repo("backend/app/api/routes/a2a.py")
    a2a_service = read_repo("backend/app/services/a2a.py")
    lifecycle = read_repo("backend/app/core/agent_lifecycle.py")
    sub_worker = read_repo("backend/app/core/sub_agent_worker.py")

    assert "const { activeProjectId } = useProjectStore();" in view
    assert "fetchA2ALog(activeProjectId)" in view
    assert "fetchAgents(activeProjectId || undefined)" in view
    assert "if (!projectId)" in store
    assert "fetchA2ALog: async (projectId) =>" in store
    assert "if (!projectId)" in store
    assert "set({ a2aMessages: [], error: null });" in store
    assert "(message.project_id || metadataProjectId) === projectId" in store
    assert "const data = await agentsApi.a2aLog(projectId, 100);" in store
    assert "a2aLog: (projectId: string, limit = 100)" in api
    assert 'params.set("project_id", projectId);' in api
    assert 'raise HTTPException(status_code=400, detail="project_id is required")' in route
    assert "await require_project_access(db, request, project_id, min_role=\"viewer\")" in route
    assert "await require_project_access(db, request, project_id, min_role=\"viewer\")" in route
    assert "messages = await a2a.get_full_log(db, limit, project_id=project_id)" in route
    assert '"project_id is required for A2A agent/discover."' in a2a_route
    assert "agents = filter_agent_dicts_for_project(agents, project_id, request)" in a2a_route
    assert "min_role=\"viewer\"" in a2a_route
    assert "async def get_project_inbox(" in a2a_service
    assert "project_id: Mapped[str] = mapped_column(String(36), default=\"\", index=True)" in read_repo("backend/app/models/agent.py")
    assert "project_id=scoped_project_id" in a2a_service
    assert "metadata_project_ids and metadata_project_ids != {scoped_project_id}" in a2a_service
    assert "async def mark_read(" in a2a_service and "project_id: str," in a2a_service
    assert "_require_project_id(project_id, \"A2A message mutations\")" in a2a_service
    assert "resolved_project_ids = await _resolve_message_project_ids(db, messages)" in a2a_service
    assert "claims[\"row\"] = row_project_id" in a2a_service
    assert "async def get_conversation_thread(" in a2a_service
    assert "project_id: str," in a2a_service
    assert "project_id=task.project_id" in lifecycle
    assert "await get_project_inbox(db, self._agent_id, unread_only=True, limit=3)" in lifecycle
    assert "await mark_read(db, msg_id, project_id=msg_project_id)" in lifecycle
    assert "await get_project_inbox(db, self._agent_id, unread_only=True, limit=3)" in sub_worker
    assert "project_id=project_id" in sub_worker


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
    assert "async def _require_admin_active_project_scope" in route
    assert 'raise HTTPException(status_code=400, detail="project_id is required")' in route
    assert "await get_visible_project_or_404(db, request, scoped_project_id, min_role=\"viewer\")" in route
    assert "await get_active_project_or_404(db, request, scoped_project_id, min_role=\"viewer\")" in route
    assert "meta_hyperagent.get_pending_proposals(project_id=scoped_project_id)" in route
    assert "meta_hyperagent.start(project_id=scoped_project_id)" in route
    assert "project_id=project_id" in route

    assert "project_id: str = \"\"" in core
    assert "async def observe_cycle(self, project_id: str | None = None)" in core
    assert "reasoning_bank.summary(\n                project_id=scoped_project_id" in core
    assert "skill_manager.get_usage_stats(project_id=scoped_project_id)" in core
    assert "project_learning_count" in core
    assert "learning_count >= 10" in core
    assert "self._matches_project(p, scoped_project_id)" in core
    assert "register_meta_proposal(\n                        asdict(proposal),\n                        project_id=scoped_project_id" in core

    assert "Meta-Hyperagent is project-scoped" in main
    assert "mh.start()" not in main
    assert "project_id: str | None = None" in usage
    assert "projects = stats.setdefault(\"projects\", {})" in usage
    assert "Ignoring automatic global lifecycle mutation" in usage


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
    assert "async def _require_active_skill_project_scope" in route
    assert 'raise HTTPException(status_code=400, detail="project_id is required")' in route
    assert "await require_project_access(db, request, scoped_project_id, min_role=min_role)" in route
    assert "await get_active_project_or_404(" in route
    assert "skill_manager.get_pending_proposals(project_id=scoped_project_id)" in route
    assert "skill_manager.get_all_proposals(limit, project_id=scoped_project_id)" in route
    assert "skill_manager.get_pending_creation_proposals(project_id=scoped_project_id)" in route
    assert "skill_manager.get_all_creation_proposals(" in route and "project_id=scoped_project_id" in route
    assert "skill_manager.approve_proposal(proposal_id, project_id=scoped_project_id)" in route
    assert "skill_manager.approve_creation_proposal(" in route and "project_id=scoped_project_id" in route

    assert "project_id: str = \"\"" in models
    assert "project_id is required for skill improvement proposals" in proposals
    assert "project_id is required for skill creation proposals" in creation
    assert "proposal.project_id == scoped_project_id" in proposals
    assert "proposal.project_id == scoped_project_id" in creation
    assert "def get_skill_health(self, name: str, project_id: str | None = None)" in usage
    assert "skill_manager.get_skill_health(skill.name, project_id=task.project_id)" in execution
    assert "project_id=task.project_id" in execution
    assert "async def register_skill_update_proposal(" in governance
    assert "project_id is required for {source_system} proposals" in governance
    assert '"skill_evolution"' in governance
    assert '"memento_skill_factory"' in governance
    assert "project_id=scoped_project_id" in governance


def test_background_autonomous_processes_are_project_safe_by_default() -> None:
    """Startup QA loops must not create global activity or LLM work by default."""
    config = read_repo("backend/app/config.py")
    main = read_repo("backend/app/main.py")
    orchestrator = read_repo("backend/app/agents/orchestrator.py")
    scheduler = read_repo("backend/app/core/scheduler.py")
    agents_route = read_repo("backend/app/api/routes/agents.py")
    learning = read_repo("backend/app/core/agent_learning.py")

    assert "autonomous_quality_agents_enabled: bool = False" in config
    assert "autonomous_quality_agents_enabled = app_settings.autonomous_quality_agents_enabled" in main
    assert "Autonomous quality audit/simulation agents disabled" in main
    assert "devops_agent.start_task_worker()" in main
    assert "ui_audit_agent.start_task_worker()" in main
    assert "ux_eval_agent.start_task_worker()" in main
    assert "user_sim_agent.start_task_worker()" in main

    assert ".join(Project, Project.id == Task.project_id)" in orchestrator
    assert "Project.is_paused.is_(False)" in orchestrator
    assert ".outerjoin(Project, Project.id == ScheduledTask.project_id)" in scheduler
    assert "Project.is_paused.is_(False)" in scheduler

    assert "async def get_ux_eval(request: Request)" in agents_route
    assert "async def get_sim_report(request: Request)" in agents_route
    assert "require_admin_from_request(request)" in agents_route

    assert "project_id is required" in learning
    assert "AgentLearning.project_id == scoped_project_id" in learning
    assert "append_learning(" not in learning


def test_self_evolution_routes_and_engine_require_active_project_scope() -> None:
    route = read_repo("backend/app/api/routes/agents.py")
    engine = read_repo("backend/app/core/self_evolution.py")
    api = read_repo("frontend/src/lib/api.ts")
    docs = read_repo("docs/features/content/agents/detail/architecture.md")

    assert "async def _require_self_evolution_project_scope" in route
    assert 'raise HTTPException(status_code=400, detail="project_id is required")' in route
    assert "await get_active_project_or_404(" in route
    assert "await require_agent_by_id(db, request, agent_id, project_id=scoped_project_id)" in route
    assert "self_evolution.scan_for_promotions(" in route
    assert "project_id=scoped_project_id" in route
    assert "self_evolution.scan_all_agents(project_id=scoped_project_id)" in route

    assert "def _normalize_project_id(project_id: str | None) -> str:" in engine
    assert "async def _is_project_active(self, project_id: str) -> bool:" in engine
    assert "Project is paused or not found" in engine
    assert '"Skipping self-evolution scan for %s because project_id is required"' in engine
    assert "AgentLearning.project_id == scoped_project_id" in engine
    assert '"project_id": scoped_project_id' in engine
    assert '"Learning not found for project"' in engine
    assert "scan_all_agents(self, project_id: str | None = None)" in engine
    assert 'logger.warning("Skipping all-agent evolution scan because project_id is required")' in engine
    assert "Agent.project_id == scoped_project_id" in engine

    assert "scan: (projectId: string)" in api
    assert "candidates: (id: string, projectId: string)" in api
    assert "promote: (id: string, learningId: number, projectId: string" in api
    assert "auto: (id: string, projectId: string)" in api
    assert "project_id=${encodeURIComponent(projectId)}" in api

    assert "Self-evolution candidate scans, auto-evolution, and promotion mutations require an explicit active project id." in docs


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


def test_context_hierarchy_project_composition_is_project_local() -> None:
    core = read_repo("backend/app/core/context_hierarchy.py")
    route = read_repo("backend/app/api/routes/context_hierarchy.py")
    preview = read_repo("frontend/src/components/common/ContextPreview.tsx")
    docs = read_repo("docs/features/content/context/editor/architecture.md")

    assert "scoped_project_id = self._normalize_project_id(project_id)" in core
    assert "query = query.where(ContextDocument.project_id == scoped_project_id)" in core
    assert "(ContextDocument.project_id == project_id) |" not in core
    assert "(ContextDocument.project_id == \"\") |" not in core
    assert "ContextDocument.level <= 2" not in core

    route_markers = ("scoped_project_id = str(project_id or \"\").strip()", "await require_project_access(db, request, scoped_project_id, min_role=\"viewer\")", "await require_project_access(db, request, scoped_project_id, min_role=\"researcher\")", "async def _get_active_context_or_404", "ContextDocument.id == doc_id,\n                ContextDocument.project_id == scoped_project_id", 'raise HTTPException(status_code=400, detail="project_id is required")', "project_id: str | None = Query(None, description=\"Active project\")", "project_id=scoped_project_id", "composed = await context_hierarchy.compose_context(db, scoped_project_id)")
    assert all(marker in route for marker in route_markers)

    assert "Composed from active project context layers" in preview
    assert "context hierarchy prompt composition is project-local" in docs


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
    assert "scoped_project_id = agent_project_id(agent)" in route
    assert "project_id=scoped_project_id" in route
    assert '"requested_scope": "universal"' in route
    assert 'return {"status": "requested", "agent_id": agent_id, "project_id": scoped_project_id}' in route
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
    scheduler_route = read_repo("backend/app/api/routes/scheduler.py")
    scheduler = read_repo("backend/app/core/scheduler.py")
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
    assert "loopsApi.updateSchedule(scheduleId, data, scopedProjectId)" in store
    assert "loopsApi.deleteSchedule(scheduleId, scopedProjectId)" in store
    assert "await get().fetchSchedules(data.project_id)" in store
    assert "await get().fetchHealth(data.project_id)" in store

    assert "overview: (projectId: string)" in api
    assert "/api/loops/overview?project_id=" in api
    assert "agents: (projectId: string)" in api
    assert "/api/loops/agents?project_id=" in api
    assert "schedules: (projectId: string)" in api
    assert "/api/schedules?project_id=" in api
    assert "getSchedule: (scheduleId: string, projectId: string)" in api
    assert "/api/schedules/${scheduleId}?project_id=${encodeURIComponent(projectId)}" in api
    assert "updateSchedule: (scheduleId: string, data:" in api
    assert "deleteSchedule: (scheduleId: string, projectId: string)" in api
    assert "executionStats: (projectId: string" in api
    assert "health: (projectId: string)" in api

    assert "async def _require_loop_project_scope" in route
    assert 'raise HTTPException(status_code=400, detail="project_id is required")' in route
    assert "await require_project_access(db, request, scoped_project_id, min_role=min_role)" in route
    assert "ScheduledTask.project_id == project_id" in route
    assert "source_ids=source_ids" in route
    assert '"project_id": s.project_id' in route
    assert "def _require_project_id(project_id: str | None) -> str:" in scheduler_route
    assert 'raise HTTPException(status_code=400, detail="project_id is required")' in scheduler_route
    assert "async def _get_project_schedule_or_404" in scheduler_route
    assert "ScheduledTask.project_id == scoped_project_id" in scheduler_route
    assert 'project_id: str | None = Query(None, description="Active project")' in scheduler_route
    assert "source_ids: Optional[list[str]] = None" in service
    assert "project_id: Optional[str] = None" in service
    assert "LoopExecution.project_id == scoped_project_id" in service
    assert "def _execution_matches_project" in service
    assert "LoopExecution.source_id.in_(source_ids) if source_ids else false()" in service
    assert "project_id=task.project_id" in scheduler


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
    assert "include_global: bool = False" in reasoning_core
    assert "DGMHArchiveVariant.project_id == safe_project_id" in archive_core
    assert "DGMHArchiveVariant.project_id == project_id" in archive_core


def test_websocket_project_events_are_active_project_filtered() -> None:
    hook = read_repo("frontend/src/hooks/useWebSocket.ts")
    websocket = read_repo("backend/app/api/websocket.py")

    assert 'import { useProjectStore } from "@/stores/projectStore";' in hook
    assert "if (activeProjectId) params.set(\"project_id\", activeProjectId);" in hook
    assert "event.code === 4001 || event.code === 4003" in hook
    assert "active_project_id=active_project_id" in websocket
    assert "async def _can_subscribe_to_project" in websocket
    assert "await current_user_context_for_payload(db, payload)" in websocket
    assert "Project access denied" in websocket
    assert "async def _resolve_project_id" in websocket
    assert '"agent_id"' in websocket and '"from_agent_id"' in websocket and '"to_agent_id"' in websocket
    assert '"deployment_id"' in websocket and '"deploymentId"' in websocket
    assert "PROJECT_BOUND_EVENT_TYPES" in websocket
    assert "Dropping project-bound websocket event without resolvable project_id" in websocket
    assert "record.get(\"active_project_id\") != project_id" in websocket
    assert "await self._connection_can_receive(db, record, project_id)" in websocket
    assert "function shouldDeliverEvent" in hook
    assert "PROJECT_BOUND_EVENT_TYPES.has(event.type)" in hook


def test_notifications_are_active_project_scoped() -> None:
    sidebar = read_repo("frontend/src/components/layout/Sidebar.tsx")
    view = read_repo("frontend/src/components/notifications/NotificationsView.tsx")
    list_tab = read_repo("frontend/src/components/notifications/NotificationListTab.tsx")
    category_filter = read_repo("frontend/src/components/notifications/CategoryFilter.tsx")
    prefs_tab = read_repo("frontend/src/components/notifications/NotificationPrefsTab.tsx")
    store = read_repo("frontend/src/stores/notificationStore.ts")
    api = read_repo("frontend/src/lib/notificationApi.ts")
    types = read_repo("frontend/src/lib/types.ts")
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
    assert "markRead(notification.id, activeProjectId)" in list_tab and "deleteNotification(notification.id, activeProjectId)" in list_tab
    assert "fetchNotifications(page - 1, activeProjectId)" in list_tab
    assert "fetchNotifications(page + 1, activeProjectId)" in list_tab
    assert "All projects" not in list_tab

    assert "fetchNotifications: async (page = 1, projectId) =>" in store
    assert "if (!projectId)" in store
    assert "params.project_id = projectId" in store
    assert "markRead: async (id, projectId) =>" in store and "await notificationsApi.markRead(id, projectId)" in store
    assert "deleteNotification: async (id, projectId) =>" in store and "await notificationsApi.delete(id, projectId)" in store
    assert "notification.project_id !== activeProjectId" in store

    assert "markRead: (id: string, projectId: string)" in api and "unreadCount: (projectId: string)" in api and "markAllRead: (projectId: string)" in api and "delete: (id: string, projectId: string)" in api and "JSON.stringify({ project_id: projectId })" in api

    assert '"backup",\n  "notifications",' in navigation
    assert all(marker in route for marker in ("async def _require_notification_project_scope", "async def _get_project_notification_or_404", "await require_project_access(db, request, scoped_project_id, min_role=min_role)", 'scoped_project_id = project_id.strip() if project_id else ""', 'raise HTTPException(status_code=400, detail="project_id is required")', "query = query.where(Notification.project_id == scoped_project_id)", ".where(Notification.project_id == scoped_project_id)", "Notification.id == notification_id", "Notification.project_id == scoped_project_id"))
    assert all(marker not in route for marker in ("from app.config import settings", "get_subject", "is_global_admin", "explicit admin-global scope"))
    assert '"agent_promotion"' in route and '"agent_promotion"' in types and "agent_promotion:" in list_tab
    assert '{ id: "agent_promotion", label: "Agent Promotion" }' in category_filter and '{ id: "agent_promotion", label: "Agent Promotion" }' in prefs_tab
