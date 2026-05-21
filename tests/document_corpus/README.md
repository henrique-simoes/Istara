# Istara Test Document Corpus

This folder is the source-of-truth harness for tests that need realistic UX research documents.

## Canonical Contract

- `tests/document_corpus/canonical/` is the committed canonical synthetic UX research corpus.
- Product-level document, research, task, Findings, Reports, benchmark, simulation, eval, and marathon tests use the canonical corpus or a manifest-backed named slice from it.
- Tiny ad hoc corpora are acceptable only for narrow parser/unit tests where document content is not product behavior. Those tests must be labeled as unit/parser fixtures.
- Raw corpus sources are not report-ready. Reports should use findings produced from approved Done tasks, not tasks still in review.

## Canonical Assets

- `canonical/manifest.json`: source metadata, Double Diamond phase, method, participants, tags, skills, slices, and byte counts.
- `canonical/README.md`: human-readable corpus contract.
- `canonical/playbook.md`: how to use slices in tests.
- `canonical/skill-coverage-map.json`: mapping from Istara skills to representative corpus sources.
- `canonical/expected-evidence-chain.json`: report-readiness and Done-task gating contract.
- `generate-canonical-corpus.mjs`: deterministic rebuild script.

## Named Slices

Use `tests/document_corpus/shared-corpus.mjs` to select material:

- `full-end-to-end`
- `interview-heavy`
- `survey-heavy`
- `usability-heavy`
- `accessibility-heavy`
- `findings-reporting`
- `multilingual`
- `malformed-edge-case`
- `upload-smoke`

## Usage

Import `materializeSharedDocumentCorpus` or `selectCanonicalCorpus` from `tests/document_corpus/shared-corpus.mjs`.

For product-level research tests, pass `canonicalOnly: true` so failures cannot be hidden by generated fallback sources:

```js
const corpus = materializeSharedDocumentCorpus({
  outputDir,
  slice: "full-end-to-end",
  minimumSources: 120,
  canonicalOnly: true,
});
```

The helper still contains a legacy curated/generated fallback for older narrow callers, but benchmark and document-heavy product tests should not use it for representative scoring.
