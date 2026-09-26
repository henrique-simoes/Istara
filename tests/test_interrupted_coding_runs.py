"""A coding run cut off by a restart settles as blocked instead of running forever (2026-09-26).

Coding runs execute inside the backend process. A run stopped mid-way on the live lane (the
process ended while the local coder was still loading) stayed ``running`` with no completion time:
its promotion never settled, and nothing said why. The backend is one process, so a run still
``running`` at startup was cut off by the previous one: startup marks it blocked, says so, and
leaves every settled run alone.
"""

from __future__ import annotations

import inspect
import uuid

from sqlalchemy import delete, select


async def _run(db, status: str) -> str:
    from app.models.research_validity import CodingRun

    run_id = f"interrupted-test-{uuid.uuid4().hex[:8]}"
    db.add(
        CodingRun(id=run_id, project_id="proj-interrupted", status=status, created_by="test")
    )
    await db.commit()
    return run_id


async def test_a_run_left_running_by_the_previous_process_settles_as_blocked():
    from app.models.database import async_session, init_db
    from app.models.research_validity import CodingRun
    from app.services.research_validity_service import settle_interrupted_coding_runs

    await init_db()
    async with async_session() as db:
        await db.execute(delete(CodingRun).where(CodingRun.project_id == "proj-interrupted"))
        await db.commit()
        running = await _run(db, "running")
        completed = await _run(db, "completed")

        settled = await settle_interrupted_coding_runs(db)

        rows = {
            r.id: r
            for r in (
                await db.execute(
                    select(CodingRun).where(CodingRun.project_id == "proj-interrupted")
                )
            ).scalars()
        }
    assert settled == [running]
    assert rows[running].status == "blocked"
    assert rows[running].promotion_status == "blocked"
    assert "interrupted" in rows[running].fallback_reason.lower()
    assert rows[running].completed_at is not None
    assert rows[completed].status == "completed"
    assert rows[completed].fallback_reason == ""


def test_startup_settles_interrupted_runs():
    from app.main import lifespan

    assert "settle_interrupted_coding_runs" in inspect.getsource(lifespan)
