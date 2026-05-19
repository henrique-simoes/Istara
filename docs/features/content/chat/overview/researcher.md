---
stable_id: chat.overview
title: Chat Workspace
ui_path: Chat
audience: researcher
status: documented
related_features: ["chat.sessions", "chat.model-controls", "chat.files", "chat.audio", "chat.steering"]
related_glossary: ["rag", "mcp"]
code_references: ["frontend/src/components/chat/ChatView.tsx", "frontend/src/stores/chatStore.ts", "frontend/src/stores/sessionStore.ts", "backend/app/api/routes/chat.py", "backend/app/api/routes/sessions.py"]
api_references: ["backend/app/api/routes/chat.py", "backend/app/api/routes/sessions.py", "frontend/src/lib/chatApi.ts", "frontend/src/lib/sessionsApi.ts"]
test_references: ["tests/test_chat.py", "tests/test_sessions.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-84 / CF-1089
---

# Chat Workspace

## What It Does

Chat is the project-scoped conversational workspace for working with Istara agents, context, files, and model settings.

## Why It Exists

Chat Workspace exists so the work represented by Chat has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Chat
- Navigation group: Chat
- Primary component: `ChatView`

## How UX Researchers Use It

- Open Chat from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with chat workspace in the active project context.
- Project switches clear the prior project's session history before the active project's chat loads.
- Agent selection is project-bound: project-owned agents can only be attached to sessions in their own project, while universal Istara system agents remain available.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Chat when the current research task needs chat workspace.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: chat.sessions, chat.model-controls, chat.files, chat.audio, chat.steering.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with chat workspace.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.
- Chat messages, agent selection, and session settings that belong to the active project and the current user's authorization.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [chat.sessions](../../chat/sessions/researcher.md)
- [chat.model-controls](../../chat/model-controls/researcher.md)
- [chat.files](../../chat/files/researcher.md)
- [chat.audio](../../chat/audio/researcher.md)
- [chat.steering](../../chat/steering/researcher.md)

## Related Concepts

- [rag](../../../glossary/rag.md)
- [mcp](../../../glossary/mcp.md)

## Evidence

- Source files: `frontend/src/components/chat/ChatView.tsx`, `frontend/src/stores/chatStore.ts`, `frontend/src/stores/sessionStore.ts`, `backend/app/api/routes/chat.py`, `backend/app/api/routes/sessions.py`
- API references: `backend/app/api/routes/chat.py`, `backend/app/api/routes/sessions.py`, `frontend/src/lib/chatApi.ts`, `frontend/src/lib/sessionsApi.ts`
- Tests: `tests/test_chat.py`, `tests/test_sessions.py`, `tests/test_project_scope_contracts.py`
