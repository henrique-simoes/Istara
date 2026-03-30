"""Service layer bridging the HTTP API to the ChannelRouter.

Handles CRUD operations for channel instances, adapter lifecycle management,
message persistence, and startup loading of active instances.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.base import ChannelAdapter, OutgoingMessage, channel_router
from app.channels.google_chat import GoogleChatAdapter
from app.channels.slack import SlackAdapter
from app.channels.telegram import TelegramAdapter
from app.channels.whatsapp import WhatsAppAdapter
from app.core.field_encryption import decrypt_field, encrypt_field
from app.models.channel_conversation import ChannelConversation
from app.models.channel_instance import ChannelInstance
from app.models.channel_message import ChannelMessage

logger = logging.getLogger(__name__)

PLATFORM_ADAPTERS: dict[str, type[ChannelAdapter]] = {
    "telegram": TelegramAdapter,
    "slack": SlackAdapter,
    "whatsapp": WhatsAppAdapter,
    "google_chat": GoogleChatAdapter,
}


# ---------------------------------------------------------------------------
# Instance CRUD
# ---------------------------------------------------------------------------

async def create_channel_instance(
    db: AsyncSession,
    platform: str,
    name: str,
    config: dict,
    project_id: str | None = None,
) -> ChannelInstance:
    """Create a new channel instance record."""
    if platform not in PLATFORM_ADAPTERS:
        raise ValueError(
            f"Unknown platform '{platform}'. Supported: {list(PLATFORM_ADAPTERS)}"
        )

    instance = ChannelInstance(
        id=str(uuid.uuid4()),
        platform=platform,
        name=name,
        config_json=encrypt_field(json.dumps(config)),
        project_id=project_id,
    )
    db.add(instance)
    await db.commit()
    await db.refresh(instance)
    logger.info("Created channel instance %s (%s/%s)", instance.id, platform, name)
    return instance


async def update_channel_instance(
    db: AsyncSession,
    instance_id: str,
    name: str | None = None,
    config: dict | None = None,
    project_id: str | None = None,
) -> ChannelInstance:
    """Update an existing channel instance."""
    result = await db.execute(
        select(ChannelInstance).where(ChannelInstance.id == instance_id)
    )
    instance = result.scalar_one_or_none()
    if instance is None:
        raise KeyError(f"Channel instance '{instance_id}' not found")

    if name is not None:
        instance.name = name
    if config is not None:
        instance.config_json = encrypt_field(json.dumps(config))
    if project_id is not None:
        instance.project_id = project_id

    await db.commit()
    await db.refresh(instance)
    return instance


async def delete_channel_instance(db: AsyncSession, instance_id: str) -> bool:
    """Stop, unregister, and delete a channel instance."""
    result = await db.execute(
        select(ChannelInstance).where(ChannelInstance.id == instance_id)
    )
    instance = result.scalar_one_or_none()
    if instance is None:
        return False

    # Stop the adapter if running
    adapter = channel_router.get(instance_id)
    if adapter is not None:
        if adapter.is_running:
            try:
                await adapter.stop()
            except Exception:
                logger.exception("Error stopping adapter %s during delete", instance_id)
        channel_router.unregister(instance_id)

    await db.delete(instance)
    await db.commit()
    logger.info("Deleted channel instance %s", instance_id)
    return True


async def get_channel_instance(db: AsyncSession, instance_id: str) -> ChannelInstance | None:
    """Get a single channel instance by ID."""
    result = await db.execute(
        select(ChannelInstance).where(ChannelInstance.id == instance_id)
    )
    return result.scalar_one_or_none()


async def list_channel_instances(
    db: AsyncSession, platform: str | None = None
) -> list[ChannelInstance]:
    """List all channel instances, optionally filtered by platform."""
    stmt = select(ChannelInstance).order_by(ChannelInstance.created_at.desc())
    if platform:
        stmt = stmt.where(ChannelInstance.platform == platform)
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Adapter lifecycle
# ---------------------------------------------------------------------------

def _instantiate_adapter(instance: ChannelInstance) -> ChannelAdapter:
    """Create an adapter instance from a ChannelInstance record."""
    adapter_cls = PLATFORM_ADAPTERS.get(instance.platform)
    if adapter_cls is None:
        raise ValueError(f"No adapter class for platform '{instance.platform}'")
    raw = decrypt_field(instance.config_json) if instance.config_json else "{}"
    config = json.loads(raw)
    return adapter_cls(instance_id=instance.id, config=config)


async def start_channel_instance(db: AsyncSession, instance_id: str) -> dict:
    """Instantiate adapter, register with router, and start polling/listening."""
    result = await db.execute(
        select(ChannelInstance).where(ChannelInstance.id == instance_id)
    )
    instance = result.scalar_one_or_none()
    if instance is None:
        raise KeyError(f"Channel instance '{instance_id}' not found")

    # Check if already registered and running
    existing = channel_router.get(instance_id)
    if existing is not None and existing.is_running:
        return {"status": "already_running", "instance_id": instance_id}

    # Create and register adapter
    adapter = _instantiate_adapter(instance)
    channel_router.register(adapter)

    if not adapter.enabled:
        return {
            "status": "not_enabled",
            "instance_id": instance_id,
            "detail": "Adapter is missing required configuration.",
        }

    await channel_router.start_adapter(instance_id)

    # Update DB status
    instance.is_active = True
    instance.health_status = "healthy"
    instance.last_health_at = datetime.now(timezone.utc)
    await db.commit()

    logger.info("Started channel instance %s (%s)", instance_id, instance.platform)
    return {"status": "started", "instance_id": instance_id}


async def stop_channel_instance(db: AsyncSession, instance_id: str) -> dict:
    """Stop a running channel adapter."""
    result = await db.execute(
        select(ChannelInstance).where(ChannelInstance.id == instance_id)
    )
    instance = result.scalar_one_or_none()
    if instance is None:
        raise KeyError(f"Channel instance '{instance_id}' not found")

    adapter = channel_router.get(instance_id)
    if adapter is None or not adapter.is_running:
        instance.is_active = False
        await db.commit()
        return {"status": "already_stopped", "instance_id": instance_id}

    await channel_router.stop_adapter(instance_id)

    instance.is_active = False
    instance.health_status = "stopped"
    await db.commit()

    logger.info("Stopped channel instance %s (%s)", instance_id, instance.platform)
    return {"status": "stopped", "instance_id": instance_id}


async def health_check_instance(db: AsyncSession, instance_id: str) -> dict:
    """Run a health check on a channel adapter and persist the result."""
    result = await db.execute(
        select(ChannelInstance).where(ChannelInstance.id == instance_id)
    )
    instance = result.scalar_one_or_none()
    if instance is None:
        raise KeyError(f"Channel instance '{instance_id}' not found")

    adapter = channel_router.get(instance_id)
    if adapter is None:
        health = {"status": "not_registered", "platform": instance.platform}
    else:
        health = await adapter.health_check()

    # Persist health status
    instance.health_status = health.get("status", "unknown")
    instance.last_health_at = datetime.now(timezone.utc)
    await db.commit()

    return health


# ---------------------------------------------------------------------------
# Message operations
# ---------------------------------------------------------------------------

async def get_message_history(
    db: AsyncSession,
    instance_id: str,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Retrieve message history for a channel instance."""
    stmt = (
        select(ChannelMessage)
        .where(ChannelMessage.channel_instance_id == instance_id)
        .order_by(ChannelMessage.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    messages = result.scalars().all()
    return [m.to_dict() for m in messages]


async def get_conversations(db: AsyncSession, instance_id: str) -> list[dict]:
    """Retrieve all conversations for a channel instance."""
    stmt = (
        select(ChannelConversation)
        .where(ChannelConversation.channel_instance_id == instance_id)
        .order_by(ChannelConversation.last_message_at.desc().nullslast())
    )
    result = await db.execute(stmt)
    conversations = result.scalars().all()
    return [c.to_dict() for c in conversations]


async def send_message(
    db: AsyncSession,
    instance_id: str,
    channel_id: str,
    text: str,
    metadata: dict | None = None,
) -> dict:
    """Send a message via the channel adapter and persist it."""
    adapter = channel_router.get(instance_id)
    if adapter is None:
        raise KeyError(f"No adapter registered for instance '{instance_id}'")
    if not adapter.is_running:
        raise RuntimeError(f"Adapter for instance '{instance_id}' is not running")

    out = OutgoingMessage(
        channel=adapter.platform,
        channel_id=channel_id,
        text=text,
        instance_id=instance_id,
        metadata=metadata or {},
    )
    await adapter.send(out)

    # Persist outbound message
    record = await record_message(
        db,
        instance_id=instance_id,
        direction="outbound",
        sender_id="system",
        sender_name="Istara",
        content=text,
        channel_id=channel_id,
    )
    return record.to_dict()


async def record_message(
    db: AsyncSession,
    instance_id: str,
    direction: str,
    sender_id: str,
    sender_name: str,
    content: str,
    content_type: str = "text",
    channel_id: str = "",
    thread_id: str | None = None,
    external_id: str | None = None,
    project_id: str | None = None,
) -> ChannelMessage:
    """Persist a message to the database and increment instance message_count."""
    msg = ChannelMessage(
        id=str(uuid.uuid4()),
        channel_instance_id=instance_id,
        project_id=project_id,
        direction=direction,
        sender_id=sender_id,
        sender_name=sender_name,
        content=content,
        content_type=content_type,
        thread_id=thread_id,
        external_message_id=external_id,
    )
    db.add(msg)

    # Increment message count on the instance
    result = await db.execute(
        select(ChannelInstance).where(ChannelInstance.id == instance_id)
    )
    instance = result.scalar_one_or_none()
    if instance is not None:
        instance.message_count = (instance.message_count or 0) + 1

    await db.commit()
    await db.refresh(msg)
    return msg


# ---------------------------------------------------------------------------
# Startup loader
# ---------------------------------------------------------------------------

async def load_active_instances(db: AsyncSession) -> int:
    """Load all active channel instances from DB, instantiate adapters, and start them.

    Called once during application startup.
    """
    stmt = select(ChannelInstance).where(ChannelInstance.is_active == True)  # noqa: E712
    result = await db.execute(stmt)
    instances = result.scalars().all()

    loaded = 0
    for instance in instances:
        try:
            adapter = _instantiate_adapter(instance)
            channel_router.register(adapter)
            if adapter.enabled:
                await channel_router.start_adapter(instance.id)
                loaded += 1
                logger.info(
                    "Auto-started channel instance %s (%s/%s)",
                    instance.id,
                    instance.platform,
                    instance.name,
                )
            else:
                logger.warning(
                    "Channel instance %s (%s) registered but not enabled (missing config).",
                    instance.id,
                    instance.platform,
                )
        except Exception:
            logger.exception(
                "Failed to load channel instance %s (%s)", instance.id, instance.platform
            )
            # Mark as unhealthy in DB
            instance.health_status = "unhealthy"
            await db.commit()

    return loaded
