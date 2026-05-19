---
stable_id: interfaces.design-chat
title: Interface Design Chat
ui_path: Interfaces > Design Chat
audience: researcher
status: documented
related_features: ["interfaces.generate", "interfaces.findings-picker"]
related_glossary: ["minto-pyramid"]
code_references: ["frontend/src/components/interfaces/InterfacesView.tsx", "frontend/src/components/interfaces/DesignChatTab.tsx", "frontend/src/stores/interfacesStore.ts", "backend/app/api/routes/interfaces.py"]
api_references: ["backend/app/api/routes/interfaces.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Interface Design Chat

## What It Does

Design Chat is the conversational starting point for generating, refining, and reasoning about interface concepts.

## Why It Exists

Interface Design Chat exists so the work represented by Interfaces > Design Chat has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Interfaces > Design Chat
- Navigation group: Interfaces
- Primary component: `DesignChatTab`

## How UX Researchers Use It

- Open Interfaces > Design Chat from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with interface design chat in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Interfaces > Design Chat when the current research task needs interface design chat.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: interfaces.generate, interfaces.findings-picker.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with interface design chat.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [interfaces.generate](../../interfaces/generate/researcher.md)
- [interfaces.findings-picker](../../interfaces/findings-picker/researcher.md)

## Related Concepts

- [minto-pyramid](../../../glossary/minto-pyramid.md)

## Evidence

- Source files: `frontend/src/components/interfaces/InterfacesView.tsx`, `frontend/src/components/interfaces/DesignChatTab.tsx`, `frontend/src/stores/interfacesStore.ts`, `backend/app/api/routes/interfaces.py`
- API references: `backend/app/api/routes/interfaces.py`
- Tests: none recorded
