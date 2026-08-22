# Independent S1 Architecture Plan — Istara Pi Model-Management Migration

**Task:** `ISTARA-PI-MODEL-MIGRATION-20260822-PLAN-C`  
**Role:** `istara-pi-model-migration-20260822-architect-c`  
**Spec:** `CF-SPEC-1`  
**Planning phase:** `draft`  
**Status:** Independent plan; owner approval is required before implementation.

## 1. Decision and boundary

Make Pi the canonical authority for provider/model identity, endpoint identity,
capabilities, credential references, and model resolution. Preserve legacy
`LLMServer`, `ComputeRegistry`, local lifecycle, and Petals as explicit transport
adapters until migration evidence proves they can be retired. This is a
model-management migration, not a destructive rewrite of every inference
transport.

The target flow is:

```text
provider/model/endpoint configuration
        -> Pi canonical catalog + credential custody
        -> engine-specific transport adapter
           -> Pi worker | legacy registry | Petals bridge | audio adapter
        -> one safe route/usage/evidence record
```

The work remains on the testing branch. No live model loading, completion probe,
backend/frontend server, secret disclosure, firewall mutation, `main` change,
merge, push, or unrelated workload mutation is authorized by this plan.

This plan uses the three carried drafts as follows: A supplies the complete
identity/resolver and research-spine contracts; B supplies the explicit state
machine, secret migration/rollback sequencing, and test/QA decomposition; C
supplies the current-tree boundary, ratchet-oriented wave breakdown, and owner
gate model. The current manifest is authoritative where it differs from the
old drafts: final staging is managed VPS/Dokploy, not multivac.

## 2. Current-tree facts to freeze before implementation

Foundation must produce a machine-readable inventory before behavior changes.
The current tree has at least these coupled surfaces:

| Boundary | Current evidence | Migration obligation |
|---|---|---|
| Legacy persistence/API | `backend/app/models/llm_server.py`, `backend/app/api/routes/llm_servers.py`, `backend/app/core/llm_router.py`, `backend/app/core/ollama.py`, admin/settings routes, frontend `SettingsView.tsx`, `apiRequestTypes.ts`, `api.ts` | Enumerate every read/write/probe/route consumer. Keep rows and API compatibility while they are migration sources/adapters. |
| Pi authority | `backend/app/core/pi_runtime/model_manager.py`, `endpoints.py`, `engine.py`, `backend/app/config.py`, `pi-runtime/{package.json,package-lock.json,PROTOCOL.md}` | Verify package release and compatibility; make catalog and endpoint identity durable and exact. |
| Two engines | `backend/app/core/agentic/dispatcher.py`, `legacy.py`, project/settings `agentic_engine` contracts, Pi facade | Preserve per-call/header/project/global precedence. Selected-engine errors fail closed; no implicit Pi↔legacy fallback. |
| Embeddings | `backend/app/core/pi_runtime/embeddings_gateway.py`, `backend/app/core/embeddings.py`, validation wrappers | Persist an explicit embedding profile and enforce model/dimension/normalization invariants independently of chat selection. |
| Petals | `backend/app/core/petals_bridge.py`, `backend/app/api/routes/petals_bridge.py`, donor-isolation tests | Keep consent, health, project authorization, exact node pinning, route evidence, and typed 503 behavior. Never capacity-score donors as ordinary Pi endpoints. |
| Audio/research | `backend/app/core/transcription.py`, `file_processor.py`, `routes/files.py`, real `/chat/voice`, and duplicate Phase-Alpha `/chat/voice-transcribe` surfaces | Introduce capability-specific audio profiles without pretending text Pi endpoints transcribe audio; preserve source spans, confidence, review, and Research Spine gates. |
| UI/contracts | `SettingsView.tsx`, `ProjectSettingsView.tsx`, `Sidebar.tsx`, `modelProviders.ts`, `modelCatalog.ts`, chat/interview/audio components | Replace duplicate identity semantics with redacted canonical catalog views; preserve engine choice and accessibility. |
| QA/operations | `docker-compose.qa.yml`, `scripts/feature_docs.py`, `scripts/security_benchmark.py`, `vpsctl.py`, `qa/`, `testing/` | Deterministic disposable testing-branch QA, then isolated managed VPS acceptance using the vps skill and strict single-workload profile. |

The inventory must also run Compass Forge impact/why/test-impact for each planned
entry point and record inherited gate failures separately from new drift.

## 3. Contracts and non-negotiable invariants

### 3.1 Canonical identity

Implement an additive catalog contract (names may follow repository conventions)
with these distinct concepts:

```text
CanonicalModel: model_id, provider_family, canonical_name, provenance aliases
CanonicalEndpoint: endpoint_id, model_id, transport, kind, safe capabilities,
                   credential_ref, legacy_source_id, migration state
CredentialRef: opaque custody reference, kind, health/presence state
EmbeddingProfile: profile_id, model/endpoint identity, dimension, dtype,
                  normalization, version, status
```

`model_id` is provider-qualified; display names, hosts, and aliases cannot create
identity. Two endpoints serving one model retain separate `endpoint_id`s and route
evidence. `legacy_source_id` and `pi-llm-<id>` are provenance aliases only. Unknown
capabilities fail closed when required. Public docs, normal telemetry, QA output,
and errors contain neither URLs, host details, raw keys, prompts, responses, nor
reusable secret fingerprints.

### 3.2 Resolution and engines

Define one resolution request carrying project, selected engine, optional model or
endpoint, purpose, required capabilities, and optional embedding profile. Return a
safe resolved target containing canonical identities, transport, capabilities,
credential reference, and route-evidence fields. `PiModelManager` owns catalog
refresh and exact resolution; transport adapters do not create catalogs.

Preserve precedence: explicit call choice, request header, project setting, global
default, then target resolution. A selected Pi failure stays a Pi failure; a
selected legacy failure stays legacy. Every attempt, including resolution failure,
creates exactly one safe usage/route record.

### 3.3 Secret custody and migration

Read legacy encrypted API keys only inside a bounded migration service. Convert to
Pi Keychain/env/OAuth/encrypted-custody references without exporting plaintext.
Migration manifests hold source ID, nonsecret metadata, credential kind, presence
and validation status, and an opaque migration reference—not keys or reversible
hashes. Keychain/environment fallback must have explicit precedence and redacted
health checks.

### 3.4 Research validity and special transports

Model output remains candidate/provisional until evidence-unit extraction,
independent atomic coding, reliability/grounding, reconciliation, human review,
Done-task, and report gates pass. Audio transcript source spans and uncertainty
must remain traceable. Petals is an explicit identity-pinned, consented transport;
unavailable/disabled returns typed 503 and never silently falls back. Audio is an
explicit Whisper/diarization capability; text-chat capability is not audio
capability.

## 4. Reversible retirement state machine

Use durable migration records keyed by source row and canonical endpoint:

`discovered -> mapped -> credential_validated -> shadowed -> canary ->
pi_primary -> deprecated -> retired`

Each transition is idempotent, authorization-checked, and records actor, source
snapshot reference, canonical IDs, validation result, timestamp, and rollback
state. A mapping conflict, duplicate identity, secret mismatch, unsupported
capability, vector mismatch, or route-evidence gap blocks promotion rather than
guessing.

Rollback is explicit: disable the Pi-primary flag, restore the prior engine/route
mode and source snapshot, invalidate any temporary credential material, and prove
legacy behavior with contract tests. Never implement rollback as exception-based
cross-engine fallback. Do not delete source rows or credentials until all removal
criteria and owner gates pass.

Feature/deprecation controls must include global and project scope, read-only
legacy visibility, write prohibition after deprecation, migration status, and an
emergency rollback switch. Retirement requires: zero unmapped rows, zero active
legacy writes, successful Pi-primary canary and shadow comparisons, no duplicate
IDs, stable embedding profile, clean security benchmark, docs/manifest parity,
testing-branch QA, owner approval, and a restorable snapshot. Otherwise remain in
deprecated adapter mode.

## 5. Implementation waves and task breakdown

### W0 — Foundation and evidence freeze

Verify the latest registry versions of both Pi packages immediately before any
pin change; record registry output, lockfile resolution, worker/protocol v2,
structured-output, tool-loop, retry, limits, and cost compatibility. Inspect all
legacy consumers above, capture `gate before`, security scorecard, feature-doc
parity, test ownership, and a migration manifest with wave/task/verification
mapping. Do not change runtime behavior.

### W1 — Pi catalog, provider contracts, and secret custody

Add additive schema/service/API contracts for canonical models, endpoints,
capabilities, credential references, embedding profiles, migration status, and
redacted admin views. Migrate no rows yet; validate encryption and authorization
using a fresh disposable database and standalone Pi worker fixtures. Align both
`pi-runtime` and `labs/pi-replacement` dependency surfaces or document why the lab
surface is intentionally pinned separately.

### W2 — Compatibility migration and dual-engine routing

Create deterministic LLM Server mapping and snapshot tooling. Project legacy rows
to Pi canonical endpoints without duplicate options, route both explicit engines
through canonical resolution, preserve legacy transport shapes and project scope,
and add shadow/canary observability. Keep legacy CRUD read-compatible, then add
deprecation gates and explicit rollback. Strengthen the count-to-zero allowlist
without deleting permanent infrastructure exceptions.

### W3 — Embeddings, controls, and selector UX

Make the embedding profile explicit and immutable per vector space; reject model or
dimension mismatch and require reindex/migration for intentional changes. Propagate
only supported temperature, thinking, and effort controls through the selected
engine. Redesign Pi/Istara selection around honest, evidence-backed capability and
latency/cost summaries, not unverified comparative prose. Keep route identity and
research-validity status visible without leaking secrets.

### W4 — Petals and audio

Preserve donor consent, health, project authorization, exact node pinning,
same-model donor isolation, scheduling, and fail-closed unavailable behavior while
integrating canonical endpoint identity. Define audio profiles for local Whisper,
compatible remote Whisper, and explicitly supported diarization (including a
provider such as GPT-4 diarization only if its current contract is verified).
Unify interview upload and microphone paths behind capability-aware resolution;
retain ICR/confidence/needs-review metadata and source evidence. Leave mock/Phase-
Alpha endpoints explicitly labeled or remove only with a documented contract
change.

### W5 — Testing branch QA, docs, and managed VPS acceptance

Update `docs/architecture`, relevant `docs/features`, generated site/manifests, UI
contracts, migration runbook, and rollback docs. Run deterministic Compose QA with
unique project/network/volume names and provider stubs; the public lane must not
depend on private hosts. For owner-authorized VPS acceptance, follow the vps skill:
`vpsctl.py preflight` and `inventory` read-only first; render Compose; use Dokploy
strict single-workload profile (one service, project-local internal network, no
proxy/external network, Docker socket, privileged mode, or host namespace); deploy
only the testing-branch workload; run `verify-isolation`, `verify-exposure`, and
`audit-anchor`; collect firewall/DOCKER-USER evidence without changing firewall
policy absent owner approval. Remove only initiative-owned disposable artifacts and
prove unrelated workloads and deployment identity are unchanged.

## 6. Acceptance and exact verification

### Work-order decomposition

Create implementation tasks with dependencies in this order; do not make later
tasks ready before their predecessor's evidence and owner gate exist:

| Task slice | Owns | Exit evidence |
|---|---|---|
| A. Foundation/dependency | inventory, graph impact, Pi version/protocol compatibility, baseline | manifest, passive registry output, gate baseline, no behavior change |
| B. Catalog/custody | canonical model/endpoint/credential/embedding contracts and migrations | fresh-DB migration, deterministic identity and secret non-disclosure tests |
| C. Engines/retirement | legacy mapping, snapshots, resolver integration, flags, shadow/canary and rollback | both-engine matrix, one-row ledger accounting, restore drill |
| D. Embeddings/UI | vector profile, capability controls, selectors and feature contracts | invariant/model-control/UI contract tests and generated docs |
| E. Petals/audio | donor isolation and capability-specific transcription/diarization | donor security, typed-unavailable, source-span/needs-review tests |
| F. QA/operations | Compose QA, docs/manifests, managed VPS acceptance and cleanup | rendered Compose, vpsctl isolation/exposure/audit evidence, post-cleanup inventory |

The owner approval gate follows A and the frozen consensus plan; it is also
required before any live or managed-VPS lane. No task may claim production
readiness from package tests, synthetic QA, or a passive endpoint check alone.

Each wave must attach command evidence and pass its focused tests before promotion.
The minimum matrix is:

```bash
# passive dependency/provenance and tree checks
npm view @earendil-works/pi-agent-core version
npm view @earendil-works/pi-ai version
cd pi-runtime && npm ci
cd ../labs/pi-replacement && npm ci
cd ../..

# focused contracts and migration safety
python -m pytest tests/pi_migration/test_count_to_zero.py -q
python -m pytest tests/pi_production/test_w1_agentic_contract.py tests/pi_production/test_w1_dispatcher_authority.py -q
python -m pytest tests/pi_production/test_endpoint_secrets.py tests/pi_production/test_same_model_donor_isolation.py -q
python -m pytest tests/pi_production/test_w8_embeddings_gateway.py tests/test_research_validity_contract.py -q
python -m pytest tests/petals_bridge -q
python -m pytest tests/llm_servers.py tests/test_llm_servers.py -q  # use only paths that exist

# frontend/runtime and repository gates
cd pi-runtime && npm test
cd ../frontend && npm test -- --runInBand
cd ..
python scripts/security_benchmark.py --fail-on-threshold
python scripts/feature_docs.py --seed-missing --generate-site --check
compass-forge gate before --task <wave-task> --summary
compass-forge gate after --task <wave-task> --summary
```

Commands must be adapted to the actual available test paths; a nonexistent path
is not a pass. Add migration-specific tests for idempotence, deterministic
mapping, duplicate identity rejection, secret non-disclosure, snapshot restore,
engine no-fallback, capability admission, and one-row usage accounting. Run
`tests/pi_benchmark` only for the explicitly authorized bounded benchmark lane;
never treat live-probe absence or synthetic QA as production readiness.

Acceptance is satisfied only when the relevant contract tests, security benchmark,
feature-doc generation/check, Compose QA, gate comparison, and (at final wave)
VPS isolation/exposure/audit evidence are attached. Inherited gate debt is reported
separately and never relabeled as a migration regression.

## 7. Documentation, security, risks, and rollback

Update the research-validity and self-improvement governance architecture docs,
feature docs for settings/models, engine selection, embeddings, Petals, audio, and
QA/deployment. Regenerate manifests/site with the required script and include the
migration state machine, identity rules, secret handling, deprecation/removal
criteria, rollback commands, and VPS cleanup boundaries. Update security control
matrix/benchmark documentation and tests whenever a security control or evidence
path changes.

Primary risks are hidden dynamic LLM Server consumers, duplicate model aliases,
credential loss, implicit fallback, vector-space drift, donor identity confusion,
audio capability overclaim, stale generated docs, Compose leakage, and VPS
cross-workload mutation. Mitigate with graph-guided inventory plus textual sweep,
explicit IDs, source snapshots, fail-closed resolver contracts, embedding profile
checks, donor isolation tests, capability probes, generated-doc checks, rendered
Compose review, and vpsctl isolation/audit evidence.

Implementation is ready only after the consensus plan is frozen, CF tasks have
dependencies and owners, the dependency contract is verified, the baseline gate
and inherited debt are recorded, and the owner approves release of W0. The
initiative is done only after all waves, rollback proof, docs, security, QA, and
managed-VPS acceptance are complete on testing and the owner accepts the ship
gate. Until then, legacy data and adapters remain recoverable.

## 8. Coverage matrix

| Required concern | Plan coverage |
|---|---|
| Legacy storage/routing/encryption | §§2, 3.3, 4, W0–W2 |
| Both agentic engines | §3.2, W2, W3 |
| Pi catalog/resolver/dependency | §§1, 3.1–3.2, W0–W1 |
| Embedding invariant | §3.4, W3 |
| Petals donor bridge | §3.4, W4 |
| Audio/transcription | §2, W4 |
| UI contracts | §2, W3, W5 |
| Testing-branch Docker QA | W5, §6 |
| Managed VPS/Dokploy/vpsctl | W5 |
| Migration/rollback/deprecation | §4, W2, §7 |
| Security/docs/manifest | W0, W5, §7 |

**Handoff:** This draft is ready for architect synthesis. No implementation or
lifecycle-file mutation is included.
