# Changelog

All notable changes to Istara are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). Versions use [CalVer](https://calver.org/) in the format `YYYY.MM.DD`.

**Note:** As of April 2026, `CHANGELOG.md` is a core Compass document. Agents MUST update this file for all releases and major feature shipments to maintain human-readable system history.

---

## [2026.04.27] — Voice Transcription & Security Hardening

### Added
- **Voice Transcription Pipeline**: Fully asynchronous background processing for audio uploads.
- **Whisper Model Caching**: Improved performance with lazy loading and caching of primary (base) and ICR (tiny) Whisper models.
- **Embedded Audio Player**: Native players in Documents and Interviews views for direct media playback.
- **Transcription Previews**: Mono-spaced, high-readability transcription previews with auto-tagging.
- **2FA (TOTP)**: Support for authenticator-based two-factor authentication for team accounts.
- **Passkey Integration**: Support for biometric/device-based login via WebAuthn API.
- **Security Onboarding**: Mandatory recovery code generation and optional passkey setup during first team login.
- **Security Headers**: HSTS, CSP, X-Frame-Options, and Referrer-Policy protection on all API responses.
- **Compass Planner Governance**: `planner.md` is now tracked as part of Compass, covering multi-agent planning, repository intelligence checks, correction/re-review loops, protected Compass files, and final user handoff reports.

### Fixed
- **Transcription Stability**: Resolved race conditions in Whisper model loading and fixed ICR consensus logic.
- **Test Integrity**: Standardized transcription unit tests to use reliable mocking and temporary file paths.
- **Gemma4 Compatibility**: Improved release packaging and Apple Metal (MPS) trainer stability.
- **ESLint Migration**: Modernized frontend linting configuration with `eslint.config.mjs`.

### Changed
- **File Processor**: Enhanced `process_audio` with content-aware chunking for interview turn detection.
- **Login Experience**: Redesigned login screen with support for 2FA flows and recovery code entry.
- **Mainline Integration State**: Dataset generation, passkey security hardening, skill registry cleanup, compute connection lifecycle hardening, integration retry semantics, Compass swarm process updates, and real-time voice recording have been integrated into `main`.
- **Branch Hygiene (2026-04-28)**: Canonical list of deprecated/stale branches added to `planner.md`. Legacy branches (`feat/voice-transcription`, `review/p*`, `fix-ci-validation`, etc.) are 46–124 commits behind `main` and must not be merged wholesale.

---

## [2026.04.20.2] — Phase Zeta & Compute Pool Overhaul

### Added
- **Layer 5 Orchestration Benchmarks**: Real-world integration benchmarking against live LLM servers (LM Studio/Ollama) with 100% Tool Selection Quality (TSQ) and true DAG decomposition.
- **Connection String Lifecycle Management**: Admins can now generate, list, and revoke connection strings for team members and compute donation, complete with a new Settings UI (`ConnectionStringPanel.tsx`).
- **Backup Restoration UI**: Full pipeline for re-importing system backups via the UI, including atomic directory replacement and automated server restart.
- **Consulting-Grade Reporting Engine**: Upgraded MECE reporting to use the Minto Pyramid Principle and SCR (Situation-Complication-Resolution) framework.
- **Instructions to Create Slides**: New Presentation API and UI feature that translates deep research reports into "Ghost Deck" structures for external AIs.

### Changed
- **ComputeRegistry Unification**: Centralized all LLM routing. Replaced brittle heuristics with a **BFCL-pattern dynamic probe** to actively verify `tool_calls` support.
- **RFC 3986 URL Normalization**: Enforced trailing-slash normalization in `ComputeRegistry` to eliminate 404 errors on generic OpenAI-compatible providers.
- **Five-Layer Testing Architecture**: Expanded from three layers to explicitly include Orchestration Benchmarks (Layer 4) and Real-World Integration (Layer 5).
- **Dynamic Documentation Scripts**: `check_integrity.py` and `update_agent_md.py` are now dynamically self-maintaining, automatically discovering new test layers and wrapper docs.

### Fixed
- **RBAC Security Reinforcements**: Restricted project deletion to admins only; allowed non-admins to contribute local compute power.
- **Team Transparency**: Authenticated researchers can now view the team member list.
- **Update Process Reliability**: Hardened the auto-update script to use `git stash` instead of destructive resets.
- **Uninstall Script Completeness**: Ensured complete purge of macOS app bundles, Linux desktop entries, and Tauri local data.

---

## [2026.03.29] — Initial Public Release

### Added

#### Agent System
- Five specialized AI agents with persistent identities: **Cleo** (istara-main), **Sentinel** (istara-devops), **Pixel** (istara-ui-audit), **Sage** (istara-ux-eval), and **Echo** (istara-sim)
- Four-file agent persona system per agent: `CORE.md`, `SKILLS.md`, `PROTOCOLS.md`, `MEMORY.md`
- **Agent Factory** — create custom agents at runtime via UI with no code changes
- **MetaOrchestrator** coordinating all agents through typed A2A message routing
- **Self-evolution engine** — agents record error patterns and workflow preferences; learnings are permanently promoted to persona files after reaching maturity thresholds (3+ occurrences, 2+ contexts, 30 days)
- Agent memory viewer showing accumulated learnings per agent
- Agent health status and activity monitoring in UI
- Design Lead agent (`design-lead`) for interface-focused research tasks
- A2A Protocol discovery endpoint at `/.well-known/agent.json`

#### Research Skills (53 total)
- **Discover phase (14 skills):** User Interviews, Contextual Inquiry, Survey Design, Survey Generator, Competitive Analysis, Diary Studies, Field Studies, Analytics Review, Accessibility Audit, Desk Research, Stakeholder Interviews, Interview Question Generator, Channel Research Deployment, Survey AI Detection
- **Define phase (12 skills):** Thematic Analysis, Kappa Thematic Analysis, Affinity Mapping, Empathy Mapping, Persona Creation, Journey Mapping, HMW Statements, JTBD Analysis, Research Synthesis, Taxonomy Generator, Prioritization Matrix, User Flow Mapping
- **Develop phase (10 skills):** Usability Testing, Heuristic Evaluation, Cognitive Walkthrough, Concept Testing, Card Sorting, Tree Testing, AB Test Analysis, Design Critique, Prototype Feedback, Workshop Facilitation
- **Deliver phase (10 skills):** Design System Audit, SUS/UMUX Scoring, NPS Analysis, Stakeholder Presentation, Handoff Documentation, Regression Impact, Task Analysis Quant, Repository Curation, Research Retro, Longitudinal Tracking
- **Skill Health Monitor** — tracks execution quality per model × skill combination; auto-proposes prompt improvements when quality drops below threshold
- `ModelSkillStats` model persisting success rate, average quality score, and execution count per model × skill
- Skill factory pattern — JSON-based skill definitions register at runtime via API
- Skill stats reset on clean install to avoid stale data from prior environments

#### Atomic Research Evidence Chain
- `Nugget` model — raw evidence with source attribution
- `Fact` model — verified patterns derived from 2+ nuggets
- `Insight` model — interpreted meaning answering "so what?"
- `Recommendation` model — actionable proposals with priority and feasibility scores
- `CodeApplication` model — implementation-ready derivations from recommendations
- Full evidence chain linking: every recommendation traces back to source quotes
- Convergence Pyramid for reports: L1 artifacts through L4 final synthesis
- Double Diamond phase tagging (discover / define / develop / deliver) on all findings

#### Hybrid RAG Pipeline
- LanceDB vector store with columnar embeddings (70% weight)
- BM25 keyword search (30% weight)
- Per-query mode toggle: hybrid, vector-only, keyword-only
- **Prompt RAG** — retrieves only relevant persona sections per query (30–50% token savings)
- **LLMLingua-inspired prompt compression** — removes filler without losing meaning (15–30% token savings)
- **DAG-based context summarizer** — hierarchical summaries of older messages preserving originals
- 6-level context hierarchy with automatic window management
- Hardware-aware Resource Governor monitoring RAM, CPU, and GPU to prevent overload

#### Compute System
- **ComputeRegistry** — unified single-source-of-truth for all LLM nodes (local, network, relay)
- Automatic health checking and failover for registered nodes
- Built-in request routing with capability filtering
- **Compute Relay** — WebSocket-based peer-to-peer compute donation; team members share GPU capacity
- Host resolution, capability detection, deduplication, and tool-filter fallback in relay streaming
- Compute Pool view with node status and contribution metrics
- Ensemble Health view for monitoring multi-model inference health

#### Team and Authentication
- **JWT authentication** with global middleware on all API routes
- Team mode toggle — switch between personal and shared workspace
- **Connection strings** for zero-friction team onboarding: `istara://team@host:port?token=JWT`
- Connection string generator in Settings view
- Heartbeat recovery — automatic reconnection on WebSocket disconnects
- User model with role-based access

#### Survey Integrations
- SurveyMonkey integration — auto-deploy surveys, pull responses
- Google Forms integration — create and distribute forms
- Typeform integration — deploy conversational surveys
- `ResearchDeployment` model tracking deployment lifecycle
- `SurveyLink` model for response collection
- Survey AI detection skill to flag machine-generated responses

#### Channel Integrations
- Telegram channel adapter
- Slack channel adapter
- WhatsApp channel adapter
- Google Chat channel adapter
- `ChannelInstance`, `ChannelConversation`, `ChannelMessage` models
- Findings delivered as messages to configured channels

#### Document Intelligence
- Document upload with auto-classification by type
- Nugget extraction from uploaded documents
- Task creation from document analysis
- Source-linked findings back to exact passages
- Folder watching for continuous ingestion
- **External folder linking** — link folders on disk without copying files into the database
- Organize documents view with bulk operations

#### Figma and Design Tools
- Figma integration — extract design system tokens and design decisions
- `DesignBrief` model — structured brief with evidence links
- `DesignDecision` model — recorded design choices with rationale
- `DesignScreen` model — AI-generated screens via Google Stitch MCP
- Design brief evidence panel showing supporting research

#### MCP Server
- MCP server implementation (disabled by default) at `http://localhost:8001/mcp`
- `MCPAccessPolicy` — granular per-tool permission configuration
- `MCPAuditEntry` — full audit log of all MCP tool invocations
- `MCPServerConfig` — server configuration model
- Available tools: `list_skills()`, `list_projects()`, `get_findings()`, `search_memory()`, `execute_skill()`, `deploy_research()`, `create_project()`, `get_deployment_status()`

#### Desktop App and Installers
- **Tauri v2 desktop app** — system tray with start/stop/restart controls
- macOS DMG installer with drag-to-Applications flow
- Windows NSIS EXE installer with Start Menu integration
- Setup wizard with LLM provider configuration, first-project creation, and team connection
- Auto-update check on startup with CalVer version comparison
- Pre-update backup creation before applying updates
- CI/CD pipeline for cross-platform release builds

#### Frontend and UI
- **22 views:** Chat, Findings, UX Laws, Tasks, Interviews, Documents, Context, Skills, Agents, Memory, Interfaces, Integrations, Loops, Notifications, Settings, Autoresearch, Backup, Meta-Agent, Compute Pool, Ensemble Health, Metrics, History
- **Contextual onboarding** for every view — adapts to what has already been configured
- Dark mode and light mode with `reclaw-{50-900}` color scale
- Sidebar with primary and secondary navigation groups
- Kanban task board with drag-and-drop
- `FocusTrap` in all modal dialogs for keyboard accessibility
- `aria-label` on all icon buttons; `role="tab"/"tablist"` on tab interfaces
- WCAG 2.1 AA compliance on all new UI components
- Sidebar scroll fix for long navigation lists
- View persistence — selected view survives page reload

#### Automation and Loops
- `AgentLoopConfig` — scheduled recurring agent tasks
- `LoopExecution` model tracking loop run history
- Loops skill dropdown for selecting research skills to run on schedule
- Loop status monitoring and cancellation

#### Notifications
- `Notification` model with read/unread state
- `NotificationPreference` — per-user notification configuration
- Real-time notification delivery via WebSocket
- Notification bell with unread count badge

#### Autoresearch
- `AutoresearchExperiment` model — define autonomous research runs
- Autoresearch view for configuring and monitoring experiments
- Automatic skill sequencing based on research phase

#### Backup System
- `BackupRecord` model tracking all backup operations
- Backup view with manual trigger and scheduled backup configuration
- Pre-update automatic backup before version upgrades

#### Metrics and Analytics
- `MethodMetric` model — per-method execution statistics
- Metrics view with aggregated skill performance data
- Historical run data in History view

#### WebSocket Real-Time Events (16 types)
- `agent_status` — agent state changes
- `task_progress` — task execution updates
- `finding_created` — new findings available
- `document_processed` — document analysis complete
- `skill_executed` — skill run result
- `loop_triggered` — scheduled loop fired
- `compute_node_joined` / `compute_node_left` — relay membership changes
- `notification` — user notification delivery
- `queue_update` — LLM request queue depth
- `throttle_status` — resource governor state
- `survey_response` — new survey response received
- `channel_message` — incoming channel message
- `backup_complete` — backup finished
- `evolution_promoted` — agent learning promoted to persona
- `skill_improvement_proposed` — skill health monitor proposal ready

#### API
- 337 REST endpoints across 35 route modules
- Consistent pagination, filtering, and sorting on collection endpoints
- Surveys API fix — correct routing for survey platform integrations
- MCP API — configuration and audit endpoints

#### Infrastructure
- SQLite with aiosqlite for async database access
- 51+ SQLAlchemy 2.0 models with mapped_column and cascade relationships
- Data integrity check endpoint (`POST /api/settings/data-integrity`)
- `python scripts/check_integrity.py` — cross-references models, routes, skills, and frontend types against documentation; exits 1 if out of sync
- `python scripts/update_agent_md.py` — auto-regenerates AGENT.md capabilities catalog
- Docker Compose for single-command local deployment
- Docker Compose GPU variant for CUDA-accelerated inference
- Caddy reverse proxy configuration
- 66-scenario simulation test suite (`tests/simulation/`)

### Changed

- Replaced fragmented LLMRouter + ComputePool with unified **ComputeRegistry** as single source of truth for all LLM node management
- CalVer versioning scheme (`YYYY.MM.DD`) replacing semantic versioning
- Agent personas migrated from flat files to structured four-file layout (CORE / SKILLS / PROTOCOLS / MEMORY) for all system agents

### Fixed

- Skill stats no longer persist stale data across clean installs — stats are reset on fresh database initialization
- CI/CD pipeline stabilized for cross-platform DMG and NSIS builds
- Compute relay streaming: resolved host resolution failures, capability detection gaps, response deduplication, and tool-filter fallback on unsupported models
- Heartbeat recovery: WebSocket connections now auto-reconnect after network interruptions without requiring page reload
- Project pause and delete operations now cascade correctly to child entities
- Sidebar scroll overflow for workspaces with many navigation items
- Loops skill dropdown now populates correctly from the skills registry
- Design brief evidence panel renders linked research correctly
- Stitch API key configuration persists across settings saves
- Survey and MCP API routing corrected for nested resource paths

### Security

- JWT authentication enforced globally via FastAPI middleware — no unauthenticated access to any API route
- MCP server disabled by default; requires explicit opt-in and `MCPAccessPolicy` configuration
- `MCPAuditEntry` records every MCP tool invocation with timestamp, tool name, caller identity, and parameters
- All agent persona files excluded from version control for user-created agents (UUID-named directories)
- `.env` and `data/` directories excluded from git tracking
- Field-level encryption available for sensitive survey credentials and API keys

---

[2026.03.29]: https://github.com/henrique-simoes/Istara/releases/tag/2026.03.29
