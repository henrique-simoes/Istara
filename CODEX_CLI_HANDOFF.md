# Codex CLI Handoff

This file is the landing page for continuing the current Codex Desktop work in Codex CLI.

Generated from Codex Desktop on 2026-05-08 for:

- Repo: `/Users/studio/Documents/Istara-main`
- Compass Forge workspace: `/Users/studio/Documents/compass-forge`
- Compass Forge recipe: `istararustgraphtrial`
- Local session file found at: `/Users/studio/.codex/sessions/2026/05/06/rollout-2026-05-06T11-41-02-019dfdbc-3061-76c0-af01-55b55218de29.jsonl`
- Best-effort session id: `019dfdbc-3061-76c0-af01-55b55218de29`

## Start In Terminal

Preferred attempt, if Codex CLI can resume the local Desktop session:

```bash
cd /Users/studio/Documents/Istara-main
codex resume 019dfdbc-3061-76c0-af01-55b55218de29
```

If the session is not shown or cannot resume, start a fresh CLI session and ask it to read this file:

```bash
cd /Users/studio/Documents/Istara-main
codex
```

Use this prompt:

```text
Read /Users/studio/Documents/Istara-main/CODEX_CLI_HANDOFF.md and continue from that state. Use Compass Forge exactly as the repo requires before making changes. Do not expose private live LLM endpoint values. Do not load multiple heavy models.
```

CLI resume support is local-session based. There is no confirmed universal one-click migration path between Codex Desktop, CLI, and Codex Web. This file is the reliable handoff.

## Required Process

Read these first:

- `/Users/studio/Documents/Istara-main/AGENTS.md`
- `/Users/studio/Documents/Istara-main/gotchas.md`
- `/Users/studio/Documents/Istara-main/CODEX_CLI_HANDOFF.md`

Before editing:

```bash
compass-forge status
compass-forge agent-brief --request "<current user request>"
```

For meaningful changes:

```bash
compass-forge gate before
compass-forge intelligence impact --request "<current user request>"
compass-forge gate after
```

For auth, authorization, session, WebAuthn, connection string, pooled compute, MCP, webhook, LLM-provider, autoresearch, self-evolution, or agentic-memory changes:

```bash
python scripts/security_benchmark.py --fail-on-threshold
```

Respect user-owned dirty work. Do not reset or revert unrelated changes.

## Current Worktree State

The worktree is intentionally very dirty from a large, multi-day implementation and audit pass. The latest `git status --short` showed 200+ modified/untracked paths across backend, frontend, relay, scripts, tests, evals, and docs.

Important:

- Do not use `git reset --hard`.
- Do not delete ignored local artifact folders.
- `LLMs/` must never be deleted.
- `Model_Finetuning/` must never be deleted.
- Private live LLM endpoint values must stay in gitignored env files and must not be pasted into docs, logs, or final answers.
- Live LLM tests should use one fixed model only: `google/gemma-4-e4b`.
- Do not probe or autoload multiple heavy models during verification.

Compass state after the stabilization continuation:

- `compass-forge refresh`: snapshot `104`.
- `compass-forge gate after --task CF-379`: pass.
- Gate output has no route drift, type drift, contract drift, import cycles, layer violations, security issues, or complexity issues.
- The pre-existing `frontend/package-lock.json` large-file item remains covered by active Compass suppression id `5`.
- The worktree is still intentionally large and dirty; keep changes organized by review domain before committing or pushing.

## What Changed In The Long Session

Major implementation areas already completed:

- Structured LLM output handling was added through `backend/app/core/llm_schema_adapter.py`.
- Thinking controls were added through `backend/app/core/llm_thinking.py`, chat/session APIs, frontend types, and migration `backend/alembic/versions/014_chat_session_thinking_mode.py`.
- ReAct skill routing now has formal skill-tool support through `backend/app/core/agent_skill_tools.py`.
- Skill candidate ranking now uses telemetry, memento skill usage, Reasoning Bank retrieval, and optional meta-hyperagent observations.
- Skill factory paths were hardened for provider-aware schemas, thinking-marker stripping, schema budget fallback, and deterministic fallback behavior.
- Live LLM test configuration was centralized in `tests/llm_test_config.py`.
- Eval runner and live harness paths were hardened in `scripts/run_istara_evals.py`, `scripts/test_llm_integration.py`, and simulation scenario 20.
- Long-horizon benchmark no longer falls back to a checked-in admin password.
- Custom eval output paths were guarded against accidentally writing runtime artifacts into tracked space.
- Database/report reliability was improved around SQLite timeouts/WAL and avoiding long LLM calls inside held DB transactions.
- Permission request/RBAC/onboarding work was added, including `backend/app/api/routes/permission_requests.py`, `backend/app/models/permission_request.py`, and migration `backend/alembic/versions/015_permission_requests.py`.
- Large backend and frontend monoliths were split behind compatibility facades:
  - `backend/app/core/agent.py`
  - `backend/app/core/compute_registry.py`
  - `backend/app/api/routes/interfaces.py`
  - `backend/app/skills/skill_manager.py`
  - major frontend agent/chat/interview/skill components and API/type modules
- Relay LLM proxy was hardened for thinking/reasoning suppression.
- Eval strategy and harness artifacts were added under `testing/AI_EVALS_STRATEGY.md`, `tests/evals/`, and `scripts/run_istara_evals.py`.

## Verification Evidence Already Run

Known passing checks from the session:

```bash
python -m pytest tests/test_agents.py tests/test_skill_factory.py tests/test_llm_schema_adapter.py tests/test_agent_skill_tools.py tests/test_compute_registry_hardening.py tests/test_reports.py tests/test_research_integrity_reports.py tests/test_documents.py -q
```

Result: 84 passed.

```bash
python scripts/security_benchmark.py --fail-on-threshold
```

Result: passed with score 93.75%.

```bash
python scripts/check_integrity.py
python scripts/check_test_harness.py
```

Result: passed.

```bash
python scripts/test_llm_integration.py
```

Result: passed against the configured gitignored local OpenAI-compatible endpoint using `google/gemma-4-e4b`.

```bash
node --test relay/lib/llm-proxy.test.mjs
```

Result: 16 passed.

```bash
node --check tests/simulation/run.mjs
node --check tests/simulation/scenarios/20-all-skills-comprehensive.mjs
node --check tests/simulation/scenarios/26-model-session-persistence.mjs
```

Result: passed.

Live scenario 20 rerun:

- Report: `/Users/studio/Documents/Istara-main/tests/simulation/.results/runs/2026-05-08T01-09-58-635Z/report.md`
- Result: 29/29 checks passed.
- Skill subset: 5 randomly selected skills, fixed run details in the report.
- Backend process started for the live run was stopped afterward.
- A pre-existing frontend dev server on port 3000 may still be running.

Final Compass evidence before handoff:

- `compass-forge gate after`: pass, no cycles, no route drift, no type drift, no complexity issues in gate output.
- `CF-SPEC-31` accepted with evidence.
- Tasks `CF-363` through `CF-376` were marked done.

## Stabilization Completion Update

The 9-item stabilization pass was executed after this handoff was first written.

Final passing evidence:

- Backend: `python -m pytest -q` -> `726 passed, 1 skipped`.
- Frontend: `npx tsc --noEmit`, `npm run lint`, `npm run build`, and `npm run test:unit` all passed.
- Relay: `npm test` -> `17 passed`.
- Simulation: non-live matrix passed with `75` scenarios and `1073/1073` checks.
- Scenario 20: fixed-seed 5-skill run passed `29/29` checks.
- Evals: full Istara eval suite passed `11/11` using the gitignored live profile and fixed model id.
- Benchmarks: orchestration benchmark passed `4/4`.
- Security benchmark: passed with score `93.75`.
- Migrations: existing local DB and fresh temp DB both reached `015_permission_requests (head)`.
- Compass: snapshot `104`; final `gate after` pass for `CF-379`.

Final corrections from the continuation:

- Alembic migrations `007` through `015` were hardened for existing DB idempotency.
- `frontend/src/components/agents/AgentsView.tsx` was split below the Compass threshold; the new creation flow lives in `frontend/src/components/agents/CreateAgentWizard.tsx`.
- Remaining simulation harness drift was fixed for auth/bootstrap, viewport, static source paths, strong passwords, and deterministic fallback flows.
- Settings status was hardened so status checks do not trigger live model probes or multi-model loading.
- Data integrity handling is now admin-visible and non-destructive through the settings integrity report and quarantine endpoint.

Known residual notes:

- Scenario 20 is green but slow; future work should add per-skill timing/progress telemetry.
- The live eval run passed, but embedding retrieval was unavailable and fell back to keyword retrieval. Keep that visible in baseline comparisons.
- Do not delete local runtime artifact folders; use the admin-visible integrity/quarantine path for cleanup.
- The diff is large. Organize commits by domain before pushing to `main`.

## Role Clarifications From The User

Current agreed role model:

- Global admin-only features are mostly correct, but loops/schedules, autoresearch, and model/provider switching are available to researchers too.
- Project folder adding/changing is global admin and project admin only.
- Researchers can still add documents through chat attachments.
- Researchers may view compute pool but not alter it.
- Project admins can do project-admin-scoped administration.
- Researchers may create, approve, and toggle skills.
- Figma token, Stitch API, survey, and platform integrations are project admin plus global admin.
- Everyone may add LLM servers because compute donation is core to Istara.
- Loops/schedules are understood as project-bound for now.
- For project-admin actions attempted by other users, the desired future pattern is a permission request sent to project admins and global admins, with logged requester/action details in the admin menu.

## Completed Stabilization Plan

The next step was stabilization, not more feature expansion. This plan has now been executed; keep it here as the review map for the large change set.

1. Freeze scope and checkpoint.
   Stop adding new behavior until this batch is reviewed, split, and verified. Compass accepted the spec, but the worktree is huge, so the next move is a stabilization pass.

2. Split the change into reviewable domains.
   Organize the work into logical commits or review packets:
   - LLM serving, thinking controls, schema adapter
   - ReAct skill routing and learned candidate selection
   - monolith decomposition
   - eval/benchmark harness
   - scenario 20 and live LLM test harness
   - permission requests/onboarding/RBAC UX
   - report/database transaction hardening

3. Run the full regression matrix.
   Focused checks and Scenario 20 already ran, but the next pass should cover:
   - full backend pytest
   - frontend typecheck/lint/build
   - relay tests
   - all non-live simulation scenarios
   - live eval suite with the fixed local model
   - security benchmark
   - Compass refresh, gate before/after, and report

4. Migration and fresh-install audit.
   Validate new migrations on:
   - fresh DB
   - existing DB
   - rollback/downgrade if supported
   - settings/session persistence
   - permission request table creation

5. Resource manager and LLM serving audit.
   Verify:
   - no path loads multiple heavy models
   - model autoload only targets one configured model
   - RAM reporting bug in frontend/backend compute menus
   - server donation UX
   - adding LLM servers from settings
   - behavior when a user pastes a donation string but has no local LLM server installed

6. Data integrity cleanup plan.
   The live run surfaced local data warnings: orphan LanceDB/index/upload dirs and invalid PDFs. Do not silently delete them. Build or run a safe admin-visible cleanup/report flow.

7. Eval baseline hardening.
   The eval framework exists now, but the next pass should make it a reliable baseline system:
   - versioned manifests per run
   - comparison report against previous run
   - core evals for RAG, prompt RAG, LLMLingua, DAG ReAct, memory, reasoning bank, memento skills, meta-hyperagents
   - clear pass/fail thresholds
   - Compass evidence integration

8. Role and onboarding acceptance pass.
   Walk admin, project admin, and researcher flows end-to-end:
   - menus visible/hidden correctly
   - permission request UX works
   - researcher can use autoresearch and skill creation/approval/toggle as intended
   - compute pool is view-only for researchers
   - admin tour teaches model/server setup, invites, projects, permissions, autoresearch, schedules, skills, compute

9. Code quality cleanup after verification.
   Only after the above: reduce frontend warnings, inspect remaining complexity hotspots, and check that the monolith split did not create thin files with unclear boundaries.

Suggested CLI prompt after reading this file:

```text
Use Compass Forge to inspect the current diff and help organize the verified Istara stabilization change set into reviewable commits for a careful main push. Do not add new features. Do not expose private live LLM endpoint values.
```
