"""Static tests for Istara's shared test harness contracts."""

import os
from pathlib import Path

import pytest

from tests.llm_test_config import (
    LIVE_LLM_PROFILES,
    PRIMARY_LIVE_LLM_MAX_ATTEMPTS,
    PRIMARY_TEST_MODEL,
    configure_live_compute_registry,
    current_primary_llm_profile,
    load_gitignored_live_env,
    openai_compatible_endpoint,
    post_live_llm_chat_completion,
)

ROOT = Path(__file__).resolve().parent.parent


def test_openai_compatible_endpoint_preserves_existing_openai_base():
    assert (
        openai_compatible_endpoint("https://example.test/v1", "chat/completions")
        == "https://example.test/v1/chat/completions"
    )


def test_openai_compatible_endpoint_adds_v1_for_lmstudio_base():
    assert (
        openai_compatible_endpoint("http://192.0.2.142:1234", "chat/completions")
        == "http://192.0.2.142:1234/v1/chat/completions"
    )
    assert (
        openai_compatible_endpoint("http://localhost:1234/v1", "models")
        == "http://localhost:1234/v1/models"
    )


def test_live_llm_profiles_are_openai_compatible_and_secret_free():
    profile_names = {profile.name for profile in LIVE_LLM_PROFILES}
    assert profile_names == {"main-openai-compatible"}
    endpoints = {
        profile.name: profile.endpoint("chat/completions")
        for profile in LIVE_LLM_PROFILES
    }
    assert endpoints["main-openai-compatible"].endswith("/v1/chat/completions")
    assert all("/api/tags" not in endpoint for endpoint in endpoints.values())
    assert all("/output_schema" not in endpoint for endpoint in endpoints.values())


def test_live_llm_models_match_current_test_contract():
    models = {profile.name: profile.model for profile in LIVE_LLM_PROFILES}
    assert models["main-openai-compatible"] == PRIMARY_TEST_MODEL
    assert PRIMARY_TEST_MODEL == "google/gemma-4-e4b"
    config = (ROOT / "tests/llm_test_config.py").read_text(encoding="utf-8")
    assert "10.0.10." not in config


class _FakeLiveLLMClient:
    def __init__(self):
        self.calls: list[str] = []
        self.payloads: list[dict] = []

    async def post(self, url: str, headers: dict, json: dict):
        self.calls.append(url)
        self.payloads.append(json)
        return type("Response", (), {"status_code": 200})()


async def test_live_llm_helper_uses_only_configured_main_server(monkeypatch):
    monkeypatch.setenv("ISTARA_LIVE_LLM_BASE_URL", "http://192.0.2.142:1234")
    monkeypatch.setenv("ISTARA_LIVE_LLM_API_KEY", "primary-test-key")
    client = _FakeLiveLLMClient()

    result = await post_live_llm_chat_completion(client)

    assert result.fallback_used is False
    assert result.primary_attempts == 1
    assert client.calls == ["http://192.0.2.142:1234/v1/chat/completions"]
    assert client.payloads == [
        {
            "model": "google/gemma-4-e4b",
            "messages": [{"role": "user", "content": "Reply with ok."}],
            "temperature": 0,
            "max_tokens": 8,
        }
    ]


def test_live_llm_profile_can_follow_istara_lmstudio_host(monkeypatch):
    monkeypatch.delenv("ISTARA_LIVE_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("ISTARA_PRIMARY_LLM_TEST_BASE_URL", raising=False)
    monkeypatch.setenv("LMSTUDIO_HOST", "http://192.0.2.142:1234")

    profile = current_primary_llm_profile()

    assert profile.base_url == "http://192.0.2.142:1234"
    assert profile.model == "google/gemma-4-e4b"


def test_live_compute_registry_uses_lmstudio_load_contract_for_lmstudio_port(monkeypatch):
    monkeypatch.setenv("ISTARA_LIVE_LLM_BASE_URL", "http://192.0.2.142:1234/v1")
    monkeypatch.setenv("ISTARA_LIVE_LLM_API_KEY", "primary-test-key")

    from app.core.compute_registry import compute_registry
    from app.config import settings

    original_nodes = dict(compute_registry._nodes)
    settings_snapshot = {
        "llm_provider": settings.llm_provider,
        "lmstudio_host": settings.lmstudio_host,
        "lmstudio_model": settings.lmstudio_model,
        "lmstudio_api_key": settings.lmstudio_api_key,
        "strict_auto_routing": settings.strict_auto_routing,
    }
    try:
        nodes = configure_live_compute_registry(clear_existing=True)

        assert len(nodes) == 1
        assert nodes[0].provider_type == "lmstudio"
        assert nodes[0].host == "http://192.0.2.142:1234"
        assert nodes[0].loaded_models == ["google/gemma-4-e4b"]
    finally:
        compute_registry._nodes.clear()
        compute_registry._nodes.update(original_nodes)
        for key, value in settings_snapshot.items():
            setattr(settings, key, value)


def test_gitignored_live_env_loader_reads_only_live_llm_keys(tmp_path, monkeypatch):
    env_file = tmp_path / ".env.local"
    env_file.write_text(
        "\n".join(
            [
                "ISTARA_LIVE_LLM_BASE_URL=http://192.0.2.142:1234",
                "ISTARA_LIVE_LLM_API_KEY='private-test-key'",
                "ADMIN_PASSWORD=must-not-load-from-live-loader",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("ISTARA_LIVE_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("ISTARA_LIVE_LLM_API_KEY", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)

    loaded_files = load_gitignored_live_env(env_files=[env_file])

    assert loaded_files == 1
    assert os.getenv("ISTARA_LIVE_LLM_BASE_URL") == "http://192.0.2.142:1234"
    assert os.getenv("ISTARA_LIVE_LLM_API_KEY") == "private-test-key"
    assert os.getenv("ADMIN_PASSWORD") is None


def test_long_horizon_benchmark_requires_private_admin_password(tmp_path, monkeypatch):
    from tests.benchmarks import long_horizon_runner

    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    monkeypatch.setattr(long_horizon_runner, "ADMIN_PASSWORD_ENV_FILES", (tmp_path / "missing.env",))

    with pytest.raises(RuntimeError, match="ADMIN_PASSWORD"):
        long_horizon_runner.load_admin_password()

    source = (ROOT / "tests/benchmarks/long_horizon_runner.py").read_text(encoding="utf-8")
    assert 'admin_pass = "' not in source


def test_scenario_20_supports_seeded_random_skill_subset():
    scenario = (ROOT / "tests/simulation/scenarios/20-all-skills-comprehensive.mjs").read_text(
        encoding="utf-8"
    )

    assert "ISTARA_SCENARIO20_SKILL_LIMIT" in scenario
    assert "ISTARA_SCENARIO20_SKILL_SEED" in scenario
    assert "Scenario 20 skill selection" in scenario
    assert "seededRandom" in scenario


def test_simulation_runner_uses_backend_chat_readiness_status():
    runner = (ROOT / "tests/simulation/run.mjs").read_text(encoding="utf-8")

    assert "/api/settings/status" in runner
    assert "llm_readiness" in runner
    assert "llmReadiness" in runner
    assert 'settingsStatus?.services?.llm === "connected"' in runner


def test_simulation_runner_retries_transient_auth_failures():
    runner = (ROOT / "tests/simulation/run.mjs").read_text(encoding="utf-8")

    assert "ISTARA_AUTH_MAX_ATTEMPTS" in runner
    assert "[429, 500, 502, 503, 504]" in runner
    assert "Auth transient status" in runner
    assert "../../backend/.env.local" in runner


def test_standalone_live_llm_script_treats_missing_key_as_skip():
    script = (ROOT / "scripts/test_llm_integration.py").read_text(encoding="utf-8")

    assert "pytest.skip.Exception" in script
    assert "Live LLM connectivity skipped" in script


def test_simulation_evaluators_avoid_networkidle_waits():
    evaluator_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "tests/simulation/evaluators").glob("*.mjs"))
    )

    assert "networkidle" not in evaluator_text
    assert "ctx.frontendUrl" in evaluator_text
    assert ".click();" not in evaluator_text
    assert ".click().catch" not in evaluator_text
    assert "click({ timeout:" in evaluator_text
    assert "DomContentLoaded - cwvMap.NavigationStart" in evaluator_text
