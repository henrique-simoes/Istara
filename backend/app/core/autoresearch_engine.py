# Inspired by Karpathy's autoresearch (MIT) — https://github.com/karpathy/autoresearch
"""Autoresearch Engine — greedy hill-climbing optimization loop for UX research.

Implements the hypothesize -> mutate -> evaluate -> keep-or-discard pattern
adapted for 6 UX research optimization domains.
"""

import json
import logging
import statistics
import uuid
from datetime import datetime, timezone

from app.config import settings
from app.core.autoresearch_isolation import autoresearch_context
from app.core.autoresearch_rate_limiter import check_experiment_limit
from app.models.autoresearch_experiment import AutoresearchExperiment
from app.models.database import async_session
from app.models.project import Project

logger = logging.getLogger(__name__)

AUTORESEARCH_SPINE_POLICY = {
    "artifact_role": "governed_improvement_proposal",
    "report_evidence": False,
    "can_bypass_research_spine": False,
    "requires_governed_review": True,
    "summary": (
        "Autoresearch outputs are process proposals and memories only. "
        "They are never accepted Atomic Research artifacts or report evidence."
    ),
}


class AutoresearchEngine:
    """Core optimization loop — all 6 runners use this engine."""

    def __init__(self):
        self._running = False
        self._current_experiment: dict | None = None
        self._active_project_id: str | None = None
        self._stop_requested = False

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def current_experiment(self) -> dict | None:
        return self._current_experiment

    @property
    def active_project_id(self) -> str | None:
        """Project that owns the currently running loop, including baseline measurement."""
        return self._active_project_id if self._running else None

    def get_current_experiment(self) -> dict | None:
        """Return the currently running experiment, or None."""
        return self._current_experiment

    def request_stop(self):
        """Signal the running loop to stop after the current iteration."""
        self._stop_requested = True

    def stop(self):
        """Backward-compatible alias for request_stop."""
        self.request_stop()

    async def run_loop(
        self,
        runner,  # BaseLoopRunner
        target: str,
        max_iterations: int = 20,
        project_id: str = "",
        engine: str | None = None,
    ) -> list[dict]:
        """Run the autoresearch optimization loop.

        ``engine`` is the per-experiment ``pi``|``legacy`` selection resolved at
        the ``/start`` boundary; it is bound into the runner so every migrated
        model call routes on this selection rather than re-reading the global
        feature flag, and it is persisted with each experiment for audit. An
        unset value resolves from ``settings.agentic_core`` (prior behavior).

        Returns list of experiment results.
        """
        from app.core.autoresearch_runners import resolve_engine

        project_id = await self._require_active_project_id(project_id)
        if self._running:
            raise RuntimeError("Engine already running")

        resolved_engine = resolve_engine(engine)

        bind_project = getattr(runner, "bind_project", None)
        if callable(bind_project):
            bind_project(project_id)
        bind_engine = getattr(runner, "bind_engine", None)
        if callable(bind_engine):
            bind_engine(resolved_engine)

        self._running = True
        self._active_project_id = project_id
        self._stop_requested = False
        results: list[dict] = []
        baseline = 0.0
        best_score = baseline
        min_delta = max(0.0, float(getattr(settings, "autoresearch_min_improvement_delta", 0.01)))
        measurement_repeats = max(
            1, min(10, int(getattr(settings, "autoresearch_measurement_repeats", 1)))
        )

        try:
            # Acquire persona lock if needed
            if runner.needs_persona_lock:
                from app.core.agent_identity import acquire_persona_lock

                if not acquire_persona_lock(target, f"autoresearch-{runner.loop_type}"):
                    raise RuntimeError(f"Cannot acquire persona lock for {target}")

            async with autoresearch_context():
                if not await self._is_project_active(project_id):
                    logger.info(
                        "Autoresearch stopped before baseline because project %s is paused or missing",
                        project_id,
                    )
                    return []

                # Measure baseline under isolation so experiment probes cannot
                # pollute learning or self-improvement stores.
                baseline = await runner.measure_baseline(target)
                best_score = baseline
                logger.info(
                    f"Autoresearch [{runner.loop_type}] baseline for '{target}': {baseline:.4f}"
                )

                for i in range(max_iterations):
                    if self._stop_requested:
                        logger.info("Autoresearch stop requested")
                        break
                    if not await self._is_project_active(project_id):
                        logger.info(
                            "Autoresearch stopped before iteration %s because project %s is paused or missing",
                            i + 1,
                            project_id,
                        )
                        break

                    # Check rate limits
                    async with async_session() as db:
                        allowed, reason = await check_experiment_limit(db, target)
                    if not allowed:
                        logger.info(f"Rate limit: {reason}")
                        break

                    # Check mutual exclusion with meta-hyperagent
                    if self._conflicts_with_meta(runner, project_id):
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
                        "project_id": project_id,
                        "engine": resolved_engine,
                        "iteration": i + 1,
                        "baseline_score": best_score,
                        "research_spine_policy": dict(AUTORESEARCH_SPINE_POLICY),
                    }
                    self._current_experiment = experiment

                    try:
                        # Hypothesize
                        hypothesis, mutation = await runner.hypothesize(target, best_score, results)
                        experiment["hypothesis"] = hypothesis
                        experiment["mutation_description"] = str(mutation.get("description", ""))

                        experiment["candidate_mutation"] = mutation
                        experiment["sandboxed"] = True
                        experiment["governance_required"] = True
                        experiment["mutation_live_after_measurement"] = False

                        # Apply mutation only inside the measurement sandbox.
                        # Even "kept" candidates are reverted and become
                        # governed proposals; production state changes happen
                        # only after approval through improvement governance.
                        revert_fn = await runner.apply_mutation(target, mutation)
                        reverted = False

                        # Measure
                        try:
                            measurement = await self._measure_candidate(
                                runner,
                                target,
                                repeats=measurement_repeats,
                            )
                            score = measurement["mean"]
                            delta = score - best_score
                            experiment["experiment_score"] = score
                            experiment["delta"] = delta
                            experiment["score_samples"] = measurement["samples"]
                            experiment["score_stddev"] = measurement["stddev"]
                            experiment["confidence_interval_95"] = measurement[
                                "confidence_interval_95"
                            ]
                            experiment["minimum_delta"] = min_delta
                            experiment["measurement_repeats"] = measurement_repeats

                            # Keep or revert
                            should_keep, decision_reason = self._should_keep_candidate(
                                delta,
                                min_delta=min_delta,
                                confidence_interval_95=measurement["confidence_interval_95"],
                            )
                            await revert_fn()
                            reverted = True
                            experiment["mutation_live_after_measurement"] = False
                            experiment["decision_reason"] = decision_reason
                            if should_keep:
                                best_score = score
                                experiment["kept"] = True
                                experiment["status"] = "proposal_ready"
                                logger.info(
                                    f"  [{i + 1}/{max_iterations}] PROPOSED: "
                                    f"{hypothesis[:60]} "
                                    f"(delta=+{delta:.4f}, reason={decision_reason})"
                                )
                            else:
                                experiment["kept"] = False
                                experiment["status"] = "reverted"
                                logger.info(
                                    f"  [{i + 1}/{max_iterations}] REVERTED: "
                                    f"{hypothesis[:60]} "
                                    f"(delta={delta:.4f}, reason={decision_reason})"
                                )
                        except Exception as e:
                            if not reverted:
                                await revert_fn()
                            experiment["kept"] = False
                            experiment["status"] = "failed"
                            experiment["error_message"] = str(e)[:500]
                            logger.warning(f"  [{i + 1}/{max_iterations}] FAILED: {e}")
                    except Exception as e:
                        experiment["kept"] = False
                        experiment["status"] = "failed"
                        experiment["error_message"] = str(e)[:500]
                        logger.warning(f"  [{i + 1}/{max_iterations}] HYPOTHESIS FAILED: {e}")

                    # Persist experiment
                    experiment["completed_at"] = datetime.now(timezone.utc).isoformat()
                    await self._persist_experiment(experiment, project_id)
                    await self._record_validity_telemetry(experiment, project_id)
                    experiment["reasoning_memory_ids"] = await self._record_reasoning_memory(
                        experiment,
                        project_id,
                    )
                    experiment[
                        "improvement_proposal_ids"
                    ] = await self._register_improvement_proposals(
                        experiment,
                        project_id,
                    )
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
            self._active_project_id = None
            if callable(bind_project):
                bind_project("")
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
                        "project_id": project_id,
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

    async def _require_active_project_id(self, project_id: str) -> str:
        """Validate project ownership before any runner can touch models."""
        scoped_project_id = str(project_id or "").strip()
        if not scoped_project_id:
            raise RuntimeError("project_id is required for autoresearch")
        if not await self._is_project_active(scoped_project_id):
            raise RuntimeError("Project is paused or not found")
        return scoped_project_id

    async def _is_project_active(self, project_id: str) -> bool:
        async with async_session() as db:
            project = await db.get(Project, project_id)
            return bool(project and not project.is_paused)

    async def _measure_candidate(self, runner, target: str, repeats: int) -> dict:
        """Measure a candidate once or repeatedly and summarize uncertainty."""
        samples = [float(await runner.measure(target)) for _ in range(repeats)]
        mean = statistics.fmean(samples)
        stddev = statistics.stdev(samples) if len(samples) > 1 else 0.0
        confidence_interval_95 = (
            1.96 * (stddev / (len(samples) ** 0.5)) if len(samples) > 1 else None
        )
        return {
            "samples": samples,
            "mean": mean,
            "stddev": stddev,
            "confidence_interval_95": confidence_interval_95,
        }

    def _should_keep_candidate(
        self,
        delta: float,
        *,
        min_delta: float,
        confidence_interval_95: float | None,
    ) -> tuple[bool, str]:
        """Use a conservative improvement rule instead of accepting any noise."""
        if delta < min_delta:
            return False, f"delta {delta:.4f} below minimum {min_delta:.4f}"
        if confidence_interval_95 is not None and delta <= confidence_interval_95:
            return (
                False,
                f"delta {delta:.4f} does not exceed 95% CI half-width {confidence_interval_95:.4f}",
            )
        return True, "delta exceeds configured minimum and uncertainty guard"

    def _conflicts_with_meta(self, runner, project_id: str) -> bool:
        """Check if meta-hyperagent has active variants on parameters this runner modifies."""
        try:
            from app.core.meta_hyperagent import meta_hyperagent

            if not settings.meta_hyperagent_enabled:
                return False
            variants = meta_hyperagent.get_active_variants(project_id=project_id)
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
                engine=experiment.get("engine"),
                config_snapshot=json.dumps(
                    {
                        "engine": experiment.get("engine"),
                        "measurement_repeats": experiment.get("measurement_repeats"),
                        "score_samples": experiment.get("score_samples"),
                        "score_stddev": experiment.get("score_stddev"),
                        "confidence_interval_95": experiment.get("confidence_interval_95"),
                        "minimum_delta": experiment.get("minimum_delta"),
                        "decision_reason": experiment.get("decision_reason"),
                        "sandboxed": experiment.get("sandboxed"),
                        "governance_required": experiment.get("governance_required"),
                        "mutation_live_after_measurement": experiment.get(
                            "mutation_live_after_measurement"
                        ),
                    }
                ),
                error_message=experiment.get("error_message", ""),
                project_id=project_id,
                completed_at=datetime.now(timezone.utc),
            )
            db.add(record)
            await db.commit()

    async def _record_reasoning_memory(self, experiment: dict, project_id: str) -> list[str]:
        """Distill an autoresearch experiment into reusable ReasoningBank memory."""
        try:
            from app.core.reasoning_bank import reasoning_bank

            memories = await reasoning_bank.record_autoresearch_experiment(
                experiment,
                project_id=project_id,
            )
            return [memory["id"] for memory in memories if memory.get("id")]
        except Exception as exc:
            logger.debug(f"Autoresearch ReasoningBank record skipped: {exc}")
            return []

    async def _record_validity_telemetry(self, experiment: dict, project_id: str) -> None:
        """Record content-free telemetry for governed autoresearch updates."""
        try:
            from app.core.telemetry import telemetry_recorder

            kept = bool(experiment.get("kept"))
            score = experiment.get("experiment_score")
            await telemetry_recorder.record_research_validity_event(
                operation="autoresearch.validity_update",
                project_id=project_id,
                agent_id="autoresearch",
                skill_name=str(experiment.get("loop_type", "")),
                status="success" if kept else "degraded",
                quality_score=score if isinstance(score, (int, float)) else None,
                error_type=None if kept else "autoresearch_candidate_not_kept",
            )
        except Exception as exc:
            logger.debug(f"Autoresearch validity telemetry skipped: {exc}")

    async def _register_improvement_proposals(self, experiment: dict, project_id: str) -> list[str]:
        """Register kept autoresearch candidates in the governance promotion lane."""
        try:
            from app.core.improvement_governance import improvement_governance

            return await improvement_governance.register_autoresearch_experiment(
                experiment,
                project_id=project_id,
                reasoning_memory_ids=experiment.get("reasoning_memory_ids", []),
            )
        except Exception as exc:
            logger.debug(f"Autoresearch governance registration skipped: {exc}")
            return []

    async def get_experiments(
        self,
        project_id: str,
        loop_type: str | None = None,
        kept: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """Get experiment history."""
        from sqlalchemy import select

        async with async_session() as db:
            query = (
                select(AutoresearchExperiment)
                .order_by(AutoresearchExperiment.started_at.desc())
                .where(AutoresearchExperiment.project_id == project_id)
            )
            if loop_type:
                query = query.where(AutoresearchExperiment.loop_type == loop_type)
            if kept is not None:
                query = query.where(AutoresearchExperiment.kept == kept)
            query = query.offset(offset).limit(limit)
            result = await db.execute(query)
            return [e.to_dict() for e in result.scalars().all()]

    async def get_experiment(self, experiment_id: str) -> dict | None:
        """Get one experiment by ID."""
        from sqlalchemy import select

        async with async_session() as db:
            result = await db.execute(
                select(AutoresearchExperiment).where(AutoresearchExperiment.id == experiment_id)
            )
            record = result.scalar_one_or_none()
            return record.to_dict() if record else None

    async def get_leaderboard(self, project_id: str) -> list[dict]:
        """Get best model+temp per skill from project-scoped telemetry."""
        from sqlalchemy import func, select

        from app.models.telemetry_span import TelemetrySpan

        async with async_session() as db:
            result = await db.execute(
                select(
                    TelemetrySpan.skill_name,
                    TelemetrySpan.model_name,
                    func.coalesce(TelemetrySpan.temperature, 0.0),
                    func.count(TelemetrySpan.id),
                    func.avg(TelemetrySpan.quality_score),
                    func.max(TelemetrySpan.quality_score),
                )
                .where(
                    TelemetrySpan.project_id == project_id,
                    TelemetrySpan.skill_name != "",
                    TelemetrySpan.model_name != "",
                    TelemetrySpan.quality_score.is_not(None),
                )
                .group_by(
                    TelemetrySpan.skill_name,
                    TelemetrySpan.model_name,
                    TelemetrySpan.temperature,
                )
                .having(func.count(TelemetrySpan.id) >= 3)
                .order_by(func.max(TelemetrySpan.quality_score).desc())
            )
            stats = result.all()
            # Group by skill, pick best
            best_per_skill: dict[str, dict] = {}
            for s in stats:
                skill_name = str(s[0] or "")
                model_name = str(s[1] or "")
                avg_quality = float(s[4] or 0.0)
                best_quality = float(s[5] or 0.0)
                entry = {
                    "skill_name": skill_name,
                    "model_name": model_name,
                    "temperature": float(s[2] or 0.0),
                    "executions": int(s[3] or 0),
                    "avg_quality": avg_quality,
                    "quality_ema": avg_quality,
                    "best_quality": best_quality,
                }
                if (
                    skill_name not in best_per_skill
                    or best_quality > best_per_skill[skill_name]["best_quality"]
                ):
                    best_per_skill[skill_name] = entry
            return list(best_per_skill.values())


# Singleton
autoresearch_engine = AutoresearchEngine()
