"""Per-project authorization for sending research data to hosted decision models.

No row means no hosted decider may receive this project's data (owner decision DEC-1, 2026-10-17).
Local deciders, whose data stays on the user's hardware, need no row.
"""

import json
from datetime import UTC, datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class DecisionModelProjectPolicy(Base):
    """Which hosted decider endpoints a project has opted in to."""

    __tablename__ = "decision_model_project_policies"

    project_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    hosted_egress_endpoint_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    updated_by: Mapped[str] = mapped_column(String(36), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def hosted_egress_endpoint_ids(self) -> list[str]:
        try:
            parsed = json.loads(self.hosted_egress_endpoint_ids_json or "[]")
        except (json.JSONDecodeError, TypeError):
            return []
        if not isinstance(parsed, list):
            return []
        return [str(item) for item in parsed if isinstance(item, str) and item]

    def set_hosted_egress_endpoint_ids(self, endpoint_ids: list[str]) -> None:
        cleaned = sorted({str(item).strip() for item in endpoint_ids if str(item).strip()})
        self.hosted_egress_endpoint_ids_json = json.dumps(cleaned)
