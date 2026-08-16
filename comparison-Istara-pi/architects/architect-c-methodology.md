# Architect C: Methodology, Metrics, And Academic Plan

Scope: planning-only evaluation methodology for a later cloud-LLM comparison. No files outside this folder should be changed; no live tests should run until the owner provides testing instructions.

## Methodology

Use a trace-first, adapter-based comparison lab. Istara and Pi should run the same scenario definitions through separate engine adapters:

- `IstaraAdapter`: drives existing APIs and traces from `tests/evals`, `tests/benchmarks`, `tests/real_user_benchmark`, `/api/chat`, tasks, A2A, telemetry, compute registry, and feature APIs.
- `PiAdapter`: exposes equivalent operations through the three core Pi packages:
  `@earendil-works/pi-coding-agent` for CLI/RPC/SDK harness behavior,
  `@earendil-works/pi-agent-core` for ReAct loop and state/tool events, and
  `@earendil-works/pi-ai` for provider/model management. It must not depend on
  `pi-review` or `pi-chat` for the primary score.
- `CanonicalToolFacade`: shared tool schemas mapped into each engine so tool accuracy is not confounded by different names/parameters.
- `JudgeLayer`: deterministic checks first; cloud judge only after the owner supplies cloud LLM access. No local models.

Use paired evaluation: each scenario is executed by both engines with the same prompt, same attached corpus, same tool affordances, same model policy, same max steps, same temperature/seed when available, and same stopping criteria. Score deltas per scenario and aggregate with bootstrap confidence intervals.

Add a dependency-boundary axis to every scenario. The Pi run must declare whether it used
library mode, CLI/RPC mode, or sidecar mode, and the score must separate engine quality from
integration overhead. A Pi result is not migration-ready unless the adapter can be upgraded
or rolled back by changing Pi package versions without changing Istara product code.

## Research Spine Scoring

Score each scenario across these phases:

1. Intent intake and constraint preservation.
2. Context and memory loading.
3. Plan/decomposition.
4. Tool/skill selection.
5. Tool/action execution.
6. Observation integration and recovery.
7. Evidence grounding.
8. Synthesis/final output.
9. Review/reflection/memory update.
10. System/governance adherence.

## Scenario Suite

- Deterministic subsystem baseline:
  - Reuse `scripts/run_istara_evals.py` cases: classic JSON, RAG, prompt RAG, LLMLingua, DAG/ReAct, ReasoningBank, Memento Skills, Meta Hyperagent, thinking-output, voice contract.
  - Pi must implement equivalent scenario hooks or mark unsupported.
- Pi package-boundary suite:
  - `@earendil-works/pi-agent-core`: fake-provider tool-call loop, sequential vs parallel tools, invalid-argument recovery, termination hints, steering/follow-up queue behavior, event trace completeness.
  - `@earendil-works/pi-ai`: provider auth resolution without secret logging, model catalog selection, dynamic refresh behavior, reasoning controls, provider-scoped environment overrides, token/cost usage, cross-provider handoff.
  - `@earendil-works/pi-coding-agent`: CLI/RPC JSONL framing, session creation/resume, built-in tool affordance mapping, skills/prompt-template loading, extension/package isolation, process lifecycle and abort behavior.
- ReAct/tool trajectory suite:
  - Derived from `backend/app/api/routes/chat.py` and `backend/app/skills/system_actions.py`: `create_task`, `search_documents`, `list_tasks`, `move_task`, `attach_document`, `search_findings`, `list_project_files`, `assign_agent`, `send_agent_message`, `get_document_content`, `search_memory`, `update_task`, `sync_project_documents`, `web_fetch`, `browse_website`, `context_expand`, `context_grep`, plus Istara's constrained `run_skill`.
- Research workflow suite:
  - Use the realistic UX corpus pattern from `tests/real_user_benchmark`: upload/search evidence, synthesize contradictory interviews, create tasks, request revision, produce report, cite sources, update memory.
- Feature matrix sweep:
  - Import all feature ids from `docs/features/inventory.json`.
  - Each feature gets a minimal success contract: reachable surface/API, project scoping, expected user action, expected agent/tool behavior if relevant, evidence emitted, graceful failure path.
  - Aggregate by groups: Shell, Auth, Chat, Findings, Tasks, Interviews, Documents, Context, Skills, Agents, Memory, Interfaces, Integrations, Loops, Settings, Autoresearch, Compute, Ensemble, Quality, Backup, Meta, Admin, History, Notifications.
- A2A suite:
  - Project-scoped message persistence, allowed message types, inbox/log visibility, delegate/debate/report tasks, conflicting project claims rejected, final task improved by collaboration.
- Long-horizon suite:
  - Adapt `tests/benchmarks/test_orchestration.py`, scenario 71, 73, and 76: DAG validity, topological execution, steering injection, multi-step synthesis, final report.

## Evidence Model

Each later run writes compact artifacts:

- `manifest.json`: git, adapter versions, scenario registry hash, model policy, environment booleans, no secrets.
- `scenarios.jsonl`: scenario metadata and feature ids.
- `trace.jsonl.gz`: compact step trace, tool calls, observations, token counts, errors.
- `outputs.jsonl.gz`: final artifacts and judge inputs, capped per record with SHA for larger content.
- `scores.json`: aggregate metrics and confidence intervals.
- `feature-matrix.json`: per-feature success criteria and pass/fail evidence.
- `article-tables/`: CSV/JSON tables for academic writeup.

Keep storage nimble: gzip JSONL, cap raw text fields, hash large artifacts, store screenshots only for UI failures, and never store endpoints/tokens.

## Token And Tool Accounting

- Wrap every engine call externally.
- Prefer provider-reported `usage.prompt_tokens`, `usage.completion_tokens`, and `usage.total_tokens` when available.
- Estimate with one shared tokenizer when model-specific usage is unavailable.
- Record token counts per research-spine phase, not only per API call.
- Count memory separately: loaded memory item count, memory bytes/chars, estimated memory tokens, memory hit relevance.
- Count tools as attempted, valid, executed, successful, repeated, hallucinated, skipped-needed.
- Compute `quality_per_1k_tokens`, `quality_per_tool_call`, and `marginal_tool_gain`.

## Academic Article Structure

Working title: "Comparing Istara and Pi as ReAct/Agentic Engines for UX Research Workflows"

1. Abstract.
2. Introduction and research questions.
3. Related work: ReAct, BFCL, tau-bench, GAIA, HELM, RAG/TruLens/Ragas, memory benchmarks, A2A protocols.
4. Systems under comparison: architecture-neutral description of Istara and Pi.
5. Methodology: paired scenarios, adapters, tools, judges, token accounting, feature matrix.
6. Metrics and statistical analysis.
7. Results: task success, step quality, final quality, tool efficiency, memory load, prompt/skill adherence, A2A, model management.
8. Qualitative trace analysis.
9. Best-practice extraction and transfer analysis.
10. Threats to validity.
11. Reproducibility package and artifact schema.
12. Conclusion.

## Runbook

1. Lab-only setup now: define adapters, scenario registry, evidence schema, and dry-run validators without model calls.
2. Freeze scenario corpus and feature matrix from existing Istara docs/tests.
3. Wait for owner cloud LLM access instructions.
4. Run a tiny credential smoke against both engines, one scenario only.
5. Run static/deterministic suites.
6. Run paired live suites in randomized order.
7. Generate scorecards and academic tables.
8. If Pi wins any category, perform best-practice extraction: identify transferable mechanism, map to Istara surface, classify as prompt/tool/memory/model/routing/governance improvement, and propose benchmark-gated adoption.
9. Summarize into article draft plus reproducibility appendix.
