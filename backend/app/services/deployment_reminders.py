"""Reminders for research participants who went quiet part-way through a study.

The scheduler calls :func:`send_due_reminders` on every tick. A reminder goes out only when the
deployment is active, its project is not paused, the conversation is still waiting on the
participant, the configured quiet period has passed since the participant's last message (and
since the last reminder), and the per-conversation reminder budget is not spent. The reminder
repeats the prompt the participant was last shown, so their reply is still attributed to it.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.channels.base import OutgoingMessage, channel_router
from app.core.datetime_utils import ensure_utc
from app.models.channel_conversation import ChannelConversation
from app.models.channel_message import ChannelMessage
from app.models.database import async_session
from app.models.project import Project
from app.models.research_deployment import ResearchDeployment
from app.services.adaptive_interview import (
    AWAITING_REPLY_STATES,
    DEFAULT_REMINDER_MESSAGE,
    deployment_config,
)

logger = logging.getLogger(__name__)


def _metadata(conversation: ChannelConversation) -> dict:
    try:
        parsed = json.loads(conversation.metadata_json or "{}")
    except (json.JSONDecodeError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _parse_time(value: object) -> datetime | None:
    if not value:
        return None
    try:
        return ensure_utc(datetime.fromisoformat(str(value)))
    except ValueError:
        return None


async def send_due_reminders(now: datetime | None = None) -> int:
    """Send every reminder that is due and return how many were sent."""
    now = ensure_utc(now or datetime.now(UTC))
    sent = 0
    async with async_session() as db:
        deployments = (
            (
                await db.execute(
                    select(ResearchDeployment)
                    .join(Project, Project.id == ResearchDeployment.project_id)
                    .where(ResearchDeployment.state == "active", Project.is_paused.is_(False))
                )
            )
            .scalars()
            .all()
        )
        for deployment in deployments:
            config = deployment_config(deployment)
            quiet_hours = config["reminder_after_hours"]
            budget = config["max_reminders"]
            if quiet_hours <= 0 or budget <= 0:
                continue
            conversations = (
                (
                    await db.execute(
                        select(ChannelConversation).where(
                            ChannelConversation.deployment_id == deployment.id,
                            ChannelConversation.project_id == deployment.project_id,
                        )
                    )
                )
                .scalars()
                .all()
            )
            for conversation in conversations:
                meta = _metadata(conversation)
                state = meta.get("state") or conversation.state
                pending = meta.get("pending_prompt")
                if state not in AWAITING_REPLY_STATES or not isinstance(pending, dict):
                    continue
                if int(meta.get("reminders_sent", 0)) >= budget:
                    continue
                last_activity = max(
                    t
                    for t in (
                        ensure_utc(conversation.last_message_at)
                        if conversation.last_message_at
                        else None,
                        _parse_time(meta.get("last_reminder_at")),
                        ensure_utc(conversation.started_at) if conversation.started_at else None,
                    )
                    if t is not None
                )
                if now - last_activity < timedelta(hours=quiet_hours):
                    continue
                adapter = channel_router.get_by_instance_id(conversation.channel_instance_id)
                channel_id = str(meta.get("channel_id") or conversation.participant_id)
                if adapter is None:
                    logger.info(
                        "Reminder for conversation %s skipped: channel %s is not running",
                        conversation.id,
                        conversation.channel_instance_id,
                    )
                    continue
                reminder_text = str(config.get("reminder_message") or DEFAULT_REMINDER_MESSAGE)
                text = f"{reminder_text}\n\n{pending.get('text') or ''}".strip()
                message_metadata = {
                    "deployment_id": deployment.id,
                    "conversation_id": conversation.id,
                    "kind": "reminder",
                }
                try:
                    await adapter.send(
                        OutgoingMessage(
                            channel=str(meta.get("platform") or ""),
                            channel_id=channel_id,
                            text=text,
                            instance_id=conversation.channel_instance_id,
                            metadata=message_metadata,
                        )
                    )
                except Exception:
                    logger.warning(
                        "Reminder for conversation %s failed to send",
                        conversation.id,
                        exc_info=True,
                    )
                    continue
                db.add(
                    ChannelMessage(
                        id=str(uuid.uuid4()),
                        channel_instance_id=conversation.channel_instance_id,
                        project_id=deployment.project_id,
                        direction="outbound",
                        sender_id="system",
                        sender_name="Istara",
                        content=text,
                        content_type="text",
                        thread_id=conversation.id,
                        metadata_json=json.dumps(message_metadata),
                    )
                )
                meta["reminders_sent"] = int(meta.get("reminders_sent", 0)) + 1
                meta["last_reminder_at"] = now.isoformat()
                conversation.metadata_json = json.dumps(meta)
                sent += 1
        if sent:
            await db.commit()
    return sent
