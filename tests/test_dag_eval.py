"""G2 context-DAG recall harness (DEC-2): conversations plant facts outside the fresh tail, the DAG
compacts them, and each arm is scored on exact-value recall. A stub model stands in for the live
one: it summarises nothing (so summaries lose the codes) and answers with any code it can see."""

from __future__ import annotations

import re
from types import SimpleNamespace

from app.evals import dag_eval


def test_planted_facts_sit_outside_the_fresh_tail_and_are_unique():
    turns, planted = dag_eval.build_conversation(seed=7, messages=120, facts=5, tail=32)
    assert len(turns) == 120 and len(planted) == 5
    assert all(p["turn"] < 120 - 32 for p in planted)
    assert len({p["participant"] for p in planted}) == 5
    for p in planted:
        assert p["code"] in turns[p["turn"]]["content"]


async def test_recall_arms_score_what_each_context_can_see(monkeypatch):
    from app.core.agentic import agentic
    from app.models.database import init_db

    await init_db()

    async def completion(*, purpose, messages, **kwargs):
        if purpose == "dag_compaction":
            return SimpleNamespace(text="A conversation about invoices and receipts.")
        question = messages[-1]["content"]
        who = re.search(r"participant (P\d+)'s", question).group(1)
        seen = "\n".join(m["content"] for m in messages[:-1])
        match = re.search(rf"participant {who}'s shop code is (HX-\d+)", seen)
        return SimpleNamespace(text=match.group(1) if match else "I do not know.")

    monkeypatch.setattr(agentic, "completion", completion)
    result = await dag_eval.run_conversation(seed=3, endpoint="stub", messages=120)
    assert result["dag"]["nodes"] >= 2 and result["dag"]["fallback_summaries"] == 0
    assert result["hits"]["full"] == 10
    assert result["hits"]["recall"] == 10
    assert result["hits"]["summaries"] == 0
