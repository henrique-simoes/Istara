# Build Stream — Pi Capability Inheritance (pi-ai standard as default)

<!-- STATUS BLOCK -->
```yaml
item: pi-capability-inheritance
branch: testing
cf: { spec: CF-SPEC-29, tasks: [] }
phase: "Phase 1 — Implementation waves (authority-and-boundary)"
stage: S3-review
status: changes-requested
blocked_on: null
last: { agent: claude-opus-5, at: 2026-09-08T10:07:37Z, ledger: L-12 }
next_action: "Review FAILED (F-1 Blocker, F-2/F-3 Major). Fixer takes FIX-pi-compat-20260908-WAVE-authority-and-boundary-REVIEW-r1 and FIX-pi-compat-20260908-WAVE-authority-and-boundary-REVIEW-r1b; delta re-review after both are terminal."
```
<!-- /STATUS BLOCK -->

## Plan Overview & Roadmap

### S0 Frame — PRFAQ / one-pager (owner-approved expanded planning frame)

**Press release.** Istara's model serving now speaks pi-ai's capability
language natively: configuring an endpoint is enough — thinking levels,
effort maps, and provider wire contracts flow from pi-ai's own registry
instead of Istara-maintained duplicates. A pi version bump is routine again:
payload-diff proofs, not archaeology.

**Problem.** Three symptoms, one disease — Istara re-states pi-ai knowledge:
(a) `provider.mjs modelCapabilities` hand-lists providers while pi-ai ships a
39-provider generated registry with per-model maps; our codex list even
*loses* pi-ai's `low→minimal` mapping. (b) The backend static mirror lags the
installed pi-ai (zai `glm-5.3` map null in mirror, present in pi-ai;
`glm-5.3-flash` absent). (c) Effort died silently on paths that bypassed
pi-ai's contract (fixed in SPEC-26), proving the seam is load-bearing yet
unverified end to end.

**Outcome.** Capability inheritance with layered precedence; menus unchanged
(they already consume `thinkingLevels`); 0.85.1 adopted with proof; mirror
regeneration documented as maintenance.

**Goal.** Improve this plan with three independent architects and implement
total Pi compatibility properly: Pi/pi-ai is the compatibility authority where
appropriate, and Istara's integration is efficient, sound, observable, and
straightforward to update whenever Pi ships a new version. The current plan is
starting evidence, not an exhaustive task list. The architects must discover
the complete compatibility surface and produce a dependency-ordered,
rollback-safe implementation plan rather than treating only the existing
descriptions as tasks.

**Non-goals.** No unrelated product redesign, no ungoverned provider additions,
no bypass of the Research Spine, authorization, evidence, review, or Done-task
gates, and no unbounded live-model spend. Any catalog, Settings/Chat, mirror,
provider-contract, update/regeneration, compatibility-fixture, telemetry,
documentation, or UI-suite work that the architects prove necessary is in
scope; live probes remain bounded and explicitly evidenced.

**Appetite.** A phased, independently verifiable compatibility delivery. The
plan must separate authority and contracts, runtime/provider integration,
update/version/regeneration mechanics, regression/conformance coverage, and
release acceptance so a future Pi update is a controlled maintenance action,
not repository archaeology.

### Owner-approved planning directive (2026-09-08)

The owner approved replacing the narrow DEC-1 frame with this expanded
objective. Use this lifecycle file as the prompt and measured starting point,
but do not infer that its existing phases are complete. The architects must
use Compass Forge impact/graph evidence and repository inspection to identify
missing dependencies across `pi-runtime`, backend model/provider management,
frontend catalogs/settings/chat, provider wire and capability contracts,
thinking/effort mapping, version locks and update/regeneration workflows,
compatibility conformance fixtures, fallback/error/telemetry behavior,
documentation, and the required container-first user journeys. They must
preserve Istara's Research Spine and security/UI-testing contracts, identify
architecture debt where Pi compatibility currently bypasses them, and define
exact tasks, waves, commands, evidence, rollback, and acceptance criteria.

The conductor must run the three distinct architect routes, synthesize and
cross-vote their plans, and stop at the winning-plan owner-approval gate. No
implementation is authorized by this directive alone.

### Acceptance criteria
- `Given` `getBuiltinModel(pi_provider, model)` resolves `When` a turn binds
  `Then` the pi-ai record's `{reasoning, thinkingLevelMap, compat}` is used,
  catalog advertised flags overriding (verify: payload-capture tests +
  wire-payload diff per provider).
- `Given` an unlisted model `When` a turn binds `Then` fallback switch +
  detection behave exactly as today (verify: dashscope/proxy payload diffs
  byte-identical).
- `Given` pi-ai 0.85.1 `When` installed `Then` all pi-runtime suites +
  backend chat/validation suites + benchmark pass (verify: exact commands).
- `Given` a fresh `low`-effort turn on luna/zai-glm/terra post-rebuild `When`
  usage arrives `Then` `effort=low` and provider-observed behavior matches
  (verify: live T1 re-probe; Codex runs at mapped `minimal` by pi-ai's map).

### Doc impact
`pi-runtime/test/provider-params.test.mjs` (inheritance tests),
`docs/build-stream/` (this file), TESTING.md only if topology changes (no).

### Rollback
Two-file revert (`provider.mjs`, `package.json`+lockfile) + `npm ci`; no
migration, no state. Pin restore = one command.

### Top risks
1. pi-ai registry misses a production model → fallback switch covers
   (dashscope precedent); payload diff proves parity.
2. pi-ai changes map semantics in a future release → inheritance tests pin
   current expectations and fail loudly at bump time (desired).
3. Codex "low"→provider string rejected → observed in T1 re-probe; fallback
   is effort omission with honest telemetry, never silent wrongness.

## Hard evidence (measured, not claimed)
- **E1 — pi-ai registry is complete and importable:** 39 providers via
  `getBuiltinProviders()`; zai `glm-5.3` record carries
  `supportsReasoningEffort:true` + `{low:"low",high:"high",max:"max"}`;
  codex luna carries `{xhigh,max,minimal:"low"}`; deepseek full compat.
  Our hardcoded codex list loses the low→minimal mapping.
- **E2 — mirror lags installed pi-ai:** mirror zai glm-5.3 map null,
  glm-5.3-flash absent; installed 0.84.3 has both. Menus degrade via
  full-list fallback (read in ChatModelControls:37-38).
- **E3 — wiring map (CF graph, complete/high):** single caller chain
  session→binding→provider; menus consume catalog shapes this plan does not
  alter; backend never imports pi-ai by design.
- **E4 — 0.85.1 diff restricted to non-consumed surfaces:** zai branch,
  detection matrix, Agent ctor, effort wire identical; changes are reasoning
  merging, SSE framing, streamDeferred refactor, cloudflare rename.
- **E5 — T1 live baseline:** luna/terra/zai-glm all serve 200 with exact
  attribution; dashscope quota dead (environmental); effort reporting fixed
  in SPEC-26 (mutation-proven), live proof pending rebuild.

## Phased task graph
| Phase | Goal | Acceptance | Verification |
|---|---|---|---|
| 1 | Inheritance in `modelCapabilities` + `thinkingLevelMap` passthrough | builtin hit → inherited; advertised overrides; fallback identical | payload tests + per-provider wire diffs |
| 2 | pi-ai 0.84.3 → 0.85.1 | suites green, no surface change | pi-runtime + backend suites + benchmark |
| 3 | QA rebuild + live T1 re-probe | effort=low reported + observed on all three | container turn logs + usage envelopes |
| 4 | Blind review + docs | independent measurement | reviewer sheet + ledger |


<!-- consensus-winning-plan:pi-compat-20260908-825cb8a8a6dd53ca201ba89199ca22f5895bbf7d51271ba18b9dfde415b45a70 -->
## Winning consensus plan — pi-compat-20260908

# Master Plan (candidate B) — Pi Compatibility Authority and the Istara Integration Boundary

**Slot:** b (MECE synthesis) · **Task:** `pi-compat-20260908-MASTER-B` · **Spec:** CF-SPEC-29
**Round:** `ac4059cd0733653e4c65` · **Phase:** S1 synthesis · **Author route:** claude-opus-5 @ effort=high
**Sources:** draft A (`gpt-5.6-sol`, effort=high) · draft B (`claude-opus-5`, effort=high) · draft C (`zai/glm-5.3-flash`, effort=max)
**Lifecycle:** `docs/build-stream/2026-09-08-pi-capability-inheritance.md`
**Scope:** planning only. No implementation is authorized by this artifact.

---

## 0. How this synthesis was made

All three drafts independently converged on the same diagnosis — Istara restates
provider knowledge that pi-ai already ships, and nothing detects divergence — and
on the same two mechanisms: **a per-field precedence law** and **a generated,
provenance-stamped projection of the pi-ai registry**. That shared core is
adopted whole.

They disagreed on four substantive points. I did not average them. I re-measured
the disputed facts in this session and resolved each on evidence (§2). Two of the
resolutions overturn a position taken in my own draft B; one overturns a position
held by two drafts against one. The measurements also exposed **one defect no
draft caught** (§3, S-E3), which changes an acceptance criterion draft B had
written as achievable.

§13 is the coverage matrix showing where every major draft insight landed.

---

## 1. Thesis and the authority law

### 1.1 Thesis

Istara has no *authority model* for provider knowledge. Capability facts live in
three places that drift independently — a hand-written `modelCapabilities()` in
`pi-runtime/src/provider.mjs`, a static JSON mirror under
`backend/app/core/pi_runtime/data/`, and pi-ai's own registry that never reaches
the worker's synthetic model record — and no test detects the divergence.

The consequence is not cosmetic. Measured: a Codex endpoint **cannot reach
`xhigh` or `max`**; a Z.AI endpoint **never transmits `reasoning_effort`**; the
mirror's effort menus are wrong for **976 of 1,307** models; and the suite
currently **pins two of these defects as expected behavior**.

The fix is one rule, applied per field:

> **pi-ai's generated registry is the sole authority for provider/model
> capability semantics.** Istara may inherit it, *restrict* it with operator or
> deployment truth pi-ai cannot know, or *project* it into a generated,
> version-stamped artifact for consumers that must not import pi-ai. Any fourth
> statement of provider knowledge is architecture debt and fails the
> `architecture_drift` gate.

### 1.2 The precedence law (per field, never per record)

Tiers 1–3 may only **restrict** tier 4; they may never silently *enable* a
capability pi-ai denies. Tiers 5–6 apply **only** when tier 4 misses.

| Tier | Layer | Owns | May |
|---|---|---|---|
| **1** | Istara safety overlay | authorization, secret custody, budget fail-closed, monotonic safety flags | restrict only |
| **2** | Endpoint / operator override | contract pricing, per-endpoint caps, `supports_reasoning:false`, base URL, credentials, timeouts | restrict; own its exclusive fields outright |
| **3** | Catalog advertised restriction | `supports_vision:false`, narrower limits | restrict only |
| **4** | **pi-ai canonical record** | `api`, `reasoning`, `thinkingLevelMap`, `compat`, `input`, headers, sampling defaults, list price, window defaults | **authority** |
| **5** | Istara identity fallback | governed custom providers (`dashscope`), gateway-URL → provider family, `thinkingFormat` naming | applies on tier-4 miss |
| **6** | pi-ai `detectCompat()` URL sniffing | last-resort detection | applies on tier-5 miss |

Today's effective order is **2 → 5 → 6 with tier 4 entirely absent.** Inserting
tier 4 is the change. It is strictly additive: any `(pi_provider, model)` pair
pi-ai does not know keeps byte-identical behavior — which is why AC-1 can demand
byte equality rather than "no observed regression".

Per-field merge mirrors pi-ai's own discipline: `getCompat()` already merges
`model.compat` over `detectCompat()` field by field, so an operator can veto one
flag without discarding the rest of the upstream record.

**Restriction is monotonic and tri-state-preserving.** An explicit `false` is not
the same as an absent value; `null`, `false`, and *unset* must survive the whole
path (catalog → endpoint POST/sparse PUT → bind → worker) without collapsing.

---

## 2. Resolved architectural conflicts

Each resolution names the drafts on each side, the deciding evidence, and what
was given up.

### DEC-M1 — Where the authority is read: **dual path, one derivation, proven equivalent**

*A and C:* runtime `getBuiltinModel()` lookup in the worker.
*B:* generator only; a `capability` descriptor persisted on the endpoint record
and couriered across the boundary; runtime import rejected on measured cost
(67 ms / 60 MB for `providers/all`).

**Resolved: adopt the runtime lookup in the worker *and* the generated
projection for every other consumer, derived by the same functions and held
equal by a conformance test.** B's persisted descriptor is rejected.

Deciding evidence:

- The 67 ms / 60 MB is a **once-per-worker-process** cost (dynamic import is
  module-registry cached), not per turn. The worker is a supervised per-session
  process. B's draft weighed it as if it recurred; it does not.
- A's operational argument is decisive and unanswered by B: a persisted
  descriptor **goes stale the moment the pin moves**, requiring every stored
  endpoint to be re-resolved or hand-edited on each bump. A runtime lookup
  re-resolves at bind, so a bump needs no data migration. That directly serves
  the initiative's actual goal.
- The descriptor is **new untrusted input crossing a trust boundary** — a risk
  B itself recorded (its R6) and then had to mitigate with a validator. Deleting
  the descriptor deletes the risk and the validator.
- B's strongest point survives and is kept: a runtime lookup alone **fixes only
  the worker**, leaving the menus, the cost ceiling, and the catalog validator
  reading a hand-maintained file. The generator fixes those. Both are needed;
  they are not alternatives.
- B's invariant "the backend never imports pi-ai" (lifecycle E3) is preserved
  exactly, because the backend reads the generated artifact, not the package.

**Given up:** the by-construction guarantee that menus and worker agree. It is
replaced by an explicit **equivalence test** (W4.1): for every model in the
projection, the projected `reasoning` / `thinkingLevels` / `thinkingLevelMap` /
`compat` must equal what the worker's resolver computes from the live registry.
Two paths, one derivation, machine-checked.

### DEC-M2 — How supported effort levels are computed: **call pi-ai; never reimplement**

*A and B:* derive via `getSupportedThinkingLevels(model)`.
*C:* "list exactly the levels whose map value is non-null when a map is present."

**Resolved in favour of A/B. C's rule is measurably wrong.** This mattered enough
to settle at the source (`node_modules/@earendil-works/pi-ai/dist/models.js:547-559`):

```js
const EXTENDED_THINKING_LEVELS = ["off","minimal","low","medium","high","xhigh","max"];
export function getSupportedThinkingLevels(model) {
  if (!model.reasoning) return ["off"];
  return EXTENDED_THINKING_LEVELS.filter((level) => {
    const mapped = model.thinkingLevelMap?.[level];
    if (mapped === null) return false;                       // explicit null  → unsupported
    if (level === "xhigh" || level === "max") return mapped !== undefined;  // opt-in only
    return true;                                             // absent → SUPPORTED
  });
}
```

The rule is asymmetric: for `off/minimal/low/medium/high`, **absent means
supported**; for `xhigh/max`, absent means unsupported. "Non-null keys" coincides
with the truth only when the map is total. Measured on live records:

| model | `thinkingLevelMap` | pi-ai supported | C's non-null rule |
|---|---|---|---|
| `zai/glm-5.3` | full, 4 nulls | `low,high,max` | `low,high,max` ✓ |
| `openai-codex/gpt-5.6-luna` | `{xhigh,max,minimal}` | **all 7** | `xhigh,max,minimal` ✗ |
| `anthropic/claude-opus-4-7` | `{xhigh,max}` | **all 7** | `xhigh,max` ✗ |
| `zai/glm-4.7` | **undefined** | `off,minimal,low,medium,high` | **`[]`** ✗ |

C's rule is wrong in 3 of 4 cases and catastrophically wrong for the mapless
majority (it would offer *no* levels). This also confirms draft B's B-E5: the
committed mirror stores non-null map keys, which is why 976 models advertise the
wrong menu — a wrong *definition*, not mere staleness.

**Binding consequence:** the emitted `thinkingLevels` array is produced by
calling pi-ai's own function. Neither Python nor TypeScript may reimplement the
filter. A hand-rolled copy of this predicate anywhere in the tree is an
`architecture_drift` finding.

### DEC-M3 — Cost authority: **pi-ai owns list price; the operator owns contract price; neither alone fixes budget integrity**

*A:* operator contract rates always override; never replace negotiated rates.
*B:* regenerate all 188 cost fields from pi-ai (owner sign-off required).
*C:* do **not** inherit cost at all; keep pricing operator/backend-resolved.

**Resolved: A's rule, with B's regeneration, plus a new mechanism both missed.**
pi-ai is authority for *list* price (tier 4); operator contract pricing is a
tier-2 override that always wins. Regeneration therefore fixes stale list rates
without ever overwriting a negotiated rate. C's "don't inherit at all" is
rejected because it preserves the zero-priced mirror entries that fail budgeted
runs closed today.

But regeneration is **not sufficient**, and this is the gap (§3, S-E3):
**119 of 1,312 upstream models are themselves zero-priced in pi-ai**, including
`zai/glm-5.3` — the exact model in the live probe set. Draft B's AC-6 ("a
budgeted run on a zai endpoint does not fail `cost_budget_unpriced`") is
**unachievable by regeneration alone** and is rewritten accordingly (AC-6 below).
The plan therefore adds an **admission-time pricing preflight** (W3.4) rather
than leaving the failure to surface mid-run.

### DEC-M4 — Version-bump ordering: **bump last, behind the conformance machinery, diff-proof first**

*A:* pin 0.85.1 in W1, before the resolver, to establish one version boundary.
*B and C:* bump after the seam and fixtures exist.

**Resolved in favour of B/C, incorporating A's lockstep requirement and C's
diff-proof step.** The bump is scheduled as W6. The reasoning is the
initiative's own goal: the deliverable is that *a bump is routine*. Bumping
before the fixtures exist means reading the 0.85.1 diff against a **known-broken**
baseline, so a genuine upstream change and one of our three present-tense defects
are indistinguishable. After W4, the catalog diff and the fixture diffs *are* the
compatibility report.

A's lockstep insight is adopted and is load-bearing: `@earendil-works/pi-ai` and
`@earendil-works/pi-agent-core` must move together, across **both** bundled
surfaces (`pi-runtime` **and** `labs/pi-replacement`), or
`tests/pi_migration/test_version_provenance.py` fails. C's "diff the consumed
`dist/` surfaces before the pin lands" becomes W6.1.

**Owner option preserved (DEC-O4):** W1–W5 are corrections to present-tense
defects on the *pinned* version and are independently shippable. W6 may ship in
this initiative or as a follow-on. Recommendation: **same initiative**, gated on
W6.1 — if the diff-proof shows a consumed surface changed, split the bump out
rather than weakening the fixtures to accommodate it.

---

## 3. Measured ground truth

Union of the three drafts' evidence, de-duplicated, with disputed claims
re-measured in this session. Environment: `pi-runtime/node_modules`,
`@earendil-works/pi-ai@0.84.3`, `@earendil-works/pi-agent-core@0.84.3`, node v26,
registry `generatedAt` `1787569009141`. All commands re-runnable from the repo.

### 3.1 Confirmed by more than one draft (adopted)

| # | Fact | Sources |
|---|---|---|
| **G1** | Registry: **39 providers / 1,312 models**; `getBuiltinProviders` / `getBuiltinModel` / `getBuiltinModels` / `getBuiltinModelDataGeneratedAt` export from **`@earendil-works/pi-ai/providers/all`**, *not* the package root. `getBuiltinProviders()` returns an array of provider **id strings**. | A, B, C |
| **G2** | `provider.mjs` hand-lists Codex/DeepSeek/Qwen/Zai behavior and builds a synthetic model record; pi-ai's registry never participates. It does **not** pass `thinkingLevelMap`. | A, B, C |
| **G3** | `thinkingLevels` is a **dead field** in pi-ai 0.84.3 and pi-agent-core 0.84.3 — the `Model` type declares `thinkingLevelMap`. Istara sets the field pi-ai never reads. | B (A concurs on the map) |
| **G4** | Codex is **inverted, not merely lossy**: with no map, `xhigh` and `max` clamp to `high`. Also dropped: `supportsOpenAIGrammarTools`, `supportsAdditionalTools`, `supportsToolSearch` — which select `deferredToolsMode`, so tool encoding differs structurally. | B (A/C note the map loss) |
| **G5** | Z.AI transmits **no `reasoning_effort` at all**. `detectCompat()` computes `supportsReasoningEffort: !isZai` = false, while the registry record for `glm-5.3` sets it **true**. Detection is being used as authority for a *known* model. | B |
| **G6** | `pi-runtime/test/provider-params.test.mjs` **asserts the defects as correct** (zai `:192-235`, codex `:121-131`). These must flip. | B (C anticipates fixture flips) |
| **G7** | Mirror vs registry: **81** registry models absent from the mirror, **36** stale mirror-only models, **976/1,307 wrong `thinkingLevels`**, 20 `contextWindow` mismatches, 188 cost-field mismatches. Provider/model **counts alone are not a freshness proof**. | A, B |
| **G8** | `PiCatalogModel` (`catalog.py:40`) has **no** `thinkingLevelMap` / `compat` field — the mirror cannot represent the decisive fields even if regenerated as-is. | B, C |
| **G9** | **There is no generator in the repo.** The mirror was produced by different ad-hoc scripts at different times (272 models follow rules different from the other 959). | B |
| **G10** | `labs/pi-replacement` is a **second bundled pi surface** on the same pins; `tests/pi_migration/test_version_provenance.py` asserts both. The lifecycle's "two-file revert" rollback is wrong — it leaves that test red. | A, B (C raises as Q2) |
| **G11** | The chat effort menu already consumes `thinkingLevels` (`ChatModelControls.tsx:37`); **no menu redesign is needed** — only correct data. | A, B, C |
| **G12** | `ResolvedPiEndpoint` carries `supports_vision`, but `_bind_payload()` **never sends it to the worker** — an advertised capability is silently dropped at the boundary. | A |
| **G13** | CF impact was high-confidence for the Python runtime/catalog/endpoint files and the TSX control; the **`.mjs` seed did not resolve** (low confidence). Node-side coverage requires direct call-site inventory, not graph output. | A |
| **G14** | `relay/lib/llm-proxy.mjs` `modelCapabilities` is **local-LLM detection** (LM Studio/Ollama), an unrelated concept. Out of scope — do not "unify" it. | C |
| **G15** | Baseline is green: `cd pi-runtime && npm test` → **54 pass / 0 fail**. | B (A reports 14 provider-param + 47 Python) |

### 3.2 Re-measured this session (disputes settled)

**S-E1 — `getSupportedThinkingLevels` semantics.** Source read and four live
records evaluated; see DEC-M2. Settles A/B vs C. The asymmetric absent-means-
supported / opt-in-`xhigh`-`max` rule is the reason the committed mirror is wrong
for 976 models.

**S-E2 — `zai/glm-5.3-flash` does not exist in 0.84.3.**
`getBuiltinModel('zai','glm-5.3-flash')` → `undefined`. The zai registry is
`glm-4.7, glm-5-turbo, glm-5.2, glm-5.2-highspeed, glm-5.3`.

- This **confirms drafts B and C** and **refutes lifecycle evidence E2**
  ("installed 0.84.3 has both"). The mirror's absence of `glm-5.3-flash` is
  *correct*, not drift.
- Draft A states 0.85.1 carries both `glm-5.3` and `glm-5.3-flash`. That is
  consistent — the model **arrives with the bump**. It must be verified in W6.2
  as evidence either way, never asserted from the lifecycle.
- `provider-params.test.mjs:206` builds a binding for this **non-existent id**,
  which is part of why the zai defect went unnoticed.

**S-E3 — Upstream zero-pricing (found here; missed by all three drafts).**

```
providers: 39 | total models: 1312
zero-priced upstream: 119  (reasoning-capable: 109)
zero-priced zai: zai/glm-5.2-highspeed, zai/glm-5.3,
                 zai-coding-cn/glm-5.2-highspeed, zai-coding-cn/glm-5.3
```

`zai/glm-5.3` — the live-probe model — is `{input:0, output:0, cacheRead:0,
cacheWrite:0}` **in pi-ai itself**. Regenerating the mirror cannot price it.
`session.mjs:539` (and `:420`) fail a run `cost_budget_unpriced` when
`max_cost_usd` is finite, the binding is real, and any **spent** category carries
a $0 rate. So:

- Draft B's AC-6 as written is unachievable; rewritten as AC-6 below.
- Even a "priced" model can trip this: `zai/glm-4.7` is priced `0.6/2.2/0.11`
  but `cacheWrite: 0`, so a run that writes cache fails closed.
- Therefore an **operator pricing override tier and an admission-time preflight
  are mandatory**, not optional. W3.4.

**S-E4 — Import cost is per-process, not per-turn.** `providers/all` costs
67.2 ms / 60.4 MB RSS to import (B-E7, accepted). Dynamic import is
module-registry cached, so a supervised per-session worker pays it once. This is
what reverses draft B's DEC-B1; see DEC-M1. W2 sets a measured budget for it.

### 3.3 Corrections to the lifecycle's recorded evidence

The lifecycle is the prompt, not ground truth. Recording these because plans
built on them mis-target work.

| Lifecycle claim | Corrected |
|---|---|
| E1: "39 providers via `getBuiltinProviders()`" | True, but the symbol lives at **`/providers/all`**, not the package root (root exports `clampThinkingLevel`, `getSupportedThinkingLevels`, `modelsAreEqual`). |
| E1: "codex luna carries `{xhigh,max,minimal:"low"}`; our list loses the `low→minimal` mapping" | The map is `minimal→"low"` (not `low→minimal`), and that loss is **not the headline**: `xhigh`/`max` silently clamp to `high` (G4). |
| E2: "`glm-5.3-flash` absent [from mirror], installed 0.84.3 has both" | **False for 0.84.3** — it exists in neither (S-E2). It appears in 0.85.1; verify at W6.2. |
| E2: mirror lag "degrades menus via full-list fallback" | Understated: it also breaks the **cost ceiling** and yields wrong menus for 976 models by a wrong *definition* (S-E1). |
| E5: "effort reporting fixed in SPEC-26; live proof pending rebuild" | The **reporting** side was fixed. The **transmit** side is still broken for zai (G5). A live zai re-probe will show no effort differentiation regardless of rebuild. |
| E4: "0.85.1 diff restricted to non-consumed surfaces" | A **claim to be re-proven as a task** (W6.1), not an input. |
| Rollback: "two-file revert (`provider.mjs`, `package.json`+lockfile)" | Misses `labs/pi-replacement` (G10). |
| Phase table: "Phase 1 inheritance, Phase 2 bump" | Bumping before conformance exists reads the diff against a broken baseline (DEC-M4). |

---

## 4. The compatibility surface

Traced end to end, not taken from the lifecycle's list.

```
pi-ai registry (39 providers / 1312 models)
   │
   ├──[W2] runtime authority ─── lazy import once per worker process
   │                             getBuiltinModel(pi_provider, model)  → tier 4
   │                                          │
   │                                          ▼
   │                             provider.mjs resolver: tiers 1-3 restrict,
   │                             5-6 on miss → effective model + receipt
   │                                          │
   │                             pi-ai adapters (openai-completions /
   │                             openai-codex-responses / anthropic-messages)
   │                                          │
   │                                          ▼  wire payload   [W4 fixtures]
   │                             session.mjs cost ceiling        [W3.4]
   │                             usage_ledger / telemetry        [W5]
   │
   └──[W1] maintenance-time projection ── emit-catalog.mjs
                     │
                     ▼
        backend/.../data/pi_models_catalog.json  (+ __provenance)
        backend/.../data/custom_providers/dashscope.json  (governed, hand-owned)
                     │
                     ├─► catalog.py  load_catalog / PiCatalogModel  [+ thinkingLevelMap, compat]
                     ├─► endpoint_policy.py  _apply_catalog_fields → endpoint record + rates
                     │        └─► PiApiEndpoint → engine.py _bind_payload  [+ vision, G12]
                     ├─► settings.py /api/settings/pi/catalog → frontend/src/lib/modelCatalog.ts
                     │        ├─ ChatModelControls.tsx:37   effort menu
                     │        └─ PiModelManagement.tsx:596  badge
                     └─► chat.py validate_model_effort ← llm_thinking.py  [W5.1]

   [W4.1] equivalence test binds the two paths: projection ≡ resolver(registry)
```

**Also in the surface, and dispositioned:**

- **`labs/pi-replacement`** — second bundled pi surface; lockstep pins (G10). In
  scope for W6 only.
- **`embeddings_gateway.py` / `embedding_profile.py`** — separate pi surface with
  its own model assumptions. **Read-only conformance check** (W4.5); not modified.
- **`relay/lib/llm-proxy.mjs`** — unrelated local-LLM detection (G14). Untouched.
- **`oauth.py` (820 lines) + `catalog.py`'s `_OAUTH_PROVIDERS` / `_API_KEY_PROVIDERS`**
  — hand-list 39 providers' auth flows and env vars, duplicating
  `builtinProviders()[].auth`. **The same defect class**, deliberately deferred
  (§11) because it touches credential custody; the generator is positioned to
  emit it in a follow-on.

---

## 5. Design

### 5.1 W1 — The generator and the generated projection

**New:** `pi-runtime/scripts/emit-catalog.mjs` — dev-time Node script, the
**only** importer of pi-ai outside the worker.
**New:** `scripts/generate_pi_catalog.py` — operator entry point; invokes the
emitter, writes the JSON, prints a drift summary. Supports `--check`.

Per model, emitted verbatim from the record plus one derived field:

```jsonc
{
  "id": "glm-5.3", "name": "GLM-5.3", "api": "openai-completions",
  "contextWindow": 1000000, "maxTokens": 131072,
  "reasoning": true, "input": ["text"], "cost": { /* list price, tier 4 */ },
  "thinkingLevels": ["low","high","max"],          // getSupportedThinkingLevels(record) — pi-ai computes it (DEC-M2)
  "thinkingLevelMap": {"off":null, ..., "max":"max"},   // NEW — the authority field
  "compat": {"supportsReasoningEffort":true, "thinkingFormat":"zai", ...}  // NEW — verbatim
}
```

Plus a provenance header the file does not have today:

```jsonc
"__provenance": {
  "pi_ai_version": "0.84.3",
  "pi_ai_generated_at": 1787569009141,
  "emitted_at": "<utc>",
  "emitter_sha256": "<sha256 of emit-catalog.mjs>",
  "model_field_set_hash": "<hash of the union of emitted model keys>",
  "governed_custom_providers": ["dashscope"]
}
```

`model_field_set_hash` (draft A) is what makes a *new upstream field* visible at
bump time instead of being silently inherited.

**Governed custom providers are preserved, not regenerated.** `dashscope` (40
models, absent from pi-ai) moves to
`backend/app/core/pi_runtime/data/custom_providers/dashscope.json`, hand-owned
and merged by the emitter. The boundary between upstream truth and Istara's
governed addition becomes a **file boundary** instead of an invisible convention,
and a future regeneration cannot delete it. The merge rejects provider/model
collisions, unknown schema fields, non-canonical ordering, and any custom record
lacking a wire fixture.

Auth/OAuth metadata, env-var names, and secret custody stay in Istara code —
they are product/security policy, not pi-ai model knowledge.

Measured cost: the mirror grows **544 KB → 892 KB (+63.9%)**, 27,977 → 39,407
lines. Accepted for auditability; §10 R4 records the slimmer alternative and the
measurement that would trigger it.

### 5.2 W2 — The runtime capability resolver

In `pi-runtime/src/provider.mjs`, a **pure resolver** consumed by
`buildRealProvider()`:

1. lazy `import("@earendil-works/pi-ai/providers/all")`, **once per worker
   process**, behind a memoised accessor (S-E4);
2. one exact, guarded `getBuiltinModel(pi_provider, model)` — **no fuzzy
   matching**;
3. on a hit, seed from the complete reviewed record and apply §1.2 field by
   field;
4. on a miss, delegate to a **separately exported** `legacyIdentityCapabilities()`
   holding today's tiers 5–6 **moved verbatim**;
5. return the effective model **plus a content-free receipt**.

`buildRealProvider` sets `thinkingLevelMap` on the model and **stops setting the
dead `thinkingLevels`** (G3). pi-ai's own `clampThinkingLevel` then does the
mapping and filtering at stream time — including Codex `minimal → "low"` — so
Istara never pre-maps provider strings in Python, TypeScript, or the worker.

Retained from tier 5 as a **default under** tier 4: `isCustomOpenAICompat`'s
`supportsDeveloperRole:false` rule. If the inherited `compat` names
`supportsDeveloperRole`, the inherited value wins; otherwise the URL rule fills
it. This preserves the DashScope/DeepSeek `developer`-role fix exactly.

A builtin/endpoint **transport disagreement** (`api` vs configured
`provider_kind`) is a typed rejection **before any network I/O**, unless a named,
fixture-backed proxy exception authorizes it (draft A).

**The receipt** — content-free, allowlisted:

```text
capability_source = pi_builtin | governed_custom | legacy_identity | legacy_detection
pi_ai_version, registry_generated_at
pi_provider, model, api, reasoning, supported_pi_levels
applied_override_names, fallback_reason
```

Never log URLs, headers, credential handles, prompts, responses, or endpoint
fingerprints. The receipt is **observability evidence only** — not report
evidence, and not a positive self-improvement signal.

### 5.3 W3 — Carry-through and budget integrity

- `PiCatalogModel` gains optional `thinkingLevelMap` and `compat`; the loader and
  the settings/chat catalog API pass them through (G8).
- Frontend types gain the optional fields. The effort menu consumes the emitted
  `thinkingLevels` **as given** — it must not reimplement the filter (DEC-M2).
- `_bind_payload()` forwards the effective advertised restrictions **including
  the currently dropped vision/input signal** (G12), and continues to exclude
  auth metadata and all secrets.
- Tri-state (`null` / `false` / unset) is preserved across POST and **sparse
  PUT**; existing endpoints stay readable and are **re-resolved at bind time**,
  so a pin bump needs no hand-editing and no migration (DEC-M1).
- **Pricing preflight (S-E3).** Endpoint admission validates that an endpoint
  intended for budgeted runs carries a positive rate for every category it can
  spend in, sourced from tier 2 (operator contract price) where tier 4 is $0.
  Failure is a clear admission-time error naming the unpriced categories. The
  mid-run `cost_budget_unpriced` terminal **remains** as defense in depth.
- Authorization is unchanged: endpoint mutation stays admin-only, project chat
  catalog access stays project-scoped, identity views stay secret-free.

### 5.4 W4 — Conformance: make drift unmergeable

Four mechanisms, each closing a different escape route:

1. **Equivalence test** (DEC-M1, new to this synthesis) — for every model in the
   projection, projected `reasoning` / `thinkingLevels` / `thinkingLevelMap` /
   `compat` equals what the resolver computes from the live registry. Proves the
   two read paths are one function of one pin.
2. **Round-trip drift test** — `tests/pi_compat/test_catalog_conformance.py`
   regenerates into a temp dir and asserts the committed file is byte-identical,
   and that `__provenance.pi_ai_version` equals the `package.json` pin. **A bump
   without regeneration fails CI.** Absent `node_modules` yields a typed
   `not_runnable`, never a silent skip (AGENTS.md).
3. **Wire-payload fixtures** — `pi-runtime/test/capability-inheritance.test.mjs`,
   table-driven over `(provider, model, level)`, capturing the real request body
   through a stub fetch. Two classes:
   - **fallback** (dashscope, unknown proxy URL, legacy binding): asserted
     **byte-identical to fixtures captured in W0, before W2 lands**. This is the
     proof that the change is additive.
   - **inherited** (zai, deepseek, qwen, codex, anthropic): asserted against the
     *corrected* payloads. This is where G6's two tests flip, each flip citing
     its evidence in-file and in the ledger.
4. **Field-set diff** — `model_field_set_hash` changes must be classified before
   a pin advances (§8 taxonomy).

### 5.5 W5 — Observability, validation, and the user journey

- `validate_model_effort` / `normalize_model_effort` gain an **allowlist** against
  pi-ai's ladder (`off|minimal|low|medium|high|xhigh|max` + `server_default`).
  Today `thinking_mode:"banana"` passes the API validator and is silently clamped
  to the lowest supported level. It becomes `unsupported_model_effort`.
- `capability_source` is emitted on the existing `pi_provider_turn` span
  (`engine.py:623`) — the single observable answering "which tier served this
  turn?", today unanswerable.
- `effort_clamped{requested, served}` is emitted whenever a level is clamped.
  *"Never silent wrongness"* is the lifecycle's own principle; this makes it
  enforceable.
- **UI suite (AGENTS.md Full UI Testing Suite Contract).** The effort-selection
  journey currently has **zero** coverage — `grep -rn "effort\|thinking"` across
  `10-settings-models.mjs`, `05-chat-interaction.mjs`,
  `26-model-session-persistence.mjs` returns nothing. Extend `10-settings-models`
  (badge reflects the model's real level count; an inherited-map model *and* a
  mapless model) and `05-chat-interaction` (open the menu, select a non-default
  level, send, assert persistence). Real browser acts, admin/researcher/viewer/
  stranger, light/dark, 375 px reflow, keyboard Tab with visible focus, loading/
  error/empty, synthetic data only, dated verdict in
  `tests/simulation/lib/scenario-registry.mjs`.

### 5.6 The routine-bump contract (the actual deliverable)

```bash
cd pi-runtime            && npm i @earendil-works/pi-ai@X @earendil-works/pi-agent-core@X
cd ../labs/pi-replacement && npm i @earendil-works/pi-ai@X @earendil-works/pi-agent-core@X
python scripts/generate_pi_catalog.py                 # regenerate; prints the drift summary
git diff --stat backend/app/core/pi_runtime/data/pi_models_catalog.json   # ← the compatibility report
cd pi-runtime && npm test                             # payload fixtures show every wire change
pytest tests/pi_compat tests/pi_migration -q          # equivalence + drift + provenance
# update EXPECTED_PINS, classify every diff (§8), review, ship
```

Five commands and a reviewed diff. Everything in W1–W5 exists to make this true.

---

## 6. Waves and tasks

Strict waves. Each completes, passes independent review, and converges through
remediation before its successor starts. Implementation begins only after the
winning plan receives **owner approval**.

### W0 — Freeze the baseline and replace the execution contract *(no product code)*

| # | Task | Output |
|---|---|---|
| 0.1 | Revise **CF-SPEC-29** to the owner-approved total-compatibility scope; encode §1.2 as the authority contract; supersede the narrow task set; create W1–W7 dependency edges and role work orders | accepted spec |
| 0.2 | Refresh CF and run native impact across runtime/catalog/endpoint/chat/validation/autoresearch/donor-routing/telemetry/Research Spine. Record the `.mjs` low-confidence gap (G13); compensate with `rg` call-site inventory + Node test ownership — **never** a legacy CF fallback | impact record |
| 0.3 | Capture **pre-change** wire fixtures on current code: dashscope, unknown proxy, legacy no-capability binding, deepseek, qwen, codex, zai — every supported level | `pi-runtime/test/fixtures/wire/pre-change/*.json` |
| 0.4 | Capture pre-change normalized model records, error/fallback classification, developer-role, vision, limits, pricing, identity receipts, catalog IDs | baseline artifacts |
| 0.5 | Commit the drift report (G7 + S-E2 + S-E3) as a dated artifact | `docs/build-stream/pi-compat-20260908-drift-report.md` |
| 0.6 | Passive audit of every configured endpoint: exact builtin hit, transport mismatch, fallback source. **Counts and stable endpoint IDs only** — never read or print secrets or private URLs | disposition list |

**Gate:** reviewed authority contract; expanded CF coverage with no drift; green
baseline; fixtures reproducible **twice with identical bytes**; an explicit
disposition for every transport mismatch. **Rollback:** artifact deletion only.

### W1 — Generator, projection, provenance, governed overlay

| # | Task | Files |
|---|---|---|
| 1.1 | `emit-catalog.mjs`: walk the registry, emit `thinkingLevelMap` + `compat` verbatim and `thinkingLevels` via **pi-ai's own** `getSupportedThinkingLevels` (DEC-M2) | `pi-runtime/scripts/emit-catalog.mjs` |
| 1.2 | Extract `dashscope` to a governed custom-provider file; emitter merges it; collision/schema/order rejection | `backend/.../data/custom_providers/dashscope.json` |
| 1.3 | Operator entry point with `--check` and drift summary | `scripts/generate_pi_catalog.py` |
| 1.4 | Provenance header incl. `model_field_set_hash` | projection |
| 1.5 | Regenerate the mirror; **review the 81/36 model, 20 context, and 188 cost diffs as a change, not a rubber stamp** | `backend/.../data/pi_models_catalog.json` |
| 1.6 | `PiCatalogModel` gains `thinkingLevelMap`, `compat`; serializer passes them through | `catalog.py` |
| 1.7 | All-provider parity test: every registry model appears exactly once; custom overlays identified; upstream deletions cannot pass unnoticed (**counts are not the oracle**, G7) | `tests/pi_compat/` |

**Acceptance:** menus correct for all 1,307 models; no runtime pi-ai import added
to the backend; overlay preserved across regeneration.
**Risk gate:** 1.5 changes list pricing → **owner sign-off (DEC-O2)**.

### W2 — Runtime capability resolver

| # | Task | Files |
|---|---|---|
| 2.1 | Memoised per-process registry accessor; measured import budget (S-E4) | `pi-runtime/src/provider.mjs` |
| 2.2 | Exact guarded `getBuiltinModel` lookup; §1.2 per-field merge; effective model + receipt | `provider.mjs` |
| 2.3 | Extract tiers 5–6 **verbatim** into exported `legacyIdentityCapabilities()` | `provider.mjs` |
| 2.4 | Set `thinkingLevelMap`; **stop setting dead `thinkingLevels`** (G3) | `provider.mjs` |
| 2.5 | `supportsDeveloperRole` URL rule preserved as a tier-5 default under tier 4 | `provider.mjs` |
| 2.6 | Typed pre-network rejection of builtin/endpoint transport mismatch, with the named proxy exception | `provider.mjs` |
| 2.7 | Collapse the hand-listed Codex/DeepSeek/Qwen/Zai branches; retain only custom-model exceptions that have catalog provenance **and** a wire fixture | `provider.mjs` |

**Acceptance:** AC-1, AC-2, AC-3, AC-4. No network call in any test.

### W3 — Carry-through, vision, and budget integrity

| # | Task | Files |
|---|---|---|
| 3.1 | Catalog API exposes `thinkingLevels` / `thinkingLevelMap` / `compat`; frontend types + menu consume as given | `settings.py`, `frontend/src/lib/types.ts`, `api.ts`, `ChatModelControls.tsx` |
| 3.2 | Forward the dropped vision/input signal through `_bind_payload` (G12) | `engine.py` |
| 3.3 | Tri-state preservation across POST and sparse PUT; bind-time re-resolution | `endpoint_policy.py`, `endpoints.py`, `config.py` |
| 3.4 | **Admission-time pricing preflight** (S-E3); operator contract price as tier 2; mid-run terminal retained | `endpoint_policy.py`, `session.mjs` (assert only) |
| 3.5 | Backend contract tests for carry-through and preflight | `tests/pi_production/test_engine_http_provider.py` |

**Acceptance:** AC-4, AC-6.

### W4 — Conformance, equivalence, fixtures

| # | Task | Files |
|---|---|---|
| 4.1 | **Equivalence test:** projection ≡ resolver(live registry), all models | `tests/pi_compat/test_authority_equivalence.py` |
| 4.2 | Round-trip drift test + provenance ≡ pin; typed `not_runnable` when `node_modules` absent | `tests/pi_compat/test_catalog_conformance.py` |
| 4.3 | Table-driven wire harness | `pi-runtime/test/capability-inheritance.test.mjs` |
| 4.4 | Inherited fixtures (corrected) + **flip** `provider-params.test.mjs:192-235` and `:121-131`, each justified in-file (G6) | fixtures, `provider-params.test.mjs` |
| 4.5 | Fallback fixtures asserted **byte-identical to W0**; read-only conformance check on `embeddings_gateway` assumptions | fixtures, `test_w8_embeddings_gateway.py` |
| 4.6 | Research Spine invariants: route authorization, distinct model identity, reliability, reconciliation, provisional status, human Done/report gates | targeted spine + donor/ensemble tests |

**Acceptance:** AC-1, AC-5, AC-9.

### W5 — Observability, effort validation, UI journey

| # | Task | Files |
|---|---|---|
| 5.1 | Effort allowlist against pi-ai's ladder | `llm_thinking.py`, `chat.py` |
| 5.2 | `capability_source` on the turn span | `engine.py`, `telemetry.py` |
| 5.3 | `effort_clamped{requested, served}` | `provider.mjs`, `session.mjs`, `usage_ledger.py` |
| 5.4 | Settings scenario: badge reflects real level count (mapped **and** mapless model) | `tests/simulation/scenarios/10-settings-models.mjs` |
| 5.5 | Chat scenario: select a non-default effort, send, assert persistence; full AGENTS.md matrix; registry verdict | `05-chat-interaction.mjs`, `scenario-registry.mjs` |
| 5.6 | Security benchmark (LLM-provider surface trigger); update `security/control_matrix.json` + `SECURITY_BENCHMARK.md` **only if** a control, evidence path, standard version, or trigger actually changed | `scripts/security_benchmark.py` |

**Acceptance:** AC-7, AC-8.

### W6 — Version adoption 0.84.3 → 0.85.1 *(diff-proof first; DEC-O4 separable)*

| # | Task |
|---|---|
| 6.1 | **Diff-proof before the pin lands:** install 0.85.1 to a scratch dir; diff the consumed `dist/` surfaces (`providers/all`, `providers/zai*`, `providers/openai-codex*`, `models.js`, `api/openai-completions`, `api/openai-codex-responses`, detection/retry). Re-measure the lifecycle's E4 claim. Any consumed-surface change updates fixtures **deliberately** — or splits the bump out |
| 6.2 | Verify `glm-5.3-flash` presence in 0.85.1 (S-E2); record evidence either way |
| 6.3 | **Lockstep** pin `pi-ai` + `pi-agent-core` in **both** `pi-runtime` and `labs/pi-replacement`; regenerate both lockfiles; `EXPECTED_PINS` → 0.85.1 (G10) |
| 6.4 | Regenerate the projection; **the catalog diff is the compatibility report**; classify every field-set change (§8) |
| 6.5 | Full suites + benchmark; every fixture diff justified in the ledger |

### W7 — Bounded live acceptance, release, documentation

| # | Task |
|---|---|
| 7.1 | **Owner-authorized only** (AGENTS.md *Live LLM and Model Loading Safety*). Rebuild the QA artifact from the candidate SHA. One configured target at a time; never load multiple heavy models. Bounded token ceiling, declared cost ceiling, secret-free artifacts |
| 7.2 | Fresh `low`-effort turns on luna / terra / zai-glm. Reconcile requested level → receipt → **captured request body** → served identity → usage envelope → terminal response. G5 says today's zai turn carries nothing — that is the proof point. Measure, do not assume, how 0.85.1 maps Codex `minimal`/`low` |
| 7.3 | Offline Pi benchmark suite. Any live benchmark only via immutable manifest, owner-approved budget ledger, exact DUT identity, safe-stop/resume |
| 7.4 | Independent **blind** review: catalog parity, fallback payload parity, wire behavior, UI journey, security scorecard, spine gates, artifact SHA, running container identity — measured before reading implementer claims |
| 7.5 | Docs: `docs/architecture/pi-compatibility-authority.md` (the law, the generator, the bump runbook), `CHANGELOG.md`, feature docs, `testing/TEST_HISTORY.md`, `TESTING.md` (W4 adds a suite file → **yes**), lifecycle ledger |

**Release gate:** deterministic acceptance green; live acceptance passed **or**
explicitly owner-waived with `not_runnable` evidence; the intended image and SHA
running; rollback retained. **Promotion is not equivalent to live proof.**

### 6.1 Task graph

| Task | Depends on | Blocks on failure |
|---|---|---|
| W0 spec + baseline freeze | owner approval of this plan | everything |
| W1 generator + projection | W0 | W2, W3, W4 |
| W2 runtime resolver | W0 (fixtures), W1 (provenance) | W4, W5 |
| W3 carry-through + budget | W1, W2 | W4, W5 |
| W4 conformance + equivalence | W1, W2, W3 | W5, W6 |
| W5 observability + UI | W3, W4 | W6, W7 |
| W6 version adoption | W4, W5 | W7 |
| W7 live + release | W5, W6, explicit permission | ship |

No task is complete from a package install, a passing process, an HTTP 200, a
configured label, or a non-empty response alone.

---

## 7. Acceptance criteria

- **AC-1 (additive / no regression).** *Given* an endpoint whose
  `(pi_provider, model)` is absent from the registry — dashscope, unknown proxy
  URL, or a legacy binding — *When* a turn binds at every supported level *Then*
  the captured request body is **byte-identical** to the W0 pre-change fixture.
  *Verify:* `cd pi-runtime && npm test -- capability-inheritance`.
- **AC-2 (Codex inheritance).** *Given* a Codex endpoint on `gpt-5.6-luna` *When*
  `xhigh` or `max` is requested *Then* the body carries `reasoning.effort`
  `"xhigh"` / `"max"` (today `"high"`), `minimal` maps to `"low"`, and
  `compat.supportsAdditionalTools` selects
  `deferredToolsMode:"additional-tools"`.
- **AC-3 (Z.AI inheritance).** *Given* `zai/glm-5.3` *When* `low`/`high`/`max` is
  requested *Then* the body carries `reasoning_effort` `"low"`/`"high"`/`"max"`
  (today the field is **absent**) with the `thinking` block unchanged.
- **AC-4 (operator veto, tri-state).** *Given* an endpoint with
  `supports_reasoning:false` on a reasoning-capable model *When* a turn binds
  *Then* no thinking or effort field is emitted — tier 2 beats tier 4 — and the
  explicit `false` survives POST, sparse PUT, bind, and worker.
- **AC-5 (conformance + equivalence).** *Given* a clean tree *When*
  `pytest tests/pi_compat -q` runs *Then* regeneration reproduces the committed
  file **byte-for-byte**, `__provenance.pi_ai_version` equals the pin, and for
  **every** projected model the projected capability fields equal the resolver's
  computation from the live registry. *A bump without regeneration fails CI.*
- **AC-6 (menus and budget — rewritten per S-E3).** *Given* the regenerated
  catalog *When* the effort menu renders *Then* it offers exactly
  `getSupportedThinkingLevels(record)` — seven levels for
  `anthropic/claude-opus-4-7`, `["low","high","max"]` for `zai/glm-5.3`,
  `["off","minimal","low","medium","high"]` for the mapless `zai/glm-4.7`;
  **and** *When* an endpoint on an upstream **zero-priced** model (e.g.
  `zai/glm-5.3`, one of 119) is configured for budgeted runs *Then* admission
  fails with a message naming the unpriced categories **unless** an operator
  tier-2 rate is supplied — and *When* a tier-2 rate is supplied *Then* the
  budgeted run completes without `cost_budget_unpriced`.
- **AC-7 (journey + observability).** *Given* the QA container *When* a user
  opens the effort menu, selects a non-default level, and sends *Then* the
  scenario passes across roles, light/dark, 375 px, and keyboard focus; the turn
  span carries `capability_source`; a clamp emits `effort_clamped`; and an
  unsupported effort is **rejected**, never silently clamped.
- **AC-8 (security + spine).** *Given* this LLM-provider surface change *When*
  `scripts/security_benchmark.py --fail-on-threshold` runs *Then* it passes and
  the scorecard is attached as CF evidence; no secret, URL, header, or endpoint
  fingerprint appears in any receipt or span (negative tests).
- **AC-9 (Research Spine non-bypass).** *Given* a research workflow on an
  affected route *When* it runs *Then* evidence units, distinct model identity,
  reliability/reconciliation, project route evidence, provisional status, human
  review, and Done/report gates remain non-bypassable.
- **AC-10 (bump, if W6 runs).** *Given* 0.85.1 lockstep on **both** surfaces
  *When* the full suites run *Then* all pass, `glm-5.3-flash` presence is
  recorded as evidence, and every fixture and field-set diff is classified (§8)
  in the ledger.
- **AC-11 (the deliverable).** *Given* a future pi version *When* an operator
  runs §5.6 *Then* the diff **is** the compatibility report, unclassified changes
  fail the gate, and no repository archaeology is required.

---

## 8. Change classification taxonomy

Every diff surfaced at a bump — catalog field, wire payload, or
`model_field_set_hash` — is classified before release. **An unclassified diff
fails the gate.**

| Class | Meaning | Action |
|---|---|---|
| `intended-upstream` | pi-ai deliberately changed a provider fact | update fixture, cite the upstream change in the ledger |
| `istara-fix` | the diff corrects a present-tense Istara defect | flip the fixture, cite the evidence ID |
| `blocked` | the change breaks a provider or a contract | do not ship; split into its own task |
| `unclassified` | not yet triaged | **gate failure** |

---

## 9. Exact verification ladder

Run from the repository root. Record each as CF `command` evidence.

```bash
# Runtime
cd pi-runtime && npm ci && npm test                    # baseline 54/54
cd pi-runtime && npm test -- capability-inheritance    # W4 wire diffs
cd labs/pi-replacement && npm ci && npm run validate   # second bundled surface (G10)

# Generator round-trip
python scripts/generate_pi_catalog.py
python scripts/generate_pi_catalog.py --check          # must be a no-op

# Backend
pytest -q tests/pi_compat
pytest -q tests/pi_production
pytest -q tests/pi_migration/test_version_provenance.py
pytest -q tests/pi_production/test_pi_catalog_ux.py \
         tests/pi_production/test_runtime_hardening.py \
         tests/pi_production/test_w1_dispatcher_authority.py \
         tests/pi_production/test_w7_pi_manager_integration.py \
         tests/pi_production/test_research_spine_donor_routing.py \
         tests/pi_production/test_engine_http_provider.py
pytest -q tests/test_model_source.py tests/test_pi_replacement_candidate.py
pytest -q tests/test_research_validity_contract.py     # spine unchanged
pytest -q tests/pi_benchmark/

# Frontend
cd frontend && npx vitest run src/lib/modelCatalog.test.ts
cd frontend && npx tsc --noEmit && npm run lint

# Harness / integrity / security
python scripts/check_test_harness.py
python scripts/check_integrity.py
python scripts/security_benchmark.py --fail-on-threshold

# Change / release gates
python scripts/check_feature_obligations.py --base origin/testing --head HEAD \
  --json-out artifacts/feature-obligations.json
python scripts/check_change_obligations.py --base origin/testing --head HEAD
python scripts/feature_docs.py --seed-missing --generate-site --check
pytest -q tests/test_feature_docs.py tests/test_security_benchmark.py
docker compose -f docker-compose.qa.yml --profile contract config --quiet
```

**Not authorized by this planning stage** — require explicit service/model
permission and container setup:

```bash
docker compose -f docker-compose.qa.yml --profile ui up -d     # loopback only
node tests/simulation/run.mjs --scenario 10-settings-models,05-chat-interaction
npm --prefix tests/real_user_benchmark run probe:pi
```

The final live command must name one configured endpoint, a token/cost ceiling,
an artifact directory, the candidate SHA, and the expected provider/model. **Do
not encode a private URL or token** in a command or a committed file. Execute
endpoints sequentially; preserve the safe-stop/resume artifact after each.

The feature-obligation report determines any additional suites; unknown paths
fail closed. Compare broad-suite failures against a clean checkout at the same
base SHA to separate inherited debt from regressions.

---

## 10. Risks

| # | Risk | L | Mitigation |
|---|---|---|---|
| R1 | Regenerating list prices changes when ceilings trip (188 fields; 104 increase) | High | 1.5 is an explicit owner-review step with the full diff (DEC-O2). Operator contract price stays tier 2 — the generator sets **list** rates only. |
| R2 | **119 upstream models are zero-priced**, so regeneration does not fix budget integrity (S-E3) | High | Admission-time preflight (3.4) + tier-2 operator rates + retained mid-run terminal. AC-6 rewritten to state the real condition. |
| R3 | Corrected `thinkingLevels` changes menus for 976 models; a saved `thinking_mode` may vanish | High | `ChatModelControls.tsx:269-270` already falls back to `server_default`; assert that path in 5.5. |
| R4 | Mirror grows +63.9% (544 KB → 892 KB), `asdict`-serialized per catalog request (`catalog.py:270`) | Med | Measured and accepted for auditability. **If** the API response size regresses, emit `compat` only where it differs from `detectCompat()` (~10× smaller) at the cost of auditability. Decide on measurement, not speculation. |
| R5 | A newly passed-through `compat` flag breaks a provider that Istara's narrower payload happened to satisfy | Med | Fixtures make every field change visible per provider before ship; W7 bounded live probe; rollback is per-field via a tier-2 endpoint override. |
| R6 | Flipping two asserted-correct tests looks like weakening the suite | Med | Each flip cites its evidence in-file and in the ledger; the byte-identical fallback fixtures **strengthen** the suite in the same commit (DEC-O3). |
| R7 | Per-process registry import (67 ms / 60 MB) regresses worker startup | Med | Memoised, once per worker process (S-E4); 2.1 sets a measured budget and asserts it. |
| R8 | Registry misses a production model | Med | Exact lookup only; governed overlay is a file boundary; fallback receipt; catalog diff blocks silent deletion. |
| R9 | Full-record inheritance silently introduces a new upstream field | Med | `model_field_set_hash` must be classified (§8) before the pin advances. |
| R10 | Endpoint transport conflicts with the builtin `api` | Med | Typed pre-network rejection; named proxy exception requires a fixture. |
| R11 | pi-ai relocates or renames `providers/all` | Low | Two importers only (generator + memoised worker accessor); a rename fails loudly at bump time — the desired mode. |
| R12 | 0.85.1 changes semantics the fixtures then pin as "expected" | Low | W6 runs **after** W4, and 6.1 diff-proofs the consumed surfaces **before** the pin lands. |
| R13 | Telemetry leaks endpoint or server identity | Low | Fixed content-free receipt allowlist + secret/URL/header negative tests (AC-8). |
| R14 | Shared worktree carries unrelated changes | Low | Isolate wave paths and commits; never `git add -A`; compare against the selected base. |
| R15 | CF `.mjs` impact stays low confidence (G13) | Low | Record the limitation; require direct call-site inventory and Node test ownership. Never use a legacy CF fallback. |

---

## 11. Explicitly out of scope (named, not silently dropped)

- **OAuth / auth-metadata inheritance.** `catalog.py`'s `_OAUTH_PROVIDERS` /
  `_API_KEY_PROVIDERS` hand-list 39 providers' flows and env vars, duplicating
  `builtinProviders()[].auth` — **the same defect class**. Deferred deliberately:
  it touches credential custody and `oauth.py` (820 lines), and folding it in
  would make this delivery security-sensitive end to end. Recorded as
  architecture debt; the generator is positioned to emit it in a follow-on
  (DEC-O5).
- **`relay/lib/llm-proxy.mjs`** — unrelated local-LLM detection (G14).
- **`embeddings_gateway`** — verified read-only in W4.5, not modified.
- Provider additions, product redesign, Research Spine changes, unbounded live
  spend.

---

## 12. Rollback and terminal states

No database migration and no schema migration at any wave. Rollback per wave:

- **W1:** revert the generator + regenerated projection. The projection has no
  reader outside `catalog.py`; reverting restores today's behavior exactly.
- **W2:** revert `provider.mjs`. Because nothing is persisted, there is no stale
  state to unwind.
- **W3:** revert the backend/frontend diff together. Added config fields have
  defaults, so previously serialized endpoints stay valid.
- **W4/W5:** tests and telemetry only.
- **W6:** `git checkout <sha> -- pi-runtime/package*.json labs/pi-replacement/package*.json`
  then `npm ci` in **both** surfaces, then `generate_pi_catalog.py --check`.
  *(This is the correction to the lifecycle's "two-file revert", which leaves
  `test_version_provenance.py` red — G10.)*

The previously accepted image/digest stays available until live acceptance
closes. Allowed terminal states are explicit:

- **deterministic complete, live pending** — offline and container gates pass; no
  claim about provider behavior is made;
- **not_runnable** — missing permission, quota, credential, or provider; exact
  blocker and resume command recorded;
- **rolled back** — prior pins/image restored and baseline reverified;
- **accepted** — deterministic, UI, security, spine, artifact identity, and
  required live evidence all reconcile; the owner approves promotion.

---

## 13. Coverage matrix

Where each draft's substantive contribution landed. `†` = adopted over a
conflicting position; `✗` = rejected with recorded reasoning.

| Insight | Source | Landed in |
|---|---|---|
| Per-field precedence law, restriction-only tiers | **A** (4-tier table) + **B** (precedence law) + **C** (L1–L4) | §1.2 — merged into one 6-tier table |
| Generated, provenance-stamped projection as the seam for non-worker consumers | **B** (core), **A** (generator + `--check`), **C** (regeneration + stamp) | §5.1, W1 |
| Runtime `getBuiltinModel()` at bind time † | **A**, **C** (over B's descriptor) | DEC-M1, §5.2, W2 |
| Persisted `capability` descriptor across the boundary ✗ | **B** | DEC-M1 — rejected (stale on bump; new untrusted input) |
| `getSupportedThinkingLevels` is the only correct derivation † | **A**, **B** (over C's non-null rule) | DEC-M2, measured S-E1 |
| "Non-null map keys" menu rule ✗ | **C** | DEC-M2 — rejected, wrong in 3 of 4 measured cases |
| `thinkingLevels` is a dead field pi-ai never reads | **B** | G3, task 2.4 |
| Codex `xhigh`/`max` clamp to `high`; `compat` tool flags dropped | **B** | G4, AC-2 |
| Z.AI transmits no `reasoning_effort`; detection wrongly used as authority | **B** | G5, AC-3 |
| Two suite tests pin the defects as correct; flip with justification | **B** (**C** anticipated fixture flips) | G6, task 4.4, DEC-O3 |
| Quantified mirror drift; counts are not a freshness proof | **A**, **B** | G7, task 1.7 |
| `PiCatalogModel` cannot represent the decisive fields | **B**, **C** | G8, task 1.6 |
| pi-ai owns **list** price; operator owns **contract** price † | **A** (over B's full replacement and C's no-inheritance) | DEC-M3 |
| Upstream zero-pricing defeats regeneration; admission preflight needed | **synthesis** (missed by all three) | S-E3, task 3.4, AC-6, R2 |
| Bump last, behind conformance † | **B**, **C** (over A's bump-first) | DEC-M4, W6 |
| Lockstep `pi-ai` + `pi-agent-core` across **both** bundled surfaces | **A**, **B** (**C** as open question) | G10, task 6.3, §12 |
| Diff-proof consumed `dist/` surfaces **before** the pin lands | **C** | task 6.1 |
| `glm-5.3-flash` absent from 0.84.3 — lifecycle E2 is wrong | **B**, **C**, re-measured | S-E2, task 6.2 |
| Byte-identical fallback fixtures captured **pre-change** as the additivity proof | **B**, **C** (**A** as frozen baseline) | W0.3, AC-1 |
| Governed custom providers as a **file boundary**, not a convention | **B** (**A** as reviewed overlay) | §5.1, task 1.2 |
| Content-free capability receipt / `capability_source` | **A** (receipt schema), **B** (span field) | §5.2, task 5.2 |
| `effort_clamped` — never silent wrongness | **B** | task 5.3 |
| Effort allowlist; `"banana"` currently passes the validator | **B** | G-corr, task 5.1 |
| `supports_vision` dropped at `_bind_payload` | **A** | G12, task 3.2 |
| Tri-state (`null`/`false`/unset) preservation through sparse PUT | **A** | task 3.3, AC-4 |
| Typed pre-network transport-mismatch rejection + named proxy exception | **A** | task 2.6, R10 |
| `model_field_set_hash` makes new upstream fields visible | **A** | §5.1, R9, §8 |
| Change-classification taxonomy (intended / fix / blocked) | **A** | §8 |
| CF `.mjs` impact gap; compensate with call-site inventory | **A** | G13, task 0.2 |
| Passive endpoint audit, IDs and counts only | **A** | task 0.6 |
| Equivalence test binding the two read paths | **synthesis** (forced by DEC-M1) | task 4.1, AC-5 |
| Zero UI coverage for the effort journey; AGENTS.md matrix | **B** (**A**, **C** extend scenarios) | §5.5, W5.4–5.5 |
| Research Spine invariants as an explicit gate | **A** (**B**, **C** assert non-impact) | task 4.6, AC-9 |
| Bounded, owner-gated live probe; one target at a time | **A**, **B**, **C** | W7 |
| `relay` `modelCapabilities` is unrelated — do not unify | **C** | G14, §11 |
| OAuth/env-var duplication is the same defect class; defer explicitly | **B** | §11, DEC-O5 |
| Blind independent review before reading implementer claims | **A** | task 7.4 |
| Routine-bump runbook as the actual deliverable | **B** (**A** update procedure, **C** runbook) | §5.6, AC-11 |
| Explicit terminal states (`not_runnable` never a silent skip) | **A** | §12 |

---

## 14. Decisions requested of the owner

Implementation is blocked on these; none is authorized by DEC-2.

- **DEC-O1 — Authority read point.** Approve the **dual path**: runtime
  `getBuiltinModel()` in the worker for binding, plus the generated projection
  for catalog/menus/pricing, held equal by the W4.1 equivalence test. This
  reverses draft B's DEC-B1 on the measured grounds in DEC-M1.
- **DEC-O2 — Pricing regeneration.** Approve replacing 188 mirror cost fields
  with pi-ai **list** rates (104 increase), confirming that operator/contract
  pricing remains a tier-2 override. **Note S-E3:** this does *not* by itself fix
  zero-priced models; DEC-O2 travels with the admission preflight (3.4).
- **DEC-O3 — Test flips.** Approve flipping the two tests that assert the
  divergent behavior as correct (`provider-params.test.mjs:192-235`, `:121-131`),
  each justified in-file and in the ledger.
- **DEC-O4 — W6 separability.** Confirm whether 0.85.1 ships with W1–W5 or as a
  follow-on. **Recommendation: same initiative, gated on the 6.1 diff-proof** —
  split it out if a consumed surface changed.
- **DEC-O5 — Auth-inheritance deferral.** Confirm §11's deferral of OAuth /
  env-var inheritance to a separate, security-gated delivery.
- **DEC-O6 — Live-probe authorization.** W7 requires explicit permission, one
  configured target at a time, with declared token and cost ceilings. Nothing in
  W0–W6 spends.

---

*Prepared by architect slot B (claude-opus-5, effort=high) as the MECE master-plan
synthesis for CF task `pi-compat-20260908-MASTER-B`, round
`ac4059cd0733653e4c65`, from the immutable snapshots of drafts A, B, and C.
Disputed facts were re-measured on 2026-09-08 against
`@earendil-works/pi-ai@0.84.3` in `pi-runtime/node_modules`, node v26, and are
re-runnable from the repository root. The conductor must stop at the
winning-plan owner-approval gate; this artifact authorizes no implementation.*

<!-- /consensus-winning-plan:pi-compat-20260908-825cb8a8a6dd53ca201ba89199ca22f5895bbf7d51271ba18b9dfde415b45a70 -->

## Decision log

<!-- consensus-winner-decision:pi-compat-20260908-825cb8a8a6dd53ca201ba89199ca22f5895bbf7d51271ba18b9dfde415b45a70 -->
DEC-consensus-winner | 2026-09-08 | S1-plan | conductor
Context: three architect cross-votes completed
Decision: slot b selected from pi-compat-20260908-MASTER-B
Why: votes={"a": {"candidate_id": "f2be3452af887bea5e0ee729b62bedf973b411b22c98b9f1142199a26dd86609", "task": "pi-compat-20260908-VOTE-A", "vote": "b"}, "b": {"candidate_id": "6f928974f42da70a7ac7e86f86c93eafe32ba09df6340e4a23025926f0eb193a", "task": "pi-compat-20260908-VOTE-B", "vote": "c"}, "c": {"candidate_id": "f2be3452af887bea5e0ee729b62bedf973b411b22c98b9f1142199a26dd86609", "task": "pi-compat-20260908-VOTE-C", "vote": "b"}}; tiebreak_used=False; plan_file=docs/build-stream/pi-compat-20260908-master-b.md


- **DEC-1 | pending | S0 | owner** — Awaiting approval for: (a) new-default
  semantics (unknown providers get detection, not hard-off), (b) 0.85.1 bump
  in the same change, (c) inheritance-over-duplication as the standing rule
  for provider knowledge.
- **DEC-2 | approved | S1 | owner | 2026-09-08T07:01:43Z** — The owner
  approved expanding the frame from the narrow inheritance/version-bump pass
  to total Pi compatibility and an efficient, sound, upstream-update-friendly
  Istara integration. The existing evidence and descriptions remain inputs,
  not an exhaustive task list. Three distinct architects must discover,
  synthesize, and cross-vote the complete dependency-ordered plan. This
  approval authorizes planning only; implementation remains behind the
  conductor's winning-plan approval gate.

## Findings register — Phase 1 wave `authority-and-boundary`

| ID | Severity | Where | Finding | CF task | Status |
|----|----------|-------|---------|---------|--------|
| F-1 | Blocker | `pi-runtime/src/provider.mjs` (`resolveCapabilities` transport gate) + `backend/app/core/pi_runtime/endpoint_policy.py` | `provider_transport_mismatch` makes 346/1352 catalog models unbindable (all 38 `openai`, 118 bedrock, 38 azure, 31 mistral, 41 google) because the derived `provider_kind` can never express `openai-responses` and friends; missed because the conformance harness passes `record.api` as the transport | FIX-pi-compat-20260908-WAVE-authority-and-boundary-REVIEW-r1 | open |
| F-2 | Major | `pi-runtime/src/worker.mjs:311` | `handlerTail` is declared inside the stdin `data` callback, so the claimed bind-before-prompt ordering invariant is per-chunk only; `supervisor.py:224-225` writes one frame per drain | FIX-pi-compat-20260908-WAVE-authority-and-boundary-REVIEW-r1b | open |
| F-3 | Major | `pi-runtime/src/worker.mjs:311-330` (with `session.mjs:652-664`, `tools.mjs:24`) | The same chain adds a cross-session head-of-line block: a `session.close` blocked in `waitForIdle()` now starves every frame batched behind it; pre-change only its own session stalled | FIX-pi-compat-20260908-WAVE-authority-and-boundary-REVIEW-r1b | open |

## Append-Only Ledger
- **L-001 | 2026-09-08 | S0-frame | pi | —**
  Did: full investigation (pi-ai registry/exports/detection semantics,
  mirror-vs-installed freshness, CF graph wiring map, 0.85.1 dist diff,
  live T1 baseline); wrote this file.
  Result: plan framed with measured evidence; 0 files touched.
  Verified: commands and greps above are re-runnable.
  Next: owner DEC-1, then CF-SPEC-29 clarify/plan/tasks + Phase 1.
- **L-002 | 2026-09-08T07:01:43Z | S1-plan | codex | DEC-2**
  Did: recorded the owner's approved planning directive for total Pi
  compatibility and upstream-update-friendly integration; broadened the goal,
  non-goals, appetite, and acceptance scope without changing product code.
  Result: lifecycle is ready to serve as the three-architect prompt; 0 code
  files touched.
  Verified: owner directive is explicit above; routing is repository-local and
  validated separately.
  Next: generate a fresh strict-wave 3-architect pipeline and hold at owner
  approval after synthesis/cross-vote.

### L-003 | 2026-09-08T07:21:10Z | S1-plan | claude-opus-5 | architect-b | Phase 0 — 3-architect planning <!-- bsc-ledger:pi-compat-20260908-PLAN-B -->
Did: independent S1 consensus-architect draft for slot B, written to `docs/build-stream/pi-compat-20260908-plan-b.md`
(685 lines). Investigated the full Pi compatibility surface directly — pi-ai
0.84.3 registry exports, `Model`/`compat` typings, `openai-completions` and
`openai-codex-responses` adapters, `provider.mjs`, `endpoint_policy.py`,
`engine.py`, `catalog.py`, `llm_thinking.py`, `session.mjs`, the 27,977-line
backend mirror, `ChatModelControls.tsx`, the simulation registry, and
`labs/pi-replacement`. No product code touched.
Result: plan proposes an explicit four-tier capability precedence law and a
single *generated* catalog projection as the one authority seam (rejecting a
runtime `getBuiltinModel()` call on measured grounds: 67 ms / 60 MB per worker
session, and it repairs only one of four consumers). Seven waves W0–W7, eight
acceptance criteria, eight risks, per-wave rollback, five owner decisions
(DEC-B1..B5). New measured findings beyond the lifecycle's E1–E5: `thinkingLevels`
is a dead field in pi-ai 0.84.3 so Codex `xhigh`/`max` silently clamp to `high`;
zai bindings emit no `reasoning_effort` at any level (proven at the wire); all
five zai mirror models are $0-priced so every budgeted zai run fails
`cost_budget_unpriced`; 976/1307 models carry a wrong `thinkingLevels` because
the mirror stores map keys rather than supported levels; no catalog generator
exists in the repo; zero UI-suite coverage of the effort journey. Recorded five
corrections to the lifecycle's E1/E2/E5 claims (incl. `glm-5.3-flash` existing in
neither the mirror nor pi-ai 0.84.3, and the rollback missing `labs/pi-replacement`).
Verified: `cd pi-runtime && npm test` -> 54 pass / 0 fail / 8.4 s (baseline, unchanged);
`grep -rn thinkingLevels node_modules/@earendil-works/{pi-ai,pi-agent-core}/dist/` -> 0
non-helper references; captured-fetch wire diff on `zai/glm-5.3` -> istara payload omits
`reasoning_effort`, pi-ai record emits `low`/`high`/`max`; mirror-vs-registry comparison ->
81 missing / 36 stale / 976 wrong levels / 20 context / 188 cost fields (21 zero-in-mirror);
`providers/all` import -> 67.2 ms, 60.4 MB RSS, 39 providers / 1312 models.
Four `command` evidence rows recorded on pi-compat-20260908-PLAN-B.
Next: stage exit — draft written to `plan_file`; awaiting the synthesis phase.

### L-4 | 2026-09-08T07:25:42Z | S1-plan | zai/glm-5.3-flash | planner | pi-compat-20260908-architect-c <!-- bsc-ledger:pi-compat-20260908-PLAN-C -->
Did: pi-compat-20260908-architect-c stage on task pi-compat-20260908-PLAN-C (harness fallback entry; the model did not append one).
Result: task pi-compat-20260908-PLAN-C finished; worktree head efdcb372.
Verified: see Compass Forge evidence rows on pi-compat-20260908-PLAN-C (command + self_report + stage_attribution).
Next: conductor advances the pipeline on evidence.

### L-5 | 2026-09-08T07:33:52Z | S1-plan | gpt-5.6-sol | planner | pi-compat-20260908-architect-a <!-- bsc-ledger:pi-compat-20260908-PLAN-A -->
Did: pi-compat-20260908-architect-a stage on task pi-compat-20260908-PLAN-A (harness fallback entry; the model did not append one).
Result: task pi-compat-20260908-PLAN-A finished; worktree head c09f0c42.
Verified: see Compass Forge evidence rows on pi-compat-20260908-PLAN-A (command + self_report + stage_attribution).
Next: conductor advances the pipeline on evidence.

### L-6 | 2026-09-08T07:42:47Z | S1-plan | claude-opus-5 | architect-b (synthesis) | Phase 0 — 3-architect planning <!-- bsc-ledger:pi-compat-20260908-MASTER-B -->
Did: MECE master-plan synthesis for slot b. Read all three immutable draft
snapshots (A/gpt-5.6-sol 508 lines, B/claude-opus-5 685 lines, C/zai-glm-5.3-flash
224 lines) and re-measured every disputed fact rather than averaging positions.
Wrote `docs/build-stream/pi-compat-20260908-master-b.md` (one complete master candidate: authority law, resolved conflicts,
unioned evidence, 8 dependency-ordered waves W0–W7, 11 acceptance criteria,
change-classification taxonomy, verification ladder, 15 risks, rollback, coverage
matrix, 6 owner decisions). No product code and no lifecycle plan body edited.
Result: 4 substantive conflicts resolved on evidence — DEC-M1 dual-path authority
(runtime `getBuiltinModel()` in the worker + generated projection for other
consumers, bound by a new equivalence test) which REVERSES my own draft B's
persisted-descriptor design in favour of A/C; DEC-M2 `getSupportedThinkingLevels`
is the only correct derivation, rejecting C's non-null-map-keys rule (measured
wrong in 3 of 4 live records); DEC-M3 pi-ai owns list price, operator owns
contract price (A's rule over B's full replacement and C's no-inheritance);
DEC-M4 version bump moves LAST behind conformance (B/C over A's bump-first), with
A's lockstep-across-both-surfaces requirement and C's diff-proof-first step.
Raised S-E3, a defect no draft caught: 119 of 1312 upstream models are zero-priced
in pi-ai itself, including `zai/glm-5.3` (the live-probe model), so regenerating
the mirror cannot fix `cost_budget_unpriced` — draft B's AC-6 was unachievable as
written and is rewritten around an admission-time pricing preflight. Also
confirmed lifecycle evidence E2 is wrong (`glm-5.3-flash` is absent from installed
0.84.3). pi-compat-20260908-MASTER-B.
Verified: `grep -n getSupportedThinkingLevels -A22 pi-runtime/node_modules/@earendil-works/pi-ai/dist/models.js`
(models.js:547-559 — absent entry means supported for off/minimal/low/medium/high,
while xhigh/max are opt-in) → passed; node evaluation of `getBuiltinModel` +
`getSupportedThinkingLevels` over zai/glm-5.3, openai-codex/gpt-5.6-luna,
anthropic/claude-opus-4-7, zai/glm-4.7 → passed (luna and opus-4-7 both support all
7 levels where the non-null rule yields 3 and 2; mapless glm-4.7 supports 5 where
the rule yields 0); `getBuiltinModel('zai','glm-5.3-flash')` → undefined → passed;
registry walk over 39 providers / 1312 models counting zero-priced records → passed
(119 zero-priced, 109 reasoning-capable); `grep -rn cost_budget_unpriced pi-runtime/src/`
+ `sed -n 525,545p pi-runtime/src/session.mjs` → passed (session.mjs:420,:539 fail
closed when max_cost_usd is finite, the binding is real, and a spent category is
$0-rated). All five recorded as CF `command` evidence on pi-compat-20260908-MASTER-B, alongside the
`self_report`. No suite was run: this is a planning stage that touched no code.
Next: conductor cross-vote on the master candidates, then stop at the winning-plan
owner-approval gate. Six owner decisions (DEC-O1..O6) block implementation.

- **L-7 | 2026-09-08T07:53:33Z | S1-plan | zai/glm-5.3-flash | synthesizer | synthesize (rev 2) <!-- bsc-ledger:pi-compat-20260908-MASTER-C -->**
  Did: read all three immutable draft snapshots (slots a/b/c) and spot re-verified the
  load-bearing claims (glm-5.3-flash ABSENT from installed 0.84.3 — lifecycle E2 wrong;
  luna map `minimal→"low"`; `providers/all` import 75ms/~61.6MB RSS; mirror zai cost zeros;
  `PiCatalogModel` lacks thinkingLevelMap/compat; `./providers/*` wildcard subpaths exist);
  wrote the MECE master-plan candidate `docs/build-stream/pi-compat-20260908-master-c.md`
  (merged per-field authority law, waves W0–W7, coverage matrix, conflict register X1–X10,
  DEC-M1..M7). Rev 2 after cross-reading L-6 (MASTER-B): independently re-measured and
  adopted S-E3 — pi-ai itself prices 119/1312 models at $0 incl. `zai/glm-5.3`, so mirror
  regeneration alone cannot fix `cost_budget_unpriced` (added G17, W1.7 pricing preflight,
  R14, DEC-M8; rewrote acceptance row 8) — and verified the `getSupportedThinkingLevels`
  semantics (absent map key = supported for the five standard levels; explicit null
  excludes; xhigh/max opt-in: luna 7, glm-5.3 3, glm-4.7 5, opus-4-7 7), fixing W3.3 to
  validate against the computed set rather than map-key presence.
  Result: synthesis candidate rev 2 ready for cross-vote; 0 code files touched; 1 doc
  created+amended; worker-side inheritance adopted primary with B's measured import-cost
  gate (≤30MB) and descriptor contingency; bump-last with diff-proof-first.
  Verified: CF command evidence ids 1265/1266 (snapshots + plan), 1268/1269 (S-E3 walk +
  level semantics), self_report id 1267 (satisfied=true); plan sha256 re-hashed post-rev2.
  Next: conductor cross-vote on the synthesized master candidates (MASTER-B, MASTER-C);
  then stop at the winning-plan owner-approval gate (DEC-M1..M8 outstanding).

### L-7 | 2026-09-08T07:57:26Z | S1-plan | gpt-5.6-sol | planner | pi-compat-20260908-architect-a <!-- bsc-ledger:pi-compat-20260908-MASTER-A -->
Did: pi-compat-20260908-architect-a stage on task pi-compat-20260908-MASTER-A (harness fallback entry; the model did not append one).
Result: task pi-compat-20260908-MASTER-A finished; worktree head 7188ab25.
Verified: see Compass Forge evidence rows on pi-compat-20260908-MASTER-A (command + self_report + stage_attribution).
Next: conductor advances the pipeline on evidence.

### L-8 | 2026-09-08T08:02:49Z | S1-plan | claude-opus-5 | architect-b (cross-vote) | Phase 0 — 3-architect planning <!-- bsc-ledger:pi-compat-20260908-VOTE-B -->
Did: cross-vote stage on task pi-compat-20260908-VOTE-B, round `438f30bed0c2576cad62`, voter
  slot b. Read the two supplied master candidates in full from their immutable snapshots —
  slot a (`16d7e698…`, gpt-5.6-sol, 816 lines) and slot c (`6f928974…`, zai/glm-5.3-flash
  rev 2, 494 lines) — plus CF-SPEC-29. Did not vote for my own slot; no plan or lifecycle
  plan section edited; no code touched. Independently re-measured candidate C's load-bearing
  claims rather than accepting either plan's prose: lockstep `@earendil-works/pi-ai@0.84.3`
  pins in BOTH `pi-runtime/package.json:13-14` and `labs/pi-replacement/package.json:17-18`;
  `EXPECTED_PINS` at `tests/pi_migration/test_version_provenance.py:34`; `cost_budget_unpriced`
  fail-closed in `pi-runtime/src/session.mjs` (~536-544); `PiCatalogModel`
  (`backend/app/core/pi_runtime/catalog.py:31-41`) carries no `thinkingLevelMap`/`compat`;
  mirror zai entries `thinkingLevels: null` with `cost {0,0,0,0}`; upstream 0.84.3 registry
  = 39 providers / 1312 models with a large zero-priced cohort **including `zai/glm-5.3`**,
  and `getBuiltinModel('zai','glm-5.3-flash')` → undefined. `zai/glm-5.3`'s map is
  `{off:null, minimal:null, low:"low", medium:null, high:"high", xhigh:null, max:"max"}` —
  i.e. supported = `[low, high, max]`, matching C's corrected `getSupportedThinkingLevels`
  semantics exactly.
Result: **voted slot c** (candidate_id `6f928974f42da70a7ac7e86f86c93eafe32ba09df6340e4a23025926f0eb193a`)
  for task pi-compat-20260908-VOTE-B. Both candidates are buildable, dependency-ordered and
  MECE; C wins on four grounds. (1) Every C anchor I checked held exactly, while A explicitly
  defers remeasurement to W0 and carries far fewer checkable anchors. (2) C alone establishes
  that **pi-ai itself** prices ~120 models at $0 (`zai/glm-5.3` included), so mirror
  regeneration can never repair budget integrity — hence its W1.7 admission-time pricing
  preflight (`pricing: "unknown"` + typed fail-closed error naming the unpriced categories).
  A treats generated pi-ai prices as sound reconciliation defaults and keeps only the generic
  unpriced floor (AC-08/AC-09), which is safe but not actionable. (3) C alone corrects the
  rollback scope: A's W3 rollback restores a single `package.json`/lockfile, which would leave
  `test_version_provenance.py` red because `labs/pi-replacement` is a second bundled pi
  surface — verified above. (4) On the central conflict (where the authority is read), A
  hard-decides the server-built descriptor transport, departing from the owner's own acceptance
  wording (`getBuiltinModel(pi_provider, model)` resolves at bind → that record's
  `{reasoning, thinkingLevelMap, compat}` is used); C satisfies it literally by default and
  converts the measured import cost into a quantified gate (≤30 MB sustained RSS delta per
  worker process) with the descriptor pre-designed as the contingency — same engineering,
  decided on measurement rather than a planning-time estimate. C's §8 conflict register
  (X1–X11) also does the synthesis job the phase asks for, and it ships the routine bump
  runbook (§12), architecture-debt register (§15) and terminal states (§16).
  **Where A is better and the winner should absorb it:** A's explicit T0–T12 task DAG with
  parallelism/dependency notes is cleaner for wave execution than C's wave tables, and A's
  monotonic invariant (advertised endpoint flags may *narrow* a builtin capability, never
  enable one) is safer than C's DEC-M6 loud bidirectional operator override — DEC-M6 is the
  item most deserving owner scrutiny at the approval gate.
  **Honest discrepancy recorded, not smoothed over:** C states 119/1312 upstream zero-priced
  (109 reasoning-capable); my count under a slightly different zero-rule gave 121/1312 (111).
  Directionally confirmed; the exact rule and count must be pinned by the W1 generator and its
  conformance test, not by either plan's prose. I also could **not** confirm C's G5 codex/luna
  `minimal→"low"` map: my id regex matched no luna/terra/sol record in installed 0.84.3, so the
  codex provider/model ids both plans assume remain unverified by me and W0 must establish them.
Verified: `grep -n earendil-works pi-runtime/package.json labs/pi-replacement/package.json`
  → both 0.84.3 (passed); `grep -rn EXPECTED_PINS tests/pi_migration/test_version_provenance.py`
  → line 34 (passed); `sed -n 530,548p pi-runtime/src/session.mjs` and
  `sed -n 28,45p backend/app/core/pi_runtime/catalog.py` (passed); node import of
  `@earendil-works/pi-ai/providers/all` → 39 providers / 1312 models / 121 zero-priced
  (111 reasoning), `zai/glm-5.3` cost all-zero, `zai/glm-5.3-flash` undefined (passed);
  `python3` inspection of `pi_models_catalog.json` → zai `thinkingLevels: null`,
  `cost {0,0,0,0}` (passed). CF rows on pi-compat-20260908-VOTE-B: 3 × `command`,
  1 × `plan_vote` (vote=c), 1 × `self_report` (satisfied=true). No test suite was run — a vote
  stage changes no code; no plan file, lifecycle plan section, or product file was edited.
Next: stage exit — vote recorded for slot c with reason and dissent. Conductor tallies
  MASTER-A vs MASTER-C, then holds at the winning-plan owner-approval gate
  (DEC-M1..M8 / DEC-O1..O6 outstanding). No implementation is authorized.

### L-9 | 2026-09-08T08:04:46Z | S1-plan | gpt-5.6-sol | planner | pi-compat-20260908-architect-a <!-- bsc-ledger:pi-compat-20260908-VOTE-A -->
Did: pi-compat-20260908-architect-a stage on task pi-compat-20260908-VOTE-A (harness fallback entry; the model did not append one).
Result: task pi-compat-20260908-VOTE-A finished; worktree head 816bcee3.
Verified: see Compass Forge evidence rows on pi-compat-20260908-VOTE-A (command + self_report + stage_attribution).
Next: conductor advances the pipeline on evidence.
### L-10 | 2026-09-08T08:08:20Z | S1-plan | zai/glm-5.3-flash | architect-c (cross-vote) | Phase 0 — 3-architect planning <!-- bsc-ledger:pi-compat-20260908-VOTE-C -->
Did: read the two supplied immutable master candidates end-to-end (slot a: 16d7e698..., gpt-5.6-sol; slot b: f2be3452..., claude-opus-5); spot re-verified the vote-decisive claims against the repo (S-E2 getBuiltinModel('zai','glm-5.3-flash') undefined on 0.84.3; S-E3 registry walk 1312 models / 119 zero-priced / 109 reasoning-capable, zai zeros incl. glm-5.3; G10 both pi surfaces pinned 0.84.3 with tests/pi_migration/test_version_provenance.py asserting both; G6 provider-params.test.mjs 121-131/192-200 pin the defective behavior as expected); recorded plan_vote for candidate slot b (candidate_id f2be3452af887bea5e0ee729b62bedf973b411b22c98b9f1142199a26dd86609, round 438f30bed0c2576cad62).
Result: vote cast for slot b over slot a on verified deltas: S-E3 admission-time pricing preflight vs an unaddressed upstream-zero-pricing gap in A; labs/pi-replacement lockstep + corrected rollback absent from A; B equivalence test, round-trip drift test, model_field_set_hash + classification taxonomy, routine-bump runbook as AC-11; B named test flips vs A generic W0 classification; B source-level corrections of lifecycle evidence E1/E2/E4/E5. Trade-off recorded: A avoids the once-per-process 67ms/60MB registry import via generator-only + ephemeral server-built envelope; B mitigates via memoised accessor + measured budget and gains exact pi-ai fidelity at the worker seam. With VOTE-A -> b and VOTE-B -> c, candidate b holds a 2-of-3 majority pending conductor tally. No plan edited, no code touched. Note: file carried two L-7 entries (MASTER-C bold variant, MASTER-A); entries L-8/L-9 were appended concurrently by VOTE-B/VOTE-A; this entry is L-10.
Verified: node --input-type=module registry walk over @earendil-works/pi-ai/providers/all -> passed (1312/119/109; zai zero-priced = glm-5.2-highspeed, glm-5.3, zai-coding-cn variants; glm-5.3-flash undefined); grep checks on labs/pi-replacement pins, test_version_provenance.py, provider-params.test.mjs -> passed; CF rows on pi-compat-20260908-VOTE-C: 2 x command, 1 x plan_vote (vote=b), 1 x self_report (satisfied=true). No test suite run: planning stage, zero code changes.
Next: conductor tallies VOTE-A/VOTE-B/VOTE-C, declares the winning master plan, and holds at the owner-approval gate (DEC-O1..O6 / DEC-M1..M8 outstanding; implementation unauthorized until then).

### L-11 | 2026-09-08T09:49:41Z | S2-execute | zai/glm-5.3-flash-max | executor | Wave authority-and-boundary (plan W1+W2+contracts) <!-- bsc-ledger:pi-compat-20260908-WAVE-authority-and-boundary-IMPL -->
Did: implemented the capability authority boundary per the owner-approved consensus plan. NEW
`pi-runtime/scripts/emit-catalog.mjs` (deterministic tier-4 projection emitter: verbatim registry fields +
thinkingLevels via pi-ai's own getSupportedThinkingLevels (DEC-M2), provenance header with pi_ai_version /
pi_ai_generated_at / emitter_sha256 / model_field_set_hash, governed-overlay merge with collision/schema/
order rejection); NEW `scripts/generate_pi_catalog.py` operator entry (in-place regeneration, --check
byte-identity drift gate, typed exit-3 not_runnable); NEW governed overlay
`backend/app/core/pi_runtime/data/custom_providers/dashscope.json` (40 records extracted verbatim, wire
fixtures referenced); regenerated `backend/app/core/pi_runtime/data/pi_models_catalog.json` (39 registry
providers / 1,312 models + overlay; provenance-stamped); `backend/app/core/pi_runtime/catalog.py` gains
PiCatalogModel.thinkingLevelMap/compat (G8), skips __-prefixed provenance keys, adds catalog_provenance();
`pi-runtime/src/provider.mjs` adds memoised once-per-process registry accessor (W2.1), async
resolveCapabilities (exact guarded getBuiltinModel, §1.2 per-field restriction merge, tier-5 URL
developer-role default under tier 4, typed pre-network provider_transport_mismatch rejection with
fixture-backed exception list W2.6), moves today's branches verbatim into exported
legacyIdentityCapabilities (W2.3, modelCapabilities kept as deprecated alias), buildRealProvider is async,
sets thinkingLevelMap and stops setting the dead thinkingLevels field (G3/W2.4), returns content-free
capability_receipt; `pi-runtime/src/session.mjs` bindProvider is async (disposes previous binding only
after the new one resolves) and `pi-runtime/src/worker.mjs` serializes frame-handler dispatch so a
provider.bind is fully applied before a following turn.prompt; captured 9 pre-change wire fixtures
(NEW scripts/capture-wire-fixtures.mjs + test/fixtures/wire/pre-change/) BEFORE the resolver landed;
NEW `pi-runtime/test/capability-inheritance.test.mjs` (33 tests: AC-1 fallback byte-identity, 15
inherited-class corrected fixtures, AC-2 codex xhigh/minimal→low, AC-3 zai reasoning_effort, AC-4 tier-2
veto tri-state, transport-mismatch typed rejection, receipt hygiene negative test, registry memoisation);
FLIPPED the two defect-pinning tests in `pi-runtime/test/provider-params.test.mjs` per G6/DEC-O3 (codex
branch → resolveCapabilities record assertion with in-file justification; zai wire test → glm-5.3 with
reasoning_effort:"low"; the previous zai test bound the non-existent glm-5.3-flash id, S-E2); NEW
`tests/pi_compat/test_catalog_conformance.py` + dump helper `pi-runtime/scripts/dump-resolved-capabilities.mjs`
(round-trip byte identity, provenance ≡ EXPECTED_PINS, overlay preservation, registry parity, authority
equivalence projection ≡ resolver over all 1,312 registry models, typed not_runnable skips); NEW drift
report `docs/build-stream/pi-compat-20260908-drift-report.md` (duplicated/stale knowledge inventory:
81 added / 36 removed / 1,231 changed models, 1,225 wrong menus, 20 context, 63 cost models, 119 upstream
zero-priced models incl. zai/glm-5.3); TESTING.md/TEST_HISTORY.md baseline entry (suite topology change).
Result: $TASK complete — authority law, generator/projection, resolver, and conformance contracts in
place; W3 carry-through (settings API/frontend/pricing preflight), W5 observability/UI scenarios, W6
0.85.1 bump, W7 live acceptance remain later waves (dependencies recorded in plan §6.1).
Verified: `cd pi-runtime && npm test` → 87 pass / 0 fail (54 baseline + 33 new; no network in tests);
`node --test test/capability-inheritance.test.mjs` → 33 pass incl. 9 fallback bodies byte-identical to
pre-change captures (AC-1); `python scripts/generate_pi_catalog.py --check` → byte-identical ok;
`uv run --project backend --extra dev python -m pytest tests/pi_compat -q` → 5 passed (authority
equivalence over 1,312 models); `pytest tests/pi_migration/test_version_provenance.py
tests/pi_production/test_pi_catalog_ux.py tests/pi_production/test_engine_http_provider.py
tests/test_model_source.py tests/test_pi_replacement_candidate.py -q` → 66 passed;
`pytest tests/pi_production -q` → 475 passed; `pytest tests/pi_benchmark -q` → 245 passed, 5 skipped;
`pytest tests/test_research_validity_contract.py` (inside pi_production run) green — Research Spine
non-bypass; `python scripts/check_test_harness.py` → passed; `python scripts/check_integrity.py` →
passed; `python scripts/security_benchmark.py --fail-on-threshold` → score 100.0, status pass;
`docker compose -f docker-compose.qa.yml --profile contract config --quiet` → ok.
Next: stage exit — S3 review of $TASK (reviewer: verify AC-1/2/3/4 wire fixtures, conformance gates, and
that no Research Spine/security gate changed).

### L-12 | 2026-09-08T10:07:37Z | S3-review | claude-opus-5 | reviewer | Wave authority-and-boundary (blind two-phase review) <!-- bsc-ledger:pi-compat-20260908-WAVE-authority-and-boundary-REVIEW -->
Did: blind two-phase adversarial review of commit c86ceeb1 (43 files: emit-catalog.mjs, generate_pi_catalog.py,
dashscope overlay, regenerated projection, catalog.py, provider.mjs, session.mjs, worker.mjs, capability-inheritance
tests, wire fixtures, tests/pi_compat). Phase 1: froze a 10-row measurement sheet from my own runs before opening the
work order, L-11, or any prior verdict. Built my own apparatus rather than reusing the implementer's — an NDJSON worker
harness driving pi-runtime/src/worker.mjs, and an A/B rig that extracts the pre-change src tree from c86ceeb1^ so
pre/post behaviour is compared directly. Reviewer scratch removed; no repository file changed except this lifecycle file.
Result: **FAIL**. Three undisclosed defects, all A/B-proven against the pre-change tree. F-1 (Blocker): the wave's
headline control, the typed `provider_transport_mismatch` rejection in `resolveCapabilities`, makes 346 of 1352 shipped
catalog models unbindable — including all 38 `openai` models — because `endpoint_policy.py::_apply_catalog_fields`
derives `provider_kind` through a three-way map and `apiForKind` emits only three transports, so records whose api is
`openai-responses` / `bedrock-converse-stream` / `azure-openai-responses` / `mistral-conversations` /
`google-generative-ai` / `google-vertex` can never agree. It went undetected because
`scripts/dump-resolved-capabilities.mjs:63` passes `record.api` as the transport, making the mismatch branch
structurally unreachable in the 1,312-model equivalence sweep. F-2 (Major): `worker.mjs:311` declares `handlerTail`
inside the stdin `data` callback, so the ordering invariant L-11 claims ("a provider.bind is fully applied before a
following turn.prompt") is per-chunk only, while `supervisor.py:224-225` writes one frame per drain. F-3 (Major): the
same chain adds a cross-session head-of-line block — a `session.close` on a session with an in-flight tool call never
completes (`tools.mjs:24` ignores the AbortSignal `agent-loop.js:457` passes) and now starves every frame batched behind
it. Confirmed as sound: the tier-1..3 restriction law is monotonic (advertisements cannot enable or add a modality), and
pi-ai 0.84.3 does gate every `thinkingFormat` branch on `model.reasoning`, so retaining `thinkingLevelMap` verbatim under
a tier-2 reasoning restriction leaks nothing onto the wire. Fix tasks FIX-pi-compat-20260908-WAVE-authority-and-boundary-REVIEW-r1 (F-1) and FIX-pi-compat-20260908-WAVE-authority-and-boundary-REVIEW-r1b (F-2+F-3)
created for pi-compat-20260908-fixer.
Verified: independent re-runs, all reproducing the implementer's numbers — `cd pi-runtime && node --test test/*.test.mjs`
-> 87 pass / 0 fail; `python scripts/generate_pi_catalog.py --check` -> byte-identical ok; `pytest tests/pi_compat -q`
-> 5 passed; `pytest tests/pi_production -q` -> 475 passed; `pytest -k "pi_runtime or pi_compat or model_manager or
endpoint" -q` -> 108 passed; `compass-forge gate after --new-only --target .` -> current.status = pass. Finding proofs:
reviewer A/B on `buildRealProvider` for openai/gpt-4o -> PRE-change bound (model.api=openai-completions), POST-change
threw `provider_transport_mismatch:openai:gpt-4o:registry_api=openai-responses:configured=openai-completions`; catalog
cross-check -> 346/1352 models affected; `_apply_catalog_fields("openai","gpt-4o")` -> provider_kind=openai_compat
(the exact input the gate rejects); reviewer A/B worker harness -> pre-change session B opens while a blocked
session.close is in flight, post-change session B never opens.
Next: S4-remediate — pi-compat-20260908-fixer takes FIX-pi-compat-20260908-WAVE-authority-and-boundary-REVIEW-r1 and FIX-pi-compat-20260908-WAVE-authority-and-boundary-REVIEW-r1b; conductor dispatches one delta
re-review to this role after both are terminal.
