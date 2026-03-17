"""Token counting and context window management.

Fills audit gap #3: Context Window Management. Prevents prompt overflow
when composing system prompts, RAG context, and chat history for local
LLMs (LM Studio / Ollama) that have finite context windows.

Uses a character-based heuristic (chars / 4) rather than a real
tokenizer — fast, zero external dependencies, accurate enough for
guard-rail purposes on models like Qwen, Llama, Mistral, etc.
"""

import logging
from dataclasses import dataclass

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Core counting helpers
# ---------------------------------------------------------------------------

# Average chars-per-token across common LLM tokenizers (GPT, Llama, Qwen).
# 4 is a widely-used conservative estimate; slightly overestimates token
# count, which is the safe direction for budget enforcement.
_CHARS_PER_TOKEN = 4

# Per-message overhead: every chat message carries role + formatting tokens.
# OpenAI-compatible APIs typically add ~4 tokens of framing per message.
_MESSAGE_OVERHEAD_TOKENS = 4

# Reply buffer — reserve tokens for the model's own response.
_REPLY_RESERVE_TOKENS = 512


def count_tokens(text: str) -> int:
    """Estimate the token count of a string using a character heuristic.

    Args:
        text: Input text.

    Returns:
        Estimated token count (always >= 0).
    """
    if not text:
        return 0
    return max(1, len(text) // _CHARS_PER_TOKEN)


def estimate_messages_tokens(messages: list[dict]) -> int:
    """Estimate total tokens for a list of chat messages.

    Each message is expected to have ``role`` and ``content`` keys
    (the OpenAI chat-completion format used by LM Studio / Ollama).

    Args:
        messages: List of ``{"role": ..., "content": ...}`` dicts.

    Returns:
        Estimated total token count across all messages.
    """
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        total += count_tokens(content) + _MESSAGE_OVERHEAD_TOKENS
    return total


# ---------------------------------------------------------------------------
# ContextWindowGuard
# ---------------------------------------------------------------------------

@dataclass
class TokenBudgetReport:
    """Result of a context-window budget check."""

    fits: bool
    total_tokens: int
    max_tokens: int
    system_tokens: int
    messages_tokens: int
    available_for_reply: int


class ContextWindowGuard:
    """Enforces context-window limits for chat completions.

    Typical usage::

        guard = ContextWindowGuard()
        fits, total = guard.check(system_prompt, messages)
        if not fits:
            messages = guard.trim_messages(system_prompt, messages)
    """

    def __init__(self, max_tokens: int | None = None) -> None:
        self.max_tokens = max_tokens or settings.max_context_tokens

    # -- Public API --------------------------------------------------------

    def check(
        self, system_prompt: str, messages: list[dict]
    ) -> tuple[bool, int]:
        """Check whether the prompt + messages fit within the context window.

        Args:
            system_prompt: The composed system prompt.
            messages: Chat message list.

        Returns:
            Tuple of (fits_within_window, estimated_total_tokens).
        """
        sys_tokens = count_tokens(system_prompt) + _MESSAGE_OVERHEAD_TOKENS
        msg_tokens = estimate_messages_tokens(messages)
        total = sys_tokens + msg_tokens + _REPLY_RESERVE_TOKENS
        fits = total <= self.max_tokens
        return fits, total

    def budget_report(
        self, system_prompt: str, messages: list[dict]
    ) -> TokenBudgetReport:
        """Return a detailed breakdown of token budget usage."""
        sys_tokens = count_tokens(system_prompt) + _MESSAGE_OVERHEAD_TOKENS
        msg_tokens = estimate_messages_tokens(messages)
        total = sys_tokens + msg_tokens + _REPLY_RESERVE_TOKENS
        return TokenBudgetReport(
            fits=total <= self.max_tokens,
            total_tokens=total,
            max_tokens=self.max_tokens,
            system_tokens=sys_tokens,
            messages_tokens=msg_tokens,
            available_for_reply=max(0, self.max_tokens - sys_tokens - msg_tokens),
        )

    def trim_messages(
        self,
        system_prompt: str,
        messages: list[dict],
        max_tokens: int | None = None,
    ) -> list[dict]:
        """Trim the oldest messages so the conversation fits the window.

        The most recent message (usually the current user turn) is always
        kept.  Older messages are dropped from the front until the total
        fits.  If *max_tokens* is ``None``, ``self.max_tokens`` is used.

        Args:
            system_prompt: The composed system prompt.
            messages: Chat message list (will **not** be mutated).
            max_tokens: Override for the context-window limit.

        Returns:
            A new message list that fits within the budget.
        """
        budget = max_tokens or self.max_tokens
        sys_tokens = count_tokens(system_prompt) + _MESSAGE_OVERHEAD_TOKENS
        available = budget - sys_tokens - _REPLY_RESERVE_TOKENS

        if available <= 0:
            # System prompt alone blows the budget — keep only the last msg
            logger.warning(
                "System prompt (%d tokens) exceeds context budget (%d). "
                "Only the latest message will be kept.",
                sys_tokens,
                budget,
            )
            return messages[-1:] if messages else []

        # Walk backwards, accumulating messages until we run out of room
        kept: list[dict] = []
        running = 0
        for msg in reversed(messages):
            msg_tokens = count_tokens(msg.get("content", "")) + _MESSAGE_OVERHEAD_TOKENS
            if running + msg_tokens > available:
                break
            kept.append(msg)
            running += msg_tokens

        kept.reverse()

        trimmed_count = len(messages) - len(kept)
        if trimmed_count > 0:
            logger.info(
                "Trimmed %d oldest message(s) to fit context window "
                "(%d / %d tokens used).",
                trimmed_count,
                sys_tokens + running + _REPLY_RESERVE_TOKENS,
                budget,
            )

        return kept

    def summarize_if_needed(
        self, system_prompt: str, messages: list[dict]
    ) -> tuple[list[dict], str | None]:
        """Trim messages and produce a plain-text summary of what was dropped.

        This is a *local* summarisation — no LLM call.  It simply notes
        which roles/counts were trimmed so the model is aware that history
        was truncated.

        Args:
            system_prompt: The composed system prompt.
            messages: Chat message list.

        Returns:
            Tuple of (trimmed_messages, summary_string_or_None).
        """
        fits, _ = self.check(system_prompt, messages)
        if fits:
            return messages, None

        trimmed = self.trim_messages(system_prompt, messages)
        dropped_count = len(messages) - len(trimmed)

        if dropped_count == 0:
            return trimmed, None

        # Build a short summary of what was removed
        dropped = messages[:dropped_count]
        user_msgs = sum(1 for m in dropped if m.get("role") == "user")
        assistant_msgs = sum(1 for m in dropped if m.get("role") == "assistant")

        parts = []
        if user_msgs:
            parts.append(f"{user_msgs} user message(s)")
        if assistant_msgs:
            parts.append(f"{assistant_msgs} assistant message(s)")

        summary = (
            f"[Context window limit reached — {dropped_count} earlier message(s) "
            f"trimmed ({', '.join(parts)}). Conversation continues from the "
            f"most recent context.]"
        )

        return trimmed, summary


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

context_guard = ContextWindowGuard()
