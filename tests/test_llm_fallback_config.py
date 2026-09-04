"""Tests for configured authenticated LLM fallback nodes."""

from app.config import settings
from app import config as app_config
from app.main import _build_configured_fallback_llm_node


def test_no_configured_fallback_returns_none():
    original_host = settings.llm_fallback_host
    try:
        settings.llm_fallback_host = ""
        assert _build_configured_fallback_llm_node() is None
    finally:
        settings.llm_fallback_host = original_host


def test_configured_openai_compatible_fallback_preserves_auth_and_model():
    original = (
        settings.llm_fallback_host,
        settings.llm_fallback_provider,
        settings.llm_fallback_model,
        settings.llm_fallback_api_key,
        settings.llm_fallback_api_key_keychain_service,
    )
    try:
        settings.llm_fallback_host = "http://192.0.2.142:1234"
        settings.llm_fallback_provider = "openai_compat"
        settings.llm_fallback_model = "qwen3.6-35b-a3b@q5_k_xl"
        settings.llm_fallback_api_key = "test-key"
        settings.llm_fallback_api_key_keychain_service = ""

        node = _build_configured_fallback_llm_node()

        assert node is not None
        assert node.node_id == "configured-llm-fallback"
        assert node.provider_type == "openai_compat"
        assert node.api_key == "test-key"
        assert node.loaded_models == ["qwen3.6-35b-a3b@q5_k_xl"]
        assert node._openai_endpoint("chat/completions") == "v1/chat/completions"
    finally:
        (
            settings.llm_fallback_host,
            settings.llm_fallback_provider,
            settings.llm_fallback_model,
            settings.llm_fallback_api_key,
            settings.llm_fallback_api_key_keychain_service,
        ) = original


def test_configured_fallback_can_read_key_from_keychain(monkeypatch):
    original = (
        settings.llm_fallback_host,
        settings.llm_fallback_provider,
        settings.llm_fallback_model,
        settings.llm_fallback_api_key,
        settings.llm_fallback_api_key_keychain_service,
    )
    try:
        settings.llm_fallback_host = "http://192.0.2.142:1234"
        settings.llm_fallback_provider = "openai_compat"
        settings.llm_fallback_model = "qwen3.6-35b-a3b@q5_k_xl"
        settings.llm_fallback_api_key = ""
        settings.llm_fallback_api_key_keychain_service = "istara-secondary-test"
        monkeypatch.setattr(
            app_config,
            "_read_macos_keychain_secret",
            lambda service: (
                "keychain-test-key" if service == "istara-secondary-test" else ""
            ),
        )

        node = _build_configured_fallback_llm_node()

        assert node is not None
        assert node.api_key == "keychain-test-key"
        assert node.provider_type == "openai_compat"
        assert node._openai_endpoint("models") == "v1/models"
    finally:
        (
            settings.llm_fallback_host,
            settings.llm_fallback_provider,
            settings.llm_fallback_model,
            settings.llm_fallback_api_key,
            settings.llm_fallback_api_key_keychain_service,
        ) = original


def test_backend_env_files_are_absolute_and_include_local_override():
    env_files = app_config.Settings.model_config["env_file"]

    assert str(app_config._BACKEND_DIR / ".env") in env_files
    assert str(app_config._BACKEND_DIR / ".env.local") in env_files
    assert all(path.startswith(str(app_config._BACKEND_DIR)) for path in env_files)
