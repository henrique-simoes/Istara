---
stable_id: ensemble.health
title: Ensemble Health
ui_path: Ensemble Health
audience: architecture
status: documented
related_features: ["quality.dashboard", "compute.pool"]
related_glossary: ["fleiss-kappa"]
code_references: ["frontend/src/components/common/EnsembleHealthView.tsx", "backend/app/core/consensus.py", "backend/app/core/validation.py", "backend/app/core/validation_executor.py", "backend/app/core/agent_execution.py", "backend/app/core/compute_route_evidence.py", "backend/app/services/research_validity_service.py", "backend/app/core/research_validity.py", "backend/app/models/research_validity.py", "backend/app/core/agentic/dispatcher.py"]
api_references: ["backend/app/api/routes/metrics.py", "backend/app/api/routes/research_validity.py"]
test_references: ["tests/test_validation_project_scope.py", "tests/test_evaluation_skill.py", "tests/test_research_validity_contract.py", "tests/test_metrics.py", "tests/pi_production/test_w1_dispatcher_authority.py", "tests/pi_production/test_w7_validation.py"]
last_verified: 2026-07-22
compass: CF-SPEC-8 / FIX-pi-full-20260720-w7-REVIEW-r1-docs; CF-SPEC-53 / CF-657; CF-SPEC-92 / CF-1170; CF-SPEC-122; CF-SPEC-123 / CF-1581; CF-SPEC-124 / CF-1590
---

# Ensemble Health Architecture

## Implementation Summary

Ensemble Health surfaces health and consensus signals for Istara's multi-model or multi-agent ensemble behavior.

## Frontend Surface

- `frontend/src/components/common/EnsembleHealthView.tsx`
- `backend/app/core/consensus.py`
- `backend/app/core/validation.py`
- `backend/app/core/agent_execution.py`

## State, API, And Backend Contracts

### Stores

- None recorded.

### API And Backend

- `backend/app/api/routes/metrics.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/common/EnsembleHealthView.tsx` and the UI navigation path recorded in the inventory.
- Project-bound ensemble validation must carry the active `project_id` into adversarial review, self-MoA, full ensemble, debate rounds, model-server selection, and validation embeddings, so donated relay/browser compute is only selected when authorized for that project.
- When a project has multiple healthy authorized model endpoints, adaptive validation selects Istara's natural multi-model path: three or more distinct available models use full ensemble/Fleiss' Kappa, two models use dual-run validation, and Self-MoA is reserved for constrained single-model conditions.
- The research-validity path computes Fleiss' Kappa, Cohen's Kappa, and Krippendorff's Alpha over coded evidence-unit matrices. The legacy LLM consensus path may still provide operational response-level agreement, but it must not be described as formal qualitative coding reliability.
- Low or borderline consensus does not automatically become report evidence. Validation metadata is stored on task output, borderline outputs can trigger refinement or reconciliation, and report eligibility still depends on accepted evidence plus approved Done tasks.
- Dual-run, full-ensemble, debate, adversarial review, and Self-MoA validation metadata carry content-free route evidence when the serving compute path provides it. This lets telemetry and benchmarks distinguish which model/node served each validation pass without recording prompts, completions, private hosts, or tokens.
- Debate and adversarial helpers now label their scope explicitly. Calls without `coding_run_id` are response-level quality signals and are not formal reliability; calls with coding-run/evidence-unit/codebook handles emit `debate.review` or `adversarial.review` telemetry for coded-evidence reconciliation.
- Qualitative coding prompts must include protected methodology, codebook, evidence-unit schema, reliability policy, and promotion gate blocks before any model codes evidence.
- Governed coding runs use Compute Manager to select distinct healthy project-authorized model identities, execute independent coding passes, persist route evidence, and compute Fleiss/Cohen/Krippendorff-style reliability on evidence-unit matrices. This is the formal reliability path; response-level validation remains an operational quality signal.
- W7 routes the validation call sites through the shared `AgenticDispatcher` when `agentic_core` is enabled: `agentic.ensemble` uses purposes `validation.dual_run` (two distinct endpoints), `validation.full_ensemble` (the requested minimum width plus one optional spare), and `validation.self_moa` (temperature samples with `distinct=False`); `agentic.completion` uses `validation.adversarial` and `validation.debate`; the structured judge uses `validation.judge`. The dispatcher remains the engine-resolution boundary, while the preserved router/server/compute-registry branches remain available when the flag is off or the resolved engine is legacy. For a legacy-resolved full ensemble, the minimum width is authoritative: a healthy distinct server is only used as the optional spare when an earlier sample fails.
- `distinct=True` is an endpoint-identity contract, not a model-name contract. Multiple endpoints serving the same model remain independent route identities; if the Pi catalog cannot satisfy the requested distinct width, validation fails closed rather than fabricating diversity. Dual-run degrades to the labeled Self-MoA path and full ensemble degrades through dual-run; dispatch failures produce an empty/unavailable validation result. The structured judge returns `passed=False` with an unavailable reason when dispatch or a usable verdict is missing, so unavailable validation cannot become report evidence.
- W7 deliberately leaves `validation.py:_get_embeddings` on the legacy plane. Embedding dispatch is deferred to W8 and must not be treated as a missing W7 migration.
- Real-user and Colima/Docker benchmarks must not enable strict single-model routing as their default architecture test. Strict routing is a technical isolation probe; the product-faithful benchmark observes the normal compute/model manager selecting and serving work across registered donors.
- Validation calls without project context remain server-owned/local only; cross-project compute aggregation is reserved for explicit admin-only surfaces.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Ensemble LLM calls must preserve project scope when validating task output or skill artifacts.
- Full ensemble reliability requires distinct serving endpoint identities. Reusing one endpoint as if it were multiple independent raters is rejected as lower assurance.
- For W7, the concrete independence unit is the serving endpoint identity. Same-model endpoints are valid independent raters only when their endpoint identities are distinct and preserved in route evidence; a missing or insufficient endpoint set is lower assurance and remains unavailable/blocked.
- Rollback is reversible: disable `settings.agentic_core` or select the legacy engine for the project. The preserved legacy branches then serve validation without changing the legacy schemas or behavior.

## Tests And Verification

- `tests/test_validation_project_scope.py`
- `tests/test_evaluation_skill.py`
- `tests/test_research_validity_contract.py`
- `tests/pi_production/test_w7_validation.py` — dispatcher purpose/verb mapping, legacy parity, endpoint-pinned distinctness, fail-closed degradation, judge unavailability, and W8 embedding deferral.

## Related Features

- [quality.dashboard](../../quality/dashboard/architecture.md)
- [compute.pool](../../compute/pool/architecture.md)

## Related Concepts

- [fleiss-kappa](../../../glossary/fleiss-kappa.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657; CF-SPEC-92 / CF-1170; CF-SPEC-122; CF-SPEC-123 / CF-1581; CF-SPEC-124 / CF-1590
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
