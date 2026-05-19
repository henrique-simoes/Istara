"""Regression tests for project-facing agent mutation scope."""

import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.agent import Agent, AgentRole, AgentState, HeartbeatStatus
from app.models.database import async_session, init_db


async def _seed_agent(
    agent_id: str,
    *,
    project_id: str = "",
    memory: dict | None = None,
) -> None:
    async with async_session() as db:
        db.add(
            Agent(
                id=agent_id,
                name=f"Agent {agent_id}",
                role=AgentRole.CUSTOM,
                system_prompt="Project mutation scope test agent.",
                capabilities=json.dumps(["a2a_messaging", "rag_retrieval"]),
                memory=json.dumps(memory or {}),
                heartbeat_interval_seconds=60,
                heartbeat_status=HeartbeatStatus.HEALTHY,
                state=AgentState.IDLE,
                is_system=False,
                is_active=True,
                scope="project" if project_id else "universal",
                project_id=project_id,
            )
        )
        await db.commit()


@pytest.mark.asyncio
async def test_project_facing_agent_mutations_require_matching_project(admin_auth_headers):
    """By-id agent actions must not act on stale cross-project ids."""
    await init_db()
    visible_project_id = f"mutation-visible-project-{uuid.uuid4()}"
    hidden_project_id = f"mutation-hidden-project-{uuid.uuid4()}"
    visible_agent_id = f"mutation-visible-agent-{uuid.uuid4()}"
    hidden_agent_id = f"mutation-hidden-agent-{uuid.uuid4()}"
    universal_agent_id = f"mutation-universal-agent-{uuid.uuid4()}"
    await _seed_agent(visible_agent_id, project_id=visible_project_id, memory={"visible": "before"})
    await _seed_agent(hidden_agent_id, project_id=hidden_project_id, memory={"hidden": "before"})
    await _seed_agent(universal_agent_id, memory={"global": "before"})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        unscoped_update = await ac.patch(
            f"/api/agents/{visible_agent_id}",
            headers=admin_auth_headers,
            json={"name": "No Project"},
        )
        assert unscoped_update.status_code == 400
        assert unscoped_update.json()["detail"] == "project_id is required"

        wrong_project_update = await ac.patch(
            f"/api/agents/{hidden_agent_id}?project_id={visible_project_id}",
            headers=admin_auth_headers,
            json={"name": "Wrong Project"},
        )
        universal_pause = await ac.post(
            f"/api/agents/{universal_agent_id}/pause?project_id={visible_project_id}",
            headers=admin_auth_headers,
        )
        assert wrong_project_update.status_code == 404
        assert universal_pause.status_code == 404

        correct_update = await ac.patch(
            f"/api/agents/{visible_agent_id}?project_id={visible_project_id}",
            headers=admin_auth_headers,
            json={"name": "Visible Project Agent"},
        )
        memory_update = await ac.patch(
            f"/api/agents/{visible_agent_id}/memory?project_id={visible_project_id}",
            headers=admin_auth_headers,
            json={"visible": "after"},
        )
        wrong_memory_update = await ac.patch(
            f"/api/agents/{hidden_agent_id}/memory?project_id={visible_project_id}",
            headers=admin_auth_headers,
            json={"hidden": "leaked"},
        )
        assert correct_update.status_code == 200
        assert correct_update.json()["name"] == "Visible Project Agent"
        assert memory_update.status_code == 200
        assert memory_update.json()["memory"]["visible"] == "after"
        assert wrong_memory_update.status_code == 404

        pause = await ac.post(
            f"/api/agents/{visible_agent_id}/pause?project_id={visible_project_id}",
            headers=admin_auth_headers,
        )
        resume = await ac.post(
            f"/api/agents/{visible_agent_id}/resume?project_id={visible_project_id}",
            headers=admin_auth_headers,
        )
        assert pause.status_code == 200
        assert pause.json()["status"] == "paused"
        assert resume.status_code == 200
        assert resume.json()["status"] == "resumed"

        export = await ac.get(
            f"/api/agents/{visible_agent_id}/export?project_id={visible_project_id}",
            headers=admin_auth_headers,
        )
        assert export.status_code == 200
        assert export.json()["agent"]["name"] == "Visible Project Agent"

        import_without_project = await ac.post(
            "/api/agents/import",
            headers=admin_auth_headers,
            json=export.json()["agent"],
        )
        import_with_project = await ac.post(
            "/api/agents/import",
            headers=admin_auth_headers,
            json={**export.json()["agent"], "project_id": visible_project_id},
        )
        assert import_without_project.status_code == 400
        assert import_with_project.status_code == 200
        assert import_with_project.json()["scope"] == "project"
        assert import_with_project.json()["project_id"] == visible_project_id

        delete_hidden_from_visible = await ac.delete(
            f"/api/agents/{hidden_agent_id}?project_id={visible_project_id}",
            headers=admin_auth_headers,
        )
        delete_visible = await ac.delete(
            f"/api/agents/{visible_agent_id}?project_id={visible_project_id}",
            headers=admin_auth_headers,
        )
        assert delete_hidden_from_visible.status_code == 404
        assert delete_visible.status_code == 204

    async with async_session() as db:
        hidden_agent = await db.get(Agent, hidden_agent_id)
        assert hidden_agent is not None
        assert hidden_agent.is_active is True
        assert json.loads(hidden_agent.memory or "{}") == {"hidden": "before"}
        assert hidden_agent.name != "Wrong Project"
