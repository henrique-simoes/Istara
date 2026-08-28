# Agentic-Core Integrity & Core-Capable QA — Build Stream lifecycle

```yaml
item: agentic-core-integrity-and-qa
branch: testing
cf: { spec: CF-SPEC-2, predecessor: CF-SPEC-1, task: CF-15 }
phase: "Phase 9 — completion blueprint, branch reconciliation, and terminal acceptance"
stage: S2-execute/S3-review
status: in-progress
blocked_on: "Owner-approved Docker-only Mac Studio provisioning: current env/config, provider-served identities, and three-model inputs; provider profile ran but served zero distinct PI models"
last: { agent: gpt-5-codex, at: 2026-08-28T01:53:29Z, ledger: L-460, commit: 0ff30925 }
next_action: "Provision or explicitly supply the required provider-served three-model inputs inside Docker only, then run provider, Petals, and combined profiles with two-call/long-horizon enabled; keep live three-model, Fleiss/alpha, reconciliation, and Done/report gates open until terminal receipts exist."
```

## Continuation blueprint — remaining work and acceptance contract

This section is the resumable work order for the next agent. It supersedes the
original Phase 1 diagnosis where a later ledger entry says that a defect has
already been fixed. It does not turn deterministic fakes into live scientific
evidence, and it does not authorize model loading or host installation. Every
step below must leave a command, gate, or review row in Compass Forge and a
timestamped ledger entry in this file.

### Current truth and non-claims

* `testing` tracks `origin/testing` and the checkout is kept clean. Re-run
  `git rev-parse HEAD` and `git rev-parse origin/testing` at the start of every
  continuation because each ledger-only commit necessarily advances both tips.
  The last observed equal tips before this amendment were `f849f267`; there is
  no `local/testing` ref. Do not create a local ref merely to make the names
  symmetrical; record the absence instead.
* The only other worktree is the clean recovery branch
  `recovery/pi-retake-linearized-2026-08-10`. It is not merged into `testing`
  (`testing...recovery/...` is `863 113`) and must not be deleted or rebased as
  cleanup. Delete branches/worktrees only after an explicit ancestry, owner, and
  artifact check proves they are unused and merged.
* The deterministic contract slices currently pass (latest targeted slice:
  `425 passed, 0 failed, 5 skipped`; the benchmark contract is `100 passed`).
  These results establish routing, rejection, accounting, and harness behavior
  with fakes/fixtures. They do **not** prove that three independent live models
  served the same research source, that Fleiss' kappa was meaningful, or that a
  human promoted a reconciled result.
* Passive SSH inspection found Docker Desktop on the Mac Studio, but no Istara
  testing stack running (only an unrelated `plex` container and the
  `pi-agent-home` volume). The non-interactive SSH PATH did not expose `docker`
  until the absolute Docker Desktop CLI path was used. Treat this as an
  operations/harness finding: all remote commands must use an explicit Docker
  path or a PATH set in the command, and a missing live stack is `not_run`, not
  `passed`.
* The Compass/CF timeline has two distinct axes and must not be collapsed into
  the age of the current SQLite registry. Istara's retained Git history has
  research/ensemble precursors in March: `3308350c` on 2026-03-14 added the
  Kappa thematic-analysis skill, while equivalent current-line commits
  `837ed4fc` (2026-03-17, true dual-coding/codebook/evidence validation) and
  `a1594cf3` (2026-03-24, ensemble validation/compute-pool infrastructure) are
  ancestors of both `refs/heads/testing` and `refs/remotes/origin/testing`.
  The alternate hashes `4ba41a4f` and `9a218603` are retained parallel-history
  copies of those March changes, not the hashes reachable from the current
  testing line. The earliest reachable Compass doctrine in the active Istara
  history is 2026-04-03 (`42e454b0`, `AGENT_ENTRYPOINT.md` defines Compass as
  Istara's comprehensive agentic development system), followed by doctrine
  hardening and the three-layer testing architecture on 2026-04-03 through
  2026-04-10 (`ce19476e`, `16d18228`, `21ef99b1`, `c0ddf50c`). The
  repository's first literal managed `compass-forge:start` block is 2026-05-02
  (`0d0d9a24`); the first tracked literal `CF-SPEC-*` marker is 2026-05-04
  (`7dca7368`). Separately, the standalone Compass Forge project's accepted
  Build Stream roadmap begins 2026-07-02 and its shared state database's oldest
  spec row is 2026-07-03. Therefore the previous statement that CF began in
  July/August was wrong when it referred to Istara's Compass governance or
  integration; July is only the start of the retained standalone CF roadmap/
  registry persistence. No retained CF SQLite database contains an April
  `CF-SPEC` row, and that absence must not be used to backdate or erase the
  April Istara lineage.

### Workstream A — Compass Forge and Build Stream control plane

1. Start with `compass-forge status`, `next`, and one compact `agent-brief`.
   Refresh/index only if staleness is reported. The active recipe is
   `istara-main`; do not silently use the legacy `istararustgraphtrial` label
   from older `AGENTS.md` text.
2. Keep CF-SPEC-2 and CF-15 as the active contract unless Compass Forge shows a
   newer accepted replacement. Inspect CF-13, CF-15, CF-20, and CF-21 before
   claiming completion. Do not create duplicate specs for the same request.
3. For every implementation or test file, run both
   `intelligence impact --path <path> --request ...` and
   `intelligence why <path>` before editing. Use `context --pack-type standard`
   before broad raw reads and record any `incomplete_evidence` warning.
4. Before and after meaningful changes run the CF gates. Attach exact command
   output, review result, feature-doc check, and (when applicable) security
   benchmark output to the task. An inherited gate failure must remain labelled
   inherited; it is not a reason to claim a new change passed.
5. Every two minutes or at each material state transition, append a ledger row
   with: timestamp, agent, phase, commit/working-tree SHA, exact command, result,
   evidence location, blocker, and next action. Update the YAML `last` pointer in
   the same edit when a new row becomes the resumable frontier.

### Workstream B — authoritative Pi routing and engine parity

The acceptance target is that Pi Model Management is the only model/endpoint
authority for all first-class engines, while the engine label still selects the
loop semantics. Verify this as a matrix, not with one happy-path request:

| Surface | Engine labels | Required authority/evidence | Required negative proof |
| --- | --- | --- | --- |
| `/chat` and completion dispatch | `pi`, `legacy`/Istara | `AgenticDispatcher` receives the label; `PiModelManager` resolves the endpoint; route and provider-served model identities are persisted | no `ComputeRegistry` lookup, no QA stub, no silent fallback |
| Agentic Loop and Pi Agentic Loop | both public labels used by the UI/API | same manager/dispatcher path, with distinct loop telemetry and turn budgets | selecting one label cannot execute the other loop |
| structured/coder calls | research-validity phases | exact endpoint, provider, served model, project, purpose, source/evidence handles | missing/contradictory served identity blocks promotion |
| ensemble/full ensemble | self-MoA and three-model mode | `distinct=True`, `minimum_n >= 3`, one route-evidence item per served sample, usage per sample | repeated endpoint IDs or partial responses are degraded/not-runnable |
| embeddings and auxiliary model calls | configured Pi endpoint | manager-owned endpoint and project scope | retired classical endpoint or global unscoped row cannot leak in |
| settings CRUD/catalog | Pi endpoint UI/API | canonical `/api/settings/pi-endpoints` and live catalog invalidation | retired `/settings/model`/`provider` endpoints remain 410 and cannot mutate state |

Use existing W7/W8, engine HTTP, ensemble identity, dispatcher, chat, and
settings tests as the deterministic baseline. Add a regression only where the
matrix is missing: the test must assert the observable route evidence and the
negative condition, not merely that a mock was called.

### Workstream C — provider-plane Research Spine proof

This is the primary scientific gate and remains unverified. It must run in a
fresh, isolated Docker project/database with owner-approved provider inputs.

1. Admit at least three independent provider routes through PiModelManager. Each
   route needs a distinct endpoint identity and a provider-served model identity;
   configured labels alone are insufficient. Capture immutable endpoint/model
   fingerprints without exposing secrets.
2. Feed every coder the same raw source and the same evidence-unit boundaries.
   Evidence units must point to source spans; synthesized nugget prose cannot be
   the input unless exact spans are retained and the artifact remains provisional.
3. Require a complete coder-by-atom matrix. Missing, duplicate, failed, or
   contradictory rows block reliability and cannot be padded with a default code.
4. Compute Fleiss' kappa for three or more raters and retain the companion
   Krippendorff alpha/grounding metrics. A threshold pass is necessary but not
   sufficient: undefined/all-same or low-signal results remain
   `needs_reconciliation`.
5. Persist reconciliation decisions with actor, timestamp, source/evidence
   handles, reason, and before/after labels. Verify that accepted atoms/nuggets
   alone can promote to facts/insights/recommendations; raw model output cannot.
6. Exercise the human gate: an accepted coding run must still leave a task or
   report in review until an authorized human marks Done. Verify that reports,
   recommendations, and design decisions are blocked before that transition and
   carry route/evidence/reliability provenance after it.
7. Repeat with a deliberately bad case (duplicate model IDs, missing served
   identity, partial coder, low kappa, and missing reconciliation) and assert a
   fail-closed outcome for each. These are scientific validity tests, not just
   HTTP error tests.

The final provider evidence packet must contain: run ID and clean image digests,
source hash, evidence-unit manifest, three route receipts, per-coder outputs,
Fleiss/alpha calculation, reconciliation record, human approval record, accepted
artifact IDs, and the exact CF command/evidence rows. Until all are present,
state `live_scientific_acceptance: unverified`.

### Workstream D — Petals donation and simultaneous operation

Petals is a governed donor route, not a substitute for the provider-plane
Research Spine proof. Verify both in one isolated run and keep claims separate:

1. Exercise donation/slash-string management through the canonical Pi endpoint
   management path. Consent must be explicit, project-scoped, revocable, and
   reflected in the manager projection; no donation data may enter a global
   catalog without that scope.
2. Project at least three healthy `pi-petals-*` donor routes with distinct route
   identities. Send served requests through the pinned project endpoint and
   capture donor, model, project, purpose, usage, and consent evidence.
3. Run a full ensemble with `distinct=True` and `minimum_n >= 3`. Confirm that
   the three samples are actually served by distinct admitted routes. Repeated
   route IDs, missing provider/donor receipts, or a downgrade must be recorded as
   `not_runnable`, never as a valid ensemble.
4. Revoke consent and invalidate manager projections. The revoked route must
   disappear from resolution and a subsequent request must fail closed. Verify
   that an already-persisted receipt remains auditable but cannot authorize a new
   call.
5. Run provider and Petals routes concurrently only after each isolated path
   passes alone. Confirm manager cache invalidation prevents stale provider or
   donor endpoints from crossing projects. Report provider-plane reliability and
   Petals transport health as two different claims.

### Workstream E — tool calls, two-call tasks, and long horizons

The benchmark must prove execution semantics, not only text generation:

* A tool-call scenario must show a requested tool, an authorized invocation, a
  tool result, a subsequent model turn, and a terminal outcome. A plain response
  or a mocked tool result is not success.
* A two-call scenario must persist two distinct dispatch receipts linked to one
  task, with independent route/usage metadata and a causal second prompt. One
  call with a long answer does not satisfy it.
* A long-horizon scenario must show multiple bounded turns, persisted state or
  checkpoints, recovery/resume behavior, and a terminal user-visible result.
  Timeout, truncation, or an unobserved background process is incomplete.
* Exercise both `pi` and `legacy`/Istara loop labels through the shared manager.
  Compare semantics and receipts, not raw wording; model-quality claims require
  a separately designed, powered evaluation.
* Preserve crash-safe records and fail-closed budget reservations. Unknown usage,
  missing text, timeouts after dispatch, and ambiguous provider receipts must not
  be converted into zero-cost success.

### Workstream F — benchmark and Docker-only harness hardening

1. Run the deterministic suites in a clean container and locally only when they
   do not load models. Keep the exact Python/Node lockfiles, image digests,
   command, exit code, and test counts.
2. For Mac Studio, SSH is control plane only. Use Docker Desktop's absolute CLI
   path (or an explicit PATH) and run the runner, services, clients, relay, and
   model servers in containers. Never install Python, Node, model runtimes,
   packages, or model files on the host.
3. Use a disposable project/volume/network per run. Start from a clean checkout
   at the pushed SHA, mount only the required source/config, and use an explicit
   teardown. Do not reuse `pi-agent-home`, unrelated containers, or old databases.
4. The benchmark wrapper must return non-zero for setup errors, missing model
   identities, failed gates, or incomplete evidence. `100 passed` means only the
   deterministic package passed; the live profile must emit a separate terminal
   status such as `accepted`, `needs_reconciliation`, `not_runnable`, or `not_run`.
5. Run provider-only, Petals-only, and combined profiles. The combined profile
   is accepted only when both route governance and Research Spine promotion gates
   pass in the same run. Keep warm/cold order and repeated-run variance visible.
6. If no approved endpoint/model inputs are available, stop after passive checks,
   record `blocked_on` with the missing inputs, and do not fabricate a live pass.

### Workstream G — verification and shipping checklist

Before terminal acceptance, the next agent must attach:

* targeted Pi/dispatcher/manager/ensemble/Petals/Research Spine tests;
* `python scripts/feature_docs.py --seed-missing --generate-site --check` for
  behavior or route changes;
* `python scripts/security_benchmark.py --fail-on-threshold` for auth, provider,
  session, webhook, model, or endpoint-management changes;
* Docker-only Mac Studio logs and teardown evidence, with host install audit;
* `compass-forge gate before` and `gate after`, task evidence, and review result;
* `git diff --check`, clean status, commit SHA, and equality of `testing` and
  `origin/testing`; and
* a final ledger row that distinguishes `accepted`, `needs_reconciliation`,
  `not_runnable`, `blocked`, and `not_run` for every profile and every gate.

Do not push, merge, delete a worktree, or call the goal complete while any
required evidence is absent. A clean deterministic suite and a green harness do
not close the live scientific gate.

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

### L-205 | 2026-08-26T23:34:00Z | S4-ship | gpt-5-codex | deterministic slice transported with exact testing parity

Did: Committed the profile-isolated acceptance workloads, scorecard truthfulness guard,
generated connection revocation evidence, websocket async-task teardown fix, living Ensemble
Health documentation, generated site artifacts, and Build Stream checkpoints as
`d9c9d30ac977de633866fbee397a150c22dbfe85` (`test: isolate acceptance profiles and clean async
teardown`). Pushed non-forced to `origin/testing`; fetch plus exact SHA comparison and
`git diff --exit-code origin/testing --` confirm local `testing` and `origin/testing` are equal
and the worktree is clean. The only separate worktree is the intentionally retained clean
`recovery/pi-retake-linearized-2026-08-10`; `git branch --merged testing` contains only
`testing`, so no branch/worktree had a demonstrably safe unused disposition for deletion.

Evidence: final checks in L-204 and the transport verification above. No protected `LLMs/` or
`Model_Finetuning/` artifact was touched or removed, and no Mac Studio host install or live
model load occurred. The external `/Users/user/Desktop/testing.md` ledger now records F-R9-46
through F-R9-48 for profile isolation, lifecycle cleanup, and vacuous donor verification.

Next: the implementation slice is complete locally, but the goal is not complete. Resume only
with owner-authorized reachable provider credit or three Compose-owned model routes. On Mac
Studio, use Docker exclusively and the exact pushed SHA; run provider and Petals profiles
independently, then combined plus legacy/PI arms. Preserve immutable source/image/Compose
metadata and require three distinct served model identities, common raw spans, numeric
Fleiss/Krippendorff reliability, grounding, reconciliation, human-approved Done/report
eligibility, two-call/long-horizon evidence, Petals slash-string consent/health/usage/revoke,
and cleanup before making any Research Spine or ensemble acceptance claim.

### L-206 | 2026-08-26T23:35:42Z | S4-ship | gpt-5-codex | exact pushed SHA corrected for live retake

Did: Corrected the durable `next_action` pointer to the actual clean `testing`/`origin/testing`
tip `b15140a76fb6c9ed8c0d83039677d8625997e51a`; the prior `da803e68` pointer was stale and
could have caused a future Mac Studio run to execute an older snapshot. This is a documentation
only correction; the external provider-credit/three-donor acceptance gate remains open, and no
live model or host installation was started.

Evidence: `git status --short --branch`, exact local/remote SHA parity, and the deterministic
verification records in L-204/L-205. Continue to preserve Docker-only execution and do not treat
the provider HTTP 402 as ensemble or Research Spine evidence.

Next: commit and push this ledger correction, verify parity again, then wait for authorized
provider credit and three Compose-owned donor routes before the terminal live retake.

### L-207 | 2026-08-26T23:40:13Z | S3-acceptance | gpt-5-codex | local fail-closed spec accepted

Did: Attached command evidence to CF-31 and CF-33 through CF-37, finished the locally provable
validation/preservation/evidence/impact/proof tasks, and accepted CF-SPEC-5 in Compass Forge.
The accepted scope is limited to the shared Pi manager and catalog-identity fail-closed seam;
it does not claim live provider, three-model, Petals, or Research Spine acceptance.

Evidence: native Rust Compass Forge `task show`/`finish-task` records report CF-31, CF-32,
CF-33, CF-34, CF-35, CF-36, and CF-37 all `done`; `spec accept CF-SPEC-5` reports status
`accepted`. The focused W1/W7/real-manager/donor/drift suite is recorded as `63 passed` at
the clean transported testing tip `43a598b8e7efd81670a12051d86d9659cf9f86c3`.

Next: keep CF-SPEC-2 and its live acceptance tasks open. The next substantive action remains
the exact pushed-SHA Docker-only Mac Studio provider/Petals/combined retake, but only after
owner-authorized provider credit and three Compose-owned donor routes are reachable.

### L-208 | 2026-08-26T23:42:56Z | S2-execute/S3-review | gpt-5-codex | Mac Studio preflight preserves dirty owner checkout

Did: Performed passive SSH/Docker preflight using the absolute Docker Desktop CLI path. Docker
server `29.7.2` is reachable, but the named `~/istara-testing` checkout is 109 commits behind
`origin/testing` and contains 340 modified/untracked paths, including deployment and secret/TLS
files. No Istara benchmark or donor/provider container is running; only unrelated `plex` is
healthy. The dirty checkout was not pulled, reset, cleaned, or overwritten. Created the isolated
detached worktree `~/istara-testing-retake-47bf` at the exact pushed SHA
`47bfeb4174ced61e64689793b660e78c3d81a9b5` for any future retake.

Evidence: base Compose, QA `contract` profile, and VPS Compose render checks all pass from the
isolated worktree (no services started); no host package was installed and no model was loaded.
The external findings ledger now records F-R9-49. This preflight does not provide provider,
three-rater, reliability, Petals, or Research Spine acceptance evidence.

Next: commit and push this checkpoint, then wait for owner-authorized provider credit and three
Compose-owned donor routes before running the live profiles from the isolated worktree only.

### L-209 | 2026-08-26T23:44:16Z | S3-acceptance | gpt-5-codex | locally provable broader-spec tasks closed

Did: Attached Compass Forge command evidence and finished CF-14, CF-16, CF-17, CF-18, and
CF-19 for the broader CF-SPEC-2 request. These records cover impacted-file/contract review,
unrelated-behavior preservation, verification-ledger recording, architecture gate accounting,
and required Compass Forge relationship inspection. CF-13/CF-15/CF-20/CF-21 remain open because
they require the still-missing live provider, three-model, Petals, and Research Spine outcome
evidence; no acceptance shortcut was taken.

Evidence: native Rust Compass Forge task records show CF-14, CF-16, CF-17, CF-18, and CF-19
`done`, with command evidence IDs 25–29. The implementation tip used by the isolated Mac Studio
worktree is `7f82389c12389bfc0d81a50458a3fe9e0e8bd2a4`; subsequent ledger-only commits must not
be confused with runtime code changes.

Next: commit and push this ledger checkpoint, verify branch parity, and keep the live gate open
until owner-authorized provider credit and three Compose-owned donor routes are available.

### L-210 | 2026-08-26T23:45:31Z | S3-acceptance | gpt-5-codex | duplicate local authority spec reconciled

Did: Attached Compass Forge evidence and finished CF-22, CF-23, and CF-25 through CF-30 for
CF-SPEC-4, then accepted that duplicate narrow authority spec. CF-SPEC-4 now records the local
shared-manager and catalog-drift behavior as complete; this does not promote the missing live
provider, three-model, Petals, or Research Spine evidence.

Evidence: native Rust Compass Forge `spec accept CF-SPEC-4` reports `accepted`; task evidence
IDs 30–37 cover focused `63 passed` regressions, full warning-clean preservation, impact/why/
test-impact graph review, gate accounting, and the all-linked-tasks-done proof. The isolated
Mac Studio retake worktree remains clean at implementation tip `7f82389c12389bfc0d81a50458a3fe9e0e8bd2a4`.

Next: commit and push this checkpoint, verify parity, and keep CF-SPEC-2 live acceptance tasks
open until the Docker-only Mac Studio provider/Petals/combined retake produces the required
three served identities, raw-span coding, reliability, reconciliation, human-Done/report,
two-call/long-horizon, route/usage/revoke, and cleanup artifacts.

### L-211 | 2026-08-27T00:03:10Z | S3-acceptance | gpt-5-codex | CF-SPEC-1 accepted; Pi guard test isolated

Did: Closed the remaining locally provable CF-SPEC-1 bookkeeping. Attached evidence to CF-11
and CF-12, finished CF-6 and CF-11/CF-12, and accepted CF-SPEC-1 in native Rust Compass Forge.
The accepted scope is deterministic agentic-core routing, QA-stub guard behavior, frontend
header wiring, WCAG contrast, and QA-obligation coverage; it does not claim live provider,
three-model ensemble, Petals, long-horizon, reconciliation, or Research Spine acceptance.

Found and fixed a test-configuration defect in `tests/test_chat.py`: the Pi stub-exemption
test had crossed the unit boundary into the real Pi/provider path because registration,
prompt/RAG, and runtime seams were not mocked. The corrected test uses a local Pi-runtime
fake and passes `13/13` under `PYTHONTRACEMALLOC=1 pytest -q -W error::RuntimeWarning
tests/test_chat.py`. External findings now include F-R9-50. Commit `7e475014` is pushed and
`testing` equals `origin/testing` with a clean worktree.

Evidence: Compass Forge task evidence IDs 43–44 and `spec accept CF-SPEC-1` report accepted;
CF gate-after record 97 reports no new dependency, cycle, missing-path, security, or taint
issues (the inherited repository gate remains separate). The exact implementation tip for
the isolated Mac Studio retake remains `7f82389c12389bfc0d81a50458a3fe9e0e8bd2a4`, because
subsequent commits are documentation/test bookkeeping only.

Next: commit and push this ledger checkpoint, verify exact local/remote parity, then wait for
owner-authorized provider credit and three Compose-owned donor routes. Run the terminal Docker-only
provider, Petals, combined, and legacy/PI arms from the isolated clean worktree; require three
served identities, common raw evidence units, numeric Fleiss/Krippendorff metrics, grounding,
reconciliation, human-Done/report eligibility, two-call/long-horizon behavior, Petals consent/
health/usage/revoke evidence, and cleanup before accepting CF-SPEC-2.

### L-212 | 2026-08-27T00:20:39Z | S2-execute/S3-review | gpt-5-codex | Pi ensemble governed-width and partial-result audit

Did: Audited the Pi migration seam against the Research Spine ensemble contract. The validation
facade intentionally requests `min_responses + 1` slots so the legacy executor can use one
optional spare, but `AgenticDispatcher.ensemble(engine="pi")` previously dropped `minimum_n`.
Pi therefore tried to resolve all four slots; a catalog with exactly three distinct model
identities could never execute the intended three-rater ensemble and failed before model calls.
The dispatcher now forwards `minimum_n`, and `PiExecutionService.run_ensemble` resolves the
governed minimum for Pi (which has no spare-retry loop). A second fail-open defect was closed:
when the spare still leaves fewer than the requested valid responses, `validation.full_ensemble`
now downgrades to the explicit `dual_run` path instead of labeling a partial result as a full
ensemble. The living architecture/researcher docs now state that independent raters require
distinct model identities, not merely endpoint IDs, and that response-level consensus is not
formal Fleiss reliability.

Evidence: focused Pi authority/runtime/validation suites pass `74 passed`; benchmark MoA and live
driver contract suites pass `45 passed`; feature docs regeneration/check passes (`224` site
artifacts, `86` feature checks); Compass Forge task CF-15 evidence IDs 46–48 and gate-after
record 98 show no new failures, no actionable failures, and zero contract/generated drift (four
new complexity warnings are recorded as non-blocking). New local coverage proves a real
`PiModelManager -> PiExecutionService` three-identity selection with `n=4, minimum_n=3`, plus
partial-response downgrade behavior. This remains deterministic proof only: the external
Mac Studio provider retake is still blocked by the observed provider HTTP 402 and missing
Compose-owned donor routes, so no live three-model/Fleiss/Petals acceptance claim is made.

Next: commit and push this checkpoint, verify exact local/remote parity, then run the terminal
Docker-only provider/Petals/combined retake from implementation tip `7f82389c12389bfc0d81a50458a3fe9e0e8bd2a4`
when owner-authorized provider credit and three donor routes exist. Add a dedicated multi-model
live benchmark profile before that retake: the current DeepSeek-only profile hard-pins one model
and one approved endpoint, so it can prove route isolation and degradation but cannot prove three
distinct model identities or Fleiss/Krippendorff reliability.

### L-213 | 2026-08-27T00:26:57Z | S2-execute | gpt-5-codex | branch/worktree and Mac Studio retake reconciliation

Did: Reconciled the repository and remote execution surfaces before opening the next benchmark
change. Local `testing` is clean at `3d0b2052352a253200aa388c3d34fe19936f5571` and the exact
tree/ref are equal to `origin/testing`. The only additional worktree is the clean recovery
checkout `/Users/user/Documents/Codex/2026-08-10/list/work/istara-pi-linearized-2026-08-10` at
`4c0ee557095549447e6934ca0f69cee861af220d`; it is not an ancestor of `testing` (113 commits
ahead and 682 behind), so it is retained as a recovery asset. Only `testing` is locally merged;
there are no gone upstreams and `git remote prune origin --dry-run` has no candidates. No branch
or worktree was deleted because no deletion target was demonstrably unused and merged.

The Mac Studio is reachable through the `macstudio` SSH alias with Docker Desktop 29.7.2. The
host inspection changed no packages, started no models, and found no Istara benchmark/provider/
donor containers (only an unrelated healthy `plex` container). The isolated retake checkout
`$HOME/istara-testing-retake-47bf` is clean/detached at `7f82389c12389bfc0d81a50458a3fe9e0e8bd2a4`,
which predates the governed-width fix now on `testing`; it must not be treated as the current
implementation or overwritten in place. The next live attempt therefore requires a new clean
detached checkout at `3d0b2052` and must remain Docker-only.

Open acceptance remains explicit: the current benchmark profile is DeepSeek-only and cannot
prove three distinct model identities, formal Fleiss/Krippendorff reliability, or Petals donor
interoperation. Provider HTTP 402 and absent Compose-owned donor routes remain external gates;
no live Research Spine acceptance claim is made. Before any provider call, add/validate a
fail-closed multi-model profile whose explicit owner-supplied allowlist records three distinct
served model identities, common raw evidence units, reliability metrics, reconciliation, and
human-Done/report eligibility without weakening route authorization or donor isolation.

### L-214 | 2026-08-27T00:40:43Z | S2-execute | gpt-5-codex | fail-closed MoA model-identity oracle

Did: Audited the benchmark-side MoA verdict against the Research Spine contract and found that
endpoint diversity alone could be reported as a clean full ensemble. `tests/pi_benchmark/moa.py`
now derives served model identities only from successful route evidence, records their distinct
count, and degrades a full ensemble as `model_identity_collapse` when identities are missing or
duplicated. Every benchmark MoA evidence object explicitly marks `formal_reliability=false` and
`research_spine_eligible=false`: response consensus is not Fleiss' kappa or Krippendorff alpha,
and cannot promote reportable research without the governed coding/reconciliation/Done path.

Added regression coverage for three endpoint replicas of one model and for missing model
identity, while preserving the clean three-route control. Updated the benchmark README to make
the independent-model gate and the boundary between deterministic response consensus and formal
Research Spine reliability explicit. The full local `tests/pi_benchmark/` package is the next
verification gate; no provider call, model load, host package operation, or Mac Studio mutation
was performed. This change is intentionally local/provable and does not claim live three-model
acceptance: the current live profile still pins DeepSeek and the last Mac Studio run stopped at
provider HTTP 402 before any coder/rater output.

Next: run focused and full benchmark tests plus feature-doc generation/check, attach Compass
Forge gate evidence, commit/push the benchmark/oracle/ledger files plus the generated feature-site
manifest, verify exact `testing`/`origin/testing` parity, and materialize a new clean detached Mac
Studio checkout at the pushed implementation tip without touching the stale recovery checkout.

### L-215 | 2026-08-27T00:47:02Z | S2-execute | gpt-5-codex | local oracle checkpoint pushed

Did: Attached Compass Forge command evidence 49 for the focused/full `tests/pi_benchmark` suites,
feature-doc generation/check, and whitespace validation. Attached gate evidence 50 (before) and
51 (after): both remain `status=fail` solely because the repository's inherited gate debt reports
31 failures/208 warnings, while `new_failures=0`, `new_issue_count=0`, and
`actionable_failures=[]`; contract/generated/GraphQL drift stayed zero. Committed the fail-closed
model-identity oracle, its endpoint-replica and missing-identity regressions, the explicit
consensus-versus-formal-reliability README boundary, this ledger, and the generated feature-site
manifest as `80f973e6` (`test: fail closed on collapsed ensemble model identity`).

Pushed `testing` to `origin/testing` and verified exact commit/tree parity; the local worktree is
clean. No provider request, model load, host package install, or Mac Studio mutation occurred.
The stale isolated Mac Studio checkout at `7f82389c...` and the unrelated recovery worktree remain
untouched. The live gate is still open: provider HTTP 402 and absent Compose-owned donor routes
prevent any claim that three independent models, Fleiss/alpha, Petals interoperation, or accepted
Research Spine artifacts have run.

Next: create a new clean detached Mac Studio checkout at `80f973e6`, inspect only Docker/Compose
status and passive configuration, and do not start models or services. Keep the provider/Petals/
combined acceptance retake pending until owner-authorized credit and three approved donor/model
routes are supplied.

### L-216 | 2026-08-27T00:50:34Z | S2-execute | gpt-5-codex | Mac Studio clean-tip materialization

Did: On the Mac Studio, fetched `origin/testing` and created the new detached worktree
`/Users/user/istara-testing-retake-57c7cae7` at exact SHA
`57c7cae714be508d3238fd453c3e298f8e5811f2`. The checkout is clean (`## HEAD (no branch)`) and
contains the new fail-closed oracle markers. Passive Docker inspection used the Docker Desktop CLI
at `/Applications/Docker.app/Contents/Resources/bin/docker`; server version is `29.7.2`, the only
running container is unrelated healthy `plex`, and only default Docker networks plus existing
opaque volumes/`pi-agent-home` are present. The first passive command confirmed the host shell has
no `rg`; it was corrected to `grep` without installing anything. No image pull, container start,
model load, host package operation, volume deletion, or service mutation occurred.

This proves branch/worktree freshness and Docker availability only. It does not satisfy the live
provider/Petals/combined gate: provider HTTP 402 still needs owner-authorized credit, and no three
Compose-owned donor/model routes are registered. The stale `7f82389c...` checkout and recovery
worktree remain preserved. Next live action is therefore conditional and Docker-only: configure
the approved three-model topology in the new checkout, run the provider, Petals, and combined
profiles, and retain raw route/model identity, Fleiss/alpha, reconciliation, and accepted-Done
evidence before any Research Spine success claim.

### L-217 | 2026-08-27T00:59:48Z | S2-execute/S3-review | gpt-5-codex | request-scoped Pi authority pairing

Did: Closed the remaining F-R9-38 seam in governed Research Spine coding. The dispatcher now
exposes its engine-owned `PiExecutionService` alongside `model_manager()`. The coding-run
orchestrator obtains that single service/manager pair, selects distinct model identities from
the paired manager snapshot, and forwards the same service into every
`structured(purpose="validity.coder")` call. Dispatcher usage-ledger accounting remains the
single accounting boundary. The selector now fails closed when a supplied service has no
manager or is paired with a different manager, preventing catalog selection and provider
dispatch from silently diverging. Endpoint identity and provider-reported endpoint drift
checks remain enforced.

Did: Corrected the living Research Spine documentation. The architecture contract now records
request-scoped service/manager pairing and fail-closed mismatch behavior. The Findings Codebook
architecture and researcher docs now state that model identity—not endpoint identity—is the
independence unit; same-model endpoint replicas are not independent raters, while endpoint
identity remains route provenance. Generated feature-site artifacts were regenerated.

Evidence: TDD red/green pairing regression (the unpaired-service test first failed because no
`ValueError` was raised, then passed after the guard); Compass Forge command evidence 53 covers
the first focused suite/docs run, 54 covers `tests/pi_benchmark`, and 56 records the final
red/green and verification summary. Final local verification: focused production/Research
Spine suite `92 passed`; full `tests/pi_benchmark` suite `231 passed, 5 skipped`; feature docs
check passed for 86 features with 224 generated site artifacts; `git diff --check` passed.
Compass Forge gate evidence 57/58 (after record 104) remains `status=fail` from inherited
repository debt (`31` failures, `209` warnings, `3` security findings), with
`new_failures=0`, `actionable_failures=[]`, and contract/generated/GraphQL drift all zero;
five touched-file complexity warnings are non-blocking. No provider request, model load, host
package operation, or Mac Studio mutation occurred.

Open gate: this is deterministic proof of authority pairing and contract behavior only. The
Mac Studio live acceptance still cannot claim three independent served models, Fleiss'
Kappa/Krippendorff's Alpha, grounding/reconciliation/Done/report promotion, two-call or
long-horizon behavior, or Petals interoperability. The provider previously returned HTTP 402,
the current live profile is DeepSeek-only, and no three Compose-owned donor/model routes are
registered. The isolated clean Mac Studio checkout at `57c7cae7` remains the safe retake base;
the stale checkout and recovery worktree remain preserved.

### L-218 | 2026-08-27T01:00:43Z | S2-execute/S3-review | gpt-5-codex | clean push and parity checkpoint

Did: Committed the request-scoped Pi authority pairing, fail-closed mismatch guard, Research
Spine contract corrections, focused regression coverage, generated feature artifacts, and this
ledger as `c0c60ef8` (`fix: pair research spine coding with pi service authority`). Pushed
`testing` to `origin/testing`; Compass Forge command evidence 59 records exact commit/ref/tree
parity and a clean local worktree. No old worktree or branch was deleted: the only recovery
checkout is not merged/ancestral and remains a retained safety asset.

Acceptance state is unchanged: local deterministic behavior is verified, but Mac Studio Docker
live acceptance remains open pending provider credit and three Compose-owned donor/model routes.

### L-219 | 2026-08-27T01:05:37Z | S2-execute/S3-review | gpt-5-codex | failure-cause and final-tip reconciliation

Did: Reconciled the user-visible failure question against the latest implementation and
execution evidence. The live Mac Studio campaign did not fail because Fleiss' kappa,
Krippendorff's alpha, reconciliation, or the Research Spine rejected model output: both the
legacy and PI arms reached the configured provider boundary and received HTTP `402
Insufficient Balance` before any model response, coder/rater label, or evidence-unit output
existed. The live profile was also DeepSeek-only and had no three Compose-owned donor/model
routes, so even an HTTP `200` from that profile could not prove three independent model
identities or formal reliability.

Cause of the earlier local failures was the Pi authority migration. The validation facade asks
for `min_responses + 1` slots for the legacy spare-retry shape, but the Pi dispatcher originally
dropped `minimum_n`; with exactly three identities it attempted four slots and failed before a
model call. Separately, the full-ensemble facade could label a below-minimum partial result as
`full_ensemble`, and Research Spine coding could select from one Pi manager while dispatching
through another service/manager pair. Those are now fixed fail-closed: Pi honors the governed
minimum, partial results downgrade to `dual_run`, and selection plus every structured coder call
share one request-scoped `PiExecutionService`/`PiModelManager` pair. The deterministic suites and
feature-doc checks are green; Compass Forge still reports only inherited repository gate debt.

Verified: local `testing` and `origin/testing` are exact and clean at
`0e21428d681e2f6ed163f51cdbb4ee5741896c37`; the pinned native Compass Forge runtime is active
with Python fallback disabled; passive Mac Studio inspection found Docker Desktop `29.7.2`, no
Istara benchmark/model/provider containers, and only unrelated `plex` running. No host install,
model load, provider retry, or Docker mutation occurred during this reconciliation.

Next: do not call the live result an ensemble or Research Spine failure. Resume only with
owner-authorized provider credit and three distinct Compose-owned routes/models, then run the
Docker-only profiles from a clean checkout at the exact SHA above and require raw-span sharing,
three served identities, numeric Fleiss/alpha, grounding, reconciliation, Done/report gates,
two-call/long-horizon artifacts, Petals interoperability, and teardown evidence.

### L-220 | 2026-08-27T01:13:20Z | S2-execute | gpt-5-codex | exact-tip handoff correction

Did: Corrected the durable Build Stream header and the live-failure handoff paragraph to point
at the actual pushed `testing`/`origin/testing` tip `a903cc049da88cd28cb2be13e65e851c4548044f`
instead of the superseded `1e93904d...` commit. Applied the same factual correction to the
external `/Users/user/Desktop/testing.md` finding F-R9-54. This prevents a future Docker retake
from silently using a stale implementation while preserving the historical failure narrative.

Evidence: local `testing` and `origin/testing` resolve to the same clean commit; Compass Forge
gate-after record 106 reports zero new issues, zero new forbidden dependencies, zero new missing
paths, zero new import cycles, and zero generated/contract drift. The repository gate remains
red only from inherited debt. No provider request, model load, host package operation, or
Mac Studio mutation occurred.

Open gate is unchanged: the live profile still has provider HTTP 402 history and no three
Compose-owned donor/model routes, so it cannot yet prove independent model identities, formal
Fleiss/Krippendorff reliability, reconciliation, accepted Done/report promotion, or Petals
interoperation.

### L-221 | 2026-08-27T01:17:30Z | S2-execute | gpt-5-codex | retake pointer made freshness-safe

Did: Replaced the Build Stream `next_action`'s hard-coded implementation SHA with an explicit
freshness check: the next operator must resolve the latest pushed `testing` tip and materialize
the Mac Studio detached checkout at that exact SHA immediately before launch. Updated F-R9-54
accordingly so a later documentation checkpoint cannot make the handoff stale again.

Evidence: the parent checkpoint was `ca0127c030fe3906c38af2ed9906930a545daaa2`; local and
`origin/testing` were equal and clean before this documentation-only edit; no provider request,
model load, host package operation, or Mac Studio mutation occurred.

### L-222 | 2026-08-27T01:39:38Z | S2-execute/S3-review/S4-remediate | gpt-5-codex | Docker-owned three-model harness closure checkpoint

Did: Repaired the Docker-only three-model path so the direct host refusal remains fail-closed
while `scripts/runner/docker-run.sh` explicitly marks a nested Docker-owned runner, selects
`probe:deep:three-model`, enables the Compose `three-model` profile, and passes the read-only
model root and project backend network into the runner. Compose now owns donor 1 at
`donor-gemma:8080`; donors 2 and 3 remain disposable llama.cpp containers started through the
nested Docker socket. Relay, preflight, and invite containers join the backend network, and
history/report artifacts persist Docker topology provenance. The container-side donor preflight
now retries within a bounded three-minute cold-load window so model initialization is not a
one-shot false negative, while persistent route/model failures still block acceptance. Updated
the living Ensemble Health and benchmark documentation and regenerated feature-site artifacts.

Result: The prior local topology tests first went red for the missing Docker marker, missing
backend-network wiring, missing probe/profile/Compose donor selection, and missing history/report
provenance; they now pass (`10/10`). The focused Research Spine/Pi authority suite passes
`84/84`; the full real-user benchmark `check` passes `72/72`; syntax and both base and
`three-model` Compose renders pass; plan-only execution returns `PLAN_RC=0`; and an explicit
missing Gemma-file invocation exits `RC=2` before workload startup. External F-R9-55 records the
topology defect and F-R9-56 records the cold-load readiness defect. No provider request, model
load, host package operation, or Mac Studio mutation occurred.

Verified: `git diff --check` passes. Compass Forge `gate before --task CF-15 --summary` reports
`new_failures=0`, `new_issue_count=0`, `actionable_failures=[]`, and the same inherited gate
status (`31` failures, `209` warnings, `3` security findings); no new drift is attributable
to this checkpoint. The live acceptance gate remains open: the last Mac Studio run stopped at
provider HTTP `402 Insufficient Balance`, and no fresh three Compose-owned routes or authorized
provider credit are available for the required live retake.

Next: run the final focused verification and Compass Forge after-gate, attach command/gate
evidence, commit only the ten intended repository files, push `testing`, verify local/remote
tree parity and clean status, then leave the Mac Studio retake as a fresh-checkout operator gate
requiring exact SHA resolution, three real served model identities, Fleiss/Krippendorff numbers,
grounding, reconciliation, Done/report promotion, two-call/long-horizon, Petals interoperation,
and teardown evidence.

### L-223 | 2026-08-27T01:41:20Z | S2-execute/S3-review/S4-remediate | gpt-5-codex | after-gate and evidence attachment

Did: Completed the final focused verification after the bounded preflight retry and living-doc
update. Compass Forge command evidence `62` records the 84-test Research Spine/Pi authority
suite, 72-test real-user benchmark check, 10 topology contracts, syntax checks, Compose renders,
feature-doc generation/check, plan-only execution, and missing-Gemma-file fail-closed control.
Compass Forge gate evidence `63` records the after-gate result.

Result: `gate after --task CF-15 --summary` remains `status=fail` only because of inherited
repository debt (`31` failures, `209` warnings, `3` security findings); it reports
`new_failures=0`, `new_issue_count=0`, `actionable_failures=[]`, and no new contract,
generated, GraphQL, or architecture drift. The branch changes are ready for transport; live
provider/ensemble acceptance remains intentionally open.

Verified: no provider request, model load, host package operation, or Mac Studio mutation was
performed. The Docker-only wrapper exits `RC=2` before workload startup when the Compose Gemma
GGUF is missing, and plan-only mode exits `PLAN_RC=0` without contacting services.

Next: commit only the ten intended repository files, push `testing`, fetch and verify exact
`testing`/`origin/testing` tree parity with a clean worktree, then retain the recovery worktree
and leave the fresh-checkout Mac Studio retake gated on owner-authorized provider credit and
three provisioned Compose-owned model routes.

### L-224 | 2026-08-27T01:41:59Z | S5-ship&learn | gpt-5-codex | clean testing transport checkpoint

Did: Committed the Docker-owned three-model harness, Compose donor profile, bounded cold-load
preflight retry, provenance fields, tests, living docs, generated feature artifacts, and the
Build Stream ledger as `b66af71e` (`fix: wire Docker-owned three-model benchmark topology`).
Pushed `testing` to `origin/testing` and fetched the remote ref for a final parity check.

Result: local `testing` and `origin/testing` both resolve to
`b66af71eb5b7d84b4a3d6fbf280986673690b261`; `git diff --exit-code` and
`git status --porcelain` are clean. No old worktree or branch was deleted because the retained
recovery checkout is not proven merged/obsolete. The external findings ledger contains F-R9-55
and F-R9-56 with the corrected live-evidence boundary.

Verified: no provider request, model load, host package operation, or Mac Studio mutation was
performed in this checkpoint. Local evidence remains deterministic/harness proof only. The live
gate is still open because the latest Mac Studio attempt stopped at provider HTTP `402
Insufficient Balance`, and three provisioned Compose-owned routes/models have not been supplied.

Next: only after owner authorization, verify the latest `origin/testing` SHA immediately before
creating a clean detached Mac Studio checkout; provision or confirm three genuinely distinct
served model identities (including the Compose Gemma donor and two llama.cpp donors), then run
provider/Petals/combined profiles as separate evidence planes. Accept the Research Spine only
with common raw source spans, independent atomic coding, numeric Fleiss and Krippendorff
metrics, grounding, reconciliation, human-Done/report promotion, two-call/long-horizon
artifacts, Petals interoperability, credential revocation, and Docker teardown proof.

### L-225 | 2026-08-27T01:44:20Z | S5-ship&learn | gpt-5-codex | passive Mac Studio handoff check

Did: Performed a read-only SSH/Docker observation after the clean push. The target is
`users-Mac-Studio.local` (macOS `26.5`) with Docker Server `29.7.2`; the Docker CLI and Compose
control path responded normally. No Istara/benchmark containers or matching Compose project is
currently running; no unrelated workload was touched.

Result: The previous live campaign is complete/idle rather than still running. The Mac Studio
is ready only for a future owner-authorized retake after the exact pushed `origin/testing` SHA,
provider credit, and three provisioned model files/routes are verified. The Docker-only rule was
honored: this checkpoint performed no host installation, package operation, model load, service
start, image pull, volume deletion, or repository mutation on the Mac Studio.

Verified: `ssh -o BatchMode=yes -o ConnectTimeout=10 macstudio` plus passive Docker version,
container listing, and Compose project listing. Local `testing`/`origin/testing` remain clean and
equal at `c19648a69ebfa3c326fc9c8d66b3bb938651a497`.

Next: resume only with owner authorization and the live prerequisites. Verify the latest pushed
SHA immediately before creating a clean detached Mac Studio checkout; run provider, Petals, and
combined profiles as separate evidence planes; require three genuinely distinct served model
identities, common raw source-span coding, numeric Fleiss/Krippendorff metrics, grounding,
reconciliation, human-Done/report promotion, two-call/long-horizon artifacts, credential
revocation, and Docker teardown before calling the Research Spine accepted.

### L-226 | 2026-08-27T01:51:24Z | S5-ship&learn | gpt-5-codex | auditor | Phase 9

Did: Corrected the Status Block and the stale SHA in L-225 after the docs-only handoff commit.
Reconciled the local branch, remote branch, test topology, and passive Mac Studio state. Audited
the Pi ensemble implementation and its verification seams against the Research Spine contract.
No source-code change was warranted in this checkpoint: the previously suspected duplicate
`_from_settings` assignment is not present, and the supported full-ensemble callers pass a
three-rater minimum (the `min_responses=2` compatibility case still requests three slots).

Result: the current tip is `14b6c83745e94fee595b845007d8da336c48fe42` on both `testing` and
`origin/testing`; the worktree is clean. The deterministic suites prove routing authority,
identity-distinct selection, fail-closed downgrade/partial handling, source-span coverage,
formal Fleiss plus Krippendorff calculation, grounding/reconciliation gates, and Docker wrapper
topology guards. They do not prove a live provider response, three served model identities,
live reliability numbers, Petals interoperability, two-call/long-horizon execution, or a
reportable human-Done artifact. Passive SSH confirms the Mac Studio is idle and Docker-only
ready; no host installation, image pull, model load, service start, or data deletion occurred.

Verified: Compass Forge native Rust `status`/`next`; impact/why/test-impact for the ensemble
engine; `git status --short --branch`; exact local/remote parity; and source/test inspection of
`backend/app/core/pi_runtime/engine.py`, `backend/app/core/pi_runtime/model_manager.py`,
`backend/app/core/agentic/dispatcher.py`, `backend/app/core/validation.py`,
`backend/app/services/research_validity_service.py`, and the W1/W3/W7/topology suites.

Next: execute the completion matrix below only when the owner supplies the live prerequisites.
Keep every live claim tied to immutable Docker artifacts and leave CF-15 open until all required
gates have command evidence.

## Phase 9 completion matrix — remaining work and exact acceptance bar

This matrix is the operative handoff for any agent continuing this Build Stream. A green
deterministic test is necessary but never sufficient for a row marked `live`. Rows must be
completed in order; a later row cannot promote evidence from a failed or skipped earlier row.
Every row needs a ledger entry, an immutable artifact path, and a Compass Forge command-evidence
record under CF-15. Never copy credentials, provider URLs, model weights, or bearer tokens into
this file or into committed artifacts.

| ID | Plane | Status | Required work | Acceptance evidence |
|----|-------|--------|---------------|---------------------|
| G0 | Authorization | open | Obtain explicit owner authorization for bounded live model activity, provider spend/credit, exact target SHA, and the model files/route configuration. Confirm whether the run may discard only testing containers/volumes after artifacts are copied. | Written authorization in the active task; no secret values in chat/ledger. |
| G1 | Checkout integrity | open | On Mac Studio, fetch `origin/testing` at launch time and create a fresh detached checkout/worktree at the resolved SHA. Do not repair or clean the old dirty `~/istara-testing` checkout. | `git rev-parse HEAD`, `git rev-parse origin/testing`, `git status --porcelain`, and checkout path recorded; all clean and equal. |
| G2 | Docker-only boundary | open | Run all application, provider, relay, Petals, test, and teardown commands inside Docker/Compose on Mac Studio. Do not run package managers, model servers, or benchmark code directly on macOS. | SSH transcript showing Docker CLI/server, Compose project labels, container IDs, and no host package/install commands. |
| G3 | Image and model provenance | open | Use only pre-approved images and already-provisioned model files. Set an absolute `ISTARA_BENCHMARK_MODEL_ROOT`; verify every GGUF is present and contained under that root. Keep the bind mount read-only. | SHA/image digests, model filenames and hashes (names only where sensitive), read-only mount inspection, and wrapper fail-closed control for a missing/out-of-root file. |
| G4 | Compose topology | open | Render the base and `three-model` profiles, start the backend plus `donor-gemma` and two additional llama.cpp donors, and attach relay/preflight/invite containers to the backend network. Let the bounded cold-load retry complete before declaring readiness. | `docker compose config --quiet`, `docker compose --profile three-model ps`, health/readiness logs, `/v1/models` identity output for each donor, and no host listener dependency. |
| G5 | PI authority API | open | Exercise PI Model Management list/add/update/delete on a disposable testing database. Verify persisted endpoint state is the source of truth, live catalog reset/projection occurs, and the dispatcher resolves through the same manager instance. | API responses plus DB rows/projection parity, manager identity/endpoint IDs, and audit records. |
| G6 | Classical retirement | open | Call the retired classical model/provider write endpoints and verify explicit `410` compatibility responses pointing callers to `/api/settings/pi-endpoints`. Verify no hidden classical discovery, reconstruction, or startup mutation occurs. | HTTP status/body captures, startup logs, and negative DB-diff assertion. |
| G7 | Petals donation | open | Exercise Petals slash-string/model donation registration, consent, project scope, health, usage, and revoke paths. Verify a non-consented/unhealthy/network donor maps to typed 503 and never falls back to a paid route. | Request/response artifacts, consent/projection rows, route evidence with donor node and served model, and revoke/cleanup proof. |
| G8 | Three identity admission | open | Admit exactly three genuinely different served model identities (not endpoint replicas), including the Compose Gemma donor and two separately identified routes. Record provider kind, endpoint ID, model ID, account handle/fingerprint, and route source. | Per-run immutable route manifest; `distinct_model_count=3`, `rater_count=3`, no blank/duplicated model identity, and evidence that each identity produced a response. |
| G9 | Engine parity | open | Run the same bounded source task through every supported execution choice: legacy/Istara semantics and Pi Agentic Loop semantics, with both resolved by PI Model Management for provider/model selection. Treat “Agentic Loop” labels as execution semantics, not a second model authority. | Paired request/response artifacts with selected engine, manager endpoint, route evidence, tool policy, and no classical bypass. |
| G10 | Common source spans | open | Feed identical raw source documents and source-span Evidence Units to every coder. Do not use synthesized nuggets, pre-accepted findings, or different prompt/source slices per model. | Source snapshot hash, Evidence Unit IDs/spans, document version, codebook version, and per-coder input hash equality. |
| G11 | Independent atomic coding | open | Run independent structured extraction/open coding for every Evidence Unit on all three admitted identities. Require complete unit coverage, exact source quotes, code/rationale/confidence, and no cross-coder response leakage. | Coding run, coder rows, CodeApplication rows, endpoint/model route evidence, and `3 x N` coverage matrix with no missing cells. |
| G12 | Formal reliability | open | Compute the production reliability gate from the coding matrix: Fleiss’ kappa plus Krippendorff alpha companion. Preserve item-level agreement and distinguish undefined perfect-agreement/zero-variance cases from a fabricated numeric score. | Numeric kappa/alpha (or explicit mathematically undefined interpretation), thresholds/version, category matrix, and `promotion_status=accepted` only when the gate passes. |
| G13 | Grounding | open | Verify every accepted application quote is an exact span in the source snapshot and that unsupported codes, stale document versions, synthetic QA units, malformed schemas, and incomplete coverage fail closed. | Grounding report with source offsets/hashes, negative fixtures, and no unsupported application accepted. |
| G14 | Reconciliation | open | Create a separate reconciliation decision for every application. Record reviewer identity, rationale, source, timestamp, and decision type. Reliability success alone must not auto-reconcile or promote. | Decision rows for all applications; unresolved count zero; rejected/uncertain cases remain non-reportable. |
| G15 | Done/report gate | open | Move the task through `IN_REVIEW` to explicit human approval/Done and call the report-validity assessor. Verify report generation is refused for missing/stale/unreconciled evidence and allowed only for accepted, reconciled evidence tied to the approved Done task. | Task transition audit, `assess_task_research_validity` output, report artifact with evidence handles, and negative gate captures. |
| G16 | Two-call continuity | open | Run a two-call/session scenario through both engine choices, preserving session identity, history, manager resolution, tool policy, and per-turn route evidence. Verify the second call sees only authorized prior context and that a failed first call cannot silently become accepted history. | Two-turn transcript, session/task IDs, per-turn route/evidence records, and failure/retry control. |
| G17 | Long horizon/tool loop | open | Execute a bounded long-horizon task with multiple tool calls/checkpoints, recovery or timeout behavior, and final synthesis. Verify every research-data-producing tool result enters the Spine or is marked provisional/non-reportable. | Event/checkpoint trace, tool call IDs, source/evidence handles, recovery outcome, budget/usage ledger, and report gate result. |
| G18 | Petals/PI combined ensemble | open | Repeat G8–G15 with a mixed API-compatible/Petals topology and then Petals-only where supported. Verify project path binding, consent, donor health, route kind, model identity, and no cross-project leakage. | Separate provider, Petals, and combined manifests; route evidence; project-scope negative tests; reliability and reconciliation outputs. |
| G19 | Negative controls | open | Deliberately run provider 402, missing model file, duplicate model IDs, duplicate endpoint replicas, unavailable donor, provider/model mismatch, partial sample failure, stale source, and missing human decision. | Each control exits with typed fail-closed status; no control creates `success`, accepted reliability, Done, or reportable output. |
| G20 | Artifact integrity | open | Copy logs/manifests/reports before teardown; redact secrets; bind artifacts to source SHA, image/model hashes, profile, environment class, and generated time. Re-run report generation from artifacts only. | Content hashes, secret-shaped scan, reproducibility diff (excluding declared timestamps), and artifact index. |
| G21 | Teardown | open | Stop and remove only the disposable testing Compose project/containers/volumes authorized by G0. Preserve evidence and protected `LLMs/`/`Model_Finetuning/` folders. Verify no unrelated Mac Studio workload was touched. | `docker compose down` transcript, final `docker ps`/volume list, artifact existence, and before/after unrelated-workload comparison. |
| G22 | Final parity/CF closure | open | Push only intended repository changes, fetch, verify exact local/remote tree parity, run the after-gate, attach command/gate evidence, and close CF-15 only if every mandatory live row is complete. | Clean `testing` worktree, exact SHA parity, CF gate/evidence IDs, completed findings register, and truthful S5 summary. |

### Audit interpretation rules for the next agent

1. `validation.full_ensemble`, `dual_run`, and `self_moa` are response-level quality
   signals. Their `consensus.agreement_score` is not Fleiss’ kappa and must never be copied
   into the Research Spine reliability fields.
2. A successful `PiExecutionService.run_ensemble` call proves dispatch mechanics only. It is
   not evidence of three independent models unless successful route evidence contains three
   distinct served model identities.
3. A dispatcher endpoint list can include failed attempts. Count successful route evidence and
   successful CodeApplication rows separately; never infer coder count from selected slots.
4. Legacy/Istara and Pi are execution planes. PI Model Management is the provider/model
   authority for both. The UI's project-inherit option is a setting inheritance choice, not a
   third independent model manager.
5. Deterministic fakes are valid for schema, routing, fail-closed, and mathematical gate
   tests. They cannot validate model quality, prompt adherence, provider compatibility,
   latency, token accounting, or real ensemble bias reduction.
6. A provider HTTP 200, a green `/v1/models`, or a green Compose healthcheck is not enough.
   The accepted evidence must connect raw source spans → independent coders → numeric
   reliability → grounding → reconciliation → human Done → report.
7. If any live prerequisite is absent, record `not_run`/`blocked` with the exact reason and
   preserve the deterministic evidence. Do not downgrade a missing live gate to “passed” and
   do not call the overall Research Spine accepted.

### L-227 | 2026-08-27T01:53:30Z | S5-ship&learn | gpt-5-codex | remediator | Phase 9

Did: Ran the Compass Forge after-gate against the ledger update. The requested single-file
completion matrix crossed the repository's `unexpected_large_files` threshold, so recorded the
required path-scoped, expiring suppression (ID `1`, expires `2026-12-31`) with the Build Stream
single-lifecycle rationale. Attached CF-15 command evidence `66` for the pushed commit/parity
and gate evidence `67` for the post-suppression result.

Result: after-gate reports the same inherited repository debt (`31` failures, `209` warnings,
`3` security findings) with `new_failures=0`, `new_issue_count=0`, and no actionable failures;
contract/generated/GraphQL drift remains zero. The suppression is explicit and temporary, not a
claim that the large historical ledger is generally acceptable. Revisit it when Phase 9 closes
or if the lifecycle file is split only through a future Build Stream policy decision.

Verified: `compass-forge gate suppress --rule unexpected_large_files --path
docs/build-stream/2026-08-23-agentic-core-integrity-and-qa.md --expires 2026-12-31`; `compass-forge
gate after --task CF-15 --summary`; CF evidence IDs `66` and `67`; and clean local/remote parity
at `476091ae923f51e1d5fbdb62f8e63578a4d81f61`.

Next: wait for G0 live authorization and prerequisites; then execute G1–G22 in order and append
one ledger entry per gate. Do not close CF-15 or claim Research Spine acceptance from the current
deterministic evidence alone.

### L-228 | 2026-08-27T01:59:45Z | S5-ship&learn | gpt-5-codex | verifier | Phase 9

Did: Re-ran the focused deterministic verification at the current testing tip after the ledger
and gate-remediation commits. No live provider, Docker workload, model load, or Mac Studio
mutation was performed.

Result: the Research Spine/Pi authority suite passed `84` tests; topology contracts passed `10`
tests; the complete real-user benchmark check passed `72` tests with zero failures, skips, or
cancellations. These results confirm the local mechanics and fail-closed test oracles remain
green after the documentation update, but they do not change the open G0–G22 live acceptance
status.

Verified: `python -m pytest -q -W error::RuntimeWarning tests/pi_production/test_w1_dispatcher_authority.py tests/pi_production/test_w7_validation.py tests/pi_production/test_w7_pi_manager_integration.py tests/pi_production/test_research_spine_donor_routing.py tests/pi_production/test_w3_research_spine.py tests/test_research_spine_end_to_end.py` → `84 passed in 5.18s`; `node --test tests/real_user_benchmark/lib/topology-contract.test.mjs` → `10 passed`; `npm --prefix tests/real_user_benchmark run check` → `72 passed`.

Next: preserve this deterministic baseline and do not reinterpret it as live ensemble proof;
resume at G0/G1 when owner authorization, provider credit, and three Docker-served model routes
are available.

### L-229 | 2026-08-27T01:54:40Z | S5-ship&learn | gpt-5-codex | auditor | Phase 9

Correction: L-228's content and command outputs are valid, but its timestamp was entered ahead
of the actual verification clock. This append-only correction establishes the truthful ledger
time (`2026-08-27T01:54:40Z`) and is the current Status Block anchor; no test result or scope
claim changed.

Verified: `date -u` at append time; the exact 84/10/72 deterministic results remain those
recorded in L-228.

Next: resume at G0/G1 only when the owner-authorized live prerequisites exist.

### L-230 | 2026-08-27T01:55:14Z | S5-ship&learn | gpt-5-codex | verifier | Phase 9

Did: Ran the post-checkpoint Compass Forge after-gate and reconciled the new ledger commit
against `origin/testing`.

Result: after-gate remains inherited-debt-only (`31` failures, `209` warnings, `3` security;
`new_failures=0`, `new_issue_count=0`, `actionable_failures=[]`) with the explicit expiring
large-ledger suppression active. The current branch tip is `901e74cabcdfdc9db23aea8933b226604e779673`.

Verified: `compass-forge gate after --task CF-15 --summary`; `git fetch origin testing`; exact
local/remote SHA equality; `git diff --check`; and clean worktree.

Next: no further local mutation is justified until G0 live authorization and G1–G4 Mac Studio
Docker prerequisites are supplied; preserve the deterministic baseline and execute the matrix
in order when they are available.

### L-231 | 2026-08-27T01:55:51Z | S5-ship&learn | gpt-5-codex | verifier | Phase 9

Did: Recorded the final clean transport state after the L-230 checkpoint commit.

Result: `testing` and `origin/testing` are equal at
`b765926670a66868c718b7242c851bc86bf4a725`; the worktree is clean. No live test campaign is
running on Mac Studio, and no host-side installation or model activity occurred.

Verified: `git fetch origin testing`, exact SHA equality, `git diff --check`, and
`git status --porcelain`.

Next: continue the active goal at G0/G1 when the owner-authorized live prerequisites become
available; do not claim terminal acceptance from this deterministic-only checkpoint.

### L-232 | 2026-08-27T02:02:16Z | S5-ship&learn | gpt-5-codex | remediator | Phase 9

Did: Audited the validation-to-MoA evidence boundary against the Research Spine completion
matrix. The PI engine and dispatcher already return the effective served model on each
successful `TurnResult`, but `validation._dispatch_ensemble` discarded that field while
constructing response-level `route_evidence`. Because the live MoA assessor counts served
model identities only from successful route evidence, a genuine three-model response could be
misclassified as `model_identity_collapse` even when the routes were independent.

Changed: Added a red-to-green regression in `tests/test_validation_project_scope.py`, preserved
the non-secret sample `model` identity in `backend/app/core/validation.py`, and documented the
contract in `docs/features/content/ensemble/health/architecture.md` plus generated site output.
Missing model identity remains absent and fail-closed; it is never inferred from an endpoint or
requested model. Appended the corresponding open-live finding as F-R9-57 to
`/Users/user/Desktop/testing.md`.

Verified: the regression failed before the patch (`models_used=[]`) and passed after it;
focused Research Spine/Pi validation tests passed `87`; MoA unit tests passed `21`; topology
contracts passed `10`; the full real-user benchmark check passed `72`; feature docs generation
and check passed for `86` features; shell/Node syntax checks and `git diff --check` passed. No
provider call, model load, Docker workload, or Mac Studio host mutation occurred.

Interpretation: this closes a local observability/oracle defect only. Response-level validation
is still not formal Fleiss/Krippendorff reliability; Research Spine acceptance still requires
the live G0–G22 Docker-only matrix (three served identities, common raw spans, coding,
reliability, grounding, reconciliation, human Done/report, two-call/long-horizon, Petals
interoperability, artifacts, teardown, and parity).

Next: commit and push this bounded remediation to `testing`, verify exact remote parity, run the
Compass Forge after-gate, then re-check Mac Studio's Docker-only prerequisites at the exact SHA.
If G0 remains unavailable, record `not_run` and leave CF-15 open.

### L-233 | 2026-08-27T02:04:21Z | S5-ship&learn | gpt-5-codex | verifier | Phase 9

Did: Transported the bounded ensemble-evidence remediation to `origin/testing` and attached
Compass Forge evidence records `74`–`78` for deterministic checks, generated feature docs,
after-gate, exact parity, and the passive remote preflight. Re-checked the Mac Studio at the
new exact SHA without starting any service or model activity.

Result: local `testing` and `origin/testing` are equal at
`aec8d98d9f1c9b5911d31a90e98950b1b046b8fd`; the local worktree is clean. Compass Forge
after-gate record `115` remains `fail` only for inherited `secret_flow` and the explicitly
suppressed path-scoped large historical ledger; the comparison has no new issues, forbidden
dependencies, import cycles, or actionable failures. Mac Studio reports `users-Mac-Studio.local`,
macOS `26.5`, Docker server `29.7.2`, and only the unrelated healthy `plex` project/container.
No Istara/benchmark containers are running, so no live campaign is available to follow.

Verified: `87` focused Research Spine/Pi tests, `21` MoA tests, `10` topology tests, `72`
real-user benchmark checks, feature docs check for `86` features, syntax checks, `git diff
--check`, exact Git parity, and the passive SSH/Docker command. No host installation, model
load, provider call, volume deletion, or unrelated workload mutation occurred.

Next: remain at G0/G1 with status `not_run` until owner-authorized provider credit and three
Compose-served model routes exist. At launch time materialize a fresh detached checkout of this
SHA, run only the Docker-owned provider/Petals/combined profiles, and preserve every G0–G22
artifact. CF-15 remains open; deterministic evidence cannot substitute for live Research Spine
reliability, reconciliation, Done/report, two-call, long-horizon, Petals, and teardown proof.

### L-234 | 2026-08-27T02:05:03Z | S5-ship&learn | gpt-5-codex | verifier | Phase 9

Did: Ran the final Compass Forge after-gate at the transported remediation tip and attached
gate evidence `80`. This checkpoint is intentionally documentation-only after the source/test
fix and does not reopen or fabricate a Mac Studio run.

Result: gate record `117` reports `status=fail` only from inherited `secret_flow` findings and
the path-scoped expiring suppression for this required single-file Build Stream ledger. The
comparison has zero new issues, forbidden dependencies, Python import cycles, or missing required
paths. No model/provider/Docker activity occurred during the gate.

Verified: the branch was pushed at
`11128c2cc689c30e43dfd9a78c4225141d22de2c` with clean local/remote parity; deterministic and
benchmark evidence remains in CF records `74`–`78`; this final after-gate is CF record `117` /
evidence `80`.

Next: the active completion goal remains open at G0/G1. Do not close CF-15 or call the Research
Spine accepted until owner-authorized provider credit, three Compose-served model identities,
and the complete Docker-only G0–G22 evidence matrix are present. If resumed with prerequisites,
start from a fresh detached checkout of this exact SHA and append each live gate result here.

### L-235 | 2026-08-27T02:06:04Z | S5-ship&learn | gpt-5-codex | verifier | Phase 9

Did: Performed a second passive Mac Studio inventory after the final parity checkpoint and
attached Compass Forge command evidence `81`. The check inspected only Git metadata and Docker
inventory; it did not install packages, alter the named checkout, pull images, start containers,
load models, or remove volumes.

Result: `/Users/user/istara-testing` remains at stale commit `1b9b6d6` with owner modifications
in deployment/runtime files. Docker reports only the existing Istara backend/frontend and
provider-stub images; no Qwen/Gemma/llama.cpp/Petals model image, Istara benchmark container,
matching testing volume, or benchmark network is present. This corroborates the existing
F-R9-49/F-R9-53/F-R9-54 live blockers rather than creating a new code regression.

Verified: evidence `81`; prior final branch tip remains
`c6247d58273bb8a8ecfe16ad451c4a0c036c0bef` and must be re-resolved at launch. The intentionally
retained recovery worktree is untouched. No host installation or unrelated Docker workload was
mutated.

Next: stay at G0/G1 `not_run`. When the owner supplies provider credit and the three-model
Docker-owned assets/routes, create a fresh detached checkout of the launch-time
`origin/testing` SHA, render Compose before startup, then execute provider, Petals, and combined
profiles with all G0–G22 artifacts. Never overwrite the dirty named checkout or count stale
images as live proof.

### L-236 | 2026-08-27T02:06:47Z | S5-ship&learn | gpt-5-codex | verifier | Phase 9

Did: Re-ran the Compass Forge after-gate after the passive prerequisite inventory and attached
gate evidence `83`.

Result: record `118` is `fail` only for inherited `secret_flow` findings and the explicit
path-scoped suppression on this historical single-file ledger. There are zero new issues,
forbidden dependencies, Python import cycles, or missing required paths. The final transported
branch remains clean and must be re-resolved at launch time after any future remote change.

Next: no additional local code or infrastructure mutation is justified while G0 is unavailable.
Resume with the launch-time `origin/testing` SHA, fresh detached Docker checkout, and the
G0–G22 live matrix; leave CF-15 open until the real provider/Petals/Research Spine evidence is
complete and independently reviewable.

### L-238 | 2026-08-27T02:20:34Z | S5-ship&learn | gpt-5-codex | verifier | Phase 9

Did: Committed the fail-closed Research Spine benchmark-oracle remediation and pushed it to
`origin/testing` at `1b94f23dfc9b1552631ac6ef8772f1b6d6d20ffb`. Local `testing` and
`origin/testing` are equal and the worktree is clean. The commit includes the probe/test
regressions, the Ensemble Health feature-doc contract plus generated site/manifest, and this
Build Stream checkpoint; the shared audit file records F-R9-58.

Verified: Compass Forge command evidence `85` records 74 Node benchmark subtests, 87 focused
Python Research Spine/Pi tests, 21 MoA tests, 10 topology tests, feature-doc generation/check,
and `git diff --check`; passive Mac Studio prerequisite evidence `86` records host
`users-Mac-Studio.local`, macOS `26.5`, Docker `29.7.2`, only unrelated healthy Plex, and no
matching benchmark containers, networks, volumes, or model/Petals images. No host install,
model load, provider call, service start, pull, or deletion occurred.

Boundary: the deterministic oracle now fails closed on missing or vacuous contract, traceability,
RAG, or telemetry payloads, but deterministic success still cannot prove live three-model bias
reduction. G0/G1 remain `not_run`; CF-15 remains open pending owner-authorized provider credit,
three Compose-served model identities, and the complete Docker-only G0–G22 artifact matrix.

Next: when prerequisites exist, re-resolve `origin/testing` immediately, create a fresh detached
checkout on Mac Studio, render Compose before startup, run the provider, Petals, and combined
profiles, and preserve route/model identity, raw-span coding, Fleiss/Krippendorff, grounding,
reconciliation, human-Done/report, two-call, long-horizon, interoperability, teardown, and
Compass Forge evidence. Do not overwrite the stale owner-dirty named checkout.

### L-237 | 2026-08-27T02:18:05Z | S4-remediate | gpt-5-codex | implementer/verifier | Phase 9

Did: Audited the real-user benchmark's Research Spine oracle after the prior ensemble-route
identity fix. The oracle accepted truthy-but-empty contract, traceability, RAG, and telemetry
objects, and it could leave an accepted coding response marked valid even when the governing
contract request returned `{}`. This was a concrete false-positive path in the test itself, not
evidence of a live model-quality regression.

Changed: `tests/real_user_benchmark/lib/research-spine-probes.mjs` now requires the typed
contract keys before coding or multi-model validation can pass, requires summary report-gate and
count fields, requires the synthesis-and-traceability contract plus promotion rule, and requires
telemetry `status=ok` with content-policy/protected-field metadata. Added regressions for missing
contract and empty evidence payloads. Updated the Ensemble Health living feature contract and
regenerated the site/manifest. Appended audit finding F-R9-58 to `/Users/user/Desktop/testing.md`.

Verified: red/green targeted proof, then `npm --prefix tests/real_user_benchmark run check` (74
subtests), 87 focused Python Research Spine/Pi tests, 21 MoA tests, 10 topology tests,
`python scripts/feature_docs.py --seed-missing --generate-site --check` (86 features), and
`git diff --check` all passed. Compass Forge after-gate record reports zero new issues,
forbidden dependencies, import cycles, or missing paths; evidence row 85 records the commands.

Boundary: this closes a benchmark false-positive and makes deterministic acceptance evidence
more truthful. It does not prove three live distinct model identities, common raw-span coding,
Fleiss/Krippendorff reliability, grounding, reconciliation, human-Done/report promotion,
two-call/long-horizon behavior, Petals interoperability, or teardown. Those remain G0/G1
`not_run` until the owner-authorized Docker-only Mac Studio prerequisites exist.

Next: commit and push this remediation with the generated feature docs, verify local/remote SHA
parity, then preserve the live campaign as blocked rather than starting host or provider work.

### L-239 | 2026-08-27T02:31:00Z | S5-ship&learn | gpt-5-codex | auditor | Phase 9

Did: Audited the Pi Model Management authority, classical-endpoint retirement, Petals bridge,
dispatcher routing, and ensemble acceptance contracts with a Compass context pack plus the
focused migration/Petals/settings/model-source/runtime suite. The suite passed 95 tests. It
confirms the deprecated classical adapters return their explicit 410/delegation behavior,
Petals consent/use/revoke/scope and diversity guards are covered, and the dispatcher resolves
the persisted/header/project choices through the two concrete runtime branches.

Finding: the implementation and living architecture expose two concrete engine choices—
`legacy` (publicly Istara) and `pi` (Pi Agentic Loop)—plus project-level `inherit`. The plan’s
P9-04 wording still calls “Istara, Agentic Loop, and Pi Agentic Loop” three selectable modes,
while G9 and the architecture contract describe legacy/Istara plus Pi as the executable parity
surface. This is an acceptance-language ambiguity, not a proven third runtime. It is recorded
as F-R9-59 in the shared audit file. No code change is justified until the owner confirms
whether “Agentic Loop” is shorthand for legacy/Istara; if it is a required third semantic, a
typed enum/API/UI option, dispatcher branch, and dedicated tests must be added before P9-04/G9
can be claimed complete.

Boundary: deterministic authority, Petals, and oracle tests are useful regression evidence but
do not prove a live three-model ensemble, common raw-span coding, Fleiss/Krippendorff metrics,
grounding, reconciliation, human-Done/report promotion, two-call/long-horizon behavior, or
Docker teardown. Mac Studio G0/G1 remain `not_run`; the passive inventory still shows no
benchmark/model/Petals workload. Do not reinterpret “inherit” as a third engine or start a
host-managed path.

Next: resolve the terminology at the next owner checkpoint. If shorthand, normalize P9-04 and
related acceptance text; if third-mode intent is confirmed, create a bounded Compass task for
the typed runtime/UI/dispatcher contract and tests. Once live prerequisites exist, re-resolve
`origin/testing`, create a fresh detached checkout, render Compose before startup, and run the
Docker-only provider/Petals/combined G0–G22 matrix with immutable identity, raw-span, reliability,
gate, long-horizon, interoperability, and teardown artifacts.

### L-240 | 2026-08-27T02:34:00Z | S5-ship&learn | gpt-5-codex | verifier | Phase 9

Did: Transported the terminology-audit checkpoint as commit
`465221ea2914855775df7f4a03f6c3a2c0afe5ab` and pushed `testing` to `origin/testing`. The local
worktree is clean and exact SHA parity is confirmed by both `git rev-parse HEAD` and
`git ls-remote origin refs/heads/testing`.

Verified: Compass Forge evidence `87` records the 95-pass static authority/Petals/settings/
runtime audit. The after-gate reports zero new issues, zero new failures, zero cycles, and no
actionable failures; its non-zero status remains inherited `secret_flow`/large-file debt plus
the documented single-file ledger suppression. No provider call, model load, image pull, host
installation, service start, or Docker mutation occurred.

Boundary: F-R9-59 remains an owner terminology decision. The branch is transport-clean, but the
Mac Studio live campaign is still unavailable: G0/G1 remain `not_run` and no claim is made for
three served model identities, independent raw-span coding, Fleiss/Krippendorff reliability,
grounding, reconciliation, human-Done/report promotion, two-call/long-horizon behavior, Petals
interoperability, or teardown.

Next: on the next authorized window, re-resolve the launch-time `origin/testing` SHA, create a
fresh detached checkout, render Compose before startup, and execute the Docker-only provider,
Petals, and combined G0–G22 matrix. Preserve immutable route/model identity and all Research
Spine gate artifacts; never overwrite the stale owner-dirty named checkout or run a host-managed
model path.

### L-241 | 2026-08-27T02:28:00Z | S5-ship&learn | gpt-5-codex | verifier | Phase 9

Did: Added the final transport receipt after the terminology-audit checkpoint was committed.
The preceding transport tip was `1ed2723ac68c207f2f4b75f3471aaae97c10c8f7`; Compass Forge
evidence `90` carries that corrected SHA (superseding the earlier intermediate receipt `89`).
This ledger entry is itself a subsequent documentation checkpoint, so the launch procedure must
always re-resolve `git rev-parse HEAD` and `git ls-remote origin refs/heads/testing` immediately
before the live run; the worktree is clean at each pushed checkpoint.

Verified: the after-gate still reports zero new issues, zero new failures, zero cycles, and no
actionable failures. Its failing status is inherited repository `secret_flow`/large-file debt
and the documented path-scoped ledger suppression, not this checkpoint. No live provider or
model activity occurred.

Boundary/next: F-R9-59 remains the only unresolved static audit decision: confirm whether
“Agentic Loop” is shorthand for legacy/Istara or a required third execution semantic. G0/G1
remain `not_run`. At the next authorized live window, re-resolve this exact remote SHA, use a
fresh detached Docker checkout on Mac Studio, render Compose before startup, and execute the
provider, Petals, and combined G0–G22 matrix with immutable route/model, raw-span, reliability,
grounding, reconciliation, human-Done/report, two-call/long-horizon, interoperability, and
teardown artifacts. Do not use the stale owner-dirty named checkout or any host-managed path.

### L-242 | 2026-08-27T02:34:13Z | S4-remediate | gpt-5-codex | implementer/verifier | Phase 9

Did: Audited the scorecard acceptance boundary after the fail-closed Research Spine oracle
change. `acceptanceGateStatus()` could still report a provider gate as `verified` from
`codingValidation=true` alone, even when the feature payload said independent multi-model
validation and Research Spine traceability were false or absent. This was a second, concrete
false-positive path in the test/scorecard layer; it did not demonstrate a live model failure.

Changed: provider verification now requires the conjunction of `codingValidation`,
`multiModelResearchSpineValidation`, and `researchSpineTraceability`. Updated complete provider
and combined fixtures to include all three signals, and added a regression proving that an
inconsistent coding-only payload is `blocked`. Updated the Ensemble Health living feature
contract and regenerated the site/manifest. Appended audit finding F-R9-60 to
`/Users/user/Desktop/testing.md`.

Verified: TDD red run reproduced the false `verified` result; the green targeted scoring suite
passed 18/18. The full real-user benchmark check passed 76/76 tests, feature-doc generation/check
passed for 86 features (224 artifacts), and `git diff --check` passed. Compass Forge before- and
after-gates report zero new issues, zero new failures, zero cycles, and no actionable failures;
their failing status remains inherited repository `secret_flow`/large-file debt and warnings.
Command evidence is recorded as CF-15 evidence 95.

Boundary: the scorecard is now unable to certify inconsistent provider evidence, but G0/G1 remain
`not_run`. This checkpoint still does not prove live three-model served identities, common raw
source-span coding, numeric Fleiss/Krippendorff reliability, grounding, reconciliation,
human-Done/report promotion, two-call/long-horizon behavior, Petals interoperability, or Docker
teardown. No host package, model, server, image, or Mac Studio workload was started or mutated.

Next: checkpoint this remediation to `testing` and `origin/testing`, re-resolve the launch-time
SHA immediately before any live run, and continue only through the Docker-owned provider/Petals/
combined G0–G22 matrix. Keep F-R9-59 as an owner terminology decision and never infer a third
engine from `inherit`.

### L-243 | 2026-08-27T02:36:30Z | S4-remediate | gpt-5-codex | implementer/verifier | Phase 9

Did: Reconciled the runner's live blocker contract with the hardened provider scorecard. A
selected provider run could otherwise pass `liveAcceptanceBlockers()` with coding and traceability
true while `multiModelResearchSpineValidation` was false, leaving exit status and scorecard status
in disagreement.

Changed: selected provider and no-profile coding paths now emit
`Requested independent multi-model Research Spine validation did not complete.` when the
multi-model flag is missing. Updated complete and partial deterministic fixtures so they declare
the full three-signal contract. Updated the Ensemble Health feature contract and generated site/
manifest, and appended finding F-R9-61 to `/Users/user/Desktop/testing.md`.

Verified: TDD red run reproduced the empty blocker list; the green scoring suite passed 19/19 and
the complete real-user benchmark check passed 76/76. Feature-doc generation/check passed for 86
features (224 artifacts), and `git diff --check` passed. This checkpoint is ready for Compass
Forge evidence and transport after the current gate review.

Boundary/next: this closes the deterministic runner/scorecard split only. G0/G1 remain `not_run`;
live proof still requires the Docker-owned provider/Petals/combined G0–G22 retake with immutable
three-model route/model identities, common raw-span coding, numeric Fleiss/Krippendorff metrics,
grounding, reconciliation, human-Done/report promotion, two-call/long-horizon artifacts, Petals
interoperability, and teardown. No host package, model load, service start, or Mac Studio mutation
occurred.

### L-244 | 2026-08-27T02:39:30Z | S4-remediate | gpt-5-codex | implementer/verifier | Phase 9

Did: Audited exported Research Spine acceptance fields after the provider gate and blocker
hardening. The scorecard's `research_spine_validation_verified` and the benchmark history record
were still copied from `codingValidation` alone, so an inconsistent caller payload could report
accepted validation without independent multi-model or traceability evidence.

Changed: `scoreRun()` now derives accepted Research Spine validation from coding,
`multiModelResearchSpineValidation`, and `researchSpineTraceability` together. `run.mjs` history
now persists the hardened scorecard value rather than the raw coding flag. Added a deterministic
regression, updated the Ensemble Health feature contract and generated site/manifest, and
appended finding F-R9-62 to `/Users/user/Desktop/testing.md`.

Verified: TDD red run reproduced the coding-only false positive; the green scoring suite passed
20/20 and the full real-user benchmark check passed 77/77. Feature-doc generation/check passed
for 86 features (224 artifacts), and `git diff --check` passed. Compass Forge impact for the
runner identified the acceptance/history contract and relevant Research Spine routes/tests.

Boundary/next: scorecard and history can no longer certify coding-only payloads, but G0/G1 remain
`not_run`. Live proof still requires the Docker-owned provider/Petals/combined G0–G22 retake with
immutable three-model route/model identities, common raw-span coding, numeric Fleiss/Krippendorff
metrics, grounding, reconciliation, human-Done/report promotion, two-call/long-horizon,
interoperability, and teardown. The Mac Studio named checkout remains stale/dirty and untouched;
re-resolve the launch SHA and use a fresh detached checkout when the host and model assets are
available.

### L-245 | 2026-08-27T02:50:00Z | S4-remediate/S5-ship&learn | gpt-5-codex | provenance and runner-contract audit

Did: Audited the Docker-only benchmark's source-snapshot evidence boundary and found that
`scripts/runner/docker-run.sh` accepted any 64-character `ISTARA_BENCHMARK_SOURCE_SNAPSHOT_SHA256`
value without comparing it to the checkout mounted into the runner. Added a fail-closed,
pre-workload recomputation of the canonical `git archive --format=tar HEAD` SHA-256 using the
existing host `shasum` or `sha256sum` utility; a mismatch now exits before image pull, Compose
startup, model load, or benchmark requests. This keeps all application/model work in Docker and
does not install tooling on the Mac Studio. Added the missing static contract assertion and
updated the stale probe-selector assertion so the explicit Docker-owned
`ISTARA_BENCHMARK_PROBE_SCRIPT` override remains covered.

Verified: the focused remote-runner contract suite passes `17/17`; the complete real-user
benchmark check passes `77/77`; feature docs regenerate/check for `86` features and `224` site
artifacts; `bash -n scripts/runner/docker-run.sh` and `git diff --check` pass. The local
canonical archive digest was computed successfully for the current checkout. Compass Forge
command evidence `101` records the deterministic checks and after-gate record `128` reports no
new dependency, missing-path, or cycle issues; its only comparison delta is the already
suppressed path-scoped large-file entry for this growing lifecycle ledger, while the repository
remains red for inherited gate debt. Findings F-R9-63 (unverified snapshot digest) and F-R9-64 (stale runner
contract assertion) were appended to `/Users/user/Desktop/testing.md`.

Boundary/next: this closes another deterministic provenance false-positive path but does not
prove a live provider response, three distinct served model identities, common raw-span coding,
numeric Fleiss/Krippendorff reliability, grounding, reconciliation, human-Done/report promotion,
two-call/long-horizon behavior, Petals interoperability, or teardown. Commit and push this
checkpoint, verify local/remote parity, then keep G0/G1 `not_run` until the owner-authorized
Mac Studio Docker prerequisites exist. At launch recompute and pass the exact archive digest,
use a fresh detached checkout, and execute provider/Petals/combined G0–G22 in order.

### L-246 | 2026-08-27T02:53:00Z | S5-ship&learn | gpt-5-codex | pushed parity and passive Docker readiness receipt

Did: Transported the source-provenance and runner-contract remediation as commit
`68c5aba7504d7d72ce441f3ac307b5eb09b8471e` to `testing` and `origin/testing`. Local status is
clean and the local, remote, and `HEAD` SHA values are equal; `git diff origin/testing` and
`git diff --check` are clean. Compass Forge task evidence `105` records the parity commands and
the no-host-mutation boundary. After-gate record `129` reports no new dependency, missing-path,
or cycle issues; the only comparison delta is the already path-scoped/suppressed large-file
entry for this lifecycle ledger, with inherited repository debt otherwise unchanged.

Did: Repeated passive SSH/Docker inspection of the Mac Studio using the explicit Docker CLI
path. Docker Server `29.7.2` is reachable, but no Istara benchmark Compose project, testing
network, testing volume, provider, relay, donor, or model container is running. Only the
unrelated healthy `plex` workload is present. The named `/Users/user/istara-testing` checkout
remains at stale SHA `1b9b6d6098dc4a420aff2cf570b9aa5b982b3949`, behind its remote and dirty; it
was not touched. No image pull, model load, service start, host installation, data deletion, or
repository mutation occurred on the Mac Studio.

Boundary/next: deterministic provenance, oracle, authority, Petals contract, and Docker
topology checks are green, but G0/G1 and all live G2–G22 rows remain `not_run`/open. The next
operator must obtain owner-authorized provider credit and three project-scoped served model
routes, re-resolve the launch-time `origin/testing` SHA, create a fresh detached checkout,
compute and pass its exact archive digest, render Compose, and then run provider/Petals/combined
profiles in order. The live result must include three distinct served identities, common raw
spans, numeric Fleiss/Krippendorff metrics, grounding, reconciliation, human-Done/report
promotion, two-call/long-horizon evidence, Petals interoperability, artifact redaction, and
teardown before CF-15 can close.

### L-247 | 2026-08-27T03:00:00Z | S4-remediate | gpt-5-codex | duplicate-rating reliability audit

Did: Audited the Research Spine reliability matrix for a raw-response integrity gap. The
matrix previously merged every application for a coder/evidence-unit pair into one set of
codes. Conflicting duplicate applications could therefore manufacture a multi-label rating
that no model returned, distort Fleiss' Kappa/Krippendorff calculations, and leave contradictory
persisted CodeApplication rows hidden behind a seemingly valid rating.

Changed: `build_binary_coding_matrix()` now counts and exposes duplicate pairs as
`matrix.duplicate_ratings`. `evaluate_reliability_gate()` fails closed with method
`duplicate_rater_applications`, `needs_reconciliation`, and no kappa/alpha before independence,
agreement, or promotion can be evaluated from a synthetic vote. The research-validity contract
and Ensemble Health feature documentation now state the one-rating-per-coder/unit invariant;
the generated feature site/manifest were refreshed. Added a TDD regression with a conflicting
duplicate from one model that proves the gate cannot accept it. Finding F-R9-65 was appended to
`/Users/user/Desktop/testing.md`.

Verified: the duplicate regression is green; the focused Research Spine metrics, coding,
donor-routing, and Pi runtime suites pass (`40` metrics/contract/donor tests and `76` Pi
production tests); the remote-runner contract suite passes (`17` tests); the complete
deterministic benchmark remains `77/77`; feature-doc generation/check remains `86` features and
`224` artifacts; `git diff --check` passes. Compass Forge impact/why were run for the core and
test files, the before-gate baseline was recorded as record `131`, the after-gate was recorded as
record `132`, and task evidence `109` was attached. The after-gate found no new dependency,
missing-path, or cycle findings relative to baseline
(the repository retains inherited gate debt and the path-scoped lifecycle-ledger large-file
comparison).

Boundary/next: duplicate-response integrity is now deterministic and fail-closed, but no live
three-model provider call has run. G0/G1 and live G2–G22 remain `not_run`/open. Commit/push and
verify exact local/origin parity. At the
next live window, use owner-authorized provider credit and three project-scoped routes, resolve
the launch-time SHA, verify its archive digest inside the Docker wrapper, render Compose, then
run provider/Petals/combined profiles with real served identities, common raw spans, numeric
Fleiss/Krippendorff reliability, grounding, reconciliation, human-Done/report promotion,
two-call/long-horizon evidence, Petals interoperability, redacted artifacts, and teardown.

### L-248 | 2026-08-27T03:04:07Z | S5-ship&learn | gpt-5-codex | duplicate-rating hardening transport receipt

Did: Committed the duplicate coder/Evidence Unit reliability hardening and its contract,
regression, feature documentation, and generated-site updates as `f676b0fd464343d16b8b35d1d138d174dd8acb0d`.
Pushed it to `origin/testing`; `testing`, `origin/testing`, and `HEAD` resolve to that exact SHA.
The worktree is clean, `git diff origin/testing --check` and `git diff --check` pass, and no
obsolete registered worktree or safely deletable merged branch was identified.

Did: Performed a passive Docker-only SSH inspection of the Mac Studio after transport. Docker
Server `29.7.2` remains reachable; no Istara benchmark Compose project, testing network, testing
volume, provider, relay, donor, or model container is running. Only the unrelated healthy
`plex` workload is present. The stale dirty `/Users/user/istara-testing` checkout remains
untouched. No image pull, model load, service start, host installation, data deletion, or remote
repository mutation occurred.

Verified: deterministic reliability, Research Spine, Pi runtime, remote-runner contract, and
benchmark checks remain green as recorded in L-247/evidence `109`; Compass Forge after-gate
record `133` reports no new dependency, missing-path, or cycle findings relative to baseline
(only the already suppressed path-scoped lifecycle-ledger large-file comparison remains). Live
three-model provider,
Petals, combined, two-call/long-horizon, and teardown gates remain unrun. The duplicate-rating
fix is transported and parity-verified, but CF-15 is not complete until the owner-authorized
Mac Studio prerequisites exist and G0–G22 produce Docker evidence with three distinct model
identities, common raw spans, numeric Fleiss/Krippendorff metrics, grounding, reconciliation,
human-Done/report promotion, redaction, and teardown.

### L-249 | 2026-08-27T03:18:19Z | S4-remediate | gpt-5-codex | served-model identity audit and fail-closed hardening

Did: Audited whether the Research Spine ensemble can prove the model that actually served each
coder judgment. The Pi runtime included its resolved model in the structured outcome, but the
shared `AgenticDispatcher.structured()` facade dropped that field. `_pi_coder_runner()` then
recorded the requested `model_name` as route evidence, allowing a provider/adapter to return a
different model—or no served identity—without the reliability ledger detecting it. This was a
material provenance/oracle gap for the user's three-model bias-reduction requirement and is
tracked as finding F-R9-66 in `/Users/user/Desktop/testing.md`.

Changed: `StructuredResult` construction now preserves `outcome.model`. The Pi coder runner
requires a non-empty provider-reported model identity equal to the model selected by Pi Model
Management; missing or mismatched identity fails before applications are persisted. Route
evidence now stores the served identity rather than guessing from request parameters. Added
red-to-green regressions for mismatched and missing served identities, dispatcher propagation,
and preserved all W7 coding flows. Updated the Research Spine contract and Ensemble Health
feature documentation, then regenerated the feature site/manifest.

Verified: focused Research Spine/Pi/dispatcher ladder passed `144` tests; W7 + W1 passed `57`;
the complete real-user benchmark check passed `77/77`; remote Docker-runner contract passed
`17/17`; targeted Ruff passed; feature docs check passed for `86` features and `224` generated
artifacts; `git diff --check` passed. Compass Forge after-gate record `135` reports no new
dependency, missing-path, or import-cycle findings; the only new comparison warning is the
existing complexity threshold on the enlarged W7 test file (`1217` lines), while inherited
repository complexity/type/secret-flow debt remains. Task command evidence `110` records these
results.

Boundary/next: this closes the deterministic served-model provenance gap but does not prove live
execution. The changes are not yet transported in this ledger entry: commit and push them, verify
`testing == origin/testing` with a clean worktree, and repeat passive Mac Studio Docker inventory.
G0/G1 and live G2–G22 remain `not_run`/open. The authorized live retake must use a fresh detached
checkout at the launch SHA, verify the archive digest before workload startup, and capture three
distinct provider-served model identities over common raw evidence units, one grounded rating per
model/unit, numeric Fleiss/Krippendorff metrics, grounding, reconciliation, human-Done/report
promotion, both loop-mode semantics, two-call/long-horizon artifacts, Petals interoperability,
redacted artifacts, and teardown without installing or mutating the Mac Studio host.

### L-250 | 2026-08-27T03:19:46Z | S5-ship&learn | gpt-5-codex | served-model hardening transport and Docker readiness receipt

Did: Committed the served-model provenance hardening, regressions, Research Spine contract,
Ensemble Health feature documentation, generated site/manifest, and L-249 checkpoint as
`20906e522d487c3a7a60a3884ee68bb2bc1327f4`; pushed `testing` to `origin/testing`. Verified
`HEAD`, local `testing`, and `origin/testing` resolve to that exact SHA; the worktree and both
diff checks are clean. No obsolete registered worktree or safely deletable merged branch was
identified, and the protected `LLMs/`/`Model_Finetuning/` artifact folders were untouched.

Did: Repeated passive SSH/Docker inspection of the Mac Studio using the explicit Docker CLI
path. Host `users-Mac-Studio.local` and Docker Server `29.7.2` are reachable. No Istara
benchmark Compose project, testing network, testing volume, provider, relay, donor, or model
container is running; only the unrelated healthy `plex` Compose workload is present. The stale
dirty `/Users/user/istara-testing` checkout remains untouched. No image pull, model load,
service start, host package installation, data deletion, or remote repository mutation occurred.

Verified: the pre-transport focused ladder remains `144` tests; W7/W1 `57`; benchmark `77/77`;
remote runner `17/17`; Ruff, feature docs (`86` features/`224` artifacts), and diff checks pass.
Compass Forge after-gate record `136` and task evidence `110` cover the code/docs/tests; no new
dependency, missing-path, or import-cycle issue was introduced. F-R9-66 is appended to
`/Users/user/Desktop/testing.md`.

Boundary/next: deterministic authority, duplicate-rating, oracle, and served-model provenance
contracts are green, but live G0/G1 and G2–G22 remain `not_run`/open. The next operator needs
owner-authorized provider credit and three project-scoped routes, then must resolve the launch
SHA, create a fresh detached checkout, recompute/pass its archive digest, render Compose, and
run provider/Petals/combined profiles in order. Acceptance requires three distinct provider-
served identities over common raw spans, one grounded rating per model/unit, numeric
Fleiss/Krippendorff reliability, grounding, reconciliation, human-Done/report promotion, both
loop-mode semantics, two-call/long-horizon artifacts, Petals interoperability, redacted
artifacts, and teardown, all through Docker without installing or mutating the Mac Studio host.

### L-251 | 2026-08-27T03:27:19Z | S4-remediate | gpt-5-codex | independent served-model benchmark oracle

Did: Audited the real-user Research Spine probe after the PI served-model transport fix. The
probe already required the backend's `distinct_model_count` and counted served donor node IDs,
but it did not independently inspect the model identities in `route_evidence`. That left a
false-positive seam where a malformed adapter could claim three model coders while the route
receipt carried fewer than three actual served identities. This is recorded as finding F-R9-67
in `/Users/user/Desktop/testing.md`.

Changed: `validateCodingRun()` now case-folds and counts non-empty model identities from served
route evidence, requires the recomputed count to meet the requested coder width, and requires it
to equal the backend-reported `distinct_model_count` before reconciliation is attempted. The
blocker payload records the recomputed identity list. Added a regression for a claimed three-model
run with only two served identities; updated accepted and negative fixtures with explicit served
model receipts; updated the Ensemble Health architecture and real-user benchmark contract text.

Verified: the focused research-spine probe passes `21/21`; the complete deterministic real-user
benchmark check passes `78/78`; feature docs generation/check passes (`86` features, `224`
artifacts); `git diff --check` passes. This checkpoint is not transported yet. After the next
gate/evidence receipt, commit and push the oracle and docs, verify exact `testing`/`origin/testing`
parity, and repeat passive Docker inventory. Existing Compass Forge baseline warnings remain
unchanged (including the enlarged W7 test-file complexity warning and inherited repository debt).

Boundary/next: deterministic route/model receipt proof is now stronger, but live G0/G1 and G2–G22
remain `not_run`/open. The next authorized live window still requires a fresh detached checkout
at the launch SHA, canonical archive digest verification inside the Docker wrapper, rendered
Compose, provider/Petals/combined profiles in order, three actual provider-served identities over
common raw spans, one grounded rating per model/unit, numeric Fleiss/Krippendorff reliability,
grounding, reconciliation, human-Done/report promotion, both loop-mode semantics,
two-call/long-horizon artifacts, Petals interoperability, redacted artifacts, and teardown.

### L-252 | 2026-08-27T03:32:51Z | S5-ship&learn | gpt-5-codex | served-model oracle transport and Docker parity receipt

Did: Committed the independent served-model route oracle, explicit model-identity fixtures and
regressions, Ensemble Health/benchmark contract documentation, generated feature site artifacts,
and the L-251 checkpoint as `964eb5a0cb418354d145261048a2fd7789d582fd`; pushed `testing` to
`origin/testing`.

Verified: `HEAD`, local `testing`, and `origin/testing` resolve to that exact SHA; the worktree is
clean and `git diff origin/testing --check` passes. The deterministic evidence remains focused
probe `21/21`, full real-user benchmark `78/78`, Research Spine/Pi ladder `144`, remote runner
`17/17`, Ruff, feature docs (`86` features/`224` artifacts), and Compass Forge after-gate `138`
with no new issues. F-R9-67 is now transported with this receipt.

Verified: passive SSH inspection used the explicit Docker CLI path on `users-Mac-Studio.local`.
Docker Server `29.7.2` is reachable; no Istara containers, networks, volumes, benchmark Compose
project, providers, relays, donors, or model loads are running. Only the unrelated healthy `plex`
Compose workload is present. No model load, image pull, service start, host installation, data
deletion, or remote checkout mutation occurred; the stale dirty `/Users/user/istara-testing`
checkout remains untouched.

Boundary/next: local transport and deterministic gates are complete for this checkpoint, but live
G0/G1 and G2–G22 remain `not_run`/open. Do not claim three-model ensemble or research-spine
acceptance until an owner-authorized Docker-only retake proves provider-served identities, common
source spans, grounded atomic coding, Fleiss/Krippendorff reliability, reconciliation, human-Done
and report gates, both engine-mode semantics, two-call/long-horizon behavior, Petals cooperation,
redaction, and teardown from a fresh detached checkout at the exact launch SHA.

### L-253 | 2026-08-27T03:59:06Z | S4-remediate | gpt-5-codex | provider-served receipt hardening and deterministic retest

Did: Continued the audit beyond the dispatcher boundary and traced provider identity through the
Pi runtime protocol. The endpoint's configured `model` is only a request label; a proxy, gateway,
or relay can serve a different checkpoint. Pi adapter `responseModel` is optional and provider-
dependent, so the runtime now observes streamed provider response frames at the fetch boundary,
preserves the original bytes, and attaches a provider-reported identity to the terminal assistant
message. `run.completed` carries this as optional `served_model`; the Python Pi engine,
dispatcher, route evidence, usage ledger, and formal Research Spine coder keep requested and
served identities separate. Formal coders fail closed when the served receipt is missing or does
not equal the Pi-selected model; ordinary turns remain compatible for providers that do not
expose response identity.

Changed: Added the protocol and architecture contract language, loopback OpenAI-compatible and
Anthropic served-identity assertions, provider-receipt usage-ledger coverage, strict coder fixtures,
and a stale Pi-manager integration fixture update. Appended finding F-R9-68 to
`/Users/user/Desktop/testing.md`. The first broad retest correctly exposed one old test stub that
claimed a configured model without a served receipt; after making the fixture explicit, the full
focused ladder passed `176` tests.

Verified: `npm --prefix pi-runtime test` passed `46/46`; the focused Python provider/structured/
Research Spine/Pi ladder passed `77` tests before the broad run and `176` tests after the stale
fixture correction. Remaining deterministic benchmark, remote-runner, Ruff, feature-doc, diff,
and Compass Forge evidence gates are still to be rerun for this uncommitted checkpoint. No live
provider/model was loaded, no image was pulled, and no host package or Mac Studio repository was
mutated. The Mac Studio remains a passive Docker-only readiness check with no Istara stack.

Boundary/next: this closes the local provider-response provenance gap but does not prove the live
three-model ensemble or the complete Research Spine. Run the remaining deterministic/security/
documentation checks, record fresh Compass Forge command and after-gate evidence, commit and push
the code/tests/contracts/docs plus this checkpoint, verify clean exact `testing`/`origin/testing`
parity, and repeat passive Docker inventory. Keep G0/G1 and live G2–G22 open until an authorized
fresh-detached-checkout retake proves three distinct served models over common raw spans, one
non-duplicate grounded rating per model/unit, numeric Fleiss/Krippendorff reliability,
reconciliation, human-Done/report promotion, both loop modes through Pi Model Management, two-call
and long-horizon behavior, Petals cooperation, artifact redaction, and teardown.

### L-254 | 2026-08-27T04:01:51Z | S5-ship&learn | gpt-5-codex | served-model receipt transport and Docker readiness receipt

Did: Committed the provider-served model receipt implementation, protocol/Research Spine
contract updates, runtime and Python propagation, strict coder gate, integration fixtures,
regressions, generated feature documentation, finding F-R9-68, and L-253 as
`0657c2f3b1f3b9af98a49739223b3459e6eefc9d`; pushed it to `origin/testing`.

Verified: `HEAD`, local `testing`, and `origin/testing` resolve to the exact same SHA; the
worktree is clean; `git diff origin/testing --check`, `git diff --check`, and the runner shell
syntax check pass. The current deterministic evidence is Pi runtime `46/46`, the broad
Research Spine/Pi provider ladder `176` passed, the real-user benchmark `78/78`, remote-runner
contract `17/17`, security benchmark `28/28` at `100%`, touched-file Ruff clean, and feature
documentation `86` features / `224` artifacts. Compass Forge task evidence `112` records the
commands and results; after-gate record `140` reports no new dependency, import-cycle, or
missing-required-path issues. It reports only expected complexity warnings for the enlarged
W7 and Research Validity contract test files plus the existing path-scoped lifecycle-ledger
large-file warning; inherited repository debt remains.

Did: Repeated passive SSH inspection of `users-Mac-Studio.local` with an explicit Docker CLI
path. Docker Server `29.7.2` is reachable; no Istara benchmark Compose project, testing
container, network, volume, provider, relay, donor, or model is running. Only the unrelated
healthy `plex` Compose workload is present. No image pull, model load, service start, host
package installation, testing-data deletion, or remote checkout mutation occurred. The stale
dirty `/Users/user/istara-testing` checkout remains untouched.

Boundary/next: deterministic provider authority, duplicate-rating handling, route/model oracle,
and provider-response provenance are now transported and parity-verified. This does not prove
the live scientific result. G0/G1 and live G2–G22 remain `not_run`/open until owner-authorized
Docker-only execution from a fresh detached checkout at the launch SHA verifies the canonical
archive digest, rendered Compose, three distinct provider-served model identities over common
raw spans, exactly one grounded rating per model/unit, numeric Fleiss/Krippendorff reliability,
reconciliation, human-Done/report promotion, both Istara and Pi loop semantics through the
shared Pi Model Management authority, two-call/long-horizon behavior, Petals cooperation,
redacted artifacts, and teardown.

### L-255 | 2026-08-27T04:03:00Z | S5-ship&learn | gpt-5-codex | final gate and handoff receipt

Verified after transport: Compass Forge after-gate record `141` and task evidence `113` are
attached. The gate comparison has no new dependency, import-cycle, or missing-required-path
issues; only the expected enlarged-test complexity warnings and the path-scoped lifecycle-ledger
large-file warning remain alongside inherited repository debt. The branch is clean and exact
parity is preserved at `632940c571c0a3630ba89d2af337c4292e7614bf`.

The Mac Studio remains passive Docker-only (`users-Mac-Studio.local`, Docker Server `29.7.2`):
only unrelated `plex` is running; no Istara Compose project, containers, networks, volumes,
providers, relays, donors, or models are present. No host installation, model load, image pull,
service start, data deletion, or remote checkout mutation occurred. G0/G1 and live G2–G22 stay
explicitly open for the next authorized retake.

### L-256 | 2026-08-27T04:08:13Z | S5-ship&learn | gpt-5-codex | orphaned Docker test-volume cleanup receipt

Did: Re-inspected the Mac Studio Docker state over SSH using the explicit Docker CLI path and
confirmed that the two anonymous hash-named volumes left by the earlier testing run had no
container references and no Compose ownership. Both contained only PostgreSQL data directories:
`9148cf1b80adc539e6ad9e8d5985b33428d4717bffacf13bf5fcc05c7e323509` (2.9G, created
2026-08-23T18:26:30Z) and `23732a6aa8da4810b7c3853fb4324d825b584687a7f967dab3bd1f54688d289f`
(49.3M, created 2026-08-23T17:29:11Z). The user authorized discarding old testing data, so only
these two demonstrably orphaned anonymous test volumes were removed with `docker volume rm`.

Verified: Docker now reports only the named `pi-agent-home` volume; it was not touched. The only
running container remains the unrelated healthy `plex` service. No image, model, service, host
package, repository checkout, or protected artifact was changed. The removed volume data is not
recoverable from Docker; it was stale test PostgreSQL state and the next live run must initialize
fresh isolated data inside its own Compose project.

Boundary/next: cleanup improves Docker readiness but does not advance scientific proof. G0/G1 and
live G2–G22 remain open. The next live window must use a fresh detached `origin/testing` checkout,
verify the canonical archive digest inside Docker, render Compose, then run provider/Petals/combined
profiles with three actual served identities, common raw evidence spans, grounded non-duplicate
ratings, Fleiss/Krippendorff reliability, reconciliation, human-Done/report promotion, both loop
modes through shared Pi Model Management, two-call/long-horizon artifacts, redaction, and teardown.

### L-257 | 2026-08-27T04:11:20Z | S2-execute/S3-review | gpt-5-codex | live prerequisite audit and blocker receipt

Did: Audited the supported Docker-only three-model runner contract against the Mac Studio state.
The model root `/Users/user/Istara-Projects/models`, mounted read-only inside an Alpine container,
contains no files; a read-only Docker search of `/Users/user` found no `.gguf`, `.safetensors`, or
model-server `Modelfile` artifacts. The Docker image inventory has no llama.cpp/Ollama model image.
The only running workload remains unrelated healthy Plex. A disposable container performed passive
GET checks against the usual host provider/model ports 1234, 11434, 8000, 18112, and 18113; all
returned `Network is unreachable`. No chat request, model load, image pull, service start, or host
installation occurred.

Finding: appended F-R9-69 to `/Users/user/Desktop/testing.md`. The supported wrapper will correctly
fail before Compose/model work because the required Compose-managed Gemma file and both llama.cpp
donor files are absent. The stale dirty `/Users/user/istara-testing` checkout and its old
backend/frontend/provider-stub images are not live model evidence and remain untouched.

Verified: the two orphaned anonymous PostgreSQL volumes were removed in L-256; only named
`pi-agent-home` remains. The repository remains clean after the prior transport commit and no
protected `LLMs/` or `Model_Finetuning/` artifact was touched.

Boundary/next: G0/G1 and live G2–G22 remain open. Before any live claim, an owner-authorized window
must provision three exact model files or three explicit provider routes inside Docker-only scope,
create a fresh detached checkout at `origin/testing`, compute and verify its canonical archive digest,
then run provider, Petals, and combined profiles in order. A deterministic green run cannot replace
this missing runtime provenance.

### L-258 | 2026-08-27T04:12:17Z | S5-ship&learn | gpt-5-codex | blocker receipt gate closure

Verified: Compass Forge before-gate record `144` and after-gate record `145` bracketed the live
prerequisite audit and ledger update. The after comparison reports no new dependency, import-cycle,
missing-required-path, or unexpected-large-file issues; the only current warnings remain inherited
repository complexity debt. The exact transport SHA is `3ed2a1b98b353aa76276039bb65d944c8f178f47`
on `HEAD`, local `testing`, and `origin/testing`, with a clean worktree and clean diff checks.

Boundary/next: this receipt closes the operational audit step, not G0/G1 or live G2–G22. The next
authorized action is a Docker-only fresh-checkout run after the owner supplies or mounts three exact
model artifacts/routes. If those prerequisites remain absent, the correct result is a preflight
blocker with no model load, not a synthetic or stub-backed ensemble claim.

### L-259 | 2026-08-27T04:19:30Z | S2-execute/S3-review | gpt-5-codex | streamed served-identity transport closure

Did: Added the red regression first and reproduced a real transport omission:
`AgenticDispatcher._collect_pi_stream()` preserved the configured `model` but
dropped the Pi terminal event's optional `served_model`. That left ordinary
streamed `chat_turn` results and their usage-ledger accounting unable to carry
provider-response identity, even though structured Research Spine coder paths
already required it fail-closed. The fix preserves `served_model` in the
collector return and therefore in `TurnResult` and `_record_outcome()` model
selection.

Added regressions for explicit served-identity propagation and for both
`engine="legacy"` and `engine="pi"` chat choices against one real
`PiExecutionService`/`PiModelManager` endpoint. The latter deliberately uses
the deterministic faux provider only to prove shared authority and endpoint
admission; it does not claim provider-served identity. The focused dispatcher
suite passes 29/29. Updated the Chat Model Controls architecture contract and
appended finding F-R9-70 to `/Users/user/Desktop/testing.md`. Compass Forge
before-gate record `146` and after-gate record `147` bracketed the change;
the after comparison reports no new dependency, import-cycle, missing-path,
or unexpected-large-file issues.

Boundary/next: this local transport fix does not advance the live scientific
claim. G0/G1 and live G2–G22 remain open pending a fresh detached
`origin/testing` checkout and Docker-only provisioning of three real served
model identities/routes, followed by provider, Petals, and combined retakes
with common raw evidence units, reliability, reconciliation, promotion, both
loop modes, two-call/long-horizon artifacts, redaction, and teardown.

### L-260 | 2026-08-27T04:23:30Z | S5-ship&learn | gpt-5-codex | transport and passive-host receipt

Verified the latest checkpoint is transported cleanly: `HEAD`, local
`testing`, and `origin/testing` all equal `20912188813a5a1c9ee7a58d01ca93c8a0b56509`;
the worktree and `git diff --check` are clean. The pushed commit contains the
streamed served-identity fix, its dispatcher regressions, feature-doc update,
generated site artifacts, and this ledger/finding receipt.

Repeated the passive Docker-only Mac Studio snapshot over SSH. Host is
`users-Mac-Studio.local`, Docker Server `29.7.2`; only unrelated healthy Plex
is running, with no Istara/benchmark/provider/donor/Petals containers,
networks, or volumes. No host installation, model load, image pull, service
start, or repository mutation occurred.

Boundary/next: local contract evidence is green (dispatcher 29/29, Pi runtime
46/46, benchmark 78/78, focused Research Spine/Pi 178 passed, feature docs
86/86, touched Ruff clean), but G0/G1 and live G2–G22 remain open. A future
authorized window must supply three real model artifacts or explicit provider
routes, use a fresh detached `origin/testing` checkout, verify its archive
digest inside Docker, and execute the provider/Petals/combined retakes before
any claim of live ensemble or Research Spine validity.

### L-261 | 2026-08-27T04:28:30Z | S2-execute/S3-review | gpt-5-codex | cross-engine structured authority coverage

Did: Closed a deterministic coverage gap at the Research Spine structured-call
boundary. Existing checks exercised Pi structured output and legacy/Pi
ensemble/chat authority sharing, but no test drove both structured engine
choices through one real `PiExecutionService`/`PiModelManager`. Added a
forced `emit_structured_output` regression for `engine="legacy"` and
`engine="pi"` using one manager-owned endpoint, original-schema revalidation,
and identical accepted output/endpoint/model assertions. The complete
dispatcher suite now passes 30/30; F-R9-71 records the former gap and its
closure in `/Users/user/Desktop/testing.md`.

Boundary/next: this remains deterministic contract evidence, not live model or
scientific validity. G0/G1 and live G2–G22 stay open pending the Docker-only
Mac Studio prerequisite (three real model artifacts or explicit provider
routes), fresh detached source checkout/archive verification, provider/Petals/
combined retakes, and final teardown/parity evidence.

### L-262 | 2026-08-27T04:29:15Z | S5-ship&learn | gpt-5-codex | structured-authority transport and gate receipt

Verified: the structured cross-engine coverage checkpoint is transported as
`4124106c060e5508e614bd6f331bcc68fa4d4e19` on `HEAD`, local `testing`, and
`origin/testing`; `git status --short --branch` is clean and `git diff --check`
passes. The first staging attempt correctly rejected
`/Users/user/Desktop/testing.md` because it is outside the repository; that
append-only findings file remains intentionally external and was not forced
into Git. Repository files were staged and committed without it.

Compass Forge `gate after --task CF-15 --summary` is record `148`: zero new
failures, zero actionable failures, zero cycles, and no new route/type drift.
The only new warning is the expected complexity threshold on the already-large
dispatcher test file; inherited secret-flow/large-file and repository warning
debt remains unchanged.

Boundary/next: this closes deterministic structured-authority coverage and its
transport receipt only. It does not close G0/G1 or live G2–G22. Continue with a
fresh detached `origin/testing` checkout and Docker-only Mac Studio execution
once three real served model identities/routes are supplied; preserve the
preflight blocker if the artifacts/routes remain absent.

### L-263 | 2026-08-27T04:31:10Z | S3-gate/S5-ship&learn | gpt-5-codex | post-commit gate closure

Verified: after the ledger transport commit `487d0ee27943754daa3abf8de2ab1954035d0e13`,
the pinned-native Compass Forge `gate after --task CF-15 --summary` completed as
record `150`. The comparison has `new_issue_count=0`, `new_failures=0`, zero
actionable failures, zero cycles, and no new warnings. Existing failures remain
the inherited `secret_flow` and `unexpected_large_files` checks; existing route
and type drift and repository warning debt are unchanged.

Transport remains exact across `HEAD`, local `testing`, and `origin/testing`,
with a clean worktree and clean diff check. The external findings register was
not staged because `/Users/user/Desktop/testing.md` is outside the repository;
its F-R9-70 wording and F-R9-71 entry remain in place as the audit record.

Boundary/next: deterministic authority and transport gates are closed for this
checkpoint. Research Spine live validity is still unproven: G0/G1 and live
G2–G22 remain open until three real served model identities/routes are mounted
and the provider/Petals/combined Docker-only retakes produce raw, traceable,
reconciled, human-reviewable evidence.

### L-264 | 2026-08-27T04:38:52Z | S2-execute/S3-review | gpt-5-codex | healthy legacy-row admission hardening

Did: Audited the Pi Model Management catalog against the Research Spine
requirement that formal coders be selected from healthy, independent model
identities. `_project_llm_server()` previously projected every non-relay
persisted `LLMServer` row, including rows explicitly marked `is_healthy=False`.
That could let a failed or never-health-checked compatibility row consume a
distinct-model slot before the provider call failed. The manager now rejects
explicitly unhealthy rows before projection; migration doubles without the
field remain compatible. Added a regression proving the unhealthy row is not
admitted and updated projection fixtures to mark their intended rows healthy.

Verified: the focused Pi catalog/authority and dispatcher suites pass `56/56`.
The change is bounded to model admission and its tests/docs; no provider,
model load, Docker service, or host installation occurred. The external
findings register records this as F-R9-72. Feature documentation is being
regenerated before the final gate; G0/G1 and live G2–G22 remain open because
the Mac Studio still lacks the three model artifacts or reachable provider
routes required for a scientific retake.

Boundary/next: run the generated feature-doc check and the broader affected
Research Spine/Pi ladder, then execute Compass Forge after-gate, commit/push
the checkpoint, and re-verify exact `HEAD`/`testing`/`origin/testing` parity.
Do not treat the deterministic 56/56 result as live ensemble validity.

### L-265 | 2026-08-27T04:41:32Z | S2-execute/S3-review | gpt-5-codex | deterministic served-identity oracle repair

The broader affected ladder exposed one more stale deterministic fixture: the
end-to-end three-coder Research Spine test returned an endpoint receipt but no
`served_model`. Under the hardened transport contract that correctly made the
run ineligible for formal model independence and blocked promotion. The test
now reports the explicit served identity it intends to simulate, preserving
the same distinction as the live Pi worker (configured request label versus
provider-served identity).

Verified: the repaired end-to-end, Pi catalog, and dispatcher suites pass
`57/57`; feature-doc generation/check remains green (`86/86`). This is an
oracle repair only: it does not add live provider evidence or relax the
fail-closed production path. The external findings register records the stale
fixture and its correction as F-R9-73. G0/G1 and live G2–G22 remain open.

Boundary/next: run the complete Research Spine/Pi affected ladder once more,
perform touched-file lint/diff checks, run the Compass Forge after-gate, then
commit and push L-264/L-265 with exact branch parity. Preserve the Mac Studio
preflight blocker unless three real model routes/artifacts are supplied.

### L-266 | 2026-08-27T05:01:20Z | S2-execute/S3-review | gpt-5-codex | final deterministic audit and gate-baseline remediation

Did: Completed the final deterministic audit after isolating the persisted
LLMServer health regression into `tests/pi_production/test_pi_model_manager_health.py`
and moving the five-verb dispatcher smoke assertion out of the already-large W1
contract module. The production boundary remains one-directional and fail-closed:
explicit `is_healthy=False` compatibility rows are not projected into the Pi
catalog, relay rows remain excluded, and healthy rows retain capability metadata.
The end-to-end three-coder fixture still carries an explicit provider-served model
identity, so the formal Research Spine oracle cannot mistake a request label for
served evidence.

Verified from the final tree: the affected Python matrix passed `529` tests with
`-W error::RuntimeWarning`; the focused model-manager/dispatcher/Research Spine
slice passed `56`; Pi runtime passed `46/46`; the complete real-user benchmark
check passed `78/78`; topology contracts passed `10/10`; feature documentation
regenerated `224` artifacts and passed `86/86`; touched Ruff checks and
`git diff --check` passed. A reviewed-state Compass Forge baseline was recorded
as gate record `158`; it intentionally includes the pre-existing W1 complexity
warning and the lifecycle-ledger large-file warning so the post-transport
comparison is against the exact reviewed tree rather than a stale pre-relocation
snapshot.

Boundary/next: commit and push the reviewed code, tests, generated feature docs,
and this receipt; verify `HEAD`, local `testing`, and `origin/testing` are exact
and the worktree is clean; then run the post-transport native Compass Forge gate
and append its result. G0/G1 and live G2-G22 remain open. The Mac Studio still
has no model artifacts, provider route, Istara container, or Petals workload, so
no three-model Docker ensemble or scientific Research Spine acceptance claim is
permitted until an authorized fresh detached checkout supplies those prerequisites
and produces raw source-span, three-served-identity, grounded rating, numeric
Fleiss/Krippendorff, reconciliation, human-Done/report, both-loop-mode,
two-call/long-horizon, Petals, redaction, and teardown evidence.

### L-267 | 2026-08-27T05:02:21Z | S3-gate/S5-ship&learn | gpt-5-codex | transported gate receipt

Verified after transport of commit `12d8d251be0976f17b92ec08e338fd2238de73b8`:
the pinned-native Compass Forge `gate after --task CF-15 --summary` is evidence
`125`, with `new_issue_count=0`, `new_failures=0`, no actionable failures, no
cycles, and no new warnings. The global status remains `fail` only because the
repository's inherited inventory is still `31` failures and `209` warnings,
including the established secret-flow, historical complexity, route, and type
drift findings; none is newly attributable to this checkpoint.

Transport is exact across `HEAD`, local `testing`, and `origin/testing`; the
worktree and `git diff --check` are clean. The external findings register at
`/Users/user/Desktop/testing.md` remains append-only and intentionally outside
the repository. The Mac Studio was not started or mutated: passive Docker
inspection still shows only the unrelated healthy Plex container, no Istara or
Petals workload, and no provider/model routes or artifacts.

Boundary/next: deterministic contracts and their transport are complete for this
checkpoint, but the live scientific gate is not. Keep G0/G1 and live G2-G22 open
until a future authorized Docker-only run from a fresh detached `origin/testing`
checkout verifies archive provenance, Compose isolation, three distinct
provider-served model identities over common raw source spans, one grounded
non-duplicate rating per model/unit, numeric Fleiss/Krippendorff reliability,
reconciliation, human-Done/report promotion, both loop modes through shared PI
Model Management, two-call/long-horizon behavior, Petals interoperability,
redacted artifacts, and teardown.

### L-268 | 2026-08-27T05:17:34Z | S2-execute/S3-review/S5-ship&learn | gpt-5-codex | provider-served ensemble oracle repair and transport receipt

Did: Audited the response-level ensemble adapter after the prior streamed
provider-receipt work. `_dispatch_ensemble()` was still reading the
configured/request `sample.model` field when constructing `models_used` and
route evidence. In the Pi contract that field is not proof of the checkpoint
that answered: provider-reported identity is carried separately as
`sample.served_model`. Distinct endpoint aliases or gateways could therefore
be counted as independent models even when all responses came from one
checkpoint, overstating MoA diversity and weakening the Research Spine
independence oracle.

Changed: the adapter now consumes `served_model` only and leaves missing
receipts unproven. Added a regression with three different configured labels
and one shared served identity; the resulting `models_used` and route
evidence correctly collapse to the shared provider identity. Updated the
Ensemble Health architecture contract and regenerated the feature-site
artifacts. Appended F-R9-74 to `/Users/user/Desktop/testing.md`; that findings
register remains intentionally external to Git.

Verified: the broad deterministic Python matrix passed `687` tests with `5`
skipped under `-W error::RuntimeWarning`; the focused validation/MoA slice
passed `57/57`; Pi runtime passed `46/46`; the complete real-user benchmark
check passed `78/78`; topology contracts passed `10/10`; touched Ruff and
`git diff --check` passed; feature documentation regenerated `224` artifacts
and passed `86/86`. Compass Forge after-gate record `163` reports
`new_issue_count=0`, `new_failures=0`, no actionable failures, no cycles, and
no new warnings; the global `fail` status remains inherited repository debt
(`31` failures/`209` warnings, including known secret-flow, complexity,
route/type drift, and large-file findings). Commit `fc0a756f` is pushed and
`HEAD`, local `testing`, and `origin/testing` are exact; the repository
worktree is clean after this receipt is transported.

Boundary/next: this closes the deterministic response-level identity oracle
gap but does not prove formal Fleiss/Krippendorff coding or live scientific
validity. Keep G0/G1 and live G2-G22 open. The next authorized live window
must use a fresh detached `origin/testing` checkout, verify its canonical
archive digest inside Docker, and run provider/Petals/combined profiles with
three actual provider-served identities over common raw source spans, one
grounded non-duplicate rating per model/unit, numeric reliability,
reconciliation, human-Done/report promotion, both Istara and Pi loop modes
through shared Pi Model Management, two-call/long-horizon artifacts, Petals
interoperability, redacted artifacts, and teardown. The Mac Studio currently
has no model artifacts or reachable provider routes, so no model load or
three-model claim is permitted.

### L-269 | 2026-08-27T05:23:26Z | S2-execute/S3-review/S5-ship&learn | gpt-5-codex | shared governed-width documentation receipt

Did: Audited the living Ensemble Health contract against the implementation
and deterministic tests. The document still described an obsolete legacy-only
optional-spare retry, although the migration intentionally routes both Istara
(legacy) and Pi engine choices through Pi Model Management. The shared manager
resolves exactly the governed minimum; it has no spare-retry loop. Updated the
feature contract and generated site artifact to state that `n=min+1` is only a
compatibility request, that both engines use the governed minimum, and that
partial valid responses downgrade instead of claiming `full_ensemble`.
Appended F-R9-75 to `/Users/user/Desktop/testing.md`; the findings register
remains append-only and external to Git.

Verified: feature documentation regenerated `224` artifacts and passed
`86/86`; the preceding deterministic receipt remains `687 passed, 5 skipped`
under `-W error::RuntimeWarning`, with Pi runtime `46/46`, benchmark `78/78`,
topology `10/10`, Ruff, and diff checks clean. Compass Forge after-gate
record `167` reports `new_issue_count=0`, `new_failures=0`, no actionable
failures, no cycles, and no new warnings. Commit `d69c4887` is pushed and
`HEAD`, local `testing`, and `origin/testing` are exact; the worktree is
clean. The global gate remains `fail` only for inherited repository debt.

Boundary/next: this corrects documentation/test-contract drift only. G0/G1
and live G2-G22 remain open. The next authorized live window still requires a
fresh detached `origin/testing` checkout, in-container archive verification,
provider/Petals/combined profiles, three distinct provider-served identities
over common raw spans, grounded non-duplicate coding, numeric
Fleiss/Krippendorff reliability, reconciliation, human-Done/report promotion,
both loop modes through shared Pi Model Management, two-call/long-horizon
artifacts, Petals interoperability, redaction, and teardown. The Mac Studio
currently has no model artifacts or reachable provider routes, so live claims
remain prohibited.

### L-270 | 2026-08-27T05:24:39Z | S3-gate/S5-ship&learn | gpt-5-codex | terminal parity and final gate receipt

Verified after the shared governed-width documentation transport: native
Compass Forge before-gate record `168` established the reviewed-tree
baseline, and after-gate record `169` reports `new_issue_count=0`,
`new_failures=0`, no actionable failures, no cycles, and no new warnings.
The global gate remains `fail` only for inherited repository debt (31
failures/209 warnings and known route/type drift, complexity, secret-flow,
and large-file findings). At gate time, the reviewed code/docs transport tip
was `cfc804853c78044b527750a6cabc9d7f1019aa17`; this receipt is transported
immediately afterward and the final parity is verified by the commit carrying
this entry on `HEAD`, local `testing`, and `origin/testing`; the worktree,
`git diff --check`, and
`git diff origin/testing --check` are clean.

The final passive SSH snapshot is still Docker-only on
`users-Mac-Studio.local` with Docker Server `29.7.2`: only unrelated healthy
Plex is running; there are no Istara/Petals/benchmark containers or networks,
and only the retained named `pi-agent-home` volume. No host installation,
model load, image pull, service start, or repository mutation occurred.

Boundary/next: all locally provable deterministic oracle, authority,
provenance, health-admission, documentation, transport, and gate work in this
window is complete. G0/G1 and live G2-G22 remain explicitly open. Resume only
when an authorized Docker-only window supplies three model artifacts or
reachable provider routes; then use a fresh detached `origin/testing` checkout,
verify its archive digest inside Docker, run provider/Petals/combined profiles,
and retain raw source-span, three-served-identity, grounded rating, numeric
Fleiss/Krippendorff, reconciliation, human-Done/report, both-loop-mode,
two-call/long-horizon, Petals, redaction, and teardown evidence. Until those
prerequisites exist, a deterministic green suite cannot be reported as live
three-model Research Spine acceptance.

### L-271 | 2026-08-27T05:31:52Z | S2-execute/S3-review/S5-ship&learn | gpt-5-codex | served-identity admission hardening

Did: Re-audited the live benchmark driver after the terminal parity receipt and found a
remaining false-positive seam. Ordinary one-call units went directly from
`_capture_from_outcome()` to a successful record without approved-route admission, and
the MoA admission compared the configured `sample.model` label instead of the
provider-reported `served_model`. A proxy substitution, endpoint mismatch, or missing
receipt could therefore look like an approved model. Hardened
`tests/pi_benchmark/live_driver.py` so plain and MoA units share fail-closed route
admission, require an explicit served-model identity, reject non-DeepSeek served
identities on the approved DeepSeek route, and admit projected `pi-petals-*` routes
only with a non-empty identity and Petals provider marker. Updated the affected fake
provider responses and added regressions for missing identity, configured-versus-served
mismatch, both engine arms, Petals slots, and raw capture.

Verified: benchmark/production contract slice `274 passed, 5 skipped`; feature docs
regenerated `224` artifacts and passed `86/86`; `git diff --check` is clean. F-R9-76
was appended to `/Users/user/Desktop/testing.md`. The live scientific boundary is
unchanged: G0/G1 and live G2-G22 remain open because the Mac Studio still has no
owner-supplied model artifacts or reachable provider routes. No host installation,
model load, image pull, service start, or remote repository mutation occurred.

The native Compass Forge before-gate is record `170`. Its comparison baseline contains
no new failures, cycles, or forbidden dependencies; it reports the touched benchmark
driver/test complexity thresholds and the existing repository-wide debt as warnings.
Those warnings are retained as explicit gate debt rather than expanded into an
unrelated refactor in this identity-admission patch; the after-gate must show zero
additional delta.

Boundary/next: run the full deterministic matrix and native before/after gate for this
receipt, commit/push exact `testing` parity, then remain at G0/G1 until the authorized
Docker-only Mac Studio retake can prove three actual served identities over common raw
spans, formal Fleiss/Krippendorff reliability, grounding, reconciliation,
human-Done/report promotion, both loop modes through shared Pi Model Management,
two-call/long-horizon behavior, Petals interoperation, redacted artifacts, and clean
teardown.

### L-272 | 2026-08-27T05:38:13Z | S5-ship&learn | gpt-5-codex | post-gate receipt and continuation boundary

Did: completed the post-change Compass Forge gate and recorded the final transport
boundary. Native after-gate record `171` reports `comparison.new_issues=[]`, with no
new forbidden dependencies, Python import cycles, missing required paths, or
unexpected large files beyond the already-suppressed ledger artifact. The repository-
wide gate remains globally `fail` only because of inherited secret-flow, route/type,
complexity, and large-file debt; none was introduced by this patch. The code, tests,
and generated feature documentation covered by the gate are at `f56aaf6c` (`test
benchmark served-model route admission`). The ledger-only receipt is intentionally
appended after that gate; final parity is verified after its commit.

Evidence: deterministic Python matrix `689 passed, 5 skipped` using
`python -m pytest -q -W error::RuntimeWarning tests/pi_production tests/pi_benchmark
tests/test_research_validity_contract.py tests/test_research_spine_end_to_end.py
tests/test_validation_project_scope.py`; Pi runtime `46/46`; real-user benchmark
checks `78/78`; topology contract `10/10`; Ruff clean on the touched benchmark files;
`git diff --check` clean. Feature documentation regenerated `224` site artifacts and
passed `86/86` checks. F-R9-76 is present in `/Users/user/Desktop/testing.md`.

Operational boundary: the Mac Studio inspection remained Docker-only. It still has no
Istara, Petals, or benchmark containers/networks, no owner-supplied model artifacts,
and no reachable provider routes; only unrelated healthy Plex and retained
`pi-agent-home` remain. No host installation, model load, image pull, service start,
or remote repository mutation occurred. Therefore deterministic acceptance is not
live three-model Research Spine acceptance: G0/G1 and live G2-G22 stay open.

Next owner/agent action: start only in an authorized Docker-only window from a fresh
detached `origin/testing` checkout; verify the archive digest inside Docker; then run
provider, Petals, and combined profiles with three distinct provider-served identities
over identical raw source spans. Preserve raw-span receipts, grounded ratings,
numeric Fleiss and Krippendorff reliability, reconciliation and accepted-atom gates,
human-Done/report promotion, both Istara and Pi Agentic Loop modes through shared Pi
Model Management, two-call and long-horizon traces, Petals donation/use/revoke scope,
redaction, and teardown evidence before closing the Research Spine claim.

### L-273 | 2026-08-27T05:45:31Z | S2-execute/S3-review/S5-ship&learn | gpt-5-codex | Docker-only topology documentation correction

Did: corrected a remaining procedure/documentation contradiction in `TESTING.md` and
the compute/pool feature contract. Both pages still described the canonical
three-model probe as host-managed (Istara/admin/LM Studio on Mac Studio with Colima
donors), despite the enforced Docker-only wrapper, topology contract, benchmark
README, and owner instruction that the Mac Studio host must never receive package,
model, or server installs. The active contract now states that Compose and disposable
nested-Docker containers own Istara, admin, simulated researchers, and all donors;
Mac Studio is only the Docker host and SSH control plane. It also requires
pre-provisioned read-only model files and explicitly refuses host-managed Istara,
weight downloads, host package installation, and Colima management. F-R9-77 records
the finding in `/Users/user/Desktop/testing.md`.

Verified: `python scripts/feature_docs.py --seed-missing --generate-site --check`
reported `seeded 0`, `generated 224 site artifact(s)`, and `feature docs check passed
for 86 feature(s)`; the Docker topology contract passed `10/10`; the real-user
benchmark check passed `78/78`; and `git diff --check` was clean. Native Compass Forge
before-gate record `172` reports no new issues, forbidden dependencies, import cycles,
or missing required paths; the only new large-file observation is the already-scoped
Build Stream ledger suppression. The global gate remains failed only for inherited
secret-flow, route/type, complexity, and large-file debt. No runtime or generated
application behavior changed and no live service/model was started.

Boundary/next: this receipt is still pre-transport. Commit and push the corrected
sources, generated feature site, and this ledger entry, then run the native after-gate
and append its final receipt. G0/G1 and live G2-G22 remain open: the Mac Studio still
needs a fresh detached exact-SHA checkout, in-container archive verification, approved
provider/Petals/combined topology, three distinct provider-served identities over
common raw spans, grounded non-duplicate coding, numeric Fleiss/Krippendorff
reliability, reconciliation, human-Done/report promotion, both loop modes through
shared Pi Model Management, two-call/long-horizon traces, redaction, and teardown.

### L-274 | 2026-08-27T05:46:15Z | S5-ship&learn | gpt-5-codex | post-gate transport receipt

Verified after transport: native Compass Forge after-gate record `173` reports
`comparison.new_issues=[]`, with no new forbidden dependencies, Python import cycles,
missing required paths, or actionable warnings introduced by the documentation patch.
The global gate remains `fail` only for inherited repository debt (secret-flow,
route/type, complexity, and large-file findings); the Build Stream ledger's scoped
large-file suppression remains the only expected delta. Commit `29c41984` is now
pushed to `origin/testing`; the final parity check confirms `HEAD`, local `testing`,
and `origin/testing` are identical and the worktree is clean.

The transported change corrects `TESTING.md` and the compute/pool feature source plus
its generated site/manifest so the supported three-model benchmark is explicitly
Docker-owned and host-managed execution is refused. F-R9-77 is present in
`/Users/user/Desktop/testing.md`. Verification remains deterministic/documentary:
feature docs `224` artifacts/`86` checks, topology contract `10/10`, and real-user
benchmark check `78/78`; no Mac Studio service, model, package, or remote repository
was started or mutated.

Boundary/next: G0/G1 and live G2-G22 remain open. The next meaningful action is an
owner-authorized fresh detached exact-SHA checkout on Mac Studio, archive verification
inside Docker, then provider/Petals/combined retakes with three distinct
provider-served identities over common raw spans and complete reliability, grounding,
reconciliation, Done/report, both-loop, two-call/long-horizon, Petals, redaction, and
teardown evidence. Do not promote this deterministic/documentation receipt to live
Research Spine acceptance.

### L-275 | 2026-08-27T06:08:53Z | S2-execute/S3-review | gpt-5-codex | shared Pi authority benchmark seam correction

Did: audited the live benchmark against the post-migration dispatcher graph and found
that `tests/pi_benchmark/live_driver.py` still seeded and approved the retired
`benchmark-deepseek-registry` for the legacy/Istara arm, while production
`AgenticDispatcher._legacy_outcome` injects the same `PiExecutionService` used by the
Pi arm. This would reject a real legacy result served from `pi-deepseek-default` and
made existing fakes prove the wrong authority. The driver now pins
`pi-deepseek-default` for both engine labels, admits the same approved Pi/Petals route
policy for both, removes live registry seeding, and leaves `engine="legacy"` as
loop-semantics selection only. Legacy/raw-capture fixtures now carry explicit
endpoint/provider/served-model receipts. The registry helper is documented as
compatibility-only isolated test support.

Verified: the red regression before implementation failed with
`RouteAdmissionError: benchmark route not approved: 'pi-deepseek-default'`; targeted
benchmark/registry/raw-capture tests passed `41`; the full benchmark package passed
`233 passed, 5 skipped`; Pi production passed `419`; Research Spine contract passed
`32`; end-to-end passed `1`; validation scope passed `4`; feature docs regenerated
`224` site artifacts and passed `86/86`; Ruff and `git diff --check` were clean.
Native Compass Forge before-gate reports `actionable_failures=[]` and
`new_failures=0`; two nonblocking complexity warnings are recorded for the large
benchmark driver/test files.

Boundary/next: run the after-gate, append F-R9-78 and its remediation evidence to
`/Users/user/Desktop/testing.md`, commit and push exact testing/origin parity, and
keep live G0/G1/G2-G22 open until an authorized Docker-only Mac Studio retake proves
three distinct provider-served identities, common raw spans, grounding,
Fleiss/Krippendorff reliability, reconciliation, human-Done/report promotion, both
loop modes, two-call/long-horizon behavior, Petals scope, redaction, and teardown.

### L-276 | 2026-08-27T06:12:00Z | S3-gate/S5-ship&learn | gpt-5-codex | benchmark authority after-gate

Verified: native Compass Forge `gate after --summary` completed with
`actionable_failures=[]`, `new_failures=0`, `comparison.new_issue_count=0`, and
`new_warnings=[]`. The global gate remains `fail` with `31` inherited findings in
the repository-wide secret-flow, route/type, complexity, and large-file checks;
the current correction introduced no new issue. The benchmark-authority finding
F-R9-78 is recorded in `/Users/user/Desktop/testing.md`.

Boundary/next: commit and push the intended benchmark driver/tests, compatibility
fixture clarification, generated manifest, and this ledger receipt; then verify
`HEAD == testing == origin/testing` and a clean worktree. Live G0/G1/G2-G22 remain
open pending the authorized Docker-only Mac Studio retake and complete Research
Spine evidence.

### L-277 | 2026-08-27T06:12:25Z | S5-ship&learn | gpt-5-codex | exact testing transport parity

Verified: commit `67bb93616f31d5ea692eb8a66eafbe4efd52cf1d` containing the benchmark
authority correction, compatibility-fixture clarification, generated manifest, and
Build Stream/F-R9-78 receipts is pushed to `origin/testing`. Local `testing`, `HEAD`,
and `origin/testing` resolve to the same SHA; `git diff origin/testing...HEAD --stat`
is empty and the worktree is clean. No branches or worktrees were deleted: the
recovery checkout is intentionally divergent and remains preserved.

Boundary/next: deterministic implementation and audit work for this slice is
complete. Live acceptance is deliberately not claimed. The next agent must obtain
owner authorization for a Docker-only Mac Studio run, start only disposable Compose
and nested-Docker services from this exact SHA, and retain the full G0/G1/G2-G22
Research Spine evidence bundle: three provider-served identities over common raw
spans, independent grounded coding, Fleiss/Krippendorff numbers, reconciliation,
human-Done/report promotion, both Istara and Pi Agentic Loop choices through shared
Pi Model Management, two-call/long-horizon traces, Petals scope, redaction, and
teardown.

### L-278 | 2026-08-27T07:02:00Z | S2-execute/S3-review | gpt-5-codex | real-dispatcher Research Spine coverage closure

Did: Re-audited the positive W7 Research Spine coding fixture against the actual
runtime graph. The prior test constructed a real ``PiModelManager`` but replaced
the process-wide ``AgenticDispatcher`` with a hand-written recording double. That
proved selection, persistence, Fleiss/Krippendorff promotion, and route assertions,
but it did not prove that the real dispatcher receives the paired Pi service,
normalizes the explicit ``engine="pi"`` choice, invokes the structured verb, or
keeps its usage-accounting boundary around the coding call. Existing W1 tests cover
the real supervised Node worker and forced structured protocol, but not this full
service-to-dispatcher-to-coding-run seam.

Changed: ``tests/pi_production/test_w7_pi_manager_integration.py`` now instantiates
the production ``AgenticDispatcher``. Its Pi service remains a deterministic,
non-networked provider seam that exposes the same manager and returns a schema-valid
object plus an explicit provider-served model receipt. The test therefore verifies
that all three manager-selected endpoint/model identities reach
``purpose="validity.coder"`` through the real dispatcher before the Research Spine
accepts the run. ``docs/features/content/findings/codebook/architecture.md`` and
the generated feature manifest/site now name this coverage explicitly.

Verified: the focused new test passed; W1/W7/research-validity slice passed
``63 passed in 70.32s``; feature documentation regenerated ``224`` artifacts and
passed ``86/86`` checks; Ruff and ``git diff --check`` are clean. Native Compass
Forge before-gate record ``176`` reports no new issues, cycles, forbidden
dependencies, or missing paths; the repository-wide failure remains inherited
secret-flow, route/type, complexity, and large-file debt, with the ledger's known
large-file suppression. The deterministic provider receipt is intentionally not a
live model claim.

Boundary/next: run the native after-gate, append the matching F-R9-79 finding to
``/Users/user/Desktop/testing.md``, commit and push the test/docs/ledger receipt,
verify exact ``HEAD == testing == origin/testing`` parity, and keep G0/G1 and live
G2-G22 open. A future authorized Docker-only Mac Studio window must still prove
three actual provider-served identities over common raw spans, grounded independent
coding, numeric Fleiss/Krippendorff reliability, reconciliation, human-Done/report
promotion, both loop choices through shared Pi Model Management, two-call and
long-horizon behavior, Petals cooperation/scope/revocation, redaction, and teardown.

### L-279 | 2026-08-27T07:08:00Z | S3-gate/S5-ship&learn | gpt-5-codex | real-dispatcher coverage transport parity

Verified: native Compass Forge `gate after --summary` completed with
`actionable_failures=[]`, `new_failures=0`, `comparison.new_issue_count=0`, and
`new_warnings=[]`. The global gate remains `fail` with `31` inherited findings
across secret-flow, route/type, complexity, and large-file checks; this correction
introduced no new issue. Ruff and `git diff --check` are clean.

Commit `8937d50d` is pushed to `origin/testing`. It contains the real
`AgenticDispatcher` W7 coding-run coverage correction, the codebook feature-doc
test reference and generated site/manifest, and this Build Stream receipt. The
external F-R9-79 finding is appended to `/Users/user/Desktop/testing.md`.
The exact parity check confirms `HEAD`, local `testing`, and `origin/testing` all
resolve to `8937d50d`, with no diff and no dirty worktree. No branches or
worktrees were deleted; the divergent recovery checkout remains intentionally
preserved.

Boundary/next: deterministic implementation and audit work for this coverage slice
is complete. Live acceptance is deliberately not claimed. G0/G1 and live G2-G22
remain open until an owner-authorized Docker-only Mac Studio window starts only
disposable Compose/nested-Docker services from this exact SHA, verifies the archive
digest in-container, and captures three actual provider-served identities over
common raw spans, grounded independent coding, numeric Fleiss/Krippendorff
reliability, reconciliation, human-Done/report promotion, both Istara and Pi
Agentic Loop choices through shared Pi Model Management, two-call/long-horizon
traces, Petals cooperation/scope/revocation, redaction, and teardown.

### L-280 | 2026-08-27T07:12:00Z | S5-ship&learn | gpt-5-codex | passive Mac Studio Docker boundary recheck

Verified: the remote SSH inspection remained strictly passive and Docker-only.
`users-Mac-Studio.local` reports Docker Server `29.7.2`; the only running
container is unrelated healthy `plex` (`plexinc/pms-docker:latest`, up four days),
and the only named volume is the retained `pi-agent-home`. There are still no
Istara, Petals, benchmark, donor, or test containers/networks, and no host
processes or model artifacts available for the requested live retake. No package,
model, image, service, or repository mutation was performed on the Mac Studio.

The local parity check remains clean at `d8550aba`: `HEAD`, `testing`, and
`origin/testing` are identical and the worktree has no changes. Deterministic
Research Spine/authority work is therefore safely handed off; live G0/G1 and
G2-G22 remain pending the owner-authorized Docker-only prerequisites documented
above.

### L-281 | 2026-08-27T07:16:00Z | S5-ship&learn | gpt-5-codex | final resumability checkpoint

The top Build Stream status now avoids pinning the handoff to an older
implementation SHA: the latest commits include ledger-only receipts, while the
tested code correction is already transported and the branch remains clean. The
next agent should read L-278 through L-280, inspect the exact pushed tip with
`git rev-parse HEAD testing origin/testing`, and treat live G0/G1/G2-G22 as open
until the owner authorizes the Docker-only Mac Studio retake. No further code or
remote-host action was taken in this checkpoint.

### L-282 | 2026-08-27T07:31:00Z | S2-execute/S3-review | gpt-5-codex | legacy served-identity seam audit

Did: audited the remaining cross-engine multi-turn boundary after L-281. The
existing W1 parity test covered only one plain turn for each engine, while the
legacy Istara ReAct loop had no regression proving that multiple provider rounds,
tool-result history, cumulative usage, and provider identity all survive the
shared Pi Model Management authority. Added a deterministic W1 test using a real
`PiModelManager` and a stateful provider seam: two `create_task` tool rounds,
then a final response, with one manager resolution per round and explicit
`served_model` receipts.

The first red run exposed a production bug rather than a test-fixture issue:
`legacy.py` retained the provider identity only in route evidence and the
dispatcher therefore returned `TurnResult.served_model=None`. The remediation
now transports an explicit `served_model` through the legacy outcome and route
receipt while preserving the configured/request `model` separately. A provider
that reports only its configured label remains unverified; the existing plain
faux-provider parity test is retained as that negative control. Added the
behavior to the Ensemble Health and Chat Model Controls living feature docs and
regenerated the generated site/manifest.

Verified locally: focused W1/W7/Pi-manager/Research-Spine slice passed `90
passed` with `RuntimeWarning` promoted to errors; Ruff and `git diff --check`
passed; feature docs reported `224` generated artifacts and `86/86` checks.
No server, model, provider, or Mac Studio host process was started. The finding
is recorded as F-R9-80 in `/Users/user/Desktop/testing.md`.

Boundary/next: run the native Compass Forge before/after gates for this code and
docs change, then commit and push exact `testing == origin/testing` parity. Keep
G0/G1 and live G2-G22 open: deterministic coverage still cannot prove live
three-checkpoint independence, per-turn route receipts through a real gateway,
two-call continuity for both HTTP engine choices, long-horizon recovery/timeout
semantics, Petals/PI combined operation, or end-to-end Research Spine
grounding/reconciliation/Fleiss/Krippendorff/Done-report evidence. The Mac Studio
must remain Docker-only and passive until an owner-authorized retake window with
exact source/model/provider prerequisites.

### L-283 | 2026-08-27T07:36:00Z | S5-ship&learn | gpt-5-codex | legacy identity receipt transport checkpoint

The native Compass Forge after-gate for the L-282 implementation completed with
`actionable_failures=[]`, `new_failures=0`, `comparison.new_issue_count=0`, and
`new_warnings=[]`. The global gate remains `fail` only because the repository still
has `31` inherited findings (including secret-flow, route/type, complexity, and
large-file debt); this change introduced no actionable or new failure.

Commit `3ccc498f` (`fix: preserve legacy provider identity receipts`) is pushed to
`origin/testing`. It contains the legacy outcome/route-receipt correction, the
cross-engine multi-turn W1 regression, living feature-doc updates, generated site
artifacts, and L-282. The external finding F-R9-80 is present in
`/Users/user/Desktop/testing.md`. The pre-ledger transport check confirmed
`HEAD == testing == origin/testing` at `3ccc498f`, with an empty diff and clean
worktree after the push; this ledger-only receipt will be transported in the next
small commit and parity will be rechecked afterward.

Deterministic evidence remains bounded: the W1/W7/Pi-manager/Research-Spine slice is
`90 passed`, the legacy real-path/ASGI/worker subset is `14 passed`, feature docs are
`224` generated artifacts with `86/86` checks, and Ruff plus `git diff --check` are
clean. No server, model, provider, or Mac Studio host process was started.

Open acceptance is unchanged. G0/G1 and live G2-G22 remain open until an
owner-authorized Docker-only Mac Studio run from the exact pushed SHA proves actual
three-model provider-served identity over common raw spans, independent grounded
coding, numeric Fleiss/Krippendorff reliability, reconciliation, Done/report gates,
both Istara and Pi Agentic Loop HTTP choices through shared Pi Model Management,
two-call continuity, long-horizon/recovery semantics, Petals cooperation/scope/
revocation, redaction, and teardown. The deterministic full-chain test still uses a
controlled coder dispatcher, so it is an oracle/contract test rather than live model
quality evidence.

### L-284 | 2026-08-27T07:44:00Z | S2-execute/S3-review | gpt-5-codex | cross-engine HTTP continuity audit

The two-call real-ASGI continuity test was audited against the actual production
seams. It had covered only the native Pi engine and asserted worker session-open
history, leaving the selectable Istara/legacy HTTP path unproven. A first
parameterized attempt intentionally went red for legacy because that bridge opens a
short-lived provider-only worker session with an empty session history; its persisted
conversation is supplied in the `provider.turn` message list instead. This was a
test-oracle mismatch, not a production history-loss finding.

The test now covers both request headers (`pi` and `legacy`) after a worker restart.
Pi asserts the DB-rehydrated user/assistant history passed to the native worker
session. Legacy records the actual provider-turn messages and asserts the same
persisted history plus the new user message. Both calls also require successful SSE
completion and usage rows stamped with the selected engine, so the test proves
continuity and route selection without forcing the two loops to share an internal
state model. The Chat Model Controls feature contract now references this coverage
and the generated site/manifest were regenerated.

Verified locally: `python -m pytest -q -W error::RuntimeWarning
tests/pi_production/test_chat_pi_asgi.py tests/pi_production/test_w1_dispatcher_authority.py`
passed `36 passed`; Ruff and prior focused dispatcher/Research-Spine slices remain
green. External finding F-R9-81 records the gap, the red oracle attempt, the seam
correction, and its limits. No server, model, provider, or Mac Studio host process
was started.

Boundary/next: this closes deterministic HTTP two-call coverage for both engine
choices, but G16 remains open for live provider/session evidence. G17 remains open
because long-horizon coverage is still Pi-worker-only, task-tool-only, and lacks a
live provider, Research Spine source/evidence tools, recovery/timeout assertions,
and legacy HTTP execution. G0/G1 and live G2-G22 remain open for the authorized
Docker-only Mac Studio retake and exact source/model/provider prerequisites.

### L-285 | 2026-08-27T08:02:00Z | S2-execute/S3-review | gpt-5-codex | legacy horizon parity and complexity-safe test placement

The deterministic horizon audit found that the Pi worker had a seven-tool-call
long-horizon oracle, but the user-selectable Istara/legacy loop did not have a
matching proof through the shared Pi Model Management authority. Added
`tests/pi_production/test_legacy_long_horizon.py`, an isolated real-dispatcher
regression that drives seven canonical `create_task` rounds and a terminal
answer through one manager-owned endpoint. It asserts one manager resolution per
provider turn, exact eight-turn cumulative usage (`8/8/16`, `turns=8`), explicit
configured versus served identity, and the complete assistant/tool history at
the final provider turn. No runtime code changed; this closes a deterministic
coverage gap only.

The first pre-gate after adding the test exposed a new complexity warning on the
already hotspot-heavy W1 authority module. The test was moved out of that module
before transport so the existing file remains byte-identical and the new oracle
does not add process debt. Post-gate verification reports `actionable_failures=[]`,
`new_failures=0`, `comparison.new_issue_count=0`, and `new_warnings=[]`; the global
gate remains `fail` with its inherited `31` findings and `209` warnings. Ruff,
`git diff --check`, and feature docs generation (`224` artifacts, `86/86` checks)
pass. The focused W1/worker/ASGI run passes `40`; the adjacent provider,
scenario, worker, validation, and Research Spine slice passes `81` with runtime
warnings promoted to errors.

The external finding F-R9-82 is appended to `/Users/user/Desktop/testing.md`.
Transport is the next bounded action; after parity is rechecked, the remaining
boundary is unchanged: deterministic fakes do not prove live three-checkpoint
served identity, source-grounded independent coding, numeric Fleiss/Krippendorff
reliability, reconciliation, human-Done/report promotion, HTTP long-horizon
recovery/timeout semantics, Petals cooperation/scope/revocation, redaction, or
teardown. G0/G1 and live G2-G22 remain open pending the owner-authorized
Docker-only Mac Studio window.

### L-286 | 2026-08-27T08:12:00Z | S3-gate/S5-ship&learn | gpt-5-codex | legacy horizon transport parity

Commit `e3a31c91` (`test: cover legacy long-horizon parity`) is pushed to
`origin/testing`. It contains the isolated legacy horizon oracle, the three
living feature-doc references/architecture notes, regenerated site/manifest
artifacts, and this Build Stream receipt. The external F-R9-82 finding is
appended to `/Users/user/Desktop/testing.md`.

Transport verification is exact and clean: `HEAD`, local `testing`, and
`origin/testing` all resolve to `e3a31c91693666d8c10dec0d3861fb2d42dc8331`;
`git diff --check` is clean and there are no uncommitted files. The final native
Compass Forge after-gate reports `actionable_failures=[]`, `new_failures=0`,
`comparison.new_issue_count=0`, and `new_warnings=[]`. The repository-wide gate
status remains `fail` only because the inherited baseline still contains `31`
findings and `209` warnings; this transport introduced no new issue. Feature
docs remain green at `224` generated artifacts and `86/86` checks.

Deterministic coverage is now `40 passed` for W1/legacy horizon/Pi worker/ASGI
continuity and `81 passed` for the adjacent provider, scenario, worker,
validation, and Research Spine slice with runtime warnings promoted to errors.
No Mac Studio service, model, host package, or repository state was touched.
The proof remains bounded: live G0/G1 and G2-G22 still require Docker-only
Mac Studio evidence for real served identities, common raw spans, independent
coding, Fleiss/Krippendorff reliability, grounding, reconciliation,
human-Done/report promotion, HTTP long-horizon recovery/timeout behavior,
Petals cooperation/scope/revocation, redaction, and teardown.

### L-287 | 2026-08-27T07:08:00Z | S2-execute/S3-review | gpt-5-codex | cross-engine ensemble served-identity parity

The ensemble audit found that the existing cross-engine authority test asserted
only configured endpoint model labels. That was enough to show that `legacy` and
`pi` selected the same manager-owned endpoints, but not enough to prove that a
provider-reported response identity survives the ensemble boundary or that three
independent served identities are observable. A proxy could return one shared
checkpoint while configured labels still appeared distinct in the test.

Added `tests/pi_production/test_ensemble_identity_parity.py`, an isolated
deterministic oracle using the real `AgenticDispatcher`, `PiExecutionService`,
and `PiModelManager` with a non-networking supervisor seam. It runs both engine
choices against three distinct manager-selected endpoints, emits explicit
provider-served identities different from configured labels, and asserts endpoint
identity, configured/request identity, and served identity remain separate and
complete for all three samples. The test passed (`1 passed`); Ruff passed.

This closes an authority/provenance test gap only. It does not make a response-
level MoA result formal Research Spine evidence and does not prove live model
independence, common raw spans, Fleiss/Krippendorff reliability, grounding,
reconciliation, human-Done/report promotion, Petals cooperation, or teardown.
The Docker-only Mac Studio G0/G1 and live G2-G22 gates remain open.

### L-288 | 2026-08-27T07:29:25Z | S2-execute/S3-review | gpt-5-codex | Pi ensemble usage exactness boundary

The deterministic accounting audit found a second ensemble-oracle gap after
served-identity parity: `PiExecutionService.run_ensemble` summed whichever
token fields were present and returned a non-empty usage object even when a
real provider supplied no usage receipt for one sample. The dispatcher then
persisted that partial aggregate as exact, unlike the legacy loop's existing
all-or-nothing rule. pi-ai can materialize an all-zero `Usage` placeholder for
an adapter that omitted usage, so checking only whether a dictionary exists is
not a trustworthy receipt test.

The shared usage-ledger boundary now inspects each preserved Pi sample receipt
before trusting the execution seam's compatibility aggregate. Fully reported
Pi samples aggregate input/output/cache-read/cache-write/total/cost/turn values
with `estimate=False`; any absent, explicitly estimated, or mixed sample makes
the public ensemble usage empty and causes the ledger to estimate the complete
dispatch from the repeated request plus every preserved sample text, marking
`estimate=1`. This preserves the Research Spine rule that estimated and exact
numbers never mix silently and prevents a partial exact total from being used
as evidence without changing the hot Pi engine file.

Added isolated `tests/pi_production/test_pi_ensemble_accounting.py` using the
real `AgenticDispatcher`, `PiExecutionService`, `PiModelManager`, and durable
usage ledger with a deterministic provider-result seam. It proves both the
mixed-provider estimate and fully reported cache/cost/turn aggregation at both
the public result and durable row. The focused authority/continuity/accounting
slice passes `43` tests with runtime warnings promoted to errors; Ruff,
`git diff --check`, and feature-doc generation remain the next gates. This is
deterministic accounting evidence,
not live provider quality or three-model Research Spine proof; live G0/G1 and
G2-G22 remain open for the authorized Docker-only Mac Studio run.

### L-289 | 2026-08-27T07:42:07Z | S2-execute/S3-review | gpt-5-codex | gate-clean ledger boundary

The first implementation moved aggregation into `PiExecutionService`, but
Compass Forge counted the edited hot engine file's inherited complexity as new
warnings even after the added block was extracted. That path was rejected for
transport. The engine is restored to the exact testing tip; the correction now
lives in the shared usage-ledger module and the dispatcher result boundary.
`authoritative_usage("pi", outcome)` checks every preserved sample receipt,
aggregates all reported samples including cache/cost/total/turn fields, and
returns `{}` for mixed/absent/explicitly estimated samples. The ledger uses the
same decision and estimates the repeated request plus each preserved sample
text as one complete dispatch, so public and durable accounting cannot diverge.

Verification after remediation: focused Pi accounting/identity/realpath tests
`10 passed`; W1 dispatcher/contract/donor-routing tests `63 passed`; benchmark
suite `233 passed, 5 skipped`; non-hanging Research Spine/validation slice
`36 passed, 1 deselected`; Ruff, `git diff --check`, and feature-doc generation
(`224` artifacts, `86/86` checks) passed. Compass Forge before-gate reports
`new_issue_count=0`, `new_failures=0`, and no new warnings against the inherited
`31` findings/`209` warnings baseline. The known survey-ingestion fixture still
hangs before test execution and remains inherited harness debt; it is not
claimed green. No live Mac Studio provider/model/container state was touched.

### L-290 | 2026-08-27T07:43:07Z | S2-execute/S3-review | gpt-5-codex | zero-placeholder oracle

The accounting oracle now covers the adapter failure mode in which pi-ai
returns a non-empty all-zero usage placeholder. A sample is accepted as an
exact receipt only when it has a positive token/cache/cost measurement or an
explicit `usage_reported=true` marker; an explicit estimate, `usage_reported=false`,
empty receipt, malformed sample, or all-zero placeholder makes the whole Pi
ensemble estimated. The new regression test runs through the real dispatcher,
Pi execution service, model manager, and durable ledger seam. The final
authority/continuity/accounting run is `57 passed`; Compass Forge remains at
`new_issue_count=0`, with no new failures or warnings. Live provider quality,
three-model independence, Fleiss/Krippendorff reliability, and Docker-only
Mac Studio G0-G22 evidence remain unclaimed.

### L-291 | 2026-08-27T07:43:58Z | S3-review | gpt-5-codex | clean transport checkpoint

The all-or-nothing Pi ensemble accounting correction is transported as commit
`82aa8657b1c5b84a25e29046e05672a550d2bd28` on both local `testing` and
`origin/testing`; the worktree is clean. Compass Forge after-gate reports
`actionable_failures=[]`, `new_failures=0`, `comparison.new_issue_count=0`, and
no new warnings against the inherited `31` findings/`209` warnings baseline.
The final deterministic verification is recorded in L-290. A passive,
Docker-binary-only SSH check on Mac Studio reports Docker server `29.7.2`, no
Istara/Petals containers, only the unrelated healthy Plex container, and the
retained `pi-agent-home` volume. No host package, model, service, or repository
mutation occurred. Live G0/G1 and G2-G22 remain open and require an explicitly
authorized Docker-only Mac Studio execution window.

### L-292 | 2026-08-27T07:59:53Z | S2-execute/S3-review | gpt-5-codex | Petals receipt-preserving stream seam

The Petals bridge audit found that `chat_completions_stream` called the generic
`ComputeNode.chat_stream` path and then unconditionally estimated usage. That
path emits text/tool-call pieces but does not carry a provider terminal receipt;
the OpenAI-compatible `ComputeNode.chat` path also discarded `data["usage"]`,
so a real donor could be charged as an estimate even when it reported exact
tokens. The existing bridge tests used a fake node and therefore did not expose
this loss of accounting provenance.

The bridge now calls the donor's receipt-preserving `chat` seam once (donors are
already fail-closed to relay/browser resources), emits the same valid content
and terminal OpenAI chunks, preserves provider usage when present, and marks the
terminal route with `usage_estimate=false`. Missing receipts still produce one
complete text estimate with `usage_estimate=true`; the durable bridge row and
terminal public chunk use the same values. OpenAI-compatible and Anthropic
`ComputeNode.chat` normalization now retain non-empty provider usage objects so
the bridge can observe them. A regression fails if `chat_stream` is called and
asserts exact donor usage survives the stream.

Verification: Petals bridge plus targeted compute tests pass (`40 passed,
20 deselected`), Ruff and `git diff --check` pass. This closes a deterministic
accounting transport gap only. It does not prove a live donor/provider receipt,
three independent served model identities, common raw evidence spans,
Fleiss/Krippendorff reliability, reconciliation, human-Done/report promotion,
or Docker-only Mac Studio execution; live G0/G1 and G2-G22 remain open.

### L-293 | 2026-08-27T08:11:18Z | S2-execute/S3-review | gpt-5-codex | live Pi catalog CRUD oracle

The Pi endpoint CRUD test previously verified only that `settings.pi_api_endpoints`
changed and that the route returned success. It did not keep a production-style
`PiModelManager` alive, so a broken `reset_live_settings_catalogs()` hook could
remain green while dispatchers continued using a stale catalog. The test now
constructs the same manager shape used by Pi dispatch, keeps it alive across
POST/PUT/DELETE, and asserts the custom endpoint is immediately added with its
model/protocol identity, updated in place, and removed. This makes the
Pi-Model-Management authority boundary executable without loading a provider.

Verification: `tests/test_settings_agentic_pi_endpoints.py` passes (`2 passed`),
Ruff passes, and feature documentation regenerates/checks cleanly (`224` site
artifacts, `86/86` feature checks). This is deterministic API-to-live-manager
evidence only; it does not prove an active dispatcher request, two-loop parity,
live provider identity, three-rater coding, Fleiss/Krippendorff reliability, or
Docker-only Mac Studio execution.

### L-294 | 2026-08-27T08:16:08Z | S2-execute/S3-review | gpt-5-codex | strict coder-unit provenance oracle

The live benchmark's Research Spine acceptance probe previously trusted the
coding-run aggregate count and top-level route receipt after it selected raw
evidence units. It did not independently prove that every selected unit was
coded by every rater, or that each persisted application retained raw source
text/location and a served-model route receipt matching its row model. That
left a malformed adapter able to present a numerically accepted but incomplete
or ungrounded three-rater result.

The validator now cross-checks fetched code applications against the exact
selected unit IDs, requires the configured rater width, checks the complete
coder-by-unit Cartesian coverage, and requires non-empty source text/location,
served route outcome, and row/served model agreement. Missing pairs and invalid
rows are included in persisted probe evidence and fail the provider gate closed.
A deterministic regression removes one coder-unit row's source/route data and
proves the run is blocked.

Verification: benchmark package checks pass (`79 passed`), Node syntax checks
pass, and feature docs regenerate/check cleanly (`224` artifacts, `86/86`
checks). This is a deterministic acceptance-oracle correction only; live
three-checkpoint independence, scientific reliability quality, reconciliation,
human-Done/report promotion, and Docker-only Mac Studio execution remain open.

### L-295 | 2026-08-27T08:23:12Z | S2-execute/S3-review | gpt-5-codex | explicit long-horizon engine and per-dispatch parity oracle

The long-horizon runner previously allowed `ISTARA_LONG_HORIZON_ENGINE` to be
unset, omitted the request header, and accepted a usage response whose latest
row named any engine. A dispatcher default or operator flag could therefore
make a two-turn result impossible to attribute, while a mixed Pi/legacy session
could appear valid if its last row matched the requested label. The usage API
also exposed only aggregates plus `latest`, so the runner had no way to inspect
each dispatch without reaching into the database.

The runner now fails before authentication/project creation unless the engine is
explicitly `legacy` or `pi`, sends that choice on both turns, requires the API's
content-free per-dispatch rows, requires at least two `chat_turn` rows, and
rejects any row whose engine differs from the requested engine. The usage route
adds additive identity-only rows (purpose, engine, model, endpoint/node handles,
outcome, accounting flags, and timestamps); prompts, responses, URLs, and keys
remain excluded. Regression tests cover unset/unsupported engine configuration,
mixed chat engines, and the route response contract. README and living feature
docs now state the explicit attribution boundary.

Verification: focused benchmark/API tests pass (`31 passed`; one pre-existing
async teardown warning), feature docs regenerate/check cleanly (`224` artifacts,
`86/86` checks), and the existing broad Ruff invocation reports only inherited
`chat.py` lint debt. This closes deterministic two-turn attribution coverage;
it does not prove same-session engine parity against live providers, model-served
identity, three-rater Research Spine quality, Petals cooperation, or Docker-only
Mac Studio execution. Those G9/G16-G22 gates remain open.

### L-296 | 2026-08-27T08:31:00Z | S2-execute/S3-review | gpt-5-codex | Docker wrapper long-horizon integration

The Docker-only Mac Studio comparison wrapper previously ran the Node marathon and
real-user probe only. It never invoked `tests/benchmarks/long_horizon_runner.py`,
so the two-call/session/task acceptance gate could not observe a real result and
G16/G17 were structurally untestable even when the backend was healthy.

The disposable runner image now installs `python3`/`python3-venv` and pinned
`httpx==0.28.1` into `/opt/runner-venv` during the Docker build; no Python package
installation occurs on the Mac Studio host. The outer wrapper passes an explicit
`ISTARA_LONG_HORIZON_ENGINE` per comparison arm and defaults the requirement on
for the `combined` profile while leaving `provider` and `petals` scoped to their
transport/donation gates. The inner runner validates the setting, runs the Python
workload before the probe, and persists one engine-specific log under the mounted
`data/test-marathon/long-horizon` evidence directory. Failure remains fail-closed
and the outer loop still records both engine arms before returning a non-zero result.

Verification: shell syntax, Docker-runner contract tests, and long-horizon unit
tests pass (`36 passed`), Ruff and `git diff --check` pass, and feature docs
regenerate/check cleanly (`224` artifacts, `86/86` checks). Compass Forge before
gate is baseline-clean (`new_issue_count=0`, `new_failures=0`, no new warnings;
inherited `31` failures/`208` warnings). This proves container wiring only; a
live same-session two-call run, provider-served identity, three-rater Research
Spine quality, Petals cooperation, and Mac Studio Docker execution remain open.

### L-297 | 2026-08-27T08:48:00Z | S2-execute/S3-review | gpt-5-codex | same-session usage identity oracle

The deterministic long-horizon check already requested usage with
`session_id`, but the API returned no session handle in each content-free row and
the validator therefore could not detect a query-filter regression that mixed a
different session into the response. The API now includes the persisted
`session_id` handle in each identity row, and the validator requires an explicit
benchmark session plus exact equality on every `purpose=chat_turn` row. The API
regression fixture also inserts a foreign-session row and proves it is excluded;
validator regressions cover cross-session rows and missing session context.

Verification: focused long-horizon/API and Docker contract tests pass (`38 passed`),
targeted Ruff passes for the changed validator/tests, Python compilation and
`git diff --check` pass, and feature docs regenerate/check cleanly (`224` artifacts,
`86/86` checks). A pre-commit gate observed four warning-level complexity findings
when `chat.py` was dirty; these are inherited oversized-file/function findings and
must be compared again after commit. This closes deterministic session attribution
only. It does not prove live provider-served identity, three independent coders,
Fleiss/Krippendorff quality, reconciliation or human-Done promotion, Petals
cooperation, or Mac Studio Docker execution.

### L-298 | 2026-08-27T08:50:11Z | S2-execute/S3-review | gpt-5-codex | long-horizon completion is now a scorecard gate

The Docker wrapper already ran the two-call Python workload, but its success was
only observable through wrapper exit/logs. A direct or partially configured Node
scorecard could therefore omit that workload and still present provider/Petals
and common-workflow results without an explicit long-horizon status.

The acceptance workload matrix now marks `longHorizon` only for `combined`. The
inner Docker runner exports `ISTARA_BENCHMARK_LONG_HORIZON_VERIFIED=1` only after
the engine-specific Python workload exits successfully. `run.mjs` reads the
explicit requirement/receipt, passes both through its final blocker path, and
persists `long_horizon_required` and `long_horizon_verified` in scorecard,
history, latest-run, and Markdown report output. A required workload without
the receipt fails closed; provider/Petals-only profiles remain intentionally
scoped. Deterministic tests cover missing/present receipts, workload scope, and
wrapper-to-scorecard wiring.

Verification: scoring/topology tests pass (`32 passed`), the complete real-user
benchmark package passes (`81 passed`), Node/shell syntax and `git diff --check`
pass, and feature docs regenerate/check cleanly (`224` artifacts, `86/86`
checks). Compass Forge before-gate remains baseline-clean (`new_issue_count=0`,
`new_failures=0`, no new warnings; inherited `31` failures/`208` warnings).
This closes the deterministic scorecard-oracle gap only; live two-call engine
parity, three independent served model identities, Fleiss/Krippendorff quality,
reconciliation/human-Done promotion, Petals cooperation, and Mac Studio Docker
execution remain open.

### L-299 | 2026-08-27T08:52:57Z | S2-execute/S3-review | gpt-5-codex | combined acceptance row reflects long-horizon receipt

The new long-horizon blocker correctly failed a required combined run, but the
`acceptance_gates.combined` row could still report `verified` because it only
conjoined provider and Petals flags. That made the table contradict the blocker
and could mislead a reviewer reading the scorecard without the blocker list.

`acceptanceGateStatus` now receives the explicit long-horizon requirement and
receipt and includes that conjunction in the combined gate status. A combined
run with provider/Petals evidence but no required receipt is now `blocked` in
both the gate table and blocker list; a verified receipt preserves `verified`.
The deterministic suite covers this exact contradiction regression.

Verification: scoring/topology tests pass (`33 passed`), the complete real-user
benchmark package passes (`82 passed`), feature docs regenerate/check cleanly
(`224` artifacts, `86/86` checks), and Compass Forge before-gate remains
baseline-clean (`new_issue_count=0`, `new_failures=0`, no new warnings; inherited
`31` failures/`208` warnings). This is still deterministic evidence only; live
Mac Studio Docker execution and all provider/Petals/Research Spine quality gates
remain open.

### L-300 | 2026-08-27T09:18:00Z | S2-execute/S3-review | gpt-5-codex | Petals project admission and Research Spine route-receipt seam

The prior deterministic coverage proved the Petals bridge, Pi catalog, and
Research Spine coding run separately, but it did not prove their production
path together. A concrete authorization defect was also present: the bridge
validated donor source/consent/health but did not re-check the donor's
`allowed_project_ids` at dispatch. Pi selection filtered scope, yet a caller
could send a project-tagged request directly to the loopback bridge for an
unauthorized donor. In addition, the Petals bridge's `_istara_route` receipt
was not carried by the Pi engine/dispatcher result contracts, so a successful
donor coder could be persisted as generic `pi` provenance.

The bridge now requires an explicit project for research-purpose traffic and
re-checks the donor allowlist immediately before dispatch. The Pi runtime
frame mapper produces a content-free route receipt (`route_kind`, endpoint,
requested/served model, donor node/source), `TurnResult`/`StructuredResult`
and ensemble samples preserve it, and the Research Spine coder adapter merges
that receipt into persisted `CodingRunCoder`/coding-run provenance. A malformed
non-dict route frame is normalized to an empty receipt before safe defaults are
applied.

New deterministic coverage crosses the real seams: three consented,
project-authorized registry donors are projected by the real
`PiModelManager`; the real `PiExecutionService.run_ensemble` dispatches all
three through the Petals bridge and retains each donor receipt; and the real
`run_independent_coding_run` uses the real dispatcher/service pair, reaches
Fleiss' Kappa plus Krippendorff's Alpha acceptance, and persists all three
`petals_bridge` routes. Dispatcher chat and ReAct regressions also prove route
receipts are not dropped on those public verbs.

Verification: Petals/research/runtime/W1/W7 focused suite passes (`130 passed`),
targeted Ruff, Python compilation, and `git diff --check` pass, and feature
docs regenerate/check cleanly (`224` site artifacts, `86/86` checks). The
Compass Forge before snapshot completes with no new forbidden dependencies,
cycles, or missing paths; it reports only the repository's existing complexity
warnings plus the touched large-file warnings (all warning-level, not a new
functional failure). No live provider, live donor, Mac Studio workload, or
host installation was performed. The post-change gate, commit/transport, and
Docker-only Mac Studio provider/Petals/combined evidence remain open.

### L-301 | 2026-08-27T09:32:00Z | S2-execute/S3-review | gpt-5-codex | checkpoint before transport

Completed the deterministic Petals admission and Research Spine provenance
seam. Project scope is now re-checked at bridge dispatch, route receipts survive
Pi engine/dispatcher/ReAct/chat boundaries, and the real Pi manager, dispatcher,
Petals bridge, ensemble service, and independent coding run are exercised in one
three-donor test. Local evidence remains `130 passed`, Ruff/compile/diff checks
clean, and feature docs `224` artifacts with `86/86` checks. Compass Forge's
before snapshot is recorded; it found no new forbidden dependency, cycle, or
missing-path issue, while retaining inherited/touched complexity warnings.

Next: append the corresponding findings register, attach command/gate evidence
to CF-15, run the after gate, commit and push `testing`, then perform only the
authorized Docker-only Mac Studio live matrix. Live provider identity,
same-session two-call parity, three independent served models, reliability
quality, reconciliation/human-Done/report promotion, and Petals cooperation are
not yet proven.

### L-302 | 2026-08-27T09:45:00Z | S2-execute/S3-review | gpt-5-codex | remote Docker preflight checkpoint

Transport is clean: local `testing`, `origin/testing`, and the isolated Mac Studio
retake worktree all resolve to `10e2241226b1fd1fbe1db18f9b71f2135acd7bc4`; the
retake has zero Git modifications. Passive SSH/Docker inspection found Docker
Server `29.7.2`, only the unrelated healthy `plex` container, and no Istara,
provider, Petals, benchmark, or donor containers. No host package installation,
model load, chat probe, or service start was performed.

The live matrix is currently blocked before workload startup: the clean retake has
no `.env.deploy`, the Docker-host model directory is empty, and the three-model
Compose profile cannot render without the required Compose-managed Gemma model
input. Base Compose renders only when pointed at the old checkout's secret-bearing
env file; that dirty checkout remains untouched and is not accepted as current
runtime evidence. A future live run needs an owner-provided, Docker-only env/model
provisioning decision and bounded provider/Petals authorization. Until then the
deterministic seam remains the strongest evidence and all live quality gates stay
open.

### L-303 | 2026-08-27T09:50:00Z | S2-execute/S3-review | gpt-5-codex | cleanup and live-gate boundary

The current detached Mac Studio retake is aligned to `origin/testing` at
`8865e0099a2f4a1453ec64f0d354954a7a69aca8` and remains clean. Two redundant,
clean, detached historical worktrees were removed after ancestry checks proved
both were ancestors of the transported testing tip. The owner-dirty named
checkout and the `pi-agent-home` volume were deliberately preserved. Passive
Docker checks still show only Plex and no Istara/model workload.

No live matrix was launched because the required Docker-host model artifacts and
current retake env/config are absent; starting a provider or loading models would
produce neither a valid three-rater proof nor a safe reproducible artifact. The
next executable step is owner-approved Docker-only provisioning, followed by
source/image digest capture, provider-only, Petals-only, and combined profiles,
then two-call/long-horizon, three-served-model reliability, reconciliation,
human-Done/report, redaction, and teardown verification.

### L-304 | 2026-08-27T10:00:00Z | S2-execute/S3-review | gpt-5-codex | final status handoff

CF-15 evidence is attached through command/gate records `162`–`176`. Final
committed-tree Compass Forge baseline/after records are `222`/`224`: the after
comparison has empty new-issue, forbidden-dependency, import-cycle,
missing-path, and unexpected-large-file sets; the overall gate remains `fail`
only because inherited repository findings still exist. Local testing is clean
and `testing` equals `origin/testing` at `33f68ed7c25d58126bec826d9efe6c86f23ce500`.

CF-15, CF-13, CF-20, and CF-21 remain open rather than being marked complete.
The unclosed gates are operational/scientific, not hidden test failures:
Docker-only provisioning of current env/model or provider routes; provider-served
identity; both engine paths through shared Pi Model Management; same-session
two-call/long-horizon behavior; three independent served models over common raw
evidence units; Fleiss/Krippendorff reliability with grounding; Petals scope,
consent, and route receipts; reconciliation; human-approved Done/report
promotion; redacted artifacts; and teardown. No live claim is made until those
artifacts exist.

### L-305 | 2026-08-27T10:05:00Z | S2-execute/S3-review | gpt-5-codex | ref synchronization

The final ledger checkpoint is transported on the testing branch; at each resumption, verify the exact equality of local `testing`, `origin/testing`, and `~/istara-testing-retake-47bf` before running anything. The isolated retake is clean. A passive final check found no runner, long-horizon, or benchmark process and only the unrelated healthy Plex container. This is the last pre-provisioning checkpoint; no active model/provider workload has been started.

## L-306 — Detailed completion matrix for the remaining live gates

This section is the resumption contract for the remaining work. It is deliberately
operational and evidence-oriented: a future agent must be able to start at the
first unchecked row, run only inside Docker on the Mac Studio, and leave a redacted
artifact plus a Compass Forge command or gate record for every claim. The deterministic
tests already prove local wiring and fail-closed scorecard behavior; they do not prove
that live model responses are independent, source-grounded, reliable, or acceptable.

### 1. Non-negotiable boundaries and resume procedure

1. Work from `/Users/user/Documents/Istara-main` on local branch `testing`, and
   verify `git status --short --branch` is clean before changing or transferring
   anything. The local tip, `origin/testing`, and the Mac Studio detached retake
   `~/istara-testing-retake-47bf` must resolve to the same commit. Do not use the
   owner-dirty `~/istara-testing` checkout as a benchmark source or modify it.
2. On the Mac Studio use SSH only for orchestration and passive Docker/Git commands.
   Use the explicit Docker Desktop CLI path when required (`/usr/local/bin/docker`
   or `/Applications/Docker.app/Contents/Resources/bin/docker`). Do not run host
   Python, Node, npm, Playwright, model servers, package managers, or chat probes.
3. Do not install packages on macOS. Build or pull disposable images and install
   dependencies only in those images. Keep the Docker socket mounted only into the
   benchmark runner when the selected profile requires nested donor/client containers;
   never mount it into the application services.
4. Before each resumed stage, record a new ledger checkpoint with: UTC time, exact
   source SHA, source archive SHA-256, Compose file and env-file paths (names only),
   image digests, profile, engine, model identities, and the next unchecked gate.
   Never record secret values, raw prompts, raw responses, private URLs, or connection
   strings. If a prerequisite is absent, stop that stage and record the blocker; do
   not substitute a stub, a same-model endpoint, or a stale checkout.
5. Preserve the unrelated healthy Plex container and the `pi-agent-home` volume unless
   a later owner-authorized inspection proves a specific testing resource is disposable.
   Teardown may remove only resources created by the run, by exact project/name, after
   result export and redaction.

### 2. Provisioning gate: make the live run reproducible before starting it

This gate is currently open and is the first required owner action. It is satisfied
only when all rows below are true and the evidence is captured in the Docker-only
retake.

| Check | Required action | Pass evidence | Fail handling |
| --- | --- | --- | --- |
| Source | Transfer or fetch the exact `testing` tip into `~/istara-testing-retake-47bf`; keep it detached and clean. | `git rev-parse HEAD`, `git status --porcelain`, and remote ref all match; `git archive --format=tar HEAD \| shasum -a 256` is recorded. | Stop before image build/start; repair the retake, never benchmark a dirty checkout. |
| Compose inputs | Owner supplies a current, mode-600 env/config path for the retake without exposing values. | `docker compose --env-file <path> -f docker-compose.vps.yml config` succeeds; a redacted variable-name inventory is attached. | Do not point at the old dirty checkout's env file as “current” evidence. |
| Provider routes | Supply exactly the configured provider endpoint/model identities for the provider arm, with health checks that do not load multiple heavy models at once. | Redacted provider health/metadata shows requested model, served model, endpoint handle, and source image digest. | Fail closed on missing/ambiguous identity; do not infer model identity from a request label. |
| Three model inputs | Supply three distinct model identities or three explicitly distinct provider-served models, all available to Docker services. The existing `three-model` profile also requires `ISTARA_BENCHMARK_DONOR_GEMMA_MODEL_FILE` under the absolute `ISTARA_BENCHMARK_MODEL_ROOT`. | `docker compose ... --profile three-model config` succeeds; each identity and file/image digest is recorded; model-root file listing contains no secrets. | Stop before startup if the model directory is empty or the required Gemma input is absent. |
| Runner image | Build or pull `istara-benchmark-runner:node20-docker-cli` inside Docker and record its immutable digest. | `docker image inspect --format '{{.Id}}'` and package/runtime versions from inside the runner. | Rebuild the disposable image; never install the Python/httpx or Playwright dependencies on the host. |
| Isolation | Confirm the stack project name, networks, mounts, and result directories are unique to this run. | Redacted `docker compose config`, `docker ps`, and mount inspection. | Teardown conflicting testing resources by exact name only, preserving Plex and unrelated data. |

The provisioning gate must be attached to CF-15 as command evidence before any
provider/Petals result is described as live. A source or image digest by itself is
not a quality result; it only establishes reproducibility.

### 3. Staged live profile matrix

Run profiles in this order. Each profile uses a fresh run group and disposable stack,
and exports its scorecard, logs, route receipts, and redacted metadata before teardown.
Do not combine stages to hide which gate failed.

#### 3.1 Provider-only transport and authority profile

Use `ISTARA_BENCHMARK_ACCEPTANCE_PROFILE=provider`, with the provider route(s) and
`ISTARA_BENCHMARK_REQUIRE_COMPUTE_DONATION=0`. This profile may skip the marathon and
long-horizon workload; it must not report Research Spine acceptance.

Required checks:

1. Compose starts only the intended application/provider services. Capture health,
   image digests, service logs, and the Pi catalog response with the requested model,
   canonical model identity, endpoint identity, and health state.
2. Exercise both selectable paths that are supposed to share Pi Model Management:
   the Istara/legacy loop and the Agentic Loop/PI Agentic Loop path as exposed by the
   current UI/API. For each path, record the engine selection, the model-manager
   selection, dispatch route receipt, usage row, and session handle. A request header
   or UI label is not proof of runtime routing.
3. Issue exactly two bounded calls in one session per engine arm. The second call must
   reference the first call's durable session/task handle and must not silently fall
   back to a new session or a different model. Compare route identity, response status,
   tool-call accounting, and usage attribution across both calls.
4. Verify no removed classical Alembic endpoint is still used by the production path,
   while migration/schema behavior remains reachable through the intended PI Model
   Management ownership. Record HTTP route/status evidence, not just source inspection.

Pass requires provider-served identity and shared Pi authority for both engines, clean
two-call/session attribution, and a scorecard with no provider blockers. It does not
pass the three-rater or Petals gates.

#### 3.2 Petals-only donation and governance profile

Use `ISTARA_BENCHMARK_ACCEPTANCE_PROFILE=petals`, require compute donation, and run
only the donor/bridge/client-sandbox scope. This profile must not claim chat, long
horizon, or Research Spine quality.

Required checks:

1. Start three consented donor identities through the Docker-managed topology. Each
   donor must have a distinct model identity, node/source handle, health result, and
   project allowlist. Same model behind three endpoints is a transport topology, not
   independent coding evidence.
2. Submit project-tagged research-purpose traffic through the real Pi Model Manager
   projection and the real Petals bridge. Verify the bridge re-checks
   `allowed_project_ids` immediately before both streaming and non-stream dispatch.
   Include negative cases for missing project, unauthorized project, revoked donor,
   unhealthy donor, and stale catalog/metadata.
3. Verify every accepted route receipt is content-free and contains only the fields
   needed for audit: route kind, endpoint/source handle, requested and served model,
   donor node/source, outcome, and timestamp/usage handle. It must survive engine,
   dispatcher, stream/ReAct, ensemble sample, and Research Spine coder persistence.
4. Revoke one donor during the run and prove new research dispatch fails closed while
   previously persisted receipts remain immutable. Confirm no prompt/response or secret
   is written to the receipt or exported artifact.

Pass requires project authorization, consent/revocation, distinct donor/model
identity, and receipt persistence. It is not evidence that model outputs are useful or
that three raters agree.

#### 3.3 Combined Research Spine acceptance profile

Use `ISTARA_BENCHMARK_ACCEPTANCE_PROFILE=combined`, require live chat, long horizon,
and compute donation. Run the full wrapper from inside the disposable runner. The
wrapper must invoke the engine-specific marathon, `tests/benchmarks/long_horizon_runner.py`,
and the deep three-model probe; the resulting `ISTARA_BENCHMARK_LONG_HORIZON_VERIFIED=1`
receipt must appear in the scorecard before the combined row can be `verified`.

### 4. Research Spine proof requirements (the scientific gate)

The combined profile is accepted only if it demonstrates the complete governed path:

`raw source -> evidence units -> three independent atomic coders/open coding ->
source grounding -> reliability -> reconciliation -> accepted atoms/nuggets ->
facts -> insights -> recommendations -> In Review -> human-approved Done -> report`.

The live probe must make each transition observable. A final answer, a green HTTP
status, or a high agreement number is insufficient.

1. **Common raw evidence.** Ingest the same raw source snapshot for all three coders.
   Store immutable source hash, source span/unit IDs, offsets or exact quoted spans,
   and ingestion provenance. Do not use synthesized nugget prose as the evidence unit.
2. **Independent model identities.** The three raters must be three distinct served
   model identities, not three aliases, endpoints, temperatures, or retries of one
   model. Record requested and served identity separately and fail closed if the
   provider cannot attest to the served model.
3. **Atomic extraction/open coding.** Each rater must produce independently persisted
   atom/code rows keyed to the same evidence-unit IDs, with prompt/codebook version,
   model identity, route receipt, and raw output hash. Do not run a consensus prompt
   before individual rows are persisted.
4. **Grounding.** Every accepted atom must link to one or more source spans and retain
   the original evidence-unit handle. A missing, synthetic, or out-of-range span is a
   blocker even if the raters agree.
5. **Reliability.** Compute Fleiss' kappa over the full three-rater categorical matrix
   with a stable category/codebook mapping and explicit missing-value policy. Compute
   Krippendorff's alpha (nominal/ordinal interval as dictated by the codebook) over
   the same independent ratings. Persist the number of units, raters, categories,
   observed agreement, expected agreement, kappa, alpha, and threshold decision.
   Do not treat duplicate rows, retries, or same-model replicas as independent ratings.
6. **Reconciliation.** Persist disagreements and the reconciliation decision with the
   participating atom IDs, reason, adjudicator/algorithm version, and source spans.
   Reconciliation may create a candidate revision, but it must not overwrite the
   independent raw ratings or silently raise reliability.
7. **Promotion gates.** Prove that only reliability-passing, grounded, reconciled
   atoms can promote to accepted nuggets/facts/insights/recommendations. Prove that
   In Review and human-approved Done are required before a report/export is marked
   reportable. A scorecard must contain explicit counts for candidate, accepted,
   review, Done, and reportable artifacts.
8. **Negative controls.** Include at least one deliberately ungrounded atom, one
   disagreement below the configured reliability threshold, one duplicate/same-model
   identity attempt, and one missing-human-approval attempt. Each must fail closed and
   leave a machine-readable blocker, without polluting accepted/reportable data.

The scientific gate is red if any one of these items is absent, even when all focused
tests pass. The scorecard must distinguish `not_run`, `blocked`, `failed`, and
`verified`; an omitted probe is never a pass.

### 5. Engine, tool-call, and long-horizon parity matrix

For both the Istara/legacy path and the Agentic Loop/PI Agentic Loop path, execute the
same bounded scenario pack against the same source and model roster:

| Scenario | Required observation | Acceptance oracle |
| --- | --- | --- |
| First chat call | Engine selection, Pi manager catalog identity, route receipt, session/task handle, response and usage row. | Selected engine and served model agree; no classical/Alembic bypass; no generic provenance. |
| Second same-session call | Prior session/task handle reused, same project scope, same or explicitly recorded model identity. | No cross-session row; no silent new session; second call has its own route/usage receipt. |
| Tool call | Tool request/result IDs, authorization, idempotency, route receipt, and final answer linkage. | Tool loop remains within selected engine and Pi authority; unauthorized/replayed tool fails closed. |
| Long horizon | Multiple turns/tasks, checkpoint/resume, bounded context, intermediate usage rows, and final task state. | `long_horizon_verified=1`, every row has the expected session handle, no truncated/cross-engine task, and nonzero blocker on any mismatch. |
| Research coding | Three independent coders and shared raw evidence units. | All Research Spine gates in section 4 pass; plain chat success cannot substitute. |

Compare outputs for parity of control flow and provenance, not byte-for-byte model
text. Semantic quality requires a separately reviewed rubric and retained samples; do
not promote deterministic wrapper success into a model-quality claim.

### 6. Artifact, redaction, and teardown checklist

Before removing the run stack, export a manifest containing run group, exact source
and image digests, Compose profile, engine, model identities, route/usage receipt
counts, gate states, test command/exit status, and timestamps. Redact prompts,
responses, tokens, passwords, private URLs, connection strings, and raw model payloads;
retain hashes and opaque handles where provenance needs continuity. Verify exported
JSON/Markdown parses and that no secret-pattern scan finds a credential. Then:

1. stop/remove only the exact Compose project and donor/client containers created by
   this run;
2. remove only its networks and anonymous runner volumes;
3. preserve source artifacts and scorecards in the approved testing-results location;
4. re-run passive `docker ps -a`, volume, and process checks to prove no workload or
   host process remains;
5. record teardown exit status and the final clean detached-worktree SHA.

### 7. Compass Forge closure sequence

After each profile, attach the command output and redacted artifact path to CF-15
(`compass-forge task evidence 15 ...`). Keep CF-13, CF-20, and CF-21 open until their
specific acceptance/proof conditions are demonstrably satisfied. Then run:

1. `compass-forge gate before --task CF-15` and preserve the record ID;
2. the focused deterministic suite plus the Docker live command(s), each with exit
   status and artifact paths;
3. `compass-forge gate after --task CF-15`, recording inherited baseline failures
   separately from new failures;
4. `compass-forge spec coverage CF-SPEC-2` and `compass-forge spec accept CF-SPEC-2`
   only if every linked task has evidence and no required gate remains open;
5. `compass-forge finish-task` only after acceptance is truthful and the ledger status
   changes to a terminal state.

If live inputs remain unavailable, leave the goal and these tasks open, append a new
checkpoint naming the exact missing prerequisite, and stop. Do not mark the spec or
Build Stream complete on deterministic evidence alone.

### 8. Current checkpoint and next executable action

At this checkpoint, local `testing` and `origin/testing` are clean and equal at
`2a32a220944d696c8949a5e7f499414eab69a635`; the isolated Mac Studio retake must be
rechecked before use. Docker is available remotely, but the clean retake still lacks
the current env/config and the Docker-host model directory is empty. Therefore the
next executable action is not a model run: obtain the owner-approved Docker-only
provisioning inputs in section 2, verify their digests and Compose rendering, and only
then begin the provider-only profile. Until that happens, all live provider,
Petals, combined, same-session, three-rater, reliability, reconciliation, human-Done,
and report gates remain `not_run`/open.

### L-310 | 2026-08-27T09:36:23Z | S3-review | gpt-5-codex | worktree and branch cleanup boundary

The local repository has only the active `testing` checkout plus one additional
worktree at `/Users/user/Documents/Codex/2026-08-10/list/work/istara-pi-linearized-2026-08-10`
on `recovery/pi-retake-linearized-2026-08-10`. That recovery tip is clean but is not
an ancestor of either current `testing` or `main`, so it is retained as a deliberate
recovery artifact. No local branch is merged into `testing` except `testing` itself;
therefore no additional branch or worktree can be safely deleted under the cleanup
authorization. The two redundant clean detached Mac Studio worktrees were already
removed under the earlier cleanup checkpoint; the owner-dirty checkout and current
retake remain preserved.

No code or runtime state changed in this inventory. The exact testing tip remains
`3198c3478f23a5bc6e22cfd699080947e5070740`, with the Mac Studio retake clean and
Docker idle. The next action is still Docker-only provisioning, not destructive
cleanup.

### L-311 | 2026-08-27T09:38:12Z | S3-review | gpt-5-codex | Compose preflight clarification

The clean Mac Studio retake successfully renders both the base and three-model
Compose configurations when given `.env.example`; this is syntax/interpolation
evidence only, recorded in Compass Forge command evidence `203`. It does not provide
live credentials, provider-served model identity, or the actual model files required
by the benchmark wrapper. The Docker-host model directory still contains zero files,
and no service or model workload was started.

The external findings register now contains F-R9-98, correcting the narrower
F-R9-96 wording while preserving the operational conclusion: `compose_config=ok`
must not be confused with runtime readiness or Research Spine acceptance. The next
gate remains owner-approved Docker-only provisioning followed by provider-only,
Petals-only, and combined runs.

### L-307 | 2026-08-27T09:30:18Z | S5-ship&learn | gpt-5-codex | detailed matrix transport and live-gate checkpoint

The detailed completion matrix in L-306 is now committed and pushed as
`94214a16fe0063bc31802a8c7347c8dffeb9f3a8`, with local `testing` and
`origin/testing` equal and the Mac Studio detached retake
`~/istara-testing-retake-47bf` clean at the same SHA. Compass Forge command evidence
`184` records the L-306 pre-gate; gate evidence `186` links after record `230` and
the Docker-only passive retake check. The after comparison found no new issues,
forbidden dependencies, import cycles, or missing required paths; the remaining
failure is the known inherited baseline plus the lifecycle file's path-suppressed
large-file category.

No provider, Petals, model, benchmark, or host workload was started. The next
unchecked item is the owner-approved Docker-only provisioning gate in L-306 section
2; until its env/config, model/provider identities, source/image digests, and
three-model Compose inputs exist, all live scientific and operational gates remain
open and no completion claim is permitted.

### L-308 | 2026-08-27T09:32:00Z | S5-ship&learn | gpt-5-codex | explicit external provisioning hold

The status block now names the only active hold: owner-approved Docker-only Mac
Studio provisioning of the current env/config, provider-served identities, and
three-model inputs. This is an in-progress external prerequisite, not a terminal
goal status and not permission to run host software. The latest transported tip is
`7f57afd2fea7206af4440ceee3051e799174b41c`; the retake is clean and passive Docker
inventory remains empty of Istara/benchmark/provider/Petals workloads. Resume at
L-306 section 2, attach provisioning evidence to CF-15, and do not claim live
Research Spine or ensemble acceptance until the full matrix is executed.

### L-309 | 2026-08-27T09:35:19Z | S3-review | gpt-5-codex | deterministic retest checkpoint

The current exact testing tip remains locally clean and the deterministic seam/oracle
coverage was re-run after the handoff: the focused Petals/Pi/Research Spine Python
suite passed `130`, and the benchmark Research Spine, scoring, topology, and
provenance Node suite passed `48`. Compass Forge command evidence `196` records both
commands and explicitly marks them deterministic-only. These results strengthen the
local wiring and fail-closed oracle proof but do not establish live provider-served
identity, model independence, semantic quality, or Mac Studio execution.

The Docker-only provisioning hold is unchanged: the clean retake has no current env
file, the Docker-host model directory is empty, and no Istara/provider/Petals/runner
workload is active. Resume at L-306 section 2 when the owner-approved inputs exist;
keep CF-13, CF-15, CF-20, and CF-21 open until the live matrix produces redacted
artifacts and terminal evidence.

### L-312 | 2026-08-27T09:59:22Z | S3-review | gpt-5-codex | namespace and reliability hardening retest checkpoint

The second review pass found that reserving the generated `pi-petals-*` namespace
was incomplete if a malformed static entry was already persisted: exact resolution
failed closed, but generic distinct-ensemble and embedding selection could still see
the collision. `PiModelManager` now excludes non-Petals entries in that namespace
from all generic selection paths, preserves explicit `kind="petals"` fixtures, hides
invalid collisions from the catalog, and the settings POST rejects new reserved IDs.
Reliability-gate failure exits now expose the same item-level promotion and evidence
ID shape as other paths, so invalid independence/provenance cannot silently omit
per-item state. These changes address F-R9-99 and F-R9-100 in the external findings
register; donor/provider live proof remains open.

Verification completed locally: the focused Python integrity set passed `96`; the
broader Petals/Pi/dispatcher/manager/Research Spine matrix passed `193`; the Node
benchmark `check` passed all `82` syntax, corpus, provenance, scoring, topology,
acceptance, and Docker-wrapper tests; Ruff on touched files, `py_compile`, and
`git diff --check` passed. Feature documentation regeneration/check passed with
`224` generated artifacts and `86/86` feature checks. Compass Forge `gate before`
record `243` completed with inherited baseline findings plus new non-blocking
complexity warnings for the edited manager and an existing oversized test file;
no new import cycles, forbidden dependencies, or missing required paths were found.

No live model/provider/Petals request or model load occurred. The only unchecked
acceptance gates remain the owner-approved Docker-only Mac Studio provisioning,
provider/Petals/combined runtime runs, engine parity, same-session two-call and
long-horizon receipts, real three-rater Fleiss/Krippendorff evidence, reconciliation,
and human-Done/report promotion. The next step is to attach these deterministic
command results to the open CF tasks, run the after-gate, commit and push only the
intended testing changes, and passively retarget the clean Mac Studio retake without
starting any workload.

### L-313 | 2026-08-27T10:00:44Z | S3-review | gpt-5-codex | deterministic evidence and after-gate checkpoint

The deterministic verification evidence is now attached to the open Compass Forge
tasks: command evidence `207` (CF-15), `208` (CF-20), and `209` (CF-13), plus
after-gate evidence `211` (CF-15). The after-gate compared against before record
`243` and reported `new_issue_count=0`, `new_failures=0`, `cycles=0`, and no
actionable failures. Its overall `status=fail` is inherited repository debt only:
the configured secret-flow and unexpected-large-file checks remain failing, with
existing route/type drift and warnings; none was introduced by this change.

The ledger, code, tests, and generated manifest are ready for a clean testing commit.
Next: stage only the nine intended repository files, commit/push `testing`, verify
local and `origin/testing` are identical, then passively retarget
`~/istara-testing-retake-47bf` on the Mac Studio to that SHA with status clean. Do
not start Docker workloads or load models until the owner-approved env, served model
identities, donor inputs, and redacted artifact paths are present.

### L-314 | 2026-08-27T10:01:45Z | S5-ship&learn | gpt-5-codex | clean transport and passive Mac Studio retarget

The intended nine-file change set was committed as `d6b6438bcf84c05278522aa14a3ec807a247e12e`
(`test: harden Petals namespace and reliability gates`) and pushed to `origin/testing`.
Local `testing` and `origin/testing` resolve to the same SHA, `git diff
origin/testing --` is empty, and the local checkout has zero unstaged/untracked
paths. The only retained additional local worktree is the deliberate recovery
checkout `recovery/pi-retake-linearized-2026-08-10`; it is not an ancestor of the
active branch and was therefore not deleted.

On Mac Studio, the clean detached retake `~/istara-testing-retake-47bf` was
passively retargeted to the same SHA and reports zero worktree changes. Docker was
queried through its explicit binary `/usr/local/bin/docker` (server `29.7.2`), with
zero Istara/provider/Petals/benchmark/donor containers; only the unrelated Plex
container is running. The first PATH-only probe reported `docker` missing, which is
expected on this host; the explicit Docker path verified the engine without any host
installation or workload start.

This transport checkpoint closes only source synchronization. It does not close the
live provider, Petals donation, combined routing, engine-parity, same-session
two-call, long-horizon, three-rater Fleiss/Krippendorff, reconciliation, human-Done,
or report-promotion gates. Resume at L-306 section 2 only after the owner-approved
Docker-only inputs exist.

### L-315 | 2026-08-27T10:02:54Z | S5-ship&learn | gpt-5-codex | final tip parity confirmation

The ledger-only follow-up commit `1e3827f06a93b0f8240370dcfe546422e7414a92`
(`docs: record testing transport checkpoint`) is now the exact local and
`origin/testing` tip. The Mac Studio detached retake
`~/istara-testing-retake-47bf` was retargeted to this final SHA and remains clean.
The explicit Docker engine `/usr/local/bin/docker` reports server `29.7.2`; the
passive inventory still has zero Istara/provider/Petals/benchmark/donor containers
and only the unrelated Plex container active.

All source synchronization work in this phase is complete. The Build Stream remains
`in-progress` because the owner-approved Docker-only live acceptance inputs are not
present. No host installation, model load, provider request, or benchmark workload
was performed. Resume at L-306 section 2 when those inputs are supplied, preserving
the fail-closed requirement for every live Research Spine and ensemble gate.

### L-316 | 2026-08-27T10:16:48Z | S3-review | gpt-5-codex | Research Spine acceptance-oracle identity hardening

The deeper benchmark audit found three acceptance-oracle gaps. Code applications and
reconciliation decisions were requested for a coding run but their returned rows were
not checked for that same `coding_run_id`; duplicate application IDs could therefore
inflate aggregate coverage; and row-level model names were not bound to the exact
served route identities or to one stable model per coder. The positive fixture also
used `model-1/2/3` and `donor-1/2/3` while its served-route receipt declared
`model-a/b/c` and `donor-a/b/c`, so the missing identity binding was not observable.

`tests/real_user_benchmark/lib/research-spine-probes.mjs` now fails closed for
cross-run applications or decisions, duplicate application IDs, coder/model
switching, missing served model identities, and unexpected model identities. The
fixture in `tests/real_user_benchmark/lib/research-spine-probes.test.mjs` is aligned
with its route receipts, with regressions for foreign application rows, foreign
decisions, duplicates, and a missing served model. Compass Forge command evidence
`212` records `npm --prefix tests/real_user_benchmark run check`: all `86` tests
passed, deterministic-only with no provider request or model load. Feature-document
regeneration/check passed (`224` generated artifacts, `86/86` checks). The new
external finding is F-R9-101.

The live scientific and operational gates remain open. Deterministic identity and
coverage checks cannot prove provider-served model independence, semantic quality,
meaningful Fleiss' kappa/Krippendorff's alpha, reconciliation, human-Done/report
promotion, same-session two-call or long-horizon behavior, Petals interoperation, or
Docker Mac Studio execution. Next: attach the after-gate, commit/push only intended
repository files, verify local/remote parity, and passively retarget the clean Mac
Studio detached retake without starting a workload.

### L-317 | 2026-08-27T10:19:26Z | S3-review/S5-ship&learn | gpt-5-codex | clean before/after gate for oracle hardening

After the deterministic oracle retest and feature-document check, Compass Forge
recorded a clean comparison pair: before record `249`, after record `250`, and task
gate evidence `215`. The after-gate status remains `fail` only for the repository's
inherited secret-flow and unexpected-large-file debt; the comparison reports zero new
issues, forbidden dependencies, missing required paths, Python import cycles, or
unexpected-large-file delta (`file_count_delta=0`, `large_file_count_delta=0`).
Current gate inventory is two failures and 378 warnings, which are not introduced by
this benchmark change. The earlier mixed baseline records are retained for history;
this pair is the transport gate for the current tree.

The intended repository change set is now ready to stage: the benchmark oracle and
regression tests, the generated feature manifest, and this Build Stream checkpoint.
External F-R9-101 is documented separately in `/Users/user/Desktop/testing.md` and
is intentionally outside Git. Next: stage only those repository paths, commit and
push `testing` to `origin/testing`, verify exact SHA/tree parity and clean status,
then passively retarget `~/istara-testing-retake-47bf` on the Mac Studio. No live
provider request, model load, host install, or Docker workload is authorized by the
current input inventory.

### L-318 | 2026-08-27T10:21:03Z | S5-ship&learn | gpt-5-codex | clean testing transport and passive Mac Studio retarget

The four-file repository change set was committed as
`cb9ffc8d9e93fcdcb41f97b8334d3097346f1a3e` (`test: bind Research Spine acceptance
to served identities`) and pushed to `origin/testing`. Local `testing` and
`origin/testing` resolve to the same SHA, `git diff origin/testing --` is empty,
`git status --porcelain` is empty, and the staged tree passed `git diff --cached
--check` before commit. The external findings register now includes F-R9-101 and
remains deliberately outside Git.

The Mac Studio host `users-Mac-Studio.local` was accessed only through SSH control
using the existing `macstudio` alias. Its detached retake
`~/istara-testing-retake-47bf` fetched `origin/testing`, was retargeted to the exact
SHA above, and reports zero worktree changes and exact remote-ref parity. Passive
Docker inspection used `/usr/local/bin/docker` and reports Server `29.7.2`, zero
Istara/provider/Petals/benchmark/donor containers, and zero files under
`~/Istara-Projects/models`. No host package operation, service startup, provider
request, model load, or benchmark workload occurred.

This closes only the deterministic oracle hardening and source synchronization
checkpoint. The live provider/Petals/combined runtime matrix, shared PI Model
Management routing for Istara and PI-agentic modes, same-session two-call and
long-horizon receipts, real three-model served identities, Fleiss' kappa and
Krippendorff's alpha semantic evidence, reconciliation, human-Done/report
promotion, redaction, and teardown remain open pending owner-approved Docker-only
inputs. The Build Stream stays `in-progress` and fail-closed.

### L-319 | 2026-08-27T10:22:25Z | S5-ship&learn | gpt-5-codex | final transport evidence attachment

Compass Forge task evidence `216` records the parity and passive-host check made
before this final ledger-only append: local `testing`, `origin/testing`, and the
Mac Studio detached retake all resolved to `335fd844d3e4362a366a9dac4b1cae8e25d04895`;
local and remote worktrees
are clean; Docker was queried only through `/usr/local/bin/docker` (Server
`29.7.2`); and the host has zero Istara/provider/Petals/benchmark/donor containers
and zero model files. No live workload or host installation occurred. This
checkpoint closes the local deterministic transport work while keeping every live
Research Spine and ensemble gate open until the owner-approved Docker-only input
set exists.

### L-320 | 2026-08-27T10:23:06Z | S5-ship&learn | gpt-5-codex | final ledger-tip parity correction

Appending L-319 created the expected docs-only transport commit
`4aa1caad6c9405a4d0c8a812b11e76112e65c137`, which was pushed and retargeted before
this follow-up. L-319 remains a valid record of the pre-append evidence row `216`.
The final tip is intentionally verified after this ledger update rather than
embedded here, because any append to this file necessarily creates a new commit;
use `git rev-parse HEAD`, `git rev-parse origin/testing`, and the detached-retake
check below as the authoritative current values. No workload, provider request,
model load, or host installation occurred.

### L-321 | 2026-08-27T10:23:48Z | S5-ship&learn | gpt-5-codex | non-self-referential final-tip handoff

The ledger now records the SHA-self-reference rule explicitly: historical commit
identities are preserved, while the current synchronized tip must be read from
the post-commit parity commands, not copied into the file that changes the tip.
This prevents a future agent from inheriting a false final SHA after a routine
ledger checkpoint. The only remaining work is owner-approved Docker-only live
acceptance; all deterministic changes and their external finding are already
transported, and the Build Stream remains `in-progress`/fail-closed.

### L-322 | 2026-08-27T10:35:58Z | S3-review/S5-ship&learn | gpt-5-codex | source grounding and public Pi selector parity

The deterministic benchmark audit found one remaining Research Spine oracle
weakness: application rows were required to have non-empty source text and
location, but the probe did not prove those fields matched the selected raw
evidence unit. A fabricated paraphrase or relocated document reference could
therefore pass coverage, route identity, reconciliation, and numeric reliability
checks. `tests/real_user_benchmark/lib/research-spine-probes.mjs` now requires a
contiguous quote from the exact expected unit and an exact source-location match,
records both mismatch classes, and fails coding/multi-model validation closed.
The regression suite covers fabricated and relocated spans, and positive fixtures
derive their source fields from the same expected units.

The public engine boundary exposes `pi`, `pi-candidate`, `pi-replacement`, and
`deepseek-pi` aliases. `tests/pi_production/test_ensemble_identity_parity.py`
now exercises `legacy` plus every alias against one real
`PiExecutionService`/`PiModelManager` pair and requires three distinct
provider-served identities for every selector. The Ensemble Health feature
documentation and generated site manifest were updated accordingly. External
finding F-R9-102 records the former grounding-oracle gap in
`/Users/user/Desktop/testing.md`.

Verification completed: the real-user benchmark package passes `87/87`; focused
Research Spine, ensemble identity, and PI-manager Python tests pass `4/4`; Ruff,
Python compilation, and `git diff --check` pass; feature docs regenerate and
validate with `224` artifacts and `86/86` feature checks; Compass Forge after-gate
reports `new_issue_count=0` and no actionable failures. Compass task evidence
`219` records the deterministic command bundle. The gate still reports only
inherited repository debt (secret-flow and unexpected-large-file checks).

No live provider request, model load, host installation, or Mac Studio workload
was performed. The next transport step is to stage only the intended repository
files, commit/push `testing`, verify local/remote parity, and passively retarget
`~/istara-testing-retake-47bf`; live three-model, Petals, two-call/long-horizon,
reconciliation, human-Done/report, and Docker acceptance gates remain open
pending owner-approved env/config, served identities, donor inputs, and redacted
artifacts.

### L-323 | 2026-08-27T10:38:02Z | S5-ship&learn | gpt-5-codex | transport and passive Mac Studio parity handoff

The source-grounding oracle and public Pi-selector parity change was committed
and pushed with only the seven intended repository files. Local `testing`,
`origin/testing`, and the detached Mac Studio retake
`~/istara-testing-retake-47bf` were fetched/retargeted and verified clean and
equal. Compass task evidence `220` records the exact parity commands and
redacted passive host result.

The Mac Studio check used only the existing `macstudio` SSH alias and explicit
`/usr/local/bin/docker`: Docker Server `29.7.2`, zero Istara/provider/Petals/
benchmark/donor containers, zero files under `~/Istara-Projects/models`, no
`.env.deploy` in the retake, and one `.env.example`. The unrelated healthy Plex
container was preserved. No host package manager, Python/Node/npm process,
model load, provider request, or benchmark workload ran.

All deterministic implementation work in this slice is therefore transported;
the Build Stream remains `in-progress` because the live matrix is not
reproducible without owner-approved current environment/config, three distinct
served model identities, donor/model inputs, and redacted result artifacts.
Resume only at the provisioning gate in L-306, keeping provider/Petals/combined,
same-session two-call and long-horizon, Fleiss/Krippendorff semantic quality,
reconciliation, human-Done/report promotion, and teardown evidence unproven
until their Docker-only receipts exist.

### L-324 | 2026-08-27T11:03:12Z | S3-review/S5-ship&learn | gpt-5-codex | companion benchmark authority boundary

The audit found that the opt-in historical live test
`tests/integration/test_llm_orchestration_real.py` was still discoverable in the
release-facing agentic contract as integration evidence for ensemble and ReAct.
Its one-profile legacy `ComputeRegistry` setup and permissive PASS oracle measure
orchestration ergonomics only; they do not prove Pi Model Management authority,
three provider-served model identities, Research Spine source grounding, Fleiss or
Krippendorff reliability, reconciliation, or human-approved report promotion.

The manifest now marks that test `evidence_role=companion`, names the strict
acceptance paths (`tests/pi_benchmark/live_driver.py` and the Docker-only
real-user runner), and records explicit non-claims. The benchmark prints the role;
the registry/README and Ensemble Health feature page repeat the boundary; and a
contract regression prevents the companion classification from being removed.
Verification passed: JSON validation, `22` contract/harness tests, Ruff, feature
documentation generation/check (`224` artifacts, `86/86`), and `git diff --check`.
No live request, model load, host installation, or Mac Studio workload occurred.
The next action remains owner-approved Docker-only provisioning and execution of
the strict provider, Petals, combined, two-call/long-horizon, reliability,
reconciliation, human-Done/report, and teardown gates; the companion PASS must not
be used as a substitute.

### L-325 | 2026-08-27T11:04:42Z | S5-ship&learn | gpt-5-codex | contract evidence and transport checkpoint

Compass command evidence `222` records the companion-boundary verification: both
JSON manifests parse, the contract/harness tests pass (`22`), the full real-user
benchmark package remains green (`87`), test-harness governance passes, feature
documentation regenerates and checks (`224` artifacts, `86/86`), Ruff passes, and
the diff is clean. Evidence `223` records the `testing` push and passive Docker-only
Mac Studio retake at the same exact commit, with zero Istara/provider/Petals/
benchmark/donor containers, zero model files, no `.env.deploy`, Docker Server
`29.7.2`, and the unrelated healthy Plex container preserved. No live provider
request, model load, host installation, or workload occurred.

The repository tip changed after this append and must be re-read from post-commit
parity commands; this checkpoint deliberately does not embed a self-referential
SHA. The strict live acceptance matrix remains open and blocked on owner-approved
current env/config, provider-served model identities, three model/donor inputs, and
redacted artifacts.

### L-326 | 2026-08-27T11:05:25Z | S5-ship&learn | gpt-5-codex | final transport handoff for this slice

After the companion-boundary commit, the detached Mac Studio testing retake was
passively fetched and checked out at `origin/testing`; its worktree is clean and
its local/remote refs agree. The Docker daemon was queried only through the
existing `/usr/local/bin/docker` binary and reports Server `29.7.2`. No Istara,
provider, Petals, benchmark, donor, or model-serving container is present; the
model directory is empty and the retake has no `.env.deploy`. The unrelated
healthy Plex container remains untouched. No host package, model, provider
request, or workload was started.

This closes the current deterministic audit/documentation slice. The final SHA
must be read from the post-append parity evidence rather than copied into this
ledger file. Resume at the owner-input provisioning gate, then run the strict
Docker-only provider, Petals, combined, two-call/long-horizon, three-rater
Fleiss/Krippendorff, reconciliation, human-Done/report, and teardown matrix.

### L-327 | 2026-08-27T11:07:28Z | S3-review/S5-ship&learn | gpt-5-codex | explicit acceptance metric contract

The release-facing ensemble contract now names the Research Spine acceptance
metrics explicitly: provider-served model identity, exact source-span grounding,
Fleiss' kappa, Krippendorff's alpha, reconciliation status, and human Done/report
promotion. The historical one-profile live orchestration benchmark remains
`evidence_role=companion`; its DAG, tool-selection, latency, and compute-capacity
metrics cannot substitute for those gates. A manifest regression test requires the
strict acceptance paths and all six metric IDs, while the benchmark registry and
Ensemble Health feature page expose the same boundary.

Verification passed: JSON validation, the manifest contract guard (`5` tests), the
real-user package (`87` tests), feature docs (`224` generated; `86/86` checked),
Ruff, and diff checks. No live provider request, model load, host installation, or
Mac Studio workload occurred. This append changes the tip; read the final SHA from
post-commit parity evidence. The live provider/Petals/combined matrix remains
blocked on owner-approved Docker-only env/config, three served model routes, donor
inputs, and redacted artifacts.

### L-328 | 2026-08-27T11:20:01Z | S2-execute/S3-review | gpt-5-codex | substantive coding payload oracle hardening

The deterministic Research Spine acceptance oracle now verifies the persisted
`CodeApplication` payload against the qualitative coding protocol instead of
accepting a row solely because it has a quote and route receipt. Every row must
carry a non-empty governed `code_id`, non-empty analytic `reasoning`, and a
numeric confidence in `[0, 1]`; when the selected evidence unit exposes
`start_offset`/`end_offset`, the persisted application must preserve both exact
offsets. The oracle records dedicated evidence arrays for missing payload,
invalid confidence, and offset mismatches, and includes those rows in the
fail-closed coverage gate. This closes a false-positive path where ORM defaults
or paraphrase-only applications could appear reconciled while violating the
required open-coding output schema.

Regression coverage now includes a three-donor fixture with missing code,
rationale, confidence, and a mismatched source offset; it must block the
multi-model Research Spine result and expose the exact invalid fields. The
Ensemble Health feature contract and generated site/manifest now document this
requirement and reference the regression suite.

Verification passed: focused Research Spine oracle (`28` tests), full real-user
benchmark harness (`88` tests), targeted Python contract/runner suite (`77`
tests), broader PI/Research Spine matrix (`245` tests), feature documentation
generation/check (`224` generated; `86/86` checked), and `git diff --check`.
Ruff was not applicable to the JavaScript files (its parser rejected the file
type); the package's `node --check` and test harness are the authoritative
syntax checks and passed. No live provider request, model load, host
installation, or Mac Studio workload occurred. The ledger append changes the
tip; final SHA and remote parity must be read from the post-commit evidence.
The strict Docker-only live matrix remains blocked on owner-approved current
env/config, three served model identities, donor inputs, and redacted artifacts.

### L-329 | 2026-08-27T11:22:34Z | S5-ship&learn | gpt-5-codex | deterministic verification and transport checkpoint

The new substantive payload oracle was verified end to end in the local
checkout. The focused Research Spine suite passes `28` tests, the full
real-user benchmark package passes `88`, the targeted contract/runner suite
passes `77`, and the broader PI/Research Spine matrix passes `245`. Feature
documentation regenerated cleanly (`224` generated artifacts; `86/86`
checked), and `git diff --check` is clean. Compass command evidence `228`-`233`
records those results. The earlier Ruff invocation against JavaScript was
discarded as a tool/type mismatch; Node syntax and package checks are the
applicable evidence and pass.

The intended six-file change (oracle, regression test, feature contract/site,
generated manifest, and this ledger) was committed and pushed as the current
`testing` tip. Compass evidence `234` records local `testing`/`origin/testing`
equality and a clean worktree. Evidence `235` records the passive Mac Studio
retarget through the existing SSH alias: detached retake and remote ref match,
clean worktree, Docker Server `29.7.2`, only unrelated `plex` running, zero
model files under `~/Istara-Projects/models`, and no `.env.deploy`. No host
package operation, provider request, model load, or benchmark workload ran.

The current synchronized SHA must be read from post-commit parity evidence,
not embedded in this file. The strict live provider/Petals/combined matrix,
three served model identities, semantic Fleiss/Krippendorff evidence,
same-session two-call/long-horizon receipts, reconciliation, human Done/report
promotion, and teardown remain blocked on owner-approved Docker-only current
env/config, donor/model inputs, and redacted artifacts.

### L-330 | 2026-08-27T11:32:59Z | S2-execute/S3-review | gpt-5-codex | reliability metric-domain oracle hardening

The acceptance oracle previously required only finite numeric reliability values
before applying the kappa threshold. It now validates the statistical domains
first: Fleiss/Cohen kappa must be finite and within `[-1, 1]`; Krippendorff
alpha must be finite and no greater than `1`, while negative alpha remains a
valid disagreement signal. A malformed response containing values such as
kappa `9` or alpha `2` therefore fails closed instead of entering the
reconciliation/promotion branch. Blocker evidence records each bound check and
whether any finite value was out of range.

Regression coverage adds an otherwise complete three-donor run with kappa `9`
and alpha `2`; both Research Spine acceptance flags remain false and the
diagnostic evidence identifies the invalid domains. Existing missing-metric and
below-threshold behavior remains unchanged. The Ensemble Health feature
contract and generated site/manifest document the bounded-metric rule, and the
external testing findings ledger records F-R9-105.

Verification passed: focused Research Spine oracle (`29` tests), complete
real-user benchmark package (`89` tests), feature documentation generation and
check (`224` generated artifacts; `86/86` checked), and `git diff --check`.
No live provider request, model load, host installation, or Mac Studio workload
occurred. The ledger append changes the tip; final SHA and remote/Mac Studio
parity must be recorded after the commit. The strict Docker-only live matrix
remains blocked on owner-approved current env/config, served model identities,
donor/model inputs, and redacted receipts.

### L-331 | 2026-08-27T11:34:50Z | S3-review/S5-ship&learn | gpt-5-codex | metric-domain evidence and parity checkpoint

Compass command evidence `241` records the focused reliability-domain regression
(`29` Research Spine oracle tests). Evidence `242` records the complete
real-user package (`89` tests), `243` records feature documentation generation
and validation (`224` generated artifacts; `86/86` checked), and `244` records
the clean diff check. The native Rust after-gate is record `261`; attached
Compass gate evidence `247` reports the inherited baseline gate status with
`new_issue_count=0`, no new forbidden dependencies, no new required paths, and
no new Python import cycles.

Commit `4842a62f` is pushed to `origin/testing`. Evidence `245` records the
post-push local/remote/Mac Studio parity check: all refs match, the detached
Mac Studio retake is clean, Docker Server is `29.7.2`, only unrelated Plex is
running, model-file count is zero, and `.env.deploy` is absent. No host package
operation, provider request, model load, or workload occurred.

This closes the deterministic metric-oracle slice. The live provider/Petals/
combined matrix, semantic three-model quality, same-session two-call and
long-horizon receipts, reconciliation, human Done/report promotion, and
teardown remain blocked on current owner-approved Docker-only env/config,
served identities, donor/model inputs, and redacted artifacts. The next audit
pass must preserve this fail-closed boundary while checking any remaining
engine-selector and Research Spine acceptance gaps.

### L-332 | 2026-08-27T11:47:44Z | S2-execute/S3-review | gpt-5-codex | project-scoped Petals preflight hardening

The deeper provider/Petals audit found that legacy/Istara chat's stub-plane
preflight called `has_non_stub_source()` without the request project id. The
Pi resolver also stopped at the first catalog entry, so an unauthorized
project-scoped Petals projection could create a false admission or hide a later
authorized donor. The resolver now carries `project_id` through
`has_non_stub_source()` and `resolve_model_source()`, passes it to
`PiModelManager.resolve()`, and continues over candidates that are not admitted;
the `/chat` route supplies the project scope before any side effect. The living
model-controls contract documents this shared governed path, and external
finding F-R9-106 records the original gap and its residual live-proof boundary.

Verification passed: `pytest -q tests/test_model_source.py
tests/test_chat.py` (`25` tests), the scoped route/source subset (`12` tests),
Ruff on the changed resolver/test files, feature documentation generation and
check (`224` generated artifacts; `86/86` checked), and `git diff --check`.
The full `chat.py` Ruff file check remains an inherited baseline failure with
unrelated pre-existing import/order/line-length issues; no such cleanup was
introduced in this slice. The strict live provider/Petals/combined matrix,
semantic three-model outputs, Fleiss/Krippendorff quality, reconciliation,
human Done/report promotion, and Docker-only Mac Studio execution remain
blocked on current owner-approved env/config, served identities, donor/model
inputs, and redacted receipts.

### L-333 | 2026-08-27T11:52:03Z | S3-review/S5-ship&learn | gpt-5-codex | broad deterministic regression and evidence checkpoint

The project-scoped preflight remediation was exercised against the full
deterministic surface, not only its new unit cases. Compass evidence `251`
records the focused source/chat contract tests (`25` passed), `252` records the
real-user benchmark package (`89` passed), and `253` records the broader PI,
Pi-benchmark, Research Spine validity, and end-to-end matrix (`701` passed,
`5` skipped with runtime warnings treated as errors). Evidence `254` records
changed-file Ruff plus `git diff --check`, and `255` records feature-doc
generation/check (`224` generated; `86/86` checked). Evidence `256` records
the native Rust after-gate: `new_issue_count=0`, `new_failures=0`, with the
repository's inherited gate status still `fail` and no new warnings.

No live provider request, model load, host installation, or Mac Studio
workload occurred. The strict provider/Petals/combined live matrix, semantic
three-model output quality, Fleiss/Krippendorff evidence, reconciliation,
human Done/report promotion, and Docker-only Mac Studio execution remain
blocked on current owner-approved env/config, served identities, donor/model
inputs, and redacted receipts. The next step is transport, push, and final
detached-checkout/Docker parity evidence for this checkpoint.

### L-334 | 2026-08-27T11:53:16Z | S5-ship&learn | gpt-5-codex | transport and Docker-only parity checkpoint

The scoped preflight fix is now transported as commit `e9933a34` on
`origin/testing`. Compass evidence `257` records local `testing`,
`origin/testing`, and the detached Mac Studio retake all at that SHA with clean
worktrees. The retake was refreshed only with Git fetch/reset inside the
disposable testing checkout; Docker remains the sole runtime path (`29.7.2`),
only unrelated Plex is running, the model artifact count is zero, and
`.env.deploy` is absent. No host package installation, Python/Node benchmark,
provider request, model load, Istara/Petals container, or workload was started.

The remaining acceptance work is therefore not hidden by a stale checkout:
the deterministic engine/provider/Petals contracts are green, while live
provider-served three-model quality, Fleiss/Krippendorff values,
source-grounded coding, reconciliation, human Done/report promotion, both
engine HTTP execution with live providers, two-call/long-horizon receipts,
Petals consent/health/revocation, redaction, and teardown still require the
owner-approved Docker-only Mac Studio inputs and run window.

### L-335 | 2026-08-27T12:06:03Z | S2-execute/S3-review | gpt-5-codex | Docker-only long-horizon proof hardening

The acceptance harness had a caller-controlled long-horizon proof: setting
`ISTARA_BENCHMARK_LONG_HORIZON_VERIFIED=1` could mark the combined two-call
workload verified even when the Docker runner had not executed the Python
workload. `tests/real_user_benchmark/run.mjs` now accepts that marker only when
`ISTARA_BENCHMARK_DOCKER_RUNNER=1` is also active, and the topology contract
asserts declaration order and the fail-closed coupling. The Ensemble Health and
Findings / Reports living contracts document that a host/direct invocation cannot
turn a skipped horizon into acceptance evidence. External finding F-R9-107
records the gap and its residual live-proof boundary.

Compass evidence `260` records the real-user package (`89` passed), `261`
records feature-doc generation/check (`224` generated artifacts; `86/86`
checked), `262` records the native Rust after-gate (`new_issue_count=0`,
`new_failures=0`, inherited gate status `fail`), and `263` records
`git diff --check`. The deterministic package remains green; no live provider
request, model load, host installation, or Mac Studio workload was started.

Next: commit/push this checkpoint, refresh the disposable detached Mac Studio
checkout to the final branch tip, and preserve the explicit boundary that live
three-model semantic quality, Fleiss/Krippendorff values, reconciliation,
human Done/report promotion, Petals cooperation, redaction, teardown, and
two-call/long-horizon receipts remain unverified until owner-approved
Docker-only inputs exist.

### L-336 | 2026-08-27T12:07:05Z | S5-ship&learn | gpt-5-codex | final Docker-only parity for oracle checkpoint

Commit `80bc2b5d` is pushed to `origin/testing`. Compass evidence `264`
records the post-push parity audit: local `testing`, `origin/testing`, and the
detached Mac Studio retake all resolve to `80bc2b5d`; the retake is clean;
Docker Server is `29.7.2`; only unrelated Plex is running; model-file count is
zero; `.env.deploy` is absent; and no provider request, model load, package
installation, or Istara/Petals workload was started. The Docker-only boundary
therefore remains intact while the live acceptance gate is unprovisioned.

The long-horizon caller-spoof oracle hardening and its 89-test deterministic
package are transported. The next review slice is static coverage of every
public engine/ensemble combination and any remaining bypass of project-scoped
Pi Model Management; live three-model semantic quality, reliability values,
reconciliation, human Done/report promotion, Petals cooperation, redaction,
teardown, and two-call/long-horizon receipts remain unverified.

### L-337 | 2026-08-27T12:30:00Z | S2-execute/S3-review | gpt-5-codex | AdaptiveSelector Pi-authority remediation

The static engine audit found a real authority split: `AdaptiveSelector` chose
`dual_run`/`full_ensemble` from the retired global `llm_router`/ComputeRegistry
inventory, while the actual `AgenticDispatcher` ensemble call resolved through
the project-scoped Pi Model Management catalog. That could count a donor the
Pi manager would reject, miss an admitted Pi endpoint, and make the selected
validation method disagree with the subsequent governed dispatch.

`PiModelManager.available_model_identities(project_id=...)` now exposes a
non-secret, distinct-model identity view using the same admission predicate as
`resolve_distinct`; it applies Petals project allowlists and reserved namespace
checks without materializing settings credentials. `AdaptiveSelector` now awaits
the engine-owned dispatcher's manager, ensures the read-only DB/Petals projection,
and uses that identity view. If the catalog cannot be inspected it fails closed
to the existing historical/default path; it no longer consults the retired
router inventory. Tests cover three-model selection, constrained Self-MoA,
cross-project donor exclusion, project-id forwarding, and no-secret
materialization. The Ensemble Health living contract now documents this shared
authority and the generated feature site/manifest were regenerated.

Focused verification passed: `pytest -q tests/test_adaptive_validation.py
tests/pi_production/test_w1_agentic_contract.py
tests/pi_production/test_w1_dispatcher_authority.py
tests/pi_production/test_w7_validation.py
tests/pi_production/test_w7_pi_manager_integration.py
tests/pi_production/test_ensemble_identity_parity.py
tests/pi_production/test_legacy_long_horizon.py
tests/petals_bridge/test_petals_bridge.py` (`130 passed`), Ruff on all changed
Python files, `git diff --check`, and feature docs (`224` generated artifacts;
`86/86` checked). This is deterministic authority/provenance coverage only;
it does not prove live model quality, Fleiss/Krippendorff values, reconciliation,
human Done/report promotion, Petals serving, or Docker-only Mac Studio execution.
The after-gate, transport, and final detached parity must be recorded after the
next broader matrix.

### L-338 | 2026-08-27T12:22:05Z | S3-review/S5-ship&learn | gpt-5-codex | broad deterministic and after-gate checkpoint

The strict broader deterministic matrix completed with `706 passed, 5 skipped`
under `python -m pytest -q -W error::RuntimeWarning tests/pi_production
tests/pi_benchmark tests/test_research_validity_contract.py
tests/test_research_spine_end_to_end.py tests/test_validation_project_scope.py`.
The focused authority/ensemble/Petals matrix remains `130 passed`; changed-file
Ruff and `git diff --check` are clean; feature documentation regenerated `224`
site artifacts and passed `86/86` checks. Compass evidence `269` records the
broad matrix, `270` records the focused/lint/docs checks, `271` records native
after-gate `267` with `new_issue_count=0` and no new forbidden dependencies,
cycles, or required-path gaps, and `272` records the Build Stream/external
finding artifacts. The repository-wide gate remains `fail` only for inherited
complexity, route/type drift, secret-flow, and suppressed large-ledger debt.

The new manager regression was deliberately moved out of the hotspot-heavy W1
module after the first after-gate exposed a newly introduced file-complexity
warning; the final after-gate has no new issues. No live provider request, model
load, host install, or Mac Studio workload occurred. This checkpoint proves
deterministic authority alignment and regression safety only. Live provider,
Petals, combined, three-served-model semantic quality, Fleiss/Krippendorff
values, source-grounded coding, reconciliation, human Done/report promotion,
two-call/long-horizon receipts, redaction, and teardown remain blocked on
owner-approved Docker-only inputs. Commit/push and exact detached parity must
follow this ledger append.

### L-339 | 2026-08-27T12:40:00Z | S5-ship&learn | gpt-5-codex | post-transport Mac Studio parity

The AdaptiveSelector authority remediation and its ledger checkpoint were
transported as commit `59621145f5aa49879ad39a115d1e29e2bea1d8f1` on
`origin/testing`. Before this append, the local `testing` branch, remote
`origin/testing`, and the detached Mac Studio retake all resolved to that SHA;
the remote checkout was clean. The only observed container was unrelated
`plex`; Docker Server was `29.7.2`; the model-file count under the testing model
directory was `0`; `.env.deploy` was absent; and no container, image pull,
provider request, package installation, or model load was started. This is
transport/parity evidence, not live semantic or Research Spine acceptance.

Appending this record changes the branch tip, so the detached parity check must
be repeated after the documentation checkpoint is committed. Continue the
static audit from the updated tip and preserve the explicit live gate: no
three-served-model Fleiss/Krippendorff, source-span grounding, reconciliation,
human Done/report promotion, two-call/long-horizon, Petals cooperation,
redaction, or teardown claim is valid without owner-approved Docker-only
runtime inputs and receipts.

### L-340 | 2026-08-27T12:30:00Z | S2-execute/S3-review | gpt-5-codex | invalid validation-method fail-closed remediation

The static validation audit found that the legacy `ValidationExecutor` returned
`passed=True` and `confidence=0.5` for an unknown method name. A stale caller or
configuration typo could therefore create a validation-looking result without
running any validator. The unknown branch now returns `passed=False`,
`confidence=0.0`, and explicit `status=invalid_method`,
`reason=unknown_validation_method`, and `skill_name` details. The integrity
regression now asserts the complete fail-closed result, and the Ensemble Health
contract documents the boundary. This is a defensive compatibility fix; W9's
current product ensemble path remains the shared dispatcher-backed
`backend/app/core/validation.py` surface.

Verification after the code/doc change: the affected Research Spine/integrity
suite passed (`75` tests), the changed executor passed Ruff, feature docs
regenerated `224` artifacts and passed `86/86` checks, and `git diff --check`
passed. The external findings register records this as F-R9-109. No provider
request, model load, host installation, or Docker workload was started. Live
three-model semantic quality, served-identity receipts, formal reliability,
source grounding, reconciliation, human Done/report promotion, Petals
cooperation, two-call/long-horizon execution, and teardown remain blocked on
owner-approved Docker-only inputs.

### L-341 | 2026-08-27T12:50:00Z | S2-execute/S3-review | gpt-5-codex | report-level consensus wording boundary

The report audit found that `ReportManager._compose_section(source="ensemble_scores")`
described stored response-level consensus scores as “Fleiss' Kappa + cosine
similarity across multiple model runs.” That text overclaimed the Research Spine:
these values are operational heuristics and do not represent an independent
coded evidence-unit matrix. Formal Fleiss/Cohen/Krippendorff reliability is
valid only in a governed coding run with evidence-unit, codebook, route, and
promotion handles.

The section now calls the metric an “average response-level consensus score,”
labels it as a heuristic signal from Self-MoA, Dual Run, or Adversarial Review,
and explicitly says it is not Fleiss' Kappa and cannot establish formal Research
Spine reliability. A W5 regression checks the disclosure and rejects the old
sentence. The Ensemble Health living contract and generated feature site were
regenerated.

Verification: the W5 report-manager suite, report integrity suite, and validation
integrity suite passed (`44` tests total); the non-hanging validity-contract
subset passed (`31 passed, 1 deselected`). The full validity-contract module
still idles at the existing survey-ingestion test and was interrupted after
isolation; this is not counted as a pass or as a regression from this wording
change. Feature docs report `224` generated artifacts and `86/86` checks;
`git diff --check` passes. Ruff is clean for the new W5 test, while the legacy
report-manager file retains its pre-existing 31 violations. Compass after-gate,
transport, and detached Mac Studio parity remain to be recorded for this
checkpoint. No live provider request, model load, host installation, or Docker
workload was started; all semantic, reliability, source-grounding, reconciliation,
human Done/report, Petals, two-call/long-horizon, and teardown claims remain
blocked on owner-approved Docker-only inputs.

### L-342 | 2026-08-27T12:48:00Z | S5-ship&learn | gpt-5-codex | report wording transport and detached parity

The report-consensus boundary fix and L-341 checkpoint are transported as
commit `3112e188` on `origin/testing`. Local `testing`, `origin/testing`, and
the detached Mac Studio retake all resolve to that SHA; both worktrees are
clean. The retake reports Docker Server `29.7.2`, only unrelated `plex` is
running, model-file count is `0`, and `.env.deploy` is absent. The checkout was
refreshed through Git only; no Docker workload, image pull, host installation,
provider request, or model load was started.

This parity proves transport and the Docker-only boundary, not live semantic
quality. The remaining Research Spine acceptance gates—three independently
served model identities, source-span grounding, independent coded evidence-unit
matrices, Fleiss/Cohen/Krippendorff reliability, reconciliation, human
Done/report promotion, Petals cooperation/revocation, same-session two-call and
long-horizon receipts, redaction, and teardown—remain unverified until
owner-approved Docker-only runtime inputs and redacted receipts exist.

### L-343 | 2026-08-27T12:56:07Z | S2-execute/S3-review | gpt-5-codex | cross-engine validation provenance coverage

The next static Research Spine audit compared the W7 validation unit tests
with the actual dispatcher/engine seam. Existing W7 tests stubbed
`agentic.ensemble`, proving purpose/verb shape and fail-closed fallback, while
the public-selector identity test exercised the real Pi service but not the
`dual_run`, `full_ensemble`, and `self_moa` validation functions themselves.
That left a coverage gap around whether legacy/Istara mode reaches the same
Pi-owned catalog as Pi mode at the validation facade.

The deterministic identity supervisor now emits both response text and the
provider-served model receipt. A new integration regression drives the real
validation functions through both global engine branches, using one injected
`PiExecutionService`/`PiModelManager`, and asserts project-scoped endpoint and
served-model provenance for dual-run (two identities), full ensemble (three
identities), and Self-MoA (one identity reused across temperatures). It also
asserts all three remain response-level signals with
`formal_reliability=false` and `research_spine_eligible=false`.

That regression exposed a concrete metadata omission: `self_moa()` returned
route evidence but no `models_used` list. The validation result now emits this
list from the same served-route helper as dual-run and full ensemble. The
Ensemble Health contract records that Self-MoA remains single-model assurance
and must not be counted as independent Research Spine raters. The external
findings register records F-R9-111.

Verification so far: the focused real-service suite passes (`2` tests), Ruff
passes on the changed validation/test files, and `git diff --check` passes. No
provider request, model load, host installation, or Docker workload was
started. Next: run the affected W7/identity/dispatcher matrix, run the native
after-gate, transport this checkpoint, and re-check detached Mac Studio parity
before continuing the Research Spine acceptance audit. Live three-model
semantic quality, formal reliability, source grounding, reconciliation,
human Done/report promotion, Petals cooperation, two-call/long-horizon, and
teardown remain blocked on owner-approved Docker-only inputs and redacted
receipts.

### L-347 | 2026-08-27T13:12:54Z | S5-ship&learn | gpt-5-codex | provenance fix transport and Docker-only parity

Commit `cb7b77aa` (incomplete-provenance item-level reconciliation outputs,
regression, living feature docs, and this ledger checkpoint) is pushed to
`origin/testing`. The detached Mac Studio checkout `~/istara-testing-retake-47bf`
was refreshed from `origin/testing` and resolves to the exact same SHA; it is
clean. Passive Docker inspection reports Server `29.7.2`, only unrelated
`plex` running, `MODEL_FILES=0` under the protected artifact roots, and
`.env.deploy` absent. The check used Git and the existing Docker binary only;
no container, image pull, provider request, model load, or host installation
was started.

This proves transport and the Docker-only boundary, not live semantic quality.
The remaining acceptance gates—three independently served model identities,
source-grounded coding, Fleiss/Cohen/Krippendorff reliability, reconciliation,
human Done/report promotion, Petals cooperation/revocation, same-session
two-call and long-horizon receipts, redaction, and teardown—remain blocked on
owner-approved Docker inputs and redacted receipts. The ledger append itself
creates a docs-only tip; refresh detached parity again after committing it.

### L-344 | 2026-08-27T13:02:00Z | S5-ship&learn | gpt-5-codex | validation provenance transport and Docker parity

The cross-engine validation provenance fix and L-343 checkpoint are
transported as commit `cae80e51` on `origin/testing`. Local `testing`,
`origin/testing`, and the detached Mac Studio testing checkout resolve to this
SHA; the remote checkout is clean. Passive Docker inspection reports Server
`29.7.2`, only unrelated `plex` running, no model files under the protected
artifact roots, and no `.env.deploy`. Git refresh only; no container, image,
provider, model, or host installation was started.

This parity proves transport and the Docker-only boundary, not live semantic
quality. The remaining Research Spine gates—three independently served model
identities in a real run, source-span grounding, independent coded evidence
units, Fleiss/Cohen/Krippendorff reliability, reconciliation, human
Done/report promotion, Petals cooperation/revocation, same-session two-call
and long-horizon receipts, redaction, and teardown—remain unverified until
owner-approved Docker-only inputs and redacted receipts exist. Continue the
static audit from this tip; the append itself requires one final detached
parity check after it is committed.

### L-345 | 2026-08-27T13:05:16Z | S2-execute/S3-review | gpt-5-codex | incomplete provenance item-status contract

The next Research Spine audit traced `evaluate_reliability_gate()` through its
service consumer and the existing integrity tests. The `require_rater_provenance`
fail-closed branch correctly returned `promotion_status=needs_reconciliation`,
but unlike every other early-exit branch it omitted `item_promotion_statuses`,
`accepted_evidence_unit_ids`, and `reconciliation_evidence_unit_ids`. The service
currently reconstructs a fallback, but direct callers and audit consumers could
observe an incomplete result contract and lose the exact unit-level remediation
set.

The branch now emits all three fields from the same matrix helper used by duplicate,
independence, conflict, missing-rating, and insufficient-model exits. A regression
in `tests/test_research_integrity_metrics.py` asserts the complete one-unit
reconciliation payload. Compass Forge impact/why/test-impact were run for the
production module and regression surface, and the pre-gate recorded no new issues;
the changed production module passes Ruff, the focused test passes, and
`git diff --check` passes. The test module still reports pre-existing unused-import
Ruff violations when linted directly; no unrelated cleanup was made.

No provider request, model load, host installation, or Docker workload was started.
Next: run the affected full deterministic reliability/ensemble matrix, feature-doc
generation, after-gate, evidence, commit/push, and detached Mac Studio parity check.
Live three-model semantic quality, formal provider reliability, source grounding,
reconciliation, human Done/report promotion, Petals cooperation, two-call/
long-horizon execution, and teardown remain blocked on owner-approved Docker inputs
and redacted receipts.

### L-346 | 2026-08-27T13:10:45Z | S2-execute/S3-review | gpt-5-codex | reliability provenance verification and gate

The incomplete-provenance contract fix and its living documentation are ready
for transport. Split verification completed with `28 passed` in
`tests/test_research_integrity_metrics.py`, `31 passed, 1 deselected` in the
non-hanging Research Spine contract subset, and `89 passed` across the
cross-engine ensemble, W7 validation, dispatcher authority, and agentic
contract suites, all under `-W error::RuntimeWarning`. Feature documentation
regeneration/check passed (`224` generated artifacts; `86/86` features), the
changed production module passes Ruff, and `git diff --check` passes.

Compass Forge after-gate record `275` reports `new_issues=[]`, no new failures,
and no new architecture/import/contract drift; the repository's known
complexity, route/type, and secret-flow findings remain inherited. Direct Ruff
on the legacy integrity test module still reports its pre-existing unused
imports and was not broadened into this change. The earlier combined command
was intentionally interrupted after `40 passed` when it reached the known
async/database idle hang in the survey-ingestion test; the isolated subset is
the authoritative contract evidence.

No provider request, model load, host installation, or Docker workload was
started. Next: commit/push and verify the detached Mac Studio checkout at the
exact resulting SHA, then resume static audit work. Live three-model semantic
quality, provider-served reliability, source grounding, reconciliation, human
Done/report promotion, Petals cooperation, two-call/long-horizon execution,
and teardown remain blocked on owner-approved Docker inputs and redacted
receipts.

### L-348 | 2026-08-27T13:27:30Z | S2-execute/S3-review | gpt-5-codex | Pi endpoint authority guard and deterministic verification

The static authority audit found that POST `/api/settings/pi-endpoints`
already rejected the reserved `pi-petals-*` namespace and built-in
`pi-deepseek-default`, but PUT and DELETE did not. A stale or malformed
persisted settings row could therefore be mutated or removed through
user-managed CRUD, breaking the boundary between Pi Model Management, the
consented Petals projection, and the built-in resolver identity.

`backend/app/api/routes/settings.py` now applies one fail-closed guard to PUT
and DELETE as well as the existing POST boundary. A regression in
`tests/pi_production/test_pi_catalog_ux.py` injects both legacy identities and
asserts that neither mutation succeeds or removes the row. The focused
endpoint matrix passes (`5 passed, 9 deselected`); the broader settings/Pi
matrix passes (`43 passed`); Ruff, `git diff --check`, and feature-doc
regeneration/check pass (`224` generated artifacts; `86/86` features).

Compass Forge before-gate record `276` captured the repository baseline for
this change. The after-gate and task evidence remain to be attached before
transport. No provider request, model load, host installation, or Docker
workload was started. The Mac Studio live three-model semantic gate remains
blocked on owner-approved Docker-only provider inputs and redacted receipts;
this deterministic guard proves only the management authority contract.

Next: run the native after-gate, attach command evidence, commit/push the
guard and documentation, refresh the detached Mac Studio checkout to the
resulting SHA, and append the parity receipt before continuing the static
ensemble/test-configuration audit.

### L-349 | 2026-08-27T13:31:20Z | S5-ship&learn | gpt-5-codex | Pi CRUD transport and Mac Studio Docker-only parity

The Pi endpoint authority guard, regression, living feature documentation,
and this ledger checkpoint are transported as commit `8b4d8fe0` on
`origin/testing`. Local `testing`, `origin/testing`, and the detached Mac
Studio checkout `~/istara-testing-retake-47bf` resolve to the exact same SHA;
the remote checkout is clean.

The passive Mac Studio check used only the existing absolute Docker binary
`/usr/local/bin/docker` because the non-interactive SSH PATH omits it. Docker
Server is `29.7.2`; only unrelated `plex` is running; `MODEL_FILES=0` under
the protected artifact roots; and `.env.deploy` is absent. No container,
image pull, provider request, model load, host installation, or destructive
cleanup was performed.

This proves Git transport and the Docker-only boundary, not live semantic
quality. Three independently served model identities, source-grounded coding,
Fleiss/Cohen/Krippendorff reliability, reconciliation, human Done/report
promotion, Petals cooperation/revocation, same-session two-call and
long-horizon receipts, redaction, and teardown remain unverified. Next is a
static audit of the actual ensemble/test harness and its provider-served
identity assertions; a live run still requires owner-approved Docker-only
model/provider inputs.

### L-350 | 2026-08-27T13:39:00Z | S2-execute/S3-review | gpt-5-codex | deterministic entrypoint and Research Spine acceptance-path audit

The real-user benchmark's authoritative deterministic command is
`npm run check`, and it passed all 89 Node tests plus syntax checks. Before this
checkpoint, `npm --prefix tests/real_user_benchmark test` failed because the
package exposed no `test` script. The package now defines `test` as an alias for
`check`, so agents and CI have one conventional, non-live entrypoint. Re-running
`npm --prefix tests/real_user_benchmark test` passed all 89 tests. This change
does not start Docker, load a model, contact a provider, or alter live workload
selection.

The substantive audit found a more important open harness gap. A successful
three-model coding run persists code applications as `review_status=pending`
and `reconciliation_status=unreconciled`. `validateCodingRun()` correctly
requires every application to be accepted/reconciled/approved and requires a
same-run accepted/revised reconciliation decision, but `run.mjs` only approves
Task rows. It never calls the per-application review/reconciliation endpoint.
Therefore a live benchmark can prove distinct served model identities,
source-grounded open-code payloads, and Fleiss/Krippendorff metrics, yet still
cannot reach the accepted Research Spine state. This is a fail-closed
limitation (not a false positive), but it makes the current “accepted coding”
acceptance profile incomplete unless a separately governed reviewer action is
performed.

Required remediation before claiming end-to-end Research Spine acceptance:

1. Add an explicit, opt-in benchmark reconciliation phase (default off) that
   fetches only applications from the current coding run, verifies exact run,
   project, evidence-unit, source-span, coder, and served-model provenance, and
   submits one per-application review decision through the public API. Never
   use bulk approval or silently mark model output human-approved.
2. Give that phase a distinct synthetic-test reviewer identity and receipt field
   (for example `benchmark_synthetic_reconciliation=true`) so reports cannot be
   mistaken for real human research acceptance. The default provider/combined
   profiles must remain blocked when the opt-in is absent.
3. Add deterministic tests for: disabled-by-default behavior; exact run scoping;
   rejection of foreign application IDs; rejected/modified decisions remaining
   blocked; accepted/revised decisions becoming eligible only after all rows are
   reconciled; and preservation of source-span/model provenance in the receipt.
4. Add a Docker-only live acceptance profile that runs the phase against three
   independently served donor routes, then checks the full chain
   `Evidence Units -> three coders -> Fleiss + Krippendorff companion ->
   reconciliation -> approved Done task -> report gate`, with redacted receipts.
   Keep real human approval as a separate non-automated gate; synthetic
   reconciliation is test evidence, not publishable research evidence.
5. Strengthen live traceability assertions beyond non-empty summary keys:
   verify graph edges, exact coding-run/application/decision counts, report-gate
   status, task Done approval, and protected provenance fields. Record any
   missing edge as a blocker rather than allowing a structural “present” flag.

The package alias closes only the deterministic invocation defect. The
reconciliation gap remains open and is now the next implementation target. No
provider request, model load, host installation, or Docker workload was
started; Mac Studio execution remains blocked on owner-approved Docker-only
model/provider inputs, a valid `.env.deploy`, and redacted receipts.

### L-351 | 2026-08-27T13:44:00Z | S5-ship&learn | gpt-5-codex | deterministic entrypoint transport and Mac Studio parity

The benchmark package alias and the generated feature-manifest timestamp were
transported as commits `d62bc3f1` and `d69eedda` on `origin/testing`. The local
`testing` checkout and detached Mac Studio retake `~/istara-testing-retake-47bf`
were refreshed to `d69eedda` and are clean. Passive Docker inspection used only
the existing `/usr/local/bin/docker`: Server `29.7.2`, unrelated `plex` only,
zero files under `~/Istara-Projects/models`, and no retake `.env.deploy`.

`npm --prefix tests/real_user_benchmark test` is now the conventional
deterministic entrypoint and passed all 89 tests. This parity receipt proves
transport and Docker-only boundary compliance, not live model quality or
Research Spine acceptance. F-R9-114/L-350 remains open: the live harness still
needs a separately governed, opt-in synthetic reconciliation phase and stronger
traceability assertions before it can demonstrate the complete accepted path.
No provider request, model load, host installation, image pull, or benchmark
workload was started.

### L-352 | 2026-08-27T13:50:00Z | S2-execute/S3-review | gpt-5-codex | stale coding-run recovery fail-closed fix

The static audit found that a timed-out coding POST could recover the first
completed project run returned by the API, even when that run predated the
current request. A prior accepted run could therefore be mistaken for the
current three-model Research Spine proof. The recovery path now records the
coding request start time, accepts only a completed run whose server
`started_at`/`created_at` is within a one-minute clock-skew window, and rejects
stale completed rows when no active candidate exists. Invalid correlation
timestamps also fail closed. A regression proves a stale accepted run cannot
be recovered; the existing server-side completion recovery remains covered.

Verification: the focused Research Spine probe suite passes (`30` tests), the
full deterministic benchmark suite passes (`90` tests), feature-doc generation
and checks pass (`224` artifacts; `86/86` features), and `git diff --check`
passes. Compass Forge impact/why was run for both probe files; the before gate
is record `281`. The after gate and task evidence remain to be attached before
transport.

This closes a deterministic stale-run false-positive risk only. The separate
F-R9-114/L-350 reconciliation gap remains open: the live harness still cannot
reach accepted coding without an explicitly governed per-application review
phase. No provider request, model load, host installation, Docker image pull,
or benchmark workload was started.

### L-353 | 2026-08-27T14:05:00Z | S2-execute/S3-review | gpt-5-codex | current-run GraphRAG traceability binding

The acceptance audit found a second false-positive seam: the benchmark marked
`researchSpineTraceability` true from project-level summary keys and marked
`ragTraceabilityEvidence` true from the graph contract alone. Neither flag was
bound to the coding run just created by the benchmark. A stale or unrelated
project payload could therefore make traceability appear present while the
current run had no source-grounded application or graph record in the response.

The probe now records `traceability_coding_run` diagnostics and, when coding is
enabled, requires the current run ID in `coding_runs`, at least the expected
number of current-run code applications, and a current-run
`evidence_unit -> coded_as -> code_application` edge. Both traceability flags
fail closed when that binding is missing. The check is intentionally scoped to
the current coding validation request; plan-only/non-coding profiles retain
structural traceability reporting without inventing a run.

Deterministic coverage now includes a positive graph-bound acceptance fixture
and a regression where a fully reliable three-model run is deliberately omitted
from project traceability. Focused Research Spine probes pass `31/31`.
Compass Forge before-gate record `283` was captured for this change; after-gate,
task evidence, docs regeneration, and transport remain pending. F-R9-114 remains
open because the live harness still cannot create human reconciliation decisions.
No provider request, model load, host installation, Docker image pull, or live
benchmark workload was started.

### L-354 | 2026-08-27T14:08:00Z | S5-ship&learn | gpt-5-codex | traceability-binding transport and Docker parity

The current-run traceability binding fix and its deterministic regression were
committed as `3190b0d4` and pushed to `origin/testing`. Local `testing`,
`origin/testing`, and detached Mac Studio checkout
`~/istara-testing-retake-47bf` all resolve to
`3190b0d464c78fed100e8bdf463c11f6ba5d54a9` and are clean. Compass Forge task
evidence `309` records the exact transport and parity commands.

Passive Docker inspection used only the existing `/usr/local/bin/docker` on the
Mac Studio: Server `29.7.2`, unrelated `plex` only, zero files under
`~/Istara-Projects/models`, and no retake `.env.deploy`. No image pull, model
load, provider request, host package installation, data deletion, or benchmark
workload was started. F-R9-114 remains open for governed synthetic/live
reconciliation; F-R9-116 is fixed in the deterministic acceptance harness.

### L-355 | 2026-08-27T14:18:00Z | S2-execute/S3-review | gpt-5-codex | project-scoped chat catalog admission

The PI/Petals audit found that runtime resolution already applied the donor
allowlist when a project id was supplied, but `GET /api/chat/model-catalog`
called the global `PiModelManager.catalog()` view. The chat picker could
therefore mark another project's projected Petals identity as configured and
selectable, only for the subsequent turn to fail at resolver/bridge admission.
This was a management-plane/UI mismatch, not a provider-quality result.

`PiModelManager.catalog(project_id=...)` now reuses the same fail-closed
admission predicate as `resolve`/`resolve_distinct`; settings and benchmark
callers retain the unscoped catalog, while the chat route passes its authorized
project id. A regression covers two project allowlists and confirms that
settings secrets remain unmaterialized. The chat architecture and legacy
compatibility feature pages now document the scoped/global distinction.

Verification: manager health `4/4`, Petals bridge `34/34`, the existing chat
catalog/usage route check `1/1`, W1 authority/contract slice `55/55`, and the
combined PI/Petals/chat/ensemble/research-spine slice `67 passed` (one
pre-existing aiosqlite event-loop teardown warning in the full mixed run).
The deterministic benchmark remains `91/91`; feature-doc regeneration/check
passes (`224` generated artifacts; `86/86` features); `git diff --check` passes;
Compass Forge after-gate record `286` reports no new forbidden dependencies,
import cycles, or missing paths. F-R9-117 is fixed. F-R9-114 remains open for
governed synthetic/live reconciliation.

No provider request, model load, host installation, Docker image pull, or live
benchmark workload was started. Mac Studio remains Docker-only and passive.

### L-356 | 2026-08-27T14:22:00Z | S5-ship&learn | gpt-5-codex | catalog-fix transport and Mac Studio parity

The project-scoped catalog fix and its docs/tests are committed as
`5790e2dcb0fc2222ddf7b5affb77bf192f19c644` and pushed to `origin/testing`.
Local `testing`, `origin/testing`, and detached Mac Studio retake
`~/istara-testing-retake-47bf` resolve to that exact SHA and are clean.

Passive SSH inspection used the configured `macstudio` alias and only the
existing `/usr/local/bin/docker` fallback: Docker Server/Client `29.7.2`,
unrelated `plex` only, zero files under `~/Istara-Projects/models`, and no
retake `.env.deploy`. No image pull, model load, provider request, host package
installation, data deletion, or benchmark workload was started. F-R9-117 is
fixed in the deterministic catalog boundary; F-R9-114 remains open for
governed synthetic/live reconciliation and human Done/report proof.
Compass Forge task evidence `313` records the exact commit, remote, detached
checkout, Docker, and no-workload parity values.

### L-357 | 2026-08-27T14:23:19Z | S3-review | gpt-5-codex | Phase 9

Did: Re-oriented through the native Compass Forge `status`, `next`, and compact
`agent-brief`; reconciled the Build Stream status block against ledger entries
L-355/L-356; confirmed local `testing`, `origin/testing`, and the detached Mac
Studio retake remain aligned at `633ff5c0` and clean. Continued the static audit
of `exerciseResearchSpineValidation` and `validateCodingRun`.

Result: The remaining acceptance gap is confirmed rather than cleared: the
benchmark can inspect three-model coding, served model identities, donor routes,
Fleiss/alpha metrics, raw evidence-unit coverage, and current-run traceability,
but it has no governed per-application reconciliation action in the live flow.
The backend correctly keeps code applications pending/unreconciled and rejects
bulk approval, so the benchmark must not synthesize human approval silently.
Next review decision is whether to add an explicitly opt-in, provenance-labeled
diagnostic reconciliation path or keep reportability blocked while exposing a
separate ensemble-coding diagnostic signal.

Verified: `compass-forge status`; `compass-forge next`; `compass-forge agent-brief
--compact`; `git status --short --branch`; `git log -4 --oneline`; targeted static
inspection of `tests/real_user_benchmark/run.mjs`,
`tests/real_user_benchmark/lib/research-spine-probes.mjs`,
`backend/app/api/routes/code_applications.py`, and
`backend/app/services/research_validity_service.py`.

Next: Choose and implement the smallest truthful diagnostic/reconciliation
improvement, with tests and feature-doc/ledger evidence; preserve the Docker-only
live gate until provider-served identities and model inputs exist.

### L-358 | 2026-08-27T14:31:00Z | S2-execute/S3-review | gpt-5-codex | separate ensemble evidence from accepted reportability

The benchmark previously exposed only `codingValidation` and
`multiModelResearchSpineValidation`. Because the latter also required governed
per-application reconciliation, a live run that genuinely proved three served
model identities, source-grounded coder coverage, Fleiss kappa, and the
Krippendorff alpha companion could not distinguish that useful diagnostic result
from a failure to complete the later human gate. The result was safe for
reportability, but incomplete for auditing whether the ensemble engine itself
worked.

The runner now exposes `ensembleCodingValidation` / `ensemble_coding_verified`
as a diagnostic-only signal. It is set only when the current coding run proves
the completed three-model contract, required served donor routes, and current-run
application coverage. The emitted coding-run receipt and report explicitly mark
this as pre-reconciliation and non-reportable. The existing
`multiModelResearchSpineValidation`, `codingValidation`, provider acceptance
gate, and reportability semantics remain unchanged and still require governed
reconciliation, current-run traceability, and Done-task/report gates. Application
and decision evidence availability is required before the diagnostic signal can
pass, so transport failures do not become ensemble evidence.

Verification: focused Research Spine/scoring tests pass `54/54`; the complete
deterministic benchmark suite passes `91/91`; feature-doc generation/check passes
(`224` generated artifacts; `86/86` features); and `git diff --check` passes.
Compass Forge before-gate record `287` and after-gate record `288` were captured for this slice.
Task evidence, commit transport, and Mac Studio parity remain pending.

This closes the diagnostic conflation sub-gap only. F-R9-114 remains open: the
live Docker harness still needs an explicitly governed, opt-in synthetic
reconciliation phase for test-only evidence, plus a separate genuine-human
approval path and deeper Done/report traceability. No provider request, model
load, host installation, Docker image pull, or live benchmark workload was
started.

### L-359 | 2026-08-27T14:36:00Z | S5-ship&learn | gpt-5-codex | ensemble diagnostic transport and Docker parity

The diagnostic split payload is committed as
`1e6722299ceb0cdc9aaac244a38059b1baae9ad7`
(`test: separate ensemble coding evidence from acceptance`) and pushed to
`origin/testing`. This lifecycle receipt is transported in the follow-up
documentation commit; local `testing`, `origin/testing`, and the detached Mac
Studio checkout `~/istara-testing-retake-47bf` are refreshed to that resulting
tip and verified clean. Compass Forge task evidence `317` records the focused/full deterministic tests,
feature-doc check, diff check, and before/after gate receipts (`287`/`288`).

Passive SSH inspection used the explicit existing Docker binary
`/usr/local/bin/docker` because the non-login SSH PATH did not contain `docker`;
no host installation was attempted. Docker Server/Client are `29.7.2`, the only
running container is unrelated healthy `plex`, the Mac Studio model directory
contains zero files, and the retake has no `.env.deploy`. No image pull, model
load, provider request, benchmark workload, or data deletion occurred.

This transport receipt does not claim live ensemble quality or accepted Research
Spine validity. F-R9-114 remains open for the governed synthetic reconciliation
test phase, genuine human approval separation, and exact Done/report traceability.

### L-360 | 2026-08-27T14:53:17Z | S2-execute/S3-review | gpt-5-codex | guarded synthetic reconciliation diagnostic and contract hardening

F-R9-114's next bounded slice is implemented as an explicitly opt-in,
benchmark-only diagnostic path. `POST /api/code-applications/{project_id}/synthetic-reconciliation`
requires the isolated-container setting
`research_validity_synthetic_reconciliation_enabled=true` and the exact
`x-istara-synthetic-reconciliation: benchmark-v1` header. It is separate from
the human `PATCH /api/code-applications/{application_id}/review` route. The
service requires a project-scoped completed coding run, exact coverage of every
application in that run, source/evidence-unit/coder/model/route provenance, and
route evidence whose served model matches the application model and proves a
served outcome (including numeric-string request counters). Unsupported or
incomplete input returns a controlled 4xx response.

Every receipt is stored as `source=benchmark_synthetic`, carries the diagnostic
identifier and coding-run handle, and is explicitly marked
`accepted_reportable=false` and `human_review_required=true`. The code
application rows remain `pending`/`unreconciled`/`blocked`; no human-review,
promotion, Done-task, or report gate is mutated. The benchmark runner only
invokes this path when `ISTARA_BENCHMARK_SYNTHETIC_RECONCILIATION=true`, records
the receipt separately from `ensemble_coding_verified`, and continues to keep
the strict `multiModelResearchSpineValidation` acceptance signal dependent on
governed reconciliation and current-run traceability.

The implementation was extracted to
`backend/app/services/synthetic_reconciliation_service.py` so the existing
research-validity orchestrator does not gain additional complexity debt. The
benchmark-only request types and route literal are named in the canonical
frontend API/type contract for Compass Forge discoverability, while no
user-facing client operation was added. The ensemble feature architecture
document now describes the diagnostic endpoint and its non-reportable boundary.

Verification: `pytest -q tests/test_code_applications.py` passes `12/12`;
`npm --prefix tests/real_user_benchmark test` passes the full deterministic
suite `92/92`; Python compilation and `git diff --check` pass; feature-doc
generation/check passes (`224` generated artifacts; `86/86` features). The
focused cross-suite attempt passed `24` tests before hanging in the existing
teardown/event-loop drain, and the contract-only attempt passed `12` before
the same teardown hang; these are recorded as fixture-lifecycle debt, not a
clean cross-suite claim. Compass Forge before-gate record `289` and after-gate
record `294` were captured; after-gate comparison reports zero new issues (the
repository still has inherited warnings/failures and the lifecycle-file
large-file suppression). No server, provider request, model load, image pull,
or live benchmark workload was started.

This closes the guarded synthetic-diagnostic slice only. Remaining F-R9-114
work includes idempotent/retry-safe receipt semantics, deeper Done/report
traceability assertions, a genuine human reconciliation acceptance exercise,
and the owner-approved Docker-only three-model Mac Studio run with exact
provider-served identities and model inputs.

### L-361 | 2026-08-27T14:54:57Z | S5-ship&learn | gpt-5-codex | guarded diagnostic transport and Mac Studio Docker parity

The guarded synthetic reconciliation implementation and its feature-contract
updates are committed as `8af702d3f9d2a06af22be3c17abe7566e0c3ade0`
(`test: add guarded synthetic reconciliation diagnostic`) and pushed to
`origin/testing`. Local `testing`, `origin/testing`, and the detached Mac
Studio retake `~/istara-testing-retake-47bf` all resolve to that exact SHA and
are clean. Compass Forge task evidence `326` records the API/deterministic/
feature-doc/compile/diff verification; evidence `327` records transport and
parity.

Passive SSH inspection remained Docker-only. The Mac Studio Docker client and
server are both `29.7.2`; only the unrelated healthy `plex` container is
running; `~/Istara-Projects/models` contains zero files; and the retake has no
`.env.deploy`. No host package installation, Docker image pull, provider
request, model load, benchmark workload, or test-data deletion was performed.

The repository gate after this slice is Compass Forge record `296` with zero
new issues relative to the baseline. Existing inherited secret-flow,
complexity, route/type, and large-file conditions remain tracked separately;
the lifecycle document's path-scoped large-file suppression remains active.
The cross-suite Python teardown hang remains an inherited fixture-lifecycle
debt signal rather than a passing acceptance claim. F-R9-114 remains open for
idempotency, genuine human reconciliation/Done/report proof, and the
owner-approved live three-model Docker run.

### L-362 | 2026-08-27T14:55:53Z | S5-ship&learn | gpt-5-codex | final lifecycle-tip parity receipt

The lifecycle receipt from L-361 is itself committed and pushed as
`9209ae2600824b2be3cad948f5d446d0aac14f2f`
(`docs: record synthetic reconciliation parity receipt`). The local `testing`
branch, `origin/testing`, and detached Mac Studio retake
`~/istara-testing-retake-47bf` now all resolve to that exact final tip and are
clean. The implementation commit remains `8af702d3...`; the final branch tip
includes its ledger receipt and is the SHA that must be used for any retake.

The Mac Studio parity check again used only the pre-existing
`/usr/local/bin/docker`: client/server `29.7.2`, unrelated healthy `plex` only,
zero files under `~/Istara-Projects/models`, and no retake `.env.deploy`. No
host install, image pull, provider request, model load, live benchmark, or
testing-data deletion occurred. This closes transport for the current slice;
F-R9-114 remains open for idempotency, human Done/report proof, and the
owner-approved live three-model Docker acceptance run.

### L-363 | 2026-08-27T14:56:40Z | S5-ship&learn | gpt-5-codex | final branch-tip transport receipt

After L-362, the final ledger edit was committed and pushed as
`20a1ae96a8cd6cb32a3a3650fd7a42384a390584`. Local `testing`,
`origin/testing`, and detached Mac Studio retake
`~/istara-testing-retake-47bf` all resolve to this exact clean tip. This is
the authoritative checkout SHA for the next agent; the implementation and
prior receipts are in its ancestry.

The final passive SSH check used only the existing `/usr/local/bin/docker`:
Docker client/server `29.7.2`, unrelated healthy `plex` only, zero model files,
and no retake `.env.deploy`. No host installation, image pull, provider
request, model load, live workload, or test-data deletion occurred. F-R9-114
remains open for idempotent synthetic receipts, human reconciliation and
Done/report traceability proof, and the owner-approved three-model Docker
acceptance run.

### L-364 | 2026-08-27T15:02:45Z | S3-review/S5-ship&learn | gpt-5-codex | idempotent synthetic receipt retry slice

The guarded synthetic reconciliation diagnostic now has deterministic,
retry-safe receipt semantics. Receipt and evidence-edge IDs are derived from
the project, coding run, diagnostic, and code-application identity. A retry
with the same exact decision payload returns the original receipt without
inserting a duplicate; a divergent decision payload or incomplete prior set
is rejected with a controlled validation error. A database-integrity race is
rolled back and reconciled against the existing receipt set. The path remains
benchmark-only and non-reportable: no code-application review, reconciliation,
promotion, Done-task, or report gate is mutated.

Verification passed: `pytest -q tests/test_code_applications.py` `12/12`;
`npm --prefix tests/real_user_benchmark test` `92/92`; feature docs generated
`224` artifacts and checked `86/86`; Python compilation and `git diff --check`
passed. Compass Forge after-gate record `297` reports zero new issues against
the inherited baseline. The implementation and test/docs changes are still
working-tree changes at this checkpoint and must be committed, pushed, and
retaken on Mac Studio before this slice can claim transport parity. No live
provider request, model load, image pull, or host installation was started.
F-R9-114 remains open for deeper Done/report traceability, genuine human
reconciliation acceptance, and the owner-approved Docker-only run with three
distinct served models.

### L-365 | 2026-08-27T15:04:41Z | S5-ship&learn | gpt-5-codex | idempotency transport and Mac Studio parity

The idempotent synthetic-reconciliation implementation, focused test, feature
documentation, generated site artifacts, and prior ledger receipt are committed
as `ddff4050ea3f60195c661d189e6afe7b30b8fa7c` and pushed to `origin/testing`.
Local `testing`, `origin/testing`, and the detached Mac Studio retake
`~/istara-testing-retake-47bf` all resolve to this exact clean tip.

Passive SSH verification remained Docker-only: `/usr/local/bin/docker` reports
client/server `29.7.2`; only the unrelated healthy `plex` container is running;
`~/Istara-Projects/models` contains zero files; and the retake has no
`.env.deploy`. No host installation, image pull, provider request, model load,
live benchmark, or testing-data deletion occurred. Compass Forge task evidence
`331` records the focused tests, docs check, compile/diff checks, gate `297`,
and transport. F-R9-114 remains open for deeper Done/report traceability,
genuine human reconciliation acceptance, and the owner-approved Docker-only
three-model run with distinct served identities.

### L-366 | 2026-08-27T15:12:30Z | S3-review | gpt-5-codex | exact current-run traceability oracle hardening

The benchmark traceability probe no longer treats an oversized application list
and one qualifying edge as sufficient evidence. It now requires the current
coding run to contain exactly the expected number of applications, unique
application identities, and a coded `evidence_unit -> coded_as ->
code_application` edge for every current-run application. Duplicate identities,
extra rows, missing per-application edges, and empty application sets fail
closed. The receipt exposes unique counts, coded-edge counts, and bounded
missing-application IDs so a failure is diagnosable without reconstructing the
graph from prose.

Two deterministic regressions cover the previous false-positive cases: a
duplicate current-run application identity and a current-run application with
no coded evidence edge. The positive three-donor path remains covered, and the
strict accepted Research Spine gate is unchanged: this is an evidence oracle
hardening, not a synthetic promotion or human-review substitute.

Verification passed: `node --check
tests/real_user_benchmark/lib/research-spine-probes.mjs`; the full deterministic
benchmark `npm --prefix tests/real_user_benchmark test` passes `94/94`; feature
docs generate/check passes (`224` generated artifacts; `86/86` features); and
`git diff --check` passes. Compass Forge after-gate record `298` reports zero
new issues against the inherited baseline; task evidence `333` records the
commands and regressions. The traceability implementation/docs are currently
working-tree changes pending commit, push, and Mac Studio retake. No server,
provider request, model load, Docker image pull, host installation, live
benchmark, or data deletion occurred. F-R9-114 remains open for a genuine
human reconciliation/Done/report exercise and the owner-approved Docker-only
three-model run with exact served identities.

### L-367 | 2026-08-27T15:14:20Z | S5-ship&learn | gpt-5-codex | traceability hardening transport and Mac Studio parity

The exact current-run traceability oracle hardening is committed as
`dc9fdb7ddadcd388c17d45a07d606f15cb61eee6`
(`test: harden current-run traceability evidence`) and pushed to
`origin/testing`. Local `testing`, `origin/testing`, and the detached Mac
Studio retake `~/istara-testing-retake-47bf` all resolve to this commit and
are clean. Compass Forge task evidence `334` records the deterministic suite,
feature-doc check, syntax/diff checks, gate `298`, and transport parity.

Passive SSH verification again used only the pre-existing
`/usr/local/bin/docker`: client/server `29.7.2`, unrelated healthy `plex` only,
zero files under `~/Istara-Projects/models`, and no retake `.env.deploy`. No
host installation, image pull, provider request, model load, live benchmark,
or testing-data deletion occurred. F-R9-114 remains open for the genuine
human reconciliation/Done/report exercise and an owner-approved Docker-only
three-model run with exact served identities.

### L-368 | 2026-08-27T15:17:30Z | S4-review/S5-ship&learn | gpt-5-codex | final gate and deterministic authority evidence

Post-transport verification confirms the exact parity tip remains clean at
`af6ff70090c6af9f1ff082dab5c59e923deeafdf`: local `testing`,
`origin/testing`, and the detached Mac Studio retake all resolve to that SHA.
Compass Forge after-gate record `299` reports zero new issues, zero new
missing required paths, and zero new forbidden dependencies relative to the
inherited baseline (the lifecycle document remains the known large-file
warning). Task evidence `336` records this final parity and the explicit
remaining F-R9-114 live gate.

The real dispatcher/Pi Model Management authority tests pass `36/36`, and the
source-to-three-model reliability -> human reconciliation -> Done -> report
causal test passes `1/1`. These use deterministic provider/supervisor seams:
they prove engine selection, distinct route/served identity persistence, and
fail-closed promotion logic, but do not claim live model quality or a real
provider-served Fleiss/Krippendorff result. No server, provider request, model
load, image pull, host installation, live benchmark, or testing-data deletion
occurred. F-R9-114 remains open for a genuine human reconciliation exercise
against live artifacts and the owner-approved Docker-only three-model run.

### L-369 | 2026-08-27T15:20:30Z | S5-ship&learn | gpt-5-codex | final ledger transport parity

The final deterministic authority evidence and this lifecycle receipt are
committed as `28b5c0fa5a45cc79dd8db48d1d8ba627e7f21bff` (`docs: record final
deterministic authority evidence`) and pushed to `origin/testing`. Local
`testing`, `origin/testing`, and the detached Mac Studio retake
`~/istara-testing-retake-47bf` all resolve to that exact clean SHA.

Compass Forge after-gate `299` and task evidence `336` remain the authoritative
post-change records: zero new issues, missing required paths, or forbidden
dependencies relative to the inherited baseline. The deterministic authority
suite (`36/36`), causal Research Spine source-to-report proof (`1/1`), full
benchmark (`94/94`), and feature-doc check (`224` generated / `86/86` checked)
are all green. These are deterministic seams and do not establish live model
quality. Passive SSH inspection used only the existing Docker binary
`/usr/local/bin/docker` (`29.7.2/29.7.2`); only unrelated healthy `plex` is
running, model files are `0`, and `.env.deploy` is absent. No host install,
image pull, provider request, model load, live benchmark, or test-data deletion
occurred. F-R9-114 remains open for live three-model provider-served identity,
human reconciliation, and Done/report acceptance.

### L-370 | 2026-08-27T15:28:23Z | S3-review/S5-ship&learn | gpt-5-codex | synthetic receipt report-gate regression

The synthetic reconciliation API regression now exercises the same
`assess_task_research_validity` service used by report promotion after a
benchmark receipt is created. The fixture is task-bound and models a completed
coding run with an otherwise accepted run-level promotion, then asserts that
the synthetic receipt leaves the code application unresolved and the report
gate denied. This closes the test gap where row state was checked but an
accidental synthetic-to-reportable bypass in the production validity service
would have gone unnoticed.

Verification passed: `pytest -q tests/test_code_applications.py` (`12/12`),
`npm --prefix tests/real_user_benchmark test` (`94/94`), feature-doc
generation/check (`224` generated artifacts; `86/86` features),
`compass-forge gate before` record `300`, `compass-forge gate after` record
`301` (zero new issues), and `git diff --check`. The implementation/test/docs
commit is `c2cd7dff` and is ready for transport. No provider request, model
load, Docker image pull, host installation, live benchmark, or test-data
deletion occurred. F-R9-114 remains open for live provider-served
three-model identity, genuine human reconciliation, and Done/report
acceptance.

### L-371 | 2026-08-27T15:30:06Z | S5-ship&learn | gpt-5-codex | synthetic report-gate regression transport

The report-gate regression and its feature documentation are transported in
`8e346b9cfbdae200996c961b7633a74fb88417dc` (`docs: record synthetic
report-gate regression`) and pushed to `origin/testing`. Local `testing`,
`origin/testing`, and the detached Mac Studio retake
`~/istara-testing-retake-47bf` all resolve to this exact clean SHA.

Compass Forge task evidence `338` records gate-before `300`, gate-after `301`,
the `12/12` API test, `94/94` deterministic benchmark, `224` generated /
`86/86` checked feature docs, and the assertion that
`assess_task_research_validity` remains `report_allowed=false` after synthetic
receipt creation. Passive SSH verification used only the existing
`/usr/local/bin/docker`: client/server `29.7.2/29.7.2`, unrelated healthy
`plex` only, zero model files, and no retake `.env.deploy`. No host install,
image pull, provider request, model load, live benchmark, or testing-data
deletion occurred. F-R9-114 remains open for live three-model provider-served
identity, genuine human reconciliation, and Done/report acceptance.

### L-372 | 2026-08-27T15:32:59Z | S3-review | gpt-5-codex | legacy reportability compatibility debt

Static call-graph and fixture audit confirmed one remaining Research Spine
architecture debt. `assess_task_research_validity` counts accepted/reconciled
row flags and only applies a run-level promotion check when a latest
`CodingRun` exists. A task-bound `CodeApplication` with
`promotion_status=accepted` and `reconciliation_status=accepted` but no
`coding_run_id` can therefore be reportable after human Done approval. Existing
legacy compatibility fixtures intentionally rely on this shape (for example,
`tests/test_findings.py` and `tests/test_research_integrity_reports.py`), so a
global fail-closed change would require a migration/compatibility policy rather
than a blind patch.

The architecture note now classifies this as explicit debt: all new Research
Spine production paths must persist a governed coding run, while tightening
legacy reportability remains an open decision. Compass Forge impact/why queries
identified the service/report-manager call graph and affected fixture suite;
feature-doc generation/check passes (`224` generated artifacts; `86/86`
features) and `git diff --check` passes. Documentation commit `1ae10760` is
ready for transport. No provider request, model load, Docker image pull, host
installation, live benchmark, or testing-data deletion occurred. F-R9-114
remains open for live three-model provider identity, genuine human
reconciliation, and Done/report acceptance.

### L-373 | 2026-08-27T15:36:29Z | S3-review | gpt-5-codex | reportability-debt transport parity

The compatibility-debt finding and preceding lifecycle receipt are committed
at `15b3d390868a4fa713d694cb652c8bcf3eccd66c`; this transport receipt is
committed at `c1cb6eb21a1147dae1e1081065fa4e78b1f5dbff`, pushed to
`origin/testing`, and retaken cleanly on the detached Mac Studio checkout
`~/istara-testing-retake-47bf`. Local `testing`, `origin/testing`, and the Mac
retake match `c1cb6eb21a1147dae1e1081065fa4e78b1f5dbff`. Compass Forge task evidence `341` records the
transport and the unchanged Docker-only boundary: Docker client/server
`29.7.2/29.7.2`, unrelated healthy `plex` only, zero model files, and no
`.env.deploy`. No host package install, image pull, provider request, model
load, live benchmark, or testing-data deletion occurred. Feature-doc checks and
`git diff --check` remain green. F-R9-114 is still open for live provider-served
three-model identity, Fleiss/Krippendorff evidence, genuine human
reconciliation, and Done/report acceptance; legacy no-coding-run reportability
requires a separate migration/compatibility decision.

### L-374 | 2026-08-27T15:40:00Z | S3-review | gpt-5-codex | ledger provenance correction

The `L-373` transport receipt was corrected to distinguish the preceding
documentation checkpoint (`15b3d390868a4fa713d694cb652c8bcf3eccd66c`) from the
transport receipt itself (`c1cb6eb21a1147dae1e1081065fa4e78b1f5dbff`). This
keeps the Build Stream SHA chain truthful: the latter is the exact commit that
local `testing`, `origin/testing`, and the detached Mac Studio retake must
match. No code, runtime, provider, model, or Docker state changed.

### L-375 | 2026-08-27T15:47:00Z | S3-review | gpt-5-codex | Docker runtime provenance hardening

The benchmark's Docker-only guard previously treated the caller-controlled
`ISTARA_BENCHMARK_DOCKER_RUNNER=1` marker as sufficient evidence of container
execution. That left a direct host invocation able to spoof the marker and
enter the Docker-owned three-model path. Commit `ead660b18edfe8af66400e7ba4e70b288f93994c`
now requires both the marker and actual container-runtime evidence
(`/.dockerenv` or a Docker/containerd/kubepods cgroup), records the two signals
separately in metadata/history, and retains the host-managed refusal when the
runtime proof is absent. The topology contract gained a regression asserting
this separation; the ensemble feature documentation and benchmark README were
regenerated/updated accordingly.

Verification: focused topology suite `11/11`; full real-user benchmark contract
suite `95/95`; `python -m pytest -q tests/test_code_applications.py
tests/test_research_spine_end_to_end.py` `13 passed`; feature-doc generation /
check `224` artifacts and `86/86` features; `git diff --check`; Compass Forge
gate-before record `302` and gate-after record `303` report no new issues (the
repository's pre-existing warning/fail inventory remains). No provider request,
model load, image pull, host installation, live benchmark, or testing-data
deletion occurred. The code commit is not yet transported to `origin/testing`
or the Mac Studio retake; transport is the next checkpoint.

### L-376 | 2026-08-27T15:49:00Z | S5-ship&learn | gpt-5-codex | guardrail transport parity

The Docker runtime provenance hardening from `L-375` is now fully transported
in the clean commit `b5ed5bf7e2f2773cecb7db6b4b437a70ccda1d19`. Local `testing`,
`origin/testing`, and the detached Mac Studio retake
`~/istara-testing-retake-47bf` all resolve to this SHA. Compass Forge task
evidence `343` records the focused/full deterministic suites, feature-doc
check, and passive Mac Docker-only state: client/server `29.7.2/29.7.2`,
unrelated healthy `plex` only, zero model files, and no `.env.deploy`. No
provider request, model load, image pull, host installation, live benchmark,
or testing-data deletion occurred. F-R9-114 remains open for the owner-approved
live three-model provider identity, Fleiss/Krippendorff evidence, genuine
human reconciliation, and Done/report acceptance; legacy no-coding-run
reportability still needs a migration/compatibility decision.

### L-377 | 2026-08-27T15:50:00Z | S5-ship&learn | gpt-5-codex | final receipt parity

The transport receipt itself advanced the branch once more: the exact clean
tip is now `bbe8e6b4e16163b38b952487acfda5c8f251612b`, and local `testing`,
`origin/testing`, and the detached Mac Studio retake all match it. Compass
Forge evidence `344` records that parity and the unchanged passive Docker-only
state (client/server `29.7.2/29.7.2`, unrelated healthy `plex` only, zero model
files, no `.env.deploy`). No provider request, model load, image pull, host
installation, live benchmark, or testing-data deletion occurred. F-R9-114
remains open for owner-approved live three-model provider identity,
Fleiss/Krippendorff evidence, genuine human reconciliation, and Done/report
acceptance; legacy no-coding-run reportability still needs a migration/
compatibility decision.

### L-378 | 2026-08-27T15:59:30Z | S4-remediate | gpt-5-codex | restricted Petals scope closure

The Pi Model Management resolver had a project-scope gap: a projected Petals
donor restricted to one or more project ids could still be explicitly resolved
or selected by a projectless call. The resolver now fails closed with
`petals_project_id_required` for restricted donor identities, preserves
`petals_project_not_authorized` for an explicit but disallowed project, and
keeps wildcard donors available to the documented global catalog inventory.
Project-scoped catalogs and ensemble selection continue to filter donors before
consuming a slot; the loopback Petals bridge remains the second admission
check. Added regressions cover restricted explicit resolution, restricted
distinct selection, authorized resolution, and wildcard compatibility.

Implementation commit: `b108b831` (`fix: fail closed restricted petals pi
resolution`). Verification: focused Petals/Research Spine/Pi manager suite
`53 passed`; feature-doc generation/check `224` artifacts and `86/86`
features; `git diff --check`; Compass Forge gate-before record `305` exited
successfully with only the repository's inherited warning/fail inventory.
The commit is ready for transport to `origin/testing` and the detached Mac
Studio Docker checkout; no provider request, model load, image pull, host
installation, or live benchmark was started.

### L-379 | 2026-08-27T16:12:00Z | S5-ship&learn | gpt-5-codex | transport and downstream coverage audit

The restricted Petals resolver hardening from `L-378` is now transported as
clean commit `13aebe544a463b7fcb99997489efc431b2b3ffc4`: local `testing`,
`origin/testing`, and detached Mac Studio checkout `~/istara-testing-retake-47bf`
match. Passive SSH verification reports Docker client/server `29.7.2/29.7.2`,
only unrelated healthy `plex`, zero model files, and no `.env.deploy`; no host
installation, image pull, provider request, model load, live benchmark, or
testing-data deletion occurred. Compass Forge task evidence `346`/`347` records
the focused suite and gate-after result.

The deterministic Research Spine end-to-end test is strong for source/evidence
unit creation, three-coder Fleiss/ Krippendorff reliability, reconciliation,
Done approval, and report traceability, but it manually inserts downstream
Nugget/Fact/Insight/Recommendation artifacts and only one grounding edge. It
therefore does not prove that the production transformation services derive
every downstream artifact from accepted atoms with complete source-span
grounding. This is a coverage limitation requiring a real-service fixture (or a
governed exception with explicit tests), not a confirmed runtime defect. The
live gate F-R9-114 remains open for provider-served identities, genuine human
reconciliation, and Done/report acceptance; legacy no-coding-run reportability
still needs an explicit migration/compatibility decision.

### L-380 | 2026-08-27T16:20:00Z | S5-ship&learn | gpt-5-codex | deterministic regression closure

The complete real-user benchmark contract passes `95/95`, and the selected
ensemble/Research Spine Python regression set passes `17/17` after the Petals
scope hardening and coverage audit. These suites validate routing authority,
served-identity/provenance requirements, three-coder Fleiss/Krippendorff gate
contracts, reconciliation/reportability blockers, Docker-only refusal and
receipt semantics, and long-horizon acceptance rules using deterministic seams.
They do not establish live model quality, live provider-served identities, or
human reconciliation. Compass Forge evidence `349` records the results.

The last transported code/docs checkpoint remains
`07c463edf9c2fd371e7121abb09871912b3232e0`; this is a documentation-only
ledger update. No provider request, model load, image pull, host installation,
live benchmark, or testing-data deletion occurred. F-R9-114 remains open for
owner-approved Docker-only three-model provider execution, genuine human
reconciliation, Done/report acceptance, and the two-call/long-horizon live
receipt; the legacy no-coding-run reportability migration decision and the real
downstream artifact generation fixture remain separate follow-ups.

### L-381 | 2026-08-27T16:36:00Z | S4-remediate/S5-ship&learn | gpt-5-codex | production-path spine coverage and SQLite telemetry safety

The deterministic Research Spine proof no longer inserts downstream artifacts
or a hand-written evidence edge. Commit `92a6b1939fe5939d4fd6cff43f355a73044cb196`
drives a `SkillOutput` through `AgentOrchestrator._store_findings`, creates
three source-span EvidenceUnits from exact document text, invokes the real
three-coder coding-run path, persists nine CodeApplications and three Coders,
and verifies generated Nuggets, Fact, Insight, Recommendation, and all three
nugget-to-evidence-unit grounding edges before human reconciliation, Done
approval, and six-finding report routing. The deterministic dispatcher parses
the protected `<evidence_units>` prompt, returns provider-served identities,
and assigns two nominal categories so Fleiss' kappa is defined; the test asserts
both Fleiss' kappa and the Krippendorff-alpha companion at 1.0. Report finding
membership is compared as a set because SQL row order is not a contract.

The same commit fixes a real SQLite test/production transaction hazard. Source
evidence persistence previously opened a second telemetry writer after a caller
had flushed an uncommitted SQLite transaction, causing a writer-lock deadlock
and making the contract suite hang before reporting a result. Telemetry now
accepts the caller's `AsyncSession`, adds the content-free span to that same
transaction, and remains atomic with the evidence graph; standalone telemetry
callers retain the existing independent-session path. Explicit
`ResolvedPiEndpoint(kind="petals")` fixture catalogs are documented and treated
as already-admitted wildcard seams, while dynamic Petals bridge projections keep
their concrete project allowlists and double admission checks.

Verification on the local testing checkout: `711 passed, 5 skipped` for
`tests/pi_production tests/pi_benchmark tests/test_research_validity_contract.py
tests/test_research_spine_end_to_end.py tests/test_validation_project_scope.py`
with `-W error::RuntimeWarning`; the focused PI/ensemble/Research Spine matrix
is `185 passed`; the previously hanging Research Spine contract file is
`32 passed`; Ruff reports `All checks passed`; and feature-doc generation/check
reports `224` generated artifacts and `86/86` features. Compass Forge
`gate before` record `307` completed with the repository's inherited warning /
secret-flow / route-drift inventory and no new architecture, dependency, or
security finding attributable to this change. Commit `92a6b193` is not yet
transported; the next action is gate-after plus clean push/parity verification.
No provider request, model load, Docker image pull, host installation, live
benchmark, or testing-data deletion occurred. F-R9-114 remains open for
owner-approved Docker-only three-model provider execution, provider-served
identity receipts, genuine human reconciliation, Done/report acceptance, and
the two-call/long-horizon live receipt; legacy no-coding-run reportability and
the live downstream transformation chain remain separate follow-ups.

### L-382 | 2026-08-27T16:38:00Z | S5-ship&learn | gpt-5-codex | transport parity and handoff receipt

The production-path spine coverage, explicit Petals fixture semantics, and
SQLite transaction-safe telemetry fix from `92a6b1939fe5939d4fd6cff43f355a73044cb196`
were recorded in the durable ledger and transported in clean commit
`b800581867f3cbe0d4eef9b65334192cbe1cde24`. Local branch `testing`,
`origin/testing`, and detached Mac Studio checkout
`~/istara-testing-retake-47bf` all resolve to this exact SHA. Compass Forge
task evidence `351` records the `711 passed, 5 skipped` broad deterministic
matrix and `185 passed` focused matrix; evidence `352` records feature-doc
generation (`224` artifacts, `86/86` features), Ruff, push, and passive Mac
verification; evidence `353` records gate-before `307` and gate-after `308`,
with no new architecture, dependency, or security issues attributable to this
change. The gate's current repository status remains fail because of inherited
complexity, secret-flow, route-drift, type-drift, and scoped large-ledger
inventory; those are not silently reclassified as fixed.

The Mac Studio boundary remains honored: Docker client/server `29.7.2/29.7.2`,
only unrelated healthy `plex`, zero files under `~/Istara-Projects/models`, and
no `.env.deploy`. No container was started, no image was pulled, no provider
request or model load was made, no host package was installed, and no testing
data was deleted. The live Research Spine gate F-R9-114 is therefore still
open: deterministic seams prove routing, three-coder Fleiss/Krippendorff
contracts, reconciliation blockers, provenance, Docker refusal, and long-
horizon rules, but they do not prove live model quality, provider-served
identities, two concurrent calls, genuine human reconciliation, Done/report
acceptance, or the real downstream transformation chain. The next agent must
obtain the owner's provider/model inputs before any bounded Docker-only live
run and must preserve the exact route/model/usage receipts.

### L-383 | 2026-08-27T16:49:00Z | S2-execute/S3-review | gpt-5-codex | CF-SPEC-3 scorecard evidence refresh

Re-ran the scorecard contract and deterministic acceptance matrix while mapping the
newly clarified `CF-SPEC-3` tasks (`CF-38` through `CF-46`) to existing shipped
behavior. `npm --prefix tests/real_user_benchmark run check` passed all `95/95`
Node contract tests, including fail-closed separation of structural traceability,
weak donor topology, served model identities, reliability/reconciliation, and
long-horizon acceptance. The Python matrix passed `711 passed, 5 skipped` with
`-W error::RuntimeWarning`, covering Pi production/benchmark paths, the Research
Spine contract, production-path end-to-end persistence, and project-scope validation.
No source, provider, model, container, or host state was changed by this receipt.

Compass Forge remains native Rust (`python_fallback=false`). Its new `CF-SPEC-3`
records live in the ignored local state database and do not alter Git branches;
the repository checkout remains `/Users/user/Documents/Istara-main` on clean
`testing`, exactly equal to `origin/testing` at `13d0f124`. The only other
registered checkout is the preserved recovery worktree under
`/Users/user/Documents/Codex/2026-08-10/list/work/istara-pi-linearized-2026-08-10`.
Passive SSH verification still shows Docker client/server `29.7.2/29.7.2`, only
unrelated healthy `plex`, zero model files, and no Istara stack; no host install,
image pull, provider request, model load, or testing-data deletion occurred.

Result: deterministic scorecard criteria are ready for task evidence/closure, but
this is not live Research Spine acceptance. F-R9-114 remains open for owner-approved
Docker-only provider/model identities, three served donor routes, Fleiss/Krippendorff
receipts from real calls, genuine reconciliation, Done/report acceptance, two-call /
long-horizon live receipts, and the real downstream transformation receipt. Legacy
no-`coding_run_id` reportability still requires an explicit migration decision.
Next: attach these exact commands as CF-SPEC-3 evidence and leave external gates open.

### L-384 | 2026-08-27T17:04:00Z | S3-review | gpt-5-codex | Corrected Compass Forge history/count claim

Corrected the earlier claim that Istara had only five Compass Forge specs beginning on
2026-08-23. That number is limited to the active repo-local database at
`/Users/user/Documents/Istara-main/.compass-forge/state.sqlite3`, which currently
contains five rows (`CF-SPEC-1` through `CF-SPEC-5`) and has oldest `created_at`
`2026-08-23T15:04:20.958685Z`. It is not a complete historical count.

Read-only inventory of the retained shared workspace database at
`/Users/user/Documents/compass-forge/.compass-forge/state.sqlite3` found 60 specs
across projects. Its Istara-main project scope contains ten rows, oldest
`CF-SPEC-41` at `2026-08-01T19:46:34+00:00`, followed by `CF-SPEC-47` and
`CF-SPEC-51` through `CF-SPEC-59`; the database's oldest row overall is a
Compass-Forge project spec from `2026-07-03`, not an Istara row. A retained pre-native
backup has 50 rows but only through `2026-08-13`, confirming that these are snapshots
of separate CF state stores, not one automatically merged history.

Git supplies the earlier Istara process history: commit `741f3420` on
`2026-04-03T15:39:09-03:00` records Compass documentation and release/onboarding
integration; `1994ba33` on April 10 embeds the three-layer testing architecture into
Compass; and `21ef99b1` the same day adds TESTING.md, a PR-required workflow, and
Compass integration. This proves Compass/Build Stream was present in Istara in April,
while the first durable Pi-specific specs (`CF-SPEC-1`, `CF-SPEC-2`, and the
`CF-SPEC-7`/`CF-SPEC-8` replacement lineage) are documented in the July 19–20
Build Stream history; later `CF-SPEC-10`/`11`/`12` acceptance is recorded around
July 31–August 1. No April CF-SPEC database rows were found in the retained state
stores, so an April process-origin claim must not be converted into a fabricated
April spec-row count.

Result: the historical answer is intentionally split by authority—April 3 is the
verified Istara Compass origin; ten is the retained shared-DB Istara row count;
five is the active repo-local row count. The current checkout remains clean on
`testing` and equal to `origin/testing`; this audit changed only this append-only
ledger and did not alter code, Docker, providers, models, or host state.

Next: keep CF state provenance explicit in all reports and decide, under owner approval,
whether a formal historical import/reconciliation is wanted. Do not merge or rewrite
CF databases implicitly, and do not close live Research Spine gates from deterministic
or historical bookkeeping evidence.

### L-385 | 2026-08-27T17:18:00Z | S3-acceptance | gpt-5-codex | Closed deterministic CF-SPEC-3 scope only

Compass Forge task evidence `355` through `363` was reviewed against the nine linked
`CF-SPEC-3` requirements. Each task (`CF-38` through `CF-46`) had command evidence,
and the receipts explicitly limit the claim to deterministic scorecard semantics:
structural Research Spine traceability and weak donor topology cannot satisfy
accepted three-model validation. All nine tasks were marked `done`, and native Rust
`compass-forge spec accept CF-SPEC-3` completed with status `accepted`.

This acceptance does not claim live provider/model execution, independent served
identities, real Fleiss/Krippendorff values from three providers, human reconciliation,
Done/report promotion, two concurrent calls, long-horizon behavior, or downstream
artifact generation against live model output. Those remain under the open
`CF-SPEC-2` implementation/test tasks (`CF-13`, `CF-15`, `CF-20`, `CF-21`) and the
external F-R9-114 gate. The current repository remains clean on `testing` at
`ba83a6df`; CF state mutations are local ignored state and do not change Git.

Next: inspect the CF-SPEC-2 evidence/task graph and production/test seams to identify
the next bounded remediation that can be implemented and verified without inventing
live provider evidence.

### L-386 | 2026-08-27T17:42:00Z | S2-execute | gpt-5-codex | Deepened Compass Forge historical provenance

The earlier history note was too narrow. A full `git log --all` and tag-level inspection
shows that Istara's Compass governance system was already present on April 3, not merely
in August. Commit `741f3420` (`2026-04-03T15:39:09-03:00`) added the Compass entrypoint,
change checklist, system-change matrix, system prompt, technical narrative, and persona
updates. `AGENT_ENTRYPOINT.md` at that tag explicitly names Compass as Istara's
comprehensive agentic development system and requires future agents to maintain its
architecture, tests, documentation, and release doctrine. `e1f69570` the same day
hardened the Compass doctrine; April 5 commits automated Compass-doc regeneration; and
`1994ba33` (`2026-04-10T00:15:02-03:00`) embedded the three-layer testing architecture
into Compass. `21ef99b1` (`2026-04-10T19:18:51-03:00`) then added the PR-required
workflow, `TESTING.md`, and explicit Compass integration. The April history continues
through security, testing, observability, and audit changes, so April is the verified
origin of the continuously evolved Compass process in Istara.

The naming distinction is also now explicit. The first literal `compass-forge` references
in Istara's Git history appear on May 2–4; commit `7dca7368` (`2026-05-04`) introduced
`CF-SPEC-6`/`CF-68` for a launch-hardening execution and `CF-SPEC-5` for the production
readiness audit. The standalone Compass Forge repository's first retained snapshot is
`6e7ed53` (`2026-05-26`), while its current shared state database begins on July 3.
Therefore the durable answer is: Compass/CF governance has been in Istara since April;
the named `compass-forge` spec command and retained spec databases are later persistence
representations of that process. No April CF-SPEC database rows survive in the inspected
state stores, so their absence cannot be used to claim CF was absent in April, nor can
an April spec-row count be fabricated.

Evidence consulted: `git log --all --reverse` for Compass, `git log -S'compass-forge'`,
April tags `v2026.04.03.3`, `v2026.04.10.13`, and `v2026.04.20.4`, exact historical
files `AGENT_ENTRYPOINT.md`, `CHANGE_CHECKLIST.md`, `SYSTEM_CHANGE_MATRIX.md`,
`SYSTEM_PROMPT.md`, `TESTING.md`, and the retained CF databases under
`/Users/user/Documents/compass-forge/.compass-forge/` and
`/Users/user/Documents/Istara-main/.compass-forge/`. This was read-only provenance
work; no code, provider, model, Docker, host, or testing data changed.

Next: retain this two-layer history in all reports, then continue the open CF-SPEC-2
implementation/test audit. Do not close live Research Spine gates from historical or
deterministic bookkeeping evidence.

### L-387 | 2026-08-27T18:02:00Z | S2-execute | gpt-5-codex | Confirmed April Compass lineage on current testing ancestry

The deeper ancestry check resolves an important nuance that a date-only search can hide.
Istara's April Compass commits exist in two equivalent histories because the repository
contains duplicated/rebased commit pairs. The original April 3 commit `741f3420` is
not the literal ancestor hash of the current `testing` ref, but its same-time equivalent
`42e454b0` is an ancestor of `testing`; the two patches have the same stable patch ID.
The same applies to the April 3 doctrine hardening (`e1f69570` / `ce19476e`), the April
10 three-layer testing update (`1994ba33` / `16d18228`), and the April 10 testing/PR
workflow (`21ef99b1`, directly present on `testing`). Therefore the current testing
branch does contain the April Compass process, not merely an unrelated later copy.

Current-testing ancestry evidence: `42e454b0`, `ce19476e`, `16d18228`, `21ef99b1`,
and `c0ddf50c` all resolve as ancestors of `testing`; `741f3420`, `e1f69570`, and
`1994ba33` are equivalent duplicate hashes on other refs. The April lineage continues
through testing, security, observability, audit, and branch-governance commits throughout
April. The named `compass-forge` string and explicit `CF-SPEC-*` references still first
appear in Istara history on May 2–4, but that is a naming/persistence milestone, not the
start of Compass governance.

Result: report `April 3, 2026` as the verified Compass origin in Istara; report May 4
as the first verified named `compass-forge`/`CF-SPEC` references; and report July 3 as
the start of the retained shared Compass Forge database snapshot. Never use the July
database's row count as the age of the process, and never claim April CF-SPEC rows that
are not present in a surviving state store.

### L-388 | 2026-08-27T17:20:19Z | S2-execute | gpt-5-codex | Full marker and state-store scan corrected the April boundary

The deeper scan distinguishes the pre-Compass governance/test foundation from the
named Compass system. Istara already had the System Integrity Guide and mandatory
change checklist on 2026-03-28 (`67302d56`), and the April 1–2 history already contains
the agent-architecture, report-pipeline, Plan-and-Execute, A2A, circuit-breaker, and
testing-infrastructure work. The first literal `Compass` marker in all Istara Git
history is the April 3, 2026 `15:39:09 -03:00` commit `741f3420` (with equivalent
rebased hash `42e454b0` on current `testing`), which added the Compass entrypoint and
governance doctrine. This makes April the verified Compass origin while acknowledging
that its operational precursors began in late March.

The later milestones remain separate: the first literal `Compass Forge` marker is
May 2 (`0d0d9a24`), the first literal `CF-SPEC-` marker is May 4 (`7dca7368`, which is
also an ancestor of current `testing`), the first retained standalone Compass Forge
repository snapshot is May 26 (`6e7ed53`), and the current shared state database begins
July 3. A complete scan of retained `state.sqlite3` files found no April CF-SPEC rows:
the shared Compass Forge database has 60 rows (10 for `Istara-main` plus 1 for the
August Pi migration worktree), the repo-local native Istara database has 5 rows dated
August 23–26, and other databases belong to Compass Forge, Skills, or Kairos projects.
These are persistence scopes, not the age of the Istara Compass process.

Verification was read-only: all-ref Git history, marker searches, tag/file inspection,
current-testing ancestry checks, and every retained Documents state database. No code,
provider, model, Docker, host, or testing-data state changed. Keep the April Compass
lineage in future reports; do not backdate CF-SPEC rows or use the July database count
as a proxy for process age.

Next: retain this corrected provenance and continue the open CF-SPEC-2 implementation/
test audit. Live three-model/provider identity, served-model Fleiss/Krippendorff
reliability, genuine human reconciliation and Done/report promotion, two-call and
long-horizon live receipts, no-coding-run migration, and live downstream transformations
remain unproven and must not be closed by this history work.

### L-389 | 2026-08-27T17:33:20Z | S2-execute/S3-review | gpt-5-codex | Unified resolver stub-plane hardening

The authority audit found a concrete contract gap after routing local selections through
`PiModelManager`: the resolver documentation and existing QA tests define
`LLM_PROVIDER_CONTRACT_STUB=true` as making the local Ollama/LM Studio plane invisible,
but a real Pi catalog still carries those entries as `kind=local`. Without an explicit
filter, a deterministic QA stack could resolve and execute its local fixture instead of
using the admitted remote Pi fallback. This would make a green deterministic run look
like provider execution and would violate the fail-closed stub contract.

TDD evidence: the new regression was first run red (the default resolver returned
`pi-local-ollama` instead of the expected `pi-remote`), then the smallest fix restored
`settings` access and excluded `kind=local` catalog entries only when the stub marker is
set. Explicit and default local selections still resolve through the Pi catalog on normal
deployments, and remote Pi entries remain eligible on stub-marked stacks. The updated
`tests/test_model_source.py` now has 13 passing tests; the focused authority/migration
suite (`tests/test_model_source.py`, `test_ensemble_identity_parity.py`,
`test_runtime_hardening.py`, `test_model_management_migration.py`, and
`test_w6_engine_selection.py`) has 75 passing tests. `git diff --check` and the required
feature-doc generator/check both pass (`224` generated artifacts, `86/86` features).

The living chat model-controls architecture now records this stub/local admission rule
and links the resolver regression. This change is still deterministic contract coverage:
it does not prove a live provider request, three independent served model identities,
Fleiss/Krippendorff values, Petals donation, human reconciliation, Done/report promotion,
or live two-call/long-horizon behavior. Those F-R9-114 / CF-SPEC-2 gates remain open.

No model was loaded, no provider was contacted, no Docker workload was started, and no
Mac Studio host state or testing data changed. Next: attach this evidence to the open
CF-SPEC-2 tasks, run the post-change Compass gate, and continue the live-proof and
legacy no-coding-run/downstream-transformation audit without conflating deterministic
Pi-authority evidence with Research Spine acceptance.

### L-390 | 2026-08-27T17:42:33Z | S2-execute/S3-review | gpt-5-codex | April Compass provenance and current evidence reconciled

The requested deeper history audit is complete and is now carried forward as the
authoritative chronology for this delivery. Istara's Compass governance is verified in
the April 3, 2026 lineage (`42e454b0` on current `testing`, patch-equivalent to
`741f3420`), with the April 3 doctrine, April 10 three-layer testing, and April 10
testing/PR workflow also confirmed as ancestors of `testing`. The explicit names
`Compass Forge` and `CF-SPEC-*` appear later (May 2–4), while the retained shared
Compass Forge state snapshot begins July 3. These are distinct milestones: the July
database age must not be reported as the age of Compass in Istara, and no surviving
state store justifies inventing April CF-SPEC rows.

The evidence previously promised by L-389 is attached: CF task evidence rows 364
(`CF-15`), 365 (`CF-20`), and 366 (`CF-13`), plus post-change gate record 313. The
model-source regression suite is 13 passed; the focused authority/migration suite is
75 passed; feature documentation generation/check is 224 artifacts with 86/86 checks;
and `git diff --check` passes. Gate 313 reports no new issues, missing required paths,
or import cycles attributable to this change; the inherited repository inventory gate
remains unresolved.

The remaining acceptance boundary is unchanged and deliberately open: deterministic
tests do not prove live provider requests, three independent served model identities,
real Fleiss/Krippendorff reliability, Petals donation, genuine human reconciliation,
Done/report promotion, two concurrent calls, long-horizon receipts, no-coding-run
migration, or live downstream transformations. Continue auditing those paths and the
open CF-SPEC-2 tasks before any spec acceptance or release claim. No model/provider
request, Docker workload, Mac Studio host mutation, or test-data deletion occurred in
this checkpoint.

### L-391 | 2026-08-27T18:06:00Z | S2-execute/S3-review | gpt-5-codex | Canonical dispatcher authority

The authority audit found two module-level `AgenticDispatcher` instances: the
package entry point (`backend/app/core/agentic/__init__.py`) constructed one and
the implementation module (`backend/app/core/agentic/dispatcher.py`) constructed
another. Current production imports use the package object, so no split behavior
was observed in the existing call graph, but the duplicate was an unsafe
maintenance seam: a future module import, monkeypatch, or instrumentation change
could configure a different Pi service or usage ledger than the product path.

TDD evidence was deliberately red first: the new singleton-identity regression
failed with two different object identities. The minimal fix makes the package
re-export the dispatcher's canonical module singleton. The regression is now green,
and the focused authority/ensemble/manager slice passes 50 tests. Architecture and
living chat-controls documentation now state the one-authority rule; feature site
generation/check passes (224 artifacts, 86/86 features), and `git diff --check`
passes.

This closes an authority-drift defect, not the live scientific gate. No provider or
model request was sent. Three independent served identities, real Fleiss/
Krippendorff values, Petals donation, human reconciliation, Done/report promotion,
two-call and long-horizon receipts, live downstream transformations, and Docker-only
Mac Studio acceptance remain unproven. The post-change gate still reports inherited
repository inventory/complexity/secret-flow warnings and the intentionally retained
large ledger; no new issue attributable to this fix was identified.

### L-392 | 2026-08-27T17:51:30Z | S3-review | gpt-5-codex | Evidence attached for canonical authority fix

Compass Forge evidence rows 367 (CF-15), 368 (CF-20), and 369 (CF-13) record the
50-test focused authority/ensemble/manager run. Row 370 records feature-doc
regeneration (224 artifacts; 86/86 checks) and a clean diff check. Gate record 316,
attached as row 371 to CF-15, reports no new issues, missing required paths, import
cycles, or forbidden dependencies; the retained large ledger and inherited repository
gate debt remain explicit. The fix is therefore reviewable and reproducible, but no
CF-SPEC-2 task is closed by this evidence alone.

### L-393 | 2026-08-27T18:14:00Z | S2-execute/S3-review | gpt-5-codex | Red test for downstream derivation traceability

The production-path Research Spine proof now contains a deliberately red contract for
the missing downstream graph edges: every Fact must be linked to its source Nuggets,
every Insight to its Facts, and every Recommendation to its Insights by explicit
`derived_from` edges. The test also requires candidate-only metadata, pending review,
uncoded reliability, and the promotion rule that graph links cannot bypass accepted
evidence and human review. The red run is reproducible (`tests/test_research_spine_end_to_end.py`:
0 derived edges, expected 5), confirming that JSON ID links alone do not provide the
complete graph traceability required by the Research Spine. No provider request,
model load, Docker workload, or Mac Studio host mutation occurred in this checkpoint.

### L-394 | 2026-08-27T18:32:00Z | S2-execute/S3-review | gpt-5-codex | Downstream graph provenance and project scoping fixed

The production `_store_findings` path now emits five candidate-only `derived_from`
edges for Fact → Nugget, Insight → Fact, and Recommendation → Insight. Each edge
records pending review, uncoded reliability, and the explicit promotion rule requiring
accepted evidence plus human review, so GraphRAG traversal cannot become an implicit
reportability shortcut. Model-supplied upstream ids are normalized and project-scoped
before persistence; stale or foreign ids are discarded, the task receives a human-review
warning, and no cross-project edge is written.

TDD evidence is red then green: the new edge contract first observed 0/5 edges, and
the cross-project regression first observed a leaked foreign id; after the fix the
two proof cases pass. The broader deterministic authority/reliability/findings slice
passes 146 tests, and feature documentation regeneration/check passes (224 artifacts,
86/86 features). This remains deterministic contract evidence: live served-model
identity, real provider reliability receipts, Petals donation/cooperation, genuine
human review, Done/report promotion, two-call and long-horizon receipts, legacy
no-coding-run migration, and Docker-only Mac Studio execution remain open.

### L-395 | 2026-08-27T18:38:00Z | S3-review | gpt-5-codex | Refactor and Compass Forge evidence recorded

The new link/scoping helper was moved to
`backend/app/services/research_finding_links.py` so the already-complex agent
orchestration module did not absorb the full implementation. The focused proof remains
green after the refactor. Compass Forge evidence 372 records the 146 deterministic
tests, 373 records the 224 generated / 86-of-86 checked feature-doc artifacts, and
374 records post-change gate 319. Gate 319 is fail because the touched
`agent_research.py` complexity evidence changed and the durable ledger remains an
explicit suppressed large-file path; no import cycle or architecture-rule regression
was reported. These gate warnings are not relabeled as live failures, but they remain
open remediation debt for the completion plan. No model/provider request or Docker
workload was started in this checkpoint.

### L-396 | 2026-08-27T18:42:00Z | S3-review | gpt-5-codex | Real-user benchmark contract evidence

The deterministic real-user benchmark suite passes all 95 Node tests via
`rtk npm test --prefix tests/real_user_benchmark`; Compass Forge evidence row 375
is attached to CF-15. The suite verifies contract-level coding/source-span/model
identity gates, Fleiss/Krippendorff bounds, reconciliation/reportability blockers,
dual/three-donor acceptance rules, long-horizon receipt requirements, and
Docker-only topology/provenance checks. It does not contact a provider, load a
model, run Docker on the Mac Studio, or prove genuine three-model scientific
agreement. Live provider identity, Petals cooperation, two-call concurrency,
long-horizon execution, human reconciliation/Done/report promotion, and legacy
no-coding-run migration therefore remain open gates. No host installation or
remote workload mutation occurred in this checkpoint.

### L-397 | 2026-08-27T18:46:00Z | S3-review | gpt-5-codex | Final post-gate checkpoint for current slice

Compass Forge post-change gate record 320 is attached as evidence row 376. It
continues to report two touched-file complexity warnings (`agent_research.py` at
1,234 lines and `_store_findings` complexity 61) plus the intentionally retained
large Build Stream ledger path. No new import cycle, architecture-rule issue, or
missing required path was found. These are explicit remediation debt, not silently
waived failures. The current code/tests/docs slice is ready for a clean testing
branch commit, but the live three-model/provider, Petals, concurrency,
long-horizon, human-review/report, migration, and Docker-only Mac Studio gates are
still not proven.

### L-398 | 2026-08-27T18:36:56Z | S2-execute/S3-review | gpt-5-codex | Node 20 Docker portability and CF provenance correction

The deterministic benchmark npm contract had a Node-version portability defect. Its
quoted recursive `node --test "lib/**/*.test.mjs"` pattern fails in the Node 20 Docker
runner before any test executes (`Could not find '/work/tests/real_user_benchmark/lib/**/*.test.mjs'`).
The package script now uses the shell-expanded `lib/*.test.mjs` pattern and the topology
contract test pins that requirement. Local Node 22 verification remains green at 95
tests; the clean Mac Studio retake must be updated to this commit and rerun under the
disposable Node 20 container before this gate is closed. No host package was installed.

The living Ensemble Health architecture page now records this runner requirement and
was regenerated successfully (224 artifacts; 86/86 feature checks). The historical
Compass correction is also evidence-backed: current `testing` ancestry contains the
April 3 Compass entrypoint lineage and April 10 testing workflow; literal
`Compass Forge`/`CF-SPEC-*` markers begin in May, while the retained shared CF DB begins
in July. The database timestamp is therefore persistence scope, not process origin.

The old Mac Studio saved run still proves only that three served identities were
recorded (`pi-codex-luna`, `pi-codex-terra`, `pi-deepseek-default`); it reported Fleiss
κ=-0.125 and Krippendorff α=0.491 against a 0.6 threshold, with 0 accepted
applications and 0 reconciliation decisions. Its historical scorecard nevertheless
said `blocker_count=0`, so it cannot be accepted as current Research Spine proof and
exposes an oracle/report-version mismatch. A separate temporary host-side marathon
wrapper failed with `node: command not found`; it did not install Node, but this remains
a process violation to remove from future runbooks. The dirty remote checkout remains
untouched; only the clean detached retake may be used for Docker acceptance.

Next: commit and push this test/doc checkpoint to `origin/testing`, update the clean
retake, rerun the Node 20 Docker suite, then audit and repair the reportability oracle
and provision an owner-approved three-identity provider/Petals environment. Keep
deterministic, historical, and live scientific evidence separate; do not close
CF-SPEC-2 while reliability, reconciliation, Done/report promotion, two-call,
long-horizon, Petals, and current Docker-only acceptance remain open.

### L-399 | 2026-08-27T18:54:00Z | S2-execute/S3-review | gpt-5-codex | Governed task-report oracle corrected

The benchmark reportability audit is now implemented. The former task-backed path
created taskless candidate findings and counted an interface handoff brief as a
report. It now calls only `POST /api/tasks/{task_id}/reports` for human-approved Done
tasks, requires a returned report id, and sets `approvedTaskFindings`,
`reportGenerated`, and `reportabilityVerified` only on that governed response. The
ordinary Findings exercise records the handoff brief as provisional and never marks
it as report evidence. A new topology contract test protects both boundaries, and
the scorecard has a fail-closed reportability-receipt blocker.

Red/green evidence: the scorecard regression failed before the receipt gate (`1.00`
report ratio despite `reportabilityVerified=false`) and passed after the fix; the
full deterministic real-user suite is now `97 passed, 0 failed`; Node syntax,
feature-doc generation/check (`224` artifacts, `86/86` features), and `git diff
--check` pass. This is still deterministic contract evidence. The clean Mac Studio
Node 20 retake and a live backend run are required to prove the actual task report
endpoint, model routing, Fleiss/Krippendorff reliability, reconciliation, and
promotion behavior.

The historical correction is retained as an explicit provenance boundary: Compass
governance is present in Istara from April 3 (with a late-March precursor), April 10
contains the three-layer testing workflow, literal `Compass Forge`/`CF-SPEC-*`
markers arrive in May, and the shared database's July start is only persistence
scope. No surviving April database row is being invented or used to date the
process. No provider request, model load, Docker workload, Mac host installation,
or deletion of testing data occurred in this checkpoint.

### L-400 | 2026-08-27T18:58:00Z | S2-execute/S3-review | gpt-5-codex | Clean Mac Studio Node 20 Docker retake green

Commit `4c2a20c` is pushed to `origin/testing` and the clean detached retake at
`$HOME/istara-testing-retake-47bf` is exactly that SHA with no working-tree changes.
The deterministic real-user benchmark ran in a disposable `node:20-bookworm`
container with the checkout mounted read-only and a temporary work volume. The
shell-expanded test pattern now executes correctly under Node 20: `97` tests passed,
`0` failed, exit `0`; the cleanup trap removed the temporary volume. Compass Forge
command evidence row `380` records this result.

The first retake attempt exposed only SSH PATH drift (`docker` was not in the
non-interactive PATH), not a missing Docker installation. `/usr/local/bin/docker`
resolved to the existing Docker Desktop binary and reported server `29.7.2`; no
host package, Node runtime, or model artifact was installed. The dirty remote
checkout remains untouched.

This closes deterministic Node portability and reportability-oracle verification,
but not live product acceptance. The task-backed report endpoint still needs a
backend run with approved tasks and valid Research Spine evidence; three independent
provider-served identities, Fleiss/Krippendorff acceptance, human reconciliation,
Done/report promotion, Petals cooperation, two-call/long-horizon parity, legacy
no-coding-run migration, and current Docker-only provider configuration remain open.

### L-401 | 2026-08-27T19:04:26Z | S2-execute/S3-review | gpt-5-codex | Strict provider receipt and project binding for ensemble validation

The Research Spine oracle had three remaining deterministic blind spots. A served route
with only a positive `served_request_count` was rejected even though the adapter had a
valid receipt; a configured route alias could be mistaken for the provider-served model;
and a completed coding run for another project could be accepted because its project
identity was ignored. The benchmark now accepts count-only served receipts, requires a
non-empty matching `route_evidence.model`/`served_model` pair for every served route,
derives model diversity from the provider receipt, and rejects a mismatched optional
`coding_run.project_id`. The Pi coder runner rejects contradictory route/provider
identities before persistence and explicitly preserves `served_model` as the provider
receipt while normalizing the compatibility `model` field.

Red/green evidence: the three new JavaScript regressions failed before the oracle change
and pass afterward; the full deterministic benchmark is `100` Node tests passed, the
Pi validation file is `33` passed, the focused Pi manager/identity slice is `37` passed,
the Research Spine contract/end-to-end slice is `34` passed, feature-doc generation and
checks report `224` artifacts and `86/86` checks, and `git diff --check` passes. These
are deterministic contract results only. The historical Mac run remains scientifically
blocked (`kappa=-0.125`, `alpha=0.491`, zero accepted/reconciled applications), and
live provider identities, Petals, human reconciliation, Done/report promotion,
two-call/long-horizon receipts, and Docker-only current-provider acceptance remain open.

Next: record the gate/evidence rows, commit and push this slice to `origin/testing`,
then rerun the exact pushed SHA in the clean Mac Studio Node 20 Docker retake without
touching the dirty checkout or installing anything on the host.

### L-402 | 2026-08-27T19:06:50Z | S2-execute/S3-review | gpt-5-codex | Pushed SHA retested in clean Mac Studio Docker

The strict provider-receipt/project-binding slice is committed as `ce3ae505` and
pushed to `origin/testing`. The clean detached Mac Studio retake at
`$HOME/istara-testing-retake-47bf` was updated to that exact SHA and remained clean.
The benchmark package was copied from a read-only bind mount into a disposable Docker
volume and executed with the existing `/usr/local/bin/docker` Docker Desktop CLI under
`node:20-bookworm`; the volume was removed after the run. Result: `100` tests passed,
`0` failed, exit `0`. No Node runtime, package, model, or other dependency was
installed on the Mac host, and the dirty `$HOME/istara-testing` checkout was not
touched.

This closes the deterministic Node 20 retake for the new oracle. It still does not
close live scientific acceptance: the only retained live artifact has Fleiss
`kappa=-0.125`, Krippendorff `alpha=0.491`, no accepted/reconciled applications, and
the current provider/Petals configuration has not been authorized or verified.
Two-call, long-horizon, human-review/Done/report promotion, and legacy compatibility
migration remain open gates.

### L-403 | 2026-08-27T19:10:30Z | S3-review | gpt-5-codex | CF persistence scope reconciled with April Istara lineage

The CF date/count question was rechecked against Git ancestry, every retained SQLite
store under `/Users/user/Documents`, and the current branch rather than using one
database timestamp as a process-origin proxy. The current shared Compass Forge store
`/Users/user/Documents/compass-forge/.compass-forge/state.sqlite3` contains `60`
spec rows, oldest `CF-SPEC-1` at `2026-07-03T01:11:53Z`; its Istara roots are `10`
rows for `/Users/user/Documents/Istara-main` plus `1` row for the Pi migration worktree.
The repo-local native Istara store contains `5` rows, oldest `CF-SPEC-1` at
`2026-08-23T15:04:20.958685Z`. Other populated stores belong to Compass Forge,
Kairos, or Skills and are not Istara process history.

Git gives the earlier process origin the databases cannot retain: late-March governance
precursor `67302d56` (March 28), first literal Compass marker `741f3420` at
`2026-04-03T15:39:09-03:00` (same-patch ancestor `42e454b0` of current `testing`),
April 10 three-layer testing architecture (`16d18228`) and PR/testing workflow
(`21ef99b1`), first literal `Compass Forge` marker May 2 (`0d0d9a24`), and first
literal `CF-SPEC-` marker May 4 (`7dca7368`). No surviving April CF-SPEC database row
was found, so none is fabricated; that absence is retention scope, not evidence that
Compass was absent from Istara in April.

Verified with read-only SQLite queries, `git show`/ancestry checks, and the existing
history findings. No code, provider, model, Docker workload, or host state changed.
The active implementation gates remain the live three-model Research Spine proof,
Petals cooperation, human reconciliation/Done/report promotion, two-call and
long-horizon receipts, and legacy no-coding-run migration.

### L-404 | 2026-08-27T19:26:00Z | S2-execute/S3-review | Central Pi runtime provider identity guard

Compass impact/why analysis identified a remaining provenance boundary: the Pi
frame mapper could emit a successful `done` event when `route_evidence.model` or
`route_evidence.served_model` contradicted the provider's top-level `served_model`.
The downstream Research Spine coder already rejected this contradiction, but
allowing it through the shared runtime made ordinary consumers observe a false
route and left the central authority weaker than its consumers.

The mapper now returns the typed error `pi_provider_route_identity_mismatch` for a
non-empty contradictory route identity. It intentionally preserves ordinary-turn
compatibility when no provider identity is supplied; missing identity remains
ineligible for formal Research Spine coding and is handled by the existing coder
gate. Two parametrized regressions cover both conflicting route identity fields.

Red/green verification after the change: `tests/pi_production/test_engine_http_provider.py`,
`test_ensemble_identity_parity.py`, `test_runtime_hardening.py`,
`test_w7_validation.py`, `test_w7_pi_manager_integration.py`, and
`test_research_spine_donor_routing.py` report `71` passed; the Research Spine
contract/end-to-end slice reports `34` passed; the deterministic benchmark reports
`100` passed; feature-doc generation reports `224` artifacts and `86/86` checks;
`git diff --check` passes. Live provider identities, Fleiss/Krippendorff acceptance,
human reconciliation, Petals donation, two-call/long-horizon receipts, and current
Docker model configuration remain unverified.

### L-405 | 2026-08-27T19:23:20Z | S2-execute/S3-review | gpt-5-codex | Valid Docker-only Mac Studio deterministic retake

The clean detached checkout `$HOME/istara-testing-retake-47bf` on the Mac Studio was
verified at pushed SHA `172d311ace30a3fbc8cc475ee32793352430eba2`. A disposable Docker
volume was populated from a read-only bind mount and the complete benchmark package was
run under the existing Docker Desktop CLI with `--network none` and `node:20-bookworm`.
The first two retake attempts failed before test execution because the mount omitted the
benchmark's repository-root dependencies (`package.json`/`document_corpus`, then
`scripts/runner/docker-run.sh`); those are harness setup errors, not product failures.
The corrected repository-root retake reached the full suite and passed `100` tests with
`0` failures and exit `0`. The disposable volume was removed afterward; no containers,
models, runtimes, packages, or other dependencies were installed on the Mac host, and
the dirty original `$HOME/istara-testing` checkout was not touched.

Verified: `ssh macstudio 'docker run --rm --network none -v istara-benchmark-retake-172d311:/work -w /work node:20-bookworm npm test --prefix tests/real_user_benchmark'` — `100 passed`, exit `0`; `docker volume rm istara-benchmark-retake-172d311`; detached checkout clean.
Compass evidence: command row `395` on CF task `CF-15`.
Next: stage exit remains blocked on live scientific acceptance and owner-approved provider
inputs; deterministic harness coverage is now independently reproduced in Docker.

### L-406 | 2026-08-27T19:43:14Z | S3-review | gpt-5-codex | Deeper CF/Compass provenance reconciled with April Istara history

The earlier database-only interpretation was too narrow. A deeper source-history and
ancestry audit confirms that the user’s statement is correct at the process level:
Istara’s ensemble/research machinery predates April, and Compass governance is explicit
in April. Current-ancestor equivalent `a1594cf30259b045db20e253b907751226053fb1`
(`2026-03-24T18:08:22-03:00`) adds the consensus engine (Fleiss’ Kappa, cosine and
composite scoring), five validation patterns, adaptive validation, ensemble health, and
simulation scenarios. `8d604d2e58dc637a9d06d2c06c02a09e47d60693` (`2026-04-01`,
`v2026.04.01.3`) wires adaptive validation and consensus telemetry into the agent loop.
`13101d26ba66f82a5d86f251c71c8477a811ea6e` (`2026-04-01`, `v2026.04.01.5`) documents
the three-independent-agent pipeline, adversarial debate, Fleiss’ Kappa, promotion and
human-review thresholds, and the tiered research thresholds. `42e454b03de9f5f5464d08eb1d0d6accc774930e`
(`2026-04-03`) explicitly defines Istara’s `Compass` governance system in
`AGENT_ENTRYPOINT.md`; `16d18228`/`21ef99b1` (`2026-04-10`) add the three-layer testing
architecture and PR workflow; `35a3d9f6` (`2026-04-24`) adds Compass swarm intelligence.
Every cited commit is an ancestor of current `testing`.

The naming/persistence boundary is separate: the literal `Compass Forge` block first
appears in current-ancestor `0d0d9a24` (`2026-05-02`), and the first source-history
`CF-SPEC-` marker verified is current-ancestor `7dca7368` (`2026-05-04`). Retained
database rows remain July 3 overall and August 1 for Istara-main, with no April row in
the inspected stores. That dates persistence, not process origin. The corrected
statement is therefore: **Compass/research governance has been in Istara since April,
with ensemble code in March; later Compass Forge and CF-SPEC markers do not invalidate
that lineage.** This audit changed no code, models, providers, Docker workload, or host
state. Live scientific acceptance remains open (`kappa=-0.125`, `alpha=0.491`, zero
accepted/reconciled applications, `needs_reconciliation`).

### L-407 | 2026-08-27T20:00:10Z | S2-execute/S3-review | gpt-5-codex | Completion blueprint and truthful benchmark documentation alignment

The continuation contract was expanded into a detailed, resumable blueprint covering
Compass Forge control-plane discipline; PiModelManager authority and engine parity;
provider-plane three-model Research Spine acceptance; Petals donation, consent,
projection, revocation, and simultaneous-operation checks; tool calls, two-call and
long-horizon receipts; Docker-only Mac Studio execution; deterministic/live status
semantics; and terminal verification/shipping requirements. It explicitly preserves the
April Compass/research lineage and distinguishes `accepted`, `needs_reconciliation`,
`not_runnable`, `blocked`, and `not_run` outcomes.

The stale module docstring in `tests/pi_benchmark/live_driver.py` was corrected: self-MoA
still repeats the approved endpoint, while `full_ensemble` requests `distinct=True` and
`minimum_n` so PiModelManager must resolve genuinely distinct admitted routes (including
consented `pi-petals-*` donors) or fail closed. No runtime behavior changed. Focused
live-driver/MoA contracts pass (`49 passed`); the broader Pi/Research Spine/Petals slice
passes (`425 passed, 0 failed, 5 skipped`); `git diff --check` passes.

`compass-forge gate after` recorded row `328`. Its status remains fail because of
pre-existing complexity, route-drift, type-drift, secret-flow, and large-ledger findings;
the new doc/test changes introduce no architecture/import/security regression. The live
three-model provider proof, Petals served receipts, human reconciliation/Done/report,
two-call, long-horizon, and owner-approved Docker model inputs remain open. Working tree
is intentionally dirty only with these two documentation changes; commit and push occur
after the final review/evidence pass.

### L-408 | 2026-08-27T20:02:04Z | S2-execute/S3-review | gpt-5-codex | Scoped documentation/test correction pushed to testing

Commit `62434b80ca88615517944fad97063e415c01a24c` contains the detailed completion
blueprint and the corrected `live_driver.py` full-ensemble contract. It was pushed to
`origin/testing`; `testing` and `origin/testing` now resolve to the same SHA and the
checkout is clean. The external audit register `/Users/user/Desktop/testing.md` also
contains findings F-R9-153 through F-R9-155; that desktop register is intentionally not
part of the repository commit.

No worktree or branch was removed: the only recovery worktree is unmerged and therefore
not safe cleanup. The next executable step is owner-approved Docker-only provisioning of
three provider-served model identities, followed by the provider/Petals/Research Spine
and long-horizon acceptance matrix in the blueprint.

### L-409 | 2026-08-27T20:02:35Z | S3-review | gpt-5-codex | Push reconciliation checkpoint

The blueprint/documentation commit was followed by a ledger-only checkpoint and
push (`68bf9bfb8cfac52f0e5bcc8a989b2757c0fa71fa`). `testing` and `origin/testing`
remain equal and clean. No live provider or Petals workload was started because
the required owner-approved Docker inputs are still absent; the next agent should
resume at Workstream C, not reinterpret the deterministic `425`/`100` suites as
scientific acceptance.

### L-410 | 2026-08-27T20:11:40Z | S2-execute/S3-review | gpt-5-codex | Mixed provider + Petals Research Spine boundary coverage

Compass impact/why was run for the W7 integration surface and the new focused
test module. The prior tests proved provider-only and Petals-only three-rater
runs independently, but no deterministic test proved that one PiModelManager
catalog could compose both sources simultaneously. A focused regression was
added at `tests/pi_production/test_w7_mixed_pi_sources.py`: one faux managed
provider plus two consented, project-scoped Petals donors are projected into the
same manager; `run_independent_coding_run` selects three distinct identities;
the real dispatcher and PiExecutionService perform structured calls; the Petals
bridge preserves donor/model/project receipts; and the Research Spine accepts
the complete Fleiss/alpha-gated matrix. The fixture intentionally includes a
provider-account receipt because the first attempt was correctly blocked by the
provenance gate when that receipt was empty.

Verification: the focused W7 slice reports `3 passed`; the broader Pi/Petals/
Research Spine production slice reports `776 passed, 0 failed, 5 skipped`;
`feature_docs.py --seed-missing --generate-site --check` reports `224` generated
artifacts and `86/86` checks; `git diff --check` passes. The source test was
moved out of the existing W7 hotspot, so the change does not add its complexity
warning. The working tree contains only the new focused test pending commit.
No live provider or Petals model was loaded, and no Mac Studio host state was
changed. Next: record command/gate evidence, commit/push this test and ledger
checkpoint, then continue with owner-approved Docker-only live acceptance.

### L-411 | 2026-08-27T20:17:05Z | S3-review | gpt-5-codex | Mixed-source regression pushed and gate reconciled

The focused mixed-source regression and this ledger update were committed as
`90387c36` and pushed to `origin/testing`; `testing` and `origin/testing` now
match at that SHA. Compass command evidence rows `396` (focused + broad tests)
and `397` (feature docs) are attached to CF task `CF-15`. `compass-forge gate
after --task CF-15 --summary` reported `new_issue_count: 0`, `new_failures: 0`,
and no actionable failures; its overall `fail` status remains inherited
route/type/secret-flow/large-ledger debt. The working tree is dirty only with
this post-push ledger pointer, which must be committed and pushed next.

The deterministic baseline is now `776 passed, 0 failed, 5 skipped` across the
Pi/Petals/Research Spine production slice, plus the separate `100`-test Node
benchmark. The new boundary proves provider and Petals can coexist in one
manager-backed accepted three-rater run under fakes. Live provider-served
identities, live Petals transport, human reconciliation/Done/report, two-call,
long-horizon, and owner-approved Docker model inputs remain open; no live model
or Mac Studio host process was started.

### L-412 | 2026-08-27T20:24:00Z | S3-review | gpt-5-codex | Clean ref/worktree checkpoint

The post-push ledger pointer was reconciled. `git status --short --branch` is
clean on `testing`; `git rev-parse HEAD` and `git rev-parse origin/testing`
both report `bcc04cd0813b5445adcd6892e63c8d74fdb3d8fe`. The only other worktree
remains the clean but unmerged `recovery/pi-retake-linearized-2026-08-10` at
`4c0ee557`; it is retained because ancestry and ownership do not prove it is
unused. No `local/testing` ref exists. No branch/worktree cleanup was safe or
authorized by the evidence.

This checkpoint changes documentation only. The next safe action remains the
owner-approved Docker-only live acceptance matrix; deterministic fake-backed
results must not be promoted to a live scientific or model-quality claim.

### L-413 | 2026-08-27T20:26:00Z | S3-review | gpt-5-codex | Post-push ledger identity

The clean-ref checkpoint was pushed as `a89b53c1`; this final pointer is written
before the next ledger-only commit, so the next agent should verify the exact
SHA with `git rev-parse HEAD` and `git rev-parse origin/testing` before editing.
At this point the intended testing history is fully reconciled and no untracked
or unstaged files are expected. The recovery worktree remains preserved for
forensic/owner review, not treated as a candidate for merge or deletion.

### L-414 | 2026-08-27T20:29:00Z | S3-review | gpt-5-codex | Ledger SHA semantics corrected

The prior wording could become stale whenever this document was amended,
because the ledger commit itself advances both `testing` and `origin/testing`.
The durable rule is now to verify both refs at continuation time and to treat
the recorded SHA as the last observation before the current ledger amendment.
This avoids claiming a historical SHA is still the tip while preserving a clean,
fully pushed branch. No code, generated artifact, model, container, host process,
worktree, or branch was changed beyond this documentation commit.

### L-415 | 2026-08-27T20:25:03Z | S2-execute/S3-review | gpt-5-codex | Provider identity observer hardened and checkpointed

The deterministic provider-observation gap from F-R9-155 is fixed. `pi-runtime/src/provider.mjs`
now observes bounded `application/json` and `application/*+json` response bodies in
addition to SSE `data:` frames. It buffers only the observer copy, forwards every
original response chunk unchanged to pi-ai, recognizes the common top-level,
`response.model`, and `message.model` envelopes, and ignores malformed observer
JSON so the adapter/parser remains authoritative. Missing or ambiguous identities
still fail closed. A split-body regression was added to
`pi-runtime/test/provider-params.test.mjs`; the ensemble health architecture
documentation and generated site artifact were updated and checked.

Verification attached to CF task `CF-15`: evidence `400` records the Pi-runtime
Node suite (`47 passed, 0 failed, 0 skipped`), `401` records the focused Pi
authority/ensemble/validation slice (`68 passed`), `402` records feature-doc
generation/check (`224` generated artifacts; `86/86` feature checks), and `403`
records the after-gate (`actionable_failures=[]`, `new_issue_count=0`,
`new_failures=0`; overall `fail` is inherited debt). `git diff --check` passes.
The code/docs change is committed and pushed as `6862ffc1acdc72436d7d05a2560f52f499021427`;
re-verify both `testing` and `origin/testing` at continuation time because the
next ledger commit will advance both refs.

This closes a deterministic observer/test-contract defect only. The live proof
is still blocked on owner-approved Docker-only Mac Studio provider inputs and
must separately demonstrate three distinct provider-served identities over the
same source/evidence units, meaningful Fleiss plus Krippendorff reliability,
reconciliation, human Done/report promotion, Petals transport/consent and
revocation, two-call continuity, and long-horizon behavior. No live model was
loaded, no Mac Studio host software was installed, and no worktree or branch
was deleted.

### L-416 | 2026-08-27T20:27:28Z | S3-review | gpt-5-codex | Mac Studio Docker preflight reclassified live run as not_run

The authorized passive SSH preflight used the explicit Docker Desktop CLI path
(`/Applications/Docker.app/Contents/Resources/bin/docker`) and confirmed Docker
Server `29.7.2`. `docker compose ls --all` showed only the unrelated `plex`
project; no Istara test workload or model container was running. The remote
`$HOME/istara-testing` checkout is dirty across application, Compose,
migration, feature-doc, and Build Stream files, and its `testing` branch is
`1b9b6d60` while its locally fetched `origin/testing` is `172d311a`, reported as
`0 306` (306 commits behind). This checkout is therefore not a valid baseline;
the live test is `not_run`, not failed or passed. No pull/reset/clean/model
load/host install was attempted. Compass command evidence `404` records the
preflight and the no-mutation decision.

The local authoritative checkout remains clean on `testing` and equal to
`origin/testing` at the last observation `177f4532` before this amendment. The
recovery worktree remains clean but unmerged and is retained. The next live
step requires owner-approved preservation/reconciliation of the Mac Studio
checkout (or a fresh disposable Docker Compose checkout), explicit provider
inputs for three served identities, and then the full Research Spine/Petals/
two-call/long-horizon acceptance matrix; no scientific claim may be based on
the absent stack.

### L-417 | 2026-08-27T20:29:50Z | S3-review | gpt-5-codex | Full deterministic production slice rechecked

The current local `testing` checkout completed the full `tests/pi_production`
deterministic suite with `441 passed, 0 failed`; no live provider, model, or
Mac Studio workload was contacted. Compass evidence `405` records this exact
command and result. This is a current regression baseline for Pi authority,
Petals, ensemble, Research Spine, accounting, and API tests, but it remains
fixture-backed evidence and cannot answer whether three real served models
produce meaningful Fleiss/Krippendorff reliability or whether a human promoted
the result through Done/report gates.

At the observation before this ledger amendment, local `testing` and
`origin/testing` both resolved to `a321645f`; the amendment commit will advance
both, so a continuation agent must re-run both `git rev-parse` commands. The
Mac Studio Docker preflight remains `not_run` because its Istara checkout is
dirty and 306 commits behind its fetched origin, and no Istara Compose project
is running. The next safe action is owner-approved preservation/reconciliation
or a disposable Docker checkout plus the provider/Petals inputs required by the
live acceptance matrix.

### L-418 | 2026-08-27T20:31:00Z | S3-review | gpt-5-codex | Compass task graph remains open at live-acceptance boundary

Compass Forge `status`/`next` and `spec show CF-SPEC-2` were rechecked after the
deterministic run. The linked task graph currently has `CF-14`, `CF-16`,
`CF-17`, `CF-18`, and `CF-19` done, while implementation `CF-15` and the
spec-validation tasks `CF-13`, `CF-20`, and `CF-21` remain open. `CF-21` is
specifically the requirement that no linked task remain incomplete; it cannot
be closed while the live acceptance evidence is absent. The next action shown
by Compass is `task ready`/`CF-21`, but that is a closure check, not permission
to claim acceptance or to bypass the outstanding implementation/live gates.

The local branch was clean and equal to `origin/testing` at `fce174c8` before
this ledger amendment; re-run both ref checks after the amendment commit. The
remote Mac Studio preflight remains `not_run` (no Istara Compose workload,
dirty checkout, 306 commits behind), so no model loading or host mutation was
performed. Keep CF task statuses open until the owner-approved Docker-only
three-model provider/Petals, Research Spine reconciliation/Done/report,
two-call, and long-horizon evidence is attached.

### L-419 | 2026-08-27T21:15:06Z | S2-execute | gpt-5-codex | Docker QA build-context fix committed and pushed

The root `.dockerignore` previously ignored the entire `scripts/` directory,
which excluded the Docker QA launcher `scripts/istara-qa.sh` from the root
build context. The scoped fix ignores `scripts/*` but re-includes only that
launcher; `tests/test_remote_benchmark_runner_contract.py` now asserts both
rules and the file's presence. This preserves the no-broad-context invariant
while making the documented Docker-only QA entrypoint buildable.

Verified: `python -m pytest -q tests/test_remote_benchmark_runner_contract.py`
= `20 passed, 0 failed`; `git diff --check` = clean; `compass-forge gate
after --task CF-15 --summary` = `actionable_failures=[]`, `new_issue_count=0`,
`new_failures=0` with the repository's pre-existing gate status still `fail`.
Compass command evidence `409` records these results. Commit `16fac555` was
pushed to `origin/testing`; the next continuation must re-check both refs
before any further edit because ledger commits advance both tips. No model was
loaded and no Mac Studio host software or workload was changed.

Next: use this pushed commit in a disposable Docker-only Mac Studio checkout;
the live three-model provider/Petals/reconciliation/two-call/long-horizon
acceptance remains unrun and cannot be inferred from this deterministic fix.

### L-420 | 2026-08-27T21:16:13Z | S3-review | gpt-5-codex | Mac Studio preflight still not runnable; dirty checkout preserved

Passive SSH inspection used the explicit Docker Desktop CLI path
`/Applications/Docker.app/Contents/Resources/bin/docker` and confirmed Docker
Server `29.7.2`. The remote `~/istara-testing` checkout remains on `testing`
at `1b9b6d6098dc4a420aff2cf570b9aa5b982b3949`, while its fetched
`origin/testing` is `172d311ace30a3fbc8cc475ee32793352430eba2`, and it has `340`
short-status entries. `docker compose ls --all` and `docker ps` show only the
unrelated `plex` project/container; no Istara test workload is running.

Result: live acceptance remains `not_run`, not failed or passed. I did not pull,
reset, clean, delete, install, load a model, or mutate the Mac Studio. The
previously dirty checkout is preserved. The local `testing` and
`origin/testing` refs both resolve to `49a24c96` after the pushed checkpoint.
Compass evidence for the remote command must be attached before any live claim.

Next: use an explicit disposable Docker-only checkout/volume on Mac Studio
pointing at `origin/testing` `49a24c96`, without touching `~/istara-testing`;
then run the provider/Petals and full Research Spine acceptance matrix only
after the required owner-approved provider inputs are available.

### L-421 | 2026-08-27T21:23:28Z | S2-execute/S3-review | gpt-5-codex | QA wrapper now honors the Docker-only host boundary

Audit found that `scripts/istara-qa.sh` still invoked repository Python on the
Mac Studio host for `qa`, `collect`, and `reset`, even though DEC-11 requires
the Mac Studio to remain a Docker host/control plane. The wrapper now runs the
governance checks and QA auditor in the disposable `qa-backend` container with
the checkout read-only and only ignored `artifacts/` and `qa/runs/` surfaces
writable. Reset is direct Compose orchestration (still Docker-only), validates
the run id and protected artifact names, and requires an explicit
`QA_CONFIRM=RESET-ISTARA-QA-RUN`; no default confirmation silently authorizes
teardown.

Added regression coverage for container-only governance/collection and
fail-closed reset confirmation. Verified: `bash -n scripts/istara-qa.sh`;
`python -m pytest -q tests/test_qa_stack_contract.py tests/test_qa_reset_seed.py
tests/test_feature_docs.py` = `41 passed`; feature docs regenerated (`224`
site artifacts, `86/86` checks); `git diff --check` clean; Compass Forge
after-gate reports `actionable_failures=[]`, `new_issue_count=0`, and
`new_failures=0` while preserving inherited repository gate debt (`31`
failures/`211` warnings). Compass evidence `413` records the commands and
result. No model load, remote mutation, host package installation, or live
service start occurred.

Next: commit and push this wrapper/docs/test change, re-check local and
`origin/testing` SHA equality, then continue the deterministic Pi/Petals and
Research Spine audit while the Mac Studio provider-input gate remains open.

### L-422 | 2026-08-27T21:31:27Z | S2-execute/S3-review | gpt-5-codex | Deeper ensemble audit found a non-positive-width fail-open edge

Compass Forge impact/why were run for `backend/app/core/pi_runtime/engine.py`
and `tests/pi_production/test_runtime_hardening.py` before editing, followed by
the CF-15 before gate. The code review found that `run_ensemble(n=0,
distinct=False)` constructs an empty endpoint/sample list and returns
`status=success` with zero usage because `all([])` is true. Zero or negative
widths also pass through the distinct branch's minimum-width coercion instead
of being rejected. That can make a malformed or bypassed validation request
look successful while producing no independent judgments, violating the
Research Spine's fail-closed ensemble contract.

This is a concrete implementation/test gap, not a live-model finding. The next
bounded change will reject non-positive `n` and `minimum_n` with the existing
typed Pi endpoint-resolution error before manager/worker work, add regression
tests that assert no binds/turns and preserve the existing three-model and
accounting tests, regenerate the Ensemble Health feature docs, and attach the
before/after gate evidence. No model was loaded and no Mac Studio state was
changed. The remote live acceptance blocker remains owner-approved Docker-only
provider/Petals inputs and a disposable checkout.

### L-423 | 2026-08-27T21:34:24Z | S2-execute/S3-review | gpt-5-codex | Invalid ensemble widths now fail closed and are pushed

Implemented the bounded fix in `PiExecutionService.run_ensemble`: `n` must be
a positive integer and any supplied `minimum_n` must also be positive; invalid
requests raise `PiEndpointResolutionError` before manager projection or worker
startup. Added a regression asserting a zero-width request cannot invoke either
manager or supervisor work. The existing Pi manager, Petals, identity-parity,
accounting, validation, Research Spine contract, and integrity-metric tests
remain green (`119 passed`). Ensemble Health feature source and generated site
were regenerated and checked (`224` artifacts, `86/86` checks).

Compass Forge command evidence `416` records the focused test and feature-doc
verification; gate evidence `417` records `actionable_failures=[]` and
`new_failures=0` with the repository's inherited gate debt unchanged (`31`
failures/`212` warnings). Commit `5684ee00c50410707724fda2537d54cb79995529`
is pushed and local `testing` equals `origin/testing`. No model was loaded and
no Mac Studio state changed.

Next: inspect the generic reliability gate's configured-versus-served identity
semantics and benchmark route-receipt tests, then return to the disposable
Docker-only Mac Studio acceptance preparation. Live provider/Petals,
reconciliation/Done/report, two-call, and long-horizon proof remains absent.

### L-424 | 2026-08-27T21:42:15Z | S2-execute/S3-review | gpt-5-codex | Reliability independence now uses provider-served identity

The generic Research Spine reliability gate previously counted `model_name` or
`model` as the independent identity even when each application carried a
different configured alias and the same provider-served checkpoint. That could
certify Fleiss' Kappa for three aliases backed by one model. The gate now gives
`served_model` precedence for both distinct-model counting and effective
checkpoint provenance, preserving legacy fields only when no served receipt is
available. This matches the route-receipt oracle and prevents configured labels
from fabricating scientific independence.

TDD evidence: the new regression was first run red (the pre-fix result was
`fleiss_kappa_with_krippendorff_alpha_companion`), then passed after the change.
Focused Research Spine, Pi ensemble, identity, accounting, validation, and
runtime suites pass (`120 passed`). Feature docs regenerated and checked (`224`
artifacts, `86/86` checks); `git diff --check` is clean. Compass Forge command
evidence `419` records the test/doc/diff result; the after-gate reports
`actionable_failures=[]`, `new_failures=0`, and inherited gate debt of `31`
failures/`212` warnings. No model was loaded and no Mac Studio state changed.

Next: commit and push this hardening plus the ledger checkpoint, then audit the
user-visible engine labels (`Istara`, `Agentic Loop`, `Pi Agentic Loop`) against
the dispatcher and settings contracts before preparing the disposable remote
Docker run. Live provider/Petals, reconciliation/Done/report, two-call, and
long-horizon proof remains absent.

### L-425 | 2026-08-27T21:51:56Z | S3-review | gpt-5-codex | Reconciled April Compass lineage with CF-SPEC persistence

The owner correction is valid at the process-lineage level. A deeper read of
all reachable Istara refs, April tags, current `testing` ancestry, deleted-file
history, unreachable commit metadata, and retained state stores confirms that
Compass was already part of Istara on April 3, 2026. Current `testing` contains
the equivalent April 3 Compass entrypoint/doctrine commits (`42e454b0` and
`ce19476e`), the April 10 three-layer testing architecture (`16d18228`), the
April 10 `TESTING.md`/PR-required Compass workflow (`21ef99b1`), and the related
April test pass (`c0ddf50c`); every hash is an ancestor of `refs/heads/testing`.
The April 3 tag `v2026.04.03.3` and April 10 tag `v2026.04.10.13` expose the
same Compass sections in the historical files. These are not August additions.

The naming and storage boundaries remain separate. The first literal
`compass-forge` block in Istara Git is `0d0d9a24` (2026-05-02), and the first
literal `CF-SPEC-*` document marker is `7dca7368` (2026-05-04); both are also
ancestors of `testing`. The retained shared CF database currently has 60 spec
rows overall (oldest `2026-07-03T01:11:53Z`): 37 Compass Forge, 12 WildSync,
10 `/Users/user/Documents/Istara-main`, and 1 Istara Pi-migration worktree.
The Istara-main project scope therefore has 11 rows across the two registered
Istara roots, with its first retained row on `2026-08-01T19:46:34Z`. The
repo-local Istara database has 5 rows from August 23–26. The pre-native backup
has 50 rows through August 13; the root Documents CF database is empty. The
Kairos/Skills/WildSync databases are separate project stores and are not
Istara CF history. No retained state database contains an April CF-SPEC row.

Result: “CF/Compass has been in Istara since April” is correct when CF means
the governed Compass development/testing process. “The state database has
April CF-SPEC rows” is not supported by any retained store. The previous
July/August dates described persistence scope, not process origin; reports must
state both dimensions rather than use a database age as a proxy for lineage.
No code, provider, model, Docker, host, or testing data changed in this audit;
the code baseline remained `a58bb1e2`, and this ledger entry is the only
working-tree change before checkpointing it to `testing`/`origin/testing`.

Evidence commands: `git log --all`/`git grep` over April tags and current
testing ancestry; `git merge-base --is-ancestor` for all cited hashes;
`git fsck --unreachable`; and read-only SQL counts over every retained
`.compass-forge/state.sqlite3` and pre-native backup found under Documents.
CF before-gate baseline: `actionable_failures=[]`, `new_failures=0`, inherited
31 failures/212 warnings. The live Research Spine acceptance gate remains open.

Next: preserve this two-axis lineage/persistence wording in the final report,
then continue CF-SPEC-2 implementation and the Docker-only live acceptance
matrix; do not backdate or synthesize missing CF-SPEC rows.

### L-426 | 2026-08-27T21:53:21Z | S3-acceptance | gpt-5-codex | Provenance checkpoint gated and transported

Post-checkpoint Compass Forge after-gate evidence `425` reports
`actionable_failures=[]`, `new_failures=0`, and `new_issue_count=0`; the
repository's inherited baseline remains 31 failures and 212 warnings. The
lineage/persistence reconciliation is committed as `c565e30b` and local
`testing` equals `origin/testing`; the worktree is clean. This gate only
qualifies the historical documentation checkpoint. It does not close the
open CF-SPEC-2 live Research Spine acceptance gate.

Next: resume CF-SPEC-2 implementation and Docker-only live acceptance when
owner-approved provider/model inputs are available.

### L-427 | 2026-08-27T22:03:17Z | S3-review | gpt-5-codex | Independent recheck confirms April Compass origin and later CF-SPEC persistence

After the owner challenge, I repeated the historical search independently
against all reachable Istara refs/tags and the retained Compass Forge stores.
The earliest Istara Compass process evidence is the April 3, 2026 commit
`42e454b0` (the `Compass` section in `AGENT_ENTRYPOINT.md`), followed by the
April 3 doctrine hardening `ce19476e`, April 10 three-layer testing mandate
`16d18228`, April 10 `TESTING.md`/PR workflow `21ef99b1`, and the related April
test pass `c0ddf50c`. Each cited commit is an ancestor of `testing`; the April
tags `v2026.04.03.3`, `v2026.04.10.13`, and `v2026.04.20.4` expose the same
Compass material. Therefore the statement that Compass was present in Istara
since April is confirmed.

The naming and persistence milestones are different facts. The first literal
`compass-forge` workflow block in Istara Git is `0d0d9a24` on May 2, 2026, and
the first literal `CF-SPEC-*` document marker is `7dca7368` on May 4, 2026.
The retained shared state database contains 60 specs overall, oldest
`2026-07-03T01:11:53+00:00`; 11 rows are Istara-scoped across the two retained
Istara roots, oldest `2026-08-01T19:46:34+00:00`. The repo-local Istara state
database contains 5 rows, oldest `2026-08-23T15:04:20.958685Z`. No retained
database contains an April CF-SPEC row, so database age must not be used as a
proxy for the April process origin.

This is a read-only provenance correction; no code, model, Docker, host, or
testing data changed. It supersedes any report that says Compass itself began
in July/August while preserving the truthful statement that April CF-SPEC rows
are not present in retained state. The live Research Spine acceptance gate
remains open.

Evidence rechecked: `git log --all`/path history, `git show`/`git grep` for the
April commits and tags, `git merge-base --is-ancestor` for every cited hash,
and read-only `sqlite3` queries over the shared and repo-local `specs` tables.

### L-428 | 2026-08-27T22:25:09Z | S2-execute/S3-review | gpt-5-codex | Closed deterministic task-lineage and route-provenance oracle gaps

Scope: CF-SPEC-2 / CF-21 implementation slice. The benchmark and chat contracts now
carry one explicit, project-scoped task anchor through both long-horizon turns and
through every engine seam. `POST /api/chat` rejects a task belonging to another
project before session/message/RAG side effects; the Pi, native-tools, and text
fallback dispatcher calls all forward `task_id`; the usage endpoint returns the
binding; and the frontend `ChatUsage` type reflects the identity rows. The Docker
benchmark creates the anchor task, sends it on both calls, checks that it persists,
and requires unique successful receipts with non-empty provider model and endpoint
identity. The ASGI restart test proves the same task id survives two calls on both
Pi and legacy loop selectors. This is causal/task observability, not a claim that a
BACKLOG benchmark task is human-approved or reportable.

The outer Docker runner now fails closed on any dirty source checkout before creating
result mounts, pulling images, or starting a container. This prevents the mounted
working tree from diverging from the advertised `git archive HEAD` provenance and
preserves the Docker-only host rule.

Verification recorded for this slice: focused Pi/benchmark/chat/ASGI suite `63 passed,
1 inherited PytestUnhandledThreadExceptionWarning`; research-spine, model-management,
mixed provider/Petals, W7, W5, and end-to-end deterministic suite `163 passed`; Ruff
on all changed test/benchmark modules passed; Python compileall and `git diff --check`
passed; feature-doc generation/check produced `224` artifacts and passed for `86`
features. Compass Forge `gate before --task CF-21` record `350` remains an inherited
repository gate failure (31 inherited failures / 212 warnings at that snapshot),
with no new architecture failure from this slice. Command evidence is recorded as
CF task evidence `435` (lint/compile/docs) and `436` (focused deterministic suites);
the after-gate receipt is CF task evidence `440` with `new_issue_count=0`,
`new_failures=0`, and no actionable failures. The repository-wide gate remains
red only on inherited debt.

Open boundary: no live Mac Studio Istara stack was run in this slice, no model was
loaded, and no host package was installed. Three provider-served model identities,
Fleiss' kappa plus Krippendorff alpha over real evidence units, Petals donation
cooperation, reconciliation/accepted promotion, human-approved Done/report gates,
and live two-call/long-horizon behavior remain open CF-SPEC-2 acceptance gates.

### L-429 | 2026-08-27T22:28:31Z | S3-review | gpt-5-codex | After-gate receipt closes the deterministic slice cleanly

Compass Forge after-gate for CF-21 was rerun after removing the optional frontend
type-module change that introduced a new complexity warning. Receipt `440` reports
`new_issue_count=0`, `new_failures=0`, and `actionable_failures=[]`; the remaining
`31` failures and `212` warnings are inherited repository debt. The changed source
checkout passes `git diff --check`; the deterministic backend/benchmark suites and
feature-doc check remain green. The next bounded step is to stage only the eleven
intended files, commit/push `testing`, verify local/remote equality, and then wait
for an owner-approved clean Docker-only Mac Studio acceptance run.

### L-430 | 2026-08-27T22:36:00Z | S3-review | gpt-5-codex | Revalidated deterministic slice and latest pre-gate

The focused Pi/benchmark/chat/ASGI contract suite was rerun after reverting the
optional frontend type-only module: `63 passed, 1 inherited
PytestUnhandledThreadExceptionWarning` in `25.61s`. The changed test/benchmark
modules remain Ruff-clean; compileall, `git diff --check`, and the previously
recorded research-spine/model-management ensemble groups remain green.

Compass Forge `gate before --task CF-21` receipt `354` was recorded after the
ledger update. It reports no new issues, forbidden dependencies, missing paths,
or import cycles. The Build Stream ledger appears in the large-file comparison
because this durable record is now approximately 760 KB; that is documented
artifact-size debt under the active suppression, not a code or runtime failure.
Inherited repository debt remains `31` failures / `212` warnings, and the live
Research Spine gate remains open. No Mac Studio container was started, no model
was loaded, and no host package was installed.

### L-431 | 2026-08-27T22:37:00Z | S3-review | gpt-5-codex | Final after-gate and evidence attachment

After-gate receipt `355` is attached to CF-21 as task evidence `445`. It reports
`new_issue_count=0`, `new_failures=0`, and no actionable failures. The gate is
still red only because of inherited repository checks (`31` failures and `212`
warnings, including existing route/type drift and security-flow debt); this is
not a regression from the eleven-file slice. Focused deterministic test receipt
is task evidence `442`, and pre-gate receipt `354` is task evidence `443`.

The next action is a narrow commit containing only the eleven intended files,
push `testing`, verify local/remote SHA equality and a clean worktree, then
perform the owner-approved Docker-only Mac Studio run. Live three-model
provider identity, Fleiss' kappa/Krippendorff alpha over raw evidence units,
Petals donation, reconciliation, accepted promotion, human-approved Done/report,
and two-call/long-horizon gates remain unclaimed until their runtime receipts
exist.

### L-432 | 2026-08-27T22:39:00Z | S3-review | gpt-5-codex | Testing branch reconciled and ready for live gate

The eleven-file deterministic hardening slice is committed as
`085ae0b255f758ac47b8ff3cd9ba34bcd55bf50a` and pushed to `origin/testing`.
Local `testing` and `origin/testing` resolve to the same SHA and the source
worktree is clean; Compass Forge task evidence `448` records the exact status,
push, and equality checks. This commit includes the task-bound long-horizon
oracle, project-scoped chat task validation, Pi/native/text task propagation,
the Docker runner dirty-check, contract tests, feature-doc regeneration, and
the durable Build Stream record.

The code and deterministic fixtures now prove causal identity and route receipt
shape, not scientific validity. The live acceptance matrix is still pending:
it must run from this clean checkout inside Docker on the Mac Studio, with
three provider-served distinct model identities and Petals configuration, and
must capture raw evidence-unit ratings, formal Fleiss' kappa plus companion
Krippendorff alpha, reconciliation and accepted promotion, human-approved
Done/report gates, and the two-call/long-horizon receipts. No host install,
host model load, or live request was performed here.

### L-433 | 2026-08-27T22:42:00Z | S3-review | gpt-5-codex | Rechecked remote Docker boundary; live gate remains not_run

The fresh passive SSH preflight used `/usr/local/bin/docker` only and observed
Docker Server `29.7.2`, the unrelated `plex` project, and no Istara Compose
workload. The remote `~/istara-testing` checkout is still dirty and remains at
the old testing SHA while its fetched `origin/testing` is a different, newer
SHA. No pull, reset, cleanup, host installation, model load, or live request
was performed. Compass Forge task evidence `450` records the sanitized result;
the matching audit entry is F-R9-162 in `/Users/user/Desktop/testing.md`.

This is an operator/baseline blocker, not an application verdict. The clean
local `testing`/`origin/testing` checkout is ready, but the live three-model
Research Spine matrix must stay `not_run` until an isolated Docker checkout,
explicit provider-served identities, Petals configuration, and approved
runtime inputs are available. The next agent should provision only that
disposable Docker workload and retain the dirty remote checkout untouched.

### L-434 | 2026-08-27T22:45:00Z | S3-review | gpt-5-codex | Final tree after-gate attached

After-gate receipt `357` is attached to CF-21 as task evidence `453`. The
comparison remains clean (`new_issue_count=0`, `new_failures=0`, no actionable
failures); the repository gate is red only on inherited checks (`31` failures,
`212` warnings). The final branch checkpoint will include this ledger line and
must preserve the same clean local/remote testing ref equality. The live Docker
acceptance gate remains open and explicitly `not_run` per L-433/F-R9-162.

### L-435 | 2026-08-27T22:48:00Z | S3-review | gpt-5-codex | Corrected final SHA pointer and handoff state

The final pushed branch advanced from `085ae0b` through the ledger-only
checkpoints `df89e9f`, `6f24758`, and `a0a56c7`. The handoff pointer now names
the actual clean tip `a0a56c7c3993b0c042f0ac2212a894186390394b`; local
`testing` and `origin/testing` are equal and the worktree is clean. CF task
evidence `454` records that equality. The after-gate comparison remains clean
per receipt `357`/evidence `453`; inherited repository debt is unchanged.

No live Mac Studio Istara workload exists, so CF-SPEC-2 cannot be accepted from
deterministic evidence alone. The next agent must preserve the dirty remote
checkout, provision an isolated Docker-only workload from this exact tip, and
capture the open Research Spine, Petals, provider identity, two-call, and
long-horizon receipts before attempting task completion.

### L-437 | 2026-08-27T22:56:00Z | S3-review | gpt-5-codex | Terminal pointer made hash-stable

The final documentation checkpoint advanced the branch to
`0b77688694cc858e6a2ffc87a6d6b5522c39fe24`; local `testing` and
`origin/testing` are equal and the worktree is clean. Because any subsequent
ledger append necessarily creates a new commit, the YAML `next_action` now
points to terminal CF evidence `458` rather than embedding a hash that would
immediately become stale. The terminal after-gate for that tree reports zero
new issues and zero actionable failures; inherited repository debt remains
unchanged. The live Mac Studio gate is still `not_run` under L-433/F-R9-162.

### L-436 | 2026-08-27T22:52:00Z | S3-review | gpt-5-codex | Final branch and gate handoff

After-gate receipt `358` is attached as CF-21 evidence `456`; it reports zero
new issues, zero new failures, and no actionable failures against the final
tip `f1b31a23da2e1b3ce317e78b3f286b48bb84de7a`. The only remaining gate output
is inherited repository debt (`31` failures / `212` warnings). The branch is
clean and equal to `origin/testing`; CF evidence `454`/`451`/`449` record the
preceding equality checkpoints. This final ledger update is documentation-only
and does not change application behavior.

The active goal is intentionally not complete: the Mac Studio has no Istara
Compose workload and its checkout is dirty/outdated (L-433, F-R9-162). A future
agent can resume from this exact clean tip and must run the live Docker-only
three-model/Petals Research Spine matrix, including raw evidence-unit coding,
formal Fleiss' kappa plus Krippendorff alpha, reconciliation, accepted
promotion, human-approved Done/report, and two-call/long-horizon receipts.

### L-438 | 2026-08-27T22:53:00Z | S3-review | gpt-5-codex | Docker-only model inventory confirms setup blocker

The owner-authorized passive SSH preflight used Docker Desktop's explicit
`/usr/local/bin/docker` CLI and found Docker Server `29.7.2`, the deploy env
file, and the configured `$HOME/Istara-Projects/models` directory, but zero
GGUF files under that model root or the bounded home-directory search. The
unrelated `plex` workload remains the only Compose workload; the dirty
`~/istara-testing` checkout was not touched. No host package/model install,
model load, pull/reset, cleanup, or live request was performed. Compass Forge
task evidence `461` is the sanitized receipt. The three-model wrapper must
remain `not_run` until all provider-served model inputs are supplied inside the
Docker-only process; no placeholder or deterministic fixture can satisfy this
live acceptance gate.

### L-439 | 2026-08-27T22:55:00Z | S3-review | gpt-5-codex | After-gate attached for model inventory blocker

After-gate record `363` is attached to CF-21 as task evidence `466`. It reports
zero new issues, zero new failures, and no actionable failures; the repository
gate remains red only on inherited debt (`31` failures / `212` warnings). The
checkpoint commit was pushed to `origin/testing`, and the local worktree is
clean/equal. The live three-model/Petals Research Spine gate remains `not_run`
because evidence `461` found zero GGUF inputs on the Mac Studio. The next agent
must keep the dirty remote checkout untouched and resume only after supplying
provider-served model inputs through the Docker-only wrapper.

### L-440 | 2026-08-27T23:03:09Z | S2-execute/S3-review | gpt-5-codex | Provider profile exposed and fixed a Bash nounset runner defect

The first real provider-only invocation from the immutable remote checkout at
`56e37b6` did not reach Compose: `reset_stack_for_engine` expanded the optional
`COMPOSE_PROFILE_ARGS` and `COMPOSE_DONOR_SERVICES` arrays directly while the
wrapper runs with `set -u`, producing `line 285: COMPOSE_PROFILE_ARGS[@]: unbound
variable`. This is a benchmark-harness defect, not an application or model
result. The wrapper now builds a `compose_args` command array and appends each
optional array only when it is non-empty, preserving provider, Petals, and
combined profile argument order. A static regression contract covers both
empty-array paths; `bash -n`, the remote-runner Python contract suite (22
passed), the full real-user benchmark Node check (100 passed), and
`git diff --check` all pass locally. No host package/model installation or model
loading occurred; the provider Docker acceptance must be rerun from the new
clean pushed tip before any runtime conclusion is made.

### L-441 | 2026-08-27T23:45:05Z | S3-review | gpt-5-codex | Corrected Compass/Compass Forge provenance after deeper retained-history search

The owner correction was valid. A deeper read-only search separated three
milestones that the prior report had conflated: (1) Istara research/ensemble
provenance, (2) Compass governance and its literal CF integration, and (3) the
later standalone Compass Forge SQLite registry. Retained Istara Git objects
show March research/ensemble precursors (`3308350c`, 2026-03-14 Kappa skill;
`4ba41a4f`, 2026-03-17 dual-coding/codebook/evidence validation;
`9a218603`, 2026-03-24 ensemble validation/compute pool). The earliest
reachable Compass doctrine on the active Istara history is 2026-04-03
(`42e454b0`, `AGENT_ENTRYPOINT.md`), followed by doctrine hardening and the
three-layer testing architecture on 2026-04-03--04-10 (`ce19476e`, `16d18228`,
`21ef99b1`, `c0ddf50c`). Literal managed `compass-forge:start` wiring first
appears on 2026-05-02 (`0d0d9a24`), and the first tracked literal `CF-SPEC-*`
marker on 2026-05-04 (`7dca7368`). The standalone Compass Forge Build Stream
roadmap begins 2026-07-02; the shared CF database's oldest spec row is
2026-07-03. Thus CF/Compass has been part of Istara's April-era development
system (with literal CF wiring by May); July/August describes registry
persistence only, not origin. March objects outside the current `testing`
ancestry remain historical corroboration, not current-branch evidence. No
retained CF SQLite database contains an April spec row. This correction changes
documentation only; no code, Docker workload, host software, model, or test
data was mutated, and the live three-model Research Spine gate remains open.

Evidence: `git log --all`/`git show`/`git grep` over the cited hashes and paths,
`git merge-base --is-ancestor` against `HEAD` to distinguish active-branch
evidence from retained historical objects, and read-only SQL over every
retained `.compass-forge/state.sqlite3` plus the standalone CF Build Stream
roadmap. The corrected two-axis wording is now recorded in the Current truth
section above so a future agent cannot infer system age from CF-SPEC row age.

Next: preserve this provenance distinction in the final handoff, then resume
the Docker-only provider/Petals acceptance from the clean pushed `testing` tip;
do not claim three-model Fleiss/alpha, reconciliation, Done, or report gates
until provider-served identities and terminal receipts exist.

### L-442 | 2026-08-27T23:56:28Z | S2-execute/S3-review | gpt-5-codex | Provider-only Docker acceptance reached the scientific oracle and correctly blocked

The corrected runner completed both selected comparison arms from the clean
remote checkout at `5a891cc50a3f2d6f56b1055e80095c636384c641`, rather than
crashing in Bash before Compose. The legacy and PI probes each started their
own fresh Docker database stack; the runner reported `blocker-bearing arms=2`
and exited with the expected non-zero comparison result. The final PI artifact
is run `2026-08-27T23-56-19-573Z` with score `25.8/100`, three blockers, zero
chat turns, zero completed tasks, and six uploaded documents. This profile
intentionally selected provider/corpus/coding only: Petals and long-horizon
were not selected, so their gates remain open rather than passing by omission.

The live Research Spine oracle behaved fail-closed: project identity matched,
raw evidence units were created, and telemetry was recorded, but the coding
run was `blocked`, with `distinct_model_count=0`, `served_model_count=0`,
`rater_count=0`, zero code applications, `kappa=null`, `alpha=null`, and
`promotion_status=blocked`. The route evidence records
`insufficient_distinct_pi_models`; no independent provider-served model
identity was proven. Traceability also correctly reported no coding runs,
applications, or reconciliation decisions bound to the current run, while
the report gate stayed
`accepted_reconciled_evidence_from_approved_done_tasks_only`. Therefore this
run proves the harness reaches and enforces the scientific oracle, but it does
not prove the ensemble engine, Fleiss' kappa, Krippendorff alpha, reconciliation,
human-approved Done/report, Petals donation interoperability, two-call
causality, or long-horizon behavior.

The runtime remained Docker-only: remote `testing` was clean/equal to
`origin/testing` at the recorded SHA, the explicit Docker CLI was used, and no
host package/model installation or model load occurred. Artifact receipts were
captured before teardown: `run-summary.json` SHA-256
`2a6e1e014090b522f733e6d81f362fe8de3940d9802c412edb1e5decbbf2f042`,
`research-spine-evidence.json`
`56d8e7bb573f013c273e411d0eab2892ced5cacce95a520951f395b1ce63d4c2`,
`run-metadata.json`
`e02ce1c40ef87367df48a78401493e76486402109bbc412c7b239f131be585d3`, and
`scorecard.json`
`b26e0c637f3745835972c76247a59e95b0c82a27b5ea12fe555931e690e4046c`.

Remaining acceptance work is concrete: provide three independently served PI
model identities and valid route receipts inside Docker; rerun provider,
Petals, and combined profiles with two-call and long-horizon enabled; require
non-empty raw-source code applications, valid bounded Fleiss/alpha metrics,
reconciliation, accepted promotion, human-approved Done/report, Petals/model
donation lifecycle evidence, and task/route causality. Do not convert the
current blocked result into a model-quality claim or close CF-SPEC-2.

### L-443 | 2026-08-28T00:04:06Z | S2-execute/S3-review | gpt-5-codex | Corrected stale Build Stream tip pointer after provenance audit

The deeper retained-history audit is now internally consistent: the Current
truth section names the latest observed equal `testing`/`origin/testing` tip as
`992a23bf` instead of the superseded `fce174c8`. The April Compass doctrine and
three-layer testing evidence remain unchanged; this is a pointer correction,
not a claim that the standalone CF registry had April rows. `git status` was
clean before the edit, and the edit was preceded by Compass Forge impact/why
inspection plus before-gate record `376`. The live Docker-only three-model,
Petals, Fleiss/alpha, reconciliation, Done/report, two-call, and long-horizon
gates remain open exactly as recorded in L-442.

Next: attach the post-change gate and this ledger checkpoint to CF-SPEC-2, then
continue the traceability/oracle audit before changing backend or benchmark
semantics. Do not create a local/testing ref or delete the preserved recovery
worktree.

### L-444 | 2026-08-28T00:12:05Z | S2-execute/S3-review | gpt-5-codex | Bound taskless Research Spine coding runs to traceability by explicit run ID

The benchmark creates project-level coding runs with `task_id=null`. The prior
traceability query only discovered runs through task-linked code applications,
so a blocked run with zero applications vanished from `/traceability`, and a
future successful taskless run could never expose its applications or evidence
edges to the benchmark oracle. The API/service now accept an optional,
project-scoped `coding_run_id`; that filter includes the exact run even when it
has zero applications, scopes applications/decisions/edges to the same run,
and leaves all reportability gates unchanged. The benchmark binds its
traceability read to the returned run ID, while its exact application/edge
checks still fail closed for incomplete or blocked runs.

Verification before commit: `rtk pytest -q
tests/test_research_validity_contract.py tests/test_research_spine_donor_routing.py
tests/pi_production/test_w3_research_spine.py
tests/pi_production/test_w7_pi_manager_integration.py` => 62 passed;
`node --test tests/real_user_benchmark/lib/research-spine-probes.test.mjs` =>
37 passed; `python scripts/feature_docs.py --seed-missing --generate-site
--check` => 86 feature checks passed; `git diff --check` and Python compileall
passed. Compass Forge after-gate record 379 reports no missing paths, forbidden
dependencies, or import cycles; it flags the touched service/test complexity
warnings as new comparison warnings alongside the repository's inherited gate
debt. No Docker workload, host package/model install, or live model load was
performed for this code-only correction.

Evidence: backend/service and route changes, benchmark query/acceptance test,
taskless blocked-run regression, architecture/feature documentation, generated
feature site, and CF after-gate record 379. Working tree was clean at base
`3d2dcc6993ac2fdbab885547cda6a57f24acef64` before this uncommitted change.

Next: commit and push this correction to `testing`, attach command/gate
evidence to CF-15, update the YAML `last` pointer to the new commit, and keep
the live three-model/Petals/two-call/long-horizon/Done/report gates open until
owner-approved Docker inputs exist.

### L-445 | 2026-08-28T00:17:05Z | S2-execute/S3-review | gpt-5-codex | Pushed taskless traceability correction and synchronized continuation tip

Commit `70e4ad9d6456074ecf862aeb05534916cd2217c5` contains the explicit
`coding_run_id` traceability filter, benchmark binding, regression coverage,
architecture/feature documentation, generated site artifacts, and L-444's
verification record. It is pushed to `origin/testing`; local `testing` and
`origin/testing` resolve to the same SHA and the worktree is clean. The YAML
frontier now points at this commit and L-445 so a stateless agent starts from a
truthful continuation tip. The preserved recovery worktree remains untouched.

CF evidence to attach: after-gate record 379; 62 focused Python tests;
37 Research Spine benchmark tests; feature-doc check (86/86); diff/compile
checks. The gate still carries inherited repository debt plus comparison
warnings for the already-large touched service/test files; no new fail/block
was introduced by the correction. Live provider-served three-model, Petals,
two-call, long-horizon, reconciliation, Done, and report gates remain open.

Next: verify CF task evidence attachment, then inspect the remaining Pi
authority/engine matrix and ensemble route receipts before attempting any new
live Docker run.

### L-446 | 2026-08-28T00:17:35Z | S2-execute/S3-review | gpt-5-codex | Corrected March ancestry claim after deeper Compass audit

The provenance wording in the Current truth section was audited against both
the commit graph and the active remote-tracking ref. `git merge-base
--is-ancestor` returns success for `3308350c`, `837ed4fc`, `a1594cf3`,
`42e454b0`, `ce19476e`, `16d18228`, `21ef99b1`, `c0ddf50c`, `0d0d9a24`, and
`7dca7368` against both `refs/heads/testing` and
`refs/remotes/origin/testing`. The current line therefore includes the March
research/ensemble foundations and the April Compass doctrine. The earlier
hashes `4ba41a4f` and `9a218603` have identical patch IDs to the current-line
dual-coding and ensemble commits but are parallel-history copies, so they are
not themselves ancestors. This is the precise explanation for why a shallow
search can report contradictory dates.

The three dates remain separate: April 3 is the first reachable Istara
Compass doctrine (`AGENT_ENTRYPOINT.md`); May 2 is the first literal managed
`compass-forge:start` block; May 4 is the first tracked `CF-SPEC-*` marker;
July 3 is the oldest row in the retained standalone CF SQLite registry. The
registry date is not the origin date of Compass in Istara. CF before-gate
record 380 captured the documentation edit; it reports only inherited/new
warnings (including the path-scoped large Build Stream ledger suppression),
with no missing required paths, forbidden dependencies, or import cycles.

Next: add this correction to the external findings ledger, commit and push the
documentation update, then continue the open live three-model/Petals/
two-call/long-horizon Research Spine acceptance work. No live model load or
host installation was performed.

### L-447 | 2026-08-28T00:20:10Z | S2-execute/S3-review | gpt-5-codex | Pushed corrected Compass ancestry chronology

The deeper provenance correction is committed as `9b8ebfb8` (`docs: correct
March Compass ancestry`) and pushed to `origin/testing`. The local
`refs/heads/testing` and remote-tracking `refs/remotes/origin/testing` tips
are expected to be equal at this commit after the push; verify before the next
continuation. The durable YAML frontier now points to L-447 and this SHA.
External finding F-R9-168 records the same correction in
`/Users/user/Desktop/testing.md`. CF after-gate record 381 is the post-edit
receipt; its `new_issues` set is empty, with the large Build Stream document
remaining covered by the existing path-scoped suppression.

No code, model configuration, container, host package, or live model state was
changed. The live three-model/Petals/two-call/long-horizon Research Spine gate
remains open pending provider-served inputs and terminal scientific receipts.

### L-448 | 2026-08-28T00:21:45Z | S2-execute/S3-review | gpt-5-codex | Recorded final post-gate for ancestry correction

CF after-gate record 382 covers the final YAML/ledger update and reports no
new issues, no missing required paths, no forbidden dependencies, and no import
cycles. The path-scoped suppression for this intentionally append-only Build
Stream ledger remains active. Commit and push this documentation checkpoint,
then verify the two testing refs are equal before resuming implementation or
live Docker acceptance.

### L-449 | 2026-08-28T00:23:10Z | S2-execute/S3-review | gpt-5-codex | Synchronized pushed tip after gate checkpoint

The ancestry correction and its post-gate checkpoint are now pushed as
`28884a674a12edc71439a480c9b7a30e1e0206ad` (`docs: checkpoint Compass ancestry
gate`). Both `refs/heads/testing` and `refs/remotes/origin/testing` resolve to
that SHA, and the checkout is clean. The YAML frontier points at the pushed
tip and this ledger entry. The preserved recovery worktree remains untouched;
no stale local/testing ref was created.

### L-450 | 2026-08-28T00:25:20Z | S2-execute/S3-review | gpt-5-codex | Attached ancestry correction to CF-15

Compass Forge task evidence `479` now records the deeper ancestry audit and
post-gate record `382`: March research/ensemble foundations and April Compass
doctrine are reachable from `testing`/`origin/testing`, while May is the first
literal managed `compass-forge:start`/`CF-SPEC-*` wiring and July is only the
oldest persisted CF SQLite spec row. The evidence payload records the exact
commit frontier `0b9d5f1da5959c2c2fca2f685e3d52185503a5bc`. This is attached to
CF-15 without changing task status; the live model gates remain open.

### L-451 | 2026-08-28T00:26:40Z | S2-execute/S3-review | gpt-5-codex | Synchronized CF evidence tip

Commit `9aad89728f049f0c61124a7d92d20116b7322ace` contains the L-450
checkpoint and is pushed to `origin/testing`. Local `testing` and
`origin/testing` are equal at this tip, and the worktree is clean. CF task
evidence `479` remains attached to CF-15; no task was marked done because the
live three-model, Petals, long-horizon, two-call, reconciliation, and
Done/report gates are still unproven.

### L-452 | 2026-08-28T00:42:44Z | S2-execute/S3-review | gpt-5-codex | Closed Istara/Pi invalid ensemble-width parity gap

Compass Forge impact/why was run for the legacy adapter, its authority tests,
and the Ensemble Health living contract before editing; CF before-gate showed
no new failures. The audit found that `PiExecutionService.run_ensemble`
rejected non-positive `n`/`minimum_n`, but `backend/app/core/agentic/legacy.py`
used `kwargs.get("n") or 1` and `kwargs.get("minimum_n") or n`, turning zero
or negative requests into a one-sample provider call. This violated the
Research Spine fail-closed ensemble boundary and made the Istara label differ
from Pi despite both delegating model authority to Pi Model Management.

The legacy adapter now validates both widths as positive integers and raises
the same typed `PiEndpointResolutionError` before any provider delegation.
Regression coverage in `tests/pi_production/test_w1_dispatcher_authority.py`
exercises zero, negative, and zero-minimum cases and proves the provider was
not called. Verification: focused authority/runtime/validation/identity tests
`91 passed`; feature docs `86/86`; `git diff --check` clean; CF command
evidence `482`; CF after-gate evidence `483` (`actionable_failures=[]`,
`new_failures=0`, inherited 31 failures/212 warnings, one non-blocking
complexity comparison warning). External finding F-R9-169 records the same
defect and correction in `/Users/user/Desktop/testing.md`.

No live provider, model load, Docker workload, Mac Studio host change, or
dependency installation occurred. The provider/Petals/combined live matrix,
three served model identities, Fleiss/alpha, reconciliation, human Done/report,
two-call, and long-horizon gates remain open. Commit and push this checkpoint,
then continue the remaining authority and live-acceptance audit.

### L-453 | 2026-08-28T00:43:35Z | S3-review | gpt-5-codex | Transported legacy-width parity checkpoint

Commit `ccdfb30bd3dfac36de1eb14f232f9aabe014e525` contains the shared
fail-closed width validation, regression coverage, Ensemble Health contract,
external finding reference, and L-452 checkpoint. It was pushed to
`origin/testing` without force; `git rev-parse HEAD` and
`git rev-parse origin/testing` both resolve to `ccdfb30bd3dfac36de1eb14f232f9aabe014e525`,
and the main checkout is clean. CF command evidence `482` and after-gate
evidence `483` remain attached to CF-15. No live model or Mac Studio state was
changed; the live three-model/Petals/Research Spine gates remain open.

### L-454 | 2026-08-28T01:16:05Z | S2-execute/S3-review | gpt-5-codex | Closed malformed reliability-metric promotion gap

Compass Forge impact/why was run for the Research Spine reliability helper and
Ensemble Health contract before editing. The audit found that the benchmark
oracle already rejected missing, non-finite, or out-of-range kappa/alpha, but
`evaluate_reliability_gate` could mark a two- or three-coder run accepted from
a passing Fleiss/Cohen score while ignoring a malformed Krippendorff alpha;
non-numeric scores could also raise instead of taking the fail-closed path.

`cb31e76a9a2a88679f3c209c08bd7924d68824fd` adds shared finite/domain checks
(kappa `[-1, 1]`, alpha `<= 1`, booleans/NaN/Infinity rejected) for both
formal multi-coder branches. Invalid metrics now route to
`needs_reconciliation` with an explicit reason. Parametrized regressions cover
missing, non-finite, non-numeric, and out-of-range values. Verification:
contract/metrics tests `68 passed`; feature docs `86/86`; `git diff --check`
clean; CF command evidence `487`; CF after-gate evidence `489` reports
`actionable_failures=[]`, `new_failures=0`, and `new_issue_count=0` (inherited
31 failures/212 warnings remain). The commit is pushed to `origin/testing`,
both testing tips are equal at the recorded SHA, and the main checkout is
clean. External finding F-R9-170 records the same correction.

No live provider, model load, Docker workload, or Mac Studio host change was
performed. The provider/Petals/combined live matrix, three served model
identities, Fleiss/alpha receipts, reconciliation, human Done/report,
two-call, and long-horizon gates remain open. Next: continue the authority and
Docker-only live-harness audit, preserving these gates as unproven until
terminal receipts exist.

### L-455 | 2026-08-28T01:34:00Z | S2-execute/S3-review | gpt-5-codex | Closed Pi settings and transcription Research Spine labeling gaps

The authority audit found that `GET /api/settings/models` silently converted a
Pi Model Management projection/catalog exception into an empty `pi_catalog`,
which could be mistaken for a healthy legacy-only inventory. The route helper
now fails closed with a typed `503` (`pi_catalog_unavailable`) while keeping
the detailed `/settings/pi-catalog` diagnostic endpoint separate. Regression
coverage was added in `tests/pi_production/test_w8_embeddings_gateway.py`.

The Research Spine audit also found that the Whisper primary/optional alternate
transcription pass was described as formal Fleiss' Kappa ICR even though it is
a one-or-two-pass heuristic keyword-category agreement signal, not three
independent coders rating the same evidence-unit matrix. Compatibility
`icr_kappa`/`icr_confidence` fields remain, but transcription results, indexed
audio chunks, file telemetry, docs, and the Istara skill now record and explain
`formal_reliability=false`, `research_spine_eligible=false`,
`validation_scope=transcription_quality_signal`, and
`research_data_status=provisional_until_coding`.

Verification: Pi/settings tests `77 passed`; transcription/files/channel/RBAC
slice `61 passed`; authority/W7/mixed-source/identity/UX/worker/legacy horizon
slice `78 passed`; real-user benchmark Node suite `100 passed`; focused
transcription tests `16 passed`; feature docs `86/86`; `git diff --check`
clean. CF command evidence `493`; before record `391`; after record `392`; gate
evidence `495` reports no new failures/issues (inherited secret-flow and
large-ledger findings remain). External findings F-R9-171 and F-R9-172 record
the corrections in `/Users/user/Desktop/testing.md`.

This checkpoint is code/test/docs-only: no provider, model, Docker workload,
Mac Studio host installation, or host model load occurred. The original plan
is not terminal. Still-open gates are owner-approved Docker-only Mac Studio
provider/Petals/combined runs with three genuinely served model identities,
formal Fleiss/alpha receipts, source-grounded coding/reconciliation, human
Done/report approval, both engine two-call causality, long-horizon
checkpoint/restart/resume and duplicate-side-effect proof, browser/UI
acceptance, fresh crossover benchmark retake, legacy reportability decision,
blind review, and CF-13/15/20/21 closure. Next action: commit/push this
checkpoint, then inspect the Mac Studio Docker preflight/config and run only
the selected acceptance profiles when required provider inputs are present.

### L-456 | 2026-08-28T01:40:00Z | S2-execute/S3-review | gpt-5-codex | Passive Mac Studio Docker preflight re-confirms live gate is not run

Using the existing `ssh macstudio` control path and explicit
`/usr/local/bin/docker` only, the passive check reported Docker client/server
`29.7.2/29.7.2`, one unrelated healthy `plex` container, and no Istara Compose
project or running benchmark workload. The remote checkout at
`$HOME/istara-testing` is on `testing` at `1b9b6d6`, behind its fetched
`origin/testing` by 306 commits, and has extensive uncommitted source,
documentation, generated-artifact, environment, secret, and TLS changes. It
was not pulled, reset, cleaned, inspected by mutation, or otherwise touched.

This is a passive infrastructure receipt, not an application or model verdict.
It confirms that no test is currently observable through the configured Docker
path and that the dirty checkout is unsafe for the authoritative retake. No
host installation, model load, image pull, container creation, provider
request, or data deletion occurred. The live provider/Petals/combined,
three-served-model, formal Fleiss/alpha, two-call, long-horizon,
reconciliation, Done/report, and UI acceptance gates remain open. The next
live attempt requires an owner-approved clean disposable Docker checkout and
explicit provider/model inputs; the dirty remote checkout remains preserved.

### L-457 | 2026-08-28T01:37:56Z | S3-review | gpt-5-codex | Original-plan gap audit and checkpoint reconciliation

The delegated plan-gap audit compared the current branch and Compass Forge
ledger against the original CF-SPEC-2 requirements. It confirms that the
deterministic implementation and oracle work is substantially complete:
Pi authority and legacy/Pi parity, ensemble identity/width validation,
fail-closed reliability metrics, synthetic Research Spine coding/reliability/
reconciliation/promotion/Done-report fixtures, Docker-only guardrails,
benchmark traceability, and deterministic provider/Petals coexistence fakes all
have coverage. CF-SPEC-3, CF-SPEC-4, and CF-SPEC-5 are accepted. CF-SPEC-2
remains open with CF-13, CF-15, CF-20, and CF-21 unresolved; its acceptance
condition cannot be claimed until the linked live and review evidence is
terminal.

The audit preserves the following as unproven rather than inferring them from
fakes: three genuinely distinct provider-served PI models; live independent
source-grounded coding with meaningful Fleiss' kappa and Krippendorff alpha;
reconciliation and human-approved Done/report promotion; Petals consent,
projection, routing, revoke/drain/stop and no-post-revocation behavior; a
combined provider+Petals Docker profile; two-call causality and long-horizon
checkpoint/restart/resume with duplicate-side-effect proof for both engine
paths; browser/UI acceptance; a fresh randomized/crossover benchmark retake;
and the legacy reportability decision for artifacts without `coding_run_id`.

Branch reconciliation is clean: local `testing` and `origin/testing` are equal
at `4bfec205`, the main checkout has no uncommitted changes, and the recovery
worktree remains preserved because it is unmerged. The passive Mac Studio
preflight found only Docker and an unrelated Plex container, no Istara workload,
and a dirty remote checkout; no host installation, model load, provider call,
image pull, container creation, or data deletion was performed. The live gate
therefore remains explicitly blocked on owner-approved disposable Docker
provisioning plus the required provider-served model identities and inputs.

Next action is not to close CF-SPEC-2 or claim ensemble quality. First obtain
the approved Docker-only inputs, run the provider, Petals, combined, two-call,
long-horizon, and Research Spine acceptance profiles with immutable receipts,
then complete UI/benchmark/blind-review gates and attach all command and gate
evidence before closing CF-13/15/20/21.

### L-458 | 2026-08-28T01:39:54Z | S3-review | gpt-5-codex | Live-status poll remains idle

A fresh passive poll through the existing `ssh macstudio` path invoked only
`/usr/local/bin/docker ps` and `/usr/local/bin/docker compose ls --all`. It
again found the unrelated healthy `plex` container and no Istara Compose
project or benchmark workload. Compass Forge command evidence `497` records
this as `live_acceptance=not_run`. The poll performed no host installation,
model load, provider request, image pull, container creation, checkout
mutation, or data deletion. The live gate is unchanged: it awaits owner-
approved disposable Docker provisioning and explicit provider-served model
inputs before any active profile is run.

### L-459 | 2026-08-28T01:46:02Z | S3-review | gpt-5-codex | Reconciled current branch and Compass Forge frontier

Did: Re-ran the repository and control-plane reconciliation before continuing the active goal.
The main `testing` checkout is clean and exactly equal to `origin/testing` at `0ba8b415`;
the only registered auxiliary worktree is the preserved unmerged recovery branch
`recovery/pi-retake-linearized-2026-08-10`. Native Rust Compass Forge remains active with
no Python fallback. The only open CF-SPEC-2 links are CF-13, CF-15, CF-20, and CF-21;
the task registry contains 42 done tasks and 4 open tasks overall.

The previous YAML frontier pointed at the preceding ledger commit rather than the current
branch tip. This checkpoint records the correction and keeps the live acceptance claims
unchanged: no Mac Studio Istara workload, three-served-model Research Spine receipt,
Petals lifecycle receipt, two-call/long-horizon receipt, browser acceptance, benchmark
retake, blind review, or CF-SPEC-2 closure exists yet. No model was loaded, no provider
request was made, and no remote checkout or host workload was mutated.

Next: update the YAML frontier to the commit carrying this checkpoint, then continue with
the owner-gated Docker-only provisioning and exact-SHA acceptance sequence. Do not claim
ensemble quality or Research Spine completion from deterministic evidence alone.

### L-460 | 2026-08-28T01:53:29Z | S2-execute/S3-review | gpt-5-codex | Krippendorff alpha lower-domain fail-closed hardening

The audit found a concrete fail-open defect in both the production Research Spine
metric coercion and the real-user benchmark oracle: Krippendorff alpha was checked
only for a finite value and an upper bound of `1`. An impossible value below `-1`
could therefore be treated as a valid companion metric and reach the reconciliation
or promotion branch. Negative alpha values within `[-1, 1]` remain valid disagreement
signals; values outside that theoretical domain must fail closed.

TDD evidence is preserved. The Python regression first added `alpha=-2.0` to
`tests/test_research_integrity_metrics.py` and failed before the implementation
change (`accepted` instead of the expected `needs_reconciliation`). The production
normalizer in `backend/app/core/research_validity.py` now applies
`minimum=-1.0, maximum=1.0` to alpha, and the focused Python slice passes `35` tests.
The JavaScript regression in
`tests/real_user_benchmark/lib/research-spine-probes.test.mjs` likewise failed before
the oracle change (`alpha_in_range=true` for `-2`); after changing
`tests/real_user_benchmark/lib/research-spine-probes.mjs` to enforce `[-1, 1]`, the
focused out-of-range pair passes and the full Research Spine/scoring package passes
`62` tests. The diagnostic now states the complete alpha domain.

The Research Spine contract and Ensemble Health living feature documentation were
updated to state the same finite `[-1, 1]` domain, explicitly retaining in-domain
negative alpha as a disagreement signal. Feature site regeneration passes with
`224` generated artifacts and `86/86` feature checks. `py_compile` and `git diff
--check` pass. Compass Forge before record `395` and after record `396` show no new
issues, forbidden dependencies, missing required paths, or import cycles; inherited
complexity, type-drift, secret-flow, and ledger-size findings remain unchanged.

This is deterministic contract hardening only. No provider request, model load,
Mac Studio workload, host installation, Docker image pull, or remote checkout
mutation occurred. The live three-served-model Research Spine, Petals, combined,
two-call/long-horizon, reconciliation, Done/report, browser, benchmark-retake,
blind-review, and CF-SPEC-2 closure gates remain open pending the owner-approved
Docker-only inputs and terminal receipts.

Next: commit and push this checkpoint, align the Build Stream YAML pointer to the
content commit, then continue the remaining live-gate and original-plan work without
turning deterministic fixtures into scientific acceptance evidence.
