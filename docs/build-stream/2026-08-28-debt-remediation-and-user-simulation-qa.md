# Debt Remediation & User-Simulation QA — Build Stream lifecycle

```yaml
item: debt-remediation-and-user-simulation-qa
branch: testing
cf: { spec: CF-SPEC-6 }
phase: "Phase 1 — Wave A: branch quality debt remediation (adopted PLAN-A)"
stage: S2-execute
status: in-progress
blocked_on: null
last: { agent: glm-5.3-flash, at: 2026-08-28T21:00:00Z, ledger: L-3 }
next_action: "Execute Wave A change set 1: freeze behavior (pi-runtime npm ci in worktree, 122-test barrier green), then facade-split research_validity_service.py behind import-compatibility."
```

## Decision log addendum

```text
DEC-2 | 2026-08-28 | S1-plan | owner (via abort) + glm-5.3-flash
Context: The conductor three-architect MECE run was aborted by the owner —
insufficient usage credits across the multi-model cast (sol/opus/glm). Two of
three architect drafts had completed; PLAN-A (sol, xhigh→high) is a fully
evidenced, measured debt-remediation plan.
Decision: Abort the conductor run (daemon stopped, PLAN-B released, strict-wave
intent stays inert pending-approval with no execution authority). Adopt the
completed PLAN-A snapshot as the S1 plan for a REGULAR Build Stream execution:
single agent (glm-5.3-flash) drives CF work orders, gates, and evidence — no
additional model-CLI credits consumed. Wave B (user-simulation QA,
deterministic) and Wave C (live serving) unchanged in scope; Wave C still
pauses for the owner-supplied DashScope credential under owner-only custody.
Why: Preserves the owner's goals without multi-model spend; PLAN-A already
contains the measured current-state table (gate record 428, ruff 1651/772
safe-fixable, 208 files to format) and the four change-set structure with a
characterization-test barrier.
```

### PLAN-A adoption (S1 design, summarized)

Four reviewable change sets, zero product-behavior change, Research Spine
fail-closed invariants protected (`docs/architecture/research-validity-contract.md`):

1. **Freeze behavior.** `npm ci` in `pi-runtime` (worktree lacked node_modules;
   54 of 498 tests were handshake_timeout as a result). Barrier: focused
   W7/W8/settings suite — 122 tests green before any structural move.
2. **Facade-split `research_validity_service.py`** (2,762 lines) into cohesive
   internal modules behind import compatibility; decompose the flagged
   functions (`run_independent_coding_run` 63, `_pi_coder_runner` 39,
   `assess_task_research_validity` 31, `build_evidence_graph_traceability` 28,
   `_run_pi_coder_with_qwen_fallback` 23, `_resolve_application_unit` 28)
   without changing query order, commit points, telemetry order, serialized
   payloads, fallback bounds, or fail-closed decisions. Split the oversized
   test files by concern.
3. **Artifacts + Ruff debt in mechanically isolated diffs.** `git rm`
   `debug_rereview.py`, `fix_payload.py`; `git mv` w7/w8/w9 instructions and
   cf-spec-4..8 answers to `docs/build-stream/archive/`; `ruff format` backend
   (208 files) and safe-fixes only (never `--unsafe-fixes`); replace stale CI
   comments with measured counts; make steps blocking only when clean.
4. **Truthful gate state.** Fix the 8 new gate-comparison findings; explicit
   path/rule-scoped expiring suppressions for inherited findings that remain;
   never relabel inherited as new.

## Plan overview / roadmap

**Problem.** The `testing` branch is functionally healthy (first-ever green CI,
469 deterministic tests, security 100%) but carries accumulated quality debt:
complexity hotspots flagged by the architecture gate, committed root scratch
files, ~1159 lint errors and 146 unformatted files hidden behind
`continue-on-error`, and inherited gate findings without explicit dispositions.
Separately, the branch has never had a full user-simulation QA pass with the
serving stack up on the Mac Studio and live model credentials.

**Outcome.** Debt eliminated with zero product-behavior change (verified by the
deterministic suites), and a completed user-simulation campaign — Docker-only
Mac Studio serving stack, simulation suite, marathon, real-user benchmark
profiles — with every profile honestly reported (`accepted` /
`needs_reconciliation` / `not_runnable` / `blocked`).

**Goal / non-goals.**
- Goal: debt remediation (complexity, strays, lint/format, gate dispositions);
  comprehensive scenario-based user-simulation QA on the Mac Studio stack;
  live serving with owner-supplied credentials under owner-only custody.
- Non-goals: product behavior change in debt work, Research Spine methodology
  weakening, host installation on the Mac Studio, secrets in Git/argv/logs/
  images, fabricating live receipts.

**Appetite.** Three strict waves, conductor-driven (multi-model), each
independently reviewable; live wave starts only when the owner supplies the
API key.

**Acceptance criteria.**
- AC-1: Architecture-gate complexity findings on the touched debt files are
  fixed or carry explicit expiring suppressions with reasons. Verified by:
  `compass-forge gate after` diff showing no new fail/warn on those paths.
- AC-2: No committed scratch files remain at repo root
  (`debug_rereview.py`, `fix_payload.py`, `w7/w8/w9_instructions.md`,
  `cf-spec-4..8-answers.json` removed or archived with rationale). Verified by:
  `git ls-files` + `tests/test_public_repo_quality.py`.
- AC-3: CI lint/format steps are blocking or carry a documented debt-reduction
  trajectory with a bounded error count. Verified by: `.github/workflows/ci.yml`
  diff + green CI run.
- AC-4: Simulation suite, marathon, and benchmark provider profile run
  Docker-only on the Mac Studio from the pushed SHA; each profile reports a
  terminal status with retained receipts. Verified by: run scorecards +
  `research-spine-evidence.json` + runner logs.
- AC-5: Every phase leaves CF evidence rows, a gate pair, and a ledger entry;
  spec accepts only with all tasks done.

**Doc impact:** `TESTING.md` (if commands change), lifecycle file, findings
register here. **Rollback:** per-wave git revert; worktree isolation.
**Top risks:** refactor regressions (mitigated by full deterministic suite per
phase); live-model quota exhaustion (fail-closed receipts, owner decision);
conductor worker hangs (watchdog + fallbacks).

## Decision log

```text
DEC-1 | 2026-08-28 | S0-frame | owner
Context: Branch quality sweep found debt items and no full user-simulation QA
pass on the Mac Studio stack; owner wants both attacked via conductor MECE
planning.
Decision: New Build Stream plan under CF-SPEC-6 with three strict waves
(debt remediation; user-simulation QA deterministic; live serving acceptance),
conductor three-architect planning, and the owner's re-routed cast:
architect-a=pi openai/gpt-5.6-sol high; architect-b=claude claude-opus-5 xhigh;
architect-c=pi zai/glm-5.3-flash high; implementer=pi zai/glm-5.3-flash high;
code-reviewer=claude claude-opus-5 high; fixer=pi openai/gpt-5.6-sol high.
Why: Owner explicitly changed roles/models (authorized registry edit, routes
probe-verified live); strict waves keep each independently reviewable; API key
is prompted only when the live wave starts, under owner-only mode-600 custody.
```

## Ledger

### L-1 | 2026-08-28T19:35:00Z | S0-frame/S1-plan | glm-5.3-flash | framer | Phase 1
Did: Oriented via Compass Forge + Build Stream + conductor skills; presented
the routing registry; applied the owner's role/model changes to the repo
override (routing.py set ×6) and probe-verified all three new routes live
(`pong` × 3); classified the request (`security_or_architecture`, full blast);
created CF-SPEC-6, clarified it (quality: pass), planned it, generated 11
linked tasks; created this lifecycle file.
Result: Conductor scaffolding next; three-architect MECE planning pauses for
owner approval of the winning master plan.
Verified: `routing.py show --root` reflects the new routes; `pi`/`claude`
probes → pong; `compass-forge spec show CF-SPEC-6` → clarified/planned.
Next: write the strict-wave manifest, run make_pipeline + make_cast with
--with-planning, create the shared worktree, spawn the conductor.

### L-3 | 2026-08-28T21:00:00Z | S1-plan/S2-execute | glm-5.3-flash | planner | Phase 1
Did: Stopped the conductor daemon (SIGTERM on PID 21425, stop_requested ack'd),
released debt-qa-20260828-PLAN-B to open, verified the shared worktree clean;
recovered the completed PLAN-A draft from the consensus snapshots; logged
DEC-2 and adopted PLAN-A as the S1 plan for regular single-agent Build Stream
execution under CF-SPEC-6.
Result: Execution proceeds without further model-CLI spend. Wave C (live
serving) remains gated on the owner-supplied DashScope credential.
Verified: `pgrep conductor.py` → empty; `task release` → PLAN-B open;
`git -C worktree status --porcelain` → 0 lines; PLAN-A snapshot read and
summarized into this file.
Next: Wave A change set 1 — freeze behavior (pi-runtime npm ci, 122-test
barrier), then begin the facade split behind import compatibility.

### L-2 | 2026-08-28T20:00:00Z | S1-plan | glm-5.3-flash | planner | Phase 1
Did: Built the strict-wave scaffolding and launched the conductor. Wrote the
3-wave manifest (`debt-qa-20260828`: debt-remediation → user-simulation-qa →
live-serving-acceptance); ran `make_pipeline --with-planning --wave-manifest`
with the pinned native binary (planning tasks only, pending owner approval);
created the shared worktree `conductor/debt-qa-20260828`; ran `make_cast
--with-planning` from the re-routed registry. Fixed three environment defects
found on the way: (1) pi routes `openai/gpt-5.6-sol` to the API-key provider —
preflight failed closed; corrected to the OAuth-backed
`openai-codex/gpt-5.6-sol` (probe-verified) for architect-a/fixer; (2) the
pinned R2-native CF binary dropped the global `--workspace` option the
conductor's `cf()` helper still emitted for external workspaces — patched the
Skills-library `conductor.py` to rely on target/cwd config resolution (CF
resolves the `/Users/user/Documents/compass-forge` workspace pointer from
`--target` itself); (3) run-scoped actor roles must sit inside the recipe's
`[context.actor_roles]` TOML section — registered all six
`debt-qa-20260828-*` roles correctly and refreshed. Daemon then dispatched
architect-a (session 1, PLAN-A).
Result: Three-architect MECE planning running; conductor pauses at
AWAITING-OWNER-APPROVAL for the winning master plan.
Verified: `routing.py show` reflects the final cast; `pi`/`claude` probes →
pong ×4; `compass-forge actor roles` lists all six debt-qa-20260828 roles;
conductor.log tick shows active session 1 on PLAN-A with 0 dispatch errors.
Next: poll the conductor; present the synthesized winning plan to the owner;
on approval run `conductor.py approve` to release wave 1.
