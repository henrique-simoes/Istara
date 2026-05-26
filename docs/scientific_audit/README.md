# Scientific Audit Artifacts

Spec: CF-SPEC-123 / CF-1581; CF-SPEC-124 / CF-1590

This folder records the durable audit results for the ensemble validation, compute donation, README claim, bibliography, and canonical corpus effort started on 2026-05-21.

Files:

- `ensemble-method-matrix.md`: implementation truth table for validation methods and scientific claims.
- `compute-donation-matrix.md`: compute manager, relay donation, and Petals-inspired architecture classification.
- `readme-claim-truth-matrix.md`: README and README.pt-BR claim audit.
- `bibliography-audit.md`: primary source references and wording guidance.
- `../architecture/research-validity-contract.md`: non-negotiable source-of-truth contract for qualitative coding, reliability, retrieval, telemetry, review, and reporting.

Key outcome:

- Istara naturally defaults to full ensemble when 3+ distinct healthy project-authorized models are visible, dual-run when 2 are visible, and Self-MoA when compute is constrained.
- Fleiss' Kappa, Cohen's Kappa, and Krippendorff's Alpha now have a research-validity contract and support helpers for coded evidence-unit matrices. Heuristic final-response consensus must not be described as formal qualitative coding reliability.
- Compute donation is project-scoped whole-request routing over local/network/relay nodes. It is Petals-inspired, not transformer layer sharding.
- Reports should use findings from approved Done tasks. In Review tasks are not report evidence.
- Hybrid RAG is the exact-evidence layer. Evidence Graph / GraphRAG is the synthesis and traceability layer and cannot bypass coding, reliability, human review, Done-task gating, or reports-only-from-Done rules.
- Product-level synthetic research tests should use `tests/document_corpus/canonical/` through `tests/document_corpus/shared-corpus.mjs`.
