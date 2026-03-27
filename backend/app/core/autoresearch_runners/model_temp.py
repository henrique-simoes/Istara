# Inspired by Karpathy's autoresearch (MIT) — https://github.com/karpathy/autoresearch
"""Loop 6: Model/Temperature Grid Search.

The simplest loop — no code mutation, just point evaluation.  Systematically
tests (model, temperature) combinations for each skill and records quality
metrics to the model_skill_stats table.  The best combo is persisted to
``data/_skill_model_config.json``.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Awaitable, Callable

from app.core.autoresearch_runners import BaseLoopRunner

logger = logging.getLogger(__name__)

TEMPERATURES = [0.1, 0.3, 0.5, 0.7, 0.9]
CONFIG_PATH = Path("data/_skill_model_config.json")


class ModelTempRunner(BaseLoopRunner):
    """Grid-search over (model, temperature) for a given skill."""

    loop_type = "model_temp"
    needs_persona_lock = False

    def __init__(self) -> None:
        self._current_model: str | None = None
        self._current_temp: float = 0.7
        self._tested: set[tuple[str, float]] = set()
        self._grid: list[tuple[str, float]] = []
        self._grid_index = 0

    # ------------------------------------------------------------------
    # Grid construction
    # ------------------------------------------------------------------

    async def _build_grid(self) -> list[tuple[str, float]]:
        """Build the (model, temperature) grid from available models."""
        from app.core.llm_router import llm_router

        models_raw = await llm_router.list_models()
        model_names: list[str] = []
        for m in models_raw:
            name = m.get("name", "")
            # Skip embedding models
            if "embed" in name.lower():
                continue
            if name and name not in model_names:
                model_names.append(name)

        if not model_names:
            logger.warning("ModelTempRunner: no models available from llm_router")
            return []

        grid: list[tuple[str, float]] = []
        for model in model_names:
            for temp in TEMPERATURES:
                if (model, temp) not in self._tested:
                    grid.append((model, temp))
        return grid

    # ------------------------------------------------------------------
    # BaseLoopRunner interface
    # ------------------------------------------------------------------

    async def measure_baseline(self, target: str) -> float:
        """Execute skill with default model/temp and return quality score."""
        self._tested.clear()
        self._grid = await self._build_grid()
        self._grid_index = 0
        return await self._evaluate_skill(target, model=None, temperature=0.7)

    async def measure(self, target: str) -> float:
        """Execute skill with the current test model/temp."""
        return await self._evaluate_skill(
            target, model=self._current_model, temperature=self._current_temp
        )

    async def hypothesize(
        self, target: str, current_score: float, history: list[dict]
    ) -> tuple[str, dict]:
        """Pick next (model, temperature) from grid, skipping already-tested combos."""
        # Rebuild grid if exhausted (shouldn't happen in normal flow)
        if self._grid_index >= len(self._grid):
            self._grid = await self._build_grid()
            self._grid_index = 0
            if not self._grid:
                raise RuntimeError("All model/temperature combos exhausted")

        model, temp = self._grid[self._grid_index]
        self._grid_index += 1

        hypothesis = f"Test model={model} temperature={temp} on skill '{target}'"
        mutation = {
            "description": f"model={model}, temp={temp}",
            "model": model,
            "temperature": temp,
        }
        return hypothesis, mutation

    async def apply_mutation(
        self, target: str, mutation: dict
    ) -> Callable[[], Awaitable[None]]:
        """Set current model/temp for evaluation. Revert is a no-op for point evals."""
        self._current_model = mutation["model"]
        self._current_temp = mutation["temperature"]
        self._tested.add((self._current_model, self._current_temp))

        async def _noop_revert() -> None:
            pass

        return _noop_revert

    # ------------------------------------------------------------------
    # Evaluation and recording
    # ------------------------------------------------------------------

    async def _evaluate_skill(
        self,
        skill_name: str,
        model: str | None,
        temperature: float,
    ) -> float:
        """Execute a skill once and return a quality score in [0, 1]."""
        from app.core.llm_router import llm_router
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
            response = await llm_router.chat(
                messages, model=model, temperature=temperature
            )
            content = response.get("message", {}).get("content", "")
        except Exception as e:
            logger.warning(f"Skill evaluation failed: {e}")
            return 0.0

        # Score the output quality via LLM self-evaluation
        score = await self._score_output(content, skill_name)

        # Record to model_skill_stats
        await self._record_stats(
            skill_name, model or "default", temperature, score
        )

        return score

    async def _score_output(self, output: str, skill_name: str) -> float:
        """Use LLM to score skill output quality on a 0-1 scale."""
        from app.core.llm_router import llm_router

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
                "content": (
                    f"Skill: {skill_name}\n\n"
                    f"Output to score:\n{output[:2000]}"
                ),
            },
        ]

        try:
            response = await llm_router.chat(
                scoring_messages, temperature=0.1, max_tokens=10
            )
            score_text = response.get("message", {}).get("content", "").strip()
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

        # Update the best-config file
        await self._save_best_config(skill_name, model_name, temperature, score)

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
