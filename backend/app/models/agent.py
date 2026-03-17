"""Agent and A2A message database models."""

from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class AgentRole(str, enum.Enum):
    TASK_EXECUTOR = "task_executor"
    DEVOPS_AUDIT = "devops_audit"
    UI_AUDIT = "ui_audit"
    UX_EVALUATION = "ux_evaluation"
    USER_SIMULATION = "user_simulation"
    CUSTOM = "custom"


class AgentState(str, enum.Enum):
    IDLE = "idle"
    WORKING = "working"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"


class HeartbeatStatus(str, enum.Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    ERROR = "error"
    STOPPED = "stopped"


ALL_CAPABILITIES = [
    "web_search",
    "file_upload",
    "skill_execution",
    "task_creation",
    "findings_write",
    "chat",
    "rag_retrieval",
    "a2a_messaging",
]

DEFAULT_CAPABILITIES = [
    "skill_execution",
    "task_creation",
    "findings_write",
    "chat",
    "rag_retrieval",
    "a2a_messaging",
]


class Agent(Base):
    """A ReClaw agent (main or sub-agent)."""

    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    role: Mapped[AgentRole] = mapped_column(Enum(AgentRole), default=AgentRole.CUSTOM)
    system_prompt: Mapped[str] = mapped_column(Text, default="")
    capabilities: Mapped[str] = mapped_column(Text, default="[]")  # JSON list
    memory: Mapped[str] = mapped_column(Text, default="{}")  # JSON dict
    heartbeat_interval_seconds: Mapped[int] = mapped_column(Integer, default=60)
    heartbeat_status: Mapped[HeartbeatStatus] = mapped_column(
        Enum(HeartbeatStatus), default=HeartbeatStatus.STOPPED
    )
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    state: Mapped[AgentState] = mapped_column(
        Enum(AgentState), default=AgentState.IDLE
    )
    current_task: Mapped[str] = mapped_column(String(500), default="")
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    executions: Mapped[int] = mapped_column(Integer, default=0)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self) -> dict:
        import json
        return {
            "id": self.id,
            "name": self.name,
            "avatar_path": self.avatar_path,
            "role": self.role.value if self.role else "custom",
            "system_prompt": self.system_prompt,
            "capabilities": json.loads(self.capabilities) if self.capabilities else [],
            "memory": json.loads(self.memory) if self.memory else {},
            "heartbeat_interval_seconds": self.heartbeat_interval_seconds,
            "heartbeat_status": self.heartbeat_status.value if self.heartbeat_status else "stopped",
            "last_heartbeat_at": self.last_heartbeat_at.isoformat() if self.last_heartbeat_at else None,
            "state": self.state.value if self.state else "idle",
            "current_task": self.current_task,
            "error_count": self.error_count,
            "executions": self.executions,
            "is_system": self.is_system,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class A2AMessage(Base):
    """Inter-agent (Agent-to-Agent) message."""

    __tablename__ = "a2a_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    from_agent_id: Mapped[str] = mapped_column(String(36), nullable=False)
    to_agent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)  # null = broadcast
    message_type: Mapped[str] = mapped_column(String(50), nullable=False)  # consult, finding, status, request, response
    content: Mapped[str] = mapped_column(Text, nullable=False)
    extra_data: Mapped[str] = mapped_column(Text, default="{}")  # JSON
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict:
        import json
        return {
            "id": self.id,
            "from_agent_id": self.from_agent_id,
            "to_agent_id": self.to_agent_id,
            "message_type": self.message_type,
            "content": self.content,
            "metadata": json.loads(self.extra_data) if self.extra_data else {},
            "read": self.read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
