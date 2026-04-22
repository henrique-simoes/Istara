"""User database model for multi-user team mode."""

import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Integer, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base
from app.core.field_encryption import EncryptedType


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    RESEARCHER = "researcher"
    VIEWER = "viewer"


class User(Base):
    """An Istara user (team mode)."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(EncryptedType, nullable=False)
    email_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.RESEARCHER)
    display_name: Mapped[str] = mapped_column(String(200), default="")
    preferences: Mapped[str] = mapped_column(Text, default="{}")  # JSON: theme, ui density, etc.

    # Multi-factor authentication (MFA)
    totp_secret: Mapped[str | None] = mapped_column(String(64), nullable=True, default=None)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Recovery codes (stored as newline-separated Argon2id hashes)
    recovery_codes_hashed: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)

    # WebAuthn / Passkey support
    passkey_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
