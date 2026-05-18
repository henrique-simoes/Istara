---
stable_id: backup.view
title: Backup
ui_path: Backup
audience: researcher
status: documented
related_features: ["history.version", "settings.project"]
related_glossary: ["compass-forge"]
code_references: ["frontend/src/components/backup/BackupView.tsx", "frontend/src/lib/backupApi.ts", "backend/app/api/routes/backup.py", "backend/app/core/backup_manager.py"]
api_references: ["backend/app/api/routes/backup.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Backup

## What It Does

Backup provides project or system backup controls and status for preserving Istara data.

## Why It Exists

Backup exists so the work represented by Backup has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Backup
- Navigation group: Secondary
- Primary component: `BackupView`

## How UX Researchers Use It

- Open Backup from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with backup in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Backup when the current research task needs backup.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: history.version, settings.project.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with backup.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [history.version](../../history/version/researcher.md)
- [settings.project](../../settings/project/researcher.md)

## Related Concepts

- [compass-forge](../../../glossary/compass-forge.md)

## Evidence

- Source files: `frontend/src/components/backup/BackupView.tsx`, `frontend/src/lib/backupApi.ts`, `backend/app/api/routes/backup.py`, `backend/app/core/backup_manager.py`
- API references: `backend/app/api/routes/backup.py`
- Tests: none recorded
