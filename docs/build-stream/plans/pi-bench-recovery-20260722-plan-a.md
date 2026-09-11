# Plan A — Pi benchmark recovery after invalid role-correction consensus

- **Task:** `PI-BENCH-RECOVERY-20260722-REPLAN-A-r2` (consensus architect slot A,
  revision r2 — supersedes r1 (`…-REPLAN-A-r1`) and r0 (`…-PLAN-A`);
  pipeline `PI-BENCH-RECOVERY-20260722`)
- **Spec:** CF-SPEC-8 · **Lifecycle:** `docs/build-stream/2026-07-22-pi-benchmark.md`
- **Brief (verbatim source):** `docs/build-stream/conductor-instructions/pi-benchmark-recovery-planning.md`
- **Authored:** 2026-07-22 (r2), against branch `Review_pi_test` @ `c53e0d01`
  (r0 audited at `75db26f5`, r1 at `9c45a42a`; every prior grounding claim
  re-verified at `c53e0d01`)
- **Scope:** planning only. This plan proposes; it edits nothing besides this file.
  The implementation it proposes is documentation + orchestration-state hygiene only —
  no backend, frontend, benchmark Python, tests, recipes, manifests, or reports.

> **r2 revision note (conductor-created repair round).** Every §1 claim was re-verified
> by fresh commands at `c53e0d01` (CF command evidence on this task); no r1 factual
> errors found. Post-r1 drift folded in:
> (1) **All three recovery candidates are now committed** — plan C landed at `02595094`
> (task `…-PLAN-C` `done`, harness fallback ledger L-38 at `ac6ec4bd`), joining A
> (`9c45a42a`/`68dcd159`) and B (`9cfe3304`). The "judges read uncommitted plan files"
> risk is fully retired for this pipeline; only AC-1's blob-sha discipline remains
> load-bearing. (2) The lifecycle append-only protection range is now **L-1..L-39+**
> (judge-a's L-39 at `c53e0d01`; judge-b's L-40 landed while this r2 was being
> authored) — AC-2 now defines the protected range as *every ledger entry existing at
> IMPL dispatch time*, not a frozen number. (3) **Recovery judging has started**: CF
> `plan_vote` rows now exist — judge-a → slot c (row 1459, 20:10:36Z, read B+C only)
> and judge-b → slot a (row 1464, 20:11:54Z, read A r1 + C); judge-c is in flight.
> r1's "zero recovery plan_vote rows" claim is historical. This r2 is itself the
> conductor-created replan round the §6 mitigation prescribes; the conductor must
> apply AC-1 sha-validation so the sealed tally names which plan-A revision each
> judge read. (4) Plan C's **six-of-seven-packs finding is independently confirmed**
> at `c53e0d01`: the execution work-order (`pi-benchmark-deepseek-moa-execution.md`
> :71-77) lists six evaluation packs and carries MoA route/downgrade evidence only as
> a judge-scoring dimension (:81), not as an evaluation pack — R3 step 3's seven-pack
> reconciliation now has an exact anchor. (5) Stale state unchanged: ROLE-CORRECTION
> `IMPL`/`REVIEW` still `open`, `REPLAN-C-r1` still `claimed`; `active-run (1).json` /
> `escalation (1|2).json` markers still present; `consensus_result` count still 6
> repo-wide, zero for ROLE-CORRECTION. (6) `active-run.json` heartbeat refreshed to
> 2026-07-22T20:10:12Z, same prefix `PI-BENCH-RECOVERY-20260722`, same live pid 91892.

**Mission:** turn the halted `PI-BENCH-ROLE-CORRECTION-20260722` run
(`HALTED-CONSENSUS-INVALID-PLAN`) into a clean, single-conductor, evidence-gated path
that lands the still-needed role correction in the lifecycle and work-order, while
preserving append-only history and the user-authoritative role contract.

## 0. Retained role contract (non-negotiable, restated verbatim in intent)

1. **DUT:** Istara's original agentic loop vs the Pi adaptation on identical scenario
   inputs. Istara is the system under evaluation — never a provider, worker, or judge.
2. **Evaluation backend:** every live DUT call traverses Istara's API/`AgenticDispatcher`
   and uses the configured **DeepSeek** route under one cumulative `$1.00` cap. No direct
   DeepSeek substitution for either arm; no Kimi/Claude/Codex/local/open-source DUT
   providers in this run.
3. **MoA:** existing Istara dispatcher/validation and Research Spine behavior is
   *measured* (requested vs served route identity, ensemble width, output processing,
   downgrade/degraded evidence). Production routing and defaults are not changed.
4. **Post-run judge:** after B0 and B1…B_N are terminal, a **separate BSC session** with
   **Kimi** as the intended judge harness/model scores frozen artifacts and emits
   `report.md`, `report.html`, `scorecard.json`, and per-judgment outputs — without
   rerunning the DUT or spending evaluation budget.

Every corrective edit proposed below is checked against these four roles; any edit that
would weaken them is out of scope by definition.

## 1. Verified current state (evidence, re-inspected 2026-07-22 at `c53e0d01`)

### 1.1 Why the prior consensus is invalid (root cause, not just the symptom)

Cross-reading lifecycle L-30..L-34 against CF `task_evidence` rows 1405/1410/1428 and
task timestamps shows the votes were cast against **moving targets**:

| Judge | Voted at | Read (per own ledger entry) | Vote |
|---|---|---|---|
| judge-a (L-30) | 19:42:46Z | plan B **r1**, plan C | slot c |
| judge-b (L-31) | 19:43:35Z | plan A **r1**, plan C | slot a |
| judge-c (L-34) | 19:50:29Z | plan A **r1 then re-read at r2** (L-32 landed mid-stage, 19:44:58Z), plan B **r1** | slot a |

- Plan A moved r1→r2 *during* the voting window (L-32 at 19:44:58Z, between judge-b and
  judge-c votes), so the two "slot a" votes endorse different documents.
- Plan B r2 (`…-REPLAN-B-r2`, L-33 at 19:46:36Z, task `done`) rewrote plan B **after**
  both judges who read B had voted — and its 219+/188− rewrite is still **uncommitted**
  in the worktree (`git diff --numstat` re-verified at r1: `219 188 …plan-b.md`). No
  judge ever saw B r2.
- **No `consensus_result` evidence row exists** for the role-correction run. Re-verified
  at r1 by listing every `consensus_result` row in `task_evidence`: exactly 6 exist
  repo-wide (rows 168, 221, 334, 1262-1264 — pi-prod-readiness, pi-complete,
  pi-runtime-complete, pi-eval pipelines); none names any
  `PI-BENCH-ROLE-CORRECTION-20260722` task. Only the three `plan_vote` rows
  1405/1410/1428 exist. The 2–1 tally for slot a was never sealed and must not be
  treated as a consensus.

Conclusion: the halt was correct. The prior consensus state is unrecoverable **as
pipeline state** and must not be resumed.

### 1.2 Residual state left by the halted run

**Worktree (uncommitted/untracked), re-verified by `git status --porcelain` at r1:**
- `M docs/build-stream/plans/pi-bench-role-correction-20260722-plan-b.md` — the unjudged
  r2 rewrite (219 insertions, 188 deletions).
- `?? docs/build-stream/plans/pi-bench-role-correction-20260722-plan-c.md` — plan C was
  **never committed** at any revision (header says r1, task `REPLAN-C-r1` still
  `claimed`, never finished).
- `?? docs/build-stream/conductor-instructions/pi-benchmark-role-correction.md`,
  `?? …/pi-benchmark-deepseek-moa-execution.md`, `?? …/pi-benchmark-recovery-planning.md`
  — the governing briefs/work-order exist only as untracked files.
- `M recipes/istara-main-pi-replacement/recipe.toml` — +21 role definitions for the
  moa/role-correction/**recovery** pipelines. The recovery roles are load-bearing for the
  *current* run; this diff is conductor-owned orchestration config, not worker scope.

**Compass Forge store (re-verified by direct `tasks` query at r1):**
- `PI-BENCH-ROLE-CORRECTION-20260722-IMPL` — `open`, never claimed (stale).
- `PI-BENCH-ROLE-CORRECTION-20260722-REVIEW` — `open`, never claimed (stale).
- `PI-BENCH-ROLE-CORRECTION-20260722-REPLAN-C-r1` — still `claimed` by
  `kimi-code/k3-max-…-architect-c-…` (actor stopped; stale claim).
- *(r1, this pipeline, NOT stale)* `PI-BENCH-RECOVERY-20260722-IMPL`/`…-REVIEW` are
  pre-created `open` rows of the recovery pipeline itself, and `…-PLAN-C` is `claimed`
  in-flight. RV-3 must cancel only the three ROLE-CORRECTION rows above and must not
  touch RECOVERY-prefixed rows.

**Conductor state (re-verified by direct inspection of `.compass-forge/conductor/` at r1):**
- `active-run.json` → `{prefix: PI-BENCH-RECOVERY-20260722, recorded_at 20:03:18Z}` with
  live pid `conductor.pid=91892` (verified alive via `ps -p`) — the current recovery
  conductor; correct.
- `active-run (1).json` → **stale duplicate marker** for `pi-full-20260720-w8`
  (2026-07-22T05:39:55Z); plus `escalation (1).json` / `escalation (2).json` duplicates.
  These " (1)"-suffixed files are not read by the conductor under their canonical names,
  but they are exactly the "stale marker" class the brief requires identified; they must
  be archived so no future resume can mistake them for live state.

**What the halted run got right (reusable content):**
- The role-correction **content** in plan A r2
  (`docs/build-stream/plans/pi-bench-role-correction-20260722-plan-a.md`, committed at
  `1ff29c48`, unmodified since — re-verified) is current, line-anchored, and its
  RC-1..RC-6 edit set implements exactly the §0 role contract: swap Kimi→DeepSeek as the
  evaluation identity in the embedded winning-plan section (task table, A3/A4/A7, §5
  commands, risks, G0/G1, non-goals), append DEC-7 superseding DEC-5's "judge call
  through DeepSeek" clause and DEC-6's Kimi-evaluation wording, and tighten the
  execution work-order. Plan B r2 (uncommitted) and plan C r1 (untracked) contain
  corroborating audits worth mining (B's normative role table and requested-vs-served
  MoA provenance; C's README-pointer sweep).
- The still-open defect is real and re-verified at r1: the lifecycle's embedded winning
  plan still names Kimi as the evaluation provider throughout (`:202` slice diagram,
  `:307` "Kimi-only evaluation adapter" B0-3 row, `:311-312` B0-7/`--provider kimi`
  wave row, `:327/:330/:339` A3/A4/A7, `:357-393` §5 commands and preflight, `:422/:424`
  risk rows, `:449/:452` G0/G1, `:465-466` non-goals), DEC-5 still routes "and judge
  call through DeepSeek" (`:489`), DEC-6 (`:495-503`) still says "configured Kimi
  route/model" for evaluation, and no DEC-7 exists. The correction is still needed;
  only the *pipeline* that was carrying it died.

### 1.3 Reuse verdict (required planner output)

**Reusable as content, not as state.** The prior plan artifacts (A r2 committed; B r2 and
C r1 preserved as history) are safe to reuse as *input material* for a fresh, scoped
correction task. The prior votes, the missing consensus tally, and the halted pipeline
state are **not** reusable: this recovery pipeline runs its own consensus (slots A/B/C +
judges) and its winning plan alone authorizes the implementation.

## 2. Design — smallest safe path

Three strictly ordered, individually verifiable recovery steps, all executed by **one**
implementer task inside **this** recovery pipeline, after this pipeline's own consensus
and the owner gate:

**R1 — Quarantine & preserve history (append-only).**
Commit the halted run's orphan artifacts *as they are*, as historical evidence:
plan B r2 (uncommitted modification), plan C r1 (untracked), and the three
conductor-instruction briefs. One commit, explicit paths only, message declaring them
historical artifacts of the halted run. No content edits. This cleans the docs surface
of the worktree so every later diff audit is exact. (`recipe.toml` is deliberately
excluded — conductor-owned, load-bearing for the live run; the conductor/owner commits
it at ship. Recovery IMPL must not touch it, per the brief.)

**R2 — Orchestration-state hygiene (no git surface).**
- Cancel/close the three stale CF rows so no future conductor dispatches them:
  `PI-BENCH-ROLE-CORRECTION-20260722-IMPL`, `…-REVIEW` (open), and release/cancel the
  stale claim on `…-REPLAN-C-r1`. Use the conductor's cancel path (never `--force`
  finish); each cancellation records a note pointing at this recovery plan.
  RECOVERY-prefixed rows (`…-RECOVERY-…-IMPL`/`…-REVIEW`, pre-created `open`) belong to
  the live pipeline and are out of RV-3's scope.
- Archive the stale markers: move `active-run (1).json`, `escalation (1).json`,
  `escalation (2).json` into `.compass-forge/conductor/archive-20260722/` (or the
  conductor's canonical archive location). Never delete; never touch the live
  `active-run.json`/`conductor.pid`.

**R3 — The role correction itself (new scoped task, fresh anchors).**
Re-apply the plan-A-r2 RC edit set as a NEW correction under this recovery pipeline:
1. In the lifecycle's embedded winning-plan section: replace every Kimi-as-evaluation
   identity with the configured DeepSeek route (B0-3 task row, A3/A4/A7, §5
   `--provider`/preflight commands, risk rows, G0/G1, non-goals §9) so the evaluation
   provider reads DeepSeek-through-Istara everywhere.
2. Append **DEC-7** superseding (not rewriting) DEC-5's "and judge call through
   DeepSeek" clause and DEC-6's "configured Kimi route" evaluation wording, restating §0
   verbatim: DeepSeek serves DUT calls via Istara's dispatcher under the `$1.00` cap;
   Kimi judges post-run in a separate BSC session over frozen artifacts.
3. Reconcile the work-order
   (`docs/build-stream/conductor-instructions/pi-benchmark-deepseek-moa-execution.md`)
   to the same role language, including the seven evaluation packs (canonical 15,
   feature breadth, Research Spine, A2A, prompt/injection probes, usage/cost, MoA
   route/downgrade evidence) and the judge-must-not-rerun-DUT / no-ledger-draw rules.
   Confirmed at r2 (`c53e0d01`): the work-order's pack list (:71-77) names only six
   packs — MoA route/downgrade evidence appears solely as a judge-scoring dimension
   (:81) and must be promoted to an evaluation pack measured during B1…B_N.
4. Append one ledger entry + Status Block refresh under `repo_lock.completion_lock`.
   All prior ledger entries and the master plan remain byte-identical.
**Anchor discipline:** role-correction plan A r2's line anchors were verified at
`1777753c`; this recovery r2 re-verified the lifecycle anchors at `c53e0d01` (they
currently hold: `:202-466` Kimi regions — B0-3 `:307`, `--provider kimi` wave row
`:312`, A3/A4/A7 `:327/:330/:339`, §5 commands `:357-393`, risks `:422/:424`, G0
`:449`, non-goals `:465-466` — DEC-5 clause `:489`, DEC-6 `:497`, no DEC-7
decision heading), but R1's quarantine commit and any
intervening ledger appends will move them again. The implementer MUST re-run the anchor
greps at its own HEAD under the completion lock and edit by match, not by stale line
number.

**Explicitly deferred (new CF tasks, not silent scope):**
- `tests/pi_benchmark/deepseek_judge.py` docstring/policy text (declares a
  shared-ledger DeepSeek judge, contradicting §0.4) — benchmark Python is barred from
  this recovery stage; defer to an owner-approved follow-up task before any live run.
- `recipe.toml` commit — conductor/ship stage.
- Any B0 re-validation or live-wave planning — blocked behind G-R2/G0 below.

### Single-conductor invariant (verified now, enforced going forward)

Re-verified at r2 planning time: exactly one conductor (`conductor.pid` 91892, alive,
bound to `active-run.json` prefix `PI-BENCH-RECOVERY-20260722`, heartbeat 20:10:12Z);
no other `worker.sh`/conductor processes; the only worktree writers are this pipeline's
architect and judge slots, each confined to its own `plan_file` (architects) or
read-only judging (judges) plus lock-serialized lifecycle appends. Enforcement in R1–R3: one implementer task at a time (the recovery cast must
not dispatch IMPL concurrently with any other writer role); every lifecycle
read-append-commit happens inside `repo_lock.completion_lock` with `commit_paths`
(explicit paths, never `-A`); R2's stale-marker archive removes the only artifacts a
second conductor could mistakenly resume from. Precondition gate before IMPL dispatch:
re-run the §5 process/marker/claim audit and require zero collisions.

## 3. Task breakdown

| # | Task | Role | Files/state touched | Depends on | Est |
|---|------|------|---------------------|-----------|-----|
| RV-0 | Recovery consensus: judges vote on recovery plan slots a/b/c; conductor seals `consensus_result` | judges + conductor | CF evidence only | plans A/B/C finished | S |
| RV-1 | **G-R1 owner gate:** owner approves the winning recovery plan (in-chat, recorded as CF evidence) before any implementation | owner + conductor | CF evidence only | RV-0 | S |
| RV-2 | R1 quarantine commit (plan B r2, plan C r1, three briefs; explicit paths) | recovery implementer | `docs/build-stream/plans/…plan-b.md`, `…plan-c.md`, `docs/build-stream/conductor-instructions/*` | RV-1 | S |
| RV-3 | R2 CF/state hygiene: cancel stale ROLE-CORRECTION IMPL/REVIEW/REPLAN-C-r1; archive ` (1)`-suffixed markers | recovery implementer (conductor-assisted for cancels) | CF store, `.compass-forge/conductor/` | RV-1 | S |
| RV-4 | R3 role correction: lifecycle winning-plan identity swap + DEC-7 + work-order reconcile + ledger/Status Block under lock | recovery implementer | `docs/build-stream/2026-07-22-pi-benchmark.md`, `…/pi-benchmark-deepseek-moa-execution.md` | RV-2, RV-3 | M |
| RV-5 | Independent review of RV-2..RV-4 diff (scope, §0 retention, append-only audit) with `review_verdict` | recovery code-reviewer | none (read-only) | RV-4 | S |
| RV-6 | **G-R2 owner gate:** owner reviews the corrected lifecycle and explicitly re-authorizes B0/live planning as a NEW pipeline; until then nothing live runs | owner | CF evidence only | RV-5 pass | — |

No task in this table starts a server, loads a model, calls DeepSeek/Kimi, runs any
B-wave, or spends evaluation budget.

## 4. Acceptance criteria

- **AC-1 (consensus validity):** a `consensus_result` evidence row exists for this
  recovery pipeline before IMPL dispatch, and every judge's `plan_vote` payload names
  the exact plan-file blob sha it read (conductor validates the files did not change
  between vote and tally).
- **AC-2 (history preserved):** after RV-2..RV-4, `git log` shows only additive doc
  commits; no ledger entry existing at IMPL dispatch time (L-1..L-39 at r2 authoring;
  the implementer pins the exact range under the completion lock before editing),
  no DEC-1..DEC-6 text, and no master-plan
  byte changes (`git diff <pre-recovery-sha>..HEAD -- docs/build-stream/plans/2026-07-20-pi-full-replacement-master-plan.md` is empty).
- **AC-3 (role contract):** post-RV-4, the lifecycle + work-order contain zero
  Kimi-as-evaluation statements: every `kimi` match (case-insensitive) in both files sits
  in post-run-judge context; every live-call statement names DeepSeek via Istara's
  API/dispatcher; DEC-7 present; `$1.00` cumulative cap, `max_processes=N`, immutable
  manifest, and resumable B1…B_N language intact.
- **AC-4 (scope):** the cumulative RV-2..RV-4 diff touches only
  `docs/build-stream/plans/*`, `docs/build-stream/conductor-instructions/*`, and
  `docs/build-stream/2026-07-22-pi-benchmark.md` — zero backend/frontend/tests/recipes/
  manifests/reports paths.
- **AC-5 (state hygiene):** CF has no `open`/`claimed` task with prefix
  `PI-BENCH-ROLE-CORRECTION-20260722`; no ` (1)`-suffixed marker files remain in
  `.compass-forge/conductor/`; `active-run.json` still names this recovery run and
  `conductor.pid` is alive and unique. RECOVERY-prefixed rows follow their own
  pipeline lifecycle and are exempt from this criterion.
- **AC-6 (no live activity):** no new rows in any benchmark budget ledger; no
  `.results/runs/` mtime changes; no DeepSeek/Kimi network activity attributable to the
  recovery tasks.
- **AC-7 (gates):** G-R1 evidence exists before RV-2; G-R2 evidence is the only path to
  any subsequent B0/live planning pipeline.

## 5. Verification (exact commands)

Pre-IMPL collision audit (RV-1 precondition, run by the conductor/implementer):

```bash
ps aux | grep -E 'conductor|worker\.sh' | grep -v grep            # exactly the one recovery conductor
cat .compass-forge/conductor/conductor.pid && ps -p "$(cat .compass-forge/conductor/conductor.pid)"
python3 -c "import json;print(json.load(open('.compass-forge/conductor/active-run.json'))['prefix'])"  # PI-BENCH-RECOVERY-20260722
ls ".compass-forge/conductor/" | grep -E '\(1\)|\(2\)'            # stale markers to archive (empty after RV-3)
( cd "$ROOT" && compass-forge task list --target "$ROOT" ) | grep -E 'ROLE-CORRECTION.*(open|claimed)'  # empty after RV-3
```

RV-2 quarantine commit audit:

```bash
git status --porcelain                                            # afterwards: only recipe.toml remains modified
git show --stat HEAD                                              # only the five named doc paths
git diff --check
```

RV-4 correction audit (all must pass before RV-5 handoff):

```bash
git diff --check
git diff --name-only <rv2-sha>..HEAD | grep -vE '^docs/build-stream/' | wc -l   # 0  (AC-4)
grep -niE 'kimi' docs/build-stream/2026-07-22-pi-benchmark.md docs/build-stream/conductor-instructions/pi-benchmark-deepseek-moa-execution.md
#   review every hit: judge-context only (AC-3)
grep -nE 'DEC-7' docs/build-stream/2026-07-22-pi-benchmark.md               # present, supersedes DEC-5 judge clause + DEC-6
grep -nE 'budget_cap_usd=1\.00|max_processes' docs/build-stream/2026-07-22-pi-benchmark.md  # invariants intact
git diff <pre-recovery-sha>..HEAD -- docs/build-stream/plans/2026-07-20-pi-full-replacement-master-plan.md | wc -l  # 0 (AC-2)
python3 - <<'EOF'  # ledger append-only check: every pre-existing L-n heading byte-identical
# diff the L-1..L-36 headings between pre-recovery-sha and HEAD; exit nonzero on any change
EOF
```

No-live-activity audit (AC-6):

```bash
find tests/pi_benchmark/.results -newer .compass-forge/conductor/active-run.json 2>/dev/null | wc -l  # 0
```

Every executed command is recorded as CF `command` evidence on the owning task.

## 6. Risks and mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Consensus invalidation recurs: a plan slot is rewritten while judges vote | High (it just happened) | AC-1: votes carry the plan-file blob sha; conductor refuses to tally if any sha changed after the earliest vote; architects may not revise after finishing (revisions = a new conductor-created replan round). Note: this r2 IS such a conductor-created round and lands **mid-window** — judge-a (read B+C only; A-revision-neutral) and judge-b (read A r1) have voted, judge-c is in flight. The conductor's tally must therefore record which plan-A revision each vote addressed and either have judge-c read r2 with its blob sha, or seal against the r1 sha judge-b read. No silent mixing. |
| Ledger-numbering race in shared worktree (observed at L-32) | Medium | All lifecycle appends inside `repo_lock.completion_lock` (read last L-n under the lock), `commit_paths` with explicit paths; never `git add -A`. |
| Stale kimi claim on REPLAN-C-r1 can't be released by a worker | Medium | RV-3 is conductor-assisted; if CF lacks a cancel verb for a claimed task, the conductor releases it; worker records the blocked state as evidence instead of forcing. |
| Quarantine commit accidentally sweeps `recipe.toml` or other non-doc state | Low | Explicit-path `commit_paths` only; RV-2 audit command asserts the post-commit porcelain shows exactly `M recipe.toml`. |
| Fresh-anchor drift: RC edit set applied at stale line numbers | Medium | R3 mandates re-grep at implementation HEAD under the lock; AC-3 grep battery is content-based, not line-based. |
| A second conductor/actor resumes from leftover markers mid-recovery | Low after RV-3 | RV-3 archives ` (1)` markers first; pre-IMPL collision audit is a blocking precondition; single-writer cast discipline. |
| `deepseek_judge.py` code/doc still contradicts §0.4 after this recovery | Certain (deferred) | Explicitly registered follow-up CF task, owner-gated, required before any live wave — G-R2 checklist item. |
| Judges read uncommitted worktree plan files that later differ from committed history | Retired (was Low) | All three recovery candidates are committed (A `9c45a42a`/`68dcd159`, B `9cfe3304`, C `02595094`); AC-1 sha discipline covers revision identity from here. |
| RV-3 accidentally cancels the recovery pipeline's own pre-created IMPL/REVIEW rows | Low | RV-3's cancel list is prefix-exact (`PI-BENCH-ROLE-CORRECTION-20260722-*` only); AC-5 explicitly exempts RECOVERY-prefixed rows; the audit grep in §5 filters on `ROLE-CORRECTION`. |

## 7. Rollback

- **Pre-recovery baseline is recorded:** branch `Review_pi_test` @ `75db26f5` (the last
  commit before this recovery pipeline's own plan commits `9cfe3304`/`b96b04a9`/
  `9c45a42a`, which are pipeline history, not RV implementation output).
- **RV-2/RV-4 (git):** each step is one additive doc commit; `git revert <sha>` restores
  the prior text exactly. No code, schema, or config is involved, so revert is total.
- **RV-3 (CF/state):** cancelled tasks can be re-opened by the conductor; archived
  marker files are moved, not deleted — restoring them is a `mv` back. The live
  `active-run.json`/`conductor.pid` are never modified, so the running conductor is
  never at risk from a rollback.
- **Worst case** (recovery itself must be abandoned): stop the conductor, `git revert`
  the RV commits in reverse order, restore archived markers, and leave a final ledger
  entry recording the abandonment — history remains append-only throughout.

## 8. Owner gates summary

- **G-R1 (blocking, before any recovery implementation):** owner approves the winning
  recovery plan in-chat; recorded as CF evidence. Nothing in RV-2..RV-4 runs before it.
- **G-R2 (blocking, after RV-5 pass):** owner reviews the corrected lifecycle/work-order
  and explicitly authorizes the next pipeline (B0 re-validation → live waves). The
  existing lifecycle gates G0/G1/G2 (DeepSeek-only `$1.00` envelope, dry-run estimate,
  per-wave budget checks) remain intact downstream and are not weakened by this plan.
- No live evaluation, model load, or spend occurs anywhere in this recovery pipeline.
