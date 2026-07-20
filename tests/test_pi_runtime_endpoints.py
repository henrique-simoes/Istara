"""Tests for Pi-private endpoint identity and compute isolation."""

from __future__ import annotations

import pytest

from app.config import PiApiEndpoint
from app.core.pi_runtime.endpoints import PiEndpointResolutionError, PiEndpointResolver


def test_pi_endpoint_resolver_rejects_same_model_identity_mismatch(monkeypatch):
    endpoint = PiApiEndpoint(
        endpoint_id="pi-api",
        provider_kind="openai_compat",
        base_url="https://provider.invalid/v1",
        model="shared-model",
        keychain_service="pi-test",
    )
    monkeypatch.setattr(
        "app.core.pi_runtime.endpoints._read_macos_keychain_secret", lambda *_: "test-key"
    )
    resolver = PiEndpointResolver([endpoint])

    with pytest.raises(PiEndpointResolutionError, match="unknown_pi_endpoint"):
        resolver.resolve("donated-node", model="shared-model")
    with pytest.raises(PiEndpointResolutionError, match="pi_endpoint_model_mismatch"):
        resolver.resolve("pi-api", model="other-model")

    resolved = resolver.resolve("pi-api", model="shared-model")
    assert resolved.telemetry_identity() == {
        "endpoint_id": "pi-api",
        "provider_kind": "openai_compat",
        "model": "shared-model",
    }
    assert "provider.invalid" not in str(resolved.telemetry_identity())


def test_pi_endpoint_resolver_fails_closed_when_keychain_is_empty(monkeypatch):
    endpoint = PiApiEndpoint(
        endpoint_id="pi-api",
        base_url="https://provider.invalid/v1",
        model="model",
        keychain_service="pi-test",
    )
    monkeypatch.setattr(
        "app.core.pi_runtime.endpoints._read_macos_keychain_secret", lambda *_: ""
    )
    with pytest.raises(PiEndpointResolutionError, match="missing_keychain_secret"):
        PiEndpointResolver([endpoint]).resolve("pi-api")
