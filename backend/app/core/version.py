"""Application version helpers."""

from __future__ import annotations

from pathlib import Path


def read_istara_version() -> str:
    """Read the CalVer application version from the repository VERSION file."""
    try:
        version_file = Path(__file__).resolve().parents[3] / "VERSION"
        if version_file.exists():
            return version_file.read_text().strip()
    except Exception:
        pass
    return "dev"
