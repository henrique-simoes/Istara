# Scientific Audit Artifacts

Spec: CF-SPEC-123 / CF-1581

This folder records the durable audit results for the ensemble validation, compute donation, README claim, bibliography, and canonical corpus effort started on 2026-05-21.

Files:

- `ensemble-method-matrix.md`: implementation truth table for validation methods and scientific claims.
- `compute-donation-matrix.md`: compute manager, relay donation, and Petals-inspired architecture classification.
- `readme-claim-truth-matrix.md`: README and README.pt-BR claim audit.
- `bibliography-audit.md`: primary source references and wording guidance.

Key outcome:

- Istara naturally defaults to full ensemble when 3+ distinct healthy project-authorized models are visible, dual-run when 2 are visible, and Self-MoA when compute is constrained.
- Fleiss' Kappa uses a correct formula, but current LLM-output consensus feeds it heuristic keyword-category presence labels, not a human-coded item-by-rater research matrix.
- Compute donation is project-scoped whole-request routing over local/network/relay nodes. It is Petals-inspired, not transformer layer sharding.
- Reports should use findings from approved Done tasks. In Review tasks are not report evidence.
- Product-level synthetic research tests should use `tests/document_corpus/canonical/` through `tests/document_corpus/shared-corpus.mjs`.
