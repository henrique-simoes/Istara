"""Lightweight async cron scheduler — no external dependencies.

Fills audit gap #5: user-configurable cron scheduling for agents and skills.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import Boolean, DateTime, String, Text, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.datetime_utils import ensure_utc
from app.models.database import Base, async_session

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SQLAlchemy model
# ---------------------------------------------------------------------------

class ScheduledTask(Base):
    """A user-configurable scheduled task."""

    __tablename__ = "scheduled_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    cron_expression: Mapped[str] = mapped_column(String(100), nullable=False)
    skill_name: Mapped[str] = mapped_column(String(100), default="")
    project_id: Mapped[str] = mapped_column(String(36), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


# ---------------------------------------------------------------------------
# Cron parser
# ---------------------------------------------------------------------------

class CronParser:
    """Parse basic cron expressions and compute the next run time.

    Supported format: ``minute hour day-of-month month day-of-week``
    Field values: number, ``*``, ``*/N`` (step).
    """

    FIELD_RANGES = [
        (0, 59),   # minute
        (0, 23),   # hour
        (1, 31),   # day of month
        (1, 12),   # month
        (0, 6),    # day of week (0=Sun, 1=Mon … 6=Sat — standard cron)
    ]

    @classmethod
    def _expand_field(cls, token: str, lo: int, hi: int) -> set[int]:
        """Expand a single cron field token into a set of valid integers."""
        if token == "*":
            return set(range(lo, hi + 1))
        if token.startswith("*/"):
            step = int(token[2:])
            return set(range(lo, hi + 1, step))
        # Comma-separated values
        values: set[int] = set()
        for part in token.split(","):
            if "-" in part:
                a, b = part.split("-", 1)
                values.update(range(int(a), int(b) + 1))
            else:
                values.add(int(part))
        return values

    @classmethod
    def parse(cls, expression: str) -> list[set[int]]:
        """Return list of expanded sets for [minute, hour, dom, month, dow]."""
        tokens = expression.strip().split()
        if len(tokens) != 5:
            raise ValueError(f"Cron expression must have 5 fields, got {len(tokens)}: {expression!r}")
        return [
            cls._expand_field(tok, lo, hi)
            for tok, (lo, hi) in zip(tokens, cls.FIELD_RANGES)
        ]

    @classmethod
    def next_run_after(cls, expression: str, after: datetime) -> datetime:
        """Compute the next datetime matching *expression* strictly after *after*.

        Uses brute-force minute-stepping (max ~525 960 iterations for a year)
        which is simple and correct for the 5-field cron subset we support.
        """
        fields = cls.parse(expression)
        minutes, hours, doms, months, dows = fields

        # Start from the next whole minute
        candidate = after.replace(second=0, microsecond=0) + timedelta(minutes=1)

        # Cap the search at ~2 years to avoid infinite loops on impossible expressions
        max_iterations = 60 * 24 * 366 * 2
        td_minute = timedelta(minutes=1)

        for _ in range(max_iterations):
            if (
                candidate.minute in minutes
                and candidate.hour in hours
                and candidate.day in doms
                and candidate.month in months
                and ((candidate.isoweekday() % 7) in dows)  # isoweekday: Mon=1..Sun=7 → %7 → Sun=0,Mon=1..Sat=6
            ):
                return candidate
            candidate += td_minute

        raise ValueError(f"No matching time found within 2 years for: {expression!r}")


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class Scheduler:
    """Async scheduler that checks the DB every 60 s for due tasks."""

    def __init__(self) -> None:
        self._running = False
        self._task: asyncio.Task | None = None
        self._check_interval = 60  # seconds

    async def start(self) -> None:
        """Start the scheduler loop."""
        self._running = True
        logger.info("Scheduler started.")
        while self._running:
            try:
                await self._tick()
            except Exception:
                logger.exception("Scheduler tick error")
            await asyncio.sleep(self._check_interval)

    def stop(self) -> None:
        """Signal the scheduler to stop."""
        self._running = False
        logger.info("Scheduler stopped.")

    async def _tick(self) -> None:
        """Find and execute all due tasks."""
        now = datetime.now(timezone.utc)

        async with async_session() as db:
            # Fetch all enabled tasks then filter in Python to avoid
            # SQLite naive-vs-aware datetime comparison crashes.
            result = await db.execute(
                select(ScheduledTask).where(
                    ScheduledTask.enabled.is_(True),
                )
            )
            all_enabled = result.scalars().all()
            due_tasks = [
                t for t in all_enabled
                if t.next_run and ensure_utc(t.next_run) <= now
            ]

            for task in due_tasks:
                try:
                    await self._execute(task, db)
                except Exception:
                    logger.exception(f"Failed to execute scheduled task {task.id} ({task.name})")

                # Update timestamps regardless of success
                task.last_run = now
                try:
                    task.next_run = CronParser.next_run_after(task.cron_expression, now)
                except ValueError:
                    logger.warning(f"Invalid cron for task {task.id}; disabling.")
                    task.enabled = False

            if due_tasks:
                await db.commit()

    async def _execute(self, task: ScheduledTask, db: AsyncSession) -> None:
        """Execute a single scheduled task."""
        logger.info(f"Executing scheduled task: {task.name} (skill={task.skill_name or 'none'})")

        if task.skill_name:
            # Run the named skill via the registry
            from app.skills.registry import registry
            from app.skills.base import SkillInput

            skill = registry.get(task.skill_name)
            if skill is None:
                logger.warning(f"Skill '{task.skill_name}' not found for scheduled task {task.id}")
                return

            skill_input = SkillInput(
                project_id=task.project_id,
                parameters={"scheduled": True, "schedule_id": task.id},
            )
            await skill.execute(skill_input)
        else:
            # No skill — broadcast a reminder via WebSocket
            from app.api.websocket import broadcast_suggestion

            await broadcast_suggestion(
                message=f"Scheduled reminder: {task.name}"
                + (f" — {task.description}" if task.description else ""),
                project_id=task.project_id,
                action="scheduled_reminder",
            )


# Module-level singleton
scheduler = Scheduler()
