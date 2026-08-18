"""Provider-neutral chat/embedding contract primitives (QA-side, deterministic).

This is the pure, importable core behind the provider-neutral adapter contract
from the winning master plan (section 9). It intentionally imports nothing from
the backend so it can run in CI without backend dependencies and cannot form
import cycles. The backend's ``assert_vector_space_invariant`` remains the
authoritative runtime guard; this module mirrors its *contract semantics* for
QA lanes and fail-closed tests.

Rules encoded here:
  * exact chat identity (provider, api_shape, model) — never a wildcard;
  * readiness requires identity + capability declaration;
  * NO FALLBACK: any QA lane that enables a provider sets fallback disabled
    semantics; a mismatch is a typed failure, never a silent retry elsewhere.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ProviderKind(str, Enum):
    OLLAMA = "ollama"
    LMSTUDIO = "lmstudio"
    OPENAI_COMPAT = "openai_compat"
    VLLM = "vllm"
    SGLANG = "sglang"
    LLAMACPP = "llamacpp"
    MLX = "mlx"
    ANTHROPIC = "anthropic"


class ApiShape(str, Enum):
    NATIVE = "native"
    OPENAI_COMPAT = "openai_compat"
    ANTHROPIC_COMPAT = "anthropic_compat"


class ProviderError(Exception):
    """Typed failure for provider contract violations (fail-closed)."""


@dataclass(frozen=True)
class ChatIdentity:
    """Exact chat provider identity. Model is the EXACT id, never a wildcard."""

    provider: ProviderKind
    api_shape: ApiShape
    model: str

    def __post_init__(self) -> None:
        if not self.model or self.model in ("*", "default", ""):
            raise ProviderError(
                f"ChatIdentity model must be an exact model id, got {self.model!r}"
            )
        if "*" in self.model:
            raise ProviderError(
                f"ChatIdentity model must not contain a wildcard, got {self.model!r}"
            )


@dataclass(frozen=True)
class ChatReadiness:
    """Readiness record for one explicitly selected chat target."""

    identity: ChatIdentity
    healthy: bool
    capability_decl: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EmbeddingIdentity:
    """Exact embedding identity: one model, one declared dimension."""

    model: str
    model_dim: int

    def __post_init__(self) -> None:
        if not self.model or self.model in ("*", "default", ""):
            raise ProviderError(
                f"EmbeddingIdentity model must be exact, got {self.model!r}"
            )
        if self.model_dim <= 0:
            raise ProviderError(f"EmbeddingIdentity model_dim must be > 0, got {self.model_dim}")


def assert_no_fallback(enabled: bool) -> None:
    """QA lanes must run with fallback disabled (fail-closed)."""
    if enabled:
        raise ProviderError(
            "LLM fallback must be disabled in QA lanes; a failure is a red lane, "
            "never a silent retry on another provider"
        )


def vector_space_invariant(
    legacy: EmbeddingIdentity, pi: EmbeddingIdentity
) -> dict[str, Any]:
    """Contract mirror of backend ``assert_vector_space_invariant``.

    Both engine paths must agree on model and dimension; a mismatch raises the
    typed ProviderError so QA lanes fail closed.
    """
    if legacy.model != pi.model or legacy.model_dim != pi.model_dim:
        raise ProviderError(
            "vector_space_invariant_violation: "
            f"legacy model/dim={legacy.model!r}/{legacy.model_dim!r}, "
            f"pi model/dim={pi.model!r}/{pi.model_dim!r}"
        )
    return {
        "provider": "embedding",
        "model": legacy.model,
        "dims": {"legacy": legacy.model_dim, "pi": pi.model_dim},
        "invariant": "ok",
    }


def readiness_gate(identity: ChatIdentity, capability_decl: dict[str, Any]) -> ChatReadiness:
    """Fail-closed readiness: identity present, secret-handle present, capability declared.

    Never prints a secret value; only presence is checked. A missing, empty, or
    non-string ``secret_handle`` makes the gate fail closed (F-4): a live report
    is green only when a secret handle is present without ever being printed.
    """
    missing: list[str] = []
    if not identity.provider:
        missing.append("provider")
    if not identity.model:
        missing.append("model")
    if not capability_decl.get("capability"):
        missing.append("capability_decl")
    secret_handle = capability_decl.get("secret_handle")
    secret_handle_present = bool(
        secret_handle and isinstance(secret_handle, str) and secret_handle.strip()
    )
    if not secret_handle_present:
        missing.append("secret_handle")
    healthy = not missing
    return ChatReadiness(
        identity=identity,
        healthy=healthy,
        capability_decl={
            "capability": capability_decl.get("capability"),
            "secret_handle_present": secret_handle_present,
            "missing": missing,
        },
    )
