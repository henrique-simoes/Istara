"""Paired benchmark runner (task B0-4, master plan §10.3).

One paired runner, zero engine-specific scenarios: a single invocation executes
``scenario × seed × engine`` and emits one schema-conformant record per run, so pairing,
seeding, and fixture identity hold by construction rather than by convention (winning
plan §2.2 principle 1). Engine is a run-level parameter — the runner records the resolved
engine label on every record; the dispatcher header plumbing itself is proven by the node
harnesses (B0-2) and the dispatcher's own contract tests.

Tier discipline is enforced *here*, not by reviewer vigilance (winning plan §2.2
principle 3): ``--tier`` is mandatory and recorded on every record. T0/T1 execute an
offline, model-free contract driver. T2/T3 are fail-closed twice: behind the owner gate
(exit 3 without a gate artifact) and behind the explicit ``--live`` consent flag (without
it the runner prints the plan and exits 0 — no dispatch, no spend). With consent, T2/T3
execute for real through the Istara dispatcher path (DeepSeek ``deepseek-v4-pro`` only —
DEC-5 disables local routes; there is no local-model path) via
:mod:`tests.pi_benchmark.live_driver`, under a shared crash-safe budget ledger. Wave mode
(``--wave i --max-processes N --manifest M --budget-ledger L``) executes one shard of an
immutable Lane A manifest and skips units already recorded (crash-safe resume).
``--plan-only`` is the B0 scheduling gate: it builds the run units, shards them into
``--max-processes`` disjoint shards, writes the immutable content-hashed manifest, and
exits — fully offline, no dispatch, no spend.

Every record is validated against ``comparison-Istara-pi/metrics-schema.json`` (via
:mod:`tests.pi_benchmark.schema`) before it is written, so a run can never emit an
off-contract record. Records and manifests land under ``--out`` (kept in the gitignored
``.results/`` tree).

Import-safe at T0: importing this module touches no backend, DB, network, or model.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import importlib
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


class LiveConsentRequired(RuntimeError):
    """Raised when a T2/T3 run is attempted without the explicit --live consent flag."""


ONLY_PROVIDER = "deepseek"
ONLY_MODEL = "deepseek-v4-pro"
MOA_MODE_CHOICES = ("none", "self_moa", "full_ensemble")


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
    budget_usd: float = 1.00
    judge_config: Path | None = None
    memory_load: bool = False
    # Live/wave controls (T2/T3 only; inert at offline tiers).
    live: bool = False
    wave: int | None = None
    max_processes: int | None = None
    manifest: Path | None = None
    budget_ledger: Path | None = None
    provider: str = ONLY_PROVIDER
    model: str = ONLY_MODEL
    moa_mode: str = "none"
    moa_n: int = 3
    plan_only: bool = False

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
        if self.moa_mode not in MOA_MODE_CHOICES:
            raise ValueError(f"invalid moa_mode {self.moa_mode!r}")
        if self.moa_n < 1:
            raise ValueError("moa_n must be >= 1")
        if self.wave is not None and self.wave < 1:
            raise ValueError("wave must be >= 1 (1-based)")


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


# ── live (T2/T3) execution through the dispatcher path ──────────────────────


@dataclass(frozen=True)
class _LiveUnit:
    """Runner-synthesized unit mirroring Lane A's scheduler.RunUnit fields."""

    unit_id: str
    pack: str
    scenario_id: str
    seed: int
    repeat: int
    engine: str
    phase: str
    moa_mode: str | None = None


class LiveStackUnavailable(RuntimeError):
    """Raised when the Lane A live stack (ledger/provider/scheduler) is not importable."""


def _open_live_stack(config: RunConfig) -> tuple[Any, Any]:
    """Open the shared crash-safe ledger + the DeepSeek provider (lazy Lane A imports)."""
    # importlib (not `from pkg import mod`) so a sys.modules-injected fake is honored
    # even when the real submodule was previously imported and bound on the package.
    try:
        budget_ledger_mod = importlib.import_module("tests.pi_benchmark.budget_ledger")
        provider_mod = importlib.import_module("tests.pi_benchmark.deepseek_provider")
    except ImportError as exc:
        raise LiveStackUnavailable(
            f"the live stack is unavailable ({exc}); T2/T3 need Lane A's "
            "budget_ledger.py and deepseek_provider.py"
        ) from exc
    ledger_path = config.budget_ledger or (config.out_dir / "budget-ledger.json")
    ledger = budget_ledger_mod.BudgetLedger(ledger_path, cap_usd=config.budget_usd)
    provider = provider_mod.DeepSeekProvider(provider=config.provider, model=config.model)
    return ledger, provider


def _live_unit_id(config: RunConfig, scenario: Scenario, seed: int, repeat: int, engine: str) -> str:
    # Identical to build_record's record_id so the driver's <unit_id>.json and write_run's
    # <record_id>.json are the same file (resume sees both).
    return f"{config.phase}-{config.tier}-{scenario.pack}-{scenario.id}-seed{seed}-r{repeat}-{engine}"


def _scenario_for_unit(unit: Any) -> Scenario | None:
    try:
        for scenario in load_pack(unit.pack):
            if scenario.id == unit.scenario_id:
                return scenario
    except (KeyError, ValueError):
        return None
    return None


def _record_unknown_scenario(unit: Any, config: RunConfig, records_dir: Path) -> dict[str, Any]:
    """A unit whose scenario/pack doesn't resolve still gets a record (never dropped)."""
    from tests.pi_benchmark import live_driver

    known_packs = ("canonical", "spine", "a2a", "features", "probes")  # schema enum
    pack = unit.pack if unit.pack in known_packs else "canonical"
    scenario = Scenario(id=unit.scenario_id, title=unit.scenario_id, pack=pack)
    git_sha, git_dirty = git_provenance()
    # The unit's own phase (from the manifest) is the identity, not the CLI --phase.
    unit_config = config
    unit_phase = str(getattr(unit, "phase", "") or "")
    if unit_phase and unit_phase != config.phase:
        unit_config = dataclasses.replace(config, phase=unit_phase)
    record = build_record(
        config=unit_config, scenario=scenario, engine=unit.engine, seed=unit.seed,
        repeat=unit.repeat,
        pair_index=int(hashlib.sha256(unit.unit_id.encode()).hexdigest()[:8], 16),
        git_sha=git_sha, git_dirty=git_dirty, ts=_utc_now_iso(),
        status="not_runnable", not_runnable_reason="feature_unavailable",
        extensions={
            "unit_id": unit.unit_id,
            "detail": {"reason": f"unknown scenario {unit.scenario_id!r} in pack {unit.pack!r}"},
        },
    )
    live_driver._write_record_atomic(records_dir, unit.unit_id, record)
    return record


def _execute_live_units(
    *,
    config: RunConfig,
    units: list[tuple[Any, Scenario | None]],
    ledger: Any,
    provider: Any,
    dispatch: Any = None,
    wave: int | None = None,
) -> list[dict[str, Any]]:
    """Run units through the live driver; every unit yields exactly one record."""
    from tests.pi_benchmark import live_driver

    records_dir = config.out_dir / "records"
    kwargs: dict[str, Any] = {}
    if dispatch is not None:
        kwargs["dispatch"] = dispatch
    records: list[dict[str, Any]] = []
    for unit, scenario in units:
        if scenario is None:
            records.append(_record_unknown_scenario(unit, config, records_dir))
            continue
        records.append(live_driver.run_live_unit_sync(
            unit=unit, scenario=scenario, config=config, ledger=ledger, provider=provider,
            records_dir=records_dir, moa_n=config.moa_n, wave=wave, **kwargs,
        ))
    return records


def _run_live_benchmark(config: RunConfig, dispatch: Any = None) -> RunSummary:
    """Non-wave live run: every scenario x seed x repeat x engine, one process."""
    scenarios = _resolve_scenarios(config.packs)
    git_sha, git_dirty = git_provenance()
    ts = _utc_now_iso()
    moa_mode = None if config.moa_mode == "none" else config.moa_mode
    units: list[tuple[Any, Scenario | None]] = []
    for scenario in scenarios:
        for seed in config.seeds:
            for repeat in range(1, config.repeats + 1):
                for engine in config.engines:
                    unit = _LiveUnit(
                        unit_id=_live_unit_id(config, scenario, seed, repeat, engine),
                        pack=scenario.pack, scenario_id=scenario.id, seed=seed,
                        repeat=repeat, engine=engine, phase=config.phase, moa_mode=moa_mode,
                    )
                    units.append((unit, scenario))
    ledger, provider = _open_live_stack(config)
    records = _execute_live_units(
        config=config, units=units, ledger=ledger, provider=provider, dispatch=dispatch,
    )
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
        "total_cost_usd": round(ledger.spent_usd(), 7),
        "moa_mode": config.moa_mode,
        "live": True,
    }
    return RunSummary(config=config, records=records, manifest=manifest)


def _coerce_unit(raw: Any, *, manifest: dict[str, Any] | None = None) -> Any:
    """Coerce a manifest shard entry (RunUnit-shaped dict or object) into a unit.

    Lane A's ``write_manifest`` serializes shards as unit-id strings and stores the
    RunUnit-shaped fields in the manifest's ``units`` table. The runner resolves that
    on-disk representation before accepting the dataclasses.asdict shape or an object
    carrying those attributes.
    """
    if isinstance(raw, str):
        if manifest is None:
            raise TypeError("string manifest entries require the loaded manifest")
        details = manifest.get("units", {}).get(raw)
        if not isinstance(details, dict):
            raise ValueError(f"manifest shard references unknown unit {raw!r}")
        raw = {**details, "unit_id": raw}
    if isinstance(raw, dict):
        return _LiveUnit(
            unit_id=str(raw["unit_id"]), pack=str(raw["pack"]),
            scenario_id=str(raw["scenario_id"]), seed=int(raw["seed"]),
            repeat=int(raw["repeat"]), engine=str(raw["engine"]), phase=str(raw["phase"]),
            moa_mode=raw.get("moa_mode"),
        )
    return raw


def run_wave(config: RunConfig, dispatch: Any = None) -> tuple[int, list[dict[str, Any]]]:
    """Execute this process's shard of an immutable manifest (crash-safe, resumable).

    Returns ``(exit_code, records)``: exit 2 on a wave/config refusal, 0 otherwise. Units
    already recorded under ``records_dir`` are skipped (a repeated wave command produces
    no duplicate work); every remaining unit yields exactly one record.
    """
    try:
        # importlib honors a sys.modules-injected fake even when the real submodule is
        # already bound as an attribute on the tests.pi_benchmark package.
        scheduler = importlib.import_module("tests.pi_benchmark.scheduler")
    except ImportError as exc:
        print(f"[refused] wave mode needs Lane A's scheduler.py ({exc})", file=sys.stderr)
        return 2, []
    manifest = scheduler.load_manifest(config.manifest)
    shards = manifest.get("shards") or []
    if not (1 <= (config.wave or 0) <= len(shards)):
        print(
            f"[refused] wave {config.wave} out of range for {len(shards)} shard(s)",
            file=sys.stderr,
        )
        return 2, []

    records_dir = config.out_dir / "records"
    records_dir.mkdir(parents=True, exist_ok=True)
    completed = scheduler.completed_unit_ids(records_dir)
    # The manifest is the source of truth for cap/moa_n; the runner passes them through.
    wave_config = dataclasses.replace(
        config,
        budget_usd=float(manifest.get("budget_cap_usd") or config.budget_usd),
        moa_n=int(manifest.get("moa_n") or config.moa_n),
    )
    ledger, provider = _open_live_stack(wave_config)

    pending: list[tuple[Any, Scenario | None]] = []
    for raw in shards[config.wave - 1]:
        unit = _coerce_unit(raw, manifest=manifest)
        if unit.unit_id in completed:
            continue
        pending.append((unit, _scenario_for_unit(unit)))
    records = _execute_live_units(
        config=wave_config, units=pending, ledger=ledger, provider=provider,
        dispatch=dispatch, wave=config.wave,
    )
    skipped = len(shards[config.wave - 1]) - len(pending)
    print(
        f"[ok] wave {config.wave}/{len(shards)}: {len(records)} records "
        f"({skipped} already complete), spend=${ledger.spent_usd():.4f}"
    )
    return 0, records


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
    """Execute a benchmark run and return its records + manifest.

    The offline path writes nothing; the live (T2/T3) path writes each record atomically
    as it completes (crash-safe resume) and still returns the full summary."""
    if config.tier not in OFFLINE_TIERS:
        _enforce_owner_gate(config)
        if not config.live:
            raise LiveConsentRequired(
                f"tier {config.tier} executes live through the dispatcher and spends real "
                "budget; re-run with --live to consent (owner gates G1/G2)"
            )
        return _run_live_benchmark(config)

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
        "total_cost_usd": 0.0,
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
    parser.add_argument("--budget-usd", type=float, default=1.00, help="approved budget ceiling for live tiers in USD")
    parser.add_argument("--judge-config", default=None, help="path to judge configuration JSON file")
    parser.add_argument("--memory-load", action="store_true", help="enable RSS and cross-session memory load measurement")
    parser.add_argument("--live", action="store_true",
                        help="explicit consent for live dispatch + spend; without it T2/T3 print the plan and exit 0")
    parser.add_argument("--wave", type=int, default=None, help="process wave index (1-based) of an immutable manifest")
    parser.add_argument("--max-processes", type=int, default=None, help="total wave processes N (shard count)")
    parser.add_argument("--manifest", default=None, help="path to the Lane A run manifest (wave mode)")
    parser.add_argument("--budget-ledger", default=None, help="path to the shared crash-safe budget ledger")
    parser.add_argument("--provider", default=ONLY_PROVIDER, help="live provider (only 'deepseek' is approved)")
    parser.add_argument("--model", default=ONLY_MODEL, help="live model (only 'deepseek-v4-pro' is approved)")
    parser.add_argument("--moa-mode", default="none", choices=MOA_MODE_CHOICES,
                        help="MoA routing mode for live units (default none)")
    parser.add_argument("--moa-n", type=int, default=3, help="MoA samples (self_moa) / requested slots (full_ensemble)")
    parser.add_argument("--plan-only", action="store_true",
                        help="B0 offline scheduling: build run units, shard into --max-processes disjoint "
                             "shards, write the immutable manifest, print the plan, exit (no dispatch, no spend)")
    ns = parser.parse_args(argv)

    if ns.provider != ONLY_PROVIDER:
        parser.error(f"--provider must be {ONLY_PROVIDER!r} (DEC-5: DeepSeek is the only approved provider)")
    if ns.model != ONLY_MODEL:
        parser.error(f"--model must be {ONLY_MODEL!r} (DEC-5: deepseek-v4-pro is the only approved model)")
    if ns.plan_only and ns.max_processes is None:
        # B0 fails closed without an explicit, recorded process bound (acceptance A2).
        parser.error("--plan-only requires --max-processes N")
    if ns.plan_only and ns.wave is not None:
        parser.error("--plan-only (B0 scheduling) and --wave (execution) are mutually exclusive")
    if ns.wave is not None:
        for flag in ("--max-processes", "--manifest", "--budget-ledger"):
            if getattr(ns, flag.lstrip("-").replace("-", "_")) is None:
                parser.error(f"--wave requires {flag}")

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
        budget_usd=ns.budget_usd,
        judge_config=Path(ns.judge_config) if ns.judge_config else None,
        memory_load=ns.memory_load,
        live=ns.live,
        wave=ns.wave,
        max_processes=ns.max_processes,
        manifest=Path(ns.manifest) if ns.manifest else None,
        budget_ledger=Path(ns.budget_ledger) if ns.budget_ledger else None,
        provider=ns.provider,
        model=ns.model,
        moa_mode=ns.moa_mode,
        moa_n=ns.moa_n,
        plan_only=ns.plan_only,
    )


def _run_b0_plan_only(config: RunConfig) -> int:
    """B0 offline scheduling gate: build units, shard, write the immutable manifest.

    Purely offline — no dispatch, no spend, no backend import. Re-running with
    identical arguments resumes the existing manifest unchanged; differing
    arguments refuse (the B0 schedule is immutable once written).
    """
    try:
        scheduler = importlib.import_module("tests.pi_benchmark.scheduler")
    except ImportError as exc:
        print(f"[refused] B0 scheduling needs Lane A's scheduler.py ({exc})", file=sys.stderr)
        return 2
    scenarios = _resolve_scenarios(config.packs)
    moa_modes: tuple[str, ...] = () if config.moa_mode == "none" else (config.moa_mode,)
    units = scheduler.build_run_units(
        scenarios=scenarios, tier=config.tier, engines=config.engines,
        seeds=config.seeds, repeats=config.repeats, moa_modes=moa_modes,
    )
    try:
        shards = scheduler.shard_units(units, config.max_processes)
        manifest_path = config.manifest or (config.out_dir / "manifest.json")
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest = scheduler.write_manifest(
            manifest_path, max_processes=config.max_processes, provider=config.provider,
            model=config.model, budget_cap_usd=config.budget_usd, moa_n=config.moa_n,
            repeats=config.repeats, tier=config.tier, shards=shards,
        )
    except (scheduler.ManifestConflict, ValueError) as exc:
        print(f"[refused] {exc}", file=sys.stderr)
        return 2
    print(f"[plan] B0 schedule: {len(units)} unit(s) across {len(shards)} shard(s) "
          f"(max_processes={config.max_processes})")
    print(f"[plan] provider={config.provider} model={config.model} "
          f"budget_cap_usd={config.budget_usd:.2f} tier={config.tier} "
          f"moa_modes={moa_modes or ('none',)} moa_n={config.moa_n} repeats={config.repeats}")
    for index, shard in enumerate(shards, start=1):
        print(f"[plan]   wave {index}: {len(shard)} unit(s)")
    print(f"[plan] immutable manifest: {manifest_path} "
          f"(content_sha256={manifest['content_sha256'][:16]}...)")
    print("[plan] offline only: no dispatch, no spend")
    return 0


def _print_plan(config: RunConfig, scenarios: list[Scenario]) -> None:
    print(f"[plan] phase={config.phase} tier={config.tier} engines={','.join(config.engines)}")
    print(f"[plan] packs={','.join(config.packs)} seeds={config.seeds} repeats={config.repeats}")
    print(f"[plan] scenarios={len(scenarios)} -> "
          f"{len(scenarios) * len(config.seeds) * config.repeats * len(config.engines)} records")
    print(f"[plan] out={config.out_dir}")
    if config.tier not in OFFLINE_TIERS:
        print(f"[plan] live={config.live} provider={config.provider} model={config.model} "
              f"moa_mode={config.moa_mode} moa_n={config.moa_n} budget_usd={config.budget_usd}")
        if not config.live:
            print("[plan] no --live: no dispatch, no spend (pass --live to execute)")


def main(argv: list[str] | None = None) -> int:
    config = build_config_from_args(argv if argv is not None else sys.argv[1:])
    scenarios = _resolve_scenarios(config.packs)
    if config.plan_only:
        return _run_b0_plan_only(config)
    if config.dry_run:
        _print_plan(config, scenarios)
        return 0
    try:
        if config.wave is not None:
            _enforce_owner_gate(config)
            if not config.live:
                _print_plan(config, scenarios)
                return 0
            code, _records = run_wave(config)
            return code
        summary = run_benchmark(config)
    except OwnerGateRequired as exc:
        print(f"[refused] {exc}", file=sys.stderr)
        return 3
    except LiveConsentRequired as exc:
        print(f"[plan] {exc}")
        _print_plan(config, scenarios)
        return 0
    except LiveStackUnavailable as exc:
        print(f"[refused] {exc}", file=sys.stderr)
        return 2
    out = write_run(summary)
    print(f"[ok] wrote {len(summary.records)} records to {out} (counts={summary.counts})")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
