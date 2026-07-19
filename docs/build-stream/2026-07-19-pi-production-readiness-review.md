# Pi Production-Test Readiness Review

```yaml
item: pi-production-readiness-review
branch: comparison/pi-replacement-core
cf: { spec: CF-SPEC-5, tasks: [] }
phase: "Phase 1 — literal BSC review and production-test readiness"
stage: S1-plan
status: in-progress
blocked_on: null
last: { agent: codex-main, at: "2026-07-19T17:38:36-03:00", ledger: L-1 }
next_action: "Generate the run-scoped CF pipeline and cast, then launch the literal conductor visibly."
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
