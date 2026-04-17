"""Telemetry export — generates portable JSON exports of local telemetry data.

No phone-home. Data stays on the user's machine. Exports are written to
settings.telemetry_export_dir for the user to share or inspect as they wish.
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

from sqlalchemy import select, func

from app.config import settings
from app.models.database import async_session
from app.models.telemetry_span import TelemetrySpan
from app.models.model_skill_stats import ModelSkillStats

logger = logging.getLogger(__name__)


async def export_telemetry(
    project_id: str | None = None,
    days: int = 7,
    include_models: bool = True,
) -> dict:
    """Export telemetry spans and model stats to a portable JSON file.

    Args:
        project_id: If provided, filter to spans from this project only.
                    If None, exports spans from all projects.
        days: How many days of recent data to include (default 7).
        include_models: Include ModelSkillStats leaderboard data.

    Returns:
        dict with export metadata and paths to generated files.
    """
    settings.ensure_telemetry_dir()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    project_tag = project_id or "all"
    base_name = f"istara_telemetry_{project_tag}_{timestamp}"

    spans_data = []
    try:
        async with async_session() as session:
            query = select(TelemetrySpan).where(TelemetrySpan.created_at >= cutoff)
            if project_id:
                query = query.where(TelemetrySpan.project_id == project_id)
            query = query.order_by(TelemetrySpan.created_at.desc())
            result = await session.execute(query)
            spans = result.scalars().all()

            for s in spans:
                spans_data.append(
                    {
                        "id": s.id,
                        "trace_id": s.trace_id,
                        "parent_id": s.parent_id,
                        "operation": s.operation,
                        "skill_name": s.skill_name,
                        "model_name": s.model_name,
                        "agent_id": s.agent_id,
                        "project_id": s.project_id,
                        "task_id": s.task_id,
                        "started_at": s.started_at.isoformat() if s.started_at else None,
                        "duration_ms": s.duration_ms,
                        "status": s.status,
                        "quality_score": s.quality_score,
                        "consensus_score": s.consensus_score,
                        "error_type": s.error_type,
                        "error_message": s.error_message,
                        "temperature": s.temperature,
                        "tool_name": s.tool_name,
                        "tool_success": bool(s.tool_success)
                        if s.tool_success is not None
                        else None,
                        "tool_duration_ms": s.tool_duration_ms,
                        "source": s.source,
                        "created_at": s.created_at.isoformat() if s.created_at else None,
                    }
                )
    except Exception as e:
        logger.error(f"Failed to export telemetry spans: {e}")
        raise

    summary = {
        "export_version": "1.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "project_id": project_id,
        "days": days,
        "cutoff": cutoff.isoformat(),
        "span_count": len(spans_data),
        "include_models": include_models,
    }

    spans_path = Path(settings.telemetry_export_dir) / f"{base_name}_spans.jsonl"
    summary_path = Path(settings.telemetry_export_dir) / f"{base_name}_summary.json"

    spans_path.write_text("\n".join(json.dumps(s) for s in spans_data))
    summary_path.write_text(json.dumps(summary, indent=2))

    if include_models:
        models_data = []
        try:
            async with async_session() as session:
                stmt = (
                    select(ModelSkillStats)
                    .where(ModelSkillStats.executions >= 1)
                    .order_by(ModelSkillStats.best_quality.desc())
                )
                result = await session.execute(stmt)
                for r in result.scalars().all():
                    models_data.append(
                        {
                            "skill_name": r.skill_name,
                            "model_name": r.model_name,
                            "temperature": r.temperature,
                            "executions": r.executions,
                            "quality_ema": r.quality_ema,
                            "best_quality": r.best_quality,
                            "total_quality": r.total_quality,
                            "source": r.source,
                            "last_used": r.last_used.isoformat() if r.last_used else None,
                        }
                    )
        except Exception as e:
            logger.error(f"Failed to export model stats: {e}")

        models_path = Path(settings.telemetry_export_dir) / f"{base_name}_models.json"
        models_path.write_text(json.dumps(models_data, indent=2))
        summary["model_stats_count"] = len(models_data)
        summary["models_file"] = str(models_path)
        summary_path.write_text(json.dumps(summary, indent=2))

    res = {
        "exported": True,
        "project_id": project_id,
        "days": days,
        "span_count": len(spans_data),
        "files": {
            "summary": str(summary_path),
            "spans": str(spans_path),
        },
        "export_dir": settings.telemetry_export_dir,
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
    if include_models:
        res["model_stats_count"] = summary.get("model_stats_count", 0)
        res["models_file"] = summary.get("models_file")
    return res
