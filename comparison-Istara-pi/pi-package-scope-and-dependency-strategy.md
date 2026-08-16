# Pi Package Scope And Loose Dependency Strategy

Status: scope correction and enrichment
Date: 2026-07-19

## Corrected Scope

The primary Pi comparison targets are three packages inside the `earendil-works/pi`
monorepo:

- `@earendil-works/pi-coding-agent` (`packages/coding-agent`): interactive coding agent CLI,
  JSON/RPC/process integration, SDK embedding, session management, built-in tools, skills,
  extensions, prompt templates, and Pi package/update mechanics.
- `@earendil-works/pi-agent-core` (`packages/agent`): agent runtime, evented ReAct loop,
  tool validation/execution, state management, streaming events, `Agent` wrapper,
  low-level `agentLoop`, compaction, custom message conversion, and steering/follow-up queues.
- `@earendil-works/pi-ai` (`packages/ai`): unified multi-provider LLM API, provider catalogs,
  OAuth/API-key resolution, tool-call streaming, TypeBox tool schemas, dynamic model refresh,
  reasoning controls, token/cost accounting, provider-scoped environment overrides, and
  cross-provider handoff.

The prior architect pass already inspected these packages in Architect B. It also treated
`pi-review` and `pi-chat` as primary repositories because the original request said "three
repos". That is now corrected: `pi-review` and `pi-chat` are reference material only.

## Reference-Only Material

- `pi-review`: useful for review workflow, verdict/fix handoff, and review guidelines
  best-practice extraction.
- `pi-chat`: useful for channel sandboxing, remote controls, channel memory, and messaging
  integration patterns.
- `pi-tutorial`: optional prompt-adherence reference.
- `pi-website`: archived and excluded.

## Migration Question

The experiment should answer whether Istara can use Pi as a loose, independently updated
dependency that replaces Istara's full agentic management core without making Pi own Istara
product data or feature semantics.

The target architecture is full agentic-core replacement without feature rewrite:

```text
Istara product layer
  owns users, projects, auth, documents, tasks, findings, feature contracts,
  workflow semantics, data stores, telemetry redaction, UX surfaces
        |
        v
IstaraPiAdapter
  owns translation, policy checks, canonical tools, feature reconnection,
  trace capture, version pinning, rollback
        |
        v
Pi agentic core dependency boundary
  pi-agent-core for agent/tool loop
  pi-ai for provider/model layer
  pi-coding-agent for CLI/RPC/SDK harness when useful
  Pi channel/harness patterns where Istara uses channel integrations
```

## Adapter Modes To Compare

### Library Mode

Use `@earendil-works/pi-agent-core` and `@earendil-works/pi-ai` as imported packages from a
Node boundary. This is likely the cleanest ReAct/model-management experiment.

Success criteria:

- Pi can own the canonical agent loop for chat, task execution, research spine, memory actions, A2A behavior, and channel-facing agent turns.
- Canonical tools run through Istara authorization and telemetry wrappers.
- Pi emits enough events to fill `trace.jsonl.gz` without parsing terminal output.
- Istara can pin package versions and roll them forward/back independently.
- No Pi state becomes the source of truth for Istara tasks, documents, memory, or findings unless a later explicit migration proves that store can move safely.

Main risk: Python/FastAPI to Node boundary complexity if Istara stays Python-centered.

### CLI/RPC Mode

Use `@earendil-works/pi-coding-agent` as an external process through JSON/RPC or strict JSONL
framing.

Success criteria:

- Process lifecycle is observable and abortable.
- Inputs/outputs are structured enough for feature scoring.
- Session files are either disabled or treated as sidecar traces, not source-of-truth state.
- Built-in tools are replaced or constrained by the canonical tool facade.
- Channel and SDK integration paths can be exercised without requiring Istara to preserve its current channel-specific ReAct loops.

Main risk: CLI behavior may be optimized for terminal coding workflows rather than Istara's
research-product workflows.

### Sidecar Mode

Wrap Pi packages behind a small local service with a stable HTTP or JSONL contract consumed
by Istara.

Success criteria:

- Istara can swap Pi versions by updating sidecar dependencies.
- Sidecar contract covers the full agentic surface: run session, stream event, plan/execute, call tool, load/write memory action, coordinate A2A, handle channel input, route model, finalize.
- Secrets, project auth, and feature eligibility remain enforced by Istara before requests
  reach Pi.
- Sidecar failure degrades cleanly to Istara's existing engine.

Main risk: operational overhead, deployment packaging, and duplicated retry/circuit-breaker
logic.

## Version And Update Evidence

Every later run manifest must record:

- Istara git SHA and dirty-state flag.
- Pi monorepo SHA.
- Pi package versions.
- Lockfile hash.
- Adapter version and adapter mode.
- Model/provider policy.
- Whether local models were disabled.
- Exact no-secret telemetry policy.

Pi should be considered updateable only if a package version change can be tested by rerunning
deterministic validators and paired live scenarios without changing Istara product code.

## Hard Rejection Criteria

Reject the Pi migration path if the adapter requires any of these:

- Pi bypasses Istara project authorization.
- Pi writes directly to Istara DB state without adapter-enforced policy.
- Pi becomes the source of truth for documents, tasks, findings, project memory, or A2A without a separate explicit store migration decision.
- Pi stores secrets or uncapped prompt/output content in traces.
- Pi requires local models for core functionality.
- Pi cannot expose token/tool/memory accounting at research-spine step granularity.
- Pi cannot cover Istara's current agentic surfaces: chat, task execution, research spine, memory actions, A2A orchestration, model management, SDK/process integration, and channel-facing behavior.
- Pi upgrades require broad Istara product-code rewrites.

## Best-Practice Extraction If Pi Wins

If Pi wins any category, extract the mechanism before recommending replacement:

- `pi-agent-core`: event model, tool preflight hooks, sequential/parallel execution controls,
  termination hints, steering/follow-up queues.
- `pi-ai`: provider catalog design, auth ownership, TypeBox tool schemas, streaming tool-call
  parsing, token/cost accounting, dynamic refresh, cross-provider handoff.
- `pi-coding-agent`: extension/package model, prompt templates, skill loading, RPC/session
  ergonomics, update controls.
- `pi-review` and `pi-chat`: review and chat/sandbox practices only after core package
  findings are separated from ecosystem extension findings.
