---
stable_id: tasks.review
title: Human Task Review
ui_path: Tasks > Review
audience: architecture
status: documented
related_features: ["findings.review", "agents.proposals"]
related_glossary: ["triangulation"]
code_references: ["frontend/src/components/kanban/KanbanBoard.tsx", "frontend/src/components/kanban/TaskEditor.tsx", "backend/app/core/task_review.py"]
api_references: ["backend/app/api/routes/tasks.py"]
test_references: ["tests/test_tasks.py", "tests/real_user_benchmark/run.mjs"]
last_verified: 2026-05-21
compass: CF-SPEC-53 / CF-657; CF-SPEC-73 / CF-941; CF-SPEC-121; CF-SPEC-122
---

# Human Task Review Architecture

## Implementation Summary

Review actions support approving, requesting revision, or otherwise resolving human-in-the-loop task work. The real-user benchmark treats review as a collaborative researcher workflow: one researcher creates or revises work, another researcher reads the output and either sends it back with concrete instructions or approves it for reporting.

## Frontend Surface

- `frontend/src/components/kanban/KanbanBoard.tsx`
- `frontend/src/components/kanban/TaskEditor.tsx`
- `backend/app/core/task_review.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/taskStore.ts`

### API And Backend

- `backend/app/api/routes/tasks.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/kanban/KanbanBoard.tsx` and the UI navigation path recorded in the inventory.
- Human review routes are active-project-bound: approval, revision, review-event reads, and legacy verification require `project_id` and resolve the task inside that project before any transition or side effect runs.
- The Task Editor passes the active project id for approval and revision calls, so a task selected from a previous project cannot be approved or reopened in the current project view.
- The real-user benchmark must not use the admin API as a substitute for normal researcher task work. Admin may set up users and project access, but collaborative task creation, revision requests, and approval evidence should be produced by authenticated researcher actors when the product contract allows it.
- Benchmark reviewer actors reject outputs that are explicitly blocked, missing required source data, low confidence because data is unavailable, or synthetic for a source-backed task. Those outputs receive revision instructions instead of being counted as done.
- Approval is the reporting boundary. When review moves a task to Done and `approved`, review side effects route that task's atomic findings into the report manager; revision and In Review states keep the findings visible for evaluation but outside Reports.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- No direct agent, skill, LLM, or MCP behavior is asserted beyond the cited source files.

## Tests And Verification

- `tests/test_tasks.py`
- `tests/real_user_benchmark/run.mjs`

## Related Features

- [findings.review](../../findings/review/architecture.md)
- [agents.proposals](../../agents/proposals/architecture.md)

## Related Concepts

- [triangulation](../../../glossary/triangulation.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657; CF-SPEC-73 / CF-941; CF-SPEC-121; CF-SPEC-122
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
