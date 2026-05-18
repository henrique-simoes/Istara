---
stable_id: settings.general
title: System Status And Models
ui_path: Settings > System Status And Models
audience: researcher
status: documented
related_features: ["settings.llm-servers", "compute.pool"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/common/SettingsView.tsx", "backend/app/api/routes/settings.py"]
api_references: ["backend/app/api/routes/settings.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# System Status And Models

## What It Does

Settings shows backend, LLM, hardware, model recommendation, and available model status for the local installation.

## Why It Exists

System Status And Models exists so the work represented by Settings > System Status And Models has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Settings > System Status And Models
- Navigation group: Settings
- Primary component: `SettingsView`

## How UX Researchers Use It

- Open Settings > System Status And Models from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with system status and models in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Settings > System Status And Models when the current research task needs system status and models.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: settings.llm-servers, compute.pool.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with system status and models.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [settings.llm-servers](../../settings/llm-servers/researcher.md)
- [compute.pool](../../compute/pool/researcher.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Evidence

- Source files: `frontend/src/components/common/SettingsView.tsx`, `backend/app/api/routes/settings.py`
- API references: `backend/app/api/routes/settings.py`
- Tests: none recorded
