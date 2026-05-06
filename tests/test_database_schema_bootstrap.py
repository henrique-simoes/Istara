import os
import subprocess
import sys
from pathlib import Path


def test_fresh_init_db_creates_agent_learning_table(tmp_path):
    """Fresh installs must create core-owned SQLAlchemy tables before startup jobs run."""
    db_path = tmp_path / "istara.db"
    repo_root = Path(__file__).resolve().parents[1]
    script = """
import asyncio
from pathlib import Path
from sqlalchemy import text
from app.models.database import async_session, init_db

async def main():
    await init_db()
    async with async_session() as db:
        result = await db.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='agent_learnings'")
        )
        if result.scalar_one_or_none() != "agent_learnings":
            raise SystemExit("agent_learnings table was not created")

asyncio.run(main())
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "backend")
    env["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    env["DATA_DIR"] = str(tmp_path / "data")
    env["UPLOAD_DIR"] = str(tmp_path / "data" / "uploads")
    env["LANCE_DB_PATH"] = str(tmp_path / "data" / "lance_db")

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=repo_root / "backend",
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr or result.stdout
