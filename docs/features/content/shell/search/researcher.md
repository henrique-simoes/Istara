---
stable_id: shell.search
title: Project Search
ui_path: Shell > Search
audience: researcher
status: documented
related_features: ["shell.navigation", "shell.keyboard-shortcuts"]
related_glossary: ["wcag"]
code_references: ["frontend/src/components/layout/HomeClient.tsx", "frontend/src/components/common/SearchModal.tsx", "frontend/src/lib/api.ts"]
api_references: ["backend/app/api/routes/findings.py"]
test_references: ["tests/test_project_scope_contracts.py", "tests/test_findings.py"]
last_verified: 2026-09-02
compass: CF-SPEC-60 / CF-772
---

# Project Search

## What It Does

The shell exposes a command/search modal from the sidebar and keyboard shortcut so users can find findings inside the active project.

## Why It Exists

Project Search exists so the work represented by Shell > Search has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Shell > Search
- Navigation group: Shell
- Primary component: `SearchModal`

## How UX Researchers Use It

- Open Shell > Search from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with project search in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Shell > Search when the current research task needs project search.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: shell.navigation, shell.keyboard-shortcuts.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with project search.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Search results are limited to the active project. The project search route combines document-RAG matches with exact text matches for manual nuggets, facts, insights, and recommendations; these remain provisional and are never promoted by searching. Cross-project findings search is reserved for explicit admin reporting surfaces.
- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [shell.navigation](../../shell/navigation/researcher.md)
- [shell.keyboard-shortcuts](../../shell/keyboard-shortcuts/researcher.md)

## Related Concepts

- [wcag](../../../glossary/wcag.md)

## Evidence

- Source files: `frontend/src/components/layout/HomeClient.tsx`, `frontend/src/components/common/SearchModal.tsx`, `frontend/src/lib/api.ts`
- API references: `backend/app/api/routes/findings.py`
- Tests: `tests/test_project_scope_contracts.py`, `tests/test_findings.py`
