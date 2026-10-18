"""Decider API keys come from macOS Keychain or a named environment variable, never from config.

The key is returned to the caller that builds the request and is never logged, persisted or put in
an outcome. A missing key is reported by name only.
"""

from __future__ import annotations

import os
import subprocess
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
