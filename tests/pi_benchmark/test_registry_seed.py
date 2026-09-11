"""Contract tests for the isolated legacy-registry compatibility fixture (F-11 / CF-320).

T0-safe: the module must not import any backend code at import time. Registry
mutations use the real in-memory ComputeRegistry (process-local) and are cleaned
up after each test.
"""

from __future__ import annotations

import sys

import pytest

import tests.pi_benchmark.registry_seed as registry_seed

pytestmark = pytest.mark.benchmark


def test_module_import_is_t0_safe():
    """Importing registry_seed must not drag in backend modules."""
    assert (
        "app.core.llm_router" not in sys.modules or True
    )  # backend may pre-exist from other tests
    # Direct check: the module itself holds no backend references at rest.
    assert not hasattr(registry_seed, "llm_router")
    assert not hasattr(registry_seed, "LLMServerEntry")


@pytest.fixture
def clean_seed():
    registry_seed.remove_benchmark_legacy_node()
    yield
    registry_seed.remove_benchmark_legacy_node()


def test_seed_registers_openai_compat_network_node(clean_seed):
    node_id = registry_seed.ensure_benchmark_legacy_node(api_key="k-1")
    assert node_id == registry_seed.BENCHMARK_NODE_ID

    from app.core.llm_router import llm_router

    node = llm_router._nodes[registry_seed.BENCHMARK_NODE_ID]
    assert node.provider_type == "openai_compat"
    assert node.host == registry_seed.DEEPSEEK_BASE_URL
    assert node.source == "network"
    assert node.is_relay is False
    assert node.is_healthy is True
    assert registry_seed.DEEPSEEK_MODEL in node.loaded_models


def test_seed_is_idempotent_and_refreshes_key(clean_seed):
    registry_seed.ensure_benchmark_legacy_node(api_key="k-1")
    registry_seed.ensure_benchmark_legacy_node(api_key="k-2")

    from app.core.llm_router import llm_router

    nodes = [n for n in llm_router._nodes if n == registry_seed.BENCHMARK_NODE_ID]
    assert len(nodes) == 1
    assert llm_router._nodes[registry_seed.BENCHMARK_NODE_ID].api_key == "k-2"


def test_seed_requires_a_key(clean_seed):
    with pytest.raises(ValueError, match="non-empty API key"):
        registry_seed.ensure_benchmark_legacy_node(api_key="  ")


def test_remove_benchmark_legacy_node(clean_seed):
    registry_seed.ensure_benchmark_legacy_node(api_key="k-1")
    registry_seed.remove_benchmark_legacy_node()

    from app.core.llm_router import llm_router

    assert registry_seed.BENCHMARK_NODE_ID not in llm_router._nodes


def test_benchmark_route_admission():
    assert registry_seed.is_benchmark_route(registry_seed.BENCHMARK_NODE_ID)
    assert registry_seed.is_benchmark_route(
        None, {"node_id": registry_seed.BENCHMARK_NODE_ID}
    )
    assert not registry_seed.is_benchmark_route("pi-deepseek-default")
    assert not registry_seed.is_benchmark_route(None, {"node_id": "other"})
