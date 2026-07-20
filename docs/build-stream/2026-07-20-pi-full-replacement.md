# Build Stream — Full Pi Replacement of Istara's Agentic Loop and Model Management

<!-- STATUS BLOCK -->
```yaml
item: pi-full-replacement
branch: Review_pi_test
cf: { spec: CF-SPEC-8, tasks: [pi-full-20260720-w0-IMPL, pi-full-20260720-w0-REVIEW] }
phase: "W0 — hardening and evidence integrity"
stage: S4-remediate
status: in-progress
blocked_on: null
last: { agent: gpt-5.6-sol, at: 2026-07-20T17:11:55Z, ledger: L-4 }
next_action: "Complete FIX-pi-full-20260720-w0-REVIEW-r1, then delta re-review every F-1 through F-4 seam."
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
| W2 | Migrate nine interactive surfaces | allowlist 78 + B1 T0/T1 + wave ladder | planned |
| W3 | Migrate eight research-spine and steering sites | allowlist 70 + wave ladder | planned |
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

## W0 — hardening and evidence integrity

**Frame/Plan:** Master plan §6 plus §12.2. Arm the deterministic inventory/ratchet before
further migration, correct the CF-SPEC-7 historical claim append-only, and implement H-1
through H-14 with named regression tests. Preserve Petals/donor isolation.

**Execution:** Pending conductor.

### Review (W0) — Findings register

| ID | Sev | Dim | Where | Finding | CF task | Status |
|---|---|---|---|---|---|---|
| F-1 | Blocker | Product | `scripts/pi_migration_inventory.py`; `tests/pi_migration/` | M0 inventory scanner, complete 87-site plus permanent-infrastructure allowlist, count-to-zero ratchet, and e2e ladder registration are absent. | FIX-pi-full-20260720-w0-REVIEW-r1 | open |
| F-2 | Blocker | Bugs | `backend/app/core/pi_runtime/`; `pi-runtime/` | H-1/H-2/H-4–H-8/H-11/H-12 are unimplemented; H-3 lacks named race/stale-frame tests; H-9 is partial; H-10 lacks its audit row and compromised-worker test. | FIX-pi-full-20260720-w0-REVIEW-r1 | open |
| F-3 | Blocker | Integration | `tests/pi_production/`; `docs/build-stream/2026-07-20-pi-production-runtime-completion.md` | H-13 real-ASGI tests and append-only CF-SPEC-7 correction are absent; H-14 lacks `PI_REQUIRE_NODE` fail-loud enforcement. | FIX-pi-full-20260720-w0-REVIEW-r1 | open |
| F-4 | Major | Plan | master plan §8.6; W0 evidence/docs | Living docs, full deterministic ladder, completion decision/evidence are absent, and literal `node --test pi-runtime/test` is invalid; use the verified package test entrypoint. | FIX-pi-full-20260720-w0-REVIEW-r1 | open |

**Remediation:** `FIX-pi-full-20260720-w0-REVIEW-r1` is open; one coupled fixer owns F-1–F-4 because the runtime changes, named tests, ratchet, docs, and final ladder form W0's atomic exit contract.

**Phase summary:** Pending.

## Summary (S5 — whole plan)

Pending completion of W0–W9 and B1–B4.
