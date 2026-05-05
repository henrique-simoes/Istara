"""Shared live-LLM test profile.

The live LLM tests intentionally use one OpenAI-compatible Gemini endpoint so
their behavior is reproducible across machines. The API key must come from an
environment variable or the local macOS keychain; it is never stored in git.
"""

from __future__ import annotations

import os
import subprocess

import pytest

GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
GEMINI_TEST_MODEL = "gemini-3.1-flash-lite-preview"
KEYCHAIN_SERVICE = "istara-gemini-openai-compatible-tests"
KEY_ENV_NAMES = ("ISTARA_LLM_TEST_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY")


def _read_env_secret(env_name: str) -> str:
    """Read one secret-bearing environment variable without logging it."""
    return os.getenv(env_name, "").strip()


def _read_keychain_secret() -> str:
    """Read the local Gemini test key from macOS Keychain when available."""
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
                KEYCHAIN_SERVICE,
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


def get_live_llm_api_key() -> str:
    """Return the configured live-test API key without exposing it in code."""
    for env_name in KEY_ENV_NAMES:
        api_key = _read_env_secret(env_name)
        if api_key:
            return api_key
    return _read_keychain_secret()


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
    settings.strict_auto_routing = True


def configure_gemini_compute_registry(*, clear_existing: bool = True):
    """Register the single Gemini live-test node and return it."""
    from app.config import settings
    from app.core.compute_registry import ComputeNode, compute_registry

    api_key = require_live_llm_api_key()
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
        host=GEMINI_OPENAI_BASE_URL.rstrip("/"),
        source="network",
        provider_type="gemini_openai",
        api_key=api_key,
        priority=0,
        is_local=False,
        is_healthy=True,
        loaded_models=[GEMINI_TEST_MODEL],
        model_capabilities={
            GEMINI_TEST_MODEL: {
                "supports_tools": True,
                "supports_vision": False,
                "context_length": 32768,
            }
        },
    )
    compute_registry.register_node(node)
    return node
