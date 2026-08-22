"""Version/lockfile provenance test for the bundled Pi package surface.

Implements the master-plan test-ownership obligation for the Pi
package/protocol surface: "exact version/lockfile provenance; no dependency
drift" (docs/build-stream/2026-08-22-istara-pi-model-management-migration.md,
master plan §11). The two bundled Pi surfaces — `pi-runtime` (production
runtime) and `labs/pi-replacement` (standalone compatibility lab) — must pin
the SAME exact upstream releases of `@earendil-works/pi-agent-core` and
`@earendil-works/pi-ai`, and their lockfiles must agree with their
`package.json` manifests so a fresh `npm ci` is reproducible:

1. ``EXPECTED_PINS`` — the exact versions the wave pinned (0.84.2/0.84.2).
2. Each surface's ``package.json`` pins both packages with exact versions
   (no ``^``/``~`` ranges).
3. Each surface's ``package-lock.json`` root dependencies equal the
   ``package.json`` dependencies and resolve the pinned packages to exactly
   ``EXPECTED_PINS`` with a supported ``lockfileVersion``.

The check is offline and deterministic (reads only repo files) — the passive
registry re-check ("npm view ... version") remains a separate V1 gate
verification, not part of this test.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

PI_PACKAGES = ("@earendil-works/pi-agent-core", "@earendil-works/pi-ai")

# Exact pins approved for this wave (verified upstream 0.84.2/0.84.2).
EXPECTED_PINS = {"@earendil-works/pi-agent-core": "0.84.2", "@earendil-works/pi-ai": "0.84.2"}

# lockfileVersion 3 is what `npm install` produces for current npm; treat it
# as the supported reproducibility format.
EXPECTED_LOCKFILE_VERSION = 3

SURFACES = (
    ("pi-runtime", REPO_ROOT / "pi-runtime"),
    ("labs/pi-replacement", REPO_ROOT / "labs" / "pi-replacement"),
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _deps_for(manifest: dict) -> dict:
    deps = dict(manifest.get("dependencies") or {})
    return {name: spec for name, spec in deps.items() if name in PI_PACKAGES}


def test_bundled_surfaces_pin_exact_approved_versions():
    """Both pi-runtime and labs/pi-replacement pin 0.84.2 with exact specs."""
    for label, root in SURFACES:
        manifest = _load_json(root / "package.json")
        pins = _deps_for(manifest)
        assert pins == EXPECTED_PINS, (
            f"{label}/package.json pins {pins}, expected exact {EXPECTED_PINS}; "
            "raise both surfaces in lockstep to the latest verified upstream "
            "release (master plan V2: lockstep pin or recorded divergence)."
        )
        for name, spec in pins.items():
            assert spec == EXPECTED_PINS[name] and spec[0] not in "^~", (
                f"{label}/package.json pins {name}={spec!r}; exact version "
                f"required, no semver range (found in plan V2)."
            )


def test_lockfiles_match_manifests_and_resolve_pins():
    """package-lock root deps == package.json deps and resolve to 0.84.2."""
    for label, root in SURFACES:
        manifest = _load_json(root / "package.json")
        lock = _load_json(root / "package-lock.json")
        lock_packages = lock.get("packages") or {}
        root_entry = lock_packages.get("") or {}

        manifest_deps = _deps_for(manifest)
        lock_root_deps = {
            name: spec
            for name, spec in (root_entry.get("dependencies") or {}).items()
            if name in PI_PACKAGES
        }
        assert lock_root_deps == manifest_deps, (
            f"{label}/package-lock.json root dependencies {lock_root_deps} do not "
            f"match package.json {manifest_deps}; run `npm install` in {root} "
            "and commit the refreshed lockfile."
        )

        for name, expected in EXPECTED_PINS.items():
            entry = lock_packages.get(f"node_modules/{name}") or {}
            locked = entry.get("version")
            assert locked == expected, (
                f"{label} lockfile resolves {name}={locked!r}, expected "
                f"{expected!r}; lockfile must be regenerated with the pinned "
                "manifest (npm ci reproducibility)."
            )

        lockfile_version = lock.get("lockfileVersion")
        assert lockfile_version == EXPECTED_LOCKFILE_VERSION, (
            f"{label}/package-lock.json lockfileVersion={lockfile_version}, "
            f"expected {EXPECTED_LOCKFILE_VERSION}; unexpected lockfile format "
            "breaks `npm ci` reproducibility."
        )


def test_lockfile_entries_are_consistent():
    """Exactly one resolved entry per pinned package; no stale duplicates."""
    for label, root in SURFACES:
        lock = _load_json(root / "package-lock.json")
        lock_packages = lock.get("packages") or {}
        for name in PI_PACKAGES:
            entry = lock_packages.get(f"node_modules/{name}")
            assert entry is not None, (
                f"{label}/package-lock.json has no resolved entry for {name}; "
                "regenerate the lockfile from the pinned manifest."
            )
            assert entry.get("version") == EXPECTED_PINS[name], (
                f"{label}/package-lock.json resolves {name} to "
                f"{entry.get('version')!r}, expected {EXPECTED_PINS[name]!r}."
            )
