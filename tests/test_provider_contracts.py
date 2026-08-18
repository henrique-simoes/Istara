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


def test_readiness_gate_requires_capability_decl():
    identity = ChatIdentity(ProviderKind.VLLM, ApiShape.OPENAI_COMPAT, "qwen3")
    ready = readiness_gate(identity, {"capability": "chat"})
    assert isinstance(ready, ChatReadiness)
    assert ready.healthy is True
    missing = readiness_gate(identity, {})
    assert missing.healthy is False
    assert "capability_decl" in missing.capability_decl["missing"]
