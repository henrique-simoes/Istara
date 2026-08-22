# Independent architecture plan — Istara Pi model-management migration

**Task:** `ISTARA-PI-MODEL-MIGRATION-20260822-PLAN-C`  
**Role:** `istara-pi-model-migration-20260822-architect-c`  
**Spec:** `CF-SPEC-1`  
**Phase:** `draft`; implementation is prohibited until consensus and owner approval.

## 1. Decision and boundary

Make Pi the canonical authority for provider/model identity, endpoint identity,
capabilities, credential references, and resolution. Keep `LLMServer`,
`ComputeRegistry`, local lifecycle, and Petals as explicit transport adapters until
measured retirement criteria pass. This is an authority migration, not deletion of
all legacy inference infrastructure.

```text
configuration -> canonical Pi catalog/credential custody -> selected transport
              -> Pi worker | legacy adapter | Petals bridge | audio adapter
              -> one safe route/usage/evidence record
```

All work stays on the testing branch. No live model load, completion probe,
backend/frontend server, secret disclosure, firewall change, merge, push, or
unapproved VPS mutation is in scope.

The three carried drafts are inputs: A supplies identity/resolver, research-spine,
and test-ownership contracts; B supplies state machine, task mapping, and QA
sequence; C supplies the current-tree boundary, ratchet, and owner-gate model.
Historical multivac references are replaced by the requested managed VPS/Dokploy
single-workload profile.

## 2. Boundary to inventory before implementation

Foundation must produce a non-secret machine-readable inventory and CF impact map:

| Area | Current anchors | Required result |
|---|---|---|
| Legacy storage/API | `backend/app/models/llm_server.py`, `backend/app/api/routes/llm_servers.py`, migrations, settings/admin routes | Every reader, writer, probe, and UI consumer identified; rows preserved as migration source. |
| Legacy transport | `backend/app/core/llm_router.py`, `compute_registry*.py`, `ollama.py`, `network_discovery.py` | Adapter boundary retained; Pi endpoints never enter donor scheduling. |
| Pi authority | `backend/app/core/pi_runtime/{model_manager,endpoints,engine}.py`, `backend/app/config.py` | Durable canonical catalog/resolver and redacted credential references. |
| Pi dependency | `pi-runtime/{package.json,package-lock.json,PROTOCOL.md}`, `labs/pi-replacement/*` | Latest registry version rechecked immediately before pinning; protocol v2 compatibility proven. |
| Engines | `backend/app/core/agentic/{dispatcher,legacy}.py`, project/settings engine contracts | Preserve call/header/project/global precedence and fail closed; no cross-engine fallback. |
| Embeddings | `pi_runtime/embeddings_gateway.py`, `core/embeddings.py`, validation/cache | Explicit stable profile; model/dimension/normalization mismatch blocks writes. |
| Petals | `core/petals_bridge.py`, route, donor isolation tests | Consent, health, project scope, exact node pin, route evidence, typed 503, no paid fallback. |
| Audio/research | `core/transcription.py`, `file_processor.py`, `/chat/voice`, files/interviews | Explicit Whisper/diarization capability; raw spans and review state remain in Research Spine. |
| UI/docs/QA/ops | settings/project UI, model catalog, `docker-compose.qa.yml`, `qa/`, feature docs, `vpsctl.py` | No duplicate options; generated docs/manifests and isolated QA/deployment evidence. |

Before touching implementation, run CF `intelligence impact`, `why`, `test-impact`,
and a standard context pack for each planned entry point. Carried-draft facts are
hypotheses until confirmed in this checkout.

## 3. Contracts and invariants

Use additive repository-native schema/service names with these semantics:

```text
CanonicalModel: model_id, provider_family, canonical_name, provenance aliases
CanonicalEndpoint: endpoint_id, model_id, transport, kind, capabilities,
                   credential_ref, legacy_source_id, migration_state
CredentialRef: opaque custody reference, kind, presence/health status
EmbeddingProfile: profile_id, model/endpoint identity, dimension, dtype,
                  normalization, version, status
```

`model_id` is provider-qualified; `endpoint_id` is always distinct. Two endpoints
serving one model retain separate route identities. `pi-llm-<id>` and
`legacy_source_id` are provenance aliases only. Names, hosts, and display labels do
not establish identity. Unknown required capabilities fail closed.

One resolution request carries project, selected engine, optional model/endpoint,
purpose, capabilities, and embedding profile. It returns safe identity, transport,
capabilities, credential reference, and route-evidence fields—never plaintext.
`PiModelManager` owns catalog/resolution; adapters do not create competing catalogs.

- Selection remains explicit: call > header > project > global. A selected Pi or
  legacy failure is typed and never implicitly falls back; every dispatch,
  including resolution failure, produces exactly one safe ledger row.
- Decrypt legacy credentials only inside a bounded migration service, immediately
  re-encrypt/externalize, and store no plaintext, raw token, URL, or reusable secret
  fingerprint in manifests, logs, telemetry, docs, or QA artifacts.
- Chat endpoint changes cannot alter the embedding profile. Vector mismatch blocks
  startup/use and cache writes.
- Petals remains consented, project-authorized, health-checked, node-pinned, and
  outside ordinary Pi capacity scoring. Unavailable/disabled is typed 503.
- Research data follows `Sources -> Evidence Units -> independent coding ->
  reliability/grounding -> reconciliation -> human-approved Done -> reports`.
  Transcripts and model outputs remain provisional until those gates pass.

## 4. Reversible retirement

Persist idempotent source-to-canonical records with actor, source snapshot,
canonical IDs, validation result, timestamp, and rollback state:

`discovered -> mapped -> credential_validated -> shadowed -> canary -> pi_primary -> deprecated -> retired`

Conflicts, duplicate identity, secret mismatch, unsupported capability, vector
mismatch, or missing route evidence block promotion. Controls support global/project
scope, read-only legacy visibility, no-new-legacy-writes, migration status, and an
emergency rollback switch.

Rollback explicitly disables Pi-primary, restores prior engine/route mode and source
snapshot, invalidates temporary credentials, and reruns legacy contract tests. It is
not exception-driven cross-engine fallback. Never delete source rows or credentials
until owner approval, restorable snapshot, zero unmapped rows, zero active legacy
writes, successful canary/shadow evidence, stable embedding profile, security pass,
docs parity, and testing-branch QA all exist.

## 5. Waves, tasks, and acceptance

| Wave | CF tasks | Deliverable and gate |
|---|---|---|
| W0 foundation | `CF-787`, `CF-797`, `CF-798`, `CF-802`, `CF-803` | Boundary inventory, dependency provenance, baseline gate, migration manifest, owner approval; no behavior change. |
| W1 catalog/secrets | `CF-788`, `CF-799` | Canonical models/endpoints/credentials/profiles, collision guards, redacted admin contract, fresh-DB tests. |
| W2 routing/migration | `CF-789`, `CF-801` | Idempotent LLM Server mapping, encrypted secret migration, dual-engine resolver, shadow/canary, snapshot/restore drill. |
| W3 embeddings/UI | `CF-791`, `CF-794` | Vector invariant, stable embedding profile, selector/API contract, no duplicate model options, accessibility tests. |
| W4 Petals/audio | `CF-792`, `CF-793` | Donor isolation unchanged; capability-specific Whisper/diarization and transcript provenance/review contracts. |
| W5 retirement/QA/docs | `CF-790`, `CF-795`, `CF-796`, `CF-800`, `CF-804`, `CF-805` | Deprecation/removal evidence, feature docs/manifests, deterministic QA, isolated Dokploy acceptance and cleanup. |

Every wave requires targeted tests, `gate before/after` with new-vs-inherited
results, security evidence when triggered, feature-doc generation/check when a
contract changes, and owner approval before promotion. The final wave proves the
count-to-zero ratchet remains zero product call sites with permanent infrastructure
exceptions documented.

## 6. Verification contract

Use fresh disposable databases; never infer validity from contaminated persistent
SQLite. Exact baseline commands, supplemented by CF `test-impact` selections:

```bash
npm view @earendil-works/pi-agent-core version
npm view @earendil-works/pi-ai version
npm ci --prefix pi-runtime
npm test --prefix pi-runtime
python scripts/pi_migration_inventory.py
python -m pytest tests/pi_migration tests/pi_benchmark tests/compute_cases -q
python -m pytest tests/pi_production tests/petals_bridge tests/test_transcription.py -q
python scripts/security_benchmark.py --fail-on-threshold
python scripts/feature_docs.py --seed-missing --generate-site --check
docker compose -f docker-compose.qa.yml config
python -m pytest tests/test_qa_stack_contract.py tests/test_provider_contracts.py -q
```

Also run targeted dispatcher/ledger, endpoint-secret, vector-space, UI catalog,
research-validity, and rollback tests identified by graph impact. Separate inherited
gate failures from migration regressions. No live model loading is part of these
commands.

Only after explicit owner authorization, run `vpsctl.py preflight`, `inventory`,
`verify-isolation`, `verify-exposure`, and `audit-anchor` against a unique testing
project/volume and one Dokploy workload. Verify `ps`, health, logs, listeners,
client access, and teardown; do not change firewall rules or touch old workloads.

## 7. Documentation, security, risks, and rollback

Update affected `docs/features/`, research-validity/self-improvement contracts,
migration runbook, deprecation/removal criteria, QA manifest, and generated site/
manifests with behavior. If controls/evidence/triggers change, update
`security/control_matrix.json`, `security/SECURITY_BENCHMARK.md`, and
`tests/test_security_benchmark.py`.

Risks: dependency/protocol drift, credential loss, identity split-brain, embedding
corruption, donor trust-boundary widening, audio capability confusion, UI/catalog
divergence, contaminated QA, and VPS collision. Mitigations: exact lockfiles and
protocol tests, encrypted snapshots, uniqueness constraints, hard vector checks,
donor isolation, explicit capabilities, contract UI tests, unique QA projects, and
vpsctl proofs. Any failed criterion keeps compatibility/deprecated mode; rollback
restores the prior snapshot and mode, and vectors are never implicitly reindexed.

## 8. Coverage matrix

| Requirement | Covered by |
|---|---|
| Pi dependency and legacy storage/routing/encryption | §§2, 3, 5 W0–W2, 6 |
| Both engines and identity semantics | §3, 4, 5 W2–W3 |
| Retirement, flags, rollback | §4, 5 W2/W5, §7 |
| Embeddings, Petals, audio | §3, 5 W3–W4 |
| UI, QA, VPS/Dokploy | §§2, 5 W3/W5, 6 |
| Research validity, docs, security | §§3, 6–7 |

**Ready for implementation:** only after architect consensus, CF evidence, and the
owner approval gate. Until then, do not implement code or deploy.
