"""H-4: Pi endpoint secret resolution — TTL cache, env fallback, no loop stalls.

Keychain reads must never run on the event loop on every turn: they go through
``asyncio.to_thread`` behind a per-endpoint 60 s TTL cache, and non-macOS hosts
fall back to the ``ISTARA_PI_SECRET_<ID>`` environment variable (parity with
``resolve_llm_fallback_api_key``). No node worker is needed for any of this.
"""

from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace

import pytest

from app.config import PiApiEndpoint
from app.core.pi_runtime import endpoint_policy
from app.core.pi_runtime import endpoints as endpoints_module
from app.core.pi_runtime.endpoints import PiEndpointResolutionError, PiEndpointResolver


def _endpoint(endpoint_id: str = "pi-test") -> PiApiEndpoint:
    return PiApiEndpoint(
        endpoint_id=endpoint_id,
        provider_kind="openai_compat",
        base_url="https://pi.example.test",
        model="pi-model",
        keychain_service="svc-pi-test",
        keychain_account="acct",
    )


def test_env_fallback_supplies_secret_without_keychain(monkeypatch):
    """``ISTARA_PI_SECRET_<ID>`` wins; Keychain is never touched."""
    monkeypatch.setenv("ISTARA_PI_SECRET_PI_TEST", "env-secret-123")

    def _boom(service, account=""):
        raise AssertionError("keychain must not be read when the env secret is set")

    monkeypatch.setattr(endpoints_module, "_read_macos_keychain_secret", _boom)

    resolved = PiEndpointResolver([_endpoint()]).resolve("pi-test")
    assert resolved.api_key == "env-secret-123"


def test_keychain_secret_cached_per_endpoint_with_ttl(monkeypatch):
    """A second resolution inside the 60 s TTL does not re-read Keychain."""
    monkeypatch.delenv("ISTARA_PI_SECRET_PI_TEST", raising=False)
    reads: list[tuple[str, str]] = []

    def fake_keychain(service, account=""):
        reads.append((service, account))
        return "kc-secret"

    monkeypatch.setattr(endpoints_module, "_read_macos_keychain_secret", fake_keychain)

    resolver = PiEndpointResolver([_endpoint()])
    assert resolver.resolve("pi-test").api_key == "kc-secret"
    assert resolver.resolve("pi-test").api_key == "kc-secret"
    assert reads == [("svc-pi-test", "acct")]

    # TTL expiry forces a fresh read.
    monkeypatch.setattr(endpoints_module, "SECRET_CACHE_TTL_SECONDS", 0)
    assert resolver.resolve("pi-test").api_key == "kc-secret"
    assert reads == [("svc-pi-test", "acct"), ("svc-pi-test", "acct")]


def test_missing_secret_fails_closed(monkeypatch):
    """No env secret and no Keychain item → typed resolution error, never a key."""
    monkeypatch.delenv("ISTARA_PI_SECRET_PI_TEST", raising=False)
    monkeypatch.setattr(
        endpoints_module, "_read_macos_keychain_secret", lambda *a, **k: ""
    )

    with pytest.raises(PiEndpointResolutionError, match="missing_keychain_secret"):
        PiEndpointResolver([_endpoint()]).resolve("pi-test")


def test_api_key_custody_persists_endpoint_env_secret_in_linux_docker(monkeypatch):
    """Linux Docker has no Keychain, so POST custody must persist the env fallback."""
    import app.config as app_config
    from app.core import env_persistence

    monkeypatch.setattr(endpoint_policy.sys, "platform", "linux")
    monkeypatch.setattr(
        app_config,
        "_write_macos_keychain_secret",
        lambda *args, **kwargs: pytest.fail(
            "Linux Docker must not attempt macOS Keychain custody"
        ),
    )
    persisted: list[tuple[str, str]] = []
    monkeypatch.setattr(
        env_persistence,
        "persist_env_value",
        lambda key, value: persisted.append((key, value)),
    )

    endpoint_policy._custody_api_key(
        SimpleNamespace(api_key="sk-docker-test"),
        {
            "endpoint_id": "dashscope-qwen",
            "keychain_service": "istara-pi-dashscope",
            "keychain_account": "default",
        },
    )

    assert persisted == [("ISTARA_PI_SECRET_DASHSCOPE_QWEN", "sk-docker-test")]


@pytest.mark.asyncio
async def test_aresolve_slow_secret_read_does_not_stall_event_loop(monkeypatch):
    """A 0.3 s blocking secret read must not stall a concurrent ticker task."""
    monkeypatch.delenv("ISTARA_PI_SECRET_PI_TEST", raising=False)

    def slow_read(endpoint):
        time.sleep(0.3)
        return "slow-secret"

    monkeypatch.setattr(endpoints_module, "_read_endpoint_secret", slow_read)
    resolver = PiEndpointResolver([_endpoint()])

    delays: list[float] = []

    async def ticker() -> None:
        for _ in range(10):
            start = time.monotonic()
            await asyncio.sleep(0.02)
            delays.append(time.monotonic() - start - 0.02)

    resolved, _ = await asyncio.gather(resolver.aresolve("pi-test"), ticker())

    assert resolved.api_key == "slow-secret"
    assert delays, "ticker never ran"
    # A loop stall would show up as ~0.3 s of unscheduled time on one tick.
    assert max(delays) < 0.2, f"event loop stalled: max tick delay {max(delays):.3f}s"

    # The off-thread read populated the same TTL cache used by the sync path.
    assert resolver.resolve("pi-test").api_key == "slow-secret"
