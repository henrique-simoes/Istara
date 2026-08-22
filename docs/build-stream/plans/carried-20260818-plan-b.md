# Plan B — Draft: Foundation for upstream Pi contract and migration boundary

**Task:** `ISTARA-PI-MODEL-MIGRATION-20260818-REPLAN-B-r1`
**Role:** `istara-pi-model-migration-20260818-architect-b`
**Plan type:** independent architect draft (S1)
**Owner constraints:** no implementation. Preserve both explicit engines, reversible migration, no silent behavior change.

## 1) Executive summary

This draft defines how Istara retires legacy `LLMServer` model-management primacy while keeping Istara safe, reversible, and inspectable.

The migration target is:
- Pi-owned model/provider/endpoint catalog and secret bindings become canonical.
- Legacy `LLMServer` becomes a compatibility layer and audit trail, then transitions to deprecation, then retirement by explicit gates.
- Both engines (`pi` and `legacy`) remain explicit and selectable; no silent fallback in either direction.
- Embedding/vector-space behavior stays stable across the migration.
- Petals donor flows remain isolated from Pi model capacity selection.
- Audio/transcription, UI selectors, feature docs, Docker-Compose QA, and multivac operational steps are included in one migration spine.

The full migration is **staged, reversible, owner-gated, and evidence-first**.

## 2) Scope and non-goals

### In scope
- CF task graph `CF-787` through `CF-805` under `CF-SPEC-59`.
- Upstream Pi dependency/runtime verification and contract guard.
- Legacy LLMServer storage/routing/encryption consumers, both agentic engines, embeddings/vector-space invariant, Petals bridge, audio/transcription, UI contracts, test ownership, docs/manifests, and multivac hygiene.
- Data and secret migration with deterministic rollback.
- Security benchmark integration.

### Non-goals
- No implementation this stage.
- No merge/push/PR/opening PR.
- No live model loading or live model-completion probes.
- No direct touching of unbounded control-plane repos.
- No mutation of `LLMs/` or `Model_Finetuning/`.

## 3) Bounded references (read-only)

Use as architecture/process comparators only:
- Compass Forge Rust branch `08d3233`.
- Skills branch `e45211e` (conductor-dspy-gepa).
- Skills branch `3d4277b` (wave3-l35-remediation).

No branch is to be cut into `main` or used for Istara source implementation.

## 4) Invariants that never regress

1. **Single model authority contract**
   - `PiModelManager` + Pi endpoint resolution is canonical for provider/model/endpoint identity.
   - Legacy `LLMServer` never remains a second source of truth after canonicalization is complete.

2. **No duplicate identity semantics**
   - One canonical model identity tuple per logical model.
   - Legacy aliases are explicit compatibility mappings only.

3. **Explicit dual-engine behavior persists**
   - `agentic_engine_default` and selector precedence remain explicit.
   - `pi` cannot silently fallback to `legacy` and vice versa.

4. **Fail-closed behavior**
   - Missing/invalid model config, secret, endpoint, or vector profile is a typed failure.

5. **Vector-space invariance**
   - Embedding model and dimension compatibility checks prevent silent drift on routing or engine change.

6. **Donor isolation preserved**
   - Donated Petals compute remains separately governed and never treated as ordinary Pi model capacity.

7. **Research Spine compliance**
   - No reportable research artifacts are produced before evidence-unit coding, reliability, reconciliation, and human review gates.

8. **Reversibility**
   - Every migration wave includes deterministic rollback to a previous operational state.

9. **Security and secret hygiene**
   - No plain secret material in exports, logs, telemetry, docs, QA artifacts, or feature docs.

## 5) Migration topology and state machine

### State sequence

- **S0 – Legacy authoritative**
  - Legacy runtime and `LLMServer` operations dominate.
  - Pi catalog exists, but compatibility-only.

- **S1 – Pi authoritative catalog & secrets, legacy default execution**
  - Pi owns model/provider/endpoint schema.
  - Legacy remains execution default while compatibility continues.

- **S2 – Dual-engine execution with explicit selection**
  - Both engines selectable by header/project/settings.
  - Fail-closed per-engine semantics retained.

- **S3 – Pi preferred + legacy compatibility-only**
  - Pi default, explicit legacy compatibility surfaces remain.

- **S4 – Deprecation window**
  - Legacy compatibility calls become deprecated with warning/expiry metadata.
  - Removal criteria must be met before phase transition.

- **S5 – Retirement complete**
  - Compatibility reads/writes removed after explicit criteria and rollback proven.

### State transition checks

- Gate evidence has zero **new** architecture failures and security gate baselines are recorded.
- Wave-level acceptance checks are green.
- Owner approval captured before moving past S2.
- Rollback drill executed before advancing from any irreversible transition.

## 6) Canonical model-management contract (conceptual)

Implement only through migration/implementation phases, not in this planning stage.

- `model_id` = canonical provider-qualified identity.
- `endpoint_id` = distinct route identity.
- `capability_profile` = explicit capabilities per endpoint.
- `secret_ref` = redacted credential handle, not plaintext.
- `migration_state` = active | compatibility_only | deprecated | sunset.
- `source_lineage` = legacy row mapping and checksum metadata.

Compatibility writes remain routed through canonical interfaces until legacy retirement. Legacy alias rows are never treated as independent model authority.

## 7) Per-wave implementation plan

### Wave 0 — Baseline freeze + dependency reality

**Goals**
- Confirm repository baseline and spec/task ownership.
- Record current inherited gate debt and inherited risks.
- Refresh upstream Pi runtime versions and compatibility evidence.

**Design outputs before Wave 1 implementation**
- Migration manifest with wave boundaries and rollback artifacts list.
- Verified upstream version record.

**Exact commands (verification)**
```bash
cd "/Users/user/Documents/Istara-worktrees/istara-pi-model-management-migration-20260818"
compass-forge --workspace "/Users/user/Documents/compass-forge" status
compass-forge --workspace "/Users/user/Documents/compass-forge" next
compass-forge --workspace "/Users/user/Documents/compass-forge" refresh
compass-forge --workspace "/Users/user/Documents/compass-forge" index refresh
compass-forge --workspace "/Users/user/Documents/compass-forge" gate before --summary
compass-forge --workspace "/Users/user/Documents/compass-forge" gate after --summary
npm view @earendil-works/pi-agent-core version
npm view @earendil-works/pi-ai version
python scripts/security_benchmark.py --fail-on-threshold
python scripts/feature_docs.py --seed-missing --generate-site --check
```

**Acceptance**
- Inherited failures only; `new_failures` stays 0.
- Upstream Pi versions and compatibility posture captured in plan evidence.
- No source behavior changed.

### Wave 1 — Upstream Pi contract + baseline dependency alignment

**CF alignment:** `CF-787`

**Goals**
- Lock and pin verified Pi versions for `pi-runtime`/related runtime dependencies.
- Establish protocol/version baseline.

**Design outputs**
- Dependency/version acceptance record with compatibility rationale.
- Any required lockfile migrations are prepared for bounded execution.

**Verification commands (wave 1 acceptance)**
```bash
npm view @earendil-works/pi-agent-core version
npm view @earendil-works/pi-ai version
cd pi-runtime && npm ci && cd ..
npm run --prefix pi-runtime test
python scripts/security_benchmark.py --fail-on-threshold
```

**Acceptance**
- New versions selected are recorded with exact provenance.
- No protocol or security invariant regressions before migration.

### Wave 2 — Canonical Pi catalog, endpoint/secret migration, and compatibility map

**CF alignment:** `CF-788`, `CF-801`

**Goals**
- Make Pi ownership explicit for catalog, model IDs, endpoint settings, and credential handles.
- Preserve legacy rows with compatibility map and source lineage.

**Design outputs**
- Secret and catalog migration scripts with provenance manifests.
- Legacy row compatibility map schema: `legacy_source_id`, checksum, migration timestamp, rollback command.

**Exact commands (wave 2 acceptance)**
```bash
python -m pytest tests/pi_migration/test_count_to_zero.py -q
python -m pytest tests/pi_migration/__init__.py -q
python -m pytest tests/test_llm_servers.py tests/test_settings_agentic_pi_endpoints.py -q
python scripts/security_benchmark.py --fail-on-threshold
python scripts/feature_docs.py --seed-missing --generate-site --check
```

**Acceptance**
- `scripts/pi_migration_inventory.py` (or equivalent equivalent manifest) confirms bounded legacy surface.
- Secret migration preserves encrypted/plaintext separation; no plaintext export.
- `CF-788/CF-801` readiness evidence exists.

### Wave 3 — Dual-engine migration and routing unification

**CF alignment:** `CF-789`, `CF-794`

**Goals**
- Preserve both engine selection paths as explicit configuration.
- Move provider/model resolution into canonical Pi surface for both engines where applicable.
- Prevent any fallback from selected engine to other engine.

**Design outputs**
- Engine resolution matrix: call/header/project/global precedence.
- Explicit `llmserver_compat_mode` behavior and deprecation semantics during transition.

**Acceptance commands**
```bash
python -m pytest tests/pi_production/test_engine_http_provider.py tests/pi_production/test_runtime_hardening.py
python -m pytest tests/pi_production/test_seams_fail_closed.py
python -m pytest tests/pi_production/test_w1_agentic_contract.py tests/pi_production/test_w1_dispatcher_authority.py -q
python -m pytest tests/pi_production/test_w1_usage_ledger.py
python -m pytest tests/pi_migration/test_count_to_zero.py -q
```

**Acceptance**
- Explicit engine precedence remains preserved.
- Unknown engine mode fails closed; no silent fallback.
- Rollback command path demonstrated to legacy default.

### Wave 4 — Embeddings/vector-space invariants and Petals safety

**CF alignment:** `CF-791`, `CF-792`

**Goals**
- Preserve vector-space invariants across both engine paths.
- Keep Petals donor bridge as isolated, consent-bound, project-scoped capability.

**Design outputs**
- Invariant checks for endpoint/model profile and vector dimension.
- Donor bridge admission and route evidence tests with no paid fallback behavior on donor unavailability.

**Acceptance commands**
```bash
python -m pytest tests/compute_cases/config.py tests/compute_cases/routing.py
python -m pytest tests/compute_cases/retries.py
python -m pytest tests/pi_production/test_same_model_donor_isolation.py tests/pi_production/test_research_spine_donor_routing.py
python -m pytest tests/pi_benchmark/test_runner.py
python -m pytest tests/pi_benchmark/budget_ledger.py
```

**Acceptance**
- No route changes that alter embedding dimension/profile without explicit migration.
- Donor node identity pinning and project consent behavior remains unchanged or stronger.

### Wave 5 — Audio/transcription and transport contracts

**CF alignment:** `CF-793`, `CF-790`

**Goals**
- Make audio/Whisper model-provider settings explicit and canonical under model-management governance.
- Keep local-only behavior for flows that do not request model-backed transcription providers.

**Design outputs**
- Audio/transcription profile schema, capability flags, and secrets binding contract.
- Capability-aware transcript pipeline with explicit unsupported-result handling.

**Acceptance commands**
```bash
python -m pytest tests/pi_benchmark/test_live_driver.py tests/pi_benchmark/test_runner.py
python -m pytest tests/pi_benchmark/live_driver.py
python -m pytest tests/pi_production/test_scenarios_structured_output.py
python -m pytest tests/pi_production/test_runtime_hardening.py
python -m pytest tests/pi_production/test_w1_agentic_contract.py
```

**Acceptance**
- Audio path uses declared profile and capability policy.
- Non-supported modes return typed failure (no silent route escalation).

### Wave 6 — Public testing-branch QA, docs/manifests, multivac isolation

**CF alignment:** `CF-795`, `CF-796`, `CF-804`, `CF-805`

**Goals**
- Finalize docs, feature manifests, and disposal-safe QA operations.
- Record complete testing evidence and closure criteria.

**Design outputs**
- `docs/features` updates for model controls, endpoints, embeddings, compute/bridge, audio/transcription.
- QA and compose contract checks from testing branch.
- Multivac runbook commands with read-only inventory and unique namespace cleanup.

**Acceptance commands**
```bash
python scripts/feature_docs.py --seed-missing --generate-site --check
python -m pytest tests/test_feature_docs.py tests/test_qa_stack_contract.py tests/test_qa_reset_seed.py
python -m pytest tests/pi_benchmark/test_b1_contract.py tests/compute_cases/routing.py
python -m pytest tests/pi_benchmark/test_live_driver.py
python -m pytest tests/test_synthetic_provisional_boundary.py tests/test_feature_obligations.py
python scripts/security_benchmark.py --fail-on-threshold
```

**Acceptance**
- Feature docs/manifests synced.
- Testing branch acceptance profile is documented.
- Multivac cleanup and namespace hygiene verified.

## 8) Data/secret migration and rollback playbook

### Data migration sequence
1. Snapshot `llm_servers`, related settings, catalog rows, and routing/usage evidence.
2. Create deterministic migration map from legacy rows to canonical model identifiers.
3. Migrate in cohorts and mark cohort state (`migrated`, `deferred`, `blocked`).
4. Keep compatibility reads and writes active with alias maps until S4.
5. Verify rollback path at each transition.

### Secret migration sequence
1. Resolve legacy encrypted secret provenance with encrypted-by-lineage checks.
2. Translate into Pi secret references via approved custody plane.
3. Validate redacted-only presence checks in every endpoint path.
4. Maintain rollback recipe restoring legacy secret accessor compatibility.

### Rollback
- Restore legacy defaults (`agentic_engine_default=legacy`, compatibility mode re-enabled), rehydrate compatibility write path, and replay verification commands for S2 baseline.
- Reimport migration snapshot if data migration already ran.
- Re-run fail-closed and secret-hygiene checks.

## 9) Feature docs, testing and manifest obligations

During implementation, implementation must update and verify:
- `docs/features/content/**/*.md` pages for model endpoints, agentic engines, embeddings, donor bridge, audio/transcription, and QA.
- `testing/feature_coverage.yml` / equivalent coverage mapping for newly touched behaviors.
- `python scripts/feature_docs.py --seed-missing --generate-site --check` after every wave that changes behavior.
- `security/control_matrix.json`, `security/SECURITY_BENCHMARK.md`, `tests/test_security_benchmark.py` only if controls/standards/triggers change.

## 10) Security benchmark and controls

Mandatory execution for any security/auth/provider/secret/agentic/Petals behavior:

```bash
python scripts/security_benchmark.py --fail-on-threshold
```

Do not suppress inherited gate failures silently; record baseline vs post-change comparison and explicitly justify residual risk.

## 11) Multivac hygiene (isolated and owner-authorized)

- Read-only inventory first.
- Unique Compose project names and isolated stack paths.
- SSH-tunnel or loopback-safe access; no firewall churn.
- No mutation of unrelated workloads.
- Teardown only initiative-owned disposable artifacts and compose resources.

Cleanup command examples (owner-authorized scope only):
```bash
scripts/multivac_inventory.sh --scope readonly
scripts/multivac_qa.sh --up --project istara-pi-migration-$(date +%Y%m%d-%H%M%S)
scripts/multivac_qa.sh --down --project <same>
```
(Exact orchestration scripts are implementation-owned and must be project-confirmed.)

## 12) Risks and mitigations

- **Duplicate identity collisions:** canonical uniqueness checks + collision failure.
- **Secret leak/regression:** one-way redaction guarantees + runtime secret-handle checks.
- **Silent fallback behavior drift:** typed-engine errors and integration tests per mode.
- **Embedding drift:** invariant assertion before cache writes and route acceptance.
- **Donor boundary erosion:** explicit isolation rules and consent tests.
- **Cleanup drift on multivac:** namespace isolation and inventory diff closure.
- **Inherited baseline debt:** all gate outputs must separate inherited vs new failures.

## 13) Handoff criteria

Plan is complete when:
- this draft covers all CF tasks with reversible waves, concrete acceptance commands, and rollback criteria;
- owner approval is required before implementation start;
- next architect/reviewer tasks receive this artifact for synthesis and final vote.

## 14) Direct task-to-wave mapping

| CF task | Wave | Focus |
|---|---|---|
| CF-787 | Wave 1 | Dependency/version update |
| CF-788 | Wave 2 | Canonical ownership |
| CF-789 | Wave 3 | Dual-engine explicit control |
| CF-790 | Wave 5 | Compatibility/deprecation/removal |
| CF-791 | Wave 4 | Embedding/vector invariance |
| CF-792 | Wave 4 | Petals donor bridge isolation |
| CF-793 | Wave 5 | Audio/transcription model config |
| CF-794 | Wave 3 | Engine selector UX migration |
| CF-795 | Wave 6 | Feature docs/fixtures/manifests |
| CF-796 | Wave 6 | Multivac QA isolation |
| CF-797 | Wave 0 | Validate system scope and behavior |
| CF-798 | Wave 0 | Review contract/tables/gates |
| CF-799 | Wave 1+ | FR-001 implementation obligations |
| CF-800 | Wave 6 | FR-002 compatibility preservation |
| CF-801 | Wave 2 | FR-003 verification evidence |
| CF-802 | Wave 0 | FR-004 impact and contracts |
| CF-803 | Wave 0 | FR-005 must-inspect evidence |
| CF-804 | Wave 6 | Final evidence acceptance |
| CF-805 | Wave 6 | Final acceptance and no open tasks |

## 15) Final note (implementation guard)

This is a planning artifact only. No source implementation, service start, multivac mutation, or live model request is authorized from this stage. Owner approval is required before moving to implementation waves.
