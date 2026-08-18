# Plan A — Public, provider-agnostic Istara testing branch and CI automation

- **Task:** `ISTARA-PUBLIC-CI-TESTING-20260818-PLAN-A`
- **Role:** `istara-public-ci-testing-20260818-architect-a`
- **Spec:** `CF-SPEC-56`
- **Pipeline:** `ISTARA-PUBLIC-CI-TESTING-20260818`
- **Lifecycle:** `docs/build-stream/2026-08-18-istara-public-ci-testing-automation.md`
- **Planning mode:** independent S1 draft; no product, workflow, Compose, test, generated-doc, or runtime implementation is included here.

## 1. Executive summary

Istara already has a substantial deterministic test estate and a useful split between
CI-safe checks and live/environment-bound checks, but the public delivery contract is
not yet current by construction. The current `.github/workflows/ci.yml` runs governance,
backend, frontend, JavaScript-harness, and desktop jobs on `main`/`staging`; it does not
run a dedicated feature-obligation classifier, disposable QA-stack render/build/reset
proof, or a human-gated promotion workflow. The root `docker-compose.yml` is a useful
local deployment contract, but it assumes a local Ollama path by default, uses fixed
container names, and is not yet the public disposable QA artifact contract.

This plan proposes a long-lived public `testing` branch as the integration/QA branch,
short-lived feature branches with declared coverage obligations, a fail-closed feature
and subfeature registry, deterministic CI lanes, an immutable disposable Docker QA
artifact, and separately authorized runtime/staging lanes. The official path is
provider-neutral and host-agnostic. It never requires Ollama, LM Studio, `multivac`, a
private endpoint, or owner credentials. A private `multivac` adapter may consume the
same public artifact later, but is not the official CI path or a prerequisite for merge.

The load-bearing boundary is evidence, not a green process exit:

- deterministic contract lanes prove only deterministic contracts;
- a contract-only provider stub cannot prove model quality, embedding quality, or
  reportability;
- an authorized live lane proves one explicitly selected chat/embedding target,
  identity, dimension, route evidence, and bounded runtime behavior;
- synthetic QA research remains provisional until the Research Spine, reconciliation,
  human review, Done-task, and report gates are demonstrated;
- all automated checks must be green before the owner reviews a promotion manifest;
- only after that explicit human gate may the promotion workflow create a PR to `main`.

### Developer outcome

A developer can branch from `testing`, run a documented deterministic command set, render
and build a disposable QA image, and obtain a short-lived QA environment with a unique
Compose project and isolated data. A feature cannot silently enter the branch without a
declared or automatically inferred test obligation. Failures identify the feature,
obligation, lane, command, and artifact needed to diagnose them.

### Maintainer outcome

Maintainers receive stable checks, immutable image provenance, sanitized artifacts,
branch protection, review evidence, and a human-controlled promotion boundary. CI does
not mutate `main`, open a promotion PR, deploy a host, load a model, or use `multivac`
without the explicit owner-controlled path.

## 2. Goals, non-goals, assumptions, and constraints

### Goals

1. Define branch topology and a state machine for `feature/*`, public `testing`,
   optional `staging`, and protected `main`.
2. Detect every changed feature/subfeature and compute its obligations from a tracked,
   reviewable registry; fail closed for unknown behavioral surfaces.
3. Preserve and orchestrate the existing deterministic test pyramid: governance,
   backend contracts, frontend checks, relay, static simulation, real-user syntax,
   mutation/property checks, security benchmark, docs parity, and Compose/image checks.
4. Produce a reproducible, host-agnostic, disposable Docker QA artifact with immutable
   tags, provenance, SBOM/attestation where available, isolated volumes, reset/reseed,
   resource limits, and sanitized result retention.
5. Make chat and embedding provider contracts explicit and provider-neutral without
   weakening `assert_vector_space_invariant`, exact model identity, dimensions, or
   fail-closed behavior.
6. Validate synthetic QA data through the Research Spine in provisional mode, without
   turning fixtures, fake vectors, raw tool success, or generated prose into report
   evidence.
7. Separate CI, authorized live QA, staging, and optional private adapters.
8. Make human approval the only path that unlocks promotion-PR creation to `main`, with
   required checks and human review still enforced after the PR exists.

### Non-goals

- No implementation in this draft: no source, workflow, Compose, test, generated-doc,
  production, or runtime changes.
- No Docker/application-server startup, image build, live provider request, model load,
  model download, `multivac` access/mutation, deploy, merge, push, or PR creation in the
  planning stage.
- No replacement of the Research Spine with a benchmark-specific shortcut.
- No provider-specific public CI dependency, private URL, token, endpoint fingerprint,
  committed credential, or host-network discovery.
- No automatic merge, automatic promotion, or implicit owner approval.
- No cleanup or mutation of `LLMs/` or `Model_Finetuning/`.
- No attempt to solve all existing gate debt, import cycles, secret-flow findings, or
  large-file findings unless an approved implementation task directly owns them.
- No assumption that the existing `staging` branch is a safe pre-main integration gate;
  its current sync workflow must be explicitly reviewed before it is used as one.

### Assumptions to verify during implementation

- GitHub branch protection, environments, CODEOWNERS, artifact policy, and package
  publication settings are available to the repository owner.
- GitHub-hosted Linux runners can run the deterministic lanes and a bounded Compose QA
  job within an approved resource/time budget. If Docker-in-Docker is not acceptable,
  use a service-container or a runner-native Docker strategy; do not mount the host
  Docker socket into product containers.
- Existing `tests/document_corpus/canonical/` contains the governed synthetic corpus
  and named slices used by product-level QA. The implementation must verify the current
  manifest rather than hard-code counts from this plan.
- The current provider adapter can represent distinct chat and embedding identities,
  or a small explicit contract change will be needed. If it cannot, the live lane must
  fail closed rather than reuse a local default.
- A public image registry is optional for fork PRs. Untrusted PRs may receive a saved
  image/build artifact but must not receive registry write credentials.

### Hard constraints from repository policy

- CI-safe and live tests are separate in `TESTING.md`; live LLM tests use one explicit
  gitignored OpenAI-compatible profile and a fixed test model identity.
- The Research Spine in `docs/architecture/research-validity-contract.md` is the
  system-wide contract for research data, including benchmarks, simulations, chat,
  integrations, compute donation, and future surfaces.
- `docs/architecture/self-improvement-governance-contract.md` limits learning to
  governed, project-scoped, verified outcomes and forbids protected-methodology bypass.
- `AGENTS.md` forbids private endpoint disclosure, unapproved active model loading,
  external mutation, and cleanup of protected artifact directories.
- `scripts/check_public_tree_clean.py` blocks runtime, database, media, model, and
  local-artifact paths from public changes.

## 3. Current-state evidence and gaps

The following is repository evidence, not a claim that the target design already exists.
Commands and paths are named so implementation can re-check the facts at the actual
base SHA.

| Area | Current evidence | Gap / implication |
|---|---|---|
| Existing CI | `.github/workflows/ci.yml` is triggered on pushes and PRs targeting `main` and `staging`. It has `governance`, `backend`, `frontend`, `test-harness-js`, and `desktop` jobs. | No first-class `testing` branch trigger, feature-obligation job, QA Compose render/build/reset job, artifact manifest, or promotion gate. |
| Governance | The governance job runs `check_integrity.py`, `check_ci_governance.py`, `check_test_harness.py`, release-security readiness, the security benchmark, and PR change-obligation checks. | Existing checks are broad path/pattern contracts. They do not provide an executable feature/subfeature registry or a union of per-feature runtime obligations. |
| Tests | `TESTING.md` explicitly separates CI-safe checks from live/environment-bound checks and documents backend, frontend, relay, static simulation, benchmark, mutation, security, and feature-doc commands. | The documented matrix is not yet the single machine-readable source that decides which obligations are required for a changed feature. |
| Existing Compose | `docker-compose.yml` includes backend, frontend, optional Postgres/relay/production/observability services, internal backend/data networks, healthchecks, resource limits, and hardened container settings. | It defaults the backend to `ollama`, depends on `ollama`, uses fixed `container_name` values, persists named volumes, publishes Caddy ports only in a profile, and mixes local-runtime assumptions with a reusable QA contract. |
| Docker images | `backend/Dockerfile` and `frontend/Dockerfile` are multi-stage and non-root at runtime; `relay/Dockerfile` is a Node Alpine image. | No public QA image naming/provenance/retention contract, digest manifest, SBOM policy, or provider-mode label is defined. Relay also needs a deliberate review of runtime argument expansion and dependency hardening before inclusion in the canonical QA image. |
| Branch flow | `.github/workflows/sync-staging.yml` force-pushes `main` to `staging` on a push to `main`. `CHANGE_CHECKLIST.md` describes `staging` as a review target in places, but the workflow makes it a mirror after the fact. | The repository has no current, executable state machine for `testing` integration followed by an owner-gated promotion to `main`. The owner must decide whether `staging` remains a mirror, becomes an environment branch, or is retired from the promotion path. |
| Provider contract | `backend/app/core/pi_runtime/endpoints.py`, `model_manager.py`, and `embeddings_gateway.py` carry explicit endpoint/provider/model fields, secret resolution, and typed failures. `embeddings_gateway.py` contains `assert_vector_space_invariant`; `tests/pi_production/test_w8_embeddings_gateway.py` covers dimensions, identity, malformed vectors, and fail-closed paths. | Compose defaults and some legacy provider paths still expose local-provider assumptions. The QA contract needs separate chat/embedding identities, explicit readiness evidence, and no fallback that silently changes vector space. |
| Live test profile | `tests/llm_test_config.py`, `testing/TESTING_STRATEGY.md`, and `TESTING.md` specify one private OpenAI-compatible profile, fixed model identity, retry budget, secret isolation, and no endpoint probing. | This is a useful live-lane contract, but it is not a public CI dependency and must not be copied into public workflow defaults. |
| Research validity | `docs/architecture/research-validity-contract.md` requires source spans → evidence units → independent coding → reliability/grounding → reconciliation → accepted artifacts → human-approved Done → reports. `TESTING.md` requires canonical corpus slices and forbids synthetic shortcuts for product-level research tests. | QA seed/reset scripts must preserve this distinction and explicitly mark contract/synthetic runs provisional. A green synthetic runtime must not be reported as model or research validity. |
| Self-improvement | `docs/architecture/self-improvement-governance-contract.md` forbids learning from raw tool success and requires project scope, verification, governance, and rollback. | Autoresearch, ReasoningBank, Memento, Meta-Hyperagent, RAG/GraphRAG, and telemetry checks need a governance lane, not a test fixture that promotes output. |
| Public-tree safety | `scripts/check_public_tree_clean.py` blocks data, model, media, database, result, and local config paths. | QA artifact export needs an explicit allowlist and sanitized manifest; raw sources, screenshots, logs, tokens, and volumes must remain ignored or ephemeral. |
| Prior readiness material | The earlier readiness investigation in `docs/build-stream/2026-08-17-istara-testing-docker-readiness.md` (currently an unmerged planning artifact in the owner checkout) records Compose validation, local-model dependency, LAN/origin, persistence, and provider-readiness risks. | Those findings are diagnostic inputs, not implementation proof. Re-run them on the selected implementation base and carry unresolved findings into CF tasks rather than assuming the prior branch is current. |

### Current known baseline risks to preserve honestly

The latest Compass Forge health output reports inherited failures including Python import
cycles, secret-flow findings, and unexpected large files. The output also reports existing
complexity, route-drift, and type-drift warnings. This plan does not relabel those as
caused by the proposed CI system. The implementation phase must capture a fresh gate
baseline, compare post-change output, and either fix newly introduced findings, record
inherited debt, or add a time-bounded suppression with an owner-approved reason.

The existing root Compose file must be checked with the repository's supported Compose
version before it is selected as the QA base. A prior readiness record reports a
`pids_limit`/`deploy.resources` validation conflict under one installed Compose version;
implementation must reproduce or refute that report with:

```bash
docker compose -f docker-compose.yml config --quiet
```

No implementation may “solve” a provider-readiness problem by removing the vector-space
invariant, generating fake production vectors, auto-downloading a model, or silently
falling back to a different provider.

## 4. Target architecture

### 4.1 Public surfaces and source-of-truth files

The implementation should add or extend the smallest set of canonical files:

- `testing/feature_coverage.yml` (or JSON if the repository's parser policy requires it):
  feature/subfeature registry, path ownership, obligations, commands, corpus slices,
  risk, live-lane requirements, and documentation links.
- `scripts/check_feature_obligations.py`: deterministic diff classifier and fail-closed
  registry evaluator; integrate its output into `check_change_obligations.py` or make
  the relationship explicit rather than creating two contradictory classifiers.
- `docker-compose.qa.yml` (name is provisional): public disposable QA entrypoint with
  explicit `contract`, `synthetic`, and `live` profiles.
- `scripts/qa_stack.py` or a small set of composable scripts: render, seed, readiness,
  reset, sanitized artifact collection, and cleanup scoped to a supplied Compose project.
- `.github/workflows/ci.yml` plus a dedicated QA/promotion workflow if separation makes
  permissions clearer.
- `tests/test_feature_obligations.py`, provider/QA contract tests, and targeted tests
  for the reset/readiness/artifact scripts.
- `TESTING.md`, `testing/TESTING_STRATEGY.md`, `README.md`, `README.pt-BR.md`,
  `CHANGE_CHECKLIST.md`, `Tech.md`, and relevant feature docs, all updated only where
  the implementation changes the documented contract. The unrelated
  `docs/features/site/manifest.json` modification must stay isolated.

The registry is the authoritative mapping. Documentation explains it, but a prose table
must not be the only enforcement mechanism.

### 4.2 Branch and promotion state machine

Recommended topology:

```text
feature/<short-name>  --checks-->  PR to testing  --merge by project policy-->
        |                                 |
        |                                 v
        +--------------------------> testing integration branch
                                          |
                              deterministic + QA artifact evidence
                                          |
                            owner human-promotion environment gate
                                          |
                              promotion workflow creates PR only now
                                          v
                                      main PR
                                          |
                       required checks + CODEOWNERS/human review, no auto-merge
                                          v
                                      main release

optional: main --mirror workflow--> staging (environment mirror only, not a
pre-main approval branch unless the owner replaces the current force-sync contract)
```

State definitions:

1. **Feature branch:** short-lived branch from `testing` (or the documented base); local
   obligations can be run before opening a PR to `testing`. A feature PR may be created
   by its developer under repository policy, but it cannot bypass required checks.
2. **Testing integration:** public long-lived branch. It is the canonical branch for
   cross-feature deterministic checks and disposable QA artifacts. No direct pushes;
   branch protection requires the feature obligation check and relevant required jobs.
3. **QA candidate:** an immutable `testing` commit with a green evidence manifest, image
   digest, generated Compose config hash, sanitized runtime report, and no unclassified
   behavioral changes. It is not yet a release or main PR.
4. **Human-promotion gate:** an owner-approved GitHub protected environment or equivalent
   manual dispatch. The approval binds the exact source SHA, test evidence manifest,
   image digest, and intended `main` base. Approval is recorded in CF and the workflow
   run. It is not inferred from a green check, bot comment, or actor identity.
5. **Promotion PR:** a workflow may create the `testing` → `main` PR only after the gate.
   The PR is never auto-merged. Main branch protection requires fresh checks, required
   human review/CODEOWNERS, and a merge action by an authorized human.
6. **Staging:** retain only as an explicitly documented environment mirror or change it
   into a separately protected pre-main branch. The current force-sync workflow must not
   be described as a human approval gate.

Cancellation/retry rules:

- PR runs use `concurrency` keyed by workflow, ref, and change class; stale runs cancel
  before they publish or promote anything.
- Push runs on `testing` are immutable by SHA; retries reuse the same source SHA but get a
  distinct run/Compose project name and artifact namespace.
- A failed or cancelled run cannot promote. A retry must regenerate the evidence manifest
  and revalidate the digest; no stale green result is reused by branch name alone.
- Fork PRs receive read-only permissions and no live-provider secrets. They may run
  contract-only QA and upload a saved/sanitized artifact; registry publication and live
  lanes are restricted to trusted branches/manual dispatch.

### 4.3 Feature/subfeature registry

Each registry entry should have at least:

```yaml
schema_version: 1
features:
  - id: research-validity.coding-reliability
    status: active
    owner: research-platform
    paths:
      - backend/app/services/research_validity_service.py
      - backend/app/models/code_application.py
      - frontend/src/components/findings/CodeReviewQueue.tsx
      - tests/pi_production/test_w5_intercoder.py
    obligations:
      deterministic:
        - backend_contracts
        - research_spine_contract
      integration:
        - canonical_corpus: coding-reliability
      live:
        - authorized_provider_smoke
      docs:
        - feature_docs
        - testing_docs
    commands:
      deterministic: [pytest_research_validity]
      live: [qa_spine_smoke]
    acceptance: reportability_requires_reconciled_evidence
```

The exact IDs and paths must be derived from the repository, not invented from the
example. Registry rules:

- Every behavioral path has one or more owners; overlapping matches are allowed only
  when the union is intentional and tested.
- Obligations are named capabilities, not arbitrary shell strings. A command catalog
  maps a capability to a pinned command, working directory, environment policy, live
  requirement, timeout, artifact allowlist, and expected result schema.
- A feature can declare `deterministic`, `contract_only`, `synthetic_provisional`,
  `authorized_live`, `security`, `docker`, `docs`, `mutation`, `property`, and
  `human_review` obligations independently.
- The registry records whether a lane is required, optional, or owner-authorized. An
  optional live lane cannot satisfy a required deterministic obligation.
- Documentation obligations are explicit for UI/menu/route/store/agent/skill/model/test
  behavior. A test-only feature entry can require test-harness docs without inventing a
  product feature page.
- Generated paths are mapped to their source owner. A generated-only diff fails if its
  source was not changed or if it is not identified as an expected generator output.
- An allowlist for truly mechanical changes (version badge, spelling, license, generated
  output) is narrow, reviewed, and cannot cover backend/frontend behavior or security.
- Entries carry `introduced_in`, `last_verified_sha`, and a stable command key so stale
  coverage is visible. CI must not silently rewrite the registry.

### 4.4 Change-obligation algorithm

`check_feature_obligations.py --base BASE --head HEAD` should:

1. Obtain the diff file list from Git, excluding deleted paths only after evaluating their
   owning registry entries.
2. Normalize path separators and classify each path into source, test, docs, generated,
   runtime-data, artifact, workflow, provider, security, or unknown zones.
3. Match changed paths against registry entries and the explicit command catalog.
4. Add obligations for every matched feature, plus cross-cutting obligations from the
   change class: CI/workflow changes require governance and workflow validation; provider,
   embedding, connection, auth, WebSocket, MCP, webhook, or Docker security changes
   require the security benchmark; test harness changes require harness governance; UI,
   route, store, agent, skill, model, or test behavior changes require feature-doc parity.
5. Require a machine-readable feature declaration for new paths or a reviewed registry
   update in the same change. A path that matches no entry is an error, not a best-effort
   warning, unless it is in a narrowly audited allowlist.
6. Compute the union of required commands and produce a stable JSON report containing:
   base/head SHA, changed paths, matched feature IDs, obligations, skipped optional lanes,
   unknown paths, required artifacts, and the reason for each obligation.
7. Fail before expensive jobs if `unknown_paths`, `missing_registry_entries`,
   `missing_test_ownership`, `missing_doc_ownership`, or `forbidden_artifacts` is nonempty.
8. Pass the report as a job output to later jobs so the workflow cannot run a narrower
   matrix than the classifier selected.
9. Validate that every selected obligation has a test owner and an artifact/evidence
   owner. This directly addresses the `test_ownership` gate rather than relying on
   filename convention alone.

The classifier must inspect dynamic/string-keyed registrations manually when creating or
updating entries. Compass Forge graph results are the starting map, not proof that every
runtime route or registry is found.

## 5. CI lanes and execution matrix

The workflow should use a cheap-to-expensive, fail-fast graph. All lanes emit JUnit/JSON
summaries and a redacted evidence manifest; raw outputs stay in ignored result roots or
short-retention CI artifacts.

| Order | Lane | Default trigger | Proves | Does not prove |
|---:|---|---|---|---|
| 0 | Diff/obligation classifier | every feature PR/push | all changed paths are classified and obligations are selected | behavior, provider health, runtime quality |
| 1 | Public-tree and secret/artifact guard | every trusted/untrusted run | no blocked files, committed secrets, private endpoint fingerprints, or unsafe artifacts | runtime behavior |
| 2 | Governance/docs contract | every run; docs lane when selected | integrity, CI governance, harness governance, change obligations, feature-doc parity | live app acceptance |
| 3 | Python compile/unit/contract | every run | Python syntax, targeted service/API/security/provider/research contracts | frontend/browser behavior or real model quality |
| 4 | Property/mutation | selected by registry; default for affected targets | deterministic invariant strength and mutation kill rate | model semantics or production research validity |
| 5 | Frontend | selected for frontend/shared behavior; full on `testing` | lint, type safety, unit, mutation, production build | backend/provider runtime |
| 6 | Relay and JS harness | selected for relay/simulation/benchmark; default on `testing` | Node tests, static simulation, real-user syntax, project-scope checks | browser acceptance against a running app |
| 7 | Compose contract | every QA-artifact candidate | rendered config, profiles, image references, healthcheck syntax, forbidden host dependency | service health or feature workflow |
| 8 | QA image build | `testing` and approved candidate runs | reproducible image build, digest, SBOM/provenance, non-root/hardening checks | live provider/model quality |
| 9 | Contract-only QA stack | `testing` and PRs when Docker obligation selected | disposable orchestration, auth/origin plumbing, reset/reseed, project scope, provisional pipeline plumbing using a test adapter | real provider quality, reportable evidence |
| 10 | Authorized live provider smoke | manual owner dispatch only | one explicit chat+embedding target, provider auth, identity, dimensions, route evidence, bounded smoke | broad product release readiness |
| 11 | Full staging acceptance | owner-authorized environment only | complete running system with chosen provider and feature acceptance | public CI reproducibility unless artifact/config is identical |
| 12 | Evidence/promotion manifest | after all required lanes | exact SHA, digest, commands, artifacts, failures, approvals | permission to merge without human review |

### Deterministic command catalog

The implementation should reuse documented commands from `TESTING.md` and add only
commands that have first been proven locally. The initial catalog should include:

```bash
# Governance and repository contracts
python scripts/check_public_tree_clean.py --base "$BASE" --head "$HEAD"
python scripts/check_integrity.py
python scripts/check_ci_governance.py
python scripts/check_test_harness.py
python scripts/check_change_obligations.py --base "$BASE" --head "$HEAD"
python scripts/check_feature_obligations.py --base "$BASE" --head "$HEAD" --json-out artifacts/feature-obligations.json
python scripts/feature_docs.py --seed-missing --generate-site --check
pytest tests/test_feature_docs.py -q

# Backend and research/provider contracts
cd backend && pytest ../tests/ -v --tb=short
pytest tests/test_model_provider_contract.py -q
pytest tests/test_research_validity_contract.py -q
pytest tests/pi_production/test_w8_embeddings_gateway.py -q
pytest tests/pi_production/test_engine_http_provider.py -q
pytest tests/test_harness_project_scope_contracts.py tests/test_project_scope_contracts.py -q

# Frontend and JS harnesses
cd frontend && npm ci && npm run lint && npx tsc --noEmit && npm run test:unit && npm run test:mutation && npm run build
cd relay && npm ci && npm test
cd tests/simulation && npm ci && npm run test:static
npm --prefix tests/real_user_benchmark ci && npm --prefix tests/real_user_benchmark run check

# Security and deterministic invariants
python scripts/security_benchmark.py --fail-on-threshold --output security/security_scorecard.json
pytest tests/test_security_benchmark.py -q
python scripts/production_rehearsal.py --json
python scripts/run_backend_mutation.py
```

Commands are illustrative plan contracts until implementation proves the exact working
directory, dependency install, environment, timeout, and artifact behavior. CI must not
silently convert a failed command into a warning except where the repository explicitly
labels inherited lint/desktop dependency drift as non-blocking; any exception is visible
in the evidence manifest.

### Property and mutation boundaries

Property/mutation jobs target deterministic invariants only: URI normalization, provider
header construction, route/type contracts, embedding vector shape/finite values,
project-scope selection, reliability calculations, reset naming, and obligation registry
classification. Do not mutate a live-provider call or use mutation results as research
quality. Mutation thresholds and target paths must remain explicit and bounded.

### E2E/simulation boundaries

The default PR lane runs static simulation checks, not a live browser suite. A full
simulation, E2E script, marathon, or real-user benchmark requires a running app, a
known test token, a named project, and explicit operator authorization. When selected,
the registry must require the relevant scenario(s), canonical corpus slice, result
schema, timeout, and project cleanup. A scenario cannot fall back to the first visible
project, a fake project ID, or an unscoped route.

## 6. Docker artifact and disposable runtime contract

### 6.1 Image identity and publication

Build the backend, frontend, and any selected relay image with BuildKit/buildx. The QA
artifact manifest should include:

- source commit SHA and repository ref;
- workflow run ID/attempt and builder version;
- image name, immutable digest, platform, and Dockerfile hash;
- Compose file/profile hash and rendered-config hash;
- dependency lockfile hashes;
- SBOM location and provenance/attestation status;
- provider mode (`contract`, `synthetic_provisional`, or `authorized_live`), never a
  secret-bearing endpoint value;
- test-obligation report and pass/fail summary.

Use immutable tags such as `qa-${SHA}` and `qa-run-${RUN_ID}-${ATTEMPT}`. A moving
`testing` tag may be a convenience pointer only and may never be used as promotion
identity. Fork PRs should upload a saved image or build record with short retention;
trusted `testing` runs may publish to GHCR only with least-privilege permissions and
provenance. Do not publish untrusted code with write credentials.

Recommended lifecycle: PR artifacts 7 days, `testing` artifacts 30 days, release
candidate evidence 90 days, with an owner-reviewed retention policy. Retention applies
to binaries and logs; it does not authorize storing user research or credentials.

### 6.2 Compose profiles and topology

Create a QA-specific entrypoint rather than overloading the benchmark overlay. Profiles:

- `contract` (default for CI): backend, frontend, deterministic provider contract stub,
  ephemeral database, and test runner; no local model daemon.
- `synthetic`: canonical synthetic corpus seed and provisional research pipeline; may
  use the contract adapter only for plumbing; all output carries `provisional_qa=true`.
- `live`: no provider container; requires an explicitly supplied provider endpoint,
  chat model, embedding model, expected dimension, and secret through an authorized
  environment. It is not enabled by a normal PR.
- `team`, `relay`, `mcp`, `autoresearch`, `observability`, and `production-ingress`:
  explicit profiles selected by registry obligations and owner authorization.

The QA file must avoid fixed `container_name` values, use the Compose project name for
resource identity, keep backend/data networks internal, publish only the intended test
port(s), and parameterize browser/API/WebSocket origins. Data services are not published
to the host by default. The frontend should depend on semantic backend readiness, not
only process health. Optional services must be independently visible as skipped rather
than silently treated as full-feature coverage.

Every service must be reviewed for `read_only`, `tmpfs`, `cap_drop`,
`no-new-privileges`, non-root user, pids/memory/CPU limits, minimal packages, and
healthcheck behavior. The CI Docker runner itself must be treated as privileged
infrastructure; product containers must not receive the host Docker socket or broad
host mounts.

### 6.3 Project names, reset, and seed

Each run receives a unique project name, for example
`istara-qa-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}`. The name is generated by CI and
validated against a safe-character/length policy. Volumes, networks, containers, and
artifact directories derive from that name. There is no global `docker system prune` or
fixed-volume deletion.

The reset/seed contract is:

1. `render` validates all required environment keys without printing values.
2. `up` creates only the selected Compose project/profile.
3. `wait` checks Docker health plus application readiness and records a redacted report.
4. `seed` creates test users and a uniquely named project, uploads named canonical
   corpus slices, and records source/evidence-unit handles without copying private data.
5. `qa` runs only the obligations selected by the registry.
6. `collect` exports allowlisted JSON/JUnit/trace summaries and a provenance manifest.
7. `reset` stops the project and deletes only its generated volumes/networks/artifacts.
8. A second `seed`/`qa` run proves idempotency and no cross-project leakage.

Reuse `scripts/reset_test_environment.py` where its guarded local SQLite contract fits;
add a thin project-scoped wrapper rather than a second unrestricted destructive tool. The
wrapper must require an explicit confirmation token for destructive reset, reject empty
or root paths, print the target Compose project, and refuse to touch `LLMs/` or
`Model_Finetuning/`.

The seed corpus must use the canonical manifest and named slices such as
`coding-reliability`, `graph-synthesis`, and `low-consensus-review`, not canned report
prose. Seeded artifacts must be visibly provisional until independent coding,
reliability/grounding, reconciliation, Done review, and report gates pass. The contract
lane may use tiny fixtures only for parser/unit checks and must label them as such.

### 6.4 Failure, retry, and artifact behavior

- `render` failure blocks all later QA jobs.
- Image build failure blocks runtime; the logs include a digest/provenance absence, not
  a misleading runtime result.
- Health timeout retains sanitized service logs and config metadata, then cleans only
  the generated project unless a debug-retention input is explicitly owner-authorized.
- Test failure retains JUnit/JSON summaries and the exact command/environment names;
  raw source text, tokens, and full provider responses are not uploaded.
- Retry creates a new project name and evidence manifest. It cannot overwrite a prior
  run's artifacts or mark a previous failure green.
- Cleanup runs in `always` steps but records whether it completed. Cleanup failure is a
  visible incident and does not authorize broad host cleanup.

## 7. Provider-neutral adapter contract

### 7.1 Three provider lanes

**Contract-only.** An in-process or isolated deterministic adapter proves request/response
schema, auth-header construction, model selection, timeout/retry handling, malformed
response handling, embedding count/shape/finite-value validation, and typed fail-closed
errors. It may return deterministic vectors solely to test plumbing. It must be labeled
contract-only and cannot satisfy full-feature research or model-quality acceptance.

**Synthetic provisional runtime.** The disposable QA stack exercises upload → evidence
unit → coding/reliability/reconciliation → task review with synthetic corpus material.
A provider stub or authorized test adapter may be used for plumbing, but all artifacts
carry a provisional state and reports are blocked. This lane can prove project scope,
traceability, reset, UI/API wiring, and gate enforcement; it cannot claim provider
quality.

**Authorized live.** A manual, one-target environment supplies exactly one selected chat
provider and one selected embedding provider, each with explicit provider kind, endpoint
identity, model identity, expected dimensions, timeout/retry budget, and secret source.
The lane records route evidence, model/provider identity, dimension probe, readiness,
selected/served state, and failure state. It must fail closed on missing auth, a
model mismatch, dimension mismatch, unsupported capability, or fallback that changes
vector space. It must never discover endpoints by scanning localhost/LAN or load more
than the configured target.

### 7.2 Capability schema

The provider adapter should expose typed capabilities similar to:

```json
{
  "provider_id": "opaque-configured-id",
  "provider_kind": "openai_compat",
  "chat": {"model": "explicit-chat-model", "endpoint_id": "opaque-chat-id"},
  "embeddings": {
    "model": "explicit-embedding-model",
    "endpoint_id": "opaque-embedding-id",
    "dimension": 1536
  },
  "auth": {"source": "environment-or-secret", "redacted": true},
  "fallback": "disabled",
  "mode": "authorized_live"
}
```

The public schema must not contain a URL, token, private host, or endpoint fingerprint.
The exact application schema may differ, but the following are non-negotiable:

- chat and embedding identities are explicit, not inferred from a local default;
- embedding dimension is probed/declared and verified against stored vector metadata;
- provider capability is checked before runtime work;
- route evidence distinguishes registered, reachable, ready, selected, served, and failed;
- failures are typed and fail closed;
- a retry may repeat the same target but may not silently change provider/vector space;
- test-only `faux` behavior is unreachable from production resolver paths;
- secret resolution is centralized and redaction-safe.

### 7.3 Readiness contract

A live readiness report is green only if all applicable checks pass:

1. configuration contains the explicit provider/chat/embedding identities;
2. secret is present without being printed;
3. provider capability and auth check succeed;
4. chat model identity matches the configured target;
5. embedding model identity and expected dimension match;
6. `assert_vector_space_invariant` succeeds;
7. the backend reports no local-provider fallback or hidden model load;
8. a bounded authorized chat and embedding request succeeds, with content omitted from
   artifacts and only handles/metrics retained;
9. project scope, route evidence, and rollback handles are present.

A contract-only report may check 1, 3, 5, 6 using the stub but must say that it did not
check real provider service or model quality.

## 8. Research Spine and self-improvement validation

The QA system must test that it preserves the same validity spine rather than create a
parallel benchmark objective.

| Spine gate | QA proof | Forbidden shortcut |
|---|---|---|
| Sources | Seed raw canonical synthetic source slices with stable IDs and provenance. | Seed only synthesized nugget/report prose. |
| Evidence Units | Verify source spans/offsets, participant/method metadata, and project ownership. | Use generated summaries as raw evidence without exact spans. |
| Independent coding | Use distinct authorized model identities or explicitly labeled contract stubs; keep coder outputs independent. | Treat one model response or a fixture as consensus. |
| Reliability/grounding | Compute the configured reliability metrics on evidence-unit matrices and verify grounding. | Pass/fail on final answer keywords. |
| Reconciliation | Seed a low-consensus case and require debate/human reconciliation state. | Bulk-accept all findings on a task. |
| Accepted artifacts | Verify accepted atoms/nuggets/facts/insights/recommendations retain evidence links. | Mark every visible artifact reportable. |
| In Review / Done | Verify agents cannot mark Done and human approval is required. | Let CI or agent completion bypass human task review. |
| Reports | Verify only accepted/reconciled evidence on human-approved Done tasks is included. | Generate a report from provisional or In Review artifacts. |
| Route/evidence | Verify project, task, coding-run, model, donor, and retrieval handles are linked. | Treat donor registration or tool success as served evidence. |
| Self-improvement | Verify proposals are sandboxed, project-scoped, governed, and rollbackable. | Learn strong positives from raw tool success or synthetic shortcut. |

All QA reports must carry a status such as `contract_only` or `provisional_qa`; they
must never be ingested as production research evidence or promotion signals. Telemetry
may be content-free and may record handles/metrics; it must not store source text,
prompts, responses, URLs, tokens, or connection strings.

## 9. Security, privacy, and supply-chain controls

### Secrets and logs

- Use GitHub environment secrets or a local ignored env/keychain source only in explicit
  authorized lanes. Never provide live secrets to fork PRs or normal public CI.
- `docker compose config` output, workflow logs, test reports, screenshots, and artifacts
  must be scanned for tokens, private URLs, connection strings, endpoint fingerprints,
  and raw source content. Redact before upload; fail closed on a match.
- Use opaque provider IDs and model names only where needed for evidence. Never include
  a secret-bearing URL in an image label or cache key.
- Do not commit `.env`, database files, media, raw result roots, model artifacts, or
  `security/security_scorecard.json` if repository policy treats it as local output.

### Runtime isolation

- No app container gets `/var/run/docker.sock`, host filesystem mounts beyond an
  explicit temporary QA data root, host PID/network mode, or privileged mode.
- Use internal backend/data networks; publish only the selected frontend/QA ingress.
- Enforce non-root, `cap_drop: ALL`, `no-new-privileges`, read-only rootfs where
  compatible, bounded tmpfs, CPU/memory/pid limits, and explicit health checks.
- Use unique Compose projects and no fixed `container_name`; cleanup is project-scoped.
- Apply CORS, WebSocket origin, WebAuthn origin, auth token, and proxy trust as one
  tested boundary. Do not treat a browser opening as proof of authorization.

### GitHub and supply chain

- Default workflow permissions are `contents: read`; grant packages/attestations/OIDC
  only to the publication job that needs them.
- Pin third-party actions to reviewed immutable SHAs when the repository's security
  policy permits; keep action updates in a governed dependency process.
- Generate SBOM and provenance for trusted QA images; sign/attest only after the source
  SHA and generated Compose config are bound to the manifest.
- Do not use mutable image tags as acceptance identity. Verify image digest before use.
- Retain SARIF/security benchmark output as sanitized evidence and keep Scorecard,
  dependency review, secret scanning, and `security_benchmark.py` aligned.
- Run the tracked benchmark for workflow, connection, provider, auth, Docker, MCP,
  webhook, autoresearch, and agentic-memory changes; update the control matrix/docs/tests
  only when a control, evidence path, standard mapping, or trigger changes.

## 10. Staging contract and optional `multivac` adapter

CI and staging are different products:

- **CI:** ephemeral, automated, reproducible, public, no owner host dependency; may use
  contract-only or provisional synthetic runtime lanes.
- **Staging:** a running integrated environment with an explicit target, network/origin,
  secret source, provider, data retention, operator, and rollback; never assumed merely
  because a CI image built.

A generic staging adapter should implement these phases:

1. `inventory --read-only`: target identity, OS/container versions, disk/memory budget,
   active Compose projects, listeners/firewall evidence, current image/config digests,
   and available rollback handles. No mutations.
2. `preflight`: validate the public artifact digest, required ports/origins, secret
   availability, provider capability, free resources, and unique project name.
3. `prepare`: create only a new QA project/env/volume namespace. Do not modify or stop
   the old stack before acceptance.
4. `run`: start the selected artifact/profile, wait for health/readiness, seed the
   named synthetic corpus, and run bounded acceptance checks.
5. `accept`: record health, route/evidence, vector-space, project-isolation, Research
   Spine provisional/reconciliation, and browser/API evidence.
6. `rollback`: stop/remove only the new project and its volumes, restore the prior env
   or image references if changed, and re-run old-stack health. Rollback must be safe if
   `prepare` partially completed.

For `multivac`, the adapter remains owner-local and read-only-first. It must use a new
unique project name, loopback or an explicitly approved HTTPS/tunnel origin, the same
public image/Compose contract, and no committed host-specific values. The owner must
explicitly authorize any SSH command, provider call, secret use, host firewall/listener
change, or old-stack stop. The public plan/docs may describe the adapter's contract and
rollback but must not publish a private address, token, or endpoint fingerprint.

Acceptance must prove that the old stack was not mutated before the new stack passed its
preflight and that rollback removes only the new QA resources. If the host cannot meet
these conditions, mark staging blocked; do not weaken the public CI contract.

## 11. Human gate and PR promotion flow

The final promotion workflow should require:

1. exact `testing` source SHA and base `main` SHA;
2. successful feature-obligation report with zero unknown paths;
3. all required deterministic jobs green;
4. Compose render, image digest, SBOM/provenance, and contract-QA evidence green;
5. authorized live/staging evidence when the registry marks it required;
6. security benchmark and documentation parity evidence where triggered;
7. no forbidden artifacts or secrets;
8. a generated promotion manifest with command IDs, results, timestamps, artifact paths,
   image digest, residual risks, and rollback command;
9. a human approval recorded in a protected GitHub environment and as CF evidence.

Only after the protected environment approval may the workflow create the promotion PR.
The workflow must re-check the source SHA immediately before creation so an approval
cannot be replayed onto a different commit. The PR body should link the manifest and CF
spec/task evidence but must not contain private secrets or raw research data.

After PR creation:

- `main` branch protection reruns required checks on the PR merge ref;
- CODEOWNERS/human review is required;
- no bot merges, force-pushes, or bypasses branch protection;
- a changed SHA invalidates the promotion manifest and requires a new gate;
- failed main checks return the candidate to `testing` remediation rather than enabling
  a direct push.

Owner-gated open decisions are listed in §16. The implementation may not infer them from
existing workflow behavior.

## 12. Implementation phases and entry/exit gates

### Phase 0 — Baseline and contract inventory

**Entry:** owner-approved `CF-SPEC-56`, fresh CF gate baseline, clean scope boundary.

**Work:** confirm branch refs/protection, read current workflows/Compose/Dockerfiles,
refresh graph, inventory test ownership and feature-doc obligations, and reproduce
Compose/provider baseline without starting services.

**Exit:** baseline report, no new source changes, explicit inherited debt, registry
skeleton and command catalog accepted by implementer/reviewer.

**Verification:**

```bash
compass-forge gate before --task <phase-task>
python scripts/check_integrity.py
python scripts/check_ci_governance.py
python scripts/check_test_harness.py
python scripts/check_feature_obligations.py --base origin/testing --head HEAD --json-out artifacts/feature-obligations.json

docker compose -f docker-compose.yml config --quiet
```

**Rollback:** delete only untracked planning/baseline artifacts; no runtime mutation.

### Phase 1 — Registry and fail-closed obligation enforcement

**Entry:** baseline identifies registry ownership and command catalog.

**Work:** add schema, classifier, test ownership validation, generated-output policy,
feature-doc obligation mapping, stable JSON report, and focused tests.

**Exit:** a deliberately unclassified behavioral path fails; a registered representative
backend/frontend/route/agent/skill/model/test change selects the correct obligation
union; mechanical allowlist remains narrow.

**Verification:**

```bash
pytest tests/test_feature_obligations.py -q
python scripts/check_feature_obligations.py --base HEAD^ --head HEAD --json-out /tmp/feature-obligations.json
python scripts/check_ci_governance.py
python scripts/check_test_harness.py
```

**Rollback:** remove registry enforcement from branch protection only after owner
approval; retain report/tests so the registry can be corrected without disabling safety.

### Phase 2 — Public CI graph and evidence manifest

**Entry:** obligation classifier is deterministic and tested.

**Work:** add `testing` triggers, concurrency, path-aware job selection, artifact
allowlists, JUnit/JSON aggregation, sanitized manifest, retry/cancel behavior, and
least-privilege workflow permissions.

**Exit:** every required obligation has a job; skipped optional lanes are visible;
failed/cancelled runs cannot publish a green manifest; fork PRs cannot access live
secrets or registry write credentials.

**Verification:**

```bash
python scripts/check_ci_governance.py
python scripts/check_test_harness.py
python scripts/check_workflow_contracts.py
python scripts/check_public_tree_clean.py --base origin/testing --head HEAD
```

**Rollback:** revert workflow changes or remove only the new required check from branch
protection while preserving existing CI; do not bypass security/governance checks.

### Phase 3 — QA Compose/image and disposable lifecycle

**Entry:** CI graph selects QA obligations and artifact policy is approved.

**Work:** add QA Compose profiles, provider contract stub boundary, health/readiness,
unique project naming, reset/seed/collect/cleanup scripts, image digest/provenance/SBOM,
and contract-QA tests. Do not start runtime services until the implementation owner
explicitly authorizes the runtime verification step.

**Exit:** render/build contracts pass, contract-only stack is disposable and resettable,
resource/network/security policy is checked, and the artifact manifest binds image/config
hashes to the source SHA.

**Verification:**

```bash
docker compose -f docker-compose.qa.yml --profile contract config --quiet
docker compose -f docker-compose.qa.yml --profile synthetic config --quiet
pytest tests/test_qa_stack_contract.py tests/test_qa_reset_seed.py -q
python scripts/check_public_tree_clean.py --base origin/testing --head HEAD
# authorized implementation step only:
docker compose -p "istara-qa-${RUN_ID}" --profile contract up --wait
python scripts/qa_stack.py readiness --project "istara-qa-${RUN_ID}"
python scripts/qa_stack.py seed --project "istara-qa-${RUN_ID}" --slice coding-reliability
python scripts/qa_stack.py reset --project "istara-qa-${RUN_ID}" --confirm
```

**Rollback:** `qa_stack.py reset` deletes only the generated project namespace; revert
workflow/image/Compose changes without touching developer volumes or protected folders.

### Phase 4 — Provider-neutral and Research Spine runtime lanes

**Entry:** contract-only QA is green; no public CI live secret dependency.

**Work:** add explicit provider capability schema, chat/embed identity/dimension
readiness, route evidence, one-target live dispatch, provisional synthetic spine
scenarios, and negative/fail-closed tests.

**Exit:** contract-only and synthetic lanes never claim live/model quality; authorized
live lane passes with one configured target or reports a typed blocker; vector-space and
Research Spine gates remain load-bearing.

**Verification:**

```bash
pytest tests/test_model_provider_contract.py tests/test_research_validity_contract.py -q
pytest tests/pi_production/test_w8_embeddings_gateway.py tests/pi_production/test_engine_http_provider.py -q
python scripts/run_istara_evals.py --suite static
# manual owner-authorized only; one configured target:
ISTARA_LIVE_LLM_BASE_URL=... python scripts/test_llm_integration.py
```

The last command must use the existing ignored secret loader; the literal endpoint must
never be committed or included in logs. The implementation should document the actual
approved invocation without copying a private value.

**Rollback:** disable the live lane/profile and restore the prior adapter settings; do
not remove dimension checks or replace the provider with synthetic vectors.

### Phase 5 — Optional staging adapter

**Entry:** local deterministic and authorized runtime evidence is green; owner explicitly
approves an external target.

**Work:** implement generic inventory/preflight/prepare/accept/rollback adapter and, if
approved, run the owner-local `multivac` adapter read-only first with a new project.

**Exit:** staging evidence is separate from CI, old stack remains unchanged until
acceptance, rollback is proven, and no private target detail enters public artifacts.

**Verification:** adapter-specific read-only inventory, listener/firewall evidence,
health/vector-space/project-isolation/Research Spine checks, and rollback evidence. No
public generic command should contain a private host value.

**Rollback:** stop/remove only the new QA project and restore prior known-good references;
if inventory or preflight cannot prove isolation, stop without preparation.

### Phase 6 — Human gate and graduation

**Entry:** all required lanes green and evidence manifest complete.

**Work:** update living docs, attach CF evidence, record residual risks, request owner
approval through protected environment, create promotion PR only after approval, and
leave merge to a human.

**Exit:** owner approval, promotion PR, required main checks, docs parity, and rollback
instructions are all linked; no automatic merge/promotion bypass exists.

**Verification:**

```bash
python scripts/feature_docs.py --seed-missing --generate-site --check
pytest tests/test_feature_docs.py -q
compass-forge gate after --task <phase-task> --summary
compass-forge spec coverage CF-SPEC-56
compass-forge spec drift CF-SPEC-56
```

**Rollback:** close the promotion PR, restore branch-protection/workflow configuration
from the last known-good commit, and retain evidence/retro; never force-push or merge as
part of the automation.

## 13. Executable acceptance criteria

### Branch and human gate

- **Given** a feature branch changes a registered behavioral surface, **when** its PR is
  evaluated, **then** the obligation classifier selects the union of required checks,
  exposes the report, and blocks unknown/unowned paths.
- **Given** all required `testing` checks and the QA artifact manifest are green, **when**
  no owner approval exists for that exact SHA, **then** no workflow creates a PR to
  `main`, changes `main`, or promotes an artifact.
- **Given** a protected human approval binds SHA, digest, evidence, and target base,
  **when** the source SHA is unchanged, **then** the workflow may create one promotion
  PR and must not merge it.
- **Given** the source SHA changes after approval, **when** promotion is attempted,
  **then** the workflow fails closed and requires a new approval.

### Coverage registry

- **Given** a new route/store/menu/agent/skill/model/test behavior path with no registry
  owner, **when** `check_feature_obligations.py` runs, **then** it exits nonzero and
  names the unclassified path and required registry update.
- **Given** a registered feature changes, **when** the classifier emits JSON, **then**
  every required command, test owner, docs obligation, security trigger, and optional
  lane is present with a reason.
- **Given** a generated feature-doc file changes without its source or declared
  generator run, **when** the check runs, **then** it fails rather than accepting drift.

### Deterministic tests

- **Given** a backend-only change, **when** the registry selects backend obligations,
  **then** targeted backend/auth/project-scope/research tests and relevant governance
  checks run; live services are not started by default.
- **Given** a frontend/shared behavior change, **when** the registry selects frontend
  obligations, **then** lint, type, unit, mutation/build and relevant feature-doc checks
  run; full browser QA is selected only if the feature declares it.
- **Given** a test-harness or CI change, **when** the registry evaluates it, **then**
  harness governance, workflow contracts, static runner checks, and the security
  benchmark trigger logic run.

### Docker and disposable QA

- **Given** a supported Compose version and no provider secret, **when** the contract QA
  profile renders/starts, **then** it runs without Ollama/LM Studio/local model services
  and reports contract-only status.
- **Given** a QA run ID, **when** the stack is created twice, **then** each run has a
  unique project/volume namespace and reset of one run cannot remove the other.
- **Given** a failed or cancelled run, **when** cleanup executes, **then** only the
  generated project namespace is removed and sanitized evidence records cleanup status.
- **Given** an image artifact, **when** the manifest is verified, **then** its digest,
  source SHA, Compose hash, dependency hashes, provenance, SBOM, and provider mode
  match; a mutable tag alone is insufficient.

### Provider and vector safety

- **Given** an authorized live configuration lacks a chat/embedding identity, secret,
  capability, or expected dimension, **when** readiness runs, **then** it fails closed
  with a typed reason and makes no fallback request.
- **Given** chat and embedding targets are explicitly configured, **when** readiness and
  the embedding probe run, **then** exact provider/model identity, dimensions,
  `assert_vector_space_invariant`, and route evidence are recorded without secret or
  content leakage.
- **Given** the selected provider is unavailable, **when** a retry occurs, **then** it
  retries the same target within its budget or fails; it does not silently switch
  vector spaces or load another model.

### Research Spine and governance

- **Given** the synthetic canonical corpus is seeded, **when** provisional QA runs,
  **then** raw source spans become evidence units, independent coding/reliability and
  low-consensus reconciliation state are exercised, and all outputs remain provisional
  until their gates pass.
- **Given** an In Review task or unreconciled code application, **when** reportability is
  checked, **then** the report route excludes it and identifies the missing gate.
- **Given** a self-improvement candidate succeeds at tool execution only, **when** QA
  records telemetry, **then** it cannot become a positive model/skill signal or
  report evidence without verification, governance, and Research Spine acceptance.

### Security and privacy

- **Given** a fork PR, **when** CI runs, **then** it has no live-provider secret,
  registry-write permission, host Docker socket, or private target access.
- **Given** an artifact/log/config is collected, **when** redaction and public-tree checks
  run, **then** tokens, private URLs, connection strings, raw research content, local
  databases, media, model files, and ignored runtime outputs are rejected.
- **Given** a Compose stack is running, **when** network/listener policy is inspected,
  **then** only intended ingress is published and backend/data services remain internal.

## 14. Verification and evidence artifact contract

Every implementation task must attach exact command evidence to Compass Forge and include
these artifacts in the build manifest where applicable:

- `feature-obligations.json`: base/head, matched IDs, selected obligations, unknown paths,
  owners, commands, and reasons;
- `compose-rendered.yaml` only after secret redaction and with no private endpoint values;
- `compose-config.sha256` and `docker-image-digest.txt`;
- `qa-readiness.json`: health/readiness/provider mode, model identity, dimension,
  route handles, project ID, and omission/redaction status;
- `junit.xml`, static-check JSON, mutation/property summary, security scorecard, and
  feature-doc check output;
- `research-spine-qa.json`: source/evidence-unit/coding/reliability/reconciliation/
  review/report-gate statuses with handles only;
- `promotion-manifest.json`: exact source/base SHA, image digest, required checks,
  artifact hashes, residual risks, rollback command, CF spec/task/evidence refs, and
  human approval record;
- sanitized service logs only on failure, with explicit retention and cleanup status.

Compass Forge evidence should include, at minimum:

```bash
compass-forge task evidence <task> --type command --summary "<lane>" \
  --payload-json '{"command":"<exact command>","result":"passed","artifact":"<path>"}'
compass-forge task evidence <task> --type gate --summary "post-change architecture gate" \
  --payload-json '{"command":"compass-forge gate after ...","result":"passed or inherited-debt","artifact":"<gate report>"}'
```

The final self-report must disclose errors introduced and corrected, corrections received,
residual risks, and whether the artifact is ready. A reviewer must record an independent
verdict; a live/full change requires the blind-review protocol from Build Stream.

## 15. Alternatives, failure modes, architecture debt, and rollback

### Alternatives considered

| Alternative | Benefit | Rejection / bounded use |
|---|---|---|
| Do nothing; keep current CI and Compose | Lowest immediate change | Leaves feature obligations manual, no disposable public QA artifact, and no explicit promotion gate. Not acceptable as the target. |
| Extend the benchmark overlay only | Reuses existing testing-oriented files | Benchmark and full-feature QA have different goals; overlay does not by itself provide a canonical registry, branch gate, provider-neutral contract, or image provenance. Use as input, not sole source. |
| Provider-specific CI (for example, owner-host model server) | Easy live smoke path | Violates public/host-agnostic contract, leaks availability assumptions, and makes forks/non-owner developers second class. Keep only as authorized adapter. |
| Self-hosted runner for every test | Can reach Docker, private network, and models | Expands trust boundary, couples CI to one host, and risks secret/data contamination. Use only for opt-in staging after generic CI is green. |
| Ephemeral GitHub-hosted runner + contract stub | Public, reproducible, least dependency | Cannot prove real model quality; pair with optional authorized live lane and honest labels. Recommended default. |
| Permanent shared staging stack as CI target | Rich runtime behavior | Flaky, stateful, difficult to isolate, and can mutate owner data. Keep staging separate and use unique namespaces/reset. |
| Automatic PR/merge after green CI | Fast throughput | Violates owner gate and weakens accountability. Allow promotion PR creation only after explicit human approval; never auto-merge. |
| Separate per-feature workflow files | Local ownership | Duplicates orchestration and can create contradictory obligations. Use one registry/command catalog with reusable workflow jobs. |

### Failure modes and mitigations

- **Unknown path passes through:** fail-closed classifier; registry test with synthetic
  new path; branch protection requires classifier.
- **A matched feature omits a related route/test/docs surface:** require ownership
  coverage tests, Compass graph review, and explicit registry review for dynamic paths.
- **A contract stub is mistaken for live validity:** mode labels, separate check names,
  promotion rule forbidding contract-only satisfaction of live obligations, and reviewer
  acceptance criteria.
- **Provider fallback changes vector space:** exact target binding, fallback disabled in
  QA, invariant probe, typed failure, negative tests.
- **Model download or multiple heavy loads:** no model service in default contract
  profile, one-target live dispatch, no discovery loops, bounded resource limits.
- **Compose project collision/data leak:** generated project names, no fixed containers,
  project-scoped volumes, reset idempotency and cross-project test.
- **Secret in config/artifact/cache:** redaction test, secret scan, no URL labels/cache
  keys, fork jobs without secrets, artifact allowlist.
- **CI says green after cancellation/retry:** immutable SHA/run manifest, concurrency
  cancellation recorded as failure/incomplete, new project and evidence on retry.
- **`staging` force-sync bypasses review:** classify it as a mirror or replace it with
  an owner-approved workflow; never call it pre-main approval while current behavior
  force-pushes from `main`.
- **Existing gate debt obscures new drift:** capture baseline, compare after, cite
  inherited findings, and create separate tasks for unrelated remediation.
- **Canonical corpus becomes a hidden fixture shortcut:** manifest validation, named
  slices, raw-span checks, provisional status, and report-gate negative cases.
- **Multivac old stack is mutated prematurely:** read-only inventory, unique project,
  preflight/accept barrier, explicit rollback handles, owner authorization.

### Architecture debt to report, not conceal

1. Existing local-provider defaults in Compose/runtime paths may remain useful for local
   development but must not be the public QA readiness prerequisite.
2. The current path-pattern governance model and test-ownership graph are not the same
   as a feature registry; migration should preserve old checks until parity is proven.
3. The current branch/workflow documentation has inconsistent descriptions of `testing`,
   `staging`, and main promotion; docs and branch protections must be reconciled.
4. Existing gate failures (import cycles, secret-flow findings, large-file findings,
   route/type drift) are separate baseline debt unless the new implementation introduces
   or touches them.
5. Full browser/real-user/live-provider QA remains environment-bound and cannot be made
   a normal public PR requirement without an approved public test provider and resource
   budget.

### Rollback hierarchy

- **Registry only:** revert registry/classifier commit; keep the old governance checks
  required until the replacement has a green parity run.
- **Workflow only:** disable new optional jobs or revert workflow commit; do not remove
  existing security/governance checks.
- **QA artifact:** stop/remove only the generated Compose project and its volumes; retain
  digest/evidence for diagnosis; never use broad Docker prune.
- **Provider contract:** disable the live profile and restore prior explicit adapter
  configuration; never remove invariant/fail-closed checks.
- **Staging adapter:** stop new QA project, remove only its namespace, re-check old stack,
  and restore prior image/env references; if old-stack health is not proven, stop and
  escalate to owner rather than guessing.
- **Promotion:** close/revert the unmerged promotion PR; no force-push to `main` and no
  automatic merge.

## 16. Likely files and surfaces changed by implementation

This is a planning inventory, not permission to edit all paths.

### CI and governance

- `.github/workflows/ci.yml`
- new `.github/workflows/qa-artifact.yml` and/or
  `.github/workflows/promote-testing.yml`
- `.github/CODEOWNERS`, branch/environment documentation, and repository settings
  outside the repository (owner-gated)
- `testing/feature_coverage.yml`
- `scripts/check_feature_obligations.py`
- `scripts/check_change_obligations.py`
- `scripts/check_ci_governance.py`
- `scripts/check_test_harness.py`
- `scripts/check_public_tree_clean.py`
- new workflow/obligation contract tests

### Runtime and artifact

- `docker-compose.qa.yml` or equivalent
- `backend/Dockerfile`, `frontend/Dockerfile`, `relay/Dockerfile` only if image
  hardening/provenance/runtime issues are demonstrated
- `.dockerignore` files
- new `scripts/qa_stack.py`, `scripts/qa_seed.py`, or a tightly scoped equivalent
- `scripts/reset_test_environment.py` only if a thin project-safe integration is needed
- provider adapter/configuration surfaces under `backend/app/config.py` and
  `backend/app/core/pi_runtime/`
- provider/vector tests under `tests/test_model_provider_contract.py` and
  `tests/pi_production/test_w8_embeddings_gateway.py`

### Tests and research/governance evidence

- `tests/test_feature_obligations.py`
- `tests/test_qa_stack_contract.py`
- `tests/test_qa_reset_seed.py`
- `tests/test_project_scope_contracts.py` and harness guards if the runner changes
- `tests/test_research_validity_contract.py` and relevant `tests/pi_production/`
- canonical corpus manifest/selector tests, never raw corpus artifacts in public output
- security benchmark package only if controls/evidence/trigger patterns change

### Documentation

- `README.md`, `README.pt-BR.md`
- `TESTING.md`, `testing/TESTING_STRATEGY.md`, `testing/TEST_HISTORY.md` when a run is
  release-relevant
- `CHANGE_CHECKLIST.md`, `Tech.md`, `DOCUMENTATION.md`, `CONTRIBUTING.md` as required
  by the final contract
- relevant `docs/features/content/*/architecture.md`, inventory, glossary, and generated
  site only if feature/test behavior or feature-doc inventory changes
- a living QA how-to/reference document under `docs/` if the repository convention
  requires a separate runtime guide

Do not touch the unrelated `docs/features/site/manifest.json` modification as part of
this initiative; reconcile it separately through its owner/task.

## 17. Open owner-gated decisions

The implementer must not silently decide these boundary questions:

1. Is `testing` the required integration target for all feature PRs, or may selected
   feature classes target `main` directly after the same checks?
2. Is `staging` retained as a post-main mirror, changed into a protected pre-main branch,
   or retired from the promotion narrative? The current force-sync workflow is not a
   human gate.
3. Which GitHub environment/reviewer(s) can approve promotion, and is a manual workflow
   allowed to create the promotion PR after approval?
4. What are the approved artifact registry and retention values, and are fork PR image
   artifacts saved to Actions only or published to a public registry?
5. Which Compose version/platform matrix is the supported public contract, and what is
   the maximum CI runtime/resource budget for contract and synthetic QA?
6. Is the deterministic provider stub allowed to run in a public Compose container, or
   must all contract tests remain in-process? Either choice must retain contract-only
   labels and must not imply model quality.
7. Which authorized live provider profile and embedding dimension may be used for owner
   QA, and where is its secret stored? No private value belongs in this repo or plan.
8. Which full-feature obligations are blocking on `testing` versus owner-authorized
   staging only (MCP, relay, autoresearch, observability, voice, browser, and live LLM)?
9. Should registry ownership be by feature team, subsystem owner, or CODEOWNERS path,
   and who resolves overlapping/dynamic registrations?
10. Are third-party action SHA pinning, SBOM signing, and provenance attestations required
    before the first public artifact or staged as a separate security phase?
11. What is the supported retention policy for QA logs/screenshots/traces, and which
    sanitized evidence may be linked from a public PR?
12. Does the public branch need a provider-backed live smoke at all, or is the initial
    acceptance bar contract-only plus optional owner-authorized live/staging evidence?

## 18. Handoff summary

This draft recommends the smallest coherent public architecture: a registry-driven
fail-closed obligation check, an ephemeral provider-neutral Docker QA artifact, a
separate authorized live/staging contract, and an owner-gated promotion workflow. It
reuses existing governance/test/provider/Research Spine contracts rather than creating a
parallel test system. The next planning action is MECE synthesis with Architect B's CI
mechanics and Architect C's runtime/provider/security design. Implementation must wait
for the winning master plan and explicit owner approval recorded by the Conductor.
