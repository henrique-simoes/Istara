# Article Collaboration Protocol

Status: required for durable OpenClaw job
Date: 2026-07-19

## Intent

The three architects should write the academic documentation together. The process must not
pick one model's article and discard the others. It should converge through section ownership,
cross-review, and incremental judging.

## Roles

- Architect A: Istara baseline and feature-contract evidence.
- Architect B: Pi replacement feasibility and package-boundary evidence.
- Architect C: methodology, metrics, statistics, reproducibility, and threats to validity.
- Conductor/editor: integrates sections, preserves disagreements, tracks evidence, and
  prevents unsupported claims.

## Article Files

Use small Markdown files under `comparison-Istara-pi/article/`:

- `outline.md`
- `research-questions.md`
- `systems-under-comparison.md`
- `methodology.md`
- `benchmark-suite.md`
- `metrics-and-statistics.md`
- `results-placeholder.md`
- `qualitative-trace-analysis.md`
- `best-practices-and-migration.md`
- `threats-to-validity.md`
- `reproducibility-appendix.md`
- `review-ledger.md`

Do not write final empirical claims until evidence exists. Use `TBD-evidence` markers with
the expected artifact path.

## Incremental Judging

Each article section must pass these checks before being marked ready:

- Traceability: every benchmark claim cites a source file or generated artifact.
- Scope fidelity: full agentic-core replacement hypothesis is represented.
- Feature preservation: Istara feature behavior remains an acceptance criterion.
- Secret hygiene: no API keys, headers, private prompts, or uncapped outputs.
- Method validity: paired scenarios, shared tools, shared model policy, capped randomness.
- Reproducibility: manifest/scenario/trace/output/score artifact paths are named.
- Storage discipline: no large raw logs or screenshots unless explicitly justified.

The judge must append to `article/review-ledger.md` instead of overwriting prior critiques.

## Score Before Prose Polish

For each section, record:

- `evidence_coverage`: 0-1.
- `methodological_rigor`: 0-1.
- `migration_relevance`: 0-1.
- `readability`: 0-1.
- `risk_honesty`: 0-1.

Sections with any score below 0.75 remain draft.

## Output Style

Write like an academic systems/evaluation article, but keep the project-grounded engineering
appendix rich enough that a future implementation agent can build the lab.
