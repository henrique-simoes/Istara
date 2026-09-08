# MECE Master Plan — Pi Compatibility Authority & Istara Integration (Synthesis, Slot C)

**Task:** `pi-compat-20260908-MASTER-C` · **Role:** `pi-compat-20260908-architect-c` (synthesizer)
**Phase:** S1 synthesize · **Round:** `ac4059cd0733653e4c65` · **Spec:** CF-SPEC-29
**Date:** 2026-09-08 · **Status:** candidate for cross-vote; **no implementation is authorized by this artifact**

**Immutable sources (read in full; candidate ids as recorded by the conductor):**

| Slot | Author | Candidate id | Snapshot |
|---|---|---|---|
| a | gpt-5.6-sol (codex, effort=high) | `04ae6b5a22242f4988bc4e9325da990edb9348f1a707462fa75155f515ef7c6c` | `.compass-forge/conductor/consensus-snapshots/04ae6b5a….md` |
| b | claude-opus-5 (claude, effort=high) | `fd288e5a1216e6ba830fccbbaae1aa65904315ab88ca62472412477b752d9880` | `.compass-forge/conductor/consensus-snapshots/fd288e5a….md` |
| c | zai/glm-5.3-flash (pi, effort=max) | `5653d65311c3b19b4fe9ac100507550f3ad63a73b0c7c066ea49348662487eb4` | `.compass-forge/conductor/consensus-snapshots/5653d653….md` |

**Lifecycle:** `docs/build-stream/2026-09-08-pi-capability-inheritance.md` (owner-approved expanded frame, DEC-2).

**Rev 2 (2026-09-08, post-synthesis cross-read):** folded two independently re-measured
corrections into this candidate before the vote — the upstream zero-pricing finding (§2 G17,
§8 X11: 119/1312 registry models priced $0 by pi-ai itself, including the live-probe model
`zai/glm-5.3`) and the true `getSupportedThinkingLevels` semantics (§3, W3.3: an absent map
key is *supported* for the five standard levels; only explicit `null` excludes, and
`xhigh`/`max` are opt-in). Both verified by direct measurement; see §8 X11.

---

## 1. Synthesis thesis

The three drafts converge on one diagnosis and one cure; they disagree only on *where the
authority is read* and *when the version bump lands*. This plan preserves the best
substantiated ideas of all three, resolves every material conflict explicitly (§8), and is
organized MECE: each wave owns exactly one concern, and every concern is owned by exactly
one wave.

> **One authority, one seam, one mirror — nothing restated.**
> `@earendil-works/pi-ai`'s generated registry (at the exact installed pin) is the sole
> authority for provider/model capability knowledge. Istara may (a) inherit from it at
> worker bind time, (b) override it with operator values pi-ai cannot know (contract
> pricing, endpoint limits, advertised capability truth), or (c) reproduce it as a
> *generated, provenance-stamped projection* for consumers that must not import pi-ai
> (the Python backend, by design; the frontend, by architecture). Any third statement of
> provider knowledge is architecture debt and is deleted or governed.

Why this is urgent, not cosmetic (B's decisive contribution, re-confirmed in synthesis):
the duplicated knowledge is not merely redundant — **it is wrong in the direction of silent
degradation, and the current tests pin the wrong behavior as correct.** A Codex endpoint
cannot reach `xhigh`/`max` (they clamp to `high`); a Z.AI turn sends **no** `reasoning_effort`
at all; and all five zai mirror entries are priced `{0,0,0,0}`, so every budgeted zai run
fails closed with `cost_budget_unpriced` (`pi-runtime/src/session.mjs:536-544`).

## 2. Reconciled ground truth (measured; re-confirmed at synthesis where marked ★)

All three drafts measured independently; the synthesis re-verified the load-bearing subset
(★) with passive, re-runnable commands on 2026-09-08. Claims from the lifecycle's hard
evidence (E1–E5) that are **corrected** by drafts are marked ⚠.

| # | Fact | Source | Status |
|---|---|---|---|
| G1 ★ | Both `pi-runtime` and `labs/pi-replacement` pin `@earendil-works/pi-ai` + `pi-agent-core` at exactly `0.84.3` | A,B,C + syn. re-check | confirmed |
| G2 ★ | The registry exports (`getBuiltinModel(s)`, `getBuiltinProviders`, `getBuiltinModelDataGeneratedAt`) live at `@earendil-works/pi-ai/providers/all`, **not** the package root; wildcard subpath exports `./providers/*` and `./api/*` exist (narrow imports possible) | B, C + syn. re-check | confirmed |
| G3 ★ | Registry: 39 providers; zai = `glm-4.7, glm-5-turbo, glm-5.2, glm-5.2-highspeed, glm-5.3`; `glm-5.3` carries `reasoning:true`, full `thinkingLevelMap` (`low→"low"`, `high→"high"`, `max→"max"`), `compat.supportsReasoningEffort:true` | A,B,C + syn. re-check | confirmed |
| G4 ★ | **⚠ Lifecycle E2 correction:** `glm-5.3-flash` is absent from the mirror **and** from installed 0.84.3 (`getBuiltinModel('zai','glm-5.3-flash')` → undefined). Lifecycle's "installed 0.84.3 has both" is wrong. Verify presence only against 0.85.1 at bump time | B-E2, C-M5 + syn. re-check | corrected |
| G5 ★ | **⚠ Lifecycle E1 correction:** luna's map is `{"xhigh":"xhigh","max":"max","minimal":"low"}` — direction is `minimal→"low"` (key → wire value), not `low→minimal` | B-E1, C-M4 + syn. re-check | corrected |
| G6 | Codex capability is **inverted**: `provider.mjs:406` hand-declares `thinkingLevels:["xhigh","max","minimal"]` — a **dead field** (zero references in pi-ai/pi-agent-core dist); with no `thinkingLevelMap`, pi-ai clamps `xhigh`/`max`→`high`, and drops `supportsOpenAIGrammarTools/AdditionalTools/ToolSearch` (→ `deferredToolsMode` differs structurally) | B-E1/E2 | adopted |
| G7 | Z.AI wire proof: Istara sends `thinking:{...}` but **no `reasoning_effort`** at any level; root cause `detectCompat()` computes `supportsReasoningEffort:!isZai` while the registry record says `true`. `provider-params.test.mjs:192-235` asserts the absence **as expected** (test must flip) | B-E3 | adopted |
| G8 ★ | Mirror (`backend/app/core/pi_runtime/data/pi_models_catalog.json`, 40 providers): zai `glm-5.3.thinkingLevels:null`; **all five zai entries priced `{0,0,0,0}`** → budgeted zai runs fail `cost_budget_unpriced` (`session.mjs:536-544`); B-E4 quantifies 81 missing / 36 stale models, 976 wrong `thinkingLevels`, 20 context, 188 cost mismatches | B-E4/E5/E6 + syn. re-check | confirmed |
| G9 ★ | `PiCatalogModel` (`catalog.py:31-41`) has **no** `thinkingLevelMap`/`compat` fields — the mirror cannot represent the fields that matter even if regenerated as-is; there is **no generator in the repo** today | B, C + syn. re-check | confirmed |
| G10 ★ | Backend never imports pi-ai by design; `_bind_payload` (`engine.py:128-156`) forwards `pi_provider`, `supports_reasoning`, `thinking_level` — but **not** `supports_vision` (A's finding); `endpoint_policy._apply_catalog_fields` (`:22-56`) reads catalog cost into endpoint defaults (the cost-ceiling chain) | A, C + syn. re-check | confirmed |
| G17 ★ | **pi-ai itself prices 119/1312 registry models at $0 on input+output (109 of them reasoning-capable), including `zai/glm-5.3`** — so mirror regeneration from list prices alone can never fix `cost_budget_unpriced` for those models; an admission-time pricing preflight is required | parallel master synthesis (L-6, MASTER-B, "S-E3") + syn. re-measurement | adopted, verified |
| G11 | `providers/all` import cost (★ re-measured at synthesis): **75 ms, ~61.6 MB RSS** in a bare node process; `providers/zai` alone: 13 ms, ~48.7 MB. Workers are supervised processes (`backend/app/core/pi_runtime/supervisor.py`), so a full-registry import is a per-worker-process cost | B-E6 + syn. | confirmed |
| G12 | `llm_thinking.normalize_model_effort` accepts any `[a-z][a-z0-9_]{0,31}` token; no allowlist, no per-model check; unsupported levels clamp silently | B-E9 | adopted |
| G13 | UI suite has **zero** effort/thinking coverage (`grep` over `10-settings-models.mjs`, `05-chat-interaction.mjs` etc. returns nothing) — AGENTS.md Full UI Testing Suite Contract unmet for the whole effort journey | B-E8 | adopted |
| G14 | Baselines green on current pins: `pi-runtime` 54 tests pass; catalog/UX/runtime Python suites pass; simulation scenario 36 resolves dry-run | A, B-E10 | adopted |
| G15 | `relay/lib/llm-proxy.mjs` `modelCapabilities` is local-LLM detection (LM Studio/Ollama shape) — a different concept, out of scope; `embeddings_gateway.py`/`embedding_profile.py` are a separate pi surface — read-only conformance check only | C-M12, B §4 | adopted |
| G16 | `catalog.py` hand-lists 39 providers' OAuth/API-key metadata (`_OAUTH_PROVIDERS`/`_API_KEY_PROVIDERS`) mirroring pi-ai's `provider.auth` — the **same defect class**, deliberately deferred (§15) | B §10 | adopted |

## 3. The authority model (merged precedence law — per field, never per record)

Drafts A and B state near-identical precedence laws from different directions (A: pi-ai →
catalog restriction → operator → safety; B: endpoint override → pi-ai → identity →
detection). C's layering (L1 pi-ai ← L2 identity ← L3 operator ← L4 advertised) is the same
law. The synthesis merges them into one table. The single substantive disagreement — may an
operator *enable* what pi-ai denies? — is resolved in row R2 and registered as DEC-M6.

| Field | Authority | Merge rule |
|---|---|---|
| `api` / wire adapter | pi-ai on builtin hit | A contradictory `provider_kind` fails validation **before network I/O** unless a named, fixture-backed proxy exception exists |
| `reasoning` | pi-ai base; endpoint `supports_reasoning` explicit value overrides | R2: override works in **both** directions but is loud — an enable-over-deny requires a wire fixture and emits `capability_source="operator_override"`; nothing is silent |
| `thinkingLevelMap` | pi-ai, verbatim | Copied unchanged onto the synthetic model record; stripped when reasoning is disabled; **never hand-maintained anywhere** |
| supported thinking levels (menus) | pi-ai-computed `getSupportedThinkingLevels(model)` | Emitted by the generator into the mirror; frontend keeps consuming `thinkingLevels` — no menu redesign |
| `compat`, headers, sampling defaults | pi-ai verbatim; Istara identity compat merges per-field **only where pi-ai has no entry** | Gateway `thinkingFormat` pass-through and custom-`openai_compat` `supportsDeveloperRole:false` remain tier-3 defaults under tier-2 (preserves the DashScope/DeepSeek developer-role fix exactly) |
| `input` / vision | pi-ai base, narrowed by explicit endpoint false | Fix A's gap: `supports_vision`/effective input now propagates config → bind → worker |
| `contextWindow`, `maxTokens` | pi-ai default; endpoint may lower | A stale mirror may never enlarge a runtime limit |
| `cost` | Mirror carries pi-ai **list** prices (display + default); endpoint contract rates always win (tier 1) | Records pi-ai itself prices at $0/missing (G17: 119 models) are `pricing: "unknown"`, never a free $0 default; a budgeted bind on such a model without explicit operator rates fails closed at admission with a typed error naming the unpriced categories (unchanged `session.mjs` fail-closed semantics, made actionable). The worker never reads cost from the registry |
| supported levels (validation) | pi-ai's own `getSupportedThinkingLevels` semantics | **An absent map key means *supported* for `off/minimal/low/medium/high`; only an explicit `null` excludes a level; `xhigh`/`max` are opt-in** (verified: luna → all 7; glm-5.3 → `[low,high,max]`; mapless glm-4.7 → the 5 standard levels). Consumers validate against the pi-ai-computed set emitted by the generator — never against raw map-key presence |
| `baseUrl`, credentials, OAuth, account identity | Istara deployment/security only | Never inherited because a builtin model resolved |
| retries, timeouts, budgets | Istara execution policy | Unchanged bounds, cumulative accounting |
| route/project/evidence handles | Istara Research Spine | Capability resolution must not alter authorization, model-independence proof, reconciliation, or Done/report gates |

**Fallback is identity, not synthesis.** A registry miss (dashscope, custom gateways,
unlisted models) routes through one named legacy path (today's `modelCapabilities()` +
`detectCompat()` semantics, preserved verbatim) and must produce **byte-identical** wire
payloads to pre-change captures (W0 fixtures). Every resolution — inherited, overridden, or
fallback — emits a content-free receipt: `capability_source ∈ {pi-ai@<ver>, operator_override,
istara-custom, fallback-identity, fallback-detection}`, plus `pi_ai_version`,
`applied_override_names`, `fallback_reason`. No URLs, headers, secrets, prompts, or endpoint
fingerprints in telemetry. The receipt is observability, not report evidence.

## 4. Where the authority is read (the A/B/C conflict, resolved)

The load-bearing architectural disagreement:

- **A + C:** the worker inherits directly from the installed pi-ai registry at bind time
  (`getBuiltinModel`), lazily imported.
- **B:** rejects a worker-side full-registry import (measured 67 ms / ~60 MB RSS per worker
  process) and ships a validated `capability` descriptor from the generated mirror through
  the bind payload instead — one seam, four consumers, zero runtime import.

**Resolution: worker-side inheritance is primary; B's measured objection becomes a gate, and
B's descriptor is the pre-designed contingency.**

1. The owner's own acceptance criterion names this semantics: *"Given `getBuiltinModel(
   pi_provider, model)` resolves When a turn binds Then the pi-ai record's
   `{reasoning, thinkingLevelMap, compat}` is used."* Worker-side inheritance is the only
   reading that satisfies it literally.
2. The worker already ships the exact same pinned pi-ai package it would import — there is
   no cross-version skew, no new trust boundary, and no backend schema change required for
   correctness.
3. **Import-cost gate (W2):** the resolver must import lazily (once per worker process, on
   first builtin lookup) and prefer the narrowest public import that yields the exact model
   record (the `./providers/*` wildcard subpaths exist, G2). Before the wave closes,
   measure RSS/latency with and without in the QA container harness. Budget: **≤30 MB
   sustained RSS delta per worker process**. If the narrow imports cannot meet the budget,
   switch to B's descriptor transport (mirror → `capability` field on the endpoint record →
   bind payload → `validateCapabilityDescriptor` in the worker) — the W1 mirror and W3
   backend already carry the data, so the contingency costs ~one wave task, not a redesign.
   The measured decision and numbers go in the ledger either way.
4. The generated projection (W1) still serves the other consumers — Settings/Chat menus,
   catalog endpoint admission, cost-ceiling defaults, model-management UI — so B's
   "one seam, four consumers" insight is fully preserved; the worker is simply a fifth
   consumer that reads the authority at its own pin.

## 5. Complete compatibility surface (discovered, not assumed)

Merged from B's chain trace, A's flow, and C's scope corrections:

```
pi-ai registry (39 providers, exact pin; providers/all + ./providers/*)
      │  [W1] generator: pi-runtime/scripts/emit-catalog.mjs  (the ONLY new pi-ai importer outside pi-runtime)
      ▼
backend/app/core/pi_runtime/data/pi_models_catalog.json  (+ provenance, + governed custom overlay)
      ├─► catalog.py  PiCatalogModel(+thinkingLevelMap/compat) → Settings/Model-management UI
      ├─► endpoint_policy.py  cost/limit admission (contract rates = tier 1)
      │        └► engine.py:163 cost ceiling → session.mjs fail-closed budget
      │        └► engine.py:140 _bind_payload (+ supports_vision fix) → worker bind frame
      └─► settings.py /api/settings/pi/catalog → frontend/src/lib/modelCatalog.ts
               ├─ ChatModelControls.tsx effort menu (consumes thinkingLevels — unchanged shape)
               └─ PiModelManagement.tsx provenance badge
pi-runtime/src/provider.mjs  [W2 worker resolver]
      ├─ builtin hit → pi-ai record {reasoning, thinkingLevelMap, compat, input} + receipt
      └─ miss → named legacy fallback (identity + detectCompat), byte-identical (W0 fixtures)
pi-ai api adapters → wire payload → [W4] conformance matrix + usage/telemetry (effort_clamped)
labs/pi-replacement — second bundled pi surface, lockstep pins (test_version_provenance.py)
embeddings_gateway / embedding_profile — read-only conformance check (W4), no change
oauth.py + catalog auth metadata — same defect class, DEFERRED (§15)
relay/lib/llm-proxy.mjs modelCapabilities — different concept, out of scope (G15)
```

**Non-goals (inherited from the lifecycle, restated for scope discipline):** no unrelated
product redesign; no ungoverned provider additions; no Research Spine, authorization,
evidence, review, or Done-task bypass; no unbounded live-model spend; no menu redesign.

## 6. Dependency-ordered waves

Strict waves: each completes, passes review, and records evidence before the next begins.
Implementation starts **only after the winning plan receives owner approval** (the
conductor's approval gate; this directive authorizes planning only).

### W0 — Contract freeze & pre-change baseline *(no product code)*

| # | Task |
|---|---|
| 0.1 | Refresh CF-SPEC-29 to the owner-approved total-compatibility scope; replace/supersede the narrow task set; create the wave dependency edges and role-specific work orders. No product edit while the spec still describes only the narrow inheritance change |
| 0.2 | Refresh Compass Forge impact for runtime/catalog/endpoint/chat/validation/autoresearch/donor-routing/telemetry/Research-Spine seams; record the `.mjs` low-confidence gap and compensate with `rg` call-site + Node test ownership inventory |
| 0.3 | Capture pre-change **fallback** wire fixtures on current code (stub fetch, real adapters): dashscope, unknown proxy base URL, legacy no-override binding, deepseek, qwen, codex, zai — at every supported level. These are the byte-equality ground truth for AC-1 |
| 0.4 | Commit the quantified drift report (G8) as a dated artifact: `docs/build-stream/pi-compat-20260908-drift-report.md` |
| 0.5 | Passive audit of currently configured endpoints: exact builtin hit? transport mismatch? fallback source? Counts and stable endpoint IDs only; never secrets or URLs |

**Gate:** reviewed authority contract; expanded CF coverage with no drift; fixtures
reproducible twice with identical bytes; explicit disposition for every transport mismatch.
**Rollback:** artifact deletion only.

### W1 — Generated authority projection *(backend + tooling; still on 0.84.3)*

| # | Task | Files |
|---|---|---|
| 1.1 | Node emitter: walk `getBuiltinProviders()`→`getBuiltinModels(p)`; emit verbatim `thinkingLevelMap`, `compat`, cost, limits; `thinkingLevels` = pi-ai-computed `getSupportedThinkingLevels(record)`; provenance block (`pi_ai_version`, `generated_at`, `emitter_sha256`, overlay list) | `pi-runtime/scripts/emit-catalog.mjs` (new) |
| 1.2 | Operator entry point with `--check` drift mode (regenerate ≡ committed, else fail); prints a diff summary | `scripts/generate_pi_catalog.py` (new) — **the canonical entry point; tests and docs invoke only this** |
| 1.3 | Extract governed custom providers into a hand-owned file boundary (dashscope, 40 models); emitter merges; a future regeneration can never silently delete them | `backend/app/core/pi_runtime/data/custom_providers/dashscope.json` (new) |
| 1.4 | Regenerate the mirror; review the 188 cost + 20 context + 81/36 model diffs **as a change, not a rubber stamp** — owner sign-off required (DEC-M2; 104 models get more expensive list rates) | `pi_models_catalog.json` |
| 1.5 | Extend `PiCatalogModel` with optional `thinkingLevelMap`, `compat`; loader passes them through; API projection stays curated (menus read `thinkingLevels`; map/compat need not reach the client) | `catalog.py` |
| 1.6 | Conformance tests: all-provider parity (every canonical record present exactly once; stale/deleted upstream models cannot survive unnoticed); regenerate ≡ committed; provenance version ≡ `package.json` pin; typed `not_runnable` when `pi-runtime/node_modules` is absent — never a silent skip | `tests/pi_compat/test_catalog_conformance.py` (new) |
| 1.7 | **Pricing preflight (G17/X11):** mirror marks upstream-$0 models `pricing: "unknown"` instead of a false $0; endpoint admission fails a budgeted bind closed with a typed error naming the unpriced categories unless the operator supplied explicit rates — the regeneration that fixes display menus cannot fix budget integrity for 119 models | `catalog.py`, `endpoint_policy.py` |

**Acceptance:** menus correct for all models; budgeted runs on upstream-unpriced models
(e.g. `zai/glm-5.3`) fail closed at admission with a typed, actionable pricing-required error
and run once the operator supplies explicit rates (G17 — regeneration alone cannot fix this);
no runtime pi-ai import added to the backend; `--check` is a no-op.
**Rollback:** revert generator + regenerated mirror (a data file with no readers outside
`catalog.py`); no migration.

### W2 — Worker canonical resolver *(the inheritance seam)*

| # | Task | Files |
|---|---|---|
| 2.1 | Pure resolver in the worker: one exact, guarded `getBuiltinModel(pi_provider, model)`; on hit, start from the complete builtin record; apply the §3 table field by field; return effective model + receipt; on miss, call the named legacy fallback | `pi-runtime/src/provider.mjs` |
| 2.2 | Import-cost gate: lazy dynamic import; prefer narrowest public subpath (`./providers/*`); measure RSS/latency in the QA harness; ≤30 MB sustained delta per worker process else switch to the descriptor contingency (§4.3) and record the decision | `provider.mjs`, harness artifact |
| 2.3 | Delete the dead `thinkingLevels` field from worker emission; set `thinkingLevelMap` on the synthetic model record so pi-ai's own `clampThinkingLevel` maps/filters at stream time (codex `minimal→"low"`, zai `reasoning_effort` present) | `provider.mjs` |
| 2.4 | Shrink `modelCapabilities()` to the exported **legacy fallback** (tier-3/4) only; custom `openai_compat` `supportsDeveloperRole` URL rule becomes a tier-3 default under tier-2 compat; no second catalog of pi-ai facts | `provider.mjs` |
| 2.5 | Typed, content-free `capability_source` receipt on the existing turn telemetry; missing builtin / transport mismatch / rejected level / applied fallback must each be observable and never silently reported as inheritance | `provider.mjs`, `session.mjs`, backend telemetry |
| 2.6 | Table-driven **wire-payload conformance test**: per `(provider, model, level)`, capture the real request body via stub fetch and assert against committed fixtures — *inherited* fixtures assert corrected payloads; *fallback* fixtures assert **byte equality with W0** | `pi-runtime/test/capability-inheritance.test.mjs` (new), `pi-runtime/test/fixtures/wire/*` (new) |
| 2.7 | **Flip** the tests that assert the divergent behavior as correct — `provider-params.test.mjs:192-235` (zai), `:121-131` (codex) — citing G6/G7 in-file and in the ledger (DEC-M3) | `pi-runtime/test/provider-params.test.mjs` |
| 2.8 | Reject unexplained builtin-adapter/`provider_kind` mismatch with a typed error before network I/O; malformed receipts/overrides fail the bind loudly (no silent revert to fallback) | `provider.mjs` |

**Gate:** payload tests prove pi-ai output for Codex Luna/Terra, Zai GLM-5.3, DeepSeek, Qwen;
the entire fallback corpus is byte-identical to W0; no network in tests; import-cost gate
measured and recorded.
**Rollback:** revert `provider.mjs` + test diffs; no persisted state (a stale override field
on an endpoint is inert to the reverted resolver).

### W3 — Backend admission & user surfaces *(lossless capability flow)*

| # | Task | Files |
|---|---|---|
| 3.1 | Forward the currently lost vision/input signal in `_bind_payload`; forward only non-secret, minimal restriction fields; never accept arbitrary client-supplied `compat` dictionaries as runtime authority | `backend/app/core/pi_runtime/engine.py` |
| 3.2 | Endpoint re-resolution at bind: catalog-derived limits/pricing defaults refresh from the current mirror at bind time so a bump never requires hand-editing endpoints; explicit endpoint values remain tier-1; preserve explicit `false`s across POST and sparse PUT | `endpoint_policy.py`, `endpoints.py`, `config.py` |
| 3.3 | Effort validation allowlist against pi-ai's ladder (`off|minimal|low|medium|high|xhigh|max` + `server_default`) **and** per-model supported-level check driven by the pi-ai-computed supported set (absent map key = supported for the five standard levels; explicit `null` excludes; `xhigh`/`max` opt-in — verified §3), **not** raw map-key presence; reject with typed `unsupported_model_effort` instead of silently clamping (G12 fix) | `backend/app/core/llm_thinking.py`, `chat.py` |
| 3.4 | Clamp honesty: when a requested level is clamped, emit `effort_clamped{requested, served}`; "never silent wrongness" becomes enforceable | `provider.mjs`, `session.mjs`, `usage_ledger.py` |
| 3.5 | Settings/Chat structure unchanged; supply standard Pi effort levels in canonical order; reset an invalid saved level to `server_default` (existing fallback at `ChatModelControls.tsx:269-270` asserted); a fallback model is never labeled provider-native; loading/error/empty states honest | `frontend/src/components/chat/ChatModelControls.tsx`, `frontend/src/lib/{types,api,modelCatalog}.ts` |
| 3.6 | Preserve authorization: endpoint mutation admin-only; project chat catalog access project-scoped; identity views secret-free | tests |

**Gate:** end-to-end deterministic test traces catalog selection → endpoint POST/PUT →
config → resolver → bind frame → worker effective model; frontend unit tests prove effort
choices, fallback labels, state reset, no layout/API regression.
**Rollback:** revert schema/bind/frontend together; added fields have defaults, no DB
migration; old serialized endpoints remain valid.

### W4 — Conformance, security, Research Spine invariants

| # | Task |
|---|---|
| 4.1 | Table-driven conformance matrix over every pi-ai API adapter used by configured/catalog models + focused exemplars: codex reasoning + SSE identity; zai thinking object + effort; deepseek forced-tool control; qwen/dashscope `enable_thinking` without unsupported effort fields; vision/input; max-token field; developer role; headers; sampling; cost tiers; timeout/retry; structured tools; cancellation; usage; typed provider errors |
| 4.2 | Read-only conformance check that `embeddings_gateway`/`embedding_profile` model assumptions still hold (G15 — verify, do not modify) |
| 4.3 | Targeted Research Spine probes: distinct endpoint/model identity, project scope, route evidence, cumulative budgets, independent coding/reconciliation, provisional status, human Done/report gates — all non-bypassable (e.g. `tests/test_research_validity_contract.py`, donor-routing suites) |
| 4.4 | Security benchmark (LLM-provider surface trigger): `python scripts/security_benchmark.py --fail-on-threshold`; update `security/control_matrix.json` / `SECURITY_BENCHMARK.md` / its tests **only if** a control, evidence path, standard version, or trigger pattern actually changed; attach scorecard as CF command evidence |

**Gate:** every conformance row has model record + normalized payload + receipt + expected
typed result; no regression vs the clean baseline; scorecard and spine evidence attached to CF.
**Rollback:** tests and telemetry only.

### W5 — Version adoption 0.84.3 → 0.85.1 *(evidence-gated; separable)*

| # | Task |
|---|---|
| 5.1 | **Diff-proof first:** install 0.85.1 in a scratch dir; diff `dist/` for every consumed surface (`providers/*`, `api/openai-completions`, `api/openai-codex-responses`, detection/retry helpers). The lifecycle's E4 claim is re-measured here, not trusted; any consumed-surface change updates W2 fixtures deliberately **before** the bump lands |
| 5.2 | Confirm `glm-5.3-flash` presence in 0.85.1 and record it as evidence either way (G4) |
| 5.3 | Bump **both** surfaces in lockstep (`pi-runtime`, `labs/pi-replacement`) + `npm ci`; move `EXPECTED_PINS` in `tests/pi_migration/test_version_provenance.py` |
| 5.4 | Regenerate the mirror from 0.85.1 (`generate_pi_catalog.py`); **the catalog diff is the compatibility report**; review every fixture diff — any wire change is a finding until justified in the ledger |
| 5.5 | Full suites + benchmark on 0.85.1 |

**Gate:** pi-runtime + backend + benchmark suites green; fixtures byte-identical or
diff-reviewed. **Separability (DEC-M4):** scheduled inside this initiative, but cleanly
deferrable by the owner — W1–W4 are present-tense corrections on the pinned version; W5 is
new adoption, and separating it means the 0.85.1 diff is reviewed against a *corrected*
baseline. **Rollback:** restore four manifests/lockfiles + prior generated catalog;
`npm ci` both surfaces; one command restores the pinned mirror. *(Corrects the lifecycle's
two-file rollback, which misses `labs/pi-replacement` and would leave
`test_version_provenance.py` red.)*

### W6 — Container-first user journeys *(AGENTS.md UI-suite contract)*

| # | Task |
|---|---|
| 6.1 | Extend `tests/simulation/scenarios/10-settings-models.mjs`: effort badge/menu reflects the model's real supported-level count for an inherited provider vs the fallback ladder for a mapless one |
| 6.2 | Extend `tests/simulation/scenarios/05-chat-interaction.mjs` (+ scenario 26/36 where they touch model/effort state): open the effort menu, select a non-default level, send, assert the session persists it — real browser acts (navigate/click/fill/send), API-behind-browser steps labeled as such |
| 6.3 | Cover the matrix: admin/researcher/viewer/stranger where auth-adjacent, light/dark, 375 px reflow, keyboard Tab + visible focus, loading/error/empty, canonical hit + custom fallback; synthetic data only; register dated verdicts + screenshot/HAR paths in `tests/simulation/lib/scenario-registry.mjs` (+ coverage matrix); loopback-only `docker-compose.qa.yml` `ui` profile |
| 6.4 | Extend `tests/real_user_benchmark` model-management probes and Research Spine probes for capability-source receipts; live requirements fail closed `not_runnable`, never silently skipped |

**Gate:** container journey passes; every unavailable live dependency is explicit
`not_runnable`. **Rollback:** scenario/registry updates only.

### W7 — Bounded live acceptance, release, docs *(owner-gated)*

| # | Task |
|---|---|
| 7.1 | After explicit live-model permission: rebuild the QA artifact from the candidate SHA; probe **one configured target at a time** (never multiple heavy models); fresh `low`-effort turns on luna / zai-glm / terra with bounded token + declared cost ceilings; secret-free raw artifacts |
| 7.2 | For each turn, reconcile requested Pi level → receipt → wire payload → served provider/model identity → usage envelope → terminal response. Measure (never assume) how 0.85.1 maps codex `minimal`/`low` and prove zai's `low` reaches the wire (G7 says today it does not). Environmental quota failure is `not_runnable`, not a compatibility pass |
| 7.3 | Offline Pi benchmark suite; any live benchmark only through its immutable manifest, owner-approved budget ledger, exact DUT identity, safe-stop/resume |
| 7.4 | Independent blind review (conductor-gated) measures catalog parity, fallback payload parity, wire behavior, UI journey, security scorecard, spine gates, artifact SHA, container identity **before** reading implementer claims |
| 7.5 | Docs: `docs/architecture/pi-compatibility-authority.md` (precedence law, generator, runbook), `CHANGELOG.md`, `CHANGE_CHECKLIST.md`/`Tech.md` touchpoints, `testing/TEST_HISTORY.md` dated release evidence; `TESTING.md` only if suite topology changed (W2/W6 add suite files → yes) |

**Release gate:** deterministic acceptance green; live acceptance passed or explicitly
owner-waived with `not_runnable` evidence; intended image/SHA running; rollback retained;
behavior verified through the UI and worker receipts. Promotion is not equivalent to live proof.

## 7. Coverage matrix — which draft insight each major section incorporates

| Master-plan section | from A (gpt-5.6-sol) | from B (claude-opus-5) | from C (glm-5.3-flash) |
|---|---|---|---|
| §1 thesis | "runtime authority for canonical semantics"; safety overlay | "wrong, not just redundant" — silent-degradation framing; budget-integrity defect | "one authority, one seam, one mirror"; third-statement-is-debt rule |
| §2 ground truth | 81/36 mirror divergence quantified; CF `.mjs` confidence gap; baselines green | B-E1..E10 (dead field, inverted codex, wire proof, mirror quantification, import cost, UI gap, effort validation) | M1–M12 registry/wire/detection measurements; E2/E1 corrections |
| §3 authority table | 4-layer precedence + restriction-only concern; receipt schema | 3-owner knowledge model; per-field (not per-record) merge; detection as last resort | L1–L4 layering; fallback-is-identity; effort telemetry unchanged |
| §4 read point | worker `getBuiltinModel` resolver (adopted, primary) | measured import-cost objection → W2.2 gate; descriptor = contingency; four-consumer seam | lazy import + registry lookup (adopted) |
| §5 surface | flow diagram, endpoint audit, provenance discipline | full chain trace incl. cost ceiling, labs/pi-replacement, oauth deferral | out-of-scope confirmations (relay, embeddings) |
| W0 | spec refresh, impact refresh, fallback freeze, endpoint audit | pre-change fixtures, drift-report artifact | — |
| W1 | provenance manifest fields; all-provider parity tests | generator + `--check`, governed overlay, cost owner-review, conformance test, mirror size acceptance | schema extension, drift test, `generated_from` stamp |
| W2 | typed pre-network rejection; resolution telemetry; no silent fallback reporting | tier-ordered resolver, dead-field removal, descriptor validation discipline, test flips | golden wire fixtures; keep `modelCapabilities()` exported as fallback; unit tests hit/miss/override |
| W3 | bind forwarding incl. vision gap; bind-time re-resolution; authorization preserved | effort allowlist, `capability_source` span, `effort_clamped`, saved-level reset | frontend honesty, no menu redesign |
| W4 | conformance matrix breadth; security + spine gates | security-benchmark trigger discipline | embeddings read-only check |
| W5 | lockstep pins + provenance test (timing overridden, see §8) | bump-last + separability (adopted); rollback correction | diff-proof-first (adopted); flash verification |
| W6 | role/theme/reflow/keyboard matrix; registry verdicts | scenario extensions 10/05 + registry | settings scenario extension |
| W7 | bounded live protocol, blind review, terminal states | wire-reconciliation proof points; docs | acceptance mapping to lifecycle criteria |
| §10 verification ladder | change/release gate commands | suite-specific commands | generator `--check`, benchmark lane |
| §11 risks | full-record inheritance field-set risk; telemetry leak allowlist | R1–R8 (pricing sign-off, menu churn, fixture flips, size) | registry-miss, bump-semantics, lockstep risks |

## 8. Conflict reconciliation register

| # | Conflict | Resolution | Rationale |
|---|---|---|---|
| X1 | Lifecycle E2 says `glm-5.3-flash` exists in installed 0.84.3; B and C measured it does not | Adopt B/C (G4); verify against 0.85.1 at W5.2 | Re-measured at synthesis (`getBuiltinModel('zai','glm-5.3-flash')` → undefined) |
| X2 | Lifecycle E1 map direction `low→minimal` | Adopt `minimal→"low"` (G5) | Direct registry read |
| X3 | Authority read point: A/C worker-side vs B descriptor transport | Worker-side primary; B's objection becomes a measured gate (≤30 MB delta); descriptor = pre-designed contingency | Lifecycle acceptance names `getBuiltinModel` at bind; same-pin import has no skew/trust cost; B's 75 ms / 61.6 MB measurement is honored as the gate |
| X4 | Bump timing: A pins 0.85.1 early; B bumps last (deferrable); C gates on diff-proof | Bump **last** (W5), diff-proof first, cleanly separable | Three-to-two with the lifecycle's own phase order (inheritance → bump); a bump diff must be read against a corrected baseline |
| X5 | Operator override direction: A restriction-only (cannot enable) vs B/C endpoint-wins | Override both directions, but **loud**: enable-over-deny requires a wire fixture + `operator_override` receipt (DEC-M6) | Preserves operator sovereignty over deployment reality (gateways pi-ai can't see) without ever allowing silence; A's safety concern is met by loudness + fixtures |
| X6 | Cost inheritance: A operator rates only; C no registry cost at runtime; B regenerate list prices | Mirror carries pi-ai **list** prices as catalog defaults (owner sign-off, DEC-M2); endpoint contract rates always tier-1; worker never reads cost from the registry; unpriced fail-closed unchanged | Fixes the real defect (zai `{0,0,0,0}` → `cost_budget_unpriced`) without letting list prices clobber negotiated rates |
| X7 | Mirror carries `thinkingLevelMap`/`compat`: A minimal vs B verbatim (+64% size) vs C schema extension | Verbatim in the **file** (auditability; the bump diff is the compatibility report), curated in the **API projection** (client reads `thinkingLevels` only) | Both concerns honored; size risk measured (B R4) with the slim-delta alternative on record |
| X8 | Effort validation: C keeps passthrough; B adds allowlist | Adopt B's typed allowlist + per-model check (W3.3) | Silent clamping of arbitrary tokens contradicts the initiative's own "never silent wrongness" principle |
| X9 | `modelCapabilities()` fate: C keeps exported; B folds tiers; A separates legacy function | Keep it exported, shrunk to the named legacy/fallback path (W2.4) | Convergence: tests need it, the fallback contract needs it named, and deletion would break the byte-equality story |
| X10 | Rollback scope: lifecycle's two-file revert | Adopt B's correction: both surfaces + mirror + resolver revert as one tested set | A two-file revert leaves `test_version_provenance.py` red |
| X11 | *(post-draft, rev 2)* Parallel master synthesis (L-6, `pi-compat-20260908-MASTER-B`, "S-E3") showed draft B's original AC-6 ("regeneration fixes zai budget runs") was unachievable, and the level-validation rule assumed in draft C's M10 reasoning (non-null map key = supported) is wrong | Adopted after **independent re-measurement**: G17 (119/1312 upstream-zero, `glm-5.3` included) → W1.7 preflight + R14 + DEC-M8; `getSupportedThinkingLevels` semantics verified (luna 7, glm-5.3 3, glm-4.7 5 levels) → §3 + W3.3 fixed | Verified before adoption; neither correction was taken on trust |

## 9. Acceptance matrix

The lifecycle's four Given/When/Then criteria are the owner-facing floor (rows 1–4); the
additions make the plan complete.

| Given / when | Then | Proof |
|---|---|---|
| 1. `getBuiltinModel(pi_provider, model)` resolves; a turn binds | pi-ai record's `{reasoning, thinkingLevelMap, compat}` is used; advertised flags override | W2 payload captures + §3 R2 fixtures (per provider) |
| 2. An unlisted model binds (dashscope/proxy/legacy) | Fallback switch + detection behave exactly as today | W0 fixture corpus byte-identical (AC-1) |
| 3. pi-ai 0.85.1 installed | All pi-runtime + backend chat/validation suites + benchmark pass | W5 exact commands |
| 4. Fresh `low`-effort turn on luna/zai-glm/terra post-rebuild | `effort=low` reported **and** provider-observed; codex runs at mapped `minimal` per pi-ai's map | W7.2 live receipts (owner-gated) |
| 5. Endpoint has `supports_reasoning:false` on a reasoning-capable model | No thinking/effort field emitted — tier-1 beats tier-2 | config→bind→worker negative test |
| 6. Builtin and configured transport disagree | Typed pre-network rejection unless a named, fixture-backed proxy exception | zero-fetch negative test |
| 7. Clean tree, `generate_pi_catalog.py --check` | Regenerating reproduces the committed mirror byte-for-byte; provenance version ≡ pin; a bump without regeneration fails CI | `tests/pi_compat` |
| 8. Budgeted run on a catalog-default endpoint whose model is upstream-unpriced (e.g. `zai/glm-5.3`) | Fails closed at admission with a typed pricing-required error naming the unpriced categories; runs without `cost_budget_unpriced` once the operator supplies explicit rates; menu offers the true ladder, not `[xhigh,max]` | W1.7 + W3 tests |
| 9. Unsupported effort token submitted | Typed `unsupported_model_effort`; clamping emits `effort_clamped{requested,served}` | W3.3/W3.4 |
| 10. User drives the effort journey in the QA container | Scenario passes across roles/light-dark/375 px/keyboard; turn span carries `capability_source` | W6 registry verdicts |
| 11. Research workflow uses an affected route | Evidence units, model identity, reliability/reconciliation, route evidence, Done/report gates intact | W4.3 spine probes |
| 12. A future Pi version is proposed | Version/field/catalog/wire diffs are generated mechanically; unclassified changes fail before release | §12 runbook + W4 differential classification |

## 10. Verification ladder (canonical; run from repo root unless subshelled)

```bash
# Worker / runtime
(cd pi-runtime && npm ci && npm test)                       # baseline 54/54 → +conformance
(cd pi-runtime && npm test -- capability-inheritance)       # W2 payload diffs
(cd labs/pi-replacement && npm ci && npm run validate)

# Generator (canonical entry point — tests/docs invoke only this)
python scripts/generate_pi_catalog.py --check               # must be a no-op diff

# Backend
python -m pytest tests/pi_compat -q
python -m pytest tests/pi_production/test_pi_catalog_ux.py \
  tests/pi_migration/test_version_provenance.py \
  tests/pi_production/test_engine_http_provider.py \
  tests/test_research_validity_contract.py -q
python -m pytest tests/pi_production tests/pi_benchmark -q   # broad lane (W4/W5)

# Frontend
(cd frontend && npx vitest run src/lib/modelCatalog.test.ts && npx tsc --noEmit)

# Change / release gates
python scripts/check_feature_obligations.py --base origin/testing --head HEAD --json-out artifacts/feature-obligations.json
python scripts/check_change_obligations.py --base origin/testing --head HEAD
python scripts/check_test_harness.py && python scripts/check_integrity.py
python scripts/security_benchmark.py --fail-on-threshold

# UI journeys (container-first, loopback publish only; explicit service permission required)
(cd tests/simulation && npm run test:static)
docker compose -f docker-compose.qa.yml --profile ui up -d
(cd tests/simulation && node run.mjs --scenarios 10-settings-models,05-chat-interaction --engine pi)
npm --prefix tests/real_user_benchmark run check
```

Live T1 commands are **not authorized by planning**: they name one configured endpoint, a
token/cost ceiling, an artifact directory, the candidate SHA, and the expected
provider/model — only inside W7, after explicit permission. No private URL or token is ever
encoded in commands or committed files.

## 11. Risks & mitigations (merged, deduplicated)

| # | Risk | Mitigation |
|---|---|---|
| R1 | Regenerating the mirror changes live pricing (188 cost fields; 104 increase); ceilings that never tripped start tripping | W1.4 owner sign-off on the full diff; contract rates stay tier-1; unpriced fail-closed unchanged |
| R14 | 119 upstream models are $0-priced in pi-ai itself (incl. `zai/glm-5.3`); list-price regeneration cannot fix their budget runs | W1.7 admission-time pricing preflight: `pricing: "unknown"`, typed fail-closed error, explicit operator rates required — no false "free" defaults |
| R2 | Corrected menus for 976 models; a user's saved `thinking_mode` may no longer be offered | Existing `server_default` fallback asserted in W6; no silent invalid states |
| R3 | Full-record inheritance passes a compat flag that breaks a provider Istara's narrower payload happened to satisfy | Fixtures expose every field change per provider pre-ship; bounded live probe; per-field endpoint override rollback |
| R4 | Mirror grows ~+64% (544 KB → ~892 KB), serialized per catalog request | Accepted for auditability; if API response size regresses, emit compat only where it differs from `detectCompat()` — decide on measurement (X7) |
| R5 | Flipping two asserted-correct tests looks like suite weakening | Each flip cites G6/G7 in-file and in the ledger; fallback fixtures *strengthen* the suite in the same commit |
| R6 | Worker-side import costs memory per supervised worker process | W2.2 measured gate (≤30 MB delta) with the descriptor contingency pre-designed |
| R7 | pi-ai relocates/renames export subpaths in a future release | The generator/resolver are the only importers; a rename breaks loudly at bump time — the desired failure mode |
| R8 | W5 changes semantics the fixtures then pin as "expected" | W5 runs after W3; every diff justified in the ledger before acceptance |
| R9 | Registry misses a production model | Fallback identity fixture-pinned; governed custom overlay survives regeneration |
| R10 | Capability/telemetry leaks endpoint identity or secrets | Content-free receipt allowlist; negative tests for URL/headers/credentials in telemetry |
| R11 | Compatibility change bypasses the Research Spine | W4.3 spine probes mandatory before ship; no gate bypassed |
| R12 | Live probes spend without approval or load multiple models | Owner-gated W7; one target at a time; hard ceilings; immutable budget/resume ledger |
| R13 | Shared worktree contains unrelated edits (observed at synthesis) | Isolate wave paths; `repo_lock.commit_paths` with explicit paths only; never stage ambient changes |

## 12. Routine bump runbook (the deliverable after W5)

```bash
cd pi-runtime && npm i @earendil-works/pi-ai@X @earendil-works/pi-agent-core@X
cd ../labs/pi-replacement && npm i @earendil-works/pi-ai@X @earendil-works/pi-agent-core@X
python scripts/generate_pi_catalog.py            # regenerate; prints the drift summary
git diff --stat backend/app/core/pi_runtime/data/pi_models_catalog.json   # the compatibility report
(cd pi-runtime && npm test)                      # fixtures show every wire change
python -m pytest tests/pi_compat tests/pi_migration -q
# move EXPECTED_PINS, classify every diff (intended-upstream | istara-fix | blocked), ship
```

Five commands plus a classified diff review. Retain previous pins/catalog/image digest until
acceptance closes.

## 13. Governance compliance

- **Research Spine:** no research-data path changes; capability resolution alters binding
  semantics only. Evidence units, identity receipts, reliability, reconciliation, and
  Done/report gates are not on this path; W4.3 proves it. Nothing becomes reportable
  without Done-task acceptance; the receipt is observability, never report evidence, and
  never a positive self-improvement signal.
- **Security Benchmark Gate:** LLM-provider surface change → `scripts/security_benchmark.py
  --fail-on-threshold` in W4/W5; control matrix updated only on real control/evidence-path
  changes; scorecard attached as CF command evidence.
- **Full UI Testing Suite Contract:** W6 adds real browser acts for the currently
  zero-covered effort journey with the full matrix, registry verdicts, and dated evidence.
- **Live LLM / model-loading safety:** no live probes before W7; one configured target at a
  time; passive status checks stay passive; endpoints/tokens only via gitignored env,
  process env, or Keychain.
- **Protected artifacts:** `LLMs/` and `Model_Finetuning/` untouched.
- **Compass Forge:** all state via the pinned native binary from the project root; gates
  expected to judge: `architecture_drift` (single authority replaces restatement),
  `test_ownership` (flipped + new conformance tests own the seam), security-sensitive
  surface (benchmark), `contract_drift` (mirror schema + wire fixtures).

## 14. Decisions requested of the owner (after cross-vote)

| # | Decision | Recommendation |
|---|---|---|
| DEC-M1 | Authority read point + import budget: worker-side lazy/narrow import with the ≤30 MB gate; descriptor contingency if breached | Approve worker-side primary |
| DEC-M2 | Pricing regeneration: replace 188 mirror cost fields with pi-ai list rates (104 increase); pi-ai owns *list* pricing; operator/contract rates stay tier-1 | Approve with sign-off on the diff |
| DEC-M3 | Test flips: `provider-params.test.mjs:192-235` (zai) and `:121-131` (codex) | Approve; flips cite evidence in-file |
| DEC-M4 | W5 bump: ship within this initiative (scheduled last, diff-proof first) or defer to a follow-on | Either is sound; deferring reads the bump diff against a corrected baseline |
| DEC-M5 | Defer OAuth/env-var auth-metadata inheritance (same defect class) to a separate security-gated delivery | Approve deferral; record as architecture debt (§15) |
| DEC-M6 | Operator override may *enable* what pi-ai denies — loudly (fixture + `operator_override` receipt) | Approve loud-override over A's silent restriction-only |
| DEC-M7 | New-default semantics for unknown providers: detection fallback, not hard-off | Confirm (carried from lifecycle DEC-1a, now evidence-backed) |
| DEC-M8 | Upstream-$0 records are `pricing: "unknown"`, never free defaults; budgeted binds require explicit operator rates (typed fail-closed preflight) | Approve (G17/X11; aligns with DEC-M2) |

## 15. Architecture-debt register (named, not silently dropped)

1. **OAuth/auth-metadata inheritance** — `catalog.py` `_OAUTH_PROVIDERS`/`_API_KEY_PROVIDERS`
   hand-list what `builtinProviders()[].auth` exposes. Deferred (DEC-M5): touches credential
   custody and `oauth.py` (820 lines); the generator is already positioned to emit it later.
2. **Mirror size optimization** — verbatim compat accepted; slim-delta alternative decided on
   measurement (X7/R4).
3. **CF `.mjs` graph confidence** — low-confidence seed compensated by call-site inventory;
   recorded, never worked around with a legacy runtime.
4. **`relay/lib/llm-proxy.mjs`** — distinct concept; no change (G15).

## 16. Terminal states

- **deterministic complete, live pending** — all offline/container gates pass; no claim of
  provider behavior.
- **not_runnable** — missing permission/quota/credential; exact blocker + resume command recorded.
- **rolled back** — prior pins/mirror/image restored; baseline reverified.
- **accepted** — deterministic, UI, security, spine, artifact identity, and required live
  evidence all reconcile; owner approves promotion.

---

*Prepared by synthesizer slot C (zai/glm-5.3-flash @ effort=max, pi harness) for CF task
`pi-compat-20260908-MASTER-C`, synthesis round `ac4059cd0733653e4c65`. All ★-marked facts
re-measured 2026-09-08 against `@earendil-works/pi-ai@0.84.3` in `pi-runtime/node_modules`
and are re-runnable from the repository root. This artifact authorizes no implementation.*
