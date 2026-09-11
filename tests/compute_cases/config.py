from tests.compute_cases.common import *


def test_configured_local_lmstudio_node_preserves_api_key_and_model(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "lmstudio")
    monkeypatch.setattr(
        settings,
        "lmstudio_host",
        "https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    monkeypatch.setattr(settings, "lmstudio_model", "gemini-3.1-flash-lite-preview")
    monkeypatch.setattr(settings, "lmstudio_api_key", "test-key")

    node = _build_configured_local_llm_node()

    assert node._openai_endpoint("chat/completions") == "chat/completions"
    assert node.api_key == "test-key"
    assert node.loaded_models == ["gemini-3.1-flash-lite-preview"]


def test_configured_lmstudio_model_is_authoritative(monkeypatch):
    monkeypatch.setattr(settings, "lmstudio_model", "gemini-3.1-flash-lite-preview")
    assert configured_lmstudio_model_is_authoritative()
    assert not configured_lmstudio_model_is_authoritative("default")


@pytest.mark.asyncio
async def test_lmstudio_model_probe_uses_configured_openai_model(monkeypatch):
    monkeypatch.setattr(settings, "lmstudio_model", "gemini-3.1-flash-lite-preview")

    class FakeClient:
        def __init__(self):
            self.payload = None

        async def post(self, path, *, json, timeout):
            self.payload = json
            return httpx.Response(
                200,
                request=httpx.Request("POST", f"http://test{path}"),
                json={"model": json["model"], "choices": []},
            )

    fake = FakeClient()
    client = LMStudioClient("https://generativelanguage.googleapis.com/v1beta/openai/")

    async def get_client():
        return fake

    monkeypatch.setattr(client, "_get_client", get_client)

    assert (
        await client.detect_loaded_model(force=True) == "gemini-3.1-flash-lite-preview"
    )
    assert fake.payload["model"] == "gemini-3.1-flash-lite-preview"


@pytest.mark.asyncio
async def test_settings_models_preserves_configured_lmstudio_model(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "lmstudio")
    monkeypatch.setattr(settings, "lmstudio_model", "gemini-3.1-flash-lite-preview")

    class AdminRequest:
        class State:
            user = {"id": "admin", "username": "admin", "role": "admin"}

        state = State()

    class MismatchedProbeClient(LMStudioClient):
        def __init__(self):
            super().__init__("https://generativelanguage.googleapis.com/v1beta/openai/")
            self.detect_calls = 0

        async def health(self):
            return True

        async def list_models(self):
            return [{"name": "models/gemini-2.5-flash"}]

        async def detect_loaded_model(self, force: bool = False):
            self.detect_calls += 1
            return "models/gemini-2.5-flash"

    fake_client = MismatchedProbeClient()

    async def no_registry_models():
        return []

    def fail_persist(*_args, **_kwargs):
        raise AssertionError("Configured LM Studio model should not be auto-persisted")

    monkeypatch.setattr(settings_routes, "ollama", fake_client)
    monkeypatch.setattr(compute_registry, "list_models", no_registry_models)
    monkeypatch.setattr(settings_routes, "_persist_env", fail_persist)

    response = await settings_routes.get_models(AdminRequest())

    assert response["active_model"] == "gemini-3.1-flash-lite-preview"
    assert settings.lmstudio_model == "gemini-3.1-flash-lite-preview"
    assert fake_client.detect_calls == 0
