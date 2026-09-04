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
from app.channels.pi_local import PiLocalAdapter
from app.channels.slack import SlackAdapter
from app.channels.telegram import TelegramAdapter
from app.channels.whatsapp import WhatsAppAdapter
from app.core.field_encryption import decrypt_field, encrypt_field
from app.models.channel_conversation import ChannelConversation
from app.models.channel_instance import ChannelInstance
from app.models.channel_message import ChannelMessage
from app.models.project import Project

logger = logging.getLogger(__name__)

# Health checks may receive provider/network exception text that includes
# private URLs, tokens, or implementation details. Keep that detail in local
# logs only and expose a stable, actionable message to API consumers.
PUBLIC_HEALTH_ERROR = (
    "Connection check failed. Verify the credentials and network access, then retry."
)

PLATFORM_ADAPTERS: dict[str, type[ChannelAdapter]] = {
    "telegram": TelegramAdapter,
    "slack": SlackAdapter,
    "whatsapp": WhatsAppAdapter,
    "google_chat": GoogleChatAdapter,
    "pi_local": PiLocalAdapter,
}

CONFIG_ALIASES: dict[str, dict[str, str]] = {
    "telegram": {
        "Bot Token": "bot_token",
        "bot token": "bot_token",
        "token": "bot_token",
    },
    "slack": {
        "Bot Token": "bot_token",
        "Signing Secret": "signing_secret",
        "App Token": "app_token",
        "bot token": "bot_token",
        "signing secret": "signing_secret",
        "app token": "app_token",
    },
    "whatsapp": {
        "Phone Number ID": "phone_number_id",
        "Access Token": "access_token",
        "Verify Token": "verify_token",
        "App Secret": "app_secret",
        "phone number id": "phone_number_id",
        "access token": "access_token",
        "verify token": "verify_token",
        "app secret": "app_secret",
    },
    "google_chat": {
        "Webhook URL": "webhook_url",
        "Webhook Token": "webhook_token",
        "Service Account JSON": "service_account_json",
        "webhook url": "webhook_url",
        "webhook token": "webhook_token",
        "service account json": "service_account_json",
    },
}


def _require_project_scope(project_id: str | None) -> str:
    scoped_project_id = (project_id or "").strip()
    if not scoped_project_id:
        raise ValueError("project_id is required")
    return scoped_project_id


def normalize_channel_config(platform: str, config: dict | None) -> dict:
    """Normalize UI credential labels into adapter config keys."""
    aliases = CONFIG_ALIASES.get(platform, {})
    normalized: dict = {}
    for raw_key, raw_value in (config or {}).items():
        if raw_value is None:
            continue
        key = aliases.get(str(raw_key), str(raw_key).strip())
        if not key:
            continue
        if isinstance(raw_value, str):
            value = raw_value.strip()
            if not value:
                continue
        else:
            value = raw_value
        normalized[key] = value
    return normalized


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
        raise ValueError(f"Unknown platform '{platform}'. Supported: {list(PLATFORM_ADAPTERS)}")
    normalized_config = normalize_channel_config(platform, config)

    instance = ChannelInstance(
        id=str(uuid.uuid4()),
        platform=platform,
        name=name,
        config_json=encrypt_field(json.dumps(normalized_config)),
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
    *,
    scope_project_id: str,
) -> ChannelInstance:
    """Update an existing channel instance."""
    scoped_project_id = _require_project_scope(scope_project_id)
    result = await db.execute(
        select(ChannelInstance).where(
            ChannelInstance.id == instance_id,
            ChannelInstance.project_id == scoped_project_id,
        )
    )
    instance = result.scalar_one_or_none()
    if instance is None:
        raise KeyError(f"Channel instance '{instance_id}' not found")

    if name is not None:
        instance.name = name
    if config is not None:
        instance.config_json = encrypt_field(
            json.dumps(normalize_channel_config(instance.platform, config))
        )
    if project_id is not None:
        instance.project_id = project_id

    await db.commit()
    await db.refresh(instance)
    return instance


async def delete_channel_instance(
    db: AsyncSession,
    instance_id: str,
    *,
    project_id: str,
) -> bool:
    """Stop, unregister, and delete a channel instance inside one project scope."""
    scoped_project_id = _require_project_scope(project_id)
    result = await db.execute(
        select(ChannelInstance).where(
            ChannelInstance.id == instance_id,
            ChannelInstance.project_id == scoped_project_id,
        )
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
    result = await db.execute(select(ChannelInstance).where(ChannelInstance.id == instance_id))
    return result.scalar_one_or_none()


async def list_channel_instances(
    db: AsyncSession,
    platform: str | None = None,
    *,
    project_id: str,
) -> list[ChannelInstance]:
    """List channel instances for exactly one active project."""
    scoped_project_id = _require_project_scope(project_id)
    stmt = (
        select(ChannelInstance)
        .where(ChannelInstance.project_id == scoped_project_id)
        .order_by(ChannelInstance.created_at.desc())
    )
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


async def start_channel_instance(
    db: AsyncSession,
    instance_id: str,
    *,
    project_id: str,
) -> dict:
    """Start a channel instance only inside one project scope."""
    scoped_project_id = _require_project_scope(project_id)
    result = await db.execute(
        select(ChannelInstance).where(
            ChannelInstance.id == instance_id,
            ChannelInstance.project_id == scoped_project_id,
        )
    )
    instance = result.scalar_one_or_none()
    if instance is None:
        raise KeyError(f"Channel instance '{instance_id}' not found")
    project = await db.get(Project, scoped_project_id)
    if project is None or project.is_paused:
        raise RuntimeError("Project is paused or not found")

    # Check if already registered and running
    existing = channel_router.get(instance_id)
    if existing is not None and existing.is_running:
        return {"status": "already_running", "instance_id": instance_id}

    # Create and register adapter only when it has enough runtime support to run.
    adapter = _instantiate_adapter(instance)

    if not adapter.enabled:
        instance.is_active = False
        instance.health_status = "not_enabled"
        instance.last_health_at = datetime.now(timezone.utc)
        await db.commit()
        return {
            "status": "not_enabled",
            "instance_id": instance_id,
            "detail": "Adapter is missing required configuration.",
        }

    channel_router.register(adapter)

    try:
        await channel_router.start_adapter(instance_id)
    except Exception:
        # Adapter startup may surface provider/network details (including
        # private URLs or credentials). Keep those details in server logs and
        # expose the same stable actionable message used by health checks.
        logger.exception(
            "Channel adapter start raised for instance %s (%s)",
            instance_id,
            instance.platform,
        )
        channel_router.unregister(instance_id)
        instance.is_active = False
        instance.health_status = "unhealthy"
        instance.last_health_at = datetime.now(timezone.utc)
        await db.commit()
        raise RuntimeError(PUBLIC_HEALTH_ERROR)

    # Update DB status
    instance.is_active = True
    instance.health_status = "healthy"
    instance.last_health_at = datetime.now(timezone.utc)
    await db.commit()

    logger.info("Started channel instance %s (%s)", instance_id, instance.platform)
    return {"status": "started", "instance_id": instance_id}


async def stop_channel_instance(
    db: AsyncSession,
    instance_id: str,
    *,
    project_id: str,
) -> dict:
    """Stop a running channel adapter only inside one project scope."""
    scoped_project_id = _require_project_scope(project_id)
    result = await db.execute(
        select(ChannelInstance).where(
            ChannelInstance.id == instance_id,
            ChannelInstance.project_id == scoped_project_id,
        )
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


async def stop_project_channel_instances(db: AsyncSession, project_id: str) -> int:
    """Stop all active channel adapters owned by one project."""
    scoped_project_id = _require_project_scope(project_id)
    result = await db.execute(
        select(ChannelInstance).where(
            ChannelInstance.project_id == scoped_project_id,
        )
    )
    instances = list(result.scalars().all())
    stopped = 0
    now = datetime.now(timezone.utc)

    for instance in instances:
        adapter = channel_router.get(instance.id)
        if adapter is None and not instance.is_active:
            continue
        if adapter is not None:
            if adapter.is_running:
                await channel_router.stop_adapter(instance.id)
            channel_router.unregister(instance.id)
        instance.is_active = False
        instance.health_status = "stopped"
        instance.last_health_at = now
        stopped += 1

    if stopped:
        await db.commit()
    return stopped


async def health_check_instance(
    db: AsyncSession,
    instance_id: str,
    *,
    project_id: str,
) -> dict:
    """Run a health check on a channel adapter inside one project scope."""
    scoped_project_id = _require_project_scope(project_id)
    result = await db.execute(
        select(ChannelInstance).where(
            ChannelInstance.id == instance_id,
            ChannelInstance.project_id == scoped_project_id,
        )
    )
    instance = result.scalar_one_or_none()
    if instance is None:
        raise KeyError(f"Channel instance '{instance_id}' not found")

    adapter = channel_router.get(instance_id)
    if adapter is None:
        adapter = _instantiate_adapter(instance)
        if not adapter.enabled:
            health = {
                "status": "not_enabled",
                "platform": instance.platform,
                "detail": "Adapter is missing required configuration.",
            }
        else:
            health = {"status": "stopped", "platform": instance.platform}
    else:
        try:
            health = await adapter.health_check()
        except Exception:
            # Adapters should normally return a structured unhealthy result,
            # but a defensive boundary here prevents a provider exception from
            # becoming a 500/raw traceback in the integration wizard.
            logger.exception(
                "Channel health check raised for instance %s (%s)",
                instance_id,
                instance.platform,
            )
            health = {
                "status": "unhealthy",
                "platform": instance.platform,
                "error": PUBLIC_HEALTH_ERROR,
            }

    if health.get("status") == "unhealthy":
        # Adapter error strings are intentionally not API-facing: HTTP/client
        # details can contain credentials or internal topology.
        health = {**health, "error": PUBLIC_HEALTH_ERROR}

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
    *,
    project_id: str,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Retrieve message history for a channel instance."""
    scoped_project_id = _require_project_scope(project_id)
    stmt = (
        select(ChannelMessage)
        .where(
            ChannelMessage.channel_instance_id == instance_id,
            ChannelMessage.project_id == scoped_project_id,
        )
        .order_by(ChannelMessage.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    messages = result.scalars().all()
    return [m.to_dict() for m in messages]


async def get_conversations(
    db: AsyncSession,
    instance_id: str,
    *,
    project_id: str,
) -> list[dict]:
    """Retrieve all conversations for a channel instance."""
    scoped_project_id = _require_project_scope(project_id)
    stmt = (
        select(ChannelConversation)
        .where(
            ChannelConversation.channel_instance_id == instance_id,
            ChannelConversation.project_id == scoped_project_id,
        )
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
    *,
    project_id: str,
    metadata: dict | None = None,
) -> dict:
    """Send a message via the channel adapter and persist it."""
    scoped_project_id = _require_project_scope(project_id)
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
        project_id=scoped_project_id,
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
    result = await db.execute(select(ChannelInstance).where(ChannelInstance.id == instance_id))
    instance = result.scalar_one_or_none()
    if instance is None:
        raise KeyError(f"Channel instance '{instance_id}' not found")

    resolved_project_id = (project_id or instance.project_id or "").strip()
    if not resolved_project_id:
        raise ValueError("project_id is required")
    if instance.project_id != resolved_project_id:
        raise ValueError("project_id does not match channel instance")

    msg = ChannelMessage(
        id=str(uuid.uuid4()),
        channel_instance_id=instance_id,
        project_id=resolved_project_id,
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
    stmt = (
        select(ChannelInstance)
        .join(Project, ChannelInstance.project_id == Project.id)
        .where(
            ChannelInstance.is_active.is_(True),
            Project.is_paused.is_(False),
        )
    )
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
