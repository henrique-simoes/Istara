# Architect C draft — Runtime / Provider / Spine / Security

**Task:** ISTARA-PUBLIC-CI-TESTING-20260818-PLAN-C
**Role:** istara-public-ci-testing-20260818-architect-c
**Phase:** S1 draft (independent, buildable plan; no implementation)
**Pipeline:** ISTARA-PUBLIC-CI-TESTING-20260818 · Spec CF-SPEC-56
**Lane:** Docker portability, provider-neutral chat/embedding readiness, vector-space safety, Research Spine-valid synthetic QA, isolation/reset/retention, runtime profiles, security boundaries, optional staging adapters, read-only-first `multivac` operational contract.

> This is one of three MECE drafts. Lane A owns the end-to-end branch/PR state machine,
> developer experience, and feature-obligation model; Lane B owns workflow graphs and
> deterministic CI orchestration. This draft supplies the runtime/provider/spine/security
> contracts those lanes depend on, and states its boundaries explicitly so the synthesizer
> can merge without duplication. Every claim cites a repository path or command; items the
> repository cannot substantiate are labeled **UNVERIFIED** or **BLOCKER**.

---

## 1. Executive summary

Istara already has a two-family testing model (`TESTING.md`: CI-safe deterministic checks vs.
live/environment-bound checks), a security benchmark release gate
(`security/SECURITY_BENCHMARK.md`, `scripts/security_benchmark.py --fail-on-threshold`), a
hardened base Compose stack (`docker-compose.yml` with read-only rootfs, `cap_drop: ALL`,
internal networks, pids/memory limits), a fail-closed vector-space invariant
(`backend/app/core/pi_runtime/embeddings_gateway.py::assert_vector_space_invariant`), and a
governed qualitative-coding orchestration service (`backend/app/services/research_validity_service.py`).
What is missing is a **public, provider-agnostic, disposable QA runtime** that:

1. turns the existing Compose stack into a reproducible, per-run-isolated, reset/reseed-capable
   synthetic QA artifact any developer can run without a private host;
2. makes provider neutrality an **enforced contract** — explicit chat/embedding identity,
   dimension and readiness evidence, one-target live authorization, no fallback that changes
   vector space, and a hard separation between contract-only lanes and full-feature runtime lanes;
3. validates the Research Spine with **provisional-only synthetic data** — synthetic sources
   flow through real evidence-unit/coding/reliability/reconciliation gates and can never become
   accepted/reportable artifacts;
4. adds a **staging contract** distinct from CI, with a read-only-first, rollback-scoped
   optional `multivac` adapter for the owner's environment only;
5. keeps a **human approval gate** after automated evidence is green and before any PR is
   created or promoted to `main` (Lane A owns the gate mechanics; this draft defines the
   evidence the gate consumes).

**Developer outcome:** `./istara-qa.sh up` (or `docker compose -f docker-compose.qa.yml up`)
produces an isolated, disposable, seeded Istara QA instance with synthetic corpus slices,
deterministic provider stubs, bounded resource use, and a `qa-reset`/`qa-audit` path — on any
Docker host, with no private endpoint, no committed credential, and no model download beyond
one documented, opt-in target.

**Owner outcome:** a read-only-first `multivac` staging adapter with its own unique project
name, explicit authorization, firewall/listener evidence, and a rollback handle; the private
server never appears in public CI, docs, or workflows as the official test path.

---

## 2. Goals, non-goals, assumptions, constraints

### Goals (lane C)

- **G-C1 Docker portability:** one public QA Compose graph that is reproducible, host-agnostic,
  per-run-isolated (unique project/volume names), and disposable (cleanup contract).
- **G-C2 Provider neutrality with safety:** adapter contracts for chat and embedding that pin
  exact model/provider identity, verify dimensions and readiness, forbid silent fallback that
  changes vector space, and distinguish contract-only lanes from full-feature runtime lanes.
- **G-C3 Research Spine-valid synthetic QA:** synthetic sources map to evidence units and
  provisional states; coding/reliability/reconciliation gates run with real orchestration;
  accepted/reportable artifacts are unreachable from seed shortcuts.
- **G-C4 Security and privacy boundaries:** no committed credentials, no private endpoint
  fingerprints, no secrets in logs/artifacts, no Docker-socket exposure, rate limits, WebAuthn
  origin fidelity, provenance/SBOM where appropriate, security-benchmark triggers preserved.
- **G-C5 Staging contract:** a defined, separate staging environment with public generic
  adapters and an optional host adapter (`multivac`) that is read-only-first and rollback-safe.

### Non-goals (lane C explicitly does not own)

- The branch topology, PR direction, and human-approval state machine mechanics (Lane A).
- The GitHub workflow graphs, caching, and artifact-publishing orchestration (Lane B).
- Any product-source behavior change, CI workflow edit, Compose-file edit, test edit, or
  generated-doc edit in this planning phase.

### Assumptions

- **A1:** The current `docker-compose.yml` (287 lines) is the canonical runtime shape and will
  be *extended* (new QA overlay files), never rewritten.
- **A2:** `scripts/check_public_tree_clean.py` remains the public-commit hygiene gate and its
  blocked-prefix/suffix list stays authoritative for QA artifacts (runtime-data zones are
  already excluded from CF context, per the work-order repo zones).
- **A3:** The `live_llm` pytest marker (`pytest.ini`) and the `ISTARA_RUN_REAL_LLM_BENCHMARK`
  env gate are the existing, enforced live-LLM authorization mechanism
  (`TESTING.md` command matrix).
- **A4:** `assert_vector_space_invariant` (`backend/app/core/pi_runtime/embeddings_gateway.py`)
  is the single source of truth for embedding-space safety and must remain load-bearing in any
  QA runtime lane that exercises embeddings.
- **A5:** `multivac` is owner-local, undocumented in repo code (no code references found —
  **UNVERIFIED** what it runs or how it is reached); its contract is therefore specified as an
  adapter boundary, not as an implementation against a known surface.

### Constraints (non-negotiable, from the brief)

- Planning only: no product source, CI workflow, Compose, test, generated-doc, or runtime
  behavior changes; only the plan artifact + planning evidence.
- No Docker startup, no live provider requests, no model loading/provisioning, no `multivac`
  access or mutation, no PR/merge/deploy.
- Preserve the Research Spine and its gates; preserve source-span traceability, project scope,
  reliability/reconciliation gates, report/Done gates, provisional-only synthetic states.
- Preserve `assert_vector_space_invariant`, embedding-dimension checks, exact model/provider
  identity, fail-closed provider behavior. Never propose synthetic vectors or disabled gates as
  full-feature validation.
- No silent model downloads, no fallback that changes vector space, no hidden host dependency,
  no committed credentials, no private endpoint fingerprints, no secrets in logs/artifacts.
- `LLMs/` and `Model_Finetuning/` are protected local artifact folders (never cleaned, pruned,
  moved, or mounted into public QA).
- Keep the unrelated `docs/features/site/manifest.json` modification isolated.
- Inference-free checks may prove only the contracts they actually cover.

---

## 3. Current-state evidence and gaps

### Evidence (with repository paths)

| # | Claim | Evidence |
|---|---|---|
| E1 | Base Compose is already hardened | `docker-compose.yml`: `read_only: true` + `tmpfs /tmp:noexec,nosuid` on backend/frontend; `cap_drop: ALL` everywhere; `pids_limit`; `deploy.resources.limits` (backend 4G/2 CPUs, frontend 512M); `security_opt: no-new-privileges:true`; networks `backend-net`/`data-net` are `internal: true`. |
| E2 | Profiles exist but are deployment-oriented | `docker-compose.yml`: `profiles: team` (postgres), `production` (caddy), `relay`, `observability` (otel-collector, jaeger). No QA/profile for disposable seeding/reset. |
| E3 | GPU is an opt-in override | `docker-compose.gpu.yml` (12 lines). QA must not require it. |
| E4 | Provider surface is a typed registry | `backend/app/api/routes/llm_servers.py`: `provider_type` in `ollama\|lmstudio\|openai_compat\|vllm\|sglang\|llamacpp\|mlx\|anthropic`; `endpoint_security.EndpointPolicy`, `normalized_service_url`, `redacted_endpoint_label`; `field_encryption` for stored keys. |
| E5 | Embedding safety is fail-closed and startup-bound | `backend/app/core/pi_runtime/embeddings_gateway.py`: `assert_vector_space_invariant(dimension_probe=...)` raises `VectorSpaceInvariantError` on mismatch; `default_embed_model()` must stay in lockstep with `app.core.embeddings._embed_model_name`. Called at startup in `backend/app/main.py:596-599`. |
| E6 | Embedding response validation is pure and strict | `backend/app/core/embedding_validation.py::validate_embedding_vectors`: rejects non-list, ragged, non-numeric, non-finite vectors; enforces `expected_dimension`. |
| E7 | Research Spine orchestration is real, gated code | `backend/app/services/research_validity_service.py`: `CodingRun`, `CodingRunCoder`, `EvidenceUnit`, `ReconciliationDecision`, `ResearchEvidenceEdge`; promotion statuses `accepted`, `accepted_after_reconciliation`, `needs_reconciliation`, `needs_human_review`, `blocked`; `DEFAULT_RELIABILITY_THRESHOLD` and `evaluate_reliability_gate` from `backend/app/core/research_validity.py`. |
| E8 | Test authorization is env-gated | `pytest.ini` markers incl. `live_llm`, `e2e`, `simulation`, `security`; `TESTING.md` documents `ISTARA_RUN_REAL_LLM_BENCHMARK=1 pytest tests/integration/test_llm_orchestration_real.py -q` as the one configured live profile. |
| E9 | CI already runs the spine-adjacent gates | `.github/workflows/ci.yml` governance job: `check_integrity.py`, `check_ci_governance.py`, `check_test_harness.py`, `security_release_readiness.py`, `security_benchmark.py --fail-on-threshold`, `check_change_obligations.py`, PR-scoped security trigger; backend job runs `tests/test_research_validity_contract.py`-class contracts via `tests/` suite and `production_rehearsal.py --json`. |
| E10 | Public-tree hygiene gate exists | `scripts/check_public_tree_clean.py` blocks `LLMs/`, `Model_Finetuning/`, `backend/data/`, `data/`, `storage/`, `uploads/`, test `.results/`, db/media/model suffixes, `.env*`. |
| E11 | Feature-doc regeneration is scripted | `scripts/feature_docs.py --seed-missing --generate-site --check` (mandatory for UI/menu/route/store/agent/skill/model/test changes; tracked output `docs/features/site/manifest.json`). |
| E12 | Security benchmark is a tracked control matrix | `security/control_matrix.json`, `security/SECURITY_BENCHMARK.md`, `tests/test_security_benchmark.py`; CI uploads `security/security_scorecard.json`. |
| E13 | No QA/reset/reseed or disposable-runtime contract exists today | No `docker-compose.qa*.yml`, no `istara-qa.sh`, no seed/reset scripts found; `infra/` holds only `otel-collector-config.yaml`. |
| E14 | Live LLM orchestration tests are present but gated | `tests/integration/test_llm_orchestration_real.py`, `tests/pi_benchmark/live_driver.py` exist (graph-verified) — **UNVERIFIED** their current pass state; they are live-lane, not CI-default. |
| E15 | Staging today is a sync workflow, not a runtime contract | `.github/workflows/sync-staging.yml` exists; no staging environment definition or host-adapter contract documented in repo (**UNVERIFIED** contents). |

### Gaps this plan closes (lane C)

- **Gap-1:** no public, host-agnostic, disposable QA runtime (Compose overlay + scripts) with
  per-run isolation and cleanup.
- **Gap-2:** provider neutrality is implemented (typed registry, health probes) but not
  *enforced as a contract*: no capability declarations file, no dimension/readiness evidence
  artifact, no explicit one-target live authorization record, no no-fallback rule encoded in
  QA lanes.
- **Gap-3:** no synthetic Research Spine QA corpus that is provably provisional-only and
  cannot reach accepted/reportable states.
- **Gap-4:** no staging contract distinguishing CI from a running staging environment, and no
  host-adapter boundary for `multivac`.
- **Gap-5:** QA artifacts (logs, seeds, screenshots) have no retention/redaction contract
  beyond `check_public_tree_clean.py`.

---

## 4. Target architecture — runtime/provider/spine/security view

The full branch/CI state machine is Lane A's deliverable. Lane C defines the **runtime
contracts** that state machine invokes and the **evidence schema** it consumes.

```
┌─────────────────────────── PUBLIC, DETERMINISTIC, HOST-AGNOSTIC ───────────────────────────┐
│  CI lanes (Lane B owns workflow graph)                                                     │
│   • contract-only lanes: no provider calls, no model loading — prove contracts only        │
│   • compose-config + image-build + container-health lanes (bounded, stub-embedding)        │
│   • security-benchmark lane (unchanged triggers, plus new QA surfaces)                     │
└───────────────────────────────────────────┬───────────────────────────────────────────────┘
                                            │ consumes
┌───────────────────────────────────────────▼───────────────────────────────────────────────┐
│  Disposable QA artifact:  docker-compose.qa.yml  (+ docker-compose.qa.<host>.yml overlays)│
│   project: istara-qa-<run-id>   volumes: istara-qa-<run-id>-*   networks: qa-internal      │
│   profiles: core | seed | reset | audit | live-llm (one-target, authorized)                │
│   seed: synthetic corpus slices → provisional Evidence Units (never accepted/reportable)   │
│   reset: wipe + reseed same run-id volumes;  audit: provenance + retention report          │
└───────────────────────────────────────────┬───────────────────────────────────────────────┘
                                            │
┌───────────────────────────────────────────▼───────────────────────────────────────────────┐
│  Provider adapter contracts (pure, testable, no network in contract lanes)                │
│   chat: identity{provider, model, api_shape} → readiness{health, capability_decl}         │
│   embed: identity{provider, model} → dims{probe, expected} → invariant gate                │
│   one-target live authorization: explicit env/flag, single documented target, no fallback │
└───────────────────────────────────────────┬───────────────────────────────────────────────┘
                                            │
┌───────────────────────────────────────────▼───────────────────────────────────────────────┐
│  OPTIONAL owner-local staging adapters (NEVER in public CI or docs as official path)      │
│   multivac-adapter: read-only-first inventory → unique project → loopback/approved TLS    │
│                    → firewall/listener evidence → acceptance → rollback                    │
└────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Branch/CI state machine — lane C boundary contract

Lane A owns the state machine. Lane C requires that it include these states with these
entry/exit conditions (so the runtime contracts are invoked in the right order):

1. `CI-verify` (pre-merge, deterministic): contract lanes + compose-config + image build +
   container health with stub embeddings. **No** provider calls, **no** model download.
   Exit: all green, security scorecard uploaded (`security/security_scorecard.json`).
2. `QA-artifact` (pre-merge, deterministic): build disposable image tagged
   `ghcr.io/istaratech/istara-qa:<sha>-<run-id>` (provenance via GitHub Attestations,
   `security/SECURITY_BENCHMARK.md` already names GitHub Artifact Attestations as the
   provenance standard). Exit: `docker compose config -q` + healthcheck pass on a bounded
   stub-embedding boot.
3. `Authorized-live` (post-merge or owner-invoked, bounded): one-target live provider QA
   against a documented model identity; evidence includes dimension/readiness probe results.
   Exit: probe invariant holds, no fallback used, artifacts redacted.
4. `Human-gate`: owner reviews automated evidence; approval recorded (Lane A mechanics).
5. `Staging` (optional, owner-local): running integrated environment via generic adapters or
   the `multivac` adapter; never a CI dependency.
6. `Promote` → `main` (human-gated only).

---

## 5. Feature/subfeature coverage registry — lane C entries

Lane A owns the full registry algorithm (`check_change_obligations.py` already implements
`TECH_REQUIRED_PATTERNS`/`TEST_REQUIRED_PATTERNS`). Lane C contributes the **runtime
capability registry** that the algorithm must consult: a declarative file
`qa/runtime_capabilities.json` (new) declaring, per surface, the deterministic obligation and
the optional live obligation:

```jsonc
{
  "version": 1,
  "surfaces": [
    {
      "id": "provider.chat",
      "paths": ["backend/app/core/ollama.py", "backend/app/api/routes/llm_servers.py",
                "backend/app/core/llm_router.py", "backend/app/core/pi_runtime/engine.py",
                "backend/app/config.py"],
      "deterministic": ["contract_tests", "provider_identity_tests", "no_fallback_tests"],
      "live_optional": ["one_target_live_probe"],
      "spine_touch": false
    },
    {
      "id": "provider.embedding",
      "paths": ["backend/app/core/pi_runtime/embeddings_gateway.py",
                "backend/app/core/embedding_validation.py",
                "backend/app/core/pi_runtime/model_manager.py"],
      "deterministic": ["contract_tests", "dimension_invariant_tests", "embedding_validation_tests"],
      "live_optional": ["dimension_probe_live"],
      "spine_touch": false
    },
    {
      "id": "spine.coding",
      "paths": ["backend/app/services/research_validity_service.py",
                "backend/app/core/research_validity.py",
                "backend/app/models/research_validity.py"],
      "deterministic": ["contract_tests", "synthetic_provisional_tests", "gate_promotion_tests"],
      "live_optional": [],
      "spine_touch": true
    },
    {
      "id": "runtime.isolation",
      "paths": ["docker-compose*.yml", "qa/**", "scripts/istara-qa*.sh", "infra/**"],
      "deterministic": ["compose_config", "image_build", "container_health", "clean_tree"],
      "live_optional": [],
      "spine_touch": false
    },
    {
      "id": "security.boundary",
      "paths": ["backend/app/core/endpoint_security.py", "backend/app/core/field_encryption.py",
                "security/**", "scripts/security_benchmark.py"],
      "deterministic": ["security_benchmark", "secret_scan", "endpoint_redaction_tests"],
      "live_optional": [],
      "spine_touch": false
    }
  ]
}
```

**Change-obligation rule (lane C contribution):** any changed path matching a surface's
`paths` triggers that surface's `deterministic` obligations **and** its `spine_touch` flag.
`spine_touch: true` additionally requires the Research Spine synthetic-QA lane
(§7) plus `tests/test_research_validity_contract.py`-style contract tests, and **fail-closed**
behavior when no test file is added/updated for the changed surface (consistent with
`check_change_obligations.py`'s `TEST_REQUIRED_PATTERNS` enforcement). Paths matching no
surface remain Lane A's unclassified-fail-closed rule. `qa/runtime_capabilities.json` itself
is registered in `TECH_REQUIRED_PATTERNS`-style governance so editing it requires the
governance checks to rerun.

---

## 6. Automated test pyramid — lane C layers and execution matrix

Lane B owns the workflow ordering and caching. Lane C defines the **layers that involve
runtime, providers, spine, or security**, their determinism class, and their evidence.

| Layer | Determinism | Runs where | Gate | Evidence artifact |
|---|---|---|---|---|
| L1 Provider identity/contract tests | Deterministic (no network) | CI + local | `pytest tests/test_*provider*` | pytest XML |
| L2 Embedding validation + dimension invariant | Deterministic (no network, stub probes) | CI + local | `pytest tests/pi_production/test_w8_embeddings_gateway.py` | pytest XML |
| L3 Research Spine contract tests (synthetic provisional) | Deterministic | CI + local | `pytest tests/test_research_validity_contract.py` + new synthetic-lane tests | pytest XML + seed manifest |
| L4 Security benchmark + secret scan + redaction scan | Deterministic | CI + local | `python scripts/security_benchmark.py --fail-on-threshold`; `scripts/check_public_tree_clean.py --staged`; new `qa/scripts/scan_qa_artifacts.py` | `security/security_scorecard.json` + scan report |
| L5 Compose config + image build | Deterministic (bounded) | CI | `docker compose -f docker-compose.qa.yml config -q`; `docker build` per image | build log, attestation |
| L6 Container health (stub embedding boot) | Deterministic (bounded) | CI | compose up with `LLM_PROVIDER=stub`, healthchecks green | health log |
| L7 One-target live provider probe | Authorized, bounded, opt-in | Owner-invoked / post-merge lane | explicit env + single documented target; probe + invariant evidence | probe JSON (redacted) |
| L8 Full-feature runtime QA (simulation/E2E) | Live, env-bound | Owner-invoked against QA artifact or staging | `tests/simulation/run.mjs`, `tests/e2e_test.py` | run reports (redacted) |

**Contract-only vs. full-feature rule (explicit):** L1–L6 prove contracts and bounded boot
only. They must never be described as full-feature model readiness. Full-feature runtime
readiness requires L7/L8 with a real provider, real vectors through the real gates, and the
invariant probe result recorded. No synthetic vectors (L2 stubs) may be written to a vector
index that any later lane treats as production-like (see §7 provisional rule).

---

## 7. Research Spine-valid synthetic QA (lane C core)

### Synthetic source → provisional evidence-unit mapping

- Seed corpus slices live in `qa/corpora/<slice>/` (new; tracked, small, license-clean).
  Each slice declares, in `qa/corpora/manifest.json`:
  `{ slice_id, kind: "synthetic_qa", provenance: "generated|curated", span_hashes: [...] }`.
- The QA seeder (new `qa/scripts/seed_synthetic.py`) ingests slices through the **real**
  evidence-unit path (the same ingestion code production uses), so every synthetic span becomes
  a real `EvidenceUnit` row with `source_kind = synthetic_qa` — never a bypass of the
  ingestion contract. **BLOCKER if the ingestion API is not reachable in the QA container
  without provider calls** — the seeder must work with provider stubs for ingestion-only paths;
  if it cannot, the QA boot profile must include a documented stub chat provider (see §8).
- Every synthetic artifact is stamped **provisional**: a QA-only marker column/flag set on
  seed creation (`is_qa_provisional = true`), and the promotion gate
  (`research_validity_service` statuses: `accepted` / `accepted_after_reconciliation` /
  `needs_reconciliation` / `needs_human_review` / `blocked`) is asserted to **never** be
  reachable from synthetic rows in the QA lane. This is enforced by a new test
  `tests/test_synthetic_provisional_boundary.py` that attempts promotion of synthetic units and
  asserts `blocked` / `needs_human_review` with `is_qa_provisional` blocking acceptance.

### Independent coder / reliability / reconciliation acceptance

- The QA lane runs the real multi-coder orchestration (`research_validity_service`) against
  synthetic evidence units with stub coders (deterministic, seeded) for L3, and (optionally)
  with one real provider in L7.
- Acceptance for synthetic lanes: reliability gate (`evaluate_reliability_gate`,
  `DEFAULT_RELIABILITY_THRESHOLD`) must be *computable* and *reportable* on synthetic units,
  but synthetic outcomes are **never** promoted to Facts/Insights/Recommendations and never
  reach Reports. A new assertion test walks the promotion graph and proves no
  accepted/reportable artifact can carry `is_qa_provisional = true`.

### Preservation guarantees (test-encoded)

- Project scope: synthetic seeds are created inside a dedicated QA project scope; project-scope
  contract tests (`tests/test_harness_project_scope_contracts.py`) must cover the QA seeder.
- Route evidence: synthetic units carry QA route/evidence handles; verification state and
  governance state are preserved through reset/reseed (see §8 reset contract).
- Rollback handles: every seed run writes `qa/runs/<run-id>/seed_manifest.json` with
  span hashes and row ids so a QA database can be recreated bit-identically from the same
  corpus (provenance, not production data).
- Self-improvement governance: QA lanes must never write to ReasoningBank/Memento
  self-improvement stores from synthetic outcomes, and the improvement-governance tests
  (`tests/test_improvement_governance.py`, already in CI backend job) must extend to the QA
  seeder surface.

---

## 8. Docker artifact / runtime / seed / reset / provider / retention contracts

### 8.1 Public QA artifact

- **Files (new):** `docker-compose.qa.yml` (base overlay that reuses the existing service
  definitions via `extends` or a merged file set), `qa/` directory (scripts, corpora, profiles),
  `scripts/istara-qa.sh` entrypoint.
- **Image tagging/provenance:** CI builds `ghcr.io/istaratech/istara-qa:<git-sha>` with
  `docker/build-push-action` provenance + GitHub Attestations (matches the standard already
  named in `security/SECURITY_BENCHMARK.md`). Local runs build the same tag locally (no push).
- **Host-agnostic:** no hard-coded host paths; all mounts under per-run volume names;
  `host.docker.internal` only in the documented `live-llm` profile (already present in base
  `docker-compose.yml` via `extra_hosts: host.docker.internal:host-gateway` — **keep it
  profile-gated in QA**, never default).

### 8.2 Per-run isolation and disposal

- Compose **project name**: `istara-qa-<run-id>` (run-id = `git-sha-<ts>-<user>` for local,
  `git-sha` for CI). Volumes `istara-qa-<run-id>-<svc>` are created per run and removed with
  the project; nothing is shared with production or other runs.
- **Networks:** QA overlay uses `internal: true` networks only; no published ports except
  one loopback-published UI port in the `ui` profile (`127.0.0.1:<port>:3000`), matching the
  existing internal-network pattern in `docker-compose.yml`.
- **Cleanup:** `scripts/istara-qa.sh down --purge` runs `docker compose -p istara-qa-<run-id>
  down -v --remove-orphans` and prunes the run's volumes; a `--retain <n>` flag keeps the last
  n run logs under `qa/runs/` (gitignored runtime zone).
- **Resource bounds:** reuse the base limits (`deploy.resources.limits`, `pids_limit`); QA
  profile adds an explicit `memory: 2G`/`cpus: "1.5"` bound for the backend so disposable runs
  cannot starve a developer machine.

### 8.3 Compose profiles (QA)

| Profile | Purpose | Starts |
|---|---|---|
| `core` | bounded boot, stub provider, no seed | backend, frontend, stub |
| `seed` | core + synthetic corpus ingestion (provisional only) | + seeder one-shot |
| `reset` | wipe QA volumes + reseed same corpus | + resetter |
| `audit` | provenance/retention report | + auditor |
| `live-llm` | one-target authorized live provider (owner opt-in) | + documented live provider |
| `ui` | publish loopback UI port | port mapping |

### 8.4 Seed / reset / audit

- **Seed:** `istara-qa.sh seed` → `qa/scripts/seed_synthetic.py` with `--corpus qa/corpora`,
  writes provisional evidence units + `qa/runs/<run-id>/seed_manifest.json`.
- **Reset:** `istara-qa.sh reset` → `docker compose -p <run> down -v` + `up --profile seed`,
  recreating volumes bit-identically from the manifest. Reset is destructive only within the
  run's own volumes.
- **Audit:** `istara-qa.sh audit` → `qa/scripts/audit_qa.py` emits: image digest, seed manifest
  hash, provisional-flag count, promotion-gate assertion result, redaction scan result, and a
  retention summary. This file is the QA artifact's provenance record.

### 8.5 Credential injection and secrets

- QA never stores secrets in images or Compose files. Credentials enter via a gitignored
  `qa/.env.qa` (documented in `qa/README.md`) or host env; `docker-compose.qa.yml` reads them
  with `${VAR:-}` defaults that are empty for public runs. Stored LLM-server keys already use
  `field_encryption` (`backend/app/api/routes/llm_servers.py`) — QA audit asserts no plaintext
  key in logs.
- Public CI must run with **no** secrets (empty default paths only); the one live target in
  CI-adjacent lanes is never a private endpoint.

### 8.6 Logs / artifacts / retention

- Run logs and artifacts go to `qa/runs/<run-id>/` (gitignored, matches CF runtime-data zone
  exclusion). A `qa/.gitignore`-style block is added to the root `.gitignore` for
  `qa/runs/` — **UNVERIFIED current `.gitignore` contents**; implementation must confirm no
  conflict with `scripts/check_public_tree_clean.py` blocked prefixes.
- Redaction: `qa/scripts/scan_qa_artifacts.py` scans logs/artifacts for URL/endpoint
  fingerprints, tokens, and key material; CI and the audit profile fail on hits (extends the
  existing `check_public_tree_clean.py` philosophy to *runtime artifacts*, not just staged
  files).

---

## 9. Provider neutrality contracts (lane C core)

### 9.1 Adapter contract (chat)

New pure module `backend/app/core/provider_contracts.py` (implementation phase) defines:

```python
@dataclass(frozen=True)
class ChatIdentity:
    provider: str          # ollama | lmstudio | openai_compat | vllm | sglang | llamacpp | mlx | anthropic
    api_shape: str         # native | openai_compat | anthropic_compat
    model: str             # EXACT model id, never a wildcard

@dataclass(frozen=True)
class ChatReadiness:
    identity: ChatIdentity
    healthy: bool
    capability_decl: dict  # from the runtime capability registry (§5)
```

- **Explicit identity:** every QA/CI live probe records `ChatIdentity` verbatim; tests assert
  the logged identity equals the configured identity (`config.py` fields `llm_provider`,
  `ollama_model`, etc.).
- **No fallback:** any QA lane that enables a provider sets
  `LLM_FALLBACK_ENABLED=false` semantics (config already has `llm_fallback_api_key` +
  `resolve_llm_fallback_api_key` — `backend/app/config.py:139,345`). New tests assert the
  router never silently switches provider/model for a probe. This is the *no-fallback rule*:
  a QA failure is a red lane, never a silent retry on another provider.

### 9.2 Adapter contract (embeddings)

- Reuse the existing gate: `assert_vector_space_invariant(dimension_probe=...)`
  (`backend/app/core/pi_runtime/embeddings_gateway.py`). QA live-embedding lane:
  1. probe both engine paths with the exact `default_embed_model()`;
  2. require `legacy.model == pi.model` and `legacy.model_dim == pi.model_dim`;
  3. on mismatch raise `VectorSpaceInvariantError` and fail the lane (fail-closed);
  4. record `{provider, model, dims{legacy, pi}, invariant: ok}` in the probe evidence JSON.
- **Dimensions evidence:** `validate_embedding_vectors` (`embedding_validation.py`) is the
  per-response guard; QA seed ingestion asserts every stored vector's dimension equals the
  declared embedding dimension. Any provider change that alters dimensions is a red lane.

### 9.3 One-target live authorization

- One documented target per run: env `QA_LIVE_PROVIDER_TARGET` naming exactly one
  `ChatIdentity`/embedding model from the capability registry. The `live-llm` profile refuses
  to start unless `QA_LIVE_PROVIDER_TARGET` is set and matches the registry. This mirrors the
  existing single-profile live rule in `TESTING.md`
  (`ISTARA_RUN_REAL_LLM_BENCHMARK=1` … "the one configured live LLM profile").
- No broad local-network probing: QA live probes only the target's documented endpoint.

### 9.4 Capability declarations

`qa/runtime_capabilities.json` (§5) is the single declaration of what each provider/embedding
surface can prove deterministically vs. only live. A governance check
(`scripts/check_qa_capabilities.py`, new) verifies: every declared surface has deterministic
obligations; no surface claims full-feature readiness from contract-only lanes; the file is
valid JSON and registered in governance patterns.

---

## 10. Security and privacy controls (lane C core)

| Control | Mechanism | Evidence |
|---|---|---|
| No committed secrets | existing env-gating + `check_public_tree_clean.py` + new `scan_qa_artifacts.py` | scan report in audit profile |
| No private endpoint fingerprints in public artifacts | redaction scan on `qa/runs/` before any upload | scan report |
| Docker socket/privileges | QA containers never mount `/var/run/docker.sock`; reuse `cap_drop: ALL`, `no-new-privileges`, `pids_limit` from base Compose | compose-config gate |
| Network exposure | QA networks `internal: true`; loopback-only UI publish | compose-config gate |
| WebAuthn/origins | QA UI/backend CORS origins fixed to `http://localhost:3000`/`127.0.0.1:3000` (already `CORS_ORIGINS` default in `docker-compose.yml`); origin fidelity tests run in L1 | pytest |
| Rate limits | `RATE_LIMIT_ENABLED=true` default preserved (`docker-compose.yml`) | health log |
| Supply chain | image provenance + GitHub Attestations (already the standard in `security/SECURITY_BENCHMARK.md`); SBOM via `docker sbom`-equivalent in audit profile (implementation may use `anchore/syft` or GitHub-native) — **UNVERIFIED** existing SBOM tooling | attestation + SBOM artifact |
| Security benchmark triggers | any QA file touching auth/LLM-provider/spine surfaces triggers `scripts/security_benchmark.py --fail-on-threshold` (same trigger patterns as today); QA additions must update `security/control_matrix.json` + `tests/test_security_benchmark.py` if a control/evidence path/trigger changes | scorecard |
| Webhook/MCP surfaces | QA default keeps `MCP_SERVER_ENABLED=false`, `AUTORESEARCH_ENABLED=false` (`docker-compose.yml` defaults) | compose-config gate |
| Secrets in logs | `field_encryption` for stored keys; redaction scan; audit asserts no plaintext key material | scan report |

---

## 11. Staging contract and optional `multivac` adapter

### 11.1 CI vs. staging (explicit separation)

- **CI** = automated pre-merge validation and artifact production (§6, Lane B workflow graph).
- **Staging** = a running integrated environment for acceptance. Public staging uses generic
  adapters (public provider endpoints a developer configures, or the QA artifact itself with
  `live-llm` profile). Staging is never required for CI and never part of the PR path.
- Evidence from staging (L7/L8) is *advisory acceptance evidence*; the human gate consumes it
  alongside CI evidence but no staging run can create or promote a PR.

### 11.2 `multivac` adapter — read-only-first operational contract (owner-local only)

`multivac` is not referenced anywhere in repo code (grep across `.py/.yml/.yaml/.md/.sh`
finds only this initiative's docs) — **UNVERIFIED** its stack/endpoints. The adapter is
therefore defined as an isolated boundary:

1. **Read-only-first inventory:** before any write, the adapter runs inventory-only commands
   (list services, volumes, networks, endpoints, listeners) and records them in
   `qa/runs/<run-id>/multivac_inventory.json` (gitignored). No old-stack mutation before
   acceptance.
2. **New unique project name:** staging on `multivac` uses `istara-staging-<run-id>`, never
   the production/old stack project names. Compose project isolation guarantees no volume or
   network collision.
3. **Loopback/tunnel or approved HTTPS:** the adapter defaults to a loopback-only listener
   (`127.0.0.1`) or an approved tunnel/HTTPS mode; the mode is recorded. No public exposure
   without explicit owner approval.
4. **Firewall/listener evidence:** after bring-up, the adapter records
   `ss -ltnp`/`docker port` output and a firewall rule dump to the inventory file; the audit
   profile asserts no unexpected published ports.
5. **No old-stack mutation before acceptance:** the adapter's first run is inventory + plan
   (dry-run); write operations are a separate, owner-approved invocation.
6. **Rollback:** `scripts/istara-qa.sh staging --rollback` tears down `istara-staging-<run-id>`
   (down -v) and restores nothing on the old stack because nothing was touched (rollback = the
   invariant "old stack unchanged" proven by inventory diff).
7. **Never official:** `multivac` must not appear in public CI workflows, `TESTING.md`,
   `README.md`, or any public doc as the test path. Public docs mention only "optional
   owner-local staging adapters".

---

## 12. Human gate and PR promotion flow — lane C evidence contract

Lane A owns the state machine. Lane C defines the **evidence bundle the human gate consumes**:

```
qa-gate-bundle/<run-id>/
  1. ci-summary.json          (Lane B: which jobs passed/failed, durations)
  2. security_scorecard.json  (scripts/security_benchmark.py --fail-on-threshold output)
  3. invariant-evidence.json  (assert_vector_space_invariant result + dims, if live lane ran)
  4. seed-manifest.json       (synthetic corpus hash + provisional-flag assertion)
  5. promotion-gate.json      (proof no provisional artifact reached accepted/reportable)
  6. redaction-scan.json      (no secrets/endpoint fingerprints in artifacts)
  7. staging-evidence.json    (optional; multivac inventory diff, listener evidence)
```

Gate rule: the human gate opens **only** when 1–6 are green (7 advisory). The gate record is
stored as Compass Forge evidence and in the Build Stream ledger; a PR may be created only
after the recorded approval (Lane A mechanics; `--force`/auto-merge never allowed).

---

## 13. Implementation phases (lane C scope) with entry/exit gates

| Phase | Scope | Entry gate | Exit gate |
|---|---|---|---|
| C1 | `qa/` scaffolding: `qa/runtime_capabilities.json`, `qa/corpora/` slice (1 small corpus), `qa/scripts/seed_synthetic.py` (ingestion-only, stub-safe), `qa/scripts/scan_qa_artifacts.py`, tests `test_synthetic_provisional_boundary.py` | spec accepted, owner approval of MECE plan | seed + boundary tests green locally; capability file passes governance check |
| C2 | `docker-compose.qa.yml` overlay + `scripts/istara-qa.sh` (up/seed/reset/audit/down) with per-run project/volume names | C1 green | `docker compose -f docker-compose.qa.yml config -q` green; local `istara-qa.sh audit` passes with stub provider; cleanup removes volumes |
| C3 | Provider contracts: `provider_contracts.py`, no-fallback + identity tests, embedding dimension/invariant QA probes | C2 green | contract tests green; live lane refuses without `QA_LIVE_PROVIDER_TARGET` |
| C4 | Staging adapter boundary + `multivac` read-only-first contract scripts (inventory/dry-run/rollback) | C3 green | inventory diff rollback test passes with a throwaway local target; no public-doc mention |
| C5 | CI wiring handoff to Lane B (workflow consumes C1–C4 gates) + docs (`TESTING.md` QA section, `qa/README.md`) + feature-doc regeneration if surfaces change | C4 green | `python scripts/feature_docs.py --seed-missing --generate-site --check` green (only if UI/menu/route/store/agent/skill/model/test surfaces change); `scripts/check_ci_governance.py` green |

Each phase records Compass Forge command evidence and a ledger entry; no phase merges to
`main` without the human gate.

---

## 14. Acceptance criteria (Given/When/Then)

- **AC-C1 (disposability):** Given a developer with Docker only, when they run
  `./scripts/istara-qa.sh up --profile seed` on any host, then the QA artifact boots with
  stub provider, seeds a synthetic provisional corpus, and `./scripts/istara-qa.sh down --purge`
  removes all run volumes — no host-specific path, credential, or model download required.
- **AC-C2 (provider identity):** Given a QA live lane with `QA_LIVE_PROVIDER_TARGET` set,
  when a probe runs, then the recorded `ChatIdentity`/embedding identity equals the configured
  identity exactly, the dimension invariant holds (`legacy.model == pi.model`,
  `legacy.model_dim == pi.model_dim`), and a provider/model mismatch fails the lane (fail-closed).
- **AC-C3 (no fallback):** Given a QA probe with fallback disabled, when the primary provider
  errors, then the lane fails red and no alternate provider/model is contacted silently.
- **AC-C4 (provisional-only spine):** Given a synthetic QA corpus, when the spine
  orchestration runs and a promotion attempt is made, then every synthetic unit stays
  provisional (`is_qa_provisional` blocks `accepted`/`accepted_after_reconciliation`) and no
  Facts/Insights/Recommendations/Reports artifact can be produced from synthetic rows —
  asserted by `tests/test_synthetic_provisional_boundary.py`.
- **AC-C5 (security):** Given a QA run, when artifacts are produced, then
  `scan_qa_artifacts.py` finds no secrets/endpoint fingerprints, `security_benchmark.py
  --fail-on-threshold` passes, and `check_public_tree_clean.py --staged` passes on any QA
  commit; no Docker socket mount; no non-loopback published port in `core`/`seed` profiles.
- **AC-C6 (multivac read-only-first):** Given an owner-invoked staging run with the adapter,
  when the first invocation completes, then only inventory/dry-run artifacts exist, the new
  project is `istara-staging-<run-id>` (unique), listener/firewall evidence is recorded, the
  old stack is byte-identical (inventory diff empty), and rollback tears down only the new
  project.
- **AC-C7 (public neutrality):** Given the merged branch, when public CI and docs are
  inspected, then no `multivac` name, private URL, token, or endpoint fingerprint appears in
  any public workflow, README, TESTING.md, or committed artifact.
- **AC-C8 (human gate):** Given all automated evidence green, when the human gate is
  evaluated, then the gate bundle (§12 items 1–6) is present and approval is recorded before
  any PR creation/promotion; no automatic PR/merge path exists.

---

## 15. Exact verification commands and evidence artifacts

Deterministic, runnable in this phase where safe (no Docker, no providers):

```bash
# Static/contract verification (safe now)
python scripts/check_integrity.py
python scripts/check_ci_governance.py
python scripts/check_test_harness.py
pytest tests/test_research_validity_contract.py -q
pytest tests/pi_production/test_w8_embeddings_gateway.py -q
pytest tests/test_project_scope_contracts.py -q
python scripts/security_benchmark.py --fail-on-threshold --output security/security_scorecard.json
git diff --check

# Implemented-phase verification (after C1–C5)
python qa/scripts/check_qa_capabilities.py            # governance of qa/runtime_capabilities.json
pytest tests/test_synthetic_provisional_boundary.py -q
pytest tests/test_provider_contracts.py -q
docker compose -f docker-compose.qa.yml config -q
./scripts/istara-qa.sh audit                          # provenance + redaction + gate assertions
python qa/scripts/scan_qa_artifacts.py --path qa/runs/<run-id>
```

Evidence artifacts to attach per phase: pytest XML/JUnit, `security/security_scorecard.json`,
`qa/runs/<run-id>/seed_manifest.json`, `qa/runs/<run-id>/invariant-evidence.json`,
`qa/runs/<run-id>/redaction-scan.json`, Compass Forge `task evidence --type command` rows, and
Build Stream ledger entries. Live/provider/`multivac` verifications are owner-authorized
later phases only — never in this planning stage.

---

## 16. Alternatives, risks, architecture debt, rollback

### Alternatives considered (lane C view)

| Alternative | Verdict | Reason |
|---|---|---|
| Do nothing (rely on existing `TESTING.md` + CI) | Rejected | No disposable QA artifact, no enforced provider/spine contracts, no staging boundary; `TESTING.md` is guidance, not enforcement. |
| Extend the benchmark overlay (`testing/` docs + `security_benchmark.py` only) | Partial | Reuses existing gates but adds no runtime artifact or provider neutrality enforcement. Keep as *input* (capability declarations mirror it) but insufficient alone. |
| Generic Docker test environment (no repo-specific QA overlay) | Rejected | Cannot honor per-run isolation, synthetic provisional spine, or provider identity contracts without repo-owned config. |
| Provider-specific CI lanes | Rejected | Violates provider neutrality; public CI must be provider-agnostic. |
| Self-hosted/ephemeral runners as the *public* path | Rejected | Hidden host dependency; public CI must be GitHub-hosted/runner-agnostic. Ephemeral runners acceptable only as an owner-local optimization. |
| `multivac` as official staging | Rejected | Private server must never be the official path (owner decision DEC-1). |

### Risks

- **R1 (highest):** QA seeder may require provider calls for ingestion. Mitigation: stub-safe
  ingestion path (AC-C1) + documented stub chat provider; escalate to a blocker if impossible.
- **R2:** Compose overlay drift vs. base `docker-compose.yml` (two sources of truth). Mitigation:
  `docker compose config -q` in CI + a parity check asserting base services remain
  unmodified (only overridden values, never replaced definitions).
- **R3:** synthetic spine lane accidentally promoting artifacts. Mitigation: hard
  `is_qa_provisional` block + boundary test (AC-C4); promotion gate tests in L3.
- **R4:** `multivac` unknown surface (**UNVERIFIED**). Mitigation: adapter boundary +
  read-only-first inventory; nothing implemented against a guessed API.
- **R5:** `.gitignore`/`check_public_tree_clean.py` conflict for `qa/runs/`. Mitigation:
  implementation confirms prefix alignment before merging; scan gate as backstop.
- **R6:** feature-doc/manifest drift (the isolated `docs/features/site/manifest.json`
  modification). Mitigation: regenerate only when surfaces change; keep the modification in its
  own commit (Lane A ship discipline).

### Architecture debt

- Two Compose files (base + QA overlay) create a maintenance surface; a future single-file
  merge is out of scope and recorded as debt.
- Stub embedding lanes prove bounded boot only; full-feature readiness remains
  live-lane-only — a documented, deliberate limitation, not a gap to close silently.

### Rollback

- **Per-run:** `istara-qa.sh down --purge` removes the run's project/volumes; nothing touches
  production or the base stack.
- **Staging/multivac:** `istara-qa.sh staging --rollback` tears down only the new unique
  project; old-stack immutability is proven by inventory diff (AC-C6).
- **Feature-level:** every phase C1–C5 is additive (new files + overlay + tests); removal is
  deletion of `qa/`, the overlay, and the QA CI steps — no product behavior change to revert.

---

## 17. Files/surfaces that would likely change in implementation (lane C)

New (lane C-owned):

- `qa/runtime_capabilities.json` — runtime capability registry (§5)
- `qa/corpora/manifest.json`, `qa/corpora/<slice>/…` — synthetic QA corpus (§7)
- `qa/scripts/seed_synthetic.py` — provisional-only seeder (§7/§8)
- `qa/scripts/scan_qa_artifacts.py` — redaction/secret scan (§10)
- `qa/scripts/audit_qa.py` — provenance/retention audit (§8)
- `qa/scripts/check_qa_capabilities.py` — capability governance (§9)
- `docker-compose.qa.yml` (+ optional `docker-compose.qa.<host>.yml` overlays) (§8)
- `scripts/istara-qa.sh` — entrypoint (up/seed/reset/audit/down/staging) (§8)
- `backend/app/core/provider_contracts.py` — chat/embedding adapter contracts (§9)
- `tests/test_synthetic_provisional_boundary.py`, `tests/test_provider_contracts.py` (§7/§9)

Modified (touch only what the phases require; each isolated):

- `TESTING.md` — add QA artifact section + QA command rows (mandatory per gate rules)
- `security/control_matrix.json`, `security/SECURITY_BENCHMARK.md`,
  `tests/test_security_benchmark.py` — only if QA adds a control/trigger/evidence path (§10)
- `scripts/check_change_obligations.py` — register `qa/**` + `qa/runtime_capabilities.json`
  in governance patterns (§5)
- `scripts/check_ci_governance.py` — register new QA scripts if CI governance requires
- root `.gitignore` — add `qa/runs/` (confirm alignment with `check_public_tree_clean.py`)
- `docs/features/site/manifest.json` — only if feature-doc regeneration is triggered; keep
  isolated (constraint)

Unchanged by lane C: product runtime behavior, existing CI workflows (Lane B), branch
protection (Lane A), existing tests (except additive new ones).

---

## 18. Open decisions (owner-gated)

- **OD-1:** QA corpus licensing/provenance — approve the synthetic slice sources and the
  `generated|curated` labeling before seeding real public data.
- **OD-2:** SBOM tooling choice (syft vs. GitHub-native vs. none for QA images) — the
  security benchmark already names Attestations; SBOM depth is owner policy.
- **OD-3:** `multivac` adapter authorization — owner confirms the read-only-first boundary,
  the unique project naming, and whether any tunnel/HTTPS mode is ever acceptable.
- **OD-4:** retention policy for `qa/runs/` (default `--retain 5`?) and whether QA artifacts
  ever get published beyond CI (they should not, absent owner decision).
- **OD-5:** whether the `live-llm` QA profile may run in GitHub Actions post-merge with the
  one documented public-compatible target, or must always be owner-invoked locally.

---

## 19. Task breakdown (S1 buildable; owner approval required before execution)

- **T-C1** Scaffold `qa/` registry + synthetic corpus + provisional boundary tests.
- **T-C2** QA Compose overlay + `istara-qa.sh` lifecycle (up/seed/reset/audit/down/purge).
- **T-C3** Provider adapter contracts + no-fallback/identity/dimension tests + live-lane guard.
- **T-C4** Staging adapter boundary + `multivac` read-only-first inventory/dry-run/rollback.
- **T-C5** CI-wiring handoff + docs (`TESTING.md`, `qa/README.md`) + governance registration.

Entry gate for T-C1: owner approval of the converged MECE plan (Phase 2). Exit gates per §13.
Each task records command evidence, self-report, ledger entry, and hands off to the next
stage; no task merges or promotes anything.

---

## 20. Lane C handoff notes for synthesis

- **To Lane A:** consume §12 gate-bundle schema and the state-machine boundary states (§4) for
  the human-gate mechanics; keep `multivac` out of all public docs/workflows.
- **To Lane B:** consume §6 layer matrix (determinism classes), §13 phase gates, and
  `qa/runtime_capabilities.json` as the obligation registry the workflow graph consults;
  lane C supplies the scripts, Lane B wires them.
- **Overlap boundary honored:** this draft does not design the PR state machine, branch
  protection, or workflow caching (Lane A/B), and does not edit any existing workflow/compose
  file (planning-only).
- **Known uncertainties:** `multivac` surface (UNVERIFIED), current `.gitignore` contents
  (UNVERIFIED), live-lane test pass state (UNVERIFIED), existing SBOM tooling (UNVERIFIED) —
  each is labeled in the relevant section and is an owner-gated or implementation-phase
  verification, never an assumed fact.
