---
stable_id: documents.suggestions
title: Document Suggestions
ui_path: Documents > Suggestions
audience: researcher
status: needs-verification
related_features: ["documents.preview", "chat.overview"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/common/InteractiveSuggestionBox.tsx", "frontend/src/components/documents/DocumentsView.tsx"]
api_references: ["backend/app/api/routes/documents.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Document Suggestions

## What It Does

Interactive suggestions surface possible next actions or edits for document-centered workflows.

## Why It Exists

Document Suggestions exists so the work represented by Documents > Suggestions has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Documents > Suggestions
- Navigation group: Documents
- Primary component: `InteractiveSuggestionBox`

## How UX Researchers Use It

- Open Documents > Suggestions from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with document suggestions in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Documents > Suggestions when the current research task needs document suggestions.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: documents.preview, chat.overview.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with document suggestions.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [documents.preview](../../documents/preview/researcher.md)
- [chat.overview](../../chat/overview/researcher.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Evidence

- Source files: `frontend/src/components/common/InteractiveSuggestionBox.tsx`, `frontend/src/components/documents/DocumentsView.tsx`
- API references: `backend/app/api/routes/documents.py`
- Tests: none recorded
