# Inspired by Karpathy's autoresearch (MIT) — https://github.com/karpathy/autoresearch
"""Base runner interface for autoresearch optimization loops."""

from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable


class BaseLoopRunner(ABC):
    """Abstract base for all autoresearch loop runners."""

    loop_type: str = ""  # Override in subclass
    needs_persona_lock: bool = False  # True for loops that modify persona files

    @abstractmethod
    async def measure_baseline(self, target: str) -> float:
        """Measure the current score before any mutations."""
        ...

    @abstractmethod
    async def measure(self, target: str) -> float:
        """Measure the score after a mutation has been applied."""
        ...

    @abstractmethod
    async def hypothesize(
        self, target: str, current_score: float, history: list[dict]
    ) -> tuple[str, dict]:
        """Generate a hypothesis and mutation.

        Returns (hypothesis_text, mutation_dict).
        mutation_dict should contain at minimum a "description" key.
        """
        ...

    @abstractmethod
    async def apply_mutation(
        self, target: str, mutation: dict
    ) -> Callable[[], Awaitable[None]]:
        """Apply a mutation and return an async revert function.

        The revert function restores the state to before the mutation.
        """
        ...
