"""Tests for deployment project isolation."""

from __future__ import annotations

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
from app.models.database import async_session, init_db
from app.models.research_deployment import ResearchDeployment


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


@pytest.mark.asyncio
async def test_deployment_create_rejects_channel_from_another_project(admin_auth_headers):
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
async def test_deployment_overview_counts_only_active_project_conversations(admin_auth_headers):
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
async def test_deployment_response_rejects_cross_project_conversation(admin_auth_headers):
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
        db.add_all([channel_a, channel_b, deployment_a, deployment_b, conversation_b])
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            f"/api/deployments/{deployment_a.id}/respond",
            headers=admin_auth_headers,
            json={
                "conversation_id": conversation_b.id,
                "message_text": "This belongs to another project.",
            },
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Conversation not found"

    async with async_session() as db:
        updated = await db.get(ChannelConversation, conversation_b.id)
        assert updated is not None
        assert updated.current_question_index == 0
        assert updated.state == "active"
