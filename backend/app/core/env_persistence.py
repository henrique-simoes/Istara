"""Helpers for persisting runtime setting changes."""

import os
from pathlib import Path


def _env_file_path() -> Path:
    """Configurable .env target (ISTARA_ENV_FILE) for read-only containers.

    Deployed stacks run with a read-only rootfs; runtime-persisted settings
    (pi endpoints, OAuth credential blobs) must land on a mounted writable
    volume. Local checkouts keep the historical `.env` behavior.
    """
    configured = os.environ.get("ISTARA_ENV_FILE", "").strip()
    return Path(configured) if configured else Path(".env")


def persist_env_value(key: str, value: str) -> None:
    """Update the env file so the setting survives restarts."""
    env_path = _env_file_path()
    if not env_path.exists():
        env_path.write_text(f"{key}={value}\n")
        return

    lines = env_path.read_text().splitlines(keepends=True)
    found = False
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f"{key}=") or stripped.startswith(f"{key} ="):
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)
    if not found:
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines[-1] += "\n"
        new_lines.append(f"{key}={value}\n")
    env_path.write_text("".join(new_lines))
