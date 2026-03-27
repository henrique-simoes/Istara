"""Autoresearch API routes — automated experiment loops for self-improvement.

Inspired by Karpathy's autoresearch (MIT) — https://github.com/karpathy/autoresearch
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.config import settings

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
        "model_temp": "app.core.autoresearch_runners.model_temp",
        "skill_prompt": "app.core.autoresearch_runners.skill_prompt",
        "rag_params": "app.core.autoresearch_runners.rag_params",
        "persona": "app.core.autoresearch_runners.persona",
        "question_bank": "app.core.autoresearch_runners.question_bank",
        "ui_sim": "app.core.autoresearch_runners.ui_sim",
    }
    module_path = runner_map.get(loop_type)
    if not module_path:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown loop type: {loop_type}. Valid types: {', '.join(runner_map.keys())}",
        )
    try:
        import importlib
        mod = importlib.import_module(module_path)
        return mod
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail=f"Runner for loop type '{loop_type}' is not installed.",
        )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/status")
async def autoresearch_status():
    """Get autoresearch engine status and current experiment."""
    engine = _get_engine()
    current = engine.get_current_experiment()
    return {
        "running": engine.is_running(),
        "enabled": getattr(settings, "autoresearch_enabled", False),
        "current_experiment": current,
    }


@router.get("/experiments")
async def list_experiments(
    loop_type: Optional[str] = None,
    kept: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
):
    """Get paginated experiment history with optional filters."""
    engine = _get_engine()
    experiments = engine.get_experiments(
        loop_type=loop_type,
        kept=kept,
        limit=limit,
        offset=offset,
    )
    return experiments


@router.get("/experiments/{experiment_id}")
async def get_experiment(experiment_id: str):
    """Get a single experiment by ID."""
    engine = _get_engine()
    experiment = engine.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return experiment


@router.post("/start")
async def start_experiment(body: StartExperimentRequest, background_tasks: BackgroundTasks):
    """Start an autoresearch experiment loop in the background."""
    engine = _get_engine()

    if engine.is_running():
        raise HTTPException(
            status_code=409,
            detail="An experiment loop is already running. Stop it first.",
        )

    if not getattr(settings, "autoresearch_enabled", False):
        raise HTTPException(
            status_code=403,
            detail="Autoresearch is disabled. Enable it first via /api/autoresearch/toggle.",
        )

    # Validate runner exists
    _get_runner(body.loop_type)

    async def _run_loop():
        try:
            await engine.run_loop(
                loop_type=body.loop_type,
                target=body.target,
                max_iterations=body.max_iterations,
                project_id=body.project_id,
            )
        except Exception as exc:
            logger.error(f"Autoresearch loop failed: {exc}", exc_info=True)

    background_tasks.add_task(_run_loop)

    return {
        "status": "started",
        "loop_type": body.loop_type,
        "target": body.target,
        "max_iterations": body.max_iterations,
    }


@router.post("/stop")
async def stop_experiment():
    """Stop the currently running experiment loop."""
    engine = _get_engine()

    if not engine.is_running():
        raise HTTPException(status_code=409, detail="No experiment loop is currently running.")

    engine.stop()
    return {"status": "stopped"}


@router.get("/config")
async def get_config():
    """Get autoresearch configuration."""
    return {
        "enabled": getattr(settings, "autoresearch_enabled", False),
        "max_experiments_per_run": getattr(settings, "autoresearch_max_experiments_per_run", 20),
        "max_daily_experiments": getattr(settings, "autoresearch_max_daily_experiments", 100),
    }


@router.patch("/config")
async def update_config(body: ConfigUpdate):
    """Update autoresearch configuration."""
    if body.enabled is not None:
        settings.autoresearch_enabled = body.enabled
    if body.max_experiments_per_run is not None:
        settings.autoresearch_max_experiments_per_run = body.max_experiments_per_run
    if body.max_daily_experiments is not None:
        settings.autoresearch_max_daily_experiments = body.max_daily_experiments

    return {
        "enabled": getattr(settings, "autoresearch_enabled", False),
        "max_experiments_per_run": getattr(settings, "autoresearch_max_experiments_per_run", 20),
        "max_daily_experiments": getattr(settings, "autoresearch_max_daily_experiments", 100),
    }


@router.get("/leaderboard")
async def get_leaderboard():
    """Get best model+temperature leaderboard per skill."""
    engine = _get_engine()
    return engine.get_leaderboard()


@router.post("/toggle")
async def toggle_autoresearch(body: ToggleRequest):
    """Enable or disable autoresearch."""
    settings.autoresearch_enabled = body.enabled

    engine = _get_engine()
    if not body.enabled and engine.is_running():
        engine.stop()

    return {
        "enabled": body.enabled,
        "message": f"Autoresearch {'enabled' if body.enabled else 'disabled'}",
    }
