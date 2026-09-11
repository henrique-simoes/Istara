from app.core.network_discovery import _extract_models, _get_local_ips


def test_extract_models_requires_openai_model_ids():
    assert _extract_models({"data": [{"id": "llama-3.2"}]}, "lmstudio") == ["llama-3.2"]
    assert _extract_models({"data": []}, "lmstudio") == []
    assert _extract_models({"data": [{"name": "not-openai-shape"}]}, "lmstudio") == []
    assert _extract_models({"foo": "bar"}, "lmstudio") == []


def test_extract_models_requires_ollama_model_names():
    assert _extract_models({"models": [{"name": "qwen3:latest"}]}, "ollama") == [
        "qwen3:latest"
    ]
    assert _extract_models({"models": []}, "ollama") == []
    assert _extract_models({"models": [{"id": "not-ollama-shape"}]}, "ollama") == []
    assert _extract_models({"data": [{"id": "wrong-provider-shape"}]}, "ollama") == []


def test_local_ip_exclusion_uses_interface_aliases(monkeypatch):
    import app.core.compute_registry_helpers as compute_registry_helpers

    monkeypatch.setattr(
        compute_registry_helpers,
        "_local_machine_aliases",
        lambda: {"localhost", "127.0.0.1", "192.0.2.142", "192.0.2.215"},
    )

    local_ips = _get_local_ips()

    assert "192.0.2.142" in local_ips
    assert "192.0.2.215" in local_ips
