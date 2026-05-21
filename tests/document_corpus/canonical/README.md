# Canonical Synthetic UX Research Corpus

This committed corpus is Istara's source of truth for product-level synthetic research tests.

Project: CareNav Renewal
Source count: 174
Long-form sources: 174
Skill definitions covered by manifest: 58

## Contract

- Product-level document, research, task, Findings, Reports, benchmark, simulation, eval, and marathon tests use this corpus or a manifest-backed named slice.
- Tiny ad hoc fixtures are allowed only for parser/unit tests and must be labeled as unit fixtures.
- Raw corpus sources are not report-ready evidence. Reports are generated only from Findings derived from approved Done tasks.
- The corpus is fully synthetic and contains no private data.

## Named slices

- interview-heavy: 54 sources across diary, field-note, interview, participant-profile
- full-end-to-end: 174 sources across ab-test, accessibility, analytics, brief, card-sort, competitor, consent, diary, field-note, guide, heuristic, interview, journey, laws-of-ux, malformed, multilingual, nps, participant-profile, plan, report, stakeholder, support, survey, sus, tree-test, umux, usability
- usability-heavy: 14 sources across usability
- survey-heavy: 26 sources across analytics, nps, survey, sus, umux
- findings-reporting: 33 sources across ab-test, analytics, journey, report, stakeholder, support
- accessibility-heavy: 14 sources across accessibility, heuristic, laws-of-ux
- upload-smoke: 8 sources across guide, plan
- multilingual: 7 sources across consent, multilingual
- malformed-edge-case: 3 sources across malformed

## Regeneration

Run `node tests/document_corpus/generate-canonical-corpus.mjs` from the repo root after intentional corpus contract changes.