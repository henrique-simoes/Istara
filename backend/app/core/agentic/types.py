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
    # ── W2 interactive-surface knobs (legacy executor only; the Pi engine
    # streams natively and always uses native tools, so it ignores these) ──
    # Stream each provider chunk through stream_cb as it arrives (per-token SSE)
    # instead of collecting the turn and emitting one terminal content event.
    stream_tokens: bool = False
    # Forwarded to the legacy stream transport (pinned-model candidate probes).
    strict_model_routing: bool | None = None
    # Regex-parsed tool calls without a tools= payload (models without native
    # function-calling support). The legacy-only fallback loop; Pi never uses it.
    text_fallback: bool = False
    # User-message suffix appended after a text-fallback tool result.
    text_fallback_followup: str | None = None
    # Text-fallback only: when the turn budget ends with a pending tool call,
    # emit nothing for the raw tail and flag the outcome instead (the caller
    # renders its own fallback answer).
    suppress_budget_exhausted_text: bool = False
    # Native streaming only: mine user-visible text from hallucinated tool-call
    # arguments ({"text"/"content"/"response": ...}) instead of dropping it.
    hallucination_text_extract: bool = True
    # Strip the final text before emitting/persisting it, and skip empty finals.
    final_text_strip: bool = False
    # Callable text -> (tool_call|None, text_before, text_after) used by the
    # text-fallback loop; None selects the executor's built-in extractor.
    tool_call_extractor: Any = None


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
