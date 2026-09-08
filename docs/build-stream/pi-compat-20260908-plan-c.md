# S1 Draft Plan — Slot C: Pi Compatibility Authority & Istara Integration Boundary

Task: `pi-compat-20260908-PLAN-C` · Role: `pi-compat-20260908-architect-c` · Phase: S1 draft (independent, pre-synthesis)
Author: zai/glm-5.3-flash (effort=max) · Date: 2026-09-08 · Spec: CF-SPEC-29
Inputs: lifecycle `docs/build-stream/2026-09-08-pi-capability-inheritance.md` (owner-approved expanded frame, DEC-2), repository inspection, Compass Forge graph context. All claims below were re-measured in this session, not copied.

---

## 0. Thesis

**One authority, one seam, one mirror — nothing restated.**

Pi compatibility in Istara currently fails not because the integration is broken but because
provider knowledge lives in three places that drift independently: (1) a hand-written
`modelCapabilities()` in `pi-runtime/src/provider.mjs`, (2) a static JSON mirror in
`backend/app/core/pi_runtime/data/pi_models_catalog.json` whose schema cannot even carry the
fields that matter (`thinkingLevelMap`, `compat`), and (3) implicit reliance on pi-ai's
internal registry that never crosses the worker's synthetic model record. The fix is a
single load-bearing rule:

> **pi-ai's generated registry (`@earendil-works/pi-ai/providers/all`) is the sole authority
> for provider/model capability knowledge.** Istara code may only (a) inherit from it at
> bind time, (b) override it with operator-resolved values that pi-ai cannot know (pricing,
> context/max-token windows, catalog-advertised flags), or (c) reproduce it as a
> *regenerated, version-stamped mirror* for the backend, which never imports pi-ai by
> design. Any third statement of provider knowledge is architecture debt.

This makes a Pi version bump a controlled maintenance action: bump, regenerate the mirror,
watch the pinned conformance fixtures, and every divergence is either an intended upstream
change (update fixtures deliberately) or a regression (test fails).

## 1. Measured ground truth (this session, re-runnable)

| # | Measurement | Result | Command |
|---|---|---|---|
| M1 | Installed pi-ai | `0.84.3` (`pi-runtime/package.json`); `labs/pi-replacement` also pins `0.84.3` | `grep '"@earendil-works/pi-ai"' pi-runtime/package.json labs/pi-replacement/package.json` |
| M2 | Registry export surface | `getBuiltinProviders`/`getBuiltinModel`/`getBuiltinModels`/`getBuiltinModelDataGeneratedAt` are exported from `@earendil-works/pi-ai/providers/all`, **not** the package root (`./compat` carries deprecated aliases `getModel/getModels/getProviders`) | `sed -n '1,60p' pi-runtime/node_modules/@earendil-works/pi-ai/dist/providers/all.d.ts` |
| M3 | Registry completeness | 39 provider ids; `getBuiltinModel('zai','glm-5.3')` carries `reasoning:true`, `thinkingLevelMap:{off:null,minimal:null,low:"low",medium:null,high:"high",xhigh:null,max:"max"}`, `compat:{supportsStore:false,supportsDeveloperRole:false,supportsReasoningEffort:true,maxTokensField:"max_tokens",thinkingFormat:"zai",zaiToolStream:true}`, contextWindow 1,000,000 | `node -e "import('@earendil-works/pi-ai/providers/all').then(m=>console.log(JSON.stringify(m.getBuiltinModel('zai','glm-5.3'))))"` (run in `pi-runtime/`) |
| M4 | Codex record | `openai-codex` models: `gpt-5.3-codex-spark,gpt-5.4,gpt-5.4-mini,gpt-5.5,gpt-5.6-luna,gpt-5.6-sol,gpt-5.6-terra`; `gpt-5.6-luna` carries `thinkingLevelMap:{xhigh:"xhigh",max:"max",minimal:"low"}` — the mapping Istara's hardcoded `thinkingLevels:["xhigh","max","minimal"]` list loses | same pattern, `getBuiltinModel('openai-codex','gpt-5.6-luna')` |
| M5 | **E2 correction** | Installed 0.84.3 zai = `glm-4.7,glm-5-turbo,glm-5.2,glm-5.2-highspeed,glm-5.3`; zai-coding-cn adds 3 models. **`glm-5.3-flash` is NOT in installed 0.84.3** (direct lookup `undefined`). Mirror absence of glm-5.3-flash *matches* installed 0.84.3; the lifecycle's E2 wording ("installed 0.84.3 has both") is wrong on this point. `glm-5.3-flash` must be verified against 0.85.1 after the bump, not asserted now | `getBuiltinModels('zai')`, `getBuiltinModel('zai','glm-5.3-flash')` |
| M6 | Mirror staleness | Mirror `zai.glm-5.3` has `thinkingLevels:null` while installed 0.84.3 has the M3 map; `PiCatalogModel` (catalog.py:40) has no `thinkingLevelMap`/`compat` field at all — the mirror cannot represent the fields that matter even if regenerated as-is | `python3` JSON dump of `backend/app/core/pi_runtime/data/pi_models_catalog.json` |
| M7 | Wire mapping is pi-ai's, given the map | `openai-completions.js:507`: `clampThinkingLevel(model, options.reasoning)`; `getSupportedThinkingLevels(model)` filters through `thinkingLevelMap` (null = unsupported; xhigh/max require explicit entries). With the map inherited onto the synthetic model record, requested `minimal` on zai clamps to wire `low` automatically | `grep -n clampThinkingLevel pi-runtime/node_modules/@earendil-works/pi-ai/dist/api/openai-completions.js` |
| M8 | Duplication point | `modelCapabilities()` (provider.mjs:402) hand-restates codex/deepseek/qwen-set/zai-set knowledge; `buildRealProvider()` builds a synthetic model record literal and registers it as `pi-endpoint-<endpoint_id>` — pi-ai's registry never participates | `sed -n '395,530p' pi-runtime/src/provider.mjs` |
| M9 | Backend stays pi-ai-free | Backend catalog is a static JSON resource; `engine.py` forwards `pi_provider`, `supports_reasoning`, `thinking_level` params only; `llm_thinking.normalize_model_effort` is a provider-agnostic passthrough; `chat.py` SSE usage frames echo `effort` (SPEC-26) | `grep -n "thinking_level\|supports_reasoning" backend/app/core/pi_runtime/engine.py` |
| M10 | Frontend consumption | `ChatModelControls.modelEffortLevels()` consumes catalog `thinkingLevels` (falls back to full 8-level ladder when null + reasoning — which is how glm-5.3 currently advertises unsupported levels); `PiCatalogModel` types at `types.ts:337` and `api.ts:1242` carry `thinkingLevels` only | `sed -n '33,40p' frontend/src/components/chat/ChatModelControls.tsx` |
| M11 | Upstream | `@earendil-works/pi-ai@0.85.1` exists on npm; E4's "diff restricted to non-consumed surfaces" is a claim to be **re-proven as a task**, not trusted | `npm view @earendil-works/pi-ai versions` |
| M12 | Out of scope confirmed | `relay/lib/llm-proxy.mjs` `modelCapabilities` is local-LLM detection (LM Studio/Ollama shape), a different concept — no change | `sed -n '404,427p' relay/lib/llm-proxy.mjs` |

## 2. Design: layered capability resolution

Replace the hand-restated branches of `modelCapabilities()` with a resolution pipeline in
`buildRealProvider()` that composes four layers, strictest-last:

```
L4  catalog advertised flags   (endpoint.supports_reasoning, supports_vision — operator truth)
L3  endpoint operator limits   (context_window, max_tokens, pricing — cost-ceiling integrity)
L2  Istara provider identity   (thinkingFormat naming, custom-gateway supportsDeveloperRole)
L1  pi-ai builtin record       (reasoning, thinkingLevelMap, compat, input modalities)
```

- **L1 (inherit).** At bind time, lazily `import("@earendil-works/pi-ai/providers/all")` and
  look up `getBuiltinModel(endpoint.pi_provider, endpoint.model)`. If found, inherit
  `reasoning`, `thinkingLevelMap`, `compat`, `input` onto the synthetic model record.
  Inheriting `thinkingLevelMap` is what makes the wire correct: pi-ai's own
  `clampThinkingLevel` then maps/filters requested levels at stream time (M7), including
  codex `minimal→low`.
- **L2 (identity).** Keep exactly two Istara-authored statements: (i) the
  `thinkingFormat` naming for zai/deepseek/qwen families (gateway/proxy base URLs may not
  reveal the provider — this is Istara's identity pass-through, merged per-field over L1);
  (ii) `supportsDeveloperRole:false` for non-OpenAI custom openai_compat gateways.
- **L3 (operator limits).** Pricing stays backend-resolved (cost ceiling fails closed);
  context/max-token windows keep `modelLimits()` endpoint-over-inherited precedence.
- **L4 (advertised flags).** `endpoint.supports_reasoning`/`supports_vision` override L1's
  `reasoning`/`input` when explicitly set (current behavior preserved).
- **Fallback is identity, not synthesis.** If `getBuiltinModel` misses (dashscope snapshot,
  custom gateways, unlisted models), the resolved record must equal today's
  `modelCapabilities()` output for the same endpoint — proven byte-for-byte by golden wire
  fixtures, not asserted. Provider families keep today's qwen/deepseek/zai restatements
  *only* where the registry has no entry (dashscope), and lose them where inheritance
  covers them (zai, deepseek, codex) with fixtures proving wire equality or intended,
  reviewed deltas.
- **Effort telemetry unchanged.** `chat.py` SSE `effort` echo and worker identity receipts
  (`captureProviderFetch`) are untouched by design — SPEC-26 semantics preserved.

**Backend boundary.** The backend never imports pi-ai (M9). The mirror is a build artifact:
a Node-side regeneration script reads the *installed* pi-ai registry and emits
`pi_models_catalog.json` with a `generated_from {version, generatedAt}` stamp. Freshness is
machine-checked: a drift test regenerates and diffs; the mirror can never silently lag its
authority again.

**Frontend honesty.** `PiCatalogModel` gains optional `thinkingLevelMap` (and
`compat.thinkingFormat` where useful); `modelEffortLevels()` lists exactly the levels whose
map value is non-null when a map is present, falling back to today's ladder otherwise. No
menu redesign — the existing consumers just stop advertising unsupported levels.

## 3. Task breakdown — dependency-ordered waves

### W1 — Inheritance seam in the worker (no version change)
*Files: `pi-runtime/src/provider.mjs`, `pi-runtime/test/provider-params.test.mjs`, new `pi-runtime/test/wire-conformance.test.mjs` + `pi-runtime/test/golden/` fixtures.*

1. Add lazy registry lookup + L1–L4 merge in `buildRealProvider()`; `modelCapabilities()`
   becomes the L2/fallback path only (kept exported for tests).
2. Golden wire-payload capture tests: per provider family (codex-responses, zai, deepseek,
   qwen/dashscope, generic openai_compat, anthropic_compat), bind via a stub fetch that
   captures `init.body`, assert the exact request payload. Fallback families (dashscope)
   assert **byte-identical to pre-change payloads**; inherited families (zai glm-5.3, codex
   luna, deepseek) assert the intended map-derived payloads (e.g. requested `minimal` on
   luna → wire effort `low`).
3. Unit tests: builtin hit vs miss, advertised-flag override, `off` omits the field,
   unknown `pi_provider` falls back unchanged.
- **Acceptance:** all four `pi-runtime` suites green; fallback payloads byte-identical;
  inherited families show only the intended, reviewable wire deltas.
- **Verify:** `(cd pi-runtime && npm test)`; `node --test test/wire-conformance.test.mjs`.
- **Rollback:** single-file revert of `provider.mjs` (+ test files); no data, no state.

### W2 — Mirror regeneration mechanics + schema extension (still on 0.84.3)
*Files: new `scripts/pi_catalog/regenerate_pi_catalog.mjs`, `backend/app/core/pi_runtime/catalog.py`, `backend/app/core/pi_runtime/data/pi_models_catalog.json`, `backend/app/core/pi_runtime/data/pi_models_catalog.meta.json` (or inline stamp), `frontend/src/lib/types.ts`, `frontend/src/lib/api.ts`, `frontend/src/components/chat/ChatModelControls.tsx`, `frontend/src/lib/modelCatalog.test.ts`, backend tests.*

1. Regeneration script (Node, reads pi-ai from `pi-runtime/node_modules`) emits the full
   registry (now including `thinkingLevelMap` + `compat` per model) plus the existing
   auth/OAuth metadata and governed dashscope snapshot; stamps `generated_from`.
2. Extend `PiCatalogModel` (catalog.py:40) with `thinkingLevelMap: dict[str, str|None] | None`
   and `compat: dict | None`; loader passes them through the settings/chat catalog API.
3. Backend drift test: regenerate → diff against committed JSON → fail on drift (pins
   mirror to installed authority; becomes the W3 re-run point).
4. Frontend: optional types; effort menu lists exactly supported levels when a map is
   present (glm-5.3 → `off? no` → `low/high/max` + server_default/off); fallback ladder
   unchanged for mapless models.
- **Acceptance:** `pytest` catalog/UX suites green; drift test fails when registry and
  mirror disagree (mutation-proven); menus for glm-5.3 advertise only supported levels.
- **Verify:** `python -m pytest tests/pi_production/test_pi_catalog_ux.py tests/test_pi_replacement_candidate.py -q`; `node scripts/pi_catalog/regenerate_pi_catalog.mjs --check`; UI scenario below.
- **Rollback:** revert script + schema + JSON; JSON-only change is data, no migration.

### W3 — Version adoption 0.84.3 → 0.85.1 (evidence-gated)
*Files: `pi-runtime/package.json` + lockfile; `labs/pi-replacement/package.json` + lockfile (lockstep or pinned-deliberately, recorded in ledger).*

1. **Diff-proof first:** install 0.85.1 in a scratch dir; diff `dist/` for the surfaces
   Istara consumes (`providers/all`, `providers/zai*`, `providers/openai-codex*`,
   `models.js` mapping, `api/openai-completions`, `api/openai-codex-responses`,
   detection/retry helpers). The lifecycle's E4 claim is re-measured here; any consumed-
   surface change updates W1 fixtures deliberately before the bump lands.
2. Confirm `glm-5.3-flash` presence (M5 correction) — record as evidence either way.
3. `npm ci` both packages; re-run regeneration + drift test (mirror now regenerated from
   0.85.1 — the intended fix for M6); all suites.
- **Acceptance:** pi-runtime suites + backend pi suites + benchmark green on 0.85.1;
  fixtures either byte-identical or diff-reviewed.
- **Verify:** `(cd pi-runtime && npm test)`; `python -m pytest tests/pi_production tests/test_pi_replacement_candidate.py -q`; `node scripts/pi_catalog/regenerate_pi_catalog.mjs --check`; benchmark per TESTING.md lane.
- **Rollback:** revert `package.json`+lockfile, `npm ci`, re-run `regenerate --check`
  (one command restores the pinned mirror).

### W4 — Acceptance, governance, live proof (owner-gated live spend)
*Files: `tests/simulation/scenarios/10-settings-models.mjs` (+ registry verdict), `security/control_matrix.json` (only if a control/evidence path changes), docs.*

1. Extend the settings-models UI scenario: effort menu reflects per-model map honesty for
   an inherited provider and the fallback ladder for a mapless one; light/dark + 375px
   reflow + keyboard focus; record dated verdict in scenario summary + registry.
2. Security benchmark (LLM-provider change triggers the gate): run scorecard, attach
   evidence; update control matrix only if a control statement actually changed.
3. Bounded live T1 re-probe (owner-approved window only): fresh `low`-effort turns on
   luna/zai-glm/terra; assert SSE `effort=low`, provider-observed behavior, identity
   receipts intact. Dashscope fallback payload parity re-checked from logs.
4. Docs: `docs/build-stream/` lifecycle + a short maintenance runbook ("when Pi ships a
   new version": bump → diff-proof → npm ci → regenerate --check → suites → fixtures
   review → ship).
- **Acceptance:** lifecycle's four Given/When/Then criteria all evidenced; UI suite green
  in the container lane; security scorecard at threshold.
- **Verify:** scenario runner + registry verdict; `python scripts/security_benchmark.py --fail-on-threshold`; container turn logs.

## 4. Acceptance-criteria mapping (lifecycle → waves)

| Lifecycle criterion | Proven by |
|---|---|
| `getBuiltinModel` record used at bind; advertised flags override | W1 fixtures + unit tests |
| Unlisted model fallback + detection byte-identical | W1 dashscope golden fixtures |
| pi-ai 0.85.1 all suites + benchmark pass | W3 suite/benchmark commands |
| Fresh `low` turn → `effort=low` reported + observed | W4 live T1 evidence (owner-gated) |

## 5. Risks & mitigations

1. **Registry misses a production model** (dashscope snapshot already proves the class) →
   fallback identity is fixture-pinned; regeneration keeps the governed snapshot.
2. **pi-ai changes map semantics at bump** → W1 fixtures fail loudly at W3 diff-proof; that
   is the desired early signal, plus `thinkingLevelMap` pinned in mirror drift test.
3. **Codex `minimal`→wire `low` rejection** (lifecycle risk 3) → fixture states the intended
   wire value; live T1 observes acceptance; degradation is effort omission with honest
   telemetry, never silent wrongness.
4. **Inheritance silently changes fallback payloads** → the golden fixtures make any
   fallback drift a test failure, not a review hope.
5. **Mirror/regeneration divergence between contributors** → `--check` drift test +
   `generated_from` stamp; CI fails on un-regenerated commits.
6. **labs/pi-replacement lockstep breakage** → explicit W3 decision (lockstep vs pinned)
   recorded in ledger; lab is not a production path.

## 6. Open questions for synthesis / owner

- Q1: Inherit `cost` from the registry? Recommendation: **no** — pricing stays
  operator/backend-resolved to preserve the fail-closed cost ceiling; registry cost is
  catalog display only.
- Q2: Lockstep-bump `labs/pi-replacement`? Recommendation: bump in W3 if its suites pass;
  else pin with a ledger note (lab-only).
- Q3: Should `modelCapabilities()` remain as an exported fallback API or fold into
  `buildRealProvider()`? Recommendation: keep exported (tests + L2 identity naming), but
  shrink to fallback-only semantics.
- Q4: 0.85.1 in the same initiative (lifecycle) vs follow-up? Recommendation: same
  initiative, **gated on W3 step 1 diff-proof** — if consumed surfaces changed, split the
  bump into its own task rather than weakening W1 fixtures.

## 7. Verification command index

```bash
cd pi-runtime && npm test                              # worker suites incl. wire conformance
node scripts/pi_catalog/regenerate_pi_catalog.mjs --check
python -m pytest tests/pi_production/test_pi_catalog_ux.py tests/test_pi_replacement_candidate.py -q
python -m pytest tests/pi_production -q                # W3 broad lane
python scripts/security_benchmark.py --fail-on-threshold
node <simulation-runner> 10-settings-models            # container-first UI lane (per TESTING.md)
```

Governance notes: Research Spine untouched — capability resolution changes binding
semantics only; evidence units, identity receipts, reliability, reconciliation, and
Done/report gates are not on this path. Compass gates expected to judge: `architecture_drift`
(single authority replaces restatement), `contract_drift` (mirror schema + wire fixtures),
`security_sensitive_surface` (LLM-provider trigger → benchmark), `test_ownership`
(provider-params + new conformance tests own the seam).
