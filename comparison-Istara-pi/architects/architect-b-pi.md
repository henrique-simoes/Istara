# Architect B: Pi Architecture And Replacement Feasibility

Scope: planning-only Pi architecture pass for comparison against Istara. No cloning, no code changes, no model calls.

## Pi Package Map

- `earendil-works/pi`: main runtime monorepo and the only primary Pi codebase for this comparison.
  - `packages/coding-agent` / `@earendil-works/pi-coding-agent`: interactive coding agent CLI, JSON/RPC modes, SDK embedding, session management, built-in `read`/`write`/`edit`/`bash` tools, skills, extensions, prompt templates, package/update mechanics, and process-integration surfaces.
  - `packages/agent` / `@earendil-works/pi-agent-core`: evented agent loop, tool validation/execution, `Agent` wrapper, low-level `agentLoop`, state management, custom message conversion, streaming events, tool execution hooks, steering/follow-up queues, and compaction/session control.
  - `packages/ai` / `@earendil-works/pi-ai`: unified provider/model layer, OAuth/API-key auth, dynamic model catalogs, streaming events, tool-call streaming/validation, reasoning levels, token/cost metadata, provider-scoped environment overrides, and cross-provider handoff.
  - `packages/orchestrator`: experimental; not stable replacement material yet.

Ecosystem references, not core comparison targets:

- `earendil-works/pi-review`: Pi extension for `/review` and `/end-review`; useful for review-loop best practices, not core ReAct replacement.
- `earendil-works/pi-chat`: Discord/Telegram extension with per-channel Gondolin VM, persistent workspace/shared memory/skills, attachments, remote controls, encrypted secret exchange, and tmux workers; useful for chat/sandbox lessons, not core harness replacement.
- `pi-tutorial`: optional prompt-adherence reference only.
- `pi-website`: archived; exclude from architecture/runtime evaluation.

## Replacement Hypotheses

- `@earendil-works/pi-agent-core` may be cleaner and more reusable than Istara's duplicated chat/design/general-task loops: stream assistant output, validate tool calls, execute tools, append tool results, and continue until no further tool/follow-up remains.
- `@earendil-works/pi-agent-core` should be tested as a possible replacement owner for Istara's low-level and high-level agentic loop mechanics: chat turns, task execution, research-spine steps, memory actions, A2A turns, and channel-facing agent behavior. Istara product data and policy remain enforced through adapters.
- `@earendil-works/pi-ai` should be tested as a replacement for Istara's model API abstraction. Donated relay/browser compute, project authorization, hardware state, circuit breakers, retries, and LM Studio recovery become adapter/policy requirements that Pi must satisfy or expose hooks for.
- `@earendil-works/pi-coding-agent` is primarily a harness/integration candidate: CLI/RPC/SDK modes, extensions, package model, session tree, and built-in coding tools can be used to evaluate process-level integration without importing the whole CLI into Istara.
- Pi skills and Istara skills are compatible in concept but not equivalent in governance. Pi uses Agent Skills progressive disclosure; Istara has DB/registry-driven research skills with ranking, ACLs, quality stats, output validation, and findings persistence.
- Pi's JSONL session tree overlaps with Istara chat sessions and DAG compaction. Treat it as an inspiration or sidecar log, not as Istara's source of truth until a migration proves no split-brain history risk.
- `pi-review` and `pi-chat` are relevant as best-practice references only. They should not be included in the primary score as if they were required replacement packages.

## Loose Dependency Feasibility

Preferred migration model: Pi becomes an independently updateable replacement for the Istara agentic core behind Istara-owned adapters.

- Do not vendor Pi source into Istara.
- Do not let Pi bypass Istara DB state, project authorization, donated compute selection, ReasoningBank/memory policy, or feature eligibility. These become adapter-enforced policies while Pi owns the agentic execution.
- Record Pi package versions and monorepo SHA in every test manifest.
- Compare three adapter shapes before implementation:
  - Library adapter using `@earendil-works/pi-agent-core` plus `@earendil-works/pi-ai`.
  - CLI/RPC adapter using `@earendil-works/pi-coding-agent` in JSON/RPC mode.
  - Sidecar adapter wrapping the Pi packages behind a stable local HTTP or JSONL contract.
- Success means Pi covers all current Istara agentic-management surfaces and Istara can pin, upgrade, or roll back Pi versions by changing adapter dependencies and rerunning the lab, without rewriting Istara product feature code.
- Failure means the adapter either leaks too much Istara policy into Pi, creates split-brain state, cannot satisfy feature contracts, or adds more operational complexity than it removes.

## Feature Criteria

- ReAct/tool loop:
  - Native tool calling, fallback behavior, max iterations, streamed tool-call deltas, JSON salvage/truncation safety, tool schema validation, parallel/sequential execution, aborts, termination hints, hook points.
- Provider/model management:
  - Provider catalog breadth, OAuth/API-key handling, local OpenAI-compatible support, dynamic refresh, model switching, reasoning controls, token/cost accounting, timeout/retry behavior, session affinity.
- Skills/prompt adherence:
  - Discovery paths, project trust, progressive disclosure reliability, forced invocation, skill ACL mapping, prompt injection boundaries, skill creation/update governance.
- Memory/session handling:
  - Persistent tree/branching, compaction quality, searchable recall, project/agent/user scopes, DB provenance, interruption recovery.
- Chat/A2A/sandbox:
  - Telegram/Discord triggers, identity spoofing defenses, attachments, secrets, remote controls, per-channel isolation, outbound network policy, A2A task delegation.
- Review workflow:
  - Target coverage, rubric quality, custom guidelines, verdict/fix queue, human callouts, integration with Istara task review rewards.

## Experiment Design Hooks

- Static matrix: map Pi classes/APIs to Istara modules before coding.
- Deterministic loop tests: compare Pi `Agent`/`AgentHarness` with fake provider/tool streams against Istara chat tool generation and general-task execution.
- Provider adapter spike: test whether `@earendil-works/pi-ai` can sit behind an Istara-compatible Python/Node boundary without bypassing project authorization.
- Agent-core adapter spike: test whether `@earendil-works/pi-agent-core` can run the canonical tool facade and emit the required trace schema without owning Istara memory/state.
- Coding-agent RPC spike: test whether `@earendil-works/pi-coding-agent` RPC/JSON mode is stable enough for process integration, version pinning, and trace capture.
- Skill bridge spike: wrap one Istara `run_skill` path as a Pi tool while preserving Istara ACLs, telemetry, finding storage, and review state.
- Ecosystem reference spike: compare `pi-chat` Gondolin per-channel model and `pi-review` review-to-fix flow as optional best-practice references after the core package test plan is stable.
- Live LLM evals: require owner-provided cloud credentials, model choices, and budget.

## Feasibility Questions

- Is the intended replacement only the ReAct loop, only provider/model management, or both?
- Is a Node/TypeScript sidecar acceptable inside Istara's Python/FastAPI deployment?
- Should cloud OAuth providers be enabled in a local-first product, or only local/OpenAI-compatible endpoints?
- Must donated relay/browser compute stay behind Istara's current project authorization contract?
- Can Pi's session tree coexist with Istara's SQL message/DAG models without split-brain history?
- Should tool execution stay Python/transaction-bound, or can it cross into Pi's TypeScript harness?
- Are Pi's skill-loading semantics strict enough for Istara's research-methodology guarantees?

## Risks

- Pi has no built-in permission sandbox; isolation is external via Gondolin/Docker/OpenShell.
- `pi-chat` uses a VM but allows outbound HTTP/TLS by default; Istara may need tighter policy.
- Pi's skill docs note models do not always load full skills unless prompted or forced.
- Pi's orchestrator package is experimental.
- TypeScript/Python bridging may add deployment, observability, and failure-mode complexity.
- Some extension repos appear to reference older package names; package lineage/version compatibility needs verification.
- Cloud/provider behavior cannot be judged without user-provided credentials and explicit test authorization.
