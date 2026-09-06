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
from app.services.adaptive_interview import get_next_action, update_conversation_metadata
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

        # Research Spine Compliance: persist incoming participant answer as provisional Nugget & EvidenceUnits
        if message.text and conversation.state in {"intro", "questions", "probing", "wrap_up"}:
            questions = _safe_json_list(deployment.questions_json)
            q_idx = conversation.current_question_index
            if 0 < q_idx <= len(questions):
                q_text = questions[q_idx - 1].get("text", f"Question {q_idx}")
            elif questions:
                q_text = questions[0].get("text", "Initial Question")
            else:
                q_text = "Research Question"

            source_location = f"channel:{message.channel}:conv:{conversation.id}:msg:{inbound_msg.id}"
            source_text = f"Q: {q_text}\nA: {message.text}"
            nugget = Nugget(
                id=str(uuid.uuid4()),
                project_id=project_id,
                text=source_text,
                source=f"channel:{message.channel}:{deployment.name}",
                source_location=source_location,
                tags=json.dumps([deployment.deployment_type, f"channel:{message.channel}", "channel-research"]),
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
            db.add(
                ChannelMessage(
                    id=str(uuid.uuid4()),
                    channel_instance_id=message.instance_id,
                    project_id=project_id,
                    direction="outbound",
                    sender_id="system",
                    sender_name="Istara",
                    content=response_text,
                    content_type="text",
                    thread_id=conversation.id,
                    metadata_json=json.dumps(response.metadata),
                )
            )
            instance.message_count += 1

        if action.get("action") == "complete":
            conversation.completed_at = now
            deployment.current_responses = (deployment.current_responses or 0) + 1

        try:
            from app.core.improvement_governance import improvement_governance

            await improvement_governance.record_feature_evidence(
                feature="whatsapp_telegram_channel_integrations",
                source_system=f"channel_{message.channel}",
                source_id=inbound_msg.external_message_id or inbound_msg.id,
                project_id=project_id,
                agent_id="channel-router",
                summary="Inbound channel message was persisted and routed through deployment logic.",
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
