"""Code application records — every code applied to source text.

Full audit trail: WHO coded WHAT, WHERE in source, WHY that code,
and whether it was human-reviewed. Based on O'Connor & Joffe (2020)
ICR guidelines and Lincoln & Guba (1985) audit trail requirements.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class CodeApplication(Base):
    __tablename__ = "code_applications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    codebook_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    code_id: Mapped[str] = mapped_column(String(100), nullable=False)

    source_document_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_text: Mapped[str] = mapped_column(Text, default="")
    source_location: Mapped[str] = mapped_column(String(200), default="")

    coder_id: Mapped[str] = mapped_column(String(100), default="")
    coder_type: Mapped[str] = mapped_column(String(20), default="llm")
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    reasoning: Mapped[str] = mapped_column(Text, default="")

    review_status: Mapped[str] = mapped_column(String(20), default="pending")
    reviewed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id, "project_id": self.project_id,
            "code_id": self.code_id, "source_text": self.source_text,
            "source_location": self.source_location,
            "coder_id": self.coder_id, "coder_type": self.coder_type,
            "confidence": self.confidence, "reasoning": self.reasoning,
            "review_status": self.review_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
