"""G2: a DAG summary keeps exact identifiers, codes and amounts (2026-09-27).

Half of the planted participant codes were paraphrased away by 300-token summaries; the summary now
ends with an 'Exact details' line copying them verbatim, with room for it.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest


@pytest.mark.asyncio
async def test_summary_prompt_asks_for_exact_details_with_room(monkeypatch):
    from app.config import settings
    from app.core.context_dag import context_dag

    seen = {}

    class _Agentic:
        async def completion(self, **kwargs):  # noqa: ANN003
            seen["prompt"] = kwargs["messages"][-1]["content"]
            seen["max_tokens"] = kwargs["params"].max_tokens
            return SimpleNamespace(text="summary\nExact details: P7 shop code: HX-4471")

    monkeypatch.setattr("app.core.agentic.agentic", _Agentic())
    out = await context_dag._summarize_batch(
        [{"role": "user", "content": "By the way, P7's shop code is HX-4471.", "created_at": ""}]
    )
    assert "Exact details:" in seen["prompt"] and "character for character" in seen["prompt"]
    assert seen["max_tokens"] == settings.dag_summary_max_tokens >= 500
    assert "HX-4471" in out
