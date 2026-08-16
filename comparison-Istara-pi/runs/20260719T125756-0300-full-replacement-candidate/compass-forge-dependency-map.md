# Compass Forge Dependency Map

## Commands Used

- `compass-forge status`
- `compass-forge next`
- `compass-forge agent-brief --compact --max-seconds 45 --request ...`
- `compass-forge context "Full Pi replacement candidate..." --pack-type standard`
- `compass-forge intelligence impact --path tests/simulation/scenarios/31-task-documents-tools.mjs --request ...`
- `compass-forge intelligence impact --path scripts/run_istara_evals.py --request ...`
- `compass-forge intelligence test-impact --path labs/pi-replacement/src/istara-pi-adapter.mjs`
- `compass-forge intelligence test-impact --path tests/agentic_eval_contract.json`
- `compass-forge gate after --summary`
- `compass-forge gate after --target /Users/user/Documents/Istara-main-pi-replacement --recipe istararustgraphtrial --summary`

## Build Stream Conductor Compliance Commands

Additional commands after the owner clarified that `/skill build-stream-conductor` was mandatory:

- `compass-forge status`
- `compass-forge next`
- `compass-forge agent-brief --request "Pi replacement candidate Build Stream Conductor compliance check and benchmark artifact update" --compact --max-seconds 45`
- `compass-forge intelligence impact --path comparison-Istara-pi/runs/20260719T125756-0300-full-replacement-candidate/status.md --request "Build Stream Conductor compliance addendum for Pi replacement candidate artifacts"`
- `compass-forge intelligence test-impact --path comparison-Istara-pi/runs/20260719T125756-0300-full-replacement-candidate/benchmark-results.md`
- `python3 /Users/user/Documents/Skills/build-stream-conductor/scripts/conductor.py status --project-root /Users/user/Documents/Istara-main --brief`
- `python3 /Users/user/Documents/Skills/build-stream-conductor/scripts/routing.py show --root /Users/user/Documents/Istara-main`
- `python3 /Users/user/Documents/Skills/build-stream-conductor/scripts/scorecard.py --project-root /Users/user/Documents/Istara-main`
- `python3 /Users/user/Documents/Skills/build-stream-conductor/scripts/make_pipeline.py --help`
- `python3 /Users/user/Documents/Skills/build-stream-conductor/scripts/make_cast.py --help`

## CF State And Limitations

Main repo CF status reported `registered: false`, no recorded snapshot, and stale/unknown state, but the compact brief, context pack, impact analysis, test-impact, and gates returned usable dependency and verification maps.

Running CF directly from the replacement worktree first failed because that worktree resolved a missing `project` recipe. The successful worktree gate used explicit `--target /Users/user/Documents/Istara-main-pi-replacement --recipe istararustgraphtrial` from the main repo context.

Build Stream Conductor limitation: no literal conductor run exists for this round. The routing registry is readable, but `conductor.py status --brief` fails because `.compass-forge/conductor/cast.json` is missing, and `scorecard.py` returns no model rows. See `build-stream-conductor-compliance.md`.

## Dependency Findings Used For The Candidate

- `tests/simulation/scenarios/31-task-documents-tools.mjs` maps to task/document APIs, chat tool-use system, frontend task fields, and system tool contracts. Candidate coverage: `documents.tools.slice` and `chat.tool_loop.task_and_finding`.
- `tests/simulation/scenarios/71-plan-and-execute.mjs` and `tests/benchmarks/test_orchestration.py` map to task planning, DAG steps, validation fields, and skills lifecycle. Candidate coverage: `task.plan_execute.lifecycle`.
- `scripts/run_istara_evals.py`, `tests/evals/registry.json`, and `tests/evals/cases/core_eval_cases.json` map to classic JSON, RAG, DAG/ReAct, memory, memento skills, and thinking-output contracts. Candidate coverage: `structured_outputs.core_eval`, `memory.rag.slice`, and `skills.three_skill_slice`.
- `tests/simulation/scenarios/73-a2a-debate-and-reports.mjs` maps to A2A logs, persona registry, report layers, MECE categories, findings chain, and validation metadata. Candidate coverage: `a2a.debate_report.slice`.
- `tests/simulation/scenarios/53-channel-lifecycle.mjs` maps to channel CRUD, health, messages, conversations, and project scoping. Candidate coverage: `channel.lifecycle.simulated_slice`.

## Gate Evidence

Main repo final gate: `warn`, 0 failures, 0 new failures, route/type/contract/generated drift all 0, security 0. Warnings are inherited complexity warnings.

Replacement worktree explicit-target gate: `warn`, 0 failures, 0 new failures, route/type/contract/generated drift all 0, security 0. Warnings are inherited complexity warnings in existing production/test files.
