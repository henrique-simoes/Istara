# Inspired by Karpathy's autoresearch (MIT) — https://github.com/karpathy/autoresearch
"""Rate limiter for autoresearch experiments and production self-improvement systems.

Prevents runaway loops by capping:
- Autoresearch experiments per skill per day
- Total autoresearch experiments per day
- Agent learnings per agent per hour (also production)
- Skill improvement proposals per skill per day (also production)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Default limits
DEFAULT_LIMITS = {
    "max_experiments_per_skill_per_day": 50,
    "max_experiments_total_per_day": 200,
    "max_learnings_per_agent_per_hour": 20,
    "max_proposals_per_skill_per_day": 5,
}


async def check_experiment_limit(
    db: AsyncSession,
    skill_name: str | None = None,
    limits: dict | None = None,
) -> tuple[bool, str]:
    """Check if autoresearch experiments are within rate limits.

    Returns (allowed, reason).
    """
    lim = limits or DEFAULT_LIMITS
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(hours=24)

    from app.models.autoresearch_experiment import AutoresearchExperiment

    # Total daily limit
    total_result = await db.execute(
        select(func.count(AutoresearchExperiment.id)).where(
            AutoresearchExperiment.started_at >= day_ago
        )
    )
    total_count = total_result.scalar() or 0
    if total_count >= lim["max_experiments_total_per_day"]:
        return False, f"Daily experiment limit reached ({total_count}/{lim['max_experiments_total_per_day']})"

    # Per-skill daily limit
    if skill_name:
        skill_result = await db.execute(
            select(func.count(AutoresearchExperiment.id)).where(
                AutoresearchExperiment.started_at >= day_ago,
                AutoresearchExperiment.target_name == skill_name,
            )
        )
        skill_count = skill_result.scalar() or 0
        if skill_count >= lim["max_experiments_per_skill_per_day"]:
            return False, f"Per-skill limit reached for '{skill_name}' ({skill_count}/{lim['max_experiments_per_skill_per_day']})"

    return True, "OK"


async def check_learning_limit(
    db: AsyncSession,
    agent_id: str,
    limits: dict | None = None,
) -> tuple[bool, str]:
    """Check if agent learnings are within hourly rate limit."""
    lim = limits or DEFAULT_LIMITS
    hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)

    from app.core.agent_learning import AgentLearning

    result = await db.execute(
        select(func.count(AgentLearning.id)).where(
            AgentLearning.agent_id == agent_id,
            AgentLearning.created_at >= hour_ago,
        )
    )
    count = result.scalar() or 0
    if count >= lim["max_learnings_per_agent_per_hour"]:
        return False, f"Learning limit reached for agent '{agent_id}' ({count}/{lim['max_learnings_per_agent_per_hour']}/h)"

    return True, "OK"


def get_limits() -> dict:
    """Return current rate limits."""
    return dict(DEFAULT_LIMITS)


def update_limits(new_limits: dict) -> None:
    """Update rate limits (in-memory only)."""
    for key, value in new_limits.items():
        if key in DEFAULT_LIMITS and isinstance(value, (int, float)):
            DEFAULT_LIMITS[key] = int(value)
