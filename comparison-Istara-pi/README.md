# comparison-Istara-pi — Pi vs Legacy benchmark deliverable

This directory holds the **generated** deliverables of the Pi-vs-Legacy benchmark program
(master plan §10; execution plan: `docs/build-stream/2026-07-22-pi-benchmark.md`).

## Contract

- **`metrics-schema.json`** — the run-record schema (benchmark task **B0-1**, the
  schema-first keystone). Every downstream asset validates against it: the paired runner
  (`tests/pi_benchmark/runner.py`), the feature-criteria compiler, the JudgeLayer, and the
  report generator (`scripts/pi_benchmark_report.py`). One record is emitted per
  `(scenario × seed × engine)` run; the two engine arms of a pair share `pair_id`.

- **`reports/<timestamp>/`** — generated report bundles (`report.md`, self-contained
  `report.html`, `scorecard.json`). Produced **only** by `scripts/pi_benchmark_report.py`
  from frozen JSON run records; hand-written numbers are forbidden and tested against. A
  dated copy of `report.md` is linked from this README **only after** the secret scan and
  reproducibility check pass.

## Hard rules (inherited from the plan and AGENTS.md)

- **Exact vs estimated tokens are never summed** in one column (schema `usage.estimate`;
  acceptance A15).
- **Tiers never mix** in a table (schema `tier`; acceptance A12).
- `not_runnable` / `invalid_pair` arms are **counted, never dropped** (schema `status`).
- Run records live under `tests/pi_benchmark/.results/` and are **gitignored**; only the
  generated, secret-scanned report bundles under `reports/` are tracked.
- The benchmark **observes** the product paths; it never flips `agentic_engine_default`,
  deletes the legacy engine, or promotes provisional research artifacts.

## Status

`metrics-schema.json` and this skeleton are the delivered **B0-1** foundation. The runner,
scenario packs, feature-criteria compiler, JudgeLayer, probes, engine-flag plumbing, and
report generator (B0-2…B0-8) and the B1–B4 execution phases are tracked as follow-up tasks
in the lifecycle file. No report bundle exists yet.

<!-- reports-index:start -->
_No report bundles generated yet._
<!-- reports-index:end -->
