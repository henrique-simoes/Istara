# Inspired by Karpathy's autoresearch (MIT) — https://github.com/karpathy/autoresearch
"""Model-Skill Statistics — tracks quality per (skill, model, temperature) combination."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class ModelSkillStats(Base):
    """Tracks quality metrics for each (skill_name, model_name, temperature) tuple.

    Populated by both production executions and autoresearch Loop 6 (model/temp optimization).
    The leaderboard query finds the best model+temperature per skill.
    """

    __tablename__ = "model_skill_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    skill_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    temperature: Mapped[float] = mapped_column(Float, default=0.7)
    executions: Mapped[int] = mapped_column(Integer, default=0)
    total_quality: Mapped[float] = mapped_column(Float, default=0.0)
    quality_ema: Mapped[float] = mapped_column(Float, default=0.5)  # EMA alpha=0.1
    best_quality: Mapped[float] = mapped_column(Float, default=0.0)
    source: Mapped[str] = mapped_column(String(20), default="production")  # production|autoresearch
    last_used: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "skill_name": self.skill_name,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "executions": self.executions,
            "avg_quality": self.total_quality / self.executions if self.executions else 0,
            "quality_ema": self.quality_ema,
            "best_quality": self.best_quality,
            "source": self.source,
            "last_used": self.last_used.isoformat() if self.last_used else None,
        }
