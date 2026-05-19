from tests.compute_cases.common import *


def test_compute_stats_treat_stale_no_model_healthy_flag_as_reachable_not_ready():
    registry = ComputeRegistry()
    registry.register_node(
        ComputeNode(
            node_id="lmstudio",
            name="Local LM Studio",
            host="http://localhost:1234",
            source="local",
            provider_type="lmstudio",
            is_healthy=True,
            health_state="no_model_loaded",
            model_capabilities={
                "qwen3": {
                    "is_loaded": False,
                    "loadable": True,
                    "supports_tools": True,
                }
            },
        )
    )

    stats = registry.get_stats()
    node = stats["nodes"][0]

    assert stats["alive_nodes"] == 0
    assert stats["ready_nodes"] == 0
    assert stats["reachable_nodes"] == 1
    assert node["alive"] is False
    assert node["is_ready"] is False
    assert node["is_reachable"] is True
    assert node["readiness_state"] == "no_model_loaded"


def test_configured_local_endpoint_collapses_with_current_lan_alias(monkeypatch):
    import app.core.compute_registry_helpers as compute_registry_helpers

    monkeypatch.setattr(
        compute_registry_helpers,
        "_local_machine_aliases",
        lambda: {"localhost", "127.0.0.1", "192.0.2.215"},
    )
    registry = ComputeRegistry()
    registry.register_node(
        ComputeNode(
            node_id="local-configured",
            name="Local LM Studio",
            host="http://192.0.2.142:1234",
            source="local",
            provider_type="lmstudio",
            is_healthy=False,
            health_state="no_model_loaded",
            ram_total_gb=36.0,
            ram_available_gb=23.2,
            cpu_cores=16,
        )
    )
    registry.register_node(
        ComputeNode(
            node_id="network-current",
            name="Network LM Studio",
            host="http://192.0.2.215:1234",
            source="network",
            provider_type="lmstudio",
            is_healthy=False,
            health_state="no_model_loaded",
            ram_total_gb=36.0,
            ram_available_gb=22.8,
            cpu_cores=16,
            model_capabilities={"qwen3": {"supports_tools": True, "is_loaded": False}},
        )
    )

    stats = registry.get_stats()

    assert list(registry._nodes) == ["local-configured"]
    assert stats["total_nodes"] == 1
    assert stats["hardware_node_count"] == 1
    assert stats["total_ram_gb"] == 36.0
    assert stats["available_ram_gb"] == 23.2
    assert stats["reachable_nodes"] == 1
    assert stats["ready_nodes"] == 0
    assert stats["nodes"][0]["node_id"] == "local-configured"
    assert stats["nodes"][0]["readiness_state"] == "no_model_loaded"
    assert "qwen3" in stats["available_models"]
