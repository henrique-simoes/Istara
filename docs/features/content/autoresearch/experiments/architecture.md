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
last_verified: 2026-07-22
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
- A start request with `dry_run: true` is non-mutating for every caller, including callers that do not select the Pi replacement engine: it returns a dry-run response and never schedules a background loop. Pi-selected dry runs additionally record the governed Pi telemetry span.
- A Pi-selected governed turn that reaches `error` or `aborted` fails closed with a typed 503 before any candidate proposal or fallback hypothesis is created; partial streamed output is not an experiment artifact.
- The engine binds the authorized project id into each loop runner before baseline measurement. Question-bank runners then load and update `ResearchDeployment` rows by both deployment id and that bound project id, so a stale deployment id from another project cannot be measured, mutated, reverted, or sent into LLM evaluation.

### Agentic Dispatcher Migration (Pi Replacement W6)

- Pi Replacement wave W6 (master plan `docs/build-stream/plans/2026-07-20-pi-full-replacement-master-plan.md` §8 W6, spec CF-SPEC-8) routes the autoresearch loop runners' own internal LLM calls through the shared `AgenticDispatcher` (`backend/app/core/agentic/dispatcher.py`, module singleton `agentic`) instead of calling `app.core.llm_router.llm_router.chat` directly. It migrates the 14 runner call sites across the six loop runners (`model_temp`, `persona`, `question_bank`, `rag_params`, `skill_prompt`, `ui_sim`) while experiment orchestration, persistence, governance, and project scope stay unchanged.
- Engine selection is per experiment. Each runner resolves Pi or legacy for the run, defaulting to the global `settings.agentic_core` flag (`pi` when enabled, otherwise `legacy`) when the experiment does not pin an engine of its own. On the Pi engine a runner call is issued through the shared dispatcher as `agentic.completion(purpose="autoresearch.<runner>.<step>", project_id=..., spine_phase=...)`; the dispatcher is the single choke point that resolves the concrete engine and endpoint and fails closed on a selected engine that cannot execute, never silently falling back to the other engine (see [chat.model-controls](../../chat/model-controls/architecture.md) for the full engine-selection precedence — per-call override, then the `x-istara-agent-engine` header, then the project `agentic_engine` setting, then `settings.agentic_engine_default`). On the legacy engine the preserved `llm_router.chat` branch in every site runs verbatim, byte-for-byte as before the wave.
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
- Model/temperature sweep semantics (`model_temp.py`, master plan §8 W6 design decision 1): on the Pi engine `_build_grid` sources the `(model, temperature)` grid from the `PiModelManager` catalog (`backend/app/core/pi_runtime/model_manager.py` — settings endpoints, projected `LLMServer` rows, and local Ollama/LM Studio entries) rather than `llm_router.list_models()`, so the sweep space is the Pi plane's catalog identities and is not degenerate with a single endpoint. Each swept candidate is pinned by its exact catalog endpoint identity so two endpoints serving the same model stay distinct sweep cells instead of collapsing to one, and the dispatcher resolves the precise endpoint rather than a bare model name; embedding models are excluded from the sweep. A sweep that cannot span at least two distinct models is recorded as `sweep_truncated` (logged) instead of being silently narrowed, and an empty catalog yields an empty grid with `sweep_truncated` set; the legacy engine keeps sweeping the `llm_router` model list unchanged (no endpoint identity).
- RAG retrieval-eval embedding stays legacy until W8 (`rag_params.py`, master plan §8 W6 design decision 2): only the `_llm_hypothesis` chat call migrates to `agentic.completion`. The retrieval-eval embedding in `_score_single_query` (`embed_text`) is deliberately left on the legacy plane and is never routed through `agentic.embed` until the W8 embeddings gateway lands; the count-to-zero migration allowlist tracks that chat site and that embed site separately so the deferral is an explicit, tracked decision rather than a missed site.
- Governance and project scope are unchanged. The governed `pi_governed` autoresearch mode remains the only path by which a Pi turn can *propose* experiments; W6 only changes the transport of the runners' internal calls once a human has already started an experiment, and the `governance_required` / no-promotion gates are untouched. The authorized project id the engine binds into each runner before baseline measurement is the id carried into every migrated `agentic.completion` call (engine resolution, telemetry, and execution scope), never a caller-supplied target, so a Pi runner turn cannot execute or account against a different project than the one that authorized the experiment.
- Rollback: set `settings.agentic_core` to `False` (or select the `legacy` engine for the project) and every runner falls back to its preserved `llm_router.chat` branch with no schema or behavior change; the count-to-zero ratchet stays at 70 because the legacy branches are preserved rather than retired.

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
- `tests/pi_production/test_w6_autoresearch_runners.py` verifies the W6 migration: every one of the 14 runner sites carries both the flag-gated `agentic.completion` dispatcher path (correct purpose slug and valid spine phase) and the preserved legacy `llm_router.chat` branch; the flag-off path uses the legacy plane exactly as before and never touches the dispatcher; the flag-on path records the call (verb, purpose, bound project scope, spine phase) and never touches the legacy plane; the `model_temp` Pi sweep builds its grid from the `PiModelManager` catalog with embeddings filtered and records `sweep_truncated` for degenerate/empty catalogs; the `rag_params` retrieval-eval embedding stays off the dispatcher; and the count-to-zero ratchet stays green at 70.
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
