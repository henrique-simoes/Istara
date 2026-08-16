# Replacement Worktree Conductor Brief

Status: approved by owner
Date: 2026-07-19

## Objective

Create an isolated working tree with lab code that wires Pi as the candidate replacement for
Istara's agentic management core. This is not a standalone Pi demo. It must prove a feasible
architecture for running Istara feature scenarios through a Pi-owned engine path.

## Worktree

- Main worktree to leave untouched: `/Users/user/Documents/Istara-main`.
- Replacement worktree path: `/Users/user/Documents/Istara-main-pi-replacement`.
- Suggested branch: `comparison/pi-replacement-core`.
- Base: current `origin/main` unless the conductor determines a safer base and records why.

## Wiring Target

The replacement path should introduce lab/prototype code that can be deleted later without
touching production behavior. Prefer a sidecar/library adapter:

```text
Istara scenario runner / feature contract
        |
        v
CanonicalToolFacade
        |
        v
IstaraPiAdapter
        |
        v
Pi sidecar/library boundary
  @earendil-works/pi-agent-core
  @earendil-works/pi-ai
  optional @earendil-works/pi-coding-agent RPC/SDK
```

Pi should own, in the candidate path:

- Chat ReAct turns.
- Design chat turns.
- Task planning/execution.
- Research-spine steps.
- Tool execution loop.
- Memory actions through Istara memory adapters.
- A2A orchestration behavior.
- Model/provider calls through `pi-ai`.
- SDK/process/channel-facing turns where Istara uses channels.

Istara remains source of truth for:

- Projects, users, permissions, documents, tasks, findings, feature contracts, existing
  memory stores, research workflow semantics, telemetry redaction, and UI/API expectations.

## Required Stages

1. Create isolated worktree and branch.
2. Use Compass Forge thoroughly for orientation, dependency/impact mapping, context packs,
   and evidence tracking before choosing the lab insertion point.
3. Inspect current Istara agentic surfaces and choose the narrowest lab insertion point.
4. Install/resolve Pi dependencies only in the isolated worktree or temporary lab area.
5. Implement a minimal `IstaraPiAdapter`, `CanonicalToolFacade`, and DeepSeek-backed Pi
   provider smoke.
6. Wire at least one scenario path through Pi-owned execution:
   - preferred first path: chat/tool loop or task planning/execution;
   - second path if cheap: memory or A2A action through canonical facade.
7. Run no-model validators and one small DeepSeek smoke through the Pi-wired path.
8. Record Compass Forge evidence, conductor ledger entries, and article/review notes under
   `comparison-Istara-pi`.
9. Clean storage and report retained artifacts.

## Compass Forge Requirements

The conductor must use Compass Forge as the dependency and process map, not as a decorative
status check.

Required use:

- Start with `compass-forge status`, `next`, and an agent brief/context pack for the
  replacement request.
- Use Compass Forge impact/context tooling to map dependencies for every chosen insertion
  point: imports, callers, routes, tests, feature docs, telemetry, and risks.
- Record which Istara surfaces were inspected and why they were selected or deferred.
- Track implementation/review/remediation stages in the conductor ledger with exact
  verification commands and evidence files.
- If Compass Forge state is stale or unavailable, record that as a limitation and fall back
  to explicit `rg`/source inspection, but do not silently skip dependency mapping.

Minimum dependency maps to produce:

- Chat/tool loop dependency map.
- Task planning/execution dependency map.
- Model/provider routing dependency map.
- Memory/RAG dependency map.
- A2A/channel dependency map, even if not implemented in the first smoke.

## Hard Constraints

- Do not modify the original `/Users/user/Documents/Istara-main` worktree outside
  `comparison-Istara-pi/`.
- Do not commit unless explicitly asked.
- Do not use local models.
- Do not write API keys into any file, command log, trace, or message.
- Keep large dependencies out of `comparison-Istara-pi`; if needed, they belong in the
  isolated worktree and must be measured.
- Stop before broad paired benchmarks unless the owner provides a token/cost cap.

## Success Criteria

This phase is successful if it produces a working isolated branch where at least one
Istara feature scenario can execute through Pi-owned agent loop/provider code with traceable
metrics, and where the remaining surfaces are represented as concrete adapter tasks rather
than vague TODOs.

It is not successful if it only runs Pi standalone without an Istara feature contract.

## Istara Test Harness Coverage Backbone

The existing Istara test harness is the scenario source of truth for the replacement
comparison. The conductor must not invent a small custom benchmark and call it representative.

Use these assets to drive the coverage plan:

- `tests/benchmarks/test_orchestration.py`
- `tests/benchmarks/run_benchmarks.py`
- `tests/benchmarks/long_horizon_runner.py`
- `tests/evals/README.md`
- `tests/evals/registry.json`
- `tests/evals/cases/core_eval_cases.json`
- `scripts/run_istara_evals.py`
- `tests/agentic_eval_contract.json`
- `tests/real_user_benchmark/benchmark-plan.md`
- `tests/real_user_benchmark/system-prompt.md`
- `tests/real_user_benchmark/benchmark-registry.json`
- `tests/real_user_benchmark/run.mjs`
- `tests/simulation/scenarios/*.mjs`

Required handling:

- Map every relevant Istara harness scenario to either:
  - baseline Istara execution,
  - Pi-wired candidate execution,
  - deterministic/no-model equivalent,
  - blocked by missing adapter, or
  - intentionally deferred with a reason.
- Preserve research-spine scoring by step: intent, context/memory load, plan,
  tool/skill selection, execution, recovery, grounding, synthesis, review, governance.
- Prioritize scenarios that cover full agentic workflow breadth:
  - tool/document/task loop: scenario 31;
  - channel lifecycle: scenario 53;
  - plan-and-execute: scenario 71;
  - A2A debate/reporting: scenario 73;
  - long-horizon trajectory: scenario 76;
  - real-user benchmark/CareNav workflow;
  - core eval registry cases for RAG, ReasoningBank, Memento/skills, DAG/ReAct, and
    structured outputs.
- The Pi candidate score must be based on the same scenarios and feature contracts as
  Istara where possible. Standalone Pi primitive tests are useful only as package-boundary
  evidence, not as replacement scores.
- Unsupported Pi paths must be recorded as evidence in the coverage matrix rather than
  silently removed from the denominator.
