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
    label = Column(String, default="")
    server_url = Column(String, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_redeemed = Column(Boolean, default=False)
    
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
            "server_url": self.server_url,
            "is_active": self.is_active,
            "is_redeemed": self.is_redeemed,
            "expires_at": self.expires_at.isoformat(),
            "created_at": self.created_at.isoformat(),
            "is_expired": now > expires_at
        }
