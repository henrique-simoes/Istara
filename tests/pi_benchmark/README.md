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
  ledger) and never counts SSE chunks. A live run must explicitly set
  `ISTARA_LONG_HORIZON_ENGINE=legacy` or `pi`; its usage oracle requires every persisted
  `chat_turn` row in the requested session to carry that engine and the exact session
  handle, rather than trusting only the latest row or the request filter. (Legacy
  per-dispatch usage capture already exists via `AgenticDispatcher` /
  `usage_ledger.build_usage_row`, W1.)
- **B1-1** — `test_b1_contract.py` runs the canonical pack × both engines at T0 and T1 and
  asserts acceptance A5/A6. Baseline records materialise under `.results/runs/b1-*`.

## Delivered (B0/B1…B_N replan — DeepSeek-only live apparatus, PI-BENCH-MOA-20260722)

- **`scheduler.py`** — B0 offline scheduling: deterministic run-unit compilation
  (scenario × seed × repeat × engine × MoA mode), disjoint round-robin sharding, and the
  immutable, content-hashed wave manifest. Re-running B0 with identical arguments resumes
  the manifest unchanged; differing arguments refuse (`ManifestConflict`).
  `completed_unit_ids` drives crash-safe resume (only parseable, schema-valid records
  count as done).
- **`budget_ledger.py`** — crash-safe cumulative budget ledger (hard `$1.00` cap):
  append-only JSONL, exclusive `flock` around every read-modify-append, fsync per row,
  reserve-before-dispatch / commit-actual / release-only-pre-dispatch, `close()` seals.
- **`deepseek_provider.py`** — the provider-isolation gate: only `deepseek` /
  `deepseek-v4-pro` constructs; the key is read at runtime from env or macOS Keychain
  (`istara-pi-deepseek`/`openclaw`), held in memory only; unknown usage after dispatch
  fails closed with the reservation retained.
- **`live_driver.py`** — real T2/T3 execution through the Istara dispatcher path
  (`agentic.ensemble` / `validation.self_moa` / `validation.full_ensemble`), replacing
  the old synthetic T2/T3 records. Worst-case reservation before dispatch; actual cost
  committed after; provider-reported usage (`estimate=False`) or the documented
  `chars4` estimator (`estimate=True`); record identity follows the manifest unit.
- **`moa.py`** — Research Spine MoA routing validation: records requested mode/samples/
  temperatures, served routes, served model identities, coder count, response consensus,
  and reconciliation status; a full ensemble must have both the requested number of
  successful routes *and* distinct served model identities. Endpoint replicas of one model
  (or missing model identity evidence) are `model_identity_collapse` and therefore
  `not_runnable`, never a success. Any other downgrade (`full_ensemble→dual_run/self_moa`,
  partial coder, route diversity collapse, blocked) is also fail-closed. The recorded
  response consensus is explicitly not Fleiss' kappa: formal Research Spine reliability
  still requires the governed independent coding run with raw evidence units, grounding,
  reconciliation, and human-Done/report gates. `validate_topology` is a spend-free dry-run
  probe of the fail-closed route chain and does not by itself prove model independence.
- **`deepseek_judge.py`** — DeepSeek-backed `judge_fn` for the JudgeLayer. Under the
  DeepSeek-only policy the judge model equals the DUT model; separation is by role
  (`kind="judge"` calls, blind A/B, position swap, shared ledger — see
  `judge_config.json`'s `separation_note`). A malformed verdict fails, never a silent tie.
- **`verify_budget_ledger.py`** — B0-gate ledger verifier: replays the durable rows and
  proves known row types, no orphan commits, spend ≤ cap; `--close` seals the ledger.
- **runner additions** — `--plan-only` (B0: build units, shard into `--max-processes`
  shards, write the immutable manifest, print, exit; no dispatch), `--wave i`
  (execute one shard of the manifest with crash-safe resume), `--live` (explicit spend
  consent; without it T2/T3 print the plan and exit 0), provider/model rejection.

## To follow (owner-gated, tracked in the lifecycle file)

The report generator lives at `scripts/pi_benchmark_report.py`. Live B1…B_N wave
execution (real DeepSeek spend under the `$1.00` cap) is blocked behind owner gates
G1/G2 (live-model permission and budget approval) — the apparatus above is the
fail-closed path those waves run through.

## Verify

```bash
python -m pytest tests/pi_benchmark/ -q
```

Run records and manifests are written to `.results/` (gitignored). Only generated,
secret-scanned report bundles under `comparison-Istara-pi/reports/` are tracked.
