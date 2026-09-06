# Build Stream — Core UX, Research Spine & Memory Architecture Remediation

<!-- STATUS BLOCK -->
```yaml
item: core-ux-research-spine-and-memory-remediation
branch: testing
phase: "Roadmap & Architecture Framing"
stage: S0-frame
status: in-progress
blocked_on: null
last: { agent: antigravity, at: 2026-09-06T14:45:00Z, ledger: L-001 }
next_action: "Present comprehensive Build Stream remediation plan to operator for review and phase sequencing approval."
```
<!-- /STATUS BLOCK -->

## Plan Overview & Roadmap

### Executive Summary & Objective
During empirical verification on the live container with the preserved 150-turn research sprint (`proj-st150-pi-dd6bf277`), six high-impact architectural and UX defects were identified across Istara's core user-facing and research-validity surfaces:
1. **Chat UI Tool Calls & Thinking Blocks**: The Istara agentic engine dumps raw markdown tool call strings (`**tool_name**: ...`) and unparsed `<think>` tags directly into assistant message streams, whereas Pi engine handles tools silently. Both engines require a unified, beautiful, collapsible UI (inspired by Claude, ChatGPT o1/o3, and OpenWebUI) with live progress indicators (`Thinking...`, `Using tool: {name}`) and expandable inspector drawers that persist in the session history.
2. **Findings -> Reports Slide Instructions Loading Hang**: In Findings > Reports, clicking "Instructions to create slides" triggers an unbounded, synchronous LLM completion call without timeout, error recovery, or database caching. The request hangs indefinitely or times out. Instructions must be generated with bounded timeouts, fallback templates, and persisted permanently on `ProjectReport` so they are immediately available on subsequent views.
3. **Codebook Submenu & Task Assignment Workflow**: Codebooks cannot currently be created or managed prior to research execution (`CodebookViewer.tsx` is strictly read-only), and the `Task` model lacks any link to codebooks. A comprehensive codebook creation drawer supporting qualitative research methodologies (Thematic Analysis, Grounded Theory, Codebook TA) must be added, alongside a codebook selector inside Task cards and task creation flows to ground qualitative coding in the research spine.
4. **Interviews & Documents Rich Tagging & Transcript Coding UX**: The current Interviews and Documents menus render static file listings without interactive qualitative coding tools. We must build a modern, interactive qualitative coding experience (reflecting Dovetail, ATLAS.ti, MAXQDA, NVivo): interactive text selection in transcripts/documents, a floating "Tag / Code Span" popover, color-coded inline text highlights linked to Sharon DAG evidence units and nuggets, and tag filtering with WCAG 2.1 AA accessibility.
5. **Settings Improvement Proposals & Self-Evolution Unified Integration**: Improvement proposals in Settings > Governed Evolution are rendered as static 2-line cards without click-to-expand details, obscuring the reasoning bank provenance, model logic, and risk scorecards from analytical researchers. Furthermore, `SkillsView.tsx`'s Self-Evolution tab queries a legacy endpoint (`/api/skills/proposals`), failing to display the 19 active proposals residing in `improvement_proposals`. We must unify the data layer and provide rich, analytical proposal inspection cards.
6. **Memory Architecture Istara-Wide Audit (Context DAG, RAG & Agent Notes)**: In the live 150-turn project, `context_dag_nodes` is 0, LanceDB contains only 28 manually uploaded chunks (74 research documents and 1,035 evidence units were never indexed), `POST /context-dag/{session_id}/compact` hangs due to 25 synchronous LLM calls in one HTTP request, and `AgentMemoryTab` fails to display any notes. We must align Istara's memory tier with academic and industry standards (MemGPT hierarchical memory, hybrid LanceDB/BM25 retrieval, background DAG compaction, and reasoning memory integration).

Compass Forge is completely bypassed per user mandate; Build Stream serves as the sole, durable process spine.

---

### Working Backwards PRFAQ / One-Pager

#### Press Release
**Heading:** Istara UX & Research Integrity Upgrade: Modern Conversational Disclosures, Interactive Qualitative Coding, and Self-Healing Hierarchical Memory.  
**Subheading:** Delivering executive consulting-grade slide synthesis, Dovetail-quality qualitative transcript coding, and transparent agent cognition across both Pi and native engines.  
**Summary:** Istara today announces a major system-wide remediation of its user experience and research memory architecture. Researchers and executives can now observe agent cognition through beautiful, collapsible thinking and tool disclosure blocks; highlight and code interview transcripts and documents interactively with full Sharon DAG grounding; pre-define methodological codebooks and assign them to research tasks; inspect self-evolution proposals with complete audit trails; and rely on a robust, automatically indexed hybrid vector and Context DAG memory system that never stalls or hangs.  
**Problem:** Researchers using AI tools face two extremes: opaque "black box" text generation that hides errors and hallucinations, or raw, noisy developer logs that litter transcripts with syntax noise. Furthermore, qualitative analysis tools frequently isolate coding from downstream reports, and agent memory systems degrade into silent failures without proper indexing or compaction.  
**Solution:** Istara unifies rigorous qualitative methodology with intuitive consumer-grade interface design. Every tool call and internal thought is neatly organized in interactive disclosures. Transcripts and documents support rich, color-coded span tagging that traces directly to atomic nuggets and reports. Memory systems operate asynchronously in the background, ensuring immediate interface responsiveness and persistent recall.

#### Internal FAQ
- **Why did thinking blocks and tool calls appear as raw text in Istara legacy engine but not Pi?**  
  In the legacy ReAct dispatcher, tool execution output was formatted as markdown text (`result_display = f"**{name}**: {result_text}\n\n"`) and queued into content chunks, while `<think>` tokens from reasoning models were streamed without structured envelope demarcation. Pi engine encapsulated tool calls inside the `pi-agent-core` loop. We resolve this by emitting typed SSE events (`type: "thought"`, `type: "tool_call"`, `type: "tool_result"`) across both engines and rendering them via a shared client component `<AgentCognitionDisclosure>`.
- **Why did "Instructions to create slides" hang?**  
  The endpoint `GET /api/presentation/reports/{report_id}/slide-instructions` executed `await agentic.completion(...)` with an open-ended timeout on every request. If the LLM provider took long or was unreachable, the HTTP request hung. Furthermore, the report never saved generated instructions. We fix this by persisting instructions in `report.slide_instructions`, applying a 10s timeout with a consulting Minto Pyramid template fallback, and providing instant cached retrieval.
- **Why was `context_dag_nodes` 0 in the 150-turn sprint?**  
  The compaction schedule hook (`context_dag.schedule_compaction`) was only invoked in the legacy chat endpoint. Pi engine turns never triggered it. When manually requested via `POST /context-dag/{session_id}/compact`, the endpoint ran 25 sequential LLM calls synchronously inside the HTTP handler. We fix this by adding the post-turn hook to Pi engine, offloading compaction to an asynchronous background worker, and implementing fast batching.
- **Why did LanceDB have only 28 chunks when 74 documents exist?**  
  Document creation in the `documents` table was decoupled from `VectorStore.ingest_chunks`. Only chat file uploads ran through RAG chunking. We add a project-wide indexing service that synchronizes all project documents, evidence units, and interview transcripts into LanceDB and BM25.

---

### Appetite & Scope
- **Appetite:** Multi-phase comprehensive remediation. High quality, zero regressions, full test coverage.
- **In Scope:**
  - **Phase 1: Chat UI Cognition & Tool Disclosures** (`frontend/src/components/chat/`, `chatStore.ts`, `chatApi.ts`, `backend/app/api/routes/chat.py`).
  - **Phase 2: Findings Reports Slide Instructions Reliability & Caching** (`ProjectReportsView.tsx`, `presentation.py`, `models/project_report.py`).
  - **Phase 3: Codebook Studio & Task Assignment** (`CodebookViewer.tsx`, `TaskCard.tsx`, `KanbanBoard.tsx`, `models/task.py`, `routes/codebooks.py`).
  - **Phase 4: Qualitative Coding UX: Interviews & Documents Tagging** (`InterviewView.tsx`, `DocumentsView.tsx`, `interviewPreviewParts.tsx`, `TagCreatePopover.tsx`).
  - **Phase 5: Governed Evolution & Proposal Detail Inspector** (`GovernedEvolutionView.tsx`, `SkillsView.tsx`, `routes/improvement_governance.py`, `routes/skills.py`).
  - **Phase 6: Memory System Istara-Wide Alignment & Indexing** (`ContextDAGView.tsx`, `MemoryView.tsx`, `context_dag.py`, `agent_memory.py`, `rag.py`).
- **Non-Goals:**
  - Replacing LanceDB with an external cloud vector database.
  - Altering the Sharon DAG research validity contract.
  - Rewriting the core Pi agent runtime.

---

### Phased Breakdown

| Phase | Initiative | Core Deliverables | Target Verification |
|---|---|---|---|
| **Phase 1** | **Chat UI Cognition & Tool Disclosures** | `<AgentCognitionDisclosure>`, collapsible thinking accordion, tool card with inputs/outputs, SSE `thought` / `tool_call` separation | Unit tests + Playwright Chat UI inspection |
| **Phase 2** | **Reports Slide Instructions & Caching** | Report model `slide_instructions` column, 10s bounded timeout + Minto fallback, instant cached return | Pytest presentation suite + UI modal test |
| **Phase 3** | **Codebook Studio & Task Binding** | Create codebook modal (Thematic, Grounded Theory, Codebook TA), `Task.codebook_id` DB migration, Task Card codebook selector | Pytest codebooks + Kanban task assignment tests |
| **Phase 4** | **Interviews & Documents Tagging UX** | Interactive text selection, span tagging popover, color-coded highlights, margin code badges, interview transcript viewer | Qualitative coding Playwright test + WCAG 2.1 AA audit |
| **Phase 5** | **Governed Evolution Analytical Inspector** | Clickable proposal detail card (provenance, ReasoningBank links, logic, diffs), unified proposal query in `SkillsView` | Pytest improvement governance + Skills tab verification |
| **Phase 6** | **Memory & Context DAG Alignment** | Asynchronous background DAG compaction, Pi turn hook, full project document indexing into LanceDB & BM25, Agent Memory reasoning integration | Pytest context DAG + LanceDB health verification |

---

## Decision Log

### DEC-001 | 2026-09-06 | S0-frame | antigravity
**Context:** User requested a comprehensive Build Stream plan addressing six interrelated UI and architectural defects across Chat, Reports, Codebooks, Interviews/Documents, Self-Evolution, and Memory.  
**Decision:** We frame this initiative under a unified Build Stream plan file (`docs/build-stream/2026-09-06-core-ux-research-spine-and-memory-remediation.md`) structured in 6 sequential phases. Compass Forge is completely bypassed per operator instruction.  
**Why:** Maintains a single durable source of truth that survives branch merges and provides clear stage boundaries from S0-frame through S5-ship.

### DEC-002 | 2026-09-06 | S0-frame | antigravity
**Context:** In the Chat UI, thinking tokens (`<think>`) and tool call outputs (`**tool**: ...`) currently intermingle with conversational text.  
**Decision:** We implement a structured SSE protocol where thoughts are streamed as `type: "thought"` and tool calls as `type: "tool_call"` / `type: "tool_result"`. The frontend isolates these in a collapsible `<AgentCognitionDisclosure>` component styled after OpenWebUI and modern frontier lab chats, retaining them above the final assistant response.  
**Why:** Delivers clean, professional conversational output while keeping full auditability of agent reasoning and tool usage.

### DEC-003 | 2026-09-06 | S0-frame | antigravity
**Context:** "Instructions to create slides" hangs or times out because it executes an unbuffered LLM call on every click without persistence.  
**Decision:** Add a `slide_instructions` column to `project_reports`. On request, return persisted instructions immediately if present. If absent, execute with a strict 10s timeout, falling back to a consulting-grade Minto Pyramid / SCQA template, and save the result to the database.  
**Why:** Guarantees zero latency on subsequent clicks, eliminates UI freezing, and ensures executive slide instructions are always available.

### DEC-004 | 2026-09-06 | S0-frame | antigravity
**Context:** Codebooks are view-only and disconnected from task execution. Researchers cannot create codebooks beforehand or assign them to tasks.  
**Decision:** (1) Add a Codebook Creator modal in `CodebookViewer` supporting qualitative coding methods. (2) Add `codebook_id` to the `tasks` table. (3) Provide a codebook selector inside Task cards and modals. (4) Inject the selected codebook into agent prompts during qualitative coding tasks.  
**Why:** Grounds agent task execution in user-defined qualitative codebooks, enforcing the Research Spine methodology.

### DEC-005 | 2026-09-06 | S0-frame | antigravity
**Context:** Qualitative coding in Interviews and Documents lacks interactive span selection, color-coded highlights, and margin annotations found in ATLAS.ti, MAXQDA, and Dovetail.  
**Decision:** Implement an interactive text-selection qualitative coding engine for both Interviews and Documents: selecting text opens a `<TagCreatePopover>` to attach a code, applying a persistent highlight connected to `evidence_units` and `nuggets`.  
**Why:** Transforms Istara from a static text viewer into a professional, interactive qualitative research platform.

### DEC-006 | 2026-09-06 | S0-frame | antigravity
**Context:** Settings improvement proposals are not clickable to view analytical details, and skill evolution proposals do not appear in the Skills > Self-Evolution menu.  
**Decision:** (1) Create an `<ImprovementProposalDetailModal>` displaying provenance, ReasoningBank memory links, model rationale, confidence, and state diffs. (2) Unify `SkillsView` to query `improvement_proposals` where `source_system == 'skill_evolution'` or `affected_surfaces` contains `skills`.  
**Why:** Provides full decision transparency for analytical researchers and eliminates fragmented data silos.

### DEC-007 | 2026-09-06 | S0-frame | antigravity
**Context:** `context_dag_nodes` is 0 in the 150-turn sprint, LanceDB lacks document chunks, and `POST /context-dag/.../compact` hangs due to 25 synchronous LLM calls.  
**Decision:** (1) Make DAG compaction asynchronous via a background task worker with fast batching. (2) Wire compaction scheduling into Pi engine turns. (3) Provide an automatic project-wide document ingestion pipeline into LanceDB and KeywordIndex. (4) Unify Agent Memory to display both vector notes and reasoning bank insights.  
**Why:** Aligns Istara with academic hierarchical memory architectures (MemGPT) and prevents UI gateway timeouts.

---

## Ledger

### L-001 | 2026-09-06T14:45:00Z | S0-frame | antigravity | framer | Roadmap
**Did:** Investigated and empirically diagnosed all 6 issue areas on the live Mac Studio container and local codebase. Identified root causes: (1) unparsed tool/think text strings in chat, (2) unbuffered LLM calls and missing report persistence for slide instructions, (3) read-only codebook UI and missing `codebook_id` in tasks, (4) static document/interview views without interactive span tagging, (5) unclickable proposal cards and split endpoints between Settings and Skills, (6) missing Pi DAG compaction trigger, synchronous compaction hang, and unindexed project documents in LanceDB. Authored comprehensive Build Stream initiative document and decision log.  
**Result:** Build Stream plan established in `docs/build-stream/2026-09-06-core-ux-research-spine-and-memory-remediation.md`. Ready for operator review.  
**Verified:** Verified live container DB tables, route handlers, frontend stores, and timeout behaviors.  
**Next:** Submit implementation plan artifact for operator approval, then advance Phase 1 to S1-plan.
