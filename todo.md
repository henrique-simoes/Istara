# Istara — Post-Promotion Open Work (hand-off TODO)

Created 2026-09-12 by the releasing manager after the `testing` → `main` promotion.
Promoted as **`2f106b57`** (squash merge of PR #34, certified candidate `25e2063d` /
`9620e5d8`).

> **Instructions for agents**
> This file is the single hand-off list of open work created by the promotion. Work the
> sections **in order**; every item states its context, the exact command(s) or paths, and a
> "done when" condition. Record evidence (command + result) in the Build Stream lifecycle
> ledger (`docs/build-stream/2026-09-09-testing-to-main-convergence.md`) or the PR that closes
> the item — never mark an item done without evidence.
> Items marked **DONE** below were completed on 2026-09-12 by the releasing manager; do not
> redo them, but do spot-check their evidence.
> **Do not delete this file early.** When **every** item below is done **and verified**,
> delete `todo.md` in a small PR (`chore: close out post-promotion TODO`) and note the closure
> in the lifecycle ledger.

## 0. Status snapshot (context)

- Promotion: PR #34, **squash-merged** as `main` @ `2f106b57` (single owner-authored commit, no
  model co-authors). Certified SHA `25e2063d` (tree `e609049f`); pushed tip `9620e5d8`
  (tree-identical to `a1b3f443` plus the Docs Website conftest guard). Dossier:
  `docs/promotion/2026-09-09-promotion-certification.md`; ledger:
  `docs/build-stream/2026-09-09-testing-to-main-convergence.md` (L-1 … L-80).
- CI evidence: `34637179724` (17/17 on `a1b3f443`), QA Artifact `34637179623`, Docs Website
  `34643719560` (green on `9620e5d8`, L-80). Main CI runs on push (`Dependency Graph`,
  `Sync Staging with Main`, `Badge sync`).
- `main` protection: **17 required contexts**, strict, linear history, no force-push, no
  deletions, enforce-admins, **approvals 0** (solo-owner repo; GitHub forbids self-bypass on
  user-owned repos). Documented as an applied override in
  `docs/promotion/branch-protection/README.md`.
- `testing` branch is the promotion train; **keep it** (the promote workflow's anti-replay
  binds `source_sha` to `origin/testing`).

## 1. Repository hygiene

**DONE 1.1 — branch-protection deviation documented.** `docs/promotion/branch-protection/README.md`
now has an "Applied overrides (2026-09-12) — solo-owner repository" section explaining approvals
0 / no code-owner reviews, with the read-back command. *Follow-up (optional):* also align
`gh-api-body.json` field-by-field with the applied state.

**DONE 1.2 — conductor worktrees removed** (`git worktree remove --force` + `git worktree prune`):
`Istara-wt-readiness5-20260910` (1.1 G), `Istara-wt-main-readiness-20260909` (777 M),
`Istara-wt-debt-qa-20260828` (161 M), `/private/tmp/ci-sim`. Free space went **8.9 → 11 GiB**.
Kept intentionally: the Codex-managed worktree
`/Users/user/Documents/Codex/2026-08-10/list/work/istara-pi-linearized-2026-08-10`.
*Note:* the debt-qa worktree had one uncommitted `AGENTS.md` modification that was discarded
with the worktree; the committed branch content is intact (`conductor/debt-qa-20260828`).

**DONE 1.3 — 32 remote-backed local branches deleted.** Kept: `main`, `testing`, and four
**local-only** branches whose tips exist on no remote — decide their fate explicitly:
`conductor/debt-qa-20260828` (`e1df95a6`),
`conductor/istara-pi-model-management-migration-20260818` (`465e0cff`),
`conductor/istara-public-ci-testing-20260818` (`c198138c`),
`conductor/istara-testing-docker-20260817` (`2c142649`).
*Done when:* each of the four is either pushed as a backup ref, merged, or deleted after
confirming its commits are redundant.

**OPEN 1.4 — remote branch pruning is owner-gated.** Produce the obsolete `origin/*` list
(`backup/*`, `review/*`, `feat/*` merged long ago) for the owner to delete on GitHub; do not
delete remote branches without an explicit request.

**OPEN 1.5 — `git gc` in the main checkout.** Not run yet. Use a plain `git gc` (not
`--prune=now`): the cited certification SHAs `25e2063d` / `a1b3f443` are unreachable by ref and
only young-object retention keeps them locally. Verify afterwards with
`git cat-file -t 25e2063d`. Record before/after disk usage.

**OPEN 1.6 — stop the conductor watcher once nothing is left to watch.**
`kill "$(cat ~/.pi/agent/conductor-monitor/watch.pid)"` (PID-managed; the extension then goes
quiet). Restart with `~/.pi/agent/conductor-monitor/watch.py` when a new run starts.

## 2. Build Stream — stale status blocks

**DONE 2.1 — eight stale status blocks closed** as `closed-superseded` with dated reasons and
evidence pointers: `2026-07-19-pi-agentic-core-replacement`,
`2026-07-19-pi-production-readiness-review`, `2026-07-20-pi-full-replacement`,
`2026-08-17-istara-testing-docker-readiness`, `2026-08-18-istara-public-ci-testing-automation`,
`2026-08-18-istara-public-ci-testing-governance-closure`,
`2026-08-18-istara-public-ci-testing-governance-minimal`,
`plans/2026-07-20-pi-full-replacement-master-plan`.
*Note:* `plans/testing-to-main-20260909-plan-b.md` has no YAML status block (nothing to close).

**OPEN 2.2 — close the lifecycle record itself.** `docs/build-stream/2026-09-09-testing-to-main-convergence.md`
still reads `status: in-progress` / Phase 6 with an owner-action `next_action`. Now that the
promotion merged, set the final status (and the roadmap table rows) so that
`python scripts/verify_build_stream_status.py` passes: mark the last phase `done`, point
`next_action` at the merge and at this file, keep the ledger intact.
*Done when:* the verifier passes and the document no longer claims an in-progress phase.

## 3. Compass Forge — control-plane state

**DONE 3.1 — three orphaned claims released.** `CF-47` (claimant `glm-5.3-flash`),
`CF-113` (`opencode`), `CF-403` (`codex-independent-review-20260910`) were released to `open`
with an audit comment each ("Orphaned claim released during post-promotion closeout…").
`task list --status claimed` is now empty.
*Follow-up:* triage these three individually — close with `--status canceled` + reason if their
spec shipped, or leave open and re-dispatch.

**OPEN 3.2 — triage the 180+ open tasks.** They are the pre-promotion backlog, classified in
`docs/promotion/2026-09-09-control-plane-triage.tsv` (open, non-release-blocking). Per task: read
it, check whether its spec shipped (lifecycle ledger + `main` history); shipped →
`$COMPASS_FORGE_BIN task status <ref> canceled --actor <you>` with the evidence in a preceding
`task comment`; real work → keep open and add a line here. **Never bulk-close without per-task
evidence.** Regenerate the triage doc afterwards.
*Command reference:* `task status <ref> <open|claimed|blocked|done|canceled|ready>` (the status is
a positional, `--actor` is the only flag); `task release <ref> --actor <claimant>` clears a claim;
`task comment <ref> --actor <you> --body "…"` records the reason.
*Done when:* the open count reflects only genuinely-open work.

## 4. Owner-gated (do NOT perform without the owner)

- `docs/build-stream/2026-08-23-agentic-core-integrity-and-qa.md` — **blocked** on DashScope
  paid billing (or an equivalent third credential) and optional Petals donor inputs.
- `docs/build-stream/2026-09-08-benchmark-modernization-full-ui-suite.md` — live lanes are
  owner-gated (donors/models/third-party keys); the CF-SPEC-25 rich-corpus wiring is doable
  without them.
- `docs/build-stream/2026-09-08-pi-capability-inheritance.md` — F-19/F-25 badge-execution
  acceptance needs a live lane (owner-gated; L-41/L-42).
- Rule for all of the above: never start live backend/frontend servers, send chat-completion
  probes, or trigger model loading without explicit owner permission (`AGENTS.md`).

## 5. Queued owner asks (do after the hygiene/closure work)

- **R-1 — compare web UIs for the pi harness** (owner is tired of the TUI). Deliverable: a
  comparison of web UI options with capability parity, auth model, local-vs-hosted trade-offs,
  and effort, ending in a recommendation. Reminder entry: `artifacts/reminders.md`.
- **Long-horizon agentic engine** — `docs/build-stream/2026-09-08-agentic-long-horizon-improvement.md`
  (CF-SPEC-19 → CF-193…CF-202), using `docs/scientific_audit/agentic-engine-evaluation-log.md`
  as the pre-change baseline (2026-09-04 row; W3/W4 rows).

## 6. Riding advisories (non-blocking — close or waive deliberately)

- `F-CFR-1` — the recorded "16/17 green" for `15ef4835` is really 15/17 (`release-gate` also
  failed); `F-CFR-2` — G1/G3 lacked exact commands. Source: review L-79.
- `F-PTG-1/2/3` and the W2/W3/W4 minors — see `artifacts/review-20260910/` (findings register,
  reconciliation, verification matrix).
- Telemetry gaps from the W4 audit: **G1** legacy engine cost unmetered, **G2** token accounting
  compares input/output only, **G3**, **G5** harness-local tool spans.
- `registerPasskey` residual (frontend), if still reproducible.
*Done when:* each is fixed, or explicitly waived with a one-line reason in the ledger.

## 7. Key references

- SHAs: `main` `2f106b57`; promoted tip `9620e5d8`; certified `25e2063d`; pre-promotion `main`
  `fa6a1a39`.
- CI: `34637179724` (17/17 on `a1b3f443`), `34643719560` (Docs Website green on `9620e5d8`).
- Verification commands used by the release: `python scripts/check_feature_obligations.py`,
  `check_change_obligations.py`, `security_benchmark.py --fail-on-threshold`,
  `check_integrity.py`, `check_ci_governance.py`, `check_test_harness.py`,
  `check_required_checks.py`, `check_ruff_changed.py`, `check_public_tree_clean.py`.
