"""B0 offline scheduler: run-unit compilation, sharding, immutable wave manifest.

The "B0 offline scheduling + B1..B_N process waves" plan schedules every live
benchmark run offline first (B0), then fans the work out to at most
``max_processes`` wave processes. This module is that offline half:

- :func:`build_run_units` expands scenarios x seeds x repeats x engines x MoA modes
  into deterministic :class:`RunUnit` records, tagged with their work-package phase
  (B1 canonical, B2 a2a, B3 spine).
- :func:`shard_units` splits units deterministically into disjoint, complete shards.
- :func:`write_manifest` persists the immutable shard manifest. Re-running B0 with
  identical arguments is an idempotent resume (the existing file is returned
  unchanged); differing arguments raise :class:`ManifestConflict` — the manifest is
  never silently overwritten.
- :func:`load_manifest` verifies the manifest's content hash on every read.
- :func:`completed_unit_ids` drives resume: a unit is complete only when its record
  file parses AND validates against the metrics schema.

Import-safe at T0: importing this module touches no backend, DB, network, or model
(the schema validator is imported lazily inside :func:`completed_unit_ids`).
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MANIFEST_SCHEMA_VERSION = "1.0.0"
MANIFEST_KIND = "pi_benchmark_wave_manifest"

# Work-package phase per pack (master plan wave split); unknown packs default to B2.
_PHASE_BY_PACK = {"canonical": "B1", "a2a": "B2", "spine": "B3"}
_DEFAULT_PHASE = "B2"


class ManifestConflict(RuntimeError):
    """Raised when an existing manifest conflicts, or a loaded one fails its hash."""


@dataclass(frozen=True)
class RunUnit:
    """One indivisible benchmark run: scenario x seed x repeat x engine (x MoA)."""

    unit_id: str
    pack: str
    scenario_id: str
    seed: int
    repeat: int
    engine: str
    phase: str  # work-package phase "B1"|"B2"|"B3"|"B4"
    moa_mode: str | None = None  # None | "self_moa" | "full_ensemble"


def build_run_units(
    *,
    scenarios: list,
    tier: str,
    engines: tuple[str, ...],
    seeds: tuple[int, ...],
    repeats: int,
    moa_modes: tuple[str, ...] = (),
) -> list[RunUnit]:
    """Expand scenarios into deterministic run units.

    ``scenarios`` are :class:`tests.pi_benchmark.scenarios.base.Scenario` objects
    (anything with ``.id`` and ``.pack``). Order is fully deterministic: scenario
    order as given, then seed, then repeat, then engine, then MoA mode.
    """
    units: list[RunUnit] = []
    for scenario in scenarios:
        phase = _PHASE_BY_PACK.get(scenario.pack, _DEFAULT_PHASE)
        for seed in seeds:
            for repeat in range(repeats):
                for engine in engines:
                    for moa_mode in moa_modes or (None,):
                        unit_id = (
                            f"{phase}-{tier}-{scenario.pack}-{scenario.id}"
                            f"-seed{seed}-r{repeat}-{engine}"
                        )
                        if moa_mode is not None:
                            unit_id += f"-{moa_mode}"
                        units.append(
                            RunUnit(
                                unit_id=unit_id,
                                pack=scenario.pack,
                                scenario_id=scenario.id,
                                seed=seed,
                                repeat=repeat,
                                engine=engine,
                                phase=phase,
                                moa_mode=moa_mode,
                            )
                        )
    return units


def shard_units(units: list[RunUnit], n: int) -> list[list[RunUnit]]:
    """Split ``units`` into ``n`` deterministic, disjoint, complete shards.

    Round-robin by unit index. ``n`` must be >= 1 — a missing or invalid
    ``max_processes`` fails closed with ValueError rather than guessing.
    """
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        raise ValueError(f"shard count must be an int >= 1, got {n!r}")
    shards: list[list[RunUnit]] = [[] for _ in range(n)]
    for index, unit in enumerate(units):
        shards[index % n].append(unit)
    # Disjoint + complete: shards cover every unit exactly once.
    shard_ids = [unit.unit_id for shard in shards for unit in shard]
    assert len(shard_ids) == len(units) and len(set(shard_ids)) == len(shard_ids), (
        "shard map must partition the run units exactly"
    )
    return shards


def _content_sha256(manifest: dict[str, Any]) -> str:
    """Hash of the canonical JSON of the manifest WITHOUT the hash field.

    ``created_ts`` is also excluded: it is provenance, not schedule content, and
    including it would make idempotent B0 resume impossible (a fresh timestamp
    would change the hash on every invocation).
    """
    content = {
        key: value
        for key, value in manifest.items()
        if key not in ("content_sha256", "created_ts")
    }
    canonical = json.dumps(content, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def write_manifest(
    path,
    *,
    max_processes: int,
    provider: str,
    model: str,
    budget_cap_usd: float,
    moa_n: int,
    repeats: int,
    tier: str,
    shards: list[list[RunUnit]],
) -> dict:
    """Write the immutable wave manifest, or resume an identical one.

    If ``path`` exists: the would-be content hash is recomputed from the arguments.
    Equal hash -> the existing manifest is returned unchanged (idempotent B0
    resume, no rewrite). Different hash -> :class:`ManifestConflict`; the existing
    manifest is never silently overwritten.
    """
    if not isinstance(max_processes, int) or isinstance(max_processes, bool) or max_processes < 1:
        raise ValueError(f"max_processes must be an int >= 1, got {max_processes!r}")
    if max_processes != len(shards):
        raise ValueError(
            f"max_processes ({max_processes}) must equal the shard count ({len(shards)})"
        )
    path = Path(path)
    manifest: dict[str, Any] = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "kind": MANIFEST_KIND,
        "created_ts": datetime.now(timezone.utc).isoformat(),
        "max_processes": max_processes,
        "provider": provider,
        "model": model,
        "budget_cap_usd": budget_cap_usd,
        "moa_n": moa_n,
        "repeats": repeats,
        "tier": tier,
        "shard_count": len(shards),
        "shards": [[unit.unit_id for unit in shard] for shard in shards],
        "units": {
            unit.unit_id: {
                "pack": unit.pack,
                "scenario_id": unit.scenario_id,
                "seed": unit.seed,
                "repeat": unit.repeat,
                "engine": unit.engine,
                "phase": unit.phase,
                "moa_mode": unit.moa_mode,
                "status": "pending",
            }
            for shard in shards
            for unit in shard
        },
    }
    if path.exists():
        existing = load_manifest(path)  # also verifies the stored hash
        if _content_sha256(existing) == _content_sha256(manifest):
            return existing
        raise ManifestConflict(
            f"manifest {path} already exists with different content; "
            "refusing to overwrite the immutable B0 schedule"
        )
    manifest["content_sha256"] = _content_sha256(manifest)
    # Atomic write (tmp + rename) so a wave process never reads a torn manifest.
    tmp_path = path.with_name(path.name + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(tmp_path, path)
    return manifest


def load_manifest(path) -> dict:
    """Read the manifest and verify its content hash (tamper-evident)."""
    path = Path(path)
    with path.open(encoding="utf-8") as handle:
        manifest = json.load(handle)
    stored = manifest.get("content_sha256")
    if not stored or _content_sha256(manifest) != stored:
        raise ManifestConflict(
            f"manifest {path} failed its content hash; refusing to schedule from it"
        )
    return manifest


def completed_unit_ids(records_dir) -> set[str]:
    """Unit ids (record file stems) with a parseable, schema-valid run record.

    Corrupt or off-schema files are NOT complete — the unit will be re-run. (The
    runner writes records atomically via tmp+rename, so partial files should not
    occur in practice; anything that slips through is treated as unfinished.)
    """
    from tests.pi_benchmark.schema import validate_record  # lazy: keeps import T0-light

    completed: set[str] = set()
    records_path = Path(records_dir)
    if not records_path.is_dir():
        return completed
    for record_file in sorted(records_path.glob("*.json")):
        try:
            with record_file.open(encoding="utf-8") as handle:
                record = json.load(handle)
            validate_record(record)
        except Exception:
            continue
        completed.add(record_file.stem)
    return completed
