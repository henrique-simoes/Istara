"""Agent loop service — manage per-agent loop configs and runtime intervals."""

from __future__ import annotations

import importlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import async_session
from app.models.agent_loop_config import AgentLoopConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Runtime singleton mapping — agent_id -> (module_path, singleton_name, interval_attr)
# ---------------------------------------------------------------------------

AGENT_INTERVAL_ATTRS: dict[str, tuple[str, str, str]] = {
    "istara-devops": ("app.agents.devops_agent", "devops_agent", "_audit_interval"),
    "istara-ui-audit": ("app.agents.ui_audit_agent", "ui_audit_agent", "_audit_interval"),
    "istara-ux-eval": ("app.agents.ux_eval_agent", "ux_eval_agent", "_audit_interval"),
    "istara-sim": ("app.agents.user_sim_agent", "user_sim_agent", "_sim_interval"),
    "istara-main": ("app.core.agent", "agent", "_loop_interval"),
}


def _get_runtime_singleton(agent_id: str) -> Any | None:
    """Import and return the runtime agent singleton, or None."""
    info = AGENT_INTERVAL_ATTRS.get(agent_id)
    if not info:
        return None
    module_path, attr_name, _ = info
    try:
        mod = importlib.import_module(module_path)
        return getattr(mod, attr_name, None)
    except Exception:
        logger.debug(f"Could not import runtime singleton for {agent_id}", exc_info=True)
        return None


def _get_interval_attr_name(agent_id: str) -> str | None:
    """Return the interval attribute name for a given agent_id."""
    info = AGENT_INTERVAL_ATTRS.get(agent_id)
    return info[2] if info else None


# ---------------------------------------------------------------------------
# Config CRUD
# ---------------------------------------------------------------------------

async def get_loop_config(db: AsyncSession, agent_id: str) -> dict:
    """Fetch the loop config for an agent, creating a default if needed."""
    result = await db.execute(
        select(AgentLoopConfig).where(AgentLoopConfig.agent_id == agent_id)
    )
    config = result.scalar_one_or_none()

    if config is None:
        # Read current runtime interval if available
        default_interval = 60
        singleton = _get_runtime_singleton(agent_id)
        if singleton:
            attr_name = _get_interval_attr_name(agent_id)
            if attr_name:
                default_interval = getattr(singleton, attr_name, 60)

        config = AgentLoopConfig(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            loop_interval_seconds=default_interval,
            paused=False,
        )
        db.add(config)
        await db.commit()

    return config.to_dict()


async def update_loop_config(db: AsyncSession, agent_id: str, data: dict) -> dict:
    """Update a loop config and apply runtime changes."""
    result = await db.execute(
        select(AgentLoopConfig).where(AgentLoopConfig.agent_id == agent_id)
    )
    config = result.scalar_one_or_none()

    if config is None:
        # Ensure a config exists first
        await get_loop_config(db, agent_id)
        result = await db.execute(
            select(AgentLoopConfig).where(AgentLoopConfig.agent_id == agent_id)
        )
        config = result.scalar_one_or_none()

    if config is None:
        raise ValueError(f"Could not create config for agent {agent_id}")

    # Apply updates
    if "loop_interval_seconds" in data:
        config.loop_interval_seconds = data["loop_interval_seconds"]
    if "paused" in data:
        config.paused = data["paused"]
    if "skills_to_run" in data:
        config.skills_to_run = json.dumps(data["skills_to_run"])
    if "project_filter" in data:
        config.project_filter = data["project_filter"]

    config.updated_at = datetime.now(timezone.utc)
    await db.commit()

    # Apply to runtime singleton if interval changed
    if "loop_interval_seconds" in data:
        _apply_runtime_interval(agent_id, data["loop_interval_seconds"])

    return config.to_dict()


def _apply_runtime_interval(agent_id: str, interval_seconds: int) -> None:
    """Set the interval on the running agent singleton."""
    singleton = _get_runtime_singleton(agent_id)
    attr_name = _get_interval_attr_name(agent_id)
    if singleton and attr_name:
        try:
            setattr(singleton, attr_name, interval_seconds)
            logger.info(f"Set {agent_id}.{attr_name} = {interval_seconds}s")
        except Exception:
            logger.debug(f"Failed to set runtime interval for {agent_id}", exc_info=True)


# ---------------------------------------------------------------------------
# List all loops
# ---------------------------------------------------------------------------

async def list_all_loops(db: AsyncSession) -> list[dict]:
    """Return all agents with their loop configs."""
    result = await db.execute(
        select(AgentLoopConfig).order_by(AgentLoopConfig.agent_id)
    )
    configs = [c.to_dict() for c in result.scalars().all()]

    # Ensure all known agents are represented
    known_ids = set(AGENT_INTERVAL_ATTRS.keys())
    existing_ids = {c["agent_id"] for c in configs}

    for agent_id in known_ids - existing_ids:
        config = await get_loop_config(db, agent_id)
        configs.append(config)

    return configs


# ---------------------------------------------------------------------------
# Pause / resume / set interval
# ---------------------------------------------------------------------------

async def pause_agent_loop(agent_id: str) -> bool:
    """Pause an agent loop via the meta orchestrator."""
    try:
        from app.agents.orchestrator import meta_orchestrator
        result = meta_orchestrator.pause_agent(agent_id)

        # Persist to DB
        async with async_session() as db:
            q = await db.execute(
                select(AgentLoopConfig).where(AgentLoopConfig.agent_id == agent_id)
            )
            config = q.scalar_one_or_none()
            if config:
                config.paused = True
                config.updated_at = datetime.now(timezone.utc)
                await db.commit()

        return result
    except Exception:
        logger.exception(f"Failed to pause agent loop {agent_id}")
        return False


async def resume_agent_loop(agent_id: str) -> bool:
    """Resume a paused agent loop via the meta orchestrator."""
    try:
        from app.agents.orchestrator import meta_orchestrator
        result = meta_orchestrator.resume_agent(agent_id)

        # Persist to DB
        async with async_session() as db:
            q = await db.execute(
                select(AgentLoopConfig).where(AgentLoopConfig.agent_id == agent_id)
            )
            config = q.scalar_one_or_none()
            if config:
                config.paused = False
                config.updated_at = datetime.now(timezone.utc)
                await db.commit()

        return result
    except Exception:
        logger.exception(f"Failed to resume agent loop {agent_id}")
        return False


async def set_agent_interval(agent_id: str, interval_seconds: int) -> bool:
    """Modify the running singleton interval and persist to DB."""
    try:
        # Apply to runtime
        _apply_runtime_interval(agent_id, interval_seconds)

        # Persist to DB
        async with async_session() as db:
            q = await db.execute(
                select(AgentLoopConfig).where(AgentLoopConfig.agent_id == agent_id)
            )
            config = q.scalar_one_or_none()
            if config:
                config.loop_interval_seconds = interval_seconds
                config.updated_at = datetime.now(timezone.utc)
                await db.commit()
            else:
                # Create config
                await get_loop_config(db, agent_id)
                q = await db.execute(
                    select(AgentLoopConfig).where(AgentLoopConfig.agent_id == agent_id)
                )
                config = q.scalar_one_or_none()
                if config:
                    config.loop_interval_seconds = interval_seconds
                    await db.commit()

        return True
    except Exception:
        logger.exception(f"Failed to set interval for {agent_id}")
        return False
