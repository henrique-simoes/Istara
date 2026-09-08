"""Helpers for persisting runtime setting changes."""

import os
from pathlib import Path

from app.core.env_secrets import SECRET_ENV_DENYLIST


def _coerce_for_settings(attr: str, value: str):
    """Coerce a persisted string to the Settings field type when safe.

    Without this, ``setattr(settings, attr, "12")`` stores a str into an
    int field (pydantic does not validate plain setattr), which later
    crashes numeric comparisons (e.g. backup retention enforcement).
    Unknown fields or unparseable values pass through unchanged.
    """
    try:
        from app.config import Settings

        annotation = str(Settings.model_fields.get(attr, {}).annotation or "")
    except Exception:
        return value
    try:
        if annotation == "<class 'int'>":
            return int(str(value).strip())
        if annotation == "<class 'float'>":
            return float(str(value).strip())
        if annotation == "<class 'bool'>":
            lowered = str(value).strip().lower()
            if lowered in ("1", "true", "yes", "on"):
                return True
            if lowered in ("0", "false", "no", "off"):
                return False
    except (ValueError, TypeError):
        pass
    return value


def _env_file_path() -> Path:
    """Configurable .env target (ISTARA_ENV_FILE) for read-only containers.

    Deployed stacks run with a read-only rootfs; runtime-persisted settings
    (pi endpoints, OAuth credential blobs) must land on a mounted writable
    volume. Local checkouts keep the historical `.env` behavior.
    """
    configured = os.environ.get("ISTARA_ENV_FILE", "").strip()
    if configured:
        return Path(configured)
    if Path("/app/data/simulation-shared").is_dir():
        return Path("/app/data/simulation-shared/runtime_overrides.env")
    if Path("./data/simulation-shared").is_dir():
        return Path("./data/simulation-shared/runtime_overrides.env")
    return Path(".env")


def _write_or_update_file(path: Path, key: str, value: str) -> None:
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(f"{key}={value}\n")
        return

    lines = path.read_text().splitlines(keepends=True)
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
    path.write_text("".join(new_lines))


def _is_shared_env_file(path: Path) -> bool:
    """True when `path` is a shared-volume env file, not a private target.

    The simulation-shared volume is mounted by more than one deployment,
    so a secret written there can be read back by a different deployment —
    the one file target the write-side denylist still protects. The explicit
    ``ISTARA_ENV_FILE`` volume and the local ``.env`` fallback are
    deployment-private and are safe write targets (the read-side precedence
    rule in ``app.config`` already stops any file value from beating a
    container-supplied secret).
    """
    return path in (
        Path("/app/data/simulation-shared/runtime_overrides.env"),
        Path("./data/simulation-shared/runtime_overrides.env"),
    )


# Server-auth and data-encryption secrets must never land in a shared env
# file: only the deployment-private primary target (explicit ISTARA_ENV_FILE
# volume or local .env) receives them, never the shared-volume mirrors — so
# a stale/shared file cannot become a cross-deployment secret channel, while
# a runtime-generated secret still survives restarts (F-11/F-12). Callers
# needing the distinction should read the return value.
#
# The list itself lives in the leaf module `app.core.env_secrets` and is
# re-exported here: `app.config` needs the SAME boundary on the read side (a
# write-side denylist alone is not sufficient, because files written by
# earlier builds already contain these keys — F-7), and importing it from
# this module would make configuration and persistence import each other.
__all__ = ["SECRET_ENV_DENYLIST", "persist_env_value"]


def persist_env_value(key: str, value: str) -> bool:
    """Update process memory and the env file so the setting survives restarts.

    Returns True when the value was also written to file(s). Secrets in
    ``SECRET_ENV_DENYLIST`` are written to the deployment-private primary
    target only (the explicit ``ISTARA_ENV_FILE`` volume, or the local
    ``.env`` fallback) and never to the shared-volume mirror candidates; the
    function returns False — memory and live settings only — solely when no
    private target is configured and the primary itself resolves to a shared
    file, so callers can log custody honestly.
    """
    # 1. Update os.environ immediately in memory
    os.environ[key] = value

    # 2. Update settings instance if matching attribute exists (coerced to
    #    the field type so later numeric comparisons never see a raw str).
    try:
        from app.config import settings

        attr = key.lower()
        if hasattr(settings, attr):
            setattr(settings, attr, _coerce_for_settings(attr, value))
    except Exception:
        pass

    # Server-auth and data-encryption secrets must never land in a
    # shared-volume env file, where a stale copy could be read back by a
    # different deployment — but they MUST reach the deployment-private
    # primary target, or an auto-generated DATA_ENCRYPTION_KEY is regenerated
    # on every restart and every field encrypted with the previous key
    # becomes permanently unrecoverable (F-11/F-12). The read-side precedence
    # rule in app.config (container environment wins for these keys) already
    # neutralizes file-beats-operator hijack, which is what makes the private
    # primary target safe to write.
    primary_path = _env_file_path()
    if key in SECRET_ENV_DENYLIST:
        if not os.environ.get("ISTARA_ENV_FILE", "").strip() and _is_shared_env_file(primary_path):
            return False
        try:
            _write_or_update_file(primary_path, key, value)
        except Exception:
            return False
        return True

    # 3. Write to the primary env file
    try:
        _write_or_update_file(primary_path, key, value)
    except Exception:
        return False

    # 4. Also mirror to persistent runtime_overrides.env in shared volume if present
    for candidate in [
        Path("/app/data/simulation-shared/runtime_overrides.env"),
        Path("./data/simulation-shared/runtime_overrides.env"),
    ]:
        if candidate.parent.is_dir() and candidate != primary_path:
            try:
                _write_or_update_file(candidate, key, value)
            except Exception:
                pass
    return True
