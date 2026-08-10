# Independent Plan B — Fresh Pi Benchmark Retake

**Task:** `PI-BENCH-RETAKE-20260722-PLAN-B`  
**Spec:** `CF-SPEC-9`  
**Role:** `pi-bench-retake-20260722-architect-b`  
**Status:** candidate plan; planning only; no live calls authorized  
**Authority:** the fresh-retake work order and
`docs/build-stream/conductor-instructions/pi-benchmark-deepseek-moa-execution.md`.
Older benchmark/recovery plans, approvals, reports, and consensus state are historical
inputs only and are not authority for this run.

## 1. Outcome, scope, and non-goals

Build a reproducible retake that compares Istara's original agentic loop with the Pi
adaptation on identical work through Istara's API/`AgenticDispatcher` boundary. B0 freezes
one strict run manifest. B1 through B_N execute the manifest's disjoint process shards with
only the configured `deepseek` / `deepseek-v4-pro` route and one crash-safe cumulative
`budget_cap_usd=1.00` ledger. After every wave is terminal and the ledger is verified and
sealed, a different Build Stream Conductor run may give a frozen, hash-verified artifact
packet to Kimi for judging and report generation. Kimi never dispatches the DUT and never
uses the DUT ledger.

This plan does not:

- reuse or mutate prior retake/recovery tasks, approvals, manifests, ledgers, or reports;
- edit `docs/build-stream/plans/2026-07-20-pi-full-replacement-master-plan.md`;
- change the product's default engine, provider registry, Research Spine gates, or legacy
  retirement state;
- make live calls, start servers, load models, read credentials, judge another plan, or
  publish a report during planning or implementation verification;
- treat model-free fixtures, synthetic records, an endpoint alias, or an old report as
  evidence that a live benchmark completed.

## 2. Verified B0 apparatus at plan time

The following paths exist in the retake worktree and are the starting point. Their tests
are model-free and use injected transports/fakes unless explicitly owner-gated later.

| Capability | Existing implementation | Existing proof | Retake disposition |
|---|---|---|---|
| Record contract | `comparison-Istara-pi/metrics-schema.json`; `tests/pi_benchmark/schema.py`; golden record `tests/pi_benchmark/fixtures/example_run_record.json` | `tests/pi_benchmark/test_metrics_schema.py` | Reuse; extend provenance/route and artifact-terminal fields without weakening current validation. |
| Strict offline scheduling | `tests/pi_benchmark/scheduler.py`: deterministic units, round-robin shards, content hash, conflict refusal, valid-record resume | `tests/pi_benchmark/test_scheduler.py` | Harden into a run-bound B0 manifest with explicit `run_id`, input digests, gate digests, `max_processes`, `moa_n`, and `repeats`. |
| Paired runner | `tests/pi_benchmark/runner.py`: both engines, T0/T1, `--plan-only`, `--wave`, live consent, provider/model rejection | `tests/pi_benchmark/test_runner.py`; `tests/pi_benchmark/test_b1_contract.py` | Reuse the single paired runner; remove ambiguous phase/wave coupling and enforce all runtime arguments against the frozen manifest. |
| Crash-safe spend ledger | `tests/pi_benchmark/budget_ledger.py`: append-only JSONL, `flock`, `fsync`, reserve/commit/release/close, idempotency and hard cap | `tests/pi_benchmark/test_budget_ledger.py`; `tests/pi_benchmark/verify_budget_ledger.py`; `tests/pi_benchmark/test_verify_budget_ledger.py` | Reuse; bind rows and close record to this `run_id`, correlate every live attempt, and require a verified terminal close before artifact freeze. |
| DeepSeek isolation/preflight | `tests/pi_benchmark/deepseek_provider.py`: rejects every non-approved provider/model, runtime-only key loading, reserve-before-call, exact usage, redacted endpoint fingerprint | `tests/pi_benchmark/test_deepseek_provider.py` | Keep only as the DeepSeek route/preflight/accounting adapter. It must not be a benchmark judge. |
| Live execution | `tests/pi_benchmark/live_driver.py`: dispatcher call, record-at-a-time atomic writes, usage exact/estimated tagging, budget blocks, route admission | `tests/pi_benchmark/test_live_driver.py` | Replace smoke-only/direct-dispatch assumptions with the real route adapter for scenario work; retain dispatcher-level MoA where no public ensemble route exists. Prove both arms cross the production boundary. |
| MoA truth | `tests/pi_benchmark/moa.py`: requested/served method, response/coder counts, route evidence, consensus, downgrade detection | `tests/pi_benchmark/test_moa.py` | Reuse and strengthen redaction. A full ensemble with fewer than `moa_n` distinct successful served routes stays degraded/blocked. |
| Packs and axes | `tests/pi_benchmark/scenarios/`; `feature_criteria.py`; `probes/` | `test_scenarios.py`; `test_feature_criteria.py`; `test_probes.py` | Freeze their content hashes into B0 and cover canonical, features, spine, A2A, probes, and usage. No pack may silently disappear. |
| Report code | `scripts/pi_benchmark_report.py` | `tests/pi_benchmark/test_report.py` | Make it consume only the post-run judged packet and fail closed on incomplete waves, open ledger, missing hashes, invalid pairs, or missing judgments. |
| Current generated output | `comparison-Istara-pi/reports/20260722T174500Z/`; `comparison-Istara-pi/article/results_summary.md` | none establishing the fresh-run contract | Historical/non-authoritative. Do not use it as a retake input or overwrite it. |

### Current gaps that prevent a live retake

1. `runner._enforce_owner_gate` accepts any existing file; the tracked
   `tests/pi_benchmark/gates/g1_owner_gate.json` and `g2_owner_gate.json` belong to an
   earlier run and conflict with the fresh USD 1.00 contract. Presence is not approval.
2. `scheduler.py` hashes a useful schedule, but it does not bind a fresh `run_id`, source
   revision/dirty state, scenario/rubric/schema digests, approval digests, or artifact
   protocol. `run_wave` does not reject a CLI `max_processes` that differs from the
   manifest.
3. `live_driver.py` invokes the dispatcher directly and its default prompt is explicitly a
   route smoke prompt, not the full scenario corpus. Route-level scenario coverage must use
   the real authenticated Istara API seam where one exists, with engine selection flowing
   through the request boundary; MoA may call the dispatcher entry only for the ensemble
   operation that has no public route.
4. Live full-ensemble execution currently pins one allowed endpoint with
   `distinct=False`, so it is expected to degrade. That is honest for a one-route topology,
   but cannot be reported as ensemble success. Any clean success requires `moa_n` distinct
   approved DeepSeek route slots actually served; otherwise the unit remains terminal
   `degraded` or `blocked` and is counted.
5. Route evidence currently retains raw endpoint IDs. The retake requires stable redacted
   route-slot IDs and a secret/endpoint leak scan while still proving distinctness.
6. `deepseek_judge.py`, `judge_config.json`, and their README text encode the superseded
   DeepSeek-as-judge policy. They must not run in B0..B_N. Kimi judging belongs to a later,
   artifact-only BSC session with its own authorization and cost boundary.
7. Existing report code/output can produce a polished verdict without proving the fresh
   manifest, wave barrier, sealed ledger, route evidence, and judgment completeness. The
   post-run artifact verifier must become the only report entry gate.
8. The planning baseline `python -m pytest tests/pi_benchmark/ -q` is not green: 170 tests
   pass and two fail in `test_deepseek_provider.py`. `DeepSeekProvider.chat` reserves from
   the request-side estimate but the fake provider's reported cache-miss/output usage can
   cost more (`0.002154 > 0.001127` for `judge-1`; `0.000512 > 0.000008` for preflight), so
   `BudgetLedger.commit` correctly refuses an under-reserved call. This is a real fail-closed
   baseline defect, not planning noise: T3 must make the pre-dispatch reservation a true
   worst-case bound and retain the ledger's no-overcommit invariant.

## 3. Design

### 3.1 One immutable run identity and manifest

B0 creates exactly one `run_id` and one canonical JSON manifest under a new gitignored
`tests/pi_benchmark/.results/<run_id>/`. The content hash excludes only the creation
timestamp. Once written, different input is a hard `ManifestConflict`; a retry with
identical input is byte-preserving and resumes.

Required immutable fields:

- `manifest_schema_version`, `run_id`, clean source `git_sha`, schema hash, runner hash,
  pack/scenario hashes, rubric/probe hashes, and the exact paired arm set `{legacy, pi}`;
- `provider=deepseek`, `model=deepseek-v4-pro`, `budget_cap_usd=1.00`, pricing version,
  credential source name only (never value), and redacted route-slot commitments;
- `max_processes=N`, `shard_count=N`, explicit wave IDs `B1` ... `B_N`, and the mapping of
  every unit to exactly one wave;
- separate integers `moa_n`, `repeats`, and seeds. `max_processes` controls concurrent
  worker/shard count only; `moa_n` controls samples/coders inside a MoA unit; `repeats`
  controls paired statistical repetitions. None may default from another;
- all work packages: canonical 15-scenario contract, feature/breadth criteria, Research
  Spine lifecycle, A2A, prompt/injection probes, token/usage accounting, plus plain,
  `self_moa`, and `full_ensemble` modes where eligible;
- unit identity, pair identity, engine, tier, pack, scenario, seed, repeat, MoA mode,
  maximum tokens, worst-case reservation, wave ID, and terminal-status vocabulary;
- digests of two fresh run-bound owner approval artifacts. The approvals live beside the
  run, not in tracked reusable fixtures.

The immutable manifest never stores mutable `pending -> complete` state. Atomic run records
and a separate append-only event index project progress. A unit is terminal only when its
record validates and is one of `completed`, `not_runnable`, `budget_blocked`, `degraded`, or
`blocked`; corrupt or missing records remain pending. Every manifest unit must be terminal
before the B-wave barrier passes.

`N` is discovered in B0 with a passive capacity calculation (CPU/memory/file-descriptor
limits plus a configured safety ceiling) and recorded as `max_processes`. The owner sees
the proposed literal value and workload/cost estimate before approval. B0 does not infer N
from `moa_n`, repeats, scenario count, or provider capacity.

### 3.2 Owner gates and the USD 1.00 ledger

There are two explicit, fresh, run-bound owner gates before the first live DeepSeek byte:

- **G1 — live-DUT authorization:** owner approves this `run_id`, clean git SHA, the only
  provider/model, the API/dispatcher route, exact scenario/MoA scope, redacted evidence
  policy, and the bounded DeepSeek preflight. No old gate file satisfies G1.
- **G2 — spend authorization:** owner approves `budget_cap_usd=1.00`, the pricing/version,
  B0 worst-case estimate, `max_processes`, `moa_n`, repeats, retry policy, and the fact that
  preflight, retries, plain calls, and all MoA samples share the same ledger. Approval is
  rejected if its manifest/run digest differs.

The gate verifier parses required fields, status, signer/actor evidence, timestamps,
`run_id`, manifest preimage digest, and exact cap/provider/model; existence alone never
passes. The finalized manifest stores the approval digests. Any mismatch, absent approval,
dirty revision, or cap other than 1.00 fails before credential resolution and before
reservation.

After G1/G2, B0 may perform exactly the manifest-declared minimal reachability preflight.
It reserves worst-case cost before dispatch and commits provider-reported usage; a
post-dispatch unknown retains the reservation. B1..B_N use the same JSONL ledger and the
same lock. Retries receive unique attempt IDs under the same unit ID and never bypass an
existing worst-case reservation. A budget refusal creates a terminal `budget_blocked`
record without dispatch.

After the wave barrier, `verify_budget_ledger.py --close` must replay the ledger, correlate
every call/attempt to a manifest unit or the single preflight, prove total committed plus
retained worst-case reservations is `<= 1.00`, append one idempotent close row, fsync, and
prove reopening refuses any mutation. Unknown-usage reservations may remain charged at
worst case, but must be explicit in the close summary rather than erased.

### 3.3 DUT and routing boundary

The paired scenario driver uses the same immutable prompt/input hash, seed, project fixture,
and limits for both arms, alternates arm order, and captures raw outputs before judging.

- For product scenarios with a public route, call the real authenticated ASGI/HTTP API
  (the established `/api/chat` seam is proven by
  `tests/pi_production/test_chat_pi_asgi.py`) and select `legacy` versus `pi` through
  `x-istara-agent-engine`. Capture the route/service response, tool events, persistence
  handles, usage, and dispatcher evidence. Test injection may replace only network/provider
  transport, not the API, middleware, route, or dispatcher.
- For `agentic.ensemble`/MoA, where there is no public HTTP ensemble endpoint, enter at
  `AgenticDispatcher.ensemble` with the same project scope and explicit engine. Record that
  boundary type in provenance; never call `DeepSeekProvider.chat` as a substitute DUT.
- Admit only route evidence whose runtime provider/model are DeepSeek/deepseek-v4-pro and
  whose slot is committed in the manifest. Raw URLs, keys, endpoint fingerprints, and raw
  private endpoint IDs never reach records. In memory, map each successful route to a
  deterministic per-run pseudonym; distinctness is computed before redaction and the
  pseudonymous cardinality is retained.

`self_moa` requests exactly `moa_n` temperature samples on one admitted route and records
temperatures, response/coder count, consensus, source unit IDs, and one served route.
Partial responses or anomalous multiple routes are degraded.

`full_ensemble` requests `moa_n` distinct admitted logical route slots, all resolving to
the approved DeepSeek model. A spend-free topology check records the available distinct
slots before live execution. Live success requires the served method to remain
`full_ensemble`, `response_count == coder_count == moa_n`, and `moa_n` distinct successful
served routes. `dual_run`, `self_moa`, a single coder, a repeated endpoint, partial success,
or missing route evidence is terminal degraded/blocked—not a successful ensemble. If the
configured topology has only one route, the retake records that limitation rather than
inventing aliases or silently using another provider.

Research outputs remain provisional benchmark evidence. The driver records Research Spine
phase, grounding/source-unit handles, coder/reconciliation status, and downgrade evidence;
it does not promote nuggets, facts, insights, recommendations, tasks, or reports as
human-approved Done.

### 3.4 B0 -> B1..B_N execution and barrier

1. **B0 offline:** run the full model-free suite; assert clean source; compute scenario and
   code digests; discover and record literal N; compile all paired units; calculate
   per-unit and cumulative worst-case spend; write and reload the manifest; prove shard
   disjointness/completeness and resume conflict behavior. No key or network access.
2. **Owner barrier G1/G2:** present the exact manifest preimage and estimate. Do not create
   a reusable tracked approval. Stop if either is absent or mismatched.
3. **B0 charged preflight:** use the same ledger and one declared preflight call. Confirm
   route admission and record only redacted evidence. A failed/uncertain preflight blocks
   B waves without switching provider.
4. **B1..B_N:** launch at most N worker processes, one immutable shard per process wave.
   A worker may resume its own incomplete units but may not claim another wave or mutate
   the manifest. Lock-protected reservations serialize spend admission. Budget/topology
   failures become counted terminal records. No per-wave ledger reset.
5. **Convergence barrier:** require all N wave IDs and every manifest unit terminal; validate
   all pairs and records; replay and seal the ledger; write an append-only convergence
   summary. Aggregation is coordinator work, not `B_(N+1)`.
6. **Artifact freeze:** create an inventory of every manifest, record, raw output,
   reconciliation/route evidence, ledger, close summary, and rubric with SHA-256 and size;
   run the secret/private-route scan; then write a read-only packet digest. A failed scan
   blocks judging and publishing.

### 3.5 Separate Kimi judging/report run

Only after the convergence and artifact-freeze checks pass does the operator/conductor
create a new CF spec/task/cast and a new lifecycle/session for Kimi. The handoff contains
only the frozen packet path, packet digest, scoring rubric, blind arm mapping instructions,
and expected outputs. It contains no DeepSeek credential, writable DUT config, server
command, benchmark runner command, or DUT ledger mutation capability.

The artifact-only session:

- verifies the packet digest before reading, blinds engine labels, position-swaps paired
  outputs, and caches one judgment per `(run_id, pair_id, rubric_version, judge_model)`;
- records Kimi judgments and its own session/cost evidence outside the DUT ledger;
- cannot import/call `runner.py`, `live_driver.py`, `deepseek_provider.py`, or a live Istara
  route; a test rejects any judging command/config containing those entry points;
- feeds complete judgments plus deterministic metrics into
  `scripts/pi_benchmark_report.py`, which generates a new timestamped `report.md`,
  `report.html`, `scorecard.json`, and per-judgment files;
- refuses a verdict if inputs are incomplete, ledger not closed, packet hash changed,
  invalid pairs were silently dropped, or any result claims a degraded full ensemble as
  success. Existing dated reports remain historical and unchanged.

## 4. Implementation task graph

| Task | Change | Primary files | Depends on | Definition of ready / exit |
|---|---|---|---|---|
| T1 | Freeze retake contracts and negative fixtures | `comparison-Istara-pi/metrics-schema.json`, `tests/pi_benchmark/schema.py`, new retake fixtures/tests | — | Current schema/tests green; exit adds run, route-redaction, terminal-state, and artifact fields with negative cases. |
| T2 | Strict B0 manifest and wave semantics | `scheduler.py`, `runner.py`, `test_scheduler.py`, `test_runner.py` | T1 | Exit proves byte-stable idempotency, conflict on any bound field, exact B1..B_N partition, and independent N/`moa_n`/repeats. |
| T3 | Run-bound approvals, true worst-case reservation, and ledger closure | new `owner_gate.py` + test; `budget_ledger.py`, `verify_budget_ledger.py`, their tests; `deepseek_provider.py` | T2 | Exit fixes the observed under-reservation failures without allowing commit-over-reservation, proves old/forged/mismatched gates reject before key load, concurrency never exceeds USD 1.00, all attempts correlate, and close seals. |
| T4 | Real paired API/dispatcher capture | `live_driver.py`, `test_live_driver.py`, scenario adapters; reuse route contracts from `test_chat_pi_asgi.py` | T1,T3 | Exit proves both engine headers cross real ASGI for route scenarios, MoA crosses dispatcher, no direct provider-as-DUT path, atomic resume, exact/estimated usage. |
| T5 | Truthful MoA and redacted routing | `moa.py`, `test_moa.py`, manifest route commitments, Research Spine route/coverage tests | T2,T4 | Exit proves one-route self-MoA, clean distinct ensemble, every downgrade/partial/unknown route blocked/degraded, raw IDs absent. |
| T6 | Coverage and offline B0 gate | scenario/feature/probe tests, `test_b1_contract.py`, new manifest-coverage test | T2,T4,T5 | Exit proves every declared pack/arm/mode is mapped once; canonical 15 and Research Spine coverage stay intact. |
| T7 | Convergence and artifact packet verifier | new `artifact_packet.py` + test, report loader/test | T3,T6 | Exit refuses missing wave/unit, open ledger, hash drift, secret/private route, invalid pair, or degraded-as-success; emits deterministic packet digest offline. |
| T8 | Remove in-run judging and define Kimi-only handoff | retire/quarantine `deepseek_judge.py` and contradictory `judge_config.json` use; update `judge.py`, README; add artifact-only judging instruction/config tests | T7 | Exit proves B0..B_N cannot invoke a judge and Kimi session cannot rerun DUT or charge DUT ledger. |
| T9 | Report fail-closed integration and living docs | `scripts/pi_benchmark_report.py`, `test_report.py`, `tests/pi_benchmark/README.md`, affected `docs/features/` | T7,T8 | Exit generates only from a complete judged packet, preserves historical reports, regenerates feature docs, and passes gates/security checks. |
| T10 | Owner-gated execution | gitignored run directory only; CF evidence from root | T1..T9 + fresh G1/G2 | Execute B0/preflight/B1..B_N, converge, seal, scan, freeze; no code change or provider fallback during the run. |
| T11 | Separate Kimi BSC judging/report | new CF spec/task/lifecycle and frozen packet output | T10 | Artifact digest verified; Kimi-only judgment complete; no DUT request and no DUT-ledger row; reports reproducible and secret-scanned. |

T1..T9 are implementation/review work and may be remediated normally. T10 and T11 are
separate owner-gated operational stages; implementation completion never implies live-run
completion.

## 5. Acceptance and verification matrix

| ID | Given / When / Then | Offline verification command |
|---|---|---|
| A1 | Given current B0 assets, when the focused suite runs, then schema, runner, packs, scheduler, ledger, provider, MoA, resume, and report contracts pass without network/model access. | `python -m pytest tests/pi_benchmark/ -q` |
| A2 | Given a literal N, `moa_n`, and repeats, when B0 writes then reloads the manifest, then it contains B1..B_N disjoint complete shards and the three values remain independent. Any bound-field change conflicts. | `python -m pytest tests/pi_benchmark/test_scheduler.py tests/pi_benchmark/test_runner.py -q` |
| A3 | Given an old, arbitrary, forged, wrong-run, wrong-cap, or wrong-digest gate file, when live/preflight is requested, then refusal occurs before credential lookup/reservation/dispatch. | `python -m pytest tests/pi_benchmark/test_owner_gate.py tests/pi_benchmark/test_runner.py -q` |
| A4 | Given concurrent workers/retries/crash recovery, when they reserve/commit/reopen, then ledger spend never exceeds 1.00; unknown post-dispatch usage stays charged; close is replay-valid and immutable. | `python -m pytest tests/pi_benchmark/test_budget_ledger.py tests/pi_benchmark/test_verify_budget_ledger.py -q` |
| A5 | Given identical scenario fixtures, when both arms run through the route adapter, then real ASGI/API middleware+route+dispatcher evidence exists for public-route scenarios and the explicit dispatcher seam exists for MoA; no direct provider call acts as DUT. | `python -m pytest tests/pi_benchmark/test_live_driver.py tests/pi_production/test_chat_pi_asgi.py -q` |
| A6 | Given self-MoA, when `moa_n` temperatures are served by one admitted DeepSeek route, then response/coder/consensus/source evidence is complete; partial or multi-route anomalies degrade. | `python -m pytest tests/pi_benchmark/test_moa.py -q -k self_moa` |
| A7 | Given full ensemble, when fewer than `moa_n` distinct successful admitted routes are served or the method downgrades, then the unit is degraded/blocked and never success; exactly `moa_n` distinct routes may reconcile. | `python -m pytest tests/pi_benchmark/test_moa.py tests/pi_benchmark/test_live_driver.py -q -k 'full_ensemble or route'` |
| A8 | Given any raw endpoint ID/URL/key/private fingerprint in a record or packet, when validation/scan runs, then freeze fails; otherwise redacted pseudonyms preserve served-route cardinality. | `python -m pytest tests/pi_benchmark/test_live_driver.py tests/pi_benchmark/test_artifact_packet.py -q -k 'redact or secret or route'` |
| A9 | Given manifest waves, when completion is projected, then corrupt/missing records stay pending and all declared units—including not-runnable/budget-blocked/degraded—are counted. | `python -m pytest tests/pi_benchmark/test_scheduler.py tests/pi_benchmark/test_artifact_packet.py -q -k 'resume or terminal or missing'` |
| A10 | Given all waves terminal, when the barrier runs, then it refuses until ledger is verified+closed and artifact hashes are stable; a second freeze is byte-identical. | `python -m pytest tests/pi_benchmark/test_artifact_packet.py tests/pi_benchmark/test_verify_budget_ledger.py -q` |
| A11 | Given a frozen packet, when the post-run judge configuration is checked, then Kimi is separate, input is read-only, and any DUT/DeepSeek runner/server/ledger invocation is rejected. | `python -m pytest tests/pi_benchmark/test_judge.py tests/pi_benchmark/test_artifact_judging.py -q` |
| A12 | Given complete Kimi judgments, when report generation runs twice, then scorecard/report numbers derive from packet JSON, degraded ensembles are not successes, invalid pairs are counted, and outputs are reproducible modulo declared timestamp. | `python -m pytest tests/pi_benchmark/test_report.py -q` |
| A13 | Given the full change, then migration and Research Spine contracts remain green. | `python -m pytest tests/pi_migration tests/pi_production/test_scenario_coverage_map.py tests/pi_production/test_w3_research_spine.py tests/test_research_validity_contract.py -q` |
| A14 | Given provider/route/accounting changes, then security score remains above threshold and no unreviewed control drift exists. | `python scripts/security_benchmark.py --fail-on-threshold` |
| A15 | Given behavior/docs changes, then feature docs regenerate cleanly, architecture gate shows no new failures, and whitespace is clean. | `python scripts/feature_docs.py --seed-missing --generate-site --check`; `compass-forge gate after --task <implementation-task> --summary`; `git diff --check` |

Live evidence is additional and cannot be fabricated from these offline commands. T10 must
record the literal G1/G2 evidence, B0 preflight row, each B-wave command/result, final
ledger replay/close, convergence summary, route-redaction scan, and packet digest. T11 must
record the separate session identity, packet digest verification, zero DUT-ledger delta,
per-judgment outputs, and report reproducibility.

## 6. Narrow changed-file scope

Expected implementation changes are limited to:

- `tests/pi_benchmark/` implementation, tests, fixtures, and its README;
- `comparison-Istara-pi/metrics-schema.json` and a new timestamped report bundle only after
  successful post-run judging (never overwrite historical bundles);
- `scripts/pi_benchmark_report.py`;
- the retake-specific conductor instruction and affected living feature/architecture docs
  required by repository policy.

Product code under `backend/app/` is out of scope unless a failing real-boundary test proves
the existing API/dispatcher cannot expose required, already-produced route/usage evidence.
If that occurs, create a separate narrowly-scoped CF task, make telemetry-only/default-off
changes, run the security benchmark, and preserve endpoint isolation from `ComputeRegistry`.
No changes to global agent config, secrets, generated integrations, unrelated reports,
`LLMs/`, or `Model_Finetuning/`.

## 7. Risks and mitigations

| Risk | Mitigation / stop condition |
|---|---|
| Old approvals or artifacts contaminate the retake | Fresh `run_id` plus manifest/gate/artifact digests; old reports are excluded inputs; wrong digest fails closed. |
| USD 1.00 buys less than the declared matrix | B0 computes worst-case reservations; G2 sees the literal workload. At runtime, remaining units become counted `budget_blocked`; never shrink silently or reset the ledger. |
| Multiple workers race past the cap | Existing `flock` + fsync read-modify-append; add run/call correlation and adversarial multi-process tests. |
| One DeepSeek route cannot support a real full ensemble | Record the topology limitation and degraded/blocked units. Do not invent endpoint aliases or use another provider. |
| API coverage is replaced by self-consistent mocks | Require ASGI/HTTP route evidence for public-route scenarios and direct dispatcher evidence only for the no-route MoA seam; fake only provider transport in tests. |
| Raw private route identity or credentials leak | Redact before persistence; scan records, ledger, packet, judgments, and reports; block freeze on match. |
| Estimated usage biases the comparison | Preserve per-call `estimate`/estimator flags; never combine exact and estimated columns; unknown successful calls retain worst-case reservation. |
| Kimi judge accidentally reruns the DUT | Separate CF/BSC lifecycle, read-only artifact packet, no runner/server commands, zero DUT-ledger delta assertion. |
| Report generator overclaims incomplete data | Require barrier+close+packet+jgment digests and fail closed; count invalid/degraded/budget-blocked records. |
| Benchmark evidence bypasses Research Spine governance | Keep artifacts provisional; record source/coder/reconciliation handles; no promotion to reportable research without the existing human Done gates. |

## 8. Rollback and recovery

- **Before live spend:** delete only the new gitignored run directory if the owner chooses
  to abandon it; code rollback is the scoped implementation commit. Do not delete shared
  model/training artifacts or historical reports.
- **After a crash:** do not rewrite manifest or ledger. Reopen and replay both, validate
  existing atomic records, retain uncertain reservations, and resume only incomplete units
  from their assigned wave.
- **After a gate/topology/budget block:** seal the ledger, freeze the honest partial packet,
  mark the run blocked/partial, and stop. A changed N, cap, provider/model, route set,
  repeats, or inputs requires a new `run_id` and new owner gates; it is never an in-place
  manifest edit.
- **After artifact freeze:** packet and report inputs are immutable. Corrections create a
  successor packet/report directory with a new digest and provenance link.
- **Kimi judging failure:** preserve the frozen DUT packet and closed ledger, discard only
  the incomplete judging-session outputs, and resume/retry the separate judging task. Never
  rerun B waves merely because judging failed.
- **Product regression:** turn off/undo only any separately authorized benchmark telemetry
  seam; the permanent legacy executor and default engine remain untouched.

## 9. Handoff criteria

This plan is ready for consensus judging because its repository-grounding audit is complete
and the focused offline baseline is recorded honestly (170 passed, two fail on the
under-reservation defect assigned to T3). Plan selection must not reinterpret that baseline
as a live-readiness pass. The winning implementer should preserve the ordering:
contracts -> manifest/gates/ledger -> real boundary -> MoA/redaction -> convergence packet
-> remove in-run judge -> report gate -> owner-gated execution -> separate Kimi session.
No later stage may collapse T10/T11 into implementation or treat current tracked gate/report
files as fresh authorization/evidence.
