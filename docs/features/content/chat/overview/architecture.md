---
stable_id: chat.overview
title: Chat Workspace
ui_path: Chat
audience: architecture
status: documented
related_features: ["chat.sessions", "chat.model-controls", "chat.files", "chat.audio", "chat.steering"]
related_glossary: ["rag", "mcp"]
code_references: ["frontend/src/components/chat/ChatView.tsx", "frontend/src/stores/chatStore.ts", "frontend/src/stores/sessionStore.ts", "backend/app/api/routes/chat.py", "backend/app/api/routes/sessions.py"]
api_references: ["backend/app/api/routes/chat.py", "backend/app/api/routes/sessions.py", "frontend/src/lib/chatApi.ts", "frontend/src/lib/sessionsApi.ts"]
test_references: ["tests/test_chat.py", "tests/test_sessions.py", "tests/test_project_rbac.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-09-01
compass: CF-SPEC-102 / CF-1295
---

# Chat Workspace Architecture

## Implementation Summary

Chat is the project-scoped conversational workspace for working with Istara agents, context, files, and model settings.

## Frontend Surface

- `frontend/src/components/chat/ChatView.tsx`
- `frontend/src/stores/chatStore.ts`
- `frontend/src/stores/sessionStore.ts`
- `backend/app/api/routes/chat.py`
- `backend/app/api/routes/sessions.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/chatStore.ts`
- `frontend/src/stores/projectStore.ts`

### API And Backend

- `backend/app/api/routes/chat.py`
- `backend/app/api/routes/sessions.py`
- `frontend/src/lib/chatApi.ts`
- `frontend/src/lib/sessionsApi.ts`

## Architecture Notes

- The feature is mounted through `frontend/src/components/chat/ChatView.tsx` and the UI navigation path recorded in the inventory.
- Chat history fetches clear previous messages before loading the active project's session history; errors also clear messages so stale conversations cannot remain visible.
- Session detail fetches include the active project id and the backend authorizes that project before loading the session and its messages.
- Toolbar session updates carry the active project id so model, agent, preset, and thinking-mode changes cannot mutate a stale session from another project.
- Chat session agent assignment is server-validated before create, update, or LLM prompt composition: project-owned agents must belong to the active project, inactive or foreign agents return 404, and universal system agents remain usable.
- Native tool calling falls back to text-based tool prompting when the selected project-scoped compute path has no tool-capable streaming node, allowing smaller donated relay models to answer instead of failing before the fallback path can run.
- Chat's native-tool and text-fallback ReAct loops enter through `AgenticDispatcher`. The legacy executor preserves project-scoped provider selection, tool authorization, hallucinated-tool filtering, and the SSE envelope; native provider content is forwarded as it arrives rather than being buffered into one terminal route chunk.
- The Pi replacement candidate is opt-in through the configured request header or environment flag. When selected, `/api/chat` keeps the normal session, Prompt-RAG, Research Spine, SSE, and tool-call envelope while routing through the DeepSeek candidate node registered at runtime from Keychain with strict model routing: a candidate transport failure is surfaced as an SSE error and cannot fall through to another node. Each Pi `tool_call` is followed by a redacted `tool_result` receipt containing only the tool name, call handle, and success state; raw tool output and detailed errors never enter the public stream. Both native and text fallback tool loops emit the same Pi chat-run metrics span; its `route_id` remains the bounded serving identity while token/tool accounting stays in the usage ledger. If registration is unavailable, the route emits a terminal `pi_registration_unavailable` SSE error and never falls back to the default provider transport.
- Pi Agentic Loop uses a bounded 24-model-turn horizon for interactive research work. Pi counts model turns around tool results, so this is intentionally wider than the legacy eight-tool window while remaining fail-closed with `turn_budget_exceeded`. Docker-only long-form benchmark turns must prove completion; an HTTP 200 alone is not acceptance.
- Chat-triggered Context-DAG compaction is scheduled through the ContextDAG lifecycle owner, deduplicated per session, and drained during application shutdown. This keeps asynchronous database work from outliving the event loop and prevents concurrent responses from creating duplicate compaction nodes.
- The composer fails closed for the legacy/Istara engine when `/api/chat/model-catalog` reports no passive cached chat readiness. Typed drafts, attachments, voice input, and pending-prefill auto-sends remain disabled until a connected model is ready, with an actionable Settings status; Pi keeps its own endpoint-resolution gate.
- Chat injects a protected Research Spine promotion gate into the runtime system prompt. Prompt-RAG, RAG snippets, tool output, and memories may support conversation, but chat must label provisional material and cannot present it as accepted research.
- The `search_findings` system action returns each finding with accepted/provisional/reportable status so ReAct/tool-assisted chat answers preserve the same gate state shown in Findings and Reports.
- Steering status/input is a global-admin capability in the current backend contract. Researcher chat sessions must not mount steering polling or steering mutation controls during normal chat journeys; negative authorization tests may still assert that researcher calls are rejected.
- Voice transcription uploads must carry the active project id and pass project researcher authorization before Istara reads audio bytes or invokes transcription. Missing, blank, hidden, or viewer-only project claims fail before audio processing.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- MCP-related behavior must keep access policy, audit evidence, and tool/resource exposure synchronized with the cited route or integration component.
- RAG-related behavior depends on project context, documents, memory, or retrieval material referenced by the cited stores and routes.
- Agent persona and system-prompt loading only occurs after the stored `agent_id` is proven assignable to the active project session.

## Tests And Verification

- `tests/test_chat.py`
- `tests/test_pi_replacement_candidate.py`
- `tests/test_sessions.py`
- `tests/test_project_rbac.py`
- `tests/test_project_scope_contracts.py`

## Related Features

- [chat.sessions](../../chat/sessions/architecture.md)
- [chat.model-controls](../../chat/model-controls/architecture.md)
- [chat.files](../../chat/files/architecture.md)
- [chat.audio](../../chat/audio/architecture.md)
- [chat.steering](../../chat/steering/architecture.md)

## Related Concepts

- [rag](../../../glossary/rag.md)
- [mcp](../../../glossary/mcp.md)

## Compass Evidence

- Spec/task: CF-SPEC-102 / CF-1295; CF-SPEC-3 / CF-38
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
