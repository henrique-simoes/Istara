# Agentic-Core Integrity & Core-Capable QA — Build Stream lifecycle

```yaml
item: agentic-core-integrity-and-qa
branch: testing
cf: { spec: CF-SPEC-2, predecessor: CF-SPEC-1, task: CF-15 }
phase: "Phase 9 — completion blueprint, branch reconciliation, and terminal acceptance"
stage: S2-execute
status: in-progress
blocked_on: null
last: { agent: gpt-5-codex, at: 2026-08-26T23:30:00Z, ledger: L-204 }
next_action: "Commit and push the profile-isolated benchmark and lifecycle-cleanup changes, verify local/origin testing parity, then run the terminal Docker-only provider/Petals/combined retake when owner-authorized provider credit and three Compose-owned donor routes are available."
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
| `<repo-root>` | dirty `testing`; base equals `origin/testing` | Integrate reviewed Phase 8 and Phase 9 changes, commit, push, and keep. |
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
| P9-04 | **Complete** — Prove Pi Model Management authority across every execution plane | P9-02 | Structural callsite inventory, negative legacy-authority tests, route evidence for all three selectable engines. |
| P9-05 | **Complete** — Prove ensemble independence and statistical correctness | P9-04 | Distinct effective identities, complete matrices, independent recomputation, adversarial same-model rejection. |
| P9-06 | **In progress** — Prove the full Research Spine, including reconciliation | P9-05 | Positive and negative Docker journeys with source-to-report lineage and fail-closed leakage assertions. |
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
5. Close the unimplemented embedding-authority contract in ordered, migration-safe slices:
   (a) add an additive `EmbeddingProfile` schema/model and one-time idempotent bootstrap that
   preserves the exact pre-migration model + endpoint identity as version 1; (b) make Pi Model
   Management resolve embeddings by the profile's exact endpoint and model, rejecting a missing
   endpoint or capability mismatch rather than consulting `llm_provider`; (c) route cache keys,
   provisioning, startup probes, vector health, Settings/Project/Memory safe metadata, and both
   selectable execution engines through the active profile; (d) persist/bind each LanceDB vector
   store and cache namespace to profile ID/version while treating untagged existing stores as the
   version-1 bootstrap identity only after dimension verification; (e) keep profile mutation
   unavailable until a separately tested re-embed/reindex workflow can create a new inactive
   version, migrate every project and cache namespace, verify dimension/dtype/normalization, and
   atomically activate or roll back. Required negative tests: changing classical provider settings
   after bootstrap changes nothing; same model on another endpoint cannot steal the route; missing
   pinned endpoint fails closed; duplicate active versions fail; untagged/mismatched stored vectors
   cannot be searched or overwritten; chat model/engine selection never mutates the profile.

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

### L-28 | 2026-08-25T00:36:40Z | S2-execute | gpt-5-codex | integrator | P9-02 transported
Did: Committed the prior ledger checkpoint as `58ee0ca5`, pushed local `testing` to
`origin/testing` without force, queried the remote branch directly, and reconciled tracking
refs and worktree status.
Result: local `testing`, `origin/testing`, and the remote `refs/heads/testing` all equal
`58ee0ca59381925a07fa7d032b63f17354cf5503`; ahead/behind is `0 0`; the main checkout was
clean after transport. This proves commit and remote transport, not CI or terminal acceptance.
Verified: GitHub push receipt, local rev-parse, `git ls-remote`, status, and ahead/behind count.
Next: revalidate exact cleanup targets and execute only the safe P9-03 removals; retain every
dirty, recovery, locked, active, or ownership-uncertain worktree/branch.

### L-29 | 2026-08-25T16:20:09Z | S2-execute | gpt-5-codex | integrator | P9-03 cleanup complete
Did: Revalidated each cleanup target's cleanliness, lock/registration state, and merge status;
removed the clean detached baseline, both clean merged conductor worktrees, and the three clean
legacy worktrees whose unique artifacts had already been preservation-committed; deleted only
the two local branches proven merged into `testing`; and pruned the two already-missing worktree
registrations.
Result: six obsolete worktree directories/registrations were removed. Local branches
`conductor/istara-pi-model-management-migration-20260822` and
`conductor/istara-testing-remote-qa-20260817` were safely deleted with `git branch -d`.
Unique preservation branches remain at `465e0cff`, `c198138c`, and `2c142649`. The intentional
recovery checkout and ownership-uncertain `/private/tmp/opencode/ci-wt` remain untouched. The
only registered worktrees now are main `testing`, the recovery checkout, and the CI checkout.
Verified: exact-path `git worktree remove` receipts, safe branch-deletion receipts, prune
receipt, after-state worktree/ref inventory, clean main status, and local/remote testing SHA
equality at `36b06429e1f9fef564476be5e71c1ae8f9e0b991` before this ledger edit.
Next: commit and push this cleanup record, then begin P9-04 by mapping every production model
execution plane to Pi Model Management authority and writing negative bypass tests where absent.

### L-30 | 2026-08-25T16:22:05Z | S2-execute | gpt-5-codex | auditor | P9-04 authority audit started
Did: Re-oriented the pinned native Compass Forge control plane after the continuation gap,
claimed the CF-15 implementation work order, detected that the repository index predated the
transported 334-file delta, refreshed project state and the graph index, obtained a new
model-authority context pack, searched direct provider/network/model-manager construction, and
ran the existing classical-plane count-to-zero ratchet plus its highest-value authority tests.
Result: the refreshed graph indexes 853 files with no warnings. The legacy-plane scanner
reports zero of its known bypass patterns, and 64 migration/dispatcher/engine/tool-authority
tests pass. This is strong regression evidence for known patterns but is not yet P9-04 proof:
the scanner does not cover every direct provider constructor, startup compatibility path,
frontend donor proxy, background/autoresearch route, or obsolete settings API.
Verified: native CF refresh/index run 4; context pack path graph; scanner output `0`; pytest
exit 0 with `64 passed in 5.24s`.
Next: inspect and map the uncovered execution planes, extend the ratchet where needed, and add
negative tests for every material authority seam before calling P9-04 complete.

### L-31 | 2026-08-25T16:24:50Z | S2-execute | gpt-5-codex | auditor | P9-04 uncovered bypasses
Did: Ran Compass Forge impact and why for the settings route and startup module, then inspected
the model inventory/mutation endpoints, startup provider detection and loading sequence, their
frontend/simulation callers, and existing tests and allowlist references.
Result: two material classical-authority paths remain despite the count-to-zero result. First,
`POST /api/settings/provider` recreates the global provider singleton and persists
`LLM_PROVIDER`, while `POST /api/settings/model` can pull an Ollama model and mutate/persist the
classical active-model settings outside Pi Model Management. Second, application startup calls
`auto_detect_provider`, may switch the global provider, may pull an Ollama model, probes LM
Studio by chat completion, and mutates/persists the selected model. The read-only
`GET /api/settings/models` also mixes classical health/model discovery with a Pi catalog; that
surface needs a compatibility contract rather than unexamined deletion because onboarding,
simulation, and model visibility currently consume it.
Verified: graph-backed impact/why; exact route and startup source inspection; repository-wide
caller/test inventory. No code or environment was changed and no live model probe was sent.
Next: write failing tests that forbid provider recreation, model pulling, and startup authority
mutation while preserving a Pi-governed read-only compatibility inventory; run the narrow red
suite before implementing the smallest authority fix.

### L-32 | 2026-08-25T16:26:15Z | S2-execute | gpt-5-codex | implementer | P9-04 red authority contracts
Did: Added route-level negative contracts for both classical model-management writes and a
startup-source tripwire for every authority operation missed by the original scanner, then ran
only those new tests before changing production code.
Result: the red gate failed for the intended reasons: both compatibility writes reached their
forbidden provider/model side effects and returned 500 under the test traps instead of a stable
410 migration response; startup still contained all four forbidden classes—auto provider
selection, environment persistence, model pulling, and completion-based loaded-model probing.
This is causal red evidence, not an inherited suite failure.
Verified: targeted pytest produced exactly 3 failures (2 route cases + 1 startup contract), 43
deselected, with each assertion naming the pre-existing bypass. `git diff --check` remains clean.
Next: preserve read-only discovery, remove only the authority-changing startup block, make both
legacy writes fail closed with successor metadata, and rerun the same three tests green.

### L-33 | 2026-08-25T16:28:45Z | S2-execute | gpt-5-codex | implementer | Classical authority fix green
Did: Converted both authenticated classical model-management write routes into side-effect-free
compatibility adapters returning a stable 410 response with `Deprecation` and successor `Link`
metadata; removed startup's provider auto-selection, model pulling, completion probe, settings
mutation, and environment persistence while leaving configured-node registration, discovery,
persisted transport loading, and health checks intact.
Result: Pi Model Management is now the only runtime write authority on these seams. Old clients
receive an actionable migration response instead of silently creating a second source of truth.
Startup no longer chooses or loads a chat model merely because the application booted. Read-only
transport/model inventory remains available and has not yet been redesigned.
Verified: the exact red suite is now green (`3 passed, 43 deselected`); forbidden startup markers
are absent; `git diff --check` is clean. No server, model, provider probe, or dependency install
was run on the host.
Next: run settings/migration/startup-adjacent regressions, synchronize living feature docs and
generated site, then commit/push this bounded checkpoint before continuing P9-04.

### L-34 | 2026-08-25T16:30:10Z | S2-execute | gpt-5-codex | implementer | Authority regression checkpoint
Did: Used Compass Forge test-impact/suggest-tests to select the broader seam coverage, updated
the living Chat Model Controls architecture contract and its references, regenerated the
feature site/manifests, and reran the migration scanner after the production fix.
Result: settings, migration, Pi UX parity, Pi endpoint, model-source, and compute-config tests
are green; the feature documentation is synchronized; and the legacy direct-call scanner still
reports zero. Generated changes are limited to the expected feature HTML and manifest entry.
Verified: `64 passed in 5.33s`; feature docs `0 seeded`, `224 artifacts`, `86 features`, pass;
scanner `0 legacy-plane call site(s)`; `git diff --check` clean.
Next: create and push a bounded authority commit, require local/remote SHA equality, then resume
the uncovered-plane audit rather than treating this checkpoint as P9-04 completion.

### L-35 | 2026-08-25T16:30:45Z | S2-execute | gpt-5-codex | integrator | Authority fix transported
Did: Staged only the eight reviewed source/test/living-doc/generated-doc paths, committed them as
`1bf24082` (`fix: make Pi model management authoritative`), pushed without force, and compared
the remote branch ref with local HEAD. Then resumed the audit at the autoresearch runner seam.
Result: local `testing`, `origin/testing`, and remote `refs/heads/testing` all equal
`1bf2408230d9fce13f0bbd4a2386866c0179e5f2`; the checkout was clean immediately after push.
Autoresearch execution calls already go through `AgenticDispatcher` for both engine choices, but
the model-temperature runner still obtains candidate models from `llm_router.list_models()` when
the Istara engine is selected. That is a remaining model-management split: loop semantics are
correctly engine-specific, while candidate catalog authority is not yet shared.
Verified: commit/push receipts and exact local/remote SHA equality; source/caller inventory for
all autoresearch runners; no live inference or model loading.
Next: use Compass Forge impact/why for the model-temperature runner and its W6 tests, establish a
red contract that both engines use Pi endpoint identities, then remove the legacy catalog read.

### L-36 | 2026-08-25T16:32:35Z | S2-execute | gpt-5-codex | implementer | Autoresearch catalog authority unified
Did: Added and ran a red W6 contract that selects Istara execution semantics while making any
`llm_router` catalog read fail, then changed `ModelTempRunner` to build every engine's sweep from
the PiModelManager catalog and updated runner documentation to separate loop semantics from model
authority. Ran the complete W6 autoresearch runner suite after the fix.
Result: the red test failed exactly at `_legacy_sweep_endpoints -> llm_router.list_models`; after
the change both Istara and Pi experiments retain exact Pi endpoint identity through candidate
selection while `engine=self.engine` still selects their distinct execution semantics. The
obsolete legacy catalog method was removed.
Verified: exact red failure; green W6 suite `49 passed in 0.61s`; migration scanner remains zero;
`git diff --check` clean. No live model, server, or dependency operation occurred.
Next: update/regenerate the autoresearch living feature contract, run engine-selection and API
regressions, then checkpoint this fix before auditing the next authority surfaces.

### L-37 | 2026-08-25T16:34:10Z | S2-execute | gpt-5-codex | implementer | Autoresearch regression and documentation gate
Did: Updated the Autoresearch Experiments living architecture contract to state that both Istara
and Pi execution semantics obtain exact endpoint identities from Pi Model Management, regenerated
the feature site/manifests, and ran the broader W6 engine-selection, fail-closed, and API suites.
Result: the unified catalog authority is covered beyond the narrow runner unit test, and generated
documentation is synchronized with the implementation. Only the expected runner, test, lifecycle,
living-document, generated HTML, and manifest paths are dirty before the bounded commit.
Verified: `91 passed in 4.60s`; feature docs `0 seeded`, `224 artifacts`, `86 features`, pass;
`git diff --check` clean. No live inference, server startup, model load, or dependency install ran.
Next: stage only the seven expected paths, commit and push without force, compare exact local and
remote `testing` SHAs, then continue the uncovered-plane audit.

### L-38 | 2026-08-25T16:34:46Z | S2-execute | gpt-5-codex | integrator | Autoresearch authority transported
Did: Staged only the seven reviewed autoresearch source/test/lifecycle/living-doc/generated-doc
paths, committed them as `cc27ff50` (`fix: unify autoresearch model catalog authority`), pushed
without force, and compared the remote `testing` ref with local HEAD.
Result: local HEAD and `origin/testing` both equal
`cc27ff50aa867f033ca63fa6bdcf44d4b4e0cb16`; the checkout was clean immediately after push.
This is a bounded authority checkpoint, not completion of P9-04 or the wider delivery.
Verified: commit/push receipts, exact local/remote SHA equality, and clean worktree after push.
Next: map every remaining task, loop, A2A, skill, donated-compute, and frontend caller; classify
read-only transport compatibility separately from forbidden execution or write authority.

### L-39 | 2026-08-25T16:36:16Z | S2-execute | gpt-5-codex | implementer | Frontend and simulation authority leak mapped
Did: Ran a graph-backed context pack plus per-file Compass Forge impact/why over the settings API,
Settings inventory, merged catalog, unit test, simulation runner/client, and scenario 26, then read
the exact callers and contracts. Loaded the TypeScript red-green-refactor discipline before edits.
Result: read-only `/api/settings/models` inventory is a valid compatibility surface, but the UI
still marks every classical row `switchable`, renders Switch/Pull controls, and calls the retired
write routes. The simulation runner, client, and scenario 26 also mutate and restore the classical
global model, so current simulation would fail against the intentional 410 and tests the obsolete
architecture rather than Pi authority. These are confirmed remaining P9-04 gaps.
Verified: graph impact/why receipts for all seven candidate paths; exact caller inventory; no code,
server, model, dependency, or remote-host operation in this audit step.
Next: establish one failing catalog contract, make all compatibility rows inventory-only, then
remove client/UI mutation affordances and rewrite simulation setup/scenario assertions around the
Pi catalog plus fail-closed legacy writes.

### L-40 | 2026-08-25T16:40:12Z | S2-execute | gpt-5-codex | implementer | Frontend authority red-green slice
Did: Added one catalog red contract, observed its exact failure, made every merged compatibility
row explicitly non-switchable, removed Settings Switch/Pull affordances and both frontend write
methods, removed the simulation client's mutation method, and changed fixed-model setup to validate
Pi admission without mutating global state. Reframed scenario 26 to assert Pi endpoint inventory,
both legacy 410 successors, unchanged compatibility inventory, and existing session persistence.
Result: the red catalog assertion failed because classical rows were still `switchable: true`; it
is now green. The migration client tripwire initially found five active classical callers and now
passes, while the scenario retains the retired URLs only as deliberate negative-contract probes.
Verified: catalog red `1 failed, 6 passed`; catalog green `7 passed`; migration green `18 passed`.
A combined follow-up command then stopped at its frontend step because npm was run from repo root
(`ENOENT package.json`), a verification-command cwd error rather than a product failure; subsequent
syntax and broader gates remain pending. No dependency install, server, or model operation occurred.
Next: rerun the frontend unit test from `frontend/`, validate all three `.mjs` files with Node syntax
checks, update living documentation, regenerate manifests, and execute broader regressions.

### L-41 | 2026-08-25T16:42:17Z | S2-execute | gpt-5-codex | implementer | Frontend and simulation regression gate
Did: Removed the two obsolete mutation selectors, changed Settings scenario 10 to require the Pi
management UI and absence of classical Switch/Pull controls, updated the Chat Model Controls living
contract, then ran frontend typing/lint/unit tests, five modified simulation syntax checks, and the
broader settings/migration/project-scope/Pi-catalog backend suites.
Result: frontend code type-checks and lints; both targeted Vitest files and all selected backend
regressions pass; every modified simulation module parses. The UI, client, runner, and simulations
now share the same sole-authority contract. A combined command stopped after those green gates only
because it named nonexistent `scripts/scan_legacy_model_plane_calls.py`; the real repository scanner
is `scripts/pi_migration_inventory.py`, so scanner/docs remain pending rather than falsely claimed.
Verified: TypeScript `tsc --noEmit` pass; targeted ESLint pass; Vitest `10 passed`; pytest `90 passed
in 5.58s`; five Node `--check` passes. No live service/model/dependency operation occurred.
Next: run the correct deterministic scanner, regenerate/check the feature artifacts, review the
bounded diff, then transport this checkpoint with exact local/remote SHA proof.

### L-42 | 2026-08-25T16:42:50Z | S2-execute | gpt-5-codex | implementer | Frontend authority documentation gate
Did: Corrected the scanner invocation to the repository's supported no-flag interface, regenerated
the feature site/manifests, checked whitespace, and reviewed the complete path/stat boundary.
Result: the deterministic scanner remains at zero; living documentation is synchronized; the diff
contains exactly fourteen expected lifecycle, feature-doc/generated-doc, frontend, migration-test,
and simulation paths. The earlier unsupported `--check` option was a command-shape error and was not
counted as product evidence.
Verified: `0 legacy-plane call site(s)`; feature docs `0 seeded`, `224 artifacts`, `86 features`,
pass; `git diff --check` clean; expected fourteen-path status only.
Next: commit and push this bounded slice, compare exact local/remote SHAs, then continue backend
task/loop/A2A/skills/donor and formal Research Spine implementation/test audits.

### L-43 | 2026-08-25T16:43:18Z | S2-execute | gpt-5-codex | integrator | Frontend authority transported
Did: Staged only the fourteen reviewed paths, committed them as `6a20dbc1` (`fix: retire
classical model management clients`), pushed without force, and compared local HEAD with the remote
`testing` ref.
Result: local and remote `testing` both equal
`6a20dbc1e0903224a81aa5d87b61550a6bd4186e`; the checkout was clean immediately after push.
The runtime, UI, and simulation clients now agree that Pi Model Management is the sole write
authority, while classical inventory remains read-only compatibility metadata.
Verified: commit/push receipts, exact SHA equality, clean post-push worktree.
Next: inspect the ensemble and full Research Spine implementation/test oracles for real three-model
independence, reliability statistics, grounding/reconciliation, acceptance, and human report gates.

### L-44 | 2026-08-25T16:46:12Z | S2-execute | gpt-5-codex | reviewer | Formal ensemble audit isolates grounding defect
Did: Used the Compass Forge context/impact/why/test-impact map to trace the formal independent-coding
plane from Pi's distinct-model resolver through structured coder calls, completeness filtering,
reliability computation, reconciliation, and persisted code applications. Compared those mechanics
to the architecture contract and their targeted tests.
Result: the formal path does require three distinct model identities (endpoint replicas do not
count), invokes coders independently, requires every admitted coder to cover every evidence unit,
and computes Fleiss kappa plus Krippendorff alpha for three or more coders. However,
`_usable_coding_applications` accepts a real evidence-unit identifier without checking that the
model-returned quote is an exact span of that unit; persistence then stores the unverified quote as
`CodeApplication.source_text`. Three agreeing models could therefore launder the same fabricated
sentence into apparently perfectly reliable, source-grounded evidence. This violates the Research
Spine's pre-trust grounding gate and is a confirmed correctness defect, not a documentation gap.
Verified: direct implementation trace plus existing tests for distinct models, replica rejection,
coder failure, incomplete coverage, and fail-closed selection. No code, service, model, dependency,
or remote-host operation occurred during this audit checkpoint.
Next: add a focused failing test for an out-of-source quote, repair exact-span admission, correct any
test fixtures that currently fabricate quotes, and run the complete formal validity regression set.

### L-45 | 2026-08-25T16:50:05Z | S2-execute | gpt-5-codex | implementer | Exact-span grounding red-green
Did: Added a direct contract test proving that a valid evidence-unit ID paired with a fabricated
quote must be rejected, observed the pre-fix failure, then required every coding application's
non-empty quote to be an exact contiguous substring of the resolved unit's raw source text before
code admission. Corrected two positive-test stubs to return the exact source quotes they claim to
ground, and updated both the architecture contract and Findings Codebook living documentation.
Result: the red test failed because the invalid application was admitted; after the smallest service
boundary check it and the existing persistence/repair tests pass. Invalid quotes now become missing
unit coverage, so the existing bounded-repair and insufficient-coder gates fail closed instead of
computing reliability over fabricated evidence.
Verified: focused red `1 failed, 28 deselected`; focused green `3 passed, 26 deselected`; Compass
Forge impact/why receipts for both documentation paths. The four-file broader Research Spine pytest
command remains actively running at this checkpoint. A duplicate invocation was briefly attempted
while recovering the process handle; process inspection shows one active pytest process, and no
duplicate result will be counted as evidence. No service, model, dependency, or remote-host action.
Next: collect the tracked pytest result, regenerate/check feature artifacts, then trace the report
manager and API surfaces to prove that accepted coding evidence still cannot report without human
approval and Done-task state.

### L-46 | 2026-08-25T16:51:02Z | S2-execute | gpt-5-codex | reviewer | Grounding regression green; Done gate bypass found
Did: Collected the complete formal validity suite, regenerated living feature artifacts, checked the
diff, then traced task approval, explicit task-to-report creation, report-manager routing/filtering,
agent tool movement, and autonomous worker lifecycle paths.
Result: all 78 formal Research Spine/reliability scenarios pass with exact-span admission, and the
report manager correctly requires both `TaskStatus.DONE` and `review_state == "approved"` before
routing findings; task approval also blocks unresolved Research Spine evidence. A separate confirmed
bypass remains: `CustomAgentWorker._execute_task` directly sets an orphaned task to `DONE` when its
project lookup fails, without a human review event or approved review state. Report routing still
rejects that task, but the Kanban lifecycle falsely represents agent-authored terminal completion and
violates the human-only Done invariant.
Verified: `78 passed in 98.95s`; feature docs `0 seeded`, `224 artifacts`, `86 features`, pass;
`git diff --check` clean; exact eight-path bounded grounding/doc/test diff. No service/model/dependency
or remote-host action occurred.
Next: commit/push the grounding slice with SHA equality, then add a worker lifecycle red contract and
replace the orphan terminal mutation with a non-Done error state that remains visible for humans.

### L-47 | 2026-08-25T16:53:57Z | S2-execute | gpt-5-codex | implementer | Human-only Done worker repair
Did: Transported the exact-span grounding slice, mapped `custom_worker.py` with Compass Forge
impact/why/test-impact, added a focused orphan-task lifecycle contract, observed the illegal Done
transition, and changed the missing-project branch to In Review / needs revision with an explicit
human-facing failure reason. Updated and regenerated the Agent Detail living contract, then ran task,
report-manager, and scenario regressions plus a source tripwire across agent/skill code.
Result: local and remote `testing` first converged at grounding commit
`36a6577d40d5b70d37b78359f0d29f297433e24a`. The new red then failed with actual
`TaskStatus.DONE`; it is green after the repair. No agent or skill implementation now directly
assigns `task.status = TaskStatus.DONE`, and the report/task suites retain human approval and
Research Spine gates.
Verified: orphan red `1 failed, 27 deselected`; orphan green `1 passed, 27 deselected`; direct-Done
source tripwire zero; task/report/spine regressions `30 passed in 36.04s`; feature docs `0 seeded`,
`224 artifacts`, `86 features`, pass; diff check clean. The broader test emitted one existing
`aiosqlite` event-loop-closed thread warning in `test_agent_execute_task_defers_when_project_paused`;
the suite passed, but the warning is retained as test-harness debt rather than suppressed.
Next: execute the relevant security/post-change gates, push this bounded repair with SHA proof, then
continue authority auditing across tasks, loops, A2A, skills, donation, tool calls, and long horizon.

### L-48 | 2026-08-25T16:54:34Z | S2-execute | gpt-5-codex | reviewer | Security green; broad CF gate debt retained
Did: Ran the tracked security benchmark and Compass Forge's repository-wide after gate over the
human-only Done slice, preserving the full outcome instead of reducing it to command exit status.
Result: the security scorecard passes all 28 applicable controls at 100% with no warnings. Compass
Forge recorded gate baseline 9 and returned process exit zero but its embedded repository status is
`fail`: it reports broad pre-existing/branch-aggregate complexity, route/type drift, large-asset, and
three secret-flow heuristic findings in `config.py`, `env_persistence.py`, and a benchmark helper.
None of those three production/test source paths changed in this bounded worker slice; they remain
unresolved gate debt and must not be represented as a passing architecture gate. The added
`tests/test_agents.py` contract also pushes that already-large test module over the configured line
threshold, a real maintainability warning to address separately without weakening the regression.
Verified: security `28 pass / 0 fail`, score `100%`; Compass Forge after record `9`, embedded status
`fail`; exact worker slice currently spans six expected source/test/living-doc/generated-doc paths.
Next: commit/push only those six paths and compare local/remote SHAs, then continue the execution-plane
authority audit while carrying the CF gate debt as open rather than using exit code zero as success.

### L-49 | 2026-08-25T16:56:16Z | S2-execute | gpt-5-codex | auditor | Skill repair policy still trusts classical settings
Did: Committed and pushed the human-only Done repair, required exact local/remote equality, then ran a
new graph-backed authority context pack spanning tasks, loops, A2A, skills, schedules, autoresearch,
embeddings, compute donation, benchmarks, model selection, and route evidence. Compared the scanner's
known patterns with broader direct-provider/classical-setting usage and traced generated-skill calls.
Result: local and remote `testing` equal
`599f7958b3bb525551190d67d423cc2a8970e25e`. Skill execution itself dispatches through the
Pi-authoritative `agentic` facade, but its repair policy still branches on the retired global
`settings.llm_provider`: a classical value of `lmstudio` skips native JSON repair and can skip the
empty-findings model repair even when Pi Model Management selected a different endpoint/provider.
Existing tests explicitly encode this obsolete coupling. This is a behavioral authority leak: the
removed control plane can still change which calls occur and whether useful model repair is attempted.
Verified: exact SHA equality; Compass context pack selected fourteen high-value paths and disclosed
86 recoverable omissions; direct provider/classical usage inventory; focused skill-factory trace.
No service, model, dependency, or remote-host operation occurred.
Next: graph-map `skill_factory.py` and its tests, turn the two legacy-coupling tests into red
Pi-authority contracts, remove both settings branches, and run the complete skill-factory suites.

### L-50 | 2026-08-25T16:59:18Z | S2-execute | gpt-5-codex | implementer | Pi owns every generated-skill repair stage
Did: Replaced the two tests that endorsed LM Studio-specific repair skipping with Pi-authority
contracts, added a static execution-source tripwire, observed all three fail against the old policy,
then removed only the two `settings.llm_provider` branches from generated-skill execution.
Result: an obsolete classical setting can no longer suppress either native structured repair or the
empty-findings model-repair attempt. `skill.execute`, `skill.repair_native`, `skill.repair_plain`, and
`skill.repair_findings` now always remain inside the same Pi-managed dispatcher chain; deterministic
fallback still runs only after the applicable model repair returns no usable findings.
Verified: focused red `3 failed, 17 deselected`; focused green `3 passed, 17 deselected`; diff check
clean. No service, model, dependency, host installation, or remote-host action occurred.
Next: run both complete skill-factory suites, update the living Skills feature contract and generated
artifacts, then commit/push this bounded authority repair with exact local/remote SHA evidence.

### L-51 | 2026-08-25T17:00:22Z | S2-execute | gpt-5-codex | reviewer | Skill authority slice fully green
Did: Ran the complete general and Pi-production generated-skill suites, updated the Skills Catalog
living architecture contract with the Pi-owned five-stage fallback order, regenerated all feature
artifacts, and checked the resulting seven-path diff.
Result: all twenty generated-skill scenarios pass. The durable documentation now names the project-
scoped dispatcher purposes and states that retired classical provider settings cannot skip, reorder,
or select a route for any repair call. Generated site and manifest remain synchronized.
Verified: skill suites `20 passed in 0.23s`; feature docs `0 seeded`, `224 artifacts`, `86 features`,
pass; diff check clean; only the expected implementation, two tests, lifecycle, living doc, generated
HTML, and manifest are modified. No service, model, dependency, host, or remote-host operation.
Next: commit/push the seven intended paths, prove SHA equality, then inspect remaining classical model
identity use at embeddings and the independent-ensemble boundary before choosing the next red test.

### L-52 | 2026-08-25T17:00:52Z | S2-execute | gpt-5-codex | implementer | Skill authority transported cleanly
Did: Staged only the seven reviewed generated-skill authority paths, committed them, pushed `testing`,
and compared the local and remote-tracking object IDs after transport.
Result: local `testing` and `origin/testing` are exactly equal at
`b6bd7b1bef9d435c0ddb529e926900f033c8c193`; the worktree was clean immediately after push. This
checkpoint removes another concrete P9-04 bypass without claiming that the wider authority audit is
complete.
Verified: commit `b6bd7b1` (`fix: keep skill repair under Pi authority`); push succeeded; exact SHA
equality; zero uncommitted paths before this ledger append.
Next: trace effective embedding model identity from API metadata through `agentic.embed` and Pi
resolution, decide from contracts/tests whether classical settings retain unauthorized selection
power, and create a red test only if the seam is behaviorally wrong.

### L-53 | 2026-08-25T17:02:02Z | S2-execute | gpt-5-codex | auditor | Binding EmbeddingProfile architecture is absent
Did: Traced embedding identity from cache keys and dispatcher parameters through
`EmbeddingsGateway` and `PiModelManager.resolve_embed`, compared that implementation with the
accepted Pi migration target architecture and vector-space invariant, and searched the full tree for
an `EmbeddingProfile` model or `embedding_profile_id` implementation.
Result: Pi does own the final gateway and endpoint resolution, but the requested model and active
local endpoint are still selected from the retired global `settings.llm_provider` in embeddings,
gateway defaults, manager resolution, and safe-metadata APIs. Tests intentionally assert this old
coupling. More importantly, the binding migration contract's explicit, versioned `EmbeddingProfile`
(model, endpoint/transport identity, dimension, dtype, normalization, health/version) exists only in
planning documents—there is no runtime or persistence implementation. This is architecture debt,
not a safe one-line rename: silently changing the cache/model key could invalidate stored vectors.
Verified: end-to-end source trace; migration invariants I3/I5 and sections 5.2/5.5; full-tree profile
search returns documentation only. No production file changed and no service/model/host action.
Next: use Compass Forge to record a migration-safe profile authority decision, define compatibility
bootstrap and no-silent-reindex behavior, then create focused red tests before adding persistence or
changing any effective vector identity.

### L-54 | 2026-08-25T17:02:56Z | S1-plan | gpt-5-codex | architect | Embedding authority decision made durable
Did: Recorded Compass Forge decision 2, translating the migration contract into an executable safety
boundary before any schema or vector-identity edit.
Result: Pi Model Management must own one persisted/versioned profile; bootstrap captures the currently
effective legacy identity exactly once and only as provenance; classical provider or chat changes can
never mutate it afterward; public mutation stays unavailable until a bounded re-embed/index workflow
versions vectors and caches; missing/incompatible pinned endpoints fail closed. The profile includes
model, endpoint/transport, dimension, dtype, normalization, health, and version.
Verified: Compass Forge decision 2, `Pi owns a versioned immutable embedding profile`; clean local and
remote `testing` at `57bd1c2e7917366a769707d36e6fc0aa20c969a6` before this ledger append.
Next: map the database/vector/cache/startup/API dependency set with Compass Forge and code references,
then create red contracts for one-time bootstrap, provider-independent reads, exact endpoint pinning,
and safe metadata before implementing the additive schema.

### L-55 | 2026-08-25T17:04:01Z | S1-plan | gpt-5-codex | planner | Embedding debt split into resumable acceptance slices
Did: Expanded P9-04 with the full ordered EmbeddingProfile delivery sequence and its negative-test
matrix rather than leaving the newly confirmed architecture gap only in chronological ledger prose.
Result: a resuming agent now has explicit boundaries for additive persistence/bootstrap, exact Pi
endpoint pinning, all runtime/metadata consumers, vector-store/cache version binding, and the later
governed re-embed/activation workflow. The plan explicitly forbids changing current vector identity
or exposing profile mutation before migration/rollback is implemented and verified.
Verified: decision 2 mapped into P9-04 step 5; no code/schema/runtime action in this checkpoint.
Next: collect graph impact/why/test-impact receipts for the persistence, manager, gateway, cache,
vector-store, startup, and metadata surfaces; implement only slice (a)-(b) after red tests.

### L-56 | 2026-08-25T17:05:16Z | S2-execute | gpt-5-codex | test-author | Embedding profile authority contracts red
Did: Collected a standard Compass context pack plus impact/why receipts for Pi Model Management,
then added four focused contracts for idempotent legacy-identity bootstrap, persistence across an
in-process restart/provider change, exact endpoint pinning when two endpoints expose the same model,
and fail-closed removal of the pinned endpoint.
Result: the new suite is red at collection because the planned `embedding_profile` authority module
does not exist. That is the expected first failure and independently confirms the documentation-only
gap before schema/runtime implementation. The context pack was derived/incomplete (15 selected;
budget omissions disclosed), so direct dependency traces remain part of the evidence.
Verified: `1 collection error` with `ModuleNotFoundError: app.core.pi_runtime.embedding_profile`;
no live service/model/remote-host action.
Next: implement only the additive ORM model, registration/migration, cached bootstrap service, and
endpoint-pinned resolver; rerun these four tests before wiring gateway/cache/startup/API consumers.

### L-57 | 2026-08-25T17:07:26Z | S2-execute | gpt-5-codex | implementer | Additive profile bootstrap and endpoint pin green
Did: Added revision 031 and the registered `EmbeddingProfile` ORM model, implemented a frozen runtime
snapshot plus idempotent database bootstrap/reload, and extended `PiModelManager.resolve_embed` with
exact endpoint identity admission before model matching. Updated the fresh-Alembic head contract.
Result: version 1 captures the current effective model, local endpoint, and existing cache namespace
without reindexing; after persistence, changing `llm_provider` or its model settings cannot mutate the
profile. A removed pinned endpoint now fails typed even if another endpoint exposes the same model.
An intermediate red was a test-fixture constructor omission (three required endpoint fields), not a
product failure; correcting the fixture produced the intended green.
Verified: profile authority `4 passed`; fresh Alembic + create-all bootstrap `2 passed`; diff check
clean before this ledger update. No runtime consumer has been switched yet, so the broader classical
selection debt remains open and this is not P9-04 completion.
Next: write gateway and startup red contracts proving exact profile consumption, then replace
`llm_provider` model/endpoint selection in gateway, wrapper, provisioning, and metadata incrementally.

### L-58 | 2026-08-25T23:28:51Z | S2-execute | gpt-5-codex | test-author | Runtime enforcement slice resumed from durable checkpoint
Did: Reconciled the working tree against L-57 and confirmed that only the bounded, uncommitted
EmbeddingProfile persistence/resolver slice plus this lifecycle file is present. Reused the already
collected Compass Forge impact/why/test-impact receipts for the gateway and startup surfaces.
Result: no hidden branch drift or unrelated dirty files were introduced during the interruption.
Persistence and exact resolver pinning are green, but runtime enforcement is still deliberately
unclaimed: the gateway can still derive its default from classical settings and startup has not yet
bootstrapped the persisted profile before vector invariants run.
Verified: local `testing` tracks `origin/testing`; eight intended paths are dirty/untracked; L-57 is
the last prior durable execution checkpoint. No live service, model load, SSH, or host install action.
Next: add red gateway and startup contracts for exact profile model+endpoint consumption and startup
ordering, implement the smallest runtime wiring, rerun focused tests, and checkpoint the evidence.

### L-59 | 2026-08-25T23:31:30Z | S2-execute | gpt-5-codex | implementer | Persisted profile now governs gateway and startup
Did: Added four runtime contracts, observed all four fail against the pre-wiring behavior, then made
startup load the persisted Pi-owned profile immediately after database initialization and made the
embedding gateway derive model plus exact endpoint exclusively from that profile. Added safe profile
id/version outcome metadata and rejected any caller model override that disagrees with the profile.
Result: classical `llm_provider` no longer selects the gateway's model; two endpoints advertising the
same model cannot be confused; a removed endpoint or conflicting override fails closed; vector-space
checks cannot run before the persisted identity is loaded. This does not yet migrate the legacy
embedding wrapper, cache keys, vector metadata, provisioning, or settings/project/memory disclosures.
Verified: intentional red `4 passed, 4 failed` (classical default, non-pinned endpoint, accepted model
override, absent startup bootstrap); focused green profile plus fresh-Alembic suites `9 passed`.
No service/model/SSH/host action.
Next: graph-map and contract the legacy wrapper/cache/provisioning consumers, bind them to profile
model+cache namespace, then update metadata surfaces without changing version-1 vector identity.

### L-60 | 2026-08-25T23:35:12Z | S2-execute | gpt-5-codex | implementer | Wrapper, cache, and provisioning moved under Pi profile
Did: Used Compass Forge impact/why/test-impact on the shared embedding wrapper (high-confidence graph;
wide consumers including RAG, validation, memory, file processing, settings, and W8). Replaced its
classical provider-derived model with the active profile, keyed cache and learned dimensions by the
profile cache namespace, and removed the legacy-engine direct Ollama provisioning bypass. Every
selectable engine now provisions the exact profile model at its exact Pi endpoint. Added explicit
profile injection only as a deterministic test seam and updated obsolete W8 classical-authority tests.
Result: Istara/legacy-loop selection no longer changes embedding authority, cache identity, or model
provisioning. Version 1 deliberately keeps `cache_namespace == model_id`, preserving existing cache
keys and vector identity while establishing the versionable boundary. Remote gateway tests must now
declare the exact profile endpoint rather than accidentally passing through model-name matching.
Verified: the first W8 regression run exposed 5 obsolete assumptions (three unpinned remote fixtures,
classical fallback resolution, classical model-rule equality); after contract updates, profile + W8
suites are `55 passed`. No service/model/SSH/host action.
Next: map settings/projects/memory metadata routes, add safe profile metadata contracts, remove their
classical embedding disclosures, then bind persisted vector records/index health to profile version.

### L-61 | 2026-08-25T23:39:20Z | S2-execute | gpt-5-codex | implementer | Public embedding metadata follows Pi authority
Did: Collected Compass Forge impact/why maps for the settings, projects, and memory routes, then made
their embedding model disclosure read the active profile. Added one centralized safe metadata shape
(profile/version/model/endpoint/dimension/dtype/normalization/health only; no URL, token, or key) and
included it in memory health while preserving the existing `embedding_model` compatibility field.
Result: changing classical provider settings can no longer make settings, project responses, or
memory health claim a vector model different from the runtime profile. A cross-route contract proves
this negative case. One UX test initially failed because it still mutated classical settings; its
fixture now establishes the Pi profile identity explicitly.
Verified: profile/W8/W8-UX/settings/projects focused set `97 passed`; no service/model/SSH/host action.
Next: identify the concrete Lance/vector write schemas and health readers, add red version-binding and
mismatch contracts, then persist profile id/version/cache namespace alongside every vector family.

### L-62 | 2026-08-25T23:43:05Z | S2-execute | gpt-5-codex | implementer | Lance indexes bound fail-closed to profile version
Did: Used Compass Forge impact/why/test-impact on the RAG/Lance store and traced its broad ingestion,
retrieval, memory, validation, agentic, and research consumers. Added a per-project embedding-profile
manifest plus profile fields on new vector rows. Existing tables may lack additive columns and the
legacy compatibility writer intentionally strips them, so the manifest is the authoritative binding
for both old and new schemas rather than pretending row metadata alone covers legacy indexes.
Result: an existing unbound index may be adopted only by version 1 (the exact pre-migration identity);
reads and writes reject corrupt manifests, unbound later-version indexes, or any profile/model/cache/
dimension/dtype/normalization mismatch. A profile v2 cannot mix vectors into or query a v1 index;
governed re-index activation remains required to replace the binding. Endpoint is recorded for audit
but excluded from vector-space equality so a transport move with identical mathematical identity is
not falsely treated as re-embedding.
Verified: profile/RAG-resilience/memory/W8 focused set `74 passed`, including real temporary Lance
write, manifest inspection, then read and write rejection after simulated v2 activation. No live
service/model/SSH/host action.
Next: update vector health to verify/report the store binding, run the wider embedding/RAG regression
set, document the living feature contract, and checkpoint/commit this bounded P9-04 authority slice.

### L-63 | 2026-08-25T23:47:04Z | S2-execute | gpt-5-codex | verifier | P9-04 embedding authority slice ready for review
Did: Used Compass Forge impact/why on vector health, corrected its store root to the authoritative
`lance_db_path`, and made health surface profile-binding failures separately from dimensional drift.
Updated both Memory Health living documents to replace the now-false legacy/Ollama rollback story with
the persisted profile, exact endpoint, cache namespace, index manifest, and governed re-index contract;
regenerated the feature site and manifest. Ran the required security benchmark and expanded regression.
Result: P9-04 now has persistence, startup ordering, gateway/wrapper/provisioning authority, safe API
metadata, versioned cache identity, project-index binding, and health reporting. It intentionally does
not expose mutation/activation: profile v2 is unusable against v1 indexes until the still-future
governed re-embed/re-index transaction exists. This bounded slice is ready for diff review and commit.
Verified: feature docs seeded 0/generated 224/check passed for 86; security benchmark 28/28 controls,
100%, no blocked/partial/fail; Pi migration + focused authority/W8/RAG/memory/settings/projects/Alembic
regression `140 passed`. No live service/model/SSH/host action.
Next: review the full intended diff for secret leakage, migration reversibility, fail-open exceptions,
and test-only assumptions; fix findings, commit/push this checkpoint, then resume P9-05 ensemble rigor.

### L-64 | 2026-08-25T23:50:08Z | S3-review/S4-remediate | gpt-5-codex | reviewer | Bootstrap race and lint findings remediated
Did: Reviewed the schema/service/runtime/vector diff and ran whitespace plus focused Ruff checks. Found
that application workers racing on a fresh database could each observe no active profile and create
multiple authorities because `(profile_id, version)` uniqueness alone does not enforce one active row.
Added a SQLite partial unique index for the active row and made bootstrap losers roll back and reload
the elected winner. Mechanically fixed import/UTC style issues in new files and wrapped one long line.
Result: concurrent bootstrap is database-enforced rather than process-assumed; downgrade removes the
new index before the table. No secret-bearing fields enter public metadata or manifests. Remaining
whole-file Ruff findings in old `memory.py`/`main.py` are pre-existing style debt outside this slice;
the newly added and materially changed modules are clean.
Verified: `git diff --check` clean before remediation; targeted Ruff returns no findings; fresh
Alembic/profile/W8/W8-UX/RAG/memory/settings/projects regression `116 passed` after remediation.
Next: append the final commit receipt, commit all and only this reviewed slice, push local `testing` to
`origin/testing`, verify ref equality and clean tree, then begin P9-05 ensemble statistical rigor.

### L-65 | 2026-08-25T23:51:12Z | S5-ship | gpt-5-codex | integrator | P9-04 authority slice transported cleanly
Did: Staged the explicit 23-file reviewed set, committed `02e7b30d` (`feat: make Pi own embedding
vector identity`), and pushed `testing` to `origin/testing`.
Result: the complete embedding-authority slice is recoverable remotely as one bounded commit; no
ambient or unrelated path was staged. Local and remote branch tips are byte-identical and the working
tree was clean immediately after transport, before this mandatory ledger receipt was appended.
Verified: push `57bd1c2e..02e7b30d`; local `testing` and `origin/testing` both resolve to
`02e7b30d8b83a31aa4ec28597ea3d45a5e1af6f7`; post-push status had no file entries.
Next: commit/push this receipt, then audit P9-05 against the Research Spine's effective-coder identity,
three-model independence, Fleiss kappa/Krippendorff alpha, abstention, and reconciliation contracts.

### L-66 | 2026-08-25T23:52:00Z | S1-frame/S2-execute | gpt-5-codex | implementer | P9-05 statistical audit isolated concrete fail-open cases
Did: Confirmed the P9-04 receipt is committed and `testing` is clean/equal to `origin/testing`, then
used the prior Compass Forge impact/why/context maps to trace coder selection, route provenance,
application persistence, matrix construction, Fleiss kappa, companion alpha, and promotion handling.
The host clock currently reports several minutes before the already-written L-65 timestamp; this entry
uses the next monotonic ledger timestamp so resumptions do not misread causal order.
Result: Three actionable metric defects are now bounded. A missing coder/unit cell is silently converted
to the substantive `__none__` category; an explicit abstention has no distinct representation; and a
single-category matrix returns kappa 1.0 even though expected agreement is 1.0 and kappa is undefined.
All can permit misleading reliability output. Model-name deduplication correctly prevents endpoint
replicas of one checkpoint from fabricating independence, but effective provider-account, endpoint,
prompt/codebook, and decoding-profile provenance is not yet present in the reconstructable matrix.
Verified: read-only branch/ref status and direct inspection only; no service/model/SSH/host action.
Next: add red contracts for missing cells, explicit abstention, and single-category degeneracy; make all
undefined/incomplete cases route to reconciliation; then add safe effective-rater provenance without
allowing aliases or endpoint replicas of the same checkpoint to count as independent models.

### L-67 | 2026-08-25T23:54:00Z | S2-execute | gpt-5-codex | implementer | Missing, abstention, and undefined reliability semantics corrected
Did: Added executable contracts before implementation, then taught matrix construction to distinguish
an absent coder/unit cell from an explicit abstention. Added a complete-cross-product check before any
Fleiss/alpha computation and corrected the single-category `expected_agreement == 1` degeneracy to an
undefined score rather than synthetic kappa 1.0.
Result: Missing ratings persist in the reconstructable matrix and force `incomplete_rater_matrix` plus
reconciliation. Explicit abstentions persist as `__abstain__` and remain analyzable. Undefined Fleiss
kappa carries its mathematical reason and cannot pass the promotion threshold. The old implicit
`__none__` substitution is gone from the metric path.
Verified: red run failed all 3 new contracts for the intended old behaviors; green focused run is
`9 passed` across new cases plus prior three-model, item-level disagreement, low-consensus, duplicate-
model, and single-model contracts. No service/model/SSH/host action.
Next: define and persist safe effective-rater provenance (checkpoint/model, provider-account handle,
endpoint, fixed prompt/codebook, decoding profile), validate it per coder, and keep checkpoint/model
identity—not route replicas—as the independence count.

### L-68 | 2026-08-25T23:56:00Z | S2-execute/S3-review | gpt-5-codex | verifier | Statistical slice under wider regression
Did: Ran the Compass Forge before-gate and started the complete research-integrity metric plus research-
validity contract suites after the focused green run. Inspected the gate delta rather than treating its
aggregate status as change attribution.
Result: The gate remains globally failed on inherited repository findings, notably three existing
secret-flow heuristic findings and broad complexity/route/type drift. None points to the two changed
metric/test files as a new secret flow. The wider pytest run has emitted 34 passing tests so far and is
still active; no completion claim is made until its process exits.
Verified: Compass Forge before record 10, status fail with baseline findings preserved; active pytest
session 37089, current stream `..................................`. No service/model/SSH/host action.
Next: wait for the bounded suite to terminate, remediate any regression, attach the exact terminal
count, then checkpoint the statistical fix before beginning effective-rater provenance.

### L-69 | 2026-08-25T23:58:00Z | S3-review/S4-remediate | gpt-5-codex | verifier | Degenerate integration expectation corrected
Did: Let the full bounded suite terminate rather than inferring success from progress dots. It found
one integration fixture where all three models apply one identical category to every evidence unit.
Updated that stale assertion to preserve the applications/coders while requiring reconciliation and
null kappa, matching the corrected `expected_agreement == 1` semantics.
Result: The production orchestration already persists the gate result correctly; only the test had
encoded false statistical confidence. Six code applications and three coder rows remain durable, but
their item reliability/promotion states now honestly remain `needs_reconciliation` for this dataset.
Verified: wider first run `1 failed, 53 passed in 72.75s`; affected integration plus three new metric
contracts now `4 passed`. No service/model/SSH/host action.
Next: rerun the complete 54-test bounded suite, append the terminal receipt, review/diff the metric
slice, then commit/push it before changing effective-rater provenance.

### L-70 | 2026-08-26T00:00:00Z | S3-review | gpt-5-codex | verifier | Corrected 54-test regression rerun active
Did: Started a fresh complete bounded reliability regression after correcting the one mathematically
obsolete integration expectation; retained the live process identifier for resumability.
Result: The rerun has emitted the same first 34 passing tests and remains active without a failure.
This is intentionally a progress record, not a green-suite claim.
Verified: active pytest session 94735, current stream `..................................`.
No service/model/SSH/host action.
Next: wait for terminal exit, record exact count/duration, run diff/targeted lint review, and transport
the bounded metric fix only if all verification is green.

### L-71 | 2026-08-26T00:02:00Z | S3-review/S4-remediate | gpt-5-codex | verifier | Final empty-rating edge case and living contract synchronized
Did: The corrected complete suite reached `54 passed in 75.00s`. During diff review, identified that an
explicit application object with empty codes but no abstention marker still appeared structurally
present. Tightened completeness so both an absent cell and an empty unmarked cell are missing, while
`rating_status=abstained` remains a deliberate categorical rating. Updated the Ensemble Health and
Fleiss Kappa living documentation and regenerated the feature site/manifests.
Result: The metric boundary no longer has an implicit null category in any input shape. Documentation,
tests, and runtime now agree that missing/empty blocks computation, explicit abstention is retained,
and single-category kappa is undefined. A final complete regression is active after this last change.
Verified: prior complete rerun `54 passed`; post-refinement focused `4 passed`; Ruff clean for both
changed Python files; `git diff --check` clean; feature docs seeded 0/generated 224/check passed for 86;
active final pytest session 10927 currently has 34 passes. No service/model/SSH/host action.
Next: collect final terminal count, run Compass Forge after-gate, review exact staged paths, commit/push
the P9-05 statistical sub-slice and receipt, then resume effective-rater provenance.

### L-72 | 2026-08-26T00:04:00Z | S3-review/S4-remediate | gpt-5-codex | reviewer | Statistical sub-slice ready for clean transport
Did: Collected the final post-refinement regression, ran the after-gate, reviewed the exact runtime/docs/
test diff, and moved the three new pure metric contracts from the oversized integration module into the
dedicated integrity-metrics module. Kept the one integration assertion change where persistence must
reflect undefined kappa; splitting that existing 1,638-line file is separate structural debt.
Result: No new dependency, import-cycle, forbidden-path, secret-flow, or large-file delta was introduced.
Compass Forge still flags the touched integration test module's inherited over-1,200-line complexity;
the move reduced it from the gate-before 1,729 lines to 1,638 rather than worsening it. The dedicated
metric file is 406 lines. Global gate status remains failed on the documented baseline.
Verified: final complete bounded suite `54 passed in 73.15s`; moved metric tests `3 passed`; changed
runtime Ruff clean; `git diff --check` clean; feature docs check passed for 86; Compass Forge after
records 11/12 with no dependency/import/secret delta. No service/model/SSH/host action.
Next: stage exactly the 9 reviewed runtime/test/living-doc/generated/ledger files, commit and push to
`origin/testing`, verify clean ref equality, append/transport the receipt, then start effective-rater
provenance as the next P9-05 sub-slice.

### L-73 | 2026-08-26T00:06:00Z | S5-ship | gpt-5-codex | integrator | P9-05 statistical fail-closed slice transported
Did: Staged exactly the nine reviewed runtime, test, living-doc, generated-site, and lifecycle files;
committed `fb3bcac7` (`fix: fail closed on undefined reliability`) and pushed `testing`.
Result: Missing/empty ratings, explicit abstention, and undefined single-category Fleiss behavior are
now remotely recoverable as one bounded commit. No unrelated path was staged. Local and remote tips
are identical and the tree was clean before this mandatory receipt was appended.
Verified: push `39c4b863..fb3bcac7`; local and `origin/testing` both resolve to
`fb3bcac71c335bbb89ffcf4c11c0f8a635126159`; post-push status had no file entries.
Next: commit/push this receipt, then add red contracts and implementation for reconstructable effective-
rater provenance while preserving the rule that same-checkpoint aliases/replicas count as one model.

### L-74 | 2026-08-26T00:08:00Z | S1-frame/S2-execute | gpt-5-codex | implementer | Effective-rater provenance boundary under test
Did: Transported the L-73 receipt (`17918777`) and used Compass Forge impact/why on the endpoint
resolver before extending its widely consumed identity contract. Added a non-secret 16-hex provider-
account handle derived from Keychain service/account identity, without exposing either value. Began
recording per-coder model/checkpoint, account handle, endpoint, prompt digest, codebook, protected
protocol version, and decoding profile in the reconstructable reliability matrix, with within-run
identity changes failing closed.
Result: Endpoint/account provenance is now separable from scientific independence: route fields are
auditable, while the existing normalized model/checkpoint count still collapses same-model replicas.
Pi coding passes use a fixed temperature and protected protocol; the exact prompt is represented by a
digest, not persisted again. One endpoint unit assertion used an incorrectly precomputed digest and
is being corrected to the implementation's deterministic value; the provenance metric tests passed.
Verified: receipt pushed and tree clean before this slice; endpoint impact confidence high; changed
runtime Ruff clean; first focused run `1 failed, 4 passed`, solely expected account-handle fixture
`db24...` versus actual `77338d4237faa913`. No service/model/SSH/host action.
Next: rerun endpoint/provenance contracts, inspect service integration persistence, add a production-
path assertion that all three coder columns carry complete consistent provenance, then wider W7 tests.

### L-75 | 2026-08-26T00:10:00Z | S2-execute/S4-remediate | gpt-5-codex | implementer | Production provenance completeness now fail-closed
Did: Added an explicit production enforcement flag to the reliability gate; governed coding runs now
require non-empty checkpoint/model, safe provider-account handle, endpoint, prompt digest, protected
protocol version, and decoding profile for every coder. Pure statistical callers can still evaluate
synthetic matrices without route metadata, while the Research Spine service cannot. Added a W7
integration assertion over all three persisted coder columns and a negative missing-provenance test.
Result: Changing endpoint/account/prompt/codebook/protocol/decoding identity within a coder column or
omitting required production provenance routes to reconciliation. Same-model routes still collapse in
the independent-model count; complete route identity never manufactures model diversity.
Verified: endpoint/provenance focused set `5 passed`; negative provenance metric `1 passed`. The first
W7/contract rerun stopped at collection because a test-fixture method was accidentally over-indented;
the indentation is corrected, with no production file implicated. No service/model/SSH/host action.
Next: rerun the identical W7/contract selection, repair only evidence-backed failures, then inspect
serialization for raw source spans, normalized categories, missing/abstain, full matrix, and routes.

### L-76 | 2026-08-26T00:12:00Z | S2-execute/S3-review | gpt-5-codex | verifier | Effective-rater provenance under complete bounded regression
Did: Corrected the fixture indentation and obtained a green W7/service integration selection. Reviewed
the persisted CodingRun matrix and CodeApplication split: the matrix now carries normalized categories,
missing/abstain states, complete rater provenance and conflicts; source quote/span/location/grounding and
route evidence remain persisted on each CodeApplication/CodingRunCoder rather than duplicated into each
matrix cell. Updated and regenerated Ensemble Health living documentation. Ran the mandatory security
benchmark because the safe account handle derives from Keychain identity metadata.
Result: The audit artifact is reconstructable across the matrix plus source-grounded application rows,
without storing secret, URL, prompt text, or raw Keychain account/service values. The account handle is
a one-way truncated digest; endpoint telemetry exposes only this safe handle. Full bounded tests run now.
Verified: W7/contract selection `16 passed`; changed files Ruff/diff clean; feature docs seeded 0/
generated 224/check passed for 86; security benchmark 28/28, 100%, no blocked/partial/fail; active pytest
session 68475 has emitted 66 passes. No service/model/SSH/host action.
Next: collect terminal pytest count, inspect endpoint identity compatibility and secret leakage, run the
after-gate, then commit/push this effective-provenance sub-slice if review remains clean.

### L-77 | 2026-08-26T00:14:00Z | S3-review/S5-ship | gpt-5-codex | reviewer | Effective-rater provenance slice ready for transport
Did: Collected the complete bounded suite, reviewed every new secret/account/prompt-related diff line,
and ran two after-gates including a compact parsed delta. Confirmed raw Keychain service/account appear
only as in-process hash inputs; persisted/telemetry data contains only the 16-hex handle. Prompt content
is not duplicated into the matrix; only its SHA-256 digest is stored. Exact source spans and grounding
remain in CodeApplication rows linked by coder/unit/run IDs.
Result: Effective identity is now auditable without weakening model independence or leaking credentials.
The after-gate reports only inherited complexity thresholds on touched large files/functions; it reports
zero new forbidden dependencies, missing required paths, or import cycles, and no new secret-flow issue.
Splitting those large service/test files is recorded structural debt, not silently claimed resolved.
Verified: complete endpoint/W7/metrics/validity set `83 passed in 74.96s`; security benchmark 28/28,
100%; feature docs 86/86; changed-file Ruff and diff check clean; Compass Forge after records 13/14.
No live service/model/SSH/host action.
Next: stage exactly the 12 reviewed runtime/test/living-doc/generated/ledger paths, commit/push, verify
clean local/remote equality, transport the receipt, then continue P9-05 with independent prompt/cache
isolation and external Fleiss/alpha cross-check edge cases.

### L-78 | 2026-08-26T00:16:00Z | S5-ship | gpt-5-codex | integrator | Effective-rater identity transported cleanly
Did: Staged exactly the 12 reviewed endpoint/model-manager/reliability/service/test/living-doc/generated/
ledger files; committed `7a0b1953` (`feat: persist effective ensemble rater identity`) and pushed.
Result: The Research Spine now has a remotely recoverable, bounded effective-rater provenance contract.
No unrelated path was staged. Local/remote tips are byte-identical and the tree was clean immediately
after transport, before this mandatory receipt was appended.
Verified: push `17918777..7a0b1953`; local and `origin/testing` both resolve to
`7a0b195391c05285f987d11487be4eee6bbdab83`; post-push status had no file entries.
Next: commit/push this receipt, audit whether independent coder calls share conversation/cache state,
then add deterministic statistical cross-checks for perfect/chance/disagreement/missing/single-category/
category-order cases before declaring P9-05 complete.

### L-79 | 2026-08-26T00:18:00Z | S2-execute/S3-review | gpt-5-codex | verifier | Coder session isolation and independent kappa cross-check proven
Did: Traced dispatcher `structured` into Pi `run_structured` and `_drive_turn`: each coder passes no
session key, so the engine creates a fresh UUID-backed session; prompt history is rebuilt from the fixed
protected messages and never includes another coder's output. Persisted explicit conversation/cache
scope in each rater identity. Added an independent count-formula Fleiss fixture with expected kappa
0.333 and proved multi-code category-order invariance.
Result: Provider prompt-prefix computation may be cached, but response/conversation state is never
replayed as another coder judgment. Missing isolation metadata fails the production provenance gate.
The source-diversity wording is applied to representative corpus/benchmark selection, not as a demand
for three distinct source documents per run: such a gate would wrongly forbid valid multi-unit coding
of one interview. Runtime requires all three models to cover every selected raw-source evidence unit;
benchmark work must separately prove source-diverse selection.
Verified: isolation/provenance and independent-formula tests `2 passed`; W7 persisted three-coder
isolation identity `1 passed`; changed-file Ruff/diff clean. No service/model/SSH/host action.
Next: regenerate living docs and rerun the complete endpoint/W7/metrics/validity boundary, then review,
gate, commit/push this final P9-05 isolation/statistical slice and advance to P9-06 full-spine paths.

### L-80 | 2026-08-26T00:20:00Z | S3-review | gpt-5-codex | verifier | Final P9-05 bounded regression active
Did: Regenerated the feature documentation after adding the explicit fresh-session/provider-prefix-cache
contract and started the complete endpoint/W7/metrics/research-validity regression.
Result: Documentation and generated site agree; the test run has emitted 67 passes and remains active.
This is a progress checkpoint rather than a terminal green claim.
Verified: feature docs seeded 0/generated 224/check passed for 86; active pytest session 84772 current
stream `...................................................................`. No service/model/SSH/host action.
Next: collect the terminal count, remediate any failure, run compact after-gate/diff review, and transport
only after the process exits green.

### L-81 | 2026-08-26T00:22:00Z | S3-review/S5-ship | gpt-5-codex | reviewer | P9-05 final isolation/statistical slice ready
Did: Collected the terminal regression, ran changed-file Ruff/diff checks, and parsed the Compass Forge
after-gate delta. Reviewed the eight-file diff: two small runtime metadata additions, two focused tests,
living/generated docs, manifest, and lifecycle only.
Result: P9-05 now covers distinct model/checkpoint independence; exact account/endpoint/prompt/codebook/
protocol/decoding provenance; complete matrices; explicit abstention; missing/empty failure; undefined
single-category handling; Fleiss plus alpha companion; independent count-formula/category-order check;
fresh conversation sessions; and reconciliation instead of threshold promotion for invalid/low/undefined
states. Remaining gate items are the already recorded touched-file complexity debt.
Verified: complete bounded suite `84 passed in 67.08s`; feature docs 86/86; changed-file Ruff/diff clean;
Compass Forge after record 15 has no new forbidden dependency, missing path, or import cycle. No live
service/model/SSH/host action.
Next: commit/push the exact eight-file slice and receipt, verify clean ref equality, mark P9-05 complete
in the execution matrix, then start P9-06 full Research Spine path coverage and bypass remediation.

### L-82 | 2026-08-26T00:24:00Z | S5-ship/S1-frame | gpt-5-codex | integrator | P9-05 transported; P9-06 activated
Did: Committed `2abe6453` (`test: prove ensemble coder isolation`), pushed it, verified exact local/
remote equality and clean status, then marked P9-04/P9-05 complete and P9-06 in progress in the durable
task graph.
Result: Ensemble reliability work is recoverable remotely and no longer conflated with the remaining
full-spine proof. P9-06 now owns positive source-to-report lineage, reconciliation/human approval, and
the negative bypass/leakage cases listed above.
Verified: push `50ee7eae..2abe6453`; local and `origin/testing` both resolve to
`2abe64536d82edcbdf9daa34de1c05ba99d13aa7`; post-push status had no file entries.
Next: transport this receipt/status change, inventory every source-to-artifact/report path from existing
Research Spine tests and routes, identify bypasses and pagination/corpus gaps, then add the first red
P9-06 end-to-end contract without starting a live service or loading a model.

### L-83 | 2026-08-26T00:26:00Z | S1-frame/S2-execute | gpt-5-codex | auditor | P9-06 inventory boundary recorded
Did: Re-established repository truth before resuming: local `testing` and `origin/testing` are exactly
equal at `af42944c`, with no dirty paths. Reviewed the prior Compass Forge P9-06 context/suggest-tests
result and retained its explicit coverage limit: 16 paths selected and 84 omitted by the 80 KB budget.
Result: The context pack is a starting map, not proof of complete Research Spine coverage. P9-06 remains
in progress; no code or service state has been changed. The next audit will explicitly include omitted
pagination, task/Done, route, model, report-manager, synthetic-boundary, integrity-validation, and real-
user benchmark probe paths rather than inferring completeness from the pack.
Verified: `git status --short --branch` reports `testing...origin/testing`; both refs resolve to
`af42944c72762622e3abe18641af0947d171abd9`. No live service/model/SSH/host action.
Next: map positive and negative gate assertions across the selected and high-priority omitted tests,
then use Compass Forge impact/why on the first actual gap before writing a red test.

### L-84 | 2026-08-26T00:28:00Z | S2-execute | gpt-5-codex | tester | Stale coding-run acceptance bypass reproduced red
Did: Mapped the task/report gate and found that `assess_task_research_validity` counts accepted code
applications across all historical runs, while its latest-run rejection executes only when the total
accepted count is zero. Added a focused regression with an older accepted run/application followed by
a newer blocked run caused by unavailable current routing.
Result: The new test fails exactly at the policy boundary: `report_allowed` is incorrectly `true`.
Thus a failed current re-code can inherit stale acceptance and leak old assurance into report routing.
This is a production Research Spine bypass, not merely missing test coverage.
Verified: targeted test `1 failed`; observed `assert True is False`. Compass Forge impact/why was run
for the service and contract test before editing; it identifies the service as a high-risk shared
Research Spine/report/API surface. No live service/model/SSH/host action.
Next: make the latest task coding run authoritative whenever task code applications exist, rerun the
red test and adjacent task/report/reconciliation contracts, then update living feature documentation.

### L-85 | 2026-08-26T00:30:00Z | S2-execute/S3-review | gpt-5-codex | implementer | Current-run authority fixed and documented
Did: Moved the latest-run acceptance check ahead of historical item-support evaluation whenever a task
has code applications. Updated the Reports living architecture to state that a newer blocked,
incomplete, or unaccepted run invalidates assurance inherited from older runs/applications, then
regenerated all feature-site artifacts.
Result: The stale-acceptance regression is green, as are adjacent unreconciled, reconciliation, Done-
task, and ReportManager contracts. The change is deliberately narrow: accepted/reconciled current runs
continue to use item-level lineage; a current failed run now fails closed before old accepted rows can
make reporting appear safe.
Verified: targeted/adjacent set `5 passed in 2.92s`; feature docs seeded 0/generated 224/check passed
for 86; changed Python Ruff and `git diff --check` pass. No live service/model/SSH/host action.
Next: run the full task/report/research-validity contract boundary, review for ordering/regression risk,
then continue P9-06 with deleted-source and continuous positive-journey proof rather than stopping at
this first bypass.

### L-86 | 2026-08-26T00:32:00Z | S3-review | gpt-5-codex | verifier | Stale-run remediation passes full report boundary
Did: Ran the complete Research Spine contract, integrity ReportManager, task, finding, and evidence-unit
pagination test boundary after the current-run authority change.
Result: All 93 tests pass. This covers reconciliation, item-level lineage, cross-project finding links,
human-approved Done transitions, report filtering and synthesis revalidation, plus bounded evidence-unit
listing. P9-06 remains open because this is broad component coverage, not yet a single causal positive
journey or explicit source-deletion/revocation invalidation proof.
Verified: `93 passed in 72.40s`; no live service/model/SSH/host action.
Next: inspect source-document deletion semantics and referential validity at the report gate; add a red
test if accepted evidence survives source removal, then build the continuous positive journey fixture.

### L-87 | 2026-08-26T00:34:00Z | S2-execute | gpt-5-codex | tester | Deleted-source reportability bypass reproduced red
Did: Traced document deletion and evidence persistence. Documents are hard-deleted, while evidence
units and accepted code applications intentionally retain audit rows without a foreign-key lifecycle
link. Added a regression that first proves a source-backed accepted code is reportable, deletes the raw
source document, then reassesses the same task.
Result: Reassessment incorrectly remains reportable. Stored source text is therefore being treated as
self-authenticating after its governed raw source has disappeared. This violates the requested revoked-
source negative gate and the Research Spine's source-grounding contract.
Verified: targeted test `1 failed`; pre-delete gate is true as expected and post-delete gate wrongly
returns true. No live service/model/SSH/host action.
Next: validate accepted evidence units against current same-project source documents and their versions
at report assessment time, preserve orphan rows for audit, and fail closed on deleted or superseded
sources before rerunning the boundary.

### L-88 | 2026-08-26T00:36:00Z | S2-execute/S3-review | gpt-5-codex | implementer | Source lifecycle gate added without erasing audit rows
Did: Added report-time validation for accepted document-backed code applications. The gate resolves
their source document in the same project and compares the evidence unit's recorded document version
to the current source version. Missing documents, malformed version provenance, or version drift are
blocked; historical evidence/code rows remain intact for audit rather than being cascade-deleted.
Result: Deleted-source acceptance now fails closed. The regression was extended to cover superseded
source versions as well, so edited source text cannot silently retain an earlier coding decision.
Documentless non-document evidence remains on its existing governed path instead of being incorrectly
rejected merely because it has no Document row.
Verified: deleted/current-run targeted set `2 passed`; changed Python Ruff and diff check pass. No live
service/model/SSH/host action.
Next: rerun the extended changed/superseded/deleted regression and the full 93-test report boundary,
update the Reports living contract, then implement the continuous positive journey proof.

### L-89 | 2026-08-26T00:38:00Z | S3-review | gpt-5-codex | verifier | Source lifecycle remediation passes full boundary
Did: Extended the regression through current source -> superseded source version -> restored version ->
deleted source and ran the complete Research Spine/report/task/finding/pagination boundary.
Result: All 94 tests pass. The gate distinguishes historical retention from current report authority:
audit rows survive, but only the active same-project document version can ground new report promotion.
The Reports living architecture now states both latest-run authority and exact-source-version authority.
Verified: `94 passed in 72.12s`; no live service/model/SSH/host action.
Next: regenerate the feature site, then add one continuous positive journey that proves raw source,
three independent coders, reliability/grounding, explicit human code acceptance, Atomic lineage, human
Done approval, ReportManager routing, and traceability in one causally linked fixture.

### L-90 | 2026-08-26T00:40:00Z | S3-review/S5-ship | gpt-5-codex | reviewer | P9-06 bypass slice ready for transport
Did: Regenerated and checked the feature site, reviewed the complete runtime/test/living-doc diff, and
ran Compass Forge after-gate record 16. The first attempted gate invocation used an unsupported native
`--request` flag and made no record; rerunning the pinned native command with its supported argument
shape completed normally.
Result: No new forbidden dependency, required-path, import-cycle, security, or taint finding exists.
The global gate remains failed on inherited secret-flow/route/type/large-file debt and reports touched-
file complexity: the already oversized research-validity service/test grew further. That structural
debt is explicit; the two production bypasses are nevertheless bounded by 94 green behavioral tests.
Verified: feature docs 86/86; full boundary 94/94; Ruff/diff clean; Compass Forge after record 16.
No live service/model/SSH/host action.
Next: commit/push exactly the six runtime/test/living/generated/lifecycle paths, verify clean ref
equality, transport the receipt, then resume P9-06 continuous positive-journey proof.

### L-91 | 2026-08-26T00:42:00Z | S5-ship/S2-execute | gpt-5-codex | integrator | Stale-assurance bypasses transported cleanly
Did: Staged exactly the six reviewed service/test/Reports living-doc/generated/ledger paths, committed
`b238d191` (`fix: invalidate stale research evidence`), pushed `testing`, and verified ref equality and
a clean tree before appending this receipt.
Result: The newer-blocked-run and changed/deleted-source fail-closed gates are remotely recoverable.
No unrelated file was staged. P9-06 remains in progress and now moves to the continuous positive path.
Verified: push `af42944c..b238d191`; local and `origin/testing` both resolve to
`b238d19157c7a0de52bff1d5470b33c59a783a3a`; post-push status had no file entries.
Next: push this receipt, then construct the end-to-end positive fixture from real service boundaries
without live model loading by using deterministic three-coder stubs and persisted route provenance.

### L-92 | 2026-08-26T00:44:00Z | S2-execute | gpt-5-codex | test-author | Continuous positive Research Spine proof assembled
Did: Created a new focused end-to-end contract rather than further enlarging the existing 1,788-line
contract file. It starts with a current raw Document and two exact EvidenceUnits; executes three
distinct deterministic model coders through the real structured coding service; requires numeric
Fleiss kappa and Krippendorff alpha; persists six grounded applications and three coder identities;
records explicit human code acceptance; builds Nugget -> Fact -> Insight -> Recommendation lineage;
uses the real human task-approval helper; routes through ReportManager; and queries graph traceability.
Result: The first run reached the human-decision assertion, proving all prior stages executed, but the
test expected a nested `decision` key while the actual durable API returns the decision fields at the
top level with only `code_application` nested. Corrected the assertion to the real contract. This was a
test-shape mismatch, not a production bypass or model call failure.
Verified: first targeted run `1 failed` at `KeyError: decision` after accepted 3-model reliability.
Compass Forge impact/why was run for ReportManager and task approval before assembly. No live model,
service, SSH, Docker, or host action.
Next: rerun the continuous journey, remediate the first genuine boundary failure if any, then add its
negative companion proving the report is absent before human Done approval.

### L-93 | 2026-08-26T00:46:00Z | S2-execute/S3-review | gpt-5-codex | verifier | Continuous positive journey green; transaction boundary made faithful
Did: Reran the corrected journey. Its first attempt hung after task approval because the test called
ReportManager while the review write was still uncommitted; ReportManager's content-free telemetry uses
a second SQLite session, faithfully exposing the documented transaction boundary. Terminated only the
owned pytest process, then made the fixture mirror the public route: commit and refresh immediately
after `_approve_task` before side effects/report routing. Added the negative companion inside the same
causal fixture: ReportManager must return zero and persist no report while the task is still In Review.
Result: The complete journey now passes in 1.59s with no live model. It proves three distinct model
calls over every exact source unit, numeric Fleiss/alpha reliability, persisted route/coder/application
identity, explicit human code acceptance, accepted Atomic lineage, human-approved Done, report routing,
and unblocked graph traceability; it also proves that the same accepted evidence cannot report before
human Done approval.
Verified: targeted end-to-end contract `1 passed in 1.59s`. No live model/service/SSH/Docker/host action.
Next: rerun after the new pre-Done assertion, lint/diff check, include this proof in the full P9-06
boundary, then audit remaining negative gaps before marking P9-06 complete.

### L-94 | 2026-08-26T00:49:00Z | S3-review | gpt-5-codex | verifier | Continuous journey included in full P9-06 boundary
Did: Re-ran the focused positive/negative Research Spine journey together with the stale-run,
source-lifecycle, report-integrity, task, finding, and pagination contracts.
Result: The full P9-06 boundary is green at 95 tests. The journey proves the causal positive path from
current raw source and exact evidence units through three distinct coder calls, numeric Fleiss kappa
and Krippendorff alpha, persisted route/coder/application provenance, explicit human code acceptance,
Atomic lineage, human-approved Done, ReportManager routing, and graph traceability; its negative half
proves no report exists before Done approval. The run emitted one existing task-suite warning that
`AsyncSession.close` was not awaited in `backend/app/api/websocket.py`; this is not treated as a green
proof and remains an explicit audit candidate.
Verified: `95 passed, 1 warning in 73.07s`; no live model/service/SSH/Docker/host action.
Next: lint/diff-check the slice, inspect the warning and remaining P9 negative contracts, then transport
the focused proof and ledger receipt before advancing to calls/long-horizon and Petals integration.

### L-95 | 2026-08-26T00:52:00Z | S3-review | gpt-5-codex | verifier | Focused proof is linted, documented, and gate-recorded
Did: Ran the changed-file Ruff check, diff check, feature-doc generation/check, and the pinned native
Compass Forge after gate for the new journey and its living Reports contract. The first broad Ruff
invocation also surfaced 11 unused/redefinition findings already present in
`tests/test_research_integrity_reports.py`; the focused changed-file check is clean, while those
pre-existing findings remain an explicit cleanup item.
Result: Feature documentation remains consistent (86/86), generated site artifacts are synchronized,
and the native gate recorded record 17. No new forbidden dependency, required-path, import-cycle,
security, or taint finding was introduced. The global gate is still failed by inherited secret-flow,
route/type drift, and complexity debt, including the touched research-validity service and the existing
large reports-contract test; this is not represented as a green repository gate.
Verified: feature docs `generated 224`, `check passed for 86`; focused Ruff and diff check pass; native
Compass Forge after record 17 completed; no live model/service/SSH/Docker/host action.
Next: commit and push exactly the focused test, Reports living contract, generated manifest, and ledger;
then audit and close remaining negative Research Spine, calls/long-horizon, Petals, and benchmark gaps.

### L-96 | 2026-08-26T00:55:00Z | S5-ship | gpt-5-codex | integrator | Continuous Research Spine proof transported cleanly
Did: Committed the focused end-to-end contract, Reports living documentation and generated site manifest,
and the preceding ledger receipts as `5a6ea9d9` (`test: prove research spine report gate`); pushed the
same commit to `origin/testing`.
Result: The positive/negative report-gate proof is now recoverable from the remote testing branch with
no uncommitted local changes. This commit does not claim Mac Studio acceptance or live-model coverage;
those remain pending Docker-only verification and the separate calls/long-horizon/Petals audit.
Verified: push `1335f449..5a6ea9d9`; local `HEAD` and `origin/testing` both resolve to
`5a6ea9d9ed4635c6ec625a0a520a00c62bb066e2`; post-push worktree clean.
Next: inspect current test topology and Compass Forge decisions for the remaining P9-06 through P9-15
items, then add only evidence-bearing contracts or fixes that close identified gaps.

### L-97 | 2026-08-26T01:02:00Z | S2-execute/S3-review | gpt-5-codex | test-author | Source breadth and Pi coding path made testable
Did: Corrected the focused Python journey to use three separate current Document rows and three
source-grounded EvidenceUnits, and routed its real coding call path through `_use_pi_coding_plane`,
`_select_pi_coders`, and `_pi_coder_runner` with deterministic dispatcher responses. It now proves
the PI Model Management coding boundary rather than a legacy router shortcut while keeping model
responses deterministic and no live model load. In the real-user benchmark, normalized source identity
no longer falls back to a unit id; missing metadata is grouped as unknown, and a configured three-source
requirement blocks before any coding request when breadth is not proven.
Result: The benchmark can no longer describe several units from one document (or unit-only metadata)
as three-source research. A new negative contract asserts no coding POST occurs with only two source
identities. The topology contract records the three-source requirement.
Verified: focused Python journey `1 passed in 1.65s`; Node probe/topology tests `21 passed`; focused
Ruff/diff checks pass; feature docs `86/86` and generated site `224`; no live model/service/SSH/Docker/
host action.
Next: run the changed benchmark and Python boundary once more after staging review, then transport this
oracle/Pi-path slice before auditing calls, long horizon, Petals, and live Docker acceptance.

### L-98 | 2026-08-26T01:05:00Z | S5-ship/S1-frame | gpt-5-codex | integrator | Source-breadth oracle transported; P9-06 remains open
Did: Committed and pushed the Pi-path Research Spine journey, three-source fixture, source-identity
normalization, fail-closed breadth oracle, topology contract, living Reports documentation, generated
manifest, and ledger as `d5659da4` (`test: enforce research source breadth`).
Result: `testing` is clean and remotely aligned. P9-06 is stronger but intentionally not complete:
the focused contract proves one accepted lineage, while the broader negative matrix still needs explicit
rejected-code, missing-route, cross-project, revoked-route, and immutable-audit assertions where gaps
remain. P9-07 through P9-15 are untouched by this transport.
Verified: push `79d75f00..d5659da4`; the next post-receipt commit must verify local/remote equality and
clean status before any additional change.
Next: audit the real tool-call and long-horizon implementations against the P9-07 contract, beginning
with whether existing tests exercise persisted assistant output and consumed tool results rather than
only synthetic parser/DAG calculations.

### L-99 | 2026-08-26T01:14:00Z | S2-execute/S3-review | gpt-5-codex | test-author | Two-call restart and long-horizon worker proofs added
Did: Added a real authenticated ASGI continuity contract that creates one persisted `ChatSession`, runs
the first Pi request, shuts down its worker, then runs the second request against a fresh worker. A
recording supervisor asserts the second `session.open` receives the exact first user/assistant transcript
from the database, and the DB assertion requires the four-message user/assistant sequence. Added a
production-worker long-horizon contract with seven canonical `create_task` calls followed by a final
assistant response; it requires seven authority executions, seven persisted tasks, one terminal
`run.completed`, and cumulative `usage.turns == 8`, exceeding the historical six-turn boundary.
Result: The focused production slice is green (`7 passed`), changed-file Ruff and diff checks pass, and
living Reports documentation plus generated site artifacts now name these proofs and their bounded
scope. This closes evidence for two-call DB rehydration and >6-turn tool-loop continuity, but it does
not yet prove live-provider checkpoint/restart, idempotency after crashes, or recovery from timeout,
cancel, malformed output, unavailable tools, or donor revocation.
Verified: `pytest -q tests/pi_production/test_worker_tool_loop.py tests/pi_production/test_chat_pi_asgi.py`
=> `7 passed in 4.37s`; focused Ruff clean; `git diff --check` clean; feature docs `generated 224`,
`check passed for 86`.
Next: audit the long-horizon runner's exit-code and oracle behavior, then cover checkpoint/cancel/
retry/idempotency and Petals donation/revocation lifecycle before remote Docker acceptance.

### L-100 | 2026-08-26T01:20:00Z | S5-ship/S1-frame | gpt-5-codex | integrator | Worker continuity slice transported and gate-recorded
Did: Committed the two-call authenticated ASGI restart proof, the seven-tool-call production-worker
long-horizon proof, living Reports documentation, generated feature artifacts, and this ledger as
`463c8316` (`test: prove Pi session continuity and long horizon`); pushed it to `origin/testing`.
Ran the pinned native Compass Forge after gate as record 19. The comparison reports no new forbidden
dependencies, missing required paths, import cycles, security findings, taint findings, or unexpected
large-file deltas. The repository-wide gate remains failed only on inherited secret-flow, route/type
drift, and complexity debt; that inherited failure is retained rather than relabeled as green.
Result: local `testing` and `origin/testing` both resolve to `463c8316785c032bde40e64f54249458b6a8fab1`,
and the worktree is clean. The focused worker/ASGI slice remains `7 passed`; this transport still does
not claim live-provider, checkpoint/retry/idempotency, Petals lifecycle, or Mac Studio acceptance.
Verified: push `a5aa227b..463c8316`; native Compass Forge after `record_id: 19`; no live model/service/
SSH/Docker/host action. Next: make the Docker-safe long-horizon runner fail closed on transport and
semantic-oracle failures, with a real second-call/session persistence assertion where the API permits.

### L-101 | 2026-08-26T01:32:00Z | S2-execute/S3-review | gpt-5-codex | test-author | Long-horizon live runner made fail-closed and session-aware
Did: Hardened tests/benchmarks/long_horizon_runner.py with operation-labelled status/JSON
validation, explicit server-side ChatSession creation, per-upload checks, canonical SSE parsing,
terminal done.message_id and provider-error requirements, exact tool-call-frame counting, a
mandatory first-turn tool-call assertion, a second turn over the same session, and a database-backed
history check requiring user/assistant/user/assistant continuity. Unexpected failures now return a
non-zero process status instead of printing a false-success report. Added regression tests for
canonical tool-call counting, complete/missing assistant history, terminal SSE requirements, and
main-process failure propagation.
Result: The benchmark no longer treats an HTTP/SSE/provider failure, missing persistence, or a
textual tool marker as successful long-horizon evidence. The live runner still reports task/A2A/
model-intelligence observations but does not pretend those metrics prove Research Spine acceptance.
Verified: pytest -q tests/pi_benchmark/test_b0_3_long_horizon_tokens.py tests/test_harness_config.py
=> 26 passed; Ruff and diff checks pass; feature docs generated 224 and checked 86/86. No live
model/service/SSH/Docker/host action in this slice.
Next: audit checkpoint, cancellation, retry, idempotency, and side-effect recovery contracts in the
Pi worker/provider seams; then inspect Petals donation/revocation lifecycle before Mac Studio Docker
acceptance.

### L-102 | 2026-08-26T01:45:00Z | S3-review/S5-ship | gpt-5-codex | test-author | Long-horizon runner complexity debt remediated before transport
Did: Extracted project/session setup, document uploads, chat-turn streaming, and event printing from
`tests/benchmarks/long_horizon_runner.py` after Compass Forge record 20 flagged `_run_benchmark`
complexity 25. Re-ran the focused benchmark/configuration tests, Ruff, diff checks, and the pinned
native Compass Forge pre-gate (record 21).
Result: `comparison.new_issues` is empty; no new missing paths, import cycles, security/taint findings,
or unexpected large-file deltas were introduced, and the helper extraction removes the new complexity
warning. The repository-wide gate remains failed only on inherited secret-flow, route/type, and
complexity debt; this is not claimed as a global green gate.
Verified: `pytest -q tests/pi_benchmark/test_b0_3_long_horizon_tokens.py tests/test_harness_config.py`
=> `26 passed`; Ruff and `git diff --check` pass. No live model/service/SSH/Docker/host action.
Next: commit and push this refactor, run the post-gate, then audit checkpoint/cancel/retry/idempotency
and side-effect recovery followed by Petals donation/revocation lifecycle.

### L-103 | 2026-08-26T01:58:00Z | S2-execute/S3-review | gpt-5-codex | test-author | Provider retry now fail-closes synchronous and non-transient throws
Did: Audited `pi-runtime/src/provider.mjs` and found two concrete gaps: synchronous adapter construction
throws escaped before the event stream was returned (leaving a run without a terminal frame), and
iteration-time thrown errors were retried without the same transient classifier used for error events.
Moved provider construction into the guarded section, applied `isRetryableAssistantError` to thrown
errors, and converted unretryable throws into one typed `error` event/terminal assistant message.
Added direct regressions for bounded transient retry and single-attempt non-retryable settlement in
`pi-runtime/test/hardening.test.mjs`; updated the Reports feature contract and generated site artifacts.
Result: Pi runtime suite is green (`46 passed`), feature docs generated `224` and checked `86/86`, and
`git diff --check` is clean. This protects Research Spine runs from retrying configuration/programming
failures or hanging without a terminal state; it does not yet provide durable tool-side-effect
idempotency across process crashes.
Verified: pinned native Compass Forge after gate record 22 has `comparison.new_issues=[]` with no new
missing paths/import cycles/security/taint/large-file findings; repository-wide inherited secret-flow,
route/type, and complexity debt remains explicitly failed. No live model/service/SSH/Docker/host action.
Next: commit/push this provider hardening, then add or document durable idempotency/recovery semantics
for authority side effects before Petals lifecycle and Mac Studio Docker acceptance.

### L-104 | 2026-08-26T02:06:00Z | S5-ship | gpt-5-codex | integrator | Provider hardening transported and post-gate boundary corrected
Did: Transported provider retry hardening as `a054a0f0` (`fix: fail closed on provider transport throws`) to
the local `testing` branch and `origin/testing`. Re-ran the pinned native Compass Forge after gate after
the commit (record 23), so the authoritative post-commit evidence is record 23 rather than the pre-commit
record 22 referenced in L-103.
Result: local and remote testing resolve to the same commit and the worktree is clean. Record 23 reports
`comparison.new_issues=[]`; no new missing paths, import cycles, security/taint findings, or large-file
regressions were introduced. Inherited repository-wide secret-flow, route/type, and complexity debt remains
failed and is retained as inherited debt. The durable idempotency gap is still open and is the next scope.
Verified: `git status --short --branch`; commit/push; native Compass Forge after record 23; `npm test` in
`pi-runtime` => 46 passed. No live model/service/SSH/Docker/host action.
Next: inspect the authority side-effect seam and implement a conservative durable replay/recovery contract
that cannot silently execute a duplicate mutation after a worker crash.

### L-105 | 2026-08-26T10:51:49Z | S2-execute/S3-review | gpt-5-codex | implementer | Durable Pi mutation replay and A2A identity propagated
Did: Added the project-scoped `pi_tool_executions` model and Alembic migration `032_pi_tool_executions`,
registered it in model/bootstrap loading, and implemented `execute_with_idempotency` at the Pi authority
boundary. Completed outcomes replay for the same request/tool/argument identity; cancellation, worker loss,
concurrent ownership ambiguity, malformed outcomes, or failed settlement leave a durable `started` recovery
barrier and return `tool_recovery_required` instead of risking a duplicate mutation. Supervisor task-local
metadata carries session/run/tool-call provenance without changing the public two-argument handler contract.
Chat uses the persisted user-message id, channel seams use the stable inbound-message session key, and
A2A delegation now propagates the persisted `A2AMessage.id` into the same ledger. Added direct tests for
completed replay, unfinished/cancelled barriers, supervisor metadata isolation, and updated A2A/Reports
feature contracts with the exact limitation that this is recovery fencing, not an exactly-once guarantee.
Result: Focused authority/lifecycle slice is green (`28 passed`); new Python files are Ruff-clean, targeted
modules compile, Alembic reports `032_pi_tool_executions` as head, feature docs generate/check cleanly, and
`git diff --check` is clean. The implementation is intentionally not yet transported; full integration,
Petals lifecycle, Research Spine ensemble proof, remote Docker acceptance, and branch reconciliation remain open.
Verified: `pytest -q tests/pi_production/test_pi_tool_idempotency.py tests/pi_production/test_tool_authority.py
tests/pi_production/test_scenario_task_lifecycle.py tests/test_pi_replacement_candidate.py` => 28 passed;
`ruff check` targeted new files; `python -m compileall` targeted modules; `alembic heads` => `032_pi_tool_executions`;
`python scripts/feature_docs.py --seed-missing --generate-site --check` => generated 224/check 86/86. No live
model/service/SSH/Docker/host action.
Next: commit/push this bounded idempotency slice with a fresh post-gate, then audit Petals donation/revocation
and the three-model Research Spine ensemble so every route has positive and negative evidence before remote Docker.

### L-106 | 2026-08-26T10:54:00Z | S3-review | gpt-5-codex | reviewer | Post-commit gate records touched-file complexity debt
Did: Ran the pinned native Compass Forge post-change gate after commit `4cdd9cf9`.
Result: Gate record 25 reports `comparison.new_issues` for eight complexity warnings on touched
`chat.py`, `engine.py`, and `agent_lifecycle.py` files/functions. These warnings reflect the existing
large/hot-file architecture plus the added routing/idempotency seams; they are not silently classified
as inherited. The same record reports no new forbidden dependencies, import cycles, security/taint
findings, missing required paths, or unexpected large-file deltas. Repository-wide secret-flow,
route/type, and complexity debt remains a failed global gate and must stay visible in the final closure.
Verified: native CF `gate after` record 25; local `testing` and `origin/testing` both at `4cdd9cf9`;
worktree clean. No live model/service/SSH/Docker/host action.
Next: decide whether to extract the newly touched complexity or record a bounded exception, then audit
Petals donation/revocation and the Research Spine ensemble contract with positive and negative tests.

### L-107 | 2026-08-26T10:57:04Z | S2-execute/S3-review | gpt-5-codex | test-author | Petals consent revocation invalidates the shared Pi projection
Did: Added `test_consent_revocation_removes_pi_projection_and_reconsent_restores_it` to
`tests/petals_bridge/test_petals_bridge.py`. The contract creates a Pi model manager projection
from a healthy, consented donor, revokes consent through the production bridge API, requires the
identity-pinned `pi-petals-donor-1` entry to disappear immediately and resolution to fail closed,
then re-consents and requires an explicit projection refresh before the donor is routable again.
This tests the boundary where Petals donation-management state and the shared Pi Model Management
catalog must agree; it does not claim a live donated-token inference or a process-restart durable
consent guarantee.
Result: `pytest -q tests/petals_bridge/test_petals_bridge.py tests/pi_production/test_research_spine_donor_routing.py`
=> `37 passed in 0.34s`; targeted Ruff and `git diff --check` pass. The audit also confirms that
consent is currently process-memory state (safe default-off after restart) and that the compatibility
route `/api/petals/v1/chat/completions` is bearer-protected but accepts an optional unpinned project,
while Pi-managed calls use the project-pinned route. These are explicit design decisions/open review
items, not silently treated as Research Spine proof.
Verified: no model load, backend/frontend server, SSH, Docker, host package install, or secret read.
Next: commit and push this focused Petals lifecycle contract, then audit the actual three-rater
ensemble execution path and its positive/negative Research Spine gates.

### L-108 | 2026-08-26T11:01:00Z | S3-review | gpt-5-codex | reviewer | Petals lifecycle post-gate boundary
Did: Re-ran the pinned native Compass Forge after gate after Petals lifecycle commit `e443d50d`.
Result: Gate record 26 reports the same eight touched-file/function complexity warnings already
visible on `chat.py`, `engine.py`, and `agent_lifecycle.py`; it reports no new forbidden dependencies,
import cycles, security/taint findings, missing required paths, or unexpected large-file deltas.
Those complexity warnings remain explicit open debt and are not silently reclassified as inherited.
Verified: `pytest -q tests/petals_bridge/test_petals_bridge.py tests/pi_production/test_research_spine_donor_routing.py`
=> 37 passed; local `testing` and `origin/testing` both resolve to `e443d50d`; worktree clean; native
CF after record 26. No live model/service/SSH/Docker/host action.
Next: constrain Petals donor selection by project authorization, then make generic response-level
ensemble metadata explicitly non-formal so the Research Spine tests cannot overclaim Fleiss/Krippendorff validity.

### L-109 | 2026-08-26T11:20:00Z | S2-execute/S3-review/S5-ship | gpt-5-codex | implementer/reviewer | Project-scoped ensemble and non-formal consensus boundary
Did: Propagated Petals donor `allowed_project_ids` into the Pi catalog and filtered project-authorized
donors before `resolve`/`resolve_distinct`; Pi turn, provider-turn, ensemble, and Research Spine coder
selection now carry the active project ID. Added a positive/negative project isolation regression and
asserted that the runtime ensemble receives the project scope. Updated dual-run/full-ensemble/Self-MoA
to emit `validation_scope=response_level_quality_signal`, `formal_reliability=false`,
`research_spine_eligible=false`, and an explicit heuristic-Kappa interpretation. The Evaluation Skill
now labels its artifact provisional/non-reportable and no longer calls response-category Kappa
inter-rater reliability. Corrected a stale provider-provenance test to require the non-secret account handle.
Result: Affected validation, Petals, W1/W7, and end-to-end Research Spine slice is green (`88 passed`);
Ruff and `git diff --check` pass; feature docs regenerate/check (`224` generated, `86/86` checked).
Project-scoped selection now fails before a donor can consume a coder slot, while formal Fleiss/Krippendorff
metrics remain exclusive to the evidence-unit coding path. No live model load or host service was started.
Verified: local and `origin/testing` both at `e68c77f8`; native Compass Forge after gate record 28 reports
`comparison.new_issues=[]`, with only repository-wide inherited complexity/secret-flow/type/route debt.
No SSH, Docker, Mac Studio, or host package action.
Open: the compatibility Petals bearer route remains less project-pinned than the Pi route and consent is
process-memory/default-off after restart; these are documented review items. Remaining P9 work is route
parity, benchmark contract verification, Docker-only remote acceptance, broad regression, independent review,
and safe worktree/branch cleanup.

### L-110 | 2026-08-26T11:31:00Z | S2-execute/S3-review/S5-ship | gpt-5-codex | implementer/reviewer | Explicit Pi alias normalization closed at dispatcher boundary
Did: Audited the direct engine-selection seam after the route-parity pass. `AgenticDispatcher.resolve_engine`
and its async `_resolve` previously returned the raw per-call value, so supported aliases
(`pi-candidate`, `pi-replacement`, and `deepseek-pi`) could bypass the Pi branch when supplied by direct
A2A, benchmark, or service callers. Both boundaries now normalize through `_as_choice`, and a parametrized
regression covers every `PI_ENGINE_VALUES` spelling in both sync and async paths. Living Chat Model Controls
documentation now records this invariant for future callers.
Result: direct aliases select Pi deterministically; no silent legacy fallback is possible from this input
class. Focused W1/W3 dispatcher contracts are green, with no live model load or service start.
Verified: `pytest -q tests/pi_production/test_w1_dispatcher_authority.py tests/pi_production/test_w1_agentic_contract.py tests/pi_production/test_w3_research_spine.py`
=> 64 passed in 5.39s; Ruff and `git diff --check` pass; feature docs generated 224/check 86/86; commit
`7cd98c60` pushed to `origin/testing`; native Compass Forge after gate record 30 reports
`comparison.new_issues=[]` and no new dependency/import/security/taint/missing-path/large-file findings.
Repository-wide inherited complexity, secret-flow, route, and type drift remains failed and explicitly open.
Next: verify all route aliases and compatibility adapters, then run the bounded benchmark contract and
Docker-only Mac Studio inventory/acceptance; no host package or model operations are permitted.

### L-111 | 2026-08-26T11:32:00Z | S2-execute/S3-review/S5-ship | gpt-5-codex | implementer/reviewer | Benchmark crossover order is now executable in every runner mode
Did: Completed the benchmark order audit. The shared schema now derives one engine-independent
crossover identity from phase/pack/scenario/seed/repeat/MoA lane. Offline and live runners, wave
unit construction, and unknown-scenario records all use that identity, so both arms receive the
same `legacy_first`/`pi_first` label. The scheduler now groups paired arms into one deterministic
shard (including each MoA lane) instead of round-robin splitting adjacent arms across processes;
the manifest's order therefore describes real execution. Added regressions for offline order,
live identity independence, pair co-location, and MoA-lane co-location.
Result: `pytest -q tests/pi_benchmark/test_live_driver.py tests/pi_benchmark/test_runner.py
tests/pi_benchmark/test_scheduler.py` => 63 passed; targeted Ruff and `git diff --check` pass.
Commit `0e4e10fa` is pushed to local `testing` and `origin/testing`; native Compass Forge after
gate record 33 reports `comparison.new_issues=[]`, no new dependency/import/security/taint/missing-
path/large-file findings. The global gate remains failed only on repository-wide inherited
complexity, secret-flow, route, and type drift. No model, server, SSH, Docker, or host package action.
Next: audit route parity and two-call/long-horizon contracts, then perform only Docker/Compose
operations on Mac Studio and capture resumable container evidence.

### L-112 | 2026-08-26T11:36:00Z | S2-execute/S3-review/S5-ship | gpt-5-codex | implementer/reviewer | Chat model-catalog engine indicator now shares POST /chat precedence
Did: Audited the route pair that drives Chat engine selection and the UI indicator. `POST /chat`
already used operator flag > request header > project setting > global default, but
`GET /chat/model-catalog` reconstructed only project/default state. That allowed a request header
or operator Pi gate to produce a legacy indicator while the actual turn would run Pi. The catalog
now calls `_resolve_chat_engine` directly, preserving one precedence contract and all alias handling.
Added integration coverage for a Pi alias header and for the operator gate overriding a legacy header;
updated the living Chat Model Controls architecture and generated site manifest.
Result: `pytest -q tests/test_chat.py` => 13 passed; feature docs generated 224/check 86/86; commit
`a531276a` is pushed to local `testing` and `origin/testing`; native Compass Forge after gate record
34 reports `comparison.new_issues=[]` with no new dependency/import/security/taint/missing-path/large-
file findings. Existing repository-wide complexity, secret-flow, route, and type drift remains visible
as inherited gate debt. No model load, server, SSH, Docker, or host package action.
Next: verify the persisted two-call and long-horizon contracts, then inspect the Mac Studio Compose
stack passively before any Docker-only test execution.

### L-113 | 2026-08-26T11:40:57Z | S2-execute/S3-review/S5-ship | gpt-5-codex | implementer/reviewer | Pi coding route provenance now fails closed on served-endpoint drift
Did: Audited the governed `_pi_coder_runner` seam against the Research Spine route-evidence
contract. The selected coder endpoint is pinned in `TurnParams`, but a provider response could
previously report a different endpoint and have that identity persisted as if it were the selected
coder. The adapter now rejects a non-empty served endpoint that differs from the pinned endpoint
before any code application, reliability evaluation, or promotion can occur. The normal route still
allows adapters that omit the endpoint metadata to use the pinned identity. Updated parser fixtures
to include the required exact source quote and corrected the end-to-end fake provider to report the
endpoint actually selected, so tests model the production contract rather than bypassing grounding
or provenance.
Result: `pytest -q tests/test_research_spine_donor_routing.py tests/test_research_spine_end_to_end.py`
=> 9 passed. `pytest -q tests/test_research_spine_donor_routing.py tests/test_research_spine_end_to_end.py
tests/test_research_validity_contract.py` => 40 passed in 66.80s. Ruff and `git diff --check` pass;
feature docs generated 224/check 86/86. `compass-forge gate before` record 35 captured the
expected touched-file complexity warnings for `research_validity_service.py`; no new dependency,
import-cycle, security, taint, missing-path, or unexpected-large-file finding was introduced.
No model load, service start, SSH, Docker, or host package action.
Next: commit/push this bounded fix, then perform passive Docker-only Mac Studio inventory and
validate the persisted two-call/long-horizon, Petals, and benchmark contracts against the remote
Compose stack. Keep live tri-model calls gated and label scripted-provider tests as contract proof,
not model-quality proof.

### L-114 | 2026-08-26T11:42:21Z | S2-execute/S3-review | gpt-5-codex | auditor | Mac Studio acceptance is blocked by dirty remote state and a host-side marathon invocation
Did: Performed the required passive SSH inventory using the server/Docker procedure. The SSH
shell's `PATH` does not include `docker`, but Docker Desktop is installed and the explicit
`/usr/local/bin/docker` client reports Docker client/server 29.7.2; the Compose plugin is available
at `~/.docker/cli-plugins/docker-compose`. The `istara-testing` Compose project renders to a
6,732-byte configuration and its five expected containers (Caddy, frontend, backend, Postgres,
provider-stub) are running and healthy. No runner or marathon process is active now.

The remote checkout at `~/istara-testing` is **not clean**: it is on `testing` at `1b9b6d6`, while
`origin/testing` is also `1b9b6d6`, but it has roughly 300 modified tracked files and untracked
secrets, TLS material, migrations, runner/provenance tests, and smoke scripts. This is an active
worktree with potentially owned changes; no pull, reset, checkout, branch deletion, or cleanup was
performed. The remote `marathon_both.log` also contains `/tmp/run_marathon_remote.sh: line 9: node:
command not found`, proving that at least one marathon attempt executed Node on the Mac Studio host
instead of through the Docker runner. The Docker-only requirement is therefore not currently
proven and the marathon result is invalid until rerun through the containerized runner.
Result: passive inventory only; no host package install, model load, service restart, container
mutation, or remote file mutation. Local `testing` remains clean and pushed at `d2697d1a`.
Next: keep the remote checkout untouched, obtain an explicit owner handoff for its dirty edits,
then use the explicit Docker binary and `docker compose` only. Reconcile the remote clone to the
same origin SHA with a non-destructive, fast-forward-only operation only after it is clean; rerun
marathon/probes inside a disposable Docker runner and capture container IDs, image digests, exit
codes, and scorecard blockers. Do not claim live tri-model or product acceptance from the existing
logs.

### L-115 | 2026-08-26T11:43:50Z | S2-execute/S3-review | gpt-5-codex | auditor | Remote runtime evidence shows tri-model coding executed but did not pass reliability
Did: Read the running Mac Studio containers and Postgres state through the explicit Docker client
only. The database contains 524 legacy and 22 Pi usage rows, with the last recorded activity on
2026-08-24; no current runner process is active. The single persisted coding run
`3737262f-ee6c-4afb-9b8d-7a18231bc509` has three distinct coders (`gpt-5.6-luna`, `gpt-5.6-terra`,
`deepseek-v4-flash`) and three evidence units, but its promotion status is
`needs_reconciliation`, Fleiss kappa is `-0.125`, and Krippendorff alpha is `0.491`. This is
valuable proof that the live path can persist three-model provenance and compute the formal
reliability metrics, but it is **not** proof of accepted Research Spine output; human
reconciliation remains required. The five containers use image digests distinct from the current
local `testing` head and were created 36 hours ago, so they cannot be treated as acceptance of
`d2697d1a` or later changes.
Result: read-only Docker/SQL inspection; no probes, model loads, restarts, image builds, or host
commands. Existing runtime evidence is retained as a blocked/needs-reconciliation artifact.
Next: after owner handoff makes the remote checkout clean, build a fresh disposable Compose stack
from the exact pushed SHA, run the Docker runner (never host Node), and preserve per-engine
scorecards plus the coding-run/reliability/reconciliation records. A green transport count alone
must not close P9-06/P9-07; acceptance requires the complete source-to-human-Done chain.

### L-116 | 2026-08-26T12:02:00Z | S2-execute/S3-review | gpt-5-codex | implementer/reviewer | Local integration and benchmark contract matrix is green; one operator command was corrected
Did: Re-ran the broad local integration matrix after correcting the W7 structured-provider fixture so
it reports the endpoint selected by the test instead of an unconditional placeholder. The matrix
covering dispatcher/agentic routing, Pi runtime hardening, chat ASGI/runtime/catalog behavior,
Research Spine donor/end-to-end/contract/pagination/evaluation paths, settings and Pi endpoints,
model migration, benchmark live/runner/scheduler, and Petals lifecycle now passes
(`363 passed in 83.48s`). The Pi runtime's complete Node suite also passes (`npm test`: 46/46).
The correct real-user benchmark contract command was then run from
`tests/real_user_benchmark`: `npm run check` => 55/55 Node tests plus syntax checks, all green.
The earlier attempt to run `npm run check` from `pi-runtime` failed only because that package has no
`check` script; this was an operator command error, not a code regression, and is recorded here so
another agent does not mistake it for a failing acceptance gate. The security benchmark also passes
at 100% (28/28 controls, `--fail-on-threshold`). No live model was loaded and no remote or host
Mac Studio mutation occurred.
Result: local contract evidence is strong and reproducible, but it remains scripted/faux-provider
proof. It does not establish live model quality, a green accepted coding run, or Docker-only remote
acceptance. The uncommitted W7 fixture correction is intentionally retained until the next commit
and ref reconciliation checkpoint.
Next: commit/push this fixture and ledger checkpoint, then inspect exact worktree/branch ancestry;
remove only clean, merged, demonstrably abandoned registrations, never dirty or recovery worktrees.
Keep P9-06/P9-07 open until a fresh exact-SHA Docker runner produces source-grounded three-model
evidence through reconciliation and human-Done, with the remote owner handoff recorded.

### L-117 | 2026-08-26T12:08:00Z | S2-execute/S3-review | gpt-5-codex | auditor | Local branch/worktree cleanup is conservative and complete for proven disposable state
Did: Verified local `testing` is clean and exactly tracks `origin/testing` at `ce209717`. The
registered worktrees are limited to the active checkout, a clean detached CI checkout at
`/private/tmp/opencode/ci-wt`, and the clean recovery branch checkout
`/Users/user/Documents/Codex/2026-08-10/list/work/istara-pi-linearized-2026-08-10`; both are retained
because they are named CI/recovery state, not demonstrably abandoned work. The two stale temporary
paths `/private/tmp/istara-main-baseline` and `/private/tmp/istara-testing-merge-20260818` contained
only empty directory skeletons (zero regular files, no `.git`, no worktree registration); their empty
directories were removed. `git worktree prune --dry-run` reports no additional stale registrations.
All local branches that are merged into `testing` still have live origin counterparts, so no branch
was deleted without evidence of abandonment; all unmerged/recovery branches were preserved.
Result: no dirty local diff remains, no branch or worktree with active ownership was removed, and the
cleanup is reversible only through the existing remote refs for the two empty skeleton paths.
Next: maintain this clean local/origin testing state while waiting for the remote owner handoff. Do
not reset or clean `~/istara-testing`; its dirty tracked/untracked state remains an explicit blocker
to exact-SHA Docker acceptance.

### L-118 | 2026-08-26T12:12:00Z | S2-execute/S3-review | gpt-5-codex | reviewer | Native Compass Forge gate remains globally red only on inherited debt; this checkpoint adds no new issues
Did: Re-ran pinned-native Compass Forge `status`, `next`, and `gate before`/`gate after` after the
fixture and cleanup checkpoint. Native Rust runtime is active with no Python fallback. Gate-before
record `37` records the expected current repository complexity, secret-flow, route-drift, and
frontend type-drift inventory; the only newly compared touched-file warning is the known size of
`tests/pi_production/test_w7_validation.py`. Gate-after record `38` reports
`comparison.new_issues=[]`, with no new forbidden dependencies, import cycles, security, taint,
missing-path, or unexpected-large-file findings. The global gate remains `fail` because inherited
repository debt is still present; this is not silently treated as a pass. Compass Forge also
confirms CF-13..CF-21 remain open, so no spec/task acceptance claim is made.
Result: lifecycle evidence and code state remain internally consistent; gate truth is preserved.
Next: continue only with a bounded remaining acceptance slice (owner-gated remote handoff, fresh
exact-SHA Docker runner, and blind review); do not mark CF-SPEC-2 or this goal complete while any
required task or Research Spine acceptance artifact is absent.

### L-119 | 2026-08-26T12:24:00Z | S2-execute/S3-review | gpt-5-codex | reviewer | Frontend unit, lint, TypeScript/build, and local benchmark syntax gates are green
Did: Completed the remaining non-server local UI checks. `frontend/npm run test:unit` passes all
3 test files and 15 tests; `frontend/npm run lint` exits 0 with no diagnostics; and
`frontend/npm run build` compiles with Next.js 16.2.4, completes TypeScript, prerenders the four
static routes (`/`, `/_not-found`, `/login`), and exits successfully. The earlier correct
`tests/real_user_benchmark/npm run check` remains green at 55/55 Node tests and all syntax checks.
These checks validate the committed UI/catalog contracts and buildability without starting a
backend/frontend server or loading a model. They do not replace browser acceptance against the
running Docker stack, and they do not prove the three selectable engine journeys or reconciliation
UI on a live Mac Studio service.
Result: P9-11 has strong static/unit evidence but remains open for browser-visible Docker acceptance;
P9-12's local frontend portion is green. The generated `.next` output is ignored and produced no
working-tree changes.
Next: commit/push this ledger checkpoint, then preserve the exact remote blocker and prepare the
owner-handoff request for a clean remote checkout before any Docker runner mutation.

### L-120 | 2026-08-26T12:31:00Z | S2-execute/S3-review | gpt-5-codex | implementer/reviewer | Host-side marathon invocation now fails closed
Did: Audited the Docker runner contract after the Mac Studio log showed `/tmp/run_marathon_remote.sh`
attempting `node` on the SSH host. `scripts/runner/docker-run.sh` already mounts the checkout
read-only and executes `inside.sh` in a disposable container, but the manual
`scripts/marathon/start-marathon.sh` wrapper had no environment boundary and could be invoked on
the host. Added a fail-closed guard requiring either the container marker
`ISTARA_MARATHON_CONTAINERIZED=1` (set by `inside.sh`) or `/.dockerenv`; an SSH-host invocation now
returns exit 2 with an actionable Docker-runner message before creating logs or starting Node.
Added a static regression contract covering both the wrapper guard and the container marker.
Verification: `pytest -q tests/test_marathon_config_integrity.py
tests/test_remote_benchmark_runner_contract.py` => 16 passed; `bash -n` for all three runner
scripts and `git diff --check` pass. No host package installation, model load, service restart,
remote mutation, or Docker execution occurred.
Result: the invalid host-side execution path is eliminated from the supported manual workflow, and
the previous remote log is classified as an operator-contract failure rather than benchmark evidence.
This does not make the current dirty remote checkout acceptable or prove a fresh live tri-model run.
Next: commit/push this guard and ledger, rerun native Compass Forge gates, then request/record an
explicit owner handoff for `~/istara-testing` before any exact-SHA Docker rebuild or benchmark run.

### L-121 | 2026-08-26T12:34:00Z | S3-review | gpt-5-codex | reviewer | Native after-gate confirms no new issues from the Docker boundary fix
Did: Ran pinned-native `compass-forge gate after` on commit `9dae2f2e`. Record `40` reports
`comparison.new_issues=[]`, with no new forbidden dependencies, import cycles, security, taint,
missing-path, or unexpected-large-file findings. The global gate remains red only on the known
repository-wide inherited complexity, secret-flow, route-drift, and frontend type-drift inventory;
that inherited debt is not reclassified as a regression from this change. Working tree and
`origin/testing` are clean and identical at `9dae2f2e`.
Result: the host-marathon guard is shipped with a truthful CF comparison and branch parity.
Next: continue the bounded completion plan: obtain owner authorization to reconcile the dirty
Mac Studio checkout, then perform a fresh exact-SHA Docker-only stack/runner acceptance and record
the full tri-model Research Spine evidence before closing P9-06 through P9-10.

### L-122 | 2026-08-26T12:42:00Z | S2-execute/S3-review | gpt-5-codex | implementer/reviewer | Report gate now requires explicit reconciliation for every coded application
Did: Reproduced and fixed a Research Spine bypass in which a perfect three-model reliability run
set every code application to `promotion_status=accepted`, while `reconciliation_status` remained
`unreconciled`; the task gate counted those rows as reportable and the end-to-end test accepted one
human decision while routing four findings. The gate now has one fail-closed predicate requiring
both an accepted promotion state and a durable `accepted`/`reconciled` reconciliation state. Any
non-rejected application that is not reconciled remains an unresolved blocker, and item-level
support diagnostics only use reconciled evidence-unit ids. A passing Fleiss/alpha score, review
approval, or bulk high-confidence approval cannot substitute for an explicit reconciliation
decision. The end-to-end proof now asserts one decision leaves eight blockers and makes all nine
decisions before human Done approval and report routing; it records nine human decisions.
Result: the red regression first failed as expected (`report_allowed` was incorrectly `True`), then
the corrected focused slice passed: `pytest -q
tests/test_research_validity_contract.py::test_task_research_validity_gate_blocks_unreconciled_report_inputs
tests/test_research_integrity_reports.py tests/test_research_spine_end_to_end.py` => 26 passed in
4.17s. Ruff, `git diff --check`, and feature docs generation/check also pass (224 site artifacts,
86 features). Pinned-native Compass Forge gate-before reports no new actionable failures; the
expected repository-wide complexity/secret-flow/route/type drift remains inherited. No model load,
server start, SSH, Docker, or host package action occurred.
Resulting contract: high agreement produces candidate accepted rows for review, not reportable
evidence; reconciliation is per application and precedes Done/report gates. This closes a material
test oracle gap and makes the positive Research Spine journey honest. The change is not yet
committed or pushed at this checkpoint.
Next: commit/push this service, test, and living-doc fix; run the full local integration matrix and
then continue P9-07–P9-10 with the remote dirty-checkout owner handoff still required.

### L-123 | 2026-08-26T12:48:00Z | S3-review | gpt-5-codex | reviewer | Strict reconciliation gate passes the native Compass Forge comparison
Did: Ran pinned-native `compass-forge gate after --summary` on the committed reconciliation fix
`e1ca7821`. The comparison is clean: `new_issue_count=0`, `new_failures=0`, no new dependency,
import-cycle, security, taint, missing-path, unexpected-large-file, or actionable finding. The
global gate remains `fail` only because the repository-wide inherited inventory still contains 31
failures / 207 warnings (complexity, secret-flow, route drift, and frontend type drift); this is not
attributed to the fix. The feature documentation check remains green at 224 generated artifacts /
86 features, and the branch was pushed to `origin/testing`.
Result: this Research Spine gate change has terminal local CF evidence, but P9-06 still cannot close
until a fresh Docker run proves the remote path and the full accepted/reconciled chain. No model load,
server start, SSH, Docker, or host package action occurred.
Next: run the broad local regression matrix, checkpoint its exact result, then prepare the
owner-gated remote clean checkout request and P9-07–P9-10 evidence collection.

### L-124 | 2026-08-26T12:53:00Z | S2-execute | gpt-5-codex | implementer/reviewer | Broad local regression pass started after strict reconciliation fix
Did: Confirmed the local `testing` worktree is clean and exactly aligned with `origin/testing` at
`d385278d`, which includes the service, test, living-doc, and ledger changes. Started the broad
local matrix covering Pi production/runtime, migration, Petals lifecycle, benchmark contracts,
Research Spine validity/end-to-end/report integrity, chat/catalog routing, task/finding gates,
model/settings contracts, and runner safety. This is a local deterministic/contract pass only:
no backend/frontend server, provider/model load, SSH, Docker, or host package action is permitted.
Result: command is running; no result is claimed yet. The remote Mac Studio checkout remains an
explicit owner-handoff blocker and is not being reset, pulled, or cleaned.
Next: record the exact pass/fail count and any newly exposed regression, then run only bounded
follow-up checks before the remote handoff boundary.

### L-125 | 2026-08-26T13:02:00Z | S2-execute/S3-review | gpt-5-codex | reviewer | Broad local regression matrix is green with two actionable warnings
Did: The broad local matrix collected 918 tests and completed with `913 passed, 5 skipped` in
146.98s (0 failures). It covered Pi production/runtime and migrations, Petals lifecycle, benchmark
and scheduler contracts, Research Spine validity/end-to-end/report integrity, chat/catalog routing,
task/finding gates, settings/model-management contracts, runner safety, and security benchmark
contracts. This validates the strict reconciliation change against the wider local suite, but is
still deterministic/contract evidence rather than live model-quality or Mac Studio acceptance.
Two warnings must remain visible: LanceDB reports that its multiprocessing path is not fork-safe,
and `tests/test_tasks.py::test_agent_execute_task_defers_when_project_paused` emits an
`AsyncSession.close` coroutine-not-awaited warning from the SQLite/asyncio teardown path. The
second warning also produced an `aiosqlite` event-loop-closed thread exception under a traced retry;
it needs a bounded lifecycle fix or an explicit quarantined test-harness disposition before release.
No live model, backend/frontend server, SSH, Docker, or host package action occurred.
Result: local behavior is green but not warning-clean; P9-12 remains open until the warnings are
understood and either repaired or recorded as owned residual risk. Remote exact-SHA acceptance is
still blocked by the dirty `~/istara-testing` checkout and requires its owner handoff.
Next: inspect the warning lifecycle without mutating the remote host, add focused regressions if a
safe fix is justified, rerun the affected slice, and append the finding to the external audit file.

### L-126 | 2026-08-26T13:12:00Z | S2-execute/S3-review | gpt-5-codex | implementer/reviewer | Test-process and notification teardown hazards fixed in scope
Did: Followed the two warnings from L-125. The benchmark concurrency test now uses Python's
`spawn` context instead of `fork`, removing the LanceDB fork-safety warning while preserving the
same cap/arithmetic assertions. `ConnectionManager` now tracks fire-and-forget notification
persistence tasks, exposes `drain_notification_tasks()`, and the application lifespan awaits the
drain after stopping producers. The paused-project execution regression drains the manager before
its event loop closes. This prevents abandoned `AsyncSession.close` coroutines and the observed
`aiosqlite` callback into a closed loop without making websocket broadcasts synchronous.
Result: the affected slice `pytest -q tests/test_websocket.py
tests/test_tasks.py::test_agent_execute_task_defers_when_project_paused
tests/pi_benchmark/test_budget_ledger.py` passes `27 passed` with no warnings. Compass Forge graph
impact/why was run for `backend/app/api/websocket.py`; the feature contract was updated and the
site regenerated (224 artifacts / 86 features). No server, model, SSH, Docker, or host package
action occurred. The external audit file now records this as F-R9-12 fixed locally.
Next: rerun the broad 918-test local matrix to prove warning cleanliness across all affected
callers, then checkpoint the exact result and retain the remote owner-handoff blocker.

### L-127 | 2026-08-26T13:22:00Z | S3-review | gpt-5-codex | reviewer | Post-fix broad matrix is green and warning-free
Did: Re-ran the complete 918-test local matrix after the async notification and multiprocessing
fixes. Result: `913 passed, 5 skipped in 145.08s` with no warnings. The local branch is clean and
exactly equal to `origin/testing` at `c53b3d19bedce313975a78f555117ee1cc27f959`; registered CI and
recovery worktrees remain preserved because they are clean, named, and not proven abandoned. The
pinned-native Compass Forge after-gate for this commit reports `new_issue_count=0`, `new_failures=0`,
no new dependency/import-cycle/security/taint/missing-path/large-file findings, while retaining the
known global inherited debt as `status=fail` (31 failures / 207 warnings). No model, server, SSH,
Docker, or host package action occurred.
Result: local P9-12 behavioral evidence is strong and warning-clean, but it remains deterministic
contract proof. The remote Docker stack still runs older images and a dirty `~/istara-testing`
checkout; exact-SHA acceptance and browser/live-model evidence remain open.
Next: obtain the explicit remote owner handoff, verify the checkout becomes clean without deleting
owned work, then use only explicit Docker/Compose operations for a fresh exact-SHA retake.

### L-128 | 2026-08-26T12:46:38Z | S2-execute/S3-review | gpt-5-codex | implementer/reviewer | Research benchmark and review UI now fail closed on reconciliation gaps
Did: Closed two additional Research Spine oracle/bypass defects found through the graph-backed
review. The real-user coding probe now scopes code applications by `coding_run_id`, fetches the
run's reconciliation decisions, requires exact application-count parity, accepted/reconciled
state, approved review, and a linked accepted/revised decision for every application before it
reports a successful three-donor run. The worker-tool-loop fixture now requires the model to have
observed the canonical `create_task` tool result before returning its final answer, so a scripted
answer cannot hide a broken tool-result round trip. Added positive/negative Node fixtures and a
run-scoped code-application API regression.

The audit also found that the review UI's “Bulk Approve Reliable Codes” and its backend route
changed rows to approved without a durable `ReconciliationDecision` or Evidence Graph edge. The
compatibility endpoint now authenticates and returns HTTP 422 with no mutation; the UI and client
API no longer expose bulk acceptance, and the documentation states that confidence/reliability
only prioritize individual review. This preserves the contract that statistical agreement and
review approval are provisional until per-application reconciliation is recorded.

Verification: `node --test tests/real_user_benchmark/lib/research-spine-probes.test.mjs` => 16
passed; `pytest -q tests/pi_production/test_worker_tool_loop.py tests/test_code_applications.py
tests/test_research_validity_contract.py` => 43 passed; `pytest -q tests/test_code_applications.py
tests/test_project_scope_contracts.py` => 39 passed; `ruff check` on the affected Python files
passed; `frontend/node_modules/.bin/tsc --noEmit -p frontend/tsconfig.json` passed; and feature
docs generation/check passed (224 artifacts, 86 features). The new summary fixture initially
failed on the required `code_id` column and was corrected before the green rerun. No server,
provider/model, SSH, Docker, or Mac Studio host action occurred.

Result: local test oracles now inspect the persisted evidence chain rather than only top-level
promotion flags, and no supported UI/API path can silently bulk-promote research evidence. The
changes are still uncommitted at this checkpoint; P9-06 remains open pending exact-image Docker
proof and P9-07–P9-15 remain open. The dirty `~/istara-testing` checkout is untouched.
Next: run the pinned-native Compass Forge before/after gates for this bounded slice, commit and
push it to `origin/testing`, then add the missing long-horizon tool-result/usage assertions and
re-run the broad local matrix before any remote owner handoff or Docker mutation.

### L-129 | 2026-08-26T12:53:28Z | S2-execute/S3-review | gpt-5-codex | Long-horizon benchmark now proves tool receipts, persisted tasks, and usage rows
Did: Closed the remaining deterministic oracle gap in `tests/benchmarks/long_horizon_runner.py`.
Each turn now requires a terminal `done` receipt whose `tools_used` multiset covers every
canonical SSE `tool_call`; the first turn specifically requires `create_task`. After the
second turn, the benchmark requires a non-empty task queue with valid IDs/titles and exact
project scope. It also queries the content-free chat usage endpoint for the dedicated session
and requires at least two usage rows/turns, a positive token total, and non-empty effective
engine provenance (matching `ISTARA_LONG_HORIZON_ENGINE` when configured). Added positive and
negative contract tests for all three oracles.

Verification: `pytest -q tests/pi_benchmark/test_b0_3_long_horizon_tokens.py` => 15 passed;
`pytest -q tests/test_harness_config.py tests/pi_benchmark/test_b0_3_long_horizon_tokens.py`
=> 32 passed; `ruff check tests/benchmarks/long_horizon_runner.py
tests/pi_benchmark/test_b0_3_long_horizon_tokens.py` passed; `python -m py_compile` passed;
`git diff --check` passed. No server, provider/model, SSH, Docker, or Mac Studio host action
occurred. F-R9-14 was appended to `/Users/user/Desktop/testing.md`.

Result: a long-horizon run can no longer be accepted from plausible assistant prose or a
single persisted transcript alone; its tool execution, task side effect, and usage accounting
must all be observable. The implementation remains uncommitted at this checkpoint. P9-07 and
P9-10 remain open, and the dirty remote `~/istara-testing` checkout remains untouched.
Next: run the pinned-native Compass Forge before/after gates, commit and push the complete
bounded slice, rerun the broad local matrix, then inspect the Pi two-call and Petals live-proof
contracts before requesting remote owner handoff.

### L-130 | 2026-08-26T12:54:07Z | S2-execute/S3-review | gpt-5-codex | before-gate baseline captured for oracle hardening
Did: Ran the pinned native Rust Compass Forge `gate before` from the repository root before
committing the current bounded slice. The comparison reported no new issues, dependency/import
cycles, missing paths, unexpected large files, or other attributable findings; the global gate
remains `fail` only because the repository retains inherited complexity, route/type drift, and
secret-flow debt already present in the baseline. This is a baseline evidence record, not a
claim that the inherited gate debt is resolved.

Result: the reconciliation-oracle, review-bypass, and long-horizon-oracle changes are ready for
commit. No server, provider/model, SSH, Docker, or Mac Studio host action occurred; the dirty
remote checkout remains untouched.
Next: commit and push the explicit file set to `origin/testing`, run the pinned native `gate
after`, and record the attributable comparison before rerunning the broad local matrix.

### L-131 | 2026-08-26T12:54:56Z | S3-review/S4-ship | gpt-5-codex | oracle hardening pushed and after-gate remains attributable-clean
Did: Committed the complete bounded slice as `951ff740` (`fix: close research oracle and
review bypasses`) and pushed it to `origin/testing`. The pinned native Rust Compass Forge
`gate after` recorded `new_issue_count=0`, `new_failures=0`, and no new dependency/import
cycle, missing-path, unexpected-large-file, or security/taint findings. The global status
remains `fail` only for inherited complexity, route/type drift, and secret-flow debt already
present in the repository baseline; no inherited finding was silently waived.

Result: local and origin now contain the same oracle/reconciliation commit. No server,
provider/model, SSH, Docker, or Mac Studio host action occurred. The remote checkout and its
older Docker images remain untouched and are not acceptance evidence.
Next: rerun the full local regression matrix against `951ff740`, then inspect and strengthen
the Pi two-call, Petals lifecycle, benchmark crossover, browser, and exact-image Docker gates.

### L-132 | 2026-08-26T12:57:52Z | S3-review | gpt-5-codex | post-push broad regression matrix is green and warning-free
Did: Re-ran the complete bounded local matrix against the pushed source. The exact command
covering Pi production/runtime and migrations, Petals bridge, benchmark contracts including the
new long-horizon oracles, Research Spine validity/end-to-end/report integrity, chat/catalog
routing, findings/tasks, model-management settings, runner safety, and security contracts
completed with `920 passed, 5 skipped in 146.21s` and no warnings.

Result: the pushed local branch is behaviorally green for deterministic coverage, including the
new tool-receipt, task-persistence, and usage-ledger assertions. This remains contract evidence
only; it does not prove live model quality, browser acceptance, Petals donor interoperability,
or Mac Studio Docker execution. No server, provider/model, SSH, Docker, or host package action
occurred.
Next: review the still-open P9-07–P9-15 gates and strengthen the Pi two-call and Petals live
proof contracts before the required owner handoff for the dirty remote checkout.

### L-133 | 2026-08-26T13:07:04Z | S2-execute/S3-review | gpt-5-codex | Research Spine probe now rejects accepted runs below their declared reliability threshold
Did: Tightened `tests/real_user_benchmark/lib/research-spine-probes.mjs` so an accepted
multi-coder run must carry a finite Fleiss/Cohen kappa that meets its declared threshold;
the probe now records `threshold` and `kappa_meets_threshold` in failure evidence. Added a
regression fixture for a three-donor run claiming `promotion_status=accepted` with
`kappa=0.4` and `threshold=0.6`; it correctly blocks both coding and multi-model validation.
Also completed the Pi two-call contract by asserting exactly two project/session-scoped
`AgenticUsageRow` records, each with `engine=pi`, endpoint `pi-faux`, and successful outcome.

Verification: `node --test tests/real_user_benchmark/lib/research-spine-probes.test.mjs`
=> 17 passed; Compass Forge graph impact/why was run for the changed Pi chat test. The
bounded changes are uncommitted at this checkpoint; no server, provider/model, SSH, Docker,
or Mac Studio host action occurred, and the dirty remote checkout remains untouched.

Result: the benchmark cannot trust an internally inconsistent accepted reliability result,
and the two-call test now observes usage-ledger provenance rather than only chat history.
This is deterministic oracle evidence, not live model or Mac Studio acceptance.
Next: run the pinned-native before gate, append F-R9-15 to `/Users/user/Desktop/testing.md`,
commit/push this bounded slice, run the after gate and warning-free matrix, then inspect
paired benchmark ordering and the remaining Petals Pi-execution/live Docker gaps.

### L-134 | 2026-08-26T13:09:24Z | S3-review/S4-ship | gpt-5-codex | threshold and Pi usage oracle slice pushed with attributable-clean after gate
Did: Completed the pinned native Rust Compass Forge after gate for commit `1362eda8`.
The comparison recorded `new_issue_count=0`, `new_failures=0`, and no new dependency/import
cycles, missing paths, unexpected large files, or security/taint findings. The commit was
pushed non-forced to `origin/testing`; local `testing` and `origin/testing` resolve to the
same SHA `1362eda8c24d641dbc8074c01572c1117aaa8d7d`. The external audit ledger received
F-R9-15 describing the accepted-status/kappa-threshold oracle gap and its fix.

Result: the deterministic Research Spine oracle and Pi two-call usage provenance are now
durable on both local and origin/testing. The global CF gate remains non-terminal only for
pre-existing complexity, route/type drift, and secret-flow debt. No server, provider/model,
SSH, Docker, or Mac Studio host action occurred; the dirty `~/istara-testing` checkout is
still untouched.
Next: inspect the paired benchmark's live execution/provenance contract and the unproven
Petals-through-Pi path, then record bounded fixes or explicit blockers before owner-gated
Docker acceptance.

### L-135 | 2026-08-26T13:16:42Z | S2-execute/S3-review | gpt-5-codex | provider-only Pi seam now fails closed for external test endpoints
Did: Audited `PiExecutionService.run_provider_turn`, the provider-only seam used by the
legacy ReAct bridge, against the streaming chat seam. The streaming path already called
`_enforce_test_provider_network_policy`, but provider-only execution resolved an endpoint
and started the Pi worker without that guard. Added the same fail-closed check immediately
after model-manager resolution and added a regression whose supervisor raises if startup is
reached. A public DeepSeek URL is rejected with `external_provider_blocked_in_test` before
any worker/network action.

Verification: `pytest -q tests/pi_production/test_runtime_hardening.py` => `17 passed in
4.51s`; compileall and `git diff --check` passed. The pinned native Compass Forge before
gate recorded baseline record `50`; it reported no cycles, missing paths, large-file
regressions, or security/taint findings, while showing the existing engine complexity
warning as attributable to the touched file. No server, provider/model, SSH, Docker, or
Mac Studio host action occurred.

Result: ordinary deterministic tests cannot accidentally launch a real provider through
the provider-only Pi/ReAct bridge when external LLM blocking is enabled. This is test
isolation and security hardening, not live model-quality evidence. The change is still
uncommitted at this checkpoint.
Next: run the after gate after commit, push local/origin parity, append F-R9-16 to the
external audit ledger, then continue the paired benchmark and Petals integration audit.

### L-136 | 2026-08-26T13:20:18Z | S3-review/S4-ship | gpt-5-codex | provider-only guard pushed with attributable-clean after gate
Did: Committed the provider-only Pi network-isolation hardening as `5957a9f3` (`fix: guard
provider-only pi turns in tests`) and pushed it non-forced to `origin/testing`. The pinned
native Rust Compass Forge after gate recorded `new_issue_count=0` and `new_failures=0`, with
no new dependency/import cycles, missing paths, unexpected-large-file, security, or taint
findings. The global gate remains `fail` only for the inherited complexity, route/type drift,
and secret-flow debt. The external audit ledger received F-R9-16.

Result: local and origin now include a fail-closed guard for both streaming and provider-only
Pi execution seams; the regression proves a blocked public endpoint cannot start a worker.
No server, provider/model, SSH, Docker, or Mac Studio host action occurred.
Next: inspect whether a configured Petals endpoint actually traverses Pi model management,
project binding, usage/reliability persistence, and ensemble routing; then close any bounded
contract gap before owner-gated exact-image Docker acceptance.

### L-137 | 2026-08-26T13:25:31Z | S2-execute/S3-review | gpt-5-codex | Petals-through-Pi ensemble contract now exercises project-scoped binds
Did: Added a deterministic integration contract to `tests/pi_production/test_runtime_hardening.py`
that drives the real `PiExecutionService.run_ensemble` with `distinct=True` across one faux
model and two Petals-kind model identities. A recording supervisor captures the actual
`provider.bind` payloads; the assertions require three distinct endpoint/model identities,
successful sample aggregation, and both donor URLs to include the URL-encoded project scope.
This closes the prior test gap where Petals and Pi were tested only in separate helpers or
through a fake dispatcher, not through the ensemble execution seam.

Verification: `pytest -q tests/pi_production/test_runtime_hardening.py` => `18 passed in
4.53s`; the initial invalid fixture was corrected after pytest caught missing required
timeout/retry fields; compileall, `git diff --check`, and Ruff all pass. The test is
deterministic and uses no server, provider/model, SSH, Docker, or Mac Studio host action.
The integration test is uncommitted at this checkpoint.

Result: the local contract now proves Pi Model Management, distinct ensemble selection, and
Petals project binding compose correctly at the execution boundary. It still does not prove
real donor interoperability, consent/health projection from a live registry, usage persistence
through the API, or Research Spine acceptance/reconciliation on a Docker image.
Next: run a fresh before gate, commit/push this test, run the after gate and broad matrix, then
decide whether live-benchmark provenance needs a bounded contract fix or remains an owner-gated
acceptance blocker.

### L-138 | 2026-08-26T13:32:48Z | S3-review | gpt-5-codex | Petals/Pi contract and full matrix are green
Did: Committed the Petals-through-Pi ensemble contract and its detailed ledger entry as
`e77c447b` (`test: exercise petals through pi ensemble`) and pushed local `testing` to
`origin/testing`. The pinned native Rust Compass Forge after gate (record `53`) reported
`new_issue_count=0`, `new_failures=0`, and no new dependency/import-cycle, missing-path,
unexpected-large-file, security, or taint findings. The exact bounded matrix was rerun after
the commit and completed `922 passed, 5 skipped in 146.27s`, with no warnings.

Result: deterministic coverage now includes Pi Model Management -> distinct ensemble ->
Petals project-scoped bind composition, alongside the existing Research Spine, usage, task,
and reconciliation oracles. This remains local contract evidence only; live donor health and
consent, actual provider responses, browser behavior, and exact-image Mac Studio Docker proof
are still open.
Next: tighten or explicitly scope the paired benchmark provenance contract, then inspect the
remote Docker checkout/image lineage and request the owner-gated retake without mutating its
dirty working tree.

### L-139 | 2026-08-26T13:43:12Z | S2-execute/S3-review | gpt-5-codex | Docker-only benchmark policy is now fail-closed
Did: Audited the real-user benchmark's three-model topology against the owner requirement that
the Mac Studio host run no Istara service, model, package installation, or host-managed test
workflow. The historical `hostManagedThreeModelRun` branch explicitly kept Istara and the admin
user on the Mac Studio host, and its cleanup helper could manage host benchmark containers. The
runner now refuses that topology before storage probing, live health checks, Docker client
startup, model loading, or package installation, writes `docker-only-policy.json`, records a
critical blocker, and exits non-zero with an actionable instruction to use the Docker wrapper.
The obsolete host-container cleanup/assertion path was removed. The living benchmark README,
plan, registry, system prompt, and Ensemble Health feature contract now describe Docker/Compose
as the only live topology and mark a fully containerized three-donor runner as a required open
acceptance gate.

Verification: the focused topology contract and full real-user harness check both pass (`57
passed`; `node --check` plus all library tests). A direct refusal probe with the legacy topology
produced a non-zero result and persisted `docker-only-policy.json` without starting a service.
`python scripts/feature_docs.py --seed-missing --generate-site --check` regenerated 224 site
artifacts and passed all 86 feature checks. The pinned native Compass Forge before gate (record
54) shows no new dependency/import-cycle, missing-path, unexpected-large-file, security, or taint
findings; its global inherited complexity, route/type drift, and secret-flow debt remains.
No SSH, remote Docker, provider/model, or Mac Studio host mutation occurred.

Result: an unsafe alternate invocation can no longer masquerade as a valid three-model run or
touch the host-managed server path. This is a test-environment safety fix, not live ensemble
quality evidence. The supported `scripts/runner/docker-run.sh` still runs the two engine arms
against the Compose stack with compute donation disabled; it does not yet prove three distinct
live donor routes, Petals consent/health, or Research Spine coding acceptance on the Mac Studio
image. The Python paired-engine benchmark has deterministic crossover ordering, while the
real-user arm metadata remains a companion artifact and does not independently record a seed,
cache/cooldown policy, or complete configuration hash set.
Next: append the Docker-only and remaining live/provenance findings to the external audit ledger,
commit/push this bounded change, run the after gate and warning-free matrix, then obtain explicit
owner handoff for the dirty remote checkout before any Docker retake or branch cleanup.

### L-140 | 2026-08-26T13:55:00Z | S3-review/S4-ship | gpt-5-codex | post-guard matrix and remaining-gates checkpoint
Did: Re-ran the full bounded regression selection after the Docker-only topology guard commit
`b172842f4ff29da702d637153f0dcffdc2014f09`. The command covered Pi production/migration,
Petals, Pi benchmark, chat, Research Spine validity and end-to-end/report contracts, findings,
tasks, settings and engine selection, replacement candidates, harness configuration, remote
benchmark-runner contracts, marathon integrity, and the security benchmark. The local
`testing` ref and `origin/testing` are exactly equal at that SHA and the main checkout is
clean.

Verification: `pytest -q tests/pi_production tests/pi_migration tests/petals_bridge
tests/pi_benchmark tests/test_chat.py tests/test_research_validity_contract.py
tests/test_research_spine_end_to_end.py tests/test_research_integrity_reports.py
tests/test_findings.py tests/test_tasks.py tests/pi_migration/test_model_management_migration.py
tests/test_settings.py tests/test_settings_agentic_pi_endpoints.py
tests/test_pi_replacement_candidate.py tests/test_harness_config.py
tests/test_remote_benchmark_runner_contract.py tests/test_marathon_config_integrity.py
tests/test_security_benchmark.py` => `922 passed, 5 skipped in 146.06s (0:02:26)` with no
warnings. The pinned native Compass Forge after gate is record `55`: `new_issue_count=0`,
`new_failures=0`, and no new dependency/import-cycle, missing-path, unexpected-large-file,
security, or taint findings; inherited complexity, route/type drift, and secret-flow debt
remain globally attributable outside this bounded slice. The topology and real-user harness
contracts remain green (`57 passed`), and the feature-doc generator/check remains green at
86 feature checks and 224 generated artifacts.

Result: deterministic code, test, documentation, and policy evidence is now current on the
transported commit. This still cannot be promoted to live quality evidence: the supported
Docker runner has only two engine arms and explicitly disables compute donation; no exact-image
three-donor stack has been exercised; Petals consent/health/revoke/usage through Pi, three
served model identities, source-diverse Research Spine reconciliation, accepted downstream
promotion, browser-visible paths, or real-user paired provenance remain unproven. The remote
`~/istara-testing` checkout previously observed over SSH is dirty with unrelated tracked and
untracked material, so no reset, pull, checkout, container teardown, or branch cleanup is
authorized until the owner supplies an explicit handoff and the dirty paths are classified.

Resumption order for any agent:
1. Read this Status Block, L-139, L-140, and external findings F-R9-18..F-R9-20 in
   `/Users/user/Desktop/testing.md`; verify `git status --short --branch` and local/remote SHA.
2. Obtain owner confirmation naming the remote checkout and allowing a Docker-only retake;
   preserve a redacted preflight bundle before any mutation. Never run host `pip`, `npm`, `uv`,
   Homebrew, backend/frontend servers, model loading, or host-managed Istara commands.
3. Build or select a Compose topology with three genuinely distinct, Pi-managed donor routes
   (including a consented Petals route where required), isolated per-arm databases/volumes,
   explicit project scope, health/usage/revoke events, and an immutable image digest for
   `b172842f`. Render Compose before startup and fail closed if any service is host-managed.
4. Execute positive and negative Research Spine journeys. Positive must preserve raw source
   spans, source-diverse evidence units, three independent effective rater identities, full
   item/category matrices, grounding, Fleiss/alpha recomputation, explicit reconciliation
   decisions, accepted code applications, lineage through atoms/nuggets -> facts -> insights
   -> recommendations, In Review -> human-approved Done, and a report containing only accepted
   lineage-complete artifacts. Negative controls must prove no leakage for low agreement,
   missing exact spans, missing route evidence, same-model aliases, rejected code, stale/revoked
   route/source, cross-project evidence, missing human approval, and non-Done tasks.
5. Prove two persisted calls, executed tool/result consumption, and long-horizon checkpoint /
   restart / retry / cancellation behavior. Prove Petals donation consent, scheduling,
   accounting, revoke, drain, and no-route-after-revoke without counting one checkpoint under
   multiple aliases as diversity. Persist route and task/tool evidence for every call.
6. Enrich or explicitly scope real-user benchmark provenance. It must either record seed,
   arm/order, cooldown/cache policy, decoding/budget/config hashes, source IDs, image/commit,
   endpoint/model identity handles, timestamps, and container attestation, or be labeled a
   non-comparable companion artifact that cannot support a score or acceptance claim.
7. Retain the redacted evidence bundle (`provenance`, source lineage, coding matrix,
   reliability, reconciliation, promotion lineage, task/report gates, route evidence,
   tool/long-horizon, Petals lifecycle, API/browser results, commands/tests, review, and
   manifest hashes), run the browser and broad/migration/security/docs/CI gates, obtain an
   independent blind review, then attach evidence to CF-13..CF-21 before any acceptance claim.
8. Only after all required gates are terminal, reconcile worktrees and branches. Remove only
   exact-path clean merged worktrees/branches proven unused; preserve dirty, recovery,
   ownership-uncertain, and remote refs. Verify no unaccounted files, clean local checkout,
   exact `testing` SHA equality, and a rollback pointer.

Next: hold at this checkpoint until the owner-gated Docker handoff exists; then start at item 1
and append a new ledger entry before and after every long-running command (no more than two
minutes apart).

### L-141 | 2026-08-26T13:56:30Z | S4-ship | gpt-5-codex | ledger transport and after-gate receipt
Did: Committed the detailed Phase 9 resumption order as `cd1ad63c` (`docs: checkpoint
remaining phase nine gates`) and pushed it non-forced to `origin/testing`. The main checkout
is clean and the exact local/remote ref is `cd1ad63c6e79b9cd1c06e14dba4fd04cfa4f24b2`.

Verification: the pinned native Compass Forge after gate is record `57`, with
`comparison.new_issues=[]`, `new_failures=[]`, and no new dependency/import-cycle,
missing-path, unexpected-large-file, security, or taint findings. The full bounded matrix
after the Docker-only guard is `922 passed, 5 skipped in 146.06s (0:02:26)` with no warnings;
real-user and topology contracts remain `57 passed`, and feature-doc generation/check remains
86 features / 224 generated artifacts. The gate still reports inherited global complexity,
route/type drift, and secret-flow debt; these are not silently reclassified as fixed.

Result: the durable Build Stream document and all bounded implementation/test/doc changes are
now transported to `origin/testing` and resumable by another agent. No Mac Studio SSH/Docker
mutation occurred. Live acceptance is intentionally still open because the remote checkout is
dirty and the current supported runner lacks a fully containerized three-donor topology. Until
the owner names the exact dirty checkout and authorizes a retake, any attempt to pull/reset,
tear down containers, or delete remote/local recovery material would risk data loss.
Next: remain at the owner-handoff gate; after authorization, execute the eight-step resumption
order in L-140 and append the preflight receipt before touching Docker.

### L-142 | 2026-08-26T13:58:00Z | S3-review/S4-ship | gpt-5-codex | after-gate receipt and hold point
Did: Ran the pinned native Compass Forge after gate after transporting the L-141 ledger
checkpoint. Record `58` reports `comparison.new_issues=[]` and `new_failures=[]`, with no new
dependency/import-cycle, missing-path, unexpected-large-file, security, or taint findings.
The existing global complexity, route/type drift, and secret-flow findings remain inherited
debt and are recorded as such. This checkpoint contains documentation-only additions to the
already transported implementation and test commit; no runtime behavior was changed.

Verification: local `testing` and `origin/testing` were equal before this ledger-only append;
the full bounded matrix remains `922 passed, 5 skipped in 146.06s`, real-user/topology contracts
remain `57 passed`, and feature-doc generation/check remains 86 features / 224 generated
artifacts. `git diff --check` passed before commit. No SSH, Docker, model, provider, or host
package action was performed.

Result: the Build Stream document now contains a complete, ordered, resumable P9 work order and
the latest deterministic evidence. The delivery is not complete: live three-donor ensemble,
Petals lifecycle, Research Spine positive/negative acceptance, browser paths, and paired
provenance remain open, and the dirty Mac Studio checkout is intentionally untouched.
Next: commit/push this ledger-only receipt, verify local/remote equality, then stop at the
owner-gated Docker handoff rather than mutating or cleaning the remote checkout.

### L-143 | 2026-08-26T14:05:00Z | S1-plan/S3-review | gpt-5-codex | remote preflight confirms stale dirty checkout
Did: Performed a passive SSH preflight using the configured `macstudio` alias and explicit
Docker client paths only. The remote `~/istara-testing` checkout is still on
`1b9b6d6098dc4a420aff2cf570b9aa5b982b3949`, while this local `testing` and `origin/testing`
are on `f09e3d1ba1c36620a033c5b6e7b585c15b2b74ea`. The remote status lists hundreds of tracked
modifications and untracked deployment secrets/TLS, migrations, smoke scripts, provenance
tests, and generated docs. No path was read for secret contents and no remote file was changed.

Verification: `/usr/local/bin/docker ps` shows only the existing five `istara-test-*` services
plus an unrelated healthy Plex container; the Istara services have been up about 38 hours.
`/usr/local/bin/docker compose -p istara-testing config --quiet` exits 0, but this only proves
Compose syntax. `pgrep`/`ps` found no active benchmark, marathon, or runner process. The exact
remote state and safety implications are appended as external finding F-R9-21 in
`/Users/user/Desktop/testing.md`.

Result: the remote runtime is operationally healthy but stale and not evidence for the
transported commit. The user’s request to make local and remote testing clean cannot be safely
completed by this agent without owner authorization to classify the dirty checkout; resetting,
pulling, deleting secrets, tearing down containers, or deleting branches now would risk another
agent’s work and violate the no-destructive-action boundary. Local checkout remains clean and
the testing refs remain exact.
Next: commit/push this passive-preflight receipt, run the after gate, and hold until the owner
names the remote dirty paths and authorizes the Docker-only retake/cleanup decision.

### L-144 | 2026-08-26T14:08:00Z | S4-ship | gpt-5-codex | final attributable-clean hold point
Did: Ran the pinned native Compass Forge after gate after the passive remote preflight receipt.
Record `59` reports `comparison.new_issues=[]` and `new_failures=[]`, with no new
dependency/import-cycle, missing-path, unexpected-large-file, security, or taint findings.
The inherited global complexity, route/type drift, and secret-flow findings remain visible and
unresolved; they are not being relabeled as introduced by this checkpoint.

Verification: commit `213e80520fef7f610a52b4d253caccc0d91d0546` is pushed non-forced and local
`testing` equals `origin/testing`; the checkout is clean. The latest deterministic baseline is
`922 passed, 5 skipped in 146.06s` with no warnings, real-user/topology contracts are `57
passed`, and feature docs are 86/86 with 224 generated artifacts. Passive SSH confirmed the
remote stack is healthy but stale and no runner is active. No remote mutation or host install,
model load, or server action occurred.

Result: the requested detailed Build Stream document, external audit findings, implementation
fixes, tests, and branch transport are checkpointed for takeover. The objective is deliberately
not marked complete: live exact-image Docker acceptance, three-donor model diversity, Petals
consent/health/revoke/usage, end-to-end Research Spine reconciliation and report gates, browser
acceptance, independent review, and safe cleanup of remote/auxiliary state still require owner
authorization and execution. This is the correct terminal state for this turn because the only
remaining actions would mutate a dirty remote checkout.
Next: wait for owner handoff naming the dirty remote paths and desired preserve/commit/discard
decisions; resume from L-140 item 1 and keep the two-minute checkpoint cadence.

### L-145 | 2026-08-26T14:12:00Z | S4-ship | gpt-5-codex | safe local branch cleanup
Did: Audited the local worktree and merged-branch inventory after transporting `testing`. The
only registered worktrees are the clean current checkout, the clean detached historical CI
checkout at `/private/tmp/opencode/ci-wt`, and the clean recovery checkout at
`/Users/user/Documents/Codex/2026-08-10/list/work/istara-pi-linearized-2026-08-10`. A dry-run
`git worktree prune` reported no stale registrations. Four local branches were exact merged
ancestors of `testing`, had no worktree, and retained matching `origin/*` refs:
`codex/main-stabilization-security-transcription`, `codex/systemwide-agentic-integration`,
`codex/task-review-feedback-learning`, and `feat/dataset-generator-upgrade`.

Verification: removed only those four local pointers with `git branch -d` (merge proof was
required); remote refs remain intact for recovery. No remote branch, recovery branch, detached
CI worktree, dirty path, protected artifact, or working tree was deleted. The main checkout
remains clean and `testing` equals `origin/testing` at `29634792c65cbf1d97c06743a25e3db7cd6c0c87`.

Result: the demonstrably unused local branch pointers are gone without deleting their remote
history, while every ownership-uncertain or recovery target is preserved. Remote cleanup and
Docker retake remain blocked by F-R9-21 and require the owner’s explicit preserve/commit/discard
decision for `~/istara-testing`.
Next: run no destructive remote action. Wait for owner handoff, then resume the Docker-only
three-donor acceptance and final P9 closure sequence from L-140.

### L-146 | 2026-08-26T14:16:00Z | S4-ship | gpt-5-codex | post-cleanup gate and handoff hold
Did: Completed the post-cleanup Compass Forge after gate. Record `60` reports
`comparison.new_issues=[]` and `new_failures=[]`, with no new dependency/import-cycle,
missing-path, unexpected-large-file, security, or taint findings. Existing global complexity,
route/type drift, and secret-flow findings remain inherited debt. The local branch cleanup did
not alter runtime code or protected artifacts.

Verification: the main checkout is clean; local `testing` equals `origin/testing` at
`75369827f0faccacf59f47b97efbd7b86264a6db`. The only remaining worktrees are the preserved
detached CI checkout and intentional recovery checkout; `git worktree prune --dry-run` has no
registrations to remove. The deterministic matrix, harness contracts, feature-doc checks, and
remote passive preflight evidence remain as recorded in L-140/L-145. No SSH or Docker mutation
occurred in this gate.

Result: all safe, local, in-scope work for this turn is transported, documented, tested, and
clean. The active goal remains open because the owner-gated remote handoff and live exact-image
Docker acceptance have not happened. This hold is intentional and fail-closed; it prevents a
reset or teardown from destroying the dirty Mac Studio checkout and prevents deterministic
contracts from being misreported as live multi-model Research Spine proof.
Next: owner must name the remote dirty-path disposition and authorize the Docker-only retake;
the next agent should resume from L-140 item 1 and append a preflight checkpoint before any
remote mutation.

### L-147 | 2026-08-26T14:25:00Z | S2-execute | gpt-5-codex | owner authorization received; Docker retake may begin
Did: The owner explicitly authorized Docker operations and disposal of old testing containers
and data, with the requirement that nothing be installed or run on the Mac Studio host. This
changes the prior hold: Docker/Compose teardown, fresh test volumes, image rebuild, and
containerized benchmark execution are now in scope. Source changes in the dirty checkout remain
preserved until a clean isolated worktree is established; authorization to discard containers
does not silently authorize deleting unclassified source files or secrets.

Preflight boundary: use SSH only for passive Git/Docker control, create a clean detached
worktree from `origin/testing` at the transported SHA, and keep the dirty `~/istara-testing`
checkout untouched except for reading metadata and using its deploy environment/TLS paths as
needed. Remove only the old Compose project containers, anonymous/named testing volumes, and
test result data explicitly covered by the owner authorization. Render Compose before startup,
capture redacted service/image/network/volume configuration, and fail closed if any service is
host-managed or any command invokes host package installation/model loading/server startup.

Next: execute the remote preflight and isolated-worktree creation, checkpoint its exact path,
SHA, container/volume inventory, and redacted artifact location before `docker compose down -v`
or any image rebuild. Then run the exact-image Docker-only comparison and Research Spine proof
in bounded intervals, appending a ledger entry at least every two minutes.

### L-148 | 2026-08-26T14:32:00Z | S2-execute/S3-review | gpt-5-codex | clean remote worktree and pre-teardown receipt
Did: Used the owner-authorized SSH control plane to fetch `origin/testing` and create the
isolated detached worktree `~/istara-testing-clean-6ce9374a` on the Mac Studio. The dirty
`~/istara-testing` checkout was not reset, cleaned, or otherwise mutated; its 340 changed paths
remain available for later owner-directed classification. The clean worktree resolves to
`6ce9374aacc821511a821dab9320d03d72e8ad1c` and has zero porcelain changes.

Verification: before teardown, the old Compose project `istara-testing` rendered successfully
with `~/istara-testing/.env.deploy`; five Istara containers (Caddy, frontend, backend, Postgres,
provider-stub) had been up approximately 39 hours, and the only project volume was
`istara-testing_istara-runtime-env`. Remote `HEAD` and `origin/testing` were both the stale
`1b9b6d6` before fetch; after fetch, the clean worktree and GitHub ref are exact at `6ce9374a`.
No secret contents were read or logged.

Result: the exact pushed source is now isolated from the dirty remote checkout, satisfying the
safe-rebuild precondition. The owner authorization covers disposal of the old testing containers,
runtime volume, and test data; it does not cover deleting the dirty source checkout. The next
remote action is an explicit Docker Compose teardown followed by a rendered-config capture and
fresh build from the clean worktree.
Next: append the teardown/build preflight receipt before starting the bounded runner; keep all
live services, model clients, and dependency installation inside Docker containers only.

### L-149 | 2026-08-26T14:38:00Z | S2-execute/S3-review | gpt-5-codex | authorized old-stack teardown complete
Did: Updated the isolated remote worktree to the latest transported `origin/testing` commit
`07c0512d915805f707b7a7f26ee2d1593713f8b2` and executed the owner-authorized Docker Compose
teardown from that clean worktree. The old `istara-testing` Caddy, frontend, backend, Postgres,
and provider-stub containers were stopped and removed; the project runtime environment volume
and four project networks were removed with `down -v --remove-orphans`.

Verification: Compose rendered successfully before teardown. After teardown, no container with
the `istara-testing` Compose label and no volume matching `istara-testing` remained. The clean
worktree has zero status changes and exact `HEAD=origin/testing=07c0512d`; the dirty
`~/istara-testing` source checkout was not reset, deleted, or used as the build context. No
host package manager, server, model load, or non-Docker runtime was invoked.

Result: stale testing data and containers are removed as authorized, eliminating prior database
and warm-state contamination. The next acceptance must build from the detached clean worktree,
with a redacted Compose/image capture before startup and fresh per-run data. Any failure to
provide three real donor routes or full Research Spine evidence remains a blocker, not a score.
Next: render the effective Compose configuration, build the exact backend/frontend/provider
images, capture digests and health evidence, then start only the containerized stack.

### L-150 | 2026-08-26T14:45:00Z | S2-execute | gpt-5-codex | pre-build checkpoint after authorized teardown
Did: Confirmed the next long-running action is constrained to the isolated clean remote worktree
and Docker daemon. The old Compose stack/data are already removed under owner authorization;
the dirty `~/istara-testing` checkout remains preserved. The clean worktree will be refreshed
to the latest pushed `origin/testing` ledger SHA before build, and the deploy environment file
will be consumed without printing its contents.

Build contract: render Compose before startup; save only a redacted configuration snapshot and
hashes/IDs; build backend, frontend, and provider-stub images with Docker; do not run host
package managers, Node, Python, model servers, or application services. Use the existing TLS
directory and deploy environment only as Docker bind/config inputs. Retain the resulting image
IDs/digests and all benchmark artifacts under a timestamped remote evidence directory.

Next: refresh the detached worktree, capture the redacted Compose/config preflight, run the
Docker image build, verify image IDs and clean source SHA, then checkpoint before starting the
stack and benchmark runner.

### L-151 | 2026-08-26T14:58:00Z | S2-execute/S3-review | gpt-5-codex | refreshed clean source and redacted Compose preflight
Did: Refreshed the isolated Mac Studio worktree `~/istara-testing-clean-6ce9374a` from
`origin/testing` and verified it is detached, clean, and exact at
`2d536d143eea80bc08ec33c9939d65cfdb8e954a`. The previously dirty `~/istara-testing`
checkout was not reset or cleaned. Compose was rendered with the deploy environment before
any service startup; the raw rendered configuration was never persisted, and only a redacted
snapshot was written.

Evidence: remote artifact directory
`/Users/user/istara-testing-evidence-20260826T145000Z`; source receipt reports
`source_status_count=0`; redacted Compose hash is
`6231482927650112a468dd38be0e8e0b8c9cef5f95f98362c03af7fc9cf980b9`. The effective service
set is `postgres`, `backend`, `frontend`, `caddy`, and `provider-stub`; the only declared
project volume is `istara-runtime-env`. No host package manager, host runtime, model server,
or application process was invoked. Secret values and deploy-file contents were not printed.

Result: the Docker-only rebuild precondition is satisfied with auditable source/config
provenance. This proves configuration validity and source isolation only; it does not prove
that PI Model Management, Petals donation, three independent donor routes, ensemble
reconciliation, Fleiss' kappa, or long-horizon/two-call behavior works live. Those remain
explicit acceptance gates, and any provider-stub or missing-donor result must be recorded as
a blocker rather than converted into a quality claim.
Next: append the build-start receipt, run `docker compose build --pull` from this detached
worktree, capture image IDs/digests and build logs, then checkpoint before `up` or the bounded
runner.

### L-152 | 2026-08-26T15:02:00Z | S2-execute | gpt-5-codex | Docker build-start checkpoint
Did: Transported the preflight ledger update as commit `405dce18` to `origin/testing`; the
detached Mac Studio build context must now refresh to that exact SHA before compilation. The
build is bounded to the five Compose services (`postgres`, `backend`, `frontend`, `caddy`,
`provider-stub`) and uses Docker’s existing images/cache plus the repository Dockerfiles.

Safety contract: no host package installation, host Python/Node execution, host server,
provider/model loading, or source reset/cleanup is permitted. Build logs and image metadata are
captured under the existing timestamped evidence directory without printing deploy secrets.
The build result is an artifact-integrity gate only; a successful image build cannot establish
PI Model Management routing, Petals donation, independent donor diversity, ensemble
reconciliation, Fleiss' kappa, or long-horizon research validity.

Next: refresh `~/istara-testing-clean-6ce9374a` to `origin/testing`, run
`docker compose build --pull`, capture service image IDs/digests and build exit status, then
append a post-build checkpoint before any container startup or benchmark request.

### L-153 | 2026-08-26T15:10:00Z | S2-execute/S3-review | gpt-5-codex | Docker build blocked by SSH credential-helper PATH
Did: Refreshed the isolated worktree to the pushed build checkpoint `972352de` and invoked
`docker compose build --pull` through the Mac Studio Docker daemon. Docker Desktop accepted the
request, but BuildKit failed before compiling the backend because the non-interactive SSH PATH
(`/usr/bin:/bin:/usr/sbin:/sbin`) could not resolve the configured `docker-credential-desktop`
helper while resolving the Dockerfile frontend image. Frontend and provider-stub metadata
resolution were canceled as a consequence; no service started and no model was loaded.

Evidence: the failed build log is retained at
`/Users/user/istara-testing-evidence-20260826T145000Z/docker-compose-build.log`; the clean
build source receipt is at the same directory and resolves to `972352de` with zero status
changes. A passive check found the existing executable at
`/Applications/Docker.app/Contents/Resources/bin/docker-credential-desktop`, so this is an
SSH environment PATH/configuration defect rather than authorization to install a host package.

Result: the image-integrity gate remains open. The remediation is bounded to adding the
existing Docker Desktop resources directory to the SSH command's PATH (or an equivalent
Docker CLI config fix) and retrying the same build. Do not claim a Docker build, runtime
health, model-management behavior, ensemble operation, Fleiss' kappa, or Research Spine
acceptance until the retry produces exact image IDs/digests and subsequent live gates.
Next: append the external audit finding, then retry with the explicit existing helper PATH;
if it fails again, preserve the exact error and stop rather than installing anything on-host.

### L-154 | 2026-08-26T15:18:00Z | S2-execute/S3-review | gpt-5-codex | Docker image build passed with exact arm64 artifacts
Did: Retried the Compose build from the detached clean Mac Studio worktree with the existing
Docker Desktop credential-helper directory added to the SSH command PATH. The five-service
configuration rendered successfully and the three buildable services completed with Docker:
`istara-testing-backend`, `istara-testing-frontend`, and `istara-testing-provider-stub`.
Postgres and Caddy remain the declared upstream images; no service was started during this
gate, and no model or application request was sent.

Evidence: build source receipt
`/Users/user/istara-testing-evidence-20260826T145000Z/retry-build-source.txt` reports clean
`HEAD=bf5504d4e922ef370f20f7fcd05ea93cebc734fb`; build log is
`docker-compose-build-retry.log`. Image manifests/digests are:
backend `sha256:974f62509b0b8161c67514c527247d8133f200ae6e2bb361a019800855756ec9`, frontend
`sha256:424964efd00cf9f6beac3819a8c5722dff3091854ff8064c7ed527d191d175c7`, provider-stub
`sha256:83088073c05e7ca7ea244320e547ec4e2b27061e65f41bfc7dd8a1a7249c969b`, Postgres
`sha256:cf78e76683b9ca8c5733cbbdce6c9262b45b6767934dd0a95e671f9a0fc20685`, and Caddy
`sha256:5f5c8640aae01df9654968d946d8f1a56c497f1dd5c5cda4cf95ab7c14d58648`.

Result: the artifact-integrity gate is green for this Docker Desktop host and exact source
lineage. The build installs dependencies only inside image layers; it is not evidence that
runtime routes, provider/model registration, Petals donation, independent donor diversity,
ensemble aggregation, Fleiss' kappa, two-call semantics, or human-approved Research Spine
promotion work. Base image tags remain mutable inputs and must be retained with these resolved
digests for any comparable retake.
Next: append the startup checkpoint, refresh the detached worktree to the latest pushed ledger
SHA, run `docker compose up -d --wait`, and record health, listeners, effective env provenance,
and logs before invoking `scripts/runner/docker-run.sh`.

### L-155 | 2026-08-26T15:22:00Z | S2-execute | gpt-5-codex | container startup checkpoint after successful build
Did: Transported the successful image-build receipt as commit `e31ee276` to `origin/testing`.
The next operation is a fresh Compose startup from the detached clean worktree, with the old
project already torn down and the Postgres service configured for ephemeral test state. Startup
will use Docker Compose only and will not invoke a host runtime, package manager, model server,
or interactive application session.

Startup evidence contract: record the exact detached source SHA, container IDs, image digests,
health status, exposed listener mappings, Compose project/network/volume inventory, and bounded
service logs. Do not print deploy secrets or infer readiness from `docker ps` alone; each service
must have a passing health/readiness signal or the gate remains open. This gate is operational
only and cannot substitute for PI Model Management route checks or three-donor Research Spine
evidence.

Next: refresh `~/istara-testing-clean-6ce9374a` to `origin/testing`, execute
`docker compose up -d --wait`, capture health/listener/log receipts, and checkpoint before the
two-engine runner or any live request.

### L-157 | 2026-08-26T15:42:00Z | S2-execute | gpt-5-codex | bounded Docker runner checkpoint
Did: Transported the healthy-stack receipt as `e7fca1be` on `origin/testing`. The next live
request is limited to one invocation of the supported `scripts/runner/docker-run.sh` from the
detached clean worktree. It will run the repository's two declared arms (`legacy` and `pi`),
recreate the Compose stack per arm, and execute the benchmark inside the disposable
`node:20-bookworm` runner container. The source snapshot SHA-256 will be computed from the
exact detached Git archive and passed into the runner; the deploy password remains an
unprinted environment value.

Acceptance boundary: this runner is valid for Docker-only two-engine service/route and
provenance checks, but its contract explicitly sets `ISTARA_BENCHMARK_REQUIRE_COMPUTE_DONATION=0`
and does not provision three donor model/relay containers. Therefore even a zero-blocker
completion cannot establish Petals donation, three independent donor identities, ensemble
aggregation, Fleiss' kappa over three live models, or full Research Spine promotion. Any
provider-stub, live-chat, task, or coding failure is retained as a blocker-bearing result.

Next: refresh the detached worktree to `origin/testing`, calculate the exact archive hash,
run one `docker-run.sh` invocation with the existing Docker helper PATH, retain its complete
stdout/stderr and generated artifacts, then append the arm-level disposition before any retry.

### L-156 | 2026-08-26T15:35:00Z | S2-execute/S3-review | gpt-5-codex | fresh Docker stack healthy before benchmark
Did: Refreshed the detached Mac Studio worktree to the transported startup checkpoint
`dd1b30fb` and started the rebuilt Compose project `istara-testing` with Docker Compose
`up -d --wait`. The command returned `UP_RC=0`; no host runtime, package manager, model server,
or non-container application was invoked. The old stack/data had already been removed, so this
runtime uses fresh ephemeral Postgres state.

Evidence: `/Users/user/istara-testing-evidence-20260826T145000Z/startup-source.txt` reports
clean source `HEAD=dd1b30fb4d6ea72a1eda53cd56dc91d1b49b0d81`. The Compose receipt shows healthy
backend, frontend, Postgres, and provider-stub containers; Caddy is running with Docker-only
published ports `13080->80` and `13081->443`. Container IDs, image IDs, and bounded 200-line
service logs are retained in `docker-ps.txt`, `runtime-images.txt`, and
`runtime-logs-tail.txt` under the same directory. Runtime images match the build manifests
recorded in L-154 (backend `974f62509b0b`, frontend `424964efd00c`, provider-stub
`83088073c05e`, Postgres `cf78e76683b9`, Caddy `5f5c8640aae0`).

Result: the operational Docker gate is green. This demonstrates only that the exact arm64
artifacts can start and pass Compose health checks. It does not demonstrate PI Model
Management endpoint parity, Petals slash-string donation integration, three independent donor
routes, source-grounded atomic coding, reliability/reconciliation, Fleiss' kappa, two-call
semantics, long-horizon behavior, or human-approved Done/report gates.
Next: run `scripts/runner/docker-run.sh` exactly once from this clean worktree inside the
containerized topology, capture its complete scorecard/exit status, and checkpoint before any
second request or topology change.

### L-158 | 2026-08-26T15:52:00Z | S2-execute/S3-review | gpt-5-codex | runner precondition failed before benchmark
Did: Invoked `scripts/runner/docker-run.sh` exactly once from the clean detached worktree at
`4915b634`, with the exact Git archive hash
`1610ec53af0b75ced7e9807886e7a62b990a1ceb7a3f1f957fab1e021d653da9` and Docker helper PATH.
The script exited `1` before pulling its runner image, recreating Compose, sending a chat turn,
or loading any model because the clean checkout did not contain the ignored directories
`tests/real_user_benchmark/.results`, `tests/simulation/.results`, and `data/test-marathon`.

Evidence: `/Users/user/istara-testing-evidence-20260826T145000Z/runner-source.txt` records
the source hash, zero source status changes, and `runner_rc=1`; `docker-run.log` contains only
the missing-result-directory precondition. The existing stack remains available, but no
benchmark arm or Research Spine artifact was produced by this attempt.

Result: the runner is not self-starting from a clean detached checkout, which is incompatible
with the stated reproducible Docker-only workflow. This is a harness/process defect, not a
model-quality result. The next action must either make the script create its disposable result
directories (with a regression test) or create them inside the clean checkout as a narrowly
documented fixture; prefer the self-contained script fix so future clean worktrees work without
manual host preparation. Re-run only after Compass Forge impact/why and a transported
checkpoint; keep the three-donor limitation and fail-closed scoring boundary unchanged.

### L-160 | 2026-08-26T16:32:00Z | S3-review/S2-execute | gpt-5-codex | live two-arm Docker run disposition and runner hardening
Did: The self-bootstrapping runner fix reached Docker successfully and ran both `legacy` and
`pi` arms exactly once. Both arms completed their marathon cycle but exited blocker-bearing
(`runner_rc=1`); the generated probe runs were `2026-08-26T14-27-30-842Z` (legacy) and
`2026-08-26T14-30-37-057Z` (pi). The latest Pi score was `43.5/100`, with `0/8` chat turns,
`0` completed tasks, `6` uploads, and `8` blockers. The legacy run reported a UI shell
readiness error followed by provider `402 Insufficient Balance` on chat/task requests.

Research disposition: the live run recorded `expected_distinct_coders=3` but
`distinct_model_count=0`, `rater_count=0`, `kappa=null`, `alpha=null`, and no served donor
routes; `compute_donation_verified=false`, `multi_donor_compute_verified=false`, and
`coding_validation_verified=false`. The Pi report marked `research_spine_traceability_verified`
true only for structural traceability, not accepted coding/reliability/reconciliation. This is
not evidence that the ensemble engine or PI Model Management is correct. The marathon summary's
`38/38` pass is a companion infrastructure cycle and does not override chat/provider or
Research Spine blockers. Evidence is retained under
`/Users/user/istara-testing-evidence-20260826T145000Z/`, including both run summaries, the
runner log, scorecard, and marathon issue artifacts.

Audit findings from this run: the original clean-checkout failure exposed missing generated
mounts (fixed in `ca2776ea`); the first successful run exposed that `ISTARA_BENCHMARK_SOURCE_SHA`
was never passed, so provenance validation falsely reported a missing source commit; and a
passive process listing showed the admin password embedded in the `docker run -e` argument
vector. Compass Forge after-gate record `62` reports no new comparison issues, failures,
dependency/import cycles, missing paths, unexpected-large-file, security, or taint deltas; its
inherited secret-flow warnings do not cover this runner argument leak.

Remediation in progress: pass the detached Git commit explicitly as `ISTARA_BENCHMARK_SOURCE_SHA`
and provide the three password aliases through a mode-600 temporary Docker `--env-file` removed
by an EXIT trap. Add static contracts for both changes, retain the Docker-only topology, and do
not rerun until the fix is transported. The current two-arm runner still intentionally sets
`ISTARA_BENCHMARK_REQUIRE_COMPUTE_DONATION=0`; three-donor/Petals/ensemble acceptance remains a
separate required implementation and test gate.
Next: commit/push this runner hardening, run the full deterministic contract matrix plus feature
docs, refresh the detached worktree, and execute one final two-arm run only to validate harness
provenance and secret handling. Treat any provider 402, missing donor, zero-rater, or absent
human-approval result as an explicit blocker.

### L-161 | 2026-08-26T16:40:00Z | S2-execute | gpt-5-codex | verification-wave checkpoint after runner hardening
Did: Transported the self-bootstrapping, source-provenance, and secret-safe runner changes as
`deaffea1` to `origin/testing`. The hardening is intentionally limited to the Docker benchmark
harness: it creates ignored result mounts, passes the exact Git commit into `/work`, and moves
password aliases from visible CLI arguments to a mode-600 temporary env file removed on exit.
No application route, model manager, ensemble algorithm, or Research Spine gate was changed.

Verification contract: run the complete bounded matrix used in L-140, the 57-case real-user
harness contract check, shell syntax, and feature-doc generation/check. Attach exact commands
and outputs before the next remote run. The final remote retake must use a fresh source hash and
record the source commit in each arm's `run-metadata.json`; a process-list check must confirm no
password value appears in the active Docker command line. The runner remains a two-arm companion
and cannot prove three-donor Petals or live Fleiss' kappa.

Next: execute local deterministic verification, append its result, then refresh the detached
Mac Studio worktree to `origin/testing` and run exactly one post-fix Docker comparison.

### L-162 | 2026-08-26T17:05:00Z | S3-review | gpt-5-codex | deterministic verification complete; live provider gap recorded
Did: Ran the complete bounded deterministic matrix after the runner hardening (`923 passed,
5 skipped in 145.67s`), the real-user benchmark contract/language checks (`57 passed`), and
`python scripts/feature_docs.py --seed-missing --generate-site --check` (`seeded 0`, `generated
224`, checks passed for `86` features). Compass Forge after-gate record `63` reports no new
comparison issues, failures, dependency/import-cycle, missing-path, unexpected-large-file,
security, or taint deltas; inherited global complexity, route/type, and secret-flow warnings
remain unchanged.

Live retake disposition: both Docker arms completed the marathon companion cycle (`38/38` in
the final cycle) but the probe path exited with blockers. The legacy run stopped at one chat
turn with provider `402 Insufficient Balance`; the Pi run recorded `score=43.5`, `chat_turns=0`,
`completed_tasks=0`, `blocker_count=8`, `compute_donation_verified=false`,
`multi_donor_compute_verified=false`, `coding_validation_verified=false`, and no live chat.
The Research Spine evidence was explicitly `expected_distinct_coders=3`,
`distinct_model_count=0`, `rater_count=0`, `kappa=null`, `alpha=null`, and
`served_donor_route_count=0`. The healthy provider-stub container was not a substitute for a
configured reachable model provider, so no PI Model Management route, Petals slash-string
donation path, three-model ensemble, or human-approved coding/reconciliation path was actually
exercised. These results are blocker evidence, not a quality score.

Result: the local code and Docker artifact gates are green, but the supplied live test
configuration cannot answer the owner's central model/ensemble question. A final retake after
the runner hardening can validate provenance and secret hygiene, but it will remain non-
authoritative for Research Spine quality unless a reachable authorized provider and three
served donor routes are configured inside Docker. The runner's current `REQUIRE_COMPUTE_DONATION=0`
and two-arm topology must be replaced or supplemented for that acceptance.
Next: commit this verification receipt, refresh the clean worktree, run one post-fix comparison,
and inspect each run's `run-metadata.json` for the exact source commit and absence of a password
in any process command line. Then update the remaining-work plan with the provider/donor
implementation work still required.

### L-159 | 2026-08-26T16:05:00Z | S1-plan/S2-execute/S3-review | gpt-5-codex | runner bootstrap fix specified by CF and TDD
Did: Ran Compass Forge `intelligence impact --path scripts/runner/docker-run.sh` for the
pristine-checkout request. The graph classified the surface as high-confidence with likely
architecture-drift, security-sensitive, and API/contract-drift rules; it recommended runner,
benchmark, compute, Petals, and orchestration verification. `intelligence why` and
`test-impact` returned no direct file relationships, so the repository's static contract suite
was used as the explicit safety net. Compass Forge `gate before` record `61` completed with no
new comparison issues, failures, dependency/import-cycle, missing-path, unexpected-large-file,
security, or taint deltas; inherited global warnings remain unchanged.

TDD evidence: added a regression assertion for a pristine checkout, observed the expected red
failure (`1 failed`), then changed only `scripts/runner/docker-run.sh` to create the three
ignored disposable bind-mount directories with one `mkdir -p` before any Docker action. The
targeted regression is green and the complete remote-runner contract module is green (`13
passed`). The script still mounts the source read-only into the disposable runner and performs
all runtime/package/model work inside Docker.

Result: this removes the manual-host-preparation failure found in L-158 without weakening
source hash, fresh-Postgres, engine isolation, or fail-closed arm handling. The change does not
add donor containers or alter the runner's explicit `REQUIRE_COMPUTE_DONATION=0` boundary; live
three-model ensemble and Research Spine proof remain separate open gates.
Next: commit and push the script/test/ledger fix, refresh the detached Mac Studio worktree,
rebuild if the source image changed, and rerun exactly one bounded Docker comparison. Preserve
its scorecard even when the two-arm harness exits with blockers.

### L-163 | 2026-08-26T17:10:00Z | S4-ship/S2-execute | gpt-5-codex | receipt transported; final retake pinned to e88a532b
Did: Committed and pushed the L-162 deterministic/live disposition plus the generated feature-site
manifest as `e88a532b` to both local `testing` and `origin/testing`. The branch is now the exact
source of truth for the final Docker retake. No application/model/ensemble behavior was changed
by this receipt; the remaining work is verification and explicit external-provider/donor closure.

Final retake contract: refresh only the detached clean Mac Studio worktree to `e88a532b`; keep the
owner's dirty `~/istara-testing` checkout untouched; use Docker Desktop/Compose and the runner's
mode-600 env-file path; run exactly one bounded legacy+Pi comparison; capture each arm's
`run-metadata.json`, exact source commit/snapshot, and a boolean-only process-list secret check;
then tear down testing containers/volume/network with the authorized Docker cleanup. Any 402,
zero-rater, zero-donor, absent human approval, or missing three-model evidence remains a blocker,
not a model-quality result.
Next: execute that retake and append its exact disposition as L-164, then append the teardown
receipt and remaining provider/donor implementation plan before closing this goal.

### L-164 | 2026-08-26T17:15:00Z | S2-execute | gpt-5-codex | final Docker retake preflight prepared
Did: Confirmed the Mac Studio detached worktree was refreshed cleanly to `ca7a9301`, while the
owner's dirty `~/istara-testing` checkout remained preserved. The existing Compose stack is
healthy and the Docker Desktop credential helper is available on the explicit SSH control PATH;
no host package installation or host-side service was introduced. The authorized teardown scope
remains limited to the testing Compose containers, network, volume, and disposable result data.

The next command will compute a fresh `git archive` snapshot from this exact detached source,
source the existing testing Compose env without printing secret values, run exactly one
legacy+Pi `scripts/runner/docker-run.sh` comparison with the mode-600 env-file hardening, and
capture only redacted metadata/logs. During the run, a boolean-only process-list check will test
that password aliases are absent; no command line containing a credential will be emitted. This
retake is scoped to provenance/secret hygiene and two-arm behavior; provider 402, zero donors,
zero raters, null reliability metrics, or absent approval remain explicit blockers.
Next: execute the one final comparison, checkpoint any long-running progress, then inspect
`run-metadata.json` and append its exact disposition before authorized Docker teardown.

### L-165 | 2026-08-26T17:20:00Z | S2-execute | gpt-5-codex | final-retake wrapper preflight corrected before Docker execution
Did: The first remote invocation against the clean `77940c4c` worktree stopped before any Docker
pull, stack reset, model load, or benchmark request because the SSH wrapper's nested `awk`
quoting wrote an empty source-snapshot value. The runner's fail-closed validation correctly
rejected that missing `ISTARA_BENCHMARK_SOURCE_SNAPSHOT_SHA256`; `RUN_STARTED=1` was only a
wrapper marker and no arm was entered. Evidence is retained in the final evidence directory,
with no secret or command line emitted.

Correction: compute the archive digest with a quote-safe `shasum | cut` pipeline, require a
non-empty value before invoking the runner, and capture the runner's non-zero blocker exit
without aborting the wrapper before writing `RUN_RC`. This remains one final comparison attempt;
the failed preflight is not counted as a live model/ensemble run.
Next: refresh only if this receipt changes the source, then execute the corrected one-run
legacy+Pi comparison and continue the provenance/secret/process-list checks.

### L-166 | 2026-08-26T17:25:00Z | S2-execute | gpt-5-codex | corrected final comparison in flight
Did: The corrected invocation is running exactly one legacy+Pi comparison from detached source
`765a85e0df148a515fdee81cc2d2cd192f06f1a9`. The archive snapshot is non-empty and recorded in
the remote evidence directory before launch; the runner has entered Compose stack recreation.
The boolean-only passive process check reports `PASSWORD_ARG_PRESENT=0` while
`RUNNER_ACTIVE=1`, confirming the new env-file path does not expose credential aliases in the
host command line. No command line or secret value was emitted.

Current output shows provider-stub/postgres/backend startup for the first arm; this is only
operational progress and not evidence of model calls, donor routes, ensemble coding, or
Research Spine acceptance. The wrapper captures a blocker-bearing runner exit without masking
the final `RUN_RC`.
Next: poll the same invocation to completion, capture per-arm metadata and a post-run boolean
secret check, then append the exact live disposition and authorized teardown receipt.

### L-167 | 2026-08-26T17:30:00Z | S2-execute | gpt-5-codex | legacy arm blocked; Pi arm still running
Did: The one corrected comparison progressed through the isolated legacy arm and recreated a
fresh stack for Pi. The legacy arm completed its marathon companion and probe, then recorded a
blocker-bearing exit (`exit=1`) as expected under the current live provider configuration; the
runner continued to Pi without launching a second comparison. The Pi marathon is active. A
boolean-only process check continues to report `PASSWORD_ARG_PRESENT=0`; no secret-bearing
command line has been printed.

This checkpoint is operational only. It does not infer model quality from the legacy blocker or
from marathon completion; per-arm run metadata and Research Spine fields remain pending until the
Pi probe exits. The same run group, source commit, image IDs, and Docker-only boundary remain in
force.
Next: wait for the Pi probe to finish, inspect both arm artifacts for source/secret provenance,
record the final blocker disposition, and then perform the authorized testing-stack teardown.

### L-168 | 2026-08-26T17:40:00Z | S3-review | gpt-5-codex | final Docker retake disposition and Research Spine blocker confirmed
Did: The corrected one-run comparison completed with both arms blocker-bearing (`RUN_RC=1`):
legacy run `2026-08-26T14-47-00-658Z` and Pi run `2026-08-26T14-50-11-279Z`. Both run metadata
files record source commit `765a85e0df148a515fdee81cc2d2cd192f06f1a9`, snapshot
`e2dc76611ff6c70971489d8f774058a884ecfa09be5bde114c9ca11e67ff0a1f`,
`container_only=true`, and `host_dependencies_installed=false`. The post-run boolean process
check reports `PASSWORD_ARG_PRESENT=0` and `RUNNER_ACTIVE=0`; the final log SHA is recorded in
the remote evidence bundle.

Behavioral disposition is unchanged and now independently re-confirmed: both scorecards are
`43.5`, with zero chat turns, zero completed tasks, `coding_validation_verified=false`,
`compute_donation_verified=false`, `multi_donor_compute_verified=false`, and blocked coding
(`rater_count=0`, `distinct_model_count=0`, `kappa=null`, `alpha=null`, `code_application_count=0`).
The provider returned 402 Insufficient Balance; the provider-stub was healthy but not an LLM
substitute. The topology fixture reports one weak donor endpoint contract while Research Spine
served routes remain zero, so this run cannot establish PI Model Management, Petals donation,
three-model ensemble behavior, Fleiss/alpha reliability, reconciliation, or human-approved
promotion. This is a blocker disposition, not a quality score.

### L-169 | 2026-08-26T17:45:00Z | S4-ship | gpt-5-codex | authorized Docker cleanup complete; remaining work is implementation plus provider handoff
Did: Before cleanup, Compose reported healthy backend, frontend, postgres, provider-stub, and
Caddy services from the exact testing project. With the owner's explicit authorization, ran
`docker compose --project-name istara-testing ... down -v --remove-orphans` and removed the
dedicated `istara-pw-browsers` runner volume. Evidence confirms zero `istara-testing` project
containers and zero project volumes remain. Unrelated workloads were not targeted. The dirty
owner checkout and disposable clean worktree were not deleted or reset beyond the clean
worktree's exact source refresh.

The transport branch is still intended to remain clean and equal to `origin/testing`; the
external audit ledger now includes F-R9-26 through F-R9-28. Remaining in-repo work is the
scorecard semantic separation/regression fixture for the donor and Research Spine flags. The
remaining live work is external-state dependent: an authorized reachable model provider and a
Compose-owned three-donor/Pi-managed route topology are required before a terminal positive
Research Spine run can produce non-null reliability metrics and accepted downstream lineage.
Next: finish the bounded scorecard contract change through Compass Forge/TDD, then commit/push
the ledger and code; do not claim goal completion until the provider/donor acceptance gates are
actually exercised or explicitly closed by owner decision.

### L-170 | 2026-08-26T18:00:00Z | S2-execute | gpt-5-codex | scorecard semantics separated and gated
Did: Applied the bounded scorecard contract fix in `tests/real_user_benchmark/lib/scoring.mjs`,
`tests/real_user_benchmark/lib/scoring.test.mjs`, and `tests/real_user_benchmark/run.mjs`. The
scorecard now exposes separate fields for the weak donor endpoint contract,
`research_spine_structure_present`, accepted `research_spine_validation_verified`, and
`research_spine_donor_routes_verified`; the legacy traceability field remains a structural
presence alias for compatibility. Added a regression fixture proving that structural traceability
and a one-endpoint topology contract cannot be reported as accepted three-model Research Spine
validation. TDD red first showed two missing-field failures; the targeted suite then passed 8/8.
Compass Forge `gate before` record 64 accepted the change as a baseline with no new comparison
deltas (only inherited repository warnings remain). This is a contract/reporting correction, not
live model evidence; the Docker provider/donor blocker remains open.
Next: commit and push this checkpoint, run the full deterministic JavaScript/Python/docs matrix,
then capture Compass Forge `gate after` evidence and reconcile `testing` with `origin/testing`.

### L-171 | 2026-08-26T18:03:00Z | S3-review | gpt-5-codex | deterministic matrix green after scorecard correction
Did: The full benchmark-library JavaScript suite passed `48/48`. The repository’s scoped
deterministic Python matrix passed `923` tests with `5` skips in `149.30s`; no new failure or
security-contract regression appeared. The passing tests cover PI Model Management migration and
settings, Petals bridge contracts, Research Spine end-to-end/gating/reports, two-call and long
horizon benchmark behavior, three-model coding and reliability gates, runner provenance, Docker
isolation, marathon integrity, and the security benchmark. These are local deterministic
contracts only and do not substitute for the blocked live provider/donor acceptance run.
Next: run feature-doc generation/check and shell syntax validation, then use Compass Forge
`gate after`, commit/push all intended changes, and verify local `testing` equals `origin/testing`.

### L-172 | 2026-08-26T18:05:00Z | S4-ship | gpt-5-codex | after-gate passed comparison with inherited repository debt
Did: Feature-doc validation passed (`seeded 0`, `generated 224`, `86` feature checks),
`bash -n scripts/runner/docker-run.sh` passed, and `git diff --check` passed. Compass Forge
`gate after` record 65 completed with `comparison.new_issues=[]`, zero file/large-file deltas,
and no new forbidden dependencies, import cycles, missing paths, or unexpected large files.
The overall current gate remains `fail` only because the repository’s pre-existing complexity,
security-taint, type-drift, and other warnings/failures are inherited; this scorecard diff adds
no comparison delta. The generated feature manifest timestamp is the only generated-doc change.
Next: append the bounded finding disposition to the external audit file, commit the five intended
repository files, push `testing`, and prove local/remote ref and worktree cleanliness.

### L-173 | 2026-08-26T18:08:00Z | S4-ship | gpt-5-codex | testing branch reconciled and stale CI worktree removed
Did: Committed the scorecard/reporting correction, generated feature manifest timestamp, and
ledger checkpoints as `f98a87c04b6d82ae10e0bc64fd8e8893ab01db41` (`test: separate research spine
scorecard gates`) and pushed it to `origin/testing`. Local `testing` and `origin/testing` resolve
to the exact same SHA, `git diff origin/testing --` is empty, and the tracked worktree is clean.
Removed only the clean detached `/private/tmp/opencode/ci-wt` worktree after verifying it had no
working changes, no attached branch, no process holding the path, and an Aug-24 stale checkout.
Preserved the explicit recovery worktree `recovery/pi-retake-linearized-2026-08-10` and the
owner-managed dirty Mac Studio checkout. The external audit file remains intentionally outside
Git and contains F-R9-29 plus the still-open live provider/donor blocker.
Next: no further local code change is justified without an authorized reachable model provider
and three Compose-owned donor routes; resume from this ledger when those external gates are ready.

### L-174 | 2026-08-26T18:10:00Z | S4-ship | gpt-5-codex | audit dispositions reconciled for runner mitigations
Did: Corrected the external audit’s stale “pending retest” wording for F-R9-24/F-R9-25 with a
new F-R9-30 disposition. The retained final Docker evidence proves the post-fix process-list
check (`PASSWORD_ARG_PRESENT=0`, `RUNNER_ACTIVE=0`) and both-arm source commit/snapshot
provenance (`PROVENANCE_OK=true`, `container_only=True`, `host_dependencies_installed=False`).
The historical credential exposure remains a rotation recommendation before non-test reuse; no
owner-managed `.env.deploy` file was changed. This is documentation reconciliation only and does
not alter the still-open provider/three-donor Research Spine acceptance gate.
Next: hold the goal open for the external provider and donor topology handoff; no further local
mutation is warranted until those inputs are available.

### L-175 | 2026-08-26T18:20:00Z | S2-execute | gpt-5-codex | Pi authority and promotion seam audit in progress
Did: Re-entered the implementation audit after the scorecard/runner closure. Compass Forge
impact/why context and direct code tracing confirm that `run_independent_coding_run` routes
both loop choices through `_use_pi_coding_plane`/`_select_pi_coders`, and `_pi_coder_runner`
dispatches `validity.coder` with an exact Pi endpoint. `PiModelManager.resolve_distinct` folds
model identities case-insensitively, excludes same-model replicas, and applies project scope
to Petals projections. Downstream report eligibility is stricter than the reliability score:
`_is_reconciled_code_application` requires both accepted promotion and durable reconciliation,
and report generation additionally requires approved Done-task state.

Still under review: the broad production `_load_units` query is deterministic by source/unit
but does not itself require multiple source identities; this is not a Research Spine contract
violation for a legitimately single-source study, but it must not be mistaken for the
benchmark's source-diversity proof. I am comparing the existing end-to-end and migration tests
before changing this boundary. No live provider/donor state has changed and no new Docker run
is justified while the reachable provider and three donor routes remain absent.
Next: finish the source-selection and engine-authority test audit, then either add a narrowly
scoped regression/fix or record why the current behavior is intentional; checkpoint evidence
before any long test or commit.

### L-176 | 2026-08-26T18:35:00Z | S2-execute | gpt-5-codex | Pi endpoint PUT parity and case-folded ensemble identity fixed
Did: Added shared `_prepare_pi_endpoint_payload` and `_custody_pi_endpoint_credentials` paths in
`backend/app/api/routes/settings.py`. POST and PUT now share canonical provider/model catalog
resolution, sparse-update inheritance, HTTPS/loopback and Keychain-reference validation, API-key
custody, and OAuth credential preservation/replacement rules. Invalid updates are validated before
the in-memory endpoint is replaced. Added catalog-route regression coverage for derived capability
refresh, replacement-key custody, atomic invalid-update rejection, and a legacy donor-selector
regression proving case variants (`Model-A`/`model-a`) cannot fabricate independent raters; the
selector now stores normalized case-folded identities. Focused suites passed `15/15`.
Updated the settings living feature docs to describe the shared authority and sparse-update contract.
This is deterministic contract evidence only; the live provider/three-donor Research Spine gate
remains open and no host installation or Docker workload was started.
Next: run the broader deterministic settings/Research Spine/PI matrix and feature-doc generation,
then Compass Forge gate-before/after, commit/push `testing`, and record the external blocker.

### L-177 | 2026-08-26T18:55:00Z | S3-review | gpt-5-codex | complexity remediation and OAuth-preservation regression green
Did: Compass Forge gate-before record 69 showed no new comparison issues after the policy was
isolated into `backend/app/core/pi_runtime/endpoint_policy.py`; the prior route/helper complexity
delta is gone. The module separates catalog application, endpoint validation, API-key custody, and
OAuth custody, including typed 503 handling for encryption/provider failures. Ruff is clean and the
focused route/Pi/ensemble suites pass `23/23` (including sparse OAuth update preservation). The
benchmark-library syntax and semantic suite remains green at `58/58`, and feature-doc generation
will be rerun after this module reference is finalized. No live provider request or host install was
performed; Docker remains the only permitted Mac Studio execution boundary.
Next: regenerate/check feature docs, run the final after-gate and diff checks, then commit/push the
intended testing changes and verify exact local/remote refs and clean worktrees.

### L-178 | 2026-08-26T19:10:00Z | S4-ship | gpt-5-codex | Pi authority fix shipped and refs reconciled
Did: Re-ran feature-doc generation/check (`seeded 0`, `generated 224`, `86` checks), benchmark
library tests (`58/58`), focused Python route/ensemble tests (`23/23`), and the broader deterministic
Pi/Research Spine/W7 matrix (`81 passed`). Compass Forge after-gate record 70 reports no new
comparison issues, forbidden dependencies, import cycles, missing paths, or unexpected large files;
the overall fail remains inherited repository debt. Committed the shared Pi endpoint write policy,
catalog/credential parity tests, case-folded donor identity guard, living docs, generated manifests,
and ledger as `cf8f7e2b5f3f1bf52c706e4f62aaef380e8ef8e4`, pushed to `origin/testing`, and verified
local `testing` and `origin/testing` resolve to that exact SHA with an empty diff. Only the
intentional recovery worktree remains; the stale detached CI worktree was previously removed safely.
The external audit file contains F-R9-31 and the still-open live provider/three-donor blocker.
No host Mac Studio installation or non-Docker execution was performed.
Next: keep the implementation goal open for the terminal Docker retake. It requires an owner-
authorized reachable model provider and three distinct, healthy, project-scoped Compose donor routes;
until those are supplied, report deterministic contract evidence as green but do not claim ensemble,
Fleiss/alpha, Petals donation, reconciliation, human-approved Done, or report acceptance.

### L-179 | 2026-08-26T19:34:00Z | S2-execute | gpt-5-codex | Mac Studio runtime rechecked; external gate still absent
Did: Performed a passive SSH inspection of the authorized Mac Studio without installing or
starting anything on the host. The default SSH shell PATH does not expose Docker, so Docker
must be invoked through `/Applications/Docker.app/Contents/Resources/bin/docker` (the pinned
Docker Desktop CLI is present). The only running container is the unrelated `plex` workload;
the Istara testing Compose project has no running containers or volumes. The owner-managed
`~/istara-testing` checkout remains dirty and 90 commits behind `origin/testing`; it was not
reset, cleaned, or mutated. Its deploy config exposes only a model-name key in the redacted
inventory, with no evidence of a reachable provider credential or three donor routes. The
clean detached retake checkout remains at the previous source and must not be treated as a
new acceptance run. This confirms the Docker-only boundary and preserves the honest state:
local deterministic contracts are green, but live model calls, three independent coders,
Fleiss/Krippendorff reliability, reconciliation, human-approved Done, report eligibility, and
Petals donation remain unverified.
Evidence: SSH command at 2026-08-26T19:33Z; Docker Desktop server `29.7.2`; `docker ps` showed
only `plex`; testing checkout was dirty/behind; no secret values were printed or changed.
Next: wait for owner-provided reachable provider credentials and three healthy, Compose-owned,
project-scoped donor routes. Then refresh a clean detached checkout to the reconciled testing
SHA and run exactly one terminal Docker-only retake, preserving hashes, logs, scorecard, and
Compass Forge gate evidence.

### L-180 | 2026-08-26T20:05:00Z | S2-execute | gpt-5-codex | Docker runner donation gate and nested CLI contract repaired
Did: TDD red first added two static runner-contract checks, which failed because
`scripts/runner/docker-run.sh` hard-coded `ISTARA_BENCHMARK_REQUIRE_COMPUTE_DONATION=0` and the
Node runner had no Docker CLI/socket contract for the donor/model/relay containers started by
`tests/real_user_benchmark/run.mjs`. Implemented a disposable `scripts/runner/Dockerfile`
(Node 20 Bookworm plus the Linux `docker.io` CLI), defaulted the wrapper to build that image,
and retained an explicit `ISTARA_RUNNER_IMAGE` override only for compatible images. The wrapper
now defaults compute donation to `1`, defaults client sandboxes to that requirement, validates
boolean inputs, requires the Docker socket when nested sandboxes are enabled, preflights
`docker info` through the socket, and fails closed before any engine arm if the image/daemon
contract is missing. It forwards all namespaced `ISTARA_BENCHMARK_*` topology/profile/connection
inputs through the mode-600 transient env file, with explicit opt-in names for donor API-key
environment variables; secrets remain out of Docker argv. It also resolves Docker Desktop's
standard Mac Studio CLI path without installing host packages. README guidance now documents the
boundary and the explicit offline-control exception. The contract suite passes `15/15`,
`bash -n scripts/runner/docker-run.sh` passes, and `git diff --check` passes. No Docker daemon
or live model was started locally; no Mac Studio host installation occurred.
Next: run the broader deterministic benchmark/Research Spine matrix and Compass Forge before/after
gates for this runner change, append the external audit disposition, then commit/push the exact
testing refs. A terminal Mac Studio run still requires the owner-authorized provider credential
and three healthy Compose-owned donor routes; this local fix makes their absence fail honestly
instead of silently bypassing compute donation.

### L-181 | 2026-08-26T15:52:00Z | S3-review | gpt-5-codex | deterministic matrix and after-gate green
Did: Ran the bounded Python matrix covering Pi production/migration, Petals, Pi benchmark,
chat, Research Spine validity/end-to-end/report gates, findings/tasks, settings and agent
selection, replacement candidates, harness configuration, remote runner contracts, marathon
integrity, and the security benchmark. Result: `927 passed, 5 skipped in 148.77s (0:02:28)` with
no failures or warnings. The count is higher than the prior `923` because the two new runner
contracts are included. Ran `npm run check` in `tests/real_user_benchmark`: `58` tests passed,
including the three-model coding, Fleiss/Krippendorff, donor-route, reconciliation, long-horizon,
Docker-only, provenance, and blocker-oracle contracts. Feature validation passed with
`seeded 0`, `generated 224`, and `86` feature checks; `bash -n scripts/runner/docker-run.sh`
and `git diff --check` also passed.

Compass Forge native `gate after` record `73` reports `comparison.new_issues=[]`, zero file and
large-file deltas, and no new forbidden dependencies, import cycles, missing paths, unexpected
large files, security findings, or taint findings. The overall current gate remains affected by
inherited repository complexity, route/type drift, and secret-flow warnings; this change adds no
comparison delta. No Docker daemon, model/provider call, SSH mutation, or host package install
was performed locally. The external audit now contains F-R9-32 for the prior silent donation
disable/nested-Docker gap and its local remediation.
Next: commit and push the six intended repository files (`scripts/runner/Dockerfile`, runner
wrapper, runner contract test, real-user README, generated feature manifest, and this ledger),
verify exact `testing`/`origin/testing` parity, then remain at the live acceptance gate until the
owner supplies one authorized reachable provider credential and three healthy Compose-owned donor
routes. Only then refresh the clean Mac Studio checkout and run one terminal Docker-only retake.

### L-182 | 2026-08-26T15:53:00Z | S4-ship | gpt-5-codex | runner checkpoint transported and refs reconciled
Did: Committed the six intended runner/doc/test files as `93a738c8702cdb86dbf97e0f9ff9c265384104c9`
(`test: enforce Docker compute-donation runner contract`) and pushed non-forced to
`origin/testing` (`dba5186c..93a738c8`). After fetch, local `testing` and `origin/testing`
resolve to the exact same SHA and `git diff origin/testing --exit-code` is empty. The main
checkout is clean. The only remaining worktree is the intentionally preserved recovery checkout
`/Users/user/Documents/Codex/2026-08-10/list/work/istara-pi-linearized-2026-08-10` on
`recovery/pi-retake-linearized-2026-08-10`; the stale detached CI worktree had already been
removed safely. No branches were deleted because the remaining refs are backups, review lines,
or active recovery history without a demonstrated merged/unused disposition.

Result: local deterministic implementation and evidence are now transported cleanly to
`origin/testing`. The external audit file `/Users/user/Desktop/testing.md` remains intentionally
outside Git and contains F-R9-32. Mac Studio live acceptance is still not run: the owner-managed
checkout is dirty/behind and no authorized provider credential or three donor routes are present.
No host package installation or non-Docker runtime occurred.
Next: obtain the explicit provider/donor handoff; then refresh only a clean detached checkout to
`93a738c8`, provision disposable Docker/Compose resources, execute exactly one terminal retake,
and append source hashes, donor route identities, Fleiss/Krippendorff metrics, reconciliation and
human-approval evidence (or fail-closed blocker evidence) before any Research Spine conclusion.

### L-183 | 2026-08-26T15:56:00Z | S2-execute/S4-ship | gpt-5-codex | Mac Studio Docker hygiene and gate separation finding
Did: Performed a narrowly scoped passive Docker inspection over SSH using the explicit Docker
Desktop binary `/Applications/Docker.app/Contents/Resources/bin/docker`. The `istara-testing`
Compose label returned no stopped/running containers, volumes, or networks, so there was no
testing resource to delete; the unrelated `plex` workload was not touched. This honors the
Docker-only boundary and the owner’s cleanup authorization without mutating the dirty
`~/istara-testing` checkout or installing anything on the Mac Studio host.

Audit update: appended F-R9-33 to `/Users/user/Desktop/testing.md`, identifying an acceptance-
profile ambiguity: the benchmark defaults compute donation as a prerequisite, while the Research
Spine contract defines validity through three provider-plane model routes, source-grounded coding,
Fleiss/Krippendorff reliability, reconciliation, and human approval. The remaining plan must
test provider-only Research Spine validity, Petals donation interoperability, and their combined
Docker profile as independent scorecard gates; donation telemetry must not substitute for model
coding evidence, and a provider-only coding proof must not be blocked merely because Petals is
disabled unless the combined profile is explicitly selected.

Next: preserve the clean `testing`/`origin/testing` parity at the current shipped tip, then await the owner’s
explicit provider/donor handoff. The terminal run must configure one authorized provider plane
with three distinct served model routes and three project-scoped donation routes (or record
fail-closed blockers), execute both engine selections through PI Model Management, and capture
route IDs, atomic code applications, Fleiss/kappa, Krippendorff/alpha, reconciliation, human
approval, Petals consent/health/revoke, and cleanup evidence from Docker only.

### L-184 | 2026-08-26T16:10:00Z | S2-execute | gpt-5-codex | provider/Petals/combined acceptance profiles implemented
Did: Added an explicit `provider`, `petals`, or `combined` acceptance profile to the real-user
benchmark. `scoreRun` now emits an `acceptance_gates` object with independent selected/status/
verified fields for provider-plane Research Spine validity, Petals donation interoperability,
and their conjunction. Markdown scorecards include the same table; `not_selected` and `not_run`
are distinct from `blocked` and `verified`. The runner defaults provider-only runs to coding
validation without donation and Petals-only/combined runs to donation, while explicit diagnostic
overrides remain visible in the gate status. The Docker wrapper validates and forwards the
profile and no longer forces donation for a provider-only run.

Tests first failed because `acceptanceGateStatus` did not exist (expected red phase), then passed
after implementation. Focused scoring tests pass `11/11`; Docker wrapper contract tests pass
`15/15`; `node --check tests/real_user_benchmark/run.mjs`, JSON parsing, `bash -n`, and
`git diff --check` pass. Plan-only runs for all three profiles generated scorecards showing the
expected independent gate states without starting services or loading models. `/Users/user/Desktop/testing.md`
now contains F-R9-34 documenting deterministic closure and the still-open live evidence gate.

Still open: run the broader deterministic matrix and Compass Forge before/after gate, commit and
push the five intended profile files plus this ledger, then obtain owner-authorized reachable
provider credentials and three Compose-owned donor routes for the terminal Docker-only retake.
The live run must exercise both Istara and PI engine selections through PI Model Management,
demonstrate three independent source-grounded coders with Fleiss/Krippendorff metrics,
reconciliation and human approval, separately demonstrate Petals slash-string consent/health/
revoke and project-scoped usage, and only then claim the combined ensemble gate.

### L-185 | 2026-08-26T16:20:00Z | S3-review | gpt-5-codex | deterministic acceptance-profile gates green
Did: Ran the full bounded deterministic matrix after the profile change: `927 passed, 5 skipped`
in `149.78s`. The real-user benchmark `npm run check` passed `61/61`, including the new
provider/Petals/combined scorecard fixtures, three-model Research Spine coding/reliability/
reconciliation contracts, Docker-only refusal and provenance checks. The static Docker runner
contract passed `15/15`; `bash -n scripts/runner/docker-run.sh`, Node syntax checks, registry
JSON parsing, and `git diff --check` passed. Feature docs regenerated with `seeded 0`, `generated
224`, and `86` checks passing.

Compass Forge native `gate after` record `75` reports `comparison.new_issues=[]`, zero file and
large-file deltas, and no new forbidden dependencies, Python import cycles, missing paths,
unexpected large files, security findings, or taint findings. The current gate still reports the
same inherited complexity/route-type/secret-flow warnings; no new warning was introduced by this
change. Plan-only profile probes generated provider, Petals, and combined scorecards without
starting any service or model. `/Users/user/Desktop/testing.md` now contains F-R9-34 recording
deterministic closure of F-R9-33 and the live evidence blocker.

Next: commit and push the exact profile/runner/docs/test files, verify local `testing` equals
`origin/testing`, then remain blocked only on the owner-authorized reachable provider credential
and three Compose-owned donor routes needed for the terminal Mac Studio Docker-only retake.

### L-186 | 2026-08-26T16:24:00Z | S4-ship | gpt-5-codex | acceptance-profile checkpoint transported
Did: Committed the nine intended profile/runner/docs/test files as `dfcda6e72605d894affcecae4b6852bdd4c9783e`
(`test: separate provider and Petals acceptance gates`) and pushed non-forced to `origin/testing`
(`479af052..dfcda6e7`). After fetch, `testing` and `origin/testing` resolve to the exact same SHA;
`git diff origin/testing --exit-code` is empty and `git status --short --branch` is clean. No
external audit file was staged; `/Users/user/Desktop/testing.md` remains the owner-facing findings
record with F-R9-34.

Result: the deterministic acceptance contract and its Docker-only transport are now available on
the remote testing branch. Live claims remain intentionally withheld. The next agent should not
redo local implementation or delete the intentional recovery worktree; it should collect the
owner-authorized provider/API-key environment mapping and three Compose-owned donor routes, refresh
the Mac Studio checkout from `dfcda6e7`, and execute the bounded terminal retake with both engine
arms and the provider/Petals/combined profiles.

### L-187 | 2026-08-26T20:40:30Z | S2-execute/S3-review | gpt-5-codex | Research Spine source gate, engine sharing, and profile fail-closed audit

Did: Corrected the benchmark's false three-document reliability prerequisite. Research Spine
reliability is over raw evidence units rated by independent model identities; a single source
may provide multiple substantive spans. The probe now records source diversity but does not use
`expectedDistinctSources=3` as an acceptance blocker. Added a deterministic one-source,
multi-span fixture with four grounded units, three coders, numeric Fleiss/Krippendorff metrics,
complete reconciliation, and accepted promotion. Added a W1 characterization that creates one
real `PiModelManager` plus one `PiExecutionService` and invokes both `legacy` and `pi` dispatcher
choices, asserting the same three manager-owned endpoint/model identities. Added a separate W7
characterization that uses the real `PiModelManager.resolve_distinct` selection path and checks
three raters, the configured reliability method, exact endpoint/model pinning, and route
provenance. Added profile wiring assertions and made selected provider/Petals/combined gates
fail closed when callers explicitly disable the selected validation plane. Updated the living
ensemble architecture, benchmark README, and Docker wrapper comments so source diversity,
provider validity, and Petals interoperability are not conflated. Appended F-R9-35 through
F-R9-40 to `/Users/user/Desktop/testing.md`.

Evidence: `npm run check` in `tests/real_user_benchmark` passed `65/65`; W1 ensemble focus
passed `3/3`; the real-manager W7 characterization passed `1/1`; the full bounded Python
matrix passed `929 passed, 5 skipped in 274.03s`; `npm run plan` completed credential-free;
`git diff --check`, `bash -n scripts/runner/docker-run.sh`, registry JSON parsing, and
`python scripts/feature_docs.py --seed-missing --generate-site --check` passed (`seeded 0`,
`generated 224`, `86` feature checks). Compass Forge native gate-before record `76` and
gate-after records `77`/`78` remain repository-wide `fail` only because of inherited
complexity/route/type/secret-flow debt; no new forbidden dependency, import cycle, missing
path, security, taint, or large-file delta was introduced. The warning naming
`tests/pi_production/test_w7_validation.py` at 1044 lines/85 symbols is not caused by this
working tree (`git diff --quiet --` is true); it is retained as a Compass Forge baseline/index
follow-up rather than hidden. No live model request, host installation, or Mac Studio mutation
occurred.

Open decisions: (1) inject a request-scoped Pi manager/service through coding selection and
dispatch to close the time-of-check/time-of-use gap (F-R9-38); (2) split provider-only,
Petals-only, and combined workload execution so unrelated chat/task/UI failures do not blur
gate status (F-R9-39); (3) obtain the owner-authorized provider credential and three healthy,
project-scoped Compose donor routes for live acceptance (F-R9-40). Do not claim ensemble,
Fleiss/alpha, Petals, human-approved Done, or report acceptance from these deterministic
fixtures.

### L-188 | 2026-08-26T20:40:30Z | S2-plan | gpt-5-codex | Terminal completion blueprint for the next agent

This is the resumable work order. Keep this section current after every bounded stage; record
the command, result, artifact path, commit SHA, and blocker status in a new ledger entry.

#### A. Reconcile source and execution boundaries

1. Confirm `testing` is clean and exactly equal to `origin/testing` before opening the live
   gate. Record `git status --short --branch`, both SHA values, and `git diff origin/testing`.
2. Refresh only a clean detached/worktree checkout to that SHA on the Mac Studio. Do not
   reset or clean the owner-managed `~/istara-testing` checkout without a separately explicit
   authorization. Never install Python, Node, Playwright, model runtimes, or package managers
   on the host.
3. Build/pull the disposable runner through Docker, verify the runner image digest, backend/
   frontend image IDs, Compose project name, source snapshot SHA-256, and a fresh Postgres
   state. Preserve these in each arm's `run-metadata.json` and provenance artifact.
4. Before any model call, prove the runner's Linux Docker CLI reaches the Docker Desktop
   socket (`docker info`), the application containers are healthy, and the runner is attached
   only to the intended Compose networks. If any prerequisite is absent, stop that arm and
   retain the fail-closed artifact.

#### B. Prove PI Model Management is the sole provider authority

1. Through `/api/settings/pi-endpoints` (and only its canonical POST/PUT/delete/OAuth paths),
   register or resolve three provider endpoints with distinct `endpoint_id`, served model
   identity, provider-account handle, and immutable route evidence. Do not use the deprecated
   classical endpoint as a write path; confirm its intentional `410` response.
2. Validate that sparse PUTs preserve omitted fields, catalog-derived protocol/capabilities,
   OAuth custody, and Keychain references; reject invalid URLs/credentials atomically. Capture
   redacted management responses and endpoint catalog snapshots without emitting secrets.
3. Confirm Petals slash-string donations enter the same manager catalog as project-scoped
   read-only donor routes, with explicit consent, health, source, project scope, and revoke
   state. Donor aliases must not be counted as distinct model identities.
4. Run one controlled endpoint mutation between coder selection and dispatch. The currently
   open F-R9-38 should fail closed once a selected endpoint is removed or materially changed;
   until that guard exists, label this scenario unverified rather than passing it.

#### C. Exercise both engine choices through the shared manager

1. Run isolated `legacy` and `pi` arms against the same source snapshot and equivalent
   configuration. The legacy arm may preserve its Python ReAct orchestration, but every model,
   credential, retry, usage, and ensemble request must resolve through the injected Pi service.
2. For each arm, capture the selected engine header/project setting, dispatcher purpose,
   endpoint ID, model identity, provider account, route evidence ID, usage delta, stop reason,
   tool calls, and fallback/repair events. A canned provider-stub response or a transport 200
   without a useful body is not a successful model turn.
3. Compare a bounded two-call and long-horizon task in both arms. Require non-empty grounded
   answers, tool/continuation behavior where requested, completion within the configured
   horizon, and no silent fallback to Ollama/classical routing. Record timeout/recovery and
   server-side completion separately from client transport status.

#### D. Execute the Research Spine acceptance gate

1. Upload raw interview/document material and record source IDs, exact source spans, evidence
   unit IDs, stable locations, and content hashes. Do not seed nugget prose or synthetic
   findings as evidence.
2. Select exactly three independent model identities through PI Model Management. Require all
   three coders to receive the same evidence-unit set and fresh coder scope; record prompt/code-
   book versions, model checkpoints, provider accounts, endpoint IDs, decoding profile, and
   cache scope.
3. Validate every atomic application against its raw quote and evidence unit. Require complete
   unit coverage, no fabricated quotes, no missing coder, and no duplicate identity hidden by
   endpoint aliases.
4. Require numeric Fleiss' kappa plus the configured Krippendorff-alpha companion (method name
   alone is insufficient), preserve the thresholds and input matrix, and record disagreements.
5. Require reconciliation decisions for each disagreement, then a human-reviewed/approved
   transition through Done before counting Facts, Insights, Recommendations, Findings, or
   Reports as accepted. Keep blocked, provisional, synthetic, low-confidence, and transport-
   recovered artifacts visibly non-accepted.
6. Verify the scorecard distinguishes structural traceability, donor topology, accepted
   Research Spine validation, and report eligibility. No structural flag may imply live model
   agreement when coder count, metrics, or route count is zero.

#### E. Execute Petals interoperability separately and together

1. Provider profile: run only the minimum source upload/coding/reliability/reconciliation/
   approval path and require the provider gate; donation may be not-selected, never silently
   disabled.
2. Petals profile: generate slash strings, obtain explicit consent, register healthy project-
   scoped relays, pass technical served probes, show usage on the intended project, revoke
   consent, and prove cleanup. This profile must never report Research Spine validity.
3. Combined profile: run both evidence planes in one isolated Compose invocation and require
   the conjunction. Preserve separate gate statuses (`verified`, `blocked`, `not_run`,
   `not_selected`) and a final combined status.
4. Repeat the combined profile for both `legacy` and `pi` engine arms, then compare route and
   usage evidence. One engine's successful donation must not satisfy the other's coding gate.

#### F. Test the test harness itself

1. Run the static and deterministic suites from the repository's Docker runner; retain the
   exact command output and avoid interpreting faux/stubbed tests as model-quality evidence.
2. Confirm profile defaults, explicit-disable blockers, source-span sampling, three-model
   identity checks, metric-oracle thresholds, route provenance, long-horizon assertions, and
   Docker-only refusal are all covered by regression fixtures.
3. Add a mutation test for manager catalog drift, a test for one-source/multiple-span proof,
   and a negative fixture where a provider stub returns healthy HTTP but zero useful model
   outputs. The latter must block acceptance and preserve a truthful scorecard.
4. Re-run Compass Forge impact/why for every production file changed, regenerate living
   feature docs, run gate-before/after, and attach command/gate/review evidence before task
   acceptance. Keep inherited gate debt separate from new regressions.

#### G. Ship, clean, and close honestly

1. Stage only intended repository files. Do not stage `/Users/user/Desktop/testing.md`, model
   artifacts under `LLMs/` or `Model_Finetuning/`, secrets, generated runtime results, or
   owner-managed worktree changes.
2. Commit with a focused message, push non-force to `origin/testing`, fetch, and verify exact
   local/remote SHA equality plus an empty diff. Record the commit in this ledger.
3. Inspect worktrees/branches read-only. Delete only a worktree or branch proven merged,
   detached, unused, and not an intentional recovery/backup line; never infer safety from a
   remote backup alone. Dispose only testing Docker containers/volumes/networks after logs,
   scorecards, and hashes are copied to the evidence folder; never touch unrelated workloads.
4. If provider credentials, donors, Docker socket, or a required approval are missing, leave
   the goal open with a precise blocker and the exact next command. Do not claim completion,
   model quality, ensemble bias reduction, or Research Spine acceptance from local green
tests alone.

### L-189 | 2026-08-26T20:49:19Z | S3-review | gpt-5-codex | exact-tree regression retake green

Did: Re-ran the full bounded deterministic matrix after isolating the real-manager test into
its own module. The exact tree passes `929 passed, 5 skipped in 277.50s (0:04:37)`. The
real-user benchmark library remains green at `65/65`; focused W1 ensemble coverage is `3/3`
and the isolated real-manager W7 characterization is `1/1`. No production service, provider,
or model was started. The remaining work is transport/reconciliation plus the external live
acceptance gate described in L-188.

Next: review the complete staged diff, run final syntax/diff/feature checks, commit and push
to `origin/testing`, fetch and verify exact SHA equality, inspect worktrees/branches read-only,
and append the transported SHA. Keep `/Users/user/Desktop/testing.md` outside Git; it contains
F-R9-35 through F-R9-40 and the owner-facing live blocker.

### L-190 | 2026-08-26T20:53:39Z | S3-execute | gpt-5-codex | testing transport parity verified

Did: Committed the complete intended 13-file testing/documentation change set as
`f705bebb0acb4b04ccb6c9c2e1a3295b3f8dd00f` with message
`test: harden Research Spine ensemble acceptance contract`. Pushed non-force to
`origin/testing`, fetched the branch, and verified `HEAD` equals `origin/testing` at
the same SHA with an empty diff. The working tree is clean except for ignored artifacts;
`/Users/user/Desktop/testing.md` remains intentionally outside Git.

Evidence: `git fetch origin testing`; `git rev-parse HEAD` and
`git rev-parse origin/testing` both returned `f705bebb0acb4b04ccb6c9c2e1a3295b3f8dd00f`;
`git diff --exit-code origin/testing --` passed; `git status --short --branch` reported
`## testing...origin/testing` with no file changes.

Next: inspect worktrees and branches read-only, preserving the intentional recovery
worktree and any unmerged/backup refs. Then obtain the owner-authorized live inputs and
run the terminal acceptance matrix only through the Mac Studio's Docker/Compose runner.
No live model/provider call, donor registration, or Mac Studio execution is claimed by
this checkpoint; deterministic green tests do not prove ensemble quality or Research
Spine acceptance.

### L-191 | 2026-08-26T20:56:41Z | S3-gate | gpt-5-codex | Compass Forge after-gate recorded

Did: Ran the pinned native Rust Compass Forge `gate after` on the transported testing
tree. Gate record `79` was written with runtime `rust`, `recorded_as_baseline: false`, and
no new forbidden dependencies, import cycles, missing paths, unexpected large files, or
security issues. The repository-wide gate remains `fail` because of inherited complexity,
route-drift, type-drift, and secret-flow debt; the only `comparison.new_issues` item is the
pre-existing warning for `tests/pi_production/test_w7_validation.py` (1044 lines, 85
symbols), which is byte-identical to the baseline and was not changed by this work.

Next: keep the external live gate open. The terminal retake still requires owner-authorized
provider credentials, three distinct Compose-owned donor routes, and the Mac Studio Docker
runner/socket. Run provider, Petals, combined, legacy, and pi profiles only there; preserve
raw source-span, three-rater, Fleiss' kappa/Krippendorff-alpha, reconciliation, human-Done,
route, usage, long-horizon, and cleanup evidence before any acceptance claim.

### L-192 | 2026-08-26T21:24:00Z | S3-remediate | gpt-5-codex | close runner portability and deterministic-suite blockers

Did: Reproduced the Mac Studio provider-profile abort caused by the empty optional
`NESTED_DOCKER_MOUNTS` expansion under macOS Bash `set -u`, then added a red/green wrapper
regression contract and refactored the outer script to build a fixed `runner_docker_args` array,
appending nested socket mounts only when present. The change preserves Docker-only execution and
keeps the runner compatible with both provider-only (no nested socket) and donor-enabled paths.
The full local matrix exposed two stale/infrastructure failures unrelated to model quality: the
fresh SQLite test expected migration `031_embedding_profiles` while the current chain correctly
ends at `032_pi_tool_executions`, and public-repo quality rejected a historical absolute checkout
path in a tracked plan. Both assertions/docs now use the current migration head and a neutral
`<repo-root>` marker. It also exposed a global websocket notification task being gathered from a
prior pytest event loop; `drain_notification_tasks` now cancels/discards foreign-loop tasks and
only gathers tasks owned by the active loop, with a regression test.

Evidence: the new wrapper regression was red before the script change and is green afterward;
`pytest -q tests/test_remote_benchmark_runner_contract.py` is `16 passed`, shell syntax and
`git diff --check` pass, and focused checks for the websocket drain, fresh migration, and public
quality audit are green. The first complete matrix before these remediations was `1990 passed,
6 skipped, 3 failed`; the three failures were the stale head, tracked-path audit, and
cross-event-loop drain error described above. No local service, provider, donor, or model was
started. The external audit file records F-R9-41 and remains intentionally outside Git.

Next: rerun the complete deterministic matrix after these remediations, run the JavaScript and
feature-doc checks, execute the pinned Compass Forge after-gate, commit/push only the intended
repository files, then refresh the clean Mac Studio checkout and retake the provider profile
through Docker before attempting any donor-dependent profile. Keep the live acceptance gate open
unless all required source, three-rater, reliability, reconciliation, human-Done, route, usage,
long-horizon, and cleanup artifacts are actually present.

### L-195 | 2026-08-26T22:09:15Z | S2-execute/S3-review | gpt-5-codex | Mac Studio provider retake completed and blocked at provider credit

Did: Refreshed the clean detached Mac Studio checkout to `973731cf03a4cf2d762574e32421e23eaf8ce162`
and verified the exact `git archive` source snapshot SHA-256
`f3f2f7de3decd1ba248ccbad70c10913f850c60f55de9709be1baf250b4f0b2c`. The corrected
`scripts/runner/docker-run.sh` ran both declared arms from the Docker-only topology with
`ISTARA_BENCHMARK_ACCEPTANCE_PROFILE=provider`, no donor sandboxes, and a fresh Postgres stack
per arm. Chromium/FFmpeg and Linux dependencies were installed only inside the disposable
runner image/volume; the Mac Studio host was not package-modified.

Result: the runner exited `1` because both arms were blocker-bearing, not because the wrapper
crashed. Legacy run `2026-08-26T22-04-08-235Z` scored `43.5`, stopped at its first chat call with
provider HTTP `402 Insufficient Balance`, and recorded `0/8` chat turns, `0` approvals, and
`0` accepted code applications. PI run `2026-08-26T22-06-53-478Z` scored `43.5` and reached
the same provider boundary as `pi_runtime_error` wrapping the same `402`, with the same zero
chat/approval/code-application counts. Both run artifacts recorded three selected raw evidence
units but a blocked/blocked coding run; no rater outputs, model identities, Fleiss' kappa,
Krippendorff-alpha, grounding, reconciliation, human-Done, or report-eligibility evidence was
produced. This proves the portability fix and that legacy/PI requests reach the configured
provider boundary; it does not prove PI Model Management/legacy manager identity sharing or the
three-model Research Spine ensemble.

Evidence retained on the Mac Studio under
`~/istara-testing-evidence-20260826T220200Z/` and the two run directories under the clean
checkout's `.results/runs/`. The boolean process-list check reported `PASSWORD_ARG_PRESENT=0`.
Authorized teardown removed only the `istara-testing` Compose containers, networks, runtime
volume, and `istara-pw-browsers`; the unrelated `plex` container remained healthy. F-R9-43
records the provider-credit blocker and the remaining live ensemble gate.

Next: obtain owner-authorized provider credit or provision three distinct Compose-owned model
routes, then run the profile-specific Petals and combined acceptance workloads. Do not convert
this provider retake into a model-quality score or Research Spine acceptance claim.

### L-194 | 2026-08-26T21:59:30Z | S3-gate | gpt-5-codex | Compass Forge after-gate recorded

Did: Ran the pinned native Rust Compass Forge `gate after` on the post-verification tree. Gate
record `81` reports no new forbidden dependencies, import cycles, missing paths, unexpected large
files, security issues, or taint issues. The repository-wide status remains `fail` because of
existing complexity, route-drift, type-drift, and secret-flow debt. The comparison surfaced the
existing `_resolve_project_id` complexity warning in the touched websocket file; the function was
not changed by this patch (only notification-task draining was), so this is a pre-existing debt
made visible by the file-level comparison, not a regression from the fix. It is retained as an
explicit follow-up rather than silently claiming a clean gate.

Next: commit/push the seven intended files only, verify exact local/remote SHA parity, then
perform the provider-only Mac Studio Docker retake. Preserve the live Research Spine gate until
the required three-model and Petals evidence is available.

### L-193 | 2026-08-26T21:57:36Z | S3-verify | gpt-5-codex | deterministic retake and documentation gates green

Did: Completed the post-remediation deterministic verification. The full Python matrix is
`1994 passed, 6 skipped, 1 warning in 543.89s (0:09:03)`. The warning is an SQLAlchemy
`SAWarning` during `tests/test_tasks.py::test_agent_execute_task_defers_when_project_paused`
about garbage collection of a non-checked-in connection; it does not fail the suite, but it is
recorded as test-lifecycle debt rather than hidden. The real-user benchmark JavaScript suite is
`65/65` with zero failures, and `npm run plan` confirms no live services were attempted. The
feature documentation contract passes: `seeded 0`, `generated 224`, `feature docs check passed
for 86 feature(s)`. `git diff --check` also passes.

This green deterministic evidence proves only local contracts, fixtures, routing assertions, and
faux/stub characterization. It does not prove that three independent live models analyze the same
raw evidence units, that Fleiss' kappa/Krippendorff-alpha and grounding are calculated from those
raters, that PI Model Management and the legacy arm share the same request-scoped authority, or
that Petals donation routes interoperate on the Mac Studio. Those remain external Docker-only
acceptance gates. F-R9-42 records the residual connection-cleanup warning.

Next: run the pinned native Compass Forge after-gate on this exact tree, commit and push the
intended testing files, verify local/remote SHA parity, then retake the provider profile from the
clean Mac Studio checkout through Docker. Do not claim the three-model Research Spine gate until
the live run contains immutable source/image/stack evidence, three distinct model identities,
raw-span coding, numeric reliability/grounding, reconciliation, human-Done, route/usage,
long-horizon, and cleanup artifacts.

### L-196 | 2026-08-26T22:11:00Z | S3-gate | gpt-5-codex | final ledger gate recorded

Did: Ran the pinned native Rust Compass Forge `gate after` once more after the live evidence
checkpoint. Gate record `82` reports zero new forbidden dependencies, import cycles, missing
required paths, security issues, or taint issues. The repository-wide gate remains `fail` on
inherited complexity, route/type drift, and secret-flow debt; one comparison warning remains the
pre-existing `_resolve_project_id` complexity finding in the touched websocket file, which is
unchanged by this work. `git diff --check` passes and the only remaining local modification is
this ledger entry, ready to commit and push.

Next: commit this final ledger checkpoint, push `testing`, verify exact SHA parity and a clean
worktree, then leave the live three-model/Petals/combined gate explicitly open pending provider
credit and three distinct Compose-owned donor routes.

### L-197 | 2026-08-26T22:23:42Z | S2-execute/S3-verify | gpt-5-codex | shared Pi authority closed

Did: Implemented the remaining production seam identified in F-R9-38. `AgenticDispatcher`
now exposes its engine-owned `PiModelManager`; the default Research Spine coding run passes
that exact manager into `_select_pi_coders` before `_pi_coder_runner` invokes the same global
dispatcher for `validity.coder`. Direct selector callers and test doubles without the accessor
retain the compatibility seam, while production no longer constructs a second manager between
identity selection and structured dispatch. Updated the Ensemble Health architecture page and
generated site artifact to state this authority invariant.

Evidence: `pytest -q tests/pi_production/test_w1_dispatcher_authority.py
tests/pi_production/test_w7_validation.py tests/test_research_spine_donor_routing.py` returned
`61 passed in 2.98s`; the new manager-identity integration assertion and the real Pi manager
characterization both pass. `python scripts/feature_docs.py --seed-missing --generate-site
--check` returned `seeded 0`, `generated 224`, and `feature docs check passed for 86 feature(s)`.
No live provider or model was started; the Mac Studio 402 gate remains unchanged.

Next: run the pinned Compass Forge after-gate, append the corresponding testing.md finding,
commit and push the focused implementation/docs/tests, then verify exact local/remote SHA
parity. The live three-model/Petals/combined acceptance gate remains open pending provider
credit and three distinct Compose-owned donor routes.

### L-198 | 2026-08-26T22:25:32Z | S3-ship | gpt-5-codex | shared-authority fix transported

Did: Committed and pushed the shared Pi authority implementation, its W1/W7 regression
coverage, Ensemble Health living documentation, and generated feature page as
`816f1ebf2e3797a3e0985ae5fb5354bac3b16660` (`fix: share Pi authority with research coding`).
The pinned native Rust Compass Forge after-gate is record `84`: no new forbidden dependencies,
import cycles, missing paths, security issues, or taint issues; the repository-wide gate remains
failed only on inherited complexity/route/type/secret-flow debt, including the now-touched large
Research Spine service and W7 test file. The external `/Users/user/Desktop/testing.md` ledger
now contains F-R9-44 documenting the closed manager split and the still-open live gate.

Evidence: `git push origin testing`, `git fetch origin testing`, equal `git rev-parse HEAD`
and `git rev-parse origin/testing`, `git diff --exit-code origin/testing --`, and
`git status --short --branch` returned a clean `testing...origin/testing` checkout. Focused
tests and feature-doc checks are recorded in L-197. No live model/provider call or host install
was performed.

Next: preserve the live acceptance blocker until owner-authorized provider credit and three
Compose-owned donor routes exist; then run the Docker-only Mac Studio provider, Petals, combined,
legacy, and PI profiles and attach complete three-rater/reliability/reconciliation/human-Done
evidence. The local authority TOCTOU finding is fixed and does not by itself prove live ensemble
quality.

### L-199 | 2026-08-26T22:26:11Z | S3-gate | gpt-5-codex | post-transport gate checkpoint

Did: Re-ran the pinned native Rust Compass Forge after-gate against the exact pushed tree. Gate
record `87` remains repository-wide `fail` only because the baseline already contains complexity,
route/type drift, and secret-flow debt; the touched Research Spine service and W7 test file
continue to surface their pre-existing size/complexity warnings. The comparison reports no new
forbidden dependencies, Python import cycles, missing required paths, unexpected large files,
security issues, or taint issues.

Evidence: local `testing` and `origin/testing` remain equal at `631ed8d8`, with no diff and no
uncommitted files after the ledger update is transported. The focused W1/W7/donor suite and
feature-doc verification remain the authoritative checks in L-197; the Mac Studio Docker retake
remains the provider-HTTP-402 external blocker in F-R9-43. No host package install or live model
load was performed.

Next: resume only when owner-authorized provider credit and three Compose-owned donor routes are
available. Use the exact pushed SHA and preserve raw source-span, three-rater, numeric Fleiss /
Krippendorff, grounding, reconciliation, human-Done, route/usage, long-horizon, and cleanup
artifacts before any Research Spine or ensemble acceptance claim.

### L-200 | 2026-08-26T22:27:31Z | S3-acceptance | gpt-5-codex | CF-24 evidence and task closure

Did: Attached Compass Forge evidence to CF-24 for the focused W1/W7/donor test run, feature-doc
generation/check, after-gate record `87`, and the manager-authority review. `finish-task CF-24`
accepted the task with four evidence records and status `done`. CF-SPEC-4 remains `tasked` with
its validation/acceptance tasks open; it is not represented as fully accepted while the live
provider/Petals/combined gates remain unresolved.

Evidence: Compass Forge `task evidence-list CF-24` shows evidence IDs 11–14, and
`finish-task CF-24` returned `evidence_count: 4`, `status: done`. The code transport remains
clean at pushed SHA `5b7811f65a018e77fae08309bddb0f4f98cf2610` on both `testing` and
`origin/testing`; task-state recording does not alter the Git tree.

Next: keep CF-SPEC-4 open until the remaining live validation tasks have Docker-only Mac Studio
evidence: three genuinely distinct served model identities, shared raw evidence units,
Fleiss/Krippendorff metrics, grounding, reconciliation, human-approved Done, route/usage,
long-horizon, Petals donation, and cleanup. Do not mark the specification accepted from these
local deterministic checks.

### L-201 | 2026-08-26T22:31:00Z | S3-gate/S3-ship | gpt-5-codex | catalog-drift fix transported and checked

Did: Verified the catalog-identity fail-closed implementation is transported cleanly as
`92a291d48a3a8ea5fb78009696ad47aa07c6e907` on both local `testing` and `origin/testing`.
The production Research Spine Pi coder now reuses the dispatcher-owned manager, refreshes its
dynamic projection, compares the selected non-secret endpoint/model/provider/account identity
against the execution-time catalog, and rejects drift before any structured provider call.
The focused W1/W7/real-manager/donor/drift suite remains green at `63 passed`; feature-doc
generation/check remains green for 86 features. Compass Forge after-gate record `91` reports no
new forbidden dependencies, import cycles, missing required paths, security issues, or taint
issues. The repository-wide gate still reports inherited complexity, route/type, and secret-flow
debt; these are not silently reclassified as fixed.

Evidence: `git fetch origin testing`, equal `git rev-parse HEAD`/`origin/testing`,
`git diff --exit-code origin/testing --`, and `git status --short --branch` show a clean,
parity-verified checkout. No Mac Studio host package install, host Python/Node execution, or live
model load was performed by this checkpoint. The live Docker acceptance remains blocked at the
provider boundary: both corrected legacy and PI runs reached the provider and received HTTP 402
Insufficient Balance before any model produced a coding response. Therefore the run still has no
three independent model identities, rater labels, Fleiss' kappa/Krippendorff-alpha, grounding,
reconciliation, human-approved Done, report, long-horizon, or Petals interoperability evidence.

Next: when owner-authorized provider credit and three distinct Compose-owned donor routes are
available, run the exact pushed SHA through Docker-only Mac Studio provider, legacy, PI, combined,
and Petals profiles. Preserve immutable source/image/Compose evidence, prove distinct served model
identities and shared raw evidence units, assert nonzero rater/reliability/grounding/reconciliation
artifacts, exercise long-horizon/two-call behavior and the accepted/report gates, then tear down
only testing resources. Until that evidence exists, the ensemble and Research Spine live gates
remain open despite the deterministic local tests being green.

### L-204 | 2026-08-26T23:30:00Z | S3-gate/S3-review | gpt-5-codex | final local acceptance slice is attributable-clean

Did: Ran the pinned native Rust Compass Forge `gate before` (record `94`) and `gate after`
(record `95`) against the profile-isolation, scorecard, connection-revocation, and test-fixture
changes. Both comparisons report `new_issues=[]`, zero file/large-file deltas, no new forbidden
dependencies, Python import cycles, missing paths, security findings, or taint findings. The
overall repository gate remains failed only on inherited complexity, route/type drift, and
secret-flow findings already present in the baseline; those are not reclassified as caused by
this slice.

The final deterministic checks are green: JavaScript benchmark/document/topology checks `70/70`,
remote runner contracts `16 passed`, shell syntax, feature-doc generation/check (`seeded 0`,
`generated 224`, `86 feature(s)`), focused websocket/task warnings-as-errors `34/34`, and full
Python strict matrix `1997 passed, 6 skipped` with no `RuntimeWarning` failures. A vacuous empty
donor list is now explicitly `not_selected`/unverified for provider-only runs, preventing a
Petals endpoint field from masquerading as evidence.

Next: commit only the intended repository files, push non-forced to `origin/testing`, verify
exact local/remote SHA parity and a clean worktree, and preserve the external Mac Studio gate.
The live provider/three-model/Petals acceptance still needs owner-authorized provider credit or
three reachable Compose-owned routes; until then no model identity, rater labels, Fleiss or
Krippendorff metrics, grounding, reconciliation, human-Done/report, two-call/long-horizon, or
Petals interoperability claim is valid.

### L-202 | 2026-08-26T23:20:00Z | S2-execute/S3-review | gpt-5-codex | benchmark profiles now isolate their executable workload planes

Did: Converted `provider`, `petals`, and `combined` from scorecard labels into explicit
workload contracts in `tests/real_user_benchmark/lib/scoring.mjs` and `run.mjs`. Provider
selects raw-corpus plus source-grounded three-rater coding/reliability/reconciliation/
promotion checks without donation or unrelated chat/task/UI/marathon work; Petals selects
slash-string donation, consent, health, technical probe, usage, revoke, and cleanup without
claiming provider validity; combined selects both planes plus the shared chat/task controls.
The wrapper and inside runner now derive profile-specific live-chat/marathon defaults, and
generated benchmark connection strings are revoked at teardown. Scorecards carry immutable
workload scope, selected/not-selected/verified gate state, unrelated workflow failures, and
credential-revocation metadata so a skipped plane cannot be mistaken for a passing one.

Evidence: `npm --prefix tests/real_user_benchmark run check` is `70/70`; the topology contract
suite is `8/8`; shell syntax, remote-runner contract (`16 passed`), and feature documentation
generation/check (`seeded 0`, `generated 224`, `86 feature(s)`) are green. Deterministic
profile fixtures cover positive provider-only and Petals-only runs plus combined negative
gates. These checks prove workload isolation and reporting semantics only; they do not create
live model/rater outputs or close the Mac Studio provider/three-donor gate.

Next: transport this profile contract through the clean `testing` checkout, then execute each
selected profile on Mac Studio Docker with immutable source/image/Compose evidence. Keep
provider, Petals, and combined acceptance independent while comparing legacy and PI arms.

### L-203 | 2026-08-26T23:26:33Z | S3-verify | gpt-5-codex | full deterministic suite is warning-clean after websocket task drain

Did: The first post-remediation full Python matrix was green but emitted one SQLAlchemy
connection/session lifecycle warning when a global websocket notification task outlived a
pytest event loop. The warning was a test-harness teardown race, not an ensemble or provider
failure: `ConnectionManager.broadcast` tracks background persistence tasks, while the
autouse `dispose_db_engine` fixture disposed the shared async engine before draining them.
The fixture now awaits `manager.drain_notification_tasks()` before telemetry drain and engine
disposal. This keeps same-loop tasks awaited and removes the cross-test loop boundary that
left `AsyncSession.close` unawaited.

Evidence: focused websocket/task tests pass `34/34` with `PYTHONTRACEMALLOC=1` and
`-W error::RuntimeWarning`; the complete strict matrix passes `1997 passed, 6 skipped in
701.01s (0:11:41)` with zero warnings promoted to errors. No service, provider, model, or
Mac Studio host package was started by this deterministic check. The repository-wide
Compass Forge gate remains subject to inherited complexity/route/type/secret-flow debt;
no new forbidden dependency, cycle, missing path, security, or taint issue was introduced.

Next: run the pinned Compass Forge after-gate on the final tree, commit only the intended
runner/profile/docs/fixture files, push non-forced to `origin/testing`, and verify exact SHA
parity. The live gate remains open until a Docker-only Mac Studio run produces three distinct
served model identities, common raw evidence units, numeric Fleiss/Krippendorff reliability,
grounding, reconciliation, human-approved Done/report evidence, two-call/long-horizon
artifacts, Petals donation interoperability, and teardown proof.
