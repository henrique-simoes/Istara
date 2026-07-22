# Plan B — Contract-first correction of Pi benchmark execution and judging roles

- **Task:** `PI-BENCH-ROLE-CORRECTION-20260722-PLAN-B`
- **Role:** `pi-bench-role-correction-20260722-architect-b`
- **Spec:** `CF-SPEC-8`
- **Pipeline:** `PI-BENCH-ROLE-CORRECTION-20260722`
- **Scope:** planning and documentation only; the implementation changes the Pi benchmark
  lifecycle and its Conductor work-order, not the master plan, benchmark code, or Istara
  production routing.

## 1. Outcome and constraints

The correction must leave one unambiguous operating contract for all later workers:

| Role | Authority after correction | Prohibited interpretation |
|---|---|---|
| Device under test (DUT) | Istara's original agentic loop and Pi adaptation receive identical scenario inputs; their captured behavior is compared. | A provider model, Conductor worker, or judge is not the DUT. |
| Evaluation backend | Live calls from both Istara arms traverse Istara's API/`AgenticDispatcher` and use the configured DeepSeek API route under the existing cumulative `$1.00` evaluation ledger. | The runner must not call DeepSeek directly as a substitute for exercising Istara. |
| MoA behavior | `self_moa` and `full_ensemble` exercise Istara's existing dispatcher/validation behavior. Requested and served route identities, coder/sample width, and downgrades are durable evidence. | The benchmark must not modify production defaults or call a benchmark-only ensemble implementation. |
| Post-run judge | Only after B0 and B1…B_N are terminal, a separate Build Stream Conductor session uses Kimi as the intended judge harness/model over immutable durable artifacts. It emits `report.md`, `report.html`, `scorecard.json`, and per-judgment outputs. | The judge must not rerun the DUT, make new benchmark-provider calls, or draw from the evaluation ledger. |
| BSC execution workers | Implementers, reviewers, and remediators orchestrate the benchmark and preserve evidence. | Their model output is neither DUT evidence nor judge evidence unless they are explicitly cast in the separate post-run judging session. |

Preserve without semantic change: `budget_cap_usd=1.00`, `max_processes=N`, the immutable
content-addressed manifest, disjoint/resumable B1…B_N shards, fail-closed provider and
budget behavior, owner gates, and Istara's existing production model-selection defaults.

## 2. Verified current-state problem

The lifecycle already has correct top-level Goals and a mostly correct “Wave and provider
contract,” but its embedded forward-looking winning plan remains internally inconsistent:

- the B0/B-wave task table, acceptance criteria, commands, risks, gates, and non-goals
  still call Kimi the evaluation provider and use `--provider kimi`;
- DEC-5 routes both evaluation and judge calls through DeepSeek and charges judges to the
  shared ledger;
- DEC-6 then routes evaluation through Kimi and leaves the judging cast open-ended;
- the newer top-level contract instead requires DeepSeek to serve live calls made through
  Istara and reserves Kimi for a separate artifact-only judging session.

The execution work-order is closer to the intended contract, but the correction should
make the five roles above an explicit normative block rather than rely on scattered prose.
It must also enumerate all required evaluation packs in both documents.

Append-only ledger entries are historical evidence, including entries that describe the
old role assignment. They must not be rewritten. A new decision and ledger entry will
supersede their forward-looking meaning.

## 3. Design

### 3.1 Establish one normative role block

Add a compact “Authoritative role separation” block near the lifecycle's top-level wave
contract and near the start of
`docs/build-stream/conductor-instructions/pi-benchmark-deepseek-moa-execution.md`.
Use the same five numbered statements in both places. Future workers should not need to
infer roles from provider names in individual commands.

The block must distinguish route from DUT: DeepSeek serves model calls, but the benchmark
continues to measure Istara's original loop versus its Pi adaptation through Istara's own
API/dispatcher. It must also say that route identity is observed, not selected by changing
production defaults.

### 3.2 Reconcile all active lifecycle instructions

Within active, forward-looking lifecycle material, replace stale Kimi-as-evaluation and
DeepSeek-as-judge language consistently across:

- the program diagram and component descriptions;
- B0/B1…B_N task rows;
- acceptance criteria;
- verification examples and preflight/wave commands;
- risks and mitigations;
- owner gates and explicit non-goals.

Commands should name the benchmark's supported DeepSeek provider/model arguments exactly
as implemented at execution time, while the prose retains “configured DeepSeek API route”
as the contract. The correction must not introduce a direct provider call: commands still
invoke the Istara benchmark runner, whose live driver traverses Istara's API/dispatcher.

Do not edit prior `### L-*` entries. Do not rewrite the historical content of DEC-5 or
DEC-6 in a way that hides the change; supersede them explicitly in a new decision.

### 3.3 Make MoA evidence part of the DUT contract

The corrected lifecycle and work-order must state that `self_moa` and `full_ensemble` are
Istara dispatcher/validation modes. Every applicable record captures:

- requested provider/model/endpoint slots and requested coder/sample width;
- served provider/model/endpoint identities and successful response count;
- engine arm (`legacy` or `pi`), reconciliation status, and route evidence handles;
- any downgrade to fewer routes/coders or another mode as `degraded`, `blocked`, or
  `not_runnable`, never a successful full-ensemble result.

This is an observational benchmark contract only. No production route, fallback, model
catalog, default, or validation policy is changed.

### 3.4 Separate evaluation closure from judging startup

Add an explicit barrier between the phases:

1. B0 and every manifest unit in B1…B_N reach a terminal state.
2. The immutable manifest and evaluation ledger are reconciled and closed; all seven
   evaluation packs are accounted for.
3. A durable artifact index with hashes and redacted route evidence is frozen.
4. A new BSC judging session is launched with Kimi as intended judge harness/model.
5. The judge reads only that artifact packet and writes the four required report classes.

The separate judging session must have no benchmark credential requirement, no DUT runner
permission, and no evaluation-ledger reservation path. Deterministic report aggregation
may consume the judge outputs, but may not manufacture missing DUT records.

### 3.5 Decision and ledger treatment

Append the next decision (`DEC-7` if still available when the implementer acquires the
lock) with the five-role matrix and a precise supersession statement:

- DEC-5 remains authoritative for B0/B1…B_N process waves, `max_processes=N`, DeepSeek
  evaluation routing, and the cumulative `$1.00` cap, but not for DeepSeek judging or
  charging post-run judging to the evaluation ledger.
- DEC-6 is superseded for Kimi-as-evaluation and open-ended judge selection; its durable
  separation of evaluation from judging remains valid.

Under `repo_lock.completion_lock`, append exactly one task-marked ledger entry and update
the Status Block's `last` pointer without changing the current remediation stage or
overwriting concurrent next-action state. Commit only the lifecycle and work-order paths
with `repo_lock.commit_paths`; never stage unrelated shared-worktree changes.

## 4. Task graph

| ID | Task | Files | Depends on | Definition of ready |
|---|---|---|---|---|
| RC-B1 | Capture a pre-edit role/invariant audit and the shared-worktree path baseline. | none | — | Current lifecycle/work-order read; stale active references and pre-existing dirty paths listed. |
| RC-B2 | Add the identical normative five-role block and seven-pack inventory to both documents. | lifecycle; execution work-order | RC-B1 | Exact role wording agreed from the task payload. |
| RC-B3 | Reconcile every forward-looking lifecycle occurrence in diagram, tasks, acceptance, commands, risks, gates, and non-goals. | lifecycle | RC-B2 | Active-vs-historical regions identified; no ledger rewrite required. |
| RC-B4 | Add the MoA observation contract and evaluation-to-judging terminal barrier. | lifecycle; execution work-order | RC-B2 | Existing manifest, ledger, and route-evidence terminology preserved. |
| RC-B5 | Append the superseding decision and one ledger entry; refresh only the concurrency-safe Status Block fields. | lifecycle | RC-B2..RC-B4 | Lock acquired; latest DEC/L number and current status re-read inside lock. |
| RC-B6 | Run lexical, invariant, path-scope, and diff-hygiene checks; record CF command evidence. | none | RC-B5 | Only the two intended implementation paths are staged/committed for this task. |
| RC-B7 | Independent review of the changed forward-looking regions and adjacent role seams. | none | RC-B6 | Implementer evidence and scoped diff available. |

RC-B2 through RC-B6 are one small documentation implementation task. RC-B7 is a separate
review task; it must not silently repair findings in the review stage.

## 5. Acceptance criteria

- **AC-1 — DUT identity:** Given either benchmark arm runs a live scenario, when the
  lifecycle/work-order describes the run, then it identifies Istara's original loop or Pi
  adaptation as the DUT and requires identical scenario inputs and captured behavior.
- **AC-2 — served route:** Given a DUT call needs a model, when it is dispatched, then the
  documents require the configured DeepSeek API route through Istara's API/dispatcher,
  charge it to the one cumulative `$1.00` ledger, and forbid a direct DeepSeek substitute
  or provider fallback.
- **AC-3 — MoA provenance:** Given `self_moa` or `full_ensemble` is requested, when results
  are recorded, then requested-versus-served route identity and width are present and any
  downgrade is degraded/blocked/not-runnable rather than success.
- **AC-4 — judge separation:** Given B0 or any B1…B_N unit is non-terminal, when judging is
  considered, then the judging session cannot start. Once all evaluation artifacts and the
  ledger are terminal/closed, the separate Kimi BSC judge reads durable artifacts only,
  makes no new benchmark-provider calls, and produces `report.md`, `report.html`,
  `scorecard.json`, and per-judgment outputs.
- **AC-5 — worker identity:** The work-order explicitly says ordinary BSC implementer,
  reviewer, and fixer model output is orchestration evidence, not DUT/judge evidence.
- **AC-6 — pack completeness:** Both documents enumerate canonical 15-scenario contract
  coverage, feature breadth, Research Spine lifecycle, A2A collaboration,
  prompt/injection probes, usage/cost accounting, and MoA route/downgrade evidence.
- **AC-7 — preserved mechanics:** The correction retains `budget_cap_usd=1.00`,
  `max_processes=N`, immutable manifest hashing, disjoint/resumable B1…B_N waves,
  fail-closed semantics, and unchanged production Istara model-selection behavior.
- **AC-8 — history and scope:** Historical ledger entries are byte-preserved; a new
  decision/ledger entry records the correction; the implementation task changes only the
  lifecycle and execution work-order under `docs/build-stream/`.

## 6. Verification

Run from `/Users/user/Documents/Istara-main-pi-replacement`; use the repository's actual
current paths and do not interpret unrelated dirty files as this task's edits.

```bash
# Diff hygiene for the two implementation paths.
git diff --check -- \
  docs/build-stream/2026-07-22-pi-benchmark.md \
  docs/build-stream/conductor-instructions/pi-benchmark-deepseek-moa-execution.md

# Path-scoped staging audit inside the lock; expected output is exactly these two paths.
git diff --cached --name-only -- \
  docs/build-stream/2026-07-22-pi-benchmark.md \
  docs/build-stream/conductor-instructions/pi-benchmark-deepseek-moa-execution.md

# No active Kimi-as-evaluation command or direct-provider wording.
rg -n -i --glob '!docs/build-stream/2026-07-22-pi-benchmark.md' \
  '(^|[^a-z])(provider kimi|--provider kimi|kimi[- ]only evaluation|kimi evaluation (provider|credential|adapter|envelope))' \
  docs/build-stream/conductor-instructions/pi-benchmark-deepseek-moa-execution.md

# Inspect lifecycle hits manually by region: any hit before the first historical ledger
# entry must be judge-only or an explicit supersession statement.
rg -n -i 'provider kimi|--provider kimi|kimi[- ]only evaluation|kimi evaluation (provider|credential|adapter|envelope)|deepseek.{0,40}judge|judge.{0,40}deepseek' \
  docs/build-stream/2026-07-22-pi-benchmark.md

# The role and output vocabulary must exist in both active documents.
for file in \
  docs/build-stream/2026-07-22-pi-benchmark.md \
  docs/build-stream/conductor-instructions/pi-benchmark-deepseek-moa-execution.md; do
  rg -q 'original agentic loop' "$file"
  rg -q 'Pi adaptation' "$file"
  rg -q 'DeepSeek' "$file"
  rg -q 'Istara.{0,40}(API|dispatcher)|API/dispatcher' "$file"
  rg -q 'Kimi' "$file"
  rg -q 'report\.md' "$file"
  rg -q 'report\.html' "$file"
  rg -q 'scorecard\.json' "$file"
  rg -q 'per-judgment' "$file"
done

# Required seven-pack vocabulary in both documents.
for file in \
  docs/build-stream/2026-07-22-pi-benchmark.md \
  docs/build-stream/conductor-instructions/pi-benchmark-deepseek-moa-execution.md; do
  for term in 'canonical 15-scenario' 'feature breadth' 'Research Spine' 'A2A' \
              'prompt/injection' 'usage/cost' 'route/downgrade'; do
    rg -q "$term" "$file" || { echo "missing: $term in $file"; exit 1; }
  done
done

# Preserved mechanics and explicit non-mutation of production defaults.
rg -n 'budget_cap_usd=1\.00|max_processes=N|immutable|resumable|production.*defaults|model-selection' \
  docs/build-stream/2026-07-22-pi-benchmark.md \
  docs/build-stream/conductor-instructions/pi-benchmark-deepseek-moa-execution.md

# Scoped task commit audit after commit. Replace <task-commit> with the resulting SHA;
# expected paths are exactly the lifecycle and work-order.
git diff-tree --no-commit-id --name-only -r <task-commit>
```

No backend/frontend test suite is required for a wording-only correction. If implementation
touches provider, dispatcher, validation, benchmark Python, or any production file, stop:
that is scope expansion and requires a new task plus the applicable architecture/security
verification rather than being folded into this correction.

## 7. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Blind global replacement rewrites historical ledger evidence. | Audit trail becomes false. | Bound edits to active sections; preserve every prior `### L-*` entry; supersede via new DEC/L entry. |
| DeepSeek is described as the DUT rather than the serving route. | Benchmark no longer measures Istara. | Lead both documents with the five-role matrix and explicitly require the Istara API/dispatcher path. |
| A “configured route” phrase silently changes production defaults. | Production behavior changes outside experiment scope. | State route observation/approval is benchmark-scoped; prohibit model catalog/default/fallback changes. |
| The Kimi judging session accidentally reruns scenarios or spends from the evaluation ledger. | Biased results and cap ambiguity. | Require terminal artifact barrier; artifact-only inputs; no DUT credential/runner permission; ledger already closed. |
| MoA selected endpoints are mistaken for served routes. | Downgraded runs look successful. | Require successful served-route evidence and requested width; selected-but-failed routes remain provenance only. |
| Shared-worktree status contains unrelated code changes. | Scope audit or commit captures another worker's files. | Snapshot baseline; lock before final read/append/stage; use explicit path-scoped commit; audit the task commit, not global dirtiness. |
| Concurrent lifecycle append changes DEC/L numbering or status. | Duplicate numbering or stale Status Block. | Re-read the latest decision, ledger heading, and Status Block only after acquiring `completion_lock`; update minimally. |
| Existing benchmark code still contains a DeepSeek judge path. | Docs and executable behavior may diverge after this docs-only correction. | Treat it as explicit architecture debt: the corrected work-order bars that path from the post-run judge; create a separate code task if executable judging still consumes DeepSeek or the evaluation ledger. |

## 8. Rollback

The implementation is one path-scoped documentation commit. Roll back by reverting that
commit; no schema, model setting, provider credential, runtime state, or benchmark artifact
is mutated. Because decision and ledger records are append-only, a rollback should append a
new superseding decision/ledger entry explaining the revert rather than erase the original
correction history.

## 9. Non-goals

- Do not edit `docs/build-stream/plans/2026-07-20-pi-full-replacement-master-plan.md`.
- Do not edit backend, frontend, benchmark Python, tests, recipes, manifests, or reports.
- Do not start a server, load a model, call DeepSeek/Kimi, run a benchmark wave, or spend.
- Do not alter Istara's production engine/model defaults or provider fallback policy.
- Do not judge results during this correction; this stage only makes the later judging
  session's authority and prerequisites explicit.
