"""Provider-neutral controls for model thinking behavior.

Istara treats provider "thinking" as two separate concerns:

1. Request intent: whether Istara asks the model/server to use private
   reasoning, avoid it, or keep the server default.
2. Output safety: raw reasoning is never shown as assistant text.

The request side is intentionally conservative. OpenAI-compatible local
servers differ in what extra JSON fields they accept, so we express the mode
through the system prompt and keep provider payloads free of unknown fields.
"""

from __future__ import annotations

from typing import Any, Literal

ThinkingMode = Literal["server_default", "off", "auto", "on"]

THINKING_MODES: tuple[ThinkingMode, ...] = ("server_default", "off", "auto", "on")
DEFAULT_THINKING_MODE: ThinkingMode = "server_default"

THINKING_MARKER_REGISTRY: dict[str, dict[str, Any]] = {
    "qwen": {"inline_blocks": [("<think>", "</think>")]},
    "deepseek": {"inline_blocks": [("<think>", "</think>")]},
    "gemma": {"inline_blocks": [("<|channel>thought", "<channel|>")]},
    "openai": {"structured_keys": ["reasoning", "reasoning_content"]},
    "anthropic": {"structured_types": ["thinking", "redacted_thinking"]},
    "gemini": {"structured_flags": ["thought", "thoughtSignature"]},
}

_THINKING_DIRECTIVES: dict[ThinkingMode, str] = {
    "off": (
        "Istara thinking mode is OFF. Answer directly. Do not emit chain-of-thought, "
        "hidden reasoning, scratchpads, <think> blocks, or thought-channel markup. "
        "Return only the final user-visible answer."
    ),
    "auto": (
        "Istara thinking mode is AUTO. Follow the model/server default for any "
        "private reasoning, but never reveal raw reasoning, scratchpads, <think> "
        "blocks, or thought-channel markup. Return only the final answer."
    ),
    "on": (
        "Istara thinking mode is ON. Use private reasoning internally if this "
        "model/server supports it, but never reveal raw reasoning, scratchpads, "
        "<think> blocks, or thought-channel markup. Return only the final answer."
    ),
}


def normalize_thinking_mode(value: str | None) -> ThinkingMode:
    """Normalize an untrusted thinking-mode value to Istara's contract."""
    mode = (value or DEFAULT_THINKING_MODE).strip().lower().replace("-", "_")
    if mode in THINKING_MODES:
        return mode  # type: ignore[return-value]
    return DEFAULT_THINKING_MODE


def thinking_directive(mode: str | None) -> str:
    """Return the system prompt fragment for a thinking mode."""
    return _THINKING_DIRECTIVES.get(normalize_thinking_mode(mode), "")


def apply_thinking_control(
    messages: list[dict[str, Any]],
    mode: str | None,
) -> list[dict[str, Any]]:
    """Return messages with the requested thinking directive injected once."""
    directive = thinking_directive(mode)
    if not directive:
        return list(messages)

    controlled = [dict(message) for message in messages]
    marker = "Istara thinking mode is "
    for message in controlled:
        if message.get("role") == "system" and marker in str(message.get("content", "")):
            return controlled

    if controlled and controlled[0].get("role") == "system":
        controlled[0]["content"] = f"{controlled[0].get('content', '')}\n\n{directive}"
    else:
        controlled.insert(0, {"role": "system", "content": directive})
    return controlled


def thinking_marker_registry() -> dict[str, dict[str, Any]]:
    """Expose the model-family marker registry for tests and diagnostics."""
    return {
        family: {
            key: [tuple(item) if isinstance(item, tuple) else item for item in value]
            if isinstance(value, list)
            else value
            for key, value in metadata.items()
        }
        for family, metadata in THINKING_MARKER_REGISTRY.items()
    }
