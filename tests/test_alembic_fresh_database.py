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
        revision = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()
    assert revision == ("036_project_assurance_policies",)
    with sqlite3.connect(database_path) as connection:
        columns = {row[1]: row for row in connection.execute("PRAGMA table_info(embedding_profiles)")}
    # Profiles from before prompt schemes existed were built from raw text.
    assert columns["prompt_scheme"][4] == "'raw'"
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute("PRAGMA table_info(decision_model_project_policies)")
        policy_columns = {row[1] for row in rows}
    # Hosted decision-model egress is opt-in per project (no row = denied).
    assert {"project_id", "hosted_egress_endpoint_ids_json", "updated_by"} <= policy_columns
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    assert {"decision_trajectories", "decision_trust_evaluations"} <= tables
    assert "project_assurance_policies" in tables
    with sqlite3.connect(database_path) as connection:
        metric_columns = {row[1] for row in connection.execute("PRAGMA table_info(method_metrics)")}
    assert {"human_agree_count", "human_disagree_count"} <= metric_columns
