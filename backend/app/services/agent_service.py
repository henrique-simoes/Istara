"""Agent service — CRUD, lifecycle, and hardware-aware management."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import (
    Agent, AgentRole, AgentState, HeartbeatStatus,
    ALL_CAPABILITIES, DEFAULT_CAPABILITIES,
)
from app.core.resource_governor import governor
from app.core.hardware import detect_hardware

logger = logging.getLogger(__name__)

# Default system agents that get seeded on first run.
# Each agent has a persona directory at agents/personas/{agent_id}/ with
# CORE.md, SKILLS.md, PROTOCOLS.md, MEMORY.md files that define its full
# identity.  The system_prompt below is a short fallback summary used only
# if persona files are missing.
SYSTEM_AGENTS = [
    {
        "id": "reclaw-main",
        "name": "ReClaw",
        "role": AgentRole.TASK_EXECUTOR,
        "system_prompt": (
            "You are ReClaw, the primary Research Coordinator. You orchestrate "
            "research workflows, execute analytical skills, synthesize findings, "
            "and provide expert UX research guidance at every stage of the Double "
            "Diamond. You are evidence-driven, structured, proactive, and honest "
            "about limitations. Cite sources explicitly and flag uncertainty clearly."
        ),
        "capabilities": ALL_CAPABILITIES,
        "is_system": True,
    },
    {
        "id": "reclaw-devops",
        "name": "Sentinel",
        "role": AgentRole.DEVOPS_AUDIT,
        "system_prompt": (
            "You are Sentinel, the DevOps Audit Agent. You continuously monitor "
            "data integrity, system health, and operational reliability. You are "
            "precise, alert but not alarmist, and proactive about detecting drift. "
            "You report issues with severity levels and actionable recommendations."
        ),
        "capabilities": ["skill_execution", "findings_write", "a2a_messaging"],
        "is_system": True,
    },
    {
        "id": "reclaw-ui-audit",
        "name": "Pixel",
        "role": AgentRole.UI_AUDIT,
        "system_prompt": (
            "You are Pixel, the UI Audit Agent. You evaluate interfaces against "
            "Nielsen's 10 Heuristics and WCAG 2.2 AA. You are detail-oriented, "
            "standards-referenced, and constructive — every issue comes with a "
            "specific, actionable fix. You think in visual hierarchy, accessibility, "
            "and design system consistency."
        ),
        "capabilities": ["skill_execution", "findings_write", "a2a_messaging"],
        "is_system": True,
    },
    {
        "id": "reclaw-ux-eval",
        "name": "Sage",
        "role": AgentRole.UX_EVALUATION,
        "system_prompt": (
            "You are Sage, the UX Evaluation Agent. You evaluate the end-to-end "
            "experience from a human-centered design perspective: information "
            "architecture, user journeys, cognitive load, and learnability. You "
            "think from the user's perspective and present findings as scenarios."
        ),
        "capabilities": ["skill_execution", "findings_write", "a2a_messaging"],
        "is_system": True,
    },
    {
        "id": "reclaw-sim",
        "name": "Echo",
        "role": AgentRole.USER_SIMULATION,
        "system_prompt": (
            "You are Echo, the User Simulation Agent. You rigorously test the "
            "platform by simulating realistic research workflows end-to-end. You "
            "approach testing with QA rigor, explore edge cases, document findings "
            "thoroughly, and simulate different user skill levels."
        ),
        "capabilities": ["skill_execution", "findings_write", "a2a_messaging"],
        "is_system": True,
    },
]


async def seed_system_agents(db: AsyncSession) -> None:
    """Create or update default system agents.

    On first run, creates all system agents.  On subsequent runs,
    updates the name and system_prompt of existing system agents
    to reflect any persona changes (e.g., new names like Sentinel,
    Pixel, Sage, Echo).
    """
    for agent_def in SYSTEM_AGENTS:
        result = await db.execute(
            select(Agent).where(Agent.id == agent_def["id"])
        )
        existing = result.scalar_one_or_none()

        if existing is None:
            new_agent = Agent(
                id=agent_def["id"],
                name=agent_def["name"],
                role=agent_def["role"],
                system_prompt=agent_def["system_prompt"],
                capabilities=json.dumps(agent_def["capabilities"]),
                is_system=agent_def["is_system"],
                state=AgentState.IDLE,
                heartbeat_status=HeartbeatStatus.STOPPED,
            )
            db.add(new_agent)
            logger.info(f"Seeded system agent: {agent_def['name']}")
        else:
            # Update existing system agent's name and prompt if changed
            updated = False
            if existing.name != agent_def["name"]:
                existing.name = agent_def["name"]
                updated = True
            if existing.system_prompt != agent_def["system_prompt"]:
                existing.system_prompt = agent_def["system_prompt"]
                updated = True
            if updated:
                logger.info(
                    f"Updated system agent: {agent_def['name']} ({agent_def['id']})"
                )
    await db.commit()


async def list_agents(db: AsyncSession, include_system: bool = True) -> list[dict]:
    """List all active agents."""
    query = select(Agent).where(Agent.is_active == True)
    if not include_system:
        query = query.where(Agent.is_system == False)
    result = await db.execute(query.order_by(Agent.created_at))
    return [a.to_dict() for a in result.scalars().all()]


async def get_agent(db: AsyncSession, agent_id: str) -> dict | None:
    """Get a single agent by ID."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    return agent.to_dict() if agent else None


async def create_agent(
    db: AsyncSession,
    name: str,
    role: str = "custom",
    system_prompt: str = "",
    capabilities: list[str] | None = None,
    heartbeat_interval: int = 60,
    avatar_path: str | None = None,
) -> dict:
    """Create a new user agent."""
    if capabilities is None:
        capabilities = list(DEFAULT_CAPABILITIES)

    agent = Agent(
        id=str(uuid.uuid4()),
        name=name,
        role=AgentRole(role),
        system_prompt=system_prompt,
        capabilities=json.dumps(capabilities),
        heartbeat_interval_seconds=heartbeat_interval,
        avatar_path=avatar_path,
        state=AgentState.IDLE,
        heartbeat_status=HeartbeatStatus.STOPPED,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    logger.info(f"Created agent: {name} ({agent.id})")
    return agent.to_dict()


async def update_agent(db: AsyncSession, agent_id: str, updates: dict) -> dict | None:
    """Update an agent's fields."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        return None

    for key, value in updates.items():
        if key == "capabilities" and isinstance(value, list):
            setattr(agent, key, json.dumps(value))
        elif key == "memory" and isinstance(value, dict):
            existing = json.loads(agent.memory or "{}")
            existing.update(value)
            agent.memory = json.dumps(existing)
        elif hasattr(agent, key):
            setattr(agent, key, value)

    agent.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(agent)
    return agent.to_dict()


async def delete_agent(db: AsyncSession, agent_id: str) -> bool:
    """Soft-delete an agent (set is_active=False)."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent or agent.is_system:
        return False
    agent.is_active = False
    agent.state = AgentState.STOPPED
    agent.heartbeat_status = HeartbeatStatus.STOPPED
    await db.commit()
    return True


async def set_agent_state(db: AsyncSession, agent_id: str, state: AgentState) -> bool:
    """Update an agent's state."""
    result = await db.execute(
        update(Agent).where(Agent.id == agent_id).values(
            state=state, updated_at=datetime.now(timezone.utc)
        )
    )
    await db.commit()
    return result.rowcount > 0


async def get_agent_memory(db: AsyncSession, agent_id: str) -> dict:
    """Get an agent's memory."""
    result = await db.execute(select(Agent.memory).where(Agent.id == agent_id))
    row = result.scalar_one_or_none()
    return json.loads(row) if row else {}


async def update_agent_memory(db: AsyncSession, agent_id: str, updates: dict) -> dict:
    """Merge updates into an agent's memory."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        return {}
    existing = json.loads(agent.memory or "{}")
    existing.update(updates)
    agent.memory = json.dumps(existing)
    agent.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return existing


async def check_capacity() -> dict:
    """Check if hardware can support another agent."""
    status = governor.get_status()
    hw = detect_hardware()

    active_count = status.get("active_agents", 0)
    max_agents = status.get("budget", {}).get("max_concurrent_agents", 2)

    can_create = active_count < max_agents
    if status.get("pressure", "") == "critical":
        can_create = False
        reason = "System resources critical — RAM or disk usage too high"
    elif active_count >= max_agents:
        reason = f"Maximum concurrent agents reached ({max_agents}). Pause or stop an agent first."
    else:
        reason = "System has capacity for another agent"

    return {
        "can_create": can_create,
        "reason": reason,
        "current_agents": active_count,
        "max_agents": max_agents,
        "ram_available_gb": round(hw.available_ram_gb, 1),
        "ram_total_gb": round(hw.total_ram_gb, 1),
        "cpu_cores": hw.cpu_cores,
        "pressure": status.get("pressure", "unknown"),
    }
