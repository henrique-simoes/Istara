"""Tests for channel router inbound processing and deployment routing."""

import json
import uuid

import pytest
from sqlalchemy import select

from app.channels.base import IncomingMessage
from app.models.channel_conversation import ChannelConversation
from app.models.channel_instance import ChannelInstance
from app.models.channel_message import ChannelMessage
from app.models.database import async_session, init_db
from app.models.project import Project
from app.models.research_deployment import ResearchDeployment
from app.services.inbound_processor import process_inbound_channel_message


@pytest.mark.asyncio
async def test_inbound_message_without_deployment_is_persisted():
    await init_db()
    instance_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())

    async with async_session() as db:
        db.add(Project(id=project_id, name="Inbound Project"))
        db.add(
            ChannelInstance(
                id=instance_id,
                platform="whatsapp",
                name="Research WhatsApp",
                config_json="{}",
                project_id=project_id,
            )
        )
        await db.commit()

    response = await process_inbound_channel_message(
        IncomingMessage(
            channel="whatsapp",
            channel_id="5511999999999",
            sender_id="5511999999999",
            sender_name="Ada",
            text="Audio transcript",
            instance_id=instance_id,
            attachments=["/tmp/audio.ogg"],
            metadata={"content_type": "audio", "external_message_id": "msg-1"},
        )
    )

    assert response is None
    async with async_session() as db:
        conversation = (
            await db.execute(
                select(ChannelConversation).where(
                    ChannelConversation.channel_instance_id == instance_id,
                    ChannelConversation.participant_id == "5511999999999",
                )
            )
        ).scalar_one()
        message = (
            await db.execute(
                select(ChannelMessage).where(ChannelMessage.channel_instance_id == instance_id)
            )
        ).scalar_one()
        instance = await db.get(ChannelInstance, instance_id)

    assert conversation.project_id == project_id
    assert conversation.deployment_id is None
    assert message.direction == "inbound"
    assert message.content_type == "audio"
    assert message.external_message_id == "msg-1"
    assert json.loads(message.metadata_json)["attachments"] == ["/tmp/audio.ogg"]
    assert instance.message_count == 1


@pytest.mark.asyncio
async def test_inbound_message_ignores_unbound_deployment_from_another_project():
    await init_db()
    instance_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    other_project_id = str(uuid.uuid4())

    async with async_session() as db:
        db.add(Project(id=project_id, name="Inbound Project"))
        db.add(Project(id=other_project_id, name="Other Inbound Project"))
        db.add(
            ChannelInstance(
                id=instance_id,
                platform="whatsapp",
                name="Project WhatsApp",
                config_json="{}",
                project_id=project_id,
            )
        )
        db.add(
            ResearchDeployment(
                id=str(uuid.uuid4()),
                project_id=other_project_id,
                name="Other Project Deployment",
                deployment_type="interview",
                questions_json=json.dumps([{"text": "Should not route"}]),
                config_json=json.dumps({"intro_message": "Hello from another project"}),
                channel_instance_ids_json=json.dumps([]),
                state="active",
            )
        )
        await db.commit()

    response = await process_inbound_channel_message(
        IncomingMessage(
            channel="whatsapp",
            channel_id="5511888888888",
            sender_id="5511888888888",
            sender_name="Lin",
            text="Hello",
            instance_id=instance_id,
            metadata={"content_type": "text", "external_message_id": "msg-cross-project"},
        )
    )

    assert response is None
    async with async_session() as db:
        conversation = (
            await db.execute(
                select(ChannelConversation).where(
                    ChannelConversation.channel_instance_id == instance_id,
                    ChannelConversation.participant_id == "5511888888888",
                )
            )
        ).scalar_one()

    assert conversation.project_id == project_id
    assert conversation.deployment_id is None


@pytest.mark.asyncio
async def test_inbound_active_deployment_advances_questions_without_repeating():
    await init_db()
    instance_id = str(uuid.uuid4())
    deployment_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())

    async with async_session() as db:
        db.add(Project(id=project_id, name="Active Deployment Project"))
        db.add(
            ChannelInstance(
                id=instance_id,
                platform="telegram",
                name="Research Telegram",
                config_json="{}",
                project_id=project_id,
            )
        )
        db.add(
            ResearchDeployment(
                id=deployment_id,
                project_id=project_id,
                name="Interview",
                deployment_type="interview",
                questions_json=json.dumps([{"text": "Q1"}, {"text": "Q2"}]),
                config_json=json.dumps({"intro_message": "Hello"}),
                channel_instance_ids_json=json.dumps([instance_id]),
                state="active",
            )
        )
        await db.commit()

    first_response = await process_inbound_channel_message(
        IncomingMessage(
            channel="telegram",
            channel_id="123",
            sender_id="123",
            sender_name="Ada",
            text="start",
            instance_id=instance_id,
            metadata={"content_type": "text", "external_message_id": "msg-1"},
        )
    )
    assert first_response is not None
    assert "Q1" in first_response.text

    second_response = await process_inbound_channel_message(
        IncomingMessage(
            channel="telegram",
            channel_id="123",
            sender_id="123",
            sender_name="Ada",
            text="Answer one",
            instance_id=instance_id,
            metadata={"content_type": "text", "external_message_id": "msg-2"},
        )
    )

    assert second_response is not None
    assert second_response.text == "Q2"

    async with async_session() as db:
        conversation = (
            await db.execute(
                select(ChannelConversation).where(
                    ChannelConversation.channel_instance_id == instance_id,
                    ChannelConversation.participant_id == "123",
                    ChannelConversation.deployment_id == deployment_id,
                )
            )
        ).scalar_one()
        messages = (
            await db.execute(
                select(ChannelMessage)
                .where(ChannelMessage.channel_instance_id == instance_id)
                .order_by(ChannelMessage.created_at.asc())
            )
        ).scalars().all()
        instance = await db.get(ChannelInstance, instance_id)

    assert conversation.state == "questions"
    assert conversation.current_question_index == 2
    assert [m.direction for m in messages] == ["inbound", "outbound", "inbound", "outbound"]
    assert messages[-1].content == "Q2"
    assert instance.message_count == 4


@pytest.mark.asyncio
async def test_inbound_message_for_paused_project_is_not_persisted_or_routed():
    await init_db()
    instance_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    deployment_id = str(uuid.uuid4())

    async with async_session() as db:
        db.add(Project(id=project_id, name="Paused Inbound Project", is_paused=True))
        db.add(
            ChannelInstance(
                id=instance_id,
                platform="telegram",
                name="Paused Telegram",
                config_json="{}",
                project_id=project_id,
            )
        )
        db.add(
            ResearchDeployment(
                id=deployment_id,
                project_id=project_id,
                name="Paused Interview",
                deployment_type="interview",
                questions_json=json.dumps([{"text": "Should not route"}]),
                config_json=json.dumps({"intro_message": "Hello"}),
                channel_instance_ids_json=json.dumps([instance_id]),
                state="active",
            )
        )
        await db.commit()

    response = await process_inbound_channel_message(
        IncomingMessage(
            channel="telegram",
            channel_id="123",
            sender_id="123",
            sender_name="Ada",
            text="start",
            instance_id=instance_id,
            metadata={"content_type": "text", "external_message_id": "msg-paused"},
        )
    )

    assert response is None
    async with async_session() as db:
        messages = (
            await db.execute(
                select(ChannelMessage).where(ChannelMessage.channel_instance_id == instance_id)
            )
        ).scalars().all()
        conversations = (
            await db.execute(
                select(ChannelConversation).where(
                    ChannelConversation.channel_instance_id == instance_id
                )
            )
        ).scalars().all()
        instance = await db.get(ChannelInstance, instance_id)

    assert messages == []
    assert conversations == []
    assert instance.message_count == 0
