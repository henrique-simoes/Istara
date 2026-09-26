"""RAG compression runs only under budget pressure (measurement 3 follow-up).

M3 (2026-09-25, ``python -m app.evals.retrieval_eval budget``) found budget recall 226/227 at every
context window of 16k tokens and above. The instrumented run names the loss: question T2-P1 (a
paraphrase), rank-2 chunk, step ``compression``, although the uncompressed block (3,065 characters)
fit every one of those budgets. ``compress_rag_chunks_indexed`` compressed every chunk after the
first by rank (0.85, 0.7, 0.7, 0.5) whatever the budget, and question-aware scoring removed the
participant's answer line because it shared no word with the question. Retrieval returns exact
evidence; removing it when the budget has room for it makes answers less faithful to the source
and buys nothing.

The contract pinned here: when the chunks fit the budget they reach the prompt byte-for-byte, in the
same order as before (protected blocks first, in their original order, then retrieval order). Under
budget pressure the rank-differentiated compression and the hard budget stay as they were.
"""

from __future__ import annotations

import pytest

SURPLUS_LEVELS = ["high", "moderate", "low", "constrained"]
QUERY = "why do participants miss invoice reminders"


def _chunk(n: int, size: int = 1200) -> str:
    """Interview-like evidence with the filler and qualifiers the compressor removes first."""
    sentence = (
        f"P{n} basically said that, in order to act on invoice reminders, they really need them "
        "before the due date. It is important to note that the bookkeeper chases clients by "
        "phone instead, which is very slow and generally happens on Friday afternoons.\n"
    )
    return (sentence * (size // len(sentence) + 1))[:size]


def _retrieved(text: str, rank: int, source: str = "interview.md"):
    from app.core.rag import RetrievalResult

    return RetrievalResult(text=text, source=source, page=None, score=1.0 / (60 + rank))


@pytest.mark.parametrize("surplus", SURPLUS_LEVELS)
def test_chunks_that_fit_the_budget_reach_the_prompt_verbatim(surplus):
    from app.core.prompt_compressor import compress_rag_chunks_indexed

    chunks = [_chunk(n) for n in range(1, 6)]  # 6,000 characters against 16,000
    kept, used = compress_rag_chunks_indexed(chunks, QUERY, 4000, surplus)

    assert kept == list(enumerate(chunks)), "every chunk whole, in retrieval order"
    assert used == sum(len(c) for c in chunks) // 4


def test_a_budget_filled_exactly_is_not_budget_pressure():
    from app.core.prompt_compressor import compress_rag_chunks_indexed

    chunks = [_chunk(n, 800) for n in range(1, 6)]  # 4,000 characters: exactly 1,000 tokens
    kept, _ = compress_rag_chunks_indexed(chunks, QUERY, 1000, "moderate")

    assert kept == list(enumerate(chunks))


def test_protected_blocks_stay_first_and_whole_when_everything_fits():
    from app.core.prompt_compressor import compress_rag_chunks_indexed

    protocol = "<qualitative_coding_protocol>Code every quote.</qualitative_coding_protocol>"
    policy = "<reliability_policy>Kappa at least 0.60.</reliability_policy>"
    chunks = [_chunk(1), protocol, _chunk(2), policy]
    kept, _ = compress_rag_chunks_indexed(chunks, QUERY, 4000, "moderate")

    assert kept == [(1, protocol), (3, policy), (0, chunks[0]), (2, chunks[2])]


@pytest.mark.parametrize("surplus", SURPLUS_LEVELS)
def test_one_character_over_the_budget_still_compresses_within_it(surplus):
    from app.core.prompt_compressor import compress_rag_chunks_indexed

    chunks = [_chunk(n, 800) for n in range(1, 6)]
    chunks[-1] += "!"  # 4,001 characters against 4,000
    kept, _ = compress_rag_chunks_indexed(chunks, QUERY, 1000, surplus)

    assert sum(len(text) for _, text in kept) <= 1000 * 4
    assert [index for index, _ in kept] == sorted(index for index, _ in kept)
    assert any(text != chunks[index] for index, text in kept), "pressure still compresses"
    if surplus in ("high", "moderate"):
        assert kept[0] == (0, chunks[0]), "the top-ranked chunk is compressed least"


async def test_chat_path_carries_every_retrieved_chunk_verbatim_at_the_largest_budget():
    """The M3 case: five default-sized chunks at the 4,000-token RAG budget of a 128k window."""
    from app.core.rag import RAGContext, build_compressed_rag_context, format_context_part

    chunks = [_chunk(n) for n in range(1, 6)]
    results = [_retrieved(text, rank) for rank, text in enumerate(chunks, 1)]
    rag = RAGContext(query=QUERY, retrieved=results, context_text="")

    text, included = await build_compressed_rag_context("p1", rag, QUERY, 4000, "moderate")

    assert included == results
    assert text == "\n\n".join(format_context_part(i, r) for i, r in enumerate(results, 1))
    assert len(text) <= 4000 * 4
