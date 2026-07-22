"""Prompt-adherence probes (task B0-8, axis 9).

Pure text scorers, safe at T0:

* :func:`protected_block_survival` — did a protected block (spine contract, codebook,
  gate/schema block) survive downstream processing (e.g. LLMLingua compression) intact?
  Governance contract (AGENTS.md): compression is only acceptable while protected blocks
  remain intact, so this is the measurable form of that rule.
* :func:`persona_compliance` — did the response avoid forbidden persona-breaking patterns?
* :func:`thinking_leak_rate` — fraction of a response that is leaked private reasoning.
"""

from __future__ import annotations

import re

# Common markers used to fence private model reasoning that must not reach the user.
_THINKING_PATTERNS = (
    re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE),
    re.compile(r"<thinking>.*?</thinking>", re.DOTALL | re.IGNORECASE),
    re.compile(r"<reasoning>.*?</reasoning>", re.DOTALL | re.IGNORECASE),
    re.compile(r"<scratchpad>.*?</scratchpad>", re.DOTALL | re.IGNORECASE),
)


def _normalise_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def protected_block_survival(protected_block: str, processed_prompt: str) -> float:
    """Fraction of the protected block's non-empty lines still present verbatim downstream.

    1.0 means every protected line survived; 0.0 means the block was stripped. An empty
    protected block trivially survives (1.0).
    """
    protected_lines = _normalise_lines(protected_block)
    if not protected_lines:
        return 1.0
    haystack = processed_prompt
    survived = sum(1 for line in protected_lines if line in haystack)
    return survived / len(protected_lines)


def persona_compliance(response: str, forbidden_patterns: list[str]) -> float:
    """1.0 when the response contains none of the forbidden (persona-breaking) patterns.

    Score is the fraction of forbidden patterns that are ABSENT — so a single leak drops
    the score proportionally and a clean response scores 1.0. An empty forbidden list is
    trivially compliant.
    """
    if not forbidden_patterns:
        return 1.0
    lowered = response.lower()
    clean = sum(1 for pattern in forbidden_patterns if pattern.lower() not in lowered)
    return clean / len(forbidden_patterns)


def thinking_leak_rate(response: str) -> float:
    """Fraction of the response's characters that fall inside leaked reasoning fences.

    0.0 means no leaked thinking; a higher value means more of the visible output is
    private reasoning that should have been withheld.
    """
    if not response:
        return 0.0
    total = len(response)
    leaked = 0
    for pattern in _THINKING_PATTERNS:
        for match in pattern.finditer(response):
            leaked += len(match.group(0))
    # Cap at 1.0: overlapping fences can never leak more than the whole response.
    return min(1.0, leaked / total)
