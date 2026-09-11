"""Regression tests for A2A project ownership claim consistency."""

import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from app.config import settings
from app.core.auth import create_token
from app.main import app
from app.models.agent import A2AMessage, Agent, AgentRole
from app.models.database import async_session, init_db
from app.models.project import Project
from app.models.task import Task


@pytest.fixture
def auth_headers():
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    token = create_token("user1", "testuser", "admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_a2a_log_excludes_conflicting_project_claims(auth_headers):
    """Metadata cannot make a task or project-scoped agent appear in the wrong project."""
    await init_db()
    project_a = f"a2a-claim-project-a-{uuid.uuid4()}"
    project_b = f"a2a-claim-project-b-{uuid.uuid4()}"
    task_a = f"a2a-claim-task-a-{uuid.uuid4()}"
    task_b = f"a2a-claim-task-b-{uuid.uuid4()}"
    visible_agent_id = f"a2a-claim-visible-agent-{uuid.uuid4()}"
    hidden_agent_id = f"a2a-claim-hidden-agent-{uuid.uuid4()}"
    message_ids = [str(uuid.uuid4()) for _ in range(4)]

    async with async_session() as db:
        db.add_all(
            [
                Project(id=project_a, name="A2A Claim Project A"),
                Project(id=project_b, name="A2A Claim Project B"),
                Task(id=task_a, project_id=project_a, title="Visible claim task"),
                Task(id=task_b, project_id=project_b, title="Hidden claim task"),
                Agent(
                    id=visible_agent_id,
                    name="Visible claim agent",
                    role=AgentRole.CUSTOM,
                    system_prompt="Visible project agent.",
                    capabilities=json.dumps(["a2a_messaging"]),
                    scope="project",
                    project_id=project_a,
                    is_active=True,
                ),
                Agent(
                    id=hidden_agent_id,
                    name="Hidden claim agent",
                    role=AgentRole.CUSTOM,
                    system_prompt="Hidden project agent.",
                    capabilities=json.dumps(["a2a_messaging"]),
                    scope="project",
                    project_id=project_b,
                    is_active=True,
                ),
                A2AMessage(
                    id=message_ids[0],
                    from_agent_id=visible_agent_id,
                    to_agent_id=None,
                    message_type="a2a_task",
                    content="consistent project A message",
                    extra_data=json.dumps({"project_id": project_a, "task_id": task_a}),
                ),
                A2AMessage(
                    id=message_ids[1],
                    from_agent_id=visible_agent_id,
                    to_agent_id=None,
                    message_type="a2a_task",
                    content="conflicting hidden task message",
                    extra_data=json.dumps({"project_id": project_a, "task_id": task_b}),
                ),
                A2AMessage(
                    id=message_ids[2],
                    from_agent_id=hidden_agent_id,
                    to_agent_id=None,
                    message_type="a2a_task",
                    content="conflicting hidden agent message",
                    extra_data=json.dumps({"project_id": project_a, "task_id": task_a}),
                ),
                A2AMessage(
                    id=message_ids[3],
                    from_agent_id=hidden_agent_id,
                    to_agent_id=None,
                    message_type="a2a_task",
                    content="consistent project B message",
                    extra_data=json.dumps({"project_id": project_b, "task_id": task_b}),
                ),
            ]
        )
        await db.commit()

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get(
                f"/api/agents/a2a/log?project_id={project_a}&limit=20",
                headers=auth_headers,
            )
            assert response.status_code == 200
            contents = [message["content"] for message in response.json()["messages"]]
            assert "consistent project A message" in contents
            assert "conflicting hidden task message" not in contents
            assert "conflicting hidden agent message" not in contents
            assert "consistent project B message" not in contents
    finally:
        async with async_session() as db:
            await db.execute(delete(A2AMessage).where(A2AMessage.id.in_(message_ids)))
            await db.execute(
                delete(Agent).where(Agent.id.in_([visible_agent_id, hidden_agent_id]))
            )
            await db.execute(delete(Task).where(Task.id.in_([task_a, task_b])))
            await db.execute(
                delete(Project).where(Project.id.in_([project_a, project_b]))
            )
            await db.commit()
