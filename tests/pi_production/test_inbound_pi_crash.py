"""H-8: the ``pi_local`` turn runs OUTSIDE the inbound DB transaction.

The inbound processor must persist and commit the inbound row first, run the
Pi turn, then persist the outbound reply in a fresh session — so a crash mid
turn can never roll the inbound record back. Deterministic fakes drive the
``build_pi_channel_reply`` seam directly; no node worker is spawned.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.channels.base import IncomingMessage, OutgoingMessage
from app.models.channel_instance import ChannelInstance
from app.models.channel_message import ChannelMessage
from app.models.database import async_session, init_db
from app.models.project import Project
from app.services import channel_service, inbound_processor
from app.services.inbound_processor import process_inbound_channel_message


async def _pi_project_and_instance(name: str) -> tuple[str, str]:
    await init_db()
    project_id = f"pi-h8-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name=name))
        await db.commit()
        instance = await channel_service.create_channel_instance(
            db,
            platform="pi_local",
            name=name,
            config={"enabled": True},
            project_id=project_id,
        )
    return project_id, instance.id


def _inbound(instance_id: str, text: str = "please note this") -> IncomingMessage:
    return IncomingMessage(
        channel="pi_local",
        channel_id="pi-local",
        sender_id="participant-1",
        sender_name="Participant",
        text=text,
        instance_id=instance_id,
        metadata={"pi_candidate": True},
    )


@pytest.mark.asyncio
async def test_crash_mid_turn_keeps_inbound_row_committed(monkeypatch):
    """The turn raising mid-stream must not roll back the committed inbound row."""
    _project_id, instance_id = await _pi_project_and_instance("Pi Local H-8 crash")

    async def _crash(**kwargs):
        raise RuntimeError("worker exploded mid-turn")

    monkeypatch.setattr(inbound_processor, "build_pi_channel_reply", _crash)

    with pytest.raises(RuntimeError, match="worker exploded mid-turn"):
        await process_inbound_channel_message(_inbound(instance_id))

    async with async_session() as db:
        msgs = (
            (
                await db.execute(
                    select(ChannelMessage).where(
                        ChannelMessage.channel_instance_id == instance_id
                    )
                )
            )
            .scalars()
            .all()
        )
        instance = await db.get(ChannelInstance, instance_id)

    assert [m.direction for m in msgs] == ["inbound"]
    assert msgs[0].content == "please note this"
    assert instance is not None
    assert instance.message_count == 1


@pytest.mark.asyncio
async def test_successful_turn_persists_outbound_in_new_session(monkeypatch):
    """Happy path: inbound committed first, outbound reply written afterwards."""
    _project_id, instance_id = await _pi_project_and_instance("Pi Local H-8 ok")

    async def _reply(**kwargs):
        return OutgoingMessage(
            channel="pi_local",
            channel_id="pi-local",
            text="pi reply",
            instance_id=kwargs["instance_id"],
            metadata={
                "pi_replacement": True,
                "inbound_message_id": kwargs["inbound_message_id"],
            },
        )

    monkeypatch.setattr(inbound_processor, "build_pi_channel_reply", _reply)

    response = await process_inbound_channel_message(_inbound(instance_id))
    assert response is not None
    assert response.text == "pi reply"

    async with async_session() as db:
        msgs = (
            (
                await db.execute(
                    select(ChannelMessage).where(
                        ChannelMessage.channel_instance_id == instance_id
                    )
                )
            )
            .scalars()
            .all()
        )
        instance = await db.get(ChannelInstance, instance_id)

    assert sorted(m.direction for m in msgs) == ["inbound", "outbound"]
    outbound = next(m for m in msgs if m.direction == "outbound")
    assert outbound.content == "pi reply"
    assert instance is not None
    assert instance.message_count == 2
