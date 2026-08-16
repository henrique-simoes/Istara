# Review Ledger

## 2026-07-19T10:56:18-03:00 - Durable DeepSeek Conductor Initial Pass

Reviewer: conductor/editor

Scores:

- `outline.md`: evidence_coverage 0.80; methodological_rigor 0.80; migration_relevance
  0.90; readability 0.85; risk_honesty 0.90.
- `research-questions.md`: evidence_coverage 0.80; methodological_rigor 0.85;
  migration_relevance 0.95; readability 0.85; risk_honesty 0.90.
- `systems-under-comparison.md`: evidence_coverage 0.80; methodological_rigor 0.80;
  migration_relevance 0.90; readability 0.85; risk_honesty 0.90.
- `methodology.md`: evidence_coverage 0.78; methodological_rigor 0.85; migration_relevance
  0.85; readability 0.80; risk_honesty 0.90.
- `benchmark-suite.md`: evidence_coverage 0.76; methodological_rigor 0.80; migration_relevance
  0.85; readability 0.80; risk_honesty 0.90.
- `metrics-and-statistics.md`: evidence_coverage 0.76; methodological_rigor 0.82;
  migration_relevance 0.80; readability 0.80; risk_honesty 0.90.
- `results-placeholder.md`: evidence_coverage 0.75; methodological_rigor 0.80;
  migration_relevance 0.80; readability 0.85; risk_honesty 0.95.
- `qualitative-trace-analysis.md`: evidence_coverage 0.75; methodological_rigor 0.80;
  migration_relevance 0.80; readability 0.80; risk_honesty 0.90.
- `best-practices-and-migration.md`: evidence_coverage 0.76; methodological_rigor 0.78;
  migration_relevance 0.90; readability 0.82; risk_honesty 0.95.
- `threats-to-validity.md`: evidence_coverage 0.80; methodological_rigor 0.85;
  migration_relevance 0.80; readability 0.85; risk_honesty 0.95.
- `reproducibility-appendix.md`: evidence_coverage 0.78; methodological_rigor 0.82;
  migration_relevance 0.80; readability 0.82; risk_honesty 0.90.

Notes:

- The article skeleton is acceptable as a pre-results draft.
- Comparative quality claims remain blocked on paired benchmark evidence.
- Pi provider execution remains blocked on dependency setup approval.

## 2026-07-19T11:50:57-03:00 - Pi Provider Smoke Method Update

Reviewer: pi-provider-smoke-subagent

Scores:

- `methodology.md`: evidence_coverage 0.82; methodological_rigor 0.86; migration_relevance
  0.88; readability 0.82; risk_honesty 0.92.
- `results-placeholder.md`: evidence_coverage 0.78; methodological_rigor 0.82;
  migration_relevance 0.82; readability 0.85; risk_honesty 0.95.

Notes:

- Pi provider execution is no longer blocked on dependency setup.
- Comparative quality claims remain blocked on a separated replacement harness plus capped
  paired benchmark evidence.
- The provider smoke is prerequisite dependency/provider evidence only; it is not a
  standalone replacement result.

## 2026-07-19T12:08:00-03:00 - Replacement Worktree Method Update

Reviewer: replacement-worktree-subagent

Scores:

- `methodology.md`: evidence_coverage 0.86; methodological_rigor 0.88; migration_relevance
  0.92; readability 0.82; risk_honesty 0.94.
- `systems-under-comparison.md`: evidence_coverage 0.84; methodological_rigor 0.84;
  migration_relevance 0.92; readability 0.84; risk_honesty 0.94.
- `results-placeholder.md`: evidence_coverage 0.82; methodological_rigor 0.84;
  migration_relevance 0.86; readability 0.85; risk_honesty 0.96.

Notes:

- The comparison now has a first replacement-harness prototype, not only provider smoke.
- Countable replacement evidence is limited to the `chat.tool_loop.task_and_finding`
  lab scenario through Pi `Agent` and canonical Istara task/finding tools.
- Comparative quality claims and broad replacement conclusions remain blocked on capped
  paired benchmarks through the sidecar.

## 2026-07-19T12:12:49-03:00 - Replacement Worktree CF Remediation

Reviewer: replacement-worktree-subagent

Scores:

- `methodology.md`: evidence_coverage 0.88; methodological_rigor 0.89; migration_relevance
  0.93; readability 0.82; risk_honesty 0.95.
- `results-placeholder.md`: evidence_coverage 0.84; methodological_rigor 0.85;
  migration_relevance 0.87; readability 0.85; risk_honesty 0.96.

Notes:

- Added CF-backed dependency maps for chat/tool loop, task planning/execution,
  model/provider routing, memory/RAG, A2A, and channels.
- Recorded CF state limitations instead of treating CF as only a status check.
- Fixed one DeepSeek key lifecycle issue in the sidecar during remediation.
