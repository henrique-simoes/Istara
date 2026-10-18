"""Shared adapter conformance suite (CF-SPEC-1, Phase 8).

Every decider protocol Istara speaks must behave the same way at the client boundary: the same
question yields the same canonical distribution, the key travels only in the Authorization header,
a partial vector or a wrong served model is ``not_runnable``, and 429 is retried with
``retry-after``. Each protocol supplies a stub server that renders one canonical answer in its own
wire format; the assertions are shared. OpenRouter is a ``systemone`` endpoint with another base
URL, so it runs through the same protocol case.
"""

import json

import httpx
import pytest

from app.core.decider.client import SystemOneClient
from app.core.decider.contract import Choice, Noul
from app.core.decider.registry import DeciderEndpoint

QUESTIONS = {
    "relation": Choice("Relation?", {"supports": "states it", "contradicts": "opposite"}),
    "grounded": Noul("Exact span?"),
}
CANONICAL = {"relation": {"supports": 0.75, "contradicts": 0.25}, "grounded": 0.9}


def _systemone(model, *, partial=False):
    probabilities = dict(CANONICAL["relation"])
    if partial:
        probabilities.pop("contradicts")
    return {
        "model": model,
        "answers": {
            "relation": {"type": "choice", "probabilities": probabilities},
            "grounded": {"type": "noul", "noul": CANONICAL["grounded"]},
        },
    }


def _openai(model, *, partial=False):
    probabilities = [{"value": k, "probability": v} for k, v in CANONICAL["relation"].items()]
    if partial:
        probabilities.pop()
    return {
        "model": model,
        "answers": [
            {"type": "choice", "name": "relation", "probabilities": probabilities},
            {"type": "predicate", "name": "grounded", "probability": CANONICAL["grounded"]},
        ],
    }


CASES = [
    pytest.param(
        DeciderEndpoint("jev", "https://api.typesafe.ai", "jev-1.14.0"),
        _systemone,
        "https://api.typesafe.ai/v1/systemone",
        id="typesafe-systemone",
    ),
    pytest.param(
        DeciderEndpoint("openrouter-jev", "https://openrouter.ai/api", "typesafe/jev-1.14"),
        _systemone,
        "https://openrouter.ai/api/v1/systemone",
        id="openrouter-systemone",
    ),
    pytest.param(
        DeciderEndpoint(
            "openai", "https://api.openai.com", "gpt-6-luna", protocol="openai_decisions"
        ),
        _openai,
        "https://api.openai.com/v1/decisions",
        id="openai-decisions",
    ),
]


def _client(endpoint, handler, sleeps=None):
    async def sleep(seconds):
        if sleeps is not None:
            sleeps.append(seconds)

    return SystemOneClient(
        endpoint, api_key="sk-conformance", transport=httpx.MockTransport(handler), sleep=sleep
    )


@pytest.mark.parametrize("endpoint,render,url", CASES)
async def test_same_question_same_canonical_answer(endpoint, render, url):
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=render(endpoint.model))

    outcome = await _client(endpoint, handler).decide({"claim": "c"}, QUESTIONS)
    assert outcome.ok, outcome.reason
    assert outcome.answers["relation"] == CANONICAL["relation"]
    assert abs(outcome.answers["grounded"]["true"] - 0.9) < 1e-12
    assert str(seen[0].url) == url
    assert seen[0].headers["authorization"] == "Bearer sk-conformance"
    assert "sk-conformance" not in seen[0].content.decode()
    assert json.loads(seen[0].content)["model"] == endpoint.model


@pytest.mark.parametrize("endpoint,render,url", CASES)
async def test_partial_vectors_and_wrong_models_are_not_runnable(endpoint, render, url):
    partial = await _client(
        endpoint, lambda r: httpx.Response(200, json=render(endpoint.model, partial=True))
    ).decide("s", QUESTIONS)
    assert not partial.ok and partial.reason == "probability_keys_mismatch"
    wrong = await _client(
        endpoint, lambda r: httpx.Response(200, json=render("someone-else"))
    ).decide("s", QUESTIONS)
    assert not wrong.ok and wrong.reason == "served_model_mismatch"


@pytest.mark.parametrize("endpoint,render,url", CASES)
async def test_rate_limits_retry_with_retry_after(endpoint, render, url):
    responses = [
        httpx.Response(429, headers={"retry-after": "2"}),
        httpx.Response(200, json=render(endpoint.model)),
    ]
    sleeps = []
    outcome = await _client(endpoint, lambda r: responses.pop(0), sleeps).decide("s", QUESTIONS)
    assert outcome.ok and outcome.attempts == 2 and sleeps == [2.0]
