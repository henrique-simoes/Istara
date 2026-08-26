"""Durable execution ledger for Pi authority tool mutations.

The Pi worker is allowed to retry transport, and a caller may resume a turn
after a process interruption.  A mutation therefore needs a server-owned
execution record before the authority is invoked.  Completed outcomes can be
replayed; an unfinished record is deliberately not retried automatically.
"""

from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class PiToolExecution(Base):
    """One project-scoped, idempotent Pi authority tool invocation."""

    __tablename__ = "pi_tool_executions"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_pi_tool_execution_project_key",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    args_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    operation: Mapped[str] = mapped_column(String(100), default="")
    worker_session_key: Mapped[str] = mapped_column(String(255), default="")
    run_id: Mapped[str] = mapped_column(String(100), default="")
    tool_call_id: Mapped[str] = mapped_column(String(160), default="")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="started", index=True)
    result_json: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
