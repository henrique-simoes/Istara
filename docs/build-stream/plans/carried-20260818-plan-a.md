# Independent S1 Draft — Pi Model-Management Migration Boundary

**Task:** `ISTARA-PI-MODEL-MIGRATION-20260818-PLAN-A`
**Role:** `istara-pi-model-migration-20260818-architect-a`
**Spec:** `CF-SPEC-59`
**Status:** Draft for architect consensus; not owner-approved; implementation is prohibited until the consensus plan is frozen and the owner approval gate is recorded.

## 1. Executive recommendation

Make Pi the single **model-management and endpoint-identity authority**, while retaining the existing legacy transport and donated-compute infrastructure as explicit transport adapters. Do not equate “Pi owns model management” with “delete every legacy LLM Server, Ollama, LM Studio, or ComputeRegistry module.” The safe boundary is:

```text
configuration + credentials + model identity + endpoint identity
        -> canonical Pi model catalog / resolver
        -> explicit engine transport
           ├─ PiExecutionService -> pi-runtime worker -> pi-ai
           ├─ legacy adapter    -> legacy executor -> ComputeRegistry/local transports
           └─ Petals adapter    -> consented donor loopback bridge
        -> one route/usage/evidence record
```

The legacy `LLMServer` table and CRUD routes become a reversible compatibility adapter and migration source. They are not a second canonical catalog after cutover. The legacy engine remains selectable and behavior-compatible, but receives a canonical endpoint selection and route identity instead of independently owning provider/model configuration. Petals donors remain a separately governed donated-compute class; they must never become ordinary Pi capacity or be selected through donor-style scoring.

The migration must be additive and idempotent first: inventory, map, validate, dual-read/shadow, canary, Pi-primary, deprecate, and only then retire. No row, credential, legacy route, or old Compose workload is deleted merely because a new Pi record exists.

## 2. Grounded current-state inventory

The following facts were inspected in the current Istara worktree. They are starting facts for implementation, not permission to alter any of these surfaces in this planning stage.

### 2.1 Pi runtime and dependency boundary

- `pi-runtime/package.json` currently pins `@earendil-works/pi-agent-core` and `@earendil-works/pi-ai` to `0.83.0`; its lockfile records the same exact versions. It exposes `npm test` and starts `src/worker.mjs`.
- `labs/pi-replacement/package.json` and its lockfile currently pin both packages to `0.80.10`; this is a lab comparison surface and must not silently diverge from the production runtime after the upgrade.
- The framing ledger records `npm view` reporting `0.84.2` for both packages. Implementation must re-run the passive registry query immediately before changing dependencies and record the exact version, registry output, lockfile resolution, and compatibility result. A registry version alone is not proof of compatibility.
- `pi-runtime/PROTOCOL.md` defines NDJSON protocol v2, bounded framing/chunking, session limits, provider binding, structured-output forced-tool semantics, tool authority round-trips, per-run cost ceilings, retry discipline, and fail-closed terminal outcomes. The dependency update must preserve this protocol or explicitly version and test a deliberate protocol change.
- `backend/app/core/pi_runtime/engine.py` is the Python facade. It resolves an endpoint through `PiModelManager`, binds secrets only on the private pipe, injects authenticated project/agent scope into tool execution, and records route telemetry. It must remain independent of `ComputeRegistry`.

### 2.2 Existing model and secret planes

- `backend/app/config.py` defines `PiApiEndpoint` settings entries, Keychain/env secret resolution, provider family, model, timeout/retry, cost, and capability metadata. `PI_API_ENDPOINTS` is currently JSON settings state, not a durable canonical catalog.
- `backend/app/core/pi_runtime/endpoints.py` resolves exact endpoint IDs and verifies the endpoint model. It reads Keychain/env secrets through a short TTL cache and refuses missing credentials.
- `backend/app/core/pi_runtime/model_manager.py` currently builds an in-memory catalog from static settings endpoints, local Ollama/LM Studio `/v1` entries, read-only projections of `LLMServer` rows (`pi-llm-<id>`), and optional Petals entries. Selection is exact/capability-filtered, not capacity-scored.
- `backend/app/models/llm_server.py` stores `name`, `provider_type`, `host`, encrypted `api_key`, local/relay flags, health, priority, and JSON capability metadata in `llm_servers`. `backend/app/api/routes/llm_servers.py` still registers and probes rows through `llm_router`/the live registry and refreshes Pi projections after CRUD.
- `backend/app/core/field_encryption.py` is the existing encrypted-field custody boundary. The migration must not export or log decrypted API keys. Keychain references and encrypted database credentials need an explicit canonical credential-reference contract.
- Provider identity must not be inferred from a display name, hostname, or model label. An endpoint can serve the same model as another endpoint and still be a distinct route identity.

### 2.3 Agentic engines and routing

- `backend/app/core/agentic/dispatcher.py` is the shared invocation choke point for `chat_turn`, `completion`, `structured`, `ensemble`, `embed`, and the `react` seam. Engine precedence is per-call override, request header, project setting, then global default.
- `backend/app/core/agentic/legacy.py` is a permanent, byte-compatible legacy executor over the existing Ollama/ComputeRegistry plane. It explicitly does not fall back to Pi. Pi also must not fall back to legacy after a Pi resolution or runtime error.
- The current global default remains `legacy`; the project `agentic_engine` column is an explicit per-project choice. The migration must preserve `pi`, `legacy`/UI `istara`, and existing unknown/empty-value normalization behavior.
- `tests/pi_migration/legacy_allowlist.yaml` and `tests/pi_migration/test_count_to_zero.py` already enforce zero direct product call sites while naming permanent infrastructure exceptions. Retirement must not weaken this ratchet or incorrectly remove permanent local-model/donor transport entries.
- The agentic usage ledger is the accounting boundary. Every dispatch, including resolution failure and error, must produce one row with safe endpoint/node identity and no prompt, response, URL, or secret.

### 2.4 Embeddings and Research Spine

- `backend/app/core/pi_runtime/embeddings_gateway.py` routes Pi embeddings by Pi identity and contains `assert_vector_space_invariant`; `backend/app/core/embeddings.py` and validation wrappers retain the legacy path behind the dispatcher.
- The current default embedding model follows active local-provider settings. A migration must make the embedding profile explicit and stable so changing a chat endpoint or engine cannot silently change vector space.
- `docs/architecture/research-validity-contract.md` requires raw source evidence units, independent coding, reliability, reconciliation, human review, route evidence, approved Done-task state, and report gates. Model-management changes touching interviews, coding, RAG, validation, reports, or QA must preserve that chain.

### 2.5 Petals/donated compute

- `backend/app/core/petals_bridge.py` and `backend/app/api/routes/petals_bridge.py` implement the sanctioned boundary: only healthy relay/browser nodes with explicit `pi_served` consent are projected, each request is pinned to one node, route evidence is stamped, and unavailable/disabled conditions return typed 503 without paid-provider fallback.
- The bridge intentionally lives outside `pi_runtime`; `tests/pi_production/test_same_model_donor_isolation.py` guards the bidirectional isolation invariant. The catalog may expose a `kind="petals"` entry for an explicit request, but Petals must not be merged into ordinary provider capacity or local endpoint selection.

### 2.6 Audio/transcription

- `backend/app/core/transcription.py` currently loads local `openai-whisper`, defaults to `base`, performs a `tiny` alternative pass where available, calculates ICR, and returns `needs_review` on low/insufficient agreement. It does not currently provide a canonical endpoint/credential/profile abstraction or diarization provider selection.
- `backend/app/core/file_processor.py` uses that local path for uploaded audio; `backend/app/api/routes/chat.py` has the real microphone upload path; `chat_voice.py` and the second `/chat/voice-transcribe` contract are phase-alpha/error or dummy surfaces. `files.py` persists transcript metadata and raw-source evidence units.
- A unified audio profile must be additive, capability-checked, and explicit about local Whisper versus compatible remote Whisper/diarization. A text-only Pi chat endpoint is never an implicit audio fallback.

### 2.7 UI, QA, and operations

- `frontend/src/components/common/SettingsView.tsx`, `frontend/src/lib/modelProviders.ts`, and the settings routes expose a legacy LLM server inventory and a Pi endpoint list. `frontend/src/components/settings/ProjectSettingsView.tsx` and `Sidebar.tsx` expose the per-project engine choice.
- `docker-compose.qa.yml` is the provider-agnostic disposable QA authority. Its default/contract profiles use a deterministic in-network provider stub, unique `istara-qa-<run-id>` project names, internal networks, read-only/hardened containers, no model service by default, and an owner-authorized one-target live lane.
- The optional owner-local multivac staging adapter is documented as read-only-first, unique-project, SSH-tunneled/loopback-safe, and cleanup-scoped. The public CI/QA path must never depend on multivac or disclose its private details.

## 3. Goals, non-goals, and invariants

### Goals

1. Update both bundled Pi package surfaces to the latest **verified compatible** upstream release available at implementation time, with reproducible lockfiles and protocol tests.
2. Establish one canonical Pi-owned catalog for provider families, model IDs, endpoint IDs, capabilities, local/cloud/custom/OAuth/API-key configuration, and credential references.
3. Preserve both explicit engines and their semantics while making endpoint/model resolution canonical and fail-closed.
4. Migrate all mappable LLM Server configuration without data or secret loss, with idempotent state, evidence, rollback, and a bounded deprecated adapter.
5. Preserve the shared embedding model/dimension invariant and make embedding identity visible in safe metadata.
6. Preserve Petals consent, project authorization, donor identity pinning, route evidence, and no-fallback behavior.
7. Add governed audio/Whisper/diarization model configuration without bypassing the Research Spine or inventing unsupported Pi audio behavior.
8. Update UI, living feature documentation, manifests, test ownership, testing-branch Compose obligations, security evidence, and optional isolated staging acceptance.

### Non-goals

- Do not merge, push, open a PR, change `main`, or cut over the separate Compass Forge/Skills branches.
- Do not delete `LLMs/` or `Model_Finetuning/`, remove unrelated benchmark artifacts, or clean external repositories.
- Do not delete the legacy transport, ComputeRegistry, donor relay/browser transport, local model provisioning, or permanent legacy executor merely because Pi becomes the model-management authority.
- Do not load a model, start a live backend/frontend stack, call a live completion provider, use a private endpoint, or access/mutate multivac without the explicit owner authorization required by the frame.
- Do not treat synthetic QA, raw tool success, transcript keyword tags, or comparative model prose as accepted research evidence.
- Do not silently merge endpoint identities that happen to share a model name or host.

### Invariants that must remain true

| Invariant | Required contract | Primary proof |
|---|---|---|
| Pi/runtime isolation | `pi_runtime` never imports or mutates `ComputeRegistry`; Pi resolution never donor-scores | `tests/pi_production/test_same_model_donor_isolation.py` |
| Explicit engine choice | Per-call/header/project/global precedence is stable; selected engine errors, never silently falls back | `tests/pi_production/test_w1_agentic_contract.py`, `test_w1_dispatcher_authority.py` |
| One identity plane | A canonical `model_id` is distinct from stable `endpoint_id`; legacy IDs are provenance aliases only | New migration/catalog contract tests |
| Secret safety | Plaintext credentials exist only in short-lived in-memory binding; no logs, responses, docs, QA artifacts, or telemetry | `tests/pi_production/test_endpoint_secrets.py`, security benchmark |
| Vector-space safety | Chat-engine/provider changes cannot silently alter the embedding profile; model/dimension mismatch blocks | `tests/pi_production/test_w8_embeddings_gateway.py` |
| Donor security | Consent + health + project authorization + exact node pin are all required; unavailable means 503 | Petals and donor-isolation tests |
| Research validity | Source spans become evidence units; candidate/provisional outputs cannot bypass coding/reliability/reconciliation/review/Done/report gates | `tests/test_research_validity_contract.py`, synthetic boundary tests |
| Migration reversibility | Every source row has a mapping/status and a restorable source snapshot before write/cutover | New migration state/rollback tests |
| QA isolation | Unique disposable project/paths; no fixed names or public private-target configuration | QA stack and cleanup contract tests |

## 4. Target architecture

### 4.1 Canonical identity model

Introduce an additive canonical model-management schema and API. Names may be adjusted during implementation to match repository conventions, but the following semantic split is load-bearing:

```text
CanonicalModel
  model_id: stable provider-qualified identity
  provider_family: openai_compat | anthropic_compat | local_ollama |
                   local_lmstudio | whisper | diarization | ...
  canonical_name: provider/model identity, not a display label
  aliases: observed provider aliases with provenance

CanonicalEndpoint
  endpoint_id: stable route identity
  model_id: referenced CanonicalModel
  transport: pi_http | legacy_registry | local_lifecycle |
             petals_bridge | audio_adapter
  endpoint_kind: cloud | custom | local | petals | audio
  nonsecret connection metadata/capabilities
  credential_ref: opaque reference to Pi credential custody
  legacy_source_id: nullable LLMServer id for migration provenance only
  migration_state and timestamps

CredentialRef
  credential_ref: opaque stable name
  kind: keychain | encrypted_db | environment | oauth
  secret material: encrypted/externally held only
  status: present | missing | invalid | rotation_required

EmbeddingProfile
  profile_id: stable profile identity
  model_id/endpoint_id or provider-neutral embedding identity
  dimension, dtype, normalization, version, health status
```

Rules:

- `model_id` is provider-qualified and normalized, not a UI display string. If two providers expose the same visible model name, they remain different canonical model identities unless an explicit provider alias mapping proves equivalence.
- `endpoint_id` is always distinct from `model_id`. Two endpoints serving one model create one model record and multiple endpoint records; route evidence always retains the endpoint identity.
- `legacy_source_id` and `pi-llm-<id>` transition identifiers are aliases/provenance, never independent model identities. Once a row is migrated, the resolver must not emit both a legacy and Pi canonical option for the same endpoint.
- Capability metadata is attached to the endpoint/model profile and is never inferred from a name alone. Unknown capability fails closed when a caller requires it.
- `base_url`, host labels, credential refs, and route IDs are never included in public feature docs, QA artifacts, or normal telemetry. Admin views return redacted/safe metadata and `has_credential` only.

### 4.2 Resolver and transport boundary

Create one canonical resolution request, conceptually:

```text
resolve_model_request(
  project_id,
  engine,
  model_id?,
  endpoint_id?,
  purpose,
  capabilities?,
  embedding_profile_id?
) -> ResolvedModelTarget
```

`ResolvedModelTarget` contains the canonical model ID, endpoint ID, transport class, safe capabilities, credential reference, and route-evidence fields. It does not expose plaintext credentials to callers.

- `PiModelManager` becomes the authoritative catalog/resolver and owns refresh, exact identity, capability admission, and migration projection.
- `PiExecutionService` consumes a resolved Pi target and binds its secret only to the worker. It must reject a target whose transport is not Pi-compatible.
- The legacy executor remains a transport adapter. It consumes a canonical target with `transport=legacy_registry`/`local_lifecycle`, preserving legacy request shapes and ComputeRegistry project authorization. It must not independently manufacture a second model catalog.
- Petals uses an explicit `transport=petals_bridge` target. Its resolver calls the bridge admission path and preserves exact donor identity; it is not a capacity candidate.
- Audio adapters use `transport=audio_adapter` and an explicit capability contract. They do not route binary audio through the text Pi worker unless a separately verified provider API supports it.
- All dispatcher verbs continue through `AgenticDispatcher` and record exactly one usage/route row. Resolution failure records a typed failure rather than trying another engine.

### 4.3 Provider and secret custody

Supported configuration classes are explicit:

- Cloud/OpenAI-compatible and Anthropic-compatible: provider family, endpoint URL, model ID, capabilities, pricing, retry/timeout, and `credential_ref`.
- OAuth: provider/account identity and refresh/access material held by Keychain or encrypted credential custody; access tokens are short-lived in memory and never returned.
- API key: Keychain/env fallback or encrypted DB custody, with a redacted presence/health status.
- Custom/local: normalized loopback or approved HTTPS endpoint with capability probe metadata; local Ollama/LM Studio lifecycle remains separate from cloud credentials.
- Audio/Whisper/diarization: provider family and capability-specific endpoint/credential reference, with no automatic promotion to chat provider.

The canonical resolver may read legacy encrypted `LLMServer.api_key` during migration, but only inside a migration service that immediately re-encrypts or externalizes it. The migration manifest stores credential reference, source kind, presence/status, and a nonsecret metadata checksum; never plaintext, a raw token, or an easily reusable secret fingerprint.

### 4.4 Engine selection and rollback

Preserve the existing selection precedence. Add the canonical target resolution after engine selection, not a hidden second engine choice:

1. explicit per-call engine/target;
2. request header engine selection;
3. project engine setting;
4. global default;
5. canonical model/endpoint resolution for that selected engine.

A selected `pi` target with missing credentials, unsupported capability, worker failure, or provider error is a failed Pi invocation. It must not fall through to legacy. A selected `legacy` target preserves the legacy transport and route evidence. Rollback changes the feature mode/project choice to `legacy` and restores the source checkout/data snapshot; it does not rely on an implicit exception fallback.

### 4.5 Embeddings

- Make one embedding profile authoritative for both engines. Persist model identity, endpoint/transport identity, dimension, dtype, normalization, and profile version.
- Engine-specific adapters may use different transports, but they must return vectors in the same declared profile. A dimension, dtype, model, normalization, or profile-version mismatch blocks startup/engine switching and prevents cache writes.
- Existing vectors remain tied to their recorded profile. A deliberate profile migration requires a new profile version, a bounded re-embed job, dual-read/reindex evidence, and explicit invalidation—not a silent settings change.
- Chat endpoint changes never mutate the embedding profile. UI separates chat model controls from embedding profile controls and shows the active profile identity safely.
- The Pi gateway retains one dispatcher-owned usage row; it must not double-account.

### 4.6 Petals

- Keep `petals_bridge.py` outside `pi_runtime`; project only `source in {relay,browser}`, `pi_served=true`, healthy, project-authorized donors.
- Require explicit `endpoint_id=pi-petals-<node>` or governed Petals purpose. Never select a donor by model-name collision, latency, or capacity when a Pi endpoint is requested.
- On unknown/unconsented/unhealthy/unauthorized donor, return typed 503 and route evidence. There is no paid API fallback.
- Preserve donor lifecycle and selected/served/failed counters and ensure donor route identity is visible to audit without prompts, URLs, or secrets.

### 4.7 Audio and diarization

Add a canonical `AudioModelProfile`/adapter contract, with fields such as profile ID, provider family, model ID, endpoint ID, credential ref, local/remote mode, language policy, diarization support, speaker-count policy, timestamps, confidence policy, and human-review threshold.

- `local_whisper` keeps the existing local model loader and ffmpeg boundary; model size becomes configuration validated against available local capability.
- `remote_whisper` and `remote_diarization` are opt-in endpoint adapters. They require capability metadata, explicit credential custody, bounded file size/timeouts, redacted errors, and deterministic mocked contract tests. A provider without diarization cannot be advertised as diarized.
- Interview uploads, microphone chat, and channel audio resolve the same profile contract, but preserve project authorization and source provenance.
- Transcriptions remain candidate/provisional source material until raw audio spans/segments, coding, reliability, reconciliation, and human review gates accept them. ICR failure remains `needs_review`; no keyword tag promotes a finding.
- If no configured audio profile can serve, return a typed unavailable state. Do not silently use a text chat model or an unrelated provider.

## 5. Exact migration and rollback procedure

### 5.1 Preflight and immutable evidence

Before any write or feature-flag cutover, the implementer must:

1. Capture the exact branch/base commit, current schema revision, package versions/lockfile hashes, and `gate before` output.
2. Export a redacted inventory of all static Pi settings, `LLMServer` rows, legacy aliases, discovered rows, relay/browser rows, local provider settings, project engine selections, and embedding metadata. Include source IDs and mapping reasons, never secret values or private endpoints.
3. Create an encrypted database backup/snapshot and preserve the pre-change checkout/Compose definition. The backup path is disposable/gitignored and has an owner-approved retention/restore proof.
4. Resolve only credential presence/status in a controlled dry-run. Do not call live completions or load models. A Keychain/env secret may be checked for availability but never printed.
5. Record a deterministic `migration_id`, schema version, source metadata checksum, and migration-tool version. A repeated run with the same source checksum must be a no-op.

### 5.2 Deterministic mapping

For each non-relay `LLMServer` row:

1. Normalize provider family and endpoint URL using the existing endpoint-security rules.
2. Parse capability JSON without inventing model names. Each advertised model becomes an alias attachment; an absent model remains an explicit `unknown/default` state requiring validation.
3. Resolve or create the provider-qualified canonical model ID.
4. Resolve or create exactly one canonical endpoint ID tied to the stable source row. Preserve `legacy_source_id`, source provider, original priority, health history summary, and capability provenance.
5. Create a credential reference. For an encrypted API key, decrypt only in memory and re-encrypt through canonical custody or bind the source encrypted field under a compatibility reference. For Ollama/local no-key profiles, use a nonsecret local credential mode. For Keychain settings, preserve service/account references without copying the value.
6. Mark the row `mapped`, `credential_validated`, `blocked`, or `legacy_only` with an actionable reason. Unsupported provider types and malformed capability payloads are preserved and visible; they are not silently dropped.
7. Compare canonical nonsecret metadata against source metadata and store a redacted mapping result. Do not compare or log raw secret values.

Relay/browser rows are not migrated into ordinary Pi endpoints. Their identity remains in the donor/ComputeRegistry plane and they are handled only by the Petals bridge contract.

### 5.3 Staged cutover state machine

The migration state belongs in an additive migration/status table or equivalent canonical metadata, not in an overloaded display field:

```text
unmapped
  -> mapped
  -> credential_validated
  -> shadow_verified
  -> pi_primary
  -> legacy_deprecated
  -> retired

any state -> blocked (reason + evidence handle)
pi_primary/legacy_deprecated -> rollback_ready -> legacy_compat
```

- **Mapped:** canonical target exists; source row untouched; no runtime cutover.
- **Credential validated:** secret reference resolves in memory and the endpoint's capability metadata is valid; no completion call is required for deterministic QA.
- **Shadow verified:** read-only resolution and metadata parity are proven for a canary project/contract stub. Shadow mode must not double-send user research content to a provider.
- **Pi primary:** Pi is the selected target for opted-in project/route, while legacy source data remains readable through the adapter.
- **Legacy deprecated:** admin writes use canonical Pi management; legacy endpoints return deprecation metadata and read-only compatibility projections where required. Existing project selections continue to resolve through the canonical mapping.
- **Retired:** only after all removal criteria in §6 pass, an owner gate accepts the evidence, and retention/restore requirements are satisfied. Retirement first disables runtime use; physical row deletion is a separate, later owner-approved action.

### 5.4 Rollback

Rollback is an explicit operation, not an exception handler:

1. Stop the staged QA/temporary Compose project before changing data.
2. Set the migration mode/project selection back to `legacy` or `legacy_compat`; do not change unrelated projects.
3. Restore the pre-cutover canonical mapping/status snapshot if the mapping itself is corrupt. Keep the failed migration report.
4. Restore the encrypted database/config snapshot only when an additive rollback cannot recover the source; verify schema downgrade/restore compatibility first.
5. Restore the previous checkout/Compose image and rerun legacy routing, embedding dimension, donor isolation, and source-evidence contract tests.
6. Prove no source LLM Server row, project engine setting, vector, donor consent, or audit row was lost. Record rollback command/evidence and retain the migration artifact for review.

No migration step may require deleting a source row to validate success. If a row cannot be mapped safely, leave it in `legacy_only`/`blocked` state and keep the adapter enabled.

## 6. Feature flags, deprecation, and removal criteria

Use one global rollout mode plus project/endpoint overrides; avoid many independent booleans that can produce an untestable combination. Proposed values:

```text
PI_MODEL_MANAGEMENT_MODE=legacy_compat   # default on existing installs
  legacy_compat | shadow | pi_primary | deprecated_adapter | retired
```

A per-project explicit engine still overrides the global engine policy according to the existing precedence contract. The mode must be visible in safe admin diagnostics and included in route/migration evidence.

### Promotion criteria

- `shadow` requires deterministic catalog/mapping parity, credential-status parity, no duplicate canonical identity, no secret-flow violation, and no new gate drift.
- `pi_primary` requires a successful canary on contract/faux providers, both engine suites, embedding invariant proof, Petals isolation proof, audio unavailable/capability proofs, and a rollback artifact.
- `deprecated_adapter` requires all new writes to use canonical Pi management, compatibility GET/read paths to preserve existing clients, deprecation headers/diagnostics, and a report of unmigrated/blocked rows.
- `retired` requires: zero active runtime reads that treat LLM Server as canonical; zero unmapped rows unless explicitly owner-accepted exceptions; all supported credentials resolvable or explicitly blocked; no data-loss or secret-loss report; three consecutive deterministic full-suite runs with no new migration failures; one isolated testing-branch Compose run; one owner-authorized staging proof when marked required; security benchmark green; docs/manifests green; and a tested rollback command. Physical deletion is not part of the first retired state.

### Deprecation behavior

- Add a stable deprecation response/header and safe diagnostic reason to legacy CRUD/runtime compatibility paths.
- Preserve read compatibility for the retention window. Writes either invoke the canonical Pi management service or fail closed with a migration-required response; they must not create an untracked second source of truth.
- Do not deprecate local lifecycle and donor APIs that are still required transport infrastructure. Deprecate only the model-management ownership semantics and document the distinction.

## 7. Wave plan and task graph

The immutable manifest defines six execution waves. The CF implementation tasks map as follows; the conductor must keep dependencies and the owner approval gate intact.

| Wave | CF work items | Scope and dependency |
|---|---|---|
| `foundation` | planning task; `CF-787` dependency/runtime verification | Freeze current contracts, latest package provenance, baseline gates, migration schema/rollback design, and inventory. No implementation before owner approval. |
| `pi-catalog-secrets` | `CF-788` | Add canonical catalog/credentials/capabilities and provider adapters. Depends on the approved foundation and `CF-787`; no LLM Server deletion. |
| `compat-routing` | `CF-789`, `CF-790` | Route both engines through canonical target resolution; implement idempotent mapping/state machine, compatibility API, feature flags, and rollback. Depends on `CF-788`. |
| `embeddings-controls` | `CF-791`, `CF-794` | Persist/enforce embedding profile and update chat/engine/effort controls and selector UX. Depends on canonical resolver and routing contracts. |
| `petals-audio` | `CF-792`, `CF-793` | Preserve donor bridge and add governed audio profile/adapters. Depends on resolver/credential/route evidence contracts. |
| `qa-docs-multivac` | `CF-795`, `CF-796` | Wire feature obligations, Compose contract QA, docs/manifests, security evidence, and owner-local staging acceptance. Depends on all prior waves. |

The linked validator tasks `CF-797`–`CF-805` remain validation/acceptance obligations and must not be used to bypass implementation evidence. Work orders should add focused tests rather than editing unrelated paths. Each meaningful task gets `gate before`, a focused `gate after`, command evidence, and a self-report.

### Implementation dependency graph

```text
CF-787
  -> CF-788 canonical catalog/secrets
      -> CF-789 dual-engine resolver
      -> CF-790 migration/compatibility
          -> CF-791 embeddings profile
          -> CF-794 selector/UI
      -> CF-792 Petals
      -> CF-793 audio
          -> CF-795 docs/QA
              -> CF-796 optional staging
```

`CF-791` may begin after the canonical identity schema is stable, but its final acceptance is blocked until `CF-789` proves both engine adapters. `CF-796` is owner-authorized and never a prerequisite for public deterministic CI when the host is unavailable.

## 8. Per-wave acceptance and exact verification

All commands below are intended as implementation-stage commands. They must be run from the repository root, with live/provider/model actions omitted unless separately authorized. New test paths named below are obligations to create in the corresponding work item, not claims that they already exist.

### Wave 0 — foundation and inventory

**Acceptance:**

- Given the current `0.83.0`/`0.80.10` manifests and the framing observation of `0.84.2`, when the implementer rechecks the registry and lockfiles, then the target version and provenance are explicit, exact, and compatible with the worker protocol.
- Given all provider/config/LLM Server/donor/project/embedding consumers, when the inventory is generated, then every source row has a mapping/status and no relay/browser donor is classified as an ordinary Pi endpoint.
- Given the existing gate failures, when baseline and impact are recorded, then inherited failures are distinguished from new migration drift.

**Commands:**

```bash
npm view @earendil-works/pi-agent-core version --json
npm view @earendil-works/pi-ai version --json
python scripts/pi_migration_inventory.py --json
uv run --project backend python -m pytest tests/pi_migration/test_count_to_zero.py tests/test_model_provider_contract.py tests/test_pi_runtime_endpoints.py -q
compass-forge --workspace /Users/user/Documents/compass-forge gate before --task CF-787 --summary
```

No live provider call, model load, Docker startup, or remote host access is part of this wave.

### Wave 1 — Pi catalog, providers, and secrets

**Acceptance:**

- Given two endpoints serve the same model label, when catalog entries are listed, then the model identity is canonicalized once while each endpoint remains distinct and routeable.
- Given a legacy encrypted key, Keychain reference, OAuth reference, env fallback, missing key, or invalid credential, when canonical resolution is exercised, then only the safe status is exposed and failure is typed/closed; no key appears in logs, responses, telemetry, or artifacts.
- Given the latest verified package version, when `pi-runtime` and the comparison lab install/test, then lockfiles are reproducible and protocol v2/structured-output/cost/retry behavior remains green.

**Commands:**

```bash
npm --prefix pi-runtime ci
npm --prefix pi-runtime test
npm --prefix labs/pi-replacement ci
npm --prefix labs/pi-replacement run validate
uv run --project backend python -m pytest tests/test_model_provider_contract.py tests/test_field_encryption.py tests/test_llm_fallback_config.py tests/pi_production/test_endpoint_secrets.py tests/pi_production/test_runtime_hardening.py -q
python scripts/security_benchmark.py --fail-on-threshold
```

### Wave 2 — compatibility migration and dual-engine routing

**Acceptance:**

- Given an existing LLM Server row and project engine setting, when dry-run then execute migration is run twice, then the second run is idempotent, the canonical mapping/status is stable, source data remains recoverable, and the secret reference resolves without plaintext export.
- Given a Pi-selected or legacy-selected project, when each dispatcher verb is invoked, then the canonical resolver supplies the target for the selected engine, exactly one usage/route record is written, and an engine/provider failure never silently switches engines.
- Given a deprecated LLM Server client, when it reads/writes during the compatibility window, then it receives the documented adapter/deprecation behavior and no new independent model identity is created.
- Given an unsupported or malformed source row, when migration runs, then it remains `legacy_only`/`blocked` with a reason and is not deleted.

**Commands:**

```bash
uv run --project backend python -m pytest tests/test_llm_servers.py tests/test_settings_agentic_pi_endpoints.py tests/test_pi_runtime_endpoints.py tests/pi_production/test_w1_agentic_contract.py tests/pi_production/test_w1_dispatcher_authority.py tests/pi_production/test_w1_usage_ledger.py tests/pi_production/test_w1_realpath_accounting.py -q
uv run --project backend python -m pytest tests/pi_migration/test_model_management_migration.py tests/pi_migration/test_model_management_rollback.py -q
python scripts/pi_migration_inventory.py --json
uv run --project backend python -m pytest tests/pi_migration/test_count_to_zero.py -q
python scripts/security_benchmark.py --fail-on-threshold
```

### Wave 3 — embeddings, model controls, and selector UX

**Acceptance:**

- Given Pi and legacy embedding dispatch for the same project, when a dimension/model probe runs, then both use the same declared embedding profile or fail before vector/cache writes.
- Given a chat endpoint change, when the project sends a new chat turn, then the embedding profile is unchanged and its identity is visible in safe metadata.
- Given explicit Pi, explicit Istara/legacy, inherited, and invalid selector values, when the UI/API is used, then the existing precedence and validation remain stable and the user can distinguish engine choice from model/endpoint choice.
- Given comparative summaries, when a benchmark/result view renders them, then it displays route/model/metric provenance and provisional status; it does not present unvalidated model prose as research evidence.

**Commands:**

```bash
uv run --project backend python -m pytest tests/pi_production/test_w8_embeddings_gateway.py tests/pi_production/test_w1_agentic_contract.py tests/test_pi_runtime_endpoints.py tests/test_rag_resilience.py tests/test_research_validity_contract.py -q
npm --prefix frontend ci
npm --prefix frontend run test:unit -- --run
npm --prefix frontend run lint
npm --prefix frontend run build
node --test tests/simulation/scenarios/79-engine-selector.mjs
```

### Wave 4 — Petals and audio

**Acceptance:**

- Given a relay/browser donor with consent, health, and project authorization, when an explicit Petals request is made, then it is pinned to the donor, records route evidence, and returns a deterministic result. Given any missing admission condition, it returns typed unavailable and never falls back to a paid/API endpoint.
- Given a same-model local/API endpoint and donor, when resolution runs, then the donor is not selected as ordinary Pi capacity and the isolation test remains green.
- Given local Whisper, supported remote Whisper, diarized provider, unsupported capability, missing credential, low ICR, and ffmpeg-unavailable inputs, when audio flows execute through interview upload and microphone contracts, then results are explicit, bounded, project-scoped, and correctly marked `needs_review`/unavailable.
- Given a transcript, when evidence is persisted, then raw source spans/evidence units and provenance are preserved; no transcript/tag/summary is reportable before coding, reliability, reconciliation, and human review gates.

**Commands:**

```bash
uv run --project backend python -m pytest tests/petals_bridge/test_petals_bridge.py tests/pi_production/test_same_model_donor_isolation.py tests/pi_production/test_research_spine_donor_routing.py tests/test_compute_registry_hardening.py tests/test_project_scope_contracts.py -q
uv run --project backend python -m pytest tests/test_transcription.py tests/test_files.py tests/test_integration_interview.py tests/pi_production/test_w3_research_spine.py tests/test_research_validity_contract.py -q
uv run --project backend python -m pytest tests/test_security_benchmark.py -q
python scripts/security_benchmark.py --fail-on-threshold
```

No live audio provider or model load is required for deterministic acceptance; use mocked HTTP and local dependency seams.

### Wave 5 — docs, Compose QA, and isolated multivac acceptance

**Acceptance:**

- Given the changed UI/routes/stores/models/tests, when feature documentation is regenerated, then every affected living feature page, frontmatter reference, generated site/manifests, architecture contract, and testing document is synchronized.
- Given a clean QA run ID, when each required Compose profile is rendered, then it uses unique project names, no fixed names, internal networks, no local model service in the contract path, and no private target leakage.
- Given the deterministic QA provider stub, when the Pi and legacy contract lanes run, then they exercise identity, migration, embeddings, provenance, and fail-closed behavior without claiming model/research quality. Synthetic data remains provisional.
- Given explicit owner authorization for staging, when the optional multivac adapter runs, then it inventories read-only first, uses unique `/srv/repos`/`/srv/stacks` names and a tunnel/loopback boundary, proves listeners/ports, never mutates the old workload before acceptance, and cleans only its own artifacts.

**Commands:**

```bash
python scripts/feature_docs.py --seed-missing --generate-site --check
uv run --project backend python -m pytest tests/test_feature_docs.py tests/test_feature_obligations.py tests/test_qa_stack_contract.py tests/test_qa_reset_seed.py tests/test_qa_artifacts.py tests/test_synthetic_provisional_boundary.py -q
docker compose -f docker-compose.yml config --quiet
docker compose -f docker-compose.qa.yml --profile contract config --quiet
docker compose -f docker-compose.qa.yml --profile synthetic config --quiet
docker compose -f docker-compose.qa.yml --profile reset config --quiet
docker compose -f docker-compose.qa.yml --profile audit config --quiet
docker compose -f docker-compose.qa.yml --profile live config --quiet
docker compose -f docker-compose.qa.yml --profile ui config --quiet
python scripts/check_feature_obligations.py --base origin/testing --head HEAD
python scripts/check_integrity.py
python scripts/check_ci_governance.py
python scripts/check_test_harness.py
python scripts/check_public_tree_clean.py --base origin/testing --head HEAD
python scripts/security_benchmark.py --fail-on-threshold
compass-forge --workspace /Users/user/Documents/compass-forge gate after --task CF-795 --summary
```

The live profile must remain a render/runtime contract only; setting a live target or starting services requires owner authorization. The multivac commands are an owner-local runbook and must never be embedded in public CI or public docs.

## 9. Test ownership and coverage matrix

The implementation must extend existing tests rather than create an unowned parallel suite. The following ownership is the minimum review map:

| Surface | Existing anchors | New/changed obligations |
|---|---|---|
| Pi package/protocol | `pi-runtime/test/*.test.mjs`, `pi-runtime/PROTOCOL.md`, `tests/pi_production/test_engine_http_provider.py` | Exact version/lockfile and protocol compatibility; no dependency drift |
| Canonical provider catalog | `tests/test_model_provider_contract.py`, `tests/test_pi_runtime_endpoints.py`, `tests/pi_production/test_endpoint_secrets.py` | Identity tuple, aliases, capabilities, credential custody, duplicate handling |
| LLM Server compatibility | `tests/test_llm_servers.py`, `tests/test_settings_agentic_pi_endpoints.py`, simulation scenario 36 | Idempotent mapping, deprecated adapter, unsupported/blocked rows, rollback |
| Engine routing | `tests/pi_production/test_w1_agentic_contract.py`, `test_w1_dispatcher_authority.py`, `test_w1_usage_ledger.py`, `test_w6_engine_selection.py` | Both engines through canonical target; precedence/no fallback/one-row accounting |
| Count-to-zero | `scripts/pi_migration_inventory.py`, `tests/pi_migration/test_count_to_zero.py`, allowlist | Product remains zero; only documented permanent infrastructure remains |
| Embeddings | `tests/pi_production/test_w8_embeddings_gateway.py`, `test_w8_ux_parity.py`, `tests/test_rag_resilience.py` | Profile identity, dimension/dtype mismatch refusal, no cache writes on mismatch |
| Petals/compute | `tests/petals_bridge/test_petals_bridge.py`, donor isolation, compute routing/status contracts | Consent, project scope, exact node identity, unavailable/no paid fallback |
| Audio/research | `tests/test_transcription.py`, `tests/test_files.py`, `tests/test_integration_interview.py`, research-spine tests | Profile capability, diarization, ICR/review, raw evidence units/provenance |
| Frontend/UI | `frontend/src/lib/modelProviders.test.ts`, engine selector simulations, API types | No duplicate options, explicit engine/model/endpoint distinction, accessibility |
| QA/docs | `tests/test_feature_docs.py`, QA stack/provisional/obligation tests | Changed path ownership, generated docs parity, provisional-only QA |
| Security | `tests/test_security_benchmark.py`, `security/control_matrix.json` | Triggered benchmark and control/evidence updates if controls change |

The gate rules named by the work order—`architecture_drift` and `test_ownership`—are load-bearing. Any new canonical model-management file must be listed in `testing/feature_coverage.yml` or a reviewed mechanical exception, and every behavior-changing file must have an owning test/doc obligation.

## 10. Documentation and manifest obligations

Update living documentation in the same implementation initiative, preserving historical dated plans as immutable records and writing successor records when facts change:

- `docs/architecture/agentic_core.md`: canonical identity/transport boundary, explicit engine resolution, legacy adapter versus legacy infrastructure, and usage/route evidence.
- `docs/architecture/research-validity-contract.md`: route/evidence provenance, audio/source evidence, provisional QA, and no reportability bypass.
- `docs/architecture/self-improvement-governance-contract.md` if telemetry/benchmark/model learning behavior changes.
- Feature pages at minimum: `settings.llm-servers`, `chat.model-controls`, `interviews.transcription`, `compute.pool`, embeddings/memory health, chat audio, engine selector, and any new provider/credential/audio pages discovered by the feature inventory.
- `README.md`, `README.pt-BR.md`, `DOCUMENTATION.md`, `TESTING.md`, `CHANGE_CHECKLIST.md`, `SYSTEM_CHANGE_MATRIX.md`, and `testing/TESTING_STRATEGY.md` where the migration/testing contract changes. Do not place private multivac host details in public docs.
- `testing/feature_coverage.yml` and related QA capability/obligation files for all changed paths.
- `security/control_matrix.json`, `security/SECURITY_BENCHMARK.md`, and `tests/test_security_benchmark.py` only when a security control, evidence path, standard version, or trigger pattern changes; the benchmark itself is mandatory for the touched surfaces.
- Regenerate the site/manifests with:

```bash
python scripts/feature_docs.py --seed-missing --generate-site --check
```

Generated site files are outputs of that command; do not hand-edit generated integration files or silently modify external repositories.

## 11. Security and privacy review checklist

The security reviewer must explicitly cover:

- credential source precedence and rotation; Keychain/env/encrypted DB reads;
- encryption context/version compatibility for migrated `LLMServer.api_key` values;
- SSRF/URL normalization and loopback/HTTPS policy for custom endpoints;
- OAuth redirect/token custody and refresh handling;
- admin/project authorization on catalog, credential, migration, Petals consent, and audio profile routes;
- model/endpoint/credential enumeration and safe redaction in UI/API/telemetry/logs;
- no secret values in migration exports, Compose interpolation, QA artifacts, or CF evidence;
- worker private-pipe binding, protocol limits, retry/cost accounting, and malformed-frame behavior;
- explicit engine/endpoint selection not bypassing Research Spine route evidence;
- donor consent, project scope, same-model isolation, and typed Petals unavailable behavior;
- audio upload size/type/scanner/temp-file cleanup, remote provider credentials, and diarization privacy;
- no public multivac references, firewall changes, or unrelated workload cleanup.

Required command for any auth/provider/secret/agentic/Petals change:

```bash
python scripts/security_benchmark.py --fail-on-threshold
```

Do not suppress inherited gate failures silently. Record the baseline and post-change comparison, and either fix new failures or create an explicit, expiring, justified suppression under project policy.

## 12. Risks and mitigations

| Risk | Mitigation / detection | Rollback |
|---|---|---|
| Package update changes Pi protocol behavior | Pin exact versions, run worker/backend contract suites, compare protocol v2 frames, update only with evidence | Restore prior package/lockfiles and worker checkout |
| Duplicate model IDs or endpoint aliases | Provider-qualified model IDs, stable endpoint IDs, migration uniqueness constraints and duplicate tests | Restore canonical mapping; source rows remain intact |
| Lost/invalid API key during migration | In-memory decrypt/re-encrypt, credential status matrix, no plaintext export, key-resolution tests | Keep source encrypted field and use legacy compatibility reference |
| Canonical resolver accidentally uses donor capacity | Static import boundary, donor isolation tests, explicit transport class | Disable Pi-primary mode; keep legacy/donor paths |
| Engine silently falls back on failure | Explicit engine target and typed error tests, one-row accounting | Revert rollout mode/project engine to legacy explicitly |
| Embedding drift corrupts retrieval | Persist profile/model/dimension/dtype, startup probe, block mismatch before cache/write | Restore previous embedding profile and vectors; reindex only as a deliberate versioned migration |
| Petals donor leaks project data or paid fallback hides failure | Bridge admission, project scope, route evidence, typed 503/no fallback | Disable bridge/Pi Petals mode; donor registry remains unchanged |
| Audio profile exposes unsupported or private provider behavior | Capability contract, local/mock tests, secret custody, no implicit fallback, `needs_review` | Return unavailable and retain existing local path |
| Compatibility API becomes a second source of truth | Deprecated adapter writes canonical only; source-to-canonical mapping and count tests | Re-enable read adapter; do not delete rows |
| QA false confidence | Contract stub labeled non-quality, synthetic provisional guard, live lane owner-gated | Stop QA project and retain evidence; never promote synthetic artifacts |
| Multivac mutation/collision | Read-only inventory, unique project/paths, old-stack diff, cleanup allowlist | Tear down only new project; old stack remains untouched |
| Docs/generated drift | Feature obligation classifier and feature-doc regeneration in same task | Block acceptance until docs/manifests are regenerated |

## 13. Definition of Ready / Done

### Ready for implementation

- This draft is reconciled with the other architect drafts into one MECE master plan and owner-approved at the explicit plan gate.
- Exact canonical identity, credential, migration-state, engine-transport, embedding-profile, audio-profile, and Petals boundaries are accepted.
- CF work orders name dependencies, changed-path ownership, tests, docs, rollback, and gates for each wave.
- Latest Pi release is rechecked passively at dependency-update execution time; no live LLM/model load is required.
- Baseline gate output and known inherited failures are attached; no new implementation begins while the plan gate is pending.

### Done for the initiative

- All required waves have green task command evidence and post-change gate evidence, or an explicit owner-approved residual risk.
- Canonical model/endpoint/credential behavior is proven without duplicate identity semantics or secret leakage.
- Both engines remain explicitly selectable and independently fail closed, with one usage/route record per dispatch.
- LLM Server migration is idempotent, reversible, observed, and deprecated; no row is deleted without the separate removal gate.
- Embedding profile, Petals bridge, audio/transcription, Research Spine, UI, QA/Compose, security benchmark, docs/manifests, and test ownership obligations are complete.
- Optional multivac staging, if authorized and required, has read-only inventory, unique namespace, tunnel/listener evidence, route/vector/project-scope proof, and cleanup evidence; otherwise it is explicitly marked blocked/advisory and public QA remains green.
- The lifecycle status/ledger, CF evidence, findings register, and final summary accurately describe the result. No implementation stage claims completion from a plan-only artifact.

## 14. Coverage and bounded reference matrix

| Requirement | Covered in this draft | Evidence/source anchor |
|---|---|---|
| Latest verified Pi dependency | §§2.1, 7, 8 Wave 0/1 | `pi-runtime/package.json`, lab package, framing ledger, `pi-runtime/PROTOCOL.md` |
| Canonical model/provider/endpoint ownership | §§4.1–4.3 | `config.py`, `endpoints.py`, `model_manager.py`, settings/LLM routes |
| Exact data/secret migration | §5 | `LLMServer`, field encryption, migration/rollback state machine |
| Both engines and no duplicate semantics | §§4.2, 4.4, Wave 2 | dispatcher, legacy executor, engine tests |
| Reversible LLM Server retirement | §§5–6, Wave 2 | compatibility state machine, deprecation/removal gates |
| Embedding/vector-space invariant | §4.5, Wave 3 | `embeddings_gateway.py`, research-validity contract |
| Petals donor bridge | §4.6, Wave 4 | `petals_bridge.py`, donor isolation/compute contracts |
| Audio/Whisper/diarization | §4.7, Wave 4 | transcription/file/chat routes, evidence-unit persistence |
| UI selector/model controls | §§2.7, 8 Wave 3 | Settings/project UI, frontend contracts/simulations |
| Testing branch Docker QA | §§2.7, 8 Wave 5 | `docker-compose.qa.yml`, `testing/feature_coverage.yml`, QA contracts |
| Security benchmark | §§11, Wave commands | `AGENTS.md`, benchmark/control matrix contract |
| Multivac hygiene | §8 Wave 5, risk table | optional staging contract in public testing plan; owner authorization boundary |
| Research Spine | §§2.4, 4.7, Wave 3/4/5 | `docs/architecture/research-validity-contract.md` |
| Control-plane references | bounded below | Rust/Skills branches; no cutover |

The bounded control-plane references are process/design comparators only:

- Compass Forge `08d3233` (`build-stream/compass-forge-rust-runtime`) demonstrates the in-flight Rust control-plane/dashboard and Build Stream checkpoint boundary.
- Skills `e45211e` (`build-stream/conductor-dspy-gepa`) demonstrates conductor stage execution/credential attachment mechanics.
- Skills `3d4277b` (`build-stream/wave3-l35-remediation`) demonstrates a bounded remediation checkpoint.

None of these references authorizes changing their repositories, importing their runtime into Istara, or cutting them into `main`. The Istara migration remains governed by `CF-SPEC-59`, this worktree, its immutable wave manifest, and the owner approval gate.

## 15. Handoff note

This is an independent draft only. The next architect/conductor step should compare it with the other immutable drafts, reconcile any schema or wave conflicts into one MECE master plan, and stop at the owner approval gate. No source implementation, lifecycle-file edit, Docker start, live provider call, model load, multivac access, merge, push, or PR is authorized from this stage.
