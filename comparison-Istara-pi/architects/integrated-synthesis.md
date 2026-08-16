# Integrated Synthesis

The three architects converge on an adapter-based lab rather than a direct source rewrite. The corrected owner intent is stronger than the first synthesis: Pi should be evaluated as a possible full replacement for Istara's agentic management core, not just as a substrate for one loop. Istara's product-specific research, memory, authorization, feature, and A2A requirements remain explicit acceptance criteria, but their agentic execution should be tested through Pi-facing adapters.

## Primary Comparison Claim

The lab should not ask "which repo has nicer code?" It should ask:

> Under identical scenarios, model policies, tool affordances, memory inputs, channel inputs, and stopping rules, can Pi replace Istara's agentic management core while producing equal or better grounded research outcomes per token, per tool call, and per A2A interaction, and while preserving Istara's feature contracts and governance constraints through adapters?

## Recommended Lab Shape

- Use `EngineAdapter` interfaces for Istara and Pi.
- Normalize tools through `CanonicalToolFacade`.
- Normalize evidence through compact JSONL/GZIP run artifacts.
- Score by research-spine step, not just final answer.
- Freeze feature success criteria from Istara's feature inventory before live runs.
- Treat Istara's current engine as the baseline, and Pi as the candidate replacement owner for agentic behavior.
- Run deterministic/dry validators before any cloud LLM test.
- Ask the owner for cloud LLM provider/model/budget/secret-loading instructions before any live execution.

## Pi Scope

Primary packages inside `earendil-works/pi`:

- `@earendil-works/pi-coding-agent` (`packages/coding-agent`): CLI/RPC/SDK harness, sessions, skills, extensions, prompt templates, process integration.
- `@earendil-works/pi-agent-core` (`packages/agent`): evented ReAct loop, tool execution, state management, custom message conversion, steering/follow-up queues.
- `@earendil-works/pi-ai` (`packages/ai`): unified provider/model layer, auth, dynamic catalogs, tool-call streaming, reasoning controls, token/cost accounting.

Reference-only material:

- `pi-review`: review workflow and review-to-fix handoff patterns.
- `pi-chat`: Telegram/Discord bridge, sandbox, channel memory, remote controls.
- `pi-tutorial`: prompt-adherence patterns only.
- `pi-website`: archived; not runtime evidence.

## What Pi Might Improve

- Full replacement of Istara's current agentic core through Pi packages.
- Cleaner evented ReAct loop from `pi-agent-core`.
- Better provider/model catalog abstraction from `pi-ai`.
- Cleaner update boundary through Pi packages, CLI/RPC, or sidecar integration.
- Explicit tool validation/execution flow.
- SDK/process integration and channel-facing harness patterns.
- Agent Skills progressive disclosure and durable session tree patterns.
- Review extension ergonomics and chat sandboxing patterns as ecosystem references only.

## What Istara Must Not Lose While Pi Owns The Agentic Core

- Project-scoped authorization for donated relay/browser compute.
- Research spine governance and UX research workflow semantics.
- DB-backed tasks, findings, documents, memory, and A2A state.
- ReasoningBank, RAG fallback, prompt-RAG persona/context composition, and untrusted-context boundaries.
- Feature-specific contracts across the full Istara inventory.
- Content-free telemetry and secret redaction expectations.

## First No-Model Deliverables

1. `EngineAdapter` and evidence schema spec.
2. Feature success matrix generated from `docs/features/inventory.json`.
3. Canonical tool schema and Istara/Pi mapping.
4. Dry-run validators that inspect scenarios, schemas, and run configs without model calls.
5. Cloud testing gate checklist.
6. Dependency-boundary decision matrix for library, CLI/RPC, and sidecar modes.
7. Full replacement coverage matrix: every current Istara agentic loop/channel/model-management path mapped to Pi ownership or explicit unsupported evidence.

## Live-Test Gate

Live testing remains blocked until the owner provides:

- Cloud provider and model list.
- API keys or env var names.
- Budget/token ceiling.
- Secret-loading method.
- Telemetry/content-retention permission.
- Confirmation of adapter mode priority: library, CLI/RPC, or sidecar.
