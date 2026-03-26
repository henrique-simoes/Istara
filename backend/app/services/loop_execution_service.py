"""Loop execution service — record, query, and aggregate execution data."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import async_session
from app.models.loop_execution import LoopExecution

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Record execution
# ---------------------------------------------------------------------------

async def record_execution(
    source_type: str,
    source_id: str,
    source_name: str = "",
    status: str = "success",
    started_at: Optional[datetime] = None,
    finished_at: Optional[datetime] = None,
    error_message: str = "",
    findings_count: int = 0,
    metadata: Optional[dict[str, Any]] = None,
) -> LoopExecution:
    """Create a LoopExecution record and persist it."""
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
        status=status,
        started_at=start,
        finished_at=end,
        duration_ms=duration_ms,
        error_message=error_message or "",
        findings_count=findings_count,
        metadata_json=json.dumps(metadata or {}, default=str),
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
    source_id: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """Paginated list of loop executions with optional filters.

    Returns ``{"items": [...], "total": int, "page": int, "page_size": int}``.
    """
    q = select(LoopExecution).order_by(LoopExecution.started_at.desc())

    if source_type:
        q = q.where(LoopExecution.source_type == source_type)
    if source_id:
        q = q.where(LoopExecution.source_id == source_id)
    if status:
        q = q.where(LoopExecution.status == status)

    # Count
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Paginate
    offset = (max(page, 1) - 1) * page_size
    q = q.offset(offset).limit(page_size)

    result = await db.execute(q)
    items = [e.to_dict() for e in result.scalars().all()]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

async def get_execution_stats(
    db: AsyncSession,
    source_id: Optional[str] = None,
) -> dict:
    """Aggregate execution statistics.

    Returns ``{total, success_count, failure_count, success_rate, avg_duration_ms}``.
    """
    base = select(LoopExecution)
    if source_id:
        base = base.where(LoopExecution.source_id == source_id)

    # Total
    total_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(total_q)).scalar() or 0

    if total == 0:
        return {
            "total": 0,
            "success_count": 0,
            "failure_count": 0,
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

    # Average duration
    avg_q = select(func.avg(LoopExecution.duration_ms))
    if source_id:
        avg_q = avg_q.where(LoopExecution.source_id == source_id)
    avg_q = avg_q.where(LoopExecution.duration_ms.isnot(None))
    avg_duration = (await db.execute(avg_q)).scalar() or 0.0

    success_rate = (success_count / total * 100) if total > 0 else 0.0

    return {
        "total": total,
        "success_count": success_count,
        "failure_count": failure_count,
        "success_rate": round(success_rate, 2),
        "avg_duration_ms": round(float(avg_duration), 2),
    }
