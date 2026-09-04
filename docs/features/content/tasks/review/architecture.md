---
stable_id: tasks.review
title: Human Task Review
ui_path: Tasks > Review
audience: architecture
status: documented
related_features: ["findings.review", "agents.proposals"]
related_glossary: ["triangulation"]
code_references: ["frontend/src/components/kanban/KanbanBoard.tsx", "frontend/src/components/kanban/TaskEditor.tsx", "backend/app/api/routes/tasks.py", "backend/app/core/task_review.py", "backend/app/services/research_validity_service.py"]
api_references: ["backend/app/api/routes/tasks.py"]
test_references: ["tests/test_tasks.py", "tests/real_user_benchmark/run.mjs"]
last_verified: 2026-08-31
compass: CF-SPEC-53 / CF-657; CF-SPEC-73 / CF-941; CF-SPEC-121; CF-SPEC-122; CF-SPEC-123 / CF-1581; Research Spine item-level report gate batch
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
- Revision controls make the destination a separate, labeled choice (`Return to Backlog` or `Resume In Progress`) and expose `Request Revision` as the state-changing action. Choosing a destination alone never implies that a transition has occurred.
- Review mutations save the editor state before acting and release the task edit lock before closing, preventing worker execution from racing with changed feedback, method, or source attachments.
- The real-user benchmark must not use the admin API as a substitute for normal researcher task work. Admin may set up users and project access, but collaborative task creation, revision requests, and approval evidence should be produced by authenticated researcher actors when the product contract allows it.
- Benchmark reviewer actors reject outputs that are explicitly blocked, missing required source data, low confidence because data is unavailable, or synthetic for a source-backed task. Those outputs receive revision instructions instead of being counted as done.
- Source-backed task tests should draw their source material from the canonical synthetic corpus or a manifest-backed canonical slice, so review decisions are based on representative documents instead of tiny ad hoc fixtures.
- Approval is a research-validity boundary, not a bypass. Review can move a task to Done only when task-linked research artifacts have no unresolved validity blockers: findings must have accepted/reconciled coded evidence, and low-agreement code applications must be resolved or rejected first.
- Approval and report routing check item-level support. A task is still blocked when any task nugget lacks an accepted/reconciled coded evidence unit, or when a fact, insight, or recommendation depends on an unsupported upstream artifact. Aggregate accepted-code counts are diagnostics only, never a bulk promotion rule.
- Task atomic-path snapshots include each visible task finding's research-validity state, so review/Kanban surfaces can show whether a nugget, fact, insight, or recommendation is accepted, provisional, blocked, or excluded instead of only showing its text.
- When review moves a valid task to Done and `approved`, review side effects route that task's accepted atomic findings into the report manager; revision and In Review states keep findings visible for evaluation but outside Reports.
- Review surfaces expose research-validity traceability for the active task: low-agreement dependencies, reconciliation decisions, report links, and stored Evidence Graph edges. These counts help researchers decide whether to approve or send work back, but the graph trail remains explanatory; report promotion still requires accepted/reconciled evidence and Done approval.
- System or machine execution failures create their own review event and diagnostic feedback without replacing an existing human revision instruction in `Task.what_to_review`. The Task Editor loads recent review events from the quality summary and exposes both human guidance and machine diagnostics in a visible review-history disclosure.
- Agent retry prompts label `Task.last_review_feedback` as review feedback (not human feedback), because the field may contain a machine execution diagnostic after a failed attempt.
- Human approval and revision requests emit content-free `human_review.decision` telemetry. Kanban status changes, including review-driven Done or revision transitions, emit `kanban.status_transition` telemetry so Quality Dashboard and governed learning can inspect review throughput without storing review text or source content.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- No direct agent, skill, LLM, or MCP behavior is asserted beyond the cited source files.

## Tests And Verification

- `tests/test_tasks.py`
- `tests/test_tasks.py::test_task_report_gate_blocks_aggregate_reliability_bulk_acceptance`
- `tests/test_tasks.py::test_task_atomic_snapshot_exposes_finding_research_validity`
- `tests/real_user_benchmark/run.mjs`

## Related Features

- [findings.review](../../findings/review/architecture.md)
- [agents.proposals](../../agents/proposals/architecture.md)

## Related Concepts

- [triangulation](../../../glossary/triangulation.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657; CF-SPEC-73 / CF-941; CF-SPEC-121; CF-SPEC-122; CF-SPEC-123 / CF-1581
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
