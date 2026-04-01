# Istara Features

Complete reference for all features available in Istara 2026.03.29.

---

## Research Methodology

### Atomic Research Evidence Chain
Every insight in Istara traces back through a 5-layer evidence chain:
- **Nuggets** — Raw evidence: quotes, observations, behavioral data points from sources
- **Facts** — Verified patterns derived from 2 or more corroborating nuggets
- **Insights** — Interpreted meanings that answer "so what?" from the facts
- **Recommendations** — Actionable proposals with priority and feasibility ratings
- **Code Applications** — Qualitative coding with full audit trail (who coded what, when, why, and review status)

This chain guarantees full traceability: every recommendation can be drilled down to the specific participant quotes that support it.

> **Research Foundation** — The Atomic Research framework is adapted from Sharon & Gadbaw (2018), "Atomic Research: The molecule approach to UX research data."

### Double Diamond Phase Tagging
All tasks, findings, documents, and skills are tagged with their research phase:
- **Discover** — Understand the problem space
- **Define** — Synthesize discoveries into a clear problem definition
- **Develop** — Generate and evaluate solutions
- **Deliver** — Measure outcomes and communicate findings

### Convergence Pyramid
Research reports synthesize progressively from raw evidence to final deliverable:
- **L1**: Raw artifacts (transcripts, survey data, screen recordings)
- **L2**: Coded artifacts (themed, tagged, categorized)
- **L3**: Synthesis (insights and recommendations)
- **L4**: Final deliverable (stakeholder-ready report)

---

## 53 Research Skills

Skills are executed by the AI agents and can also be triggered manually from the Chat view. Each skill follows the OpenClaw AgentSkills standard.

### Discover Phase (14 skills)
| Skill | Purpose |
|-------|---------|
| User Interviews | Structure and analyze 1-on-1 research conversations |
| Contextual Inquiry | Guide observation in users' natural environment |
| Diary Studies | Coordinate longitudinal self-reporting |
| Competitive Analysis | Systematic multi-competitor evaluation |
| Stakeholder Interviews | Internal knowledge gathering and alignment |
| Survey Design | Questionnaire construction with bias avoidance |
| Survey Generator | AI-assisted survey question generation |
| Survey AI Detection | Detect and flag AI-generated survey responses |
| Analytics Review | Behavioral data interpretation and pattern finding |
| Desk Research | Secondary research synthesis from existing sources |
| Field Studies | Ethnographic observation in real-world context |
| Accessibility Audit | WCAG compliance and assistive technology evaluation |
| Interview Question Generator | Generate targeted interview guides from research objectives |
| Channel Research Deployment | Deploy research instruments via Telegram or Slack |

### Define Phase (12 skills)
| Skill | Purpose |
|-------|---------|
| Affinity Mapping | Cluster observations into emergent themes |
| Persona Creation | Build evidence-based user archetypes |
| Journey Mapping | Visualize end-to-end user experience |
| Empathy Mapping | Profile users' emotional and behavioral states |
| JTBD Analysis | Apply Jobs-to-Be-Done framework to understand motivations |
| HMW Statements | Generate "How Might We" creative reframing questions |
| User Flow Mapping | Diagram task flows and decision trees |
| Thematic Analysis | Qualitative coding and theme extraction |
| Kappa Thematic Analysis | Multi-coder analysis with Fleiss' Kappa inter-rater reliability |
| Research Synthesis | Consolidate findings across methods and data sources |
| Prioritization Matrix | Rank opportunities by impact vs. effort |
| Taxonomy Generator | Classify and structure information architecture |

### Develop Phase (10 skills)
| Skill | Purpose |
|-------|---------|
| Usability Testing | Task-based evaluation with participants |
| Heuristic Evaluation | Nielsen's 10 heuristics expert review |
| A/B Test Analysis | Statistical comparison of design variants |
| Card Sorting | Validate information architecture with users |
| Tree Testing | Evaluate navigation structure without visual design |
| Concept Testing | Validate ideas early before full development |
| Cognitive Walkthrough | Step-by-step usability inspection technique |
| Design Critique | Structured review of designs against principles |
| Prototype Feedback | Iterative prototype evaluation and synthesis |
| Workshop Facilitation | Guide collaborative design and ideation sessions |

### Deliver Phase (10 skills — includes Survey AI Detection moved to Discover)
| Skill | Purpose |
|-------|---------|
| SUS/UMUX Scoring | System Usability Scale calculation and industry benchmarking |
| NPS Analysis | Net Promoter Score interpretation and segmentation |
| Task Analysis (Quant) | Completion rates, time-on-task, error rate analysis |
| Regression/Impact Analysis | Before/after design change measurement |
| Design System Audit | Component library consistency and coverage review |
| Handoff Documentation | Developer-ready specification generation |
| Repository Curation | Organize and tag the research repository for reuse |
| Stakeholder Presentation | Executive-ready findings packaging and narrative |
| Research Retro | Research process retrospective and improvement |
| Longitudinal Tracking | Trend analysis and metric tracking across time |

### Self-Evolving Skills
The **Skill Health Monitor** tracks execution quality over time. When a skill's performance drops below a threshold (measured by consensus scores, user ratings, or output quality metrics), Istara automatically proposes prompt improvements via the **Meta-Agent** view. Researchers can review and approve or reject each proposal.

> **Research Foundation** — Self-evolving agent skill design is grounded in Zhou et al. (2026) "Memento-Skills: Let Agents Design Agents" and Zhang et al. (2026) "Hyperagents: DGM-H Metacognitive Self-Modification." The Kappa Thematic Analysis skill uses Fleiss' Kappa inter-rater reliability (Fleiss, 1971).

---

## Views

### Chat
Conversational interface with Cleo (the research coordinator). Features:
- Natural language skill invocation ("analyze my interviews", "run a heuristic evaluation")
- File drag-and-drop and paste
- Real-time streaming responses
- Source citations linked to specific documents and findings
- Session history with full context preservation
- **LLM-native tool selection**: 13 system action tools the LLM calls based on intent (create_task, search_findings, attach_document, etc.)

### Findings
Evidence chain explorer organized by Double Diamond phase. Drill down: Recommendations → Insights → Facts → Nuggets → Source documents. Filter by phase, tag, date, and confidence level.

### Documents
Upload and manage research artifacts: interview transcripts, survey exports, screen recordings, PDF reports. Auto-ingested into vector store for RAG retrieval. Linked to tasks and findings.

> **Research Foundation** — RAG retrieval is based on Lewis et al. (2020) "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks" (NeurIPS 2020). Multi-document ranking uses Reciprocal Rank Fusion from Cormack et al. (2009) "Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods" (SIGIR 2009).

### Tasks (Kanban)
Direct the agent via a Kanban board with columns: Backlog, In Progress, Review, Done. Features:
- Priority levels: Critical, High, Medium, Low
- Input/output document linking with count badges
- URL attachment for web pages the agent should analyze
- Per-task instructions field
- Agent assignment
- Task checkpoints for crash recovery

### Interviews
Dedicated transcript viewer with:
- Participant ID management (anonymization-first)
- Inline nugget extraction — highlight text to create a nugget directly
- Tag filtering by participant, theme, or sentiment
- Export to structured formats

> **Research Foundation** — AI-assisted interview analysis methodology is grounded in "AURA: AI-Powered User Research Assistant" (arXiv:2510.27126).

### UX Laws
40+ cognitive psychology and UX heuristics laws (Fitts's Law, Hick's Law, Miller's Law, Jakob's Law, etc.) linked to your findings. Generate a compliance radar chart showing which laws your product violates.

> **Research Foundation** — The UX Laws library is grounded in Yablonski (2020), *Laws of UX: Using Psychology to Design Better Products & Services* (O'Reilly Media).

### Skills
Browse all 53 skills with phase filtering and search. Features:
- Edit skill prompts and instructions
- View skill execution history and performance metrics
- Track self-evolution proposals (approve / reject)
- Create custom skills with the skill editor
- Import skills from external sources (OpenClaw skill packages)

### Agents
Manage the 5 system agents plus any custom agents. Features:
- View agent status, current task, and heartbeat
- Start and stop individual agents
- View A2A messages between agents
- Configure agent settings (scope, specialties, system prompt)
- Create custom agents with auto-generated persona files

> **Research Foundation** — The Agent Factory and custom agent creation patterns are grounded in Zhou et al. (2026) "Memento-Skills: Let Agents Design Agents" and Zhang et al. (2026) "Hyperagents: DGM-H Metacognitive Self-Modification."

### Memory
View and manage agent learnings across all agents. Features:
- Browse learnings by category (error_pattern, workflow_pattern, user_preference, performance_note)
- Search learnings by keyword
- Manually promote learnings to persona files
- Delete outdated learnings
- View evolution history

> **Research Foundation** — The memory compression and context management strategies draw on Jiang et al. (2023) "LLMLingua: Compressing Prompts for Accelerated Inference of Large Language Models" and Chen et al. (2023) "MemWalker: Interactive Memory Management and Traversal for Long Contexts."

### Interfaces
Design tool integrations:
- **Figma**: Import screens and auto-generate design briefs
- **Stitch**: API key configuration for design screen import
- Link design decisions to research findings

### Integrations
External platform connections:
- **Telegram**: Bot token setup for community research deployment and channel research
- **Slack**: Workspace integration for messaging and research deployment
- **Survey platforms**: Typeform, SurveyMonkey — sync responses directly into Istara
- **MCP servers**: Register external Model Context Protocol servers for tool access

### Loops
Automated recurring research tasks using cron scheduling:
- Define a skill + schedule expression
- Agent runs the skill automatically on schedule
- View execution history with full output logs
- Enable/disable without deleting the configuration

### Notifications
Real-time activity feed of all system events:
- Agent status changes
- Task completions
- New findings created
- File processing results
- Resource throttle warnings
- Custom notification preferences (filter by event type)

### Settings
System configuration:
- Hardware info (RAM, CPU, GPU)
- LLM provider management (LM Studio / Ollama endpoints)
- Model selection with hardware-aware recommendations
- Data management (import/export, data integrity check)
- Team mode configuration
- Connection string management
- Auto-update settings

### Compute Pool
LLM compute node management:
- View all compute nodes (local, network, relay)
- Add network nodes manually or via auto-discovery
- View node health, available models, and routing statistics
- Configure relay nodes (donate or use donated compute)

> **Research Foundation** — The distributed compute relay architecture is inspired by Borzunov et al. (2022) "Petals: Collaborative Inference and Fine-tuning of Large Models" (arXiv:2209.01188).

### Context
Edit the 6-level context hierarchy:
- Platform (built-in Istara expertise)
- Company (organization-level context)
- Product (product-specific context)
- Project (research-specific context)
- Task (per-task instructions)
- Agent (per-agent constraints)

### History
Version tracking for findings and documents with rollback capability.

### Metrics
Quantitative research dashboards:
- SUS scores with industry benchmarks
- NPS trends over time
- Task completion rates, time-on-task, error rates
- Custom metric visualizations

### Autoresearch
Automated research experiment loops that run multiple configurations and compare outputs. Includes a model leaderboard showing which local model performs best for each research skill.

> **Research Foundation** — Automated research loop design draws on Karpathy (2026) "Software 2.0 and the Autonomous Research Loop." Output grounding and quality evaluation follow Zheng et al. (2023) "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena."

### Backup
Manual and scheduled backup management:
- Create named backups on demand
- Schedule automatic backups (daily, weekly)
- Restore from any backup point
- Pre-update backups created automatically before version upgrades

### Meta-Agent
Review and approve or reject agent self-evolution proposals:
- Browse pending promotion candidates
- See what change would be made to which persona file
- Approve to write the change, reject to discard
- View confirmed overrides and evolution history

### Ensemble Health
Multi-model consensus validation status:
- Current Fleiss' Kappa scores per finding type
- Validation strategy performance history
- Adaptive learning status (which strategy is best for your context)

> **Research Foundation** — Multi-model validation draws on Wang et al. (2024) "Mixture-of-Agents Enhances Large Language Model Capabilities" (MoA), Du et al. (2024) "Improving Factuality and Reasoning in Language Models through Multiagent Debate," Li et al. (2025) "Self-MoA: Self-Mixture of Agents," and Fleiss (1971) "Measuring Nominal Scale Agreement Among Many Raters" for Kappa scoring.

---

## Local-First Privacy

- All data stored locally in SQLite (structured) and LanceDB (vector embeddings)
- No telemetry, no analytics, no cloud sync by default
- LLM inference is fully local via LM Studio or Ollama
- **MCP Server** is OFF by default — when enabled, access policies control per-tool permissions with full audit logging

---

## Team Mode

- **Local mode** (default): Single-user, no authentication
- **Team mode**: Multi-user with JWT authentication and role-based access (admin/user)
- **Connection strings**: Encode server URL + auth token for easy team onboarding
- **Shared knowledge**: All team members work from the same research repository

---

## External Folder Linking

Projects can be linked to external folders on the filesystem:
- Watch folders (e.g., Google Drive sync, Dropbox, local research folder)
- Istara's **File Watcher** monitors the folder and automatically ingests new or changed files
- Supports: `.txt`, `.md`, `.pdf`, `.docx`, `.csv`, `.json`, and audio transcripts

---

## Desktop App

The Tauri v2 desktop app provides a thin GUI tray layer that delegates to `istara.sh`:
- System tray icon with live port-based state indicators (Start/Stop reflects actual server state)
- Process management via shell delegation to `istara.sh` (single source of truth for PID files)
- LLM status click with donation toggle or LM Studio launch prompt
- Compute Donation toggle with confirmation dialogs and relay management
- Three-tier update checking (Tauri updater, git tags, GitHub releases) with result dialogs
- First-run setup wizard for configuration
- macOS `.dmg` and Windows NSIS installer

---

## AI Suggestion Boxes

InteractiveSuggestionBox — a reusable component for inline AI conversations:
- Creates a real chat session when suggestions are requested
- Streams the AI response with auto-scroll
- Quick-reply input for follow-up questions without leaving the current view
- "Continue in Chat" link navigates to the full session in the Chat view
- Used in Documents ("Organize") and available for Interviews and other views

## Notifications

- Notification bell with unread count badge in the sidebar header (next to dark mode toggle)
- Red badge shows count (up to "99+")
- Click navigates to the Notifications view
- Polls for new notifications every 30 seconds

## Documents Sync

- Sync button scans the project folder for new files
- Shows a toast notification with the count of files found
- Auto-sync runs on project load to detect new files automatically

---

## CalVer Versioning and Auto-Updates

- Version format: `YYYY.MM.DD` (e.g., `2026.03.29`)
- Auto-update check runs at startup (backend) and every 6 hours (tray app via `git fetch --tags`)
- **Pre-update backup** created automatically before applying any update
- Update channel configurable in Settings (stable / dev)
