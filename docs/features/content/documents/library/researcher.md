---
stable_id: documents.library
title: Document Library
ui_path: Documents > Library
audience: researcher
status: documented
related_features: ["documents.upload", "documents.preview", "chat.files"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/documents/DocumentsView.tsx", "frontend/src/stores/documentStore.ts", "backend/app/api/routes/documents.py"]
api_references: ["backend/app/api/routes/documents.py"]
test_references: ["tests/test_documents.py", "tests/test_project_rbac.py"]
last_verified: 2026-05-19
compass: CF-SPEC-53 / CF-657
---

# Document Library

## What It Does

Documents centralizes project documents and makes source material available for preview, chat, and analysis workflows.

## Why It Exists

Document Library exists so the work represented by Documents > Library has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Documents > Library
- Navigation group: Documents
- Primary component: `DocumentsView`

## How UX Researchers Use It

- Open Documents > Library from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with document library in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Documents > Library when the current research task needs document library.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: documents.upload, documents.preview, chat.files.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with document library.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.
- Switching projects clears the visible document library before the next project loads, so stale documents from another project should not remain on screen.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [documents.upload](../../documents/upload/researcher.md)
- [documents.preview](../../documents/preview/researcher.md)
- [chat.files](../../chat/files/researcher.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Evidence

- Source files: `frontend/src/components/documents/DocumentsView.tsx`, `frontend/src/stores/documentStore.ts`, `backend/app/api/routes/documents.py`
- API references: `backend/app/api/routes/documents.py`
- Tests: `tests/test_documents.py`, `tests/test_project_rbac.py`
