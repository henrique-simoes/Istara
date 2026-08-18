"""Provider-neutral adapter contract tests (pure, deterministic, no fallback)."""

from __future__ import annotations

import pytest

from qa.scripts.provider_contracts import (
    ApiShape,
    ChatIdentity,
    ChatReadiness,
    EmbeddingIdentity,
    ProviderError,
    ProviderKind,
    assert_no_fallback,
    readiness_gate,
    vector_space_invariant,
)


def test_chat_identity_requires_exact_model():
    with pytest.raises(ProviderError):
        ChatIdentity(ProviderKind.OLLAMA, ApiShape.NATIVE, "")
    with pytest.raises(ProviderError):
        ChatIdentity(ProviderKind.OLLAMA, ApiShape.NATIVE, "*")
    with pytest.raises(ProviderError):
        ChatIdentity(ProviderKind.OLLAMA, ApiShape.NATIVE, "default")
    identity = ChatIdentity(ProviderKind.OPENAI_COMPAT, ApiShape.OPENAI_COMPAT, "qwen3.5-35b-a3b")
    assert identity.model == "qwen3.5-35b-a3b"


def test_embedding_identity_requires_positive_dim():
    with pytest.raises(ProviderError):
        EmbeddingIdentity("nomic-embed-text", 0)
    identity = EmbeddingIdentity("nomic-embed-text", 768)
    assert identity.model_dim == 768


def test_no_fallback_is_fail_closed():
    assert_no_fallback(False)
    with pytest.raises(ProviderError):
        assert_no_fallback(True)


def test_vector_space_invariant_ok():
    result = vector_space_invariant(
        EmbeddingIdentity("nomic-embed-text", 768),
        EmbeddingIdentity("nomic-embed-text", 768),
    )
    assert result["invariant"] == "ok"
    assert result["dims"] == {"legacy": 768, "pi": 768}


def test_vector_space_invariant_violation_fails_closed():
    with pytest.raises(ProviderError):
        vector_space_invariant(
            EmbeddingIdentity("nomic-embed-text", 768),
            EmbeddingIdentity("nomic-embed-text", 1024),
        )
    with pytest.raises(ProviderError):
        vector_space_invariant(
            EmbeddingIdentity("model-a", 768),
            EmbeddingIdentity("model-b", 768),
        )


def test_readiness_gate_requires_capability_decl_and_secret_handle():
    identity = ChatIdentity(ProviderKind.VLLM, ApiShape.OPENAI_COMPAT, "qwen3")
    # Fail closed: capability declared but no secret_handle (F-4 regression).
    no_secret = readiness_gate(identity, {"capability": "chat"})
    assert isinstance(no_secret, ChatReadiness)
    assert no_secret.healthy is False
    assert "secret_handle" in no_secret.capability_decl["missing"]
    assert no_secret.capability_decl["secret_handle_present"] is False
    # Capability declaration itself is still required.
    missing = readiness_gate(identity, {})
    assert missing.healthy is False
    assert "capability_decl" in missing.capability_decl["missing"]
    assert "secret_handle" in missing.capability_decl["missing"]
    # A non-empty string secret handle (a handle, never the secret value) passes.
    ready = readiness_gate(identity, {"capability": "chat", "secret_handle": "qa-live-openai"})
    assert ready.healthy is True
    assert ready.capability_decl["secret_handle_present"] is True
    # An empty or non-string secret handle still fails closed.
    empty = readiness_gate(identity, {"capability": "chat", "secret_handle": ""})
    assert empty.healthy is False
    assert "secret_handle" in empty.capability_decl["missing"]
    non_string = readiness_gate(identity, {"capability": "chat", "secret_handle": 42})
    assert non_string.healthy is False
    assert "secret_handle" in non_string.capability_decl["missing"]
