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

logger = logging.getLogger(__name__)


class TaskCheckpoint(Base):
    """Tracks task execution progress for crash recovery."""

    __tablename__ = "task_checkpoints"

    task_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(100))
    phase: Mapped[str] = mapped_column(String(50))
    # started, skill_selected, executing, findings_stored, verified
    checkpoint_data: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


async def create_checkpoint(
    db: AsyncSession, task_id: str, agent_id: str, phase: str, data: dict | None = None
) -> None:
    """Create or update a task checkpoint."""
    existing = await db.get(TaskCheckpoint, task_id)
    if existing:
        existing.phase = phase
        existing.checkpoint_data = json.dumps(data or {})
        existing.updated_at = datetime.now(timezone.utc)
    else:
        cp = TaskCheckpoint(
            task_id=task_id,
            agent_id=agent_id,
            phase=phase,
            checkpoint_data=json.dumps(data or {}),
        )
        db.add(cp)
    await db.commit()


async def update_checkpoint(
    db: AsyncSession, task_id: str, phase: str, data: dict | None = None
) -> None:
    """Update an existing checkpoint's phase and data."""
    existing = await db.get(TaskCheckpoint, task_id)
    if existing:
        existing.phase = phase
        if data is not None:
            existing.checkpoint_data = json.dumps(data)
        existing.updated_at = datetime.now(timezone.utc)
        await db.commit()


async def complete_checkpoint(db: AsyncSession, task_id: str) -> None:
    """Remove checkpoint — task completed successfully."""
    await db.execute(
        delete(TaskCheckpoint).where(TaskCheckpoint.task_id == task_id)
    )
    await db.commit()


async def recover_incomplete(db: AsyncSession) -> list[dict]:
    """On startup, find orphaned checkpoints and return tasks to BACKLOG."""
    from app.models.task import Task, TaskStatus

    result = await db.execute(select(TaskCheckpoint))
    checkpoints = result.scalars().all()
    recovered: list[dict] = []

    for cp in checkpoints:
        # Find the task
        task = await db.get(Task, cp.task_id)
        if task:
            logger.warning(
                f"Recovering task {cp.task_id} from checkpoint phase={cp.phase}"
            )
            task.status = TaskStatus.BACKLOG
            task.agent_id = None
            recovered.append({
                "task_id": cp.task_id,
                "phase": cp.phase,
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
