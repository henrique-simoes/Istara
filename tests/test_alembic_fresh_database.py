"""Fresh-install coverage for the complete Alembic revision chain."""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path


def test_upgrade_head_succeeds_on_fresh_sqlite(tmp_path: Path) -> None:
    """Every supported revision must apply to Istara's default SQLite database."""
    repo_root = Path(__file__).resolve().parents[1]
    backend_root = repo_root / "backend"
    database_path = tmp_path / "fresh-istara.db"
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite+aiosqlite:///{database_path}"

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=backend_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    with sqlite3.connect(database_path) as connection:
        revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()
    assert revision == ("032_pi_tool_executions",)
