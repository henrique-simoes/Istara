# Build Stream — Testing to Main Convergence

<!-- STATUS BLOCK -->
```yaml
item: testing-to-main-convergence
branch: testing
cf: { spec: CF-SPEC-30, tasks: [] }
phase: "Phase 0 — three-architect consensus planning"
stage: S1-plan
status: in-progress
blocked_on: owner approval after consensus winner
last: { agent: codex, at: 2026-09-09T00:00:00-03:00, ledger: L-1 }
next_action: "Run the three-architect consensus pipeline and present the frozen MECE winner for owner approval."
```
<!-- /STATUS BLOCK -->

## Plan overview (roadmap)

This initiative converts the ambiguous, red, and partially dirty `testing` state into one
immutable candidate that can be proposed to `main` only after architecture, lifecycle, CI,
security, mutation, and real-browser evidence converge. The strict wave manifest is
`.compass-forge/conductor/testing-to-main-20260909-waves.json`. Implementation is owner-gated.

| Phase | Goal (one line) | Acceptance / verify | Status |
|-------|-----------------|---------------------|--------|
| 0 | Three independent architects produce, synthesize, and cross-vote a MECE master plan | conductor consensus reaches `AWAITING-OWNER-APPROVAL` | in-progress |
| 1 | Freeze and reconcile the candidate boundary | exact candidate SHA and worktree disposition | planned |
| 2 | Reconcile lifecycle and Compass Forge control-plane truth | fresh index, linked evidence, no hidden release blocker | planned |
| 3 | Repair correctness and quality failures | credential-free release checks green | planned |
| 4 | Align CI and branch-protection enforcement | required checks match architecture | planned |
| 5 | Prove real container-first behavior | dated journey verdicts on candidate SHA | planned |
| 6 | Certify promotion readiness | binary owner-gated promotion dossier | planned |

## Decision log

DEC-1 | 2026-09-09 | S1 | owner pending
Context: testing is substantially ahead of main but has divergent local work, red CI, contradictory lifecycle state, stale CF indexing, and under-protective main branch settings.
Decision: Pending the three-architect MECE consensus and owner approval; no implementation, push, PR, merge, live model loading, or destructive cleanup is authorized by this planning run.
Why: Independent architectural plans are required before selecting the implementation sequence for a cross-cutting release and CI redesign.

## Ledger

### L-1 | 2026-09-09T00:00:00-03:00 | S1-plan | codex | planner | Phase 0
Did: Created the strict-wave manifest and prepared the exact shared architect brief for three independent planning workers. Architect A is routed to Codex gpt-5.6-sol at low effort for this run; implementation remains behind owner approval.
Result: Planning run is ready to dispatch; no product or branch mutation has been performed.
Verified: Native Rust Compass Forge identity and conductor routing inspected; no live servers, models, or providers started.
Next: Dispatch three architect drafts, synthesize MECE master candidates, cross-vote, and stop at the human approval gate.

## Phase 0 — Three-architect consensus planning

The exact brief sent to each architect is held outside the repository at
`/tmp/istara-final-testing-to-main-architect-prompt.md` to avoid polluting the public-quality
scan with diagnostic text. The conductor will freeze the three drafts, synthesize one MECE
candidate per architect, run cross-votes, and stop before implementation.

## Phase 1 — Freeze and reconcile the testing release candidate

Reserved for the owner-approved winning plan.

## Phase 2 — Reconcile Build Stream and Compass Forge lifecycle truth

Reserved for the owner-approved winning plan.

## Phase 3 — Repair correctness, formatting, lint, public quality, and mutation gaps

Reserved for the owner-approved winning plan.

## Phase 4 — Align CI and main protection with the changed architecture

Reserved for the owner-approved winning plan.

## Phase 5 — Prove changed behavior through real container-first journeys

Reserved for the owner-approved winning plan.

## Phase 6 — Certify one exact SHA for owner-gated promotion

Reserved for the owner-approved winning plan.

### L-2 | 2026-09-09T14:55:13Z | S1-plan | gpt-5.6-sol | planner | testing-to-main-20260909-architect-a <!-- bsc-ledger:testing-to-main-20260909-PLAN-A -->
Did: testing-to-main-20260909-architect-a stage on task testing-to-main-20260909-PLAN-A (harness fallback entry; the model did not append one).
Result: task testing-to-main-20260909-PLAN-A finished; worktree head 85f64e4d.
Verified: see Compass Forge evidence rows on testing-to-main-20260909-PLAN-A (command + self_report + stage_attribution).
Next: conductor advances the pipeline on evidence.
