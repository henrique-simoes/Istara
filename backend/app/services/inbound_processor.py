"""Inbound message processor bridging channel adapters to research deployments."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, select

from app.api.websocket import broadcast_channel_status
from app.channels.base import IncomingMessage, OutgoingMessage
from app.core.pi_runtime.seams import build_pi_channel_reply
from app.models.channel_conversation import ChannelConversation
from app.models.channel_instance import ChannelInstance
from app.models.channel_message import ChannelMessage
from app.models.database import async_session
from app.models.finding import Nugget
from app.models.project import Project
from app.models.research_deployment import ResearchDeployment
from app.services.adaptive_interview import (
    ANSWER_PROMPT_KINDS,
    DEFAULT_PAUSED_MESSAGE,
    DEFAULT_QUOTA_FULL_MESSAGE,
    FINISHED_STATES,
    ConversationState,
    get_next_action,
    is_withdrawal,
    update_conversation_metadata,
)
from app.services.research_validity_service import persist_task_nugget_evidence_units

logger = logging.getLogger(__name__)


def _safe_json_list(value: str | None) -> list:
    try:
        parsed = json.loads(value or "[]")
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _state_value(value: object, default: str = "active") -> str:
    if hasattr(value, "value"):
        return str(getattr(value, "value"))
    return str(value or default)


async def _active_deployment_for_instance(
    db,
    instance: ChannelInstance,
) -> ResearchDeployment | None:
    """Return the active deployment bound to a channel instance, if any."""
    result = await db.execute(
        select(ResearchDeployment).where(
            ResearchDeployment.state == "active",
            ResearchDeployment.project_id == instance.project_id,
        )
    )
    deployments = result.scalars().all()

    for deployment in deployments:
        channel_ids = _safe_json_list(deployment.channel_instance_ids_json)
        if instance.id in channel_ids:
            return deployment
    return None


async def _get_or_create_conversation(
    db,
    *,
    instance_id: str,
    project_id: str | None,
    deployment_id: str | None,
    participant_id: str,
    participant_name: str,
) -> ChannelConversation:
    conditions = [
        ChannelConversation.channel_instance_id == instance_id,
        ChannelConversation.project_id == project_id,
        ChannelConversation.participant_id == participant_id,
    ]
    if deployment_id:
        conditions.append(ChannelConversation.deployment_id == deployment_id)
    else:
        conditions.append(ChannelConversation.deployment_id.is_(None))

    result = await db.execute(select(ChannelConversation).where(and_(*conditions)))
    conversation = result.scalar_one_or_none()
    if conversation:
        return conversation

    conversation = ChannelConversation(
        id=str(uuid.uuid4()),
        channel_instance_id=instance_id,
        project_id=project_id,
        participant_id=participant_id,
        participant_name=participant_name,
        deployment_id=deployment_id,
        state="intro" if deployment_id else "active",
        current_question_index=0,
        started_at=datetime.now(UTC),
    )
    db.add(conversation)
    await db.flush()
    return conversation


def _conversation_metadata(conversation: ChannelConversation) -> dict:
    try:
        parsed = json.loads(conversation.metadata_json or "{}")
    except (json.JSONDecodeError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


async def _participant_in_held_study(
    db,
    instance: ChannelInstance,
    participant_id: str,
) -> tuple[ChannelConversation, ResearchDeployment] | None:
    """Return an unfinished study conversation whose deployment is paused or closed.

    A participant part-way through a study must never be handed to the project's agent when the
    study stops being active: that agent can read the project's research data.
    """
    result = await db.execute(
        select(ChannelConversation).where(
            ChannelConversation.channel_instance_id == instance.id,
            ChannelConversation.project_id == instance.project_id,
            ChannelConversation.participant_id == participant_id,
            ChannelConversation.deployment_id.is_not(None),
        )
    )
    conversations = sorted(
        result.scalars().all(),
        key=lambda c: c.last_message_at or c.started_at or datetime.min.replace(tzinfo=UTC),
        reverse=True,
    )
    for conversation in conversations:
        deployment = await db.get(ResearchDeployment, conversation.deployment_id)
        if deployment is not None and deployment.state != "active":
            return conversation, deployment
    return None


def _answered_prompt(
    conversation: ChannelConversation,
    metadata: dict,
    questions: list,
    text: str,
) -> dict | None:
    """Return the prompt this message answers, or None when it is not a research answer.

    Only replies to a question, a follow-up probe or the closing question are research answers.
    Greetings, consent replies, screener answers and withdrawals are not.
    """
    if not text or is_withdrawal(text):
        return None
    state = metadata.get("state") or conversation.state
    pending = metadata.get("pending_prompt")
    if isinstance(pending, dict):
        if pending.get("kind") in ANSWER_PROMPT_KINDS and state in {
            ConversationState.QUESTIONS.value,
            ConversationState.PROBING.value,
            ConversationState.CLOSING.value,
        }:
            return pending
        return None
    # Conversations started before pending prompts were recorded: attribute to the question last
    # shown, and never store anything sent before the first question.
    q_idx = conversation.current_question_index
    if state in {ConversationState.QUESTIONS.value, ConversationState.PROBING.value} and (
        0 < q_idx <= len(questions)
    ):
        item = questions[q_idx - 1]
        return {
            "kind": "question",
            "text": item.get("text", f"Question {q_idx}") if isinstance(item, dict) else str(item),
            "question_index": q_idx,
        }
    return None


def _record_outbound(
    db,
    *,
    instance: ChannelInstance,
    project_id: str | None,
    conversation: ChannelConversation,
    text: str,
    metadata: dict,
) -> None:
    db.add(
        ChannelMessage(
            id=str(uuid.uuid4()),
            channel_instance_id=instance.id,
            project_id=project_id,
            direction="outbound",
            sender_id="system",
            sender_name="Istara",
            content=text,
            content_type="text",
            thread_id=conversation.id,
            metadata_json=json.dumps(metadata),
        )
    )
    instance.message_count = (instance.message_count or 0) + 1


async def process_inbound_channel_message(
    message: IncomingMessage,
) -> OutgoingMessage | None:
    """Persist and route an inbound channel message.

    This is the callback installed on ``channel_router``. It records inbound
    traffic even when no deployment is active, then returns an OutgoingMessage
    for active adaptive deployments so the router can send it through the same
    adapter that received the original message.
    """
    logger.info(
        "Processing inbound %s message from %s",
        message.channel,
        message.sender_id,
    )

    async with async_session() as db:
        instance = await db.get(ChannelInstance, message.instance_id)
        if instance is None:
            logger.warning(
                "Dropping inbound %s message for unknown channel instance %s",
                message.channel,
                message.instance_id,
            )
            return None
        if not instance.project_id:
            logger.warning(
                "Dropping inbound %s message for unscoped channel instance %s",
                message.channel,
                message.instance_id,
            )
            return None
        project = await db.get(Project, instance.project_id)
        if project is None or project.is_paused:
            logger.info(
                "Dropping inbound %s message for paused or missing project %s",
                message.channel,
                instance.project_id,
            )
            await broadcast_channel_status(
                message.instance_id,
                "paused",
                "Project is paused or not found; inbound processing skipped.",
            )
            return None

        deployment = await _active_deployment_for_instance(db, instance)
        project_id = deployment.project_id if deployment else instance.project_id
        now = datetime.now(UTC)

        if deployment is None:
            held = await _participant_in_held_study(db, instance, message.sender_id)
            if held is not None:
                held_conversation, held_deployment = held
                held_state = (
                    _conversation_metadata(held_conversation).get("state")
                    or held_conversation.state
                )
                held_conversation.last_message_at = now
                db.add(
                    ChannelMessage(
                        id=str(uuid.uuid4()),
                        channel_instance_id=message.instance_id,
                        project_id=project_id,
                        direction="inbound",
                        sender_id=message.sender_id,
                        sender_name=message.sender_name or message.sender_id,
                        content=message.text,
                        content_type=(message.metadata or {}).get("content_type", "text"),
                        thread_id=held_conversation.id,
                        external_message_id=(message.metadata or {}).get("external_message_id"),
                        metadata_json=json.dumps({**(message.metadata or {}), "study_held": True}),
                    )
                )
                instance.message_count = (instance.message_count or 0) + 1
                if held_state in FINISHED_STATES:
                    # The participant already finished, declined or left: record the message,
                    # send nothing, and never hand them to the project's agent.
                    await db.commit()
                    return None
                held_text = (
                    DEFAULT_PAUSED_MESSAGE
                    if held_deployment.state == "paused"
                    else "This study has closed. Thank you for taking part!"
                )
                reply_metadata = {
                    "deployment_id": held_deployment.id,
                    "conversation_id": held_conversation.id,
                    "study_state": held_deployment.state,
                }
                _record_outbound(
                    db,
                    instance=instance,
                    project_id=project_id,
                    conversation=held_conversation,
                    text=held_text,
                    metadata=reply_metadata,
                )
                await db.commit()
                return OutgoingMessage(
                    channel=message.channel,
                    channel_id=message.channel_id,
                    text=held_text,
                    instance_id=message.instance_id,
                    metadata=reply_metadata,
                )

        conversation = await _get_or_create_conversation(
            db,
            instance_id=message.instance_id,
            project_id=project_id,
            deployment_id=deployment.id if deployment else None,
            participant_id=message.sender_id,
            participant_name=message.sender_name or message.sender_id,
        )
        conversation.last_message_at = now

        metadata = dict(message.metadata or {})
        if message.attachments:
            metadata["attachments"] = message.attachments

        inbound_msg = ChannelMessage(
            id=str(uuid.uuid4()),
            channel_instance_id=message.instance_id,
            project_id=project_id,
            direction="inbound",
            sender_id=message.sender_id,
            sender_name=message.sender_name or message.sender_id,
            content=message.text,
            content_type=metadata.get("content_type", "text"),
            thread_id=conversation.id,
            external_message_id=metadata.get("external_message_id"),
            metadata_json=json.dumps(metadata),
        )
        db.add(inbound_msg)

        if instance.message_count is None:
            instance.message_count = 0
        instance.message_count += 1

        if deployment is None:
            try:
                from app.core.improvement_governance import improvement_governance

                await improvement_governance.record_feature_evidence(
                    feature="whatsapp_telegram_channel_integrations",
                    source_system=f"channel_{message.channel}",
                    source_id=inbound_msg.external_message_id or inbound_msg.id,
                    project_id=project_id,
                    agent_id="channel-router",
                    summary="Inbound channel message persisted without an active deployment.",
                    evidence={
                        "passed": True,
                        "platform": message.channel,
                        "instance_id": message.instance_id,
                        "content_type": inbound_msg.content_type,
                        "has_attachments": bool(message.attachments),
                        "deployment_routed": False,
                    },
                    metrics_after={"message_count": instance.message_count},
                    db=db,
                )
            except Exception:
                pass
            # H-8: persist and commit the inbound row BEFORE running the Pi turn.
            # A crash mid-turn must never roll the inbound record back with the
            # transaction; the outbound reply is written in a fresh session below.
            await db.commit()

            pi_response = await build_pi_channel_reply(
                message_channel=message.channel,
                channel_id=message.channel_id,
                instance_id=message.instance_id,
                project_id=project_id,
                inbound_message_id=inbound_msg.id,
                inbound_text=message.text,
                metadata=metadata,
            )
            if pi_response is not None and pi_response.text:
                # Persist the real Pi channel reply in a new session so the
                # transcript matches what the router sends back.
                async with async_session() as out_db:
                    out_db.add(
                        ChannelMessage(
                            id=str(uuid.uuid4()),
                            channel_instance_id=message.instance_id,
                            project_id=project_id,
                            direction="outbound",
                            sender_id="system",
                            sender_name="Istara",
                            content=pi_response.text,
                            content_type="text",
                            thread_id=conversation.id,
                            metadata_json=json.dumps(pi_response.metadata or {}),
                        )
                    )
                    out_instance = await out_db.get(ChannelInstance, message.instance_id)
                    if out_instance is not None:
                        out_instance.message_count = (out_instance.message_count or 0) + 1
                    await out_db.commit()
            await broadcast_channel_status(
                message.instance_id,
                "active",
                f"Recorded message from {message.sender_id}",
            )
            return pi_response

        questions = _safe_json_list(deployment.questions_json)
        conversation_meta = _conversation_metadata(conversation)
        if message.channel_id:
            # Kept so a reminder can reach the participant on the same chat later.
            conversation_meta["channel_id"] = message.channel_id
        conversation_meta.setdefault("platform", message.channel)
        update_conversation_metadata(conversation, conversation_meta)

        # Quota: once the target number of completed participants is reached, nobody new starts.
        not_started = conversation.state in {"intro", "active"} and not conversation_meta.get(
            "state"
        )
        if (
            not_started
            and (deployment.target_responses or 0) > 0
            and (deployment.current_responses or 0) >= deployment.target_responses
        ):
            conversation.state = ConversationState.CLOSED_QUOTA.value
            conversation_meta["state"] = ConversationState.CLOSED_QUOTA.value
            update_conversation_metadata(conversation, conversation_meta)
            quota_text = DEFAULT_QUOTA_FULL_MESSAGE
            reply_metadata = {"deployment_id": deployment.id, "conversation_id": conversation.id}
            _record_outbound(
                db,
                instance=instance,
                project_id=project_id,
                conversation=conversation,
                text=quota_text,
                metadata=reply_metadata,
            )
            await db.commit()
            return OutgoingMessage(
                channel=message.channel,
                channel_id=message.channel_id,
                text=quota_text,
                instance_id=message.instance_id,
                metadata=reply_metadata,
            )

        # Research Spine: a participant's answer to a question, a follow-up probe or the closing
        # question is persisted as a provisional nugget plus a raw evidence unit, attributed to the
        # exact prompt the participant was shown. Nothing else they send is research data.
        answered = _answered_prompt(conversation, conversation_meta, questions, message.text)
        if answered is not None:
            q_text = str(answered.get("text") or "Research Question")
            source_location = (
                f"channel:{message.channel}:conv:{conversation.id}:msg:{inbound_msg.id}"
            )
            source_text = f"Q: {q_text}\nA: {message.text}"
            nugget = Nugget(
                id=str(uuid.uuid4()),
                project_id=project_id,
                text=source_text,
                source=f"channel:{message.channel}:{deployment.name}",
                source_location=source_location,
                tags=json.dumps(
                    [deployment.deployment_type, f"channel:{message.channel}", "channel-research"]
                ),
                phase="discover",
            )
            db.add(nugget)
            await persist_task_nugget_evidence_units(
                db,
                project_id=project_id,
                task_id=None,
                nugget_id=nugget.id,
                source_text=source_text,
                source_location=source_location,
                method=f"deployment:{deployment.deployment_type}",
                phase="discover",
                source_type="channel_response",
                candidate_only=False,
            )
            answer_log = list(conversation_meta.get("answers") or [])
            answer_log.append(
                {
                    "kind": answered.get("kind"),
                    "question_index": answered.get("question_index"),
                    "question": q_text,
                    "message_id": inbound_msg.id,
                    "nugget_id": nugget.id,
                }
            )
            conversation_meta["answers"] = answer_log
            update_conversation_metadata(conversation, conversation_meta)

        previous_state = conversation_meta.get("state") or conversation.state
        action = await get_next_action(conversation, deployment, message.text)
        action_state = _state_value(action.get("state"), conversation.state)
        conversation.state = action_state

        if action.get("question_index") is not None:
            conversation.current_question_index = int(action["question_index"])
        if action.get("metadata"):
            update_conversation_metadata(conversation, action["metadata"])

        response_text = action.get("text") or ""
        response: OutgoingMessage | None = None
        if action.get("action") in {"send_message", "complete"} and response_text:
            response = OutgoingMessage(
                channel=message.channel,
                channel_id=message.channel_id,
                text=response_text,
                instance_id=message.instance_id,
                metadata={"deployment_id": deployment.id, "conversation_id": conversation.id},
            )
            _record_outbound(
                db,
                instance=instance,
                project_id=project_id,
                conversation=conversation,
                text=response_text,
                metadata=response.metadata,
            )

        if action_state in FINISHED_STATES and previous_state not in FINISHED_STATES:
            conversation.completed_at = now
            if action_state == ConversationState.COMPLETED.value:
                deployment.current_responses = (deployment.current_responses or 0) + 1

        try:
            from app.core.improvement_governance import improvement_governance

            await improvement_governance.record_feature_evidence(
                feature="whatsapp_telegram_channel_integrations",
                source_system=f"channel_{message.channel}",
                source_id=inbound_msg.external_message_id or inbound_msg.id,
                project_id=project_id,
                agent_id="channel-router",
                summary=(
                    "Inbound channel message was persisted and routed through deployment logic."
                ),
                evidence={
                    "passed": True,
                    "platform": message.channel,
                    "instance_id": message.instance_id,
                    "content_type": inbound_msg.content_type,
                    "has_attachments": bool(message.attachments),
                    "deployment_id": deployment.id,
                    "action": action.get("action"),
                    "state": action_state,
                },
                metrics_after={"message_count": instance.message_count},
                db=db,
            )
        except Exception:
            pass
        await db.commit()
        await broadcast_channel_status(
            message.instance_id,
            "active",
            f"Processed message from {message.sender_id}",
        )
        return response


async def process_inbound_message(
    instance_id: str,
    platform: str,
    sender_id: str,
    text: str,
    metadata: dict | None = None,
) -> OutgoingMessage | None:
    """Backward-compatible entry point for older callers."""
    return await process_inbound_channel_message(
        IncomingMessage(
            channel=platform,
            channel_id=sender_id,
            sender_id=sender_id,
            sender_name=sender_id,
            text=text,
            instance_id=instance_id,
            metadata=metadata or {},
        )
    )
