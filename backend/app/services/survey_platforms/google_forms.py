"""Google Forms adapter — Service account / OAuth token, Forms API v1."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.services.survey_platforms import SurveyPlatformAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://forms.googleapis.com/v1"


class GoogleFormsAdapter(SurveyPlatformAdapter):
    """Google Forms API v1 wrapper.

    Config keys:
        access_token (str): OAuth 2.0 or service-account Bearer token.
    """

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        token = self.config.get("access_token", "")
        if not token:
            raise ValueError("Google Forms access_token not configured")
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
            return resp.json()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_form_item(question: dict, index: int) -> dict:
        """Translate a platform-agnostic question dict into a Forms API item."""
        q_type = question.get("type", "open")
        item: dict[str, Any] = {
            "title": question.get("text", f"Question {index + 1}"),
        }

        if q_type == "open":
            item["questionItem"] = {
                "question": {
                    "required": False,
                    "textQuestion": {"paragraph": True},
                }
            }
        elif q_type == "multiple_choice":
            choices = question.get("choices", [])
            item["questionItem"] = {
                "question": {
                    "required": False,
                    "choiceQuestion": {
                        "type": "RADIO",
                        "options": [{"value": c} for c in choices],
                    },
                }
            }
        elif q_type == "rating":
            item["questionItem"] = {
                "question": {
                    "required": False,
                    "scaleQuestion": {
                        "low": 1,
                        "high": 5,
                        "lowLabel": "Low",
                        "highLabel": "High",
                    },
                }
            }
        else:
            item["questionItem"] = {
                "question": {
                    "required": False,
                    "textQuestion": {"paragraph": False},
                }
            }

        return item

    # ------------------------------------------------------------------
    # Required interface
    # ------------------------------------------------------------------

    async def health_check(self) -> dict:
        """Try listing forms via Drive API as a connectivity check."""
        try:
            # There is no dedicated /forms listing endpoint. We try
            # fetching a known form or simply verify the token works
            # by creating a minimal request.
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    "https://www.googleapis.com/drive/v3/files",
                    headers=self._headers(),
                    params={
                        "q": "mimeType='application/vnd.google-apps.form'",
                        "pageSize": "1",
                        "fields": "files(id,name)",
                    },
                )
                resp.raise_for_status()
            return {"healthy": True}
        except Exception as exc:
            logger.debug("Google Forms health check failed: %s", exc)
            return {"healthy": False, "error": str(exc)}

    async def create_survey(self, title: str, questions: list[dict]) -> dict:
        """Create a Google Form and add questions via batchUpdate.

        1. POST /v1/forms  — create the form (title only).
        2. POST /v1/forms/{id}:batchUpdate — add question items.
        """
        # Step 1: Create empty form
        create_body = {"info": {"title": title}}
        form_data = await self._request("POST", "/forms", json_body=create_body)
        form_id = form_data.get("formId", "")
        responder_uri = form_data.get("responderUri", "")

        # Step 2: Add questions via batchUpdate
        if questions:
            requests_list: list[dict] = []
            for idx, q in enumerate(questions):
                item = self._build_form_item(q, idx)
                requests_list.append({
                    "createItem": {
                        "item": item,
                        "location": {"index": idx},
                    }
                })

            await self._request(
                "POST",
                f"/forms/{form_id}:batchUpdate",
                json_body={"requests": requests_list},
            )

        return {
            "id": form_id,
            "title": title,
            "url": responder_uri,
            "raw": form_data,
        }

    async def get_responses(self, survey_id: str) -> list[dict]:
        """GET /v1/forms/{id}/responses — normalise into Q/A pairs.

        Also fetches the form definition to resolve question IDs to text.
        """
        # Fetch form definition for question mapping
        form_data = await self._request("GET", f"/forms/{survey_id}")
        question_map: dict[str, str] = {}
        for item in form_data.get("items", []):
            q_item = item.get("questionItem", {})
            q = q_item.get("question", {})
            q_id = q.get("questionId", "")
            if q_id:
                question_map[q_id] = item.get("title", "")

        # Fetch responses
        resp_data = await self._request("GET", f"/forms/{survey_id}/responses")
        raw_responses = resp_data.get("responses", [])

        normalised: list[dict] = []
        for resp in raw_responses:
            answers: list[dict[str, str]] = []
            for q_id, answer_obj in resp.get("answers", {}).items():
                q_text = question_map.get(q_id, q_id)
                text_answers = answer_obj.get("textAnswers", {})
                ans_parts: list[str] = []
                for ta in text_answers.get("answers", []):
                    ans_parts.append(ta.get("value", ""))
                answers.append({
                    "question": q_text,
                    "answer": "; ".join(ans_parts) if ans_parts else "",
                })
            normalised.append({
                "id": resp.get("responseId", ""),
                "answers": answers,
            })

        return normalised

    async def list_surveys(self) -> list[dict]:
        """Google Forms has no native list endpoint.

        Falls back to Drive API to find forms the token has access to.
        """
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.get(
                    "https://www.googleapis.com/drive/v3/files",
                    headers=self._headers(),
                    params={
                        "q": "mimeType='application/vnd.google-apps.form'",
                        "pageSize": "50",
                        "fields": "files(id,name,webViewLink)",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            return [
                {
                    "id": f.get("id", ""),
                    "title": f.get("name", ""),
                    "url": f.get("webViewLink", ""),
                }
                for f in data.get("files", [])
            ]
        except Exception as exc:
            logger.debug("Google Forms list_surveys via Drive failed: %s", exc)
            return []

    async def register_webhook(self, survey_id: str, webhook_url: str) -> dict:
        """Google Forms does not support native webhooks.

        Returns an advisory note suggesting Apps Script or polling.
        """
        return {
            "status": "unsupported",
            "note": (
                "Google Forms does not support native webhooks. "
                "Use Google Apps Script triggers or periodic polling via "
                "the /sync endpoint to pull new responses."
            ),
        }
