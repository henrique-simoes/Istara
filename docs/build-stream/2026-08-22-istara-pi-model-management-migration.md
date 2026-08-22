# Istara Pi Model-Management Migration (resumed 2026-08-22)

```yaml
item: istara-pi-model-management-migration
branch: conductor/istara-pi-model-management-migration-20260822
base: origin/testing@15260a78df6637c2d1981c74683525cb75ab1a22
cf:
  framing_spec: CF-SPEC-58 (prior run) / CF-SPEC-1 (this run)
  spec: CF-SPEC-1
  tasks: [planning-only until owner approval; CF-SPEC-1 tasks generated at approval]
phase: "Phase 0 — architecture and migration plan (resumed)"
stage: S1-plan
status: in-progress
blocked_on: owner approval gate — consensus vote round ef3baec72460f4802e2b complete (a=2: VOTE-B, VOTE-C; b=1: VOTE-A); winner candidate ec3a76e7… (master-a.md) pending freeze + owner approval; no implementation task released before owner approval
last:
  agent: deepseek/deepseek-v4-flash
  at: 2026-08-22T12:42:10Z
  ledger: L-13
next_action: "Conductor freezes the winning consensus plan (candidate ec3a76e7…, master-a.md), records owner approval at the plan gate, then generates implementation tasks from CF-SPEC-1; no implementation task is released before owner approval."
```

## Plan overview

### Problem

Istara has two model-management identity planes: legacy Istara `LLMServer` rows and Pi's provider/model catalog and endpoint resolver. Pi owns the agentic runtime seams, but persisted LLM Server CRUD, legacy routing, compute registration, compatibility projection, embeddings, Petals, audio configuration, and UI contracts are not yet one coherent migration. Removing LLM Servers abruptly would risk provider loss, model-ID ambiguity, embedding/vector-space drift, Petals donor isolation regressions, secret exposure, and broken existing projects.

### Outcome

Pi becomes the canonical model-management plane while Istara preserves both explicit agentic engines, research-validity protections, the shared embedding invariant, Petals donation, audio/transcription flows, and deterministic disposable Docker QA. Legacy LLM Servers retire through a reversible compatibility migration with observable deprecation and removal criteria. The resulting branch remains testing-only (everything goes to `testing`, never `main`).

### Resume context (2026-08-18 run, frozen as reference)

The prior run (`ISTARA-PI-MODEL-MIGRATION-20260818`) paused at the planning stage with a Conductor finalization hold. Its three independent architect drafts are carried forward as inputs:

- `docs/build-stream/plans/carried-20260818-plan-a.md` (Architect A, 55.6 KB)
- `docs/build-stream/plans/carried-20260818-plan-b.md` (Architect B repair, 18.2 KB)
- `docs/build-stream/plans/carried-20260818-plan-c.md` (Architect C, 35.1 KB)

These MUST be used as inputs by the new architects; they were authored by independent models (Pi gpt-5.6-luna, Codex, Pi deepseek-flash) under the old roster and are not re-authorizations of the new roster.

### Owner-approved roster (2026-08-22)

| Role | Harness | Model | Effort |
|---|---|---|---|
| Architect A | pi | deepseek/deepseek-v4-flash | max |
| Architect B | pi | deepseek/deepseek-v4-pro | max |
| Architect C | codex | gpt-5.6-luna | low |
| Implementer | codex | gpt-5.6-luna | low |
| Code reviewer | pi | deepseek/deepseek-v4-flash | max |
| Fixer | pi | deepseek/deepseek-v4-flash | max |
| Fallback (unlisted roles) | codex | gpt-5.6-luna | low |

### Owner-approved boundaries

- Work only from the isolated branch/worktree based on `origin/testing` at `15260a78`.
- Use the pinned native Compass Forge binary (`COMPASS_FORGE_BIN`/`COMPASS_FORGE_SHA256` from `resolve-pin.sh`); no Python/PATH fallback.
- Carry the three 2026-08-18 drafts forward as inputs; re-do whatever needs re-doing with the new roster.
- Everything goes to the `testing` branch lineage, including pushes to origin. Never touch `main`.
- Multivac is no longer available. Final acceptance deploys on the managed VPS per the `vps` skill (Dokploy strict single-workload profile, vpsctl.py preflight/inventory/verify-isolation/verify-exposure/audit-anchor, no firewall changes without owner approval).
- Do not start live backend/frontend servers, load models, expose secrets, touch `LLMs/` or `Model_Finetuning/`, weaken gates, or alter unrelated Docker workloads.
- Owner approval remains mandatory at the plan gate, at ship, and for any firewall/VPS exposure change.

## Roadmap

1. **Foundation and inventory** — verify latest Pi release, freeze provider/model/secret contracts, map all legacy LLM Server consumers, capture gates, migration/rollback artifacts, and establish test obligations. Uses the carried-forward drafts.
2. **Pi canonical catalog and secret custody** — remove duplicate model-ID ambiguity, unify provider catalog/endpoints/OAuth/API-key/custom/local configuration, validate encryption against standalone Pi, preserve exact endpoint identity/capability metadata.
3. **Compatibility migration and routing** — migrate/project legacy configuration without silent data loss, route both Pi and legacy Istara engines through Pi-owned resolution, deprecate legacy LLM Server APIs, preserve explicit rollback.
4. **Embeddings and agent controls** — preserve the vector-space invariant, define chat/embedding separation, support temperature/thinking/effort controls, redesign the Pi-vs-Istara selector with honest comparative summaries.
5. **Petals and audio** — preserve donor opt-in, identity/security, scheduling and fail-closed Petals behavior; define unified Whisper/audio/diarized transcription model configuration.
6. **Testing, documentation, and VPS acceptance** — update living feature docs/manifests, Compose contracts and feature coverage, run disposable provider-backed QA on `testing`, then deploy the isolated staging service on the managed VPS per the `vps` skill (Dokploy strict profile, verify-isolation/exposure, firewall evidence, audit-anchor), and remove only initiative-owned disposable artifacts.


<!-- consensus-winning-plan:ISTARA-PI-MODEL-MIGRATION-20260822-241fd9bafde32a2921e12fb79ffc33bbfdbacb29953e3e56ae5b7841a62748a5 -->
## Winning consensus plan — ISTARA-PI-MODEL-MIGRATION-20260822

# MECE Master Plan (Slot A synthesis, repaired) — Istara Pi Model-Management Migration, 2026-08-22 run

**Task:** `ISTARA-PI-MODEL-MIGRATION-20260822-REMASTER-A-r1` (consensus master-plan repair a; supersedes the L-8 synthesis at the misnamed `istara-pi-model-management-20260822-master-a.md` path)
**Role:** `istara-pi-model-management-20260822-architect-a` · **Spec:** `CF-SPEC-1`
**Synthesis round:** `0bb85df72bbe6604f51a` · **Phase:** `synthesize` (sole synthesis round; no vote)
**Plan file (authoritative):** `docs/build-stream/plans/istara-pi-model-management-migration-20260822-master-a.md` (this file)
**Inputs (immutable snapshots):** slot-A draft `8b084d99…` (`…-plan-a.md`), slot-B repair `6ca5b84c…` (`…-plan-b.md`), slot-C draft `a7e88f54…` (`…-plan-c.md`); carried 2026-08-18 drafts `carried-20260818-plan-{a,b,c}.md` as historical inputs.
**Branch:** `conductor/istara-pi-model-management-migration-20260822` (base `origin/testing@15260a78`). Everything stays on the testing lineage; never `main`.
**Status:** Master-plan candidate. Implementation is prohibited until the frozen consensus plan passes the owner approval gate.

> **Repair note (REMASTER-A-r1, 2026-08-22):** The L-8 slot-A synthesis was delivered
> under the wrong filename (`istara-pi-model-management-20260822-master-a.md`) instead
> of this task's authoritative `plan_file`
> (`istara-pi-model-management-migration-20260822-master-a.md`), so the vote phase
> could not consume it under the task's plan_file. This file is the repaired,
> authoritative slot-A master-plan candidate: full content preserved from the L-8
> synthesis, every current-tree fact re-verified at repair time (2026-08-22: Pi
> latest 0.84.2/0.84.2; inventory ratchet 0 with 1 allowlisted permanent site; gate
> before 30 inherited / 0 new; 62 tests collect across the six key surfaces; security
> benchmark pass; feature-doc parity green 86 features/224 artifacts; `vpsctl.py` 7
> subcommands at the vps skill path). The misnamed duplicate is removed in the same
> commit.
>
> This is the sole synthesis round. The three independent drafts were read in full and
> reconciled below — overlaps merged into single sections, conflicts resolved with a
> stated rule, gaps closed, and every current-tree fact re-verified on 2026-08-22 at
> synthesis time. Where a draft made a claim this synthesis could not confirm, the
> claim is marked and corrected, never silently carried. The coverage matrix (§15)
> records which draft insight each major section incorporates.

## 1. Decision and executive summary

**Decision:** Make Pi the single canonical model-management authority — provider/model
identity, endpoint identity, capability metadata, credential custody, and resolution —
while Istara keeps **two explicitly selectable, permanently supported agentic engines**
(`pi`, `legacy`) whose transports differ but whose model identity, route evidence,
accounting, and vector space are governed by one canonical plane. The legacy `LLMServer`
row plane (storage + CRUD + live registration + Fernet encryption) becomes a
**reversible compatibility adapter and migration source**, never a second catalog. It
retires in observable, evidence-gated stages; physical deletion is a separate,
later, owner-approved action.

The agentic dispatch ratchet is already at **0 direct product call sites**
(`tests/pi_migration/test_count_to_zero.py`): this is not a call-site migration, it is a
**model-management authority migration**. The migration is additive and idempotent first:
inventory → map → validate → dual-read/shadow → canary → Pi-primary → deprecate →
(separate, later) retire.

All work stays on the `testing` branch lineage. The plan freezes here at the owner
approval gate; implementation tasks are generated from the approved plan. No live model
load, completion probe, backend/frontend server start, secret disclosure, firewall
change, merge, push, or PR is authorized from this stage. VPS acceptance (the retired
multivac path's replacement, DEC-2) follows the `vps` skill contract: Dokploy strict
single-workload profile, `vpsctl.py` from the **vps skill path** (`~/.pi/agent/skills/vps/scripts/vpsctl.py` — it is not in this repo), no firewall change without owner approval.

## 2. Verified current-state boundary (re-verified 2026-08-22 at synthesis time)

Every fact below was re-checked in this worktree during this synthesis. These are the
surfaces the plan protects; nothing here is altered by the planning stage.

| # | Verified fact (2026-08-22) | Command / source |
|---|---|---|
| V1 | Upstream latest `@earendil-works/pi-agent-core` = **0.84.2**, `@earendil-works/pi-ai` = **0.84.2** (passive registry query) | `npm view … version` |
| V2 | Tree pins: `pi-runtime/package.json` + lockfile **0.83.0 / 0.83.0**; `labs/pi-replacement/package.json` + lockfile **0.80.10 / 0.80.10** (lab comparator has diverged from runtime; must be raised in lockstep or given a recorded, reviewed divergence rationale) | read package files |
| V3 | Engine precedence (dispatcher docstring + code): per-call `engine=` → header `x-istara-agent-engine` → project `agentic_engine` → `settings.agentic_engine_default` (**"legacy"**, config.py:315). No silent fallback either way | `backend/app/core/agentic/dispatcher.py` |
| V4 | Pi endpoint config field is `pi_api_endpoints: list[PiApiEndpoint]` (config.py:304); `DEFAULT_ENDPOINT_ID="pi-deepseek-default"` (endpoints.py:23); `SECRET_CACHE_TTL_SECONDS=60.0` | read config/endpoints |
| V5 | Count-to-zero ratchet green: **3 passed** | `uv run --project backend python -m pytest tests/pi_migration/test_count_to_zero.py -q` |
| V6 | Gate baseline (this run): `gate before` = fail, **30 failures** (`secret_flow`, `unexpected_large_files`), **0 new, 0 actionable**, drift route=4/type=2, warnings=188, 1981 files scanned | `compass-forge gate before --task …-REMASTER-A-r1 --summary` |
| V7 | Security benchmark baseline: **28/28 pass (100.0%)**, `status: pass`, version 2026.05.19, `triggered_paths: []` | `python3 scripts/security_benchmark.py --fail-on-threshold` |
| V8 | Feature-doc parity green: **86 features, 224 site artifacts, 0 seeded** | `python3 scripts/feature_docs.py --seed-missing --generate-site --check` |
| V9 | Ratchet inventory: **1 allowlisted permanent site** (`backend/app/core/agentic/legacy.py:599` — permanent legacy executor transport); `EXPECTED_PRODUCT_SITES = 0` | `python3 scripts/pi_migration_inventory.py --json` |
| V10 | Six-wave manifest confirmed: `foundation, pi-catalog-secrets, compat-routing, embeddings-controls, petals-audio, qa-docs-vps` | `docs/build-stream/manifests/istara-pi-model-management-migration-20260822.json` |
| V11 | `vpsctl.py` lives in the **vps skill**, not this repo: `~/.pi/agent/skills/vps/scripts/vpsctl.py`; subcommands exactly `preflight, inventory, audit-verify, audit-anchor, verify-isolation, verify-exposure, ssh`; strict profile = one service, project-local `internal: true` bridge, one published port, no proxy/external network/socket/privileged/host-namespace, `read_only` + `cap_drop: ALL` | vps SKILL.md + `python3 ~/.pi/agent/skills/vps/scripts/vpsctl.py --help` |
| V12 | `docker-compose.yml` is an **8-service** topology (ollama, postgres, backend, frontend, caddy, relay, otel-collector, jaeger) — the strict single-workload VPS profile therefore requires a dedicated single-service acceptance image or an owner-approved connectivity exception | `docker-compose.yml` service count |
| V13 | All 40 existing test anchors cited in the wave plan exist in the tree (incl. `pi_production/test_{endpoint_secrets,runtime_hardening,w1_agentic_contract,w1_dispatcher_authority,w1_usage_ledger,w1_realpath_accounting,w6_engine_selection,w8_embeddings_gateway,w8_ux_parity,engine_http_provider,seams_fail_closed,same_model_donor_isolation,w3_research_spine}`, `petals_bridge/test_petals_bridge`, `compute_cases/*`, `pi_benchmark/*`) | file inventory sweep |
| V14 | **Not yet existing** (obligations to create in W2/W4, never claimed green today): `tests/pi_migration/test_model_management_migration.py`, `tests/pi_migration/test_model_management_rollback.py`, `tests/pi_production/test_research_spine_donor_routing.py` | file inventory sweep |
| V15 | Frontend anchors: `frontend/src/lib/modelCatalog.ts`, `frontend/src/lib/modelProviders.ts`, `frontend/src/components/settings/ProjectSettingsView.tsx` (not the non-nested path); simulation scenario `tests/simulation/scenarios/79-engine-selector.mjs` exists | file inventory sweep |
| V16 | QA/governance scripts present: `scripts/istara-qa.sh`, `scripts/check_feature_obligations.py`, `scripts/check_integrity.py`, `scripts/check_ci_governance.py`, `scripts/check_test_harness.py`, `scripts/check_public_tree_clean.py`; `scripts/multivac_*` does **not** exist (never cite it); `docker-compose.qa.yml` profiles: contract/synthetic/reset/audit/live/ui | file inventory sweep |
| V17 | Environment prerequisites: backend tests run under `uv run --project backend …`; `pi-runtime/node_modules` is absent at HEAD → worker-backed suites (e.g. `test_w1_agentic_contract.py`) require `cd pi-runtime && npm ci` first | filesystem |

### Surfaces in scope (boundary inventory, non-exhaustive file list)

- **Legacy LLM Server plane (retirement target, reversibly):** `backend/app/models/llm_server.py` (table `llm_servers`); `backend/app/api/routes/llm_servers.py` (admin CRUD, `/health-check`, `/discover`, `_refresh_pi_catalog_projection`); `backend/app/core/llm_router.py` (backward-compat wrapper over `ComputeRegistry`); `backend/app/core/compute_registry*.py` (donor-schedulable node registry — must never contain Pi endpoints); `backend/app/core/ollama.py` + `network_discovery.py` (startup re-hydration); `backend/app/core/field_encryption.py` (Fernet, `DATA_ENCRYPTION_KEY`); `backend/app/core/endpoint_security.py` (URL normalization, plaintext/credential rejection, redaction); consumers in `compute_node*.py`, `autoresearch_runners/model_temp.py`, `api/routes/settings.py`, `api/routes/admin.py`, `services/research_validity_service.py`; schema `backend/alembic/versions/002_distributed_platform.py`.
- **Pi plane (target authority):** `backend/app/core/pi_runtime/{endpoints,model_manager,engine,embeddings_gateway,model_manager_provisioning,supervisor,seams}.py`; `pi-runtime/src/worker.mjs` + `pi-runtime/PROTOCOL.md` (NDJSON protocol v2, `PROTOCOL_VERSION=2`); `backend/app/core/agentic/{dispatcher,legacy,usage_ledger}.py`; `backend/app/core/pi_replacement.py` (`PI_ENGINE_VALUES={"pi","pi-candidate","pi-replacement","deepseek-pi"}`); `backend/app/config.py`.
- **Coupled governed surfaces:** embeddings (`core/embeddings.py`, `embedding_validation.py`, `embedding_cache.py`, invariant on `default_embed_model()`); Petals (`core/petals_bridge.py`, `api/routes/petals_bridge.py`, `relay/`); audio (`core/transcription.py`, `file_processor.py`, `api/routes/chat.py`, `chat_voice.py`, `files.py`); research spine (`docs/architecture/research-validity-contract.md`, `core/research_validity.py`); UI (`frontend/src/lib/modelCatalog.ts`, `modelProviders.ts`, settings views, `Sidebar.tsx`); QA (`docker-compose.qa.yml`, `qa/`, `scripts/istara-qa.sh`, `tests/test_qa_stack_contract.py`, `tests/test_provider_contracts.py`).

## 3. Corrections carried from the drafts (all independently re-verified)

| # | Correction | Status at synthesis |
|---|---|---|
| C1 | **Multivac is retired (DEC-2).** VPS acceptance replaces it, per the `vps` skill: Dokploy strict single-workload profile, `vpsctl.py preflight → inventory → deploy → verify-isolation → verify-exposure → audit-anchor`, firewall/DOCKER-USER evidence, no firewall/port changes without owner approval | Verified (V11, V12, V16); carried everywhere below |
| C2 | Old-run CF ids `CF-787…CF-805` (CF-SPEC-59) are frozen history. This run = CF-SPEC-1 + six-wave manifest (V10). Old ids appear only as scope checklists in parentheses | Verified (V10) |
| C3 | Gate baseline is **30 inherited / 0 new / 0 actionable** (not the stale "80"); security benchmark 28/28; docs parity 86 features | Verified (V6–V8) |
| C4 | Settings field name is `pi_api_endpoints` (not "`PI_API_ENDPOINTS` JSON settings state") | Verified (V4) |
| C5 | **VPS single-workload constraint is load-bearing:** the 8-service `docker-compose.yml` does not fit the strict profile; the default target is a dedicated single-service acceptance image; any multi-service exception requires written owner approval with the minimum connectivity graph (§9.3) | Verified (V12) |
| C6 | Environment prerequisites explicit: `uv run --project backend …` for backend suites; `cd pi-runtime && npm ci` before worker-backed suites; `labs/pi-replacement` must not silently diverge after the upgrade | Verified (V2, V17) |
| C7 | `vpsctl.py` is **not in this repo** — run it from `~/.pi/agent/skills/vps/scripts/vpsctl.py` | Verified (V11) |
| C8 | (this synthesis) Verification must use **fresh disposable databases** and never infer validity from contaminated persistent SQLite; CF `intelligence impact`/`why`/`test-impact` context packs are mandatory before touching implementation entry points | Draft C §2/§6; adopted as a foundation-wave obligation |

## 4. Goals, non-goals, and invariants

### Goals

1. Update both bundled Pi package surfaces (`pi-runtime`, `labs/pi-replacement`) to the latest **verified compatible** upstream release (0.84.2 as of 2026-08-22; re-verify passively immediately before the change), with reproducible lockfiles and protocol-v2 contract tests.
2. One canonical Pi-owned catalog for provider families, model IDs, endpoint IDs, capabilities, local/cloud/custom/OAuth/API-key configuration, and credential references; no duplicate model-identity semantics.
3. Both explicit engines preserved and selectable, with canonical endpoint/model resolution fail-closed for each; no silent fallback in either direction.
4. Migrate all mappable LLM Server configuration and encrypted secrets without data or secret loss — idempotent, evidenced, reversible, with a bounded deprecated adapter.
5. Preserve the shared embedding model/dimension/dtype/normalization invariant; make embedding identity explicit and visible in safe metadata.
6. Preserve Petals consent, project authorization, donor identity pinning, route evidence, and fail-closed no-paid-fallback behavior.
7. Governed audio/Whisper/diarization model configuration without bypassing the Research Spine or inventing unsupported Pi audio behavior.
8. Update UI, living feature docs, manifests, test ownership, testing-branch Compose obligations, security evidence, and (owner-authorized) isolated VPS acceptance.

### Non-goals

- No merge, push, PR, or `main` change — everything stays on the `testing` lineage; the conductor ship stage owns merge/push, gated by cast config.
- Do not delete `LLMs/` or `Model_Finetuning/`, clean external repos, or touch unrelated Docker/VPS workloads.
- Do not delete the legacy transport, `ComputeRegistry`, donor relay/browser transport, local Ollama/LM Studio provisioning, or the permanent legacy executor merely because Pi becomes the model-management authority.
- No live model loading, no live backend/frontend servers, no live completion calls, no private endpoint access without explicit owner authorization.
- Do not treat synthetic QA, raw tool success, transcript keyword tags, or comparative model prose as accepted research evidence (Research Spine contract).
- Do not silently merge endpoint identities that share a model name or host.
- No firewall/VPS exposure changes without owner approval.

### Invariants that must remain true (each mapped to its primary proof)

| # | Invariant | Primary proof |
|---|---|---|
| I1 | Pi/runtime isolation: `pi_runtime` never imports/mutates `ComputeRegistry`; Pi resolution never donor-scores | `tests/pi_production/test_same_model_donor_isolation.py` |
| I2 | Explicit dual-engine choice; precedence V3 stable; selected-engine failure never silently switches engines | `test_w1_agentic_contract.py`, `test_w1_dispatcher_authority.py`, `test_w6_engine_selection.py` |
| I3 | One identity plane: provider-qualified `model_id` ≠ stable `endpoint_id`; legacy ids are provenance aliases only; no duplicate canonical identity | `test_model_provider_contract.py` + **new** migration catalog contract tests (W2) |
| I4 | Secret safety: plaintext credentials only in short-lived in-memory binding; none in logs/responses/docs/QA artifacts/telemetry/CF evidence | `test_endpoint_secrets.py`, `test_field_encryption.py`, security benchmark |
| I5 | Vector-space safety: chat-engine/provider changes cannot silently alter the embedding profile; model/dimension/dtype mismatch blocks before cache/writes | `test_w8_embeddings_gateway.py` |
| I6 | Donor security: consent + health + project authorization + exact node pin all required; unavailable = typed 503, no paid fallback; donor never ordinary Pi capacity | `tests/petals_bridge/test_petals_bridge.py`, donor-isolation test, **new** `test_research_spine_donor_routing.py` (W4) |
| I7 | Research validity: source spans → evidence units → coding → reliability → reconciliation → human review → Done → reports; candidate/provisional outputs never reportable | `test_research_validity_contract.py`, `test_synthetic_provisional_boundary.py` |
| I8 | Migration reversibility: every source row has mapping/status and a restorable snapshot before write/cutover; rollback is a documented operation, not an exception handler | **new** `tests/pi_migration/test_model_management_{migration,rollback}.py` (W2) |
| I9 | QA isolation: unique `istara-qa-<run-id>` projects, internal networks, deterministic provider stub, live lane owner-gated; fresh disposable DBs for validation | `test_qa_stack_contract.py`, `test_qa_reset_seed.py` |
| I10 | VPS isolation: strict single-workload profile only; proof of `Internal: true`, one endpoint, no default route, no host/other-container reachability, exactly the approved published port set | `vpsctl.py verify-isolation`/`verify-exposure` + firewall/`DOCKER-USER` evidence (W5) |

## 5. Target architecture

### 5.1 Canonical identity model (additive; semantic split is load-bearing)

```text
CanonicalModel      model_id (provider-qualified, normalized — never a UI display string)
                    provider_family: openai_compat | anthropic_compat | local_ollama |
                                     local_lmstudio | whisper | diarization | …
                    canonical_name | aliases[] (observed aliases with provenance;
                    legacy ids are aliases ONLY)

CanonicalEndpoint   endpoint_id (stable route identity, always distinct from model_id)
                    model_id | transport: pi_http | legacy_registry | local_lifecycle |
                                      petals_bridge | audio_adapter
                    endpoint_kind: cloud | custom | local | petals | audio
                    nonsecret connection metadata + capability profile
                    credential_ref (opaque) | legacy_source_id (nullable, provenance ONLY)
                    migration_state + timestamps

CredentialRef       credential_ref (opaque stable name) | kind: keychain | encrypted_db |
                    environment | oauth
                    secret material encrypted/externally held ONLY
                    status: present | missing | invalid | rotation_required

EmbeddingProfile    profile_id | model identity | endpoint/transport identity | dimension |
                    dtype | normalization | profile version | health status

AudioModelProfile   profile_id | provider_family | model_id | endpoint_id | credential_ref |
                    local|remote mode | language policy | diarization support |
                    speaker-count policy | timestamps | confidence policy | review threshold
```

Rules (merged from all three drafts, binding):
- `model_id` is provider-qualified and normalized; two providers exposing the same visible model name remain distinct canonical identities unless an explicit alias mapping proves equivalence.
- `endpoint_id` is always distinct from `model_id`; route evidence always retains endpoint identity.
- `legacy_source_id` / `pi-llm-<id>` / `pi-petals-<node_id>` are aliases/provenance, never independent identities; after migration the resolver must not emit both a legacy and a Pi canonical option for the same endpoint. Relay rows are NEVER projected as ordinary Pi endpoints.
- Capability metadata is attached to profiles, never inferred from a name; unknown required capability fails closed.
- `base_url`, host labels, credential refs, route IDs are never in public feature docs, QA artifacts, or normal telemetry; admin views return redacted/safe metadata and `has_credential` only.

### 5.2 Resolver and transport boundary

One canonical resolution request consumed by every dispatcher verb:

```text
resolve_model_request(project_id, engine, model_id?, endpoint_id?, purpose,
                      capabilities?, embedding_profile_id?) -> ResolvedModelTarget
```

`ResolvedModelTarget` = canonical model ID, endpoint ID, transport class, safe capabilities, credential reference, route-evidence fields. **Never plaintext credentials.**

- `PiModelManager` becomes the authoritative catalog/resolver (owns refresh, exact identity, capability admission, migration projection, weakref invalidation for live-DB projections — the existing three-source catalog is reorganized, not discarded).
- `PiExecutionService` consumes `transport=pi_http` targets only and binds secrets only on the private worker pipe; rejects non-Pi transports.
- The legacy executor remains a permanent, byte-compatible **transport adapter** (`transport=legacy_registry`/`local_lifecycle`), preserving legacy request shapes and ComputeRegistry project authorization; it never manufactures a second catalog.
- Petals uses explicit `transport=petals_bridge` targets through bridge admission; never a capacity candidate.
- Audio adapters use `transport=audio_adapter` with an explicit capability contract; binary audio never routes through the text Pi worker unless a separately verified provider API supports it.
- Every dispatcher verb (`chat_turn`, `completion`, `structured`, `ensemble`, `embed`, `react`) keeps exactly one usage/route row per dispatch — including typed resolution failures; no cross-engine fallback. `PI_ENGINE_VALUES` stays canonical.

### 5.3 Provider classes and secret custody

Explicit configuration classes: cloud OpenAI-compatible; Anthropic-compatible; OAuth (Keychain/encrypted custody, short-lived in-memory tokens); API key (Keychain/env/encrypted DB); custom/local (normalized loopback or approved HTTPS; local Ollama/LM Studio lifecycle separate from cloud credentials); audio/Whisper/diarization (never auto-promoted to a chat provider).

- Legacy `LLMServer.api_key` (Fernet) may be read **only inside a bounded migration service** that immediately re-encrypts or externalizes; the migration manifest stores credential reference, source kind, presence/status, and a nonsecret metadata checksum — never plaintext, raw tokens, or reusable secret fingerprints.
- Keychain references preserve service/account identities without copying values.
- Encryption must be validated against standalone Pi semantics — the migration must not assume the same encryption context/version; record and test context compatibility.

### 5.4 Engine selection and rollback semantics (preserves V3 exactly)

Precedence: per-call → header `x-istara-agent-engine` → project `agentic_engine` → `settings.agentic_engine_default` (default `"legacy"` until the owner flips it). Canonical target resolution happens **after** engine selection — never a hidden second engine choice. A selected `pi` target with missing credentials, unsupported capability, worker failure, or provider error is a **failed Pi invocation** (typed error + ledger row). A selected `legacy` target preserves the legacy transport and route evidence. Rollback = explicit mode/project flip to `legacy` + snapshot restore (§7.4), never an implicit exception fallback.

### 5.5 Embeddings

- One authoritative `EmbeddingProfile` for both engines: model identity, endpoint/transport identity, dimension, dtype, normalization, profile version. Engine adapters may differ in transport but must return vectors in the declared profile; mismatch blocks startup/engine switching and cache writes.
- Existing vectors stay tied to their recorded profile version; a deliberate profile migration = new profile version + bounded re-embed job + dual-read/reindex evidence + explicit invalidation. Vectors are never implicitly reindexed.
- Chat endpoint changes never mutate the embedding profile; UI separates chat-model controls from embedding-profile controls and shows the active profile identity safely.
- Pi gateway retains exactly one dispatcher-owned usage row; no double accounting.

### 5.6 Petals

- `petals_bridge.py` stays outside `pi_runtime`; projects only `source ∈ {relay,browser}`, `pi_served=true`, healthy, project-authorized donors; explicit `endpoint_id=pi-petals-<node>` or governed Petals purpose only — never donor selection by model-name collision, latency, or capacity when a Pi endpoint is requested.
- Unknown/unconsented/unhealthy/unauthorized donor → typed 503 + route evidence; no paid fallback.
- Donor lifecycle + selected/served/failed counters preserved; donor route identity visible to audit without prompts, URLs, or secrets. No early-wave bridge changes; W4 adds authorization/consent/scheduling tests.

### 5.7 Audio and diarization

- One canonical `AudioModelProfile` contract consumed by interview uploads, microphone chat (`/chat/voice`), and channel audio, preserving project authorization and source provenance.
- `local_whisper`: existing local model loader + ffmpeg boundary; model size becomes validated configuration.
- `remote_whisper`/`remote_diarization`: opt-in endpoint adapters with capability metadata, explicit credential custody, bounded file size/timeouts, redacted errors, deterministic mocked contract tests. A provider without diarization cannot be advertised as diarized.
- No configured audio profile → typed unavailable; **never** an implicit text-chat fallback.
- Transcriptions remain candidate/provisional until raw source spans/evidence units, coding, reliability, reconciliation, and human review gates accept them; ICR failure stays `needs_review`. No transcript/tag reportable before gates.

## 6. Reversible retirement: three orthogonal axes

The three drafts used three overlapping state vocabularies (A: row states; B: deployment stages S0–S5; C: row states with `canary`). MECE resolution: **two orthogonal state axes plus a mode registry**. This closes the gap where a single linear list conflated row-level progress with deployment stage.

### Axis 1 — Row/endpoint migration state (per source row or canonical endpoint)

```text
unmapped -> mapped -> credential_validated -> shadow_verified -> canary_verified
         -> pi_primary -> legacy_deprecated -> retired
any state -> blocked (reason + evidence handle)
pi_primary / legacy_deprecated -> rollback_ready -> legacy_compat
```

- **mapped:** canonical target exists; source row untouched; no cutover.
- **credential_validated:** secret reference resolves in memory; capability metadata valid; no completion call needed for deterministic QA.
- **shadow_verified:** read-only resolution + metadata parity for a canary project/contract stub; never double-sends user research content to a provider.
- **canary_verified** (from draft C): one opted-in non-research contract/faux-provider route executes end-to-end through the canonical target.
- **pi_primary:** Pi selected for opted-in project/route; legacy data still readable through the adapter.
- **legacy_deprecated:** admin writes use canonical Pi management; legacy endpoints return deprecation metadata + read-only compatibility projections; existing project selections resolve through the mapping.
- **retired:** only after §6.3 removal criteria pass, an owner gate accepts evidence, and retention/restore is satisfied. Retirement first disables runtime use; physical row deletion is a separate, later owner-approved action.
- Unsupported/malformed rows stay `legacy_only`/`blocked` with an actionable reason and the adapter enabled — **no migration step may require deleting a source row to validate success.**

### Axis 2 — Deployment stage (run-level)

```text
S0 legacy-authoritative (today)
S1 pi-authoritative catalog + secrets (Pi owns catalog/custody; both engines run)
S2 dual-engine execution (both engines through the canonical resolver)
S3 pi-preferred + legacy compatibility-only
S4 deprecated-adapter (warnings, compat reads, canonical writes)
S5 retired (runtime use off; archival, not deletion)
```

**Transition rule (every S_i → S_i+1):** (a) that wave's acceptance commands green; (b) `gate after` with **0 new** failures attributable to the wave (inherited baseline V6 tracked separately, never suppressed silently); (c) reviewer `review_verdict` pass; (d) performed rollback drill evidence for S2→S3 and S3→S4; (e) owner approval before S2→S3 and S4→S5.

### Axis 3 — Mode registry and feature flags (one global mode + existing selectors)

```text
PI_MODEL_MANAGEMENT_MODE = legacy_compat | shadow | pi_primary | deprecated_adapter | retired
```

Defaults: `legacy_compat` on existing installs; `agentic_engine_default` stays `"legacy"` until the owner flips it; per-project `agentic_engine` remains an explicit override, cleared on rollback; `llmserver_compat_mode` on through W2, off per-surface after the S4 criteria; `petals_bridge_enabled` semantics unchanged. Avoid many independent booleans: every flag flip is a code change with its own task, evidence, and rollback switch. Mode visible in safe admin diagnostics and included in route/migration evidence.

**Deprecation behavior:** stable deprecation response/header + safe diagnostic reason on legacy CRUD/runtime compatibility paths; read compatibility preserved for the retention window; writes either invoke canonical management or fail closed with a migration-required response (no second source of truth). Local lifecycle and donor APIs that remain required transport infrastructure are **not** deprecated — only the model-management ownership semantics are.

### 6.3 Removal criteria (all must hold with evidence before `retired`/S5)

- Count-to-zero ratchet green + allowlist audit clean (only documented permanent infrastructure entries).
- Zero active runtime reads treating LLM Server as canonical; zero unmapped rows except owner-accepted exceptions.
- All supported credentials resolvable or explicitly `blocked`; no data/secret-loss report.
- Vector invariant green on both engines; Petals security controls intact; audio flows on canonical config.
- UI offers no legacy-only model CRUD without deprecation notice; no duplicate model options.
- ≥1 performed staging-equivalent rollback drill; three consecutive deterministic full-suite runs with no new migration failures; one isolated testing-branch Compose run; one owner-authorized VPS staging proof when marked required.
- Security benchmark passes **with** the removal; docs/manifests regenerated and green.
- **Physical deletion is not part of the first `retired` state** — it is a separate later owner-approved action.

## 7. Data/secret migration and rollback

### 7.1 Preflight (immutable evidence, before any write or flag cutover)

1. Record branch/base commit, schema revision, package versions + lockfile hashes, `gate before` output.
2. Export a redacted inventory (`scripts/pi_migration_inventory.py --json`) of static Pi settings, `LLMServer` rows, aliases, relay/browser rows, local provider settings, project engine selections, embedding metadata — source IDs and mapping reasons only, never secret values or private endpoints.
3. Create an encrypted database backup/snapshot + preserve the pre-change checkout/Compose definition (disposable/gitignored path, owner-approved retention/restore proof).
4. Resolve only credential **presence/status** in a controlled dry-run; no live completions, no model loads, secrets never printed.
5. Record deterministic `migration_id`, schema version, source metadata checksum, migration-tool version; a repeated run with the same checksum is a **no-op** (idempotency contract).

### 7.2 Deterministic mapping (per non-relay `LLMServer` row)

Normalize provider family + endpoint URL (`endpoint_security.py` rules) → parse capability JSON **without inventing model names** (absent model = explicit `unknown/default` needing validation) → resolve/create provider-qualified canonical `model_id` → resolve/create exactly one canonical endpoint tied to the source row (`legacy_source_id`, source provider, priority, health summary, capability provenance preserved) → create credential reference (in-memory decrypt → re-encrypt through canonical custody, or nonsecret local mode for Ollama/no-key, or preserve Keychain service/account refs) → mark `mapped | credential_validated | blocked | legacy_only` with an actionable reason → store a redacted mapping result (never compare or log raw secrets).

Relay/browser rows are **never** migrated into ordinary Pi endpoints; they remain donor-plane identities handled only by the Petals bridge contract. Unsupported/malformed rows are preserved and visible, never dropped.

### 7.3 Staged cutover

Per Axis 1: `mapped` → `credential_validated` → `shadow_verified` → `canary_verified` → `pi_primary` → `legacy_deprecated` → `retired`; promotion is blocked by: conflicts, duplicate identity, secret mismatch, unsupported capability, vector mismatch, or missing route evidence. Global progression per Axis 2, gated by the §6 transition rule.

### 7.4 Rollback (explicit operation, per-wave switches — never an exception handler)

1. Stop the staged QA/temporary Compose (and any VPS acceptance) workload before changing data.
2. `PI_MODEL_MANAGEMENT_MODE=legacy_compat`; `agentic_engine_default=legacy`; clear per-project `agentic_engine` overrides; re-enable `llmserver_compat_mode`; invalidate temporary credentials. Do not change unrelated projects.
3. Restore the pre-cutover canonical mapping/status snapshot if the mapping itself is corrupt; keep the failed-migration report.
4. Restore the encrypted DB/config snapshot only when additive rollback cannot recover the source; verify schema downgrade/restore compatibility first.
5. Restore the previous checkout/Compose image; rerun legacy routing, embedding dimension, donor isolation, source-evidence contract tests.
6. Prove no source `LLMServer` row, project engine setting, vector, donor consent, or audit row was lost; record rollback command evidence; retain the migration artifact.

## 8. Wave plan with exact verification (maps to the run's six-wave manifest)

**Environment prerequisites (C6):** backend suites run as `uv run --project backend python -m pytest …`; worker-backed suites require `cd pi-runtime && npm ci` first (V17). VPS commands run `vpsctl.py` from the vps skill path (C7). All verification commands below exist/collect in this tree (V13–V16). Inherited gate failures (V6: 30) are tracked separately from migration findings in every evidence narrative.

### Wave 0 — `foundation` (planning; this stage)

**Goal:** freeze the boundary, record baselines, reconcile the three drafts into this master plan, stop at the owner approval gate. No code changes.
**Acceptance:** (1) verified Pi version/provenance record (V1/V2); (2) baseline gate/security/docs evidence captured (V6–V8); (3) ratchet green (V5); (4) master plan covers §4–§7 scope; (5) no implementation task released before owner approval; (6) CF `intelligence impact`/`why`/`test-impact` context packs recorded for the planned entry points (C8).

```bash
npm view @earendil-works/pi-agent-core version ; npm view @earendil-works/pi-ai version
python3 scripts/pi_migration_inventory.py --json
compass-forge gate before --summary
uv run --project backend python -m pytest tests/pi_migration/test_count_to_zero.py -q
python3 scripts/security_benchmark.py --fail-on-threshold
python3 scripts/feature_docs.py --seed-missing --generate-site --check
```

### Wave 1 — `pi-catalog-secrets` (≈ old CF-787 + CF-788 + CF-801)

**Goal:** Pi becomes the canonical catalog/secret owner; unify provider/endpoint/model config under the Pi plane; validate encryption against standalone Pi; update the Pi dependency; `LLMServer` rows stay intact.
**Design outputs:** dependency/version acceptance record (latest verified upstream, protocol-v2 compatibility statement against `pi-runtime/PROTOCOL.md`; `labs/pi-replacement` aligned in lockstep or explicit reviewed divergence rationale); canonical catalog service layered on `PiModelManager` (identity graph, endpoint capabilities, auth hints, secret handles) with duplicate-identity collision guards; secret custody translation (Fernet → Keychain/env/encrypted-DB references) with redaction audit and non-production readback checks; W2 snapshot tooling stubs.
**Verification:**

```bash
cd pi-runtime && npm ci && npm test && cd ..
cd labs/pi-replacement && npm ci && npm run validate && cd ..
uv run --project backend python -m pytest tests/test_model_provider_contract.py tests/test_pi_runtime_endpoints.py \
  tests/test_field_encryption.py tests/pi_production/test_endpoint_secrets.py \
  tests/pi_production/test_runtime_hardening.py -q
uv run --project backend python -m pytest tests/pi_production/test_w1_agentic_contract.py -q   # worker-backed; npm ci first
python3 scripts/pi_migration_inventory.py --json
uv run --project backend python -m pytest tests/pi_migration/test_count_to_zero.py -q
python3 scripts/security_benchmark.py --fail-on-threshold
python3 scripts/feature_docs.py --seed-missing --generate-site --check
compass-forge gate before --summary && compass-forge gate after --summary   # 0 new failures attributable
```

**Acceptance:** same-model-different-endpoint canonicalization proven (one `model_id`, distinct `endpoint_id`s); zero secret leakage in logs/config snapshots; lockfiles reproducible; protocol contract green; ratchet still 0; inherited (V6) vs new failures separated; `LLMServer` rows untouched.
**Rollback:** restore prior package pins/lockfiles/worker checkout; disable canonical catalog via `PI_MODEL_MANAGEMENT_MODE=legacy_compat`.

### Wave 2 — `compat-routing` (≈ old CF-789 + CF-790 + CF-794 + CF-804)

**Goal:** Pi becomes the canonical resolver for BOTH engines; legacy config migrates idempotently without silent loss; bounded deprecated adapter; rollback + migration observability; fail-closed removal criteria defined.
**Design outputs:** migration/projection layer (legacy readers resolve through Pi catalog views; legacy writes route through canonical write APIs with provenance tags); per-row lineage + migration audit log + switchboard (`PI_MODEL_MANAGEMENT_MODE`, `agentic_engine_default`, per-project `agentic_engine`, `llmserver_compat_mode`); engine resolution matrix (V3) preserved at all dispatcher verbs; deprecation headers + diagnostics; rollback runbook v1; **new** `tests/pi_migration/test_model_management_migration.py` + `test_model_management_rollback.py` (V14).
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
python3 scripts/security_benchmark.py --fail-on-threshold
```

**Acceptance:** dry-run-then-execute migration is idempotent (second run no-op); canonical mapping/status stable; source data recoverable (diff counts + checksums); secret reference resolves without plaintext export; per-dispatch exactly one usage/route row; engine/provider failure never switches engines; deprecated clients get documented adapter/deprecation behavior and create no new identity; unsupported/malformed rows remain `legacy_only`/`blocked` with reason; rollback drill performed and recorded.
**Rollback:** §7.4 switch sequence + reverse migration script; re-run W2 acceptance to prove reversion.

### Wave 3 — `embeddings-controls` (≈ old CF-791 + CF-794 + CF-799)

**Goal:** one coherent vector space with explicit embedding identity; chat endpoint changes never silently alter embeddings; expose temperature/thinking/effort controls; clear Pi-vs-Istara engine buttons with evidence-backed comparative summaries.
**Design outputs:** embedding policy keyed by canonical model identity; dimension/dtype/normalization/endpoint invariant in gateway + benchmark surface (drift requires explicit compat flag + owner sign-off); chat control propagation (`temperature`, `max_tokens`, `thinking_level`, `timeout_ms`, `max_retries`) via the existing bind-params path; selector UX rework in `frontend/src/lib/modelCatalog.ts` + `frontend/src/components/settings/ProjectSettingsView.tsx` (V15) with honest comparative summaries sourced from benchmark evidence (research-spine grounded; provisional status — never fabricated claims); accessibility contract; scenario `79-engine-selector.mjs`.
**Verification:**

```bash
uv run --project backend python -m pytest tests/pi_production/test_w8_embeddings_gateway.py \
  tests/pi_production/test_w8_ux_parity.py tests/pi_production/test_w6_engine_selection.py \
  tests/pi_production/test_w1_agentic_contract.py tests/test_pi_runtime_endpoints.py \
  tests/test_rag_resilience.py tests/test_research_validity_contract.py -q
npm --prefix frontend ci && npm --prefix frontend run test:unit -- --run
npm --prefix frontend run lint && npm --prefix frontend run build
node --test tests/simulation/scenarios/79-engine-selector.mjs
python3 scripts/feature_docs.py --seed-missing --generate-site --check
```

**Acceptance:** embedding dimension/model mapping identical before/after each migration step (invariant probe green both engines); no duplicate embedding identity accepted; chat endpoint change leaves embedding profile unchanged and identity visible in safe metadata; selector precedence/validation stable; comparative summaries cite evidence provenance and stay provisional.
**Rollback:** restore prior profile version + settings; vectors remain keyed to their recorded profile (no silent reindex).

### Wave 4 — `petals-audio` (≈ old CF-792 + CF-793 + CF-800)

**Goal:** preserve donor opt-in, identity pinning, security boundaries, compute donation/scheduling, same-model donor isolation, fail-closed 503 unavailable; add governed audio-model settings (local Whisper, compatible remote Whisper, supported diarized providers) without inventing unsupported local Pi audio behavior.
**Design outputs:** Petals — no bridge changes in early waves; authorization/consent/scheduling test matrix; donor rows never Pi-catalog capacity entries. Audio — canonical `AudioModelProfile` contract (§5.7); interview + microphone + channel flows; capabilities + secrets + fallbacks; local-only/optional-provider behavior explicit; no secrets in raw config payloads; **new** `tests/pi_production/test_research_spine_donor_routing.py` (V14).
**Verification:**

```bash
uv run --project backend python -m pytest tests/petals_bridge/test_petals_bridge.py \
  tests/pi_production/test_same_model_donor_isolation.py tests/pi_production/test_research_spine_donor_routing.py \
  tests/test_compute_registry_hardening.py tests/test_project_scope_contracts.py \
  tests/compute_cases/config.py tests/compute_cases/retries.py -q
uv run --project backend python -m pytest tests/test_transcription.py tests/test_files.py \
  tests/test_integration_interview.py tests/pi_production/test_w3_research_spine.py \
  tests/test_research_validity_contract.py tests/test_synthetic_provisional_boundary.py -q
python3 scripts/security_benchmark.py --fail-on-threshold
```

**Acceptance:** relay/browser donor with consent/health/project authorization is pinned to the donor, records route evidence, deterministic result; any missing admission condition → typed 503, never paid fallback; donor never selected as ordinary Pi capacity; local Whisper / remote Whisper / diarized / unsupported / missing-credential / low-ICR / ffmpeg-unavailable inputs behave explicitly, bounded, project-scoped, correctly marked `needs_review`/unavailable; raw source spans + provenance preserved; no transcript/tag reportable before gates. Mocked HTTP + local seams only — no live audio provider or model load.
**Rollback:** disable bridge/Pi-petals mode; retain existing local Whisper path; audio profiles revert to local-only.

### Wave 5 — `qa-docs-vps` (≈ old CF-795 + CF-796 + CF-797/798/804/805 + DEC-2)

**Goal:** final integration: living feature docs + manifests regenerated; deterministic Compose QA coverage for every accepted feature; security benchmark + broad focused suites; then VPS acceptance per the `vps` skill (§9) and cleanup of only initiative-owned disposable artifacts.
**Design outputs:** regenerated living feature docs; `testing/feature_coverage.yml` + `qa/runtime_capabilities.json` obligations for all changed paths; VPS single-service acceptance Compose (§9.2); VPS runbook + rollback state.
**Verification (public/testing-branch deterministic part):**

```bash
python3 scripts/feature_docs.py --seed-missing --generate-site --check
uv run --project backend python -m pytest tests/test_feature_docs.py tests/test_feature_obligations.py \
  tests/test_qa_stack_contract.py tests/test_qa_reset_seed.py tests/test_qa_artifacts.py \
  tests/test_synthetic_provisional_boundary.py tests/test_provider_contracts.py -q
docker compose -f docker-compose.yml config --quiet
for p in contract synthetic reset audit live ui; do \
  docker compose -f docker-compose.qa.yml --profile $p config --quiet; done
./scripts/istara-qa.sh render
python3 scripts/check_feature_obligations.py --base origin/testing --head HEAD
python3 scripts/check_integrity.py && python3 scripts/check_ci_governance.py && python3 scripts/check_test_harness.py
python3 scripts/check_public_tree_clean.py --base origin/testing --head HEAD
uv run --project backend python -m pytest tests/pi_benchmark/test_b1_contract.py -q
uv run --project backend python -m pytest tests/pi_benchmark/test_live_driver.py -q --collect-only   # render-only; live lane owner-gated
python3 scripts/security_benchmark.py --fail-on-threshold
compass-forge gate before --summary && compass-forge gate after --summary   # 0 NEW failures attributable
```

**VPS commands (owner-authorized only; every remote command via the vps skill's `vpsctl.py` — C7, never raw SSH):** see §9.
**Acceptance:** feature-doc parity + generated manifests/site green; every accepted feature has a deterministic contract lane; security benchmark pass; 0 new gate failures attributable to the wave; VPS: strict-profile proof, firewall/DOCKER-USER evidence agrees with the approved port list, audit chain anchored, rollback available until owner accepts, only initiative-owned artifacts removed, `main` untouched.
**Rollback:** VPS deployment identity + prior image digest preserved until post-deploy checks pass (§9.5); Compose/deps revert to prior wave state.

## 9. Isolated VPS acceptance and cleanup (replaces multivac — DEC-2, C1)

The managed VPS (`vps` skill) is the only staging-acceptance path for this run. `vpsctl.py` is **not** in this repo — every invocation uses `~/.pi/agent/skills/vps/scripts/vpsctl.py` (C7); never raw `ssh` or ad-hoc shell scripts.

### 9.1 Procedure (strict order)

1. **Preflight:** `python3 $VPSCTL preflight` — keychain-backed SSH identity (`id_ed25519_capi`, `IdentitiesOnly`, strict host-key checking), helper integrity, audit DB health. Never print key material.
2. **Inventory (read-only):** `python3 $VPSCTL inventory` — observed Compose projects/containers and current public exposure. Existing workloads are inventory-only; nothing is mutated without explicit owner authorization.
3. **Service creation:** Dokploy Docker Compose service from the repository using the strict single-workload profile (§9.2). No Dokploy Domain, proxy labels, external network, Docker socket, `network_mode: host`, privileged, or host PID/IPC. Secrets only in the Dokploy secret/environment UI.
4. **Preview before deploy:** reject any rendered Compose that adds a shared/proxy network or a second service.
5. **Deploy preserving identity:** capture current deployment identity + image digest as rollback target; deploy.
6. **Verify:** `verify-isolation` (one attached network, one endpoint, `Internal: true`, no default route, no host/other-container reachability) and `verify-exposure` with the documented approved port set (IPv4+IPv6).
7. **Firewall evidence:** check firewall before/after and the `DOCKER-USER` chain (published ports bypass ordinary rules). **No firewall change without owner approval** — escalate unexpected exposure; never remove a port until its owning workload is known.
8. **Audit:** `audit-verify` then `audit-anchor` (signs the chain head with the SSH identity). Report verified port set, image identity, isolation proof, firewall result, rollback state, and audit event ids — never secrets or raw output.

```bash
VPSCTL=~/.pi/agent/skills/vps/scripts/vpsctl.py
python3 $VPSCTL preflight
python3 $VPSCTL inventory
python3 $VPSCTL deploy --compose <strict-template> --project istara-pi-model-migration-<run>   # one target
python3 $VPSCTL verify-isolation --port <approved-port>
python3 $VPSCTL verify-exposure --ports <approved-port-set>
python3 $VPSCTL audit-verify && python3 $VPSCTL audit-anchor
# cleanup of initiative-owned disposable artifacts only, after owner acceptance
```

### 9.2 Strict single-workload Compose baseline (from the vps skill)

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

The repository's production `docker-compose.yml` is 8-service (V12); the strict profile permits exactly one service with inbound-only connectivity. The default acceptance target is therefore a **dedicated single-service acceptance image** (minimal read-only bundle exercising the acceptance contract — healthcheck + one approved port), built on the testing branch. If the acceptance contract genuinely requires multi-container topology, a database, outbound API access, or a domain proxy, that is an explicit security exception: **stop, describe the minimum connectivity graph, obtain written owner approval, and record the exception in the audit DB before any change.** Never silently weaken isolation.

### 9.4 Cleanup

After acceptance: remove **only** initiative-owned disposable artifacts (this run's Compose service, named volumes if created, rendered previews; local audit rows stay in the gitignored audit DB). Existing workloads and the audit database are untouched. Record cleanup commands through `$VPSCTL ssh`.

### 9.5 Rollback

Until the owner accepts: preserve prior deployment identity/digest; re-deploy prior Compose on verification failure; record the event in the audit chain. No firewall rollback is needed if no firewall change was made (the default).

## 10. Task breakdown (CF shape; generated at owner approval)

| Wave | This-run CF tasks (generated at approval) | Scope checklist (old-run anchors, reference only) |
|---|---|---|
| `foundation` | PLAN-A/B/C + REPLAN-A/B/C-r1 + REMASTER-A-r1 synthesis + vote + owner gate (planning-only) | old CF-797/798/802/803 obligations folded into planning + later waves |
| `pi-catalog-secrets` | W1 implementation + reviewer + fixer | old CF-787/788/801 |
| `compat-routing` | W2 implementation + reviewer + fixer | old CF-789/790/794/804 |
| `embeddings-controls` | W3 implementation + reviewer + fixer | old CF-791/794/799 |
| `petals-audio` | W4 implementation + reviewer + fixer | old CF-792/793/800 |
| `qa-docs-vps` | W5 implementation + reviewer + fixer | old CF-795/796/797/798/804/805 |

Every implementation task carries: `gate before` baseline, focused `gate after` with new-vs-inherited separation, command evidence, `self_report`, reviewer `review_verdict`, fixer loop on findings; major transitions (S2→S3, S4→S5) stop at owner gates. Out-of-scope defects become new tasks via `task import`, never silent edits.

## 11. Test ownership and coverage matrix

Extend existing tests; never create an unowned parallel suite. Gate rules `architecture_drift` and `test_ownership` are load-bearing: every behavior-changing file needs an owning test/doc obligation in `testing/feature_coverage.yml` or a reviewed mechanical exception.

| Surface | Existing anchors | New/changed obligations |
|---|---|---|
| Pi package/protocol | `pi-runtime/test/*.test.mjs`, `pi-runtime/PROTOCOL.md`, `test_engine_http_provider.py`, `test_runtime_hardening.py`, `test_protocol_version_per_frame.py` | exact version/lockfile provenance; no dependency drift; protocol-v2 compatibility after upgrade |
| Canonical provider catalog | `test_model_provider_contract.py`, `test_pi_runtime_endpoints.py`, `test_endpoint_secrets.py` | identity tuple, aliases, capabilities, credential custody, duplicate handling |
| LLM Server compatibility | `test_llm_servers.py`, `test_settings_agentic_pi_endpoints.py`, simulation 36 | idempotent mapping, deprecated adapter, blocked rows, rollback |
| Engine routing | `test_w1_agentic_contract.py`, `test_w1_dispatcher_authority.py`, `test_w1_usage_ledger.py`, `test_w6_engine_selection.py`, `test_w4_a2a_handlers.py` | both engines through canonical target; precedence; no fallback; one-row accounting |
| Count-to-zero | `scripts/pi_migration_inventory.py`, `test_count_to_zero.py`, `legacy_allowlist.yaml` | product remains 0; only documented permanent infrastructure entries |
| Embeddings | `test_w8_embeddings_gateway.py`, `test_w8_ux_parity.py`, `test_rag_resilience.py` | profile identity, dimension/dtype mismatch refusal, no cache writes on mismatch |
| Petals/compute | `tests/petals_bridge/test_petals_bridge.py`, donor isolation, `tests/compute_cases/*` | consent, project scope, exact node identity, typed 503, no paid fallback |
| Audio/research | `test_transcription.py`, `test_files.py`, `test_integration_interview.py`, research-spine tests | profile capability, diarization, ICR/review, raw evidence units/provenance |
| Frontend/UI | `frontend/src/lib/modelProviders.test.ts`, `modelCatalog.test.ts`, `79-engine-selector.mjs` | no duplicate options, explicit engine/model/endpoint distinction, accessibility |
| QA/docs | `test_feature_docs.py`, `test_feature_obligations.py`, QA stack/provisional/obligation tests | changed-path ownership, generated docs parity, provisional-only QA, fresh-DB validation (C8) |
| Security | `test_security_benchmark.py`, `security/control_matrix.json` | triggered benchmark + control/evidence updates if controls change |

## 12. Documentation and manifest obligations

Update living docs in the same implementation initiative (dated historical plans stay immutable; write successor records when facts change):

- Architecture: `docs/architecture/agentic_core.md` (canonical identity/transport boundary, legacy adapter vs legacy infrastructure, route evidence); `docs/architecture/research-validity-contract.md` (only if spine-visible seams change — audio evidence, route provenance); `docs/architecture/self-improvement-governance-contract.md` (only if self-improvement paths change).
- Feature pages at minimum: `settings/llm-servers`, `chat/model-controls`, `chat/audio`, `interviews/transcription`, `settings/compute-donation`, `compute/pool` (+ `agents/registry`, `agents/a2a` if engine metadata changes) — plus any new provider/credential/audio pages the feature inventory discovers.
- Repo docs: `README.md`, `README.pt-BR.md`, `DOCUMENTATION.md`, `TESTING.md`, `CHANGE_CHECKLIST.md`, `SYSTEM_CHANGE_MATRIX.md`, `testing/TESTING_STRATEGY.md` where contracts change.
- `testing/feature_coverage.yml` + `qa/runtime_capabilities.json` for all changed paths.
- Security: `security/control_matrix.json`, `security/SECURITY_BENCHMARK.md`, `tests/test_security_benchmark.py` only when a control/evidence path/standard version/trigger changes.
- Regenerate with `python3 scripts/feature_docs.py --seed-missing --generate-site --check` in the same change; attach output as evidence; never hand-edit generated site/manifest files. No private VPS host details, keys, or endpoint fingerprints in public docs or QA artifacts.

## 13. Security benchmark and review checklist

Mandatory on any auth/provider/secret/agentic/Petals/audio change: `python3 scripts/security_benchmark.py --fail-on-threshold` (baseline V7: 28/28, 100.0%). Record the scorecard as CF command evidence; update `security/control_matrix.json` + `security/SECURITY_BENCHMARK.md` + `tests/test_security_benchmark.py` when a control, evidence path, standard version, or trigger pattern changes.

Reviewer coverage must include: credential source precedence/rotation; encryption context/version compatibility for migrated `api_key` values; SSRF/URL normalization + loopback/HTTPS policy for custom endpoints; OAuth redirect/token custody; admin/project authorization on catalog/credential/migration/Petals-consent/audio routes; enumeration + safe redaction in UI/API/telemetry/logs; no secrets in migration exports, Compose interpolation, QA artifacts, or CF evidence; worker private-pipe binding, protocol limits, retry/cost accounting, malformed-frame behavior; explicit engine selection never bypassing Research Spine route evidence; donor consent/project scope/same-model isolation/typed 503; audio upload size/type/scanner/temp-file cleanup, remote provider credentials, diarization privacy; no public VPS/multivac references, no firewall changes, no unrelated workload cleanup. Inherited gate failures (V6) are never suppressed silently: record baseline vs post-change comparison and either fix new failures or create an explicit, expiring, justified suppression under project policy.

## 14. Risks and mitigations (consolidated register)

| ID | Risk | Sev | Mitigation | Rollback |
|---|---|---|---|---|
| R1 | Package update breaks worker protocol / structured contract | High | Pin exact versions; protocol-v2 handshake + contract suites both sides; compatibility statement before bump | Restore prior pins/lockfiles/worker checkout |
| R2 | Duplicate model identity / split-brain | High | Provider-qualified ids + uniqueness constraints + collision tests; aliases provenance-only | Restore canonical mapping; source rows intact |
| R3 | Secret coupling drift (Fernet → Keychain/env) | High | In-memory decrypt/re-encrypt; credential status matrix; redaction audit; no plaintext export | Keep source encrypted field + compat reference |
| R4 | Silent cross-engine fallback | High | Typed per-engine errors; one-ledger-row accounting; dispatcher contract tests | Explicit mode revert (§7.4) |
| R5 | Embedding/vector drift corrupts retrieval | High | Profile persisted + startup probe; block mismatch before cache/write; vectors keyed to recorded profile | Restore prior profile; never implicit reindex |
| R6 | Donor boundary erosion / paid fallback hides failure | High | No early bridge changes; consent+pin+503 tests; isolation invariant green | Disable bridge mode; donor registry unchanged |
| R7 | Compatibility adapter becomes second source of truth | High | Canonical-only writes; count-to-zero ratchet + allowlist audit per wave | Re-enable read adapter; never delete rows |
| R8 | VPS isolation/exposure defect | High | Strict profile + preview rejection + verify-isolation/exposure + firewall/`DOCKER-USER` evidence + audit-anchor; no firewall change w/o owner approval | Prior deployment identity/digest retained; redeploy prior Compose |
| R9 | VPS credential/exposure leak | High | Secrets only in Dokploy secret UI; `vpsctl.py` audit chain; no secrets in args/history/chat | Revoke + rotate; audit-verify chain |
| R10 | QA false confidence / contaminated DB | Med | Contract stub labeled non-quality; synthetic provisional guard; live lane owner-gated; fresh disposable DBs (C8) | Stop QA project; never promote synthetic artifacts |
| R11 | Audio provider unsupported/private behavior | Med | Capability contract + local/mocked tests + `needs_review`; no implicit fallback | Return unavailable; retain local Whisper path |
| R12 | Inherited gate debt masks new drift | Med | V6 baseline recorded; per-wave before/after diff; 0-new-failures rule | — |
| R13 | Docs/generated drift | Med | Feature obligation classifier + feature-doc regeneration in same task | Block acceptance until docs/manifests regenerated |

## 15. Coverage matrix (requirement → this master plan → draft inputs)

| Requirement | This master plan § | Draft inputs incorporated |
|---|---|---|
| Verified boundary inventory | §2 | C §2 (primary), A §2, B §2 (V1–V17) — re-verified at synthesis time |
| Canonical identity model | §5.1–5.3 | A §5.1–5.3 (schema depth), B §4.1–4.3 (rules + V10 correction), C §3 (contracts) |
| Resolver/transport boundary | §5.2 | A §5.2 (transport classes), B §4.2 (verb list), C §3 (single resolution request) |
| Engine selection + rollback semantics | §5.4 | A §5.4, B §4.4 (V3 precedence), C §3 (explicit selection) |
| Retirement: three orthogonal axes | §6 | A §6/§7 (row states + promotion criteria), B §5 (S0–S5 stages + transition rule), C §4 (row states with canary + controls) — merged into two axes + mode registry |
| Data/secret migration + rollback | §7 | A §6 (preflight/mapping), B §6 (rollback switch sequence), C §4/§6 (idempotency + fresh-DB rule) |
| Wave plan + exact verification | §8 | A §8 (most complete command sets), B §7 (compute_cases/b1_contract additions, env prerequisites), C §5/§6 (consolidated baseline + impact packs) — all re-verified (V13–V16) |
| VPS acceptance (replaces multivac) | §9 | vps skill + `references/dokploy-and-isolation.md` (authoritative); A §8 W5 + B §9 (C1/C5/C7); carried drafts' multivac sections superseded |
| Task breakdown / CF shape | §10 | B §8 (wave→CF mapping), A §8, C §5 — re-baselined to this run's manifest (C2) |
| Test ownership | §11 | A §9, B §10 (V13/V14 anchors), C §3 |
| Docs/manifests/security | §12–13 | A §10–11, B §10, C §7 |
| Risks | §14 | A §12 + B §11 merged (R1–R13, VPS risks R8/R9 added) |
| Definition of Ready/Done + gates | §16 | A §13, B §12, C §4/§8 |

## 16. Definition of Ready / Done and owner gates

### Ready for implementation

- This master plan (or the vote-winning synthesis) is frozen and **owner-approved at the explicit plan gate**.
- Exact canonical identity, credential, migration-state, engine-transport, embedding-profile, audio-profile, and Petals boundaries are accepted.
- CF work orders name dependencies, changed-path ownership, tests, docs, rollback, and gates per wave.
- Latest Pi release re-checked passively at dependency-update execution time; no live LLM/model load required.
- Baseline gate output and known inherited failures (V6) attached; no implementation begins while the plan gate is pending.

### Done for the initiative

- All waves green with command evidence + reviewer pass; post-change gate evidence shows 0 new failures attributable, or explicit owner-approved residual risk.
- Canonical model/endpoint/credential behavior proven without duplicate identity semantics or secret leakage.
- Both engines explicitly selectable and independently fail-closed with one usage/route record per dispatch.
- LLM Server migration idempotent, reversible, observed, deprecated; no row deleted without the separate removal gate.
- Embedding profile, Petals bridge, audio/transcription, Research Spine, UI, QA/Compose, security benchmark, docs/manifests, and test ownership obligations complete.
- VPS acceptance (if authorized/required): strict-profile isolation/exposure proof, firewall evidence, audit-anchor, cleanup of only initiative-owned artifacts; otherwise explicitly marked blocked/advisory and public QA stays green.
- Lifecycle status/ledger, CF evidence, findings register, and final summary accurately describe the result. No implementation stage claims completion from a plan-only artifact.

### Owner gates

1. **Plan gate (this stage):** conductor stops here; owner approves the frozen consensus plan before any implementation task is generated/released.
2. **Transition gates:** S2→S3 and S4→S5 (§6) require owner approval with acceptance evidence.
3. **VPS/firewall gate:** any firewall/port/exposure change requires explicit owner approval (§9.1.7).
4. **Ship gate:** merge/push/PR is the conductor ship stage's job, owner-gated by cast config; `main` is never touched.

## 17. Handoff note

This is the slot-A **MECE master-plan synthesis** — one complete plan, not a concatenation: the three drafts' state machines are merged into two orthogonal axes + mode registry (§6), their risk registers into one table (§14), their rollback playbooks into one sequence (§7.4), and their verification command sets into per-wave blocks verified against the tree (§8). Corrections C1–C8 are carried and re-verified (§3). Next: the consensus vote round compares the master-plan candidates; the winner is frozen and the conductor stops at the **owner approval gate** before any implementation task is released. No source implementation, lifecycle-plan edit beyond this artifact, Docker/VPS start, live provider call, model load, merge, push, or PR is authorized from this stage.

<!-- /consensus-winning-plan:ISTARA-PI-MODEL-MIGRATION-20260822-241fd9bafde32a2921e12fb79ffc33bbfdbacb29953e3e56ae5b7841a62748a5 -->

## Decision log

<!-- consensus-winner-decision:ISTARA-PI-MODEL-MIGRATION-20260822-241fd9bafde32a2921e12fb79ffc33bbfdbacb29953e3e56ae5b7841a62748a5 -->
DEC-consensus-winner | 2026-08-22 | S1-plan | conductor
Context: three architect cross-votes completed
Decision: slot a selected from ISTARA-PI-MODEL-MIGRATION-20260822-REMASTER-A-r1
Why: votes={"a": {"candidate_id": "65a2de29913abc7cbda40c9edb336a3634b50cd832c3955877674f374761a587", "task": "ISTARA-PI-MODEL-MIGRATION-20260822-VOTE-A", "vote": "b"}, "b": {"candidate_id": "ec3a76e75d82e2d4495aec7d0c251f128fda99643de77b1180f56c00f9bc34ed", "task": "ISTARA-PI-MODEL-MIGRATION-20260822-VOTE-B", "vote": "a"}, "c": {"candidate_id": "ec3a76e75d82e2d4495aec7d0c251f128fda99643de77b1180f56c00f9bc34ed", "task": "ISTARA-PI-MODEL-MIGRATION-20260822-VOTE-C", "vote": "a"}}; tiebreak_used=False; plan_file=docs/build-stream/plans/istara-pi-model-migration-20260822-master-a.md



### DEC-1 | 2026-08-22 | S0-frame | owner

Context: The prior 2026-08-18 run paused on a Conductor finalization hold; Skills and Compass Forge were subsequently fixed, and the native Rust Compass Forge cutover is now active.

Decision: Freeze the 2026-08-18 run as reference (do not resume or mutate it) and start a fresh matched-release run on the native stack: new worktree/branch, new CF project and spec (CF-SPEC-1), new strict-wave manifest, new cast with the owner-approved roster, drafts carried forward. Keep the same delivery scope and boundaries.

Why: The cutover directive requires a matched release (native binary + current Skills + fresh process configuration) rather than resuming a Python-era run with the new stack.

### DEC-2 | 2026-08-22 | S0-frame | owner

Context: Multivac is no longer available for staging acceptance.

Decision: Replace multivac acceptance with the managed VPS (wildsync) following the `vps` skill: Dokploy Docker Compose strict single-workload profile, vpsctl.py preflight → inventory → deploy → verify-isolation → verify-exposure → audit-anchor, firewall/DOCKER-USER evidence, and owner approval before any port/firewall change.

Why: The vps skill is the maintained, audited deployment path for this host.

## Ledger

### L-1 | 2026-08-22T11:36:00Z | S0-frame | owner | framer | Phase 0

Did: Created fresh isolated worktree `istara-pi-model-management-migration-20260822` (branch `conductor/istara-pi-model-management-migration-20260822`, base `origin/testing@15260a78`); carried forward the three 2026-08-18 architect drafts as `docs/build-stream/plans/carried-20260818-plan-{a,b,c}.md`; initialized the native CF project (recipe `istara-main`, workspace `/Users/user/Documents/compass-forge`); created execution spec `CF-SPEC-1`; wrote the new strict-wave manifest `docs/build-stream/manifests/istara-pi-model-management-migration-20260822.json` (SHA-256 `b9c8ff0ca1c0521fff18e27d3caf53e11fac89c6fb9a44e1656688ac1cf5a8fd`); registered the new run's actor roles in the active recipe; generated the planning-only tasks `ISTARA-PI-MODEL-MIGRATION-20260822-PLAN-A/B/C` and the new cast with the owner-approved roster (see table above; `plan_gate=true`, `ship.auto_pr=false`, pending `wave_binding`).

Result: Fresh matched-release planning stage ready. No implementation/review roots exist; the cast has no executable `waves` state until owner approval binds the winning plan to the manifest. No worker was launched yet, no model preflight probe was sent yet, no source code changed, and no Docker/VPS workload was touched.

Verified: `resolve-pin.sh` (pin `559af310…`); native `compass-forge status --target <wt>` (project/recipe resolved); `make_pipeline.py --wave-manifest …` (3 planning tasks imported, roles verified); `make_cast.py --wave-manifest …` (cast written, roster asserted); manifest SHA-256.

Next: Run conductor preflight (real one-shot probes for the three distinct model routes), spawn the detached conductor, and monitor the three-architect planning stage with status updates every ~5 minutes.

## Phase 0 — architecture and migration plan

### Frame

This is a Full security/architecture change. The plan must cover the complete migration boundary: storage/migrations, encryption, provider catalog provenance, endpoint identity, engine dispatch, embeddings, Petals, audio, UI, tests, docs, CI/Compose, and VPS operations as one dependency graph. The three carried-forward drafts are inputs, not blind re-runs.

### Definition of Ready for implementation

- Winning architect plan is frozen and owner-approved through the Conductor approval gate.
- All CF tasks have explicit scope, dependencies, impacted paths, and verification commands.
- Latest Pi package versions and standalone compatibility contract are recorded.
- Migration/rollback contract and LLM Server deprecation/removal criteria are explicit.
- Testing branch Docker automation and VPS acceptance are represented in the task graph.
- `gate before` baseline and inherited debt are recorded.
- No implementation task is dispatched before these conditions hold.

### Findings register

| ID | Sev | Dim | Where | Finding | CF task | Status |
|---|---|---|---|---|---|---|
| F-1 | High | Architecture | Carried 2026-08-18 drafts reference multivac staging and old-run CF task ids (CF-787..CF-805) | Must be re-baselined to the managed-VPS contract (vps skill, DEC-2) and this run's six-wave manifest; corrected in draft A, must be held through synthesis | ISTARA-PI-MODEL-MIGRATION-20260822-PLAN-A | open — corrected in draft A; bind in master plan |
| — | — | — | — | No independent review has run yet in this run. | — | pending |

## Final summary

Not yet shipped. This lifecycle intentionally stops before implementation until the independent architect consensus plan is frozen and the owner approval gate is passed.

### L-2 | 2026-08-22T11:49:51Z | S1-plan | deepseek/deepseek-v4-flash | executor | draft <!-- bsc-ledger:ISTARA-PI-MODEL-MIGRATION-20260822-PLAN-A -->
Did: Wrote independent architect-A draft `docs/build-stream/plans/istara-pi-model-management-20260822-plan-a.md` (58 KB, 15 sections); carried the three 2026-08-18 drafts forward and independently verified every surface against the tree; re-verified Pi versions, migration ratchet, gate baseline, and test collection.
Result: Draft covers the six manifest waves, canonical identity model (model_id/endpoint_id/credential_ref/embedding+audio profiles), resolver/transport boundary, exact data+secret migration and rollback state machine, feature-flag/deprecation/removal criteria, test ownership, docs/manifest obligations, security benchmark coverage, and isolated VPS acceptance per the vps skill. Corrections C1-C6 recorded: multivac replaced by managed VPS (DEC-2, vpsctl.py preflight/inventory/verify-isolation/verify-exposure/audit-anchor, no firewall changes without owner approval); old-run CF task ids re-baselined to this run's waves; gate debt re-measured (30 inherited / 0 new); Pi latest re-verified at 0.84.2; worker deps prerequisite made explicit.
Verified: `npm view` → 0.84.2 / 0.84.2 (passed); `python3 scripts/pi_migration_inventory.py --json` → 1 allowlisted permanent site, ratchet 0 (passed); `compass-forge gate before --task ISTARA-PI-MODEL-MIGRATION-20260822-PLAN-A --summary` → fail, 30 inherited, 0 new (passed as baseline); `uv run --project backend --with pytest --with pytest-asyncio python -m pytest --collect-only -q` on 6 key surfaces → 62 tests collected (passed).
Next: Architect B and C independent drafts, then synthesis into one MECE master plan with coverage matrix; freeze plan and stop at the owner approval gate. No implementation before owner approval.

### L-3 | 2026-08-22T11:55:00Z | S1-plan | deepseek/deepseek-v4-pro | architect | draft <!-- bsc-ledger:ISTARA-PI-MODEL-MIGRATION-20260822-PLAN-B -->
Did: Independent architect-B draft written to `docs/build-stream/plans/istara-pi-model-management-migration-20260822-plan-b.md` (47 KB; no code touched). Independently re-verified the carried 2026-08-18 drafts A/B/C against the current tree and recorded corrections C1-C6: multivac retired -> managed VPS per vps skill (DEC-2); CF-SPEC-59/CF-787..805 graph superseded by CF-SPEC-1 + this run's six-wave manifest (foundation, pi-catalog-secrets, compat-routing, embeddings-controls, petals-audio, qa-docs-vps); gate baseline refreshed (30 failures / 0 new / 0 actionable, not the stale "80"); settings field corrected to `pi_api_endpoints: list[PiApiEndpoint]` (config.py:304); VPS strict single-workload profile vs 8-service docker-compose.yml reality check (dedicated single-service acceptance image or owner-approved connectivity exception, vps skill §decision-rule); environment prerequisites made explicit (`uv sync --extra dev`; `cd pi-runtime && npm ci` before worker-backed tests).
Result: Draft covers canonical identity model (model_id/endpoint_id/credential_ref/embedding+audio profiles), resolver+transport boundary, engine precedence (per-call > header x-istara-agent-engine > project agentic_engine > settings.agentic_engine_default="legacy"; no silent fallback), reversible retirement state machine S0-S5 with feature-flag registry + deprecation/removal criteria, exact data/secret migration + rollback playbook, per-wave acceptance + commands for all six manifest waves, isolated VPS acceptance/cleanup runbook (vpsctl.py preflight -> inventory -> strict single-workload profile -> rendered-Compose preview -> deploy preserving prior identity -> verify-isolation -> verify-exposure -> firewall/DOCKER-USER evidence -> audit-anchor; no firewall change without owner approval), docs/manifests/security/test-ownership obligations, risk register R1-R11, Definition of Ready/Done + owner gates, coverage matrix vs carried drafts A/B/C. ISTARA-PI-MODEL-MIGRATION-20260822-PLAN-B.
Verified: `compass-forge status/next --target <wt>` (project resolved, runtime rust, python_fallback false); `gate before --summary` (fail, 30 failures secret_flow/unexpected_large_files, new_failures=0, actionable=0, drift route=4 type=2, warnings=188); `npm view @earendil-works/pi-agent-core|pi-ai version` (0.84.2 both; tree pins 0.83.0/0.80.10); `uv run --project backend python -m pytest tests/pi_migration/test_count_to_zero.py -q` (3 passed); `python3 scripts/security_benchmark.py --fail-on-threshold` (28/28 pass, 100.0%); `python3 scripts/feature_docs.py --seed-missing --generate-site --check` (86 features green, 224 artifacts); boundary file sweep + `vpsctl.py --help` (subcommands preflight/inventory/audit-verify/audit-anchor/verify-isolation/verify-exposure/ssh; 3 test paths recorded as new obligations: test_research_spine_donor_routing.py, test_model_management_migration.py, test_model_management_rollback.py). CF evidence rows 28-36 on ISTARA-PI-MODEL-MIGRATION-20260822-PLAN-B.
Next: Architect C draft, then consensus synthesis (A/B/C -> one MECE master plan -> vote); conductor freezes the plan and stops at the owner approval gate before any implementation task is released.

### L-4 | 2026-08-22T12:02:16Z | S1-plan | deepseek/deepseek-v4-flash | architect | draft <!-- bsc-ledger:ISTARA-PI-MODEL-MIGRATION-20260822-REPLAN-A-r1 -->
Did: Repaired the slot-A consensus draft. The L-2 slot-A draft had landed at the misnamed path `docs/build-stream/plans/istara-pi-model-management-20260822-plan-a.md`, which the synthesis phase cannot consume; wrote the full 15-section S1 draft to the task's authoritative `plan_file` `docs/build-stream/plans/istara-pi-model-migration-20260822-plan-a.md` and removed the duplicate in the same commit. Re-verified every current-tree fact at repair time and added correction C7: `vpsctl.py` lives in the vps skill (`~/.pi/agent/skills/vps/scripts/vpsctl.py`), not in repo `scripts/` (subcommands verified: preflight, inventory, audit-verify, audit-anchor, verify-isolation, verify-exposure, ssh).
Result: Authoritative slot-A draft exists at the path the synthesis phase reads; covers the six manifest waves, canonical identity model (model_id/endpoint_id/credential_ref/embedding+audio profiles), resolver/transport boundary, exact data+secret migration and rollback state machine, feature-flag/deprecation/removal criteria, test ownership, docs/manifest obligations, security benchmark coverage, and isolated VPS acceptance per the vps skill (C1/C5/C7). ISTARA-PI-MODEL-MIGRATION-20260822-REPLAN-A-r1.
Verified: `npm view` -> 0.84.2 / 0.84.2 (passed; tree pins 0.83.0 / 0.80.10); `python3 scripts/pi_migration_inventory.py --json` -> 1 allowlisted permanent site, ratchet 0 (passed); `compass-forge gate before --task ISTARA-PI-MODEL-MIGRATION-20260822-REPLAN-A-r1 --summary` -> fail, 30 inherited, 0 new, 0 actionable (passed as baseline); `pytest --collect-only` on six key surfaces -> 62 tests collected (passed); `vpsctl.py --help` -> 7 subcommands (passed); `git diff --check` clean. CF evidence rows on ISTARA-PI-MODEL-MIGRATION-20260822-REPLAN-A-r1.
Next: Architect B and C drafts -> consensus synthesis into one MECE master plan with coverage matrix; freeze plan and stop at the owner approval gate before any implementation task is released.

### L-5 | 2026-08-22T12:18:00Z | S1-plan | gpt-5.6-luna | architect | draft <!-- bsc-ledger:ISTARA-PI-MODEL-MIGRATION-20260822-PLAN-C -->
Did: Updated the authoritative slot-C draft `docs/build-stream/plans/istara-pi-model-migration-20260822-plan-c.md` after rechecking the current tree and all three carried drafts; corrected its focused verification matrix to use the existing `tests/test_llm_servers.py` and frontend `test:unit` script.
Result: Independent plan covers the Pi canonical catalog/resolver and dependency boundary, legacy storage/routing/encryption migration, both explicit engines, embeddings/vector-space invariant, Petals isolation, audio/transcription capability contracts, UI, testing-branch QA, managed VPS/Dokploy/vpsctl acceptance, security/docs obligations, reversible retirement, and owner gates. No implementation or live workload changes.
Verified: pinned native `compass-forge status`, `next`, and compact `agent-brief` (project resolved; Rust runtime); Compass Forge impact/why/test-impact; `python -m pytest tests/pi_migration/test_count_to_zero.py -q` -> 3 passed; `git diff --check` clean; current-tree existence check corrected the stale/nonexistent test path and frontend script.
Next: Synthesize A/B/C into one MECE master plan, freeze it, and stop at the owner approval gate.

### L-6 | 2026-08-22T12:09:26Z | S1-plan | deepseek/deepseek-v4-pro | architect | draft <!-- bsc-ledger:ISTARA-PI-MODEL-MIGRATION-20260822-REPLAN-B-r1 -->
Did: Repaired the slot-B consensus draft. The L-3 slot-B draft had landed at the misnamed path `docs/build-stream/plans/istara-pi-model-management-migration-20260822-plan-b.md`, which the synthesis phase cannot consume; wrote the full S1 draft to the task's authoritative `plan_file` `docs/build-stream/plans/istara-pi-model-migration-20260822-plan-b.md` and removed the misnamed duplicate in the same commit (mirroring REPLAN-A-r1/L-4). Re-verified every current-tree fact at repair time and added: correction C7 (`vpsctl.py` lives in the vps skill at `~/.pi/agent/skills/vps/scripts/vpsctl.py`, not repo `scripts/`; every VPS command in the draft now uses the skill path); V15 (repo QA/governance scripts and extra test anchors present; `scripts/multivac_*` and `tests/llm_servers.py` absent — never cited); V16 (frontend anchor path `frontend/src/components/settings/ProjectSettingsView.tsx`). No code touched.
Result: Authoritative slot-B draft exists at the path the synthesis phase reads; covers the six manifest waves, canonical identity model (model_id/endpoint_id/credential_ref/embedding+audio profiles), resolver/transport boundary, engine precedence (per-call > header x-istara-agent-engine > project agentic_engine > settings.agentic_engine_default="legacy"; no silent fallback), reversible retirement state machine S0-S5 with feature-flag registry + deprecation/removal criteria, exact data/secret migration + rollback playbook, per-wave acceptance + commands, isolated VPS acceptance/cleanup per the vps skill (C1/C5/C7), docs/manifests/security/test-ownership obligations, risk register R1-R11, Definition of Ready/Done + owner gates, coverage matrix vs carried drafts A/B/C. ISTARA-PI-MODEL-MIGRATION-20260822-REPLAN-B-r1.
Verified: `npm view` -> 0.84.2 / 0.84.2 (passed; tree pins 0.83.0 / 0.80.10); `python3 scripts/pi_migration_inventory.py --json` -> 1 allowlisted permanent site (legacy.py:599), ratchet 0 (passed); `compass-forge gate before --task ISTARA-PI-MODEL-MIGRATION-20260822-REPLAN-B-r1 --summary` -> fail, 30 inherited, 0 new, drift route=4/type=2, warnings=188 (passed as baseline); `uv run --project backend python -m pytest tests/pi_migration/test_count_to_zero.py -q` -> 3 passed; `python3 scripts/security_benchmark.py --fail-on-threshold` -> 28/28, 100.0%, pass; `python3 scripts/feature_docs.py --seed-missing --generate-site --check` -> 86 features, 224 artifacts, 0 seeded (passed); `python3 ~/.pi/agent/skills/vps/scripts/vpsctl.py --help` -> 7 subcommands (passed); 38/38 V13 test anchors present, 3/3 V14 absent (passed); `git diff --check` clean. CF evidence rows on ISTARA-PI-MODEL-MIGRATION-20260822-REPLAN-B-r1.
Next: All three authoritative drafts now exist (A repaired, B repaired, C); consensus synthesis reconciles them into one MECE master plan with a coverage matrix, freezes the plan, and stops at the owner approval gate before any implementation task is released.

### L-2 | 2026-08-22T12:10:00Z | S1-plan | owner | cast-manager | Phase 0

Did: Managed the cast during planning. Diagnosed PLAN-C blocked-loop: the architect-a REPLAN worker generated `backend/uv.lock` (1.5MB, untracked) while validating `uv run` commands, and the gate `after --new-only` treated it as a new large file, reopening PLAN-C repeatedly; architect-c had no fallbacks so escalation was inert. Removed the spurious file and added `backend/uv.lock` to `allowed_large_file_globs` + `ignored_file_globs` in the worktree and workspace recipes (config-only, no source code). Reopened PLAN-C and cleared the stale escalation state; architect-c re-dispatched (session 8/9).

Result: Gate `after --new-only` now reports zero new issues with uv.lock present. Architect-c can complete PLAN-C with valid finalization.

Verified: `compass-forge gate after --new-only --report-format json` (new_issues: []); `conductor.py status` (daemon up); sessions 8/9 architect-c active.

Next: Monitor planning to convergence; expect PLAN-C done, then MECE synthesis and owner approval gate.

### L-7 | 2026-08-22T12:15:38Z | S1-plan | gpt-5.6-luna | planner | istara-pi-model-migration-20260822-architect-c <!-- bsc-ledger:ISTARA-PI-MODEL-MIGRATION-20260822-MASTER-C -->
Did: istara-pi-model-migration-20260822-architect-c stage on task ISTARA-PI-MODEL-MIGRATION-20260822-MASTER-C (harness fallback entry; the model did not append one).
Result: task ISTARA-PI-MODEL-MIGRATION-20260822-MASTER-C finished; worktree head 15f26486.
Verified: see Compass Forge evidence rows on ISTARA-PI-MODEL-MIGRATION-20260822-MASTER-C (command + self_report + stage_attribution).
Next: conductor advances the pipeline on evidence.
### L-8 | 2026-08-22T12:17:22Z | S1-plan | deepseek/deepseek-v4-flash | synthesizer | synthesize <!-- bsc-ledger:ISTARA-PI-MODEL-MIGRATION-20260822-MASTER-A -->
Did: Synthesized the three immutable candidate snapshots (slot A `8b084d99…`, slot B `6ca5b84c…`, slot C `a7e88f54…`) into ONE MECE master plan at `docs/build-stream/plans/istara-pi-model-management-20260822-master-a.md` (610 lines, 17 sections). Reconciled overlaps/conflicts: the three drafts' retirement state vocabularies merged into two orthogonal axes (row/endpoint migration state + deployment stage S0–S5) plus the `PI_MODEL_MANAGEMENT_MODE` registry (§6); risk registers merged into R1–R13 (§14); rollback playbooks merged into one sequence (§7.4); per-wave verification command sets consolidated and re-verified against the tree (§8). Closed gaps: C8 (fresh disposable DBs + CF impact/why/test-impact packs before implementation), explicit transition rule with rollback-drill + owner gates (§6), VPS single-service reality check C5 (§9.3), vpsctl skill path C7 (§9), encryption context/version compatibility with standalone Pi. Coverage matrix §15 maps every section to its draft inputs.
Result: Complete slot-A master-plan candidate covering the full task scope: legacy LLM Server storage/routing/encryption consumers, both agentic engines, Pi provider/model catalog + endpoint resolver, embeddings/vector-space invariant, Petals donor bridge, audio/transcription flows, UI contracts, testing-branch Docker QA, VPS deployment per the vps skill, reversible staged LLM Server retirement, exact data/secret migration + rollback, latest verified Pi dependency (0.84.2, re-verify at execution), no duplicate model identity semantics, feature-flag/deprecation/removal criteria, per-wave acceptance + commands, docs/manifest obligations, security benchmark coverage, isolated VPS deployment/cleanup. F-1 (multivac→VPS) bound into the plan (C1). No vote (sole synthesis round). ISTARA-PI-MODEL-MIGRATION-20260822-MASTER-A.
Verified: `npm view` → 0.84.2 / 0.84.2 (passed; tree pins 0.83.0/0.80.10); `python3 scripts/pi_migration_inventory.py --json` → 1 allowlisted permanent site, ratchet 0 (passed); `compass-forge gate before --task …-MASTER-A --summary` → fail, 30 inherited, 0 new, 0 actionable (passed as baseline); `uv run --project backend python -m pytest tests/pi_migration/test_count_to_zero.py -q` → 3 passed; `python3 scripts/security_benchmark.py --fail-on-threshold` → 28/28, 100.0%, pass; `python3 scripts/feature_docs.py --seed-missing --generate-site --check` → 86 features, 224 artifacts, 0 seeded; `pytest --collect-only` six key surfaces → 62 tests collected; `python3 ~/.pi/agent/skills/vps/scripts/vpsctl.py --help` → 7 subcommands; 40/40 V13 anchors present, 3/3 V14 obligations absent (passed); `git diff --check` clean. CF evidence rows (command ×3 + self_report) on …-MASTER-A.
Next: Vote round compares master-plan candidates; conductor freezes the consensus plan and stops at the owner approval gate before any implementation task is generated or released.

### L-9 | 2026-08-22T12:20:03Z | S1-plan | deepseek/deepseek-v4-pro | architect | synthesize <!-- bsc-ledger:ISTARA-PI-MODEL-MIGRATION-20260822-MASTER-B -->
Did: Wrote the slot-B MECE master-plan synthesis candidate to `docs/build-stream/plans/istara-pi-model-migration-20260822-master-b.md` (544 lines). Re-read all three immutable consensus snapshots (SHA-verified against consensus.json: A 830a54b9, B ffa5899f, C fd6fa270) and reconciled them into ONE master plan (not a concatenation): unified retirement model (§6: global mode registry + per-row state machine + S0-S5 phases), 13-item conflict/correction table C1-C13 (multivac->VPS, six-wave re-baselining, 30-inherited gate baseline, `pi_api_endpoints` naming, single-service VPS reality check, environment prerequisites, vpsctl skill path, test-anchor corrections, `uv run --project backend` command canonicalization, state-machine unification, Wave-1 dependency update, frontend path fix, lockstep lab pin), merged per-wave acceptance + exact verification commands for all six manifest waves, unified risk register R1-R14, Definition of Ready/Done + owner gates, and two coverage matrices (§0 draft->section; §15 requirement->section).
Result: Complete MECE master-plan candidate B exists at the authoritative plan_file for synthesis round `0bb85df72bbe6604f51a`; the parallel slot-C candidate (master-c.md) exists in the worktree. Ready for the vote phase. ISTARA-PI-MODEL-MIGRATION-20260822-MASTER-B.
Verified: `npm view` -> 0.84.2 / 0.84.2 (tree pins 0.83.0 / 0.80.10); `uv run --project backend python -m pytest tests/pi_migration/test_count_to_zero.py -q` -> 3 passed; `python3 scripts/pi_migration_inventory.py --json` -> 1 allowlisted permanent site, ratchet 0; pinned-CF `gate before --summary` -> fail, 30 inherited / 0 new / 0 actionable, drift route=4 type=2, warnings=188; `vpsctl.py --help` -> 7 subcommands at the vps skill path; snapshot SHA triple-check -> matches consensus.json; manifest binding hash b9c8ff0c re-derived from canonical JSON; `git diff --check` clean. CF evidence rows 104-111 on ISTARA-PI-MODEL-MIGRATION-20260822-MASTER-B.
Next: Consensus vote phase compares the two master candidates (master-b, master-c) and votes; the conductor freezes the winning plan and stops at the owner approval gate before any implementation task is released. No vote cast in this synthesize phase.

### L-10 | 2026-08-22T12:24:25Z | S1-plan | deepseek/deepseek-v4-flash | synthesizer | synthesize <!-- bsc-ledger:ISTARA-PI-MODEL-MIGRATION-20260822-REMASTER-A-r1 -->
Did: Repaired the slot-A MECE master-plan synthesis. The L-8 synthesis had landed at the misnamed path `docs/build-stream/plans/istara-pi-model-management-20260822-master-a.md`, which the vote phase cannot consume under this task's `plan_file`; wrote the full MECE master plan to the authoritative `plan_file` `docs/build-stream/plans/istara-pi-model-management-migration-20260822-master-a.md` and removed the misnamed duplicate in the same commit (mirroring the REPLAN-A/B-r1 draft repairs). Re-verified every current-tree fact at repair time (2026-08-22).
Result: Authoritative slot-A MECE master-plan candidate exists at the path the vote phase reads; covers the full task scope: legacy LLM Server storage/routing/encryption consumers, both agentic engines, Pi provider/model catalog + endpoint resolver, embeddings/vector-space invariant, Petals donor bridge, audio/transcription flows, UI contracts, testing-branch Docker QA, VPS deployment per the vps skill, reversible staged LLM Server retirement (three orthogonal axes + mode registry), exact data/secret migration + rollback, latest verified Pi dependency (0.84.2, re-verify at execution), no duplicate model identity semantics, feature-flag/deprecation/removal criteria, per-wave acceptance + commands, docs/manifest obligations, security benchmark coverage, isolated VPS deployment/cleanup. ISTARA-PI-MODEL-MIGRATION-20260822-REMASTER-A-r1.
Verified: `npm view` → 0.84.2 / 0.84.2 (passed); `python3 scripts/pi_migration_inventory.py --json` → 1 allowlisted permanent site, ratchet 0 (passed); `compass-forge gate before --task …-REMASTER-A-r1 --summary` → fail, 30 inherited, 0 new, 0 actionable, drift route=4/type=2, warnings=188 (passed as baseline); `pytest --collect-only` six key surfaces → 62 tests collected (passed); `python3 scripts/security_benchmark.py --fail-on-threshold` → pass (passed); `python3 scripts/feature_docs.py --seed-missing --generate-site --check` → 86 features, 224 artifacts, 0 seeded (passed); `python3 ~/.pi/agent/skills/vps/scripts/vpsctl.py --help` → 7 subcommands (passed); `git diff --check` clean. CF evidence rows (command ×4 + self_report) on …-REMASTER-A-r1.
Next: Vote round compares the master-plan candidates (a repaired, b, c); conductor freezes the consensus plan and stops at the owner approval gate before any implementation task is generated or released.

### L-11 | 2026-08-22T12:37:59Z | S1-plan | deepseek/deepseek-v4-pro | voter | vote <!-- bsc-ledger:ISTARA-PI-MODEL-MIGRATION-20260822-VOTE-B -->
Did: Read both master-plan candidates supplied for vote round ef3baec72460f4802e2b — slot a (`docs/build-stream/plans/istara-pi-model-migration-20260822-master-a.md`, candidate ec3a76e7…, 624 lines) and slot c (`docs/build-stream/plans/istara-pi-model-migration-20260822-master-c.md`, candidate a1619826…, 716 lines) — and verified each plan_file is byte-identical to its frozen consensus snapshot. No plan files edited; no code touched.
Result: Voted slot a (candidate ec3a76e75d82e2d4495aec7d0c251f128fda99643de77b1180f56c00f9bc34ed). Rationale: A models retirement as three orthogonal axes (per-row migration state incl. canary_verified + rollback_ready→legacy_compat × S0–S5 deployment stage × PI_MODEL_MANAGEMENT_MODE registry) vs C's single linear S0–S5; A adds C8 (fresh disposable DBs + mandatory CF impact/why/test-impact packs), 17 verified facts (V1–V17) vs 16, risk register R1–R13 vs R1–R11, surface-by-surface test-ownership matrix, 8-item removal criteria, and a security-benchmark/review checklist — while retaining everything C covers (per-wave verification commands, VPS strict-profile acceptance, coverage matrix, owner gates). ISTARA-PI-MODEL-MIGRATION-20260822-VOTE-B.
Verified: `shasum -a 256` snapshots + plan files → a=10096535…, c=85eae608… (both match consensus.json); `diff -q` plan vs snapshot → identical for both (A MATCH, C MATCH); `wc -l` 624/716. CF evidence rows: command (id 138) + plan_vote (id 139) + self_report (id 140) on ISTARA-PI-MODEL-MIGRATION-20260822-VOTE-B.
Next: Remaining vote slot(s) record plan_vote; conductor tallies the round, freezes the winning consensus plan, and stops at the owner approval gate before any implementation task is generated or released.

### L-12 | 2026-08-22T12:41:02Z | S1-plan | gpt-5.6-luna | planner | istara-pi-model-migration-20260822-architect-c <!-- bsc-ledger:ISTARA-PI-MODEL-MIGRATION-20260822-VOTE-C -->
Did: istara-pi-model-migration-20260822-architect-c stage on task ISTARA-PI-MODEL-MIGRATION-20260822-VOTE-C (harness fallback entry; the model did not append one).
Result: task ISTARA-PI-MODEL-MIGRATION-20260822-VOTE-C finished; worktree head cd8aa76f.
Verified: see Compass Forge evidence rows on ISTARA-PI-MODEL-MIGRATION-20260822-VOTE-C (command + self_report + stage_attribution).
Next: conductor advances the pipeline on evidence.

### L-13 | 2026-08-22T12:42:10Z | S1-plan | deepseek/deepseek-v4-flash | voter | vote <!-- bsc-ledger:ISTARA-PI-MODEL-MIGRATION-20260822-VOTE-A -->
Did: Read both master-plan candidates supplied for vote round ef3baec72460f4802e2b — slot b (master-b.md, candidate 65a2de29…) and slot c (master-c.md, candidate a1619826…) via their immutable consensus snapshots (the work-order plan_file paths for b/c did not exist in the worktree; snapshots are the authoritative inputs). Spot-checked shared load-bearing facts at vote time: config.py:304 `pi_api_endpoints: list[PiApiEndpoint]`, config.py:315 `agentic_engine_default="legacy"`, pi-runtime pins 0.83.0 vs labs/pi-replacement 0.80.10, `tests/test_llm_servers.py` present (not `tests/llm_servers.py`) — all accurate in both candidates. No plan files edited; no code touched.
Result: Voted slot b (candidate 65a2de29913abc7cbda40c9edb336a3634b50cd832c3955877674f374761a587). Rationale: B is the more complete MECE synthesis — explicit C10 unified three-layer retirement model (initiative S0–S5 × per-row state machine × PI_MODEL_MANAGEMENT_MODE registry), 13-item conflict table (C1–C13) vs C's 7, broadest per-wave verification command sets (compute_cases, pi_benchmark, w4_a2a_handlers, research-spine anchors), security reviewer checklist. C is nearly as strong (finer V1–V16 fact table, explicit doc paths, CF task-shape table). Round ef3baec72460f4802e2b tally: a=2 (VOTE-B, VOTE-C), b=1 (VOTE-A). ISTARA-PI-MODEL-MIGRATION-20260822-VOTE-A.
Verified: read .compass-forge/conductor/consensus-snapshots/65a2de29… + a1619826… (both full plans, passed); `grep -n "agentic_engine_default|pi_api_endpoints" backend/app/config.py` -> lines 304/315 (passed); `grep @earendil-works/pi-agent-core|pi-ai pi-runtime/package.json labs/pi-replacement/package.json` -> 0.83.0 / 0.80.10 (passed); `ls tests/test_llm_servers.py tests/llm_servers.py` -> only tests/test_llm_servers.py exists (passed). CF evidence rows on ISTARA-PI-MODEL-MIGRATION-20260822-VOTE-A: command (id 146) + plan_vote (id 155) + self_report (id 156).
Next: Conductor tallies round ef3baec72460f4802e2b (a=2, b=1), freezes the winning consensus plan, and stops at the owner approval gate before any implementation task is generated or released.
