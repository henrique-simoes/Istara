"""WebAuthn / Passkey credential model for passwordless authentication.

Stores FIDO2/WebAuthn credentials for users who register passkeys.
Each credential is tied to a specific authenticator (device).
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class WebAuthnCredential(Base):
    """A single WebAuthn credential (passkey) registered to a user.

    A user can have multiple credentials (primary device, backup device, security key).
    """

    __tablename__ = "webauthn_credentials"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    credential_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    credential_public_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    sign_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    aaguid: Mapped[str | None] = mapped_column(String(64), nullable=True, default=None)
    transports: Mapped[str] = mapped_column(Text, default="[]", nullable=False)  # JSON array

    # Attestation metadata
    attestation_object: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    client_data_json: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)

    # Friendly label for the user
    label: Mapped[str] = mapped_column(String(100), default="Passkey", nullable=False)

    # Device attestation — what type of authenticator created this
    authenticator_type: Mapped[str | None] = mapped_column(String(50), nullable=True, default=None)  # "platform" | "cross-platform"

    # Revocation
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
