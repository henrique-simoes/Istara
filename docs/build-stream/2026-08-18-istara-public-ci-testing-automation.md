# Build Stream — Public Istara testing branch and CI automation

<!-- STATUS BLOCK -->
```yaml
item: istara-public-ci-testing-automation
branch: conductor/istara-public-ci-testing-20260818
cf: { spec: CF-SPEC-56, tasks: [CF-717, CF-718, CF-719, CF-720, CF-721, CF-722, CF-723, CF-724, CF-725, CF-726, CF-727, CF-728, CF-729, CF-730] }
phase: "Phase 3 — Public CI/testing implementation"
stage: S4-remediate
status: in-progress
blocked_on: null
last: { agent: deepseek/deepseek-v4-flash, at: 2026-08-18T02:34:44Z, ledger: L-21 }
next_action: "Owner approved MECE master plan (slot c); conductor may dispatch implementation."
```
<!-- /STATUS BLOCK -->


## Plan overview (roadmap)

**Outcome.** Create a professional, public, provider-agnostic testing branch and CI system for Istara. Every feature change must be mapped to the appropriate deterministic and authorized runtime checks, produce a reusable disposable Docker QA artifact, and stop at a human approval gate before any PR is created or promoted to `main`.

**Official-path principle.** The public workflow must be usable by every Istara developer without requiring a particular host, private endpoint, cloud vendor, local model server, or owner credential. `multivac` is an optional private adapter for the owner's environment only; it is never the official CI or staging dependency.

**Safety spine.** The plan must preserve the Research Spine, source-span evidence, provisional-only synthetic data, exact model/provider identity, embedding dimensions, `assert_vector_space_invariant`, fail-closed provider behavior, credential isolation, and no silent model loading. Inference-free lanes must not be described as full-feature readiness, and synthetic vectors must never bypass production gates.

**CI/staging distinction.** CI is automated pre-merge validation and artifact production. Staging is a running integrated environment used for acceptance. The plan must define both without conflating them, and must place the human gate after automated evidence but before PR creation to `main`.

| Phase | Goal | Acceptance / verification | Status |
|---|---|---|---|
| 0 | Frame the owner-approved initiative and Compass Forge contract | `compass-forge spec clarify/plan/tasks CF-SPEC-56` | done |
| 1 | Produce and converge a thorough MECE master plan | Conductor architect drafts, synthesis, cross-vote, no implementation | in-progress |
| 2 | Owner approves the frozen plan and releases implementation | `conductor.py approve`; explicit owner approval evidence | planned |
| 3 | Implement public branch/CI, feature mapping, Docker artifact, and developer workflow | deterministic gates, CI workflows, contract tests, docs | planned |
| 4 | Validate disposable runtime and provider-neutral adapter contracts | local authorized runtime checks; Research Spine and fail-closed evidence | planned |
| 5 | Validate optional staging adapters, including private `multivac` | read-only-first, explicit authorization, isolated project, rollback evidence | planned |
| 6 | Human gate, PR creation, promotion, and learning | automated evidence green, owner approval, PR-ready artifact; no auto-merge | planned |


<!-- consensus-winning-plan:ISTARA-PUBLIC-CI-TESTING-20260818-4daccbc523dcf574f44a4abfc595ded25ba3fbf085acdf6376de9a505fb3559f -->
## Winning consensus plan — ISTARA-PUBLIC-CI-TESTING-20260818

# MECE Master Plan (Candidate C) — Public provider-agnostic Istara testing branch and CI automation

- **Task:** `ISTARA-PUBLIC-CI-TESTING-20260818-MASTER-C`
- **Role:** `istara-public-ci-testing-20260818-architect-c`
- **Phase:** S1 MECE synthesis (`synthesize`; round `2fde79fb5fe8105a621d`)
- **Pipeline:** `ISTARA-PUBLIC-CI-TESTING-20260818` · Spec `CF-SPEC-56`
- **Plan file:** `docs/build-stream/plans/istara-public-ci-testing-20260818-master-c.md`
- **Sources synthesized (immutable):**
  - Plan A (holistic / branch+PR+developer experience) — `…plan-a.md` (snapshot `dd3e6f29…`)
  - Plan B (CI automation / workflow graph) — `…plan-b.md` (snapshot `bbef82ea…`)
  - Plan C (runtime / provider / spine / security) — `…plan-c.md` (snapshot `53df2c4c…`)

> This is a **synthesis**, not a concatenation. Section 1 records how the three drafts were
> reconciled (conflict resolutions and a coverage matrix). Every claim cites a repository path
> or command; items the repository cannot substantiate are labeled **UNVERIFIED** or **BLOCKER**
> and must be confirmed during implementation, never assumed.

---

## 1. Synthesis note, reconciliation decisions, and coverage matrix

### 1.1 Method

The three drafts are MECE by lane: A owns the end-to-end branch/PR state machine and developer
experience; B owns the CI workflow graph and deterministic orchestration mechanics; C owns the
runtime/provider/spine/security contracts. They agree on the load-bearing principles (public
`testing` integration branch, fail-closed feature obligations, disposable provider-agnostic
Docker QA artifact, provisional-only synthetic Research Spine data, human gate before any PR to
`main`, `multivac` never official). The synthesis preserves the strongest substantiated idea per
section, resolves the conflicts below, and closes material gaps (a consolidated phase/task plan,
a single executable acceptance set, one evidence/artifact contract).

### 1.2 Conflicts resolved (explicit reconciliation)

| # | Conflict | Drafts | Resolution (adopted by this master plan) |
|---|---|---|---|
| R1 | QA reset mechanism: B proposed HTTP test endpoints `POST /_qa/reset` / `POST /_qa/reseed` behind a QA token; A and C proposed script/Compose-project-scoped reset. | B vs A+C | **Adopt script-driven, Compose-project-scoped reset/seed** (A §6.3, C §8.4) as the primary mechanism — it needs no new attack surface and survives without a running app. If HTTP QA endpoints are ever added, they must be loopback-only, token-gated, disabled in public CI, registered in `security/control_matrix.json`, and covered by `scripts/security_benchmark.py`; until then they are out of scope. |
| R2 | Compose profile naming: A proposed `contract`/`synthetic`/`live` + optional `team`/`relay`/`mcp`/`autoresearch`/`observability`/`production-ingress`; C proposed `core`/`seed`/`reset`/`audit`/`live-llm`/`ui`. | A vs C | **Merge:** `contract` (deterministic default, = C's `core`), `synthetic` (seed + provisional spine, = C's `seed`), `reset`, `audit`, `live` (one-target authorized = C's `live-llm`), `ui` (loopback publish only), plus A's registry-selected optional profiles (`team`, `relay`, `mcp`, `autoresearch`, `observability`, `production-ingress`) that are **never** part of the public default. |
| R3 | `staging` branch role: A flagged the existing force-sync workflow (`sync-staging.yml`) as not a human gate and left three options; B treated `staging` as absent from the promotion narrative; C treated staging as an environment, not a branch. | A/B/C | **Adopt:** `staging` is an *environment mirror* (post-main), never a pre-main approval branch while `sync-staging.yml` force-pushes from `main`; the promotion path is `testing` → human gate → PR → `main`. Changing this is an owner-gated decision (OD-2), not an implementer choice. |
| R4 | Obligation registry ownership: A proposed `testing/feature_coverage.yml` as the single registry; C proposed a second runtime capability registry `qa/runtime_capabilities.json`; B proposed a path-glob registry with `exceptions`/`requires_human_review`/`docs_features_update`. | A/B/C | **Adopt a two-layer model with one authority:** `testing/feature_coverage.yml` is the single authority for feature→obligation mapping (A's schema + B's fields); `qa/runtime_capabilities.json` is a *consulted* runtime/provider capability declaration that feeds the same algorithm (C §5). One classifier (`scripts/check_feature_obligations.py`) reads both; no second contradictory classifier. |
| R5 | Live lane placement: B listed an authorized-live lane as a normal step in the ordered gate list; A and C made it owner-dispatched and non-default. | B vs A+C | **Adopt A/C:** the live lane is **opt-in, one-target, owner-authorized** — never a default PR step, never merge-critical unless a registry entry declares it required for that feature class (owner-gated). |
| R6 | Phase numbering: A proposed Phases 0–6; B proposed Phases A–E; C proposed C1–C5. | A/B/C | **Adopt one consolidated Phase 0–6 sequence** (§13) and map B's A–E and C's C1–C5 onto it; every phase has entry/exit gates and task IDs. |
| R7 | Acceptance criteria: three overlapping G/W/T sets (A: 13, B: 17, C: 8). | A/B/C | **Consolidate into one themed set (§14)** that preserves every distinct claim (branch gate, registry, determinism, disposability, provider/vector, spine, security, staging, docs parity) without duplication. |

### 1.3 Coverage matrix (which draft insight each master section incorporates)

| Master section | Primary source(s) | Draft insight incorporated |
|---|---|---|
| §3 Current-state evidence | C (E1–E15) + A (gap table) + B (script checks) | Evidence with repo paths; unverified items labeled |
| §4 Branch/CI state machine | A (full state machine) + B (enforcement points) | `feature/* → testing → gate → main`; fail-closed checks |
| §5 Coverage registry + obligation algorithm | A (schema + algorithm) + B (fail-closed policy, docs coupling) + C (runtime capability registry) | One authority registry; consulted capability file |
| §6 Test pyramid and execution matrix | B (ordered gates) + A (13-lane matrix, command catalog) + C (L1–L8 determinism classes) | Cheap-to-expensive, fail-fast; determinism class per lane |
| §7 Docker artifact, reset/seed, retention | C (QA overlay, profiles, per-run isolation) + A (image provenance, immutable tags, retention) + B (run-id volumes) | `istara-qa-<run-id>`; immutable digests; reset/audit |
| §8 Provider neutrality | C (ChatIdentity/readiness/invariant, one-target) + A (three lanes, capability schema) + B (no-fallback) | Contract-only vs synthetic-provisional vs authorized-live |
| §9 Research Spine validation | C (is_qa_provisional boundary) + A (spine gate table) + B (reconciliation checkpoints) | Synthetic sources → provisional evidence units only |
| §10 Security/privacy/supply chain | C (controls table) + A (secrets/logs/isolation/GitHub) + B (redaction) | No secrets, loopback-only, provenance/SBOM |
| §11 Staging + multivac | C (read-only-first contract) + A (generic adapter phases) + B (rollback) | Inventory → unique project → accept → rollback |
| §12 Human gate + promotion | A (9-step flow) + C (7-item gate bundle) + B (approval record) | Gate opens only on bundle 1–6 green; no auto-merge |
| §13 Phases + tasks | A (0–6) + B (A–E) + C (C1–C5, T-C1..5) | One consolidated phase/task plan |
| §14 Acceptance criteria | A/B/C G/W/T sets | Single themed set |
| §15 Verification/evidence | A (§14) + C (§15) + B (§13) | One command + artifact contract |

---

## 2. Executive summary

Istara already has a substantial deterministic test estate and a useful two-family model
(`TESTING.md`: CI-safe deterministic checks vs. live/environment-bound checks), a hardened base
Compose stack (`docker-compose.yml`: `read_only`, `cap_drop: ALL`, internal networks, pids/
memory limits), a fail-closed vector-space invariant
(`backend/app/core/pi_runtime/embeddings_gateway.py::assert_vector_space_invariant`), a
governed coding/reliability/reconciliation service
(`backend/app/services/research_validity_service.py`), and a security-benchmark release gate
(`security/SECURITY_BENCHMARK.md`, `scripts/security_benchmark.py --fail-on-threshold`).
Current `.github/workflows/ci.yml` runs `governance`, `backend`, `frontend`, `test-harness-js`,
and `desktop` jobs on `main`/`staging`; it has **no** feature-obligation classifier, disposable
QA-stack proof, or human-gated promotion workflow.

This master plan delivers a long-lived public `testing` integration branch, short-lived feature
branches with declared coverage obligations, a fail-closed feature/subfeature registry,
deterministic CI lanes, an immutable disposable Docker QA artifact, and separately authorized
live/staging lanes. The official path is provider-neutral and host-agnostic: it never requires
Ollama, LM Studio, `multivac`, a private endpoint, or owner credentials. A private `multivac`
adapter may consume the same public artifact later, but it is never the official CI path or a
prerequisite for merge.

The load-bearing boundary is **evidence, not a green process exit**:

- deterministic contract lanes prove only deterministic contracts;
- a contract-only provider stub cannot prove model quality, embedding quality, or reportability;
- an authorized live lane proves one explicitly selected chat/embedding target: identity,
  dimension, route evidence, and bounded runtime behavior;
- synthetic QA research remains **provisional** until Research Spine, reconciliation, human
  review, Done-task, and report gates are demonstrated;
- all automated checks must be green before the owner reviews a promotion manifest;
- only after that explicit human gate may the promotion workflow create a PR to `main`.

### Developer outcome

A developer can branch from `testing`, run a documented deterministic command set, render and
build a disposable QA image, and obtain a short-lived QA environment with a unique Compose
project and isolated data. A feature cannot silently enter the branch without a declared or
automatically inferred test obligation. Failures identify the feature, obligation, lane,
command, and artifact needed to diagnose them.

### Maintainer/owner outcome

Maintainers receive stable checks, immutable image provenance, sanitized artifacts, branch
protection, review evidence, and a human-controlled promotion boundary. CI never mutates
`main`, opens a promotion PR, deploys a host, loads a model, or touches `multivac` without the
explicit owner-controlled path. The owner gets a read-only-first staging adapter for `multivac`
with its own unique project name, authorization records, and a rollback handle.

---

## 3. Goals, non-goals, assumptions, constraints

### 3.1 Goals

1. Define branch topology and a state machine for `feature/*`, public `testing`, optional
   `staging` (environment mirror), and protected `main`.
2. Detect every changed feature/subfeature and compute its obligations from a tracked,
   reviewable registry; **fail closed** for unknown behavioral surfaces.
3. Preserve and orchestrate the existing deterministic test pyramid: governance, backend
   contracts, frontend checks, relay, static simulation, real-user syntax, mutation/property
   checks, security benchmark, docs parity, Compose/image checks.
4. Produce a reproducible, host-agnostic, disposable Docker QA artifact with immutable tags,
   provenance, SBOM/attestation where available, isolated volumes, reset/reseed, resource
   limits, and sanitized result retention.
5. Make chat and embedding provider contracts explicit and provider-neutral without weakening
   `assert_vector_space_invariant`, exact model identity, dimensions, or fail-closed behavior.
6. Validate synthetic QA data through the Research Spine in provisional mode, without turning
   fixtures, fake vectors, raw tool success, or generated prose into report evidence.
7. Separate CI, authorized live QA, staging, and optional private adapters.
8. Make human approval the only path that unlocks promotion-PR creation to `main`, with
   required checks and human review still enforced after the PR exists.

### 3.2 Non-goals

- No implementation in this planning stage: no product source, workflow, Compose, test,
  generated-doc, production, or runtime changes.
- No Docker/application-server startup, image build, live provider request, model load,
  model download, `multivac` access/mutation, deploy, merge, push, or PR creation.
- No replacement of the Research Spine with a benchmark-specific shortcut.
- No provider-specific public CI dependency, private URL, token, endpoint fingerprint,
  committed credential, or host-network discovery.
- No automatic merge, automatic promotion, or implicit owner approval.
- No cleanup or mutation of `LLMs/` or `Model_Finetuning/` (protected local artifact folders).
- No attempt to solve all existing gate debt (import cycles, secret-flow findings, large-file
  findings, route/type drift) unless an approved implementation task directly owns them.

### 3.3 Assumptions (verify during implementation)

- GitHub branch protection, environments, CODEOWNERS, artifact policy, and package publication
  settings are available to the repository owner.
- GitHub-hosted Linux runners can run the deterministic lanes and a bounded Compose QA job
  within an approved resource/time budget; Docker-in-Docker, a service-container, or a
  runner-native Docker strategy is acceptable — never mount the host Docker socket into product
  containers.
- `tests/document_corpus/canonical/` contains the governed synthetic corpus and named slices;
  implementation must verify the current manifest rather than hard-code counts.
- The current provider adapter can represent distinct chat and embedding identities, or a
  small explicit contract change is needed; if not, the live lane fails closed rather than
  reusing a local default.
- A public image registry is optional for fork PRs; untrusted PRs get saved/build artifacts but
  never registry write credentials or live secrets.
- `multivac` is owner-local and not referenced in repo code (**UNVERIFIED** its stack); its
  contract is an adapter boundary, not an implementation against a known surface.

### 3.4 Hard constraints (repository policy, non-negotiable)

- CI-safe and live tests are separate in `TESTING.md`; live LLM tests use one explicit
  gitignored profile and a fixed model identity
  (`ISTARA_RUN_REAL_LLM_BENCHMARK=1 pytest tests/integration/test_llm_orchestration_real.py -q`).
- The Research Spine in `docs/architecture/research-validity-contract.md` is the system-wide
  contract for research data (including benchmarks, simulations, chat, integrations, compute
  donation).
- `docs/architecture/self-improvement-governance-contract.md` limits learning to governed,
  project-scoped, verified outcomes.
- `AGENTS.md` forbids private endpoint disclosure, unapproved active model loading, external
  mutation, and cleanup of protected artifact directories.
- `scripts/check_public_tree_clean.py` blocks runtime, database, media, model, and local
  artifact paths from public changes.
- Keep the unrelated `docs/features/site/manifest.json` modification isolated.
- Inference-free checks may prove only the contracts they actually cover.

---

## 4. Current-state evidence and gaps

Consolidated from all three drafts. Repository evidence, not a claim the target already exists.

| # | Area | Evidence (path/command) | Gap / implication |
|---|---|---|---|
| E1 | Existing CI | `.github/workflows/ci.yml` triggered on pushes/PRs to `main`/`staging`; jobs: `governance`, `backend`, `frontend`, `test-harness-js`, `desktop`. | No `testing` trigger, feature-obligation job, QA Compose job, artifact manifest, or promotion gate. |
| E2 | Governance | Governance job runs `check_integrity.py`, `check_ci_governance.py`, `check_test_harness.py`, `security_release_readiness.py`, `security_benchmark.py --fail-on-threshold`, `check_change_obligations.py` (requires `--base`/`--head`). | Broad path/pattern contracts; no executable feature/subfeature registry or per-feature obligation union. |
| E3 | Tests | `TESTING.md` documents the two-family model and a command matrix; `pytest.ini` markers: `acceptance, agentic_eval, benchmark, contract, e2e, live_llm, mutation, security, simulation, ui`. | Documented matrix is not yet the single machine-readable source deciding obligations. |
| E4 | Base Compose | `docker-compose.yml` (services: `ollama, postgres, backend, frontend, caddy, relay, otel-collector, jaeger`; networks `frontend-net/backend-net/data-net`): `read_only`, `cap_drop: ALL`, `pids_limit`, `deploy.resources.limits`, `no-new-privileges`, internal networks. | Defaults backend to `ollama`, uses fixed container names, persists named volumes, mixes local-runtime assumptions with a reusable QA contract. |
| E5 | GPU override | `docker-compose.gpu.yml` exists (opt-in). | QA must not require GPU. |
| E6 | Provider surface | `backend/app/api/routes/llm_servers.py`: typed `provider_type` (`ollama\|lmstudio\|openai_compat\|vllm\|sglang\|llamacpp\|mlx\|anthropic`), `endpoint_security.EndpointPolicy`, `normalized_service_url`, `redacted_endpoint_label`, `field_encryption` for stored keys. | Typed but not yet an enforced capability contract with per-run evidence. |
| E7 | Embedding safety | `backend/app/core/pi_runtime/embeddings_gateway.py::assert_vector_space_invariant` (line 65) raises on mismatch; called at startup (`backend/app/main.py:596-599`); `backend/app/core/embedding_validation.py::validate_embedding_vectors` enforces shape/dimension/finite values. | Contract exists; QA lanes must keep it load-bearing and add dimension/readiness evidence artifacts. |
| E8 | Research Spine | `backend/app/services/research_validity_service.py`: `CodingRun`, `CodingRunCoder`, `EvidenceUnit`, `ReconciliationDecision`, `ResearchEvidenceEdge`; statuses `accepted`, `accepted_after_reconciliation`, `needs_reconciliation`, `needs_human_review`, `blocked`; `backend/app/core/research_validity.py` (`DEFAULT_RELIABILITY_THRESHOLD`, `evaluate_reliability_gate`). | No synthetic provisional-only QA corpus or boundary test today. |
| E9 | Live authorization | `pytest.ini` `live_llm` marker; `TESTING.md` documents one configured live profile (`ISTARA_RUN_REAL_LLM_BENCHMARK=1 …`). | Live contract is env-gated; QA must keep one-target authorization and never make it a public CI default. |
| E10 | Public-tree hygiene | `scripts/check_public_tree_clean.py` blocks `LLMs/`, `Model_Finetuning/`, `backend/data/`, `data/`, `storage/`, `uploads/`, test `.results/`, db/media/model suffixes, `.env*`. | QA artifact export needs an explicit allowlist + redaction scan for runtime artifacts. |
| E11 | Feature docs | `scripts/feature_docs.py --seed-missing --generate-site --check`; tracked output `docs/features/site/manifest.json`. | UI/menu/route/store/agent/skill/model/test changes must keep docs parity enforced. |
| E12 | Security benchmark | `security/control_matrix.json`, `security/SECURITY_BENCHMARK.md`, `tests/test_security_benchmark.py`; CI uploads `security/security_scorecard.json`. | Triggers exist; QA surfaces must extend the matrix only when a control/evidence path/trigger changes. |
| E13 | QA runtime | No `docker-compose.qa*.yml`, no `istara-qa.sh`, no seed/reset scripts found; `infra/` holds only `otel-collector-config.yaml`. | **Gap:** no public disposable QA runtime contract exists. |
| E14 | Live orchestration tests | `tests/integration/test_llm_orchestration_real.py`, `tests/pi_benchmark/live_driver.py` exist — **UNVERIFIED** current pass state; live-lane only. | Not CI-default. |
| E15 | Staging | `.github/workflows/sync-staging.yml` force-pushes `main` → `staging`; no staging environment or host-adapter contract documented (**UNVERIFIED** contents). | `staging` is a mirror, not a pre-main approval branch; must not be called a human gate. |
| E16 | Change-obligation classifier | `scripts/check_change_obligations.py --base <BASE> --head <HEAD>` runs today; also `scripts/public_repo_quality_audit.py --check` reports historical findings (`machine_checkout_path`, `ai_disclaimer`) — currently non-greedy for green status. | Extend, do not duplicate; historical audit findings must be grandfathered or triaged before fail-on-error is enforced (owner-gated). |

**Baseline risk honesty.** Latest CF health output reports inherited failures (Python import
cycles, secret-flow findings, unexpected large files) and existing complexity/route-drift/
type-drift warnings. This plan does not relabel those as caused by the proposed CI system; the
implementation captures a fresh gate baseline, compares post-change output, and either fixes
newly introduced findings, records inherited debt, or adds a time-bounded owner-approved
suppression. The prior readiness record
(`docs/build-stream/2026-08-17-istara-testing-docker-readiness.md`) reports a
`pids_limit`/`deploy.resources` validation conflict under one installed Compose version;
implementation must reproduce or refute it with
`docker compose -f docker-compose.yml config --quiet` before selecting the QA base.

---

## 5. Target architecture and branch/CI state machine

### 5.1 Public surfaces and source-of-truth files

The implementation adds or extends the smallest set of canonical files:

- `testing/feature_coverage.yml` — the **single authority** feature/subfeature registry
  (schema §6.1);
- `scripts/check_feature_obligations.py` — deterministic diff classifier + fail-closed registry
  evaluator, integrated with `check_change_obligations.py` (one classifier, not two);
- `qa/runtime_capabilities.json` — runtime/provider capability declaration consulted by the
  classifier (§8.4);
- `docker-compose.qa.yml` — public disposable QA entrypoint with profiles (§7);
- `qa/` scripts + corpora (seeder, resetter, auditor, redaction scanner, capability check);
- `scripts/istara-qa.sh` — developer entrypoint (up/seed/reset/audit/down/staging);
- `.github/workflows/ci.yml` + a dedicated QA/promotion workflow where permissions are clearer;
- `tests/test_feature_obligations.py`, provider/QA contract tests, synthetic-provisional
  boundary tests, and targeted reset/readiness/artifact tests;
- docs: `TESTING.md`, `testing/TESTING_STRATEGY.md`, `README.md`, `README.pt-BR.md`,
  `CHANGE_CHECKLIST.md`, `Tech.md`, and relevant feature docs — updated only where the contract
  changes. The unrelated `docs/features/site/manifest.json` modification stays isolated.

### 5.2 Branch topology and promotion state machine

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

optional: main --mirror workflow--> staging (environment mirror only, NOT a pre-main
approval branch while sync-staging.yml force-pushes from main)
```

State definitions:

1. **Feature branch:** short-lived branch from `testing`; local obligations may run before
   opening a PR to `testing`. A feature PR may be created by its developer under repository
   policy, but cannot bypass required checks.
2. **Testing integration:** public long-lived branch, canonical for cross-feature deterministic
   checks and disposable QA artifacts. No direct pushes; branch protection requires the
   feature-obligation check and relevant required jobs.
3. **QA candidate:** an immutable `testing` commit with a green evidence manifest, image
   digest, generated Compose config hash, sanitized runtime report, and no unclassified
   behavioral changes. Not yet a release or main PR.
4. **Human-promotion gate:** an owner-approved protected environment or equivalent manual
   dispatch. Approval binds the exact source SHA, evidence manifest, image digest, and intended
   `main` base; recorded in CF and the workflow run. Never inferred from a green check, bot
   comment, or actor identity.
5. **Promotion PR:** created by the workflow only after the gate. Never auto-merged; `main`
   branch protection requires fresh checks, required human review/CODEOWNERS, and an authorized
   human merge.
6. **Staging:** explicitly documented environment mirror (post-main) only, unless the owner
   replaces the current force-sync contract (OD-2).

Cancellation/retry rules:

- PR runs use `concurrency` keyed by workflow, ref, and change class; stale runs cancel before
  they publish or promote anything.
- Push runs on `testing` are immutable by SHA; retries reuse the same source SHA but get a
  distinct run/Compose project name and artifact namespace.
- A failed or cancelled run cannot promote; a retry regenerates the evidence manifest and
  revalidates the digest — no stale green result is reused by branch name alone.
- Fork PRs get read-only permissions, no live-provider secrets; they may run contract-only QA
  and upload a saved/sanitized artifact; registry publication and live lanes are restricted to
  trusted branches/manual dispatch.

---

## 6. Feature/subfeature coverage registry and change-obligation algorithm

### 6.1 Registry schema (single authority: `testing/feature_coverage.yml`)

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
    exceptions: []                       # narrow, reviewed; never backend/frontend/security behavior
    requires_human_review: false         # true for spine/report/security surfaces
    docs_features_update: true           # UI/menu/route/store/agent/skill/model/test behavior
    obligations:
      deterministic: [backend_contracts, research_spine_contract]
      integration: [canonical_corpus: coding-reliability]
      live: [authorized_provider_smoke]  # owner-authorized only
      docs: [feature_docs, testing_docs]
    commands:
      deterministic: [pytest_research_validity]
      live: [qa_spine_smoke]
    acceptance: reportability_requires_reconciled_evidence
    introduced_in: <sha>
    last_verified_sha: <sha>
```

Rules:

- Every behavioral path has one or more owners; overlapping matches allowed only when the union
  is intentional and tested.
- Obligations are named capabilities backed by a command catalog (pinned command, working
  directory, environment policy, live requirement, timeout, artifact allowlist, expected result
  schema).
- A feature can declare `deterministic`, `contract_only`, `synthetic_provisional`,
  `authorized_live`, `security`, `docker`, `docs`, `mutation`, `property`, and `human_review`
  obligations independently. Optional live lanes can never satisfy required deterministic
  obligations.
- Documentation obligations are explicit for UI/menu/route/store/agent/skill/model/test
  behavior; a test-only entry can require test-harness docs without inventing a product page.
- Generated paths map to their source owner; a generated-only diff fails if its source was not
  changed or it is not identified as an expected generator output.
- A narrow allowlist covers truly mechanical changes (version badge, spelling, license,
  generated output) and cannot cover backend/frontend/security behavior.
- CI never silently rewrites the registry; entries carry `introduced_in` and
  `last_verified_sha` so stale coverage is visible.

### 6.2 Runtime capability registry (consulted: `qa/runtime_capabilities.json`)

Per-surface declaration of what is provable deterministically vs. only live (C §5):

```jsonc
{
  "version": 1,
  "surfaces": [
    { "id": "provider.embedding",
      "paths": ["backend/app/core/pi_runtime/embeddings_gateway.py",
                "backend/app/core/embedding_validation.py",
                "backend/app/core/pi_runtime/model_manager.py"],
      "deterministic": ["contract_tests", "dimension_invariant_tests", "embedding_validation_tests"],
      "live_optional": ["dimension_probe_live"],
      "spine_touch": false }
  ]
}
```

Rule: any changed path matching a surface's `paths` triggers that surface's `deterministic`
obligations and its `spine_touch` flag. `spine_touch: true` additionally requires the Research
Spine synthetic-QA lane (§9) and fail-closed behavior when no test file is added/updated for
the surface. `qa/runtime_capabilities.json` itself is registered in governance patterns so
editing it reruns the governance checks.

### 6.3 Change-obligation algorithm (`check_feature_obligations.py --base BASE --head HEAD`)

1. Obtain the diff file list from Git; evaluate deleted paths' owning registry entries too.
2. Normalize separators; classify each path into source, test, docs, generated, runtime-data,
   artifact, workflow, provider, security, or unknown zones.
3. Match changed paths against registry entries and the command catalog.
4. Add obligations per matched feature, plus cross-cutting obligations from change class:
   CI/workflow → governance + workflow validation; provider/embedding/connection/auth/
   WebSocket/MCP/webhook/Docker security → security benchmark; test harness → harness
   governance; UI/route/store/agent/skill/model/test → feature-doc parity.
5. Require a machine-readable feature declaration for new paths or a reviewed registry update
   in the same change. **A path matching no entry is an error, not a warning**, unless in the
   narrow audited allowlist.
6. Compute the union of required commands; emit a stable JSON report: base/head SHA, changed
   paths, matched feature IDs, obligations, skipped optional lanes, unknown paths, required
   artifacts, per-obligation reason.
7. Fail before expensive jobs if `unknown_paths`, `missing_registry_entries`,
   `missing_test_ownership`, `missing_doc_ownership`, or `forbidden_artifacts` is nonempty.
8. Pass the report as a job output so later jobs cannot run a narrower matrix than the
   classifier selected.
9. Validate every selected obligation has a test owner and an artifact/evidence owner (directly
   serves the `test_ownership` gate).
10. Inspect dynamic/string-keyed registrations manually when creating entries; Compass Forge
    graph results are the starting map, not proof every runtime route is found.

### 6.4 Living feature documentation coupling

For UI/menu/route/store/agent/skill/model/test changes: run
`python scripts/feature_docs.py --seed-missing --generate-site --check` and fail the PR if
`docs/features` are stale. `docs/features` and the generated site stay aligned per the AGENTS
contract; `docs/features/site/manifest.json` changes stay isolated.

---

## 7. CI lanes and execution matrix

Cheap-to-expensive, fail-fast graph. All lanes emit JUnit/JSON summaries and a redacted
evidence manifest; raw outputs stay in ignored result roots or short-retention CI artifacts.
Determinism class per lane (C's L1–L8) is preserved.

| Ord | Lane | Determinism | Trigger | Proves | Does not prove |
|---:|---|---|---|---|---|
| 0 | Diff/obligation classifier | D | every PR/push | all changed paths classified, obligations selected | behavior, provider health, runtime quality |
| 1 | Public-tree + secret/artifact guard | D | every run | no blocked files, committed secrets, private endpoint fingerprints, unsafe artifacts | runtime behavior |
| 2 | Governance/docs contract | D | every run; docs lane when selected | integrity, CI governance, harness governance, change obligations, feature-doc parity | live app acceptance |
| 3 | Python compile/unit/contract | D | every run | Python syntax, targeted service/API/security/provider/research contracts | frontend/browser behavior, real model quality |
| 4 | Property/mutation | D | registry-selected | deterministic invariant strength, mutation kill rate | model semantics, production research validity |
| 5 | Frontend | D | selected; full on `testing` | lint, type safety, unit, mutation, production build | backend/provider runtime |
| 6 | Relay + JS harness | D | selected; default on `testing` | Node tests, static simulation, real-user syntax, project-scope checks | browser acceptance against a running app |
| 7 | Compose contract | D | every QA candidate | rendered config, profiles, image refs, healthcheck syntax, no forbidden host dependency | service health, feature workflow |
| 8 | QA image build | D (bounded) | `testing` + approved candidates | reproducible build, digest, SBOM/provenance, non-root/hardening | live provider/model quality |
| 9 | Contract-only QA stack | D (bounded) | `testing` + PRs when Docker obligation selected | disposable orchestration, auth/origin plumbing, reset/reseed, project scope, provisional pipeline plumbing | real provider quality, reportable evidence |
| 10 | Authorized live provider smoke | **Authorized** | manual owner dispatch only | one explicit chat+embedding target, identity, dimensions, route evidence, bounded smoke | broad product release readiness |
| 11 | Full staging acceptance | Live, env-bound | owner-authorized environment only | complete running system, chosen provider, feature acceptance | public CI reproducibility |
| 12 | Evidence/promotion manifest | D | after all required lanes | exact SHA, digest, commands, artifacts, failures, approvals | permission to merge without human review |

### 7.1 Deterministic command catalog

Reuse documented commands from `TESTING.md`; add only commands proven locally first.
Illustrative plan contracts until implementation proves exact working dirs/deps/timeouts:

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

CI must not silently convert a failed command into a warning except where the repository
explicitly labels inherited lint/desktop dependency drift as non-blocking; any exception is
visible in the evidence manifest.

### 7.2 Property/mutation boundaries

Target deterministic invariants only: URI normalization, provider header construction,
route/type contracts, embedding vector shape/finite values, project-scope selection,
reliability calculations, reset naming, obligation-registry classification. Never mutate a
live-provider call or use mutation results as research quality.

### 7.3 E2E/simulation boundaries

The default PR lane runs static simulation checks, not a live browser suite. Full simulation,
E2E (`tests/e2e_test.py`, `tests/simulation/run.mjs`), marathon, or real-user benchmark
requires a running app, a known test token, a named project, and explicit operator
authorization. When selected, the registry requires the relevant scenario(s), canonical corpus
slice, result schema, timeout, and project cleanup; a scenario never falls back to the first
visible project, a fake project ID, or an unscoped route.

---

## 8. Docker artifact, disposable runtime, seed/reset, retention

### 8.1 Image identity and publication

Build with BuildKit/buildx. Manifest includes: source commit SHA/ref; workflow run ID/attempt
and builder version; image name, immutable digest, platform, Dockerfile hash; Compose
file/profile hash and rendered-config hash; dependency lockfile hashes; SBOM location and
provenance/attestation status; provider mode (`contract`, `synthetic_provisional`,
`authorized_live`) — never a secret-bearing endpoint value; test-obligation report and pass/
fail summary.

Tags: immutable `qa-${SHA}` and `qa-run-${RUN_ID}-${ATTEMPT}`. A moving `testing` tag is a
convenience pointer only, never promotion identity. Fork PRs upload a saved image/build record
with short retention; trusted `testing` runs may publish to GHCR only with least-privilege
permissions and provenance. Do not publish untrusted code with write credentials.

Retention (owner-reviewed): PR artifacts 7 days, `testing` artifacts 30 days, release-candidate
evidence 90 days. Retention applies to binaries/logs; never to user research or credentials.

### 8.2 Compose profiles (merged R2)

`docker-compose.qa.yml` reuses existing service definitions (extends/merged file set; base
services never replaced, only overridden):

| Profile | Purpose | Starts |
|---|---|---|
| `contract` (default) | bounded boot, stub provider, no seed | backend, frontend, provider contract stub, ephemeral db |
| `synthetic` | contract + synthetic corpus ingestion (provisional only) | + seeder one-shot |
| `reset` | wipe QA volumes + reseed same corpus | + resetter |
| `audit` | provenance/retention/redaction report | + auditor |
| `live` | one-target authorized live provider (owner opt-in) | + documented live provider; refuses without `QA_LIVE_PROVIDER_TARGET` |
| `ui` | publish loopback UI port (`127.0.0.1:<port>:3000`) | port mapping |
| `team`/`relay`/`mcp`/`autoresearch`/`observability`/`production-ingress` | registry-selected optional profiles, never public default | per obligation |

Constraints: no fixed `container_name`; unique Compose project `istara-qa-<run-id>`; internal
backend/data networks; publish only intended test port(s); parameterized browser/API/WebSocket
origins; data services not published by default; frontend depends on semantic backend
readiness, not only process health; optional services are visibly skipped, never silently
treated as full coverage. Every service reviewed for `read_only`, `tmpfs`, `cap_drop`,
`no-new-privileges`, non-root user, pids/memory/CPU limits, minimal packages, healthchecks.
Product containers never receive the host Docker socket or broad host mounts.

### 8.3 Project names, reset, seed, audit

Each run: `istara-qa-${RUN_ID}-${ATTEMPT}` (validated safe chars/length). Volumes, networks,
containers, artifacts derive from it. No global `docker system prune`; no fixed-volume deletion.

Reset/seed contract:

1. `render` validates required env keys without printing values.
2. `up` creates only the selected project/profile.
3. `wait` checks Docker health + application readiness; records a redacted report.
4. `seed` creates test users and a uniquely named project, uploads named canonical corpus
   slices via the real ingestion path, records source/evidence-unit handles — no private data.
5. `qa` runs only registry-selected obligations.
6. `collect` exports allowlisted JSON/JUnit/trace summaries + provenance manifest.
7. `reset` stops the project and deletes only its generated volumes/networks/artifacts.
8. A second `seed`/`qa` run proves idempotency and no cross-project leakage.

`scripts/reset_test_environment.py` is reused only where its guarded local SQLite contract fits,
behind a thin project-scoped wrapper requiring an explicit confirmation token, rejecting empty/
root paths, printing the target project, and refusing to touch `LLMs/`/`Model_Finetuning/`.

Seed corpus: canonical manifest + named slices (`coding-reliability`, `graph-synthesis`,
`low-consensus-review`), not canned report prose. Seeded artifacts stay visibly provisional
until coding/reliability/reconciliation/Done/report gates pass (§9). The contract lane may use
tiny fixtures only for parser/unit checks, labeled as such.

### 8.4 Failure, retry, and artifact behavior

- `render` failure blocks all later QA jobs.
- Image-build failure blocks runtime; logs record digest/provenance absence, not a misleading
  runtime result.
- Health timeout retains sanitized logs + config metadata, then cleans only the generated
  project unless a debug-retention input is owner-authorized.
- Test failure retains JUnit/JSON summaries and command/env names; raw source text, tokens, and
  full provider responses are never uploaded.
- Retry = new project name + new evidence manifest; cannot overwrite prior artifacts or mark a
  prior failure green.
- Cleanup runs in `always` steps and records completion; cleanup failure is a visible incident,
  never a license for broad host cleanup.

### 8.5 Credentials and redaction

- Secrets enter via gitignored `qa/.env.qa` or host env; QA Compose reads with `${VAR:-}`
  empty defaults for public runs. Stored LLM-server keys already use `field_encryption`; the
  audit profile asserts no plaintext key in logs.
- Public CI runs with **no** secrets. The one live target in CI-adjacent lanes is never a
  private endpoint.
- `qa/scripts/scan_qa_artifacts.py` scans logs/artifacts for URL/endpoint fingerprints, tokens,
  key material; CI and the audit profile fail on hits (extends `check_public_tree_clean.py`
  philosophy to runtime artifacts).
- Run logs/artifacts go to `qa/runs/<run-id>/` (gitignored; **UNVERIFIED** current `.gitignore`
  contents — implementation confirms no conflict with `check_public_tree_clean.py` prefixes
  before merging).

---

## 9. Provider-neutral adapter contracts

### 9.1 Three provider lanes (A taxonomy + C contracts)

1. **Contract-only:** in-process/isolated deterministic adapter proves request/response schema,
   auth-header construction, model selection, timeout/retry handling, malformed-response
   handling, embedding count/shape/finite-value validation, typed fail-closed errors.
   Deterministic vectors allowed solely to test plumbing; labeled contract-only; cannot satisfy
   full-feature research or model-quality acceptance.
2. **Synthetic provisional runtime:** disposable QA stack exercises upload → evidence unit →
   coding/reliability/reconciliation → task review with synthetic corpus material; stub or
   authorized test adapter for plumbing; all artifacts carry provisional state; reports blocked.
   Proves project scope, traceability, reset, UI/API wiring, gate enforcement — not provider
   quality.
3. **Authorized live:** manual, one-target environment with exactly one selected chat provider
   and one selected embedding provider, each with explicit provider kind, endpoint identity,
   model identity, expected dimensions, timeout/retry budget, secret source. Records route
   evidence, model/provider identity, dimension probe, readiness, selected/served state,
   failure state. Fails closed on missing auth, model mismatch, dimension mismatch, unsupported
   capability, or fallback changing vector space. Never scans localhost/LAN; never loads more
   than the configured target.

### 9.2 Chat adapter contract (new pure module, implementation phase)

```python
@dataclass(frozen=True)
class ChatIdentity:
    provider: str      # ollama | lmstudio | openai_compat | vllm | sglang | llamacpp | mlx | anthropic
    api_shape: str     # native | openai_compat | anthropic_compat
    model: str         # EXACT model id, never a wildcard

@dataclass(frozen=True)
class ChatReadiness:
    identity: ChatIdentity
    healthy: bool
    capability_decl: dict   # from qa/runtime_capabilities.json
```

Every QA/CI live probe records `ChatIdentity` verbatim; tests assert logged identity ==
configured identity (`config.py` fields `llm_provider`, `ollama_model`, etc.). **No fallback:**
any QA lane enabling a provider sets `LLM_FALLBACK_ENABLED=false` semantics (config already has
`llm_fallback_api_key`/`resolve_llm_fallback_api_key`); a QA failure is a red lane, never a
silent retry on another provider.

### 9.3 Embedding adapter + dimension invariant

Reuse `assert_vector_space_invariant(dimension_probe=...)`. QA live-embedding lane:
1. probe both engine paths with the exact `default_embed_model()`;
2. require `legacy.model == pi.model` and `legacy.model_dim == pi.model_dim`;
3. on mismatch raise `VectorSpaceInvariantError` and fail the lane;
4. record `{provider, model, dims{legacy, pi}, invariant: ok}` in the probe evidence JSON.
`validate_embedding_vectors` is the per-response guard; QA seed ingestion asserts every stored
vector's dimension equals the declared embedding dimension. Any provider change altering
dimensions is a red lane.

### 9.4 One-target live authorization and capability declarations

- One documented target per run: env `QA_LIVE_PROVIDER_TARGET` naming exactly one
  `ChatIdentity`/embedding model from `qa/runtime_capabilities.json`; the `live` profile
  refuses to start otherwise. Mirrors the existing single-profile live rule in `TESTING.md`.
- `qa/runtime_capabilities.json` (§6.2) is the single declaration of what each surface can
  prove deterministically vs. only live. `scripts/check_qa_capabilities.py` (new) verifies:
  every declared surface has deterministic obligations; no surface claims full-feature
  readiness from contract-only lanes; valid JSON; registered in governance patterns.

### 9.5 Readiness contract (live report green only if all apply)

1. config contains explicit provider/chat/embedding identities;
2. secret present without being printed;
3. provider capability + auth check succeed;
4. chat model identity matches configured target;
5. embedding model identity and expected dimension match;
6. `assert_vector_space_invariant` succeeds;
7. backend reports no local-provider fallback or hidden model load;
8. a bounded authorized chat+embedding request succeeds, content omitted, only handles/metrics
   retained;
9. project scope, route evidence, and rollback handles present.

A contract-only report may check 1/3/5/6 with the stub but must say it did not check real
provider service or model quality.

---

## 10. Research Spine and self-improvement validation

### 10.1 Synthetic source → provisional evidence-unit mapping

- Seed corpus slices live in `qa/corpora/<slice>/` (tracked, small, license-clean), declared in
  `qa/corpora/manifest.json`: `{ slice_id, kind: "synthetic_qa", provenance: "generated|curated",
  span_hashes: [...] }`.
- The QA seeder (`qa/scripts/seed_synthetic.py`) ingests slices through the **real**
  evidence-unit path, so every synthetic span becomes a real `EvidenceUnit` row with
  `source_kind = synthetic_qa` — never a bypass of the ingestion contract. **BLOCKER if the
  ingestion API is not reachable in the QA container without provider calls** — the seeder must
  work with provider stubs for ingestion-only paths; if it cannot, the QA boot profile includes
  a documented stub chat provider.
- Every synthetic artifact is stamped provisional (`is_qa_provisional = true`), and the
  promotion gate (`accepted` / `accepted_after_reconciliation` / `needs_reconciliation` /
  `needs_human_review` / `blocked`) is asserted to **never** be reachable from synthetic rows.
  Enforced by new `tests/test_synthetic_provisional_boundary.py`, which attempts promotion of
  synthetic units and asserts `blocked`/`needs_human_review` with `is_qa_provisional` blocking
  acceptance.

### 10.2 Independent coder / reliability / reconciliation acceptance

- QA lane runs the real multi-coder orchestration (`research_validity_service`) against
  synthetic evidence units with stub coders (deterministic, seeded) for L3 and optionally one
  real provider in the live lane.
- Reliability gate (`evaluate_reliability_gate`, `DEFAULT_RELIABILITY_THRESHOLD`) must be
  *computable* and *reportable* on synthetic units, but synthetic outcomes are **never**
  promoted to Facts/Insights/Recommendations and never reach Reports. A new assertion test walks
  the promotion graph and proves no accepted/reportable artifact can carry
  `is_qa_provisional = true`.

### 10.3 Spine gate table (QA proof vs. forbidden shortcut)

| Spine gate | QA proof | Forbidden shortcut |
|---|---|---|
| Sources | Seed raw canonical synthetic source slices with stable IDs/provenance | Seed only synthesized nugget/report prose |
| Evidence Units | Verify source spans/offsets, participant/method metadata, project ownership | Generated summaries as raw evidence without exact spans |
| Independent coding | Distinct authorized model identities or labeled contract stubs; independent coder outputs | One model response or a fixture treated as consensus |
| Reliability/grounding | Configured reliability metrics on evidence-unit matrices + grounding verification | Pass/fail on final-answer keywords |
| Reconciliation | Seed a low-consensus case; require debate/human reconciliation state | Bulk-accept all findings on a task |
| Accepted artifacts | Accepted atoms/nuggets/facts/insights/recommendations retain evidence links | Every visible artifact marked reportable |
| In Review / Done | Agents cannot mark Done; human approval required | CI or agent completion bypasses human task review |
| Reports | Only accepted/reconciled evidence on human-approved Done tasks included | Report generated from provisional/In Review artifacts |
| Route/evidence | Project, task, coding-run, model, donor, retrieval handles linked | Donor registration or tool success treated as served evidence |
| Self-improvement | Proposals sandboxed, project-scoped, governed, rollbackable | Strong positives learned from raw tool success or synthetic shortcut |

All QA reports carry `contract_only` or `provisional_qa` status; never ingested as production
research evidence or promotion signals. Telemetry is content-free (handles/metrics only).

### 10.4 Preservation guarantees (test-encoded)

- Project scope: synthetic seeds live in a dedicated QA project scope; project-scope contract
  tests (`tests/test_harness_project_scope_contracts.py`) must cover the QA seeder.
- Route evidence: synthetic units carry QA route/evidence handles; verification and governance
  state preserved through reset/reseed.
- Rollback handles: every seed run writes `qa/runs/<run-id>/seed_manifest.json` (span hashes +
  row ids) so a QA database can be recreated bit-identically from the same corpus.
- Self-improvement governance: QA lanes never write to ReasoningBank/Memento stores from
  synthetic outcomes; improvement-governance tests extend to the QA seeder surface.

---

## 11. Security, privacy, and supply-chain controls

| Control | Mechanism | Evidence |
|---|---|---|
| No committed secrets | env-gating + `check_public_tree_clean.py` + `scan_qa_artifacts.py` | scan report in audit profile |
| No private endpoint fingerprints in public artifacts | redaction scan on `qa/runs/` before any upload | scan report |
| Docker socket/privileges | QA containers never mount `/var/run/docker.sock`; `cap_drop: ALL`, `no-new-privileges`, `pids_limit` from base Compose | compose-config gate |
| Network exposure | QA networks `internal: true`; loopback-only UI publish | compose-config gate |
| WebAuthn/origins | CORS/WebSocket/WebAuthn origins fixed to `http://localhost:3000`/`127.0.0.1:3000` (base defaults); origin-fidelity tests in lane 3 | pytest |
| Rate limits | `RATE_LIMIT_ENABLED=true` preserved | health log |
| Supply chain | image provenance + GitHub Attestations (already named in `security/SECURITY_BENCHMARK.md`); SBOM via syft/GitHub-native in audit profile — **UNVERIFIED** existing SBOM tooling | attestation + SBOM artifact |
| Security benchmark triggers | QA files touching auth/LLM-provider/spine surfaces trigger `security_benchmark.py --fail-on-threshold`; update `security/control_matrix.json` + `tests/test_security_benchmark.py` only if a control/evidence path/trigger changes | scorecard |
| Webhook/MCP surfaces | QA defaults keep `MCP_SERVER_ENABLED=false`, `AUTORESEARCH_ENABLED=false` (base defaults) | compose-config gate |
| Secrets in logs | `field_encryption` for stored keys; redaction scan; audit asserts no plaintext key material | scan report |

GitHub/supply-chain specifics: default workflow permissions `contents: read`; grant
packages/attestations/OIDC only to the publication job; pin third-party actions to reviewed
immutable SHAs where policy permits; do not use mutable image tags as acceptance identity;
retain SARIF/security-benchmark output as sanitized evidence; keep Scorecard, dependency
review, and secret scanning aligned.

---

## 12. Staging contract and optional `multivac` adapter

### 12.1 CI vs. staging (explicit separation)

- **CI** = automated pre-merge validation and artifact production (§7). Ephemeral, public,
  reproducible, no owner-host dependency.
- **Staging** = a running integrated environment for acceptance: explicit target,
  network/origin, secret source, provider, data retention, operator, rollback. Never assumed
  merely because a CI image built. Staging evidence is advisory acceptance evidence; no staging
  run can create or promote a PR.

Generic staging adapter phases (A's model):

1. `inventory --read-only`: target identity, OS/container versions, disk/memory budget, active
   Compose projects, listeners/firewall evidence, current image/config digests, rollback
   handles. No mutations.
2. `preflight`: validate artifact digest, required ports/origins, secret availability, provider
   capability, free resources, unique project name.
3. `prepare`: create only a new QA project/env/volume namespace; never modify/stop the old
   stack before acceptance.
4. `run`: start the selected artifact/profile, wait for health/readiness, seed the named
   synthetic corpus, run bounded acceptance checks.
5. `accept`: record health, route/evidence, vector-space, project-isolation, Research Spine
   provisional/reconciliation, browser/API evidence.
6. `rollback`: stop/remove only the new project and its volumes; restore prior env/image
   references if changed; re-run old-stack health. Safe if `prepare` partially completed.

### 12.2 `multivac` adapter — read-only-first, owner-local only

`multivac` is not referenced in repo code (**UNVERIFIED** its stack/endpoints). Contract:

1. **Read-only-first inventory:** inventory-only commands (services, volumes, networks,
   endpoints, listeners) recorded in `qa/runs/<run-id>/multivac_inventory.json` (gitignored).
   No old-stack mutation before acceptance.
2. **New unique project name:** `istara-staging-<run-id>`, never production/old-stack names;
   Compose project isolation guarantees no volume/network collision.
3. **Loopback/tunnel or approved HTTPS:** default loopback-only listener or approved
   tunnel/HTTPS mode; mode recorded; no public exposure without explicit owner approval.
4. **Firewall/listener evidence:** after bring-up, record `ss -ltnp`/`docker port` output and a
   firewall dump; audit profile asserts no unexpected published ports.
5. **No old-stack mutation before acceptance:** first run is inventory + plan (dry-run); write
   operations are a separate owner-approved invocation.
6. **Rollback:** `istara-qa.sh staging --rollback` tears down `istara-staging-<run-id>`
   (`down -v`) and restores nothing on the old stack because nothing was touched — the
   invariant "old stack unchanged" is proven by inventory diff.
7. **Never official:** `multivac` must not appear in public CI workflows, `TESTING.md`,
   `README.md`, or any public doc as the test path; public docs mention only "optional
   owner-local staging adapters".

The owner must explicitly authorize any SSH command, provider call, secret use, host
firewall/listener change, or old-stack stop. If the host cannot meet these conditions, staging
is marked blocked; the public CI contract is never weakened.

---

## 13. Human gate and PR promotion flow

The promotion workflow requires, in order:

1. exact `testing` source SHA and base `main` SHA;
2. successful feature-obligation report with zero unknown paths;
3. all required deterministic jobs green;
4. Compose render, image digest, SBOM/provenance, and contract-QA evidence green;
5. authorized live/staging evidence when the registry marks it required;
6. security benchmark and documentation parity evidence where triggered;
7. no forbidden artifacts or secrets;
8. a generated promotion manifest: command IDs, results, timestamps, artifact paths, image
   digest, residual risks, rollback command;
9. a human approval recorded in a protected GitHub environment **and** as CF evidence.

**Gate bundle (C §12) the human gate consumes:**

```
qa-gate-bundle/<run-id>/
  1. ci-summary.json          (Lane B: jobs passed/failed, durations)
  2. security_scorecard.json  (security_benchmark.py --fail-on-threshold output)
  3. invariant-evidence.json  (assert_vector_space_invariant result + dims, if live lane ran)
  4. seed-manifest.json       (synthetic corpus hash + provisional-flag assertion)
  5. promotion-gate.json      (proof no provisional artifact reached accepted/reportable)
  6. redaction-scan.json      (no secrets/endpoint fingerprints in artifacts)
  7. staging-evidence.json    (optional; multivac inventory diff, listener evidence)
```

Gate rule: the human gate opens **only** when 1–6 are green (7 advisory). The gate record is
stored as CF evidence and in the Build Stream ledger.

After the protected environment approval, the workflow may create the promotion PR. It
re-checks the source SHA immediately before creation so an approval cannot be replayed onto a
different commit. The PR body links the manifest and CF spec/task evidence but never contains
private secrets or raw research data. After creation: `main` branch protection reruns required
checks on the PR merge ref; CODEOWNERS/human review required; no bot merges, force-pushes, or
branch-protection bypasses; a changed SHA invalidates the manifest and requires a new gate;
failed main checks return the candidate to `testing` remediation rather than enabling a direct
push.

---

## 14. Implementation phases with entry/exit gates

Consolidated Phase 0–6 (mapping B's A–E and C's C1–C5 is shown inline). Planning-only until
owner approval (Phase 2 gate).

### Phase 0 — Baseline and contract inventory

**Entry:** owner-approved `CF-SPEC-56`, fresh CF gate baseline, clean scope boundary.
**Work:** confirm branch refs/protection; read workflows/Compose/Dockerfiles; refresh graph;
inventory test ownership and feature-doc obligations; reproduce Compose/provider baseline
without starting services.
**Exit:** baseline report; no new source changes; explicit inherited debt; registry skeleton +
command catalog accepted.
**Verify:**
```bash
compass-forge gate before --task <phase-task>
python scripts/check_integrity.py
python scripts/check_ci_governance.py
python scripts/check_test_harness.py
python scripts/check_feature_obligations.py --base origin/testing --head HEAD --json-out artifacts/feature-obligations.json
docker compose -f docker-compose.yml config --quiet
```
**Rollback:** delete only untracked planning/baseline artifacts; no runtime mutation.

### Phase 1 — Registry and fail-closed obligation enforcement (≈ B-A, C-T1)

**Work:** add `testing/feature_coverage.yml` schema, `scripts/check_feature_obligations.py`,
test-ownership validation, generated-output policy, feature-doc obligation mapping, stable JSON
report, `qa/runtime_capabilities.json` + `check_qa_capabilities.py`, focused tests.
**Exit:** a deliberately unclassified behavioral path fails; a registered representative
backend/frontend/route/agent/skill/model/test change selects the correct obligation union; the
mechanical allowlist stays narrow.
**Verify:** `pytest tests/test_feature_obligations.py -q`; classifier on `HEAD^..HEAD`;
`check_ci_governance.py`; `check_test_harness.py`.
**Rollback:** remove registry enforcement from branch protection only after owner approval;
retain report/tests.

### Phase 2 — Public CI graph and evidence manifest (≈ B-B/C, C-T5)

**Work:** add `testing` triggers, concurrency, path-aware job selection, artifact allowlists,
JUnit/JSON aggregation, sanitized manifest, retry/cancel behavior, least-privilege workflow
permissions.
**Exit:** every required obligation has a job; skipped optional lanes visible; failed/cancelled
runs cannot publish a green manifest; fork PRs cannot access live secrets or registry write
credentials.
**Verify:** `check_ci_governance.py`, `check_test_harness.py`, `check_workflow_contracts.py`,
`check_public_tree_clean.py --base origin/testing --head HEAD`.
**Rollback:** revert workflow changes or remove only the new required check from branch
protection while preserving existing CI.

### Phase 3 — QA Compose/image and disposable lifecycle (≈ C-T2)

**Work:** add `docker-compose.qa.yml` profiles, provider contract stub boundary,
health/readiness, unique project naming, reset/seed/collect/cleanup scripts, image
digest/provenance/SBOM, contract-QA tests. Do not start runtime services until the
implementation owner explicitly authorizes the runtime verification step.
**Exit:** render/build contracts pass; contract-only stack disposable and resettable;
resource/network/security policy checked; artifact manifest binds image/config hashes to source
SHA.
**Verify:**
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

### Phase 4 — Provider-neutral and Research Spine runtime lanes (≈ B-D, C-T3)

**Work:** add provider capability schema, `provider_contracts.py`, chat/embed
identity/dimension readiness, route evidence, one-target live dispatch, provisional synthetic
spine scenarios, negative/fail-closed tests, `test_synthetic_provisional_boundary.py`.
**Exit:** contract-only and synthetic lanes never claim live/model quality; authorized live
lane passes with one configured target or reports a typed blocker; vector-space and Research
Spine gates remain load-bearing.
**Verify:**
```bash
pytest tests/test_model_provider_contract.py tests/test_research_validity_contract.py -q
pytest tests/pi_production/test_w8_embeddings_gateway.py tests/pi_production/test_engine_http_provider.py -q
pytest tests/test_synthetic_provisional_boundary.py tests/test_provider_contracts.py -q
python scripts/run_istara_evals.py --suite static
# manual owner-authorized only; one configured target:
ISTARA_LIVE_LLM_BASE_URL=... python scripts/test_llm_integration.py
```
The last command uses the existing ignored secret loader; the literal endpoint is never
committed or logged. Document the approved invocation without copying a private value.
**Rollback:** disable the live lane/profile and restore prior adapter settings; never remove
dimension checks or replace the provider with synthetic vectors.

### Phase 5 — Optional staging adapter (≈ B-E, C-T4)

**Work:** implement generic inventory/preflight/prepare/accept/rollback adapter and, if
approved, run the owner-local `multivac` adapter read-only-first with a new project.
**Exit:** staging evidence separate from CI; old stack unchanged until acceptance; rollback
proven; no private target detail in public artifacts.
**Verify:** adapter-specific read-only inventory, listener/firewall evidence,
health/vector-space/project-isolation/Research Spine checks, rollback evidence. No public
generic command contains a private host value.
**Rollback:** stop/remove only the new QA project and restore prior known-good references; if
inventory/preflight cannot prove isolation, stop without preparation.

### Phase 6 — Human gate and graduation

**Work:** update living docs, attach CF evidence, record residual risks, request owner approval
through protected environment, create promotion PR only after approval, leave merge to a human.
**Exit:** owner approval, promotion PR, required main checks, docs parity, and rollback
instructions linked; no automatic merge/promotion bypass exists.
**Verify:**
```bash
python scripts/feature_docs.py --seed-missing --generate-site --check
pytest tests/test_feature_docs.py -q
compass-forge gate after --task <phase-task> --summary
compass-forge spec coverage CF-SPEC-56
compass-forge spec drift CF-SPEC-56
```
**Rollback:** close the promotion PR, restore branch-protection/workflow configuration from the
last known-good commit, retain evidence/retro; never force-push or merge as part of automation.

---

## 15. Acceptance criteria (consolidated Given/When/Then)

### Branch and human gate

- **AC-1** Given a feature branch changes a registered behavioral surface, when its PR is
  evaluated, then the obligation classifier selects the union of required checks, exposes the
  report, and blocks unknown/unowned paths.
- **AC-2** Given all required `testing` checks and the QA artifact manifest are green, when no
  owner approval exists for that exact SHA, then no workflow creates a PR to `main`, changes
  `main`, or promotes an artifact.
- **AC-3** Given a protected human approval binds SHA, digest, evidence, and target base, when
  the source SHA is unchanged, then the workflow may create one promotion PR and must not merge
  it.
- **AC-4** Given the source SHA changes after approval, when promotion is attempted, then the
  workflow fails closed and requires a new approval.
- **AC-5** Given `multivac` is unavailable, then public branch CI remains fully runnable with
  public providers and local adapters configured by profile defaults.

### Coverage registry

- **AC-6** Given a new route/store/menu/agent/skill/model/test behavior path with no registry
  owner, when `check_feature_obligations.py` runs, then it exits nonzero and names the
  unclassified path and required registry update.
- **AC-7** Given a registered feature changes, when the classifier emits JSON, then every
  required command, test owner, docs obligation, security trigger, and optional lane is present
  with a reason.
- **AC-8** Given a generated feature-doc file changes without its source or declared generator
  run, when the check runs, then it fails rather than accepting drift.

### Deterministic tests

- **AC-9** Given a backend-only change, when the registry selects backend obligations, then
  targeted backend/auth/project-scope/research tests and relevant governance checks run; live
  services are not started by default.
- **AC-10** Given a frontend/shared behavior change, when the registry selects frontend
  obligations, then lint, type, unit, mutation/build, and relevant feature-doc checks run; full
  browser QA is selected only if the feature declares it.
- **AC-11** Given a test-harness or CI change, when the registry evaluates it, then harness
  governance, workflow contracts, static runner checks, and the security benchmark trigger
  logic run.

### Docker and disposable QA

- **AC-12** Given a supported Compose version and no provider secret, when the contract QA
  profile renders/starts, then it runs without Ollama/LM Studio/local model services and reports
  contract-only status.
- **AC-13** Given a QA run ID, when the stack is created twice, then each run has a unique
  project/volume namespace and reset of one run cannot remove the other.
- **AC-14** Given a failed or cancelled run, when cleanup executes, then only the generated
  project namespace is removed and sanitized evidence records cleanup status.
- **AC-15** Given an image artifact, when the manifest is verified, then its digest, source
  SHA, Compose hash, dependency hashes, provenance, SBOM, and provider mode match; a mutable
  tag alone is insufficient.

### Provider and vector safety

- **AC-16** Given an authorized live configuration lacks a chat/embedding identity, secret,
  capability, or expected dimension, when readiness runs, then it fails closed with a typed
  reason and makes no fallback request.
- **AC-17** Given chat and embedding targets are explicitly configured, when readiness and the
  embedding probe run, then exact provider/model identity, dimensions,
  `assert_vector_space_invariant`, and route evidence are recorded without secret or content
  leakage.
- **AC-18** Given the selected provider is unavailable, when a retry occurs, then it retries
  the same target within its budget or fails; it does not silently switch vector spaces or load
  another model.

### Research Spine and governance

- **AC-19** Given the synthetic canonical corpus is seeded, when provisional QA runs, then raw
  source spans become evidence units, independent coding/reliability and low-consensus
  reconciliation state are exercised, and all outputs remain provisional until their gates
  pass.
- **AC-20** Given an In Review task or unreconciled code application, when reportability is
  checked, then the report route excludes it and identifies the missing gate.
- **AC-21** Given a self-improvement candidate succeeds at tool execution only, when QA records
  telemetry, then it cannot become a positive model/skill signal or report evidence without
  verification, governance, and Research Spine acceptance.

### Security and privacy

- **AC-22** Given a fork PR, when CI runs, then it has no live-provider secret,
  registry-write permission, host Docker socket, or private target access.
- **AC-23** Given an artifact/log/config is collected, when redaction and public-tree checks
  run, then tokens, private URLs, connection strings, raw research content, local databases,
  media, model files, and ignored runtime outputs are rejected.
- **AC-24** Given a Compose stack is running, when network/listener policy is inspected, then
  only intended ingress is published and backend/data services remain internal.
- **AC-25** Given a failed public-tree quality check, then CI blocks and emits a remediation
  report before any container artifact publish.

### Staging / multivac

- **AC-26** Given an owner-invoked staging run with the adapter, when the first invocation
  completes, then only inventory/dry-run artifacts exist, the new project is
  `istara-staging-<run-id>` (unique), listener/firewall evidence is recorded, the old stack is
  byte-identical (inventory diff empty), and rollback tears down only the new project.
- **AC-27** Given the merged branch, when public CI and docs are inspected, then no `multivac`
  name, private URL, token, or endpoint fingerprint appears in any public workflow, README,
  TESTING.md, or committed artifact.

---

## 16. Verification and evidence artifact contract

Every implementation task attaches exact command evidence to Compass Forge and includes these
artifacts in the build manifest where applicable:

- `feature-obligations.json` — base/head, matched IDs, selected obligations, unknown paths,
  owners, commands, reasons;
- `compose-rendered.yaml` only after secret redaction, with no private endpoint values;
- `compose-config.sha256`, `docker-image-digest.txt`;
- `qa-readiness.json` — health/readiness/provider mode, model identity, dimension, route
  handles, project ID, omission/redaction status;
- `junit.xml`, static-check JSON, mutation/property summary, security scorecard, feature-doc
  check output;
- `research-spine-qa.json` — source/evidence-unit/coding/reliability/reconciliation/review/
  report-gate statuses with handles only;
- `promotion-manifest.json` — exact source/base SHA, image digest, required checks, artifact
  hashes, residual risks, rollback command, CF spec/task/evidence refs, human approval record;
- sanitized service logs only on failure, with explicit retention and cleanup status.

Compass Forge evidence rows:

```bash
compass-forge task evidence <task> --type command --summary "<lane>" \
  --payload-json '{"command":"<exact command>","result":"passed","artifact":"<path>"}'
compass-forge task evidence <task> --type gate --summary "post-change architecture gate" \
  --payload-json '{"command":"compass-forge gate after ...","result":"passed or inherited-debt","artifact":"<gate report>"}'
```

The final self-report discloses errors introduced/corrected, corrections received, residual
risks, and readiness. A reviewer records an independent verdict; a live/full change requires
the Build Stream blind-review protocol.

---

## 17. Alternatives, risks, architecture debt, rollback

### 17.1 Alternatives considered

| Alternative | Benefit | Rejection / bounded use |
|---|---|---|
| Do nothing; keep current CI + Compose | Lowest immediate change | Feature obligations stay manual, no disposable public QA artifact, no promotion gate. Not acceptable as target. |
| Extend the benchmark overlay only | Reuses existing testing-oriented files | Overlay alone provides no canonical registry, branch gate, provider-neutral contract, or image provenance. Use as input, not sole source. |
| Provider-specific CI (owner-host model server) | Easy live smoke path | Violates public/host-agnostic contract; leaks availability assumptions; second-class forks. Authorized adapter only. |
| Self-hosted runner for every test | Docker/private network/models reachable | Expands trust boundary, couples CI to one host, risks secret/data contamination. Opt-in staging only, after generic CI is green. |
| Ephemeral GitHub-hosted runner + contract stub | Public, reproducible, least dependency | Cannot prove real model quality; pair with optional authorized live lane and honest labels. **Recommended default.** |
| Permanent shared staging stack as CI target | Rich runtime behavior | Flaky, stateful, hard to isolate, can mutate owner data. Staging separate; unique namespaces/reset. |
| Automatic PR/merge after green CI | Fast throughput | Violates the owner gate. Promotion PR creation only after explicit human approval; never auto-merge. |
| Separate per-feature workflow files | Local ownership | Duplicates orchestration; contradictory obligations. One registry/command catalog + reusable jobs. |
| HTTP QA reset endpoints (B's proposal) | Convenient in-app reset | Adds attack surface; script/Compose-project-scoped reset is primary (R1). |

### 17.2 Failure modes and mitigations

- **Unknown path passes through:** fail-closed classifier; registry test with synthetic new
  path; branch protection requires classifier.
- **Matched feature omits related route/test/docs surface:** ownership coverage tests, Compass
  graph review, explicit registry review for dynamic paths.
- **Contract stub mistaken for live validity:** mode labels, separate check names, promotion
  rule forbidding contract-only satisfaction of live obligations, reviewer acceptance criteria.
- **Provider fallback changes vector space:** exact target binding, fallback disabled in QA,
  invariant probe, typed failure, negative tests.
- **Model download or multiple heavy loads:** no model service in default contract profile,
  one-target live dispatch, no discovery loops, bounded resource limits.
- **Compose project collision/data leak:** generated project names, no fixed containers,
  project-scoped volumes, reset idempotency and cross-project tests.
- **Secret in config/artifact/cache:** redaction test, secret scan, no URL labels/cache keys,
  fork jobs without secrets, artifact allowlist.
- **CI green after cancellation/retry:** immutable SHA/run manifest, concurrency cancellation
  recorded as failure/incomplete, new project and evidence on retry.
- **`staging` force-sync bypasses review:** classify as mirror or replace with owner-approved
  workflow; never call it pre-main approval while force-pushing from `main`.
- **Existing gate debt obscures new drift:** capture baseline, compare after, cite inherited
  findings, separate tasks for unrelated remediation.
- **Canonical corpus becomes a hidden fixture shortcut:** manifest validation, named slices,
  raw-span checks, provisional status, report-gate negative cases.
- **`multivac` old stack mutated prematurely:** read-only inventory, unique project,
  preflight/accept barrier, explicit rollback handles, owner authorization.

### 17.3 Architecture debt (report, don't conceal)

1. Local-provider defaults in Compose/runtime paths remain useful for local development but must
   not become the public QA readiness prerequisite.
2. Path-pattern governance and test-ownership graph ≠ feature registry; migration preserves old
   checks until parity is proven.
3. Branch/workflow docs inconsistently describe `testing`/`staging`/`main`; docs and branch
   protections must be reconciled.
4. Existing gate failures (import cycles, secret-flow findings, large-file findings, route/type
   drift) are separate baseline debt unless the new implementation introduces/touches them.
5. Full browser/real-user/live-provider QA stays environment-bound and cannot be a normal
   public PR requirement without an approved public test provider and resource budget.
6. Two Compose files (base + QA overlay) create a maintenance surface; a future single-file
   merge is out of scope and recorded.

### 17.4 Rollback hierarchy

- **Registry only:** revert registry/classifier commit; keep old governance checks required
  until a green parity run.
- **Workflow only:** disable new optional jobs or revert workflow commit; never remove existing
  security/governance checks.
- **QA artifact:** stop/remove only the generated Compose project and its volumes; retain
  digest/evidence; never broad Docker prune.
- **Provider contract:** disable the live profile and restore prior explicit adapter config;
  never remove invariant/fail-closed checks.
- **Staging adapter:** stop new QA project, remove only its namespace, re-check old stack,
  restore prior image/env references; if old-stack health is not proven, stop and escalate.
- **Promotion:** close/revert the unmerged promotion PR; no force-push to `main`; no automatic
  merge.

---

## 18. Files/surfaces likely to change in implementation

Planning inventory, not permission to edit all paths.

**CI and governance:** `.github/workflows/ci.yml`; new `.github/workflows/qa-artifact.yml` and/or
`promote-testing.yml`; `.github/CODEOWNERS`, branch/environment docs and repository settings
(outside repo, owner-gated); `testing/feature_coverage.yml`; `scripts/check_feature_obligations.py`;
`scripts/check_change_obligations.py`; `scripts/check_ci_governance.py`; `scripts/check_test_harness.py`;
`scripts/check_public_tree_clean.py`; new workflow/obligation contract tests.

**Runtime and artifact:** `docker-compose.qa.yml`; `backend/Dockerfile`, `frontend/Dockerfile`,
`relay/Dockerfile` only if hardening/provenance/runtime issues are demonstrated; `.dockerignore`;
new `qa/` directory (`runtime_capabilities.json`, `corpora/`, `scripts/{seed_synthetic,scan_qa_artifacts,
audit_qa,check_qa_capabilities}.py`); `scripts/istara-qa.sh`; `scripts/reset_test_environment.py`
only if a thin project-safe integration is needed; provider surfaces under `backend/app/config.py`
and `backend/app/core/pi_runtime/` (incl. new `provider_contracts.py`); provider/vector tests
under `tests/test_model_provider_contract.py`, `tests/pi_production/test_w8_embeddings_gateway.py`.

**Tests and evidence:** `tests/test_feature_obligations.py`; `tests/test_qa_stack_contract.py`;
`tests/test_qa_reset_seed.py`; `tests/test_synthetic_provisional_boundary.py`;
`tests/test_provider_contracts.py`; project-scope and harness guards if the runner changes;
`tests/test_research_validity_contract.py` and relevant `tests/pi_production/`; canonical corpus
manifest/selector tests (never raw corpus artifacts in public output); security benchmark
package only if controls/evidence/trigger patterns change.

**Documentation:** `README.md`, `README.pt-BR.md`, `TESTING.md`, `testing/TESTING_STRATEGY.md`,
`testing/TEST_HISTORY.md` (when release-relevant), `CHANGE_CHECKLIST.md`, `Tech.md`,
`DOCUMENTATION.md`, `CONTRIBUTING.md` as required; relevant `docs/features/content/*/architecture.md`
and generated site only if feature/test behavior or feature-doc inventory changes; a living QA
how-to/reference doc under `docs/` if convention requires. The unrelated
`docs/features/site/manifest.json` modification stays isolated and reconciles separately.

---

## 19. Open decisions (owner-gated — implementer must not decide silently)

1. Is `testing` the required integration target for all feature PRs, or may selected feature
   classes target `main` directly after the same checks?
2. Is `staging` retained as a post-main mirror, changed into a protected pre-main branch, or
   retired from the promotion narrative? The current force-sync workflow is not a human gate.
3. Which GitHub environment/reviewer(s) can approve promotion, and may a manual workflow create
   the promotion PR after approval?
4. What are the approved artifact registry and retention values, and are fork-PR image artifacts
   saved to Actions only or published to a public registry?
5. Which Compose version/platform matrix is the supported public contract, and what is the
   maximum CI runtime/resource budget for contract and synthetic QA?
6. Is the deterministic provider stub allowed to run in a public Compose container, or must all
   contract tests remain in-process? Either choice keeps contract-only labels and implies no
   model quality.
7. Which authorized live provider profile and embedding dimension may be used for owner QA, and
   where is its secret stored? No private value belongs in this repo or plan.
8. Which full-feature obligations are blocking on `testing` versus owner-authorized staging only
   (MCP, relay, autoresearch, observability, voice, browser, live LLM)?
9. Should registry ownership be by feature team, subsystem owner, or CODEOWNERS path, and who
   resolves overlapping/dynamic registrations?
10. Are third-party action SHA pinning, SBOM signing, and provenance attestations required
    before the first public artifact or staged as a separate security phase?
11. What is the supported retention policy for QA logs/screenshots/traces, and which sanitized
    evidence may be linked from a public PR?
12. Does the public branch need a provider-backed live smoke at all, or is the initial
    acceptance bar contract-only plus optional owner-authorized live/staging evidence?
13. QA corpus licensing/provenance: approve the synthetic slice sources and
    `generated|curated` labeling before seeding real public data.
14. SBOM tooling choice (syft vs. GitHub-native vs. none for QA images).
15. `multivac` adapter authorization: confirm read-only-first boundary, unique project naming,
    and whether any tunnel/HTTPS mode is ever acceptable.
16. Whether the `live` QA profile may run in GitHub Actions post-merge with the one documented
    public-compatible target, or must always be owner-invoked locally.
17. Whether existing historical `public_repo_quality_audit` findings are grandfathered or
    remediated before full fail-on-error enforcement.

---

## 20. Handoff and next action

This master candidate is a complete MECE synthesis: one architecture, one registry authority,
one consolidated test pyramid with determinism classes, one disposable QA artifact contract,
one provider-neutral contract set, one human-gated promotion flow, one phase/task plan, and one
executable acceptance set. It reconciles all three drafts (R1–R7) and preserves every
load-bearing invariant (Research Spine provisional-only synthetic data,
`assert_vector_space_invariant`, exact model/provider identity, fail-closed provider behavior,
no committed secrets, `multivac` never official, human gate before PR creation).

**Known uncertainties carried forward (labeled, not assumed):** `multivac` surface (UNVERIFIED);
current `.gitignore` contents (UNVERIFIED); live-lane test pass state (UNVERIFIED); existing
SBOM tooling (UNVERIFIED); exact branch-protection state and runner profile behavior (UNVERIFIED).

**Next planning action:** the Conductor cross-votes the master candidates, preserves
disagreement/trade-offs, and pauses at the owner-approval barrier (Phase 2). No implementation
task may run before explicit owner approval. After approval, implementation follows §14 phases
0–6 with CF command evidence, ledger entries, and the human gate at §13.

<!-- /consensus-winning-plan:ISTARA-PUBLIC-CI-TESTING-20260818-4daccbc523dcf574f44a4abfc595ded25ba3fbf085acdf6376de9a505fb3559f -->

## Decision log

<!-- consensus-winner-decision:ISTARA-PUBLIC-CI-TESTING-20260818-4daccbc523dcf574f44a4abfc595ded25ba3fbf085acdf6376de9a505fb3559f -->
DEC-consensus-winner | 2026-08-18 | S1-plan | conductor
Context: three architect cross-votes completed
Decision: slot c selected from ISTARA-PUBLIC-CI-TESTING-20260818-MASTER-C
Why: votes={"a": {"candidate_id": "75a1fc68de62745e5a9aaabe8580d02d071e3a98260a765b37c17f7b0cd91d37", "task": "ISTARA-PUBLIC-CI-TESTING-20260818-VOTE-A", "vote": "c"}, "b": {"candidate_id": "75a1fc68de62745e5a9aaabe8580d02d071e3a98260a765b37c17f7b0cd91d37", "task": "ISTARA-PUBLIC-CI-TESTING-20260818-VOTE-B", "vote": "c"}, "c": {"candidate_id": "1bc3c6cd42ef3e87a77be964f71fe7055cdcc860b437d9af04d96168c829bed6", "task": "ISTARA-PUBLIC-CI-TESTING-20260818-VOTE-C", "vote": "a"}}; tiebreak_used=False; plan_file=docs/build-stream/plans/istara-public-ci-testing-20260818-master-c.md

 <!-- append-only -->

DEC-1 | 2026-08-18 | S0 | owner
Context: The existing `testing` branch/process is documented but not current-by-construction, lacks Docker/feature CI enforcement, and cannot make the private `multivac` server the public testing dependency.
Decision: Create a public, provider-agnostic testing branch and CI system for every Istara developer, with an optional private `multivac` adapter and a human gate before PR creation to `main`.
Why: This separates reusable project infrastructure from one owner's host while preserving a practical private validation path.

DEC-2 | 2026-08-18 | S1 | owner
Context: The requested MECE roster changes the planning perspectives while keeping the implementation, fixer, and reviewer assignments.
Decision: Architect A uses the current Pi model `openai/gpt-5.6-luna` at xhigh; Architect B uses Codex `gpt-5.3-codex-spark` through standalone OAuth Codex CLI at xhigh; Architect C uses Pi `deepseek/deepseek-v4-flash` at high. Implementer, fixer, and reviewer remain on their existing routes. All architect routes have no fallback.
Why: The three primary architect identities are distinct across harness/model, planning remains independently comparative, and stale Kimi quota/fallback paths are removed from this run.

## Ledger <!-- append-only -->

### L-1 | 2026-08-18T00:12:00Z | S1-plan | openai/gpt-5.6-luna | planner | Phase 1
Did: Created the new public CI/testing initiative from the owner request, clarified CI versus staging, defined the public/provider-agnostic boundary, kept `multivac` optional, created CF-SPEC-56 with clarification answers, generated its plan and tasks, and prepared the three-architect Conductor roster.
Result: Planning is ready to dispatch. No source implementation, Docker startup, provider request, model provisioning, PR creation, merge, or `multivac` mutation has occurred.
Verified: `compass-forge spec clarify CF-SPEC-56`; `compass-forge constitution check`; `compass-forge spec plan CF-SPEC-56`; `compass-forge spec tasks CF-SPEC-56`; read-only inspection of current branch/worktrees and Conductor routing; lifecycle and architect brief created in this worktree.
Next: Run the Conductor's three-architect MECE planning stages and stop at the owner-approval barrier.

### L-2 | 2026-08-18T00:21:04Z | S1-plan | deepseek/deepseek-v4-flash | executor | Phase 1 <!-- bsc-ledger:ISTARA-PUBLIC-CI-TESTING-20260818-PLAN-C -->
Did: Wrote the independent Architect C draft plan at docs/build-stream/plans/istara-public-ci-testing-20260818-plan-c.md (774 lines, 20 sections) covering: Docker/QA artifact portability with per-run isolation, seed/reset/audit/retention contracts; provider-neutral chat/embedding adapter contracts with exact identity, no-fallback, dimension/readiness evidence and one-target live authorization; Research Spine-valid provisional-only synthetic QA (is_qa_provisional blocks accepted/reportable states); security/privacy controls incl. redaction scan and provenance; staging contract + read-only-first multivac adapter with rollback; human-gate evidence bundle; implementation phases C1-C5 with entry/exit gates; Given/When/Then acceptance criteria; exact verification commands; alternatives/risks/debt/rollback; files-surfaces list; owner-gated open decisions; task breakdown. Planning-only: no product source, CI workflow, Compose, test, or generated-doc changes; no Docker started, no provider/model calls, no multivac access, no PR/merge.
Result: Draft plan artifact complete for MECE synthesis; lane boundaries stated for A (state machine/gate mechanics) and B (workflow graph). Unverified items explicitly labeled: multivac surface, current .gitignore contents, live-lane pass state, existing SBOM tooling.
Verified: wc -l docs/build-stream/plans/istara-public-ci-testing-20260818-plan-c.md -> 774 lines; grep -c '^## ' -> 20; evidence rows E1-E15 cited from docker-compose.yml, .github/workflows/ci.yml, backend/app/core/pi_runtime/embeddings_gateway.py (assert_vector_space_invariant), backend/app/services/research_validity_service.py, backend/app/api/routes/llm_servers.py, backend/app/core/embedding_validation.py, scripts/check_public_tree_clean.py, scripts/check_change_obligations.py, TESTING.md, pytest.ini, security/SECURITY_BENCHMARK.md; command evidence + self_report recorded via compass-forge.
Next: Conductor synthesizes A+B+C drafts into MECE master candidates, cross-votes, then pauses at the owner-approval gate (Phase 2); no implementation before approval.


### L-3 | 2026-08-18T00:24:01Z | S1-plan | openai/gpt-5.6-luna | planner | Phase 1 <!-- bsc-ledger:ISTARA-PUBLIC-CI-TESTING-20260818-PLAN-A -->
Did: Wrote the independent holistic Architect A draft at `docs/build-stream/plans/istara-public-ci-testing-20260818-plan-a.md` (1,204 lines; 72,853 bytes). It covers public branch and promotion state machine, fail-closed feature/subfeature obligations, deterministic and authorized test lanes, immutable disposable Docker QA artifacts, provider/vector-space safety, Research Spine and self-improvement governance, security, optional `multivac` staging adapter, implementation phases, executable acceptance, evidence, risks, rollback, and owner-gated decisions.
Result: Plan A is ready for MECE synthesis. It recommends a public `testing` integration branch, a registry-driven obligation classifier, distinct contract-only/synthetic-provisional/authorized-live lanes, and a human approval boundary before promotion-PR creation. No product source, CI workflow, Compose file, test, provider, model, server, Docker runtime, or `multivac` state was changed.
Verified: plan structure assertion (passed; 1,204 lines / 72,853 bytes); `python -m py_compile scripts/check_ci_governance.py scripts/check_test_harness.py scripts/check_public_tree_clean.py scripts/check_change_obligations.py` (passed); `python scripts/check_ci_governance.py` (passed); `python scripts/check_test_harness.py` (passed); `docker compose -f docker-compose.yml config --quiet` (failed with the inherited `pids_limit`/`deploy.resources.limits.pids` conflict; no services started).
Next: Conductor synthesizes this draft with Architect B and Architect C, cross-votes the master candidates, and pauses for owner approval before implementation.

### L-4 | 2026-08-18T00:25:39Z | S1-plan | gpt-5.3-codex-spark | planner | Phase 1 <!-- bsc-ledger:ISTARA-PUBLIC-CI-TESTING-20260818-PLAN-B -->
Did: Wrote independent Architect B planning draft at docs/build-stream/plans/istara-public-ci-testing-20260818-plan-b.md, covering public branch/CI state machine, fail-closed feature-obligation mapping, deterministic test automation order, provider-agnostic disposable Docker QA artifact design, Research Spine-compliant provisional lane boundaries, security posture, optional `multivac` adapter boundaries, and acceptance criteria in executable form.
Result: Planning artifact is ready for MECE synthesis; no code/workflow/compose/tests/runtime or provider calls were changed.
Verified: `python scripts/check_public_tree_clean.py --help`; `python scripts/check_change_obligations.py --help`; `python scripts/check_ci_governance.py` (passed); `python scripts/public_repo_quality_audit.py --check` (failed on historical findings unrelated to this draft, treated as pre-existing).
Next: Await synthesis/cross-vote and owner approval checkpoint before any implementation work.

### L-5 | 2026-08-18T00:30:01Z | S1-plan | gpt-5.3-codex-spark | planner | synthesize <!-- bsc-ledger:ISTARA-PUBLIC-CI-TESTING-20260818-MASTER-B -->
Did: Synthesized the consolidated plan artifact at `docs/build-stream/plans/istara-public-ci-testing-20260818-master-b.md` from Architect A/B/C drafts and wrote a unified MECE master plan covering branch/CI state machine, feature-obligation mapping, ordered automation matrix, disposable public Docker QA artifact contract, provider-neutrality checks, Research Spine controls, security controls, human gate, and alternatives.
Result: Planning completion for stage ISTARA-PUBLIC-CI-TESTING-20260818-MASTER-B; no code/workflow/runtime implementation executed.
Verified: `compass-forge --workspace /Users/user/Documents/compass-forge status`; `compass-forge --workspace /Users/user/Documents/compass-forge next`; `compass-forge --workspace /Users/user/Documents/compass-forge work-order --role istara-public-ci-testing-20260818-architect-b --task ISTARA-PUBLIC-CI-TESTING-20260818-MASTER-B`; `compass-forge --workspace /Users/user/Documents/compass-forge spec show CF-SPEC-56`; `ls -la .github/workflows` (discovery evidence); `git branch -a` (branch topology); `cat docs/build-stream/plans/istara-public-ci-testing-20260818-master-b.md`.
Next: Provide this plan to conductor consensus and wait for owner approval before any implementation tasks.


### L-7 | 2026-08-18T00:34:52Z | S1-plan | deepseek/deepseek-v4-flash | executor | Phase 1 <!-- bsc-ledger:ISTARA-PUBLIC-CI-TESTING-20260818-MASTER-C -->
Did: Synthesized the three immutable architect drafts (A: holistic/branch+PR, B: CI automation, C: runtime/provider/spine/security) into one complete MECE master-plan candidate at docs/build-stream/plans/istara-public-ci-testing-20260818-master-c.md (1289 lines, 20 sections, 27 consolidated Given/When/Then acceptance criteria). Recorded 7 explicit reconciliation decisions (R1-R7: script-scoped reset over HTTP QA endpoints; merged Compose profile naming; staging as environment mirror; two-layer registry with one authority + consulted qa/runtime_capabilities.json; live lane owner-dispatched only; consolidated Phase 0-6 plan; single themed acceptance set) and a coverage matrix mapping each master section to its source draft. Grounded all claims in repo evidence (E1-E16) verified at worktree HEAD; carried UNVERIFIED items forward (multivac surface, .gitignore contents, live-lane pass state, SBOM tooling, branch-protection state). Planning-only: no product source, CI workflow, Compose, test, or generated-doc changes; no Docker started, no provider/model calls, no multivac access, no PR/merge.
Result: MECE master-plan candidate C complete for the conductor's cross-vote; conflicts resolved; no voting performed in this synthesize phase.
Verified: wc -l -> 1289 lines; grep -c '^## ' -> 20 sections; 27 AC-* criteria; repo facts re-verified: assert_vector_space_invariant at backend/app/core/pi_runtime/embeddings_gateway.py, ci.yml jobs (governance/backend/frontend/test-harness-js/desktop), scripts/check_change_obligations.py --base/--head, TESTING.md live LLM profile (ISTARA_RUN_REAL_LLM_BENCHMARK=1); command evidence + self_report recorded via compass-forge (workspace /Users/user/Documents/compass-forge).
Next: Conductor cross-votes the three master candidates (A/B/C), preserves disagreement/trade-offs, and pauses at the owner-approval barrier (Phase 2); no implementation before approval.

### L-8 | 2026-08-18T00:38:13Z | S1-plan | gpt-5.3-codex-spark | executor | Phase 1 <!-- bsc-ledger:ISTARA-PUBLIC-CI-TESTING-20260818-VOTE-B -->
Did: Reviewed and compared master-plan candidates A and C against the user request, then issued a MECE cross-vote.
Result: Voted `C` (`75a1fc68de62745e5a9aaabe8580d02d071e3a98260a765b37c17f7b0cd91d37`) to carry the synthesis that explicitly resolves draft conflicts, keeps one canonical feature obligation authority, and preserves explicit owner-gated uncertainty and rollback paths.
Verified: `compass-forge --workspace /Users/user/Documents/compass-forge task evidence ISTARA-PUBLIC-CI-TESTING-20260818-VOTE-B --type plan_vote ...`; `compass-forge --workspace /Users/user/Documents/compass-forge task evidence ISTARA-PUBLIC-CI-TESTING-20260818-VOTE-B --type command --summary "Read work-order payload for vote"`; `compass-forge --workspace /Users/user/Documents/compass-forge task evidence ISTARA-PUBLIC-CI-TESTING-20260818-VOTE-B --type self_report --summary ...`.
Next: Await owner approval for the selected Phase 1 master plan before any implementation work.

## Phase 1 — MECE master planning

**Architect coverage contract:**

- Architect A: whole-system architecture, branch/PR lifecycle, developer experience, feature-to-test obligations, human approval gate, public contract, and synthesis-quality challenge.
- Architect B: CI/test automation, GitHub workflow design, changed-path classification, unit/integration/E2E/simulation/security orchestration, Docker artifact publication, caching, evidence, and PR promotion mechanics.
- Architect C: Compose/runtime portability, provider-neutral model and embedding contracts, Research Spine validity, synthetic data/reset/retention, security/isolation, optional staging adapters, and `multivac` rollback.

**Execution:** Planning-only Conductor dispatch. Architects may write only their assigned plan artifacts and lifecycle planning evidence. They must not modify product source, start Docker, call live providers, provision models, access or mutate `multivac`, create a PR, merge, or deploy.

**Review:** The Conductor will synthesize MECE master candidates, cross-vote them, preserve disagreement and trade-offs, and pause for explicit owner approval. No implementation task may run before approval.

### Review (Phase 1)

**Findings register**

| ID | Sev | Dim | Where | Finding | CF task | Status |
|---|---|---|---|---|---|---|
| P1-F-1 | open | Plan | pending architect plans | Planning coverage and unresolved trade-offs are not yet known. | pending | open |

**Phase summary:** Pending the three-architect MECE run.

## Summary (S5 — whole plan)

Pending. This section is completed only after implementation, validation, human approval, PR creation, and final evidence review.

### L-6 | 2026-08-18T00:34:06Z | S1-plan | openai/gpt-5.6-luna | planner | Phase 1 <!-- bsc-ledger:ISTARA-PUBLIC-CI-TESTING-20260818-MASTER-A -->
Did: Synthesized the three immutable Architect A/B/C snapshots into `docs/build-stream/plans/istara-public-ci-testing-20260818-master-a.md`. Reconciled the whole-system branch/promotion lifecycle, one canonical feature-obligation and capability registry, deterministic CI graph, disposable Docker QA, provider/vector safety, Research Spine and self-improvement governance, security, optional owner-local staging, human approval, implementation phases, executable acceptance, evidence, rollback, open decisions, and a draft coverage matrix. No product source, workflow, Compose, test, generated-doc, runtime, provider, Docker, staging, PR, or production surface was changed.
Result: Candidate A is complete and ready for consensus review. The synthesis deliberately avoids three competing registries by keeping runtime capabilities in the canonical coverage registry; it distinguishes contract-only, synthetic-provisional, authorized-live, and staging claims; and it preserves unverified blockers, owner decisions, inherited gate debt, and rollback boundaries. The lifecycle status now reflects concurrent master-plan review; no existing ledger entry or unrelated worker artifact was edited.
Verified: the plan validator command passed: `python - <<'PY' ... required sections present; no trailing whitespace/TODO/clarification markers ... PY` (1,222 lines / 81,351 bytes); `git status --short --untracked-files=all` showed the candidate plus pre-existing architect instruction/master-plan files. No architecture gate was run because this stage is planning-only and changes no architecture boundary.
Next: Conductor cross-votes master candidates A, B, and C, records the selected candidate ID in `plan_vote` evidence, and pauses for explicit owner approval before implementation.


### L-9 | 2026-08-18T00:39:33Z | S1-plan | openai/gpt-5.6-luna | planner | Phase 1 <!-- bsc-ledger:ISTARA-PUBLIC-CI-TESTING-20260818-VOTE-A -->
Did: Reviewed exactly the two supplied master-plan snapshots (candidate B and candidate C) and recorded a vote for candidate C; no code or plan artifact was edited.
Result: Candidate C selected for explicit R1-R7 reconciliation, coverage matrix, labeled uncertainties, single registry authority, phase gates, acceptance criteria, and rollback/evidence boundaries; ISTARA-PUBLIC-CI-TESTING-20260818-VOTE-A is ready for conductor tally.
Verified: packet validation Python command -> passed; Compass Forge command, plan_vote, and self_report evidence rows -> recorded.
Next: Conductor tallies the cross-votes, freezes the winning master plan, and waits at the owner-approval barrier before implementation.

### L-10 | 2026-08-18T00:39:44Z | S1-plan | deepseek/deepseek-v4-flash | reviewer | Phase 1 <!-- bsc-ledger:ISTARA-PUBLIC-CI-TESTING-20260818-VOTE-C -->
Did: Read both MECE master-plan candidates supplied for the cross-vote (candidate A at docs/build-stream/plans/istara-public-ci-testing-20260818-master-a.md, 1223 lines/24 G/W/T criteria; candidate B at docs/build-stream/plans/istara-public-ci-testing-20260818-master-b.md, 433 lines/6 criteria), verified both are byte-identical to their conductor consensus snapshots (diff -q passed for both), ran a required-term/section/GWT structural validator, and recorded a MECE cross-vote as Architect C (slot c).
Result: Voted candidate A (1bc3c6cd42ef3e87a77be964f71fe7055cdcc860b437d9af04d96168c829bed6): it resolves the known conflicts explicitly (single canonical registry, staging as post-main mirror, fork-PR permission boundary, inherited Compose pids_limit conflict must be reproduced before parity), carries 24 executable Given/When/Then criteria with per-phase (0-6) verification/entry-exit gates/rollback, and specifies the load-bearing safety detail (promotion-manifest.json SHA/base/digest/approval binding, 10-point provider readiness with assert_vector_space_invariant and no-fallback one-target live lane, per-gate Research Spine QA proof table, self-improvement isolation, redaction/public-tree contracts) that candidate B only sketches. Candidate B is coherent but thinner and cites a known-failing verification command (public_repo_quality_audit.py --check) and a ghcr.io registry-write tag that is fork-unsafe. No plan file, spec, or code was edited; planning-only.
Verified: shasum -a 256 on both .compass-forge/conductor/consensus-snapshots/*.md; diff -q master-a.md snapshot-a (identical); diff -q master-b.md snapshot-b (identical); python3 plan validator -> candidate a: 1223 lines / 19 sections / 24 GWT / no missing terms; candidate b: 433 lines / 19 sections / 6 GWT / no missing terms; plan_vote + self_report + command evidence recorded via compass-forge (workspace /Users/user/Documents/compass-forge).
Next: Conductor collects VOTE-A/VOTE-B/VOTE-C, records consensus_result, then pauses at the owner-approval barrier (Phase 2); no implementation before approval.

### L-11 | 2026-08-18T01:06:19Z | S2-execute | gpt-5.3-codex-spark | executor | istara-public-ci-testing-20260818-implementer <!-- bsc-ledger:ISTARA-PUBLIC-CI-TESTING-20260818-IMPL -->
Did: istara-public-ci-testing-20260818-implementer stage on task ISTARA-PUBLIC-CI-TESTING-20260818-IMPL (harness fallback entry; the model did not append one).
Result: task ISTARA-PUBLIC-CI-TESTING-20260818-IMPL finished; worktree head 7f69a1a5.
Verified: see Compass Forge evidence rows on ISTARA-PUBLIC-CI-TESTING-20260818-IMPL (command + self_report + stage_attribution).
Next: conductor advances the pipeline on evidence.


## Phase 3 — Public CI/testing implementation

### Review (S3)

**Findings register**

| ID | Sev | Dim | Where | Finding | CF task | Status |
|----|-----|-----|-------|---------|---------|--------|
| F-1 | Blocker | Completeness | branch diff / implementation task | The implementation stage produced no implementation: the branch diff from `origin/testing` contains only Build Stream planning documents, while every load-bearing artifact required by the approved plan is absent (`testing/feature_coverage.yml`, `scripts/check_feature_obligations.py`, `qa/runtime_capabilities.json`, `docker-compose.qa.yml`, QA lifecycle scripts/tests, and QA/promotion workflows). Therefore the public provider-agnostic CI/testing system is not present and the acceptance criteria cannot be met. | FIX-ISTARA-PUBLIC-CI-TESTING-20260818-REVIEW-r1 | **fixed** (L-13: 37 files, 3645 insertions; classifier/governance/security/compose/test battery green; gate after 0 new failures) |
| F-2 | Major | CI/promotion | `.github/workflows/ci.yml:4-7` | The existing CI remains scoped to pushes/PRs for `main` and `staging` and has no `testing` integration trigger, feature-obligation job, disposable QA artifact job, or human-approval promotion workflow. This independently leaves AC-1 through AC-4 and the approved human-gate contract unenforced even if the planning documents are present. | FIX-ISTARA-PUBLIC-CI-TESTING-20260818-REVIEW-r1 | **fixed** (L-13: ci.yml triggers on `testing`, adds feature-obligations/qa-artifact/qa-contract-stack jobs; qa-artifact.yml builds disposable image; promote-testing.yml human-gated, anti-replay, never auto-merges) |
| F-3 | Major | QA runtime / Research Spine | `docker-compose.qa.yml:35-131`; `scripts/istara-qa.sh:25-65`; `qa/scripts/seed_synthetic.py:50-115` | The advertised disposable QA runtime is not executable end-to-end: the Compose seeder builds from `./backend` but the backend Dockerfile does not contain `qa/scripts/seed_synthetic.py` or `qa/corpora/manifest.json`; `seed_synthetic.py` only writes a local seed manifest and never calls the real evidence-unit ingestion path despite claiming it does; `scripts/istara-qa.sh seed` passes the directory `$ROOT/backend` as a Docker image; and its up/reset path merges the base compose, reintroducing default `ollama` plus fixed `istara-*` container names. | CF-744 | **fixed** (L-17: root-context qa/Dockerfile; seed ingests via real documents evidence-unit path; istara-qa.sh/reset isolated from base compose; coding-run guard blocks provisional promotion) |
| F-4 | Major | Provider safety | `qa/scripts/provider_contracts.py:120-141`; `docker-compose.qa.yml:187-188` | The live readiness contract is not fail-closed as documented: `readiness_gate(identity, {capability: chat})` returns healthy without a `secret_handle`, and the live Compose gate echoes `QA_LIVE_PROVIDER_TARGET` verbatim, which can disclose a private endpoint in logs. | CF-745 | **fixed** (CF-745: readiness_gate fails closed without secret_handle; live gate emits redacted checksum label only) |
| F-5 | Major | Promotion workflow | `.github/workflows/promote-testing.yml:53-63` | The human-gated promotion workflow does not provide `GH_TOKEN`/`GITHUB_TOKEN` to the `gh api` check step. The token is only exported in the later PR-creation step, while the check masks API/authentication errors with `|| true` and then exits because `RUNS` is empty; the only promotion path therefore fails before PR creation on a normal runner. | CF-746 | **fixed** (CF-746: check step binds `GH_TOKEN: secrets.GITHUB_TOKEN` and fails explicitly on API errors; exact-SHA + required-check validation retained) |
| F-6 | Major | CI/promotion integrity | `.github/workflows/ci.yml:54-81` | Adding `testing` to CI triggers also activates the existing governance job's `contents:write` README badge sync and pushes a generated commit to whatever branch triggered the run, including `testing`. That can change `testing` HEAD during or immediately after QA evidence and invalidate the exact-SHA human promotion gate. | CF-747 | **fixed** (L-18: badge-sync writeback restricted to `main`; regression contract in `check_workflow_contracts.py` + 7 tests; workflow contract check green) |
| F-3-r2 | Major | QA runtime / run isolation | `scripts/istara-qa.sh:23,58-67`; `docker-compose.qa.yml:130-141` | The compose-backed seed command does not propagate the script's generated `RUN_ID` into `qa-seeder`; with `QA_RUN_ID` unset, Compose resolves the service value to `local`, so the manifest is written under `qa/runs/local` while the output/project claims `istara-qa-<timestamp>`. The default seed path's collected artifacts and project/evidence handles therefore do not match the run. | FIX-REREV-ISTARA-PUBLIC-CI-TESTING-20260818-REVIEW-r2-F3 | **fixed** (L-21: script exports QA_RUN_ID + seed passes -e; 3 regression tests; manifest lands under qa/runs/<ts>) |
| F-5-r2 | Major | Promotion workflow permissions | `.github/workflows/promote-testing.yml:29-31,54-63` | The new fail-closed `gh api` check has a token but no `actions: read` permission: the workflow's explicit permissions grant only `contents:write` and `pull-requests:write`, while listing Actions runs requires the Actions read scope. A normal runner can therefore receive 403 and still cannot reach PR creation. | FIX-REREV-ISTARA-PUBLIC-CI-TESTING-20260818-REVIEW-r2-F5 | **fixed** (L-20: `actions: read` bound; regression contract in `check_workflow_contracts.py` + 3 tests; workflow contract check green) |

**Verdict:** fail. F-1, F-2, F-4, and F-6 are fixed. The bounded r2 delta review found two new residual Major findings, F-3-r2 and F-5-r2; no finding may be accepted or waived before both fixer tasks and the conductor-created re-review complete.


### L-12 | 2026-08-18T01:20:00Z | S3-review | openai/gpt-5.6-luna | reviewer | Phase 3 <!-- bsc-ledger:ISTARA-PUBLIC-CI-TESTING-20260818-REVIEW -->
Did: Reviewed the implementation task and branch diff against CF-SPEC-56 and the winning MECE plan. No implementation files were changed; added review findings F-1 (Blocker: implementation absent) and F-2 (Major: existing CI has no testing/human-promotion path). No product, Docker, provider, multivac, or runtime surfaces were started or mutated.
Result: FAIL. The branch contains planning artifacts only, so the approved public provider-agnostic testing branch/CI system and its required evidence gates are not present. Findings remain open under FIX-ISTARA-PUBLIC-CI-TESTING-20260818-REVIEW-r1.
Verified: `git diff --no-ext-diff origin/testing...HEAD --name-status` -> only seven planning-document additions; required implementation artifact existence check -> all missing; `python scripts/check_ci_governance.py` -> passed; `python scripts/check_test_harness.py` -> passed; `python scripts/check_integrity.py` -> passed; `python scripts/check_public_tree_clean.py --base origin/testing --head HEAD` -> passed; `python scripts/security_benchmark.py --fail-on-threshold` -> passed (100%); `docker compose -f docker-compose.yml config --quiet` -> failed on inherited pids_limit/deploy.resources conflict; focused pytest -> 15 passed, 1 pre-existing public-repo-quality failure; `compass-forge gate after --task ISTARA-PUBLIC-CI-TESTING-20260818-REVIEW --summary` -> failed with 0 new failures and 80 inherited failures.
Next: Fix F-1/F-2 in FIX-ISTARA-PUBLIC-CI-TESTING-20260818-REVIEW-r1, then run a focused delta re-review; do not promote or create a PR.

### L-13 | 2026-08-18T01:33:06Z | S4-remediate | deepseek/deepseek-v4-flash | remediator | Phase 3 <!-- bsc-ledger:FIX-ISTARA-PUBLIC-CI-TESTING-20260818-REVIEW-r1 -->
Did: Implemented the approved public provider-agnostic testing branch and CI system (CF-SPEC-56 + winning plan) in the shared worktree, closing F-1 and F-2. Added `testing/feature_coverage.yml` (single-authority registry, 10 features + allowlist), `scripts/check_feature_obligations.py` (fail-closed classifier with stable JSON report + test-ownership validation + stdlib YAML-subset parser), `scripts/check_qa_capabilities.py` + `qa/runtime_capabilities.json` (consulted capability declaration), `qa/scripts/{seed_synthetic,reset_qa,scan_qa_artifacts,audit_qa,provider_contracts}.py` + `qa/corpora/manifest.json`, `docker-compose.qa.yml` (contract/synthetic/reset/audit/live/ui profiles, unique project names, no fixed container names, no local model services by default), `scripts/istara-qa.sh` (developer entrypoint), and `scripts/check_workflow_contracts.py`. Fixed the inherited `docker-compose.yml` pids_limit/deploy.resources render conflict (top-level mem_limit/cpus keys). Extended `ci.yml` with a `testing` trigger plus feature-obligations, qa-artifact, and qa-contract-stack jobs; added `qa-artifact.yml` (immutable digest + provenance/SBOM disposable image) and `promote-testing.yml` (protected-environment human gate, anti-replay SHA check, gh pr create, never auto-merges). Extended governance (check_change_obligations/check_ci_governance/check_test_harness) and added 7 test files (63 tests). Updated TESTING.md, testing/TESTING_STRATEGY.md, CHANGE_CHECKLIST.md, README.md, Tech.md.
Result: F-1 flipped open -> fixed (all load-bearing artifacts present; 37 files, 3645 insertions). F-2 flipped open -> fixed (testing trigger, obligation classifier job, QA artifact job, human-gated promotion workflow all in place). Classifier passes on the full diff with zero unknown paths; `docs/features/site/manifest.json` intentionally untouched (isolated per plan).
Verified: `python scripts/check_feature_obligations.py --base origin/testing --head HEAD` -> passed (0 unknown paths, 0 missing test ownership); `check_integrity`/`check_ci_governance`/`check_test_harness`/`check_workflow_contracts`/`check_qa_capabilities`/`check_public_tree_clean` -> all passed; `security_benchmark.py --fail-on-threshold` -> 100% pass; `docker compose -f docker-compose.yml config --quiet` and all QA profiles render -> passed; `pytest tests/test_feature_obligations.py tests/test_qa_capabilities.py tests/test_qa_reset_seed.py tests/test_provider_contracts.py tests/test_qa_artifacts.py tests/test_synthetic_provisional_boundary.py tests/test_qa_stack_contract.py -q` -> 63 passed; focused existing contract tests -> 74 passed + 1 pre-existing public-repo-quality failure (debug_rereview.py, not in fix diff); `compass-forge gate after` -> 0 new failures, 80 inherited (unchanged). Command + self_report evidence recorded on FIX-ISTARA-PUBLIC-CI-TESTING-20260818-REVIEW-r1.
Next: stage exit — F-1/F-2 closed with evidence; conductor dispatches focused delta re-review of the changed surface (do not re-review the full branch).

### L-14 | 2026-08-18T01:39:32Z | S3-review | openai/gpt-5.6-luna | reviewer | Phase 3 <!-- bsc-ledger:REREV-ISTARA-PUBLIC-CI-TESTING-20260818-REVIEW-r1 -->
Did: Performed the bounded delta re-review of the completed FIX task against F-1/F-2, the cited verification evidence, and the immediate QA/provider/promotion seams. Confirmed F-1 is materially present and F-2's testing trigger, classifier, QA jobs, and human-gated promotion workflow exist. Added independent findings F-3 through F-6: the QA runtime/seed path is not executable or Research-Spine-ingesting, provider readiness fails open and logs the live target, the promotion check lacks authentication and masks API errors, and the new testing trigger allows the existing badge-sync writeback to mutate the promotion source.
Result: FAIL. F-1 and F-2 are fixed, but four independent Major findings remain open; CF-744, CF-745, CF-746, and CF-747 are owned by `istara-public-ci-testing-20260818-fixer`. No source fixes, Docker services, live providers, model loads, pushes, merges, PRs, or promotions were performed.
Verified: `python scripts/check_feature_obligations.py --base origin/testing --head HEAD --json-out artifacts/review-feature-obligations.json` plus integrity/governance/harness/workflow/capability/public-tree/security/compile/shell battery -> passed; `pytest tests/test_feature_obligations.py tests/test_qa_capabilities.py tests/test_qa_reset_seed.py tests/test_provider_contracts.py tests/test_qa_artifacts.py tests/test_synthetic_provisional_boundary.py tests/test_qa_stack_contract.py -q` -> 63 passed; all QA overlay profiles render, while the merged `scripts/istara-qa.sh up` service set includes `ollama` and the backend build context lacks `qa/scripts/seed_synthetic.py`; readiness probe returns `healthy=true` without `secret_handle`.
Next: Fix CF-744 through CF-747, then run the conductor-created delta re-review; do not promote or create a PR.

### L-15 | 2026-08-18T01:50:54Z | S4-remediate | deepseek/deepseek-v4-flash | remediator | Phase 3 <!-- bsc-ledger:CF-745 -->
Did: Fixed F-4 in the shared worktree. `qa/scripts/provider_contracts.py` `readiness_gate` now fails closed when `secret_handle` is missing/empty/non-string (healthy=false, `secret_handle` in `missing[]`, `secret_handle_present` recorded without echoing the value). `docker-compose.qa.yml` `qa-live-gate` now emits only a redacted checksum label (`live-target-set=1`, `live-target-label=<cksum>`) instead of echoing `QA_LIVE_PROVIDER_TARGET` verbatim. Updated `tests/test_provider_contracts.py` (fail-closed + positive + empty/non-string cases) and added `test_live_gate_never_echoes_target_verbatim` to `tests/test_qa_stack_contract.py`. NOTE: CF-744 fixer is concurrently editing the same worktree (overlapping files docker-compose.qa.yml / tests/test_qa_stack_contract.py); this commit stages only CF-745 hunks.
Result: F-4 flipped open -> fixed. `readiness_gate(identity, {capability: chat})` now returns healthy=false with missing=["secret_handle"]; runtime probe with a private endpoint prints only `live-target-label=<checksum>`, never the value. 64 passed (QA battery), 19 passed (focused), all 6 QA profiles render, security_benchmark 100%, gate after 0 new failures (80 inherited, unchanged).
Verified: `pytest tests/test_provider_contracts.py tests/test_qa_stack_contract.py -q` -> 19 passed; `pytest tests/test_feature_obligations.py tests/test_qa_capabilities.py tests/test_qa_reset_seed.py tests/test_provider_contracts.py tests/test_qa_artifacts.py tests/test_synthetic_provisional_boundary.py tests/test_qa_stack_contract.py -q` -> 64 passed; `docker compose -f docker-compose.qa.yml --profile <contract|synthetic|reset|audit|live|ui> config --quiet` -> all OK; runtime gate probe of the compose-interpolated command -> exit=1 without target, exit=0 with checksum-only label for a private endpoint; `check_qa_capabilities/check_ci_governance/check_test_harness/check_integrity/check_workflow_contracts/check_public_tree_clean` -> passed; `python scripts/security_benchmark.py --fail-on-threshold` -> pass (100%); `compass-forge gate before/after` -> 0 new failures (80 inherited, unchanged).
Next: stage exit — F-4 closed with evidence; conductor dispatches the delta re-review of CF-745 when the remaining fixer tasks (CF-744/CF-746/CF-747) close.

### L-16 | 2026-08-18T01:56:56Z | S4-remediate | deepseek/deepseek-v4-flash | remediator | Phase 3 <!-- bsc-ledger:CF-746 -->
Did: Fixed F-5 in the shared worktree. `.github/workflows/promote-testing.yml` "Verify required checks are green on the exact SHA" step now binds `env: GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}` and drops the `2>/dev/null || true` masking so `gh api` authentication/API errors abort the step explicitly with the real error (shell -e), while retaining the exact-SHA anti-replay check (previous step) and the required-check case validation (empty/non-success RUNS still fails closed with the explicit "no green CI run" message). No other files changed; concurrent fixer work (CF-744/CF-747) left untouched.
Result: F-5 flipped open -> fixed. Token bound in the check step; API errors now fail the step instead of being masked into a misleading "no green CI run" failure. CF-746 verified with governance battery, shell simulation of all three outcomes (API error aborts, empty RUNS fails closed, green run passes), 68-test QA battery, obligations classifier, security benchmark, and CF gates (0 new issues).
Verified: `python3 -c yaml.safe_load` -> YAML OK; `python3 scripts/check_workflow_contracts.py` / `check_ci_governance.py` / `check_test_harness.py` / `check_integrity.py` / `check_public_tree_clean.py --base origin/testing --head HEAD` -> all passed; fail-closed shell simulation -> API-error abort + empty-RUNS exit 1 + green-run pass; `uv run --project backend python -m pytest tests/test_feature_obligations.py tests/test_qa_stack_contract.py tests/test_qa_capabilities.py tests/test_qa_reset_seed.py tests/test_provider_contracts.py tests/test_qa_artifacts.py tests/test_synthetic_provisional_boundary.py -q` -> 68 passed; `python3 scripts/check_feature_obligations.py --base origin/testing --head HEAD --json-out /tmp/f5-obligations.json` -> passed; `python3 scripts/security_benchmark.py --fail-on-threshold` -> pass; `compass-forge gate before/after --task CF-746 --summary` -> 0 new issues both runs. Command + self_report evidence recorded on CF-746.
Next: stage exit — F-5 closed with evidence; conductor dispatches the delta re-review of CF-746 when the remaining fixer tasks (CF-744/CF-747) close.
### L-17 | 2026-08-18T01:57:27Z | S4-remediate | deepseek/deepseek-v4-flash | remediator | Phase 3 <!-- bsc-ledger:CF-744 -->
Did: Fixed F-3 (CF-744) in the shared worktree. Added `qa/Dockerfile` (repo-root-context image containing the product backend PLUS `qa/scripts` + `qa/corpora`) and pointed qa-backend/qa-seeder/qa-resetter/qa-auditor at `context: .` / `dockerfile: qa/Dockerfile`. `qa/scripts/seed_synthetic.py` now implements the REAL evidence-unit ingestion: `--api-base` creates/reuses a run-scoped QA project, POSTs each raw source span through `POST /api/documents` (which persists EvidenceUnit rows via `persist_document_source_evidence_units`) with `qa_provisional=true`/`source_kind=synthetic_qa`, and records live project/document/evidence-unit handles in the seed manifest; offline plan-only mode is unchanged. `scripts/istara-qa.sh` no longer merges the base compose (`COMPOSE=(docker compose -f "$ROOT/docker-compose.qa.yml")`; up/seed/reset/down stay isolated from ollama + fixed istara-* names) and `seed` runs the compose `qa-seeder` service (never `docker run $ROOT/backend`); `qa/scripts/reset_qa.py` reset targets only `docker-compose.qa.yml`. Backend: `DocumentCreate` gains `qa_provisional`/`source_kind` provenance fields stamped into EvidenceUnit metadata (`is_qa_provisional`/`promotion_blocked`/`source_kind`/`qa_run_boundary`), and `run_independent_coding_run` fails closed to `blocked` for any provisional unit (synthetic rows can never be promoted). New tests: `tests/test_qa_seed_ingestion.py` (5, httpx MockTransport) and `tests/test_qa_provisional_guard.py` (3, incl. real documents-route stamping); extended `tests/test_qa_stack_contract.py` + `tests/test_qa_reset_seed.py`.
Result: F-3 flipped open -> fixed. The disposable QA runtime is now executable end-to-end: the image contains the QA tooling, seed ingests through the real Research Spine path with the provisional boundary enforced, and the QA path is isolated from the base local-model stack. 76 passed (QA battery incl. 8 new tests), 43 passed (documents + research-validity contract), 28 passed (W7 + integrity), all 6 QA compose profiles render, governance/feature-docs parity green, security benchmark 100%, CF gate after 0 new issues.
Verified: `pytest tests/test_feature_obligations.py tests/test_qa_capabilities.py tests/test_qa_reset_seed.py tests/test_provider_contracts.py tests/test_qa_artifacts.py tests/test_synthetic_provisional_boundary.py tests/test_qa_stack_contract.py tests/test_qa_seed_ingestion.py tests/test_qa_provisional_guard.py -q` -> 76 passed; `pytest tests/test_documents.py tests/test_research_validity_contract.py -q` -> 43 passed; `pytest tests/pi_production/test_w7_validation.py tests/test_research_integrity_code_applications.py -q` -> 28 passed; `docker compose -f docker-compose.qa.yml --profile <contract|synthetic|reset|audit|live|ui> config --quiet` -> all OK; `check_feature_obligations/check_ci_governance/check_test_harness/check_workflow_contracts/check_qa_capabilities/check_public_tree_clean/check_integrity` + `feature_docs.py --check` -> all green; `python scripts/security_benchmark.py --fail-on-threshold` -> pass; `compass-forge gate before/after` -> 0 new issues (3 inherited, unchanged).
Next: stage exit — F-3 closed with evidence; conductor dispatches the delta re-review of the CF-744 changed surface when the remaining fixer tasks (CF-746/CF-747) close.

### L-18 | 2026-08-18T02:03:49Z | S4-remediate | deepseek/deepseek-v4-flash | remediator | Phase 3 <!-- bsc-ledger:CF-747 -->
Did: Fixed F-6 (CF-747). `.github/workflows/ci.yml` governance badge-sync writeback is now restricted to the release branch: `if: github.event_name == 'push' && github.ref_name == 'main'` and `git push origin HEAD:main` (was `HEAD:${ github.ref_name }`), so CI never pushes a generated commit to `testing`/`staging` and `testing` HEAD stays the exact, reproducible SHA the human promotion gate verifies. Added the F-6 regression contract to `scripts/check_workflow_contracts.py` (check functions now accept a testable `root`; new checks reject `${ github.ref_name }` writebacks, require the `main`-only gate, and forbid any `git push` targeting `testing`) plus `tests/test_workflow_contracts.py` (7 tests: real workflows pass all checks, CLI exit 0, each regression mutation — ref_name writeback, missing main gate, push to testing, disabled gate — is rejected). Synced docs in the same change: TESTING.md (CI coverage), CHANGE_CHECKLIST.md, SYSTEM_CHANGE_MATRIX.md, README.md, Tech.md.
Result: F-6 open -> fixed. Badge sync no longer mutates the promotion source; the no-direct-push/reproducible-source contract for `testing` is now enforced structurally by the workflow contract check. CF-747 verified with the governance battery, the new 7-test regression suite, YAML parse, security benchmark (exit 0), and feature-docs check. Pre-existing cumulative-branch failures (check_change_obligations governed-evolution trigger via scripts/check_test_harness.py from da030c23; check_feature_obligations unknown paths backend/app/api/routes/documents.py + qa/Dockerfile from CF-744) were confirmed identical at HEAD via stash before/after — my change adds no new failures.
Verified: `python3 scripts/check_workflow_contracts.py` -> passed; `backend/.venv/bin/python -m pytest tests/test_workflow_contracts.py tests/test_feature_obligations.py tests/test_qa_capabilities.py tests/test_qa_stack_contract.py -q` -> 45 passed (7 new); `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` -> YAML OK; `check_ci_governance.py`/`check_test_harness.py`/`check_integrity.py`/`check_public_tree_clean.py --base origin/testing --head HEAD` -> all passed; `python3 scripts/security_benchmark.py --fail-on-threshold` -> exit 0 (triggered_paths: []); `python3 scripts/feature_docs.py --check` -> passed (86 features); `check_change_obligations.py --base origin/testing --head HEAD` -> only pre-existing governed-evolution failure (verified identical at HEAD via stash); `check_feature_obligations.py` -> only pre-existing unknown paths (verified identical at HEAD via stash).
Next: stage exit — F-6 closed with evidence; conductor dispatches the delta re-review of the CF-747 changed surface.

### L-19 | 2026-08-18T02:11:49Z | S3-review | openai/gpt-5.6-luna | reviewer | Phase 3 <!-- bsc-ledger:REREV-ISTARA-PUBLIC-CI-TESTING-20260818-REVIEW-r2 -->
Did: Performed the bounded delta re-review of F-3, F-4, F-5, and F-6 against the completed fixes, their cited evidence, and only the changed QA/provider/workflow seams. Verified the root-context QA image, real documents-to-EvidenceUnit ingestion wrapper, provisional guard, isolated Compose overlay, fail-closed secret-handle readiness, redacted live target output, exact-SHA promotion check, explicit API-error handling, and main-only badge writeback. No Docker services, live providers, model loads, pushes, merges, PRs, or promotions were performed.
Result: **FAIL**. F-4 and F-6 are fixed. The F-3 and F-5 fixes are directionally correct but leave two independent Major defects: the compose seed service loses the generated default run ID, and the promotion workflow omits the Actions read permission required by its new API call. Finding tasks `FIX-REREV-ISTARA-PUBLIC-CI-TESTING-20260818-REVIEW-r2-F3` and `FIX-REREV-ISTARA-PUBLIC-CI-TESTING-20260818-REVIEW-r2-F5` were created for the cast fixer; the conductor must create the next re-review only after both siblings are terminal.
Verified: `pytest tests/test_provider_contracts.py tests/test_qa_stack_contract.py tests/test_qa_seed_ingestion.py tests/test_qa_reset_seed.py tests/test_synthetic_provisional_boundary.py tests/test_workflow_contracts.py -q` -> 51 passed; `python scripts/check_workflow_contracts.py` -> passed; `docker compose -f docker-compose.qa.yml --profile <contract|synthetic|reset|audit|live|ui> config --quiet` -> all six profiles passed; `bash -n scripts/istara-qa.sh && python -m py_compile qa/scripts/seed_synthetic.py qa/scripts/provider_contracts.py qa/scripts/reset_qa.py scripts/check_workflow_contracts.py` -> passed; `env -u QA_RUN_ID docker compose -f docker-compose.qa.yml --profile synthetic config --format json` -> `qa-seeder.env.QA_RUN_ID= local`, confirming F-3-r2; workflow inspection confirms no `actions: read` permission, confirming F-5-r2.
Next: stage exit is blocked on the two new Major finding tasks; do not promote, merge, push, open a PR, or create the re-review.

### L-20 | 2026-08-18T02:32:41Z | S4-remediate | deepseek/deepseek-v4-flash | remediator | Phase 3 <!-- bsc-ledger:FIX-REREV-ISTARA-PUBLIC-CI-TESTING-20260818-REVIEW-r2-F5 -->
Did: Fixed F-5-r2 in the shared worktree. `.github/workflows/promote-testing.yml` top-level `permissions` now binds `actions: read` (retaining `contents: write` + `pull-requests: write`), so the fail-closed required-checks step's `gh api .../actions/runs` call is authorized on a normal runner and the only promotion path can reach PR creation. Added the F-5-r2 regression contract to `scripts/check_workflow_contracts.py` (docstring item 7; `check_promote` requires the `actions/runs` verification step to exist and the explicit `permissions` block to bind the Actions read scope — `write` accepted as it implies read) plus 3 new tests in `tests/test_workflow_contracts.py` (real workflow passes; dropping `actions: read` rejected; removing the `actions/runs` check rejected). Synced docs in the same change: TESTING.md, CHANGE_CHECKLIST.md, SYSTEM_CHANGE_MATRIX.md, README.md, Tech.md. Sibling F-3-r2 fixer's uncommitted files (scripts/istara-qa.sh, tests/test_qa_stack_contract.py) left untouched and NOT committed.
Result: F-5-r2 flipped open -> fixed. `actions: read` bound; workflow contract check green; 10/10 workflow-contract tests pass (3 new); r2 QA battery green; security benchmark and feature-docs parity green; governance battery green; obligations classifier green (0 new unknown paths).
Verified: `python3 scripts/check_workflow_contracts.py` -> passed; `backend/.venv/bin/python -m pytest tests/test_workflow_contracts.py -q` -> 10 passed; `backend/.venv/bin/python -m pytest tests/test_provider_contracts.py tests/test_qa_stack_contract.py tests/test_qa_seed_ingestion.py tests/test_qa_reset_seed.py tests/test_synthetic_provisional_boundary.py tests/test_workflow_contracts.py tests/test_qa_artifacts.py -q` -> 64 passed; `python3 -c yaml.safe_load` on promote-testing.yml -> YAML OK; `python3 scripts/security_benchmark.py --fail-on-threshold` -> passed; `python3 scripts/feature_docs.py --check` -> passed (86 features); check_ci_governance/check_test_harness/check_integrity/check_public_tree_clean -> passed; `check_feature_obligations.py --base origin/testing --head HEAD` -> passed (0 new unknown paths).
Next: stage exit — F-5-r2 closed with evidence; conductor dispatches the r2 re-review only after the sibling F-3-r2 fixer task (FIX-REREV-ISTARA-PUBLIC-CI-TESTING-20260818-REVIEW-r2-F3) is terminal.

### L-21 | 2026-08-18T02:34:44Z | S4-remediate | deepseek/deepseek-v4-flash | remediator | Phase 3 <!-- bsc-ledger:FIX-REREV-ISTARA-PUBLIC-CI-TESTING-20260818-REVIEW-r2-F3 -->
Did: Fixed F-3-r2 in the shared worktree. `scripts/istara-qa.sh` now exports the generated run id (`export QA_RUN_ID="$RUN_ID"` immediately after `RUN_ID="${QA_RUN_ID:-$(date -u +%Y%m%d%H%M%S)}"`) so EVERY compose subprocess (up/seed/reset/audit/down) resolves `${QA_RUN_ID:-local}` to this run's id instead of the `local` fallback, and the `seed` command additionally passes `-e QA_RUN_ID="$RUN_ID"` to the compose `qa-seeder` run (explicit at the point of use). Added 3 regression tests to `tests/test_qa_stack_contract.py`: two text contracts (export line present; `-e QA_RUN_ID="$RUN_ID"` inside cmd_seed) plus a behavioral unset-input test that runs `bash scripts/istara-qa.sh seed` with a stubbed `docker` in PATH and asserts the generated 14-digit run id reaches the seeder invocation via argv AND env, never `local`. No other files touched; sibling F-5-r2 commit (0e5a7f43) untouched.
Result: F-3-r2 flipped open -> fixed. With `QA_RUN_ID` unset the compose overlay now resolves `name: istara-qa-<ts>` and `qa-seeder`/`qa-backend` `QA_RUN_ID=<ts>` (previously `local`), so the seed manifest is written under `qa/runs/<ts>` matching the claimed `istara-qa-<ts>` project and the disposable QA path is end-to-end executable for its default invocation.
Verified: `env -u QA_RUN_ID docker compose -f docker-compose.qa.yml --profile synthetic config --format json` -> BEFORE: name=istara-qa-local, seeder/backend QA_RUN_ID=local (defect reproduced); AFTER (exported run id): name=istara-qa-<ts>, seeder/backend QA_RUN_ID=<ts>; stubbed-docker run of `bash scripts/istara-qa.sh seed` (QA_RUN_ID unset) -> ARGS include `-e QA_RUN_ID=<ts> qa-seeder`, env `QA_RUN_ID=<ts>`, no `QA_RUN_ID=local`/`istara-qa-local`; `pytest tests/test_qa_stack_contract.py -q` -> 19 passed; full QA battery (9 files) -> 79 passed (76 before + 3 new); all 6 QA compose profiles render; `bash -n scripts/istara-qa.sh` -> OK; check_workflow_contracts/check_qa_capabilities/check_ci_governance/check_test_harness -> all green; `compass-forge gate before` -> 0 new issues.
Next: stage exit — F-3-r2 closed with evidence (F-5-r2 closed at L-20); conductor dispatches the r3 delta re-review; do not promote, merge, push, or open a PR.
