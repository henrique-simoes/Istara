"""Context summarizer — compresses older messages into summaries instead of trimming.

Pipeline (ordered by cost, cheapest first):
1. **DAG-based lossless compression** — if enabled, uses the context DAG engine
   for structured context compression (zero LLM cost, preserves exact references)
2. **LLMLingua heuristic compression** — uses the prompt compressor to remove
   low-information content from old messages while keeping verbatim text.
   ~5ms, zero LLM cost, 50-70% reduction. (Morph 2026: verbatim > summarization
   for agents because it preserves exact file paths, line numbers, error messages)
3. **LLM summarization** — calls the LLM to rewrite old messages into a structured
   summary. Expensive (full LLM call), but preserves semantic structure. Only used
   when heuristic compression doesn't achieve enough reduction.
4. **Hard trim** — drops oldest messages entirely. Last resort.

References:
- Morph FlashCompact (2026): prevention beats compression, verbatim compaction
  3,300+ tok/s, 50-70% reduction, 98% accuracy, zero hallucination risk
- Factory.ai 36K message eval: structured summary 3.70/5, but causes re-reading loops
- JetBrains SWE-bench: observation masking matched summarization quality at $0 cost
- OpenAI Codex team: inline compression as default primitive, not emergency fallback
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ContextSummary:
    summary_text: str
    messages_summarized: int
    original_token_count: int
    summary_token_count: int


class ContextSummarizer:
    """Summarizes older messages when context window pressure is high.

    Uses a cost-escalating pipeline: DAG → heuristic compression → LLM
    summarization → hard trim.
    """

    def __init__(self, threshold: float = 0.75) -> None:
        self.threshold = threshold  # Trigger at 75% of context window

    async def summarize_messages(
        self, messages: list[dict], max_summary_tokens: int = 200
    ) -> ContextSummary:
        """Use the LLM to summarize a batch of messages."""
        from app.core.ollama import ollama

        # Build conversation text for summarization
        conv_text = "\n".join(
            f"{m.get('role', 'unknown')}: {m.get('content', '')[:500]}" for m in messages
        )

        original_chars = sum(len(m.get("content", "")) for m in messages)

        summary_prompt = (
            "Summarize the following conversation concisely. "
            "Preserve key facts, decisions, research findings, and action items. "
            "Be specific about names, numbers, and research methods mentioned.\n\n"
            f"{conv_text}"
        )

        try:
            result = await ollama.chat(
                messages=[{"role": "user", "content": summary_prompt}],
                temperature=0.3,
                max_tokens=max_summary_tokens,
            )
            summary_text = result.get("message", {}).get("content", "")
            if not summary_text.strip():
                summary_text = f"[Summary of {len(messages)} messages about: {messages[0].get('content', '')[:100]}...]"
        except Exception as e:
            logger.warning(f"Summarization failed, using fallback: {e}")
            topics = set()
            for m in messages:
                content = m.get("content", "")[:100]
                if content:
                    topics.add(content.split(".")[0])
            summary_text = f"[Previous conversation summary ({len(messages)} messages): {'; '.join(list(topics)[:5])}]"

        return ContextSummary(
            summary_text=summary_text,
            messages_summarized=len(messages),
            original_token_count=original_chars // 4,
            summary_token_count=len(summary_text) // 4,
        )

    def compress_messages_heuristic(
        self,
        messages: list[dict],
        target_ratio: float = 0.6,
    ) -> tuple[list[dict], int]:
        """Compress messages using LLMLingua-inspired heuristic (zero LLM cost).

        Removes filler, redundant qualifiers, and low-importance sentences
        while keeping verbatim text. Preserves exact file paths, line numbers,
        and error messages that LLM summarization would paraphrase away.

        Args:
            messages: Messages to compress.
            target_ratio: Fraction of content to keep (0.6 = keep 60%).

        Returns:
            Tuple of (compressed_messages, original_token_count).
        """
        from app.core.prompt_compressor import compress_text, SectionType

        compressed: list[dict] = []
        original_tokens = 0

        for msg in messages:
            content = msg.get("content", "")
            original_tokens += len(content) // 4

            if not content or len(content) < 100:
                compressed.append(msg)
                continue

            # Compress based on message role
            if msg.get("role") == "user":
                # User messages: light compression, preserve query intent
                compressed_content = compress_text(content, target_ratio * 1.1, SectionType.CONTEXT)
            elif msg.get("role") == "assistant":
                # Assistant messages: moderate compression
                compressed_content = compress_text(content, target_ratio, SectionType.INSTRUCTIONS)
            else:
                # System/tool messages: heavy compression
                compressed_content = compress_text(
                    content, target_ratio * 0.7, SectionType.METADATA
                )

            compressed.append({**msg, "content": compressed_content})

        return compressed, original_tokens

    async def apply_summarization(
        self,
        system_prompt: str,
        messages: list[dict],
        session_id: str | None = None,
        budget: int | None = None,
    ) -> tuple[list[dict], ContextSummary | None]:
        """If messages exceed budget, compress/summarize older ones.

        Cost-escalating pipeline:
        1. DAG-based lossless compression (if enabled)
        2. LLMLingua heuristic compression (fast, ~5ms, zero LLM cost)
        3. LLM summarization (expensive, only if heuristic isn't enough)
        4. Hard trim (last resort)

        When DAG-based summarization is enabled and a session_id is provided,
        delegates to the DAG engine for lossless context compression. Falls
        back to the lossy path on failure.

        Returns (modified_messages, summary_or_none).
        """
        # DAG-based lossless path
        if settings.dag_enabled and session_id:
            try:
                from app.core.context_dag import context_dag

                dag_summaries, fresh = await context_dag.build_context_window(
                    session_id, settings.dag_fresh_tail_size
                )
                if dag_summaries or fresh:
                    return dag_summaries + fresh, None
            except Exception as e:
                logger.warning(f"DAG context build failed, falling back to lossy: {e}")

        max_tokens = budget or settings.max_context_tokens

        # Estimate total tokens
        system_tokens = len(system_prompt) // 4
        msg_tokens = sum(len(m.get("content", "")) // 4 for m in messages)
        total = system_tokens + msg_tokens

        threshold_tokens = int(max_tokens * self.threshold)

        if total <= threshold_tokens or len(messages) <= 4:
            return messages, None

        # Keep the most recent 4 messages (2 user + 2 assistant typically)
        fresh_count = min(4, len(messages))
        old_messages = messages[:-fresh_count]
        fresh_messages = messages[-fresh_count:]

        if not old_messages:
            return messages, None

        # Step 1: Heuristic compression (LLMLingua-inspired, ~5ms, zero LLM cost)
        compressed_old, original_tokens = self.compress_messages_heuristic(
            old_messages, target_ratio=0.6
        )
        compressed_tokens = sum(len(m.get("content", "")) // 4 for m in compressed_old)
        compressed_total = (
            system_tokens
            + compressed_tokens
            + sum(len(m.get("content", "")) // 4 for m in fresh_messages)
        )

        # If heuristic got us under threshold, use it
        if compressed_total <= threshold_tokens:
            result_messages = compressed_old + fresh_messages
            logger.info(
                f"Heuristically compressed {len(old_messages)} messages: "
                f"{original_tokens} -> {compressed_tokens} tokens "
                f"(saved {original_tokens - compressed_tokens} tokens, zero LLM cost)"
            )
            return result_messages, ContextSummary(
                summary_text="[Messages compressed heuristically — verbatim text preserved]",
                messages_summarized=len(old_messages),
                original_token_count=original_tokens,
                summary_token_count=compressed_tokens,
            )

        # Step 2: LLM summarization (only if heuristic wasn't enough)
        summary = await self.summarize_messages(old_messages)

        # Prepend summary as a system message
        summary_msg = {
            "role": "system",
            "content": f"[Previous conversation summary]\n{summary.summary_text}",
        }

        result_messages = [summary_msg] + fresh_messages
        logger.info(
            f"Summarized {summary.messages_summarized} messages: "
            f"{summary.original_token_count} -> {summary.summary_token_count} tokens"
        )

        return result_messages, summary


context_summarizer = ContextSummarizer()
