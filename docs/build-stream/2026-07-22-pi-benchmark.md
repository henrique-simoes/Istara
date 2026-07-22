# Build Stream Lifecycle — Pi Benchmark Experimentation

<!-- STATUS BLOCK -->
```yaml
item: pi-benchmark
branch: Review_pi_test
cf: { spec: CF-SPEC-8 }
phase: "Execution phase"
stage: S2-execute
status: in-progress
blocked_on: "none"
authored_by: henrique-simoes
grounding: "Based on 2026-07-20-pi-full-replacement-master-plan.md Section 10"
last: {agent: claude-opus-4-8, at: 2026-07-22T15:22:53Z, ledger: L-10}
next_action: "Independent code review of pi-eval-IMPL (B0-1 schema foundation); then follow-up implementer tasks for B0-2..B0-8 and owner-gated B1-B4 execution"
```
<!-- /STATUS BLOCK -->

## Context
We have completed all 9 waves of the Pi candidate replacement (W0 through W9). The next and final step is to conduct a professional, industry-class paired experiment (B1 through B4) evaluating the Pi candidate against the original Istara React and agentic loops.

## Goals
1. Execute the B1 contract tests.
2. Execute the B2 breadth tier 2 tests.
3. Execute the B3 depth tier 2 and tier 3 tests.
4. Generate the final B4 report in comparison-Istara-pi/reports/.
5. Ensure exact or estimated tokens are flagged properly.

## Instructions
Review Section 10 of docs/build-stream/plans/2026-07-20-pi-full-replacement-master-plan.md for the exact benchmark rules.
Create a step-by-step plan for running all benchmarks, collecting the results, and generating the report.

### L-1 | 2026-07-22T10:25:00Z | S1-plan | human | creator
Did: created lifecycle file   Result: ok   Verified: N/A   Next: architects plan

### L-2 | 2026-07-22T13:33:17Z | S1-plan | claude-fable-5 | architect | Planning phase <!-- bsc-ledger:pi-eval-PLAN-A -->
Did: authored independent consensus plan A at docs/build-stream/plans/pi-eval-plan-a.md (design, E0 asset-build wave, E1-E4 = B1-B4 execution waves, acceptance A1-A5 + per-phase, exact verification commands, risks R1-R9, layered rollback)
Result: plan slot A ready for consensus judging; key finding: S10.3 assets (tests/pi_benchmark/, metrics-schema.json, pi_benchmark_report.py, comparison-Istara-pi/, --engine plumbing) do not exist yet, so plan front-loads build wave E0; pi-eval-PLAN-A
Verified: ls/grep gap audit (tests/pi_benchmark absent, --engine unplumbed in both run.mjs, header support present api-client.mjs:31,244); evidence rows 1222-1224 on CF task
Next: consensus judges vote on plan slots a/b/c

### L-3 | 2026-07-22T13:33:48Z | S1-plan | gpt-5.6-sol | planner | pi-eval-architect-b <!-- bsc-ledger:pi-eval-PLAN-B -->
Did: pi-eval-architect-b stage on task pi-eval-PLAN-B (harness fallback entry; the model did not append one).
Result: task pi-eval-PLAN-B finished; worktree head ccf1680e.
Verified: see Compass Forge evidence rows on pi-eval-PLAN-B (command + self_report + stage_attribution).
Next: conductor advances the pipeline on evidence.

### L-4 | 2026-07-22T13:38:20Z | S1-plan | claude-fable-5 | architect | Planning phase <!-- bsc-ledger:pi-eval-REPLAN-A-r1 -->
Did: repaired consensus plan A (revision r1) at docs/build-stream/plans/pi-eval-plan-a.md — closed all three r0 residual risks with verified evidence; extended ground-truth table (axis-1 vocab in tests/agentic_eval_contract.json; pricing table labs/pi-replacement/src/raw-llm-capture.mjs:5-10; chunk-count tokens bug tests/benchmarks/long_horizon_runner.py:138); E0.8/E3.2 now cite exact file:line
Result: plan slot A ready for consensus judging (r1); metrics-schema.json confirmed absent repo-wide so E0.1 is definitively an authoring task; pi-eval-REPLAN-A-r1
Verified: ls/find/grep grounding audit (assets absent, vocab present, bug located at :138, engine header intact api-client.mjs:31,244); wc -l plan = 253 lines; CF evidence rows 1233,1235,1236
Next: consensus judges vote on plan slots a/b/c

### L-5 | 2026-07-22T13:39:18Z | S1-plan | kimi-code/k3 | planner | pi-eval-architect-c <!-- bsc-ledger:pi-eval-PLAN-C -->
Did: pi-eval-architect-c stage on task pi-eval-PLAN-C (harness fallback entry; the model did not append one).
Result: task pi-eval-PLAN-C finished; worktree head 4f1fe8ca.
Verified: see Compass Forge evidence rows on pi-eval-PLAN-C (command + self_report + stage_attribution).
Next: conductor advances the pipeline on evidence.

### L-6 | 2026-07-22T13:41:52Z | S1-plan | claude-fable-5 | reviewer | Planning phase <!-- bsc-ledger:pi-eval-JUDGE-A -->
Did: consensus judge slot a — read candidate plans docs/build-stream/plans/pi-eval-plan-b.md and pi-eval-plan-c.md; spot-checked both plans' repo-grounding claims (missing benchmark assets confirmed absent; cited existing assets incl. api-client.mjs:31 engine header, usage ledger, pricing table, long_horizon_runner chunk-count bug all confirmed present). No plan edited.
Result: plan_vote recorded for slot c (execution-readiness: verified file:line grounding, dependency-ordered task table B0-1..B4-2 with A1-A15 acceptance, per-component rollback, owner gates G1-G3); noted B's order-alternation + immutable-manifest strengths for the implementer to fold in; pi-eval-JUDGE-A
Verified: ls/grep grounding audit (passed; CF evidence 1242); plan_vote evidence 1243; self_report evidence 1244
Next: remaining consensus judges vote; conductor tallies consensus_result

### L-7 | 2026-07-22T13:43:30Z | S1-plan | gpt-5.6-sol | reviewer | Planning phase <!-- bsc-ledger:pi-eval-JUDGE-B -->
Did: Compared exactly candidate plans A (`claude-fable-5`) and C (`kimi-code/k3`); edited only this lifecycle file.
Result: Voted for slot `c` on `pi-eval-JUDGE-B`; C has the stronger schema placement, explicit T2 live-model owner gate, and mandated security benchmark. Recorded residual risk that a T2-only B4 path is needed if T3 spend is declined.
Verified: `sha256sum docs/build-stream/plans/pi-eval-plan-a.md docs/build-stream/plans/pi-eval-plan-c.md` passed (A `8932b5ed16c6062551587e6045df1f4279d74f3945857bf6568ca682aaa17b50`; C `90c7b0c2fb68b5c2474aec386565de7f0bcef8f270b5991aedb82c0245816c5f`); CF command evidence `1247`, plan vote `1248`, self-report `1249` recorded.
Next: stage exit: consensus judge B vote recorded; conductor should tally after remaining judges vote.

### L-8 | 2026-07-22T13:45:25Z | S1-plan | kimi-code/k3 | judge | Planning phase <!-- bsc-ledger:pi-eval-JUDGE-C -->
Did: consensus judge slot c - read both candidate plans (pi-eval-plan-a.md r1, pi-eval-plan-b.md), spot-verified plan A grounding claims in-tree, recorded plan_vote for slot a
Result: vote a recorded (CF evidence rows 1250 command, 1251 plan_vote, 1252 self_report); pi-eval-JUDGE-C
Verified: ls/grep/sed grounding audit all pass - benchmark assets absent; long_horizon_runner.py:138 total_tokens += 1 per chunk; api-client.mjs:31,244 engine header; run.mjs harnesses unplumbed; raw-llm-capture.mjs:5-10 pricing table
Next: conductor tallies judge plan_votes (a/b/c) and advances the pipeline


<!-- consensus-winning-plan -->
## Winning consensus plan

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

## Decision log


### L-9 | 2026-07-22T13:50:34Z | S1-plan | kimi-code/k3 | architect | Planning phase <!-- bsc-ledger:pi-eval-REPLAN-C-r1 -->
Did: repaired consensus plan C (revision r1)
Result: plan slot C ready for consensus judging (r1)
Verified: ls/find/grep/sed grounding audit
Next: consensus judges vote on plan slots a/b/c

### L-10 | 2026-07-22T15:22:53Z | S2-execute | claude-opus-4-8 | executor | Execution phase <!-- bsc-ledger:pi-eval-IMPL -->
Did: implemented winning-plan task **B0-1 (schema-first foundation)** — the keystone every downstream benchmark asset validates against. Added `comparison-Istara-pi/metrics-schema.json` (Draft-2020-12 run-record contract: identity, tier/engine/pack/phase, provenance with redacted fingerprint + sha256, `usage` with mandatory `estimate` flag, the 10 owner-axis metric blocks, `$defs.feature_criteria_scores` and `$defs.paired_stats`, `not_runnable_reason` enum, `if/then` requiring a reason when `status=not_runnable`), `comparison-Istara-pi/README.md` + `reports/.gitkeep` skeleton, and `tests/pi_benchmark/` package (`schema.py` loader/validator — T0-safe, no backend/DB/net/model; golden `fixtures/example_run_record.json`; `test_metrics_schema.py` with the acceptance-A1 negative battery; `.gitignore` for `.results/`; README). No product-code touched — purely additive.
Result: 20/20 unit tests pass; schema is a valid JSON Schema; acceptance A1 (validates conformant record, rejects schema-violating records) foundation met for B0. Delivered B0-1 only; B0-2..B0-8 and B1-B4 remain follow-ups (B0-3 security-sensitive; B2/B3 owner-gated G1/G2). pi-eval-IMPL
Verified: `python -m pytest tests/pi_benchmark/ -q` → 20 passed; `python -m json.tool comparison-Istara-pi/metrics-schema.json` → parses OK; `python -m pytest tests/pi_migration/test_count_to_zero.py -q` → 3 passed (ratchet 0, acceptance A4, no product-code regression). CF command+self_report evidence on pi-eval-IMPL.
Next: stage exit — B0-1 ready for independent code review; conductor spawns follow-up implementer tasks for B0-2 (engine plumbing), B0-3 (legacy usage capture + long_horizon_runner.py:138 fix, +security gate), B0-4..B0-8, then owner-gated B1-B4.

