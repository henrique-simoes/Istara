# Systems Under Comparison

## Istara Baseline

Istara's current agentic surface includes chat and design ReAct loops, task/research
execution, skill routing, model/provider routing, RAG and ReasoningBank memory, A2A routes,
channel integrations, and content-free telemetry. Baseline evidence starts from the feature
inventory, existing tests, eval contracts, and benchmark plans.

## Pi Candidate

Pi is evaluated through the three core packages in `earendil-works/pi`:

- `@earendil-works/pi-agent-core` for the evented ReAct loop and tool/session mechanics.
- `@earendil-works/pi-ai` for provider/model management and usage metadata.
- `@earendil-works/pi-coding-agent` for CLI/RPC/SDK harness and process integration.

`pi-review`, `pi-chat`, and `pi-tutorial` are reference-only unless a later run explicitly
separates ecosystem lessons from primary package results.

## Replacement Boundary

Pi may own agentic execution. Istara must retain product data, authorization, memory policy,
research workflow semantics, feature contracts, telemetry policy, and user-visible UX.

