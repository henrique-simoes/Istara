---
stable_id: chat.sessions
title: Chat Sessions
ui_path: Chat > Sessions
audience: researcher
status: documented
related_features: ["chat.overview", "history.version"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/chat/ChatSessionsSidebar.tsx", "frontend/src/stores/sessionStore.ts", "backend/app/api/routes/sessions.py"]
api_references: ["frontend/src/lib/sessionsApi.ts", "backend/app/api/routes/sessions.py"]
test_references: ["tests/test_sessions.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-60 / CF-761
---

# Chat Sessions

## What It Does

The chat session sidebar manages project-scoped conversation history and new session creation. A saved chat selection belongs to one project only, so switching projects cannot show another project's conversation even when the same user is authorized in both projects.

## Why It Exists

Chat Sessions exists so the work represented by Chat > Sessions has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Chat > Sessions
- Navigation group: Chat
- Primary component: `ChatSessionsSidebar`

## How UX Researchers Use It

- Open Chat > Sessions from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with chat sessions in the active project context.
- Rename, star, delete, and reopen sessions only inside the active project; stale sessions from another project are cleared before the new project's list loads.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Chat > Sessions when the current research task needs chat sessions.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: chat.overview, history.version.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with chat sessions.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.
- Session history and messages whose `project_id` matches the active project and the current user's authorization.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [chat.overview](../../chat/overview/researcher.md)
- [history.version](../../history/version/researcher.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Evidence

- Source files: `frontend/src/components/chat/ChatSessionsSidebar.tsx`, `frontend/src/stores/sessionStore.ts`, `backend/app/api/routes/sessions.py`
- API references: `frontend/src/lib/sessionsApi.ts`, `backend/app/api/routes/sessions.py`
- Tests: `tests/test_sessions.py`, `tests/test_project_scope_contracts.py`
