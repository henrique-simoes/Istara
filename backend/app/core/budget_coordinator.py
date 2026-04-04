"""Budget Coordinator — dynamic token budget allocation based on detected context window.

Instead of hardcoding 8192 tokens and fixed ratios, this module:
1. Reads the detected context window from the active LLM model
2. Allocates budgets per component (identity, RAG, history, reply, buffer)
3. Scales budgets adaptively — identity caps at ~3K even for 200K windows,
   while history gets the lion's share
4. Integrates with the resource governor to downgrade compression strategies
   when compute is constrained

Budget philosophy (industry standard 2026):
- Identity: min(context * 0.3, 3000) — caps to avoid signal dilution
- RAG: min(context * 0.05, 4000) — grows with context, more chunks with compression
- Reply reserve: max(512, context * 0.05) — allows longer outputs on big windows
- Buffer: max(0, context * 0.05) — overflow protection
- History: everything remaining — this is what users experience as "remembers more"

References:
- Liu et al. "Lost in the Middle" (2023) — accuracy drops 30% in middle of long contexts
- LongLLMLingua (ACL 2024) — question-aware compression for RAG chunks
- Morph FlashCompact (2026) — prevention beats compression, verbatim > summarization
- Factory.ai 36K message eval — structured summary 3.70/5, verbatim 98% accuracy
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Budget allocation
# ---------------------------------------------------------------------------


@dataclass
class BudgetAllocation:
    """Per-component token budget for a single LLM request."""

    identity_tokens: int  # Prompt RAG + agent identity
    rag_tokens: int  # RAG context chunks
    history_tokens: int  # Conversation history
    reply_reserve: int  # Reserved for model output
    buffer_tokens: int  # Safety overflow
    total_tokens: int  # Full context window

    @property
    def available_for_input(self) -> int:
        """Tokens available for identity + RAG + history (excludes reply + buffer)."""
        return self.identity_tokens + self.rag_tokens + self.history_tokens


class BudgetCoordinator:
    """Allocates token budgets based on the detected context window size.

    Budgets scale with context size but with caps to prevent signal dilution
    (Liu et al., 2023: bigger windows don't solve the "lost in the middle" problem).
    """

    def allocate(self, context_window: int | None = None) -> BudgetAllocation:
        """Compute per-component token budgets.

        Args:
            context_window: Detected model context length. Falls back to
                ``settings.max_context_tokens`` if not provided.

        Returns:
            BudgetAllocation with per-component token budgets.
        """
        ctx = context_window or settings.max_context_tokens

        # Identity: scales but caps at 3K — more persona detail isn't better
        # beyond a point (signal dilution in long contexts)
        identity = min(int(ctx * 0.3), 3000)

        # RAG: grows with context, caps at 4K — more retrieved chunks
        # but compressed with question-aware compression (LongLLMLingua)
        rag = min(int(ctx * 0.05), 4000)

        # Reply reserve: min 512, scales to 5% for big windows
        reply = max(512, int(ctx * 0.05))

        # Buffer: 5% overflow protection
        buffer = max(0, int(ctx * 0.05))

        # History gets everything remaining
        history = ctx - identity - rag - reply - buffer

        # Safety: history must be positive
        if history < 512:
            # Context too small — prioritize history over everything
            identity = min(identity, max(512, ctx // 4))
            rag = min(rag, max(256, ctx // 8))
            reply = max(256, ctx // 8)
            buffer = 0
            history = ctx - identity - rag - reply - buffer

        allocation = BudgetAllocation(
            identity_tokens=identity,
            rag_tokens=rag,
            history_tokens=history,
            reply_reserve=reply,
            buffer_tokens=buffer,
            total_tokens=ctx,
        )

        logger.debug(
            f"Budget allocation for {ctx}-token window: "
            f"identity={identity}, rag={rag}, history={history}, "
            f"reply={reply}, buffer={buffer}"
        )

        return allocation


# ---------------------------------------------------------------------------
# Compute surplus assessment
# ---------------------------------------------------------------------------


def compute_surplus_level() -> str:
    """Assess available compute power to choose compression strategy.

    Returns one of:
    - ``"high"``: Multiple agents + remote nodes or plenty of RAM — use full
      question-aware compression with LLM scoring
    - ``"moderate"``: Normal load — heuristic question-aware compression
    - ``"low"``: Single agent, no remote nodes — heuristic only, no question-awareness
    - ``"constrained"``: System under pressure — hard trim only, zero LLM cost

    Uses the existing ResourceGovernor and ComputePool infrastructure.
    """
    from app.core.resource_governor import governor

    budget = governor.compute_budget()

    # Constrained: system under pressure
    if budget.paused or budget.throttle_delay_ms > 0:
        return "constrained"

    # Check remote compute capacity
    remote_nodes = 0
    try:
        from app.core.compute_pool import compute_pool

        remote_nodes = compute_pool.total_capacity()
    except Exception:
        pass

    # Low: only 1 agent allowed, no remote nodes
    if budget.max_concurrent_agents <= 1 and remote_nodes == 0:
        return "low"

    # High: multiple remote nodes OR plenty of RAM with no throttling
    res = governor.get_resources()
    if remote_nodes >= 2 or (res.ram_available_gb >= 12 and budget.throttle_delay_ms == 0):
        return "high"

    return "moderate"


# ---------------------------------------------------------------------------
# Module singleton
# ---------------------------------------------------------------------------

budget_coordinator = BudgetCoordinator()
