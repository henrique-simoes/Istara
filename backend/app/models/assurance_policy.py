"""A project's assurance mode: which evaluators validate its candidate outputs.

No row means ``auto``, the behaviour before modes existed. See ``app.core.assurance``.
"""

import json
from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


def _now() -> datetime:
    return datetime.now(UTC)


class ProjectAssurancePolicy(Base):
    __tablename__ = "project_assurance_policies"

    project_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    mode: Mapped[str] = mapped_column(String(20), default="auto")
    llm_method: Mapped[str] = mapped_column(String(30), default="auto")
    llm_judges: Mapped[int] = mapped_column(Integer, default=3)
    decider_endpoint_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    updated_by: Mapped[str] = mapped_column(String(36), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    def decider_endpoint_ids(self) -> list[str]:
        try:
            parsed = json.loads(self.decider_endpoint_ids_json or "[]")
        except (json.JSONDecodeError, TypeError):
            return []
        if not isinstance(parsed, list):
            return []
        return [str(item) for item in parsed if isinstance(item, str) and item.strip()]
