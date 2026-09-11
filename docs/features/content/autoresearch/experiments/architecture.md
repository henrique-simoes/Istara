---
stable_id: autoresearch.experiments
title: Autoresearch Experiments
ui_path: Autoresearch > Experiments
audience: architecture
status: documented
related_features: ["autoresearch.dashboard", "autoresearch.config", "chat.model-controls"]
related_glossary: ["triangulation"]
code_references: ["frontend/src/components/autoresearch/AutoresearchView.tsx", "backend/app/core/autoresearch_engine.py", "backend/app/core/autoresearch_runners/__init__.py", "backend/app/core/autoresearch_runners/model_temp.py", "backend/app/core/autoresearch_runners/persona.py", "backend/app/core/autoresearch_runners/question_bank.py", "backend/app/core/autoresearch_runners/skill_prompt.py", "backend/app/core/autoresearch_runners/ui_sim.py", "backend/app/core/agentic/dispatcher.py", "backend/app/core/pi_runtime/model_manager.py"]
api_references: ["backend/app/api/routes/autoresearch.py"]
test_references: ["tests/test_autoresearch.py", "tests/test_project_scope_contracts.py", "tests/pi_production/test_w6_autoresearch_runners.py"]
last_verified: 2026-09-02
compass: CF-SPEC-60 / CF-754; CF-SPEC-68 / CF-870; CF-SPEC-96 / CF-1226; CF-SPEC-8 (Pi replacement W6)
---

# Autoresearch Experiments Architecture

## Implementation Summary

Experiments configure and inspect automated research runs across strategies or parameters.

## Frontend Surface

- `frontend/src/components/autoresearch/AutoresearchView.tsx`
- `backend/app/core/autoresearch_engine.py`
- `backend/app/core/autoresearch_runners/__init__.py`
- `backend/app/core/autoresearch_runners/question_bank.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/autoresearchStore.ts`
- Experiment history and start/stop actions are bound to the active project id; the store returns an empty experiment list instead of issuing an unscoped request when no project is active.

### API And Backend

- `backend/app/api/routes/autoresearch.py`
- Experiment list, start, and stop routes require `project_id` and enforce project access. Autoresearch engine records and broadcasts the experiment project id, and experiment history filters by `AutoresearchExperiment.project_id`.
- Starting an experiment requires the requested project to be active and unpaused before the runner is constructed or scheduled. The engine records the active project owner for the whole run, including baseline measurement, and repeats the active-project check before baseline and iteration work so a paused or missing project cannot keep processing in the background.
- A start request with `dry_run: true` is non-mutating for every caller, including callers that do not select the Pi replacement engine: it returns a dry-run response and never schedules a background loop. The request still validates `loop_type` against the six installed runners, so an unknown loop name is rejected consistently with a live run. Pi-selected dry runs additionally record the governed Pi telemetry span.
- A Pi-selected governed turn that reaches `error` or `aborted` fails closed with a typed 503 before any candidate proposal or fallback hypothesis is created; partial streamed output is not an experiment artifact.
- The engine binds the authorized project id into each loop runner before baseline measurement. Question-bank runners then load and update `ResearchDeployment` rows by both deployment id and that bound project id, so a stale deployment id from another project cannot be measured, mutated, reverted, or sent into LLM evaluation.

### Agentic Dispatcher Migration (Pi Replacement W6)

- Pi Replacement wave W6 (master plan `docs/build-stream/plans/2026-07-20-pi-full-replacement-master-plan.md` §8 W6, spec CF-SPEC-8) routes the autoresearch loop runners' own internal LLM calls through the shared `AgenticDispatcher` (`backend/app/core/agentic/dispatcher.py`, module singleton `agentic`) instead of calling `app.core.llm_router.llm_router.chat` directly. It migrates the 14 runner call sites across the six loop runners (`model_temp`, `persona`, `question_bank`, `rag_params`, `skill_prompt`, `ui_sim`) while experiment orchestration, persistence, governance, and project scope stay unchanged.
- Engine selection is per experiment. The start boundary accepts an explicit `engine` of `pi` or `legacy`, validates it, and binds the choice once to every runner. When it is unset, autoresearch resolves the choice from the global `settings.agentic_core` flag (`pi` when enabled, otherwise `legacy`); runner call sites do not re-read that flag. Every runner call is issued unconditionally through the shared dispatcher as `agentic.completion(purpose="autoresearch.<runner>.<step>", project_id=..., spine_phase=..., engine=self.engine)`, which fails closed on a selected engine that cannot execute and never silently falls back. The generic dispatcher precedence for callers that do not provide this bound per-experiment override is documented on [chat.model-controls](../../chat/model-controls/architecture.md). W9 retired the preserved per-site `llm_router.chat` branches: a legacy-resolved run is served by the dispatcher's permanent legacy executor, which preserves the pre-dispatcher behavior.
- Which engine actually executed each runner turn stays auditable per run through the durable usage ledger (`backend/app/core/agentic/usage_ledger.py`): every dispatcher call records one content-free accounting row plus a short identity-only trace span `route_id="agentic:<engine>:<endpoint|node|unresolved>"`, so a Pi run and a legacy run of the same experiment are distinguishable in the accounting plane without exposing prompts, responses, or endpoint secrets.
- All 14 sites use the `completion` verb; the purpose slug and Research Spine phase per site are:
  - `model_temp._evaluate_skill` — candidate skill run → `autoresearch.model_temp.evaluate` (spine phase `execution`).
  - `model_temp._score_output` — LLM-as-judge score → `autoresearch.model_temp.score` (spine phase `review`).
  - `persona.hypothesize` — persona-file mutation → `autoresearch.persona.hypothesize` (spine phase `plan`).
  - `persona._evaluate_agent` — simulated-task run → `autoresearch.persona.evaluate` (spine phase `execution`).
  - `persona._score_response` — response-quality score → `autoresearch.persona.score` (spine phase `review`).
  - `question_bank.hypothesize` — question-bank improvement → `autoresearch.question_bank.hypothesize` (spine phase `plan`).
  - `question_bank._evaluate_questions` — simulated participant → `autoresearch.question_bank.evaluate` (spine phase `execution`).
  - `question_bank._score_responses` — elicited-response score → `autoresearch.question_bank.score` (spine phase `review`).
  - `rag_params._llm_hypothesis` — next-parameter suggestion → `autoresearch.rag_params.hypothesize` (spine phase `plan`).
  - `skill_prompt.hypothesize` — skill-prompt mutation → `autoresearch.skill_prompt.hypothesize` (spine phase `plan`).
  - `skill_prompt._single_eval` — sample skill run → `autoresearch.skill_prompt.evaluate` (spine phase `execution`).
  - `skill_prompt._score_output` — skill-output score → `autoresearch.skill_prompt.score` (spine phase `review`).
  - `ui_sim.hypothesize` — component accessibility/UX mutation → `autoresearch.ui_sim.hypothesize` (spine phase `plan`).
  - `ui_sim._evaluate_component` — WCAG-style component score → `autoresearch.ui_sim.evaluate` (spine phase `review`).
- Model/temperature sweep semantics (`model_temp.py`): `_build_grid` sources the `(model, temperature)` grid from `PiModelManager` for both loop modes, covering settings endpoints, read-only legacy-row projections, local serving, and admitted Petals identities. The selected engine changes dispatcher/loop semantics only; it never selects a different model catalog. Each candidate stays pinned to its exact endpoint for reproducibility. Endpoint replicas may remain separate experimental cells, but this sweep identity is not Research Spine coder independence: same-model replicas still count as one model for formal reliability.
- RAG retrieval-eval embedding migrated in W8: the `_score_single_query` (`embed_text`) call inherits the W8 `agentic.embed` dispatch like every other embed consumer (legacy engine → the unchanged `ollama.embed*` plane via the dispatcher's permanent legacy executor; Pi engine → the W8 embeddings gateway).
- Governance and project scope are unchanged. The governed `pi_governed` autoresearch mode remains the only path by which a Pi turn can *propose* experiments; W6 only changes the transport of the runners' internal calls once a human has already started an experiment, and the `governance_required` / no-promotion gates are untouched. The authorized project id the engine binds into each runner before baseline measurement is the id carried into every migrated `agentic.completion` call (engine resolution, telemetry, and execution scope), never a caller-supplied target, so a Pi runner turn cannot execute or account against a different project than the one that authorized the experiment.
- Rollback: select the `legacy` engine for the project (or keep the legacy global default) and every runner is served by the dispatcher's permanent legacy executor with no schema or behavior change. W9 retired the per-site legacy branches, so the count-to-zero ratchet is 0: the dispatcher path is the only path in product code.

## Architecture Notes

- The feature is mounted through `frontend/src/components/autoresearch/AutoresearchView.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Autoresearch experiments can mutate strategies that later affect agents, skills, LLM choice, RAG behavior, question banks, or UI simulations. Each experiment must remain attached to the project that authorized it.
- Paused projects are execution-stop boundaries for autoresearch: no baseline measurement, mutation, model-choice exploration, reasoning memory, or improvement proposal should be produced after the project is paused.
- Baseline and candidate measurements run inside the autoresearch isolation context, so experiment probes do not write normal learning, skill-stat, or self-improvement evidence until they are explicitly promoted through project-bound governance.
- Candidate mutations are reverted after measurement even when they improve the score. A successful iteration is recorded as `proposal_ready`: it may create a governed improvement proposal, but it does not leave prompt, persona, UI, RAG, model, deployment, or skill state mutated in production.
- Model/temperature exploration writes project-scoped measurement evidence only. It does not update the global best-model config directly; applying a preferred configuration must go through improvement governance.
- Completed project-scoped experiments emit content-free `autoresearch.validity_update` telemetry after persistence. The event records project, loop type, agent handle, status, and score only; hypotheses, mutation bodies, prompts, and experiment text remain out of telemetry.

## Tests And Verification

- `tests/test_autoresearch.py` verifies start/stop routing, runner project binding, and project-scoped question-bank deployment behavior.
- `tests/test_project_scope_contracts.py` verifies the frontend and backend keep experiment requests project-bound.
- `tests/pi_production/test_seams_fail_closed.py` verifies error and abort terminals, including failures after partial output, cannot create Pi candidate proposals.
- `tests/pi_production/test_w6_autoresearch_runners.py` verifies the W6/W9 runner contract: all 14 runner sites use `agentic.completion` with the expected purpose and spine phase, contain no direct `llm_router.chat` branch, forward the bound engine and project scope, and preserve Istara execution semantics through the dispatcher. It also verifies that both engine choices source the `model_temp` sweep from Pi Model Management, filter embedding models, preserve same-model endpoint identities, reject a legacy catalog read, and record `sweep_truncated` for a narrow or empty catalog. The W8 embedding wrapper and gateway behavior is covered by `tests/pi_production/test_w8_embeddings_gateway.py`; the count-to-zero ratchet is asserted at 0 by `tests/pi_migration/test_count_to_zero.py`.
- Regenerate and validate the machine manifests and static site with `python scripts/feature_docs.py --seed-missing --generate-site --check`.

## Related Features

- [autoresearch.dashboard](../../autoresearch/dashboard/architecture.md)
- [autoresearch.config](../../autoresearch/config/architecture.md)
- [chat.model-controls](../../chat/model-controls/architecture.md)

## Related Concepts

- [triangulation](../../../glossary/triangulation.md)

## Compass Evidence

- Spec/task: CF-SPEC-60 / CF-754; CF-SPEC-68 / CF-870; CF-SPEC-96 / CF-1226; CF-SPEC-8 (Pi replacement W6 autoresearch-runner dispatcher migration)
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
