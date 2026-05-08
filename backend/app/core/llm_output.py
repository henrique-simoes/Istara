"""Provider-neutral LLM output normalization.

Different OpenAI-compatible servers expose reasoning in different places:
OpenAI keeps raw reasoning out of visible text, Gemini and Anthropic use
separate thought/thinking blocks when enabled, and local servers may emit
``reasoning_content`` fields or inline thinking blocks such as Qwen's
``<think>...</think>`` and Gemma's thought channel tokens.

This module returns only user-visible final answer text.
"""

from __future__ import annotations

import json
from typing import Any


THINK_OPEN = "<think>"
THINK_CLOSE = "</think>"
GEMMA_THOUGHT_OPEN = "<|channel>thought"
GEMMA_THOUGHT_CLOSE = "<channel|>"
_THINKING_BLOCKS = (
    (THINK_OPEN, THINK_CLOSE),
    (GEMMA_THOUGHT_OPEN, GEMMA_THOUGHT_CLOSE),
)
_VISIBLE_CONTROL_TOKENS = (
    "<|think|>",
    "<turn|>",
    "<end_of_turn>",
    "<bos>",
    "<eos>",
)
_STREAM_SUPPRESSED_TOKENS = (
    *(open_token for open_token, _ in _THINKING_BLOCKS),
    *_VISIBLE_CONTROL_TOKENS,
)
_THINKING_CLOSE_TOKENS = tuple(close_token for _, close_token in _THINKING_BLOCKS)

_NON_VISIBLE_CONTENT_TYPES = {
    "thinking",
    "redacted_thinking",
    "reasoning",
    "reasoning_content",
    "thought",
    "thought_signature",
}
_NON_VISIBLE_MESSAGE_KEYS = _NON_VISIBLE_CONTENT_TYPES | {"thoughtSignature"}


def _longest_token_prefix_suffix(text: str, tokens: tuple[str, ...]) -> int:
    """Return how much of a suppressed token is dangling at text end."""
    max_len = min(max(len(token) for token in tokens) - 1, len(text))
    for size in range(max_len, 0, -1):
        if any(text.endswith(token[:size]) for token in tokens):
            return size
    return 0


def _first_thinking_open(text: str, index: int) -> tuple[int, str, str] | None:
    found: tuple[int, str, str] | None = None
    for open_token, close_token in _THINKING_BLOCKS:
        start = text.find(open_token, index)
        if start == -1:
            continue
        if found is None or start < found[0]:
            found = (start, open_token, close_token)
    return found


def _strip_visible_control_tokens(text: str) -> str:
    for token in _VISIBLE_CONTROL_TOKENS:
        text = text.replace(token, "")
    return text


def strip_thinking_blocks(text: str) -> str:
    """Remove inline thinking blocks from visible output."""
    if not text:
        return text or ""
    if not any(open_token in text for open_token, _ in _THINKING_BLOCKS):
        return _strip_visible_control_tokens(text)

    result: list[str] = []
    index = 0
    while index < len(text):
        found = _first_thinking_open(text, index)
        if found is None:
            result.append(text[index:])
            break
        start, open_token, close_token = found
        result.append(text[index:start])
        end = text.find(close_token, start + len(open_token))
        if end == -1:
            break
        index = end + len(close_token)
        while index < len(text) and text[index] in " \t\r\n":
            index += 1
    return _strip_visible_control_tokens("".join(result))


def _content_to_visible_text(content: Any) -> str:
    """Extract visible text from provider content payloads."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        block_type = str(content.get("type") or "").lower()
        if block_type in _NON_VISIBLE_CONTENT_TYPES:
            return ""
        if content.get("thought") is True or content.get("thinking") is True:
            return ""
        if block_type in {"text", "output_text", "input_text"}:
            text = content.get("text")
            if text is None:
                text = content.get("content")
            return _content_to_visible_text(text)
        return json.dumps(content, ensure_ascii=False)
    if not isinstance(content, list):
        return str(content)

    visible: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            visible.append(_content_to_visible_text(block))
            continue
        block_type = str(block.get("type") or "").lower()
        if block_type in _NON_VISIBLE_CONTENT_TYPES:
            continue
        if block.get("thought") is True or block.get("thinking") is True:
            continue
        if block_type in {"text", "output_text", "input_text", ""}:
            text = block.get("text")
            if text is None:
                text = block.get("content")
            if text:
                visible.append(_content_to_visible_text(text))
            elif block_type == "" and not any(key in block for key in ("text", "content")):
                visible.append(json.dumps(block, ensure_ascii=False))
    return "".join(visible)


def visible_assistant_content(message: dict[str, Any] | None) -> str:
    """Return final-answer content only, never raw reasoning/thinking text."""
    if not isinstance(message, dict):
        return ""
    content = _content_to_visible_text(message.get("content"))
    if not content.strip() and "parsed" in message:
        content = _content_to_visible_text(message.get("parsed"))
    return strip_thinking_blocks(content).strip()


def visible_assistant_message(message: dict[str, Any] | None) -> dict[str, Any]:
    """Return an assistant message with non-visible reasoning fields removed."""
    normalized = dict(message) if isinstance(message, dict) else {}
    normalized["role"] = normalized.get("role") or "assistant"
    normalized["content"] = visible_assistant_content(message)
    for key in _NON_VISIBLE_MESSAGE_KEYS:
        normalized.pop(key, None)
    return normalized


class ThinkingContentFilter:
    """Streaming filter that suppresses inline ``<think>...</think>`` blocks."""

    def __init__(self) -> None:
        self._in_thinking = False
        self._thinking_close = ""
        self._pending = ""
        self._suppress_leading_space = False

    def push(self, chunk: str | None) -> str:
        """Return the visible portion of a streamed chunk."""
        if not chunk:
            return ""
        text = self._pending + chunk
        self._pending = ""
        output: list[str] = []
        index = 0

        while index < len(text):
            if self._in_thinking:
                end = text.find(self._thinking_close, index)
                if end == -1:
                    hold = _longest_token_prefix_suffix(text[index:], (self._thinking_close,))
                    if hold:
                        self._pending = text[-hold:]
                    return ""
                index = end + len(self._thinking_close)
                self._in_thinking = False
                self._thinking_close = ""
                self._suppress_leading_space = True
                continue

            if self._suppress_leading_space:
                while index < len(text) and text[index] in " \t\r\n":
                    index += 1
                self._suppress_leading_space = False
                if index >= len(text):
                    break

            found = _first_thinking_open(text, index)
            if found is None:
                visible = text[index:]
                hold = _longest_token_prefix_suffix(visible, _STREAM_SUPPRESSED_TOKENS)
                if hold:
                    self._pending = visible[-hold:]
                    visible = visible[:-hold]
                output.append(_strip_visible_control_tokens(visible))
                break

            start, open_token, close_token = found
            output.append(text[index:start])
            index = start + len(open_token)
            self._in_thinking = True
            self._thinking_close = close_token

        return _strip_visible_control_tokens("".join(output))

    def flush(self) -> str:
        """Flush pending non-thinking text at stream end."""
        pending = self._pending
        self._pending = ""
        if self._in_thinking:
            return ""
        if any(token.startswith(pending) for token in _STREAM_SUPPRESSED_TOKENS):
            return ""
        return _strip_visible_control_tokens(pending)
