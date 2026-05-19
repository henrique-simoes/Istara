---
stable_id: settings.governed-evolution
title: Governed Evolution
ui_path: Settings > Governed Evolution
audience: researcher
status: documented
related_features: ["meta.hyperagent", "quality.dashboard"]
related_glossary: ["compass-forge"]
code_references: ["frontend/src/components/settings/GovernedEvolutionView.tsx", "frontend/src/lib/improvementGovernanceApi.ts", "frontend/src/lib/dgmhArchiveApi.ts", "frontend/src/lib/api.ts", "backend/app/api/routes/improvement_governance.py", "backend/app/api/routes/dgmh_archive.py", "backend/app/api/routes/reasoning_bank.py", "backend/app/core/improvement_governance.py", "backend/app/core/dgmh_archive.py", "backend/app/core/reasoning_bank.py"]
api_references: ["backend/app/api/routes/improvement_governance.py", "backend/app/api/routes/dgmh_archive.py", "backend/app/api/routes/reasoning_bank.py"]
test_references: ["tests/test_improvement_governance.py", "tests/test_dgmh_archive.py", "tests/test_reasoning_bank.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-60 / CF-757
---

# Governed Evolution

## What It Does

Governed Evolution displays proposals, archive variants, reasoning memories, and contract information for controlled self-improvement in the active project.

## Why It Exists

Governed Evolution exists so the work represented by Settings > Governed Evolution has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Settings > Governed Evolution
- Navigation group: Settings
- Primary component: `GovernedEvolutionView`

## How UX Researchers Use It

- Open Settings > Governed Evolution from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with governed evolution in the active project context.
- Select a project before reviewing proposals, archive variants, or reasoning memories; this view does not show global governed-evolution history.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Settings > Governed Evolution when the current research task needs governed evolution.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: meta.hyperagent, quality.dashboard.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with governed evolution.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.
- Approvals, sandbox checks, applies, reverts, and quarantines stay bound to the same project as the displayed proposal or archive variant.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Global aggregation for governed-evolution metrics belongs to admin reporting surfaces, not this project-facing settings view.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [meta.hyperagent](../../meta/hyperagent/researcher.md)
- [quality.dashboard](../../quality/dashboard/researcher.md)

## Related Concepts

- [compass-forge](../../../glossary/compass-forge.md)

## Evidence

- Source files: `frontend/src/components/settings/GovernedEvolutionView.tsx`, `frontend/src/lib/improvementGovernanceApi.ts`, `frontend/src/lib/dgmhArchiveApi.ts`, `frontend/src/lib/api.ts`, `backend/app/api/routes/improvement_governance.py`, `backend/app/api/routes/dgmh_archive.py`, `backend/app/api/routes/reasoning_bank.py`, `backend/app/core/improvement_governance.py`, `backend/app/core/dgmh_archive.py`, `backend/app/core/reasoning_bank.py`
- API references: `backend/app/api/routes/improvement_governance.py`, `backend/app/api/routes/dgmh_archive.py`, `backend/app/api/routes/reasoning_bank.py`
- Tests: `tests/test_improvement_governance.py`, `tests/test_dgmh_archive.py`, `tests/test_reasoning_bank.py`, `tests/test_project_scope_contracts.py`
