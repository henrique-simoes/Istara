# Plan B — Quiesce, re-baseline, and apply one scoped Pi benchmark contract correction

- **Task:** `PI-BENCH-RECOVERY-20260722-PLAN-B`
- **Role:** `pi-bench-recovery-20260722-architect-b`
- **Spec:** `CF-SPEC-8`
- **Pipeline:** `PI-BENCH-RECOVERY-20260722`
- **Lifecycle:** `docs/build-stream/2026-07-22-pi-benchmark.md`
- **Scope:** recovery planning only. This plan does not authorize implementation, benchmark
  execution, live model/provider calls, judging, or changes to the master plan.

## 1. Recovery decision

The prior `PI-BENCH-ROLE-CORRECTION-20260722` pipeline must not be resumed. Its Plan A/B/C
files, votes, CF evidence, and lifecycle entries are historical evidence only. They are useful
as an edit inventory and risk register, but none is a valid consensus winner because the run
ended `HALTED-CONSENSUS-INVALID-PLAN` while concurrent fixers and planners were changing the
shared worktree and lifecycle.

The smallest safe recovery is a new owner-approved, documentation-only correction of exactly:

1. `docs/build-stream/2026-07-22-pi-benchmark.md`; and
2. `docs/build-stream/conductor-instructions/pi-benchmark-deepseek-moa-execution.md`.

Do not rewrite or recommit the old Plan A/B/C slots. Do not edit the master plan, correction
brief, recovery brief, recipes, benchmark Python, tests, manifests, reports, backend, frontend,
or generated feature documentation. The old plans may be cited for their grounded stale-text
inventory, but the implementer must re-read current files under the repository completion lock
and derive the final patch from the recovery winner and user-authoritative contract.

## 2. Evidence-backed current state

### 2.1 Reusable evidence

- The lifecycle's Goals and top-level wave/provider contract already make Istara's original
  loop and Pi adaptation the DUT arms, route live evaluation through Istara to DeepSeek, retain
  the cumulative `$1.00` cap, and reserve Kimi for later judging.
- The remaining-wave work order already carries most of the correct DUT, DeepSeek, MoA,
  fail-closed budget, and Kimi separation. It needs reconciliation, not replacement.
- All three historical correction plans identify the same core active-text defect: the embedded
  winning plan still contains Kimi-as-evaluation and DeepSeek-as-judge/shared-judge-ledger
  language. They also agree that append-only ledger history must remain untouched.
- The historical plans' strongest reusable details are the active-text inventory, the seven-pack
  coverage list, requested-versus-served MoA evidence, the frozen-artifact judging barrier, and
  path-scoped commit discipline. Line numbers and revision claims are not reusable without a
  fresh read because the lifecycle advanced to `L-34` during that run.

### 2.2 State that blocks implementation now

- `conductor.py status --brief` reported the recovery pipeline as `converged=False`,
  `daemon=up`, with active sessions `189`, `190`, and `191`. Those are the three current
  recovery architects and are legitimate concurrent writers during consensus planning, but
  they violate the required no-shared-writer condition for implementation.
- The lifecycle Status Block still says the prior role-correction votes should be tallied and
  points to `L-34`. It is stale relative to this recovery pipeline and cannot be treated as an
  implementation instruction.
- CF still reports older sessions `173`, `174`, `175`, `177`, and `183` as `active`, although
  the process inspection showed only the recovery conductor and recovery worker wrappers. These
  are stale state until runner/process polling proves otherwise and the sessions are terminally
  reconciled; they must not be assumed harmless solely because their PIDs were absent once.
- `.compass-forge/conductor/active-run.json` correctly points at `recovery-cast.json`, while
  `active-run (1).json` is a stale older marker. Only the canonical filename is authoritative;
  neither stale marker nor the prior cast may be used to resume correction implementation.
- The shared tree is already dirty: the historical Plan B and recipe are modified, and the
  work order, correction/recovery briefs, and historical Plan C are untracked. These paths
  belong to prior/current shared work and must not be swept into a recovery commit.
- The recovery cast itself includes an `implement` stage. Therefore consensus completion alone
  is unsafe: the conductor must be stopped at the consensus boundary unless owner approval for
  the separate documentation implementation has already been recorded.

## 3. Authoritative contract to retain

Every corrected active instruction must state the following roles without provider-role drift:

1. **DUT:** Istara's original agentic loop and the Pi adaptation run identical scenario inputs;
   Istara remains the evaluated system.
2. **Evaluation backend:** every live DUT backend call traverses Istara's API/dispatcher and
   uses the configured DeepSeek API route under one cumulative `budget_cap_usd=1.00`. Direct
   DeepSeek calls are not a substitute for either Istara arm. Kimi, Claude, Codex, local models,
   and open-source routes are forbidden as DUT providers for this run.
3. **MoA:** `self_moa` and `full_ensemble` measure Istara's existing dispatcher, validation,
   output-processing, and Research Spine behavior. Durable evidence records requested and served
   route identity, requested and served ensemble width, reconciliation/output status, and any
   downgrade as `degraded`, `blocked`, or `not_runnable`. No production route/default changes.
4. **Post-run judge:** only after B0 and all immutable-manifest B1…B_N units are terminal and the
   evaluation ledger is reconciled/closed may a separate BSC session use Kimi as the intended
   judge harness/model over frozen artifacts. It emits `report.md`, `report.html`,
   `scorecard.json`, and per-judgment outputs without rerunning the DUT, making benchmark-provider
   calls, or consuming evaluation budget.
5. **BSC workers:** planners, implementers, reviewers, and remediators are orchestration
   infrastructure, not DUT or judge evidence unless explicitly cast in the later judging session.

Both active documents must enumerate the seven evaluation packs: canonical 15-scenario contract
coverage, feature breadth, Research Spine lifecycle, A2A collaboration, prompt/injection probes,
usage/cost accounting, and MoA route/downgrade evidence. Preserve `max_processes=N`, the immutable
content-addressed manifest, disjoint/resumable B1…B_N units, fail-closed provider/budget behavior,
owner gates, and Istara's existing production routing/model-selection defaults.

## 4. Design

### 4.1 Establish a hard recovery barrier

The current recovery conductor may finish architect and judge tasks, record one new
`consensus_result`, and identify a recovery winner. It must not auto-dispatch the cast's
implementation stage. At the consensus boundary:

1. stop the recovery conductor cleanly;
2. prove `daemon=down`;
3. prove there are no recovery or older worker processes;
4. poll/reconcile every non-terminal project actor session and distinguish stale CF rows from
   live processes;
5. confirm the canonical `active-run.json` is no longer treated as an executable resume marker;
6. capture a new `git status --short` baseline; and
7. obtain explicit owner approval for the documentation-only implementation task.

If any worker, fixer, reviewer, conductor, or lifecycle writer is still active, implementation
remains blocked. Do not solve the collision by killing unknown processes, deleting conductor
state, or rewriting CF rows; use the conductor's clean stop and CF actor lifecycle commands.

### 4.2 Re-baseline instead of replaying the invalid consensus

After the barrier, the one implementer reads the current lifecycle Status Block, Decision log,
first historical ledger boundary, last real `### L-*` heading, both correction/recovery briefs,
the current work order, the selected recovery plan, current CF evidence, and the scoped diff.
It verifies each historical inventory item against current text. The implementer may reuse
wording or checks from old plans only when the fresh read still supports them; it must not copy a
historical consensus marker or claim the old vote tally is valid.

### 4.3 Apply one prospective two-document correction

Under `repo_lock.completion_lock`, the sole implementer:

- reconciles the lifecycle's active forward-looking plan, acceptance, commands, risks, gates,
  and non-goals to the five-role contract;
- adds the same role canon and seven-pack inventory to the work order;
- adds the terminal frozen-artifact barrier and requested-versus-served MoA proof;
- appends the next available decision that prospectively supersedes only the stale role clauses
  in DEC-5/DEC-6 without rewriting either decision;
- appends exactly one task-marked recovery implementation ledger entry and refreshes the Status
  Block from the current locked read; and
- commits only the lifecycle and work-order paths with `repo_lock.commit_paths`.

Historical `L-*` entries remain byte-preserved. Existing executable DeepSeek-judge/shared-ledger
apparatus under `tests/pi_benchmark/` is explicitly recorded as non-conforming architecture debt
and cannot satisfy the future Kimi artifact-only judge contract, but it is not changed in this
documentation task. Any executable migration or retirement gets a separate owner-approved task
with its own tests and security/architecture gates.

### 4.4 Separate later live-evaluation and judging gates

Documentation correction does not authorize B0, B1…B_N, DeepSeek reachability, server startup,
or Kimi judging. A later evaluation task requires a new owner approval after the corrected docs
pass independent review, the process state is quiescent, B0 offline artifacts and immutable
manifest are ready, and a worst-case cumulative DeepSeek cost projection proves the `$1.00` cap.
The Kimi judging session requires a still-later terminality check over the frozen artifact index
and closed evaluation ledger; it cannot share the evaluation conductor or budget.

## 5. Task breakdown

| ID | Task | Files/state | Depends on | Definition of ready |
|---|---|---|---|---|
| R-B1 | Complete recovery planning/judging and record a new recovery `consensus_result`; do not reuse the prior result | CF state only | — | Plans A/B/C for this recovery are terminal and judges use frozen candidate revisions |
| R-B2 | Stop at the consensus boundary and audit daemon, processes, actors, marker, and dirty tree | process/CF state only | R-B1 | No implementation task has been launched |
| R-B3 | Obtain explicit owner approval for the two-document implementation and record it as CF evidence/decision | CF state only | R-B2 | `daemon=down`, no worker processes, stale sessions reconciled, dirty baseline captured |
| R-B4 | Re-read current governing artifacts under `completion_lock` and produce the exact active-text edit inventory | no mutation yet | R-B3 | Exactly one implementer; no shared lifecycle writers |
| R-B5 | Reconcile active lifecycle and work order; append prospective decision and one ledger entry | lifecycle; work order | R-B4 | Fresh inventory confirms the two-file scope is sufficient |
| R-B6 | Commit only the two files via `repo_lock.commit_paths`; run lexical, invariant, history, and commit-scope checks | same two files | R-B5 | Unrelated dirty/untracked paths match the captured baseline |
| R-B7 | Independent review of the two-file diff and immediate role seams; remediate findings serially | CF evidence; same two files only if needed | R-B6 | Implementer is no longer active; reviewer sees immutable commit/evidence capsule |
| R-B8 | Ask for separate owner approval for B0/live evaluation; later freeze terminal artifacts before a separate Kimi judging cast | separate future tasks | R-B7 | Docs review passes; no open findings; live cost/credential/process gates satisfied |

R-B1 through R-B3 are recovery control-plane tasks. R-B4 through R-B7 are a later
owner-approved documentation correction. R-B8 is not part of recovery implementation.

## 6. Acceptance criteria

- **AC-1 — no invalid resume:** Given the historical role-correction run, when recovery begins,
  then no old consensus marker, vote tally, status next-action, or plan slot is used as execution
  authority; a new recovery `consensus_result` identifies the selected plan.
- **AC-2 — single-writer invariant:** Given documentation implementation is about to start, then
  exactly one conductor has owned recovery, that conductor is stopped at the consensus boundary,
  no worker/fixer/reviewer processes remain, non-terminal actor rows are reconciled, and exactly
  one implementer owns the lifecycle lock.
- **AC-3 — owner gate:** No implementation task starts without explicit owner approval of the
  two-document scope. No server, model, DeepSeek/Kimi call, B0/B1…B_N run, or spend occurs without
  the separate live-evaluation approval and required cost/credential gates.
- **AC-4 — scope:** The implementation commit contains exactly the lifecycle and remaining-wave
  work order. Historical plan slots, master plan, recipes, code, tests, manifests, and reports are
  unchanged.
- **AC-5 — role consistency:** Both active documents identify Istara original-versus-Pi as the
  DUT, DeepSeek only behind Istara as evaluation backend, existing Istara MoA/Research Spine as
  measured behavior, Kimi as terminal artifact-only judge, and ordinary BSC workers as
  orchestration.
- **AC-6 — seven packs and invariants:** Both documents enumerate all seven packs and preserve
  `budget_cap_usd=1.00`, `max_processes=N`, immutable/resumable waves, fail-closed semantics, and
  unchanged production routing/defaults.
- **AC-7 — history:** Historical DEC/L entries are byte-preserved. One new decision and one
  task-marked ledger entry explain the prospective correction and current state.
- **AC-8 — honest executable debt:** Existing DeepSeek judge/shared-ledger code is not described
  as satisfying Kimi artifact-only judging and is assigned to a separate future task.
- **AC-9 — review:** An independent reviewer passes the exact two-file commit or all findings are
  fixed and delta-reviewed before any evaluation approval is requested.

## 7. Exact verification commands

Run from `<repo-root>-pi-replacement`. The first group is the mandatory
pre-implementation barrier; it must be green before any file edit.

```bash
# Recovery must have a new consensus result; inspect evidence for the recovery tasks only.
compass-forge task evidence-list PI-BENCH-RECOVERY-20260722-JUDGE-A
compass-forge task evidence-list PI-BENCH-RECOVERY-20260722-JUDGE-B
compass-forge task evidence-list PI-BENCH-RECOVERY-20260722-JUDGE-C

# Stop cleanly at the consensus boundary, then prove no conductor is running.
python3 /Users/user/Documents/Skills/build-stream-conductor/scripts/conductor.py stop \
  --project-root <repo-root>-pi-replacement
python3 /Users/user/Documents/Skills/build-stream-conductor/scripts/conductor.py status \
  --project-root <repo-root>-pi-replacement --brief

# Expected after stop: daemon=down and no conductor/worker command rows.
ps -ax -o pid=,etime=,command= | \
  rg 'build-stream-conductor|worker\.example\.sh|worker\.sh' | rg -v 'rg ' || true

# Inspect and reconcile non-terminal sessions; validate stale rows against actor processes.
compass-forge actor sessions
sqlite3 -header -column .compass-forge/state.sqlite3 \
  "select id,task_id,role,status,updated_at from actor_sessions where status not in ('done','canceled','failed') order by id;"
sqlite3 -header -column .compass-forge/state.sqlite3 \
  "select * from actor_processes order by id;"

# Canonical marker/cast audit and shared-tree baseline.
sed -n '1,80p' .compass-forge/conductor/active-run.json
git status --short --branch
git diff --stat
```

After owner approval and inside the single-implementer critical section:

```bash
# Re-read current authority and locate actual append-only boundaries; never trust old lines.
sed -n '1,120p' docs/build-stream/2026-07-22-pi-benchmark.md
rg -n '^DEC-|^### L-|consensus-winning-plan|HALTED|Kimi|DeepSeek|budget_cap_usd|max_processes' \
  docs/build-stream/2026-07-22-pi-benchmark.md
sed -n '1,180p' \
  docs/build-stream/conductor-instructions/pi-benchmark-deepseek-moa-execution.md

# Patch hygiene and exact implementation-path diff.
git diff --check -- \
  docs/build-stream/2026-07-22-pi-benchmark.md \
  docs/build-stream/conductor-instructions/pi-benchmark-deepseek-moa-execution.md
git diff -- \
  docs/build-stream/2026-07-22-pi-benchmark.md \
  docs/build-stream/conductor-instructions/pi-benchmark-deepseek-moa-execution.md

# Both active documents must contain the roles, outputs, and all seven packs.
for file in \
  docs/build-stream/2026-07-22-pi-benchmark.md \
  docs/build-stream/conductor-instructions/pi-benchmark-deepseek-moa-execution.md; do
  for term in 'original agentic loop' 'Pi adaptation' 'DeepSeek' 'API/dispatcher' \
              'Kimi' 'report.md' 'report.html' 'scorecard.json' 'per-judgment' \
              'canonical 15-scenario' 'feature breadth' 'Research Spine' 'A2A' \
              'prompt/injection' 'usage/cost' 'MoA route/downgrade'; do
    rg -q "$term" "$file" || { echo "missing: $term in $file"; exit 1; }
  done
done

# Inspect all ambiguous provider-role language. Hits are allowed only in byte-preserved
# historical DEC/L text or explicit prospective supersession, never as active instructions.
rg -n -i \
  'provider kimi|--provider kimi|kimi[- ]only evaluation|kimi evaluation (credential|provider|adapter)|judge call through deepseek|deepseek.{0,40}judge' \
  docs/build-stream/2026-07-22-pi-benchmark.md \
  docs/build-stream/conductor-instructions/pi-benchmark-deepseek-moa-execution.md

# Preserved mechanics and non-mutation of production defaults remain explicit.
rg -n 'budget_cap_usd=1\.00|max_processes=N|immutable|resumable|fail.closed|production.*(routing|defaults|model-selection)' \
  docs/build-stream/2026-07-22-pi-benchmark.md \
  docs/build-stream/conductor-instructions/pi-benchmark-deepseek-moa-execution.md

# Before commit, compare global status with the captured baseline and stage no unrelated path.
git status --short
git diff --cached --name-only

# After repo_lock.commit_paths, replace <task-commit>; expected output is exactly two paths.
git diff-tree --no-commit-id --name-only -r <task-commit>
```

No backend/frontend test, benchmark run, feature-doc regeneration, server startup, model load,
or provider probe belongs to this documentation task. If the patch touches executable code,
tests, recipes, security controls, or feature behavior, stop and create a new scoped task with
the applicable tests, feature-doc generation, CF gates, and security benchmark.

## 8. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Recovery cast auto-launches `implement` immediately after consensus | Unapproved mutation repeats the collision | Stop the conductor at the consensus boundary; require recorded owner approval before a separate implementation claim |
| Stale CF `active` sessions hide a real writer | Concurrent lifecycle/plan edits corrupt history | Poll actor/process state, reconcile terminal statuses, and require both daemon/process and CF checks before editing |
| Stale lifecycle Status Block or old consensus marker is trusted | Invalid plan becomes execution authority | New recovery `consensus_result`; fresh locked read; prospective decision/ledger entry |
| Historical plan content is copied wholesale | Stale line anchors or broadened scope enter the correction | Reuse only verified inventory/contract ideas; regenerate the patch from current files and recovery winner |
| Shared dirty tree contaminates the commit | User or sibling changes are committed | Capture baseline, use `completion_lock` plus `commit_paths`, and audit the exact commit paths |
| Append-only DEC/L history is rewritten | Audit trail becomes false | Never edit old entries; add a prospective superseding decision and one new task-marked ledger entry |
| DeepSeek/Kimi roles drift again | Benchmark no longer measures Istara or judge spends evaluation budget | Identical five-role canon in both docs; mechanical ambiguity audit; independent review |
| Requested MoA routes are mistaken for served routes | Downgraded behavior looks like successful ensemble evidence | Require requested-versus-served identities/width and degraded/blocked/not-runnable disposition |
| Executable DeepSeek judge path is silently treated as compliant | Documentation overclaims readiness | Record as non-conforming debt and create a separate owner-approved code task; do not use it for Kimi judging |
| Documentation correction is mistaken for evaluation approval | Live calls or spend occur prematurely | Separate owner gates for docs implementation, DeepSeek evaluation, and terminal artifact-only Kimi judging |

## 9. Rollback

The implementation is one path-scoped documentation commit. If review rejects it, revert that
commit without touching unrelated dirty paths. Because Decision log and Ledger records are
append-only, record the rollback prospectively with a new decision/ledger entry rather than
deleting or rewriting the rejected correction. The rollback does not mutate runtime state,
credentials, manifests, budget ledgers, model configuration, benchmark artifacts, or reports.

If the recovery control plane itself collides before implementation, stop the conductor cleanly,
leave all recovery tasks/evidence open and intact, record the collision, and start a fresh
planning recovery only after `daemon=down`, no worker processes, reconciled actor state, and an
unchanged dirty-tree baseline are proven. Never resume `PI-BENCH-ROLE-CORRECTION-20260722`.

## 10. Explicit non-goals

- No edit to the lifecycle, work order, master plan, prior plan slots, code, tests, recipes,
  manifests, reports, or generated docs in this architect stage.
- No cleanup or deletion of stale conductor files, CF rows, user changes, or historical records.
- No B0/B1…B_N run, server start, DeepSeek/Kimi call, local model load, or evaluation spend.
- No production routing/default change and no benchmark-only replacement for Istara's
  dispatcher, validation, output processing, or Research Spine.
- No post-run judging until immutable evaluation artifacts and the cumulative ledger are
  terminal and a separate judging session is explicitly authorized.
