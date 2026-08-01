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
