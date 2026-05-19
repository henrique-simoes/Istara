"""Mid-execution steering for Istara agents.

Implements the steering pattern inspired by pi-mono's PendingMessageQueue:
- **Steering messages**: Injected after the current skill execution completes.
  The agent picks them up and creates interim tasks to address them.
  Tools/skills already in progress are NEVER interrupted — steering waits
  for the current turn to finish (deferred execution, matching pi-mono's
  post-commit 208a2cc behavior).
- **Follow-up messages**: Injected only when the agent would otherwise stop
  working (all tasks complete, no pending work).
- **Queue modes**: "one-at-a-time" (default — delivers one message, waits
  for response) or "all" (delivers all queued messages at once).
- **Abort**: Signals the current skill execution to stop. Queued steering
  messages are cleared (like pi-mono's Escape behavior).

Usage:
    from app.core.steering import steering_manager

    # Queue a steering message
    steering_manager.steer("istara-main", "Also check the accessibility of the new page")

    # Queue a follow-up
    steering_manager.follow_up("istara-main", "After that, run the UX audit")

    # In agent work cycle, after skill execution:
    messages = steering_manager.get_steering("istara-main")
    for msg in messages:
        # Create interim task from steering message
        ...

    # After all work complete:
    follow_ups = steering_manager.get_follow_up("istara-main")
    for msg in follow_ups:
        # Continue working with follow-up tasks
        ...

    # Wait for agent to finish
    await steering_manager.wait_for_idle("istara-main")
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.core.steering_types import (
    AgentSteeringState,
    SteeringMessage,
    SteeringMode,
    SteeringQueue,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Steering Manager — global registry of per-agent steering state
# ---------------------------------------------------------------------------

class SteeringManager:
    """Global manager for agent steering queues.

    Provides:
    - steer(agent_id, message) — queue steering message
    - follow_up(agent_id, message) — queue follow-up message
    - get_steering(agent_id) — drain steering queue (called by agent loop)
    - get_follow_up(agent_id) — drain follow-up queue
    - abort(agent_id) — abort current work, clear steering queues
    - wait_for_idle(agent_id) — wait until agent finishes all work
    """

    def __init__(self) -> None:
        self._agents: dict[str, AgentSteeringState] = {}

    def _get_or_create(self, agent_id: str) -> AgentSteeringState:
        """Get or create steering state for an agent."""
        if agent_id not in self._agents:
            self._agents[agent_id] = AgentSteeringState()
        return self._agents[agent_id]

    @staticmethod
    def _normalize_project_id(project_id: str | None) -> str | None:
        if project_id is None:
            return None
        normalized = str(project_id).strip()
        return normalized or None

    def _matches_project(self, message: SteeringMessage, project_id: str | None) -> bool:
        return self._normalize_project_id(message.metadata.get("project_id")) == (
            self._normalize_project_id(project_id)
        )

    def _drain_matching(
        self,
        messages: list[SteeringMessage],
        *,
        mode: SteeringMode,
        project_id: str | None,
    ) -> list[SteeringMessage]:
        if not messages:
            return []
        if mode == "all":
            drained = [msg for msg in messages if self._matches_project(msg, project_id)]
            messages[:] = [msg for msg in messages if not self._matches_project(msg, project_id)]
            return drained
        for idx, msg in enumerate(messages):
            if self._matches_project(msg, project_id):
                return [messages.pop(idx)]
        return []

    def _clear_matching(
        self,
        messages: list[SteeringMessage],
        *,
        project_id: str | None,
    ) -> list[SteeringMessage]:
        cleared = [msg for msg in messages if self._matches_project(msg, project_id)]
        messages[:] = [msg for msg in messages if not self._matches_project(msg, project_id)]
        return cleared

    def _matching_messages(
        self,
        messages: list[SteeringMessage],
        project_id: str | None,
    ) -> list[SteeringMessage]:
        return [msg for msg in messages if self._matches_project(msg, project_id)]

    # -----------------------------------------------------------------------
    # Steering message queueing
    # -----------------------------------------------------------------------

    async def steer(
        self,
        agent_id: str,
        message: str,
        source: str = "user",
        metadata: dict[str, Any] | None = None,
        project_id: str | None = None,
        mode: SteeringMode | None = None,
    ) -> None:
        """Queue a steering message to be injected after current skill execution."""
        state = self._get_or_create(agent_id)
        async with state.lock:
            if mode is not None:
                state.steering_mode = mode
            msg_metadata = dict(metadata or {})
            scoped_project_id = self._normalize_project_id(project_id)
            if scoped_project_id is not None:
                msg_metadata["project_id"] = scoped_project_id
            msg = SteeringMessage(message=message, source=source, metadata=msg_metadata)
            state.steering_queue.append(msg)
            logger.info(f"Steering queued for {agent_id}: {message[:80]}...")

    async def follow_up(
        self,
        agent_id: str,
        message: str,
        source: str = "user",
        metadata: dict[str, Any] | None = None,
        project_id: str | None = None,
        mode: SteeringMode | None = None,
    ) -> None:
        """Queue a follow-up message to be injected when agent would otherwise stop."""
        state = self._get_or_create(agent_id)
        async with state.lock:
            if mode is not None:
                state.follow_up_mode = mode
            msg_metadata = dict(metadata or {})
            scoped_project_id = self._normalize_project_id(project_id)
            if scoped_project_id is not None:
                msg_metadata["project_id"] = scoped_project_id
            msg = SteeringMessage(message=message, source=source, metadata=msg_metadata)
            state.follow_up_queue.append(msg)
            logger.info(f"Follow-up queued for {agent_id}: {message[:80]}...")

    # -----------------------------------------------------------------------
    # Steering message retrieval (called by agent work cycle)
    # -----------------------------------------------------------------------

    async def get_steering(
        self,
        agent_id: str,
        project_id: str | None = None,
    ) -> list[SteeringMessage]:
        """Drain steering queue. Called by agent after each skill execution completes."""
        state = self._get_or_create(agent_id)
        async with state.lock:
            return self._drain_matching(
                state.steering_queue,
                mode=state.steering_mode,
                project_id=project_id,
            )

    async def get_follow_up(
        self,
        agent_id: str,
        project_id: str | None = None,
    ) -> list[SteeringMessage]:
        """Drain follow-up queue. Called when agent would otherwise stop working."""
        state = self._get_or_create(agent_id)
        async with state.lock:
            return self._drain_matching(
                state.follow_up_queue,
                mode=state.follow_up_mode,
                project_id=project_id,
            )

    # -----------------------------------------------------------------------
    # Queue management
    # -----------------------------------------------------------------------

    async def clear_steering(
        self,
        agent_id: str,
        project_id: str | None = None,
    ) -> list[SteeringMessage]:
        """Clear and return all queued steering messages."""
        state = self._get_or_create(agent_id)
        async with state.lock:
            return self._clear_matching(state.steering_queue, project_id=project_id)

    async def clear_follow_up(
        self,
        agent_id: str,
        project_id: str | None = None,
    ) -> list[SteeringMessage]:
        """Clear and return all queued follow-up messages."""
        state = self._get_or_create(agent_id)
        async with state.lock:
            return self._clear_matching(state.follow_up_queue, project_id=project_id)

    async def clear_all(
        self,
        agent_id: str,
        project_id: str | None = None,
    ) -> dict[str, list[SteeringMessage]]:
        """Clear both queues and return the cleared messages."""
        return {
            "steering": await self.clear_steering(agent_id, project_id=project_id),
            "follow_up": await self.clear_follow_up(agent_id, project_id=project_id),
        }

    def get_queues(
        self,
        agent_id: str,
        project_id: str | None = None,
    ) -> dict[str, list[SteeringMessage]]:
        state = self._get_or_create(agent_id)
        return {
            "steering": self._matching_messages(state.steering_queue, project_id),
            "follow_up": self._matching_messages(state.follow_up_queue, project_id),
        }

    async def project_ids_with_queued_steering(self, agent_id: str) -> list[str]:
        """Return project ids that currently have queued steering messages."""
        state = self._get_or_create(agent_id)
        async with state.lock:
            project_ids: list[str] = []
            for msg in state.steering_queue:
                msg_project_id = self._normalize_project_id(msg.metadata.get("project_id"))
                if msg_project_id and msg_project_id not in project_ids:
                    project_ids.append(msg_project_id)
            return project_ids

    # -----------------------------------------------------------------------
    # Agent state management
    # -----------------------------------------------------------------------

    async def mark_working(self, agent_id: str, project_id: str | None = None) -> None:
        """Mark agent as currently working (starting a task/skill)."""
        state = self._get_or_create(agent_id)
        async with state.lock:
            state.is_working = True
            state.active_project_id = self._normalize_project_id(project_id) or ""
            state.work_complete_event.clear()

    async def mark_idle(self, agent_id: str, project_id: str | None = None) -> None:
        """Mark agent as idle (finished all work)."""
        state = self._get_or_create(agent_id)
        async with state.lock:
            scoped_project_id = self._normalize_project_id(project_id)
            if scoped_project_id is None or state.active_project_id == scoped_project_id:
                state.is_working = False
                state.active_project_id = ""
                state.work_complete_event.set()

    def is_working(self, agent_id: str) -> bool:
        """Check if agent is currently working."""
        state = self._get_or_create(agent_id)
        return state.is_working

    async def wait_for_idle(
        self,
        agent_id: str,
        timeout: float = 300.0,
        project_id: str | None = None,
    ) -> bool:
        """Wait until agent finishes all work (steering + follow-up processed)."""
        state = self._get_or_create(agent_id)
        scoped_project_id = self._normalize_project_id(project_id)
        if scoped_project_id and state.active_project_id != scoped_project_id:
            return True
        try:
            await asyncio.wait_for(state.work_complete_event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            logger.warning(f"wait_for_idle timed out for {agent_id} after {timeout}s")
            return False

    # -----------------------------------------------------------------------
    # Status inspection
    # -----------------------------------------------------------------------

    def get_status(
        self,
        agent_id: str,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        """Get steering status for an agent."""
        state = self._get_or_create(agent_id)
        scoped_project_id = self._normalize_project_id(project_id)
        steering_count = len(self._matching_messages(state.steering_queue, scoped_project_id))
        follow_up_count = len(self._matching_messages(state.follow_up_queue, scoped_project_id))
        is_working = state.is_working
        if scoped_project_id is not None:
            is_working = state.is_working and state.active_project_id == scoped_project_id
        return {
            "agent_id": agent_id,
            "project_id": scoped_project_id or "",
            "is_working": is_working,
            "steering_queue_count": steering_count,
            "follow_up_queue_count": follow_up_count,
            "steering_mode": state.steering_mode,
            "follow_up_mode": state.follow_up_mode,
            "has_queued_messages": steering_count > 0 or follow_up_count > 0,
        }

    def get_all_status(self, project_id: str | None = None) -> dict[str, dict[str, Any]]:
        """Get steering status for all agents."""
        statuses = {agent_id: self.get_status(agent_id, project_id=project_id) for agent_id in self._agents}
        if self._normalize_project_id(project_id) is None:
            return statuses
        return {
            agent_id: status
            for agent_id, status in statuses.items()
            if status["has_queued_messages"] or status["is_working"]
        }

    # -----------------------------------------------------------------------
    # Abort
    # -----------------------------------------------------------------------

    async def abort(
        self,
        agent_id: str,
        project_id: str | None = None,
    ) -> dict[str, list[SteeringMessage]]:
        """Abort current work and clear steering queues.

        Returns cleared messages so caller can restore them to editor
        (like pi-mono's Escape behavior).
        """
        state = self._get_or_create(agent_id)
        async with state.lock:
            scoped_project_id = self._normalize_project_id(project_id)
            if scoped_project_id is None or state.active_project_id == scoped_project_id:
                state.is_working = False
                state.active_project_id = ""
                state.work_complete_event.set()
            res = {
                "steering": self._clear_matching(state.steering_queue, project_id=scoped_project_id),
                "follow_up": self._clear_matching(state.follow_up_queue, project_id=scoped_project_id),
            }
            return res


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

steering_manager = SteeringManager()
