"""Autoresearch API routes — automated experiment loops for self-improvement.

Inspired by Karpathy's autoresearch (MIT) — https://github.com/karpathy/autoresearch
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security_middleware import require_admin_from_request
from app.models.database import get_db
from app.models.agent import Agent, AgentState, HeartbeatStatus
from app.models.code_application import CodeApplication
from app.models.document import Document, DocumentStatus
from app.models.finding import Fact, Insight, Nugget, Recommendation
from app.models.method_metric import MethodMetric
from app.models.model_skill_stats import ModelSkillStats
from app.models.research_deployment import ResearchDeployment
from app.models.survey_integration import SurveyIntegration, SurveyLink
from app.models.task import Task, TaskStatus
from app.models.task_review import TaskReviewEvent
from app.models.telemetry_span import TelemetrySpan

router = APIRouter(prefix="/autoresearch")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class StartExperimentRequest(BaseModel):
    loop_type: str  # skill_prompt|model_temp|rag_params|persona|question_bank|ui_sim
    target: str  # skill name, agent id, deployment id, or component path
    max_iterations: int = 20
    project_id: str = ""


class ConfigUpdate(BaseModel):
    enabled: bool | None = None
    max_experiments_per_run: int | None = None
    max_daily_experiments: int | None = None
    min_improvement_delta: float | None = None
    measurement_repeats: int | None = None


class ToggleRequest(BaseModel):
    enabled: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_engine():
    """Lazy-import the autoresearch engine singleton."""
    try:
        from app.core.autoresearch_engine import autoresearch_engine
        return autoresearch_engine
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="Autoresearch engine not available. Ensure app.core.autoresearch_engine is installed.",
        )


def _get_runner(loop_type: str):
    """Lazy-import a runner by loop type."""
    runner_map = {
        "model_temp": ("app.core.autoresearch_runners.model_temp", "ModelTempRunner"),
        "skill_prompt": ("app.core.autoresearch_runners.skill_prompt", "SkillPromptRunner"),
        "rag_params": ("app.core.autoresearch_runners.rag_params", "RAGParamsRunner"),
        "persona": ("app.core.autoresearch_runners.persona", "PersonaRunner"),
        "question_bank": ("app.core.autoresearch_runners.question_bank", "QuestionBankRunner"),
        "ui_sim": ("app.core.autoresearch_runners.ui_sim", "UISimRunner"),
    }
    runner_spec = runner_map.get(loop_type)
    if not runner_spec:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown loop type: {loop_type}. Valid types: {', '.join(runner_map.keys())}",
        )
    module_path, class_name = runner_spec
    try:
        import importlib
        mod = importlib.import_module(module_path)
        runner_cls = getattr(mod, class_name)
        return runner_cls()
    except (AttributeError, ImportError, TypeError) as exc:
        logger.warning("Autoresearch runner load failed for %s: %s", loop_type, exc)
        raise HTTPException(
            status_code=501,
            detail=f"Runner for loop type '{loop_type}' is not installed.",
        )


def _clamp_iterations(requested: int) -> int:
    """Clamp requested iterations to configured production limits."""
    max_per_run = max(1, int(getattr(settings, "autoresearch_max_experiments_per_run", 20)))
    return max(1, min(int(requested or 1), max_per_run))


async def _build_operational_metrics(db: AsyncSession) -> dict:
    """Summarize operational signals that AutoResearch can use."""
    total_tasks = await db.scalar(select(func.count(Task.id))) or 0
    done_tasks = (
        await db.scalar(select(func.count(Task.id)).where(Task.status == TaskStatus.DONE))
    ) or 0
    in_review_tasks = (
        await db.scalar(select(func.count(Task.id)).where(Task.status == TaskStatus.IN_REVIEW))
    ) or 0
    needs_revision_tasks = (
        await db.scalar(
            select(func.count(Task.id)).where(
                Task.review_state.in_(("needs_revision", "rejected_after_done", "system_failed"))
            )
        )
    ) or 0
    approved_tasks = (
        await db.scalar(select(func.count(Task.id)).where(Task.review_state == "approved"))
    ) or 0
    total_review_cycles = await db.scalar(select(func.coalesce(func.sum(Task.review_cycle_count), 0))) or 0
    avg_feedback = await db.scalar(
        select(func.avg(Task.human_feedback_score)).where(Task.human_feedback_score.is_not(None))
    )
    avg_consensus = await db.scalar(
        select(func.avg(Task.consensus_score)).where(Task.consensus_score.is_not(None))
    )
    validation_method_rows = (
        (
            await db.execute(
                select(
                    MethodMetric.method,
                    func.sum(MethodMetric.total_runs),
                    func.sum(MethodMetric.success_count),
                    func.sum(MethodMetric.fail_count),
                    func.avg(MethodMetric.avg_consensus_score),
                ).group_by(MethodMetric.method)
            )
        )
        .all()
    )
    validation_method_stats = [
        {
            "method": row[0],
            "total_runs": int(row[1] or 0),
            "success_count": int(row[2] or 0),
            "fail_count": int(row[3] or 0),
            "avg_consensus_score": round(float(row[4]), 2) if row[4] is not None else None,
            "success_rate": round((row[2] or 0) / max(row[1] or 0, 1) * 100, 1),
        }
        for row in validation_method_rows
    ]
    validation_runs = sum(row["total_runs"] for row in validation_method_stats)
    validation_successes = sum(row["success_count"] for row in validation_method_stats)
    review_events = await db.scalar(select(func.count(TaskReviewEvent.id))) or 0
    approval_events = (
        await db.scalar(select(func.count(TaskReviewEvent.id)).where(TaskReviewEvent.outcome == "approved"))
    ) or 0
    revision_events = (
        await db.scalar(
            select(func.count(TaskReviewEvent.id)).where(
                TaskReviewEvent.outcome.in_(("needs_revision", "rejected_after_done", "system_failed"))
            )
        )
    ) or 0

    total_agents = await db.scalar(select(func.count(Agent.id))) or 0
    active_agents = await db.scalar(select(func.count(Agent.id)).where(Agent.is_active.is_(True))) or 0
    working_agents = await db.scalar(select(func.count(Agent.id)).where(Agent.state == AgentState.WORKING)) or 0
    paused_agents = await db.scalar(select(func.count(Agent.id)).where(Agent.state == AgentState.PAUSED)) or 0
    agent_errors = await db.scalar(select(func.coalesce(func.sum(Agent.error_count), 0))) or 0
    agent_executions = await db.scalar(select(func.coalesce(func.sum(Agent.executions), 0))) or 0
    unhealthy_heartbeats = (
        await db.scalar(
            select(func.count(Agent.id)).where(
                Agent.heartbeat_status.in_((HeartbeatStatus.DEGRADED, HeartbeatStatus.ERROR, HeartbeatStatus.STOPPED))
            )
        )
    ) or 0

    total_documents = await db.scalar(select(func.count(Document.id))) or 0
    ready_documents = await db.scalar(select(func.count(Document.id)).where(Document.status == DocumentStatus.READY)) or 0
    errored_documents = await db.scalar(select(func.count(Document.id)).where(Document.status == DocumentStatus.ERROR)) or 0
    indexed_text_documents = (
        await db.scalar(select(func.count(Document.id)).where(Document.content_text != ""))
    ) or 0
    total_findings = sum(
        [
            await db.scalar(select(func.count(Nugget.id))) or 0,
            await db.scalar(select(func.count(Fact.id))) or 0,
            await db.scalar(select(func.count(Insight.id))) or 0,
            await db.scalar(select(func.count(Recommendation.id))) or 0,
        ]
    )
    avg_insight_confidence = await db.scalar(select(func.avg(Insight.confidence)))

    total_code_applications = await db.scalar(select(func.count(CodeApplication.id))) or 0
    pending_code_reviews = (
        await db.scalar(select(func.count(CodeApplication.id)).where(CodeApplication.review_status == "pending"))
    ) or 0
    approved_code_reviews = (
        await db.scalar(select(func.count(CodeApplication.id)).where(CodeApplication.review_status == "approved"))
    ) or 0

    recent_cutoff = datetime.now(timezone.utc) - timedelta(days=1)
    total_spans = await db.scalar(select(func.count(TelemetrySpan.id))) or 0
    spans_last_24h = (
        await db.scalar(select(func.count(TelemetrySpan.id)).where(TelemetrySpan.created_at >= recent_cutoff))
    ) or 0
    error_spans_last_24h = (
        await db.scalar(
            select(func.count(TelemetrySpan.id)).where(
                TelemetrySpan.created_at >= recent_cutoff,
                TelemetrySpan.status.in_(("error", "timeout")),
            )
        )
    ) or 0
    avg_quality_24h = await db.scalar(
        select(func.avg(TelemetrySpan.quality_score)).where(
            TelemetrySpan.created_at >= recent_cutoff,
            TelemetrySpan.quality_score.is_not(None),
        )
    )
    total_model_entries = await db.scalar(select(func.count(ModelSkillStats.id))) or 0
    production_model_entries = (
        await db.scalar(select(func.count(ModelSkillStats.id)).where(ModelSkillStats.source == "production"))
    ) or 0
    autoresearch_model_entries = (
        await db.scalar(select(func.count(ModelSkillStats.id)).where(ModelSkillStats.source == "autoresearch"))
    ) or 0
    avg_model_quality = await db.scalar(select(func.avg(ModelSkillStats.quality_ema)))
    best_model_quality = await db.scalar(select(func.max(ModelSkillStats.best_quality)))

    total_deployments = await db.scalar(select(func.count(ResearchDeployment.id))) or 0
    active_deployments = (
        await db.scalar(select(func.count(ResearchDeployment.id)).where(ResearchDeployment.state == "active"))
    ) or 0
    deployment_responses = await db.scalar(select(func.coalesce(func.sum(ResearchDeployment.current_responses), 0))) or 0
    deployment_targets = await db.scalar(select(func.coalesce(func.sum(ResearchDeployment.target_responses), 0))) or 0
    survey_integrations = await db.scalar(select(func.count(SurveyIntegration.id))) or 0
    active_survey_integrations = (
        await db.scalar(select(func.count(SurveyIntegration.id)).where(SurveyIntegration.is_active.is_(True)))
    ) or 0
    survey_links = await db.scalar(select(func.count(SurveyLink.id))) or 0
    survey_responses = await db.scalar(select(func.coalesce(func.sum(SurveyLink.response_count), 0))) or 0

    try:
        from app.core.scheduler import ScheduledTask

        total_schedules = await db.scalar(select(func.count(ScheduledTask.id))) or 0
        active_schedules = (
            await db.scalar(select(func.count(ScheduledTask.id)).where(ScheduledTask.enabled.is_(True)))
        ) or 0
        running_schedules = (
            await db.scalar(select(func.count(ScheduledTask.id)).where(ScheduledTask.is_running.is_(True)))
        ) or 0
        schedule_executions = await db.scalar(select(func.coalesce(func.sum(ScheduledTask.execution_count), 0))) or 0
    except Exception:
        total_schedules = active_schedules = running_schedules = schedule_executions = 0

    from app.core.compute_registry import compute_registry

    compute_stats = compute_registry.get_stats()
    nodes = compute_stats.get("nodes", [])
    healthy_nodes = [
        node
        for node in nodes
        if node.get("is_healthy") or node.get("health_state") == "ready"
    ]
    available_models = sorted(
        {
            model
            for node in healthy_nodes
            for model in (node.get("loaded_models") or [])
            if isinstance(model, str) and model
        }
    )

    return {
        "tasks": {
            "total": total_tasks,
            "done": done_tasks,
            "in_review": in_review_tasks,
            "approved": approved_tasks,
            "needs_revision": needs_revision_tasks,
            "review_events": review_events,
            "approval_events": approval_events,
            "revision_events": revision_events,
            "review_cycles": total_review_cycles,
            "completion_rate": round(done_tasks / max(total_tasks, 1) * 100, 1),
            "approval_rate": round(approval_events / max(review_events, 1) * 100, 1),
            "avg_human_feedback": round(float(avg_feedback), 2) if avg_feedback is not None else None,
            "avg_consensus": round(float(avg_consensus), 2) if avg_consensus is not None else None,
            "validation_runs": validation_runs,
            "validation_success_rate": round(validation_successes / max(validation_runs, 1) * 100, 1),
            "validation_methods": validation_method_stats,
        },
        "agents": {
            "total": total_agents,
            "active": active_agents,
            "working": working_agents,
            "paused": paused_agents,
            "unhealthy_heartbeats": unhealthy_heartbeats,
            "executions": agent_executions,
            "errors": agent_errors,
            "error_rate": round(agent_errors / max(agent_executions, 1) * 100, 1),
        },
        "research_pipeline": {
            "documents": total_documents,
            "ready_documents": ready_documents,
            "errored_documents": errored_documents,
            "indexed_text_documents": indexed_text_documents,
            "findings": total_findings,
            "avg_insight_confidence": round(float(avg_insight_confidence), 2) if avg_insight_confidence is not None else None,
            "code_applications": total_code_applications,
            "pending_code_reviews": pending_code_reviews,
            "approved_code_reviews": approved_code_reviews,
        },
        "telemetry": {
            "enabled": settings.telemetry_enabled,
            "total_spans": total_spans,
            "spans_last_24h": spans_last_24h,
            "errors_last_24h": error_spans_last_24h,
            "error_rate_24h": round(error_spans_last_24h / max(spans_last_24h, 1) * 100, 1),
            "avg_quality_24h": round(float(avg_quality_24h), 2) if avg_quality_24h is not None else None,
            "model_entries": total_model_entries,
            "production_model_entries": production_model_entries,
            "autoresearch_model_entries": autoresearch_model_entries,
            "avg_model_quality": round(float(avg_model_quality), 2) if avg_model_quality is not None else None,
            "best_model_quality": round(float(best_model_quality), 2) if best_model_quality is not None else None,
        },
        "loops": {
            "total_schedules": total_schedules,
            "active_schedules": active_schedules,
            "running_schedules": running_schedules,
            "schedule_executions": schedule_executions,
        },
        "research_collection": {
            "deployments": total_deployments,
            "active_deployments": active_deployments,
            "deployment_responses": deployment_responses,
            "deployment_targets": deployment_targets,
            "deployment_completion_rate": round(deployment_responses / max(deployment_targets, 1) * 100, 1),
            "survey_integrations": survey_integrations,
            "active_survey_integrations": active_survey_integrations,
            "survey_links": survey_links,
            "survey_responses": survey_responses,
        },
        "compute_pool": {
            "total_nodes": compute_stats.get("total_nodes", 0),
            "alive_nodes": compute_stats.get("alive_nodes", 0),
            "healthy_nodes": len(healthy_nodes),
            "available_models": available_models,
            "available_model_count": len(available_models),
            "active_requests": compute_stats.get("active_requests", 0),
        },
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/status")
async def autoresearch_status(request: Request, db: AsyncSession = Depends(get_db)):
    """Get autoresearch engine status and current experiment."""
    require_admin_from_request(request)
    engine = _get_engine()
    current = engine.get_current_experiment()
    return {
        "running": engine.is_running,
        "enabled": getattr(settings, "autoresearch_enabled", False),
        "current_experiment": current,
        "operational_metrics": await _build_operational_metrics(db),
    }


@router.get("/experiments")
async def list_experiments(
    request: Request,
    loop_type: Optional[str] = None,
    kept: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
):
    """Get paginated experiment history with optional filters."""
    require_admin_from_request(request)
    engine = _get_engine()
    experiments = await engine.get_experiments(
        loop_type=loop_type,
        kept=kept,
        limit=limit,
        offset=offset,
    )
    return experiments


@router.get("/experiments/{experiment_id}")
async def get_experiment(experiment_id: str, request: Request):
    """Get a single experiment by ID."""
    require_admin_from_request(request)
    engine = _get_engine()
    experiment = await engine.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return experiment


@router.post("/start")
async def start_experiment(body: StartExperimentRequest, request: Request, background_tasks: BackgroundTasks):
    """Start an autoresearch experiment loop in the background."""
    require_admin_from_request(request)
    engine = _get_engine()

    if engine.is_running:
        raise HTTPException(
            status_code=409,
            detail="An experiment loop is already running. Stop it first.",
        )

    if not getattr(settings, "autoresearch_enabled", False):
        raise HTTPException(
            status_code=403,
            detail="Autoresearch is disabled. Enable it first via /api/autoresearch/toggle.",
        )

    runner = _get_runner(body.loop_type)
    max_iterations = _clamp_iterations(body.max_iterations)

    async def _run_loop():
        try:
            await engine.run_loop(
                runner=runner,
                target=body.target,
                max_iterations=max_iterations,
                project_id=body.project_id,
            )
        except Exception as exc:
            logger.error(f"Autoresearch loop failed: {exc}", exc_info=True)

    background_tasks.add_task(_run_loop)

    return {
        "status": "started",
        "loop_type": body.loop_type,
        "target": body.target,
        "max_iterations": max_iterations,
    }


@router.post("/stop")
async def stop_experiment(request: Request):
    """Stop the currently running experiment loop."""
    require_admin_from_request(request)
    engine = _get_engine()

    if not engine.is_running:
        raise HTTPException(status_code=409, detail="No experiment loop is currently running.")

    engine.request_stop()
    return {"status": "stopped"}


@router.get("/config")
async def get_config(request: Request):
    """Get autoresearch configuration."""
    require_admin_from_request(request)
    return {
        "enabled": getattr(settings, "autoresearch_enabled", False),
        "max_experiments_per_run": getattr(settings, "autoresearch_max_experiments_per_run", 20),
        "max_daily_experiments": getattr(settings, "autoresearch_max_daily_experiments", 100),
        "min_improvement_delta": getattr(settings, "autoresearch_min_improvement_delta", 0.01),
        "measurement_repeats": getattr(settings, "autoresearch_measurement_repeats", 1),
    }


@router.patch("/config")
async def update_config(body: ConfigUpdate, request: Request):
    """Update autoresearch configuration."""
    require_admin_from_request(request)
    if body.enabled is not None:
        settings.autoresearch_enabled = body.enabled
    if body.max_experiments_per_run is not None:
        if body.max_experiments_per_run < 1 or body.max_experiments_per_run > 100:
            raise HTTPException(status_code=400, detail="max_experiments_per_run must be between 1 and 100")
        settings.autoresearch_max_experiments_per_run = body.max_experiments_per_run
    if body.max_daily_experiments is not None:
        if body.max_daily_experiments < 1 or body.max_daily_experiments > 1000:
            raise HTTPException(status_code=400, detail="max_daily_experiments must be between 1 and 1000")
        settings.autoresearch_max_daily_experiments = body.max_daily_experiments
    if body.min_improvement_delta is not None:
        if body.min_improvement_delta < 0 or body.min_improvement_delta > 1:
            raise HTTPException(status_code=400, detail="min_improvement_delta must be between 0 and 1")
        settings.autoresearch_min_improvement_delta = body.min_improvement_delta
    if body.measurement_repeats is not None:
        if body.measurement_repeats < 1 or body.measurement_repeats > 10:
            raise HTTPException(status_code=400, detail="measurement_repeats must be between 1 and 10")
        settings.autoresearch_measurement_repeats = body.measurement_repeats

    return {
        "enabled": getattr(settings, "autoresearch_enabled", False),
        "max_experiments_per_run": getattr(settings, "autoresearch_max_experiments_per_run", 20),
        "max_daily_experiments": getattr(settings, "autoresearch_max_daily_experiments", 100),
        "min_improvement_delta": getattr(settings, "autoresearch_min_improvement_delta", 0.01),
        "measurement_repeats": getattr(settings, "autoresearch_measurement_repeats", 1),
    }


@router.get("/leaderboard")
async def get_leaderboard(request: Request):
    """Get best model+temperature leaderboard per skill."""
    require_admin_from_request(request)
    engine = _get_engine()
    return await engine.get_leaderboard()


@router.post("/toggle")
async def toggle_autoresearch(body: ToggleRequest, request: Request):
    """Enable or disable autoresearch."""
    require_admin_from_request(request)
    settings.autoresearch_enabled = body.enabled

    engine = _get_engine()
    if not body.enabled and engine.is_running:
        engine.request_stop()

    return {
        "enabled": body.enabled,
        "message": f"Autoresearch {'enabled' if body.enabled else 'disabled'}",
    }
