# Build Stream Lifecycle — Pi Benchmark Experimentation

<!-- STATUS BLOCK -->
```yaml
item: pi-benchmark
branch: Review_pi_test
cf: { spec: CF-SPEC-8 }
phase: "Replanned execution — B0 through B_N process waves"
stage: S4-remediate
status: in-progress
blocked_on: null
authored_by: build-stream-conductor
grounding: "Based on 2026-07-20-pi-full-replacement-master-plan.md Section 10"
last: {agent: claude-fable-5, at: 2026-07-22T19:38:59Z, ledger: L-27}
next_action: "F-5 fixed; complete the sibling barrier, then run one delta re-review."
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

## Decision log

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
