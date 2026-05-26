"""Source-level contracts for project-scoped mid-execution steering."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read_repo(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_mid_execution_steering_is_project_scoped() -> None:
    route = read_repo("backend/app/api/routes/steering.py")
    manager = read_repo("backend/app/core/steering.py")
    lifecycle = read_repo("backend/app/core/agent_lifecycle.py")
    api = read_repo("frontend/src/lib/researchIntegrityApi.ts")
    steering_input = read_repo("frontend/src/components/common/SteeringInput.tsx")
    agents_view = read_repo("frontend/src/components/agents/AgentsView.tsx")
    chat_view = read_repo("frontend/src/components/chat/ChatView.tsx")

    assert "project_id: str" in route
    assert "def _require_project_id(project_id: str | None) -> str:" in route
    assert 'raise HTTPException(status_code=400, detail="project_id is required")' in route
    assert "require_admin_from_request(request)" in route
    assert "await require_project_access(db, request, scoped_project_id, min_role=min_role)" in route
    assert "select(Project).where(Project.id == scoped_project_id)" in route
    assert "await _require_steerable_agent(db, agent_id, project.id)" in route
    assert "agent.scope or \"universal\"" in route
    assert "agent.project_id or \"\") != project_id" in route
    assert "project_id: str | None = Query(default=None)" in route
    assert "steering_manager.get_status(agent_id, project_id=project.id)" in route
    assert "steering_manager.get_queues(agent_id, project_id=project.id)" in route
    assert "steering_manager.clear_all(agent_id, project_id=project.id)" in route
    assert "steering_manager.get_all_status(project_id=project.id)" in route

    assert "def _matches_project" in manager
    assert "project_ids_with_queued_steering" in manager
    assert "project_id: str | None = None" in manager
    assert "msg_metadata[\"project_id\"] = scoped_project_id" in manager
    assert "state.active_project_id == scoped_project_id" in manager
    assert "get_all_status(self, project_id: str | None = None)" in manager

    assert "if await self._process_project_steering():" in lifecycle
    assert "project_ids_with_queued_steering(self._agent_id)" in lifecycle
    assert "project_id=project.id" in lifecycle
    assert "project_id=task.project_id" in lifecycle
    assert "project_id=\"\"" not in lifecycle
    assert "Steering messages don't require a project" not in lifecycle

    assert "const steeringProjectParam = (projectId: string)" in api
    assert "{ message, mode, project_id: projectId }" in api
    assert "/api/steering/${agentId}/status?${steeringProjectParam(projectId)}" in api
    assert "/api/steering?${steeringProjectParam(projectId)}" in api

    assert "projectId?: string | null;" in steering_input
    assert "steering.getStatus(agentId, projectId)" in steering_input
    assert "steering.send(agentId, message.trim(), projectId)" in steering_input
    assert "steering.abort(agentId, projectId)" in steering_input
    assert "steering.getQueues(agentId, projectId)" in steering_input
    assert (
        "if (!capabilities.canUseSteering || !projectId || (!isWorking && queueCount === 0)) "
        "return null;"
    ) in steering_input

    assert "projectId={activeProjectId}" in agents_view
    assert "function SteeringQueueIndicator({" in chat_view
    assert "enabled," in chat_view
    assert "if (!enabled || !agentId || !projectId)" in chat_view
    assert "steeringApi.getAllStatus(projectId)" in chat_view
    assert "projectId={activeProjectId}" in chat_view
