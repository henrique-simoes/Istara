---
stable_id: chat.files
title: Chat File Attachments
ui_path: Chat > File Attachments
audience: researcher
status: documented
related_features: ["documents.upload", "documents.library", "chat.overview"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/chat/ChatView.tsx", "backend/app/api/routes/files.py", "backend/app/core/file_processor.py"]
api_references: ["backend/app/api/routes/files.py", "backend/app/api/routes/documents.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Chat File Attachments

## What It Does

Chat can attach uploaded project files and documents so the conversation can use project evidence and user-provided material.

## Why It Exists

Chat File Attachments exists so the work represented by Chat > File Attachments has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Chat > File Attachments
- Navigation group: Chat
- Primary component: `ChatView`

## How UX Researchers Use It

- Open Chat > File Attachments from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with chat file attachments in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Chat > File Attachments when the current research task needs chat file attachments.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: documents.upload, documents.library, chat.overview.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with chat file attachments.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [documents.upload](../../documents/upload/researcher.md)
- [documents.library](../../documents/library/researcher.md)
- [chat.overview](../../chat/overview/researcher.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Evidence

- Source files: `frontend/src/components/chat/ChatView.tsx`, `backend/app/api/routes/files.py`, `backend/app/core/file_processor.py`
- API references: `backend/app/api/routes/files.py`, `backend/app/api/routes/documents.py`
- Tests: none recorded
