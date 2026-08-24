# Agentic-Core Integrity & Core-Capable QA — Build Stream lifecycle

```yaml
item: agentic-core-integrity-and-qa
branch: testing
cf: { spec: CF-SPEC-1 }
phase: "Phases 1–4 complete — ship pending live VPS verification"
stage: S5-ship
status: blocked
blocked_on: "Owner-gated outward steps: push, VPS redeploy (SSH direction), live chat smoke on Pi core"
last: { agent: ox-alpha, at: 2026-08-23T16:40:00Z, ledger: L-7 }
next_action: "Owner pushes 342ea9a4 and redeploys the VPS stack; verify Pi-core DeepSeek chat live; then Codex OAuth endpoint #2 and spec accept."
```

## Plan overview / roadmap

**Problem.** After the Pi-agentic-core + provider/model UX integration landed on
`origin/testing`, chat behaves as if no integration happened: every message returns the
literal stub text `qa-contract-responseqa-contract-response` and stops (no agentic loop),
the core indicator says "Pi" even when Istara is selected, and the Agentic-Core chooser
has unmeasured color/accessibility in light and dark modes.

**Outcome.** Choosing a core in Settings actually routes chat through that core; chat runs
its real loop against a configured live endpoint; the chooser passes WCAG 2.2 AA in both
modes; the QA architecture can assess Pi and Istara cores end-to-end (deterministic first,
live behind explicit authorization).

**Goal / non-goals.**
- Goal: restore correct engine selection for `/chat`, remove any path where the QA stub
  serves interactive user chat, measure and fix chooser contrast, extend QA obligations so
  both cores are assessed.
- Non-goals: replacing either engine, changing the research-validity spine, touching
  `LLMs/` or `Model_Finetuning/`, starting servers or loading models without explicit
  permission, configuring OpenAI Codex OAuth before the two-endpoint comparison stage.

**Appetite.** One focused delivery: Phase 1 correctness fixes + Phase 2 a11y measurement +
Phase 3 QA extension. Live multi-endpoint spine comparison is explicitly deferred until
the owner configures the second endpoint.

**Acceptance criteria (draft — finalized after owner answers).**
- AC-1: With project setting `agentic_engine=legacy`, a chat turn executes on the Istara
  legacy plane; with `pi`, it executes via Pi runtime. Verified by: targeted pytest that
  drives `/chat` routing logic with each persisted setting (CI-safe).
- AC-2: No interactive chat surface can resolve its model to the QA contract stub unless
  an explicit QA env/profile is active. Verified by: pytest asserting routing rejects the
  QA-contract model outside the QA profile + grep guard in CI obligations.
- AC-3: Every color pair in `AgenticCoreSection` (both modes) measured ≥4.5:1 body text,
  ≥3:1 UI borders/indicators; failures fixed. Verified by: a token-level contrast script
  checked into tests/frontend + attached output.
- AC-4: QA obligation registry gains core-assessment entries (deterministic engine-routing
  contracts; live chat smoke stays `live_optional` behind explicit target). Verified by:
  `python scripts/check_qa_capabilities.py` and `check_feature_obligations.py` passing.
- AC-5: Feature docs regenerated (`python scripts/feature_docs.py --seed-missing
  --generate-site --check`) for any behavior change; attached as evidence.

**Doc impact:** `docs/features/content/chat/model-controls/*`,
`docs/architecture/agentic_core.md`, `TESTING.md` command matrix rows if commands change.

**Rollback:** fixes are small reversible diffs on `testing`; per-phase revert via git.

**Top risks:** chat routing change could alter non-Pi byte-compatibility (AC guard exists);
a11y palette changes could drift from DESIGN.md tokens (measure before edit).

## Diagnosis (evidence from orientation)

- **F-1 (root cause, routing):** `backend/app/api/routes/chat.py` selects the engine only
  from the global flag `settings.pi_replacement_enabled` or request header
  `x-istara-agent-engine`; the frontend never sends that header anywhere, and neither the
  project column `projects.agentic_engine` nor `settings.agentic_engine_default` is
  consulted by `/chat`. Result: chat always runs the legacy (Istara) plane regardless of
  the user's choice — the "core isn't being changed" suspicion is correct, not just UI.
- **F-2 (indicator divergence):** the chip in `ChatModelControls.tsx:320` renders
  `/api/chat/model-catalog` → `engine`, which reads exactly the settings `/chat` ignores
  (`chat.py:1167-1171`). UI state and runtime routing are computed from different sources.
- **F-3 (stub reply):** `qa-contract-responseqa-contract-response` is produced by
  `qa/scripts/provider_stub.py`; streaming emits the content twice (chunk `done:false`
  then final `done:true`, lines 101–106) and concatenation yields the doubled string. The
  QA compose wires `OLLAMA_HOST=http://qa-provider-stub:11434` (`docker-compose.qa.yml:65`),
  so any chat whose legacy model resolves there gets this reply by design. Interactive chat
  reaching the stub means environment/model-selection leakage (which environment was being
  used is an S0 question) — nothing listens on local :11434 right now.
- **F-4 (no loop):** consequence of F-1/F-3: the legacy native-tool loop terminates after
  one turn when the model returns plain text and zero tool calls — with the canned stub
  response that is every turn.
- **F-5 (keys located, values untouched):** macOS Keychain services exist for
  `istara-pi-deepseek` (account `openclaw`) — current Pi DeepSeek endpoint key — and
  `istara-secondary-openai-compatible-tests` — candidate "second DeepSeek key" used for
  test-criteria generation. Confirmation pending with owner before wiring as endpoint #2.
- **F-6 (a11y):** `AgenticCoreSection.tsx` uses amber/istara/slate combinations not yet
  measured; repo gained a root `DESIGN.md` in this branch — audit must run against it
  (interface-design authority model), measuring both modes programmatically.

## Decision log

```
DEC-1 | 2026-08-23 | ox-alpha
Context: Local checkout was 174 commits behind origin/testing with leftover stash dirt.
Decision: Stashed local modifications ("wip-before-ff-to-origin-testing-20260823") and
fast-forwarded testing to origin/testing@9d7c506e (pure ff, 0 local-only commits).
Why: User stated the work lives on origin/testing; ff keeps history linear and recoverable.

DEC-2 | 2026-08-23 | owner (via S0 answers)
Context: Stub replies observed by owner.
Decision: The affected environment is the VPS deployment at :13081 — which
docker-compose.vps.yml:67 hardwires to the QA provider stub (OLLAMA_HOST=http://provider-stub:11434).
Why: Confirms D2: the deployed "production-like" stack has no real model provider; combined
with F-1 every interactive chat there is stub-served regardless of Settings.

DEC-3 | 2026-08-23 | owner
Decision: Fix approach = persisted setting + header. /chat resolves engine from
project.agentic_engine → settings.agentic_engine_default, AND the frontend sends
x-istara-agent-engine per chat request. Non-Pi default behavior stays byte-compatible when
nothing is persisted and no header is present.
Why: Closes both divergence sources found in F-1/F-2; header gives per-request override for
benchmark/A2A parity with dispatcher resolution order.

DEC-4 | 2026-08-23 | owner
Decision: The "second DeepSeek key" is macOS Keychain service istara-secondary-openai-compatible-tests.
Why: Owner confirmed. It will be wired as research-spine endpoint #2 at the multi-model stage;
values are never read into repo or logs before then.

DEC-5 | 2026-08-23 | owner
Decision: Scope/order = Phase 1 routing+stub-leak fixes → Phase 2 chooser WCAG audit/fix →
Phase 3 QA obligations extended to assess both cores. Live smoke prep included in design but any
live call still requires explicit owner go.
Why: Correctness first; a11y measured against root DESIGN.md; QA extension builds on fixed routing.

DEC-6 | 2026-08-23 | ox-alpha
Context: WCAG audit found real defects: istara-950 undefined (dark selected backgrounds
silently transparent), light unselected radio border 1.48:1, light selected card border
2.28:1, dark radio borders <3:1, focus ring hardcoded blue-600 in both modes.
Decision: Added istara-950 #052e16 (consistent with dark --ui-accent-soft); unselected radio
border slate-500 light / slate-400 dark; selected circle dark border istara-400; selected card
light border istara-600; focus ring now var(--ui-focus). Audit script + pytest wrapper added.
Why: Brings AgenticCoreSection to WCAG 2.2 AA in both modes with measured evidence; aligns
component with DESIGN.md authority instead of hardcoded hues.

DEC-7 | 2026-08-23 | ox-alpha (owner-requested addition)
Context: Owner asked for a design.md-standard systemization of Istara's Design System for
agentic development and UI processes.
Decision: Extended root DESIGN.md with the three-layer token architecture (primitives →
semantic --ui-* aliases with normative per-mode values → DTCG export), enforcement tooling
pointers, and the governance/authority model. Added scripts/export_design_tokens.py emitting
docs/design/tokens.json (W3C DTCG) deterministically from globals.css + tailwind.config.js,
with --check drift mode and tests/test_design_tokens.py gate.
Why: interface-design authority model — one export graph from DESIGN.md/DTCG rather than
hand-maintained duplicates; gives every agent and design tool a stable, machine-readable
contract without forking hand-edited token files.
```

## Ledger

```
### L-1 | 2026-08-23T15:10:00Z | S0-frame | ox-alpha | framer | Phase 0
Did: Oriented (CF status/refresh/agent-brief, skills loaded); fast-forwarded to origin/testing;
diagnosed F-1..F-6 above; created CF-SPEC-1; verified Keychain service existence (no values read);
confirmed no local :11434 listener; mapped QA harness (istara-qa.sh, docker-compose.qa.yml,
feature_coverage.yml, TESTING.md matrix).
Result: Root-cause chain established (F-1→F-4); S0 questions posed to owner.
Verified: compass-forge status/agent-brief OK (process_level=full); git ff clean;
rg evidence for F-1..F-3 captured in file paths above.
Next: Owner answers → DEC records → spec clarify → spec plan/tasks → Phase 1 implementation.
```

## Phase 0 — Frame (closed: DEC-2..DEC-5 recorded)

```
### L-2 | 2026-08-23T15:25:00Z | S0-frame | ox-alpha | framer | Phase 0
Did: Posed four S0 questions; owner answered (DEC-2..DEC-5). Confirmed VPS compose ships
provider-stub as sole legacy provider (docker-compose.vps.yml:67) — root cause of the
interactive stub replies; F-1 explains why DeepSeek config was bypassed.
Result: S0 gate closed. Phase 1 scope locked (routing + stub-leak guard).
Verified: docker-compose.vps.yml read directly; answers recorded verbatim in decision log.
Next: spec clarify → constitution → plan → tasks → impact analysis → implement.
```


```
### L-3 | 2026-08-23T15:32:00Z | S2-execute | ox-alpha | executor | Phase 1
Did: CF-1 — chat.py `_resolve_chat_engine` (flag>header>project>global), pi_candidate now
uses it; frontend sends x-istara-agent-engine from catalog-derived core state
(chatApi.send engine param → chatStore.engine ← ChatView catalog fetch). CF-2 —
LLM_PROVIDER_CONTRACT_STUB config + qa/vps compose wiring; POST /api/chat fails closed
with provider_stub_chat_blocked SSE before any side effect. Tests added for both.
Result: Phase 1 complete; CF-1, CF-2 done with command evidence.
Verified: pytest tests/test_chat.py -q = 12 passed (scratch DATABASE_URL); ruff no new
findings (chat.py 29 pre-existing on origin/testing, identical count); tsc --noEmit clean;
eslint clean (fixed setEngine dep warning); vitest modelCatalog 6 passed;
docker compose config OK for qa+profiles and vps.
Next: Phase 2 — measure chooser contrast both modes against DESIGN.md tokens.
```

```
### L-4 | 2026-08-23T15:55:00Z | S2-execute | ox-alpha | executor | Phase 2
Did: Built scripts/check_a11y_contrast.py (46 pairs, alpha compositing over real parent
chains, light+dark); first run exposed istara-950 undefined + 5 contrast failures; fixed
palette/component (DEC-6); re-ran to PASS; added tests/test_a11y_contrast.py. Owner-added
design-system task (DEC-7): extended DESIGN.md (token architecture, normative values,
governance) and added scripts/export_design_tokens.py → docs/design/tokens.json with
--check gate + tests/test_design_tokens.py.
Result: CF-5 done with evidence; chooser passes WCAG 2.2 AA both modes; design system
now has a deterministic machine-readable contract.
Verified: python scripts/check_a11y_contrast.py → RESULT: PASS (46/46);
pytest tests/test_a11y_contrast.py tests/test_design_tokens.py = 2 passed.
Next: CF-3 frontend gates, then Phase 3 QA registry extension (CF-4).
```

```
### L-5 | 2026-08-23T16:05:00Z | S2-execute | ox-alpha | executor | Phase 3
Did: Extended QA architecture (CF-4): new qa/runtime_capabilities.json surface
agentic.core-routing; COMMAND_CATALOG pytest_core_routing (engine precedence, stub guard,
contrast audit, token determinism); wired into migration.pi-ux-convergence obligations with
extended acceptance. Ran mandated gates: security benchmark PASS 100%; feature docs
regenerated (224 artifacts, 86 features checked). CF-3 frontend gates green. Evidence rows
attached to CF-2/CF-3/CF-4.
Result: Phases 1–3 executed end-to-end with evidence. CF-1..CF-5 done.
Verified: security_benchmark status=pass score=100.0; feature_docs check passed;
check_qa_capabilities + check_feature_obligations passed; 32 governance tests passed;
tsc/eslint/vitest(14)/next build clean.
Next: S3 independent review (different model) of the full working diff → remediate →
spec accept. Live smoke on VPS after owner redeploys stack.
```

## Phase 4 — S3 independent review & S4 remediation

### Findings register (blind sheet: review-packet/2026-08-23-agentic-core-integrity-blind-sheet.md)

| ID | Sev | Dim | Where | Finding | CF task | Status |
|----|-----|-----|-------|---------|---------|--------|
| F-B1 | Minor | Code | chat.py:147 / ChatView.tsx:102 | Non-empty unrecognized header short-circuits to legacy; frontend could send explicit "legacy" after a failed catalog fetch and silently downgrade a persisted "pi" project | CF-1 | fixed |
| F-B2 | Minor | Integration | chat.py:669-672 | Stub-block SSE response missing Cache-Control/Connection/X-Accel-Buffering headers (Caddy may buffer the error frame) | CF-2 | fixed |
| F-B3 | Nit | Quality | chat.py:665 | Fail-closed returns 200 + in-stream error instead of 4xx/5xx | CF-2 | accepted-risk (matches existing in-stream error convention consumed by chatStore.ts) |
| F-B4 | Nit | Bugs | chat.py:149 | Route engine lookup raises on DB error vs dispatcher swallowing | CF-1 | accepted-risk (live session already required; silent fallback would hide real faults) |
| F-B5 | Nit | Tests | tests/test_chat.py:238 | Stub test did not assert absence of session/message rows | CF-2 | fixed |
| F-B6 | Minor | Process | check_feature_obligations invocation | Gate measured empty range while work uncommitted | — | fixed-by-commit (re-run post-commit evidence pending below) |
| F-B7 | Nit | Quality | qa/runtime_capabilities.json | Indentation inconsistency | — | false-positive (normalized to 4-space before review artifact read) |
| F-B8 | Info | Docs | docs/features/site/manifest.json | Whether living feature docs needed substantive update unverified | CF-4 | fixed (added "Agentic Core Resolution (CF-SPEC-1)" section to chat/model-controls/architecture.md + regen) |

Blind verdicts: Q1–Q10 all PASS independently measured (46 backend tests incl. reviewer's own
run, vitest 14/14, tsc/eslint clean, both governance validators exit 0). Claim comparison:
no divergence between frozen measurement sheet and ledger claims.

```
### L-6 | 2026-08-23T16:20:00Z | S3-review+S4-remediate | ox-alpha | remediator | Phases 1-3
Did: Blind S3 via independent agent (sheet frozen before claims read): 0 Blocker, 0 Major,
3 Minor, 4 Nit. Remediated F-B1 (store engine nullable → header omitted when catalog unknown;
ChatView catch sets null), F-B2 (SSE headers on stub-block response), F-B5 (row-absence
assertions), F-B8 (feature doc section + site regen); dispositions recorded for the rest.
Result: Register clean except F-B6 which resolves at commit time.
Verified: pytest tests/test_chat.py = 12 passed (incl. new row-absence assertions);
tsc+eslint OK; feature docs regen check passed (86 features).
Next: Commit scoped diff; re-run obligation checker over real range (F-B6); record review
verdict evidence; spec accept path.
```

```
### L-7 | 2026-08-23T16:40:00Z | S5-ship | ox-alpha | executor | Phases 1-4
Did: Committed the initiative as 342ea9a4 (26 files; includes AGENTS.md skills pointer and
the two new test gates). Registered design.system-contract feature + docker-compose.vps.yml
ownership so the real-range obligation gate passes (F-B6 closed with evidence, not an empty
range). Review-verdict evidence attached to CF-4.
Result: Local ship-ready state. Spec accept deferred until live VPS verification per plan.
Verified: check_feature_obligations --base origin/testing --head HEAD → pass=true,
unknown_paths=[]; pytest governance suites 22 passed; git status clean (except owner's
pre-existing untracked 2026-08-17 planning files, intentionally untouched).
Next: Owner-gated push + VPS redeploy → live Pi-core chat smoke → Codex OAuth endpoint #2
→ spec accept CF-SPEC-1.
```

## Phase 5 — Dual-core assessment across real-user/simulation suites

DEC-8 | 2026-08-23 | owner
Context: Full landscape inventory (see L-8). Owner approved push (done, 342ea9a4), VPS
redeploy, live smoke, and modifying the broad real-user/simulation suites so they assess
BOTH agentic loops against current architecture (LLM Servers replaced by Pi).
Decision: Modify in leverage order: (1) simulation runner engine wiring + scenario 79
behavioral turns; (2) stale llm-servers scenarios 36/35/72/37 re-homed to Pi surfaces,
keeping pinned IDs (70-73,76 untouched in name); (3) marathon engine threading + Pi-based
env detection + cycle-M checks; (4) e2e_test.py + long_horizon_runner engine params;
(5) benchmark npm engine passthrough + both→paired-runner handoff; (6) stub-guard explicit
skip messaging for chat-asserting scenarios. Compat-route pytest files tracked as-is
(compat projection exists by design). Colima/Docker requested ONLY at execution time.
Why: Deterministic/static verification runs locally; broad live suites need the owner's
Colima server and are explicitly gated.
```

```
### L-8 | 2026-08-23T17:10:00Z | S2-execute | ox-alpha | executor | Phase 5
Did: Dual-core assessment wiring across suites (DEC-8): simulation run.mjs now consumes
liveEngineHeader (client default + inline client headers + [SIM] project agentic_engine
pin/reconcile); api-client.mjs chat.send gains engine override, global engine default in
authHeaders, and explicit provider_stub_chat_blocked error; scenario 79 adds behavioral
per-engine chat turns with usage-ledger routing evidence (skips without LLM); scenarios
35/36/37/72 re-homed from removed-surface assertions to the current dual-plane contract
(model-catalog providers/engine/configured identity view; 36 pins compat-CRUD → Pi
projection invariant incl. no-secret-leak); marathon threads ISTARA_MARATHON_ENGINE
(pi|legacy|both double-run labeled id[engine]), env.llm detection now spans compat
healthy servers OR Pi-configured endpoints; e2e_test.py Phase 5 dual turn via
ISTARA_E2E_ENGINE; long_horizon_runner de-hardcoded API base + ISTARA_LONG_HORIZON_ENGINE;
benchmark package gains probe:pi/probe:legacy; TESTING.md documents the full matrix;
check_test_harness governance updated to REQUIRE x-istara-agent-engine capability.
Result: All suites can now assess both agentic loops; stale-surface assertions replaced
by current-architecture contracts.
Verified: simulation test:static 6 pass/0 fail; benchmark check pass; node --check on all
touched mjs OK; pytest marathon-integrity+harness 21 passed; chat/a11y/tokens/governance
36 passed; check_test_harness exit=0; check_workflow_contracts exit=0; feature-obligation
classifier over real range pass=true unknown=[].
Next: Owner Colima server to RUN broad live suites (probe/full/marathon both-engine);
VPS redeploy remains pending SSH direction.
```

DEC-9 | 2026-08-23 | owner
Context: VPS redeploy was pending SSH direction; owner redirected deployment to the Mac
Studio Docker host (ssh alias `macstudio`, 10.0.10.142) using key `multivac` naming.
Decision: Deployed the testing branch there via docker-compose.vps.yml (project
istara-testing); VPS deploy dropped. Secrets supplied via remote .env.deploy (chmod 600):
JWT_SECRET, ADMIN_PASSWORD, CORS_ORIGINS for LAN origins, ISTARA_PI_SECRET_PI_DEEPSEEK_DEFAULT
piped from local Keychain without display.
Why: Same-host deployment doubles as the live-provider target for both-engine test runs.

```
### L-9 | 2026-08-23T18:05:00Z | S5-ship | ox-alpha | executor | Deployment & live smoke
Did: Deployed testing@e72da9dd to macstudio:~/istara-testing (Docker 29.7.2). Fixed four
deploy blockers found en route, each committed+pushed:
 1) ADMIN_PASSWORD/ADMIN_USERNAME seam missing -> unpersistable bootstrap admin;
 2) TLS dir root-owned -> ISTARA_TLS_DIR configurable;
 3) backend image lacked pi-runtime+node -> repo-root build context, node in both stages,
    npm ci --omit=dev, root .dockerignore protecting LLMs//Model_Finetuning/data;
 4) supervisor worker path resolved to / in flattened layout -> PI_WORKER_ENTRY override;
 plus backend-net internal:true had no provider egress -> opened (caddy-only publishing,
 data/provider planes stay internal).
Result: LIVE VERIFICATION PASSED. Pi core: real DeepSeek turn ("PONG", deepseek-v4-pro,
pi-deepseek-default, stop). Legacy core: fail-closed provider_stub_chat_blocked (correct on
stub plane). Usage ledger records engine/model/endpoint per turn. Stack healthy at
http://10.0.10.142:13081 (Caddy same-origin) / :13080.
Verified: remote smoke.py output above; all five containers healthy; health=200 from LAN.
Next: Broad both-engine suites against this instance (ISTARA_API_URL/ISTARA_FRONTEND_URL);
three-model donor modes need Colima donors if requested; then Codex OAuth endpoint #2.
```

## Phase 6 — Unified provider plane (pi model management serves BOTH engines)

DEC-10 | 2026-08-23 | owner
Context: Owner defined the culminating architecture: Istara loop is first-class and NEVER
uses stubs (testing or production); users pick either engine; PI MODEL MANAGEMENT manages
provider/model communication for BOTH; LLM Servers retires entirely (pi manages local
endpoint configuration too); Petals keeps its own donation process which talks TO pi model
management (ensemble, compute registry/pool); provenance is precise everywhere (ensembles,
usage, menus); agents on any core/endpoint interoperate (A2A etc.). Entire testing process
(all scenarios, colima, benchmarks pi-vs-istara inside Istara's suite) validates this.
Decision: (1) Per-turn model precedence = explicit user selection (chat picker) outright >
explicit local endpoint > pi-managed endpoint > donation pool. (2) /api/llm-servers retires;
local-endpoint config migrates into pi model management surfaces. (3) Stub guard leaves the
chat path — unified resolution simply never selects a stub plane; QA harness stub remains
embeddings/wire-only. (4) Execution-only bridge: engines may execute turns over pi-resolved
endpoints; nothing pi-side is advertised as compute-pool capacity (donor-collision and
research-spine routing guarantees preserved).
Why: Culmination of the integration work; makes engine choice purely about loop semantics.

```
### L-10 | 2026-08-23T18:40:00Z | S5-ship | ox-alpha | executor | Phase 6a
Did: Implemented the unified provider plane (DEC-10): model_source resolver with approved
precedence (explicit > local-direct > pi-managed fallback on stub-marked planes > donations
untouched); pi_bridge execution-only OpenAI-compatible streaming bridge (tools + exact usage,
never advertised as pool capacity); legacy ReAct loop routes through it with full provenance
(route_evidence.plane, endpoint_id, serving model -> usage ledger); stub guard now blocks
only when NO non-stub source exists; architecture doc updated.
Result: LIVE VERIFICATION on Mac Studio deploy @ef0c5940: Istara core served real DeepSeek
turns through pi model management — default resolution AND explicit selection; ledger shows
engine=legacy model=deepseek-v4-pro endpoint=pi-deepseek-default stop=stop.
Verified: pytest test_chat+test_model_source = 20 passed; ruff clean; remote smoke_istara.py
output recorded above. Pre-existing local failures in tests/pi_production worker tests
reproduced without my changes (env-only).
Next: Phase 6b LLM-Servers retirement sweep; broad both-engine suites vs this instance;
Codex OAuth endpoint #2; spec accept.
```

```
### L-11 | 2026-08-23T19:10:00Z | S5-ship | ox-alpha | executor | Phase 6b
Did: Retired the LLM Servers surface (commit afa22d98): backend route + registration
(-672 lines), dead frontend client/types, test_llm_servers.py removed; scenario 36 rewritten
to pin retirement + catalog truth + identity-only configured view; marathon network
discovery/env-detection/cycle-M checks re-pointed to the unified catalog and PiModelManagement
sources; feature registry, QA capabilities, security benchmark trigger patterns (now cover
model_manager/endpoints/model_source), Tech.md, feature docs deprecated + site regenerated.
Result: pi model management is the sole provider configuration plane for BOTH cores.
Verified: 72 pytest passed (settings/marathon-integrity/obligations/capabilities/
model_source/chat); harness+workflow gates exit 0; security benchmark pass 100;
simulation static 6/0; tsc+eslint clean; feature docs regen check passed (86 features).
Live @afa22d98 on macstudio: /api/llm-servers gone (401 pre-auth gate); Istara-core
DeepSeek turns still BRIDGE with full provenance.
Next: Broad both-engine suites vs this instance; Codex OAuth endpoint #2; spec accept.
```

## Phase 7 — Tri-model configuration (DeepSeek + Codex Luna/Terra via OAuth)

```
### L-12 | 2026-08-23T19:45:00Z | S2-execute | ox-alpha | executor | Phase 7
Did: Configured the owner-specified three-model tier through pi model management on the
Mac Studio deploy: pi-codex-luna (gpt-5.6-luna, oauth, effort=low) and pi-codex-terra
(gpt-5.6-terra, oauth, effort=low) alongside pi-deepseek-default. Fixed en route (all
committed+pushed): Cloudflare 530 on urllib UA (oauth.py runtime UA); codex-responses
rejects temperature (pi-runtime filterParamsForApi + tests); durable ISTARA_ENV_FILE
persistence (config loader + env writers + compose volume + Dockerfile ownership).
Result: All three models serve real turns; endpoints + encryption key survive restarts.
Note: live API advertises effort levels none|low|medium|high|xhigh|max for gpt-5.6-* —
catalog metadata was stale; owner-requested "low" is valid and in use. Owner's
"deepseek v4 flash" note: current default endpoint model is deepseek-v4-pro; switching
to flash is a one-line settings change if desired.
Verified: smoke_istara.py + verify_three.py outputs above; restart persistence check
(endpoints + stable key) recorded.
Next: metrics capture extension; broad both/tri-engine suites; Codex endpoint #2 done ->
research-spine comparison can proceed after suites.

## Findings register (Phase 7 broad-suite runs) — owner-flagged for later revisit

| ID | Sev | Dim | Where | Finding | Status |
|----|-----|-----|-------|---------|--------|
| F-P2b | Major | Bugs | probe chat turns vs INFERENCE_PRESETS | Refined: server-side turns SUCCEED with real output (ledger: 1.1–7k output tokens, deepseek-v4-flash via pi-deepseek-default), but probe client sees empty content. Working hypothesis: MEDIUM preset max_tokens cap + reasoning-style flash output at thinking_mode=low consumes the completion budget before any visible content channel emits; probe sessions use default preset (no custom max_tokens). Fix direction: benchmark-created sessions pin inference_preset=custom with adequate max_tokens (env-driven), keeping product presets untouched. | open |

| F-S1 | Major (deferred) | Tests | simulation scenarios failing identically on BOTH engines (~43/77; e.g. 09-navigation-search, 10-agent-architecture, 11-agents-system, 12-chat-sessions, 13-task-agent-assignment, 16-findings-population, 19-file-preview, 20-all-skills-comprehensive, 23-memory-view, 24-context-dag, 74-2fa-login-flow, 78-real-time-voice, 79-engine-selector) | Owner assessment: the scenario expectations drifted from code/UI changes and were not re-seeded/updated alongside those changes. Near-identical cross-engine failure sets support this (not engine regressions). | open — DEFERRED by owner; revisit after Phase 7 completes |

```
### L-13 | 2026-08-24T01:30:00Z | S2-execute | ox-alpha | executor | Phase 7
Did: Logged owner directive (F-S1): the ~43 identical cross-engine simulation failures are
attributed to stale scenario expectations vs evolved product code/UI — a test-maintenance
debt item, deferred by owner until the rest of Phase 7 finishes.
Result: Register updated; triage of these failures postponed, not dropped.
Verified: both pass logs show matching failure lists (sim_legacy.log / sim_pi.log).
Next: continue queue (probes → marathon → T1 done → T2 live); revisit F-S1 afterwards.
```

## Findings register (Phase 7 continued)

| ID | Sev | Dim | Where | Finding | Status |
|----|-----|-----|-------|---------|--------|
| F-P1 | Major | Bugs | backend agent worker cycle (Postgres deploy) | `asyncpg DataError: can't subtract offset-naive and offset-aware datetimes` crashes Agent work cycle / istara-ui-audit SubAgents on every execution under Postgres — background agents are broken on deployed stacks | open |
| F-P2 | Major | Bugs | pi_bridge transport + resolver fallback | TWO stacked causes: (a) httpx TLS fingerprint drew Cloudflare 403 HTML from api.deepseek.com while urllib passed; (b) no-explicit-model fallback selected the codex-family endpoint (Responses API → 404 on /v1/chat/completions). Fixed: bridge dials via urllib+runtime UA (request-builder unit-tested); resolver excludes openai_codex family from Istara-bridge sources (codex models are Pi-engine-native). | fixed — live-verified 'SEAM' turn on deepseek-v4-flash @7d2e9351 |
| F-S1 | Major (deferred) | Tests | ~43 identical cross-engine simulation failures | stale scenario expectations vs evolved code/UI (owner assessment) | open — DEFERRED by owner |

Queue status: probes now authenticate and execute the full research-spine journey
(corpus upload, sessions, task review flows visible in run artifacts); marathon chain
requeued behind probes with detection fixes (project-scoped catalog probe, TLS tolerance).
pi_benchmark T0+T1 complete (60 records).

```
### L-14 | 2026-08-24T02:10:00Z | S2-execute | ox-alpha | executor | Phase 7
Did: Diagnosed probe auth/credential path (admin password env), fixed pi_bridge UA 403
(8fc83bed), durable-env + compose seams (d09629ba, f2fc41a7), marathon detection project-
scoped catalog + TLS tolerance, tri-model flash switch verified live (all three models
OK turns), launched probes+marathon queue.
Result: Realistic benchmark now executes end-to-end infrastructure-wise; two genuine
product findings logged (F-P1 datetime crash breaking Postgres agent workers; F-P2
success-in-ledger/empty-SSE mismatch on probe's first legacy turn).
Verified: scorecard blockers evolution recorded above; agentic_usage_rows shows legacy/
deepseek-v4-flash success row for probe turn 1.
Next: Fix F-P2 (streaming seam), assess F-P1 fix scope, let marathon finish, then T2.
```

## Phase 7b — CI triage (testing branch)

```
### L-15 | 2026-08-24T14:55:00Z | S2-execute | ox-alpha | executor | CI
Did: Triaged all failing testing-branch workflows. Four root causes identified and fixed
(commit b2eb658b):
 1. PI-RATCHET line-key drift (legacy.py 599->637 after bridge insert) -> allowlist re-pinned.
 2. feature-obligations fail-closed on unowned new paths -> testing.docker-runner feature
    registered covering runner/benchmark dual-core surfaces.
 3. backend production_rehearsal vs FastAPI>=0.141 lazy _IncludedRouter includes ->
    prefix-aware recursive unwrap in rehearsal route enumeration; REPRODUCED locally in an
    isolated fresh-deps venv before fixing, verified green in that env after.
 4. QA Artifact + CI qa-image GHCR tags uppercase repo slug rejected by registry ->
    lowercased via repo_lc step in both workflows.
Baseline finding: CI on testing was ALREADY red at 9d7c506 (pre-work) — rehearsal gap is
structural (unpinned fastapi upper bound), not caused by Phase 6/7.
Result: fixes pushed @b2eb658b; CI run in flight.
Verified: check_integrity coherent; obligations classifier passes over multi-commit range;
rehearsal ci-sim passed=True in isolated venv; yaml valid.
Next: watch CI; then propose restructured testing-branch CI (tiered lanes) per owner ask.

## Phase 7c — CI answers + independent audit consensus

**Owner Q1 — do the three models run inference in CI?** No, and it is now
structurally enforced: no workflow sets any provider secret; the only live-LLM
suite is marker-gated (`ISTARA_RUN_REAL_LLM_BENCHMARK`, never set in CI); full
pytest runs with `-m "not live_llm"`; an autouse conftest guard fails the suite
if that env is ever armed; rehearsal exercises pure route enumeration. Endpoints
are never consulted — resolution paths are monkeypatched/injected.

**Owner Q2 — pi model management integrity coverage today:** PI-RATCHET
count-to-zero, version provenance, dispatcher authority (W1), catalog/UX
contract tests, provider contracts, engine-precedence tests, resolver seam
tests, security benchmark triggers on the provider surfaces. Gaps accepted from
audit: catalog JSON schema validation, resolver error-taxonomy golden contract,
model-source precedence matrix, route_introspection unit tests, SSE golden
corpus — queued as tracked work.

**Independent audit (sub-agent, adversarial) — consensus record:**
Accepted & implemented now: duplicate qa-image build removed (tag-race +
~15min/push); `-m "not live_llm"` + conftest guard; top-level least-privilege
permissions with packages:write only where needed; fetch-depth:0 so changed-
file gates never go vacuous; loud failure on release writeback.
Accepted & queued: hash-pinned constraints.txt + weekly drift job;
changed-path COMMAND_CATALOG execution lane (makes obligations real);
catalog/resolver/introspection/SSE-golden contracts; actions SHA-pinning;
image retention; mutation gates to scheduled lane.
Rebutted/adjusted: pytest-socket immediately (deferred — needs careful unix/
localhost allowlist to stay hermetic); rehearsal "endpoints empty" invariant
(rehearsal also runs on deployed stacks where endpoints legitimately exist);
"desktop decorative" (kept green-and-blocking for now, revisit at restructure).

```
### L-16 | 2026-08-24T15:50:00Z | S2-execute | ox-alpha | executor | CI hardening
Did: Answered owner's token-spend question (zero by construction, now structural);
spawned independent adversarial auditor; reached consensus on 25 findings; implemented
6 quick-wins (commits c6d98dc1..aeac896e + fix); documented deferred set.
Result: CI push path loses ~15min duplicate build; zero-token structuralized.
Verified: yaml valid; harness+chat 30 passed locally post-guard; runs in flight.
Next: watch CI green; implement queued contracts + changed-path lane; T2 after probes.
```
