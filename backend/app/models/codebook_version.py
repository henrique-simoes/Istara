"""Codebook versioning — persistent, versioned codebooks per project.

Academic gold standard (Saldaña, 2021): each code has 6 components:
label, brief_definition, full_definition, exclusion_criteria,
typical_example, boundary_example.
"""

from datetime import UTC, datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


def _json_list(value: str | None) -> list:
    import json

    if not value:
        return []
    try:
        parsed = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []
    return parsed if isinstance(parsed, list) else []


class CodebookVersion(Base):
    __tablename__ = "codebook_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    codes_json: Mapped[str] = mapped_column(Text, default="[]")
    change_log: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(100), default="")
    methodology: Mapped[str] = mapped_column(String(30), default="codebook_ta")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "version": self.version,
            "codes": _json_list(self.codes_json),
            "change_log": self.change_log,
            "created_by": self.created_by,
            "methodology": self.methodology,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
