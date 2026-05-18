---
stable_id: settings.governed-evolution
title: Governed Evolution
ui_path: Settings > Governed Evolution
audience: researcher
status: documented
related_features: ["meta.hyperagent", "quality.dashboard"]
related_glossary: ["compass-forge"]
code_references: ["frontend/src/components/settings/GovernedEvolutionView.tsx", "frontend/src/lib/improvementGovernanceApi.ts", "backend/app/api/routes/improvement_governance.py", "backend/app/core/improvement_governance.py"]
api_references: ["backend/app/api/routes/improvement_governance.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Governed Evolution

## What It Does

Governed Evolution displays proposals, archive, reasoning, and contract information for controlled system self-improvement.

## Why It Exists

Governed Evolution exists so the work represented by Settings > Governed Evolution has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Settings > Governed Evolution
- Navigation group: Settings
- Primary component: `GovernedEvolutionView`

## How UX Researchers Use It

- Open Settings > Governed Evolution from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with governed evolution in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Settings > Governed Evolution when the current research task needs governed evolution.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: meta.hyperagent, quality.dashboard.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with governed evolution.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [meta.hyperagent](../../meta/hyperagent/researcher.md)
- [quality.dashboard](../../quality/dashboard/researcher.md)

## Related Concepts

- [compass-forge](../../../glossary/compass-forge.md)

## Evidence

- Source files: `frontend/src/components/settings/GovernedEvolutionView.tsx`, `frontend/src/lib/improvementGovernanceApi.ts`, `backend/app/api/routes/improvement_governance.py`, `backend/app/core/improvement_governance.py`
- API references: `backend/app/api/routes/improvement_governance.py`
- Tests: none recorded
