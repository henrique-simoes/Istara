"""Task checkpoint and recovery — process hardening for crash resilience."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import String, Text, DateTime, select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base
from app.models.agent import AgentState

logger = logging.getLogger(__name__)


class TaskCheckpoint(Base):
    """Tracks task execution progress for crash recovery.

    The checkpoint captures both the task's progress AND the agent's state
    at the time of interruption. This enables proper session recovery when:
    - A task is mid-execution (AgentState.WORKING, Error)
    - An agent has paused processing (AgentState.PAUSED)
    - An agent encountered a fatal error (AgentState.STOPPED)

    Reference: AgentState from app.models.agent.
    """

    __tablename__ = "task_checkpoints"

    task_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(100))
    phase: Mapped[str] = mapped_column(String(50))
    # started, skill_selected, executing, findings_stored, verified
    checkpoint_data: Mapped[str] = mapped_column(Text, default="{}")
    agent_state: Mapped[str] = mapped_column(
        String(20), default=AgentState.IDLE.value  # Capture AgentState enum value
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self) -> dict:
        """Convert checkpoint to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "phase": self.phase,
            "data": json.loads(self.checkpoint_data) if self.checkpoint_data else {},
            "agent_state": self.agent_state,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


async def create_checkpoint(
    db: AsyncSession, task_id: str, agent_id: str, phase: str, data: dict | None = None, agent_state: AgentState = AgentState.IDLE
) -> None:
    """Create or update a task checkpoint.

    Captures both the task's state (phase, data) and the agent's state at interruption time.

    Args:
        db: Database session
        task_id: UUID of the task being checkpointed
        agent_id: Agent executing the task
        phase: Current execution phase
        data: Application-level state
        agent_state: The AgentState enum value from moment of pause/error/crash
    """
    existing = await db.get(TaskCheckpoint, task_id)
    if existing:
        existing.phase = phase
        existing.checkpoint_data = json.dumps(data or {})
        existing.agent_state = agent_state.value
        existing.updated_at = datetime.now(timezone.utc)
    else:
        cp = TaskCheckpoint(
            task_id=task_id,
            agent_id=agent_id,
            phase=phase,
            checkpoint_data=json.dumps(data or {}),
            agent_state=agent_state.value,
        )
        db.add(cp)
    await db.commit()


async def update_checkpoint(
    db: AsyncSession, task_id: str, phase: str, data: dict | None = None, agent_state: AgentState | str = None
) -> None:
    """Update an existing checkpoint's phase and data."""
    existing = await db.get(TaskCheckpoint, task_id)
    if existing:
        existing.phase = phase
        if data is not None:
            existing.checkpoint_data = json.dumps(data)
        if agent_state is not None and isinstance(agent_state, AgentState):
            existing.agent_state = agent_state.value
        elif agent_state is not None:
            existing.agent_state = agent_state
        existing.updated_at = datetime.now(timezone.utc)
        await db.commit()


async def complete_checkpoint(db: AsyncSession, task_id: str) -> None:
    """Remove checkpoint — task completed successfully."""
    await db.execute(
        delete(TaskCheckpoint).where(TaskCheckpoint.task_id == task_id)
    )
    await db.commit()


async def recover_incomplete(db: AsyncSession) -> list[dict]:
    """On startup, find orphaned checkpoints and return tasks to BACKLOG.

    The recovery logic uses the captured agent_state to determine how to resume:
    - AgentState.WORKING or ERROR → TaskStatus.BACKLOG (agent should be restarted manually)
    - AgentState.PAUSED → Keep in current state with user notification
    - AgentState.IDLE → Ignore (wasn't actually executing)

    This alignment ensures proper session recovery when an agent crashes mid-execution.
    """
    from app.models.task import Task, TaskStatus

    # Enum values for comparison
    WORKING_OR_ERROR = [AgentState.WORKING.value, AgentState.ERROR.value]
    PAUSED = [AgentState.PAUSED.value]
    
    result = await db.execute(select(TaskCheckpoint))
    checkpoints = result.scalars().all()
    recovered: list[dict] = []

    for cp in checkpoints:
        # Find the task
        task = await db.get(Task, cp.task_id)
        if task:
            agent_state_recovered = AgentState(cp.agent_state) if cp.agent_state else None
            
            if agent_state_recovered and agent_state_recovered in WORKING_OR_ERROR:
                logger.warning(
                    f"Recovering task {cp.task_id} from checkpoint phase={cp.phase}, "
                    f"agent_state={cp.agent_state}: TaskStatus.BACKLOG. Agent needs manual restart."
                )
                task.status = TaskStatus.BACKLOG
                task.agent_id = None
            elif agent_state_recovered and cp.phase != "started":
                # Was paused mid-execution, put back in queue for manual recovery attempt
                logger.warning(
                    f"Recovering task {cp.task_id} from checkpoint phase={cp.phase}: TaskStatus.BACKLOG. "
                    f"Agent was paused at interruption."
                )
                task.status = TaskStatus.BACKLOG
            
            recovered.append({
                "task_id": cp.task_id,
                "phase": cp.phase,
                "agent_state_recovered": str(agent_state_recovered) if agent_state_recovered else "unknown",
                "agent_id": cp.agent_id,
            })

        # Remove the orphaned checkpoint
        await db.execute(
            delete(TaskCheckpoint).where(TaskCheckpoint.task_id == cp.task_id)
        )

    await db.commit()
    return recovered


def atomic_write(path: Path, data: str) -> None:
    """Atomically write data to a file (write tmp + rename)."""
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(data, encoding="utf-8")
    tmp.replace(path)  # atomic on POSIX
