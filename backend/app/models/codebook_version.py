"""Codebook versioning — persistent, versioned codebooks per project.

Academic gold standard (Saldaña, 2021): each code has 6 components:
label, brief_definition, full_definition, exclusion_criteria,
typical_example, boundary_example.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


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
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict:
        import json
        return {
            "id": self.id, "project_id": self.project_id,
            "version": self.version,
            "codes": json.loads(self.codes_json) if self.codes_json else [],
            "change_log": self.change_log, "created_by": self.created_by,
            "methodology": self.methodology,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
