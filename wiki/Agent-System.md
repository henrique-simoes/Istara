# Agent System

Istara is built on a multi-agent architecture where five specialized AI agents coordinate to handle different aspects of UX research work. This page explains how the agents work, how they evolve over time, and how to work with them effectively.

---

## The Five System Agents

### Cleo — Research Coordinator (`istara-main`)
**Role**: Task Executor and primary user interface agent.

Cleo is the main agent you interact with. She executes all 53 UXR skills, synthesizes findings into the Atomic Research chain, and manages the Kanban task board. She communicates like a senior UX researcher (10+ years experience) — evidence-driven, structured, and methodologically rigorous.

Cleo's key behaviors:
- Never presents inferences as facts (uses calibrated language: "I'm confident that..." vs. "The data suggests...")
- Actively triangulates findings across methods and sources
- Adapts communication style based on researcher experience level
- Delegates to specialist agents rather than duplicating their work
- Always cites specific participant IDs, document references, and timestamps

### Sentinel — DevOps Auditor (`istara-devops`)
**Role**: System health, data integrity, and performance monitoring.

Sentinel runs continuously in the background. She monitors:
- Database integrity (orphaned references, cascade delete gaps)
- Agent heartbeat status
- Task checkpoint recovery for crashed agents
- System resource utilization
- Skill performance metrics

Sentinel also drives the **skill self-evolution pipeline** — she's the agent that evaluates learnings for promotion thresholds.

### Pixel — UI Auditor (`istara-ui-audit`)
**Role**: UI evaluation, accessibility, and design system audit.

Pixel specializes in evaluating interfaces against:
- Nielsen's 10 Usability Heuristics (with severity ratings)
- WCAG 2.1 AA accessibility standards
- Design system consistency (spacing, color, typography, component usage)
- Cognitive load principles

When a task involves UI evaluation, Cleo automatically delegates to Pixel.

### Sage — UX Evaluator (`istara-ux-eval`)
**Role**: Holistic UX assessment and strategic evaluation.

Sage takes a broader view than Pixel — evaluating:
- End-to-end user journey completeness
- Cognitive load distribution across workflows
- Mental model alignment between product and users
- Platform experience quality scoring
- Strategic UX opportunity identification

### Echo — User Simulator (`istara-sim`)
**Role**: End-to-end testing and scenario simulation.

Echo runs 66 numbered test scenarios that verify Istara's own research workflows function correctly. Echo's output is used for regression testing and finding friction in the research experience. Echo communicates in a structured, technical format focused on reproducibility.

---

## Agent Personas

Each agent's personality is defined by four Markdown files stored at `backend/app/agents/personas/{agent_id}/`:

| File | Purpose | Context Budget |
|------|---------|---------------|
| `CORE.md` | Identity, personality, values, communication style | 40% (highest priority) |
| `SKILLS.md` | Technical capabilities, methodologies, tools | 25% |
| `PROTOCOLS.md` | Behavioral rules, decision-making, error handling | 25% |
| `MEMORY.md` | Persistent learnings auto-updated by the agent | 10% |

These files compose the agent's system prompt on every interaction. When the composed identity exceeds the context budget, **Prompt RAG** retrieves only the most relevant sections for the current query (saving 30–74% of tokens).

---

## Self-Evolution System

Istara implements an OpenClaw-inspired self-improvement system where agents literally rewrite their own personas based on accumulated experience.

### How Learning Works

```
Agent encounters error or pattern during skill execution
    ↓
Learning recorded with:
  - category: error_pattern | workflow_pattern | user_preference | performance_note
  - trigger (what caused it)
  - resolution (how it was handled)
  - confidence score (0–100)
  - times_applied, times_successful
    ↓
On future similar situations, agent checks for matching learnings
(keyword matching against past triggers)
    ↓
Self-evolution engine evaluates promotion eligibility
    ↓
Promotion thresholds met:
  ✓ ≥3 occurrences (times_applied)
  ✓ ≥2 distinct project contexts
  ✓ 30-day maturity window
  ✓ ≥70% confidence score
  ✓ ≥60% success rate
    ↓
Learning promoted to persona file:
  error_pattern     → PROTOCOLS.md
  workflow_pattern  → SKILLS.md
  user_preference   → CORE.md
  performance_note  → MEMORY.md
    ↓
Original learning marked [PROMOTED]
Agent's next load includes the new persona content
```

### Two Evolution Modes

- **User approval** (default): Mature learnings appear as proposals in the **Meta-Agent** view. You review each one — see exactly what text would be added to which persona file — then approve or reject.
- **Auto-promote** mode: Mature patterns are written to persona files automatically during Sentinel's audit cycle. Enable via `self_evolution_auto_promote: true` in Settings.

### Reviewing Evolution Proposals

Navigate to **Meta-Agent** view to:
1. See all pending proposals with the proposed change text
2. Approve a proposal — writes the change to the persona file immediately
3. Reject a proposal — discards it without affecting the learning record
4. View all confirmed overrides and the evolution history

---

## Agent-to-Agent Communication (A2A)

Agents communicate through a database-backed messaging system with real-time WebSocket broadcasts.

### Message Types
| Type | When Used |
|------|-----------|
| `consult` | Cleo asks Pixel for a UI assessment mid-task |
| `report` | Sentinel reports data integrity issues to Cleo |
| `alert` | Any agent sends a critical system warning |
| `delegate` | Cleo delegates a specialized sub-task to Sage or Pixel |

### External A2A Protocol
Istara exposes `/.well-known/agent.json` for standard A2A Protocol discovery. External agents (e.g., Claude Desktop with A2A support) can connect and exchange messages with Istara's agents.

---

## Custom Agents

Users can create custom agents to specialize in domain-specific research or organizational contexts.

### Creating a Custom Agent

1. Go to **Agents** view
2. Click **Create Agent**
3. Provide:
   - **Name** — displayed in the UI and used in A2A messages
   - **System prompt** — the agent's core instructions and personality
   - **Capabilities** — what skills and task types this agent handles
   - **Scope** — `universal` (all projects) or `project` (specific project only)
4. Istara auto-generates all four persona files from your inputs

### Custom Agent Lifecycle
Once created, custom agents:
- Participate in the task queue alongside system agents
- Receive A2A messages from system agents
- Accumulate learnings and evolve via the same self-evolution pipeline
- Appear in the Agents view with full heartbeat and status monitoring

---

## Agent Work Loop

The core agent loop runs continuously for each active agent:

```
1. Check resources (Resource Governor — abort if RAM >90%)
2. Pick highest-priority assigned task (critical > high > medium > low)
   If no assigned tasks, pick highest-priority unassigned task
3. Load 6-level project context (platform → company → product → project → task → agent)
4. Retrieve relevant persona sections (Prompt RAG)
5. Select appropriate skill (explicit in task, or keyword-inferred from task title)
6. Execute skill → SkillOutput (structured JSON)
7. Store findings in Atomic Research chain (Nugget → Fact → Insight → Recommendation)
8. Self-verify output (check_findings — validates evidence chain completeness)
9. Ingest output artifacts into LanceDB vector store
10. Record learnings if errors occurred during execution
11. Update task status → broadcast progress via WebSocket
12. Check queue depth: sleep 5s if tasks remain, 30s if idle
13. Repeat
```

**Task checkpoints**: After each major step, the agent writes a checkpoint to the database. If the agent crashes, it can resume from the last checkpoint rather than restarting the entire task.

---

## Resource Governor

The Resource Governor ensures agents don't overwhelm the user's machine.

### Behavior
- Monitors CPU and RAM usage in real-time
- **Warning threshold** (>80% RAM): Reduces concurrent agent workers
- **Critical threshold** (>90% RAM): Pauses ALL agents, broadcasts `resource_throttle` event, shows warning toast
- Agents resume automatically when resources drop below the critical threshold

### Priority Preservation
Even when throttling, **user interactions** (chat messages) always take priority over background agent tasks. You can always use the Chat view regardless of agent queue status.

---

## MetaOrchestrator

The MetaOrchestrator coordinates all agents and prevents conflicts:
- Prevents two agents from working on the same task simultaneously
- Routes incoming A2A messages to the appropriate agent
- Manages agent registration and deregistration
- Coordinates the self-evolution audit cycle (run by Sentinel)
- Handles agent crash recovery via task checkpoints

---

## Viewing Agent Activity

### Agents View
- Real-time status for each agent (IDLE / WORKING / PAUSED / ERROR / STOPPED)
- Current task and progress
- Last heartbeat timestamp
- Start/Stop controls
- A2A message feed

### Notifications View
All agent events appear in the notification feed:
- Task completions
- Finding creations
- System warnings
- Resource throttle events

### Backend Logs
For detailed debugging, check the backend terminal output. Each agent logs its actions with agent ID, task ID, and timing information.
