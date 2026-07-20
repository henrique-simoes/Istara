"""Agentic usage ledger — one durable, queryable row per dispatcher invocation.

Complements ``telemetry_spans``: spans keep short identity/route handles for
tracing, while this table carries the full accounting contract (tokens, cost,
outcome, exact-vs-estimated flag) so benchmarks and cost ceilings can query
usage without parsing packed identity fields. Content-free by design: counts
and identities only, never prompts, responses, URLs, or keys.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class AgenticUsageRow(Base):
    """The §5.5 one-row-per-dispatch accounting contract."""

    __tablename__ = "agentic_usage_rows"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: __import__("uuid").uuid4().hex[:36]
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )

    engine: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    # "pi" or "legacy"
    purpose: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(String(36), default="", index=True)
    agent_id: Mapped[str] = mapped_column(String(36), default="")
    task_id: Mapped[str | None] = mapped_column(String(36), nullable=True, default=None, index=True)
    spine_phase: Mapped[str] = mapped_column(String(40), default="")
    # The fixed 10-phase taxonomy (intent ... governance); "" when untagged.

    endpoint_id: Mapped[str] = mapped_column(String(120), default="")
    node_id: Mapped[str] = mapped_column(String(120), default="")
    model: Mapped[str] = mapped_column(String(200), default="", index=True)

    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_read: Mapped[int] = mapped_column(Integer, default=0)
    cache_write: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)

    tool_calls: Mapped[int] = mapped_column(Integer, default=0)
    turns: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    stop_reason: Mapped[str] = mapped_column(String(60), default="")

    outcome: Mapped[str] = mapped_column(String(20), default="success", index=True)
    # "success", "error", "aborted"
    estimate: Mapped[bool] = mapped_column(Integer, default=0)
    # 1 only when provider usage was absent and tokens were estimated locally;
    # exact provider-reported (Pi or legacy) rows are always 0.
    error_type: Mapped[str] = mapped_column(String(80), default="")
