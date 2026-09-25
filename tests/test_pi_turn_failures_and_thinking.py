"""A failed provider turn tells its caller why; an endpoint's configured thinking level is used.

Found in passing while probing the live lane (2026-09-25). Z.ai's GLM-5.3-flash always reasons, so
a request that turns thinking off is refused with HTTP 400 ("This model always engages in thinking
and cannot be disabled; please use low, high, or max"). Two defects hid that:

* The endpoint's ``thinking_level`` was never read. ``PiApiEndpoint`` had no such field (pydantic
  dropped it), and only a per-turn ``TurnParams.thinking_mode`` reached the worker, which the chat
  controls send and every other path (skills, coding runs, evaluations) does not. So GLM-5.3-flash
  failed everywhere except chat, whatever its endpoint said.
* The engine returns the provider's reason in ``error``, and the dispatcher dropped it: every
  ``TurnResult`` it built left ``error`` as ``None``, so callers saw ``status="error"`` and nothing
  else.
"""

from __future__ import annotations

import pytest

from app.config import PiApiEndpoint
from app.core.agentic.dispatcher import AgenticDispatcher
from app.core.agentic.types import TurnParams
from app.core.pi_runtime.endpoints import PiEndpointResolver

PROVIDER_400 = (
    '400: {"code":"1210","message":"This model always engages in thinking and cannot be disabled;'
    ' please use low, high, or max"}'
)


class _FailingPi:
    """A Pi service whose provider refuses every turn, as Z.ai does."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def _failed(self) -> dict:
        return {
            "status": "error",
            "error": PROVIDER_400,
            "text": "",
            "tool_calls": [],
            "usage": {},
            "endpoint_id": "pi-zai-glm",
            "model": "glm-5.3-flash",
        }

    async def run_completion(self, **kwargs):
        self.calls.append("completion")
        return self._failed()

    async def run_react(self, **kwargs):
        self.calls.append("react")
        return self._failed()


@pytest.fixture
def dispatcher(monkeypatch):
    d = AgenticDispatcher(pi_service=_FailingPi())

    async def _no_record(**kwargs):
        return None

    monkeypatch.setattr(d, "_record_outcome", _no_record)
    return d


async def test_a_failed_completion_carries_the_provider_reason(dispatcher):
    result = await dispatcher.completion(
        purpose="test.failure",
        project_id="p",
        system=None,
        messages=[{"role": "user", "content": "hi"}],
        params=TurnParams(endpoint_id="pi-zai-glm"),
        engine="pi",
    )
    assert result.status == "error"
    assert result.error == PROVIDER_400


def _endpoint(**extra) -> PiApiEndpoint:
    return PiApiEndpoint(
        endpoint_id="pi-zai-glm",
        base_url="https://example.invalid/v1",
        model="glm-5.3-flash",
        keychain_service="svc",
        pi_provider="zai",
        **extra,
    )


def _resolved(endpoint: PiApiEndpoint):
    return PiEndpointResolver([endpoint])._build(endpoint, "k")


def test_the_endpoint_thinking_level_is_kept():
    assert getattr(_resolved(_endpoint(thinking_level="low")), "thinking_level", None) == "low"


def test_a_bare_turn_uses_the_endpoint_thinking_level_and_a_turn_can_override_it():
    from app.core.pi_runtime.engine import _turn_bind_params

    resolved = _resolved(_endpoint(thinking_level="low"))
    assert _turn_bind_params(TurnParams(), resolved).get("thinking_level") == "low"
    assert _turn_bind_params(TurnParams(thinking_mode="high"), resolved)["thinking_level"] == "high"


def test_an_endpoint_without_a_thinking_level_binds_as_before():
    from app.core.pi_runtime.engine import _turn_bind_params

    assert "thinking_level" not in _turn_bind_params(TurnParams(), _resolved(_endpoint()))


def test_an_unknown_thinking_level_is_refused():
    with pytest.raises(ValueError):
        _endpoint(thinking_level="extreme")
