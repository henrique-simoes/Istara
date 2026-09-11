# Plan C (r1) — Pi benchmark recovery: reconcile pipeline state, re-validate and apply the role correction

- **Task:** `PI-BENCH-RECOVERY-20260722-REPLAN-C-r1` (consensus architect slot C,
  revision r1 — supersedes r0 authored under `PI-BENCH-RECOVERY-20260722-PLAN-C`,
  committed at `02595094`, sha256 `8a014ff5336dd6f248a445bd87f990f9527421ecfd8ec3bf6a26f65e64e7db32`;
  pipeline `PI-BENCH-RECOVERY-20260722`)
- **Spec:** CF-SPEC-8 · **Lifecycle:** `docs/build-stream/2026-07-22-pi-benchmark.md`
- **Brief (verbatim source):** `docs/build-stream/conductor-instructions/pi-benchmark-recovery-planning.md`
- **Authored:** 2026-07-22 (r1), against branch `Review_pi_test` @ `146e04fc`
  (plus tail-only append `5f8207ea`; r0 was audited @ `75db26f5`). Every r0
  load-bearing claim below was re-verified by fresh commands at r1 — grep/sqlite/ps/shasum
  battery recorded as CF command evidence on this task.
- **Scope:** documentation/planning-only recovery. No backend/frontend/tests/recipes/
  manifest/report edits, no benchmark execution, no live model calls, no spend. The
  master plan `docs/build-stream/plans/2026-07-20-pi-full-replacement-master-plan.md` is
  never touched.

> **r1 revision note (conductor-created repair round).** No r0 factual errors found; all
> §1.2 line anchors still hold at `146e04fc` (`5f8207ea` appended only a ledger tail and
> the Status Block, leaving `:202-500` untouched). Post-r0 drift folded in:
> (1) All three recovery candidates are now committed — A r0 `9c45a42a`, B `9cfe3304`,
> C r0 `02595094`, A r1 `68dcd159`, **A r2 `5f8207ea`** — so r0's "judges read
> uncommitted files" hazard is retired for this pipeline; what remains is the
> moving-target hazard, which has *recurred* (§1.5).
> (2) **Recovery judging opened while this repair round runs.** CF `plan_vote` rows now
> exist: 1459 (judge-a → slot c; read B + C r0 `8a014ff5…`) and 1464 (judge-b → slot a;
> read A r1 `d221d818…` + C r0 — its recorded shas match both blobs exactly). Judge-c is
> `claimed`/in-flight. Zero `consensus_result` rows exist for this pipeline (6 repo-wide,
> all earlier pipelines — re-verified by direct sqlite scan).
> (3) Slot A moved r1→r2 (`d221d818…` → `ac339631…` at `5f8207ea`, 20:15:02Z) **after**
> judge-b's vote (20:12:43Z); this r1 moves slot C **after** judge-a's vote (20:11:15Z).
> The incommensurable-votes failure that invalidated the role-correction consensus is
> repeating on both leading slots right now; §1.5 + AC-8 make the freeze rule binding.
> (4) Lifecycle append-only protection range is now **L-1..L-41** (L-39/L-40 judge votes,
> L-41 plan-A-r2; Status Block `ledger: L-41`).
> (5) New verified apparatus defect: `tests/pi_benchmark/` runs **170 passed / 2 failed**
> at HEAD — `test_deepseek_provider.py::test_chat_happy_path_commits_actual_cost` and
> `::test_preflight_is_a_minimal_ledgered_call` raise `LedgerStateError: commit … exceeds
> its reservation` at `budget_ledger.py:277`. Red continuously since L-26 (19:38Z); the
> post-F-3..F-7 delta re-review never ran. Registered as follow-up debt (§3 RV-3, §9
> G-REC-1) — code repair is outside this recovery's docs-only scope.
> (6) The CF verbs §6 relies on (`task release`, `task status`, `task comment`) are
> confirmed to exist (`compass-forge task --help`).
> (7) Stale surface unchanged: ROLE-CORRECTION `IMPL`/`REVIEW` still `open`,
> `…-REPLAN-C-r1` still `claimed` by the stopped kimi actor; `active-run (1).json`,
> `escalation (1).json`, `escalation (2).json` still present; exactly one conductor
> (pid 91892, `recovery-cast.json`, prefix `PI-BENCH-RECOVERY-20260722`, heartbeat
> 20:10:12Z, verified alive).

**Mission:** turn the halted `PI-BENCH-ROLE-CORRECTION-20260722` run
(`HALTED-CONSENSUS-INVALID-PLAN`) into a clean, single-conductor, evidence-gated path
that lands the still-needed DeepSeek/Kimi role correction in the lifecycle and
work-order — preserving append-only history and the user-authoritative role contract,
and this time with a consensus seal that provably names the artifacts it ratifies.

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

The invalidity is structural, not a transient wedge — re-verified at r1 against CF state
(`.compass-forge/state.sqlite3`, direct sqlite scan) and git:

1. **Incommensurable votes.** The three role-correction `plan_vote` rows were cast
   against *different candidate sets and revisions*: judge-a read plan-B r1 vs plan-C r0
   (CF evidence 1405); judge-b read plan-A r1 vs plan-C r0 (1410); judge-c read plan-A
   r1→r2 *mid-stage* vs plan-B r1 (1428). No two judges evaluated the same frozen
   artifact pair, so the 2-1 "slot a" tally is void as a governing decision.
2. **Governing artifacts not durable.** Role-correction slot C's plan was never committed
   at any revision (`docs/build-stream/plans/pi-bench-role-correction-20260722-plan-c.md`
   is **still untracked** at r1, 347 lines); slot B's r2 exists only as *uncommitted*
   working-tree modifications (`git diff --numstat` re-verified: `219 188`).
3. **Unterminated stage.** `PI-BENCH-ROLE-CORRECTION-20260722-REPLAN-C-r1` is still
   `claimed` in CF by the stopped kimi architect actor (re-verified by direct `tasks`
   query at r1); never finished.
4. **No seal.** Zero `consensus_result` evidence rows name any
   `PI-BENCH-ROLE-CORRECTION-20260722` task (re-verified at r1: exactly 6
   `consensus_result` rows exist repo-wide — ids 168, 221, 334, 1262-1264 — all from
   pi-prod-readiness, pi-complete, pi-runtime-complete, pi-eval).
5. **Ledger numbering races are a matter of record.** L-15 → L-17 gap (no L-16); plan A
   r2's note of a dangling Status Block `ledger: L-30` while its entry landed as L-32.
   Proof the Status Block cannot be trusted for numbering under concurrent writers.
6. **Orphan claimable surface.** `PI-BENCH-ROLE-CORRECTION-20260722-IMPL` and `-REVIEW`
   remain `open` (re-verified at r1). Any future conductor pointed at the old prefix
   could "resume" the invalid pipeline.

**Conclusion (unchanged from r0):** the halt was correct; the prior consensus state is
unrecoverable *as pipeline state* and must not be resumed.

### 1.2 The underlying defect is still present and still needs exactly one correction

The lifecycle's embedded winning plan still contradicts the user-authoritative role
contract. Re-verified by fresh grep at `146e04fc` (line numbers current; `5f8207ea`
touched only the ledger tail/Status Block):

| Region | Lines | Wrong text (verified at r1) |
|---|---|---|
| §2.1 diagram | 202 | "disjoint, resumable Kimi-evaluation slices under one $1.00 cap" |
| §3 task table B0-3 | 307 | "Kimi-only evaluation adapter/preflight" |
| §3 task table B1…B_N | 312 | `--provider kimi --model <configured-kimi-model>` |
| §4 acceptance A3 / A4 / A7 | 327 / 330 / 339 | "Kimi evaluation credential", "configured Kimi evaluation provider/model", "uses Kimi only" |
| §5 verification commands | 374, 377, 385–386, 393 | `--provider kimi` in runner/ledger/preflight commands |
| §6 risk rows | 422, 424 | "Kimi evaluation API quota", "rejects non-Kimi evaluation configuration" |
| §8 owner gates G0 / G1 | 449, 452 | "authorizes Kimi-only …", "Kimi provider/model identity" |
| §9 non-goals | 465–466 | "non-Kimi evaluation provider routing", "Kimi evaluation `$1.00` envelope" |
| Decision log DEC-5 | 489 | "…and judge call through DeepSeek `deepseek-v4-pro`" |
| Decision log DEC-6 | 497 | "route every live benchmark evaluation call through the configured Kimi route/model" (+ open judge cast :499-500) |

(r0 omitted the :202 diagram row from its table on pattern-matching grounds; it is
included here — judge-a independently confirmed it at CF 1404-1406 and again at L-39.)

**Already correct — do not churn (re-verified):** Goals (:26-30); the wave/provider
contract (:35-57, incl. "All live Istara evaluation calls use the configured DeepSeek
provider/model through Istara's API/dispatcher … Kimi … disabled for this run. Post-run
judging is a separate BSC session using the intended Kimi judging harness" :50-53, and
the $1.00 cumulative envelope + judge-does-not-consume-budget rule :54-57); §2.2 design
principle 5. The execution work-order
`docs/build-stream/conductor-instructions/pi-benchmark-deepseek-moa-execution.md` is
role-correct (DUT=Istara, DeepSeek-only behind Istara; Kimi intended judge; judge must
not rerun the DUT; judging does not consume the evaluation ledger) — but its
"Evaluation matrix" wave list (:69-73) names only **six** packs (canonical 15-scenario
contract, feature/breadth, Research Spine, A2A, prompt/injection probes, token/usage
accounting); MoA route/downgrade evidence appears only as a judge-scoring dimension
(:81), not as an evaluation pack. Plan A r2 independently confirms this arithmetic.

### 1.3 Prior correction artifacts — inventory and reuse verdict (required planner output)

| Artifact | State @ r1 (verified) | Reuse verdict |
|---|---|---|
| `pi-bench-role-correction-20260722-plan-a.md` r2 (268 lines) | committed @ `1ff29c48`, unmodified since (git log re-verified) | **Reusable as the correction reference.** Triple-verified line anchors; smallest surgical scope; all load-bearing claims re-verified at r1 (§1.2). Its §7 debt row (deepseek_judge.py judge-shares-evaluation-ledger policy) stands. |
| `pi-bench-role-correction-20260722-plan-b.md` r2 | uncommitted working-tree edits on r0 (`219 +/188 −`) | Content valuable (normative role block, terminal eval→judging barrier, requested-vs-served MoA provenance); no commit identity — **harvest ideas, do not execute from it.** |
| `pi-bench-role-correction-20260722-plan-c.md` r1 (347 lines) | untracked | As B: strong 16-region audit and full DEC-7 pre-specification to cross-check against; **not executable** (never durable, its REPLAN task never terminated). |
| The 2-1 judge tally (a/c/a → slot a) | CF `plan_vote` rows 1405/1410/1428 | **Void.** Cast on mixed revisions of non-committed artifacts (§1.1-1/2). Must not be reused as a consensus marker. |
| Ledger L-1…L-41 + findings register (F-1…F-7 all `fixed`) | committed | Append-only history. Keep byte-identical; supersede by new entries only. Note: F-3…F-7 say `fixed`, but the delta re-review barrier never ran and the suite still shows 2 red provider tests (below) — the register is history, not a green attestation. |
| Benchmark apparatus (`tests/pi_benchmark/`, scheduler/manifest/ledger/live-driver/MoA/judge/report) | committed; **170 passed / 2 failed** at HEAD | Reusable as *apparatus content* for the later owner-approved pipeline, **not** as execution-ready state: the two `test_deepseek_provider.py` failures (`commit exceeds reservation`, `budget_ledger.py:277`) mean the provider/ledger contract is untested-red. Follow-up debt before any live wave; out of this recovery's code scope. |
| Execution work-order + role-correction brief + recovery brief | untracked (`??`) | Governing docs that must become durable before the correction edits them (RV-1). Content role-correct except the six-pack gap (§1.2). |
| `recipes/istara-main-pi-replacement/recipe.toml` | modified (+21 conductor-generated role registrations) | Conductor-owned cast plumbing, load-bearing for the live run; **not** worker scope. Disposition: ship stage or owner commits it separately. |

**Decision (unchanged, now doubly evidenced): reuse the *content* (correction intent,
five-role target, audit tables, verification battery), with role-correction plan A r2 as
the primary reference cross-checked against plan C r1's 16-region audit and plan B r2's
role-block/barrier machinery. Do not reuse the *consensus outcome*, do not resume the
halted pipeline's tasks, and re-anchor every citation at implementation HEAD before
editing.** Authoring a fourth from-scratch correction plan would add churn, not safety:
three independent audits plus two judge spot-checks converge on the same surfaces, and
the r1 grep battery confirms them at current HEAD.

### 1.4 Process / marker / worktree hazards to clear before implementation

Verified at r1:

- **One live conductor** for this recovery run: `conductor.py start --cast
  .compass-forge/conductor/recovery-cast.json` (PID 91892, verified alive via `ps -p`);
  its `active-run.json` matches that cast and prefix `PI-BENCH-RECOVERY-20260722`
  (heartbeat 20:10:12Z). The recovery cast serializes 3 architect slots → 3 judge slots
  → one implementer → one code-reviewer → one fixer (`max_rounds 6`), which is the
  single-conductor invariant to preserve.
- **Stale marker duplicates** in `.compass-forge/conductor/`: `active-run (1).json`
  (points at `cast.json`, prefix `pi-full-20260720-w8`), `escalation (1).json`,
  `escalation (2).json` (w7-era). Must be archived so only one active-run marker exists.
- **Uncommitted cast plumbing:** `recipes/…/recipe.toml` carries the conductor-generated
  `pi-bench-recovery-*` / `pi-bench-role-correction-*` / `pi-bench-moa-*` role
  registrations (uncommitted). Must NOT be swept into any docs-only commit.
- **Untracked governing docs:** all three `docs/build-stream/conductor-instructions/*.md`
  (execution work-order, role-correction brief, recovery brief) remain untracked — the
  correction would otherwise edit an uncommitted file.
- **In-flight sibling stages right now:** judge-c (`kimi-code/k3`) is claimed; slot A's
  r2 repair landed at `5f8207ea` during this stage; this r1 is the slot-c repair.
  Architects write only their own `plan_file`; all lifecycle writes at implementation
  time go through `repo_lock.completion_lock` + path-scoped commits.

### 1.5 Consensus integrity — the freeze rule (new in r1; root-cause fix for the halt)

Evidence that the moving-target failure is recurring **in this pipeline**:

| Vote (CF row) | Cast at | Read | Voted | Candidate state now |
|---|---|---|---|---|
| 1459 judge-a | 20:11:15Z (L-39) | B (`9cfe3304`) + C r0 (`8a014ff5…`) | slot c | C will move to this r1 (`8a014ff5…` → new sha) |
| 1464 judge-b | 20:12:43Z (L-40) | A r1 (`d221d818…`) + C r0 | slot a | A moved to r2 (`ac339631…`) at `5f8207ea`, **after** the vote |
| judge-c | claimed, in flight | — | — | will read A r2 + (C r0 or this r1, depending on timing) |

No `consensus_result` is sealed yet, so the pipeline can still be saved without a second
halt — but only under an explicit freeze discipline:

- **FZ-1 (vote binding).** Every `plan_vote` payload must name the sha256 of each plan
  file the judge actually read. Judge-b already did this (CF 1463 command evidence);
  make it mandatory for judge-c and any re-vote.
- **FZ-2 (staleness check at tally).** Before sealing, the conductor re-hashes all three
  committed plan files. A vote cast on a superseded blob is **void for that slot**. At
  r1 authoring time this voids judge-b's slot-a endorsement (read r1, current is r2) and
  prospectively voids judge-a's slot-c endorsement once this r1 commits.
- **FZ-3 (remedy, not halt).** If any vote is void under FZ-2, the conductor runs **one
  re-vote round** on the now-frozen committed blobs (all slots committed; no further
  architect revisions until the seal — replan rounds reopen only if a judge's re-vote
  verdict demands it). Alternatively, if the conductor determines a revision is
  immaterial to the votes cast, the sealed `consensus_result` payload must name each
  vote's read-sha and record that justification — never a bare tally. Either path is
  valid; a tally that silently mixes blobs is not.
- **Disclosure (this r1).** This revision lands mid-vote because the conductor created
  `…-REPLAN-C-r1` after judging had opened. r0 (`8a014ff5…`, committed `02595094`)
  remains the artifact judge-a endorsed; r1 preserves r0's design (RV-0…RV-4) and
  changes only what the drift evidence requires (this section, the debt registration,
  updated anchors/ranges). If slot c wins, the implementer executes **this r1**; the
  conductor may treat the r0→r1 delta as material (re-vote per FZ-3) or immaterial
  (record the justification in the seal).

## 2. Authoritative role canon (retained verbatim from the owner brief; the correction's target)

1. **DUT:** Istara itself — the original agentic loop vs the Pi adaptation on identical
   scenario inputs; captured behavior is compared. Istara remains the system being
   evaluated — never a provider, worker, or judge.
2. **Evaluation backend:** every live DUT call traverses Istara's API/dispatcher on the
   configured **DeepSeek** API route under one cumulative `$1.00` cap; no direct DeepSeek
   calls as an Istara substitute; no Kimi/Claude/Codex/local/open-source DUT providers
   in this run.
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

Every corrective edit proposed below is checked against these five roles; any edit that
would weaken them is out of scope by definition.

## 3. Design

Five ordered steps; only RV-2 edits content, everything else reconciles state.
Historical ledger entries and DEC-5/DEC-6 text are never rewritten — supersession only.

- **RV-0 — Quarantine the halted run + freeze attestation (conductor/owner, CF state
  only).** Release the stale claim and cancel the three halted-run tasks with a comment
  recording the reason: `PI-BENCH-ROLE-CORRECTION-20260722-IMPL`,
  `…-REVIEW` (both `open`), `…-REPLAN-C-r1` (stale `claimed`). The cancel list is
  **prefix-exact** (`PI-BENCH-ROLE-CORRECTION-20260722-*` only); the recovery pipeline's
  own pre-created rows (`PI-BENCH-RECOVERY-20260722-IMPL`/`…-REVIEW`, `open`) are this
  pipeline's claimable surface and are **exempt**. Archive the stale conductor markers
  (`active-run (1).json`, `escalation (1).json`, `escalation (2).json` →
  `*.stale-20260722.json`; rename, never delete; never touch live
  `active-run.json`/`conductor.pid`). Verify exactly one conductor process and one
  matching `active-run.json`. Record the FZ-1/FZ-2 freeze attestation (§1.5) as CF
  evidence: each vote's read-sha, each candidate's current sha, which votes are valid.
- **RV-1 — Hygiene commit (docs only, one path-scoped commit).** Add the three untracked
  `docs/build-stream/conductor-instructions/*.md` and commit the halted run's plan-B r2
  working-tree content and untracked plan-C r1 **as-is** under a message marking them
  historical artifacts of the invalid run. Result: a clean tree under
  `docs/build-stream/**` so the correction diff in RV-2 is unambiguous and every edited
  file is tracked. `recipes/recipe.toml` is explicitly excluded (§1.4).
- **RV-2 — Role-language correction (one path-scoped commit, two files).** Re-anchored
  at implementation HEAD by the §6 battery (never by copying §1.2 line numbers):
  (a) lifecycle embedded winning-plan: identity-swap every Kimi-as-evaluation usage
  (§1.2 table, :202 included) to the DeepSeek evaluation route (`--provider deepseek
  --model deepseek-v4-pro`), keeping judge references pointed at the post-run Kimi BSC
  session; extend the wave-contract slice list (:42-43) with usage/cost accounting and
  MoA route/downgrade evidence so all seven packs are enumerated (keep `depth` as the
  mapped legacy label); append **DEC-7** (five-role canon of §2, superseding DEC-5's
  judge clause :489 and DEC-6's Kimi-evaluation clause/open cast :497-500) and add
  one-line `(superseded by DEC-7 …)` annotations under DEC-5/DEC-6; (b) work-order: add
  "MoA route/downgrade evidence" to the :69-73 evaluation-matrix pack list, add a
  pointer naming the role-correction brief as the authoritative role statement, and
  repeat the judge-does-not-consume-the-evaluation-ledger rule inside the role list.
  Preserve verbatim: `$1.00` cap, `max_processes=N`, immutable manifest, resumable
  B1…B_N, fail-closed rules, gates, non-goal structure.
- **RV-3 — Recovery reconciliation entry (append-only).** Append **DEC-8** recording:
  the halt (`halted-consensus-invalid-plan`), why the prior tally is void, what was
  reused (content) vs discarded (consensus marker, halted tasks), the single-conductor +
  freeze attestation from RV-0, the owner gate required before any benchmark execution,
  and the **follow-up debt list**: (i) `tests/pi_benchmark/deepseek_judge.py`
  docstring/code declaring judge-shares-evaluation-ledger policy (contradicts §2.4);
  (ii) the two red `test_deepseek_provider.py` tests (`commit exceeds reservation` at
  `budget_ledger.py:277` — provider reservation arithmetic vs the F-6-hardened ledger;
  red since L-26, no delta re-review closed F-3…F-7); (iii) `recipe.toml` commit
  disposition (ship stage/owner). Items (i)-(ii) become NEW CF tasks before any live
  wave; neither is edited in this recovery. Append the implementer's `### L-<n+1>`
  ledger entry under `repo_lock.completion_lock` (number taken from a fresh read of the
  last `### L-<n>` heading, never the Status Block), then refresh the Status Block
  (`stage`, `status`, `last:`, `next_action` → owner gate G-REC-1). Path-scoped commit
  of the lifecycle only.
- **RV-4 — Verification + independent delta review.** Run the full §6 battery, record
  CF command evidence; the recovery code-reviewer re-runs it on the commit and records a
  `review_verdict`.

## 4. Task breakdown

| # | Task | Files / surface | Actor | Depends |
|---|------|-----------------|-------|---------|
| RV-0 | Cancel halted-run tasks (prefix-exact; RECOVERY rows exempt), archive stale markers, single-conductor + freeze attestation | CF state; `.compass-forge/conductor/` | conductor/owner | — |
| RV-1 | Hygiene commit of untracked governing docs + historical plan B/C | `docs/build-stream/**` only | implementer | RV-0 |
| RV-2 | Role-language correction + DEC-7 + work-order tighten | lifecycle + execution work-order | implementer | RV-1 |
| RV-3 | DEC-8 (incl. debt list) + ledger L-<n+1> + Status Block refresh, under completion lock | lifecycle | implementer | RV-2 |
| RV-4 | §6 battery as CF evidence; delta re-review | — | implementer → reviewer | RV-3 |

One implementer task (the already-open `PI-BENCH-RECOVERY-20260722-IMPL`) carries
RV-1…RV-4; RV-0 is a conductor/owner precondition recorded as CF comment evidence on
that task. No task in this table starts a server, loads a model, calls DeepSeek/Kimi,
runs any B-wave, or spends evaluation budget.

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
  regions byte-identical (diff-audit vs pre-RV-2 commit; protected range = every ledger
  entry existing at IMPL dispatch time, L-1..L-41+ at r1).
- **AC-5** DEC-7 (supersession) and DEC-8 (recovery disposition + single-conductor
  attestation + the §3-RV-3 follow-up debt list) present; exactly one new ledger entry;
  Status Block coherent with the last `### L-<n>` heading.
- **AC-6** The three halted-run tasks read `canceled` in CF (RECOVERY-prefixed rows
  exempt); exactly one conductor process, one `active-run.json` matching
  `recovery-cast.json`; no `* (1).json` / `* (2).json` markers remain unarchived.
- **AC-7** No live call, no spend, no benchmark execution, no server start — the
  correction is provably docs/state-only (`git diff --name-only` + process check).
- **AC-8 (consensus freeze, new in r1):** before any IMPL dispatch, a `consensus_result`
  evidence row exists for THIS recovery pipeline whose payload names, per vote, the
  read-sha256 of each candidate plan; every vote counted was cast on the blob that is
  current at seal time (or the seal records the FZ-3 materiality justification); and no
  architect slot revised any candidate between the last counted vote and the seal.

## 6. Verification (exact commands)

Run from the project root `<repo-root>-pi-replacement`. CF verbs
(`release`, `status`, `comment`) verified present by `compass-forge task --help` at r1.

```bash
# --- RV-0 state quarantine (conductor/owner; CF commands run from root) ---
( cd "$ROOT" && compass-forge task release PI-BENCH-ROLE-CORRECTION-20260722-REPLAN-C-r1 )
( cd "$ROOT" && compass-forge task status  PI-BENCH-ROLE-CORRECTION-20260722-REPLAN-C-r1 canceled )
( cd "$ROOT" && compass-forge task status  PI-BENCH-ROLE-CORRECTION-20260722-IMPL      canceled )
( cd "$ROOT" && compass-forge task status  PI-BENCH-ROLE-CORRECTION-20260722-REVIEW    canceled )
( cd "$ROOT" && compass-forge task comment PI-BENCH-ROLE-CORRECTION-20260722-IMPL \
  "Superseded: halted-consensus-invalid-plan; recovery run PI-BENCH-RECOVERY-20260722 owns the correction (DEC-8)." )
mv ".compass-forge/conductor/active-run (1).json"  ".compass-forge/conductor/active-run-1.stale-20260722.json"
mv ".compass-forge/conductor/escalation (1).json"  ".compass-forge/conductor/escalation-1.stale-20260722.json"
mv ".compass-forge/conductor/escalation (2).json"  ".compass-forge/conductor/escalation-2.stale-20260722.json"

# AC-6 single-conductor attestation
ps aux | grep -E 'conductor\.py start' | grep -v grep            # expect exactly one line, recovery-cast.json
cat .compass-forge/conductor/conductor.pid; ps -p "$(cat .compass-forge/conductor/conductor.pid)"
cat .compass-forge/conductor/active-run.json                     # cast_path == recovery-cast.json, prefix == PI-BENCH-RECOVERY-20260722
ls .compass-forge/conductor/ | grep -E '\(1\)|\(2\)' && echo "STALE MARKER" || echo "markers clean"
python3 -c "
import sqlite3; db=sqlite3.connect('.compass-forge/state.sqlite3')
print(db.execute(\"SELECT public_id,status FROM tasks WHERE public_id LIKE 'PI-BENCH-ROLE-CORRECTION%' AND status IN ('open','claimed')\").fetchall())"
# expect: []

# --- AC-8 freeze attestation (before IMPL dispatch; conductor) ---
shasum -a 256 docs/build-stream/plans/pi-bench-recovery-20260722-plan-{a,b,c}.md
python3 -c "
import sqlite3, json; db=sqlite3.connect('.compass-forge/state.sqlite3')
for r in db.execute(\"SELECT e.id, t.public_id, e.payload_json FROM task_evidence e JOIN tasks t ON t.id=e.task_id WHERE e.evidence_type='plan_vote' AND t.public_id LIKE 'PI-BENCH-RECOVERY%' ORDER BY e.id\"):
    print(r[0], r[1]); print(r[2][:400])
print('consensus_result for recovery:', db.execute(\"SELECT count(*) FROM task_evidence e JOIN tasks t ON t.id=e.task_id WHERE e.evidence_type='consensus_result' AND t.public_id LIKE 'PI-BENCH-RECOVERY%'\").fetchone())"
# every counted vote's read-sha must equal the current blob sha (or carry the FZ-3 justification)

# --- pre-RV-2 freshness battery (re-anchor; every edit uses match text, not line numbers) ---
grep -n -iE 'provider kimi|--provider kimi|kimi[- ]only (benchmark )?evaluation|kimi evaluation (credential|provider|api|envelope|adapter)|non-kimi evaluation|configured-kimi-model|kimi[- ]evaluation slices|uses kimi only|authorizes kimi|kimi provider/model identity|kimi route/model|judge call through deepseek' \
  docs/build-stream/2026-07-22-pi-benchmark.md
#   ^ must reproduce the §1.2 table before editing; after RV-2 the same battery must
#     produce ZERO hits outside ### L- history and the annotated DEC-5/DEC-6 quotes.

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

# --- docs-only change must not alter the suite: record counts BEFORE RV-2, compare after ---
backend/.venv/bin/python -m pytest tests/pi_benchmark/ -q
# r1 baseline at 146e04fc: 170 passed, 2 failed (test_deepseek_provider.py —
# commit-exceeds-reservation, pre-existing debt per §1.3/§3-RV-3, NOT caused by RV-2).
# After RV-2 the counts must be IDENTICAL (170/2); any change means the docs commit
# touched code — stop and report.
```

Every executed command is recorded as CF `command` evidence on the owning task; owner
approvals are recorded as CF evidence with the in-chat approval quoted.

## 7. Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Moving-target votes invalidated again (a slot revised while judges vote) | **Realized at r1** (A r1→r2 post-vote; C r0→r1 post-vote) | AC-8/FZ-1..FZ-3: sha-bound votes, staleness check at tally, one re-vote round on frozen blobs instead of a halt; architects do not revise after judging opens unless the conductor opens a replan round. |
| Conductor seals a bare tally from mixed blobs | Medium | AC-8 requires the seal payload to name per-vote read-shas; RV-0 records the freeze attestation as CF evidence; owner gate G-REC-1 reviews it. |
| Stale anchors: §1.2 line numbers drift before RV-2 (sibling ledger appends land) | Medium | Fresh-anchor rule: implementer re-runs the §6 battery at HEAD and edits by matched text; any region that no longer matches is a stop-and-report, not an improvisation. |
| Reusing the void tally or resuming halted tasks | Low | AC-6 cancels the claimable surface; DEC-8 records the tally as void; §1.3 forbids reuse. |
| Ledger numbering race during RV-3 (observed L-16 gap, dangling L-30) | Medium | `repo_lock.completion_lock` around read-append-commit; number from the last `### L-<n>` heading re-read under the lock; path-scoped `repo_lock.commit_paths`; never `git add -A`. |
| recipe.toml cast plumbing swept into the docs commit, breaking AC-4 | Medium | RV-1/RV-2 stage explicit paths only; §6 scope audit greps the commit, not the dirty tree; recipe.toml disposition left to ship stage/owner. |
| Over-correction of already-correct regions (:26-57, work-order roles) | Low | §1.2 keep-list is verified; RV-2 is an identity swap plus the enumerated additions only; reviewer checks the diff is role-identity + pack/pointer/DEC text, nothing else. |
| grep battery false positives from historical ledger text (e.g. L-18 "DeepSeek judge") | Medium | AC-1 scopes hits to non-`### L-` regions by hunk inspection; history is declared exempt. |
| The 2 red provider tests are silently carried into a live wave | Certain if unregistered | Registered in DEC-8's debt list + G-REC-1 checklist; become NEW CF tasks (benchmark-code scope) before any live run; this recovery never edits code. |
| deepseek_judge.py code/doc contradiction left silently | High (it persists) | Not edited here (code out of scope); recorded in DEC-8 and raised as a NEW CF task before any live run. |
| Second conductor started later against the old prefix | Low | RV-0 cancellation + archived duplicate markers + DEC-8 note; G-REC-1 requires the attestation output. |
| Stale kimi claim on REPLAN-C-r1 can't be released by a worker | Medium | RV-0 is conductor/owner-executed; verbs verified to exist; if a claimed task resists `release`, the conductor records the blocked state as evidence instead of forcing. |

## 8. Rollback

- **Baseline:** pre-recovery `75db26f5` (last commit before this pipeline's plan/judge
  commits, which are pipeline history, not RV implementation output).
- RV-1/RV-2/RV-3 are discrete docs-only commits: `git revert <sha>` (reverse order)
  restores prior text exactly. Appended DEC-7/DEC-8/ledger entries remain as history per
  append-only discipline; a revert is itself recorded by a further decision entry.
- RV-0 CF cancellations are reversible (`compass-forge task status <id> open`); archived
  markers are renames, restorable by the inverse `mv`.
- A voided-vote re-vote round (FZ-3) is itself rollback-safe: no candidate file is
  edited during re-voting.
- No code, config, data, credential, or spend state is touched, so no other rollback
  surface exists.

## 9. Owner gates (blocking, in order)

- **G-REC-0 (met by this consensus + owner sign-off):** owner approves the winning
  recovery plan; RV-0 attestation shows one conductor, one active-run marker, halted-run
  tasks canceled, and the AC-8 freeze record (per-vote read-shas, valid votes). No
  implementation before this.
- **G-REC-1 (before ANY benchmark execution task is created):** owner reviews the
  corrected lifecycle + DEC-7/DEC-8 and declares it the valid resumable execution state
  — the declaration the halted run never had. The G-REC-1 checklist includes the DEC-8
  debt list: (i) deepseek_judge.py judge-ledger policy task, (ii) the two red
  `test_deepseek_provider.py` tests task, (iii) recipe.toml disposition. Only then may
  B0 live preflight proceed under the lifecycle's pre-existing **G0** (DeepSeek
  credential, `$1.00` envelope) and **G1** (recorded `N`, provider identity, ledger
  closed).
- **G-JUDGE (unchanged, post-B_N):** separate BSC judging session over frozen artifacts,
  Kimi judge harness/model, no DUT rerun, no evaluation-ledger draw.

## 10. Explicit non-goals

- No edit to the master plan, backend/, frontend/, `tests/` (incl. `deepseek_judge.py`
  and the two red provider tests), recipes/, manifests, `comparison-Istara-pi/`, or any
  report.
- No rewriting of historical ledger entries or deletion of DEC-5/DEC-6 text.
- No reuse of the halted run's 2-1 tally, its open tasks, or its uncommitted artifacts
  as governing state — and no recovery consensus seal that mixes plan blobs (AC-8).
- No live model calls, no DeepSeek/Kimi invocation, no B0/B1…B_N execution, no spend.
- No production Istara routing, model-selection, or default changes.
