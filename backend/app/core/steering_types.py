"""Types and queue primitives for mid-execution steering."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Literal

SteeringMode = Literal["one-at-a-time", "all"]


@dataclass
class SteeringMessage:
    """A single steering message from a user or extension."""

    message: str
    timestamp: float = field(default_factory=time.time)
    source: str = "user"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentSteeringState:
    """Per-agent steering state."""

    steering_queue: list[SteeringMessage] = field(default_factory=list)
    follow_up_queue: list[SteeringMessage] = field(default_factory=list)
    steering_mode: SteeringMode = "one-at-a-time"
    follow_up_mode: SteeringMode = "one-at-a-time"
    is_working: bool = False
    active_project_id: str = ""
    work_complete_event: asyncio.Event = field(default_factory=asyncio.Event)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class SteeringQueue:
    """Thread-safe steering queue with configurable drain mode."""

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
        first = self._messages.pop(0)
        return [first]

    def clear(self) -> list[SteeringMessage]:
        """Clear and return all queued messages."""

        messages = self._messages[:]
        self._messages.clear()
        return messages

    def count(self) -> int:
        return len(self._messages)
