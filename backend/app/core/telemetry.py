"""Telemetry Recorder — writes observability spans to the local database.

Local-first by design: data stays on the user's machine. No phone-home.
The TELEMETRY_ENABLED flag is reserved for future opt-in sharing (P3-B).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func

from app.models.database import async_session
from app.models.telemetry_span import TelemetrySpan

logger = logging.getLogger(__name__)


class TelemetryRecorder:
    """Records telemetry spans and model performance data to the local database."""

    async def record_span(
        self,
        trace_id: str,
        operation: str,
        skill_name: str = "",
        model_name: str = "",
        agent_id: str = "",
        project_id: str = "",
        task_id: str | None = None,
        parent_id: str | None = None,
        duration_ms: float = 0.0,
        status: str = "success",
        quality_score: float | None = None,
        consensus_score: float | None = None,
        error_type: str | None = None,
        error_message: str | None = None,
        temperature: float | None = None,
        tool_name: str | None = None,
        tool_success: bool | None = None,
        tool_duration_ms: float | None = None,
        source: str = "production",
    ) -> None:
        """Write a telemetry span to the database."""
        try:
            async with async_session() as session:
                span = TelemetrySpan(
                    id=uuid.uuid4().hex[:36],
                    trace_id=trace_id,
                    parent_id=parent_id,
                    operation=operation,
                    skill_name=skill_name,
                    model_name=model_name,
                    agent_id=agent_id,
                    started_at=datetime.now(timezone.utc),
                    duration_ms=duration_ms,
                    status=status,
                    quality_score=quality_score,
                    consensus_score=consensus_score,
                    error_type=error_type,
                    error_message=(error_message or "")[:500] if error_message else None,
                    project_id=project_id,
                    task_id=task_id,
                    temperature=temperature,
                    tool_name=tool_name,
                    tool_success=int(tool_success) if tool_success is not None else None,
                    tool_duration_ms=tool_duration_ms,
                    source=source,
                )
                session.add(span)
                await session.commit()
        except Exception as e:
            logger.debug(f"Telemetry span write failed: {e}")

    async def record_model_performance(
        self,
        skill_name: str,
        model_name: str,
        temperature: float = 0.7,
        quality: float = 0.5,
        success: bool = True,
    ) -> None:
        """Upsert ModelSkillStats from production path."""
        try:
            from app.models.model_skill_stats import ModelSkillStats

            async with async_session() as session:
                stmt = select(ModelSkillStats).where(
                    ModelSkillStats.skill_name == skill_name,
                    ModelSkillStats.model_name == model_name,
                    ModelSkillStats.temperature == temperature,
                    ModelSkillStats.source == "production",
                )
                result = await session.execute(stmt)
                row = result.scalar_one_or_none()

                if row is None:
                    row = ModelSkillStats(
                        skill_name=skill_name,
                        model_name=model_name,
                        temperature=temperature,
                        executions=1,
                        total_quality=quality,
                        quality_ema=quality,
                        best_quality=quality,
                        source="production",
                        last_used=datetime.now(timezone.utc),
                    )
                    session.add(row)
                else:
                    row.executions += 1
                    row.total_quality += quality
                    old_ema = row.quality_ema or 0.5
                    alpha = 0.1
                    row.quality_ema = old_ema * (1 - alpha) + quality * alpha
                    if quality > (row.best_quality or 0):
                        row.best_quality = quality
                    row.last_used = datetime.now(timezone.utc)

                await session.commit()
        except Exception as e:
            logger.debug(f"Model performance write failed: {e}")

    async def get_model_intelligence(self, project_id: str, limit: int = 50) -> dict:
        """Get model intelligence data for a project.

        Returns leaderboard, error taxonomy, tool success rates, and latency percentiles.
        """
        try:
            async with async_session() as session:
                from app.models.model_skill_stats import ModelSkillStats

                stmt = (
                    select(ModelSkillStats)
                    .where(ModelSkillStats.executions >= 1)
                    .order_by(ModelSkillStats.best_quality.desc())
                    .limit(limit)
                )
                result = await session.execute(stmt)
                rows = result.scalars().all()

                leaderboard = [
                    {
                        "skill_name": r.skill_name,
                        "model_name": r.model_name,
                        "temperature": r.temperature,
                        "quality_ema": round(r.quality_ema or 0, 3),
                        "best_quality": round(r.best_quality or 0, 3),
                        "executions": r.executions,
                        "source": r.source,
                    }
                    for r in rows
                ]

                error_stmt = (
                    select(TelemetrySpan)
                    .where(
                        TelemetrySpan.project_id == project_id,
                        TelemetrySpan.status == "error",
                    )
                    .order_by(TelemetrySpan.created_at.desc())
                    .limit(100)
                )
                error_result = await session.execute(error_stmt)
                error_spans = error_result.scalars().all()

                error_taxonomy: dict[str, list[dict]] = {}
                for s in error_spans:
                    etype = s.error_type or "other"
                    if etype not in error_taxonomy:
                        error_taxonomy[etype] = []
                    entry = {
                        "skill_name": s.skill_name,
                        "model_name": s.model_name,
                        "duration_ms": round(s.duration_ms, 1),
                    }
                    if len(error_taxonomy[etype]) < 20:
                        error_taxonomy[etype].append(entry)

                tool_stmt = (
                    select(TelemetrySpan)
                    .where(
                        TelemetrySpan.project_id == project_id,
                        TelemetrySpan.operation == "tool_call",
                    )
                    .order_by(TelemetrySpan.created_at.desc())
                    .limit(200)
                )
                tool_result = await session.execute(tool_stmt)
                tool_spans = tool_result.scalars().all()

                tool_stats: dict[str, dict] = {}
                for s in tool_spans:
                    tname = s.tool_name or "unknown"
                    if tname not in tool_stats:
                        tool_stats[tname] = {
                            "total": 0,
                            "success": 0,
                            "errors": {},
                            "durations": [],
                        }
                    tool_stats[tname]["total"] += 1
                    if s.tool_success:
                        tool_stats[tname]["success"] += 1
                    if s.error_type:
                        tool_stats[tname]["errors"][s.error_type] = (
                            tool_stats[tname]["errors"].get(s.error_type, 0) + 1
                        )
                    if s.tool_duration_ms:
                        tool_stats[tname]["durations"].append(s.tool_duration_ms)

                tool_success_rates = []
                for tname, stats in tool_stats.items():
                    durations = sorted(stats["durations"]) if stats["durations"] else [0]
                    p50 = durations[len(durations) // 2] if durations else 0
                    p90 = durations[int(len(durations) * 0.9)] if len(durations) > 1 else p50
                    tool_success_rates.append(
                        {
                            "tool": tname,
                            "success_rate": round(stats["success"] / max(stats["total"], 1), 3),
                            "total_calls": stats["total"],
                            "avg_duration_ms": round(
                                sum(stats["durations"]) / max(len(stats["durations"]), 1), 1
                            ),
                            "p50_duration_ms": round(p50, 1),
                            "p90_duration_ms": round(p90, 1),
                            "error_types": stats["errors"],
                        }
                    )

                latency_stmt = (
                    select(TelemetrySpan)
                    .where(
                        TelemetrySpan.project_id == project_id,
                        TelemetrySpan.operation == "skill_execute",
                        TelemetrySpan.duration_ms > 0,
                    )
                    .order_by(TelemetrySpan.created_at.desc())
                    .limit(500)
                )
                latency_result = await session.execute(latency_stmt)
                latency_spans = latency_result.scalars().all()

                model_latencies: dict[str, list[float]] = {}
                for s in latency_spans:
                    mn = s.model_name or "unknown"
                    if mn not in model_latencies:
                        model_latencies[mn] = []
                    model_latencies[mn].append(s.duration_ms)

                latency_percentiles = []
                for mn, durs in model_latencies.items():
                    sd = sorted(durs)
                    p50 = sd[len(sd) // 2] if sd else 0
                    p90 = sd[int(len(sd) * 0.9)] if len(sd) > 1 else p50
                    p99 = sd[int(len(sd) * 0.99)] if len(sd) > 10 else p90
                    latency_percentiles.append(
                        {
                            "model": mn,
                            "p50_ms": round(p50, 1),
                            "p90_ms": round(p90, 1),
                            "p99_ms": round(p99, 1),
                            "samples": len(sd),
                        }
                    )

                return {
                    "project_id": project_id,
                    "leaderboard": leaderboard,
                    "error_taxonomy": error_taxonomy,
                    "tool_success_rates": tool_success_rates,
                    "latency_percentiles": latency_percentiles,
                }

        except Exception as e:
            logger.warning(f"Model intelligence query failed: {e}")
            return {
                "project_id": project_id,
                "leaderboard": [],
                "error_taxonomy": {},
                "tool_success_rates": [],
                "latency_percentiles": [],
            }


    async def get_task_health(self, task_id: str) -> dict:
        """Get aggregated health status for a specific task based on its spans."""
        try:
            async with async_session() as session:
                stmt = (
                    select(TelemetrySpan)
                    .where(TelemetrySpan.task_id == task_id)
                    .order_by(TelemetrySpan.created_at.desc())
                )
                result = await session.execute(stmt)
                spans = result.scalars().all()

                if not spans:
                    return {"status": "unknown", "error_count": 0, "avg_quality": None}

                error_count = sum(1 for s in spans if s.status == "error")
                qualities = [s.quality_score for s in spans if s.quality_score is not None]
                avg_quality = sum(qualities) / len(qualities) if qualities else None
                
                # Determine status
                status = "healthy"
                if error_count > 0:
                    status = "degraded"
                if error_count > 2 or (avg_quality is not None and avg_quality < 0.4):
                    status = "critical"
                
                return {
                    "status": status,
                    "error_count": error_count,
                    "avg_quality": round(avg_quality, 2) if avg_quality is not None else None,
                    "span_count": len(spans)
                }
        except Exception as e:
            logger.debug(f"Task health query failed: {e}")
            return {"status": "unknown", "error_count": 0, "avg_quality": None}


telemetry_recorder = TelemetryRecorder()
