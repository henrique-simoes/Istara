# Plan C — Execution plan: Pi vs Legacy benchmark program (B1–B4)

- **Task:** `pi-eval-REPLAN-C-r1` (consensus architect slot C, revision r1 — supersedes r0
  authored under `pi-eval-PLAN-C`; pipeline `pi-eval`)
- **Spec:** CF-SPEC-8 · **Lifecycle:** `docs/build-stream/2026-07-22-pi-benchmark.md`
- **Grounding:** master plan §10 (`docs/build-stream/plans/2026-07-20-pi-full-replacement-master-plan.md:685-797`), §5.5, §10.6, §13
- **Authored:** 2026-07-22 (r1), against branch `Review_pi_test` @ `e1c9c994`

> **r1 revision note.** Every §1 citation was re-verified at file:line on @ `e1c9c994`
> (command evidence on the CF task); no r0 factual errors found. Closed r0 residual risk:
> the master plan cites `metrics-schema.json:51-63,121-126` as if the file exists — a
> repo-wide `find` confirms no copy exists anywhere, so B0-1 is definitively an authoring
> task, not a discovery task. Remaining r0 residual risks stand unchanged: they are
> design-latitude disclosures (B0 phased explicitly vs folded into B1–B4; T2 wall-clock
> unknown until first runs; runner CLI / judge-config shape within §10.3 latitude; B1–B4
> sequenced as one post-W9 program per the lifecycle file's instruction), not defects.

- **Mission:** run the paired, industry-class B1–B4 benchmark of the Pi candidate engine
  against the legacy agentic engine, on the 10 owner axes, ending in the generated
  `comparison-Istara-pi/reports/<ts>/` deliverable set and the owner rollout review.

---

## 1. Verified current state (why the plan is shaped this way)

Verified by direct inspection on 2026-07-22 — these facts drive the design:

**Already in place (reuse, do not rebuild):**
- W0–W9 complete: `AgenticDispatcher` is the only product path; the legacy engine runs
  through the dispatcher's permanent legacy executor (`backend/app/core/agentic/legacy.py`),
  so `engine=legacy` behavior is preserved by construction. Ratchet is 0 product sites
  (`tests/pi_migration/legacy_allowlist.yaml:80`, `expected_product_sites: 0`).
- Engine selection works per-call, per-header, per-project, per-default
  (`backend/app/core/agentic/dispatcher.py:91-101`); the benchmark client header
  `x-istara-agent-engine` is already honored by
  `tests/real_user_benchmark/lib/api-client.mjs:31,244`.
- Usage ledger `backend/app/core/agentic/usage_ledger.py` exists (§5.5) with the
  `estimate` flag discipline for legacy provider-reported vs estimated tokens.
- Exactly 15 canonical Pi scenario ids are cataloged in
  `labs/pi-replacement/src/scenario-catalog.mjs` (top-level `id:` entries, verified count)
  and every id is contract-mapped to a production test by
  `tests/pi_production/test_scenario_coverage_map.py` (`COVERAGE` dict at `:21`;
  set-equality with the catalog asserted at `:63`).
- Deterministic output checks (`scripts/run_istara_evals.py:308-377`) and RAG gold
  precision@1/recall@3 (`scripts/run_istara_evals.py:538-558`) are reusable for axes 3/5.
- Tool vocabulary + eval metric ids exist in `tests/agentic_eval_contract.json:108-123`
  (`tool_calling_react` block: tool_name_accuracy, argument_schema_validity,
  multi_turn_recovery, evidence_chain_completeness) (axis 1).
- Skill phase enum (Double Diamond: discover/define/develop/deliver) at
  `backend/app/skills/base.py:10-16` (axis 8); protected-block machinery at
  `backend/app/api/routes/chat.py:52,248` with protected-compression telemetry at
  `:690-716` (axis 9); production Fleiss kappa at `backend/app/core/consensus.py:36`
  (axis 10).
- T3 pricing table for dry-run estimates: `labs/pi-replacement/src/raw-llm-capture.mjs:5-10`.
- `docs/features/inventory.json` (86 features) is present for the axis-2 feature matrix.

**Verified missing (must be built — this is the bulk of the work):**
- `tests/pi_benchmark/` — does not exist (runner, scenario packs, feature compiler,
  judge, probes are all §10.3 assets still to create).
- `comparison-Istara-pi/` — does not exist, including `metrics-schema.json`, which the
  master plan already cites as the contract (`metrics-schema.json:51-63,121-126`); a
  repo-wide `find` (2026-07-22, excluding `node_modules`/`.venv`/`.git`) confirms no copy
  exists anywhere, so this is an authoring task, not a discovery task.
- `scripts/pi_benchmark_report.py` — does not exist.
- `--engine` plumbing in `tests/simulation/run.mjs` and `tests/real_user_benchmark/run.mjs`
  — both parse args by hand and ignore the engine flag (the §10.1 "verified gap").
- Legacy per-step usage capture in the registry `chat/chat_stream` path, and the
  `tests/benchmarks/long_horizon_runner.py:138` chunk-count-as-tokens bug (verified:
  `total_tokens += 1` per streamed SSE chunk at exactly `:138`).

**Hard gates that shape sequencing:**
- AGENTS.md live-LLM rule + master plan §13.2: no live model loading (T2 local, T3 API)
  without explicit owner permission. T0/T1 need no models.
- §10.6: T3 requires a dry-run cost estimate + explicit in-chat owner budget approval,
  recorded as CF evidence, before any spend ($0.409 remaining of the historical envelope
  is NOT sufficient).
- Any LLM-provider/registry telemetry edit runs
  `python scripts/security_benchmark.py --fail-on-threshold` (AGENTS.md security gate).

## 2. Design

### 2.1 Program shape

Five phases, strictly sequential, each fail-closed before the next starts:

```
B0 assets ──► B1 contract (T0/T1) ──► B2 breadth (T2) ──► B3 depth (T2 high-N + T3) ──► B4 report
   build        both engines,          N≥5, full packs,     spine+A2A+memory,            generated
   §10.3        deterministic          feature matrix       owner-gated spend            report set
```

The master plan's phase table gated B1 "after W2" etc. as wave regression gates; with all
waves done, B1–B4 run as one program and B1 additionally serves as the smoke gate that the
B0 assets are correct before any owner-gated spend is requested.

### 2.2 Design principles (chosen to make bias structurally hard)

1. **One paired runner, zero engine-specific scenarios.** Scenarios are engine-agnostic
   definitions; engine is a *run-level* parameter injected through the dispatcher header /
   per-call `engine=` override. A single invocation of the runner executes
   `scenario × seed × {pi, legacy}` and emits one schema-conformant record per run, so
   pairing, seeding, and fixture-identity hold by construction rather than by convention.
2. **Schema-first.** `comparison-Istara-pi/metrics-schema.json` is task B0-1: every later
   asset (runner, judge, feature compiler, report) validates against it. The master plan
   already cites its reserved sections; writing it first turns those citations into an
   executable contract.
3. **Tier discipline enforced by the runner CLI, not by reviewer vigilance.**
   `--tier T0|T1|T2|T3` is mandatory, recorded on every record, and the report generator
   asserts no table mixes tiers (§10.1.2). T0/T1 never touch a model; T2/T3 are only
   reachable behind the owner gates.
4. **Reuse the production scenario contract for B1.** The canonical pack re-hosts the 15
   catalog ids at route level; `test_scenario_coverage_map.py` already guarantees each id
   resolves to a real production test, so B1 measures the shipped behavior, not a parallel
   lab fiction.
5. **Judges are never the DUT and never re-spend.** JudgeLayer config (owner-set model,
   rubric versions) lives in one file; every judgment logs sha256(prompt+rubric); blind
   engine labels, position-swapped A/B; cache keyed by
   `(scenario, run, rubric_version, judge_model)` so B4 re-reports cost nothing (§10.1.3).
6. **Exact-or-estimated tokens, always flagged.** Pi rows come exact from the ledger;
   legacy rows come provider-reported where available, else `estimate=true`. The report
   renders exact and estimated numbers in separate columns (§10.1.4, §5.5).
7. **Fail-closed everywhere.** A scenario that cannot run on an engine is recorded as
   `not_runnable` with a machine-readable reason and counted in the report — never dropped
   (§10.1.6). Every run dir carries a manifest (git sha, input sha256, redacted endpoint
   fingerprints); results dirs are gitignored; a secret scan precedes any README link
   (§10.6).
8. **Minimal backend footprint.** Exactly two backend edits in the whole program, both
   telemetry-additive: legacy usage capture in registry `chat/chat_stream`, and the
   `long_horizon_runner.py:138` fix. No behavior change, no allowlist change, donor plane
   untouched.

### 2.3 Component design

- **`comparison-Istara-pi/metrics-schema.json`** — run-record schema: identity
  (scenario id, pack, engine, tier, seed, git sha, model id, ts), the §10.2 axis metric
  blocks (tool calling; per-feature `criteria_scores`; output quality; spine-phase scores;
  memory load; token/cost with `estimate` flags; tool-efficiency; skills; prompt
  adherence; A2A), paired-statistics fields (per-scenario delta, bootstrap CI, effect
  size), and the `not_runnable` reason enum.
- **`tests/pi_benchmark/runner.py`** — CLI:
  `--pack canonical|spine|a2a|features|probes --tier <T> --engine pi|legacy|both
  --seeds <csv> --repeats N --out <dir> [--dry-run]`. Drives real ASGI routes with the
  engine header, orchestrates seeded repetitions (default N≥5 for T2), samples worker/
  backend RSS via psutil per run, emits one record per run plus a run manifest into
  `tests/pi_benchmark/.results/runs/<ts>/` (gitignored, secret-scanned).
- **`tests/pi_benchmark/scenarios/`** — three packs: `canonical/` (15 ids re-hosted
  route-level from the scenario catalog), `spine/` (full task lifecycle backlog→review on
  a pinned subset of `tests/document_corpus/canonical/`), `a2a/` (collaboration, debate,
  delegation chains). Each scenario declares its tier eligibility and deterministic checks.
- **`tests/pi_benchmark/feature_criteria.py`** — compiles `docs/features/inventory.json`
  (86 features) into executable criteria: route reachable, project-scope enforced,
  expected-action smoke, evidence rows present, graceful-failure probe. Underivable
  features get explicit `criteria: manual` entries, counted and reported (§10.3).
- **`tests/pi_benchmark/judge.py`** — JudgeLayer per §10.3: owner-set judge model
  (≠ any DUT model), blind + position-swapped protocol, rubric bank per axis,
  sha256-logged prompts/rubrics, cache by `(scenario, run, rubric_version, judge_model)`.
- **`tests/pi_benchmark/probes/`** — system-prompt adherence + injection suite: protected
  spine-contract block survival (`backend/app/api/routes/chat.py:52,248` protected-block
  region), persona-constraint compliance, adversarial injection (reusing
  security_benchmark patterns), thinking-leak rate.
- **Engine-flag plumbing** — `--engine pi|legacy|both` in `tests/simulation/run.mjs` and
  `tests/real_user_benchmark/run.mjs`, threaded to the existing api-client header support;
  plus a `--dry-run`/plan-only mode so plumbing is verifiable without starting services.
- **Legacy usage capture** — registry `chat/chat_stream` records provider-reported usage
  into `usage_ledger.py` (telemetry-additive); `long_horizon_runner.py:138` reads the
  ledger instead of counting chunks.
- **`scripts/pi_benchmark_report.py`** — reads `.results/runs/` records + judge cache,
  computes paired per-scenario deltas with 10k-resample bootstrap 95% CIs and effect
  sizes, and emits `comparison-Istara-pi/reports/<ts>/`:
  `report.md` (methodology, per-axis tables with CIs, efficiency frontiers, feature
  matrix, capability-diff table, threats to validity, raw-artifact index), `report.html`
  (self-contained single file, inline CSS/JS/SVG: executive verdict, axis scorecards,
  drill-downs, token/cost dashboards, spine-phase heatmap, A2A dominance plot),
  `scorecard.json` (machine-readable roll-up of the 10 axes). Every number generated from
  JSON — hand-written numbers are forbidden and tested against.

## 3. Task breakdown

Estimates: S < half day, M ≈ 1 day, L ≈ 2–3 days (agent execution, T2/T3 wall-clock excluded).

| # | Task | Files (primary) | Depends on | Est |
|---|------|-----------------|-----------|-----|
| B0-1 | metrics-schema.json + `comparison-Istara-pi/` skeleton (README, `reports/`, gitignore rules) | `comparison-Istara-pi/metrics-schema.json` | — | S |
| B0-2 | `--engine` + `--dry-run` plumbing in both node harnesses | `tests/simulation/run.mjs`, `tests/real_user_benchmark/run.mjs` | — | S |
| B0-3 | Legacy usage capture + long-horizon token fix | `backend/app/core/compute_registry_invocation.py` (telemetry only), `tests/benchmarks/long_horizon_runner.py` | — | S |
| B0-4 | Paired runner core (CLI, ASGI driver, seed/repeat orchestration, manifest, RSS sampler, schema validation) | `tests/pi_benchmark/runner.py` | B0-1 | L |
| B0-5 | Canonical + spine + A2A scenario packs | `tests/pi_benchmark/scenarios/` | B0-4 | L |
| B0-6 | Feature-criteria compiler over inventory.json | `tests/pi_benchmark/feature_criteria.py` | B0-1, B0-4 | M |
| B0-7 | JudgeLayer (config, blind A/B, rubric bank, cache, sha256 logging) | `tests/pi_benchmark/judge.py` | B0-1 | M |
| B0-8 | System-prompt adherence + injection probes | `tests/pi_benchmark/probes/` | B0-4 | M |
| B1-1 | Run B1 contract: canonical pack + W2-surface checks, T0 and T1, both engines; publish regression baseline | `.results/runs/b1-*` | B0-2..B0-5 | S |
| B2-1 | **Owner gate G1** (judge + T2 model policy, live-model permission); then B2 T2 runs: all packs + feature matrix + probes, N≥5, both engines | `.results/runs/b2-*` | B1-1, G1 | M |
| B2-2 | First full report generation on B2 data (exercises B4 pipeline early) | `comparison-Istara-pi/reports/<ts>/` | B2-1, B0-7 | S |
| B3-1 | B3 T2 high-N: spine pack end-to-end, A2A pack, memory-load runs (incl. cross-session recall probe) | `.results/runs/b3-t2-*` | B2-1 | M |
| B3-2 | **Owner gate G2**: T3 dry-run cost estimate (T2 rehearsal token counts × `raw-llm-capture.mjs:5-10` pricing), presented in chat, explicit approval recorded as CF evidence | CF evidence row | B3-1 | S |
| B3-3 | B3 T3 low-N paired runs within the approved envelope; per-run cost ceilings enforced by ledger | `.results/runs/b3-t3-*` | B3-2 | M |
| B4-1 | Final report: all runs → `report.md`/`report.html`/`scorecard.json`, secret scan, dated copy linked from `comparison-Istara-pi/README.md` | `scripts/pi_benchmark_report.py`, `comparison-Istara-pi/` | B3-3 | M |
| B4-2 | Article results sections auto-generated into `comparison-Istara-pi/article/`; owner rollout review packet (§13.4 gate G3, decision itself is out of scope) | `comparison-Istara-pi/article/` | B4-1 | S |

Suggested CF roles: one implementer role for B0 (`pi-eval-implementer`), reviewer per wave,
owner gates executed by the conductor pausing the pipeline.

## 4. Acceptance criteria

**B0 (assets):**
- A1 `metrics-schema.json` validates; runner/judge/feature-compiler unit tests pass and
  reject a schema-violating record (negative test).
- A2 `node tests/simulation/run.mjs --engine pi --scenario 05-chat-interaction --dry-run`
  and the legacy/both variants exit 0 and print the resolved engine header; same for
  `tests/real_user_benchmark/run.mjs --engine both --plan-only`.
- A3 Legacy registry capture: a unit test shows a `chat_stream` call writes a usage-ledger
  row with provider-reported tokens and `estimate=false`; long_horizon_runner reads the
  ledger (test fails on the old chunk-count behavior).
- A4 No product-code behavior change: `python -m pytest tests/pi_migration/test_count_to_zero.py -q`
  stays green (ratchet 0); `python -m pytest tests/pi_production/ -q` stays green.

**B1 (contract):**
- A5 All 15 canonical scenarios × both engines × T0 and T1 produce schema-valid records;
  0 `not_runnable` without a filed reason; deterministic outcome classes match across
  repeats of the same seed.
- A6 B1 results are published as the regression baseline manifest referenced by B2/B3.

**B2 (breadth):**
- A7 G1 owner approval recorded as CF evidence *before* the first T2 run.
- A8 Full packs + 86-feature matrix + probes ran at N≥5 per scenario per engine at T2;
  every feature is either auto-scored or counted `criteria: manual`.
- A9 First full report generates from B2 data with zero hand-written numbers (test:
  every numeric cell in `report.md` traces to `scorecard.json`).

**B3 (depth):**
- A10 Spine pack end-to-end, A2A pack, and memory-load runs complete at T2 high-N with
  paired bootstrap CIs computed per scenario.
- A11 G2: dry-run T3 estimate presented in chat and explicit owner approval recorded as CF
  evidence *before* any T3 call; judge spend counted in the same envelope; per-run cost
  ceilings enforced (a run that would exceed the ceiling aborts `budget_exceeded`, not
  silently overruns).
- A12 T3 tier records never mix into T2 tables (report-level assert).

**B4 (report):**
- A13 `comparison-Istara-pi/reports/<ts>/` contains `report.md`, `report.html`
  (self-contained: zero external asset references — tested), `scorecard.json`; a dated
  `report.md` copy is linked from `comparison-Istara-pi/README.md` only after the secret
  scan passes.
- A14 Report is reproducible: two invocations over the same runs dir produce byte-identical
  `scorecard.json` and identical `report.md` modulo the timestamp header.
- A15 Exact vs estimated tokens are never summed in one column anywhere in the report.

## 5. Verification (exact commands)

Asset/wave gates (T0/T1, no live models — safe at will):

```bash
# schema + unit suites for new assets (created in B0, extended per wave)
python -m pytest tests/pi_benchmark/ -q
# ratchet + existing production ladder must stay green after B0-3 backend edits
python -m pytest tests/pi_migration/test_count_to_zero.py -q
python -m pytest tests/pi_production/ -q
# deterministic eval reuse for axes 3/5 (no --require-live-llm)
python scripts/run_istara_evals.py --output-dir tests/pi_benchmark/.results/evals
# engine plumbing (dry-run, starts nothing)
node tests/simulation/run.mjs --engine pi --scenario 05-chat-interaction --dry-run
node tests/simulation/run.mjs --engine legacy --scenario 05-chat-interaction --dry-run
node tests/real_user_benchmark/run.mjs --engine both --plan-only
# security gate for the registry telemetry edit (AGENTS.md)
python scripts/security_benchmark.py --fail-on-threshold
```

B1 execution:

```bash
python tests/pi_benchmark/runner.py --pack canonical --tier T0 --engine both --repeats 3 \
  --out tests/pi_benchmark/.results/runs/b1-t0
python tests/pi_benchmark/runner.py --pack canonical --tier T1 --engine both --repeats 3 \
  --out tests/pi_benchmark/.results/runs/b1-t1
```

B2/B3 execution (each only after its owner gate):

```bash
python tests/pi_benchmark/runner.py --pack all --tier T2 --engine both --repeats 5 \
  --judge-config tests/pi_benchmark/judge_config.json --out tests/pi_benchmark/.results/runs/b2-t2
python tests/pi_benchmark/runner.py --pack spine,a2a --tier T2 --engine both --repeats 10 \
  --memory-load --out tests/pi_benchmark/.results/runs/b3-t2
python tests/pi_benchmark/runner.py --pack canonical,spine --tier T3 --engine both --repeats 3 \
  --budget-usd <approved-envelope> --out tests/pi_benchmark/.results/runs/b3-t3
```

B4 + reproducibility + hygiene:

```bash
python scripts/pi_benchmark_report.py --runs tests/pi_benchmark/.results/runs \
  --out comparison-Istara-pi/reports/$(date -u +%Y%m%dT%H%M%SZ)
python scripts/pi_benchmark_report.py --runs tests/pi_benchmark/.results/runs --out /tmp/pi-rerun \
  && diff <(jq -S . comparison-Istara-pi/reports/<ts>/scorecard.json) <(jq -S . /tmp/pi-rerun/scorecard.json)
python scripts/check_public_tree_clean.py   # or the repo's secret-scan equivalent, over the report dir
```

Every executed command is recorded as CF `command` evidence on the owning task; owner
approvals (G1/G2) are recorded as CF evidence with the in-chat approval quoted.

## 6. Risks and mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Scope creep: "run benchmarks" read as "skip missing assets" | High | This plan makes B0 explicit; B1 acceptance (A5) is impossible without the runner+packs, so the gap cannot be silently skipped. |
| Legacy/engine behavioral drift during B0-3 edit | Low | Telemetry-additive only; ratchet test + full pi_production suite green (A4); security benchmark gate. |
| Tier mixing contaminates tables | Medium | Tier is a mandatory runner arg recorded per record; report asserts single-tier tables (A12); schema rejects missing tier. |
| Judge = DUT or judge bias | Medium | Judge config owner-set (G1), must differ from DUT models; blind labels, position swap, sha256-logged rubrics, deterministic checks always computed alongside (§10.1.3). |
| Unapproved live-model load or spend | Medium | T2/T3 unreachable without G1/G2 CF evidence rows; runner refuses `--tier T2/T3` without the gate artifact; budget ceiling enforced per run (A11). |
| Estimated vs exact tokens silently mixed | Medium | `estimate` flag in schema; report renders separate columns; A15 test scans generated tables. |
| Non-determinism leaks (timestamps, git sha) breaking reproducibility | Medium | A14 byte-identity check on scorecard.json; report normalizes volatile fields. |
| T2 local-model throughput makes N≥5 slow | Medium | T2 runs are free and resumable: runner writes per-run records incrementally, so interrupted runs resume without re-spending completed runs. |
| Feature inventory drift (86 → N) between plan and B2 | Low | feature_criteria compiles from `inventory.json` at run time; manual-criteria count is reported, so drift is visible, never silent. |
| Corpus/fixture drift between engines | Low | Runner hashes inputs into the manifest (input sha256); a pair with mismatched hashes is `invalid_pair`, not compared. |
| Flaky ASGI startup in runner | Low | Runner reuses the existing harness service-boot discipline from real_user_benchmark; startup failure is `not_runnable` with logs, retried once, then counted. |
| Report hand-edits after generation | Low | A9/A14 tests; README links only the dated generated copy. |

## 7. Rollback

- **B0 assets:** all new files under `tests/pi_benchmark/` and `comparison-Istara-pi/`
  are additive — delete the directories to roll back. Results dirs are gitignored; nothing
  user-facing changes.
- **B0-2 plumbing:** flag parsing is additive; revert the single commit per harness.
  Without the flag, both harnesses behave exactly as today.
- **B0-3 backend edits:** one revert commit restores the registry to no-capture and the
  runner to its previous (buggy but harmless outside benchmarks) behavior. No schema
  migrations, no settings changes, no allowlist edits involved.
- **B1–B3 runs:** produce only gitignored `.results/` artifacts; "rollback" is deleting a
  runs dir. A failed gate never mutates product code.
- **B4:** reports are additive artifacts; un-linking the README line reverts publication.
- **Engine state:** `agentic_engine_default` stays `legacy` throughout the program; the
  rollout flip is a post-B4 owner decision (§13.4) explicitly outside this plan. The
  benchmark itself never changes which engine serves production traffic.

## 8. Owner gates summary (blocking, in order)

- **G1 (before B2):** judge model + T2 local model policy + explicit live-model-load
  permission (master plan §13.2; AGENTS.md live-LLM rule).
- **G2 (before B3 T3):** dry-run T3 cost estimate presented in chat; explicit approved
  envelope recorded as CF evidence; judge spend inside the same envelope (§10.6, §13.3).
- **G3 (after B4):** rollout decision review — presented with the report packet; the
  decision and any `agentic_engine_default` flip are out of scope here.

## 9. Explicit non-goals

- No rollout/engine-default flip, no legacy deletion (§13.4: a NEW spec if Pi wins).
- No changes to the donor/Petals permanent allowlist plane.
- No new product features; benchmark findings become new CF tasks, not in-scope fixes.
- No live model loading or external spend before the corresponding owner gate.
