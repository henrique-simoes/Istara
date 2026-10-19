"""SystemOneClient against stub ``/v1/systemone`` servers (CF-SPEC-1, Phase 1).

``httpx.MockTransport`` stands in for TypeSafe's JEV API and for a llama.cpp-style local server; no
network is used. Every failure must surface as ``not_runnable`` with a reason, never as a verdict,
and the API key must appear only in the Authorization header.
"""

import json

import httpx
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.decider.access import open_decider
from app.core.decider.client import SystemOneClient
from app.core.decider.contract import Choice, Noul
from app.core.decider.registry import DeciderEndpoint, DeciderUnavailableError, parse_endpoints
from app.models.decision_policy import DecisionModelProjectPolicy

QUESTIONS = {
    "relation": Choice(
        "How does the section relate to the claim?",
        {"supports": "states it", "contradicts": "states the opposite", "says_nothing": "silent"},
    ),
    "grounded": Noul("Is the quote an exact span of the evidence unit?"),
}
JEV = DeciderEndpoint("jev", "https://api.typesafe.ai", "jev-1.13.0", max_retries=2)
LOCAL = DeciderEndpoint("kev", "http://127.0.0.1:8081", "kev-4b")


def _answer(model: str = "jev-1.13.0") -> dict:
    return {
        "model": model,
        "answers": {
            "relation": {
                "type": "choice",
                "choice": "supports",
                "probabilities": {"supports": 0.93, "contradicts": 0.02, "says_nothing": 0.05},
                "confidence": 0.9,
            },
            "grounded": {"type": "noul", "noul": 0.97},
        },
        "usage": {"input_tokens": 120, "output_tokens": 6},
    }


class Stub:
    """Replays queued responses and records requests."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


async def _no_sleep(_seconds: float) -> None:
    return None


def _client(endpoint, stub, key="sk-secret-test", sleeps=None):
    async def sleep(seconds: float) -> None:
        if sleeps is not None:
            sleeps.append(seconds)

    return SystemOneClient(
        endpoint, api_key=key, transport=httpx.MockTransport(stub), sleep=sleep
    )


async def test_jev_answer_is_parsed_with_provenance_and_auth_header():
    stub = Stub(httpx.Response(200, json=_answer()))
    outcome = await _client(JEV, stub).decide({"claim": "c", "section": "s"}, QUESTIONS)
    assert outcome.ok and outcome.served_model == "jev-1.13.0"
    assert outcome.endpoint_id == "jev" and not outcome.alias_requested and outcome.attempts == 1
    assert outcome.answers["relation"]["supports"] == 0.93
    request = stub.requests[0]
    assert str(request.url) == "https://api.typesafe.ai/v1/systemone"
    assert request.headers["authorization"] == "Bearer sk-secret-test"
    sent = json.loads(request.content)
    assert sent["model"] == "jev-1.13.0" and set(sent["questions"]) == {"relation", "grounded"}
    assert "sk-secret-test" not in repr(outcome)


async def test_local_llama_cpp_style_server_needs_no_key():
    stub = Stub(httpx.Response(200, json=_answer("kev-4b")))
    outcome = await _client(LOCAL, stub, key="").decide("state", QUESTIONS)
    assert outcome.ok and outcome.served_model == "kev-4b"
    assert "authorization" not in stub.requests[0].headers
    assert str(stub.requests[0].url) == "http://127.0.0.1:8081/v1/systemone"


async def test_served_model_must_match_a_pinned_request():
    outcome = await _client(JEV, Stub(httpx.Response(200, json=_answer("jev-1.14.0")))).decide(
        "s", QUESTIONS
    )
    assert outcome.status == "not_runnable" and outcome.reason == "served_model_mismatch"
    assert outcome.served_model == "jev-1.14.0" and outcome.answers == {}


async def test_alias_request_records_the_served_version():
    alias = DeciderEndpoint("jev-alias", "https://api.typesafe.ai", "jev-latest")
    outcome = await _client(alias, Stub(httpx.Response(200, json=_answer()))).decide("s", QUESTIONS)
    assert outcome.ok and outcome.alias_requested and outcome.served_model == "jev-1.13.0"


async def test_rate_limits_retry_with_retry_after_then_succeed():
    sleeps: list[float] = []
    stub = Stub(
        httpx.Response(429, headers={"retry-after": "2"}),
        httpx.Response(529),
        httpx.Response(200, json=_answer()),
    )
    outcome = await _client(JEV, stub, sleeps=sleeps).decide("s", QUESTIONS)
    assert outcome.ok and outcome.attempts == 3 and sleeps == [2.0, 1.0]


async def test_retries_are_bounded():
    stub = Stub(*[httpx.Response(429) for _ in range(3)])
    outcome = await _client(JEV, stub, sleeps=[]).decide("s", QUESTIONS)
    assert outcome.reason == "rate_limited" and outcome.attempts == 3


@pytest.mark.parametrize(
    ("response", "reason"),
    [
        (httpx.Response(400, json={"error": "max_tokens_exceeded"}), "max_tokens_exceeded"),
        (httpx.Response(401, json={"error": "bad key"}), "unauthorized"),
        (httpx.Response(422, json={"error": "questions.relation"}), "validation_failed"),
        (httpx.Response(500, text="boom"), "http_500"),
        (httpx.Response(200, text="not json"), "malformed_body"),
        (httpx.Response(200, json={"model": "jev-1.13.0", "answers": {}}), "missing_answer"),
        (httpx.ReadTimeout("slow"), "timeout"),
        (httpx.ConnectError("down"), "transport_error"),
    ],
)
async def test_failures_are_not_runnable_never_verdicts(response, reason):
    outcome = await _client(JEV, Stub(response)).decide("s", QUESTIONS)
    assert outcome.status == "not_runnable" and outcome.reason == reason
    assert outcome.answers == {}


async def _policy_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(DecisionModelProjectPolicy.__table__.create)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def test_open_decider_enforces_hosted_opt_in_and_key(monkeypatch):
    engine, maker = await _policy_session()
    endpoints = parse_endpoints(
        json.dumps(
            [
                {
                    "endpoint_id": "jev",
                    "base_url": "https://api.typesafe.ai",
                    "model": "jev-1.13.0",
                    "api_key_env": "ISTARA_TEST_TYPESAFE_KEY",
                }
            ]
        )
    )
    try:
        async with maker() as session:
            with pytest.raises(DeciderUnavailableError) as denied:
                await open_decider("jev", "p1", session=session, endpoints=endpoints)
            assert denied.value.reason == "hosted_egress_not_authorized"

            policy = DecisionModelProjectPolicy(project_id="p1")
            policy.set_hosted_egress_endpoint_ids(["jev", " jev ", ""])
            session.add(policy)
            await session.commit()
            assert policy.hosted_egress_endpoint_ids() == ["jev"]

            monkeypatch.delenv("ISTARA_TEST_TYPESAFE_KEY", raising=False)
            with pytest.raises(DeciderUnavailableError) as no_key:
                await open_decider("jev", "p1", session=session, endpoints=endpoints)
            assert no_key.value.reason == "missing_api_key"

            monkeypatch.setenv("ISTARA_TEST_TYPESAFE_KEY", "sk-from-env")
            client = await open_decider("jev", "p1", session=session, endpoints=endpoints)
            assert isinstance(client, SystemOneClient) and "sk-from-env" not in repr(client)

            with pytest.raises(DeciderUnavailableError) as other_project:
                await open_decider("jev", "p2", session=session, endpoints=endpoints)
            assert other_project.value.reason == "hosted_egress_not_authorized"
    finally:
        await engine.dispose()
