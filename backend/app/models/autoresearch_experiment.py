# Inspired by Karpathy's autoresearch (MIT) — https://github.com/karpathy/autoresearch
"""Autoresearch Experiment model — replaces Karpathy's results.tsv with a DB table."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class AutoresearchExperiment(Base):
    """A single autoresearch experiment record.

    Each row represents one iteration of the hypothesize→mutate→evaluate→keep/discard loop.
    Equivalent to one row in Karpathy's results.tsv, but richer.
    """

    __tablename__ = "autoresearch_experiments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    loop_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    # skill_prompt|model_temp|rag_params|persona|question_bank|ui_sim
    target_name: Mapped[str] = mapped_column(String(200), nullable=False)
    hypothesis: Mapped[str] = mapped_column(Text, default="")
    mutation_description: Mapped[str] = mapped_column(Text, default="")
    mutation_diff: Mapped[str] = mapped_column(Text, default="{}")  # JSON diff
    baseline_score: Mapped[float] = mapped_column(Float, default=0.0)
    experiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    delta: Mapped[float] = mapped_column(Float, default=0.0)
    kept: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="running")
    # running|completed|failed|reverted
    config_snapshot: Mapped[str] = mapped_column(Text, default="{}")
    error_message: Mapped[str] = mapped_column(Text, default="")
    project_id: Mapped[str] = mapped_column(String(36), default="")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "loop_type": self.loop_type,
            "target_name": self.target_name,
            "hypothesis": self.hypothesis,
            "mutation_description": self.mutation_description,
            "baseline_score": self.baseline_score,
            "experiment_score": self.experiment_score,
            "delta": self.delta,
            "kept": self.kept,
            "status": self.status,
            "error_message": self.error_message,
            "project_id": self.project_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
