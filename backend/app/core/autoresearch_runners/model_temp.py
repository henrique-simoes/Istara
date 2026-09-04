# Inspired by Karpathy's autoresearch (MIT) — https://github.com/karpathy/autoresearch
"""Loop 6: Model/Temperature Grid Search.

The simplest loop — no code mutation, just point evaluation.  Systematically
tests (endpoint, temperature) combinations for each skill and records quality
metrics to the model_skill_stats table.  The best combo is persisted to
``data/_skill_model_config.json``.

For every selectable agentic engine the sweep space is the **PiModelManager
catalog**: each catalog row is a distinct endpoint identity,
so two rows that serve the same model stay separate and every candidate is
resolved/pinned by exact ``endpoint_id`` through grid, mutation, dispatch, and
the recorded stat evidence — never collapsed to a unique model name.  Projected
``LLMServer`` rows are included (read-only, no live model loading) and a catalog
that spans fewer distinct endpoints than the requested sweep width is recorded
``sweep_truncated`` rather than silently narrowed. The selected engine changes
the AgenticDispatcher's loop semantics, never the model-management authority.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Awaitable, Callable

from app.core.autoresearch_runners import BaseLoopRunner

logger = logging.getLogger(__name__)

TEMPERATURES = [0.1, 0.3, 0.5, 0.7, 0.9]
CONFIG_PATH = Path("data/_skill_model_config.json")

# A cross-endpoint sweep needs at least this many distinct catalog identities to
# be non-degenerate; a catalog narrower than this is recorded ``sweep_truncated``
# against the requested endpoint width (master plan §8 W6).
DEFAULT_REQUESTED_ENDPOINT_WIDTH = 2


@dataclass(frozen=True)
class SweepEndpoint:
    """One distinct sweep identity: an exact Pi endpoint (``endpoint_id``) plus
    the model it serves."""

    endpoint_id: str | None
    model: str


@dataclass(frozen=True)
class SweepCandidate:
    """One point in the (endpoint, temperature) grid.

    ``endpoint_id`` pins the exact PiModelManager catalog identity on the Pi
    engine so same-model endpoints never collapse."""

    endpoint_id: str | None
    model: str | None
    temperature: float


class ModelTempRunner(BaseLoopRunner):
    """Grid-search over (endpoint, temperature) for a given skill."""

    loop_type = "model_temp"
    needs_persona_lock = False

    def __init__(self) -> None:
        self._current: SweepCandidate | None = None
        # Key already-tested cells by exact identity so same-model endpoints are
        # tracked independently: (endpoint_id, model, temperature).
        self._tested: set[tuple[str | None, str | None, float]] = set()
        self._grid: list[SweepCandidate] = []
        self._grid_index = 0
        # The requested endpoint width the sweep wants to span; a catalog with
        # fewer distinct endpoints is recorded truncated (master plan §8 W6).
        self._requested_endpoint_width: int = DEFAULT_REQUESTED_ENDPOINT_WIDTH
        # True when the Pi-engine sweep could not span the requested number of
        # distinct endpoints (recorded, never silently narrowed).
        self._sweep_truncated: bool = False

    # ------------------------------------------------------------------
    # Grid construction
    # ------------------------------------------------------------------

    async def _build_grid(self) -> list[SweepCandidate]:
        """Build the (endpoint, temperature) grid from available endpoints.

        The sweep space is always the PiModelManager catalog (settings
        endpoints + projected LLMServer rows + local Ollama/LM Studio entries)
        with exact endpoint identities preserved. This holds for both Istara
        and Pi loop semantics: engine selection controls execution, not catalog
        ownership. When the catalog cannot span the requested endpoint width
        the sweep is flagged ``sweep_truncated`` rather than silently narrowed.
        """
        self._sweep_truncated = False
        endpoints = await self._pi_sweep_endpoints()

        if not endpoints:
            return []

        grid: list[SweepCandidate] = []
        for ep in endpoints:
            for temp in TEMPERATURES:
                if (ep.endpoint_id, ep.model, temp) not in self._tested:
                    grid.append(SweepCandidate(ep.endpoint_id, ep.model, temp))
        return grid

    async def _pi_sweep_endpoints(self) -> list[SweepEndpoint]:
        """Distinct non-embedding endpoint identities from the PiModelManager catalog.

        Each catalog row is one exact-identity endpoint (settings + projected
        ``LLMServer`` rows + local Ollama/LM Studio).  Identities are preserved,
        never collapsed to unique model names, so two endpoints that serve the
        same model stay separate and are resolved/pinned by exact
        ``endpoint_id`` at dispatch.  Persisted ``LLMServer`` rows are projected
        read-only via ``ensure_db_projection`` (identity only — never a live
        model load).  A catalog spanning fewer distinct endpoints than the
        requested sweep width is recorded ``sweep_truncated``.
        """
        from app.core.pi_runtime.model_manager import PiModelManager

        try:
            manager = PiModelManager()
            # Project persisted LLMServer rows into the catalog before sweeping.
            # This is a read-only DB projection of endpoint identities; it never
            # connects to a server or loads a model.
            projection = getattr(manager, "ensure_db_projection", None)
            if callable(projection):
                await projection()
            catalog = manager.catalog()
        except Exception as e:  # pragma: no cover - catalog construction guard
            logger.warning("ModelTempRunner: PiModelManager catalog unavailable: %s", e)
            self._sweep_truncated = True
            return []

        endpoints: list[SweepEndpoint] = []
        seen_ids: set[str] = set()
        for info in catalog:
            endpoint_id = (getattr(info, "endpoint_id", "") or "").strip()
            model = (getattr(info, "model", "") or "").strip()
            # Skip embedding endpoints (never a chat-sweep candidate).
            if not model or "embed" in model.lower():
                continue
            # Preserve exact identity; only guard against a missing/duplicate id.
            if not endpoint_id or endpoint_id in seen_ids:
                continue
            seen_ids.add(endpoint_id)
            endpoints.append(SweepEndpoint(endpoint_id=endpoint_id, model=model))

        self._record_endpoint_width(len(endpoints))
        return endpoints

    def _record_endpoint_width(self, available: int) -> None:
        """Flag ``sweep_truncated`` when the catalog spans fewer distinct
        endpoints than the requested sweep width (never silently narrowed)."""
        if available == 0:
            logger.warning("ModelTempRunner: no models available from PiModelManager catalog")
            self._sweep_truncated = True
        elif available < self._requested_endpoint_width:
            logger.warning(
                "ModelTempRunner: sweep_truncated — Pi catalog spans %d distinct "
                "endpoint(s), fewer than the requested sweep width %d; the sweep "
                "cannot compare across the requested endpoint pool",
                available,
                self._requested_endpoint_width,
            )
            self._sweep_truncated = True

    # ------------------------------------------------------------------
    # BaseLoopRunner interface
    # ------------------------------------------------------------------

    async def measure_baseline(self, target: str) -> float:
        """Execute skill with default model/temp and return quality score."""
        self._tested.clear()
        self._grid = await self._build_grid()
        self._grid_index = 0
        return await self._evaluate_skill(target, endpoint_id=None, model=None, temperature=0.7)

    async def measure(self, target: str) -> float:
        """Execute skill with the current test endpoint/temp."""
        candidate = self._current
        if candidate is None:
            return await self._evaluate_skill(target, endpoint_id=None, model=None, temperature=0.7)
        return await self._evaluate_skill(
            target,
            endpoint_id=candidate.endpoint_id,
            model=candidate.model,
            temperature=candidate.temperature,
        )

    async def hypothesize(
        self, target: str, current_score: float, history: list[dict]
    ) -> tuple[str, dict]:
        """Pick next (endpoint, temperature) from grid, skipping tested combos."""
        # Rebuild grid if exhausted (shouldn't happen in normal flow)
        if self._grid_index >= len(self._grid):
            self._grid = await self._build_grid()
            self._grid_index = 0
            if not self._grid:
                raise RuntimeError("All model/temperature combos exhausted")

        candidate = self._grid[self._grid_index]
        self._grid_index += 1

        identity = candidate.endpoint_id or candidate.model or "default"
        hypothesis = (
            f"Test endpoint={identity} model={candidate.model} "
            f"temperature={candidate.temperature} on skill '{target}'"
        )
        mutation = {
            "description": (
                f"endpoint={identity}, model={candidate.model}, temp={candidate.temperature}"
            ),
            "endpoint_id": candidate.endpoint_id,
            "model": candidate.model,
            "temperature": candidate.temperature,
        }
        return hypothesis, mutation

    async def apply_mutation(self, target: str, mutation: dict) -> Callable[[], Awaitable[None]]:
        """Set current endpoint/temp for evaluation. Revert is a no-op for point evals."""
        self._current = SweepCandidate(
            endpoint_id=mutation.get("endpoint_id"),
            model=mutation["model"],
            temperature=mutation["temperature"],
        )
        self._tested.add(
            (self._current.endpoint_id, self._current.model, self._current.temperature)
        )

        async def _noop_revert() -> None:
            pass

        return _noop_revert

    # ------------------------------------------------------------------
    # Evaluation and recording
    # ------------------------------------------------------------------

    async def _evaluate_skill(
        self,
        skill_name: str,
        *,
        endpoint_id: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> float:
        """Execute a skill once and return a quality score in [0, 1].

        The swept candidate is pinned by exact ``endpoint_id``
        (``TurnParams.endpoint_id``) so the dispatcher resolves the precise
        catalog identity rather than the first model match.
        """
        from app.skills.skill_manager import skill_manager

        defn = skill_manager.get(skill_name)
        if not defn:
            raise ValueError(f"Skill not found: {skill_name}")

        prompt = defn.data.get("execute_prompt", "")
        if not prompt:
            raise ValueError(f"Skill '{skill_name}' has no execute_prompt")

        # Use a simple quality-assessment prompt to evaluate the skill output
        messages = [
            {
                "role": "system",
                "content": prompt,
            },
            {
                "role": "user",
                "content": (
                    "Generate a brief example output for this UX research skill. "
                    "Demonstrate its core capability with realistic sample data."
                ),
            },
        ]

        try:
            # W6/W9: the candidate skill run goes through the AgenticDispatcher
            # (``autoresearch.model_temp.evaluate``); the swept candidate is
            # pinned by exact ``endpoint_id`` so same-model endpoints are
            # resolved distinctly.
            from app.core.agentic import agentic
            from app.core.agentic.types import TurnParams

            outcome = await agentic.completion(
                purpose="autoresearch.model_temp.evaluate",
                project_id=self.require_project_id(),
                system=messages[0]["content"],
                messages=messages[1:],
                params=TurnParams(
                    endpoint_id=endpoint_id,
                    model=model,
                    temperature=temperature,
                ),
                spine_phase="execution",
                engine=self.engine,
            )
            content = outcome.text
        except Exception as e:
            logger.warning(f"Skill evaluation failed: {e}")
            return 0.0

        # Score the output quality via LLM self-evaluation
        score = await self._score_output(content, skill_name)

        # Record to model_skill_stats under the exact swept identity so
        # same-model endpoints do not collapse in the stat evidence.
        await self._record_stats(
            skill_name,
            self._stat_identity(model, endpoint_id),
            temperature,
            score,
        )

        return score

    @staticmethod
    def _stat_identity(model: str | None, endpoint_id: str | None) -> str:
        """The model_skill_stats key that preserves endpoint identity.

        Two endpoints serving the same model stay distinct
        (``<model>@<endpoint_id>``) for every loop engine.
        """
        base = model or "default"
        if endpoint_id:
            return f"{base}@{endpoint_id}"
        return base

    async def _score_output(self, output: str, skill_name: str) -> float:
        """Use LLM to score skill output quality on a 0-1 scale."""
        if not output or len(output.strip()) < 20:
            return 0.1

        scoring_messages = [
            {
                "role": "system",
                "content": (
                    "You are a quality evaluator for UX research skill outputs. "
                    "Score the following output on a scale of 0.0 to 1.0 based on: "
                    "completeness, relevance, actionability, and evidence quality. "
                    "Respond with ONLY a decimal number between 0.0 and 1.0."
                ),
            },
            {
                "role": "user",
                "content": (f"Skill: {skill_name}\n\nOutput to score:\n{output[:2000]}"),
            },
        ]

        try:
            # W6/W9: the LLM-as-judge score goes through the AgenticDispatcher
            # (``autoresearch.model_temp.score``).
            from app.core.agentic import agentic
            from app.core.agentic.types import TurnParams

            outcome = await agentic.completion(
                purpose="autoresearch.model_temp.score",
                project_id=self.require_project_id(),
                system=scoring_messages[0]["content"],
                messages=scoring_messages[1:],
                params=TurnParams(temperature=0.1, max_tokens=10),
                spine_phase="review",
                engine=self.engine,
            )
            score_text = (outcome.text or "").strip()
            # Parse the score — extract first float-like token
            for token in score_text.replace(",", ".").split():
                try:
                    val = float(token)
                    return max(0.0, min(1.0, val))
                except ValueError:
                    continue
            return 0.5
        except Exception:
            return 0.5

    async def _record_stats(
        self,
        skill_name: str,
        model_name: str,
        temperature: float,
        score: float,
    ) -> None:
        """Record a measurement to the model_skill_stats table."""
        from sqlalchemy import select

        from app.models.database import async_session
        from app.models.model_skill_stats import ModelSkillStats

        async with async_session() as db:
            result = await db.execute(
                select(ModelSkillStats).where(
                    ModelSkillStats.project_id == self.require_project_id(),
                    ModelSkillStats.skill_name == skill_name,
                    ModelSkillStats.model_name == model_name,
                    ModelSkillStats.temperature == temperature,
                )
            )
            stats = result.scalar_one_or_none()

            if stats:
                stats.executions += 1
                stats.total_quality += score
                # EMA update (alpha=0.1)
                stats.quality_ema = stats.quality_ema * 0.9 + score * 0.1
                stats.best_quality = max(stats.best_quality, score)
                stats.last_used = datetime.now(timezone.utc)
                stats.source = "autoresearch"
            else:
                stats = ModelSkillStats(
                    project_id=self.require_project_id(),
                    skill_name=skill_name,
                    model_name=model_name,
                    temperature=temperature,
                    executions=1,
                    total_quality=score,
                    quality_ema=score,
                    best_quality=score,
                    source="autoresearch",
                    last_used=datetime.now(timezone.utc),
                )
                db.add(stats)

            await db.commit()
        # Do not write the global best-config here. Autoresearch measurements
        # are sandbox evidence; applying a preferred model/temperature requires
        # an approved governance proposal.

    async def _save_best_config(
        self,
        skill_name: str,
        model_name: str,
        temperature: float,
        score: float,
    ) -> None:
        """Persist the best model+temp per skill to data/_skill_model_config.json."""
        from app.core.checkpoint import atomic_write

        config: dict = {}
        if CONFIG_PATH.exists():
            try:
                config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                config = {}

        current = config.get(skill_name)
        if current is None or score > current.get("best_quality", 0):
            config[skill_name] = {
                "model": model_name,
                "temperature": temperature,
                "best_quality": score,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            atomic_write(CONFIG_PATH, json.dumps(config, indent=2))
