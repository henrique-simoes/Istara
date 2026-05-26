# Canonical Corpus Playbook

Use `tests/document_corpus/shared-corpus.mjs` rather than reading this folder directly. The helper exposes manifest-backed selectors so tests can ask for `interview-heavy`, `survey-heavy`, `usability-heavy`, `accessibility-heavy`, `findings-reporting`, `multilingual`, `malformed-edge-case`, `upload-smoke`, `coding-reliability`, `graph-synthesis`, `low-consensus-review`, or `full-end-to-end` material.

Historical slash-style aliases such as `findings/reporting` and `malformed/edge-case` are normalized by the shared helper; manifests store canonical hyphenated names.

## Research process

The synthetic program follows a Double Diamond flow: discover sources capture interviews, diary studies, support tickets, and field notes; define sources capture surveys, card sorting, tree testing, analytics, and stakeholder tensions; develop sources capture usability, heuristic, accessibility, and Laws of UX work; deliver sources capture A/B tests, privacy review, multilingual review, malformed exports, and report-readiness material.
Support-ticket exports are represented as CSV in the canonical upload path because `.jsonl` is not an Istara document upload format.

## Evidence flow

Tests should upload or ingest these sources, create or execute research tasks, let agent outputs move into review, and only treat findings as report-eligible after humans approve the task into Done.

## Speed guidance

Use a named slice for focused tests and reserve `full-end-to-end` for benchmark, marathon, and representative document-heavy scenarios.