# Plan B r2 — Contract-first Pi benchmark role correction

- **Task:** `PI-BENCH-ROLE-CORRECTION-20260722-REPLAN-B-r2`
- **Role:** `pi-bench-role-correction-20260722-architect-b`
- **Spec:** `CF-SPEC-8`
- **Pipeline:** `PI-BENCH-ROLE-CORRECTION-20260722`
- **Lifecycle:** `docs/build-stream/2026-07-22-pi-benchmark.md`
- **Scope:** documentation-only correction of the Pi benchmark lifecycle and remaining-wave
  work-order. Do not edit the master plan, benchmark code, production code, routing defaults,
  manifests, reports, or historical ledger entries.

> **r2 correction note (grounded at `8fc982d8`).** This revision adds exact anchors for
> every active role contradiction and separates the required two-document correction from
> the adjacent stale operator/code surfaces. The latter are recorded as follow-up debt; they
> are not silently pulled into this documentation task. Source lines are planning anchors,
> not edit coordinates: the implementer must refresh them after acquiring the repository
> completion lock because the shared lifecycle is concurrently append-only.

## 1. Outcome and invariants

The implementation leaves one authoritative contract that every later benchmark worker can
apply without inferring roles from provider names:

| Concern | Authoritative role | Prohibited interpretation |
|---|---|---|
| DUT/evaluation | Run Istara's original agentic loop and Pi adaptation against identical scenario inputs and compare their captured behavior. | DeepSeek, Kimi, or a BSC worker is not the DUT. |
| Evaluation backend | Live model calls from both Istara arms traverse Istara's API/dispatcher and use the configured DeepSeek API route under one cumulative `$1.00` evaluation cap. | The runner may not call DeepSeek directly as a substitute for exercising Istara. |
| MoA | `self_moa` and `full_ensemble` exercise Istara's existing dispatcher/validation path. Record requested and served route identity and mark any downgrade `degraded`, `blocked`, or `not_runnable`. | Benchmark-only ensemble behavior and production-default changes are forbidden. |
| Post-run judge | After B0 and every B1…B_N unit are terminal, a separate BSC session uses Kimi as the intended judge harness/model over frozen durable artifacts. It emits `report.md`, `report.html`, `scorecard.json`, and per-judgment outputs. | The judge may not rerun the DUT, call a benchmark provider, or reserve/commit evaluation-ledger spend. |
| BSC workers | Implementation, review, and remediation workers are orchestration infrastructure. | Their outputs are not DUT or judge evidence unless explicitly cast in the separate judging session. |

The correction must preserve without semantic change:

- `budget_cap_usd=1.00` and the crash-safe cumulative evaluation ledger;
- `max_processes=N`, disjoint/resumable B1…B_N shards, and the immutable content-addressed
  manifest;
- fail-closed provider, usage, cost, route, and downgrade handling;
- existing owner gates and no unapproved live calls or model loading;
- Istara's production engine, provider, model-selection, fallback, catalog, and validation
  defaults.

## 2. Current-state audit

The lifecycle's top-level goals and wave/provider contract already identify DeepSeek as the
backend serving Istara evaluation calls and Kimi as the later judge. Its embedded active plan
still contradicts that contract in task rows, acceptance criteria, example commands, risks,
gates, non-goals, and decisions:

- active text still calls Kimi the evaluation adapter/credential/provider and includes
  `--provider kimi` examples;
- DEC-5 includes judge calls in the DeepSeek route and shared evaluation ledger;
- DEC-6 sends evaluation through Kimi and leaves the judging harness open-ended;
- the remaining-wave work-order is substantially role-correct but does not yet enumerate
  MoA route/downgrade evidence as a seventh evaluation pack or present the five roles as one
  normative block.

The grounded edit map is:

| Surface at `8fc982d8` | Current state | Planned disposition |
|---|---|---|
| Lifecycle lines 24–31 and 36–64 | Top-level Goals and wave/provider contract are already role-correct. | Preserve and use as the normative source for the active-plan rewrite. |
| Lifecycle lines 307–313 | B0/B-wave tasks call Kimi the evaluation adapter/provider and use `--provider kimi`. | Rewrite active task rows to DeepSeek-behind-Istara evaluation and a terminal artifact-only Kimi judge session. |
| Lifecycle lines 327–353 | Acceptance A3/A4/A7 assign Kimi to evaluation; POST-N names outputs without a full judge barrier. | Correct the provider identity and add manifest/ledger terminality plus frozen-artifact prerequisites. |
| Lifecycle lines 357–405 | Verification headings and commands use Kimi evaluation credentials and runner flags. | Use the supported DeepSeek route/model while retaining Istara runner/dispatcher execution. |
| Lifecycle lines 418–424 and 449–466 | Risks, G0/G1, and non-goals still describe Kimi-only evaluation. | Reconcile the forward-looking language; preserve cap, gates, and fail-closed semantics. |
| Lifecycle lines 484–503 | DEC-5 sends judges through DeepSeek/shared spend; DEC-6 sends evaluation through Kimi and leaves the judging cast open. | Leave DEC-5/DEC-6 immutable and append the next decision that prospectively supersedes only those role clauses. |
| Work-order lines 24–38 and 43–55 | DUT, DeepSeek evaluation route, artifact-only Kimi judging, and MoA downgrade rules are already correct. | Preserve; consolidate them as the normative five-role block for every future worker. |
| Work-order lines 71–82 | Six evaluation packs are named; MoA route/downgrade appears only as a judging criterion. | Enumerate all seven required evaluation packs explicitly and retain the artifact-only judging rule. |

Historical `### L-*` entries are evidence of what agents previously believed and must remain
byte-preserved. The implementation must append a new decision and ledger entry that supersede
the stale role assignments prospectively.

There are also adjacent contradictions outside the required two-document correction:

- `tests/pi_benchmark/README.md:73-76` advertises a DeepSeek judge that shares the
  evaluation ledger;
- `tests/pi_benchmark/deepseek_judge.py:3-7,84-89` implements and documents that same
  provider-backed/shared-ledger judge path.

Neither may be presented as satisfying the corrected Kimi artifact-only judging contract.
The implementation must identify them in the lifecycle/work-order as non-conforming legacy
apparatus and create one separately scoped follow-up task for their documentation/code
migration or retirement. This task must not edit either file, because doing so would expand a
role-contract documentation correction into executable benchmark behavior without its tests,
security trigger analysis, or independent review.

## 3. Design

### 3.1 One normative role block in both active documents

Add the five-role contract from section 1 near the lifecycle's top-level provider/wave
contract and near the beginning of
`docs/build-stream/conductor-instructions/pi-benchmark-deepseek-moa-execution.md`. The two
blocks must be semantically identical. Both must state that DeepSeek is a serving route behind
Istara, not the DUT, and that Kimi is reserved for the terminal artifact-only judging session.

Enumerate the same seven evaluation packs in both documents:

1. canonical 15-scenario contract coverage;
2. feature breadth;
3. Research Spine lifecycle;
4. A2A collaboration;
5. prompt/injection probes;
6. usage/cost accounting;
7. MoA route/downgrade evidence.

Keep any existing `depth` or internal scheduling labels when they map manifest work; the
seven-pack list is the external coverage contract, not permission to silently drop work.

### 3.2 Reconcile only active forward-looking lifecycle text

Within the active plan, update every stale Kimi-as-evaluation or DeepSeek-as-judge reference
across the diagram, component descriptions, B0/B-wave task table, acceptance, commands,
risks, gates, and non-goals. Supported runner examples use the existing CLI contract
`--provider deepseek --model deepseek-v4-pro` while still invoking Istara's benchmark runner.

Do not globally replace provider names. Kimi remains correct in judge-only text, DeepSeek
remains correct in evaluation-backend text, and historical ledger entries remain untouched.

### 3.3 Make MoA proof observational and fail closed

For every applicable `self_moa` or `full_ensemble` result, require durable capture of:

- requested provider/model/endpoint slots and requested sample/coder width;
- served provider/model/endpoint identities and successful response count;
- engine arm (`legacy` or `pi`), reconciliation state, and route evidence handles;
- rejected route evidence and any downgrade classification.

Selected or requested routes are not proof of service. A run with fewer served routes or
coders than requested cannot be recorded as successful full ensemble. This change documents
existing Istara behavior; it does not add a benchmark-only dispatcher or alter production
routing.

### 3.4 Add a terminal evaluation-to-judging barrier

The active lifecycle and work-order must enforce this sequence:

1. B0 and every immutable-manifest unit in B1…B_N reaches a terminal state.
2. The evaluation ledger is reconciled and closed, with all seven packs accounted for.
3. A frozen artifact index records hashes and redacted route-evidence handles.
4. A separate BSC judging session is launched with Kimi as the intended judge harness/model.
5. The judge reads only the frozen packet and writes `report.md`, `report.html`,
   `scorecard.json`, and per-judgment outputs.

The judging session has no DUT-runner permission, no benchmark-provider credential
requirement, and no evaluation-ledger reservation/commit path. Deterministic aggregation may
consume judgment files but may not fabricate missing DUT records.

### 3.5 Supersede, append, and commit safely

Append the next available decision number after re-reading the lifecycle under the repository
completion lock. At the audited snapshot this would be `DEC-7`, but the implementer must use
the actual next number under lock. The new decision must preserve DEC-5's
wave/process/cap choices while superseding its DeepSeek-judge/shared-judge-spend clause, and
preserve DEC-6's evaluation-to-judging separation while superseding its
Kimi-evaluation/open-judge clauses. Its decision text must explicitly bind all five roles,
all seven packs, the frozen-artifact barrier, and the adjacent non-conforming judge debt.

Do not edit historical ledger text. Under `repo_lock.completion_lock`, re-read the latest
decision, ledger number, and Status Block; append exactly one task-marked ledger entry and
refresh only the concurrency-safe status fields. Commit the lifecycle and work-order with
`repo_lock.commit_paths`. Never stage unrelated shared-worktree files.

## 4. Task graph

| ID | Task | Files | Depends on | Definition of ready |
|---|---|---|---|---|
| RC-B1 | Capture a pre-edit role/invariant audit and dirty-path baseline. | none | — | Lifecycle/work-order read; active stale references distinguished from historical ledger text; unrelated dirty paths recorded. |
| RC-B2 | Add the normative five-role block and seven-pack inventory to both documents. | lifecycle; work-order | RC-B1 | Exact task-payload roles are available; no provider inference required. |
| RC-B3 | Reconcile all active Kimi-evaluation and DeepSeek-judge references, including supported CLI examples. | lifecycle | RC-B2 | Active regions and first historical ledger boundary identified. |
| RC-B4 | Add requested-versus-served MoA evidence and the terminal artifact barrier. | lifecycle; work-order | RC-B2 | Existing manifest, ledger, route-evidence, and report vocabulary preserved. |
| RC-B5 | Record the README/DeepSeek-judge mismatch as out-of-scope debt, bar it from satisfying the post-run contract, and import one separately scoped cleanup task. | lifecycle; work-order; CF state only | RC-B2 | Exact contradictory anchors are refreshed; no benchmark or production code edit is required. |
| RC-B6 | Append the superseding decision and task ledger entry; refresh minimal status fields under lock. | lifecycle | RC-B2..RC-B5 | Lock acquired; latest decision/ledger/status re-read. |
| RC-B7 | Run lexical, invariant, diff-hygiene, and task-commit path checks; attach command evidence. | none | RC-B6 | Only lifecycle/work-order paths belong to the task commit. |
| RC-B8 | Independent delta review of changed active regions and immediate role seams. | none | RC-B7 | Scoped diff and evidence capsule available. |

RC-B2 through RC-B7 form one documentation implementation task. RC-B8 is a separate review
task; the reviewer reports findings rather than repairing them in-place.

## 5. Acceptance criteria

- **AC-1 — DUT identity:** Given either benchmark arm runs a scenario, when the documents
  describe the result, then Istara's original loop or Pi adaptation is the evaluated system,
  the scenario input is paired, and DeepSeek/Kimi/BSC workers are not called the DUT.
- **AC-2 — evaluation route:** Given a live DUT model call, when it is dispatched, then it
  traverses Istara's API/dispatcher, uses the configured DeepSeek route, reserves against the
  one cumulative `$1.00` evaluation ledger, and has no direct-provider substitute or fallback.
- **AC-3 — MoA provenance:** Given `self_moa` or `full_ensemble` is requested, when the
  record is finalized, then requested and served identities/widths are present and any
  shortfall is degraded, blocked, or not-runnable rather than successful ensemble evidence.
- **AC-4 — judge barrier:** Given B0 or any B1…B_N unit is non-terminal or the ledger is
  open, when judging is considered, then the separate session cannot start. Once terminal,
  the Kimi BSC judge reads frozen artifacts only, makes no provider calls, spends nothing
  from the evaluation ledger, and emits all four required report classes.
- **AC-5 — worker identity:** Ordinary BSC implementer/reviewer/remediator output is clearly
  orchestration evidence, not DUT/judge evidence.
- **AC-6 — pack completeness:** Both active documents enumerate all seven required packs.
- **AC-7 — preserved mechanics:** `budget_cap_usd=1.00`, `max_processes=N`, immutable
  manifest hashing, disjoint/resumable waves, fail-closed behavior, owner gates, and
  production model-selection defaults retain their meaning.
- **AC-8 — honest debt:** `tests/pi_benchmark/README.md` and the executable DeepSeek-judge
  path are not claimed as the corrected Kimi judge; one separately scoped cleanup task owns
  their migration/retirement and its required tests/gates.
- **AC-9 — history and scope:** Historical ledger entries are unchanged; a new decision and
  ledger entry explain the correction; the task commit contains only the lifecycle and
  remaining-wave work-order under `docs/build-stream/`.

## 6. Verification

Run from `/Users/user/Documents/Istara-main-pi-replacement`. Compare against the captured
dirty-path baseline so concurrent user/worker changes are not attributed to this task.

```bash
# Whitespace and Markdown diff hygiene for the implementation paths.
git diff --check -- \
  docs/build-stream/2026-07-22-pi-benchmark.md \
  docs/build-stream/conductor-instructions/pi-benchmark-deepseek-moa-execution.md

# Inspect active ambiguity hits. Hits in historical L-* entries are allowed only as
# preserved history; active hits must be judge-only or explicit supersession prose.
rg -n -i \
  'provider kimi|--provider kimi|kimi[- ]only evaluation|kimi evaluation (credential|provider|adapter|envelope)|judge call through deepseek|deepseek.{0,40}judge' \
  docs/build-stream/2026-07-22-pi-benchmark.md \
  docs/build-stream/conductor-instructions/pi-benchmark-deepseek-moa-execution.md

# Exact supported runner route appears in active examples.
rg -n -- '--provider deepseek|--model deepseek-v4-pro' \
  docs/build-stream/2026-07-22-pi-benchmark.md

# Both documents contain the role/output vocabulary and every evaluation pack.
for file in \
  docs/build-stream/2026-07-22-pi-benchmark.md \
  docs/build-stream/conductor-instructions/pi-benchmark-deepseek-moa-execution.md; do
  for term in 'original agentic loop' 'Pi adaptation' 'DeepSeek' 'API/dispatcher' \
              'Kimi' 'report.md' 'report.html' 'scorecard.json' 'per-judgment' \
              'canonical 15-scenario' 'feature breadth' 'Research Spine' 'A2A' \
              'prompt/injection' 'usage/cost' 'route/downgrade'; do
    rg -q "$term" "$file" || { echo "missing: $term in $file"; exit 1; }
  done
done

# Preserved mechanics and explicit production non-mutation remain visible.
rg -n \
  'budget_cap_usd=1\.00|max_processes=N|immutable|resumable|production.*defaults|model-selection' \
  docs/build-stream/2026-07-22-pi-benchmark.md \
  docs/build-stream/conductor-instructions/pi-benchmark-deepseek-moa-execution.md

# Adjacent stale judge surfaces are explicitly named as debt, not silently treated as
# compliant or edited in this task.
rg -n \
  'tests/pi_benchmark/README\.md|tests/pi_benchmark/deepseek_judge\.py|non-conforming|follow-up' \
  docs/build-stream/2026-07-22-pi-benchmark.md \
  docs/build-stream/conductor-instructions/pi-benchmark-deepseek-moa-execution.md

# Before committing, staged paths must be exactly the two implementation paths.
git diff --cached --name-only

# After the path-scoped commit, audit that commit rather than the globally dirty tree.
git diff-tree --no-commit-id --name-only -r <task-commit>
```

No backend/frontend or live benchmark suite is required for this wording-only correction.
If implementation touches benchmark Python, provider/dispatcher/validation code, production
files, credentials, or live services, stop and create a new scoped task with the applicable
architecture/security verification. Do not load a model or make a DeepSeek/Kimi call.

## 7. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Global replacement rewrites append-only history. | Audit trail becomes false. | Bound edits to active regions; verify historical ledger hunks are absent; supersede with new DEC/L entries. |
| DeepSeek is described as the DUT instead of a serving route. | The comparison no longer measures Istara. | Put the five-role contract first and require the Istara API/dispatcher path. |
| Kimi judging starts before terminal evaluation. | Results become incomplete or biased. | Require manifest/ledger terminality and a frozen artifact index before launching the separate session. |
| The judge makes provider calls or uses the evaluation ledger. | Role leakage and cap ambiguity. | Give the judge artifact-only inputs and no runner, provider credential, or evaluation-ledger write path. |
| Requested routes are mistaken for served routes. | Downgraded MoA looks successful. | Require served identities/counts and explicit degraded/blocked/not-runnable classification. |
| Existing README/`deepseek_judge.py` surfaces are treated as compliant. | Docs overclaim executable readiness and future workers may select the wrong judge path. | Name both exact surfaces as non-conforming debt, bar them from the corrected contract, and create one separate cleanup task. |
| Shared-worktree changes are staged with this task. | Another worker's code enters the commit. | Capture baseline, use the completion lock and `commit_paths`, and audit the task commit's exact paths. |
| Concurrent lifecycle append changes numbering/status. | Duplicate DEC/L numbers or stale status. | Re-read inside the lock and update only the fields owned by this completion. |

## 8. Rollback

The implementation is a path-scoped documentation commit. Revert that commit to restore the
prior active wording; no runtime state, schema, credential, manifest, report, or production
route changes. Because decisions and ledger entries are append-only, a later rollback records
a superseding decision/ledger entry rather than deleting the correction from history.

## 9. Non-goals

- Do not edit `docs/build-stream/plans/2026-07-20-pi-full-replacement-master-plan.md`.
- Do not edit backend, frontend, `tests/pi_benchmark/`, recipes, manifests, reports, or
  generated feature documentation.
- Do not repair, annotate, or invoke `tests/pi_benchmark/README.md` or
  `deepseek_judge.py` in this documentation task; their cleanup is separately scoped.
- Do not start servers, load models, call DeepSeek/Kimi, run benchmark waves, or spend.
- Do not alter Istara production engine/provider/model defaults or fallback policy.
- Do not judge benchmark results during this role-correction stage.
