# Getting Started with Istara

This guide walks you through installing Istara and running it for the first time.

---

## System Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| RAM | 8 GB | 16 GB+ |
| OS | macOS 12+, Windows 10+, Ubuntu 20.04+ | macOS 14+ / Windows 11 |
| Python | 3.11+ | 3.12 |
| Node.js | 18+ | 20 LTS |
| Disk | 10 GB free | 20 GB+ free |

---

## Step 1: Install a Local LLM Provider

Istara uses **LM Studio** (recommended) or **Ollama** for local inference.

### Option A: LM Studio (Recommended)
1. Download LM Studio from https://lmstudio.ai
2. Open LM Studio and download a model:
   - 8 GB RAM: `Qwen2.5-3B-Instruct` (Q4_K_M)
   - 16 GB RAM: `Qwen2.5-7B-Instruct` (Q4_K_M) or `Llama-3.1-8B-Instruct`
   - 32 GB RAM: `Qwen2.5-14B-Instruct` or `Mistral-7B-Instruct` (Q8)
3. Start the local server: go to **Local Server** tab and click **Start Server**

### Option B: Ollama
1. Download Ollama from https://ollama.ai
2. Install and run:
   ```bash
   ollama serve
   ollama pull qwen3:latest
   ```

---

## Step 2: Install Istara

### Option A: Desktop App (Easiest)

Download the installer from the [Releases page](https://github.com/henrique-simoes/Istara/releases):
- **macOS**: Download the `.dmg` file, open it, drag Istara to Applications
- **Windows**: Download the `.exe` installer, run it, follow the setup wizard

The desktop app includes a first-run setup wizard that guides you through configuration.

### Option B: From Source

```bash
# Clone the repository
git clone https://github.com/henrique-simoes/Istara.git
cd Istara

# Install backend dependencies
cd backend && pip install -e ".[dev]" && cd ..

# Install frontend dependencies
cd frontend && npm install && cd ..

# Copy environment config
cp .env.example .env
```

### Option C: Docker

```bash
cp .env.example .env
mkdir -p data/watch data/uploads data/projects data/lance_db
docker compose up
```

---

## Step 3: Configure Your Environment

Edit the `.env` file in the project root:

```env
# LLM Provider — choose one
LLM_PROVIDER=lmstudio       # or: ollama

# LM Studio settings (if using LM Studio)
LM_STUDIO_URL=http://localhost:1234

# Ollama settings (if using Ollama)
OLLAMA_URL=http://localhost:11434
```

---

## Step 4: Start Istara

### From Source
```bash
# In terminal 1 — start the backend
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# In terminal 2 — start the frontend
cd frontend
npm run dev
```

Then open **http://localhost:3000** in your browser.

### Convenience Script
From the project root:
```bash
./istara.sh
```

---

## Step 5: First-Time Setup

When you open Istara for the first time:

1. **Create a Project** — click "New Project" and give it a name
2. **Configure Context** — visit the Context view to set your company, product, and research goals
3. **Try a Skill** — in the Chat view, type "help me create an interview guide" to see skills in action
4. **Add Research Data** — upload transcripts, notes, or survey data via the Documents view

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Cmd+K` | Global search across all findings |
| `Cmd+1` – `Cmd+6` | Switch between primary views |
| `Cmd+.` | Toggle right panel |
| `?` | Show all keyboard shortcuts |
| `Esc` | Close modal / cancel action |
| `Enter` | Send message / confirm |

---

## Hardware Tips

Istara's **Resource Governor** automatically prevents the LLM from overwhelming your machine. It monitors CPU and RAM usage and pauses background agents if resources are critical (>90% RAM used). You can always keep using the chat while background tasks pause.

**GPU acceleration**: Both LM Studio and Ollama support GPU inference on supported hardware (Apple Silicon MPS, NVIDIA CUDA, AMD ROCm). Enable GPU layers in your LLM provider settings for significantly faster inference.

---

## Next Steps

- Read the [Features](Features) page for a complete overview of what Istara can do
- Read [Agent System](Agent-System) to understand how the AI agents work
- Check [Troubleshooting](Troubleshooting) if you run into issues
