# Engine Adapter And Evidence Spec

## Common Interface

Each engine adapter must expose equivalent behavior for the same scenario:

- `prepare_run(manifest)`: validate git SHA, adapter version, model policy, local-model
  prohibition, secret presence boolean, and scenario registry hash.
- `start_session(scenario)`: create an isolated session with capped retention.
- `run_step(step)`: execute one ReAct turn or research-spine phase.
- `call_tool(tool_call)`: route through the canonical facade and record schema validation.
- `load_memory(query, scope)`: record memory scope, relevance, token estimate, and redaction.
- `finalize()`: emit final output, compact trace, scores, and cleanup status.

## Istara Adapter Boundary

Istara baseline runs measure the current engine. They may use Istara APIs, eval runners, and
feature routes, but this comparison run does not modify Istara source code.

## Pi Adapter Boundary

Pi candidate runs test ownership of the agentic core through:

- `@earendil-works/pi-agent-core` for loop/tool/session events.
- `@earendil-works/pi-ai` for provider/model routing and usage accounting.
- `@earendil-works/pi-coding-agent` for CLI/RPC/SDK harness behavior when useful.

Pi must not bypass Istara authorization, data ownership, memory policy, feature eligibility,
or telemetry redaction. If a capability is missing, the result is marked unsupported with
evidence instead of silently narrowing the replacement scope.

## Trace Retention

Traces and outputs are JSONL, gzip-compressed, capped to 1200 text characters per record, and
must not include API keys, headers, uncapped prompts, or production data.

