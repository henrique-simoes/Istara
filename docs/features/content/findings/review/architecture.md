---
stable_id: findings.review
title: Findings Code Review
ui_path: Findings > Review
audience: architecture
status: needs-verification
related_features: ["findings.codebook", "tasks.review"]
related_glossary: ["triangulation"]
code_references: ["frontend/src/components/findings/FindingsView.tsx", "frontend/src/components/findings/CodeReviewQueue.tsx", "frontend/src/lib/researchIntegrityApi.ts"]
api_references: ["backend/app/api/routes/code_applications.py", "backend/app/api/routes/codebooks.py"]
test_references: ["tests/test_code_applications.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-78 / CF-1005
---

# Findings Code Review Architecture

## Implementation Summary

The Review tab presents code review queues for validating and adjudicating qualitative coding work. Review mutations pass the active project id and the backend binds each code-application id to that same project before applying reviewer decisions.

## Frontend Surface

- `frontend/src/components/findings/FindingsView.tsx`
- `frontend/src/components/findings/CodeReviewQueue.tsx`
- `frontend/src/lib/researchIntegrityApi.ts`

## State, API, And Backend Contracts

### Stores

- None recorded.

### API And Backend

- `backend/app/api/routes/code_applications.py`
- `backend/app/api/routes/codebooks.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/findings/FindingsView.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Code review is a project-content surface. Pending queues, bulk approval, and review mutations must stay inside the caller's authorized active project and must not infer project scope from a globally unique application id.

## Tests And Verification

- `tests/test_code_applications.py`
- `tests/test_project_scope_contracts.py`

## Related Features

- [findings.codebook](../../findings/codebook/architecture.md)
- [tasks.review](../../tasks/review/architecture.md)

## Related Concepts

- [triangulation](../../../glossary/triangulation.md)

## Compass Evidence

- Spec/task: CF-SPEC-78 / CF-1005
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
