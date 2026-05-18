---
stable_id: chat.model-controls
title: Chat Model Controls
ui_path: Chat > Model Controls
audience: researcher
status: documented
related_features: ["settings.llm-servers", "settings.general", "compute.pool"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/chat/ChatView.tsx", "frontend/src/components/chat/chatViewParts.tsx", "frontend/src/lib/modelProviders.ts", "backend/app/api/routes/llm_servers.py"]
api_references: ["backend/app/api/routes/llm_servers.py", "backend/app/core/llm_router.py"]
test_references: ["frontend/src/lib/modelProviders.test.ts"]
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Chat Model Controls

## What It Does

Chat exposes model, thinking, and reasoning controls so users can tune how the assistant responds within the configured local or server-backed model environment.

## Why It Exists

Chat Model Controls exists so the work represented by Chat > Model Controls has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Chat > Model Controls
- Navigation group: Chat
- Primary component: `ChatView / chatViewParts`

## How UX Researchers Use It

- Open Chat > Model Controls from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with chat model controls in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Chat > Model Controls when the current research task needs chat model controls.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: settings.llm-servers, settings.general, compute.pool.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with chat model controls.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [settings.llm-servers](../../settings/llm-servers/researcher.md)
- [settings.general](../../settings/general/researcher.md)
- [compute.pool](../../compute/pool/researcher.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Evidence

- Source files: `frontend/src/components/chat/ChatView.tsx`, `frontend/src/components/chat/chatViewParts.tsx`, `frontend/src/lib/modelProviders.ts`, `backend/app/api/routes/llm_servers.py`
- API references: `backend/app/api/routes/llm_servers.py`, `backend/app/core/llm_router.py`
- Tests: `frontend/src/lib/modelProviders.test.ts`
