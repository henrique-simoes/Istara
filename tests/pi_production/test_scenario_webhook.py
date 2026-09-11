"""Production scenario 12 (channels.webhook.telegram.lifecycle) — a Telegram-like
inbound (the webhook-style external platform) is handled by the real in-process
Pi loop with ZERO external channel traffic: the outbound adapter transport is
spied and never fires, and the inbound→outbound lifecycle is persisted in order.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.channels.base import IncomingMessage
from app.channels.telegram import TelegramAdapter
from app.core.pi_runtime import seams
from app.core.pi_runtime.supervisor import PiRuntimeSupervisor
from app.models.channel_message import ChannelMessage
from app.models.database import async_session, init_db
from app.models.project import Project
from app.services import channel_service
from app.services.inbound_processor import process_inbound_channel_message

from .harness import faux_service, final_text, requires_node

pytestmark = requires_node


@pytest.mark.asyncio
async def test_scenario12_telegram_inbound_uses_real_loop_with_zero_external_traffic(
    monkeypatch,
):
    await init_db()
    project_id = f"pi-prod-s12-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Pi Production Scenario 12"))
        await db.commit()
        instance = await channel_service.create_channel_instance(
            db,
            platform="telegram",
            name="Pi Telegram S12",
            config={"bot_token": "unused"},
            project_id=project_id,
        )
    instance_id = instance.id

    # Transport spy with teeth: if any code path tries to send over the real
    # Telegram adapter, the test fails — proving zero external channel egress.
    sent: list[object] = []

    async def _spy_send(self, message):
        sent.append(message)
        raise AssertionError(
            "external Telegram transport must never be used in-process"
        )

    monkeypatch.setattr(TelegramAdapter, "send", _spy_send)

    reply_text = "Real Pi loop reply over the Telegram fixture: noted your request."
    sup = PiRuntimeSupervisor()
    monkeypatch.setattr(seams, "_service", faux_service([final_text(reply_text)], sup))

    try:
        response = await process_inbound_channel_message(
            IncomingMessage(
                channel="telegram",
                channel_id="123456789",
                sender_id="tg-user-1",
                sender_name="Telegram User",
                text="Please log a follow-up for the team.",
                instance_id=instance_id,
                metadata={"pi_candidate": True, "external_message_id": "tg-msg-1"},
            )
        )
    finally:
        await sup.shutdown()

    # The reply is the real in-process Pi loop's output; the transport never fired.
    assert response is not None
    assert response.text == reply_text
    assert response.metadata.get("engine") == "pi"
    assert sent == []  # zero external Telegram traffic

    # Lifecycle ordering: inbound then outbound, both persisted under the project.
    async with async_session() as db:
        msgs = (
            (
                await db.execute(
                    select(ChannelMessage)
                    .where(ChannelMessage.channel_instance_id == instance_id)
                    .order_by(ChannelMessage.created_at)
                )
            )
            .scalars()
            .all()
        )
        await channel_service.stop_channel_instance(
            db, instance_id, project_id=project_id
        )
    assert [m.direction for m in msgs] == ["inbound", "outbound"]
    assert msgs[1].content == reply_text
    assert all(m.project_id == project_id for m in msgs)
    assert sup.is_running is False
