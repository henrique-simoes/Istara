---
stable_id: interfaces.findings-picker
title: Findings Picker
ui_path: Interfaces > Findings Picker
audience: researcher
status: documented
related_features: ["findings.evidence", "interfaces.design-chat"]
related_glossary: ["atomic-research"]
code_references: ["frontend/src/components/interfaces/FindingsPicker.tsx", "backend/app/api/routes/findings.py"]
api_references: ["backend/app/api/routes/findings.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Findings Picker

## What It Does

The Findings Picker lets interface workflows reference insights and recommendations from the Findings area.

## Why It Exists

Findings Picker exists so the work represented by Interfaces > Findings Picker has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Interfaces > Findings Picker
- Navigation group: Interfaces
- Primary component: `FindingsPicker`

## How UX Researchers Use It

- Open Interfaces > Findings Picker from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with findings picker in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Interfaces > Findings Picker when the current research task needs findings picker.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: findings.evidence, interfaces.design-chat.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with findings picker.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [findings.evidence](../../findings/evidence/researcher.md)
- [interfaces.design-chat](../../interfaces/design-chat/researcher.md)

## Related Concepts

- [atomic-research](../../../glossary/atomic-research.md)

## Evidence

- Source files: `frontend/src/components/interfaces/FindingsPicker.tsx`, `backend/app/api/routes/findings.py`
- API references: `backend/app/api/routes/findings.py`
- Tests: none recorded
