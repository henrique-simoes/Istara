"""SurveyMonkey adapter — OAuth 2.0 Bearer token, REST v3 API."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.services.survey_platforms import SurveyPlatformAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://api.surveymonkey.com/v3"


class SurveyMonkeyAdapter(SurveyPlatformAdapter):
    """SurveyMonkey REST API v3 wrapper.

    Config keys:
        access_token (str): OAuth 2.0 Bearer token.
    """

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        token = self.config.get("access_token", "")
        if not token:
            raise ValueError("SurveyMonkey access_token not configured")
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
    # Required interface
    # ------------------------------------------------------------------

    async def health_check(self) -> dict:
        """GET /v3/users/me — verify token validity."""
        try:
            data = await self._request("GET", "/users/me")
            return {"healthy": True, "username": data.get("username", "")}
        except Exception as exc:
            logger.debug("SurveyMonkey health check failed: %s", exc)
            return {"healthy": False, "error": str(exc)}

    async def create_survey(self, title: str, questions: list[dict]) -> dict:
        """POST /v3/surveys with pages/questions.

        Translates the platform-agnostic question format into SurveyMonkey's
        page → question hierarchy.
        """
        sm_questions: list[dict[str, Any]] = []
        for q in questions:
            q_type = q.get("type", "open")
            sm_q: dict[str, Any] = {"headings": [{"heading": q.get("text", "")}]}

            if q_type == "open":
                sm_q["family"] = "open_ended"
                sm_q["subtype"] = "essay"
            elif q_type == "multiple_choice":
                sm_q["family"] = "single_choice"
                sm_q["subtype"] = "vertical"
                choices = q.get("choices", [])
                sm_q["answers"] = {
                    "choices": [{"text": c} for c in choices]
                }
            elif q_type == "rating":
                sm_q["family"] = "matrix"
                sm_q["subtype"] = "rating"
                sm_q["answers"] = {
                    "choices": [{"text": str(i)} for i in range(1, 6)]
                }
            else:
                sm_q["family"] = "open_ended"
                sm_q["subtype"] = "essay"

            sm_questions.append(sm_q)

        body: dict[str, Any] = {
            "title": title,
            "pages": [
                {
                    "title": "Page 1",
                    "questions": sm_questions,
                }
            ],
        }

        data = await self._request("POST", "/surveys", json_body=body)
        return {
            "id": str(data.get("id", "")),
            "title": data.get("title", title),
            "url": data.get("preview", ""),
            "raw": data,
        }

    async def get_responses(self, survey_id: str) -> list[dict]:
        """GET /v3/surveys/{id}/responses/bulk — normalise into Q/A pairs."""
        data = await self._request("GET", f"/surveys/{survey_id}/responses/bulk")
        raw_responses = data.get("data", [])

        normalised: list[dict] = []
        for resp in raw_responses:
            answers: list[dict[str, str]] = []
            for page in resp.get("pages", []):
                for question in page.get("questions", []):
                    q_heading = ""
                    for h in question.get("headings", []):
                        q_heading = h.get("heading", "")
                        break
                    answer_texts: list[str] = []
                    for ans in question.get("answers", []):
                        answer_texts.append(
                            ans.get("text", ans.get("choice_id", ""))
                        )
                    answers.append({
                        "question": q_heading,
                        "answer": "; ".join(answer_texts) if answer_texts else "",
                    })
            normalised.append({
                "id": str(resp.get("id", "")),
                "answers": answers,
            })

        return normalised

    async def list_surveys(self) -> list[dict]:
        """GET /v3/surveys — list all surveys in the account."""
        data = await self._request("GET", "/surveys")
        return [
            {
                "id": str(s.get("id", "")),
                "title": s.get("title", ""),
                "url": s.get("href", ""),
            }
            for s in data.get("data", [])
        ]

    async def register_webhook(self, survey_id: str, webhook_url: str) -> dict:
        """POST /v3/webhooks — register for response_completed events."""
        body = {
            "name": f"reclaw-{survey_id}",
            "event_type": "response_completed",
            "object_type": "survey",
            "object_ids": [survey_id],
            "subscription_url": webhook_url,
        }
        data = await self._request("POST", "/webhooks", json_body=body)
        return {
            "webhook_id": str(data.get("id", "")),
            "status": "registered",
            "raw": data,
        }
