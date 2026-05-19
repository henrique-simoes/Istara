"""Lightweight async cron scheduler — no external dependencies.

Fills audit gap #5: user-configurable cron scheduling for agents and skills.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text, delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.datetime_utils import ensure_utc
from app.models.database import Base, async_session
from app.models.project import Project

logger = logging.getLogger(__name__)


class PermanentScheduleError(RuntimeError):
    """A schedule configuration error that will not recover by retrying."""


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
    is_running: Mapped[bool] = mapped_column(Boolean, default=False)
    last_run: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    agent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    loop_type: Mapped[str] = mapped_column(String(50), default="cron")  # cron | interval | custom
    interval_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    execution_count: Mapped[int] = mapped_column(Integer, default=0)
    last_status: Mapped[str] = mapped_column(String(20), default="")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict:
        """Serialize to API-ready dict."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "cron_expression": self.cron_expression,
            "skill_name": self.skill_name,
            "project_id": self.project_id,
            "enabled": self.enabled,
            "is_running": self.is_running,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "agent_id": self.agent_id,
            "loop_type": self.loop_type,
            "interval_seconds": self.interval_seconds,
            "execution_count": self.execution_count,
            "last_status": self.last_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


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
    def _parse_value(cls, raw: str, lo: int, hi: int) -> int:
        """Parse and bounds-check a cron field value."""
        try:
            value = int(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid cron value {raw!r}") from exc
        if value < lo or value > hi:
            raise ValueError(f"Cron value {value} is outside the allowed range {lo}-{hi}")
        return value

    @classmethod
    def _expand_field(cls, token: str, lo: int, hi: int) -> set[int]:
        """Expand a single cron field token into a set of valid integers."""
        if not token:
            raise ValueError("Cron fields cannot be empty")
        if token == "*":
            return set(range(lo, hi + 1))
        if token.startswith("*/"):
            try:
                step = int(token[2:])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid cron step {token!r}") from exc
            if step <= 0:
                raise ValueError("Cron step must be greater than zero")
            return set(range(lo, hi + 1, step))

        values: set[int] = set()
        for part in token.split(","):
            if not part:
                raise ValueError("Cron list entries cannot be empty")
            if "-" in part:
                start_raw, end_raw = part.split("-", 1)
                start = cls._parse_value(start_raw, lo, hi)
                end = cls._parse_value(end_raw, lo, hi)
                if start > end:
                    raise ValueError(f"Cron range start {start} cannot be greater than {end}")
                values.update(range(start, end + 1))
            else:
                values.add(cls._parse_value(part, lo, hi))
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
        self._stale_running_after = timedelta(hours=1)

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
            await self._reset_stale_running_tasks(db, now)

            # Fetch enabled tasks for active projects, then filter due time in
            # Python to avoid SQLite naive-vs-aware datetime comparison crashes.
            result = await db.execute(
                select(ScheduledTask)
                .outerjoin(Project, Project.id == ScheduledTask.project_id)
                .where(
                    ScheduledTask.enabled.is_(True),
                    ScheduledTask.is_running.is_(False),
                    or_(Project.id.is_(None), Project.is_paused.is_(False)),
                )
            )
            all_enabled = result.scalars().all()
            due_tasks = [
                t for t in all_enabled
                if t.next_run and ensure_utc(t.next_run) <= now
            ]

            for task in due_tasks:
                # Mark as running before execution
                task.is_running = True
                await db.commit()

                exec_started = datetime.now(timezone.utc)
                exec_status = "success"
                exec_error = ""

                permanent_failure = False
                try:
                    exec_status = await self._execute(task, db)
                except PermanentScheduleError as exc:
                    permanent_failure = True
                    exec_status = "failure"
                    exec_error = str(exc)
                    logger.error(
                        "Disabling scheduled task %s (%s): %s",
                        task.id,
                        task.name,
                        exec_error,
                    )
                except Exception as exc:
                    exec_status = "failure"
                    exec_error = str(exc)
                    logger.exception(f"Failed to execute scheduled task {task.id} ({task.name})")
                finally:
                    # Always clear the running flag
                    task.is_running = False
                    exec_finished = datetime.now(timezone.utc)

                    # Record execution
                    task.execution_count = (task.execution_count or 0) + 1
                    task.last_status = exec_status
                    try:
                        from app.services.loop_execution_service import record_execution
                        await record_execution(
                            source_type="custom" if task.loop_type == "custom" else "schedule",
                            source_id=task.id,
                            source_name=task.name,
                            status=exec_status,
                            started_at=exec_started,
                            finished_at=exec_finished,
                            error_message=exec_error,
                        )
                    except Exception:
                        logger.debug("Failed to record loop execution", exc_info=True)

                # Update timestamps regardless of success
                task.last_run = now
                if permanent_failure:
                    task.enabled = False
                    task.next_run = None
                    continue

                try:
                    task.next_run = CronParser.next_run_after(task.cron_expression, now)
                except ValueError:
                    logger.warning(f"Invalid cron for task {task.id}; disabling.")
                    task.enabled = False

            if due_tasks:
                await db.commit()

    async def _reset_stale_running_tasks(self, db: AsyncSession, now: datetime) -> None:
        """Release tasks left running by a crashed process or interrupted tick."""
        result = await db.execute(
            select(ScheduledTask).where(
                ScheduledTask.enabled.is_(True),
                ScheduledTask.is_running.is_(True),
            )
        )
        stale_cutoff = now - self._stale_running_after
        reset_count = 0
        for task in result.scalars().all():
            next_run = ensure_utc(task.next_run) if task.next_run else None
            if next_run and next_run <= stale_cutoff:
                task.is_running = False
                task.last_status = "failure"
                reset_count += 1
        if reset_count:
            logger.warning("Released %s stale scheduled task leases", reset_count)
            await db.commit()

    async def _execute(self, task: ScheduledTask, db: AsyncSession) -> str:
        """Execute a single scheduled task."""
        logger.info(f"Executing scheduled task: {task.name} (skill={task.skill_name or 'none'})")

        project = await db.get(Project, task.project_id)
        if not project:
            raise PermanentScheduleError(
                f"Project {task.project_id!r} not found for scheduled task {task.id}"
            )
        if project and project.is_paused:
            logger.info(
                "Skipping scheduled task %s because project %s is paused",
                task.id,
                task.project_id,
            )
            return "paused"

        if task.skill_name:
            # Run the named skill via the registry
            from app.skills.registry import registry
            from app.skills.base import SkillInput

            skill = registry.get(task.skill_name)
            if skill is None:
                raise PermanentScheduleError(
                    f"Skill {task.skill_name!r} not found for scheduled task {task.id}"
                )

            skill_input = SkillInput(
                project_id=task.project_id,
                parameters={"scheduled": True, "schedule_id": task.id},
            )
            output = await skill.execute(skill_input)
            if getattr(output, "success", True) is False:
                errors = "; ".join(str(error) for error in getattr(output, "errors", []) or [])
                summary = getattr(output, "summary", "") or "Skill execution failed"
                raise RuntimeError(errors or summary)
        else:
            # No skill — broadcast a reminder via WebSocket
            from app.api.websocket import broadcast_suggestion

            await broadcast_suggestion(
                message=f"Scheduled reminder: {task.name}"
                + (f" — {task.description}" if task.description else ""),
                project_id=task.project_id,
                action="scheduled_reminder",
            )

        return "success"


# Module-level singleton
scheduler = Scheduler()
