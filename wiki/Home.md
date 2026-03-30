# Istara Wiki

**Local-first AI agents for UX Research.**

Istara is an open-source platform that runs entirely on your machine. It helps UX researchers organize, analyze, and synthesize research findings using local LLMs — no data ever leaves your computer.

---

## Quick Navigation

| Topic | Description |
|-------|-------------|
| [Getting Started](Getting-Started) | Installation, first run, hardware requirements |
| [Architecture](Architecture) | System design, data flow, technology stack |
| [Features](Features) | Complete feature reference |
| [Agent System](Agent-System) | How the 5 AI agents work, self-evolution, personas |
| [API Reference](API-Reference) | REST API endpoints and WebSocket events |
| [Security](Security) | JWT auth, local-first model, encryption |
| [FAQ](FAQ) | Frequently asked questions |
| [Troubleshooting](Troubleshooting) | Common issues and fixes |

---

## What Is Istara?

Istara combines three paradigms into a single local application:

- **AI Research Agent** — a conversational assistant that executes 53 UXR skills across the Double Diamond
- **Research Repository** — structured evidence chain (Nugget → Fact → Insight → Recommendation) with full traceability
- **Multi-Agent System** — 5 specialized agents (Cleo, Sentinel, Pixel, Sage, Echo) that collaborate autonomously

Unlike cloud-based research tools, Istara processes everything locally. Your interview transcripts, findings, and insights never touch an external server.

---

## Current Version

**2026.03.29** (CalVer: YYYY.MM.DD)

Istara uses calendar versioning. Each release is dated to make it easy to know how current your installation is. Auto-update checks run at startup and create a pre-update backup before applying changes.

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, React, Tailwind CSS, Zustand |
| Backend | FastAPI, Python 3.11, async SQLAlchemy |
| Database | SQLite + LanceDB (vector store) |
| LLM | LM Studio or Ollama (local inference) |
| Desktop | Tauri (macOS + Windows) |
| Real-time | WebSocket (16 event types) |

---

## License

Istara is open source under the MIT License.

GitHub: https://github.com/henrique-simoes/Istara
