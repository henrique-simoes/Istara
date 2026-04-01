"""Project member access control — per-project user permissions."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class ProjectMember(Base):
    """Links a user to a project with a role (admin/member/viewer)."""

    __tablename__ = "project_members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    role: Mapped[str] = mapped_column(String(20), default="member")  # admin | member | viewer
    added_by: Mapped[str] = mapped_column(String(36), default="")
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_active: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "user_id": self.user_id,
            "role": self.role,
            "added_by": self.added_by,
            "added_at": self.added_at.isoformat() if self.added_at else None,
            "last_active": self.last_active.isoformat() if self.last_active else None,
        }
