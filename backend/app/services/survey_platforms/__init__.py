"""Survey platform adapters — abstract base + concrete implementations.

Each adapter wraps a survey platform's REST API (SurveyMonkey, Google Forms,
Typeform) behind a uniform interface so the ingestion layer can pull responses
regardless of the upstream provider.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class SurveyPlatformAdapter(ABC):
    """Abstract base class for survey platform integrations.

    Subclasses must implement health_check, create_survey, get_responses,
    and register_webhook.  Additional platform-specific methods (e.g.
    list_surveys) may be added as concrete helpers.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    # ------------------------------------------------------------------
    # Required interface
    # ------------------------------------------------------------------

    @abstractmethod
    async def health_check(self) -> dict:
        """Verify the connection to the survey platform.

        Returns a dict with at least ``{"healthy": bool}``.
        """
        ...

    @abstractmethod
    async def create_survey(self, title: str, questions: list[dict]) -> dict:
        """Create a survey on the platform.

        Args:
            title: Survey title.
            questions: List of question dicts (platform-agnostic format):
                ``{"text": str, "type": "open"|"multiple_choice"|"rating", "choices": [...]}``

        Returns:
            Platform response containing at least ``{"id": str, "url": str}``.
        """
        ...

    @abstractmethod
    async def get_responses(self, survey_id: str) -> list[dict]:
        """Fetch all responses for a given survey.

        Returns a list of response dicts, each with an ``"answers"`` key
        containing ``[{"question": str, "answer": str}, ...]``.
        """
        ...

    @abstractmethod
    async def register_webhook(self, survey_id: str, webhook_url: str) -> dict:
        """Register a webhook for new responses.

        Returns platform-specific webhook registration info, or a note
        if the platform does not support webhooks.
        """
        ...

    # ------------------------------------------------------------------
    # Optional helpers (may be overridden)
    # ------------------------------------------------------------------

    async def list_surveys(self) -> list[dict]:
        """List surveys available on the platform.  Default: empty list."""
        return []
