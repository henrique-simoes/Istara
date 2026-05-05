"""Static tests for Istara's shared test harness contracts."""

from tests.llm_test_config import (
    GEMINI_OPENAI_BASE_URL,
    GEMINI_TEST_MODEL,
    LIVE_LLM_PROFILES,
    SECONDARY_OPENAI_BASE_URL,
    SECONDARY_TEST_MODEL,
    openai_compatible_endpoint,
)


def test_openai_compatible_endpoint_preserves_gemini_openai_base():
    assert (
        openai_compatible_endpoint(GEMINI_OPENAI_BASE_URL, "chat/completions")
        == "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    )


def test_openai_compatible_endpoint_adds_v1_for_lmstudio_base():
    assert (
        openai_compatible_endpoint(SECONDARY_OPENAI_BASE_URL, "chat/completions")
        == "http://10.0.10.142:1234/v1/chat/completions"
    )
    assert (
        openai_compatible_endpoint("http://localhost:1234/v1", "models")
        == "http://localhost:1234/v1/models"
    )


def test_live_llm_profiles_are_openai_compatible_and_secret_free():
    profile_names = {profile.name for profile in LIVE_LLM_PROFILES}
    assert profile_names == {
        "gemini-openai-compatible",
        "secondary-openai-compatible",
    }
    endpoints = {
        profile.name: profile.endpoint("chat/completions")
        for profile in LIVE_LLM_PROFILES
    }
    assert endpoints["gemini-openai-compatible"].endswith("/openai/chat/completions")
    assert endpoints["secondary-openai-compatible"].endswith("/v1/chat/completions")
    assert all("/api/tags" not in endpoint for endpoint in endpoints.values())
    assert all("/output_schema" not in endpoint for endpoint in endpoints.values())


def test_live_llm_models_match_current_test_contract():
    models = {profile.name: profile.model for profile in LIVE_LLM_PROFILES}
    assert models["gemini-openai-compatible"] == GEMINI_TEST_MODEL
    assert models["secondary-openai-compatible"] == SECONDARY_TEST_MODEL
    assert GEMINI_TEST_MODEL == "gemini-3.1-flash-lite-preview"
    assert SECONDARY_TEST_MODEL == "qwen3.6-35b-a3b@q5_k_xl"
