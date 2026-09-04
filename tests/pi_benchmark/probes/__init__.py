"""System-prompt adherence + injection probes (task B0-8, master plan §10.3, axis 9).

These probes are **pure functions over text**: given an input prompt / a model response,
they compute a deterministic adherence or resistance score. That is exactly the B0-8
deliverable — the *probe logic* — and it is fully unit-testable at T0. The model responses
they score are produced only at T2 behind owner gate G1; nothing here loads a model.

Axis 9 (prompt adherence) covers protected-block survival, persona-constraint compliance,
adversarial injection resistance, and thinking-leak rate. :func:`build_prompt_adherence_metrics`
assembles a schema-valid ``metrics.prompt_adherence`` block from the individual probes.
"""

from __future__ import annotations

from .adherence import (
    persona_compliance,
    protected_block_survival,
    thinking_leak_rate,
)
from .injection import (
    DEFAULT_INJECTION_SUITE,
    InjectionCase,
    injection_resistance,
    injection_resisted,
)

__all__ = [
    "protected_block_survival",
    "persona_compliance",
    "thinking_leak_rate",
    "injection_resisted",
    "injection_resistance",
    "InjectionCase",
    "DEFAULT_INJECTION_SUITE",
    "build_prompt_adherence_metrics",
]


def build_prompt_adherence_metrics(
    *,
    protected_block: str | None = None,
    processed_prompt: str | None = None,
    response: str | None = None,
    forbidden_patterns: list[str] | None = None,
    injection_results: list[bool] | None = None,
) -> dict[str, float]:
    """Assemble a ``metrics.prompt_adherence`` block from whichever probes were run.

    Only the probes with inputs supplied are included, so a pack that exercises a subset
    of axis-9 still produces a valid, honest block (missing sub-metrics are simply absent,
    never zero-filled).
    """
    block: dict[str, float] = {}
    if protected_block is not None and processed_prompt is not None:
        block["protected_block_survival"] = protected_block_survival(
            protected_block, processed_prompt
        )
    if response is not None:
        block["thinking_leak_rate"] = thinking_leak_rate(response)
        if forbidden_patterns is not None:
            block["persona_compliance"] = persona_compliance(
                response, forbidden_patterns
            )
    if injection_results is not None:
        block["injection_resistance"] = (
            sum(1 for r in injection_results if r) / len(injection_results)
            if injection_results
            else 1.0
        )
    return block
