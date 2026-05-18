---
stable_id: interfaces.figma
title: Configuration
ui_path: Interfaces > Configuration
audience: researcher
status: needs-verification
related_features: ["interfaces.screens", "integrations.overview"]
related_glossary: ["wcag"]
code_references: ["frontend/src/components/interfaces/FigmaTab.tsx", "backend/app/api/routes/interfaces_integrations.py"]
api_references: ["backend/app/api/routes/interfaces_integrations.py"]
test_references: ["tests/test_project_scope_contracts.py"]
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657; CF-SPEC-59 / CF-740
---

# Configuration

## What It Does

The Configuration tab connects interface work with design-tool setup, including Figma-oriented import or export flows.

## Why It Exists

Configuration exists so the work represented by Interfaces > Configuration has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Interfaces > Configuration
- Navigation group: Interfaces
- Primary component: `FigmaTab`

## How UX Researchers Use It

- Open Interfaces > Configuration from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with interface configuration in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Interfaces > Configuration when the current research task needs interface configuration.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: interfaces.screens, integrations.overview.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with interface configuration.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.
- The navigation label is expected to read `Configuration`; `tests/test_project_scope_contracts.py` protects this copy from regressing to the old menu label.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [interfaces.screens](../../interfaces/screens/researcher.md)
- [integrations.overview](../../integrations/overview/researcher.md)

## Related Concepts

- [wcag](../../../glossary/wcag.md)

## Evidence

- Source files: `frontend/src/components/interfaces/FigmaTab.tsx`, `backend/app/api/routes/interfaces_integrations.py`
- API references: `backend/app/api/routes/interfaces_integrations.py`
- Tests: `tests/test_project_scope_contracts.py`
