"""Shared live-LLM test profile.

The live LLM tests intentionally use one OpenAI-compatible Gemini endpoint so
their behavior is reproducible across machines. The API key must come from an
environment variable or the local macOS keychain; it is never stored in git.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from urllib.parse import urlparse

import pytest

GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
GEMINI_TEST_MODEL = "gemini-3.1-flash-lite-preview"
SECONDARY_OPENAI_BASE_URL = "http://10.0.10.142:1234"
SECONDARY_TEST_MODEL = "qwen3.6-35b-a3b@q5_k_xl"
KEYCHAIN_SERVICE = "istara-gemini-openai-compatible-tests"
SECONDARY_KEYCHAIN_SERVICE = "istara-secondary-openai-compatible-tests"
KEY_ENV_NAMES = ("ISTARA_LLM_TEST_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY")
SECONDARY_KEY_ENV_NAMES = (
    "ISTARA_SECONDARY_LLM_TEST_API_KEY",
    "ISTARA_LMSTUDIO_TEST_API_KEY",
)


@dataclass(frozen=True)
class LiveLLMProfile:
    """OpenAI-compatible profile used by live tests and harness scripts."""

    name: str
    provider_type: str
    base_url: str
    model: str
    key_env_names: tuple[str, ...]
    keychain_service: str
    required: bool = False

    def endpoint(self, suffix: str) -> str:
        """Return a provider-correct OpenAI-compatible endpoint URL."""
        return openai_compatible_endpoint(self.base_url, suffix)


def openai_compatible_endpoint(base_url: str, suffix: str) -> str:
    """Append OpenAI-compatible suffixes without creating Ollama-style paths."""
    clean_base = base_url.rstrip("/")
    clean_suffix = suffix.lstrip("/")
    parsed = urlparse(clean_base if "://" in clean_base else f"http://{clean_base}")
    base_path = parsed.path.rstrip("/")
    already_openai_compatible = (
        parsed.hostname == "generativelanguage.googleapis.com"
        or base_path.endswith("/openai")
        or base_path.endswith("/v1")
    )
    if already_openai_compatible:
        return f"{clean_base}/{clean_suffix}"
    return f"{clean_base}/v1/{clean_suffix}"


PRIMARY_LLM_PROFILE = LiveLLMProfile(
    name="gemini-openai-compatible",
    provider_type="gemini_openai",
    base_url=GEMINI_OPENAI_BASE_URL,
    model=GEMINI_TEST_MODEL,
    key_env_names=KEY_ENV_NAMES,
    keychain_service=KEYCHAIN_SERVICE,
    required=True,
)

SECONDARY_LLM_PROFILE = LiveLLMProfile(
    name="secondary-openai-compatible",
    provider_type="openai_compat",
    base_url=SECONDARY_OPENAI_BASE_URL,
    model=SECONDARY_TEST_MODEL,
    key_env_names=SECONDARY_KEY_ENV_NAMES,
    keychain_service=SECONDARY_KEYCHAIN_SERVICE,
)

LIVE_LLM_PROFILES = (PRIMARY_LLM_PROFILE, SECONDARY_LLM_PROFILE)


def _read_env_secret(env_name: str) -> str:
    """Read one secret-bearing environment variable without logging it."""
    return os.getenv(env_name, "").strip()


def _read_keychain_secret(service: str = KEYCHAIN_SERVICE) -> str:
    """Read a local live-test key from macOS Keychain when available."""
    if os.name != "posix" or not os.path.exists("/usr/bin/security"):
        return ""
    account = os.getenv("USER", "istara")
    try:
        result = subprocess.run(
            [
                "/usr/bin/security",
                "find-generic-password",
                "-a",
                account,
                "-s",
                service,
                "-w",
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
        )
    except Exception:
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def get_profile_api_key(profile: LiveLLMProfile) -> str:
    """Return a profile's configured API key without exposing it in code."""
    for env_name in profile.key_env_names:
        api_key = _read_env_secret(env_name)
        if api_key:
            return api_key
    return _read_keychain_secret(profile.keychain_service)


def get_live_llm_api_key() -> str:
    """Return the configured live-test API key without exposing it in code."""
    return get_profile_api_key(PRIMARY_LLM_PROFILE)


def get_secondary_live_llm_api_key() -> str:
    """Return the fallback live-test API key without exposing it in code."""
    return get_profile_api_key(SECONDARY_LLM_PROFILE)


def require_live_llm_api_key() -> str:
    """Return the API key or skip the live LLM test with an explicit reason."""
    api_key = get_live_llm_api_key()
    if not api_key:
        pytest.skip(
            "Live LLM tests require ISTARA_LLM_TEST_API_KEY, GEMINI_API_KEY, "
            f"or a macOS Keychain item named {KEYCHAIN_SERVICE}."
        )
    return api_key


def configure_gemini_settings(settings, api_key: str) -> None:
    """Point Istara's OpenAI-compatible settings at Gemini for live tests."""
    settings.llm_provider = "lmstudio"
    settings.lmstudio_host = GEMINI_OPENAI_BASE_URL
    settings.lmstudio_model = GEMINI_TEST_MODEL
    settings.lmstudio_api_key = api_key
    # Live tests need deterministic primary routing but must still allow the
    # secondary provider to take over after Gemini transient retries fail.
    settings.strict_auto_routing = False


def configure_gemini_compute_registry(*, clear_existing: bool = True):
    """Register Gemini plus an optional secondary OpenAI-compatible fallback."""
    from app.config import settings
    from app.core.compute_registry import ComputeNode, compute_registry

    api_key = require_live_llm_api_key()
    secondary_api_key = get_secondary_live_llm_api_key()
    configure_gemini_settings(settings, api_key)

    if clear_existing:
        for node in list(compute_registry._nodes.values()):
            if node._client and not node._client.is_closed:
                # Best-effort cleanup; tests should not fail on stale clients.
                pass
        compute_registry._nodes.clear()

    node = ComputeNode(
        node_id="gemini-openai-compatible-live-test",
        name="Gemini OpenAI-Compatible Live Test",
        host=PRIMARY_LLM_PROFILE.base_url.rstrip("/"),
        source="network",
        provider_type=PRIMARY_LLM_PROFILE.provider_type,
        api_key=api_key,
        priority=0,
        is_local=False,
        is_healthy=True,
        loaded_models=[PRIMARY_LLM_PROFILE.model],
        model_capabilities={
            PRIMARY_LLM_PROFILE.model: {
                "supports_tools": True,
                "supports_vision": False,
                "context_length": 32768,
            }
        },
    )
    compute_registry.register_node(node)
    nodes = [node]

    if secondary_api_key:
        fallback = ComputeNode(
            node_id="secondary-openai-compatible-live-test",
            name="Secondary OpenAI-Compatible Live Test",
            host=SECONDARY_LLM_PROFILE.base_url,
            source="network",
            provider_type=SECONDARY_LLM_PROFILE.provider_type,
            api_key=secondary_api_key,
            priority=10,
            is_local=False,
            is_healthy=True,
            loaded_models=[SECONDARY_LLM_PROFILE.model],
            model_capabilities={
                SECONDARY_LLM_PROFILE.model: {
                    "supports_tools": True,
                    "supports_vision": False,
                    "context_length": 32768,
                }
            },
        )
        compute_registry.register_node(fallback)
        nodes.append(fallback)

    return nodes
