from app.core.network_discovery import _extract_models


def test_extract_models_requires_openai_model_ids():
    assert _extract_models({"data": [{"id": "llama-3.2"}]}, "lmstudio") == ["llama-3.2"]
    assert _extract_models({"data": []}, "lmstudio") == []
    assert _extract_models({"data": [{"name": "not-openai-shape"}]}, "lmstudio") == []
    assert _extract_models({"foo": "bar"}, "lmstudio") == []


def test_extract_models_requires_ollama_model_names():
    assert _extract_models({"models": [{"name": "qwen3:latest"}]}, "ollama") == ["qwen3:latest"]
    assert _extract_models({"models": []}, "ollama") == []
    assert _extract_models({"models": [{"id": "not-ollama-shape"}]}, "ollama") == []
    assert _extract_models({"data": [{"id": "wrong-provider-shape"}]}, "ollama") == []
