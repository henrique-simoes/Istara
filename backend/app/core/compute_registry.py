"""Unified Compute Registry facade for all Istara LLM compute.

The implementation is split into focused modules while this facade preserves
legacy imports such as ``app.core.compute_registry.ComputeRegistry`` and the
singleton ``compute_registry``.
"""

from __future__ import annotations

from app.core.compute_node import ComputeNode
from app.core.compute_registry_core import ComputeRegistry
from app.core.compute_registry_helpers import (
    LMSTUDIO_MODEL_LOAD_LOCK,
    PROVIDER_ALIASES,
    TRANSIENT_CHAT_BASE_DELAY_S,
    TRANSIENT_CHAT_MAX_ATTEMPTS,
    TRANSIENT_CHAT_MAX_DELAY_S,
    TRANSIENT_HTTP_STATUS_CODES,
    infer_provider_type,
    normalize_provider_type,
)


async def check_all_health() -> dict[str, bool]:
    """Re-probe all registered nodes and sync detected context windows."""
    results = await compute_registry.check_all_health()
    if results:
        for node_name, healthy in results.items():
            if healthy:
                node = compute_registry._nodes.get(node_name)
                if node:
                    for _model_name, cap in node.model_capabilities.items():
                        ctx = cap.get("context_length", 0) if isinstance(cap, dict) else 0
                        if ctx > 0:
                            from app.config import settings

                            settings.update_context_window(ctx)
                            break
    return results


compute_registry = ComputeRegistry()

__all__ = [
    "ComputeNode",
    "ComputeRegistry",
    "LMSTUDIO_MODEL_LOAD_LOCK",
    "PROVIDER_ALIASES",
    "TRANSIENT_CHAT_BASE_DELAY_S",
    "TRANSIENT_CHAT_MAX_ATTEMPTS",
    "TRANSIENT_CHAT_MAX_DELAY_S",
    "TRANSIENT_HTTP_STATUS_CODES",
    "check_all_health",
    "compute_registry",
    "infer_provider_type",
    "normalize_provider_type",
]
