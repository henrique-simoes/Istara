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
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

SteeringMode = "one-at-a-time" | "all"


@dataclass
class SteeringMessage:
    """A single steering message from a user or extension."""
    message: str
    timestamp: float = field(default_factory=time.time)
    source: str = "user"  # "user", "extension", "system"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentSteeringState:
    """Per-agent steering state."""
    steering_queue: list[SteeringMessage] = field(default_factory=list)
    follow_up_queue: list[SteeringMessage] = field(default_factory=list)
    steering_mode: SteeringMode = "one-at-a-time"
    follow_up_mode: SteeringMode = "one-at-a-time"
    is_working: bool = False
    work_complete_event: asyncio.Event = field(default_factory=asyncio.Event)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


# ---------------------------------------------------------------------------
# Steering Queue (inspired by pi-mono's PendingMessageQueue)
# ---------------------------------------------------------------------------

class SteeringQueue:
    """Thread-safe steering queue with configurable drain mode.

    Mirrors pi-mono's PendingMessageQueue:
    - "one-at-a-time": drain() returns first message only
    - "all": drain() returns all messages
    """

    def __init__(self, mode: SteeringMode = "one-at-a-time"):
        self._messages: list[SteeringMessage] = []
        self._mode: SteeringMode = mode

    @property
    def mode(self) -> SteeringMode:
        return self._mode

    @mode.setter
    def mode(self, value: SteeringMode) -> None:
        self._mode = value

    def enqueue(self, message: SteeringMessage) -> None:
        self._messages.append(message)

    def has_items(self) -> bool:
        return len(self._messages) > 0

    def drain(self) -> list[SteeringMessage]:
        if not self._messages:
            return []
        if self._mode == "all":
            drained = self._messages[:]
            self._messages.clear()
            return drained
        # one-at-a-time: return first message only
        first = self._messages.pop(0)
        return [first]

    def clear(self) -> list[SteeringMessage]:
        """Clear and return all queued messages (for abort restoration)."""
        messages = self._messages[:]
        self._messages.clear()
        return messages

    def count(self) -> int:
        return len(self._messages)


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

    # -----------------------------------------------------------------------
    # Steering message queueing
    # -----------------------------------------------------------------------

    def steer(
        self,
        agent_id: str,
        message: str,
        source: str = "user",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Queue a steering message to be injected after current skill execution."""
        state = self._get_or_create(agent_id)
        msg = SteeringMessage(message=message, source=source, metadata=metadata or {})
        state.steering_queue.append(msg)
        logger.info(f"Steering queued for {agent_id}: {message[:80]}...")

    def follow_up(
        self,
        agent_id: str,
        message: str,
        source: str = "user",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Queue a follow-up message to be injected when agent would otherwise stop."""
        state = self._get_or_create(agent_id)
        msg = SteeringMessage(message=message, source=source, metadata=metadata or {})
        state.follow_up_queue.append(msg)
        logger.info(f"Follow-up queued for {agent_id}: {message[:80]}...")

    # -----------------------------------------------------------------------
    # Steering message retrieval (called by agent work cycle)
    # -----------------------------------------------------------------------

    def get_steering(self, agent_id: str) -> list[SteeringMessage]:
        """Drain steering queue. Called by agent after each skill execution completes.

        Steering messages are NEVER injected mid-skill — they wait for the
        current turn to finish (deferred execution).
        """
        state = self._get_or_create(agent_id)
        sq = SteeringQueue(state.steering_mode)
        sq._messages = state.steering_queue  # Direct access, caller manages lock
        return sq.drain()

    def get_follow_up(self, agent_id: str) -> list[SteeringMessage]:
        """Drain follow-up queue. Called when agent would otherwise stop working."""
        state = self._get_or_create(agent_id)
        fq = SteeringQueue(state.follow_up_mode)
        fq._messages = state.follow_up_queue
        return fq.drain()

    # -----------------------------------------------------------------------
    # Queue management
    # -----------------------------------------------------------------------

    def clear_steering(self, agent_id: str) -> list[SteeringMessage]:
        """Clear and return all queued steering messages."""
        state = self._get_or_create(agent_id)
        messages = state.steering_queue[:]
        state.steering_queue.clear()
        return messages

    def clear_follow_up(self, agent_id: str) -> list[SteeringMessage]:
        """Clear and return all queued follow-up messages."""
        state = self._get_or_create(agent_id)
        messages = state.follow_up_queue[:]
        state.follow_up_queue.clear()
        return messages

    def clear_all(self, agent_id: str) -> dict[str, list[SteeringMessage]]:
        """Clear both queues and return the cleared messages."""
        return {
            "steering": self.clear_steering(agent_id),
            "follow_up": self.clear_follow_up(agent_id),
        }

    # -----------------------------------------------------------------------
    # Agent state management
    # -----------------------------------------------------------------------

    def mark_working(self, agent_id: str) -> None:
        """Mark agent as currently working (starting a task/skill)."""
        state = self._get_or_create(agent_id)
        state.is_working = True
        state.work_complete_event.clear()

    def mark_idle(self, agent_id: str) -> None:
        """Mark agent as idle (finished all work)."""
        state = self._get_or_create(agent_id)
        state.is_working = False
        state.work_complete_event.set()

    def is_working(self, agent_id: str) -> bool:
        """Check if agent is currently working."""
        state = self._get_or_create(agent_id)
        return state.is_working

    async def wait_for_idle(self, agent_id: str, timeout: float = 300.0) -> bool:
        """Wait until agent finishes all work (steering + follow-up processed).

        Returns True if agent became idle, False if timeout.
        Mirrors pi-mono's waitForIdle().
        """
        state = self._get_or_create(agent_id)
        try:
            await asyncio.wait_for(state.work_complete_event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            logger.warning(f"wait_for_idle timed out for {agent_id} after {timeout}s")
            return False

    # -----------------------------------------------------------------------
    # Status inspection
    # -----------------------------------------------------------------------

    def get_status(self, agent_id: str) -> dict[str, Any]:
        """Get steering status for an agent."""
        state = self._get_or_create(agent_id)
        return {
            "agent_id": agent_id,
            "is_working": state.is_working,
            "steering_queue_count": len(state.steering_queue),
            "follow_up_queue_count": len(state.follow_up_queue),
            "steering_mode": state.steering_mode,
            "follow_up_mode": state.follow_up_mode,
            "has_queued_messages": len(state.steering_queue) > 0 or len(state.follow_up_queue) > 0,
        }

    def get_all_status(self) -> dict[str, dict[str, Any]]:
        """Get steering status for all agents."""
        return {agent_id: self.get_status(agent_id) for agent_id in self._agents}

    # -----------------------------------------------------------------------
    # Abort
    # -----------------------------------------------------------------------

    def abort(self, agent_id: str) -> dict[str, list[SteeringMessage]]:
        """Abort current work and clear steering queues.

        Returns cleared messages so caller can restore them to editor
        (like pi-mono's Escape behavior).
        """
        state = self._get_or_create(agent_id)
        state.is_working = False
        state.work_complete_event.set()
        return self.clear_all(agent_id)


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

steering_manager = SteeringManager()
