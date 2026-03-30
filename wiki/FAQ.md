# Frequently Asked Questions

---

## General

### What is Istara?
Istara is a local-first, privacy-first AI agent platform for UX Research. It runs entirely on your machine using local LLMs (LM Studio or Ollama). It helps UX researchers organize, analyze, and synthesize research findings without sending any data to external servers.

### Is Istara free?
Yes. Istara is open-source under the MIT License. There is no subscription, no cloud plan, and no feature gating. Everything runs on your hardware.

### Does Istara require an internet connection?
No. Once installed, Istara runs entirely offline. The only time it uses the internet is to check for updates (which can be disabled in Settings) and optionally to connect to Telegram or Slack for community channel features.

### What data does Istara collect?
None. Istara does not collect telemetry, usage data, or any analytics. All your research data stays on your machine in local SQLite and LanceDB databases.

### Who makes Istara?
Istara is an open-source project. Contributions are welcome via GitHub: https://github.com/henrique-simoes/Istara

---

## Installation and Setup

### What are the minimum hardware requirements?
- 8 GB RAM (16 GB recommended)
- Python 3.11+
- Node.js 18+
- macOS, Windows, or Linux

### Which LLM should I use?
For most UX research tasks, a 7B–14B parameter instruction-tuned model works well. Recommendations:
- **8 GB RAM**: Qwen2.5-3B-Instruct (Q4_K_M)
- **16 GB RAM**: Qwen2.5-7B-Instruct (Q4_K_M) or Llama-3.1-8B-Instruct
- **32 GB RAM**: Qwen2.5-14B or Mistral-7B (Q8)
- **64 GB+ RAM**: Qwen2.5-32B or Llama-3.1-70B

Istara auto-detects your hardware and recommends appropriate models in Settings.

### Can I use OpenAI or other cloud APIs instead of local models?
Istara is designed for local inference. If your LLM provider exposes an OpenAI-compatible API (many do), you can point Istara at it via the `LM_STUDIO_URL` environment variable. However, this would send your research data to that external API — which goes against Istara's privacy-first philosophy.

### How do I update Istara?
Istara checks for updates automatically at startup. When an update is available, you'll see a notification. Before applying the update, a backup is created automatically. You can also check for updates manually from Settings > About.

---

## LLM Providers

### LM Studio vs. Ollama — which should I use?
- **LM Studio**: Better for beginners. Has a GUI for downloading and managing models, hardware-aware recommendations, and easy server management.
- **Ollama**: Better for power users. Lightweight CLI, easy scripting, lower overhead.

Both work equally well with Istara. You can switch between them in Settings.

### My LLM is slow — how can I speed it up?
- Enable GPU layers in LM Studio (Settings > GPU) or Ollama (`OLLAMA_NUM_GPU=99`)
- Use a smaller or more aggressive quantization (e.g., Q4_K_M instead of Q8)
- Reduce the context window size in Settings if you don't need very long conversations
- Close other applications to free up RAM for the model

### Istara says "No models found" — what do I do?
1. Ensure your LLM provider is running (LM Studio local server or `ollama serve`)
2. Check your `.env` file: `LM_STUDIO_URL` should be `http://localhost:1234`, `OLLAMA_URL` should be `http://localhost:11434`
3. Verify the server is accessible by visiting the URL in your browser
4. Restart the Istara backend after fixing the `.env`

---

## Research Features

### What is the Atomic Research evidence chain?
Atomic Research is a methodology that makes research findings fully traceable. In Istara, every recommendation links back through insights → facts → nuggets (raw quotes/observations). This prevents hallucinated conclusions and makes your research auditable.

### Can Istara analyze audio recordings?
Istara works with text transcripts. For audio, use a transcription tool (Whisper, Otter.ai, etc.) to generate a transcript, then upload the transcript to Istara. The agent will handle the rest.

### How do the 53 skills work?
Skills are research method templates the AI agents follow. When you create a task (e.g., "Analyze P03 interview transcript using thematic analysis"), the agent selects the Thematic Analysis skill, follows its structured instructions, and produces tagged findings in the Atomic Research chain. Skills can also be triggered directly from the Chat view using natural language.

### Can I add my own skills?
Yes. Skills follow the OpenClaw AgentSkills standard. Create a directory under `skills/{phase}/your-skill-name/` with a `SKILL.md` file containing YAML frontmatter and instructions. Istara auto-discovers skills on startup.

### What is the Context Hierarchy?
The Context Hierarchy is a 6-level system that ensures agents have the right background knowledge before responding. You configure levels 1–4 (Company, Product, Project, Task) in the Context view. Higher levels override lower levels, so company-level guidance always applies unless overridden by project-level specifics.

### How does Kappa analysis work?
Istara's Kappa Thematic Analysis skill uses **Fleiss' Kappa** to measure inter-rater reliability when multiple models analyze the same data. It also supports multi-run analysis where the same model runs multiple times (Self-MoA). Confidence thresholds: Nuggets κ≥0.70, Facts κ≥0.65, Insights κ≥0.55, Recommendations κ≥0.50.

---

## Agents

### What are the 5 agents?
- **Cleo** (istara-main): Primary research coordinator — your main conversational agent
- **Sentinel** (istara-devops): System health and data integrity monitor
- **Pixel** (istara-ui-audit): UI heuristics and accessibility auditor
- **Sage** (istara-ux-eval): Holistic UX evaluation specialist
- **Echo** (istara-sim): End-to-end test runner and simulator

### Can I create my own agents?
Yes. Go to Agents > Create Agent. Give it a name, system prompt, and capabilities. Istara auto-generates all 4 persona files (CORE.md, SKILLS.md, PROTOCOLS.md, MEMORY.md) and adds the agent to the work loop.

### What is self-evolution?
Agents record their errors and patterns as "learnings." When a learning is applied successfully at least 3 times across 2+ projects over 30 days with ≥70% confidence, it becomes eligible for promotion into the agent's persona files (its permanent "memory"). You review and approve proposals in the Meta-Agent view.

### An agent is stuck in "WORKING" state — what do I do?
Go to Settings > Data Integrity to check for orphaned tasks. Then go to Agents, select the stuck agent, and click Stop, then Start. If the issue persists, check the backend terminal for error messages.

---

## Team and Collaboration

### Can multiple people use Istara at the same time?
Yes, in Team Mode. Enable Team Mode in Settings, which activates JWT authentication. Team members connect using a **connection string** that encodes the server URL and auth token.

### Who hosts the server in Team Mode?
One team member runs Istara on their machine (or a shared server/NAS) and shares the connection string with teammates. Istara is not a cloud service — the "server" is always a local machine on your network.

### Is there role-based access control?
Yes. Team Mode supports `admin` and `user` roles. Admins can manage settings, agents, and team members. Users have full access to research features.

---

## Privacy and Security

### Where is my data stored?
All data is stored locally:
- `data/istara.db` — SQLite database (all structured research data)
- `data/lance_db/` — LanceDB vector store (embeddings)
- `data/uploads/` — Uploaded files
- `backend/app/agents/personas/` — Agent persona files

### Can I export my data?
Yes. Go to Settings > Export to export all data as JSON. You can also create backups (Settings > Backup) that can be restored to any Istara installation.

### Is my data encrypted at rest?
Sensitive fields (API keys, tokens) are encrypted in the database. The main research data (findings, documents, transcripts) is stored in plaintext SQLite — encrypted disk volumes are recommended for sensitive research data.

### What is the MCP server?
The Model Context Protocol (MCP) server allows external AI agents and tools to query Istara's data. It is **OFF by default**. When enabled, you configure granular access policies per tool with full audit logging. This is an advanced feature for power users integrating Istara with Claude Desktop or other MCP clients.

---

## Troubleshooting Quick Reference

See the full [Troubleshooting](Troubleshooting) page for detailed solutions. Quick answers:

| Problem | Solution |
|---------|---------|
| "No models found" | Start LM Studio server or run `ollama serve` |
| Backend won't start | Check Python 3.11+, run `pip install -e ".[dev]"` |
| Frontend won't load | Check Node 18+, run `npm install` |
| Agent stuck in WORKING | Settings > Data Integrity, then restart agent |
| Slow responses | Enable GPU layers in LM Studio/Ollama, use Q4 quantization |
| Skills not showing | Restart backend, check SKILL.md YAML syntax |
| Can't upload files | Check `data/uploads/` directory exists and is writable |
