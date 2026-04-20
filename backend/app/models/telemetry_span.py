"""Telemetry Span model — lightweight trace spans for observability.

Stores operational metadata (what happened, how long, did it work, which model)
WITHOUT any user content, prompts, responses, or project data.

Local-first and zero-trust by design: data stays on the user's machine unless
they explicitly opt in to sharing (TELEMETRY_ENABLED=false by default).
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class TelemetrySpan(Base):
    """A single observability span for an agent operation."""

    __tablename__ = "telemetry_spans"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: __import__("uuid").uuid4().hex[:36]
    )
    trace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    parent_id: Mapped[str | None] = mapped_column(String(36), nullable=True, default=None)

    operation: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # "skill_execute", "validation", "llm_request", "tool_call",
    # "file_process", "transcribe_audio"

    skill_name: Mapped[str] = mapped_column(String(100), default="", index=True)
    model_name: Mapped[str] = mapped_column(String(200), default="", index=True)
    agent_id: Mapped[str] = mapped_column(String(36), default="")

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0)

    status: Mapped[str] = mapped_column(String(20), default="success")
    # "success", "error", "timeout", "degraded"

    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    consensus_score: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)

    error_type: Mapped[str | None] = mapped_column(String(50), nullable=True, default=None)
    # "json_parse", "hallucination", "timeout", "rate_limit",
    # "context_length", "navigation_failed", "other"

    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None)

    project_id: Mapped[str] = mapped_column(String(36), default="", index=True)
    task_id: Mapped[str | None] = mapped_column(String(36), nullable=True, default=None)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)

    tool_name: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)
    tool_success: Mapped[bool | None] = mapped_column(Integer, nullable=True, default=None)
    tool_duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)

    source: Mapped[str] = mapped_column(String(20), default="production")
    # "production" or "autoresearch"

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
