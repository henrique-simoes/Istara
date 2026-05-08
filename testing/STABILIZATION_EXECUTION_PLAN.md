# Istara Stabilization Execution Plan

Date: 2026-05-08
Compass spec: `CF-SPEC-32`
Scope: stabilize the current large active diff, update tests only where they no longer reflect backend behavior, run a complete verification/eval pass, correct verified failures, and prepare `main` for a careful remote push.

## Deliverables

1. Durable Compass Forge execution record for the stabilization work.
2. Reviewed plan covering all 9 stabilization items and every subitem.
3. Current Compass map/gate evidence, or an explicit blocker if Compass state writes are unavailable.
4. Review packets or commit-ready domains for the current diff.
5. Full regression/eval/security evidence with pass/fail results and failure analysis.
6. Test harness updates where verification proves drift from backend behavior.
7. Targeted corrections for verified failures.
8. Completion audit mapping every explicit user requirement to concrete evidence.
9. Main-branch preparation for careful push after audit.

## Non-Goals

- Do not add unrelated product features.
- Do not delete `LLMs/` or `Model_Finetuning/`.
- Do not expose private live LLM endpoint values.
- Do not probe or autoload multiple heavy models.
- Do not silently delete local data warnings such as orphan indexes/uploads or invalid PDFs.

## Execution Plan

### 1. Freeze Scope And Checkpoint

Success criteria:
- No new product behavior is introduced unless required to fix a verified regression or test harness drift.
- Current worktree is captured through `git status --short`.
- Compass spec and baseline gate exist.

Evidence:
- `compass-forge status`
- `compass-forge agent-brief`
- `compass-forge gate before`
- `git status --short`

### 2. Split The Change Into Reviewable Domains

Domains:
- LLM serving, thinking controls, schema adapter
- ReAct skill routing and learned candidate selection
- monolith decomposition
- eval/benchmark harness
- scenario 20 and live LLM test harness
- permission requests/onboarding/RBAC UX
- report/database transaction hardening

Success criteria:
- Each domain has a file list, verification commands, and risk notes.
- Domain split is suitable for staged review or commit planning.

### 3. Run The Full Regression Matrix

Required checks:
- full backend pytest
- frontend typecheck/lint/build
- relay tests
- all non-live simulation scenarios
- live eval suite with the fixed local model
- security benchmark
- Compass refresh, gate before/after, and report

Success criteria:
- Every check has a command, result, and artifact path when applicable.
- Failures are classified as product bug, test harness drift, environment issue, or known local-data issue.

### 4. Migration And Fresh-Install Audit

Validate:
- fresh DB
- existing DB
- rollback/downgrade if supported
- settings/session persistence
- permission request table creation

Success criteria:
- New migrations `014_chat_session_thinking_mode.py` and `015_permission_requests.py` apply cleanly.
- Existing DB upgrade path is verified or blockers are documented with exact error output.

### 5. Resource Manager And LLM Serving Audit

Verify:
- no path loads multiple heavy models
- model autoload only targets one configured model
- RAM reporting bug in frontend/backend compute menus
- server donation UX
- adding LLM servers from settings
- behavior when a user pastes a donation string but has no local LLM server installed

Success criteria:
- Code paths for model discovery/autoload are inspected and covered by tests where feasible.
- RAM reporting source of truth is traced from backend to frontend display.
- Any verified defect has either a fix or a documented blocker.

### 6. Data Integrity Cleanup Plan

Validate warnings:
- orphan LanceDB/index/upload dirs
- invalid uploaded PDFs

Success criteria:
- No silent deletion.
- Admin-visible cleanup/report flow is either verified existing behavior or proposed as a follow-up with concrete path references.

### 7. Eval Baseline Hardening

Verify:
- versioned manifests per run
- comparison report against previous run
- core evals for RAG, prompt RAG, LLMLingua, DAG ReAct, memory, reasoning bank, memento skills, meta-hyperagents
- clear pass/fail thresholds
- Compass evidence integration

Success criteria:
- Eval runner can produce repeatable, versioned artifacts.
- Baseline comparison behavior is tested.

### 8. Role And Onboarding Acceptance Pass

Walk flows for:
- global admin
- project admin
- researcher

Verify:
- menus visible/hidden correctly
- permission request UX works
- researcher can use autoresearch and skill creation/approval/toggle
- compute pool is view-only for researchers
- admin tour teaches model/server setup, invites, projects, permissions, autoresearch, schedules, skills, compute

Success criteria:
- Role matrix is matched against current code.
- UI/API test coverage exists or is updated where behavior changed.

### 9. Code Quality Cleanup After Verification

Verify:
- frontend warnings
- remaining complexity hotspots
- monolith split boundaries
- thin files do not obscure ownership or create unclear facades

Success criteria:
- Compass gate shows no new route/type/complexity drift.
- Remaining warnings are either fixed or documented with reason and path.

## Plan Review Verdict

The plan is executable with two important constraints:

1. Compass Forge refresh/spec/task operations write to Compass state outside the repo workspace. In a sandboxed run, they require approval.
2. Live LLM and simulation commands must use the existing gitignored single-model profile and must not trigger broad model probing.

The plan should proceed in this order:

1. Finish Compass spec clarification, planning, and tasks for `CF-SPEC-32`.
2. Run baseline verification to discover actual failures.
3. Correct only verified failures or harness drift.
4. Re-run affected checks.
5. Run completion audit before accepting the spec or preparing push.

## Completion Audit Checklist

| Requirement | Evidence Required | Status |
| --- | --- | --- |
| Create a plan | This file plus `CF-SPEC-32` plan output | Pending Compass plan |
| Review the plan using Compass and local process | Compass spec quality plus this Plan Review Verdict | Pending Compass plan |
| Execute every 9-item section | Task evidence for each item | Pending |
| Update tests when code/test meaning diverges | Test diffs and targeted runs | Pending |
| Run new round of tests after corrections | Regression/eval/security results | Pending |
| Analyze what went right/wrong | Stabilization report | Pending |
| Perform corrections if needed | Diffs plus reruns | Pending |
| Prepare main for careful remote push | Clean audit, staged/committed state, remote status | Pending |
| Follow Compass Forge thoroughly | Spec/tasks/gates/evidence/acceptance | Pending |
