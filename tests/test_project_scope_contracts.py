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
    assert "fetchChannels(undefined, activeProjectId || undefined)" in source
    assert "fetchDeployments(activeProjectId || undefined)" in source
    assert "fetchSurveyIntegrations(activeProjectId || undefined)" in source
    assert "const scopedChannels = activeProjectId" in source
    assert "const scopedDeployments = activeProjectId" in source
    assert "const scopedSurveyIntegrations = activeProjectId" in source
    assert "...scopedChannels.slice(0, 3)" in source
    assert "...scopedDeployments.slice(0, 3)" in source
    assert "...channelInstances.slice(0, 3)" not in source
    assert "...deploymentsList.slice(0, 3)" not in source


def test_integrations_store_and_api_accept_project_filters() -> None:
    store = read_repo("frontend/src/stores/integrationsStore.ts")
    api = read_repo("frontend/src/lib/api.ts")

    assert "fetchChannels: (platform?: string, projectId?: string) => Promise<void>;" in store
    assert "fetchDeployments: (projectId?: string) => Promise<void>;" in store
    assert "fetchSurveyIntegrations: (projectId?: string) => Promise<void>;" in store
    assert "const list = await channels.list(platform, projectId);" in store
    assert "const list = await deployments.list(projectId);" in store
    assert "const list = await surveys.integrations.list(projectId);" in store

    assert 'if (projectId) query.set("project_id", projectId);' in api
    assert "return get<ResearchDeployment[]>(`/api/deployments${params}`)" in api
    assert "const suffix = projectId ? `?project_id=${encodeURIComponent(projectId)}` : \"\";" in api


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


def test_agents_a2a_project_view_passes_active_project_id() -> None:
    view = read_repo("frontend/src/components/agents/AgentsView.tsx")
    store = read_repo("frontend/src/stores/agentStore.ts")
    api = read_repo("frontend/src/lib/api.ts")
    route = read_repo("backend/app/api/routes/agents.py")

    assert "const { activeProjectId } = useProjectStore();" in view
    assert "fetchA2ALog(activeProjectId || undefined)" in view
    assert "fetchA2ALog: async (projectId) =>" in store
    assert "const data = await agentsApi.a2aLog(100, projectId);" in store
    assert 'if (projectId) params.set("project_id", projectId);' in api
    assert "await require_project_access(db, request, project_id, min_role=\"viewer\")" in route
    assert "messages = await a2a.get_full_log(db, limit, project_id=project_id)" in route
