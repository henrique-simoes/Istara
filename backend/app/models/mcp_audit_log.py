"""MCP audit log model — tracks every MCP request for security monitoring."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class MCPAuditEntry(Base):
    """Audit trail entry for every MCP server request.

    Every tool invocation and resource access via the MCP server is logged
    here for security monitoring and compliance.
    """

    __tablename__ = "mcp_audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    arguments_json: Mapped[str] = mapped_column(Text, default="{}")
    caller_info: Mapped[str] = mapped_column(String(500), default="")
    policy_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    access_granted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    result_summary: Mapped[str] = mapped_column(Text, default="")
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "tool_name": self.tool_name,
            "caller_info": self.caller_info,
            "access_granted": self.access_granted,
            "result_summary": self.result_summary,
            "duration_ms": self.duration_ms,
        }
