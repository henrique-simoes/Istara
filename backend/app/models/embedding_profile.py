"""Persisted authority for Istara's single canonical embedding vector space."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class EmbeddingProfile(Base):
    """One immutable version of the Pi-managed embedding identity."""

    __tablename__ = "embedding_profiles"
    __table_args__ = (
        UniqueConstraint("profile_id", "version", name="uq_embedding_profile_version"),
        Index(
            "uq_embedding_profiles_single_active",
            "is_active",
            unique=True,
            sqlite_where=text("is_active = 1"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    profile_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    model_id: Mapped[str] = mapped_column(String(255), nullable=False)
    endpoint_id: Mapped[str] = mapped_column(String(255), nullable=False)
    transport: Mapped[str] = mapped_column(String(50), nullable=False, default="pi_http")
    dimension: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    dtype: Mapped[str] = mapped_column(String(40), nullable=False, default="float")
    normalization: Mapped[str] = mapped_column(
        String(60), nullable=False, default="provider_native"
    )
    cache_namespace: Mapped[str] = mapped_column(String(320), nullable=False)
    health_status: Mapped[str] = mapped_column(String(40), nullable=False, default="unknown")
    migration_source: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    activated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
