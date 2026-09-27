"""Participant flow through a channel research deployment (professional-readiness Phase 1).

Each test drives a scripted participant through ``process_inbound_channel_message`` and then
checks exactly what was stored as research data. Strict equality on counts and texts: the old
suite asserted ``len(nuggets) >= 1`` and missed that a greeting was stored as an answer.
"""

from __future__ import annotations

import app.core.agentic  # noqa: F401  (import-order guard, see tests/test_deployments.py)

import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.channels.base import IncomingMessage
from app.models.channel_conversation import ChannelConversation
from app.models.channel_instance import ChannelInstance
from app.models.channel_message import ChannelMessage
from app.models.database import async_session, init_db
from app.models.finding import Nugget
from app.models.project import Project
from app.models.research_deployment import ResearchDeployment
from app.models.research_validity import EvidenceUnit
from app.services import adaptive_interview
from app.services.inbound_processor import process_inbound_channel_message


async def _seed(questions: list[str], config: dict, *, target: int = 0, platform: str = "telegram"):
    await init_db()
    project_id = str(uuid.uuid4())
    instance_id = str(uuid.uuid4())
    deployment_id = str(uuid.uuid4())
    async with async_session() as db:
        db.add(Project(id=project_id, name=f"Flow {project_id[:8]}"))
        db.add(
            ChannelInstance(
                id=instance_id,
                platform=platform,
                name="Research channel",
                config_json="{}",
                project_id=project_id,
            )
        )
        db.add(
            ResearchDeployment(
                id=deployment_id,
                project_id=project_id,
                name="Flow study",
                deployment_type="interview",
                questions_json=json.dumps([{"text": q} for q in questions]),
                config_json=json.dumps(config),
                channel_instance_ids_json=json.dumps([instance_id]),
                state="active",
                target_responses=target,
            )
        )
        await db.commit()
    return project_id, instance_id, deployment_id


async def _say(instance_id: str, sender: str, text: str, platform: str = "telegram"):
    return await process_inbound_channel_message(
        IncomingMessage(
            channel=platform,
            channel_id=f"chat-{sender}",
            sender_id=sender,
            sender_name=sender,
            text=text,
            instance_id=instance_id,
            metadata={"content_type": "text"},
        )
    )


async def _stored(project_id: str) -> tuple[list[str], list[str]]:
    async with async_session() as db:
        nuggets = (
            (
                await db.execute(
                    select(Nugget)
                    .where(Nugget.project_id == project_id)
                    .order_by(Nugget.created_at.asc())
                )
            )
            .scalars()
            .all()
        )
        units = (
            (await db.execute(select(EvidenceUnit).where(EvidenceUnit.project_id == project_id)))
            .scalars()
            .all()
        )
    return [n.text for n in nuggets], [u.source_text for u in units]


async def _conversation(instance_id: str, sender: str) -> ChannelConversation:
    async with async_session() as db:
        return (
            await db.execute(
                select(ChannelConversation).where(
                    ChannelConversation.channel_instance_id == instance_id,
                    ChannelConversation.participant_id == sender,
                )
            )
        ).scalar_one()


@pytest.mark.asyncio
async def test_greeting_before_any_question_is_not_stored_as_an_answer():
    project_id, instance_id, _ = await _seed(["What slows you down?"], {"intro_message": "Hi"})

    reply = await _say(instance_id, "p1", "hello, ready")
    assert reply is not None and "What slows you down?" in reply.text
    await _say(instance_id, "p1", "Exports take ages")

    nuggets, units = await _stored(project_id)
    assert nuggets == ["Q: What slows you down?\nA: Exports take ages"]
    # The evidence unit is the participant's answer only; the question is context, not data.
    assert units == ["Exports take ages"]


@pytest.mark.asyncio
async def test_closing_question_is_asked_alone_and_its_answer_is_stored():
    project_id, instance_id, deployment_id = await _seed(
        ["What slows you down?"],
        {"closing_question": "Anything else?", "thank_you_message": "Thanks!"},
    )
    await _say(instance_id, "p1", "hi")
    closing = await _say(instance_id, "p1", "Exports take ages")
    assert closing is not None
    assert closing.text == "Anything else?"

    thanks = await _say(instance_id, "p1", "The search is great")
    assert thanks is not None and thanks.text == "Thanks!"

    nuggets, _ = await _stored(project_id)
    assert nuggets == [
        "Q: What slows you down?\nA: Exports take ages",
        "Q: Anything else?\nA: The search is great",
    ]
    conversation = await _conversation(instance_id, "p1")
    assert conversation.state == "completed"
    async with async_session() as db:
        deployment = await db.get(ResearchDeployment, deployment_id)
    assert deployment.current_responses == 1


@pytest.mark.asyncio
async def test_wizard_adaptive_setting_turns_follow_ups_on(monkeypatch):
    async def fake_clarification(*_args, **_kwargs):
        return "Could you tell me more about that?"

    monkeypatch.setattr(adaptive_interview, "generate_clarification", fake_clarification)
    project_id, instance_id, _ = await _seed(
        ["What slows you down?", "What do you like?"],
        {"adaptive_enabled": True, "max_follow_ups": 1},
    )
    await _say(instance_id, "p1", "hi")
    probe = await _say(instance_id, "p1", "exports")
    assert probe is not None and probe.text == "Could you tell me more about that?"

    after_probe = await _say(instance_id, "p1", "They time out on big projects")
    assert after_probe is not None and after_probe.text == "What do you like?"

    nuggets, _ = await _stored(project_id)
    assert nuggets == [
        "Q: What slows you down?\nA: exports",
        "Q: Could you tell me more about that?\nA: They time out on big projects",
    ]


@pytest.mark.asyncio
async def test_wizard_adaptive_setting_off_asks_no_follow_up(monkeypatch):
    async def fake_clarification(*_args, **_kwargs):
        return "Could you tell me more about that?"

    monkeypatch.setattr(adaptive_interview, "generate_clarification", fake_clarification)
    _, instance_id, _ = await _seed(
        ["What slows you down?", "What do you like?"],
        {"adaptive_enabled": False, "max_follow_ups": 2},
    )
    await _say(instance_id, "p1", "hi")
    reply = await _say(instance_id, "p1", "exports")
    assert reply is not None and reply.text == "What do you like?"


@pytest.mark.asyncio
async def test_failed_follow_up_moves_on_instead_of_sending_nothing(monkeypatch):
    calls = {"n": 0}

    async def flaky_clarification(*_args, **_kwargs):
        calls["n"] += 1
        return "Tell me more?" if calls["n"] == 1 else None

    monkeypatch.setattr(adaptive_interview, "generate_clarification", flaky_clarification)
    _, instance_id, _ = await _seed(
        ["What slows you down?", "What do you like?"],
        {"adaptive": True, "max_probes_per_question": 3},
    )
    await _say(instance_id, "p1", "hi")
    assert (await _say(instance_id, "p1", "exports")).text == "Tell me more?"
    # Long enough not to count as saturated, so the engine must try (and fail) a second probe.
    reply = await _say(instance_id, "p1", "it gets slow on big exports every week")
    assert reply is not None and reply.text == "What do you like?"


@pytest.mark.asyncio
async def test_consent_declined_stores_nothing_and_asks_nothing():
    project_id, instance_id, _ = await _seed(
        ["What slows you down?"], {"consent_required": True, "intro_message": "Hi"}
    )
    invite = await _say(instance_id, "p1", "hello")
    assert invite is not None
    assert "YES" in invite.text and "What slows you down?" not in invite.text

    goodbye = await _say(instance_id, "p1", "No")
    assert goodbye is not None and "What slows you down?" not in goodbye.text
    after = await _say(instance_id, "p1", "actually exports are slow")

    assert after is None or "What slows you down?" not in after.text
    nuggets, units = await _stored(project_id)
    assert nuggets == [] and units == []
    conversation = await _conversation(instance_id, "p1")
    assert conversation.state == "declined"


@pytest.mark.asyncio
async def test_consent_given_then_questions_and_only_answers_are_stored():
    project_id, instance_id, _ = await _seed(
        ["What slows you down?"], {"consent_required": True, "intro_message": "Hi"}
    )
    await _say(instance_id, "p1", "hello")
    first_question = await _say(instance_id, "p1", "yes")
    assert first_question is not None and "What slows you down?" in first_question.text
    await _say(instance_id, "p1", "Exports take ages")

    nuggets, units = await _stored(project_id)
    assert nuggets == ["Q: What slows you down?\nA: Exports take ages"]
    assert all(text.strip().lower() not in {"yes", "hello"} for text in units)
    metadata = json.loads((await _conversation(instance_id, "p1")).metadata_json)
    assert metadata["consent"]["given"] is True


@pytest.mark.asyncio
async def test_unclear_consent_is_asked_again_then_treated_as_no():
    project_id, instance_id, _ = await _seed(["What slows you down?"], {"consent_required": True})
    await _say(instance_id, "p1", "hello")
    again = await _say(instance_id, "p1", "what is this?")
    assert again is not None and "YES" in again.text
    await _say(instance_id, "p1", "hmm")
    assert (await _conversation(instance_id, "p1")).state == "declined"
    assert await _stored(project_id) == ([], [])


@pytest.mark.asyncio
async def test_stop_withdraws_and_nothing_after_is_stored():
    project_id, instance_id, _ = await _seed(["Q one?", "Q two?"], {})
    await _say(instance_id, "p1", "hi")
    await _say(instance_id, "p1", "answer one")
    bye = await _say(instance_id, "p1", "STOP")
    assert bye is not None and "Q two?" not in bye.text
    await _say(instance_id, "p1", "answer two")

    nuggets, _ = await _stored(project_id)
    assert nuggets == ["Q: Q one?\nA: answer one"]
    assert (await _conversation(instance_id, "p1")).state == "withdrawn"


@pytest.mark.asyncio
async def test_screener_screens_out_without_storing_research_data():
    project_id, instance_id, _ = await _seed(
        ["What slows you down?"],
        {"screener": [{"text": "Do you export reports weekly?", "accept": ["yes"]}]},
    )
    screener = await _say(instance_id, "p1", "hi")
    assert screener is not None and "Do you export reports weekly?" in screener.text
    out = await _say(instance_id, "p1", "no")
    assert out is not None and "What slows you down?" not in out.text
    assert (await _conversation(instance_id, "p1")).state == "screened_out"
    assert await _stored(project_id) == ([], [])

    await _say(instance_id, "p2", "hi")
    qualified = await _say(instance_id, "p2", "Yes")
    assert qualified is not None and "What slows you down?" in qualified.text
    metadata = json.loads((await _conversation(instance_id, "p2")).metadata_json)
    assert metadata["screener_answers"] == [
        {"question": "Do you export reports weekly?", "answer": "Yes", "qualified": True}
    ]


@pytest.mark.asyncio
async def test_quota_refuses_new_participants_once_target_is_reached():
    project_id, instance_id, _ = await _seed(["Only question?"], {}, target=1)
    await _say(instance_id, "p1", "hi")
    await _say(instance_id, "p1", "my answer")
    assert (await _conversation(instance_id, "p1")).state == "completed"

    full = await _say(instance_id, "p2", "hi")
    assert full is not None and "Only question?" not in full.text
    await _say(instance_id, "p2", "my answer anyway")

    nuggets, _ = await _stored(project_id)
    assert nuggets == ["Q: Only question?\nA: my answer"]
    assert (await _conversation(instance_id, "p2")).state == "closed_quota"


@pytest.mark.asyncio
async def test_paused_study_does_not_hand_participants_to_the_project_agent(monkeypatch):
    import app.services.inbound_processor as inbound

    async def forbidden_pi_reply(**_kwargs):
        raise AssertionError("a study participant must not reach the project's agent")

    monkeypatch.setattr(inbound, "build_pi_channel_reply", forbidden_pi_reply)
    project_id, instance_id, deployment_id = await _seed(["Q one?", "Q two?"], {})
    await _say(instance_id, "p1", "hi")
    await _say(instance_id, "p1", "answer one")
    async with async_session() as db:
        deployment = await db.get(ResearchDeployment, deployment_id)
        deployment.state = "paused"
        await db.commit()

    reply = await _say(instance_id, "p1", "answer two")
    assert reply is not None and "paused" in reply.text.lower()
    nuggets, _ = await _stored(project_id)
    assert nuggets == ["Q: Q one?\nA: answer one"]


@pytest.mark.asyncio
async def test_finished_participant_of_a_closed_study_gets_no_agent_and_no_reply(monkeypatch):
    import app.services.inbound_processor as inbound

    async def forbidden_pi_reply(**_kwargs):
        raise AssertionError("a study participant must not reach the project's agent")

    monkeypatch.setattr(inbound, "build_pi_channel_reply", forbidden_pi_reply)
    project_id, instance_id, deployment_id = await _seed(["Only question?"], {})
    await _say(instance_id, "p1", "hi")
    await _say(instance_id, "p1", "my answer")
    async with async_session() as db:
        deployment = await db.get(ResearchDeployment, deployment_id)
        deployment.state = "completed"
        await db.commit()

    assert await _say(instance_id, "p1", "one more thought") is None
    nuggets, _ = await _stored(project_id)
    assert nuggets == ["Q: Only question?\nA: my answer"]


class _RecordingAdapter:
    def __init__(self):
        self.sent = []

    async def send(self, message):
        self.sent.append(message)


@pytest.mark.asyncio
async def test_reminder_is_sent_once_to_a_participant_who_went_quiet(monkeypatch):
    from app.channels.base import channel_router
    from app.services import deployment_reminders

    project_id, instance_id, _ = await _seed(
        ["Q one?", "Q two?"], {"reminder_after_hours": 24, "max_reminders": 1}
    )
    await _say(instance_id, "p1", "hi")
    await _say(instance_id, "p1", "answer one")
    adapter = _RecordingAdapter()
    monkeypatch.setattr(channel_router, "get_by_instance_id", lambda _id: adapter)

    now = datetime.now(UTC)
    assert await deployment_reminders.send_due_reminders(now=now + timedelta(hours=1)) == 0
    assert await deployment_reminders.send_due_reminders(now=now + timedelta(hours=25)) == 1
    assert await deployment_reminders.send_due_reminders(now=now + timedelta(hours=50)) == 0

    assert len(adapter.sent) == 1
    assert adapter.sent[0].channel_id == "chat-p1"
    assert "Q two?" in adapter.sent[0].text
    async with async_session() as db:
        outbound = (
            (
                await db.execute(
                    select(ChannelMessage).where(
                        ChannelMessage.channel_instance_id == instance_id,
                        ChannelMessage.direction == "outbound",
                    )
                )
            )
            .scalars()
            .all()
        )
    assert sum(1 for m in outbound if "reminder" in (m.metadata_json or "")) == 1
    nuggets, _ = await _stored(project_id)
    assert nuggets == ["Q: Q one?\nA: answer one"]


@pytest.mark.asyncio
async def test_no_reminder_for_completed_or_declined_conversations(monkeypatch):
    from app.channels.base import channel_router
    from app.services import deployment_reminders

    _, instance_id, _ = await _seed(
        ["Q one?"], {"consent_required": True, "reminder_after_hours": 1, "max_reminders": 2}
    )
    await _say(instance_id, "p1", "hi")
    await _say(instance_id, "p1", "no")
    adapter = _RecordingAdapter()
    monkeypatch.setattr(channel_router, "get_by_instance_id", lambda _id: adapter)
    sent = await deployment_reminders.send_due_reminders(
        now=datetime.now(UTC) + timedelta(hours=10)
    )
    assert sent == 0 and adapter.sent == []
