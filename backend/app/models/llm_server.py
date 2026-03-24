"""LLM Server model — external LLM endpoints (Ollama, LM Studio, OpenAI-compatible)."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class LLMServer(Base):
    """An LLM server endpoint that ReClaw can route requests to."""

    __tablename__ = "llm_servers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(50), nullable=False)  # ollama | lmstudio | openai_compat
    host: Mapped[str] = mapped_column(String(500), nullable=False)  # Full base URL
    api_key: Mapped[str] = mapped_column(String(500), default="")  # Optional API key
    is_local: Mapped[bool] = mapped_column(Boolean, default=True)
    is_healthy: Mapped[bool] = mapped_column(Boolean, default=False)
    is_relay: Mapped[bool] = mapped_column(Boolean, default=False)  # From a relay node
    priority: Mapped[int] = mapped_column(Integer, default=10)  # Lower = higher priority
    last_health_check: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    capabilities: Mapped[str] = mapped_column(Text, default="{}")  # JSON: models, embed support, etc.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
