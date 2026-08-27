---
stable_id: ensemble.health
title: Ensemble Health
ui_path: Ensemble Health
audience: architecture
status: documented
related_features: ["quality.dashboard", "compute.pool"]
related_glossary: ["fleiss-kappa"]
code_references: ["frontend/src/components/common/EnsembleHealthView.tsx", "backend/app/core/consensus.py", "backend/app/core/validation.py", "backend/app/core/validation_executor.py", "backend/app/core/adaptive_validation.py", "backend/app/core/pi_runtime/model_manager.py", "backend/app/core/agent_execution.py", "backend/app/core/compute_route_evidence.py", "backend/app/services/research_validity_service.py", "backend/app/services/synthetic_reconciliation_service.py", "backend/app/core/research_validity.py", "backend/app/models/research_validity.py", "backend/app/api/routes/code_applications.py", "backend/app/core/agentic/dispatcher.py"]
api_references: ["backend/app/api/routes/metrics.py", "backend/app/api/routes/research_validity.py", "backend/app/api/routes/code_applications.py"]
test_references: ["tests/test_adaptive_validation.py", "tests/test_validation_project_scope.py", "tests/test_evaluation_skill.py", "tests/test_research_validity_contract.py", "tests/test_metrics.py", "tests/test_code_applications.py", "tests/pi_production/test_w1_dispatcher_authority.py", "tests/pi_production/test_pi_model_manager_health.py", "tests/pi_production/test_legacy_long_horizon.py", "tests/pi_production/test_ensemble_identity_parity.py", "tests/pi_production/test_w7_validation.py", "tests/pi_production/test_w7_pi_manager_integration.py", "tests/pi_production/test_runtime_hardening.py", "tests/petals_bridge/test_petals_bridge.py", "tests/pi_production/test_research_spine_donor_routing.py", "tests/pi_benchmark/live_driver.py", "tests/pi_benchmark/test_live_driver.py", "tests/real_user_benchmark/lib/research-spine-probes.test.mjs"]
last_verified: 2026-08-27
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
- Dual-run, full-ensemble, debate, adversarial review, and Self-MoA validation metadata carry content-free route evidence when the serving compute path provides it. Ensemble samples preserve the provider-reported `served_model` identity alongside the endpoint, so the live MoA oracle can distinguish independent model checkpoints from endpoint replicas without guessing from request parameters. This lets telemetry and benchmarks distinguish which model/node served each validation pass without recording prompts, completions, private hosts, or tokens; missing identity remains unproven and cannot satisfy the independent-model gate.
- Debate and adversarial helpers now label their scope explicitly. Calls without `coding_run_id` are response-level quality signals and are not formal reliability; calls with coding-run/evidence-unit/codebook handles emit `debate.review` or `adversarial.review` telemetry for coded-evidence reconciliation.
- Dual-run, full-ensemble, and Self-MoA results explicitly emit `validation_scope=response_level_quality_signal`, `formal_reliability=false`, `research_spine_eligible=false`, and a heuristic-Kappa interpretation. The Evaluation Skill repeats that boundary in its provisional artifact instead of labeling response-category agreement as formal Fleiss' Kappa.
- Self-MoA results also preserve `models_used` from the provider-served route evidence, even though all temperature samples intentionally share one admitted endpoint/model. This keeps the single-model assurance boundary auditable without presenting temperature variation as independent Research Spine raters.
- Report section VII preserves the same boundary: stored consensus scores are disclosed as heuristic response-level quality signals and explicitly cannot establish formal Research Spine reliability. Formal Fleiss/Cohen/Krippendorff metrics are reported only from independent coded evidence-unit matrices in governed coding runs.
- The legacy `ValidationExecutor` rejects unknown validation-method names with an explicit failed/invalid result (`confidence=0`) instead of treating configuration or caller drift as a successful validation. This fail-closed behavior prevents an unrecognized method from being mistaken for Research Spine evidence.
- Qualitative coding prompts must include protected methodology, codebook, evidence-unit schema, reliability policy, and promotion gate blocks before any model codes evidence.
- Governed coding runs use Pi Model Management to select distinct healthy project-authorized model identities, execute independent coding passes, persist route evidence, and compute Fleiss/Krippendorff reliability on evidence-unit matrices. Each coder must cover every selected evidence unit after at most one bounded repair. This is the formal reliability path; response-level validation remains an operational quality signal.
- Adaptive response-level method selection uses the same project-scoped Pi Model Management catalog as the subsequent dispatcher call. Its identity-only inventory applies Petals allowlists and reserved-namespace admission without materializing settings credentials; the retired global `llm_router`/ComputeRegistry inventory is not an authority for choosing `dual_run` or `full_ensemble`.
- The default Research Spine coder path obtains the manager from the same AgenticDispatcher instance that performs each `validity.coder` structured dispatch. Selection and dispatch therefore share one Pi catalog authority; each selected coder also retains a non-secret endpoint-identity snapshot and fails closed before dispatch if the shared catalog changes. A missing accessor in a test double falls back only to the direct selector seam and is not a production path.
- Structured coder route evidence records the provider-reported model identity, and the coder fails closed when that identity is missing or differs from the Pi-selected model. A requested model parameter alone is never treated as proof of the model that served the judgment.
- Petals project authorization is enforced twice: Pi Model Management filters the projected catalog before selecting an endpoint, and the loopback bridge re-checks the request's project against the donor allowlist immediately before dispatch. Research-purpose traffic without an explicit project scope is rejected.
- The Petals route receipt survives the `PiExecutionService` frame mapper and `AgenticDispatcher` structured/ensemble/React result contracts, then is persisted by the Research Spine coder adapter. A successful donor judgment therefore remains attributable to `route_kind=petals_bridge`, its donor node, served model, and exact Pi endpoint instead of being relabeled as generic Pi traffic.
- The provider identity receipt is carried as `served_model` from the Pi response stream through the worker's `run.completed` frame, the Python engine, and the dispatcher. Providers or gateways that do not report an identity remain usable for ordinary turns, but cannot satisfy the independent Research Spine coder gate; the configured/request `model` is never substituted.
- Pi ensemble usage follows the same all-or-nothing exactness boundary as the legacy loop. When every sample has a provider receipt, the aggregate preserves input/output/cache/cost/total/turn counts exactly. If a real-provider sample is missing usage (including pi-ai's all-zero placeholder) or the ensemble is mixed, the shared ledger derives a complete whole-dispatch text estimate from preserved sample text and the public result is empty rather than partial; deterministic faux providers remain test-only exceptions.
- Petals streaming is a compatibility transport, not a second accounting authority: its terminal OpenAI-shaped chunk carries the donor's provider receipt when present, while missing receipts are explicitly estimated and marked in route evidence. This keeps donated samples subject to the same exact-versus-estimated boundary before an ensemble or Research Spine ledger can use them.
- The Istara/legacy ReAct loop preserves that same provider receipt on its returned outcome (`served_model`) while retaining the configured model separately. This keeps multi-turn tool-loop usage and route provenance comparable with the Pi loop when both are delegated through Pi Model Management.
- The reliability matrix rejects duplicate coder/Evidence Unit applications instead of unioning multiple model judgments into a synthetic vote; duplicate ratings remain visible for reconciliation and audit.
- Reliability matrices distinguish an absent/unrated coder cell from an explicit abstention. Missing or empty unmarked ratings make the matrix incomplete and force reconciliation before Fleiss' Kappa or its Krippendorff companion can be used; only an explicit abstention is retained as the `__abstain__` category.
- When required rater provenance is incomplete, the reliability result also exposes item-level `needs_reconciliation` statuses plus the exact `reconciliation_evidence_unit_ids`; direct audit consumers must not reconstruct this remediation set from the matrix.
- The isolated benchmark may opt into `POST /api/code-applications/{project_id}/synthetic-reconciliation` only with the container setting and `x-istara-synthetic-reconciliation: benchmark-v1`. It requires exact current-run coverage and source/evidence-unit/coder/model/route provenance, records `source=benchmark_synthetic` receipts, and leaves every code application `pending/unreconciled/blocked`; synthetic receipts are diagnostic evidence only and never substitute for the authenticated human review route. The API regression also invokes `assess_task_research_validity` after receipt creation and requires the report gate to remain blocked until human reconciliation.
- A synthetic diagnostic is idempotent per project/coding-run/diagnostic/application identity: deterministic receipt IDs and retry lookup return the original receipt without inserting duplicates. Reusing a diagnostic with a different decision payload or an incomplete receipt set is rejected; this retry path still cannot alter human review, promotion, Done-task, or reportability state.
- Current-run traceability acceptance is exact rather than structural: the benchmark requires the expected application count with unique application IDs and a coded evidence edge for every current-run application. Extra/duplicate rows or a missing `evidence_unit -> coded_as -> code_application` edge fail closed, so one valid edge cannot mask an incomplete graph.
- A single-category matrix has expected agreement 1.0, so Fleiss' Kappa is mathematically undefined even when raw agreement is perfect. Istara records the undefined reason and routes the run and its evidence units to reconciliation instead of reporting kappa 1.0 or promoting them.
- W7 routes the validation call sites through the shared `AgenticDispatcher` unconditionally: `agentic.ensemble` uses purposes `validation.dual_run` (two distinct endpoints), `validation.full_ensemble` (a compatibility `n=min+1` request whose governed minimum remains authoritative), and `validation.self_moa` (temperature samples with `distinct=False`); `agentic.completion` uses `validation.adversarial` and `validation.debate`; the structured judge uses `validation.judge`. The dispatcher remains the engine-resolution boundary. W9 retired the per-site preserved router/server/compute-registry branches: the dispatcher path is the only path, and both Istara (legacy) and Pi engine choices delegate ensemble selection and execution to the shared Pi Model Management authority. Pi resolves only the governed minimum because it has no spare-retry loop; if valid responses still fall below the minimum, the validation facade downgrades to `dual_run` instead of labeling a partial result `full_ensemble`. Failed samples remain visible in the underlying usage/telemetry records, but neither engine claims optional-spare recovery.
- `distinct=True` preserves endpoint pinning but scientific coder independence is a model-identity contract. Replicas serving the same model may improve availability but never count as separate Research Spine raters. If the Pi catalog cannot satisfy the requested distinct-model width, coding and formal reliability fail closed rather than fabricating diversity.
- Every governed rater column persists an effective identity: model/checkpoint, a non-secret provider-account handle, exact endpoint, prompt digest, codebook version, protected protocol version, and decoding profile. Missing fields or any identity change within a coding run force reconciliation. Provider/account/endpoint diversity is provenance, not a substitute for three distinct model/checkpoint identities; aliases or replicas of one model still count once.
- Each Pi coder call opens a fresh UUID-backed runtime session with no prior coder response in its history. Effective-rater provenance records `fresh_session_per_coder_call` and `provider_prefix_cache_no_response_reuse`: provider-side prompt-prefix computation may be reused, but conversation/output state is never shared as another model's judgment.
- Both loop modes use the Pi-governed embeddings gateway and canonical embedding identity. Engine selection changes orchestration semantics, not the provider/model authority or vector-space invariant.
- Real-user and Colima/Docker benchmarks must not enable strict single-model routing as their default architecture test. Strict routing is a technical isolation probe; the product-faithful benchmark observes the normal compute/model manager selecting and serving work across registered donors.
- Live benchmark acceptance is Docker-only: the Mac Studio is the Docker host and SSH control plane, while Istara, browser clients, relay clients, and donor model servers run in containers. The historical host-managed three-model probe is refused before live work and cannot produce acceptance evidence. The supported `scripts/runner/docker-run.sh` three-model profile marks the nested runner explicitly, starts the Compose-managed Gemma donor from an already-present Q4 file, mounts the model root read-only, starts the Qwen/Gemma-E2B llama.cpp donors through the nested Docker socket, and attaches relay/preflight clients to the project backend network. Container-side donor preflight retries within a bounded cold-load window so a healthy llama.cpp process is not rejected during model initialization; missing files, routes, or provider credit remain fail-closed blockers.
- The real-user benchmark's acceptance profile is an executable workload contract, not a label applied after a broad run. `provider` selects raw-corpus upload, Research Spine coding, reliability, grounding, reconciliation, and promotion; it does not start Petals relays or require chat/tasks/UI. `petals` selects slash-string/consent, container-side donor preflight, relay registration and health, served-route/usage proof, revocation, and cleanup; it does not claim provider-plane coding. `combined` selects both evidence planes plus the common chat/task/UI, integration, governed self-improvement workflow, and the two-call long-horizon workload. The runner records both requested and effective limits and emits unrelated workflow failures separately, so a skipped surface cannot quietly become an acceptance blocker or a Petals pass masquerade as ensemble validity. When combined acceptance requires long horizon, the disposable Docker runner exports an explicit completion receipt only after the Python workload succeeds; the Node scorecard accepts `long_horizon_verified` only when Docker-runner mode is active as well as the marker being present, blocks the blocker path when the receipt is absent or caller-supplied outside that mode, and keeps the combined acceptance row blocked rather than claiming verified provider/Petals-only evidence.
- The benchmark Research Spine oracle is fail-closed: coding and multi-model validation require the typed contract payload, while traceability, RAG, and telemetry signals require their non-empty structural fields (`report_gate`/counts, synthesis contract and promotion rule, and `status=ok` policy/protected-field metadata). Truthy empty objects, an accepted coding response without the contract, or a provider health response alone cannot be reported as research evidence.
- Each persisted code application must also carry a substantive open-code payload: a non-empty governed `code_id`, a non-empty analytic `reasoning` memo, and a bounded numeric confidence. When an evidence unit supplies source offsets, the application must preserve matching start/end offsets; empty ORM defaults or paraphrase-only rows cannot satisfy the ensemble gate.
- The acceptance oracle also validates reliability-metric domains before applying thresholds: Fleiss/Cohen kappa must be finite and within `[-1, 1]`, while Krippendorff alpha must be finite and no greater than `1` (negative alpha remains a valid disagreement signal). Impossible numeric values fail closed instead of certifying a malformed adapter or fixture response.
- The historical opt-in `tests/integration/test_llm_orchestration_real.py` is companion evidence for one-profile orchestration ergonomics only. It is not an ensemble or Research Spine acceptance oracle: it does not prove Pi Model Management routing, three provider-served identities, source-grounded coder coverage, Fleiss/Krippendorff reliability, reconciliation, or human-approved report promotion. Those claims require `tests/pi_benchmark/live_driver.py` and the Docker-only real-user `provider`/`combined` profiles.
- The release-facing ensemble contract names the acceptance metrics explicitly: provider-served model identity, exact source-span grounding, Fleiss' kappa, Krippendorff's alpha, reconciliation status, and human Done/report promotion. Companion metrics such as DAG success, latency, and compute capacity cannot substitute for any of those Research Spine gates.
- The benchmark also independently recomputes served model identities from the coding run's route receipt. A backend-reported `distinct_model_count` cannot satisfy the three-rater gate unless the served route evidence contains the same number of non-empty, distinct model identities; missing, aliased, or inconsistent receipts fail closed before reconciliation is treated as proven.
- The live benchmark driver applies the same route admission to ordinary one-call units as to MoA units: an approved endpoint alone is insufficient. Every successful sample must carry an explicit provider-served model identity, and a proxy-substituted identity is rejected even when the configured/request label is the approved model. Projected `pi-petals-*` routes are admitted only with a non-empty served identity and the Petals provider marker.
- Docker benchmark provenance is fail-closed before workload startup: `scripts/runner/docker-run.sh` recomputes the canonical `git archive --format=tar HEAD` SHA-256 with an already-installed `shasum`/`sha256sum` utility and rejects a caller-supplied snapshot digest that does not match the mounted source. This binds each container-only run to the exact detached checkout instead of treating a digest-shaped environment value as proof.
- Provider acceptance is fail-closed at both the blocker and scorecard boundaries: `codingValidation` is not sufficient by itself. A verified provider gate requires coding, independent multi-model validation, and Research Spine traceability flags together; inconsistent feature payloads are reported as blocked so a partial run cannot be certified, and the live blocker path emits the same missing-multi-model failure before exit status can pass. The exported accepted-validation score and history field use that same conjunction rather than copying the coding flag alone.
- Generated project-scoped connection strings are revoked in the same Docker-owned run before the final scorecard. The revocation artifact distinguishes generated credentials from externally supplied overrides and records every confirmed, unexpected, skipped, or failed result; cleanup is incomplete when a generated credential cannot be confirmed inactive.
- A bounded live Research Spine proof must page through the project evidence inventory, prefer raw substantive spans from distinct source documents when the corpus provides them, and persist the selected evidence-unit IDs and source count. Source diversity is a sampling preference and observability field, not a three-document reliability gate: one source document may legitimately provide multiple independent spans. Coding the first rows in source order is not valid proof because one document's titles, project metadata, protocol boilerplate, or adjacent spans can otherwise bias the sample.
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
- `tests/real_user_benchmark/lib/research-spine-probes.test.mjs` — paginated source-diverse substantive-span selection, complete coder-by-evidence-unit coverage, per-application raw-span/served-model provenance, multi-model route diversity, and numeric Fleiss/Krippendorff proof.
- `tests/test_research_validity_pagination.py` — bounded evidence-unit pagination used by the live proof.
- `tests/pi_production/test_w7_validation.py` — dispatcher purpose/verb mapping, legacy parity, endpoint-pinned distinctness, actual Pi Model Management-backed coding selection, fail-closed degradation, and judge unavailability. W8 embedding dispatch and gateway behavior are covered by `tests/pi_production/test_w8_embeddings_gateway.py`.
- `tests/pi_production/test_w1_dispatcher_authority.py` — legacy/Istara multi-turn and seven-step long-horizon tool-loop parity over a real `PiModelManager`; verifies per-round manager resolution, accumulated tool-result history, cumulative usage, governed horizon behavior, and provider-served identity.
- `tests/pi_production/test_legacy_long_horizon.py` — isolated seven-step legacy horizon oracle, kept separate from the complexity-heavy authority module while preserving the same real `PiModelManager` seam.
- `tests/pi_production/test_ensemble_identity_parity.py` — `legacy` plus every public Pi selector alias (`pi`, `pi-candidate`, `pi-replacement`, `deepseek-pi`) use one real `PiExecutionService`/`PiModelManager` authority and preserve three distinct provider-served identities separately from configured request labels; this is provenance/authority coverage, not live model-quality or Fleiss/Krippendorff evidence.
- `tests/pi_production/test_pi_ensemble_accounting.py` — real dispatcher/manager/ledger seam proves mixed Pi usage is estimated as one complete dispatch and fully reported Pi samples retain cache, cost, total, and turn accounting.
- `tests/real_user_benchmark/lib/scoring.test.mjs` and `tests/real_user_benchmark/lib/topology-contract.test.mjs` — deterministic workload/scorecard and Docker-wrapper contracts fail closed when the combined long-horizon receipt is missing.
- `tests/benchmarks/long_horizon_runner.py` — the two-turn long-horizon workload must name
  `legacy` or `pi` explicitly and validates every content-free `chat_turn` identity row
  returned for the requested session, including the exact session handle, so a query-filter
  regression, latest-row-only response, or mixed-engine result cannot be reported as engine
  parity.
- `scripts/runner/docker-run.sh` and `scripts/runner/inside.sh` — the combined Docker
  acceptance profile invokes that Python workload inside the disposable runner image for
  each engine arm, persists one log per engine, and leaves provider/Petals-only profiles
  scoped to their transport/donation gates.

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
