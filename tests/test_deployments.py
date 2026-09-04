"""Tests for deployment project isolation."""

from __future__ import annotations

# Import-order guard: app.main pulls modules on a latent module-level import
# cycle (research_validity -> skills.intercoder -> skill_factory ->
# file_processor -> embeddings -> pi_runtime.engine -> telemetry ->
# research_validity) that only resolves when the dispatcher plane
# (app.core.agentic) has been initialized first in the process. The cycle is
# pre-existing architecture debt outside this file; initializing the plane
# here keeps a standalone run of this file green.
import app.core.agentic  # noqa: F401

import json
import uuid
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.config import settings
from app.main import app
from app.models.channel_conversation import ChannelConversation
from app.models.channel_instance import ChannelInstance
from app.models.channel_message import ChannelMessage
from app.models.database import async_session, init_db
from app.models.project import Project
from app.models.research_deployment import ResearchDeployment
from app.services import deployment_service


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


@pytest.fixture(autouse=True)
def reset_settings():
    original_team_mode = settings.team_mode
    original_jwt_secret = settings.jwt_secret
    yield
    settings.team_mode = original_team_mode
    settings.jwt_secret = original_jwt_secret


def _deployment(
    *,
    project_id: str,
    channel_instance_id: str,
    state: str = "active",
) -> ResearchDeployment:
    return ResearchDeployment(
        id=_id("deployment"),
        project_id=project_id,
        name=f"Deployment {project_id}",
        deployment_type="survey",
        questions_json=json.dumps([{"text": "How was it?", "type": "open"}]),
        config_json=json.dumps({}),
        channel_instance_ids_json=json.dumps([channel_instance_id]),
        state=state,
        target_responses=10,
    )


def _conversation(
    *,
    project_id: str,
    channel_instance_id: str,
    deployment_id: str,
) -> ChannelConversation:
    return ChannelConversation(
        id=_id("conversation"),
        channel_instance_id=channel_instance_id,
        project_id=project_id,
        participant_id=_id("participant"),
        participant_name="Participant",
        deployment_id=deployment_id,
        state="active",
        current_question_index=0,
        started_at=datetime.now(timezone.utc),
    )


def _message(
    *,
    project_id: str,
    channel_instance_id: str,
    conversation_id: str,
) -> ChannelMessage:
    return ChannelMessage(
        id=_id("message"),
        channel_instance_id=channel_instance_id,
        project_id=project_id,
        direction="inbound",
        sender_id=_id("sender"),
        sender_name="Participant",
        content="Scoped response",
        thread_id=conversation_id,
    )


@pytest.mark.asyncio
async def test_deployment_project_lists_require_active_project_scope(
    admin_auth_headers,
):
    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        deployments = await ac.get("/api/deployments", headers=admin_auth_headers)
        overview = await ac.get("/api/deployments/overview", headers=admin_auth_headers)

    assert deployments.status_code == 400
    assert deployments.json()["detail"] == "project_id is required"
    assert overview.status_code == 400
    assert overview.json()["detail"] == "project_id is required"


@pytest.mark.asyncio
async def test_deployment_create_requires_existing_active_project_for_admin(
    admin_auth_headers,
):
    await init_db()
    missing_project_id = _id("missing-deployment-project")
    paused_project_id = _id("paused-deployment-create-project")
    transport = ASGITransport(app=app)

    async with async_session() as db:
        db.add(
            Project(
                id=paused_project_id, name="Paused Deployment Create", is_paused=True
            )
        )
        await db.commit()

    payload = {
        "name": "Scoped Deployment",
        "deployment_type": "survey",
        "questions": [{"text": "How was it?", "type": "open"}],
        "channel_instance_ids": [],
    }
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        missing = await ac.post(
            "/api/deployments",
            headers=admin_auth_headers,
            json={"project_id": missing_project_id, **payload},
        )
        paused = await ac.post(
            "/api/deployments",
            headers=admin_auth_headers,
            json={"project_id": paused_project_id, **payload},
        )

    assert missing.status_code == 404
    assert missing.json()["detail"] == "Project not found"
    assert paused.status_code == 409
    assert paused.json()["detail"] == "Project is paused"

    async with async_session() as db:
        result = await db.execute(
            select(ResearchDeployment).where(
                ResearchDeployment.project_id.in_(
                    [missing_project_id, paused_project_id]
                )
            )
        )
        assert result.scalars().all() == []


@pytest.mark.asyncio
async def test_deployment_create_rejects_channel_from_another_project(
    admin_auth_headers,
):
    await init_db()
    project_a = _id("project-a")
    project_b = _id("project-b")
    channel_a = ChannelInstance(
        id=_id("channel-a"),
        platform="slack",
        name="Project A Slack",
        project_id=project_a,
    )
    channel_b = ChannelInstance(
        id=_id("channel-b"),
        platform="slack",
        name="Project B Slack",
        project_id=project_b,
    )
    async with async_session() as db:
        db.add_all(
            [
                Project(id=project_a, name="Deployment Create Project A"),
                Project(id=project_b, name="Deployment Create Project B"),
            ]
        )
        db.add_all([channel_a, channel_b])
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/deployments",
            headers=admin_auth_headers,
            json={
                "project_id": project_a,
                "name": "Cross Project Deployment",
                "deployment_type": "survey",
                "questions": [{"text": "How was it?", "type": "open"}],
                "channel_instance_ids": [channel_b.id],
            },
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Channel instance not found"

        valid = await ac.post(
            "/api/deployments",
            headers=admin_auth_headers,
            json={
                "project_id": project_a,
                "name": "Scoped Deployment",
                "deployment_type": "survey",
                "questions": [{"text": "How was it?", "type": "open"}],
                "channel_instance_ids": [channel_a.id, channel_a.id],
            },
        )

    assert valid.status_code == 201
    assert valid.json()["project_id"] == project_a
    assert valid.json()["channel_instance_ids"] == [channel_a.id]

    async with async_session() as db:
        result = await db.execute(
            select(ResearchDeployment).where(
                ResearchDeployment.project_id == project_a,
                ResearchDeployment.name == "Cross Project Deployment",
            )
        )
        assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_deployment_overview_counts_only_active_project_conversations(
    admin_auth_headers,
):
    await init_db()
    project_a = _id("project-a")
    project_b = _id("project-b")
    channel_a = ChannelInstance(
        id=_id("channel-a"),
        platform="slack",
        name="Project A Slack",
        project_id=project_a,
    )
    channel_b = ChannelInstance(
        id=_id("channel-b"),
        platform="telegram",
        name="Project B Telegram",
        project_id=project_b,
    )
    deployment_a = _deployment(project_id=project_a, channel_instance_id=channel_a.id)
    deployment_b = _deployment(project_id=project_b, channel_instance_id=channel_b.id)
    conversation_a = _conversation(
        project_id=project_a,
        channel_instance_id=channel_a.id,
        deployment_id=deployment_a.id,
    )
    conversation_b = _conversation(
        project_id=project_b,
        channel_instance_id=channel_b.id,
        deployment_id=deployment_b.id,
    )
    async with async_session() as db:
        db.add_all(
            [
                channel_a,
                channel_b,
                deployment_a,
                deployment_b,
                conversation_a,
                conversation_b,
            ]
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/deployments/overview?project_id={project_a}",
            headers=admin_auth_headers,
        )

    assert response.status_code == 200
    overview = response.json()
    assert overview["total_deployments"] == 1
    assert overview["last_24h_conversations_initiated"] == 1


@pytest.mark.asyncio
async def test_deployment_detail_requires_matching_active_project_for_admin(
    admin_auth_headers,
):
    await init_db()
    project_a = _id("project-a")
    project_b = _id("project-b")
    channel_a = ChannelInstance(
        id=_id("channel-a"),
        platform="slack",
        name="Project A Slack",
        project_id=project_a,
    )
    deployment_a = _deployment(project_id=project_a, channel_instance_id=channel_a.id)
    async with async_session() as db:
        db.add_all([channel_a, deployment_a])
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        unscoped = await ac.get(
            f"/api/deployments/{deployment_a.id}",
            headers=admin_auth_headers,
        )
        wrong_project = await ac.get(
            f"/api/deployments/{deployment_a.id}?project_id={project_b}",
            headers=admin_auth_headers,
        )
        scoped = await ac.get(
            f"/api/deployments/{deployment_a.id}?project_id={project_a}",
            headers=admin_auth_headers,
        )

    assert unscoped.status_code == 400
    assert unscoped.json()["detail"] == "project_id is required"
    assert wrong_project.status_code == 404
    assert wrong_project.json()["detail"] == "Deployment not found"
    assert scoped.status_code == 200
    assert scoped.json()["project_id"] == project_a


@pytest.mark.asyncio
async def test_deployment_delete_requires_project_scope_and_removes_owned_conversations(
    admin_auth_headers,
):
    """Simulation cleanup must delete only the scoped deployment and its children."""
    await init_db()
    project_a = _id("project-a")
    project_b = _id("project-b")
    channel_a = ChannelInstance(
        id=_id("channel-a"),
        platform="telegram",
        name="Project A Telegram",
        project_id=project_a,
    )
    deployment_a = _deployment(
        project_id=project_a,
        channel_instance_id=channel_a.id,
        state="completed",
    )
    conversation_a = _conversation(
        project_id=project_a,
        channel_instance_id=channel_a.id,
        deployment_id=deployment_a.id,
    )
    message_a = _message(
        project_id=project_a,
        channel_instance_id=channel_a.id,
        conversation_id=conversation_a.id,
    )
    async with async_session() as db:
        db.add_all(
            [
                Project(id=project_a, name="Deployment Delete Project A"),
                Project(id=project_b, name="Deployment Delete Project B"),
                channel_a,
                deployment_a,
                conversation_a,
                message_a,
            ]
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        unscoped = await ac.delete(
            f"/api/deployments/{deployment_a.id}",
            headers=admin_auth_headers,
        )
        wrong_project = await ac.delete(
            f"/api/deployments/{deployment_a.id}?project_id={project_b}",
            headers=admin_auth_headers,
        )
        deleted = await ac.delete(
            f"/api/deployments/{deployment_a.id}?project_id={project_a}",
            headers=admin_auth_headers,
        )
        missing = await ac.delete(
            f"/api/deployments/{deployment_a.id}?project_id={project_a}",
            headers=admin_auth_headers,
        )

    assert unscoped.status_code == 400
    assert unscoped.json()["detail"] == "project_id is required"
    assert wrong_project.status_code == 404
    assert wrong_project.json()["detail"] == "Deployment not found"
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Deployment not found"

    async with async_session() as db:
        assert await db.get(ResearchDeployment, deployment_a.id) is None
        assert await db.get(ChannelConversation, conversation_a.id) is None
        assert await db.get(ChannelMessage, message_a.id) is None
        assert await db.get(ChannelInstance, channel_a.id) is not None


@pytest.mark.asyncio
async def test_deployment_detail_actions_require_matching_active_project_scope(
    admin_auth_headers,
):
    await init_db()
    project_a = _id("project-a")
    project_b = _id("project-b")
    channel_a = ChannelInstance(
        id=_id("channel-a"),
        platform="slack",
        name="Project A Slack",
        project_id=project_a,
    )
    deployment_a = _deployment(
        project_id=project_a,
        channel_instance_id=channel_a.id,
        state="draft",
    )
    conversation_a = _conversation(
        project_id=project_a,
        channel_instance_id=channel_a.id,
        deployment_id=deployment_a.id,
    )
    message_a = _message(
        project_id=project_a,
        channel_instance_id=channel_a.id,
        conversation_id=conversation_a.id,
    )
    cross_project_message = _message(
        project_id=project_b,
        channel_instance_id=channel_a.id,
        conversation_id=conversation_a.id,
    )
    async with async_session() as db:
        db.add_all(
            [channel_a, deployment_a, conversation_a, message_a, cross_project_message]
        )
        await db.commit()

    paths = [
        ("get", f"/api/deployments/{deployment_a.id}/analytics"),
        ("post", f"/api/deployments/{deployment_a.id}/activate"),
        ("post", f"/api/deployments/{deployment_a.id}/pause"),
        ("post", f"/api/deployments/{deployment_a.id}/complete"),
        ("get", f"/api/deployments/{deployment_a.id}/conversations"),
        (
            "get",
            f"/api/deployments/{deployment_a.id}/conversations/{conversation_a.id}",
        ),
        (
            "get",
            f"/api/deployments/{deployment_a.id}/conversations/{conversation_a.id}/transcript",
        ),
    ]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        for method, path in paths:
            unscoped = await getattr(ac, method)(path, headers=admin_auth_headers)
            wrong_project = await getattr(ac, method)(
                f"{path}?project_id={project_b}",
                headers=admin_auth_headers,
            )

            assert unscoped.status_code == 400
            assert unscoped.json()["detail"] == "project_id is required"
            assert wrong_project.status_code == 404
            assert wrong_project.json()["detail"] == "Deployment not found"

        analytics = await ac.get(
            f"/api/deployments/{deployment_a.id}/analytics?project_id={project_a}",
            headers=admin_auth_headers,
        )
        conversations = await ac.get(
            f"/api/deployments/{deployment_a.id}/conversations?project_id={project_a}",
            headers=admin_auth_headers,
        )
        conversation = await ac.get(
            f"/api/deployments/{deployment_a.id}/conversations/{conversation_a.id}?project_id={project_a}",
            headers=admin_auth_headers,
        )
        transcript = await ac.get(
            f"/api/deployments/{deployment_a.id}/conversations/{conversation_a.id}/transcript?project_id={project_a}",
            headers=admin_auth_headers,
        )

    assert analytics.status_code == 200
    assert analytics.json()["deployment_id"] == deployment_a.id
    assert conversations.status_code == 200
    assert [item["id"] for item in conversations.json()] == [conversation_a.id]
    assert conversation.status_code == 200
    assert conversation.json()["project_id"] == project_a
    assert transcript.status_code == 200
    transcript_messages = transcript.json()["messages"]
    assert len(transcript_messages) == 1
    assert transcript_messages[0]["project_id"] == project_a

    async with async_session() as db:
        unchanged = await db.get(ResearchDeployment, deployment_a.id)
        assert unchanged is not None
        assert unchanged.state == "draft"


@pytest.mark.asyncio
async def test_deployment_response_rejects_cross_project_conversation(
    admin_auth_headers,
):
    await init_db()
    project_a = _id("project-a")
    project_b = _id("project-b")
    channel_a = ChannelInstance(
        id=_id("channel-a"),
        platform="slack",
        name="Project A Slack",
        project_id=project_a,
    )
    channel_b = ChannelInstance(
        id=_id("channel-b"),
        platform="telegram",
        name="Project B Telegram",
        project_id=project_b,
    )
    deployment_a = _deployment(project_id=project_a, channel_instance_id=channel_a.id)
    deployment_b = _deployment(project_id=project_b, channel_instance_id=channel_b.id)
    conversation_b = _conversation(
        project_id=project_b,
        channel_instance_id=channel_b.id,
        deployment_id=deployment_b.id,
    )
    async with async_session() as db:
        db.add(Project(id=project_a, name="Deployment Project A"))
        db.add(Project(id=project_b, name="Deployment Project B"))
        db.add_all([channel_a, channel_b, deployment_a, deployment_b, conversation_b])
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        unscoped = await ac.post(
            f"/api/deployments/{deployment_a.id}/respond",
            headers=admin_auth_headers,
            json={
                "conversation_id": conversation_b.id,
                "message_text": "This belongs to another project.",
            },
        )
        wrong_project = await ac.post(
            f"/api/deployments/{deployment_a.id}/respond?project_id={project_b}",
            headers=admin_auth_headers,
            json={
                "conversation_id": conversation_b.id,
                "message_text": "This belongs to another project.",
            },
        )
        response = await ac.post(
            f"/api/deployments/{deployment_a.id}/respond?project_id={project_a}",
            headers=admin_auth_headers,
            json={
                "conversation_id": conversation_b.id,
                "message_text": "This belongs to another project.",
            },
        )

    assert unscoped.status_code == 400
    assert unscoped.json()["detail"] == "project_id is required"
    assert wrong_project.status_code == 404
    assert wrong_project.json()["detail"] == "Deployment not found"
    assert response.status_code == 404
    assert response.json()["detail"] == "Conversation not found"

    async with async_session() as db:
        updated = await db.get(ChannelConversation, conversation_b.id)
        assert updated is not None
    assert updated.current_question_index == 0
    assert updated.state == "active"


@pytest.mark.asyncio
async def test_deployment_dispatch_rejects_paused_project(admin_auth_headers):
    await init_db()
    project_id = _id("paused-deployment-project")
    channel = ChannelInstance(
        id=_id("channel"),
        platform="slack",
        name="Paused Slack",
        project_id=project_id,
    )
    deployment = _deployment(
        project_id=project_id,
        channel_instance_id=channel.id,
        state="draft",
    )
    conversation = _conversation(
        project_id=project_id,
        channel_instance_id=channel.id,
        deployment_id=deployment.id,
    )

    async with async_session() as db:
        db.add(Project(id=project_id, name="Paused Deployment Project", is_paused=True))
        db.add_all([channel, deployment, conversation])
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        activate = await ac.post(
            f"/api/deployments/{deployment.id}/activate?project_id={project_id}",
            headers=admin_auth_headers,
        )
        response = await ac.post(
            f"/api/deployments/{deployment.id}/respond?project_id={project_id}",
            headers=admin_auth_headers,
            json={
                "conversation_id": conversation.id,
                "message_text": "Paused projects should not dispatch.",
            },
        )

    assert activate.status_code == 409
    assert activate.json()["detail"] == "Project is paused"
    assert response.status_code == 409
    assert response.json()["detail"] == "Project is paused"

    async with async_session() as db:
        unchanged = await db.get(ResearchDeployment, deployment.id)
        untouched_conversation = await db.get(ChannelConversation, conversation.id)

    assert unchanged.state == "draft"
    assert untouched_conversation.current_question_index == 0


@pytest.mark.asyncio
async def test_deployment_service_helpers_require_project_scope():
    await init_db()
    project_a = _id("project-a")
    project_b = _id("project-b")
    channel_a = ChannelInstance(
        id=_id("channel-a"),
        platform="slack",
        name="Project A Slack",
        project_id=project_a,
    )
    deployment_a = _deployment(
        project_id=project_a,
        channel_instance_id=channel_a.id,
        state="draft",
    )
    conversation_a = _conversation(
        project_id=project_a,
        channel_instance_id=channel_a.id,
        deployment_id=deployment_a.id,
    )
    message_a = _message(
        project_id=project_a,
        channel_instance_id=channel_a.id,
        conversation_id=conversation_a.id,
    )
    cross_project_message = _message(
        project_id=project_b,
        channel_instance_id=channel_a.id,
        conversation_id=conversation_a.id,
    )

    async with async_session() as db:
        db.add_all(
            [channel_a, deployment_a, conversation_a, message_a, cross_project_message]
        )
        await db.commit()

        assert (
            await deployment_service.get_deployment(
                db,
                deployment_a.id,
                project_id=project_b,
            )
            is None
        )
        assert (
            await deployment_service.list_deployments(
                db,
                project_id=project_b,
            )
            == []
        )
        assert (
            await deployment_service.get_deployment_analytics(
                db,
                deployment_a.id,
                project_id=project_b,
            )
            == {}
        )
        assert (
            await deployment_service.list_conversations(
                db,
                deployment_a.id,
                project_id=project_b,
            )
            == []
        )
        assert (
            await deployment_service.get_conversation(
                db,
                conversation_a.id,
                deployment_id=deployment_a.id,
                project_id=project_b,
            )
            is None
        )
        assert (
            await deployment_service.get_conversation_transcript(
                db,
                conversation_a.id,
                deployment_id=deployment_a.id,
                project_id=project_b,
            )
            == []
        )

        with pytest.raises(ValueError, match="Deployment .* not found"):
            await deployment_service.activate_deployment(
                db,
                deployment_a.id,
                project_id=project_b,
            )

        assert (
            await deployment_service.get_deployment(
                db,
                deployment_a.id,
                project_id=project_a,
            )
            is not None
        )
        transcript = await deployment_service.get_conversation_transcript(
            db,
            conversation_a.id,
            deployment_id=deployment_a.id,
            project_id=project_a,
        )

    assert [message["project_id"] for message in transcript] == [project_a]


@pytest.mark.asyncio
async def test_activate_interview_uses_grammatically_correct_intro():
    await init_db()
    project_id = _id("project-interview-intro")
    channel_id = _id("channel-interview-intro")
    deployment = _deployment(
        project_id=project_id,
        channel_instance_id=channel_id,
        state="draft",
    )
    deployment.deployment_type = "interview"

    async with async_session() as db:
        db.add(deployment)
        await db.commit()
        result = await deployment_service.activate_deployment(
            db,
            deployment.id,
            project_id=project_id,
        )

    assert result["intro"].startswith("Hi! We're conducting an interview.")
