"""D-10/D-11: desktop versions an MSI accepts, a VERSION that keeps up, and a bundled source.

Every Windows build after 8 August failed because the desktop semver's MINOR was month*31+day
(> 255); VERSION lagged the release tags by four months; and the source the desktop app installs
on first run was copied in after the build, so the Windows and Linux installers never had it.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _semver(calver: str) -> str:
    result = subprocess.run(  # noqa: PLW1510 (exit status is the assertion)
        ["bash", str(ROOT / "scripts" / "set-version.sh"), "--semver-of", calver],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _key(semver: str) -> tuple[int, ...]:
    return tuple(int(part) for part in semver.split("."))


def test_desktop_semver_mapping():
    assert _semver("2026.09.27") == "126.9.2700"
    assert _semver("2026.09.27.3") == "126.9.2703"
    assert _semver("2027.01.02") == "127.1.200"


def test_every_day_of_the_year_fits_the_msi_and_sorts_in_order():
    day = date(2026, 1, 1)
    previous = None
    while day.year == 2026:
        for build in ("", ".2", ".99"):
            major, minor, patch = _key(_semver(f"{day:%Y.%m.%d}{build}"))
            assert major <= 255 and minor <= 255 and patch <= 65535
            current = (major, minor, patch)
            assert previous is None or current > previous
            previous = current
        day += timedelta(days=45) if day.day == 1 else timedelta(days=1)


def test_new_versions_sort_above_every_old_desktop_version():
    # Old mapping: 26.<month*31+day>.<build>; its largest value was 26.403.x (31 December).
    assert _key(_semver("2026.09.27")) > (26, 12 * 31 + 31, 99)


def test_set_version_rejects_what_is_not_calver():
    for bad in ("bad", "2026.13.01", "2026.09"):
        result = subprocess.run(  # noqa: PLW1510
            ["bash", str(ROOT / "scripts" / "set-version.sh"), "--semver-of", bad],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0


def test_version_drift_ordering():
    drift = _load("check_version_drift")
    assert drift.parse("v2026.09.27") < drift.parse("2026.09.27.2") < drift.parse("2026.10.01")
    assert drift.parse("2026.05.27.3") < drift.parse("v2026.09.26.6")
    assert drift.parse("latest") is None


@pytest.mark.skipif(
    shutil.which("git") is None or not (ROOT / ".git").exists(),
    reason="staging reads the git index; needs git and a checkout",
)
def test_staged_bundle_is_exactly_the_tracked_source(tmp_path):
    stage = _load("stage_desktop_bundle")
    report = stage.stage(tmp_path / "istara")
    assert report["has_backend_app"] and report["has_version"]
    out = Path(report["out"])
    assert (out / "backend" / "app" / "core" / "pi_runtime" / "data").is_dir()
    assert not any(p.name == ".env" for p in out.rglob(".env"))
    assert not any(p.suffix in {".db", ".sqlite3"} for p in out.rglob("*"))
    tracked = set(stage.tracked_files())
    staged = {str(p.relative_to(out)) for p in out.rglob("*") if p.is_file()}
    assert staged == tracked
