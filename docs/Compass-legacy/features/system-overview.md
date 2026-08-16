# Istara System Overview

> Status: Product-facing feature summary.
> Authority: Not a canonical development-control document. For live architecture and change obligations, start with `AGENT_ENTRYPOINT.md`.

A complete feature catalog for agents and users to understand all Istara capabilities.

## Core Philosophy

- **Local-first**: All data stays on the user's machine. No cloud dependency.
- **Privacy-first**: Research data never leaves user control unless explicitly configured.
- **Open methodology**: 53 UXR skills based on industry-standard research methods.
- **Agent-powered**: 5 specialized AI agents that learn and improve over time.
- **Cross-platform**: Native installers for macOS (.dmg) and Windows (.exe) with setup wizard.

## Feature Map

### Chat
Natural language interface to all Istara capabilities. Agents understand project context, available skills, and can execute research tasks from conversation. In team mode, Chat is project-scoped: invited viewers can read history but cannot send messages, upload files, create sessions, or spend model/agent work.

### Findings
Atomic Research evidence chain: Nuggets (raw evidence) -> Facts (verified patterns) -> Insights (interpreted meanings) -> Recommendations (actionable proposals). Finding drilldowns show the supporting chain when links exist and explain incomplete chains when evidence is missing.

### Tasks
Kanban board for managing research tasks. Tasks can be assigned to agents, linked to documents and skills, and prioritized (critical/high/medium/low). Done represents human approval, so review/revision controls govern movement into and out of Done.

### Interviews
Interview management with audio playback, transcript analysis, and finding extraction.

### Documents
Upload and manage research artifacts (PDF, DOCX, CSV, TXT, MD). Documents are automatically chunked, embedded, and indexed in the vector store for RAG retrieval. Documents are the broad tag surface for Istara, aggregating document tags, nugget/interview tags, and code-application tags where applicable. Istara-generated artifacts are shown as researcher-readable Markdown documents; raw JSON remains machine-facing for agents/RAG rather than the default UI surface.

### Context
Six-level context hierarchy: Platform -> Company -> Product -> Project -> Task -> Agent. Each level can be edited to provide rich context for LLM inference.

### Skills
53 UXR skills organized by Double Diamond phase (Discover/Define/Develop/Deliver). Skills can be executed manually or automatically by agents. The skill system is self-improving with quality monitoring, proposals, verification status, and gated promotion.

### Agents
Specialized agents have persistent identities, learnable memory, and self-evolution:
- **Cleo**: Primary research coordinator and task executor
- **Sentinel**: Data integrity and system health monitoring
- **Pixel**: UI audit (WCAG compliance, Nielsen heuristics)
- **Sage**: UX evaluation (cognitive load, user journeys)
- **Echo**: User simulation and end-to-end testing
- **Piper**: Design Lead / Interface Agent for Interfaces, design critique, and research-to-design translation

### Memory
RAG-powered knowledge base per project. Hybrid search combining vector similarity (70%) with BM25 keyword search (30%).

### Interfaces
Design integration hub: Stitch (MCP-based AI design generation), Figma (REST API), design chat, screen generation, handoff specs. Design Chat persists to a design-scoped chat session and renders assistant output with Markdown formatting. Viewer access is read-only; design chat sending and generation work require researcher-level project access or higher.

### Integrations
Multi-platform integration hub with 5 tabs:
- **Overview**: 24h activity dashboard across all integrations
- **Messaging**: Telegram, Slack, WhatsApp, Google Chat — multi-instance channel management
- **Surveys**: SurveyMonkey, Google Forms, Typeform — create surveys and ingest responses
- **Deployments**: Deploy interviews/surveys via messaging with adaptive questioning and real-time analytics
- **MCP**: Expose Istara to external agents (server) or connect external tools (client)

### Loops & Schedule
Recurring task execution on configurable intervals per agent.

### Notifications
9 event types broadcast via WebSocket with configurable preferences per category.

### Backup
Automated incremental/full backups with retention policy, restore, and verification.

### Meta-Agent (Experimental)
Optional meta-agent that observes system performance and proposes parameter optimizations. Off by default. All changes require user approval. Proposals may persist after the observation loop is disabled; recent observations are persisted separately and the UI explains when no observations have been collected in the current session.

### UX Laws
30 Laws of UX (Yablonski, 2024) with compliance scoring. Evaluate your design against cognitive psychology principles. Violation badges link directly to relevant findings. Compliance views distinguish "not evaluated" from actual 100% compliance when no UX-law evidence exists.

### Compute Pool
Unified view of all LLM servers: local, network-discovered, and relay nodes. Donate compute from browser or desktop app. Connection strings support team relay setup. Network discovery requires provider-shaped model advertisements; duplicate-alias handling should be explicit/admin-reviewed rather than silently collapsing identical model catalogs.

### Settings
LLM server configuration, hardware detection, resource governance, team mode toggle, connection string generation, compute donation, and system preferences. Hardware shows server stats. Team members managed via invite form with role selection (admin/researcher/viewer). Team authorization is enforced server-side: global admins manage all projects and system settings; project members see only invited projects. User invite strings and compute donation strings are distinct token kinds so a compute node cannot redeem user access.

### Admin Dashboard
Admin-only operational view for global users, project inventory, project access, compute health, usage collection status, and connection-string visibility. It uses `/api/admin/*` endpoints and existing project/auth/connection APIs for inline role changes, project access grants, project deletion, user invite generation, and compute donation string generation. It labels unavailable token/compute accounting as not collected instead of implying zero usage. Admin/security-sensitive route families now require global admin for system operations such as MCP client/tool calls, backup reads/writes, schedules, autoresearch controls, agent self-evolution, steering, compute pool readouts, Meta-Hyperagent controls, channels, loops, audit logs, and global survey integrations.

### Desktop App
System tray app (macOS menubar / Windows system tray) for managing Istara:
- **Server mode**: Start/Stop server, open browser, compute donation, stats
- **Client mode**: Connection status, compute donation, change server
- Setup wizard on first launch with dependency installation

### Project Management
Projects support pause/resume/delete via sidebar context menu. External folder linking watches Google Drive, Dropbox, or any local folder. Documents auto-discovered by FileWatcher with cloud-sync temp file filtering. In team mode, global admins see every project; project admins, researchers, and viewers only see projects they were invited to. Project API responses include the current user's project role for frontend role-aware controls. Uninvited project access is concealed as not found, while forbidden operations inside visible projects return an explicit permission error. Viewers are read-only across locked-down Chat, sessions, Interfaces Design Chat, Tasks, Documents, Findings, Codebooks, Files, Memory, Metrics, Reports, UX Laws compliance, Deployments, Code Applications, Codebook Versions, presentation instructions, Interfaces screens/Figma/handoff/mock endpoints, and project-scoped Skill execution/planning.
