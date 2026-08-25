# Agentic-Core Integrity & Core-Capable QA — Build Stream lifecycle

```yaml
item: agentic-core-integrity-and-qa
branch: testing
cf: { spec: CF-SPEC-2, predecessor: CF-SPEC-1, task: CF-15 }
phase: "Phase 9 — completion blueprint, branch reconciliation, and terminal acceptance"
stage: S1-plan
status: in-progress
blocked_on: null
last: { agent: gpt-5-codex, at: 2026-08-25T00:36:05Z, ledger: L-27 }
next_action: "Commit this ledger-only transport checkpoint, push local testing to origin/testing without force, and query the remote ref for exact SHA equality."
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

## Phase 8 — Research Spine, Pi-management, and Docker benchmark remediation

### Owner contract and decisions

```
DEC-11 | 2026-08-24 | owner
Decision: Mac Studio verification is Docker-only. SSH may orchestrate Docker and inspect
container evidence, but must not install packages, run the benchmark through host Python or
Node, or load models directly on the macOS host.
Why: The Mac Studio is a container host, not a mutable benchmark workstation.

DEC-12 | 2026-08-24 | owner + codex audit
Decision: Full Research Spine assurance requires three distinct model identities. Separate
endpoints or donated routes serving the same model remain useful redundancy, but do not
count as independent bias-reduction coders and cannot satisfy the Fleiss-kappa ensemble gate.
Why: Endpoint replication does not create independent model judgments. The durable
Research Spine contract says distinct project-authorized models; the implementation and
tests had weakened that to endpoint identity.

DEC-13 | 2026-08-24 | owner
Decision: Pi Model Management is the provider-management authority for both selectable
agentic loop implementations. Petals donations remain a separately governed capacity plane
and enter Pi only through the consented, identity-pinned bridge; they do not bypass project
scope, route evidence, reliability, reconciliation, review, or report gates.
Why: Loop selection changes orchestration semantics, not the source of truth for configured
provider identities or the Research Spine governance boundary.
```

### S0/S1 audit result

- The provider/loop separation is implemented in the right direction: the dispatcher owns
  engine selection, Pi Model Management resolves configured providers, and the Petals bridge
  projects consented donors one way without making Pi a donor scheduler.
- The Research Spine independence oracle is wrong. `resolve_distinct`, Pi ensemble routing,
  `_select_pi_coders`, and `distinct_model_identities` treat endpoint identity as coder
  independence. Existing tests explicitly approve three endpoints serving `same-model` as a
  full three-model Fleiss-kappa run. This contradicts DEC-12 and can overstate bias reduction.
- The live benchmark produced no successful coding run, no coders, no code applications, no
  reconciliation, and no accepted promotion, yet its scorecard awarded Research Spine
  validation and traceability. The probe checks route/API shape rather than the terminal
  research state it claims to prove.
- The runner exits zero and prints `ALL DONE` despite blockers and low scores. It reuses one
  persistent Postgres volume, runs legacy before Pi with fresh-sandbox disabled, mounts the
  repository read-write, installs dependencies repeatedly in a floating image, points browser
  automation at an internal-only frontend URL, and uses corpus paths visible only to the
  runner container. These defects prevent fair engine comparison and reproducible acceptance.
- Current live evidence therefore does not prove that either engine completes the Research
  Spine, tool-call journey, or long-horizon journey. It proves infrastructure reachability
  plus several failures. Earlier positive score labels are withdrawn pending the Phase 8 run.

### Phase 8 acceptance contract

- AC-8.1: Pi `distinct=True` ensembles and Research Spine coder selection return one route
  per distinct normalized model identity and fail closed when fewer than the requested number
  of distinct models are available, even if more endpoint identities exist.
- AC-8.2: Legacy ensembles enforce the same model-diversity rule while retaining distinct
  route evidence and optional-spare behavior.
- AC-8.3: Three genuinely different models produce three independent code-application sets;
  Fleiss' kappa and companion Krippendorff alpha are computed from those sets; low agreement
  routes to reconciliation; accepted atoms remain unreportable until human review and Done.
- AC-8.4: Both loop engines reach configured providers through the Pi-management authority;
  a consented Petals donor is selectable through the bridge with explicit donated-route
  evidence, and an unconsented/unhealthy donor fails closed without becoming Pi capacity.
- AC-8.5: Benchmark Research Spine credit requires persisted evidence units, three successful
  distinct-model coders, code applications, a computed reliability result, reconciliation
  evidence when required, accepted promotion, and the human review/report gate state. A
  blocked or empty run scores false and emits a blocker.
- AC-8.6: Tool-call and long-horizon credit requires executed tool evidence and terminal task
  state, not model prose, endpoint reachability, or an HTTP 2xx alone.
- AC-8.7: Any blocker, missing mandatory journey, zero completed scored turns, or score below
  the configured acceptance threshold makes the runner exit nonzero; partial diagnostics are
  still preserved.
- AC-8.8: Each compared engine starts from an isolated fresh database and deterministic seed;
  run order is recorded and must not change results. Images/digests, commit SHA, compose
  render, container health, model/endpoint identities, inference parameters, and artifact
  hashes are captured.
- AC-8.9: Every remote command runs through Docker. The acceptance record includes a negative
  host-mutation audit (no package-manager invocation and no host Python/Node benchmark process).
- AC-8.10: CI, feature-documentation generation, security benchmark, targeted unit/integration
  suites, and Docker acceptance all pass or remain explicitly open; green unit tests alone are
  never described as live Research Spine proof.

### Remediation order

1. Correct model-identity semantics and regression tests first, because every later score
   depends on the oracle being honest.
2. Repair Research Spine probe assertions and benchmark failure semantics.
3. Isolate databases, paths, images, mounts, and run provenance.
4. Fix the concrete runtime blockers (connection-string 500s, telemetry identifier width,
   credential/decryption mismatch handling, output-budget truncation, and worker datetime
   handling) with causal tests.
5. Re-run local gates, then perform one bounded Docker-only Mac Studio acceptance using the
   three configured models; append unfiltered results and residual findings to `testing.md`.

```
### L-17 | 2026-08-24T17:06:00Z | S1-plan | codex | executor | Phase 8
Did: Re-opened the lifecycle under CF-SPEC-2/CF-15, recorded the Docker-only owner boundary,
audited the provider/loop/donation architecture, and found that endpoint identity had been
substituted for model independence in both implementation and tests. Reclassified the prior
live Research Spine score as unproven because its coding run was blocked with zero coders.
Result: Phase 8 acceptance and remediation order are durable; Compass Forge pre-change gate
record 5 captures the inherited failing baseline (231 issues, including known false-positive
secret-flow findings and route/type drift).
Verified: CF status/next/agent-brief; CF-SPEC-2 clarified, planned, tasked (CF-13..CF-21);
CF-15 work order; gate-before record 5; decision record 1; impact+why on the model manager,
reliability core/service, both ensemble implementations, and this lifecycle.
Next: Add red regression tests for same-model endpoint replicas, then implement fail-closed
distinct-model selection before touching the benchmark oracle.
```

### Phase 8 live evidence disposition

- Authoritative Docker run group: `cf-spec-2-20260824-r9`; source snapshot SHA-256
  `c737706072ec81f0de8fc3e5158137978e1d55b03e2ac82c7d25df931f84d979`;
  backend image `sha256:c61d10d3457fa0dcf0eefa8563af4358cdb28fcd7f7b6f14d8448e9fc26a8bbf`.
- Both arms used a fresh Postgres container, immutable recorded images, and a disposable
  runner container. Provenance records `container_only=true`,
  `host_dependencies_installed=false`; package installation occurred only inside the
  runner container.
- Legacy arm `2026-08-24T23-20-35-427Z`: score 51.6, 8 primary chat turns, 8 tasks
  created, 2 revision events, 0 approvals. Its scorecard correctly retained blockers for
  the review and report journey.
- Pi arm `2026-08-24T23-32-56-466Z`: score 59.4, 8 primary chat turns, 8 tasks created,
  9 revision events, 1 approval. The 24-turn Pi budget removed r8's deterministic turn-6
  exhaustion, but backend logs still recorded failed Pi task subturns with no assistant
  message persisted.
- Both coding runs used Pi-managed Luna, Terra, and DeepSeek routes and complete three-
  rater matrices. Legacy produced Fleiss kappa -0.029 / Krippendorff alpha 0.511; Pi
  produced Fleiss kappa -0.125 / alpha 0.491. Both were below the 0.6 threshold and
  correctly persisted `needs_reconciliation` with no accepted code applications.
- r9 revealed two remaining benchmark-oracle defects: the three raw spans came from one
  document, and Pi was called blocker-free despite zero reconciliation decisions and zero
  accepted code applications. Both defects are now fixed locally with paginated,
  source-diverse selection and fail-closed acceptance of only `accepted` or
  `accepted_after_reconciliation` coding runs. These final fixes are unit/integration
  verified but have not received a new live Docker retake.

```text
### L-18 | 2026-08-25T00:00:00Z | S2-execute | codex | executor | Phase 8 remediation
Did: Corrected distinct-model identity across Pi/legacy ensembles and Research Spine coder
selection; centralized provider authority through Pi management; hardened the consented
Petals projection; repaired migrations, telemetry widths/provenance, encrypted-field failure
handling, benchmark blocker exits, fresh per-engine database isolation, immutable provenance,
read-only source handling, Docker runtime health, AppleDouble filtering, and Pi token/turn
budgets. Added TDD coverage for each causal defect and regenerated living feature docs.
Result: local Python suite reached 1927 passed / 0 failed / 6 skipped; benchmark Node check
54/54; security benchmark 28/28 at 100%; feature docs 86/86 and 224 artifacts; diff check
clean. The implementation surface is substantially repaired, but live Research Spine
acceptance remains open.
Verified: targeted red/green tests; full pytest; benchmark `npm run check`; security and
feature-doc gates; Docker Compose rendering, container health, migrations, and image identity.
Next: run and audit the authoritative Docker comparison.

### L-19 | 2026-08-25T00:08:00Z | S4-review | codex | reviewer | r9 Docker acceptance
Did: Followed the Mac Studio Docker run through completion, retained both artifact sets,
compared chat/task/research telemetry, and re-measured the Research Spine result rather than
trusting the scorecard label. Found that r9 proved independent three-model coding and
reliability computation but did not prove reconciliation, accepted promotion, reportability,
Petals donation, corpus-wide processing, or fully reliable Pi task subturns. Added source-
diverse pagination and made unresolved low agreement a benchmark blocker.
Result: Pi is better than legacy on this bounded workflow, but neither arm is accepted as a
complete Research Spine journey. r9's Pi `blockers=[]` is withdrawn as an oracle false
positive; under the corrected oracle both arms remain blocker-bearing until human
reconciliation accepts evidence. The final oracle fix is not live-retaken.
Verified: r9 provenance and scorecards; route evidence for all three Pi-managed models;
complete coding matrices; kappa/alpha values; zero accepted applications/decisions; 54/54
benchmark checks; 50 affected Python tests; full 1927-test Python suite; Compass Forge
after-gate record 7 (failing, intentionally not accepted).
Next: source-diverse Docker retake with reconciliation and accepted/report-gate evidence,
then Petals donor, executed tool-call, long-horizon, UI-shell, and crossover-order proofs.
```

## Phase 9 — Completion blueprint, clean testing branch, and terminal acceptance

### DEC-14 | 2026-08-24 | S0-frame | owner
Context: Phase 8 materially improved correctness and test honesty but left the checkout dirty
and several live acceptance journeys open. A rate limit or agent change must not erase the
current position.
Decision: Expand this existing cardinal lifecycle instead of creating a competing plan file;
checkpoint its Status Block and append-only ledger at intervals no longer than two minutes
while active work is in flight. Reconcile the intended change onto local `testing`, push it
to `origin/testing`, and remove only worktrees/branches proven obsolete and safe to delete.
Why: One continuously current source of truth gives any replacement agent the full rationale,
exact evidence boundary, and next executable action without depending on chat history.

### L-20 | 2026-08-25T00:25:40Z | S1-plan | gpt-5-codex | planner | Phase 9
Did: Loaded the Build Stream and pinned-native Compass Forge contracts; oriented through
CF status, next, and compact agent brief; created the explicit completion goal; and resumed
this lifecycle as Phase 9 under the owner's clean-branch and two-minute-checkpoint mandate.
Result: CF-SPEC-2 remains active, CF-17..CF-21 are visibly open, and the current architecture
gate remains red with 237 projected issues. No commit, push, branch deletion, or worktree
removal has occurred yet.
Verified: pinned Rust Compass Forge status/next/agent-brief completed against recipe
`istara-main`; lifecycle Status Block now points to this ledger entry.
Next: inventory Git status, refs, worktrees, remotes, ancestry, ignored/sensitive files, and
the exact changed-file ownership boundary before drafting the detailed completion task graph.

### L-21 | 2026-08-25T00:27:55Z | S1-plan | gpt-5-codex | planner | Git truth inventory
Did: Reconciled the main checkout, local and remote testing refs, every registered worktree,
merged-branch membership, tracked/untracked changes, and the known sensitive-artifact names.
Result: main `testing` HEAD is exactly `origin/testing` at `1b9b6d6098dc4a420aff2cf570b9aa5b982b3949`;
all new implementation is still an uncommitted working-tree delta. Two clean conductor
worktrees are merged and eligible for later removal, two missing temporary worktrees are
prunable, one clean detached baseline is a removal candidate, and three older worktrees have
unique dirty state that must be inspected or preserved rather than deleted. The recovery
worktree remains intentionally out of cleanup scope. No listed secret artifact is present in
the main checkout.
Verified: `git status --short --branch`, `git rev-list --left-right --count`, two ancestry
checks, `git worktree list --porcelain`, per-worktree status/ahead-behind inspection,
`git branch --merged testing`, remote inventory, and exact-path sensitive-artifact checks.
Next: obtain Compass Forge impact/why and CF-SPEC-2/task truth, then encode the complete
Phase 9 task graph with dependencies, exact evidence, rollback, cleanup rules, and a
single-command resume point before staging any file.

## Phase 9 execution contract

### Why this phase exists

Phase 8 fixed substantial implementation and test-oracle defects, but it did not establish
terminal product truth. In particular, a three-model coding matrix plus a computed Fleiss
kappa is not equivalent to a successful Research Spine journey. The live r9 retake stopped
with low agreement, no completed reconciliation, no accepted code applications, and no
reportable downstream artifacts. The current checkout also contains 324 modified tracked
files and 10 untracked files on top of an otherwise non-diverged `testing` branch. Phase 9
therefore has two inseparable duties:

1. preserve and transport the intended implementation without losing another agent's work;
2. prove the full governed product behavior, including negative controls, in Docker on the
   Mac Studio before describing the architecture as complete.

### Governing invariants

- `testing` is the integration and evidence branch. A local commit is not transport; a push
  is not CI; CI is not Docker acceptance; Docker acceptance is not Compass Forge acceptance.
- Pi Model Management is the only provider/model authority. Istara, Agentic Loop, and Pi
  Agentic Loop remain independently selectable execution semantics, but each obtains model
  identity, endpoint, credentials, capability, and route evidence through Pi management.
- The removed classical/Alembic-era provider endpoint must not remain as a parallel runtime
  authority. Compatibility names may survive only at a typed boundary that delegates to Pi
  and is proven not to load, select, or call a model independently.
- Petals model donation may contribute consented compute through Pi Model Management, but
  cannot manufacture model diversity, bypass provider authorization, weaken tenant/project
  scope, or promote research artifacts.
- Research data follows the complete contract: source spans -> evidence units -> independent
  atomic extraction/open coding by three genuinely distinct configured model identities ->
  reliability and grounding -> reconciliation -> accepted atoms/nuggets -> facts -> insights
  -> recommendations -> In Review -> human-approved Done -> report. A missing gate is a
  blocker, not a scoring deduction that can be averaged away.
- Fleiss' kappa is evidence about categorical inter-rater agreement, not a generic quality
  score. The benchmark must preserve the item/category matrix, rater identity, missing-rating
  policy, category normalization, and enough per-item detail to recompute the statistic.
  Krippendorff's alpha and grounding measures are complementary diagnostics, not substitutes
  for reconciliation or human approval.
- No host package install, model load, backend/frontend server, benchmark runner, or live
  probe is permitted on the Mac Studio. SSH is transport/control only; execution and package
  installation occur in Docker containers. Host commands are limited to passive SSH/Git,
  Docker/Compose control, file transfer, and process/log observation.
- `LLMs/` and `Model_Finetuning/` are protected. Never clean, move, prune, or stage them.
- Runtime secrets, endpoint fingerprints, credentials, tokens, database snapshots, and
  private URLs never enter Git or this document. Evidence uses hashes, redacted identity
  handles, container/image identifiers, and artifact-relative paths.
- During active work, update the Status Block and append one ledger checkpoint at least every
  two minutes. A long command must be started in a resumable session; checkpoint immediately
  before it and immediately after it yields. Never rewrite old ledger entries.

### Current truth at Phase 9 start

| Surface | Established truth | Still unproven / unsafe to claim |
|---|---|---|
| Git integration | Local `testing` and `origin/testing` both point to `1b9b6d60`; the main checkout contains the Phase 8 delta. | No Phase 8 commit or remote transport yet; auxiliary dirty worktrees have not been reconciled. |
| Deterministic tests | 1,927 Python tests passed, 6 skipped; benchmark library 54/54; security 28/28; feature docs 86/86 / 224 artifacts. | Results precede the final source-diversity/oracle edit and current lifecycle edit; authoritative clean-commit rerun is pending. |
| Docker runtime | r9 ran in Docker and both arms produced artifacts; no host dependency install was reported. | A fresh immutable-commit retake of the corrected oracle is pending. |
| Model routing | Both arms recorded Luna, Terra, and DeepSeek coding routes through Pi management. | All production/background/skill/schedule callsites have not yet been structurally proven free of independent classical provider authority. |
| Ensemble | Three-rater matrices and kappa/alpha were produced for both arms. | Independence beyond labels, source/corpus breadth, reconciliation efficacy, and accepted promotion are not proven. |
| Research Spine | Low agreement correctly remained `needs_reconciliation`; final local oracle now fails closed. | No accepted reconciliation decision, accepted code application, downstream fact/insight/recommendation chain, Done task, or valid report was demonstrated. |
| Pi tasks | Larger Pi budget removed deterministic turn-6 exhaustion; Pi outscored legacy in r9. | Backend logs still contained task subturns with no persisted assistant message; long-horizon and two-call reliability are open. |
| Petals | Unit/contract coverage exists for consent and routing boundaries. | A live consented donate/use/revoke/stop lifecycle through Pi management is open. |
| UI | API and deterministic paths have broad coverage. | Browser-visible shell, engine chooser, error presentation, and absence of hidden 500s are open. |
| Compass Forge | CF-SPEC-2 is 100-quality, tasked, and names CF-13..CF-21. | Every task is still open; after-gate record 7 is red; no spec acceptance exists. |

### Worktree disposition register

This register is authoritative until a later ledger entry records a change. “Delete” always
means `git worktree remove` followed by safe `git branch -d`, never raw recursive deletion.

| Worktree | State | Phase 9 disposition |
|---|---|---|
| `/Users/user/Documents/Istara-main` | dirty `testing`; base equals `origin/testing` | Integrate reviewed Phase 8 and Phase 9 changes, commit, push, and keep. |
| `/private/tmp/istara-baseline-RyA031` | clean detached baseline at current old testing head | Remove after the integration commit is proven; no unique data. |
| `/private/tmp/istara-main-baseline` | missing/prunable | Prune registration after verifying the path remains absent. |
| `/private/tmp/istara-testing-merge-20260818` | missing/prunable | Prune registration after verifying the path remains absent. |
| `/private/tmp/opencode/ci-wt` | clean detached historical CI checkout | Preserve until owner/process/lock inspection proves it abandoned; do not infer from cleanliness. |
| `.../istara-pi-linearized-2026-08-10` | clean recovery branch equal to its remote | Preserve as intentional recovery/archive material. |
| `.../istara-pi-model-management-migration-20260818` | dirty; branch ahead 4/behind 176 | Inspect every unique commit and dirty path; integrate unique valid work or make a recovery commit. Never delete dirty state. |
| `.../istara-pi-model-management-migration-20260822` | clean; branch merged into testing | Remove worktree and then local branch after the new testing commit/push. |
| `.../istara-public-ci-testing-20260818` | merged branch but dirty untracked lock/docs | Compare with main; integrate or preservation-commit unique artifacts; only then reconsider removal. |
| `.../istara-testing-docker-20260817` | dirty docs/plans | Compare with main and preserve unique rationale/evidence; do not delete while dirty. |
| `.../istara-testing-remote-qa-20260817` | clean; branch merged into testing | Remove worktree and then local branch after the new testing commit/push. |

### Completion task graph

| ID | Task | Depends on | Completion proof |
|---|---|---|---|
| P9-01 | Reconcile all Git/worktree state | none | Classification manifest, no unaccounted files, unique dirty state integrated or recoverably preserved. |
| P9-02 | Create clean integration commit(s) and transport `testing` | P9-01 | Clean main checkout, local/remote SHA equality, remote branch query, push receipt. |
| P9-03 | Safely remove only obsolete worktrees/branches | P9-02 | Before/after worktree and branch inventories; no dirty or recovery target removed. |
| P9-04 | Prove Pi Model Management authority across every execution plane | P9-02 | Structural callsite inventory, negative legacy-authority tests, route evidence for all three selectable engines. |
| P9-05 | Prove ensemble independence and statistical correctness | P9-04 | Distinct effective identities, complete matrices, independent recomputation, adversarial same-model rejection. |
| P9-06 | Prove the full Research Spine, including reconciliation | P9-05 | Positive and negative Docker journeys with source-to-report lineage and fail-closed leakage assertions. |
| P9-07 | Prove two-call, tool-call, and long-horizon behavior | P9-04 | Executed-tool evidence, resumed checkpoints, persisted assistant outputs, bounded failure/retry proof. |
| P9-08 | Prove Petals donation lifecycle through Pi authority | P9-04 | Consent/use/revoke/stop evidence; tenant isolation; no diversity inflation or post-revoke routing. |
| P9-09 | Repair and validate benchmark methodology | P9-05, P9-06, P9-07 | Randomized/crossover design, source/corpus breadth, immutable provenance, calibrated blocker oracle. |
| P9-10 | Run Docker-only Mac Studio acceptance retake | P9-06..P9-09 | Container/image/commit provenance, complete artifacts, health/log evidence, no host install/load. |
| P9-11 | Browser-visible UI and error-path acceptance | P9-10 | All engine options usable, shell state correct, no hidden 500s, accessible failure/recovery states. |
| P9-12 | Broad regression, migrations, docs, security, and CI | P9-02, relevant fixes | Clean deterministic suite, fresh SQLite and PostgreSQL migration proof, docs/security outputs, CI terminal. |
| P9-13 | Independent blind review and remediation loop | P9-10..P9-12 | Reviewer verdicts, severity register, fixed or explicitly owner-waived findings, retest evidence. |
| P9-14 | Compass Forge evidence, gates, tasks, and acceptance | P9-13 | CF-13..CF-21 terminal with evidence, after-gate disposition, CF-SPEC-2 accepted only if truthful. |
| P9-15 | Final branch/repo closure | P9-14 | Clean worktrees, local/remote testing equality, artifact index, final lifecycle summary and rollback pointer. |

### Detailed execution instructions

#### P9-01 — Reconcile all Git and worktree state

1. Save `git status --short --branch`, `git diff --name-status`, `git diff --stat`, local
   and remote SHA, both ancestry directions, worktree porcelain, merged branches, and remotes.
2. Classify every main-checkout path as one of: production implementation, migration/schema,
   deterministic test, live benchmark, security control, living documentation source,
   generated living documentation, Build Stream/decision evidence, operator tooling, or
   unrelated/temporary. The last category is never silently staged or discarded.
3. Inspect `debug_rereview.py`, `fix_payload.py`, runner scripts, Docker files, recipe files,
   every untracked migration/test/doc, and generated-site churn explicitly. Verify generated
   changes reproduce from `scripts/feature_docs.py`; do not hand-curate generated HTML.
4. Scan staged candidates for secrets and endpoint fingerprints without printing secret
   values. Confirm protected model/training directories are absent from status and index.
5. For each dirty auxiliary worktree, compare commits and file content against main. Unique
   product code/tests/docs are brought onto `testing`; obsolete generated plans may be left
   on a preservation commit, but no uncommitted data may be destroyed.
6. Record an exact staging manifest in the ledger. Run `git diff --check` before staging and
   inspect the staged diff after staging. If a path's rationale cannot be explained, unstage
   it and keep the worktree dirty until resolved.

#### P9-02 — Clean integration and transport

1. Prefer coherent commits: implementation/migrations/tests/docs may be one atomic Phase 8
   commit when splitting would make either commit fail; the Phase 9 lifecycle/cleanup record
   may be a follow-up documentation commit. Never rewrite another agent's existing commit.
2. Rerun the smallest high-value deterministic checks affected by any post-r9 edits before
   commit. Commit with a descriptive conventional message and record the SHA immediately.
3. Verify main checkout cleanliness, commit tree, and local branch ancestry. Push the exact
   local `testing` ref to `origin/testing` without force. Query the remote ref after push and
   require exact SHA equality. If rejected, fetch and reconcile—never force-update.
4. Record separately: committed, pushed, remote-confirmed, CI-started, CI-terminal. A rate
   limit after commit or push must leave the next command and SHA in the Status Block.

#### P9-03 — Safe cleanup

1. Re-read porcelain immediately before cleanup and reject any candidate that is dirty,
   locked, active, unmerged, a recovery/archive ref, or not exact-path identified.
2. Remove only clean worktrees with `git worktree remove <exact path>`. Delete their local
   branch only with `git branch -d <exact branch>` after merge proof. Use `git worktree prune`
   only for already-missing registrations.
3. Do not delete remote branches in this phase unless a later explicit owner decision names
   them. Do not remove the clean recovery worktree or the opencode CI worktree without an
   abandonment/ownership proof. Record what was removed and recovery implications.

#### P9-04 — Pi Model Management as single authority

1. Build a graph-backed callsite inventory covering chat, websocket, tasks, agents, skills,
   schedules, background jobs, autoresearch, embeddings, A2A, compute registry, Petals, and
   benchmarks. For each, record model selection entrypoint, endpoint resolution, credential
   source, capability validation, route-evidence sink, and execution-engine semantic.
2. Prove Istara, Agentic Loop, and Pi Agentic Loop are selectable first-class modes. Each
   mode must preserve its own orchestration semantics while all model calls pass through Pi
   management. UI aliases and persisted enum values must map deterministically and survive
   a session/restart without falling back to a removed endpoint.
3. Add negative tests that make obsolete provider settings attractive and assert they cannot
   become runtime authority. Add direct-call spies/monkeypatches around legacy/classical
   clients so background paths fail a test if they bypass Pi. Compatibility APIs must emit
   explicit deprecation/delegation behavior, not silently create a second source of truth.
4. Exercise unavailable, unauthorized, capability-mismatch, timeout, partial stream, and
   endpoint-removal cases. Fail closed with actionable UI/API errors and no secret leakage.

#### P9-05 — Ensemble identity, independence, and reliability

1. A rater identity is the effective provider account + endpoint handle + model/checkpoint +
   relevant decoding profile, not merely a display name. Reject duplicate effective identities
   even when they have different aliases, donated routes, or request IDs.
2. Use at least three source-diverse evidence units and three distinct model identities. Keep
   prompts/codebook fixed within a comparison arm, isolate conversations and caches, and
   prevent one rater from reading another's output before reconciliation.
3. Persist raw source spans, candidate atoms/codes, grounding handles, normalized categories,
   missing/abstain states, the full item-by-rater matrix, and route evidence for every rating.
4. Recompute Fleiss' kappa independently from artifacts; test perfect agreement, chance-like
   agreement, disagreement, missing ratings, single-category degeneracy, category-order
   invariance, and duplicate-rater rejection. Cross-check Krippendorff alpha where applicable.
5. Treat low/undefined reliability as `needs_reconciliation`. Never infer acceptance from a
   positive benchmark score, completion status, or the existence of three responses.

#### P9-06 — Full Research Spine acceptance

1. Positive journey: ingest multiple raw sources; preserve exact spans; create evidence units;
   independently code; compute grounding/reliability; enter reconciliation; obtain an explicit
   human acceptance decision; apply accepted codes; derive atoms/nuggets, facts, insights, and
   recommendations with lineage; move a task to In Review then human-approved Done; generate
   a report that contains only accepted, lineage-complete artifacts.
2. Negative journeys: low agreement without reconciliation, synthesized prose without exact
   spans, rejected code, missing route evidence, same-model ensemble, missing human approval,
   task not Done, revoked source, cross-project evidence, and stale/deleted model route. Assert
   that no downstream/report endpoint leaks provisional content in each case.
3. Verify pagination and corpus breadth at every list boundary. The benchmark must not select
   the first three spans from one document and describe this as source diversity.
4. Verify every artifact has project scope, source/evidence lineage, coding-run/reconciliation
   identifiers, governance status, and reportability status. Test immutability/audit history
   when a source, model route, codebook, or decision changes.

#### P9-07 — Calls and long-horizon tasks

1. Define “two calls” as two independently persisted model interactions with route evidence,
   assistant output, tool/result lineage when relevant, and a deterministic continuation rule;
   do not count retries, hidden evaluator calls, or empty subturns as success.
2. For tool use, require proposed call -> authorization -> executed tool -> captured result ->
   model observation -> persisted final assistant response. A syntactically valid tool call or
   tool-success telemetry without a consumed result fails acceptance.
3. Run long-horizon tasks across checkpoint/restart boundaries and enough turns to exceed the
   former six-turn failure. Verify budgets, cancellation, resume idempotency, no duplicate side
   effects, bounded retries, persisted assistant messages, and explicit terminal states.
4. Inject model timeout, dropped stream, malformed structured result, unavailable tool, donor
   revocation, and process restart. Assert recovery or truthful failure without orphan tasks.

#### P9-08 — Petals donation through Pi

1. Use only explicitly consented test donation. Prove registration, capability advertisement,
   Pi-managed scheduling, one bounded inference, usage/accounting, revocation, draining, and
   no subsequent routing. Never load multiple heavy models merely to test discovery.
2. Verify donor and requester isolation, encrypted/redacted connection material, authorization,
   health expiry, concurrency/backpressure, cancellation, and cleanup on disconnect.
3. Ensure one physical checkpoint donated through multiple aliases counts as one ensemble
   identity and cannot satisfy three-rater diversity. Donor tool success cannot promote a
   model/skill or research artifact without the normal governance gates.

#### P9-09 — Benchmark validity

1. Replace fixed arm ordering with seeded randomization or a documented crossover; record seed,
   order, cooldown/cache state, commit SHA, image digest, config hashes, endpoint identity handles,
   model identities, decoding parameters, budgets, dataset/source IDs, timestamps, and host/Docker
   provenance. Redact secrets and private endpoint fingerprints.
2. Run both positive and fail-closed negative controls. The scorecard blocker list is derived
   from invariant assertions, not manually curated labels. Any missing required artifact blocks.
3. Calibrate deterministic stubs only for contract tests. Live claims require live model routes;
   live quality claims require sufficient repeated/crossover trials and uncertainty reporting.
4. Compare new failures against a clean `origin/testing` baseline when attribution is ambiguous.
   Separate harness/oracle defects, environment failures, product regressions, and model variance.
5. Retire or update the 43 stale scenario tests only after mapping each to a current route and
   contract. A scenario that never reaches its asserted surface cannot count as coverage.

#### P9-10 — Docker-only Mac Studio retake

1. Build from the transported immutable testing SHA. Render Compose first and capture the
   effective service/image/volume/network configuration with sensitive values redacted.
2. Over SSH, run only Docker/Compose operations. Capture `docker ps`, image digest, health,
   migrations, listeners reachable from the test container, benchmark session IDs, and logs.
3. Use fresh per-arm databases/volumes where comparison contamination is possible. Keep exact
   teardown commands and retain evidence artifacts before teardown. Do not reuse production data.
4. Monitor in bounded intervals and update this lifecycle every two minutes. On interruption,
   record container IDs, session IDs, last completed stage, artifact path, and exact resume command.
5. After completion, verify provenance says container-only and independently inspect commands/logs
   for host `pip`, `npm`, `uv`, package-manager, backend/frontend, or model-server execution.

#### P9-11 through P9-15 — Closure gates

- P9-11: drive the real browser shell for each engine, model selection persistence, task/research
  journey, reconciliation UI, report gate, donation consent/revocation, loading/empty/error/retry
  states, accessibility, console errors, network failures, and backend 5xx correlation.
- P9-12: run graph-selected targeted tests, Pi runtime Node tests, benchmark library checks,
  full Python suite, fresh SQLite and PostgreSQL migration upgrades, Compose render/health,
  security benchmark, feature-doc regeneration/check, diff check, secret scan, and CI. Explain
  every skip and compare broad failures to a clean baseline.
- P9-13: obtain an independent blind review of code, Research Spine methodology, benchmark oracle,
  security/tenant isolation, migrations, and Docker evidence. Re-measure important numbers before
  reading author conclusions. Remediate every P0/P1/P2 unless the owner explicitly accepts risk.
- P9-14: attach command/review/gate evidence to CF-13..CF-21, resolve projected gate findings as
  introduced regression, inherited debt, false positive, or accepted exception, and accept
  CF-SPEC-2 only when zero required task remains open and terminal evidence exists.
- P9-15: pull/fetch without destructive reset, verify all intended refs, ensure no worktree has
  unexplained dirty state, confirm local and remote testing SHA equality, index retained Docker
  artifacts, record rollback commit/instructions, update this lifecycle to terminal, and state
  any remaining non-blocking debt without calling it complete.

### Required evidence bundle

Store or link one redacted bundle per acceptance run containing:

- `provenance.json`: commit SHA, branch/ref, dirty flag, image digest, Compose hashes, container
  IDs, Docker-only attestation, config hashes, model route identity handles, seed/order, budgets;
- `source-lineage.json`: source/evidence spans and project scope;
- `coding-matrix.json`: raw independent ratings, normalized categories, abstentions, grounding;
- `reliability.json`: Fleiss inputs/result, independent recomputation, alpha and diagnostics;
- `reconciliation.json`: disagreements, actor, decision, rationale, accepted/rejected applications;
- `promotion-lineage.json`: accepted atoms/nuggets -> facts -> insights -> recommendations;
- `task-report-gates.json`: In Review, human-approved Done, report inclusion/exclusion proofs;
- `route-evidence.json`: engine, Pi-managed model identity, endpoint handle, provider/capability;
- `tool-long-horizon.json`: calls, tool execution/results, checkpoints, restarts, terminal messages;
- `petals-lifecycle.json`: consent, scheduling, accounting, revoke/drain/no-route-after-revoke;
- `api-browser-results.json`: requests, statuses, console errors, correlated server logs/screenshots;
- `commands.log` and `tests.xml`: exact redacted commands, exits, durations, skips/failures;
- `review.md`: independent verdicts and remediation mapping;
- `artifact-manifest.sha256`: integrity digest for every retained artifact.

### Resume protocol for any agent

1. Read the YAML Status Block, then the last three ledger entries, then this Phase 9 contract.
2. Run pinned-native Compass Forge `status`, `next`, and one compact `agent-brief`; refresh the
   index if stale. Do not assume CF task state from this document alone.
3. Run `git status --short --branch`, local/remote SHA checks, and worktree porcelain. If reality
   differs, append a checkpoint explaining the difference before acting.
4. Continue the exact `next_action`; do not create a second Build Stream plan. Before every
   nontrivial edit, run Compass Forge impact and why for that path.
5. Every two minutes update `last`, `next_action`, and append `L-N`. Include completed action,
   result, verification, blocker if any, and the exact next command/action. Never claim an old
   test result covers a newer commit.

### L-22 | 2026-08-25T00:28:59Z | S1-plan | gpt-5-codex | planner | Completion blueprint
Did: Re-resolved and digest-verified the installed native Compass Forge release after its prior
release filename changed; ran graph-backed impact/why and inspected CF-SPEC-2; then expanded
this lifecycle with the full Phase 9 invariants, worktree disposition, fifteen-task dependency
graph, detailed execution/negative-control instructions, evidence schema, and resume protocol.
Result: another agent can now resume from Git reconciliation through Docker acceptance and CF
closure without relying on chat history. CF confirms full blast radius across chat, settings,
Pi runtime, legacy semantics, research, Petals, skills, websocket, tasks, and migrations; all
CF-13..CF-21 remain open. The native `task list` build does not accept `--spec`, so task truth
was taken from `spec show CF-SPEC-2` rather than an unsupported fallback.
Verified: binary digest `559af310d332ab72ceeb75bdd057b54f43b185ce875b93f7b3943d988b5be2c1`,
native capabilities/version, Compass Forge impact/why, and CF-SPEC-2 task payload.
Next: execute P9-01 by classifying every changed/untracked path—including all dirty auxiliary
worktrees—before producing the staging manifest and first clean integration commit.

### L-23 | 2026-08-25T00:33:41Z | S1-plan | gpt-5-codex | integrator | P9-01 classification
Did: Inspected the main checkout's utility, Docker runner, recipe, untracked, largest-diff,
generated-doc, protected-path, and secret-pattern surfaces; then inspected commits, dirty
diffs, untracked files, sizes, hashes, and representative content in all three dirty auxiliary
worktrees.
Result: the 324 tracked paths classify as 25 backend, 1 tracked migration, 7 Pi runtime,
27 general tests, 10 benchmark, 2 security, 2 architecture docs, 22 Build Stream, 13 living
feature sources, 202 generated feature-site artifacts, 3 Docker, 3 scripts, 3 recipes, and
7 root/other. The ten untracked main paths are three forward migrations, two historical QA
documents, two benchmark-provenance modules/tests, and three regression tests. The generated
site is required output, not accidental churn. No private-key/bearer/database-credential
pattern was found in candidate files; protected artifact folders are not candidates. Local
path/Mac-Studio references occur only in operator/history documentation and the Docker runner,
where they are intentional context rather than embedded credentials.
Result: the old public-CI worktree lockfile differs from the current ignored lock and must not
replace it; two zero-byte instruction files and one architect brief are abandoned planning
artifacts. The Docker-readiness worktree contains five unique historical plan drafts. The
20260818 Pi-migration worktree contains four unique commits plus a manifest and Plan B; its
content was superseded operationally but still carries recoverable rationale. No dirty
auxiliary file has been deleted or overwritten.
Verified: categorized name inventory; `git diff --check`; filename-only credential scan;
ignored/protected checks; per-worktree status, log, `git cherry`, hashes, sizes, diffs, and
representative reads.
Next: create recoverable preservation commits for unique auxiliary dirty state instead of
discarding it, then stage and inspect the entire classified main-checkout change set.

### L-24 | 2026-08-25T00:34:44Z | S2-execute | gpt-5-codex | integrator | P9-01 staged
Did: Created recovery commits for every unique dirty artifact in the three auxiliary legacy
worktrees, making each worktree clean without discarding data. Staged the complete classified
main-checkout delta and started the post-oracle benchmark plus targeted Python gate in resumable
terminal session `84308`.
Result: recovery SHAs are `465e0cf` (20260818 Pi migration), `c198138` (public CI), and
`2c14264` (Docker readiness). The main staging manifest contains 334 files with 7,292 additions
and 2,263 deletions; `git diff --cached --check` and the staged filename-only credential scan
are clean. No commit or push has occurred yet. The benchmark check was running and had reached
10 passing Node subtests when this checkpoint was written.
Verified: all three auxiliary `git status --short --branch` outputs are clean; staged status,
stat, whitespace check, and credential scan completed; test session ID is recorded for resume.
Next: poll session `84308`; on a green exit, restage this lifecycle checkpoint, inspect the
final staged summary, commit, verify local cleanliness, and push without force.

### L-25 | 2026-08-25T00:35:07Z | S2-execute | gpt-5-codex | integrator | Targeted gate correction
Did: Polled session `84308`. The benchmark library completed 54/54 passing tests; the chained
Python command did not start tests because `backend/.venv` has no pytest module. Inspected
existing interpreters without installing or changing dependencies.
Result: Node/benchmark verification is green. The Python portion is unexecuted, not failed.
An already-installed `/opt/homebrew/bin/pytest` is available, so the retry requires no install.
Verified: terminal exit/output, pytest discovery, interpreter paths. No source or environment
mutation occurred.
Next: run the same targeted Python selection with `/opt/homebrew/bin/pytest`; if green, restage
the lifecycle checkpoint, inspect the final index, commit, and verify the local branch.

### L-26 | 2026-08-25T00:35:41Z | S2-execute | gpt-5-codex | integrator | Pre-commit gate green
Did: Ran the post-oracle Python selection with the existing system pytest and waited for the
terminal process to exit cleanly.
Result: 86 targeted Python tests passed in 8.50 seconds; combined with the immediately prior
54/54 Node benchmark result, the changes made after the last full-suite run have focused green
coverage. No dependency installation or live model/server activity occurred.
Verified: pytest process exit 0 and complete result line; benchmark session's 54/54 result.
Next: restage this checkpoint, commit the atomic integration set on `testing`, verify the
resulting tree is clean and ahead of the unchanged remote by exactly one commit, then push.

### L-27 | 2026-08-25T00:36:05Z | S2-execute | gpt-5-codex | integrator | Main integration committed
Did: Restaged the final lifecycle state, rechecked the index, and created the atomic Phase 8/9
integration commit on local `testing`.
Result: commit `f768e83d` (`fix: harden Pi model authority and research spine QA`) contains the
334-file integration set. The checkout was clean immediately after commit; local `testing` is
ahead of `origin/testing` by exactly one commit (`0 1`) with no remote-only commit. Nothing has
been pushed yet.
Verified: commit receipt, post-commit status, ahead/behind count, and decorated one-line log.
Next: commit this ledger-only checkpoint, push both commits to `origin/testing` without force,
then query the remote ref and require exact local/remote SHA equality.
