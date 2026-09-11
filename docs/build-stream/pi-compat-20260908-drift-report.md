# Pi Compatibility Drift Report — pi-compat-20260908

**Task:** `pi-compat-20260908-WAVE-authority-and-boundary-IMPL` · **Wave:** authority-and-boundary (W1+W2+contracts)
**Measured:** 2026-09-08 against `@earendil-works/pi-ai@0.84.3` installed in `pi-runtime/node_modules`
**Re-run:** `python scripts/generate_pi_catalog.py` prints this drift summary live; the conformance test
`tests/pi_compat/test_catalog_conformance.py` now makes recurrence impossible without a gate failure.

---

## 1. Duplicated Pi knowledge (the defect class)

| Location | What it duplicated | Disposition this wave |
| --- | --- | --- |
| `pi-runtime/src/provider.mjs` `modelCapabilities` (hand-listed Codex/DeepSeek/Qwen/Zai branches) | pi-ai's registry records (`reasoning`, `thinkingLevelMap`, `compat`) | Moved **verbatim** to exported `legacyIdentityCapabilities()`, applied only on registry miss (tier-5 fallback). Registry hits now inherit the record (tier-4 authority). |
| Codex `thinkingLevels: ["xhigh","max","minimal"]` hand list | pi-ai's `thinkingLevelMap {xhigh:"xhigh", max:"max", minimal:"low"}` | Deleted from the authority path — the list lost the `minimal→"low"` mapping, so `xhigh`/`max` **silently clamped to `high`** on the wire. Fixed; wire fixtures pin `reasoning.effort: "xhigh"`. |
| Zai identity branch relying on detection fallback | `glm-5.3` record `compat.supportsReasoningEffort: true` | Detection is no longer authority for known models: `reasoning_effort` is now transmitted (`low/high/max`), previously **absent at every level**. |
| `thinkingLevels` field set on the worker model | dead field — pi-ai 0.84.x reads `thinkingLevelMap` only | No longer set. pi-ai's own `getSupportedThinkingLevels`/`clampThinkingLevel` own level semantics (DEC-M2: never reimplemented). |
| `relay/lib/llm-proxy.mjs` `modelCapabilities` | unrelated local-LLM detection (LM Studio/Ollama) | **Not unified** — different concept, explicitly out of scope (G14). |
| `catalog.py` `_OAUTH_PROVIDERS` / `_API_KEY_PROVIDERS` | `builtinProviders()[].auth` flows/env vars | Same defect class, **deferred** (credential custody; DEC-O5 architecture debt). |

## 2. Stale mirror vs installed registry (regenerated this wave)

Projection `backend/app/core/pi_runtime/data/pi_models_catalog.json` regenerated from the installed pin
(39 providers / 1,312 models) + 40 governed DashScope records (overlay file, hand-owned):

| Measure | Value |
| --- | --- |
| Models added (registry → projection) | 81 |
| Models removed (stale mirror-only) | 36 |
| Models with changed fields | 1,231 |
| `thinkingLevels` corrected (wrong menu definition) | 1,225 |
| `thinkingLevelMap` now present (was never representable) | 407 |
| `compat` now present (was never representable) | 899 |
| `contextWindow` mismatches fixed | 20 |
| Models with cost-field changes (list price, tier 4) | 63 |

Count-only freshness checks were never a proof (G7); the round-trip conformance test now enforces
**byte identity** (modulo `emitted_at`) against the installed pin.

## 3. Version / update boundary (now defined and enforced)

- **Emission:** `pi-runtime/scripts/emit-catalog.mjs` — the only maintenance-time importer of
  `@earendil-works/pi-ai/providers/all` outside the worker. Deterministic; provenance header carries
  `pi_ai_version`, `pi_ai_generated_at`, `emitter_sha256`, `model_field_set_hash` (a new upstream
  field becomes visible at bump time instead of being silently inherited).
- **Operator entry:** `python scripts/generate_pi_catalog.py` (`--check` fails on any drift; exit 3 =
  typed `not_runnable` when node/pi-ai is absent — never a silent skip).
- **Governed overlay:** `backend/app/core/pi_runtime/data/custom_providers/dashscope.json` — hand-owned
  tier-5 data, merged verbatim; collision/schema/order rejection in the emitter; wire fixtures required.
- **Conformance:** `tests/pi_compat/` — round-trip byte identity, `pi_ai_version ≡ EXPECTED_PINS`,
  all-provider parity (deletions cannot pass), and **authority equivalence**: for all 1,312 registry
  models, projected `reasoning`/`thinkingLevels`/`thinkingLevelMap`/`compat` ≡ the worker resolver's
  computation from the live registry (two read paths, one derivation).
- **Worker seam:** `resolveCapabilities()` (async, memoised once-per-process registry import) returns the
  effective record plus a content-free capability receipt; typed pre-network
  `provider_transport_mismatch` rejection with a named, fixture-backed exception list (empty today).
- **Routine bump runbook (AC-11):** lockstep `npm i @earendil-works/pi-ai@X @earendil-works/pi-agent-core@X`
  in `pi-runtime` **and** `labs/pi-replacement` → `python scripts/generate_pi_catalog.py` → the git diff of
  the projection plus the wire fixtures **is** the compatibility report → classify per §8 taxonomy.

## 4. Known constraints carried forward (evidence, not blockers)

- **Upstream zero-pricing:** 119/1,312 registry models are $0-list-priced in pi-ai itself (109
  reasoning-capable), including `zai/glm-5.3` — regeneration cannot fix `cost_budget_unpriced` for
  them. The admission-time pricing preflight (plan W3.4) and operator tier-2 rates are the designed fix
  and belong to the carry-through wave. Mid-run fail-closed terminal unchanged this wave.
- **`glm-5.3-flash`** is absent from pi-ai 0.84.3 (lifecycle E2 was wrong); verify presence in 0.85.1 at
  the bump task (W6.2). The former test bound this non-existent id — flipped to `glm-5.3`.
- **W6 (0.85.1) not attempted here** — bump runs after conformance exists (DEC-M4); diff-proof first.
