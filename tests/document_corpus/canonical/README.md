# Canonical Synthetic UX Research Corpus

This committed corpus is Istara's source of truth for product-level synthetic research tests.

Project: CareNav Renewal
Source count: 174
Long-form sources: 174
Approximate total words: 2,716,595
Average words per source: 15,613
Sources with at least 10,000 words/row-word equivalents: 114
Skill definitions covered by manifest: 58

## Contract

- Product-level document, research, task, Findings, Reports, benchmark, simulation, eval, and marathon tests use this corpus or a manifest-backed named slice.
- Canonical sources must remain compatible with Istara upload/processable file types so benchmark failures test product behavior, not bad fixture formats.
- Tiny ad hoc fixtures are allowed only for parser/unit tests and must be labeled as unit fixtures.
- Raw corpus sources are not report-ready evidence. Reports are generated only from Findings derived from approved Done tasks.
- Raw Markdown sources must look like plausible source artifacts, not pre-digested candidate evidence, coding hints, canned implications, or report paragraphs.
- Interview sources must preserve coherent participant IDs, timestamped speaker turns, monotonic transcript positions, varied participant quotes, and language/content consistency.
- The corpus is fully synthetic and contains no private data.
- The corpus is intentionally large enough to stress retrieval, coding, task review, summarization, report gating, and multi-model route evidence.
- Run `python scripts/public_repo_quality_audit.py --check` with corpus tests before merging corpus or public-doc changes.

## Named slices

- interview-heavy: 54 sources across diary, field-note, interview, participant-profile
- coding-reliability: 70 sources across diary, field-note, interview, participant-profile, support, survey
- low-consensus-review: 67 sources across accessibility, field-note, heuristic, interview, malformed, support, usability
- full-end-to-end: 174 sources across ab-test, accessibility, analytics, brief, card-sort, competitor, consent, diary, field-note, guide, heuristic, interview, journey, laws-of-ux, malformed, multilingual, nps, participant-profile, plan, report, stakeholder, support, survey, sus, tree-test, umux, usability
- graph-synthesis: 52 sources across ab-test, analytics, brief, competitor, diary, journey, report, stakeholder, survey
- usability-heavy: 14 sources across usability
- survey-heavy: 26 sources across analytics, nps, survey, sus, umux
- findings-reporting: 33 sources across ab-test, analytics, journey, report, stakeholder, support
- accessibility-heavy: 14 sources across accessibility, heuristic, laws-of-ux
- upload-smoke: 8 sources across guide, plan
- multilingual: 7 sources across consent, multilingual
- malformed-edge-case: 3 sources across malformed

## Regeneration

Run `node tests/document_corpus/generate-canonical-corpus.mjs` from the repo root after intentional corpus contract changes.