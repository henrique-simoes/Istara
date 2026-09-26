# Inspired by Karpathy's autoresearch (MIT) — https://github.com/karpathy/autoresearch
"""Loop 4: RAG Parameter Tuning.

Tunes retrieval parameters (chunk size, overlap, hybrid weights, RRF k) against RELEVANCE
JUDGMENTS: the objective is mean nDCG@10 of the production hybrid retriever on the retrieval
benchmark's qrels (``app.evals.retrieval_eval``, measurement 1).

The previous objective was ``0.6 x mean(fused score) + 0.4 x coverage`` over five fixed queries
(F3). The fused RRF score is proportional to the weights being tuned, so raising either weight
raised the "precision@k" with no change in what was retrieved. Chunk-size mutations never
re-indexed anything, and every mutation was a ``setattr`` on the process-wide settings, which
other projects' requests read while the measurement ran.

Now every candidate is measured on a sandbox index rebuilt from the benchmark corpus whenever
chunking changes. The candidate is passed explicitly and never written to ``settings``, and
without a benchmark the loop fails closed instead of optimising a proxy.
"""

from __future__ import annotations

import logging
import random
from collections.abc import Awaitable, Callable

from app.config import settings
from app.core.autoresearch_runners import BaseLoopRunner

logger = logging.getLogger(__name__)

# Tunable parameter ranges
PARAM_RANGES = {
    "rag_chunk_size": (400, 2400),
    "rag_chunk_overlap": (50, 400),
    "rag_hybrid_vector_weight": (0.3, 0.9),
    "rag_hybrid_keyword_weight": (0.1, 0.7),
    "rag_rrf_k": (10, 200),
}

_CONFIG_FIELDS = {
    "rag_chunk_size": "chunk_size",
    "rag_chunk_overlap": "chunk_overlap",
    "rag_hybrid_vector_weight": "vector_weight",
    "rag_hybrid_keyword_weight": "keyword_weight",
    "rag_rrf_k": "rrf_k",
}


class RAGParamsRunner(BaseLoopRunner):
    """Tune RAG retrieval parameters via greedy hill-climbing."""

    loop_type = "rag_params"
    needs_persona_lock = False

    def __init__(self) -> None:
        self._original_values: dict[str, float | int] = {}
        self._project_id: str = ""
        self._candidate: dict[str, float | int] = {}
        self.objective = None  # app.evals.retrieval_eval.RetrievalObjective

    # ------------------------------------------------------------------
    # BaseLoopRunner interface
    # ------------------------------------------------------------------

    async def measure_baseline(self, target: str) -> float:
        """nDCG@10 of the current configuration on the retrieval benchmark (fails closed)."""
        self._bind_target_scope(target)
        self._snapshot_current_params()
        self._candidate = {}
        self.close()
        from app.evals.retrieval_eval import Qrels, RetrievalObjective

        qrels = Qrels.load(
            settings.retrieval_benchmark_qrels or _default_qrels(),
            settings.retrieval_benchmark_corpus or None,
        )
        self.objective = RetrievalObjective(qrels)
        return await self._evaluate_retrieval()

    async def measure(self, target: str) -> float:
        """nDCG@10 of the candidate configuration, on its own sandbox index."""
        self._bind_target_scope(target)
        return await self._evaluate_retrieval()

    def close(self) -> None:
        """Delete the sandbox indices (called by the engine when the loop ends)."""
        if self.objective is not None:
            self.objective.close()
            self.objective = None

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

    async def apply_mutation(self, target: str, mutation: dict) -> Callable[[], Awaitable[None]]:
        """Stage a candidate for the next measurement. Nothing process-wide changes.

        The candidate lives on this runner and reaches only the sandbox objective. The old
        ``setattr(settings, ...)`` changed retrieval for every project while it measured (F9).
        """
        params = mutation.get("params", {})
        self._candidate = {k: v for k, v in params.items() if k in PARAM_RANGES}

        async def _revert() -> None:
            self._candidate = {}

        return _revert

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _bind_target_scope(self, target: str) -> str:
        """Resolve the RAG *target* to the authorized project binding, fail-closed.

        The engine binds ``_active_project_id`` from the route-authorized
        ``project_id`` (``bind_project`` / ``require_project_id``).  ``target``
        is caller-controlled and the ``/start`` route authorizes
        ``body.project_id`` without requiring ``target == project_id``.  Trusting
        the raw ``target`` for scope would let a turn resolve retrieval, the
        dispatcher, telemetry, and execution under an unauthorized project id, so
        we bind every measurement to the authorized id and reject a divergent
        target before any retrieval or dispatcher call runs.
        """
        authorized = self.require_project_id()
        requested = str(target or "").strip()
        if requested and requested != authorized:
            raise RuntimeError(
                "rag_params target scope mismatch: refusing to tune retrieval "
                f"for target project '{requested}' under project '{authorized}' "
                "authorization"
            )
        self._project_id = authorized
        return authorized

    def _snapshot_current_params(self) -> None:
        """Capture current RAG settings for reference."""
        self._original_values = {
            key: getattr(settings, key) for key in PARAM_RANGES if hasattr(settings, key)
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

    async def _llm_hypothesis(self, current_score: float, history: list[dict]) -> tuple[str, dict]:
        """Ask the LLM to suggest parameter changes based on experiment history."""
        # Scope the dispatch/telemetry to the authorized BaseLoopRunner binding,
        # never the caller-controlled target. Resolving it before the try block
        # fails closed loudly on a missing binding instead of silently degrading
        # to a random perturbation.
        project_id = self.require_project_id()

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
            # W6/W9: the next-parameter suggestion goes through the
            # AgenticDispatcher (``autoresearch.rag_params.hypothesize``).
            from app.core.agentic import agentic
            from app.core.agentic.types import TurnParams

            outcome = await agentic.completion(
                purpose="autoresearch.rag_params.hypothesize",
                project_id=project_id,
                system=messages[0]["content"],
                messages=messages[1:],
                params=TurnParams(temperature=0.7, max_tokens=200),
                spine_phase="plan",
                engine=self.engine,
            )
            content = outcome.text
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

    def _config(self):
        from app.evals.retrieval_eval import RetrievalConfig

        overrides = {_CONFIG_FIELDS[k]: v for k, v in self._candidate.items()}
        return RetrievalConfig.from_settings(**overrides)

    async def _evaluate_retrieval(self) -> float:
        """Mean nDCG@10 over the benchmark questions (relevance judgments, not fused scores)."""
        if self.objective is None:
            raise RuntimeError("rag_params: measure_baseline must run first")
        return await self.objective.score(self._config())


def _default_qrels():
    from app.evals.retrieval_eval import DEFAULT_QRELS

    return DEFAULT_QRELS
