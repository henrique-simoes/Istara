"""Method Metric model — tracks validation method performance for adaptive learning."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class MethodMetric(Base):
    """Tracks which validation method works best per project/skill/agent."""

    __tablename__ = "method_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    skill_name: Mapped[str] = mapped_column(String(100), default="")
    agent_id: Mapped[str] = mapped_column(String(36), default="")
    method: Mapped[str] = mapped_column(String(50), nullable=False)  # dual_run, adversarial_review, etc.
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_consensus_score: Mapped[float] = mapped_column(Float, default=0.0)
    total_runs: Mapped[int] = mapped_column(Integer, default=0)
    weight: Mapped[float] = mapped_column(Float, default=1.0)  # Adaptive weight with recency bias
    last_used: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
