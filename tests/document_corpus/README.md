# Shared Istara Test Document Corpus

This folder is the source-of-truth harness for tests that need realistic UX research documents.

Istara tests should use this shared corpus whenever the behavior under test depends on documents, transcripts, surveys, field notes, evidence grounding, task outputs, Findings, or Reports. Small ad hoc corpora are acceptable only for narrow parser/unit tests where the document content itself is not part of the product behavior.

## Contract

- Realistic benchmark and simulation runs should expose at least 120 long-form research sources unless a test explicitly documents a smaller unit-test fixture.
- Sources should include interviews/transcripts, usability studies, surveys, analytics, support tickets, diary studies, field notes, competitive notes, multilingual examples, and edge cases.
- The real-user benchmark materializes this corpus through `tests/document_corpus/shared-corpus.mjs`, reusing curated fixtures from `tests/simulation/data/fixtures` and `tests/fixtures`, then generating additional long UX research sources if needed.
- Tests that evaluate agentic research, document retrieval, task execution, Findings, or Reports should assert against this shared-corpus contract instead of quietly uploading 10 or 20 documents and treating that as representative.

## Usage

Import `materializeSharedDocumentCorpus` from `tests/document_corpus/shared-corpus.mjs` and pass the destination run folder plus any existing manifest entries. The helper copies long curated fixtures, generates enough additional sources to satisfy the minimum, and returns manifest entries shaped like the real-user benchmark upload manifest.
