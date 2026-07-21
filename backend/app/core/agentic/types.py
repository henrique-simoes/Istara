"""Small, transport-neutral contracts for the AgenticDispatcher."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

EngineChoice = Literal["pi", "legacy"]


@dataclass(frozen=True)
class TurnParams:
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    thinking_mode: str | None = None
    min_context: int = 0
    timeout_s: float | None = None
    max_turns: int | None = None
    require_vision: bool = False
    # Exact Pi endpoint pin (benchmark/A2A envelopes). None leaves admission to
    # the PiModelManager capability/model filters.
    endpoint_id: str | None = None


@dataclass(frozen=True)
class TurnResult:
    text: str
    usage: dict[str, Any] = field(default_factory=dict)
    stop_reason: str | None = None
    endpoint_id: str | None = None
    status: str = "success"
    tool_calls: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class StructuredResult(TurnResult):
    value: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EnsembleResult:
    """N sampled turns (distinct endpoints or self-MoA on one endpoint)."""

    samples: list[TurnResult] = field(default_factory=list)
    endpoint_ids: list[str] = field(default_factory=list)
    usage: dict[str, Any] = field(default_factory=dict)
    status: str = "success"


class AgenticDispatchError(RuntimeError):
    """A selected engine could not execute; callers must not silently switch."""
