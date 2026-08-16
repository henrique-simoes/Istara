# Compass Forge Context Scope

Run: `20260719T114723-0300-pi-provider-setup`

Status: recorded after owner steering clarification

## Purpose

This file records the Compass Forge and context-mapping boundary for the Pi provider setup
run. The run proved package-boundary preflight only: Pi dependency resolution plus a
DeepSeek provider call through `@earendil-works/pi-ai`. It did not wire Pi into Istara's
agentic loops and must not be cited as replacement-harness evidence or a replacement score.

## Compass Forge Commands

- `compass-forge status`
  - Target: `/Users/user/Documents/Istara-main`.
  - Recipe: `istararustgraphtrial`.
  - State: unregistered/unknown; no snapshot recorded.
- `compass-forge next`
  - Recommended repository initialization; not performed because this run was confined to
    comparison artifacts and no Istara app code was modified.
- `compass-forge agent-brief --request "Record Compass Forge/context mapping scope for Pi provider dependency smoke; provider smoke is not replacement wiring; artifacts only under comparison-Istara-pi" --compact --max-seconds 30`
  - Timed out with structured `agent_brief_timeout` and `fallback_authorized: true`.
- `compass-forge classify "Record Compass Forge/context mapping scope for Pi provider dependency smoke; provider smoke is not replacement wiring; artifacts only under comparison-Istara-pi"`
  - Classified as `local_fix` / `lite`.
- `compass-forge intelligence impact --path comparison-Istara-pi/runs/20260719T114723-0300-pi-provider-setup/status.md --request "Record CF/context mapping scope for Pi provider dependency smoke; provider smoke is not replacement wiring"`
  - Produced a replacement-surface map relevant to the future harness, not to this smoke.
- `compass-forge context "Pi provider dependency smoke scope only: summarize relevant Istara surfaces for future replacement harness, but no provider-smoke wiring" --pack-type lite`
  - Selected comparison artifacts, the replacement worktree brief, package-scope strategy,
    and broad Istara surfaces as future harness context.

## Relevant To This Provider Smoke

- Artifact scope under `comparison-Istara-pi/`.
- Pi package boundary: `@earendil-works/pi-ai@0.80.10`.
- Provider path: Pi built-in `deepseekProvider()` calling `deepseek-v4-pro`.
- Secret handling and cleanup evidence.
- Storage constraints and dependency retention checks.
- Status/manifest/evidence wording that prevents over-claiming the smoke.

## Future Replacement-Harness Inputs

Compass Forge impact/context mapping identified these Istara surfaces as relevant when the
separate replacement worktree or sidecar harness is built:

- Model/provider routing: `backend/app/api/routes/compute.py`,
  `backend/app/core/compute_registry_routing.py`, `backend/app/core/model_capabilities.py`.
- Agent loop and lifecycle: `backend/app/core/agent_lifecycle.py`,
  `tests/test_loops.py`.
- Tool and skill execution: `backend/app/core/agent_skill_tools.py`,
  `tests/test_agent_skill_tools.py`.
- Memory/RAG/reasoning: `backend/app/core/rag.py`,
  `backend/app/core/reasoning_bank.py`, `frontend/src/lib/contextDagApi.ts`.
- A2A/channel behavior: `backend/app/services/channel_service.py`,
  `tests/test_a2a_project_claims.py`, `tests/test_a2a_security.py`,
  `tests/test_a2a_service_scope.py`.
- Product feature contracts: findings, tasks, MCP, surveys, project scope/RBAC, and
  feature documentation linked by Compass Forge impact output.

These surfaces are dependency-map inputs for the replacement harness. They were not edited
or executed by the provider smoke run.

Replacement comparison coverage must be anchored to Istara's existing harnesses:

- `tests/benchmarks/`
- `tests/evals/`
- `scripts/run_istara_evals.py`
- `tests/agentic_eval_contract.json`
- `tests/real_user_benchmark/`
- `tests/simulation/scenarios/`

Pi standalone primitive/provider tests are useful only to prove package boundaries and
runtime feasibility before wiring. They are not scored as replacement coverage.

## Out Of Scope For This Run

- No isolated worktree was created.
- No Istara app code was modified.
- No `IstaraPiAdapter`, `CanonicalToolFacade`, sidecar, RPC bridge, or agent-core harness
  was implemented.
- No Istara chat, task, research-spine, memory, A2A, channel, or tool loop ran through Pi.
- No paired Istara-vs-Pi metrics were collected.
- No local models were used or loaded.
- No live calls beyond the approved minimal Pi provider smoke were run.

## Next Gate

Use `comparison-Istara-pi/replacement-worktree-conductor-brief.md` for the next phase. That
phase must create a separated Istara worktree or sidecar harness, use Compass Forge for
real dependency/impact mapping and evidence tracking, and wire Pi as the candidate engine
for Istara agentic loops through adapters/canonical tools before any replacement metrics
are claimed.
