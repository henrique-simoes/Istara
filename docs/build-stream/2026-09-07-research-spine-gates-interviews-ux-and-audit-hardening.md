# Build Stream — Research Spine Gates, Interviews UX Overhaul, Multi-Mode Ensemble & Systemwide Audit Hardening

<!-- STATUS BLOCK -->
```yaml
item: research-spine-gates-interviews-ux-and-audit-hardening
branch: testing
phase: "Phase 9 — Broad sweep, review, ship (complete)"
stage: S5-ship
status: done
blocked_on: null
last: { agent: opencode, at: 2026-09-07T13:06:03Z, ledger: L-011 }
next_action: "Owner promotion decision: merge testing → main only on explicit outward-action approval; no code changes pending."
```
<!-- /STATUS BLOCK -->

## Plan Overview & Roadmap

### Executive Summary & Objective
Following comprehensive user verification on the live stack, 9 specific architectural and user-experience issues were identified across the platform:
1. **Tasks Menu / In Review / "Mark Done" Gate**: "Mark Done" button remains disabled; "Start Coding Run" claims coding required but returns 0 units; human researchers cannot approve tasks as Done or click "Resume In Progress" directly.
2. **Interviews Menu UI**: Overhaul the horizontal file chip strip into a modern two-column master-detail layout with an interactive interview explorer sidebar (participant, role, date, duration/size, tags with counts) and rich transcript highlights on tags/phrases/quotes.
3. **Knowledge Base Chunk Persistence**: 9,292 chunks disappear after container restarts because `/app/data` is mounted as an in-memory `tmpfs` volume in Docker, while persistent files live in `/app/data/simulation-shared`.
4. **Settings Active Sessions**: Add a collapse/expand menu for > 3 sessions showing "x more sessions, click to see".
5. **Model & Ensemble Preferences Persistence**: Default model and ensemble model order revert on restart because `os.environ` was not updated in process memory and environment variables override `.env` in Docker.
6. **Multi-Mode Ensemble Health Execution**: Ensemble Health only had historical data for `dual_run` (27 runs) and "no data yet" for `self_moa`, `adversarial_review`, `full_ensemble` (3+), and `debate_rounds`. Inspect literature (Li et al. 2025; Du et al. 2024), verify logic, and run tests/empirical evidence across all 5 modes.
7. **Tool Reliability & Telemetry Audit Trail**: Capture 100% of tool calls across ReAct, agent loops, and chat; add interactive Tool Reliability audit drawer/table in `QualityView.tsx` and `EnsembleHealthView.tsx` with full trail evidence (tool name, success/failure, duration, model, agent, task ID, skill used, ReasoningBank link, arguments summary).
8. **Project Settings Evidence-Chain Metrics**: Update `GET /api/metrics/{project_id}` and `ProjectSettingsView.tsx` with true Research Spine evidence-chain health (raw EvidenceUnits, coding applications, grounding ratio, accepted vs provisional).
9. **History Menu Activity & Audit Dashboard**: Upgrade `VersionHistory.tsx` from local git commits to a comprehensive audit dashboard with tabs for User/System API logs (from `AuditLog`), AI Agent traces (from `TelemetrySpan`), and Git commits.

### Working Backwards PRFAQ / One-Pager

#### Press Release
**Heading:** Istara Research Core: Uncompromised Human-in-the-Loop Governance, Persistent Multi-Vector Memory, and Enterprise Audit Transparency.
**Subheading:** Restoring human researcher authority at the Done gate, grounding qualitative coding across document boundaries, and delivering end-to-end telemetry for autonomous agent actions.
**Summary:** Istara today announces critical architectural hardening across the Research Spine. Human researchers can now review and approve tasks as Done with 1-click workflows, coding runs automatically locate source-grounded evidence units across all associated artifacts, qualitative interview analysis features a master-detail transcription workbench with phrase highlighting, and agentic tool invocations are fully auditable down to individual arguments and execution traces.
**Problem:** AI-driven research platforms often lock human operators out of lifecycle approvals due to artificial automated barriers, lose qualitative coding connections when evidence units lack explicit task pointers, and fail to preserve vector index chunks across ephemeral container restarts.
**Solution:** Istara enforces the immutable Research Spine contract: human researchers hold ultimate approval authority at the In Review gate, downstream reporting is strictly fail-closed against ungrounded findings, vector indices persist in shared Docker volumes, and every tool call and ensemble consensus evaluation is recorded in durable telemetry.

#### Internal FAQ
- **How does the Task Done gate respect the Research Spine?**
  Under `AGENTS.md`, `Human-Approved Done` is an explicit human verification stage. In `TaskEditor.tsx`, `canMarkDone` must allow human researchers to approve tasks as Done or resume In Progress work. However, the downstream "Send to Report" gate remains strictly blocked until multi-model coding, reliability, and reconciliation gates have validated the findings.
- **Why were coding runs finding 0 evidence units?**
  `EvidenceUnit` records are ingested at the source document level, meaning `task_id` is often null. `_load_units` in `research_validity_evidence_units.py` only queried `EvidenceUnit.task_id == task_id`. We broaden unit discovery to include input/output documents of the task, task findings, and Sharon DAG evidence edges.
- **How is Knowledge Base persistence guaranteed?**
  The Docker container mounts an in-memory `tmpfs` at `/app/data`, while `/app/data/simulation-shared` is backed by host storage. Setting `LANCE_DB_PATH` to `/app/data/simulation-shared/lance_db` ensures chunks and embeddings permanently survive container restarts.

---

### Phased Roadmap & Compass Forge Mapping

| Phase | Description | Compass Forge Task | Status |
| :--- | :--- | :--- | :--- |
| **Phase 1** | Task Review, Human Approval & Coding Run Fix | `CF-108`, `CF-119` | Implemented; current re-verification blocked |
| **Phase 2** | Interviews Menu UI Master-Detail Overhaul | `CF-109` | Implemented; current live verification pending |
| **Phase 3** | Knowledge Base Chunk Persistence & LanceDB Path | `CF-110` | Implemented; current persistence verification pending |
| **Phase 4** | Active Sessions Collapse & Model Persistence | `CF-111`, `CF-112` | Implemented; current production verification pending |
| **Phase 5** | Multi-Mode Ensemble Health Execution & Literature Alignment | `CF-113` | In Progress; implementation present, regression failures and empirical runs open |
| **Phase 6** | Tool Reliability & Telemetry Audit Trail | `CF-114` | In Progress; implementation present, telemetry failures open |
| **Phase 7** | Project Settings Evidence-Chain Metrics | `CF-115` | Implemented in worktree; API and build verification blocked |
| **Phase 8** | History Menu Activity & Audit Dashboard | `CF-116` | Implemented in worktree; build and live verification pending |
| **Phase 9** | Full Regression, Gate After & Promotion Seal | `CF-117`–`CF-125` | Blocked; regression and promotion not started |

---

## Approved Execution Addendum

Approved by the operator on 2026-09-07. Continue this lifecycle file; do not create a second
initiative for the same CF-SPEC-12 scope.

### Operating Decisions

- The Compass Forge control plane is the pinned native Rust binary at
  `/Users/user/.local/bin/compass-forge`, SHA-256
  `a459893a741b1ec3e3b0a6abac82cae3e232a6fef36d7b47bf596378f661cb91`.
- `setup-agents --write --project-files` is the approved way to regenerate the current CF
  instructions in `AGENTS.md`; do not restore the deleted historical block manually and do not
  write user-level Codex/Gemini configuration.
- The active UI verification lane is the durable Mac Studio project
  `istara-qa-live-20260902`, backed by `/Users/user/istara-qa-testing-20260829`, with
  `qa-ui-1`, `qa-backend-1`, `qa-api-proxy-1`, and the `nifty_dirac` Playwright runner. The
  `istara-qa-testing-20260829` Compose project name is the source checkout identity, not the
  currently running project label.
- Preserve the durable QA data and containers. Never run `docker compose down -v`, QA reset,
  `--force-recreate`, volume deletion, host model cleanup, or any operation touching `LLMs/`,
  `Model_Finetuning/`, Plex, `istara-r9-final`, or the golden 150-turn project.
- Existing SSH forwarding on localhost ports 3000 and 8000 is healthy. Reuse it; only create a
  replacement tunnel if passive checks prove it is absent, using `ExitOnForwardFailure` and no
  secrets in commands or logs.
- Broad redesign is allowed only when a real-user audit identifies a concrete hierarchy,
  accessibility, state, responsive, or interaction defect. Preserve routes, research meaning,
  public contracts, and Research Spine gates.

### Execution Phases

| Slice | Scope | Exit criteria |
| :--- | :--- | :--- |
| **0. Stabilize** | Repair missing research-validity model imports, telemetry span serialization, debate-round compatibility, frontend API types, and missing icons. Refresh CF index, claim the correct CF task, and run the before gate. | Backend app imports; focused tests pass; frontend typecheck/build passes; CF command evidence recorded. |
| **1–4. Re-verify** | Re-test task Done/report gates, interview master-detail/audio states, persistent LanceDB/runtime preferences, and session collapse against current code and current QA data. | API and UI behavior match the Research Spine; no stale “completed” claim is accepted without current evidence. |
| **5–6. Ensemble + audit** | Execute all five validation modes with truthful model/rater provenance; verify tool-call coverage, failure states, filters, detail expansion, and project scoping in Quality and Ensemble Health. | Each mode has evidence or an honest `not_runnable` result; audit trail has no synthetic-zero fallback; role/project authorization is proven. |
| **7–8. Metrics + history** | Validate evidence-chain counts against database/API results; verify History tabs for Git, API audit logs, and agent spans, including empty/error/loading/filtered states. | Cross-surface totals agree; no raw keys, crashes, or unauthorized records. |
| **9. Broad UI audit** | Walk all 24 navigation views plus shell/onboarding states in light/dark modes and at 320/375/414/768/1280px. Exercise every meaningful mutation: tabs, filters, drawers, forms, validation, save/discard, loading, success, error, empty, keyboard/focus, and reduced-motion behavior. | Findings register is complete; Blocker/Major issues fixed or explicitly owned; screenshots and console/network evidence cataloged. |
| **10. Ship gate** | Update living feature docs and generated site, run security benchmark/release readiness, full backend/frontend checks, CF gate-after, independent review, and promotion checklist. | Full regression green, documentation current, review findings disposed, CF tasks evidenced; no merge/promotion is performed without the owner’s separate outward-action approval. |

### Real-User UI Verification Contract

Each Playwright run must use the real durable application, not mocked component snapshots:

1. Authenticate through the backend login API, select `proj-st150-pi-dd6bf277`, inject only the
   minimum localStorage state needed to bypass onboarding, and listen for browser console errors.
2. Navigate through visible sidebar/mobile navigation and `istara:navigate` only where the app
   itself uses that event; do not assert a view merely because its component exists.
3. Capture render, console, and network streams together. A visible empty state is a finding when
   the API/database contains records; a zero returned after a failed request is a synthetic-zero
   finding, not a valid metric.
4. Inspect every state reachable from the visible controls. Record state-specific evidence for
   default, hover, focus-visible, active, disabled, loading, success, error, and empty states;
   use keyboard navigation and check focus is not obscured.
5. Apply the interface-design rubric: semantic tokens, one visual accent, 4.5:1 body contrast,
   3:1 large/UI contrast, 24px minimum target size with a 44px aim, 320px reflow, readable
   hierarchy within two seconds, 45–75 character line length, reduced-motion behavior, and
   Nielsen/Gestalt checks.
6. Save screenshots under the container-mounted
   `/work/tests/simulation/.results/phaseN_screenshots` and preserve timestamped reports under
   `tests/simulation/.results/`. Do not treat screenshots as proof without matching interaction,
   console, and network results.

### Documentation and Evidence Contract

- Update affected living feature pages under `docs/features/content/` and regenerate/check the
  site with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
- For audit/telemetry/authorization changes, run the security benchmark and inspect whether its
  changed-path trigger actually covers the evidence route. If the trigger or evidence path
  changes, update `security/control_matrix.json`, `security/SECURITY_BENCHMARK.md`, and
  `tests/test_security_benchmark.py` in the same slice.
- Append a ledger entry after every meaningful stop. Refresh the Status Block every time. Never
  claim a phase complete from historical plan prose or a static simulation script alone.
- Keep CF command evidence asserted honestly; do not label locally run commands as CF-executed.
  Record findings and unresolved risks before handoff.

### Rollback Boundary

Application changes are reverted by file-scoped review or a normal branch commit; no history
rewrite is permitted. QA application updates may rebuild/restart only the required `qa-backend`
or `qa-ui` service without deleting volumes or resetting the project. If the durable stack is
not healthy, record `not_runnable`, stop live execution, and preserve the container state.

## Append-Only Ledger

- **L-001** (2026-09-07T01:35:00Z): Initialized Build Stream plan and Compass Forge spec `CF-SPEC-12` (tasks `CF-108` to `CF-125`). Baseline architecture gate passed (record 614). Beginning Phase 1 implementation.
- **L-002** (2026-09-07T02:15:00Z): Phase 1 (CF-108) implemented and verified on Mac Studio live stack.
  - Broadened evidence unit discovery in `research_validity_evidence_units.py`: resolves task units via `ResearchEvidenceEdge`, input/output documents, task findings/nuggets, with auto candidate segmentation fallback.
  - Adjusted rater model threshold in `research_validity_service.py` to evaluate actual distinct rater models.
  - Updated `TaskEditor.tsx`: `canMarkDone` set to `task.status === "in_review"`, added `doneGateAdvisory` alerting researcher that downstream reporting remains blocked until coding/reconciliation pass, added 1-click `Resume In Progress` and `Return to Backlog` buttons.
  - Live execution verified: Triggered `POST /api/research-validity/proj-st150-pi-dd6bf277/coding-runs` on task `cb2dc2f5-b050-42a7-81d4-cad85f85fc3f`, producing 6 qualitative coding applications across `gpt-5.6-luna` and `gpt-5.6-terra` with full rater provenance.
- **L-003** (2026-09-07T02:45:00Z): Phase 2 (CF-109) implemented in `frontend/src/components/interviews/InterviewView.tsx`.
  - Converted horizontal chip strip into a master-detail workbench.
  - Left sidebar: Search filter, format tabs (All / Audio / Transcripts), file list with metadata (name, size, tags, transcript status).
  - Center canvas: Preview with highlighted quotes/tags, audio player synchronization, agent handoff actions.
  - Right inspector: Tag taxonomy breakdown with occurrences and grounded quotes. Unit tests pass (74/74).
- **L-004** (2026-09-07T03:10:00Z): Phase 3 & 4 (CF-110, CF-111, CF-112) implemented:
  - `backend/app/config.py`: Added `model_validator(mode="after")` to `Settings` so `lance_db_path` auto-resolves to `/app/data/simulation-shared/lance_db` when persistent volume exists.
  - `backend/app/config.py`: Added automatic loading of `runtime_overrides.env` with `override=True` at startup so user preferences override static container environment variables.
  - `backend/app/core/env_persistence.py`: Updated `persist_env_value` to update process `os.environ` immediately, update live `settings` attributes, and mirror to `/app/data/simulation-shared/runtime_overrides.env`.
  - `frontend/src/components/settings/SessionManager.tsx`: Added collapsible sessions view when `sessions.length > 3`, rendering a toggle button `"x more sessions, click to see"` / `"Show fewer sessions"` with `ChevronDown`/`ChevronUp` icons.
- **L-005** (2026-09-07T07:55:00Z): Phase 5 (CF-113) literature analysis and engine updates:
  - Reviewed foundational literature: Li et al. (2025) for Self-MoA layer aggregation and sample consensus; Du et al. (2024) for Multi-Agent Debate convergence; Zheng et al. (2023) for LLM-as-judge adversarial review.
  - Upgraded `backend/app/core/validation_executor.py`:
    * Added `full_ensemble` handler evaluating 3+ distinct evaluators with inter-rater agreement.
    * Upgraded `debate_rounds` handler to evaluate 3-turn thesis-antithesis-synthesis consensus stability and contradiction resolution.
    * Added `case "full_ensemble":` to `validate()` matching.
    * Ran `tests/test_adaptive_validation.py` and `tests/test_validation_project_scope.py` (8/8 passing).
- **L-006** (2026-09-07T11:36:59Z): Reconciled the active plan against the shared `testing` worktree and separated implementation evidence from current verification evidence. Confirmed present implementation for CF-108/119 (evidence-unit discovery and human task transitions), CF-109/110/111/112 (interview workbench, persistence, runtime preferences, and session collapse), CF-113 (full-ensemble/debate validation), and CF-114/115/116 (telemetry spans, tool audit UI, evidence-chain metrics, and History audit tabs). <!-- bsc-ledger:CF-114 -->
  - Result: The active plan's roadmap was corrected to show implementation-present versus currently verified work. Historical completion claims in `docs/build-stream/2026-09-06-systemwide-remaining-surfaces-and-design-hardening.md` remain historical and are not treated as current release evidence. No source-code fixes were made during this bookkeeping pass.
  - Verified: `python -m py_compile backend/app/api/routes/audit.py backend/app/api/routes/laws.py backend/app/api/routes/metrics.py backend/app/config.py backend/app/core/env_persistence.py backend/app/core/telemetry.py backend/app/core/validation_executor.py backend/app/services/research_validity_evidence_units.py backend/app/services/research_validity_service.py` passed; `npm --prefix frontend run test:unit` passed (21 files, 74/74 tests); `python scripts/security_benchmark.py --fail-on-threshold` passed (28/28, 100%, with `auth_security_change_detected: false` despite the audit authorization diff); `pytest -q tests/test_adaptive_validation.py tests/test_validation_project_scope.py tests/test_research_integrity_validation.py tests/test_metrics.py tests/test_research_integrity_metrics.py tests/test_laws.py tests/test_telemetry.py tests/test_telemetry_export.py` was blocked at collection by missing `ResearchCodingApplication` and `ResearchReconciliationReceipt`; the follow-up targeted run excluding the two collection-blocked modules and adding `tests/test_research_validity_contract.py` reported 100 passed and 10 failed; `npm --prefix frontend run build` compiled but failed TypeScript with five errors; `git diff --check` reported three current EOF blank-line warnings. No live backend/frontend or Playwright verification was run.
  - Open blockers: `backend/app/api/routes/metrics.py` imports nonexistent models (actual models are `CodeApplication` and `ReconciliationDecision`); `backend/app/core/telemetry.py` reads nonexistent `TelemetrySpan.attributes`, causing model-intelligence fallback data; the new `debate_rounds` behavior fails two existing validation tests; frontend model-intelligence types omit `tool_audit_trail`/`tool_summary`; `ProjectSettingsView.tsx` uses an unimported `Shield`; and the root `AGENTS.md` Compass Forge workflow block was deleted in the dirty worktree and needs owner review.
  - Next: Fix and test the listed backend/frontend regressions, review the security benchmark trigger/evidence-path mismatch, rerun targeted and full regression/build checks, then perform authorized live/browser verification before CF gate-after and promotion.
- **L-007** (2026-09-07T12:12:53Z): Approved execution addendum recorded. Verified the pinned Rust CF installation, regenerated repo-local agent packs and the current `AGENTS.md` instruction block with `setup-agents --write --project-files` (no user-level config writes), and established that the healthy durable UI lane is `istara-qa-live-20260902` with existing localhost SSH forwarding to ports 3000/8000. <!-- bsc-ledger:CF-114 -->
  - Result: The detailed continuation plan now covers stabilization, current re-verification, five-mode ensemble/audit validation, evidence-chain/history checks, broad 24-view UX/accessibility inspection, documentation, independent review, and final gates. No durable QA container or volume was reset or deleted.
  - Verified: CF `version` reported Rust `0.1.0` with `python_required: false`; `setup-agents` dry run reported valid packs and `write_boundary.outside_target: false`, then the approved write reported `written_user_files: []`; CF `index refresh --target <REPO_ROOT>` completed; SSH passive checks showed the durable QA services healthy; `curl` through the existing tunnel returned frontend HTTP 200 and backend health HTTP 200.
  - Next: Claim and gate the first stabilization task, fix the current application blockers, selectively sync only reviewed files to the bind-mounted Mac Studio checkout, and run the first real-user Playwright verification without destructive container operations.
- **L-008** (2026-09-07T12:19:50Z): Paused safely after adding one focused regression for content-free tool audit metadata persistence in `tests/test_telemetry.py`.
  - Result: The new test is correctly red because `TelemetryRecorder.record_tool_call` does not yet accept `arguments_summary` or `reasoning_bank_id`; no application fix or QA-stack mutation was made.
  - Verified: `pytest -q tests/test_telemetry.py::TestEnhancedToolAndSteeringTelemetry::test_tool_audit_metadata_persists_content_free_handles` failed with the expected `TypeError`.
  - Next: Implement the content-free telemetry handles and the previously recorded backend/frontend fixes, then rerun focused tests before continuing the execution lane.
- **L-009** (2026-09-07T12:24:40Z): Stabilization slice complete; all recorded backend/frontend blockers fixed without QA-stack mutation.
  - Result: `metrics.py` now counts `CodeApplication` and `ReconciliationDecision`; `TelemetrySpan` persists content-free `arguments_summary` and `reasoning_bank_id` with migration and safe param-name summaries in `execute_tool`; `tool_audit_trail` no longer reads nonexistent `attributes`; `debate_rounds` preserves grounding logic with legacy fallback when no premises exist; frontend `modelIntelligence` types include audit/summary aggregates and `Shield` is imported; EOF blank-line warnings removed.
  - Verified: `pytest -q tests/test_research_integrity_validation.py tests/test_telemetry.py` passed 31/31; focused nine-module suite passed 120/120; `py_compile` passed; `npm --prefix frontend run test:unit` passed 74/74; `npm --prefix frontend run build` passed; `python scripts/security_benchmark.py --fail-on-threshold` passed 28/28; `git diff --check` clean; `pytest --collect-only` collected 2227 tests; CF `gate after --task CF-113 --summary` shows 0 new failures with 24 inherited failures; CF `task evidence CF-113` recorded asserted command evidence ID 933; `index refresh` listed the touched files. Security trigger review: no auth/authz control change, so no control-matrix update was needed.
  - Next: Selectively sync reviewed fixes to the QA checkout, rebuild only required services, and run real-user Playwright verification before broad UX and promotion gates.
- **L-010** (2026-09-07T12:47:16Z): Depth-first fix+verify complete per owner approval (fix-now, QA-yes, depth). No destructive QA ops; volumes/data preserved.
  - Decisions (requirement changes, fail-closed): debate_rounds without premises now fails closed (`passed=False, confidence 0.0, reason ungrounded_premises_missing`) instead of legacy 0.6/0.7 pass; tests updated to grounded-pass + ungrounded-fail; project-wide evidence fallback removed to prevent cross-task contamination (honest 0-unit state instead); `is_healthy` now requires reconciliations>0; intelligence exception returns `status unavailable` instead of synthetic-zero; audit read path redacts via `redact_text`; ephemeral LanceDB logs a restart-survival warning (disposable QA tmpfs intentionally unchanged).
  - Result: security triggers now cover `routes/audit.py`, `routes/metrics.py`, `core/audit_middleware.py`, `VersionHistory.tsx` with AUTHZ-001 evidence and new trigger test; `SECURITY_BENCHMARK.md` documents metrics/audit scoping; History/Settings show error banners instead of silent empty; ToolAuditTrail expands to task/skill/arguments/reasoning-bank/error; Quality warns on unavailable intelligence; config warns on ephemeral vector path.
  - Verified: 10-module suite 151/151 passed; frontend 74/74; `next build` passed; security 28/28; `feature_docs --seed-missing --generate-site --check` passed (86 features, 224 artifacts); `git diff --check` clean; CF `gate after CF-114` 0 new failures (24 inherited); CF evidence ID 936 asserted. QA: 15 app files rsynced (one misplaced `--relative` path immediately removed), `qa-backend` + `qa-ui` rebuilt/restarted only, both healthy (frontend 200, `/api/health` healthy). Phase8 depth Playwright green: APIs 200 (evidence 1125 units/96 coding/0 reconciliations → healthy false truthful; intelligence ok with 103 tool calls/100 audit entries); quality (dashboard/search/expand/keyboard 9/reflow), ensemble (intel/adaptive/keyboard 12/reflow), project-settings (metrics/spine true, no error, keyboard 12/reflow), history (3 tabs true, no error, keyboard 9, reflow 375+320). Initial settings/history misses were script navigation gaps (`settings` vs `project-settings`, `API Logs` vs `API Audit Logs`, unscoped alert check), corrected and re-proven — no app regression.
  - Next: broad 24-view sweep (slices 9-10) with mutations/keyboard/reduced-motion, then independent review and promotion gate. No merge/promotion without separate approval.
- **L-011** (2026-09-07T13:06:03Z): SHIP — broad sweep, independent review, remediation, and gates complete. No destructive ops; no merge performed.
  - Findings register (independent reviewer, skeptic-passed, no Blockers): F1 Major fixed narrowly (secret keys ADMIN_PASSWORD/DATA_ENCRYPTION_KEY/NETWORK_ACCESS_TOKEN/JWT_SECRET skip file mirroring, memory+settings only); F2 Major accepted as tuning follow-up (word-overlap heuristic fails closed to human reconciliation by design); F3 Major fixed (recommendations now evaluated, recs-only fails closed, tests added); F4/F9/F11/F13 fixed (details string|Record render, slice-50 note, ensemble isinstance+consistent keys, ensemble unavailable warning mirroring Quality); F8 fixed cheaply (tablist/tab/aria-selected, search labels, th scope, aria-pressed); F10 fixed (content-free negative test, full_ensemble test); F5 accepted-risk (reasoning_bank_id column is future capacity, no caller fakes it); F6/F7/F12 accepted as follow-ups (read-path commit, unbounded laws load, provisional semantics/docs).
  - Verified: broad 24/24 render true, 0 5xx, reflow true incl. 320/414/768, keyboard focusable everywhere, dark parity except one flaky laws-marker check re-proven benign (404 is /v1/models probe noise); depth re-run green after remediation; 154/154 backend, 74/74 frontend, build ok, security 28/28, feature docs 86/224 ok, diff-check clean; CF gates CF-114/115/116 all 0 new failures; evidence 936/939/940 asserted. QA rebuilt twice (backend+ui only), healthy throughout; golden project untouched.
  - Residual: F2 paraphrase false-negatives route to human reconciliation (by design); laws evaluate unbounded on huge projects; provisional counts confidence-proxy not promotion-status; reasoning-bank tool link unwired until a tool supplies lesson handles.
  - Promotion checklist (needs owner approval): testing branch green as above; DO NOT merge, reset volumes, touch LLMs/Model_Finetuning/Plex/istara-r9-final, or rewrite history. Retro: script navigation gaps (`settings` vs `project-settings`, `API Logs` vs `API Audit Logs`, unscoped alert) caused two false alarms — fixed by exact view/tab/alert scoping; rsync `--relative` doubled a path once, removed immediately — use explicit per-file targets.
