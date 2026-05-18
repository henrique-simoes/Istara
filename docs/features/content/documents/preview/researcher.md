---
stable_id: documents.preview
title: Document Preview
ui_path: Documents > Preview
audience: researcher
status: needs-verification
related_features: ["documents.library", "documents.suggestions"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/documents/DocumentsView.tsx", "frontend/src/components/common/ContextPreview.tsx"]
api_references: ["backend/app/api/routes/documents.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Document Preview

## What It Does

Document preview lets users inspect uploaded project material before using it in chat, interviews, or findings workflows.

## Why It Exists

Document Preview exists so the work represented by Documents > Preview has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Documents > Preview
- Navigation group: Documents
- Primary component: `DocumentsView`

## How UX Researchers Use It

- Open Documents > Preview from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with document preview in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Documents > Preview when the current research task needs document preview.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: documents.library, documents.suggestions.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with document preview.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [documents.library](../../documents/library/researcher.md)
- [documents.suggestions](../../documents/suggestions/researcher.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Evidence

- Source files: `frontend/src/components/documents/DocumentsView.tsx`, `frontend/src/components/common/ContextPreview.tsx`
- API references: `backend/app/api/routes/documents.py`
- Tests: none recorded
