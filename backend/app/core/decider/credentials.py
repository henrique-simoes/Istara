"""Decider API keys come from macOS Keychain or a named environment variable, never from config.

The key is returned to the caller that builds the request and is never logged, persisted or put in
an outcome. A missing key is reported by name only.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

_SECURITY_TOOL = "/usr/bin/security"


def _keychain_secret(service: str, account: str) -> str:
    if not service or not Path(_SECURITY_TOOL).exists():
        return ""
    command = [_SECURITY_TOOL, "find-generic-password"]
    if account:
        command.extend(["-a", account])
    command.extend(["-s", service, "-w"])
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=3, check=False)
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def resolve_api_key(
    *, keychain_service: str = "", keychain_account: str = "", env_var: str = ""
) -> str:
    """The configured key, or "" when none is available (a local server may need none).

    An environment variable named in config takes precedence over Keychain, so containers, which
    have no Keychain, can supply the key.
    """
    if env_var:
        value = os.environ.get(env_var, "").strip()
        if value:
            return value
    return _keychain_secret(keychain_service, keychain_account)


KEYCHAIN_SERVICE = "istara-decider"


def secret_env_name(endpoint_id: str) -> str:
    """The environment variable that supplies an endpoint's key where there is no Keychain."""
    slug = re.sub(r"[^A-Za-z0-9]+", "_", endpoint_id).strip("_").upper()
    return f"ISTARA_DECIDER_SECRET_{slug}"


def custody_fields(endpoint_id: str) -> dict[str, str]:
    """Where a key entered in Settings lives: Keychain on macOS, the named env var elsewhere."""
    return {
        "keychain_service": KEYCHAIN_SERVICE,
        "keychain_account": endpoint_id,
        "api_key_env": secret_env_name(endpoint_id),
    }


def store_api_key(endpoint_id: str, api_key: str) -> None:
    """Keep a key entered in Settings in macOS Keychain, or in the runtime env file elsewhere.

    Mirrors Pi endpoint custody (``pi_runtime.endpoint_policy``). Raises ``RuntimeError`` when the
    key cannot be stored; the key itself never appears in a log or an error.
    """
    if sys.platform == "darwin":
        from app.config import _write_macos_keychain_secret

        if not _write_macos_keychain_secret(KEYCHAIN_SERVICE, endpoint_id, api_key):
            raise RuntimeError("keychain_write_failed")
        return
    from app.core.env_persistence import persist_env_value

    name = secret_env_name(endpoint_id)
    persist_env_value(name, api_key)
    os.environ[name] = api_key


def delete_api_key(endpoint_id: str) -> None:
    """Best-effort removal of a key stored by :func:`store_api_key`."""
    os.environ.pop(secret_env_name(endpoint_id), None)
    if sys.platform != "darwin" or not Path(_SECURITY_TOOL).exists():
        return
    command = [
        _SECURITY_TOOL,
        "delete-generic-password",
        "-a",
        endpoint_id,
        "-s",
        KEYCHAIN_SERVICE,
    ]
    try:
        subprocess.run(command, capture_output=True, text=True, timeout=3, check=False)
    except (OSError, subprocess.SubprocessError):
        return
