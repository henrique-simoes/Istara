# ReClaw — Claude Code Development Guide

For full system understanding, see [AGENT.md](AGENT.md).

## MANDATORY: System Integrity Guide

**Before making ANY change, consult these files:**
- [SYSTEM_INTEGRITY_GUIDE.md](SYSTEM_INTEGRITY_GUIDE.md) — Complete reference: all models, routes, flows, dependencies
- [CHANGE_CHECKLIST.md](CHANGE_CHECKLIST.md) — Step-by-step checklist for every type of change
- [INTEGRITY_INDEX.md](INTEGRITY_INDEX.md) — Quick navigation to find what you need

**After EVERY change:**
1. Verify impact using the Change Impact Matrix in SYSTEM_INTEGRITY_GUIDE.md
2. Update SYSTEM_INTEGRITY_GUIDE.md if you added models, routes, skills, types, or integrations
3. Run `python scripts/update_agent_md.py` to update AGENT.md
4. Run `python -m pytest tests/test_research_integrity.py` for backend verification
5. Update Tech.md if the change affects architecture

## Quick Start

```bash
# Backend (Python 3.11+)
cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend (Node 18+)
cd frontend && npm run dev

# LM Studio
lms server start
```

## Development Patterns

### Adding a New Feature
1. Model: `backend/app/models/{feature}.py` — SQLAlchemy model with `to_dict()`
2. Register model in `backend/app/models/database.py` init_db()
3. Service: `backend/app/services/{feature}_service.py` — async functions
4. Route: `backend/app/api/routes/{feature}.py` — FastAPI APIRouter
5. Register route in `backend/app/main.py`
6. Types: append to `frontend/src/lib/types.ts`
7. API client: append namespace to `frontend/src/lib/api.ts`
8. Store: `frontend/src/stores/{feature}Store.ts` — Zustand
9. Components: `frontend/src/components/{feature}/`
10. Nav: add to `Sidebar.tsx` primaryNav/secondaryNav + `HomeClient.tsx` renderView switch
11. **Run `python scripts/update_agent_md.py`** to update AGENT.md capabilities

### Code Style
- Backend: Python 3.11+, async/await, type hints, SQLAlchemy 2.0 mapped_column
- Frontend: TypeScript, "use client" on all components, Tailwind CSS, `cn()` for conditional classes
- Colors: `reclaw-{50-900}` scale, dark mode via class toggle
- Accessibility: `aria-label` on icon buttons, `role="tab"/"tablist"`, FocusTrap in modals

### Testing
- Simulation scenarios: `tests/simulation/scenarios/{id}-{name}.mjs`
- Each exports `name`, `id`, `async run(ctx)` where ctx has `api`, `page`, `report`
- Run: `node tests/simulation/run.mjs`

### Git Rules
- Never commit: `.env`, `data/`, `*.db`, UUID agent persona dirs, skill evolution stats
- Always tracked: source code, skill definitions, system agent personas, docs, tests
- Run tests before committing integration changes

### WebSocket Events
When adding real-time features, add broadcast functions to `backend/app/api/websocket.py` following the existing pattern: `async def broadcast_{event}(...) -> None: await manager.broadcast("{type}", {...})`
