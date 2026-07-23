# Build Stream Lifecycle — Pi Benchmark Experimentation

<!-- STATUS BLOCK -->
```yaml
item: pi-benchmark
branch: conductor/pi-bench-retake-20260722
cf: { spec: CF-SPEC-9 }
phase: "Retake execution - F-9 cross-event-loop remediation"
stage: S4-remediate
status: in-progress
blocked_on: null
authored_by: build-stream-conductor
grounding: "Based on 2026-07-20-pi-full-replacement-master-plan.md Section 10"
last: { agent: gpt-5.6-luna, at: 2026-07-23T13:57:38Z, ledger: L-59 }
next_action: "F-9 fixed; run the conductor-created delta re-review before deciding whether to re-dispatch the ten startup_failure records."
```
<!-- /STATUS BLOCK -->

## Context
We have completed all 9 waves of the Pi candidate replacement (W0 through W9). The next
and final step is to conduct a professional, industry-class paired experiment using B0
plus process-bounded B1…B_N waves, evaluating the Pi candidate against the original Istara
React and agentic loops.

## Goals
1. Build and verify the B0 scheduler, budget ledger, DeepSeek adapter, and resumable manifest without loading a model.
2. Execute process-bounded benchmark waves B1 through B_N, where `N` is the explicit maximum number of benchmark worker processes for this machine/run.
3. Run Istara's original agentic loop and Pi adaptation against the same scenarios, with all live backend model calls routed through the configured DeepSeek API.
4. Enforce a hard cumulative spend ceiling of `$1.00` across all waves, retries, and evaluation preflight calls; stop before a call that could exceed the remaining envelope.
5. After B_N is terminal, launch a separate Build Stream Conductor judging session using the durable artifacts; Kimi is the intended judge and generates the final report and scorecards.

## Instructions
Review Section 10 of docs/build-stream/plans/2026-07-20-pi-full-replacement-master-plan.md for benchmark semantics, but treat this file as the execution authority for this wave.

### Wave and provider contract (this lifecycle file is authoritative)

- `B0` is the offline preparation and gate. It must discover and record an explicit
  `max_processes=N` value, create the immutable run manifest, validate the scheduler,
  and verify runtime credential/provider configuration. Any bounded DeepSeek reachability preflight
  is charged to the same cumulative ledger and is not a benchmark scenario call.
- `B1` through `B_N` are process-indexed execution waves, not the old fixed B1/B2/B3
  semantic labels. Each wave owns a disjoint, resumable slice of the canonical,
  breadth, depth, feature, spine, A2A, and probe work. At most `N` worker processes may
  exist at once; a wave may use fewer when its slice or remaining budget requires it.
- The former B1 contract, B2 breadth, B3 depth, and B4 report work packages are mapped
  into these waves by the B0 scheduler. No work package is silently skipped: its manifest
  row is `completed`, `not_runnable`, or `budget_blocked` with a reason.
- `B_N` is the final execution wave. Report aggregation is a coordinator step after all
  B1…B_N worker processes are terminal; it is not an additional unbounded process wave.
- All live Istara evaluation calls use the configured DeepSeek provider/model through
  Istara's API/dispatcher for both the original and Pi arms. Local/open-source routes,
  Claude, Codex, Kimi, and any other evaluation provider are disabled for this run.
  Post-run judging is a separate BSC session using the intended Kimi judging harness.
  Deterministic and T0/T1 model-free checks remain
  allowed and must be marked `model_free` in the manifest.
- The budget is one cumulative envelope: `budget_cap_usd=1.00`. Every call reserves its
  worst-case estimated cost before dispatch, records actual provider usage afterward, and
  is rejected with `budget_exceeded` if reservation plus committed spend would exceed the
  cap. Retries and evaluation preflight consume the same envelope; post-run judging is
  artifact-based and does not consume evaluation budget. There is no per-wave reset.
- The DeepSeek evaluation credential is read at runtime from its configured secret path; it
  must never appear in prompts, logs, manifests, or report output.

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

`B0` is offline preparation. `B1` through `B_N` are process-indexed execution waves,
where `N` is the explicit maximum number of benchmark worker processes for this run.
The coordinator aggregates results after `B_N`; it is not an additional unbounded wave.

```
B0 gate ──► B1 ──► B2 ──► … ──► B_N ──► separate BSC judging/report session
 scheduler       disjoint, resumable Kimi-evaluation slices under one $1.00 cap
```

The master plan's phase table gated B1 "after W2" etc. as wave regression gates; with all
waves done, the former B1 contract, B2 breadth, B3 depth, and B4 report work packages are
mapped into the B1…B_N slices by the B0 scheduler. They no longer define the process
topology.

`N` must be recorded in the immutable run manifest. The scheduler fails closed if it is
missing, less than 1, or would exceed the process or budget bounds.

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
5. **Judges are never the DUT and run after evaluation.** A separate BSC judging session
   consumes the durable artifact packet, logs sha256(prompt+rubric), uses blind engine
   labels and position-swapped A/B comparisons, and caches judgments by
   `(scenario, run, rubric_version, judge_model)`. Its harness/model is independent of
   the DeepSeek evaluation route; Kimi is the intended judge.
6. **Exact-or-estimated tokens, always flagged.** Pi rows come exact from the ledger;
   legacy rows come provider-reported where available, else `estimate=true`. The report
   renders exact and estimated numbers in separate columns (§10.1.4, §5.5).
7. **Fail-closed everywhere.** A scenario that cannot run on an engine is recorded as
   `not_runnable` with a machine-readable reason and counted in the report — never dropped
   (§10.1.6). Every run dir carries a manifest (git sha, input sha256, redacted endpoint
   fingerprints); results dirs are gitignored; a secret scan precedes any README link
   (§10.6).
8. **Provider isolation and budget safety.** The runner rejects every non-DeepSeek evaluation
   provider/model before dispatch. The budget ledger is append-only and shared by every
   evaluation wave and retry. A missing credential, unavailable model, malformed usage
   response, or uncertain cost blocks the call instead of falling back.
9. **Minimal backend footprint.** Exactly two backend edits in the whole program, both
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
| B0-1 | Schema and result skeleton | `comparison-Istara-pi/metrics-schema.json`, `comparison-Istara-pi/` | — | S |
| B0-2 | Offline scheduler with explicit `N=max_processes`, disjoint shard manifest, resume markers, and process watchdog | `tests/pi_benchmark/runner.py`, manifest schema | B0-1 | M |
| B0-3 | Kimi-only evaluation adapter/preflight and append-only cumulative budget ledger (`budget_cap_usd=1.00`) | `tests/pi_benchmark/runner.py`, provider adapter, run metadata | B0-1 | M |
| B0-4 | Existing dry-run/plan-only engine plumbing and model-free contract checks | node harnesses, `tests/pi_benchmark/` | B0-1 | S |
| B0-5 | Canonical/spine/A2A packs, feature compiler, and injection probes | `tests/pi_benchmark/` | B0-2 | L |
| B0-6 | Legacy usage capture and long-horizon token correction, only if the current tree still lacks them | backend telemetry path, `tests/benchmarks/long_horizon_runner.py` | B0-1 | M |
| B0-7 | B0 gate: schema/tests, Kimi credential/model preflight, `N` recorded, zero provider fallback, dry-run cost estimate ≤ `$1.00` | `.results/runs/b0-gate/` | B0-2..B0-6 | S |
| B1…B_N | Process-indexed benchmark waves. Each wave claims a disjoint shard and runs mapped contract/breadth/depth work packages with `--provider kimi --model <configured-kimi-model> --budget-usd 1.00 --max-processes N` | `tests/pi_benchmark/.results/runs/b{i}-*` | prior wave + B0-7 | M/L |
| POST-N | Coordinator-only aggregation, reproducible report, secret scan, and rollout packet; no new unbounded worker process | `scripts/pi_benchmark_report.py`, `comparison-Istara-pi/reports/`, `comparison-Istara-pi/article/` | B_N terminal, budget ledger closed | M |

Suggested CF roles: one implementer role for B0 (`pi-eval-implementer`), one independent
reviewer for the scheduler/provider contract, and one executor lane per B wave. The
conductor preserves the same `N` and budget ledger across all waves; owner gates are
blocking evidence gates, not provider-selection opportunities.

## 4. Acceptance criteria

**B0 (offline gate):**
- A1 `metrics-schema.json` validates; all scheduler, adapter, ledger, and fixture tests
  pass and reject schema-violating records.
- A2 B0 records one explicit integer `N=max_processes`, process watchdog settings, and a
  deterministic shard map; resuming B0 does not duplicate shards or budget rows.
- A3 Provider preflight proves the Kimi evaluation credential and exact configured model
  are reachable; any preflight usage is ledgered and no key material is
  written to artifacts.
- A4 The manifest contains the configured Kimi evaluation provider/model,
  `budget_cap_usd=1.00`, an explicit starting spend row, and rejects every alternate
  provider/model.
- A5 The dry-run worst-case estimate for the complete B1…B_N evaluation schedule is ≤
  `$1.00`, with retries included; otherwise B0 blocks without a live call.

**Each B_i wave, for `1 ≤ i ≤ N`:**
- A6 The wave has a disjoint shard, ≤ `N` total worker processes, and resumable per-run
  records; no scenario is silently dropped.
- A7 Every live benchmark evaluation call uses Kimi only and reserves cost before dispatch;
  any uncertain or over-cap call becomes `budget_exceeded`/`budget_blocked`.
- A8 Each result is schema-valid, records exact or estimated usage explicitly, includes
  redacted provenance, and records `not_runnable` with a machine-readable reason when
  needed.
- A9 A wave cannot advance until its process sessions are terminal and its budget ledger
  reconciliation passes.

**POST-N coordinator:**
- A10 All mapped contract, breadth, depth, feature, spine, A2A, and probe work packages
  are accounted for across B1…B_N; the final report contains no unaccounted shard.
- A11 A post-run BSC judging session produces reproducible `report.md`, self-contained
  `report.html`, `scorecard.json`, and judge outputs; numeric values trace to run data.
- A12 Exact and estimated tokens/costs remain separate, and cumulative spend is proven
  `≤ $1.00` by the closed ledger.

## 5. Verification (exact commands)

Asset and B0 gates (no live benchmark calls until the Kimi evaluation preflight and owner gate):

```bash
# schema + unit suites for new assets (created in B0, extended per wave)
python -m pytest tests/pi_benchmark/ -q
# ratchet + existing production ladder must stay green after B0-3 backend edits
python -m pytest tests/pi_migration/test_count_to_zero.py -q
python -m pytest tests/pi_production/ -q
# deterministic eval reuse for axes 3/5 (no live model)
python scripts/run_istara_evals.py --output-dir tests/pi_benchmark/.results/evals
# engine plumbing (dry-run, starts nothing)
node tests/simulation/run.mjs --engine pi --scenario 05-chat-interaction --dry-run
node tests/simulation/run.mjs --engine legacy --scenario 05-chat-interaction --dry-run
node tests/real_user_benchmark/run.mjs --engine both --plan-only
# security gate for the registry telemetry edit (AGENTS.md)
python scripts/security_benchmark.py --fail-on-threshold
# B0 scheduler/provider/budget checks (must prove no alternate route)
python tests/pi_benchmark/runner.py --plan-only --provider kimi --model <configured-kimi-model> \
  --budget-usd 1.00 --max-processes <N> --out tests/pi_benchmark/.results/runs/b0-gate
python tests/pi_benchmark/verify_budget_ledger.py \
  --runs tests/pi_benchmark/.results/runs/b0-gate --cap-usd 1.00 --provider kimi
```

Kimi evaluation preflight (credential presence only; no benchmark spend):

```bash
# Resolve the configured Kimi credential through its existing runtime secret path.
# Do not print or persist the credential.
python tests/pi_benchmark/runner.py --preflight-only --provider kimi \
  --model <configured-kimi-model> --budget-usd 1.00
```

Process waves (repeat for `i=1…N`; the scheduler supplies the disjoint shard):

```bash
python tests/pi_benchmark/runner.py --wave <i> --max-processes <N> \
  --provider kimi --model <configured-kimi-model> --budget-usd 1.00 \
  --budget-ledger tests/pi_benchmark/.results/runs/budget-ledger.jsonl \
  --manifest tests/pi_benchmark/.results/runs/manifest.json
```

Coordinator aggregation after B_N + reproducibility + hygiene:

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
| Judge = DUT or judge bias | Medium | A separate post-run BSC judge uses blind labels, position swap, sha256-logged rubrics, and deterministic checks over durable artifacts; it cannot rerun the DUT. |
| Unapproved live-model load or spend | Medium | B0/G0/G1 evidence is required before live calls; the runner refuses calls without the gate artifact and enforces the shared ledger cap. |
| Estimated vs exact tokens silently mixed | Medium | `estimate` flag in schema; report renders separate columns; A15 test scans generated tables. |
| Non-determinism leaks (timestamps, git sha) breaking reproducibility | Medium | A14 byte-identity check on scorecard.json; report normalizes volatile fields. |
| Kimi evaluation API quota/latency makes a wave slow | Medium | Waves are resumable and bounded by `N`; completed records and reservations are durable, and a transient failure never triggers an alternate-provider fallback. |
| Parallel workers race the $1.00 envelope | High | One append-only budget ledger is locked before every call; reservation failure blocks the call and the coordinator reports `budget_blocked`. |
| Local/open-source route is accidentally selected | High | B0 validates the Kimi evaluation provider/model; the runner rejects non-Kimi evaluation configuration before dispatch; no fallback route is configured. |
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

- **G0 (before B0 live preflight):** this owner instruction authorizes Kimi-only
  benchmark evaluation with a hard cumulative cap of `$1.00`; record the approval as CF
  evidence, without recording the secret or inventing spend.
- **G1 (before B1):** B0 proves the exact `N`, Kimi provider/model identity, runtime credential
  credential presence, immutable shard manifest, and dry-run worst-case estimate ≤ `$1.00`.
- **G2 (before each live wave):** the conductor verifies remaining budget and process slots;
  if either is insufficient, the wave is `budget_blocked`/`process_blocked` and no call is
  made. There is no local-model or other-provider fallback gate.
- **G3 (after POST-N):** rollout decision review — presented with the report packet; the
  decision and any `agentic_engine_default` flip are out of scope here.

## 9. Explicit non-goals

- No rollout/engine-default flip, no legacy deletion (§13.4: a NEW spec if Pi wins).
- No changes to the donor/Petals permanent allowlist plane.
- No new product features; benchmark findings become new CF tasks, not in-scope fixes.
- No local/open-source model routing or non-Kimi evaluation provider routing, and no
  external spend above the single Kimi evaluation `$1.00` envelope. Post-run judging is
  a separate BSC artifact-evaluation stage.
- No benchmark worker may bypass the shared process scheduler or budget ledger.

## Findings register

| ID | Severity | Where | Finding | CF task | Status |
|----|----------|-------|---------|---------|--------|
| F-1 | Major | comparison-Istara-pi/metrics-schema.json (`metrics.spine_phase`) | 10-phase spine taxonomy (intent, context, plan, tool_selection, execution, recovery, grounding, synthesis, review, governance) not pinned; master plan §5.5 citation of metrics-schema.json:39-50 dangles; typo'd phase keys validate | FIX-pi-eval-REVIEW-r1 | verified (REREV pass, L-13) |
| F-2 | Minor | comparison-Istara-pi/metrics-schema.json (`metrics.additionalProperties`) | open axis-key set accepts typo'd axis names (e.g. tool_cal ling); inconsistent with strict top level + extensions escape hatch | FIX-pi-eval-REVIEW-r1 | verified (REREV pass, L-13) |
| F-3 | Blocker | `scheduler.py:write_manifest` / `runner.py:run_wave` | Real manifests store shard entries as unit-id strings, but wave execution dereferences them as unit objects and crashes before dispatch. | FIX-PI-BENCH-MOA-20260722-REVIEW-r1-wave | fixed |
| F-4 | Blocker | `moa.py:assess_validation_result` / `live_driver.py:_moa_evidence_from_capture` | Partial coder success can be labeled reconciled because selected endpoints count as served and requested response count is not enforced. | FIX-PI-BENCH-MOA-20260722-REVIEW-r1-moa | fixed |
| F-5 | Blocker | `live_driver.py:dispatch_unit` / `validation.py:_get_embeddings` | MoA omits the requested engine and approved route identity; embeddings escape the DeepSeek-only ledger; stamped provenance does not prove the served route. | FIX-PI-BENCH-MOA-20260722-REVIEW-r1-routing | fixed (L-26) |
| F-6 | Blocker | `live_driver.py:run_live_unit` / `budget_ledger.py` | The reserved output bound is not forwarded to dispatch, and duplicate/orphan/over-reservation ledger transitions can undercount or exceed the hard cap. | FIX-PI-BENCH-MOA-20260722-REVIEW-r1-budget | fixed (L-22) |
| F-7 | Major | Compass Forge post-change gate | New Python import cycles include `live_driver -> runner -> live_driver`; the task-scope architecture gate is not clean. | FIX-PI-BENCH-MOA-20260722-REVIEW-r1-gate | fixed (L-25) |
| F-8 | Major | `docs/build-stream/2026-07-22-pi-benchmark.md` Status Block | The B0 update left the resume contract on stale branch `Review_pi_test` and stale spec `CF-SPEC-8` instead of the active retake branch and `CF-SPEC-9`. | FIX-PI-BENCH-RETAKE-B0-20260723-WAVE-b0-REVIEW-r1-lifecycle | verified (REREV pass, L-55) |
| F-9 | Critical | `live_driver.py:740 run_live_unit_sync` / `pi_runtime/supervisor.py:526 get_supervisor` | Wave mode runs each unit in a fresh `asyncio.run` loop while the pi-runtime supervisor is a process-wide loop-bound singleton; units 2..N of a wave fail at dispatch ("Future attached to a different loop"): lane none B1 = 1 ok + 10 not_runnable/startup_failure with retained reservations ($0.0238 worst-case booked, not billed). | FIX-PI-BENCH-RETAKE-EXEC-20260723-WAVE-none-b1-eventloop | fixed (L-59) |


<!-- consensus-winning-plan:PI-BENCH-RETAKE-20260722 -->
## Winning consensus plan — PI-BENCH-RETAKE-20260722

# Plan C — Fresh Pi benchmark retake: validated B0, strict DeepSeek-only B1…B_N, separated Kimi judging

- **Task:** `PI-BENCH-RETAKE-20260722-PLAN-C` (consensus architect slot C; pipeline run `PI-BENCH-RETAKE-20260722`)
- **Spec:** CF-SPEC-9 · **Lifecycle:** `docs/build-stream/2026-07-22-pi-benchmark.md`
- **Brief:** `docs/build-stream/conductor-instructions/pi-benchmark-retake-20260722.md`
- **Authored:** 2026-07-22, worktree `Istara-main-pi-benchmark-retake`, branch `conductor/pi-bench-retake-20260722` @ `3a226139`
- **Mission:** retake the Pi-vs-Legacy benchmark as a clean, fully evidenced run: validate and
  harden the existing B0 apparatus, execute strict process-bounded waves B1…B_N against the
  Istara dispatcher with DeepSeek `deepseek-v4-pro` as the only provider under one cumulative
  USD 1.00 ledger, then hand frozen artifacts to a *separate* artifact-only Kimi judging/report
  session. This is a fresh, isolated run: the pi-eval / recovery / role-correction lineages are
  historical evidence only; none of their tasks, plans, casts, consensus state, gate approvals,
  or uncommitted files are continued.

---

## 1. Verified current state (all claims re-checked in-tree on 2026-07-22 @ `3a226139`)

### 1.1 B0 apparatus that already exists — reuse, do not rebuild

| Asset | Path | Contract (verified by reading) | Tests |
|---|---|---|---|
| Run-record schema | `comparison-Istara-pi/metrics-schema.json` | Draft-2020-12 record contract (identity, tier/engine/pack/phase, provenance, `usage.estimate`, 10 axis blocks, `not_runnable` reason enum) | `tests/pi_benchmark/test_metrics_schema.py` |
| Schema loader/helpers | `tests/pi_benchmark/schema.py` | `validate_record()`, `build_record()`, `write_record_atomic()` (tmp+rename), provenance/input hashing | via all suites |
| Paired runner + CLI | `tests/pi_benchmark/runner.py` | `--pack/--tier/--engine/--seeds/--repeats/--phase/--out` mandatory discipline; `--plan-only` (B0 scheduling), `--wave i --max-processes N --manifest M --budget-ledger L`, `--live` consent; provider/model hard-rejected unless `deepseek`/`deepseek-v4-pro` (`ONLY_PROVIDER`/`ONLY_MODEL`, runner.py:78-79,551-554); T2/T3 refuse without `--owner-gate` (exit 3, runner.py:472-479); wave requires max-processes+manifest+ledger (runner.py:560-563) | `tests/pi_benchmark/test_runner.py` |
| B0 scheduler | `tests/pi_benchmark/scheduler.py` | deterministic `build_run_units` (scenario×seed×repeat×engine×moa), disjoint round-robin `shard_units` (refuses `n<1`), immutable content-hashed `write_manifest` (idempotent resume / `ManifestConflict` on differing args), hash-verified `load_manifest`, `completed_unit_ids` resume (only parseable schema-valid records count) | `tests/pi_benchmark/test_scheduler.py` |
| Budget ledger | `tests/pi_benchmark/budget_ledger.py` | append-only JSONL, `flock`-serialized read-modify-append, fsync per row, torn-tail tolerance, reserve-before-dispatch / commit-actual (≤ reservation) / release-only-pre-dispatch / `close()` seals; secret-marker meta refusal | `tests/pi_benchmark/test_budget_ledger.py` |
| Ledger verifier | `tests/pi_benchmark/verify_budget_ledger.py` | replays durable rows: known types, no orphan commit/release, commit ≤ reservation, spend ≤ cap; `--close` seals; exit 0/1/2 | `tests/pi_benchmark/test_verify_budget_ledger.py` |
| Provider isolation | `tests/pi_benchmark/deepseek_provider.py` | constructs only `deepseek`/`deepseek-v4-pro`; key from env `ISTARA_PI_SECRET_PI_DEEPSEEK_DEFAULT` or Keychain `istara-pi-deepseek`/`openclaw`, memory-only; reserve→dispatch→commit with retained reservation on unknown usage; redacted `endpoint_fingerprint()` | `tests/pi_benchmark/test_deepseek_provider.py` (**2 red, §1.2**) |
| Live DUT driver | `tests/pi_benchmark/live_driver.py` | every live unit through `AgenticDispatcher.ensemble` pinned to endpoint `pi-deepseek-default` + model `deepseek-v4-pro` (`distinct=False`); engine from the unit; route admission rejects unapproved endpoint/provider/model (`RouteAdmissionError`); redacted route evidence → provenance fingerprint (`deepseek-route:<sha>`); usage provider-reported (`estimate=False`) else documented `chars4` (`estimate=True`); crash-safe record writes; resume skips completed units | `tests/pi_benchmark/test_live_driver.py` |
| MoA truthfulness | `tests/pi_benchmark/moa.py` | requested vs served mode/samples/routes; downgrade detection (`<requested>-><served>`, `partial_coder`, `single_coder`, 0-response blocked) → `degraded` → record `not_runnable`, never `ok`; `validate_topology` spend-free dry-run probe | `tests/pi_benchmark/test_moa.py` |
| In-run judge (superseded for retake, §2.6) | `tests/pi_benchmark/deepseek_judge.py`, `judge.py`, `judge_config.json` | DeepSeek-backed `judge_fn` on the shared ledger; blind A/B + position swap; malformed verdict fails | `test_deepseek_judge.py`, `test_judge.py` |
| Scenario packs | `tests/pi_benchmark/scenarios/` | **22 scenarios**: `canonical` 15 (min_tier T0), `spine` 4 (min_tier T2), `a2a` 3 (min_tier T2); `PACK_NAMES=("canonical","spine","a2a")` — `features`/`probes` are compiled elsewhere, not runner-loadable packs | `test_scenarios.py`, `test_b1_contract.py` |
| Offline axes | `tests/pi_benchmark/feature_criteria.py`, `tests/pi_benchmark/probes/` | 86-feature criteria compiler; pure scorers (protected-block, persona, thinking-leak, injection) | `test_feature_criteria.py`, `test_probes.py` |
| Report generator | `scripts/pi_benchmark_report.py` | CLI `--runs <dir> --out <dir>` (:602-603); generates `report.md`/`report.html`/`scorecard.json` from frozen records only | `tests/pi_benchmark/test_report.py` |
| Prior fixes | `tests/pi_benchmark/test_b0_3_long_horizon_tokens.py` | long-horizon chunk-count-as-tokens bug fixed (B0-3) | green |

### 1.2 Validation executed in this planning stage (offline only — no live calls, no servers, no models, no credentials)

- `backend/.venv/bin/python -m pytest tests/pi_benchmark/ -q` → **170 passed, 2 failed** (3.23s).
  The suite is **red**; a live program cannot start on a red money path. Red tests:
  - `test_deepseek_provider.py::test_chat_happy_path_commits_actual_cost`
  - `test_deepseek_provider.py::test_preflight_is_a_minimal_ledgered_call`

  **Root cause (pinned):** `DeepSeekProvider.chat` reserves `estimate_cost(ceil(chars/4 of prompt JSON), max_tokens)` (deepseek_provider.py:203-207). That bound ignores provider-reported cache-token classes and can undercount real prompt tokens. Since F-6's hardening, `BudgetLedger.commit` refuses `actual > reservation` (budget_ledger.py:276-280), so any real call whose reported usage exceeds the estimate raises `LedgerStateError` *after* dispatch. The two tests encode the pre-F-6 expectation and fail; both must be reconciled (RT-1). Same class of bug on the DUT side: `live_driver.run_live_unit` reserves from `_chars4(system+prompt)` (live_driver.py:558-566) and commits at live_driver.py:648 **outside** the dispatch try/except — a `LedgerStateError` there escapes `run_wave`/`main` and kills the wave process. Worse, the unit's record is never written, so a resume re-enters `ledger.reserve(unit_id)` → `LedgerStateError("already has a reservation")` → the wave is **permanently wedged**, and the money truth (reservation outstanding, usage unknown) is lost. This is the single most important latent defect for the retake; RT-1 fixes it fail-closed.
- CLI probes (throwaway `/tmp` paths, offline): `--plan-only --moa-mode self_moa --max-processes 4` wrote a content-hashed manifest (44 units over 4 shards, exit 0); identical rerun resumed unchanged (exit 0); differing `--max-processes 3` refused with `ManifestConflict` (exit 2); `--provider kimi` rejected by argparse; `--wave 1 --live` without `--owner-gate` refused (exit 3). All as designed.
- Pack census (executed): canonical 15 / spine 4 / a2a 3 = 22 scenarios; spine+a2a are `min_tier=T2`.
- **One MoA mode per manifest:** `--moa-mode` takes a single value (runner.py:543), so the full program is **three B0 schedules** (`none`, `self_moa`, `full_ensemble`) sharing one budget ledger (§2.3).

### 1.3 State facts that shape the retake

- **No `tests/pi_benchmark/.results/` exists** → no prior manifest/ledger; B0 starts clean (no `ManifestConflict` risk). `.results/` is gitignored (`.gitignore`: `.results/`).
- **Stale gate artifacts:** `tests/pi_benchmark/gates/g1_owner_gate.json` / `g2_owner_gate.json` are `APPROVED` but belong to the prior lineage (authorized 2026-07-22T14:32:34Z; judge_model `gpt-5.6-luna`; budget USD **0.50**). They contradict the retake canon (USD 1.00; Kimi post-run judge; DeepSeek-only DUT) and **must not** authorize this run. Fresh retake-scoped gate artifacts are required (§2.7); the stale files stay untouched as history.
- **Prior report bundle is non-authoritative:** `comparison-Istara-pi/reports/20260722T174500Z/` claims 654 executed records, but its input `.results/` tree is not in the repo and cannot be audited. It is a historical artifact: never cited as evidence about Pi vs Legacy, never edited, never deleted. The retake publishes a *new* timestamped bundle derived only from the retake's frozen records + closed ledger.
- **Brief indirection:** the retake brief's pointer to `docs/build-stream/conductor-instructions/pi-benchmark-deepseek-moa-execution.md` dangles (no such file on this branch, no git history). The brief `pi-benchmark-retake-20260722.md` itself is the execution authority.
- **Role-canon drift in the lifecycle file:** the embedded winning plan and DEC-5/DEC-6 still carry Kimi-as-evaluation text (14+ regions; no DEC-7 supersession recorded). RT-0 appends DEC-7 to the lifecycle decision log restating the canon below (§1.4); the append is an execution-phase edit by the implementer/conductor, not by this planning stage.
- **Backend import hazard (live waves):** with the shared root venv, `import app` resolves to the **root checkout** (`/Users/user/Documents/Istara-main-pi-replacement/backend/app/__init__.py`), not the worktree. Waves launched from the worktree would silently execute root code while recording worktree provenance. RT-0/RT-3 attests and pins the execution checkout (`PYTHONPATH="$PWD/backend"` + recorded `app.__file__` assertion) before any live call.
- **Approved route exists:** `backend/app/core/pi_runtime/endpoints.py:23` registers `DEFAULT_ENDPOINT_ID = "pi-deepseek-default"` — the one approved benchmark route.

### 1.4 Role canon (authoritative for this retake; supersedes the stale lifecycle text via DEC-7 at RT-0)

- **DUT** = Istara's two agentic arms (`engine=pi` and `engine=legacy`) through the API/dispatcher path (`AgenticDispatcher.ensemble`).
- **Evaluation provider** = DeepSeek `deepseek-v4-pro` only, via pinned endpoint `pi-deepseek-default`. Local routes, Claude, Codex, Kimi, and every other provider are disabled for DUT traffic; there is no fallback.
- **Budget** = one cumulative crash-safe ledger, `budget_cap_usd=1.00`, shared by preflight, all waves, all lanes, and all retries; no per-wave reset; closed at POST-N.
- **Kimi** is **not** a benchmark provider and makes **no** in-run judge calls. Kimi is reserved for a separate, artifact-only post-run judging/report BSC session (§2.6).
- `deepseek_judge.py` / `judge_config.json` (judge = DUT model on the shared ledger) are **superseded for this retake**: no judge calls inside B waves. Judging happens post-run, over artifacts, by Kimi, off the DUT ledger.

---

## 2. Design

### 2.1 Program shape

```
RT-0 attestation ─► RT-1 harden (red→green) ─► RT-2 estimate gate ─► RT-3 B0 scheduling
      │ offline, no spend; G-R0 = owner approval of this plan before any implementation
      ▼
G-R1 owner gate ─► RT-4 preflight (1 ledgered ping) ─► G-R2 owner gate
      ▼
RT-5 waves: lane none (B1..B4) ─► lane self_moa (B1..B4) ─► lane full_ensemble (B1..B4)
      ▼
RT-6 POST-N: ledger close+verify ─► aggregate ─► report bundle ─► secret scan ─► G-R3 ─► README link
      ▼
[separate BSC session] Kimi artifact-only judging/report (interface spec §2.6; not executed here)
```

Everything up to G-R1 is offline and spends nothing. The only pre-wave spend is one
cheapest-possible preflight ping, charged to the same ledger.

### 2.2 Immutable, strict wave manifest (B0 → B1…B_N)

Three B0 schedules — one per MoA lane, because `--moa-mode` is single-valued — each produced
by `runner.py --plan-only` into its own run root, all sharing one budget ledger:

| Lane | Run root (gitignored) | Manifest | Units |
|---|---|---|---|
| `none` | `tests/pi_benchmark/.results/runs/retake/none/` | `…/none/manifest.json` | 44 |
| `self_moa` | `…/runs/retake/self_moa/` | `…/self_moa/manifest.json` | 44 |
| `full_ensemble` | `…/runs/retake/full_ensemble/` | `…/full_ensemble/manifest.json` | 44 |
| shared | `…/runs/retake/budget-ledger.json` (+ `.lock`) | — | — |

- Units per lane = 22 scenarios × seeds`(0,)` × repeats `1` × engines `(pi, legacy)` = **44**;
  132 total. Sharded round-robin into `max_processes` disjoint shards; wave `i` executes shard `i`.
- **`N` = `max_processes` = 4**, recorded in each manifest (`write_manifest` refuses `N<1` and
  `N ≠ shard_count`, scheduler.py:156-161). `N` bounds *worker processes*; it is **not**
  `moa_n` (MoA samples per `self_moa` unit / requested slots per `full_ensemble` unit = **3**)
  and **not** `repeats` (per-scenario repetitions = **1**). All three are manifest fields.
- `B1…B_N` per lane = waves 1..4 of that lane's manifest. Execution order: lane `none` waves
  1→4, then `self_moa` 1→4, then `full_ensemble` 1→4 — sequential by default (a wave may use
  fewer than `N` processes); up to `N` concurrent wave processes are permitted because the
  ledger's `flock` serializes money. `B_N` terminal = last wave of the `full_ensemble` lane.
- Immutability: identical rerun resumes the manifest unchanged; differing arguments raise
  `ManifestConflict`; every `load_manifest` re-verifies `content_sha256` (probe-verified §1.2).
- Work-package accounting: every manifest unit ends exactly one of `completed` (schema-valid
  record written), `not_runnable` (typed reason), or `budget_blocked` (`budget_exceeded`
  record). No unit is silently dropped; unknown scenario ids still get `not_runnable` records
  (runner.py:239-262).

### 2.3 Budget and ledger contract (preserved, plus RT-1's fail-closed edges)

- One ledger file for the whole retake; `BudgetLedger(cap_usd=1.00)`; reserve-before-dispatch;
  commit actual ≤ reservation; release only for provably pre-dispatch failures; unknown usage
  after dispatch retains the reservation as worst-case spend; `close()` seals (idempotent).
- Per-unit worst-case reservation (post-RT-1 formula): `(max(2×prompt_tokens, 256) × input_rate
  + max_tokens × output_rate) × model_calls(unit)`, where `model_calls` = 1 / `moa_n`=3 /
  `max(3, moa_n)`=3 (live_driver.py:399-404). Input priced at the input rate (== cache-write
  rate; cache-read is cheaper, so this is conservative).
- **Default-schedule arithmetic (max_tokens=1024, smoke prompt ≈120 tokens → reserve input 256):**
  per call ≈ 256×0.55e-6 + 1024×2.19e-6 ≈ **$0.00238**.
  Lane `none`: 44 × $0.00238 ≈ **$0.105**; lane `self_moa`: 44 × 3 × $0.00238 ≈ **$0.314**;
  lane `full_ensemble`: ≈ **$0.314**; preflight ≈ **$0.00015**.
  **Total worst case ≈ $0.73 ≤ $1.00** (~27% headroom for retries; retries only re-dispatch
  incomplete units and draw new reservations from the same envelope).
- The RT-2 estimate gate prints this figure deterministically at B0 and **exits 2 when > cap**:
  e.g. `repeats=2` (264 units ≈ $1.47) must block *before* any live call.
- `full_ensemble` units are expected-degraded (§2.5) and cost ≈ $0.31 to *measure* the routing
  truth empirically. Owner option at G-R2: mark the lane `not_run` without dispatch (records
  `not_runnable` with reason, saves ≈ $0.31) — a budget decision, not a silent skip.

### 2.4 Route and evidence truthfulness

- Every live sample must prove the approved route: endpoint `pi-deepseek-default`, provider
  `deepseek`, model `deepseek-v4-pro`; anything else raises `RouteAdmissionError` →
  `not_runnable` record with rejected route evidence (live_driver.py:212-258, 608-622).
- Provenance fingerprints are derived from the **served** redacted route evidence
  (`deepseek-route:<sha256>`); blocked-before-dispatch records carry null live identity —
  never a guessed route (live_driver.py:480-516).
- Usage is provider-reported (`estimate=False`) when exposed; otherwise the documented
  `chars4` estimator over actual text (`estimate=True`, `estimator="chars4"`). A
  successful-looking dispatch with neither usage nor text is `not_runnable/other`
  (`unknown_usage_fail_closed`), reservation retained. Exact and estimated numbers are never
  summed in one column (schema `usage.estimate`; report renders them separately).

### 2.5 MoA truthfulness (self-MoA and full ensemble)

- `self_moa` (moa_n=3): one endpoint sampled 3× with the backend temperature sweep
  (0.3/0.7/1.0). Served 3 responses on 1 distinct route **reconciles** (valid self-MoA).
- `full_ensemble` (slots=3): `distinct=False` pins all slots to the one approved endpoint →
  diversity collapse → `single_coder` → `degraded` → record `not_runnable` with full
  `extensions.moa` evidence. **A route/endpoint downgrade is degraded or blocked, never an
  ensemble success.** Method downgrades (`full_ensemble->dual_run/self_moa`), `partial_coder`,
  and zero-response `blocked` follow the same rule (moa.py:132-160, 202-211).
- Serving a *real* full ensemble would require ≥3 owner-approved distinct DeepSeek endpoints —
  an owner decision, explicitly out of scope (§9). The benchmark reports the truthful degraded
  outcome instead of discovering unapproved local/other endpoints.

### 2.6 Post-run separation (Kimi judging is a different session)

1. **POST-N coordinator (this lifecycle):** after `B_N` is terminal — close the ledger
   (`verify_budget_ledger.py --close`), verify spend ≤ $1.00, generate the report bundle from
   frozen records (`scripts/pi_benchmark_report.py`), run the reproducibility diff and secret
   scan, link the README. All artifact-only: no model calls, no DUT dispatch.
2. **Separate BSC judging session (not this pipeline):** a distinct conductor run with its own
   cast/lifecycle, where **Kimi** judges the frozen artifact packet and writes the final
   judging outputs/report narrative. Contract this plan imposes on that session:
   - **Inputs (read-only):** the three manifests, `records/` trees, the **closed** DUT ledger
     (read-only — never opened for writes, never charged), the generated bundle, and an
     artifact-packet index with sha256 per file.
   - **Forbidden:** rerunning/re-dispatching any DUT unit; mutating records, manifests, or the
     DUT ledger; using DeepSeek or any benchmark provider for judging; writing into
     `tests/pi_benchmark/.results/`.
   - **Outputs:** per-judgment records (blind A/B, position-swapped, rubric-versioned,
     sha256-logged prompts) and the final report artifacts under a new
     `comparison-Istara-pi/reports/<ts>-judging/` path (additive; prior bundles untouched).
   - It launches **only after** G-R3 evidence shows all B waves terminal and the DUT ledger
     closed ≤ cap.

### 2.7 Owner gates (fresh, retake-scoped, blocking)

| Gate | Before | Owner approves | Evidence |
|---|---|---|---|
| G-R0 | any implementation | this consensus-winning plan | CF evidence on the IMPL task |
| G-R1 | preflight (first live call) | DeepSeek-only DUT route, USD 1.00 cumulative cap, credential path (env/Keychain), no-fallback policy | new artifact `tests/pi_benchmark/gates/retake_g1_owner_gate.json` + CF evidence quoting the approval |
| G-R2 | first live wave | B0 evidence pack: green suite, three immutable manifests (N=4 recorded), dry-run estimate ≤ $1.00, preflight ledgered, environment attestation, route-isolation probes | new artifact `tests/pi_benchmark/gates/retake_g2_owner_gate.json` + CF evidence |
| G-R3 | report publication / judging-session launch | closed ledger verified ≤ $1.00, reproducibility diff clean, secret scan clean | CF evidence on the POST-N task |

The stale `g1/g2_owner_gate.json` files are left byte-identical (history). The runner's
fail-closed checks (`--owner-gate`, `--live`) are the mechanical enforcement; the gates above
are the human authorization. No gate is a provider-selection opportunity.

---

## 3. Task breakdown

Estimates: S < half day, M ≈ 1 day (agent time; wave wall-clock excluded).

| # | Task | Primary files | Depends | Est |
|---|---|---|---|---|
| RT-0 | Environment & state attestation (offline): record `max_processes` decision N=4 + justification, branch/HEAD, resolved `app.__file__` (must point inside the execution checkout — set `PYTHONPATH="$PWD/backend"` for all bench commands and assert), absence of `.results/` residue; append **DEC-7** (role canon §1.4, superseding stale DEC-5/DEC-6 Kimi clauses) to the lifecycle decision log; write `b0-attestation.json` | lifecycle decision log (append-only), `.results/runs/retake/b0-attestation.json` | G-R0 | S |
| RT-1 | **Apparatus hardening — red→green + wedge-proof accounting.** (a) `deepseek_provider.py`: reserve `max(2×est_input, 256)` input-priced + `max_tokens` output-priced; catch commit `LedgerStateError` → `ProviderCallFailed("over_reservation_fail_closed")`, reservation **retained**. (b) `live_driver.py`: same reservation formula; wrap `ledger.commit` — on `LedgerStateError` write `not_runnable/other` record (`accounting_fail_closed`), retain reservation, never crash the wave; on resume, `reserve` raising `LedgerStateError` (prior reservation exists, no record) → write `not_runnable/other` (`interrupted_unknown_usage`), retain reservation — wedge impossible. (c) Update the 2 stale tests to realistic usage within the documented margin; add tests: over-reservation commit fail-closed (provider + driver), resume-with-outstanding-reservation, retained-reservation accounting. | `tests/pi_benchmark/deepseek_provider.py`, `tests/pi_benchmark/live_driver.py`, `tests/pi_benchmark/test_deepseek_provider.py`, `tests/pi_benchmark/test_live_driver.py` | RT-0 | M |
| RT-2 | **Dry-run estimate gate.** `--plan-only` prints a deterministic worst-case USD estimate (per-lane unit counts × per-call worst case by MoA mode × model-calls + preflight reservation) and exits 2 when it exceeds `--budget-usd`; unit tests for ≤cap exit 0 / >cap exit 2. | `tests/pi_benchmark/runner.py`, `tests/pi_benchmark/test_runner.py` | RT-1 | S |
| RT-3 | **B0 scheduling (offline).** Run `--plan-only` for the three lanes (§2.2) into the shared run root; record manifest content hashes; probe idempotent resume + `ManifestConflict`; offline `validate_topology` probe recorded as spend-free evidence. | `.results/runs/retake/**` (gitignored) | RT-2 | S |
| RT-4 | **Preflight (post-G-R1).** One `DeepSeekProvider.preflight()` call against the shared ledger (documented heredoc command, §5); `verify_budget_ledger.py` proves reserve+commit ≤ cap. No key material in any artifact. | `.results/runs/retake/budget-ledger.json` | G-R1 | S |
| RT-5 | **Waves B1…B_N × 3 lanes** (§2.2 order; sequential default, ≤N concurrent). Per wave: `--wave i --max-processes 4 --live --owner-gate gates/retake_g2_owner_gate.json` with lane manifest + shared ledger; after each wave assert shard records == shard units and ledger verify passes; `budget_exceeded`/`not_runnable` counted, never dropped. | `.results/runs/retake/**` | G-R2 | M |
| RT-6 | **POST-N coordinator.** `verify_budget_ledger.py --close` + tally evidence; generate bundle to `comparison-Istara-pi/reports/<ts>/`; reproducibility re-run diff of `scorecard.json`; secret scan; G-R3; README reports-index link; write the judging-session artifact-packet index (sha256 per file). | `comparison-Istara-pi/reports/<ts>/`, `comparison-Istara-pi/README.md` (index lines only) | B_N terminal | M |

Suggested CF roles: one implementer (RT-0…RT-2) + independent reviewer; one executor lane
(RT-3…RT-6) under the conductor; owner approvals at G-R1/G-R2/G-R3 recorded as CF evidence.
The Kimi judging session is a **new** cast in a **new** conductor run (§2.6), not a role here.

---

## 4. Acceptance criteria

- **AC-1 (validated apparatus):** `pytest tests/pi_benchmark/ -q` → **172 passed, 0 failed**
  (170 existing − 2 stale-fixed + 4 new RT-1/RT-2 tests, minimum). Suite green before G-R1.
- **AC-2 (immutable manifest):** three manifests written; each records `max_processes=4`,
  `provider=deepseek`, `model=deepseek-v4-pro`, `budget_cap_usd=1.0`, `moa_n=3`, `repeats=1`,
  `tier=T3`, disjoint shards covering 44 units exactly once; identical rerun resumes;
  differing args `ManifestConflict`; `load_manifest` hash-verified. `N` ≠ `moa_n` ≠ `repeats`
  are distinct recorded fields.
- **AC-3 (estimate gate):** B0 prints worst-case **≤ $1.00** (expected ≈ $0.73) and exits 0;
  a demonstrated `repeats=2` probe exits 2 with no manifest mutation and no live call.
- **AC-4 (owner gates):** no live call occurs before G-R1; no wave before G-R2; runner refuses
  T2/T3 without `--owner-gate` (exit 3) and without `--live`; fresh retake gate artifacts
  exist and are quoted in CF evidence; stale gates untouched.
- **AC-5 (budget truth):** every dispatched call has reserve→commit (or retained reservation
  with typed fail-closed record); no orphan commits; `verify_budget_ledger.py` passes after
  every wave; final closed tally proves spend ≤ $1.00; preflight and retries included.
- **AC-6 (record completeness):** every manifest unit ends with exactly one schema-valid
  record: `ok`, `not_runnable` (typed reason), or `budget_blocked`; re-running a wave writes
  no duplicate records and dispatches no completed unit (crash-safe resume); a mid-wave kill
  leaves the next resume able to complete the shard (RT-1 wedge-proofing).
- **AC-7 (route truth):** every `ok` record carries redacted route evidence proving endpoint
  `pi-deepseek-default` / `deepseek` / `deepseek-v4-pro`; any unapproved route is
  `not_runnable` with rejected-route evidence; blocked-before-dispatch records carry null
  live identity.
- **AC-8 (MoA truth):** `extensions.moa` records requested vs served mode/samples/routes/
  consensus; every downgrade (`full_ensemble->*`, `partial_coder`, `single_coder`, blocked)
  is `not_runnable` — zero `ok` downgraded ensembles. On the single approved route, the
  `full_ensemble` lane is expected 100% degraded and is counted, not hidden.
- **AC-9 (post-run separation):** the DUT ledger carries no `kind="judge"` rows; the Kimi
  judging session consumes only the frozen artifact packet read-only, launches after G-R3,
  and writes only additive outputs under its own `reports/<ts>-judging/` path.
- **AC-10 (report integrity):** the new bundle derives solely from retake records (manifest
  content hash + git sha recorded); reproducibility re-run produces byte-identical
  `scorecard.json`; secret scan passes before the README link; the prior
  `20260722T174500Z` bundle is neither cited nor modified.

## 5. Verification matrix (exact commands)

Conventions: `PY=/Users/user/Documents/Istara-main-pi-replacement/backend/.venv/bin/python`
(or the worktree-local equivalent pinned in RT-0); all bench commands run from the execution
checkout root with `PYTHONPATH="$PWD/backend"`; `R=tests/pi_benchmark/.results/runs/retake`.

**V0 — offline apparatus (RT-1/RT-2 done; before G-R1):**
```bash
$PY -m pytest tests/pi_benchmark/ -q                      # AC-1: 172 passed
$PY -m pytest tests/pi_migration/test_count_to_zero.py -q # ratchet stays 0
$PY -m pytest tests/pi_production/ -q                     # production ladder green
python scripts/security_benchmark.py --fail-on-threshold  # provider/ledger surface (AGENTS.md)
```

**V1 — B0 scheduling (RT-3; offline):**
```bash
for lane in none self_moa full_ensemble; do
  $PY tests/pi_benchmark/runner.py --pack canonical,spine,a2a --tier T3 --engine both \
    --seeds 0 --repeats 1 --moa-mode $lane --moa-n 3 --budget-usd 1.00 \
    --plan-only --max-processes 4 \
    --out $R/$lane --manifest $R/$lane/manifest.json --budget-ledger $R/budget-ledger.json
done   # AC-2/AC-3: 44 units × 4 shards per lane; estimate ≤ $1.00 printed; exit 0
# immutability probes: identical rerun -> exit 0 unchanged; --max-processes 3 -> exit 2 ManifestConflict
# estimate-gate probe: --repeats 2 -> exit 2, no manifest mutation, no live call
$PY -c "from tests.pi_benchmark.moa import validate_topology as v; \
import json;print(json.dumps(v(available_endpoint_ids=['pi-deepseek-default'],requested_slots=3)))"
# ^ spend-free: full_ensemble would degrade to self_moa on one route (AC-8 expectation)
```

**V2 — preflight (after G-R1; first spend, one ping):**
```bash
$PY - <<'PY'
from pathlib import Path
from tests.pi_benchmark.budget_ledger import BudgetLedger
from tests.pi_benchmark.deepseek_provider import DeepSeekProvider
ledger = BudgetLedger(Path("tests/pi_benchmark/.results/runs/retake/budget-ledger.json"), cap_usd=1.00)
usage = DeepSeekProvider(provider="deepseek", model="deepseek-v4-pro").preflight(ledger=ledger)
print("preflight ok:", usage.cost_usd, "estimate:", usage.estimate)
PY
$PY tests/pi_benchmark/verify_budget_ledger.py --ledger $R/budget-ledger.json --cap-usd 1.00
```

**V3 — waves (after G-R2; `i=1..4` per lane, in lane order none → self_moa → full_ensemble):**
```bash
$PY tests/pi_benchmark/runner.py --pack canonical,spine,a2a --tier T3 --engine both \
  --seeds 0 --repeats 1 --moa-mode <lane> --moa-n 3 --budget-usd 1.00 \
  --wave <i> --max-processes 4 --live \
  --owner-gate tests/pi_benchmark/gates/retake_g2_owner_gate.json \
  --manifest $R/<lane>/manifest.json --budget-ledger $R/budget-ledger.json \
  --out $R/<lane>
# after each wave: shard records == shard units (resume re-run is a no-op), and:
$PY tests/pi_benchmark/verify_budget_ledger.py --ledger $R/budget-ledger.json --cap-usd 1.00
```

**V4 — POST-N (after B_N terminal):**
```bash
$PY tests/pi_benchmark/verify_budget_ledger.py --ledger $R/budget-ledger.json --cap-usd 1.00 --close
python scripts/pi_benchmark_report.py --runs $R --out comparison-Istara-pi/reports/$(date -u +%Y%m%dT%H%M%SZ)
python scripts/pi_benchmark_report.py --runs $R --out /tmp/pi-retake-rerun \
  && diff <(jq -S . comparison-Istara-pi/reports/<ts>/scorecard.json) <(jq -S . /tmp/pi-retake-rerun/scorecard.json)
python scripts/check_public_tree_clean.py   # secret scan over the new report dir before README link
```

**V5 — judging-session interface (G-R3 passed; separate BSC run):** artifact-packet index
(sha256 per file: 3 manifests, records trees, closed ledger, bundle, scorecard) exists; DUT
ledger verified closed and read-only; packet is the session's only input (§2.6).

Every executed command is recorded as CF `command` evidence on the owning task; owner
approvals are recorded with the in-chat approval quoted.

## 6. Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Reservation underestimates real usage → post-dispatch `LedgerStateError` kills/wedges a wave | **High (latent, proven red)** | RT-1: input margin (×2, floor 256, input-priced), commit fail-closed record, resume reconciliation; AC-6 wedge-proof test. |
| Stale G1/G2 artifacts mistaken as authorization ($0.50, wrong judge canon) | Medium | Fresh retake-scoped gate artifacts required at G-R1/G-R2 (AC-4); stale files untouched; DEC-7 restates canon. |
| Live waves execute the wrong checkout's backend (shared venv resolves `app` to root) | Medium | RT-0 attestation: `PYTHONPATH="$PWD/backend"` pinned for all bench commands; `app.__file__` asserted inside the execution checkout before G-R2. |
| `full_ensemble` degradation misread as benchmark failure | Medium | Expected-degraded is documented (§2.5), pre-probed offline (`validate_topology`, V1), counted `not_runnable` (AC-8); optional owner skip at G-R2 (§2.3). |
| Budget exhaustion mid-program | Medium | Worst-case estimate gated at B0 (AC-3); reserve-before-dispatch; `budget_exceeded` units recorded and counted; ~27% headroom; no per-wave reset. |
| Judge/DUT conflation (spend or role) | Medium | No in-run judge calls (§1.4); AC-9 asserts zero `kind="judge"` rows; Kimi judging is a separate artifact-only session after G-R3. |
| Prior bundle cited as Pi-superiority evidence | Medium | Marked non-authoritative (§1.3); AC-10 forbids citing/modifying it; new bundle derives only from retake records. |
| `.results/` loss before aggregation (gitignored, local-only) | Low | POST-N aggregation runs immediately after B_N; the tracked bundle + closed-ledger tally are the durable deliverables; packet index hashes everything. |
| Shared-worktree lifecycle races (ledger/status corruption) | Medium | `repo_lock` critical section for every lifecycle read-append-commit (conductor protocol); append-only entries. |
| Secret leakage (API key into logs/ledger/report) | Low | Key held in memory only; ledger meta secret-markers refused; redacted fingerprints; secret scan gates publication (V4). |
| Report hand-editing / irreproducibility | Low | Generated-from-records only; reproducibility diff (V4); README links only the dated generated copy. |
| Scope creep into product code or feature/probe live packs | Medium | Changed-file scope pinned (§9); features/probes stay offline compilers; new defects become new CF tasks, not in-scope edits. |

## 7. Rollback

- **RT-1/RT-2 (code):** each lands as one focused commit on the worktree branch; revert the
  commit. No backend/product files are touched; no migrations, settings, or allowlist changes.
- **RT-3/RT-4 (schedule/preflight):** `.results/` is gitignored — delete the run root. The
  ledger is append-only: "rollback" of a started program is stopping wave launches, closing
  the ledger, and recording remaining units `budget_blocked` — never editing rows.
- **Gate artifacts:** additive new files; delete to withdraw (the stale prior gates are never
  modified, so no history is lost).
- **RT-6 (publication):** report bundles are additive; un-link the README index line. The
  judging session has not launched until G-R3, so there is nothing downstream to unwind.
- **Engine state:** the benchmark observes product paths only; `agentic_engine_default` and
  production routing are never touched by any task in this plan.

## 8. Owner gates summary

G-R0 (pre-implementation) → G-R1 (pre-preflight: DeepSeek-only route, $1.00 cap, credential
path) → G-R2 (pre-wave: B0 evidence pack + estimate ≤ cap) → G-R3 (pre-publication and
pre-judging-session: closed ledger ≤ cap, reproducible bundle, secret scan). Gates are
blocking evidence checkpoints recorded in CF with the approval quoted; they are never
provider-selection opportunities, and there is no fallback-route gate.

## 9. Changed-file scope (narrow) and non-goals

**In scope (the entire retake touches only):**
- `tests/pi_benchmark/deepseek_provider.py`, `tests/pi_benchmark/live_driver.py`,
  `tests/pi_benchmark/runner.py` (RT-1/RT-2 hardening + estimate gate)
- `tests/pi_benchmark/test_deepseek_provider.py`, `tests/pi_benchmark/test_live_driver.py`,
  `tests/pi_benchmark/test_runner.py` (reconciled + new tests)
- `tests/pi_benchmark/gates/retake_g1_owner_gate.json`, `…/retake_g2_owner_gate.json` (new)
- `tests/pi_benchmark/.results/runs/retake/**` (gitignored run artifacts)
- `comparison-Istara-pi/reports/<ts>/` (new bundle), `comparison-Istara-pi/README.md`
  (reports-index lines only)
- `docs/build-stream/2026-07-22-pi-benchmark.md` (append-only: DEC-7, ledger, status block)

**Explicit non-goals:** editing `docs/build-stream/plans/2026-07-20-pi-full-replacement-master-plan.md`;
editing another architect's plan or any prior plan/ledger entry; modifying or deleting stale
gates, prior report bundles, or prior-lineage CF state; backend/product code changes; adding
approved endpoints or any non-DeepSeek route; a servable multi-endpoint full ensemble (owner
decision, separate spec); in-run judge calls of any kind; launching the Kimi judging session
from this pipeline; engine-default flips or rollout decisions.

<!-- /consensus-winning-plan:PI-BENCH-RETAKE-20260722 -->

## Decision log

<!-- consensus-winner-decision:PI-BENCH-RETAKE-20260722 -->
DEC-consensus-winner | 2026-07-23 | S1-plan | conductor
Context: three architect cross-votes completed
Decision: slot c selected from PI-BENCH-RETAKE-20260722-PLAN-C
Why: votes={"a": {"candidate_id": "db2ac00d234d86ff298074d9727a350342b4728c1eb73b1ed11db6250064385d", "task": "PI-BENCH-RETAKE-20260722-JUDGE-A", "vote": "c"}, "b": {"candidate_id": "db2ac00d234d86ff298074d9727a350342b4728c1eb73b1ed11db6250064385d", "task": "PI-BENCH-RETAKE-20260722-JUDGE-B", "vote": "c"}, "c": {"candidate_id": "80d2db4550151c9e45205e9cc44d4f5bfa2015d20954fbcd24b610f2c969ead6", "task": "PI-BENCH-RETAKE-20260722-JUDGE-C", "vote": "b"}}; tiebreak_used=False; plan_file=docs/build-stream/plans/pi-bench-retake-20260722-plan-c.md



DEC-5 | 2026-07-22 | S1-plan | owner + build-stream-conductor
Context: The machine has no working local/open-source model route for benchmark evaluation;
the next wave must remain resumable and must not exceed a one-dollar external spend cap.
Decision: Replan this lifecycle file only around B0 plus process-indexed waves B1…B_N,
where `N=max_processes` is discovered and recorded in B0. Route every live evaluation and
judge call through DeepSeek `deepseek-v4-pro`, disable all provider fallbacks, and enforce
one cumulative `budget_cap_usd=1.00` ledger across all waves, retries, and judges.
Why: This preserves the benchmark work packages while matching the machine's actual
provider availability, bounds concurrency, and makes an over-cap or uncertain-cost call
fail closed instead of silently switching models or overspending.

DEC-6 | 2026-07-22 | S2-execute | owner + build-stream-conductor
Context: the benchmark DUT/evaluation route and the judging harness have different roles.
Decision: route every live benchmark evaluation call through the configured Kimi route/model
under the cumulative `$1.00` evaluation ledger. After B_N is terminal, launch a separate
Build Stream Conductor judging session over durable artifacts; its cast may use Claude,
Codex, Kimi, or another configured judging harness, must not rerun the DUT, and must emit
the HTML, Markdown, JSON, and per-judgment outputs. Production Istara routing is unchanged.
Why: evaluation measures the requested model-routing behavior, while judging/reporting is
post-run analysis and should not be conflated with the evaluated provider or spend ledger.

DEC-7 | 2026-07-23 | S2-execute | build-stream-conductor + implementer (RT-0)
Context: The PI-BENCH-RETAKE-20260722 consensus winner (Plan C, §1.4) is a fresh, isolated
run. DEC-5/DEC-6 above still carry the prior lineage's Kimi-as-evaluation and judge-on-the-
DUT-ledger language, which contradicts the retake canon.
Decision: This DEC restates and pins the authoritative role canon for the retake, superseding
the conflicting Kimi-evaluation clauses in DEC-5/DEC-6 (which stay byte-identical as history):
  - DUT = Istara's two agentic arms (`engine=pi` and `engine=legacy`) through the API/
    dispatcher path (`AgenticDispatcher.ensemble`).
  - Evaluation provider = DeepSeek `deepseek-v4-pro` ONLY, via the one approved endpoint
    `pi-deepseek-default`. Local routes, Claude, Codex, Kimi, and every other provider are
    disabled for DUT traffic; there is no fallback route.
  - Budget = one cumulative crash-safe ledger, `budget_cap_usd=1.00`, shared by preflight,
    all waves, all MoA lanes, and all retries; no per-wave reset; closed at POST-N.
  - Kimi is NOT a benchmark/evaluation provider and makes NO in-run judge calls. Kimi is
    reserved for a separate, artifact-only post-run judging/report BSC session.
  - `deepseek_judge.py` / `judge_config.json` (judge = DUT model on the shared ledger) are
    superseded for this retake: no judge calls occur inside the B waves. Judging happens
    post-run, over frozen artifacts, off the DUT ledger.
Why: the stale Kimi-evaluation text would mis-route DUT spend and conflate the evaluation
provider with the post-run judge; pinning the canon keeps the money path DeepSeek-only and
the judging session cleanly separated.


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

### L-11 | 2026-07-22T15:33:47Z | S3-review | kimi-code/k3 | reviewer | Execution phase <!-- bsc-ledger:pi-eval-REVIEW -->
Did: independent code review of pi-eval-IMPL (B0-1 schema-first foundation, commit 349af3e0, 10 additive files). Reproduced the implementer's verification; probed the schema against the three master-plan citations (§5.5 :39-50 spine taxonomy, §10.2 :51-63 feature criteria_scores, §10.1.5 :121-126 paired stats). Added Findings register (F-1, F-2); created fixer task FIX-pi-eval-REVIEW-r1 (owner_role pi-eval-fixer, pipeline_run pi-eval).
Result: verdict FAIL — F-1 Major: `metrics.spine_phase` is an open object; the 10-phase research-validity taxonomy (intent, context, plan, tool_selection, execution, recovery, grounding, synthesis, review, governance) is enumerated nowhere, so the §5.5 "already defined in metrics-schema.json:39-50" citation dangles and typo'd phase keys validate (probe: {intnet:1.0, syntesis:0.5} → is_valid True). F-2 Minor: `metrics.additionalProperties:true` accepts typo'd axis keys. Everything else passes: 20/20 unit tests reproduced, ratchet 3/3 (A4), valid Draft 2020-12 schema, axis-1 vocabulary + axis-2 criteria + paired_stats match citations, diff strictly additive, no product code touched. pi-eval-REVIEW
Verified: `backend/.venv/bin/python -m pytest tests/pi_benchmark/ -q` → 20 passed; `python -m json.tool comparison-Istara-pi/metrics-schema.json` → parses OK; spine_phase typo-key probe → validates (the defect); `backend/.venv/bin/python -m pytest tests/pi_migration/test_count_to_zero.py -q` → 3 passed. CF evidence rows 1272-1276 (3×command, review_verdict, self_report).
Next: pi-eval-fixer resolves F-1/F-2 on FIX-pi-eval-REVIEW-r1 (schema + test_metrics_schema.py only); conductor spawns one delta re-review after all sibling fixes are terminal, then B0-2..B0-8 follow-ups.

## Ledger

### L-12 | 2026-07-22T15:37:11Z | S4-remediate | gpt-5.6-luna | remediator | Execution phase <!-- bsc-ledger:FIX-pi-eval-REVIEW-r1 -->
Did: remediated F-1 and F-2 in comparison-Istara-pi/metrics-schema.json and tests/pi_benchmark/test_metrics_schema.py; pinned all ten spine phases and made the metrics axis container strict.
Result: F-1 and F-2 fixed under FIX-pi-eval-REVIEW-r1; optional axis blocks remain compatible while unknown phase and axis keys are rejected.
Verified: `git diff --check` passed; `python -m json.tool comparison-Istara-pi/metrics-schema.json` passed; `backend/.venv/bin/python -m pytest tests/pi_benchmark/ -q` → 23 passed; `backend/.venv/bin/python -m pytest tests/pi_migration/test_count_to_zero.py -q` → 3 passed; post-change gate recorded inherited `secret_flow`/`unexpected_large_files` failures and no task-scope contract/import/dependency drift.
Next: conductor spawns the delta re-review for FIX-pi-eval-REVIEW-r1.

### L-13 | 2026-07-22T16:01:00Z | S3-review | kimi-code/k3 | reviewer | Execution phase <!-- bsc-ledger:REREV-pi-eval-REVIEW-r1 -->
Did: delta re-review of FIX-pi-eval-REVIEW-r1 (commit df45b8a1) against findings F-1/F-2 only — no full-review repeat. Verified the schema diff (metrics.additionalProperties true→false; spine_phase now enumerates the 10 phases intent/context/plan/tool_selection/execution/recovery/grounding/synthesis/review/governance, each number|null, additionalProperties:false), the three new contract tests (full-taxonomy positive, typo-phase negative `syntesis`, typo-axis negative `tool_cal ling`), and the immediate seams (golden fixture uses only valid axis keys; `tests/pi_benchmark/schema.py` validator covered by the suite; README references intact). Re-ran the fixer's verification and added a direct probe re-running the original finding's typo payloads.
Result: verdict **PASS** — both findings closed, 0 corrections. F-1: typo spine_phase keys now rejected, full 10-phase block validates; the schema is now the executable source of truth for the taxonomy. F-2: unknown axis keys rejected; forward-compat preserved via top-level `extensions`. Non-blocking observation: master plan §5.5 (:549) still cites `metrics-schema.json:39-50`; phases now live at :176-192 — pre-existing doc line-nit, not fix-induced, recommend a one-line touch-up in a future B0-x task. Untracked worktree files (debug_rereview.py, fix_payload.py, pi-eval-plan-b.md, recipe.toml mod) are outside the fix commit and were left untouched. REREV-pi-eval-REVIEW-r1
Verified: `git diff --check && python -m json.tool comparison-Istara-pi/metrics-schema.json && backend/.venv/bin/python -m pytest tests/pi_benchmark/ -q` → 23 passed; `backend/.venv/bin/python -m pytest tests/pi_migration/test_count_to_zero.py -q` → 3 passed; probe → typo spine_phase False / typo axis False / full 10-phase True. CF evidence rows 1289-1292 (2×command, review_verdict=pass, self_report).
Next: no finding tasks created (pass); conductor proceeds with B0-2..B0-8 follow-ups per the winning plan.

### L-14 | 2026-07-22T17:03:04Z | S2-execute | claude-opus-4-8 | executor | Execution phase <!-- bsc-ledger:pi-eval-B0-2-B1-final2 -->
Did: implemented the winning-plan **B0-2 … B0-8 offline asset layer + B1-1 contract execution** as strictly additive, tier-T0-safe apparatus (no product/security-sensitive source touched). New under `tests/pi_benchmark/`: `runner.py` (B0-4 paired runner — one record per `scenario×seed×engine`, mandatory `--tier`, offline model-free T0/T1 driver, **fail-closed owner gate for T2/T3**, per-record schema validation, manifest, RSS sampler, order-alternation); `scenarios/` (B0-5 — `canonical` re-hosts the 15 production-contract ids via an AST literal read of `test_scenario_coverage_map.COVERAGE`, `spine`/`a2a` behavioural packs `min_tier=T2`); `feature_criteria.py` (B0-6 — compiles all 86 `docs/features/inventory.json` features into axis-2 auto/manual criteria, none skipped); `judge.py` (B0-7 — judge≠DUT, blind + deterministic position-swap, rubric bank, `(scenario,run,rubric_version,judge_model)` cache, sha256-logged prompts, injected `judge_fn`); `probes/` (B0-8 — pure axis-9 scorers: protected-block survival, persona compliance, thinking-leak, injection resistance); 7 new test modules. B0-2: verified the pre-existing `--engine/--dry-run/--plan-only` plumbing in both node harnesses. B0-3: fixed `tests/benchmarks/long_horizon_runner.py` chunk-count-as-tokens bug (`:138 total_tokens += 1`) with a pure, tested `extract_total_tokens()` reading provider-reported usage (legacy per-dispatch capture already exists via `AgenticDispatcher`/`usage_ledger.build_usage_row`, W1). B1-1: canonical × both engines × T0/T1 baseline materialised to `.results/runs/b1-{t0,t1}` (gitignored). Updated `tests/pi_benchmark/README.md`.
Result: acceptance A1/A2/A3/A4/A5/A6 met at tier T0/T1; A2 (dry-run engine plumbing) and A5 (15 canonical × both × T0/T1 schema-valid, 0 unfiled not_runnable, stable outcome classes across seed repeats) verified. B2-B4 + live T2/T3 driver/judge-wiring/report generator remain **owner-gated behind G1/G2** and are explicit non-goals here (AGENTS.md live-model rule). Security benchmark gate NOT triggered — the diff touches no LLM-provider/registry/telemetry product code (the plan's §5 gate was tied to a registry telemetry edit that was deliberately not made). pi-eval-B0-2-B1-final2
Verified: `backend/.venv/bin/python -m pytest tests/pi_benchmark/ -q` → 64 passed; `... tests/pi_migration/test_count_to_zero.py -q` → 3 passed (ratchet 0, A4); `... tests/pi_production/test_scenario_coverage_map.py -q` → 1 passed (canonical-pack contract source); `node tests/simulation/run.mjs --engine pi|legacy --scenario 05-chat-interaction --dry-run` → exit 0, resolved `x-istara-agent-engine` header; `node tests/real_user_benchmark/run.mjs --engine both --plan-only` → exit 0, both engine plans; runner CLI T0+T1 → 90+90 schema-valid records; T2 without gate → refused (exit 3); `git diff --check` clean.
Next: stage exit — ready for independent code review of the B0-2..B0-8 + B1-1 diff; conductor spawns the reviewer, then owner gate G1 before any B2 (T2) run.

### L-15 | 2026-07-22T17:11:00Z | S2-execute | claude-opus-4-8 | executor | Execution phase <!-- bsc-ledger:pi-eval-B0-2-B1 -->
Did: CONVERGENCE entry. This task ran concurrently with sibling task pi-eval-B0-2-B1-final2 (same model, same shared worktree); the sibling committed the B0-2..B0-8 + B1-1 deliverable first (L-14, commit ff2721d7). I independently reviewed and verified that committed deliverable rather than re-authoring it, and contributed one delta already folded into ff2721d7: a `runner.py` sys.path bootstrap so the plan's §5 `python tests/pi_benchmark/runner.py ...` script-form command works (not only `python -m`). No code delta remains uncommitted; this entry commits only the lifecycle narrative for this task.
Result: converged — independent verification agrees with L-14 (64 pi_benchmark tests pass, ratchet 0, runner emits schema-valid paired records, spine/a2a counted not_runnable at T0, T2/T3 fail-closed without an owner-gate). Two honest residual nuances for the reviewer: (1) B0-3 registry-side capture — the dispatch-level ledger (usage_ledger.build_usage_row, W1) exists, but the *streaming* legacy arm (agentic/legacy.py `_stream_turn`) still appends empty usage so its tokens are estimated, not exact; surfacing provider usage from compute_registry_invocation.chat_stream (A3 estimate=false) needs a live provider response and is owner-gated follow-up. (2) Security benchmark gate not triggered — the committed diff touches no product LLM-provider/registry/auth surface. pi-eval-B0-2-B1
Verified: `backend/.venv/bin/python -m pytest tests/pi_benchmark/ -q` -> 64 passed; `... tests/pi_migration/test_count_to_zero.py -q` -> 3 passed (A4, ratchet 0); `python tests/pi_benchmark/runner.py --pack canonical --tier T0 --engine both --repeats 3` -> 90 ok records; spine,a2a@T0 -> 14 not_runnable; T2 refused exit 3; node dry-run/plan-only print the resolved engine plan (A2). CF 4×command + self_report evidence on pi-eval-B0-2-B1.
Next: stage exit — B0 assets committed and ready for independent code review (S3-review); reviewer verifies commit ff2721d7 + the two residual nuances above; conductor schedules the registry-side B0-3 follow-up and owner-gated B2/B3 (G1/G2).

### L-17 | 2026-07-22T17:47:49Z | S1-plan | gpt-5-codex | planner | Replanned execution
Did: Updated this lifecycle plan only (not the master plan) to replace the fixed B1–B4
process topology with B0 offline gating plus B1…B_N process-indexed waves. Added explicit
`N=max_processes` discovery, disjoint resumable shards, DeepSeek-only routing, Keychain
secret handling, and one cumulative `$1.00` budget ledger covering evaluations, judges,
retries, and reservations.
Result: The next run is fail-closed for missing/alternate providers, uncertain costs,
insufficient process slots, and budget exhaustion. The former contract/breadth/depth/report
work packages remain accounted for by the scheduler and are not silently removed.
Verified: `git diff --check` passed; lifecycle status, wave topology, task table, acceptance
criteria, verification commands, risks, gates, non-goals, DEC-5, and this ledger entry are
present in `docs/build-stream/2026-07-22-pi-benchmark.md`.
Next: Independent review of this plan update; then execute B0 with the owner-approved
DeepSeek-only `$1.00` envelope and an explicit recorded `N`.

### L-18 | 2026-07-22T19:10:16Z | S2-execute | kimi-code/k3 | executor | Execution phase <!-- bsc-ledger:PI-BENCH-MOA-20260722-IMPL -->
Did: completed the DeepSeek-only remaining-wave apparatus, building on the inherited uncommitted lane-A/lane-B worktree state (a prior attempt's partial implementation). Fixed the 3 failing tests: moa topology sentinel dedupe (test used 3 distinct sentinel instances while asserting identity-dedupe semantics — now one shared sentinel), and runner wave-mode Lane A imports moved to importlib so sys.modules-injected fakes are honored even when the real submodules are already bound on the package. Fixed a real seam bug: deepseek_judge now unpacks DeepSeekProvider.chat's (content, usage) tuple (+regression test) — against the real provider the judge would previously have stringified the tuple and failed every verdict. Fixed record identity: live records now follow the manifest unit's own phase and record_id (not the wave's CLI --phase), so file name, ledger call id, and record_id agree (resume keys on the file stem). Added the B0 `--plan-only` scheduling gate to runner.py (build run units, shard into --max-processes disjoint shards, write the immutable content-hashed manifest, idempotent resume, conflict refusal, exit without dispatch; fails closed when --max-processes is missing) and tests/pi_benchmark/verify_budget_ledger.py (replays the durable ledger: known row types, no orphan commits, spend <= cap, --close seals) with 14 new tests. Updated tests/pi_benchmark/README.md and the runner docstring.
Result: PI-BENCH-MOA-20260722-IMPL offline apparatus complete: B0 scheduling + immutable shard manifest + crash-safe $1.00 ledger, resumable wave mode, real dispatcher-path live driver (DeepSeek deepseek-v4-pro only), MoA self_moa/full_ensemble downgrade detection (downgrade => not_runnable, never success), role-separated DeepSeek judge on the shared ledger, and report generation from durable artifacts. NO live dispatch was performed and live completion is NOT claimed (owner gates G1/G2; AGENTS.md live-model rule). Security benchmark gate not triggered: the diff touches only tests/ benchmark apparatus, no product provider/registry/telemetry code. Reverted accidental comparison-Istara-pi/README.md + results_summary.md mutations from a report smoke run (they had been regenerated from the old synthetic records).
Verified: `backend/.venv/bin/python -m pytest tests/pi_benchmark/ -q` -> 154 passed; `... tests/pi_migration/test_count_to_zero.py -q` -> 3 passed (ratchet 0); `... tests/pi_production/ -q` -> 346 passed; `... tests/pi_production/test_w7_validation.py tests/test_validation_project_scope.py tests/pi_production/test_scenario_coverage_map.py tests/pi_production/test_scenario_research_spine.py -q` -> 28 passed (Research Spine route/coverage); `git diff --check` clean; CLI smoke: `--plan-only` wrote an immutable 15-unit/2-shard manifest and resumed it unchanged on re-run; `--wave 1` without an owner gate refused exit 3; `verify_budget_ledger.py --runs ... --close` sealed and passed (spent=$0.0042 <= $1.00); `scripts/pi_benchmark_report.py` generated scorecard/report.md/report.html from durable run records.
Next: stage exit — ready for independent code review (pi-bench-moa-20260722-code-reviewer). Live B1...B_N wave execution and the G0/G1 owner approvals remain owner-gated.

### L-19 | 2026-07-22T19:19:41Z | S3-review | gpt-5.6-sol | reviewer | Execution phase <!-- bsc-ledger:PI-BENCH-MOA-20260722-REVIEW -->
Did: independently reviewed commit 4850b035 and the implementer evidence; inspected the scheduler, ledger, provider, dispatcher, MoA, judge, runner, tests, and Research Spine seams; created five fixer tasks for F-3 through F-7. No production or benchmark code was changed.
Result: verdict FAIL on PI-BENCH-MOA-20260722-REVIEW. F-3 through F-6 are Blockers: real B0 manifests cannot enter wave execution; partial MoA coder success is reported reconciled; MoA does not preserve paired-engine/DeepSeek-only route identity and performs unbudgeted embedding work; and the external ledger is not a hard pre-dispatch one-dollar cap. F-7 is Major: new task-scope Python import cycles fail the architecture gate.
Verified: `backend/.venv/bin/python -m pytest tests/pi_benchmark/ -q` -> 154 passed; adversarial scheduler->wave probe -> `AttributeError: str has no attribute unit_id`; partial full_ensemble probe -> `degraded=False,status=reconciled,coders=1,routes=3`; focused migration/Research Spine suite -> 27 passed; `git diff --check` -> passed; `python scripts/security_benchmark.py --fail-on-threshold` -> 28/28; CF gate after -> failed with new import cycles and zero route/type/contract/graphql/generated drift.
Next: remediate F-3 through F-7 in the five linked FIX tasks; stage exit: fail verdict, evidence, findings, and fixer tasks recorded for conductor barrier + delta re-review.

### L-20 | 2026-07-22T19:24:49Z | S4-remediate | gpt-5.6-luna | remediator | Execution phase <!-- bsc-ledger:FIX-PI-BENCH-MOA-20260722-REVIEW-r1-wave -->
Did: fixed F-3 in `tests/pi_benchmark/runner.py` and added direct scheduler-to-wave integration coverage in `tests/pi_benchmark/test_runner.py`; the runner now resolves string shard IDs through the manifest `units` table while preserving dict/object compatibility.
Result: F-3 fixed under FIX-PI-BENCH-MOA-20260722-REVIEW-r1-wave; real B0 manifests no longer crash before dispatch.
Verified: `python -m pytest tests/pi_benchmark -q` -> 155 passed; `python -m compileall -q tests/pi_benchmark/runner.py tests/pi_benchmark/test_runner.py` -> passed; `compass-forge gate after --task FIX-PI-BENCH-MOA-20260722-REVIEW-r1-wave --summary` -> gate status fail with 0 new failures and 0 actionable failures, inherited `python_import_cycles`/`secret_flow`/`unexpected_large_files` only.
Next: sibling fixer tasks F-4 through F-7, then one delta re-review after all fixer tasks are terminal.

### L-21 | 2026-07-22T19:27:35Z | S4-remediate | gpt-5.6-luna | remediator | Execution phase <!-- bsc-ledger:FIX-PI-BENCH-MOA-20260722-REVIEW-r1-moa -->
Did: fixed F-4 in `tests/pi_benchmark/moa.py` and `tests/pi_benchmark/live_driver.py`; added partial self-MoA/full-ensemble contract and live-driver coverage in `tests/pi_benchmark/test_moa.py` and `tests/pi_benchmark/test_live_driver.py`. Successful `route_evidence` now determines served routes, requested coder/route width is required, and consensus score/confidence survive the live capture shim.
Result: F-4 fixed under FIX-PI-BENCH-MOA-20260722-REVIEW-r1-moa; selected-but-failed endpoint ids remain provenance only, partial MoA records are `not_runnable`, and consensus evidence is retained.
Verified: `backend/.venv/bin/python -m pytest tests/pi_benchmark/test_moa.py tests/pi_benchmark/test_live_driver.py -q` -> 34 passed; `backend/.venv/bin/python -m pytest tests/pi_benchmark/ -q` -> 159 passed; `python -m compileall -q tests/pi_benchmark/moa.py tests/pi_benchmark/live_driver.py` -> passed; `git diff --check` -> passed; `compass-forge gate after --task FIX-PI-BENCH-MOA-20260722-REVIEW-r1-moa --summary` -> fail with 0 new failures, inherited `python_import_cycles`/`secret_flow`/`unexpected_large_files`, route/type/contract/graphql/generated drift 0.
Next: sibling fixer tasks F-5 through F-7, then one delta re-review after all fixer tasks are terminal.

### L-22 | 2026-07-22T19:29:52Z | S4-remediate | gpt-5.6-luna | remediator | Execution phase <!-- bsc-ledger:FIX-PI-BENCH-MOA-20260722-REVIEW-r1-budget -->
Did: fixed F-6 across `tests/pi_benchmark/budget_ledger.py`, `tests/pi_benchmark/verify_budget_ledger.py`, `tests/pi_benchmark/live_driver.py`, and the validation dispatch seam in `backend/app/core/validation.py`; added adversarial ledger/verifier tests and bound-forwarding coverage.
Result: F-6 fixed under FIX-PI-BENCH-MOA-20260722-REVIEW-r1-budget. Reservations now use a hard finite non-negative cap with unique call ids; commits/releases require one outstanding reservation, commits cannot exceed the reservation, and malformed durable rows are rejected by the verifier. `run_live_unit` forwards the reserved `max_tokens` bound to plain and MoA dispatch paths, including validation fallback routes.
Verified: `backend/.venv/bin/python -m pytest tests/pi_benchmark/test_budget_ledger.py tests/pi_benchmark/test_verify_budget_ledger.py -q` -> 25 passed; `backend/.venv/bin/python -m pytest tests/pi_production/test_w7_validation.py tests/test_validation_project_scope.py -q` -> 26 passed; direct dispatch probe with `max_tokens=23` -> passed; `git diff --check` -> passed; Python compile checks -> passed. Full `tests/pi_benchmark/` remains blocked by sibling F-7's in-progress `runner.py`/`recording.py` refactor (pre-existing missing helper import and injection API drift), not by this task's focused surface.
Next: sibling F-5 and F-7, then delta re-review; stage exit: F-6 fixed with focused evidence and handoff ready.

### L-23 | 2026-07-22T19:32:42Z | S1-plan | claude-fable-5 | architect | Role-correction planning <!-- bsc-ledger:PI-BENCH-ROLE-CORRECTION-20260722-PLAN-A -->
Did: authored independent consensus plan A at docs/build-stream/plans/pi-bench-role-correction-20260722-plan-a.md (209 lines: verified role-ambiguity audit, five-role model, correction design for the lifecycle winning-plan section + DEC-7 supersession + work-order tighten, RC-1..RC-6 task table, AC-1..AC-7 acceptance, exact grep/diff verification battery, risks incl. the deepseek_judge.py code/doc mismatch follow-up, rollback). No lifecycle plan content or code edited.
Result: plan slot A ready for consensus judging; key audit: 14 Kimi-as-evaluation occurrences in the embedded winning plan (task table, A3/A4/A7, section-5 commands, risks, G0/G1, non-goals, DEC-6) plus DEC-5's "and judge call through DeepSeek" clause; execution work-order pi-benchmark-deepseek-moa-execution.md confirmed already role-correct, needing only pack-list/pointer tightening; PI-BENCH-ROLE-CORRECTION-20260722-PLAN-A
Verified: git diff --check passed; grep -iE role-ambiguity audit over lifecycle + work-order (14 kimi-eval hits at lines 202-500, deepseek-judge clause at :489); wc -l plan = 209; CF evidence rows 1361-1364 (3x command, self_report)
Next: consensus judges vote on plan slots a/b/c; winning plan's implementer executes RC-1..RC-6

### L-24 | 2026-07-22T19:35:04Z | S1-plan | gpt-5.6-sol | planner | pi-bench-role-correction-20260722-architect-b <!-- bsc-ledger:PI-BENCH-ROLE-CORRECTION-20260722-PLAN-B -->
Did: pi-bench-role-correction-20260722-architect-b stage on task PI-BENCH-ROLE-CORRECTION-20260722-PLAN-B (harness fallback entry; the model did not append one).
Result: task PI-BENCH-ROLE-CORRECTION-20260722-PLAN-B finished; worktree head b13b238c.
Verified: see Compass Forge evidence rows on PI-BENCH-ROLE-CORRECTION-20260722-PLAN-B (command + self_report + stage_attribution).
Next: conductor advances the pipeline on evidence.

### L-25 | 2026-07-22T19:36:36Z | S4-remediate | gpt-5.6-luna | remediator | Execution phase <!-- bsc-ledger:FIX-PI-BENCH-MOA-20260722-REVIEW-r1-gate -->
Did: fixed F-7 by moving shared benchmark record/provenance/atomic-write helpers into `tests/pi_benchmark/schema.py`, removing the `live_driver -> runner -> live_driver` dependency cycle while preserving runner/live behavior; touched `tests/pi_benchmark/schema.py`, `tests/pi_benchmark/runner.py`, and `tests/pi_benchmark/live_driver.py`.
Result: F-7 fixed under FIX-PI-BENCH-MOA-20260722-REVIEW-r1-gate; the task-scope post-change architecture comparison reports zero new failures and zero actionable failures. The unrelated live-driver injection-API failure remains outside this cycle-only task.
Verified: `python -m pytest tests/pi_benchmark/test_runner.py tests/pi_benchmark/test_moa.py tests/pi_benchmark/test_live_driver.py -q -k 'not dispatch_unit_moa_uses_pinned_engine_and_never_embeddings'` -> 57 passed, 1 deselected; `python -m pytest tests/pi_benchmark/test_b1_contract.py -q` -> 5 passed; `python -m compileall -q tests/pi_benchmark/schema.py tests/pi_benchmark/live_driver.py tests/pi_benchmark/runner.py` -> passed; `git diff --check` -> passed; `compass-forge gate after --task FIX-PI-BENCH-MOA-20260722-REVIEW-r1-gate --summary` -> fail with 0 new failures, 0 actionable failures, inherited cycle/secret/large-file debt only.
Next: complete sibling F-5, then delta re-review; stage exit: F-7 fixed with focused evidence and handoff ready.

### L-26 | 2026-07-22T19:38:20Z | S4-remediate | gpt-5.6-luna | remediator | Execution phase <!-- bsc-ledger:FIX-PI-BENCH-MOA-20260722-REVIEW-r1-routing -->
Did: fixed F-5 in `tests/pi_benchmark/live_driver.py` and `tests/pi_benchmark/test_live_driver.py`; MoA now uses the benchmark-safe dispatcher path with `engine=unit.engine`, a pinned approved DeepSeek endpoint/model, deterministic local consensus without embedding dispatch, rejected-route evidence, and provenance fingerprints derived from the served redacted route. Added regression coverage for paired-engine forwarding, embedding avoidance, unapproved-route rejection, and null provenance on rejected routes.
Result: F-5 open -> fixed under FIX-PI-BENCH-MOA-20260722-REVIEW-r1-routing. Full ensembles remain explicitly degraded on the single approved route instead of discovering local or unrelated endpoints; no live model or network call was made.
Verified: `python -m pytest tests/pi_benchmark/test_live_driver.py tests/pi_benchmark/test_moa.py -q` -> 38 passed; `python -m ruff check tests/pi_benchmark/live_driver.py tests/pi_benchmark/test_live_driver.py tests/pi_benchmark/moa.py tests/pi_benchmark/test_moa.py` -> passed; `python -m compileall -q tests/pi_benchmark/live_driver.py tests/pi_benchmark/test_live_driver.py` -> passed; `git diff --check` -> passed; `compass-forge gate after --task FIX-PI-BENCH-MOA-20260722-REVIEW-r1-routing --summary` -> no new/actionable routing-scope failures, with inherited debt and the sibling ledger-suite failures recorded in CF evidence. The full `tests/pi_benchmark` suite remains 170 passed/2 failed in sibling F-6 provider reservation tests.
Next: stage exit: F-5 fixed; sibling barrier and one delta re-review remain.

### L-27 | 2026-07-22T19:38:59Z | S1-plan | claude-fable-5 | architect | Role-correction planning <!-- bsc-ledger:PI-BENCH-ROLE-CORRECTION-20260722-REPLAN-A-r1 -->
Did: repaired consensus plan A (revision r1) at docs/build-stream/plans/pi-bench-role-correction-20260722-plan-a.md (242 lines) — re-verified every r0 grounding citation by fresh grep on @ b13b238c (14 Kimi-as-evaluation regions at :202-500, DEC-5 judge-through-DeepSeek at :488-489, DEC-6 at :497-500, work-order role text at :26-31/:38/:76-79) and closed the r0 residual imprecisions: exact pack arithmetic (work-order :71-73 has 6/7 brief packs, lifecycle :42-43 slice list keeps depth as a mapped legacy label), work-order :38 no-ledger-draw rule is explicit not implied, deepseek_judge.py code/doc mismatch pinned to :6 and :84-89, findings drift refreshed (F-3/F-4/F-6 fixed; F-5/F-7 open). No lifecycle plan content or code edited.
Result: plan slot A ready for consensus judging (r1); PI-BENCH-ROLE-CORRECTION-20260722-REPLAN-A-r1
Verified: git diff --check passed; grep re-audit over lifecycle + work-order + deepseek_judge.py (all citations hold at b13b238c); wc -l plan = 242; scope audit — only the plan file modified by this stage; CF evidence rows 1380-1383 (3x command, self_report)
Next: consensus judges vote on plan slots a/b/c; winning plan's implementer executes RC-1..RC-6

### L-28 | 2026-07-22T19:39:47Z | S1-plan | kimi-code/k3 | planner | pi-bench-role-correction-20260722-architect-c <!-- bsc-ledger:PI-BENCH-ROLE-CORRECTION-20260722-PLAN-C -->
Did: pi-bench-role-correction-20260722-architect-c stage on task PI-BENCH-ROLE-CORRECTION-20260722-PLAN-C (harness fallback entry; the model did not append one).
Result: task PI-BENCH-ROLE-CORRECTION-20260722-PLAN-C finished; worktree head e1f9d8a7.
Verified: see Compass Forge evidence rows on PI-BENCH-ROLE-CORRECTION-20260722-PLAN-C (command + self_report + stage_attribution).
Next: conductor advances the pipeline on evidence.

### L-29 | 2026-07-22T19:42:00Z | S1-plan | gpt-5.6-sol | planner | pi-bench-role-correction-20260722-architect-b <!-- bsc-ledger:PI-BENCH-ROLE-CORRECTION-20260722-REPLAN-B-r1 -->
Did: pi-bench-role-correction-20260722-architect-b stage on task PI-BENCH-ROLE-CORRECTION-20260722-REPLAN-B-r1 (harness fallback entry; the model did not append one).
Result: task PI-BENCH-ROLE-CORRECTION-20260722-REPLAN-B-r1 finished; worktree head 5b9b5d56.
Verified: see Compass Forge evidence rows on PI-BENCH-ROLE-CORRECTION-20260722-REPLAN-B-r1 (command + self_report + stage_attribution).
Next: conductor advances the pipeline on evidence.

### L-30 | 2026-07-22T19:42:46Z | S1-plan | claude-fable-5 | judge | pi-bench-role-correction-20260722-judge-a <!-- bsc-ledger:PI-BENCH-ROLE-CORRECTION-20260722-JUDGE-A -->
Did: consensus judge slot a — read both candidate plans (pi-bench-role-correction-20260722-plan-b.md r1 by gpt-5.6-sol, plan-c.md by kimi-code/k3) and spot-verified their factual claims against this lifecycle and tests/pi_benchmark/runner.py; edited only this lifecycle file (this append).
Result: plan_vote for slot c recorded (CF evidence 1405) — Plan C's line-anchored stale-Kimi audit fully verified against the file, DEC-7 content pre-specified, tests/pi_benchmark/README.md pointer in scope, explicit F-5/F-7 collision avoidance; Plan B strong on MoA requested-vs-served spec and judging barrier but unanchored audit and no README annotation; PI-BENCH-ROLE-CORRECTION-20260722-JUDGE-A
Verified: grep -n -i kimi docs/build-stream/2026-07-22-pi-benchmark.md (all Plan C cited instances at :202,:307-312,:327-339,:357-395,:422-424,:449-452,:465-466 present); sed DEC-5/DEC-6 (judge-on-ledger and Kimi-eval contradictions confirmed); runner.py ONLY_PROVIDER/ONLY_MODEL parser.error enforcement confirmed; CF evidence rows 1404-1406 (command, plan_vote, self_report)
Next: conductor tallies judge votes a/b/c and advances the winning plan to implementation

### L-31 | 2026-07-22T19:43:35Z | S1-plan | gpt-5.6-sol | judge | pi-bench-role-correction-20260722-judge-b <!-- bsc-ledger:PI-BENCH-ROLE-CORRECTION-20260722-JUDGE-B -->
Did: consensus judge slot b read exactly candidate plan A r1 by claude-fable-5 and candidate plan C by kimi-code/k3; compared currency, scope discipline, role reconciliation, verification, concurrency safety, and residual-debt handling. Edited only this lifecycle file for the required append and status projection.
Result: voted for slot a on PI-BENCH-ROLE-CORRECTION-20260722-JUDGE-B (CF plan_vote evidence 1410). Plan A is newer, limits the primary correction to the lifecycle and authoritative work-order, reconciles the seven packs precisely, preserves append-only history, and explicitly isolates the DeepSeek-judge/shared-ledger code contradiction as follow-up debt; Plan C is coherent but uses an older snapshot and expands the main diff into tests/pi_benchmark/README.md.
Verified: full reads of docs/build-stream/plans/pi-bench-role-correction-20260722-plan-a.md and docs/build-stream/plans/pi-bench-role-correction-20260722-plan-c.md passed; CF evidence rows 1408, 1410, and 1411 (command, plan_vote, self_report).
Next: stage exit: judge-b vote and required evidence recorded; conductor tallies votes and advances the winning plan.

### L-32 | 2026-07-22T19:44:58Z | S1-plan | claude-fable-5 | architect | Role-correction planning <!-- bsc-ledger:PI-BENCH-ROLE-CORRECTION-20260722-REPLAN-A-r2 -->
Did: repaired consensus plan A (revision r2) at docs/build-stream/plans/pi-bench-role-correction-20260722-plan-a.md (268 lines) — re-verified every r1 grounding citation by fresh grep at HEAD 1777753c (all Kimi-as-evaluation regions :202-500, DEC-5 judge clause :488-489, DEC-6 :497-500, wave-contract slice list :42-43, work-order roles/packs :24-31/:36-38/:71-83) and folded in post-r1 drift: ledger advanced to L-29 with harness fallback entries L-28/L-29 and a dangling Status Block ledger: L-30 reference; deepseek_judge.py docstring rewritten to explicitly declare the judge-IS-DUT-model shared-ledger policy (:3-8, make_deepseek_judge_fn :84-90), so the plan's code/doc-mismatch risk row and its follow-up CF task now also cover superseding that docstring/separation_note policy text; F-3..F-7 all read fixed in the register. No lifecycle plan content or code edited.
Result: plan slot A ready for r2 consensus judging; PI-BENCH-ROLE-CORRECTION-20260722-REPLAN-A-r2
Verified: git diff --check passed; grep re-audit over lifecycle + work-order + deepseek_judge.py (all citations hold at 1777753c); wc -l plan = 268; scope audit — only the plan file modified by this stage; CF evidence rows 1414-1416 (2x command, self_report)
Next: consensus judges a/b/c vote on plan slots; winning plan's implementer executes RC-1..RC-6

### L-33 | 2026-07-22T19:46:36Z | S1-plan | gpt-5.6-sol | planner | pi-bench-role-correction-20260722-architect-b <!-- bsc-ledger:PI-BENCH-ROLE-CORRECTION-20260722-REPLAN-B-r2 -->
Did: pi-bench-role-correction-20260722-architect-b stage on task PI-BENCH-ROLE-CORRECTION-20260722-REPLAN-B-r2 (harness fallback entry; the model did not append one).
Result: task PI-BENCH-ROLE-CORRECTION-20260722-REPLAN-B-r2 finished; worktree head 1ff29c48.
Verified: see Compass Forge evidence rows on PI-BENCH-ROLE-CORRECTION-20260722-REPLAN-B-r2 (command + self_report + stage_attribution).
Next: conductor advances the pipeline on evidence.

### L-34 | 2026-07-22T19:50:29Z | S1-plan | kimi-code/k3 | judge | pi-bench-role-correction-20260722-judge-c <!-- bsc-ledger:PI-BENCH-ROLE-CORRECTION-20260722-JUDGE-C -->
Did: consensus judge slot c — read exactly the two assigned candidate files (plan A by claude-fable-5, read at r1 then re-read at r2 after L-32 landed mid-stage; plan B r1 by gpt-5.6-sol); spot-verified their load-bearing claims against this lifecycle (:488-489 DEC-5 judge clause, 11 Kimi-as-evaluation residuals), tests/pi_benchmark/deepseek_judge.py (:3-8 shared-ledger judge now declared as explicit policy, make_deepseek_judge_fn :84-90 sharing the evaluation ledger), and the conductor-instructions docs (role-correction brief + execution work-order both exist). Edited only this lifecycle file (this append + Status Block).
Result: plan_vote for slot a recorded on PI-BENCH-ROLE-CORRECTION-20260722-JUDGE-C. Plan A r2 wins on audit precision/currency (triple-re-verified line anchors; r2 tracks live drift incl. the deepseek_judge.py docstring hardening and observed ledger-numbering races with a re-read-under-lock mandate) and surgical scope (identity-swap + DEC-7 supersession + work-order tighten + exact seven-pack arithmetic). Plan B's normative role table, terminal judging barrier, and requested-vs-served MoA provenance are stronger contract machinery but its audit is unanchored and one revision staler, and its extras exceed the role-correction brief. Vote tally now: judge-a -> slot c, judge-b -> slot a, judge-c -> slot a.
Verified: grep DEC-5 pin -> :488-489 confirmed; Kimi-eval residual grep -> 11 matches; sed deepseek_judge.py :1-10/:84-92 -> shared-ledger policy + ledger-sharing judge_fn confirmed at HEAD 070f9dd2; ls conductor-instructions -> both docs present; CF evidence rows 1427 (command), 1428 (plan_vote), 1429 (self_report).
Next: conductor tallies judge votes (slot a leads 2-1) and advances the winning role-correction plan to implementation; stage exit: plan_vote + self_report + command evidence recorded.

### L-35 | 2026-07-22T20:01:52Z | S1-plan | gpt-5.6-sol | planner | pi-bench-recovery-20260722-architect-b <!-- bsc-ledger:PI-BENCH-RECOVERY-20260722-PLAN-B -->
Did: pi-bench-recovery-20260722-architect-b stage on task PI-BENCH-RECOVERY-20260722-PLAN-B (harness fallback entry; the model did not append one).
Result: task PI-BENCH-RECOVERY-20260722-PLAN-B finished; worktree head 9cfe3304.
Verified: see Compass Forge evidence rows on PI-BENCH-RECOVERY-20260722-PLAN-B (command + self_report + stage_attribution).
Next: conductor advances the pipeline on evidence.

### L-36 | 2026-07-22T20:02:09Z | S1-plan | claude-fable-5 | architect | Recovery planning <!-- bsc-ledger:PI-BENCH-RECOVERY-20260722-PLAN-A -->
Did: authored independent recovery consensus plan A at docs/build-stream/plans/pi-bench-recovery-20260722-plan-a.md (293 lines: invalid-consensus root-cause table with vote timestamps vs plan-revision timestamps, worktree/CF/conductor residue inventory, reuse verdict "content yes / state no", R1 quarantine-commit + R2 state-hygiene + R3 fresh-anchor role-correction design, RV-0..RV-6 task table with G-R1/G-R2 owner gates, AC-1..AC-7, exact verification commands, risks, rollback to 75db26f5). No lifecycle plan content, code, or prior ledger entry edited.
Result: plan slot A ready for recovery consensus judging; key audit: no consensus_result row exists for PI-BENCH-ROLE-CORRECTION-20260722 (only plan_vote rows 1405/1410/1428 against mixed plan revisions — A moved r1->r2 mid-vote at L-32, B r2 landed post-vote and is still uncommitted); stale CF rows IMPL/REVIEW open + REPLAN-C-r1 claimed by stopped actor; stale conductor markers "active-run (1).json"/"escalation (1|2).json" identified; single live conductor pid 91892 on the recovery prefix confirmed; DUT=Istara arms, DeepSeek=evaluation backend via dispatcher under $1.00, MoA=measured, Kimi=post-run judge retained verbatim in plan section 0; PI-BENCH-RECOVERY-20260722-PLAN-A
Verified: git status/diff residue audit; sqlite task_evidence query (zero consensus_result rows); conductor pid/marker audit (pid 91892 alive, prefix PI-BENCH-RECOVERY-20260722); git diff --check clean; wc -l plan = 293; CF evidence rows recorded 20:01:11-20:01:41Z (4x command, self_report)
Next: recovery consensus judges vote on plan slots a/b/c; G-R1 owner gate before any implementation

### L-37 | 2026-07-22T20:09:14Z | S1-plan | claude-fable-5 | architect | Recovery planning <!-- bsc-ledger:PI-BENCH-RECOVERY-20260722-REPLAN-A-r1 -->
Did: repaired recovery consensus plan A (revision r1) at docs/build-stream/plans/pi-bench-recovery-20260722-plan-a.md (341 lines) — re-verified every r0 grounding claim by fresh commands at HEAD 9c45a42a (no r0 factual errors) and folded in post-r0 drift: recovery plans A/B now committed (9c45a42a L-36, 9cfe3304 + fallback L-35) so the uncommitted-candidate risk narrows to slot C (claimed, in-flight; its plan file appeared untracked mid-stage); AC-2 append-only range widened L-1..L-34 -> L-1..L-36; recovery pipeline's own pre-created IMPL/REVIEW open rows explicitly exempted from RV-3 cancels and AC-5; consensus-invalidity proof strengthened (full task_evidence scan: 6 consensus_result rows repo-wide, all earlier pipelines, 0 for ROLE-CORRECTION; recovery plan_vote count 0 at authoring); conductor heartbeat refreshed 20:03:18Z, pid 91892, same prefix. No lifecycle plan content, code, or prior ledger entry edited.
Result: plan slot A ready for recovery consensus judging (r1); reuse verdict unchanged — prior correction artifacts reusable as content not state; DUT/DeepSeek/MoA/post-run-Kimi roles retained verbatim in plan section 0; PI-BENCH-RECOVERY-20260722-REPLAN-A-r1
Verified: grep kimi-eval + DEC-5/6/7 anchor re-audit at 9c45a42a (regions :202-466 hold, DEC-5 clause :489, no DEC-7); sqlite consensus_result full listing (0 for role-correction) + stale-row recheck (IMPL/REVIEW open, REPLAN-C-r1 claimed); conductor pid/marker audit (91892 alive, stale (1)/(2) markers present); git diff --check clean; wc -l plan = 341; scope audit — only the plan file modified by this stage; CF evidence rows 1446-1449 (3x command, self_report)
Next: recovery consensus judges vote on plan slots a/b/c; conductor seals consensus_result; G-R1 owner gate before any implementation

### L-38 | 2026-07-22T20:09:18Z | S1-plan | kimi-code/k3 | planner | pi-bench-recovery-20260722-architect-c <!-- bsc-ledger:PI-BENCH-RECOVERY-20260722-PLAN-C -->
Did: pi-bench-recovery-20260722-architect-c stage on task PI-BENCH-RECOVERY-20260722-PLAN-C (harness fallback entry; the model did not append one).
Result: task PI-BENCH-RECOVERY-20260722-PLAN-C finished; worktree head 68dcd159.
Verified: see Compass Forge evidence rows on PI-BENCH-RECOVERY-20260722-PLAN-C (command + self_report + stage_attribution).
Next: conductor advances the pipeline on evidence.

### L-39 | 2026-07-22T20:11:15Z | S1-plan | claude-fable-5 | judge | pi-bench-recovery-20260722-judge-a <!-- bsc-ledger:PI-BENCH-RECOVERY-20260722-JUDGE-A -->
Did: Consensus judge slot a — read recovery candidate plans B (gpt-5.6-sol, plan-b.md) and C (kimi-code/k3, plan-c.md); spot-verified plan C's lifecycle stale-text line anchors (307/312/327/330/339/374-393/422/424/449/465-466/489 all match) and its six-of-seven-packs finding in pi-benchmark-deepseek-moa-execution.md. No plan edited.
Result: plan_vote for slot c (CF evidence 1459): C is evidence-grounded and operational (void-tally proof, orphan-task cancellation, hygiene commit for untracked governing docs, fresh-anchor rule); B is sound but abstract and internally tense on untracked-path scope. PI-BENCH-RECOVERY-20260722-JUDGE-A
Verified: grep -n -iE 'provider kimi|kimi[- ]only|kimi evaluation|configured-kimi-model|judge call through deepseek' docs/build-stream/2026-07-22-pi-benchmark.md (14 active-text regions confirmed); sed -n 68,85p docs/build-stream/conductor-instructions/pi-benchmark-deepseek-moa-execution.md (six packs listed, MoA route/downgrade only as judge dimension). No tests run — judging-only stage, no code touched.
Next: remaining judges vote; conductor tallies and seals consensus_result; G-R1 owner gate before implementation.

### L-40 | 2026-07-22T20:12:43Z | S3-review | gpt-5.6-sol | reviewer | Recovery consensus <!-- bsc-ledger:PI-BENCH-RECOVERY-20260722-JUDGE-B -->
Did: Read candidate plans A and C exactly as assigned; recorded judge-b plan_vote for slot a; no plan or code files changed.
Result: Slot a selected for its newer-state grounding, exact RECOVERY-task exclusion, and plan-freeze safeguard; PI-BENCH-RECOVERY-20260722-JUDGE-B.
Verified: `shasum -a 256 docs/build-stream/plans/pi-bench-recovery-20260722-plan-a.md docs/build-stream/plans/pi-bench-recovery-20260722-plan-c.md` passed (A d221d818..., C 8a014ff5...); CF evidence IDs 1463 command, 1464 plan_vote, 1465 self_report.
Next: stage exit: vote, self-report, command evidence, and durable lifecycle handoff recorded.

### L-41 | 2026-07-22T20:15:02Z | S1-plan | claude-fable-5 | architect | Recovery planning <!-- bsc-ledger:PI-BENCH-RECOVERY-20260722-REPLAN-A-r2 -->
Did: repaired recovery consensus plan A (revision r2) at docs/build-stream/plans/pi-bench-recovery-20260722-plan-a.md (361 lines) — re-verified every r1 grounding claim by fresh commands at HEAD c53e0d01 (no r1 factual errors) and folded in post-r1 drift: all three recovery candidates now committed (plan C at 02595094, task done, fallback ledger L-38; uncommitted-candidate risk retired); recovery judging started mid-repair (plan_vote rows 1459 judge-a->slot c read B+C, 1464 judge-b->slot a read A r1 + C; judge-c in flight) so the r1 "zero plan_vote" claim is historical and the consensus-recurrence risk row now mandates revision-sha-explicit tallying; AC-2 protected range redefined as every-entry-at-IMPL-dispatch (L-1..L-39 at authoring); plan C's six-of-seven-packs work-order gap independently confirmed (pi-benchmark-deepseek-moa-execution.md :71-77 lists six packs, MoA route/downgrade only a judge dimension at :81) and anchored into R3 step 3; stale ROLE-CORRECTION rows (IMPL/REVIEW open, REPLAN-C-r1 claimed), stale (1)/(2) conductor markers, and 6-repo-wide/0-role-correction consensus_result counts unchanged; conductor pid 91892 alive, heartbeat 20:10:12Z, prefix PI-BENCH-RECOVERY-20260722. No lifecycle plan content, code, or prior ledger entry edited.
Result: plan slot A ready for recovery consensus judging (r2); reuse verdict unchanged — prior correction artifacts reusable as content not state; DUT=Istara arms / DeepSeek-via-dispatcher under $1.00 / MoA measured / Kimi post-run judge retained verbatim in plan section 0; PI-BENCH-RECOVERY-20260722-REPLAN-A-r2
Verified: conductor pid/marker audit (ps -p 91892 alive, active-run.json prefix+heartbeat, stale (1)/(2) markers listed); sqlite CF audit (stale ROLE-CORRECTION rows, 6 consensus_result rows all pre-recovery, recovery plan_vote rows 1459/1464); grep kimi-anchor battery at c53e0d01 (:307-:466 regions hold, DEC-5 clause :489, DEC-6 :497, no DEC-7); work-order pack-list read :71-83 (six packs confirmed); git diff --check clean; wc -l plan = 361; scope audit — only the plan file modified by this stage
Next: judge-c votes; conductor seals consensus_result with per-vote plan-revision blob shas; G-R1 owner gate before any implementation

### L-42 | 2026-07-22T20:17:35Z | S1-plan | kimi-code/k3 | judge | pi-bench-recovery-20260722-judge-c <!-- bsc-ledger:PI-BENCH-RECOVERY-20260722-JUDGE-C -->
Did: consensus judge slot c — read exactly the two assigned candidates (slot a plan-a.md r1 by claude-fable-5 @68dcd159; slot b plan-b.md by gpt-5.6-sol @9cfe3304; both committed and drift-free at HEAD c53e0d01) plus the recovery brief; spot-verified load-bearing claims in the CF store and worktree. Edited only this lifecycle file (this append + Status Block); no plan, code, or prior entry touched.
Result: plan_vote for slot a recorded on PI-BENCH-RECOVERY-20260722-JUDGE-C (CF evidence 1477). Plan A wins: AC-1 blob-sha vote discipline mechanically prevents the moving-target failure that invalidated the prior consensus (verified: zero consensus_result rows for ROLE-CORRECTION; 6 repo-wide, all earlier pipelines); plan A R1-R3 actually clears the verified hazards (3 stale ROLE-CORRECTION rows open/claimed, (1)/(2) conductor markers present, orphan plan docs) with prefix-exact scoping that exempts the live pipeline rows, while plan B names the same hazards but non-goals their cleanup; plan A owner-gate-as-blocking-task plus pre-IMPL collision audit keeps single-conductor continuity versus plan B under-specified conductor-stop; plan A grounding is re-verified at named HEADs while plan B stale-session list is incomplete (the non-terminal set is larger than 173-183). Plan B strengths noted: five-role canon, term-presence loops, honest-debt AC-8, barrier conservatism. Tally: judge-a -> slot c, judge-b -> slot a, judge-c -> slot a (slot a leads 2-1).
Verified: git log/status per candidate (frozen, committed); sqlite consensus_result + stale-row + session scans; ls .compass-forge/conductor markers ((1)/(2) present); grep kimi-as-evaluation battery (20 residuals, no DEC-7 — defect real, correction still needed); CF evidence rows 1473/1475 (command), 1477 (plan_vote), 1478 (self_report).
Next: conductor tallies the three judge votes and seals consensus_result (slot a, 2-1); G-R1 owner gate before any implementation.

### L-43 | 2026-07-22T20:24:57Z | S1-plan | kimi-code/k3 | planner | pi-bench-recovery-20260722-architect-c <!-- bsc-ledger:PI-BENCH-RECOVERY-20260722-REPLAN-C-r1 -->
Did: pi-bench-recovery-20260722-architect-c stage on task PI-BENCH-RECOVERY-20260722-REPLAN-C-r1 (harness fallback entry; the model did not append one).
Result: task PI-BENCH-RECOVERY-20260722-REPLAN-C-r1 finished; worktree head 4fcfc4ec.
Verified: see Compass Forge evidence rows on PI-BENCH-RECOVERY-20260722-REPLAN-C-r1 (command + self_report + stage_attribution).
Next: conductor advances the pipeline on evidence.

### L-44 | 2026-07-22T22:42:32Z | S1-plan | claude-fable-5 | architect | Retake planning <!-- bsc-ledger:PI-BENCH-RETAKE-20260722-PLAN-A -->
Did: authored independent retake consensus plan A at docs/build-stream/plans/pi-bench-retake-20260722-plan-a.md (283 lines: verified B0 apparatus inventory with exact paths+tests, wave-manifest design with max_processes N distinct from moa_n/repeats, owner gates G-RT1/G-RT2 with gate-to-manifest-hash binding, MoA downgrade-is-never-success acceptance, post-run artifact-only Kimi judging separation, RT-1..RT-8 task table, A1-A8 acceptance, verification matrix, risks R1-R6, rollback, narrow changed-file scope). No code, no other plan, no prior ledger entry edited.
Result: plan slot A ready for retake consensus judging; key audit at 3a226139: apparatus largely complete but suite is 170 passed/2 FAILED (deepseek_provider commit-exceeds-reservation seam at budget_ledger.py:277, plan gap G-1/RT-1); owner-gate check is existence-only with stale prior-lineage G1/G2 artifacts (runner.py:472-478, gap G-2/RT-2); referenced work order pi-benchmark-deepseek-moa-execution.md absent on this branch (G-3); stale Kimi-as-evaluation text remains in embedded winning plan (G-4); PI-BENCH-RETAKE-20260722-PLAN-A
Verified: python3 -m pytest tests/pi_benchmark/ -q -> 170 passed 2 failed (documented defect); focused test_scheduler+test_budget_ledger+test_moa -> 43 passed; git diff --check clean; CF evidence rows 1489-1492 (3x command, self_report)
Next: architects B/C finish; consensus judges vote on retake slots a/b/c; conductor pins immutable candidates and tallies

### L-45 | 2026-07-22T22:45:08Z | S1-plan | gpt-5.6-sol | planner | pi-bench-retake-20260722-architect-b <!-- bsc-ledger:PI-BENCH-RETAKE-20260722-PLAN-B -->
Did: pi-bench-retake-20260722-architect-b stage on task PI-BENCH-RETAKE-20260722-PLAN-B (harness fallback entry; the model did not append one).
Result: task PI-BENCH-RETAKE-20260722-PLAN-B finished; worktree head 3c91b30c.
Verified: see Compass Forge evidence rows on PI-BENCH-RETAKE-20260722-PLAN-B (command + self_report + stage_attribution).
Next: conductor advances the pipeline on evidence.

### L-46 | 2026-07-22T22:54:53Z | S1-plan | kimi-code/k3 | architect | Planning phase <!-- bsc-ledger:PI-BENCH-RETAKE-20260722-PLAN-C -->
Did: authored independent consensus plan C at docs/build-stream/plans/pi-bench-retake-20260722-plan-c.md (387 lines): verified B0 apparatus inventory with exact paths+tests; validated suite (170 passed/2 failed — root cause pinned: post-F6 commit<=reservation invariant vs underestimated reservations, plus the wave-wedge path at live_driver.py:648; RT-1 fail-closed hardening designed); three-lane immutable manifest design (max_processes N=4 recorded, distinct from moa_n=3 and repeats=1; 132 units); USD0.73 worst-case arithmetic + RT-2 estimate gate; fresh G-R0..G-R3 owner gates superseding stale g1/g2 (USD0.50, judge gpt-5.6-luna); MoA downgrade truthfulness (full_ensemble expected-degraded, never an ensemble success); post-run artifact-only Kimi judging separation (zero judge rows on the DUT ledger); V0-V5 verification matrix; rollback; narrow changed-file scope. No code, no other architect's plan, no lifecycle plan content edited.
Result: plan slot C ready for consensus judging; PI-BENCH-RETAKE-20260722-PLAN-C
Verified: backend/.venv/bin/python -m pytest tests/pi_benchmark/ -q -> 170 passed 2 failed (stale pre-F6 provider tests, fix designed in RT-1); plan-only/idempotent/ManifestConflict/provider-reject/owner-gate CLI probes -> exit 0/0/2/argparse-error/3; pack census 15+4+3=22; approved endpoint pi-deepseek-default at backend/app/core/pi_runtime/endpoints.py:23; shared-venv 'import app' resolves to ROOT checkout (RT-0 attestation mitigation); CF evidence rows 1508-1512 (4x command, self_report)
Next: consensus judges vote on plan slots a/b/c; conductor seals consensus_result; G-R0 owner gate before any implementation

### L-47 | 2026-07-22T22:59:43Z | S1-plan | claude-fable-5 | judge | Retake planning <!-- bsc-ledger:PI-BENCH-RETAKE-20260722-JUDGE-A -->
Did: consensus judge slot a for round fcf29273d0f8bddbc66e — read exactly candidates B (docs/build-stream/plans/pi-bench-retake-20260722-plan-b.md, sha f39e3f52) and C (docs/build-stream/plans/pi-bench-retake-20260722-plan-c.md, sha e090b229), verified both hashes and git head a9b0b795 against the task payload, and fact-checked their differentiating claims in-tree. No plan edited; no review_verdict recorded (judge contract).
Result: plan_vote = slot C (candidate_id db2ac00d…). C wins on verified grounding + execution risk: it pinned the red-baseline root cause, independently found the latent wave-wedge defect (ledger.commit outside try/except in live_driver.run_live_unit — verified) and the shared-venv backend import hazard, proved budget fit (~$0.73 <= $1.00), and correctly flagged that B's cited authority file pi-benchmark-deepseek-moa-execution.md does not exist (verified). B is stronger on gate-digest binding + ASGI DUT fidelity but is a heavier 11-task redesign resting on a dangling authority pointer; recommend grafting B's run-bound gate-digest verification onto C at implementation. PI-BENCH-RETAKE-20260722-JUDGE-A
Verified: shasum -a 256 of both plans + git rev-parse HEAD -> match payload; backend/.venv/bin/python -m pytest tests/pi_benchmark/ -q -> 2 failed, 170 passed (exactly the two test_deepseek_provider.py tests both plans reported); ls conductor-instructions/ -> pi-benchmark-deepseek-moa-execution.md absent; sed live_driver.py 550-660 -> commit outside dispatch try/except confirmed; CF evidence rows 1518-1522 (3x command, plan_vote, self_report)
Next: judges b/c vote; conductor tallies and seals consensus_result; G-R0 owner gate before any implementation

### L-48 | 2026-07-23T00:05:28Z | S1-plan | gpt-5.6-sol | judge | Retake planning <!-- bsc-ledger:PI-BENCH-RETAKE-20260722-JUDGE-B -->
Did: consensus judge slot b for round fcf29273d0f8bddbc66e — read exactly candidates A (`docs/build-stream/plans/pi-bench-retake-20260722-plan-a.md`, sha256 `5abf12ff…`) and C (`docs/build-stream/plans/pi-bench-retake-20260722-plan-c.md`, sha256 `e090b229…`) plus their supplied author identities; both hashes matched the work-order payload. No plan or code edited and no `review_verdict` recorded.
Result: `plan_vote = slot C` (`candidate_id db2ac00d…`) on `PI-BENCH-RETAKE-20260722-JUDGE-B`. C is stronger because it models the current single-`moa_mode` CLI as three manifests and closes the proven `live_driver.py` post-dispatch accounting/resume wedge plus checkout-import hazard. A's manifest-bound stale-gate rejection is stronger than C's fresh-artifact-only gate design and remains an explicit implementation residual risk.
Verified: `shasum -a 256 docs/build-stream/plans/pi-bench-retake-20260722-plan-a.md docs/build-stream/plans/pi-bench-retake-20260722-plan-c.md` matched both pinned hashes; both files read in full; CF evidence IDs 1529 command, 1530 plan_vote, 1531 self_report.
Next: stage exit: judge c votes, then the conductor tallies and seals `consensus_result`; G-R0 owner gate precedes implementation.

### L-49 | 2026-07-23T00:11:57Z | S1-plan | kimi-code/k3 | judge | Retake planning <!-- bsc-ledger:PI-BENCH-RETAKE-20260722-JUDGE-C -->
Did: consensus judge slot c for round fcf29273d0f8bddbc66e — read exactly candidates A (`docs/build-stream/plans/pi-bench-retake-20260722-plan-a.md`, sha256 `5abf12ff…`) and B (`docs/build-stream/plans/pi-bench-retake-20260722-plan-b.md`, sha256 `f39e3f52…`) plus their supplied author identities; both hashes matched the work-order payload. No plan or code edited; no `review_verdict` recorded (judge contract).
Result: `plan_vote = slot B` (`candidate_id 80d2db45…`) on `PI-BENCH-RETAKE-20260722-JUDGE-C`. B found the decisive apparatus-validity gap A missed: waves dispatch `default_prompt_builder`'s route smoke prompt ("not the full scenario corpus", `live_driver.py:384-397`, default-wired at `:549-550` with no runner override), so A's unchanged reuse would run B1..B_N without measuring scenario quality; B's T4 grounds the fix in the verified ASGI seam (`test_chat_pi_asgi.py` + `x-istara-agent-engine` in `dispatcher.py`). B's Kimi-only artifact judging with structural no-DUT enforcement fits the spec's reserved separate judging session better than A's in-run DeepSeek judge on the DUT ledger (same-provider self-judging + redundant spend). A's audit is sharper on citations (correctly flagged the missing `pi-benchmark-deepseek-moa-execution.md` that B's header cites — verified absent) and its interpreter pin + append-only lifecycle DEC should be grafted onto B at implementation. Both A and B miss the bare `ledger.commit` wave-wedge (`live_driver.py:648`, verified: commit refusal escapes record-less and wedges the unit) — implementation must close it regardless of winner.
Verified: `shasum -a 256` of both plans -> match payload; `ls docs/build-stream/conductor-instructions/` -> moa-execution file absent (A G-3 true, B header slip); `sed`/`grep` on `live_driver.py` -> smoke-prompt default wired at :549-550, bare commit at :648; `sed runner.py 472-478` + `cat tests/pi_benchmark/gates/g1_owner_gate.json` -> existence-only gate + stale `gpt-5.6-luna` approval; `ls tests/pi_production/test_chat_pi_asgi.py` + `grep x-istara-agent-engine backend/app` -> B's seam real; CF evidence IDs 1542, 1543 (command), 1544 (plan_vote), 1545 (self_report)
Next: stage exit: conductor tallies judge a/b/c votes and seals `consensus_result`; G-R0 owner gate precedes implementation.

### L-50 | 2026-07-23T00:59:02Z | S2-execute | claude-opus-4-8 | executor | Retake execution (RT-0/RT-1/RT-2) <!-- bsc-ledger:PI-BENCH-RETAKE-20260722-IMPL -->
Did: implemented the winning Plan C implementer scope RT-1 (apparatus hardening, red→green + wedge-proof accounting) and RT-2 (dry-run estimate gate), plus RT-0's DEC-7 role-canon supersession. Files: `tests/pi_benchmark/deepseek_provider.py` (reserve `max(2×est_input, MIN_RESERVE_INPUT_TOKENS=256)` input-priced + `max_tokens` output-priced; catch commit `LedgerStateError` → `ProviderCallFailed("over_reservation_fail_closed")`, reservation retained), `tests/pi_benchmark/live_driver.py` (same reserve margin + `DEFAULT_MAX_TOKENS=1024`; on resume `reserve`→`LedgerStateError` write `not_runnable/other` `interrupted_unknown_usage` retaining the reservation instead of re-raising; wrap the bare `commit` (old :648) → on `LedgerStateError` write `not_runnable/other` `accounting_fail_closed`, reservation retained, wave never crashes), `tests/pi_benchmark/runner.py` (`_worst_case_program_cost_usd` + estimate gate in `_run_b0_plan_only`: prints the deterministic whole-program worst case and exits 2 before any manifest write when it exceeds `--budget-usd`). Reconciled the 2 stale provider tests to realistic in-margin usage; added over-reservation (provider+driver), resume-with-outstanding-reservation, and estimate-gate tests. Appended DEC-7 pinning the DeepSeek-only DUT / Kimi-post-run-only canon (supersedes DEC-5/DEC-6 Kimi-eval clauses). RT-0 attestation artifacts and RT-3+ live scheduling/waves are the executor lane's, behind G-R1/G-R2 — not done here.
Result: apparatus is green and the F-6-class latent wedge is closed fail-closed. AC-1 met (178 passed / 0 failed; was 170/2). AC-3 estimate gate verified ($0.7342 ≤ $1.00 → exit 0 with manifest; `--repeats 2` → $1.4683 > cap → exit 2, no manifest, no live call). AC-5/AC-6 fail-closed reserve/commit/resume paths unit-proven. No product/backend/security file touched; changed-file scope = the 6 RT-1/RT-2 files under `tests/pi_benchmark/` + this lifecycle file (DEC-7, L-50, Status Block). No live dispatch, no spend, no models loaded. PI-BENCH-RETAKE-20260722-IMPL
Verified: `PYTHONPATH=$PWD/backend backend/.venv/bin/python -m pytest tests/pi_benchmark/ -q` → 178 passed; `... tests/pi_migration/test_count_to_zero.py -q` → 3 passed (ratchet 0); `scripts/security_benchmark.py --fail-on-threshold` → pass, 100.0%, 28/0, triggered_paths=[]; CLI probes: lane-none `--plan-only` exit 0 (estimate $0.7342, 44 units/4 shards), `--repeats 2` exit 2 no manifest, identical rerun exit 0, `--max-processes 3` `ManifestConflict` exit 2, offline `validate_topology` → `full_ensemble->self_moa` degraded; `git status` → only the 6 tests/pi_benchmark files + this lifecycle file. CF evidence: 4×command + self_report on PI-BENCH-RETAKE-20260722-IMPL.
Next: stage exit — RT-1/RT-2 ready for independent code review (pi-bench-retake-20260722-fixer/reviewer lane); executor lane then does RT-0 attestation (`app.__file__` pin, `b0-attestation.json`) and, behind G-R1/G-R2, RT-3 B0 scheduling + RT-4 preflight + RT-5 waves + RT-6 POST-N.

### L-51 | 2026-07-23T01:26:00Z | S3-review | kimi-code/k3 | reviewer | Retake execution (RT-1/RT-2 review) <!-- bsc-ledger:PI-BENCH-RETAKE-20260722-REVIEW -->
Did: independent code review of PI-BENCH-RETAKE-20260722-IMPL (commit a68ffc25) against the approved Plan C RT-1/RT-2 rows, section 2.3 budget contract, and AC-1/2/3. Read the full diff (6 tests/pi_benchmark files + this lifecycle file); cross-checked every fail-closed claim against budget_ledger.py (reserve/commit raise LedgerStateError BEFORE any append, so retained-reservation semantics hold: budget_ledger.py:234,273,277); re-ran the touched suites and the offline CLI probes myself (all in /tmp, no spend, no live calls).
Result: review_verdict=pass, zero findings (no new Findings-register rows). RT-1: reserve max(2x chars4, 256) input-priced + max_tokens output-priced per model call in provider and driver; commit LedgerStateError -> provider ProviderCallFailed("over_reservation_fail_closed") / driver not_runnable/other "accounting_fail_closed", reservation retained, wave never crashes; resume reserve LedgerStateError -> not_runnable/other "interrupted_unknown_usage", no re-dispatch. RT-2: whole-program worst-case gate in _run_b0_plan_only exits 2 before any manifest write when > --budget-usd; estimate math matches plan section 2.3 exactly ($0.7342 <= $1.00). Scope clean: only the 6 declared tests/pi_benchmark files + this file; DEC-7 appended, DEC-5/6 byte-identical; L-50 + status block correct. Non-blocking observation: tests/pi_production is red in THIS worktree (47 failed / 299 passed) because pi-runtime/node_modules is absent here (present in the root checkout) -> worker handshake_timeout; diff overlap with pi-runtime/backend/pi_production is zero files, so it is a pre-existing worktree-setup gap for executor RT-0, not a defect in the reviewed change. PI-BENCH-RETAKE-20260722-REVIEW
Verified: pytest tests/pi_benchmark -q -> 178 passed (AC-1); tests/pi_migration/test_count_to_zero.py -> 3 passed (ratchet 0); scripts/security_benchmark.py --fail-on-threshold -> pass, triggered_paths=[]; plan-only probes -> lane-none exit 0 estimate $0.7342 with manifest (44 units, 4x11 shards, AC-2 fields incl. max_processes=4/provider=deepseek/model=deepseek-v4-pro/cap=1.0/moa_n=3/repeats=1/T3, 44 distinct unit_ids), --repeats 2 -> $1.4683 exit 2 no manifest, identical rerun exit 0 manifest sha256 unchanged, --max-processes 3 -> exit 2 ManifestConflict; pytest tests/pi_production -q -> 47 failed/299 passed (environmental: pi-runtime/node_modules missing in worktree; reproduced handshake_timeout on test_worker_tool_loop.py). CF evidence: 6x command + self_report + review_verdict on PI-BENCH-RETAKE-20260722-REVIEW.
Next: stage exit: review passed — conductor advances; executor lane owns RT-0 attestation (install pi-runtime deps in this worktree, pin app.__file__, write b0-attestation.json), then G-R1 before RT-3/RT-4 and G-R2 before waves.

### L-52 | 2026-07-23T02:12:48Z | S2-execute | kimi-code/k3 | executor | Retake execution (RT-0 attestation + RT-3 B0 scheduling) <!-- bsc-ledger:PI-BENCH-RETAKE-B0-20260723-WAVE-b0-IMPL -->
Did: executed the remaining offline Plan C work in the shared worktree (wave b0). RT-0: attested the execution checkout pin — unpinned `import app` resolves to the ROOT checkout (/Users/user/Documents/Istara-main-pi-replacement/backend/app/__init__.py, hazard confirmed), with PYTHONPATH="$PWD/backend" it resolves inside this worktree; branch conductor/pi-bench-retake-20260722 @ 4a089e9c; N=max_processes=4 per Plan C section 2.2 (distinct from moa_n=3 and repeats=1); verified absence of prior retake .results residue (dir did not exist before RT-3; .results/ gitignored via tests/pi_benchmark/.gitignore:4); wrote tests/pi_benchmark/.results/runs/retake/b0-attestation.json (file_sha256 b9fee3edd4343cd4f9a7cc05e1bd6673b432b83da9e2768b2543f83b6c34d1c7); closed the L-51 environmental gap by running npm ci in pi-runtime (dependency install only, no code change). RT-3: produced three immutable, content-hashed, plan-only manifests for lanes none/self_moa/full_ensemble (44 units x 4 disjoint shards of 11 per lane) into the gitignored retake run root sharing the (not yet created) budget-ledger path. DEC-7 was already appended at L-50; no new decision entry required.
Result: B0 offline evidence complete — 0 live calls, 0 spend, no credentials read, no ledger file created, no G-R1/G-R2/G-R3 artifacts, stale g1/g2 gates byte-identical. AC-2 met: three manifests each recording max_processes=4, provider=deepseek, model=deepseek-v4-pro, budget_cap_usd=1.0, moa_n=3, repeats=1, tier=T3, shards covering 44 units exactly once (22 scenarios x engines pi/legacy). AC-3 met: deterministic worst-case estimate $0.7342 <= $1.00 printed at B0 with exit 0; repeats=2 probe ($1.4683) exit 2 with no manifest mutation and no live call. content_sha256: none=e22c796a05af3235..., self_moa=ea2288e3c172c880..., full_ensemble=0d65a54e4ac57466.... Spend-free topology probe: requested_slots=3 on available=[pi-deepseek-default] -> would_serve_mode=self_moa, would_degrade=true, downgrade=full_ensemble->self_moa (AC-8 expectation for the full_ensemble lane). PI-BENCH-RETAKE-B0-20260723-WAVE-b0-IMPL
Verified: pytest tests/pi_benchmark -q -> 178 passed, 0 failed (AC-1); pytest tests/pi_migration/test_count_to_zero.py -q -> 3 passed (ratchet 0); npm ci (pi-runtime) then pytest tests/pi_production -q -> 346 passed in 64.36s (was 47 failed / 299 passed without node_modules); python3 scripts/security_benchmark.py --fail-on-threshold -> status pass, triggered_paths=[]; runner --plan-only x3 lanes -> exit 0 each (estimate $0.7342); identical rerun lane none -> exit 0, manifest file_sha256 unchanged; --max-processes 3 -> exit 2 ManifestConflict, unchanged; --repeats 2 -> exit 2, unchanged; all three manifest file hashes byte-identical before/after every probe; validate_topology -> spend-free JSON as above. CF evidence: 7x command + self_report on PI-BENCH-RETAKE-B0-20260723-WAVE-b0-IMPL.
Next: stage exit — B0 offline evidence complete. RT-4 preflight (first live call) requires the G-R1 owner gate; RT-5 waves require G-R2; both remain owner-gated and untouched.

### L-53 | 2026-07-23T02:24:17Z | S3-review | gpt-5.6-sol | reviewer | Retake execution (RT-0/RT-3 B0 review) <!-- bsc-ledger:PI-BENCH-RETAKE-B0-20260723-WAVE-b0-REVIEW -->
Did: independently reviewed Plan C RT-0/RT-3 against implementer commit `81557fa0`, CF evidence 1576-1583/1588, ignored runtime artifacts, and actor session 208 logs. Recomputed attestation/file hashes; hash-verified all three manifests; reran the offline suite and focused idempotent-resume/`ManifestConflict` probes. Added F-8 and created `FIX-PI-BENCH-RETAKE-B0-20260723-WAVE-b0-REVIEW-r1-lifecycle`; no benchmark code or runtime artifact was edited.
Result: verdict **FAIL** with one Major lifecycle-integrity finding. The B0 evidence itself passes: checkout pin and N=4 are attested; none/self_moa/full_ensemble manifests each contain 44 unique units in four disjoint shards of 11, are content-hash-bound, and preserve the required provider/model/cap/moa_n/repeats/tier fields; resume exits 0 unchanged and differing max_processes exits 2 unchanged. Session 208 shows plan-only commands, zero live/provider/credential/server operations, no budget ledger, and no fresh retake gate artifact. F-8: the refreshed Status Block still named stale branch `Review_pi_test` and `CF-SPEC-8`, violating the resume identity contract; the fixer must correct those identity fields and preserve append-only history.
Verified: `PYTHONPATH=/Users/user/Documents/Istara-main-pi-benchmark-retake/backend /Users/user/Documents/Istara-main-pi-replacement/backend/.venv/bin/python -m pytest tests/pi_benchmark/ -q` -> 178 passed; `tests.pi_benchmark.scheduler.load_manifest` + invariant audit -> three hashes valid, 44 unique units/lane, shard sizes `[11,11,11,11]`, lane modes `{None}`/`{self_moa}`/`{full_ensemble}`, N=4/moa_n=3/repeats=1; identical lane-none `runner.py --plan-only --max-processes 4` -> exit 0 and file sha256 `71130343...` unchanged; differing `--max-processes 3` -> expected exit 2 `ManifestConflict` and same sha256; `rg --files --hidden tests/pi_benchmark/.results/runs/retake` -> only attestation + three manifests; `rg --files tests/pi_benchmark/gates` -> only stale g1/g2 files; actor session 208 log audit -> no `--live` execution/provider call/credential read/server start.
Next: stage exit — fixer resolves F-8, then the conductor creates one delta re-review; RT-4/RT-5 remain owner-gated.

### L-54 | 2026-07-23T02:31:28Z | S4-remediate | gpt-5.6-luna | remediator | Retake execution (B0 lifecycle identity remediation) <!-- bsc-ledger:FIX-PI-BENCH-RETAKE-B0-20260723-WAVE-b0-REVIEW-r1-lifecycle -->
Did: resolved F-8 in `docs/build-stream/2026-07-22-pi-benchmark.md` by preserving the corrected active resume identity (`conductor/pi-bench-retake-20260722`, `CF-SPEC-9`), marking the finding fixed, and refreshing the Status Block handoff; no code or historical ledger entries changed.
Result: F-8 Major closed (`open` -> `fixed (L-54)`); lifecycle resume identity and append-only history are coherent for the delta re-review.
Verified: focused Status Block/ledger integrity check, `git diff --check`, and scoped diff audit passed; pre-change `compass-forge gate before` reported 0 new failures/warnings (80 inherited failures, actionable_failures=[]).
Next: stage exit: F-8 fixed and ready for the conductor-created delta re-review; RT-4/RT-5 remain owner-gated.

### L-55 | 2026-07-23T02:38:26Z | S3-review | gpt-5.6-sol | reviewer | Retake execution (B0 lifecycle delta re-review) <!-- bsc-ledger:REREV-PI-BENCH-RETAKE-B0-20260723-WAVE-b0-REVIEW-r1 -->
Did: delta re-reviewed F-8 only against fixer commit `d91a170` and its cited verification evidence; inspected the lifecycle diff, live Status Block, F-8 register row, L-54, and the immediate historical-identity seam. No benchmark code, runtime artifacts, historical decisions, or earlier ledger entries were changed.
Result: verdict **PASS** with zero findings. The live resume identity is uniquely `conductor/pi-bench-retake-20260722` plus `CF-SPEC-9`; F-8 is verified closed. The remaining `Review_pi_test` / `CF-SPEC-8` mentions are correctly preserved inside the superseded historical pi-eval plan, not the live Status Block.
Verified: `git diff d91a170^ d91a170 --check` passed; commit `d91a170` changes only `docs/build-stream/2026-07-22-pi-benchmark.md`; exact assertions passed for one live branch/spec pair, one L-54 fixer marker, and the F-8 fixed marker; Compass Forge command evidence 1612 recorded on the re-review task.
Next: stage exit: F-8 delta re-review passed; conductor may advance, while RT-4/RT-5 remain blocked behind G-R1/G-R2.

### L-56 | 2026-07-23T13:23:10Z | S2-execute | kimi-code/k3 | executor | Retake execution (RT-4 DeepSeek-only budgeted preflight) <!-- bsc-ledger:PI-BENCH-RETAKE-EXEC-20260723-WAVE-rt4-preflight-IMPL -->
Did: executed approved Plan C RT-4 in the shared worktree. Recorded the owner's whole-plan approval ("The wave is supposed to have continue everything. Approved, the whole plan is approved, use the wave to execute it all") as CF evidence (row 1622) and created the fresh retake-scoped G-R1 artifact tests/pi_benchmark/gates/retake_g1_owner_gate.json stating exactly: DeepSeek deepseek-v4-pro via endpoint pi-deepseek-default only; USD 1.00 cumulative ledger cap across preflight, all waves, all lanes, and all retries; no fallback; credentials only via env ISTARA_PI_SECRET_PI_DEEPSEEK_DEFAULT / Keychain istara-pi-deepseek/openclaw, memory-only, never logged. Stale prior-lineage gates g1/g2 left byte-identical. Asserted PYTHONPATH=$PWD/backend resolves app inside this worktree, then made exactly ONE DeepSeekProvider.preflight() call against the shared retake ledger tests/pi_benchmark/.results/runs/retake/budget-ledger.json (cap_usd=1.00).
Result: preflight succeeded — provider-reported usage (estimate=False): 5 input / 1 output / 5 cache-write tokens, actual cost 7.7e-06 USD; ledger reserve 0.000143 -> commit 7.7e-06, rows=2, closed=False; verify_budget_ledger exit 0 (spent=$0.000008 <= cap=$1.00). No server started, no other provider/model used, no credential read or printed by this agent, no fallback. First live spend of the retake program: 0.0008% of the $1.00 envelope. PI-BENCH-RETAKE-EXEC-20260723-WAVE-rt4-preflight-IMPL
Verified: PYTHONPATH=$PWD/backend pin assertion -> pin ok (app resolves to worktree backend/app/__init__.py); preflight heredoc (Plan C section 5 V2) -> preflight ok: 7.7e-06 estimate: False; $PY tests/pi_benchmark/verify_budget_ledger.py --ledger tests/pi_benchmark/.results/runs/retake/budget-ledger.json --cap-usd 1.00 -> [ok] exit 0; git status -> scope = gate artifact + this lifecycle file only (.results gitignored). CF evidence rows 1622 (owner_approval), 1623-1624 (command), self_report follows.
Next: stage exit: preflight complete, stopping here per manifest — later waves are separate manifest entries and remain blocked behind the G-R2 owner gate (B0 evidence pack: green suite, three immutable manifests, estimate <= cap, preflight ledgered, attestation, route-isolation probes).

### L-57 | 2026-07-23T13:32:00Z | S3-review | gpt-5.6-sol | reviewer | Retake execution (RT-4 DeepSeek-only budgeted preflight review) <!-- bsc-ledger:PI-BENCH-RETAKE-EXEC-20260723-WAVE-rt4-preflight-REVIEW -->
Did: independently reviewed Plan C RT-4, implementer commit `26c13b42`, fresh `tests/pi_benchmark/gates/retake_g1_owner_gate.json`, the ignored shared retake ledger, CF evidence 1622-1630, and authoritative actor session 212. Confirmed the complete-plan approval quote, DeepSeek `deepseek-v4-pro` through `pi-deepseek-default` only, cumulative USD 1.00 cap, no fallback, configured env/Keychain-only credential policy, pinned worktree import, and exactly one ledgered preflight. No code, run artifact, prior ledger entry, historical decision, or stale owner gate was changed by this review.
Result: verdict **PASS** with zero findings (CF evidence 1635). The shared ledger contains exactly one `preflight` reserve and one matching commit, provider-reported spend USD 0.0000077, no credential-shaped keys or secret values, and no other provider/model row. Session 212 records one pinned preflight execution marker and no server or fallback action. Stale `g1_owner_gate.json` and `g2_owner_gate.json` remain byte-identical to their pre-RT-4 Git blobs. RT-5 remains correctly blocked behind G-R2.
Verified: `verify_budget_ledger.py --ledger tests/pi_benchmark/.results/runs/retake/budget-ledger.json --cap-usd 1.00` -> passed, rows=2 and spend USD 0.0000077; exact `jq` artifact/ledger assertions and session secret-value scan -> passed; `PYTHONPATH=$PWD/backend backend/.venv/bin/python -m pytest tests/pi_benchmark/test_deepseek_provider.py::test_preflight_is_a_minimal_ledgered_call tests/pi_benchmark/test_verify_budget_ledger.py -q` -> 13 passed; stale-gate `git hash-object --no-filters` values matched `HEAD^` blobs; `git diff --check HEAD^ HEAD` passed. CF command evidence 1631-1634 and self-report 1636.
Next: stage exit: RT-4 independent review passed; conductor may advance to B0 evidence-pack assembly and G-R2 owner approval, but must not dispatch RT-5 before G-R2.

### L-58 | 2026-07-23T13:55:40Z | S2-execute | kimi-code/k3 | executor | Retake execution (RT-5 lane none B1) <!-- bsc-ledger:PI-BENCH-RETAKE-EXEC-20260723-WAVE-none-b1-IMPL -->
Did: executed approved Plan C RT-5 lane=none wave=1 in the shared worktree. Recorded the owner's complete-plan approval as CF evidence (row 1643; quote "The wave is supposed to have continue everything. Approved, the whole plan is approved, use the wave to execute it all") and created the fresh G-R2 artifact `tests/pi_benchmark/gates/retake_g2_owner_gate.json` binding the B0 evidence pack (attestation sha b9fee3ed…, three manifest file/content hashes, green suite, $0.7342 estimate ≤ $1.00, successful preflight ledgered, route-isolation probes), N=4, DeepSeek-only `pi-deepseek-default`/`deepseek-v4-pro`, $1.00 cumulative cap, no fallback; stale g1/g2 left byte-identical. Asserted `PYTHONPATH=$PWD/backend` with `app.__file__` inside this worktree, then ran `runner.py --wave 1 --max-processes 4 --live` with the immutable none manifest and shared ledger. No server, no non-DeepSeek provider/model, no credential read or printed by this agent.
Result: wave exit 0; 11 records == shard 1 units exactly, no duplicates, manifest file sha256 unchanged, ledger verify [ok] spent=$0.024960 ≤ $1.00 (rows=14, closed=False, provider=deepseek). Outcome: 1 ok (`a2a.debate_report.slice`, engine=pi, actual $0.0011187) + 10 not_runnable/startup_failure — the wave path runs each unit in a fresh `asyncio.run` loop (`live_driver.py:740`) while the pi-runtime supervisor is a process-wide loop-bound singleton (`supervisor.py:526`), so units 2–11 failed at dispatch with "Future attached to a different loop"; their reservations are retained as worst-case spend per fail-closed accounting (they are not billed usage). Triaged as F-9 (Critical) to fixer task `FIX-PI-BENCH-RETAKE-EXEC-20260723-WAVE-none-b1-eventloop`; no code edited in this stage per scope rules. PI-BENCH-RETAKE-EXEC-20260723-WAVE-none-b1-IMPL
Verified: wave run exit 0 (`[ok] wave 1/4: 11 records (0 already complete), spend=$0.0250`); completeness script (record_ids == manifest.shards[0], all unique, wave.index==1) -> passed; route/model assertions (`pi-deepseek-default`/`deepseek-v4-pro`, estimate=False) -> passed; manifest sha256 71130343bc41… unchanged; `verify_budget_ledger.py --cap-usd 1.00` -> [ok] spent=$0.024960, exit 0; G-R2 gate JSON parsed and pin assertion passed. CF evidence rows 1643-1648 (owner_approval, 4x command, self_report).
Next: conductor routes F-9 to the fixer lane; RT-5 waves none B2..B4 and both MoA lanes must wait for the cross-loop fix (the same defect will recur on every wave); review of PI-BENCH-RETAKE-EXEC-20260723-WAVE-none-b1-IMPL decides whether B1 stands complete-with-finding or the 10 startup_failure units are re-dispatched after the fix.

### L-59 | 2026-07-23T13:57:38Z | S4-remediate | gpt-5.6-luna | remediator | Retake execution (F-9 cross-event-loop remediation) <!-- bsc-ledger:FIX-PI-BENCH-RETAKE-EXEC-20260723-WAVE-none-b1-eventloop -->
Did: fixed F-9 in `tests/pi_benchmark/runner.py` by executing each live batch, including wave shards, inside one shared `asyncio.run` loop and awaiting `live_driver.run_live_unit`; added `tests/pi_benchmark/test_runner.py::test_wave_mode_dispatches_all_pending_units_on_one_event_loop` to prove two pending units share the same loop. Regenerated `docs/features/site/manifest.json` through the required feature-doc check. Updated the Findings register F-9 `open -> fixed (L-59)` and refreshed the Status Block; no runtime artifacts, ledger history, or unrelated files changed.
Result: the process-wide Pi runtime supervisor is no longer reused across per-unit event loops in runner-managed batches. Existing resume filtering and the public single-unit sync wrapper remain unchanged; the ten prior startup_failure records were not mutated or re-dispatched by this fixer.
Verified: `PYTHONPATH=$PWD/backend /Users/user/Documents/Istara-main-pi-replacement/backend/.venv/bin/python -m pytest tests/pi_benchmark/test_runner.py -q` -> 24 passed; `... -m pytest tests/pi_benchmark/test_live_driver.py -q` -> 21 passed; `... -m pytest tests/pi_benchmark/ -q` -> 179 passed; `... -m compileall -q tests/pi_benchmark/runner.py tests/pi_benchmark/test_runner.py` -> passed; `python scripts/feature_docs.py --seed-missing --generate-site --check` -> 86 features passed; `compass-forge gate after --task FIX-PI-BENCH-RETAKE-EXEC-20260723-WAVE-none-b1-eventloop --summary` -> inherited 80 failures, `new_failures: 0`, `actionable_failures: []`; `git diff --check` -> passed.
Next: stage exit: F-9 is fixed and ready for the conductor-created delta re-review; the reviewer must verify the changed batch seam before any live retry decision.
