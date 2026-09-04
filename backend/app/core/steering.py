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
        # Active work is tracked per (project_id, session_key) binding — not a
        # single global slot — so two concurrent turns of the same agent never
        # clear each other's working flag (no spurious aborts). Entries are
        # (normalized_project_id_or_"", session_key_or_"").
        self._active_work: dict[str, set[tuple[str, str]]] = {}

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
            if scoped_project_id:
                try:
                    from app.core.telemetry import telemetry_recorder

                    await telemetry_recorder.record_steering_event(
                        project_id=scoped_project_id,
                        agent_id=agent_id,
                        action="steer_queued",
                        queue_depth=len(state.steering_queue),
                    )
                except Exception as exc:
                    logger.debug("Steering telemetry skipped: %s", exc)

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
            if scoped_project_id:
                try:
                    from app.core.telemetry import telemetry_recorder

                    await telemetry_recorder.record_steering_event(
                        project_id=scoped_project_id,
                        agent_id=agent_id,
                        action="follow_up_queued",
                        queue_depth=len(state.follow_up_queue),
                    )
                except Exception as exc:
                    logger.debug("Follow-up telemetry skipped: %s", exc)

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
            messages = self._drain_matching(
                state.steering_queue,
                mode=state.steering_mode,
                project_id=project_id,
            )
            if messages:
                scoped_project_id = self._normalize_project_id(project_id)
                if scoped_project_id:
                    try:
                        from app.core.telemetry import telemetry_recorder

                        await telemetry_recorder.record_steering_event(
                            project_id=scoped_project_id,
                            agent_id=agent_id,
                            action="steer_drained",
                            queue_depth=len(messages),
                        )
                    except Exception as exc:
                        logger.debug("Steering drain telemetry skipped: %s", exc)
            return messages

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

    def _work_set(self, agent_id: str) -> set[tuple[str, str]]:
        return self._active_work.setdefault(agent_id, set())

    def _work_matches(
        self,
        entry: tuple[str, str],
        scoped_project_id: str | None,
        session_key: str | None,
    ) -> bool:
        project, sess = entry
        if session_key is not None and sess != session_key:
            return False
        if scoped_project_id is not None and project != scoped_project_id:
            return False
        return True

    def _has_work(
        self,
        agent_id: str,
        *,
        project_id: str | None = None,
        session_key: str | None = None,
    ) -> bool:
        scoped_project_id = self._normalize_project_id(project_id)
        return any(
            self._work_matches(entry, scoped_project_id, session_key)
            for entry in self._active_work.get(agent_id, ())
        )

    def is_binding_working(
        self,
        agent_id: str,
        project_id: str | None = None,
        session_key: str | None = None,
    ) -> bool:
        """Check one ``(agent_id, project_id, session_key)`` binding's working flag.

        The Pi steering pump polls this — never the global single slot — so a
        concurrent turn of the same agent finishing cannot read as an abort.
        """
        return self._has_work(agent_id, project_id=project_id, session_key=session_key)

    async def mark_working(
        self,
        agent_id: str,
        project_id: str | None = None,
        session_key: str | None = None,
    ) -> None:
        """Mark agent as currently working (starting a task/skill)."""
        state = self._get_or_create(agent_id)
        async with state.lock:
            scoped_project_id = self._normalize_project_id(project_id)
            self._work_set(agent_id).add((scoped_project_id or "", session_key or ""))
            state.is_working = True
            state.active_project_id = scoped_project_id or ""
            state.work_complete_event.clear()

    async def mark_idle(
        self,
        agent_id: str,
        project_id: str | None = None,
        session_key: str | None = None,
    ) -> None:
        """Mark agent as idle (finished all work).

        Only this binding's ``(project_id, session_key)`` mark is cleared; work
        marked by other concurrent bindings keeps the agent working. The legacy
        single-slot mirror (``active_project_id``) is kept in sync for older
        callers.
        """
        state = self._get_or_create(agent_id)
        async with state.lock:
            scoped_project_id = self._normalize_project_id(project_id)
            work = self._work_set(agent_id)
            for entry in list(work):
                if self._work_matches(entry, scoped_project_id, session_key):
                    work.discard(entry)
            state.is_working = bool(work)
            if (
                scoped_project_id is None
                or state.active_project_id == scoped_project_id
                or not work
            ):
                state.active_project_id = sorted(work)[0][0] if work else ""
            if not state.is_working:
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
        if scoped_project_id and not self._has_work(agent_id, project_id=scoped_project_id):
            return True
        try:
            await asyncio.wait_for(state.work_complete_event.wait(), timeout=timeout)
            return True
        except TimeoutError:
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
            is_working = self._has_work(agent_id, project_id=scoped_project_id)
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
        statuses = {
            agent_id: self.get_status(agent_id, project_id=project_id) for agent_id in self._agents
        }
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
            work = self._work_set(agent_id)
            for entry in list(work):
                if self._work_matches(entry, scoped_project_id, None):
                    work.discard(entry)
            state.is_working = bool(work)
            if (
                scoped_project_id is None
                or state.active_project_id == scoped_project_id
                or not work
            ):
                state.active_project_id = sorted(work)[0][0] if work else ""
            if not state.is_working:
                state.work_complete_event.set()
            res = {
                "steering": self._clear_matching(
                    state.steering_queue, project_id=scoped_project_id
                ),
                "follow_up": self._clear_matching(
                    state.follow_up_queue, project_id=scoped_project_id
                ),
            }
            if scoped_project_id:
                try:
                    from app.core.telemetry import telemetry_recorder

                    await telemetry_recorder.record_steering_event(
                        project_id=scoped_project_id,
                        agent_id=agent_id,
                        action="abort",
                    )
                except Exception as exc:
                    logger.debug("Abort telemetry skipped: %s", exc)
            return res


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

steering_manager = SteeringManager()
