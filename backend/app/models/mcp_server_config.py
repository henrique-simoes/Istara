"""MCP server configuration model — stores connected external MCP servers."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class MCPServerConfig(Base):
    """Configuration for an external MCP server connected to ReClaw.

    Used by the MCP Client Registry to discover and invoke tools
    from external MCP servers.
    """

    __tablename__ = "mcp_server_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    transport: Mapped[str] = mapped_column(String(20), default="http")  # http|stdio|websocket
    headers_json: Mapped[str] = mapped_column(Text, default="{}")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    tools_json: Mapped[str] = mapped_column(Text, default="[]")  # cached tool list from discovery
    last_discovery_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    health_status: Mapped[str] = mapped_column(String(20), default="unknown")  # healthy|unhealthy|unknown
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict:
        import json
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "transport": self.transport,
            "is_active": self.is_active,
            "tools": json.loads(self.tools_json) if self.tools_json else [],
            "last_discovery_at": self.last_discovery_at.isoformat() if self.last_discovery_at else None,
            "health_status": self.health_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
