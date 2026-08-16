# Istara Stabilization Audit — 2026-04-30

Status: Compass documentation update for the long stabilization session on `codex/compute-pool-access-connectivity-audit`.

This note records product, backend, frontend, and test changes made during the session so future agents do not have to infer them from scattered diffs.

## Scope

The session focused on integration gaps across Compute Pool, Settings, Tasks, Findings, Documents, Interfaces, Meta-Agent, Skills, Agents, MCP, UX Laws, Autoresearch, and live status indicators. The work was mostly stabilization: making persisted backend state, frontend surfaces, and Compass expectations match the real product behavior.

## Compute, LLM Discovery, and Status

- Network LLM discovery now rejects endpoints that do not advertise real provider-shaped model lists. OpenAI-compatible/LM Studio discovery requires `data[].id`; Ollama discovery requires `models[].name`.
- The attempted automatic deduplication of same-subnet LLM servers by identical model catalog was reverted because it could hide two legitimate production machines configured identically.
- Future duplicate-server handling must use stronger identity evidence or an explicit admin review/merge/ignore workflow, not silent catalog heuristics.
- The bottom-left connection label was clarified. It now describes the browser live-events WebSocket, not backend availability or LLM availability.
- The live-events WebSocket hook retries after stale/missing auth token states and reconnects when authentication changes.

## Autoresearch and Metrics

- Autoresearch status now exposes operational metrics needed by the frontend, including task review, compute, telemetry, agent, pipeline, and collection context.
- The Autoresearch dashboard was updated to display the newer task and compute metrics from the task-review and compute-pool work.
- Compass note: Autoresearch is a cross-cutting consumer of Tasks, ComputeRegistry, telemetry, model-skill stats, and agent state. Metrics changes must be verified in both backend payloads and frontend panels.

## Meta-Agent

- Recent Meta-Agent observations are persisted and returned with status so a restart does not leave proposals visible with no explanatory observation state.
- The frontend now distinguishes disabled observation loops from persisted pending proposals.
- Pending proposal confidence bars are clamped to prevent layout overflow.
- Empty observation metrics now explain when no observations have been collected this session.
- Product rule: a disabled Meta-Agent may still show persisted proposals, but the UI must explain the lifetime split between persisted proposals and observation snapshots.

## Documents, Interviews, Tags, and Codebooks

- Documents became the source-of-truth tag surface across document tags, nugget tags, and code applications.
- Tags produced from Interviews/agent analysis now propagate into Documents and codebook views where applicable.
- The Codebook tab in Findings now has a fallback path to legacy codebook data and can derive codebook content from nuggets/code applications when no explicit version exists.
- Document preview path/content handling was tightened so simple text files can render reliably in the Documents preview.
- Onboarding's "Add research files" step now routes to the Documents upload surface instead of remaining in Settings.
- Generated skill artifacts now follow a two-surface contract: researchers see a readable Markdown Document, while agents/RAG retain structured/raw content for machine reuse.
- Markdown/generated artifacts render as formatted Markdown in Documents instead of monospaced raw JSON.

## Findings and Evidence Chains

- The evidence-chain endpoint now returns diagnostics for supporting counts, missing links, and whether support exists below the selected item.
- Recommendation chains include the normal Recommendation -> Insight -> Fact -> Nugget path when links exist.
- The frontend no longer treats the selected Recommendation itself as supporting evidence.
- Empty evidence-chain states no longer claim there is a raw quote/observation when no chain exists. They now explain missing supporting evidence and show where the chain stops.
- Current data audit found recommendations linked to insights while those insights lacked fact links, so some missing chains are a deeper data integrity gap, not only a frontend bug.

## Tasks and Kanban

- Native drag behavior was restored after the task-review change.
- Attempts to drag Done tasks backward are blocked with explanatory messaging directing users to Request Revision, because Done represents human approval.
- Attempts to drag directly into Done are blocked when the review workflow requires explicit review/approval.
- Task cards and the task editor expose task labels/tags, including system-derived tags with hover explanations.
- Compass rule: Done is human-approved, not merely agent-completed. Any Kanban workflow change must preserve review/revision semantics.

## Skills and Self-Evolution

- The Skills Self-Evolution tab now shows proposal diagnostics, verification status, promotion readiness, and refresh/error feedback.
- Skill creation proposals persist verification/test results.
- Approval runs verification when needed and blocks promotion on failed verification.
- A verification endpoint was added for self-evolution proposals.
- Product rule: promotion must remain evidence-backed and test-gated; the UI should make proposal state and verification state explicit.

## Agents and Personas

- Piper/design-lead was added as a first-class system agent role in backend/frontend role lists and the orchestrator.
- The system seed updates Piper/design-lead role/capabilities.
- `design-lead/CORE.md` now identifies Piper as the Istara Interface Agent.
- Persona creation now repairs incomplete runtime persona directories instead of treating them as valid.
- Test coverage now asserts hardcoded system agents have the required four persona files: `CORE.md`, `SKILLS.md`, `PROTOCOLS.md`, and `MEMORY.md`.

## UX Laws

- UX Laws compliance now distinguishes "not evaluated" from "100% compliant."
- Backend compliance profiles expose evaluated/evidence counts, total findings, and law-tag counts.
- Frontend compliance UI displays empty/not-evaluated states when no `ux-law:` evidence exists.
- Product rule: a perfect compliance score is only meaningful after relevant UX Law evidence has been evaluated.

## MCP Integrations

- MCP access policy updates now accept grouped frontend payloads and normalize them into explicit `allow_*` backend fields.
- The MCP tab now clearly distinguishes server disabled/enabled state from the command to enable/disable.
- Access Policy editor warnings/errors are displayed in the UI.
- Runtime installed state and exposure count are surfaced so "disabled but enable" ambiguity is reduced.

## Interfaces

- Design Chat assistant responses are now saved to the resolved design chat session instead of `null` session ids.
- The frontend tracks the design session id/project id and sends subsequent messages into the same session.
- Design Chat history reloads correctly when returning to Interfaces or switching projects.
- Design Chat assistant and streaming responses render Markdown/GFM like the main Chat menu.

## Live Status

- The status bar now says "Live updates" rather than vague "Realtime."
- Tooltip copy explains that this reflects the `/ws` live-events channel for agent/task/document/notification updates.
- HTTP API health and LLM server health are separate concepts and must not be conflated with live-event socket state.

## Tests Added or Updated

- `tests/test_agent_personas.py`
  - Verifies every hardcoded system agent has complete persona files.
  - Verifies Piper/design-lead is seeded.
  - Verifies incomplete runtime persona directories are repaired.
- `tests/test_document_preview_paths.py`
  - Covers document preview/path behavior for text-like files.
- `tests/test_network_discovery.py`
  - Covers strict provider-shaped model extraction for network discovery.

## Verification Performed During Session

Focused checks were run repeatedly after affected changes:

- `python -m py_compile` on changed backend modules.
- `pytest -q tests/test_agent_personas.py`
- `pytest -q tests/test_document_preview_paths.py`
- `pytest -q tests/test_network_discovery.py`
- `npm run build` for frontend changes.

The frontend build completed with existing lint warnings unrelated to this session's changes.

## Follow-Up Risks

- Duplicate LLM server aliases still need a production-grade design. Do not silently collapse nodes by identical model catalog.
- Existing data may contain incomplete Recommendation -> Insight -> Fact -> Nugget chains; repair/migration or integrity tooling may be needed.
- Compass simulation coverage should be expanded for Design Chat persistence, Meta-Agent observation persistence, task review drag guards, document/codebook tag sync, MCP policy payloads, and UX Laws not-evaluated state.
