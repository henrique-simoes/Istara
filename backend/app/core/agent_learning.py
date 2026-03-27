"""Agent Learning System — structured error learning and evolution.

Agents learn from:
1. Error patterns and successful resolutions
2. User feedback and corrections
3. Performance metrics over time
4. Cross-agent observations

Learnings are persisted to the agent's MEMORY.md file and also stored
in the database for structured querying.  This enables agents to improve
their behavior over time without manual prompt engineering.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy import select, String, Text, Integer, Float, DateTime, Boolean
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base, async_session
from app.core.agent_identity import append_learning

logger = logging.getLogger(__name__)


class AgentLearning(Base):
    """A structured learning record for an agent."""

    __tablename__ = "agent_learnings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    category: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # error_pattern, workflow_pattern, user_preference, performance_note
    trigger: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # What caused this learning (error message, user action, etc.)
    resolution: Mapped[str] = mapped_column(
        Text, default=""
    )  # How it was resolved (if applicable)
    learning: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # The distilled learning
    confidence: Mapped[int] = mapped_column(
        Integer, default=50
    )  # 0-100 confidence score
    times_applied: Mapped[int] = mapped_column(Integer, default=0)
    times_successful: Mapped[int] = mapped_column(Integer, default=0)
    project_id: Mapped[str] = mapped_column(
        String(36), default=""
    )  # Empty = global learning
    utility_score: Mapped[float] = mapped_column(Float, default=0.5)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class AgentLearningManager:
    """Manages agent learning lifecycle: record, retrieve, apply, evolve."""

    async def record_error_learning(
        self,
        agent_id: str,
        error_message: str,
        resolution: str,
        project_id: str = "",
    ) -> None:
        """Record a learning from an error encounter and resolution.

        Skipped during autoresearch experiments to prevent pollution.
        This is called when an agent encounters an error, tries to resolve it,
        and succeeds.  The pattern is stored for future reference.
        """
        from app.core.autoresearch_isolation import is_autoresearch_active
        if is_autoresearch_active():
            return

        learning_text = (
            f"When encountering '{error_message[:200]}', "
            f"resolve by: {resolution[:500]}"
        )

        try:
            async with async_session() as db:
                # Check if a similar learning already exists
                existing = await db.execute(
                    select(AgentLearning).where(
                        AgentLearning.agent_id == agent_id,
                        AgentLearning.category == "error_pattern",
                        AgentLearning.trigger == error_message[:500],
                    )
                )
                existing_record = existing.scalar_one_or_none()

                if existing_record:
                    # Reinforce existing learning
                    existing_record.times_applied = (
                        existing_record.times_applied or 0
                    ) + 1
                    existing_record.times_successful = (
                        existing_record.times_successful or 0
                    ) + 1
                    existing_record.confidence = min(
                        100, (existing_record.confidence or 50) + 5
                    )
                    # Update utility on successful resolution
                    existing_record.utility_score = (
                        (existing_record.utility_score or 0.5) * 0.9 + 0.1
                    )
                    existing_record.updated_at = datetime.now(timezone.utc)
                    await db.commit()
                    logger.info(
                        f"Reinforced learning for {agent_id}: {error_message[:60]}"
                    )
                else:
                    # Create new learning
                    record = AgentLearning(
                        agent_id=agent_id,
                        category="error_pattern",
                        trigger=error_message[:500],
                        resolution=resolution[:500],
                        learning=learning_text,
                        confidence=60,
                        project_id=project_id,
                    )
                    db.add(record)
                    await db.commit()
                    logger.info(
                        f"New error learning for {agent_id}: {error_message[:60]}"
                    )

                    # Also persist to MEMORY.md
                    append_learning(
                        agent_id,
                        "Error Patterns & Resolutions",
                        learning_text,
                    )
        except Exception as e:
            logger.warning(f"Failed to record error learning: {e}")

    async def record_workflow_learning(
        self,
        agent_id: str,
        pattern: str,
        project_id: str = "",
    ) -> None:
        """Record a workflow pattern observation."""
        from app.core.autoresearch_isolation import is_autoresearch_active
        if is_autoresearch_active():
            return
        try:
            async with async_session() as db:
                record = AgentLearning(
                    agent_id=agent_id,
                    category="workflow_pattern",
                    trigger="workflow_observation",
                    learning=pattern[:1000],
                    confidence=50,
                    project_id=project_id,
                )
                db.add(record)
                await db.commit()

                append_learning(agent_id, "Workflow Patterns", pattern[:500])
        except Exception as e:
            logger.warning(f"Failed to record workflow learning: {e}")

    async def record_user_feedback(
        self,
        agent_id: str,
        feedback: str,
        context: str = "",
        project_id: str = "",
    ) -> None:
        """Record a user preference or feedback learning."""
        from app.core.autoresearch_isolation import is_autoresearch_active
        if is_autoresearch_active():
            return
        try:
            async with async_session() as db:
                record = AgentLearning(
                    agent_id=agent_id,
                    category="user_preference",
                    trigger=context[:500],
                    learning=feedback[:1000],
                    confidence=70,
                    project_id=project_id,
                )
                db.add(record)
                await db.commit()

                append_learning(agent_id, "User Preferences", feedback[:500])
        except Exception as e:
            logger.warning(f"Failed to record user feedback: {e}")

    async def update_utility(
        self,
        learning_id: int,
        success: bool,
    ) -> None:
        """Update utility score for a learning based on application outcome.

        success: utility = utility * 0.9 + 0.1  (trends toward 1.0)
        failure: utility = utility * 0.9          (trends toward 0.0)
        """
        try:
            async with async_session() as db:
                result = await db.execute(
                    select(AgentLearning).where(AgentLearning.id == learning_id)
                )
                record = result.scalar_one_or_none()
                if not record:
                    return
                current = record.utility_score or 0.5
                if success:
                    record.utility_score = current * 0.9 + 0.1
                else:
                    record.utility_score = current * 0.9
                record.times_applied = (record.times_applied or 0) + 1
                if success:
                    record.times_successful = (record.times_successful or 0) + 1
                record.updated_at = datetime.now(timezone.utc)
                await db.commit()
        except Exception as e:
            logger.warning(f"Failed to update utility for learning {learning_id}: {e}")

    async def archive_low_utility(self, agent_id: str) -> int:
        """Archive learnings with low utility that have been applied enough times.

        Criteria: utility_score < 0.2 AND times_applied >= 5.
        Sets active = False (archive, don't delete).

        Returns the number of archived learnings.
        """
        archived = 0
        try:
            async with async_session() as db:
                result = await db.execute(
                    select(AgentLearning).where(
                        AgentLearning.agent_id == agent_id,
                        AgentLearning.active == True,
                        AgentLearning.utility_score < 0.2,
                        AgentLearning.times_applied >= 5,
                    )
                )
                low_utility = result.scalars().all()
                for record in low_utility:
                    record.active = False
                    record.updated_at = datetime.now(timezone.utc)
                    archived += 1
                if archived:
                    await db.commit()
                    logger.info(
                        f"Archived {archived} low-utility learnings for {agent_id}"
                    )
        except Exception as e:
            logger.warning(f"Failed to archive low-utility learnings: {e}")
        return archived

    async def get_relevant_learnings(
        self,
        agent_id: str,
        context: str = "",
        category: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """Retrieve relevant learnings for an agent, optionally filtered.

        Returns learnings ordered by confidence (descending) and recency.
        """
        try:
            async with async_session() as db:
                query = (
                    select(AgentLearning)
                    .where(
                        AgentLearning.agent_id == agent_id,
                        AgentLearning.active == True,
                    )
                    .order_by(
                        AgentLearning.confidence.desc(),
                        AgentLearning.updated_at.desc(),
                    )
                    .limit(limit)
                )

                if category:
                    query = query.where(AgentLearning.category == category)

                result = await db.execute(query)
                learnings = result.scalars().all()

                return [
                    {
                        "category": l.category,
                        "learning": l.learning,
                        "confidence": l.confidence,
                        "times_applied": l.times_applied,
                        "times_successful": l.times_successful,
                    }
                    for l in learnings
                ]
        except Exception as e:
            logger.warning(f"Failed to retrieve learnings: {e}")
            return []

    async def get_error_resolution(
        self, agent_id: str, error_message: str
    ) -> str | None:
        """Look up a known resolution for an error pattern.

        Returns the resolution string if a matching pattern is found,
        None otherwise.  Used by the error-resilient agent loop.
        """
        try:
            async with async_session() as db:
                # Search for similar error patterns
                result = await db.execute(
                    select(AgentLearning)
                    .where(
                        AgentLearning.agent_id == agent_id,
                        AgentLearning.category == "error_pattern",
                        AgentLearning.active == True,
                    )
                    .order_by(AgentLearning.confidence.desc())
                    .limit(20)
                )
                learnings = result.scalars().all()

                # Simple keyword matching for now
                error_lower = error_message.lower()
                for learning in learnings:
                    trigger_lower = (learning.trigger or "").lower()
                    # Check if the error message contains key phrases from the trigger
                    trigger_words = set(trigger_lower.split())
                    error_words = set(error_lower.split())
                    overlap = len(trigger_words & error_words)
                    if overlap >= min(3, len(trigger_words)):
                        # Update application count
                        learning.times_applied = (learning.times_applied or 0) + 1
                        await db.commit()
                        return learning.resolution
        except Exception as e:
            logger.warning(f"Failed to look up error resolution: {e}")
        return None

    async def propose_evolution(
        self, agent_id: str, proposal: str, reason: str
    ) -> None:
        """Record an evolution proposal for an agent.

        Evolution proposals suggest changes to the agent's behavior,
        skills, or protocols.  They can be auto-applied (self-evolving)
        or require user approval.
        """
        try:
            async with async_session() as db:
                record = AgentLearning(
                    agent_id=agent_id,
                    category="evolution_proposal",
                    trigger=reason[:500],
                    learning=proposal[:1000],
                    confidence=40,  # Proposals start with low confidence
                )
                db.add(record)
                await db.commit()

                append_learning(
                    agent_id,
                    "Evolution Proposals",
                    f"[PENDING] {proposal[:300]} (Reason: {reason[:200]})",
                )
                logger.info(f"Evolution proposal for {agent_id}: {proposal[:80]}")
        except Exception as e:
            logger.warning(f"Failed to record evolution proposal: {e}")


# Singleton
agent_learning = AgentLearningManager()
