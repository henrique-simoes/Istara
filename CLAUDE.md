# ReClaw — Claude Code Development Guide

For full system understanding, see [AGENT.md](AGENT.md).

## MANDATORY: System Integrity Protocol

This protocol is NON-NEGOTIABLE. Skipping any step risks breaking subsystems.

### Before ANY Code Change
1. Read [CHANGE_CHECKLIST.md](CHANGE_CHECKLIST.md) for the type of change you're making
2. Check the Change Impact Matrix in [SYSTEM_INTEGRITY_GUIDE.md](SYSTEM_INTEGRITY_GUIDE.md)
3. Identify ALL files that need updating (use the dependency graph in the guide)

### After EVERY Code Change — The Integrity Gate
Every commit MUST pass this gate. No exceptions.

```
┌─────────────────────────────────────────────────┐
│            INTEGRITY GATE (run before commit)    │
│                                                  │
│  □ Tests pass: pytest tests/                     │
│  □ Integrity check: python scripts/check_integrity.py │
│  □ AGENT.md updated: python scripts/update_agent_md.py │
│  □ SYSTEM_INTEGRITY_GUIDE.md updated if:         │
│     - New model added                            │
│     - New API route added                        │
│     - New skill definition added                 │
│     - New frontend type/API namespace added      │
│     - New WebSocket event added                  │
│     - New integration/channel added              │
│     - Agent personas changed                     │
│  □ Tech.md updated if architecture changed       │
│  □ Affected test scenarios updated               │
│  □ All 5 agent personas know about the feature   │
│  □ WCAG compliance verified on new UI components │
└─────────────────────────────────────────────────┘
```

**The `check_integrity.py` script will FAIL if the guide is out of sync.** It cross-references database.py models, main.py routes, skill definitions, and frontend types against SYSTEM_INTEGRITY_GUIDE.md. If it exits with code 1, update the guide before committing.

### Reference Files
- [SYSTEM_INTEGRITY_GUIDE.md](SYSTEM_INTEGRITY_GUIDE.md) — 80KB complete reference: 51+ models, 200+ endpoints, 53 skills, data flows, dependency graph
- [CHANGE_CHECKLIST.md](CHANGE_CHECKLIST.md) — Step-by-step procedures for each change type + common pitfalls
- [INTEGRITY_INDEX.md](INTEGRITY_INDEX.md) — Quick navigation
- [INVESTIGATION_SUMMARY.md](INVESTIGATION_SUMMARY.md) — Architecture overview + critical paths

### Self-Updating Rule
**The guide documents MUST be updated as part of the same commit that changes the system.** Not in a follow-up. Not later. In the SAME commit. If you add a model, the guide's model registry gets a new row in that commit. If you add a route, the guide's route table gets a new row in that commit. This is how the guide stays reliable.

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
