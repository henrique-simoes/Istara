from pathlib import Path

from app.config import settings
from app.core.file_watcher import FileWatcher


def test_file_watcher_state_follows_configured_data_dir(tmp_path):
    original_data_dir = settings.data_dir
    try:
        settings.data_dir = str(tmp_path / "runtime-data")
        watcher = FileWatcher()

        assert watcher._state_file == Path(settings.data_dir) / "watcher_state.json"
    finally:
        settings.data_dir = original_data_dir
