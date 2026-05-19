---
stable_id: findings.evidence
title: Findings Evidence
ui_path: Findings > Evidence
audience: architecture
status: documented
related_features: ["findings.phase-tabs", "findings.codebook", "findings.reports"]
related_glossary: ["atomic-research", "triangulation"]
code_references: ["frontend/src/components/findings/FindingsView.tsx", "backend/app/api/routes/findings.py"]
api_references: ["backend/app/api/routes/findings.py"]
test_references: ["tests/test_findings.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-60 / CF-772
---

# Findings Evidence Architecture

## Implementation Summary

The Findings evidence tab lists research insights and recommendations for the active project and supports phase-oriented review.

## Frontend Surface

- `frontend/src/components/findings/FindingsView.tsx`
- `backend/app/api/routes/findings.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/projectStore.ts`

### API And Backend

- `backend/app/api/routes/findings.py`
- Project-facing findings list routes require `project_id` and verify project access before returning nuggets, facts, insights, recommendations, or design decisions.
- Evidence-chain traversal filters linked records by the originating finding's project before returning nested nuggets, facts, insights, recommendations, design decisions, or screens.

## Architecture Notes

- The feature is mounted through `frontend/src/components/findings/FindingsView.tsx` and the UI navigation path recorded in the inventory.
- The backend retains an explicit admin-only global findings search route for admin/reporting aggregation; project-facing evidence views do not use unscoped list routes.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Findings evidence is project content. Every non-admin read must be bound to the caller's authorized active project, and global aggregation belongs only to dedicated admin surfaces.

## Tests And Verification

- `tests/test_findings.py`
- `tests/test_project_scope_contracts.py`

## Related Features

- [findings.phase-tabs](../../findings/phase-tabs/architecture.md)
- [findings.codebook](../../findings/codebook/architecture.md)
- [findings.reports](../../findings/reports/architecture.md)

## Related Concepts

- [atomic-research](../../../glossary/atomic-research.md)
- [triangulation](../../../glossary/triangulation.md)

## Compass Evidence

- Spec/task: CF-SPEC-60 / CF-772
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
