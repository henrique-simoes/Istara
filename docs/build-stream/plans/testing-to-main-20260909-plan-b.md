# Plan B — Freeze and reconcile the testing release candidate

Consensus architect B (slot `b`) · pipeline run `testing-to-main-20260909` · spec `CF-SPEC-30`
Phase: `draft` (independent). Status: proposal only. No implementation is authorized by this document.

> **Path hygiene notice (load-bearing).** `scripts/public_repo_quality_audit.py` fails the build on
> the literal absolute checkout path of the owner's machine appearing in any tracked text file.
> This plan therefore writes `<REPO_ROOT>` wherever that path would appear. Implementers must do
> the same in every artifact that gets committed. See F-B01.

---

## 0. How this plan was produced

Every claim in section B was measured read-only in the worktree during this drafting session. No
server was started, no model was loaded, no provider was contacted, nothing was reset, cleaned or
deleted. Where my measurement disagrees with the assignment brief, I say so explicitly and give the
command that produced my value. The brief is treated as a hypothesis to test, not as ground truth.

Four brief claims did not survive measurement (F-B01, F-B08, F-B09, F-B11). Two of those change what
the implementation waves must actually do, so they are called out rather than quietly corrected.

---

## A. Candidate definition

### A.1 Exact measured state

| Fact | Measured value | Command |
|---|---|---|
| Local branch | `testing` | `git rev-parse --abbrev-ref HEAD` |
| Local `testing` HEAD | `85f64e4d25467b7e95ca4f0fb033f4039adbf59e` | `git rev-parse HEAD` |
| `origin/testing` | `9961fa3dbd2ce03a6e1d8cc3e303478edaf17a79` | `git rev-parse origin/testing` |
| `origin/main` | `fa6a1a391b5a1089690eb8fed5d179ce146ec9e9` | `git rev-parse origin/main` |
| Merge base with `main` | `fa6a1a39…` (i.e. `main` is a strict ancestor) | `git merge-base HEAD origin/main` |
| local vs `origin/testing` | 64 ahead, 0 behind | `git rev-list --left-right --count origin/testing...HEAD` |
| `origin/testing` vs `origin/main` | 994 ahead, 0 behind | `git rev-list --left-right --count origin/main...origin/testing` |
| Tracked modifications | 155 files, **4712** insertions, 977 deletions | `git diff --shortstat` |
| Staged | none | `git diff --cached --shortstat` |
| Untracked (excluding ignored) | **119** files | `git ls-files --others --exclude-standard \| wc -l` |

All three refs match the brief exactly, and `main` is a strict ancestor of `origin/testing`, so the
promotion is a fast-forwardable lineage with no rebase or conflict surface. That is the single most
favourable fact in this release and the plan is built on it.

Two numbers do **not** match the brief: insertions are 4712 (brief: 4706) and untracked files are
119 (brief: 118). The delta is small but the meaning is large — **the candidate surface moved while
the release was being analysed** (F-B11). Every wave below is therefore written to be
re-measurable, and the freeze in Wave 1 exists precisely to stop this.

### A.2 What the dirty tree actually is

The dirty tree is not ambient noise, and must not be treated as disposable. Grouping it:

```
modified (155):   48 tests/simulation/scenarios   16 tests   12 frontend/src/lib
                  11 backend/app/core   11 backend/app/api/routes   5 docs/build-stream
                   2 security   … plus AGENTS.md, recipes/, qa/
untracked (119):  71 tests/document_corpus/rich/**  17 docs/build-stream
                  13 tests/simulation   4 frontend/src   …
```

This is coherent, intentional Build Stream work: a research document corpus, simulation scenarios,
frontend API-client changes, backend route changes, and lifecycle records. Two facts make it
release-relevant rather than incidental:

- `security/control_matrix.json` and `security/SECURITY_BENCHMARK.md` are modified — the audit and
  metrics routes were added to two control scopes. Under the Istara contract this **mandates** a
  security benchmark rerun on the frozen SHA (F-B15).
- 17 lifecycle files under `docs/build-stream/` are untracked, **including the conductor's own
  lifecycle file for this very initiative** (F-B10).

### A.3 Reconciliation algorithm

The algorithm is *classify, then include deliberately*. Nothing is ever deleted, reset, cleaned,
stashed away permanently, or pruned. `LLMs/` and `Model_Finetuning/` are never touched at any step.

**Step 0 — snapshot before anything.** Create a recovery point that does not depend on any later
step being correct:

```
git bundle create ../istara-recovery-<UTC>.bundle --all
git stash list > ../istara-stashlist-<UTC>.txt          # record only, never drop
tar -czf ../istara-untracked-<UTC>.tar.gz $(git ls-files --others --exclude-standard)
git status --porcelain=v1 > ../istara-status-<UTC>.txt
```

The bundle plus the untracked tarball together reconstruct the exact pre-wave state. Store outside
the repository. This is the rollback substrate for *every* wave.

**Step 1 — enumerate into five buckets.** Produce `candidate-classification.tsv` with one row per
modified and untracked path and exactly one disposition:

| Bucket | Meaning | Default disposition |
|---|---|---|
| `INCLUDE-INTENT` | Traceable to a named Build Stream initiative or CF task | include |
| `INCLUDE-HYGIENE` | Formatting/whitespace/lint repair produced by this release effort | include |
| `LIFECYCLE` | `docs/build-stream/**` narrative and plan records | include, after §A.4 truth pass |
| `AMBIENT` | Local experiment, editor artifact, scratch, machine-specific | **exclude**, preserve in place |
| `UNDECIDED` | Cannot be traced by evidence | **exclude and escalate to owner** |

`UNDECIDED` defaulting to *exclude* is deliberate: accidentally shipping unreviewed local work is a
worse failure than deferring a file to the next release. Nothing enters the candidate because it
happened to be sitting in the tree.

**Step 2 — evidence rule for classification.** A path may be `INCLUDE-INTENT` only if at least one
holds: it appears in a lifecycle ledger `Did:` line; it is named by an open or accepted CF task or
spec; it is a test/fixture required by an included source change; or it is required to make a
blocking check pass. Otherwise it is `UNDECIDED`. Classification is recorded as CF evidence so the
reviewer can audit it, not re-derive it.

**Step 3 — generated and derived artifacts.** Anything reproducible from source (coverage output,
`.results/`, scorecards, build output, `node_modules`) is excluded from the candidate and
regenerated by CI. `security/security_scorecard.json` is regenerated by the governance job, so the
committed copy must never be the evidence of record.

**Step 4 — stage by explicit path list only.** Commit with `git add --pathspec-from-file`, never
`git add -A` and never a pathless commit. This is the single most important mechanical rule in the
plan: `git add -A` here would sweep 119 untracked files, including unclassified ones, into a release.

**Step 5 — the untracked lifecycle problem.** The 17 untracked lifecycle files must be resolved
*before* freeze, because a lifecycle record that is not in the candidate cannot be evidence about the
candidate. Each is either committed (if it is truth about included work) or explicitly deferred with
a written reason. The conductor's own convergence file is committed as part of Wave 1.

### A.4 Freeze

After Waves 1–5 complete, one commit is made on `testing` and its SHA is recorded as
`CANDIDATE_SHA`. From that instant:

- `CANDIDATE_SHA` is written into the CF spec, the lifecycle status block, and the promotion dossier;
- every subsequent verification records the SHA it ran against;
- any commit after the freeze **invalidates** the dossier and forces re-freeze at a new SHA. There is
  no "small amendment" path. This is enforced by the dossier check in Wave 6, not by convention.

`origin/testing` is only updated by a normal push of the frozen commit — never force-pushed, so
`origin/testing`'s history stays append-only and auditable, and the existing anti-replay check in
`.github/workflows/promote-testing.yml` (which verifies the promoted SHA equals current `testing`
HEAD) keeps working.

### A.5 Rollback and recovery

| Failure | Recovery |
|---|---|
| Wrong file included | `git revert` the specific commit; re-freeze at a new SHA |
| Wrong file excluded | It is still in the worktree — classify and include in the next release |
| Local work appears lost | Restore from the Step-0 bundle + untracked tarball |
| Candidate proves unshippable | Abandon the SHA; `origin/testing` history is intact; `main` never moved |
| Lifecycle record wrong | Ledgers are append-only; append a correction entry, never rewrite |

`main` is never touched by any wave, so the worst case is always "the release does not happen",
never "the release branch is damaged".

### A.6 Rules preventing silent basis change

1. Every wave records the SHA it started from and the SHA it produced, as CF `command` evidence.
2. No wave may commit a path outside its declared scope; the supervisor check compares
   `git diff --name-only <wave-start>..<wave-end>` against the wave's scope list.
3. `git add -A`, `git checkout -- .`, `git reset --hard`, `git clean`, and `git stash drop` are
   forbidden in every wave (§G).
4. The Wave 6 dossier re-verifies that the frozen SHA still equals `testing` HEAD before any
   promotion evidence is considered valid.

---

## B. Findings register

Severity: **S1** blocks promotion · **S2** blocks promotion unless owner accepts with rationale ·
**S3** should be fixed in this release · **S4** record and defer.

---

### F-B01 · S1 · Release hygiene / public-artifact audit — *the brief misstates this defect*

**Surface:** `scripts/public_repo_quality_audit.py`, `AGENTS.md`, `docs/build-stream/**`
**Evidence:** `pytest tests/test_public_repo_quality.py -q` → 1 failed. Direct run of `audit()` yields:
```
AGENTS.md: forbidden public artifact phrase: machine_checkout_path
docs/build-stream/2026-09-08-pi-capability-inheritance.md: forbidden public artifact phrase: machine_checkout_path
```
But `grep -n "machine_checkout_path" AGENTS.md` returns **nothing**.

**Root cause:** `machine_checkout_path` is the *rule name*, not the forbidden text. In
`GLOBAL_FORBIDDEN` (line 74) it maps to the literal absolute checkout path of the owner's machine.
The real leak is one line in each file:
- `AGENTS.md:142` — `Project root: ` followed by the absolute path.
- `docs/build-stream/2026-09-08-pi-capability-inheritance.md:1722` — a reviewer's prose quoting the
  absolute path while describing where they did *not* measure.

Repo-wide there are exactly **three** tracked occurrences; the third is the audit script itself,
which is self-excluded by design.

**Why this matters more than a two-line fix:** an implementer who follows the brief literally will
grep for `machine_checkout_path`, find nothing, and either declare the failure spurious or start
editing the audit script — i.e. suppressing a working release gate. This is the single highest-risk
misdirection in the assignment.

**Consequence:** the owner's local filesystem layout is published in a public repository, and a
correct quality gate is at risk of being disabled to obtain green.

**Recurrence mechanism (the actual architectural defect):** the conductor protocol hands every
worker the absolute checkout path in its prompt and instructs it to write ledger entries into
`docs/build-stream/`, which the audit scans. The leak is therefore *systematically regenerated* on
every wave. Fixing the two lines without fixing the generator guarantees recurrence — including
from the very waves this plan defines.

**Correction:**
1. Rewrite both lines to repo-relative form (`Project root: repository root`) — never edit the audit.
2. Add a pre-commit hook and a fast CI step running `python scripts/public_repo_quality_audit.py --check`
   so the leak fails at commit time, not at end-of-suite.
3. Add a rule to `docs/build-stream/protocol.md`: lifecycle entries use repo-relative paths and the
   `<REPO_ROOT>` placeholder.
4. Note that the audit scans `git ls-files` — **tracked files only**. Wave 1 commits 17 currently
   untracked lifecycle files, so the audit must be re-run *after* that commit, when its scan surface
   grows. Running it only before Wave 1 proves nothing about the candidate.

**Verification:** `pytest tests/test_public_repo_quality.py -q` on the frozen SHA, plus a negative
test that reintroducing the path fails the audit. **Wave:** 1 (hook + protocol), 3 (text repair),
6 (re-verify on frozen SHA). **Disposition:** blocking.

---

### F-B02 · S1 · Backend correctness escaping the lint gate

**Surface:** `backend/app/core/token_counter.py:105`, `backend/app/core/compute_registry_helpers.py:253`
**Evidence:** `python -m ruff check backend/ --select F821 --output-format concise` → 2 errors:
`Undefined name BudgetAllocation`, `Undefined name ComputeNode`.

I did not accept these as false positives. Proof they are real:
```
python -c "import app.core.compute_registry_helpers as m, typing;
           typing.get_type_hints(m._hydrate_local_resources)"
→ NameError: name 'ComputeNode' is not defined
```
Neither module has a `TYPE_CHECKING` block and neither name is imported anywhere in the file.
`compute_registry_helpers.py` has `from __future__ import annotations`, so annotations are lazy and
the module imports cleanly — the defect is dormant, not absent.

**Root cause — a genuine hole in the protection architecture, which is what the brief asked me to
determine.** Three mechanisms compose:
1. `Strict lint for changed backend files` (`check_ruff_changed.py`) is **blocking** but only sees
   the changed set;
2. `ruff check . --statistics` is **`continue-on-error: true`** (ci.yml:181) — advisory;
3. neither file is in the current changed set.

So a correctness class (`F821`, undefined name) is blocking on new code and invisible on existing
code. **Answer to the brief's question: yes — release-critical correctness findings demonstrably
escape protection, and I have two live specimens.**

**Consequence:** any future call to `get_type_hints`, a Pydantic model rebuild, a FastAPI response
model resolution, or `typing.get_type_hints`-based DI on these functions raises `NameError` at
runtime. Latent today, a production 500 the moment a caller resolves hints.

**Correction (root cause, not workaround):** import the two names under `if TYPE_CHECKING:` from
their defining modules. Then split ruff policy by *severity class* rather than by *changed-ness*:
promote the correctness subset (`F821`, `F811`, `F822`, `E999`) to repo-wide **blocking**, while the
378 pre-existing style errors (`E501`/`E402`/`UP042`/`E712`/`N806`/`F841`) stay advisory with their
existing burn-down note. This makes the gate stricter, not looser, and is achievable now because the
correctness subset is exactly 2 violations.

**Verification:** `ruff check backend/ --select F821,F811,F822,E999` → 0; the `get_type_hints` probe
above returns a dict for both functions; full backend suite still green. **Wave:** 3.
**Disposition:** blocking.

---

### F-B03 · S1 · The frontend mutation gate is architecturally hollow *and* brittle

**Surface:** `frontend/stryker.config.json`, `frontend/src/lib/runtimeConfig.ts`
**Evidence:** the config mutates exactly one file:
```json
"mutate": ["src/lib/runtimeConfig.ts"],  "thresholds": { "high": 90, "low": 80, "break": 75 }
```
`frontend/src/lib/runtimeConfig.ts` is **82 lines** and is **not modified by this candidate**
(`git diff --stat -- frontend/src/lib/runtimeConfig.ts` → empty); neither is its test.

Reconciling the remote numbers: 95 killed + 21 survived + 14 no-coverage = 130 mutants;
95/130 = **73.08%**, matching the reported score exactly. So the score is `killed / total`, and
clearing the 75 break needs **98 killed — just 3 more mutants**.

**Root cause:** two independent problems that the single reported number conflates.
1. *Hollowness*: "frontend mutation score" gates the entire release on one 82-line file, while
   `frontend/src/lib/` alone has 12 modified files (245 insertions) in this very candidate — none of
   them mutated. The gate's name promises far more than its scope delivers.
2. *Brittleness*: with only 130 mutants, three mutants is 2.3 points. Any incidental change to test
   selection swings the release verdict. Note `"vitest": { "related": true }` — Stryker runs only
   *related* tests, so mutant coverage depends on relation detection, which explains 14 no-coverage
   mutants in an 82-line file that has a dedicated test.

**Consequence:** the release is currently blocked by a gate that measures almost nothing, and
passing it would create false confidence about the frontend as a whole.

**Correction — never lower the threshold.** In order:
1. Strengthen `frontend/src/lib/runtimeConfig.test.ts` to kill the 21 survivors and cover the 14
   no-coverage mutants. Use the Stryker HTML/JSON report to target them individually. Only 3 kills
   are required to pass, so aim well past it (target ≥ 90, the configured `high`) to restore margin.
2. Set `"related": false` for the mutated set so no-coverage mutants are a test-quality signal, not
   a test-selection artifact.
3. Expand `mutate` to the changed `src/lib/*Api.ts` surface **with its own threshold**, introduced
   as advisory for one release and promoted to blocking in the next — so scope expansion never
   silently blocks a release on a number nobody has seen yet.

Step 1 is Wave 3 (blocking). Steps 2–3 are Wave 4, and step 3's promotion to blocking is a stated
owner decision, because widening a gate's scope changes the release contract.

**Verification:** `npm run test:mutation` in `frontend/` → score ≥ 75 blocking, report attached as
evidence with the killed/survived/no-coverage triple recorded. **Wave:** 3, then 4.
**Disposition:** blocking.

---

### F-B04 · S1 · No real browser acceptance exists anywhere in CI

**Surface:** `.github/workflows/ci.yml` job `qa-contract-stack`, `.github/workflows/qa-artifact.yml`
**Evidence:** the job's only container-related step is
```
docker compose -f docker-compose.qa.yml --profile contract config --quiet
```
`docker compose config` **parses and validates** the compose file. It starts nothing. The remaining
steps are `pytest` contract tests. No Playwright invocation, no browser, no container runtime, in
the entire job.

**Root cause:** compose-rendering was adopted as a proxy for stack health and then treated as
evidence of user-journey health. It is a syntax check wearing a stack check's name.

**Consequence:** this is the sharpest instance of the brief's own warning — *a green process,
container, workflow, or artifact is not proof of the requested user behavior*. The repository
currently has **zero** automated evidence that any user journey works in a browser, while carrying a
Full UI Acceptance Contract that demands exactly that. Promoting on today's evidence would certify
behaviour that has never been executed.

**Correction:** add a `ui-journeys` job that actually starts the QA stack (loopback-only publication),
waits for health, and runs the container-first Playwright suites in `tests/simulation` and
`tests/real_user_benchmark`, emitting dated verdicts, deterministic screenshot/HAR paths, and
explicit `not_runnable` results for unavailable live dependencies. Rename `qa-contract-stack` to
`qa-contract-render` so its name states what it proves.

**Verification:** the new job runs the changed-surface journeys on the frozen SHA with role
(admin/researcher/viewer/stranger), light/dark, 375px reflow, Tab-order/visible-focus, and
loading/error/empty coverage; synthetic data only; golden data untouched. **Wave:** 5.
**Disposition:** blocking for the journeys covering changed behaviour; full-matrix backfill for
unchanged surfaces may be deferred with owner sign-off.

---

### F-B05 · S1 · Sequential steps collapse independent failure domains

**Surface:** `.github/workflows/ci.yml` jobs `backend`, `frontend`
**Evidence:** in `backend`, step order is … `Strict lint` → `Lint` (advisory) → **`Format check`** →
**`Test`**. In `frontend`: **`Lint`** → `Type check` → `Unit tests` → `Mutation tests` → `Build`.

**Root cause:** one job per technology instead of one job per failure domain. A step failure aborts
every later step in the same job.

**Consequence:** this is exactly the observed situation and it is actively costing information. The
red run reports a Ruff formatting failure and a mutation failure — but because `Format check`
precedes `Test`, **nobody knows whether the 2,329-test backend suite passes on the pushed SHA**.
Each red run yields one datum instead of six, so the release converges by serialised guessing.

**Correction:** split into independent jobs — `backend-format`, `backend-lint`, `backend-test`,
`frontend-lint`, `frontend-typecheck`, `frontend-unit`, `frontend-mutation`, `frontend-build` — each
checking out independently, none `needs:`-chained on a sibling quality gate. Add `if: always()` where
a genuine dependency exists. Costs parallel runners; buys a complete failure picture per run.

**Verification:** a deliberately introduced formatting error produces a red `backend-format` **and**
a green `backend-test` in the same run. **Wave:** 4. **Disposition:** blocking.

---

### F-B06 · S1 · Branch protection does not enforce the architecture

**Surface:** GitHub repository settings for `main` (not in-repo)
**Evidence:** `gh api repos/henrique-simoes/Istara/branches/main/protection`:
```
required_status_checks.contexts = ["governance"]   strict = true
required_approving_review_count = 0    require_code_owner_reviews = false
enforce_admins = false                 allow_force_pushes = true
required_linear_history = false        required_conversation_resolution = false
```
`ci.yml` defines seven jobs: `feature-obligations`, `governance`, `backend`, `frontend`,
`test-harness-js`, `desktop`, `qa-contract-stack`. **Six of seven are advisory at the merge gate.**

**Root cause:** protection was configured when `governance` was the only meaningful gate and never
grew with the workflow.

**Consequence:** `main` can be merged with a red backend suite, red frontend, failed mutation and
failed QA — and can be force-pushed, by an admin, with zero reviews. Every other finding in this
register is unenforced at the boundary that matters. `strict: true` is the one bright spot: it
requires the branch to be current before merge.

**Correction — and note the split the brief demands.** The workflow changes (F-B05) land in-repo in
Wave 4. The protection change is a **GitHub repository setting**, cannot be made by editing
`ci.yml`, and is **owner-gated** (§G). Wave 4 produces an exact, reviewed `gh api` request body;
the owner applies it. Requested target: require every renamed job context plus `ui-journeys`; ≥1
approving review; code-owner review on; `enforce_admins` on; force pushes off; linear history on.

**Verification:** re-read the protection endpoint after the owner applies it and attach the JSON to
the dossier; a promotion PR with a failing required context must be un-mergeable.
**Wave:** 4 (prepare) / owner (apply). **Disposition:** blocking for promotion.

---

### F-B07 · S2 · The freeze mechanism's own hash cannot be verified as documented

**Surface:** `.compass-forge/conductor/testing-to-main-20260909-waves.json`, task payload
`wave_manifest_sha256`
**Evidence:** payload pins `8601a1fc7cc2373909234cf8bcf6534e0f8a7f7e46c731c1f4f9ad864e142c3c`, but
`shasum -a 256` on the file gives `dd54b84901d847f97ca6d52f79aec1bdb2f7fddf5479b9b891e36c384dcc179d`.

I did not stop at "mismatch". File mtime is `2026-09-09T14:38:46Z`, *before* task creation
(`14:39:32Z`), so nothing mutated it. Testing canonicalisations:
```
raw                                              dd54b849…
json.dumps(obj, sort_keys=True, separators=(',',':'))   8601a1fc…  ← MATCH
json.dumps(obj, separators=(',',':'))                   d8b7f4ee…
json.dumps(obj, sort_keys=True, indent=2)               74b5465b…
```
**The manifest is intact.** The hash is over canonical compact sorted JSON; the canonicalisation is
undocumented anywhere.

**Consequence:** every reviewer who verifies the manifest the obvious way (`shasum`) computes a
mismatch and concludes tampering — a false alarm in the one mechanism whose entire job is detecting
tampering. In a plan built on freezing an immutable boundary, an unfalsifiable freeze check is a
structural weakness, not a nit.

**Correction:** document the canonicalisation next to the manifest and ship
`scripts/verify_wave_manifest.py` that recomputes and compares it, so verification is one command
with no folklore.

**Related, and worse (F-B13):** `.gitignore:142` ignores `.compass-forge/`, so the wave manifest —
the plan of record for this release — **never rides the candidate commit**. The frozen SHA will not
contain the plan it was frozen against. Wave 1 must export the approved manifest to a tracked path
under `docs/build-stream/` and pin its canonical hash in the lifecycle status block.

**Verification:** `python scripts/verify_wave_manifest.py` exits 0; the tracked export exists at the
frozen SHA. **Wave:** 1. **Disposition:** blocking (the tracked export); the script is S3.

---

### F-B08 · S2 · The brief's Compass Forge diagnosis is wrong, and following it wastes a wave

**Surface:** Compass Forge control plane
**Evidence:** three brief claims, each measured:

| Brief claim | Measurement | Verdict |
|---|---|---|
| "index is unusable, schema 12 vs required 21" | `index status`: `index_version: 12`, `kernel: "rust"`, `indexed_file_count: 941`, `warnings: []`, built `2026-09-09T14:48:19Z` | **unsupported** — 12 is what the current Rust kernel itself just wrote |
| "`graph_usable=false` until a deliberate refresh" | `intelligence impact --path …` → `graph_source: "tree-sitter"`, `confidence: {level: "high"}` | **unsupported** — the graph answers now |
| "read `resolution`, `answer_completeness`, `confidence`, `graph source`, `freshness`" | response keys are `confidence, corpus, docs_or_agent_rules, gate_rules_likely_relevant, graph_source, input, must_inspect, ownership_and_hotspots, project_root, recommended_verification, resource_limits, routes_or_contracts, runtime, seed_files, should_inspect, tests_likely_affected` | `resolution`, `answer_completeness`, `freshness`, `graph_usable` **do not exist** in this build |

**Actual defect found:** the bare `impact` command returns
`{"code": "not_yet_native", "message": "Command impact has not completed its Rust migration gate", "remedy": "Python fallback is forbidden"}`.
The working command is the namespaced `intelligence impact --path <p>` (`--paths` plural is
rejected). So the capability was never missing — the *command name* changed.

**Consequence:** a wave task reading "refresh the index until `graph_usable=true`, then run
`compass-forge impact`" is **unexecutable**: no refresh changes `index_version`, and `impact` will
never succeed under the pinned binary. An implementer would burn a wave chasing it, and a reviewer
checking `answer_completeness` would report a nonexistent field as missing evidence.

**Correction:** waves call `intelligence impact --path <p>` and read only `confidence` and
`graph_source`; index freshness is asserted via `index status` (`created_at` newer than the last
source commit, `warnings: []`), not via a nonexistent `graph_usable` flag. Record the command-name
migration in the lifecycle decision log so later agents do not re-derive it.

**Verification:** `index status` is fresh with no warnings on the frozen SHA; one recorded
`intelligence impact --path` per changed architectural surface. **Wave:** 2. **Disposition:**
blocking (the plan must be executable).

---

### F-B09 · S2 · Compass Forge task debt is two orders of magnitude larger than briefed

**Surface:** CF task/spec state
**Evidence:** `task list --status open` → **181 open tasks** (brief mentions only CF-SPEC-29's).
Titles are overwhelmingly auto-generated boilerplate — `Validate US-001…`, `Implement FR-001…`
through `FR-005`, `Prove SC-001/SC-002` — repeating across many old specs (CF-13/20/21 through
CF-91+). `spec list` → 30 specs; non-terminal: **CF-SPEC-19** (`tasked`), **CF-SPEC-25** (`tasked`),
**CF-SPEC-28** (`draft`), **CF-SPEC-29** (`tasked`), plus **CF-SPEC-30** (this release).

**Root cause:** spec creation emits a fixed task template; specs were accepted (CF-SPEC-20 through
27 are `accepted`) without closing their generated children. The debt is administrative, not
functional — but it is indistinguishable from real blockers without inspection.

**Consequence:** "no open release-blocking CF tasks" (final criterion) is currently unprovable. And
per the brief's own instruction, staleness **must be proven, not assumed** — so 181 tasks cannot be
bulk-closed.

**Correction:** triage all 181 into `stale-administrative` (parent spec `accepted`, work evidenced
elsewhere), `genuinely-open-but-not-release-blocking` (deferred with a named future spec), and
`release-blocking` (must close in this release). Closure requires citing the evidence that satisfies
it. Given the volume, expect the first two buckets to dominate; the deliverable is the *proof*, not
the closure count. CF-SPEC-19/25/28/29 each get an explicit disposition.

**Verification:** a triage table in the dossier; zero tasks in `release-blocking` at freeze; every
`stale-administrative` closure carries an evidence citation. **Wave:** 2. **Disposition:** blocking
for the release-blocking bucket only.

---

### F-B10 · S2 · Lifecycle truth is uncommitted and self-contradictory

**Surface:** `docs/build-stream/**`
**Evidence:** of the four files the brief names as inconsistent, **three are untracked**
(`2026-09-08-agentic-long-horizon-improvement.md`, `…-benchmark-modernization-full-ui-suite.md`,
`…-systemwide-audit-coverage.md`); only `…-pi-capability-inheritance.md` is tracked. In total **17**
lifecycle files under `docs/build-stream/` are untracked — **including
`2026-09-09-testing-to-main-convergence.md`, this initiative's own lifecycle file**, whose status
block reads `stage: S1-plan`, `status: in-progress`, `cf: { spec: CF-SPEC-30, tasks: [] }`.

**Consequence:** the release's own narrative record does not exist in the release. `tasks: []` while
CF-SPEC-30 has live tasks. Contradictory records (S0/in-progress alongside "Done/spec accepted") make
"reconciled Build Stream ledgers" unprovable, and the brief's rule that older completion claims
cannot override newer contradictory records cannot even be applied to files git has never seen.

**Correction:** for each of the ~10 recent initiatives, resolve status to exactly one of
`included / excluded / superseded / completed / deferred(with rationale)`; correct status blocks by
**appending** a correcting ledger entry (never rewriting history); commit the reconciled files in
Wave 1's explicit path list; populate `cf.tasks` in the convergence file.

**Verification:** a reconciliation table in the dossier; every lifecycle file referenced by the
release is tracked at the frozen SHA; no file simultaneously claims two stages. **Wave:** 1 (commit),
2 (truth reconciliation). **Disposition:** blocking.

---

### F-B11 · S2 · The candidate surface is moving during analysis

**Surface:** worktree
**Evidence:** brief states 4,706 insertions and 118 untracked files; I measure **4,712** and **119**.
**Root cause:** the worktree is a live shared checkout that agents and the owner both write to.
**Consequence:** any measurement not tied to a SHA is stale on arrival, and two reviewers can
legitimately disagree about the candidate — the exact ambiguity this release exists to end.
**Correction:** Wave 1 freezes first and measures afterwards; every evidence row records the SHA it
ran against; the supervisor rejects evidence lacking a SHA. Between freeze and promotion the owner is
asked to avoid writes to the checkout, or accept re-freeze.
**Verification:** re-running the Wave 1 measurements on `CANDIDATE_SHA` reproduces identical numbers.
**Wave:** 1. **Disposition:** blocking (procedural).

---

### F-B12 · S3 · Local mutation failure is an environment divergence, not a product defect

**Surface:** local `frontend/node_modules`, CI node version
**Evidence:** installed versions are mutually consistent — `@stryker-mutator/core` 9.6.1,
`@stryker-mutator/vitest-runner` 9.6.1 (peer: core `9.6.1`, vitest `>=2.0.0`), `vitest` 4.1.11. All
peers satisfied, so the brief's local plugin-init failure is **not** a version mismatch. Local
`node -v` is **v26.0.0**; `ci.yml` pins **node 24**.

**Root cause:** most likely native/ESM loader behaviour differing under an unpinned major node
version two releases ahead of CI.
**Consequence:** the local environment is not authoritative for mutation results — correctly
distinguishing this from the genuine remote 73.08 failure, as the brief requires.
**Correction:** treat CI (node 24, `npm ci`) as the authoritative mutation lane; verify mutation
fixes there or in a node-24 container; add `.nvmrc`/`engines` pinning node 24 so local and CI agree.
**Verification:** mutation runs clean in the node-24 lane; `node -v` recorded alongside every local
frontend result. **Wave:** 3. **Disposition:** non-blocking for promotion; blocking for trusting any
local mutation number.

---

### F-B13 · S3 · The plan of record is gitignored

**Surface:** `.gitignore:142`
**Evidence:** `git check-ignore -v` confirms `.compass-forge/` ignores the wave manifest.
**Consequence:** the frozen SHA cannot be audited against the plan it was frozen against.
**Correction:** export the approved manifest to a tracked `docs/build-stream/` path at freeze.
Covered by F-B07. **Wave:** 1. **Disposition:** blocking.

---

### F-B14 · S3 · Whitespace/blank-line errors across the diff

**Surface:** documentation and four code files
**Evidence:** `git diff --check origin/main` → 295 lines. Concentration:
`2026-09-05-testing-branch-readiness-and-main-promotion.md` (63),
`2026-09-06-core-ux-research-spine-and-memory-remediation.md` (29),
`docs/scientific_audit/long-horizon-agentic-engine-audit.md` (18), then a long tail. Code files
affected: `tests/test_stress_test_dataset.py`, `tests/test_reports.py`,
`tests/test_code_applications.py`, `frontend/src/components/chat/ChatView.tsx`.
**Root cause:** no whitespace hygiene gate; agent-authored Markdown carries trailing spaces.
**Consequence:** release-hygiene noise that obscures real diffs; not a functional defect.
**Correction:** strip trailing whitespace on the affected files; add `git diff --check` to the
pre-commit hook and a fast CI hygiene step. Ledger entries are append-only, so whitespace repair of
*historical* ledger text is a content edit — restrict repair to non-ledger regions, or record the
touch explicitly in the decision log.
**Verification:** `git diff --check origin/main` → empty on the frozen SHA. **Wave:** 3.
**Disposition:** blocking (it is an explicit release-hygiene criterion).

---

### F-B15 · S2 · Security control matrix changed — benchmark rerun is mandatory

**Surface:** `security/control_matrix.json`, `security/SECURITY_BENCHMARK.md`
**Evidence:** `git diff -- security/` shows +6 lines in the matrix: `backend/app/api/routes/audit.py`
and `backend/app/api/routes/metrics.py` added to **two** control scopes, plus
`backend/app/core/audit_middleware.py` and `frontend/src/components/common/VersionHistory.tsx`.
`SECURITY_BENCHMARK.md` +1 line.
**Root cause:** audit/metrics surfaces were brought under existing controls — a scope widening.
**Consequence:** the Istara contract makes the benchmark mandatory when a control's evidence path
changes. The known-passing 28/28 result predates the frozen SHA and cannot be extrapolated to it.
**Correction:** rerun `python scripts/security_benchmark.py --fail-on-threshold` on the frozen SHA;
confirm `tests/test_security_benchmark.py` covers the added paths; confirm the newly scoped routes
genuinely implement the controls claimed rather than merely being listed.
**Verification:** 28/28 (or higher denominator) on `CANDIDATE_SHA`, scorecard attached to the dossier.
**Wave:** 3 (verify), 6 (rerun on frozen SHA). **Disposition:** blocking.

---

### F-B16 · S3 · Backend formatting drift

**Surface:** 15 backend files
**Evidence:** `python -m ruff format --check backend/` → "15 files would be reformatted, 332 already
formatted" — the exact 15 the brief lists. Independently confirmed.
**Root cause:** no format-on-commit hook; formatting only checked in CI, after which F-B05 hides
everything downstream.
**Correction:** `ruff format backend/` (a mechanical, reviewable diff), plus the pre-commit hook.
**Verification:** `ruff format --check backend/` → clean; full backend suite re-run afterwards, since
this is the first run that can *see* past the format gate. **Wave:** 3. **Disposition:** blocking.

---

### F-B17 · S3 · Frontend lint error

**Surface:** `frontend/src/components/chat/ChatModelControls.tsx:20`
**Evidence:** `interface ModelChoice extends ChatModelChoice {}` — an empty interface extending a
type, violating `@typescript-eslint/no-empty-object-type`. Confirmed present.
**Root cause:** a local alias introduced for readability where a type alias was needed.
**Correction:** `type ModelChoice = ChatModelChoice;` — behaviour-identical, satisfies the rule.
Verify the two use sites (lines 246, 257) still typecheck.
**Verification:** `npm run lint` and `npx tsc --noEmit` clean. **Wave:** 3. **Disposition:** blocking.

---

### F-B18 · S4 · `governance` job holds `contents: write` and pushes to `main`

**Surface:** `.github/workflows/ci.yml` `governance` job
**Evidence:** `permissions: contents: write`; a README badge-sync step commits and pushes
`HEAD:main`, guarded by `if: github.event_name == 'push' && github.ref_name == 'main'`.
**Assessment:** the guard is correct and carries an explicit F-6 regression comment explaining that
`testing` HEAD must stay reproducible for the promotion gate. I flag it only because `governance` is
today's *sole* required check and therefore the highest-value target in the repository, and because
a CI job that writes to the release branch weakens "merged code" as a distinct stage.
**Correction (proposed, non-blocking):** move badge sync to a separate workflow with narrowly scoped
permissions so the required check itself is read-only.
**Verification:** `governance` runs with `contents: read`; badge sync still works on `main`.
**Wave:** 4. **Disposition:** deferred unless the owner wants it in scope.

---

### F-B19 · S4 · Desktop release status undefined

**Surface:** `.github/workflows/ci.yml` `desktop` job
**Evidence:** `continue-on-error: true` with the comment "Dependencies may require system libs not
available in CI".
**Consequence:** the desktop surface has no defined release status — neither proven nor formally
out of scope.
**Correction:** an explicit owner decision, recorded in the dossier: either *out of release scope*
(and excluded from required checks), or *in scope* (and the CI image gains the system libs and the
job becomes blocking). Do not leave it ambiguous.
**Verification:** the dossier states the decision. **Wave:** 4 (prepare) / owner (decide).
**Disposition:** deferred, decision required before promotion.

---

**Register summary:** 6 × S1 (F-B01, B02, B03, B04, B05, B06) · 5 × S2 (F-B07, B08, B09, B10, B11,
B15) · 5 × S3 (F-B12, B13, B14, B16, B17) · 3 × S4 (F-B18, B19, and the F-B03 scope-expansion
decision). Promotion is blocked until every S1 and S2 is closed or owner-accepted.

---

## C. Strict-wave manifest proposal

Six waves, matching the conductor's existing manifest IDs so the plan drops into the pipeline
unchanged. Waves are strictly sequential; each ends at a reviewable boundary.

---

### Wave 1 — `candidate-boundary`

**Objective.** Convert three ambiguous candidate surfaces into one classified, committed, frozen
boundary without losing or accidentally including any work.

**Scope.** Recovery snapshot; classification of 155 modified + 119 untracked paths; commit of
classified `INCLUDE-*` and `LIFECYCLE` paths; tracked export of the wave manifest; pre-commit hook
for path-leak and whitespace hygiene.

**Inputs.** §A.3 algorithm; lifecycle ledgers; CF task list; the brief's intent statements.

**Explicit exclusions.** No source-code repair (Wave 3). No CI edits (Wave 4). No CF task closure
(Wave 2). No push. No branch creation. **No deletion of anything, ever.**

**Tasks.**
1. Step-0 recovery snapshot (bundle + untracked tarball + status), stored outside the repository.
2. Produce `candidate-classification.tsv` with a disposition and evidence citation per path.
3. Owner review of the `UNDECIDED` bucket — **owner-gated pause**.
4. Resolve the 17 untracked lifecycle files (F-B10); commit those that are truth about included work.
5. Export the approved wave manifest to a tracked `docs/build-stream/` path; document its canonical
   hash recipe and add `scripts/verify_wave_manifest.py` (F-B07, F-B13).
6. Install the pre-commit hook: `public_repo_quality_audit --check` + `git diff --check` (F-B01, F-B14).
7. Commit via `git add --pathspec-from-file` only. Record start/end SHAs.

**Dependencies.** None — this is the root wave.

**Verification.** `git status --porcelain` contains only `AMBIENT`/`UNDECIDED` paths, each accounted
for in the TSV; `git stash list` unchanged; `LLMs/` and `Model_Finetuning/` byte-identical; the
recovery bundle restores in a scratch clone; classification row count equals the measured path count.

**CF gates/evidence.** `command` rows for snapshot, classification, commit; the TSV attached; start
and end SHAs recorded.

**Review questions.** Is every included path justified by cited evidence? Could any excluded path be
required by an included one? Does the recovery snapshot demonstrably restore? Was `git add -A` used
anywhere? Are protected directories untouched?

**Completion.** One commit exists whose contents are fully explained by the TSV, and the audit is
re-run *after* it (F-B01's scan surface grows with the commit).

**Rollback.** Revert the commit; restore from bundle + tarball.

**Residual risks.** Classification is judgement-based; the `UNDECIDED` bucket may be large; the owner
pause may block for a long time.

---

### Wave 2 — `control-plane-lifecycle`

**Objective.** Make Compass Forge and Build Stream tell one true, provable story about the candidate.

**Scope.** Index freshness; the 181-task triage; CF-SPEC-19/25/28/29/30 dispositions; lifecycle
status reconciliation; `intelligence impact` on each changed architectural surface.

**Inputs.** Wave 1 commit; F-B08, F-B09, F-B10.

**Explicit exclusions.** No code repair. No CI edits. **No bulk task closure without cited evidence.**

**Tasks.**
1. `index refresh`; assert `index status` → `warnings: []`, `created_at` newer than the Wave 1 commit.
   Record `index_version`/`kernel` as observed — do **not** chase a schema-21 target (F-B08).
2. Record the command-name migration (`impact` → `intelligence impact --path`) in the decision log.
3. Run `intelligence impact --path <p>` for each changed architectural surface; record `confidence`
   and `graph_source`; then follow dependencies manually, because the static graph misses dynamic
   dispatch and string-keyed routes.
4. Triage all 181 open tasks into the three buckets; close `stale-administrative` **with citations**.
5. Give CF-SPEC-19, 25, 28, 29 an explicit disposition; drive CF-SPEC-30 to `tasked` with real tasks.
6. Reconcile every recent lifecycle file to one status; populate `cf.tasks` in the convergence file.

**Dependencies.** Wave 1.

**Verification.** `index status` fresh, no warnings; `task list --status open` contains zero
release-blocking tasks; a triage table with one row per task; no lifecycle file claiming two stages.

**CF gates/evidence.** `command` rows per refresh/impact/triage; the triage table attached.

**Review questions.** Is each closure evidenced or merely asserted? Does any closed task hide real
work? Do the lifecycle statuses match the Wave 1 classification? Was the graph output believed beyond
its `confidence`?

**Completion.** "No open release-blocking CF tasks" is provable from evidence rows alone.

**Rollback.** Task closure is reversible via CF; lifecycle corrections are append-only entries.

**Residual risks.** 181 tasks is a large manual triage; misclassifying a real blocker as
administrative is the principal danger, which is why closures need citations.

---

### Wave 3 — `correctness-quality`

**Objective.** Repair every blocking correctness, format, lint, hygiene, mutation and security
failure at root cause.

**Scope.** F-B01 (text), F-B02, F-B03 (step 1), F-B14, F-B15, F-B16, F-B17, F-B12.

**Inputs.** Wave 1 commit; Wave 2 impact results.

**Explicit exclusions.** No CI restructuring (Wave 4). No browser work (Wave 5). **No threshold
lowering. No `continue-on-error` added. No test deletion or skip to obtain green.**

**Tasks.**
1. Repo-relative path repair in `AGENTS.md:142` and the lifecycle file (F-B01) — never edit the audit.
2. `TYPE_CHECKING` imports for `BudgetAllocation` and `ComputeNode`; re-run the `get_type_hints`
   probe as the acceptance test (F-B02).
3. `ruff format backend/` for the 15 files (F-B16).
4. `ModelChoice` → type alias (F-B17).
5. Strip trailing whitespace, excluding historical ledger prose (F-B14).
6. Strengthen `runtimeConfig.test.ts` to kill the 21 survivors and cover the 14 no-coverage mutants;
   target ≥ 90, not the bare 75 (F-B03).
7. Pin node 24 via `.nvmrc`/`engines`; re-verify mutation in the node-24 lane (F-B12).
8. Rerun the security benchmark for the changed control matrix (F-B15).
9. Run the **full** backend suite — the first run able to see past the format gate.

**Dependencies.** Waves 1–2.

**Verification.**
```
python -m ruff format --check backend/                     → clean
python -m ruff check backend/ --select F821,F811,F822,E999 → 0
pytest tests/ -q -m "not live_llm"                         → 0 failed
pytest tests/test_public_repo_quality.py -q                → passed
git diff --check origin/main                               → empty
npm run lint && npx tsc --noEmit && npm run test:unit      → clean   (frontend, node 24)
npm run test:mutation                                      → ≥ 75, target ≥ 90
python scripts/security_benchmark.py --fail-on-threshold   → 28/28
```

**CF gates/evidence.** One `command` row per line above, each recording the SHA it ran against.

**Review questions.** Was any fix a suppression? Did the mutation score rise from real assertions or
from narrowed scope? Does the backend suite pass now that formatting no longer masks it? Were the
F821 fixes verified by execution, not just by ruff falling silent?

**Completion.** Every credential-free blocking check is green on one commit.

**Rollback.** Each task is an independent revertible commit.

**Residual risks.** The full backend suite has never been observed green on this candidate — it may
reveal new failures behind the format gate. This is the wave most likely to expand.

---

### Wave 4 — `ci-enforcement`

**Objective.** Make CI represent the architecture, and prepare the owner-gated protection change.

**Scope.** Job split (F-B05); mutation scope policy (F-B03 steps 2–3); ruff severity policy (F-B02);
hygiene job (F-B01, F-B14); `qa-contract-stack` → `qa-contract-render`; `ui-journeys` job definition
(executed in Wave 5); protection request body (F-B06); desktop decision (F-B19); optional governance
permission split (F-B18).

**Inputs.** Wave 3 green candidate.

**Explicit exclusions.** **No repository-setting mutation** — the plan prepares, the owner applies.
No weakening of any existing check. No new `continue-on-error` on a correctness gate.

**Tasks.**
1. Split `backend`/`frontend` into independent failure-domain jobs (F-B05).
2. Promote repo-wide `F821,F811,F822,E999` to blocking; keep the style backlog advisory with its
   burn-down note (F-B02).
3. Add a fast `hygiene` job: public-quality audit + `git diff --check`.
4. Widen mutation scope advisory-first, with its own threshold (F-B03).
5. Rename the render job; define `ui-journeys`.
6. Draft the exact `gh api` protection body listing every required context (F-B06).
7. Record the desktop decision (F-B19).

**Dependencies.** Wave 3.

**Verification.** `python scripts/check_ci_governance.py` and `check_workflow_contracts.py` pass; a
deliberately injected format error yields red `backend-format` **and** green `backend-test` in one
run; the protection body is reviewed and attached, unapplied.

**CF gates/evidence.** `command` rows; the protection request body attached as an artifact.

**Review questions.** Can any correctness class still escape (the F-B02 question, re-asked of the new
design)? Does any job silently depend on a sibling? Could a required check pass while its domain is
broken? Does the required-context list exactly match the job names after renaming?

**Completion.** A push produces a complete, independent failure picture, and the protection change is
queued for the owner.

**Rollback.** `ci.yml` is one file; revert restores prior behaviour. No external state was changed.

**Residual risks.** Job renames invalidate existing required contexts — protection must be updated in
the same owner action or `main` briefly requires a context that no longer exists. **This ordering
hazard is the single most dangerous step in the plan** and must be sequenced explicitly with the owner.

---

### Wave 5 — `browser-spine-acceptance`

**Objective.** Prove the changed system in a real browser, and prove the Research Spine is not
bypassable.

**Scope.** Container-first Playwright journeys for changed surfaces; Research Spine probes;
`TESTING.md` and `testing/TEST_HISTORY.md` updates.

**Inputs.** Wave 4 CI; the Wave 1 classification's list of changed product behaviour.

**Explicit exclusions.** **No live model or provider execution. No server started outside the
container lane. No golden-data mutation** — synthetic data only. No API-only step presented as a
browser journey.

**Tasks.**
1. Stand up the QA stack with loopback-only publication; execute journeys for each changed behaviour.
2. Cover admin/researcher/viewer/stranger for auth-adjacent changes; light and dark; 375px reflow;
   Tab order and visible focus; loading/error/empty states.
3. Research Spine probes for touched research paths (§F).
4. Donor/model-management probes for donated-compute paths; team/persona extensions where relevant.
5. Emit dated verdicts and deterministic screenshot/HAR paths; emit explicit `not_runnable` with the
   named missing capability wherever a live dependency is absent.
6. Update `TESTING.md` and `testing/TEST_HISTORY.md`.

**Dependencies.** Wave 4.

**Verification.** Each journey has a dated verdict and artifacts; every `not_runnable` names its
missing capability; no journey asserts on an API response in place of a rendered UI state.

**CF gates/evidence.** `command` rows per journey; artifact paths recorded.

**Review questions.** Does each journey actually navigate, click, fill, upload and send? Is any step
an API call in disguise (the F-B04 failure mode, re-asked)? Is any `not_runnable` concealing a real
failure? Was golden data touched? Was publication loopback-only?

**Completion.** Every changed behaviour has a real browser verdict, or an explicit, owner-visible
`not_runnable`.

**Rollback.** Test-only wave; revert the additions.

**Residual risks.** Journey authoring is the largest unknown effort in the plan, and this is the wave
most likely to discover genuine product bugs — which would loop back to Wave 3. Sequence accordingly.

---

### Wave 6 — `promotion-certification`

**Objective.** Freeze one SHA and produce a binary, owner-gated promotion verdict.

**Scope.** Freeze; full re-verification on the frozen SHA; blind independent review; dossier.

**Inputs.** Waves 1–5.

**Explicit exclusions.** **No merge. No push to `main`. No PR unless separately authorized. No
repository-setting change.**

**Tasks.**
1. Freeze `CANDIDATE_SHA`; record it everywhere (§A.4).
2. Re-run the **entire** §E matrix on the frozen SHA — earlier results do not transfer.
3. Push `testing` (fast-forward only) and confirm all required checks green on that exact SHA.
4. Blind independent architectural/code review; remediate; delta re-review until dry.
5. Confirm the owner applied the protection change (F-B06) and re-read the endpoint as evidence.
6. Assemble the dossier (§H) and stop, pending owner approval.

**Dependencies.** Waves 1–5, plus the owner's protection action.

**Verification.** Every §E row marked "rerun on frozen SHA" has a result tied to `CANDIDATE_SHA`;
`git rev-parse testing` still equals `CANDIDATE_SHA` at dossier close.

**CF gates/evidence.** Full evidence set on `CANDIDATE_SHA`; `review_verdict` rows; the dossier.

**Review questions.** Is every claim tied to the frozen SHA? Did anything move after the freeze? Is
any "green" inherited from an earlier SHA? Does any claim overstate what was executed?

**Completion.** A dossier stating **READY** or **NOT READY**, with owner approval outstanding.

**Rollback.** Abandon the SHA; `main` is untouched.

**Residual risks.** Any post-freeze commit forces a full re-freeze and re-verification.

---

## D. CI target architecture

### D.1 Job graph

```
                          ┌── hygiene            (audit + diff --check)     fast, blocking
                          ├── governance         (integrity, CI-gov, security)  blocking
                          ├── feature-obligations                                blocking
   push / PR ─────────────┼── backend-format ─┐
                          ├── backend-lint    ├─ independent, none gating a sibling
                          ├── backend-test    ┘
                          ├── frontend-lint      ─┐
                          ├── frontend-typecheck  ├─ independent
                          ├── frontend-unit       │
                          ├── frontend-mutation   │
                          ├── frontend-build     ─┘
                          ├── test-harness-js                                blocking
                          ├── qa-contract-render  (compose parse only — named honestly)
                          └── ui-journeys         needs: qa-contract-render   blocking
   desktop ── per F-B19 owner decision: excluded, or included and blocking
```

The only `needs:` edge is `ui-journeys → qa-contract-render`, a true prerequisite (a stack that does
not render cannot start). No quality gate gates another quality gate — that is F-B05's root cause.

### D.2 Required checks

| Context | testing | main |
|---|---|---|
| `hygiene`, `governance`, `feature-obligations` | required | required |
| `backend-format`, `backend-lint`, `backend-test` | required | required |
| `frontend-lint`, `frontend-typecheck`, `frontend-unit`, `frontend-build` | required | required |
| `frontend-mutation` | required | required |
| `test-harness-js`, `qa-contract-render` | required | required |
| `ui-journeys` | required on PR | required |
| `desktop` | advisory | per F-B19 |

Plus, on `main`: ≥1 approving review, code-owner review, `enforce_admins` on, force pushes off,
linear history on, `strict` retained. All of this is an owner action (§G).

### D.3 Event behaviour

- **PR**: full graph, including `ui-journeys` and change-obligation checks (already PR-scoped).
- **Push to `testing`**: full graph — `testing` is the promotion source and must never carry an
  unproven SHA.
- **Push to `main`**: full graph; badge sync remains `main`-only (F-B18).
- **Scheduled (nightly)**: full graph plus the wider mutation scope and the full journey matrix, so
  expensive coverage exists without lengthening PR latency.

### D.4 Change-scoped vs full-suite

Change-scoping is allowed for *cost*, never for *correctness class*. Concretely: `check_ruff_changed`
keeps its blocking changed-file role, **and** the correctness subset runs repo-wide and blocking
(F-B02). The scheduled run is always full-suite, so a change-scoped gap cannot persist past a day.

### D.5 Caches, artifacts, retention

Per-job `npm`/`pip` caches keyed by lockfile hash; no cache shared across a trust boundary. Artifacts:
security scorecard, mutation report, Playwright screenshots/HAR/verdicts, promotion dossier. Retain
release-evidence artifacts at least through promotion plus one release; deterministic paths keyed by
SHA so an artifact can never be mistaken for another commit's.

### D.6 Mutation policy

Threshold `break: 75` is **never lowered**. Score improves via tests. Scope expands advisory-first,
then blocking by owner decision. Every mutation result records killed/survived/no-coverage — the
composite score alone hid F-B03's real shape.

### D.7 Formatting and lint policy

Formatting is blocking but in its own job, so it can never hide the test suite again. Lint is split by
severity: correctness classes blocking repo-wide; the style backlog advisory with its documented
burn-down. No correctness class is ever advisory.

### D.8 Credential-free and live lanes

The credential-free lane is the default and gates the release. The live lane is opt-in, never runs on
PR, and fails closed as `not_runnable` with the missing capability named. A `not_runnable` is never
counted as a pass, and never silently omitted from the dossier.

### D.9 Containers, desktop, stale-green prevention

`ui-journeys` runs container-first with loopback-only publication and synthetic data. Desktop status
is decided in F-B19 rather than left `continue-on-error` forever.

Stale or misleading green is prevented by four mechanisms: `strict: true` keeps branches current;
every required context maps to a job that actually executes its domain (F-B04's rename is part of
this); job names state what they prove; and the dossier binds every claim to one SHA. A check that
cannot fail for its stated reason is treated as a defect, not as coverage.

---

## E. Verification matrix

`CF` = credential-free · `Blk` = blocking · `Re` = must rerun on the frozen SHA.

| # | Surface / claim | Command or journey | Env | Expected | Evidence | Blk | CF | Re |
|---|---|---|---|---|---|---|---|---|
| 1 | Candidate boundary | `git status --porcelain` vs classification TSV | local | only AMBIENT/UNDECIDED remain | TSV + CF row | ✓ | ✓ | ✓ |
| 2 | Recovery | restore bundle into scratch clone | local | tree reconstructs | CF row | ✓ | ✓ | – |
| 3 | Protected dirs | checksum `LLMs/`, `Model_Finetuning/` | local | unchanged | CF row | ✓ | ✓ | ✓ |
| 4 | Backend format | `ruff format --check backend/` | CI | clean | `backend-format` | ✓ | ✓ | ✓ |
| 5 | Backend correctness lint | `ruff check backend/ --select F821,F811,F822,E999` | CI | 0 | `backend-lint` | ✓ | ✓ | ✓ |
| 6 | F821 defects are gone | `get_type_hints` probe on both functions | CI | returns dict | CF row | ✓ | ✓ | ✓ |
| 7 | Backend suite | `pytest tests/ -q -m "not live_llm"` | CI | 0 failed | `backend-test` | ✓ | ✓ | ✓ |
| 8 | Public quality | `pytest tests/test_public_repo_quality.py -q` | CI | passed | `hygiene` | ✓ | ✓ | ✓ |
| 9 | Whitespace | `git diff --check origin/main` | CI | empty | `hygiene` | ✓ | ✓ | ✓ |
| 10 | Frontend lint | `npm run lint` | CI n24 | clean | `frontend-lint` | ✓ | ✓ | ✓ |
| 11 | Typecheck | `npx tsc --noEmit` | CI n24 | clean | `frontend-typecheck` | ✓ | ✓ | ✓ |
| 12 | Frontend unit | `npm run test:unit` | CI n24 | 89/89 | `frontend-unit` | ✓ | ✓ | ✓ |
| 13 | Mutation | `npm run test:mutation` | CI n24 | ≥75 (target ≥90) + triple | `frontend-mutation` | ✓ | ✓ | ✓ |
| 14 | Frontend build | `npm run build` | CI n24 | succeeds | `frontend-build` | ✓ | ✓ | ✓ |
| 15 | Security benchmark | `security_benchmark.py --fail-on-threshold` | CI | 28/28 | scorecard | ✓ | ✓ | ✓ |
| 16 | Security matrix coverage | `pytest tests/test_security_benchmark.py -q` | CI | passed | `governance` | ✓ | ✓ | ✓ |
| 17 | Integrity / CI-gov / harness / contracts / QA-capability | the five `scripts/check_*.py` | CI | pass | `governance` | ✓ | ✓ | ✓ |
| 18 | Compose renders | `docker compose … config --quiet` ×3 | CI | renders | `qa-contract-render` | ✓ | ✓ | ✓ |
| 19 | **Real browser journeys** | container-first Playwright, changed surfaces | CI container | dated verdicts | `ui-journeys` | ✓ | ✓ | ✓ |
| 20 | Roles / themes / 375px / focus / states | journey matrix | CI container | pass or `not_runnable` | artifacts | ✓ | ✓ | ✓ |
| 21 | Research Spine non-bypass | spine probes + contract tests (§F) | CI | pass | CF row | ✓ | ✓ | ✓ |
| 22 | Self-improvement governance | `pytest tests/test_improvement_governance.py -q` | CI | pass | `backend-test` | ✓ | ✓ | ✓ |
| 23 | Index freshness | `index status` | local | fresh, `warnings: []` | CF row | ✓ | ✓ | ✓ |
| 24 | Impact per changed surface | `intelligence impact --path <p>` | local | `confidence` recorded | CF row | – | ✓ | – |
| 25 | No release-blocking CF task | `task list --status open` + triage | local | zero blocking | triage table | ✓ | ✓ | ✓ |
| 26 | Wave manifest integrity | `scripts/verify_wave_manifest.py` | local | matches | CF row | ✓ | ✓ | ✓ |
| 27 | Branch protection | `gh api …/branches/main/protection` | GitHub | matches D.2 | dossier JSON | ✓ | – | ✓ |
| 28 | Simulation/RUB static | `npm run test:static`, `npm run check` | CI | 111 / 107 | `test-harness-js` | ✓ | ✓ | ✓ |
| 29 | Production rehearsal | `scripts/production_rehearsal.py --json` | CI | pass | `backend-test` | ✓ | ✓ | ✓ |
| 30 | Backend mutation gate | `scripts/run_backend_mutation.py` | CI | pass | `backend-test` | ✓ | ✓ | ✓ |
| 31 | Blind review dry | reviewer verdicts | — | pass, no open findings | `review_verdict` | ✓ | ✓ | ✓ |
| 32 | SHA still current | `git rev-parse testing` = `CANDIDATE_SHA` | local | equal | dossier | ✓ | ✓ | ✓ |

Rows 4–20 are the release-critical core. **Every row marked `Re` must be re-executed on the frozen
SHA** — this plan treats pre-freeze results as diagnostics, never as certification.

---

## F. Research Spine assurance

The spine is:

```
Sources → Evidence Units → Independent Multi-Model Atomic Extraction + Open Coding
→ Reliability + Grounding → Reconciliation → Accepted Atoms/Nuggets → Facts → Insights
→ Recommendations → In Review → Human-Approved Done → Reports
```

**Changed research-data paths in this candidate.** The tree touches
`backend/app/services/research_validity_service.py`,
`backend/app/services/research_validity_evidence_units.py`, `backend/app/core/report_manager.py`
(graph neighbour), 48 modified `tests/simulation/scenarios`, and adds ~71 untracked files under
`tests/document_corpus/rich/**` (sources, chat-packs, context, method).

**The corpus addition is the spine-relevant risk and needs stating plainly.** A large new document
corpus entering the repository is exactly the shape of change that can introduce pre-digested
evidence — source files that already contain conclusions — which would let synthesized prose enter as
if it were a raw source span. The audit already defends this: `RAW_SOURCE_FORBIDDEN` rejects
`## Evidence unit candidate`, `Coding hints:`, `Implication candidate:` and `Report gate reminder:` in
canonical sources, and `scan_repeated_source_excerpts` catches duplicated excerpts. That defence only
runs over **tracked** files, so it says nothing about the corpus until Wave 1 commits it — another
consequence of F-B01's tracked-only scan surface, and the reason the audit must be re-run
post-commit.

**Wave 2/5 obligations.** For each changed path, trace and record: evidence units are created before
any atom; extraction identities are genuinely independent models, not one model twice; reliability and
grounding are computed, not defaulted; reconciliation is not bypassed for single-coder input; artifacts
stay provisional until accepted; raw source spans (not nugget prose) are the evidence basis; route
evidence is recorded; the Done/report gate requires human approval.

**Self-improvement boundary.** Confirm telemetry, ReasoningBank, Memento Skills, Autoresearch,
Meta-Hyperagent, Self-Evolution, RAG/GraphRAG/Prompt-RAG and LLMLingua cannot manufacture report
evidence, weaken authorization, silently alter protected methodology, promote project-scoped evidence
globally, or learn strong positive signals from raw tool success.
`tests/test_improvement_governance.py` and `tests/test_agent_learning_scope.py` are the executable
gates; `docs/architecture/research-validity-contract.md` and
`docs/architecture/self-improvement-governance-contract.md` are the written contracts, and both must
be re-read against the actual diff rather than assumed current.

**Disposition:** any discovered bypass is architecture debt. If it is reachable by a research-data
path in this candidate, promotion is **blocked**; if unreachable, it is recorded with a named
follow-up spec. This determination happens in Wave 2 and is re-proven in Wave 5 (matrix row 21).

---

## G. Owner-gated operations

Automated waves must **never** perform these. Each requires explicit owner authorization at the time.

| # | Operation | Why gated |
|---|---|---|
| 1 | `git reset --hard`, `git clean`, `git checkout -- .`, `git stash drop` | destroys unclassified local work irreversibly |
| 2 | Deleting or moving `LLMs/`, `Model_Finetuning/`, or any local artifact | protected, gitignored, irreplaceable |
| 3 | Deleting/pruning any untracked file | 119 exist; classification is judgement-based |
| 4 | Force-push, or any write to `main` | protection currently permits it — the guard is policy, not mechanism |
| 5 | Starting servers, loading models, contacting a provider | live-safety contract; passive discovery stays passive |
| 6 | Reading, printing or persisting secrets, endpoints, fingerprints, tokens, connection strings | disclosure risk |
| 7 | Mutating GitHub repository settings, incl. branch protection | out-of-repo state; F-B06 prepares, owner applies |
| 8 | Creating the promotion PR | only via `promote-testing.yml` with environment approval |
| 9 | Merging to `main` | the terminal decision; never automated |
| 10 | Lowering any mutation/security/quality/accessibility/spine threshold | requires an explicit, justified owner decision |
| 11 | Rewriting an existing ledger entry | ledgers are append-only |
| 12 | Closing a CF task without cited evidence | staleness must be proven |

Two additional owner pauses are structural: the Wave 1 `UNDECIDED` review, and the Wave 4 → owner
protection ordering hazard (renaming job contexts while `main` requires the old names).

---

## H. Final release criteria

One binary verdict. **READY** requires **every** line below; any miss yields **NOT READY** with the
failing criterion named. There is no partial or conditional readiness.

1. **Exact candidate SHA** — `CANDIDATE_SHA` frozen, recorded in the CF spec, lifecycle status block
   and dossier, and still equal to `testing` HEAD at dossier close.
2. **Clean intended worktree boundary** — every path classified; residual dirt is only `AMBIENT`/
   `UNDECIDED`, each accounted for; protected directories untouched; recovery snapshot verified.
3. **All required CI green on that SHA** — every D.2 context, on `CANDIDATE_SHA` itself, not an
   ancestor and not a re-run of an earlier commit.
4. **Container-first UI verdicts** — dated, artifact-backed, for every changed behaviour; every
   `not_runnable` explicit and owner-visible.
5. **Security benchmark current** — `--fail-on-threshold` green on the frozen SHA, with the changed
   control matrix (F-B15) covered by tests.
6. **Mutation thresholds met without lowering** — ≥75 from real test improvement, with the
   killed/survived/no-coverage triple recorded.
7. **No open release-blocking CF tasks or specs** — proven by the 181-task triage, not asserted.
8. **Reconciled Build Stream ledgers** — every recent initiative has exactly one status; every
   referenced lifecycle file is tracked at the frozen SHA.
9. **Blind independent review pass** — comprehensive review plus delta re-reviews until dry, with no
   open findings.
10. **Branch protection aligned** — owner-applied, re-read from the API and attached as evidence.
11. **Promotion dossier complete** — §E matrix with results, findings register with dispositions,
    classification TSV, triage table, journey verdicts, scorecards, protection JSON.
12. **Owner approval still pending** — the dossier ends at the decision point. No PR, no merge.

**Explicitly not evidence of readiness:** a green process, container, workflow or artifact; a green
run on an ancestor SHA; `main`'s historic green runs (it has never contained this architecture); a
local result from an unpinned node 26 environment; or a compose file that renders.

---

## Coverage of the assignment's thirteen objectives

| # | Objective | Where |
|---|---|---|
| 1 | Frozen auditable candidate boundary | §A, Wave 1, criterion 1–2 |
| 2 | Every recent plan reconciled | F-B10, Wave 2, criterion 8 |
| 3 | No loss or accidental inclusion | §A.3 five-bucket rule, §G 1–3, criterion 2 |
| 4 | CF index/specs/tasks/gates/evidence reconciled | F-B08, F-B09, Wave 2, criterion 7 |
| 5 | All blocking failures repaired | F-B01/02/14/16/17, Wave 3, criteria 3, 5 |
| 6 | Mutation improved, never lowered | F-B03, Wave 3–4, criterion 6 |
| 7 | Independent failure domains still report | F-B05, §D.1, Wave 4 |
| 8 | Main-required checks aligned | F-B06, §D.2, criterion 10 |
| 9 | Real container-first acceptance | F-B04, Wave 5, criterion 4 |
| 10 | Spine/self-improvement non-bypassable | §F, criterion 4/9 |
| 11 | Security evidence current | F-B15, criterion 5 |
| 12 | Blind review remediated until dry | Wave 6, criterion 9 |
| 13 | Dossier tied to one SHA | Wave 6, §H, criteria 1, 11 |
| 14 | No automatic merge | §G 8–9, criterion 12 |

---

## Residual risks in this plan

1. **Wave 3 may expand.** The full backend suite has never been observed green on this candidate,
   because formatting aborts the job before it runs. Failures may be hiding behind that gate.
2. **Wave 5 is the largest unknown.** Journey authoring effort is unestimated here, and it is the
   wave most likely to find real product bugs, looping back to Wave 3.
3. **The Wave 4 → protection ordering hazard** can leave `main` requiring contexts that no longer
   exist. It needs deliberate sequencing with the owner.
4. **The 181-task triage is manual** and its main danger is misfiling a real blocker as
   administrative — mitigated by requiring an evidence citation per closure.
5. **The worktree is shared and live** (F-B11). Between freeze and promotion, any write forces a
   re-freeze.
6. **I could not verify the remote CI run contents** — GitHub Actions run 34039897688 was read only
   through the brief's summary. The remote mutation figure reconciles exactly with the local config
   (95/130 = 73.08%), which corroborates it, but the CI log itself is unverified by me.
7. **Two brief claims I could not fully resolve**: the local Stryker plugin initialisation failure
   (I confirmed versions are compatible and identified node 26 vs 24 as the likely cause, but did not
   reproduce it, as running mutation locally is expensive); and whether the 378 advisory backend lint
   errors contain further correctness-class findings beyond the two F821s — the F-B02 correction
   makes that class visible going forward regardless.
