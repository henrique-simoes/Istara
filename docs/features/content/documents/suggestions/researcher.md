---
stable_id: documents.suggestions
title: Document Suggestions
ui_path: Documents > Suggestions
audience: researcher
status: verified
related_features: ["documents.preview", "chat.overview"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/common/InteractiveSuggestionBox.tsx", "frontend/src/components/documents/DocumentsView.tsx", "frontend/src/lib/suggestionStream.ts"]
api_references: ["backend/app/api/routes/sessions.py", "backend/app/api/routes/chat.py"]
test_references: ["frontend/src/lib/suggestionStream.test.ts"]
last_verified: 2026-08-31
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
- Review the provisional output in the same view and follow the related feature links when the workflow moves into another Istara surface.
- Use Stop to cancel an active suggestion request. If no chat-ready model is
  configured, the panel shows the server's Settings guidance instead of
  remaining blank.

## Supported Workflows

- Start from Documents > Suggestions when the current research task needs document suggestions.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: documents.preview, chat.overview.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with document suggestions.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Organization suggestions do not rename or move files. They are provisional
  chat guidance and are not accepted Research Spine evidence.
- A project-scoped suggestion session can still be opened in Chat after it is
  created. A model-readiness error must be resolved in Settings before a useful
  answer can be generated.
- Loading, unavailable-model error, and cancellation behavior were verified on
  the published QA surface; permission-denied behavior remains contract-tested
  elsewhere rather than exercised with a second live role in this walkthrough.

## Related Features

- [documents.preview](../../documents/preview/researcher.md)
- [chat.overview](../../chat/overview/researcher.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Evidence

- Source files: `frontend/src/components/common/InteractiveSuggestionBox.tsx`, `frontend/src/components/documents/DocumentsView.tsx`
- API references: `backend/app/api/routes/sessions.py`, `backend/app/api/routes/chat.py`
- Tests: `frontend/src/lib/suggestionStream.test.ts`
