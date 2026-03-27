# Inspired by Karpathy's autoresearch (MIT) — https://github.com/karpathy/autoresearch
"""Autoresearch Engine — greedy hill-climbing optimization loop for UX research.

Implements the hypothesize -> mutate -> evaluate -> keep-or-discard pattern
adapted for 6 UX research optimization domains.
"""

import json
import logging
import uuid
from datetime import datetime, timezone

from app.config import settings
from app.core.autoresearch_isolation import autoresearch_context
from app.core.autoresearch_rate_limiter import check_experiment_limit
from app.models.autoresearch_experiment import AutoresearchExperiment
from app.models.database import async_session

logger = logging.getLogger(__name__)


class AutoresearchEngine:
    """Core optimization loop — all 6 runners use this engine."""

    def __init__(self):
        self._running = False
        self._current_experiment: dict | None = None
        self._stop_requested = False

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def current_experiment(self) -> dict | None:
        return self._current_experiment

    def request_stop(self):
        """Signal the running loop to stop after the current iteration."""
        self._stop_requested = True

    async def run_loop(
        self,
        runner,  # BaseLoopRunner
        target: str,
        max_iterations: int = 20,
        project_id: str = "",
    ) -> list[dict]:
        """Run the autoresearch optimization loop.

        Returns list of experiment results.
        """
        if self._running:
            raise RuntimeError("Engine already running")

        self._running = True
        self._stop_requested = False
        results: list[dict] = []
        baseline = 0.0

        try:
            # Acquire persona lock if needed
            if runner.needs_persona_lock:
                from app.core.agent_identity import acquire_persona_lock

                if not acquire_persona_lock(target, f"autoresearch-{runner.loop_type}"):
                    raise RuntimeError(f"Cannot acquire persona lock for {target}")

            # Measure baseline
            baseline = await runner.measure_baseline(target)
            best_score = baseline
            logger.info(
                f"Autoresearch [{runner.loop_type}] baseline for '{target}': {baseline:.4f}"
            )

            async with autoresearch_context():
                for i in range(max_iterations):
                    if self._stop_requested:
                        logger.info("Autoresearch stop requested")
                        break

                    # Check rate limits
                    async with async_session() as db:
                        allowed, reason = await check_experiment_limit(db, target)
                    if not allowed:
                        logger.info(f"Rate limit: {reason}")
                        break

                    # Check mutual exclusion with meta-hyperagent
                    if self._conflicts_with_meta(runner):
                        logger.info(
                            "Skipping — meta-hyperagent has active variant on target parameters"
                        )
                        continue

                    # Create experiment record
                    experiment_id = str(uuid.uuid4())
                    experiment: dict = {
                        "id": experiment_id,
                        "loop_type": runner.loop_type,
                        "target_name": target,
                        "iteration": i + 1,
                        "baseline_score": best_score,
                    }
                    self._current_experiment = experiment

                    try:
                        # Hypothesize
                        hypothesis, mutation = await runner.hypothesize(
                            target, best_score, results
                        )
                        experiment["hypothesis"] = hypothesis
                        experiment["mutation_description"] = str(
                            mutation.get("description", "")
                        )

                        # Apply mutation (returns revert function)
                        revert_fn = await runner.apply_mutation(target, mutation)

                        # Measure
                        try:
                            score = await runner.measure(target)
                            experiment["experiment_score"] = score
                            experiment["delta"] = score - best_score

                            # Keep or revert
                            if score > best_score:
                                best_score = score
                                experiment["kept"] = True
                                experiment["status"] = "completed"
                                logger.info(
                                    f"  [{i+1}/{max_iterations}] KEPT: "
                                    f"{hypothesis[:60]} "
                                    f"(delta=+{score - experiment['baseline_score']:.4f})"
                                )
                            else:
                                await revert_fn()
                                experiment["kept"] = False
                                experiment["status"] = "reverted"
                                logger.info(
                                    f"  [{i+1}/{max_iterations}] REVERTED: "
                                    f"{hypothesis[:60]} "
                                    f"(delta={score - experiment['baseline_score']:.4f})"
                                )
                        except Exception as e:
                            await revert_fn()
                            experiment["kept"] = False
                            experiment["status"] = "failed"
                            experiment["error_message"] = str(e)[:500]
                            logger.warning(
                                f"  [{i+1}/{max_iterations}] FAILED: {e}"
                            )
                    except Exception as e:
                        experiment["kept"] = False
                        experiment["status"] = "failed"
                        experiment["error_message"] = str(e)[:500]
                        logger.warning(
                            f"  [{i+1}/{max_iterations}] HYPOTHESIS FAILED: {e}"
                        )

                    # Persist experiment
                    experiment["completed_at"] = datetime.now(timezone.utc).isoformat()
                    await self._persist_experiment(experiment, project_id)
                    results.append(experiment)

                    # Broadcast progress
                    try:
                        from app.api.websocket import manager

                        await manager.broadcast("autoresearch_progress", experiment)
                    except Exception:
                        pass

            logger.info(
                f"Autoresearch [{runner.loop_type}] complete: "
                f"{len(results)} experiments, "
                f"{sum(1 for r in results if r.get('kept'))} kept"
            )

        finally:
            self._running = False
            self._current_experiment = None
            # Release persona lock
            if runner.needs_persona_lock:
                from app.core.agent_identity import release_persona_lock

                release_persona_lock(target, f"autoresearch-{runner.loop_type}")

            # Broadcast completion
            try:
                from app.api.websocket import manager

                await manager.broadcast(
                    "autoresearch_complete",
                    {
                        "loop_type": runner.loop_type,
                        "total": len(results),
                        "kept": sum(1 for r in results if r.get("kept")),
                        "best_score": best_score,
                        "baseline": baseline,
                    },
                )
            except Exception:
                pass

        return results

    def _conflicts_with_meta(self, runner) -> bool:
        """Check if meta-hyperagent has active variants on parameters this runner modifies."""
        try:
            from app.core.meta_hyperagent import meta_hyperagent

            if not settings.meta_hyperagent_enabled:
                return False
            variants = meta_hyperagent.get_active_variants()
            # Check overlap based on runner type
            conflict_prefixes: dict[str, list[str]] = {
                "rag_params": ["rag_"],
                "skill_prompt": ["skill_"],
                "persona": ["self_evolution."],
                "model_temp": [],
                "question_bank": [],
                "ui_sim": [],
            }
            prefixes = conflict_prefixes.get(runner.loop_type, [])
            for variant in variants:
                path = variant.get("parameter_path", "")
                if any(path.startswith(p) for p in prefixes):
                    return True
            return False
        except Exception:
            return False

    async def _persist_experiment(self, experiment: dict, project_id: str) -> None:
        """Save experiment to database."""
        async with async_session() as db:
            record = AutoresearchExperiment(
                id=experiment["id"],
                loop_type=experiment["loop_type"],
                target_name=experiment["target_name"],
                hypothesis=experiment.get("hypothesis", ""),
                mutation_description=experiment.get("mutation_description", ""),
                mutation_diff=json.dumps(experiment.get("mutation_diff", {})),
                baseline_score=experiment.get("baseline_score", 0),
                experiment_score=experiment.get("experiment_score"),
                delta=experiment.get("delta", 0),
                kept=experiment.get("kept", False),
                status=experiment.get("status", "failed"),
                error_message=experiment.get("error_message", ""),
                project_id=project_id,
                completed_at=datetime.now(timezone.utc),
            )
            db.add(record)
            await db.commit()

    async def get_experiments(
        self,
        loop_type: str | None = None,
        kept: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """Get experiment history."""
        from sqlalchemy import select

        async with async_session() as db:
            query = select(AutoresearchExperiment).order_by(
                AutoresearchExperiment.started_at.desc()
            )
            if loop_type:
                query = query.where(AutoresearchExperiment.loop_type == loop_type)
            if kept is not None:
                query = query.where(AutoresearchExperiment.kept == kept)
            query = query.offset(offset).limit(limit)
            result = await db.execute(query)
            return [e.to_dict() for e in result.scalars().all()]

    async def get_leaderboard(self) -> list[dict]:
        """Get best model+temp per skill from model_skill_stats."""
        from sqlalchemy import select

        from app.models.model_skill_stats import ModelSkillStats

        async with async_session() as db:
            result = await db.execute(
                select(ModelSkillStats)
                .where(ModelSkillStats.executions >= 3)
                .order_by(ModelSkillStats.best_quality.desc())
            )
            stats = result.scalars().all()
            # Group by skill, pick best
            best_per_skill: dict[str, dict] = {}
            for s in stats:
                if (
                    s.skill_name not in best_per_skill
                    or s.best_quality > best_per_skill[s.skill_name]["best_quality"]
                ):
                    best_per_skill[s.skill_name] = s.to_dict()
            return list(best_per_skill.values())


# Singleton
autoresearch_engine = AutoresearchEngine()
