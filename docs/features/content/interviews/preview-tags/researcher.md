---
stable_id: interviews.preview-tags
title: Interview Preview And Tags
ui_path: Interviews > Preview And Tags
audience: researcher
status: documented
related_features: ["agents.registry", "interviews.files"]
related_glossary: ["atomic-research"]
code_references: ["frontend/src/components/interviews/interviewPreviewParts.tsx", "frontend/src/components/interviews/InterviewView.tsx"]
api_references: ["backend/app/api/routes/files.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Interview Preview And Tags

## What It Does

Interview preview parts display file previews, send-to-agent actions, and tag creation controls.

## Why It Exists

Interview Preview And Tags exists so the work represented by Interviews > Preview And Tags has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Interviews > Preview And Tags
- Navigation group: Interviews
- Primary component: `interviewPreviewParts`

## How UX Researchers Use It

- Open Interviews > Preview And Tags from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with interview preview and tags in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Interviews > Preview And Tags when the current research task needs interview preview and tags.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: agents.registry, interviews.files.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with interview preview and tags.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [agents.registry](../../agents/registry/researcher.md)
- [interviews.files](../../interviews/files/researcher.md)

## Related Concepts

- [atomic-research](../../../glossary/atomic-research.md)

## Evidence

- Source files: `frontend/src/components/interviews/interviewPreviewParts.tsx`, `frontend/src/components/interviews/InterviewView.tsx`
- API references: `backend/app/api/routes/files.py`
- Tests: none recorded
