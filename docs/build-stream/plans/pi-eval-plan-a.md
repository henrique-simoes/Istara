# Execution Plan A — Benchmarks B1–B4: Pi vs Legacy (Experiment Pi vs Legacy)

```yaml
plan_slot: a
task: pi-eval-REPLAN-A-r1   # revision r1 of pi-eval-PLAN-A
author_model: claude-fable-5
grounding: docs/build-stream/plans/2026-07-20-pi-full-replacement-master-plan.md §10
lifecycle: docs/build-stream/2026-07-22-pi-benchmark.md
date: 2026-07-22
revision: r1
```

**r1 repair note.** The r0 self-report carried three residual risks; all are now closed with
verified evidence: (1) `metrics-schema.json` is confirmed absent **repo-wide** (searched the
whole tree, not just `tests/pi_benchmark/`), so E0.1 is definitively an authoring task, not an
adoption task; (2) the §10.6 pricing table the master plan cites pathlessly is
`labs/pi-replacement/src/raw-llm-capture.mjs:5-10` (`DEEPSEEK_ESTIMATE_USD_PER_MILLION`) —
E3.2 now cites it exactly; (3) the long-horizon "tokens" bug §10.3 assigns to E0.8 is verified
at `tests/benchmarks/long_horizon_runner.py:138` (`total_tokens += 1` per SSE chunk). Axis-1
metric vocabulary confirmed present at `tests/agentic_eval_contract.json` (`tool_name_accuracy`,
`argument_schema_validity`, `multi_turn_recovery`, `evidence_chain_completeness`).

## 0. Ground truth this plan is built on (verified 2026-07-22 in this worktree)

| Fact | Status | Evidence |
|---|---|---|
| W0–W9 complete; dispatcher + usage ledger live | ✅ exists | `backend/app/core/agentic/dispatcher.py`, `usage_ledger.py`; branch `Review_pi_test` at `1f843f31` |
| 15 canonical scenarios mapped to production tests | ✅ exists | `tests/pi_production/test_scenario_coverage_map.py` |
| Engine header supported client-side | ✅ exists | `tests/real_user_benchmark/lib/api-client.mjs:31,244` (`x-istara-agent-engine`) |
| `--engine` flag in the two `run.mjs` harnesses | ❌ missing | grep of `tests/simulation/run.mjs`, `tests/real_user_benchmark/run.mjs` — no engine plumbing |
| `tests/pi_benchmark/` (runner, scenarios, judge, probes, feature_criteria) | ❌ missing | dir does not exist |
| `metrics-schema.json` | ❌ missing | referenced by §10 with line numbers, but absent repo-wide (full-tree name search, r1) — must be authored first |
| Axis-1 metric vocabulary | ✅ exists | `tests/agentic_eval_contract.json` (`eval_metrics`: tool_name_accuracy, argument_schema_validity, multi_turn_recovery, evidence_chain_completeness) |
| T3 pricing table for dry-run estimates | ✅ exists | `labs/pi-replacement/src/raw-llm-capture.mjs:5-10` (`DEEPSEEK_ESTIMATE_USD_PER_MILLION`) |
| Long-horizon chunk-count "tokens" bug | ✅ located | `tests/benchmarks/long_horizon_runner.py:138` (`total_tokens += 1` per SSE chunk) — E0.8 fixes it to read the ledger |
| `scripts/pi_benchmark_report.py` | ❌ missing | not in `scripts/` |
| `comparison-Istara-pi/` (reports + article home) | ❌ missing | dir does not exist |
| Deterministic eval harness to reuse | ✅ exists | `scripts/run_istara_evals.py`, `tests/evals/` (registry + `.results/` conventions) |
| T3 budget | ⚠️ $0.409 remaining of $0.50 DeepSeek envelope — insufficient for B3 as specced | master plan §10.6 |

**Consequence:** "run B1–B4" is really *build the §10.3 assets, then run the four phases*.
This plan therefore has a build wave (E0) before the four execution waves (E1–E4). B1's
tier-0/1 content is the one thing partially runnable today (the `tests/pi_production/`
scenario suite), so E1 starts while E0 finishes its later assets.

## 1. Design

### 1.1 Architecture of the benchmark run

One paired-scenario runner (`tests/pi_benchmark/runner.py`) is the single execution
engine for all phases; phases differ only in **scenario pack**, **tier**, and **N**:

```
                    ┌──────────────────────────────────────────────┐
 scenario packs ───▶│ runner.py  (paired, seeded, fixture-identical)│──▶ .results/runs/<ts>/
 (canonical/spine/  │  engine=pi   run ─┐                           │     one JSON record per
  a2a/probes/       │  engine=legacy run┘ same seed, same fixtures  │     run, schema-validated
  feature-criteria) └──────────────────────────────────────────────┘
                                   │
                                   ▼
                      judge.py (blind, position-swapped, cached)
                                   │
                                   ▼
              scripts/pi_benchmark_report.py ──▶ comparison-Istara-pi/reports/<ts>/
                                                 report.md / report.html / scorecard.json
```

Non-negotiable design rules (from §10.1, restated as implementation constraints):

1. **Pairing:** every (scenario, seed, repetition) executes on both engines via the
   dispatcher with the `x-istara-agent-engine` header over real ASGI routes (reuse the
   `tests/pi_production/harness.py` ASGI pattern; no direct service calls).
2. **Tier is a field on every record** (`tier: T0|T1|T2|T3`); the report generator hard-fails
   if a table would mix tiers.
3. **Tokens:** Pi side reads exact counts from the usage ledger; legacy side records
   provider-reported usage where the W-era telemetry captures it, else `token_source:
   "estimated"` is stamped on the record. The report renders estimated values with an
   explicit ~ marker and a footnote — the lifecycle Goal 5 gate.
4. **Judging:** judge model ≠ DUT model, engine labels stripped, A/B and B/A passes,
   deterministic checks computed regardless; judge prompt + rubric sha256 in every judge
   record; judge cache keyed (scenario, run, rubric_version).
5. **Statistics:** N≥5 paired runs per scenario for T2; per-scenario paired deltas with
   10k-resample bootstrap 95% CIs; CI-crossing-zero ⇒ "no detected difference".
6. **Fail-closed:** `not_runnable` + reason, never a dropped row.
7. **Hygiene:** results dirs gitignored; manifest with git sha + input sha256; redaction
   before write; secret scan over any report dir before linking.

### 1.2 Scenario pack composition

- **canonical/** — the 15 canonical scenarios re-hosted route-level (source of truth for
  ids: `tests/pi_production/test_scenario_coverage_map.py`). T0/T1.
- **spine/** — full task lifecycle backlog→review on a seeded subset of
  `tests/document_corpus/canonical/`. T2/T3.
- **a2a/** — collaboration/debate/delegation chains. T2/T3.
- **probes/** — system-prompt adherence + injection suite (reuse
  `scripts/security_benchmark.py` patterns). T1/T2.
- **feature-criteria matrix** — compiled from `docs/features/inventory.json` by
  `feature_criteria.py`; underivable features get `criteria: manual` and are counted in
  the report, never skipped.

### 1.3 Tier realization

| Tier | Transport | Model | Cost | Used in |
|---|---|---|---|---|
| T0 | scripted/faux tools, no model | none | free | B1 |
| T1 | loopback stub provider | none | free | B1, probes |
| T2 | live local (Ollama / LM Studio) | owner's local model, pinned tag + digest in manifest | free | B2, B3 high-N |
| T3 | live API (DeepSeek et al.) | owner-approved | **owner-gated envelope** | B3 low-N only |

## 2. Task breakdown

Waves are sequential; tasks inside a wave marked ∥ can run in parallel. Each task is one
CF task sized for a single worker.

### E0 — Build the benchmark assets (blocks everything downstream)

| ID | Task | Deliverable | Depends |
|---|---|---|---|
| E0.1 | Author `tests/pi_benchmark/metrics-schema.json` (per-run record: engine, tier, scenario, seed, rep, tokens{exact\|estimated}, tool metrics, criteria_scores, paired-stat reserved fields) + validator | schema + `test_metrics_schema.py` | — |
| E0.2 ∥ | `runner.py` — paired seeded runner over ASGI with engine header, N-repetition orchestration, manifest + sha256, gitignored `.results/runs/<ts>/`, secret scan | runner + unit tests (T0 self-test) | E0.1 |
| E0.3 ∥ | `scenarios/canonical/` pack — re-host the 15 ids route-level | pack + coverage test asserting all 15 ids present | E0.2 |
| E0.4 ∥ | `feature_criteria.py` compiler over `docs/features/inventory.json` (86 features); manual-criteria counting | compiler + tests | E0.1 |
| E0.5 ∥ | `judge.py` JudgeLayer: blind A/B+B/A, rubric bank per axis, sha256 logging, (scenario, run, rubric_version) cache | judge + tests with stub judge model | E0.1 |
| E0.6 ∥ | `probes/` — adherence + injection suite (protected-block survival incl. spine contract block near `backend/app/api/chat.py`, persona constraints, thinking-leak rate) | probe pack + T1 smoke | E0.2 |
| E0.7 ∥ | Engine-flag plumbing: `--engine pi\|legacy\|both` in `tests/simulation/run.mjs` and `tests/real_user_benchmark/run.mjs` (client already supports it) | flag + one smoke run per harness | — |
| E0.8 ∥ | Legacy per-step usage capture (telemetry-additive registry edit ONLY, per §10.3; fix the chunk-count bug at `tests/benchmarks/long_horizon_runner.py:138` to read the ledger) | edit + regression test proving donor paths untouched (`tests/pi_migration/test_count_to_zero.py` still green, allowlist unchanged) | — |
| E0.9 | `scenarios/spine/` + `scenarios/a2a/` packs on seeded corpus | packs + T1 dry-run | E0.2 |
| E0.10 | `scripts/pi_benchmark_report.py` + `comparison-Istara-pi/` scaffold (README, reports/, gitignore for raw) — all numbers from JSON, tier-mix hard-fail, estimated-token flagging | generator + golden-file test on synthetic records | E0.1 |

### E1 — B1 contract (T0/T1, deterministic, both engines)

| ID | Task |
|---|---|
| E1.1 | Run the 15 canonical scenarios + W2 interactive surfaces through `runner.py` on both engines at T0 and T1; every record schema-valid; zero `not_runnable` on Pi side (legacy `not_runnable` only for documented capability diffs) |
| E1.2 | Freeze B1 as a regression gate: `pytest tests/pi_benchmark/test_b1_contract.py` wraps the run and asserts pass; wire into the repo's standard gate list |

### E2 — B2 breadth (T2 local, free, N≥5)

| ID | Task |
|---|---|
| E2.1 | Preflight: verify local engine (Ollama/LM Studio) reachable; pin model tag+digest into the manifest; record a calibration run |
| E2.2 | Full scenario packs + feature-criteria matrix + probes, N≥5 per scenario per engine, seeds {1..5} fixed |
| E2.3 | Judge pass over B2 outputs (local judge model ≠ DUT model) |
| E2.4 | First full report generation (`pi_benchmark_report.py`) — dry-run of B4 machinery; secret scan; NOT linked as final |

### E3 — B3 depth (T2 high-N + T3 owner-budgeted)

| ID | Task |
|---|---|
| E3.1 | Spine pack end-to-end + A2A pack + memory-load runs (psutil RSS sampler; retrieval precision@1/recall@3 on seeded gold) at T2 high-N (N≥10 where wall-clock permits; actual N recorded, shortfalls logged, never silent) |
| E3.2 | **T3 gate (hard stop):** T2-rehearsal-derived dry-run cost estimate using the pricing table at `labs/pi-replacement/src/raw-llm-capture.mjs:5-10`; present to owner; obtain explicit owner-approved envelope **in chat**, recorded as CF evidence on the benchmark task. $0.409 remaining is presumed insufficient — no T3 run before a new envelope. If owner declines: B3 completes at T2-only, and the report's threats-to-validity section states the missing API-model tier |
| E3.3 | T3 runs within the envelope (per-run cost ceilings enforced by the ledger; judge spend counted inside the same envelope) |
| E3.4 | Final paired statistics: bootstrap CIs, effect sizes, dominance analysis (A2A), Fleiss kappa on multi-coder agreement |

### E4 — B4 report

| ID | Task |
|---|---|
| E4.1 | Generate `comparison-Istara-pi/reports/<ts>/`: `report.md`, self-contained `report.html`, `scorecard.json`; capability-diff table (mid-turn abort, cache accounting, streaming granularity, donor reachability) reported alongside, unscored |
| E4.2 | Secret scan over the report dir; link dated `report.md` from `comparison-Istara-pi/README.md`; append lifecycle ledger entry; hand to owner rollout review (conductor ships — no merge/push by workers) |

## 3. Acceptance criteria

**Global**
- A1. Every emitted run record validates against `metrics-schema.json`; the schema test is green.
- A2. No table in any generated report mixes tiers; `token_source: estimated` values are visibly flagged (Goal 5).
- A3. Every scenario appears in results as passed/failed/`not_runnable`+reason — a completeness check in the report generator asserts (scenarios × engines × tiers-attempted) = rows emitted.
- A4. No hand-written numbers: `report.md`/`report.html`/`scorecard.json` are generated only by `scripts/pi_benchmark_report.py` from JSON records (golden-file test proves determinism on fixed input).
- A5. Donor/legacy protection: `tests/pi_migration/test_count_to_zero.py` green before and after; `legacy_allowlist.yaml` unchanged except nothing (the E0.8 registry edit is telemetry-additive and outside donor paths).

**Per phase**
- B1: both engines complete all 15 canonical scenarios + W2 surfaces at T0/T1 deterministically (two consecutive runs, identical scorable outputs); B1 wrapper test wired as a regression gate.
- B2: N≥5 paired runs per scenario per engine at T2; feature-criteria matrix covers all 86 inventory features (auto + counted `manual`); probes executed; first full report generated and secret-scanned.
- B3: spine + A2A + memory-load complete at T2; T3 either (a) executed inside an owner-approved envelope recorded as CF evidence, or (b) explicitly waived by owner with the waiver recorded — no third state. Paired deltas carry bootstrap 95% CIs; CI-crossing-zero deltas reported as "no detected difference".
- B4: `comparison-Istara-pi/reports/<ts>/` contains all three artifacts; README link present; judge sha256s and raw-artifact index included; threats-to-validity section present.

## 4. Verification (exact commands)

```bash
# E0 asset gates (run after each E0 task, from repo root)
cd backend && python -m pytest ../tests/pi_benchmark/ -x -q                  # new asset tests
cd backend && python -m pytest ../tests/pi_migration/test_count_to_zero.py -q # donor ratchet unchanged
cd backend && python -m pytest ../tests/pi_production/ -q                     # existing suite still green
node --test tests/real_user_benchmark/lib/api-client.test.mjs                 # client contract intact

# Engine-flag smoke (E0.7)
node tests/simulation/run.mjs --engine pi --smoke
node tests/simulation/run.mjs --engine legacy --smoke
node tests/real_user_benchmark/run.mjs --engine both --smoke

# B1 (E1)
cd backend && python -m pytest ../tests/pi_benchmark/test_b1_contract.py -q
python tests/pi_benchmark/runner.py --pack canonical --tier T0 --engine both --n 1 --seed 1
python tests/pi_benchmark/runner.py --pack canonical --tier T1 --engine both --n 1 --seed 1
# determinism: run twice, diff scorable fields
python scripts/pi_benchmark_report.py --check-only .results/runs/<ts1> .results/runs/<ts2>

# B2 (E2)
curl -s http://localhost:11434/api/tags   # or LM Studio equivalent — preflight, model pinned
python tests/pi_benchmark/runner.py --pack all --tier T2 --engine both --n 5 --seeds 1,2,3,4,5
python tests/pi_benchmark/judge.py --runs .results/runs/<ts> --swap-positions
python scripts/pi_benchmark_report.py --runs .results/runs/<ts> --out /tmp/b2-dryrun

# B3 (E3)
python tests/pi_benchmark/runner.py --pack spine,a2a --tier T2 --engine both --n 10 --seeds 1..10
python tests/pi_benchmark/runner.py --dry-run-cost --pack api-tier --tier T3   # → owner gate
# (T3 execution only after owner envelope recorded as CF evidence)

# B4 (E4)
python scripts/pi_benchmark_report.py --runs .results/runs/ --out comparison-Istara-pi/reports/<ts>/
python scripts/security_benchmark.py --scan comparison-Istara-pi/reports/<ts>/   # secret scan
git status --porcelain comparison-Istara-pi/  # only intended artifacts staged

# CF bookkeeping per task (from project root)
compass-forge gate before && compass-forge gate after
compass-forge task evidence <task> --type command --summary "..." --payload-json '{"command":"...","result":"passed"}'
```

Flag spellings above are the contract for E0.2's CLI design; if implementation refines
them, the verification list in the lifecycle file is updated in the same commit.

## 5. Risks & mitigations

| # | Risk | Likelihood | Mitigation |
|---|---|---|---|
| R1 | §10 references assets with line numbers (`metrics-schema.json:121-126`) that don't exist in-tree — spec drift between plan and repo | certain (verified repo-wide, r1) | E0.1 authors the schema first and reserves the paired-stat fields; treat §10's line refs as design intent, not ground truth |
| R2 | T3 budget ($0.409) insufficient; owner may not approve more | high | E3.2 hard gate with dry-run estimate; T2-only fallback path is a first-class outcome with a threats-to-validity note — the pipeline never blocks on T3 |
| R3 | Local T2 engine (Ollama/LM Studio) unavailable or model drift between B2 and B3 | medium | E2.1 preflight; pin model tag + digest in the manifest; B3 refuses to run if digest differs from B2's without an explicit `--allow-model-change` note in the manifest |
| R4 | Judge validity (self-preference, position bias) | medium | judge ≠ DUT model, blind + position-swapped, deterministic checks always alongside; Fleiss kappa reported |
| R5 | Legacy engine can't run some scenarios (by design, W-era capability diffs) | certain for some | fail-closed `not_runnable`+reason; capability-diff table reported unscored — never a silent drop, never counted as a Pi "win" by default |
| R6 | Long T2 wall-clock (packs × 2 engines × N≥5) starves the schedule | medium | runner supports resumable run dirs (skip completed (scenario,engine,seed,rep) tuples); N shortfalls recorded per A3/no-silent-caps |
| R7 | E0.8 registry edit regresses donor paths | low | ratchet test + allowlist diff in the E0.8 gate; edit is telemetry-additive only; instant revert path (single commit) |
| R8 | Secrets/PII leaking into reports or raw captures | low | redaction-before-write (schema_version 3 discipline), secret scan gate before any linking; results dirs gitignored |
| R9 | Concurrent workers in the shared worktree colliding on lifecycle/ledger | medium | `repo_lock.completion_lock` + `commit_paths` for every lifecycle touch; path-scoped commits only |

## 6. Rollback

The benchmark program is **additive by construction**: everything new lives under
`tests/pi_benchmark/`, `comparison-Istara-pi/`, and `scripts/pi_benchmark_report.py`;
run outputs live in gitignored `.results/` dirs. Rollback is therefore cheap and layered:

1. **Per-task:** each E-task is one path-scoped commit — `git revert <sha>` removes it
   without touching neighbours.
2. **The one non-additive edit (E0.8 legacy usage capture):** isolated in its own commit;
   revert restores the registry byte-for-byte; the ratchet test proves donor-path
   integrity both before and after.
3. **Reports:** a bad report dir is deleted and the README link removed (one commit);
   regeneration from the retained JSON records is deterministic (A4), so no data is lost.
4. **Whole-program abort:** `git revert` of the E-series commits on `Review_pi_test` (or
   conductor drops the branch pre-ship); no production code path depends on
   `tests/pi_benchmark/`, so the product is unaffected at every rollback layer.
5. **Never rolled back:** CF evidence rows and lifecycle ledger entries (append-only) —
   corrections are appended per the L-26/L-27 precedent, not rewritten.
