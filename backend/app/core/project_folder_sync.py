"""The project folder sync, reachable from agent tools without importing the API layer.

The Documents routes own the sync (``register_untracked_project_files``) and register it here when
they load. The agent's ``sync_project_documents`` tool calls it through this module, so tool code
never imports a route module: that import would close a cycle through the Pi runtime, whose tool
registry imports the system actions.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

FolderSync = Callable[..., Awaitable[dict[str, Any]]]

_sync: FolderSync | None = None


def register(sync: FolderSync) -> None:
    """Install the folder sync (called by the Documents routes at import)."""
    global _sync
    _sync = sync


def registered() -> FolderSync | None:
    """The installed folder sync, or None when the Documents routes are not loaded."""
    return _sync
