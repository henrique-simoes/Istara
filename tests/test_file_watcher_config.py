import uuid
from pathlib import Path

import pytest

from app.config import settings
from app.core.file_watcher import FileWatcher
from app.models.database import async_session, init_db
from app.models.project import Project


def test_file_watcher_state_follows_configured_data_dir(tmp_path):
    original_data_dir = settings.data_dir
    try:
        settings.data_dir = str(tmp_path / "runtime-data")
        watcher = FileWatcher()

        assert watcher._state_file == Path(settings.data_dir) / "watcher_state.json"
    finally:
        settings.data_dir = original_data_dir


@pytest.mark.asyncio
async def test_file_watcher_skips_paused_projects(tmp_path):
    await init_db()
    project = Project(
        id=str(uuid.uuid4()),
        name="Paused watcher project",
        is_paused=True,
    )
    async with async_session() as db:
        db.add(project)
        await db.commit()

    file_path = tmp_path / "interview-notes.txt"
    file_path.write_text("interviewer: hello\nparticipant: hi", encoding="utf-8")
    watcher = FileWatcher()

    result = await watcher._process_file(file_path, project.id)

    assert result is None
