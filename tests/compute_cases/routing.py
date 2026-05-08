from tests.compute_cases.common import *

def test_select_candidates_filters_saturated_nodes_and_prefers_score():
    registry = ComputeRegistry()
    saturated = ComputeNode(
        node_id="saturated",
        name="Saturated",
        host="http://localhost:1234",
        source="local",
        provider_type="lmstudio",
        is_healthy=True,
        active_requests=4,
        max_active_requests=4,
    )
    available = ComputeNode(
        node_id="available",
        name="Available",
        host="http://localhost:1235",
        source="local",
        provider_type="lmstudio",
        is_healthy=True,
        active_requests=1,
        max_active_requests=4,
        ram_available_gb=8,
    )
    registry.register_node(saturated)
    registry.register_node(available)

    candidates = registry._select_candidates()

    assert [node.node_id for node in candidates] == ["available"]


def test_openai_compatible_endpoint_paths_respect_provider_base_url():
    gemini = ComputeNode(
        node_id="gemini",
        name="Gemini",
        host="https://generativelanguage.googleapis.com/v1beta/openai",
        source="network",
        provider_type="gemini_openai",
    )
    lmstudio = ComputeNode(
        node_id="lmstudio",
        name="LM Studio",
        host="http://localhost:1234",
        source="local",
        provider_type="lmstudio",
    )
    explicit_v1 = ComputeNode(
        node_id="openai",
        name="OpenAI-compatible",
        host="https://api.example.com/v1",
        source="network",
        provider_type="openai_compat",
    )

    assert gemini._openai_endpoint("chat/completions") == "chat/completions"
    assert lmstudio._openai_endpoint("chat/completions") == "v1/chat/completions"
    assert explicit_v1._openai_endpoint("models") == "models"


def test_relay_provider_inference_preserves_openai_compatible_contracts():
    assert _infer_relay_provider_type("http://192.0.2.142:1234", None) == "lmstudio"
    assert _infer_relay_provider_type("http://192.0.2.142:1234", "ollama") == "lmstudio"
    assert _infer_relay_provider_type("http://example.test:9999/v1", "ollama") == ("openai_compat")
    assert _infer_relay_provider_type("http://192.0.2.142:11434", None) == "ollama"
    assert (
        _infer_relay_provider_type(
            "https://generativelanguage.googleapis.com/v1beta/openai/",
            "ollama",
        )
        == "gemini_openai"
    )


def test_register_node_skips_lower_priority_duplicate_provider_mismatch():
    registry = ComputeRegistry()
    lmstudio = ComputeNode(
        node_id="lmstudio",
        name="LM Studio",
        host="http://192.0.2.142:1234",
        source="network",
        provider_type="openai_compat",
        is_healthy=True,
        priority=1,
    )
    mistaken_ollama = ComputeNode(
        node_id="ollama-duplicate",
        name="Mistaken Ollama",
        host="http://192.0.2.142:1234/v1",
        source="network",
        provider_type="ollama",
        is_healthy=True,
        priority=5,
    )

    registry.register_node(lmstudio)
    registry.register_node(mistaken_ollama)

    assert list(registry._nodes) == ["lmstudio"]
    assert registry._nodes["lmstudio"].provider_type == "openai_compat"


def test_select_candidates_prefers_requested_model_before_score():
    registry = ComputeRegistry()
    fast_wrong_model = ComputeNode(
        node_id="fast-wrong",
        name="Fast Wrong",
        host="http://localhost:1234",
        source="local",
        provider_type="lmstudio",
        is_healthy=True,
        priority=0,
        ram_available_gb=10,
        loaded_models=["other-model"],
    )
    slower_requested_model = ComputeNode(
        node_id="slower-requested",
        name="Slower Requested",
        host="http://localhost:1235",
        source="local",
        provider_type="lmstudio",
        is_healthy=True,
        priority=25,
        loaded_models=["llama3:latest"],
    )
    registry.register_node(fast_wrong_model)
    registry.register_node(slower_requested_model)

    candidates = registry._select_candidates(model="llama3")

    assert [node.node_id for node in candidates] == ["slower-requested", "fast-wrong"]


def test_select_candidates_strict_model_filters_missing_models():
    registry = ComputeRegistry()
    wrong_model = ComputeNode(
        node_id="wrong",
        name="Wrong",
        host="http://localhost:1234",
        source="local",
        provider_type="lmstudio",
        is_healthy=True,
        loaded_models=["other-model"],
    )
    requested_model = ComputeNode(
        node_id="requested",
        name="Requested",
        host="http://localhost:1235",
        source="local",
        provider_type="lmstudio",
        is_healthy=True,
        loaded_models=["llama3"],
    )
    registry.register_node(wrong_model)
    registry.register_node(requested_model)

    candidates = registry._select_candidates(model="llama3", strict_model=True)

    assert [node.node_id for node in candidates] == ["requested"]


def test_resolve_model_prefers_explicit_capability_over_advertised_fallback():
    node = ComputeNode(
        node_id="gemini",
        name="Gemini",
        host="https://generativelanguage.googleapis.com/v1beta/openai",
        source="network",
        provider_type="gemini_openai",
        loaded_models=["models/gemini-2.5-flash"],
        model_capabilities={
            "gemini-3.1-flash-lite-preview": {
                "supports_tools": True,
                "context_length": 32768,
            }
        },
    )

    assert node._resolve_model("gemini-3.1-flash-lite-preview") == ("gemini-3.1-flash-lite-preview")


def test_configured_openai_primary_uses_pinned_model_when_models_list_is_broader(monkeypatch):
    monkeypatch.setattr(
        settings,
        "lmstudio_host",
        "https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    monkeypatch.setattr(settings, "lmstudio_model", "gemini-3.1-flash-lite-preview")
    node = ComputeNode(
        node_id="gemini",
        name="Gemini",
        host="https://generativelanguage.googleapis.com/v1beta/openai",
        source="local",
        provider_type="lmstudio",
        loaded_models=["models/gemini-2.5-flash", "models/gemini-2.5-pro"],
    )

    assert node._resolve_model(None) == "gemini-3.1-flash-lite-preview"
    assert node._resolve_model("gemini-3.1-flash-lite-preview") == "gemini-3.1-flash-lite-preview"


def test_network_openai_fallback_keeps_own_advertised_model(monkeypatch):
    monkeypatch.setattr(
        settings,
        "lmstudio_host",
        "https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    monkeypatch.setattr(settings, "lmstudio_model", "gemini-3.1-flash-lite-preview")
    node = ComputeNode(
        node_id="secondary",
        name="Secondary",
        host="http://192.0.2.142:1234",
        source="network",
        provider_type="openai_compat",
        loaded_models=["qwen3.6-35b-a3b@q5_k_xl"],
    )

    assert node._resolve_model(None) == "qwen3.6-35b-a3b@q5_k_xl"
