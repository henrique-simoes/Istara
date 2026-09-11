# Plan C — Foundation: upstream Pi contract and migration boundary

> Independent draft by architect C (ISTARA-PI-MODEL-MIGRATION-20260818-PLAN-C).
> This is one of three independent S1 drafts (A/B/C) that the consensus phase will
> synthesize into the master plan. It is a *planning* artifact — no code is changed.

## 0) How this plan is organized (and how it differs from the sibling drafts)

This draft is contract-first and inventory-driven. Instead of narrating a wish-list,
it opens with the **actual migration boundary** as I verified it in this worktree
(section 2), then pins the **invariants that must not move** (section 3), then defines
the **reversible retirement spine** with explicit state transitions and rollback
(section 4), then the **wave plan with exact verification commands** (section 5),
the **task breakdown mapped to the CF task graph** (section 6), and finally risks,
documentation obligations, security benchmark coverage, and multivac hygiene
(sections 7–10).

Buildability comes from the fact that every verification command in section 5 was
checked against this tree (files exist, tests collect, the security benchmark passes
at HEAD, the migration ratchet is at its W9 end-state of 0 product sites).

## 1) Executive summary

Istara has two model-management identity planes today:

1. **Legacy `LLMServer` rows** (`backend/app/models/llm_server.py`, table
   `llm_servers`) persisted in SQLite, CRUD at `backend/app/api/routes/llm_servers.py`,
   live-registered into the `ComputeRegistry` via `llm_router.py` (a backward-compat
   wrapper), discovered by `network_discovery.py`, and health-probed by `ollama.py`.
2. **Pi model management** (`backend/app/core/pi_runtime/`) — `PiEndpointResolver`
   (Keychain-backed secrets, TTL cache), `PiModelManager` (a three-source catalog:
   static settings endpoints + built-in `pi-deepseek-default`, read-only projection of
   `LLMServer` rows as `pi-llm-<id>`, and local Ollama/LM Studio serving), and
   `PiExecutionService` (the governed seams: chat/delegation/channel/autoresearch/
   completion/react/structured/ensemble).

The `AgenticDispatcher` (`backend/app/core/agentic/dispatcher.py`) is already the only
product-code path: engine resolution is per-call > header > project setting >
`settings.agentic_engine_default` (default `"legacy"`). The count-to-zero ratchet
(`tests/pi_migration/test_count_to_zero.py`) is already at 0 product sites — product
code no longer calls the legacy plane directly; the allowlist holds permanent entries
only. This migration therefore is **not** a call-site migration; it is a
**model-management authority migration**: make Pi the canonical catalog/secret/routing
owner, migrate legacy configuration and data with zero silent loss, keep both engines
explicitly selectable, and retire the `LLMServer` row plane only after observable
removal criteria are met — reversibly.

The plan retires `LLMServer` through six waves (W1 foundation → W6 QA/multivac), with
every wave reversible to the previous state via a documented rollback switch
(`agentic_engine_default=legacy`, `llmserver_compat_mode`, key/endpoint snapshot
restores). No wave deletes legacy data; data deletion is gated on migration proof,
vector-space invariant green, and Petals security controls intact.

## 2) Verified migration boundary (this worktree, HEAD 15260a78+)

I independently inspected the following surfaces. This is the boundary the plan must
protect.

### 2.1 Legacy LLM Server plane (to be retired reversibly)

| Surface | Verified location | Role |
|---|---|---|
| Model | `backend/app/models/llm_server.py` — `LLMServer`, table `llm_servers` | Persisted endpoint rows: name, provider_type, host, encrypted api_key, is_local, is_healthy, is_relay, priority, last_health_check, last_latency_ms, capabilities (JSON) |
| CRUD + health + discover | `backend/app/api/routes/llm_servers.py` | `GET/POST/PATCH/DELETE /llm-servers`, `/health-check`, `/discover`; admin-gated; already calls `_refresh_pi_catalog_projection()` after mutations (W8 UX parity) |
| Live registry | `backend/app/core/llm_router.py` — backward-compat wrapper over `ComputeRegistry`; `LLMServerEntry` | `llm_router.register_server/unregister_server/list_servers`; health probe delegation |
| Compute registry | `backend/app/core/compute_registry*.py` (facade + core/helpers/lifecycle/routing/invocation) | Donor-schedulable node registry; must never contain Pi endpoints |
| Startup + discovery | `backend/app/core/ollama.py` (`load_persisted_servers_async`), `backend/app/core/network_discovery.py` (`discover_and_register`) | Re-hydrates rows into the live router; discovers and persists rows; relay rows flagged `is_relay` |
| Encryption | `backend/app/core/field_encryption.py` (Fernet, `DATA_ENCRYPTION_KEY`) | `encrypt_field/decrypt_field` for `api_key` and other secrets |
| Endpoint safety | `backend/app/core/endpoint_security.py` (`normalized_service_url`, `EndpointPolicy`, `redacted_endpoint_label`) | URL normalization, plaintext/credential rejection, redaction |
| Consumers (readers/writers) | `backend/app/core/compute_node*.py`, `backend/app/core/compute_registry*.py`, `backend/app/core/autoresearch_runners/model_temp.py`, `backend/app/api/routes/settings.py`, `backend/app/api/routes/admin.py`, `backend/app/services/research_validity_service.py` | Read catalog/models for UI, benchmarks, and research-validity surfaces |
| Alembic | `backend/alembic/versions/002_distributed_platform.py` (drops `llm_servers` on downgrade only; table created in 001) | Schema lifecycle |

### 2.2 Pi model-management plane (the target authority)

| Surface | Verified location | Role |
|---|---|---|
| Endpoint model + resolver | `backend/app/core/pi_runtime/endpoints.py` — `PiApiEndpoint` (config), `PiEndpointResolver`, `ResolvedPiEndpoint` | Keychain secret resolution with 60s TTL cache; `DEFAULT_ENDPOINT_ID="pi-deepseek-default"`; fail-closed typed errors |
| Catalog | `backend/app/core/pi_runtime/model_manager.py` — `PiModelManager` | Three sources: settings endpoints, read-only `LLMServer` projection (`pi-llm-<id>`, never relay), local Ollama/LM Studio; `resolve`, `resolve_distinct`, `resolve_embed`, `catalog`; `reset_live_db_projections` weakref invalidation |
| Engine facade | `backend/app/core/pi_runtime/engine.py` — `PiExecutionService` | Governed seams: `run_chat_turn`, `run_delegation`, `run_channel_turn`, `run_autoresearch_turn`, `run_completion`, `run_react`, `run_structured`, `run_ensemble`; telemetry; tool-authority rejection |
| Worker | `backend/app/core/pi_runtime/supervisor.py` + `pi-runtime/src/worker.mjs` | One Node child per process, versioned NDJSON protocol (`PROTOCOL_VERSION=2` on both sides), secrets only in `provider.bind` frames |
| Embeddings | `backend/app/core/pi_runtime/embeddings_gateway.py` — `EmbeddingsGateway`, `assert_vector_space_invariant` | Pi identity-pinned embed path (native Ollama `/api/embed` or `/v1/embeddings`); vector-space invariant probes both engines with the same model |
| Provisioning | `backend/app/core/pi_runtime/model_manager_provisioning.py` | Local `kind=local` ensure-model via existing Ollama/LM Studio helpers, never donated compute |
| Seams | `backend/app/core/pi_runtime/seams.py` | Governance clause + fail-closed glue for A2A/channel/autoresearch |
| Dispatcher | `backend/app/core/agentic/dispatcher.py` + `legacy.py` + `usage_ledger.py` | Engine resolution (per-call > header > project > default), 5+ verbs, one usage-ledger row per dispatch, no silent fallback |
| Pi engine values | `backend/app/core/pi_replacement.py` — `PI_ENGINE_VALUES={"pi","pi-candidate","pi-replacement","deepseek-pi"}` | Canonical Pi selection vocabulary |
| Frontend | `frontend/src/lib/modelCatalog.ts` (`mergeModelCatalogs`), `frontend/src/components/settings/ProjectSettingsView.tsx` (per-project engine selector), `frontend/src/components/common/SettingsView.tsx` | Merged catalog + engine indicator UI |

### 2.3 Coupled governed surfaces

- **Embeddings / vector space**: `backend/app/core/embeddings.py`,
  `embedding_validation.py`, `embedding_cache.py`; invariant anchored on
  `default_embed_model()` (mirrors `app.core.embeddings._embed_model_name`).
- **Petals donor bridge**: `backend/app/core/petals_bridge.py` — consented
  relay/browser donors projected as `pi-petals-<node_id>` catalog entries, fail-closed
  `PetalsUnavailable` (503), route stamp `_istara_route.route_kind="petals_bridge"`,
  `settings.petals_bridge_enabled`; tests in `tests/petals_bridge/` and
  `tests/pi_production/test_same_model_donor_isolation.py`.
- **Audio / transcription**: `backend/app/core/transcription.py` (local Whisper +
  ICR consensus), `backend/app/api/routes/chat_voice.py` (dummy voice stub), interview
  transcription paths, `tests/test_transcription.py`. No unified audio-model settings
  contract exists yet.
- **UI contracts**: `frontend/src/lib/modelCatalog.ts`, model pickers, engine selector,
  `chat.model-controls` feature doc (documented), `settings.llm-servers` doc
  (documented), `chat.audio` + `interviews.transcription` docs (needs-verification).
- **QA**: `docker-compose.qa.yml` (profiles: contract/synthetic/reset/audit/live/ui,
  no fixed container_name, unique `istara-qa-<run-id>` project), `qa/`
  (`runtime_capabilities.json`, `scripts/*`, `Dockerfile`, `provider-stub.Dockerfile`),
  `scripts/istara-qa.sh`, `tests/test_qa_stack_contract.py`,
  `tests/test_provider_contracts.py`.
- **Research spine**: `docs/architecture/research-validity-contract.md` — any migrated
  surface that touches research data must preserve evidence-unit → coding →
  reliability → reconciliation → Done gates. `backend/app/core/research_validity.py`
  and `tests/test_research_validity_contract.py` cover it.

### 2.4 Version and ratchet facts (verified)

- `pi-runtime/package.json` pins `@earendil-works/pi-agent-core@0.83.0` and
  `@earendil-works/pi-ai@0.83.0`. Upstream latest (checked 2026-08-18) is **0.84.2**
  for both. The implementation must re-check upstream immediately before the change
  and record provenance.
- `tests/pi_migration/test_count_to_zero.py` — `EXPECTED_PRODUCT_SITES = 0`; allowlist
  holds permanent entries only; scanner is `scripts/pi_migration_inventory.py`.
- `gate before` at HEAD: status fail with 80 inherited baseline failures
  (`python_import_cycles`, `secret_flow`, `unexpected_large_files`), **0 new failures,
  0 actionable** — inherited baseline debt must be separated from migration findings
  in every evidence narrative.

## 3) Governing invariants (these never move)

1. **Pi is the canonical model-management authority.** Provider/model/endpoint/secret
   metadata resolves through `PiModelManager`/`PiEndpointResolver`. Legacy storage and
   selectors may read through compatibility views only.
2. **No duplicate model identity semantics.** Exactly one canonical identity tuple
   per logical model `{provider_key, model_key, runtime_tier}`. Legacy aliases live
   only in explicit, expiring compatibility maps; collision/split-brain detection
   fails closed with telemetry.
3. **Both engines stay explicit.** `pi` and `legacy` remain selectable and measurable
   at per-call, per-project, per-experiment, and per-header levels. No silent fallback
   from `pi` to `legacy` (dispatcher fail-closed both ways).
4. **Fail-closed everywhere.** Unresolved secret/routing/identity/capability is a
   typed error (`PiEndpointResolutionError`, `PetalsUnavailable`, `PiRuntimeTurnError`),
   never an implicit provider fallthrough.
5. **One vector space.** Both engines embed with the same model; changing a chat
   endpoint must never silently change embeddings; `assert_vector_space_invariant`
   stays green.
6. **Research spine intact.** No migrated path may create report evidence, weaken
   coding/reliability/reconciliation gates, or bypass human review.
7. **Reversibility is a design constraint.** Every wave has a documented rollback that
   restores user-facing behavior on the legacy path.
8. **Pi traffic never enters the donated-compute registry.** Same-model donor
   isolation stays proven (`tests/pi_production/test_same_model_donor_isolation.py`).
9. **No live model loading during agent work**; passive status/discovery only; one
   bounded target on owner-authorized live lanes.
10. **Disposable QA and multivac artifacts are cleaned** after verification; existing
    benchmark workloads are inventory-only.

## 4) Reversible retirement spine (state machine)

States (authoritative identity + routing):

- **S0 Legacy-authoritative**: `LLMServer` rows authoritative; Pi catalog adapters
  (projection) only. (≈ today.)
- **S1 Pi-authoritative catalog + secrets**: Pi owns provider/model/endpoint/secret
  resolution; legacy runtime still default route; compatibility views read Pi.
- **S2 Dual-engine execution**: per-call/project/experiment selection, both engines
  measurable, no silent fallback.
- **S3 Pi-preferred**: default route is Pi; legacy remains compatibility-only.
- **S3.5 Deprecation window**: explicit warnings + allowlist-driven compatibility;
  legacy CRUD surfaces display deprecation banners; no new legacy writes.
- **S4 Retirement complete**: `llmserver_compat_mode` off, read path removed, data
  archived (not deleted), after all removal criteria met.

**Transition rule**: every S_i → S_i+1 requires (a) wave acceptance commands green,
(b) `gate after` with 0 *new* failures attributable to the wave, (c) `review_verdict`
pass from the code-reviewer role, (d) owner approval at each major gate.

**Rollback rule**: S_i+1 → S_i is a documented switch, not a code revert:
`agentic_engine_default=legacy` (+ project overrides cleared), `llmserver_compat_mode`
re-enabled, compatibility catalog writes restored from the migration snapshot, secret
vault backups restored, and W-acceptance commands re-run to prove reversion. Rollback
does not require redeploy unless a data migration already ran; if it did, the reverse
migration script (section 5, W2/W3) is the rollback path.

**Removal criteria (before S4 data/CRUD removal) — all must hold with evidence:**

1. Zero direct legacy consumers outside the bounded compatibility adapter
   (`scripts/pi_migration_inventory.py` ratchet remains 0; allowlist audit clean).
2. Vector-space invariant tests green on both engines (W4 acceptance).
3. Petals bridge security controls unchanged or hardened (W5 acceptance).
4. Audio/transcription flows on canonical config (W6 acceptance).
5. UI no longer offers legacy-only model CRUD without deprecation notice (W6/7).
6. Rollback drill performed on a staging-equivalent flow at least once (W3/W6).
7. Security benchmark passes with the removal (`--fail-on-threshold`).

## 5) Wave plan with exact verification

Each wave lists: goal, primary CF task(s), the files it touches, exact verification
commands (all verified to exist/collect in this tree), and acceptance.

### W1 — Foundation: upstream Pi contract, boundary freeze, baseline

**Goal**: verify latest upstream Pi release, record provenance, freeze the boundary
inventory, capture gate baseline and inherited debt, and create the migration manifest
that all later waves read. No user-facing behavior changes.

**CF alignment**: CF-787 (deps), CF-802 (FR-004 inspect), CF-803 (FR-005 must-inspect),
and the W1 slice of CF-788.

**Design outputs**:
- `docs/build-stream/manifests/...` migration manifest extension: boundary file list
  (section 2), wave→task→verification mapping, deprecation flag registry, rollback
  playbook stub.
- Dependency pin recorded: re-run `npm view @earendil-works/pi-agent-core version` /
  `@earendil-works/pi-ai version`, confirm 0.84.2 or newer-latest-verified, and a
  compatibility statement (protocol v2, worker entry, structured-output contract) in
  the manifest.
- Baseline: `compass-forge gate before --summary` (inherited failures separated),
  security benchmark scorecard, feature-doc parity run.

**Environment prerequisite**: worker-backed Pi tests (e.g.
`tests/pi_production/test_w1_agentic_contract.py` supervised-worker cases) require
`pi-runtime/node_modules` (they fail on worker handshake timeout when it is absent —
verified in this worktree, where `pi-runtime/node_modules` is not installed). W1 must
record `cd pi-runtime && npm ci` as the standard environment step and confirm the
upgraded pin resolves before running worker-backed tests.

**Verification commands** (target per implementer; record as `command` evidence):
```bash
npm view @earendil-works/pi-agent-core version
npm view @earendil-works/pi-ai version
cd pi-runtime && npm ci && cd ..   # worker deps prerequisite
python -m pytest tests/pi_migration/test_count_to_zero.py -q            # ratchet stays 0
python -m pytest tests/pi_production/test_w1_agentic_contract.py -q      # engine contract
python -m pytest tests/test_llm_servers.py -q                            # legacy CRUD intact
python scripts/security_benchmark.py --fail-on-threshold                  # baseline scorecard
python scripts/feature_docs.py --seed-missing --generate-site --check     # docs parity
compass-forge gate before --task ISTARA-PI-MODEL-MIGRATION-20260818-W1 --summary
compass-forge gate after  --task ISTARA-PI-MODEL-MIGRATION-20260818-W1 --summary
```

**Acceptance**:
- Provenance + version + compatibility statement recorded in the manifest with
  evidence rows.
- Boundary inventory matches the tree (no unlisted legacy consumer introduced).
- Ratchet 0, security benchmark pass, feature-doc parity pass, 0 new gate failures.
- No code behavior change (planning wave).

### W2 — Pi canonical catalog, provider auth, and secret custody

**Goal**: make Pi the canonical catalog/secret owner. Unify provider/endpoint/model
config (settings `PI_API_ENDPOINTS`, Keychain, OAuth/API-key/custom/local) under the
Pi plane; validate encryption against standalone Pi; keep `LLMServer` rows intact.

**CF alignment**: CF-788 (canonical owner), CF-790 (retirement prep), CF-801 (FR-003).

**Design outputs**:
- Canonical catalog service layered on `PiModelManager`: identity graph, endpoint
  capabilities, auth hints, secret handles (no plaintext persistence).
- Secret custody migration: legacy `llm_servers.api_key` (Fernet) → Pi Keychain/env
  secret abstraction with deterministic secret names, non-production readback checks,
  redaction audit, TTL cache unchanged.
- Data/secret migration snapshot: row-level lineage, encrypted backups, checksum
  manifests, reverse script.

**Verification commands**:
```bash
python -m pytest tests/test_pi_runtime_endpoints.py -q
python -m pytest tests/test_settings_agentic_pi_endpoints.py -q
python -m pytest tests/pi_production/test_endpoint_secrets.py -q
python -m pytest tests/pi_production/test_w8_embeddings_gateway.py -q   # projection + invariant
python -m pytest tests/pi_migration/test_count_to_zero.py -q
python -m pytest tests/test_synthetic_provisional_boundary.py -q         # spine boundary
python scripts/security_benchmark.py --fail-on-threshold
```

**Acceptance**:
- Zero secret leakage in logs/config snapshots (redaction audit rows).
- Exact source fields preserved through migrated alias maps (field-level diff tests).
- Rollback restores runtime settings and encrypted secret bindings (W2 rollback test).
- `LLMServer` rows untouched (no data deletion in this wave).

### W3 — Reversible compatibility migration + dual-engine routing

**Goal**: Pi becomes the canonical resolver for BOTH engines; legacy config migrates/
projects without silent loss; bounded deprecated adapter where required; explicit
rollback + migration observability; fail-closed removal criteria defined.

**CF alignment**: CF-789 (dual engines), CF-790 (retirement), CF-794 (selector UX),
CF-804 (SC-001).

**Design outputs**:
- Migration/projection layer: legacy readers resolve through Pi catalog views;
  legacy writes route through canonical write APIs with provenance tags.
- Rollback observability: per-row lineage, migration audit log, switchboard
  (`agentic_engine_default`, per-project `agentic_engine`, `llmserver_compat_mode`).
- Engine selection preserved at all five dispatcher verbs; `PI_ENGINE_VALUES` stays
  canonical.

**Verification commands**:
```bash
python -m pytest tests/pi_production/test_w1_dispatcher_authority.py -q
python -m pytest tests/pi_production/test_w4_a2a_handlers.py -q
python -m pytest tests/pi_production/test_w6_engine_selection.py -q
python -m pytest tests/pi_benchmark/test_b1_contract.py -q               # both engines T0/T1
python -m pytest tests/compute_cases/routing.py -q
python -m pytest tests/compute_cases/status_contracts.py -q
python -m pytest tests/test_llm_servers.py -q                            # legacy CRUD still works
python scripts/pi_migration_inventory.py --json | python -m json.tool    # scanner: 0 product sites
```

**Acceptance**:
- Opt-in Pi calls are Pi-exclusive; legacy behavior unchanged when not selected.
- No silent fallback (fail-closed on invalid engine mode).
- Migration proof: no silent data loss (diff counts, checksums); rollback drill
  performed and recorded.
- Deprecation warnings on legacy-only surfaces with explicit removal criteria.

### W4 — Embedding invariant + chat controls + agentic selector UX

**Goal**: one coherent vector space with explicit embedding endpoint/model/dimension
identity; chat endpoint changes must never silently change embeddings; expose
temperature/thinking/effort; clear Pi-vs-Istara engine buttons with evidence-backed
comparative summaries.

**CF alignment**: CF-791 (embedding invariant), CF-794 (selector UX), CF-799 (FR-001),
CF-802 (FR-004).

**Design outputs**:
- Embedding policy keyed by canonical model identity; dimension/endpoint invariant in
  gateway + benchmark surface; drift requires explicit compat flag + owner sign-off.
- Chat controls propagate `temperature`, `max_tokens`, `thinking_level`,
  `timeout_ms`, `max_retries` via `_turn_bind_params` (already canonical).
- Selector UX: `frontend/src/lib/modelCatalog.ts` + `ProjectSettingsView.tsx`
  reworked with honest comparative summaries sourced from benchmark evidence
  (research-spine grounded, no fabricated claims).

**Verification commands**:
```bash
python -m pytest tests/pi_production/test_w8_embeddings_gateway.py -q
python -m pytest tests/pi_production/test_w8_ux_parity.py -q
python -m pytest tests/pi_production/test_w6_engine_selection.py -q
python -m pytest tests/compute_cases/api_routes.py -q
python -m pytest tests/document_corpus/shared-corpus.mjs -q               # note: mjs corpus runner
python -m pytest tests/test_qa_stack_contract.py -q
cd frontend && npx vitest run src/lib/modelCatalog.test.ts src/lib/modelProviders.test.ts
```

**Acceptance**:
- Embedding dimension/model mapping identical before/after each migration step
  (invariant probe green both engines).
- No duplicate embedding model identity accepted.
- UI comparative summaries cite evidence provenance (benchmark rows), not invented
  claims; accessibility contract checked.

### W5 — Petals donor bridge preservation + audio/transcription config

**Goal**: preserve donor opt-in, identity pinning, security boundaries, compute
donation/scheduling, same-model donor isolation, fail-closed unavailable behavior;
add governed audio-model settings (local Whisper, compatible remote Whisper,
supported diarized providers e.g. GPT-4 diarization) without inventing unsupported
local Pi audio behavior.

**CF alignment**: CF-792 (Petals), CF-793 (audio/Whisper/diarized), CF-800 (FR-002).

**Design outputs**:
- Petals: no bridge changes in early waves; explicit authorization/consent tests;
  compute scheduling explicit and auditable; donor rows never Pi-catalog entries
  (isolation invariant retained).
- Audio: unified transcription model config under canonical model management;
  interview + microphone flows; capabilities + secrets + fallbacks; local-only /
  optional-provider behavior explicit.

**Verification commands**:
```bash
python -m pytest tests/petals_bridge/test_petals_bridge.py -q
python -m pytest tests/pi_production/test_same_model_donor_isolation.py -q
python -m pytest tests/pi_production/test_w1_agentic_contract.py -q
python -m pytest tests/test_transcription.py -q
python -m pytest tests/compute_cases/config.py -q
python -m pytest tests/compute_cases/retries.py -q
python scripts/security_benchmark.py --fail-on-threshold
```

**Acceptance**:
- Donor trust boundary not widened; no credential materialization outside approved
  stores; fail-closed on unknown/unconsented/unhealthy donors (503 typed).
- Audio models follow canonical policy; non-audio paths unaffected; no secrets in raw
  config payload; unsupported local Pi audio behavior never invented.

### W6 — Docs, testing-branch Docker QA, multivac acceptance, cleanup

**Goal**: final integration — living feature docs + manifests regenerated, Compose QA
profiles exercise every accepted feature deterministically without weakening public QA
isolation, security benchmark + broad focused suites, then multivac read-only
inventory → isolated checkout/project → SSH-tunnel verification → cleanup of only
initiative-owned disposable artifacts.

**CF alignment**: CF-795 (docs/manifests/contracts/tests/Compose), CF-796 (multivac),
CF-797/798/804/805 (validation), CF-799/800/801 (FR evidence).

**Design outputs**:
- Docs: update `docs/features/content/settings/llm-servers/*`,
  `chat/model-controls/*`, `chat/audio/*`, `interviews/transcription/*`,
  `settings/compute-donation/*`, `compute/pool/*`; regenerate site/manifests.
- QA: extend `qa/runtime_capabilities.json` obligations + `docker-compose.qa.yml`
  profiles (deterministic contract lanes cover every accepted feature); run
  `scripts/istara-qa.sh render` (no live model), reset/audit lanes.
- Multivac: read-only inventory of existing benchmark/staging workloads FIRST; unique
  `/srv/repos/<run>` checkout + `/srv/stacks/<run>` compose project; render + inspect
  Compose; run via SSH tunnel (no firewall changes); verify live staging path;
  preserve existing workloads; remove only initiative-owned containers/networks/
  checkouts.

**Verification commands**:
```bash
python scripts/feature_docs.py --seed-missing --generate-site --check
python scripts/check_qa_capabilities.py
python scripts/check_workflow_contracts.py
docker compose -f docker-compose.qa.yml --profile contract config --quiet
./scripts/istara-qa.sh render
python -m pytest tests/test_feature_docs.py -q
python -m pytest tests/test_security_benchmark.py -q
python -m pytest tests/pi_benchmark/test_b1_contract.py -q
python -m pytest tests/pi_benchmark/test_live_driver.py -q --collect-only   # live lanes owner-gated
python scripts/security_benchmark.py --fail-on-threshold
compass-forge gate before --task ... --summary && compass-forge gate after --task ... --summary
# multivac (owner-authorized, SSH tunnel):
ssh multivac 'cd /srv/repos/istara-pi-migration-<run> && docker compose -f docker-compose.qa.yml config --quiet'
ssh multivac 'docker compose -f /srv/stacks/istara-pi-migration-<run>/docker-compose.qa.yml up -d --wait'  # one target
# post-verification cleanup (initiative-owned only):
ssh multivac 'docker compose -f /srv/stacks/istara-pi-migration-<run>/docker-compose.qa.yml down -v --remove-orphans'
```

**Acceptance**:
- Feature-doc parity + generated manifests/site green; every accepted feature has a
  deterministic contract lane in the QA stack contract.
- Security benchmark pass; 0 new gate failures attributable to the wave.
- Multivac: read-only inventory evidence; unique project/paths; SSH-tunneled run;
  benchmark workloads untouched; cleanup proof (only initiative-owned artifacts
  removed).

## 6) Task breakdown mapped to the CF task graph

The CF graph (CF-SPEC-59) already encodes ITEM-001…ITEM-010; this section maps waves
to tasks so implementers can claim work-orders unambiguously.

| Wave | CF task(s) | Core deliverables |
|---|---|---|
| W1 | CF-787, CF-802, CF-803 | Pi dep provenance/version, boundary manifest, gate baseline, migration manifest |
| W2 | CF-788, CF-790 (prep), CF-801 | Canonical catalog, secret custody, migration/rollback snapshot |
| W3 | CF-789, CF-790, CF-794, CF-804 | Compatibility migration, dual-engine routing, deprecation flags, rollback drill |
| W4 | CF-791, CF-794, CF-799, CF-802 | Vector-space invariant, chat controls, selector UX + comparative summaries |
| W5 | CF-792, CF-793, CF-800 | Petals bridge preservation, unified audio/Whisper/diarized config |
| W6 | CF-795, CF-796, CF-797/798/804/805 | Docs/manifests, Compose QA, multivac acceptance + cleanup, FR/SC validation evidence |

Validation tasks CF-797 (US-001), CF-798 (US-002), CF-804 (SC-001), CF-805 (SC-002)
are evidence-gathering acceptance tasks: they must reference the wave evidence rows
above rather than re-run ad-hoc checks.

## 7) Feature-flag / deprecation / removal model

Flags (all recorded in the migration manifest with owner, timestamp, reason, sunset,
cleanup command):

- `agentic_engine_default`: `"legacy"` until W3/S3 owner flip, then `"pi"`.
- `agentic_engine` (per-project): explicit override; cleared on rollback.
- `llmserver_compat_mode`: true through W3; false per-surface after S3.5 criteria.
- `legacy_embed_bridge_enabled`: temporary until vector invariant proves Pi path
  equivalence (W4).
- `petals_bridge_enabled`: unchanged semantics; never defaults to true.
- Per-surface deprecation banners on legacy CRUD UI from S3.5; removal only after
  section-4 removal criteria with evidence bundle + owner sign-off.

Every flag flip is a code change with its own task, evidence, and rollback switch.

## 8) Documentation and manifest obligations

Per AGENTS.md and the CF gates (`architecture_drift`, `test_ownership`), the SAME
change that alters behavior must update:

- Living feature docs under `docs/features/content/`: `settings/llm-servers`,
  `chat/model-controls`, `chat/audio`, `interviews/transcription`,
  `settings/compute-donation`, `compute/pool` (+ `agents/registry`, `agents/a2a` if
  engine metadata changes).
- Regenerate: `python scripts/feature_docs.py --seed-missing --generate-site --check`
  and attach output as evidence.
- Architecture docs: `docs/architecture/agentic_core.md`,
  `docs/architecture/research-validity-contract.md` (only if the migration changes
  spine-visible seams), `docs/architecture/self-improvement-governance-contract.md`
  (only if self-improvement paths change).
- Repo docs: `README.md`, `README.pt-BR.md`, `DOCUMENTATION.md`, `TESTING.md`,
  `AGENTS.md` (only if agent instructions change), `CHANGE_CHECKLIST.md`.
- Security: update `security/control_matrix.json`, `security/SECURITY_BENCHMARK.md`,
  and `tests/test_security_benchmark.py` when a security control/evidence path/
  standard version/trigger changes.

## 9) Security benchmark coverage

Security-sensitive surfaces in scope: LLM-provider config, secrets, endpoint security,
Petals donor compute, MCP/audio secrets, auth on CRUD routes, route evidence. Required
on every wave that touches these:

```bash
python scripts/security_benchmark.py --fail-on-threshold
```

Record the scorecard as CF command evidence. When a control/evidence path/trigger
changes, update the matrix + benchmark docs + `tests/test_security_benchmark.py` in
the same change. Secret-flow findings must be separated: inherited baseline
(`secret_flow`) vs migration-introduced (each wave's diff), with a typed narrative.

## 10) Risks and rollback

### Risk register

| ID | Risk | Sev | Mitigation |
|---|---|---|---|
| R1 | Secret coupling drift (Fernet → Keychain/env mismatch) | High | Staged secret migration, immutable snapshots, non-prod readback + redaction checks, rollback restores bindings (W2) |
| R2 | Identity collision / split-brain (duplicate canonical model IDs) | High | Canonical identity tuple + collision guards + telemetry fail-closed (invariant 2) |
| R3 | Vector-space drift on engine switch | High | Hard invariant probes both engines each wave; drift = compat flag + owner sign-off (W4) |
| R4 | Petals donor trust-boundary widening | High | No bridge changes in early waves; consent/identity/scheduling tests; isolation test green (W5) |
| R5 | UI/route divergence (selector contract mismatch) | Med | Contract-first selector tests, feature-doc coupling, vitest on modelCatalog (W4) |
| R6 | Multivac contamination of existing workloads | High | Read-only inventory first, unique `/srv/repos`+`/srv/stacks` paths, SSH tunnel only, cleanup proof (W6) |
| R7 | Dependency upgrade breaks worker protocol/structured contract | High | Pin latest verified (0.84.2) with compatibility statement; protocol v2 handshake tests; rollback = revert pin |
| R8 | Inherited baseline gate debt masks migration findings | Med | Separate inherited vs new in every gate/security narrative; `gate before/after` diff |
| R9 | Rollback drift after partial data migration | High | Reverse migration script + checksum manifests + W2/W3 rollback drill evidence |
| R10 | Live-model lanes pollute QA determinism | Med | QA `live` profile fails closed without exactly one `QA_LIVE_PROVIDER_TARGET`; deterministic contract lanes separate |

### Rollback commitments

- W2/W3 include rollback validation steps in their own command evidence rows.
- W4/W5 include security + vector invariants evidence before advancing.
- Any proposed deletion of compatibility mode (CF-790 / CF-803 completion) requires:
  full evidence bundle, removal criteria met, and a signed rollback drill on a
  staging-equivalent flow.
- Rollback switch (documented in the manifest): `agentic_engine_default=legacy`,
  clear per-project `agentic_engine` overrides, re-enable `llmserver_compat_mode`,
  restore secret bindings from vault backup, restore compatibility catalog writes
  from migration snapshot, re-run W2/W3 acceptance commands to prove reversion.

## 11) Owner gates and stopping conditions

- The conductor stops at the **owner approval gate** after the architect consensus
  plan is frozen (this draft + A + B → synthesized master plan).
- Implementation waves are released only after the frozen plan is owner-approved.
- Each wave stops at its own evidence gate; the pipeline advances only on command
  evidence + reviewer pass + (major transitions) owner approval.
- No PR is opened, no push, no merge by implementers — the conductor ship stage owns
  that, gated by the cast configuration.

## 12) Deliverables summary

For the implementation teams, this plan yields:

1. A verified boundary inventory and migration manifest (W1).
2. Canonical Pi catalog + secret custody with encrypted, reversible migration
   snapshots (W2).
3. Compatibility migration with dual-engine routing, deprecation flags, and a
   performed rollback drill (W3).
4. Vector-space invariant + chat controls + honest engine-selector UX (W4).
5. Petals preservation + unified audio/Whisper/diarized config (W5).
6. Living docs + manifests, deterministic Compose QA coverage, multivac acceptance +
   cleanup proof (W6).
7. Full rollback package usable by operations with clear exit points at every wave.
