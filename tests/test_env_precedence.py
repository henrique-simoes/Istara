"""Runtime env-file precedence and persistent-path resolution.

Pins the four behavioural hunks of `backend/app/config.py`'s import-time env
loading (F-7/F-8/F-9). The loading runs at module import, so precedence is
exercised in a FRESH interpreter per case: importing the already-imported
`app.config` in-process would prove nothing.
"""

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from app.config import Settings
from app.core.env_persistence import SECRET_ENV_DENYLIST

_BACKEND = Path(__file__).resolve().parent.parent / "backend"

# Keys the container environment must always win on.
SECRETS = ("ADMIN_PASSWORD", "JWT_SECRET", "DATA_ENCRYPTION_KEY", "NETWORK_ACCESS_TOKEN")


def _probe(env: dict, keys, cwd: Path) -> dict:
    """Import app.config in a fresh interpreter; return os.environ for `keys`."""
    script = textwrap.dedent(
        """
        import json, os, sys
        sys.path.insert(0, sys.argv[1])
        import app.config  # noqa: F401  (import-time env loading is under test)
        print(json.dumps({k: os.environ.get(k) for k in sys.argv[2:]}))
        """
    )
    full_env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        # Keep the fresh interpreter off the developer checkout's database.
        "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
        **env,
    }
    proc = subprocess.run(
        [sys.executable, "-c", script, str(_BACKEND), *keys],
        capture_output=True,
        text=True,
        cwd=str(cwd),
        env=full_env,
    )
    assert proc.returncode == 0, f"probe failed:\n{proc.stderr}"
    return json.loads(proc.stdout.strip().splitlines()[-1])


@pytest.fixture()
def runtime_env_file(tmp_path):
    """A stale runtime env file of the kind earlier builds wrote."""
    path = tmp_path / "runtime-state" / "env"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [f"{k}=stale-file-{k.lower()}" for k in SECRETS]
            + ["LLM_PROVIDER=file-provider", ""]
        )
    )
    return path


# --- F-7: container env wins for secrets, file still wins for ordinary keys ---


def test_container_env_beats_runtime_file_for_secrets(runtime_env_file, tmp_path):
    """Rotating a secret through compose must not be a silent no-op."""
    env = {"ISTARA_ENV_FILE": str(runtime_env_file)}
    env.update({k: f"operator-{k.lower()}" for k in SECRETS})

    resolved = _probe(env, SECRETS, cwd=tmp_path)

    for key in SECRETS:
        assert resolved[key] == f"operator-{key.lower()}", (
            f"{key} resolved to the stale runtime env file value instead of the "
            "operator-supplied container environment value"
        )


def test_runtime_file_still_wins_for_ordinary_settings(runtime_env_file, tmp_path):
    """The override flip's intended behaviour: UI prefs survive a restart."""
    env = {
        "ISTARA_ENV_FILE": str(runtime_env_file),
        "LLM_PROVIDER": "container-provider",
    }

    resolved = _probe(env, ["LLM_PROVIDER"], cwd=tmp_path)

    assert resolved["LLM_PROVIDER"] == "file-provider"


def test_runtime_file_supplies_secret_when_container_env_is_absent(
    runtime_env_file, tmp_path
):
    """Denylisting is precedence, not erasure: existing deployments keep their key."""
    env = {"ISTARA_ENV_FILE": str(runtime_env_file)}

    resolved = _probe(env, ["DATA_ENCRYPTION_KEY"], cwd=tmp_path)

    # Denylisting is a precedence rule, not erasure: with nothing in the
    # container environment to protect, the file value is still adopted so
    # already-encrypted data stays decryptable.
    assert resolved["DATA_ENCRYPTION_KEY"] == "stale-file-data_encryption_key"


def test_denylist_is_shared_by_both_sides_of_the_boundary():
    """One canonical list: a write-side-only denylist cannot fix stale files."""
    assert set(SECRETS) == set(SECRET_ENV_DENYLIST)


# --- F-8: runtime_overrides.env gate, load order, and redirect refusal --------


@pytest.fixture()
def overrides_dir(tmp_path):
    path = tmp_path / "data" / "simulation-shared"
    path.mkdir(parents=True)
    (path / "runtime_overrides.env").write_text(
        "LLM_PROVIDER=overrides-provider\nADMIN_PASSWORD=stale-overrides-admin\n"
    )
    return tmp_path


def test_runtime_overrides_not_loaded_without_opt_in(overrides_dir):
    """A CWD-relative file must not inject env into a process that just runs there."""
    resolved = _probe({}, ["LLM_PROVIDER"], cwd=overrides_dir)

    assert resolved["LLM_PROVIDER"] != "overrides-provider"


def test_runtime_overrides_loaded_when_opted_in(overrides_dir):
    resolved = _probe(
        {"ISTARA_RUNTIME_OVERRIDES": "1"}, ["LLM_PROVIDER"], cwd=overrides_dir
    )

    assert resolved["LLM_PROVIDER"] == "overrides-provider"


def test_runtime_env_file_beats_runtime_overrides(overrides_dir, runtime_env_file):
    """First-match-wins: ISTARA_ENV_FILE is env_persistence's primary write target."""
    resolved = _probe(
        {
            "ISTARA_RUNTIME_OVERRIDES": "1",
            "ISTARA_ENV_FILE": str(runtime_env_file),
        },
        ["LLM_PROVIDER"],
        cwd=overrides_dir,
    )

    assert resolved["LLM_PROVIDER"] == "file-provider"


def test_runtime_overrides_cannot_redirect_the_runtime_env_target(tmp_path):
    """A file must not choose which file is loaded next."""
    shared = tmp_path / "data" / "simulation-shared"
    shared.mkdir(parents=True)
    hijack = tmp_path / "hijack.env"
    hijack.write_text("LLM_PROVIDER=hijacked\n")
    (shared / "runtime_overrides.env").write_text(f"ISTARA_ENV_FILE={hijack}\n")

    resolved = _probe(
        {"ISTARA_RUNTIME_OVERRIDES": "1"},
        ["ISTARA_ENV_FILE", "LLM_PROVIDER"],
        cwd=tmp_path,
    )

    assert resolved["ISTARA_ENV_FILE"] is None
    assert resolved["LLM_PROVIDER"] != "hijacked"


def test_runtime_overrides_secrets_do_not_beat_container_env(overrides_dir):
    resolved = _probe(
        {"ISTARA_RUNTIME_OVERRIDES": "1", "ADMIN_PASSWORD": "operator-admin"},
        ["ADMIN_PASSWORD"],
        cwd=overrides_dir,
    )

    assert resolved["ADMIN_PASSWORD"] == "operator-admin"


def test_malformed_runtime_env_file_does_not_break_import(tmp_path):
    """Unreadable file: warn and continue, never crash the process."""
    bad = tmp_path / "runtime.env"
    bad.write_bytes(b"\xff\xfe not utf-8 at all \x00\n")

    # Regression: warning-and-continue is not enough on its own — the same
    # unparseable file was still handed to pydantic-settings' `env_file`, which
    # re-raised the decode error and aborted startup.
    resolved = _probe({"ISTARA_ENV_FILE": str(bad)}, ["ISTARA_ENV_FILE"], cwd=tmp_path)

    assert resolved["ISTARA_ENV_FILE"] == str(bad)


# --- F-9: _resolve_persistent_paths respects an explicit lance_db_path --------


@pytest.mark.parametrize("env_key", ["LANCE_DB_PATH", "lance_db_path"])
def test_explicit_lance_db_path_is_never_rewritten(tmp_path, monkeypatch, env_key):
    """pydantic-settings is case-insensitive; the guard must be too."""
    shared = tmp_path / "data" / "simulation-shared"
    shared.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(env_key, "./data/lance_db")

    resolved = Settings(_env_file=None)

    assert resolved.lance_db_path == "./data/lance_db"
    assert resolved._ephemeral_lance_db is False


def test_unset_lance_db_path_still_resolves_to_shared_storage(tmp_path, monkeypatch):
    """The resolution behaviour itself must survive the guard change."""
    shared = tmp_path / "data" / "simulation-shared"
    shared.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("LANCE_DB_PATH", raising=False)

    # `_env_file=None`: the developer checkout's backend/.env sets
    # LANCE_DB_PATH explicitly, which is the very case the guard now honours.
    resolved = Settings(_env_file=None)

    assert resolved.lance_db_path == "./data/simulation-shared/lance_db"


def test_ephemeral_lance_db_warning_is_deferred_not_emitted_at_import(
    tmp_path, monkeypatch, caplog
):
    """Import-time logging runs before logging is configured; defer it."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("LANCE_DB_PATH", raising=False)
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

    with caplog.at_level("WARNING"):
        resolved = Settings(_env_file=None)
    assert "ephemeral" not in caplog.text

    assert resolved._ephemeral_lance_db is True
    with caplog.at_level("WARNING"):
        resolved.log_storage_warnings()
    assert "LanceDB path is ephemeral" in caplog.text
