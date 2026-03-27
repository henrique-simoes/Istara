# Inspired by Karpathy's autoresearch (MIT) — https://github.com/karpathy/autoresearch
"""Loop 4: RAG Parameter Tuning.

Optimizes retrieval parameters — chunk_size, chunk_overlap, hybrid weights —
by running test queries against a project's vector store and measuring
precision@k.
"""

from __future__ import annotations

import logging
import random
from typing import Awaitable, Callable

from app.config import settings
from app.core.autoresearch_runners import BaseLoopRunner

logger = logging.getLogger(__name__)

# Tunable parameter ranges
PARAM_RANGES = {
    "rag_chunk_size": (400, 2400),
    "rag_chunk_overlap": (50, 400),
    "rag_hybrid_vector_weight": (0.3, 0.9),
    "rag_hybrid_keyword_weight": (0.1, 0.7),
}

# Test queries used for evaluation (UX-research domain)
TEST_QUERIES = [
    "What are the key usability issues found in the interviews?",
    "Summarize participant feedback on onboarding flow",
    "What design patterns were most effective?",
    "List the main pain points from user testing sessions",
    "How do participants describe their experience with search?",
]


class RAGParamsRunner(BaseLoopRunner):
    """Tune RAG retrieval parameters via greedy hill-climbing."""

    loop_type = "rag_params"
    needs_persona_lock = False

    def __init__(self) -> None:
        self._original_values: dict[str, float | int] = {}
        self._project_id: str = ""

    # ------------------------------------------------------------------
    # BaseLoopRunner interface
    # ------------------------------------------------------------------

    async def measure_baseline(self, target: str) -> float:
        """Measure current retrieval quality.  *target* is a project_id."""
        self._project_id = target
        self._snapshot_current_params()
        return await self._evaluate_retrieval(target)

    async def measure(self, target: str) -> float:
        """Measure retrieval quality after a parameter mutation."""
        return await self._evaluate_retrieval(target)

    async def hypothesize(
        self, target: str, current_score: float, history: list[dict]
    ) -> tuple[str, dict]:
        """Generate a parameter mutation hypothesis.

        Uses LLM-guided suggestion when history is available, otherwise
        applies a random perturbation.
        """
        if len(history) >= 3:
            return await self._llm_hypothesis(current_score, history)
        return self._random_perturbation()

    async def apply_mutation(
        self, target: str, mutation: dict
    ) -> Callable[[], Awaitable[None]]:
        """Apply parameter changes to settings in-memory.  Returns revert fn."""
        old_values: dict[str, float | int] = {}
        params = mutation.get("params", {})

        for key, value in params.items():
            if hasattr(settings, key):
                old_values[key] = getattr(settings, key)
                setattr(settings, key, value)
                logger.debug(f"RAGParamsRunner: {key} = {value} (was {old_values[key]})")

        async def _revert() -> None:
            for k, v in old_values.items():
                setattr(settings, k, v)
                logger.debug(f"RAGParamsRunner: reverted {k} = {v}")

        return _revert

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _snapshot_current_params(self) -> None:
        """Capture current RAG settings for reference."""
        self._original_values = {
            key: getattr(settings, key)
            for key in PARAM_RANGES
            if hasattr(settings, key)
        }

    def _random_perturbation(self) -> tuple[str, dict]:
        """Pick a random parameter and nudge it within its valid range."""
        key = random.choice(list(PARAM_RANGES.keys()))
        lo, hi = PARAM_RANGES[key]
        current = getattr(settings, key, lo)

        # Perturb by 10-30% of the range
        span = hi - lo
        delta = random.uniform(0.1, 0.3) * span * random.choice([-1, 1])
        new_val = current + delta

        # Clamp to range and match type
        if isinstance(current, int):
            new_val = int(max(lo, min(hi, round(new_val))))
        else:
            new_val = round(max(lo, min(hi, new_val)), 2)

        hypothesis = (
            f"Adjust {key} from {current} to {new_val} "
            f"(range {lo}-{hi}) to improve retrieval precision"
        )
        mutation = {
            "description": f"{key}: {current} -> {new_val}",
            "params": {key: new_val},
        }
        return hypothesis, mutation

    async def _llm_hypothesis(
        self, current_score: float, history: list[dict]
    ) -> tuple[str, dict]:
        """Ask the LLM to suggest parameter changes based on experiment history."""
        from app.core.llm_router import llm_router

        # Summarize history for context
        history_summary = "\n".join(
            f"  - {h.get('mutation_description', '?')}: "
            f"score={h.get('experiment_score', '?')}, kept={h.get('kept', False)}"
            for h in history[-10:]
        )
        current_params = {
            key: getattr(settings, key) for key in PARAM_RANGES if hasattr(settings, key)
        }

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an optimization assistant tuning RAG retrieval parameters. "
                    "Suggest ONE parameter change. Respond in this exact JSON format:\n"
                    '{"param": "<param_name>", "value": <number>, '
                    '"reason": "<brief reason>"}\n\n'
                    f"Parameters and ranges: {PARAM_RANGES}\n"
                    f"Current values: {current_params}\n"
                    f"Current score: {current_score:.4f}"
                ),
            },
            {
                "role": "user",
                "content": f"Recent experiment results:\n{history_summary}\n\nSuggest next change:",
            },
        ]

        try:
            response = await llm_router.chat(messages, temperature=0.7, max_tokens=200)
            content = response.get("message", {}).get("content", "")
            # Parse JSON from response
            import json

            # Find JSON in the response
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                suggestion = json.loads(content[start:end])
                param = suggestion.get("param", "")
                value = suggestion.get("value")
                reason = suggestion.get("reason", "LLM-suggested")

                if param in PARAM_RANGES and value is not None:
                    lo, hi = PARAM_RANGES[param]
                    current = getattr(settings, param)
                    if isinstance(current, int):
                        value = int(max(lo, min(hi, round(value))))
                    else:
                        value = round(max(lo, min(hi, float(value))), 2)

                    hypothesis = f"LLM suggests: {param} = {value} ({reason})"
                    mutation = {
                        "description": f"{param}: {current} -> {value}",
                        "params": {param: value},
                    }
                    return hypothesis, mutation
        except Exception as e:
            logger.debug(f"LLM hypothesis generation failed, falling back: {e}")

        # Fallback to random perturbation
        return self._random_perturbation()

    async def _evaluate_retrieval(self, project_id: str) -> float:
        """Run test queries and measure retrieval quality as average precision@k."""
        from app.core.rag import VectorStore

        store = VectorStore(project_id)
        count = await store.count()
        if count == 0:
            logger.warning(f"RAGParamsRunner: project '{project_id}' has no indexed chunks")
            return 0.0

        scores: list[float] = []
        for query in TEST_QUERIES:
            try:
                score = await self._score_single_query(project_id, query)
                scores.append(score)
            except Exception as e:
                logger.debug(f"Query evaluation failed: {e}")
                scores.append(0.0)

        return sum(scores) / len(scores) if scores else 0.0

    async def _score_single_query(self, project_id: str, query: str) -> float:
        """Score a single retrieval query using relevance assessment."""
        from app.core.embeddings import embed_text
        from app.core.rag import hybrid_search

        query_vector = await embed_text(query)
        results = await hybrid_search(project_id, query, query_vector)

        if not results:
            return 0.0

        # Score based on: number of results, score distribution, and content relevance
        # More results with higher scores = better
        num_results = len(results)
        avg_score = sum(r.score for r in results) / num_results if num_results else 0.0

        # Penalize if too few results
        coverage = min(1.0, num_results / max(settings.rag_top_k, 1))

        # Combined score
        return (avg_score * 0.6 + coverage * 0.4)
