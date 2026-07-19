# Pi Production-Test Readiness Review

```yaml
item: pi-production-readiness-review
branch: comparison/pi-replacement-core
cf: { spec: CF-SPEC-5, tasks: [] }
phase: "Phase 1 — literal BSC review and production-test readiness"
stage: S3-review
status: in-progress
blocked_on: null
last: { agent: gpt-5.6-terra, at: "2026-07-19T20:55:43Z", ledger: L-8 }
next_action: "Conductor: tally consensus plan votes and select the winning plan for execution."
```

## Plan overview

Review the existing opt-in Pi replacement candidate in the isolated replacement worktree,
prove the real route/service boundaries that can be exercised without production
credentials, remediate any findings through a role-separated Build Stream Conductor cast,
and leave an evidence-backed readiness classification.

Non-goals: production deployment, external channel sends, production data mutation, live
model loading without explicit authorization, commits, or claims of deployment readiness.

## Decision log

DEC-1 | 2026-07-19 | S1-plan | codex-main
Context: The prior round used an OpenClaw fallback because the conductor was launched from
the wrong nested runtime and its daemon was down.
Decision: Re-run the literal conductor from a clean login-shell path using a visible
Terminal.app watcher, after real one-shot CLI preflight and harness-symlink checks.
Why: This directly tests the documented failure mode before any fallback is considered.

## Ledger

### L-1 | 2026-07-19T17:38:36-03:00 | S1-plan | codex-main | planner | Phase 1
Did: Created CF-SPEC-5, clarified it with the isolated-worktree and credential-free
production-test boundary, planned it, and created the continuation lifecycle/run folder.
Verified: `compass-forge spec show CF-SPEC-5` reports `status: planned`; direct Codex
preflight probes for `gpt-5.6-terra` and `gpt-5.6-sol` exited 0; conductor preflight cache
reports `ok: true`.
Next: Generate a fresh run-scoped pipeline/cast and launch the visible conductor.

## Phase 1

### Frame and plan

Acceptance: the literal BSC cast starts from Terminal.app, reaches convergence or records
the exact command-level failure, and the final run preserves review findings, remediation,
tests, gates, raw-capture state, and credential/runtime blockers separately.

### Findings register

| ID | Sev | Dim | Where | Finding | CF task | Status |
|----|-----|-----|-------|---------|---------|--------|

### L-2 | 2026-07-19T20:48:39Z | S1-plan | gpt-5.6-terra | planner | pi-prod-readiness-20260719t173836-planner-b <!-- bsc-ledger:pi-prod-readiness-20260719t173836-PLAN-B -->
Did: pi-prod-readiness-20260719t173836-planner-b stage on task pi-prod-readiness-20260719t173836-PLAN-B (harness fallback entry; the model did not append one).
Result: task pi-prod-readiness-20260719t173836-PLAN-B finished; worktree head fa6a1a39.
Verified: see Compass Forge evidence rows on pi-prod-readiness-20260719t173836-PLAN-B (command + self_report + stage_attribution).
Next: conductor advances the pipeline on evidence.

### L-3 | 2026-07-19T20:48:57Z | S1-plan | gpt-5.6-terra | planner | pi-prod-readiness-20260719t173836-planner-a <!-- bsc-ledger:pi-prod-readiness-20260719t173836-PLAN-A -->
Did: pi-prod-readiness-20260719t173836-planner-a stage on task pi-prod-readiness-20260719t173836-PLAN-A (harness fallback entry; the model did not append one).
Result: task pi-prod-readiness-20260719t173836-PLAN-A finished; worktree head 1fad745a.
Verified: see Compass Forge evidence rows on pi-prod-readiness-20260719t173836-PLAN-A (command + self_report + stage_attribution).
Next: conductor advances the pipeline on evidence.

### L-4 | 2026-07-19T20:50:38Z | S1-plan | gpt-5.6-terra | planner | pi-prod-readiness-20260719t173836-planner-c <!-- bsc-ledger:pi-prod-readiness-20260719t173836-PLAN-C -->
Did: pi-prod-readiness-20260719t173836-planner-c stage on task pi-prod-readiness-20260719t173836-PLAN-C (harness fallback entry; the model did not append one).
Result: task pi-prod-readiness-20260719t173836-PLAN-C finished; worktree head ece54640.
Verified: see Compass Forge evidence rows on pi-prod-readiness-20260719t173836-PLAN-C (command + self_report + stage_attribution).
Next: conductor advances the pipeline on evidence.

### L-5 | 2026-07-19T20:53:22Z | S1-plan | gpt-5.6-terra | planner | pi-prod-readiness-20260719t173836-planner-a <!-- bsc-ledger:pi-prod-readiness-20260719t173836-REPLAN-A-r1 -->
Did: pi-prod-readiness-20260719t173836-planner-a stage on task pi-prod-readiness-20260719t173836-REPLAN-A-r1 (harness fallback entry; the model did not append one).
Result: task pi-prod-readiness-20260719t173836-REPLAN-A-r1 finished; worktree head 437b9831.
Verified: see Compass Forge evidence rows on pi-prod-readiness-20260719t173836-REPLAN-A-r1 (command + self_report + stage_attribution).
Next: conductor advances the pipeline on evidence.

### L-6 | 2026-07-19T20:54:00Z | S3-review | gpt-5.6-terra | reviewer | Phase 1 <!-- bsc-ledger:pi-prod-readiness-20260719t173836-JUDGE-A -->
Did: Compared the assigned Plan B and Plan C candidates without editing either plan.
Result: Voted for Plan C; it explicitly remediates direct accepted-artifact creation in the readiness probe and better preserves the governed Research Spine. Task pi-prod-readiness-20260719t173836-JUDGE-A.
Verified: `sed -n` review of `docs/build-stream/plans/pi-prod-readiness-20260719t173836-plan-b.md` and `docs/build-stream/plans/pi-prod-readiness-20260719t173836-plan-c.md` completed; Compass Forge command, plan_vote, and self_report evidence recorded.
Next: conductor tallies consensus votes and selects the execution plan; stage exit: consensus vote recorded.

### L-7 | 2026-07-19T20:56:00Z | S3-review | gpt-5.6-terra | reviewer | Phase 1 <!-- bsc-ledger:pi-prod-readiness-20260719t173836-JUDGE-C -->
Did: Compared the assigned Plan A and Plan B candidates without editing either plan.
Result: Voted for Plan A; it defines one selection predicate, a more explicit post-gate A2A telemetry matrix, and a concrete governed-research remediation path that distinguishes provisional fixtures from accepted/reportable artifacts. Task pi-prod-readiness-20260719t173836-JUDGE-C.
Verified: `sed -n` review of `docs/build-stream/plans/pi-prod-readiness-20260719t173836-plan-a.md` and `docs/build-stream/plans/pi-prod-readiness-20260719t173836-plan-b.md` completed; Compass Forge command, plan_vote, and self_report evidence recorded.
Next: conductor tallies consensus votes and selects the execution plan; stage exit: consensus vote recorded.

### L-8 | 2026-07-19T20:55:43Z | S3-review | gpt-5.6-terra | reviewer | Phase 1 <!-- bsc-ledger:pi-prod-readiness-20260719t173836-JUDGE-B -->
Did: Compared the assigned Plan A and Plan C candidates without editing either plan.
Result: Voted for Plan A because its phased task graph, acceptance-to-proof matrix, and security, feature-documentation, and gate verification sequence provide the stronger executable readiness contract. Task pi-prod-readiness-20260719t173836-JUDGE-B.
Verified: `sed -n` review of `docs/build-stream/plans/pi-prod-readiness-20260719t173836-plan-a.md` and `docs/build-stream/plans/pi-prod-readiness-20260719t173836-plan-c.md` completed; Compass Forge command, plan_vote, and self_report evidence recorded.
Next: conductor tallies consensus votes and selects the execution plan; stage exit: consensus vote recorded.
