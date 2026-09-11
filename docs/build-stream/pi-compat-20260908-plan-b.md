# Plan B — Pi Compatibility Authority and the Istara Integration Boundary

**Slot:** b · **Task:** `pi-compat-20260908-PLAN-B` · **Spec:** CF-SPEC-29
**Phase:** S1 draft (independent) · **Lifecycle:** `docs/build-stream/2026-09-08-pi-capability-inheritance.md`
**Author route:** claude-opus-5 @ effort=high · **Written:** 2026-09-08

---

## 1. Thesis

The lifecycle file frames this as *duplication*: Istara re-states knowledge pi-ai
already ships. That framing is correct but too gentle. My measurements show the
duplicated knowledge is not merely redundant — **it is wrong, it is wrong in the
direction of silent degradation, and the test suite currently pins the wrong
behavior as correct.**

Three independent proofs (§3):

- **A Codex endpoint cannot reach `xhigh` or `max`.** `provider.mjs` declares
  `thinkingLevels: ["xhigh","max","minimal"]`, but **`thinkingLevels` is a dead
  field** — it appears nowhere in pi-ai 0.84.3 or pi-agent-core 0.84.3. pi-ai
  reads `thinkingLevelMap`. With no map, `getSupportedThinkingLevels` excludes
  `xhigh`/`max`, so both clamp to `high`. The declaration is inverted, not
  redundant.
- **A Z.AI endpoint never sends `reasoning_effort` at all.** Captured wire
  payloads show the field absent at every requested level; pi-ai's own registry
  record for `glm-5.3` carries `supportsReasoningEffort: true` and sends
  `low`/`high`/`max`. `pi-runtime/test/provider-params.test.mjs:206` asserts the
  absence **as the expected result**.
- **Every catalog-selected Z.AI model fails budgeted runs closed.** All five zai
  entries in the backend mirror are priced `{0,0,0,0}` while pi-ai prices
  `glm-4.7` at `0.6/2.2/0.11`. `session.mjs` fails a budgeted run with
  `cost_budget_unpriced` when any used category is $0-rated. Mirror drift is a
  **budget-integrity and availability defect**, not menu cosmetics.

So the real problem is not "we should inherit more." It is that **Istara has no
authority model**: no rule says which layer owns which field, no mechanism
derives the mirror from upstream, and no test detects divergence. Adding a
`getBuiltinModel()` call at bind time — the obvious fix, and the one the
lifecycle's Phase 1 describes — repairs the worker and leaves the menus, the
cost ceiling, and the catalog validator still reading a hand-maintained file
that is wrong for 976 of 1,307 models.

**This plan installs the authority model and one generated seam that serves all
four consumers at once**, then bumps the pin behind a conformance test that
makes the next bump routine.

---

## 2. The authority model (the core architectural contribution)

### 2.1 Three kinds of knowledge, three owners

| Knowledge | Owner | Why | Where it lives after this plan |
|---|---|---|---|
| **Model semantics** — reasoning support, `thinkingLevelMap`, `compat` flags, context/output limits, list prices | **pi-ai** (upstream) | Generated from provider docs, versioned with the release, changes when providers change | Generated projection: `backend/app/core/pi_runtime/data/pi_models_catalog.json` |
| **Deployment identity** — which provider a base URL actually is, governed non-pi providers (`dashscope`), operator contract pricing, per-endpoint caps | **Istara catalog / operator** | pi-ai cannot know a gateway URL's true provider or an operator's negotiated rate | `catalog.py` custom-provider snapshots + endpoint records |
| **Per-binding overrides** — `supports_reasoning: false` on a model an operator knows is degraded, endpoint `max_tokens`, `timeout_ms` | **The endpoint** | Deployment reality beats both | `PiApiEndpoint` fields, already present |

### 2.2 The precedence law (per field, not per record)

```
1. Endpoint explicit override        (operator knows their deployment)
2. Generated pi-ai capability record (upstream authority for (provider, model))
3. Istara identity fallback switch   (governed/custom providers; gateway URLs)
4. pi-ai detectCompat() URL sniffing (unchanged last resort)
```

Today's effective order is **1 → 3 → 4 with tier 2 entirely missing.** Inserting
tier 2 is the whole change. It is strictly additive: any `(pi_provider, model)`
pair pi-ai does not know keeps today's byte-identical behavior, which is why the
fallback payload-diff acceptance in §7 can demand *byte equality*.

Per-field merge, never per-record replacement. pi-ai's own `getCompat()` already
merges `model.compat` over `detectCompat()` field by field; our tier-1/tier-2
merge mirrors that discipline so an operator can veto exactly one flag without
discarding the rest of the upstream record.

### 2.3 Where the authority is read — once, not per turn

The tempting design is `import("@earendil-works/pi-ai/providers/all")` inside
`buildRealProvider`. I reject it, measured:

- `providers/all` costs **67 ms and ~60 MB RSS** to import (measured, §3 B-E6).
  The worker is a supervised per-session process; that is a per-session tax for
  data that changes only when the pin changes.
- It fixes only the worker. The **frontend effort menu**
  (`ChatModelControls.tsx:37`), the **cost ceiling** (`endpoint_policy.py:54-58`
  → `engine.py:163` → `session.mjs:632`), and the **catalog validator**
  (`endpoint_policy.py:33`) all read the mirror, and would stay wrong.
- It would break the deliberate invariant recorded as E3 — *"backend never
  imports pi-ai by design"* — or force the backend to shell out to Node per
  request.

**So the authority is read at maintenance time by a generator, and the generated
artifact is the single seam every consumer reads.** One read point, four fixed
consumers, zero runtime cost, invariant preserved.

---

## 3. Measured evidence (all commands re-runnable from the repo)

Environment: `pi-runtime/node_modules`, `@earendil-works/pi-ai@0.84.3`,
`@earendil-works/pi-agent-core@0.84.3`, node v26. Registry `generatedAt`
`1787569009141`.

**B-E1 — `thinkingLevels` is a dead field.**
`grep -rn "thinkingLevels" node_modules/@earendil-works/{pi-ai,pi-agent-core}/dist/`
returns **zero** references outside `getSupportedThinkingLevels`'s own body.
pi-ai's `Model` type (`dist/types.d.ts:706`) declares `thinkingLevelMap`, not
`thinkingLevels`.

**B-E2 — Codex capability is inverted, and Codex `compat` is dropped.**
Comparing the model `provider.mjs` builds against `getBuiltinModel("openai-codex","gpt-5.6-luna")`:

| requested | Istara clamp → wire | pi-ai clamp → wire |
|---|---|---|
| `minimal` | `minimal` → `minimal` | `minimal` → **`low`** |
| `xhigh` | **`high` → `high`** | `xhigh` → `xhigh` |
| `max` | **`high` → `high`** | `max` → `max` |
| off/low/medium/high | identical | identical |

Also dropped: `supportsOpenAIGrammarTools: true`, `supportsAdditionalTools: true`,
`supportsToolSearch: true`. `openai-codex-responses.js:376-380` selects
`deferredToolsMode` from those flags, so tool encoding differs structurally, not
just in effort.

**B-E3 — Z.AI sends no `reasoning_effort`, proven at the wire.** Captured request
bodies (stub fetch, real adapter), `zai/glm-5.3` at `https://api.z.ai/api/coding/paas/v4`:

```
istara   : {... "thinking":{"type":"enabled","clear_thinking":false}}
inherited: {... "thinking":{"type":"enabled","clear_thinking":false}, "reasoning_effort":"low"}
```

Divergence at `low`→`low`, `high`→`high`, `max`→`max`, `medium`→`high`. Root
cause: `detectCompat()` (`openai-completions.js:1244`) computes
`supportsReasoningEffort: !isZai` = **false**, while pi-ai's *registry record*
for `glm-5.3` sets it **true**. `provider.mjs:513-518` and its test at
`provider-params.test.mjs:192-205` both name URL detection as the authority.
That is the specific reasoning error: **detection is a fallback for unknown
models, not the authority for known ones.**

**B-E4 — Mirror drift, quantified.** Mirror (40 providers / 1,307 models) vs
installed registry (39 / 1,312):

| Divergence | Count |
|---|---|
| Registry models absent from mirror | **81** |
| Mirror models absent from registry (stale) | **36** |
| Wrong `thinkingLevels` | **976 / 1,307 (74.7%)** |
| `contextWindow` mismatches | **20** |
| Cost-field mismatches | **188** — 21 zero-in-mirror, 63 under-priced, 104 over-priced |
| `reasoning` boolean mismatches | 0 |

**B-E5 — The mirror's `thinkingLevels` is the wrong quantity.** For 959 of 1,231
shared models it equals the *non-null keys of `thinkingLevelMap`*, not the
supported-level set. `getSupportedThinkingLevels` returns the full ladder minus
explicit `null`s. So `anthropic.claude-opus-4-7` offers the user
`["xhigh","max"]` when pi-ai supports `off,minimal,low,medium,high,xhigh,max`.
The remaining 272 follow *other* rules — evidence the file was produced by
different ad-hoc scripts at different times. **There is no generator in the
repo**: `grep -rln "pi_models_catalog\|models.generated" scripts backend tests`
finds only the consumer and a doc.

**B-E6 — Budget integrity.** All five `zai` mirror entries are
`{input:0,output:0,cacheRead:0,cacheWrite:0}`; pi-ai prices `glm-4.7` at
`0.6/2.2/0.11`. `session.mjs:536-541` fails a budgeted run `cost_budget_unpriced`
when a used category is $0-rated. **Every budgeted run on a catalog-selected zai
endpoint fails closed today.** Symmetrically, 63 under-priced fields let a
ceiling under-count real spend.

**B-E7 — Import cost of the naive design.** `import("@earendil-works/pi-ai/providers/all")`
= 67.2 ms, 60.4 MB RSS, 39 providers / 1,312 models eagerly constructed.

**B-E8 — No effort/thinking coverage in the UI suite.** `grep -rn "effort\|thinking"`
across `10-settings-models.mjs`, `05-chat-interaction.mjs`,
`26-model-session-persistence.mjs` returns **nothing**. The AGENTS.md *Full UI
Testing Suite Contract* is unmet for the entire effort-selection journey.

**B-E9 — Effort validation has no capability check.** `normalize_model_effort`
(`llm_thinking.py:25-40`) accepts any `[a-z][a-z0-9_]{0,31}` token. `thinking_mode:"banana"`
passes the API validator, reaches the worker, and `clampThinkingLevel` silently
returns the lowest supported level. No allowlist against pi-ai's `ThinkingLevel`
enum, no per-model check.

**B-E10 — Baseline green.** `cd pi-runtime && npm test` → **54 pass / 0 fail**, 8.4 s.

### 3.1 Corrections to the lifecycle's recorded evidence

Recording these because a plan built on them would mis-target work.

| Lifecycle claim | Measured |
|---|---|
| E1: "39 providers via `getBuiltinProviders()`" | True, but the symbol is exported from **`@earendil-works/pi-ai/providers/all`**, not the package root. The root exports only `clampThinkingLevel`, `getSupportedThinkingLevels`, `modelsAreEqual` (46 exports total). |
| E1: "codex luna carries `{xhigh,max,minimal:"low"}`; our codex list loses the `low→minimal` mapping" | The map is `minimal→"low"` (not `low→minimal`), and the loss is **not** the headline: `xhigh`/`max` silently clamp to `high` (B-E2). |
| E2: "`glm-5.3-flash` absent [from mirror], installed 0.84.3 has both" | **`glm-5.3-flash` exists in neither** the mirror nor pi-ai 0.84.3. The zai registry is `glm-4.7, glm-5-turbo, glm-5.2, glm-5.2-highspeed, glm-5.3`. `provider-params.test.mjs:206` builds a binding for this non-existent id. |
| E2: mirror lag "degrades menus via full-list fallback" | Understated. It also breaks the **cost ceiling** (B-E6) and produces wrong menus for 976 models via a wrong *definition*, not just staleness (B-E5). |
| E5: "effort reporting fixed in SPEC-26 … live proof pending rebuild" | The *reporting* side was fixed. B-E3 shows the **transmit** side is still broken for zai. A live re-probe on zai will show no effort differentiation regardless of rebuild. |

---

## 4. The complete compatibility surface

Discovered by tracing the chain end to end, not by taking the lifecycle's list.

```
pi-ai registry (models.generated.js, 39 providers / 1312 models)
      │  [W1] generator: pi-runtime/scripts/emit-catalog.mjs
      ▼
backend/app/core/pi_runtime/data/pi_models_catalog.json   ← generated projection + provenance
      │
      ├─► catalog.py            load_catalog / pi_catalog_json      → Settings UI
      ├─► endpoint_policy.py    _apply_catalog_fields               → endpoint record + cost rates
      │        │
      │        ▼
      │   PiApiEndpoint {pi_provider, model, supports_reasoning, supports_vision,
      │                  context_window, max_tokens, cost_*_per_mtok}   ← [W2] + capability{}
      │        │
      │        ▼  engine.py:140-171 _bind_payload
      │   provider.bind frame ──────────────────────────────────────────┐
      │                                                                 ▼
      ├─► settings.py /api/settings/pi/catalog ──► frontend/src/lib/modelCatalog.ts
      │                                            ├─ ChatModelControls.tsx:37 effort menu
      │                                            └─ PiModelManagement.tsx:596 badge
      │                                                                 │
      └─► frontend thinking_mode ──► chat.py validate_model_effort ─────┤ [W4]
                                                                        ▼
                                        pi-runtime provider.mjs modelCapabilities()  [W2]
                                                                        │
                                                    pi-ai model {reasoning, thinkingLevelMap, compat}
                                                                        │
                                            openai-completions / anthropic-messages /
                                            openai-codex-responses  → wire payload
                                                                        │
                                                     session.mjs cost ceiling  [W1 fixes rates]
                                                     usage_ledger / telemetry   [W4]
```

Also in the surface, and covered:

- **`labs/pi-replacement`** — a second bundled pi surface pinned to the same
  versions; `tests/pi_migration/test_version_provenance.py` asserts both. Any
  bump must move both lockfiles or that test fails. *(The lifecycle's rollback
  section names only `provider.mjs` + `package.json`; it misses this surface.)*
- **`embeddings_gateway.py` / `embedding_profile.py`** — separate pi surface with
  its own model assumptions; in scope for a read-only conformance check (W3), not
  for change.
- **`oauth.py`** (820 lines) — mirrors pi-ai's `auth/oauth/load.js` flows;
  `catalog.py`'s `_OAUTH_PROVIDERS`/`_API_KEY_PROVIDERS` hand-list 39 providers'
  env vars and flows. pi-ai's `builtinProviders()` exposes `provider.auth` with
  `{apiKey:{name}}` / `{oauth:{name,isSubscription}}`. **This is a second
  duplication of the same class** — deliberately deferred, see §10.

---

## 5. Design

### 5.1 W1 — The generator and the generated projection

**New:** `pi-runtime/scripts/emit-catalog.mjs` (node, dev-only, imports pi-ai).
**New:** `scripts/generate_pi_catalog.py` (thin operator entry point; invokes the
node emitter, writes the JSON, prints a diff summary).

The emitter walks `getBuiltinProviders()` → `getBuiltinModels(p)` and emits per
model, verbatim from the record:

```jsonc
{
  "id": "glm-5.3", "name": "GLM-5.3", "api": "openai-completions",
  "baseUrl": "...", "contextWindow": 1000000, "maxTokens": 131072,
  "reasoning": true, "input": ["text"], "cost": {...},
  "thinkingLevels": ["low","high","max"],        // getSupportedThinkingLevels(record) — pi-ai computes it
  "thinkingLevelMap": {"off":null,...,"max":"max"},  // NEW — the authority field
  "compat": {"supportsReasoningEffort":true, "thinkingFormat":"zai", ...}  // NEW — verbatim
}
```

Plus a **provenance header** the file does not have today:

```jsonc
"__provenance": {
  "pi_ai_version": "0.84.3",
  "pi_ai_generated_at": 1787569009141,
  "emitted_at": "<utc>",
  "emitter_sha256": "<sha256 of emit-catalog.mjs>",
  "governed_custom_providers": ["dashscope"]
}
```

**Governed custom providers are preserved, not regenerated.** `dashscope` (40
models, absent from pi-ai) moves to
`backend/app/core/pi_runtime/data/custom_providers/dashscope.json`, hand-owned
and merged by the emitter. This makes the boundary between "upstream truth" and
"Istara's governed addition" a file boundary instead of an invisible convention
— and stops a future regeneration from deleting it.

`thinkingLevels` is retained and now **correct**, so no frontend change is needed
for the 976-model menu fix. `catalog.py`'s `PiCatalogModel` gains
`thinkingLevelMap` and `compat` as optional fields.

Measured cost: mirror grows **544 KB → 892 KB (+63.9%)**, 27,977 → 39,407 lines.
Accepted for auditability; §9 R4 records the slimmer alternative and why not.

### 5.2 W2 — The capability descriptor crosses the boundary

`endpoint_policy._apply_catalog_fields` already reads the matched catalog record.
It gains:

```python
payload["capability"] = {
    "reasoning": bool(match["reasoning"]),
    "thinking_level_map": match.get("thinkingLevelMap"),
    "compat": match.get("compat"),
    "source": f"pi-ai@{provenance['pi_ai_version']}",   # or "istara-custom"
}
```

`PiApiEndpoint` gains `capability: dict | None`. `engine._bind_payload` forwards
it. Nothing else in the backend interprets it — the backend stays a **courier**,
which is the point: it needs no pi-ai import and no capability logic.

In `provider.mjs`, `modelCapabilities(endpoint, modelApi)` becomes tier-ordered:

```js
export function modelCapabilities(endpoint, modelApi) {
  const inherited = validateCapabilityDescriptor(endpoint?.capability);  // NEW, throws on bad shape
  if (inherited) {
    const advertised = endpoint?.supports_reasoning;                     // tier 1 vetoes tier 2
    const reasoning = advertised == null ? inherited.reasoning : Boolean(advertised);
    return {
      reasoning,
      thinkingLevelMap: reasoning ? inherited.thinkingLevelMap : undefined,
      compat: reasoning ? inherited.compat : stripThinking(inherited.compat),
    };
  }
  return legacyIdentityCapabilities(endpoint, modelApi);   // tiers 3+4, moved verbatim
}
```

`buildRealProvider` sets `thinkingLevelMap` on the model and **stops setting the
dead `thinkingLevels`** (B-E1). `validateCapabilityDescriptor` rejects unknown
keys the way `mapProviderParams` does, so a malformed descriptor fails the bind
loudly instead of silently reverting to the fallback.

`isCustomOpenAICompat` (the `supportsDeveloperRole:false` rule) still applies as
a **tier-3 default under** tier 2: if the inherited `compat` names
`supportsDeveloperRole`, the inherited value wins; otherwise the URL rule fills
it. This preserves the DashScope/DeepSeek `developer`-role fix exactly.

### 5.3 W3 — Conformance: make drift impossible to merge

**New:** `tests/pi_compat/test_catalog_conformance.py` — regenerates the catalog
in a temp dir (subprocess to the node emitter) and asserts the committed file is
**byte-identical**, plus asserts `__provenance.pi_ai_version` equals the pin in
`pi-runtime/package.json`. Skips with a typed `not_runnable` (never a silent
skip, per AGENTS.md) when `pi-runtime/node_modules` is absent.

**New:** `pi-runtime/test/capability-inheritance.test.mjs` — a table-driven
**wire-payload diff** harness (the `.tmp-arch-b/wirediff.mjs` prototype,
productionised): for each `(provider, model, level)` case it captures the real
request body through a stub fetch and asserts it against a committed fixture.
Two fixture classes:

- **inherited** — zai/deepseek/qwen/codex/anthropic: asserts the *corrected*
  payload (this is where `provider-params.test.mjs:206` gets flipped, with the
  flip and its justification named in the commit).
- **fallback** — dashscope, an unknown proxy base URL, a legacy binding with no
  `capability`: asserts **byte equality with a fixture captured on the current
  code before W2 lands**. This is the acceptance criterion that proves the change
  is additive.

Capture the fallback fixtures in W0 (below) so they are pre-change ground truth.

### 5.4 W4 — Observability, validation, and the user journey

- `validate_model_effort` gains an allowlist against pi-ai's ladder
  (`off|minimal|low|medium|high|xhigh|max` + `server_default`), rejecting anything
  else with `unsupported_model_effort` instead of silently clamping (B-E9).
- The bind emits one telemetry field, `capability_source` ∈
  `{pi-ai@<ver>, istara-custom, fallback-identity, fallback-detection}`, on the
  existing `pi_provider_turn` span (`engine.py:623`). This is the single
  observable that answers "which tier served this turn?" — today unanswerable.
- When a requested level is clamped, emit `effort_clamped{requested, served}`
  rather than degrading silently. *"Never silent wrongness"* is already the
  lifecycle's stated principle; this makes it enforceable.
- **UI suite (AGENTS.md contract):** extend `10-settings-models.mjs` (the effort
  badge reflects the model's real level count) and `05-chat-interaction.mjs`
  (open the effort menu, select a non-default level, send, assert the session
  persists it) — real browser acts, light/dark, 375 px reflow, keyboard Tab with
  visible focus, synthetic data only. Register verdicts in
  `tests/simulation/lib/scenario-registry.mjs`. This closes B-E8.

### 5.5 W5 — The version bump, behind the conformance gate

Only now is `0.84.3 → 0.85.1` safe, because W3 makes its effect *visible*:
`npm i` → regenerate → the catalog diff **is** the compatibility report, and the
payload fixtures show every wire change. Both surfaces (`pi-runtime` and
`labs/pi-replacement`) move together; `EXPECTED_PINS` in
`tests/pi_migration/test_version_provenance.py` moves with them.

**W5 is the one wave I recommend the owner may defer.** W1–W4 are corrections to
present-tense defects on the pinned version; W5 is new adoption. They are cleanly
separable, and separating them means the 0.85.1 diff is reviewed against a
*correct* baseline rather than a broken one.

### 5.6 The routine-bump contract (the actual goal)

After this plan, a pi version bump is:

```bash
cd pi-runtime && npm i @earendil-works/pi-ai@X @earendil-works/pi-agent-core@X
cd ../labs/pi-replacement && npm i @earendil-works/pi-ai@X @earendil-works/pi-agent-core@X
python scripts/generate_pi_catalog.py            # regenerate; prints the drift summary
git diff --stat backend/app/core/pi_runtime/data/pi_models_catalog.json   # the compatibility report
cd pi-runtime && npm test                        # payload fixtures show every wire change
pytest tests/pi_compat tests/pi_migration -q     # conformance + provenance
# update EXPECTED_PINS, review fixture diffs, ship
```

Five commands and a diff review. That is the deliverable.

---

## 6. Waves and tasks (dependency-ordered)

Strict waves: each completes and passes review before the next starts.

### W0 — Freeze the pre-change baseline *(no product code)*
| # | Task | Files |
|---|---|---|
| 0.1 | Capture fallback wire-payload fixtures on **current** code (dashscope, unknown proxy, legacy no-`capability` binding, deepseek, qwen, codex, zai) | `pi-runtime/test/fixtures/wire/pre-change/*.json` |
| 0.2 | Commit the drift report (B-E4) as a dated artifact | `docs/build-stream/pi-compat-20260908-drift-report.md` |

*Gate:* fixtures exist and are reproducible twice with identical bytes.

### W1 — Generator + generated projection
| # | Task | Files |
|---|---|---|
| 1.1 | `emit-catalog.mjs`: walk registry, emit verbatim `thinkingLevelMap`/`compat`, pi-ai-computed `thinkingLevels`, provenance header | `pi-runtime/scripts/emit-catalog.mjs` |
| 1.2 | Extract `dashscope` to a governed custom-provider file; emitter merges it | `backend/.../data/custom_providers/dashscope.json` |
| 1.3 | Operator entry point + drift summary output | `scripts/generate_pi_catalog.py` |
| 1.4 | Regenerate the mirror; **review the 188 cost + 20 context + 81/36 model diffs as a change, not a rubber stamp** | `backend/.../data/pi_models_catalog.json` |
| 1.5 | `PiCatalogModel` gains `thinkingLevelMap`, `compat`; serializer passes them through | `catalog.py` |
| 1.6 | Conformance test: regenerate ≡ committed; provenance ≡ pin | `tests/pi_compat/test_catalog_conformance.py` |

*Acceptance:* menus correct for all 1,307 models; zai endpoints priced; no
runtime pi-ai import added to the backend.
*Risk gate:* 1.4 changes live pricing. **The cost diff needs owner sign-off** —
104 models get *more expensive* rates, which changes when ceilings trip.

### W2 — Capability descriptor across the boundary
| # | Task | Files |
|---|---|---|
| 2.1 | `capability` on the endpoint record + policy population | `endpoint_policy.py`, `endpoints.py`, `config.py` |
| 2.2 | Forward `capability` in the bind payload | `engine.py` |
| 2.3 | `validateCapabilityDescriptor` (unknown-key rejection) | `pi-runtime/src/provider.mjs` |
| 2.4 | Tier-ordered `modelCapabilities`; set `thinkingLevelMap`, drop dead `thinkingLevels` | `pi-runtime/src/provider.mjs` |
| 2.5 | Preserve `supportsDeveloperRole` URL rule as a tier-3 default under tier 2 | `pi-runtime/src/provider.mjs` |
| 2.6 | Backend contract tests for descriptor population/forwarding | `tests/pi_production/test_engine_http_provider.py` |

*Acceptance:* §7 AC-2, AC-3, AC-4.

### W3 — Conformance and payload fixtures
| # | Task | Files |
|---|---|---|
| 3.1 | Table-driven wire-payload harness | `pi-runtime/test/capability-inheritance.test.mjs` |
| 3.2 | Inherited fixtures (corrected expectations) | `pi-runtime/test/fixtures/wire/inherited/*.json` |
| 3.3 | **Flip** `provider-params.test.mjs:192-235` (zai) and `:121-131` (codex); justify each flip in-file | `pi-runtime/test/provider-params.test.mjs` |
| 3.4 | Fallback fixtures asserted **byte-identical to W0** | `pi-runtime/test/fixtures/wire/pre-change/*` |
| 3.5 | Read-only conformance check that `embeddings_gateway` model assumptions still hold | `tests/pi_production/test_w8_embeddings_gateway.py` |

*Acceptance:* AC-1, AC-5.

### W4 — Observability, validation, UI journey
| # | Task | Files |
|---|---|---|
| 4.1 | Effort allowlist against pi-ai's ladder | `backend/app/core/llm_thinking.py`, `chat.py` |
| 4.2 | `capability_source` on the turn span | `engine.py`, `telemetry.py` |
| 4.3 | `effort_clamped{requested,served}` signal | `provider.mjs`, `session.mjs`, `usage_ledger.py` |
| 4.4 | Settings scenario: effort badge reflects real level count | `tests/simulation/scenarios/10-settings-models.mjs` |
| 4.5 | Chat scenario: select a non-default effort, send, assert persistence — matrix per AGENTS.md | `tests/simulation/scenarios/05-chat-interaction.mjs`, `scenario-registry.mjs` |
| 4.6 | Security benchmark (LLM-provider surface trigger) | `python scripts/security_benchmark.py --fail-on-threshold` |

*Acceptance:* AC-6, AC-7.

### W5 — Version bump *(separable; owner may defer)*
| # | Task | Files |
|---|---|---|
| 5.1 | Bump both surfaces to 0.85.1 + `npm ci` | `pi-runtime/`, `labs/pi-replacement/` |
| 5.2 | Regenerate; **the catalog diff is the compatibility report** | mirror |
| 5.3 | `EXPECTED_PINS` → 0.85.1 | `tests/pi_migration/test_version_provenance.py` |
| 5.4 | Review every fixture diff; any wire change is a finding until justified | fixtures |
| 5.5 | Full suites + benchmark | — |

### W6 — Bounded live re-probe *(owner-authorized only)*
Per AGENTS.md *Live LLM and Model Loading Safety*: **no live probe without
explicit permission**, one configured target at a time. One turn each on
luna / zai-glm / terra at `low`, asserting the usage envelope reports `effort=low`
**and** that the captured request body carried it (B-E3 says today's zai turn
carries nothing — this is the proof point). Container turn logs as evidence.

### W7 — Documentation
`docs/architecture/pi-compatibility-authority.md` (the precedence law, the
generator, the bump runbook), `CHANGELOG.md`, `TESTING.md` only if suite topology
changed (W3 adds a suite file → yes), lifecycle ledger.

---

## 7. Acceptance criteria

- **AC-1 (additive/no-regression).** *Given* an endpoint whose `(pi_provider, model)`
  is absent from the pi-ai registry — dashscope, an unknown proxy URL, or a legacy
  binding with no `capability` — *When* a turn binds at every thinking level
  *Then* the captured request body is **byte-identical** to the W0 pre-change
  fixture. *Verify:* `cd pi-runtime && npm test -- capability-inheritance`.
- **AC-2 (Codex inheritance).** *Given* a Codex endpoint on `gpt-5.6-luna` *When*
  `xhigh` or `max` is requested *Then* the body carries `reasoning.effort` of
  `"xhigh"`/`"max"` (today: `"high"`), `minimal` maps to `"low"`, and
  `compat.supportsAdditionalTools` selects `deferredToolsMode:"additional-tools"`.
- **AC-3 (Z.AI inheritance).** *Given* `zai/glm-5.3` *When* `low`/`high`/`max` is
  requested *Then* the body carries `reasoning_effort` of `"low"`/`"high"`/`"max"`
  (today: field absent) with the `thinking` block unchanged.
- **AC-4 (operator veto).** *Given* an endpoint with `supports_reasoning: false`
  on a model pi-ai marks reasoning-capable *When* a turn binds *Then* no thinking
  or effort field is emitted — tier 1 beats tier 2.
- **AC-5 (conformance).** *Given* a clean tree *When*
  `pytest tests/pi_compat/test_catalog_conformance.py` runs *Then* regenerating
  the catalog reproduces the committed file byte-for-byte and `__provenance.pi_ai_version`
  equals the `package.json` pin. *A bump without regeneration fails CI.*
- **AC-6 (menus and budget).** *Given* the regenerated catalog *When* the effort
  menu renders for `anthropic.claude-opus-4-7` *Then* it offers the seven pi-ai
  levels, not `["xhigh","max"]`; **and** *When* a budgeted run uses a zai endpoint
  *Then* it does not fail `cost_budget_unpriced`.
- **AC-7 (journey + observability).** *Given* the QA container *When* a user opens
  the chat effort menu, selects a non-default level, and sends *Then* the scenario
  passes across light/dark, 375 px, and keyboard focus; the turn span carries
  `capability_source`; and an unsupported effort is rejected, never silently clamped.
- **AC-8 (bump, if W5 runs).** *Given* 0.85.1 on both surfaces *When* the full
  suites run *Then* all pass and every fixture diff is justified in the ledger.

---

## 8. Exact verification commands

```bash
# Runtime
cd pi-runtime && npm test                                    # baseline 54/54, 8.4s
cd pi-runtime && npm test -- capability-inheritance           # W3 payload diffs

# Backend
pytest tests/pi_compat -q
pytest tests/pi_production -q
pytest tests/pi_migration/test_version_provenance.py -q
pytest tests/test_model_source.py tests/test_pi_replacement_candidate.py -q
pytest tests/test_research_validity_contract.py -q            # spine unchanged

# Frontend
cd frontend && npx vitest run src/lib/modelCatalog.test.ts
cd frontend && npx tsc --noEmit

# Generator round-trip
python scripts/generate_pi_catalog.py --check                 # must be a no-op diff

# Security (LLM-provider surface trigger, AGENTS.md)
python scripts/security_benchmark.py --fail-on-threshold

# UI suite (container-first, loopback publish only)
docker compose -f docker-compose.qa.yml --profile ui up -d
node tests/simulation/run.mjs --scenario 10-settings-models,05-chat-interaction

# Benchmarks
python tests/benchmarks/run_benchmarks.py
```

---

## 9. Risks

| # | Risk | Likelihood | Mitigation |
|---|---|---|---|
| R1 | **Regenerating the mirror silently changes live pricing** (188 cost fields; 104 get more expensive). Ceilings that never tripped start tripping. | High | 1.4 is an explicit owner-review step with the full diff. Operator contract pricing stays a tier-1 endpoint override — the generator sets list rates, not negotiated rates. |
| R2 | Corrected `thinkingLevels` changes menus for 976 models; a user's saved `thinking_mode` may no longer be offered. | High | `ChatModelControls.tsx:269-270` already falls back to `server_default` when the saved value is not in the list. Assert that path in 4.5. |
| R3 | A registry `compat` flag we now pass through breaks a provider that Istara's narrower payload happened to satisfy. | Medium | Fixtures make every field change visible per provider before it ships; W6 bounded live probe on the three real endpoints. Rollback is per-field: pin an override in the endpoint record. |
| R4 | Mirror grows +63.9% (544 KB → 892 KB); it is loaded and `asdict`-serialized per catalog request (`catalog.py:270`). | Medium | Measured and accepted for auditability. If the API response size regresses, emit `compat` only where it differs from `detectCompat()` — a ~10× smaller delta — at the cost of a harder-to-audit file. Decide on measurement, not speculation. |
| R5 | Flipping two asserted-correct tests looks like weakening the suite. | Medium | Each flip cites its B-E evidence in-file and in the ledger; the fallback fixtures (AC-1) *strengthen* the suite in the same commit. |
| R6 | `capability` descriptor crossing the boundary is new untrusted input to the worker. | Medium | `validateCapabilityDescriptor` rejects unknown keys and non-conforming shapes at bind time, matching `mapProviderParams`' existing discipline. Descriptor carries no secrets. |
| R7 | pi-ai relocates or renames `providers/all` in a future release. | Low | The generator is the *only* importer; a rename breaks one dev-time script loudly at bump time — precisely the desired failure mode. |
| R8 | W5 (0.85.1) changes semantics the fixtures then pin as "expected." | Low | W5 runs **after** W3, so every diff is visible and must be justified in the ledger before it is accepted. |

---

## 10. Explicitly out of scope (named, not silently dropped)

- **OAuth/auth-metadata inheritance.** `catalog.py`'s `_OAUTH_PROVIDERS` /
  `_API_KEY_PROVIDERS` hand-list 39 providers' flows and env vars, duplicating
  what `builtinProviders()[].auth` exposes — the *same* defect class as
  capabilities. Deferred deliberately: it touches credential custody and
  `oauth.py` (820 lines), and folding it in would make this delivery
  security-sensitive end to end. **Recorded as architecture debt** with the
  generator already positioned to emit it in a follow-on.
- Provider additions, product redesign, embeddings-gateway changes (W3 verifies,
  does not modify), Research Spine changes.
- Unbounded live spend: W6 is bounded, owner-authorized, one target at a time.

---

## 11. Rollback

Per wave, no state migration, no schema change:

- **W1:** `git revert` the generator + regenerated mirror. The mirror is a data
  file with no readers outside `catalog.py`; reverting restores today's exact
  behavior.
- **W2:** revert `provider.mjs` + the four backend files. A stale `capability`
  key on a persisted endpoint is inert — the reverted `modelCapabilities` ignores
  unknown endpoint fields.
- **W3/W4:** test-and-telemetry only.
- **W5:** `git checkout <sha> -- pi-runtime/package*.json labs/pi-replacement/package*.json && npm ci`
  in both surfaces, then regenerate.

**Correction to the lifecycle's stated rollback:** it names a "two-file revert
(`provider.mjs`, `package.json`+lockfile)". That misses `labs/pi-replacement`,
whose pin `tests/pi_migration/test_version_provenance.py` asserts must match — a
two-file revert leaves that test red.

---

## 12. Contract compliance

- **Research Spine.** No research-data path changes. The turn's provider-reported
  identity receipt (`attachProviderModel` / `responseModel`) is untouched; W4's
  `capability_source` is additive span metadata that strengthens route evidence.
  No gate is bypassed; nothing becomes reportable without Done-task acceptance.
- **Security Benchmark Gate.** This is an LLM-provider surface change →
  `python scripts/security_benchmark.py --fail-on-threshold` runs in W4 and its
  scorecard is attached as CF command evidence. Secrets are untouched: the
  descriptor carries capability metadata only, and the per-session env-var
  custody in `buildRealProvider` is unchanged.
- **Full UI Testing Suite Contract.** W4.4/4.5 add real browser acts for the
  effort journey — currently **zero** coverage (B-E8) — with the role/theme/
  reflow/keyboard matrix, synthetic data, registry verdicts, and `TESTING.md`
  updated for the new suite file.
- **Protected local artifacts.** `LLMs/` and `Model_Finetuning/` untouched.
- **Live-model safety.** No live probe before W6, which is owner-gated.

---

## 13. Decisions requested of the owner

- **DEC-B1 — Authority read point.** Approve the **generated projection** (§2.3)
  over a runtime `getBuiltinModel()` call, on the measured grounds that the
  latter costs 67 ms / 60 MB per worker session and fixes only one of four
  consumers.
- **DEC-B2 — Pricing regeneration.** Approve replacing 188 mirror cost fields
  with pi-ai list rates (104 increase). Confirms that pi-ai is the authority for
  *list* pricing and that operator/contract pricing remains a tier-1 endpoint
  override.
- **DEC-B3 — Test flips.** Approve flipping the two tests that currently assert
  the divergent behavior as correct (`provider-params.test.mjs:192-235`, `:121-131`).
- **DEC-B4 — W5 separability.** Confirm whether the 0.85.1 bump ships with W1–W4
  or as a follow-on. **Recommendation: follow-on**, so the bump diff is read
  against a corrected baseline.
- **DEC-B5 — Auth inheritance deferral.** Confirm §10's deferral of OAuth/env-var
  inheritance to a separate, security-gated delivery.

---

## 14. Why this ordering

W0 before W1 because the only credible proof that inheritance is additive is a
fixture captured *before* the change. W1 before W2 because the descriptor W2
transports does not exist until the generator emits it. W3 immediately after W2
because the two tests that currently assert the defect must flip in the same
review that makes them wrong. W4 after W3 because an effort allowlist is only
correct once the levels are correct. W5 last because a version bump is only
routine once the machinery that makes it routine exists — which is the entire
point of the initiative.

---

*Prepared by architect slot B (claude-opus-5, effort=high) for CF task
`pi-compat-20260908-PLAN-B`. All measurements taken 2026-09-08 against
`@earendil-works/pi-ai@0.84.3` in `pi-runtime/node_modules`, node v26, and are
re-runnable from the repository root.*
