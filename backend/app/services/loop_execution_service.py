"""Loop execution service — record, query, and aggregate execution data."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import async_session
from app.models.loop_execution import LoopExecution

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Record execution
# ---------------------------------------------------------------------------


def _clean_project_id(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _metadata_dict(execution: LoopExecution) -> dict[str, Any]:
    metadata = LoopExecution._parse_json_dict(execution.metadata_json)
    return metadata if isinstance(metadata, dict) else {}


def _metadata_project_id(execution: LoopExecution) -> str:
    return _clean_project_id(_metadata_dict(execution).get("project_id"))


def _execution_project_id(execution: LoopExecution) -> str:
    return _clean_project_id(getattr(execution, "project_id", "")) or _metadata_project_id(
        execution
    )


def _execution_matches_project(
    execution: LoopExecution,
    scoped_project_id: str,
    source_id_scope: set[str] | None,
) -> bool:
    row_project_id = _clean_project_id(getattr(execution, "project_id", ""))
    if row_project_id:
        return row_project_id == scoped_project_id

    legacy_metadata_project_id = _metadata_project_id(execution)
    if legacy_metadata_project_id:
        return legacy_metadata_project_id == scoped_project_id

    return source_id_scope is not None and execution.source_id in source_id_scope


def _execution_to_dict(
    execution: LoopExecution,
    scoped_project_id: str | None = None,
) -> dict[str, Any]:
    data = execution.to_dict()
    data["project_id"] = data.get("project_id") or _execution_project_id(execution)
    if not data["project_id"] and scoped_project_id:
        data["project_id"] = scoped_project_id
    return data


async def record_execution(
    source_type: str,
    source_id: str,
    project_id: str | None = None,
    source_name: str = "",
    status: str = "success",
    started_at: Optional[datetime] = None,
    finished_at: Optional[datetime] = None,
    error_message: str = "",
    findings_count: int = 0,
    metadata: Optional[dict[str, Any]] = None,
) -> LoopExecution:
    """Create a LoopExecution record and persist it."""
    metadata_payload = dict(metadata or {})
    scoped_project_id = _clean_project_id(project_id) or _clean_project_id(
        metadata_payload.get("project_id")
    )
    if not scoped_project_id:
        raise ValueError("project_id is required for loop execution records")
    metadata_payload["project_id"] = scoped_project_id

    now = datetime.now(timezone.utc)
    start = started_at or now
    end = finished_at

    duration_ms: int | None = None
    if start and end:
        duration_ms = int((end - start).total_seconds() * 1000)

    execution = LoopExecution(
        id=str(uuid.uuid4()),
        source_type=source_type,
        source_id=source_id,
        source_name=source_name,
        project_id=scoped_project_id,
        status=status,
        started_at=start,
        finished_at=end,
        duration_ms=duration_ms,
        error_message=error_message or "",
        findings_count=findings_count,
        metadata_json=json.dumps(metadata_payload, default=str),
        created_at=now,
    )

    async with async_session() as db:
        db.add(execution)
        await db.commit()

    return execution


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

async def list_executions(
    db: AsyncSession,
    *,
    source_type: Optional[str] = None,
    source_types: Optional[list[str]] = None,
    source_id: Optional[str] = None,
    source_ids: Optional[list[str]] = None,
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    started_from: Optional[datetime] = None,
    started_to: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """Paginated list of loop executions with optional filters.

    Returns ``{"items": [...], "total": int, "page": int, "page_size": int}``.
    """
    q = select(LoopExecution).order_by(LoopExecution.started_at.desc())

    if source_types:
        q = q.where(LoopExecution.source_type.in_(source_types))
    elif source_type:
        q = q.where(LoopExecution.source_type == source_type)
    if source_id:
        q = q.where(LoopExecution.source_id == source_id)
    if source_ids is not None:
        q = q.where(LoopExecution.source_id.in_(source_ids) if source_ids else false())
    if status:
        q = q.where(LoopExecution.status == status)
    if started_from:
        q = q.where(LoopExecution.started_at >= started_from)
    if started_to:
        q = q.where(LoopExecution.started_at < started_to)

    safe_page = max(page, 1)
    safe_page_size = min(max(page_size, 1), 100)
    offset = (safe_page - 1) * safe_page_size

    scoped_project_id = _clean_project_id(project_id)
    if scoped_project_id:
        q = q.where(
            or_(
                LoopExecution.project_id == scoped_project_id,
                LoopExecution.project_id == "",
            )
        )
        source_id_scope = set(source_ids) if source_ids is not None else None
        result = await db.execute(q)
        filtered = [
            execution
            for execution in result.scalars().all()
            if _execution_matches_project(execution, scoped_project_id, source_id_scope)
        ]
        total = len(filtered)
        page_items = filtered[offset : offset + safe_page_size]
        items = [_execution_to_dict(execution, scoped_project_id) for execution in page_items]
    else:
        count_q = select(func.count()).select_from(q.subquery())
        total = (await db.execute(count_q)).scalar() or 0

        q = q.offset(offset).limit(safe_page_size)
        result = await db.execute(q)
        items = [_execution_to_dict(execution) for execution in result.scalars().all()]

    return {
        "items": items,
        "total": total,
        "page": safe_page,
        "page_size": safe_page_size,
    }


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

async def get_execution_stats(
    db: AsyncSession,
    source_id: Optional[str] = None,
    source_ids: Optional[list[str]] = None,
    project_id: Optional[str] = None,
) -> dict:
    """Aggregate execution statistics.

    Returns ``{total, success_count, failure_count, success_rate, avg_duration_ms}``.
    """
    base = select(LoopExecution)
    if source_id:
        base = base.where(LoopExecution.source_id == source_id)
    if source_ids is not None:
        base = base.where(LoopExecution.source_id.in_(source_ids) if source_ids else false())

    scoped_project_id = _clean_project_id(project_id)
    if scoped_project_id:
        base = base.where(
            or_(
                LoopExecution.project_id == scoped_project_id,
                LoopExecution.project_id == "",
            )
        )
        source_id_scope = set(source_ids) if source_ids is not None else None
        result = await db.execute(base.order_by(LoopExecution.started_at.desc()))
        executions = [
            execution
            for execution in result.scalars().all()
            if _execution_matches_project(execution, scoped_project_id, source_id_scope)
        ]
        total = len(executions)
        if total == 0:
            return {
                "total": 0,
                "success_count": 0,
                "failure_count": 0,
                "running_count": 0,
                "skipped_count": 0,
                "success_rate": 0.0,
                "avg_duration_ms": 0.0,
            }
        success_count = sum(1 for execution in executions if execution.status == "success")
        failure_count = sum(1 for execution in executions if execution.status == "failure")
        running_count = sum(1 for execution in executions if execution.status == "running")
        skipped_count = sum(1 for execution in executions if execution.status == "skipped")
        durations = [
            execution.duration_ms
            for execution in executions
            if execution.duration_ms is not None
        ]
        avg_duration = sum(durations) / len(durations) if durations else 0.0
        success_rate = (success_count / total * 100) if total > 0 else 0.0
        return {
            "total": total,
            "success_count": success_count,
            "failure_count": failure_count,
            "running_count": running_count,
            "skipped_count": skipped_count,
            "success_rate": round(success_rate, 2),
            "avg_duration_ms": round(float(avg_duration), 2),
        }

    # Total
    total_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(total_q)).scalar() or 0

    if total == 0:
        return {
            "total": 0,
            "success_count": 0,
            "failure_count": 0,
            "running_count": 0,
            "skipped_count": 0,
            "success_rate": 0.0,
            "avg_duration_ms": 0.0,
        }

    # Success count
    success_base = base.where(LoopExecution.status == "success")
    success_q = select(func.count()).select_from(success_base.subquery())
    success_count = (await db.execute(success_q)).scalar() or 0

    # Failure count
    failure_base = base.where(LoopExecution.status == "failure")
    failure_q = select(func.count()).select_from(failure_base.subquery())
    failure_count = (await db.execute(failure_q)).scalar() or 0

    running_base = base.where(LoopExecution.status == "running")
    running_q = select(func.count()).select_from(running_base.subquery())
    running_count = (await db.execute(running_q)).scalar() or 0

    skipped_base = base.where(LoopExecution.status == "skipped")
    skipped_q = select(func.count()).select_from(skipped_base.subquery())
    skipped_count = (await db.execute(skipped_q)).scalar() or 0

    # Average duration
    avg_q = select(func.avg(LoopExecution.duration_ms))
    if source_id:
        avg_q = avg_q.where(LoopExecution.source_id == source_id)
    if source_ids is not None:
        avg_q = avg_q.where(LoopExecution.source_id.in_(source_ids) if source_ids else false())
    avg_q = avg_q.where(LoopExecution.duration_ms.isnot(None))
    avg_duration = (await db.execute(avg_q)).scalar() or 0.0

    success_rate = (success_count / total * 100) if total > 0 else 0.0

    return {
        "total": total,
        "success_count": success_count,
        "failure_count": failure_count,
        "running_count": running_count,
        "skipped_count": skipped_count,
        "success_rate": round(success_rate, 2),
        "avg_duration_ms": round(float(avg_duration), 2),
    }
