---
stable_id: interviews.transcription
title: Interview Transcription
ui_path: Interviews > Transcription
audience: researcher
status: needs-verification
related_features: ["interviews.files", "findings.evidence"]
related_glossary: ["atomic-research"]
code_references: ["frontend/src/components/interviews/InterviewView.tsx", "frontend/src/components/interviews/AudioPlayer.tsx", "backend/app/core/transcription.py"]
api_references: ["backend/app/api/routes/files.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Interview Transcription

## What It Does

Interview audio processing uses backend transcription capabilities to turn recordings into usable research text.

## Why It Exists

Interview Transcription exists so the work represented by Interviews > Transcription has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Interviews > Transcription
- Navigation group: Interviews
- Primary component: `InterviewView / AudioPlayer`

## How UX Researchers Use It

- Open Interviews > Transcription from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with interview transcription in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Interviews > Transcription when the current research task needs interview transcription.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: interviews.files, findings.evidence.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with interview transcription.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [interviews.files](../../interviews/files/researcher.md)
- [findings.evidence](../../findings/evidence/researcher.md)

## Related Concepts

- [atomic-research](../../../glossary/atomic-research.md)

## Evidence

- Source files: `frontend/src/components/interviews/InterviewView.tsx`, `frontend/src/components/interviews/AudioPlayer.tsx`, `backend/app/core/transcription.py`
- API references: `backend/app/api/routes/files.py`
- Tests: none recorded
