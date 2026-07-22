"""Paired benchmark runner (task B0-4, master plan §10.3).

One paired runner, zero engine-specific scenarios: a single invocation executes
``scenario × seed × engine`` and emits one schema-conformant record per run, so pairing,
seeding, and fixture identity hold by construction rather than by convention (winning
plan §2.2 principle 1). Engine is a run-level parameter — the runner records the resolved
engine label on every record; the dispatcher header plumbing itself is proven by the node
harnesses (B0-2) and the dispatcher's own contract tests.

Tier discipline is enforced *here*, not by reviewer vigilance (winning plan §2.2
principle 3): ``--tier`` is mandatory and recorded on every record. T0/T1 execute an
offline, model-free contract driver. T2/T3 are fail-closed behind the owner gate — the
runner refuses to run them without a gate artifact and never loads a model in this build
(AGENTS.md live-model rule; owner gates G1/G2).

Every record is validated against ``comparison-Istara-pi/metrics-schema.json`` (via
:mod:`tests.pi_benchmark.schema`) before it is written, so a run can never emit an
off-contract record. Records and manifests land under ``--out`` (kept in the gitignored
``.results/`` tree).

Import-safe at T0: importing this module touches no backend, DB, network, or model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

# Allow both invocation styles: `python -m tests.pi_benchmark.runner` (package import,
# used by the tests) and `python tests/pi_benchmark/runner.py` (the plan's §5 command,
# where the repo root is not yet on sys.path). The latter needs the root injected before
# the absolute `tests.pi_benchmark` imports resolve.
if __package__ in (None, ""):  # pragma: no cover - only hit in script mode
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.pi_benchmark import schema
from tests.pi_benchmark.scenarios import PACK_NAMES, Scenario, load_pack
from tests.pi_benchmark.scenarios.base import tier_at_least

SCHEMA_VERSION = "1.0.0"
ENGINES = ("pi", "legacy")
TIERS = ("T0", "T1", "T2", "T3")
OFFLINE_TIERS = ("T0", "T1")
# Packs whose scenarios come from a static list (the others are compiled by B0-6/B0-8).
STATIC_PACKS = PACK_NAMES


class OwnerGateRequired(RuntimeError):
    """Raised when a T2/T3 run is attempted without an owner-gate artifact."""


@dataclass(frozen=True)
class RunConfig:
    packs: tuple[str, ...]
    tier: str
    engines: tuple[str, ...]
    seeds: tuple[int, ...]
    repeats: int
    phase: str
    out_dir: Path
    owner_gate: Path | None = None
    dry_run: bool = False

    def __post_init__(self) -> None:
        if self.tier not in TIERS:
            raise ValueError(f"invalid tier {self.tier!r}")
        if self.phase not in ("B1", "B2", "B3", "B4"):
            raise ValueError(f"invalid phase {self.phase!r}")
        for engine in self.engines:
            if engine not in ENGINES:
                raise ValueError(f"invalid engine {engine!r}")
        if self.repeats < 1:
            raise ValueError("repeats must be >= 1")


@dataclass
class RunSummary:
    config: RunConfig
    records: list[dict[str, Any]] = field(default_factory=list)
    manifest: dict[str, Any] = field(default_factory=dict)

    @property
    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for record in self.records:
            out[record["status"]] = out.get(record["status"], 0) + 1
        return out


# ── provenance helpers ──────────────────────────────────────────────────────


def _git(*args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args], cwd=str(_repo_root()), stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:  # pragma: no cover - git absent / not a repo
        return ""


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def git_provenance() -> tuple[str, bool]:
    """Return ``(git_sha, git_dirty)``; sha falls back to a padded stub if git is absent."""
    sha = _git("rev-parse", "HEAD") or "0000000"
    dirty = bool(_git("status", "--porcelain"))
    return sha[: max(7, len(sha))] if len(sha) >= 7 else (sha + "0000000")[:7], dirty


def input_sha256(scenario_id: str, seed: int) -> str:
    """Deterministic 64-hex hash of the byte-identical input shared by both arms.

    Both engine arms of a pair pass the identical ``(scenario_id, seed)`` here, so the
    pair shares one ``input_sha256`` — a pair whose arms disagree is an ``invalid_pair``
    downstream, never compared (winning plan risk table).
    """
    payload = json.dumps({"scenario": scenario_id, "seed": seed}, sort_keys=True).encode()
    return hashlib.sha256(payload).hexdigest()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sample_rss_bytes() -> int | None:
    """Sample this process's RSS in bytes (T2 live memory-load axis). None if psutil absent."""
    try:
        import psutil  # imported lazily; not needed at T0/T1
    except Exception:  # pragma: no cover - psutil optional
        return None
    return int(psutil.Process().memory_info().rss)


# ── record construction ─────────────────────────────────────────────────────


def _order_for_pair(pair_index: int) -> str:
    """Alternate which arm ran first, per pair, to expose and control order bias."""
    return "legacy_first" if pair_index % 2 == 0 else "pi_first"


def build_record(
    *,
    config: RunConfig,
    scenario: Scenario,
    engine: str,
    seed: int,
    repeat: int,
    pair_index: int,
    git_sha: str,
    git_dirty: bool,
    ts: str,
    status: str,
    not_runnable_reason: str | None = None,
    metrics: dict[str, Any] | None = None,
    usage: dict[str, Any] | None = None,
    extensions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble one schema-conformant run record. Validates before returning."""
    record_id = f"{config.phase}-{config.tier}-{scenario.pack}-{scenario.id}-seed{seed}-r{repeat}-{engine}"
    pair_id = f"{config.phase}-{config.tier}-{scenario.pack}-{scenario.id}-seed{seed}-r{repeat}"
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "record_id": record_id,
        "pair_id": pair_id,
        "phase": config.phase,
        "tier": config.tier,
        "engine": engine,
        "pack": scenario.pack,
        "scenario": {
            "id": scenario.id,
            "title": scenario.title,
            "seed": seed,
            "order": _order_for_pair(pair_index),
        },
        "provenance": {
            "git_sha": git_sha,
            "git_dirty": git_dirty,
            "input_sha256": input_sha256(scenario.id, seed),
            "model_id": None,  # no model at T0/T1; T2/T3 live driver would fill this in
            "endpoint_fingerprint": "offline-contract",
            "ts": ts,
        },
        "status": status,
        "usage": usage if usage is not None else {
            # An offline contract run consumes no model tokens — a true, exact zero.
            "input_tokens": 0, "output_tokens": 0, "cache_tokens": 0,
            "total_tokens": 0, "cost_usd": 0, "estimate": False, "estimator": None,
        },
    }
    if not_runnable_reason is not None:
        record["not_runnable_reason"] = not_runnable_reason
    if metrics is not None:
        record["metrics"] = metrics
    if extensions is not None:
        record["extensions"] = extensions
    schema.validate_record(record)
    return record


# ── offline (T0/T1) execution ───────────────────────────────────────────────


def _offline_record(
    *, config: RunConfig, scenario: Scenario, engine: str, seed: int, repeat: int,
    pair_index: int, git_sha: str, git_dirty: bool, ts: str,
) -> dict[str, Any]:
    """Execute one scenario arm at an offline tier and build its record."""
    if not tier_at_least(config.tier, scenario.min_tier):
        # Scenario needs a higher tier than requested — counted, never dropped.
        return build_record(
            config=config, scenario=scenario, engine=engine, seed=seed, repeat=repeat,
            pair_index=pair_index, git_sha=git_sha, git_dirty=git_dirty, ts=ts,
            status="not_runnable", not_runnable_reason="feature_unavailable",
            extensions={"detail": {"reason": f"scenario min_tier={scenario.min_tier} > requested {config.tier}"}},
        )
    if scenario.contract_check is None:  # pragma: no cover - guarded by min_tier above
        return build_record(
            config=config, scenario=scenario, engine=engine, seed=seed, repeat=repeat,
            pair_index=pair_index, git_sha=git_sha, git_dirty=git_dirty, ts=ts,
            status="not_runnable", not_runnable_reason="feature_unavailable",
            extensions={"detail": {"reason": "no offline contract check"}},
        )
    result = scenario.contract_check(engine, seed)
    metrics = {"output_quality": {"deterministic_pass": result.passed}}
    return build_record(
        config=config, scenario=scenario, engine=engine, seed=seed, repeat=repeat,
        pair_index=pair_index, git_sha=git_sha, git_dirty=git_dirty, ts=ts,
        status="ok", metrics=metrics,
        # outcome_class is the stable label compared across seed repeats (acceptance A5).
        extensions={"outcome_class": result.outcome_class, "detail": result.detail},
    )


def _resolve_scenarios(packs: Iterable[str]) -> list[Scenario]:
    scenarios: list[Scenario] = []
    seen: set[str] = set()
    for pack in packs:
        for scenario in load_pack(pack):
            if scenario.id in seen:  # pragma: no cover - defensive
                continue
            seen.add(scenario.id)
            scenarios.append(scenario)
    return scenarios


def run_benchmark(config: RunConfig) -> RunSummary:
    """Execute a benchmark run and return its records + manifest (no disk writes)."""
    if config.tier not in OFFLINE_TIERS:
        _enforce_owner_gate(config)
        # Even with a gate artifact present, live T2/T3 execution (which would load a
        # model) is deliberately not implemented in this build — it is owner-gated
        # future work (G1/G2). Fail loudly rather than silently produce empty results.
        raise NotImplementedError(
            f"tier {config.tier} live execution is owner-gated future work (gates G1/G2); "
            "this build implements the T0/T1 offline driver only"
        )

    scenarios = _resolve_scenarios(config.packs)
    git_sha, git_dirty = git_provenance()
    ts = _utc_now_iso()
    records: list[dict[str, Any]] = []
    pair_index = 0
    for scenario in scenarios:
        for seed in config.seeds:
            for repeat in range(1, config.repeats + 1):
                for engine in config.engines:
                    records.append(_offline_record(
                        config=config, scenario=scenario, engine=engine, seed=seed,
                        repeat=repeat, pair_index=pair_index, git_sha=git_sha,
                        git_dirty=git_dirty, ts=ts,
                    ))
                pair_index += 1

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "phase": config.phase,
        "tier": config.tier,
        "packs": list(config.packs),
        "engines": list(config.engines),
        "seeds": list(config.seeds),
        "repeats": config.repeats,
        "git_sha": git_sha,
        "git_dirty": git_dirty,
        "generated_ts": ts,
        "record_count": len(records),
        "scenario_count": len(scenarios),
    }
    return RunSummary(config=config, records=records, manifest=manifest)


def _enforce_owner_gate(config: RunConfig) -> None:
    """Fail-closed: T2/T3 require an existing owner-gate artifact (acceptance A7/A11)."""
    gate = config.owner_gate
    if gate is None or not Path(gate).is_file():
        raise OwnerGateRequired(
            f"tier {config.tier} requires an owner-gate artifact (--owner-gate <path>); "
            "no live-model run or spend is permitted without gate G1/G2 evidence"
        )


# ── disk output ─────────────────────────────────────────────────────────────


def write_run(summary: RunSummary) -> Path:
    """Write records + manifest under ``config.out_dir``; returns the run directory."""
    out = summary.config.out_dir
    records_dir = out / "records"
    records_dir.mkdir(parents=True, exist_ok=True)
    for record in summary.records:
        path = records_dir / f"{record['record_id']}.json"
        path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "manifest.json").write_text(
        json.dumps(summary.manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return out


# ── CLI ─────────────────────────────────────────────────────────────────────


def _parse_packs(raw: str) -> tuple[str, ...]:
    if raw == "all":
        return STATIC_PACKS
    packs = tuple(p.strip() for p in raw.split(",") if p.strip())
    for pack in packs:
        if pack not in PACK_NAMES:
            raise argparse.ArgumentTypeError(
                f"unknown pack {pack!r}; choose from {', '.join(PACK_NAMES)} or 'all'"
            )
    return packs


def _parse_seeds(raw: str) -> tuple[int, ...]:
    return tuple(int(s.strip()) for s in raw.split(",") if s.strip() != "")


def build_config_from_args(argv: list[str]) -> RunConfig:
    parser = argparse.ArgumentParser(prog="pi-benchmark-runner", description=__doc__)
    # Wire the parsers as argparse `type=` callables so a bad value produces a clean
    # usage error + SystemExit rather than an uncaught ArgumentTypeError.
    parser.add_argument("--pack", required=True, type=_parse_packs, help="canonical|spine|a2a|all or a comma list")
    parser.add_argument("--tier", required=True, choices=TIERS)
    parser.add_argument("--engine", required=True, choices=("pi", "legacy", "both"))
    parser.add_argument("--seeds", default=(0,), type=_parse_seeds, help="comma-separated integer seeds")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--phase", default="B1", choices=("B1", "B2", "B3", "B4"))
    parser.add_argument("--out", required=True, help="output run directory")
    parser.add_argument("--owner-gate", default=None, help="owner-gate artifact (required for T2/T3)")
    parser.add_argument("--dry-run", action="store_true", help="print the plan and exit without executing")
    ns = parser.parse_args(argv)

    engines = ENGINES if ns.engine == "both" else (ns.engine,)
    return RunConfig(
        packs=ns.pack,
        tier=ns.tier,
        engines=engines,
        seeds=ns.seeds,
        repeats=ns.repeats,
        phase=ns.phase,
        out_dir=Path(ns.out),
        owner_gate=Path(ns.owner_gate) if ns.owner_gate else None,
        dry_run=ns.dry_run,
    )


def main(argv: list[str] | None = None) -> int:
    config = build_config_from_args(argv if argv is not None else sys.argv[1:])
    scenarios = _resolve_scenarios(config.packs)
    if config.dry_run:
        print(f"[dry-run] phase={config.phase} tier={config.tier} engines={','.join(config.engines)}")
        print(f"[dry-run] packs={','.join(config.packs)} seeds={config.seeds} repeats={config.repeats}")
        print(f"[dry-run] scenarios={len(scenarios)} -> "
              f"{len(scenarios) * len(config.seeds) * config.repeats * len(config.engines)} records")
        print(f"[dry-run] out={config.out_dir}")
        return 0
    try:
        summary = run_benchmark(config)
    except OwnerGateRequired as exc:
        print(f"[refused] {exc}", file=sys.stderr)
        return 3
    out = write_run(summary)
    print(f"[ok] wrote {len(summary.records)} records to {out} (counts={summary.counts})")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
