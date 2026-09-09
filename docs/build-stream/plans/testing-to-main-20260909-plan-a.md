# Architect A — testing-to-main convergence plan

Plan slot: `a`  
Task: `testing-to-main-20260909-PLAN-A`  
Spec: `CF-SPEC-30`  
Prepared: 2026-09-09  
Disposition: independent S1 draft; no implementation or promotion authorization

## Executive decision

Do not promote any of the three present surfaces. Build a fourth surface, Candidate D, by inventorying and classifying every delta, then applying only explicitly included units in sequential, reviewable waves. Candidate D becomes immutable only after source repair, control-plane reconciliation, CI redesign, container-first acceptance, and independent review converge. The promotion PR and merge remain separate owner-gated operations.

The release invariant is: every claim, command, artifact, and GitHub check names the same full 40-character candidate SHA. Any source change after the freeze invalidates certification and returns the stream to the affected wave; evidence is never silently carried forward.

## A. Candidate definition

### Measured state

Measured read-only on 2026-09-09 from `/Users/user/Documents/Istara-main`:

| Surface | Exact state | Meaning |
|---|---|---|
| A | `origin/testing` = `9961fa3dbd2ce03a6e1d8cc3e303478edaf17a79` | Pushed surface. It is 994 commits ahead of and 0 behind `origin/main`. GitHub run 34039897688 on this SHA failed backend and frontend. |
| B | local `testing` HEAD = `85f64e4d25467b7e95ca4f0fb033f4039adbf59e` | Committed surface, 64 commits ahead of and 0 behind A. Not the complete local candidate. |
| C | B plus worktree/index | 155 tracked paths changed; 4,712 insertions and 977 deletions relative to HEAD; 119 untracked leaf files (44 porcelain entries); untracked leaves group under `tests/`, `docs/`, and `frontend/`. | Mutable mixed-ownership surface; not releasable or safe to bulk-stage. |
| Main | `origin/main` = merge base `fa6a1a391b5a1089690eb8fed5d179ce146ec9e9` | Main has none of A's 994 commits. Historic main green runs do not test A/B/C. |

The full `origin/main..C` stat is approximately 1,400 files, 264,900 insertions, and 14,976 deletions. `git diff --check origin/main` currently reports whitespace errors. Ruff format reports 15 backend files requiring format. The focused public-quality test fails with two forbidden-phrase findings even though a literal `rg` does not see the token; the audit implementation and generated/normalized inputs therefore require diagnosis. Current frontend lint reports 233 errors and 82 warnings, so the defect is materially wider than the previously reported empty-interface error. The pushed SHA's GitHub run is conclusively red.

Compass Forge status agrees with the asserted target/workspace identity. Its latest index row was created at `2026-09-09T14:43:51Z`, indexed 941 files, reports `index_version: 12`, and cannot satisfy the required schema-21 graph contract. Treat every graph-derived hint in the work order as a non-authoritative starting point until a schema-21 refresh proves `graph_usable=true` and freshness.

Lifecycle state is contradictory: the Pi capability ledger is at S3 with L-41 while its next action still dispatches implementation; long-horizon work remains S1/in progress; benchmark modernization says S0/in progress/owner-blocked while its next action says Done; systemwide audit is Done with accepted risk and deferred live matrices. These are release inputs, not proof of completion.

### Reconciliation algorithm

1. Acquire the conductor repository completion lock. Capture a tamper-evident inventory bundle under a gitignored release-evidence directory: `git status --porcelain=v2 -z`, `git diff --binary HEAD`, `git diff --cached --binary HEAD`, `git ls-files --others --exclude-standard -z`, file hashes, modes, symlink targets, refs, merge bases, submodules, ignored-file summary, and CF state backup. Hash the manifest. Never include secret values or protected model contents.
2. Create recoverable Git objects without altering the shared worktree: archive the tracked patch and untracked files to an owner-readable, non-repository backup; verify archive hashes and restore into a temporary directory. Do not stash as the sole backup. Never enumerate contents of `LLMs/` or `Model_Finetuning/` beyond confirming they remain ignored and untouched.
3. Partition all deltas into immutable units: A→B commits; B→tracked worktree hunks; untracked leaf files; generated artifacts; local/runtime evidence; and ambiguous ambient edits. Record path, owner/provenance where knowable, related lifecycle/CF task, intended disposition, dependencies, and hash. A directory-level `??` entry is expanded to leaf files.
4. For each A→B commit, use patch-id, tree comparison, lifecycle marker, CF evidence, and tests to classify `include`, `exclude`, `superseded`, `split`, or `needs-owner-attribution`. Do not equate “committed” with “intended for release.”
5. For dirty tracked files, classify at hunk granularity. If one file contains release and ambient edits, reproduce the release unit in an isolated candidate worktree rather than editing or staging the shared file. Untracked generated outputs must be reproducibly regenerated from an included source before inclusion; otherwise exclude them from Candidate D while preserving the backup.
6. Build Candidate D in a new isolated worktree/branch rooted at exact B only after inventory freeze. Apply included units using cherry-picks or path/hunk patches whose hashes match the manifest. Record every exclusion and ambiguity. No `git add -A`, `git clean`, reset, checkout-overwrite, stash-pop, or deletion is allowed.
7. Compare D against the inventory: all included units present exactly once; every excluded/ambient unit still exists in the shared worktree or verified archive; no unexpected path; no secret/private endpoint; protected folders untouched. An independent reviewer signs this comparison.
8. After waves W0–W7 converge, create the immutable release commit and tag-like evidence label (not a pushed Git tag unless authorized). Set `CANDIDATE_SHA=$(git rev-parse HEAD)` and write it into the dossier, CF evidence payloads, artifact names, test summaries, and PR template. Freeze only when `git status --porcelain` is empty in the candidate worktree.
9. Any post-freeze source/config/test/documentation change creates a new SHA and invalidates all SHA-sensitive results. Classify the change, reopen the earliest affected wave, rerun its downstream matrix, and issue a superseding dossier. External branch-protection changes do not alter the SHA but require fresh settings evidence.

### Recovery and rollback

- Before any state mutation: verified Git bundle/patch/untracked archive, CF `state backup`, refs file, and GitHub settings snapshot.
- Each wave is one or more small conventional commits and can be reverted in Candidate D without touching the shared worktree.
- If reconciliation is wrong, discard only the isolated candidate worktree after verifying the shared tree and backup hashes; recreate D from B and the inclusion manifest.
- If CF refresh fails, restore CF state only from the verified native backup and keep promotion blocked; never use Python fallback.
- No rollback may use `git reset --hard`, `git clean`, broad checkout, or delete protected/local artifact directories.

## B. Findings register

| ID | Sev | Surface | Evidence / root cause | Consequence | Correction and verification | Wave | Disposition |
|---|---|---|---|---|---|---|---|
| A-F01 | Blocker | Candidate custody | Three different source surfaces; 155 tracked changes and 119 untracked leaves lack one provenance boundary. | Loss or accidental release of ambient work; irreproducible evidence. | Inventory, verified backup, hunk-level disposition, isolated D, independent manifest comparison. | W0 | blocking |
| A-F02 | Blocker | Remote CI | Run 34039897688 failed backend and frontend on A. | Pushed testing is not promotable. | Repair on D; run all independent jobs on D SHA. | W3–W7 | blocking |
| A-F03 | Major | Backend format | `ruff format --check .`: 15 files would be reformatted. Formatting is ordered before broad pytest in one job. | CI stops early and hides functional signal. | Mechanical formatting only after candidate classification; split format from tests; verify diff and full tests independently. | W3/W4 | blocking |
| A-F04 | Blocker | Frontend quality | Current lint: 233 errors, 82 warnings; remote mutation score 73.08 < 75 with 21 survived and 14 no-coverage. | More than one known lint defect; mutation quality below policy. | Baseline by rule/file, correct code or add behavior tests for each relevant survivor, never lower threshold; clean install and rerun. | W3 | blocking |
| A-F05 | Major | Public quality | Focused audit currently fails with two forbidden-phrase findings although literal search is empty. | Full backend suite remains red; scanner/input discrepancy could recur. | Trace audit inputs/normalization, remove public machine-specific content at source, add regression fixtures, rerun focused and full suite. | W2/W3 | blocking |
| A-F06 | Major | Release hygiene | `git diff --check origin/main` reports trailing whitespace/blank EOF across lifecycle/docs. | Patch cannot satisfy clean-release gate. | Path-scoped whitespace cleanup only for included files; preserve meaningful Markdown breaks; `git diff --check <base>...HEAD`. | W2/W3 | blocking |
| A-F07 | Blocker | Lifecycle truth | Active/Done/status/next-action contradictions and untracked ledgers. | Agents may dispatch completed work or certify unfinished work. | Reconcile each recent lifecycle against Git+CF+evidence; append corrective entries, never rewrite ledger history. | W1 | blocking |
| A-F08 | Blocker | CF authority | CF-SPEC-29 linkage/state unresolved; latest index schema 12 vs required 21. | Impact/task closure claims are incomplete and potentially false. | Native state backup; schema-21 refresh; read resolution/completeness/confidence/source/freshness; reconcile every linked task and stale session. | W1 | blocking |
| A-F09 | Blocker | Branch protection | Live API: only `governance` required; 0 approvals; no code-owner review; admins unenforced; force pushes allowed. | Red architectural checks can be merged. | Owner applies verified settings after workflow stabilizes: required checks, strict update, review/code-owner policy, admin enforcement, force-push denial. | W5 | owner-gated/blocking |
| A-F10 | Major | CI observability | Serial backend/frontend mega-jobs short-circuit; full Ruff and Cargo are advisory. | Green/red status is incomplete and root causes are hidden. | Independent jobs with stable unique contexts and aggregator; define full vs changed scope and desktop policy. | W4 | blocking |
| A-F11 | Blocker | UI acceptance | CI validates static/contracts/Compose render, not full container-first browser journeys. Existing records include deferred/not-runnable lanes. | A healthy workflow/artifact does not prove user behavior. | Run deterministic credential-free Docker UI matrix with browser actions, roles/themes/mobile/keyboard/states, HAR/screenshots; honest capability results. | W6 | blocking |
| A-F12 | Blocker | Research validity | Huge candidate touches research, routing, donor, reporting, and self-improvement surfaces; stale graph cannot enumerate paths. | A bypass could promote provisional/synthetic output to reports. | After graph repair, trace each changed path manually and execute fail-closed spine/governance probes. Any bypass blocks promotion. | W2/W6 | blocking |
| A-F13 | Blocker | Security | Candidate touches auth/WebAuthn/connections/providers/autoresearch/evolution/memory. | Security evidence may be stale relative to D. | Threat-model deltas; update control evidence when triggers change; run 28/28 benchmark plus focused auth/session/provider tests on final SHA. | W3/W7 | blocking |
| A-F14 | Major | Dependency/tooling | Local frontend mutation runner cannot initialize from current `node_modules`. | Local failure is ambiguous; cannot substitute for real remote threshold failure. | Clean lockfile-faithful install in isolated environment, record Node/npm/lock hashes, reproduce mutation outcome; treat bootstrap and score as separate gates. | W3 | blocking |
| A-F15 | Major | Release artifacts | QA artifact workflow builds but does not prove journeys; no open promotion PR. | Artifact existence can be mistaken for readiness. | Build after source gates, bind SBOM/checksums/manifests/UI verdict to SHA, inspect downloads, then owner-authorized PR only. | W7/W8 | blocking |
| A-F16 | Major | Residual/deferred work | F-007 accepted risk and deferred Docker/Playwright matrices coexist with “Done”; long-horizon work remains open. | Scope may be silently swept into promotion or omitted. | Explicit include/exclude/defer decision with rationale and release impact; Blocker/Major risk cannot be deferred without owner changing acceptance. | W1 | blocking until classified |

## C. Strict-wave manifest

All waves are sequential. Each wave begins with a CF before-gate/work order and ends with command evidence, independent review, after-gate, ledger entry, and commit. Reviewer findings become separate remediation tasks and delta re-reviews. The implementation stream pauses for owner approval before W0 and again before outward operations in W5/W8.

### W0 — Custody, backup, and Candidate D assembly

- **Objective:** preserve every local byte and establish an explicit release boundary.
- **Inputs:** A/B/C refs and worktree, CF backup capability, current lifecycle inventory.
- **Scope/tasks:** verified archive; refs/status/diff/hash manifests; hunk-level dispositions; isolated candidate worktree; apply included units; secret/generated/ignored classification; ownership signoff.
- **Exclusions:** product fixes, formatting, lifecycle truth changes, cleanup, pushing.
- **Dependencies:** owner approves master plan; repository lock available.
- **Verification:** `git fsck --full`; `git bundle verify <bundle>` if bundle used; archive checksum and test restore; `git status --porcelain=v2`; `git diff --binary`; manifest reconciliation script; `git check-ignore LLMs Model_Finetuning`.
- **CF evidence/gates:** state backup receipt; before/after architecture and test-ownership gates; command rows with manifest hash; candidate-disposition evidence.
- **Review questions:** Can every byte be recovered? Does each included hunk have provenance? Is any ambient/generated/private item included? Are protected directories untouched?
- **Complete when:** D is clean, all units disposed, backup restore sampled successfully, independent custody review passes.
- **Rollback:** delete only the explicit isolated worktree registration/path after verification; recreate from B.
- **Residual risk:** provenance ambiguity requires exclusion or owner attribution, never assumption.

### W1 — Lifecycle and Compass Forge control-plane reconciliation

- **Objective:** make Git, Build Stream, CF, and conductor state agree without falsifying history.
- **Inputs:** D manifest, CF-SPEC-19/20/21/24/29/30, recent lifecycle ledgers, active sessions/tasks/evidence.
- **Scope/tasks:** native CF backup; deliberate index refresh to schema 21; prove graph usability/freshness; enumerate every open/stale task/spec/session; map to commit and command evidence; close only with evidence, supersede explicitly, split remaining work; append corrective lifecycle entries/status projections; classify all September 7–9 artifacts included/excluded/superseded/deferred.
- **Exclusions:** invented impact, retroactive ledger edits, administrative closure by title, code repair.
- **Dependencies:** W0.
- **Verification:** pinned-binary `status`, `index status`, `spec show`, `task list/show/evidence-list/events`, `actor sessions`; impact calls whose `resolution.inputs=resolved`, `answer_completeness=complete`, confidence is non-none, graph source/freshness is current; lifecycle invariant checker plus manual last-ledger comparison.
- **Review questions:** Does every status block project its last ledger? Is each closure supported by exact source/test evidence? Did refreshed graph omit dynamic routes requiring textual follow-up?
- **Complete when:** graph usable/current; no unexplained open release task; contradictions corrected append-only; next points to this stream.
- **Rollback:** restore native CF backup; revert only W1 corrective projections while retaining ledger correction history through a new entry.
- **Residual risk:** older tasks may be stale, but remain open until proven.

### W2 — Architecture inventory and release obligations

- **Objective:** convert D's changed-file manifest into a complete dependency, security, documentation, and user-journey obligation map.
- **Inputs:** fresh CF impact output, D path list, architecture contracts, route registries, workflow/test registries.
- **Scope/tasks:** CF impact per cohesive surface; record resolution/completeness/confidence/source/freshness; manual textual sweep for dynamic dispatch/string registries; map each changed behavior to owning tests/docs/scenarios/security triggers; trace research and self-improvement paths; diagnose public-quality scanner; disposition accepted/deferred risks.
- **Exclusions:** broad implementation and live probes.
- **Dependencies:** W1.
- **Verification:** CF impact/test-impact/related plus `rg` class/route/event/schema searches; `python scripts/check_change_obligations.py --base <base> --head HEAD`; public-quality focused test; coverage-map validation.
- **Review questions:** Are graph limitations explicit? Does every changed behavior have a real user journey? Is any research path parallel to the spine?
- **Complete when:** signed obligation matrix has no unowned changed path; bypasses are tasks or promotion blockers.
- **Rollback:** revert matrix commit; no source behavior changed.
- **Residual risk:** runtime-composed dependencies require reviewer sampling.

### W3 — Source, test, mutation, and hygiene repair

- **Objective:** repair all known deterministic failures at root cause on D.
- **Inputs:** W2 matrix, remote mutation report/artifacts, current lint/format/test outputs.
- **Scope/tasks:** fix frontend errors by rule/root cause; add tests or correct implementation for survived/no-coverage mutants; clean-install mutation runner; format only included backend files; repair Ruff correctness findings (especially F821) and decide a zero-undefined-name blocking policy; fix public-quality source/scanner; whitespace cleanup; security-control updates if triggered.
- **Exclusions:** lowering thresholds, blanket unsafe auto-fix, advisory conversion, unrelated warning sweep, live provider execution.
- **Dependencies:** W2.
- **Verification:** `ruff format --check .`; changed-file and defined release-critical Ruff gates; full Ruff result recorded; `pytest ../tests/ -v --tb=short -m 'not live_llm'`; focused public-quality; frontend `npm ci`, lint, typecheck, unit, mutation >=75 with zero relevant no-coverage escape, build; backend mutation; integrity/governance/harness/workflow/QA/security scripts; `git diff --check <base>...HEAD`.
- **Review questions:** Did tests kill mutants through behavior rather than implementation coupling? Are format-only diffs separated? Can undefined names escape changed-file selection?
- **Complete when:** all blocking commands pass; full results and remaining warnings are explicitly disposed; 28/28 security benchmark where applicable.
- **Rollback:** revert focused repair commits; restore lockfile only if intentionally changed and verified.
- **Residual risk:** broad legacy lint debt must be either eliminated for D or governed by a release-critical policy that cannot hide correctness defects.

### W4 — CI architecture redesign

- **Objective:** make independent failure domains execute and publish honest stable checks.
- **Inputs:** W3 green commands, branch policies, workflow contract tests.
- **Scope/tasks:** split backend format, lint, tests, mutation, rehearsal/security; split frontend lint, type, unit, mutation, build; independent governance, feature obligations, harness, QA contract, container UI, desktop; add a final `release-gate` aggregator using `if: always()` that fails if any required producer failed/skipped unexpectedly; upload machine-readable summaries.
- **Exclusions:** repository-settings mutations, threshold reductions, writeback from validation jobs.
- **Dependencies:** W3.
- **Verification:** workflow syntax/contract/governance checks; actionlint if repository-pinned; event matrix dry-run; GitHub run on D proving multiple intentional failures all report in a temporary validation branch, followed by clean rerun.
- **Review questions:** Can format hide pytest? Can advisory lint hide F821? Can canceled/skipped jobs yield a misleading green aggregator? Are contexts unique and stable?
- **Complete when:** all domains run independently, aggregator is fail-closed, artifacts identify SHA, clean D run green.
- **Rollback:** revert workflow commit; retain old contexts required until replacement contexts exist.
- **Residual risk:** GitHub context renames must be sequenced with protection to avoid unmergeable or unprotected gaps.

### W5 — Branch-protection alignment (owner-gated external operation)

- **Objective:** align testing/main merge policy with W4 architecture.
- **Inputs:** successful W4 checks and exact context names, settings backup.
- **Scope/tasks:** prepare declarative settings diff; owner applies or separately authorizes API mutation; require release-gate or the complete stable context set on both relevant branches; strict up-to-date branch; at least one independent approval and code-owner review where CODEOWNERS applies; dismiss stale approval/last-push approval; enforce admins; disallow force pushes/deletions.
- **Exclusions:** agent mutation without owner authority, merge, PR creation.
- **Dependencies:** W4 contexts observed on GitHub.
- **Verification:** read-back REST/GraphQL settings; negative test with a controlled draft PR/check failure; screenshot/JSON evidence excluding tokens.
- **Review questions:** Is any release-critical job absent? Can admins/force pushes bypass? Do old contexts create stale-green ambiguity?
- **Complete when:** read-back exactly matches policy and negative test blocks merge.
- **Rollback:** owner reapplies captured prior settings, but promotion remains blocked until protective policy is restored.
- **Residual risk:** GitHub plan/app permissions may constrain settings; report blocked rather than weaken policy.

### W6 — Credential-free container-first browser acceptance

- **Objective:** prove changed behavior as users experience it while preserving live-model safety.
- **Inputs:** W2 journey matrix, D containers, synthetic fixtures.
- **Scope/tasks:** run loopback-only `docker-compose.qa.yml` UI profile; actual navigation/click/fill/upload/send; admin/researcher/viewer/stranger for auth-adjacent changes; light/dark; 375px; keyboard Tab/focus; loading/error/empty; research-spine/team/donor probes where affected; deterministic screenshot/HAR/console/network evidence; update registry, coverage matrix, `TESTING.md`, `testing/TEST_HISTORY.md` when topology/behavior changes.
- **Exclusions:** golden data mutation, private providers, chat completion/model loading, secrets, API-only steps mislabeled as UI.
- **Dependencies:** W3 and W4 local workflow design.
- **Verification:** Compose render then isolated up/health; registered Playwright scenario batches; real-user benchmark UI/persona layer; console/network assertion; loopback port inspection; deterministic teardown. Missing live capability returns blocking/nonblocking `not_runnable` exactly as declared, never skip/pass.
- **Review questions:** Did each claim arise from browser acts? Are role and responsive/a11y states covered? Are source spans/provisional states visible and report gating enforced?
- **Complete when:** credential-free required matrix passes with dated artifacts; every unavailable live lane has an honest capability record and correct disposition.
- **Rollback:** tear down only named QA project/volumes with synthetic data; retain evidence; never touch golden or protected data.
- **Residual risk:** explicitly owner-authorized live acceptance may remain not_runnable, but any release criterion requiring it keeps promotion blocked.

### W7 — Frozen-SHA certification and blind convergence

- **Objective:** freeze one SHA and independently re-prove every release claim.
- **Inputs:** green W0–W6 commits and settings read-back.
- **Scope/tasks:** freeze SHA; clean worktree proof; run full final matrix from clean clones/containers; build artifacts/SBOM/checksums/manifests; independent blind plan/code/security/architecture review; remediation tasks and delta re-review until no Blocker/Major; reconcile CF tasks/specs and ledgers; assemble dossier.
- **Exclusions:** source changes without invalidating freeze; automatic PR/merge; live provider calls without authorization.
- **Dependencies:** W0–W6.
- **Verification:** complete Section E matrix on exact SHA; CF after-gates `architecture_drift` and `test_ownership`; spec coverage/drift; artifact download and checksum inspection; review verdict evidence.
- **Review questions:** Can a reviewer reproduce results without implementer claims? Is every artifact built from SHA? Does any unverified claim appear as confirmed?
- **Complete when:** no open release-blocking finding/task/spec; every required job green on SHA; dossier internally consistent; binary verdict `PR-ready, owner approval pending`.
- **Rollback:** unfreeze, record invalidation reason, reopen earliest affected wave, issue a new SHA/dossier.
- **Residual risk:** only explicitly enumerated accepted Minor risks; no accepted Blocker/Major.

### W8 — Owner-gated promotion proposal

- **Objective:** expose the certified candidate for human decision without merging it.
- **Inputs:** W7 dossier and owner authorization to create/push/PR.
- **Scope/tasks:** push exact candidate ref; verify remote SHA; create PR testing→main only if separately authorized; attach dossier/checks; require fresh green protected checks and approvals.
- **Exclusions:** merge, force push, admin bypass, deployment.
- **Dependencies:** owner authorization plus W7 and W5.
- **Verification:** remote ref equals dossier SHA; PR base/head exact; checks and protection read-back; no auto-merge.
- **Review questions:** Is transported/pushed/CI/artifact/PR-ready state labeled distinctly? Is merge still disabled?
- **Complete when:** PR is ready for owner decision, or package is handed off locally if PR creation is not authorized.
- **Rollback:** close draft PR/delete only the newly authorized remote candidate branch; retain dossier and local commits.
- **Residual risk:** merge and deployment remain unverified future states.

## D. CI target architecture

### Job graph

`classify-changes` emits a signed path/obligation matrix. The following jobs depend only on checkout/setup or classification and run in parallel: `governance`, `public-quality`, `backend-format`, `backend-lint`, `backend-tests`, `backend-mutation`, `backend-rehearsal`, `security`, `frontend-lint`, `frontend-typecheck`, `frontend-unit`, `frontend-mutation`, `frontend-build`, `harness-python`, `harness-js`, `desktop-check`, and `qa-contract`.

`container-ui` depends on successful image builds plus `qa-contract`, not on unrelated format/lint jobs. `artifact-build` depends on all source/build/test/security gates and produces SHA-bound immutable outputs. `release-gate` depends on every required job with `if: always()` and fails on failure, cancellation, or unexplained skip. It never trusts a previous run or branch-level status.

### Policy

- **Required on testing PRs and main PRs:** feature obligations, governance/integrity, public quality, backend format/lint/tests/mutation/rehearsal, frontend lint/type/unit/mutation/build, harness suites, security, QA contract, credential-free container UI, desktop (after policy resolved), artifact cleanliness, and final release-gate. Prefer requiring one fail-closed aggregator plus protecting its workflow file with CODEOWNERS; retain granular contexts for diagnosis.
- **Push:** run the full required matrix on `testing` and `main`; no source-mutating writeback in validation. Scheduled runs exercise extended mutation, dependency/security, platform/desktop, and non-secret capability discovery, but cannot replace PR/SHA gates.
- **Change-scoped:** may accelerate PR feedback only after fail-closed classification. Security/research/CI/harness/shared-runtime changes trigger full affected suites. Final frozen SHA always runs full matrix.
- **Formatting/lint:** separate jobs. Formatting blocking. Changed-file lint blocking for all enabled rules, plus repository-wide release-critical correctness rules such as F821 blocking; full lint debt cannot be hidden under a green required context.
- **Mutation:** threshold stays >=75; no threshold/config exclusion changes without owner-approved methodology change. Survived and no-coverage mutants require disposition. Run on relevant PR changes and always on frozen SHA; upload raw report.
- **Caches:** keyed by OS, runtime version, lockfile hash, and tool config; never cache workspaces/results. Artifact boundaries separate test reports, mutation, security, browser evidence, and release binaries. Every artifact embeds SHA and retention policy; release dossier artifacts receive longer retention.
- **Capabilities:** credential-free lane is required. Live/provider/model lane is manual, owner-authorized, bounded to one configured target, and reports `not_runnable` with reason when capability is absent; it never silently skips or blocks unless release policy explicitly requires that live claim.
- **Container UI:** Compose UI profile on loopback; isolated synthetic project/volumes; real Playwright acts; screenshots, HAR, console/network, accessibility and summary artifacts.
- **Desktop:** first establish a reproducible supported runner matrix. If desktop ships in this release, Cargo check/build is blocking on supported OSes. If not, owner must explicitly exclude desktop from release scope and artifact claims; `continue-on-error` is not an acceptable release status.
- **Stale green prevention:** exact SHA concurrency keys that do not cancel the certification run; aggregator validates producer run IDs/SHA; protections require strict update; artifact attestations bind SHA; no badge/writeback commit changes a certified source branch.
- **External settings:** W5, not `.github/workflows/ci.yml`, changes required contexts, approvals, CODEOWNERS enforcement, admins, and force-push policy.

## E. Verification matrix

`<SHA>` always means the final W7 SHA; all rows marked rerun=yes execute after freeze.

| Claim/surface | Command or journey | Environment | Expected/evidence | Blocking | Credential-free | Rerun |
|---|---|---|---|---|---|---|
| Candidate custody | manifest/hash/restore verifier; `git status --porcelain=v2`; `git diff --check origin/main...<SHA>` | isolated worktree | zero unexplained/dirty/whitespace; custody JSON | yes | yes | yes |
| CF graph | pinned `index status`, impact/test-impact/related per surface | repo root/native Rust | schema 21, usable/current, resolved+complete, non-none confidence; CF JSON | yes | yes | yes |
| Lifecycle/CF closure | lifecycle invariant checker; `spec show`, `task list`, `evidence-list`, `actor sessions` | repo root | no contradiction/open release blocker; CF evidence | yes | yes | yes |
| Backend format/lint | `ruff format --check .`; changed/full correctness lint | clean CI env | zero blocking findings; logs/SARIF | yes | yes | yes |
| Backend behavior | `pytest ../tests/ -v --tb=short -m 'not live_llm'` | backend clean env | pass, declared skips only; JUnit | yes | yes | yes |
| Public quality | focused public audit plus full suite | clean repo clone | no private/machine artifacts; report | yes | yes | yes |
| Backend mutation | `python scripts/run_backend_mutation.py` | clean CI | policy pass; raw results | yes | yes | yes |
| Frontend static/build | `npm ci`; lint; `npx tsc --noEmit`; unit; build | Node 24 clean CI | all pass; logs/JUnit/build manifest | yes | yes | yes |
| Frontend mutation | `npm run test:mutation` | clean Node env | bootstrap succeeds; score >=75; survivors/no-coverage disposed; HTML/JSON | yes | yes | yes |
| Governance/harness | integrity, CI governance, test harness, workflow contracts, QA capabilities, change obligations | clean CI | all pass; command evidence | yes | yes | yes |
| Security | `python scripts/security_benchmark.py --fail-on-threshold --output ...` plus triggered focused tests | clean CI | 28/28, 100%, current matrix/docs/tests | yes | yes | yes |
| Research Spine | research validity, end-to-end, donor routing, synthetic provisionality, report-gate and self-improvement contract tests | clean CI/QA | no bypass; route/model/reconciliation/Done evidence preserved | yes | yes | yes |
| QA contract | Compose contract/synthetic/audit/ui `config --quiet`; QA pytest | Docker CI | render and contract pass; config artifacts | yes | yes | yes |
| Browser UX | registered simulation journeys through UI | loopback Docker+Playwright | role/theme/375px/keyboard/states pass; dated screenshot/HAR/console/network | yes | yes | yes |
| Long-form/team/donor | real-user persona and applicable donor/model probes | isolated QA | pass or policy-correct `not_runnable`; benchmark summary | when affected | mostly | yes |
| Desktop | `cargo check` and supported build/package checks | supported OS matrix | pass or explicit owner exclusion | yes if shipped | yes | yes |
| Artifact | build, SBOM/checksum/manifest, download and inspect | clean release runner | files match SHA and cleanliness policy | yes | yes | yes |
| GitHub policy | API read-back and negative mergeability test | GitHub | exact required contexts, reviews, admins, no force push | yes | n/a | after change |
| Independent review | blind sheet, comprehensive verdict, delta re-reviews | separate reviewer env | PASS; no open Blocker/Major | yes | yes | yes |

Evidence locations: CF command rows on the owning task; SHA-named CI artifacts; `tests/simulation/artifacts/<SHA>/`; `tests/real_user_benchmark/artifacts/<SHA>/`; security scorecard; release dossier under `docs/releases/<SHA>/` or the repository's existing release-evidence convention. Generated runtime evidence should remain gitignored unless the project contract explicitly requires a dated summary in source.

## F. Research Spine assurance

W2 builds a changed-path trace table with columns: ingress source, evidence-unit constructor and exact raw-span handle, independent coder identities and served-model receipts, reliability matrix/metrics, grounding validation, reconciliation decision, accepted atom/nugget transition, facts/insights/recommendations derivation, task In Review/human approval, Done transition, report query/gate, route evidence, project scope, and owning tests/journeys.

Required invariants:

1. Documents, audio/interviews, surveys, channels, chat, integrations, skills, simulations, donated compute, and autoresearch outputs enter as sources/evidence units or remain explicitly non-research/provisional.
2. No synthesized nugget prose substitutes for raw evidence unless its exact original source span is retained and it remains provisional.
3. At least three distinct healthy project-authorized model identities are required for governed multi-model coding; requested/configured model is not served-model proof; replicas are not independent raters.
4. Every coder covers every unit with an exact contiguous quote; incomplete, duplicate, mismatched-model, missing-route, or invalid-metric runs fail closed before promotion.
5. Reliability and grounding precede reconciliation; reconciliation decisions are durable and project scoped.
6. Visible atoms/nuggets/facts/insights/recommendations remain provisional until accepted evidence and human-approved Done state; reports query only accepted/reconciled evidence attached to Done tasks.
7. Donor selection and served-request route evidence survive bridge, Pi frames, dispatcher, and persistence; donor visibility/readiness is not proof of use.
8. Telemetry and ReasoningBank are process signals, not report evidence. Memento learns strong positive signals only from verified/quality/reportable outcomes. Autoresearch remains sandbox/proposal-only; Meta-Hyperagent and Self-Evolution stay project-scoped and governed. RAG/GraphRAG/Prompt-RAG/LLMLingua preserve provenance and protected methodology blocks and cannot relax authorization or report gates.

Each changed row is proven by focused unit/contract tests plus at least one container browser journey showing provisional state and denied premature reporting. Any untraced path, bypass, missing route/model identity, or fail-open legacy fallback is architecture debt and a promotion Blocker; it is repaired in W3/W6 or the release stops.

## G. Owner-gated operations

Automated waves must not:

- clean/reset/discard/overwrite the shared worktree or delete local artifacts;
- delete, move, prune, inspect content from, or clean `LLMs/` and `Model_Finetuning/`;
- access, print, persist, or request secrets, private endpoints, connection strings, or credentials;
- start live servers, send completions, load models, or exercise private providers without explicit permission;
- mutate GitHub branch protection, required checks, repository settings, CODEOWNERS policy, or Actions secrets without a separate owner authorization;
- create a PR, push a branch/tag, merge, force-push, publish an artifact/release, deploy, or claim live verification without separate authorization;
- lower mutation/security/quality/accessibility/Research Spine thresholds or accept a Blocker/Major risk without an explicit owner decision changing acceptance.

The required pauses are: owner approval of the synthesized master plan before W0 implementation; authorization immediately before W5 external settings; authorization before any live-capability lane; authorization before W8 push/PR; and a final human merge decision after all protection and review gates.

## H. Binary final release criteria

The dossier emits exactly one of:

- `NOT READY` — default if any condition below is absent, stale, contradictory, attached to another SHA, skipped without an allowed capability disposition, or failed.
- `PR-READY — OWNER APPROVAL PENDING` — all conditions below pass for one exact SHA. This is not merged, deployed, or live-verified unless separately evidenced.

`PR-READY — OWNER APPROVAL PENDING` requires all of the following:

1. Full 40-character Candidate D SHA; clean isolated worktree; signed inclusion/exclusion manifest; verified ambient-work backup; protected folders untouched.
2. Every intended recent Build Stream artifact classified included/excluded/superseded/completed/deferred with rationale; status blocks agree with last ledgers.
3. CF schema-21 graph current/usable; impact results resolved, complete, and non-none confidence; no open release-blocking task/spec/session; CF-SPEC-30 coverage/drift/gates/evidence complete but acceptance not used to imply merge.
4. Every required CI context green on that exact SHA; no stale/advisory/canceled/skipped escape; mutation threshold met without reduction; formatting/lint/public-quality/tests/build/harness/governance/release hygiene pass.
5. Container-first Playwright matrix passes with real browser acts and deterministic evidence; required live claims either pass under explicit authorization or keep verdict NOT READY; `not_runnable` is never a fabricated pass.
6. Research Spine and self-improvement traces show no bypass across every changed research-data path.
7. Security benchmark is 28/28 at 100% and affected control matrix, benchmark document, and tests are current.
8. Independent blind architectural/code/security review passes after every Blocker/Major is remediated and delta re-reviewed dry.
9. Release artifacts, SBOM, checksums, manifests, and downloaded inspection bind to the same SHA; dossier distinguishes local/committed/pushed/CI-validated/artifact-built/PR-ready/merged/deployed/live-verified states.
10. Branch protection read-back requires the release architecture, approving/code-owner review policy is enforced, admins cannot bypass, and force pushes are disabled.
11. No automatic merge; PR creation and promotion remain pending explicit owner approval.

## Risks and rejected shortcuts

- Bulk-committing C is rejected because it conflates intentional release work with ambient edits.
- Promoting A or B is rejected because A is remotely red and neither contains the classified full candidate.
- Treating current graph hints as impact proof is rejected because index schema is 12.
- Reordering formatting inside the same backend job is insufficient; failure domains must be independent.
- Requiring only `governance` is rejected because it does not represent product architecture.
- Lowering mutation threshold, excluding mutants, making red checks advisory, accepting static simulation as UI proof, or treating artifacts/containers as user acceptance are rejected.
- Administratively closing CF/lifecycles by age or title is rejected; evidence and candidate reachability decide disposition.

## Handoff to synthesis

Preserve this plan's load-bearing ideas during synthesis: Candidate D built from a byte-preserving hunk-level manifest; schema-21 CF repair before impact; append-only lifecycle reconciliation; root-cause repair before CI restructuring; independent failure-domain CI plus fail-closed aggregator; owner-gated branch settings; credential-free container-browser acceptance; final-SHA evidence invalidation; and one binary `PR-READY — OWNER APPROVAL PENDING` verdict.
