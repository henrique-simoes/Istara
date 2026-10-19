"""HTTP client for deciders: ``/v1/systemone`` (TypeSafe JEV, OpenRouter, compatible servers) and
OpenAI's ``/v1/decisions``. The endpoint's ``protocol`` picks the wire format; outcomes are the
same canonical distributions either way.

Every failure becomes a ``not_runnable`` outcome with a reason code: transport errors, timeouts,
HTTP errors, malformed or incomplete bodies, and a served model that breaks provenance. Retries
apply only to 429/503/529 and honour ``retry-after``. The API key goes into the Authorization
header and nowhere else.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from app.core.decider.contract import (
    RETRYABLE_STATUSES,
    Choice,
    ContractViolationError,
    DecisionOutcome,
    Noul,
    Score,
    build_request,
    check_served_identity,
    http_failure_reason,
    is_alias_model_id,
    not_runnable,
    parse_response,
    retry_delay,
)
from app.core.decider.openai_decisions import (
    build_decisions_request,
    parse_decisions_response,
    served_matches,
)
from app.core.decider.registry import DeciderEndpoint


class SystemOneClient:
    """One endpoint, one call per :meth:`decide`; build it with ``open_decider``.

    The name predates the second protocol; it serves every protocol in ``registry.PROTOCOLS``.
    """

    def __init__(
        self,
        endpoint: DeciderEndpoint,
        *,
        api_key: str = "",
        transport: Any = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.endpoint = endpoint
        self._api_key = api_key
        self._transport = transport
        self._sleep = sleep

    def __repr__(self) -> str:
        return f"SystemOneClient({self.endpoint!r})"

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _identity(self) -> dict[str, Any]:
        return {
            "endpoint_id": self.endpoint.endpoint_id,
            "requested_model": self.endpoint.model,
            "alias_requested": is_alias_model_id(self.endpoint.model),
        }

    async def decide(
        self, state: Any, questions: Mapping[str, Choice | Score | Noul]
    ) -> DecisionOutcome:
        import httpx

        body = self._build(state, questions)
        started = time.monotonic()
        attempts = 0
        outcome: DecisionOutcome | None = None
        async with httpx.AsyncClient(
            timeout=self.endpoint.timeout_s, transport=self._transport
        ) as http:
            while outcome is None:
                attempts += 1
                try:
                    response = await http.post(
                        self.endpoint.request_url, json=body, headers=self._headers()
                    )
                except httpx.TimeoutException:
                    outcome = not_runnable("timeout")
                    break
                except httpx.HTTPError:
                    outcome = not_runnable("transport_error")
                    break
                retry = response.status_code in RETRYABLE_STATUSES
                if retry and attempts <= self.endpoint.max_retries:
                    await self._sleep(retry_delay(attempts, response.headers.get("retry-after")))
                    continue
                outcome = self._interpret(response, questions)
        outcome.attempts = attempts
        outcome.latency_s = time.monotonic() - started
        for key, value in self._identity().items():
            setattr(outcome, key, value)
        return outcome

    @property
    def _openai(self) -> bool:
        return self.endpoint.protocol == "openai_decisions"

    def _build(self, state: Any, questions: Mapping[str, Choice | Score | Noul]) -> dict[str, Any]:
        if self._openai:
            return build_decisions_request(state, questions, self.endpoint.model)
        return build_request(state, questions, self.endpoint.model)

    def _served_mismatch(self, served: str) -> str | None:
        if self._openai:
            return None if served_matches(self.endpoint.model, served) else "served_model_mismatch"
        return check_served_identity(self.endpoint.model, served)

    def _interpret(
        self, response: Any, questions: Mapping[str, Choice | Score | Noul]
    ) -> DecisionOutcome:
        if response.status_code != 200:
            return not_runnable(http_failure_reason(response.status_code, response.text))
        try:
            payload = response.json()
        except ValueError:
            return not_runnable("malformed_body")
        try:
            parse = parse_decisions_response if self._openai else parse_response
            outcome = parse(payload, questions)
        except ContractViolationError as violation:
            return not_runnable(violation.reason)
        mismatch = self._served_mismatch(outcome.served_model or "")
        if mismatch:
            return not_runnable(mismatch, served_model=outcome.served_model)
        return outcome
