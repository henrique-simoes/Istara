"""Typeform adapter — Personal API token, REST API."""

from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any

import httpx

from app.services.survey_platforms import SurveyPlatformAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://api.typeform.com"


class TypeformAdapter(SurveyPlatformAdapter):
    """Typeform REST API wrapper.

    Config keys:
        access_token (str): Personal access token (Bearer).
        webhook_secret (str, optional): Shared secret for HMAC-SHA256
            signature verification on incoming webhook payloads.
    """

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        token = self.config.get("access_token", "")
        if not token:
            raise ValueError("Typeform access_token not configured")
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict | None = None,
        params: dict | None = None,
    ) -> dict:
        url = f"{BASE_URL}{path}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.request(
                method, url, headers=self._headers(), json=json_body, params=params
            )
            resp.raise_for_status()
            # Some Typeform endpoints (PUT webhook) may return 204 No Content
            if resp.status_code == 204 or not resp.content:
                return {}
            return resp.json()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_field(question: dict, index: int) -> dict:
        """Translate a platform-agnostic question dict into a Typeform field."""
        q_type = question.get("type", "open")
        field: dict[str, Any] = {
            "title": question.get("text", f"Question {index + 1}"),
        }

        if q_type == "open":
            field["type"] = "long_text"
        elif q_type == "multiple_choice":
            field["type"] = "multiple_choice"
            choices = question.get("choices", [])
            field["properties"] = {
                "choices": [{"label": c} for c in choices],
                "allow_multiple_selection": False,
            }
        elif q_type == "rating":
            field["type"] = "rating"
            field["properties"] = {"steps": 5}
        else:
            field["type"] = "short_text"

        return field

    @staticmethod
    def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
        """Verify Typeform webhook HMAC-SHA256 signature.

        Args:
            payload: Raw request body bytes.
            signature: Value of the ``Typeform-Signature`` header
                       (``sha256=<hex>``).
            secret: The webhook secret configured during registration.

        Returns:
            True if the signature is valid.
        """
        expected = hmac.new(
            secret.encode(), payload, hashlib.sha256
        ).hexdigest()
        provided = signature.removeprefix("sha256=")
        return hmac.compare_digest(expected, provided)

    # ------------------------------------------------------------------
    # Required interface
    # ------------------------------------------------------------------

    async def health_check(self) -> dict:
        """GET /me — verify token validity."""
        try:
            data = await self._request("GET", "/me")
            return {
                "healthy": True,
                "alias": data.get("alias", ""),
                "email": data.get("email", ""),
            }
        except Exception as exc:
            logger.debug("Typeform health check failed: %s", exc)
            return {"healthy": False, "error": str(exc)}

    async def create_survey(self, title: str, questions: list[dict]) -> dict:
        """POST /forms — create a typeform with fields."""
        fields = [self._build_field(q, i) for i, q in enumerate(questions)]

        body: dict[str, Any] = {"title": title, "fields": fields}
        data = await self._request("POST", "/forms", json_body=body)

        return {
            "id": data.get("id", ""),
            "title": data.get("title", title),
            "url": data.get("_links", {}).get("display", ""),
            "raw": data,
        }

    async def get_responses(self, survey_id: str) -> list[dict]:
        """GET /forms/{id}/responses — normalise into Q/A pairs.

        Also fetches the form definition to map field IDs to titles.
        """
        # Fetch form for field mapping
        form_data = await self._request("GET", f"/forms/{survey_id}")
        field_map: dict[str, str] = {}
        for field in form_data.get("fields", []):
            field_map[field.get("id", "")] = field.get("title", "")

        # Fetch responses
        resp_data = await self._request("GET", f"/forms/{survey_id}/responses")
        raw_items = resp_data.get("items", [])

        normalised: list[dict] = []
        for item in raw_items:
            answers: list[dict[str, str]] = []
            for ans in item.get("answers", []):
                field_id = ans.get("field", {}).get("id", "")
                q_text = field_map.get(field_id, field_id)

                # Typeform stores the answer value under a type-specific key
                ans_type = ans.get("type", "")
                if ans_type == "text":
                    value = ans.get("text", "")
                elif ans_type == "choice":
                    value = ans.get("choice", {}).get("label", "")
                elif ans_type == "choices":
                    labels = [c.get("label", "") for c in ans.get("choices", {}).get("labels", [])]
                    value = "; ".join(labels)
                elif ans_type == "number":
                    value = str(ans.get("number", ""))
                elif ans_type == "boolean":
                    value = str(ans.get("boolean", ""))
                elif ans_type == "email":
                    value = ans.get("email", "")
                elif ans_type == "url":
                    value = ans.get("url", "")
                elif ans_type == "date":
                    value = ans.get("date", "")
                else:
                    value = str(ans.get(ans_type, ""))

                answers.append({"question": q_text, "answer": value})

            normalised.append({
                "id": item.get("response_id", item.get("token", "")),
                "answers": answers,
            })

        return normalised

    async def list_surveys(self) -> list[dict]:
        """GET /forms — list all typeforms in the workspace."""
        data = await self._request("GET", "/forms")
        return [
            {
                "id": f.get("id", ""),
                "title": f.get("title", ""),
                "url": f.get("_links", {}).get("display", ""),
            }
            for f in data.get("items", [])
        ]

    async def register_webhook(self, survey_id: str, webhook_url: str) -> dict:
        """PUT /forms/{id}/webhooks/{tag} — register a response webhook.

        Uses HMAC-SHA256 secret if configured.
        """
        tag = f"istara-{survey_id}"
        secret = self.config.get("webhook_secret", "")

        body: dict[str, Any] = {
            "url": webhook_url,
            "enabled": True,
        }
        if secret:
            body["secret"] = secret

        await self._request(
            "PUT", f"/forms/{survey_id}/webhooks/{tag}", json_body=body
        )

        return {
            "webhook_tag": tag,
            "status": "registered",
            "secret_configured": bool(secret),
        }
