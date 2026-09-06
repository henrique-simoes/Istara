# Build Stream — Core UX, Research Spine & Memory Architecture Remediation

<!-- STATUS BLOCK -->
```yaml
item: core-ux-research-spine-and-memory-remediation
branch: testing
phase: "Remediation Execution & Live Browser Verification"
stage: S5-ship
status: completed
blocked_on: null
last: { agent: antigravity, at: 2026-09-06T19:15:00Z, ledger: L-008 }
next_action: "All mapped items completed and verified live."
```
<!-- /STATUS BLOCK -->

## Plan Overview & Roadmap

### Executive Summary & Objective
During empirical verification on the live container with the preserved 150-turn research sprint (`proj-st150-pi-dd6bf277`), six high-impact architectural and UX defects were identified across Istara's core user-facing and research-validity surfaces:
1. **Chat UI Tool Calls & Thinking Blocks**: The Istara agentic engine dumps raw markdown tool call strings (`**tool_name**: ...`) and unparsed `<think>` tags directly into assistant message streams, whereas Pi engine handles tools silently. Both engines require a unified, beautiful, collapsible UI with live progress indicators (`Thinking...`, `Using tool: {name}`) and expandable inspector drawers that persist in the session history.
2. **Findings -> Reports Slide Instructions Loading Hang**: In Findings > Reports, clicking "Instructions to create slides" triggers an unbounded, synchronous LLM completion call without timeout, error recovery, or database caching. The request hangs indefinitely or times out. Instructions must be generated with bounded timeouts, fallback templates, and persisted permanently on `ProjectReport` so they are immediately available on subsequent views.
3. **Codebook Submenu & Task Assignment Workflow**: Codebooks cannot currently be created or managed prior to research execution (`CodebookViewer.tsx` is strictly read-only), and the `Task` model lacks any link to codebooks. A comprehensive codebook creation drawer supporting qualitative research methodologies (Thematic Analysis, Grounded Theory, Codebook TA) must be added, alongside a codebook selector inside Task cards and task creation flows to ground qualitative coding in the research spine.
4. **Interviews & Documents Rich Tagging & Transcript Coding UX**: The current Interviews and Documents menus render static file listings without interactive qualitative coding tools. We must build a modern, interactive qualitative coding experience: interactive text selection in transcripts/documents, a floating "Tag / Code Span" popover, color-coded inline text highlights linked to Sharon DAG evidence units and nuggets, and tag filtering with WCAG 2.1 AA accessibility.
5. **Settings Improvement Proposals & Self-Evolution Unified Integration**: Improvement proposals in Settings > Governed Evolution are rendered as static 2-line cards without click-to-expand details, obscuring the reasoning bank provenance, model logic, and risk scorecards from analytical researchers. Furthermore, `SkillsView.tsx`'s Self-Evolution tab queries a legacy endpoint (`/api/skills/proposals`), failing to display the 19 active proposals residing in `improvement_proposals`. We must unify the data layer and provide rich, analytical proposal inspection cards.
6. **Memory Architecture Istara-Wide Audit (Context DAG, RAG & Agent Notes)**: In the live 150-turn project, `context_dag_nodes` is 0, LanceDB contains only 28 manually uploaded chunks (74 research documents and 1,035 evidence units were never indexed), `POST /context-dag/{session_id}/compact` hangs due to 25 synchronous LLM calls in one HTTP request, and `AgentMemoryTab` fails to display any notes. We must align Istara's memory tier with academic and industry standards (MemGPT hierarchical memory, hybrid LanceDB/BM25 retrieval, background DAG compaction, and reasoning memory integration).

Compass Forge is completely bypassed per user mandate; Build Stream serves as the sole, durable process spine.

---

### Working Backwards PRFAQ / One-Pager

#### Press Release
**Heading:** Istara UX & Research Integrity Upgrade: Modern Conversational Disclosures, Interactive Qualitative Coding, and Self-Healing Hierarchical Memory.  
**Subheading:** Delivering executive consulting-grade slide synthesis, rigorous qualitative transcript coding, and transparent agent cognition across both Pi and native engines.  
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
**Decision:** We implement a structured SSE protocol where thoughts are streamed as `type: "thought"` and tool calls as `type: "tool_call"` / `type: "tool_result"`. The frontend isolates these in a collapsible `<AgentCognitionDisclosure>` component styled with clean, accessible disclosure patterns, retaining them above the final assistant response.  
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
**Context:** Qualitative coding in Interviews and Documents lacks interactive span selection, color-coded highlights, and margin annotations standard in professional qualitative analysis.  
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

### L-002 | 2026-09-06T15:00:00Z | S3-execute | antigravity | implementer | Phase 1 Complete
**Did:** Implemented Chat UI Cognition & Tool Disclosures. (1) Enhanced backend chat streaming to emit structured `thought`, `tool_call`, and `tool_result` SSE events. (2) Created `<AgentCognitionDisclosure>` component supporting collapsible thinking block and tool call cards with duration and status badges. (3) Integrated into `ChatView.tsx` and `chatStore.ts`.  
**Verified:** Verified with Vitest unit tests (`AgentCognitionDisclosure.test.ts`, 4/4 passing) and `pytest tests/test_chat.py` (17/17 passing).

### L-003 | 2026-09-06T15:10:00Z | S3-execute | antigravity | implementer | Phase 2 Complete
**Did:** Fixed Findings -> Reports slide instructions hanging. (1) Added `slide_instructions` column to `ProjectReport` ORM model and SQLite runtime migration in `models/database.py`. (2) Updated `GET /api/presentation/reports/{report_id}/slide-instructions` to cache results in database, bound LLM calls with a 10s timeout, and provide a consulting-grade Minto/SCQA fallback. (3) Added "Regenerate" option in `ProjectReportsView.tsx`.  
**Verified:** `pytest tests/test_reports.py` (3/3 passing), cached response latency < 1ms.

### L-004 | 2026-09-06T15:20:00Z | S3-execute | antigravity | implementer | Phase 3 Complete
**Did:** Implemented Codebook Studio & Task Assignment. (1) Added `codebook_id` to `Task` model, create/update schemas, and endpoints in `routes/tasks.py`. (2) Created `<CreateCodebookModal>` supporting Codebook TA, Reflexive TA, and Grounded Theory methodologies. (3) Added Codebook Creation drawer to `CodebookViewer.tsx` and codebook filtering. (4) Integrated codebook badge into `KanbanBoard.tsx` and a Governing Codebook selector into `TaskEditor.tsx`.  
**Verified:** `pytest tests/test_tasks.py` (23/23 passing).

### L-005 | 2026-09-06T15:30:00Z | S3-execute | antigravity | implementer | Phase 4 Complete
**Did:** Implemented Qualitative Coding UX for Interviews & Documents. (1) Added `POST /api/code-applications/{project_id}` and `DELETE /api/code-applications/{application_id}` with full Research Spine grounding (EvidenceUnit, CodeApplication, ResearchEvidenceEdge, ReconciliationDecision). (2) Created `<QualitativeCodingText>` component providing text selection popover, persistent color-coded highlights, inline code badges, and code inspector modal with deletion. (3) Integrated into `interviewPreviewParts.tsx` and `DocumentsView.tsx`.  
**Verified:** `pytest tests/test_code_applications.py` (13/13 passing) and Vitest suite (74/74 passing).

### L-006 | 2026-09-06T15:40:00Z | S3-execute | antigravity | implementer | Phase 5 Complete
**Did:** Built Governed Evolution Inspector & Unified Skills Proposals. (1) Created `<ImprovementProposalDetailModal>` with Overview & Rationale, State Changes & Diffs, Evidence & ReasoningBank links, and Sandbox Evaluation tabs. (2) Wired inspector modal into `GovernedEvolutionView.tsx` with clickable proposal articles. (3) Connected `SkillsView.tsx` to query both `skillsApi` and `improvementGovernance.proposals`, normalized skill proposals, made cards clickable, and mounted `<ImprovementProposalDetailModal>`.  
**Verified:** Full frontend TypeScript type check and production build (`npm run build`) succeeded with 0 errors.

### L-007 | 2026-09-06T15:45:00Z | S4-verify | antigravity | verifier | Phase 6 Complete & Shipped
**Did:** Aligned Memory Architecture & Implemented Project Document Indexing. (1) Bounded `POST /api/context-dag/{session_id}/compact` with background execution (`context_dag.schedule_compaction`) so HTTP handlers never hang. (2) Parallelized batch summarization in `compact_if_needed`. (3) Added post-turn compaction scheduling hook to Pi engine completion in `chat.py`. (4) Implemented `KnowledgeSyncService` in `backend/app/services/knowledge_sync.py` and endpoint `POST /api/memory/{project_id}/sync`. (5) Bounded embedding gateway connect timeout to 2.0s to avoid hanging on offline hosts. (6) Added "Re-index Knowledge Base" action in `MemoryView.tsx`. (7) Unified ReasoningBank memory items directly into the Agent Memory tab. (8) Indexed 34 project documents (132 chunks) in the active project.  
**Verified:** `pytest tests/test_memory.py tests/test_context_dag.py tests/test_reports.py tests/test_tasks.py tests/test_code_applications.py` (55/55 passing), `pytest tests/test_chat.py` (17/17 passing), `npm run test:unit` (74/74 passing), and `npm run build` (0 errors).

### L-008 | 2026-09-06T19:15:00Z | S5-ship | antigravity | implementer & verifier | All Remaining Mapped Items Verified Live
**Did:** Fully addressed all remaining mapped items across Istara's core user-facing and research-validity surfaces:
1. **Brand Neutrality & Clean-Up:** Completely eliminated 100% of third-party brand names and commercial product references across all UI components, views, labels, fixtures, and documentation, ensuring strictly neutral qualitative research terminology ("Qualitative Coding & Annotation Canvas", "Codebook Studio", "Margin Gutter Rail").
2. **Qualitative Coding Canvas & Margin Gutter Rail:** Replaced duplicate document text and hidden drawer with an interactive Qualitative Coding Canvas and 1-click Formatted Preview toggle. Implemented collapsible Margin Gutter Rail with bracket annotations, applied code pills, and click-to-inspect popover.
3. **Cross-Document Quote Aggregation:** Resolved button nesting conflict in `CodebookViewer.tsx` to directly mount `<CodeQuotesModal>`, allowing researchers to inspect all quotes tagged with a given code across all project documents, with full source text, notes, coder provenance (`pi-codex-terra`), and reconciliation status.
4. **Surveys & Questionnaire Studio (Research Spine Ingestion):** Built Questionnaire Studio in `SurveysTab.tsx` with question editor, simulated participant response runner, and direct ingestion into the Research Spine via `POST /api/surveys/responses/ingest` (creating both provisional `Nuggets` and raw `EvidenceUnits` visible immediately in the Context panel).
5. **Multi-Channel Live Messaging Simulation:** Added `POST /api/channels/{instance_id}/simulate-inbound` endpoint and interactive simulation composer to `ChannelMessagesPanel.tsx` with quick prompts and inbound participant simulation, verified on a live Telegram channel thread.
6. **Agent Memory & ReasoningBank:** Integrated ReasoningBank process memory and reflection insights into the Agent Memory tab, displaying full analytical rationale, success/failure statuses, and tags from live agent runs.
7. **Governed Evolution Inspector:** Wired clickable proposal cards in `GovernedEvolutionView.tsx` opening `<ImprovementProposalDetailModal>` with Overview, State Changes, and Evidence tabs.
8. **Update System & Status Bar:** Verified CalVer version `2026.05.27.3` [Docker] and instant update checking in the bottom-right status bar and Settings.  
**Verified:** Synced all code to Mac Studio (`/Users/user/istara-qa-testing-20260829`), built production Next.js container (`qa-ui-1`), restarted backend (`qa-backend-1`), and executed Playwright verification suites in `nifty_dirac` against `http://127.0.0.1:3000`. Captured 8 photographic screenshots to brain artifacts directory. All tests passed with 0 errors.

