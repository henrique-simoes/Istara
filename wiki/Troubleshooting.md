# Troubleshooting

Common issues and their solutions. If you don't find your issue here, please [open a GitHub issue](https://github.com/henrique-simoes/Istara/issues).

---

## Installation Issues

### Backend fails to install dependencies

**Symptom**: `pip install -e ".[dev]"` fails with errors.

**Solutions**:
1. Verify Python version: `python --version` — must be 3.11 or higher
2. Upgrade pip: `pip install --upgrade pip`
3. On macOS, if you have multiple Python versions: use `python3.11 -m pip install -e ".[dev]"`
4. If you see compiler errors for native extensions, install system build tools:
   - macOS: `xcode-select --install`
   - Ubuntu: `sudo apt-get install build-essential python3-dev`
   - Windows: Install Visual Studio Build Tools

### Frontend fails to install dependencies

**Symptom**: `npm install` fails.

**Solutions**:
1. Verify Node version: `node --version` — must be 18 or higher
2. Clear npm cache: `npm cache clean --force`
3. Delete `node_modules` and `package-lock.json`, then retry: `rm -rf node_modules package-lock.json && npm install`

### Port already in use

**Symptom**: Backend or frontend fails to start with "address already in use."

**Solutions**:
```bash
# Find what's using port 8000 (backend)
lsof -i :8000
# Kill it (replace PID with actual process ID)
kill -9 <PID>

# Or start on a different port
python -m uvicorn app.main:app --port 8001 --app-dir backend
# Then set NEXT_PUBLIC_API_URL=http://localhost:8001 in frontend/.env.local
```

---

## LLM Provider Issues

### "No models found" or LLM connection errors

**Symptom**: The Chat view shows an error, or Settings shows no models.

**Checklist**:
1. Is LM Studio's local server running? Open LM Studio, go to the Local Server tab, verify it shows "Running" and port 1234.
2. Is Ollama running? Run `ollama list` — if it fails, run `ollama serve` in a terminal.
3. Check `.env` settings:
   ```env
   LLM_PROVIDER=lmstudio
   LM_STUDIO_URL=http://localhost:1234
   # OR
   LLM_PROVIDER=ollama
   OLLAMA_URL=http://localhost:11434
   ```
4. Test connectivity manually: `curl http://localhost:1234/v1/models` (LM Studio) or `curl http://localhost:11434/api/tags` (Ollama)
5. Restart the Istara backend after fixing `.env`

### LLM responses are very slow

**Solutions**:
1. **Enable GPU acceleration**: In LM Studio, go to Settings and increase GPU Layers to maximum. For Ollama: `OLLAMA_NUM_GPU=99 ollama serve`
2. **Use lower quantization**: Switch from Q8 to Q4_K_M for 2x speed improvement (minor quality trade-off)
3. **Use a smaller model**: A fast 7B model often produces better research outputs than a slow 13B model
4. **Close other applications**: Free up RAM and GPU VRAM for the LLM
5. **Reduce context window**: Lower `MAX_CONTEXT_TOKENS` in Settings to reduce prompt processing time

### LLM produces garbled or nonsensical output

**Solutions**:
1. The model may be overloaded — reduce concurrent agent count in Settings
2. Try a different model (some models handle research tasks better than others)
3. Check that the model you're using is instruction-tuned (not a base model)
4. Restart LM Studio or Ollama to clear any corrupted state

---

## Backend Issues

### Backend starts but immediately crashes

**Symptom**: Uvicorn starts but exits with an error.

**Common causes and fixes**:
```bash
# See the full error
cd backend
python -m uvicorn app.main:app --port 8000 --log-level debug

# Database corruption
# If you see SQLAlchemy or SQLite errors:
mv data/istara.db data/istara.db.bak  # Rename (backup) the database
# Restart backend — it will create a fresh database
```

### "AttributeError" or "ImportError" on startup

**Solution**: Reinstall dependencies — the package may be partially installed:
```bash
cd backend
pip install -e ".[dev]" --force-reinstall
```

### Skills are not showing up in the UI

**Solutions**:
1. Skills are auto-discovered on startup. Restart the backend after adding new skill files.
2. Check SKILL.md frontmatter for YAML syntax errors — a single invalid character will prevent the skill from loading
3. Verify the skill directory is under `skills/{phase}/skill-name/` — the phase must be `discover`, `define`, `develop`, or `deliver`
4. Check backend logs for "Error loading skill" messages

### Data integrity errors

**Symptom**: Settings > Data Integrity reports errors.

**Solutions**:
1. Run the data integrity check: `POST /api/settings/data-integrity`
2. For orphaned tasks (tasks with no project): use Settings > Export to back up your data, then delete orphaned records via the API
3. For orphaned findings: these are usually safe to delete (they have no project context)
4. Contact the community for guidance before taking destructive action

---

## Frontend Issues

### Frontend loads but shows blank screen

**Solutions**:
1. Open browser DevTools (F12), check the Console tab for errors
2. Verify the backend is running: visit `http://localhost:8000/api/health`
3. Check `frontend/.env.local` — ensure `NEXT_PUBLIC_API_URL=http://localhost:8000`
4. Hard refresh the browser: `Cmd+Shift+R` (macOS) or `Ctrl+Shift+R` (Windows)

### "Failed to fetch" errors in the UI

**Solution**: The frontend can't reach the backend.
1. Verify the backend is running on port 8000
2. Check for CORS errors in the browser console — the backend must be configured to allow `http://localhost:3000`
3. In Docker, ensure the containers are on the same network

### Chat messages don't stream (appear all at once)

**Solution**: Streaming is handled via SSE (Server-Sent Events). If your browser or network proxy is buffering responses:
1. Disable proxy settings for localhost
2. Try a different browser
3. Check that `STREAM_RESPONSES=true` in `.env`

---

## Agent Issues

### Agent is stuck in "WORKING" state

**Solutions**:
1. Go to Settings > Data Integrity — this detects and can clean up orphaned tasks
2. Go to Agents view, select the stuck agent, click **Stop**, then **Start**
3. Check the backend terminal for error messages from the agent worker
4. If the agent is stuck on a specific task, go to Tasks and move that task to "Backlog" to release it

### Agent doesn't pick up tasks

**Solutions**:
1. Verify the agent is in "IDLE" state (not PAUSED or STOPPED) in the Agents view
2. Check the Resource Governor — if RAM is >90%, agents are automatically paused. Free up memory.
3. Verify the task is assigned to the right agent (or is unassigned, which any agent can pick up)
4. Check the task priority — Critical and High priority tasks are picked up first

### Self-evolution proposals don't appear

**Solutions**:
1. Proposals appear in Meta-Agent > Proposals once learnings reach promotion thresholds (3+ occurrences, 2+ projects, 30 days)
2. New installations won't have proposals until the agents have enough operational history
3. Check that `self_evolution_enabled=true` in Settings

---

## File Upload Issues

### Files fail to upload

**Solutions**:
1. Check that the `data/uploads/` directory exists and is writable: `ls -la data/`
2. Verify the file format is supported: `.txt`, `.md`, `.pdf`, `.docx`, `.csv`, `.json`
3. For large files (>50 MB), uploading may take time — wait for the "file processed" toast notification
4. Check the backend logs for error messages from the file watcher

### Uploaded files don't appear in Documents view

**Solutions**:
1. The file is processed asynchronously. Wait for the "file processed" toast notification.
2. Ensure the file was uploaded to the correct project
3. Restart the backend if the file watcher seems stuck

### External folder linking not working

**Solutions**:
1. Verify the folder path in Project Settings is correct and accessible
2. The folder must be readable by the Istara backend process
3. On macOS, grant Full Disk Access to Terminal (or the desktop app) in System Settings > Privacy & Security
4. Check the backend logs for file watcher errors

---

## Database Issues

### "Database is locked" errors

**Solutions**:
1. Ensure only one Istara backend instance is running
2. If you have multiple terminals open, kill all backend processes: `pkill -f uvicorn`
3. SQLite WAL mode should prevent most locking issues — verify it's enabled (it is by default)

### Resetting the database (last resort)

WARNING: This deletes ALL research data. Always create a backup first.

```bash
# Create a backup via the API
curl -X POST http://localhost:8000/api/backups -H "Authorization: Bearer <token>"

# Stop the backend, then:
mv data/istara.db data/istara.db.bak
# Remove vector store
mv data/lance_db data/lance_db.bak
# Restart backend — fresh database will be created
```

---

## Docker Issues

### Docker containers fail to start

**Solutions**:
1. Ensure Docker Desktop is running
2. Check that required ports (3000, 8000) are not occupied
3. Verify environment variables are set in `.env`: `cp .env.example .env`
4. Ensure data directories exist: `mkdir -p data/watch data/uploads data/projects data/lance_db`

### LLM provider not reachable from Docker

**Solution**: When running in Docker, localhost refers to the container, not the host machine. Use your machine's local network IP:
```env
# Instead of:
LM_STUDIO_URL=http://localhost:1234
# Use:
LM_STUDIO_URL=http://host.docker.internal:1234  # macOS/Windows
# Or on Linux:
LM_STUDIO_URL=http://172.17.0.1:1234  # Docker bridge IP
```

---

## Desktop Tray App Issues

### Tray icon shows wrong Start/Stop state

The menu label reflects actual port state (8000/3000). If the label is wrong:
1. Wait 10 seconds for the health loop to refresh
2. If persistent, check `~/.istara/config.json` has a valid `install_dir` pointing to your installation
3. Verify `istara.sh` exists in your install directory: `ls ~/.istara/istara.sh`

### Compute Donation shows Off when On

The tray reads `donate_compute` from `~/.istara/config.json` every time the menu is rebuilt. Check the config file:
```bash
cat ~/.istara/config.json | python3 -c "import sys,json; print(json.load(sys.stdin).get('donate_compute'))"
```

### Check for Updates shows nothing

The tray uses a three-tier approach: Tauri updater (DMG installs), git tags, GitHub releases. Ensure git is available:
```bash
which git
cd ~/.istara && git fetch --tags
```

### Backend fails to start via tray

The tray delegates to `istara.sh`. Check the CLI directly:
```bash
cd ~/.istara && ./istara.sh start
```
If it fails, check `~/.istara/.istara-backend.log` for errors. Common cause: `NEXT_PUBLIC_*` vars in `backend/.env` crash pydantic.

---

## Getting More Help

If none of the above resolves your issue:

1. Check backend logs: the terminal running `uvicorn` contains detailed error messages
2. Check frontend logs: browser DevTools > Console
3. Search existing GitHub issues: https://github.com/henrique-simoes/Istara/issues
4. Open a new issue with:
   - Istara version (Settings > About)
   - OS and hardware
   - LLM provider and model
   - Full error message from terminal or browser console
   - Steps to reproduce the issue
