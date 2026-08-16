# Run Status

Run: `20260719T120128-0300-replacement-worktree`

Status: complete

## Compass Forge Remediation Update

Owner steering after the first completion required explicit CF dependency maps. The
conductor re-read `replacement-worktree-conductor-brief.md`, ran CF status/next, a compact
agent brief, a standard context pack, and targeted impact maps for chat/tool loop, task
planning/execution, model/provider routing, memory/RAG, A2A, and channels.

Artifact added: `cf-dependency-maps.md`.

One implementation remediation came out of that pass: the DeepSeek smoke now deletes
`DEEPSEEK_API_KEY` in a `try/finally` that covers provider setup, model lookup, and the live
completion call.

## Constraints

- Created isolated worktree: `/Users/user/Documents/Istara-main-pi-replacement`.
- Created branch: `comparison/pi-replacement-core`.
- Base: `origin/main` at `fa6a1a391b5a1089690eb8fed5d179ce146ec9e9`.
- Main worktree writes stayed under `comparison-Istara-pi/`.
- No commit was created.
- No local models were used or loaded.
- DeepSeek key was read from macOS Keychain only inside the live smoke process.

## Outcome

The replacement candidate now has a removable lab sidecar under
`labs/pi-replacement/`. It wires:

- `CanonicalToolFacade` for Istara canonical tool schemas and result envelopes.
- `IstaraPiAdapter` for Istara scenario/session/tool concepts mapped into Pi-owned
  `Agent` turns and Pi provider calls.
- `@earendil-works/pi-agent-core@0.80.10` for loop, events, and tool execution.
- `@earendil-works/pi-ai@0.80.10` for faux no-model validation and DeepSeek
  `deepseek-v4-pro` provider smoke.

Working replacement evidence exists for one Istara feature scenario:
`chat.tool_loop.task_and_finding`. Pi owns the agent turn loop and executes canonical
Istara task/finding tools while Istara-owned project state remains in facade envelopes.

## Remaining Unsupported

- Production Istara routes are not switched to Pi.
- Research-spine phases, memory persistence, A2A delegation, channel harnesses, SDK/process
  sidecar lifecycle, steering queues, telemetry integration, and autoresearch governance
  remain adapter tasks.
- Paired Istara-vs-Pi benchmarks remain blocked on owner token/cost cap and scenario count.
