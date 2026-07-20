"""Production scenario 8 (channel.lifecycle.simulated_slice) — the ``pi_local``
channel reply is produced by the real in-process Pi loop (the canned response is
gone), and inbound + outbound are persisted with zero external channel traffic.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.channels.base import IncomingMessage
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
async def test_scenario8_pi_local_channel_reply_is_real_loop_and_persists(monkeypatch):
    await init_db()
    project_id = f"pi-prod-s8-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Pi Production Scenario 8"))
        await db.commit()
        instance = await channel_service.create_channel_instance(
            db, platform="pi_local", name="Pi Local S8", config={"enabled": True}, project_id=project_id
        )
    instance_id = instance.id

    reply_text = "Real Pi loop reply: I logged your request for the team."
    sup = PiRuntimeSupervisor()
    monkeypatch.setattr(seams, "_service", faux_service([final_text(reply_text)], sup))

    try:
        response = await process_inbound_channel_message(
            IncomingMessage(
                channel="pi_local",
                channel_id="pi-local",
                sender_id="participant-1",
                sender_name="Participant",
                text="Can you note that we need an accessibility pass?",
                instance_id=instance_id,
                metadata={"pi_candidate": True},
            )
        )
    finally:
        await sup.shutdown()

    # The response is the real Pi loop's text — not the deleted canned string.
    assert response is not None
    assert response.text == reply_text
    assert "recorded the inbound channel message for local benchmark" not in response.text
    assert response.metadata.get("engine") == "pi"

    async with async_session() as db:
        msgs = (
            await db.execute(
                select(ChannelMessage)
                .where(ChannelMessage.channel_instance_id == instance_id)
                .order_by(ChannelMessage.direction)
            )
        ).scalars().all()
    directions = sorted(m.direction for m in msgs)
    assert directions == ["inbound", "outbound"]
    outbound = [m for m in msgs if m.direction == "outbound"][0]
    assert outbound.content == reply_text
    assert sup.is_running is False


@pytest.mark.asyncio
async def test_scenario8_channel_fails_closed_when_runtime_unavailable(monkeypatch):
    """When Pi is selected but the runtime is unavailable, the channel fails
    closed (no reply), never a canned or fabricated response."""
    await init_db()
    project_id = f"pi-prod-s8fc-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Pi Production Scenario 8 FC"))
        await db.commit()
        instance = await channel_service.create_channel_instance(
            db, platform="pi_local", name="Pi Local S8 FC", config={"enabled": True}, project_id=project_id
        )
    instance_id = instance.id

    from app.core.pi_runtime.endpoints import PiEndpointResolutionError

    class _DeadService:
        async def run_channel_turn(self, **_kw):
            raise PiEndpointResolutionError("missing_keychain_secret")

    monkeypatch.setattr(seams, "_service", _DeadService())

    response = await process_inbound_channel_message(
        IncomingMessage(
            channel="pi_local",
            channel_id="pi-local",
            sender_id="participant-1",
            sender_name="Participant",
            text="hello",
            instance_id=instance_id,
            metadata={"pi_candidate": True},
        )
    )

    assert response is None  # fail closed
    async with async_session() as db:
        msgs = (
            await db.execute(
                select(ChannelMessage).where(ChannelMessage.channel_instance_id == instance_id)
            )
        ).scalars().all()
    # Inbound is still recorded; no outbound reply was fabricated.
    assert [m.direction for m in msgs] == ["inbound"]
