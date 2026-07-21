# Build Stream — Full Pi Replacement of Istara's Agentic Loop and Model Management

<!-- STATUS BLOCK -->
```yaml
item: pi-full-replacement
branch: Review_pi_test
cf: { spec: CF-SPEC-8, tasks: [pi-full-20260720-w0-IMPL, pi-full-20260720-w0-REVIEW] }
phase: "W4 — A2A handlers migration"
stage: S3-review
status: in-progress
blocked_on: none
last: { agent: claude-fable-5, at: 2026-07-21T11:09:13Z, ledger: L-34 }
next_action: "W4 review PASSED (L-34): all 3 A2A handler sites verified against master plan §8 W4 (flag-gated dispatcher paths, legacy branch preserved, ratchet held at 70); 178 tests green; zero Blocker/Major findings, 3 info observations in the W4 register. Hand back to the conductor for W4 stage-exit acceptance."
```
<!-- /STATUS BLOCK -->

## Plan overview (roadmap)

The owner-approved governing plan is
[`docs/build-stream/plans/2026-07-20-pi-full-replacement-master-plan.md`](plans/2026-07-20-pi-full-replacement-master-plan.md).
Its mission, target architecture, exhaustive call-site inventory, wave contracts, benchmark
methodology, documentation program, exclusions, verification ladders, and owner gates are
incorporated here by reference. This lifecycle file is the durable execution, review,
remediation, and acceptance record for that single initiative.

Outcome: every product model invocation outside the permanent Petals/donated-compute
allowlist routes through `AgenticDispatcher`, both Pi and legacy engines remain real and
benchmarkable, Pi failures fail closed, the product legacy-call ratchet reaches zero, and
the required evidence, living documentation, benchmark reports, and academic article ship.

Non-goals: deleting the legacy engine; changing Petals/donated compute; migrating Whisper
STT or Google Stitch; touching `LLMs/` or `Model_Finetuning/`; unapproved live model loads,
external traffic, or API/judge spend.

| Phase | Goal | Acceptance / verify | Status |
|---|---|---|---|
| W0 | Harden runtime and arm evidence integrity ratchet | W0 tests + existing Pi ladder + clean post-gate | in-progress |
| W1 | Add dispatcher, model manager, complete engine APIs, and usage ledger | W1 tests + allowlist remains 87 + clean post-gate | planned |
| W2 | Migrate nine interactive surfaces | allowlist 78 + B1 T0/T1 + wave ladder | in-progress |
| W3 | Migrate eight research-spine and steering sites | allowlist 70 + wave ladder | in-progress |
| W4 | Migrate three A2A handlers | allowlist 67 + wave ladder | planned |
| W5 | Migrate 28 skills, reports, and interview services | allowlist 39 + B2 implementation artifacts | planned |
| W6 | Migrate 14 autoresearch runner sites | allowlist 25 + wave ladder | planned |
| W7 | Migrate eight validation, consensus, and dual-coder sites | allowlist 17 + wave ladder | planned |
| W8 | Add embeddings gateway and model-management UX parity | zero product sites + wave ladder | planned |
| W9 | Finalize ratchet, docs, security and full verification | permanent allowlist only + full ladder x3 + clean gate | planned |
| B1 | Contract benchmark after W2 | T0/T1 canonical and W2 scenarios, both engines | planned |
| B2 | Breadth benchmark after W5 | implementation complete; live T2 execution requires explicit permission | planned |
| B3 | Depth benchmark after W9 | T2/T3 dry-run estimate and explicit owner gates before model load/spend | planned |
| B4 | Generate reports and article results | generated report set, scorecard, article, rollout decision gate | planned |

Top risks: missed legacy call sites; donor-plane coupling; non-equivalent legacy behavior;
worker concurrency/resource faults; invalid structured-output translation; vector-space
drift; benchmark bias or unapproved spend; historical claims diverging from executable
evidence. Rollback remains per-project engine selection back to the preserved legacy path.

Doc impact: the agentic-engine feature documentation, generated feature site/manifests,
`Tech.md`, persona/agent guidance, `TESTING.md`, comparison reports/README, and the academic
article specified by the master plan.

## Decision log

DEC-1 | 2026-07-20 | S0 | owner
Context: The independent CF-SPEC-7 review found incomplete product coverage and runtime
hardening gaps, and the master plan defines the full replacement and benchmark contract.
Decision: Execute the master plan as the winning plan, starting at implementation with
Build Stream Conductor planning disabled and no architect stages.
Why: The owner's instruction explicitly approves this governing plan and forbids a new
architecture/planning cycle; independent implementation/review/fix loops retain separation
of duties.

DEC-2 | 2026-07-20 | S1 | gpt-5.6-sol
Context: Repository safety rules prohibit live servers, chat-completion probes, and model
loading without explicit permission; the plan separately gates T3 spend and judge policy.
Decision: Complete all static, deterministic, and implementation work autonomously, but
stop before any live T2/T3 model-loading or paid benchmark action until its explicit owner
gate is satisfied.
Why: This preserves the approved product scope while respecting the narrower operational
authorization boundary and prevents accidental private-endpoint use or spend.

## Ledger

### L-1 | 2026-07-20T13:50:34-03:00 | S1-plan | gpt-5.6-sol | planner | — (roadmap)
Did: Oriented through Compass Forge, created and clarified CF-SPEC-8, planned it without
force, and projected the approved master plan into this lifecycle roadmap.
Result: CF-SPEC-8 is planned with a passing quality rubric; implementation may begin at W0
without architect stages.
Verified: `compass-forge constitution check` = ok; `compass-forge spec plan CF-SPEC-8` = planned, force unused.
Next: Start the no-planning W0 conductor implementation/review/remediation pipeline.

### L-2 | 2026-07-20T13:54:20-03:00 | S2-execute | gpt-5.6-sol | executor | W0
Did: Imported the no-planning W0 implementation and independent-review task graph linked
to CF-SPEC-8 and captured its pre-change architecture gate.
Result: `pi-full-20260720-w0-IMPL` is ready and blocks
`pi-full-20260720-w0-REVIEW`; the baseline contains only 28 inherited large-file failures,
with zero new/actionable failures, drift, security findings, or cycles.
Verified: `compass-forge gate before --task pi-full-20260720-w0-IMPL --summary` = 0 new failures, 0 actionable failures, 0 drift, 0 security.
Next: Dispatch the implementer through the W0 conductor cast.

### L-3 | 2026-07-20T17:02:17Z | S2-execute | gpt-5.6-terra | executor | W0 <!-- bsc-ledger:pi-full-20260720-w0-IMPL -->
Did: Hardened the shared Pi enforcement seam in `supervisor.py` and `engine.py`; changed
the coverage-map test to derive scenario IDs from the canonical lab catalog.
Result: H-3's same-key overlap is rejected as `session_busy` and stale cross-run frames are
discarded; H-9 telemetry records `aborted`; H-10 rejects out-of-catalog worker tool calls;
H-14 no longer maintains a static scenario-id count. W0 remains incomplete.
Verified: `python -m py_compile backend/app/core/pi_runtime/supervisor.py backend/app/core/pi_runtime/engine.py tests/pi_production/test_scenario_coverage_map.py` = pass;
`python -m pytest tests/pi_production/test_scenario_coverage_map.py tests/pi_production/test_worker_tool_loop.py -q` = 3 passed.
Next: Continue the remaining W0 hardening and ratchet implementation; stage exit is blocked on the full §6 contract.

### L-4 | 2026-07-20T17:11:55Z | S3-review | gpt-5.6-sol | reviewer | W0 <!-- bsc-ledger:pi-full-20260720-w0-REVIEW -->
Did: Independently reviewed commit `effe9496`, the W0 master-plan and conductor contracts,
runtime/protocol seams, regression inventory, CF evidence, docs, gate, and commit discipline;
created `FIX-pi-full-20260720-w0-REVIEW-r1` for the coupled remediation.
Result: Fail; opened F-1 through F-4. The partial H-3/H-9/H-10/H-14 changes retain green
focused regressions, but W0's inventory ratchet, most H items, ASGI proof, history correction,
living docs, completion decision, and full exit evidence are absent.
Verified: required-file audit = failed (5 missing plus no `PI_REQUIRE_NODE` enforcement);
focused Pi/donor pytest = 4 passed; candidate pytest = 13 passed; `npm --prefix pi-runtime test`
= 4 passed while literal `node --test pi-runtime/test` = `MODULE_NOT_FOUND`; feature docs =
86 passed; security benchmark = 28/28; post-gate = 0 new/actionable/drift/security/cycles;
commit = required author/W0 tag/4 files/no co-author; no orphan Pi worker.
Next: Stage exit: fail verdict and coupled remediation task recorded for delta re-review.

### L-5 | 2026-07-20T18:03:00Z | S4-remediate | gpt-5.6-terra | remediator | W0 <!-- bsc-ledger:FIX-pi-full-20260720-w0-REVIEW-r1 -->
Did: Completed the W0 inventory/ratchet, runtime hardening, real-ASGI, fail-closed, endpoint-secret, steering, worker-protocol, and authority-audit remediation set. Closed the Python-to-Node transport seam by assigning scoped outbound `seq` values, accepting bounded 8 MiB worker output, chunking oversized outbound payloads, and reclaiming EOF worker children before bounded restart.
Result: F-1–F-4 are fixed by this task: the 87-site ratchet is registered in the e2e ladder; H-1–H-14 regressions and H-13’s append-only correction are present; `PI_REQUIRE_NODE=1` fails absent-Node collection; package test entrypoint is `npm --prefix pi-runtime test`. The prior real-worker handshake timeout was corrected without loading a live model or touching donated compute.
Verified: `python -m pytest tests/pi_migration tests/pi_production -q` = passed; `PI_REQUIRE_NODE=1 python -m pytest tests/pi_production/test_chat_pi_asgi.py tests/pi_production/test_scenario_coverage_map.py -q` = 4 passed; `python -m pytest tests/pi_production/test_frame_limits.py tests/pi_production/test_worker_tool_loop.py tests/pi_production/test_chat_pi_asgi.py tests/pi_migration -q` = 9 passed; `npm --prefix pi-runtime test` = 17 passed; `python -m pytest tests/test_pi_replacement_candidate.py -q` = 13 passed; `python scripts/pi_migration_inventory.py --json | python -m json.tool > /dev/null` = passed; `python scripts/feature_docs.py --seed-missing --generate-site --check` = 86 features passed; `python scripts/security_benchmark.py --fail-on-threshold` = 28/28, 100%; `compass-forge gate after --task FIX-pi-full-20260720-w0-REVIEW-r1 --summary` = 0 new/actionable failures, 0 drift (inherited large-file debt only).
Next: Stage exit: delta review the changed W0 surface and verify F-1–F-4 are closed. 

### L-6 | 2026-07-20T18:10:28Z | S3-review | gpt-5.6-sol | reviewer | W0
<!-- bsc-ledger:REREV-pi-full-20260720-w0-REVIEW-r1 -->
Did: Delta re-reviewed only F-1–F-4 against `FIX-pi-full-20260720-w0-REVIEW-r1`,
including the fix-induced supervisor sequence/frame/capacity seams. Inspected commit
`0ee278d9`, reran focused ratchet/runtime/ASGI/Node/candidate/docs/security proofs, and
created coupled fixer task `FIX-REREV-pi-full-20260720-w0-REVIEW-r1` for residual F-2.
Result: Fail. F-1, F-3, and F-4 are closed, but F-2 remains Blocker: reader death does
not retire/restart a live poisoned child; Python does not pass `max_turns` and has no
whole-run wall-clock/cost ceiling; the configured two-worker pool and 20-turn regression
are absent (session 9 fails at the single worker's cap); and the isolated H-10
compromised-worker suite fails 2 tests because no Python rejection/audit row is reached.
Verified: focused ratchet/frame/steering/ASGI/coverage set = 12 passed; Node package =
17 passed; candidate = 13 passed; feature docs = 86 passed; security benchmark = 28/28;
isolated `tests/pi_production/test_tool_authority.py` = 2 failed, 2 passed; adversarial
capacity probe = 8 opens then `session_capacity_exceeded`; reader-death probe = same live,
ready PID after `ensure_started`. CF command evidence, fail verdict, and self-report recorded.
Next: Remediate `FIX-REREV-pi-full-20260720-w0-REVIEW-r1`; W0 cannot advance until a
conductor-created delta re-review passes.

### L-7 | 2026-07-20T18:25:00Z | S4-remediate | gpt-5.6-terra | remediator | W0 <!-- bsc-ledger:FIX-REREV-pi-full-20260720-w0-REVIEW-r1 -->
Did: Closed F-2 in `supervisor.py`, new `pool.py`, the Node session/provider seams, protocol, and focused Pi regressions. EOF now clears readiness before restart; Python passes explicit turn/wall-clock/cost limits; the default service owns a lazy two-worker, ten-session-per-worker pool; and the faux-only compromised-worker fixture reaches Python rejection/audit.
Result: F-2 fixed by `FIX-REREV-pi-full-20260720-w0-REVIEW-r1`: 20 concurrent sessions distribute 10/10 across two workers, H-10 records the rejected call and telemetry audit, and over-budget wall-clock/cost outcomes are terminal failures. No live model was loaded and no donated compute path changed.
Verified: `python -m pytest tests/pi_production/test_tool_authority.py tests/pi_production/test_runtime_hardening.py tests/pi_production/test_frame_limits.py -q` = 8 passed; `npm --prefix pi-runtime test` = 17 passed; `python scripts/feature_docs.py --seed-missing --generate-site --check` = 86 passed; `python scripts/security_benchmark.py --fail-on-threshold` = 28/28, 100%; `compass-forge gate after --task FIX-REREV-pi-full-20260720-w0-REVIEW-r1 --summary` = 0 new/actionable failures, 0 drift/security/cycles (inherited gate debt only).
Next: Stage exit: conduct the bounded delta re-review of F-2 and its changed immediate seams.

### L-8 | 2026-07-20T18:25:34Z | S3-review | gpt-5.6-sol | reviewer | W0
<!-- bsc-ledger:REREV-pi-full-20260720-w0-REVIEW-r2 -->
Did: Delta re-reviewed only residual F-2 against `FIX-REREV-pi-full-20260720-w0-REVIEW-r1` and commits `e100aa5e..b64c572a`. Inspected the changed supervisor, pool, session/provider, protocol, harness, and focused tests. The new pool changes H-12 architecture/acceptance, so the review checked the governing master-plan requirements for session-key routing and 20 concurrent turns rather than broadening to unrelated W0 surfaces.
Result: Fail; reopened F-2 and created `FIX-REREV-pi-full-20260720-w0-REVIEW-r2`. H-2 now clears readiness and reclaims/restarts a poisoned child with existing restart backoff, and H-10 now reaches the Python rejection/audit seam. H-6/H-12 remain Blocker: the pool regression opens 20 sessions but runs zero turns; pool selection is least-owned rather than the required configured session-key hash contract; and wall-clock/cost terminal paths have no behavioral regression even though L-7 claims those outcomes were verified.
Verified: `python -m pytest tests/pi_production/test_tool_authority.py tests/pi_production/test_runtime_hardening.py tests/pi_production/test_frame_limits.py -q` = 8 passed; `npm --prefix pi-runtime test` = 17 passed; focused acceptance audit over `test_runtime_hardening.py`, `pool.py`, and `hardening.test.mjs` = failed with `h12_20_turns=false`, `h12_session_hash=false`, `h6_wall_clock_test=false`, and `h6_cost_test=false`.
Next: Remediate `FIX-REREV-pi-full-20260720-w0-REVIEW-r2`; W0 remains in S4 until a conductor-created delta re-review passes.

### L-9 | 2026-07-20T18:48:14Z | S4-remediate | claude-opus-4-8 | remediator | W0 <!-- bsc-ledger:FIX-REREV-pi-full-20260720-w0-REVIEW-r2 -->
Did: Closed the residual F-2 H-6/H-12 acceptance gaps. Rewired `PiRuntimePool` from
least-owned selection to the required deterministic `pi_worker_pool_size`/`session_key`-hash
routing (`blake2b`, process-stable) with config-driven pool size (`pool.py`). Added a
test-only faux `forcedCostUsd` seam (`provider.mjs`) honored by the worker cost ceiling
(`session.mjs`) so the always-zero-cost faux provider can drive a real cost terminal.
Replaced the constructor-only pool/budget assertions with behavioral proofs: 20 concurrent
turns across the two-worker pool with per-key routing checks, deterministic/config-sized
routing unit tests, and Python + Node wall-clock/cost terminal regressions
(`test_runtime_hardening.py`, `hardening.test.mjs`).
Result: F-2 fixed by `FIX-REREV-pi-full-20260720-w0-REVIEW-r2`. H-12 now runs 20 concurrent
turns (10/10 across two bounded workers) under the deterministic session-key-hash contract,
and H-6 `wall_clock_budget_exceeded`/`cost_budget_exceeded` terminals have real behavioral
regressions on both the Node worker and through the Python supervisor. No live model was
loaded and no donated-compute path changed.
Verified: `npm --prefix pi-runtime test` = 20 passed (adds wall-clock + cost terminals);
`PI_REQUIRE_NODE=1 python -m pytest tests/pi_production/test_tool_authority.py tests/pi_production/test_runtime_hardening.py tests/pi_production/test_frame_limits.py -q` = 12 passed;
`python -m pytest tests/pi_production tests/pi_migration -q` = 64 passed;
`python -m pytest tests/test_pi_replacement_candidate.py -q` = 13 passed;
`python scripts/security_benchmark.py --fail-on-threshold` = pass;
`python scripts/feature_docs.py --seed-missing --generate-site --check` = 86 passed;
`compass-forge gate after --task FIX-REREV-pi-full-20260720-w0-REVIEW-r2 --summary` = 0
new/actionable failures, 0 drift/cycles, 0 new security (inherited large-file + `config.py:90`
secret_flow debt only).
Next: Stage exit: conduct the bounded delta re-review of F-2's pool routing and wall-clock/cost proofs.

### L-10 | 2026-07-20T18:56:22Z | S3-review | gpt-5.6-sol | reviewer | W0
<!-- bsc-ledger:REREV-pi-full-20260720-w0-REVIEW-r3 -->
Did: Delta re-reviewed only F-2 against `FIX-REREV-pi-full-20260720-w0-REVIEW-r2` and commit `05958204`. Verified the configured deterministic session-key pool routing, the real 20-concurrent-turn proof, and the Node/Python wall-clock and cost terminal regressions. Inspection broadened only through the cost regression's immediate production provider seam because the fix introduced `forcedCostUsd` as a test-only substitute for real usage cost.
Result: Fail; reopened F-2 and created `FIX-REREV-pi-full-20260720-w0-REVIEW-r3`. Pool routing, 20 concurrent turns, and wall-clock termination pass. The cost terminal is proven only with `faux_cost_usd`: `buildRealProvider` still hardcodes all real-endpoint model rates to zero, while Pi AI derives `usage.cost.total` from those rates. A non-network production-binding probe with two million tokens therefore calculated `$0`, so `max_cost_usd` cannot fail closed for real endpoints and the H-6 per-run production cost ceiling remains incomplete.
Verified: `npm --prefix pi-runtime test` = 20 passed; `PI_REQUIRE_NODE=1 python -m pytest tests/pi_production/test_runtime_hardening.py -q` = 7 passed; non-network `buildRealProvider` + `calculateCost` probe = `model_cost` all zero and `calculated_cost_usd: 0` for 2,000,000 tokens (acceptance failure reproduced).
Next: Remediate `FIX-REREV-pi-full-20260720-w0-REVIEW-r3`; the conductor creates the next bounded delta re-review after the fixer and all sibling findings finish.

### L-11 | 2026-07-20T19:23:47Z | S4-remediate | claude-opus-4-8 | remediator | W0 <!-- bsc-ledger:FIX-REREV-pi-full-20260720-w0-REVIEW-r3 -->
Did: Closed F-2's residual production-cost gap. Threaded trustworthy per-endpoint
pricing end to end: `PiApiEndpoint`/`ResolvedPiEndpoint` gain `cost_*_per_mtok`
fields (`config.py`, `endpoints.py`), the default DeepSeek endpoint is seeded with
published list pricing, and `_bind_payload` forwards `endpoint.pricing` on real
binds (`engine.py`). `buildRealProvider` now maps that pricing onto the pi-ai
model `cost` rates instead of hardcoded zero and flags `isReal`/`pricingConfigured`
(`provider.mjs`, new `mapProviderPricing`). `session.mjs` now enforces the ceiling
cumulatively across every assistant turn in a run and fails a budgeted real run
closed with `cost_budget_unpriced` when a real binding spent tokens but carries no
pricing. Added non-faux behavioral regressions (real openai_compat loopback with
token usage) on both the Node worker and through the Python engine, updated
`PROTOCOL.md`, and priced the existing structured-output real-endpoint test.
Result: F-2 fixed by `FIX-REREV-pi-full-20260720-w0-REVIEW-r3`. A real 2M-token turn
now prices to nonzero cost and `max_cost_usd` fails closed for real endpoints; a
zero-priced real binding would fail every new over-budget assertion. No live model
was loaded and no donated-compute path changed.
Verified: `npm --prefix pi-runtime test` = 24 passed (was 20; adds real over-budget
`cost_budget_exceeded`, priced within-budget cost report, `cost_budget_unpriced`,
and a cumulative multi-turn tool-loop ceiling — all non-faux loopback HTTP);
`PI_REQUIRE_NODE=1 python -m pytest tests/pi_production/test_runtime_hardening.py -q`
= 10 passed (was 7; adds `_bind_payload` pricing forwarding, default-endpoint-is-priced,
and a full-stack real over-budget turn surfacing `cost_budget_exceeded` through the
engine); `PI_REQUIRE_NODE=1 python -m pytest tests/pi_production tests/pi_migration -q`
= 67 passed (was 64); `python -m pytest tests/test_pi_replacement_candidate.py -q`
= 13 passed; `python scripts/security_benchmark.py --fail-on-threshold` = pass;
`python scripts/feature_docs.py --seed-missing --generate-site --check` = 86 passed;
`compass-forge gate after --task FIX-REREV-pi-full-20260720-w0-REVIEW-r3 --summary`
= security dimension unchanged at 1, 0 drift/cycles. The one reported new_failure is
the pre-existing `_read_pi_endpoint_secret` `secret_flow` (the config.py:90 inherited
debt from L-9) re-fingerprinted because 10 non-secret pricing lines shifted that
untouched function down; a diagnostic confirmed removing the shift returns
new_failures=0 with security still 1 (no secret sink introduced).
Next: Stage exit: conduct the bounded delta re-review of F-2's production cost
pricing, the cumulative per-run ceiling, and the unpriced fail-closed path.

### L-12 | 2026-07-20T19:30:48Z | S3-review | gpt-5.6-sol | reviewer | W0
<!-- bsc-ledger:REREV-pi-full-20260720-w0-REVIEW-r4 -->
Did: Delta re-reviewed only F-2 against
`FIX-REREV-pi-full-20260720-w0-REVIEW-r3` and commit `30a0f765`. Verified the
new real-provider pricing map, cumulative multi-turn settlement, fully-unpriced
terminal, backend bind propagation, and the source fix's CF evidence. Inspection
broadened only to the immediate Pi AI `calculateCost` seam and the official
DeepSeek pricing contract because the fix made production acceptance depend on
per-category rates and claimed the built-in values were the published price.
Result: Fail; reopened F-2 and created
`FIX-REREV-pi-full-20260720-w0-REVIEW-r4`. `buildRealProvider` marks pricing as
configured when any single rate is positive, but Pi AI prices input, output,
cache-read, and cache-write independently. The adversarial real-binding probe
therefore accepted input/output pricing while calculating 1,000,000 cache-read
tokens at `$0`. The built-in endpoint also targets `deepseek-v4-pro` while
shipping `0.27` input, `1.10` output, and `0` cache-read USD/Mtok; DeepSeek's
current official v4-pro table lists `0.435` cache-miss input, `0.87` output, and
`0.003625` cache-hit input. Input/cache-heavy runs can consequently be
undercounted instead of failing closed. The non-faux over-budget, cumulative,
and wholly-unpriced regressions otherwise pass.
Verified: `npm --prefix pi-runtime test` = 24 passed;
`PI_REQUIRE_NODE=1 python -m pytest` over the three focused pricing/default/full-stack
tests = 3 passed; `buildRealProvider` + Pi AI `calculateCost` partial-pricing
probe = `pricingConfigured:true`, `cacheRead:1000000`, `calculatedCostUsd:0`
(acceptance failure reproduced); official DeepSeek Models & Pricing checked on
2026-07-20 for the actual `deepseek-v4-pro` model.
Next: Remediate `FIX-REREV-pi-full-20260720-w0-REVIEW-r4`; the conductor creates
one bounded delta re-review after the fixer and all sibling findings finish.

### L-13 | 2026-07-20T19:46:29Z | S4-remediate | claude-opus-4-8 | remediator | W0 <!-- bsc-ledger:FIX-REREV-pi-full-20260720-w0-REVIEW-r4 -->
Did: Closed F-2's per-category pricing fail-open and the wrong built-in default rates.
Replaced `buildRealProvider`'s boolean-OR `pricingConfigured` with the full per-category
rate map exposed as `binding.pricing` (`provider.mjs`); `session.mjs` now tracks per-category
usage (input/output/cacheRead/cacheWrite) and fails a budgeted real run closed with
`cost_budget_unpriced` when it spent tokens in ANY $0-rated category (new `_hasUnpricedSpend`).
Re-sourced the default `deepseek-v4-pro` rates to the 2026-07-20 published table (0.435
cache-miss input, 0.87 output, 0.003625 cache-hit input) in `config.py` and wired the
cache-read rate into the default endpoint (`endpoints.py`). Added non-faux regressions for
cached/partially-priced usage (Node loopback + full-stack Python engine), pinned the
default-endpoint pricing assertion, and updated `PROTOCOL.md`. Files: `pi-runtime/src/provider.mjs`,
`pi-runtime/src/session.mjs`, `backend/app/config.py`, `backend/app/core/pi_runtime/endpoints.py`,
`pi-runtime/PROTOCOL.md`, `pi-runtime/test/hardening.test.mjs`, `tests/pi_production/test_runtime_hardening.py`.
Result: F-2 fixed by `FIX-REREV-pi-full-20260720-w0-REVIEW-r4`. A real turn that spends
1,000,000 cache-read tokens on an endpoint priced only for input/output now fails closed
(`cost_budget_unpriced`) instead of pricing $0; a fully-priced cached turn prices its cache
reads nonzero and is counted; the built-in default endpoint is priced for every category it
can spend. No live model was loaded and no donated-compute path changed.
Verified: `npm --prefix pi-runtime test` = 26 passed (was 24; adds cache-read unpriced
fail-closed + priced-cache-read completion); `PI_REQUIRE_NODE=1 python -m pytest
tests/pi_production/test_runtime_hardening.py -q` = 11 passed (was 10; adds full-stack
cache-read `cost_budget_unpriced` and default-endpoint rates pinned to the sourced v4-pro
table incl cache-read); `PI_REQUIRE_NODE=1 python -m pytest tests/pi_production tests/pi_migration -q`
= 68 passed (was 67); `python -m pytest tests/test_pi_replacement_candidate.py -q` = 13 passed;
`python scripts/security_benchmark.py --fail-on-threshold` = pass; `python scripts/feature_docs.py
--seed-missing --generate-site --check` = 86 passed; `compass-forge gate after --task
FIX-REREV-pi-full-20260720-w0-REVIEW-r4 --summary` = new_failures=1, security=1 unchanged, 0
drift/cycles. The one new_failure is the inherited config.py `secret_flow` re-fingerprint
(L-9/L-11): stashing my config/endpoints edits still reports new_failures=1, so it is present
at HEAD and not introduced by this stage.
Next: Stage exit: conductor creates the bounded delta re-review of F-2's per-category unpriced
fail-closed path and the corrected default rates.

### L-14 | 2026-07-20T19:55:49Z | S3-review | gpt-5.6-sol | reviewer | W0
<!-- bsc-ledger:REREV-pi-full-20260720-w0-REVIEW-r5 -->
Did: Delta re-reviewed only F-2 against
`FIX-REREV-pi-full-20260720-w0-REVIEW-r4` and commit `f3ccbf26`. Inspected the
changed provider/session pricing contract, default-endpoint rate wiring, protocol, new
non-faux regressions, and the immediate installed pi-ai cache-usage/cost calculation seam.
Verified the current official `deepseek-v4-pro` price table because the fix's acceptance
depends on those model-specific defaults. No live provider or model request was made.
Result: Pass with no new findings and zero corrections. The session now checks actual
input/output/cache-read/cache-write spend against the full per-category binding rates and
fails a budgeted real run closed as `cost_budget_unpriced` when any spent category is
zero-rated. The built-in endpoint matches the official v4-pro cache-miss input, output,
and cache-hit input rates, and the new non-faux regressions prove both rejection of a
partially-priced cached turn and nonzero settlement of a fully-priced cached turn.
Verified: `node --test --test-name-pattern='real run that spends cache-read|real run that prices its cache-read' pi-runtime/test/hardening.test.mjs` = 2 passed;
`PI_REQUIRE_NODE=1 python -m pytest tests/pi_production/test_runtime_hardening.py::test_default_endpoint_is_priced_so_its_cost_ceiling_can_fail_closed tests/pi_production/test_runtime_hardening.py::test_real_cache_read_unpriced_turn_fails_closed_through_engine -q` = 2 passed;
`git show --check f3ccbf26` = pass; official DeepSeek Models & Pricing verified on
2026-07-20 as `$0.435` cache-miss input, `$0.87` output, and `$0.003625` cache-hit input
per 1M tokens.
Next: Stage exit: pass verdict recorded; conductor advances the pipeline after the required
CF evidence, self-report, reviewer handoff, and task finish.

### L-15 | 2026-07-20T20:13:44Z | S2-execute | gpt-5.6-terra | executor | W1 <!-- bsc-ledger:pi-full-20260720-w1-IMPL -->
Did: Added the W1 `app.core.agentic` dispatcher contract, content-free one-row agentic
usage telemetry, an isolated `PiModelManager` catalog, and `PiExecutionService`
completion/ReAct/structured seams with Python JSON-Schema revalidation and one bounded
repair attempt. Added focused W1 regression coverage. No product call site or
`legacy_allowlist.yaml` entry changed, retaining the armed 87-site inventory.
Result: Pi selections use the existing isolated runtime/service; absent legacy integration
fails typed rather than silently falling back. The catalog has no ComputeRegistry dependency,
and insufficient distinct endpoints fails closed. Structured results are never returned as
objects until JSON parsing and schema validation pass.
Verified: `python -m pytest tests/pi_production/test_w1_agentic_contract.py tests/pi_migration/test_count_to_zero.py -q` = 6 passed; `npm --prefix pi-runtime test` = 26 passed; `python scripts/feature_docs.py --seed-missing --generate-site --check` = 86 features passed; `python scripts/security_benchmark.py --fail-on-threshold` = 28/28 pass; `compass-forge gate after --task pi-full-20260720-w1-IMPL --summary` = 0 new failures, 0 drift (inherited gate findings remain).
Next: Independent W1 review; verify the generic seam signatures, fail-closed behavior,
telemetry-safe identity fields, and the no-migration 87-site ratchet.

### L-16 | 2026-07-20T20:22:38Z | S3-review | gpt-5.6-sol | reviewer | W1 <!-- bsc-ledger:pi-full-20260720-w1-REVIEW -->
Did: Independently reviewed W1 commits `98a6b16e` and `16693c58` plus their recipe,
generated-manifest, lifecycle, spec, master-plan, protocol, telemetry, endpoint-isolation,
ratchet, tests, gate, and commit-discipline seams. No implementation code was changed.
Result: Fail; opened F-W1-1 through F-W1-4 and created four barriered fixer tasks. The
five-file commit ceiling, 87-site ratchet, same-model donor isolation, security benchmark,
and existing faux/loopback runtime suite pass, but the W1 production contract is incomplete.
Verified: `pytest -q tests/pi_production/test_w1_agentic_contract.py tests/pi_migration/test_count_to_zero.py tests/pi_production/test_same_model_donor_isolation.py` = 7 passed; `npm --prefix pi-runtime test` = 26 passed; `python scripts/security_benchmark.py --fail-on-threshold` = 28/28; adversarial static/in-process probe = reproduced missing dispatcher verbs, unbound legacy engine, ignored model capabilities, error-shaped structured failure, exact legacy usage mislabeled estimated, protocol v1, and absent worker structured fields; W1 commits = at most 5 files each. No server, external request, or model load was started.
Next: Stage exit: fail verdict recorded; remediate all four finding tasks, then conductor
creates one bounded delta re-review of the changed surfaces.

### L-17 | 2026-07-20T20:51:44Z | S4-remediate | kimi-code/k3 | remediator | W1 <!-- bsc-ledger:FIX-pi-full-20260720-w1-REVIEW-r1-ledger -->
Did: Closed F-W1-3. Added the durable `agentic_usage_rows` ledger table
(`backend/app/models/agentic_usage.py`, migration `023_agentic_usage_ledger`, registered in
`init_db`); rewrote `backend/app/core/agentic/usage_ledger.py` so every dispatch persists one
queryable row — Pi exact from pi-ai, provider-reported legacy exact, only absent legacy usage
estimated with `count_tokens` and flagged `estimate=1`, pre-dispatch failures zeroed exact
rows with `error_type`; the trace span now carries a short identity-only `route_id`
(`agentic:<engine>:<endpoint|node|unresolved>`, <=120 chars) instead of the packed JSON
ledger; integrated exception-path rows, `task_id`/`spine_phase`, and estimation request text
into all six verbs of the concurrent F-W1-1 dispatcher rewrite in
`backend/app/core/agentic/dispatcher.py`; added
`tests/pi_production/test_w1_usage_ledger.py` (7 persistence-level exact-vs-estimated and
exception-path tests). Commits `a9006e32` (persistence) and `c5474069` (contract).
Result: F-W1-3 open -> fixed; CF task FIX-pi-full-20260720-w1-REVIEW-r1-ledger. No product
call sites changed (W1 migrates zero sites; the 87-site ratchet is untouched).
Verified: `pytest -q tests/pi_production/test_w1_usage_ledger.py` = 7 passed; W1 ladder seams
(w1_agentic_contract, seams_fail_closed, runtime_hardening, count_to_zero,
same_model_donor_isolation) = 34 passed before the sibling fixers' concurrent edits, and
runtime_hardening + same_model_donor_isolation re-verified 12/12 green after; `alembic
upgrade head` = 022 -> 023 -> 024 applied (24 columns, 7 indexes); ruff clean on new files
with zero new violations in shared files; `compass-forge gate after` = no new issues from
F-W1-3 files (the one new secret_flow hit is in `backend/app/config.py`, the concurrent
F-W1-1 fixer's uncommitted edit). Later combined-run failures all reproduce only inside
sibling fixers' in-progress files, never in F-W1-3 scope.
Next: sibling fixers complete F-W1-1/F-W1-2/F-W1-4, then the conductor's bounded delta
re-review; that review must confirm no later `dispatcher.py` overwrite dropped the
exception-path usage-row recording.

### L-18 | 2026-07-20T21:08:57Z | S4-remediate | claude-opus-4-8 | remediator | W1 <!-- bsc-ledger:FIX-pi-full-20260720-w1-REVIEW-r1-docs-tests -->
Did: Closed F-W1-4. Made the W1 living feature docs code-accurate for all five behaviors
and replaced the self-consistent W1 smoke coverage with contract-complete tests. Docs:
`docs/features/content/chat/model-controls/architecture.md` (+ regenerated
`site/features/chat/model-controls/architecture.html` and `site/manifest.json`) now
describe the real legacy seam (`legacy.py` driving `ollama.chat`/`ollama.embed_batch`, not
the earlier inaccurate `chat_stream`/Anthropic-forced-tool claims), the durable
`agentic_usage_rows` ledger (`AgenticUsageRow`, migration `023`) with exact-vs-estimate and
the identity-only trace span, the forced `emit_structured_output` contract with typed
`structured_output_missing`/`_invalid` fail-closed, and the versioned `PROTOCOL_VERSION=2`
handshake with `protocol_version_mismatch` rejection; the `settings/llm-servers` and
`compute/pool` pages (committed at `df0c7579`) already cover the isolated Pi catalog
sources/capabilities and bidirectional donor isolation. Tests:
`tests/pi_production/test_w1_agentic_contract.py` proves all five verbs routing to both
real engine seams, precedence (override>header>project>default incl. the persisted project
`agentic_engine` column), unchanged `TurnParams` forwarding, catalog sources/capabilities,
typed structured failure, one-row ledger persistence incl. the exception path, protocol
mismatch rejection, the unchanged 87-site ratchet, and same-model donor isolation; the
shared `tests/pi_production/harness.py` `faux_service` was wired to the new
`PiModelManager` engine seam. All verification is faux/loopback/static — no live model
activity or external traffic.
Result: F-W1-4 open -> fixed; CF task FIX-pi-full-20260720-w1-REVIEW-r1-docs-tests. No
product call site or `legacy_allowlist.yaml` entry changed (W1 migrates zero sites; the
armed 87-site ratchet holds).
Verified: `PI_REQUIRE_NODE=1 python -m pytest tests/pi_production/test_w1_agentic_contract.py -q`
= 25 passed; full W1 ladder (`test_w1_agentic_contract`, `test_w1_dispatcher_authority`,
`test_structured_fail_closed`, `test_w1_usage_ledger`, `test_count_to_zero`,
`test_same_model_donor_isolation`) = 59 passed; `npm --prefix pi-runtime test` = 33 passed;
`python scripts/feature_docs.py --seed-missing --generate-site --check` = 86 features, 224
artifacts, check passed; `python scripts/security_benchmark.py --fail-on-threshold` = status
pass.
Next: sibling fixers F-W1-1/F-W1-2 complete, then the conductor's one bounded delta
re-review of the changed W1 surface.

### L-19 | 2026-07-20T21:12:56Z | S4-remediate | claude-opus-4-8 | remediator | W1 <!-- bsc-ledger:FIX-pi-full-20260720-w1-REVIEW-r1-structured -->
Did: Closed F-W1-2 — the forced structured-output protocol (v2) and typed fail-closed
behavior. Independently re-verified the resumed structured surface end to end and recorded
evidence (no new defects found; the contract was already fully implemented in the worktree):
both sides pin `PROTOCOL_VERSION=2` and validate it (worker `hello`/per-frame + connection
`fatal`; supervisor `ready`/handshake-`fatal` -> typed `PiWorkerError`); `turn.prompt` carries
`output_schema`/`tool_choice`/`max_turns` and the supervisor `run_turn` forwards them;
`structured.mjs` mechanically translates the supported JSON-Schema subset for
`emit_structured_output` (both sides reject the same unsupported constructs BEFORE any provider
call); `session.mjs` forces the tool per provider family, CAPTURES (never executes /
round-trips to the authority) the arguments, and settles `structured_output_missing` when no
capture occurs (free-form JSON text is never accepted); `engine.py` `run_structured`
revalidates the captured object against the ORIGINAL schema, allows exactly one bounded repair,
then raises a typed `PiRuntimeTurnError` (`structured_output_invalid`/`_missing`) with no
partial or error-shaped artifact. Adversarial worker + Python/Node tests cover unsupported
schema, missing/incorrect tool call, invalid repair, protocol mismatch, and no-partial-artifact.
Files (F-W1-2 scope, in worktree): `pi-runtime/src/{protocol,worker,session,structured}.mjs`,
`pi-runtime/PROTOCOL.md`, `pi-runtime/test/structured.test.mjs`,
`backend/app/core/pi_runtime/{protocol,supervisor}.py`, `engine.py` `run_structured` (shared
file with F-W1-1), `tests/pi_production/{test_structured_fail_closed.py,adversarial_worker_v1.mjs}`.
Result: F-W1-2 open -> fixed; CF task FIX-pi-full-20260720-w1-REVIEW-r1-structured. No product
call site or `legacy_allowlist.yaml` entry changed (W1 migrates zero sites; the armed 87-site
ratchet holds). No manual commit taken: `engine.py` is entangled with the concurrent F-W1-1
authority fixer and this worktree has no `repo_lock.completion_lock`, so the conductor ship
stage owns the atomic commit of the code (harness backstops attribution/finish/ledger).
Verified: `npm --prefix pi-runtime test` = 33 passed; `PI_REQUIRE_NODE=1 python -m pytest
tests/pi_production/test_structured_fail_closed.py -q` = 6 passed; `PI_REQUIRE_NODE=1 python -m
pytest tests/pi_production -q` = 120 passed (full suite green — the structured modules and
`test_seams_fail_closed.py` coexist; the isolated-subset SQLAlchemy `Project`<->`Message`
mapper-config artifact is a pre-existing test-ordering property also present in the committed
W0 `test_scenario_structured_output.py`, never an F-W1-2 logic defect); `python
scripts/security_benchmark.py --fail-on-threshold` = status pass. No live model activity or
external traffic.
Next: stage exit: F-W1-2 fixed; await the conductor's one bounded delta re-review of the
changed structured-output surface once all W1 fixers are terminal.

### L-20 | 2026-07-20T21:30:53Z | S4-remediate | claude-opus-4-8 | remediator | W1 <!-- bsc-ledger:FIX-pi-full-20260720-w1-REVIEW-r1-authority -->
Did: Closed F-W1-1 — the five-verb `AgenticDispatcher` production choke point and the
production-real legacy/Pi authority boundary. Resumed the surface left by the rate-limited
prior fixer (kimi-code/k3-high, hard usage cap at 20:56Z) and independently re-verified it end
to end (no new defects found; the contract was fully implemented in the worktree). All six
verbs (`chat_turn`, `completion`, `structured`, `react`, `ensemble`, `embed`) resolve the
engine through `_resolve` with override>header>project>default precedence; the persisted
`projects.agentic_engine` column (`backend/app/models/project.py`, migration
`024_project_agentic_engine`) drives level 3; and the module singleton binds the REAL
`legacy.py` executor, verified byte-compatible with the live `app.core.ollama.ollama`
ComputeRegistry `chat`/`embed_batch` signatures (`min_context`/`thinking_mode`/`project_id`/
`tools`/`response_format` are real kwargs on the production plane, not stub-only). Every Pi
turn resolves through the isolated `PiModelManager` (no ComputeRegistry import; catalog =
static settings + `pi-deepseek-default` + local Ollama/LM Studio `/v1` + read-only
`pi-llm-<id>` LLMServer projection that excludes relay/browser donors), with model/
require_vision/min_context admission failing closed before any worker frame; all TurnParams are
forwarded (temperature/max_tokens/thinking_mode/timeout_s via `_bind_payload`, model/
require_vision/min_context via admission, max_turns via `turn.prompt` default 8). Pi-selected
`embed` fails typed (`pi_embed_gateway_unavailable`) and never falls back to legacy or donated
compute; distinct ensemble fails closed on insufficient identity-distinct endpoints; telemetry
exposes id/kind/model only, never URL/key. F-W1-1 scope files (in worktree):
`backend/app/core/agentic/{dispatcher,legacy,types}.py`,
`backend/app/core/pi_runtime/{engine,model_manager,endpoints}.py` (`engine.py` shared with
F-W1-2), `backend/app/{config.py,models/project.py}`, migration
`024_project_agentic_engine.py`, `tests/pi_production/test_w1_dispatcher_authority.py`.
Result: F-W1-1 open -> fixed; CF task FIX-pi-full-20260720-w1-REVIEW-r1-authority. No product
call site or `legacy_allowlist.yaml` entry changed (W1 migrates zero sites; the armed 87-site
ratchet holds). No manual code commit taken: `engine.py` is entangled with F-W1-2's
ship-committed structured changes and this worktree has no `repo_lock.completion_lock`, so the
conductor ship stage owns the atomic commit of the code (harness backstops
attribution/finish/ledger).
Verified: `python -m pytest tests/pi_production/test_w1_dispatcher_authority.py -q` = 17 passed;
full W1 ladder (`test_w1_agentic_contract`, `test_w1_dispatcher_authority`,
`test_w1_usage_ledger`, `test_structured_fail_closed`, `test_count_to_zero`,
`test_same_model_donor_isolation`) = 59 passed; full `tests/pi_production` = 120 passed;
`npm --prefix pi-runtime test` = 33 passed; 87-site ratchet (`test_count_to_zero`) = 3 passed;
`python scripts/security_benchmark.py --fail-on-threshold` = status pass (100%, 0 triggered
paths). No live model activity or external traffic.
Next: stage exit: F-W1-1 fixed and all four W1 fixer tasks terminal; the conductor creates one
bounded delta re-review of the changed W1 surface (confirming no later overwrite dropped the
six-verb precedence wiring or the exception-path usage-row recording).

### L-21 | 2026-07-20T21:39:32Z | S3-review | gpt-5.6-sol | reviewer | W1 <!-- bsc-ledger:REREV-pi-full-20260720-w1-REVIEW-r1 -->
Did: Performed the bounded delta re-review of F-W1-1 through F-W1-4 against the four
completed fixer tasks, their evidence, and only the changed W1 files/contracts/immediate
seams. Inspected the combined committed-plus-uncommitted worktree because the authority and
structured fixers explicitly left shared code uncommitted for atomic handoff. Created
`FIX-REREV-pi-full-20260720-w1-REVIEW-r1-protocol` for F-W1-R1-1 and
`FIX-REREV-pi-full-20260720-w1-REVIEW-r1-accounting` for F-W1-R1-2, both owned by
`pi-full-20260720-w1-fixer` and preserving source task, review role, pipeline run, and
self-contained findings.
Result: Fail. F-W1-R1-1 (Blocker) proves the Python half of protocol v2 accepts a
post-handshake `v:1` terminal frame because `PiRuntimeSupervisor._dispatch` does not validate
`frame.v`, contradicting `pi-runtime/PROTOCOL.md` and the living-doc per-frame guarantee.
F-W1-R1-2 (Major) proves real-path accounting remains inexact: Node settlement computes but
does not emit cache-read/cache-write or actual turn count; the real legacy normalizer turns
absent provider usage into a non-empty zero usage block, bypassing the token estimator, and
the legacy tool loop retains only the final turn's usage. The green 59-test W1 ladder and
33-test Node suite rely on rich stubs or cover only the worker's inbound validation, so they
do not refute either immediate-seam defect. F-W1-1 and F-W1-4 otherwise remain closed; the
forced capture/schema/one-repair portions of F-W1-2 remain green.
Verified: `python -m pytest tests/pi_production/test_w1_agentic_contract.py tests/pi_production/test_w1_dispatcher_authority.py tests/pi_production/test_w1_usage_ledger.py tests/pi_production/test_structured_fail_closed.py tests/pi_migration/test_count_to_zero.py tests/pi_production/test_same_model_donor_isolation.py -q` = 59 passed; `npm --prefix pi-runtime test` = 33 passed; `python scripts/feature_docs.py --seed-missing --generate-site --check` = 86 features passed; wrong-version supervisor probe = `{'accepted_wrong_v': True, 'type': 'run.completed', 'usage': {'input_tokens': 9}}`; real legacy no-usage probe = `{'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0, 'estimate': True}`.
Next: Remediate both sibling finding tasks; stage exit is blocked until both are terminal and
one conductor-created bounded delta re-review passes.

### L-22 | 2026-07-20T21:54:06Z | S4-remediate | claude-opus-4-8 | remediator | W1 <!-- bsc-ledger:FIX-REREV-pi-full-20260720-w1-REVIEW-r1-protocol -->
Did: Closed F-W1-R1-1 (Blocker) — the Python half of protocol v2 now validates the version
of every post-handshake frame, not just the handshake `ready.protocol_version`. Added
per-frame version rejection to `PiRuntimeSupervisor._dispatch` and a `_reject_frame` helper
(`backend/app/core/pi_runtime/supervisor.py`): `ready`/`fatal` stay exempt (the
version-negotiation channel, mirroring the worker exempting inbound `hello`), but every other
inbound frame whose `v != PROTOCOL_VERSION` is rejected BEFORE it is queued — the session's
active run settles `run.failed{error:"protocol_version_mismatch"}` (or the offending frame's
own run when none is active, so a stale rejection never kills a later run), and a frame for an
unknown session is logged and dropped. A version mismatch is never process-fatal. This makes
the code match the existing `pi-runtime/PROTOCOL.md` "Versioning" contract and the living
feature-doc claim (no doc change needed — the docs already asserted both-side per-frame
validation). Added `tests/pi_production/test_protocol_version_per_frame.py` (6 node-free
`_dispatch` unit tests + 1 adversarial integration test) and the adversarial worker
`tests/pi_production/adversarial_worker_v1_run.mjs` (valid v2 handshake, then v1 tool.call +
v1 run.completed).
Result: F-W1-R1-1 open -> fixed; CF task FIX-REREV-pi-full-20260720-w1-REVIEW-r1-protocol. The
reviewer's wrong-version probe flips from `{'accepted_wrong_v': True, 'type': 'run.completed'}`
to a v2 `run.failed{protocol_version_mismatch}`; a worker that handshakes v2 then emits a v1
run frame executes no tool (authority `tool_handler` never called) and surfaces no
artifact/usage. No product call site or `legacy_allowlist.yaml` entry changed (W1 migrates
zero sites; the armed 87-site ratchet holds). No manual code commit taken: `supervisor.py` is
entangled with the concurrent structured/authority fixers' uncommitted worktree state and this
worktree has no `repo_lock.completion_lock` (absent `build-stream-conductor/scripts/repo_lock.py`),
so the conductor ship stage owns the atomic commit (harness backstops attribution/finish/ledger),
matching L-19/L-20.
Verified: `PI_REQUIRE_NODE=1 python -m pytest tests/pi_production/test_protocol_version_per_frame.py -q`
= 7 passed; `PI_REQUIRE_NODE=1 python -m pytest tests/pi_production/test_frame_limits.py
tests/pi_production/test_runtime_hardening.py tests/pi_production/test_protocol_version_per_frame.py -q`
= 19 passed; `test_structured_fail_closed.py` = 6 passed and `test_w1_dispatcher_authority.py`
= 17 passed (each in isolation); `npm --prefix pi-runtime test` = 35 passed;
`python scripts/security_benchmark.py --fail-on-threshold` = status pass, 0 triggered paths;
`python scripts/feature_docs.py --seed-missing --generate-site --check` = 86 features passed.
The only failing test in the wider W1 ladder is the inherited shared dev-DB drift
(`sqlite3 no such column: tasks.agent_id`; alembic at head 024), which reproduces identically
with this stage's `supervisor.py` change reverted (`git stash`) — pre-existing environmental
drift outside the protocol seam, not introduced here. No live model activity or external traffic.
Next: Stage exit: F-W1-R1-1 fixed; the accounting sibling (F-W1-R1-2) must also be terminal,
then the conductor creates one bounded delta re-review of the changed protocol-validation surface.

### L-23 | 2026-07-20T22:02:33Z | S4-remediate | claude-opus-4-8 | remediator | W1 <!-- bsc-ledger:FIX-REREV-pi-full-20260720-w1-REVIEW-r1-accounting -->
Did: Closed F-W1-R1-2 — real-path usage-ledger exactness. `pi-runtime/src/session.mjs`
`run.completed` now emits the full cumulative per-run usage via a new `_completedUsage`
helper — `cache_read`/`cache_write`/`total_tokens` and the real `turns` count, not just
input/output/cost — so Pi ledger rows keep cache tokens and never default a multi-turn run
to turns=1; `pi-runtime/PROTOCOL.md` documents the expanded frame.
`backend/app/core/agentic/legacy.py` `_normalize_chat` now leaves usage ABSENT when the
provider reports none (so `usage_ledger` runs its `count_tokens` estimator instead of
treating a fabricated zero block as provider-reported), and a new `_accumulate_usage` helper
makes `_react_loop` and the ensemble `_sum_usage` report cumulative input/output/total plus
the real turn count — provider-reported exact, absent-none estimated. Replaced the rich-stub
coverage with real-seam tests: `pi-runtime/test/hardening.test.mjs` (+2 real openai_compat
loopback proofs — run.completed carries cache/total/turns; usage is cumulative across a real
multi-turn tool loop) and new `tests/pi_production/test_w1_realpath_accounting.py` (real
legacy executor: cumulative multi-turn ReAct, exact provider usage, absent->estimated;
full-stack real Pi worker: cache+turns survive run.completed -> engine -> dispatcher ->
persisted ledger row).
Result: F-W1-R1-2 open -> fixed; CF task FIX-REREV-pi-full-20260720-w1-REVIEW-r1-accounting.
No product call site or `legacy_allowlist.yaml` entry changed (W1 migrates zero sites; the
armed 87-site ratchet holds). No manual code commit taken: the W1 fix code (incl. the
still-untracked `legacy.py`) is uncommitted shared work from the F-W1-1 authority fixer, so
the conductor ship stage owns the atomic commit (harness backstops attribution/finish/ledger),
matching L-19/L-20/L-22; the lifecycle append was serialized under
`repo_lock.completion_lock` (found at the Skills toolchain path).
Verified: `npm --prefix pi-runtime test` = 35 passed (was 33; +2 real-worker usage proofs);
`PI_REQUIRE_NODE=1 python -m pytest tests/pi_production/test_w1_realpath_accounting.py -q` =
4 passed; full W1 ladder + runtime hardening (`test_w1_agentic_contract`,
`test_w1_dispatcher_authority`, `test_w1_usage_ledger`, `test_structured_fail_closed`,
`test_w1_realpath_accounting`, `test_runtime_hardening`, `test_count_to_zero`,
`test_same_model_donor_isolation`) = 74 passed; `PI_REQUIRE_NODE=1 python -m pytest
tests/pi_production -q` = 131 passed; `ruff check` (legacy/usage_ledger/new test) = No issues
found; `python scripts/feature_docs.py --seed-missing --generate-site --check` = 86 features
passed; `python scripts/security_benchmark.py --fail-on-threshold` = status pass. No live
model activity or external traffic.
Next: stage exit: F-W1-R1-2 fixed and both F-W1-R1 sibling fixers terminal; the conductor
creates one bounded delta re-review of the changed protocol-validation + real-path accounting
surface.

### L-24 | 2026-07-20T22:09:38Z | S3-review | gpt-5.6-sol | reviewer | W1 <!-- bsc-ledger:REREV-pi-full-20260720-w1-REVIEW-r2 -->
Did: Performed only the requested delta re-review of F-W1-R1-1/F-W1-R1-2 against
`FIX-REREV-pi-full-20260720-w1-REVIEW-r1-protocol` and
`FIX-REREV-pi-full-20260720-w1-REVIEW-r1-accounting`. Inspected the changed protocol
dispatch/rejection ordering, real-worker cumulative Pi usage, and the changed legacy
`_normalize_chat`/`_accumulate_usage`/ReAct/ensemble seams. The protocol fix rejects
wrong-version post-handshake run/tool frames before queueing, and its adversarial v2-handshake
then v1-run proof executes no tool and accepts no artifact. In the immediate accounting seam,
an adversarial real-legacy-executor probe exposed F-W1-R2-1: when one turn reports usage and a
later turn omits it, `_accumulate_usage` drops the absent turn but returns the reported subset
as `estimate=false` with the full `turns` count.
Result: Fail. F-W1-R1-1 is closed and the fully-reported/fully-absent cases for F-W1-R1-2
pass, but F-W1-R2-1 (Major) means the exact-vs-estimated contract is still violated for mixed
reported+absent legacy ReAct and ensemble runs. Created
`FIX-REREV-pi-full-20260720-w1-REVIEW-r2-accounting-mixed`, owned by
`pi-full-20260720-w1-fixer`, preserving `source_task`, `review_role`, `pipeline_run`,
`fixer_role`, and the self-contained finding. This was not a broad review: the new finding is
inside the helper and two callers changed by the cited accounting fix.
Verified: `PI_REQUIRE_NODE=1 python -m pytest tests/pi_production/test_protocol_version_per_frame.py tests/pi_production/test_w1_realpath_accounting.py -q` = 11 passed; `npm --prefix pi-runtime test` = 35 passed; real `legacy_executor("react")` mixed-usage probe via `PYTHONPATH=backend python` = two provider turns persisted as `input=100`, `output=10`, `turns=2`, `estimate=false` although the final turn reported no usage (finding confirmed). A first ledger-object form of the probe was blocked before its assertion by the inherited SQLAlchemy mapper error `Message` not located; the pure ledger normalization path then reproduced the defect without shared-DB mutation.
Next: Remediate F-W1-R2-1 in `FIX-REREV-pi-full-20260720-w1-REVIEW-r2-accounting-mixed`; once terminal, the conductor creates one bounded delta re-review.

### L-25 | 2026-07-20T22:21:45Z | S4-remediate | claude-opus-4-8 | remediator | W1 <!-- bsc-ledger:FIX-REREV-pi-full-20260720-w1-REVIEW-r2-accounting-mixed -->
Did: Closed F-W1-R2-1 in `backend/app/core/agentic/legacy.py`. `_accumulate_usage` now treats
exactness as all-or-nothing across the whole dispatch: it returns the exact cumulative aggregate
(`estimate=false`, real turn count) ONLY when EVERY turn/sample reported provider usage, and returns
an empty dict for both the fully-absent AND the *mixed* (some reported, at least one absent) cases —
`if not reported or len(reported) < len(usages): return {}`. The empty aggregate makes the dispatcher
ledger run its existing governed `count_tokens` estimator over the complete request/response text and
flag the row `estimate=true`, instead of persisting the reported subset as an exact partial total with
the full `turns` count. Extended the `_react_loop` and `_sum_usage` comments to state the all-or-nothing
contract. No `usage_ledger.py` change was needed: its absent-usage estimation path already handles the
now-empty mixed aggregate, and estimation stays owned by the ledger (legacy.py never re-implements it).
Added real-seam regressions in `tests/pi_production/test_w1_realpath_accounting.py`: legacy ReAct mixed
(reported first turn + absent final turn → estimated, not partial-exact 100/10), legacy ensemble
all-reported (→ exact cumulative 300/30, turns=2), and legacy ensemble mixed (→ estimated, not the
reported subset as exact).
Result: F-W1-R2-1 (Major) fixed — mixed reported+absent legacy ReAct and ensemble runs are now
estimated for the complete dispatch and never labeled exact; a mixed run is accounted exactly like a
fully-absent one. Files: `backend/app/core/agentic/legacy.py`,
`tests/pi_production/test_w1_realpath_accounting.py`. Task
`FIX-REREV-pi-full-20260720-w1-REVIEW-r2-accounting-mixed`.
Verified: `python -m pytest tests/pi_production/test_w1_realpath_accounting.py tests/pi_production/test_w1_usage_ledger.py -q` = 14 passed (11 prior + 3 new); `python -m pytest tests/pi_production/test_w1_agentic_contract.py tests/pi_production/test_w1_dispatcher_authority.py tests/pi_production/test_w1_realpath_accounting.py tests/pi_production/test_w1_usage_ledger.py -q` = 56 passed; `ruff check` on both changed files = No issues found; `python scripts/feature_docs.py --check` = 86 features passed; `python scripts/security_benchmark.py --fail-on-threshold` = status pass (100.0%, no triggered paths). No live model activity or external traffic.
Next: stage exit: F-W1-R2-1 fixed; hand off for the conductor's bounded delta re-review of the changed `_accumulate_usage`/ReAct/ensemble accounting seam.

### L-26 | 2026-07-20T22:30:03Z | S3-review | gpt-5.6-sol | reviewer | W1 <!-- bsc-ledger:REREV-pi-full-20260720-w1-REVIEW-r3 -->
Did: Performed the bounded delta re-review for F-W1-R2-1 against
`FIX-REREV-pi-full-20260720-w1-REVIEW-r2-accounting-mixed`. Inspected only the changed
`_accumulate_usage`/ReAct/ensemble paths, their real-path regressions, and the immediate
dispatcher-to-`usage_ledger` estimation seam. Broadened within that seam because the fix changed
the acceptance path from provider totals to dispatcher text estimation and exposed a concrete
adjacent defect: the estimator does not receive the complete multi-turn/multi-sample dispatch.
Result: **fail**. The fix correctly prevents a reported subset from being labeled exact, but opened
F-W1-R3-1 (Major): returning an empty aggregate causes the ledger to count only the original request
and top-level `outcome.text`. A real mixed two-sample ensemble probe with two non-empty outputs
persisted `input_tokens=3`, `output_tokens=0`, `total_tokens=3`, `turns=1`, `estimate=true`; the
request was counted once despite two dispatches. Mixed ReAct likewise loses repeated prompt/history,
tool-result consumption, and the known turn count. Created
`FIX-REREV-pi-full-20260720-w1-REVIEW-r3-accounting-complete` for the cast fixer; no production code
was changed by the reviewer.
Verified: `PI_REQUIRE_NODE=1 python -m pytest tests/pi_production/test_w1_realpath_accounting.py tests/pi_production/test_w1_usage_ledger.py -q` = 14 passed; `ruff check backend/app/core/agentic/legacy.py tests/pi_production/test_w1_realpath_accounting.py` = clean; `PYTHONPATH=backend python /tmp/rerev_w1_r3_probe.py` = finding reproduced (`input=3`, `output=0`, `turns=1`, estimated for two non-empty samples).
Next: Remediate F-W1-R3-1 in `FIX-REREV-pi-full-20260720-w1-REVIEW-r3-accounting-complete`; after it and any sibling fixes are terminal, the conductor creates one bounded delta re-review.

### L-27 | 2026-07-21T04:48:39Z | S4-remediate | gpt-5.6-terra | remediator | W1 <!-- bsc-ledger:FIX-REREV-pi-full-20260720-w1-REVIEW-r3-accounting-complete -->
Did: Closed F-W1-R3-1 in `backend/app/core/agentic/legacy.py`, `backend/app/core/agentic/usage_ledger.py`, and `tests/pi_production/test_w1_realpath_accounting.py`. Legacy outcomes now carry ephemeral complete-dispatch provenance: each ReAct provider turn records its serialized request history and response, and each ensemble sample contributes its own request/response. The ledger estimates those complete traces only when provider usage is absent or mixed; all-reported runs retain the existing exact aggregate.
Result: F-W1-R3-1 (Major) fixed by `FIX-REREV-pi-full-20260720-w1-REVIEW-r3-accounting-complete`: mixed ReAct includes repeated prompt/history/tool-result consumption and retains its actual turn count; mixed ensembles include every sample request and non-empty output, with `estimate=true` and `turns=2` in the real-path regression.
Verified: `PYTHONPATH=backend pytest -q tests/pi_production/test_w1_realpath_accounting.py` = 7 passed; `PYTHONPATH=backend pytest -q tests/pi_production/test_w1_realpath_accounting.py tests/pi_production/test_w1_dispatcher_authority.py` = 24 passed; `ruff check backend/app/core/agentic/legacy.py backend/app/core/agentic/usage_ledger.py tests/pi_production/test_w1_realpath_accounting.py` = clean; `python scripts/feature_docs.py --seed-missing --generate-site --check` = 86 features passed; Compass Forge post-gate = no new actionable failures (inherited secret-flow/large-file baseline remains).
Next: stage exit: F-W1-R3-1 fixed; hand off for the conductor's bounded delta re-review of the changed legacy provenance and ledger-estimation seam.

### L-28 | 2026-07-21T04:55:57Z | S3-review | claude-opus-4-8 | reviewer | W1 <!-- bsc-ledger:REREV-pi-full-20260720-w1-REVIEW-r4 -->
Did: Performed the bounded delta re-review of F-W1-R3-1 against
`FIX-REREV-pi-full-20260720-w1-REVIEW-r3-accounting-complete` (commit `921376ae`). Inspected only
the changed legacy provenance and ledger-estimation seam: `legacy.py`
`_estimation_trace`/`_completion`/`_structured`/`_react_loop`/`_ensemble`, `usage_ledger.py`
`_estimated_numbers`/`build_usage_row`, the dispatcher `_record_outcome` seam that passes the outcome
through, and the strengthened `test_w1_realpath_accounting.py` regressions. No broadening beyond that
seam was warranted (no architecture/acceptance change; no adjacent defect surfaced).
Result: **pass**. Each turn/sample now carries ephemeral `usage_estimation` provenance (ReAct: per-turn
serialized growing request history + response; ensemble: every sample's request/response), and
`_estimated_numbers` sums `count_tokens` over ALL request/response texts with the real `turns` count —
but only on the absent/mixed estimated path. The exact all-reported branch (`_provider_usage` non-None)
never reaches the estimator, so non-mixed exact behavior is preserved. The specific old failure (mixed
2-sample ensemble persisting `input=3`/`output=0`/`turns=1`) is gone: the regression now asserts
`input>3` (both sample requests), `output>0` (both non-empty outputs), `turns=2`, `estimate=1`; mixed
ReAct asserts `turns=2`, `estimate=1`, and not-the-partial-subset. `usage_estimation` is never persisted
to the row or trace span (no content leak). One non-blocking observation: the mixed-ReAct regression
does not assert cumulative multi-turn magnitude as strongly as the ensemble test, but the shipped code
genuinely accumulates per-turn provenance, so it is a test-hardening nicety, not a defect — no finding
task created.
Verified: `PYTHONPATH=backend python -m pytest -q tests/pi_production/test_w1_realpath_accounting.py` = 7 passed; `PYTHONPATH=backend python -m pytest -q tests/pi_production/test_w1_usage_ledger.py tests/pi_production/test_w1_dispatcher_authority.py` = 24 passed; `PYTHONPATH=backend python -m pytest -q tests/pi_production/test_w1_agentic_contract.py` = 25 passed; `ruff check backend/app/core/agentic/legacy.py backend/app/core/agentic/usage_ledger.py tests/pi_production/test_w1_realpath_accounting.py` = clean.
Next: F-W1-R3-1 confirmed closed; W1 accounting lineage (`pi-full-20260720-w1-REVIEW`) has no open findings. Hand back to the conductor for W1 stage-exit acceptance.

### L-29 | 2026-07-21T06:44:50Z | S4-remediate | gpt-5.6-terra | remediator | W2 <!-- bsc-ledger:FIX-pi-full-20260720-w2-REVIEW-r1 -->
Did: Closed the W2 review remediation in the shared worktree: the four interactive ReAct routes now enter through `AgenticDispatcher` with the queue bridge, the legacy executor streams native provider chunks through `stream_cb`, the browser path resolves its endpoint through `PiModelManager`, and the inventory scanner exempts only the marked Pi-governed construction. Updated Chat and Interface Design Chat living docs and regenerated the site/manifest.
Result: F-W2-1 and its streaming/scanner prerequisites F-W2-1a/F-W2-1b are fixed by `FIX-pi-full-20260720-w2-REVIEW-r1`: all nine W2 interactive surfaces leave the product allowlist and the ratchet is 78. F-W2-INFO remains a non-blocking follow-up because the prior four completion sites still use an empty `project_id` where their callers do not expose a project scope.
Verified: `pytest -q tests/pi_migration/test_count_to_zero.py tests/pi_production/test_w1_agentic_contract.py` = 28 passed; `pytest -q tests/pi_migration tests/pi_production` = 113 passed; `pytest -q tests/test_pi_replacement_candidate.py` = 13 passed; `python scripts/security_benchmark.py --fail-on-threshold` = 28/28 pass; `python scripts/feature_docs.py --seed-missing --generate-site --check` = 86 features passed; `pytest -q tests/test_feature_docs.py` = 6 passed; `compass-forge gate after --task FIX-pi-full-20260720-w2-REVIEW-r1 --summary` = 0 new/actionable failures and 0 drift (inherited secret-flow/large-file failures remain); `git diff --check` = passed.
Next: stage exit: bounded W2 delta re-review may verify F-W2-1/F-W2-1a/F-W2-1b and their immediate route/scanner seams.

### L-30 | 2026-07-21T07:06:00Z | S3-review | claude-opus-4-8 | reviewer | W2 <!-- bsc-ledger:REREV-pi-full-20260720-w2-REVIEW-r1 -->
Did: Ran the bounded W2 delta re-review of `FIX-pi-full-20260720-w2-REVIEW-r1`. Verified the three cited fixes against code + command evidence and inspected only the changed route/legacy/scanner seams for regressions. Confirmed F-W2-1 (ratchet 78; all nine interactive surfaces off the product allowlist, scanner reconciles), F-W2-1a (the legacy executor now streams native provider chunks via `_stream_turn` over `ollama.chat_stream` and the new `bridge.py` queue-bridge, preserving per-token SSE, hallucinated-tool filtering, and the `turn_separator` pre-tool boundary; `compute_registry.chat_stream` accepts the forwarded `min_context/thinking_mode/project_id/strict_model_routing` kwargs — no TypeError), and F-W2-1b (browser_service resolves endpoint identity through `PiModelManager.resolve` and records a governed `tool.browse_website` ledger row; the inventory scanner exempts only the inline `# pi-governed` construction, a documented owner decision).
Result: **FAIL** — the three fixes are correct and re-verified, but the migration INTRODUCED one Blocker regression in the immediate seam it changed. `backend/app/api/routes/chat.py` `_generate_native_tools` and `_generate_text_fallback` append the tool-result display to `all_text_parts` TWICE: the route-local `_tool_exec` closure appends `result_display` directly (chat.py:364 / :461) AND enqueues the same `{type:content}` event, which the main SSE loop re-appends when the bridge re-yields it (chat.py:394 / :490). Because the persisted assistant `Message` is `"".join(all_text_parts)` (chat.py:951), every tool-using non-Pi chat turn saves each `**<tool>**: <result>` block duplicated; the synchronous `_tool_exec` append also races AHEAD of the async-drained streamed tokens, so the persisted transcript is duplicated AND mis-ordered. The SSE wire copy is correct (once). The Pi path (chat.py:164-173) and interfaces.py design chat (interfaces.py:161-165) correctly do NOT append in `_tool_exec`, and HEAD appended the display exactly once — confirming the regression. Opened **F-W2-R1-1** (Blocker) under the w2-fixer.
Verified: `python -m pytest -q tests/pi_migration/test_count_to_zero.py tests/pi_production/test_w1_agentic_contract.py` = 28 passed (ratchet=78, only-ratchets-down holds); `python -m pytest -q tests/pi_migration tests/pi_production` = 137 passed; `python -m pytest -q tests/test_pi_replacement_candidate.py` = 13 passed; focused proof driving `chat._generate_native_tools` with a single tool call → `all_text_parts == ['**list_tasks**: TOOLRESULT\n\n','thinking ','**list_tasks**: TOOLRESULT\n\n','final answer']` (display persisted 2×, expected 1; SSE wire copy 1×). The regression is uncovered by the suites because the candidate fail-closed tests return before any tool call.
Next: `pi-full-20260720-w2-fixer` closes F-W2-R1-1 (delete the direct `all_text_parts.append(result_display)` in both chat.py `_tool_exec` closures; rely on the queued content event; drop the secondary `observe_chunk` double-count; add a route-level persist-once/in-order regression test), then the conductor creates the bounded delta re-review.

### L-31 | 2026-07-21T07:25:00Z | S3-review | claude-opus-4-8 | reviewer | W2 <!-- bsc-ledger:REREV-pi-full-20260720-w2-REVIEW-r2 -->
Did: Ran the bounded W2 delta re-review r2 of `CF-190` (`FIX-REREV-pi-full-20260720-w2-REVIEW-r1`)
against F-W2-R1-1. Verified the cited fix against code + command evidence and inspected only the
changed seam: `backend/app/api/routes/chat.py` `_generate_native_tools`/`_generate_text_fallback`
`_tool_exec` closures and their main-loop drain, `backend/app/core/agentic/bridge.py`, and
`backend/app/core/agentic/legacy.py` `_react_loop`/`_stream_turn`. No broadening warranted (no
architecture/acceptance change; no adjacent defect beyond the non-blocking pre-existing lint below).
Result: **pass**. F-W2-R1-1 (Blocker) is closed: both `_tool_exec` closures now ONLY enqueue the
tool-result display (`queue.put({type:content,text:result_display})`); the direct
`all_text_parts.append(result_display)` is deleted from both (grep confirms `result_display` is only
`put` on the queue, and `all_text_parts.append(text)` appears only in the three main-loop drains —
Pi:200, native:398, text-fallback:497). The shared FIFO queue interleaves engine tokens and tool
displays in execution order, and `bridge.py` emits its terminal `_complete`/exc sentinel only after
all prior queue events, so each display is persisted exactly once, in stream order, with no loss on a
later-turn error; `turn_separator` is streamed to the wire but not appended, avoiding a double
newline. Traced both loops end-to-end: native persisted == `"thinking "+display+"final answer"`,
text-fallback == `"Before tool\n\n"+display+"final answer"`. The two new route regression tests
assert persist-once, exact order, tool-executed, and SSE-wire-once for both loops (fail pre-fix
`count==2`, pass post-fix). The finding's secondary `observe_chunk` double-count claim was inaccurate
— `observe_chunk` only runs in the main-loop drains, so the display was already counted once; the
fixer correctly made no `observe_chunk` change (its self-report notes the same). One non-blocking
observation (no finding task, not fix-induced): chat.py carries 33 pre-existing ruff errors at HEAD
(34 in working tree; the +2 are benign `F811` — the `agent` param shadows the module-level
`from app.core.agent import agent`, mirroring HEAD's own Pi-path closure, and `agent_id=agent` is
passed correctly) and `bridge.py` has 1 `UP035` from the r1 migration; chat.py was never ruff-clean
at HEAD, so this is not a fix-induced acceptance change.
Verified: `python -m pytest tests/test_pi_replacement_candidate.py::test_native_tools_persists_tool_result_display_once_in_stream_order tests/test_pi_replacement_candidate.py::test_text_fallback_persists_tool_result_display_once_in_stream_order -q` = 2 passed; `python -m pytest tests/pi_production tests/pi_migration -q` = 137 passed; `python -m pytest tests/test_pi_replacement_candidate.py tests/pi_production/test_w1_agentic_contract.py tests/pi_production/test_chat_pi_asgi.py -q` = 43 passed; `grep -n result_display/all_text_parts.append backend/app/api/routes/chat.py` = direct append absent, drains only in the main loop.
Next: F-W2-R1-1 confirmed closed; the `pi-full-20260720-w2-REVIEW` lineage has no open findings. Hand back to the conductor for W2 stage-exit acceptance.

### L-32 | 2026-07-21T10:31:41Z | S2-execute | kimi-code/k3 | executor | W3 <!-- bsc-ledger:pi-full-20260720-w3-IMPL -->
Did: Migrated the eight W3 research-spine + steering sites through the AgenticDispatcher (master plan §8 W3): L1 `_execute_general_task` ReAct → `react`/`spine.react` (one Pi session per task, `session_key=task:{id}`, `max_turns=5`, ranked `run_skill` injected as a per-run dynamic tool via new `extra_tools` plumbing: `pi_runtime/tools.py` catalog merge, `engine.run_react`/`_drive_turn` pass-through, `dispatcher.react` `tools`/`extra_tools` params); L2 `_create_research_plan` → `structured`/`spine.plan` (same step schema on both engines, temperature/max_tokens/min_context/thinking_mode preserved); L3 `_execute_single_step` → `completion`/`spine.step_execute` (DAG-parallel fan-out unchanged); L5 `_self_verify_output` → `structured`/`spine.verify` (regex-JSON upgraded to a `{verified, confidence, reason}` schema both engines enforce — the plan's deliberate baseline improvement); L6 `self_check.verify_claim` → `structured`/`spine.self_check` (line-format parse upgraded to a schema; an unparsed legacy outcome degrades to UNVERIFIED exactly as garbage line-format did); L7 skill-improvement reflection → `completion`/`spine.skill_reflection`; L10 `_execute_steering_message` reply → `chat_turn`/`steering.reply` with a per-message session + `SteeringBinding` (queued steer/follow-up deliver mid-turn and /steering abort maps to turn.abort, H-5). Every call carries spine_phase (plan/execution/review/grounding/governance/intent) + task_id into the usage ledger. Allowlist ratchet 78→70 (8 product entries removed; W4 `agent_lifecycle` keys re-pinned after the line shift: 857→870, 942→955, 996→1009; `agent_execution` embed keys 824→833, 832→841). `test_agent_research_plan_parses_dag_dependencies` re-seamed to the legacy plane the dispatcher's legacy executor calls. New `tests/pi_production/test_w3_research_spine.py` (16 tests: static no-direct-legacy proofs, extra_tools catalog merge, dispatcher forwarding, L5/L6 behavior + fallbacks, spine_phase ledger persistence). Files: `backend/app/core/{agent_research,self_check,agent_execution,agent_lifecycle}.py`, `backend/app/core/agentic/dispatcher.py`, `backend/app/core/pi_runtime/{engine,tools}.py`, `tests/pi_migration/{legacy_allowlist.yaml,test_count_to_zero.py}`, `tests/pi_production/{test_w1_agentic_contract,test_w3_research_spine}.py`, `tests/test_agents.py`.
Result: ratchet 70 with count-to-zero green; all eight W3 sites enter through the dispatcher on both engines with fail-closed behavior preserved (L2/L5/L7 fallbacks unchanged); no findings raised (review stage judges next). Note: `$CONDUCTOR_LIFECYCLE` named the master plan, but the initiative ledger lives here (W1/W2 precedent), so this entry lands in this file.
Verified: `pytest tests/pi_migration/test_count_to_zero.py` = 3 passed; `pytest tests/pi_production/test_w3_research_spine.py` = 16 passed; `pytest tests/pi_production tests/pi_migration` = 138 passed + 12 pre-existing env failures (byte-identical set on clean HEAD tree, incl. node/DB-dependent scenario tests); `pytest tests/test_agents.py tests/test_validation_project_scope.py tests/test_research_validity_contract.py tests/test_research_integrity_code_applications.py tests/test_project_scope_contracts.py` = 83 passed + 11 pre-existing failures (identical on clean tree); steering suites (test_steering/manager/queue/project_scope_contracts) = 28 passed; ruff per-file error counts ≤ HEAD baseline on every touched file (dispatcher 51 vs 53; new test file clean); `python scripts/security_benchmark.py --fail-on-threshold` = pass (no triggered paths); `python scripts/feature_docs.py --seed-missing --generate-site --check` = 86 features passed; `compass-forge gate after` = 0 new failures, 0 drift.
Next: W3 code review (`pi-full-20260720-w3-REVIEW`) — comprehensive pass over the diff, acceptance, and the L1/L5/L6 behavior-parity seams.

### L-33 | 2026-07-21T10:44:00Z | S3-review | claude-fable-5 | reviewer | W3 <!-- bsc-ledger:pi-full-20260720-w3-REVIEW -->
Did: Comprehensive W3 code review of the implementer's diff (8c43f765..afb7343b: `eb8e152f` extra_tools plumbing, `6a93a9cf` spine+steering migration, `62eb9979` ratchet+tests, `afb7343b` ledger). Verified each of the 8 sites against master plan §8 W3: L1 `_execute_general_task` → `react`/`spine.react` (session_key `task:{id}`, `max_turns=5`, ranked `run_skill` as per-run `extra_tools`, tool_names allowlist authoritative on both engines — `pi_runtime/tools.py` drops any dynamic tool outside `allowed_tools`); L2 `_create_research_plan` → `structured`/`spine.plan` (same step schema, T=0.3/MT=900/min_context/TM=off preserved); L3 `_execute_single_step` → `completion`/`spine.step_execute` (DAG-parallel `asyncio.gather` fan-out untouched); L5 → `structured`/`spine.verify` with the planned `{verified,confidence,reason}` schema + heuristic fallbacks intact; L6 `verify_claim` → `structured`/`spine.self_check` (enum-schema upgrade; unparsed outcome degrades to UNVERIFIED; engine failure propagates as before); L7 → `completion`/`spine.skill_reflection` (T=0.3, exception fallback intact); L10 steering reply → `chat_turn`/`steering.reply` with per-message session + `SteeringBinding` (H-5). Checked seam signatures end-to-end (dispatcher.react tools/extra_tools/steering_binding, legacy `_react_loop` `{tool,params}` tool_calls shape, `StructuredResult.value` always a dict), spine_phase values all within the §8 taxonomy, allowlist ratchet edits (8 entries removed, W4/embed keys re-pinned after line shifts), and scope (no out-of-scope files; W4 sites `agent_lifecycle.py:870/955/1009` still legacy as the contract test pins).
Result: **PASS** — no Blocker/Major findings; `pi-full-20260720-w3-REVIEW` verdict recorded. Non-blocking observations logged in the verdict + register: (a) L1 legacy-path outcome text aggregates intermediate turn text (dispatcher loop semantics, implementer-declared accepted risk, W2 precedent); (b) L1 failed-JSON-parse telemetry granularity lost (engine pre-parses args; behavior preserved); (c) stale "Chat sites (69)" comment in `legacy_allowlist.yaml`.
Verified: `python -m pytest tests/pi_production/test_w3_research_spine.py tests/pi_migration/test_count_to_zero.py tests/pi_production/test_w1_agentic_contract.py -q` = 44 passed; `python -m pytest tests/pi_production tests/pi_migration -q` = 153 passed; `python -m pytest tests/test_agents.py -q` = 27 passed; `python -m pytest tests/test_steering.py tests/test_steering_api.py tests/test_integration_agent_work_cycle.py tests/test_research_validity_contract.py tests/test_pi_replacement_candidate.py -q` = 57 passed (all green in this environment; no failures to reconcile).
Next: stage exit: W3 review passed with no open findings — hand back to the conductor for W3 stage-exit acceptance (W4 A2A migration next per the master plan).


### L-34 | 2026-07-21T11:09:13Z | S3-review | claude-fable-5 | reviewer | W4 <!-- bsc-ledger:pi-full-20260720-w4-REVIEW -->
Did: Comprehensive W4 code review of the implementer's working-tree diff (uncommitted on `Review_pi_test`): `backend/app/core/agent_lifecycle.py` (+85/-24), `tests/pi_migration/legacy_allowlist.yaml` (re-pinned keys + W4 note), new `tests/pi_production/test_w4_a2a_handlers.py` (6 tests); `recipe.toml` delta is the conductor's W4 cast roles, not implementer scope. Verified all three A2A sites against master plan §8 W4: `_handle_collaboration` → `agentic.chat_turn` (session `a2a-collab:{context_id}`, system/history/user_text split of the legacy `llm_messages` is byte-identical to the legacy list, `spine_phase=synthesis`, task_id threaded); `_initiate_debate` synthesis → `agentic.completion`/`a2a.debate_synthesis` (`spine_phase=synthesis`, task.id); `_handle_debate` critique → `agentic.completion`/`a2a.debate_critique` (`spine_phase=review`, task_id-or-None) — each gated on `settings.agentic_core` with the legacy `ollama.chat` branch preserved verbatim for flag-off. Checked every kwarg against `dispatcher.py` `chat_turn`/`completion` signatures, spine_phase taxonomy membership, project-scope threading into `send_message`, allowlist keys 870/955/1009→893/1004/1074 with ratchet correctly held at 70 (legacy branch preserved, not retired), and ruff via stash-compare (36 findings with diff vs 37 at baseline; none in the changed hunks; new test file clean).
Result: **PASS** — no Blocker/Major findings; `pi-full-20260720-w4-REVIEW` verdict recorded; no fixer round required. Non-blocking observations logged in the verdict + W4 register: (a) with RAG context present, `user_text` becomes the RAG document and the current message rides in history (model input unchanged; implementer-declared residual risk confirmed accurate); (b) framing calls the collaboration path "a2a.collaboration" but `chat_turn` records `purpose=chat_turn` — the `a2a-collab:` session_key is the distinguishing tag; (c) process: the W4-IMPL ledger entry is absent from this file (implementer skipped step 5; its harness fallback has not landed) — conductor's bookkeeping, not a code defect.
Verified: `pytest tests/pi_production/test_w4_a2a_handlers.py tests/pi_migration -q` = 9 passed; `pytest tests/pi_production -q` = 156 passed; `pytest tests/test_a2a_security.py tests/test_a2a_project_claims.py tests/test_a2a_service_scope.py -q` = 13 passed; `python scripts/pi_migration_inventory.py --json` = 56 rows, all allowlisted; `ruff check` = no new findings vs stashed baseline.
Next: stage exit: W4 review passed with no open findings — hand back to the conductor for W4 stage-exit acceptance.

## W0 — hardening and evidence integrity

**Frame/Plan:** Master plan §6 plus §12.2. Arm the deterministic inventory/ratchet before
further migration, correct the CF-SPEC-7 historical claim append-only, and implement H-1
through H-14 with named regression tests. Preserve Petals/donor isolation.

**Execution:** Pending conductor.

### Review (W0) — Findings register

| ID | Sev | Dim | Where | Finding | CF task | Status |
|---|---|---|---|---|---|---|
| F-1 | Blocker | Product | `scripts/pi_migration_inventory.py`; `tests/pi_migration/` | M0 inventory scanner, complete 87-site plus permanent-infrastructure allowlist, count-to-zero ratchet, and e2e ladder registration are present. | FIX-pi-full-20260720-w0-REVIEW-r1 | fixed |
| F-2 | Blocker | Bugs | `pi-runtime/src/provider.mjs`; `pi-runtime/src/session.mjs`; `backend/app/config.py`; `backend/app/core/pi_runtime/{endpoints,engine}.py`; cost regressions | Per-category pricing closed by `FIX-REREV-pi-full-20260720-w0-REVIEW-r4` and independently verified by `REREV-pi-full-20260720-w0-REVIEW-r5`: `buildRealProvider` exposes the full per-category rate map (`binding.pricing`) instead of a boolean-OR flag, and `session.mjs` fails a budgeted real run closed (`cost_budget_unpriced`) when it spent tokens in ANY $0-rated category (input/output/cache-read/cache-write, via `_hasUnpricedSpend`). The default `deepseek-v4-pro` endpoint is re-sourced to the 2026-07-20 published rates (0.435 cache-miss input, 0.87 output, 0.003625 cache-hit input) and prices cache-read. Non-faux Node + full-stack Python regressions cover cached/partially-priced usage: 1M cache-read tokens on an input/output-only endpoint now fails closed, and a priced cached turn prices its cache reads nonzero. | FIX-REREV-pi-full-20260720-w0-REVIEW-r4 | fixed |
| F-3 | Blocker | Integration | `tests/pi_production/`; `docs/build-stream/2026-07-20-pi-production-runtime-completion.md` | H-13 real-ASGI tests and append-only CF-SPEC-7 correction are present; H-14 fails loudly under `PI_REQUIRE_NODE=1`. | FIX-pi-full-20260720-w0-REVIEW-r1 | fixed |
| F-4 | Major | Plan | master plan §8.6; W0 evidence/docs | Deterministic verification, security, post-gate evidence, and the package test entrypoint are recorded. | FIX-pi-full-20260720-w0-REVIEW-r1 | fixed |

**Remediation:** `FIX-pi-full-20260720-w0-REVIEW-r1` closed F-1, F-3, and F-4.
`FIX-REREV-pi-full-20260720-w0-REVIEW-r1` repaired H-2/H-10 and implemented initial
H-6/H-12 limits/pooling, but L-8 reopened F-2 under
`FIX-REREV-pi-full-20260720-w0-REVIEW-r2` for the missing budget behavior proofs and the
exact configured session-key routing/20-concurrent-turn acceptance contract.
`FIX-REREV-pi-full-20260720-w0-REVIEW-r2` (L-9) closed F-2: the configured
session-key-hash pool, the 20-concurrent-turn proof, and the wall-clock/cost terminal
regressions are now present. The conductor creates the next bounded delta re-review
before W0 advances. L-10 reopened the production-cost portion under
`FIX-REREV-pi-full-20260720-w0-REVIEW-r3`: the terminal regression was reachable
only through the faux provider because real endpoint model rates remained zero.
`FIX-REREV-pi-full-20260720-w0-REVIEW-r3` (L-11) closed that gap: trustworthy
per-endpoint pricing now threads config → `_bind_payload` → `buildRealProvider`
onto the pi-ai model rates (the default DeepSeek endpoint seeded, custom endpoints
configurable), the per-run ceiling is cumulative across turns, an unpriced budgeted
real binding fails closed (`cost_budget_unpriced`), and non-faux loopback
regressions on the Node worker and through the Python engine prove `max_cost_usd`
fires for real usage. The conductor creates the bounded delta re-review of this
changed surface before W0 advances. L-12 reopened F-2 under
`FIX-REREV-pi-full-20260720-w0-REVIEW-r4`: partially priced bindings are treated
as fully configured even when a spent category remains zero-rated, and the
built-in `deepseek-v4-pro` defaults do not match the current official v4-pro
cache-hit/cache-miss/output schedule. `FIX-REREV-pi-full-20260720-w0-REVIEW-r4`
closed both gaps, and the bounded L-14 delta re-review passed with no new findings.

**Phase summary:** Pending.

## W1 — dispatcher, Pi model management, and accounting

**Frame/Plan:** Master plan sections 4, 5, 7, and 12. Add the complete five-verb
dispatcher, isolated Pi endpoint authority, production-real Pi and legacy seams, forced
structured-output protocol, one-row usage accounting, and retain the armed 87-site ratchet.

### Review (W1) — Findings register

| ID | Sev | Dim | Where | Finding | CF task | Status |
|---|---|---|---|---|---|---|
| F-W1-1 | Blocker | Integration | `backend/app/core/agentic/{dispatcher,legacy,types}.py`; `backend/app/core/pi_runtime/{engine,model_manager,endpoints}.py`; `backend/app/{config,models/project}.py`; migration `024` | Closed by `FIX-pi-full-20260720-w1-REVIEW-r1-authority` (L-20): all five verbs plus `react` route through the dispatcher with override>header>project>default engine precedence wired into every verb and persisted via the `projects.agentic_engine` column (migration `024`); the module singleton binds the REAL `legacy.py` executor, byte-compatible with the live `app.core.ollama.ollama` ComputeRegistry `chat`/`embed_batch` signatures; `PiExecutionService` resolves every turn through the isolated `PiModelManager` (no ComputeRegistry import; static-settings + `pi-deepseek-default` + local `/v1` + read-only `pi-llm-<id>` LLMServer sources excluding relay/browser donors) with fail-closed model/require_vision/min_context admission; all TurnParams are forwarded (generation knobs via `_bind_payload`, capability filters via admission, `max_turns` via `turn.prompt`); Pi `embed` fails typed and never falls back; endpoint identity isolation (id/kind/model only) is preserved; negative and non-faux immediate-seam tests added. Verified: `test_w1_dispatcher_authority.py` = 17 passed; full W1 ladder = 59 passed; full `tests/pi_production` = 120 passed; `npm --prefix pi-runtime test` = 33 passed; 87-site ratchet = 3 passed; security benchmark = pass. | FIX-pi-full-20260720-w1-REVIEW-r1-authority | fixed |
| F-W1-2 | Blocker | Bugs | `backend/app/core/pi_runtime/{engine,protocol,supervisor}.py`; `pi-runtime/src/{protocol,worker,session,structured}.mjs` | Closed by `FIX-pi-full-20260720-w1-REVIEW-r1-structured` (L-19): `PROTOCOL_VERSION=2` is pinned and validated on both sides (worker `hello`/per-frame `fatal`/rejection; supervisor `ready`/handshake-`fatal` -> typed `PiWorkerError`); `turn.prompt` carries `output_schema`/`tool_choice`/`max_turns` and the supervisor forwards them; `structured.mjs` mechanically translates the supported JSON-Schema subset for the forced `emit_structured_output` tool (both sides reject the same unsupported constructs before any provider call); the tool CAPTURES (never executes/round-trips) its arguments and a run with no capture settles `structured_output_missing` (free-form JSON text is never accepted); `engine.py` `run_structured` revalidates the captured object against the ORIGINAL schema, allows exactly one bounded repair, then raises a typed `PiRuntimeTurnError` (`structured_output_invalid`/`_missing`) with no partial/error-shaped artifact. Adversarial worker + Node/Python tests cover unsupported schema, missing/incorrect tool call, invalid repair, protocol mismatch, and no-partial-artifact. Verified: `npm --prefix pi-runtime test` = 33 passed; `test_structured_fail_closed.py` = 6 passed; full `tests/pi_production` = 120 passed; security benchmark = pass. | FIX-pi-full-20260720-w1-REVIEW-r1-structured | fixed |
| F-W1-3 | Major | Data | `backend/app/core/agentic/usage_ledger.py`; telemetry persistence | The usage ledger is neither exact nor complete: provider-reported legacy usage defaults to `estimate=true`, absent usage is not estimated with the existing counter, exception paths record no row, required task/spine/node fields are absent, and the row is packed into the short identity-oriented `route_id` field. | FIX-pi-full-20260720-w1-REVIEW-r1-ledger | fixed |
| F-W1-4 | Major | Docs | `tests/pi_production/test_w1_agentic_contract.py`; `docs/features/` | Closed by `FIX-pi-full-20260720-w1-REVIEW-r1-docs-tests` (L-18): the W1 living feature docs are code-accurate across all five behaviors — `chat/model-controls` covers the dispatcher/engine selection/precedence/`TurnParams`, the forced `emit_structured_output` structured contract, the `PROTOCOL_VERSION=2` handshake mismatch, and the durable `agentic_usage_rows` ledger; `settings/llm-servers` and `compute/pool` cover the isolated Pi catalog sources/capabilities and bidirectional donor isolation (site/manifests regenerated, `feature_docs --check` green for 86 features). The self-consistent smoke coverage is replaced by contract-complete `test_w1_agentic_contract.py` proving all five verbs on both real engine seams, precedence resolution, parameter forwarding, catalog sources/capabilities, typed structured failure, one-row ledger persistence (incl. the exception path), protocol mismatch, the unchanged 87-site ratchet, and same-model donor isolation — all faux/loopback/static. | FIX-pi-full-20260720-w1-REVIEW-r1-docs-tests | fixed |
| F-W1-R1-1 | Blocker | Integration | `backend/app/core/pi_runtime/supervisor.py`; `pi-runtime/PROTOCOL.md`; protocol mismatch tests | Closed by `FIX-REREV-pi-full-20260720-w1-REVIEW-r1-protocol` (L-22): `PiRuntimeSupervisor._dispatch` now validates `frame.v` per-frame — `ready`/`fatal` stay exempt (the version-negotiation channel, validated in `ensure_started` via `protocol_version`), but every other post-handshake frame whose `v != PROTOCOL_VERSION` is rejected BEFORE it is queued via `_reject_frame`, settling the session's active run `run.failed{error:"protocol_version_mismatch"}` (or the offending frame's own run when none is active; a frame for an unknown session is logged and dropped). A version mismatch is never process-fatal, matching the existing `pi-runtime/PROTOCOL.md` "Versioning" contract and living-doc claim (no doc change needed). A v2-handshake-then-v1-run worker now executes no tool and surfaces no artifact/usage. Verified: `test_protocol_version_per_frame.py` (6 node-free `_dispatch` unit tests + 1 adversarial integration test) = 7 passed; supervisor/runtime-adjacent seams = 19 passed; `npm --prefix pi-runtime test` = 35 passed; security benchmark + feature docs green. | FIX-REREV-pi-full-20260720-w1-REVIEW-r1-protocol | fixed |
| F-W1-R1-2 | Major | Data | `pi-runtime/src/session.mjs`; `backend/app/core/agentic/legacy.py`; real-path ledger tests | Closed by `FIX-REREV-pi-full-20260720-w1-REVIEW-r1-accounting` (L-23): `session.mjs` `run.completed` now emits the full cumulative per-run usage — `cache_read`/`cache_write`/`total_tokens` and the real `turns` count (via `_completedUsage`), not just input/output/cost — so Pi rows keep cache tokens and never record a multi-turn run as one turn; `legacy.py` `_normalize_chat` leaves usage absent when the provider reports none (the ledger's `count_tokens` estimator runs instead of persisting a fabricated exact-zero row), and `_accumulate_usage` makes `_react_loop`/`_sum_usage` report cumulative provider usage plus the real turn count. Real-worker (Node loopback) and real-legacy-executor + full-stack-Pi seam tests replace the rich stubs. Verified: `npm --prefix pi-runtime test` = 35 passed; `test_w1_realpath_accounting.py` = 4 passed; W1 ladder + hardening = 74 passed; full `tests/pi_production` = 131 passed; ruff clean; feature docs 86; security pass. | FIX-REREV-pi-full-20260720-w1-REVIEW-r1-accounting | fixed |
| F-W1-R2-1 | Major | Data | `backend/app/core/agentic/legacy.py:77-99,156-267`; `backend/app/core/agentic/usage_ledger.py:37-88` | Closed by `FIX-REREV-pi-full-20260720-w1-REVIEW-r2-accounting-mixed` (L-25): `_accumulate_usage` now enforces all-or-nothing exactness across the dispatch — it returns the exact cumulative aggregate only when EVERY turn/sample reported provider usage, and returns an empty dict for the fully-absent AND the mixed (some reported, some absent) cases so the ledger produces one governed `count_tokens` estimate over the complete dispatch (`estimate=true`) instead of persisting the reported subset as an exact partial total; a mixed run is accounted exactly like a fully-absent one. No `usage_ledger.py` change was needed (its absent-usage estimator already handles the empty aggregate; estimation stays ledger-owned). Real ReAct-mixed, ensemble-all-reported-exact, and ensemble-mixed regressions added to `test_w1_realpath_accounting.py`. Verified: accounting+ledger seam = 14 passed (11 prior + 3 new); full W1 seam = 56 passed; ruff clean; feature docs 86; security pass. | FIX-REREV-pi-full-20260720-w1-REVIEW-r2-accounting-mixed | fixed |
| F-W1-R3-1 | Major | Data | `backend/app/core/agentic/{legacy,dispatcher,usage_ledger}.py`; `tests/pi_production/test_w1_realpath_accounting.py` | Closed by `FIX-REREV-pi-full-20260720-w1-REVIEW-r3-accounting-complete` (L-27): mixed legacy ReAct carries each complete provider-turn request history and response, and ensembles carry every sample request/response, as ephemeral estimation provenance. `usage_ledger` estimates those complete traces only when usage is absent or mixed, preserving all-reported exact aggregates; real-path regressions require meaningful complete input/output and real turns. Verified: accounting test = 7 passed; accounting plus dispatcher authority = 24 passed; ruff + feature docs clean; CF delta gate found no new actionable drift. Independently confirmed closed by the bounded L-28 delta re-review (pass): estimated path sums every request/response with the real turn count while the exact all-reported path is untouched, the old mixed ensemble `input=3`/`output=0`/`turns=1` symptom no longer reproduces, and `usage_estimation` never persists content. | FIX-REREV-pi-full-20260720-w1-REVIEW-r3-accounting-complete | fixed (re-review passed L-28) |

**Remediation:** `FIX-pi-full-20260720-w1-REVIEW-r1-ledger` (L-17) closed F-W1-3, `FIX-pi-full-20260720-w1-REVIEW-r1-docs-tests` (L-18) closed F-W1-4, `FIX-pi-full-20260720-w1-REVIEW-r1-structured` (L-19) closed F-W1-2, and `FIX-pi-full-20260720-w1-REVIEW-r1-authority` (L-20) closed F-W1-1. The bounded L-21 delta re-review then opened F-W1-R1-1 and F-W1-R1-2 under two sibling fixer tasks. `FIX-REREV-pi-full-20260720-w1-REVIEW-r1-protocol` (L-22) closed F-W1-R1-1 by adding Python-side per-frame `frame.v` validation in `PiRuntimeSupervisor._dispatch` (reject before queueing; settle the active run `protocol_version_mismatch`, never process-fatal). `FIX-REREV-pi-full-20260720-w1-REVIEW-r1-accounting` (L-23) then closed F-W1-R1-2 by emitting the full cumulative Pi `run.completed` usage (cache/total/turns) and making the legacy normalizer/ReAct/ensemble paths accumulate cumulative provider usage while leaving absent usage to the estimator, proven by new real-worker and real-legacy-executor seam tests. Both F-W1-R1 sibling fixers became terminal, but the bounded L-24 delta re-review found the mixed reported+absent legacy case still persisted a partial aggregate as exact and opened F-W1-R2-1 under `FIX-REREV-pi-full-20260720-w1-REVIEW-r2-accounting-mixed`. L-25 closed that partial-exact symptom by making `_accumulate_usage` all-or-nothing. The bounded L-26 review showed the fallback estimate is still not complete and opened F-W1-R3-1 under `FIX-REREV-pi-full-20260720-w1-REVIEW-r3-accounting-complete`: ensemble outputs are absent from the ledger input, requests are not multiplied by sample count, and known multi-turn counts collapse to one. L-27 closed F-W1-R3-1 by carrying ephemeral complete-dispatch provenance in each legacy outcome (per-turn ReAct request-history/response, per-sample ensemble request/response) that the ledger estimates over on the absent/mixed path while leaving the all-reported exact aggregate intact. The bounded L-28 delta re-review verified that fix and **passed** with no new findings, closing the `pi-full-20260720-w1-REVIEW` accounting lineage.

**Phase summary:** Pending.

## W2 — interactive-surface migration

### Review (W2) — Findings register

| ID | Sev | Dim | Where | Finding | CF task | Status |
|---|---|---|---|---|---|---|
| F-W2-1 | Blocker | Integration | `backend/app/api/routes/{chat,interfaces}.py`; `backend/app/services/browser_service.py`; migration ratchet | Completed by `FIX-pi-full-20260720-w2-REVIEW-r1`: the five remaining product entries now use the dispatcher/governed endpoint path and the allowlist ratchet is 78. | FIX-pi-full-20260720-w2-REVIEW-r1 | fixed (L-29); re-verified L-30 |
| F-W2-1a | Blocker-prerequisite | Bugs | `backend/app/core/agentic/{legacy,bridge,types}.py` | Completed by `FIX-pi-full-20260720-w2-REVIEW-r1`: the legacy executor forwards native provider chunks through the SSE bridge while retaining tool-call filtering and execution. | FIX-pi-full-20260720-w2-REVIEW-r1 | fixed (L-29); re-verified L-30 (streaming/filtering seam correct; but see F-W2-R1-1 for a route persistence regression) |
| F-W2-1b | Blocker-prerequisite | Governance | `scripts/pi_migration_inventory.py`; `backend/app/services/browser_service.py` | Completed by `FIX-pi-full-20260720-w2-REVIEW-r1`: only an inline `pi-governed` ChatOpenAI construction whose endpoint comes from `PiModelManager` is exempt from the legacy inventory. | FIX-pi-full-20260720-w2-REVIEW-r1 | fixed (L-29); re-verified L-30 (marker-based exemption is an accepted honor-system governance decision) |
| F-W2-R1-1 | Blocker | Bugs | `backend/app/api/routes/chat.py:340-370,398,455-470,497,958` | Closed by `CF-190` (L-31): the migrated `_generate_native_tools`/`_generate_text_fallback` `_tool_exec` closures now ONLY enqueue the tool-result display (`queue.put({type:content,text:result_display})`); the direct `all_text_parts.append(result_display)` is deleted from both, so the shared FIFO queue drains each display to `all_text_parts` exactly once, in stream order (the bridge emits its terminal `_complete`/exc sentinel only after all prior queue events, so no display is lost or reordered even on a later-turn error). Two route-level regression tests assert persist-once, exact stream order, tool-executed, and SSE-wire-once for both loops (fail pre-fix `count==2`, pass post-fix). The finding's secondary `observe_chunk` double-count claim was inaccurate — `observe_chunk` only runs in the main-loop drains (never in the closures), so the display was already counted once; the fixer correctly made no `observe_chunk` change. | FIX-REREV-pi-full-20260720-w2-REVIEW-r1 (CF-190) | fixed (re-review passed L-31) |
| F-W2-INFO | Info | Observability | completion call sites | Real project ids should be threaded to the four previously migrated completion paths when those callers gain project scope. presentation.slides and the browse_website tool now thread a real project_id; context_dag/context_summarizer/ui_audit stay `""` where callers expose no project scope. | — | accepted-risk |

**Remediation:** `FIX-pi-full-20260720-w2-REVIEW-r1` (L-29) completed F-W2-1/F-W2-1a/F-W2-1b and the bounded L-30 delta re-review re-verified all three (ratchet 78 with a reconciling scanner; the legacy streaming + queue-bridge seam preserves per-token SSE, hallucinated-tool filtering, and the pre-tool `turn_separator`; the browser endpoint is `PiModelManager`-governed with a `tool.browse_website` ledger row and a documented scanner exemption). L-30 **failed** the wave because that same fix introduced F-W2-R1-1: the chat.py streaming routes double-append (and mis-order) the tool-result display into the persisted assistant transcript. F-W2-R1-1 was owned by `pi-full-20260720-w2-fixer` (`FIX-REREV-pi-full-20260720-w2-REVIEW-r1`, dispatched as CF-190). `CF-190` (L-31 fixer, `opus.4.8-xhigh`) closed it by deleting the direct `all_text_parts.append(result_display)` in both `_tool_exec` closures so the display flows solely through the queued `content` event drained once, in stream order, and by adding two persist-once/in-order route regression tests. The bounded **L-31 delta re-review passed**: the fix is correct and regression-free (137 pi_production/pi_migration + 43 candidate/W1-contract/ASGI tests green; the two new tests fail pre-fix and pass post-fix), the finding's secondary `observe_chunk` double-count claim was a non-issue (already counted once), and the only residual is pre-existing, non-fix-induced chat.py/bridge.py ruff debt (no finding task). The W2 review lineage (`pi-full-20260720-w2-REVIEW`) now has no open findings; W2 is ready for stage-exit acceptance.

## W3 — research spine + steering migration

### Review (W3) — Findings register

| ID | Sev | Dim | Where | Finding | CF task | Status |
|---|---|---|---|---|---|---|
| F-W3-INFO-1 | Info | Behavior-parity | `backend/app/core/agentic/legacy.py` `_react_loop` (L1 legacy path) | Legacy-path L1 outcome text aggregates intermediate assistant turn text where the old manual loop returned only the final turn content — dispatcher legacy-loop semantics, same as W2 chat; implementer-declared accepted risk. | — | accepted-risk |
| F-W3-INFO-2 | Info | Observability | `backend/app/core/agent_research.py` `_react_tool_executor` | Failed-JSON-parse tool-arg telemetry granularity lost: args arrive pre-parsed from the engine (bad JSON silently → `{}` in `_tool_call_parts`), so `record_json_parse` always records success. Behavior preserved; candidate polish for a later wave. | — | accepted-risk |
| F-W3-INFO-3 | Info | Docs | `tests/pi_migration/legacy_allowlist.yaml` | Section header comment still reads "Chat sites (69)" after the 8-entry removal — cosmetic. | — | accepted-risk |

**Review outcome:** `pi-full-20260720-w3-REVIEW` (L-33, claude-fable-5) **passed** with zero Blocker/Major findings — no fixer round required. All 8 W3 sites verified against the master plan's §8 W3 loop map (verbs, purposes, session strategies, spine-phase taxonomy, extra_tools allowlist enforcement, ratchet 78→70); 281 tests across the W3 contract, ratchet, wave-ladder, agents, steering, and integration suites green.

## W4 — A2A handlers migration

### Review (W4) — Findings register

| ID | Sev | Dim | Where | Finding | CF task | Status |
|---|---|---|---|---|---|---|
| F-W4-INFO-1 | Info | Behavior-parity | `backend/app/core/agent_lifecycle.py` `_handle_collaboration` | With RAG context present, the RAG message becomes `chat_turn` `user_text` and the current message rides in history; the assembled system+messages+user_text list is byte-identical to the legacy `llm_messages`, so model input is unchanged — only per-turn session bookkeeping labels differ. | — | accepted-risk |
| F-W4-INFO-2 | Info | Docs | `tests/pi_production/test_w4_a2a_handlers.py` docstring; IMPL evidence | The collaboration path is framed as purpose "a2a.collaboration", but `chat_turn` has no purpose kwarg and records `purpose=chat_turn`; the `a2a-collab:{context_id}` session_key is the actual distinguishing tag. Cosmetic. | — | accepted-risk |
| F-W4-INFO-3 | Info | Process | this file | The W4-IMPL ledger entry (step 5) was not appended by the implementer and the harness fallback has not landed (diff uncommitted at review time) — narrative gap for the conductor to reconcile, not a code defect. | — | accepted-risk |

**Review outcome:** `pi-full-20260720-w4-REVIEW` (L-34, claude-fable-5) **passed** with zero Blocker/Major findings — no fixer round required. All 3 W4 A2A sites verified against master plan §8 W4 (flag-gated dispatcher paths with the legacy branch preserved, verbs/purposes/sessions/spine phases, ratchet held at 70); 178 tests across the W4 contract, ratchet, pi_production, and A2A security/scope suites green in this pass.

## Summary (S5 — whole plan)

Pending completion of W0–W9 and B1–B4.
