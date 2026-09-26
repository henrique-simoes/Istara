"""G2 · Context-DAG recall (plan `2026-09-26-graph-quality-measurement.md`, DEC-2).

Long synthetic research conversations carry planted facts ("participant P7's shop code is HX-4471")
at known turns. The Context DAG compacts everything outside the fresh tail into summary nodes. Each
planted fact is then asked about in three arms:

* ``summaries`` — what a chat turn sees: the DAG's top summaries plus the fresh tail;
* ``recall`` — the same plus ``grep_history`` results for the participant, as the agent's recall
  tool would return them;
* ``full`` — the whole uncompacted history (the ceiling).

The score is exact-value recall: the planted code appears in the answer. The report also counts
summaries that fell back to the mechanical "topics" line (a silent loss of every fact in that
batch) and the DAG's depth. Synthetic data only; one project and one session per conversation.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from app.evals.graph_eval import _share

FILLER = [
    "We talked about how invoices get chased on Fridays and why calls work better than email.",
    "The owner described receipts ending up in an apron pocket, then the van, then the laundry.",
    "Payroll lands Thursday and client money on Friday, so the account runs short overnight.",
    "Two signatures are needed above five hundred dollars, which stalls purchases for days.",
    "The auto-match is right most of the time, and the rest gets fixed with coffee.",
    "The Spanish statement uses a different term for the overdraft transfer fee.",
    "Customers start online and finish at the branch, repeating everything they already did.",
    "Most fraud alerts are noise; forty were cleared before lunch on a quiet Tuesday.",
    "Every month the owner exports PDFs and screenshots for the accountant to puzzle over.",
    "A good month hit the mobile deposit limit and a check bounced back as rejected.",
]


def build_conversation(seed: int, messages: int = 300, facts: int = 10, tail: int = 32):
    """(turns, planted) — planted facts sit outside the fresh tail, one per participant."""
    rng = random.Random(seed)
    turns = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": rng.choice(FILLER)}
        for i in range(messages)
    ]
    slots = rng.sample(range(0, messages - tail, 2), facts)
    planted = []
    for n, slot in enumerate(sorted(slots), 1):
        code = f"HX-{rng.randint(1000, 9999)}"
        turns[slot]["content"] = (
            f"For the record, participant P{n}'s shop code is {code}. {turns[slot]['content']}"
        )
        planted.append({"participant": f"P{n}", "code": code, "turn": slot})
    return turns, planted


async def _store(turns: list[dict], seed: int) -> str:
    from app.models.database import async_session
    from app.models.message import Message
    from app.models.project import Project
    from app.models.session import ChatSession

    project_id, session_id = str(uuid.uuid4()), str(uuid.uuid4())
    start = datetime.now(UTC) - timedelta(hours=len(turns))
    async with async_session() as db:
        db.add(Project(id=project_id, name=f"[G2] DAG recall {seed} (synthetic)"))
        db.add(ChatSession(id=session_id, project_id=project_id, title=f"G2 {seed}"))
        for i, turn in enumerate(turns):
            db.add(
                Message(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    session_id=session_id,
                    role=turn["role"],
                    content=turn["content"],
                    created_at=start + timedelta(minutes=i),
                )
            )
        await db.commit()
    return session_id


async def _compact(session_id: str) -> dict[str, Any]:
    from app.core.context_dag import context_dag

    await context_dag.compact_if_needed(session_id)
    await context_dag.drain_compaction_tasks()
    structure = await context_dag.get_dag_structure(session_id)
    nodes = structure.get("nodes") or []
    fallbacks = sum(1 for n in nodes if str(n.get("summary_text", "")).startswith("[Fallback"))
    depth = max((int(n.get("depth", 0)) for n in nodes), default=-1)
    return {"nodes": len(nodes), "fallback_summaries": fallbacks, "max_depth": depth}


async def _arm_messages(session_id: str, arm: str, participant: str, turns: list[dict]):
    from app.core.context_dag import context_dag

    if arm == "full":
        return list(turns)
    summaries, tail = await context_dag.build_context_window(session_id)
    context = summaries + tail
    if arm == "recall":
        hits = await context_dag.grep_history(session_id, participant)
        found = "\n".join(str(h.get("content_excerpt") or "") for h in hits)
        header = f"[recall: grep_history {participant}]"
        context.append({"role": "system", "content": f"{header}\n{found}"})
    return context


async def _ask(messages: list[dict], question: str, endpoint: str) -> str:
    from app.core.agentic import agentic
    from app.core.agentic.types import TurnParams

    outcome = await agentic.completion(
        purpose="eval.dag_recall",
        project_id="",
        system="Answer from the conversation only. If it is not there, say you do not know.",
        messages=[*messages, {"role": "user", "content": question}],
        params=TurnParams(endpoint_id=endpoint, temperature=0.0, max_tokens=200),
    )
    return outcome.text or ""


async def run_conversation(seed: int, endpoint: str, messages: int) -> dict[str, Any]:
    turns, planted = build_conversation(seed, messages)
    session_id = await _store(turns, seed)
    dag = await _compact(session_id)
    scores: dict[str, list[bool]] = {"summaries": [], "recall": [], "full": []}
    for fact in planted:
        question = f"What is participant {fact['participant']}'s shop code?"
        for arm in scores:
            context = await _arm_messages(session_id, arm, fact["participant"], turns)
            answer = await _ask(context, question, endpoint)
            scores[arm].append(fact["code"] in answer)
    hits = {arm: sum(v) for arm, v in scores.items()}
    return {"seed": seed, "dag": dag, "hits": hits, "flags": scores}


async def run(seeds: list[int], endpoint: str, messages: int) -> dict[str, Any]:
    conversations = [await run_conversation(s, endpoint, messages) for s in seeds]
    pooled = {
        arm: [flag for c in conversations for flag in c["flags"][arm]]
        for arm in ("summaries", "recall", "full")
    }
    return {
        "measurement": "G2 context-DAG recall",
        "answer_endpoint": endpoint,
        "messages_per_conversation": messages,
        "recall": {arm: _share(flags) for arm, flags in pooled.items()},
        "fallback_summaries": sum(c["dag"]["fallback_summaries"] for c in conversations),
        "dag_nodes": sum(c["dag"]["nodes"] for c in conversations),
        "max_depth": max(c["dag"]["max_depth"] for c in conversations),
        "conversations": [{k: v for k, v in c.items() if k != "flags"} for c in conversations],
    }


async def _run_and_stop_worker(**kwargs: Any) -> dict:
    try:
        return await run(**kwargs)
    finally:
        from app.core import pi_runtime

        await pi_runtime.shutdown_supervisor()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--endpoint", required=True, help="Pi endpoint that answers the questions")
    parser.add_argument("--seeds", default="1,2,3,4,5")
    parser.add_argument("--messages", type=int, default=300)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    from app.models.database import register_models

    register_models()
    seeds = [int(s) for s in args.seeds.split(",") if s]
    report = asyncio.run(
        _run_and_stop_worker(seeds=seeds, endpoint=args.endpoint, messages=args.messages)
    )
    text = json.dumps(report, indent=1, default=str)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text if not args.out else f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
