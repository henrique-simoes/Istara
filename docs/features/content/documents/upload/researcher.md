---
stable_id: documents.upload
title: Document Upload
ui_path: Documents > Upload
audience: researcher
status: documented
related_features: ["documents.library", "chat.files", "tasks.attachments"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/documents/DocumentsView.tsx", "backend/app/api/routes/files.py", "backend/app/core/upload_security.py"]
api_references: ["backend/app/api/routes/files.py", "backend/app/api/routes/documents.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Document Upload

## What It Does

Upload controls import project files and documents into Istara for downstream reading, chat, and evidence workflows.

## Why It Exists

Document Upload exists so the work represented by Documents > Upload has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Documents > Upload
- Navigation group: Documents
- Primary component: `DocumentsView`

## How UX Researchers Use It

- Open Documents > Upload from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with document upload in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Documents > Upload when the current research task needs document upload.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: documents.library, chat.files, tasks.attachments.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with document upload.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [documents.library](../../documents/library/researcher.md)
- [chat.files](../../chat/files/researcher.md)
- [tasks.attachments](../../tasks/attachments/researcher.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Evidence

- Source files: `frontend/src/components/documents/DocumentsView.tsx`, `backend/app/api/routes/files.py`, `backend/app/core/upload_security.py`
- API references: `backend/app/api/routes/files.py`, `backend/app/api/routes/documents.py`
- Tests: none recorded
