# Independent S1 Draft (Slot B, repaired) — Istara Pi Model-Management Migration, 2026-08-22 run

**Task:** `ISTARA-PI-MODEL-MIGRATION-20260822-REPLAN-B-r1` (CF task id 5, "Consensus draft repair b")
**Role:** `istara-pi-model-migration-20260822-architect-b`
**Spec:** `CF-SPEC-1` (this run; the old `CF-SPEC-59` / `CF-787…CF-805` graph is frozen history)
**Pipeline run:** `ISTARA-PI-MODEL-MIGRATION-20260822` · strict-wave manifest SHA-256 `b9c8ff0ca1c0521fff18e27d3caf53e11fac89c6fb9a44e1656688ac1cf5a8fd`
**Planning phase:** `draft` — independent, buildable S1 plan only. No implementation, no lifecycle-plan edits, no vote in this phase.
**Repair provenance:** this is a draft **repair**. The prior slot-B draft (`ISTARA-PI-MODEL-MIGRATION-20260822-PLAN-B`, ledger L-3) landed at the misnamed path `docs/build-stream/plans/istara-pi-model-management-migration-20260822-plan-b.md`, which the synthesis phase cannot consume. This repair re-lands the corrected draft at the task's authoritative `plan_file` (this file) and removes the misnamed duplicate in the same commit — mirroring the slot-A repair (`REPLAN-A-r1`, ledger L-4). Every current-tree fact was re-verified at repair time (2026-08-22); correction **C7** is added.
**Branch/worktree:** `conductor/istara-pi-model-management-migration-20260822` (base `origin/testing@15260a78df6637c2d1981c74683525cb75ab1a22`). Everything stays on the testing lineage; never `main`.

---

## 1. Executive recommendation

Make Pi the **single canonical model-management authority** (provider families, model
identity, endpoint identity, capability metadata, secret references, and resolution)
while Istara keeps **two explicitly selectable, permanently supported agentic engines**
(`pi` and `legacy`) whose transports differ but whose model identity, route evidence,
accounting, and vector space are governed by one canonical plane.

The legacy `LLMServer` row plane (storage + CRUD + live registration + encryption)
becomes a **reversible compatibility adapter and migration source**, not a second
catalog. It retires in observable stages — *legacy-compat → shadow → pi-primary →
deprecated-adapter → retired* — each transition gated by acceptance evidence,
a performed rollback drill, and owner approval at the major gates. No legacy row,
credential, vector, donor consent, or audit record is deleted merely because a
canonical record now exists; physical deletion is a separate, later, owner-approved
action after all removal criteria hold.

The 2026-08-22 run replaces the retired multivac staging path with **isolated
acceptance on the managed VPS per the `vps` skill** (Dokploy strict single-workload
profile, `vpsctl.py` preflight → inventory → deploy → verify-isolation →
verify-exposure → audit-anchor; no firewall change without owner approval).

## 2. What I independently verified in this tree (2026-08-22)

Every "current" fact below was re-checked against this worktree at planning time,
and **re-checked again at repair time** (this file). The carried-forward 2026-08-18
drafts (A/B/C) were inputs; where they disagree with the current tree, this plan
extends/corrects rather than discards.

| # | Verified fact (2026-08-22) | Command / source |
|---|---|---|
| V1 | Upstream latest `@earendil-works/pi-agent-core` = **0.84.2**, `@earendil-works/pi-ai` = **0.84.2** (passive registry query, no model probes) | `npm view … version` |
| V2 | `pi-runtime/package.json` + lockfile pin **0.83.0**; `labs/pi-replacement/package.json` + lockfile pin **0.80.10** (lab has silently diverged from runtime) | read package files |
| V3 | Engine precedence (dispatcher docstring + code): per-call `engine=` → header `x-istara-agent-engine` → project `agentic_engine` → `settings.agentic_engine_default` (**"legacy"**, config.py:315). No silent fallback either way. | `backend/app/core/agentic/dispatcher.py` |
| V4 | Count-to-zero ratchet green: `EXPECTED_PRODUCT_SITES = 0`, **3 passed** | `uv run --project backend python -m pytest tests/pi_migration/test_count_to_zero.py -q` |
| V5 | Gate baseline (this run): `gate before` = fail, **30 failures** (`secret_flow`, `unexpected_large_files`), **0 new, 0 actionable**, drift route=4/type=2, warnings=188. (Carried plan C's "80 inherited failures" is stale.) | `compass-forge gate before --summary` |
| V6 | Security benchmark baseline: **28/28 pass, 100.0%**, `status: pass` | `python3 scripts/security_benchmark.py --fail-on-threshold` |
| V7 | Feature-doc parity green: 86 features, 224 site artifacts, 0 seeded | `python3 scripts/feature_docs.py --seed-missing --generate-site --check` |
| V8 | Environment prerequisites: backend test env needs `uv sync --extra dev` (done at planning); `pi-runtime/node_modules` is **absent** → worker-backed tests (e.g. `test_w1_agentic_contract.py`) fail on worker handshake until `npm ci` runs. | filesystem + pytest run |
| V9 | All legacy/Pi seams exist as described in carried draft C §2: `models/llm_server.py`, `routes/llm_servers.py`, `llm_router.py`, `field_encryption.py`, `endpoint_security.py`, `pi_runtime/{endpoints,model_manager,engine,embeddings_gateway}.py`, `agentic/{dispatcher,legacy}.py`, `petals_bridge.py`, `transcription.py`, `compute_registry.py` | file inventory |
| V10 | Pi endpoint config field is `pi_api_endpoints: list[PiApiEndpoint]` (config.py:304) with `DEFAULT_ENDPOINT_ID="pi-deepseek-default"` (endpoints.py:23). Carried plan A's "`PI_API_ENDPOINTS` JSON settings state" is an incorrect name — corrected here. | read config/endpoints |
| V11 | `docker-compose.yml` is an **8-service** topology (ollama, postgres, backend, frontend, caddy, relay, otel-collector, jaeger); `docker-compose.qa.yml` profiles: contract/synthetic/reset/audit/live/ui; `qa/runtime_capabilities.json`, `testing/feature_coverage.yml`, scenario `79-engine-selector.mjs` exist | file inventory |
| V12 | `vpsctl.py` lives in the **vps skill**, not this repo: `~/.pi/agent/skills/vps/scripts/vpsctl.py`; exposes exactly `preflight, inventory, audit-verify, audit-anchor, verify-isolation, verify-exposure, ssh`; strict profile = **one service**, project-local `internal: true` bridge, one published port, no proxy/Domain/external network/socket/privileged/host namespace, read_only + cap_drop ALL | vps SKILL.md + `--help` (repair re-check) |
| V13 | Test anchors verified present: `test_pi_runtime_endpoints`, `test_model_provider_contract`, `test_field_encryption`, `test_llm_servers`, `test_settings_agentic_pi_endpoints`, `test_transcription`, `test_research_validity_contract`, `test_synthetic_provisional_boundary`, `test_feature_docs`, `test_feature_obligations`, `test_qa_reset_seed`, `test_qa_stack_contract`, `test_security_benchmark`, `pi_production/test_{endpoint_secrets,runtime_hardening,w1_agentic_contract,w1_dispatcher_authority,w1_usage_ledger,w1_realpath_accounting,w6_engine_selection,w8_embeddings_gateway,w8_ux_parity,engine_http_provider,seams_fail_closed,same_model_donor_isolation,w3_research_spine}`, `petals_bridge/test_petals_bridge`, `pi_migration/__init__`, `compute_cases/{config,routing,retries,status_contracts}`, `pi_benchmark/{budget_ledger,test_b1_contract,test_live_driver,test_runner}`, `test_project_scope_contracts`, `test_compute_registry_hardening` | file inventory (repair re-check: all present) |
| V14 | **Not yet existing** (obligations to create in later waves, never claimed as green today): `tests/pi_production/test_research_spine_donor_routing.py`, `tests/pi_migration/test_model_management_migration.py`, `tests/pi_migration/test_model_management_rollback.py` | file inventory (repair re-check: all absent) |
| V15 | Repo QA/governance scripts present and usable in later waves: `scripts/istara-qa.sh`, `scripts/check_feature_obligations.py`, `scripts/check_integrity.py`, `scripts/check_ci_governance.py`, `scripts/check_test_harness.py`, `scripts/check_public_tree_clean.py`; extra test anchors `tests/test_qa_artifacts.py`, `tests/test_provider_contracts.py` present. `scripts/multivac_*` and `tests/llm_servers.py` do **not** exist (do not cite them; multivac is retired, C1). | file inventory (repair re-check) |
| V16 | Frontend anchor paths: `frontend/src/lib/modelCatalog.ts` and `frontend/src/components/settings/ProjectSettingsView.tsx` (not `frontend/src/components/ProjectSettingsView.tsx`). | file inventory (repair re-check) |

### Corrections this draft makes to the carried 2026-08-18 drafts (and repair deltas)

- **C1 — Multivac is retired.** DEC-2 replaces multivac staging with the managed VPS
  (`vps` skill). All carried-draft multivac sections (§8/§11/risk rows in A/B/C) are
  replaced by the VPS acceptance + cleanup procedure in §9 here. No multivac commands
  remain anywhere in the 2026-08-22 plan.
- **C2 — CF task graph changed.** Carried drafts map waves to `CF-787…CF-805`
  (CF-SPEC-59). This run's manifest defines **six waves**: `foundation` (this planning
  wave), `pi-catalog-secrets`, `compat-routing`, `embeddings-controls`,
  `petals-audio`, `qa-docs-vps`. Implementation CF tasks are generated at owner
  approval from CF-SPEC-1; the wave mapping in §8 uses the new manifest ids, with the
  old-task mapping retained only as a scope checklist.
- **C3 — Baseline numbers refreshed** (V5–V7 above): 30 gate failures / 0 new / 0
  actionable; security benchmark 100%; feature-doc parity green.
- **C4 — Settings field name corrected** (`pi_api_endpoints`, V10).
- **C5 — VPS single-workload constraint is load-bearing.** The full 8-service
  `docker-compose.yml` does not fit the strict single-workload profile. §9 defines a
  dedicated single-service acceptance Compose; any multi-service exception requires
  the owner's written approval with the minimum connectivity graph (§9.3).
- **C6 — Environment prerequisites made explicit** (V8): `uv sync --extra dev` and
  `cd pi-runtime && npm ci` are recorded as wave-0/1 environment steps, and
  worker-backed tests are not run until the pin installs.
- **C7 — `vpsctl.py` is not in this repo (repair correction).** It lives in the vps
  skill at `~/.pi/agent/skills/vps/scripts/vpsctl.py`. Every VPS command in this plan
  runs it from the skill path (`VPSCTL=~/.pi/agent/skills/vps/scripts/vpsctl.py`;
  subcommands re-verified at repair time: `preflight, inventory, audit-verify,
  audit-anchor, verify-isolation, verify-exposure, ssh`). The pre-repair slot-B draft
  cited `scripts/vpsctl.py`; that is corrected throughout (§7 wave 5, §9).

## 3. Scope, non-goals, and invariants

### In scope

Legacy LLM Server storage/routing/encryption consumers; both agentic engines; Pi
provider/model catalog and endpoint resolver; embeddings/vector-space invariant;
Petals donor bridge; audio/transcription flows; UI contracts; testing-branch Docker
QA automation; VPS acceptance + cleanup per the `vps` skill; exact data/secret
migration + rollback; latest verified Pi dependency update; duplicate-identity
elimination; feature-flag/deprecation/removal criteria; per-wave acceptance +
commands; documentation/manifest obligations; security benchmark coverage.

### Non-goals (this planning stage and, unless separately authorized, later stages)

- No implementation in this stage. No merge/push/PR (conductor ship stage owns it).
- No live backend/frontend servers, no model loading, no live completion probes;
  passive status/discovery and registry queries only; at most one owner-authorized
  bounded target on live QA lanes.
- No mutation of `LLMs/` or `Model_Finetuning/`; no deletion of legacy transport,
  `ComputeRegistry`, local Ollama/LM Studio provisioning, donor relay/browser
  transport, or the permanent legacy executor.
- No firewall change on the VPS without owner approval; no mutation of unrelated
  Docker workloads; no public exposure of private host/tunnel details.
- No treating synthetic QA results, raw tool success, or comparative model prose as
  research evidence (Research Spine contract).

### Invariants that never regress (each mapped to its primary proof)

| # | Invariant | Primary proof (exists today unless marked new) |
|---|---|---|
| I1 | Pi/runtime isolation: `pi_runtime` never imports/mutates `ComputeRegistry`; Pi resolution never donor-scores | `tests/pi_production/test_same_model_donor_isolation.py` |
| I2 | Explicit dual-engine choice; precedence V3 stable; selected-engine failure never silently switches engines | `test_w1_agentic_contract.py`, `test_w1_dispatcher_authority.py` |
| I3 | One identity plane: provider-qualified `model_id` ≠ stable `endpoint_id`; legacy ids are provenance aliases only; no duplicate identity semantics | `test_model_provider_contract.py` + **new** migration catalog contract tests (W2) |
| I4 | Secret safety: plaintext credentials only in short-lived in-memory binding; no logs/responses/docs/QA artifacts/telemetry | `test_endpoint_secrets.py`, `test_field_encryption.py`, security benchmark |
| I5 | Vector-space invariance: chat-engine/endpoint changes cannot silently alter embedding model/dimension/dtype/normalization; mismatch blocks before vector/cache writes | `test_w8_embeddings_gateway.py` |
| I6 | Donor security: consent + health + project authorization + exact node pin; unavailable ⇒ typed 503; no paid fallback; no donor as ordinary Pi capacity | `tests/petals_bridge/test_petals_bridge.py`, donor-isolation test |
| I7 | Research Spine: source spans → evidence units → coding → reliability → reconciliation → review → Done → report; candidate/provisional outputs never reportable | `test_research_validity_contract.py`, `test_synthetic_provisional_boundary.py` |
| I8 | Reversibility: every source row has mapping/status + restorable snapshot before write/cutover; rollback is a documented switch, not an exception handler | **new** `tests/pi_migration/test_model_management_{migration,rollback}.py` (W2/W3) |
| I9 | QA isolation: unique `istara-qa-<run-id>` projects, internal networks, deterministic provider stub, live lane owner-gated | `test_qa_stack_contract.py`, `test_qa_reset_seed.py` |
| I10 | VPS isolation: strict single-workload profile only; proof of `Internal: true`, one endpoint, no default route, no host/other-container reachability, exact approved port set | `vpsctl.py verify-isolation/verify-exposure` + firewall/`DOCKER-USER` evidence (W5) |

## 4. Target architecture

### 4.1 Canonical identity model (semantic split is load-bearing; names adapt to repo conventions)

```text
CanonicalModel    model_id (provider-qualified, normalized — never a display string)
                  provider_family | canonical_name | aliases[] (provenance-attached)
CanonicalEndpoint endpoint_id (stable route identity, always distinct from model_id)
                  model_id | transport: pi_http | legacy_registry | local_lifecycle |
                            petals_bridge | audio_adapter
                  endpoint_kind: cloud | custom | local | petals | audio
                  nonsecret connection metadata + capability profile
                  credential_ref (opaque) | legacy_source_id (nullable, provenance only)
                  migration_state: unmapped|mapped|credential_validated|shadow_verified|
                                   pi_primary|legacy_deprecated|retired|blocked(reason)
CredentialRef     credential_ref (opaque stable name) | kind: keychain|encrypted_db|
                  environment|oauth | status: present|missing|invalid|rotation_required
EmbeddingProfile  profile_id | model identity | dimension | dtype | normalization |
                  version | health
AudioModelProfile profile_id | provider_family | model_id | endpoint_id | credential_ref
                  local|remote mode | language policy | diarization support |
                  speaker-count policy | confidence/human-review threshold
```

Rules: two providers serving the same visible model name remain distinct canonical
models unless an explicit alias mapping proves equivalence; capability metadata is
attached, never inferred from names; unknown capability fails closed when required;
base URLs/hosts/route ids never appear in public docs, QA artifacts, or normal
telemetry; admin views return redacted metadata + `has_credential` only.

### 4.2 Resolver and transport boundary

One canonical resolution request — `resolve(project_id, engine, model_id?,
endpoint_id?, purpose, capabilities?, embedding_profile_id?) -> ResolvedModelTarget`
(canonical model id, endpoint id, transport class, safe capabilities, credential
reference, route-evidence fields; never plaintext credentials).

- `PiModelManager` becomes the authoritative catalog/resolver (exact identity,
  capability admission, migration projection, weakref invalidation for live-DB
  projections — the existing three-source catalog is reorganized, not discarded).
- `PiExecutionService` consumes only `transport=pi_http` targets and binds secrets
  only on the private worker pipe.
- The legacy executor stays a permanent, byte-compatible **transport adapter**
  consuming `legacy_registry`/`local_lifecycle` targets; it never manufactures a
  second catalog.
- Petals: explicit `transport=petals_bridge`, `pi-petals-<node_id>` identity, bridge
  admission required, exact donor pin, route stamp; never a capacity candidate.
- Audio: `transport=audio_adapter` with explicit capability contract; binary audio
  never routes through the text Pi worker unless a separately verified provider API
  supports it.
- Every dispatcher verb (`chat_turn`, `completion`, `structured`, `ensemble`,
  `embed`, `react`) keeps one usage-ledger row per dispatch, including typed
  resolution failures; no cross-engine fallback.

### 4.3 Provider classes and secret custody

Explicit classes: cloud OpenAI-compatible; Anthropic-compatible; OAuth (Keychain/
encrypted custody, short-lived in-memory tokens); API key (Keychain/env/encrypted DB);
custom/local (normalized loopback or approved HTTPS, capability probe metadata; local
Ollama/LM Studio lifecycle separate from cloud credentials); audio/Whisper/diarization
(never auto-promoted to a chat provider). The migration service may read legacy
encrypted `LLMServer.api_key` only in memory, immediately re-encrypting/externalizing;
manifests store credential reference + kind + presence + nonsecret checksum — never
plaintext or reusable fingerprints.

### 4.4 Engine selection and rollback (preserves V3 exactly)

Per-call → header → project → global default → canonical target resolution for the
selected engine. A selected `pi` target with missing credentials/unsupported
capability/worker failure is a failed Pi invocation (typed error + ledger row) — no
legacy fallthrough, and symmetrically no Pi fallthrough for `legacy`. Rollback =
explicit switch (see §6.4), never an implicit exception path.

### 4.5 Embeddings

One authoritative `EmbeddingProfile` for both engines; engine-specific adapters may
differ in transport but must produce identical dimension/dtype/model/normalization.
Mismatch blocks startup/engine switching and cache writes. Existing vectors stay tied
to their recorded profile version; a deliberate profile change is a new version with
a bounded re-embed job + dual-read/reindex evidence + explicit invalidation. Chat
endpoint changes never mutate the embedding profile; UI separates chat-model controls
from embedding-profile controls and shows the active profile identity safely. The Pi
gateway keeps exactly one dispatcher-owned usage row (no double accounting).

### 4.6 Petals

Keep `petals_bridge.py` outside `pi_runtime`; require `source ∈ {relay,browser}`,
`pi_served=true`, health, project authorization, exact node pin, route stamp.
Unavailable/unconsented/unhealthy/unauthorized ⇒ typed 503, no paid fallback. Donor
identity visible to audit without prompts/URLs/secrets. No early-wave bridge changes;
W4 adds authorization/consent/scheduling tests and keeps the isolation invariant
green.

### 4.7 Audio and transcription

Unified `AudioModelProfile` contract consumed by interview uploads, microphone chat,
and channel audio, preserving project authorization and source provenance.
`local_whisper` keeps the existing local loader + ffmpeg boundary (model size
validated against local capability); `remote_whisper`/`remote_diarization` are opt-in
adapters with capability metadata, credential custody, bounded size/timeouts, redacted
errors, deterministic mocked contract tests. No configured audio profile ⇒ typed
unavailable — never a silent text-chat fallback. Transcripts remain candidate/
provisional source material until raw audio spans/segments, coding, reliability,
reconciliation, and human review accept them; ICR failure stays `needs_review`.

## 5. Reversible retirement state machine

```text
S0 legacy-authoritative  (today)                 S4 deprecated-adapter (warnings, compat reads)
S1 pi-authoritative catalog + secrets            S5 retired (runtime use off; archival, not deletion)
S2 dual-engine execution (both explicit)         any state -> blocked(reason)
S3 pi-preferred + legacy compatibility-only      S3/S4 -> rollback_ready -> legacy_compat
```

**Transition rule:** every S_i → S_i+1 requires (a) that wave's acceptance commands
green, (b) `gate after` with **0 new** failures attributable to the wave (inherited
baseline V5 tracked separately), (c) reviewer `review_verdict` pass, (d) performed
rollback drill evidence for the S2→S3 and S3→S4 transitions, (e) owner approval
before S2→S3 and S4→S5.

**Removal criteria (all must hold with evidence before S5):** count-to-zero ratchet
green + allowlist audit clean; vector invariant green on both engines; Petals
security controls intact; audio flows on canonical config; UI offers no legacy-only
model CRUD without deprecation notice; ≥1 performed staging-equivalent rollback
drill; security benchmark passes **with** the removal; three consecutive
deterministic full-suite runs with no new migration failures; docs/manifests
regenerated. Physical row deletion is a separate later owner-approved action.

### Feature-flag / deprecation model (one rollout mode + existing engine selectors)

```text
PI_MODEL_MANAGEMENT_MODE = legacy_compat | shadow | pi_primary | deprecated_adapter | retired
```

Defaults: `legacy_compat` on existing installs; `agentic_engine_default` stays
`"legacy"` until the owner flips it; per-project `agentic_engine` remains an explicit
override cleared on rollback; `llmserver_compat_mode` on through W2, off per-surface
after the S4 criteria; `petals_bridge_enabled` semantics unchanged. Every flag flip
is a code change with its own task, evidence, and rollback switch. Deprecation =
stable header + safe diagnostic reason on legacy CRUD/compat paths; writes go
canonical or fail closed (never create an untracked second source of truth); local
lifecycle and donor APIs are transport infrastructure and are **not** deprecated —
only the model-management ownership semantics are.

## 6. Data/secret migration and rollback

### 6.1 Preflight (immutable evidence, before any write/cutover)

1. Capture branch/base commit, schema revision, package versions + lockfile hashes,
   `gate before` output.
2. Redacted inventory (`scripts/pi_migration_inventory.py --json`) of static Pi
   settings, `LLMServer` rows, relay/browser rows, local provider settings, project
   engine selections, embedding metadata — source ids + mapping reasons, never
   secret values or private endpoints.
3. Encrypted DB backup/snapshot (gitignored disposable path, owner-approved
   retention/restore proof) + pre-change Compose definition copy.
4. Credential presence/status dry-run only — no live completions, no model loads, no
   printed secrets.
5. Deterministic `migration_id` + schema version + source checksum + tool version;
   rerun with the same checksum is a no-op.

### 6.2 Deterministic mapping (per non-relay LLM Server row)

Normalize provider family + URL via `endpoint_security.py` → parse capability JSON
without inventing model names (absent model = explicit `unknown/default` needing
validation) → resolve/create one provider-qualified `model_id` → resolve/create
exactly one `endpoint_id` bound to the stable source row (`legacy_source_id`,
priority, health summary, capability provenance preserved) → credential reference
(in-memory decrypt → re-encrypt via canonical custody or bind the source encrypted
field as a compatibility reference; Keychain service/account references copied
without values; local no-key rows use a nonsecret local mode) → mark
`mapped|credential_validated|blocked|legacy_only` with actionable reason → store
redacted mapping result. Relay/browser rows are **never** migrated into ordinary Pi
endpoints (donor plane only). Unsupported/malformed rows are preserved and visible,
never dropped.

### 6.3 Staged cutover

`mapped` (no runtime cutover) → `credential_validated` (in-memory secret resolution
+ capability validity; no completion call) → `shadow_verified` (read-only resolution
+ metadata parity on a canary project/contract stub; no double-sending user research
content) → `pi_primary` (opt-in project/route, legacy data still readable) →
`legacy_deprecated` (canonical writes only, read compat + deprecation metadata) →
`retired` (only after §5 removal criteria + owner gate; runtime use disabled first,
physical deletion separately).

### 6.4 Rollback (explicit operation, per-wave switches)

1. Stop the staged QA/VPS acceptance workload before data changes.
2. `PI_MODEL_MANAGEMENT_MODE=legacy_compat`; `agentic_engine_default=legacy`; clear
   per-project `agentic_engine` overrides; re-enable `llmserver_compat_mode`.
3. Restore canonical mapping/status snapshot if mapping corrupt (keep the failed
   migration report).
4. Restore encrypted DB/config snapshot only when additive recovery fails; verify
   schema downgrade compatibility first.
5. Restore prior checkout/Compose and re-run: legacy routing, embedding dimension,
   donor isolation, source-evidence contract suites.
6. Prove no source row / engine setting / vector / donor consent / audit row was
   lost; record rollback command + evidence; retain the migration artifact.

No step requires deleting a source row to validate success; unmappable rows stay
`legacy_only`/`blocked` with the adapter enabled.

## 7. Wave plan (mapped to the 2026-08-22 strict-wave manifest)

The manifest defines: `foundation` (this planning wave) then five implementation
waves. Old-run scope anchors (CF-787…CF-805) are retained in parentheses as a
checklist only; the actual CF tasks for implementation are generated at owner
approval. **Environment prerequisite for all backend runs:** `uv run --project
backend …`; for all worker-backed tests: `cd pi-runtime && npm ci` first (V8).
**VPS commands run `vpsctl.py` from the vps skill path, never from this repo (C7).**

### Wave 0 — `foundation` (planning only; this stage)

- **Goal:** freeze the boundary, record baselines, produce the architect consensus
  plan, stop at the owner approval gate. No code changes.
- **Acceptance:** (1) verified version/provenance record for upstream Pi packages
  (V1/V2); (2) baseline gate/security/docs evidence captured (V5–V7); (3) ratchet
  green (V4); (4) the three drafts + consensus master plan cover §3 scope; (5) no
  implementation task is released before owner approval.
- **Commands (already run as this stage's evidence):**
  ```bash
  compass-forge status --target <wt> && compass-forge next --target <wt>
  compass-forge gate before --target <wt> --summary
  npm view @earendil-works/pi-agent-core version ; npm view @earendil-works/pi-ai version
  uv run --project backend python -m pytest tests/pi_migration/test_count_to_zero.py -q
  python3 scripts/security_benchmark.py --fail-on-threshold
  python3 scripts/feature_docs.py --seed-missing --generate-site --check
  ```

### Wave 1 — `pi-catalog-secrets` (≈ old CF-787 + CF-788 + CF-801)

- **Scope:** update both pinned Pi package surfaces to the **latest verified
  compatible** release (0.84.2 as of V1, re-checked passively immediately before the
  change); record exact version, registry output, lockfile resolution, and a
  protocol-compatibility statement against `pi-runtime/PROTOCOL.md` (protocol v2,
  worker entry, structured-output forced-tool, cost ceilings, retry discipline,
  fail-closed terminals); align `labs/pi-replacement` to the same verified release or
  record an explicit, reviewed divergence rationale. Add the canonical catalog +
  credential custody (§4.1–4.3) with duplicate-identity collision guards, endpoint
  capabilities, OAuth/API-key/custom/local classes, and encrypted secret custody
  validated against standalone Pi. **No LLM Server deletion.**
- **Design outputs:** dependency/version acceptance record; canonical identity
  schema + migration; secret custody translation (Fernet → Keychain/env/encrypted-DB
  references) with redaction audit; W2 snapshot tooling stubs.
- **Exact verification:**
  ```bash
  cd pi-runtime && npm ci && npm test && cd ..
  cd labs/pi-replacement && npm ci && npm run validate && cd ..
  uv run --project backend python -m pytest tests/test_model_provider_contract.py \
    tests/test_pi_runtime_endpoints.py tests/test_field_encryption.py \
    tests/pi_production/test_endpoint_secrets.py tests/pi_production/test_runtime_hardening.py -q
  uv run --project backend python -m pytest tests/pi_production/test_w1_agentic_contract.py -q   # worker-backed; npm ci first
  python scripts/pi_migration_inventory.py --json
  uv run --project backend python -m pytest tests/pi_migration/test_count_to_zero.py -q
  python scripts/security_benchmark.py --fail-on-threshold
  python scripts/feature_docs.py --seed-missing --generate-site --check
  compass-forge gate before --summary && compass-forge gate after --summary   # 0 new failures
  ```
- **Acceptance:** same-model-different-endpoint canonicalization proven (one
  `model_id`, distinct `endpoint_id`s); no secret in logs/responses/telemetry/
  artifacts; lockfiles reproducible; protocol contract green; ratchet still 0;
  inherited (V5) vs new failures separated; `LLMServer` rows untouched.
- **Rollback:** restore prior package pins/lockfiles/worker checkout; disable
  canonical catalog via `PI_MODEL_MANAGEMENT_MODE=legacy_compat`.

### Wave 2 — `compat-routing` (≈ old CF-789 + CF-790 + CF-794 + CF-804)

- **Scope:** make Pi the canonical resolver for **both** engines; idempotent
  migration/state machine (§6) with per-row lineage + audit log + switchboard
  (`agentic_engine_default`, per-project `agentic_engine`, `llmserver_compat_mode`,
  `PI_MODEL_MANAGEMENT_MODE`); bounded deprecated adapter; explicit rollback +
  observability; fail-closed removal criteria; engine selection preserved at all
  dispatcher verbs; `PI_ENGINE_VALUES` stays canonical.
- **Design outputs:** engine resolution matrix (V3); compatibility write-path
  routing with provenance tags; migration audit log schema; deprecation headers +
  diagnostics; rollback runbook v1.
- **Exact verification:**
  ```bash
  uv run --project backend python -m pytest tests/test_llm_servers.py \
    tests/test_settings_agentic_pi_endpoints.py tests/pi_production/test_w1_dispatcher_authority.py \
    tests/pi_production/test_w1_usage_ledger.py tests/pi_production/test_w1_realpath_accounting.py \
    tests/pi_production/test_w6_engine_selection.py -q
  uv run --project backend python -m pytest tests/pi_migration/test_model_management_migration.py \
    tests/pi_migration/test_model_management_rollback.py -q          # NEW obligations (V14)
  python scripts/pi_migration_inventory.py --json
  uv run --project backend python -m pytest tests/pi_migration/test_count_to_zero.py -q
  uv run --project backend python -m pytest tests/compute_cases/routing.py tests/compute_cases/status_contracts.py -q
  python scripts/security_benchmark.py --fail-on-threshold
  ```
- **Acceptance:** second migration run is a no-op; no silent data loss (diff counts
  + checksums); rollback drill performed and recorded; typed failure on unknown
  engine mode; deprecation metadata on legacy surfaces; no new identity created by
  compat writes.
- **Rollback:** §6.4 switch sequence + reverse migration script; re-run W2
  acceptance to prove reversion.

### Wave 3 — `embeddings-controls` (≈ old CF-791 + CF-794 + CF-799)

- **Scope:** persist/enforce the embedding profile (model/dimension/dtype/
  normalization/version); drift requires explicit compat flag + owner sign-off;
  propagate `temperature`/`max_tokens`/`thinking_level`/`timeout_ms`/`max_retries`
  via the existing `_turn_bind_params` path; rework the Pi-vs-Istara engine selector
  with evidence-backed comparative summaries (benchmark-row provenance, provisional
  status — never invented claims); accessibility contract.
- **Design outputs:** embedding policy keyed by canonical model identity; selector
  UX contract (`frontend/src/lib/modelCatalog.ts`,
  `frontend/src/components/settings/ProjectSettingsView.tsx` (V16), scenario
  `79-engine-selector.mjs`); summary provenance schema.
- **Exact verification:**
  ```bash
  uv run --project backend python -m pytest tests/pi_production/test_w8_embeddings_gateway.py \
    tests/pi_production/test_w8_ux_parity.py tests/pi_production/test_w6_engine_selection.py -q
  uv run --project backend python -m pytest tests/test_pi_runtime_endpoints.py tests/test_research_validity_contract.py -q
  npm --prefix frontend ci && npm --prefix frontend run test:unit -- --run
  npm --prefix frontend run lint && npm --prefix frontend run build
  node --test tests/simulation/scenarios/79-engine-selector.mjs
  python scripts/feature_docs.py --seed-missing --generate-site --check
  ```
- **Acceptance:** invariant probe green on both engines before/after each step; no
  duplicate embedding identity accepted; chat endpoint changes never mutate the
  profile; summaries cite evidence provenance.
- **Rollback:** restore prior profile version + settings; vectors remain keyed to
  their recorded profile (no silent reindex).

### Wave 4 — `petals-audio` (≈ old CF-792 + CF-793 + CF-800)

- **Scope:** preserve donor opt-in/identity/security/scheduling/same-model isolation
  and fail-closed 503 behavior; no early-wave bridge changes; add unified
  audio-model settings (§4.7) for local Whisper, compatible remote Whisper, and
  supported diarized providers; interview + microphone + channel flows share one
  profile contract; unsupported ⇒ typed unavailable.
- **Design outputs:** Petals authorization/consent/scheduling test matrix; audio
  profile schema + capability flags + secret binding contract; capability-aware
  transcript pipeline with explicit unsupported handling.
- **Exact verification:**
  ```bash
  uv run --project backend python -m pytest tests/petals_bridge/test_petals_bridge.py \
    tests/pi_production/test_same_model_donor_isolation.py \
    tests/pi_production/test_w3_research_spine.py tests/test_compute_registry_hardening.py \
    tests/test_project_scope_contracts.py -q          # + NEW test_research_spine_donor_routing.py (V14)
  uv run --project backend python -m pytest tests/test_transcription.py \
    tests/test_research_validity_contract.py tests/test_synthetic_provisional_boundary.py -q
  uv run --project backend python -m pytest tests/compute_cases/config.py tests/compute_cases/retries.py -q
  python scripts/security_benchmark.py --fail-on-threshold
  ```
- **Acceptance:** donor trust boundary not widened; no credential materialization
  outside approved stores; typed 503 + route evidence on unavailable donors; audio
  uses declared profile and capability policy; ICR/`needs_review` semantics intact;
  no silent text-model audio fallback. Mocked HTTP only — no live audio provider.
- **Rollback:** disable bridge/Pi-petals mode; retain existing local Whisper path;
  audio profiles revert to local-only.

### Wave 5 — `qa-docs-vps` (≈ old CF-795 + CF-796 + CF-797/798/804/805 + DEC-2)

- **Scope:** docs/manifests/feature coverage + deterministic Compose QA lanes for
  every accepted feature, then **VPS acceptance per the `vps` skill** (§9) with
  cleanup of only initiative-owned artifacts.
- **Design outputs:** regenerated living feature docs; `testing/feature_coverage.yml`
  + `qa/runtime_capabilities.json` obligations for all changed paths; VPS
  single-service acceptance Compose (§9.2); VPS runbook + rollback state.
- **Exact verification:**
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
  # VPS (see §9; every remote command via the vps skill's vpsctl.py — C7):
  VPSCTL=~/.pi/agent/skills/vps/scripts/vpsctl.py
  python3 $VPSCTL preflight
  python3 $VPSCTL inventory
  python3 $VPSCTL verify-isolation && python3 $VPSCTL verify-exposure
  python3 $VPSCTL audit-verify && python3 $VPSCTL audit-anchor
  ```
- **Acceptance:** feature-doc parity + site/manifests green; every accepted feature
  has a deterministic contract lane; security benchmark passes; 0 new gate failures
  attributable to the wave; VPS isolation/exposure/firewall/audit evidence recorded;
  cleanup proof for initiative-owned artifacts only.
- **Rollback:** VPS deployment identity + prior image digest preserved until
  post-deploy checks pass (§9.5); Compose/deps revert to prior wave state.

## 8. Task breakdown (this run's CF shape)

| Wave | This-run CF task (generated at approval) | Scope checklist (old anchors) |
|---|---|---|
| `foundation` | PLAN-A/B/C + REPLAN-A/B/C-r1 draft repairs + synthesis/vote + owner gate (planning-only) | old CF-797/798/802/803 (validate/contract/inspect obligations folded into planning + later waves) |
| `pi-catalog-secrets` | W1 implementation + reviewer/fixer | old CF-787/788/801 |
| `compat-routing` | W2 implementation + reviewer/fixer | old CF-789/790/794/804 |
| `embeddings-controls` | W3 implementation + reviewer/fixer | old CF-791/794/799 |
| `petals-audio` | W4 implementation + reviewer/fixer | old CF-792/793/800 |
| `qa-docs-vps` | W5 implementation + reviewer/fixer | old CF-795/796/797/798/804/805 |

Each implementation task: `gate before`, focused `gate after`, command evidence,
`self_report`, reviewer `review_verdict`, fixer loop on findings; major transitions
stop at owner gates.

## 9. Isolated VPS acceptance and cleanup (replaces multivac — DEC-2, C1)

The managed VPS (`vps` skill) is the only staging-acceptance path for this run.
`vpsctl.py` is **not** in this repo — every invocation uses the skill path
`~/.pi/agent/skills/vps/scripts/vpsctl.py` (C7); never raw `ssh` or shell scripts.

### 9.1 Procedure (strict order)

1. **Preflight:** `python3 $VPSCTL preflight` — verify keychain-backed SSH identity
   (`id_ed25519_capi`, `IdentitiesOnly`, strict host-key checking), helper
   integrity, audit DB health. Never print key material.
2. **Inventory (read-only evidence):** `python3 $VPSCTL inventory` — observed
   Compose projects/containers and current public exposure. Existing workloads are
   inventory-only; nothing is mutated without explicit owner authorization.
3. **Service creation:** Dokploy Docker Compose service from the repository using
   the strict single-workload profile (below). No Dokploy Domain, proxy labels,
   external network, Docker socket, `network_mode: host`, privileged, or host
   PID/IPC. Secrets set only in the Dokploy secret/environment UI.
4. **Preview before deploy:** reject any rendered Compose that adds a shared/proxy
   network or a second service.
5. **Deploy preserving identity:** capture current deployment identity + image
   digest as rollback target; deploy.
6. **Verify:** `python3 $VPSCTL verify-isolation` (one attached network, one
   endpoint, `Internal: true`, no default route, no host/other-container
   reachability) and `python3 $VPSCTL verify-exposure` with the documented approved
   port set (IPv4+IPv6).
7. **Firewall evidence:** check firewall before/after and the `DOCKER-USER` chain
   (published ports bypass ordinary rules). **No firewall change without owner
   approval** — escalate unexpected exposure; never remove a port until its owning
   workload is known.
8. **Audit:** `python3 $VPSCTL audit-verify` then `python3 $VPSCTL audit-anchor`
   (signs the chain head with the SSH identity). Report verified port set, image
   identity, isolation proof, firewall result, rollback state, and audit event ids —
   never secrets or raw output.

### 9.2 Strict single-workload Compose baseline (adapted from the vps skill)

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

No `container_name`, host bind mounts, `extra_hosts`, or socket mounts; named
volumes only if persistence is explicitly approved.

### 9.3 Single-service reality check (C5)

The repository's production `docker-compose.yml` is 8-service. The strict profile
permits exactly one service with inbound-only connectivity. Therefore the default
acceptance target is a **dedicated single-service acceptance image** (a minimal
read-only bundle that exercises the acceptance contract — healthcheck + one approved
port), built on the testing branch. If the acceptance contract genuinely requires
multi-container topology, a database, outbound API access, or a domain proxy, that
is an explicit security exception: stop, describe the minimum connectivity graph,
obtain written owner approval, and record the exception in the audit DB before any
change. Never silently weaken isolation.

### 9.4 Cleanup

After acceptance: remove **only** initiative-owned disposable artifacts (this run's
Compose service, its named volumes if created, rendered previews; local audit rows
stay in the gitignored audit DB). Existing workloads, benchmark deployments, and the
audit database are untouched. Record cleanup commands through `$VPSCTL ssh`.

### 9.5 Rollback

Until the owner accepts: preserve prior deployment identity/digest; re-deploy prior
Compose on verification failure; record the event in the audit chain. No firewall
rollback is needed if no firewall change was made (the default).

## 10. Documentation, manifests, and test ownership

- Living feature docs (`docs/features/content/…`): `settings/llm-servers`,
  `chat/model-controls`, `chat/audio`, `interviews/transcription`,
  `settings/compute-donation`, `compute/pool`, engine selector, and any
  provider/credential/audio pages the feature inventory discovers.
- Regenerate with `python scripts/feature_docs.py --seed-missing --generate-site
  --check` in the same change; attach output as evidence; never hand-edit generated
  site files.
- Architecture docs: `docs/architecture/agentic_core.md` (identity/transport
  boundary, explicit engine resolution, legacy adapter vs infrastructure),
  `docs/architecture/research-validity-contract.md` (route/evidence provenance,
  audio evidence, provisional QA), `self-improvement-governance-contract.md` only if
  self-improvement paths change.
- Repo docs: `README.md`, `README.pt-BR.md`, `DOCUMENTATION.md`, `TESTING.md`,
  `CHANGE_CHECKLIST.md`, `SYSTEM_CHANGE_MATRIX.md`, `testing/TESTING_STRATEGY.md`
  where contracts change. No private VPS host details in public docs.
- `testing/feature_coverage.yml` + `qa/runtime_capabilities.json` for all changed
  paths (gates `architecture_drift`, `test_ownership` are load-bearing: every
  behavior-changing file needs an owning test/doc obligation).
- Security: update `security/control_matrix.json`, `security/SECURITY_BENCHMARK.md`,
  `tests/test_security_benchmark.py` only when a control/evidence path/standard/
  trigger changes; run the benchmark on every security-sensitive wave.

## 11. Risks and mitigations

| ID | Risk | Sev | Mitigation | Rollback |
|---|---|---|---|---|
| R1 | Package update breaks worker protocol / structured contract | High | Pin exact versions; protocol v2 handshake + contract suites both sides; compatibility statement before bump | Restore prior pins/lockfiles/worker checkout |
| R2 | Duplicate model identity / split-brain | High | Provider-qualified ids + uniqueness constraints + collision tests; aliases provenance-only | Restore canonical mapping; source rows intact |
| R3 | Secret coupling drift (Fernet → Keychain/env) | High | In-memory decrypt/re-encrypt; credential status matrix; redaction audit; no plaintext export | Keep source encrypted field + compat reference |
| R4 | Silent cross-engine fallback | High | Typed per-engine errors; one-ledger-row accounting; dispatcher contract tests | Explicit mode revert (§6.4) |
| R5 | Embedding/vector drift | High | Profile persisted + startup probe; block mismatch before cache/write | Restore prior profile; vectors keyed to recorded profile |
| R6 | Donor boundary erosion / paid fallback hides failure | High | No early bridge changes; consent+pin+503 tests; isolation invariant green | Disable bridge mode; donor registry unchanged |
| R7 | Compatibility adapter becomes second source of truth | High | Canonical-only writes; count-to-zero ratchet + allowlist audit per wave | Re-enable read adapter; never delete rows |
| R8 | VPS isolation/exposure defect | High | Strict profile + preview rejection + verify-isolation/exposure + firewall/`DOCKER-USER` evidence + audit-anchor; no firewall change w/o owner approval | Prior deployment identity/digest retained; redeploy prior Compose |
| R9 | QA false confidence | Med | Contract stub labeled non-quality; synthetic provisional guard; live lane owner-gated | Stop QA project; never promote synthetic artifacts |
| R10 | Inherited gate debt masks new drift | Med | V5 baseline recorded; per-wave before/after diff; 0-new-failures rule | — |
| R11 | Audio provider unsupported/private behavior | Med | Capability contract + local/mocked tests + `needs_review`; no implicit fallback | Return unavailable; retain local Whisper path |

## 12. Definition of Ready / Done and owner gates

**Ready for implementation:** winning consensus plan frozen; owner approval recorded
at the plan gate; per-wave CF tasks generated with scope/dependencies/impacted
paths/verification; version + baseline evidence attached; migration/rollback contract
explicit; VPS procedure represented; no implementation dispatched before approval.

**Done for the initiative:** every wave green with command evidence + reviewer pass;
canonical identity proven without duplicates or secret leakage; both engines
explicitly selectable and independently fail-closed with one usage row per dispatch;
migration idempotent/reversible/observed; deprecation + removal criteria met with
evidence; embeddings/Petals/audio/spine/UI/QA/security/docs obligations complete;
VPS acceptance isolated, verified, audited, and cleaned; lifecycle/ledger/findings
accurate. The conductor stops at the owner approval gate after the consensus plan is
frozen and again at ship.

## 13. Coverage matrix (which carried draft informs which section — for synthesis)

| Requirement | This draft § | Carried inputs used |
|---|---|---|
| Verified boundary inventory | §2 | C §2 (primary), A §2 (corrections C1–C7) |
| Canonical identity model | §4.1–4.3 | A §4.1–4.3 (schema), B §6 (conceptual contract), C §4 (states) |
| Retirement state machine + removal criteria | §5 | B §5/§6 (sequence + gates), A §5.3/§6 (row states + promotion criteria), C §4 (S0–S4 + removal list) |
| Data/secret migration + rollback | §6 | A §5 (preflight/mapping/rollback), C §4 rollback switch, B §8 |
| Wave plan + verification commands | §7 | C §5 (command sets, environment note), A §8 (acceptance phrasing), B §7 (wave command lists) — all re-verified against this tree (V13–V16) |
| VPS acceptance (replaces multivac) | §9 | vps SKILL.md + `references/dokploy-and-isolation.md` (authoritative); carried drafts' multivac sections **superseded** (C1); vpsctl skill path (C7) |
| Docs/manifests/security/test ownership | §10 | A §9–11, C §8–9, B §9–10 |
| Risks | §11 | A §12 + C §10 merged, VPS risk R8 added |
| Feature flags/deprecation | §5 | C §7 (flag registry), A §6 (promotion criteria) |

## 14. Handoff note

This is an independent, repaired draft (slot B), now at the authoritative
`plan_file` the synthesis phase consumes. The misnamed pre-repair duplicate
(`docs/build-stream/plans/istara-pi-model-management-migration-20260822-plan-b.md`)
is removed in the same commit as this file, mirroring the slot-A repair (L-4). The
next stage — architect consensus — compares A/B/C (A repaired, B repaired, C),
reconciles the corrections in §2 (especially C1 multivac→VPS, C2 CF-SPEC-1 wave
mapping, C5 single-service VPS reality check, C7 vpsctl skill path), and freezes one
MECE master plan. The conductor must stop at the owner approval gate before any
implementation task is released. No source implementation, lifecycle-plan edit,
Docker/VPS start, live provider call, model load, merge, push, or PR is authorized
from this stage.
