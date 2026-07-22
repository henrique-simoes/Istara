# tests/pi_benchmark — Pi vs Legacy benchmark apparatus

Implements the benchmark assets in master plan §10.3. Execution plan:
`docs/build-stream/2026-07-22-pi-benchmark.md`.

## Delivered (B0-1, schema-first foundation)

- **`schema.py`** — loads and validates run records against
  `comparison-Istara-pi/metrics-schema.json`. `validate_record()` is the one definition
  of "conforms to the schema" shared by every downstream asset. Import-safe at tier T0
  (no backend, DB, network, or model).
- **`fixtures/example_run_record.json`** — a canonical, schema-conformant record used by
  the tests and as living documentation of a run record's shape.
- **`test_metrics_schema.py`** — asserts the schema is a valid JSON Schema, the golden
  record validates, and a battery of malformed records is rejected (the acceptance-A1
  negative test).

## Delivered (B0-2 … B0-8, B1 — the offline asset layer)

- **`runner.py`** (B0-4) — the paired runner. One invocation executes
  `scenario × seed × engine` and emits one schema-validated record per run. `--tier` is
  mandatory; **T0/T1 run a fully offline, model-free contract driver**, and **T2/T3 are
  fail-closed behind the owner gate** (they refuse without a gate artifact and never load
  a model in this build). Importable for unit tests; also a CLI.
- **`scenarios/`** (B0-5) — pack registry. `canonical` re-hosts the 15 production-contract
  ids (read from `test_scenario_coverage_map.py` by an AST literal read, no import); its
  T0 contract check asserts each id still resolves to a real production test. `spine` and
  `a2a` are behavioural packs (`min_tier=T2`) recorded `not_runnable` at T0/T1, never
  dropped.
- **`feature_criteria.py`** (B0-6) — compiles `docs/features/inventory.json` (86 features)
  into per-feature axis-2 criteria; every feature is `auto` or counted `manual`, none
  skipped.
- **`judge.py`** (B0-7) — JudgeLayer: judge model must differ from every DUT, blind +
  deterministic position-swap, rubric bank, `(scenario, run, rubric_version, judge_model)`
  cache, `sha256`-logged prompts. The model call is injected, so the layer is unit-tested
  offline; a live judge is wired only behind gate G1.
- **`probes/`** (B0-8) — pure axis-9 scorers: protected-block survival, persona
  compliance, thinking-leak rate, adversarial injection resistance.
- **B0-2** — `--engine`/`--dry-run`/`--plan-only` plumbing in `tests/simulation/run.mjs`
  and `tests/real_user_benchmark/run.mjs`.
- **B0-3** — the `tests/benchmarks/long_horizon_runner.py` chunk-count-as-tokens bug is
  fixed: `extract_total_tokens()` reads provider-reported usage (or defers to the usage
  ledger) and never counts SSE chunks. (Legacy per-dispatch usage capture already exists
  via `AgenticDispatcher` / `usage_ledger.build_usage_row`, W1.)
- **B1-1** — `test_b1_contract.py` runs the canonical pack × both engines at T0 and T1 and
  asserts acceptance A5/A6. Baseline records materialise under `.results/runs/b1-*`.

## To follow (owner-gated, tracked in the lifecycle file)

The B2/B3/B4 execution phases and the live T2/T3 driver, JudgeLayer wiring, and the report
generator are blocked behind owner gates G1/G2 (live-model permission and budget approval).

## Verify

```bash
python -m pytest tests/pi_benchmark/ -q
```

Run records and manifests are written to `.results/` (gitignored). Only generated,
secret-scanned report bundles under `comparison-Istara-pi/reports/` are tracked.
