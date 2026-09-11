# MECE Master Plan — testing → main promotion convergence (Synthesis C)

- **Task:** testing-to-main-20260909-MASTER-C (CF-SPEC-30, slot `c`, phase `synthesize`, round `b35539f4f7bdabc5be5f`)
- **Role:** testing-to-main-20260909-architect-c · conductor model zai/glm-5.3-flash (effort=max)
- **Status:** synthesis candidate for cross-vote. No code, branch, threshold, or lifecycle-plan content was changed by this planning run. Owner approval is required before any implementation wave.
- **Sources (immutable snapshots, read in full):**
  - Slot A — gpt-5.6-sol (effort=low): `7d248018…79c71c` — "Candidate D" custody plan
  - Slot B — claude-opus-5 (effort=high): `1285af17…60bc1` — measured-reality plan (F-B01…F-B19)
  - Slot C — zai/glm-5.3-flash-max (effort=max): `d6c89546…c60bea` — freeze-and-reconcile plan (F-C-01…F-C-21)
- **Snapshot integrity note:** `sha256sum` of each snapshot file does **not** equal its conductor `candidate_id`; the candidate_id is computed on a conductor-internal basis (the same undocumented-canonicalisation folklore Plan B documented for the wave manifest, F-B07). Snapshots were consumed as delivered; this is recorded, not treated as tampering.

---

## 0. Synthesis method

All three snapshots were read end-to-end. Where the drafts disagree, the conflict was re-measured with read-only, credential-free commands in this synthesis session; every arbitration below cites the measured value. Nothing was implemented, reset, cleaned, deleted, pushed, or probed live.

### 0.1 Conflicts found and arbitrated (measured 2026-09-09, this session)

| # | Conflict | Drafts | Measured resolution |
|---|---|---|---|
| K1 | Frontend lint error count: 1 error (B, C) vs "233 errors, 82 warnings — materially wider" (A) | A vs B/C | `eslint .` (the `lint` script) reports 233 errors / 82 warnings — but ~232 of them are **phantom errors from `.stryker-tmp/sandbox-*/`**, a leftover crashed-Stryker sandbox directory that the eslint config does not ignore (220 × `ban-ts-comment`, plus `no-var`/`prefer-rest-params`/`prefer-spread`, one per sandbox file). The real source tree has **exactly 1 error**: `src/components/chat/ChatModelControls.tsx:20` `no-empty-object-type`. A measured the raw output; B/C measured the source. Both were "right"; the root cause is a lint-config ignore gap plus mutation-harness residue. → M-09, M-13. |
| K2 | Compass Forge index: "schema 12 unusable, refresh to 21, `graph_usable=false`" (brief, A) vs "index_version 12 is current Rust output; bare `impact` is `not_yet_native`; `intelligence impact --path` works" (B) vs "refresh, verify schema ≥ 21" (C) | A/B/C | Measured: bare `impact` → `{"code":"not_yet_native"}`; `intelligence impact --path backend/app/core/report_manager.py` → `graph_source: tree-sitter`, `confidence.level: high`; response keys contain **no** `resolution`/`answer_completeness`/`freshness`/`graph_usable`; `index status` → `index_version: 12`, `kernel: rust`, `warnings: []`, created 2026-09-09T14:48:19Z, 941 files. **B is correct**: "12 vs 21" is unsupported; there is no schema-21 target to chase and no `graph_usable` flag to read. A deliberate `refresh-project` for freshness is still worthwhile; the `impact`/`graph` `not_yet_native` gap is architecture debt. → M-13. |
| K3 | Worktree drift: brief 118 untracked / 4,706 ins vs B/C 119 / 4,712 | B, C vs brief | Re-measured: 155 modified, +4,712/−977, 119 untracked — B/C correct. The drift B worried about is now explained: local HEAD moved `85f64e4d` → `50c4d493`, and those three commits are the planning pipeline's own draft-plan commits (PLAN-A fallback, PLAN-B, PLAN-C). Refs are unchanged (`origin/testing` = `9961fa3d`, 67 ahead of it now). The surface moved because the pipeline commits its own plans — freeze discipline (M-01) must account for exactly this. |
| K4 | Untracked lifecycle files: 17 (B) vs 10 (C) | B vs C | Measured: **17** untracked paths under `docs/build-stream/` (C counted only the Sep 6–9 window). B's number governs; all 17 must be resolved before freeze. → M-11. |
| K5 | Candidate assembly: isolated worktree "Candidate D" (A) vs in-place classification + commits on local `testing` (B, C) | A vs B/C | **Synthesis decision: in-place on local `testing`** (B/C), with A's protections absorbed: byte-preserving recovery bundle + untracked tarball + porcelain snapshot before anything (B), hunk-level splitting only where one file mixes release and ambient provenance (A), quarantine branch for ambiguous work (C). Rationale: the conductor pipeline, QA lanes, and evidence rows all operate on this worktree; an isolated worktree would fork the surface the rest of the machinery certifies. Isolation is achieved instead by append-only refs + verified backups + the no-destructive-ops rule (§G). |
| K6 | Freeze semantics: single freeze after all waves (A) vs freeze after Waves 1–5 (B) vs Candidate Base + Promotion SHA (C) | A/B/C | **Synthesis decision: C's two-stage freeze.** Candidate Base SHA after W0 classification commits; Promotion SHA at W7. Every evidence row records the SHA it ran on; a post-freeze change invalidates SHA-sensitive downstream evidence (A's invalidation rule) and forces re-verification of everything the change touches, with the full §E matrix re-run on the final Promotion SHA. |
| K7 | Required-check mechanism: fail-closed `release-gate` aggregator (A) vs granular required contexts (B, C) | A vs B/C | **Synthesis decision: granular required contexts** from a committed required-checks manifest enforced by a checker script (C's M-21), plus honest job names (B). A single required context is weaker here: a required context that never reports blocks merge, so granular contexts fail closed naturally; an aggregator would create a second source of truth that itself needs protecting. A's aggregator is recorded as considered-and-rejected (§I). A's `if: always()` + skipped-job audit survives as a checker-script rule. |
| K8 | Snapshot hashes vs candidate_ids | this synthesis | `sha256sum` of the three snapshot files ≠ their `candidate_id`s (see header note). Recorded as evidence folklore debt; folded into M-19's "document the hash recipe" correction. |

### 0.2 Coverage matrix — which draft each major section incorporates

| Master section | Slot A | Slot B | Slot C | Synthesis-only |
|---|---|---|---|---|
| A. Candidate definition | hunk-level manifest, byte-preservation, commit patch-id classification | recovery bundle + tarball, five-bucket classification, `git add --pathspec-from-file`, freeze-on-`testing`, `promote-testing.yml` anti-replay kept intact | surface verdict (C selected; B internally broken), C1–C6 classes, dependency-closure proof, backup + quarantine branches, drift rules, two-stage freeze | K3/K5/K6 arbitrations; moving-surface cause identified |
| B. Findings register | custody/observability/aggregator framing (A-F01, A-F10) | F-B01…F-B19 (public-quality root cause, F821 proof, mutation anatomy, CF corrections, protection detail) | F-C-01…F-C-21 (untracked-import proof, ruff pin, SC-002 dependency, corpus verification, doc drift) | K1 lint-contamination finding; K2/K3 arbitrations |
| C. Wave manifest | W0 custody rigor, W2 obligation matrix, W8 stage separation | conductor 6-ID mapping, evidence rules, per-wave review questions | W0–W7 mapping, W2/W3 and W4/W5 splits, rollback shapes | merged into 8 waves keyed to the conductor's 6 IDs |
| D. CI architecture | independent failure domains, SHA-bound artifacts, aggregator (rejected) | honest naming (`qa-contract-render`), required-checks table, event matrix, mutation advisory-first, ordering hazard | job graph, required-checks manifest + checker, no-`continue-on-error` audit, concurrency, weekly schedule, desktop default | K7 arbitration |
| E. Verification matrix | custody/manifest rows | probe rows (`get_type_hints`, manifest verify, audit-after-commit) | CI `headSha` binding, stage rows | merged, deduplicated |
| F. Research Spine | trace table + invariants 1–8 | corpus = pre-digested-evidence risk; `RAW_SOURCE_FORBIDDEN` scans tracked files only; audit re-run post-commit | corpus verified synthetic + tests-only; contract tests as executable gates; reviewer re-confirmation duty | corpus disposition: include + scan-after-commit |
| G. Owner-gated ops | pause-point list (before W0/W5/live/W8) | 12-row table incl. ledger-append-only, evidence-cited closure | 8-item list incl. badge-sync fix precondition | unified list + 5 pause points |
| H. Release criteria | default-NOT-READY binary | "not evidence of readiness" list | stage-separation table (transported→deployed), merge-mechanics decision | merged |

---

## A. Candidate definition

### A.1 Measured state (re-confirmed this session, 2026-09-09)

| Fact | Value | Command basis |
|---|---|---|
| Local `testing` HEAD | `50c4d493` (moved from `85f64e4d` during planning; delta = the three draft-plan commits) | `git rev-parse HEAD`; `git log --oneline -5` |
| `origin/testing` | `9961fa3dbd2ce03a6e1d8cc3e303478edaf17a79` | `git rev-parse` |
| `origin/main` | `fa6a1a391b5a1089690eb8fed5d179ce146ec9e9` — strict ancestor of `origin/testing`; promotion is fast-forwardable | `git merge-base`, `rev-list --left-right --count origin/main...origin/testing` = `0 994` |
| Local vs `origin/testing` | 67 ahead / 0 behind | `rev-list --left-right --count origin/testing...HEAD` |
| Working tree | 155 modified tracked files, +4,712/−977; **119 untracked** files | `git diff --shortstat HEAD`; `git status --porcelain -uall` |
| Untracked lifecycle files | **17** under `docs/build-stream/` (incl. this initiative's own convergence file) | `git status --porcelain -uall -- docs/build-stream` |
| Whitespace debt | 295 trailing-whitespace / blank-at-EOF findings vs `origin/main` | `git diff --check origin/main \| wc -l` |
| Backend format debt | 15 files would be reformatted (local venv); CI resolved ruff 0.16.6 vs local floor `ruff>=0.8.0` (pyproject:62) → version drift | B + C measurements; `grep ruff backend/pyproject.toml` |
| Frontend lint (source tree) | exactly 1 error: `ChatModelControls.tsx:20` empty interface | K1 measurement above |
| Frontend mutation gate | mutates exactly `src/lib/runtimeConfig.ts` (82 lines, unmodified by this candidate); thresholds {high 90, low 80, break 75}; `related: true`; remote score 73.08 = 95/130 killed | `frontend/stryker.config.json`; CI run 34039897688 |
| Public-quality audit | 2 findings: `AGENTS.md:142` ("Project root: …" absolute machine path) and one tracked lifecycle doc line; `tests/test_public_repo_quality.py` fails | B + C measurements; `grep -n "Project root" AGENTS.md` |
| Remote CI run 34039897688 | red on A: frontend mutation 73.08 < 75; backend format (2 files at that SHA) aborts before full pytest; governance/feature-obligations/test-harness/qa-contract-stack green | `gh run view` (B, C, read-only) |
| Branch protection on `main` | required = ["governance"] only; 0 approvals; no code-owner review; dismiss-stale off; `enforce_admins` false; **force pushes allowed**; `strict: true` (the one bright spot) | `gh api …/branches/main/protection` (B, C) |
| Compass Forge | 413 tasks, **181 open**; CF-SPEC-29 ×13 open (blocks CF-SPEC-30 acceptance via SC-002); bare `impact`/`graph` `not_yet_native`; `intelligence impact --path` works (tree-sitter, high confidence); index_version 12 = current Rust output, `warnings: []` | `task list`, `index status`, `intelligence impact` (this session) |
| Security evidence | `security/control_matrix.json` +6 lines (audit.py, metrics.py added to two control scopes; audit_middleware.py, VersionHistory.tsx), `SECURITY_BENCHMARK.md` +1 → benchmark rerun mandatory | `git diff --stat -- security/` |
| Doc drift | `docs/architecture/research-validity-contract.md:3` cites "CF-SPEC-124 / CF-1590" — nonexistent objects | `grep` (this session) |

### A.2 Surface verdict

| Surface | Contents | Verdict |
|---|---|---|
| A — `origin/testing` (`9961fa3d`) | pushed, 994 commits over main | **Rejected.** Missing all 64+ local commits and the entire classified working tree; its CI run is red. |
| B — local committed `testing` | A + 64→67 commits | **Rejected and internally broken.** Working-tree *tracked* files import **untracked** modules: `git grep tokenStore HEAD -- frontend/src` → 0 hits, while 22 working-tree files reference `@/lib/tokenStore` (also `SeeMoreList.tsx`, `ToolAuditTrailTable.tsx`). Surface B cannot typecheck or build. |
| **C — local commits + classified working tree** | B + all classified working-tree content | **SELECTED — the only functionally complete candidate**, and the surface all known-green evidence was measured on. |

Rule: the candidate is C, and only C. Nothing is pushed during implementation until W7's owner-gated push step; `main` is written by no wave.

### A.3 Reconciliation algorithm (classify → include deliberately; never destroy)

1. **Recovery point first (before any git mutation).** `git bundle create` of `--all` to an owner-readable location outside the repository; `tar` of every untracked file (`git ls-files --others --exclude-standard`); `git status --porcelain=v1` snapshot; stash list recorded (never dropped); local branch `backup/pre-candidate-20260909` at HEAD. Verify the bundle and tarball restore into a scratch directory before proceeding. `LLMs/` and `Model_Finetuning/` are never enumerated beyond confirming they remain ignored and untouched.
2. **Inventory.** `git status --porcelain -uall`; `git diff --numstat HEAD`; ignored roots listed read-only. Expand directory-level `??` entries to leaf files.
3. **Classify every path into exactly one class**, recorded in a committed Candidate Classification Manifest (`docs/promotion/2026-09-09-candidate-classification.md`):
   - **C1 include — product code** (`backend/`, `frontend/src`, `relay/`, `desktop/`, `pi-runtime/`, `recipes/`, `qa/`, root configs);
   - **C2 include — tests & fixtures** (incl. `tests/document_corpus/rich/**` after the M-17 synthetic-content verification);
   - **C3 include — docs/lifecycle** (all `docs/**` incl. the 17 untracked lifecycle files, `TESTING.md`, `testing/*`, `AGENTS.md`, security evidence files);
   - **C4 exclude — generated** (`node_modules`, `.stryker-tmp`, `.results`, build output, caches): present locally, never committed, never deleted;
   - **C5 exclude — protected/local** (`LLMs/`, `Model_Finetuning/`, `.compass-forge/`, `.env*`, keys): never committed, never deleted;
   - **C6 quarantine — ambiguous/ambient**: committed to branch `quarantine/ambient-20260909` (created at current state, non-destructive), left out of the candidate, working-tree copy untouched, owner arbitrates later.
   **Evidence rule (B):** C1/C2 inclusion requires at least one of — named in a lifecycle ledger `Did:` line; required by an open/accepted CF task or spec; a test/fixture required by included source; required to make a blocking check pass. Untracked C1 files additionally require **dependency-closure proof** (≥1 tracked/modified importer — the test that validated `tokenStore.ts` et al.); files with no importer are demoted to C6. **Default for anything unproven is C6, never silent inclusion.**
4. **Hunk-level split (A's rule, narrow use):** only where one file demonstrably mixes release edits and ambient edits, reproduce the release hunks as a patch applied in the candidate commit rather than staging the whole file. The shared file is never edited or reset to achieve the split.
5. **Commit by explicit path list only:** `git add --pathspec-from-file` in a small number of reviewable commits (e.g. "candidate: frontend chat/model work", "candidate: tests & corpus fixtures", "candidate: docs & lifecycle"). `git add -A`, pathless commits, `git clean`, `reset --hard`, `checkout -- .`, and `stash drop` are forbidden everywhere (§G).
6. **Candidate Base SHA.** After the classification commits: record the SHA in the lifecycle status block, the manifest, and CF evidence; create a **local-only** annotated tag `rc/testing-to-main-20260909` (no push). The `promote-testing.yml` anti-replay check (promoted SHA must equal `testing` HEAD) keeps working because `origin/testing` is only ever fast-forward-updated.
7. **Promotion SHA (W7).** The last commit after repair waves; the full §E matrix re-runs on it; the dossier records `git log --oneline <Candidate-Base>..<Promotion-SHA>` as the post-freeze audit trail.

### A.4 Drift-prevention rules

1. No force-push, amend, or rebase of any commit a prior wave's evidence refers to.
2. Every wave's ledger entry records HEAD SHA before and after (`git rev-parse` in evidence rows).
3. Between waves, only wave-owned paths may change; the wave's evidence must explain any other path (new ambient edits → C6 quarantine, never into the wave).
4. CI/verification evidence must bind to the exact SHA it ran on; the dossier's final check is `git rev-parse testing == CANDIDATE_SHA` before any promotion evidence is considered valid.
5. Between freeze and promotion the owner is asked to avoid writes to the checkout, or accept re-freeze.

### A.5 Rollback and recovery

| Failure | Recovery |
|---|---|
| Wrong file included | `git revert` that commit; re-freeze at a new SHA |
| Wrong file excluded | it still exists in the worktree or quarantine branch; classify and include next release |
| Local work appears lost | restore from the W0 bundle + tarball into a scratch tree and compare |
| Candidate proves unshippable | abandon the SHA; `origin/testing` history intact (append-only); `main` never moved |
| Lifecycle record wrong | append a correcting ledger entry — never rewrite history |
| CF state damaged | restore only from a verified native CF backup; never Python/PATH fallback |

---

## B. Findings register

Severity: **S1** blocks promotion · **S2** blocks unless owner accepts with rationale · **S3** fix this release · **S4** record/defer. Wave = owning wave in §C.

**M-01 · S1 · Candidate custody.** Evidence: three divergent surfaces; worktree moved `85f64e4d`→`50c4d493` during planning (the pipeline's own plan commits — K3). Root cause: no freeze ritual; pipeline commits its own artifacts onto the candidate branch. Consequence: any "green" claim is unfalsifiable; ambient work can be lost or silently shipped. Correction: §A.3 protocol → Candidate Base SHA + manifest + local tag. Verification: manifest committed; `git status` clean-for-scope; SHAs recorded in lifecycle + CF. Wave W0. **Blocking.**

**M-02 · S1 · Candidate identity.** Evidence: surface B cannot build — 0 committed importers of `tokenStore` vs 22 working-tree references (K-verified). Root cause: feature work split across tracked edits + untracked new modules. Consequence: promoting any ref that is not C ships a broken frontend or drops feature work. Correction: candidate = C per §A.2. Verification: `npx tsc --noEmit` on the frozen candidate. Wave W0. **Blocking.**

**M-03 · S1 · Remote CI red.** Evidence: run 34039897688 on `9961fa3d` — frontend mutation 73.08 < 75; backend format aborts before the test step runs. Root cause: real quality/format debt + sequential job design (M-16). Consequence: pushed `testing` is not promotable; functional signal hidden. Correction: repair on the candidate (M-04…M-10), then green run on the Promotion SHA. Wave W2–W7. **Blocking.**

**M-04 · S1 · Backend format + tool drift.** Evidence: 15 files fail `ruff format --check`; CI 0.16.6 vs local floor `ruff>=0.8.0` (pyproject:62) → formatter output varies by machine. Root cause: floating floor + no format-on-commit hook. Consequence: non-reproducible format gate; CI red. Correction: `ruff format` once with a **pinned exact version equal to CI's resolution**; pin it in dev deps; add pre-commit hook. Verification: `ruff format --check .` exit 0 on the Promotion SHA in both environments. Wave W2. **Blocking.**

**M-05 · S1 · Correctness escaping the lint gate (F821).** Evidence: `backend/app/core/token_counter.py:105` (`BudgetAllocation`) and `backend/app/core/compute_registry_helpers.py:253` (`ComputeNode`) — no import anywhere, no `TYPE_CHECKING` guard; `typing.get_type_hints` raises `NameError` (B's proof). Root cause: changed-file lint is blocking, global lint is `continue-on-error`, so the correctness class is invisible on unchanged files. Consequence: latent runtime 500s the moment hints are resolved. Correction: `TYPE_CHECKING` imports for both names; promote the correctness subset (`F821,F811,F822,E999`) to repo-wide **blocking**; keep the ~378-error style backlog advisory with a burn-down note. Verification: `ruff check backend/ --select F821,F811,F822,E999` → 0; the `get_type_hints` probe returns; full suite green. Wave W2 (fix) / W4 (gate). **Blocking.**

**M-06 · S1 · Frontend mutation gate hollow and brittle.** Evidence: mutates only `runtimeConfig.ts` (82 lines, unmodified by this candidate); 95/130 = 73.08; 21 survived + 14 no-coverage; `related: true` makes no-coverage a test-selection artifact (B's anatomy, arithmetic reconciles exactly). Root cause: tests assert happy paths only; gate scope promises far more than it measures. Consequence: release blocked by a gate measuring almost nothing; passing it would create false confidence. Correction: extend `runtimeConfig.test.ts` to kill the 21 survivors and cover the 14 no-coverage mutants (implementation fixes where a mutant exposes a real bug — `runtimeConfig` derives origin/websocket URLs, auth-adjacent); target ≥ 90, not bare 75; never lower thresholds; scope expansion advisory-first with its own threshold, promoted to blocking only by owner decision. Verification: `npm run test:mutation` ≥ 75 with the killed/survived/no-coverage triple recorded from the raw report (score arithmetic re-derived, not the summary line). Wave W3. **Blocking.**

**M-07 · S2 · Local mutation harness + node drift.** Evidence: local Stryker vitest-runner plugin init failure; local node v26 vs CI node 24; a `.stryker-tmp/sandbox-*` residue from the crashed run contaminates local lint (K1). Root cause: unpinned node major + corrupted/partial `node_modules` (all package peer versions verified consistent — B). Consequence: local mutation numbers are not authoritative; tooling residue pollutes other gates. Correction: bounded, owner-visible `npm ci` reinstall in `frontend/` (C4 generated dir); pin node 24 via `.nvmrc`/`engines`; treat CI (node 24, `npm ci`) as the authoritative mutation lane; the `.stryker-tmp` ignore fix lands with M-09. Verification: mutation completes in the node-24 lane; `node -v` recorded with every local frontend result. Wave W3. **Blocking for W3 evidence.**

**M-08 · S1 · Public-quality leak, regenerated by the process itself.** Evidence: `audit()` returns exactly 2 findings; `machine_checkout_path` is the rule **name** — the forbidden text is the machine-local absolute checkout path, present at `AGENTS.md:142` ("Project root: …") and one tracked lifecycle-doc line; literal `grep machine_checkout_path` finds nothing (the brief's phrasing would send an implementer to "fix" a working audit). Root cause: the conductor protocol hands every worker the absolute path and has it write lifecycle entries the audit scans — the leak is systematically regenerated every wave; the audit also scans **tracked files only**, so committing the 17 untracked lifecycle files grows its scan surface. Consequence: private filesystem layout published; a correct gate at risk of suppression. Correction: rewrite both lines to repo-relative form ("repository root"); **never edit the audit**; add a pre-commit hook + fast CI step running the audit `--check`; add a protocol rule (lifecycle entries use repo-relative paths); **re-run the audit after the candidate commits** (scan surface grows). Verification: `pytest tests/test_public_repo_quality.py -q` green on the frozen SHA + a negative test that reintroducing the path fails. Wave W0 (hook/protocol) / W2 (text) / W7 (re-verify). **Blocking.**

**M-09 · S1 · Frontend lint — one real defect, hidden in phantom noise.** Evidence: source tree = exactly 1 error, `ChatModelControls.tsx:20` `interface ModelChoice extends ChatModelChoice {}` (A's "233 errors" was `.stryker-tmp` contamination — K1). Root cause: interface-alias idiom; eslint config does not ignore the Stryker sandbox. Consequence: CI frontend lint red at next push; local lint output unusable. Correction: `type ModelChoice = ChatModelChoice;` (behaviour-identical; verify use sites); add `.stryker-tmp` to the eslint ignore list. Verification: `npm run lint` exit 0 (with sandbox present or absent); `npx tsc --noEmit` clean. Wave W2. **Blocking.**

**M-10 · S2 · Whitespace debt.** Evidence: 295 `git diff --check origin/main` findings, concentrated in `docs/build-stream/*` plus 4 code files. Root cause: no whitespace guard; agent-authored Markdown carries trailing spaces. Consequence: noisy diffs; hygiene-gate failures. Correction: strip trailing whitespace/EOF blanks on affected files (append-only constraint: historical ledger prose is repaired only in non-ledger regions, or the touch is recorded in the decision log); add `git diff --check` to the pre-commit hook and a blocking docs-scoped CI hygiene step. Verification: `git diff --check origin/main` → empty on the frozen SHA. Wave W2. **Blocking.**

**M-11 · S1 · Lifecycle truth uncommitted and self-contradictory.** Evidence: 4 contradictory STATUS BLOCKs (pi-capability-inheritance S3/in-progress/"may dispatch implementation"; long-horizon S1/in-progress; benchmark-modernization S0/owner-blocked **while** next-action claims Done; systemwide-audit Done with accepted-risk F-007 + deferred matrices); **17 untracked lifecycle files incl. this initiative's convergence file**. Root cause: ledgers updated without status-block discipline; recent lifecycle docs never committed. Consequence: agents dispatch completed work or certify unfinished work; the release's own narrative record does not exist in the release. Correction: per recent initiative, resolve to exactly one disposition (included / excluded / superseded / completed / deferred, with rationale); correct status blocks by **appending** correcting entries; commit the reconciled files in the candidate commits; populate `cf.tasks` in the convergence file. Verification: status blocks parse and agree with last ledger; every Sep 6–9 lifecycle file tracked at the frozen SHA; no file claims two stages. Wave W0 (commit) / W1 (truth reconciliation). **Blocking.**

**M-12 · S1 · Compass Forge task/spec debt.** Evidence: 181 open tasks (413 total); CF-SPEC-29 ×13 open (CF-344…356); CF-SPEC-19/25/28 also non-terminal; CF-SPEC-30 SC-002 ("no linked task incomplete at spec acceptance") makes this a hard dependency of the pipeline itself. Root cause: spec templates emit tasks; specs accepted without closing children. Consequence: "no open release-blocking CF tasks" is currently unprovable; CF-SPEC-30 can never be accepted. Correction: triage all open tasks into `stale-administrative` (parent accepted, work evidenced elsewhere), `genuinely-open-not-release-blocking` (deferred to a named future spec), `release-blocking` (close in this release) — closure only **with cited evidence**; explicit disposition for CF-SPEC-19/25/28/29; nothing closed by assumption. Verification: triage table in the dossier; zero `release-blocking` tasks at freeze; every closure carries an evidence citation. Wave W1. **Blocking (release-blocking bucket only).**

**M-13 · S1 · CF impact capability gap (brief's diagnosis corrected).** Evidence: bare `impact`/`graph` → `not_yet_native`; `intelligence impact --path` works (`graph_source: tree-sitter`, `confidence.level: high`); response has no `resolution`/`answer_completeness`/`freshness`/`graph_usable` keys; `index_version: 12` is the current Rust kernel's own output with `warnings: []` (K2). Root cause: Rust migration gate renamed/limited commands; the "schema 12 vs 21" claim is unsupported. Consequence: a wave told to "refresh until graph_usable" is unexecutable; reviewers would demand nonexistent fields. Correction: waves call `intelligence impact --path <p>` and read `confidence` + `graph_source`; index freshness asserted via `index status` (`created_at` newer than the last candidate commit, `warnings: []`) after a deliberate `refresh-project`; record the command-name migration and the `not_yet_native` gap as architecture debt; **never fabricate impact output**; follow dependencies manually past the static graph (dynamic dispatch/string routes absent from it). Verification: `index status` fresh at each wave's start; one recorded `intelligence impact` per changed architectural surface. Wave W1. **Blocking (plan executability).**

**M-14 · S1 · Branch protection does not enforce the architecture.** Evidence: required = ["governance"] only; 0 approvals; no code-owner; dismiss-stale off; `enforce_admins` false; force pushes allowed; `strict: true` retained. Six of seven current CI jobs are advisory at the merge gate. Root cause: protection never grew with the workflow. Consequence: every other finding here is unenforced at the boundary that matters. Correction (owner-gated, §G): require the §D.3 context set on `main` and `testing`; ≥1 approving review; code-owner review; dismiss stale; enforce admins; disallow force pushes; require linear history; keep strict up-to-date. In-repo workflow edits cannot do this. Verification: API read-back JSON in the dossier + a negative test (failing required context ⇒ unmergeable). Wave W4 (prepare) / W5 (owner applies). **Blocking for promotion.**

**M-15 · S2 · The `governance` job writes to `main`.** Evidence: `contents: write`; badge-sync step pushes `HEAD:main` on main-push events (both B and C found it independently). Root cause: badge sync predates protection design. Consequence: the sole required check writes to the release branch; after M-14 it also starts failing (no bypass). Correction: move badge sync to a separate narrowly-scoped workflow or a promotion-PR step; the required check becomes read-only. Verification: `governance` runs with `contents: read`; badges still update. Wave W4 (must precede W5). **Blocking before W5.**

**M-16 · S1 · CI hides failure domains; no browser acceptance anywhere.** Evidence: backend job order `…Format check → Test` (a format failure aborts the 2,329-test suite — nobody knows if it passes on the pushed SHA); frontend job `Lint → Type → Unit → Mutation → Build` serial; `qa-contract-stack`'s only container step is `docker compose config --quiet` — a syntax check that starts nothing; no Playwright invocation anywhere in CI. Root cause: one job per technology instead of one per failure domain; compose-render adopted as a proxy for journey health. Consequence: each red run yields one datum instead of six; zero automated evidence any user journey works while the Full UI Acceptance Contract demands exactly that. Correction: §D job split; rename `qa-contract-stack` → `qa-contract-render` (honest naming); add a real `qa-browser` job (loopback-only compose UI profile + registered Playwright journeys); simulation failure drill proves a red format cannot mask a green suite. Verification: deliberate format error ⇒ red `backend-format` **and** green `backend-test` in one run; journeys emit dated verdicts + screenshot/HAR artifacts. Wave W4 (CI) / W6 (journeys). **Blocking.**

**M-17 · S2 · Research corpus enters the candidate — spine scan must follow the commit.** Evidence: ~71 untracked files under `tests/document_corpus/rich/**` (synthetic fixtures + generator); the audit's `RAW_SOURCE_FORBIDDEN` markers (which reject pre-digested "Evidence unit candidate"/"Coding hints:" content) scan **tracked files only**, so they say nothing about the corpus until it is committed. Root cause: large new corpus landed untracked; scan surface lags the tree. Consequence: a corpus shape that could carry pre-digested evidence ( conclusions inside "sources") is exactly the spine risk; unverified inclusion would be silent. Correction: classify C2 only after verifying generator-authored synthetic content staying under `tests/`; commit; then re-run the public-quality audit and the spine contract tests so the corpus enters the scan surface. Verification: generator reproducible; `RAW_SOURCE_FORBIDDEN` scan green post-commit; corpus never referenced by product code. Wave W0 (verify+commit) / W2 (scan) / W6 (spine journeys). **Blocking (inclusion).**

**M-18 · S2 · Security evidence predates the candidate.** Evidence: `security/control_matrix.json` +6 / `SECURITY_BENCHMARK.md` +1 in the working tree (audit.py, metrics.py added to two control scopes; audit_middleware.py; VersionHistory.tsx). Root cause: control scopes widened without (yet) a rerun on the final SHA. Consequence: the known 28/28 result cannot be extrapolated to the candidate. Correction: rerun `python scripts/security_benchmark.py --fail-on-threshold` on the Promotion SHA; confirm `tests/test_security_benchmark.py` covers the added paths; confirm the newly scoped routes genuinely implement the claimed controls (listed ≠ implemented). Verification: 28/28 (or grown denominator) scorecard bound to the Promotion SHA in the dossier. Wave W2 (verify) / W7 (rerun). **Blocking.**

**M-19 · S3 · Verification folklore; plan-of-record gitignored.** Evidence: wave-manifest hash only matches canonical compact sorted JSON (undocumented); `.compass-forge/` is gitignored so the release's plan of record never rides the candidate; snapshot `candidate_id`s likewise undocumented (K8). Root cause: conductor-internal hashing conventions not documented. Consequence: every honest verifier computes a mismatch and suspects tampering; the frozen SHA cannot be audited against its plan. Correction: document the canonicalisation; ship `scripts/verify_wave_manifest.py`; export the approved master plan + manifest to a tracked `docs/build-stream/` path at freeze; pin the hash in the lifecycle status block. Verification: verify script exit 0; tracked export present at the frozen SHA. Wave W0/W1. **Blocking (the tracked export); script S3.**

**M-20 · S2 · Desktop release status undefined.** Evidence: `cargo check` is `continue-on-error` ("system libs"); green in the observed run without proving compile. Root cause: runner lacks Tauri deps; no decision recorded. Consequence: desktop regressions reach main invisibly; status misleading. Correction (owner decision, default = try (a)): (a) install system deps in CI and make the job blocking; or (b) keep advisory but emit a distinct, explicitly non-gating context documented in `TESTING.md` + the dossier. Verification: the dossier states the decision; context name makes it obvious. Wave W4 (prepare) / owner decides. **Decision required before promotion.**

**M-21 · S3 · Required-check rot.** Evidence: only `governance` required while 13 jobs exist; nothing ties workflow job ids to protection. Root cause: no contract between workflow graph and settings. Consequence: context renames silently orphan required checks. Correction: committed required-checks manifest + `scripts/check_required_checks.py` (or extension of `check_ci_governance.py`) that parses `ci.yml`, compares against the manifest, and fails on `continue-on-error` inside any required job; the manifest is what W5's owner change consumes. Verification: checker green; manifest committed; simulated rename fails the checker. Wave W4. **Blocking before W5.**

**M-22 · S3 · Contract-doc drift.** Evidence: `docs/architecture/research-validity-contract.md:3` cites "CF-SPEC-124 / CF-1590" — no such objects exist (max task id 413). Correction: correct the header reference in W1's doc pass; content otherwise untouched. Verification: grep shows valid references. Wave W1. **Non-blocking.**

**M-23 · S2 · Context-rename ordering hazard.** Evidence: job renames (M-16) invalidate existing required contexts; `main` currently requires `governance`. Root cause: protection and workflow evolve separately. Consequence: the most dangerous step in the plan — `main` can briefly require a context that no longer exists (unmergeable) or lose its only required check. Correction: sequence W4→W5 as one owner-coordinated action: apply the protection change in the same operation as (or immediately after) the rename lands, with `governance` retained as a context name throughout; verify read-back immediately. Verification: read-back after rename shows the full new set with no gap. Wave W4/W5. **Blocking.**

**M-24 · S3 · Merge mechanics undecided.** Evidence: `main` tip 2026-05-27; a 994-commit, ~1,400-file fast-forward pending; `main`'s historic green runs prove nothing about this candidate (its workflow predates the current architecture). Correction: dossier recommends `--no-ff` merge commit for an auditable promotion point; owner chooses FF vs merge; post-merge `main` CI run required. Wave W7. **Owner decision.**

**M-25 · S4 · Blind-review convergence.** Evidence: process requirement (objective 12). Correction: W7 runs independent blind architectural/code/security review; findings become remediation tasks with delta re-reviews until dry; verdicts recorded as CF `review_verdict` evidence. Wave W7. **Blocking process gate.**

Register summary: 10 × S1 · 8 × S2 · 5 × S3 · 2 × S4. Promotion is blocked until every S1 is closed and every S2 is closed or owner-accepted with rationale.

---

## C. Strict-wave manifest (8 waves; conductor's 6 IDs preserved)

Mapping: W0→`candidate-boundary` · W1→`control-plane-lifecycle` · W2+W3→`correctness-quality` · W4+W5→`ci-enforcement` · W6→`browser-spine-acceptance` · W7→`promotion-certification`. Waves are strictly sequential; each begins with a CF before-gate/work order and ends with command evidence, independent review, after-gate, ledger entry, and commit. Owner pauses: before W0 (this plan + manifest ratification), before W5 (settings), before any live lane, before W7's push/PR.

### W0 — Freeze the candidate boundary (`candidate-boundary`)

- **Objective:** one Candidate Base SHA containing exactly the classified work, with zero loss and zero accidental inclusion.
- **Scope:** §A.3 steps 1–6 (recovery point, inventory, classification manifest, hunk-splits where needed, pathspec commits, local tag); pre-commit hooks (audit `--check`, `git diff --check`); resolution of the 17 untracked lifecycle files; tracked export of the approved plan + wave manifest (M-19); `.stryker-tmp` eslint ignore (M-09 half).
- **Inputs:** §A.1 measured state; lifecycle ledgers; CF task list; owner's plan approval.
- **Explicit exclusions:** no source repair (W2/W3), no CI edits (W4), no CF task closure (W1), no push, no deletions, no touching C4/C5 paths, no protected-folder enumeration.
- **Tasks:** recovery bundle+tarball+snapshot → restore-verify → classification manifest with per-path evidence citations → dependency-closure proof for untracked C1 files → M-17 corpus verification → owner spot-check of the C6/quarantine bucket (folded into implementation approval; unresolved ⇒ quarantine) → pathspec commits → Candidate Base SHA + local tag → hooks installed → audit re-run post-commit (M-08 scan-surface rule).
- **Dependencies:** owner approval of this plan; repo completion lock.
- **Verification:** `git bundle verify`; tarball restore into scratch; `git status --porcelain -uall` shows only C4/C5/C6 remainder, each in the manifest; stash list unchanged; `git check-ignore LLMs Model_Finetuning` (untouched, byte-identical listing); `git rev-parse` recorded; classification row count == measured path count; audit green **after** the commits.
- **CF gates/evidence:** architecture_drift + test_ownership before/after; command rows for snapshot/classification/commit with manifest hash; start/end SHAs.
- **Review questions:** every included path cited? every excluded path still recoverable? `git add -A` used anywhere? protected dirs untouched? does the audit's grown scan surface still pass?
- **Completion:** one commit-set fully explained by the manifest; Candidate Base SHA recorded everywhere; restore drill passed.
- **Rollback:** §A.5 (revert commits; restore from bundle+tarball).
- **Residual risks:** classification is judgement; a large UNDECIDED bucket stalls on the owner (by design).

### W1 — Reconcile control-plane and lifecycle truth (`control-plane-lifecycle`)

- **Objective:** Git, Build Stream, CF, and conductor state tell one true, provable story; hidden blockers surfaced.
- **Scope:** native CF state backup; deliberate `refresh-project` + freshness assertion (M-13 — no schema-21 chase); record the command migration + `not_yet_native` debt; M-12 triage of all 181 open tasks with citations; dispositions for CF-SPEC-19/25/28/29; drive CF-SPEC-30 toward acceptance readiness; M-11 lifecycle status reconciliation (append-only); M-22 doc-drift fix; `intelligence impact --path` per changed architectural surface + manual dependency follow-up.
- **Explicit exclusions:** no bulk closure without cited evidence; no retroactive ledger edits; no code repair; no invented impact output.
- **Dependencies:** W0.
- **Verification:** `index status` fresh, `warnings: []`, `created_at` newer than W0 commits; `task list` shows zero release-blocking open tasks with a triage table; every closure cites evidence; STATUS BLOCKs parse and match last ledgers; `compass-forge next` points at this stream truthfully; `python scripts/check_integrity.py` green.
- **CF gates/evidence:** command rows per refresh/impact/triage; triage table attached as evidence.
- **Review questions:** was any task closed without evidence? does any lifecycle file still dispatch implementation while blocked? was graph output trusted beyond its `confidence`/`graph_source`? do dynamic routes need textual follow-up?
- **Completion:** "no open release-blocking CF tasks" provable from evidence alone; ledgers truthful and tracked.
- **Rollback:** restore native CF backup; lifecycle corrections stay (append-only); revert only doc commits.
- **Residual risks:** a genuinely unfinished obligation surfaces → becomes a new blocking task, never cosmetic closure.

### W2 — Mechanical correctness repair (`correctness-quality`, part 1)

- **Objective:** every known deterministic red check green at root cause; thresholds untouched.
- **Scope:** M-04 (format + exact ruff pin), M-05 (F821 `TYPE_CHECKING` + correctness-lint promotion), M-08 (machine-path text fix), M-09 (type alias; ignore fix completed), M-10 (whitespace), M-18 (security verification pass), full-suite unmasking run.
- **Explicit exclusions:** no CI restructuring (W4); no threshold lowering; no `continue-on-error` added; no unrelated warning sweep; no live execution.
- **Dependencies:** W0, W1.
- **Verification (exact commands, each a CF command row with SHA):**
  - `cd backend && ruff format --check .` → exit 0
  - `ruff check backend/ --select F821,F811,F822,E999` → 0; `get_type_hints` probe returns for both functions
  - `pytest tests/ -m "not live_llm"` → 0 failed (first run able to see past the format gate)
  - `pytest tests/test_public_repo_quality.py -q` → green
  - `git diff --check origin/main` → 0
  - frontend `npm run lint && npx tsc --noEmit && npm run test:unit` → green (89/89 baseline preserved or grown)
  - six governance check scripts + `python scripts/security_benchmark.py --fail-on-threshold` → green
- **CF gates/evidence:** one command row per line; blind review queued at W7.
- **Review questions:** was any fix a suppression? does the ruff pin equal CI's resolution? did the full suite pass now that format no longer masks it?
- **Completion:** all blocking commands exit 0 on one commit; before/after counts in the ledger.
- **Rollback:** per-fix revertible commits.
- **Residual risks:** the full backend suite may reveal failures hidden behind the format gate — the wave most likely to expand; if it does, fixes stay in W2 scope (deterministic reds) and new feature-scope defects become new tasks.

### W3 — Mutation quality and harness repair (`correctness-quality`, part 2)

- **Objective:** frontend mutation ≥ 75 (target ≥ 90) with honest coverage; backend mutation stays green; local harness reproducible.
- **Scope:** M-06 (kill 21 survivors, cover 14 no-coverage; implementation fixes where mutants expose real bugs), M-07 (`npm ci` reinstall — owner-visible note; node 24 pin).
- **Explicit exclusions:** thresholds {90/80/75} unchanged; no mutation-scope change without a recorded decision; no tautological tests; no test weakening.
- **Dependencies:** W2.
- **Verification:** `npm run test:mutation` → score ≥ 75, no-coverage = 0 in scope, survivors enumerated to zero or justified; score arithmetic re-derived from the raw report; `npm run test:unit` green; `python scripts/run_backend_mutation.py` green; mutation report artifact retained; summary into `testing/TEST_HISTORY.md`.
- **CF gates/evidence:** command rows; reviewer verifies score arithmetic from the report, not the summary line.
- **Review questions:** do new tests assert behavior (not implementation coupling)? are no-coverage mutants covered or explicitly scoped? did any "fix" weaken a check?
- **Completion:** threshold met without touching thresholds; harness reproducible locally.
- **Rollback:** revert test commits; thresholds never moved.
- **Residual risks:** survivors may reveal real bugs in `runtimeConfig.ts` (auth-adjacent URL derivation) → fixes enter W3 with their own tests.

### W4 — CI target architecture, in-repo (`ci-enforcement`, part 1)

- **Objective:** workflow graph matches §D; independent failure domains; honest names; self-enforcing required-check contract; protection change prepared.
- **Scope:** M-16 job split + `qa-contract-render` rename + `qa-browser` job definition (executed W6); M-21 required-checks manifest + checker; M-05 correctness-lint gate in CI; M-15 badge-sync fix; M-10 hygiene step; M-20 desktop decision prepared; M-14 protection request body drafted (unapplied); M-23 sequencing plan; `TESTING.md` + `testing/TEST_HISTORY.md` topology updates.
- **Explicit exclusions:** no GitHub settings mutation (W5); no gate weakening; no new `continue-on-error` on a required job; no live-credential lanes.
- **Dependencies:** W2, W3.
- **Verification:** extended `check_workflow_contracts.py` + new required-checks checker green; `actionlint` where available; failure drill on a throwaway branch (red format must NOT mask green suite); a candidate push shows the new graph with all required contexts emitted; protection body reviewed and attached, unapplied.
- **CF gates/evidence:** command rows; protection body artifact; contract-check rows.
- **Review questions:** can any correctness class still escape (re-ask M-05 of the new design)? could a required context pass while its domain is broken? does any required job carry `continue-on-error`/`if: always()` shortcuts? does the manifest match post-rename job ids exactly?
- **Completion:** a push yields a complete independent failure picture; protection change queued with the sequencing plan.
- **Rollback:** revert the workflow commit; old contexts retained until replacements exist.
- **Residual risks:** M-23 ordering hazard — mitigated by sequencing with the owner (W5 in the same operation).

### W5 — Owner-gated branch-protection alignment (`ci-enforcement`, part 2)

- **Objective:** repository settings enforce the architecture (M-14). Not automatable in-repo; the wave delivers the exact checklist and verifies after the owner applies it.
- **Scope:** owner applies the §D.3 context set (from the W4 manifest) on `main` and `testing`; ≥1 approving review; code-owner review; dismiss-stale; enforce admins; disallow force pushes; require linear history; keep strict up-to-date; M-15 must already be fixed or the new rules fail the badge workflow.
- **Explicit exclusions:** agents do not mutate settings; no merge; no PR creation.
- **Dependencies:** W4 (contexts observed on GitHub); owner action.
- **Verification:** API read-back exactly matches the checklist (JSON in dossier); negative test — a controlled failing check renders the PR unmergeable.
- **CF gates/evidence:** read-back JSON; negative-test evidence.
- **Review questions:** is any release-critical job absent from required? can admins or force-pushes bypass? do stale contexts linger?
- **Completion:** settings match the manifest; dossier snapshot recorded.
- **Rollback:** owner reverts settings from the captured prior snapshot; promotion stays blocked until policy is restored.
- **Residual risks:** enforcing admins may block the owner's own emergency pushes — explicit owner ack.

### W6 — Container-first browser + spine acceptance (`browser-spine-acceptance`)

- **Objective:** prove changed behavior as users experience it, and prove the Research Spine non-bypassable.
- **Scope:** loopback-only `docker-compose.qa.yml --profile ui` stack; real Playwright journeys (navigate/click/fill/upload/send) for every changed UI surface (chat model controls/settings, metrics/quality views, auth-token paths touched by `tokenStore`); roles admin/researcher/viewer/stranger where auth-adjacent; light/dark; 375px reflow; keyboard Tab + visible focus; loading/error/empty states; synthetic data only; Research-Spine probes (§F) for touched research paths incl. the corpus fixtures; donor/model-management and team/persona probes where the candidate touched them; dated verdicts + deterministic screenshot/HAR/console/network paths; scenario-registry + coverage-matrix + `TESTING.md` + `testing/TEST_HISTORY.md` updates.
- **Explicit exclusions:** no live model/provider execution; no golden-data mutation; no API-only step presented as a journey; no silent skips.
- **Dependencies:** W3, W4.
- **Verification:** every journey has a dated verdict and artifacts under deterministic paths; every unavailable live lane returns an explicit `not_runnable` naming the missing capability (never counted as a pass, never omitted); registry/coverage maps updated; spine probes green.
- **CF gates/evidence:** command rows per journey batch; artifact paths recorded.
- **Review questions:** did each claim arise from browser acts? is any step an API call in disguise? is any `not_runnable` concealing a real failure? was publication loopback-only? were golden data or protected folders touched?
- **Completion:** coverage map complete or honestly `not_runnable`; no silent skips.
- **Rollback:** test-only wave; revert additions; journey failures loop to W2/W3 as defects.
- **Residual risks:** journey authoring is the largest unknown effort and the most likely wave to discover real product bugs.

### W7 — Promotion certification (`promotion-certification`)

- **Objective:** freeze one Promotion SHA; re-prove every release claim on it; blind review until dry; dossier complete; owner approval pending.
- **Scope:** freeze Promotion SHA; full §E matrix re-run on it (pre-freeze results are diagnostics, never certification); owner-gated push of the Promotion SHA to `origin/testing` (fast-forward only) + verify CI `headSha` == dossier SHA; M-25 blind independent review (architecture/code/security), remediation tasks + delta re-reviews until no open Blocker/Major; M-12/M-11 final CF/lifecycle reconciliation check; M-18 security rerun; M-24 merge-mechanics recommendation; `docs/promotion/2026-09-09-promotion-dossier.md`.
- **Explicit exclusions:** no merge; no PR without separate owner authorization; no source change without invalidating the freeze (re-freeze ⇒ new dossier); no threshold changes.
- **Dependencies:** W0–W6 + W5 read-back.
- **Verification:** every §E row green on the Promotion SHA; `git rev-parse testing == CANDIDATE_SHA` at dossier close; artifact download/checksum inspection; verdict evidence rows present.
- **CF gates/evidence:** full evidence set on the final SHA; `review_verdict` rows; architecture_drift + test_ownership after-gates.
- **Review questions:** can a reviewer reproduce results without implementer claims? is every artifact built from this SHA? does any unverified claim appear confirmed? did anything move after freeze?
- **Completion:** §H verdict READY (owner approval pending) or NOT READY (criterion named).
- **Rollback:** abandon the SHA; record invalidation; reopen the earliest affected wave; `main` untouched.
- **Residual risks:** any post-freeze commit forces full re-verification at a new SHA.

---

## D. CI target architecture

### D.1 Job graph (independent failure domains; only true prerequisites gate)

```
classify/feature-obligations ─── fail-closed path/obligation matrix (PR-scoped, as today)
hygiene ──────────────────────── public-quality audit --check + git diff --check        fast, blocking
governance ───────────────────── integrity, ci-governance, test-harness, qa-capabilities, security benchmark
                                  [contents: read only — badge sync removed, M-15]
backend-format ───────────────── ruff format --check (pinned ruff)                      blocking
backend-lint ─────────────────── changed-file strict + repo-wide F821,F811,F822,E999    blocking
backend-tests ────────────────── FULL pytest (-m "not live_llm") + rehearsal            blocking
backend-mutation ─────────────── run_backend_mutation.py                                blocking
frontend-lint ─┐
frontend-typecheck ┤
frontend-unit ─┤                 eslint / tsc / vitest — parallel, independent
frontend-mutation ────────────── stryker (break 75 unchanged; triple reported)
frontend-build ───────────────── next build
test-harness-js ──────────────── relay + simulation static + RUB static/contracts
qa-contract-render ───────────── compose config render + contract/synthetic/audit pytest  (renamed honestly, M-16)
qa-browser ───────────────────── needs: qa-contract-render — compose ui profile, loopback-only, Playwright journeys
desktop-check ────────────────── cargo check — blocking or explicitly non-gating (M-20)
```

No quality gate gates a sibling quality gate; the only `needs:` edge is `qa-browser → qa-contract-render` (a stack that does not render cannot start a journey). A required context that never reports blocks merge — the graph fails closed by construction.

### D.2 Rejected alternative: single `release-gate` aggregator

Considered (A) and rejected: granular required contexts already fail closed (missing context = blocked merge); an aggregator adds a second source of truth that itself requires CODEOWNERS protection and rewrite risk. A's valid concerns survive as checker rules: no `continue-on-error` on required jobs; no skipped/cancelled context treated as green (GitHub blocks merge on a never-reported required context).

### D.3 Required checks (manifest-committed; M-21)

`hygiene, governance, feature-obligations, backend-format, backend-lint, backend-tests, backend-mutation, frontend-lint, frontend-typecheck, frontend-unit, frontend-mutation, frontend-build, test-harness-js, qa-contract-render, qa-browser, desktop-check` (or its explicitly non-gating variant per M-20). Enforced on `main` and `testing` PRs/pushes; consumed verbatim by W5's owner settings change; verified by read-back.

### D.4 Events, scoping, caches, artifacts

- **PR** (rare, release-sized here): full graph incl. `qa-browser` + change-obligation checks.
- **Push to `testing`/`main`:** full graph — `testing` is the promotion source and never carries an unproven SHA.
- **Scheduled (weekly):** full matrix on both branches to catch rot (runner/dependency drift); required checks must not depend on push-only paths.
- **Change-scoping:** allowed for cost only where fail-closed classification exists (`qa-browser` scenario selection on ordinary PRs to `testing` via registry tags); never for a correctness class; the final frozen SHA always runs the full matrix.
- **Caches:** keyed by OS/runtime/lockfile/tool-config hash; never across trust boundaries; never cache workspaces or results.
- **Artifacts:** security scorecard, mutation reports (HTML/JSON with the triple), journey verdicts + screenshots/HAR/console/network, feature-obligation report, promotion dossier bundle — all named with the SHA; promotion evidence retained ≥ 90 days; key summaries also copied into `docs/promotion/` so evidence survives artifact expiry.

### D.5 Policies

- **Mutation:** thresholds {high 90, low 80, break 75} never lowered; score improves via tests or implementation fixes; scope grows only by explicit reviewed decision (advisory-first); killed/survived/no-coverage triple always reported — the composite number alone hid M-06's shape.
- **Format/lint:** ruff pinned exactly (== CI resolution); `ruff format --check` blocking in its own job; changed-file strict lint blocking; correctness subset (`F821,F811,F822,E999`) repo-wide blocking; style backlog advisory with documented burn-down; `git diff --check` blocking, docs-scoped.
- **Credential-free vs live:** the credential-free lane is the default and gates the release. Live lanes (live-LLM evals, donor compute) are manual, owner-authorized, bounded to one configured target, never run on PR, excluded from required checks, and report `not_runnable` with the named missing capability — never a silent skip, never a fabricated pass.
- **Containers/Playwright:** loopback-only publication; isolated synthetic project/volumes; deterministic teardown; evidence paths deterministic and SHA-keyed.
- **Desktop:** M-20 decision recorded; whichever branch is chosen, `TESTING.md` + dossier state it and the context name is self-explanatory.
- **Stale-green prevention:** required-checks manifest checked by CI itself (a rename without a manifest update fails the contract check); no `continue-on-error` on required jobs (checker-enforced); weekly scheduled runs keep checks exercised; `concurrency` keeps only the latest run per ref; M-15 removes the one job that writes to `main`; every dossier claim binds to one SHA.

### D.6 External repository settings (not code)

Branch protection, required contexts, review policy, admin enforcement, and force-push rules are **GitHub settings changed only by the owner in W5** (M-14/M-23). Updating `.github/workflows/ci.yml` cannot do it; the plan keeps the two strictly separated and sequenced.

---

## E. Verification matrix

Legend: **B** = blocking · **CFr** = credential-free · **R** = must be re-run on the final Promotion SHA. "CF" = Compass Forge command-evidence rows; "dossier" = `docs/promotion/2026-09-09-promotion-dossier.md`.

| # | Surface / claim | Command / journey | Environment | Expected | Evidence | B | CFr | R |
|---|---|---|---|---|---|---|---|---|
| 1 | Candidate boundary | manifest vs `git status --porcelain -uall` | local | only C4/C5/C6 remain, all in manifest | CF + dossier | ✓ | ✓ | ✓ |
| 2 | Recovery drill | restore bundle + tarball into scratch | local | tree reconstructs | CF | ✓ | ✓ | – |
| 3 | Protected dirs | ignore-status + untouched listing of `LLMs/`, `Model_Finetuning/` | local | unchanged | CF | ✓ | ✓ | ✓ |
| 4 | Backend format | `ruff format --check .` (pinned ruff) | CI + local | exit 0 | `backend-format` | ✓ | ✓ | ✓ |
| 5 | Correctness lint | `ruff check backend/ --select F821,F811,F822,E999` | CI | 0 | `backend-lint` | ✓ | ✓ | ✓ |
| 6 | F821 defects gone | `get_type_hints` probe on both functions | CI | returns dict | CF | ✓ | ✓ | ✓ |
| 7 | Backend suite | `pytest tests/ -m "not live_llm"` | CI | 0 failed | `backend-tests` | ✓ | ✓ | ✓ |
| 8 | Backend mutation | `python scripts/run_backend_mutation.py` | CI | green | `backend-mutation` | ✓ | ✓ | ✓ |
| 9 | Public quality | `pytest tests/test_public_repo_quality.py -q` (post-commit scan) | CI | green; `audit() == []` | `hygiene` | ✓ | ✓ | ✓ |
| 10 | Whitespace | `git diff --check origin/main` | CI | 0 | `hygiene` | ✓ | ✓ | ✓ |
| 11 | Frontend lint | `npm run lint` | CI node 24 | exit 0 | `frontend-lint` | ✓ | ✓ | ✓ |
| 12 | Typecheck | `npx tsc --noEmit` | CI node 24 | clean | `frontend-typecheck` | ✓ | ✓ | ✓ |
| 13 | Frontend unit | `npm run test:unit` | CI node 24 | ≥ 89/89 baseline | `frontend-unit` | ✓ | ✓ | ✓ |
| 14 | Frontend mutation | `npm run test:mutation` | CI node 24 | ≥ 75 (target ≥ 90); triple reported; no-coverage 0 in scope | `frontend-mutation` + report | ✓ | ✓ | ✓ |
| 15 | Frontend build | `npm run build` | CI node 24 | succeeds | `frontend-build` | ✓ | ✓ | ✓ |
| 16 | Governance battery | integrity / ci-governance / test-harness / workflow-contracts / qa-capabilities / required-checks checker | CI | all exit 0 | `governance` | ✓ | ✓ | ✓ |
| 17 | Security benchmark | `python scripts/security_benchmark.py --fail-on-threshold` | CI | 28/28 (or grown), matrix/docs/tests current | scorecard | ✓ | ✓ | ✓ |
| 18 | Compose render | `docker compose … config --quiet` × profiles | CI | renders | `qa-contract-render` | ✓ | ✓ | ✓ |
| 19 | Real browser journeys | registered Playwright scenarios on the QA stack | Docker, loopback | dated verdicts; matrix cells covered or `not_runnable` | `qa-browser` + artifacts | ✓ | ✓* | ✓ |
| 20 | Research Spine non-bypass | spine contract tests + §F probes + audit-profile QA | CI/Docker | no bypass; provisionality + gates intact | CF | ✓ | ✓ | ✓ |
| 21 | Self-improvement governance | improvement-governance + agent-learning-scope tests | CI | pass | `backend-tests` | ✓ | ✓ | ✓ |
| 22 | Simulation/RUB static | `test:static` / `check` | CI | 111 syntax/17 checks; 107/107 | `test-harness-js` | ✓ | ✓ | ✓ |
| 23 | CF truth | `task list` / `next` / spec shows / triage table | native binary, repo root | zero release-blocking open; SC-002 satisfiable | CF + dossier | ✓ | ✓ | ✓ |
| 24 | Lifecycle truth | STATUS BLOCK parse vs ledgers; Sep 6–9 files tracked | local | no contradictions | dossier | ✓ | ✓ | ✓ |
| 25 | Plan-of-record | `scripts/verify_wave_manifest.py`; tracked export present | local | hash verifies | CF | ✓ | ✓ | ✓ |
| 26 | Branch protection | `gh api …/branches/main/protection` | GitHub API | matches §D.3 checklist | dossier JSON | ✓ | – | ✓ (snapshot) |
| 27 | CI bound to SHA | `gh run list --commit <SHA>`; `headSha` == dossier SHA | GitHub | all required contexts green on the exact SHA | dossier | ✓ | – | ✓ |
| 28 | Blind review dry | reviewer verdicts + delta re-reviews | reviewer env | pass; no open Blocker/Major | `review_verdict` | ✓ | ✓ | ✓ |
| 29 | Production rehearsal | `scripts/production_rehearsal.py` | CI | pass | `backend-tests` | ✓ | ✓ | ✓ |
| 30 | SHA currency | `git rev-parse testing` == `CANDIDATE_SHA` | local | equal | dossier | ✓ | ✓ | ✓ |

\* Row 19 requires Docker (credential-free but not host-free). Non-blocking, explicitly-not-gates (recorded honestly as `not_runnable` when absent): live-LLM evals, donor-compute probes, VPS deployment, performance soak.

---

## F. Research Spine assurance

Spine (unchanged, non-negotiable): Sources → Evidence Units → Independent Multi-Model Atomic Extraction + Open Coding → Reliability + Grounding → Reconciliation → Accepted Atoms/Nuggets → Facts → Insights → Recommendations → In Review → Human-Approved Done → Reports.

**Changed research-data paths in this candidate:**
1. `tests/document_corpus/rich/**` (~71 untracked files + generator) — **the spine-relevant risk.** A large corpus entering the repo is exactly the shape that can smuggle pre-digested evidence (conclusions inside "sources"). The audit's `RAW_SOURCE_FORBIDDEN` markers reject such content but scan **tracked files only** — so the corpus is unscanned until committed (M-17). Disposition: verify generator-authored synthetic content confined to `tests/`; classify C2; commit in W0; re-run the audit and spine contract tests post-commit; never reference from product code.
2. Working-tree modifications to research-validity/self-improvement contract tests and the security control matrix — these *strengthen* the spine; verified at W2, re-proven at W7.
3. Backend `app/` diff hotspots (chat model controls, metrics views, Pi model management, endpoint policy) — no new research-data ingestion/reporting path found by two architects' inspection; W6/W7 reviewers must re-confirm on the frozen diff.

**Trace obligation (A's table, adopted):** for each changed research path, record — ingress source; evidence-unit constructor and exact raw-span handle; independent coder identities (distinct served models; requested ≠ served; replicas ≠ independent raters); reliability + grounding computed (not defaulted) and preceding reconciliation; durable project-scoped reconciliation decisions; provisional-until-accepted visibility; raw spans (not nugget prose) as the evidence basis unless exact spans are preserved and the artifact stays provisional; route evidence surviving bridge/frames/dispatcher/persistence; In-Review → human-approved Done; report queries reading only accepted evidence attached to Done tasks.

**Self-improvement boundary (all three drafts, merged):** telemetry/ReasoningBank are process signals, never report evidence; Memento learns strong positive signals only from verified/quality/reportable outcomes; autoresearch stays sandbox/proposal-only; Meta-Hyperagent/Self-Evolution stay project-scoped and governed; RAG/GraphRAG/Prompt-RAG preserve provenance and protected methodology blocks; LLMLingua compresses only with protected protocol/codebook/gate/schema blocks intact; none may weaken authorization or report gates. Executable gates: the improvement-governance and agent-learning-scope test suites (matrix rows 20–21); written contracts re-read against the actual diff, not assumed current.

**Disposition:** any bypass reachable by a research-data path in this candidate is architecture debt and **blocks promotion** unless repaired in-scope; unreachable bypasses are recorded with a named follow-up spec. The system is never described as aligned while any path is red.

---

## G. Owner-gated operations (no wave may perform these)

1. `git reset --hard`, `git clean`, `git checkout -- .`, `stash drop`, history rewrite, force-push — destroys unclassified work irreversibly.
2. Deleting/moving/pruning/inspecting `LLMs/`, `Model_Finetuning/`, or any ignored local artifact (C4/C5).
3. Deleting or pruning any untracked file (119 exist; classification is judgement-based).
4. Starting servers, sending chat-completion probes, loading models, exercising a live provider (passive discovery only).
5. Reading, printing, or persisting secrets, endpoints, fingerprints, tokens, connection strings.
6. Mutating GitHub repository settings (branch protection, required checks, CODEOWNERS, Actions secrets) — W4 prepares, W5's owner applies.
7. Pushing branches/tags, creating the promotion PR, merging to `main` — push/PR only in W7 if separately authorized; merge is always the owner's act.
8. Lowering any mutation/security/quality/accessibility/Research-Spine threshold, or accepting a Blocker/Major risk — explicit owner decision only, none requested by this plan.
9. Rewriting an existing ledger entry (append-only) or closing a CF task without cited evidence.

**Pause points:** (1) approval of this plan + ratification of the classification manifest before W0; (2) before W5 settings application (with the M-23 sequencing note); (3) before any live-capability lane; (4) before W7 push/PR; (5) the final merge decision after the dossier.

---

## H. Final release criteria — one binary verdict

**`NOT READY`** is the default whenever any condition below is absent, stale, contradictory, attached to a different SHA, or skipped without an allowed `not_runnable` disposition. **`READY — OWNER APPROVAL PENDING`** requires **all** of:

1. One exact Promotion SHA recorded in the dossier, lifecycle status block, and CF evidence; `git log <Candidate-Base>..<Promotion-SHA>` fully explains everything added after the freeze; worktree clean for candidate scope.
2. Every intended recent Build Stream initiative has exactly one recorded disposition (included / excluded / superseded / completed / deferred, with rationale); no lifecycle file is both "done" and "in-progress"; every referenced lifecycle file is tracked at the frozen SHA.
3. No loss or accidental inclusion of ambient work: manifest ratified; quarantine branch exists; recovery snapshot verified; protected folders untouched.
4. Compass Forge reconciled: index fresh, `intelligence impact` recorded per changed surface, zero open release-blocking tasks (proven by the M-12 triage), CF-SPEC-29/30 dispositions evidenced, `next` truthful.
5. Rows 1–25, 28–30 of §E green **on the Promotion SHA**; row 27 green on the pushed same SHA (CI `headSha` binding).
6. Frontend mutation ≥ 75 (target ≥ 90) with zero unexplained no-coverage mutants; thresholds untouched since `9961fa3d`.
7. Container-first UI verdicts dated on the Promotion SHA; the full role/theme/reflow/keyboard/state matrix covered or honestly `not_runnable`.
8. Security benchmark green and current on the frozen SHA; control-matrix/benchmark-doc/test updates committed for any changed trigger.
9. Blind independent architectural/code/security review passed; findings remediated and delta re-reviewed until dry (`review_verdict` evidence).
10. Branch protection on `main` and `testing` matches the §D.3 manifest (API-verified snapshot in the dossier); no stale or advisory required context.
11. Promotion dossier complete: candidate story, findings register with dispositions, §E results, CF evidence ids, journey verdicts, security scorecard, mutation report, protection snapshot, merge-mechanics recommendation (M-24).
12. Owner approval still pending — the verdict enables the decision; it never executes it. No merge, no deployment, no live-verified claim.

### Stage separation (transported → live)

| Stage | Proof object after this plan |
|---|---|
| transported | working tree before W0 commits · classification manifest |
| committed | Candidate Base SHA → Promotion SHA (local git log + local tag) |
| pushed | `origin/testing` @ Promotion SHA (W7, owner-gated, fast-forward only) |
| CI-validated | the green required-context run with `headSha` == Promotion SHA |
| artifact-built | frontend build + QA containers + SBOM/manifests from that SHA |
| PR-ready | dossier complete + branch protection aligned |
| merged | **not part of this plan** — the owner's act after READY |
| deployed / live-verified | out of scope — separate owner-gated operation |

### Explicitly not evidence of readiness

A green process, container, workflow, or artifact; a green run on an ancestor SHA; `main`'s historic green runs; a local result from an unpinned node 26 environment; a compose file that renders; a mutation summary line without its triple.

---

## I. Rejected shortcuts

- Bulk-committing surface C unclassified (conflates release work with ambient edits). · Promoting A or B (A remotely red; B cannot build). · Chasing a "schema-21 refresh" (unexecutable; M-13). · Reordering format inside the same backend job (insufficient; domains must be independent). · Keeping only `governance` required (does not represent the architecture). · Lowering the mutation threshold, excluding mutants, converting red checks to advisory, or accepting static compose render as UI proof. · Administrative closure of CF tasks/lifecycles by age or title. · Editing the public-quality audit to obtain green. · A single fail-closed aggregator as the only required context (D.2).

---

## J. Residual risks

1. **W2 may expand** — the full backend suite has never been observed green on this candidate (the format gate masked it); failures may be hiding behind it.
2. **W6 is the largest unknown** — journey authoring effort unestimated; most likely to find real product bugs, looping to W2/W3.
3. **M-23 ordering hazard** — context renames vs required contexts need one owner-coordinated operation.
4. **M-12 triage is manual** — the danger is misfiling a real blocker as administrative; mitigated by evidence-cited closures only.
5. **The worktree is shared and live** — the planning phase itself moved it (K3); between freeze and promotion any outside write forces re-freeze.
6. **Remote CI log contents** were read only through `gh` read-only output of two architects; the mutation figure reconciles exactly with local config (95/130 = 73.08%), corroborating but not re-executing the run.
7. **Merge blast radius** — a 994-commit promotion to a 3.5-month-stale `main`; mitigated by the dossier's merge-mechanics recommendation and a post-merge `main` CI run.

## Handoff to cross-vote

Load-bearing synthesis decisions voters should scrutinize: candidate = C with two-stage freeze (K6); in-place assembly over an isolated worktree (K5); granular required contexts over an aggregator (K7); `intelligence impact --path` over the unexecutable "refresh to schema 21" (K2); the lint-contamination finding that reconciles A's 233 errors with B/C's 1 (K1); audit re-run *after* candidate commits (M-08); corpus include-then-scan (M-17); W4→W5 sequencing (M-23).
