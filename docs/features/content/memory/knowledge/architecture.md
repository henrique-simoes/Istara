---
stable_id: memory.knowledge
title: Knowledge Memory
ui_path: Memory > Knowledge
audience: architecture
status: documented
related_features: ["memory.agent", "memory.context-dag", "documents.library"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/memory/MemoryView.tsx", "frontend/src/lib/memoryApi.ts", "backend/app/api/routes/memory.py", "backend/app/core/file_watcher.py", "backend/app/evals/retrieval_eval.py"]
api_references: ["backend/app/api/routes/memory.py"]
test_references: ["tests/test_memory.py", "tests/test_spine_single_ingestion.py", "tests/test_spine_chunking_parameters.py", "tests/test_spine_retrieval_eval.py"]
last_verified: 2026-09-26
compass: CF-SPEC-60 / CF-757
---

# Knowledge Memory Architecture

## Implementation Summary

The Memory knowledge tab manages project knowledge artifacts and retrieval material for the active project.

## Frontend Surface

- `frontend/src/components/memory/MemoryView.tsx`
- `frontend/src/lib/memoryApi.ts`
- `backend/app/api/routes/memory.py`

## State, API, And Backend Contracts

### Stores

- None recorded.

### API And Backend

- `backend/app/api/routes/memory.py`

## Ingestion, Chunking And Measured Retrieval (2026-09-25)

- **One writer per uploaded file.** The upload route owns an upload's ingestion (Document, evidence
  units, both indices) and creates its research tasks from the plaintext before encryption. The
  file watcher, which also watches every project's upload directory, skips managed uploads: indexing
  them too raced the route and left two copies of each chunk in the vector store (2,134 rows for
  1,097 spans on the Harbor Ledger corpus). Reprocess cleans existing duplicates.
- **Uploads are classified by the researcher's file name.** An upload is stored as `<uuid>.<ext>`,
  so the task rules keyed on the name (interview, survey, usability, field notes, diary, competitor)
  never matched it; the route now passes the original name for classification and task titles. An
  upload does not raise the watcher's sticky "new research file" suggestion (the upload has its own
  confirmation; stacked suggestions covered the Memory tabs at 375 px). Files dropped into a watched
  folder still raise it.
- **Chunking parameters mean what they say.** `chunk_overlap=0` is zero (it used to become the
  default 180), a chunk size must be positive, and the splitter always advances, so a large overlap
  can no longer loop forever.
- **Measured retrieval.** `python -m app.evals.retrieval_eval evaluate|ablate|budget` measures
  nDCG@10, Recall@10 and MRR@10 with bootstrap intervals on span-graded qrels over the Harbor Ledger
  corpus, with paired randomization tests (Holm) for ablations and budget recall per context
  window. Results with the local nomic-embed-text embedder are in
  `docs/build-stream/2026-09-25-spine-findings-evidence.md` (measurements 1-3); the five-embedder
  comparison behind the BGE-M3 default (DEC-15) is in the same file.

## Architecture Notes

- The feature is mounted through `frontend/src/components/memory/MemoryView.tsx` and the UI navigation path recorded in the inventory.
- `backend/app/api/routes/memory.py` validates project visibility before opening vector or keyword memory storage, so unknown or unauthorized project ids cannot create or inspect memory indexes.
- `frontend/src/components/memory/MemoryView.tsx` remounts project-backed memory tabs when the active project changes so local chunks, search results, notes, and health state do not linger across projects.
- Memory source rows, health breakdowns, filters, search results, and chunks resolve uploaded document metadata to a human-readable title (with the filename as a disambiguator); the canonical source path remains in the DOM title and is still used for filtering and deletion.
- If document metadata cannot be loaded, the UI safely falls back to the source basename without blocking memory browsing.
- Search results render their hybrid rank (`data-testid=memory-result-rank`) rather than the reciprocal-rank-fusion sum, which ranges about 0.005-0.02 and read as "1.6%" for the best match. `KeywordIndex.search` runs the exact-phrase query first and fills top-k from the all-terms query, keeping two-character tokens; `VectorStore.delete_file_source` deletes both the full-path and basename spellings of a source, so reprocess is idempotent. Pinned by `tests/test_retrieval_correctness_fixes.py` and simulation scenario `85-retrieval-correctness`.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- RAG-related behavior depends on project context, documents, memory, or retrieval material referenced by the cited stores and routes.

## Tests And Verification

- `tests/test_memory.py`

## Related Features

- [memory.agent](../../memory/agent/architecture.md)
- [memory.context-dag](../../memory/context-dag/architecture.md)
- [documents.library](../../documents/library/architecture.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Compass Evidence

- Spec/task: CF-SPEC-60 / CF-757
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
