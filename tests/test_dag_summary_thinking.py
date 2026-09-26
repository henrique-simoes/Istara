"""Context-DAG summaries must not be eaten by a model's hidden reasoning (G2, 2026-09-26).

Live lane: all 50 compaction calls on a reasoning model stopped at the 300-token cap with no
visible text, and each batch silently became the mechanical "topics" line, so the summaries recalled
none of the planted facts. Summaries now run with thinking off, and an empty answer is logged with
its stop reason instead of disappearing into the fallback."""

from __future__ import annotations

import logging
from types import SimpleNamespace


async def test_summaries_turn_thinking_off(monkeypatch):
    from app.core.agentic import agentic
    from app.core.context_dag import ContextDAG

    seen = {}

    async def completion(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(text="P1's shop code is HX-1234.", stop_reason="stop")

    monkeypatch.setattr(agentic, "completion", completion)
    batch = [{"role": "user", "content": "P1's code HX-1234"}]
    summary = await ContextDAG()._summarize_batch(batch)
    assert summary == "P1's shop code is HX-1234."
    assert seen["params"].thinking_mode == "off"


async def test_an_empty_summary_is_logged_with_its_stop_reason(monkeypatch, caplog):
    from app.core.agentic import agentic
    from app.core.context_dag import ContextDAG

    async def completion(**kwargs):
        return SimpleNamespace(text="", stop_reason="length")

    monkeypatch.setattr(agentic, "completion", completion)
    with caplog.at_level(logging.WARNING, logger="app.core.context_dag"):
        summary = await ContextDAG()._summarize_batch([{"role": "user", "content": "hello"}])
    assert summary.startswith("[Fallback summary")
    assert any("stop_reason=length" in r.getMessage() for r in caplog.records)
