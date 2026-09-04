"""Telemetry Recorder — writes observability spans to the local database.

Local-first by design: data stays on the user's machine. No phone-home.
The TELEMETRY_ENABLED flag is reserved for future opt-in sharing (P3-B).
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.research_validity import (
    research_validity_telemetry_contract,
    telemetry_operation_names,
)
from app.models.database import async_session
from app.models.telemetry_span import TelemetrySpan

logger = logging.getLogger(__name__)


class TelemetryRecorder:
    """Records telemetry spans and model performance data to the local database."""

    def __init__(self) -> None:
        self._write_failures = 0
        self._last_write_failure_at: str | None = None

    def write_health_snapshot(self) -> dict[str, object]:
        """Return value-free, process-local evidence-store health."""
        return {
            "healthy": self._write_failures == 0,
            "write_failures": self._write_failures,
            "last_failure_at": self._last_write_failure_at,
        }

    def reset_write_health_for_tests(self) -> None:
        """Reset process-local counters for an isolated test baseline."""
        self._write_failures = 0
        self._last_write_failure_at = None

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
        reliability_score: float | None = None,
        error_type: str | None = None,
        error_message: str | None = None,
        event_kind: str = "",
        route_id: str = "",
        donor_id: str = "",
        retrieval_mode: str = "",
        coding_run_id: str = "",
        evidence_unit_id: str = "",
        codebook_version_id: str = "",
        temperature: float | None = None,
        tool_name: str | None = None,
        tool_success: bool | None = None,
        tool_duration_ms: float | None = None,
        source: str = "production",
        session: AsyncSession | None = None,
    ) -> None:
        """Write a telemetry span to the database."""
        span = TelemetrySpan(
            id=uuid.uuid4().hex[:36],
            trace_id=trace_id,
            parent_id=parent_id,
            operation=operation,
            skill_name=skill_name,
            model_name=model_name,
            agent_id=agent_id,
            started_at=datetime.now(UTC),
            duration_ms=duration_ms,
            status=status,
            quality_score=quality_score,
            consensus_score=consensus_score,
            reliability_score=reliability_score,
            error_type=error_type,
            error_message=(error_message or "")[:500] if error_message else None,
            project_id=project_id,
            task_id=task_id,
            event_kind=event_kind,
            route_id=route_id,
            donor_id=donor_id,
            retrieval_mode=retrieval_mode,
            coding_run_id=coding_run_id,
            evidence_unit_id=evidence_unit_id,
            codebook_version_id=codebook_version_id,
            temperature=temperature,
            tool_name=tool_name,
            tool_success=int(tool_success) if tool_success is not None else None,
            tool_duration_ms=tool_duration_ms,
            source=source,
        )
        if session is not None:
            # Keep telemetry in the caller's transaction.  A separate SQLite
            # writer here can deadlock when the caller has already flushed a
            # source/evidence row, and atomic lifecycle evidence is preferable
            # to an eventually-consistent side write.
            session.add(span)
            return
        try:
            async with async_session() as session:
                session.add(span)
                await session.commit()
        except Exception as e:
            # A missing research-validity span is an observability failure, not
            # harmless debug noise. Keep request handling non-fatal while
            # making the loss visible to operators and benchmark log capture.
            self._write_failures += 1
            self._last_write_failure_at = datetime.now(UTC).isoformat()
            logger.warning("Telemetry span write failed: %s", e)

    async def record_research_validity_event(
        self,
        *,
        operation: str,
        project_id: str,
        trace_id: str | None = None,
        task_id: str | None = None,
        status: str = "success",
        skill_name: str = "",
        model_name: str = "",
        agent_id: str = "",
        route_id: str = "",
        donor_id: str = "",
        retrieval_mode: str = "",
        coding_run_id: str = "",
        evidence_unit_id: str = "",
        codebook_version_id: str = "",
        reliability_score: float | None = None,
        consensus_score: float | None = None,
        quality_score: float | None = None,
        error_type: str | None = None,
        error_message: str | None = None,
        source: str = "production",
        session: AsyncSession | None = None,
    ) -> None:
        """Record a content-free research-validity lifecycle event.

        The taxonomy lives in ``app.core.research_validity`` so the API,
        frontend, tests, and docs all reason about the same workflow events.
        """
        if operation not in set(telemetry_operation_names()):
            logger.debug("Unknown research-validity telemetry operation: %s", operation)
        await self.record_span(
            trace_id=trace_id or uuid.uuid4().hex[:36],
            operation=operation,
            skill_name=skill_name,
            model_name=model_name,
            agent_id=agent_id,
            project_id=project_id,
            task_id=task_id,
            status=status,
            quality_score=quality_score,
            consensus_score=consensus_score,
            reliability_score=reliability_score,
            error_type=error_type,
            error_message=error_message,
            event_kind="research_validity",
            route_id=route_id,
            donor_id=donor_id,
            retrieval_mode=retrieval_mode,
            coding_run_id=coding_run_id,
            evidence_unit_id=evidence_unit_id,
            codebook_version_id=codebook_version_id,
            source=source,
            session=session,
        )

    async def record_json_parse(
        self,
        trace_id: str,
        model_name: str = "",
        success: bool = True,
        error_type: str | None = None,
        error_message: str | None = None,
        agent_id: str = "",
        project_id: str = "",
    ) -> None:
        """Record whether an LLM response was successfully parsed as JSON.

        Used to track model reliability with structured outputs — models that
        frequently fail JSON parsing should be flagged in the compatibility UI.
        """
        await self.record_span(
            trace_id=trace_id,
            operation="json_parse",
            model_name=model_name,
            agent_id=agent_id,
            project_id=project_id,
            status="success" if success else "error",
            error_type=error_type,
            error_message=(error_message or "")[:500] if error_message else None,
        )

    async def record_tool_call(
        self,
        *,
        tool_name: str,
        duration_ms: float,
        success: bool,
        model_name: str = "",
        project_id: str = "",
        agent_id: str = "",
        task_id: str | None = None,
        trace_id: str | None = None,
        parent_id: str | None = None,
        error_type: str | None = None,
        error_message: str | None = None,
        source: str = "production",
        session: AsyncSession | None = None,
    ) -> None:
        """Record a canonical tool execution span following OpenTelemetry GenAI conventions."""
        await self.record_span(
            trace_id=trace_id or uuid.uuid4().hex[:36],
            parent_id=parent_id,
            operation="tool_call",
            tool_name=tool_name,
            tool_success=success,
            tool_duration_ms=duration_ms,
            duration_ms=duration_ms,
            model_name=model_name,
            status="success" if success else "error",
            agent_id=agent_id,
            project_id=project_id,
            task_id=task_id,
            error_type=error_type,
            error_message=error_message,
            source=source,
            session=session,
        )

    async def record_steering_event(
        self,
        *,
        project_id: str,
        agent_id: str,
        action: str,
        trace_id: str | None = None,
        task_id: str | None = None,
        status: str = "success",
        queue_depth: int | None = None,
        error_message: str | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        """Record an agentic steering lifecycle event (queue, drain, abort)."""
        await self.record_span(
            trace_id=trace_id or uuid.uuid4().hex[:36],
            operation="steering.event",
            event_kind="agent_steering",
            agent_id=agent_id,
            project_id=project_id,
            task_id=task_id,
            status=status,
            route_id=f"{action}:queue_depth={queue_depth}" if queue_depth is not None else action,
            error_message=error_message,
            session=session,
        )

    async def record_reliability_evaluation(
        self,
        *,
        project_id: str,
        coding_run_id: str,
        metric_name: str,
        score: float | None,
        alpha: float | None = None,
        threshold: float = 0.60,
        rater_count: int = 3,
        item_count: int = 0,
        promotion_status: str = "accepted",
        trace_id: str | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        """Record mathematical inter-coder reliability evaluation across multi-model ensemble."""
        await self.record_span(
            trace_id=trace_id or uuid.uuid4().hex[:36],
            operation="coding_run.reliability",
            event_kind="research_validity",
            coding_run_id=coding_run_id,
            project_id=project_id,
            reliability_score=score,
            consensus_score=alpha,
            status="success" if promotion_status == "accepted" else "degraded",
            route_id=f"{metric_name}:raters={rater_count}:items={item_count}:threshold={threshold}",
            session=session,
        )

    async def record_model_performance(
        self,
        skill_name: str,
        model_name: str,
        temperature: float = 0.7,
        quality: float = 0.5,
        success: bool = True,
        project_id: str = "",
    ) -> None:
        """Upsert project-scoped ModelSkillStats from production path."""
        scoped_project_id = str(project_id or "").strip()
        if not scoped_project_id:
            logger.debug("Model performance write skipped: project_id is required")
            return
        try:
            from app.models.model_skill_stats import ModelSkillStats

            async with async_session() as session:
                stmt = select(ModelSkillStats).where(
                    ModelSkillStats.project_id == scoped_project_id,
                    ModelSkillStats.skill_name == skill_name,
                    ModelSkillStats.model_name == model_name,
                    ModelSkillStats.temperature == temperature,
                    ModelSkillStats.source == "production",
                )
                result = await session.execute(stmt)
                row = result.scalar_one_or_none()

                if row is None:
                    row = ModelSkillStats(
                        project_id=scoped_project_id,
                        skill_name=skill_name,
                        model_name=model_name,
                        temperature=temperature,
                        executions=1,
                        total_quality=quality,
                        quality_ema=quality,
                        best_quality=quality,
                        source="production",
                        last_used=datetime.now(UTC),
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
                    row.last_used = datetime.now(UTC)

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
                    .where(
                        ModelSkillStats.project_id == project_id,
                        ModelSkillStats.executions >= 1,
                    )
                    .order_by(ModelSkillStats.best_quality.desc())
                    .limit(limit)
                )
                result = await session.execute(stmt)
                rows = result.scalars().all()

                leaderboard = [
                    {
                        "project_id": r.project_id,
                        "skill_name": r.skill_name,
                        "model_name": r.model_name,
                        "model": r.model_name,
                        "temperature": r.temperature,
                        "quality_ema": round(r.quality_ema or 0, 3),
                        "best_quality": round(r.best_quality or 0, 3),
                        "executions": r.executions,
                        "total_calls": r.executions,
                        "source": r.source,
                    }
                    for r in rows
                ]

                # Model activity across all telemetry spans (OpenTelemetry GenAI conventions)
                model_activity_stmt = (
                    select(TelemetrySpan)
                    .where(
                        TelemetrySpan.project_id == project_id,
                        TelemetrySpan.model_name != "",
                    )
                    .order_by(TelemetrySpan.created_at.desc())
                    .limit(500)
                )
                model_spans_res = await session.execute(model_activity_stmt)
                spans_by_model: dict[str, list[TelemetrySpan]] = {}
                for sp in model_spans_res.scalars().all():
                    spans_by_model.setdefault(sp.model_name, []).append(sp)

                should_synthesize_leaderboard = not leaderboard
                model_activity: list[dict] = []
                for mn, mspans in spans_by_model.items():
                    m_total = len(mspans)
                    m_success = sum(1 for sp in mspans if sp.status == "success")
                    m_durs = [sp.duration_ms for sp in mspans if sp.duration_ms > 0]
                    m_qualities = [
                        sp.quality_score for sp in mspans if sp.quality_score is not None
                    ]
                    m_ops = sorted({sp.operation for sp in mspans if sp.operation})
                    m_qual = (
                        (sum(m_qualities) / len(m_qualities))
                        if m_qualities
                        else round(m_success / max(m_total, 1), 3)
                    )
                    model_activity.append(
                        {
                            "model": mn,
                            "model_name": mn,
                            "total_calls": m_total,
                            "success_count": m_success,
                            "success_rate": round(m_success / max(m_total, 1), 3),
                            "avg_duration_ms": round(sum(m_durs) / max(len(m_durs), 1), 1)
                            if m_durs
                            else 0.0,
                            "quality_ema": round(m_qual, 3),
                            "operations": m_ops,
                        }
                    )
                    if should_synthesize_leaderboard:
                        leaderboard.append(
                            {
                                "project_id": project_id,
                                "skill_name": mspans[0].skill_name or "research_validity",
                                "model_name": mn,
                                "model": mn,
                                "temperature": mspans[0].temperature or 0.2,
                                "quality_ema": round(m_qual, 3),
                                "best_quality": round(
                                    max(m_qualities) if m_qualities else m_qual, 3
                                ),
                                "executions": m_total,
                                "total_calls": m_total,
                                "source": "spans_aggregated",
                            }
                        )

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
                            "agents": set(),
                            "models": set(),
                        }
                    tool_stats[tname]["total"] += 1
                    if s.tool_success:
                        tool_stats[tname]["success"] += 1
                    if s.error_type:
                        tool_stats[tname]["errors"][s.error_type] = (
                            tool_stats[tname]["errors"].get(s.error_type, 0) + 1
                        )
                    if s.tool_duration_ms is not None and s.tool_duration_ms >= 0:
                        tool_stats[tname]["durations"].append(s.tool_duration_ms)
                    if s.agent_id:
                        tool_stats[tname]["agents"].add(s.agent_id)
                    if s.model_name:
                        tool_stats[tname]["models"].add(s.model_name)

                total_tool_calls = sum(st["total"] for st in tool_stats.values())
                total_tool_success = sum(st["success"] for st in tool_stats.values())
                all_tool_durations = [d for st in tool_stats.values() for d in st["durations"]]
                all_tool_errors = sorted({e for st in tool_stats.values() for e in st["errors"]})
                tool_summary = {
                    "total_calls": total_tool_calls,
                    "overall_success_rate": round(total_tool_success / max(total_tool_calls, 1), 3)
                    if total_tool_calls
                    else 0.0,
                    "distinct_tools": len(tool_stats),
                    "avg_duration_ms": round(
                        sum(all_tool_durations) / max(len(all_tool_durations), 1), 1
                    )
                    if all_tool_durations
                    else 0.0,
                    "error_types_observed": all_tool_errors,
                }

                tool_success_rates = []
                for tname, stats in tool_stats.items():
                    durations = sorted(stats["durations"]) if stats["durations"] else [0]
                    p50 = durations[len(durations) // 2] if durations else 0
                    p90 = durations[int(len(durations) * 0.9)] if len(durations) > 1 else p50
                    p95 = durations[int(len(durations) * 0.95)] if len(durations) > 1 else p90
                    p99 = durations[int(len(durations) * 0.99)] if len(durations) > 10 else p95
                    min_d = durations[0] if durations else 0
                    max_d = durations[-1] if durations else 0
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
                            "p95_duration_ms": round(p95, 1),
                            "p99_duration_ms": round(p99, 1),
                            "min_duration_ms": round(min_d, 1),
                            "max_duration_ms": round(max_d, 1),
                            "error_types": stats["errors"],
                            "agents": sorted(stats["agents"]),
                            "models": sorted(stats["models"]),
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
                    p95 = sd[int(len(sd) * 0.95)] if len(sd) > 1 else p90
                    p99 = sd[int(len(sd) * 0.99)] if len(sd) > 10 else p90
                    avg_ms = sum(sd) / max(len(sd), 1)
                    latency_percentiles.append(
                        {
                            "model": mn,
                            "avg_ms": round(avg_ms, 1),
                            "p50_ms": round(p50, 1),
                            "p90_ms": round(p90, 1),
                            "p95_ms": round(p95, 1),
                            "p99_ms": round(p99, 1),
                            "samples": len(sd),
                        }
                    )

                # Compute JSON parse success rates per model (Phase Epsilon Step 2)
                json_parse_stmt = (
                    select(TelemetrySpan)
                    .where(
                        TelemetrySpan.project_id == project_id,
                        TelemetrySpan.operation == "json_parse",
                    )
                    .order_by(TelemetrySpan.created_at.desc())
                    .limit(500)
                )
                json_result = await session.execute(json_parse_stmt)
                json_spans = json_result.scalars().all()

                model_json_stats: dict[str, dict] = {}
                for s in json_spans:
                    mn = s.model_name or "unknown"
                    if mn not in model_json_stats:
                        model_json_stats[mn] = {"total": 0, "success": 0}
                    model_json_stats[mn]["total"] += 1
                    if s.status == "success":
                        model_json_stats[mn]["success"] += 1

                json_parse_success_rates = []
                for mn, stats in model_json_stats.items():
                    total = max(stats["total"], 1)
                    json_parse_success_rates.append(
                        {
                            "model": mn,
                            "json_parse_success_rate": round(stats["success"] / total, 3),
                            "total_parses": stats["total"],
                        }
                    )

                # Steering summary for this project
                steering_stmt = (
                    select(TelemetrySpan)
                    .where(
                        TelemetrySpan.project_id == project_id,
                        TelemetrySpan.operation == "steering.event",
                    )
                    .order_by(TelemetrySpan.created_at.desc())
                    .limit(200)
                )
                steering_result = await session.execute(steering_stmt)
                steering_spans = steering_result.scalars().all()
                steering_counts: dict[str, int] = {}
                for sp in steering_spans:
                    act = sp.route_id.split(":")[0] if sp.route_id else "unknown"
                    steering_counts[act] = steering_counts.get(act, 0) + 1
                steering_summary = {
                    "total_events": len(steering_spans),
                    "action_counts": steering_counts,
                }

                return {
                    "project_id": project_id,
                    "leaderboard": leaderboard,
                    "model_activity": model_activity,
                    "error_taxonomy": error_taxonomy,
                    "tool_success_rates": tool_success_rates,
                    "tool_summary": tool_summary,
                    "steering_summary": steering_summary,
                    "json_parse_success_rates": json_parse_success_rates,
                    "latency_percentiles": latency_percentiles,
                }

        except Exception as e:
            logger.warning(f"Model intelligence query failed: {e}")
            return {
                "project_id": project_id,
                "leaderboard": [],
                "model_activity": [],
                "error_taxonomy": {},
                "tool_success_rates": [],
                "tool_summary": {
                    "total_calls": 0,
                    "overall_success_rate": 0.0,
                    "distinct_tools": 0,
                },
                "steering_summary": {"total_events": 0, "action_counts": {}},
                "json_parse_success_rates": [],
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
                    "span_count": len(spans),
                }
        except Exception as e:
            logger.debug(f"Task health query failed: {e}")
            return {"status": "unknown", "error_count": 0, "avg_quality": None}

    async def get_research_validity_audit(self, project_id: str, limit: int = 500) -> dict:
        """Summarize project research-validity telemetry without content payloads."""
        contract = research_validity_telemetry_contract()
        operation_meta = {row["operation"]: row for row in contract["operations"]}
        operation_names = set(operation_meta)
        capped_limit = max(1, min(limit, 2000))
        try:
            async with async_session() as session:
                stmt = (
                    select(TelemetrySpan)
                    .where(
                        TelemetrySpan.project_id == project_id,
                        or_(
                            TelemetrySpan.event_kind == "research_validity",
                            TelemetrySpan.operation.in_(operation_names),
                        ),
                    )
                    .order_by(TelemetrySpan.created_at.desc())
                    .limit(capped_limit)
                )
                result = await session.execute(stmt)
                spans = list(result.scalars().all())
        except Exception as e:
            logger.warning(f"Research-validity telemetry audit failed: {e}")
            return {
                "project_id": project_id,
                "status": "unavailable",
                "error_type": "telemetry_query_failed",
                "operation_counts": {},
                "category_counts": {},
                "retrieval_mode_counts": {},
                "donor_lifecycle_counts": {},
                "route_evidence_count": 0,
                "coding_run_ids": [],
                "evidence_unit_ids": [],
                "codebook_version_ids": [],
                "unobserved_contract_operations": telemetry_operation_names(),
                "content_policy": contract["content_policy"],
            }

        operation_counts: dict[str, int] = {}
        category_counts: dict[str, int] = {}
        status_counts: dict[str, int] = {}
        retrieval_mode_counts: dict[str, int] = {}
        donor_lifecycle_counts: dict[str, int] = {}
        coding_run_ids: set[str] = set()
        evidence_unit_ids: set[str] = set()
        codebook_version_ids: set[str] = set()
        reliability_scores: list[float] = []
        route_evidence: list[dict] = []

        for span in spans:
            operation_counts[span.operation] = operation_counts.get(span.operation, 0) + 1
            category = operation_meta.get(span.operation, {}).get("category", "uncategorized")
            category_counts[category] = category_counts.get(category, 0) + 1
            status_counts[span.status] = status_counts.get(span.status, 0) + 1
            if span.retrieval_mode:
                retrieval_mode_counts[span.retrieval_mode] = (
                    retrieval_mode_counts.get(span.retrieval_mode, 0) + 1
                )
            if category == "donor_lifecycle":
                donor_lifecycle_counts[span.operation] = (
                    donor_lifecycle_counts.get(span.operation, 0) + 1
                )
            if span.coding_run_id:
                coding_run_ids.add(span.coding_run_id)
            if span.evidence_unit_id:
                evidence_unit_ids.add(span.evidence_unit_id)
            if span.codebook_version_id:
                codebook_version_ids.add(span.codebook_version_id)
            if span.reliability_score is not None:
                reliability_scores.append(float(span.reliability_score))
            if span.route_id or span.donor_id or span.model_name:
                route_evidence.append(
                    {
                        "operation": span.operation,
                        "status": span.status,
                        "model_name": span.model_name,
                        "route_id": span.route_id,
                        "donor_id": span.donor_id,
                        "coding_run_id": span.coding_run_id,
                        "evidence_unit_id": span.evidence_unit_id,
                        "retrieval_mode": span.retrieval_mode,
                        "reliability_score": span.reliability_score,
                        "created_at": span.created_at.isoformat() if span.created_at else None,
                    }
                )

        observed = set(operation_counts)
        reliability_summary = {
            "count": len(reliability_scores),
            "min": round(min(reliability_scores), 3) if reliability_scores else None,
            "max": round(max(reliability_scores), 3) if reliability_scores else None,
            "avg": round(sum(reliability_scores) / len(reliability_scores), 3)
            if reliability_scores
            else None,
        }
        return {
            "project_id": project_id,
            "status": "ok",
            "span_count": len(spans),
            "operation_counts": operation_counts,
            "category_counts": category_counts,
            "status_counts": status_counts,
            "retrieval_mode_counts": retrieval_mode_counts,
            "donor_lifecycle_counts": donor_lifecycle_counts,
            "route_evidence_count": len(route_evidence),
            "route_evidence": route_evidence[:50],
            "coding_run_ids": sorted(coding_run_ids),
            "evidence_unit_ids": sorted(evidence_unit_ids),
            "codebook_version_ids": sorted(codebook_version_ids),
            "reliability_summary": reliability_summary,
            "unobserved_contract_operations": [
                operation for operation in telemetry_operation_names() if operation not in observed
            ],
            "content_policy": contract["content_policy"],
            "protected_fields": contract["protected_fields"],
        }


telemetry_recorder = TelemetryRecorder()
