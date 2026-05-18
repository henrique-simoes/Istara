---
stable_id: history.version
title: Version History
ui_path: History
audience: researcher
status: documented
related_features: ["backup.view", "chat.sessions", "loops.history"]
related_glossary: ["compass-forge"]
code_references: ["frontend/src/components/common/VersionHistory.tsx", "backend/app/core/versioning.py"]
api_references: ["backend/app/api/routes/projects.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Version History

## What It Does

History lists project or artifact version events for traceability and recovery.

## Why It Exists

Version History exists so the work represented by History has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: History
- Navigation group: Secondary
- Primary component: `VersionHistory`

## How UX Researchers Use It

- Open History from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with version history in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from History when the current research task needs version history.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: backup.view, chat.sessions, loops.history.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with version history.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [backup.view](../../backup/view/researcher.md)
- [chat.sessions](../../chat/sessions/researcher.md)
- [loops.history](../../loops/history/researcher.md)

## Related Concepts

- [compass-forge](../../../glossary/compass-forge.md)

## Evidence

- Source files: `frontend/src/components/common/VersionHistory.tsx`, `backend/app/core/versioning.py`
- API references: `backend/app/api/routes/projects.py`
- Tests: none recorded
