# Inspired by Karpathy's autoresearch (MIT) — https://github.com/karpathy/autoresearch
"""Base runner interface for autoresearch optimization loops."""

from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable

# The engine for a loop is chosen once at the experiment boundary
# (``StartExperimentRequest.engine``) and threaded into the runner via
# ``bind_engine`` so the migrated loop-model call sites route on the bound
# selection instead of re-reading ``settings.agentic_core`` at each of the 14
# sites (master plan §8 W6). Both values route through AgenticDispatcher and
# Pi Model Management; the choice changes loop semantics, not model authority.
AUTORESEARCH_ENGINES = ("pi", "legacy")


def normalize_engine(engine: str | None) -> str:
    """Validate an explicit engine selection, returning ``pi`` or ``legacy``.

    Raises ``ValueError`` for any value outside the supported set so an invalid
    selection fails closed at the experiment boundary instead of silently
    falling back to a default.
    """
    value = str(engine or "").strip().lower()
    if value not in AUTORESEARCH_ENGINES:
        raise ValueError(
            f"engine must be one of {AUTORESEARCH_ENGINES}; got {engine!r}"
        )
    return value


def resolve_engine(engine: str | None) -> str:
    """Resolve the effective engine, defaulting an unset value from settings.

    An explicit value is validated (``pi``|``legacy``); an empty/``None`` value
    falls back to the global ``agentic_core`` flag (``pi`` when enabled, else
    ``legacy``) so callers that do not select an engine keep prior behavior.
    """
    if str(engine or "").strip():
        return normalize_engine(engine)
    from app.config import settings

    return "pi" if getattr(settings, "agentic_core", False) else "legacy"


class BaseLoopRunner(ABC):
    """Abstract base for all autoresearch loop runners."""

    loop_type: str = ""  # Override in subclass
    needs_persona_lock: bool = False  # True for loops that modify persona files
    _active_project_id: str = ""
    # Per-experiment engine ("pi"|"legacy"); "" until ``bind_engine`` runs, in
    # which case ``use_pi_engine`` resolves lazily from the global flag.
    _engine: str = ""

    def bind_project(self, project_id: str) -> None:
        """Bind runner work to the project that authorized the experiment."""
        self._active_project_id = str(project_id or "").strip()

    def require_project_id(self) -> str:
        """Return the bound project id, failing closed if the engine skipped binding."""
        if not self._active_project_id:
            raise RuntimeError("project_id is required for autoresearch runner")
        return self._active_project_id

    def bind_engine(self, engine: str | None) -> None:
        """Bind the per-experiment engine selection (``pi``|``legacy``).

        The engine loop calls this once before any model call so every migrated
        call site routes on the experiment's own selection rather than the
        global feature flag.
        """
        self._engine = resolve_engine(engine)

    @property
    def engine(self) -> str:
        """Effective engine for this run, resolving lazily when unbound."""
        return self._engine or resolve_engine(None)

    def use_pi_engine(self) -> bool:
        """True when this run routes model calls through the Pi AgenticDispatcher."""
        return self.engine == "pi"

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
