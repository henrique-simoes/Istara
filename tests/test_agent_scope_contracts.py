"""Source contracts for project-scoped agent mutation surfaces."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read_repo(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_agent_by_id_mutations_require_active_project_scope() -> None:
    api = read_repo("frontend/src/lib/api.ts")
    store = read_repo("frontend/src/stores/agentStore.ts")
    view = read_repo("frontend/src/components/agents/AgentsView.tsx")
    route = read_repo("backend/app/api/routes/agents.py")
    guard = read_repo("backend/app/api/agent_project_scope.py")

    for expected in (
        "const agentProjectPath = (id: string, projectId: string, suffix = \"\")",
        "update: (id: string, data: Record<string, unknown>, projectId: string)",
        "delete: (id: string, projectId: string) => del(agentProjectPath(id, projectId))",
        "pause: (id: string, projectId: string)",
        "resume: (id: string, projectId: string)",
        "restart: (id: string, projectId: string)",
        "uploadAvatar: async (id: string, file: File, projectId: string)",
        "updateMemory: (id: string, data: Record<string, unknown>, projectId: string)",
        "updateIdentity: (id: string, files: Record<string, string>, projectId: string)",
        "exportConfig: (id: string, projectId: string)",
        "importConfig: (data: Record<string, unknown>, projectId: string)",
        "project_id: projectId",
    ):
        assert expected in api

    for expected in (
        "updateAgent: (id: string, data: Record<string, unknown>, projectId: string)",
        "deleteAgent: (id: string, projectId: string)",
        "pauseAgent: (id: string, projectId: string)",
        "resumeAgent: (id: string, projectId: string)",
        "agentsApi.update(id, data, projectId)",
        "agentsApi.delete(id, projectId)",
        "agentsApi.pause(id, projectId)",
        "agentsApi.resume(id, projectId)",
    ):
        assert expected in store

    for expected in (
        "const isProjectOwnedAgent = Boolean(activeProjectId && agent.project_id === activeProjectId);",
        "resumeAgent(agent.id, activeProjectId!)",
        "pauseAgent(agent.id, activeProjectId!)",
        "agentsApi.exportConfig(agent.id, activeProjectId!)",
        "deleteAgent(agent.id, activeProjectId!)",
        "updateAgent(agent.id, { is_active: false }, activeProjectId!)",
        "updateAgent(agent.id, { capabilities: newCaps }, activeProjectId!)",
        "agentsApi.importConfig(agentData, activeProjectId)",
    ):
        assert expected in view
    assert "agentsApi.updateIdentity(agent.id" in view and "activeProjectId!)" in view

    for expected in (
        "async def require_project_owned_agent",
        'raise HTTPException(status_code=400, detail="project_id is required")',
        "await require_project_access(db, request, scoped_project_id, min_role=min_role)",
        "if agent_project_id(agent) != scoped_project_id:",
        'raise HTTPException(status_code=404, detail="Agent not found")',
    ):
        assert expected in guard

    for expected in (
        "async def update_agent(",
        "async def delete_agent(",
        "async def pause_agent(",
        "async def resume_agent(",
        "async def restart_agent(",
        "async def upload_avatar(",
        "async def update_identity(",
        "async def update_memory(",
        "async def export_agent(",
        "project_id: str | None = None",
        "scope=\"project\"",
        "project_id=scoped_project_id",
    ):
        assert expected in route
