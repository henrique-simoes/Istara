"""MCP access policy model — granular permission control for MCP server exposure.

SECURITY: ReClaw is local-first. MCP breaks that boundary by allowing external
agents to query local research data. Every tool/resource is gated by this policy.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class MCPAccessPolicy(Base):
    """Granular access control for what external agents can see/do via MCP.

    Each tool and resource has an individual toggle with risk classification:
    - LOW: Read-only, non-sensitive (skill catalog, project names, status)
    - SENSITIVE: Exposes research data (findings, memory, project context)
    - HIGH RISK: Can modify data or trigger external actions (execute skills, deploy research)

    All SENSITIVE and HIGH RISK permissions are OFF by default.
    """

    __tablename__ = "mcp_access_policies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), default="Default Policy")
    description: Mapped[str] = mapped_column(Text, default="")
    is_default: Mapped[bool] = mapped_column(Boolean, default=True)

    # Tool permissions — LOW risk (default ON)
    allow_list_skills: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_list_projects: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_get_deployment_status: Mapped[bool] = mapped_column(Boolean, default=True)

    # Tool permissions — SENSITIVE (default OFF)
    allow_get_findings: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_search_memory: Mapped[bool] = mapped_column(Boolean, default=False)

    # Tool permissions — HIGH RISK (default OFF)
    allow_execute_skill: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_create_project: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_deploy_research: Mapped[bool] = mapped_column(Boolean, default=False)

    # Resource permissions — SENSITIVE (default OFF)
    allow_project_resource: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_findings_resource: Mapped[bool] = mapped_column(Boolean, default=False)

    # Resource permissions — LOW (default ON)
    allow_skills_resource: Mapped[bool] = mapped_column(Boolean, default=True)

    # Scope limits
    allowed_project_ids_json: Mapped[str] = mapped_column(Text, default="[]")  # empty = none, ["*"] = all
    max_findings_per_request: Mapped[int] = mapped_column(Integer, default=50)
    max_skill_executions_per_hour: Mapped[int] = mapped_column(Integer, default=5)

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
            "description": self.description,
            "is_default": self.is_default,
            "tools": {
                "list_skills": {"allowed": self.allow_list_skills, "risk": "low"},
                "list_projects": {"allowed": self.allow_list_projects, "risk": "low"},
                "get_deployment_status": {"allowed": self.allow_get_deployment_status, "risk": "low"},
                "get_findings": {"allowed": self.allow_get_findings, "risk": "sensitive"},
                "search_memory": {"allowed": self.allow_search_memory, "risk": "sensitive"},
                "execute_skill": {"allowed": self.allow_execute_skill, "risk": "high"},
                "create_project": {"allowed": self.allow_create_project, "risk": "high"},
                "deploy_research": {"allowed": self.allow_deploy_research, "risk": "high"},
            },
            "resources": {
                "project": {"allowed": self.allow_project_resource, "risk": "sensitive"},
                "findings": {"allowed": self.allow_findings_resource, "risk": "sensitive"},
                "skills": {"allowed": self.allow_skills_resource, "risk": "low"},
            },
            "limits": {
                "allowed_project_ids": json.loads(self.allowed_project_ids_json) if self.allowed_project_ids_json else [],
                "max_findings_per_request": self.max_findings_per_request,
                "max_skill_executions_per_hour": self.max_skill_executions_per_hour,
            },
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
