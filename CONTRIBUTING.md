# Contributing to Istara

Thank you for your interest in contributing to Istara! 🐾

## Quick Start

```bash
git clone https://github.com/henrique-simoes/Istara.git
cd Istara

# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install && npm run dev
```

## Project Structure

- `backend/` — Python FastAPI backend
- `frontend/` — Next.js React frontend
- `skills/` — UXR skill definitions (SKILL.md + references + scripts)
- `scripts/` — Utility scripts
- `docs/` — Documentation

## Branching & Pull Requests

Istara uses a **staging-first** workflow:

```
feature branch → PR → staging → PR → main
```

- **`main`** — production. Protected — CI must pass, PR required.
- **`staging`** — integration. All feature work lands here first. Auto-synced to `main` after merges.
- **Feature branches** — `feat/`, `fix/`, `docs/` prefixes. Created from `staging`.

### ⚠️ Stale Branch Notice (2026-04-28)

Multiple legacy branches exist locally (e.g., `feat/voice-transcription`, `review/p*`, `fix-ci-validation`) but are **significantly behind `main` (46–124 commits)** and must not be merged wholesale. See `planner.md` "Deprecated Branches" for the full list. Treat them as historical artifacts only — salvage by cherry-pick or create fresh branches from `staging` if any work is still needed.

### For multi-commit work (3+ commits):
```bash
git checkout staging && git pull
git checkout -b feat/my-feature
# ... work, commit ...
git push origin feat/my-feature
gh pr create --base staging --title "feat: my feature"
```

### For trivial changes (typos, version bumps):
```bash
git checkout staging && git pull
# ... change, commit, push directly to staging ...
```

### Testing Before Merge
See [TESTING.md](TESTING.md) for the review queue, recently integrated mainline work, and branch testing instructions.

## Code Style

- **Python:** Ruff for linting/formatting, type hints everywhere, async/await
- **TypeScript:** ESLint + Prettier, strict mode, no `any` where avoidable
- **Commits:** Conventional commits (`feat:`, `fix:`, `docs:`, `refactor:`)
- **Tests:** Run `pytest tests/` — all tests must pass. New features need test coverage.
- **Compass:** Run `python scripts/update_agent_md.py` and `python scripts/check_integrity.py` after architecture changes.

## Release Prep

Release-worthy pushes to `main` publish the installer/release workflow for the repository.

Release-worthy means:
- backend/frontend/desktop/relay behavior changed
- install/update/version/release behavior changed
- Compass-critical internal agent docs or persona knowledge changed in a way Istara's internal agents rely on

When preparing a release locally, use:

```bash
./scripts/prepare-release.sh --bump
```

That syncs generated docs, runs integrity checks, and bumps the version before you push.

## Adding a Skill

1. Create `skills/{phase}/{skill-name}/SKILL.md` with YAML frontmatter
2. Add JSON definition in `backend/app/skills/definitions/{skill-name}.json`
3. For complex skills, add Python implementation in `backend/app/skills/{phase}/`
4. Register in `backend/app/skills/registry.py`

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
