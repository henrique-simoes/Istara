"""Tests for Channels API routes — CRUD, start/stop, health, messages, conversations, send."""

import json
import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.channels.base import channel_router
from app.main import app
from app.config import settings
from app.models.database import init_db
from app.models.database import async_session
from app.models.channel_instance import ChannelInstance
from app.models.channel_message import ChannelMessage
from app.models.channel_conversation import ChannelConversation
from app.models.project import Project
from app.core.field_encryption import decrypt_field
from app.core.auth import create_token
from app.services import channel_service


@pytest.fixture(autouse=True)
def reset_settings():
    original_team_mode = settings.team_mode
    original_jwt_secret = settings.jwt_secret
    yield
    settings.team_mode = original_team_mode
    settings.jwt_secret = original_jwt_secret


@pytest.fixture
def auth_headers():
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    token = create_token("user1", "testuser", "admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_channels_list_returns_list(auth_headers):
    """GET /api/channels returns a list."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/channels?project_id=channel-list-project", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_channels_list_requires_project_id_for_project_facing_api(auth_headers):
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/channels", headers=auth_headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "project_id is required"


@pytest.mark.asyncio
async def test_channel_detail_routes_are_bound_to_active_project(auth_headers):
    await init_db()
    project_id = f"channel-detail-project-{uuid.uuid4()}"
    other_project_id = f"channel-detail-other-{uuid.uuid4()}"
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        created = await ac.post(
            "/api/channels",
            headers=auth_headers,
            json={
                "platform": "slack",
                "name": "Project Slack",
                "project_id": project_id,
                "config": {"Bot Token": "xoxb-test", "Signing Secret": "secret"},
            },
        )
        assert created.status_code == 200
        instance_id = created.json()["id"]

        missing_scope = await ac.get(f"/api/channels/{instance_id}", headers=auth_headers)
        wrong_scope = await ac.get(
            f"/api/channels/{instance_id}?project_id={other_project_id}",
            headers=auth_headers,
        )
        correct_scope = await ac.get(
            f"/api/channels/{instance_id}?project_id={project_id}",
            headers=auth_headers,
        )

    assert missing_scope.status_code == 400
    assert wrong_scope.status_code == 404
    assert correct_scope.status_code == 200
    assert correct_scope.json()["project_id"] == project_id


@pytest.mark.asyncio
async def test_channel_messages_and_conversations_filter_by_active_project(auth_headers):
    await init_db()
    project_id = f"channel-messages-project-{uuid.uuid4()}"
    other_project_id = f"channel-messages-other-{uuid.uuid4()}"
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        created = await ac.post(
            "/api/channels",
            headers=auth_headers,
            json={
                "platform": "slack",
                "name": "Scoped Slack",
                "project_id": project_id,
                "config": {"Bot Token": "xoxb-test", "Signing Secret": "secret"},
            },
        )
        assert created.status_code == 200
        instance_id = created.json()["id"]

    visible_message_id = str(uuid.uuid4())
    hidden_message_id = str(uuid.uuid4())
    visible_conversation_id = str(uuid.uuid4())
    hidden_conversation_id = str(uuid.uuid4())
    async with async_session() as db:
        db.add_all(
            [
                ChannelMessage(
                    id=visible_message_id,
                    channel_instance_id=instance_id,
                    project_id=project_id,
                    direction="inbound",
                    sender_id="participant-1",
                    sender_name="Participant 1",
                    content="visible project message",
                ),
                ChannelMessage(
                    id=hidden_message_id,
                    channel_instance_id=instance_id,
                    project_id=other_project_id,
                    direction="inbound",
                    sender_id="participant-2",
                    sender_name="Participant 2",
                    content="hidden cross-project message",
                ),
                ChannelConversation(
                    id=visible_conversation_id,
                    channel_instance_id=instance_id,
                    project_id=project_id,
                    participant_id="participant-1",
                    participant_name="Participant 1",
                ),
                ChannelConversation(
                    id=hidden_conversation_id,
                    channel_instance_id=instance_id,
                    project_id=other_project_id,
                    participant_id="participant-2",
                    participant_name="Participant 2",
                ),
            ]
        )
        await db.commit()

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        messages = await ac.get(
            f"/api/channels/{instance_id}/messages?project_id={project_id}",
            headers=auth_headers,
        )
        missing_scope = await ac.get(f"/api/channels/{instance_id}/messages", headers=auth_headers)
        wrong_scope = await ac.get(
            f"/api/channels/{instance_id}/messages?project_id={other_project_id}",
            headers=auth_headers,
        )
        conversations = await ac.get(
            f"/api/channels/{instance_id}/conversations?project_id={project_id}",
            headers=auth_headers,
        )

    assert messages.status_code == 200
    assert [item["id"] for item in messages.json()] == [visible_message_id]
    assert missing_scope.status_code == 400
    assert wrong_scope.status_code == 404
    assert conversations.status_code == 200
    assert [item["id"] for item in conversations.json()] == [visible_conversation_id]


@pytest.mark.asyncio
async def test_channel_service_helpers_require_matching_project_scope():
    await init_db()
    project_id = f"channel-service-project-{uuid.uuid4()}"
    other_project_id = f"channel-service-other-{uuid.uuid4()}"

    async with async_session() as db:
        instance = await channel_service.create_channel_instance(
            db,
            platform="slack",
            name="Service Scoped Slack",
            config={"Bot Token": "xoxb-test", "Signing Secret": "secret"},
            project_id=project_id,
        )
        instance_id = instance.id

        assert await channel_service.list_channel_instances(db, project_id=other_project_id) == []
        assert await channel_service.delete_channel_instance(
            db, instance_id, project_id=other_project_id
        ) is False
        with pytest.raises(KeyError):
            await channel_service.start_channel_instance(
                db, instance_id, project_id=other_project_id
            )

        scoped = await channel_service.list_channel_instances(db, project_id=project_id)
        assert [item.id for item in scoped] == [instance_id]
        assert await channel_service.delete_channel_instance(
            db, instance_id, project_id=project_id
        ) is True


@pytest.mark.asyncio
async def test_channels_list_requires_auth():
    """Channels listing requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/channels")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_channel_create_normalizes_ui_credential_labels(auth_headers):
    await init_db()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/channels",
            headers=auth_headers,
            json={
                "platform": "slack",
                "name": "Research Slack",
                "project_id": "channel-credentials-project",
                "config": {
                    "Bot Token": " xoxb-test ",
                    "Signing Secret": " secret ",
                    "App Token": "",
                },
            },
        )

    assert response.status_code == 200
    instance_id = response.json()["id"]
    async with async_session() as db:
        result = await db.execute(select(ChannelInstance).where(ChannelInstance.id == instance_id))
        instance = result.scalar_one()
        stored = json.loads(decrypt_field(instance.config_json))

    assert stored == {"bot_token": "xoxb-test", "signing_secret": "secret"}


@pytest.mark.asyncio
async def test_channel_start_missing_config_reports_not_enabled(auth_headers, monkeypatch):
    await init_db()
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setattr("app.channels.telegram._TELEGRAM_AVAILABLE", True)
    transport = ASGITransport(app=app)
    project_id = f"channel-missing-config-project-{uuid.uuid4()}"

    async with async_session() as db:
        db.add(Project(id=project_id, name="Channel Missing Config Project"))
        await db.commit()

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        created = await ac.post(
            "/api/channels",
            headers=auth_headers,
            json={
                "platform": "telegram",
                "name": "Missing Token",
                "project_id": project_id,
                "config": {},
            },
        )
        assert created.status_code == 200
        instance_id = created.json()["id"]

        started = await ac.post(
            f"/api/channels/{instance_id}/start?project_id={project_id}",
            headers=auth_headers,
        )
        health = await ac.get(
            f"/api/channels/{instance_id}/health?project_id={project_id}",
            headers=auth_headers,
        )

    assert started.status_code == 200
    assert started.json()["status"] == "not_enabled"
    assert health.status_code == 200
    assert health.json()["status"] == "not_enabled"
    assert channel_router.get(instance_id) is None


@pytest.mark.asyncio
async def test_channel_start_rejects_paused_project(auth_headers):
    await init_db()
    project_id = f"paused-channel-project-{uuid.uuid4()}"
    transport = ASGITransport(app=app)

    async with async_session() as db:
        db.add(Project(id=project_id, name="Paused Channel Project", is_paused=True))
        await db.commit()

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        created = await ac.post(
            "/api/channels",
            headers=auth_headers,
            json={
                "platform": "slack",
                "name": "Paused Slack",
                "project_id": project_id,
                "config": {"Bot Token": "xoxb-test", "Signing Secret": "secret"},
            },
        )
        assert created.status_code == 200
        instance_id = created.json()["id"]

        started = await ac.post(
            f"/api/channels/{instance_id}/start?project_id={project_id}",
            headers=auth_headers,
        )

    assert started.status_code == 409
    assert started.json()["detail"] == "Project is paused"
    assert channel_router.get(instance_id) is None


@pytest.mark.asyncio
async def test_channel_startup_loader_skips_paused_projects():
    await init_db()
    project_id = f"paused-loader-project-{uuid.uuid4()}"
    instance_id = str(uuid.uuid4())

    async with async_session() as db:
        db.add(Project(id=project_id, name="Paused Loader Project", is_paused=True))
        db.add(
            ChannelInstance(
                id=instance_id,
                platform="telegram",
                name="Paused Telegram",
                config_json="{}",
                project_id=project_id,
                is_active=True,
            )
        )
        await db.commit()
        loaded = await channel_service.load_active_instances(db)

    assert loaded == 0
    assert channel_router.get(instance_id) is None


@pytest.mark.asyncio
async def test_record_message_rejects_cross_project_claim():
    await init_db()
    project_id = f"record-message-project-{uuid.uuid4()}"
    other_project_id = f"record-message-other-{uuid.uuid4()}"
    instance_id = str(uuid.uuid4())

    async with async_session() as db:
        db.add(
            ChannelInstance(
                id=instance_id,
                platform="slack",
                name="Scoped Slack",
                config_json="{}",
                project_id=project_id,
            )
        )
        await db.commit()

        with pytest.raises(ValueError, match="project_id does not match"):
            await channel_service.record_message(
                db,
                instance_id=instance_id,
                direction="inbound",
                sender_id="participant",
                sender_name="Participant",
                content="wrong project",
                project_id=other_project_id,
            )
