---
stable_id: interviews.files
title: Interview Files
ui_path: Interviews > Files
audience: architecture
status: documented
related_features: ["interviews.transcription", "documents.upload"]
related_glossary: ["atomic-research"]
code_references: ["frontend/src/components/interviews/InterviewView.tsx", "backend/app/api/routes/files.py"]
api_references: ["backend/app/api/routes/files.py"]
test_references: ["tests/document_corpus/canonical/manifest.json", "tests/simulation/scenarios/70-research-integrity.mjs"]
last_verified: 2026-05-21
compass: CF-SPEC-53 / CF-657; CF-SPEC-123 / CF-1581
---

# Interview Files Architecture

## Implementation Summary

The Interviews view manages interview recordings and source files for participant research analysis.

## Frontend Surface

- `frontend/src/components/interviews/InterviewView.tsx`
- `backend/app/api/routes/files.py`

## State, API, And Backend Contracts

### Stores

- None recorded.

### API And Backend

- `backend/app/api/routes/files.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/interviews/InterviewView.tsx` and the UI navigation path recorded in the inventory.
- Interview-heavy tests should use the canonical corpus `interview-heavy` slice through `tests/document_corpus/shared-corpus.mjs` when they evaluate product behavior. Tiny transcript strings are reserved for parser/unit tests only.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- No direct agent, skill, LLM, or MCP behavior is asserted beyond the cited source files.

## Tests And Verification

- `tests/document_corpus/canonical/manifest.json`
- `tests/simulation/scenarios/70-research-integrity.mjs`

## Related Features

- [interviews.transcription](../../interviews/transcription/architecture.md)
- [documents.upload](../../documents/upload/architecture.md)

## Related Concepts

- [atomic-research](../../../glossary/atomic-research.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657; CF-SPEC-123 / CF-1581
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
