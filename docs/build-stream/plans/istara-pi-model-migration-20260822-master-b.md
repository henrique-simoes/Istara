# MECE Master Architecture Plan (Synthesis B) — Istara Pi Model-Management Migration, 2026-08-22 run

**Task:** `ISTARA-PI-MODEL-MIGRATION-20260822-MASTER-B` (consensus master-plan synthesis, slot B)
**Role:** `istara-pi-model-migration-20260822-architect-b`
**Spec:** `CF-SPEC-1` (this run; the frozen `CF-SPEC-59` / `CF-787…CF-805` graph of the 2026-08-18 run is history, not scope)
**Pipeline run:** `ISTARA-PI-MODEL-MIGRATION-20260822` · strict-wave manifest SHA-256 `b9c8ff0ca1c0521fff18e27d3caf53e11fac89c6fb9a44e1656688ac1cf5a8fd` (canonical JSON serialization; re-verified at synthesis time)
**Planning phase:** `synthesize` (round `0bb85df72bbe6604f51a`) — write one complete MECE master-plan candidate to this `plan_file`. No implementation, no lifecycle-plan edits, no vote in this phase.
**Inputs (immutable, SHA-256 verified against `consensus.json` at synthesis time):** slot-A draft `…plan-a.md` (`830a54b9…`), slot-B draft `…plan-b.md` (`ffa5899f…`), slot-C draft `…plan-c.md` (`fd6fa270…`); carried-forward 2026-08-18 drafts `carried-20260818-plan-{a,b,c}.md` used as inputs by all three slot drafts and re-inspected here.
**Branch/worktree:** `conductor/istara-pi-model-management-migration-20260822` (base `origin/testing@15260a78df6637c2d1981c74683525cb75ab1a22`). Everything stays on the testing lineage; never `main`. No merge, push, or PR from this stage.

---

## 0. Synthesis coverage matrix (which draft insight each major section incorporates)

This candidate reconciles — does not concatenate — the three immutable drafts. Load-bearing insights per draft: **A** = canonical identity schema, secret custody discipline, migration state machine, research-spine/test-ownership contracts, security reviewer checklist; **B** = verified current-tree facts V1–V16, engine-precedence contract, S0–S5 retirement phases with per-transition gates, VPS single-service reality check, wave command sets; **C** = current-tree boundary tables, ratchet/gate framing, owner-gate model, disposable-database discipline, coverage-by-requirement shape.

| Master section | Primary substantiation | Secondary |
|---|---|---|
| §1 Executive recommendation | B §1 (authority migration, two engines) | A §1 (ratchet framing), C §1 (transport boundary) |
| §2 Verified current-state boundary | A §2 (surface inventory), B §2 (V1–V16) | C §2 (inventory table) |
| §3 Conflict reconciliation | A §3 + B §2 (C1–C7), C §1/§5 (self-corrections) | — |
| §4 Scope / non-goals / invariants | B §3 (I1–I10) | A §4 (invariant table), C §3 (contracts) |
| §5 Target architecture | A §5 + B §4 (identical semantic split, merged) | C §3 (fail-closed semantics) |
| §6 Retirement state machine, flags, removal | A §7 (promotion criteria), B §5 (S0–S5 + gates) | C §4 (states, owner gates) |
| §7 Data/secret migration + rollback | A §6 (procedure), B §6 (switchboard) | C §4 (rollback switch) |
| §8 Wave plan with exact verification | B §7 (commands, VPS path), A §8 (acceptance phrasing) | C §5/§6 (baselines, disposable DB) |
| §9 Isolated VPS acceptance + cleanup | B §9 (vps skill contract, C5 reality check) | A §8 W5 (C1/C5/C7) |
| §10 Test ownership | A §9 (ownership matrix) | B §10, C §6 (verification contract) |
| §11 Documentation/manifest obligations | A §10 + B §10 (merged lists) | C §7 |
| §12 Security benchmark + review checklist | A §11 (checklist) | B §10, C §7 |
| §13 Risks and mitigations | A §12 + B §11 (merged register) | C §7 (risk list) |
| §14 Definition of Ready/Done + owner gates | A §13 + B §12 (merged) | C §4/§7 |
| §15 Requirement coverage matrix | C §8 (shape) | A §14, B §13 |

## 1. Executive recommendation

Make Pi the **single canonical model-management authority** — provider families, model identity, endpoint identity, capability metadata, secret references, and resolution — while Istara keeps **two explicitly selectable, permanently supported agentic engines** (`pi` and `legacy`) whose transports differ but whose model identity, route evidence, accounting, and vector space are governed by one canonical plane.

The legacy `LLMServer` row plane (storage + CRUD + live `ComputeRegistry` registration + Fernet encryption) becomes a **reversible compatibility adapter and migration source**, not a second catalog. It retires in observable stages — *legacy-compat → shadow → pi-primary → deprecated-adapter → retired* — each transition gated by acceptance evidence, a performed rollback drill, and owner approval at the major gates. No legacy row, credential, vector, donor consent, or audit record is deleted merely because a canonical record now exists; physical deletion is a separate, later, owner-approved action after all removal criteria hold.

The product-side dispatch ratchet is already **0 direct call sites** (`tests/pi_migration/test_count_to_zero.py`, 3 passed at synthesis time), so this is a **model-management authority migration**, not a call-site migration. The recommendation of all three drafts is confirmed: do **not** equate "Pi owns model management" with "delete every legacy LLM Server, Ollama, LM Studio, or `ComputeRegistry` module." The migration is additive and idempotent first: inventory → map → validate → dual-read/shadow → canary → Pi-primary → deprecate → (separate, later) retire.

The 2026-08-22 run replaces the retired multivac staging path with **isolated acceptance on the managed VPS per the `vps` skill** (Dokploy strict single-workload profile; `vpsctl.py` preflight → inventory → deploy → verify-isolation → verify-exposure → audit-anchor; no firewall change without owner approval). The conductor **stops at the owner approval gate after the consensus plan is frozen**; no implementation task is released before it.

## 2. Verified current-state boundary (re-verified at synthesis, 2026-08-22)

Facts re-verified by this synthesis stage against the worktree (independent of the drafts, confirming them):

| # | Fact | Evidence |
|---|---|---|
| S1 | Upstream latest `@earendil-works/pi-agent-core` = **0.84.2**, `@earendil-works/pi-ai` = **0.84.2** (passive registry query) | `npm view … version` (synthesis re-run) |
| S2 | `pi-runtime` pins **0.83.0**/0.83.0; `labs/pi-replacement` pins **0.80.10**/0.80.10 (lab diverged silently) | package.json reads |
| S3 | Count-to-zero ratchet green: 1 allowlisted permanent site (`backend/app/core/agentic/legacy.py:599` `server.chat(`), `EXPECTED_PRODUCT_SITES=0`, **3 passed** | `uv run --project backend python -m pytest tests/pi_migration/test_count_to_zero.py -q` |
| S4 | Gate baseline: `gate before` = **fail, 30 failures** (`secret_flow`, `unexpected_large_files`), **0 new, 0 actionable**, drift route=4/type=2, warnings=188 | pinned CF binary `gate before --summary` (synthesis re-run) |
| S5 | Manifest binding hash matches canonical serialization (`b9c8ff0c…`); six waves: `foundation`, `pi-catalog-secrets`, `compat-routing`, `embeddings-controls`, `petals-audio`, `qa-docs-vps` | sha256 over canonical JSON |
| S6 | `vpsctl.py` is **not** in this repo; lives at `~/.pi/agent/skills/vps/scripts/vpsctl.py` with subcommands `preflight, inventory, audit-verify, audit-anchor, verify-isolation, verify-exposure, ssh` | `vpsctl.py --help` (synthesis re-run) |
| S7 | `repo_lock.py` for the ledger critical section: `/Users/user/Documents/Skills/build-stream-conductor/scripts/repo_lock.py` | filesystem |

Facts verified by the drafts (accepted into the master plan; each was checked at draft/repair time and is re-checkable at implementation): B's V1–V16 table (Pi versions/pins; engine precedence per-call → header `x-istara-agent-engine` → project `agentic_engine` → `settings.agentic_engine_default="legacy"` at config.py:315, no silent fallback; security benchmark 28/28 pass; feature docs 86 features/224 artifacts/0 seeded; environment prerequisites; `pi_api_endpoints: list[PiApiEndpoint]` config.py:304 with `DEFAULT_ENDPOINT_ID="pi-deepseek-default"`; 8-service `docker-compose.yml`; QA profiles contract/synthetic/reset/audit/live/ui; 38/38 test anchors present; 3 new-obligation tests absent; frontend anchor `frontend/src/components/settings/ProjectSettingsView.tsx`), and A's §2 surface inventory (legacy plane: `models/llm_server.py`, `routes/llm_servers.py`, `llm_router.py`, `compute_registry*.py`, `ollama.py`, `network_discovery.py`, `field_encryption.py`, `endpoint_security.py`; Pi plane: `pi_runtime/{endpoints,model_manager,engine,supervisor,embeddings_gateway,model_manager_provisioning,seams}.py`, `pi-runtime/src/worker.mjs` NDJSON protocol v2, `agentic/{dispatcher,legacy,usage_ledger}.py`, `pi_replacement.py`; coupled surfaces: embeddings, `petals_bridge.py`, `transcription.py`/`file_processor.py`/chat voice routes, frontend `modelCatalog.ts`/`modelProviders.ts`/settings views, `docker-compose.qa.yml`/`qa/`, `relay/`, research-validity contract).

**Baselines every implementation wave must carry forward (do not re-measure wrongly):** gate 30 inherited / 0 new (NOT the stale "80" of the 2026-08-18 run); security benchmark 28/28; feature-doc parity green; ratchet 0 product sites with exactly 1 documented permanent infrastructure allowlist entry.

## 3. Reconciliation of conflicts and corrections (synthesis decisions)

| ID | Conflict between drafts / carried drafts | Resolution adopted (load-bearing) |
|---|---|---|
| C1 | Carried drafts stage final acceptance on multivac; DEC-2 retired multivac | **VPS per the `vps` skill** everywhere (§9). No multivac command remains in this plan. |
| C2 | C maps waves to old-run `CF-787…CF-805`; A/B map to this run's six-wave manifest | **This run's manifest wave ids are authoritative** (`foundation`, `pi-catalog-secrets`, `compat-routing`, `embeddings-controls`, `petals-audio`, `qa-docs-vps`). Old CF ids appear only as a scope checklist in parentheses. Implementation CF tasks are generated at owner approval from CF-SPEC-1. |
| C3 | C's baseline "80 inherited gate failures" vs A/B's "30" | **30 inherited / 0 new / 0 actionable** (S4). Every later narrative separates inherited debt from migration findings. |
| C4 | A's "`PI_API_ENDPOINTS` settings state" naming | Correct field is `pi_api_endpoints: list[PiApiEndpoint]` (config.py:304). |
| C5 | Full 8-service `docker-compose.yml` vs vps strict single-workload profile | The strict profile permits exactly one service. Default VPS acceptance target is a **dedicated single-service acceptance image**; any multi-container exception requires written owner approval with the minimum connectivity graph (§9.3). Never silently weaken isolation. |
| C6 | Environment prerequisites implicit in A | Explicit in every wave: backend tests via `uv run --project backend …`; worker-backed tests require `cd pi-runtime && npm ci` first; frontend via `npm --prefix frontend ci`. |
| C7 | Pre-repair drafts cited `scripts/vpsctl.py` in-repo | `vpsctl.py` lives in the **vps skill**; all VPS commands use `VPSCTL=~/.pi/agent/skills/vps/scripts/vpsctl.py` (S6). |
| C8 | C cites `tests/llm_servers.py`; correct anchor is `tests/test_llm_servers.py` | Use `tests/test_llm_servers.py` (C's L-5 self-correction held). |
| C9 | C runs `python -m pytest` bare; A/B use `uv run --project backend` | Canonical runner: **`uv run --project backend python -m pytest … -q`** (backend/uv.lock now exists in the worktree). |
| C10 | Three state-machine variants: A per-row `unmapped→…→retired`, B initiative phases S0–S5, C `discovered→…→retired` | **Unified in §6**: one global rollout-mode registry + one per-row/per-endpoint migration state machine + initiative-level phase narrative; mapping table shows equivalence. All three agree no state transition without evidence + gates. |
| C11 | Dependency-update placement: A/B put it in Wave 1; C spreads it over W0/W1 | **Wave 1** (`pi-catalog-secrets` manifest instructions name "latest verified upstream Pi packages"). Re-verify passively immediately before changing pins; record registry output, lockfile resolution, and protocol-v2 compatibility statement. |
| C12 | Frontend selector path: C's `components/ProjectSettingsView.tsx` | Correct: `frontend/src/components/settings/ProjectSettingsView.tsx` (V16). |
| C13 | Pi latest: all drafts say 0.84.2 vs pins 0.83.0/0.80.10 | Held (S1/S2). Update both `pi-runtime` **and** `labs/pi-replacement` in lockstep to the latest verified compatible release, or record an explicit reviewed divergence rationale. |

## 4. Scope, non-goals, and invariants

### In scope

Legacy LLM Server storage/routing/encryption consumers; both agentic engines; Pi provider/model catalog and endpoint resolver; embeddings/vector-space invariant; Petals donor bridge; audio/transcription flows; UI contracts; testing-branch Docker QA; VPS acceptance + cleanup per the `vps` skill; exact data/secret migration + rollback; latest verified Pi dependency update; duplicate-identity elimination; feature-flag/deprecation/removal criteria; per-wave acceptance + commands; documentation/manifest obligations; security benchmark coverage.

### Non-goals (planning stage now; later stages only with separate authorization)

- No implementation in this planning stage. No merge/push/PR (the conductor ship stage owns it, gated by cast config).
- No live backend/frontend servers, no model loading, no live completion probes; passive status/discovery and registry queries only; at most one owner-authorized bounded target on live QA lanes.
- No mutation of `LLMs/` or `Model_Finetuning/`; no deletion of the legacy transport, `ComputeRegistry`, local Ollama/LM Studio provisioning, donor relay/browser transport, or the permanent legacy executor.
- No firewall change on the VPS without owner approval; no mutation of unrelated Docker workloads; no public exposure of private host/tunnel details or credentials.
- No treating synthetic QA results, raw tool success, transcript keyword tags, or comparative model prose as accepted research evidence (Research Spine contract).
- No silent merge of endpoint identities that share a model name or host.

### Invariants that never regress (each mapped to its primary proof)

| # | Invariant | Primary proof |
|---|---|---|
| I1 | Pi/runtime isolation: `pi_runtime` never imports/mutates `ComputeRegistry`; Pi resolution never donor-scores | `tests/pi_production/test_same_model_donor_isolation.py` |
| I2 | Explicit dual-engine choice; precedence stable (S-docstring, config.py:315); selected-engine failure never silently switches engines | `test_w1_agentic_contract.py`, `test_w1_dispatcher_authority.py`, `test_w6_engine_selection.py` |
| I3 | One identity plane: provider-qualified `model_id` ≠ stable `endpoint_id`; legacy ids (`pi-llm-<id>`, `pi-petals-<node_id>`, `legacy_source_id`) are provenance aliases only; no duplicate canonical identities | `test_model_provider_contract.py` + **new** migration catalog contract tests (Wave 2) |
| I4 | Secret safety: plaintext credentials only in short-lived in-memory binding; none in logs/responses/docs/QA artifacts/telemetry/CF evidence | `test_endpoint_secrets.py`, `test_field_encryption.py`, security benchmark |
| I5 | Vector-space invariance: chat-engine/endpoint changes cannot silently alter embedding model/dimension/dtype/normalization; mismatch blocks before vector/cache writes | `test_w8_embeddings_gateway.py` |
| I6 | Donor security: consent + health + project authorization + exact node pin; unavailable ⇒ typed 503; no paid fallback; no donor as ordinary Pi capacity | `tests/petals_bridge/test_petals_bridge.py`, donor-isolation test |
| I7 | Research Spine: source spans → evidence units → coding → reliability → reconciliation → review → Done → report; candidate/provisional outputs never reportable | `test_research_validity_contract.py`, `test_synthetic_provisional_boundary.py` |
| I8 | Reversibility: every source row has mapping/status + restorable snapshot before write/cutover; rollback is a documented switch, not an exception handler | **new** `tests/pi_migration/test_model_management_{migration,rollback}.py` (Wave 2) |
| I9 | QA isolation: unique `istara-qa-<run-id>` projects, internal networks, deterministic provider stub, live lane owner-gated | `test_qa_stack_contract.py`, `test_qa_reset_seed.py` |
| I10 | VPS isolation: strict single-workload profile only; one internal network, one endpoint, no default route, no host/other-container reachability, exact approved port set | `vpsctl.py verify-isolation`/`verify-exposure` + firewall/`DOCKER-USER` evidence (Wave 5) |

## 5. Target architecture

### 5.1 Canonical identity model (additive schema; semantic split is load-bearing, names adapt to repo conventions)

```text
CanonicalModel    model_id (provider-qualified, normalized — never a display string)
                  provider_family | canonical_name | aliases[] (provenance-attached)
CanonicalEndpoint endpoint_id (stable route identity, always distinct from model_id)
                  model_id | transport: pi_http | legacy_registry | local_lifecycle |
                            petals_bridge | audio_adapter
                  endpoint_kind: cloud | custom | local | petals | audio
                  nonsecret connection metadata + capability profile
                  credential_ref (opaque) | legacy_source_id (nullable, provenance ONLY)
                  migration_state (§6)
CredentialRef     credential_ref (opaque stable name) | kind: keychain | encrypted_db |
                  environment | oauth | status: present | missing | invalid | rotation_required
EmbeddingProfile  profile_id | model identity | endpoint/transport identity | dimension | dtype |
                  normalization | version | health
AudioModelProfile profile_id | provider_family | model_id | endpoint_id | credential_ref |
                  local|remote mode | language policy | diarization support | speaker-count
                  policy | confidence/human-review threshold
```

Rules: two providers serving the same visible model name remain distinct canonical models unless an explicit alias mapping proves equivalence; capability metadata is attached, never inferred from names, and unknown capability fails closed when required; `base_url`, hosts, route ids, and credential refs never appear in public docs, QA artifacts, or normal telemetry; admin views return redacted metadata + `has_credential` only.

### 5.2 Resolver and transport boundary

One canonical resolution request for every dispatcher verb:

```text
resolve_model_request(project_id, engine, model_id?, endpoint_id?, purpose,
                      capabilities?, embedding_profile_id?) -> ResolvedModelTarget
```

`ResolvedModelTarget` = canonical model id, endpoint id, transport class, safe capabilities, credential reference, route-evidence fields. Never plaintext credentials.

- `PiModelManager` becomes the authoritative catalog/resolver (exact identity, capability admission, migration projection, weakref invalidation for live-DB projections; the existing three-source catalog is reorganized, not discarded).
- `PiExecutionService` consumes only `transport=pi_http` targets and binds secrets only on the private worker pipe (NDJSON v2 `provider.bind` frames; `PROTOCOL_VERSION=2`).
- The legacy executor stays a permanent, byte-compatible **transport adapter** consuming `legacy_registry`/`local_lifecycle` targets; it never manufactures a second catalog.
- Petals: explicit `transport=petals_bridge`, `pi-petals-<node_id>` identity, bridge admission, exact donor pin, route stamp; never a capacity candidate.
- Audio: `transport=audio_adapter` with explicit capability contract; binary audio never routes through the text Pi worker unless a separately verified provider API supports it.
- Every dispatcher verb (`chat_turn`, `completion`, `structured`, `ensemble`, `embed`, `react`, plus A2A/channel/autoresearch seams) keeps exactly one usage-ledger row per dispatch, including typed resolution failures; resolution failure is a typed failure, never a fallback to another engine.

### 5.3 Provider classes and secret custody

Explicit classes: cloud OpenAI-compatible; Anthropic-compatible; OAuth (Keychain/encrypted custody, short-lived in-memory tokens); API key (Keychain/env/encrypted DB); custom/local (normalized loopback or approved HTTPS via `endpoint_security.py`, capability probe metadata); audio/Whisper/diarization (never auto-promoted to a chat provider). Local Ollama/LM Studio lifecycle is separate from cloud credentials.

The migration service may read legacy Fernet-encrypted `LLMServer.api_key` only in memory, immediately re-encrypting/externalizing into canonical custody. Manifests store credential reference + kind + presence + nonsecret metadata checksum — never plaintext, raw tokens, or reusable secret fingerprints. Keychain references preserve service/account identities without copying values. Encryption context/version compatibility is recorded and tested (the migration must not assume the same encryption context as standalone Pi).

### 5.4 Engine selection and rollback semantics

Preserve precedence exactly: per-call → header → project `agentic_engine` → `settings.agentic_engine_default` (default `"legacy"` until the owner flips it). Canonical target resolution happens **after** engine selection — never a hidden second engine choice. A selected `pi` target with missing credentials, unsupported capability, worker failure, or provider error is a failed Pi invocation (typed error + ledger row); symmetrically no Pi fallthrough for `legacy`. Rollback = explicit mode/project flip to `legacy` + snapshot restore (§7.4), never an implicit exception path. `PI_ENGINE_VALUES={"pi","pi-candidate","pi-replacement","deepseek-pi"}` stays canonical.

### 5.5 Embeddings

One authoritative `EmbeddingProfile` for both engines; adapters may differ in transport but must produce identical dimension/dtype/model/normalization. Mismatch blocks startup/engine switching and cache writes. Existing vectors stay tied to their recorded profile version; a deliberate profile change is a new version with a bounded re-embed job + dual-read/reindex evidence + explicit invalidation. Chat endpoint changes never mutate the embedding profile; the UI separates chat-model controls from embedding-profile controls and shows the active profile identity safely. The Pi embeddings gateway keeps exactly one dispatcher-owned usage row (no double accounting).

### 5.6 Petals

`petals_bridge.py` stays outside `pi_runtime`; only `source ∈ {relay,browser}`, `pi_served=true`, healthy, project-authorized donors are admitted. Unavailable/unconsented/unhealthy/unauthorized ⇒ typed `PetalsUnavailable` 503 + route evidence, no paid fallback. Donor identity visible to audit without prompts/URLs/secrets. No early-wave bridge changes; Wave 4 adds authorization/consent/scheduling tests and keeps the isolation invariant green. `settings.petals_bridge_enabled` semantics unchanged.

### 5.7 Audio and diarization

Unified `AudioModelProfile` contract consumed by interview uploads, microphone chat, and channel audio, preserving project authorization and source provenance. `local_whisper` keeps the existing local loader + ffmpeg boundary (model size validated against local capability); `remote_whisper`/`remote_diarization` are opt-in adapters (e.g., GPT-4 diarization per the manifest wave) with capability metadata, credential custody, bounded size/timeouts, redacted errors, deterministic mocked contract tests. A provider without diarization cannot be advertised as diarized. No configured audio profile ⇒ typed unavailable — never a silent text-chat fallback. Transcripts remain candidate/provisional source material until raw audio spans/segments, coding, reliability, reconciliation, and human review accept them; ICR failure stays `needs_review`.

## 6. Reversible retirement: state machine, feature flags, deprecation, removal

### 6.1 Unified model (C10): three coordinated layers

**Layer 1 — initiative phases (narrative; B's S0–S5):**

```text
S0 legacy-authoritative (today)          S3 pi-preferred + legacy compatibility-only
S1 pi-authoritative catalog + secrets    S4 deprecated-adapter (warnings, compat reads)
S2 dual-engine execution (both explicit) S5 retired (runtime use off; archival, not deletion)
any state -> blocked(reason)
```

**Layer 2 — per-row/per-endpoint migration state machine (A's, authoritative for data):**

```text
unmapped -> mapped -> credential_validated -> shadow_verified
        -> pi_primary -> legacy_deprecated -> retired
any state -> blocked (reason + evidence handle)
pi_primary / legacy_deprecated -> rollback_ready -> legacy_compat
```

- **mapped:** canonical target exists; source row untouched; no cutover.
- **credential_validated:** secret reference resolves in memory; capability metadata valid; no completion call needed.
- **shadow_verified:** read-only resolution + metadata parity on a canary project/contract stub; never double-sends user research content to a provider.
- **pi_primary:** Pi selected for opted-in project/route; legacy data readable through the adapter.
- **legacy_deprecated:** admin writes use canonical Pi management; legacy endpoints return deprecation metadata + read-only compatibility projections.
- **retired:** runtime use disabled; physical deletion separate and later.

**Layer 3 — one rollout-mode registry (avoid many independent booleans):**

```text
PI_MODEL_MANAGEMENT_MODE = legacy_compat | shadow | pi_primary | deprecated_adapter | retired
```

Defaults: `legacy_compat` on existing installs; `agentic_engine_default` stays `"legacy"` until the owner flips it; per-project `agentic_engine` remains an explicit override cleared on rollback; `llmserver_compat_mode` on through Wave 2, off per-surface after S4 criteria. Mode is visible in safe admin diagnostics and included in route/migration evidence. Every flag flip is a code change with its own task, evidence, and rollback switch.

### 6.2 Transition gates

Every S_i → S_i+1 requires: (a) that wave's acceptance commands green; (b) `gate after` with **0 new** failures attributable to the wave (inherited baseline tracked separately); (c) reviewer `review_verdict` pass; (d) performed rollback-drill evidence for S2→S3 and S3→S4; (e) **owner approval** before S2→S3 and S4→S5 (and at the plan gate and ship, always).

### 6.3 Promotion criteria per mode

- `shadow`: deterministic catalog/mapping parity, credential-status parity, no duplicate canonical identity, no secret-flow violation, no new gate drift.
- `pi_primary`: successful canary on contract/faux providers; both engine suites green; embedding invariant proof; Petals isolation proof; audio unavailable/capability proofs; rollback artifact exists.
- `deprecated_adapter`: all new writes use canonical Pi management; compatibility GET/read paths preserve existing clients; deprecation headers/diagnostics; report of unmigrated/blocked rows.
- `retired`: **all** removal criteria (§6.4) with evidence.

### 6.4 Removal criteria (all must hold before `retired`; physical deletion is a separate later owner-approved action)

1. Count-to-zero ratchet green + allowlist audit clean (only the documented permanent legacy-executor transport entry).
2. Zero active runtime reads treating LLM Server as canonical; zero unmapped rows except owner-accepted exceptions.
3. All supported credentials resolvable or explicitly blocked; no data/secret-loss report.
4. Vector invariant green on both engines; Petals security controls intact; audio flows on canonical config; UI offers no legacy-only model CRUD without deprecation notice.
5. ≥1 performed staging-equivalent rollback drill.
6. Three consecutive deterministic full-suite runs with no new migration failures; one isolated testing-branch Compose run; one owner-authorized VPS staging proof when marked required.
7. Security benchmark green; docs/manifests green.

**Deprecation behavior:** stable deprecation header + safe diagnostic reason on legacy CRUD/compat paths; read compatibility preserved for the retention window; writes go canonical or fail closed with a migration-required response (never an untracked second source of truth). Local lifecycle and donor APIs are transport infrastructure and are **not** deprecated — only the model-management ownership semantics are.

## 7. Exact data/secret migration and rollback

### 7.1 Preflight (immutable evidence, before any write/cutover)

1. Capture branch/base commit, schema revision, package versions + lockfile hashes, `gate before` output.
2. Redacted inventory (`scripts/pi_migration_inventory.py --json`) of static Pi settings, `LLMServer` rows, relay/browser rows, local provider settings, project engine selections, embedding metadata — source ids + mapping reasons, never secret values or private endpoints.
3. Encrypted DB backup/snapshot (gitignored disposable path, owner-approved retention/restore proof) + pre-change Compose definition copy.
4. Credential presence/status dry-run only — no live completions, no model loads, no printed secrets.
5. Deterministic `migration_id` + schema version + source checksum + tool version; rerun with the same checksum is a no-op.

### 7.2 Deterministic mapping (per non-relay LLM Server row)

Normalize provider family + URL via `endpoint_security.py` → parse capability JSON without inventing model names (absent model = explicit `unknown/default` needing validation) → resolve/create one provider-qualified `model_id` → resolve/create exactly one `endpoint_id` bound to the stable source row (`legacy_source_id`, priority, health summary, capability provenance preserved) → credential reference (in-memory decrypt → re-encrypt via canonical custody, or bind the source encrypted field as a compatibility reference; Keychain service/account refs copied without values; local no-key rows use a nonsecret local mode) → mark `mapped | credential_validated | blocked | legacy_only` with actionable reason → store redacted mapping result. Relay/browser rows are **never** migrated into ordinary Pi endpoints (donor plane only). Unsupported/malformed rows are preserved and visible, never dropped.

### 7.3 Staged cutover

`mapped` (no runtime cutover) → `credential_validated` (in-memory secret resolution + capability validity; no completion call) → `shadow_verified` (read-only resolution + metadata parity on a canary project/contract stub) → `pi_primary` (opt-in project/route; legacy data still readable) → `legacy_deprecated` (canonical writes only; read compat + deprecation metadata) → `retired` (only after §6.4 + owner gate).

### 7.4 Rollback (explicit operation, per-wave switches — never an exception handler)

1. Stop the staged QA/VPS acceptance workload before data changes.
2. `PI_MODEL_MANAGEMENT_MODE=legacy_compat`; `agentic_engine_default=legacy`; clear per-project `agentic_engine` overrides; re-enable `llmserver_compat_mode`.
3. Restore canonical mapping/status snapshot if mapping corrupt (keep the failed-migration report).
4. Restore encrypted DB/config snapshot only when additive recovery fails; verify schema downgrade/restore compatibility first.
5. Restore prior checkout/Compose and re-run: legacy routing, embedding dimension, donor isolation, source-evidence contract suites.
6. Prove no source row / engine setting / vector / donor consent / audit row was lost; record rollback command + evidence; retain the migration artifact.

No step requires deleting a source row to validate success; unmappable rows stay `legacy_only`/`blocked` with the adapter enabled.

## 8. Wave plan with exact verification (maps to the run's strict-wave manifest)

Environment prerequisites for every wave: backend via `uv run --project backend …` (with `uv sync --extra dev`); worker-backed tests only after `cd pi-runtime && npm ci`; frontend via `npm --prefix frontend ci`; VPS via `VPSCTL=~/.pi/agent/skills/vps/scripts/vpsctl.py`. Fresh disposable databases for migration evidence; never infer validity from contaminated persistent SQLite (C §6). Implementation CF tasks are generated at owner approval; work orders name dependencies, changed-path ownership, tests, docs, rollback, gates per task.

### Wave 0 — `foundation` (planning only; this stage)

- **Goal:** freeze the boundary, record baselines, produce the architect consensus plan, stop at the owner approval gate. No code changes.
- **Acceptance:** verified version/provenance record (S1/S2); baseline gate/security/docs evidence captured (S4 + drafts' V5–V7); ratchet green (S3); three independent drafts reconciled into one frozen MECE master plan with coverage matrix; owner approval recorded; **no implementation task released before approval**.
- **Commands (already run as this stage's evidence):** `npm view` (S1); `python3 scripts/pi_migration_inventory.py --json`; `uv run --project backend python -m pytest tests/pi_migration/test_count_to_zero.py -q`; pinned-CF `gate before --summary`; `python3 scripts/security_benchmark.py --fail-on-threshold`; `python3 scripts/feature_docs.py --seed-missing --generate-site --check`.

### Wave 1 — `pi-catalog-secrets` (≈ old CF-787/788/801)

- **Goal:** Pi becomes the canonical catalog/secret owner; unify provider/endpoint/model config under the Pi plane; validate encryption against standalone Pi; keep `LLMServer` rows intact. Includes the dependency update and effort/thinking/temperature control plumbing.
- **Design outputs:** canonical catalog service layered on `PiModelManager` (identity graph, endpoint capabilities, auth hints, secret handles); secret custody migration (Fernet → Keychain/env/encrypted-DB references with deterministic secret names, non-production readback checks, redaction audit, 60s TTL cache unchanged); migration snapshot stubs; `pi-runtime` + `labs/pi-replacement` pinned to the latest verified upstream (re-verify before change; record registry output, lockfile resolution, protocol-v2 compatibility statement).
- **Verification:**
  ```bash
  npm view @earendil-works/pi-agent-core version && npm view @earendil-works/pi-ai version
  cd pi-runtime && npm ci && npm test && cd ..
  npm --prefix labs/pi-replacement ci && npm --prefix labs/pi-replacement run validate
  uv run --project backend python -m pytest tests/test_pi_runtime_endpoints.py \
    tests/test_settings_agentic_pi_endpoints.py tests/pi_production/test_endpoint_secrets.py \
    tests/test_field_encryption.py tests/test_llm_fallback_config.py \
    tests/test_model_provider_contract.py tests/pi_production/test_w8_embeddings_gateway.py \
    tests/pi_migration/test_count_to_zero.py -q
  uv run --project backend python -m pytest tests/pi_production/test_w1_agentic_contract.py -q   # worker-backed; npm ci first
  python scripts/security_benchmark.py --fail-on-threshold
  python scripts/feature_docs.py --seed-missing --generate-site --check
  compass-forge gate before --summary && compass-forge gate after --summary   # 0 new failures
  ```
- **Acceptance:** zero secret leakage in logs/config snapshots; exact source fields preserved through alias maps (field-level diff tests); rollback restores runtime settings + encrypted bindings; `LLMServer` rows untouched; duplicate model identity impossible (uniqueness + collision tests); same-model-different-endpoint canonicalization proven (one `model_id`, distinct `endpoint_id`s); lockfiles reproducible; latest verified package provenance recorded; ratchet still 0; inherited vs new failures separated.
- **Rollback:** restore prior package pins/lockfiles/worker checkout; `PI_MODEL_MANAGEMENT_MODE=legacy_compat`.

### Wave 2 — `compat-routing` (≈ old CF-789/790/794/804)

- **Goal:** Pi becomes the canonical resolver for BOTH engines; legacy config migrates without silent loss; bounded deprecated adapter; rollback + migration observability; fail-closed removal criteria defined.
- **Design outputs:** migration/projection layer (legacy readers resolve through Pi catalog views; legacy writes route through canonical write APIs with provenance tags); rollback observability (per-row lineage, migration audit log, switchboard `PI_MODEL_MANAGEMENT_MODE` + `agentic_engine_default` + per-project `agentic_engine` + `llmserver_compat_mode`); engine selection preserved at all dispatcher verbs; `PI_ENGINE_VALUES` stays canonical; new `tests/pi_migration/test_model_management_migration.py` + `test_model_management_rollback.py` obligations.
- **Verification:**
  ```bash
  uv run --project backend python -m pytest tests/test_llm_servers.py \
    tests/test_settings_agentic_pi_endpoints.py tests/test_pi_runtime_endpoints.py \
    tests/pi_production/test_w1_agentic_contract.py tests/pi_production/test_w1_dispatcher_authority.py \
    tests/pi_production/test_w1_usage_ledger.py tests/pi_production/test_w1_realpath_accounting.py \
    tests/pi_production/test_w4_a2a_handlers.py tests/pi_production/test_w6_engine_selection.py \
    tests/pi_benchmark/test_b1_contract.py tests/compute_cases/routing.py \
    tests/compute_cases/status_contracts.py -q
  uv run --project backend python -m pytest tests/pi_migration/test_model_management_migration.py \
    tests/pi_migration/test_model_management_rollback.py tests/pi_migration/test_count_to_zero.py -q
  python3 scripts/pi_migration_inventory.py --json
  python scripts/security_benchmark.py --fail-on-threshold
  ```
- **Acceptance:** dry-run-then-execute migration is idempotent (second run no-op); canonical mapping/status stable; source data recoverable (diff counts + checksums); secret reference resolves without plaintext export; per-dispatch exactly one usage/route row; engine/provider failure never switches engines; deprecated clients get documented adapter/deprecation behavior and create no new identity; unsupported/malformed rows remain `legacy_only`/`blocked` with reason; rollback drill performed and recorded; typed failure on unknown engine mode.
- **Rollback:** §7.4 switch sequence + reverse migration script; re-run W2 acceptance to prove reversion.

### Wave 3 — `embeddings-controls` (≈ old CF-791/794/799)

- **Goal:** one coherent vector space with explicit embedding identity; chat endpoint changes never silently change embeddings; expose temperature/thinking/effort controls; clear Pi-vs-Istara engine buttons with evidence-backed comparative summaries.
- **Design outputs:** embedding policy keyed by canonical model identity; dimension/dtype/endpoint invariant in gateway + benchmark surface (drift requires explicit compat flag + owner sign-off); chat control propagation (`temperature`, `max_tokens`, `thinking_level`, `timeout_ms`, `max_retries` via the canonical bind-params path); selector UX rework in `frontend/src/lib/modelCatalog.ts` + `frontend/src/components/settings/ProjectSettingsView.tsx` with honest comparative summaries sourced from benchmark evidence (research-spine grounded, provisional status — no fabricated claims); accessibility contract.
- **Verification:**
  ```bash
  uv run --project backend python -m pytest tests/pi_production/test_w8_embeddings_gateway.py \
    tests/pi_production/test_w8_ux_parity.py tests/pi_production/test_w6_engine_selection.py \
    tests/pi_production/test_w1_agentic_contract.py tests/test_pi_runtime_endpoints.py \
    tests/test_rag_resilience.py tests/test_research_validity_contract.py -q
  npm --prefix frontend ci && npm --prefix frontend run test:unit -- --run
  npm --prefix frontend run lint && npm --prefix frontend run build
  node --test tests/simulation/scenarios/79-engine-selector.mjs
  python scripts/feature_docs.py --seed-missing --generate-site --check
  ```
- **Acceptance:** embedding dimension/model mapping identical before/after each migration step (invariant probe green both engines); no duplicate embedding identity accepted; chat endpoint change leaves embedding profile unchanged and identity visible in safe metadata; selector precedence/validation stable; comparative summaries cite evidence provenance and stay provisional (never presented as research evidence).
- **Rollback:** restore prior profile version + settings; vectors remain keyed to their recorded profile (no silent reindex).

### Wave 4 — `petals-audio` (≈ old CF-792/793/800)

- **Goal:** preserve donor opt-in, identity pinning, security boundaries, compute donation/scheduling, same-model donor isolation, fail-closed unavailable; add governed audio-model settings (local Whisper, compatible remote Whisper, supported diarized providers such as GPT-4 diarization) without inventing unsupported local Pi audio behavior.
- **Design outputs:** Petals authorization/consent/scheduling test matrix (no bridge changes in early waves; donor rows never Pi-catalog capacity entries); canonical `AudioModelProfile` contract; interview + microphone + channel flows share one profile; capabilities + secrets + fallbacks explicit; local-only/optional-provider behavior explicit; no secrets in raw config payloads.
- **Verification:**
  ```bash
  uv run --project backend python -m pytest tests/petals_bridge/test_petals_bridge.py \
    tests/pi_production/test_same_model_donor_isolation.py \
    tests/pi_production/test_research_spine_donor_routing.py \
    tests/test_compute_registry_hardening.py tests/test_project_scope_contracts.py \
    tests/compute_cases/config.py tests/compute_cases/retries.py -q
  uv run --project backend python -m pytest tests/test_transcription.py tests/test_files.py \
    tests/test_integration_interview.py tests/pi_production/test_w3_research_spine.py \
    tests/test_research_validity_contract.py tests/test_synthetic_provisional_boundary.py -q
  python scripts/security_benchmark.py --fail-on-threshold
  ```
  (`test_research_spine_donor_routing.py` is a **new obligation created in this wave**, not a pre-existing anchor.)
- **Acceptance:** relay/browser donor with consent/health/project authorization is pinned to the donor, records route evidence, deterministic result; any missing admission condition → typed unavailable, never paid fallback; donor never selected as ordinary Pi capacity; local Whisper / remote Whisper / diarized / unsupported / missing-credential / low-ICR / ffmpeg-unavailable inputs behave explicitly, bounded, project-scoped, correctly marked `needs_review`/unavailable; raw source spans + provenance preserved; no transcript/tag reportable before gates. Mocked HTTP only — no live audio provider or model load.
- **Rollback:** disable bridge/Pi-petals mode; retain existing local Whisper path; audio profiles revert to local-only.

### Wave 5 — `qa-docs-vps` (≈ old CF-795/796/797/798/804/805 + DEC-2)

- **Goal:** final integration: living feature docs + manifests regenerated; deterministic Compose QA coverage for every accepted feature without weakening public QA isolation; security benchmark + broad focused suites; then VPS acceptance per the `vps` skill (§9), and cleanup of only initiative-owned disposable artifacts.
- **Design outputs:** regenerated living feature docs; `testing/feature_coverage.yml` + `qa/runtime_capabilities.json` obligations for all changed paths; VPS single-service acceptance Compose (§9.2); VPS runbook + rollback state.
- **Verification (public/testing-branch deterministic part):**
  ```bash
  python scripts/feature_docs.py --seed-missing --generate-site --check
  uv run --project backend python -m pytest tests/test_feature_docs.py tests/test_feature_obligations.py \
    tests/test_qa_stack_contract.py tests/test_qa_reset_seed.py tests/test_qa_artifacts.py \
    tests/test_synthetic_provisional_boundary.py tests/test_provider_contracts.py -q
  docker compose -f docker-compose.yml config --quiet
  for p in contract synthetic reset audit ui; do docker compose -f docker-compose.qa.yml --profile $p config --quiet; done
  docker compose -f docker-compose.qa.yml --profile live config --quiet   # render-only; live lane owner-gated
  ./scripts/istara-qa.sh render
  python scripts/check_feature_obligations.py --base origin/testing --head HEAD
  python scripts/check_integrity.py && python scripts/check_ci_governance.py && python scripts/check_test_harness.py
  python scripts/check_public_tree_clean.py --base origin/testing --head HEAD
  uv run --project backend python -m pytest tests/pi_benchmark/test_b1_contract.py -q
  uv run --project backend python -m pytest tests/pi_benchmark/test_live_driver.py -q --collect-only
  python scripts/security_benchmark.py --fail-on-threshold
  compass-forge gate before --summary && compass-forge gate after --summary   # 0 NEW failures attributable
  # VPS (owner-authorized; every remote command via the vps skill's vpsctl.py — C7):
  VPSCTL=~/.pi/agent/skills/vps/scripts/vpsctl.py
  python3 $VPSCTL preflight
  python3 $VPSCTL inventory
  python3 $VPSCTL verify-isolation && python3 $VPSCTL verify-exposure
  python3 $VPSCTL audit-verify && python3 $VPSCTL audit-anchor
  ```
- **Acceptance:** feature-doc parity + generated manifests/site green; every accepted feature has a deterministic contract lane; security benchmark pass; 0 new gate failures attributable to the wave; VPS: strict-profile proof (one internal network, one endpoint, no default route, no host/other-container reachability, exactly the allowed published port), firewall/DOCKER-USER evidence agrees with the approved port list, audit chain anchored, rollback available until owner accepts, only initiative-owned artifacts removed, `main` untouched.
- **Rollback:** VPS deployment identity + prior image digest preserved until post-deploy checks pass (§9.5); Compose/deps revert to prior wave state.

## 9. Isolated VPS acceptance and cleanup (replaces multivac — DEC-2, C1/C5/C7)

The managed VPS (`vps` skill) is the only staging-acceptance path for this run. `vpsctl.py` is **not** in this repo — every invocation uses `VPSCTL=~/.pi/agent/skills/vps/scripts/vpsctl.py`; never raw `ssh` or shell scripts; SSH identity `~/.ssh/id_ed25519_capi` with strict host-key checking.

### 9.1 Procedure (strict order)

1. **Preflight:** `python3 $VPSCTL preflight` — keychain-backed SSH identity, helper integrity, audit DB health. Never print key material.
2. **Inventory (read-only evidence):** `python3 $VPSCTL inventory` — observed Compose projects/containers and current public exposure. Existing workloads are inventory-only.
3. **Service creation:** Dokploy Docker Compose service from the repository using the strict single-workload profile (§9.2). No Dokploy Domain, proxy labels, external network, Docker socket, `network_mode: host`, privileged, or host PID/IPC. Secrets only in the Dokploy secret/environment UI.
4. **Preview before deploy:** reject any rendered Compose that adds a shared/proxy network or a second service.
5. **Deploy preserving identity:** capture current deployment identity + image digest as rollback target; deploy.
6. **Verify:** `verify-isolation` (one attached network, one endpoint, `Internal: true`, no default route, no host/other-container reachability) and `verify-exposure` with the documented approved port set (IPv4+IPv6).
7. **Firewall evidence:** check firewall before/after and the `DOCKER-USER` chain (published ports bypass ordinary rules). **No firewall change without owner approval** — escalate unexpected exposure; never remove a port until its owning workload is known.
8. **Audit:** `audit-verify` then `audit-anchor` (signs the chain head with the SSH identity). Report verified port set, image identity, isolation proof, firewall result, rollback state, and audit event ids — never secrets or raw output.

### 9.2 Strict single-workload Compose baseline (vps skill contract)

```yaml
services:
  app:
    image: <istara-acceptance-image>@sha256:<immutable-digest>
    restart: unless-stopped
    ports:
      - target: <app-port>
        published: "<owner-approved-host-port>"
        protocol: tcp
        mode: host
    networks: [workload]
    read_only: true
    tmpfs: [/tmp]
    security_opt: [no-new-privileges:true]
    cap_drop: [ALL]
    pids_limit: 256
    mem_limit: 512m
    cpus: 1.0
    healthcheck: { test: [CMD, /app/healthcheck], interval: 30s, timeout: 5s, retries: 3 }
networks:
  workload:
    driver: bridge
    internal: true
```

No `container_name`, host bind mounts, `extra_hosts`, or socket mounts; named volumes only if persistence is explicitly approved.

### 9.3 Single-service reality check (C5)

The production `docker-compose.yml` is 8-service. The strict profile permits exactly one service with inbound-only connectivity. The default acceptance target is a **dedicated single-service acceptance image** (minimal read-only bundle exercising the acceptance contract — healthcheck + one approved port), built on the testing branch. If the acceptance contract genuinely requires multi-container topology, a database, outbound API access, or a domain proxy: stop, describe the minimum connectivity graph, obtain written owner approval, and record the exception in the audit DB before any change. Never silently weaken isolation.

### 9.4 Cleanup

After acceptance: remove **only** initiative-owned disposable artifacts (this run's Compose service, its named volumes if created, rendered previews). Existing workloads, benchmark deployments, and the audit database are untouched. Record cleanup commands through `$VPSCTL ssh`.

### 9.5 Rollback

Until the owner accepts: preserve prior deployment identity/digest; re-deploy prior Compose on verification failure; record the event in the audit chain. No firewall rollback needed if no firewall change was made (the default).

## 10. Test ownership and coverage matrix

Extend existing tests; never create an unowned parallel suite. Gate rules `architecture_drift` and `test_ownership` are load-bearing: every new canonical model-management file must be listed in `testing/feature_coverage.yml` (or a reviewed mechanical exception); every behavior-changing file needs an owning test/doc obligation. Documents the code-graph gate rules name — `CHANGE_CHECKLIST.md`, `Tech.md`, `docs/features/content/agents/a2a/{architecture,researcher}.md`, `docs/features/content/chat/steering/architecture.md` — are updated in the same change.

| Surface | Existing anchors | New/changed obligations |
|---|---|---|
| Pi package/protocol | `pi-runtime/test/*.test.mjs`, `pi-runtime/PROTOCOL.md`, `test_engine_http_provider.py`, `test_runtime_hardening.py`, `test_protocol_version_per_frame.py` | exact version/lockfile provenance; no dependency drift; protocol v2 compatibility after upgrade |
| Canonical provider catalog | `test_model_provider_contract.py`, `test_pi_runtime_endpoints.py`, `test_endpoint_secrets.py` | identity tuple, aliases, capabilities, credential custody, duplicate handling |
| LLM Server compatibility | `test_llm_servers.py`, `test_settings_agentic_pi_endpoints.py`, simulation scenario 36 | idempotent mapping, deprecated adapter, blocked rows, rollback |
| Engine routing | `test_w1_agentic_contract.py`, `test_w1_dispatcher_authority.py`, `test_w1_usage_ledger.py`, `test_w6_engine_selection.py`, `test_w4_a2a_handlers.py` | both engines through canonical target; precedence; no fallback; one-row accounting |
| Count-to-zero | `scripts/pi_migration_inventory.py`, `test_count_to_zero.py`, `legacy_allowlist.yaml` | product remains 0; only documented permanent infrastructure entries |
| Embeddings | `test_w8_embeddings_gateway.py`, `test_w8_ux_parity.py`, `test_rag_resilience.py` | profile identity, dimension/dtype mismatch refusal, no cache writes on mismatch |
| Petals/compute | `tests/petals_bridge/test_petals_bridge.py`, donor isolation, `tests/compute_cases/*` | consent, project scope, exact node identity, typed 503, no paid fallback; **new** `test_research_spine_donor_routing.py` |
| Audio/research | `test_transcription.py`, `test_files.py`, `test_integration_interview.py`, research-spine tests | profile capability, diarization, ICR/review, raw evidence units/provenance |
| Migration/rollback | — (does not exist yet) | **new** `tests/pi_migration/test_model_management_migration.py`, `test_model_management_rollback.py` |
| Frontend/UI | `modelProviders.test.ts`, `modelCatalog.test.ts`, engine selector simulations | no duplicate options, explicit engine/model/endpoint distinction, accessibility |
| QA/docs | `test_feature_docs.py`, `test_feature_obligations.py`, QA stack/provisional/obligation tests | changed-path ownership, generated docs parity, provisional-only QA |
| Security | `test_security_benchmark.py`, `security/control_matrix.json` | triggered benchmark + control/evidence updates if controls change |

## 11. Documentation and manifest obligations

Update living docs in the same implementation initiative (dated historical plans stay immutable; write successor records when facts change):

- Architecture: `docs/architecture/agentic_core.md` (canonical identity/transport boundary, legacy adapter vs legacy infrastructure, route evidence); `docs/architecture/research-validity-contract.md` (only if spine-visible seams change); `docs/architecture/self-improvement-governance-contract.md` (only if self-improvement paths change).
- Feature pages at minimum: `settings/llm-servers`, `chat/model-controls`, `chat/audio`, `interviews/transcription`, `settings/compute-donation`, `compute/pool` (+ `agents/registry`, `agents/a2a` if engine metadata changes) — plus any new provider/credential/audio pages the feature inventory discovers.
- Repo docs: `README.md`, `README.pt-BR.md`, `DOCUMENTATION.md`, `TESTING.md`, `CHANGE_CHECKLIST.md`, `SYSTEM_CHANGE_MATRIX.md`, `testing/TESTING_STRATEGY.md` where contracts change.
- `testing/feature_coverage.yml` + `qa/runtime_capabilities.json` for all changed paths.
- Regenerate with `python scripts/feature_docs.py --seed-missing --generate-site --check` in the same change; attach output as CF evidence; never hand-edit generated site files or silently modify external repos.
- No private VPS host details, keys, or endpoint fingerprints in public docs or QA artifacts.

## 12. Security benchmark and review checklist

Mandatory on any auth/provider/secret/agentic/Petals/audio change: `python scripts/security_benchmark.py --fail-on-threshold`. Record the scorecard as CF command evidence; update `security/control_matrix.json` + `security/SECURITY_BENCHMARK.md` + `tests/test_security_benchmark.py` when a security control, evidence path, standard version, or trigger pattern changes.

Security reviewer must cover: credential source precedence/rotation; encryption context/version compatibility for migrated `api_key` values; SSRF/URL normalization + loopback/HTTPS policy for custom endpoints; OAuth redirect/token custody; admin/project authorization on catalog/credential/migration/Petals-consent/audio routes; enumeration + safe redaction in UI/API/telemetry/logs; no secrets in migration exports, Compose interpolation, QA artifacts, or CF evidence; worker private-pipe binding, protocol limits, retry/cost accounting, malformed-frame behavior; explicit engine selection never bypassing Research Spine route evidence; donor consent/project scope/same-model isolation/typed 503; audio upload size/type/scanner/temp-file cleanup, remote provider credentials, diarization privacy; no public VPS references, no firewall changes, no unrelated workload cleanup. Inherited gate failures are never suppressed silently: record baseline vs post-change comparison; either fix new failures or create an explicit, expiring, justified suppression under project policy.

## 13. Risks and mitigations (unified register)

| ID | Risk | Sev | Mitigation / detection | Rollback |
|---|---|---|---|---|
| R1 | Package update breaks worker protocol / structured contract | High | Pin exact versions; protocol v2 handshake + contract suites both sides; compatibility statement before bump | Restore prior pins/lockfiles/worker checkout |
| R2 | Duplicate model identity / split-brain | High | Provider-qualified ids + uniqueness constraints + collision tests; aliases provenance-only | Restore canonical mapping; source rows intact |
| R3 | Lost/invalid API key during migration | High | In-memory decrypt/re-encrypt; credential status matrix; redaction audit; no plaintext export | Keep source encrypted field + compat reference |
| R4 | Silent cross-engine fallback | High | Typed per-engine errors; one-ledger-row accounting; dispatcher contract tests | Explicit mode revert (§7.4) |
| R5 | Embedding/vector drift corrupts retrieval | High | Profile persisted + startup probe; block mismatch before cache/write | Restore prior profile; vectors keyed to recorded profile; reindex only as versioned migration |
| R6 | Donor boundary erosion / paid fallback hides failure | High | No early bridge changes; consent+pin+503 tests; isolation invariant green | Disable bridge mode; donor registry unchanged |
| R7 | Compatibility adapter becomes second source of truth | High | Canonical-only writes; count-to-zero ratchet + allowlist audit per wave | Re-enable read adapter; never delete rows |
| R8 | VPS isolation/exposure defect | High | Strict profile + preview rejection + verify-isolation/exposure + firewall/`DOCKER-USER` evidence + audit-anchor; no firewall change without owner approval | Prior deployment identity/digest retained; redeploy prior Compose |
| R9 | VPS credential/exposure leak | High | Secrets only in Dokploy secret UI; `vpsctl.py` audit chain; no secrets in args/history/chat | Revoke + rotate; audit-verify chain |
| R10 | QA false confidence | Med | Contract stub labeled non-quality; synthetic provisional guard; live lane owner-gated; fresh disposable DBs | Stop QA project; retain evidence; never promote synthetic artifacts |
| R11 | Inherited gate debt masks migration findings | Med | Baseline recorded (S4); per-wave before/after diff; 0-new-failures rule | — |
| R12 | Audio provider unsupported/private behavior | Med | Capability contract + local/mocked tests + `needs_review`; no implicit fallback | Return unavailable; retain local Whisper path |
| R13 | Docs/generated drift | Med | Feature obligation classifier + feature-doc regeneration in same task | Block acceptance until docs/manifests regenerated |
| R14 | Contaminated persistent-SQLite evidence | Med | Fresh disposable databases for migration verification | Re-run on clean DB |

## 14. Definition of Ready / Done and owner gates

**Ready for implementation:**
- The three drafts are reconciled into one MECE master plan and **owner-approved at the explicit plan gate**; the conductor records the gate and stops.
- Exact canonical identity, credential, migration-state, engine-transport, embedding-profile, audio-profile, and Petals boundaries are accepted.
- CF work orders name dependencies, changed-path ownership, tests, docs, rollback, and gates for each wave.
- Latest Pi release re-checked passively at dependency-update execution time; no live LLM/model load required.
- Baseline gate output and known inherited failures attached; no implementation begins while the plan gate is pending.

**Done for the initiative:**
- All required waves have green task command evidence and post-change gate evidence, or an explicit owner-approved residual risk.
- Canonical model/endpoint/credential behavior proven without duplicate identity semantics or secret leakage.
- Both engines remain explicitly selectable and independently fail closed, with one usage/route record per dispatch.
- LLM Server migration idempotent, reversible, observed, deprecated; no row deleted without the separate removal gate.
- Embedding profile, Petals bridge, audio/transcription, Research Spine, UI, QA/Compose, security benchmark, docs/manifests, and test ownership obligations complete.
- VPS acceptance (if authorized/required): strict-profile isolation/exposure proof, firewall evidence, audit-anchor, cleanup of only initiative-owned artifacts; otherwise explicitly marked blocked/advisory and public QA stays green.
- Lifecycle status/ledger, CF evidence, findings register, and final summary accurately describe the result. No implementation stage claims completion from a plan-only artifact.

**Owner gates:** plan gate (after consensus freeze — mandatory stop), S2→S3 and S4→S5 transitions, VPS authorization, firewall/VPS exposure changes, ship. Never merge/push/PR from any worker stage.

## 15. Coverage matrix (requirement → this master plan)

| Requirement (task instructions + manifest) | Section | Drafts substantiating |
|---|---|---|
| Legacy LLM Server storage/routing/encryption consumers | §2, §5.2, §7, Wave 2 | A §2/§6, B §2/V9, C §2 |
| Both agentic engines, explicit selection, no duplicate semantics | §4 I2, §5.2/§5.4, Wave 2 | A §5.4, B §4.4/V3, C §3 |
| Pi provider/model catalog + endpoint resolver | §5.1–5.3, Wave 1 | A §5, B §4, C §3 |
| Embeddings/vector-space invariant | §5.5, Wave 3 | A §5.5, B §4.5, C §3 |
| Petals donor bridge | §5.6, Wave 4 | A §5.6, B §4.6, C §3 |
| Audio/transcription flows | §5.7, Wave 4 | A §5.7, B §4.7, C §3 |
| UI contracts | §5.4, §10, Wave 3 | A §2.2/§8 W3, B §7 W3/V16, C §2/§5 W3 |
| Testing-branch Docker QA | §4 I9, Wave 5 | A §8 W5, B §7 W5/V11, C §5–6 |
| VPS deployment per vps skill (preflight/inventory/verify-isolation/verify-exposure/audit-anchor, no firewall changes w/o owner approval) | §9 | B §9 (authoritative), A C1/C5/C7, C §5–6 |
| Reversible staged LLM Server retirement | §6 | A §7, B §5, C §4 |
| Exact data/secret migration and rollback | §7 | A §6, B §6, C §4 |
| Latest verified Pi dependency update | §2 S1/S2, Wave 1, C13 | A C4, B V1/V2, C §2 |
| No duplicate model identity semantics | §5.1 rules, §10, Wave 1 acceptance | A §5.1, B §4.1, C §3 |
| Feature-flag/deprecation/removal criteria | §6.1–6.4 | A §7, B §5, C §4 |
| Per-wave acceptance and commands | §8 | B §7 (commands), A §8 (acceptance), C §5/§6 |
| Documentation/manifest obligations | §11 | A §10, B §10, C §7 |
| Security benchmark coverage | §12, per-wave commands | A §11, B §10, C §7 |
| Isolated VPS deployment/cleanup | §9.4–9.5 | B §9, A §8 W5, C §5 |
| Everything stays on testing branch; stop at owner approval gate | §1, §14 | A §1/§13, B §12, C §1/§4 |

## 16. Handoff note

This is the slot-B MECE master-plan candidate at the authoritative `plan_file` for the synthesis round (`0bb85df72bbe6604f51a`); the slot-C synthesis candidate exists in parallel (`master-c.md`). The next stage — the consensus **vote** — reads exactly the two master candidates supplied in its work order and votes for one slot (self-votes forbidden). After the winning candidate is frozen, the conductor records the plan gate and **stops for owner approval**; implementation tasks are generated from the approved plan only. No source implementation, lifecycle-plan edit, Docker/VPS start, live provider call, model load, merge, push, or PR is authorized from this stage.
