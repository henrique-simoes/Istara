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
test_references: ["tests/document_corpus/canonical/manifest.json", "tests/document_corpus/shared-corpus.test.mjs", "tests/test_public_repo_quality.py", "tests/simulation/scenarios/70-research-integrity.mjs"]
last_verified: 2026-05-26
compass: CF-SPEC-53 / CF-657; CF-SPEC-123 / CF-1581; CF-SPEC-131; CF-SPEC-142
---

# Interview Files Architecture

## Implementation Summary

The Interviews view manages interview recordings and source files for participant research analysis.
Interview files enter the Research Spine as raw sources. Audio recordings do not become trusted findings when uploaded; after transcription succeeds, the transcript is segmented into source evidence units that later require independent coding, reliability or reconciliation, and task review before report use.

## Frontend Surface

- `frontend/src/components/interviews/InterviewView.tsx`
- `backend/app/api/routes/files.py`
- Audio transcription stores transcript metadata on the `Document` and creates source evidence units only after the document is ready.

## State, API, And Backend Contracts

### Stores

- None recorded.

### API And Backend

- `backend/app/api/routes/files.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/interviews/InterviewView.tsx` and the UI navigation path recorded in the inventory.
- Interview-heavy tests should use the canonical corpus `interview-heavy` slice through `tests/document_corpus/shared-corpus.mjs` when they evaluate product behavior. Tiny transcript strings are reserved for parser/unit tests only.
- Canonical interview sources must remain transcript-like raw material: coherent participant IDs, timestamped speaker turns, monotonic transcript positions, varied quotes, and language/content consistency. They must not ship as pre-digested candidate evidence blocks.
- Interview transcript text is a source substrate for coding, not accepted Atomic Research. Any interview-derived nuggets/facts/insights/recommendations remain provisional until accepted by the Research Spine gates.
- Audio metadata keeps the compatibility `icr_kappa`/`icr_confidence` fields for operational review, but also records `formal_reliability: false`, `research_spine_eligible: false`, and `validation_scope: transcription_quality_signal`; the heuristic Whisper agreement must never be interpreted as the formal three-coder reliability gate.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- No direct agent, skill, LLM, or MCP behavior is asserted beyond the cited source files.

## Tests And Verification

- `tests/document_corpus/canonical/manifest.json`
- `tests/document_corpus/shared-corpus.test.mjs`
- `tests/test_public_repo_quality.py`
- `tests/simulation/scenarios/70-research-integrity.mjs`

## Related Features

- [interviews.transcription](../../interviews/transcription/architecture.md)
- [documents.upload](../../documents/upload/architecture.md)

## Related Concepts

- [atomic-research](../../../glossary/atomic-research.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657; CF-SPEC-123 / CF-1581; CF-SPEC-131
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
