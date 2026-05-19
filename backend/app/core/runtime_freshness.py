"""Runtime/source freshness checks for local operator diagnostics."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


FRONTEND_SOURCE_GLOBS = ("**/*.css", "**/*.js", "**/*.mjs", "**/*.ts", "**/*.tsx")
STALE_GRACE_SECONDS = 1.0

_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _iso_timestamp(value: float | None) -> str | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value, tz=UTC).isoformat()


def _frontend_sources(frontend_src: Path) -> list[Path]:
    if not frontend_src.exists():
        return []
    files: list[Path] = []
    for pattern in FRONTEND_SOURCE_GLOBS:
        files.extend(path for path in frontend_src.rglob(pattern) if path.is_file())
    return sorted(set(files))


def _safe_mtime(path: Path) -> float | None:
    try:
        return path.stat().st_mtime
    except OSError:
        return None


def detect_runtime_freshness(
    repo_root: Path | str | None = None,
    *,
    ttl_seconds: float = 30.0,
) -> dict[str, Any]:
    """Report whether the production frontend bundle predates source files.

    This is intentionally read-only and lightweight enough for status polling.
    It detects the class of confusion where source-level project-isolation fixes
    exist, but the running Next production bundle still serves older code.
    """
    root = Path(repo_root) if repo_root is not None else _repo_root()
    cache_key = str(root.resolve() if root.exists() else root)
    now = time.monotonic()
    cached = _CACHE.get(cache_key)
    if cached and ttl_seconds > 0 and now - cached[0] < ttl_seconds:
        return cached[1]

    build_id_path = root / "frontend" / ".next" / "BUILD_ID"
    build_mtime = _safe_mtime(build_id_path)
    build_id = None
    if build_id_path.exists():
        try:
            build_id = build_id_path.read_text(encoding="utf-8").strip() or None
        except OSError:
            build_id = None

    source_files = _frontend_sources(root / "frontend" / "src")
    source_mtimes = [
        (path, mtime)
        for path in source_files
        if (mtime := _safe_mtime(path)) is not None
    ]
    newest_source_mtime = max((mtime for _, mtime in source_mtimes), default=None)

    source_newer_than_build: list[str] = []
    if build_mtime is not None:
        source_newer_than_build = [
            str(path.relative_to(root))
            for path, mtime in source_mtimes
            if mtime > build_mtime + STALE_GRACE_SECONDS
        ]

    stale = bool(build_mtime is not None and source_newer_than_build)
    if stale:
        status = "stale"
        message = "The production frontend build predates frontend source changes; rebuild and restart the frontend."
    elif build_mtime is None:
        status = "development_or_unbuilt"
        message = "No production frontend build id was found; this usually means a development server or unbuilt checkout."
    else:
        status = "fresh"
        message = "The production frontend build is at least as new as the tracked frontend source files."

    payload: dict[str, Any] = {
        "frontend": {
            "status": status,
            "stale": stale,
            "build_present": build_mtime is not None,
            "build_id": build_id,
            "build_mtime": _iso_timestamp(build_mtime),
            "newest_source_mtime": _iso_timestamp(newest_source_mtime),
            "source_file_count": len(source_files),
            "source_newer_than_build_count": len(source_newer_than_build),
            "source_newer_than_build": source_newer_than_build[:20],
            "message": message,
        }
    }
    _CACHE[cache_key] = (now, payload)
    return payload
