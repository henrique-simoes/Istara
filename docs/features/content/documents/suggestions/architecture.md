---
stable_id: documents.suggestions
title: Document Suggestions
ui_path: Documents > Suggestions
audience: architecture
status: verified
related_features: ["documents.preview", "chat.overview"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/common/InteractiveSuggestionBox.tsx", "frontend/src/components/documents/DocumentsView.tsx", "frontend/src/lib/suggestionStream.ts"]
api_references: ["backend/app/api/routes/sessions.py", "backend/app/api/routes/chat.py"]
test_references: ["frontend/src/lib/suggestionStream.test.ts"]
last_verified: 2026-08-31
compass: CF-SPEC-53 / CF-657
---

# Document Suggestions Architecture

## Implementation Summary

Interactive suggestions create a project-scoped chat session and stream
provisional organization guidance for the current document library. The panel
shows immediate loading state, displays server-provided SSE failures, and
allows an active request to be cancelled through its request signal.

## Frontend Surface

- `frontend/src/components/common/InteractiveSuggestionBox.tsx`
- `frontend/src/components/documents/DocumentsView.tsx`
- `frontend/src/lib/suggestionStream.ts`

## State, API, And Backend Contracts

### Stores

- Local component state owns the suggestion session, message stream, visible
  error, and active `AbortController`.

### API And Backend

- `backend/app/api/routes/sessions.py` creates the project-scoped suggestion
  session.
- `backend/app/api/routes/chat.py` streams suggestion events through the same
  governed chat route used by Chat.

## Architecture Notes

- The feature is mounted through `frontend/src/components/common/InteractiveSuggestionBox.tsx` and the UI navigation path recorded in the inventory.
- Stream `error` events are terminal visible failures, including the
  credential/readiness guidance supplied by the server. They must never leave
  an empty assistant row or an apparently idle blank panel.
- The Stop control passes an `AbortSignal` into the active chat request. It is
  not a cosmetic streaming-state toggle.
- Suggestions remain provisional conversation output. Opening this panel does
  not mutate, rename, move, validate, or make a document reportable.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- RAG-related behavior depends on project context, documents, memory, or retrieval material referenced by the cited stores and routes.

## Tests And Verification

- `frontend/src/lib/suggestionStream.test.ts` covers ordered chunk accumulation,
  terminal SSE error propagation, and forwarding of the active abort signal.
- Published-UI verification covers the unavailable-model state: loading is
  visible and the server guidance replaces the prior empty panel.

## Related Features

- [documents.preview](../../documents/preview/architecture.md)
- [chat.overview](../../chat/overview/architecture.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
