# Harbor Ledger rich corpus ("Northloop small-business banking redesign")

**Fully synthetic test fixtures.** Every person, business, quote, number, and
event is authored by `generate-rich-corpus.mjs` (seeded, deterministic — same
seed yields byte-identical output). There are no real participants here.

## Why synthetic instead of scraped public materials

We surveyed freely-available sources first: methodology guides exist in the
open (18F's human-centered design methods, GOV.UK research and design-system
material under the Open Government Licence, standard SUS/UMUX instruments),
but no freely-licensed public corpus offers dozens of deep, mutually coherent,
full-length interview transcripts with known ground truth. Scraping real
research data into a test suite would raise consent/licensing/PII problems and
still leave us without answer keys. So the corpus is **methodologically shaped
by those public sources, with all content generated**: it gives us what scraped
data cannot — planted theme distributions, known survey means and SUS scores,
declared contradictions, and stale markers, all recorded in `manifest.json`
as machine-checkable ground truth for eval scenarios.

## Contents (75 files, ~11,000 lines)

| Area | Files | Notes |
|---|---|---|
| `sources/interview/` | 16 transcripts, 414–503 lines each | EN + ES (P04, P08, P13), per-persona voices, theme stances |
| `sources/survey/` | 120 responses CSV + computed analysis | Means in manifest are ground truth |
| `sources/usability/` | 8 sessions with raw SUS items + scores | P16 accessibility-depressed scores honest |
| `sources/support/` | 30 tickets | Severity, channel, theme links |
| `sources/analytics/` | 8-week funnel + dictionary | W19 dip explained (stale-after-fix) |
| `sources/competitor/` | 3 benchmark reports | Trial-based, no scraping |
| `sources/journey/` | 2 journey maps | Invoice chase, month-end close |
| `sources/plan/` + `sources/guide/` | program plan, 3 discussion guides | |
| `method/codebook-v1.md` | 10-theme codebook | Method artifact, not a finding |
| `context/` | 4 packs, 250–488 lines each | Project context, guardrails, personas, objectives |
| `chat-packs/` | 3 exemplar threads (38–52 turns) | Labeled method exemplars with steering, not evidence |

## Regenerate

```bash
node tests/document_corpus/generate-rich-corpus.mjs [--out DIR]
```

Default output is `tests/document_corpus/rich/`. Consumers read via
`tests/document_corpus/rich-corpus.mjs` (`selectRichCorpus`,
`richGroundTruth`). Slices: interview/survey/usability-heavy, full-end-to-end,
coding-reliability, context-pack, chat-packs.
