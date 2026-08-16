# Istara vs Pi ReAct Engine Comparison

Status: production-runtime candidate (branch `Review_pi_test`, CF-SPEC-7) independently reviewed on 2026-07-20 — verdict: NOT a full-replacement candidate; credible opt-in chat-turn engine only. **Read `2026-07-20-pi-replacement-review-diagnosis.md` first.**
Date: 2026-07-19 (review addendum 2026-07-20)
Owner request: compare Istara's current agentic management core against Pi, with the explicit hypothesis that Pi could replace Istara's ReAct loops, agentic orchestration, model management, SDK/process integration, and channel agent harnesses while Istara features reconnect through Pi-facing adapters.

## Hard Constraints

- Do not change Istara application code.
- Keep all new artifacts under this folder: `comparison-Istara-pi/`.
- Do not start live LLM testing beyond explicitly approved small DeepSeek smokes.
- Do not use local models.
- Ask the owner for cloud LLM/API instructions before any live evaluation.
- Keep storage nimble: prefer source inspection, thin fixtures, JSONL logs, and sampled traces over cloned bulk data or large run artifacts.
- Use Compass Forge read-only inspection for Istara code graph and repository relationships.

## Replacement Intent

The target experiment is full agentic-core replacement, not a partial augmentation. If Pi wins
on evidence, the desired direction is:

- Pi owns the ReAct/tool loop, planner/executor behavior, model/provider routing, SDK/process integration, session/harness mechanics, and supported-channel agent surfaces.
- Istara keeps its product features, data, project permissions, UX/research workflows, documents, findings, tasks, memory stores, telemetry policy, and user-facing contracts.
- Istara features are reconnected to Pi through adapters and canonical tools where needed.
- Pi remains independently updateable by version pinning or sidecar/package updates, so Istara can choose when to advance Pi without rewriting unrelated feature code.

## Pi Scope Confirmed By Owner

Primary comparison targets are the three core packages inside the `earendil-works/pi`
monorepo:

- `@earendil-works/pi-coding-agent` at `packages/coding-agent`: interactive coding agent CLI, RPC/SDK integration surface, session management, built-in tools, skills, extensions, prompt templates, and package/update model.
- `@earendil-works/pi-agent-core` at `packages/agent`: agent runtime, evented ReAct loop, tool execution, state management, session events, compaction, steering/follow-up queues, and custom message conversion.
- `@earendil-works/pi-ai` at `packages/ai`: unified multi-provider LLM API, provider catalogs, OAuth/API-key auth, tool-call streaming, token/cost accounting, reasoning controls, dynamic provider refresh, and cross-provider handoff.

Pi ecosystem references, not primary targets:

- `earendil-works/pi-review`: optional review workflow reference only, useful for best-practice extraction around review-to-fix loops.
- `earendil-works/pi-chat`: optional chat/sandbox reference only, useful for remote-control, channel isolation, and messaging integration patterns.
- `earendil-works/pi-tutorial`: optional prompt-adherence reference only.
- `earendil-works/pi-website`: archived website. Exclude from runtime comparison.

## Folder Map

- `2026-07-20-pi-replacement-review-diagnosis.md`: independent review verdict on the CF-SPEC-7 production-runtime candidate — coverage numbers, runtime defects (2 Blockers), test/evidence integrity findings, and the realistic replacement ceiling. Start here.
- `conductor-prompt.md`: prompt/instructions passed to the three architects.
- `evaluation-lab-plan.md`: durable Build Stream style plan and academic article plan.
- `metrics-schema.json`: compact metrics and evidence schema for the later cloud-LLM run.
- `evidence-log.md`: commands and observations gathered during this planning round.
- `pi-package-scope-and-dependency-strategy.md`: corrected Pi package scope and loose-dependency migration plan.
- `deepseek-test-config.md`: approved DeepSeek model/runtime configuration without secrets.
- `article-collaboration-protocol.md`: three-architect article writing and incremental judging protocol.
- `storage-cleanup-runbook.md`: storage limits, retained artifacts, and cleanup instructions for future runs.
- `architects/`: architect outputs and integrated synthesis.

## Architect Readouts

- `architects/architect-a-istara.md`: Istara internals, feature criteria, existing eval/test assets.
- `architects/architect-b-pi.md`: Pi repo map, replacement hypotheses, feasibility questions, risks.
- `architects/architect-c-methodology.md`: paired-eval methodology, metrics, evidence schema, academic article structure.
- `architects/integrated-synthesis.md`: reconciled lab blueprint and next gate.

## Current Phase

This comparison has now produced a robust isolated replacement candidate in
`/Users/user/Documents/Istara-main-pi-replacement/labs/pi-replacement`. Pi owns
deterministic Agent loops for eight representative Istara harness-derived scenario
families while Istara-shaped feature contracts stay behind canonical tools. The API key
stayed outside repo files.

The Pi provider smoke remains package-boundary preflight only, not a standalone replacement
score. Replacement scoring now has deterministic sidecar evidence for chat/tool loop,
plan-and-execute, documents/tools, structured outputs, memory/RAG, three skills, A2A,
channel lifecycle, and telemetry. Full production replacement still requires real Istara
service adapters and broader live scoring through `tests/benchmarks/`, `tests/evals/`,
`scripts/run_istara_evals.py`, `tests/agentic_eval_contract.json`,
`tests/real_user_benchmark/`, and `tests/simulation/scenarios/`.
