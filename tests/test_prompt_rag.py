"""Focused Prompt-RAG budget regressions."""

import pytest


def _estimate_tokens(text: str) -> int:
    return len(text) // 4


@pytest.mark.asyncio
async def test_prompt_rag_small_budget_preserves_identity_notice_and_content():
    from app.core.prompt_rag import (
        PROMPT_RAG_SPINE_NOTICE,
        _extract_identity_anchor,
        compose_dynamic_prompt,
    )

    budget = 512
    anchor = _extract_identity_anchor("istara-main")
    composed = await compose_dynamic_prompt(
        "istara-main",
        query="Help me with research",
        max_tokens=budget,
        use_embeddings=False,
    )

    assert _estimate_tokens(composed) <= budget
    assert anchor[:100] in composed[:200]
    assert PROMPT_RAG_SPINE_NOTICE in composed
    assert "## " in composed[len(PROMPT_RAG_SPINE_NOTICE) :]


def test_keyword_prompt_small_budget_respects_budget_and_identity():
    from app.core.prompt_rag import (
        PROMPT_RAG_SPINE_NOTICE,
        _extract_identity_anchor,
        compose_keyword_prompt,
    )

    budget = 512
    anchor = _extract_identity_anchor("istara-main")
    composed = compose_keyword_prompt(
        "istara-main",
        query="Help me with research",
        max_tokens=budget,
    )

    assert _estimate_tokens(composed) <= budget
    assert anchor[:100] in composed[:200]
    assert PROMPT_RAG_SPINE_NOTICE in composed
    assert "## " in composed[len(PROMPT_RAG_SPINE_NOTICE) :]
