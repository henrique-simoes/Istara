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
last: { agent: claude-opus-5, at: 2026-09-09T15:00:20Z, ledger: L-3 }
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

### L-3 | 2026-09-09T15:00:20Z | S1-plan | claude-opus-5 | planner | Phase 0 — three-architect consensus planning <!-- bsc-ledger:testing-to-main-20260909-PLAN-B -->
Did: Drafted independent consensus architect plan B to `docs/build-stream/plans/testing-to-main-20260909-plan-b.md` (slot b, phase `draft`). Measured the candidate read-only rather than trusting the brief: git refs/divergence/worktree, ruff format + F821, the public-quality audit internals, `stryker.config.json` scope, all seven `ci.yml` jobs, `gh api` main branch protection, Compass Forge `index status` / `intelligence impact` / `task list` / `spec list`, and the wave-manifest hash. No code, CI, branch, or lifecycle-plan content changed.
Result: 19 findings (F-B01..F-B19: 6 S1, 6 S2, 5 S3, 3 S4) mapped onto the conductor's existing six wave IDs, plus CI target architecture, a 32-row verification matrix, Research Spine assurance, owner-gated operations, and a 12-line binary release verdict. Four brief claims did not survive measurement: (1) the forbidden phrase is the absolute checkout path, not the literal string `machine_checkout_path` — an implementer following the brief would find nothing and risk editing the working audit; (2) the CF index is NOT schema-stale — `index_version` 12 was written by the current Rust kernel with `warnings: []` and the graph answers at high confidence, while bare `impact` is `not_yet_native` and the working command is `intelligence impact --path`, so any "refresh until graph_usable" task is unexecutable; (3) open CF tasks number 181, not just CF-SPEC-29's; (4) the worktree drifted during analysis (4712 insertions/119 untracked vs the briefed 4706/118). Also proved the two F821s are real latent defects (`get_type_hints` raises `NameError`) that escaped because global lint is advisory while changed-file lint is blocking; that `qa-contract-stack` only runs `docker compose config` and never starts a container or a browser; and that the frontend mutation gate mutates a single 82-line file the candidate never modified, where 95/130 = 73.08% and only 3 more kills clear the threshold. Reconciled the wave-manifest hash mismatch as a documentation gap, not tampering: the pinned value matches canonical compact sorted JSON. $TASK = testing-to-main-20260909-PLAN-B.
Verified: `git rev-parse` / `rev-list --left-right --count` / `diff --shortstat` / `ls-files --others` (refs match brief exactly; `main` is a strict ancestor); `python -m ruff format --check backend/` → 15 files (brief confirmed); `python -m ruff check backend/ --select F821` → 2 errors + a `typing.get_type_hints` probe raising `NameError`; `pytest tests/test_public_repo_quality.py -q` → 1 failed, plus direct `audit()` inspection; `gh api repos/henrique-simoes/Istara/branches/main/protection` (only `governance` required, 0 approvals, `enforce_admins` false, force pushes allowed); `compass-forge index status` / `intelligence impact --path` / `task list --status open` / `spec list`; `shasum -a 256` vs a Python canonicalisation sweep over the wave manifest; and a self-check confirming this plan file trips no `GLOBAL_FORBIDDEN` phrase and has no trailing whitespace. 11 `command` evidence rows + `self_report` recorded on testing-to-main-20260909-PLAN-B. No servers, models, or providers were touched; nothing was reset, cleaned, or deleted.
Next: stage exit — draft complete and frozen for the `synthesize` phase; owner approval still required before any implementation wave.
