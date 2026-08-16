# Architect Lane Passes

This subagent run could not safely spawn additional child sessions, so the collaboration is
preserved as three separated passes grounded in the prior architect files.

## Architect A - Istara Baseline And Feature Contracts

Istara's replacement bar is not "the answer looks plausible." Pi must preserve documented
feature behavior and the concrete contracts around project scoping, task/finding/document
state, memory redaction, A2A authorization, telemetry, and graceful failure. The generated
`feature-matrix.json` uses `docs/features/inventory.json` as the feature source of truth and
links every row to a required later evidence artifact.

## Architect B - Pi Package Replacement Feasibility

The comparison stays focused on `@earendil-works/pi-coding-agent`,
`@earendil-works/pi-agent-core`, and `@earendil-works/pi-ai`. The direct Pi provider smoke is
not run in this job because the package is not locally installed; installing it would change
the storage/dependency profile and requires owner approval. The preferred next spike is a
minimal dependency-gated Pi checkout or package install outside Istara application code, then
a single `@earendil-works/pi-ai` DeepSeek call.

## Architect C - Methodology And Reproducibility

The lab remains paired, trace-first, and storage-capped. Deterministic validators run before
paid LLM benchmarks. Live results must report token usage, latency, feature coverage, and
bootstrap-ready per-scenario scores. Article claims stay marked `TBD-evidence` until the
trace and score artifacts exist.

## Integrated Judge Notes

- Scope fidelity: pass for full agentic-core replacement framing.
- Feature preservation: pass at matrix skeleton level; empirical pass/fail remains
  `TBD-evidence`.
- Secret hygiene: pass at artifact level; the key was checked by boolean and read only inside
  the smoke process.
- Method validity: draft-pass; later paired benchmarks need budget, package setup, and a frozen
  scenario corpus.
- Storage discipline: pass for this smoke run.

