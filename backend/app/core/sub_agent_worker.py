"""Sub-Agent Worker — adds task execution capability to monitoring agents.

Each sub-agent (devops, ui-audit, ux-eval, sim) can now execute tasks
assigned to them via the intelligent task router, in addition to their
existing monitoring/audit duties.

This module provides a shared work loop that any sub-agent can integrate.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import case, select, or_

from app.models.database import async_session
from app.models.task import Task, TaskStatus
from app.models.agent import Agent, AgentState
from app.api.websocket import broadcast_agent_status, broadcast_task_progress

logger = logging.getLogger(__name__)


class SubAgentWorker:
    """Mixin-like worker that picks and executes tasks for a specific agent."""

    def __init__(self, agent_id: str, check_interval: int = 30):
        self._agent_id = agent_id
        self._check_interval = check_interval
        self._running = False

    async def start_task_loop(self) -> None:
        """Start checking for and executing assigned tasks."""
        self._running = True
        logger.info(f"SubAgentWorker started for {self._agent_id}")
        while self._running:
            try:
                await self._check_and_execute()
            except Exception as e:
                logger.error(f"SubAgentWorker {self._agent_id} error: {e}")
            await asyncio.sleep(self._check_interval)

    def stop_task_loop(self) -> None:
        self._running = False

    async def _check_and_execute(self) -> None:
        """Check for tasks assigned to this agent and execute them."""
        async with async_session() as db:
            priority_order = case(
                (Task.priority == "critical", 0),
                (Task.priority == "high", 1),
                (Task.priority == "medium", 2),
                (Task.priority == "low", 3),
                else_=4,
            )

            result = await db.execute(
                select(Task)
                .where(
                    Task.status.in_([TaskStatus.BACKLOG, TaskStatus.IN_PROGRESS]),
                    Task.agent_id == self._agent_id,
                    or_(
                        Task.locked_by.is_(None),
                        Task.locked_by == self._agent_id,
                    ),
                )
                .order_by(priority_order, Task.position.asc())
                .limit(1)
            )
            task = result.scalar_one_or_none()
            if not task:
                return

            logger.info(f"SubAgent {self._agent_id} picking up task: {task.title}")
            await self._execute_with_main_pipeline(db, task)

    async def _execute_with_main_pipeline(self, db, task: Task) -> None:
        """Delegate to the main AgentOrchestrator's execution pipeline."""
        from app.core.agent import AgentOrchestrator
        from app.models.project import Project

        # Create a temporary orchestrator instance for this agent
        executor = AgentOrchestrator(agent_id=self._agent_id)

        project_result = await db.execute(
            select(Project).where(Project.id == task.project_id)
        )
        project = project_result.scalar_one_or_none()
        if not project:
            logger.warning(f"Project {task.project_id} not found for task {task.id}")
            return

        try:
            await executor._execute_task(db, task, project)
        except Exception as e:
            logger.error(f"SubAgent {self._agent_id} task execution failed: {e}")
            task.status = TaskStatus.BACKLOG
            task.agent_notes = f"Execution failed: {str(e)[:200]}"
            await db.commit()

    async def check_collaboration_requests(self) -> list[dict]:
        """Check A2A inbox for collaboration requests."""
        from app.services.a2a import get_messages
        async with async_session() as db:
            messages = await get_messages(db, self._agent_id, limit=10, unread_only=True)
            collab_requests = [
                m for m in messages
                if m.get("message_type") == "collaboration_request"
            ]
            return collab_requests
