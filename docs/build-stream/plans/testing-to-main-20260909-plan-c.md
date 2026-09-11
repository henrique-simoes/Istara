# Architect C — Draft Plan: Freeze and reconcile the testing release candidate

- **Task:** testing-to-main-20260909-PLAN-C (CF-SPEC-30, slot `c`, phase `draft`)
- **Role:** testing-to-main-20260909-architect-c
- **Author:** zai/glm-5.3-flash-max (effort=max), independent draft — written without reading the other architects' plan files
- **Date:** 2026-09-09
- **Status:** DRAFT for conductor synthesis and cross-vote. No product code, branch state, lifecycle plan, or threshold was touched by this planning run.
- **Verification basis:** every fact in §A.1/§B marked "measured" was reproduced by this architect with read-only, credential-free commands on 2026-09-09. Remote evidence (CI run, branch protection) was read via the GitHub API/CLI in read-only mode. Items that could not be verified are explicitly marked.

---

## 0. Executive summary

`main` is 3.5 months stale; `origin/testing` is 994 commits ahead and 0 behind (promotion is fast-forwardable); local `testing` is 64 commits ahead of `origin/testing`; and the working tree adds 155 modified tracked files (+4,712/−977) and 119 untracked files. **No existing ref is the release candidate.** The decisive discovery of this inspection: the working tree's *tracked, modified* frontend files import **untracked** modules (`tokenStore.ts`, `SeeMoreList.tsx`, `ToolAuditTrailTable.tsx`) that do not exist in any commit — so candidate surface B (local commits only) is internally broken (it cannot typecheck or build), and **surface C (local commits + a classified subset of the working tree) is the only viable candidate**. The plan therefore makes candidate reconciliation a first-class wave with a classification protocol, an owner-visible manifest, and a frozen SHA, before any repair work.

The observed red checks are real and reproduced: backend Ruff formatting (15 files locally, 2 at the remote SHA, with an unpinned `ruff>=0.8.0` creating version drift), the frontend mutation score 73.08 against break-threshold 75 (95/130 killed; 21 survived + 14 no-coverage — all inside the single mutated file `runtimeConfig.ts`), one frontend lint error (`ChatModelControls.tsx:20` empty interface), the public-quality audit (machine-local checkout path leaked into two tracked files), and 295 whitespace/blank-line defects across lifecycle docs. Control-plane debt is equally real: four contradictory lifecycle files, CF-SPEC-29 with 13 open tasks (which per CF-SPEC-30 SC-002 blocks spec acceptance), a stale CF index (schema 12 vs required 21) with `impact`/`graph` still `not_yet_native`, and main branch protection that requires only `governance` (0 reviews, no admin enforcement, force pushes allowed — all confirmed via API).

The plan proposes **8 sequential waves** (W0–W7) mapping onto the conductor's 6-wave manifest: candidate freeze → control-plane truth → correctness repairs → mutation quality → CI redesign → owner-gated protection → container-first browser acceptance → promotion certification. Every wave has scope, dependencies, exact verification commands, gates, review questions, completion criteria, and rollback. The final verdict (§H) is binary and requires the full verification matrix re-run on one exact promotion SHA, a passed blind review, and — still — owner approval. Nothing merges automatically.

---

## A. Candidate definition

### A.1 Measured current state (2026-09-09, this architect's own commands)

| Item | Measured value | How measured |
|---|---|---|
| local `testing` HEAD | `85f64e4d25467b7e95ca4f0fb033f4039adbf59e` | `git rev-parse HEAD` |
| `origin/testing` | `9961fa3dbd2ce03a6e1d8cc3e303478edaf17a79` | `git rev-parse origin/testing` |
| `origin/main` | `fa6a1a391b5a1089690eb8fed5d179ce146ec9e9` | `git rev-parse origin/main` |
| main ↔ origin/testing | 0 behind / **994 ahead**; merge-base = main tip ⇒ fast-forwardable | `git rev-list --left-right --count`; `git merge-base` |
| local ↔ origin/testing | **64 ahead** / 0 behind; 59 of 64 touch `docs/build-stream`; code commits are the pi-ai 0.85.1 lockstep bump (f576d216) and five review-fix commits (657632dc, d01b2364, ceb7344b, 492f081c, f0b34f96) | `git log --oneline origin/testing..HEAD` |
| working tree | 155 modified tracked files, +4,712/−977; **119 untracked files** (`-uall`) | `git status --porcelain -uall`; `git diff --shortstat HEAD` |
| working-tree hotspots | frontend/src (2,106+), backend/app (1,125+), tests/simulation (432+), tests/real_user_benchmark (166+), ~20 root test files, AGENTS.md, qa/Dockerfile, security/{control_matrix.json,SECURITY_BENCHMARK.md} | `git diff --numstat HEAD` |
| untracked of product relevance | `frontend/src/lib/tokenStore.{ts,test.ts}`, `frontend/src/components/common/{SeeMoreList,ToolAuditTrailTable}.tsx`, 10 lifecycle docs (2026-09-06→09-09), `tests/document_corpus/rich/**` (~70 research-corpus fixtures + generator), `docs/architecture/agentic-engine-deep-dive.html` | `git status --porcelain -uall` |
| untracked modules are required | `git grep tokenStore HEAD -- frontend/src` → **empty**; working tree: 8+ tracked files (authStore, LoginScreen, StatusBar, HomeClient, MetricsView, ContextPreview, ProjectSettingsView, ConnectionStringPanel) import `@/lib/tokenStore`; SessionManager/GovernedEvolutionView import `SeeMoreList`; QualityView/EnsembleHealthView import `ToolAuditTrailTable` | `git grep HEAD` + `grep -rl` |
| CI run 34039897688 | push to testing @ `9961fa3d`, 2026-09-06: **frontend failed** ("Mutation tests" — final score 73.08 < break 75; 130 mutants: 95 killed / 21 survived / 14 no-coverage), **backend failed** ("Format check" — 2 files would be reformatted; the full `pytest` step never ran); governance, feature-obligations, test-harness-js, qa-contract-stack green; desktop green (continue-on-error) | `gh run view` + `gh api .../jobs` (read-only) |
| backend format debt (full candidate) | `ruff format --check .` in backend → **15 files** would be reformatted (list matches the brief exactly) with repo venv ruff **0.16.4**; CI resolves `ruff>=0.8.0` → **0.16.6** | `backend/.venv/bin/ruff format --check .`; CI log; `backend/pyproject.toml:62` |
| frontend lint | `ChatModelControls.tsx 20:11 error @typescript-eslint/no-empty-object-type` (empty `interface ModelChoice extends ChatModelChoice {}`) — reproduced | local `eslint` on the file |
| public quality | `audit()` returns exactly 2 findings: AGENTS.md (line 142, compass-forge block "Project root") and `docs/build-stream/2026-09-08-pi-capability-inheritance.md` contain the machine-local checkout path substring the audit labels `machine_checkout_path`; `tests/test_public_repo_quality.py` fails (reproduced) | ran `scripts/public_repo_quality_audit.audit()` + pytest |
| whitespace debt | `git diff --check origin/main` → **295** trailing-whitespace / blank-line-at-EOF findings, concentrated in `docs/build-stream/*` | `git diff --check origin/main` |
| known-green on full candidate | integrity, ci-governance, test-harness, workflow-contracts, qa-capabilities checks and `security_benchmark.py --fail-on-threshold` all exit 0 (re-run by this architect); backend suite per brief 1 failed / 2,329 passed / 5 skipped — the 1 failure is the public-quality test above | re-ran all six; full suite result taken from the brief (not re-run — ~2,335 tests; scheduled in W2) |
| branch protection on `main` (API, read-only) | required contexts: **["governance"]** only; required approvals **0**; code-owner review **false**; dismiss-stale **false**; enforce_admins **false**; allow_force_pushes **true**; required_linear_history **false** | `gh api repos/.../branches/main/protection` |
| CF state | 413 tasks: 222 done, **181 open**, 5 claimed, 5 canceled; open includes CF-SPEC-29 ×13 (CF-344…356) and CF-SPEC-30 ×12 (CF-402…410, this pipeline); `compass-forge next` → CF-SPEC-30/CF-410; doctor: pass (native nucleus); **`impact` and `graph` return `not_yet_native`** (Rust migration gate) — CF-indexed context comes from the conductor packet only; SC-002 of CF-SPEC-30 ("no linked task remains incomplete when the spec is accepted") makes CF-SPEC-29 reconciliation a hard dependency | `task list`, `next`, `doctor`, `impact` (all native binary, from repo root) |
| lifecycle truth | confirmed contradictory: `pi-capability-inheritance` S3-review/in-progress/"conductor may dispatch implementation"; `agentic-long-horizon-improvement` S1-plan/in_progress (CF-SPEC-19 ×10 tasks); `benchmark-modernization-full-ui-suite` S0-frame/in_progress/blocked-on-owner-approval **while** next_action claims "Done. CF-SPEC-24 accepted 18/18"; `systemwide-audit-coverage` done but retains accepted-risk F-007 + deferred Docker/Playwright matrices; the 2026-09-09 convergence lifecycle file itself is **untracked**; `2026-09-08-pi-capability-inheritance.md` is tracked and contains the machine-path leak | read STATUS BLOCKs of the four files |
| mutation harness | frontend Stryker `mutate: ["src/lib/runtimeConfig.ts"]`, thresholds {high 90, low 80, break 75}; local run cannot start (vitest-runner plugin init failure — environment defect in `node_modules`, per brief; not re-run by this architect); backend mutation gate green in CI (64 passed) | `frontend/stryker.config.json`; CI log |
| QA/browser lane | `docker-compose.qa.yml` profiles: ui, contract, synthetic, audit, reset; 79 simulation scenario files; CI `qa-contract-stack` renders compose + runs contract pytest only — **no container-first Playwright journeys in CI** | file inspection |
| governance job | `governance` job holds `contents: write` and on `main` pushes the README version-badge commit **directly to main** | `.github/workflows/ci.yml` |

### A.2 The three candidate surfaces and the verdict

| Surface | Contents | Verdict | Evidence-based reason |
|---|---|---|---|
| A — `origin/testing` (`9961fa3d`) | 994 commits over main | **Rejected as candidate** | Missing all 64 local commits (pi-ai 0.85.1 lockstep, five review-fix commits, lifecycle truth) and the entire working-tree feature work; its CI run is red (mutation 73.08, format). |
| B — local committed testing (`85f64e4d`) | A + 64 commits | **Rejected as candidate** | Internally inconsistent: committed-in-working-tree *tracked* files are fine, but the surface excludes the untracked modules that the (locally modified) tracked files import; without the classified working tree the frontend cannot typecheck/build. It also lacks the newest feature work. |
| **C — local committed testing + classified working tree** | B + all classified working-tree and untracked content | **SELECTED** | The only surface that is functionally complete (import graph closes) and contains all recent Build Stream work. All known-green evidence was measured on this surface. |

Rule: **the candidate is C, and only C**. Surfaces A/B remain untouched on the remotes; nothing is pushed during planning or implementation until the certification wave's owner-gated push step.

### A.3 Reconciliation algorithm (classification protocol)

Never discard, reset, clean, prune, or overwrite anything. The protocol *classifies*; only the owner can approve exclusions of ambiguous work.

1. **Inventory** (machine-generated, exhaustive):
   - `git status --porcelain -uall` → modified/untracked lists;
   - `git diff --numstat HEAD` → per-file change size;
   - `git ls-files --others --ignored --exclude-standard --directory` (top-level only) → ignored-but-present roots, listed **read-only** (never deleted).
2. **Classify every path** into exactly one class, recorded in the Candidate Classification Manifest (`docs/promotion/2026-09-09-candidate-classification.md`, committed):
   - **C1 include — product code**: `backend/`, `frontend/src`, `relay/`, `desktop/`, `pi-runtime/`, `recipes/`, `qa/`, root configs.
   - **C2 include — tests & fixtures**: `tests/**` including `tests/document_corpus/rich/**` (synthetic research-corpus fixtures + generator; verified to live only under `tests/`), `tests/simulation`, `tests/real_user_benchmark`.
   - **C3 include — docs/lifecycle**: all `docs/**` including the 10 untracked lifecycle files, TESTING.md, testing/*, AGENTS.md, security evidence files.
   - **C4 exclude — generated/ignored**: `node_modules`, `.results`, build outputs, caches. Present locally, never committed, never deleted.
   - **C5 exclude — protected & local**: `LLMs/`, `Model_Finetuning/` (untouchable per contract), `.compass-forge/` (gitignored at .gitignore:142 — its state rides nowhere), `.env*`, keys. Never committed, never deleted.
   - **C6 quarantine — ambiguous/ambient**: anything not demonstrably C1–C3 (e.g., stray personal notes, WIP unrelated to any lifecycle file). Copied to a **quarantine branch** `quarantine/ambient-20260909` (branch created at current state, non-destructive) and left out of the candidate. Owner arbitrates later; the working tree copy is untouched until the owner decides.
   - The classification must prove dependency closure: for each untracked C1 file, at least one tracked/modified importer must exist (this is exactly what validated `tokenStore.ts`, `SeeMoreList.tsx`, `ToolAuditTrailTable.tsx`); files with no importer are demoted to C6.
3. **Owner spot-check gate**: the manifest (every path + class + one-line rationale) is presented in the lifecycle file; the same owner approval that authorizes implementation ratifies the manifest. The default for any path the owner does not rule on is C6 (quarantine), never silent inclusion.
4. **Commit the candidate**: C1–C3 paths are committed to local `testing` in a small number of reviewable commits (e.g., "candidate: frontend chat/model work", "candidate: tests & corpus fixtures", "candidate: docs & lifecycle"). Produce the **Candidate Base SHA**.
5. **Freeze**: record the Candidate Base SHA in the lifecycle file and in `docs/promotion/`; create a **local-only** annotated tag `rc/testing-to-main-20260909` (no push). The tag is documentation, not a gate; the dossier binds to the Promotion SHA (W7) which includes the repair-wave commits on top of the Candidate Base.

### A.4 Drift-prevention rules (candidate basis cannot silently move)

- Every wave appends commits; **no force-push, no amend, no rebase** of any commit that a previous wave's evidence refers to.
- Each wave's ledger entry records the worktree HEAD SHA before and after its commits (`git rev-parse HEAD` in the evidence).
- Between waves, only wave-owned paths may change; the fixer of wave N re-runs `git status --porcelain` and must explain any path outside its declared scope (new ambient edits go to C6 quarantine, not into the wave).
- The **Promotion SHA** (W7) is the last commit; the FULL verification matrix (§E) re-runs on it, and the dossier records `git log --oneline <Candidate-Base>..<Promotion-SHA>` as the audit trail of everything added after the freeze.
- CI evidence must be bound to the Promotion SHA: the push to `origin/testing` happens only in W7's owner-gated step, and the green run's `headSha` must equal the dossier SHA (checked with `gh run list --commit`).

### A.5 Rollback and recovery

- Before W0's first commit: create local branch `backup/pre-candidate-20260909` at `85f64e4d`. Cheap, non-destructive, survives everything.
- Ambient/quarantined work: `quarantine/ambient-20260909` branch (A.3 step 2). The working tree is never cleaned; if a later wave must remove a local-only file from the *index*, it is first committed to the quarantine branch.
- Every wave is a small commit set; rollback = `git revert` of the wave's commits (never `reset --hard` on the shared worktree), with the wave's ledger entry recording the revert SHA.
- Protected folders (`LLMs/`, `Model_Finetuning/`) and ignored local state are untouched by every rollback path; reflog remains intact because nothing is rewritten.
- Remotes are only touched in W7 (push of the Promotion SHA to `origin/testing`), owner-gated; `main` is only touched by the owner's PR merge after the dossier.

---

## B. Findings register

Severity: **S1** blocks promotion; **S2** must be fixed before promotion or explicitly accepted by the owner; **S3** quality debt tracked for follow-up. "Wave" = owning wave in §C. Disposition: blocking / deferred-with-rationale / owner-decision.

| ID | Sev | Surface | Evidence (measured 2026-09-09) | Root cause | Consequence | Proposed correction | Verification | Wave | Disposition |
|---|---|---|---|---|---|---|---|---|---|
| F-C-01 | S1 | Release candidate | No ref contains all recent work; 3 divergent surfaces (§A.1) | work accumulated on testing + local commits + untracked files without a freeze ritual | any "green" claim is unfalsifiable; risk of shipping or losing ambient work | §A.3 classification protocol → Candidate Base SHA + manifest + local tag | manifest committed; `git status` clean-for-scope; SHA in lifecycle | W0 | blocking |
| F-C-02 | S1 | backend format | 15 files need reformat locally (ruff 0.16.4); CI (0.16.6) saw 2 at `9961fa3d` | format debt re-introduced by recent edits; `ruff>=0.8.0` floor (pyproject:62) lets the formatter version drift between machines | CI backend job fails; full pytest never runs remotely; format results not reproducible | run `ruff format` once with the **pinned** version and commit; pin exact `ruff==0.16.6` (or the chosen pin) in dev deps; document the pin | `ruff format --check .` exit 0 on Promotion SHA (CI + local) | W2 | blocking |
| F-C-03 | S1 | CI topology | backend job: Format check (fails) runs before full pytest ⇒ suite skipped; frontend: mutation before build ⇒ build evidence lost | sequential single job mixes independent failure domains | information hiding: a style failure masks functional results; stale-green risk | split into independent jobs (§D); format/lint jobs parallel to test jobs | job graph in workflow; simulated-failure drill proves suite still reports when format fails | W4 | blocking |
| F-C-04 | S1 | frontend mutation | score 73.08 < break 75; 130 mutants in `runtimeConfig.ts`: 95 killed / 21 survived / 14 no-coverage (CI log) | tests assert the happy paths but not the survived mutants; no-coverage mutants have no test touching them | genuine quality gap; CI red | add/extend unit tests to kill the 21 survivors; cover the 14 no-coverage mutants; where a surviving mutant reveals a real bug, fix the implementation. Threshold stays 75 (targets: high 90 / low 80 unchanged) | `npm run test:mutation` ≥ 75 locally and in CI on Promotion SHA | W3 | blocking |
| F-C-05 | S2 | local tooling | local Stryker cannot init the vitest-runner plugin from present `node_modules` (per brief; not re-run) | corrupted/partial node_modules installation | local verification of F-C-04 impossible | bounded, owner-visible `npm ci` reinstall in `frontend/` (generated dir; C4); if it persists, capture `stryker` init error and file as separate task | mutation run completes locally | W3 | blocking for W3 evidence |
| F-C-06 | S1 | frontend lint | `ChatModelControls.tsx:20:11` `no-empty-object-type` (reproduced) | `interface ModelChoice extends ChatModelChoice {}` alias idiom | CI frontend lint red at next push | replace with `type ModelChoice = ChatModelChoice` | `npm run lint` exit 0 | W2 | blocking |
| F-C-07 | S1 | public quality | audit(): 2 findings — AGENTS.md:142 and `docs/build-stream/2026-09-08-pi-capability-inheritance.md` contain the machine-local checkout path (`machine_checkout_path`); test_public_repo_quality fails (reproduced) | absolute machine path written into tracked docs (AGENTS.md compass-forge block; a doc reference) | release-blocking test; private-environment leak | replace with repo-relative ("repository root") in both files; sweep tracked files for the substring before the final commit | `pytest tests/test_public_repo_quality.py` green; audit() == [] | W2 | blocking |
| F-C-08 | S2 | repo hygiene | `git diff --check origin/main` → 295 trailing-whitespace / blank-line-at-EOF findings in docs/lifecycle files | editors/agents emitting markdown trailing spaces; no automated guard | noisy diffs; check_integrity-class tools and reviewers distracted | W2 hygiene pass: strip trailing whitespace/EOF blank lines on the affected tracked files (content-preserving); add a `git diff --check <base>` step to CI (blocking, docs-scoped) | `git diff --check origin/main` == 0 after candidate commits are in; CI step green | W2 | blocking |
| F-C-09 | S1 | lifecycle truth | 4 contradictory STATUS BLOCKs (§A.1); convergence lifecycle file untracked | ledgers updated without status-block discipline; recent lifecycle docs never committed | "older completed files vs newer active records" ambiguity; untracked truth can be lost | W1: reconcile each file (pi-capability-inheritance → completed-or-blocked with explicit owner-gate note; long-horizon → explicitly deferred with CF-SPEC-19 task disposition; benchmark-modernization → resolve S0-vs-Done contradiction to the truth CF-SPEC-24/21 evidence supports; systemwide-audit-coverage → annotate F-007 accepted-risk + deferred matrices as explicit deferrals); commit all lifecycle docs | status blocks parse; every Sep 6–9 lifecycle file tracked; dispositions recorded in manifest | W1 | blocking |
| F-C-10 | S1 | Compass Forge | CF-SPEC-29 has 13 open tasks (CF-344…356); 181 open tasks repo-wide; SC-002 of CF-SPEC-30 requires zero incomplete linked tasks at spec acceptance; `next` → CF-SPEC-30 | wave tasks were never closed after work shipped; specs accumulated | CF-SPEC-30 can never be accepted; conductor pipeline wedged | W1: reconcile CF-SPEC-29 tasks against the shipped pi-capability work — close with evidence where the work+verification exist, cancel with rationale where superseded; older-spec stale tasks (CF-SPEC-2…25) get a documented administrative disposition (close/cancel) **only where evidence proves the outcome**; nothing is closed by assumption | `task list` shows CF-SPEC-29/30 linked tasks resolved with evidence rows; `next` unblocked | W1 | blocking |
| F-C-11 | S1 | CF index/graph | index schema 12 vs required 21 (brief); `impact`/`graph` `not_yet_native` (measured); `graph_usable=false` | deliberate Rust-only migration; index refresh pending | impact analysis can be silently invented; architecture-gate evidence weaker | W1: run the deliberate native index refresh (`refresh-project`), verify schema/freshness; until native `impact` migrates, record manual dependency analysis per wave (as this plan does) and mark the capability gap as architecture debt — never fabricate impact output | refresh succeeds; doctor/`status` freshness fields honest; waves record manual impact notes | W1 | blocking |
| F-C-12 | S1 | branch protection | required=["governance"], 0 approvals, no code-owner, enforce_admins off, force-push allowed, linear history off (API) | protection never updated as CI architecture grew | any of backend/frontend/QA/UI failures may merge to main; force-push can rewrite main | §D.13 owner checklist (GitHub settings, not code): required contexts per §D.4, ≥1 approval, code-owner review, enforce admins, disallow force pushes, require linear history + up-to-date branches | settings diff recorded in dossier; API re-check after owner applies | W5 | blocking (owner-gated) |
| F-C-13 | S2 | CI governance job | `governance` pushes README badge commits **directly to main** with `contents: write` | badge sync predates protection design | a job writes to main outside the PR path; after F-C-12 it will also start failing (no bypass) | convert badge sync to a promotion-PR step (version bump inside the PR) or have the job open an auto-PR on main; job keeps only check semantics on testing | workflow change; no direct-to-main push step remains, or an explicit owner-approved bypass is documented | W4 | blocking before W5 |
| F-C-14 | S2 | desktop CI | `cargo check` is `continue-on-error` ("Dependencies may require system libs") — success is ambiguous (green in run 34039897688 without proving compile) | Ubuntu runner lacks Tauri system deps | desktop regressions can reach main invisibly; status misleading | decide (owner): (a) fix runner deps and make cargo check blocking, or (b) keep advisory but emit a distinct `desktop-check` context explicitly marked non-gating in TESTING.md + dossier | honest desktop status in workflow + docs | W4 | owner-decision (default: (a) try; fall back (b)) |
| F-C-15 | S2 | QA/browser CI | qa-contract-stack renders compose + pytest contracts only; no container-first Playwright journeys in CI; QA artifact workflow builds artifacts without proving journeys | browser lane never added to CI | UI regressions reach main; Full UI contract unproven at release | W6 adds the journey suite; W4 wires a `qa-browser` CI job (loopback-only compose ui profile) required on testing pushes and main PRs; honest `not_runnable` when live deps absent | dated journey verdicts + CI job green on Promotion SHA | W4+W6 | blocking |
| F-C-16 | S2 | lint correctness | global `ruff check` advisory (continue-on-error) with ignored F821 undefined-name findings possible; changed-file strict lint covers only diff (per ci.yml comment: 378 legacy errors) | historical debt; advisory posture | release-critical correctness (F821) can escape on unchanged files | W2: triage F821 class immediately (fix or prove false-positive); W4: after count ↓, flip global lint to blocking (existing plan in ci.yml comment) — never by deleting rules | `ruff check .` blocking green on Promotion SHA | W2+W4 | blocking (F821), staged for full lint |
| F-C-17 | S3 | untracked corpus | ~70 `tests/document_corpus/rich/**` research fixtures + generator untracked | new research-spine test data never committed | tests referencing them are environment-dependent | classify C2, commit; verify fixture content is synthetic (generator-authored) and stays under `tests/` | files tracked; corpus generator reproducible | W0 | blocking (inclusion) |
| F-C-18 | S3 | main staleness | main tip 2026-05-27; 994-commit, 1,233-file, +223k/−13k fast-forward pending | long-lived testing branch | big-bang promotion risk; main's historic green runs prove nothing about this candidate (workflow on main predates current architecture) | promotion dossier + full matrix on the exact Promotion SHA (§E); owner chooses FF vs merge commit (recommendation: merge commit `--no-ff` for an auditable promotion point) | dossier section "main promotion mechanics" | W7 | owner-decision on merge mechanics |
| F-C-19 | S3 | spec doc drift | `docs/architecture/research-validity-contract.md` header cites "CF-SPEC-124 / CF-1590" — no such objects exist in CF state (max task id 413) | doc written against a planned/external numbering | minor truth drift in a protected-contract doc | correct the header reference in W1's doc pass (content untouched otherwise) | grep shows valid references | W1 | non-blocking |
| F-C-20 | S2 | required-check mapping | only `governance` required while 13 jobs exist; nothing verifies required contexts match job names | no contract between workflow graph and protection | required-check rot; stale green | add `scripts/check_required_checks.py` (or extend check_ci_governance.py): parse ci.yml job ids, compare against a committed required-checks manifest consumed by W5's owner settings change | new check green; manifest committed | W4 | blocking before W5 |
| F-C-21 | S3 | plan-independence | this draft was written without reading plan-a/plan-b; conductor packet context (graph hints) used only as a lexical starting map | by design | — | synthesizer reconciles all three | n/a | Phase 0 | informational |

---

## C. Wave manifest proposal (strict sequential)

Waves are strictly ordered; each wave's evidence and review must pass before the next starts. Mapping to the conductor's manifest: W0→`candidate-boundary`, W1→`control-plane-lifecycle`, W2+W3→`correctness-quality`, W4+W5→`ci-enforcement`, W6→`browser-spine-acceptance`, W7→`promotion-certification`. (W3 is split out of `correctness-quality` because mutation work has a different failure/rollback shape than mechanical fixes; W5 is the non-automatable half of `ci-enforcement`.)

### W0 — Freeze the candidate boundary (conductor: candidate-boundary)
- **Objective:** one immutable Candidate Base SHA containing exactly the classified work.
- **Scope:** git operations (branch backup, quarantine branch, classified commits, local tag), `docs/promotion/2026-09-09-candidate-classification.md`, lifecycle ledger update. **Exclusions:** no remote push; no deletions; no touching C4/C5 paths; no code edits.
- **Inputs:** §A.3 protocol; the measured inventory (§A.1).
- **Tasks:** backup branch → inventory → classification manifest → dependency-closure proof for untracked C1 files → owner manifest ratification (folded into the already-granted implementation approval; unresolved paths default to quarantine) → classified commits → Candidate Base SHA + local tag `rc/testing-to-main-20260909` → record in lifecycle.
- **Dependencies:** none (first wave). **Verification:** `git log --stat` of candidate commits; `git status --porcelain` shows only C4/C5/C6 remainder; manifest committed; `git rev-parse` recorded. **Gates:** CF `architecture_drift` + `test_ownership` run before/after; evidence rows attached.
- **Review questions:** Does every included untracked file have a proven importer or documented rationale? Is any C6 path silently inside the candidate? Are C5 paths untouched?
- **Completion:** Candidate Base SHA recorded; manifest ratified; remainder classified. **Rollback:** §A.5. **Residual risk:** owner disagreement on a classification → quarantine path, candidate recomputed (cheap, before repairs).

### W1 — Reconcile lifecycle and control-plane truth (conductor: control-plane-lifecycle)
- **Objective:** Git, Build Stream ledgers, CF specs/tasks/evidence, and CI truth agree with the candidate; hidden blockers surfaced.
- **Scope:** 4 contradictory lifecycle files (F-C-09), untracked lifecycle docs commit, CF-SPEC-29/CF-SPEC-30 task reconciliation (F-C-10), native index refresh (F-C-11), doc drift fix (F-C-19). **Exclusions:** no product code; no threshold changes; no history rewrite in CF.
- **Verification:** lifecycle STATUS BLOCKs parse and agree with their ledgers; `task list` shows CF-SPEC-29 open tasks resolved with evidence (close-with-evidence or cancel-with-rationale); index refresh succeeds (schema ≥ 21) and `status` freshness is honest; `pytest tests/test_public_repo_quality.py` still relevant docs pass; `python scripts/check_integrity.py` green.
- **Gates:** CF spec/task evidence rows; architecture gate recorded. **Review questions:** Was any task closed without evidence? Does any lifecycle file still claim implementation dispatch while blocked? **Completion:** `next` no longer points at unresolved CF-SPEC-29 work; ledger truthful. **Rollback:** revert doc commits; CF task state changes are append-only evidence rows (no destructive mutation). **Residual risk:** a genuinely unfinished CF-SPEC-29 obligation surfaces → it becomes a new blocking task instead of a close.

### W2 — Repair correctness, format, lint, public quality, whitespace (conductor: correctness-quality, part 1)
- **Objective:** every known mechanical red check green on the candidate, root-caused, with thresholds untouched.
- **Scope:** F-C-02 (ruff format + **pin ruff**), F-C-06 (ChatModelControls type alias), F-C-07 (machine-path leak in AGENTS.md + pi-capability doc), F-C-08 (295 whitespace findings + CI `git diff --check` guard), F-C-16 part 1 (F821 triage). **Exclusions:** no behavior changes beyond the named fixes; no threshold edits; no new features.
- **Verification (exact commands):**
  - `cd backend && ruff format --check .` → exit 0; `ruff check ../tests/test_public_repo_quality.py` context audit: `pytest ../tests/test_public_repo_quality.py -q` → green;
  - full backend suite re-run: `pytest ../tests/ -m "not live_llm"` → 0 failed (baseline: 2,329 passed / 5 skipped / 1 failed);
  - `cd frontend && npm run lint && npx tsc --noEmit && npm run test:unit` → green (baseline 89/89);
  - `git diff --check origin/main` → 0 on files touched by the candidate;
  - the six credential-free governance checks + `security_benchmark.py --fail-on-threshold` re-run green (security evidence paths did not change; if the AGENTS.md/doc edits touch trigger patterns, update control matrix per contract).
- **Gates:** CF command evidence per check; blind review queued. **Review questions:** Was any check weakened or scoped down to pass? Does the ruff pin match CI's resolved version? **Completion:** all commands exit 0; wave ledger records before/after counts. **Rollback:** revert wave commits (mechanical, low risk). **Residual risk:** ruff pin changes formatting output vs the W2 run → re-run format in W3/W7 (the Promotion SHA re-verify catches this).

### W3 — Mutation quality and harness repair (conductor: correctness-quality, part 2)
- **Objective:** frontend mutation ≥ break threshold with honest coverage; backend mutation stays green; local harness repaired.
- **Scope:** F-C-04 (kill 21 survivors + 14 no-coverage in `runtimeConfig.ts`: new unit tests; implementation fixes where a mutant exposes a real bug), F-C-05 (`npm ci` reinstall of `frontend/node_modules` — C4 generated dir, owner-visible note in ledger). **Exclusions:** thresholds {90/80/75} unchanged; no mutation of new files without a recorded decision; no test weakening.
- **Verification:** `cd frontend && npm run test:mutation` → score ≥ 75 (target: no-coverage count 0 within the mutated scope), survivors enumerated to zero or each justified in the ledger; `npm run test:unit` green; backend mutation: `python scripts/run_backend_mutation.py` green (re-run once). Mutation report artifact kept at ignored result root; summary into `testing/TEST_HISTORY.md`.
- **Gates:** CF command evidence; review verifies score arithmetic (killed/(killed+survived+no-cov)) from the raw report, not the summary line. **Review questions:** Are any "tests" added that assert tautologies to kill mutants? Are no-coverage mutants covered or explicitly scoped? **Completion:** threshold met without touching thresholds; harness reproducible locally. **Rollback:** revert test commits; thresholds never moved. **Residual risk:** survivors reveal real bugs → implementation fixes enter W3 with their own tests (still no scope creep: same file scope).

### W4 — CI target architecture, in-repo (conductor: ci-enforcement, part 1)
- **Objective:** workflow graph matches §D; independent failure domains; no information hiding; required-check contract testable.
- **Scope:** `.github/workflows/ci.yml` restructure per §D.1–D.12; F-C-03, F-C-13, F-C-14, F-C-15 (CI side), F-C-20 (required-checks manifest + checker); TESTING.md / testing/TEST_HISTORY.md updates (topology change). **Exclusions:** no GitHub settings mutation (W5); no gate weakening; no live-credential lanes added.
- **Verification:** `python scripts/check_workflow_contracts.py` extended and green; `actionlint` (if available) or workflow render check; simulate-failure drill on a throwaway branch PR (docs-only test job failure must NOT mask backend results); CI run on the candidate shows the new job graph with all required contexts emitted.
- **Review questions:** Does any required job have `continue-on-error` or `if: always()` shortcuts that can produce green-without-running? Are caches artifact-scoped so a red job's artifacts still upload? **Completion:** §D graph implemented; contract check green. **Rollback:** revert workflow commit (old graph known-red but understood). **Residual risk:** runner-time/cost growth from the browser lane → mitigation in §D.9 (change-scoped triggers).

### W5 — Owner-gated GitHub branch protection (conductor: ci-enforcement, part 2)
- **Objective:** repository settings enforce the architecture (F-C-12). **Not automatable in-repo**; the wave delivers an exact, checked-against-API checklist and verifies after the owner applies it.
- **Checklist (from measured API state):** required checks ← §D.4 manifest (via `scripts/check_required_checks.py` output); required approving reviews ≥ 1; require code-owner review; dismiss stale reviews; enforce admins; disallow force pushes; require linear history; require branches up to date. The `governance` direct-to-main push must already be removed (W4/F-C-13) or it will fail under the new rules.
- **Verification:** re-run the protection API read; diff vs checklist recorded in dossier. **Completion:** settings match checklist. **Rollback:** owner reverts settings (documented). **Residual risk:** enforcing admins may block the owner's own emergency pushes — explicit owner ack.

### W6 — Container-first browser acceptance (conductor: browser-spine-acceptance)
- **Objective:** prove the changed product behavior in a real browser through the QA container lane, with dated verdicts on the candidate.
- **Scope:** `tests/simulation` + `tests/real_user_benchmark` journeys for every changed UI surface in the candidate (chat model controls/settings work, metrics/quality views, auth token paths touched by tokenStore); roles admin/researcher/viewer/stranger where auth-adjacent; light/dark; 375px reflow; keyboard Tab + visible focus; loading/error/empty states; synthetic data only; Research-Spine probes where research artifacts are touched (document_corpus fixtures are test-only); donor/model paths only if the candidate touched them (fail `not_runnable` honestly if a live dependency is absent); update `tests/simulation/lib/scenario-registry.mjs` + coverage matrix + TESTING.md/TEST_HISTORY.md.
- **Environment:** `docker compose -f docker-compose.qa.yml --profile ui up` loopback-only; Playwright against the container stack. **Exclusions:** no live private LLM endpoints; no golden-data mutation.
- **Verification:** scenario run manifests with dated verdicts + deterministic screenshot/HAR paths under ignored result roots; summary rows into `testing/TEST_HISTORY.md` with the candidate SHA; `not_runnable` entries name the missing capability.
- **Review questions:** Is any step an API call masquerading as a journey? Are all matrix cells either covered or honestly marked? **Completion:** coverage map updated; no silent skips. **Rollback:** journey failures block promotion (fix or owner-accept as deferred with rationale). **Residual risk:** flaky selectors → fix selectors as part of the feature (contract requires scenario updates with the change).

### W7 — Promotion certification (conductor: promotion-certification)
- **Objective:** one exact Promotion SHA with the full §E matrix re-run, blind independent review dry, dossier complete; owner approval still pending.
- **Scope:** final verification sweep; blind architectural/code review of the whole candidate delta (`origin/main..Promotion-SHA` is too large to review file-by-file — review is scoped to the candidate-vs-origin/testing delta plus the wave commits: `git diff origin/testing..Promotion-SHA` + `git log origin/testing..Promotion-SHA`); findings remediated and re-reviewed until dry; `docs/promotion/2026-09-09-promotion-dossier.md`; owner-gated push of the Promotion SHA to `origin/testing`; owner-gated PR testing→main. **Exclusions:** no merge; no PR creation without separate authorization; no threshold changes.
- **Verification:** every §E row green on the Promotion SHA; CI run `headSha` == Promotion SHA; dossier binds SHAs, evidence row ids, journey verdicts, security scorecard, mutation report, CF task/spec closure, and the branch-protection API snapshot.
- **Completion:** §H verdict = READY; owner pause. **Rollback:** promotion simply does not proceed; candidate remains on testing. **Residual risk:** late findings → remediation loop inside W7 (delta re-review), or a new wave if scope changes.

---

## D. CI target architecture

**D.1 Job graph (independent failure domains; every release-relevant signal is its own job):**

```
feature-obligations ────────────┐ (unchanged; fail-closed classification)
governance (checks only) ───────┤   integrity, ci-governance, test-harness,
  [main-push badge sync REMOVED │   security-release-readiness, security-benchmark,
   → auto-PR or PR step, F-C-13]│   change-obligations (PR), scorecard artifact
backend-lint ───────────────────┤   ruff format --check (blocking) + strict changed lint
backend-tests ──────────────────┤   compileall, rehearsal, harness smoke, property,
backend-mutation ───────────────┤   evolution regressions, FULL pytest
frontend-lint ─┐                │
frontend-type ─┤ (parallel)     │   eslint / tsc / vitest unit
frontend-unit ─┘                │
frontend-mutation ──────────────┤   stryker (break 75 unchanged)
frontend-build ─────────────────┤   next build
test-harness-js ────────────────┤   relay tests, simulation static, RUB static
qa-contract ────────────────────┤   compose render + contract/synthetic/audit pytest
qa-browser ─────────────────────┤   NEW: compose ui profile + Playwright journeys (D.9)
desktop-check ──────────────────┘   cargo check — blocking or explicitly non-gating (F-C-14)
```

**D.2 Independence rule:** no job may `needs:` a job whose failure is not a true precondition (the only retained dependency: `qa-contract`/`qa-browser` on `feature-obligations` for the capability declaration). Format/lint never gate test execution; a red format cannot hide a red suite.

**D.3 Triggers:** push to `main|staging|testing` = full matrix; PR to those branches = full matrix (PRs are rare and release-sized here); `schedule:` weekly full-matrix on `main` and `testing` to catch rot (runner-image drift, dependency drift) — required checks must not depend on push-only paths.

**D.4 Required checks (main and testing):** `governance`, `feature-obligations`, `backend-lint`, `backend-tests`, `backend-mutation`, `frontend-lint`, `frontend-typecheck`, `frontend-unit`, `frontend-mutation`, `frontend-build`, `test-harness-js`, `qa-contract`, `qa-browser`, `desktop-check` (or its explicitly non-gating context if the owner picks F-C-14(b)). Enforced by the committed manifest + `check_required_checks.py` (F-C-20); the W5 settings change consumes exactly this list.

**D.5 Change-scoped vs full:** full matrix on release branches (this promotion is a 994-commit event; scoping would be false economy). Change-scoping is permitted only for the `qa-browser` journey selection on ordinary PRs *to testing* (select scenarios by registry impact tags), never on PRs to main or pushes.

**D.6 Caches/artifacts:** pip/npm/cargo caches per job (swatinem/rust-cache already for desktop); artifacts: feature-obligations report, security scorecard, mutation reports (HTML), journey verdicts + screenshots/HARs, dossier bundle. Retention ≥ 90 days for promotion evidence artifacts (owner-configurable); promotion dossier also copies the key summaries into `docs/promotion/` so evidence survives artifact expiry.

**D.7 Mutation policy:** thresholds stay {high 90, low 80, break 75}; no-coverage mutants count as failures (Stryker default) and the wave target is zero no-coverage within the mutated scope; the mutated scope grows only by explicit, reviewed decisions (never shrink to pass); backend `mutmut` gate unchanged and blocking.

**D.8 Format/lint policy:** ruff version pinned exactly (dev dep) and CI installs the same pin (no floating floor); `ruff format --check` blocking; changed-file strict lint blocking; global `ruff check` moves advisory→blocking after the F-C-16 count reaches zero, with F821 triaged immediately (correctness class); the `git diff --check` hygiene guard blocking (docs-scoped).

**D.9 Container/Playwright:** `qa-browser` job runs `docker compose -f docker-compose.qa.yml --profile ui` with **loopback-only publication**, installs Playwright, runs the registered journeys with dated verdicts and deterministic artifact paths; missing live capabilities (private LLM profile, donated compute, third-party keys) produce explicit `not_runnable` verdict rows naming the missing capability — never a silent skip, never a fabricated pass.

**D.10 Credential-free vs live lanes:** default = credential-free (everything above). Live lanes (live-LLM evals, donor compute) remain manual/operator-gated and are excluded from required checks; their absence cannot turn any required context green.

**D.11 Desktop status:** decide blocking vs explicitly-non-gating (F-C-14); whichever is chosen, TESTING.md and the dossier must state it and the context name must make it obvious from the PR UI.

**D.12 Stale/misleading-green prevention:** (a) required-context manifest checked in CI itself (a workflow change that renames a job fails the contract check until the manifest is updated); (b) audit: no `continue-on-error` on any required job (script-enforced); (c) weekly scheduled runs keep checks exercised; (d) main's badge-sync job may not push directly (F-C-13) so main's status is produced by the same matrix as testing's; (e) `concurrency` groups keep only the latest run per ref.

**D.13 External (owner-gated) settings change:** the W5 checklist (F-C-12) applied through GitHub UI/API by the owner; verified by re-reading the protection API and recording the snapshot in the dossier. In-repo workflow edits alone cannot fix this — the plan keeps them strictly separated.

---

## E. Verification matrix

Legend: **B** = blocking for promotion; **CF** = credential-free; **R** = must be re-run on the final Promotion SHA. Evidence location "CF" = Compass Forge `task evidence` rows on the wave task; "dossier" = `docs/promotion/2026-09-09-promotion-dossier.md`.

| # | Surface / claim | Command / journey | Environment | Expected | Evidence | B | CF | R |
|---|---|---|---|---|---|---|---|---|
| 1 | Candidate boundary | `git rev-parse HEAD`, `git status --porcelain -uall`, manifest diff | local worktree | SHA frozen; remainder = C4/C5/C6 only | lifecycle + dossier | ✓ | ✓ | ✓ |
| 2 | Backend format | `cd backend && ruff format --check .` | repo venv, pinned ruff | exit 0 | CF + dossier | ✓ | ✓ | ✓ |
| 3 | Backend lint (changed) | `python scripts/check_ruff_changed.py --base … --head …` | CI/local | exit 0 | CF | ✓ | ✓ | ✓ |
| 4 | Global ruff advisory→blocking | `cd backend && ruff check . --statistics` | CI/local | F821 count 0; blocking by W4 decision point | CF | ✓ | ✓ | ✓ |
| 5 | Full backend suite | `pytest ../tests/ -m "not live_llm"` | repo venv | 0 failed (~2,334 passed) | CF + dossier | ✓ | ✓ | ✓ |
| 6 | Backend mutation gate | `python scripts/run_backend_mutation.py` | repo venv | green (as today) | CF | ✓ | ✓ | ✓ |
| 7 | Public quality | `pytest tests/test_public_repo_quality.py -q` | repo venv | green; `audit() == []` | CF | ✓ | ✓ | ✓ |
| 8 | Frontend lint/type/unit | `npm run lint && npx tsc --noEmit && npm run test:unit` | node 24 | exit 0; 89/89 baseline preserved or grown | CF | ✓ | ✓ | ✓ |
| 9 | Frontend mutation | `npm run test:mutation` | node 24 (local `npm ci` repaired) | score ≥ 75, no-coverage = 0 in scope | CF + report artifact | ✓ | ✓ | ✓ |
| 10 | Frontend build | `npm run build` | node 24 | exit 0 | CF | ✓ | ✓ | ✓ |
| 11 | Governance battery | integrity / ci-governance / test-harness / workflow-contracts / qa-capabilities scripts | local or CI | all exit 0 | CF | ✓ | ✓ | ✓ |
| 12 | Security benchmark | `python scripts/security_benchmark.py --fail-on-threshold` | local/CI | 28/28 (or grown set) ≥ threshold | CF + scorecard artifact | ✓ | ✓ | ✓ |
| 13 | Simulation static | `tests/simulation npm run test:static` | node | green (111 syntax files / 17 checks baseline) | CF | ✓ | ✓ | ✓ |
| 14 | RUB static/contracts | `tests/real_user_benchmark npm run check` | node | green (107/107 baseline) | CF | ✓ | ✓ | ✓ |
| 15 | QA compose contracts | `pytest tests/test_qa_stack_contract.py …` | repo venv | green | CF | ✓ | ✓ | ✓ |
| 16 | Container-first journeys | `--profile ui` compose + Playwright scenarios (registry-driven) | Docker, loopback-only | dated verdicts, all matrix cells covered or `not_runnable` w/ reason | TEST_HISTORY + artifacts + dossier | ✓ | ✗ (needs Docker) | ✓ |
| 17 | CI matrix on candidate | CI run on pushed Promotion SHA | GitHub Actions | all required contexts green; `headSha` == dossier SHA | dossier | ✓ | n/a | ✓ |
| 18 | Branch protection | `gh api branches/main/protection` | API read | matches §D.4 checklist | dossier | ✓ | n/a | ✓ (snapshot) |
| 19 | CF truth | `task list` / `next` / spec show | native binary from root | CF-SPEC-29/30 linked tasks resolved w/ evidence; no stale `next` | CF evidence rows | ✓ | ✓ | ✓ |
| 20 | Lifecycle truth | STATUS BLOCK parse vs ledgers; all Sep 6–9 lifecycle files tracked | local | no contradictions; files committed | dossier | ✓ | ✓ | ✓ |
| 21 | Research Spine probes | spine contract tests + audit-profile QA (row 15) + W6 research-artifact journeys | repo venv/Docker | no bypass; provisionality/human-gates intact | CF | ✓ | ✓ | ✓ |
| 22 | Whitespace hygiene | `git diff --check origin/main` | local | 0 findings on candidate-touched files | CF | ✓ | ✓ | ✓ |

Non-blocking, explicitly **not** promotion gates (recorded honestly): live-LLM evals, donor-compute probes, VPS deployments, performance soak — each absent capability is `not_runnable`, never silently skipped.

---

## F. Research Spine assurance

- **Changed research-data paths in the candidate:** (1) `tests/document_corpus/rich/**` synthetic corpus + generator (test fixtures only — they enter the spine as *source material* inside test scenarios; they must never ship as product data; verified to live only under `tests/`); (2) research-validity/self-improvement contract tests modified in the working tree (`tests/test_research_validity_contract.py`, `tests/test_research_integrity_validation.py`, `tests/test_project_scope_contracts.py`, security control matrix + benchmark docs) — these *strengthen* the spine; (3) backend `app/` changes inspected at wave level: no new research-data ingestion/reporting path was found in the diff hotspots (chat model controls, metrics views, Pi model management, endpoint policy) — the spine trace obligation for W6/W7 reviewers is to re-confirm this on the frozen diff.
- **Gates preserved:** evidence units from raw source spans, independent multi-model coding, reliability/grounding, reconciliation, human-approved Done, and report gates are all contract-tested (`test_research_validity_contract.py` runs in row 21); nothing in this plan weakens, bypasses, or parallel-tracks them. Any spine bypass discovered during waves is architecture debt: either repaired in-scope or the promotion is blocked — never described as aligned while red.
- **Self-improvement governance:** no wave uses telemetry/ReasoningBank/Memento/autoresearch output as release evidence; lessons go to the Build Stream ledger only. RAG/GraphRAG/LLMLingua are untouched by this plan.
- **Provisionality:** until the owner merges, the candidate is provisional; the dossier labels it as such; no artifact built before W7's certification claims release status.

---

## G. Owner-gated operations (waves must NOT perform)

1. Destructive git cleanup: `reset --hard`, `clean`, `checkout -- <file>` without quarantine, history rewrite, force push, tag/branch deletion.
2. Deletion/move/prune of `LLMs/`, `Model_Finetuning/`, or any ignored local artifact (C4/C5).
3. Starting backend/frontend servers, sending chat-completion probes, loading models, or exercising live private providers (passive discovery only).
4. Secret access, printing, or persisting endpoints/tokens/connection strings.
5. GitHub repository-settings mutation (branch protection) — W5 delivers the checklist; the owner applies it.
6. PR creation and push to remotes — only in W7, only if the owner has separately authorized that step; `main` is never written by waves (F-C-13 removes the one current in-repo writer).
7. Merge to main in any form; the promotion is the owner's act on the dossier.
8. Lowering any threshold (mutation/security/quality/a11y/Research Spine) — owner decision only, none requested by this plan.

---

## H. Final release criteria (one binary verdict)

**READY** requires **all** of the following, else **NOT READY**:

1. One exact Promotion SHA recorded in the dossier; `git log origin/testing..Promotion-SHA` fully explains everything added after the Candidate Base; worktree clean for candidate scope.
2. Every intended recent Build Stream plan has a recorded disposition (included / excluded / superseded / completed / deferred) in the classification manifest and lifecycle ledgers — no file is both "done" and "in-progress" anywhere in `docs/build-stream/`.
3. No loss or accidental inclusion of ambient work: manifest ratified; quarantine branch exists; protected folders untouched (verified by path listing, not assumption).
4. Compass Forge reconciled: index refreshed (schema ≥ 21), CF-SPEC-29 and CF-SPEC-30 linked tasks resolved with evidence, no open release-blocking CF task, `next` truthful.
5. Rows 2–15, 19–22 of §E green on the Promotion SHA (local re-run), and row 17 (CI) green on the pushed same SHA.
6. Frontend mutation ≥ 75 with zero unexplained no-coverage mutants; thresholds untouched since `9961fa3d`.
7. Container-first UI verdicts dated on the Promotion SHA with the full role/theme/reflow/keyboard/state matrix covered or honestly `not_runnable`.
8. Security benchmark green and current; control-matrix/benchmark-doc/test updates committed if any trigger changed.
9. Blind independent architectural/code review passed with findings remediated and re-reviewed until dry (verdicts recorded in CF).
10. Branch protection on `main` matches the §D.4 manifest (API-verified snapshot in the dossier).
11. Promotion dossier complete: candidate story, findings register (all S1/S2 closed or owner-accepted), verification matrix results, CF evidence ids, journey verdicts, security scorecard, mutation report, protection snapshot, main-merge mechanics recommendation.
12. Owner approval still pending — the verdict enables the decision, never executes it.

---

## I. Separation of code stages (transported → live)

| Stage | Where it exists after this plan | Proof object |
|---|---|---|
| transported | working tree before W0 commits | classification manifest |
| committed | Candidate Base SHA → Promotion SHA (local) | git log + tag |
| pushed | `origin/testing` @ Promotion SHA (owner-gated, W7) | `gh run list --commit` |
| CI-validated | the green required-check run on that SHA | run URL + headSha |
| artifact-built | frontend build + QA containers from that SHA | artifacts + compose digests |
| PR-ready | dossier complete + branch protection aligned | dossier §H snapshot |
| merged | **not part of this plan** — owner's act after READY | merge commit on main |
| deployed/live-verified | out of scope (separate owner-gated operation) | n/a |

---

## J. Residual risks and open questions

1. **Ruff pin choice:** pin must equal the version CI resolves (0.16.6 at run 34039897688); W2 verifies pin == CI resolution, else format results can still drift.
2. **Mutation survivors may expose real bugs** in `runtimeConfig.ts` (origin/websocket URL derivation is auth-adjacent) — W3 treats implementation fixes as first-class outcomes, with tests.
3. **CF-SPEC-29 reconciliation** may surface genuinely unfinished obligations; the plan prefers "new blocking task" over cosmetic closure.
4. **994-commit fast-forward** is a large blast radius for consumers of `main`; the dossier's merge-mechanics section (FF vs `--no-ff`) and a post-merge main CI run are the mitigations; a staged rollout (main → release tag) is possible but owner-chosen.
5. **Local-only verification limits:** the full backend suite (~2,335 tests) and browser journeys were not re-run by this architect (planning-stage constraint); they are mandatory rows in §E and re-run on the Promotion SHA.
6. **Native `impact` migration** may land mid-pipeline; waves should use it when available but must not block on it (manual dependency analysis documented instead).

---

## K. Traceability to the conductor wave manifest

| Conductor manifest id | This plan's waves | Delta rationale |
|---|---|---|
| candidate-boundary | W0 | unchanged in intent; adds classification classes C1–C6, dependency-closure proof, quarantine branch, drift-prevention rules |
| control-plane-lifecycle | W1 | unchanged; adds explicit CF-SPEC-29 task reconciliation and the not_yet_native impact debt record |
| correctness-quality | W2 + W3 | split: mechanical red-check repairs (W2) vs mutation quality + harness repair (W3) for intelligible review/rollback |
| ci-enforcement | W4 + W5 | split: in-repo workflow redesign (W4) vs owner-gated GitHub settings (W5), which the brief itself requires separating |
| browser-spine-acceptance | W6 | unchanged; adds spine-probe and not_runnable honesty requirements |
| promotion-certification | W7 | unchanged in intent; adds blind-review-dry requirement and CI-headSha binding |

*End of Architect C draft.*
