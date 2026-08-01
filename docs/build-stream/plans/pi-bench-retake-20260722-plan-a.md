# Plan A — Pi benchmark retake: B0 gate, B1…B_N DeepSeek waves, post-run Kimi judging

- **Task:** `PI-BENCH-RETAKE-20260722-PLAN-A` (consensus architect slot A, pipeline
  `PI-BENCH-RETAKE-20260722`) · **Spec:** CF-SPEC-9
- **Lifecycle:** `docs/build-stream/2026-07-22-pi-benchmark.md` (execution authority)
- **Brief:** `docs/build-stream/conductor-instructions/pi-benchmark-retake-20260722.md`
- **Authored:** 2026-07-22, against branch `conductor/pi-bench-retake-20260722` @ `3a226139`
- **Author model:** claude-fable-5 (effort=medium)

## 0. Role contract (authoritative for this retake)

- **DUT:** Istara's original agentic loop (`engine=legacy`) vs the Pi adaptation
  (`engine=pi`), both through the Istara API/dispatcher path.
- **Evaluation route:** every live DUT call uses only the configured DeepSeek route
  (`deepseek` / `deepseek-v4-pro`, enforced at `tests/pi_benchmark/runner.py:78-79` and
  `tests/pi_benchmark/deepseek_provider.py`). All live traffic — scenario calls, retries,
  preflight, and any in-run DeepSeek judge calls — shares one hard USD 1.00 cumulative
  ledger. There is no per-wave reset.
- **Kimi:** reserved for a separate, artifact-only post-run judging/report BSC session.
  It is **not** a benchmark provider, never appears in the manifest's provider fields,
  never reruns the DUT, and never charges the DUT ledger.
- The prior recovery / role-correction lineages are historical evidence only; this plan
  creates no repairs of their tasks and reuses their *artifacts* (committed code) only.

## 1. Verified current state (exact paths; audited at `3a226139`)

### 1.1 B0 apparatus that already exists (reuse, do not rebuild)

| Asset | Path | Covering tests | Status |
|---|---|---|---|
| Metrics schema (contract) | `comparison-Istara-pi/metrics-schema.json` (12.6K) | `tests/pi_benchmark/test_metrics_schema.py` | green |
| Record validation / shared helpers | `tests/pi_benchmark/schema.py` | `test_metrics_schema.py`, fixture `fixtures/example_run_record.json` | green |
| Paired runner CLI (`--pack --tier --engine --seeds --repeats --plan-only --wave --max-processes --manifest --budget-ledger --live --owner-gate`, flags at `runner.py:523-540`) | `tests/pi_benchmark/runner.py` | `test_runner.py` | green |
| B0 scheduler: run-unit compilation, disjoint round-robin shards, **immutable content-hashed manifest** (`content_sha256` at `scheduler.py:199,214`; fails closed on missing/invalid `max_processes` at `:157,160`; `ManifestConflict` on drift at `:195,216`) | `tests/pi_benchmark/scheduler.py` | `test_scheduler.py` (part of 43-passed focused run) | green |
| Crash-safe cumulative budget ledger (append-only JSONL, `flock` + fsync, reserve→commit/release, `close()` seals; commit>reservation refused at `budget_ledger.py:277`) | `tests/pi_benchmark/budget_ledger.py` | `test_budget_ledger.py` | green |
| Ledger verifier/replayer (`--close` seals) | `tests/pi_benchmark/verify_budget_ledger.py` | `test_verify_budget_ledger.py` | green |
| DeepSeek-only provider gate (constructs only `deepseek`/`deepseek-v4-pro`; runtime key from env/Keychain, memory-only) | `tests/pi_benchmark/deepseek_provider.py` | `test_deepseek_provider.py` | **2 FAILING** (§1.2) |
| Live driver through the real dispatcher path (worst-case reservation before dispatch, `estimate` flag discipline, record identity from the manifest unit) | `tests/pi_benchmark/live_driver.py` | `test_live_driver.py` | green |
| MoA routing truth (`moa_mode: None | self_moa | full_ensemble` at `scheduler.py:56`; downgrade ⇒ `not_runnable`, never success; `validate_topology` spend-free probe) | `tests/pi_benchmark/moa.py` | `test_moa.py` | green |
| JudgeLayer (blind, position-swapped, cached, sha256-logged) + DeepSeek judge_fn on the shared ledger | `tests/pi_benchmark/judge.py`, `deepseek_judge.py`, `judge_config.json` | `test_judge.py`, `test_deepseek_judge.py` | green |
| Scenario packs (canonical 15 ids, spine, a2a) + probes + feature compiler | `tests/pi_benchmark/scenarios/`, `probes/`, `feature_criteria.py` | `test_scenarios.py`, `test_probes.py`, `test_feature_criteria.py`, `test_b1_contract.py` | green |
| Report generator (durable-artifact → `report.md`/`report.html`/`scorecard.json`) | `scripts/pi_benchmark_report.py` (24.3K) | `test_report.py` | green |
| Prior report bundle | `comparison-Istara-pi/reports/20260722T174500Z/`, `article/` | n/a (artifact) | present |

Verified suite tally at `3a226139` (python3.11, offline, no servers/models/credentials):

- `python3 -m pytest tests/pi_benchmark/ -q` → **170 passed, 2 failed**
- `python3 -m pytest tests/pi_benchmark/test_scheduler.py tests/pi_benchmark/test_budget_ledger.py tests/pi_benchmark/test_moa.py -q` → 43 passed

### 1.2 Verified defects and gaps (the retake's actual work)

- **G-1 (blocker): provider reservation/commit seam.**
  `test_deepseek_provider.py::test_chat_happy_path_commits_actual_cost` and
  `::test_preflight_is_a_minimal_ledgered_call` fail with
  `LedgerStateError: commit … exceeds its reservation` (`budget_ledger.py:277` vs
  `deepseek_provider.py:263`). The F-6 ledger hardening (commit ≤ reservation) landed,
  but the provider's worst-case pre-dispatch estimate can under-reserve. This is exactly
  the class of bug the fail-closed ledger exists to catch; it must be fixed **in the
  provider's estimator** (reserve a true worst case), never by loosening the ledger.
- **G-2 (blocker): owner-gate artifacts are stale and unbound.**
  `_enforce_owner_gate` (`runner.py:472-478`) only checks that a gate *file exists*.
  The checked-in `tests/pi_benchmark/gates/g1_owner_gate.json` /`g2_owner_gate.json` are
  prior-lineage approvals (both `2026-07-22T14:32:34Z`; G1 names judge model
  `gpt-5.6-luna`, contradicting current policy; G2 approves `$0.50`). As-is, a stale file
  can authorize new spend. The retake needs gate→manifest binding (§2.3).
- **G-3: the execution work order `docs/build-stream/conductor-instructions/`
  `pi-benchmark-deepseek-moa-execution.md` does not exist on this branch** (only the
  retake brief + three older instruction files are present), even though the retake brief
  lists it as read-first. It was never committed by the prior lineage. The retake must
  not depend on it: this plan is self-contained, and RT-6 records the discrepancy.
- **G-4: stale Kimi-as-evaluation text** remains in the lifecycle file's embedded
  winning-plan section (e.g. acceptance A3/A4/A7 and §5 commands citing
  `--provider kimi`). The role-correction consensus that would have fixed it was
  invalidated and never implemented. Handled append-only via a DEC entry (RT-6), not by
  editing history — and per the brief, not during this planning stage.
- **G-5: no `backend/.venv` in this worktree.** Verification commands below use the
  system `python3` (3.11). Wave execution must pin one interpreter in the manifest env
  block so B0 and B_i runs are comparable.

## 2. Design

### 2.1 Wave topology and the immutable manifest

```
B0 (offline gate) ──► B1 ──► B2 ──► … ──► B_N ──► POST (coordinator aggregation)
                                                      └─► separate BSC session: Kimi judging/report (artifact-only)
```

**Three integers, three meanings — recorded as three distinct manifest keys:**

- `max_processes` (**N**): the machine/run bound on concurrently existing benchmark
  worker processes, and therefore the number of process-indexed waves B1…B_N and the
  shard count. Discovered and fixed at B0 (`min(physical_cores - 2, owner_cap)`, ≥1);
  the scheduler already fails closed if it is missing or ≠ shard count
  (`scheduler.py:157,160`).
- `moa_n`: MoA samples per MoA-mode run unit (runner default 3, `runner.py:106`;
  manifest is source of truth per `runner.py:385-389`). Orthogonal to N: it shapes a
  *single unit's* internal fan-out, not process count.
- `repeats`: seeded repetitions per scenario×engine cell (statistical power). Also
  orthogonal to N; it multiplies run units, which the scheduler then shards.

The manifest is written once by `--plan-only`, content-hashed (`content_sha256`), and
immutable: identical re-invocation resumes; any drift raises `ManifestConflict`. The
retake adds `run_id: "PI-BENCH-RETAKE-20260722"` and the pinned interpreter/env
fingerprint to the manifest payload so gate binding (§2.3) and resume are run-exact.

Wave rules (already enforced, kept as acceptance): each B_i owns exactly shard i
(disjoint by construction); resume counts only parseable schema-valid records; no unit is
dropped — terminal states are `completed`, `not_runnable`, or `budget_blocked` with a
machine-readable reason.

### 2.2 Budget safety (unchanged contract, one fix)

One append-only, crash-safe ledger file for the entire run
(`.results/runs/<run>/budget-ledger.jsonl`): reserve worst-case before dispatch, commit
provider-reported actuals after, release only pre-dispatch, `budget_exceeded` when
reservation+committed would cross `budget_cap_usd=1.00`, `close()` seals after B_N.
`verify_budget_ledger.py --close` is the POST-stage proof. RT-1 fixes the provider
estimator so reservation ≥ any committable actual (G-1); the ledger's refusal semantics
are not relaxed. Preflight is a ledgered minimal call, not a scenario. The DeepSeek
credential is resolved at runtime (env/Keychain), held in memory, and never written to
prompts, logs, manifests, records, or reports; route evidence in records is redacted
fingerprints only (host+model hash, no keys, no full URLs with tokens).

### 2.3 Owner gates before any live DeepSeek spend

Two blocking gates, each an explicit in-chat owner approval recorded as CF evidence
**and** a gate artifact bound to this run:

- **G-RT1 (live-model permission):** owner authorizes live DeepSeek DUT traffic for this
  retake. Artifact must carry `run_id` and the B0 manifest `content_sha256`.
- **G-RT2 (budget envelope):** owner approves `budget_cap_usd=1.00` against the B0
  dry-run worst-case estimate for the *complete* B1…B_N schedule including retries and
  preflight; if the estimate exceeds $1.00, B0 blocks with no live call.

RT-2 hardens `_enforce_owner_gate` to verify, not just existence, but:
`gate_id`, `status=APPROVED`, `run_id` == manifest `run_id`,
`manifest_sha256` == manifest `content_sha256`, `provider/model` == the pinned DeepSeek
route, and cap == 1.00. Stale artifacts (the two currently checked in) then fail closed
with a distinct exit and message. The stale files are kept as negative-test fixtures
(moved under `fixtures/stale_gates/`) so history is preserved and the refusal is tested.

### 2.4 MoA truthfulness (preserve, verify, do not weaken)

`self_moa` and `full_ensemble` are manifest-recorded modes per run unit. Truth rules
already implemented in `moa.py`/`live_driver.py` and kept as acceptance:

- Requested coder/route width is required; served routes are determined by successful
  `route_evidence` only.
- Any downgrade — `full_ensemble → dual_run/self_moa`, diversity collapse to
  `single_coder`, endpoint substitution, or route rejection — yields `degraded=true` and
  the record is `not_runnable` (or `budget_blocked`), **never** an ensemble success.
- Selected-but-failed endpoints remain provenance only; consensus score/confidence are
  retained on the record; no embedding or auxiliary dispatch outside the ledger.
- `moa.validate_topology` runs spend-free in B0 as part of the gate.

### 2.5 Post-run separation: Kimi judging/report session

Only after **all** of B1…B_N are terminal, the ledger reconciles and is sealed
(`--close`), and POST aggregation has produced the durable bundle, the owner launches a
**distinct BSC session** whose inputs are artifacts only:

- Input packet: `.results/runs/<run>/` records + manifest + sealed ledger,
  `comparison-Istara-pi/reports/<ts>/` (`scorecard.json`, `report.md`, `report.html`),
  judge cache, and the lifecycle file.
- That session uses Kimi as judge/report author. It makes **zero** Istara/DeepSeek DUT
  calls, cannot append to the (sealed) DUT ledger, and any Kimi cost is accounted in
  that session, not here. It may re-score from records and author the final comparative
  report/scorecards.
- Enforcement is structural: the sealed ledger refuses appends (`LedgerClosed`), the
  packet contains no DUT credentials, and the retake pipeline's ship step ends at POST.

## 3. Task breakdown

| # | Task | Files (primary) | Depends | Est |
|---|---|---|---|---|
| RT-1 | Fix provider worst-case reservation so commit ≤ reservation always holds (estimator, not ledger); make the 2 red tests + suite green | `tests/pi_benchmark/deepseek_provider.py`, `test_deepseek_provider.py` | — | S |
| RT-2 | Gate→run binding: strict `_enforce_owner_gate` schema/run checks; relocate stale gate files to `fixtures/stale_gates/` as refusal fixtures; new tests | `tests/pi_benchmark/runner.py`, `test_runner.py`, `tests/pi_benchmark/gates/`, `fixtures/` | — | S/M |
| RT-3 | Manifest retake keys: `run_id` + interpreter/env fingerprint in the manifest payload (hash-covered); explicit `max_processes` vs `moa_n` vs `repeats` docstring + a test asserting all three round-trip distinctly | `tests/pi_benchmark/scheduler.py`, `test_scheduler.py`, `runner.py` | — | S |
| RT-4 | B0 gate run (offline): discover and record N; `--plan-only` manifest; `validate_topology`; ledger verifier on the empty ledger; dry-run worst-case cost estimate for the full B1…B_N schedule | `.results/runs/pi-bench-retake-20260722/` (gitignored artifacts) | RT-1..3 | S |
| RT-5 | Owner gates G-RT1/G-RT2 (blocking evidence tasks; owner-only; includes ledgered DeepSeek preflight after approval) | gate artifacts + CF evidence | RT-4 | — |
| RT-6 | Lifecycle DEC append (append-only): retake supersedes the embedded winning-plan's stale Kimi-as-evaluation text (G-4) and records the missing moa-execution work order (G-3); README refresh for RT-1..3 | `docs/build-stream/2026-07-22-pi-benchmark.md` (append), `tests/pi_benchmark/README.md` | RT-1..3 | S |
| RT-7 | Live waves B1…B_N: `--wave i --max-processes N --live --owner-gate <G-RT1/2>` per shard; per-wave ledger reconciliation before advance | runtime artifacts only | RT-5 | M/L |
| RT-8 | POST: coordinator aggregation, reproducibility diff, secret scan, seal ledger; assemble the Kimi judging input packet; hand to owner for the separate judging session | `scripts/pi_benchmark_report.py` outputs under `comparison-Istara-pi/reports/<ts>/` | RT-7 | S/M |

Suggested cast: one implementer (RT-1/2/3/6), one independent code reviewer, executor
lane(s) for RT-7 under the single conductor, owner for RT-5. No task edits backend/
product code; the security-benchmark gate is not triggered unless a reviewer forces a
product-side change (none is planned).

## 4. Acceptance criteria

- **A1** `python3 -m pytest tests/pi_benchmark/ -q` fully green (172+ passed, 0 failed)
  after RT-1..3; no ledger semantics loosened (commit>reservation still refused,
  covered by an explicit test).
- **A2** B0 manifest exists, is content-hashed and immutable (re-run resumes unchanged;
  mutation attempt ⇒ `ManifestConflict`), and records `run_id`, integer
  `max_processes=N`, `moa_n`, `repeats` as three distinct keys plus the pinned env.
- **A3** No live call is possible without both G-RT1 and G-RT2 artifacts that match this
  run's `run_id` + manifest hash; the stale prior-lineage gate files provably fail
  (negative tests). Owner approvals are recorded as CF evidence before any spend.
- **A4** Every live call: DeepSeek route only, reserve-before-dispatch, ledgered actuals,
  cumulative spend ≤ $1.00, `budget_exceeded/budget_blocked` on the margin; retries and
  preflight draw the same envelope; records carry redacted route fingerprints and
  explicit `estimate` flags; no credential material anywhere in artifacts.
- **A5** MoA truth: requested vs served mode/width recorded; any downgrade ⇒ degraded ⇒
  `not_runnable`, never success (existing tests stay green; RT-7 spot-audits live
  records for `moa_mode` units).
- **A6** Each B_i owns a disjoint shard, ≤ N worker processes exist at any time, resume
  never duplicates records or ledger rows, and no unit is silently dropped.
- **A7** POST: all units accounted across B1…B_N; `verify_budget_ledger.py --close`
  seals with spend ≤ $1.00; report bundle regenerates byte-identically
  (`scorecard.json` diff empty) from the same records; secret scan clean.
- **A8** Kimi separation: the judging session starts only after A7, consumes the
  artifact packet, makes no DUT/DeepSeek call, and appends nothing to the sealed ledger.

## 5. Verification matrix (exact commands; offline unless owner-gated)

| Stage | Command | Expect |
|---|---|---|
| RT-1..3 unit | `python3 -m pytest tests/pi_benchmark/ -q` | all pass, 0 failed |
| Ratchet | `python3 -m pytest tests/pi_migration/test_count_to_zero.py -q` | 3 passed (0 product sites) |
| Production ladder (unchanged by this plan; run once after RT-1..3 to prove no drift) | `python3 -m pytest tests/pi_production/ -q` | green |
| Hygiene | `git diff --check` | clean |
| B0 manifest | `python3 tests/pi_benchmark/runner.py --pack canonical,spine,a2a --tier T2 --engine both --repeats 5 --plan-only --max-processes <N> --manifest .../manifest.json --out .../b0-gate` | immutable manifest, N shards; re-run ⇒ resume; edited arg ⇒ `ManifestConflict` |
| B0 topology | MoA `validate_topology` probe (via its test / `--plan-only` output) | fail-closed chain proven, zero spend |
| B0 ledger | `python3 tests/pi_benchmark/verify_budget_ledger.py --runs .../b0-gate --cap-usd 1.00` | pass, spend $0.00 pre-gate |
| Gate refusal | `runner.py --wave 1 --live --owner-gate tests/pi_benchmark/fixtures/stale_gates/g1_owner_gate.json …` | refusal exit ≠ 0, stale-gate message |
| Preflight (post-G-RT1/2 only) | `runner.py --preflight … --owner-gate <fresh>` | one minimal ledgered call, key never printed |
| Wave i (owner-gated) | `runner.py --wave <i> --max-processes <N> --manifest … --budget-ledger … --live --owner-gate <fresh>` | shard i terminal, ledger reconciles |
| POST | `python3 scripts/pi_benchmark_report.py --runs … --out comparison-Istara-pi/reports/<ts>` then rerun to tmp + `diff` sorted `scorecard.json`; `verify_budget_ledger.py --close` | reproducible bundle; sealed ledger ≤ $1.00 |

## 6. Risks

- **R1** Provider estimator fix (RT-1) could over-reserve and spuriously
  `budget_exceeded` small calls. Mitigate: estimator test pins worst case within a
  factor bound of actual pricing table; dry-run estimate (RT-4) re-checked against cap.
- **R2** Real B0 dry-run estimate may exceed $1.00 for the full schedule. Then B0 blocks
  (by design); options recorded for the owner: reduce `repeats`, shrink T2 slice —
  never raise the cap unilaterally.
- **R3** Gate hardening (RT-2) may break existing runner tests that use the old gate
  files. Mitigate: fixtures move with the tests; negative tests added in the same task.
- **R4** Live-wave wall-clock and DeepSeek availability are unknown; a mid-wave crash is
  covered by manifest resume + ledger replay (crash-safety already tested), but repeated
  provider outages can strand units `budget_blocked`. They are reported, not retried
  past the envelope.
- **R5** Stale-text confusion (G-4): a future agent might follow the embedded winning
  plan's `--provider kimi` commands. RT-6's DEC append is the mitigation; the runner's
  hard DeepSeek-only rejection is the backstop.
- **R6** This worktree has no `backend/.venv`; interpreter drift between B0 and waves is
  possible. Mitigated by the manifest env fingerprint (RT-3): the runner refuses a wave
  whose interpreter fingerprint mismatches the manifest.

## 7. Rollback

- RT-1..3/6 are ordinary commits on this branch touching only `tests/pi_benchmark/`,
  `tests/pi_benchmark/README.md`, and an append-only lifecycle entry: rollback is
  `git revert` of those commits; no product code, migrations, or contracts move.
- Run artifacts live under gitignored `.results/`; abandoning a run deletes nothing
  tracked. The ledger is append-only — a rolled-back run's spend remains visible and
  still counts against the $1.00 envelope (by design; the envelope is cumulative).
- Gate artifacts are revocable by the owner at any time; deleting/withdrawing them
  fail-closes all further live dispatch immediately.
- If the retake is abandoned entirely, the branch is discarded before ship; `main` is
  untouched (the conductor's ship stage is the only merge path).

## 8. Changed-file scope (narrow, code only in the benchmark package)

```
tests/pi_benchmark/deepseek_provider.py        (RT-1)
tests/pi_benchmark/test_deepseek_provider.py   (RT-1)
tests/pi_benchmark/runner.py                   (RT-2, RT-3)
tests/pi_benchmark/test_runner.py              (RT-2)
tests/pi_benchmark/scheduler.py                (RT-3)
tests/pi_benchmark/test_scheduler.py           (RT-3)
tests/pi_benchmark/gates/ → fixtures/stale_gates/ (RT-2, git mv)
tests/pi_benchmark/README.md                   (RT-6)
docs/build-stream/2026-07-22-pi-benchmark.md   (RT-6, append-only)
```

No `backend/` edits, no allowlist changes, no master-plan edits, no schema changes
(`metrics-schema.json` untouched). Anything beyond this list is out of scope and becomes
a new CF task.
