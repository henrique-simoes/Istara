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
last: { agent: zai/glm-5.3-flash, at: 2026-09-09T15:22:44Z, ledger: L-7 }
next_action: "All three master candidates synthesized (a/b/c). Run the cross-vote, then stop at the owner-approval gate before W1 candidate-boundary."
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

### L-4 | 2026-09-09T15:04:57Z | S1-plan | zai/glm-5.3-flash | architect | draft <!-- bsc-ledger:testing-to-main-20260909-PLAN-C -->
Did: Wrote the independent architect-C draft plan to docs/build-stream/plans/testing-to-main-20260909-plan-c.md (350 lines): candidate verdict (surface C selected — untracked tokenStore/SeeMoreList/ToolAuditTrailTable are imported by modified tracked files, so surface B cannot typecheck/build), C1–C6 classification protocol with quarantine branch and drift-prevention rules, findings register F-C-01..F-C-21, 8 waves W0–W7 mapped onto the conductor manifest, CI target architecture with required-check manifest, 22-row verification matrix, Research Spine assurance, owner-gated operations, and binary READY criteria.
Result: Planning-only artifact; no product code, branch state, threshold, or lifecycle plan content edited. Read-only evidence reproduced: 64 commits ahead of origin/testing, 155 modified/119 untracked files, 15 ruff-format files (pin drift 0.16.4 local vs 0.16.6 CI via >=0.8.0 floor), ChatModelControls.tsx:20 no-empty-object-type, public-quality audit 2 findings (machine checkout path in AGENTS.md:142 and pi-capability-inheritance.md), 295 whitespace findings vs origin/main, CI 34039897688 red (frontend mutation 73.08 < 75; backend Format check; full pytest step never ran), main protection = [governance]/0 reviews/enforce-admins off/force-push allowed, CF: 181 open tasks incl. CF-SPEC-29×13 blocking SC-002, CF impact/graph not_yet_native.
Verified: six credential-free governance checks + security_benchmark --fail-on-threshold all exit 0 on the working candidate; refs/divergence/lint/audit/whitespace commands re-run by this architect; task evidence rows (2 command + 1 self_report) attached; plan file leak-checked against public_repo_quality GLOBAL_FORBIDDEN (0 hits).
Next: Conductor freezes the three drafts, runs synthesize, then cross-vote; owner-approval gate precedes W0.

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

### L-5 | 2026-09-09T15:14:04Z | S1-plan | gpt-5.6-sol | planner | testing-to-main-20260909-architect-a <!-- bsc-ledger:testing-to-main-20260909-MASTER-A -->
Did: testing-to-main-20260909-architect-a stage on task testing-to-main-20260909-MASTER-A (harness fallback entry; the model did not append one).
Result: task testing-to-main-20260909-MASTER-A finished; worktree head 50c4d493.
Verified: see Compass Forge evidence rows on testing-to-main-20260909-MASTER-A (command + self_report + stage_attribution).
Next: conductor advances the pipeline on evidence.

### L-6 | 2026-09-09T15:20:19Z | S1-plan | claude-opus-5 | planner | Phase 0 — three-architect consensus planning <!-- bsc-ledger:testing-to-main-20260909-MASTER-B -->
Did: Synthesized one MECE master plan from all three immutable draft snapshots (a: gpt-5.6-sol-low, b: claude-opus-5-high, c: zai/glm-5.3-flash-max) into `docs/build-stream/plans/testing-to-main-20260909-master-b.md` (1006 lines). Read every snapshot in full, then re-measured the four facts on which the drafts materially disagreed rather than averaging them. Corrected M-08 in-flight after finding this lifecycle file had been committed mid-planning (3bdea267). No product code, branch state, lifecycle plan, or threshold was touched.
Result: Master candidate for slot `b`, task testing-to-main-20260909-MASTER-B. Unified register: 24 findings (8×S1, 8×S2, 7×S3, 1×S4) deduplicated across the drafts, each attributed to its source. Four cross-draft conflicts adjudicated by measurement — K-1: draft c is right that local-committed `testing` is unbuildable, and understated it (22 tracked-modified files import untracked `@/lib/tokenStore`, not 8), so the candidate must include classified untracked files and dependency closure becomes a W1 acceptance test. K-2: draft a's "233 blocking frontend lint errors" is an artifact — 232 of them live in a leftover `.stryker-tmp/sandbox-2OnHq3` created today at 11:12; the real product count is 1, a ~200x scoping correction, and the trap itself is filed as new finding M-16 (gitignored but not eslint-ignored). K-3: the brief's blocker #4 is false and drafts a and c each inherited an unexecutable wave — bare `impact` is `not_yet_native` but `intelligence impact --path` works (confidence high, tree-sitter, graph_version 2), and `index_version 12` is what the current Rust kernel writes, so no schema-21 refresh target exists. K-4: draft b's root cause (`machine_checkout_path` is the rule name, not the literal) composes with draft c's leak sites, neutralizing the brief's highest-risk misdirection. Draft c's four-way wave split preserved as internal W3a/W3b and W4a/W4b phase boundaries without breaking the conductor's six manifest ids. Escalated `governance` direct-push-to-main from S4 to S2 blocking-before-W4b, since branch protection will break it.
Verified: `git grep -l tokenStore HEAD -- frontend/src` empty + 22 worktree importers; `npm run lint` 233 errors attributed by file (232 in sandbox, 1 real); `compass-forge intelligence impact --path` and `index status` via the pinned native binary from repo root; `public_repo_quality_audit.audit()` 2 findings (unchanged by me); `ruff>=0.8.0` floating pin and `ci.yml:87 git push origin HEAD:main` confirmed; plan file self-compliance `grep -c /Users/user` = 0 and GLOBAL_FORBIDDEN scan NONE. Five `command` evidence rows plus `self_report` recorded on testing-to-main-20260909-MASTER-B.
Next: stage exit — synthesis complete. Awaits the cross-vote phase (architects vote on the two master candidates they did not author), then the owner-approval gate before W1.

### L-7 | 2026-09-09T15:22:44Z | S1-plan | zai/glm-5.3-flash | architect | synthesize <!-- bsc-ledger:testing-to-main-20260909-MASTER-C -->
Did: Read all three frozen architect snapshots in full and wrote the MECE master plan to docs/build-stream/plans/testing-to-main-20260909-master-c.md (480 lines): candidate definition (surface C selected = local commits plus classified working tree; two-stage Candidate-Base/Promotion-SHA freeze), merged 25-finding register (M-01..M-25), 8-wave manifest keyed to the conductor's 6 wave IDs, CI target architecture with a committed required-checks manifest, 30-row verification matrix, Research Spine assurance (corpus include-then-scan), owner-gated operations, and binary release criteria with stage separation. Arbitrated every cross-draft conflict with fresh read-only measurements (K1..K8).
Result: testing-to-main-20260909-MASTER-C synthesis complete; master candidate c ready for cross-vote; no code, branch, threshold, or lifecycle-plan content changed.
Verified: artifact self-check clean (0 machine-local paths, 0 trailing whitespace; public-quality audit shows only the 2 pre-existing findings); measured-state re-confirmation (refs unchanged; HEAD 85f64e4d->50c4d493 explained as the three draft-plan commits; 155 modified / +4712/-977 / 119 untracked / 17 untracked lifecycle files / 295 whitespace findings); eslint arbitration (233 reported errors are .stryker-tmp sandbox contamination; source tree has exactly 1 error at ChatModelControls.tsx:20); CF arbitration (bare impact/graph not_yet_native; intelligence impact --path returns tree-sitter/high; index_version 12 is current Rust output with warnings []); CF evidence rows 1761-1765 + self_report recorded on testing-to-main-20260909-MASTER-C.
Next: cross-vote phase — vote on the two other master candidates; stop at the owner-approval gate before W1 candidate-boundary.
