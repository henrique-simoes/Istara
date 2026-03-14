# 🧪 ReClaw User Simulation Report

**Persona:** Sarah, UX Researcher, found ReClaw on GitHub  
**Date:** 2026-03-14  
**Methodology:** Step-by-step walkthrough of actual files, checking every claim against reality  

---

## Step 1: Discovering ReClaw on GitHub

### First Impression (5-Second Test)

**What Sarah reads first:** "Local-first AI agent for UX Research" — ✅ immediately clear.

The tagline "Think OpenClaw meets Google NotebookLM meets Dovetail — but running on your hardware, your models, your data" is great for someone who knows those tools. For Sarah, a UX researcher? She definitely knows Dovetail. NotebookLM, probably. OpenClaw... maybe not. But the "running on your hardware" part sells the privacy angle clearly.

**Quick Start makes sense?** Yes — 5 commands, copy-paste friendly. The `mkdir -p data/...` step is slightly unusual (why can't Docker or the app create these?), but not a blocker.

**Docker knowledge:** Sarah probably doesn't know Docker deeply. The README says "Docker Desktop" with a link — that's enough. But "docker compose up" is not "one-command" if she needs to install Docker Desktop first (500MB+ download, account creation, restart). The README undersells this friction. A more honest framing: "After installing Docker Desktop, it's one command."

**Prerequisites clarity:** Good — "8GB RAM minimum (16GB recommended)" is helpful. Missing: disk space requirements (Docker images + Ollama models = 5-10GB easily), macOS version requirements, whether Apple Silicon is supported.

### README Rating: 7/10

**Strengths:** Clear value prop, beautiful feature table, good tech stack documentation, honest about what it is.

**Weaknesses:** Oversells "one-command" setup, no screenshots (the "UI Overview" section is a table of text descriptions, not images), no video/GIF demo. For a UX research tool, the README is ironically lacking in visual evidence of the product.

---

## Step 2: Following the Setup Guide

### Step-by-step evaluation:

#### Step 1 (Clone): ✅ Fine
Standard git clone. Works.

#### Step 2 (Configure Environment): ✅ Mostly fine
- `.env.example` exists ✅ 
- Defaults are sensible ✅ — `qwen3:latest`, reasonable RAG params
- "No API keys needed" is a great selling point ✅
- **Issue:** `.env.example` has `OLLAMA_HOST=http://ollama:11434` — this is the Docker internal hostname. If Sarah tries to run locally (not Docker), this won't work and the error will be opaque. Should note this.

#### Step 3 (Create Data Directories): ⚠️ Misleading
Sarah runs `mkdir -p data/watch data/uploads data/projects data/lance_db`. But looking at `docker-compose.yml`:

```yaml
volumes:
  - backend_data:/app/data        # ← Named Docker volume!
  - ${WATCH_DIR:-./data/watch}:/app/watch:ro  # ← Bind mount (only this one)
```

**BIG PROBLEM:** The backend uses a named Docker volume (`backend_data`) for `/app/data`. The directories Sarah created on the host (`data/uploads`, `data/projects`, `data/lance_db`) are **never used by Docker**. Only `data/watch` is actually bind-mounted.

This means:
- Sarah's uploaded research data lives inside a Docker volume, NOT in the visible `data/` folder
- If she does `docker compose down -v`, her data is **gone**
- She can't browse her files in Finder/Explorer
- The setup guide creates a false expectation of where data lives

**Fix:** Either use bind mounts for all data dirs, or don't ask users to create directories that Docker ignores.

#### Step 4 (Start ReClaw): ⚠️ Will fail on first build
`docker compose up` — this references `./backend/Dockerfile` and `./frontend/Dockerfile`. Both exist ✅.

**Potential Mac issues with docker-compose.yml:**
- Ollama healthcheck uses `curl` — the Ollama Docker image may not have curl installed. This could cause the healthcheck to always fail, meaning the backend (which `depends_on` ollama healthy) would never start. This is a common Docker footgun.
- No platform specified — on Apple Silicon Macs, some images may default to arm64 which is correct for `ollama/ollama:latest`, but worth noting.

#### Step 5 (Download a Model): ⚠️ Ordering problem
The guide says to pull a model AFTER `docker compose up`. But the backend already started and the frontend is already showing. If Sarah opens localhost:3000 before the model is pulled, she'll see... what? The OllamaCheck screen says "Ollama Not Connected" — but Ollama IS connected, it just has no model. The health check hits `/api/tags` which returns 200 even with no models. So she'd get past the Ollama check but then the first chat message would fail.

**The model pull should happen BEFORE or AS PART OF docker compose up.** Or the onboarding should check for models and guide through pulling.

#### Step 6 (Open ReClaw): ✅ Clear

#### Step 7 (Start Researching): ✅ Good
The command table is helpful. Natural language triggers map well.

### `scripts/install.sh` Review: 🐛 Has bugs

1. **Wrong git URL (line ~48):** `git clone https://github.com/your-org/reclaw.git` — placeholder URL was never updated. Should be `https://github.com/henrique-simoes/ReClaw.git`. **This is a ship-blocker.** Anyone running the install script gets a clone failure.

2. **Good practices:** Checks for Docker, checks for docker-compose vs. docker compose, creates .env from template. The error messages are helpful.

3. **Missing:** No model pull step. After `docker compose up -d`, the user has a running system with NO model. First chat will fail.

### Frontend `package.json`: ✅ Clean
- All major deps present (Next.js 14, React 18, Radix UI, Zustand, dnd-kit, Tailwind)
- No obvious missing deps for the components I reviewed
- Versions look reasonable and compatible

### Backend `requirements.txt`: ✅ Solid
- FastAPI, SQLAlchemy async, LanceDB, file parsing (pypdf, python-docx), hardware monitoring (psutil)
- No pinned versions with `==` (uses `>=`) — good for flexibility, slight risk of breaking changes
- `python-magic` requires `libmagic` system library — needs to be in the Dockerfile. If missing, file type detection fails silently or crashes.

---

## Step 3: First Run Experience

### Opening localhost:3000

Sarah's journey:

1. **First gate: OllamaCheck** — The app checks `settingsApi.status()` and looks for `services.ollama === "connected"`. If Ollama container is healthy (healthcheck passes), she gets past this. If not, she sees a full-screen warning with install instructions... but she's using Docker, so the instructions (`curl -fsSL https://ollama.com/install.sh | sh`) are WRONG for her context. The small note "If using Docker, Ollama starts automatically via docker-compose" at the bottom is too subtle.

2. **Second gate: Onboarding** — If no projects exist (first run), `showOnboarding` becomes true. She sees the OnboardingWizard as a modal overlay.

### Onboarding Wizard Walkthrough

**Step 0 — Welcome:** ✅ Great
- Clear, friendly, shows 3-step preview (Create project → Upload research → Get insights)
- "Your data never leaves your machine" — good trust signal
- Single CTA: "Get Started" — clean

**Step 1 — Create Project:** ✅ Good
- Input with placeholder "e.g., Onboarding Redesign Study" — helpful
- Enter key works to submit ✅
- Button disabled until text entered ✅
- Sarah types: "User Onboarding Study Q1 2026"
- **Minor issue:** No validation feedback. What if the API call to create the project fails? No error state shown. She'd be stuck.

**Step 2 — Set Context:** ✅ Very Good
- Both fields optional with "Skip for Now" option — low pressure
- Placeholders are excellent examples
- Sarah fills in: Company = "B2B SaaS for project management", Research Goals = "Understand why users drop off during onboarding"
- **Nice touch:** Button text changes from "Skip for Now" to "Save & Continue" when she types something

**Step 3 — Upload:** ✅ Good
- File upload with accepted types clearly shown (PDF, DOCX, TXT, CSV, MD)
- Upload feedback shows checkmarks with filenames
- "Skip & Explore" option available
- **Issue:** No drag-and-drop on the upload area in the wizard. The main ChatView has drag-and-drop, but the onboarding wizard's upload button only supports click-to-browse. Inconsistent.
- **Issue:** No file size limit shown. What if Sarah drops a 500MB video transcript?
- **Issue:** No progress indicator during upload — just "Uploading..." text. For large files this would look frozen.

**After onboarding:** She lands on the main app with ChatView active. The sidebar shows her project. She sees "🐾 Ready to research!" empty state.

### Overall Onboarding UX: Solid B+
Clean, focused, optional fields, good copywriting. Missing: error handling, drag-drop in upload, progress indicators.

---

## Step 4: First Research Task

### Sarah's scenario: 3 interview transcripts about onboarding

**Path: Upload → Analyze → View Findings → Drill Down**

#### Upload (via Chat or Interviews view)

**Option A: Chat drag-and-drop** 
- She drags `interview-participant-1.txt` onto the chat area
- The file gets uploaded via `filesApi.upload()`
- An automatic message is sent: `I just uploaded "interview-participant-1.txt" (47 chunks indexed). Can you analyze it?`
- This triggers the chat flow, which detects "analyze" + "interview" + "transcript" → maps to `user-interviews` skill

**This is actually pretty slick!** The upload-then-auto-analyze flow is well designed.

**Option B: Interviews view**
- She clicks "Upload" button, selects files
- Files appear as tabs
- She clicks a file tab → sees placeholder text: `[Loading transcript: filename]` with instructions
- She clicks "Analyze" button → triggers chat API with skill detection
- Streaming results appear inline

**Issue with Interviews view:** `handleFileSelect` doesn't actually load the file content! It shows a hardcoded placeholder:
```tsx
setTranscriptText(`[Loading transcript: ${filename}]\n\nTo analyze this file, click "Analyze" below...`);
```
There's no file content API being called. Sarah would see the placeholder, not her actual transcript text. **This is a significant gap** — the transcript viewer doesn't actually display transcripts.

#### Analyze

The skill detection in `chat.py` works well:
- "analyze the interview transcripts" → matches "interview" and "transcript" → triggers `user-interviews` skill
- The `_detect_skill_intent()` function is comprehensive with 50+ phrase mappings
- Skill execution returns structured output (nuggets, facts, insights, recommendations)

**What could go wrong:**
- If Ollama has no model pulled, `agent.execute_skill()` will fail and the error bubbles up as an SSE error event. The UI shows `⚠️ {error}` but doesn't tell Sarah what to do about it.
- If the skill takes a long time (likely for 3 transcripts), there's no progress indication — just "Thinking..." with a spinner.

#### View Findings

After analysis, Sarah switches to FindingsView:
- Sees Double Diamond phase tabs (Discover/Define/Develop/Deliver) — ✅ good mental model for a UX researcher
- Summary stats show counts of Nuggets, Facts, Insights, Recommendations — ✅ 
- Can expand sections and click findings for drill-down — ✅
- **Atomic Research chain** (Recommendation → Insight → Fact → Nugget → Source) via `AtomicDrilldown` — this is the killer feature

**Issue:** Findings are filtered by phase, but after initial interview analysis, everything likely goes to "Discover." Sarah would need to understand the Double Diamond mapping to find her data. If she clicks "Define" and sees nothing, she might think the analysis failed.

#### Drill Down

Clicking a finding opens `AtomicDrilldown` — traces evidence chain back to source. 

**What works well:**
- Click an insight → see the facts that support it → see the nuggets → see the source file and location
- Confidence scores and source attribution
- Tag-based filtering in the Interviews sidebar

**What's confusing:**
- The relationship between Chat analysis results and Findings view isn't obvious. Sarah analyzes in Chat, but results appear in a different view. No notification or redirect says "Hey, 5 new insights were added to Findings."
- Quick Actions in Interview sidebar ("Run thematic analysis on nuggets", "Generate affinity map") fire chat API calls but the results stream into the Interview view's analysis panel, not into Chat or Findings. The data flow is unclear.

### ChatView.tsx Syntax Bug 🐛

**Line 175 has a JSX syntax error:**
```tsx
        )

        {streaming && streamingContent && (
```

The closing `)` on line 175 is missing the `}` to complete the JSX expression. It should be `)}`. **This would cause a build failure** — the frontend would not compile. This is a **ship-blocker**.

---

## Step 5: Grades

### 1. README Clarity — **B** (7/10)

Clear value prop, good feature list, honest tech stack. Missing screenshots, oversells "one-command" setup, no mention of disk space or Apple Silicon.

**Fix:** Add 2-3 screenshots/GIFs of the actual UI. Add disk space requirement (≥10GB free). Reframe Quick Start as "5-command setup" or add `scripts/install.sh` as the true one-command option (once fixed).

### 2. Setup Guide Accuracy — **C-** (4/10)

Several commands don't match reality:
- `mkdir -p data/...` creates directories Docker ignores
- No model pull in the main flow
- Install script has wrong git URL
- Ollama healthcheck may fail if curl isn't in the image

**Fix:** Fix the data volume mismatch (use bind mounts), add model pull to docker-compose via entrypoint, fix install.sh URL, verify healthcheck works.

### 3. Onboarding Wizard UX — **B+** (8/10)

Clean, friendly, low-pressure. Good copywriting and progressive disclosure.

**Fix:** Add error handling for failed API calls, add drag-drop to upload step, add file size limits/progress.

### 4. First-Task Completion — **C+** (5/10)

The chat-to-skill flow is clever but the Interviews view has a non-functional transcript viewer. Evidence chain drill-down is impressive when it works. Data flow between views is confusing.

**Fix:** Implement actual file content loading in InterviewView, add cross-view notifications ("3 new insights added"), add a "View Findings" CTA after skill execution in chat.

### 5. Error Handling — **D** (3/10)

- No model → opaque failure
- Ollama check shows wrong instructions for Docker users
- No error states in onboarding wizard
- `ChatView.tsx` has a syntax error that prevents building
- Upload failures show console.error, not user-facing messages

**Fix:** Add model availability check to onboarding, contextualize OllamaCheck for Docker vs. native, add error boundaries and user-facing error messages throughout.

### 6. Overall "Time to First Insight" — **C** (5/10)

**Realistic timeline for Sarah:**
1. Install Docker Desktop: 10-20 min (download, install, restart, create account)
2. Clone + setup: 2 min
3. Docker build: 3-5 min (first run)
4. Discover she needs to pull a model: 5-10 min of confusion
5. Pull model: 5-10 min (download)
6. Complete onboarding: 2 min
7. Upload + analyze: 3-5 min
8. Find results in Findings view: 2-3 min of clicking around

**Total: 30-50 minutes to first insight.** For a tool competing with "paste into ChatGPT" (30 seconds), this needs to be faster. The model pull is the biggest bottleneck and should be automated.

---

## 🚨 Sarah's Showstoppers

Things that would make Sarah close the tab and never come back:

1. **`ChatView.tsx` syntax error (line 175)** — Frontend won't build. Docker compose fails. Sarah sees a build error in logs and has no idea what to do. **Game over.**

2. **`scripts/install.sh` wrong git URL** — `git clone https://github.com/your-org/reclaw.git` fails instantly. If she found the install script first, her very first interaction with ReClaw is a failure. **Game over.**

3. **No model after setup** — She completes all setup steps, opens the app, types her first message... and gets an error. The setup guide mentions model pulling as Step 5 but it's easy to miss, and the app gives no guidance. **Likely to give up.**

4. **Data in Docker volume, not visible on host** — Sarah creates `data/` directories, puts files in `data/watch`, expects to find her research in `data/uploads`. It's not there. Her data feels "lost." **Trust broken.**

---

## ✨ Sarah's Delights

Things that would make Sarah tweet about ReClaw:

1. **Privacy-first positioning** — "Your data never leaves your machine" is a perfect pitch for UX researchers who handle sensitive user data. Dovetail/UserTesting require cloud uploads. This is a genuine differentiator.

2. **45 UXR skills with Double Diamond organization** — Sarah immediately recognizes the framework. The skill list reads like her toolkit. She feels this was built BY a UX researcher, FOR UX researchers.

3. **Atomic Research evidence chain** — Recommendation → Insight → Fact → Nugget → Source. This is research rigor built into the tool. No other AI tool does this. Click any insight and see exactly where it came from. **This is the killer feature.**

4. **Natural language skill triggering** — She types "create personas from the interviews" and it just works. No menu diving, no mode switching. The intent detection map in `chat.py` is extensive and covers how researchers actually talk.

5. **Onboarding wizard tone** — Friendly, non-intimidating, doesn't require commitment upfront. "Skip for Now" on every optional step. This respects her time.

6. **Drag-and-drop file upload in Chat** — Drop a file, it gets indexed and analyzed in one flow. That's magical.

7. **Keyboard shortcuts (⌘K search, ⌘1-5 view switching)** — Power-user features from day one. Shows maturity.

---

## 🔧 Exact Fixes Needed

### Ship-Blockers (Must fix before any release)

| # | File | Line | Issue | Fix |
|---|------|------|-------|-----|
| 1 | `frontend/src/components/chat/ChatView.tsx` | 175 | Missing `}` in JSX — syntax error prevents build | Change `)` to `)}` |
| 2 | `scripts/install.sh` | ~48 | Wrong git URL: `your-org/reclaw.git` | Change to `henrique-simoes/ReClaw.git` |
| 3 | `docker-compose.yml` | 27 | Named volume `backend_data:/app/data` hides data from host | Change to bind mount: `./data:/app/data` |

### High Priority (Should fix before beta)

| # | File | Line | Issue | Fix |
|---|------|------|-------|-----|
| 4 | `docker-compose.yml` | ollama service | Healthcheck uses `curl` which may not exist in Ollama image | Use `wget -q --spider` or test with `ollama list` |
| 5 | `docker-compose.yml` | — | No automatic model pull | Add entrypoint script that pulls `${OLLAMA_MODEL}` on first run |
| 6 | `frontend/src/components/interviews/InterviewView.tsx` | `handleFileSelect` | Transcript content never loaded — shows placeholder | Add file content API endpoint; call it in `handleFileSelect` |
| 7 | `frontend/src/components/common/OllamaCheck.tsx` | — | Shows native install instructions to Docker users | Detect Docker context; show `docker logs reclaw-ollama` and `docker restart reclaw-ollama` instead |
| 8 | `docs/SETUP-GUIDE.md` | Step 3 | Tells users to create dirs that Docker ignores | Remove step or align with actual volume mounts |
| 9 | `frontend/src/components/onboarding/OnboardingWizard.tsx` | `handleCreateProject` | No error handling — failed API call leaves wizard stuck | Add try/catch, show error toast, allow retry |

### Medium Priority (Should fix before v1.0)

| # | File | Line | Issue | Fix |
|---|------|------|-------|-----|
| 10 | `README.md` | Quick Start | No disk space requirement mentioned | Add "10GB free disk space" to prerequisites |
| 11 | `README.md` | UI Overview | No screenshots — just text descriptions | Add 3-4 screenshots or a 30-second GIF |
| 12 | `frontend/src/components/chat/ChatView.tsx` | — | After skill execution, no CTA to view findings | Add "View N new findings →" button after skill completes |
| 13 | `frontend/src/components/onboarding/OnboardingWizard.tsx` | Step 3 | No drag-and-drop on upload area | Add `onDrop` handler matching ChatView pattern |
| 14 | `frontend/src/components/onboarding/OnboardingWizard.tsx` | Step 3 | No upload progress indicator | Add progress bar per file |
| 15 | `backend/app/api/routes/chat.py` | `_detect_skill_intent` | "analyze my interviews" doesn't match (needs "interview" singular or "transcript") | Add "interviews" (plural) to intent map |

---

## Summary Verdict

**ReClaw is NOT ready to ship.**

The concept is excellent — possibly the best-positioned AI research tool I've seen for the privacy-conscious UX researcher market. The Atomic Research chain, the 45 skills, the natural language triggers — these are genuine innovations.

But **two syntax/config bugs prevent it from even running** (ChatView.tsx build failure, install.sh wrong URL), and the data volume mismatch means users' research data is silently stored in a Docker volume they can't see or easily back up.

**Minimum to ship a beta:**
1. Fix the 3 ship-blockers (30 minutes of work)
2. Add automatic model pull (1-2 hours)
3. Fix the transcript viewer to actually show content (2-3 hours)
4. Add error handling to onboarding (1-2 hours)

**Time estimate to beta-ready: 1 day of focused work.**

The bones are great. The flesh needs patching. Fix the showstoppers, and Sarah would not only use ReClaw — she'd evangelize it.
