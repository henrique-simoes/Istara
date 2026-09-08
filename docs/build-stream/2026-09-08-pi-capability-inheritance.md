# Build Stream — Pi Capability Inheritance (pi-ai standard as default)

<!-- STATUS BLOCK -->
```yaml
item: pi-capability-inheritance
branch: testing
cf: { spec: CF-SPEC-29, tasks: [] }
phase: "Phase 0 — Owner-approved expanded frame; 3-architect planning"
stage: S1-plan
status: in_progress
blocked_on: null
last: { agent: claude-opus-5, at: 2026-09-08T07:21:10Z, ledger: L-003 }
next_action: "Generate the strict-wave 3-architect plan; hold implementation at the winning-plan owner-approval gate."
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

## Decision log
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
