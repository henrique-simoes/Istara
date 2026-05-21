# README Claim Truth Matrix

Spec: CF-SPEC-123 / CF-1581

| Claim Area | Previous Risk | Current Wording / Implementation Alignment | Status |
| --- | --- | --- | --- |
| Academic-grade multi-model validation | README implied formal MoA plus formal Fleiss' Kappa inter-coder reliability and strict Kappa >= 0.60 promotion. | README now describes compute-aware multi-model validation, heuristic consensus, route evidence, and human review. | Fixed wording. |
| Fleiss' Kappa | Formula is correct, but input matrix is heuristic category presence. | Runtime metadata and docs now disclose `category_presence_by_response`. | Fixed transparency. |
| Self-MoA | Could be read as equivalent to multi-model ensemble. | README now describes it as constrained-compute fallback. | Fixed wording. |
| Petals-inspired compute relay | README could imply Petals-style layer sharding. | README/docs now clarify whole-request routing over project-scoped donor nodes. | Fixed wording. |
| No hallucinated insights | Overstated guarantee. | README now says evidence-constrained with source links, validation metadata, and human rejection of weak work. | Fixed wording. |
| Atomic Research chain | Strong method alignment, but report eligibility needed explicit Done-task gate. | README and feature docs now state reports use approved Done task findings; In Review is not report evidence. | Fixed wording. |
| AURA/interview channels | README implied real channel deployment without credentials. | README now says live participant channels require provider credentials or bounded simulators. | Fixed wording. |
| Connection strings | README.pt-BR still showed old JWT URL form. | README.pt-BR now uses `rcl_<convite-assinado-de-usuario-ou-computacao>` and notes no pre-minted user JWT. | Fixed wording. |
| Canonical research material | Product-level tests previously mixed runtime generated sources and small fixtures. | Canonical corpus exists under `tests/document_corpus/canonical/`; harness supports named slices and canonical-only materialization. | Implemented. |
