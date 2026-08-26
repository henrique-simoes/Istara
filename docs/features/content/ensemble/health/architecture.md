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
test_references: ["tests/test_validation_project_scope.py", "tests/test_evaluation_skill.py", "tests/test_research_validity_contract.py", "tests/test_metrics.py", "tests/pi_production/test_w1_dispatcher_authority.py", "tests/pi_production/test_w7_validation.py", "tests/petals_bridge/test_petals_bridge.py", "tests/pi_production/test_research_spine_donor_routing.py"]
last_verified: 2026-08-26
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
- Governed Research Spine coding requires three or more distinct model identities and computes reliability on their complete evidence-unit matrices. Two-model dual-run and one-model Self-MoA remain operational response-quality signals only; neither can promote research evidence.
- The research-validity path computes Fleiss' Kappa, Cohen's Kappa, and Krippendorff's Alpha over coded evidence-unit matrices. The legacy LLM consensus path may still provide operational response-level agreement, but it must not be described as formal qualitative coding reliability.
- Low or borderline consensus does not automatically become report evidence. Validation metadata is stored on task output, borderline outputs can trigger refinement or reconciliation, and report eligibility still depends on accepted evidence plus approved Done tasks.
- Dual-run, full-ensemble, debate, adversarial review, and Self-MoA validation metadata carry content-free route evidence when the serving compute path provides it. This lets telemetry and benchmarks distinguish which model/node served each validation pass without recording prompts, completions, private hosts, or tokens.
- Debate and adversarial helpers now label their scope explicitly. Calls without `coding_run_id` are response-level quality signals and are not formal reliability; calls with coding-run/evidence-unit/codebook handles emit `debate.review` or `adversarial.review` telemetry for coded-evidence reconciliation.
- Dual-run, full-ensemble, and Self-MoA results explicitly emit `validation_scope=response_level_quality_signal`, `formal_reliability=false`, `research_spine_eligible=false`, and a heuristic-Kappa interpretation. The Evaluation Skill repeats that boundary in its provisional artifact instead of labeling response-category agreement as formal Fleiss' Kappa.
- Qualitative coding prompts must include protected methodology, codebook, evidence-unit schema, reliability policy, and promotion gate blocks before any model codes evidence.
- Governed coding runs use Pi Model Management to select distinct healthy project-authorized model identities, execute independent coding passes, persist route evidence, and compute Fleiss/Krippendorff reliability on evidence-unit matrices. Each coder must cover every selected evidence unit after at most one bounded repair. This is the formal reliability path; response-level validation remains an operational quality signal.
- Reliability matrices distinguish an absent/unrated coder cell from an explicit abstention. Missing or empty unmarked ratings make the matrix incomplete and force reconciliation before Fleiss' Kappa or its Krippendorff companion can be used; only an explicit abstention is retained as the `__abstain__` category.
- A single-category matrix has expected agreement 1.0, so Fleiss' Kappa is mathematically undefined even when raw agreement is perfect. Istara records the undefined reason and routes the run and its evidence units to reconciliation instead of reporting kappa 1.0 or promoting them.
- W7 routes the validation call sites through the shared `AgenticDispatcher` unconditionally: `agentic.ensemble` uses purposes `validation.dual_run` (two distinct endpoints), `validation.full_ensemble` (the requested minimum width plus one optional spare), and `validation.self_moa` (temperature samples with `distinct=False`); `agentic.completion` uses `validation.adversarial` and `validation.debate`; the structured judge uses `validation.judge`. The dispatcher remains the engine-resolution boundary. W9 retired the per-site preserved router/server/compute-registry branches: the dispatcher path is the only path, and a legacy-resolved engine is served exclusively by the dispatcher's permanent legacy executor. For a legacy-resolved full ensemble, the minimum width is authoritative: a healthy distinct server is only used as the optional spare when an earlier sample fails, and satisfying that minimum records aggregate success while retaining the failed sample detail for telemetry.
- `distinct=True` preserves endpoint pinning but scientific coder independence is a model-identity contract. Replicas serving the same model may improve availability but never count as separate Research Spine raters. If the Pi catalog cannot satisfy the requested distinct-model width, coding and formal reliability fail closed rather than fabricating diversity.
- Every governed rater column persists an effective identity: model/checkpoint, a non-secret provider-account handle, exact endpoint, prompt digest, codebook version, protected protocol version, and decoding profile. Missing fields or any identity change within a coding run force reconciliation. Provider/account/endpoint diversity is provenance, not a substitute for three distinct model/checkpoint identities; aliases or replicas of one model still count once.
- Each Pi coder call opens a fresh UUID-backed runtime session with no prior coder response in its history. Effective-rater provenance records `fresh_session_per_coder_call` and `provider_prefix_cache_no_response_reuse`: provider-side prompt-prefix computation may be reused, but conversation/output state is never shared as another model's judgment.
- Both loop modes use the Pi-governed embeddings gateway and canonical embedding identity. Engine selection changes orchestration semantics, not the provider/model authority or vector-space invariant.
- Real-user and Colima/Docker benchmarks must not enable strict single-model routing as their default architecture test. Strict routing is a technical isolation probe; the product-faithful benchmark observes the normal compute/model manager selecting and serving work across registered donors.
- Live benchmark acceptance is Docker-only: the Mac Studio is the Docker host and SSH control plane, while Istara, browser clients, relay clients, and donor model servers run in containers. The historical host-managed three-model probe is refused before live work and cannot produce acceptance evidence.
- A bounded live Research Spine proof must page through the project evidence inventory, prefer raw substantive spans from distinct source documents, and persist the selected evidence-unit IDs and source count. Coding the first rows in source order is not valid proof because one document's titles, project metadata, protocol boilerplate, or adjacent spans can otherwise stand in for corpus diversity.
- Validation calls without project context remain server-owned/local only; cross-project compute aggregation is reserved for explicit admin-only surfaces.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Ensemble LLM calls must preserve project scope when validating task output or skill artifacts.
- Full ensemble reliability requires at least three distinct model identities with exact endpoint and route provenance. Reusing an endpoint or same-model replica as another rater is rejected.
- Rollback is reversible: select the legacy engine for the project (or keep `settings.agentic_engine_default` at `legacy`). The dispatcher's permanent legacy executor then serves validation without changing the legacy schemas or behavior; W9 removed the per-site legacy fallback branches, so engine choice no longer changes the code path.

## Tests And Verification

- `tests/test_validation_project_scope.py`
- `tests/test_evaluation_skill.py`
- `tests/test_research_validity_contract.py`
- `tests/real_user_benchmark/lib/research-spine-probes.test.mjs` — paginated source-diverse substantive-span selection, exact evidence-unit provenance, multi-model route diversity, and numeric Fleiss/Krippendorff proof.
- `tests/test_research_validity_pagination.py` — bounded evidence-unit pagination used by the live proof.
- `tests/pi_production/test_w7_validation.py` — dispatcher purpose/verb mapping, legacy parity, endpoint-pinned distinctness, fail-closed degradation, and judge unavailability. W8 embedding dispatch and gateway behavior are covered by `tests/pi_production/test_w8_embeddings_gateway.py`.

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
