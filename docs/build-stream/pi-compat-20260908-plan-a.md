# Plan A — Pi capability inheritance and compatibility authority

**Candidate:** A  
**Task:** `pi-compat-20260908-PLAN-A`  
**Planning phase:** independent draft  
**Scope:** planning only; no implementation is authorized by this artifact

## 1. Executive decision

Make the installed, exactly pinned `@earendil-works/pi-ai` model registry the
runtime authority for canonical model semantics. When
`getBuiltinModel(pi_provider, model)` resolves, Istara starts from that complete
model record and preserves pi-ai's `api`, `reasoning`, `thinkingLevelMap`,
`compat`, headers, sampling defaults, and future reviewed model fields. Istara
then applies only deployment-owned values and monotonic safety constraints.

The precedence contract is:

1. **pi-ai canonical model record** — provider/model wire and reasoning
   semantics.
2. **catalog-advertised capability restrictions** — explicit `false`, smaller
   limits, or a narrower input set may restrict a canonical record; catalog
   data cannot silently enable a capability that pi-ai denies.
3. **operator deployment contract** — endpoint URL, credential handle,
   contract pricing, retry/timeout policy, and an explicitly governed proxy
   transport exception.
4. **Istara safety overlay** — project/route authorization, secret custody,
   budget enforcement, and conservative compatibility flags such as disabling
   the `developer` role on a custom OpenAI-compatible endpoint.

If the canonical lookup does not resolve, the current provider-identity and
URL-detection behavior runs through one named `legacy/custom fallback`
function. Its normalized model and captured wire payloads are frozen before
the refactor and must remain byte-identical. This keeps DashScope, proxies, and
other governed custom models working without turning their exceptions into a
second catalog of pi-ai facts.

The Python catalog remains static at runtime, but it must be generated
deterministically from the pinned Node package and checked for drift. Istara's
auth/login metadata and governed custom-provider overlays stay separate because
they are product/security policy, not pi-ai model knowledge.

## 2. Measured starting point

These measurements were made in the shared worktree on 2026-09-08 without
starting services or loading a model:

- Both `pi-runtime` and `labs/pi-replacement` pin
  `@earendil-works/pi-ai` and `@earendil-works/pi-agent-core` at `0.84.3`.
- The installed 0.84.3 pi-ai registry exposes 39 providers and 1,312 models.
  The shipped backend mirror contains 40 provider keys and 1,307 models,
  including the Istara-only DashScope overlay. Compared by provider/model ID to
  installed pi-ai, it has 81 missing canonical records and 36 stale canonical
  records. Therefore provider/model counts alone are not an adequate freshness
  proof.
- The published 0.85.1 package exposes the stable public
  `@earendil-works/pi-ai/providers/all` entry point, including
  `getBuiltinModel`, `getBuiltinProviders`, `getBuiltinModels`, and
  `getBuiltinModelDataGeneratedAt`; it currently reports 39 providers and
  1,354 models.
- In 0.85.1, `openai-codex/gpt-5.6-luna` carries a
  `thinkingLevelMap`, and `zai/glm-5.3` plus `glm-5.3-flash` carry their
  reasoning map and full `compat` record. The mirror has no `glm-5.3-flash`
  and has no thinking map for `glm-5.3`.
- `pi-runtime/src/provider.mjs` currently hand-lists Codex, DeepSeek, Qwen,
  and Zai capability behavior and builds a new partial model instead of
  inheriting the builtin record. It does not pass `thinkingLevelMap`.
- `backend/app/core/pi_runtime/catalog.py` drops `thinkingLevelMap` and
  `compat`. `endpoint_policy.py` copies only selected booleans/limits.
  `ResolvedPiEndpoint` holds `supports_vision`, but `_bind_payload()` does not
  send it to the worker. These are compatibility-path architecture debts.
- The chat effort menu already consumes `thinkingLevels`; no menu redesign is
  required. Its data must become the standard Pi thinking levels returned by
  `getSupportedThinkingLevels(model)`, not provider wire strings.
- Native Compass Forge impact output was high-confidence/tree-sitter for the
  Python runtime/catalog/endpoint files and the TSX chat control. It links the
  runtime through dispatcher, seams, telemetry, chat, autoresearch, validation,
  donor routing, and Research Spine tests. The `.mjs` seed did not resolve in
  the current index and returned low confidence, so direct call-site search and
  the Node test inventory remain mandatory for that half of the graph.
- Current deterministic baselines pass: 14 provider-parameter Node tests and
  47 selected Python catalog/version/runtime tests. Simulation scenario 36
  resolves in dry-run mode without launching services.

## 3. Authority and merge contract

| Field or concern | Authority | Required behavior |
| --- | --- | --- |
| `id`, `pi_provider` | selected endpoint identity | Exact pair is the lookup key; no fuzzy model matching. |
| `api` / provider wire adapter | pi-ai for a builtin hit | A contradictory `provider_kind` fails validation unless a named, tested proxy exception is present. Unknown/custom models retain today's `provider_kind` mapping. |
| `reasoning` | pi-ai, restricted by explicit catalog false | An explicit false disables reasoning and its map; no provider-name default may re-enable it. |
| `thinkingLevelMap` | pi-ai for a builtin hit | Copy unchanged. Pi levels are keys; mapped values are provider wire values. Never hand-maintain a second map. |
| `compat`, `headers`, `samplingParams` | pi-ai baseline | Preserve pi-ai fields. Merge only documented custom-model compatibility and monotonic safety overrides; snapshot field-set changes on every bump. |
| `input` / vision | pi-ai, narrowed by advertised endpoint capability | Propagate the effective value through config → resolver → bind → worker. Explicit false is preserved. |
| `contextWindow`, `maxTokens` | pi-ai defaults, operator may lower | Never let a stale mirror enlarge a runtime limit. |
| `cost` | operator's contract rates | Do not replace negotiated rates with pi-ai list prices; all spent categories remain fail-closed when unpriced. |
| `baseUrl`, credentials, OAuth/account identity | Istara deployment/security | Never inherit a URL or secret custody decision merely because a builtin model resolved. |
| retries, timeout, budgets | Istara execution policy | Preserve present bounds and cumulative accounting. |
| route/project/evidence handles | Istara Research Spine | Capability resolution must not alter route authorization, model-independence proof, reconciliation, or Done/report gates. |

The resolver should return both the effective model and a content-free receipt:

```text
capability_source = pi_builtin | governed_custom | legacy_fallback
pi_ai_version, registry_generated_at, registry_digest
pi_provider, model, api, reasoning, supported_pi_levels
applied_override_names, fallback_reason
```

Do not log URLs, headers, credential handles, raw prompts, responses, or
endpoint fingerprints. The receipt is observability evidence, not report
evidence and not a positive self-improvement signal.

## 4. Target flow

```text
pinned pi-ai registry ──generator/check──> canonical static catalog projection
        │                                      │
        │ exact runtime lookup                 ├─> Settings / Chat menus
        │                                      └─> catalog endpoint admission
        v
canonical model seed
        + catalog restrictions
        + endpoint deployment values
        + Istara safety overlay
        v
effective pi-ai model + capability receipt
        v
pi-agent-core turn (unchanged Research Spine route/evidence/Done gates)
```

The generator writes the existing provider-map JSON shape to avoid an API
migration and writes provenance beside it. A separate reviewed custom overlay
contains DashScope/custom records. The merge rejects provider/model collisions,
unknown schema fields, non-canonical ordering, and a custom record without a
wire-capture fixture.

## 5. Dependency-ordered delivery waves

Implementation starts only after the synthesized winning plan receives owner
approval. Each wave is an immutable Build Stream wave with before/after gates,
command evidence, independent review, and remediation convergence before its
successor begins.

### W0 — Replace the stale execution contract and freeze behavior

**Purpose:** make the expanded objective executable without losing today's
fallback behavior.

1. Revise `CF-SPEC-29` to the owner-approved total-compatibility scope, clarify
   the authority table above, and replace/supersede its narrow generic task set.
   Create dependency edges for W1–W6 and role-specific work orders. No product
   edit may begin while the spec still describes only the narrow inheritance
   change.
2. Refresh Compass Forge and run native impact for the runtime, catalog,
   endpoint, chat, validation, autoresearch, donor-routing, telemetry, and
   Research Spine seams. Record the `.mjs` low-confidence gap if it persists;
   compensate with `rg` call-site inventory and Node test ownership rather than
   a legacy CF runtime.
3. Capture pre-change deterministic fixtures from 0.84.3:
   - complete normalized model records for Codex, Zai, DeepSeek, Qwen and a
     generic unknown/proxy;
   - `onPayload` wire captures for `off/minimal/low/medium/high/xhigh/max` where
     supported;
   - error/fallback classification, developer-role behavior, vision, limits,
     pricing, and identity receipts;
   - catalog provider/model IDs and provenance.
4. Audit every currently configured endpoint passively for exact builtin hit,
   transport mismatch, and fallback source. Output counts and stable endpoint
   IDs only; never read or print secrets or private URLs.

**Gate:** reviewed authority contract, expanded CF coverage with no drift,
green baseline fixtures, and an explicit disposition for every transport
mismatch. Rollback is artifact deletion only.

### W1 — Pin 0.85.1 and make catalog regeneration reproducible

**Purpose:** establish one version/provenance boundary before changing runtime
resolution.

1. Pin both `@earendil-works/pi-ai` and
   `@earendil-works/pi-agent-core` to exact `0.85.1` in both bundled surfaces,
   regenerate both lockfiles, and update the version-provenance test. Lockstep
   is required because pi-agent-core declares the corresponding pi-ai train.
2. Add a deterministic Node generator plus `--check` mode. It imports only the
   public `providers/all` and model helper exports from the installed pin,
   produces canonical ordering/format, and writes a provenance manifest with
   package versions, registry generation timestamp, generator schema version,
   model-field-set hash, catalog hash, and custom-overlay hash.
3. Extract the current DashScope/custom additions into a separate governed
   overlay. Keep Python auth methods, OAuth flows, env-var names, and secret
   custody metadata in Istara code; pi-ai's model registry does not own them.
4. Extend the Python catalog schema and frontend API/types with standard
   `thinkingLevels` derived by `getSupportedThinkingLevels`; retain
   `thinkingLevelMap`/`compat` in the server-side projection only where needed
   for governed custom models. Do not expose secret or endpoint-specific data.
5. Add all-provider parity tests: every canonical pi-ai provider/model appears
   exactly once, all canonical fields match, custom overlays are identified,
   and stale/deleted upstream models cannot survive unnoticed.

**Gate:** clean `npm ci` on both bundled surfaces, generator `--check` is a
no-op, provenance tests pass, 0.85.1 field-set diff is reviewed, and catalog API
tests prove canonical plus custom counts without hard-coding a count as the
sole oracle.

**Rollback:** restore four manifests/lockfiles and the prior generated catalog;
run `npm ci` in both surfaces. No state migration.

### W2 — Implement the canonical capability resolver

**Purpose:** remove hand-maintained builtin knowledge from the worker.

1. In `pi-runtime/src/provider.mjs`, introduce a pure resolver that:
   - performs one exact, guarded `getBuiltinModel(pi_provider, model)` lookup;
   - starts from the complete reviewed builtin record on a hit;
   - applies the authority/merge table field by field;
   - returns the effective model plus the content-free receipt;
   - invokes a separately exported legacy/custom fallback only on no hit.
2. Preserve endpoint-specific provider ID, base URL, auth, contract pricing,
   and stricter limits while inheriting pi-ai wire semantics. Reject unexplained
   builtin API/`provider_kind` mismatches with a typed error before network I/O.
3. Collapse builtin Codex/DeepSeek/Qwen/Zai lists out of the primary resolver.
   Retain only custom-model exceptions that have explicit catalog provenance
   and a wire fixture. Keep the existing custom OpenAI compatibility safety
   overlay, merged after the pi-ai record so it can only make the transport
   safer.
4. Pass `thinkingLevelMap` on the actual model. Validate every requested Pi
   thinking level with pi-ai's own supported-level/clamping behavior; do not
   pre-map provider strings in Python or the frontend.
5. Emit typed, content-free resolution telemetry. Missing builtin, transport
   mismatch, rejected level, and applied fallback must be observable and must
   never be silently reported as canonical inheritance.

**Gate:** payload-capture tests prove pi-ai output for Codex Luna/Terra, Zai
GLM-5.3/Flash, DeepSeek, and Qwen; the entire unknown/proxy fixture corpus is
byte-identical to W0; no network is called by tests.

**Rollback:** revert the resolver/provider test diff and restore the W1 pin if
the incompatibility is upstream-specific. No persisted state changes.

### W3 — Carry capabilities through backend admission and user surfaces

**Purpose:** eliminate data loss between catalog selection and worker binding.

1. Extend `PiApiEndpoint` and `ResolvedPiEndpoint` only with the minimal
   non-secret canonical identity/restriction fields needed at bind time. Do not
   accept arbitrary client-supplied `compat` dictionaries as runtime authority.
2. Make `endpoint_policy.py` resolve catalog data server-side and validate the
   builtin wire adapter. Preserve explicit false values, narrower limits, and
   custom overlay provenance across POST and sparse PUT. Existing endpoints
   remain readable and are re-resolved at bind time so a package bump does not
   require hand-editing every endpoint.
3. Update `_bind_payload()` to forward the effective advertised restrictions,
   including the currently lost vision/input signal, while still excluding
   auth metadata and all other secrets.
4. Keep Settings and Chat structure unchanged. Supply standard Pi effort levels
   in canonical order, reset an invalid saved level to `server_default`, and
   render loading/error/empty/fallback provenance honestly. A fallback model
   must not be labeled provider-native.
5. Preserve authorization: endpoint mutation remains admin-only; project chat
   catalog access remains project-scoped; identity views remain secret-free.

**Gate:** an end-to-end deterministic test traces catalog selection → endpoint
POST/PUT → config → resolver → bind frame → worker effective model. Frontend
unit tests prove effort choices, configured identity, fallback labels, state
reset, and no layout/API regression.

**Rollback:** revert schema/bind/frontend changes together. Because added
configuration fields have defaults and no database migration, old serialized
endpoint settings remain valid.

### W4 — Prove provider conformance, security, and Research Spine invariants

**Purpose:** turn compatibility into an update gate, not a collection of spot
tests.

1. Build a table-driven conformance matrix over every pi-ai API adapter used by
configured/catalog models and focused exemplars for:
   - Codex reasoning and SSE identity transport;
   - Zai thinking object plus reasoning effort;
   - DeepSeek forced-tool thinking control;
   - Qwen/DashScope `enable_thinking` without unsupported effort fields;
   - vision/input, max-token field, developer role, headers, sampling defaults,
     cost tiers, timeout/retry, structured tools, cancellation, usage, and typed
     provider errors.
2. Differentially compare W0 and 0.85.1 wire payloads. Every difference is
   classified `intended-upstream`, `Istara-fix`, or `blocked`; an unclassified
   diff fails the gate.
3. Run chat, validation, ensemble, autoresearch, donated-compute, and model
   management tests identified by CF impact. Prove distinct endpoint/model
   identity, project scope, route evidence, cumulative budgets, independent
   coding/reconciliation, provisional status, and human Done/report gates.
4. Run the security benchmark. Update `security/control_matrix.json`,
   `security/SECURITY_BENCHMARK.md`, and its tests only if the control,
   evidence path, standard version, or trigger pattern actually changes.
5. Extend feature docs and test history because the compatibility/update
   contract changes even though the visible menu structure does not.

**Gate:** no regression against the clean baseline; every conformance row has
model record, normalized payload, effective receipt, and expected typed result.
The security scorecard and Research Spine evidence are attached to CF.

### W5 — Container-first user journeys

**Purpose:** verify the behavior as users encounter it, without requiring live
credentials.

1. Extend scenarios 10, 26, and 36 or add one focused registered scenario that
   uses real browser actions to open Settings, select a canonical model, inspect
   its effort levels, open Chat, select the configured endpoint, change effort,
   and observe fallback/error state. API-behind-browser setup is labeled.
2. Cover admin/researcher/viewer/stranger, light/dark, 375 px reflow, keyboard
   Tab and visible focus, loading/error/empty, canonical hit, and custom
   fallback. Use synthetic endpoints and captured local provider responses;
   never golden research data or real credentials.
3. Register the scenario and coverage matrix, record a dated verdict with
   screenshot/HAR paths, and use only the loopback `docker-compose.qa.yml`
   `ui` profile. Extend the real-user model-management probes and Research
   Spine probes for model-source receipts and fail-closed `not_runnable` live
   requirements.

**Gate:** static harness checks and the focused container journey pass; any
unavailable live dependency is explicit `not_runnable`, never skipped or
fabricated. The full UI suite runs only with the required explicit service
permission.

### W6 — Bounded live acceptance and release

**Purpose:** prove actual provider observation without converting a healthy
process into deployment evidence.

1. After explicit live-model permission, rebuild the QA artifact from the
   candidate SHA. Probe one configured target at a time; never load multiple
   heavy models. Use fresh turns for Luna, Terra, and Zai GLM, a bounded token
   ceiling, a declared cost ceiling, and secret-free raw artifacts.
2. For each turn, reconcile requested Pi level, effective receipt, provider
   wire payload, served provider/model identity, usage envelope, and terminal
   response. Specifically measure rather than assume how 0.85.1 maps Codex
   `minimal`/`low`, and prove Zai's `low` behavior. Environmental quota failure
   is `not_runnable`, not a compatibility pass.
3. Run the offline Pi benchmark suite. Run any live benchmark only through its
   immutable manifest, owner-approved budget ledger, exact DUT identity, and
   safe-stop/resume protocol.
4. Independent blind review measures catalog parity, fallback payload parity,
   provider wire behavior, UI journey, security scorecard, Research Spine
   gates, artifact SHA, and running container identity before reading
   implementer claims.
5. Update `TESTING.md` only if topology changed, update
   `testing/TEST_HISTORY.md` with dated release evidence, and document the
   repeatable Pi update/regeneration procedure.

**Release gate:** deterministic acceptance is green, live acceptance is passed
or explicitly owner-waived with `not_runnable` evidence, the intended image and
SHA are running, rollback is retained, and the requested behavior is verified
through the UI and worker receipts. Promotion is not equivalent to live proof.

## 6. Task graph

| Task | Depends on | Deliverable | Blocks on failure |
| --- | --- | --- | --- |
| A0 expanded CF spec + baseline/fallback freeze | winning-plan owner approval | accepted spec, task DAG, W0 fixtures | all implementation |
| A1 exact 0.85.1 pins + deterministic catalog generator | A0 | manifests, lockfiles, generator/check, provenance, overlay | A2, A3 |
| A2 runtime capability resolver | A1 | canonical/fallback resolver, typed receipts, payload tests | A3, A4 |
| A3 backend bind + frontend projection | A1, A2 | lossless non-secret capability flow and unchanged menus | A4, A5 |
| A4 conformance/security/Research Spine verification | A2, A3 | differential matrix, scorecards, invariant tests | A5, A6 |
| A5 container user journeys | A3, A4 | scenario, coverage map, dated UI evidence | A6 |
| A6 bounded live/release acceptance | A4, A5, explicit permission | live receipts, benchmark, blind review, docs | ship |

No task may be declared complete from a package install, passing process, HTTP
200, configured label, or non-empty response alone.

## 7. Acceptance matrix

| Given / when | Then | Proof |
| --- | --- | --- |
| Exact builtin `(pi_provider, model)` resolves | Effective model uses pi-ai `api`, `reasoning`, `thinkingLevelMap`, `compat`, and reviewed ancillary fields; explicit catalog restrictions win | normalized-record assertion + provider payload capture |
| Catalog explicitly says non-reasoning/non-vision | Runtime does not re-enable the capability | config→bind→worker integration test |
| Builtin and configured transport disagree | Typed pre-network rejection, unless a named governed proxy fixture authorizes it | negative unit/API test; zero fetch calls |
| Model is absent from pi-ai | Named fallback path produces W0-equivalent normalized model and byte-identical wire payload | differential fixture for DashScope/proxy/unknown |
| 0.85.1 is installed from a clean checkout | Both bundled surfaces resolve exact lockstep pins and generated catalog/provenance matches package registry | `npm ci`, provenance and generator-check tests |
| User opens model controls | Standard Pi effort levels are accurate, ordered, accessible, and an invalid saved level falls back honestly | Vitest + Playwright desktop/mobile/theme/keyboard matrix |
| Fresh bounded Luna/Terra/Zai turn runs | Requested level, pi-ai mapping, provider-observed behavior, served identity, and usage agree | secret-free live payload/receipt/usage bundle |
| Research workflow uses affected route | Evidence units, distinct model identity, reliability/reconciliation, project route evidence, human review, and Done/report gates remain non-bypassable | targeted Research Spine and donor/ensemble tests |
| Future Pi version is proposed | Version/field/catalog/wire diffs are generated mechanically; unclassified changes fail before release | documented update command + `--check` + differential suite |

## 8. Exact verification ladder

Run from the repository root unless a subshell changes directory. Record every
result and artifact path as CF command evidence.

### Per-wave deterministic checks

```bash
(cd pi-runtime && npm ci && npm test)
(cd labs/pi-replacement && npm ci && npm run validate)
pytest -q tests/pi_migration/test_version_provenance.py \
  tests/pi_production/test_pi_catalog_ux.py \
  tests/pi_production/test_runtime_hardening.py \
  tests/pi_production/test_w1_dispatcher_authority.py \
  tests/pi_production/test_w7_pi_manager_integration.py \
  tests/pi_production/test_research_spine_donor_routing.py \
  tests/pi_production/test_engine_http_provider.py
pytest -q tests/pi_benchmark/
(cd frontend && npm run test:unit && npx tsc --noEmit && npm run lint)
(cd tests/simulation && npm run test:static)
npm --prefix tests/real_user_benchmark run check
python scripts/check_test_harness.py
python scripts/check_integrity.py
python scripts/security_benchmark.py --fail-on-threshold
```

Add the generator's final supported command to this ladder, with both write and
drift modes, for example:

```bash
node pi-runtime/scripts/generate-istara-catalog.mjs
node pi-runtime/scripts/generate-istara-catalog.mjs --check
```

The implementation plan must settle the filename before creating tasks; tests
and docs invoke the same entry point.

### Change/release gates

```bash
python scripts/check_feature_obligations.py \
  --base origin/testing --head HEAD \
  --json-out artifacts/feature-obligations.json
python scripts/check_change_obligations.py --base origin/testing --head HEAD
python scripts/feature_docs.py --seed-missing --generate-site --check
pytest -q tests/test_feature_docs.py tests/test_security_benchmark.py
docker compose -f docker-compose.qa.yml --profile contract config --quiet
```

The feature-obligation report determines any additional deterministic suites;
unknown paths fail closed. Compare broad-suite failures with a clean checkout
at the same base SHA and separate inherited debt from regressions.

### User journey and live gates

These commands are not authorized by this planning stage. Run them only after
the required service/model permission and container setup:

```bash
(cd tests/simulation && node run.mjs --scenarios 10,26,36,<new-id> --engine pi)
npm --prefix tests/real_user_benchmark run probe:pi
```

The final live T1 command must name one configured endpoint, token/cost ceiling,
artifact directory, candidate SHA, and expected provider/model. Do not encode a
private URL or token in the command or committed files. Execute endpoints
sequentially and preserve the safe-stop/resume artifact after each one.

## 9. Update procedure after this delivery

Every future Pi upgrade follows the same maintenance transaction:

1. propose exact lockstep versions and verify package integrity;
2. regenerate catalog and provenance from a clean install;
3. review provider/model additions, removals, model-field-set changes, and auth
   policy separately;
4. run normalized model-record and wire differential tests;
5. classify every change and update governed custom overlays explicitly;
6. run deterministic, security, Research Spine, and container UI gates;
7. perform bounded live probes only where the diff affects an active provider;
8. retain the previous pins, catalog, image digest, and resume instructions
   until acceptance closes.

This makes a bump mechanical while keeping new upstream semantics visible and
reviewable rather than silently inheriting an unknown security or wire change.

## 10. Risks and mitigations

| Risk | Mitigation / fail-closed behavior |
| --- | --- |
| Upstream record is missing or renamed | Exact lookup only; explicit fallback receipt; catalog diff blocks silent deletion. |
| Full-record inheritance introduces a new field | Model-field-set hash/diff must be classified before the pin advances. |
| Endpoint wire adapter conflicts with builtin API | Validate before network; require named proxy exception plus fixture. |
| Catalog becomes a stale second authority | Generated projection, provenance manifest, `--check`, and all-record parity; runtime still looks up pi-ai directly. |
| Custom DashScope behavior is lost | Separate governed overlay and frozen byte-level fallback fixtures. |
| Capability false/null is collapsed | Preserve tri-state values end to end and test sparse PUT plus bind serialization. |
| Contract cost is overwritten by list price | Operator rates always override; spent unpriced categories fail closed. |
| Telemetry leaks endpoint/server identity | Fixed content-free receipt allowlist; secret/URL/header negative tests. |
| Compatibility change bypasses Research Spine | Route/evidence/independence/reconciliation/Done probes are mandatory before ship. |
| Live check loads too many models or spends without approval | Explicit permission, one endpoint at a time, hard token/cost limits, immutable budget/resume ledger. |
| Shared worktree contains unrelated changes | Isolate wave paths/commits, compare against the selected base, never stage ambient edits. |
| CF `.mjs` impact remains low confidence | Record the limitation; require direct import/call-site inventory and Node test ownership. Never use legacy CF fallback. |

## 11. Rollback and terminal states

The compatibility change has no database migration. Rollback restores the
previous package manifests/lockfiles, generated catalog/provenance, resolver,
backend capability fields, and frontend projection as one tested revert, then
runs clean `npm ci` in both bundled surfaces and the fallback fixture suite.
The previously accepted image/digest remains available until live acceptance.

Allowed terminal states are explicit:

- **deterministic complete, live pending** — all offline/container gates pass;
  no claim of provider behavior;
- **not_runnable** — missing permission, quota, credential, or provider; exact
  blocker and resume command recorded;
- **rolled back** — prior pins/image restored and baseline reverified;
- **accepted** — deterministic, UI, security, Research Spine, artifact identity,
  and required live evidence all reconcile; owner approves promotion.

The conductor must stop at the synthesized winning-plan owner-approval gate.
This independent draft neither selects itself nor authorizes W0 execution.
