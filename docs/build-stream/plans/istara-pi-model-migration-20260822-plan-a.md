# Independent S1 Draft (Slot A, repaired) — Pi Model-Management Migration (resumed 2026-08-22)

**Task:** `ISTARA-PI-MODEL-MIGRATION-20260822-REPLAN-A-r1` (consensus draft repair a; supersedes the L-2 draft at the misnamed `istara-pi-model-management-20260822-plan-a.md` path)
**Role:** `istara-pi-model-management-20260822-architect-a`
**Spec:** `CF-SPEC-1` (this run); framing reference `CF-SPEC-58` (frozen 2026-08-18 run)
**Planning phase:** `draft` (repair — this is the authoritative `plan_file` for slot A: `docs/build-stream/plans/istara-pi-model-migration-20260822-plan-a.md`)
**Branch:** `conductor/istara-pi-model-management-migration-20260822`, base `origin/testing@15260a78`
**Status:** Independent draft for architect consensus; implementation is prohibited until the consensus master plan is frozen and the owner approval gate is recorded.

> **Repair note (REPLAN-A-r1, 2026-08-22):** The L-2 slot-A draft was delivered under the wrong filename
> (`istara-pi-model-management-20260822-plan-a.md`) instead of this task's `plan_file`
> (`istara-pi-model-migration-20260822-plan-a.md`), so the synthesis phase could not consume it.
> This file is the repaired, authoritative slot-A draft: full content preserved from the L-2
> draft, re-verified against the tree at repair time (Pi latest 0.84.2/0.84.2; inventory ratchet 0
> with 1 allowlisted permanent site; gate before 30 inherited / 0 new; 62 tests collect across the
> six key surfaces), and corrected where noted (C7: `vpsctl.py` lives in the vps skill, not the repo).
> The misnamed duplicate is removed in the same commit.

## 1. Executive summary

Istara has two model-management identity planes: legacy persisted `LLMServer` rows
(`llm_servers` table, CRUD, live `ComputeRegistry` registration, Fernet-encrypted
`api_key`) and Pi's provider/model catalog with endpoint resolver
(`PiEndpointResolver`/`PiModelManager`/`PiExecutionService`). The agentic dispatch
ratchet is already at **0 direct product call sites** (`tests/pi_migration/
test_count_to_zero.py`), so this is not a call-site migration — it is a
**model-management authority migration**: make Pi the canonical catalog/secret/
endpoint-identity owner, migrate legacy configuration and secrets with zero silent
loss and a deterministic rollback, keep both explicit engines (`pi`, `legacy`)
selectable with no silent fallback in either direction, preserve the embedding
vector-space invariant, the Petals donor bridge, audio/transcription flows, UI
contracts, deterministic testing-branch Docker QA, and — new for this run —
isolated VPS acceptance on the managed VPS per the `vps` skill (multivac is no
longer available, DEC-2).

The recommendation of the carried-forward drafts is confirmed: do **not** equate
"Pi owns model management" with "delete every legacy LLM Server, Ollama, LM Studio,
or ComputeRegistry module." The legacy plane becomes a reversible compatibility
adapter and migration source; retirement is staged, evidence-gated, and
owner-approved at each major transition. The migration is additive and idempotent
first: inventory → map → validate → dual-read/shadow → canary → Pi-primary →
deprecate → (separate, later) retire.

This draft was independently verified against the current tree on 2026-08-22 and
carries the three 2026-08-18 drafts forward with corrections (section 3), the most
important being the multivac → managed-VPS replacement and the re-baselining of
task numbering, versions, and gate debt.

## 2. Verified current-state boundary (this tree, base 15260a78)

All of the following were re-inspected on 2026-08-22 and match the carried drafts'
inventory (with updated facts where noted). This is the boundary the plan protects;
nothing here is altered by the planning stage.

### 2.1 Legacy LLM Server plane (retirement target, reversibly)

| Surface | Location | Role |
|---|---|---|
| Model | `backend/app/models/llm_server.py` (table `llm_servers`) | name, provider_type, host, encrypted api_key, is_local, is_healthy, is_relay, priority, last_health_check, last_latency_ms, capabilities JSON |
| CRUD + health + discover | `backend/app/api/routes/llm_servers.py` | admin-gated `GET/POST/PATCH/DELETE /llm-servers`, `/health-check`, `/discover`; refreshes Pi catalog projection after mutations (`_refresh_pi_catalog_projection`) |
| Live registry | `backend/app/core/llm_router.py` | backward-compat wrapper over `ComputeRegistry` (`LLMServerEntry`, register/unregister/list, health delegation) |
| Compute registry | `backend/app/core/compute_registry*.py` | donor-schedulable node registry; must never contain Pi endpoints |
| Startup + discovery | `backend/app/core/ollama.py` (`load_persisted_servers_async`), `backend/app/core/network_discovery.py` (`discover_and_register`) | re-hydrates rows into live router; relay rows flagged `is_relay` |
| Encryption | `backend/app/core/field_encryption.py` (Fernet, `DATA_ENCRYPTION_KEY`) | `encrypt_field`/`decrypt_field` for `api_key` and other secrets |
| Endpoint safety | `backend/app/core/endpoint_security.py` | URL normalization, plaintext/credential rejection, redaction |
| Consumers | `backend/app/core/compute_node*.py`, `compute_registry*.py`, `autoresearch_runners/model_temp.py`, `api/routes/settings.py`, `api/routes/admin.py`, `services/research_validity_service.py` | read catalog/models for UI, benchmarks, research-validity surfaces |
| Schema | `backend/alembic/versions/002_distributed_platform.py` (drops `llm_servers` on downgrade only) | table created in 001 |

### 2.2 Pi model-management plane (target authority)

| Surface | Location | Verified facts |
|---|---|---|
| Endpoint model + resolver | `backend/app/core/pi_runtime/endpoints.py` | `DEFAULT_ENDPOINT_ID="pi-deepseek-default"`, `SECRET_CACHE_TTL_SECONDS=60.0`, Keychain/env secret resolution, fail-closed typed errors |
| Catalog | `backend/app/core/pi_runtime/model_manager.py` | three sources: static settings endpoints + default; read-only `LLMServer` projection as `pi-llm-<id>` (relay rows NEVER projected); local Ollama/LM Studio; plus one-directional Petals projection; `resolve`/`resolve_distinct`/`resolve_embed`/`catalog`; `reset_db_projection` weakref invalidation |
| Engine facade | `backend/app/core/pi_runtime/engine.py` | `PiExecutionService` governed seams: chat/delegation/channel/autoresearch/completion/react/structured/ensemble; telemetry; tool-authority rejection |
| Worker | `backend/app/core/pi_runtime/supervisor.py` + `pi-runtime/src/worker.mjs` | one Node child per process, NDJSON protocol v2 (`PROTOCOL_VERSION=2` both sides, `pi-runtime/PROTOCOL.md`), secrets only in `provider.bind` frames |
| Embeddings | `backend/app/core/pi_runtime/embeddings_gateway.py` | `EmbeddingsGateway`, `assert_vector_space_invariant` probes both engines with the same model |
| Provisioning | `backend/app/core/pi_runtime/model_manager_provisioning.py` | local `kind=local` ensure-model via Ollama/LM Studio helpers, never donated compute |
| Seams | `backend/app/core/pi_runtime/seams.py` | governance clause + fail-closed glue for A2A/channel/autoresearch |
| Dispatcher | `backend/app/core/agentic/dispatcher.py`, `legacy.py`, `usage_ledger.py` | precedence per-call → request header → project `agentic_engine` → `settings.agentic_engine_default` ("legacy" until owner flips); one usage-ledger row per dispatch; no silent fallback |
| Pi engine vocabulary | `backend/app/core/pi_replacement.py` | `PI_ENGINE_VALUES={"pi","pi-candidate","pi-replacement","deepseek-pi"}` |
| Frontend | `frontend/src/lib/modelCatalog.ts` (`mergeModelCatalogs`), `frontend/src/lib/modelProviders.ts`, `frontend/src/components/settings/ProjectSettingsView.tsx`, `frontend/src/components/common/SettingsView.tsx`, `Sidebar.tsx` | merged catalog, per-project engine selector, legacy server inventory + Pi endpoint list |

### 2.3 Coupled governed surfaces

- **Embeddings / vector space**: `backend/app/core/embeddings.py`, `embedding_validation.py`, `embedding_cache.py`; invariant anchored on `default_embed_model()`. The default embedding model currently follows active local-provider settings — a migration must make the embedding profile explicit and stable.
- **Petals donor bridge**: `backend/app/core/petals_bridge.py`, `backend/app/api/routes/petals_bridge.py` — consented relay/browser donors projected as `pi-petals-<node_id>`; typed `PetalsUnavailable` (503); no paid fallback; route stamp; `settings.petals_bridge_enabled`. Tests: `tests/petals_bridge/`, `tests/pi_production/test_same_model_donor_isolation.py`.
- **Audio / transcription**: `backend/app/core/transcription.py` (local Whisper + ICR consensus, `needs_review` on low agreement), `backend/app/core/file_processor.py` (uploaded audio), `backend/app/api/routes/chat.py` (microphone upload), `backend/app/api/routes/chat_voice.py` + second `/chat/voice-transcribe` (phase-alpha/error/dummy surfaces), `files.py` (transcript metadata + raw-source evidence units). No unified audio-model settings contract exists yet.
- **UI contracts**: `frontend/src/lib/modelCatalog.ts`, model pickers, engine selector; living feature docs present for `settings/llm-servers`, `chat/model-controls`, `chat/audio`, `interviews/transcription`, `settings/compute-donation`, `compute/pool`.
- **QA**: `docker-compose.qa.yml` (profiles: contract/synthetic/reset/audit/live/ui; unique `istara-qa-<run-id>` project names; internal networks; no fixed container_name), `qa/` (`runtime_capabilities.json`, `scripts/*`, `Dockerfile`, `provider-stub.Dockerfile`), `scripts/istara-qa.sh`, `tests/test_qa_stack_contract.py`, `tests/test_provider_contracts.py`.
- **Relay**: `relay/` (Node ws relay, `relay/Dockerfile`, `relay/index.mjs`) — the donor transport; in scope only for Petals preservation, never as Pi capacity.
- **Research spine**: `docs/architecture/research-validity-contract.md`; `backend/app/core/research_validity.py`; `tests/test_research_validity_contract.py`. Any migrated surface touching research data must preserve evidence-unit → coding → reliability → reconciliation → human review → Done → report gates.

### 2.4 Version and ratchet facts (re-verified 2026-08-22)

- `pi-runtime/package.json` pins `@earendil-works/pi-agent-core@0.83.0` + `@earendil-works/pi-ai@0.83.0`; lockfile matches.
- `labs/pi-replacement/package.json` pins `0.80.10` + `0.80.10` — the lab comparison surface must not silently diverge from the production runtime after the upgrade (the lab is a comparator, not production; it must be raised in lockstep and revalidated).
- **Passive registry re-check (this draft, 2026-08-22):** `npm view @earendil-works/pi-agent-core version` → **0.84.2**; `npm view @earendil-works/pi-ai version` → **0.84.2**. Matches the framing observation. Implementation must re-run the passive query immediately before changing dependencies and record provenance + protocol compatibility (v2, structured output, cost ceilings, retry discipline — `pi-runtime/PROTOCOL.md`).
- `scripts/pi_migration_inventory.py` output at HEAD: **1 allowlisted permanent site** (`backend/app/core/agentic/legacy.py` `server.chat(` — permanent legacy executor transport). `EXPECTED_PRODUCT_SITES = 0`.
- **Gate baseline (this draft):** `compass-forge gate before` → status `fail`, **30 inherited failures** (`secret_flow`, `unexpected_large_files`), **0 new failures**, 0 actionable, drift: route 4 / type 2. (The 2026-08-18 drafts recorded 80 inherited failures; the baseline has since improved. Every later evidence narrative must separate inherited debt from migration findings.)
- 62 tests across the six key surfaces (`test_count_to_zero`, `test_llm_servers`, `test_pi_runtime_endpoints`, `test_settings_agentic_pi_endpoints`, `test_petals_bridge`, `test_transcription`) **collect cleanly** at HEAD (collection-only; no live workers).

## 3. Corrections and extensions to the carried-forward drafts

The three carried drafts (`carried-20260818-plan-{a,b,c}.md`) were used as inputs and
independently verified. Confirmed facts are in section 2. The following are the
deliberate corrections/extensions for this run:

| # | Carried-draft claim | Correction for this run | Evidence |
|---|---|---|---|
| C1 | Staging acceptance on multivac (plans A §8 W5, B §11, C W6) | **Multivac is no longer available (DEC-2).** Final acceptance deploys on the managed VPS per the `vps` skill: Dokploy Docker Compose **strict single-workload profile**, `vpsctl.py preflight → inventory → deploy → verify-isolation → verify-exposure → audit-anchor`, firewall/DOCKER-USER evidence, no firewall/port changes without owner approval, rollback preserved until owner accepts. | Lifecycle DEC-2, `vps` skill (`~/.pi/agent/skills/vps/SKILL.md`), manifest wave `qa-docs-vps` instructions |
| C2 | CF task numbers `CF-787`…`CF-805` (old run's graph, CF-SPEC-59) | Those tasks belong to the **frozen** 2026-08-18 run. This run is CF-SPEC-1 with a fresh six-wave manifest (`foundation`, `pi-catalog-secrets`, `compat-routing`, `embeddings-controls`, `petals-audio`, `qa-docs-vps`); implementation tasks are generated at owner approval. This draft maps to wave IDs, not old CF numbers. | Lifecycle DEC-1, manifest `istara-pi-model-management-migration-20260822.json` |
| C3 | Baseline "80 inherited gate failures" | Re-measured: **30 inherited failures** (secret_flow, unexpected_large_files), 0 new, at this run's base. Use the fresh baseline; do not copy the old number. | `compass-forge gate before` (2026-08-22) |
| C4 | Pi versions "0.83.0 / 0.80.10, latest 0.84.2 observed" | Re-verified passively: latest is still **0.84.2** for both packages (2026-08-22). The dependency-update task must re-check at execution time and record lockfile resolution + protocol compatibility. | `npm view` (2026-08-22) |
| C5 | VPS wave scope in carried plan C treated VPS as "multivac" shell scripts | The VPS wave must use the **vps skill contract verbatim**: SSH key `~/.ssh/id_ed25519_capi`, every remote command through `vpsctl.py ssh -- …`, `internal: true` single bridge network, one published port, no Docker socket/host ns/privileged, Dokploy secret UI for secrets, audit-anchor after final checks. | `vps` skill |
| C7 | (repair) `scripts/vpsctl.py` implied inside this repo (L-2 draft §8 W5) | `vpsctl.py` is **not** in this repo — it lives in the vps skill at `~/.pi/agent/skills/vps/scripts/vpsctl.py` (mirror `/Users/user/Documents/Skills/vps/scripts/vpsctl.py`). VPS-wave commands must run it from the skill path (e.g. `python3 ~/.pi/agent/skills/vps/scripts/vpsctl.py …`); subcommands verified at repair time: `preflight, inventory, audit-verify, audit-anchor, verify-isolation, verify-exposure, ssh`. | `vps` skill; `--help` at repair time |
| C6 | (plan A) `pi-runtime` env prerequisite implied | Make explicit: worker-backed Pi tests require `pi-runtime/node_modules` (`cd pi-runtime && npm ci`); the upgraded pin must resolve before worker-backed suites run. | carried plan C W1 note, confirmed tree state (no node_modules at HEAD) |

## 4. Goals, non-goals, and invariants

### Goals

1. Update both bundled Pi package surfaces (`pi-runtime`, `labs/pi-replacement`) to the latest **verified compatible** upstream release (0.84.2 as of 2026-08-22; re-verify at execution), with reproducible lockfiles and protocol-v2 contract tests.
2. Establish one canonical Pi-owned catalog for provider families, model IDs, endpoint IDs, capabilities, local/cloud/custom/OAuth/API-key configuration, and credential references.
3. Preserve both explicit engines and their selection semantics while making endpoint/model resolution canonical and fail-closed.
4. Migrate all mappable LLM Server configuration and encrypted secrets without data or secret loss — idempotent, evidenced, reversible, with a bounded deprecated adapter.
5. Preserve the shared embedding model/dimension/dtype invariant; make embedding identity explicit and visible in safe metadata.
6. Preserve Petals consent, project authorization, donor identity pinning, route evidence, and fail-closed no-fallback behavior.
7. Add governed audio/Whisper/diarization model configuration without bypassing the Research Spine or inventing unsupported Pi audio behavior.
8. Update UI, living feature docs, manifests, test ownership, testing-branch Compose obligations, security evidence, and (owner-authorized) isolated VPS acceptance.

### Non-goals

- No merge, push, PR, or `main` change — everything stays on the `testing` branch lineage; the conductor ship stage owns merge/push, gated by cast config.
- Do not delete `LLMs/` or `Model_Finetuning/`, clean external repos, or touch unrelated Docker workloads.
- Do not delete the legacy transport, ComputeRegistry, donor relay/browser transport, local model provisioning, or the permanent legacy executor merely because Pi becomes the model-management authority.
- No live model loading, no live backend/frontend servers, no live completion calls, no private endpoint access without explicit owner authorization.
- Do not treat synthetic QA, raw tool success, transcript keyword tags, or comparative model prose as accepted research evidence.
- Do not silently merge endpoint identities that share a model name or host.
- No firewall/VPS exposure changes without owner approval.

### Invariants that must remain true (proof anchors)

| Invariant | Required contract | Primary proof |
|---|---|---|
| Pi/runtime isolation | `pi_runtime` never imports or mutates `ComputeRegistry`; Pi resolution never donor-scores | `tests/pi_production/test_same_model_donor_isolation.py` |
| Explicit engine choice | Per-call/header/project/global precedence stable; selected engine errors, never silently falls back | `test_w1_agentic_contract.py`, `test_w1_dispatcher_authority.py`, `test_w6_engine_selection.py` |
| One identity plane | Canonical `model_id` distinct from stable `endpoint_id`; legacy IDs are provenance aliases only; no duplicate canonical identities | new migration/catalog contract tests |
| Secret safety | Plaintext credentials only in short-lived in-memory binding; none in logs/responses/docs/QA artifacts/telemetry/CF evidence | `test_endpoint_secrets.py`, security benchmark |
| Vector-space safety | Chat-engine/provider changes cannot silently alter the embedding profile; model/dimension/dtype mismatch blocks before cache/writes | `test_w8_embeddings_gateway.py` |
| Donor security | Consent + health + project authorization + exact node pin all required; unavailable = typed 503, no paid fallback | Petals + donor-isolation tests |
| Research validity | Source spans → evidence units; candidate/provisional outputs cannot bypass coding/reliability/reconciliation/review/Done/report gates | `test_research_validity_contract.py`, synthetic boundary tests |
| Migration reversibility | Every source row has a mapping/status and restorable snapshot before write/cutover | new migration state/rollback tests |
| QA isolation | Unique disposable project/paths; no fixed names; no private target config in public CI | QA stack + cleanup contract tests |
| VPS isolation | Strict single-workload profile: one internal network, one published port, no host/other-container reachability | `vpsctl.py verify-isolation`/`verify-exposure`, firewall/DOCKER-USER evidence |

## 5. Target architecture

### 5.1 Canonical identity model (additive schema)

Semantic split (names adjustable at implementation, split is load-bearing):

```text
CanonicalModel
  model_id: stable provider-qualified identity (e.g. provider_key/model_key)
  provider_family: openai_compat | anthropic_compat | local_ollama |
                   local_lmstudio | whisper | diarization | ...
  canonical_name: provider/model identity, not a display label
  aliases: observed provider aliases with provenance (legacy ids are aliases only)

CanonicalEndpoint
  endpoint_id: stable route identity (distinct from model_id)
  model_id: ref
  transport: pi_http | legacy_registry | local_lifecycle | petals_bridge | audio_adapter
  endpoint_kind: cloud | custom | local | petals | audio
  nonsecret connection metadata + capabilities
  credential_ref: opaque ref into Pi credential custody
  legacy_source_id: nullable LLMServer id (migration provenance ONLY)
  migration_state + timestamps

CredentialRef
  credential_ref: opaque stable name
  kind: keychain | encrypted_db | environment | oauth
  secret material: encrypted/externally held only; status: present|missing|invalid|rotation_required

EmbeddingProfile
  profile_id, model identity, endpoint/transport identity, dimension, dtype,
  normalization, profile version, health status
```

Rules:
- `model_id` is provider-qualified and normalized, never a UI display string; two providers exposing the same visible model name remain distinct canonical identities unless an explicit provider alias mapping proves equivalence.
- `endpoint_id` is always distinct from `model_id`; route evidence always retains endpoint identity.
- `legacy_source_id` / `pi-llm-<id>` / `pi-petals-<node_id>` are aliases/provenance, never independent identities; once migrated, the resolver must not emit both a legacy and a Pi canonical option for the same endpoint.
- Capability metadata is attached to endpoint/model profiles and never inferred from a name; unknown capability fails closed when a caller requires it.
- `base_url`, host labels, credential refs, route IDs are never in public feature docs, QA artifacts, or normal telemetry; admin views return redacted/safe metadata and `has_credential` only.

### 5.2 Resolver and transport boundary

One canonical resolution request consumed by every dispatcher verb:

```text
resolve_model_request(project_id, engine, model_id?, endpoint_id?, purpose,
                      capabilities?, embedding_profile_id?) -> ResolvedModelTarget
```

`ResolvedModelTarget` = canonical model ID, endpoint ID, transport class, safe
capabilities, credential reference, route-evidence fields. No plaintext credentials.

- `PiModelManager` becomes the authoritative catalog/resolver (owns refresh, exact identity, capability admission, migration projection).
- `PiExecutionService` consumes a Pi target and binds its secret only to the worker; rejects non-Pi transports.
- The legacy executor remains a transport adapter (`transport=legacy_registry`/`local_lifecycle`), preserving legacy request shapes and ComputeRegistry project authorization; it must not manufacture a second catalog.
- Petals uses explicit `transport=petals_bridge` targets through bridge admission; never a capacity candidate.
- Audio adapters use `transport=audio_adapter` with an explicit capability contract; binary audio never routes through the text Pi worker unless a separately verified provider API supports it.
- All verbs continue through `AgenticDispatcher` with exactly one usage/route row; resolution failure is a typed failure, never a fallback to another engine.

### 5.3 Provider and secret custody

Supported configuration classes (explicit): cloud/OpenAI-compatible, Anthropic-compatible, OAuth, API-key (Keychain/env/encrypted DB), custom/local (normalized loopback or approved HTTPS), audio/Whisper/diarization. Rules:

- Legacy `LLMServer.api_key` (Fernet) may be read only inside a migration service that immediately re-encrypts or externalizes; the migration manifest stores credential reference, source kind, presence/status, and a nonsecret metadata checksum — never plaintext, raw tokens, or reusable secret fingerprints.
- Keychain references preserve service/account identities without copying values.
- Encryption validated against standalone Pi semantics (the migration must not assume the same encryption context/version — record and test context compatibility).

### 5.4 Engine selection and rollback semantics

Preserve precedence exactly: per-call → header → project `agentic_engine` → `settings.agentic_engine_default` (default `legacy` until the owner flips it). Canonical target resolution happens **after** engine selection — never a hidden second engine choice. A selected `pi` target with missing credentials, unsupported capability, worker failure, or provider error is a failed Pi invocation. A selected `legacy` target preserves the legacy transport and route evidence. Rollback = explicit mode/project flip to `legacy` + snapshot restore, never an implicit exception fallback.

### 5.5 Embeddings

- One authoritative `EmbeddingProfile` for both engines: model identity, endpoint/transport identity, dimension, dtype, normalization, profile version.
- Engine adapters may differ in transport but must return vectors in the declared profile; mismatch blocks startup/engine switching and cache writes.
- Existing vectors stay tied to their recorded profile; deliberate profile migration = new profile version + bounded re-embed job + dual-read/reindex evidence + explicit invalidation.
- Chat endpoint changes never mutate the embedding profile; UI separates chat controls from embedding profile controls.
- Pi gateway retains one dispatcher-owned usage row; no double accounting.

### 5.6 Petals

- `petals_bridge.py` stays outside `pi_runtime`; projects only `source in {relay,browser}`, `pi_served=true`, healthy, project-authorized donors.
- Explicit `endpoint_id=pi-petals-<node>` or governed Petals purpose only; never donor selection by model-name collision, latency, or capacity when a Pi endpoint is requested.
- Unknown/unconsented/unhealthy/unauthorized donor → typed 503 + route evidence; no paid fallback.
- Donor lifecycle + selected/served/failed counters preserved; donor route identity visible to audit without prompts, URLs, or secrets.

### 5.7 Audio and diarization

Add a canonical `AudioModelProfile` contract: profile ID, provider family, model ID, endpoint ID, credential ref, local/remote mode, language policy, diarization support, speaker-count policy, timestamps, confidence policy, human-review threshold.

- `local_whisper`: existing local model loader + ffmpeg boundary; model size becomes validated configuration.
- `remote_whisper`/`remote_diarization`: opt-in endpoint adapters with capability metadata, explicit credential custody, bounded file size/timeouts, redacted errors, deterministic mocked contract tests. A provider without diarization cannot be advertised as diarized.
- Interview uploads, microphone chat, channel audio resolve the same profile contract with project authorization and source provenance preserved.
- Transcriptions remain candidate/provisional until raw source spans/evidence units, coding, reliability, reconciliation, and human review gates accept them; ICR failure stays `needs_review`.
- No configured audio profile → typed unavailable; never an implicit text-chat fallback.

## 6. Exact migration and rollback procedure

### 6.1 Preflight and immutable evidence (before any write or flag cutover)

1. Record branch/base commit, schema revision, package versions + lockfile hashes, and `gate before` output.
2. Export a redacted inventory of static Pi settings, `LLMServer` rows, aliases, relay/browser rows, local provider settings, project engine selections, embedding metadata — source IDs and mapping reasons only, never secret values or private endpoints.
3. Create an encrypted database backup/snapshot + preserve pre-change checkout/Compose definition (disposable/gitignored path, owner-approved retention).
4. Resolve only credential **presence/status** in a controlled dry-run; no live completions, no model loads, secrets never printed.
5. Record deterministic `migration_id`, schema version, source metadata checksum, migration-tool version; a repeated run with the same checksum is a no-op.

### 6.2 Deterministic mapping

Per non-relay `LLMServer` row: normalize provider family + endpoint URL (endpoint-security rules) → parse capability JSON without inventing model names (absent model = explicit `unknown/default` needing validation) → resolve/create provider-qualified canonical model ID → resolve/create exactly one canonical endpoint tied to the source row (`legacy_source_id`, source provider, priority, health summary, capability provenance preserved) → create credential reference (in-memory decrypt + re-encrypt through canonical custody, or nonsecret local mode for Ollama/no-key, or preserve Keychain service/account refs) → mark row `mapped` / `credential_validated` / `blocked` / `legacy_only` with an actionable reason → store a redacted mapping result (never compare or log raw secrets).

Relay/browser rows are never migrated into ordinary Pi endpoints; they remain donor-plane identities handled only by the Petals bridge contract.

### 6.3 Staged cutover state machine (additive migration/status metadata)

```text
unmapped -> mapped -> credential_validated -> shadow_verified
        -> pi_primary -> legacy_deprecated -> retired
any state -> blocked (reason + evidence handle)
pi_primary / legacy_deprecated -> rollback_ready -> legacy_compat
```

- **Mapped:** canonical target exists; source row untouched; no cutover.
- **Credential validated:** secret reference resolves in memory; capability metadata valid; no completion call needed for deterministic QA.
- **Shadow verified:** read-only resolution + metadata parity for a canary project/contract stub; never double-sends user research content to a provider.
- **Pi primary:** Pi selected for opted-in project/route; legacy data readable through the adapter.
- **Legacy deprecated:** admin writes use canonical Pi management; legacy endpoints return deprecation metadata + read-only compatibility projections; existing project selections resolve through the mapping.
- **Retired:** only after §7 removal criteria pass, an owner gate accepts evidence, and retention/restore is satisfied. Retirement first disables runtime use; physical row deletion is a separate, later owner-approved action.

### 6.4 Rollback (explicit operation, not an exception handler)

1. Stop the staged QA/temporary Compose project before changing data.
2. Set migration mode/project selection back to `legacy`/`legacy_compat`; do not change unrelated projects.
3. Restore the pre-cutover canonical mapping/status snapshot if the mapping itself is corrupt; keep the failed-migration report.
4. Restore the encrypted DB/config snapshot only when additive rollback cannot recover the source; verify schema downgrade/restore compatibility first.
5. Restore the previous checkout/Compose image; rerun legacy routing, embedding dimension, donor isolation, source-evidence contract tests.
6. Prove no source LLM Server row, project engine setting, vector, donor consent, or audit row was lost; record rollback command evidence; retain the migration artifact.

No migration step may require deleting a source row to validate success; unmappable rows stay `legacy_only`/`blocked` with the adapter enabled.

## 7. Feature flags, deprecation, and removal criteria

One global rollout mode + project/endpoint overrides (avoid many independent booleans):

```text
PI_MODEL_MANAGEMENT_MODE=legacy_compat   # default on existing installs
  legacy_compat | shadow | pi_primary | deprecated_adapter | retired
```

Per-project explicit `agentic_engine` still overrides per the existing precedence contract. Mode visible in safe admin diagnostics and included in route/migration evidence.

**Promotion criteria:**

- `shadow`: deterministic catalog/mapping parity, credential-status parity, no duplicate canonical identity, no secret-flow violation, no new gate drift.
- `pi_primary`: successful canary on contract/faux providers; both engine suites green; embedding invariant proof; Petals isolation proof; audio unavailable/capability proofs; rollback artifact exists.
- `deprecated_adapter`: all new writes use canonical Pi management; compatibility GET/read paths preserve existing clients; deprecation headers/diagnostics; report of unmigrated/blocked rows.
- `retired`: zero active runtime reads treating LLM Server as canonical; zero unmapped rows except owner-accepted exceptions; all supported credentials resolvable or explicitly blocked; no data/secret-loss report; three consecutive deterministic full-suite runs with no new migration failures; one isolated testing-branch Compose run; one owner-authorized VPS staging proof when marked required; security benchmark green; docs/manifests green; tested rollback command. **Physical deletion is not part of the first retired state.**

**Deprecation behavior:** stable deprecation response/header + safe diagnostic reason on legacy CRUD/runtime compatibility paths; read compatibility preserved for the retention window; writes either invoke canonical management or fail closed with a migration-required response (no second source of truth). Local lifecycle and donor APIs that remain required transport infrastructure are **not** deprecated — only the model-management ownership semantics.

## 8. Wave plan with exact verification (maps to the run's manifest waves)

Every wave: goal, primary manifest wave, files it touches, exact verification commands (all verified to exist/collect in this tree), acceptance. Implementation tasks are generated from this plan at owner approval; work orders name dependencies, changed-path ownership, tests, docs, rollback, gates per task.

### Wave 0 — foundation (planning; this draft) · manifest wave `foundation`

**Acceptance:** three independent drafts reconciled into one frozen MECE master plan; owner approval gate recorded; no implementation task released before it.

**Commands (already run for this draft):**

```bash
npm view @earendil-works/pi-agent-core version        # -> 0.84.2 (2026-08-22)
npm view @earendil-works/pi-ai version                # -> 0.84.2
python3 scripts/pi_migration_inventory.py --json      # 1 allowlisted permanent site; ratchet 0
compass-forge gate before --task ISTARA-PI-MODEL-MIGRATION-20260822-REPLAN-A-r1 --summary  # fail, 30 inherited, 0 new
uv run --project backend --with pytest --with pytest-asyncio python -m pytest --collect-only -q \
  tests/pi_migration/test_count_to_zero.py tests/test_llm_servers.py tests/test_pi_runtime_endpoints.py \
  tests/test_settings_agentic_pi_endpoints.py tests/petals_bridge/test_petals_bridge.py tests/test_transcription.py
# -> 62 tests collected
```

### Wave 1 — Pi canonical catalog, provider auth, secret custody · `pi-catalog-secrets`

**Goal:** Pi becomes the canonical catalog/secret owner; unify provider/endpoint/model config under the Pi plane; validate encryption against standalone Pi; keep `LLMServer` rows intact. Includes the dependency update.

**Design outputs:** canonical catalog service layered on `PiModelManager` (identity graph, endpoint capabilities, auth hints, secret handles); secret custody migration (Fernet `api_key` → Pi Keychain/env abstraction with deterministic secret names, non-production readback checks, redaction audit, 60s TTL cache unchanged); data/secret migration snapshot (row-level lineage, encrypted backups, checksum manifests, reverse script); `pi-runtime` + `labs/pi-replacement` pinned to the latest verified upstream (re-verify before change; record registry output, lockfile resolution, protocol-v2 compatibility statement).

**Verification:**

```bash
npm view @earendil-works/pi-agent-core version && npm view @earendil-works/pi-ai version
cd pi-runtime && npm ci && npm test && cd ..          # worker deps prerequisite; protocol tests green
npm --prefix labs/pi-replacement ci && npm --prefix labs/pi-replacement run validate
uv run --project backend python -m pytest tests/test_pi_runtime_endpoints.py tests/test_settings_agentic_pi_endpoints.py \
  tests/pi_production/test_endpoint_secrets.py tests/test_field_encryption.py tests/test_llm_fallback_config.py \
  tests/test_model_provider_contract.py tests/pi_production/test_w8_embeddings_gateway.py \
  tests/pi_migration/test_count_to_zero.py -q
python scripts/security_benchmark.py --fail-on-threshold
```

**Acceptance:** zero secret leakage in logs/config snapshots; exact source fields preserved through alias maps (field-level diff tests); rollback restores runtime settings + encrypted bindings; `LLMServer` rows untouched; duplicate model identity impossible (uniqueness + collision tests); latest verified package provenance recorded; lockfiles reproducible.

### Wave 2 — reversible compatibility migration + dual-engine routing · `compat-routing`

**Goal:** Pi becomes the canonical resolver for BOTH engines; legacy config migrates without silent loss; bounded deprecated adapter; rollback + migration observability; fail-closed removal criteria defined.

**Design outputs:** migration/projection layer (legacy readers resolve through Pi catalog views; legacy writes route through canonical write APIs with provenance tags); rollback observability (per-row lineage, migration audit log, switchboard `PI_MODEL_MANAGEMENT_MODE` + `agentic_engine_default` + per-project `agentic_engine` + `llmserver_compat_mode`); engine selection preserved at all dispatcher verbs; `PI_ENGINE_VALUES` stays canonical; new `tests/pi_migration/test_model_management_migration.py` + `test_model_management_rollback.py` obligations.

**Verification:**

```bash
uv run --project backend python -m pytest tests/test_llm_servers.py tests/test_settings_agentic_pi_endpoints.py \
  tests/test_pi_runtime_endpoints.py tests/pi_production/test_w1_agentic_contract.py \
  tests/pi_production/test_w1_dispatcher_authority.py tests/pi_production/test_w1_usage_ledger.py \
  tests/pi_production/test_w1_realpath_accounting.py tests/pi_production/test_w4_a2a_handlers.py \
  tests/pi_production/test_w6_engine_selection.py tests/pi_benchmark/test_b1_contract.py \
  tests/compute_cases/routing.py tests/compute_cases/status_contracts.py -q
uv run --project backend python -m pytest tests/pi_migration/test_model_management_migration.py \
  tests/pi_migration/test_model_management_rollback.py tests/pi_migration/test_count_to_zero.py -q
python3 scripts/pi_migration_inventory.py --json
python scripts/security_benchmark.py --fail-on-threshold
```

**Acceptance:** dry-run-then-execute migration is idempotent (second run no-op); canonical mapping/status stable; source data recoverable; secret reference resolves without plaintext export; per-dispatch exactly one usage/route row; engine/provider failure never switches engines; deprecated clients get documented adapter/deprecation behavior and create no new identity; unsupported/malformed rows remain `legacy_only`/`blocked` with reason; rollback drill performed and recorded.

### Wave 3 — embedding invariant, chat controls, agentic selector UX · `embeddings-controls`

**Goal:** one coherent vector space with explicit embedding identity; chat endpoint changes never silently change embeddings; expose temperature/thinking/effort controls; clear Pi-vs-Istara engine buttons with evidence-backed comparative summaries.

**Design outputs:** embedding policy keyed by canonical model identity; dimension/dtype/endpoint invariant in gateway + benchmark surface (drift requires explicit compat flag + owner sign-off); chat control propagation (`temperature`, `max_tokens`, `thinking_level`, `timeout_ms`, `max_retries` via the canonical bind params); selector UX rework in `frontend/src/lib/modelCatalog.ts` + `ProjectSettingsView.tsx` with honest comparative summaries sourced from benchmark evidence (research-spine grounded; no fabricated claims); accessibility contract.

**Verification:**

```bash
uv run --project backend python -m pytest tests/pi_production/test_w8_embeddings_gateway.py \
  tests/pi_production/test_w8_ux_parity.py tests/pi_production/test_w6_engine_selection.py \
  tests/pi_production/test_w1_agentic_contract.py tests/test_pi_runtime_endpoints.py \
  tests/test_rag_resilience.py tests/test_research_validity_contract.py -q
npm --prefix frontend ci && npm --prefix frontend run test:unit -- --run
npm --prefix frontend run lint && npm --prefix frontend run build
node --test tests/simulation/scenarios/79-engine-selector.mjs
```

**Acceptance:** embedding dimension/model mapping identical before/after each migration step (invariant probe green both engines); no duplicate embedding identity accepted; chat endpoint change leaves embedding profile unchanged and identity visible in safe metadata; selector precedence/validation stable; comparative summaries cite evidence provenance and stay provisional (never presented as research evidence).

### Wave 4 — Petals preservation + unified audio-model settings · `petals-audio`

**Goal:** preserve donor opt-in, identity pinning, security boundaries, compute donation/scheduling, same-model donor isolation, fail-closed unavailable; add governed audio-model settings (local Whisper, compatible remote Whisper, supported diarized providers) without inventing unsupported local Pi audio behavior.

**Design outputs:** Petals — no bridge changes in early waves; explicit authorization/consent tests; compute scheduling explicit and auditable; donor rows never Pi-catalog capacity entries. Audio — canonical `AudioModelProfile` contract; interview + microphone flows; capabilities + secrets + fallbacks; local-only/optional-provider behavior explicit; no secrets in raw config payloads.

**Verification:**

```bash
uv run --project backend python -m pytest tests/petals_bridge/test_petals_bridge.py \
  tests/pi_production/test_same_model_donor_isolation.py tests/pi_production/test_research_spine_donor_routing.py \
  tests/test_compute_registry_hardening.py tests/test_project_scope_contracts.py \
  tests/compute_cases/config.py tests/compute_cases/retries.py -q
uv run --project backend python -m pytest tests/test_transcription.py tests/test_files.py \
  tests/test_integration_interview.py tests/pi_production/test_w3_research_spine.py \
  tests/test_research_validity_contract.py -q
python scripts/security_benchmark.py --fail-on-threshold
```

**Acceptance:** relay/browser donor with consent/health/project authorization is pinned to the donor, records route evidence, deterministic result; any missing admission condition → typed unavailable, never paid fallback; donor never selected as ordinary Pi capacity; local Whisper / remote Whisper / diarized / unsupported / missing-credential / low-ICR / ffmpeg-unavailable inputs behave explicitly, bounded, project-scoped, correctly marked `needs_review`/unavailable; raw source spans + provenance preserved; no transcript/tag reportable before gates. No live audio provider or model load required — mocked HTTP + local seams.

### Wave 5 — docs, testing-branch Docker QA, isolated VPS acceptance · `qa-docs-vps`

**Goal:** final integration: living feature docs + manifests regenerated; deterministic Compose QA coverage for every accepted feature without weakening public QA isolation; security benchmark + broad focused suites; then VPS acceptance per the `vps` skill (strict single-workload profile), and cleanup of only initiative-owned disposable artifacts.

**Design outputs:**

- Docs: `docs/features/content/settings/llm-servers/*`, `chat/model-controls/*`, `chat/audio/*`, `interviews/transcription/*`, `settings/compute-donation/*`, `compute/pool/*` (+ `agents/registry`, `agents/a2a` if engine metadata changes); regenerate site/manifests; architecture docs (`agentic_core.md`, research-validity contract only if spine-visible seams change, self-improvement contract only if self-improvement paths change); repo docs (`README.md`, `README.pt-BR.md`, `DOCUMENTATION.md`, `TESTING.md`, `CHANGE_CHECKLIST.md`, `SYSTEM_CHANGE_MATRIX.md`); `testing/feature_coverage.yml` for every behavior-changing path.
- QA: extend `qa/runtime_capabilities.json` obligations + `docker-compose.qa.yml` profiles (deterministic contract lanes cover every accepted feature); `scripts/istara-qa.sh render` (no live model); reset/audit lanes.
- VPS acceptance (owner-authorized; the `vps` skill contract verbatim): `python3 ~/.pi/agent/skills/vps/scripts/vpsctl.py preflight` → `vpsctl.py inventory` (read-only) → create Dokploy Docker Compose service from the strict single-workload profile (one service, project-local bridge network `internal: true`, one published port, no proxy/external network/Docker socket mount/host ns/privileged) → preview rendered Compose (stop if it injects shared/proxy network) → deploy preserving prior deployment identity + rollback target → `vpsctl.py verify-isolation` + `verify-exposure` (approved port set; firewall + `DOCKER-USER` evidence; IPv4/IPv6) → `vpsctl.py audit-anchor`. **No firewall/port changes without owner approval.** Cleanup: remove only initiative-owned disposable artifacts (unique VPS project/stack paths); never touch unrelated workloads.

**Verification (public/testing-branch deterministic part):**

```bash
python scripts/feature_docs.py --seed-missing --generate-site --check
uv run --project backend python -m pytest tests/test_feature_docs.py tests/test_feature_obligations.py \
  tests/test_qa_stack_contract.py tests/test_qa_reset_seed.py tests/test_qa_artifacts.py \
  tests/test_synthetic_provisional_boundary.py tests/test_provider_contracts.py -q
docker compose -f docker-compose.yml config --quiet
for p in contract synthetic reset audit live ui; do \
  docker compose -f docker-compose.qa.yml --profile $p config --quiet; done
./scripts/istara-qa.sh render
python scripts/check_feature_obligations.py --base origin/testing --head HEAD
python scripts/check_integrity.py && python scripts/check_ci_governance.py && python scripts/check_test_harness.py
python scripts/check_public_tree_clean.py --base origin/testing --head HEAD
python scripts/security_benchmark.py --fail-on-threshold
compass-forge gate before --summary && compass-forge gate after --summary   # 0 NEW failures attributable
```

**VPS commands (owner-authorized, all through the vps skill's `vpsctl.py`, never raw SSH):**

```bash
VPSCTL=~/.pi/agent/skills/vps/scripts/vpsctl.py   # vpsctl.py is NOT in this repo (C7)
python3 $VPSCTL preflight
python3 $VPSCTL inventory
python3 $VPSCTL deploy --compose <strict-template> --project istara-pi-model-migration-<run>   # one target
python3 $VPSCTL verify-isolation --port <approved-port>
python3 $VPSCTL verify-exposure --ports <approved-port-set>
python3 $VPSCTL audit-anchor
# cleanup of initiative-owned disposable artifacts only, after owner acceptance
```

**Acceptance:** feature-doc parity + generated manifests/site green; every accepted feature has a deterministic contract lane; security benchmark pass; 0 new gate failures attributable to the wave; VPS: strict-profile proof (one internal network, one endpoint, no default route, no host/other-container reachability, exactly the allowed published port), firewall/DOCKER-USER evidence agrees with the approved port list, audit chain anchored, rollback available until owner accepts, only initiative-owned artifacts removed, `main` untouched.

## 9. Test ownership and coverage matrix

Extend existing tests; never create an unowned parallel suite. Gate rules `architecture_drift` and `test_ownership` are load-bearing: every new canonical model-management file must be listed in `testing/feature_coverage.yml` or a reviewed mechanical exception; every behavior-changing file needs an owning test/doc obligation.

| Surface | Existing anchors | New/changed obligations |
|---|---|---|
| Pi package/protocol | `pi-runtime/test/*.test.mjs`, `pi-runtime/PROTOCOL.md`, `tests/pi_production/test_engine_http_provider.py`, `test_runtime_hardening.py`, `test_protocol_version_per_frame.py` | exact version/lockfile provenance; no dependency drift; protocol v2 compatibility after upgrade |
| Canonical provider catalog | `test_model_provider_contract.py`, `test_pi_runtime_endpoints.py`, `test_endpoint_secrets.py` | identity tuple, aliases, capabilities, credential custody, duplicate handling |
| LLM Server compatibility | `test_llm_servers.py`, `test_settings_agentic_pi_endpoints.py`, simulation scenario 36 | idempotent mapping, deprecated adapter, blocked rows, rollback |
| Engine routing | `test_w1_agentic_contract.py`, `test_w1_dispatcher_authority.py`, `test_w1_usage_ledger.py`, `test_w6_engine_selection.py`, `test_w4_a2a_handlers.py` | both engines through canonical target; precedence; no fallback; one-row accounting |
| Count-to-zero | `scripts/pi_migration_inventory.py`, `test_count_to_zero.py`, `legacy_allowlist.yaml` | product remains 0; only documented permanent infrastructure entries |
| Embeddings | `test_w8_embeddings_gateway.py`, `test_w8_ux_parity.py`, `test_rag_resilience.py` | profile identity, dimension/dtype mismatch refusal, no cache writes on mismatch |
| Petals/compute | `tests/petals_bridge/test_petals_bridge.py`, donor isolation, `tests/compute_cases/*` | consent, project scope, exact node identity, typed 503, no paid fallback |
| Audio/research | `test_transcription.py`, `test_files.py`, `test_integration_interview.py`, research-spine tests | profile capability, diarization, ICR/review, raw evidence units/provenance |
| Frontend/UI | `frontend/src/lib/modelProviders.test.ts`, `modelCatalog.test.ts`, engine selector simulations | no duplicate options, explicit engine/model/endpoint distinction, accessibility |
| QA/docs | `test_feature_docs.py`, `test_feature_obligations.py`, QA stack/provisional/obligation tests | changed-path ownership, generated docs parity, provisional-only QA |
| Security | `test_security_benchmark.py`, `security/control_matrix.json` | triggered benchmark + control/evidence updates if controls change |

## 10. Documentation and manifest obligations

Update living docs in the same implementation initiative (dated historical plans stay immutable; write successor records when facts change):

- `docs/architecture/agentic_core.md` (canonical identity/transport boundary, legacy adapter vs legacy infrastructure, route evidence); `docs/architecture/research-validity-contract.md` (only if spine-visible seams change); `docs/architecture/self-improvement-governance-contract.md` (only if self-improvement paths change).
- Feature pages at minimum: `settings.llm-servers`, `chat.model-controls`, `chat.audio`, `interviews.transcription`, `settings.compute-donation`, `compute.pool` (+ `agents/registry`, `agents/a2a` if engine metadata changes) — plus any new provider/credential/audio pages the feature inventory discovers.
- Repo docs: `README.md`, `README.pt-BR.md`, `DOCUMENTATION.md`, `TESTING.md`, `CHANGE_CHECKLIST.md`, `SYSTEM_CHANGE_MATRIX.md`, `testing/TESTING_STRATEGY.md` where contracts change.
- `testing/feature_coverage.yml` + QA capability/obligation files for all changed paths.
- Security: `security/control_matrix.json`, `security/SECURITY_BENCHMARK.md`, `tests/test_security_benchmark.py` only when a control/evidence path/standard version/trigger changes; the benchmark itself is mandatory on touched surfaces.
- Regenerate with `python scripts/feature_docs.py --seed-missing --generate-site --check`; attach output as evidence. Generated site files are outputs of that command — never hand-edit generated integration files or silently modify external repos.
- No private VPS host details, keys, or endpoint fingerprints in public docs or QA artifacts.

## 11. Security benchmark and review checklist

Mandatory on any auth/provider/secret/agentic/Petals/audio change:

```bash
python scripts/security_benchmark.py --fail-on-threshold
```

Record scorecard as CF command evidence; update `security/control_matrix.json` + `security/SECURITY_BENCHMARK.md` + `tests/test_security_benchmark.py` when a security control, evidence path, standard version, or trigger pattern changes. The security reviewer must cover: credential source precedence/rotation; encryption context/version compatibility for migrated `api_key` values; SSRF/URL normalization + loopback/HTTPS policy for custom endpoints; OAuth redirect/token custody; admin/project authorization on catalog/credential/migration/Petals-consent/audio routes; enumeration + safe redaction in UI/API/telemetry/logs; no secrets in migration exports, Compose interpolation, QA artifacts, or CF evidence; worker private-pipe binding, protocol limits, retry/cost accounting, malformed-frame behavior; explicit engine selection never bypassing Research Spine route evidence; donor consent/project scope/same-model isolation/typed 503; audio upload size/type/scanner/temp-file cleanup, remote provider credentials, diarization privacy; no public VPS/multivac references, no firewall changes, no unrelated workload cleanup. Inherited gate failures are never suppressed silently: record baseline vs post-change comparison and either fix new failures or create an explicit, expiring, justified suppression under project policy.

## 12. Risks and mitigations

| Risk | Mitigation / detection | Rollback |
|---|---|---|
| Package update changes Pi protocol behavior | Pin exact versions; run worker/backend contract suites; compare protocol-v2 frames; update only with evidence | restore prior package/lockfiles + worker checkout |
| Duplicate model IDs / endpoint aliases | provider-qualified IDs, stable endpoint IDs, uniqueness constraints + collision tests | restore canonical mapping; source rows intact |
| Lost/invalid API key during migration | in-memory decrypt/re-encrypt, credential status matrix, no plaintext export, key-resolution tests | keep source encrypted field + legacy compatibility reference |
| Resolver accidentally uses donor capacity | static import boundary, donor isolation tests, explicit transport class | disable Pi-primary mode; keep legacy/donor paths |
| Engine silently falls back on failure | explicit engine target + typed error tests, one-row accounting | revert rollout mode/project engine to legacy explicitly |
| Embedding drift corrupts retrieval | persist profile/model/dimension/dtype, startup probe, block mismatch before cache/write | restore previous profile + vectors; reindex only as versioned migration |
| Petals donor leaks project data / paid fallback hides failure | bridge admission, project scope, route evidence, typed 503/no fallback | disable bridge/Pi Petals mode; donor registry unchanged |
| Audio profile exposes unsupported/private provider behavior | capability contract, local/mock tests, secret custody, no implicit fallback, `needs_review` | return unavailable; retain existing local path |
| Compatibility API becomes second source of truth | deprecated adapter writes canonical only; source→canonical mapping + count tests | re-enable read adapter; never delete rows |
| QA false confidence | contract stub labeled non-quality, synthetic provisional guard, live lane owner-gated | stop QA project; retain evidence; never promote synthetic artifacts |
| VPS isolation regression / exposure | strict single-workload profile, preview-reject injected networking, verify-isolation/exposure, firewall + DOCKER-USER evidence, audit-anchor | preserve prior deployment identity + rollback target until owner accepts |
| VPS credential/exposure leak | secrets only in Dokploy secret UI, `vpsctl.py` audit chain, no secrets in args/history/chat | revoke + rotate; audit-verify chain |
| Docs/generated drift | feature obligation classifier + feature-doc regeneration in same task | block acceptance until docs/manifests regenerated |
| Inherited baseline gate debt masks migration findings | separate inherited vs new in every gate/security narrative; `gate before/after` diff | — |

## 13. Definition of Ready / Done

### Ready for implementation

- The three drafts are reconciled into one MECE master plan and **owner-approved at the explicit plan gate**.
- Exact canonical identity, credential, migration-state, engine-transport, embedding-profile, audio-profile, and Petals boundaries are accepted.
- CF work orders name dependencies, changed-path ownership, tests, docs, rollback, and gates for each wave.
- Latest Pi release is re-checked passively at dependency-update execution time; no live LLM/model load required.
- Baseline gate output and known inherited failures are attached; no new implementation begins while the plan gate is pending.

### Done for the initiative

- All required waves have green task command evidence and post-change gate evidence, or an explicit owner-approved residual risk.
- Canonical model/endpoint/credential behavior proven without duplicate identity semantics or secret leakage.
- Both engines remain explicitly selectable and independently fail closed, with one usage/route record per dispatch.
- LLM Server migration idempotent, reversible, observed, deprecated; no row deleted without the separate removal gate.
- Embedding profile, Petals bridge, audio/transcription, Research Spine, UI, QA/Compose, security benchmark, docs/manifests, and test ownership obligations complete.
- VPS acceptance (if authorized/required): strict-profile isolation/exposure proof, firewall evidence, audit-anchor, cleanup of only initiative-owned artifacts; otherwise explicitly marked blocked/advisory and public QA stays green.
- Lifecycle status/ledger, CF evidence, findings register, and final summary accurately describe the result. No implementation stage claims completion from a plan-only artifact.

## 14. Coverage matrix (requirement → this draft)

| Requirement | Where | Evidence anchor |
|---|---|---|
| Latest verified Pi dependency | §§2.4, 8 Wave 1, C4 | `npm view` 0.84.2 (2026-08-22), `pi-runtime/package.json`, `labs/pi-replacement/package.json`, `pi-runtime/PROTOCOL.md` |
| Canonical model/provider/endpoint ownership | §5.1–5.3 | `endpoints.py`, `model_manager.py`, `config.py`, settings/LLM routes |
| Exact data/secret migration + rollback | §6 | `LLMServer`, `field_encryption.py`, migration state machine, rollback playbook |
| Both engines, no duplicate semantics | §§5.2, 5.4, Wave 2 | dispatcher, legacy executor, engine tests |
| Reversible LLM Server retirement | §§6–7, Wave 2 | state machine, deprecation/removal gates |
| Embedding/vector-space invariant | §5.5, Wave 3 | `embeddings_gateway.py`, research-validity contract |
| Petals donor bridge | §5.6, Wave 4 | `petals_bridge.py`, donor isolation/compute contracts |
| Audio/Whisper/diarization | §5.7, Wave 4 | transcription/file/chat routes, evidence-unit persistence |
| UI selector/model controls | §2.2, Wave 3 | modelCatalog/modelProviders, engine selector sims |
| Testing-branch Docker QA | §8 Wave 5 | `docker-compose.qa.yml`, `testing/feature_coverage.yml`, QA contracts |
| VPS deployment per vps skill | §8 Wave 5, C1/C5 | vps skill contract, vpsctl.py preflight/inventory/verify-isolation/verify-exposure/audit-anchor |
| Security benchmark | §11, wave commands | AGENTS.md, benchmark/control matrix contract |
| Research Spine | §§2.3, 5.7, Waves 3–5 | `docs/architecture/research-validity-contract.md` |
| Feature-flag/deprecation/removal | §7 | mode registry, promotion/retirement criteria |
| Testing branch only; stop at owner gate | §§1, 13 | manifest, lifecycle, cast config |

Bounded control-plane references (process/design comparators only — never cut into `main`, never import their runtime): Compass Forge Rust branch `08d3233` (`build-stream/compass-forge-rust-runtime`), Skills `e45211e` (`build-stream/conductor-dspy-gepa`), Skills `3d4277b` (`build-stream/wave3-l35-remediation`).

## 15. Handoff note

This is an independent draft. The next steps: Architect B and Architect C produce their independent drafts; the synthesis phase merges all three into one MECE master plan (with the coverage matrix showing which draft insight each section incorporates); the plan gate stops at owner approval; implementation tasks are then generated from the approved plan. No source implementation, lifecycle-file edit beyond this plan artifact, Docker start, live provider call, model load, VPS access, merge, push, or PR is authorized from this stage.
