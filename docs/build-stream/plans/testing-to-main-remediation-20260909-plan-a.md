# Final testing-to-main readiness remediation — Plan A

Plan slot: `a`  
Planning phase: `draft` (sole architect; no synthesis or vote)  
Compass Forge spec: `CF-SPEC-30`  
Status: `AWAITING-OWNER-APPROVAL`  
Planning input SHA: `fd1c3934b4a7d9bf66389d135e5a95a7de51e44f`  
Target: owner-gated `testing -> main` proposal

## Executive decision

`testing` is **not ready** to be proposed to `main`. The remaining blockers are not a request to rerun already-green suites: browser selection currently proves only 7 of 82 registered scenarios, scenarios 83 and 84 can overstate coverage, no GitHub Actions run exists for the reviewed SHA, live `main` protection is below the committed package, and the lifecycle/certification documents claim more readiness than the evidence supports.

The smallest complete remedy is seven ordered waves after an owner approval gate:

1. reconcile the candidate and existing `CF-SPEC-30` work;
2. repair the browser oracles and role/variant evidence model;
3. make release selection and browser execution fail-closed and container-first;
4. review, verify, and freeze one promotion SHA;
5. obtain CI on that exact SHA;
6. execute isolated exact-SHA Mac Studio browser acceptance;
7. apply and verify branch protection, then make a final owner promotion decision.

No implementation, remote write, container action, live-model probe, repository-setting change, PR, or merge is authorized by this plan. The plan stops here for approval.

## Fixed execution contract

- **Owner gate G0:** no implementation wave may dispatch until the owner approves this frozen plan. Approval records the desktop scope decision as either `blocking` or `out-of-scope-with-no-release-claim`.
- **Routes after approval:** implementation uses Pi `zai/glm-5.3-flash` at its existing `max` effort; fix and code-review stages use Pi `meta/muse-spark-1.3-contributor` at `xhigh`.
- **Per-wave convergence:** implement -> independent comprehensive review -> focused remediation -> delta re-review. The next wave starts only when the prior wave has no open Blocker/Major finding and its exit evidence is attached.
- **Control plane:** extend the existing `CF-SPEC-30` task/evidence spine; do not create a parallel release story. Native Compass Forge state commands run from `<REPO_ROOT>` with the pinned binary and `--target <REPO_ROOT>`; never use a removed workspace flag.
- **Tracked paths:** use `<REPO_ROOT>` and placeholders in committed artifacts. Never record private checkout paths, endpoint fingerprints, credentials, tokens, or connection strings.
- **Local safety:** preserve ambient work and use explicit path lists. Never clean, reset, mass-stage, or touch `LLMs/` or `Model_Finetuning/`.
- **Model safety:** default and release lanes are credential-free. Do not send chat completions or load/probe any live LLM. A genuinely live-only capability stays `not_runnable` with its exact requirement and cannot be relabeled as passed.
- **Remote QA:** Docker, Compose, browser, and live QA execute only on the Mac Studio, in a new exact-SHA checkout, under a unique Docker project, with the browser runner itself containerized. The existing detached/dirty stack is evidence-ineligible and must not be changed, stopped, cleaned, or reused.
- **Ship policy:** retain `ship.auto_pr=false`. Agents do not push, open a PR, merge, bypass protection, or mutate GitHub settings.

## Measured inputs and reuse boundary

The following are historical inputs from the 2026-09-09 review, not fresh evidence produced by this planning stage:

- the pre-plan worktree was clean at `fd1c3934b4a7d9bf66389d135e5a95a7de51e44f`;
- backend: 2,364 passed, 5 skipped, 1 deselected, 5 warnings;
- frontend: typecheck passed, lint had 0 errors/41 warnings, 108 unit tests passed, production build passed;
- simulation static validation: 115 files and 17 tests passed;
- security benchmark: 28/28 at 100%, with auth/security change detection true;
- public-quality, required-check, workflow-contract, CI-governance, harness-integrity, integrity, QA-capability, Ruff format, F821/F811/F822, and `git diff --check` gates passed;
- the reviewed HEAD and frozen certification SHA had no non-document product diff.

Historical evidence may be cited only when its code, oracle, environment, and candidate identity remain unchanged. W1-W3 intentionally change test oracles, selection, runner topology, and tracked readiness documents, so those seams require fresh targeted proof and the final exact-SHA gates. No old green row may be copied into the final dossier as if it were rerun.

## Findings-to-wave map

| Finding | Blocking condition | Closure wave(s) | Required proof |
|---|---|---|---|
| B1 | full browser lane selects 7/82 and records 75 generic `not_runnable`; 82/83/84 never ran | W2, W5 | registry/matrix bijection, fail-closed resolver tests, container browser run, per-variant verdicts, screenshots/HAR |
| B2 | no CI run exists for the reviewed SHA; dossier SHA differs from tip | W3, W4, W6 | one sealed SHA; remote ref, CI `head_sha`, artifacts, QA manifest, and final decision all match |
| B3 | live protection requires only `governance` and lacks review/admin/linear/no-force controls | W6 | pre-read, exact desired PUT body, post-read comparison, red-context negative mergeability proof |
| B4 | scenario 83 contains unconditional and contradictory pass logic | W1 | broken search/filter/catalog states fail deterministically; non-empty and empty/loading/error branches proven |
| B5 | scenario 84 omits roles; bookkeeping is scenario-level; matrix lacks 82/83/84 | W1, W2, W5 | required role/variant cells cannot be hidden by aggregate scenario status |
| B6 | lifecycle/certification overstate readiness; desktop undecided; `CF-SPEC-30` tasks open | G0, W3, W6 | truthful pending status, desktop decision, CF task/evidence reconciliation, no readiness label before convergence |

## Compass Forge reconciliation

`CF-SPEC-30` remains the sole durable spec. Its open tasks are mapped as follows:

| CF task | Meaning | Planned closure |
|---|---|---|
| `CF-402` | validate requested release behavior | W1-W6 acceptance evidence and final owner decision |
| `CF-403` | validate impacted contracts/tests/gates | W0 impact ledger plus per-wave review evidence |
| `CF-404` | implement the requested readiness behavior | W1-W3 code/docs work; W4-W6 external convergence |
| `CF-405` | preserve unrelated behavior/surfaces | explicit path manifests, clean-tree proof, protected-folder checks |
| `CF-406` | record verification before completion | every wave's command/artifact evidence |
| `CF-407` | account for contracts/tests/architecture gates | W0 impact ledger and W1-W3 targeted/broad gates |
| `CF-408` | inspect must-inspect relationships | refreshed per-seam impact plus manual dynamic/config dependency sweep |
| `CF-409` | prove requested behavior | exact-SHA CI, Mac QA, policy, and reviewer evidence |
| `CF-410` | zero incomplete linked tasks at acceptance | final pre-acceptance task/spec audit only |

No task is closed from age, a prior `.done` marker, or historical green output. `CF-SPEC-30` may be accepted only after `CF-402` through `CF-410` are terminal with evidence and the spec coverage/drift plus after-gates pass.

## Dependency and evidence graph

```text
G0 owner approval + desktop decision
  -> W0 candidate/CF reconciliation
  -> W1 deterministic oracles + role/variant schema
  -> W2 release selection + container runner + CI contract
  -> W3 review, full local gates, truthful docs, freeze <PROMOTION_SHA>
  -> G1 owner authorization to push exact SHA
  -> W4 exact-SHA GitHub CI/artifact inspection
  -> G2 owner authorization for isolated Mac Studio QA
  -> W5 exact-SHA remote browser acceptance
  -> G3 owner applies branch protection
  -> W6 policy proof + identity convergence + owner promotion decision
```

The graph is sequential because W1 defines the truth model W2 consumes; W2 defines the executable lane W3 certifies; W3 creates the only identity W4/W5 may test; branch protection cannot require contexts until W4 proves those contexts exist; and promotion cannot be proposed until every independent identity and policy row agrees.

## W0 — Re-measure, impact, and reconcile existing truth

**Owner role:** approved pipeline; implementer gathers read-only state, reviewer validates.  
**Dependencies:** G0.  
**Mutations:** Compass Forge evidence and, only if needed after approval, append-only lifecycle correction; no product code.

### Work

1. Re-measure `HEAD`, worktree cleanliness, `testing`, `origin/testing`, `main`, and merge-base. Compare with planning input `fd1c3934b4a7d9bf66389d135e5a95a7de51e44f`; never silently substitute a moved commit.
2. Record current `CF-SPEC-30`, `CF-402..CF-410`, lifecycle, conductor, and index state. Map every blocker and wave to those tasks.
3. Run Compass Forge impact/context for each proposed changed seam: scenarios 82/83/84, registry/runner, coverage and release-selection data, QA Compose/runner, CI workflow/required-check contract, promotion certification, and lifecycle. Follow imports, dynamic scenario loading, workflow/config consumers, tests, and docs manually where graph coverage is partial or unavailable for JSON/YAML.
4. Produce a changed-path ownership manifest before edits. Treat unrelated discoveries as new tasks, not opportunistic changes.
5. Append a truthful lifecycle transition to approved execution only after G0. Do not edit prior ledger entries.

### Entry / exit / evidence

- **Entry:** owner approval and explicit desktop decision recorded.
- **Exit:** clean or fully classified candidate; input drift either resolved by owner or stopped; every proposed seam has impact completeness/confidence and manual fallback recorded; `CF-402..410` mapped; no parallel spec/lifecycle.
- **Evidence:** Git ref/status commands; pinned CF status/spec/task/index/impact output; path manifest; lifecycle verifier.
- **Stop:** unexpected ref/tree drift, unowned ambient edits, stale CF project identity, partial impact presented as complete, or any request to touch protected model folders.
- **Rollback:** this wave is read-mostly; correct lifecycle mistakes with a new append-only entry and remove only wave-owned uncommitted artifacts by explicit path.

## W1 — Repair browser oracles and role/variant evidence

**Owner role:** implementer `zai/glm-5.3-flash` (`max`); independent reviewer/fixer `meta/muse-spark-1.3-contributor` (`xhigh`).  
**Dependencies:** W0.  
**Primary scope:** `tests/simulation/scenarios/82-quality-dashboard.mjs`, `83-chat-model-controls.mjs`, `84-token-session-lifecycle.mjs`, shared simulation helpers/tests, `tests/simulation/coverage-matrix.json`, and the smallest product seam required to expose an honest state.

### Design

1. Replace scenario 83's unconditional pass with assertions over the post-filter state:
   - a known matching query yields at least one enabled option and the intended model can be selected;
   - a known zero-match query yields the explicit no-results state and no option click is attempted;
   - an empty catalog is reported as empty, never “available”;
   - loading and request failure are distinguishable and fail if the UI gives a false available/success signal.
2. Make fixture/catalog control deterministic. Network interception or setup APIs may create known responses, but those steps must be labeled `API-behind-browser setup`; only real browser navigation, clicks, keyboard input, and visible assertions count as journey evidence. If the product currently swallows a catalog error into an indistinguishable empty state, add the smallest accessible error-state seam and its unit test.
3. Extend scenario 82 to exercise and assert non-empty, loading, error, and empty quality states, not merely theme/reflow/focus.
4. Extend scenario 84 from admin-only to explicit admin/researcher/viewer/stranger variants. Use isolated browser contexts. Create synthetic researcher/viewer accounts through the actual admin UI where possible; any unavoidable provisioning API is labeled setup and excluded from browser-act claims. Stranger begins unauthenticated.
5. Treat 82, 83, and 84 as auth-adjacent. Each receives machine-checkable cells for admin, researcher, viewer, and stranger with an explicit expected outcome based on backend authorization. Each also records light/dark, desktop/375px reflow, keyboard Tab plus visible focus, and relevant loading/error/empty states.
6. Use an obligation model rather than pretending one scenario-level boolean proves every combination. Every required cell has a stable `variant_id`, expectation, result (`pass|fail|not_runnable`), reason/capability when unavailable, and artifact references. A scenario cannot aggregate to pass while a required cell is missing, failed, or invalidly unavailable.
7. Update the tracked coverage matrix with structural mappings for 82/83/84 and correct the empty project-settings/81 mapping. Pre-certification tracked rows may say `pending`; dated runtime verdicts belong in SHA-bound run artifacts, not post-seal commits.

### Acceptance and verification

- A deliberately broken filter, unconditional `passed: true`, missing role cell, missing focus assertion, or empty-catalog mislabel makes a focused test fail.
- 82/83/84 have a declared, complete obligation set; expected denials count only when the expected authorization behavior is actually observed.
- Real journeys use browser acts; setup/API steps are visibly classified.
- Changed auth/session semantics, if any, have backend/frontend ownership tests and trigger the security contract work below.

Planned commands from `<REPO_ROOT>`:

```bash
node --check tests/simulation/scenarios/82-quality-dashboard.mjs
node --check tests/simulation/scenarios/83-chat-model-controls.mjs
node --check tests/simulation/scenarios/84-token-session-lifecycle.mjs
npm --prefix tests/simulation run test:static
npm --prefix frontend run test:unit -- --run src/lib/modelCatalog.test.ts src/stores/authStore.test.ts
npm --prefix frontend run lint
npm --prefix frontend run build
python -m pytest -q tests/test_auth_security.py tests/test_project_rbac.py tests/test_security_benchmark.py
python scripts/security_benchmark.py --fail-on-threshold
```

Add focused Node tests for the new obligation/aggregation module and include their exact paths in command evidence. If W1 changes only scenarios/helpers and no product/security control, do not churn security matrices; still run the tracked benchmark because the scope is auth/session-adjacent. If a control, trigger, or evidence path changes, update `security/control_matrix.json`, `security/SECURITY_BENCHMARK.md`, and `tests/test_security_benchmark.py` together.

**Exit:** deterministic negative tests prove the false-green paths are closed; all required cells are declared; focused/static/unit/security checks pass.  
**Stop:** a required variant is collapsed into an aggregate result, browser coverage is simulated only through APIs, a live provider/model becomes necessary, or auth behavior differs from the documented contract.  
**Rollback:** revert only W1's explicit path set; the old scenarios remain blocked and must not regain “proven” status.

## W2 — Truthful release selection, container runner, and CI contract

**Owner role:** implementer `zai/glm-5.3-flash` (`max`); independent reviewer/fixer `meta/muse-spark-1.3-contributor` (`xhigh`).  
**Dependencies:** W1.  
**Primary scope:** scenario registry/runner, a new declarative release matrix and resolver, QA Docker/Compose/scripts, `.github/workflows/ci.yml`, required-check/workflow/QA contract tests, and testing documentation.

### Design

1. Keep `testing/ui-journeys.smoke.json` as a fast subset, but remove “smoke plus empty proven-extra equals full” semantics. Replace it with one declarative release matrix (proposed: `testing/ui-journeys.release-matrix.json`) that is the complete source of selection obligations.
2. Require a registry/matrix bijection:
   - every registered scenario appears exactly once;
   - unknown, duplicate, malformed, or non-importable scenarios fail before execution;
   - selection uses exact scenario IDs, not substring matching;
   - every variant is either credential-free and required, or names a specific governed live capability;
   - generic reasons such as “not yet proven” are invalid;
   - 82/83/84 and all their required variants are credential-free release obligations.
3. Extract selection and validation into a testable module consumed by local runs and CI. Import failures are release failures, not warnings that silently shrink the executable set.
4. Emit a versioned run manifest containing repository SHA, tree state, registry/matrix hashes, scenario and variant IDs, expected/actual results, environment, container image IDs/digests, timestamps, screenshots, HAR, console/network findings, and named unavailable capabilities. The release job fails on any missing/failed required cell or invalid `not_runnable`.
5. Add a dedicated Playwright/browser service to `docker-compose.qa.yml` and the QA image/scripts. It runs Node/Playwright inside the container, reaches the QA UI/API over the Compose network, records HAR/screenshots/results to a mounted run-specific artifact directory, and never relies on host-repository Node or Python.
6. Preserve unique `QA_RUN_ID`/Docker project isolation, synthetic volumes, loopback-only host publication, internal backend/data networks, credential-free provider settings, and no live model probes. Prove the browser container's UI/API addressing and CORS contract rather than assuming host-loopback URLs work inside the container.
7. Make the `ui-journeys` CI job invoke the same containerized command and release resolver as the Mac Studio lane. Host-side CI may orchestrate Compose, but browser execution and repository test tooling stay in the runner container. The `release-gate` continues to consume the required `ui-journeys` result.
8. Update `TESTING.md` and `testing/TEST_HISTORY.md` because suite topology changes. Keep tracked status provisional until exact-SHA execution exists.

### Acceptance and verification

Planned non-live commands:

```bash
npm --prefix tests/simulation run test:static
node --test tests/simulation/lib/release-matrix.test.mjs tests/simulation/lib/scenario-registry.test.mjs
python -m pytest -q tests/test_qa_stack_contract.py tests/test_qa_capabilities.py tests/test_qa_artifacts.py tests/test_required_checks.py tests/test_workflow_contracts.py
python scripts/check_qa_capabilities.py
python scripts/check_required_checks.py
python scripts/check_workflow_contracts.py
python scripts/check_ci_governance.py
```

Compose render and actual browser execution are deliberately **not** run on the architect's/local machine. They run in owner-authorized CI or on the Mac Studio:

```bash
QA_RUN_ID=<RUN_ID> docker compose -f docker-compose.qa.yml --profile ui config --quiet
QA_RUN_ID=<RUN_ID> docker compose -f docker-compose.qa.yml --profile ui run --rm -T qa-browser npm --prefix tests/simulation test -- --selection release
```

Add contract tests proving the second command uses the browser container, every release artifact embeds `<PROMOTION_SHA>`, all host-published ports bind loopback, no live credential/provider is selected, and cleanup targets only `<RUN_ID>`.

**Exit:** complete truth table for all registered scenarios/required variants; no silent import/selection shrinkage; container runner and CI share one contract; static/workflow/QA tests pass.  
**Stop:** any full lane still derives from smoke+empty-extra, `not_runnable` lacks an allowed capability, host Node/Python performs the Mac browser run, container networking requires public exposure, or the job can pass without the run manifest.  
**Rollback:** revert W2's explicit commits; retain the previous lane only as known-blocked historical behavior, never as release evidence.

## W3 — Independent review, truthful documents, full gates, and SHA seal

**Owner role:** implementer for remediations; independent code reviewer `meta/muse-spark-1.3-contributor` (`xhigh`); owner owns desktop scope decision from G0.  
**Dependencies:** W2 fully converged.  
**Mutations:** final code/test/doc corrections before sealing only.

### Work

1. Review the complete W1-W2 diff against B1-B6, the Research Spine, self-improvement governance, auth/session security, QA isolation, selection algebra, and workflow/required-context contracts. Remediate all Blocker/Major findings and delta re-review changed seams.
2. Correct `docs/promotion/2026-09-09-promotion-certification.md` so it says evidence-pending/blocked, not owner-gated ready, until exact-SHA CI, browser, policy, and owner gates exist. Append—not rewrite—the Build Stream lifecycle to the same truthful state and reconcile its findings register.
3. Apply the G0 desktop decision:
   - **blocking:** add `desktop-check` to the manifest/release gate and require successful `cargo check`; or
   - **out of scope:** retain 16 required contexts and state explicitly that no desktop readiness claim or desktop release artifact is included.
4. Run changed-seam tests, all required local deterministic gates, and the full credential-free suites whose oracle/config changed. Update Research Spine/self-improvement docs only if behavior changed; otherwise record non-impact and run the contract probes appropriate to touched research-facing journeys.
5. Confirm explicit path ownership, no ambient changes, and no protected-folder mutation. Commit every tracked code, test, workflow, coverage, lifecycle, and certification correction **before** selecting the SHA.
6. Freeze clean `HEAD` as `<PROMOTION_SHA>`. Record the commit and tree hash in CF evidence. From this point, any tracked edit invalidates the seal and returns to W3 for a new SHA and complete recertification.

### Final pre-seal command matrix

```bash
git diff --check
python -m ruff format --check backend tests scripts
python -m ruff check backend tests scripts --select F821,F811,F822
python -m pytest -q -m "not live_llm" tests --ignore=tests/simulation
npm --prefix frontend run lint
npm --prefix frontend run test:unit
npm --prefix frontend run build
npm --prefix tests/simulation run test:static
python scripts/security_benchmark.py --fail-on-threshold
python scripts/public_repo_quality_audit.py
python scripts/check_required_checks.py
python scripts/check_workflow_contracts.py
python scripts/check_ci_governance.py
python scripts/check_qa_capabilities.py
python scripts/verify_build_stream_status.py docs/build-stream/2026-09-09-testing-to-main-convergence.md
```

Also run the repository's required integrity, feature-obligation, security-release-readiness, release-artifact-cleanliness, research-validity, self-improvement-governance, and QA provisional/reset/seed tests as resolved by W0 impact and the CI manifest. Record exact commands/results, warnings, environment, and duration rather than copying historical counts.

**Exit:** independent review pass; truthful evidence-pending documents; desktop decision reflected; every tracked mutation committed; clean `<PROMOTION_SHA>` and tree hash frozen; `CF-402..410` remain open/pending external evidence where appropriate.  
**Stop:** false-ready wording, security benchmark below threshold, Research Spine bypass, changed required context without contract sync, dirty tree, unresolved Major finding, or any tracked post-seal edit.  
**Rollback:** revert only the faulty pre-seal wave commits and reseal after review; a seal is invalidated, never amended in place.

## G1 and W4 — Owner-authorized push and exact-SHA GitHub CI

**Owner-only action G1:** authorize pushing exactly `<PROMOTION_SHA>` through the approved `testing` path. No force push, rebase, squash, or unrelated commit is allowed.  
**Dependencies:** W3 sealed and clean.

### Work and proof

1. Pre-read local refs and `git ls-remote` remote refs. Stop if remote `testing` moved from the expected predecessor; do not force or overwrite.
2. Owner-approved push transports exactly `<PROMOTION_SHA>`. Immediately prove `refs/heads/testing` equals it.
3. Require a fresh GitHub `push` workflow run whose `head_sha` is exactly `<PROMOTION_SHA>`. All 16 contexts must pass, or 17 when desktop is blocking. No branch-level green from another SHA counts.
4. Download artifacts rather than trusting the green UI. Validate checksums, manifests, scenario/variant summaries, registry/matrix hashes, image IDs/digests, source/tree SHA, and generated manifests. `ui-journeys` must have executed the container runner and must not report invalid/missing required cells.
5. Store GitHub/CF evidence externally keyed to `<PROMOTION_SHA>`; do not commit a post-run dossier update into the sealed candidate.

Planned verification:

```bash
git ls-remote origin refs/heads/testing
gh api "repos/<OWNER>/<REPO>/actions/runs?head_sha=<PROMOTION_SHA>&event=push"
gh api -H "Accept: application/vnd.github+json" "repos/<OWNER>/<REPO>/commits/<PROMOTION_SHA>/check-runs"
gh run download <RUN_ID> --dir <EVIDENCE_ROOT>/<PROMOTION_SHA>/github
sha256sum -c <EVIDENCE_ROOT>/<PROMOTION_SHA>/github/checksums.txt
```

**Exit:** remote ref, run `head_sha`, every required context, and every downloaded artifact agree on `<PROMOTION_SHA>`; artifact contents pass inspection.  
**Stop:** remote drift, absent/extraneous required context, cancellation/skip, source/tree mismatch, stale artifact, scenario import loss, or a required `not_runnable`.  
**Rollback:** do not rewrite the remote; fix forward on a new reviewed commit, return to W3, and produce a new seal.

## G2 and W5 — Isolated exact-SHA Mac Studio browser acceptance

**Owner-only action G2:** authorize a bounded remote QA run and the exact remote checkout/evidence roots. This does not authorize changes to existing stacks, Docker installation, host package installation, or live providers.  
**Dependencies:** W4 exact-SHA CI green.

### Preflight

1. Passively record Docker/Compose versions, free space, existing project/container names, and checkout state without secrets. Do not enumerate protected model data for cleanup.
2. Create a new isolated checkout at exactly `<PROMOTION_SHA>` and verify clean commit/tree identity. Never use or mutate the detached `8c4e54f...` checkout with 679 dirty entries or its local-bundle origin.
3. Select a collision-free `<RUN_ID>`; render Compose before startup; prove all published ports are loopback-only, volumes/networks are run-owned, and the browser executes in `qa-browser`.
4. Use synthetic data and credential-free configuration. Team mode may be enabled for role coverage, but no chat completion, live LLM server, donor, or third-party key may be loaded/probed.

### Browser matrix and evidence

- Execute every credential-free release-matrix scenario, including 82/83/84.
- For auth-adjacent 82/83/84, require separate admin/researcher/viewer/stranger cells and their expected allow/deny/redirect behavior.
- Require light/dark, desktop/375px, Tab/visible focus, and relevant loading/error/empty cells.
- Record browser actions, labeled setup APIs, screenshots, HAR, console errors, failed network requests, run manifest, container logs/health, SHA/tree/image identities, and dated verdicts.
- A genuine live-only variant may be `not_runnable` only with its declared capability and release disposition. A credential-free required cell may not be `not_runnable`.

Planned remote commands, executed only from the isolated checkout:

```bash
test "$(git rev-parse HEAD)" = "<PROMOTION_SHA>"
test -z "$(git status --porcelain=v1 -uall)"
QA_RUN_ID=<RUN_ID> docker compose -f docker-compose.qa.yml --profile ui config --quiet
QA_RUN_ID=<RUN_ID> docker compose -f docker-compose.qa.yml --profile ui up -d --build
QA_RUN_ID=<RUN_ID> docker compose -f docker-compose.qa.yml --profile ui run --rm -T qa-browser npm --prefix tests/simulation test -- --selection release
QA_RUN_ID=<RUN_ID> docker compose -f docker-compose.qa.yml --profile ui ps
```

Use the repository QA wrapper when W2 defines it as the authoritative equivalent. Cleanup, if owner-authorized, targets only `<RUN_ID>` after artifacts and logs are secured; never use a broad Docker prune or affect pre-existing containers.

**Exit:** all credential-free required cells pass on `<PROMOTION_SHA>` with complete artifacts; container/checkout provenance matches CI; no pre-existing resource changed.  
**Stop:** dirty/stale checkout, SHA/tree mismatch, Docker project collision, public bind, host Node/Python test execution, missing HAR/screenshot/verdict, live-model contact, false-green/aggregate coverage, or resource pressure threatening other workloads.  
**Rollback:** bring down only `<RUN_ID>` resources after preserving evidence; retain the exact checkout and evidence until owner accepts disposal.

## G3 and W6 — Branch protection, negative proof, convergence, and promotion decision

**Owner-only action G3:** apply GitHub settings after W4 proves every intended context exists. The agent prepares and validates the payload but does not perform the write.  
**Dependencies:** W4 and W5 green on the same `<PROMOTION_SHA>`.

### Protection transaction

1. Pre-read and archive the current `main` protection response with secrets excluded.
2. Render `docs/promotion/branch-protection/gh-api-body.json` from `testing/required-checks.json`; compare it byte-for-semantics with the chosen 16- or 17-context package.
3. Owner applies one exact PUT requiring strict checks, all required contexts, at least one approval, code-owner review, stale-review dismissal, admin enforcement, conversation resolution, linear history, and no force pushes/deletions.
4. Read back every field and compare mechanically. Any difference blocks.
5. With separate owner authorization, create a disposable non-draft PR whose deliberately failing required context makes it unmergeable. Capture the red check and blocked mergeability, then close/delete only the disposable branch. Never weaken protection to perform the test.

```bash
gh api "repos/<OWNER>/<REPO>/branches/main/protection" > <EVIDENCE_ROOT>/<PROMOTION_SHA>/protection-before.json
gh api --method PUT "repos/<OWNER>/<REPO>/branches/main/protection" --input docs/promotion/branch-protection/gh-api-body.json
gh api "repos/<OWNER>/<REPO>/branches/main/protection" > <EVIDENCE_ROOT>/<PROMOTION_SHA>/protection-after.json
```

### Exact-identity convergence

Before any promotion proposal, mechanically compare:

- clean local `<PROMOTION_SHA>` and tree;
- `refs/heads/testing` on the remote;
- GitHub CI `head_sha` and required check suite;
- downloaded artifact manifests/checksums;
- Mac Studio checkout/tree, images, and browser run manifest;
- protection context manifest/readback;
- latest independent review verdicts and CF evidence.

Then reconcile `CF-402..CF-410`, run the architecture/security/contract/test-ownership after-gates, verify spec coverage/drift, and accept `CF-SPEC-30` only at zero incomplete linked tasks. The lifecycle and certification remain evidence-pending inside the sealed candidate; final external readiness is recorded in CF/GitHub/owner evidence keyed to the SHA. A later historical documentation closure is a separate post-promotion commit and must not masquerade as part of the certified source SHA.

### Promotion-mechanics decision (stop-the-line)

The required linear-history policy permits squash or rebase-style PR merges, and GitHub rebase-and-merge creates new commit SHAs. Therefore an ordinary GitHub merge can make the `main` commit SHA differ from the tested `testing` source SHA. Under this plan's strict identity rule, tree equivalence alone is not permission to call that exact SHA promoted.

Before a PR is proposed, the owner must choose and document one of these explicit policies:

- an organization-approved, narrowly controlled promotion mechanism that preserves the certified commit identity while still satisfying the chosen protection policy, followed by readback and negative proof; or
- a revised acceptance rule that names the resulting merge SHA as a new certification subject and requires fresh exact-SHA CI/artifact/QA evidence before readiness is declared.

No agent may invent a bypass, treat a merge-queue temporary SHA as the source SHA, or silently downgrade identity to “same product diff.” If neither policy is approved and proven, the correct terminal state is `BLOCKED-PROMOTION-MECHANICS`, not ready.

### Final owner gate

Only when every identity row matches, every required context/variant passes, protection is proven, CF is converged, and the promotion-mechanics policy is satisfied may the system present an owner decision packet. Creating a PR still requires separate owner authorization; merging is never performed by this pipeline.

**Exit:** either `PR-READY-AWAITING-OWNER` with complete exact-SHA evidence and a proven promotion mechanism, or an explicit blocked state naming the first unmet gate.  
**Stop:** any identity drift, open Blocker/Major, incomplete CF task, policy mismatch, failed negative test, missing owner evidence, or wording that conflates transported, CI-green, artifact-built, QA-verified, PR-ready, merged, deployed, and live-verified.  
**Rollback:** owner restores the captured protection payload if necessary; the candidate remains unpromoted. Any source correction returns to W3 and receives a new SHA.

## Research Spine and self-improvement guard

The planned remediation is release/test infrastructure, not a new research-data path. Nevertheless, quality metrics and the full scenario matrix touch research-facing surfaces, so every changed seam receives an explicit impact disposition:

- browser fixtures are synthetic and provisional;
- source-derived evidence remains tied to raw evidence units;
- no candidate nugget, fact, insight, recommendation, design decision, task, or report becomes reportable without independent coding, reliability/grounding, reconciliation, human review, route evidence, Done-task acceptance, and report gates;
- no QA result becomes report evidence;
- telemetry, ReasoningBank, skill memory, autoresearch, Meta-Hyperagent, and self-evolution cannot learn a strong positive signal from raw browser/tool success or mutate global process state;
- protected protocol/codebook/gate/schema blocks remain intact.

Any detected bypass is architecture debt and a release blocker. It is fixed in the owning wave if caused by these changes; otherwise it becomes a separate scoped task and blocks only when it invalidates this release's contract.

## Global stop-the-line and rollback rules

- **SHA drift:** stop immediately; never force, amend, or silently substitute. Return to W3 and reseal.
- **Dirty or stale remote QA:** do not clean/reuse it. Provision a new isolated exact-SHA checkout or remain blocked.
- **Missing CI context:** do not remove it from protection or interpret absence as pass. Repair workflow/selection, then reseal if tracked files change.
- **False green:** any unconditional pass, missing cell, silent import loss, invalid `not_runnable`, or artifact without provenance invalidates the whole browser verdict.
- **Security regression:** benchmark threshold failure, weakened auth/session behavior, public bind, secret exposure, or live-model contact stops the run.
- **Research Spine regression:** any bypass of evidence, coding, reliability, reconciliation, human review, route evidence, Done, or report gates stops the run.
- **Ambient/protected paths:** an unexplained path or any mutation to `LLMs/`/`Model_Finetuning/` stops the run.
- **External drift:** remote ref, protection, GitHub workflow, runner image, or Mac environment changes between proof steps invalidate affected evidence; re-run from the earliest changed boundary.
- **Rollback unit:** targeted revert/fix-forward of only wave-owned commits/resources. Never reset the repository, broadly clean Docker, or overwrite ambient work.

## Owner approval packet

### Proposed mutations after approval

- W1: scenarios 82/83/84, shared variant/oracle tests, coverage mappings, and possibly the smallest accessible catalog error-state UI seam.
- W2: release matrix/resolver, simulation runner result/provenance schema, QA browser container and wrapper, CI `ui-journeys` selection/execution, required workflow/QA contract tests, and testing documentation.
- W3: review remediations, truthful lifecycle/certification append/update, desktop-policy manifest/docs change, and final verification evidence before sealing.
- No unrelated lint/complexity cleanup. The 41 frontend warnings and inherited complexity remain separately governed unless a changed seam worsens them.

### Owner-only external actions

1. **G0 now:** approve/reject this plan and choose desktop `blocking` or `out of scope`.
2. **G1 after W3:** authorize the exact candidate push to `testing`.
3. **G2 after W4:** authorize the isolated Mac Studio exact-SHA QA run and bounded run-owned cleanup.
4. **G3 after W5:** apply the exact branch-protection payload and separately authorize the disposable negative-test PR.
5. **Final:** choose/prove the promotion identity policy, then decide whether a PR may be created. Merge remains a separate owner action.

### Estimated cost

| Activity | Expected elapsed time | External/model cost |
|---|---:|---|
| W0 reconciliation/impact | 20-45 minutes | no live model/provider calls |
| W1 oracle/variant implementation + focused review | 2-4 hours | planned Pi agent usage only |
| W2 resolver/container/CI implementation + review | 3-6 hours | planned Pi agent usage only |
| W3 broad deterministic verification + remediation/seal | 2-5 hours | local CPU; no Docker/live LLM on this machine |
| W4 exact-SHA GitHub CI + artifact inspection | 1-2 hours, runner-dependent | GitHub Actions minutes |
| W5 Mac Studio full browser matrix | 2-4 hours, scenario-dependent | Mac CPU/storage; no provider/API spend |
| W6 protection/negative proof/final audit | 30-90 minutes plus CI for disposable PR | GitHub Actions minutes |

### Residual risks requiring owner awareness

- Full execution of all credential-free scenarios may expose real product defects or runtime beyond the estimate; failures create focused remediation and a new seal.
- The Mac Studio's available disk/ports/resources are unknown until passive preflight; existing protected workloads take precedence.
- GitHub permissions or plan limits may prevent the desired protection payload; the response is blocked, not weakened policy.
- Linear-history PR promotion and strict source-SHA identity are not automatically compatible; W6 requires an explicit, proven owner policy.
- Genuine live-only journeys may remain `not_runnable`; they cannot block or pass silently. If the owner makes one a release requirement, promotion stays blocked until its separately authorized capability exists.
- Frontend lint's 41 warnings and inherited complexity are non-blocking debt unless W1-W2 worsen them.

## Approval requested

Approve only if the seven-wave graph, planned mutations, model routes, external gates, runtime cost, desktop scope choice, and strict identity stop condition are acceptable. Until that explicit decision is recorded, the durable state is:

`AWAITING-OWNER-APPROVAL — NO IMPLEMENTATION OR EXTERNAL ACTION AUTHORIZED`
