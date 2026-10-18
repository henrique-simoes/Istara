# Inspired by Karpathy's autoresearch (MIT) — https://github.com/karpathy/autoresearch
"""Autoresearch Engine — greedy hill-climbing optimization loop for UX research.

Implements the hypothesize -> mutate -> evaluate -> keep-or-discard pattern
adapted for 6 UX research optimization domains.
"""

import json
import logging
import statistics
import uuid
from datetime import UTC, datetime

from app.config import settings
from app.core.autoresearch_isolation import autoresearch_context
from app.core.autoresearch_statistics import MIN_SAMPLES, keep_decision
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
        # At least two samples per side: a single sample has no variance, so noise would pass as
        # improvement (AR-2). The setting can raise this, never lower it below two.
        measurement_repeats = max(
            MIN_SAMPLES,
            min(10, int(getattr(settings, "autoresearch_measurement_repeats", MIN_SAMPLES))),
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
                        "Autoresearch stopped before baseline "
                        "because project %s is paused or missing",
                        project_id,
                    )
                    return []

                # Measure the baseline under isolation so experiment probes cannot pollute
                # learning or self-improvement stores. Every candidate is reverted, so the
                # incumbent is always this unmutated state (AR-1).
                baseline_samples = await self._baseline_samples(runner, target, measurement_repeats)
                if baseline_samples is None:
                    logger.info("Autoresearch [%s]: baseline not measurable", runner.loop_type)
                    return []
                baseline = statistics.fmean(baseline_samples)
                best_score = baseline
                logger.info(
                    f"Autoresearch [{runner.loop_type}] baseline for '{target}': {baseline:.4f}"
                )

                for i in range(max_iterations):
                    if not await self._may_continue(project_id, target, i):
                        break
                    experiment = await self._run_iteration(
                        runner,
                        target,
                        iteration=i + 1,
                        project_id=project_id,
                        engine=resolved_engine,
                        baseline_samples=baseline_samples,
                        repeats=measurement_repeats,
                        min_delta=min_delta,
                        history=results,
                    )
                    if experiment.get("kept"):
                        best_score = max(best_score, experiment.get("experiment_score") or 0.0)
                    await self._finish_experiment(experiment, project_id)
                    results.append(experiment)

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
            _close_runner(runner)
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

    async def _may_continue(self, project_id: str, target: str, index: int) -> bool:
        if self._stop_requested:
            logger.info("Autoresearch stop requested")
            return False
        if not await self._is_project_active(project_id):
            logger.info(
                "Autoresearch stopped before iteration %s because project %s is paused or missing",
                index + 1,
                project_id,
            )
            return False
        async with async_session() as db:
            allowed, reason = await check_experiment_limit(db, target)
        if not allowed:
            logger.info(f"Rate limit: {reason}")
            return False
        return True

    @staticmethod
    async def _samples(measure, target: str, repeats: int) -> list[float] | None:
        """``repeats`` measurements, or None as soon as one could not be measured (AR-4)."""
        samples: list[float] = []
        for _ in range(repeats):
            value = await measure(target)
            if value is None:
                return None
            samples.append(float(value))
        return samples

    async def _baseline_samples(self, runner, target: str, repeats: int) -> list[float] | None:
        first = await runner.measure_baseline(target)
        if first is None:
            return None
        extra_measure = getattr(runner, "measure_incumbent", None) or runner.measure_baseline
        extra = await self._samples(extra_measure, target, repeats - 1)
        return None if extra is None else [float(first), *extra]

    async def _run_iteration(
        self,
        runner,
        target: str,
        *,
        iteration: int,
        project_id: str,
        engine: str,
        baseline_samples: list[float],
        repeats: int,
        min_delta: float,
        history: list[dict],
    ) -> dict:
        experiment: dict = {
            "id": str(uuid.uuid4()),
            "loop_type": runner.loop_type,
            "target_name": target,
            "project_id": project_id,
            "engine": engine,
            "iteration": iteration,
            "research_spine_policy": dict(AUTORESEARCH_SPINE_POLICY),
            "sandboxed": True,
            "governance_required": True,
            "mutation_live_after_measurement": False,
            "kept": False,
            "minimum_delta": min_delta,
            "measurement_repeats": repeats,
        }
        self._current_experiment = experiment
        if self._conflicts_with_meta(runner, project_id):
            experiment["status"] = "skipped_meta_conflict"
            experiment["decision_reason"] = "meta-hyperagent has an active variant on them"
            return experiment
        incumbent_measure = getattr(runner, "measure_incumbent", None)
        incumbent = (
            await self._samples(incumbent_measure, target, repeats)
            if incumbent_measure
            else list(baseline_samples)
        )
        if incumbent is None:
            return self._not_runnable(experiment, "incumbent not measurable")
        experiment["incumbent_samples"] = incumbent
        experiment["baseline_score"] = statistics.fmean(incumbent)
        try:
            hypothesis, mutation = await runner.hypothesize(
                target, experiment["baseline_score"], history
            )
        except Exception as e:
            experiment["status"] = "failed"
            experiment["error_message"] = str(e)[:500]
            logger.warning(f"  [{iteration}] HYPOTHESIS FAILED: {e}")
            return experiment
        experiment["hypothesis"] = hypothesis
        experiment["mutation_description"] = str(mutation.get("description", ""))
        experiment["candidate_mutation"] = mutation
        # Apply the mutation only inside the measurement sandbox. Even kept candidates are
        # reverted and become governed proposals; production changes need approval.
        revert_fn = await runner.apply_mutation(target, mutation)
        try:
            await self._measure_candidate_block(runner, target, experiment, incumbent)
        except Exception as e:
            experiment["kept"] = False
            experiment["status"] = "failed"
            experiment["error_message"] = str(e)[:500]
            logger.warning(f"  [{iteration}] FAILED: {e}")
        finally:
            await revert_fn()
        logger.info(
            "  [%s] %s: %s (%s)",
            iteration,
            experiment.get("status"),
            str(hypothesis)[:60],
            experiment.get("decision_reason", ""),
        )
        return experiment

    async def _measure_candidate_block(
        self, runner, target: str, experiment: dict, incumbent: list[float]
    ) -> None:
        """Measure and decide; confirm a kept candidate on an independent block (winner's curse)."""
        repeats = experiment["measurement_repeats"]
        candidate = await self._samples(runner.measure, target, repeats)
        if candidate is None:
            self._not_runnable(experiment, "candidate not measurable")
            return
        keep, reason, comparison = keep_decision(incumbent, candidate, experiment["minimum_delta"])
        experiment["score_samples"] = candidate
        experiment["experiment_score"] = statistics.fmean(candidate)
        experiment["score_stddev"] = statistics.stdev(candidate)
        if comparison is not None:
            experiment["delta"] = comparison.delta
            experiment["delta_ci_95"] = [comparison.low, comparison.high]
            experiment["confidence_interval_95"] = (comparison.high - comparison.low) / 2.0
        if keep:
            confirmation = await self._samples(runner.measure, target, repeats)
            if confirmation is None:
                keep, reason = False, "confirmation block not measurable"
            else:
                confirmed, why, second = keep_decision(
                    incumbent, confirmation, experiment["minimum_delta"]
                )
                experiment["confirmation_samples"] = confirmation
                experiment["confirmation_ci_95"] = [second.low, second.high] if second else None
                if not confirmed:
                    keep, reason = False, f"not confirmed on an independent block: {why}"
        experiment["kept"] = keep
        experiment["status"] = "proposal_ready" if keep else "reverted"
        experiment["decision_reason"] = reason

    @staticmethod
    def _not_runnable(experiment: dict, reason: str) -> dict:
        experiment["kept"] = False
        experiment["status"] = "not_runnable"
        experiment["decision_reason"] = reason
        return experiment

    async def _finish_experiment(self, experiment: dict, project_id: str) -> None:
        """Persist, record telemetry and memory, register proposals, and broadcast."""
        experiment["completed_at"] = datetime.now(UTC).isoformat()
        await self._persist_experiment(experiment, project_id)
        await self._record_validity_telemetry(experiment, project_id)
        experiment["reasoning_memory_ids"] = await self._record_reasoning_memory(
            experiment,
            project_id,
        )
        experiment["improvement_proposal_ids"] = await self._register_improvement_proposals(
            experiment,
            project_id,
        )
        try:
            from app.api.websocket import manager

            await manager.broadcast("autoresearch_progress", experiment)
        except Exception:
            pass

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

    def _should_keep_candidate(
        self, incumbent: list[float], candidate: list[float], *, min_delta: float
    ) -> tuple[bool, str]:
        """Keep only when the 95% Welch interval of the gain clears ``min_delta``."""
        keep, reason, _ = keep_decision(incumbent, candidate, min_delta)
        return keep, reason

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
                "decision_policy": [],
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
                mutation_diff=json.dumps(experiment.get("candidate_mutation", {}), default=str),
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
                completed_at=datetime.now(UTC),
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
        """Best model+temp per skill from project-scoped telemetry, by a 95% lower bound.

        Ranking by the single best score rewarded one lucky sample (AR-8). The lower bound of the
        mean (normal approximation, at least 3 executions) rewards consistent quality.
        """
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
                    func.avg(TelemetrySpan.quality_score * TelemetrySpan.quality_score),
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
            )
            stats = result.all()
            # Group by skill, pick best
            best_per_skill: dict[str, dict] = {}
            for s in stats:
                skill_name = str(s[0] or "")
                model_name = str(s[1] or "")
                avg_quality = float(s[4] or 0.0)
                best_quality = float(s[5] or 0.0)
                executions = int(s[3] or 0)
                variance = max(0.0, float(s[6] or 0.0) - avg_quality**2)
                lower = avg_quality - 1.96 * (variance / max(1, executions)) ** 0.5
                entry = {
                    "skill_name": skill_name,
                    "model_name": model_name,
                    "temperature": float(s[2] or 0.0),
                    "executions": executions,
                    "avg_quality": avg_quality,
                    # Kept for older readers; it is the plain mean, not an exponential average.
                    "quality_ema": avg_quality,
                    "best_quality": best_quality,
                    "quality_lower_bound_95": lower,
                }
                if (
                    skill_name not in best_per_skill
                    or lower > best_per_skill[skill_name]["quality_lower_bound_95"]
                ):
                    best_per_skill[skill_name] = entry
            return list(best_per_skill.values())


# Singleton
autoresearch_engine = AutoresearchEngine()


def _close_runner(runner: object) -> None:
    """Runners that measure on sandboxes (rag_params) remove them when the loop ends."""
    close_runner = getattr(runner, "close", None)
    if callable(close_runner):
        try:
            close_runner()
        except Exception as exc:
            logger.debug("Runner close skipped: %s", exc)
