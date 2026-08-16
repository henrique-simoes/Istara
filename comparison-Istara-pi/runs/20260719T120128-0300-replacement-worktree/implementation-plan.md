# Implementation Plan

## Selected Insertion Point

Use a removable lab sidecar in the isolated worktree:

`/Users/user/Documents/Istara-main-pi-replacement/labs/pi-replacement`

This avoids production route changes while proving the intended boundary:

1. Istara feature scenario supplies project/session intent.
2. `CanonicalToolFacade` exposes Istara-owned actions as strict schemas and result envelopes.
3. `IstaraPiAdapter` creates a Pi `Agent` session and injects canonical tools.
4. Pi owns turn execution, tool execution events, and provider calls.
5. Istara-owned state stays in facade snapshots.

## Compass Forge Impact Basis

After the owner steering update, the conductor ran CF orientation plus targeted impact maps
for the minimum required surfaces. The detailed dependency maps are in
`cf-dependency-maps.md`.

CF showed the production insertion surfaces are broad and contract-heavy:

- Chat/tool loop: `backend/app/api/routes/chat.py`, chat SSE/tool contracts, session/message
  persistence, RAG, prompt identity, and frontend chat stores.
- Task planning/execution: `backend/app/core/agent_execution.py`, task state, skill
  routing, checkpoints, telemetry, findings, memory, review, and A2A debate.
- Provider routing: `backend/app/core/llm_router.py` -> `compute_registry`, settings,
  compute routes, relay proxy, and model-provider frontend controls.
- Memory/RAG: `backend/app/core/rag.py`, LanceDB, embeddings, keyword fallback, content
  guard wrapping, and memory/API callers.
- A2A/channel: `backend/app/api/routes/a2a.py`, `backend/app/services/a2a.py`,
  `backend/app/api/routes/channels.py`, `backend/app/services/channel_service.py`, project
  scoping, channel credentials, and platform adapters.

This is why the sidecar remains the safe lab insertion point for this phase.

## Implemented

- Canonical tools:
  - `tasks.create`
  - `findings.create`
  - `memory.search`
  - `a2a.delegate`
- Scenario:
  - `chat.tool_loop.task_and_finding`
- Provider path:
  - Pi built-in `deepseekProvider()` with `deepseek-v4-pro`.
- Tests:
  - Facade schema/result-envelope validation.
  - Adapter scenario through Pi-owned `Agent` tool execution.

## Deferred Adapter Tasks

- Route an existing Istara backend chat scenario through the sidecar.
- Add real Istara DB/service adapters for task, finding, memory, and A2A handlers.
- Feed Pi event stream into Istara telemetry with redaction.
- Add sidecar lifecycle, abort, resume, and version pinning.
- Expand replacement coverage to research spine, design chat, channel turns, steering, and SDK/process integration.
