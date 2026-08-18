🇧🇷 [Leia em Português](README.pt-BR.md)

<div align="center">
<img width="300" height="300" alt="Istara" src="https://github.com/user-attachments/assets/b250903a-8272-43b7-b91d-dfcf3b249910" />
</div>

# 🐾 Istara

### Local-first AI agents for UX Research — your data never leaves your machine

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/github/v/release/henrique-simoes/Istara?label=version&sort=semver)](https://github.com/henrique-simoes/Istara/releases/latest)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](backend/)
[![Node](https://img.shields.io/badge/node-20-green.svg)](frontend/)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey.svg)](installer/)
[![GitHub](https://img.shields.io/badge/GitHub-henrique--simoes%2FIstara-181717?logo=github)](https://github.com/henrique-simoes/Istara)

[**Install in 1 Minute**](#install) · [**Documentation Website**](https://henrique-simoes.github.io/Istara/) · [**Architecture**](#architecture) · [**Testing**](TESTING.md) · [**Security**](SECURITY.md) · [**Docs Map**](DOCUMENTATION.md) · [**References**](#academic-references-and-standards) · [**Contributing**](CONTRIBUTING.md)

---

*Five autonomous AI agents. Fifty-three governed research skills. Zero cloud dependency.*
*Every trusted insight is source-validated. Agent learning is governed, project-scoped, and auditable.*
*Scale your intelligence: share compute between team members to run more agents simultaneously—a smarter, faster team working as one agentic swarm.*

![](https://istara.goatcounter.com/count?p=/count-top)
<div align="center">
<img src="Screenshots/istara_presentation.gif" width="900" alt="Istara demo — AI agents conducting UX research autonomously" />
<img src="Screenshots/istara_chat.gif" width="900" alt="Istara intelligent chat — grounded conversations with your research data" />
</div>

### At a Glance

| Feature | What It Does |
|---|---|
| 🧠 Intelligent Chat | Grounded conversations with your research data, source-aware answers, and reviewable evidence |
| ⚛️ Atomic Findings | Accepted atoms/nuggets → facts → insights → recommendations, every trusted claim linked to validated source evidence |
| 📐 Laws of UX | 30+ psychological principles audited automatically against your designs with scoring |
| 📋 Kanban Board | Agents pick up tasks and execute skills, while review, Done, and report gates stay explicit |
| 🎯 Smart Routing | Match tasks to specialists — Pixel for UI audits, Sage for UX eval, Echo for simulations |
| 🎙️ Interview Analysis | Transcribe, tag, analyze, relate and generate reports across your entire participant pool |
| 🧭 Context Engine | Ground agents in company culture, project goals and custom guardrails for better performance |
| 🛠️ 53+ Research Skills | Competitive analysis, card sorting, journey mapping — agents equipped for any challenge |
| 🐝 Agent Swarm | Five specialized agents that learn from verified outcomes and project-scoped process memory |
| 🎨 Google Stitch & Figma | Generative AI screen design, handoff specs, component audits — design-to-dev bridge built in |
| 💬 Messaging Channels | Deploy research to Slack, Telegram, WhatsApp — managed entirely by your agents |
| 📊 Survey Sync | Pull from SurveyMonkey, Typeform, Google Forms — ingest responses into the Research Spine with source, review, and reliability state |
| 🔄 Autoresearch | Sandboxed self-improvement experiments — candidate prompt/RAG/model changes become governed proposals before production use |
| 🧾 Improvement Governance | Self-evolution changes are project-scoped, evidence-backed, approval-gated, rollbackable, and barred from bypassing the Research Spine |
| ✅ Ensemble Health | Multi-model coding, reliability metrics, route evidence, adversarial review, and human reconciliation |

<details>
<summary><strong>View product screenshots</strong></summary>

<div align="center">
  <p><strong>Intelligent Chat:</strong> Talk to your research context. Ask about findings, brainstorm with agents, and get instant answers grounded in your data.</p>
  <img src="Screenshots/Screenshot%202026-04-02%20at%2016.37.30.png" width="1600" />

  <p><strong>Atomic Research Findings:</strong> Extract candidate atoms, validate them against source evidence, then promote accepted nuggets, facts, insights, and recommendations. Every trusted claim stays linked to its original source.</p>
  <img src="Screenshots/Screenshot%202026-04-02%20at%2016.37.34.png" width="1600" />

  <p><strong>Laws of UX Compliance:</strong> Audit your designs against 30+ psychological principles and Nielsen heuristics. See exactly where your UI excels or needs improvement.</p>
  <img src="Screenshots/Screenshot%202026-04-02%20at%2016.38.34.png" width="1600" />

  <p><strong>Autonomous Task Management:</strong> A powerful Kanban board where agents pick up tasks, execute skills, and report progress in real-time while research outputs remain reviewable until approved.</p>
  <img src="Screenshots/Screenshot%202026-04-02%20at%2016.38.47.png" width="1600" />

  <p><strong>Multi-Agent Assignment:</strong> Choose the best agent for the job. Route tasks to specialists like Pixel for UI audits or Sage for UX evaluation.</p>
  <img src="Screenshots/Screenshot%202026-04-02%20at%2016.38.54.png" width="1600" />

  <p><strong>Interviews & Transcripts:</strong> Istara can transcribe, tag, analyze, relate, and generate reports from many interviews at once — including voice messages from WhatsApp and Telegram with automatic Whisper transcription and inter-coder reliability scoring. Find insights shared across your entire participant pool!</p>
  <img src="Screenshots/Screenshot%202026-04-02%20at%2016.39.01.png" width="1600" />

  <p><strong>Context Engine:</strong> Ground your agents in your company culture, project goals, and specific guardrails. The more they know, the better they perform.</p>
  <img src="Screenshots/Screenshot%202026-04-02%20at%2016.39.08.png" width="1600" />

  <p><strong>Skill Catalog:</strong> Over 50 research skills ready to go. From Competitive Analysis to Card Sorting, your agents are equipped for any research challenge.</p>
  <img src="Screenshots/Screenshot%202026-04-02%20at%2016.39.11.png" width="1600" />

  <p><strong>Agentic Swarm:</strong> Meet your team—Cleo, Sentinel, Pixel, Sage, and Echo. Five specialized agents that learn from verified outcomes, project-scoped telemetry, and governed process memory.</p>
  <img src="Screenshots/Screenshot%202026-04-02%20at%2016.39.16.png" width="1600" />

  <p><strong>Google Stitch & Figma Integration:</strong> Generate screens with AI, connect Figma for handoff specs, audit components, and close the gap between design intent and dev implementation.</p>
  <img src="Screenshots/Screenshot%202026-04-02%20at%2016.39.28.png" width="1600" />

  <p><strong>Messaging Channels:</strong> Deploy your research directly to Slack, Telegram, or WhatsApp. Collect data where your users are, managed entirely by your agents.</p>
  <img src="Screenshots/Screenshot%202026-04-02%20at%2016.39.36.png" width="1600" />

  <p><strong>Survey Integrations:</strong> Pull data from SurveyMonkey, Typeform, or Google Forms. Responses enter the same evidence-unit, coding, reliability, review, and report-gate pipeline as interviews and documents.</p>
  <img src="Screenshots/Screenshot%202026-04-02%20at%2016.39.40.png" width="1600" />

  <p><strong>Autoresearch Engine:</strong> Enable sandboxed self-improvement loops. Agents measure candidate prompt, RAG, or model changes, revert them after evaluation, and send successful candidates through governed approval before production use.</p>
  <img src="Screenshots/Screenshot%202026-04-02%20at%2016.39.59.png" width="1600" />

  <p><strong>Ensemble Health:</strong> Trust through verification. Istara uses multi-model coding, reliability metrics, route evidence, adversarial review, debate rounds, and human reconciliation before evidence becomes reportable.</p>
  <img src="Screenshots/Screenshot%202026-04-02%20at%2016.40.15.png" width="1600" />
</div>

</details>

---
![](https://istara.goatcounter.com/count?p=/count-install)
## Install

### Homebrew (macOS — Recommended)

```bash
brew install --cask henrique-simoes/istara/istara
```

### Shell One-Liner (macOS / Linux)

Installs all dependencies (Python, Node, LLM provider), sets up the server, and offers to start it:

```bash
curl -fsSL https://raw.githubusercontent.com/henrique-simoes/Istara/main/scripts/install-istara.sh | bash
```

### From Source

```bash
git clone https://github.com/henrique-simoes/Istara.git
cd Istara

# Backend
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend (new terminal)
cd frontend
npm install && npm run dev
```

### Docker

```bash
git clone https://github.com/henrique-simoes/Istara.git && cd Istara
cp .env.example .env
docker compose up -d
```

### Uninstall

```bash
curl -fsSL https://raw.githubusercontent.com/henrique-simoes/Istara/main/scripts/uninstall-istara.sh | bash
```

> **DMG / EXE Installers:** The native desktop installers (`.dmg` for macOS, `.exe` for Windows) available on the [Releases](https://github.com/henrique-simoes/Istara/releases) page are currently experiencing issues and **should not be used**. Use one of the methods above instead. We are actively working on a fix.

Open [http://localhost:3000](http://localhost:3000) after starting. The onboarding wizard guides you through your first project.

---

## Release, Testing, and Security Posture

Istara's public-release process is now evidence-first. Development runs through
Compass Forge work orders, impact analysis, and gates; test history is kept as
curated release baselines instead of scattered temporary logs.

- **Testing and evals:** see [TESTING.md](TESTING.md),
  [testing/TESTING_STRATEGY.md](testing/TESTING_STRATEGY.md),
  [testing/AI_EVALS_STRATEGY.md](testing/AI_EVALS_STRATEGY.md), and
  [testing/TEST_HISTORY.md](testing/TEST_HISTORY.md). The suite covers backend
  contracts, frontend build/type/lint/unit checks, relay tests, simulation,
  orchestration benchmarks, live single-profile LLM checks, RAG, Prompt RAG,
  LLMLingua, DAG/ReAct, ReasoningBank, Memento Skills, Meta Hyperagents,
  thinking-output controls, and voice contracts.
- **Public testing branch and CI:** every feature change is mapped to
  deterministic obligations by `testing/feature_coverage.yml` +
  `scripts/check_feature_obligations.py` (fail-closed on unowned paths). The
  long-lived `testing` branch builds a disposable, provider-agnostic Docker QA
  artifact (`docker-compose.qa.yml`, `scripts/istara-qa.sh`), and
  `promote-testing.yml` is the only workflow that may create a promotion PR to
  `main` — and only after a protected-environment human approval bound to the
  exact source SHA. No workflow auto-merges, and CI-generated commits (README
  badge sync) stay on `main` only, so `testing` HEAD is never mutated by CI.
  The promotion workflow's green-checks verification lists Actions runs with an
  `actions: read`-scoped workflow token, enforced by
  `scripts/check_workflow_contracts.py`.
- **Security:** see [SECURITY.md](SECURITY.md),
  [security/SECURITY_BENCHMARK.md](security/SECURITY_BENCHMARK.md),
  [security/RELEASE_SECURITY_READINESS.md](security/RELEASE_SECURITY_READINESS.md),
  and [the current assessment](security/ISTARA_SECURITY_ASSESSMENT_2026-05-08.md).
  The release gate maps controls to OWASP ASVS, NIST SP 800-63-4, Better Auth
  guidance, WebAuthn, OAuth security guidance, OWASP LLM/agentic risks, NIST AI
  RMF, SSDF, SLSA, OpenSSF Scorecard, and GitHub Artifact Attestations.
- **Live LLM testing:** live tests use one gitignored OpenAI-compatible profile
  and the fixed test model id `google/gemma-4-e4b`. Private endpoints and tokens
  are never committed, and tests must not probe or autoload multiple heavy
  models.
- **Documentation organization:** see [DOCUMENTATION.md](DOCUMENTATION.md) for
  the canonical map of current docs, generated docs, compatibility notes,
  testing history, security evidence, and ignored runtime markdown.

---

## Why Istara Exists

UX researchers deserve tools that respect their data, enforce methodological rigor, and improve through use — not SaaS platforms that upload transcripts to foreign servers, charge per seat, and forget everything the moment you close the tab.

Istara runs entirely on your hardware. It ships with five specialized AI agents, 53 UX research skills, and an evidence-chain methodology grounded in peer-reviewed research. Agents and skills can improve, but only through project-scoped telemetry, verified outcomes, governed proposals, and Research Spine gates.

**No cloud. No subscription. Evidence first.**

---

## Istara vs. The Alternatives

| Capability | Istara | Alternatives |
|---|---|---|
| Data privacy | 100% local — data never leaves your machine | Uploaded to vendor cloud |
| Agent memory | Persistent, evolving personas across sessions | Stateless API calls |
| Research methodology | Research Spine with source-validated Atomic Research artifacts | Ad-hoc summarization |
| Skill improvement | Project-scoped, verified skill health and governed prompt changes | Static prompts |
| Agent creation | Runtime agent factory — new agents without code | Fixed feature set |
| Multi-model validation | Source-evidence coding, reliability metrics, route evidence, reconciliation | Single model, no validation |
| Memory compression | LLMLingua-inspired, 30–74% token savings | No long-context management |
| UX compliance | 30 Laws of UX automated auditing | Not available |
| Compute sharing | Donate GPU via WebSocket relay — team cluster | Pay-per-API-call |
| Autonomous research | Sandboxed autoresearch proposals; no live mutation before governance | Manual execution only |
| Survey channels | WhatsApp, Telegram, Typeform, SurveyMonkey | Limited integrations |

---
![](https://istara.goatcounter.com/count?p=/count-features)
## 1. 🧠 Agents That Create Agents

> *"Let Agents Design Agents"* — Zhou et al. (2026)

Istara implements a **Memento-inspired agent factory** grounded in the insight that the most effective way to extend an AI system is to have it design its own extensions. When an existing agent detects a capability gap — a research task it cannot handle well — it proposes a new specialized agent: defines the persona, selects skills, writes the protocols, and registers it in the orchestration pipeline.

**No direct production mutation. The system can propose its own extensions, but governed approval decides what becomes active.**

The five built-in agents each carry four evolving persona files:

| Agent | Name | Specialization |
|---|---|---|
| `istara-main` | **Cleo** | Primary researcher — executes all 53 skills, leads projects, interfaces with you |
| `istara-devops` | **Sentinel** | Data integrity guardian — monitors health, audits orphaned records, runs checks |
| `istara-ui-audit` | **Pixel** | WCAG compliance expert — Nielsen heuristics, accessibility scoring |
| `istara-ux-eval` | **Sage** | Cognitive load analyst — user journeys, workflow friction detection |
| `istara-sim` | **Echo** | End-to-end tester — simulates users, runs 75 regression scenarios |

Each agent's persona is stored in four files — `CORE.md` (identity), `SKILLS.md` (capabilities), `PROTOCOLS.md` (behavioral rules), `MEMORY.md` (accumulated learnings) — but updates are bounded by project scope, verification, and governance rules. Protected research methodology, reliability thresholds, auth constraints, and report gates are not silently rewritten.

### Self-Evolution Pipeline

```
User interaction
      ↓
Agent records project-scoped process signal
      ↓
Telemetry separates tool success · execution success · verification · research quality · reportability
      ↓
Candidate learning tracked: 3+ occurrences · active project context · 30-day window · confidence · success rate
      ↓
Governance check blocks protected methodology/gate/auth mutations
      ↓
Approved or allowed learning is promoted into the appropriate persona memory/protocol surface
      ↓
Future work can use the improvement, still inside Research Spine gates
```

This is not fine-tuning. It is **structured prompt evolution** — it works with any local model, including 3B parameter models on modest consumer hardware.

Skills also self-evolve. Every invocation records quality per model × skill combination:

```python
ModelSkillStats(
    project_id="project-123",
    model_name="llama-3.2-3b",
    skill_name="thematic_analysis",
    success_rate=0.94,
    avg_quality_score=4.2,
    execution_count=47,
    last_improvement_proposed="2026-03-15"
)
```

When quality drops below threshold, Istara surfaces a diff between the current prompt and the proposed revision. You approve or reject. Skills that consistently produce verified, spine-valid outcomes earn higher health scores and priority routing inside that project. Raw tool success alone does not improve a skill.

All self-improvement now runs through an **Improvement Governance** contract and **DGM-H Archive**. Reasoning memories and telemetry can be recorded automatically, while behavior-changing updates to prompts, configs, skills, agents, UI, integrations, compute, or backend code become visible proposals with evidence, metrics, approval state, lineage, parent-selection scores, and rollback/revert tracking.

> **References:** Zhou et al. (2026) "Memento-Skills: Let Agents Design Agents" arXiv:2603.18743; Zhang et al. (2026) "Hyperagents: DGM-H Metacognitive Self-Modification for Cross-Domain Transfer" arXiv:2603.19461; Ouyang et al. (2026) "ReasoningBank: Scaling Agent Self-Evolving with Reasoning Memory" arXiv:2509.25140

---

## 2. 🔬 Multi-Model Validation With Human Review

> *"Improving Factuality and Reasoning in Language Models through Multiagent Debate"* — Du et al. (2024)

Research findings produced by a single LLM are unreliable. Istara employs a **compute-aware validation pipeline** that prefers distinct authorized models when they are healthy, falls back to dual-run validation when only two models are available, and uses Self-MoA-style single-model variation only when compute is constrained. The system records route evidence, model identities where available, coded evidence-unit reliability metrics, disagreement state, and human review state instead of treating one model answer as research fact.

### The Validation Stack

```
Sources (transcripts, surveys, notes, tickets, diaries, analytics)
      ↓
Stable evidence units with source span, participant, method, project provenance
      ↓
Inductive/open coding calibration → draft codebook → governed codebook freeze
      ↓
Distinct project-authorized models independently code the same evidence units
      ↓
Fleiss/Cohen/Krippendorff reliability over coded evidence-unit matrices
      ↓
Debate, adversarial review, and human reconciliation resolve disagreement
      ↓
Accepted/reconciled source-grounded atoms/nuggets feed Facts → Insights → Recommendations
      ↓
Only approved Done tasks can create report-ready findings
      ↓
Report with evidence chain, reliability status, route evidence, and review state
```

**Research findings are evidence-constrained, not magic-proof.** Istara stores source links, task review state, consensus scores, and dissent metadata so researchers can reject weak work. Reports draw from approved Done task evidence; tasks still in review are deliberately excluded.

The research-validity contract lives in [`docs/architecture/research-validity-contract.md`](docs/architecture/research-validity-contract.md). The self-improvement contract lives in [`docs/architecture/self-improvement-governance-contract.md`](docs/architecture/self-improvement-governance-contract.md). Fleiss' Kappa, Cohen's Kappa, and Krippendorff's Alpha are applied to coded evidence-unit matrices. Qualitative coding is not keyword tagging: models receive a protected coding protocol, codebook, inclusion/exclusion criteria, examples, evidence-unit schema, reliability policy, and promotion gate before they code. Autoresearch, ReasoningBank, Memento Skills, Meta-Hyperagent, self-evolution, RAG/GraphRAG, Prompt-RAG, and LLMLingua may improve process quality, but they cannot become report evidence or bypass the Research Spine.

When three or more distinct healthy project-authorized models exist, Istara defaults to multi-model coding/validation. With two distinct models it uses a two-coder reliability path. With one model it can run a Self-MoA-style fallback, but that result is marked lower assurance and cannot be represented as full ensemble reliability.

> **References:** Fleiss (1971) "Measuring nominal scale agreement among many raters"; Cohen (1960) "A coefficient of agreement for nominal scales"; O'Connor & Joffe (2020) "Intercoder Reliability in Qualitative Research"; MacQueen et al. (1998) "Codebook Development for Team-Based Qualitative Analysis"; Wang et al. (2024) "Mixture-of-Agents Enhances Large Language Model Capabilities"; Du et al. (2023) "Improving Factuality and Reasoning in Language Models through Multiagent Debate"; Li et al. (2025) "Rethinking Mixture-of-Agents"; Zheng et al. (2023) "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena"

---

## 3. 💾 Lossless Memory — Never Lose Context

> *"LLMLingua: Compressing Prompts for Accelerated Inference"* — Jiang et al. (2023)

Long research sessions accumulate more context than any model's window can hold. Istara manages this with a **six-level hierarchical context system** combined with LLMLingua-inspired prompt compression that achieves **30–74% token reduction** while preserving semantic fidelity.

### Context Hierarchy

```
Level 1 — Immediate: current turn (full resolution)
Level 2 — Session: active conversation (lightly compressed)
Level 3 — Project: cross-session research state (DAG-summarized)
Level 4 — Domain: persistent knowledge about your research area
Level 5 — Agent: persona + accumulated learnings
Level 6 — System: platform capabilities + skill registry
```

The **DAG Context Summarizer** (inspired by MemWalker, Chen et al. 2023) builds a directed acyclic graph of conversation segments, enabling hierarchical retrieval without information loss. Old summaries collapse into higher-level nodes; recent context remains at full resolution. The system navigates the graph to retrieve the most relevant past context for each new query.

**Prompt RAG** (Pan et al., 2024) retrieves relevant past context snippets at inference time, injecting them into the current prompt — turning a limited context window into an effectively unlimited research memory.

In research workflows, context tools stay subordinate to the Research Spine. Prompt RAG can add supporting context, but mandatory coding methodology, codebook criteria, reliability policy, and promotion gates are injected deterministically by the relevant services. LLMLingua-style compression preserves protected protocol, codebook, evidence schema, reliability, promotion, and auth blocks during compression and final trimming.

> **References:** Jiang et al. (2023) "LLMLingua: Compressing Prompts for Accelerated Inference of Large Language Models" EMNLP 2023; Chen et al. (2023) "Walking Down the Memory Maze: Beyond Context Limit through Interactive Reading" arXiv:2310.05029; Pan et al. (2024) "From RAG to Prompt RAG" ACL 2024

---

## 4. 🖥️ Distributed Compute Swarm

> *"Petals: Collaborative Inference and Fine-tuning of Large Models"* — Borzunov et al. (2022/2023)

Your team's idle hardware is a cluster waiting to be used. Istara's **Compute Relay** implements a WebSocket-based whole-request inference network where team members donate spare GPU or CPU capacity to a project-scoped pool. Inference requests are routed to available nodes with **priority-based scheduling, automatic capability detection, route counters, and failover**.

It is Petals-inspired in the collaboration sense, but it is not Petals-equivalent transformer layer sharding. Istara donates and routes complete chat, embedding, and model-server requests through authorized nodes.

### Relay Architecture

```
Research Agent (needs inference)
      ↓
Compute Router: query available nodes
      ↓
Node A: MacBook Pro M3 (local, latency 2ms)    — priority: HIGH
Node B: Linux workstation RTX 4090 (LAN, 8ms) — priority: HIGH
Node C: Relay server (WAN, 120ms)              — priority: MEDIUM
      ↓
Route to highest-priority available node
      ↓
Automatic failover if node drops
      ↓
Result streamed back to requesting agent
```

Connect your entire team with a single string:

```
rcl_<signed-user-or-compute-invite>
```

User invite strings no longer contain a pre-minted login JWT; they redeem into a
server-backed session and one-time recovery codes.

> **References:** Borzunov et al. (2022) "Petals: Collaborative Inference and Fine-tuning of Large Models" arXiv:2209.01188; Borzunov et al. (2023) "Distributed Inference and Fine-tuning of Large Language Models Over the Internet" NeurIPS 2023

---

## 5. 🔎 Karpathy's Autoresearch Built In

> *"autoresearch: autonomous experiment loops for AI systems"* — Karpathy (2026)

Istara includes an **autonomous research optimization engine** inspired by Karpathy's autoresearch framework. It runs controlled, project-scoped experiments to improve process quality — testing RAG retrieval parameters, skill prompt templates, model temperature settings, and related configuration without letting the experiment mutate production state.

Experiments are sandboxed, rate-limited, reversible, and non-reportable. A successful experiment becomes a governed proposal, not an automatic production change.

### Autoresearch Loop

```
Measure current system performance baseline
      ↓
Generate experiment hypothesis (e.g., "reduce chunk overlap from 200 to 100 tokens")
      ↓
Run controlled A/B test on held-out evaluation set
      ↓
Measure quality delta (retrieval precision, skill output scores)
      ↓
If improvement ≥ threshold: revert sandbox mutation and create proposal_ready candidate
      ↓
Governance review approves, rejects, or archives the proposal with rollback evidence
      ↓
Repeat: next hypothesis
```

The system maintains a **Skill Health Monitor** dashboard showing per-skill performance trends, which experiments are running, which proposals are awaiting review, and which governed changes have been approved. Autoresearch artifacts are process evidence only; they cannot become research findings or report evidence.

> **Reference:** Karpathy (2026) "autoresearch" github.com/karpathy/autoresearch

---

## 6. 📊 Research Spine Evidence Chain

> *"The Atomic Research model"* — Sharon & Gadbaw (2018)

Every insight Istara produces is expected to remain traceable because it is connected to a verified evidence chain with source references and task review state. This implements the Atomic Research methodology developed at WeWork (Sharon & Gadbaw, 2018) as a computational pipeline.

```
Raw source quote or observation
      ↓  creates: source evidence unit with exact text + provenance
Candidate atom/nugget
      ↓  requires: independent extraction/coding + grounding + reliability/reconciliation
Accepted atom/nugget
      ↓  promotes: verified pattern, fact, insight, recommendation
Report evidence
      ↓  requires: accepted/reconciled evidence on a human-approved Done task
```

**No reportable recommendation without an accepted insight. No accepted insight without accepted facts. No accepted fact without accepted atoms/nuggets. No accepted atom/nugget without source-grounded validation.**

Every level of the chain is stored as a discrete database record with foreign key relationships enforcing the hierarchy. Atomic Research artifacts are not trusted merely because a model wrote them; raw model outputs remain candidate/provisional until the Research Spine accepts or reconciles them. Reports use findings from approved Done tasks; task outputs still in review are not report evidence. When you export a research report, every recommendation should hyperlink back through the chain to the exact interview passage, survey response, or observation that supports it.

> **Reference:** Sharon & Gadbaw (2018) "Atomic Research" WeWork Research Operations

---

## 7. 🔍 Hybrid RAG: Vector + Keyword Search

> *"Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"* — Lewis et al. (2020)

Pure vector search misses exact terminology. Pure keyword search misses semantic similarity. Istara uses **Reciprocal Rank Fusion** to blend both:

```
Query
  ├── LanceDB vector search (cosine similarity on embeddings)  → ranked list A
  └── BM25 keyword search (term frequency × inverse doc freq) → ranked list B
                    ↓
         Reciprocal Rank Fusion
         score(d) = Σ 1/(k + rank_i(d))
                    ↓
         Merged ranking: 70% vector weight · 30% BM25 weight
                    ↓
         Top-k results injected into agent context
```

This means Istara finds semantically similar content ("participant struggled with navigation") AND exact terminology matches ("information architecture"). Switch to pure vector or pure keyword mode per-query when you need it.

Hybrid RAG is Istara's exact-evidence retrieval layer. BM25 fallback preserves `evidence_unit_id`, document/source span, review status, reliability status, and provenance; when that provenance is missing, the result is marked non-promotional. Evidence Graph / GraphRAG is the synthesis and traceability layer, used for cross-document relationships and dependency questions, but graph answers must backfill exact evidence through Hybrid RAG before anything can be promoted.

**LanceDB is embedded** — no separate vector database process, no network overhead, no configuration.

> **References:** Lewis et al. (2020) "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks" NeurIPS 2020; Cormack et al. (2009) "Reciprocal rank fusion outperforms condorcet and individual rank learning methods" SIGIR 2009; Robertson & Zaragoza (2009) "The Probabilistic Relevance Framework: BM25 and Beyond" *Foundations and Trends in Information Retrieval* 3(4)

---
![](https://istara.goatcounter.com/count?p=/count-features-middle)
## 8. 📱 Deploy Surveys & Interviews on WhatsApp and Telegram

> *"AURA: Adaptive User Research Assistant"* — arXiv:2510.27126

Istara supports **AURA-style adaptive interview workflows** and credentialed setup paths for messaging and survey channels. Live participant channels require the relevant provider credentials or bounded test simulators; without them, Istara documents the setup/error path rather than pretending a real participant deployment occurred.

```
Researcher designs interview guide in Istara
      ↓
Deploy to: WhatsApp Business · Telegram Bot · Typeform · SurveyMonkey · Google Forms
      ↓
Participant receives message in their preferred app
      ↓
Adaptive agent conducts interview: asks follow-ups, probes interesting answers,
adjusts question order based on prior responses
      ↓
Responses stream back to Istara in real time
      ↓
Register raw source → extract evidence units → create candidate atoms/codes
      ↓
Run reliability, grounding, reconciliation, and review gates
      ↓
AI-Detection check flags responses that appear machine-generated
```

The adaptive interview engine is intended to adjust question phrasing and order based on prior answers, producing richer qualitative data than static survey forms when the channel integration is configured. Imported responses do not become trusted findings directly; they enter the same Research Spine as documents, interviews, and manual notes.

> **Reference:** AURA: Adaptive User Research Assistant, arXiv:2510.27126

---

## 9. 🎨 Figma + Google Stitch AI Design Tools

Istara bridges research and design in a single workflow:

- **Figma Integration**: Import design files, extract design system tokens, link design decisions to accepted/reconciled research evidence, run compliance checks against UX Laws
- **Google Stitch MCP**: Generate screen wireframes and UI concepts from accepted insights and clearly marked candidate evidence — describe what users need, get design proposals
- **Design Briefs**: Auto-generate design briefs from reportable findings, with UX Law references attached to each recommendation
- **Evidence-to-Design Traceability**: Every reportable design decision links back to accepted atoms/nuggets and source evidence that motivated it

---

## 10. ⚖️ 30 Laws of UX Automated Compliance

> *"Laws of UX: Design Principles for Persuasive and Ethical Products"* — Yablonski (2020)

Run any interface description, design file, or user flow through Istara's **UX Law compliance auditor** and receive a scored report against all 30 Laws of UX — including Fitts's Law, Hick's Law, Jakob's Law, Miller's Law, the Peak-End Rule, and 25 more.

```
Input: interface description / Figma file / user flow diagram
      ↓
Compliance check against 30 Laws of UX
      ↓
Per-law score: PASS / WARN / FAIL + evidence + severity
      ↓
Aggregate compliance score
      ↓
Prioritized recommendations with research citations
      ↓
Export: PDF report / JSON for CI pipeline integration
```

**Integrate compliance checking into your CI/CD pipeline** — catch UX violations before they ship to production.

> **Reference:** Yablonski (2020) *Laws of UX: Design Principles for Persuasive and Ethical Products* O'Reilly Media

---

## 11. 📄 Smart Document Intelligence

Drop any file into Istara and the document pipeline activates automatically:

```
Upload (PDF · DOCX · TXT · transcript · spec)
      ↓
Auto-classify: research report / interview transcript / survey data /
               design spec / competitive analysis / academic paper
      ↓
Extract source evidence units → draft candidate atoms/codes → validate/reconcile before tasks
      ↓
Link findings back to exact source passages with page/line references
      ↓
Index in hybrid RAG for future retrieval
```

**External folder linking** connects Google Drive, Dropbox, or any local folder without copying files — Istara watches for changes and syncs automatically. Cloud-aware: detects when files are stored remotely and adapts ingestion accordingly.

---

## 12. 🔗 Interoperability: MCP + A2A Protocol

Istara speaks both dominant agent interoperability standards:

**Model Context Protocol (MCP)** — Anthropic's open standard for tool-augmented LLM interactions. Istara exposes an MCP server (disabled by default, `http://localhost:8001/mcp` when enabled) with 8 tools:

```
list_skills()         list_projects()       get_findings()
search_memory()       execute_skill()       deploy_research()
create_project()      get_deployment_status()
```

**Agent-to-Agent Protocol (A2A)** — Google's standard for agent discovery and communication. Istara publishes a discovery manifest at `/.well-known/agent.json` enabling any A2A-compliant agent framework to discover and invoke Istara's capabilities.

Both interfaces are gated by `MCPAccessPolicy` with per-tool permissions, JWT authentication, and full audit logging.

> **References:** Model Context Protocol (2025) "MCP Specification" modelcontextprotocol.io; Agent2Agent Project (2026) "A2A Protocol Specification" a2a-protocol.org

---

## 13. 🛡️ Security and Privacy by Design

Istara is **zero-trust by default**:

- **JWT authentication** on every API endpoint — no unauthenticated access
- **Better Auth-inspired account hardening** — first admin receives one-time recovery codes during onboarding, passkey setup is offered immediately, users can change username/profile/password from Settings, and admin-created users receive one-time recovery codes
- **Two-factor options** — password sign-in can be protected with TOTP, recovery codes are the fallback factor, and WebAuthn/passkeys provide phishing-resistant passwordless sign-in; Istara does not use SMS or email OTP factors
- **Fernet field encryption** on sensitive database fields — secrets are encrypted at rest
- **Admin-managed file and backup encryption** — when enabled, managed uploads, stored document text, and future backup archives are encrypted at rest; backups are written as `.tar.gz.enc` and require the correct file-encryption key to restore
- **Secure key handling** — the file-encryption key should live in a secrets manager or macOS Keychain, with an owner-only local key-file fallback for source installs; losing the key is destructive for encrypted files and backups
- **Local-first architecture** — LLM inference runs on your hardware via LM Studio or Ollama; no data transmitted to external APIs unless you explicitly configure one
- **MCP server OFF by default** — external agent access requires conscious opt-in
- **SQLite database** — a single portable file you control completely
- **No phone-home telemetry** — Istara records local process, route, quality, and governance events for audits, but never sends them to an external service

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js 14)                        │
│  Chat · Kanban · Findings · Documents · Skills · Agents · Settings  │
│  22 views · Contextual onboarding per view · Dark/light mode        │
│  Zustand state · WCAG 2.1 AA compliant · Tauri system tray          │
└────────────────────────────┬────────────────────────────────────────┘
                             │ REST (400+ endpoints) + WebSocket (16 events)
┌────────────────────────────▼────────────────────────────────────────┐
│                         BACKEND (FastAPI)                           │
│                                                                     │
│  ┌────────────┐  ┌────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │ 400+ REST  │  │ WebSocket  │  │ MCP Server  │  │ A2A Protocol│  │
│  │  endpoints │  │  Manager   │  │  (opt-in)   │  │  Discovery  │  │
│  └──────┬─────┘  └──────┬─────┘  └──────┬──────┘  └──────┬──────┘  │
│         └───────────────┴───────────────┴─────────────────┘        │
│                                    │                                │
│  ┌─────────────────────────────────▼──────────────────────────┐    │
│  │                        CORE ENGINE                         │    │
│  │                                                            │    │
│  │  MetaOrchestrator (A2A message routing)                    │    │
│  │  Context Hierarchy (6 levels) + DAG Summarizer             │    │
│  │  Hybrid RAG: LanceDB + BM25 + RRF + provenance status      │    │
│  │  Evidence Graph / GraphRAG traceability and synthesis      │    │
│  │  LLMLingua Compressor with protected Research Spine blocks │    │
│  │  Self-Improvement Governance + Skill Health Monitor        │    │
│  │  Sandboxed Autoresearch proposals, not live mutations      │    │
│  │  Multi-model Coding/Validation (Kappa/Alpha + route proof) │    │
│  │  Resource Governor + Priority Scheduler                    │    │
│  │  Accepted Atomic Chain (Atom→Fact→Insight→Rec)             │    │
│  └─────────────────────────────────┬──────────────────────────┘    │
│                                    │                                │
│  ┌──────────────────┐  ┌───────────▼──────────┐  ┌──────────────┐  │
│  │  Agent Personas  │  │      Data Layer       │  │  LLM Layer   │  │
│  │  CORE.md         │  │  SQLite (51+ models)  │  │  LM Studio   │  │
│  │  SKILLS.md       │  │  LanceDB (vectors)    │  │  Ollama      │  │
│  │  PROTOCOLS.md    │  │  Fernet encryption    │  │  Any OpenAI- │  │
│  │  MEMORY.md       │  │  JWT auth             │  │  compatible  │  │
│  └──────────────────┘  └───────────────────────┘  └──────────────┘  │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    INTEGRATIONS                             │   │
│  │  Compute Relay (WebSocket swarm · Petals-inspired)          │   │
│  │  Survey Channels (WhatsApp · Telegram · Typeform · Forms)   │   │
│  │  Design Tools (Figma · Google Stitch MCP)                   │   │
│  │  Notifications (Slack · Telegram · WhatsApp)                │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, React, Tailwind CSS, Zustand |
| Backend | FastAPI, Python 3.12, async SQLAlchemy 2.0 |
| Database | SQLite + aiosqlite (zero-config, ACID, single file) |
| Vector Store | LanceDB (embedded, no server process, no config) |
| Search | BM25 keyword index + Reciprocal Rank Fusion |
| Desktop App | Tauri v2 (thin GUI tray, delegates to `istara.sh` for process management) |
| Real-time | WebSocket — 16 broadcast event types |
| LLM Providers | LM Studio · Ollama · Any OpenAI-compatible API |
| Compute Relay | WebSocket-based distributed inference swarm |
| Installers | macOS DMG · Windows NSIS EXE · Linux AppImage |

---
![](https://istara.goatcounter.com/count?p=/count-features-middle2)
## Quick Start

See [**Install**](#install) above for all installation methods. Prerequisites:

- **Python 3.12+** and **Node 20+** (the shell installer handles these automatically)
- **[LM Studio](https://lmstudio.ai)** or **[Ollama](https://ollama.ai)** with at least one model loaded

After installing, start the server and open [http://localhost:3000](http://localhost:3000):

```bash
istara start
```

---

## 53 Research Skills

<details>
<summary><strong>View all 53 skills organized by Double Diamond phase</strong></summary>

### Discover Phase (14 skills)

| Skill | Description |
|---|---|
| User Interviews | Plan, conduct, and synthesize 1:1 research interviews |
| Contextual Inquiry | Observe users in their natural environment |
| Survey Design | Design validated questionnaires with bias controls |
| Survey Generator | Generate full survey instruments from a research brief |
| Competitive Analysis | Systematic competitive landscape evaluation |
| Diary Studies | Design and analyze longitudinal self-report studies |
| Field Studies | Plan and synthesize ethnographic field observations |
| Analytics Review | Extract behavioral insights from quantitative data |
| Accessibility Audit | WCAG 2.1 AA compliance evaluation |
| Desk Research | Synthesize secondary sources and literature |
| Stakeholder Interviews | Elicit requirements from business stakeholders |
| Interview Question Generator | Generate calibrated question sets by research objective |
| Channel Research Deployment | Deploy research instruments to WhatsApp/Telegram/Forms |
| Survey AI Detection | Flag machine-generated survey responses |

### Define Phase (12 skills)

| Skill | Description |
|---|---|
| Thematic Analysis | Inductive coding and theme development |
| Kappa Thematic Analysis | Multi-coder thematic analysis with Fleiss' Kappa reliability |
| Affinity Mapping | Cluster observations into meaningful groups |
| Empathy Mapping | Four-quadrant user empathy model (Say/Think/Do/Feel) |
| Persona Creation | Evidence-grounded user persona synthesis |
| Journey Mapping | End-to-end experience journey with emotions and friction points |
| HMW Statements | How-Might-We opportunity framing from insights |
| JTBD Analysis | Jobs-To-Be-Done functional, emotional, and social job mapping |
| Research Synthesis | Cross-study synthesis across projects and methods |
| Taxonomy Generator | Build hierarchical classification systems from data |
| Prioritization Matrix | Impact/effort and RICE prioritization frameworks |
| User Flow Mapping | Task-level user flow analysis and gap identification |

### Develop Phase (10 skills)

| Skill | Description |
|---|---|
| Usability Testing | Moderated and unmoderated usability test design and analysis |
| Heuristic Evaluation | Nielsen's 10 usability heuristics audit |
| Cognitive Walkthrough | Step-by-step cognitive load evaluation |
| Concept Testing | Early-stage concept validation and desirability testing |
| Card Sorting | Open and closed card sort analysis |
| Tree Testing | Information architecture findability testing |
| A/B Test Analysis | Statistical analysis of controlled experiments |
| Design Critique | Structured critique against research evidence |
| Prototype Feedback | Collect and synthesize feedback on interactive prototypes |
| Workshop Facilitation | Design and facilitate collaborative research workshops |

### Deliver Phase (10 skills)

| Skill | Description |
|---|---|
| Design System Audit | Evaluate design system consistency and coverage |
| SUS/UMUX Scoring | System Usability Scale and UMUX score calculation |
| NPS Analysis | Net Promoter Score trend analysis and driver identification |
| Stakeholder Presentation | Generate research presentation decks |
| Handoff Documentation | Developer handoff with research rationale |
| Regression Impact | Assess design change impact on prior research findings |
| Task Analysis Quant | Quantitative task completion and time-on-task analysis |
| Repository Curation | Organize and tag the research repository |
| Research Retro | Project retrospective and methodology improvement |
| Longitudinal Tracking | Track metrics and insights across research waves |

### Cross-Phase Skills (7 skills)

| Skill | Description |
|---|---|
| Agent Factory | Create new specialized agents at runtime |
| Skill Evolution | Propose governed prompt/skill improvements from verified Research Spine outcomes |
| UX Law Compliance | Automated audit against 30 Laws of UX |
| Design Brief Generator | Generate design briefs from research findings |
| Evidence Chain Validator | Verify accepted atom/nugget → fact → insight → recommendation linkage |
| Multi-model Validator | Validate source evidence units with distinct project-authorized models and reliability metrics |
| Autoresearch Optimizer | Run sandboxed optimization experiments that produce governed improvement proposals |

</details>

---

## 5 AI Agents

<details>
<summary><strong>View agent personas and capabilities</strong></summary>

### Cleo (`istara-main`) — Primary Researcher

Cleo is your primary research partner. She executes all 53 skills, manages projects end-to-end, maintains the evidence chain, and is the main conversational interface. Her MEMORY.md accumulates learnings about your research style, preferred methods, and domain knowledge over time.

**Core capabilities:** All 53 research skills · Project management · Evidence chain construction · Multi-model validation orchestration · Report generation

### Sentinel (`istara-devops`) — Data Integrity Guardian

Sentinel watches over the health of the entire system. He monitors for orphaned records, validates evidence chain integrity, runs integrity checks, and ensures the research repository stays coherent as it grows.

**Core capabilities:** Database health monitoring · Evidence chain integrity validation · Orphaned record detection · System performance monitoring · Automated repair suggestions

### Pixel (`istara-ui-audit`) — WCAG Compliance Expert

Pixel is a specialist in interface accessibility and usability compliance. She runs Nielsen heuristics evaluations, WCAG 2.1 AA audits, and 30 Laws of UX compliance checks on any interface description or design artifact.

**Core capabilities:** WCAG 2.1 AA audit · Nielsen's 10 heuristics evaluation · 30 Laws of UX compliance · Accessibility scoring · Remediation recommendations

### Sage (`istara-ux-eval`) — Cognitive Load Analyst

Sage analyzes user journeys for cognitive load, workflow friction, and mental model mismatches. He specializes in task analysis, flow mapping, and identifying the points in an experience where users get stuck or fail.

**Core capabilities:** Cognitive walkthrough · Mental model analysis · Workflow friction detection · Task completion analysis · User journey evaluation

### Echo (`istara-sim`) — End-to-End Tester

Echo is the quality assurance agent. She runs the 76-scenario simulation test suite, performs regression testing on research workflows, and validates that system changes don't break existing research pipelines.

**Core capabilities:** 76-scenario E2E test suite · Regression testing · User simulation · API endpoint validation · Performance benchmarking

</details>

---

## Screenshots

Screenshots are intentionally omitted until the public deployment assets are stable.
*Additional architecture and process references are listed in [DOCUMENTATION.md](DOCUMENTATION.md).*

---

## Repository Structure

```
istara/
├── backend/                   # FastAPI backend (Python 3.12)
│   └── app/
│       ├── api/               # 400+ REST endpoints + WebSocket manager
│       ├── agents/            # Agent personas (CORE, SKILLS, PROTOCOLS, MEMORY)
│       ├── core/              # Orchestrator, RAG, evolution engine, autoresearch
│       ├── models/            # 51+ SQLAlchemy 2.0 models
│       ├── services/          # Survey, MCP, channel, compute relay integrations
│       └── skills/            # Skill base class, factory, 53 implementations
├── frontend/                  # Next.js 14 (React, Tailwind CSS, Zustand)
│   └── src/
│       ├── components/        # 22 views + shared UI components
│       ├── stores/            # Zustand state management
│       └── lib/               # API client, route helpers, shared types
├── desktop/                   # Tauri v2 system tray application
├── installer/                 # macOS DMG + Windows NSIS + Linux AppImage configs
├── relay/                     # Compute donation WebSocket relay server
├── skills/                    # Skill definition files (SKILL.md per skill)
├── security/                  # Security benchmark matrix, release checklist, assessments
├── testing/                   # Testing, eval, benchmark, and historical baseline strategy
├── tests/
│   └── simulation/            # 76-scenario E2E simulation test suite
└── scripts/                   # Integrity checks, agent MEMORY.md updaters
```

---

## Contributing

Istara is MIT-licensed and actively welcomes contributions. High-impact areas:

- **New research skills** — Add a `SKILL.md` + JSON definition. No Python required for most skills.
- **LLM adapters** — Support for new local inference backends
- **Channel integrations** — Discord, Microsoft Teams, Signal, etc.
- **UI components** — Accessibility improvements, new research views
- **Research methodology** — Improved prompts and validation logic, with protected protocol/gate changes governed
- **Academic citations** — Connect features to relevant research literature

```bash
# Run the backend test suite
pytest tests/

# Run the 76-scenario E2E simulation agent
node tests/simulation/run.mjs

# Verify system integrity before committing
python scripts/check_integrity.py

# Verify CI/CD governance and production rehearsal
python scripts/check_ci_governance.py
python scripts/security_benchmark.py --fail-on-threshold
python scripts/production_rehearsal.py --json

# Run deterministic property and mutation gates
pytest tests/test_property_contracts.py -q
python scripts/run_backend_mutation.py
(cd frontend && npm run test:unit && npm run test:mutation)
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions, code style guide, and the change checklist.
See [TESTING.md](TESTING.md), [SECURITY.md](SECURITY.md), and [DOCUMENTATION.md](DOCUMENTATION.md) before release-sensitive changes.

---
![](https://istara.goatcounter.com/count?p=/count-features-bottom)
## Academic References and Standards

<details>
<summary><strong>Full bibliography and standards (38 references)</strong></summary>

### Agent Self-Evolution and Design

1. **Zhou et al. (2026)** — "Memento-Skills: Let Agents Design Agents" *arXiv:2603.18743*. The foundational paper for Istara's agent factory: agents detecting capability gaps and designing new specialized agents.

2. **Zhang et al. (2026)** — "Hyperagents: DGM-H Metacognitive Self-Modification for Cross-Domain Transfer and Recursive Improvement" *arXiv:2603.19461*. Framework for metacognitive self-modification in autonomous agents; informs Istara's skill evolution pipeline.

### Multi-Model Validation

3. **Fleiss, J. L. (1971)** — "Measuring Nominal Scale Agreement among Many Raters" *Psychological Bulletin* 76(5):378-382. DOI: 10.1037/h0031619. Used for 3+ coder reliability over item-by-rater nominal coding matrices.

4. **Cohen, J. (1960)** — "A Coefficient of Agreement for Nominal Scales" *Educational and Psychological Measurement* 20(1):37-46. DOI: 10.1177/001316446002000104. Used for two-coder reliability.

5. **O'Connor & Joffe (2020)** — "Intercoder Reliability in Qualitative Research: Debates and Practical Guidelines" *International Journal of Qualitative Methods*. DOI: 10.1177/1609406919899220. Used for the independent-coder/reconciliation process.

6. **MacQueen et al. (1998)** — "Codebook Development for Team-Based Qualitative Analysis" *Cultural Anthropology Methods* 10(2):31-36. DOI: 10.1177/1525822X980100020301. Used for code definitions, inclusion/exclusion criteria, and team codebook discipline.

7. **Wang et al. (2024)** — "Mixture-of-Agents Enhances Large Language Model Capabilities" *arXiv:2406.04692*. Inspiration for Istara's multi-agent validation layer.

8. **Du et al. (2023)** — "Improving Factuality and Reasoning in Language Models through Multiagent Debate" *arXiv:2305.14325*. Adversarial debate protocol for reducing unsupported outputs; implemented as a validation/refinement path in Istara's stack.

9. **Li et al. (2025)** — "Rethinking Mixture-of-Agents: Is Mixing Different Large Language Models Beneficial?" *arXiv:2502.00674*. Single-model Self-MoA variant for constrained-compute environments.

10. **Zheng et al. (2023)** — "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena" *NeurIPS 2023*. LLM-as-Judge methodology used only as auxiliary validation and not as a replacement for evidence/reliability/human review gates.

### Memory and Context Management

11. **Jiang et al. (2023)** — "LLMLingua: Compressing Prompts for Accelerated Inference of Large Language Models" *EMNLP 2023*. Prompt compression; Istara protects methodology/codebook/evidence/reliability blocks from compression loss.

12. **Jiang et al. (2023)** — "LongLLMLingua: Accelerating and Enhancing LLMs in Long Context Scenarios via Prompt Compression" *arXiv:2310.06839*. Long-context compression reference; protected research-validity blocks remain non-compressible.

13. **Chen et al. (2023)** — "Walking Down the Memory Maze: Beyond Context Limit through Interactive Reading" *arXiv:2310.05029*. MemWalker DAG-based hierarchical summarization; implemented in Istara's context hierarchy.

14. **Pan et al. (2024)** — "From RAG to Prompt RAG: Revisiting Retrieval-Augmented Generation for Long-Context Language Models" *ACL 2024*. Prompt RAG for injecting retrieved context at inference time; Istara still injects mandatory coding methodology deterministically.

15. **Ouyang et al. (2026)** — "ReasoningBank: Scaling Agent Self-Evolving with Reasoning Memory" *arXiv:2509.25140*. Structured reasoning memory for distilling successful and failed agent trajectories into reusable strategies; implemented as Istara's shared orchestration-memory layer for Memento routing, autoresearch, and meta-agent observation.

### Retrieval-Augmented Generation

16. **Lewis et al. (2020)** — "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks" *NeurIPS 2020*. The foundational RAG paper; Istara's hybrid retrieval is the exact-evidence layer.

17. **Edge et al. (2024)** — "From Local to Global: A Graph RAG Approach to Query-Focused Summarization" *arXiv:2404.16130*. Basis for GraphRAG-style global synthesis; Istara uses graph synthesis only over traceable evidence and never as a bypass around coding/reliability/review gates.

18. **Microsoft Research GraphRAG / LazyGraphRAG / DRIFT Search** — Official Microsoft Research and GraphRAG documentation. Used for local/global/DRIFT search concepts and cost-aware graph retrieval design.

19. **Cormack et al. (2009)** — "Reciprocal rank fusion outperforms condorcet and individual rank learning methods" *SIGIR 2009*. RRF algorithm merging vector and keyword search rankings in Istara.

20. **Robertson & Zaragoza (2009)** — "The Probabilistic Relevance Framework: BM25 and Beyond" *Foundations and Trends in Information Retrieval* 3(4). BM25 keyword search component of Istara's hybrid retrieval.

### Distributed Compute

21. **Borzunov et al. (2022)** — "Petals: Collaborative Inference and Fine-tuning of Large Models" *arXiv:2209.01188*. Distributed inference architecture; Istara's Compute Relay is inspired by Petals.

22. **Borzunov et al. (2023)** — "Distributed Inference and Fine-tuning of Large Language Models Over the Internet" *NeurIPS 2023*.

### Survey and Interview Channels

23. **AURA (2025)** — "AURA: Adaptive User Research Assistant" *arXiv:2510.27126*. Adaptive interview agent architecture deployed by Istara across messaging channels.

### Research Methodology

24. **Sharon & Gadbaw (2018)** — "Atomic Research" WeWork Research Operations. Istara implements Atomic Research as an accepted, source-validated Atom/Nugget→Fact→Insight→Recommendation evidence chain.

25. **Yablonski, J. (2020)** — *Laws of UX: Design Principles for Persuasive and Ethical Products*. O'Reilly Media. The 30 Laws of UX audited by Istara's compliance checker.

26. **Karpathy, A. (2026)** — "autoresearch: autonomous experiment loops for AI systems" github.com/karpathy/autoresearch. Autonomous optimization framework; implemented as Istara's autoresearch engine.

### Interoperability Standards

21. **Model Context Protocol (2025)** — "MCP Specification" modelcontextprotocol.io. Open standard for tool-augmented LLM interactions; Istara exposes an MCP server.

22. **Agent2Agent Project (2026)** — "Agent2Agent (A2A) Protocol Specification" a2a-protocol.org. Agent discovery and communication standard; Istara publishes an A2A discovery manifest.

### Evaluation and Benchmarking

23. **OpenAI (2026)** — "Evals" github.com/openai/evals and OpenAI Evals API documentation. Framework and registry model for repeatable LLM/system evaluations.

24. **UK AI Security Institute (2026)** — "Inspect AI" inspect.aisi.org.uk. Evaluation harness pattern for reproducible model and agent assessments.

25. **Liang et al. (2022)** — "Holistic Evaluation of Language Models" Stanford CRFM HELM. Multi-metric evaluation inspiration for Istara's versioned eval baselines.

26. **Es et al. (2023)** — "RAGAS: Automated Evaluation of Retrieval Augmented Generation" *arXiv:2309.15217*. RAG evaluation framing for faithfulness, context relevance, and answer relevance.

27. **Berkeley Sky Computing Lab (2026)** — "Berkeley Function Calling Leaderboard (BFCL) V4" gorilla.cs.berkeley.edu. Tool/function-call correctness benchmark inspiration for Istara ReAct and skill schema tests.

28. **Yao et al. (2024)** — "tau-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains" *arXiv:2406.12045*. Multi-turn tool-agent-user evaluation inspiration for Istara simulation and agentic workflows.

### Security, Identity, and Release Standards

29. **OWASP (2025)** — "Application Security Verification Standard 5.0.0" owasp.org. Application security baseline for Istara's benchmark matrix.

30. **NIST (2025)** — "Digital Identity Guidelines, SP 800-63-4 and SP 800-63B-4" pages.nist.gov. Identity, authenticator, MFA, passkey, and session guidance.

31. **Better Auth (2026)** — "Security" better-auth.com/docs/reference/security. Comparative authentication guidance for base URLs, trusted origins, sessions, CSRF safeguards, rate limiting, and secret handling.

32. **W3C (2026)** — "Web Authentication: An API for accessing Public Key Credentials, Level 3" w3.org/TR/webauthn-3. Passkey/WebAuthn reference for origin/RP validation and public-key credential behavior.

33. **IETF (2025)** — "OAuth 2.0 Security Best Current Practice, RFC 9700" datatracker.ietf.org. OAuth/OpenID-style provider security guidance.

34. **OWASP GenAI Security Project (2025)** — "OWASP Top 10 for LLM Applications 2025" genai.owasp.org. Prompt injection, sensitive disclosure, model/provider, and tool-abuse threat model.

35. **NIST (2023–2026)** — "AI Risk Management Framework 1.0" and GenAI profile resources. AI risk governance for agentic orchestration, telemetry, evaluation, and rollback.

36. **Model Context Protocol (2025)** — "MCP Specification 2025-11-25" modelcontextprotocol.io. Tool, prompt, resource, authorization, and trust/safety model for MCP integrations.

37. **Agent2Agent Project (2026)** — "Agent2Agent (A2A) Protocol Specification" a2a-protocol.org. Agent-card discovery and JSON-RPC interoperability reference.

38. **OpenSSF / SLSA / GitHub (2026)** — OpenSSF Scorecard, SLSA v1.2, and GitHub Artifact Attestations. Supply-chain posture and release provenance references for installer hardening.

</details>

---

## License

MIT © 2026 Istara Contributors — see [LICENSE](LICENSE).

---

<div align="center">

Built for researchers who believe their data should stay theirs.

**Autonomous. Self-improving. Zero-trust. Evidence first.**

[GitHub](https://github.com/henrique-simoes/Istara) · [Issues](https://github.com/henrique-simoes/Istara/issues) · [Discussions](https://github.com/henrique-simoes/Istara/discussions)

</div>
