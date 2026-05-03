"""Connection String model — persists generated team invite strings."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Boolean
from app.models.database import Base

class ConnectionString(Base):
    """A generated connection string for team members or compute donation."""
    __tablename__ = "connection_strings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    connection_string = Column(String, unique=True, index=True, nullable=False)
    token_type = Column(String, default="user_invite")  # user_invite | compute_donation
    label = Column(String, default="")
    server_url = Column(String, nullable=False)
    ws_url = Column(String, default="")
    intended_role = Column(String, default="researcher")
    
    # Status
    is_active = Column(Boolean, default=True)
    is_redeemed = Column(Boolean, default=False)
    redeemed_by_user_id = Column(String, nullable=True)
    redeemed_username = Column(String, nullable=True)
    redeemed_at = Column(DateTime, nullable=True)
    last_validated_at = Column(DateTime, nullable=True)
    
    # Expiration
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        now = datetime.now(timezone.utc)
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
            
        return {
            "id": self.id,
            "label": self.label,
            "connection_string": self.connection_string,
            "token_type": self.token_type or "user_invite",
            "server_url": self.server_url,
            "ws_url": self.ws_url,
            "intended_role": self.intended_role,
            "is_active": self.is_active,
            "is_redeemed": self.is_redeemed,
            "redeemed_by_user_id": self.redeemed_by_user_id,
            "redeemed_username": self.redeemed_username,
            "redeemed_at": self.redeemed_at.isoformat() if self.redeemed_at else None,
            "last_validated_at": self.last_validated_at.isoformat() if self.last_validated_at else None,
            "expires_at": self.expires_at.isoformat(),
            "created_at": self.created_at.isoformat(),
            "is_expired": now > expires_at
        }
