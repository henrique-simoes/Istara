"""Project-owned Interfaces integration credentials."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.field_encryption import decrypt_field, encrypt_field
from app.models.database import Base
from app.models.project import Project as _Project  # noqa: F401 - registers relationship target


class ProjectInterfaceConfig(Base):
    """Encrypted Stitch/Figma credentials scoped to one Istara project."""

    __tablename__ = "project_interface_configs"

    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id"),
        primary_key=True,
    )
    stitch_api_key_encrypted: Mapped[str] = mapped_column(Text, default="")
    figma_api_token_encrypted: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    project = relationship("Project")

    def set_stitch_api_key(self, value: str) -> None:
        self.stitch_api_key_encrypted = encrypt_field(value.strip())

    def set_figma_api_token(self, value: str) -> None:
        self.figma_api_token_encrypted = encrypt_field(value.strip())

    @property
    def stitch_api_key(self) -> str:
        return decrypt_field(self.stitch_api_key_encrypted or "")

    @property
    def figma_api_token(self) -> str:
        return decrypt_field(self.figma_api_token_encrypted or "")

    @property
    def stitch_configured(self) -> bool:
        return bool(self.stitch_api_key)

    @property
    def figma_configured(self) -> bool:
        return bool(self.figma_api_token)
