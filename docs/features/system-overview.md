# Istara System Overview

A complete feature catalog for agents and users to understand all Istara capabilities.

## Core Philosophy

- **Local-first**: All data stays on the user's machine. No cloud dependency.
- **Privacy-first**: Research data never leaves user control unless explicitly configured.
- **Open methodology**: 53 UXR skills based on industry-standard research methods.
- **Agent-powered**: 5 specialized AI agents that learn and improve over time.
- **Cross-platform**: Native installers for macOS (.dmg) and Windows (.exe) with setup wizard.

## Feature Map

### Chat
Natural language interface to all Istara capabilities. Agents understand project context, available skills, and can execute research tasks from conversation.

### Findings
Atomic Research evidence chain: Nuggets (raw evidence) -> Facts (verified patterns) -> Insights (interpreted meanings) -> Recommendations (actionable proposals). Every finding traces back to its source.

### Tasks
Kanban board for managing research tasks. Tasks can be assigned to agents, linked to documents and skills, and prioritized (critical/high/medium/low).

### Interviews
Interview management with audio playback, transcript analysis, and finding extraction.

### Documents
Upload and manage research artifacts (PDF, DOCX, CSV, TXT, MD). Documents are automatically chunked, embedded, and indexed in the vector store for RAG retrieval.

### Context
Six-level context hierarchy: Platform -> Company -> Product -> Project -> Task -> Agent. Each level can be edited to provide rich context for LLM inference.

### Skills
53 UXR skills organized by Double Diamond phase (Discover/Define/Develop/Deliver). Skills can be executed manually or automatically by agents. The skill system is self-improving with quality monitoring and proposals.

### Agents
5 specialized agents with persistent identities, learnable memory, and self-evolution:
- **Cleo**: Primary research coordinator and task executor
- **Sentinel**: Data integrity and system health monitoring
- **Pixel**: UI audit (WCAG compliance, Nielsen heuristics)
- **Sage**: UX evaluation (cognitive load, user journeys)
- **Echo**: User simulation and end-to-end testing

### Memory
RAG-powered knowledge base per project. Hybrid search combining vector similarity (70%) with BM25 keyword search (30%).

### Interfaces
Design integration hub: Stitch (MCP-based AI design generation), Figma (REST API), design chat, screen generation, handoff specs.

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
Optional meta-agent that observes system performance and proposes parameter optimizations. Off by default. All changes require user approval.

### UX Laws
30 Laws of UX (Yablonski, 2024) with compliance scoring. Evaluate your design against cognitive psychology principles. Violation badges link directly to relevant findings.

### Compute Pool
Unified view of all LLM servers: local, network-discovered, and relay nodes. Donate compute from browser or desktop app. Connection strings for team relay setup.

### Settings
LLM server configuration, hardware detection, resource governance, team mode toggle, connection string generation, compute donation, and system preferences. Hardware shows server stats. Team members managed via invite form with role selection (admin/researcher/viewer).

### Desktop App
System tray app (macOS menubar / Windows system tray) for managing Istara:
- **Server mode**: Start/Stop server, open browser, compute donation, stats
- **Client mode**: Connection status, compute donation, change server
- Setup wizard on first launch with dependency installation

### Project Management
Projects support pause/resume/delete via sidebar context menu. External folder linking watches Google Drive, Dropbox, or any local folder. Documents auto-discovered by FileWatcher with cloud-sync temp file filtering.
