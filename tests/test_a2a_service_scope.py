"""Regression tests for A2A service project scoping."""

import json
import uuid

import pytest
from sqlalchemy import delete

from app.models.agent import A2AMessage, Agent, AgentRole
from app.models.database import async_session, init_db
from app.models.project import Project
from app.models.task import Task


@pytest.mark.asyncio
async def test_a2a_service_requires_and_persists_project_scope():
    """A2A service writes and mutations should fail closed without active project scope."""
    await init_db()
    from app.services import a2a

    project_id = f"a2a-service-scope-{uuid.uuid4()}"
    message_id = ""

    async with async_session() as db:
        with pytest.raises(ValueError, match="project_id is required for A2A messages"):
            await a2a.send_message(
                db,
                from_agent_id="agent-a",
                to_agent_id="agent-b",
                message_type="request",
                content="missing project scope should fail",
                project_id="",
            )

        with pytest.raises(ValueError, match="metadata project_id does not match"):
            await a2a.send_message(
                db,
                from_agent_id="agent-a",
                to_agent_id="agent-b",
                message_type="request",
                content="conflicting project scope should fail",
                project_id=project_id,
                metadata={"projectId": f"other-{project_id}"},
            )

        msg = await a2a.send_message(
            db,
            from_agent_id="agent-a",
            to_agent_id="agent-b",
            message_type="request",
            content="project-scoped service write",
            project_id=project_id,
        )
        message_id = msg["id"]
        stored = await db.get(A2AMessage, message_id)
        assert msg["project_id"] == project_id
        assert msg["metadata"]["project_id"] == project_id
        assert stored and stored.project_id == project_id
        assert json.loads(stored.extra_data)["project_id"] == project_id

        with pytest.raises(ValueError, match="project_id is required for A2A message mutations"):
            await a2a.mark_read(db, message_id, project_id="")

    async with async_session() as db:
        if message_id:
            await db.execute(delete(A2AMessage).where(A2AMessage.id == message_id))
            await db.commit()


@pytest.mark.asyncio
async def test_a2a_thread_context_resolves_task_project_scope():
    """Conversation threads must not mix messages with the same context_id across projects."""
    await init_db()
    from app.services import a2a

    project_a = f"a2a-thread-project-a-{uuid.uuid4()}"
    project_b = f"a2a-thread-project-b-{uuid.uuid4()}"
    task_a = f"a2a-thread-task-a-{uuid.uuid4()}"
    task_b = f"a2a-thread-task-b-{uuid.uuid4()}"
    context_id = f"a2a-shared-context-{uuid.uuid4()}"
    message_ids = [str(uuid.uuid4()) for _ in range(3)]
    agent_a = f"a2a-thread-agent-a-{uuid.uuid4()}"
    agent_b = f"a2a-thread-agent-b-{uuid.uuid4()}"

    async with async_session() as db:
        db.add_all(
            [
                Project(id=project_a, name="A2A Thread Project A"),
                Project(id=project_b, name="A2A Thread Project B"),
                Task(id=task_a, project_id=project_a, title="Visible thread task"),
                Task(id=task_b, project_id=project_b, title="Hidden thread task"),
                A2AMessage(
                    id=message_ids[0],
                    from_agent_id=agent_a,
                    to_agent_id=agent_b,
                    message_type="collaboration_request",
                    content="visible project thread content",
                    extra_data=json.dumps({"task_id": task_a, "context_id": context_id}),
                ),
                A2AMessage(
                    id=message_ids[1],
                    from_agent_id=agent_b,
                    to_agent_id=agent_a,
                    message_type="collaboration_request",
                    content="hidden project thread content",
                    extra_data=json.dumps({"task_id": task_b, "context_id": context_id}),
                ),
                A2AMessage(
                    id=message_ids[2],
                    from_agent_id=agent_b,
                    to_agent_id=agent_a,
                    message_type="collaboration_request",
                    content="conflicting project thread content",
                    extra_data=json.dumps(
                        {"project_id": project_a, "task_id": task_b, "context_id": context_id}
                    ),
                ),
            ]
        )
        await db.commit()

        thread = await a2a.get_conversation_thread(
            db,
            context_id,
            project_id=project_a,
            limit=10,
        )
        contents = [message["content"] for message in thread]
        assert contents == ["visible project thread content"]
        assert thread[0]["project_id"] == project_a
        assert thread[0]["metadata"]["project_id"] == project_a

    async with async_session() as db:
        await db.execute(delete(A2AMessage).where(A2AMessage.id.in_(message_ids)))
        await db.execute(delete(Task).where(Task.id.in_([task_a, task_b])))
        await db.execute(delete(Project).where(Project.id.in_([project_a, project_b])))
        await db.commit()


@pytest.mark.asyncio
async def test_a2a_project_inbox_and_mark_read_are_project_scoped():
    """Background A2A inbox processing should skip global content and respect agent scope."""
    await init_db()
    from app.services import a2a

    project_a = f"a2a-inbox-project-a-{uuid.uuid4()}"
    project_b = f"a2a-inbox-project-b-{uuid.uuid4()}"
    scoped_agent_id = f"a2a-scoped-agent-{uuid.uuid4()}"
    message_ids = [str(uuid.uuid4()) for _ in range(3)]
    sender_a = f"a2a-inbox-sender-a-{uuid.uuid4()}"
    sender_b = f"a2a-inbox-sender-b-{uuid.uuid4()}"
    sender_c = f"a2a-inbox-sender-c-{uuid.uuid4()}"

    async with async_session() as db:
        db.add_all(
            [
                Project(id=project_a, name="A2A Inbox Project A"),
                Project(id=project_b, name="A2A Inbox Project B"),
                Agent(
                    id=scoped_agent_id,
                    name="Scoped inbox agent",
                    role=AgentRole.CUSTOM,
                    system_prompt="Scoped inbox test agent.",
                    capabilities=json.dumps(["a2a_messaging"]),
                    scope="project",
                    project_id=project_a,
                    is_active=True,
                ),
                A2AMessage(
                    id=message_ids[0],
                    from_agent_id=sender_a,
                    to_agent_id=scoped_agent_id,
                    message_type="collaboration_request",
                    content="project A inbox content",
                    extra_data=json.dumps({"project_id": project_a}),
                ),
                A2AMessage(
                    id=message_ids[1],
                    from_agent_id=sender_b,
                    to_agent_id=scoped_agent_id,
                    message_type="collaboration_request",
                    content="project B inbox content",
                    extra_data=json.dumps({"project_id": project_b}),
                ),
                A2AMessage(
                    id=message_ids[2],
                    from_agent_id=sender_c,
                    to_agent_id=scoped_agent_id,
                    message_type="collaboration_request",
                    content="global inbox content",
                    extra_data=json.dumps({}),
                ),
            ]
        )
        await db.commit()

        inbox = await a2a.get_project_inbox(db, scoped_agent_id, limit=10)
        contents = [message["content"] for message in inbox]
        assert contents == ["project A inbox content"]
        assert inbox[0]["project_id"] == project_a

        wrong_project = await a2a.mark_read(db, message_ids[0], project_id=project_b)
        right_project = await a2a.mark_read(db, message_ids[0], project_id=project_a)
        message = await db.get(A2AMessage, message_ids[0])
        assert wrong_project is False
        assert right_project is True
        assert message and message.read is True

    async with async_session() as db:
        await db.execute(delete(A2AMessage).where(A2AMessage.id.in_(message_ids)))
        await db.execute(delete(Agent).where(Agent.id == scoped_agent_id))
        await db.execute(delete(Project).where(Project.id.in_([project_a, project_b])))
        await db.commit()
