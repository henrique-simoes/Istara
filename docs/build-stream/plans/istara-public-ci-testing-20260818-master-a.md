# Istara Public CI, Testing Branch, and Disposable QA — MECE Master Plan Candidate A

- **Task:** `ISTARA-PUBLIC-CI-TESTING-20260818-MASTER-A`
- **Spec:** `CF-SPEC-56`
- **Pipeline:** `ISTARA-PUBLIC-CI-TESTING-20260818`
- **Lifecycle:** `docs/build-stream/2026-08-18-istara-public-ci-testing-automation.md`
- **Planning phase:** `synthesize` (sole synthesis round)
- **Candidate slot:** `a`
- **Status:** candidate for cross-vote; implementation is not authorized by this artifact

> This is a planning artifact. It proposes no source, workflow, Compose, test, generated-doc,
> runtime, provider, host, or production mutation in the planning stage. Commands below are
> implementation contracts unless explicitly marked as evidence observed in the current
> repository. Live provider calls, model loading, Docker/application startup, staging, and
> `multivac` access remain owner-authorized later-stage actions only.

## 1. Executive summary and outcomes

Istara has substantial deterministic coverage and several strong safety contracts, but its
public delivery path is not yet current-by-construction. The repository already separates
CI-safe and live/environment-bound testing (`TESTING.md`), runs governance and security jobs
(`.github/workflows/ci.yml`), validates provider/embedding contracts, and encodes the Research
Spine in architecture documentation and production tests. The missing connective tissue is a
single enforceable coverage model, a public testing-branch lifecycle, an isolated Docker QA
artifact, and an approval boundary that cannot be crossed by a green bot alone.

This plan establishes one coherent system:

1. Short-lived feature branches target a protected public `testing` integration branch.
2. One declarative feature/subfeature registry and one evaluator map every changed behavioral
   path to the union of deterministic, documentation, security, runtime, and human-review
   obligations. Unknown or unowned behavior fails closed.
3. CI runs cheap deterministic and governance checks before progressively more expensive
   contract, Compose, image, disposable-stack, synthetic, simulation, E2E, and authorized
   runtime lanes. A skipped optional lane is visible and never counted as a pass.
4. A dedicated, provider-neutral QA Compose artifact is reproducible and disposable on any
   supported Docker host. It uses unique project/volume namespaces, no fixed container names,
   no private endpoint, and no model download in its public default profile.
5. Contract-only and synthetic-provisional lanes prove only their actual contracts. A full
   feature/runtime claim requires an explicitly authorized provider target, exact model and
   embedding identity, readiness evidence, and the existing vector-space invariant.
6. Synthetic research data follows Sources -> Evidence Units -> independent coding ->
   reliability/grounding -> reconciliation -> review gates, but remains visibly provisional
   and cannot become reportable evidence or a self-improvement signal.
7. Optional staging adapters, including an owner-local `multivac` adapter, are separate from
   CI, read-only-first, uniquely named, firewall/origin-audited, and rollback-scoped. The
   private adapter is never the official public path and its private details do not enter
   public workflows or documentation.
8. A green evidence manifest opens a protected human approval gate. Only approval bound to the
   exact source SHA, target base, image digest, and evidence bundle permits creation of a PR
   from `testing` to `main`; the PR still requires normal human review and is never auto-merged.

### Developer outcome

Any contributor can run the deterministic commands and disposable contract/synthetic QA
artifact without Ollama, LM Studio, a cloud vendor, `multivac`, owner credentials, hidden
host paths, or a model download. Failure output identifies the changed feature, selected
obligation, command, lane, owner, and sanitized artifact.

### Maintainer outcome

Maintainers get a public, auditable branch state machine, a fail-closed test-ownership
contract, immutable QA provenance, explicit provider safety, Research Spine-valid evidence,
security controls, and a human-controlled promotion boundary. The system is honest about
what it has not proved: a stub is not model quality, a synthetic run is not report evidence,
and a staging result is not public CI reproducibility.

## 2. Goals, non-goals, assumptions, and constraints

### Goals

- Make `testing` the documented public integration/QA branch, subject to owner decisions in
  §19, with protected `main` as the human-reviewed promotion target.
- Detect every new or changed behavioral feature/subfeature and select its required checks
  from a versioned, reviewable registry.
- Preserve and orchestrate current backend, frontend, relay, simulation, E2E, benchmark,
  mutation/property, governance, documentation, security, and provider contracts.
- Produce a reproducible, host-agnostic, per-run disposable Docker QA artifact with digest,
  provenance, SBOM/attestation policy, seed/reset/audit, redacted evidence, and retention.
- Preserve `assert_vector_space_invariant`, embedding dimensions, exact provider/model
  identity, centralized secret handling, fail-closed provider behavior, and no hidden model
  loading or fallback.
- Validate the Research Spine and self-improvement governance rather than inventing a
  benchmark-specific parallel data path.
- Separate deterministic CI, authorized live provider QA, staging, and optional private
  adapters so each result has a truthful claim boundary.
- Require explicit human approval after automated evidence is green and before a promotion PR
  is created or `main` is changed.

### Non-goals

- No product behavior rewrite, broad refactor, provider migration, production deployment, or
  replacement of the existing test estate.
- No Docker/application startup, live provider request, model load/download, `multivac` access,
  PR creation, merge, push, or production mutation during planning.
- No provider-specific public CI dependency, private endpoint fingerprint, credential, token,
  or host-network discovery.
- No synthetic vector or stub result may be presented as full-feature model or research
  validity evidence.
- No automatic merge, automatic promotion, or inferred owner approval.
- No cleanup, pruning, movement, or mounting of `LLMs/` or `Model_Finetuning/`.
- No attempt to fix unrelated inherited gate debt unless an implementation task explicitly
  owns it; new drift must still be detected and fixed or explicitly dispositioned.
- No public documentation may make the private adapter an official test/staging path or
  disclose its private endpoint, topology, credentials, or fingerprints.

### Assumptions to verify during implementation

- Repository settings permit a protected `testing` branch, protected `main`, CODEOWNERS, and
  a human-approved environment or equivalent manual gate. These settings are **UNVERIFIED**
  from repository files and require owner confirmation.
- Supported GitHub-hosted runners can run deterministic lanes and bounded Compose contract QA.
  If a service-container/buildx strategy is required, it must not expose a product container
  to the host Docker socket.
- `tests/document_corpus/canonical/` and its manifests are the governed synthetic-corpus
  source. Counts and slice names must be discovered during implementation, not assumed from
  this plan.
- Existing provider surfaces can expose separate chat and embedding identities, or an
  additive contract will be needed. If they cannot, the live lane fails closed.
- A public registry is optional for fork PRs. Untrusted PRs may upload a saved/sanitized
  Actions artifact but receive no registry-write or live-provider credentials.
- The exact Compose version/platform support matrix, image registry, SBOM tool, retention
  periods, and live target are owner-gated decisions (§19), not inferred defaults.

### Constraints and governing contracts

- `AGENTS.md` prohibits private endpoint disclosure, unapproved active model loading, external
  mutation, and protected-artifact cleanup.
- `docs/architecture/research-validity-contract.md` is the system-wide research-validity
  contract, including benchmarks, simulations, chat, integrations, compute, and future paths.
- `docs/architecture/self-improvement-governance-contract.md` governs telemetry, ReasoningBank,
  Memento, Autoresearch, Meta-Hyperagent, RAG/GraphRAG, and promotion of process signals.
- `scripts/check_public_tree_clean.py` is the public-tree hygiene boundary for data, models,
  databases, media, results, local config, and related artifacts.
- Security-sensitive auth, provider, connection, Docker, MCP, webhook, autoresearch,
  self-evolution, and agentic-memory changes trigger the tracked benchmark:
  `python scripts/security_benchmark.py --fail-on-threshold`.
- UI/menu/route/store/agent/skill/model/test behavior changes must keep living feature docs
  and generated site/manifests synchronized using the repository's feature-doc command.
- The unrelated `docs/features/site/manifest.json` working-tree modification remains isolated
  from this initiative.

## 3. Current-state evidence and gaps

The following is a synthesis of repository evidence cited by the three architect drafts. It is
not a claim that the target architecture already exists. Implementation begins with a fresh
baseline and re-checks each item at the chosen base SHA.

| Surface | Evidence observed or cited | Gap / planning implication |
|---|---|---|
| Public CI | `.github/workflows/ci.yml` has governance, backend, frontend, JavaScript-harness, and desktop jobs and targets `main`/`staging`. | No first-class public `testing` lifecycle, feature-obligation report, QA artifact manifest, or protected promotion job is established by the cited workflow. |
| Existing governance | `scripts/check_ci_governance.py`, `scripts/check_test_harness.py`, `scripts/check_integrity.py`, `scripts/check_change_obligations.py`, and `scripts/check_public_tree_clean.py` exist. | Existing path/pattern gates must be preserved and extended through one evaluator, not replaced by a competing registry implementation. |
| Feature docs | `scripts/feature_docs.py --seed-missing --generate-site --check` exists and the repository requires parity for UI/menu/route/store/agent/skill/model/test behavior. | The change-obligation report must make documentation parity an explicit selected obligation and isolate unrelated manifest edits. |
| Testing guidance | `TESTING.md`, `testing/TESTING_STRATEGY.md`, `pytest.ini`, and live-test configuration distinguish deterministic CI from `live_llm`, `e2e`, `simulation`, and other environment-bound lanes. | Guidance is not yet the single machine-readable selector for every changed feature. |
| Compose | `docker-compose.yml` already contains internal networks, healthchecks, `read_only`, `cap_drop`, `no-new-privileges`, pids/resources, and deployment profiles. | It also carries local/deployment assumptions, fixed names or persistent resources that need review, and is not yet a public disposable QA contract. The cited `docker compose -f docker-compose.yml config --quiet` check reports an inherited `pids_limit`/`deploy.resources` compatibility conflict in the current environment; implementation must reproduce/refute it before relying on the file. |
| Images | `backend/Dockerfile`, `frontend/Dockerfile`, and `relay/Dockerfile` provide build surfaces. | No single public QA image identity, digest/provenance/SBOM manifest, retention, or fork-publication policy is defined in the cited evidence. |
| Provider identity | `backend/app/api/routes/llm_servers.py`, `backend/app/config.py`, `backend/app/core/pi_runtime/`, and `tests/test_model_provider_contract.py` expose provider/model/configuration contracts. | QA needs an explicit capability/readiness evidence schema for chat and embeddings and a no-fallback, one-target authorization boundary. |
| Embedding safety | `backend/app/core/pi_runtime/embeddings_gateway.py::assert_vector_space_invariant` and `backend/app/core/embedding_validation.py` enforce model/dimension and response-shape safety; `tests/pi_production/test_w8_embeddings_gateway.py` covers relevant invariants. | Every live/runtime lane must invoke or prove the existing invariant; no shortcut may replace it with a fake dimension or disabled gate. |
| Research Spine | `docs/architecture/research-validity-contract.md`, `backend/app/services/research_validity_service.py`, `backend/app/core/research_validity.py`, `tests/test_research_validity_contract.py`, and `tests/pi_production/test_w3_research_spine.py` provide the validity/gating surface. | QA seed/reset must use raw source spans and real evidence-unit/coding/reliability/reconciliation paths while making synthetic outputs non-reportable and provisional. |
| Self-improvement | `docs/architecture/self-improvement-governance-contract.md`, `backend/app/core/agent_research.py`, `backend/app/core/meta_hyperagent.py`, and `backend/app/core/telemetry.py` are governed surfaces. | QA must prevent raw tool success or synthetic shortcuts from creating strong positive skill/model signals or report evidence. |
| Security | `security/control_matrix.json`, `security/SECURITY_BENCHMARK.md`, `scripts/security_benchmark.py`, and `tests/test_security_benchmark.py` provide a tracked benchmark. | New QA controls/evidence/trigger patterns require synchronized security matrix/docs/tests; otherwise reuse the existing benchmark without inventing a parallel score. |
| Branch/staging | `.github/workflows/sync-staging.yml` force-syncs `main` to `staging` after pushes; existing docs describe branch behavior inconsistently. | `staging` must not be called a pre-main approval branch unless the owner replaces the mirror contract. The target state machine uses `testing` for integration and a separate human gate for promotion. |
| Prior readiness | `docs/build-stream/2026-08-17-istara-testing-docker-readiness.md` records earlier Compose, origin, persistence, provider, and local-model concerns. | It is diagnostic planning material, not proof. Re-run its relevant checks on the implementation base and carry unresolved risks as tasks. |
| Current CF health | The refreshed CF snapshot still reports inherited Python import-cycle, secret-flow, and large-file failures plus warnings; the snapshot reports no new issues relative to its baseline. | Phase 0 must capture the baseline and compare post-change output. Do not attribute unrelated inherited debt to this initiative or silently suppress new findings. |

### Confirmed gaps that the implementation must close

1. No single registry currently owns feature/subfeature -> test/documentation/runtime
   obligations with fail-closed unknown-path behavior.
2. No explicit `testing` branch state machine and human-gated promotion-PR contract is
   represented in a protected workflow.
3. No dedicated public disposable QA Compose artifact with a documented seed/reset/audit and
   per-run namespace contract is evidenced.
4. No public evidence schema cleanly distinguishes contract-only, synthetic-provisional,
   authorized-live, and staging claims.
5. No end-to-end manifest binds changed-path obligations, exact SHA, Compose hash, image digest,
   provider mode, security evidence, and human approval.

### Unverified blockers to resolve before implementation

- Exact branch protections, environment approvers, action permissions, and whether a workflow
  may create a `testing` -> `main` PR after approval.
- Exact supported Docker Compose version and how to resolve the current `pids_limit` conflict
  without weakening resource/security controls.
- Whether ingestion can create evidence units without a provider call in a contract/synthetic
  stack; if not, define a clearly labeled deterministic test adapter at the ingestion boundary.
- Current `.gitignore` alignment for QA runtime outputs and the available SBOM/attestation tool.
- Actual private staging target surface and permissions. Do not guess it from the name of the
  owner-local adapter.

## 4. Target architecture and authoritative boundaries

### 4.1 One source of truth for coverage and capabilities

Create or extend one canonical, versioned registry (provisionally
`testing/feature_coverage.yml`; use an existing repository convention if implementation
inspection finds one) containing both feature obligations and runtime capability declarations.
Do **not** create independent `testing/feature_coverage.yml` and
`qa/runtime_capabilities.json` files that can disagree. A generated or validated JSON report
may be emitted for CI, but it is derived output, not another authority.

The existing `scripts/check_change_obligations.py` remains the compatibility entry point and
is extended or refactored into the one evaluator. A separate wrapper is acceptable only if it
calls the same evaluator and preserves current checks. The implementation command contract is:

```bash
python scripts/check_change_obligations.py \
  --base "$BASE_SHA" --head "$HEAD_SHA" \
  --coverage-registry testing/feature_coverage.yml \
  --json-out artifacts/feature-obligations.json
```

The exact option names may follow the existing script, but CI must have one authoritative
selection result. Existing path-pattern checks remain active during migration; replacement
requires a parity run and owner approval.

Minimum registry shape:

```yaml
schema_version: 1
command_catalog:
  backend_contracts:
    command: "pytest <selected backend tests> -q"
    owner: "backend-owner"
    deterministic: true
    artifact: "junit/backend.xml"
    live_authorization: none
features:
  - id: research.validity.coding
    owner: research-owner
    test_owner: research-test-owner
    paths:
      - backend/app/services/research_validity_service.py
      - backend/app/core/research_validity.py
      - tests/pi_production/test_w3_research_spine.py
    obligations:
      deterministic: [backend_contracts, research_spine_contract]
      synthetic: [provisional_spine_qa]
      security: []
      docs: [feature_docs_when_behavior_changes]
      live: none
    capability: {chat: false, embeddings: false, spine: true}
    generated_by: null
    risk: data-trust-boundary
```

Required registry properties:

- Stable feature and subfeature IDs, owner and test-owner identities, path globs, risk class,
  commands from a pinned command catalog, artifact owners, and documentation obligations.
- Separate fields for deterministic, contract-only, synthetic-provisional, authorized-live,
  staging, security, mutation/property, E2E, and human-review obligations.
- Explicit chat/embedding capability declarations: provider kind, API shape, exact model
  identity requirements, dimension requirement, readiness evidence, and fallback policy.
- Source ownership for generated outputs and an explicit generator command; generated-only
  changes fail if their source/registry relationship is absent.
- A narrow, reviewed mechanical allowlist for license/version/spelling/generated-only changes;
  it cannot cover product behavior, providers, security, routes, tests, or workflow logic.
- `introduced_in`, `last_verified_sha`, and registry schema version so stale entries are
  visible rather than silently rewritten by CI.
- No secrets, endpoints, raw research, private host values, or model download instructions.

### 4.2 Feature-obligation algorithm

`check_change_obligations.py` (or its one shared evaluator) performs the following fail-closed
algorithm:

1. Resolve `BASE_SHA` and `HEAD_SHA`, enumerate added/modified/deleted paths, normalize path
   separators, and evaluate deleted paths against their previous owners.
2. Classify paths into product source, test, docs, generated, workflow, provider, security,
   runtime-data, artifact, or unknown zones. Use Compass Forge graph output as a starting map,
   then inspect dynamic/string-keyed registrations when adding or changing entries.
3. Match each path against all intentionally overlapping registry entries. Missing owner,
   missing test owner, or overlapping entries without an explicit union reason is an error.
4. Add cross-cutting obligations: workflow/CI changes require workflow and governance checks;
   provider, embeddings, auth, connection, WebSocket, MCP, webhook, Docker, autoresearch,
   self-evolution, or agentic-memory changes trigger the security benchmark as configured;
   test-harness changes require harness governance; UI/menu/route/store/agent/skill/model/test
   behavior changes require feature-doc parity.
5. Require a same-change registry declaration for a new behavioral path. An unknown path,
   missing test owner, missing documentation owner, unapproved generated artifact, or forbidden
   public artifact exits nonzero before expensive jobs.
6. Compute the union of required lanes, deduplicate commands by catalog key, and mark optional
   lanes as `selected`, `not_selected` with a reason, or `blocked` with a typed reason.
7. Emit stable JSON containing base/head, changed paths, matched feature IDs, obligations,
   command keys, owners, reasons, skipped/blocked lanes, unknown paths, required artifacts,
   registry version, and report hash.
8. Pass exactly that report to downstream jobs. A workflow must not hand-author a narrower
   matrix than the classifier selected.
9. Validate the report itself against its JSON schema and ensure a failed/cancelled command
   cannot be rendered as green.

The report is evidence of selection, not evidence that a test passed. Every selected command
must produce a result row and an allowlisted artifact or an explicit, visible failure.

### 4.3 Branch and CI state machine

Recommended topology:

```text
feature/<name> -- deterministic checks --> PR to testing
       |                                      |
       +-- local obligation report ---------->|
                                              v
                                    protected testing integration
                                              |
                              selected CI + QA artifact + manifest
                                              |
                              protected human-promotion environment
                                              |
                              exact SHA/digest/evidence approval
                                              |
                         workflow creates testing -> main promotion PR
                                              |
                             fresh main checks + CODEOWNERS review
                                              |
                                      human merge to main

optional: main -> staging mirror only (not a pre-main approval gate)
```

States and transitions:

1. **Feature branch.** Branch from the owner-approved base (`testing` by default). A normal
   feature PR may target `testing`; its classifier and selected checks must be green. No direct
   push to protected `testing`.
2. **Testing integration.** The public long-lived branch receives feature PRs and runs the
   union of selected checks plus the cross-feature suite. A push is an immutable source SHA,
   not a mutable artifact identity.
3. **QA candidate.** A green `testing` SHA has a complete obligation report, test-result bundle,
   Compose-render hash, image digest/provenance, security/docs evidence, and residual-risk
   summary. It is not a release and cannot create a `main` PR yet.
4. **Human gate.** A protected environment/manual action accepts or rejects the exact candidate.
   Approval binds source SHA, current `main` base SHA, report hash, image digest, and required
   artifacts. Approval is recorded in the workflow and Compass Forge evidence/ledger.
5. **Promotion PR.** Only the post-approval job may create exactly one PR from `testing` to
   `main`. It re-checks the SHA immediately before creation and fails closed if it changed.
   It has narrowly scoped write permission and no merge permission.
6. **Main PR.** Main branch protection reruns required checks on the merge ref and requires
   CODEOWNERS/human review. A bot never merges, force-pushes, or bypasses protections.
7. **Staging.** A separate, owner-authorized runtime environment. The current force-sync
   `staging` workflow must either remain a documented post-main mirror or be replaced by a
   separately protected pre-main contract; it is not a human gate by implication.

Failure/retry rules:

- PR runs use `concurrency` keyed by workflow/ref/change class; cancelled runs cannot publish
  a green manifest.
- Retries use the same source SHA but a new run/attempt and unique Compose project/artifact
  namespace. No previous green result is reused by branch name alone.
- A failed health, test, scan, or cleanup step produces a visible typed failure and sanitized
  artifacts. Cleanup failure is an incident, not permission for a broad Docker prune.
- Fork PRs use read-only permissions, no live secrets, no private target access, and no image
  registry write. They can run contract-only lanes and upload short-retention saved artifacts.

## 5. Complete automated test pyramid and execution matrix

The workflow is a dependency graph, not a single opaque “CI” command. Cheap deterministic
checks run first; expensive or authorized checks run only after their prerequisites. The
registry selects the minimum required union for a change, while `testing` runs the broader
cross-feature suite.

| Order | Lane | Trigger | Proves | Does not prove | Required evidence |
|---:|---|---|---|---|---|
| 0 | Diff/obligation classifier | Every PR/push | Every path is owned and selected obligations are complete | Runtime behavior | `feature-obligations.json` |
| 1 | Public-tree/secret/artifact guard | Every PR/push | No forbidden files, tokens, private endpoints, local data, model artifacts, or unsafe outputs | Product behavior | sanitized scan JSON |
| 2 | Governance/docs parity | Every run; selected docs | Integrity, CI/harness/change governance, feature-doc generation/parity | Running app | check outputs + generated-doc diff/hash |
| 3 | Python compile/unit/API contracts | Changed backend/tests; broad on `testing` | Syntax, deterministic units, route/config/project-scope/security/provider contracts | Browser/live model quality | JUnit + command result |
| 4 | Research/provider/vector contracts | Selected by registry | Spine, provider identity, embedding shape/dimension/invariant, fail-closed behavior | Real provider quality | JUnit + invariant contract report |
| 5 | Property/mutation | Selected deterministic targets | Invariant strength and mutation kill signal | Model semantics/research validity | mutation/property summary |
| 6 | Frontend | Frontend/shared changes; broad on `testing` | Unit, lint, typecheck, production build, selected mutation | Backend/provider runtime | JUnit/build log |
| 7 | Relay/JS harness/simulation | Relay/harness/simulation changes; broad on `testing` | Node tests, static simulation, real-user syntax/project-scope checks | Full browser acceptance unless declared | test reports |
| 8 | E2E/browser | Registry-selected or owner-authorized | Running API/UI behavior against named QA project and corpus slice | Provider/model quality unless live target enabled | redacted trace/JUnit |
| 9 | Security benchmark | Triggered by control matrix | Threshold and tracked security controls | General functionality | `security_scorecard.json` |
| 10 | Compose contract | Every QA candidate | Profiles, interpolation, healthcheck, network/security/resource configuration | Service health | redacted rendered config/hash |
| 11 | Image build/provenance | `testing`/approved candidate | Reproducible image, digest, non-root/hardening, provenance/SBOM policy | Full runtime quality | digest + attestation/SBOM |
| 12 | Contract QA stack | QA obligation | Disposable orchestration, readiness/reset/audit using deterministic adapter | Real provider/model quality | QA manifest + logs |
| 13 | Synthetic provisional QA | Spine obligation or `testing` candidate | Source-span/evidence/coding/reliability/reconciliation and blocked report gates | Reportable research validity | spine QA report |
| 14 | Authorized live provider | Explicit owner dispatch only | One selected chat/embed target, exact identity, dimensions, bounded requests | Broad release readiness | redacted readiness/invariant evidence |
| 15 | Staging acceptance | Owner-authorized environment only | Full running system under declared target/origin/rollback | Public CI reproducibility | staging evidence |
| 16 | Promotion manifest | After all required lanes | Exact SHA/digest/obligation/evidence/approval binding | Permission to merge without human review | `promotion-manifest.json` |

### Command catalog and calibration

Commands must be taken from `TESTING.md`, current workflow conventions, and selected registry
entries. Before making a command a required check, implementation runs it once through
Compass Forge calibration or records why a local-only command is not available. Examples of
candidate commands (working directories and exact targets must be verified):

```bash
# governance/public hygiene
python scripts/check_integrity.py
python scripts/check_ci_governance.py
python scripts/check_test_harness.py
python scripts/check_public_tree_clean.py --base "$BASE_SHA" --head "$HEAD_SHA"
python scripts/check_change_obligations.py --base "$BASE_SHA" --head "$HEAD_SHA" --json-out artifacts/feature-obligations.json
python scripts/feature_docs.py --seed-missing --generate-site --check

# deterministic backend/provider/spine/security
pytest tests/test_model_provider_contract.py -q
pytest tests/test_research_validity_contract.py -q
pytest tests/pi_production/test_w8_embeddings_gateway.py -q
pytest tests/pi_production/test_w3_research_spine.py -q
pytest tests/test_project_scope_contracts.py tests/test_harness_project_scope_contracts.py -q
python scripts/security_benchmark.py --fail-on-threshold
pytest tests/test_security_benchmark.py -q

# frontend/relay/harness (only when selected)
cd frontend && npm ci && npm run lint && npx tsc --noEmit && npm run test:unit && npm run build
cd relay && npm ci && npm test
npm --prefix tests/simulation ci && npm --prefix tests/simulation run test:static
npm --prefix tests/real_user_benchmark ci && npm --prefix tests/real_user_benchmark run check

# Compose/image/QA (implementation and authorized runtime stages only)
docker compose -f docker-compose.qa.yml --profile contract config --quiet
docker compose -f docker-compose.qa.yml --profile synthetic config --quiet
python scripts/qa_stack.py render --profile contract --output artifacts/compose-rendered.yaml
python scripts/qa_stack.py readiness --project "$QA_PROJECT"
python scripts/qa_stack.py seed --project "$QA_PROJECT" --slice "$CORPUS_SLICE"
python scripts/qa_stack.py reset --project "$QA_PROJECT" --confirm
python scripts/qa_stack.py collect --project "$QA_PROJECT" --output artifacts/qa-gate-bundle
```

The repository's existing broad suites and benchmark commands remain available, but the
registry must choose targeted commands where possible to keep PR signal bounded. Full
simulation, browser, marathon, live LLM, or staging commands must carry their authorization,
project, corpus slice, timeout, and retention in the registry/report.

### Property, mutation, simulation, and E2E boundaries

- Mutation/property targets are deterministic invariants: path classification, URI/route
  normalization, provider request construction, embedding vector finite/shape checks,
  project-scope selection, reset naming, reliability calculations, and manifest binding.
- Static simulation is public CI-safe. A live simulation/E2E must use a named disposable
  project and corpus slice; it cannot choose the first visible project, fake an ID, or fall
  back to an unscoped route.
- A contract stub may prove schema, timeout/retry, malformed-response, identity, and dimension
  handling. It cannot prove model quality, embedding semantic quality, reportability, or
  full-feature runtime readiness.
- If a required runtime lane cannot run because its environment is absent, the result is
  `blocked`/`not_authorized`, not green. The human gate must see the blocker.

## 6. Docker artifact, runtime, seed/reset, and retention contract

### 6.1 QA entrypoint and profiles

Use a dedicated `docker-compose.qa.yml` (or repository-approved equivalent) rather than
silently overloading the deployment Compose or an unrelated benchmark overlay. It should
reuse stable service definitions where safe, but make QA differences explicit and testable.
Profiles are:

- `contract` (public default): backend/frontend, ephemeral data service if needed, deterministic
  provider contract adapter, and test runner. No Ollama, LM Studio, model daemon, private host,
  or live provider.
- `synthetic`: `contract` plus governed synthetic source slices and provisional-only Research
  Spine orchestration.
- `e2e`/`relay`/`mcp`/`observability`: opt-in capability profiles selected by registry; each
  profile has its own security and evidence contract.
- `live`: owner-authorized only; no provider container or discovery loop; one explicit external
  chat/embedding target.
- `staging`: not a normal CI profile; invoked through the separate adapter contract.

The default QA profile must not inherit a local-model dependency or use `host.docker.internal`.
If a host adapter is needed for live QA, it is profile-gated and never part of public default
or public documentation.

### 6.2 Reproducibility and isolation

- Build with BuildKit/buildx where available; bind source SHA, Dockerfile hash, lockfile hashes,
  Compose/profile hash, builder/run ID, platform, provider mode, and image digest in the manifest.
- Use immutable tags such as `qa-${SOURCE_SHA}` plus a run-attempt tag. A moving branch tag is
  a convenience pointer only and never promotion identity.
- Generate a safe, unique Compose project name such as
  `istara-qa-${RUN_ID}-${ATTEMPT}`. Derive networks, volumes, container labels, and artifact
  directories from it. Do not use fixed `container_name` values.
- Keep data/backend networks internal. Publish only explicitly required loopback ingress for
  an authorized UI/E2E profile; never publish database, relay, or backend data ports by default.
- Enforce non-root runtime, `cap_drop: ALL`, `no-new-privileges`, read-only root filesystems
  where compatible, bounded tmpfs, CPU/memory/pid limits, minimal packages, healthchecks, and
  no `/var/run/docker.sock`, privileged mode, host PID, host network, or broad host mounts.
- Verify origin/CORS/WebSocket/WebAuthn settings as one contract; a page loading is not auth
  or origin evidence.

### 6.3 Lifecycle commands

A thin `scripts/qa_stack.py` or equivalent must expose explicit, project-scoped operations:

1. `render`: validate required keys and emit redacted config plus hash without printing values.
2. `up`: create only the generated project/profile and wait for semantic application readiness.
3. `seed`: create a named QA project and ingest named canonical synthetic source slices through
   the real source/evidence-unit path; write a seed manifest with hashes and handles.
4. `qa`: run exactly the obligations selected by the registry.
5. `collect`: export allowlisted JUnit/JSON/trace summaries and provenance; redact before upload.
6. `audit`: verify digest/config/source binding, provisional flags, report gate, redaction, and
   retention status.
7. `reset`: destroy only this project's resources and recreate from the same manifest; require
   an explicit confirmation token and reject empty/root/protected paths.
8. `down`: stop/remove only this project. `--purge` must not call `docker system prune` or touch
   any other project, developer volume, `LLMs/`, or `Model_Finetuning/`.

Reset must be idempotent and prove cross-project isolation by running two names and showing
that reset of one leaves the other unchanged. Reuse `scripts/reset_test_environment.py` only
through a guarded project-scoped wrapper if its contract fits; do not create a second unrestricted
reset mechanism.

### 6.4 Synthetic corpus and artifacts

Use small, licensed, canonical synthetic slices with raw source spans, stable provenance, and
manifest hashes. Do not seed nugget/report prose as if it were source evidence. Every derived
QA record carries a QA/provisional marker and a provenance handle. If the current schema lacks
a safe marker, implementation must add the smallest explicit provenance boundary after impact
analysis; an environment variable alone is insufficient.

Runtime outputs go to an ignored per-run directory or CI artifact namespace. The collection
allowlist includes only handles, counts, hashes, statuses, durations, JUnit/JSON summaries,
redacted health, and route/invariant evidence. It excludes source text, prompts, model output,
full provider responses, tokens, URLs, connection strings, screenshots containing research,
local databases, media, model files, and private endpoint fingerprints.

Suggested retention policy pending owner approval: short PR retention, longer `testing` and
release-candidate evidence retention, and no retention of user research or credentials. The
actual values and storage destination are owner-gated.

## 7. Provider-neutral chat/embedding contract

### 7.1 Three truthfully labeled lanes

**Contract-only.** A deterministic in-process or isolated adapter proves request/response
schemas, header construction, explicit model selection, timeout/retry/typed failure behavior,
malformed responses, embedding count/shape/finite values, and expected dimension handling. It
may use deterministic vectors only to test plumbing; it must be labeled `contract_only` and
cannot satisfy live or reportability obligations.

**Synthetic-provisional runtime.** The QA stack exercises source ingestion, evidence units,
independent coders, reliability/grounding, reconciliation, task review, and report exclusion
using governed synthetic sources and deterministic test adapters. It proves wiring, scope,
traceability, and gate enforcement. It remains `provisional_qa` and cannot claim model quality,
research validity, or production reportability.

**Authorized-live.** A manually authorized run supplies one explicit chat target and one explicit
embedding target with provider kind/API shape, exact model identities, expected dimension,
secret source, timeout/retry budget, and no-fallback policy. It probes readiness and bounded
requests, records route/identity/dimension evidence without content, and fails closed on any
missing or mismatched capability.

### 7.2 Capability and readiness evidence

The registry's capability section and generated readiness report must contain only safe metadata:

```json
{
  "mode": "authorized_live",
  "provider_kind": "openai_compat",
  "chat": {"endpoint_id": "opaque-id", "model": "exact-chat-model"},
  "embedding": {"endpoint_id": "opaque-id", "model": "exact-embedding-model", "dimension": 1536},
  "fallback": "disabled",
  "secret_source": "environment-or-protected-secret",
  "redacted": true
}
```

The actual schema may follow existing application types, but readiness is green only when:

1. one configured target is named and authorized; no endpoint discovery or localhost/LAN scan
   occurs;
2. chat and embedding provider/API/model identities are explicit and exact;
3. credentials are present without being logged;
4. declared and probed embedding dimensions agree with stored metadata;
5. `assert_vector_space_invariant` remains enabled and passes where the embedding path is used;
6. `validate_embedding_vectors` rejects malformed/ragged/non-finite/wrong-dimension results;
7. route evidence distinguishes registered, reachable, ready, selected, served, and failed;
8. no hidden fallback changes provider/model/vector space and no model is silently loaded;
9. project scope, verification state, governance state, and rollback handles are present;
10. bounded chat/embedding requests succeed only in the explicitly authorized lane.

A missing capability, dimension, secret, route, target, or invariant is a typed failure. Retries
repeat the same target within budget or fail; they never switch provider/vector space. A
contract-only report may state which pure checks passed, but must state that no real provider
service or model quality was checked.

## 8. Research Spine and self-improvement governance validation

The QA path must preserve the same validity spine rather than optimize a parallel benchmark:

| Spine gate | QA proof | Forbidden shortcut |
|---|---|---|
| Sources | Seed raw canonical synthetic slices with stable provenance and span hashes. | Seed synthesized nugget/report prose as source. |
| Evidence Units | Ingest through the real source/evidence-unit contract; preserve span offsets, project, method, and participant metadata. | Create only a database row or summary with no source span. |
| Independent coding | Run independent named deterministic coders for contract QA, or explicitly authorized distinct live coder identities. | Treat one response or shared fixture as consensus. |
| Reliability/grounding | Compute configured reliability and grounding metrics against evidence-unit coding matrices. | Pass on final-answer keywords or tool success. |
| Reconciliation | Include a low-consensus case and require reconciliation/debate/human-review state. | Bulk-accept all generated findings. |
| Accepted atoms/nuggets/facts | Preserve evidence links and QA provenance through status transitions. | Treat provisional visibility as acceptance. |
| In Review / Done | Assert tasks/artifacts cannot become Done/reportable without required human review. | Let CI/agent completion bypass review. |
| Reports | Assert report routes exclude provisional, unreconciled, unapproved, or not-Done artifacts. | Generate reports from seed output or provisional rows. |
| Route/evidence | Preserve project, task, coding-run, model/coder, donor, retrieval, verification, and governance handles. | Treat registration or raw tool success as served evidence. |
| Self-improvement | Assert synthetic QA cannot write promotable ReasoningBank/Memento/model/skill signals; proposals remain sandboxed and rollbackable. | Learn strong positives from raw tool success or synthetic shortcuts. |

Every QA report is marked `contract_only`, `provisional_qa`, `authorized_live`, or `staging`
and includes a non-reportable boundary. The QA runner must not ingest its own output as
research evidence, promotion evidence, or a strong self-improvement signal.

## 9. Security, privacy, and supply-chain controls

### Secrets and artifacts

- Public/fork CI receives no live-provider secret, registry write credential, private target,
  connection string, endpoint fingerprint, or host path.
- Authorized secrets come only from protected GitHub environments or ignored local env/keychain
  sources. They never enter images, Compose files, labels, cache keys, command output, or
  uploaded logs.
- Run redaction scans over rendered config, logs, JUnit/JSON, traces, screenshots, and manifests;
  fail closed on token/key/URL/connection-string/raw-content matches.
- `scripts/check_public_tree_clean.py` and a QA artifact scanner are complementary: staged-tree
  hygiene prevents commits; artifact scanning prevents CI leakage.

### Runtime and application boundary

- No Docker socket, privileged mode, host PID/network, broad host mount, or unbounded resource.
- Backend/data networks remain internal; only intended loopback or approved ingress is exposed.
- Test WebAuthn origin, CORS, CSRF/auth token, WebSocket origin, proxy trust, and rate-limit
  behavior using the same named QA project. A browser screenshot cannot substitute for a policy
  assertion.
- Preserve `MCP_SERVER_ENABLED=false`, `AUTORESEARCH_ENABLED=false`, and equivalent safe defaults
  in public contract QA unless a selected obligation has its own isolated profile and tests.

### Supply chain and benchmark

- Use least-privilege workflow permissions (`contents: read` by default); grant packages,
  attestations, or OIDC only to the exact trusted publication job.
- Pin third-party actions to reviewed immutable SHAs if repository policy requires it.
- Bind SBOM/provenance/attestation to source SHA, Dockerfile, lockfiles, Compose hash, and image
  digest. A mutable tag is never acceptance identity.
- Run `python scripts/security_benchmark.py --fail-on-threshold` for configured security triggers.
  If QA introduces a new control/evidence path/standard mapping/trigger, update
  `security/control_matrix.json`, `security/SECURITY_BENCHMARK.md`, and
  `tests/test_security_benchmark.py` in the same implementation change. Do not update them
  merely to disguise inherited failures.

## 10. Staging contract and optional private adapter

CI and staging are different contracts:

- **CI** is public, automated, reproducible, ephemeral, and provider-neutral by default. It may
  prove deterministic and provisional synthetic behavior without a live target.
- **Staging** is a running integrated environment with a named operator, target SHA/image,
  provider/embedding identity, origin/network, secret source, data retention, and rollback.
  Staging evidence is advisory input to the human gate and never creates/promotes a PR by itself.
- Public documentation describes only an optional owner-local staging adapter in generic terms.
  Private adapter names, addresses, routes, credentials, and fingerprints stay outside public
  workflows and docs.

The owner-local adapter (including an optional `multivac` implementation) must run this sequence:

1. `inventory --read-only`: record host/container versions, active projects, volumes/networks,
   listeners, firewall/origin evidence, current image/config digests, resources, and rollback
   handles. No write or stop.
2. `preflight`: validate the public artifact digest, unique project name, required resources,
   origins, secret availability, provider capability, and no unexpected port.
3. `prepare`: create only a new project/volume/network namespace. Never stop or mutate the old
   stack before acceptance.
4. `run`: start selected artifact/profile, wait for health/readiness, seed named synthetic
   corpus, and execute bounded acceptance checks.
5. `accept`: record health, project isolation, route/invariant, provisional Spine, origin,
   listener/firewall, artifact-redaction, and rollback evidence.
6. `rollback`: stop/remove only the new namespace and verify the old-stack inventory/health is
   unchanged. If isolation cannot be proved, stop without preparation and escalate.

For `multivac` specifically, the first invocation is inventory/dry-run only; a new unique
project name is mandatory; loopback or explicitly approved HTTPS/tunnel is required; firewall
and listener evidence are captured; no old-stack mutation occurs before acceptance; and rollback
removes only the new project. This adapter is not an official public test path and is never a
public CI prerequisite.

## 11. Human approval and promotion evidence contract

The human gate consumes one sanitized, immutable bundle, for example:

```text
qa-gate-bundle/<run-id>/
  feature-obligations.json
  ci-summary.json
  test-results/                  # JUnit/JSON, sanitized
  compose-rendered.yaml          # only after redaction
  compose-rendered.sha256
  image-digest.txt
  provenance.json
  sbom.json                      # if owner policy requires it
  security-scorecard.json
  research-spine-qa.json         # handles/statuses, no raw research
  provider-readiness.json        # only if live lane was authorized; redacted
  redaction-scan.json
  cleanup.json
  promotion-manifest.json
```

`promotion-manifest.json` binds:

- exact `testing` source SHA and current `main` base SHA;
- registry version/report hash and zero unknown/unowned paths;
- required selected commands and their pass results;
- Compose file/profile/hash, image digest, Dockerfile/lockfile hashes, provenance/SBOM status;
- provider mode and any required exact identity/dimension/invariant evidence;
- Research Spine provisional/report-gate result;
- security/docs/public-tree results and sanitized artifact hashes;
- residual risks, blocked optional lanes, retention, cleanup, and rollback commands;
- CF spec/task/evidence references and the pending/approved human decision.

Approval is explicit, human, protected, and SHA-bound. The post-approval job re-fetches the
source SHA and manifest hash immediately before creating a single promotion PR. A changed SHA,
changed target base, missing artifact, failed check, stale approval, or duplicate PR condition
fails closed. The job cannot merge. A human review remains required on the resulting `main` PR.

## 12. Implementation phases, entry/exit gates, and rollback

### Phase 0 — Baseline and ownership inventory

**Entry:** Owner-approved `CF-SPEC-56`; no implementation authorization is inferred from this
candidate.

**Work:** Capture CF gate baseline; inspect branch protections/workflows/Compose/Dockerfiles;
reconcile `TESTING.md`, governance scripts, feature docs, provider/embedding contracts,
Research Spine/self-improvement contracts, and test ownership; reproduce the Compose config
result; identify inherited vs new findings.

**Exit:** Baseline report, explicit inherited debt, confirmed registry owner/test-owner model,
command catalog draft, supported Compose decision, and no source/runtime mutation.

**Verification:**

```bash
compass-forge gate before --task <phase-task>
python scripts/check_integrity.py
python scripts/check_ci_governance.py
python scripts/check_test_harness.py
python scripts/check_public_tree_clean.py --base "$BASE_SHA" --head "$HEAD_SHA"
python scripts/check_change_obligations.py --base "$BASE_SHA" --head "$HEAD_SHA"
docker compose -f docker-compose.yml config --quiet
```

The last command is a diagnostic baseline and may expose the inherited compatibility conflict;
Phase 0 cannot call it green without documenting the supported Compose resolution.

**Rollback:** Remove only untracked baseline artifacts; no host or runtime cleanup.

### Phase 1 — Canonical registry and fail-closed evaluator

**Entry:** Phase 0 ownership and command catalog accepted.

**Work:** Add the single feature/subfeature registry, nested capabilities, evaluator schema,
path classification, ownership/docs/generated-artifact checks, JSON report, parity tests, and
compatibility with existing `check_change_obligations.py`.

**Exit:** Deliberately unclassified backend/frontend/route/agent/skill/model/test/workflow
paths fail; registered representative changes select the correct union; optional lanes and
reasons are visible; test ownership is explicit; existing checks remain green or inherited
issues are recorded.

**Verification:**

```bash
pytest tests/test_feature_obligations.py -q
python scripts/check_change_obligations.py --base HEAD^ --head HEAD --json-out /tmp/feature-obligations.json
python scripts/check_ci_governance.py
python scripts/check_test_harness.py
```

**Rollback:** Disable only the new required check through an owner-approved branch-protection
change if needed, while retaining the registry/tests and existing governance gates.

### Phase 2 — Public testing-branch CI graph and evidence manifest

**Entry:** Phase 1 evaluator is deterministic and parity-tested.

**Work:** Add protected `testing` triggers, concurrency/cancellation rules, selected-lane job
matrix, artifact allowlists, JUnit/JSON aggregation, redaction, failure/retry semantics,
least-privilege permissions, and manifest generation. Keep live credentials out of ordinary
PR/fork jobs.

**Exit:** Every required obligation has a job; skipped optional lanes are explicit; a failed or
cancelled run cannot publish green; fork jobs cannot access secrets or registry write; manifest
binds SHA and selected report.

**Verification:**

```bash
python scripts/check_ci_governance.py
python scripts/check_test_harness.py
python scripts/check_public_tree_clean.py --base "$BASE_SHA" --head "$HEAD_SHA"
# repository-approved workflow contract/lint command, once calibrated
```

**Rollback:** Revert only new workflow files or remove their new required status checks under
owner control; retain existing security/governance checks and do not bypass branch protection.

### Phase 3 — QA Compose, image, and disposable lifecycle

**Entry:** Phase 2 selects QA obligations and artifact policy is approved.

**Work:** Add the dedicated QA Compose contract, profiles, provider contract adapter boundary,
health/readiness, unique project/volume naming, seed/reset/audit/collect, cleanup guard,
artifact redaction, image digest/provenance/SBOM integration, and focused tests. Resolve the
base Compose compatibility issue before claiming parity.

**Exit:** Contract profile renders and runs only when an authorized runtime verification is
requested; it has no local-model/private-host dependency; two projects are isolated; reset is
idempotent and scoped; digest/config/source manifest binds; cleanup is visible.

**Verification (runtime commands require explicit implementation-stage authorization):**

```bash
docker compose -f docker-compose.qa.yml --profile contract config --quiet
docker compose -f docker-compose.qa.yml --profile synthetic config --quiet
pytest tests/test_qa_stack_contract.py tests/test_qa_reset_seed.py -q
python scripts/check_public_tree_clean.py --base "$BASE_SHA" --head "$HEAD_SHA"
# authorized bounded runtime only:
python scripts/qa_stack.py up --project "$QA_PROJECT" --profile contract
python scripts/qa_stack.py readiness --project "$QA_PROJECT"
python scripts/qa_stack.py reset --project "$QA_PROJECT" --confirm
python scripts/qa_stack.py down --project "$QA_PROJECT" --purge
```

**Rollback:** Remove only the generated QA project/artifacts and revert QA workflow/Compose
changes. Never broad-prune Docker or touch developer/protected volumes.

### Phase 4 — Provider, vector, and Research Spine lanes

**Entry:** Phase 3 contract QA is green and public CI has no live secret dependency.

**Work:** Implement capability/readiness report, exact chat/embed identity, no-fallback guard,
one-target live authorization, invariant/dimension evidence, canonical synthetic slices,
provisional boundary, independent-coder/reliability/reconciliation/report exclusion tests,
and self-improvement isolation.

**Exit:** Contract and synthetic lanes never claim live/model quality; synthetic results cannot
become reportable or promotable; live lane passes only with one configured target or gives a
typed blocker; vector and Research Spine gates remain load-bearing.

**Verification:**

```bash
pytest tests/test_model_provider_contract.py tests/test_research_validity_contract.py -q
pytest tests/pi_production/test_w8_embeddings_gateway.py tests/pi_production/test_w3_research_spine.py -q
pytest tests/test_synthetic_provisional_boundary.py tests/test_provider_readiness.py -q
python scripts/security_benchmark.py --fail-on-threshold
# owner-authorized, one configured target only; secret loader must redact the endpoint:
ISTARA_RUN_REAL_LLM_BENCHMARK=1 python scripts/test_llm_integration.py
```

The final command is not a public CI default and must never be recorded with a private URL,
token, or endpoint fingerprint.

**Rollback:** Disable the live profile and restore explicit prior adapter configuration; never
remove dimension/invariant/fail-closed checks or replace a provider with synthetic vectors.

### Phase 5 — Optional staging adapter and private host validation

**Entry:** Deterministic, contract, synthetic, and authorized runtime evidence are green where
required; owner explicitly authorizes an external target.

**Work:** Implement generic inventory/preflight/prepare/accept/rollback boundary and, only if
approved, the owner-local `multivac` adapter. Keep private values outside public repo artifacts.

**Exit:** Read-only inventory precedes all writes; new project is isolated; listener/firewall,
origin, health, provider/vector, project-scope, provisional-Spine, and rollback evidence exist;
old stack is unchanged before acceptance and verified afterward.

**Verification:** Adapter-specific read-only inventory, listener/firewall evidence, health and
invariant checks, project isolation, and rollback. No public command contains a private target.

**Rollback:** Tear down only the unique new project, re-check old-stack health/inventory, and
stop/escalate if the old stack was touched or isolation cannot be proven.

### Phase 6 — Documentation graduation, human gate, and promotion readiness

**Entry:** All required automated evidence and manifests are complete; no open Blocker/Major
review finding; owner-gated decisions are resolved.

**Work:** Update living testing/branch/QA/provider/security docs, feature docs if behavior
obligations changed, attach CF evidence, record residual risk and rollback, request protected
human approval, and create a promotion PR only after the approval job succeeds. Do not merge.

**Exit:** Human approval is SHA/digest-bound; promotion PR is created only afterward; main
checks and CODEOWNERS remain required; docs parity and CF/Build Stream evidence are attached.

**Verification:**

```bash
python scripts/feature_docs.py --seed-missing --generate-site --check
pytest tests/test_feature_docs.py -q
compass-forge gate after --task <phase-task> --summary
compass-forge spec coverage CF-SPEC-56
compass-forge spec drift CF-SPEC-56
```

**Rollback:** Close/revert an unmerged promotion PR, restore prior workflow/branch settings
through owner-controlled changes, retain evidence/retro, and never force-push or auto-merge.

## 13. Executable acceptance criteria

Each criterion is a contract for a later implementation task; exact repository command names
must be calibrated before becoming required CI checks.

### Branch and human gate

1. **Given** a feature branch changes a registered behavioral path, **when** the classifier runs,
   **then** the report contains the matched feature, test owner, docs obligation, security
   trigger, selected commands, and reasons. **Verify:**
   `python scripts/check_change_obligations.py --base "$BASE" --head "$HEAD" --json-out artifacts/feature-obligations.json`.
2. **Given** a new route/store/menu/agent/skill/model/test behavior path has no registry owner,
   **when** the classifier runs, **then** it exits nonzero and names the path and required
   registry update. **Verify:** `pytest tests/test_feature_obligations.py -q`.
3. **Given** all required `testing` checks and QA evidence are green, **when** no owner approval
   exists for the exact SHA, **then** no job creates a PR to `main`, changes `main`, or promotes
   an artifact. **Verify:** workflow contract test plus a negative promotion-run fixture.
4. **Given** protected approval binds source SHA, base SHA, manifest hash, and image digest,
   **when** the source SHA is unchanged, **then** exactly one promotion PR may be created and
   no merge occurs. **Verify:** promotion workflow contract test.
5. **Given** the source SHA or manifest changes after approval, **when** promotion is attempted,
   **then** the job fails closed and requires new approval. **Verify:** stale-approval negative
   test.

### Deterministic test obligations

6. **Given** a backend/provider/research change, **when** the union is selected, **then** the
   targeted backend contracts, provider/vector checks, Research Spine checks, docs obligations,
   and benchmark triggers run without a live provider by default. **Verify:** registry report
   fixture plus selected CI matrix test.
7. **Given** a frontend/shared behavior change, **when** its entry is selected, **then** lint,
   type, unit, build, relevant mutation/property, and feature-doc checks run; full browser QA
   is selected only when declared. **Verify:** frontend lane contract test.
8. **Given** a workflow or test-harness change, **when** the classifier runs, **then** CI and
   harness governance checks are required. **Verify:** `python scripts/check_ci_governance.py`
   and `python scripts/check_test_harness.py`.
9. **Given** a generated feature-doc file changes without an allowed source/generator relation,
   **when** governance runs, **then** it fails rather than accepting drift. **Verify:**
   `python scripts/feature_docs.py --seed-missing --generate-site --check` plus negative fixture.

### Docker and disposable QA

10. **Given** a supported Compose version and no provider secret, **when** the `contract` profile
    renders, **then** it has no Ollama/LM Studio/model service, no private host dependency, and
    its readiness claim is `contract_only`. **Verify:**
    `docker compose -f docker-compose.qa.yml --profile contract config --quiet` and rendered-config assertions.
11. **Given** two QA run IDs, **when** both stacks are created, **then** projects, volumes,
    networks, and artifact roots are unique and reset of one leaves the other unchanged.
    **Verify:** `pytest tests/test_qa_reset_seed.py -q` and an authorized bounded two-project run.
12. **Given** a failed or cancelled run, **when** cleanup executes, **then** only its generated
    namespace is removed and cleanup status is retained in sanitized evidence. **Verify:** QA
    cleanup contract test.
13. **Given** an image artifact, **when** its manifest is verified, **then** source SHA,
    Dockerfile/lockfile hashes, Compose hash, image digest, provenance/SBOM status, and provider
    mode match; a mutable tag alone fails. **Verify:** artifact-manifest test.

### Provider and vector safety

14. **Given** an authorized-live configuration lacks one explicit chat/embed identity, secret,
    capability, expected dimension, or target, **when** readiness runs, **then** it fails with a
    typed reason and makes no fallback request. **Verify:** `pytest tests/test_provider_readiness.py -q`.
15. **Given** exact chat and embedding targets are configured, **when** readiness/probe runs,
    **then** exact identities, dimensions, route evidence, and `assert_vector_space_invariant`
    are recorded without content or secret leakage. **Verify:** provider readiness and
    `tests/pi_production/test_w8_embeddings_gateway.py`.
16. **Given** the selected provider is unavailable, **when** retry occurs, **then** it retries
    only that target within budget or fails; it does not switch vector space or load another
    model. **Verify:** no-fallback negative test.

### Research Spine and self-improvement

17. **Given** a canonical synthetic corpus slice is seeded, **when** provisional QA runs, **then**
    raw spans become evidence units, independent coding/reliability/grounding and a
    low-consensus reconciliation path are exercised, and all outputs retain provisional state.
    **Verify:** `pytest tests/test_synthetic_provisional_boundary.py tests/test_research_validity_contract.py -q`.
18. **Given** a synthetic or unreconciled artifact is In Review, **when** reportability is
    checked, **then** report routes exclude it and identify the missing gate. **Verify:**
    research report negative-case tests.
19. **Given** a self-improvement candidate succeeds only at tool execution, **when** telemetry
    records it, **then** it cannot become a strong model/skill signal or report evidence without
    verification, governance, and Research Spine acceptance. **Verify:**
    `pytest tests/test_improvement_governance.py tests/pi_production/test_autoresearch_failclosed.py -q`.

### Security and privacy

20. **Given** a fork PR, **when** CI runs, **then** it has no live secret, registry-write
    permission, private target, host Docker socket, or protected host mount. **Verify:** workflow
    permissions/negative fixture test and rendered Compose assertions.
21. **Given** logs/configs/traces/screenshots/artifacts are collected, **when** redaction and
    public-tree checks run, **then** tokens, private URLs, connection strings, raw research,
    local DB/media/model files, and ignored runtime outputs are rejected. **Verify:**
    `python scripts/check_public_tree_clean.py --base "$BASE" --head "$HEAD"` plus QA artifact scan.
22. **Given** a QA stack is running, **when** network/listener policy is inspected, **then** only
    intended ingress is published and data/backend networks remain internal. **Verify:** Compose
    security contract test and authorized `docker compose ps/port` audit.

### Optional staging

23. **Given** an owner invokes a staging adapter for the first time, **when** it completes,
    **then** only read-only inventory/dry-run artifacts exist, the new project is unique,
    listener/firewall/origin evidence is present, and the old stack is unchanged. **Verify:**
    adapter dry-run/inventory test.
24. **Given** a staged QA project fails acceptance, **when** rollback runs, **then** only that
    project/volume/network namespace is removed and old-stack health/inventory remains equal.
    **Verify:** adapter rollback test and inventory diff.

## 14. Evidence and handoff contract

Every implementation task attaches exact command evidence to Compass Forge and includes only
sanitized artifacts. At minimum:

- `feature-obligations.json` with base/head, registry/report hashes, paths, owners, selected
  obligations, unknowns, skips, and reasons;
- redacted Compose render and hash, image digest, Dockerfile/lockfile hashes, provenance/SBOM;
- JUnit/JSON command results, mutation/property summary, security scorecard, docs-parity output;
- `qa-readiness.json` with mode, project ID, safe provider identity/dimension metadata, route
  handles, and redaction status (no private URL/content);
- `research-spine-qa.json` with source/evidence/coding/reliability/reconciliation/review/report
  statuses and handles only;
- cleanup/retention status and typed failure evidence;
- `promotion-manifest.json` with exact SHA/base/digest/evidence/rollback and human approval.

CF evidence must include command rows such as:

```bash
compass-forge task evidence <task> --type command --summary "feature obligation report" \
  --payload-json '{"command":"<exact command>","result":"passed","artifact":"artifacts/feature-obligations.json"}'
compass-forge task evidence <task> --type gate --summary "post-change architecture gate" \
  --payload-json '{"command":"compass-forge gate after ...","result":"passed or inherited-debt","artifact":"<gate report>"}'
```

The Build Stream ledger records the phase, files, results, exact commands, findings, residual
risks, and next action. The implementation/review stages provide independent verification;
standard/full changes use the blind-review protocol. The plan candidate itself has no runtime
verification claim.

## 15. Alternatives, failure modes, architecture debt, and rollback

### Alternatives considered

| Alternative | Decision | Rationale |
|---|---|---|
| Do nothing; retain current CI/Compose guidance | Reject | No fail-closed feature ownership, disposable public artifact, or human-bound promotion. |
| Extend only the benchmark overlay | Partial input, not target | Reuses existing gates but cannot by itself define branch state, registry ownership, provider safety, or artifact lifecycle. |
| Two independent registries (feature coverage plus runtime capability JSON) | Reject | Creates contradictory sources of truth. Keep capability declarations in the canonical registry and emit derived reports. |
| Provider-specific public CI | Reject | Violates provider neutrality, fork usability, and host independence. |
| Permanent/self-hosted runner as official path | Reject as default | Couples trust, secrets, network, and data to one host. Allowed only as owner-authorized staging optimization. |
| Ephemeral public runner plus contract stub | Recommend | Reproducible and provider-neutral; pair with optional live evidence and honest claim labels. |
| Generic Docker environment with no repo-owned QA contract | Reject | Cannot encode project scope, Spine provenance, no-fallback, reset, artifact, and ownership obligations. |
| Automatic PR/merge after green CI | Reject | Violates the explicit human gate. Allow only post-approval PR creation; never auto-merge. |
| Keep `staging` as pre-main gate while it force-syncs from `main` | Reject | A mirror cannot serve as a pre-main approval boundary. |

### Failure modes and mitigations

- **Unknown path slips through:** fail-closed evaluator, registry negative fixtures, required status
  check, and review of dynamic registrations.
- **Registry drift or overlapping ownership:** schema validation, test-owner requirement,
  last-verified SHA, and parity with existing `check_change_obligations.py` before migration.
- **Stub mistaken for live readiness:** distinct check names/modes, manifest labels, and a rule
  that contract-only cannot satisfy a live obligation.
- **Provider fallback changes vector space:** exact target binding, fallback disabled, typed
  failure, dimension probe, and invariant negative test.
- **Model download/heavy load:** no model service in default profile, one-target authorization,
  no discovery loops, bounded resources, and passive preflight.
- **Compose collision/data leak:** generated project names, no fixed containers, isolated volumes,
  cross-project reset test, and no broad prune.
- **Secret/artifact leakage:** fork permission boundary, centralized redaction scan, allowlist,
  no private value in labels/cache/manifests, and public-tree check.
- **Cancelled/retried run falsely green:** immutable run/attempt manifest, fresh project, and
  explicit cancelled/cleanup statuses.
- **Synthetic shortcut becomes report evidence:** raw-span ingestion, provisional marker,
  promotion/report negative cases, and no self-improvement writes.
- **Staging mutates old stack:** read-only inventory, new namespace, acceptance barrier, old-stack
  inventory diff, and rollback-only-new-project rule.
- **Inherited gate debt masks new regression:** Phase 0 baseline and `gate after` comparison;
  new findings are fixed or explicitly tasked, inherited findings are not relabeled.
- **Compose version incompatibility:** owner-approved support matrix and a tested, additive
  compatibility fix; never disable resource/security controls to force a local pass.

### Architecture debt to report, not conceal

1. Existing local-provider defaults may remain useful for local development but must not be the
   public QA prerequisite.
2. Existing path-pattern governance and a feature registry are not equivalent; retain old checks
   until measured parity is proven.
3. Branch/docs descriptions of `testing`, `staging`, and `main` are inconsistent and need one
   living contract.
4. Existing import-cycle, secret-flow, large-file, complexity, route-drift, and type-drift
   findings are baseline debt unless a touched implementation changes them.
5. Full browser/real-user/live-provider QA remains environment-bound and cannot be made a normal
   public PR requirement without an approved public target and budget.
6. A dedicated QA overlay adds maintenance surface; a later consolidation is a separate task.

### Rollback hierarchy

- Registry: revert the registry/evaluator while keeping existing governance checks active until
  parity is restored.
- Workflow: disable/revert only new jobs; preserve existing security and governance checks.
- QA artifact: stop/remove only its generated project and volumes; retain sanitized evidence.
- Provider: disable live profile and restore explicit adapter settings; never remove invariant.
- Staging: remove only the new project and verify old stack; stop if old stack is not provably
  unchanged.
- Promotion: close/revert the unmerged PR; no force-push or automatic merge.

## 16. Likely implementation files and surfaces

This is an inventory, not authorization to edit all listed paths.

### New or primary testing surfaces

- `testing/feature_coverage.yml` (or repository-approved canonical registry location)
- `scripts/check_change_obligations.py` and focused evaluator helpers/tests
- `tests/test_feature_obligations.py`
- `docker-compose.qa.yml` and any narrowly scoped QA overlay/health contract
- `scripts/qa_stack.py` or a tightly scoped equivalent
- `qa/README.md`, `qa/corpora/manifest.json`, small licensed synthetic slices, and ignored
  `qa/runs/` runtime output
- QA artifact/redaction/provenance/manifest tests
- provider capability/readiness contract module only if existing contracts cannot express the
  required identity boundary
- `tests/test_provider_readiness.py`, `tests/test_synthetic_provisional_boundary.py`, and
  focused QA reset/seed tests

### Workflow and governance surfaces

- `.github/workflows/ci.yml` and/or new dedicated QA/promotion workflow files
- `.github/CODEOWNERS` and repository branch/environment settings (owner-controlled)
- `scripts/check_ci_governance.py`, `scripts/check_test_harness.py`, and
  `scripts/check_public_tree_clean.py` only where new QA surfaces require registration
- `security/control_matrix.json`, `security/SECURITY_BENCHMARK.md`,
  `tests/test_security_benchmark.py` only if a tracked control/trigger/evidence path changes

### Existing runtime/provider/test contracts to inspect before touching

- `backend/app/config.py`
- `backend/app/api/routes/llm_servers.py`
- `backend/app/core/pi_runtime/embeddings_gateway.py`
- `backend/app/core/embedding_validation.py`
- `backend/app/services/research_validity_service.py`
- `backend/app/core/research_validity.py`
- `backend/app/core/agent_research.py`, `backend/app/core/meta_hyperagent.py`, and
  `backend/app/core/telemetry.py`
- `tests/test_model_provider_contract.py`
- `tests/pi_production/test_w8_embeddings_gateway.py`
- `tests/test_research_validity_contract.py`, `tests/pi_production/test_w3_research_spine.py`
- `tests/test_project_scope_contracts.py`, `tests/test_harness_project_scope_contracts.py`
- `tests/integration/test_llm_orchestration_real.py`, `tests/llm_test_config.py`, and relevant
  relay/simulation/E2E suites

### Living documentation impact

- `README.md`, `README.pt-BR.md` only for public developer workflow/branch/QA quickstart
- `TESTING.md`, `testing/TESTING_STRATEGY.md`, and possibly `testing/TEST_HISTORY.md`
- `CHANGE_CHECKLIST.md`, `Tech.md`, `CONTRIBUTING.md`, `SYSTEM_CHANGE_MATRIX.md`, and
  `DOCUMENTATION.md` only where their existing contracts require updates
- `docs/architecture/research-validity-contract.md` and
  `docs/architecture/self-improvement-governance-contract.md` only if the implemented QA
  contract adds durable behavior that belongs in those living contracts
- relevant `docs/features/content/**` and generated site output only when feature/test behavior
  obligations change; `docs/features/site/manifest.json` remains isolated
- private owner-local adapter instructions belong outside public docs and contain no secrets

## 17. Coverage matrix: synthesis of the three drafts

| Master-plan section | Architect A insight preserved | Architect B insight preserved | Architect C insight preserved | Synthesis decision |
|---|---|---|---|---|
| Executive outcome and boundaries | Whole-system public developer/maintainer outcomes and human gate | Provider-neutral public CI outcome | Docker/Spine/provider/security lane boundaries | One outcome model with explicit claim labels, not three parallel systems. |
| Current-state evidence | Existing CI/Compose/branch/docs gaps | Existing governance scripts and historical audit caveat | Existing provider/vector/Spine/security evidence and unverified runtime gaps | Cite repository paths and label every unverified assumption. |
| Registry | Declarative feature/subfeature ownership and fail-closed algorithm | Changed-path union, command catalog, test ownership, generated-path rules | Runtime capability/spine-touch declarations | One canonical registry contains runtime capability metadata; one evaluator remains authority. |
| Branch state machine | Feature -> testing -> human gate -> main PR and staging distinction | Trigger, concurrency, retry, permissions, fork behavior | Runtime states consumed by CI (`contract`, `synthetic`, `live`, `staging`) | Separate branch control plane from runtime lane contracts and bind them via manifest. |
| CI pyramid | Holistic ordering including docs, security, simulation, E2E, Compose | Workflow graph, artifacts, caching/retry/cancellation, lane matrix | Provider/vector/Spine/security-specific layers | Cheap-to-expensive DAG with registry-selected union and visible skips. |
| Docker QA | Reusable immutable artifact and developer UX | Digest/artifact publication and retention | Profiles, isolation, reset/seed/audit, network/resource hardening | Dedicated QA overlay, no fixed names, no private default, project-scoped lifecycle. |
| Provider contract | Exact identity/no fallback and distinction between test lanes | Explicit one-target live selection and artifact evidence | Chat/embed capability, dimensions, invariant, readiness, no model loading | Existing invariant stays load-bearing; derived readiness report never stores secrets. |
| Research Spine | System-wide spine and report/Done gates | Synthetic/provisional lane labeling | Raw-span ingestion, independent coders, reliability/reconciliation, promotion block | Synthetic QA exercises real gates but is permanently non-reportable. |
| Security | Public-tree, secret, Docker, origin, branch protection controls | Least-privilege actions, retries, artifacts, supply chain | Socket/network/resource/redaction, benchmark trigger, staging firewall | One security contract spans source, workflow, runtime, evidence, and staging. |
| Staging/private adapter | Optional adapter and human boundary | No private dependency in public CI | Read-only inventory, unique project, listener/firewall, rollback | Generic public docs; owner-local adapter details remain private and never official. |
| Phases/acceptance | End-to-end executable GWT criteria and rollback | Implementable workflow/registry/artifact phases | Runtime/provider/Spine phase gates | Six dependent phases with owner decisions only at explicit boundary points. |
| Alternatives/debt | Public-vs-private and branch alternatives | Self-hosted/ephemeral/benchmark trade-offs | Provider/staging/overlay and safety debt | Preserve reversible rollout and honest inherited-debt reporting. |

## 18. Open decisions that remain owner-gated

The implementation must not silently decide:

1. Whether every feature PR must target `testing`, or whether a documented exception exists.
2. Whether `staging` remains a post-main mirror, becomes a separately protected pre-main branch,
   or is retired from the promotion narrative.
3. Which GitHub environment/reviewers can approve promotion and whether post-approval PR creation
   is permitted by repository policy.
4. Exact required checks for feature PRs, `testing`, and the candidate-to-main gate; especially
   which E2E/live/MCP/relay/autoresearch/observability lanes are blocking.
5. Supported Compose versions/platforms and resource/time budget; resolution of the current
   `pids_limit` compatibility conflict.
6. Canonical registry file location/schema ownership and who resolves overlapping/dynamic paths.
7. Artifact registry, fork artifact strategy, retention periods, and whether any QA evidence may
   be publicly linked.
8. SBOM/provenance/signing tooling and whether attestations are required for the first artifact.
9. Whether the public contract adapter is in-process or a dedicated Compose service; neither may
   imply live/model quality.
10. Approved authorized live provider profile, chat model, embedding model/dimension, secret
    storage, and whether live QA is always owner-invoked.
11. Corpus licensing/provenance and the exact synthetic slices allowed in public QA.
12. Whether full-feature obligations are blocking on `testing` or owner-authorized staging only.
13. Whether an owner-local adapter is permitted to use loopback, approved tunnel, or HTTPS, and
    the inventory/firewall evidence required before any write.
14. QA log/screenshot/trace retention and redaction policy; no raw research or credentials may
    be retained regardless of the answer.

## 19. Immediate handoff and Definition of Ready for implementation

The Conductor should cross-vote this candidate against the other supplied master candidates;
no implementation task begins merely because this file exists. Once an owner approves a winning
plan, the implementer is ready only when:

- `CF-SPEC-56` and the winning plan are owner-approved and the task graph is linked;
- Phase 0 has a fresh gate baseline and reconciled repo/workflow/Compose/provider inventory;
- the owner-gated decisions in §18 needed for the first implementation phase are recorded;
- the canonical registry and command catalog have named owners and test owners;
- the public/contract/synthetic/live/staging claim labels are accepted;
- the unrelated `docs/features/site/manifest.json` change is isolated;
- no runtime, provider, Docker, staging, PR, or production action is performed without the
  explicit authorization required by the repository instructions.

**Next planning action:** cross-vote this MECE master candidate with slots B and C, preserve the
selected candidate ID in Compass Forge `plan_vote` evidence, then pause at the owner-approval
barrier before implementation.
