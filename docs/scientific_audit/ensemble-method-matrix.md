# Ensemble Method Matrix

Spec: CF-SPEC-123 / CF-1581

| Method | Implementation Surface | Current Behavior | Classification | Action |
| --- | --- | --- | --- | --- |
| Compute-aware default selection | `backend/app/core/adaptive_validation.py` | Chooses full ensemble when 3+ distinct healthy project-authorized models exist, dual-run when 2 exist, and Self-MoA when constrained. | Scientifically aligned as orchestration policy | Documented in README and feature docs. |
| Full ensemble / Mixture-of-Agents inspired validation | `backend/app/core/validation.py` | Calls up to 3 diverse healthy authorized servers and computes consensus over responses. | Acceptable heuristic | README now says MoA-inspired validation, not guaranteed formal MoA layering. |
| Dual-run validation | `backend/app/core/validation.py` | Uses two diverse healthy servers when available; falls back to Self-MoA if fewer than two responses. | Scientifically reasonable heuristic | Keep tests focused on project scope and diversity. |
| Self-MoA fallback | `backend/app/core/validation.py` | Repeats one model with temperature variation and consensus scoring. | Acceptable constrained-compute fallback | README now frames as fallback signal. |
| Adversarial review | `backend/app/core/validation.py` | One draft response and one critique/refinement pass. | Acceptable heuristic | Do not claim this alone proves consensus. |
| Debate rounds | `backend/app/core/validation.py` | Iterative refinement using router calls; may reuse the same model depending router state. | Test gap / docs caveat | Future improvement: record route identity per debate round and prefer distinct models when available. |
| Fleiss' Kappa formula | `backend/app/core/consensus.py` | Standard formula over an N x category-count matrix. | Scientifically faithful formula | Keep formula tests. |
| Fleiss' Kappa input semantics | `backend/app/core/consensus.py` | Matrix is built from keyword-category presence across LLM responses. | Acceptable heuristic, misleading if called formal inter-rater reliability | Runtime metadata and docs now state `kappa_basis=category_presence_by_response`. |
| Kappa >= 0.60 enforcement | `backend/app/core/agent_execution.py` | Consensus score is recorded; low/borderline scores can trigger refinement and human review, but there is no strict Kappa >= 0.60 promotion gate. | README stale claim fixed | Do not add tests that require strict Kappa gating unless product code intentionally changes. |
| Low-consensus promotion | `backend/app/core/agent_execution.py`, reports code | Task output still enters review flow; Reports are gated by approved Done task findings. | Human-in-loop architecture | README/docs now point to Done-task report eligibility. |
| Route/model identity evidence | `backend/app/core/validation.py`, compute registry counters | Full ensemble and dual-run record server names. Debate path route evidence is weaker. | Partial coverage | Future improvement: record per-validation call route evidence across all methods. |
