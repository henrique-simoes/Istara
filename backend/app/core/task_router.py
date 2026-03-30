"""Task Router — intelligent skill-based + capability-based routing for multi-agent system.

Routes tasks to the best-matching agent based on:
1. Task skill_name / description keywords -> agent specialties
2. Agent capabilities and role
3. Agent availability (active, not paused/stopped)
4. Multi-specialty detection: if a task needs multiple specialties,
   identifies primary + collaborating agents for A2A coordination.

Supports user-created agents by reading their specialties from the
agent's memory JSON field (key: "specialties") or role.
"""

from __future__ import annotations

import json
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.agent import Agent, AgentRole, AgentState

logger = logging.getLogger(__name__)

# Specialty keyword mappings — which keywords suggest which specialty domains
SPECIALTY_KEYWORDS = {
    "devops": [
        "audit", "data integrity", "system health", "monitoring",
        "infrastructure", "deployment", "security", "performance",
        "logging", "metrics",
        "compute pool", "relay", "node", "docker", "container",
        "encryption", "authentication", "jwt", "backup",
    ],
    "ui": [
        "ui", "interface", "component", "design", "layout", "css",
        "styling", "responsive", "visual", "accessibility", "wcag",
        "a11y", "contrast", "typography", "heuristic",
        "aria", "touch target",
    ],
    "ux": [
        "usability", "user experience", "ux", "evaluation", "journey",
        "flow", "onboarding", "navigation", "interaction", "cognitive",
        "user testing", "prototype",
    ],
    "simulation": [
        "simulation", "simulate", "test scenario", "end-to-end", "e2e",
        "synthetic user", "load test", "stress test",
    ],
    "research": [
        "interview", "survey", "persona", "empathy", "thematic",
        "affinity", "competitive", "stakeholder", "diary", "ethnograph",
        "field study", "analytics", "jtbd", "jobs to be done",
        "synthesis", "report",
        "channel", "telegram", "slack", "whatsapp", "messaging",
        "mcp", "integration", "browser", "web fetch", "autoresearch",
        "laws of ux", "ux law", "compliance", "gestalt", "fitts", "hick",
    ],
}

# Role to specialty domain mapping
ROLE_TO_SPECIALTY = {
    AgentRole.DEVOPS_AUDIT: "devops",
    AgentRole.UI_AUDIT: "ui",
    AgentRole.UX_EVALUATION: "ux",
    AgentRole.USER_SIMULATION: "simulation",
    AgentRole.TASK_EXECUTOR: "research",  # default domain
}

# System agent IDs to specialty mapping
SYSTEM_AGENT_SPECIALTIES = {
    "istara-main": ["research"],
    "istara-devops": ["devops"],
    "istara-ui-audit": ["ui"],
    "istara-ux-eval": ["ux"],
    "istara-sim": ["simulation"],
}


async def get_agent_specialties(db: AsyncSession, agent_id: str) -> list[str]:
    """Get an agent's specialties from DB specialties column, memory, or role."""
    # Check system agent shortcuts first
    if agent_id in SYSTEM_AGENT_SPECIALTIES:
        return SYSTEM_AGENT_SPECIALTIES[agent_id]

    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        return ["research"]

    # Check specialties column first
    try:
        specs = json.loads(agent.specialties) if agent.specialties else []
        if specs:
            return specs
    except (json.JSONDecodeError, TypeError, AttributeError):
        pass

    # Check memory for user-defined specialties
    try:
        memory = json.loads(agent.memory) if agent.memory else {}
        if "specialties" in memory:
            return memory["specialties"]
    except (json.JSONDecodeError, TypeError):
        pass

    # Fall back to role mapping
    role_spec = ROLE_TO_SPECIALTY.get(agent.role, "research")
    return [role_spec]


def detect_task_specialties(
    task_title: str, task_description: str, skill_name: str | None = None
) -> list[str]:
    """Detect which specialty domains a task requires based on text analysis."""
    text = f"{task_title} {task_description or ''} {skill_name or ''}".lower()

    matched = {}
    for domain, keywords in SPECIALTY_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if kw in text:
                score += 1
        if score > 0:
            matched[domain] = score

    if not matched:
        return ["research"]  # Default: main agent handles general research

    # Sort by match strength
    sorted_domains = sorted(matched.keys(), key=lambda d: matched[d], reverse=True)
    return sorted_domains


async def get_available_agents(db: AsyncSession) -> list[Agent]:
    """Get all active, non-paused agents."""
    result = await db.execute(
        select(Agent).where(
            Agent.is_active == True,
            Agent.state.notin_([AgentState.PAUSED, AgentState.STOPPED]),
        )
    )
    return list(result.scalars().all())


async def route_task(
    db: AsyncSession,
    task_title: str,
    task_description: str,
    skill_name: str | None = None,
    explicit_agent_id: str | None = None,
) -> dict:
    """Route a task to the best agent(s).

    Returns:
        {
            "primary_agent_id": str,        # Agent that should execute the task
            "collaborators": list[str],      # Agents to consult via A2A
            "specialties_needed": list[str], # Detected specialty domains
            "routing_reason": str,           # Human-readable explanation
        }
    """
    # If explicitly assigned, respect that
    if explicit_agent_id:
        return {
            "primary_agent_id": explicit_agent_id,
            "collaborators": [],
            "specialties_needed": [],
            "routing_reason": f"Explicitly assigned to {explicit_agent_id}",
        }

    # Detect what specialties this task needs
    specialties = detect_task_specialties(task_title, task_description, skill_name)

    # Get all available agents and their specialties
    available = await get_available_agents(db)

    # Build a lookup: specialty -> [agent_ids]
    spec_to_agents: dict[str, list[str]] = {}
    for agent in available:
        agent_specs = await get_agent_specialties(db, agent.id)
        for spec in agent_specs:
            if spec not in spec_to_agents:
                spec_to_agents[spec] = []
            spec_to_agents[spec].append(agent.id)

    # Also include system agents even if not in DB (they're managed by MetaOrchestrator)
    for sys_id, sys_specs in SYSTEM_AGENT_SPECIALTIES.items():
        for spec in sys_specs:
            if spec not in spec_to_agents:
                spec_to_agents[spec] = []
            if sys_id not in spec_to_agents[spec]:
                spec_to_agents[spec].append(sys_id)

    primary_specialty = specialties[0]
    primary_candidates = spec_to_agents.get(primary_specialty, [])

    # Choose primary agent (prefer the first matching agent; istara-main as ultimate fallback)
    primary_agent = primary_candidates[0] if primary_candidates else "istara-main"

    # Determine collaborators for multi-specialty tasks
    collaborators = []
    if len(specialties) > 1:
        for spec in specialties[1:]:
            candidates = spec_to_agents.get(spec, [])
            for c in candidates:
                if c != primary_agent and c not in collaborators:
                    collaborators.append(c)
                    break  # One collaborator per specialty

    reason_parts = [f"Primary: {primary_specialty} -> {primary_agent}"]
    if collaborators:
        reason_parts.append(f"Collaborators: {', '.join(collaborators)}")

    return {
        "primary_agent_id": primary_agent,
        "collaborators": collaborators,
        "specialties_needed": specialties,
        "routing_reason": "; ".join(reason_parts),
    }
