"""Shared live-LLM test profile.

Live LLM tests use one OpenAI-compatible endpoint configured only through a
gitignored environment file or the local environment. The checked-in harness
keeps the model contract stable, but never stores the private base URL or API
token in source control.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pytest

ROOT = Path(__file__).resolve().parents[1]
LIVE_LLM_ENV_FILES = (
    ROOT / ".env",
    ROOT / ".env.local",
    ROOT / "backend" / ".env",
    ROOT / "backend" / ".env.local",
)
LIVE_LLM_ENV_KEYS = (
    "ISTARA_LIVE_LLM_BASE_URL",
    "ISTARA_PRIMARY_LLM_TEST_BASE_URL",
    "LMSTUDIO_HOST",
    "ISTARA_LIVE_LLM_API_KEY",
    "ISTARA_LLM_TEST_API_KEY",
    "ISTARA_PRIMARY_LLM_TEST_API_KEY",
    "LMSTUDIO_API_KEY",
    "ISTARA_LIVE_LLM_KEYCHAIN_SERVICE",
)
_LOADED_GITIGNORED_LIVE_ENV_FILES = 0


def _parse_gitignored_env_assignment(raw_line: str) -> tuple[str, str] | None:
    line = raw_line.strip()
    if not line or line.startswith("#") or "=" not in line:
        return None
    if line.startswith("export "):
        line = line[len("export "):].strip()
    key, value = line.split("=", 1)
    key = key.strip()
    if key not in LIVE_LLM_ENV_KEYS:
        return None
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return key, value


def load_gitignored_live_env(
    *,
    override: bool = False,
    env_files: tuple[Path, ...] | list[Path] | None = None,
) -> int:
    """Load live-LLM harness keys from gitignored env files without logging values."""
    global _LOADED_GITIGNORED_LIVE_ENV_FILES

    loaded_files = 0
    for path in env_files or LIVE_LLM_ENV_FILES:
        if not path.exists() or not path.is_file():
            continue
        loaded_files += 1
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            parsed = _parse_gitignored_env_assignment(raw_line)
            if parsed is None:
                continue
            key, value = parsed
            if override or key not in os.environ:
                os.environ[key] = value
    _LOADED_GITIGNORED_LIVE_ENV_FILES = loaded_files
    return loaded_files


def loaded_gitignored_live_env_file_count() -> int:
    return _LOADED_GITIGNORED_LIVE_ENV_FILES


load_gitignored_live_env()

PRIMARY_OPENAI_BASE_URL = os.getenv(
    "ISTARA_LIVE_LLM_BASE_URL",
    os.getenv("ISTARA_PRIMARY_LLM_TEST_BASE_URL", os.getenv("LMSTUDIO_HOST", "")),
).strip()
PRIMARY_TEST_MODEL = os.getenv("ISTARA_LIVE_LLM_MODEL", "google/gemma-4-e4b")
KEYCHAIN_SERVICE = os.getenv(
    "ISTARA_LIVE_LLM_KEYCHAIN_SERVICE",
    "istara-live-openai-compatible-tests",
)
KEY_ENV_NAMES = (
    "ISTARA_LIVE_LLM_API_KEY",
    "ISTARA_LLM_TEST_API_KEY",
    "ISTARA_PRIMARY_LLM_TEST_API_KEY",
    "LMSTUDIO_API_KEY",
)
PRIMARY_LIVE_LLM_MAX_ATTEMPTS = 5
LIVE_LLM_TEST_TEMPERATURE = 0
LIVE_LLM_TEST_MAX_TOKENS = 8

# Backward-compatible aliases for older imports. They now point at the private
# main OpenAI-compatible profile, not a checked-in public endpoint.
GEMINI_OPENAI_BASE_URL = PRIMARY_OPENAI_BASE_URL
GEMINI_TEST_MODEL = PRIMARY_TEST_MODEL
SECONDARY_OPENAI_BASE_URL = ""
SECONDARY_TEST_MODEL = ""
SECONDARY_LIVE_LLM_MAX_ATTEMPTS = 0


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


@dataclass(frozen=True)
class LiveLLMCompletionResult:
    """Result metadata for the single-profile live-test contract."""

    profile_name: str
    model: str
    endpoint: str
    response: Any
    primary_attempts: int
    fallback_used: bool
    errors: tuple[str, ...]


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
    name="main-openai-compatible",
    provider_type="openai_compat",
    base_url=PRIMARY_OPENAI_BASE_URL,
    model=PRIMARY_TEST_MODEL,
    key_env_names=KEY_ENV_NAMES,
    keychain_service=KEYCHAIN_SERVICE,
    required=True,
)

LIVE_LLM_PROFILES = (PRIMARY_LLM_PROFILE,)


def current_primary_llm_profile() -> LiveLLMProfile:
    """Return the current env-backed primary live-test profile."""
    base_url = os.getenv(
        "ISTARA_LIVE_LLM_BASE_URL",
        os.getenv(
            "ISTARA_PRIMARY_LLM_TEST_BASE_URL",
            os.getenv("LMSTUDIO_HOST", PRIMARY_OPENAI_BASE_URL),
        ),
    ).strip()
    return LiveLLMProfile(
        name=PRIMARY_LLM_PROFILE.name,
        provider_type=PRIMARY_LLM_PROFILE.provider_type,
        base_url=base_url,
        model=PRIMARY_TEST_MODEL,
        key_env_names=PRIMARY_LLM_PROFILE.key_env_names,
        keychain_service=PRIMARY_LLM_PROFILE.keychain_service,
        required=True,
    )


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
    return get_profile_api_key(current_primary_llm_profile())


def get_secondary_live_llm_api_key() -> str:
    """Compatibility shim: the live harness no longer uses a secondary server."""
    return ""


def require_live_llm_profile() -> tuple[LiveLLMProfile, str]:
    """Return the configured profile or skip with an explicit reason."""
    profile = current_primary_llm_profile()
    if not profile.base_url:
        pytest.skip(
            "Live LLM tests require ISTARA_LIVE_LLM_BASE_URL, "
            "ISTARA_PRIMARY_LLM_TEST_BASE_URL, or LMSTUDIO_HOST in a gitignored env file."
        )
    api_key = get_live_llm_api_key()
    if not api_key:
        pytest.skip(
            "Live LLM tests require ISTARA_LIVE_LLM_API_KEY, ISTARA_LLM_TEST_API_KEY, "
            f"or a macOS Keychain item named {KEYCHAIN_SERVICE}."
        )
    return profile, api_key


def require_live_llm_api_key() -> str:
    """Return the API key or skip the live LLM test with an explicit reason."""
    _, api_key = require_live_llm_profile()
    return api_key


def configure_live_llm_settings(settings, api_key: str) -> None:
    """Point Istara's OpenAI-compatible settings at the private live test server."""
    profile = current_primary_llm_profile()
    settings.llm_provider = "lmstudio"
    settings.lmstudio_host = profile.base_url
    settings.lmstudio_model = profile.model
    settings.lmstudio_api_key = api_key
    settings.strict_auto_routing = True


def configure_gemini_settings(settings, api_key: str) -> None:
    """Backward-compatible alias for the single-profile live LLM settings."""
    configure_live_llm_settings(settings, api_key)


async def post_live_llm_chat_completion(
    client: Any,
    *,
    messages: list[dict] | None = None,
    temperature: float = LIVE_LLM_TEST_TEMPERATURE,
    max_tokens: int = LIVE_LLM_TEST_MAX_TOKENS,
    primary_attempts: int = PRIMARY_LIVE_LLM_MAX_ATTEMPTS,
    secondary_attempts: int = SECONDARY_LIVE_LLM_MAX_ATTEMPTS,
) -> LiveLLMCompletionResult:
    """Call the configured live LLM profile without probing fallback servers."""
    if primary_attempts != PRIMARY_LIVE_LLM_MAX_ATTEMPTS:
        raise ValueError("Live tests must use the shared main-server retry budget.")
    if secondary_attempts != SECONDARY_LIVE_LLM_MAX_ATTEMPTS:
        raise ValueError("Live tests must not configure secondary LLM retries.")

    profile, api_key = require_live_llm_profile()
    payload_messages = messages or [{"role": "user", "content": "Reply with ok."}]
    errors: list[str] = []

    for attempt in range(1, primary_attempts + 1):
        try:
            response = await client.post(
                profile.endpoint("chat/completions"),
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": profile.model,
                    "messages": payload_messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            if getattr(response, "status_code", 500) < 400:
                return LiveLLMCompletionResult(
                    profile_name=profile.name,
                    model=profile.model,
                    endpoint=profile.endpoint("chat/completions"),
                    response=response,
                    primary_attempts=attempt,
                    fallback_used=False,
                    errors=tuple(errors),
                )
            errors.append(f"{profile.name} attempt {attempt}: HTTP {response.status_code}")
        except Exception as exc:  # pragma: no cover - exercised through fake clients
            errors.append(f"{profile.name} attempt {attempt}: {type(exc).__name__}: {exc}")

    raise RuntimeError("Live LLM test provider failed: " + " | ".join(errors[-5:]))


def configure_live_compute_registry(*, clear_existing: bool = True):
    """Register exactly the private main OpenAI-compatible live-test node."""
    from app.core.compute_registry import ComputeNode, compute_registry, infer_provider_type

    profile, api_key = require_live_llm_profile()
    from app.config import settings

    configure_live_llm_settings(settings, api_key)

    if clear_existing:
        compute_registry._nodes.clear()

    provider_type = infer_provider_type(None, profile.base_url)
    registry_host = profile.base_url.rstrip("/")
    if provider_type == "lmstudio" and registry_host.endswith("/v1"):
        registry_host = registry_host.removesuffix("/v1")

    node = ComputeNode(
        node_id="main-openai-compatible-live-test",
        name="Main OpenAI-Compatible Live Test",
        host=registry_host,
        source="network",
        provider_type=provider_type,
        api_key=api_key,
        priority=0,
        is_local=False,
        is_healthy=True,
        loaded_models=[profile.model],
        model_capabilities={
            profile.model: {
                "supports_tools": True,
                "supports_vision": False,
                "context_length": 32768,
            }
        },
    )
    compute_registry.register_node(node)
    return [node]


def configure_gemini_compute_registry(*, clear_existing: bool = True):
    """Backward-compatible alias for the single-profile compute registry setup."""
    return configure_live_compute_registry(clear_existing=clear_existing)
