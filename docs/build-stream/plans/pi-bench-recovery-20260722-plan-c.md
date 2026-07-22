# Plan C — Pi benchmark recovery: reconcile pipeline state, re-validate and apply the role correction

- **Task:** `PI-BENCH-RECOVERY-20260722-PLAN-C` (consensus architect slot C, recovery run
  `PI-BENCH-RECOVERY-20260722`)
- **Spec:** CF-SPEC-8 · **Lifecycle:** `docs/build-stream/2026-07-22-pi-benchmark.md`
- **Authored:** 2026-07-22 against branch `Review_pi_test` @ `75db26f5` (post-L-34 state);
  every citation below verified by fresh grep/read/sqlite at that HEAD unless marked
  otherwise.
- **Scope:** documentation/planning-only recovery. No backend/frontend/tests/recipes/
  manifest/report edits, no benchmark execution, no live model calls, no spend. The
  master plan `docs/build-stream/plans/2026-07-20-pi-full-replacement-master-plan.md` is
  never touched.

---

## 1. Verified current state

### 1.1 Why the prior run is not a resumable execution state

The conductor's own tick record (`.compass-forge/conductor/conductor.log`, repeated
unchanged across ticks 3671–3690) states:

```
"consensus": {"pipeline_run": "PI-BENCH-ROLE-CORRECTION-20260722",
  "state": "halted-consensus-invalid-plan", "slot": "a",
  "reason": "governing PLAN/REPLAN artifact or attribution is invalid"}
```

The invalidity is structural, not a transient wedge — verified against CF state
(`.compass-forge/state.sqlite3`) and git:

1. **Incommensurable votes.** The three `plan_vote` rows were cast against *different
   candidate sets and revisions*: judge-a read plan-B r1 vs plan-C r0 (CF evidence 1405);
   judge-b read plan-A r1 vs plan-C r0 (1410); judge-c read plan-A r1→r2 *mid-stage* vs
   plan-B r1 (1428). No two judges evaluated the same frozen artifact pair, so the 2-1
   "slot a" tally is void as a governing decision even though slot a led.
2. **Governing artifacts not durable.** Slot C's plan was never committed
   (`docs/build-stream/plans/pi-bench-role-correction-20260722-plan-c.md` is untracked
   today); slot B's r1/r2 revisions exist only as *uncommitted* working-tree
   modifications (last commit on that file is r0, `b13b238c`). Judges voted on content
   that had no commit identity.
3. **Unterminated stage.** `PI-BENCH-ROLE-CORRECTION-20260722-REPLAN-C-r1` is still
   `claimed` in CF (claim from 19:39:07Z, has command+self_report evidence, never
   finished, no harness `stage_attribution`, no ledger entry).
4. **Ledger numbering races already observed.** The sequence jumps L-15 → L-17 (no
   L-16); plan A's r2 note records a dangling Status Block `ledger: L-30` reference and
   that its own entry landed as L-32 instead of the predicted L-30 — proof the Status
   Block cannot be trusted for numbering under concurrent writers.
5. **Orphan claimable surface.** `PI-BENCH-ROLE-CORRECTION-20260722-IMPL` and
   `-REVIEW` remain `open` (IMPL is `ready` per the conductor tick). Any future
   conductor pointed at the old prefix could "resume" the invalid pipeline.

### 1.2 The underlying defect is still present and still needs exactly one correction

The lifecycle still contradicts the user-authoritative role contract. Verified by my own
grep @ `75db26f5` (line numbers current):

| Region | Lines | Wrong text (verified) |
|---|---|---|
| §3 task table B0-3 | 307 | "Kimi-only evaluation adapter/preflight" |
| §3 task table B1…B_N | 312 | `--provider kimi --model <configured-kimi-model>` |
| §4 acceptance A3 / A4 / A7 | 327 / 330 / 339 | "Kimi evaluation credential", "configured Kimi evaluation provider/model", "uses Kimi only" |
| §5 verification commands | 374, 377, 385–386, 393 | `--provider kimi` in runner/ledger/preflight commands |
| §6 risk rows | 422, 424 | "Kimi evaluation API quota", "rejects non-Kimi evaluation configuration" |
| §8 owner gates G0 / G1 | 449, 452 | "authorizes Kimi-only …", "Kimi provider/model identity" |
| §9 non-goals | 465–466 | "non-Kimi evaluation provider routing", "Kimi evaluation `$1.00` envelope" |
| Decision log DEC-5 | 489 | "…and judge call through DeepSeek `deepseek-v4-pro`" |
| Decision log DEC-6 | 497 | "route every live benchmark evaluation call through the configured Kimi route/model" (+ open judge cast :499-500) |

Plan A r2's audit additionally lists the §2.1 diagram "resumable Kimi-evaluation slices"
at :202 (verified there by judge-a, CF 1404–1406; my battery did not pattern-match that
phrasing — the implementer's fresh battery in §6 must include it).

**Already correct — do not churn (verified):** Goals (:26-30); the wave/provider
contract (:35-57, incl. "All live Istara evaluation calls use the configured DeepSeek
provider/model through Istara's API/dispatcher … Kimi … disabled for this run. Post-run
judging is a separate BSC session using the intended Kimi judging harness" :50-53, and
the $1.00 cumulative envelope + judge-does-not-consume-budget rule :54-57); §2.2 design
principle 5. The execution work-order
`docs/build-stream/conductor-instructions/pi-benchmark-deepseek-moa-execution.md` is
role-correct (DUT=Istara, DeepSeek-only behind Istara :24-28; Kimi intended judge
:28-31, :74-77; judge must not rerun the DUT :31, :79; judging does not consume the
evaluation ledger :37-38) — but its evaluation-matrix pack list (:71-73) names only six
of the seven brief packs; MoA route/downgrade evidence appears only as a judge-scoring
dimension (:81).

### 1.3 Prior correction artifacts — inventory and reuse verdict

| Artifact | State @ 75db26f5 | Reuse verdict |
|---|---|---|
| `pi-bench-role-correction-20260722-plan-a.md` r2 (268 lines) | committed @ `1ff29c48` | **Reusable as the correction reference.** Triple-verified line anchors (r0/r1/r2), smallest surgical scope, all its load-bearing claims I re-verified still hold (§1.2). Its §7 debt row (deepseek_judge.py docstring/code declaring judge-shares-evaluation-ledger policy, :3-8/:84-90) remains valid follow-up debt. |
| `pi-bench-role-correction-20260722-plan-b.md` r2 (297 lines) | uncommitted working-tree edits on top of r0 commit | Content valuable (normative role block, terminal eval→judging barrier, requested-vs-served MoA provenance) but has no commit identity; **harvest ideas, do not execute from it.** |
| `pi-bench-role-correction-20260722-plan-c.md` r1 (347 lines) | untracked | As B: strong 16-region audit and full DEC-7 pre-specification to cross-check against; **not executable** (never durable, its REPLAN task never terminated). |
| The 2-1 judge tally (a/c/a→slot a) | CF `plan_vote` rows 1405/1410/1428 | **Void.** Cast on mixed revisions of non-committed artifacts (§1.1-1/2). Must not be reused as a consensus marker. |
| Ledger L-23…L-34 + findings register | committed | Append-only history. Keep byte-identical; supersede by new entries only. |

**Decision: reuse the *content* (correction intent, five-role target, audit tables,
verification battery), with plan A r2 as the primary reference cross-checked against
plan C r1's 16-region audit and plan B r2's role-block/barrier machinery. Do not reuse
the *consensus outcome*, do not resume the halted pipeline's tasks, and re-anchor every
citation at implementation HEAD before editing.** Authoring a fourth from-scratch
correction plan would add churn, not safety: three independent audits already converge
on the same surfaces, and my own grep confirms them at current HEAD.

### 1.4 Process / marker / worktree hazards to clear before implementation

Verified @ audit time:

- **One live conductor** for this recovery run: `conductor.py start --cast
  .compass-forge/conductor/recovery-cast.json` (PID 91892, started 16:55); its
  `active-run.json` matches that cast and prefix `PI-BENCH-RECOVERY-20260722`. This is
  the single-conductor invariant to preserve — the recovery cast serializes consensus
  (3 architects → 3 judges) then exactly one implement, one review, one fixer stage.
- **Stale marker duplicates** in `.compass-forge/conductor/`: `active-run (1).json`
  (points at `cast.json`, prefix `pi-full-20260720-w8`, recorded 05:39), `escalation
  (1).json`, `escalation (2).json` (w7-era). Leftover collision evidence; must be
  archived so only one active-run marker exists.
- **Uncommitted cast plumbing:** `recipes/istara-main-pi-replacement/recipe.toml`
  carries the conductor-generated `pi-bench-recovery-*` / `pi-bench-role-correction-*` /
  `pi-bench-moa-*` actor-role registrations (uncommitted). Required by the running
  cast; must NOT be swept into the docs-only correction commit. Disposition: ship stage
  or owner commits it separately (flagged, not silently left).
- **Untracked governing docs:** all three `docs/build-stream/conductor-instructions/*.md`
  (execution work-order, role-correction brief, recovery brief) are untracked — the
  correction would otherwise edit an uncommitted file.
- **Sibling writers right now:** recovery architects A/B/C write distinct plan files
  concurrently (by design); all lifecycle writes at implementation time must go through
  `repo_lock.completion_lock` + path-scoped commits.

## 2. Authoritative role canon (retained verbatim from the owner brief; the correction's target)

1. **DUT:** Istara itself — the original agentic loop vs the Pi adaptation on identical
   scenario inputs; captured behavior is compared.
2. **Evaluation backend:** every live DUT call traverses Istara's API/dispatcher on the
   configured DeepSeek API route under one cumulative `$1.00` cap; no direct DeepSeek
   calls as an Istara substitute; no Kimi/Claude/Codex/local/open-source DUT providers.
3. **MoA:** existing Istara dispatcher/validation + Research Spine behavior, measured
   observationally: requested-vs-served route identity, ensemble width, output
   processing, downgrade/degraded evidence. Production routing/defaults unchanged.
4. **Post-run judging:** after B0 and B1…B_N are terminal, a separate Build Stream
   Conductor session judges frozen artifacts; **Kimi is the intended judge
   harness/model**; it emits `report.md`, `report.html`, `scorecard.json`, and
   per-judgment outputs; it never reruns the DUT and does not consume the evaluation
   ledger.
5. **BSC implementation/review workers** are orchestration infrastructure, not DUT or
   judge evidence, unless explicitly cast in the post-run judging session.

## 3. Design

Five ordered steps; only RV-2 edits content, everything else reconciles state.
Historical ledger entries and DEC-5/DEC-6 text are never rewritten — supersession only.

- **RV-0 — Quarantine the halted run (conductor/owner, CF state only).** Release the
  stale claim and cancel the three halted-run tasks so no conductor can claim them, with
  a comment recording the reason. Archive the stale conductor markers (`active-run
  (1).json`, `escalation (1).json`, `escalation (2).json` → `*.stale-20260722`). Verify
  exactly one conductor process and one matching `active-run.json`.
- **RV-1 — Hygiene commit (docs only, one path-scoped commit).** Add the three untracked
  `docs/build-stream/conductor-instructions/*.md` and commit the halted run's plan-B r2
  working-tree content and untracked plan-C r1 **as-is** under a message marking them
  historical artifacts of the invalid run. Result: a clean tree under
  `docs/build-stream/**` so the correction diff in RV-2 is unambiguous and every edited
  file is tracked. `recipes/recipe.toml` is explicitly excluded (§1.4).
- **RV-2 — Role-language correction (one path-scoped commit, two files).** Re-anchored
  at implementation HEAD by the §6 battery (never by copying §1.2 line numbers):
  (a) lifecycle embedded winning-plan: identity-swap every Kimi-as-evaluation usage
  (§1.2 table + :202) to the DeepSeek evaluation route (`--provider deepseek --model
  deepseek-v4-pro`), keeping judge references pointed at the post-run Kimi BSC session;
  extend the wave-contract slice list (:42-43) with usage/cost accounting and MoA
  route/downgrade evidence so all seven packs are enumerated (keep `depth` as the mapped
  legacy label); append **DEC-7** (five-role canon of §2, superseding DEC-5's judge
  clause :489 and DEC-6's Kimi-evaluation clause/open cast :497-500) and add one-line
  `(superseded by DEC-7 …)` annotations under DEC-5/DEC-6; (b) work-order: add "MoA
  route/downgrade evidence" to the :71-73 pack list, add a pointer naming the
  role-correction brief as the authoritative role statement, and repeat the
  judge-does-not-consume-the-evaluation-ledger rule inside the role list. Preserve
  verbatim: `$1.00` cap, `max_processes=N`, immutable manifest, resumable B1…B_N,
  fail-closed rules, gates, non-goal structure.
- **RV-3 — Recovery reconciliation entry (append-only).** Append **DEC-8** recording:
  the halt (`halted-consensus-invalid-plan`), why the prior tally is void, what was
  reused (content) vs discarded (consensus marker, halted tasks), the single-conductor
  attestation from RV-0, and the owner gate required before any benchmark execution.
  Append the implementer's `### L-<n+1>` ledger entry under
  `repo_lock.completion_lock` (number taken from a fresh read of the last `### L-<n>`
  heading, never the Status Block), then refresh the Status Block (`stage`, `status`,
  `last:`, `next_action` → owner gate G-REC-1). Path-scoped commit of the lifecycle
  only.
- **RV-4 — Verification + independent delta review.** Run the full §6 battery, record
  CF command evidence; the recovery code-reviewer re-runs it on the commit and records a
  `review_verdict`.

The pre-existing deepseek_judge.py code/doc debt (judge shares the evaluation ledger;
docstring declares that policy) is **not** edited here — it becomes a NEW CF task
(`tests/pi_benchmark/` code scope) for a later owner-approved stage, exactly as plan A
r2's §7 prescribes.

## 4. Task breakdown

| # | Task | Files / surface | Actor | Depends |
|---|------|-----------------|-------|---------|
| RV-0 | Cancel halted-run tasks (release + status `canceled` + comment), archive stale markers, single-conductor attestation | CF state; `.compass-forge/conductor/` | conductor/owner | — |
| RV-1 | Hygiene commit of untracked governing docs + historical plan B/C | `docs/build-stream/**` only | implementer | RV-0 |
| RV-2 | Role-language correction + DEC-7 + work-order tighten | lifecycle + execution work-order | implementer | RV-1 |
| RV-3 | DEC-8 + ledger L-<n+1> + Status Block refresh, under completion lock | lifecycle | implementer | RV-2 |
| RV-4 | §6 battery as CF evidence; delta re-review | — | implementer → reviewer | RV-3 |

One implementer task (the already-open `PI-BENCH-RECOVERY-20260722-IMPL`) carries
RV-1…RV-4; RV-0 is a conductor/owner precondition recorded as CF comment evidence on
that task.

## 5. Acceptance criteria

- **AC-1** Zero Kimi-in-evaluation-provider-role and zero DeepSeek-in-judge-role
  occurrences in active lifecycle/work-order text; hits remain only inside `### L-`
  history and the annotated DEC-5/DEC-6 quotes (machine battery §6).
- **AC-2** Lifecycle (wave contract + DEC-7) and work-order both state the §2 five-role
  canon, and both enumerate all seven packs: canonical 15-scenario contract coverage,
  feature breadth, Research Spine lifecycle, A2A collaboration, prompt/injection probes,
  usage/cost accounting, MoA route/downgrade evidence.
- **AC-3** Invariants textually preserved: `budget_cap_usd=1.00`, `max_processes=N`,
  immutable manifest, resumable B1…B_N, fail-closed rules, owner gates, production
  model-selection behavior.
- **AC-4** RV-1/RV-2 diffs touch only `docs/build-stream/**`; no backend/, frontend/,
  tests/, recipes/, comparison-Istara-pi/ path in either commit; historical `### L-*`
  regions byte-identical (diff-audit vs pre-RV-2 commit).
- **AC-5** DEC-7 (supersession) and DEC-8 (recovery disposition + single-conductor
  attestation) present; one new ledger entry; Status Block coherent with the last
  `### L-<n>` heading.
- **AC-6** The three halted-run tasks read `canceled` in CF; exactly one conductor
  process, one `active-run.json` matching `recovery-cast.json`; no `* (1).json` markers
  remain unarchived.
- **AC-7** No live call, no spend, no benchmark execution, no server start — the
  correction is provably docs/state-only (`git diff --name-only` + process check).

## 6. Verification (exact commands)

Run from the project root `/Users/user/Documents/Istara-main-pi-replacement`.

```bash
# --- RV-0 state quarantine (conductor/owner; CF commands run from root) ---
compass-forge task release PI-BENCH-ROLE-CORRECTION-20260722-REPLAN-C-r1
compass-forge task status  PI-BENCH-ROLE-CORRECTION-20260722-REPLAN-C-r1 canceled
compass-forge task status  PI-BENCH-ROLE-CORRECTION-20260722-IMPL      canceled
compass-forge task status  PI-BENCH-ROLE-CORRECTION-20260722-REVIEW    canceled
compass-forge task comment PI-BENCH-ROLE-CORRECTION-20260722-IMPL \
  "Superseded: halted-consensus-invalid-plan; recovery run PI-BENCH-RECOVERY-20260722 owns the correction (DEC-8)."
mv ".compass-forge/conductor/active-run (1).json"  ".compass-forge/conductor/active-run-1.stale-20260722.json"
mv ".compass-forge/conductor/escalation (1).json"  ".compass-forge/conductor/escalation-1.stale-20260722.json"
mv ".compass-forge/conductor/escalation (2).json"  ".compass-forge/conductor/escalation-2.stale-20260722.json"

# AC-6 single-conductor attestation
ps aux | grep -E 'conductor\.py start' | grep -v grep            # expect exactly one line, recovery-cast.json
cat .compass-forge/conductor/active-run.json                     # cast_path == recovery-cast.json, prefix == PI-BENCH-RECOVERY-20260722
ls .compass-forge/conductor/ | grep -E '\(1\)|\(2\)' && echo "STALE MARKER" || echo "markers clean"
python3 -c "
import sqlite3; db=sqlite3.connect('.compass-forge/state.sqlite3')
print(db.execute(\"SELECT public_id,status FROM tasks WHERE public_id LIKE 'PI-BENCH-ROLE-CORRECTION%' AND status IN ('open','claimed')\").fetchall())"
# expect: []

# --- pre-RV-2 freshness battery (re-anchor; every edit uses match text, not line numbers) ---
grep -n -iE 'provider kimi|--provider kimi|kimi[- ]only (benchmark )?evaluation|kimi evaluation (credential|provider|api|envelope|adapter)|non-kimi evaluation|configured-kimi-model|kimi[- ]evaluation slices|uses kimi only|authorizes kimi|kimi provider/model identity|kimi route/model|judge call through deepseek' \
  docs/build-stream/2026-07-22-pi-benchmark.md
#   ^ must reproduce the §1.2 table + :202 before editing; after RV-2 the same battery
#     must produce ZERO hits outside ### L- history and the annotated DEC-5/DEC-6 quotes.

# --- hygiene + scope (AC-4, AC-7) ---
git diff --check
git status --porcelain -- backend frontend tests recipes comparison-Istara-pi   # expect: only the pre-existing recipe.toml row, never staged
git show --name-only --format= HEAD | grep -v '^docs/build-stream/' && echo "SCOPE VIOLATION" || echo "scope ok"
git diff HEAD~1 HEAD -- docs/build-stream/2026-07-22-pi-benchmark.md | grep -E '^[+-]### L-' \
  && echo "LEDGER HISTORY TOUCHED" || echo "ledger history intact"

# --- content acceptance (AC-1..AC-3, AC-5) ---
for f in docs/build-stream/2026-07-22-pi-benchmark.md \
         docs/build-stream/conductor-instructions/pi-benchmark-deepseek-moa-execution.md; do
  for p in canonical feature "Research Spine" A2A probe usage downgrade; do
    grep -qi "$p" "$f" || echo "MISSING pack '$p' in $f"; done; done   # expect: silence
grep -n 'budget_cap_usd=1.00\|max_processes\|immutable' docs/build-stream/2026-07-22-pi-benchmark.md | head
grep -n 'DEC-7\|DEC-8\|superseded by DEC-7' docs/build-stream/2026-07-22-pi-benchmark.md

# --- docs-only change must not alter the suite: record count BEFORE RV-2, compare after ---
backend/.venv/bin/python -m pytest tests/pi_benchmark/ -q    # identical pass/fail counts both runs
```

## 7. Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Stale anchors: §1.2 line numbers drift before RV-2 (sibling commits land) | Medium | Fresh-anchor rule: implementer re-runs the §6 battery at HEAD and edits by matched text; any region that no longer matches is a stop-and-report, not an improvisation. |
| Reusing the void tally or resuming halted tasks | Low | AC-6 cancels the claimable surface; DEC-8 records the tally as void; plan explicitly forbids reuse (§1.3). |
| Ledger numbering race during RV-3 (observed L-16 gap, dangling L-30) | Medium | `repo_lock.completion_lock` around read-append-commit; number from the last `### L-<n>` heading re-read under the lock; path-scoped `repo_lock.commit_paths`; never `git add -A`. |
| recipe.toml cast plumbing swept into the docs commit, breaking AC-4 | Medium | RV-1/RV-2 stage explicit paths only; §6 scope audit greps the commit, not the dirty tree; recipe.toml disposition left to ship stage/owner. |
| Over-correction of already-correct regions (:26-57, work-order roles) | Low | §1.2 keep-list is verified; RV-2 is an identity swap plus the enumerated additions only; reviewer checks the diff is role-identity + pack/pointer/DEC text, nothing else. |
| grep battery false positives from historical ledger text (e.g. L-18 "DeepSeek judge") | Medium | AC-1 scopes hits to non-`### L-` regions by hunk inspection; history is declared exempt. |
| Second conductor started later against the old prefix | Low | RV-0 cancellation + archived duplicate markers + DEC-8 note; owner gate G-REC-1 requires the attestation output. |
| deepseek_judge.py code/doc contradiction left silently | High (it persists) | Not edited here (code out of scope); recorded as residual risk in DEC-8 and raised as a NEW CF task before any live run. |

## 8. Rollback

- RV-1/RV-2/RV-3 are discrete docs-only commits: `git revert <sha>` (reverse order)
  restores prior text exactly. Appended DEC-7/DEC-8/ledger entries remain as history per
  append-only discipline; a revert is itself recorded by a further decision entry.
- RV-0 CF cancellations are reversible (`compass-forge task status <id> open`); archived
  markers are renames, restorable by the inverse `mv`.
- No code, config, data, credential, or spend state is touched, so no other rollback
  surface exists.

## 9. Owner gates (blocking, in order)

- **G-REC-0 (met by this consensus + owner sign-off):** owner approves the winning
  recovery plan; RV-0 attestation shows one conductor, one active-run marker, halted-run
  tasks canceled. No implementation before this.
- **G-REC-1 (before ANY benchmark execution task is created):** owner reviews the
  corrected lifecycle + DEC-7/DEC-8 and declares it the valid resumable execution state
  — the declaration the halted run never had. Only then may B0 live preflight proceed
  under the lifecycle's pre-existing **G0** (DeepSeek credential, `$1.00` envelope) and
  **G1** (recorded `N`, provider identity, ledger closed).
- **G-JUDGE (unchanged, post-B_N):** separate BSC judging session over frozen artifacts,
  Kimi judge harness/model, no DUT rerun, no evaluation-ledger draw.

## 10. Explicit non-goals

- No edit to the master plan, backend/, frontend/, `tests/` (incl. `deepseek_judge.py`),
  recipes/, manifests, `comparison-Istara-pi/`, or any report.
- No rewriting of historical ledger entries or deletion of DEC-5/DEC-6 text.
- No reuse of the halted run's 2-1 tally, its open tasks, or its uncommitted artifacts
  as governing state.
- No live model calls, no DeepSeek/Kimi invocation, no B0/B1…B_N execution, no spend.
- No production Istara routing, model-selection, or default changes.
