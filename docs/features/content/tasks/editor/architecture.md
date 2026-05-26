---
stable_id: tasks.editor
title: Task Editor
ui_path: Tasks > Task Editor
audience: architecture
status: documented
related_features: ["tasks.kanban", "tasks.attachments"]
related_glossary: ["scr"]
code_references: ["frontend/src/components/kanban/TaskEditor.tsx", "frontend/src/stores/taskStore.ts", "backend/app/api/routes/tasks.py", "backend/app/core/task_contracts.py", "backend/app/skills/system_actions.py"]
api_references: ["backend/app/api/routes/tasks.py"]
test_references: ["tests/test_tasks.py", "tests/test_agents.py"]
last_verified: 2026-05-21
compass: CF-SPEC-53 / CF-657; CF-SPEC-73 / CF-941
---

# Task Editor Architecture

## Implementation Summary

The task editor creates and updates task details, assignments, status, and task-linked research context.

## Frontend Surface

- `frontend/src/components/kanban/TaskEditor.tsx`
- `frontend/src/stores/taskStore.ts`
- `backend/app/api/routes/tasks.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/taskStore.ts`

### API And Backend

- `backend/app/api/routes/tasks.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/kanban/TaskEditor.tsx` and the UI navigation path recorded in the inventory.
- The editor treats the selected project as part of every task action. Saves, quality summaries, atomic-path reads, review approvals, revision requests, and report sends require `activeProjectId` to match `task.project_id` before calling the backend.
- Backend task-by-id routes require the active `project_id` and bind it to `Task.project_id` before returning or mutating task data, preventing stale editor state from acting on another project's task.
- Chat and agent system-action task creation follows the same active-project contract for task-bound context. LLM-created tasks remain backlog work items, attached `input_document_ids` must belong to the active project, and legacy `critical` priority is normalized to the canonical `urgent` priority before storage.
- Task atomic paths include task-linked research-validity state: coding-run counts, code-application counts, accepted code counts, latest coding-run status, and blocked/review items. Review UI uses that data to explain low reliability, missing accepted codes, missing coding, or reconciliation needs before a task is approved or sent to Reports.
- The editor disables Mark Done and Send to Report for research tasks with task-bound findings until accepted/reconciled coded evidence exists. Researchers see whether they need to start a coding run, reconcile low-agreement codes, or accept governed code applications.
- The Task Editor also calls the project-scoped research-validity traceability API for the active task. It shows `graph+hybrid` Evidence Graph counts for low-agreement dependencies, reconciliation decisions, report links, and graph edges so researchers can understand why work needs review without treating GraphRAG as a promotion shortcut.
- Report creation from the task route still requires human-approved Done status, and also checks the research-validity gate. If a task has unreconciled code applications or no accepted/reconciled evidence after review, `POST /tasks/{task_id}/reports` returns a conflict instead of letting unreviewed evidence flow into Reports.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Agent skill output that stores nuggets creates task-linked evidence units and starts a governed coding run through `backend/app/services/research_validity_service.py`. The coding run may use donated/project-authorized compute through Compute Manager; route evidence and reliability status remain project scoped.
- Manual skill execution receives a task id before the skill runs, then stores the output on that same In Review task so any task-aware skill can attach provenance to the eventual review artifact.

## Tests And Verification

- `tests/test_tasks.py`
- `tests/test_agents.py`

## Related Features

- [tasks.kanban](../../tasks/kanban/architecture.md)
- [tasks.attachments](../../tasks/attachments/architecture.md)

## Related Concepts

- [scr](../../../glossary/scr.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657; CF-SPEC-73 / CF-941
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
