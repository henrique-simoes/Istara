# Istara Test Document Corpus

This folder is the source-of-truth harness for tests that need realistic UX research documents.

## Canonical Contract

- `tests/document_corpus/canonical/` is the committed canonical synthetic UX research corpus.
- Product-level document, research, task, Findings, Reports, benchmark, simulation, eval, and marathon tests use the canonical corpus or a manifest-backed named slice from it.
- Canonical product-level sources must use Istara upload-processable file types. Unsupported research archive formats belong in parser/unit fixtures or require product ingestion support before entering the canonical upload path.
- Tiny ad hoc corpora are acceptable only for narrow parser/unit tests where document content is not product behavior. Those tests must be labeled as unit/parser fixtures.
- Raw corpus sources are not report-ready. Reports should use findings produced from approved Done tasks, not tasks still in review.
- Canonical raw sources must look like plausible source artifacts, not pre-digested candidate evidence blocks, coding hints, canned implications, or report paragraphs.
- Interview sources must preserve coherent participant IDs, timestamped speaker turns, monotonic transcript positions, varied participant quotes, and language/content consistency.
- Live harnesses should begin from `scripts/reset_test_environment.py` when they need clean users/projects/artifacts, then create their own suite-specific projects from canonical sources.

## Canonical Assets

- `canonical/manifest.json`: source metadata, Double Diamond phase, method, participants, tags, skills, slices, byte counts, and word counts.
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
- `coding-reliability`
- `graph-synthesis`
- `low-consensus-review`

Slash-style aliases are accepted for historical prompt wording:

- `findings/reporting` -> `findings-reporting`
- `malformed/edge-case` -> `malformed-edge-case`

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

## Depth Standard

The canonical corpus is intentionally large. It currently contains 174 synthetic upload-compatible sources, every source is long-form, and the manifest records more than 2.5 million words/row-word equivalents. Interviews are modeled as extended transcript-scale raw sources with speaker turns, timestamps, coherent participant IDs, and method-specific contradictions. Product-level benchmark prompts assume this material is rich enough to test retrieval, evidence-unit extraction, coding reliability, GraphRAG traceability, task review, report gating, and multi-model route evidence.

Do not shrink the corpus back into small prompt fixtures. If a future test needs speed, use a named slice or limit selector; if a future product feature needs a new method, add realistic source depth to the generator and regenerate the manifest.

Run these quality gates after intentional corpus changes:

```bash
node --test tests/document_corpus/shared-corpus.test.mjs
python scripts/public_repo_quality_audit.py --check
```

## Clean Local Test State

For destructive local harness setup:

```bash
ISTARA_DESTRUCTIVE_TEST_RESET=1 python scripts/reset_test_environment.py \
  --confirm DELETE-ISTARA-LOCAL-TEST-DATA --researchers 2
```

This seeds admin `admin` / `istara123` and optional `researcher_N` accounts, deletes benchmark/simulation result folders, leaves zero projects, and refuses non-local database URLs. The protected `LLMs/` and `Model_Finetuning/` folders are never deleted.
