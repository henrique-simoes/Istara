---
stable_id: interviews.files
title: Interview Files
ui_path: Interviews > Files
audience: researcher
status: documented
related_features: ["interviews.transcription", "documents.upload"]
related_glossary: ["atomic-research"]
code_references: ["frontend/src/components/interviews/InterviewView.tsx", "backend/app/api/routes/files.py"]
api_references: ["backend/app/api/routes/files.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Interview Files

## What It Does

The Interviews view manages interview recordings and source files for participant research analysis.

## Why It Exists

Interview Files exists so the work represented by Interviews > Files has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Interviews > Files
- Navigation group: Interviews
- Primary component: `InterviewView`

## How UX Researchers Use It

- Open Interviews > Files from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with interview files in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Interviews > Files when the current research task needs interview files.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: interviews.transcription, documents.upload.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with interview files.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [interviews.transcription](../../interviews/transcription/researcher.md)
- [documents.upload](../../documents/upload/researcher.md)

## Related Concepts

- [atomic-research](../../../glossary/atomic-research.md)

## Evidence

- Source files: `frontend/src/components/interviews/InterviewView.tsx`, `backend/app/api/routes/files.py`
- API references: `backend/app/api/routes/files.py`
- Tests: none recorded
