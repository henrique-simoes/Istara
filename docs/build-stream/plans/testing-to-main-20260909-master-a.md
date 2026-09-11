# Master plan A — testing to main convergence

Synthesis round: `b35539f4f7bdabc5be5f`
Status: planning candidate only; implementation and promotion require owner approval
Target: `testing -> main`

## Executive decision

The repository is **NOT READY** for promotion. The release candidate is not a ref yet: `origin/testing`, local committed `testing`, and the dirty/untracked working tree are three different surfaces. The delivery must first classify and preserve them, then converge lifecycle/control-plane truth, repair correctness and quality, redesign CI enforcement, execute real container-first journeys, and certify one exact SHA. No wave may push, create a PR, merge, mutate repository settings, access secrets, or run live models without separate owner authorization.

## A. Candidate definition

### Measured state

On 2026-09-09 this synthesis measured:

- `HEAD=50c4d493fcd0b9aef8df8277e5c766822f65d0aa`, not the prompt's older `85f64e4d...`; therefore the candidate moved during planning.
- `origin/testing=9961fa3dbd2ce03a6e1d8cc3e303478edaf17a79`; local HEAD is 67 commits ahead and 0 behind.
- `origin/main=fa6a1a391b5a1089690eb8fed5d179ce146ec9e9`; `origin/testing` is 994 commits ahead and 0 behind.
- The tree remains extensively dirty across backend, frontend, tests, workflows/contracts, security evidence, lifecycle documents, plus many untracked files. Counts must be re-measured at W0, never copied from this plan.
- Pinned Compass Forge SHA-256 is `559af310d332ab72ceeb75bdd057b54f43b185ce875b93f7b3943d988b5be2c1`; runtime is Rust-only and reports target `<REPO_ROOT>`, workspace identity `/Users/user/Documents/compass-forge`.
- CF-SPEC-30 is active; CF-SPEC-29 and older tasks require evidence-based reconciliation. The supplied graph output is only a starting map and must not be treated as a complete inventory.

### Reconciliation algorithm

1. Acquire the repository completion lock. Record refs, merge bases, `git status --porcelain=v2 -uall`, staged/unstaged diffs, ignored-path inventory (names only for protected directories), submodules, and worktrees. Do not fetch unless separately authorized; if fetched, preserve pre-fetch refs.
2. Create a recoverable custody bundle outside the candidate: `git bundle` of reachable refs, binary patches for staged/unstaged tracked edits, an untracked-file manifest with size/hash, and a separately permission-restricted archive of only owner-approved untracked files. Prove restoration in a scratch clone before classification. Never copy secrets into release artifacts.
3. Classify every delta relative to `origin/testing` into exactly one bucket: `RELEASE`, `AMBIENT`, `GENERATED/DEPENDENCY`, `SECRET/SENSITIVE`, `DUPLICATE/SUPERSEDED`, or `UNDECIDED`. Record path, owner/initiative, rationale, dependencies, source ref/working-tree state, and intended disposition in a committed candidate manifest.
4. Follow dependency closure for each `RELEASE` file using refreshed CF impact output when valid plus textual/import/config/workflow/test/selector inspection. Record `resolution`, `answer_completeness`, `confidence`, graph source, and freshness. Partial/none answers require manual analysis; never infer “no impact.”
5. Preserve `AMBIENT`, `UNDECIDED`, generated dependencies, secrets, `LLMs/`, and `Model_Finetuning/` in place and outside candidate commits. Do not stash, clean, reset, prune, or overwrite them.
6. Commit only ratified `RELEASE` path sets with explicit pathspecs. After each classification commit, compare manifest to `git diff --name-status origin/testing...HEAD`; unexplained paths fail the wave.
7. Freeze `Candidate Base SHA` only after the manifest is complete, the custody restore test passes, release-scope changes are committed, and remaining dirty files map exclusively to non-release buckets. Record the SHA, manifest hash, refs, custody bundle checksum/location, and protected-directory inventory in CF evidence and the lifecycle.

### Drift prevention and rollback

- Every later wave starts by asserting `git rev-parse <expected predecessor>` and ends by recording its new SHA and explicit path delta. An unexpected ref/tree change halts the run and returns to W0 classification.
- No amendment, rebase, squash, force push, or history rewrite after freeze. Corrections are additive commits and a new recorded candidate SHA.
- Roll back a wave with a targeted revert of that wave's commits; never restore the whole dirty tree over ambient work. A wrongly excluded file remains preserved for a later owner decision. A wrongly included file is removed by an explicit revert and reclassification.
- Distinguish transported, committed, pushed, CI-validated, artifact-built, PR-ready, merged, and live-verified states in every status report.

## B. Findings register

| ID | Sev | Surface | Evidence / root cause | Consequence | Correction and verification | Wave | Disposition |
|---|---|---|---|---|---|---|---|
| F-01 | S1 | Candidate custody | No immutable ref contains all work; HEAD changed after the supplied review | Green claims cannot bind to a stable object; ambient loss/inclusion risk | Classification manifest, tested custody bundle, Candidate Base SHA, drift assertions | W0 | blocking |
| F-02 | S1 | Backend formatting | CI and local checks report Ruff formatting drift; formatter floor permits version variance | CI red and tests masked | Pin formatter; format only classified release files; `ruff format --check` | W2 | blocking |
| F-03 | S1 | Backend correctness lint | Global Ruff is advisory while changed-file lint is blocking; F821 can escape | Runtime defects can retain green required status | Make correctness classes globally blocking immediately; burn down remaining lint without advisory promotion gaps | W2/W4 | blocking |
| F-04 | S1 | Backend tests/public quality | Full suite has one public-quality failure from machine-local terminology in tracked docs | Candidate red and public metadata leakage | Replace machine-specific wording with portable repo-relative language; sweep; full suite green | W2 | blocking |
| F-05 | S1 | Frontend lint | Empty interface alias in `ChatModelControls.tsx` violates lint | Frontend lane red | Use a type alias or remove redundant alias; lint/type/unit green | W2 | blocking |
| F-06 | S1 | Frontend mutation | Remote score 73.08: 95 killed, 21 survived, 14 no coverage; local runner install broken | Genuine test-strength gap and missing reproducibility | Clean reproducible dependency install, tests/implementation fixes that kill meaningful mutants; threshold never lowered; mutation report green | W3 | blocking |
| F-07 | S2 | Whitespace/release hygiene | `git diff --check origin/main` reports documentation/lifecycle errors | Noisy and non-reproducible release delta | Content-preserving scoped cleanup plus blocking hygiene job | W2/W4 | blocking |
| F-08 | S1 | Lifecycle truth | Multiple recent status blocks contradict ledgers/next actions; several artifacts untracked | “Done” is not durable or resumable | Evidence-based disposition table and append-only corrective entries; track intended artifacts | W1 | blocking |
| F-09 | S1 | CF truth | Open CF-SPEC-29/30 and older task debt; stale/insufficient graph state was reported | Acceptance and impact claims may be false | Refresh/verify index; reconcile each task from evidence; close/cancel nothing by assumption | W1 | blocking |
| F-10 | S1 | CI topology | Formatting/lint precedes broad tests in combined jobs | One failure domain hides others | Independent required jobs with dependencies only for true prerequisites | W4 | blocking |
| F-11 | S1 | Branch protection | Only `governance` required; no approval/codeowner/admin enforcement; force pushes allowed | Red architectural checks may merge | Commit required-context manifest; owner applies and verifies settings separately | W4/W5 | blocking |
| F-12 | S1 | Browser acceptance | QA workflows render/build/contracts but do not execute complete Playwright journeys | UI behavior is unproven | Loopback-only container-first credential-free journey job with artifacts and honest `not_runnable` | W6 | blocking |
| F-13 | S2 | Governance write authority | Governance/badge automation may write directly to main | Bypasses owner-gated promotion path | Remove direct-main write; use read-only check or owner-approved PR workflow | W4 | blocking |
| F-14 | S2 | Desktop | Cargo check is continue-on-error and release status is ambiguous | Desktop regressions may be hidden | Install CI deps and make blocking, or owner explicitly documents non-gating scope; never call advisory green | W4 | owner decision, release blocking until decided |
| F-15 | S1 | Security evidence | Security-sensitive/auth/provider surfaces and control matrix changed | Stale security claim | Run benchmark; update matrix/doc/test iff control/evidence/trigger changed | W2/W7 | blocking |
| F-16 | S1 | Research Spine | Broad research and self-improvement surfaces are in the candidate; static graph can omit dynamic paths | A bypass could become reportable | Per-path spine trace, contract tests, browser probes, independent review; any bypass blocks | W2/W6/W7 | blocking |
| F-17 | S2 | Required-check drift | No durable mapping from workflow contexts to branch protection | Renames can create stale green | Machine-checkable required-context manifest compared with workflow and protection API | W4/W5 | blocking |
| F-18 | S2 | Promotion provenance | No open PR/dossier tied to one SHA | “Ready” cannot be audited | Exact-SHA dossier plus matching GitHub `headSha`, artifacts, CF evidence and review verdicts | W7 | blocking |

## C. Strict sequential wave manifest

Each wave is imported only after its predecessor has converged through implement -> independent comprehensive review -> remediation -> focused delta re-review. Every wave records commands as CF evidence and updates the single lifecycle through the conductor protocol. The owner approval between this plan and W0 is mandatory.

### W0 — Candidate custody and boundary

- **Objective:** preserve all work and freeze one auditable Candidate Base without contaminating it with ambient files.
- **Scope:** Git refs/worktrees/status; tracked/untracked/ignored classification; custody and restore test; manifest. **Excludes:** code fixes, cleanup, deletion, remote writes.
- **Tasks:** execute §A algorithm; resolve every `UNDECIDED` item with the owner or hold; verify dependency closure; commit only ratified paths; freeze SHA.
- **Verification:** `git fsck`; bundle verify and scratch restore; manifest/hash validator; `git diff --name-status origin/testing...CandidateBase`; `git status --porcelain=v2 -uall`; protected directory path/hash inventory unchanged.
- **CF:** gate before/after; candidate-boundary command evidence; classification manifest as artifact evidence.
- **Review questions:** Can every candidate byte be traced? Can every excluded byte be recovered? Did any secret/generated/ambient file enter?
- **Complete when:** restore succeeds, manifest accounts for all paths, one SHA is frozen, no release-scope dirt remains. **Rollback:** discard only the isolated candidate commit(s); custody remains intact. **Risk:** ownership ambiguity blocks.

### W1 — Lifecycle and control-plane reconciliation

- **Objective:** make Build Stream, CF, graph/index, Git, and conductor state agree with the frozen boundary.
- **Scope:** recent lifecycle files; CF-SPEC-29/30 and stale tasks; index refresh/status; manual impact fallback. **Excludes:** product changes and cosmetic task closure.
- **Tasks:** classify every recent plan as included/excluded/superseded/completed/deferred with rationale; add append-only corrections; refresh index with pinned binary; inspect freshness/schema; run impact per candidate surface and manually follow dynamic/config/test seams; reconcile tasks only against cited evidence.
- **Verification:** native `index status`; impact response-field audit; `spec show`, `task list`, `task evidence-list`, `next`; lifecycle parser ensuring status/last/next consistency and tracked intended files.
- **Review questions:** Is any closure based on age rather than evidence? Does `next` identify real remaining work? Is incomplete graph coverage explicit?
- **Complete when:** no contradictory release ledger state, CF-SPEC-29 disposition is evidence-backed, CF-SPEC-30 tasks are mapped to waves, graph limitation is honest. **Rollback:** corrective ledger entries, never edit history. **Risk:** genuinely unfinished old obligations create blocking tasks.

### W2 — Correctness, contracts, security, and hygiene repair

- **Objective:** repair deterministic blocking defects and prove architecture contracts before CI redesign.
- **Scope:** classified release files only: Ruff pin/format/lint, frontend lint, public-quality strings, whitespace, backend/full contract tests, security evidence, Research Spine/self-improvement trace. **Excludes:** mutation campaign and workflow topology.
- **Tasks:** fix root causes; do not mass-format ambient paths; inventory changed research-data and security paths; update docs/tests only when behavior/contract changes; add regression tests before behavioral fixes.
- **Verification:** `ruff format --check`; blocking correctness lint including F821/F811/F822/E999; frontend lint/type/unit; `git diff --check`; public-quality test; full non-live backend suite; governance battery; security benchmark; research-validity, integrity, project-scope and self-improvement contract suites.
- **CF:** impact/test-impact evidence per changed surface; security scorecard; architecture/test-ownership gates.
- **Review questions:** Did formatting change semantics? Are security docs and tests synchronized? Can any candidate/provisional artifact bypass acceptance?
- **Complete when:** all deterministic checks green, security controls current, no unclassified file touched. **Rollback:** revert task commits individually. **Risk:** new correctness findings expand only through new tasks.

### W3 — Mutation quality and reproducible frontend harness

- **Objective:** exceed the unchanged mutation threshold by improving tests or implementation correctness.
- **Scope:** frontend dependency lock/install, Stryker/Vitest integration, mutated source and owned tests. **Excludes:** threshold reduction or scope shrinkage.
- **Tasks:** reproduce via clean `npm ci`; capture environment versions; classify all 21 survivors/14 no-coverage mutants; add behavior tests or correct implementation; justify equivalent/invalid mutants explicitly.
- **Verification:** lint/type/unit/build; `npm run test:mutation`; score >=75 (target >=90 where feasible), zero unexplained no-coverage, mutation triple archived.
- **CF:** report artifact and per-mutant disposition evidence.
- **Review questions:** Were mutants killed by meaningful assertions? Was production behavior weakened to satisfy tests? Did mutated scope shrink?
- **Complete when:** local and clean-environment mutation runs agree and threshold is untouched. **Rollback:** revert focused test/implementation commits. **Risk:** runner defect may require a separately reviewed harness task.

### W4 — CI architecture and enforcement in repository

- **Objective:** make every release-critical failure domain execute independently and prevent stale green contexts.
- **Scope:** workflows, scripts, required-context manifest, TESTING.md and TEST_HISTORY topology. **Excludes:** GitHub settings mutation.
- **Tasks:** implement §D job graph; remove direct-main writes; pin tool/runtime versions; add artifact retention, required-context validation, fail-closed capability reporting and workflow contract tests.
- **Verification:** workflow syntax/contract/governance scripts; job-graph parser; controlled failure-injection fixture proving backend tests still schedule when format fails; local commands matching every job.
- **CF:** workflow diff, gate results and artifact-schema evidence.
- **Review questions:** Is each required context always emitted on relevant events? Does any `continue-on-error` hide a required check? Are credentials absent from default lane?
- **Complete when:** independent graph is contract-tested and all local equivalents green. **Rollback:** revert workflow commit; old red architecture remains blocking. **Risk:** GitHub job names are external API contracts.

### W5 — Branch-protection alignment (owner operation)

- **Objective:** align external enforcement with the committed context manifest.
- **Scope:** prepare exact settings diff and read-only API verification. **Excludes:** automated settings writes.
- **Tasks:** owner chooses desktop policy and applies required checks, >=1 approval, code-owner review, up-to-date branch, admin enforcement, linear history, no force pushes; record before/after snapshots without secrets.
- **Verification:** read branch protection API; compare exact context names to manifest and latest workflow emissions.
- **CF:** owner-decision and settings-snapshot evidence.
- **Review questions:** Can an admin/force push bypass policy? Does a required context exist on both PR and push paths?
- **Complete when:** API snapshot matches manifest. **Rollback:** owner restores captured settings. **Risk:** external authority may delay delivery; promotion remains blocked.

### W6 — Container-first browser and Research Spine acceptance

- **Objective:** prove changed behavior through real user journeys in the credential-free Docker lane.
- **Scope:** `tests/simulation`, applicable `tests/real_user_benchmark`, scenario registry/coverage matrix, selectors, QA UI profile, TESTING history. **Excludes:** live private providers, donated compute without capability, golden-data mutations.
- **Tasks:** derive affected journeys from W0/W1 trace; navigate/click/fill/upload/send in browser; cover admin/researcher/viewer/stranger when auth-adjacent, light/dark, 375px, keyboard focus, loading/error/empty; use synthetic data; add team/persona, donor/model, and spine probes where applicable.
- **Verification:** loopback-only Compose UI profile and Playwright; dated deterministic verdict JSON, screenshots and HARs; unavailable live capability => explicit `not_runnable`, never pass/skip.
- **CF:** scenario command, verdict summary and artifact paths.
- **Review questions:** Is any API call mislabeled as browser evidence? Are provisional artifacts prevented from reporting? Are all matrix cells covered or explicit?
- **Complete when:** all credential-free required journeys pass on the candidate SHA, coverage registry and history agree. **Rollback:** revert scenario/product fixes by task; failures block. **Risk:** flaky selectors are fixed in this wave.

### W7 — Exact-SHA certification and owner pause

- **Objective:** produce one reproducibly green Promotion SHA and a complete dossier, then stop.
- **Scope:** final frozen-SHA rerun, CI on owner-authorized push, blind independent architecture/code review, remediation/delta re-review, dossier. **Excludes:** automatic PR or merge.
- **Tasks:** freeze Promotion SHA; rerun §E; ensure GitHub run `headSha` matches; reconcile all findings/tasks/ledgers; review candidate-vs-`origin/testing` plus wave commits; remediate until dry; document promotion mechanics without executing them.
- **Verification:** all blocking matrix rows; CF latest reviewer verdicts pass; dossier checksum; branch protection snapshot.
- **CF:** final gates, command evidence, review verdicts, spec coverage/drift, task closure. Spec acceptance only after all linked tasks are done.
- **Review questions:** Is any claim from another SHA? Are accepted risks explicit and owner-approved? Is live/deployed behavior being implied?
- **Complete when:** binary READY criteria below hold and owner approval remains pending. **Rollback:** do not promote; add a remediation task/wave. **Risk:** late scope change invalidates SHA and requires recertification.

## D. CI target architecture

### Job and dependency graph

Independent jobs: `feature-obligations`, `governance`, `backend-format`, `backend-lint`, `backend-tests`, `backend-mutation`, `frontend-lint`, `frontend-typecheck`, `frontend-unit`, `frontend-mutation`, `frontend-build`, `test-harness-js`, `qa-contract`, `qa-browser`, `desktop-check`, and `release-hygiene`. No format/lint job is a prerequisite for functional tests. `qa-browser` may consume a built image/artifact and the feature-obligation capability manifest; that is a real dependency, not a scheduling shortcut.

### Policy

- PRs to and pushes on `testing`/`main`: full credential-free matrix. Weekly schedule on both refs detects dependency/runner rot. Required contexts must be emitted on every protected event; path filters cannot silently omit them.
- Required on both protected branches: all jobs above except explicitly owner-designated live-capability jobs; desktop is required by default until an explicit owner decision documents a narrower product contract.
- Full suites run for main promotions and release-branch pushes. Change-scoped browser selection is allowed only for ordinary testing PRs when the registry proves coverage; main PRs and final SHA run the complete release matrix.
- Cache keys include lockfile, runtime and tool versions; jobs do not share mutable dependency directories. Build images/artifacts once when reusable, identify by source SHA/digest, and retain promotion evidence at least 90 days.
- Ruff format is pinned and blocking. Correctness lint classes are globally blocking; broader lint becomes blocking through an explicit debt-burn-down plan, never by hiding findings. `git diff --check` and public-quality are blocking.
- Mutation thresholds remain high/low/break `90/80/75`; scope cannot shrink to pass; reports retain killed/survived/no-coverage counts. Backend mutation remains blocking.
- Default lane is credential-free. Live LLM/provider/donor lanes are manual and fail closed as `not_runnable` with capability reason; they never manufacture a required green context.
- `qa-browser` uses loopback-only Docker Compose and Playwright real acts. Upload screenshots/HAR/verdict/coverage keyed by SHA.
- No required job uses `continue-on-error`. Advisory experiments use unmistakably advisory names and cannot satisfy the required-context manifest.
- Governance is read-only. Badge/version updates go through owner-approved PR mechanics, never direct pushes to main.
- W5 is the only branch-protection change path and is owner-executed; workflow edits alone are not enforcement.

## E. Verification matrix

`B` blocking; `CF` credential-free; `R` rerun on Promotion SHA.

| Claim | Command/journey | Environment | Expected/evidence | B | CF | R |
|---|---|---|---|---|---|---|
| Candidate custody | refs/status/manifest validator; scratch restore | local | exact boundary and successful restoration in CF/dossier | yes | yes | yes |
| Protected artifacts | names/hash inventory of `LLMs/`, `Model_Finetuning/` | local | unchanged | yes | yes | yes |
| Format/lint/hygiene | pinned Ruff checks; ESLint; `git diff --check`; public-quality | clean local + CI | exit 0, job artifacts | yes | yes | yes |
| Backend behavior | full non-live pytest + focused contracts + compile/rehearsal | clean local + CI | zero failures | yes | yes | yes |
| Frontend behavior | typecheck, unit, production build | Node lockfile environment | all green | yes | yes | yes |
| Mutation | frontend Stryker and backend mutation | clean local + CI | thresholds unchanged and met; triple archived | yes | yes | yes |
| Governance | integrity, CI governance, harness, workflow, QA capability, required-context validators | local + CI | all exit 0 | yes | yes | yes |
| Security | `python scripts/security_benchmark.py --fail-on-threshold`; benchmark tests | local + CI | 28/28 baseline or expanded controls green | yes | yes | yes |
| Research Spine | research-validity/integrity/project-scope/self-improvement tests | local + CI | no bypass and gates fail closed | yes | yes | yes |
| Static harness | simulation and real-user static/contract suites | Node CI | baselines preserved or increased | yes | yes | yes |
| QA contracts | Compose profiles render; QA contract/synthetic/audit tests | Docker CI | green, loopback-only | yes | yes | yes |
| Browser UX | registered Playwright journeys and matrix | Docker CI | dated pass or explicit capability-scoped `not_runnable`; artifacts | yes | yes for required lane | yes |
| Desktop | Cargo check with required system deps | CI | blocking green or owner-approved explicit exclusion | yes | yes | yes |
| CF truth | index/status/impact fields; task/spec/evidence/next | pinned native runtime | fresh/explicitly partial; no release blocker | yes | yes | yes |
| Lifecycle truth | status/ledger/disposition validator | local | no contradictory active release record | yes | yes | yes |
| Branch protection | read-only GitHub protection API vs manifest | GitHub | exact match | yes | n/a | yes |
| CI identity | workflow run inspection | GitHub | all required contexts green and `headSha=Promotion SHA` | yes | n/a | yes |
| Blind review | CF reviewer verdicts and finding register | isolated reviewer | latest verdict pass; no open finding | yes | yes | yes |

Live LLM, donor compute, deployment and production soak are not proven by this promotion unless separately authorized and executed; absence is recorded, not converted into a pass.

## F. Research Spine assurance

For every changed ingestion, creation, processing, retrieval, summarization, validation, visualization, routing, promotion or reporting path, W1/W2 construct a trace:

`source span -> evidence unit -> independent model identities and atomic/open coding -> reliability + grounding -> reconciliation -> accepted atom/nugget -> fact -> insight -> recommendation -> In Review -> human-approved Done task -> report`.

The trace must cite schemas, services/routes, authorization, route-evidence handles, tests, and browser journeys. Candidate/provisional artifacts remain provisional; synthesized nugget prose is never substituted for raw source evidence unless exact spans survive and acceptance remains pending. Model independence is proven by distinct identities, not labels. Reports require human review plus Done-task gates.

Self-improvement paths are separately traced: telemetry and raw tool success cannot become report evidence or strong positive promotion signals; ReasoningBank/Memento memory is project-scoped and validated; autoresearch/meta-hyperagent experiments remain sandboxed/provisional; self-evolution requires governed promotion; RAG/GraphRAG/Prompt-RAG preserve evidence handles; LLMLingua cannot compress protected contract/codebook/gate/schema blocks. Any bypass is architecture debt and blocks promotion unless repaired—never an accepted silent exception.

## G. Owner-gated operations

Automated waves must not:

1. reset, clean, stash/drop, prune, rewrite history, delete worktrees, or delete/move local artifacts;
2. touch `LLMs/` or `Model_Finetuning/` beyond passive inventory;
3. start servers, load models, call private providers, or access/print/store secrets and endpoint fingerprints;
4. mutate GitHub settings or branch protection;
5. push, create a promotion PR, force-push, tag remotely, or merge to main;
6. lower mutation, security, quality, accessibility or Research Spine thresholds;
7. close CF tasks/specs or rewrite lifecycle history without evidence.

W5 pauses for owner settings action. W7 pauses for separate authorization before any push/PR and again leaves the main merge to the owner.

## H. Binary final release criteria

Verdict is **READY** only if every item is true; otherwise **NOT READY**:

1. Promotion SHA and Candidate Base SHA are exact and recorded; candidate-scope worktree is clean and every remainder is classified.
2. Custody restore was proven; ambient/user work and protected directories are intact.
3. Every recent Build Stream plan has one durable disposition and no contradictory release status remains.
4. CF index/impact limitations are explicit; CF-SPEC-29/30 and all release-blocking tasks have evidence-backed terminal state; `next` is truthful.
5. All blocking local and CI checks in §E pass on the same Promotion SHA; mutation thresholds are unchanged.
6. Container-first browser verdicts on that SHA cover roles/themes/375px/keyboard/states with deterministic artifacts and honest capability reporting.
7. Research Spine and self-improvement traces show no bypass; security benchmark/evidence is current.
8. Independent blind review passes after all findings are remediated and delta re-reviewed.
9. Main branch protection matches the required-context manifest, verified after owner action.
10. Promotion dossier binds refs, commits, CI `headSha`, artifact digests, CF evidence, review verdicts, security/mutation reports, journey results, risks, and recommended merge mechanics.
11. No PR has been created and no merge/deployment/live verification is claimed. Owner approval is still pending.

## I. Coverage matrix across frozen source drafts

| Master section | Draft A contribution | Draft B contribution | Draft C contribution |
|---|---|---|---|
| Candidate custody | W0 custody/Candidate D, explicit promotion pause | Five/six-bucket classification, restore bundle, freeze invariants, moving-surface finding | Candidate Base/Promotion SHA and drift checks |
| Control-plane truth | Separate lifecycle/CF reconciliation and architecture inventory | Corrected CF diagnosis, large task-debt evidence, plan-file tracking risk | Native-field honesty, CF-SPEC-29/30 mapping |
| Correctness/quality | Dedicated architecture inventory then repair | Specific F821, public-quality, hash/freeze, security, desktop and governance-write findings | Ruff pin, mutation triple/no-coverage and split W2/W3 |
| CI enforcement | Independent job graph plus separate external protection wave | Required contexts, event behavior, cache/retention, hollow mutation and browser findings | Required-context manifest, no stale green, direct-main write removal |
| UI/spine acceptance | Full role/theme/reflow/focus/state contract | Container browser job, explicit self-improvement assurance | Loopback QA, registry/persona/donor probes, deterministic evidence |
| Certification | Separate frozen-SHA certification and owner-gated proposal | Binary criteria, exact command matrix and blind dry review | Promotion dossier, headSha binding and transported-to-live distinctions |

Conflict resolutions:

- Draft A's nine-wave clarity and B's six-wave compactness are reconciled into eight waves: mutation is separated from mechanical repair; external branch protection remains separate; PR proposal is not an executable wave because authorization is outside this plan.
- Draft B's measured corrections supersede stale prompt claims where current read-only evidence differs, while every mutable count is deliberately re-measured in W0.
- Draft C's suggestion that unavailable native impact should not halt all work is retained only with fail-closed disclosure and documented manual dependency traversal; no invented graph evidence is allowed.
- Desktop defaults to blocking because ambiguity cannot yield READY; the owner may explicitly narrow the release contract, but an advisory green is never represented as desktop validation.

## J. Residual risks

- The candidate is moving while planning; W0 must re-measure everything and any drift returns to classification.
- The release delta from main is exceptionally large. Final review uses both the full architecture/contract matrix and the smaller `origin/testing..Promotion SHA` wave delta; neither alone is sufficient.
- Old CF tasks may represent real unfinished obligations. Evidence-based reconciliation may add waves rather than close debt.
- Mutation survivors may expose production bugs, not merely missing tests.
- GitHub settings and CI retention depend on owner/repository authority; until verified, promotion stays blocked.
- Credential-free UI coverage cannot establish live-provider, donor, deployment or production behavior.

*End of master-plan candidate A. No implementation or lifecycle-plan mutation was performed by this synthesis stage.*
