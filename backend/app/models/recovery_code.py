"""One-time account recovery code model."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class RecoveryCode(Base):
    """A hashed one-time recovery code with lifecycle metadata."""

    __tablename__ = "recovery_codes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code_hash: Mapped[str] = mapped_column(Text, nullable=False)
    batch_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    created_by_user_id: Mapped[str] = mapped_column(String(36), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    replaced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    used_ip_hash: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    used_user_agent_hash: Mapped[str] = mapped_column(String(64), default="", nullable=False)
