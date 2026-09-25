"""Local models are judged by progress, not by a two-minute stopwatch (DEC-10, 2026-09-25).

Every Pi run had one fixed 120 s wall clock, and the supervisor waited at most 120 s between
frames. ``timeout_ms`` was capped at 120 s too. A local model that streams steadily (the owner's
local Qwen3.8-27B thinks at about 15 tokens/s) was killed at 120 s however healthy it was, while Istara
is local-first. The industry pattern separates the two questions: is the model still producing
(an idle timeout between streamed events), and is the run within a generous total budget (the
OpenAI and Anthropic SDKs default to 10 minutes, llama.cpp's server to an hour). Defaults now
depend on whether the endpoint is local.
"""

from __future__ import annotations

import asyncio

import pytest

from app.config import PiApiEndpoint
from app.core.pi_runtime.endpoints import PiEndpointResolver


def _endpoint(base_url: str, **extra) -> PiApiEndpoint:
    return PiApiEndpoint(
        endpoint_id="pi-test",
        base_url=base_url,
        model="m",
        keychain_service="svc",
        **extra,
    )


def _resolved(endpoint: PiApiEndpoint):
    return PiEndpointResolver([endpoint])._build(endpoint, "k")


LOCAL_URLS = [
    "http://127.0.0.1:8080/v1",
    "http://localhost:11434",
    "http://192.168.1.20:8080/v1",
    "http://10.0.0.5/v1",
    "http://172.20.0.3:11434",
    "http://100.101.102.103:8080/v1",  # Tailscale (CGNAT 100.64.0.0/10)
    "http://gpu-box.tail1234.ts.net:8080/v1",
    "http://host.docker.internal:1234/v1",
    "http://ollama:11434",  # a Docker service name
    "http://[::1]:8080",
    "http://[fd12::1]:8080",
    "http://studio.local:8080",
]
REMOTE_URLS = [
    "https://api.z.ai/api/paas/v4",
    "https://api.meta.ai/v1",
    "https://openrouter.ai/api/v1",
    "http://8.8.8.8/v1",
]


@pytest.mark.parametrize("url", LOCAL_URLS)
def test_local_hosts_get_the_local_budget(url):
    resolved = _resolved(_endpoint(url))
    assert getattr(resolved, "is_local", None) is True
    assert resolved.idle_timeout_ms == 300_000
    assert resolved.max_run_ms == 3_600_000


@pytest.mark.parametrize("url", REMOTE_URLS)
def test_remote_hosts_get_the_remote_budget(url):
    resolved = _resolved(_endpoint(url))
    assert getattr(resolved, "is_local", None) is False
    assert resolved.idle_timeout_ms == 120_000
    assert resolved.max_run_ms == 600_000


def test_explicit_locality_and_budgets_win():
    assert _resolved(_endpoint("https://gpu-box.example.org/v1", locality="local")).is_local
    tuned = _resolved(
        _endpoint("http://127.0.0.1:8080/v1", idle_timeout_ms=90_000, max_run_ms=7_200_000)
    )
    assert (tuned.idle_timeout_ms, tuned.max_run_ms) == (90_000, 7_200_000)


def test_a_response_may_take_longer_than_two_minutes_to_start():
    # A local server can load weights before it answers; 120 s was the ceiling.
    assert _endpoint("http://127.0.0.1:8080/v1", timeout_ms=300_000).timeout_ms == 300_000


def test_the_session_carries_the_endpoint_budgets_and_the_supervisor_waits_longer():
    from app.core.pi_runtime.engine import _session_limits
    from app.core.pi_runtime.supervisor import PiRuntimeSupervisor

    resolved = _resolved(_endpoint("http://127.0.0.1:8080/v1"))
    limits = _session_limits(resolved)
    assert limits == {"max_wall_clock_ms": 3_600_000, "max_idle_ms": 300_000}

    sup = PiRuntimeSupervisor(run_timeout=120.0)
    sent: list[dict] = []

    async def _send(frame):
        sent.append(frame)
        sup._sessions[frame["session_key"]].put_nowait({"type": "session.opened"})

    sup._send = _send

    async def _open():
        await sup.open_session(
            "s1", system_prompt="", history=[], revision=None, catalog=[], limits=limits
        )

    asyncio.run(_open())
    assert sent[0]["limits"]["max_wall_clock_ms"] == 3_600_000
    assert sent[0]["limits"]["max_idle_ms"] == 300_000
    # The worker owns the stream and reports the precise error; Python must not give up first.
    assert sup._frame_wait("s1") > 300


def test_an_unknown_locality_is_refused():
    with pytest.raises(ValueError):
        _endpoint("http://127.0.0.1:8080/v1", locality="nearby")
