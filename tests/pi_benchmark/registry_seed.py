"""Compatibility-only ComputeRegistry fixture for legacy routing unit tests.

The live benchmark no longer imports this module: both ``pi`` and ``legacy``
benchmark arms use the shared PiModelManager endpoint, and ``engine="legacy"``
changes only loop semantics. These helpers remain narrowly scoped to tests that
exercise the retired ComputeRegistry adapter in isolation, so historical
compatibility behavior is explicit without making it a benchmark or production
model-management authority.

Isolation contract (do not weaken):

- The node is a plain network server — NEVER ``is_relay``/``source="relay"`` —
  so donor semantics, donor authorization, and the ``pi_runtime`` isolation
  invariant (``test_same_model_donor_isolation.py``) are untouched.
- Registration is in-memory and process-local: the ComputeRegistry is a module
  singleton, so the seed lives only inside the benchmark process. Nothing is
  persisted to the database or written to settings.
- The API key is resolved at runtime through ``DeepSeekProvider.load_api_key()``
  (env var or macOS Keychain), held in memory only, and never logged.
- Import-safe at T0: no backend imports happen at module import time.
"""

from __future__ import annotations

from typing import Any

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-v4-pro"

# Historical identity of the isolated compatibility fixture. Live benchmark route
# admission intentionally does not accept this endpoint.
BENCHMARK_NODE_ID = "benchmark-deepseek-registry"
BENCHMARK_NODE_NAME = "Benchmark DeepSeek (registry-seeded)"


def ensure_benchmark_legacy_node(*, api_key: str) -> Any:
    """Idempotently register the benchmark DeepSeek node in the ComputeRegistry.

    Returns the registered/updated node id. Safe to call before every dispatch:
    an existing node gets its key/health/model list refreshed in place. The
    ``is_healthy=True`` seed means the first dispatch is not gated on a health
    probe; the registry's own transient-failure handling still applies per call.
    """
    if not api_key or not api_key.strip():
        raise ValueError("benchmark registry seed requires a non-empty API key")
    from app.core.llm_router import LLMServerEntry, llm_router  # lazy (live path only)

    existing = llm_router._nodes.get(BENCHMARK_NODE_ID)
    if existing is not None:
        existing.api_key = api_key
        existing.is_healthy = True
        if DEEPSEEK_MODEL not in list(getattr(existing, "loaded_models", []) or []):
            existing.loaded_models = [*list(getattr(existing, "loaded_models", []) or []), DEEPSEEK_MODEL]
        return BENCHMARK_NODE_ID

    entry = LLMServerEntry(
        server_id=BENCHMARK_NODE_ID,
        name=BENCHMARK_NODE_NAME,
        host=DEEPSEEK_BASE_URL,
        provider_type="openai_compat",
        api_key=api_key,
        priority=1,  # prefer the seeded node over any ambient network entries
        is_local=False,
        is_relay=False,
        is_healthy=True,
        available_models=[DEEPSEEK_MODEL],
        model_capabilities={},
    )
    llm_router.register_server(entry)
    return BENCHMARK_NODE_ID


def remove_benchmark_legacy_node() -> None:
    """Remove the seeded node (test isolation)."""
    from app.core.llm_router import llm_router  # lazy

    if BENCHMARK_NODE_ID in llm_router._nodes:
        llm_router.remove_node(BENCHMARK_NODE_ID)


def is_benchmark_route(endpoint_id: str | None, route: dict | None = None) -> bool:
    """True when route evidence points at the seeded benchmark node (AC-7)."""
    if endpoint_id == BENCHMARK_NODE_ID:
        return True
    if route and str(route.get("node_id") or "") == BENCHMARK_NODE_ID:
        return True
    return False
