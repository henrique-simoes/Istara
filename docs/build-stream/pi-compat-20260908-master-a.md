# Pi Capability Inheritance — MECE Master Plan A

**Pipeline:** `pi-compat-20260908`

**Synthesis round:** `ac4059cd0733653e4c65`

**Candidate slot:** `a`

**Stage:** S1 plan only — implementation is not authorized

**Required next gate:** owner approval of the winning master plan

## 1. Executive decision

Make the exact pinned `@earendil-works/pi-ai` registry the canonical authority for
model and provider semantics, but do not load the complete registry in every Pi
worker. A deterministic Node generator will call pi-ai's public
`providers/all` API and produce one provenance-bound catalog at
`backend/app/core/pi_runtime/data/pi_models_catalog.json`. The backend will use
that artifact for Settings, Chat, endpoint resolution, validation, and cost
defaults. At turn bind, the backend will select one exact record and send a
small, server-built capability envelope to the worker. The worker will validate
that envelope and give it to pi-ai when constructing the model.

This resolves the architects' main disagreement:

- pi-ai remains the compatibility authority; Istara no longer hand-codes
  Codex, DeepSeek, Qwen, or Zai model semantics.
- the full registry is imported once during generation, not once per worker;
  the measured draft-B cost of loading `providers/all` (about 67 ms and 60 MB
  in its environment) does not become a per-session tax;
- the worker still receives the exact pi-ai record selected by
  `(pi_provider, model)` rather than an endpoint-authored approximation;
- the Python backend does not acquire a Node package runtime dependency;
- one generated artifact serves catalog, UI, validation, binding, and drift
  checks, eliminating divergent mirrors.

Operator-owned deployment details remain separate: base URL, secret custody,
timeouts, retries, operational limits, and contract pricing are not silently
replaced by upstream catalog values. Istara's safety overlay is applied last.
Unknown/custom models retain their named legacy fallback path and must be proven
byte-identical before any default-detection policy is considered.

## 2. Reconciled evidence and corrections

The three immutable drafts agree on the disease and most of the delivery
shape. Before implementation, W0 must remeasure the figures below against the
clean implementation base and save machine-readable reports; the numbers are
planning evidence, not release evidence.

| Evidence | Synthesis conclusion |
| --- | --- |
| Installed 0.84.3 exposes 39 providers and roughly 1,312 models; the current static mirror has 40 providers and roughly 1,307 models. | The extra provider is a governed custom overlay, not evidence that the mirror is fresher. Builtin and custom records need explicit provenance. |
| Drafts measured 81 builtin records missing from the mirror and 36 stale records; draft B additionally measured large `thinkingLevels`, context, and price divergence. | The static file is architecture debt until it is generated, normalized, diffed, and checked against the pin. |
| pi-ai model records use `thinkingLevelMap`; the worker currently constructs models with `thinkingLevels`. | The hand-maintained field is not the upstream capability contract. Generate pi-ai's computed supported-level list for UI/validation and preserve the map itself for provider payload translation. |
| The starting frame describes Codex as `low -> minimal`, but direct 0.84.3 API inspection shows Luna/Sol/Terra maps contain `minimal: "low"`, and pi-ai indexes the map by logical level. Current handling can also clamp unsupported values; Zai behavior and tests encode a no-effort baseline. | Treat the starting direction as corrected, then remeasure it at 0.85.1. Tests must assert logical input, exact map lookup, and provider wire payload. Existing contrary tests must be explicitly reclassified, not silently rewritten. |
| `normalize_model_effort` and worker-side handling can accept/clamp a value outside the selected model's levels. | Validate against the resolved model capability at session update and again at turn bind. No silent downgrade. |
| The backend currently sends provider identity and reasoning support, but not the complete capability record; `supports_vision` is present in endpoint resolution but absent from the bind payload on the inspected baseline. | A typed bind envelope is the missing seam. It must include modality and semantic capability without including secrets or private endpoint fingerprints. |
| Static model costs can diverge materially; Zai zero rates make budgeted execution fail closed. | pi-ai prices are generated defaults, while persisted/operator rates remain runtime authority. Existing records require previewed, explicit reconciliation; no silent cost migration. |
| pi-ai 0.85.1 has a larger registry and other internal changes. | Build the drift/conformance machinery on 0.84.3 first, then update and classify the 0.85.1 diff. |
| `glm-5.3-flash` was claimed present in installed 0.84.3 by the starting lifecycle, but drafts B and C measured it absent. | Treat the lifecycle sentence as unverified/corrected. W0 records the exact before/after presence from the package APIs and lockfiles. |
| The root pi-ai export does not expose `getBuiltinModel`; the public `@earendil-works/pi-ai/providers/all` subpath does. | The generator must import only documented/public package exports and its import contract must be tested. |
| Settings, Chat, endpoint policy, worker construction, validation, cost/budget accounting, usage telemetry, and route evidence all consume or depend on this data. | The work is a system compatibility change, not a two-file provider patch. |

Compass Forge's current tree-sitter impact is high-confidence for
`backend/app/core/pi_runtime/endpoint_policy.py` and points directly to
`catalog.py` and `backend/app/api/routes/settings.py`. Its impact for the `.mjs`
worker seam could not resolve the seed, so W0 must preserve a complementary
`rg` import/call-site inventory. Absence from the graph is not an exclusion.

## 3. Scope and invariants

### 3.1 In scope

- pi-ai pin and lockfile discipline;
- deterministic builtin-registry generation and governed custom overlays;
- provider/model identity normalization and exact lookup;
- capability, thinking/effort, compat, input-modality, context/output-limit,
  and catalog-cost projection;
- endpoint resolution, ephemeral binding, worker model construction, wire
  payloads, validation, fallback, error, telemetry, and budget behavior;
- Settings and Chat catalog/effort behavior;
- backend, runtime, security, Research Spine, container-first browser, and
  bounded live conformance;
- update/regeneration/diff runbooks and required feature/architecture docs.

### 3.2 Out of scope

- unrelated provider additions or UI redesign;
- making pi-ai's auth/OAuth metadata authoritative in this initiative;
- silently mutating existing endpoint prices or credentials;
- changing generic non-Pi LLM paths, relay-local model capability shapes, or
  provider selection policy without a separate spec;
- weakening authorization, project scope, cost gates, Research Spine gates, or
  Done/report acceptance;
- broad or unbounded live model probes.

The duplicated auth/OAuth table remains declared architecture debt. It needs a
separate security-gated design because upstream authentication metadata and
Istara credential custody do not have the same authority boundary.

### 3.3 Non-negotiable invariants

1. Secrets, private base URLs, connection strings, and endpoint fingerprints
   never enter the generated catalog, receipts, logs, or committed fixtures.
2. A client cannot author `compat`, `thinkingLevelMap`, or catalog provenance.
   The backend constructs the capability envelope from the committed artifact.
3. Catalog-advertised endpoint flags may narrow a builtin capability, never
   enable a capability the builtin record denies.
4. Operator deployment values and explicit operator pricing override generated
   defaults. A zero/unpriced category continues to fail a budgeted run closed.
5. Unknown/custom/proxy models use an explicit fallback classification. No
   unknown model silently inherits an unrelated builtin record.
6. Unsupported effort is rejected with a stable typed error at session update
   or bind; it is never clamped or silently omitted.
7. Compatibility telemetry is operational evidence only. It cannot become
   research evidence or a positive self-improvement signal from raw tool
   success.
8. Research artifacts remain provisional through independent extraction,
   reliability, reconciliation, human review, route evidence, and Done/report
   gates. Provider compatibility cannot bypass any stage.
9. No live server, model load, chat completion, or network probe runs without a
   separately recorded owner authorization for that bounded target.
10. `LLMs/` and `Model_Finetuning/` are never moved, deleted, pruned, or cleaned.

## 4. Authority and precedence

### 4.1 Field ownership

| Field family | Canonical authority | Override rule |
| --- | --- | --- |
| builtin provider/model identity, `api`, `reasoning`, `thinkingLevelMap`, `compat`, input modalities, upstream context/output limits | exact pinned pi-ai registry | server-side catalog restriction may narrow; no client-side enabling |
| custom provider/model semantics | reviewed custom overlay with explicit `source: custom_overlay` | cannot impersonate builtin provenance; follows existing fallback until separately accepted |
| base URL, credential reference/custody, timeout, retry, enabled state | Istara operator endpoint configuration | always deployment-local; never generated from pi-ai into logs |
| effective context/output limits | minimum of valid upstream maximum and explicit operator restriction, with legacy behavior preserved for unknown models | expansion beyond upstream requires a governed custom classification, not a flag |
| effective runtime price | persisted/explicit operator contract price | generated pi-ai price is only a default and reconciliation suggestion; no silent overwrite |
| safety compat, including custom OpenAI-compatible developer-role restriction | Istara safety overlay | applied last and may only make behavior stricter |
| UI effort menu | generated pi-ai `getSupportedThinkingLevels(model)` result after lawful restrictions | `server_default` remains available; invalid saved state resets visibly |
| provider wire value | resolved pi-ai `thinkingLevelMap[logical_level]`, then pi-ai compat/detection | exact payload contract tests; no Istara provider switch table |

### 4.2 Resolution algorithm

For every turn:

1. Normalize the server-resolved `pi_provider` and model identifier without
   accepting a capability object from the request.
2. Exact-match that pair in the generated builtin projection.
3. If found, build the capability envelope from that record, attach catalog
   provenance, and apply only server-resolved restrictions.
4. If not found, exact-match a governed custom overlay. Mark it
   `custom_overlay` and preserve its existing explicit compat behavior.
5. Otherwise select a named legacy fallback reason such as
   `unknown_provider`, `unknown_model`, `proxy_override`, or
   `identity_mismatch`. Preserve the pre-change payload behavior.
6. Validate the requested logical effort against the generated supported
   levels. Map it
   through the upstream map or reject with `unsupported_model_effort`.
7. Add operator deployment values and prices.
8. Apply the Istara safety overlay last.
9. The worker validates schema, identity, version/digest shape, restrictions,
   pricing completeness, and allowed compat keys before constructing the pi-ai
   model.

A `pi_provider`/model mismatch or a capability-envelope identity mismatch is a
typed fail-closed error. It must not fall through to a different provider.

## 5. Contracts to implement

### 5.1 Generated catalog

Extend `backend/app/core/pi_runtime/data/pi_models_catalog.json` into a
deterministic artifact with top-level metadata and separate builtin/custom
sections. The exact JSON shape is finalized in W1, but it must carry:

- schema version;
- exact pi-ai package version and lockfile-integrity fingerprint;
- generator version and UTC generation timestamp excluded from semantic digest
  comparison;
- normalized semantic digest and pi-ai source-generation timestamp (not the
  wall-clock time of the local command, so clean generation is reproducible);
- builtin provider count/model count;
- for each model: provider, id, api, reasoning, full `thinkingLevelMap`, pi-ai
  `getSupportedThinkingLevels(model)` output, compat, input, context window,
  max tokens, and upstream catalog cost;
- for each custom overlay: stable overlay id, source file, reviewer rationale,
  and the same normalized fields it actually owns;
- auth hints only in the existing Istara-owned overlay, explicitly outside the
  pi-ai semantic digest.

The generator lives under `pi-runtime/scripts/`, imports
`@earendil-works/pi-ai/providers/all`, produces stable ordering and canonical
JSON, rejects duplicate identities/unknown keys/non-finite numeric values, and
supports:

- `--write` to regenerate;
- `--check` to fail when artifact and pin disagree;
- `--diff <old> <new>` to emit a machine-readable classified report;
- `--version`/metadata output for CI evidence.

Generation runs with network disabled after `npm ci`; no runtime provider call
or credential is needed.

### 5.2 Backend model and catalog API

`catalog.py` parses and validates the schema once, exposes exact provider/model
lookup, and retains a compatibility serializer for current API clients. Python
types gain `thinkingLevelMap`, `compat`, provenance, and explicit source/fallback
classification. Unknown fields fail closed in CI and startup validation.

Settings and Chat responses expose only non-secret, UI-needed fields. They may
expose derived `thinkingLevels` plus a safe capability source/version, but not
raw compatibility internals that would invite the client to become an
authority.

`endpoint_policy.py` continues to resolve catalog selection and secret custody.
It must distinguish generated defaults from operator values and must not write
upstream cost changes into existing endpoints during a read.

### 5.3 Ephemeral capability envelope

`engine._bind_payload` adds a `capability` object built from server-side exact
lookup and the resolved endpoint. It is not persisted and is not accepted from
Chat/Settings request JSON. Minimum fields:

```json
{
  "schema_version": 1,
  "source": "pi_ai_builtin",
  "pi_ai_version": "0.85.1",
  "catalog_digest": "sha256:...",
  "provider": "zai",
  "model": "glm-5.3",
  "api": "openai-completions",
  "reasoning": true,
  "thinking_level_map": {"minimal": "low", "xhigh": "xhigh", "max": "max"},
  "supported_thinking_levels": ["off", "minimal", "low", "medium", "high", "xhigh", "max"],
  "compat": {},
  "input": ["text"],
  "context_window": 0,
  "max_tokens": 0,
  "restrictions": {"reasoning": null, "vision": null}
}
```

The illustrative zero values above are not accepted as runtime maxima; actual
records must use the generated values or omit an unavailable optional field.
Pricing stays in the existing separate operator-controlled `pricing` envelope.
The bind also carries `supports_vision` until the capability envelope fully
owns that input-modality contract.

### 5.4 Worker resolution and provider wire

Replace `modelCapabilities()` provider lists with:

- strict capability-envelope validation;
- identity and API consistency checks;
- logical-effort validation and `thinkingLevelMap` translation;
- pi-ai model construction with inherited `reasoning`, `thinkingLevelMap`,
  `compat`, and `input`;
- the existing operator limit/price application;
- the custom OpenAI-compatible safety overlay last;
- an isolated, named legacy fallback function whose output is captured before
  modification and kept byte-identical for unlisted DashScope/proxy fixtures.

Provider-specific knowledge may remain only when it is an Istara safety policy
or a governed custom overlay. Every remaining provider-name branch must be
listed and justified in the architecture document.

### 5.5 Effort validation and observability

Session create/update and Chat bind validate the logical effort using the
selected effective catalog record. `server_default` and no value remain valid.
An endpoint/model switch invalidates an incompatible saved effort and returns a
visible normalization reason; arbitrary strings such as `banana` are rejected.

Record a sanitized compatibility receipt alongside existing usage/route
telemetry:

- capability source (`pi_ai_builtin`, `custom_overlay`, or named fallback);
- pi-ai version and catalog digest prefix;
- normalized provider/model public ids;
- requested logical effort, mapped provider effort, and outcome;
- effective reasoning/modality flags;
- names of applied restrictions/overlays;
- fallback or rejection reason;
- route-evidence handle and project scope already owned by the execution path.

Never record secret values, private URLs, raw prompts, completions, source
content, or connection strings. Receipt success is not evidence of research
quality, model quality, or skill fitness.

### 5.6 Pricing reconciliation

Add a read-only report that compares persisted endpoint rates with generated
defaults and classifies `same`, `unpriced`, `under`, `over`, and `custom` by
category. Applying suggested prices is an explicit operator mutation with
before/after evidence and rollback data. No startup, catalog read, or version
bump silently changes persisted cost. A budgeted turn with token use in an
unpriced category remains `cost_budget_unpriced`.

## 6. Dependency-ordered delivery waves

Every wave starts from a clean, recorded base reference; preserves ambient
worktree changes; runs its before-gate; uses a role-specific Compass Forge work
order; receives comprehensive independent review; remediates findings through
delta review; and cannot advance until all acceptance and evidence rows pass.

### W0 — Governance reset, impact closure, and frozen baseline

**Purpose:** make the expanded owner-approved objective the durable execution
contract before any code changes.

**Tasks**

1. Revise or supersede the narrow CF-SPEC-29 request/acceptance so it covers
   the winning plan, Research Spine impact, security/UI obligations, version
   update, cost behavior, rollback, and explicit live authorization.
2. Create the complete CF task DAG and gates. Do not reuse the master synthesis
   task as an implementation task.
3. Save CF impact/graph/model/zones output for `catalog.py`,
   `endpoint_policy.py`, `engine.py`, Settings/Chat routes, frontend model
   controls, and worker files. For unresolved `.mjs` graph seeds, attach an
   `rg` import/call-site inventory and record the graph limitation.
4. Freeze 0.84.3 registry and mirror reports, all hand-coded provider branches,
   current payload captures for builtin and fallback models, current error
   behavior, UI menus, effective prices, and worker cold-start/RSS.
5. Correct the `glm-5.3-flash` baseline with direct package evidence.
6. Classify every currently contrary test as `preserve`, `intentionally flip`,
   or `architecture debt`; no test is merely edited until its classification is
   accepted.

**Required fixtures**

- Codex/Luna logical low and high;
- DeepSeek reasoning and non-reasoning;
- Qwen/DashScope listed and unlisted proxy;
- Zai `glm-5.3` and the version-dependent flash model;
- one non-reasoning builtin;
- one vision builtin;
- one governed custom overlay;
- unknown provider, unknown model, identity mismatch, invalid effort;
- priced, partially priced, and unpriced usage.

**Acceptance**

- expanded spec and task graph trace every plan acceptance criterion;
- baseline artifacts contain no secrets/private endpoints;
- fallback payload fixtures are immutable and hash-addressed;
- no product file has changed;
- implementation remains blocked on owner approval of the winning plan.

**Verification**

```bash
git status --short
rg -n "modelCapabilities|thinkingLevels|thinkingLevelMap|compat|supports_reasoning|supports_vision|pi_provider|pricing" backend pi-runtime frontend tests
cd pi-runtime && npm test
cd .. && pytest tests/test_pi_runtime_endpoints.py tests/test_settings_agentic_pi_endpoints.py tests/test_chat.py tests/test_provider_contracts.py tests/test_model_provider_contract.py -q
```

**Rollback:** delete only newly generated ignored baseline artifacts and revert
the W0 spec/task changes through Compass Forge; no application rollback exists.

### W1 — Deterministic authority projection on 0.84.3

**Purpose:** replace the manually maintained builtin mirror with a reproducible
artifact before changing package version or runtime behavior.

**Tasks**

1. Implement the generator, schema validator, semantic digest, drift report,
   and deterministic tests.
2. Split builtin pi-ai semantics from Istara-owned auth hints and custom
   overlays; retain the governed DashScope overlay with explicit provenance.
3. Generate the artifact from 0.84.3, update Python catalog types/serialization,
   and keep the public API backwards compatible while adding safe derived
   levels/provenance.
4. Add CI/check-integrity enforcement that the artifact matches
   `pi-runtime/package.json` and lockfile exactly.
5. Add a read-only cost-reconciliation report; do not mutate endpoints.

**Acceptance**

- two clean generations are byte-identical;
- counts and each normalized builtin field equal public pi-ai API output;
- custom overlays cannot collide with or claim builtin provenance;
- `--check` fails on package/artifact/version/digest drift;
- catalog responses remain authorized and contain no secret/private fields;
- existing endpoint prices do not change on catalog load or application start.

**Verification**

```bash
cd pi-runtime && npm ci --engine-strict --ignore-scripts && npm test
node scripts/export-istara-catalog.mjs --check
cd ..
pytest tests/test_pi_runtime_endpoints.py tests/test_settings_agentic_pi_endpoints.py tests/test_chat.py tests/test_security_benchmark.py -q
python scripts/check_integrity.py
python scripts/security_benchmark.py --fail-on-threshold
```

Add generator-specific tests to `npm test` and catalog/cost reconciliation
tests to the listed pytest files or narrowly named new files.

**Rollback:** revert generator/schema/artifact/catalog changes together. Restore
the prior JSON and parser; no database migration is permitted in this wave.

### W2 — Server-built bind envelope and worker conformance on 0.84.3

**Purpose:** make one generated record flow from endpoint selection to pi-ai
model construction with strict validation and unchanged fallback behavior.

**Tasks**

1. Add exact lookup and effective-capability resolution to the backend.
2. Add the typed ephemeral envelope to `_bind_payload`, including modality,
   source/version/digest, restrictions, and named fallback classification.
3. Remove builtin provider lists from worker `modelCapabilities`; retain only
   justified safety/custom/fallback code.
4. Validate envelope identity and allowed compat fields before model creation.
5. Map logical effort through `thinkingLevelMap`; reject unsupported values at
   session update and bind.
6. Add sanitized receipts and route-evidence linkage without making receipts
   research evidence or self-improvement reward.
7. Preserve independent multi-model/research validation behavior and prove that
   provider selection cannot skip route evidence or Done/report gates.

**Acceptance**

- exact builtin hit uses generated pi-ai `reasoning`, map, compat, and input;
- explicit endpoint restrictions narrow but cannot enable capabilities;
- on 0.84.3, Codex logical `minimal` maps to provider `low` while logical
  `low` remains identity; 0.85.1 must either preserve that measured direction
  or expose it as a classified semantic diff, with captured wire assertions;
- DeepSeek, Qwen, and Zai exact request bodies match pi-ai contract fixtures;
- unsupported logical effort returns `unsupported_model_effort` without a
  network call;
- unlisted DashScope/proxy payload and detection are byte-identical to W0;
- malformed, stale-schema, or identity-mismatched envelopes fail closed;
- `supports_vision` reaches worker model input;
- budgeted unpriced usage still fails closed;
- receipts are redaction-tested and project-scoped;
- Research Spine routing/reconciliation/Done gates remain non-bypassable.

**Verification**

```bash
cd pi-runtime && npm test
cd ..
pytest tests/test_pi_runtime_endpoints.py tests/test_settings_agentic_pi_endpoints.py tests/test_chat.py tests/test_provider_contracts.py tests/test_model_provider_contract.py -q
pytest tests/pi_production/test_chat_pi_asgi.py tests/pi_production/test_engine_http_provider.py tests/pi_production/test_w3_research_spine.py tests/pi_production/test_research_spine_donor_routing.py -q
pytest tests/test_research_validity_contract.py tests/test_research_spine_end_to_end.py tests/test_research_spine_donor_routing.py -q
python scripts/security_benchmark.py --fail-on-threshold
```

**Rollback:** revert the bind schema/backend resolver and worker consumer as one
unit. The W1 generated catalog may remain because its public serializer is
backwards compatible. No persisted state needs rollback.

### W3 — Controlled pi-ai 0.85.1 adoption

**Purpose:** make the version update a measured regeneration event after the
compatibility machinery is trustworthy.

**Tasks**

1. Update the exact dependency and lockfile with scripts disabled during
   install; capture package integrity and license/provenance evidence.
2. Regenerate the builtin artifact from 0.85.1.
3. Produce a classified before/after report for additions, removals, renames,
   API changes, reasoning/maps/compat, modality, limits, and prices.
4. Require an explicit disposition for every semantic breaking change.
   Registry additions with no behavior conflict may be accepted as generated
   data; removals/renames and cost changes are never silently accepted.
5. Re-run W1/W2 conformance plus pi production and benchmark tests. Compare any
   broad-suite failures with the frozen base so inherited debt is not reported
   as a regression.
6. Measure worker cold-start/RSS and turn setup against W0 even though the full
   registry is not imported in workers.

**Acceptance**

- package.json, lockfile, artifact version, and digest agree on 0.85.1;
- no unclassified semantic diff remains;
- the flash-model presence and Zai maps are established by direct evidence;
- runtime wire fixtures either remain identical or have an approved upstream
  compatibility reason and new expected payload;
- cold-start/RSS does not regress beyond the predeclared W0 budget; any breach
  blocks the wave rather than being waived after measurement;
- all deterministic Pi runtime, backend, security, and benchmark gates pass.

**Verification**

```bash
cd pi-runtime && npm ci --engine-strict --ignore-scripts && npm test
node scripts/export-istara-catalog.mjs --check
cd ..
pytest tests/pi_production -q
pytest tests/pi_benchmark -q
pytest tests/test_pi_runtime_endpoints.py tests/test_settings_agentic_pi_endpoints.py tests/test_chat.py tests/test_provider_contracts.py tests/test_model_provider_contract.py -q
python scripts/check_integrity.py
python scripts/security_benchmark.py --fail-on-threshold
```

If `tests/pi_production` or `tests/pi_benchmark` contains an explicitly live
case, invoke its documented deterministic selection instead of silently
skipping; declare a live-only requirement `not_runnable` until W6 authorization.

**Rollback:** restore the prior package.json and lockfile, run `npm ci
--engine-strict --ignore-scripts`, regenerate the 0.84.3 artifact, and rerun W1
plus W2 checks. Do not hand-edit generated JSON.

### W4 — System contract, security, documentation, and pricing acceptance

**Purpose:** converge the surrounding product and governance surfaces after
runtime semantics and the version pin are stable.

**Tasks**

1. Update Settings/Chat types and controls to use exact derived levels,
   `server_default`, invalid-state recovery, loading/error/empty states, and
   safe capability provenance.
2. Add the operator-facing cost reconciliation preview and explicit apply/
   rollback flow only if separately authorized as a mutation. Without that
   authorization, ship preview plus `unpriced` fail-closed guidance.
3. Update `docs/architecture/research-validity-contract.md` only if the durable
   contract needs a clarified provider-route seam; otherwise attach evidence
   showing compliance without gratuitous edits.
4. Update `docs/architecture/self-improvement-governance-contract.md` if
   compatibility receipts enter telemetry/learning plumbing; explicitly bar raw
   receipt success from promotion signals.
5. Update `docs/features/content/settings/llm-servers/architecture.md` and
   researcher guidance, Pi runtime protocol/architecture docs, `TESTING.md`,
   `testing/TEST_HISTORY.md`, `CHANGE_CHECKLIST.md`, and `Tech.md` as required by
   the actual diff.
6. Document the update runbook: pin, install, generate, diff, classify, test,
   container acceptance, bounded live acceptance, and rollback.
7. Update `security/control_matrix.json`,
   `security/SECURITY_BENCHMARK.md`, and
   `tests/test_security_benchmark.py` if trigger patterns, controls, or evidence
   paths changed.

**Acceptance**

- UI exposes only levels the selected model supports and does not silently
  preserve an invalid saved level;
- all catalog/settings routes retain authentication, authorization, and project
  scoping;
- cost changes are previewed and auditable; no implicit endpoint mutation;
- receipts pass redaction and self-improvement-governance tests;
- required architecture and testing documentation describes the implemented
  contract, not the starting hypothesis;
- feature-obligation and documentation generators are clean.

**Verification**

```bash
cd frontend && npm run test:unit && npx tsc --noEmit && npm run lint && npm run build
cd ..
pytest tests/test_chat.py tests/test_settings_agentic_pi_endpoints.py tests/test_feature_docs.py tests/test_security_benchmark.py -q
python scripts/feature_docs.py --seed-missing --generate-site --check
python scripts/check_feature_obligations.py --base origin/testing --head HEAD --json-out artifacts/feature-obligations.json
python scripts/check_test_harness.py
python scripts/check_integrity.py
python scripts/security_benchmark.py --fail-on-threshold
```

**Rollback:** revert UI/API/doc/receipt changes as one reviewed set. Endpoint
cost application, if authorized, needs a separately captured per-endpoint
before-state rollback; code rollback alone is insufficient after that mutation.

### W5 — Container-first real-user acceptance

**Purpose:** prove the feature through the browser and deployed container shape,
not only through unit contracts.

**Tasks**

1. Extend or add a registered scenario under
   `tests/simulation/scenarios/` that uses browser actions to open Settings,
   select/configure models, open Chat, switch model/effort, and observe success
   or typed failure. API-behind-browser setup must be labeled.
2. Cover admin, researcher, viewer, and stranger where auth-adjacent; light and
   dark; 375 px reflow; keyboard Tab and visible focus; loading, error, empty,
   unsupported-effort, and unpriced states.
3. Use synthetic projects/endpoints and loopback payload-capture providers only.
   No golden data, destructive mutation, private URL, or live model.
4. Register the scenario in
   `tests/simulation/lib/scenario-registry.mjs`, update the coverage matrix and
   dated verdict, and update `TESTING.md`/`testing/TEST_HISTORY.md` if topology
   or release behavior changed.
5. Extend `tests/real_user_benchmark/lib/model-management-probes.mjs` and the
   Research Spine probes because model-management and research routing are in
   scope. Credential-free runs must pass or return an explicit `not_runnable`
   for a genuinely live-only assertion.
6. Run in the `docker-compose.qa.yml` `ui` profile with loopback-only publish;
   retain screenshots, HAR, console, network, backend/frontend, and Docker
   evidence.

**Acceptance**

- a user sees the exact model-native effort menu and can select a supported
  level end to end;
- unsupported effort, missing endpoint, unpriced budget, and catalog error are
  honest visible states, never fabricated success;
- role restrictions, responsive behavior, focus, and both themes pass;
- browser, console, network, container identity, and API receipt agree on the
  same provider/model/effort without exposing secrets;
- Research Spine probes show evidence remains provisional until accepted Done
  tasks and report gates.

**Verification**

```bash
docker compose -f docker-compose.qa.yml --profile contract config --quiet
cd tests/simulation && npm run test:static
cd ../..
pytest tests/test_simulation_project_scope_contracts.py tests/test_integration_simulation_scope.py tests/test_project_scope_contracts.py -q
npm --prefix tests/real_user_benchmark run check
```

After explicit authorization to start the disposable stack:

```bash
./scripts/istara-qa.sh render
./scripts/istara-qa.sh up
./scripts/istara-qa.sh wait
./scripts/istara-qa.sh seed
cd tests/simulation && node run.mjs --scenario <assigned-id> --engine pi
cd ../.. && ./scripts/istara-qa.sh collect && ./scripts/istara-qa.sh down
```

The teardown command runs even on scenario failure. The implementer must use
the actual assigned scenario id and artifact paths in CF command evidence.

**Rollback:** revert scenario/UI behavior with W4/W2 as appropriate; stop and
remove only the named disposable QA project through its documented lifecycle.

### W6 — Bounded live T1 and release acceptance

**Purpose:** confirm provider-observed behavior for the configured targets and
close the gap between deterministic conformance and live compatibility.

**Preconditions**

- explicit owner authorization names exactly one configured target at a time,
  spend ceiling, prompt fixture, timeout, and allowed providers;
- rebuilt container/image identity and 0.85.1 catalog digest are verified;
- deterministic W0–W5 gates and independent review are green;
- no command discovers or probes unrelated LAN endpoints.

**Tasks**

1. Re-run the bounded T1 baseline for Luna/Codex, Terra, and Zai/GLM one target
   at a time, using synthetic non-research prompts and minimal output.
2. Capture sanitized request/payload evidence at the controlled adapter or
   loopback proxy plus usage receipt. Never log credentials or private URLs.
3. Confirm logical `low` and `minimal` and their exact mapped provider
   values/behavior; for Codex, verify the 0.85.1 map rather than assuming the
   direction.
4. Mark quota/unavailable providers `not_runnable` with environmental evidence;
   never substitute another model or fabricate a pass.
5. Run final independent comprehensive review, reconcile findings through delta
   review, produce release/rollback evidence, and stop at the configured ship
   boundary. No worker merges, pushes, or opens a PR.

**Acceptance**

- each authorized live target has exact route attribution, 200/typed failure,
  reported logical effort, mapped provider effort, usage, cost, stop reason,
  version/digest, and redaction proof;
- provider-observed payload behavior matches deterministic fixtures;
- fallback target behavior remains unchanged;
- all non-runnable gates remain visibly pending; a healthy process or 200 alone
  is not live acceptance;
- final status distinguishes tested, reviewed, merged, promoted, and
  live-verified states.

**Verification:** the exact live command is intentionally not hard-coded in the
plan because it must name the owner-authorized endpoint/profile at execution
time. Record the approved command, target alias, ceiling, result, and artifact
paths as Compass Forge command evidence. Re-run the deterministic W3/W5 release
set after live probes without starting additional models.

**Rollback:** restore the W3 pin/artifact and W2 runtime as one release unit,
rebuild, verify container identity, and rerun deterministic fallback/route
smoke. Restore any explicitly applied endpoint prices from the captured
before-state. Live acceptance is revoked until repeated on the restored build.

## 7. Task DAG and ownership

The implementation spec should create narrowly owned tasks with these edges:

```text
T0 spec/impact/baseline
  -> T1 generator + schema + deterministic drift tests
  -> T2 Python catalog/API + custom overlay separation
  -> T3 endpoint resolver + ephemeral bind envelope
  -> T4 worker validation/model construction + wire fixtures
  -> T5 effort/session validation + sanitized receipts
  -> T6 Research Spine/security/cost reconciliation contracts
  -> T7 pi-ai 0.85.1 pin + regenerate + classified diff
  -> T8 frontend Settings/Chat behavior + unit/build gates
  -> T9 docs/update runbook/governance matrices
  -> T10 container-first user journey + benchmark probes
  -> T11 bounded live T1 (owner-authorized only)
  -> T12 independent final review/release handoff
```

T3 and T4 may be implemented in parallel only after the capability-envelope
schema is frozen and each uses independent files/tests. T5 depends on both.
T6 may draft tests early but cannot accept until T5. T8 depends on the safe API
serializer from T2 and validation semantics from T5. T7 occurs after the W1/W2
machinery is green. T10 depends on T7–T9. T11 depends on all deterministic
gates and separate live authorization. Every code task owns its tests and
required docs in the same change.

## 8. Acceptance matrix

| ID | Given / when / then | Proof |
| --- | --- | --- |
| AC-01 | Given an exact builtin pair, when generation runs, then every projected semantic field equals the pinned pi-ai record. | generator conformance + semantic digest report |
| AC-02 | Given an exact builtin pair, when a turn binds, then the worker uses the server-selected inherited reasoning/map/compat/input with only lawful restrictions. | backend bind capture + worker model snapshot |
| AC-03 | Given Codex logical `minimal` and `low`, when bound, then the upstream map produces their exact provider values rather than clamp/omission; the 0.84.3 baseline is `minimal -> low` and identity `low`. | unit mapping + wire payload capture + bounded live receipt |
| AC-04 | Given DeepSeek/Qwen/Zai fixtures, when turns bind, then provider-specific payloads match pi-ai contracts without Istara provider tables. | per-provider golden semantic/payload diffs |
| AC-05 | Given an unlisted DashScope/proxy model, when bound, then fallback classification and payload are byte-identical to W0. | hash-addressed before/after fixture |
| AC-06 | Given unsupported effort or capability identity mismatch, when session updates/binds, then a stable typed error occurs before network I/O. | backend + worker negative tests and zero-request assertion |
| AC-07 | Given a vision builtin, when bound, then `input` contains image; an explicit restriction can remove but not add it. | bind/model snapshots |
| AC-08 | Given generated cost changes, when catalog loads, then persisted prices stay unchanged and an auditable reconciliation preview is available. | DB before/after + report fixture |
| AC-09 | Given token use in any zero-priced category under a budget, when usage settles, then execution fails closed. | deterministic budget tests |
| AC-10 | Given 0.85.1, when regenerated, then every semantic diff is classified and lockfile/artifact/version agree. | diff report + `--check` + lock integrity |
| AC-11 | Given Chat/Settings, when a user changes model, then only valid native efforts appear and invalid saved state recovers visibly. | frontend unit + Playwright roles/themes/mobile/keyboard/state matrix |
| AC-12 | Given a research execution, when compatibility resolution succeeds/fails, then route evidence and Research Spine reliability/reconciliation/Done/report gates remain intact. | spine contract and production scenario tests |
| AC-13 | Given compatibility telemetry, when stored/exported/learned from, then it is sanitized, project-scoped, and cannot directly promote a skill/model/process policy. | security and self-improvement governance tests |
| AC-14 | Given a future pi-ai bump, when the runbook is followed, then generation/diff/tests expose drift before product behavior changes. | clean-room runbook rehearsal on pinned package |
| AC-15 | Given an authorized live target, when low effort is probed, then route, mapped effort, payload behavior, usage, cost, and version attribution agree. | bounded T1 evidence; otherwise explicit `not_runnable` |

## 9. Review dimensions and release gates

Each comprehensive review covers:

- architecture authority and absence of duplicate provider knowledge;
- generated-artifact determinism and supply-chain provenance;
- API/bind schema trust boundary and secret redaction;
- effort mapping and exact provider wire behavior;
- unknown/custom fallback parity;
- pricing, budget, and operator-mutation safety;
- authentication, authorization, project scope, and security benchmark;
- Research Spine and self-improvement governance;
- UI correctness/accessibility/responsiveness/state coverage;
- Docker build/runtime identity, performance, docs, rollback, and future-update
  operability.

Objective after-gates must include at least the commands named by their wave.
A green existing container, non-empty output, passing unit subset, or HTTP 200
cannot substitute for the required evidence. Broad failures are compared with
the frozen W0 base and recorded as inherited debt or new regression.

## 10. Risks and mitigations

| Risk | Mitigation / stop condition |
| --- | --- |
| Generated artifact becomes another stale mirror. | Lockfile-bound version/digest, deterministic `--check`, CI failure, and update runbook. |
| Backend sends a forged/stale/inconsistent capability. | Server-only construction, strict schema/identity checks on both sides, version/digest receipt, negative tests. |
| Map direction is misread. | Generator and mapping tests compare public pi-ai records and captured wire payloads; live proof uses observed 0.85.1 map. |
| Upstream cost changes alter spend unexpectedly. | Generated cost is default only; previewed explicit reconciliation; budget remains fail-closed. |
| Existing endpoints remain zero-priced. | Report as `unpriced`; budgeted turns remain blocked until operator applies audited rates. Do not claim automatic repair. |
| Registry removal or rename strands an endpoint. | Classified diff blocks update; explicit custom/fallback/migration decision with rollback. |
| Unknown proxies change through detection. | Frozen byte-identical fallback fixtures; any new default semantics require a separate owner decision. |
| UI advertises unsupported effort. | Derive menu from effective record, validate at update and bind, visible invalid-state recovery. |
| Compat accepts unsafe arbitrary keys. | Allowlisted typed schema and Istara safety overlay last. |
| Telemetry leaks private infrastructure or contaminates learning. | Redaction fixtures, project scoping, no URLs/secrets/raw content, governance tests bar raw-success promotion. |
| Runtime/package update regresses memory or startup. | W0 baseline and predeclared W3 performance budget; full registry remains generation-time only. |
| Test edits normalize a behavior change. | W0 test-disposition register and before/after payload fixtures reviewed before modifications. |
| Graph misses dynamic/JavaScript seams. | Pair CF impact with explicit `rg`/call-site inventory and container journey. |
| Live proof causes spend or loads multiple models. | Separate explicit authorization, one target at a time, hard ceiling/timeouts, minimal synthetic prompt. |

## 11. Coverage matrix across source drafts

| Master-plan section | Draft A contribution | Draft B contribution | Draft C contribution |
| --- | --- | --- | --- |
| Authority and precedence | Canonical pi-ai semantics, monotonic advertised restrictions, operator and safety layers | Single generated authority seam; operator cost/deployment ownership | Strictest-last layering and explicit custom/gateway identity |
| Generated catalog | Deterministic mirror, provenance, custom overlay | One projection serving worker/UI/cost/validation; drift quantification | Mirror regeneration mechanics and 0.85.1 gating |
| Bind/runtime design | Direct exact lookup goal, receipt, fallback parity, vision seam | Typed capability descriptor and avoidance of per-worker full-registry load | Exact provider/model resolution and fail-closed mismatch |
| Effort/wire conformance | Codex lost mapping and provider payload diffs | Dead `thinkingLevels`, clamp/invalid-effort and Zai test contradictions | Exact UI levels and live mapped-effort acceptance |
| Version sequencing | Lockstep pin/artifact and broad release gates | Build correction machinery before bump; classify diff | Version update as an independently reversible wave |
| Pricing | Operator effective pricing and unpriced fail-closed | Quantified price drift and Zai budget impact | Keep pricing as backend/operator policy |
| Governance/security/spine | Sanitized receipts, Research Spine/security/UI contracts | Auth inheritance deferred; telemetry and owner decision boundaries | Explicit non-bypass and bounded-live constraints |
| Verification/rollback | Full deterministic, container, live ladder and terminal-state truth | Detailed acceptance criteria, performance and before/after gates | Compact dependency ordering and two-way rollback |

No draft was concatenated verbatim. The synthesis adopts draft B's efficient
generated projection, draft A's stronger authority/precedence/governance model,
and draft C's strict resolution and reversible version boundary. It rejects
both a hand-maintained runtime provider switch and a full `providers/all`
import in every worker.

## 12. Owner decisions at the winning-plan gate

The winning plan asks the owner to approve these bounded choices before code:

1. **Architecture:** generated pi-ai semantic projection plus ephemeral
   server-built bind envelope, not per-worker full-registry lookup.
2. **Fallback:** preserve current unknown/custom behavior byte-for-byte in this
   initiative; detection-as-new-default requires a later explicit decision.
3. **Version:** build conformance on 0.84.3, then update to 0.85.1 within the
   same initiative as a separately reversible wave.
4. **Pricing:** never silently mutate existing endpoints; ship reconciliation
   preview, and require separate explicit authorization before applying rates.
5. **Auth metadata:** retain the Istara-owned table as declared architecture
   debt and handle pi-ai auth inheritance in a separate security design.
6. **Live acceptance:** authorize only after W0–W5, with named targets and spend
   ceilings at execution time.

Approval authorizes creation/revision of the durable CF spec and task DAG. It
does not itself authorize live probes, endpoint price mutation, merge, push,
promotion, or deployment.
