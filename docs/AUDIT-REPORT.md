# Istara Comprehensive Codebase Audit Report

**Date**: 2026-03-28
**Scope**: Full codebase — security, code quality, paid platform references, agent system, architecture conflicts, documentation

---

## Executive Summary

3 parallel audit agents analyzed the entire Istara codebase. Results:

| Severity | Security | Code Quality | Agent System | Total |
|----------|----------|-------------|-------------|-------|
| **CRITICAL** | 3 | 0 | 2 | **5** |
| **HIGH** | 6 | 4 | 3 | **13** |
| **MEDIUM** | 9 | 9 | 4 | **22** |
| **LOW** | 5 | 14 | 6 | **25** |
| **Total** | 23 | 27 | 15 | **65** |

**Positive findings**: No SQL injection, no mutable defaults, proper async cleanup in frontend, SQLAlchemy ORM throughout, .env properly gitignored, PBKDF2 with 100K iterations, content guard for prompt injection, data directory permissions hardened.

---

## CRITICAL Issues (5)

### 1. WebSocket accepts connection BEFORE auth validation
- **File**: `backend/app/api/websocket.py:98`
- **Impact**: Unauthenticated clients briefly receive broadcast messages in the race window
- **Fix**: Move token verification BEFORE `manager.connect(websocket)`

### 2. WebSocket requests bypass global JWT middleware
- **File**: `backend/app/core/security_middleware.py:80-82`
- **Impact**: All WebSocket connections skip the SecurityAuthMiddleware entirely
- **Fix**: Remove the WebSocket bypass or enforce auth in every WS handler before accept()

### 3. Relay WebSocket allows unauthenticated localhost connections
- **File**: `backend/app/api/routes/compute.py:38-71`
- **Impact**: Any process on localhost can register as relay node and intercept LLM requests
- **Fix**: Require auth on relay regardless of team_mode

### 4. Agent ID mismatch in orchestrator sub-agent sync
- **File**: `backend/app/agents/orchestrator.py:253-256`
- **Impact**: MetaOrchestrator NEVER syncs sub-agent states — they appear perpetually stopped
- **Fix**: Change `agent_map` keys to match `_ROLE_AGENT_IDS` (e.g., `"istara-devops"` not `"istara-devops_audit"`)

### 5. Priority "urgent" vs "critical" mismatch
- **File**: `backend/app/skills/system_actions.py:52` + `backend/app/core/agent.py:225`
- **Impact**: Tasks created with "urgent" priority via chat are processed LAST (lowest priority)
- **Fix**: Align tool enum with agent priority ordering

---

## HIGH Issues (13)

### Security (6)
| # | Issue | File |
|---|-------|------|
| 4 | No password strength validation | `auth.py:22-27` |
| 5 | No rate limiting on login endpoint | `auth.py:86` |
| 6 | LLM server API keys stored in plaintext | `llm_server.py:20` |
| 7 | User emails unencrypted despite docs claiming encryption | `user.py:25` |
| 8 | Encryption silently falls back to plaintext | `field_encryption.py:76-92` |
| 9 | Multiple routes missing admin checks (LLM servers, channels, surveys, scheduler, autoresearch) | Various |

### Code Quality (4)
| # | Issue | File |
|---|-------|------|
| 1 | README.md references "Dovetail" | `README.md:7` |
| 2 | Sage persona references Dovetail, EnjoyHQ, Optimal Workshop, UserTesting | `istara-ux-eval/SKILLS.md:42` |
| 21 | Relay LLM response handler is a no-op (silently drops responses) | `compute.py:114-116` |
| 24 | SETUP-GUIDE.md says Python 3.12+ but pyproject.toml says 3.11+ | `SETUP-GUIDE.md:5` |

### Agent System (3)
| # | Issue | File |
|---|-------|------|
| 3 | OllamaClient.chat_stream missing `tools` parameter | `ollama.py:114-149` |
| 4 | SPECIALTY_KEYWORDS missing new feature domains (channels, MCP, browser, autoresearch, Laws of UX) | `task_router.py:25-51` |
| 5 | Sage persona references paid tools | `istara-ux-eval/SKILLS.md:42` |

---

## MEDIUM Issues (22)

### Security (9)
- No upload file size limit
- Agent avatar path traversal possible
- Custom JWT instead of standard library
- PBKDF2 salt uses UUID instead of crypto random
- Fernet key derivation uses static salt
- Admin password logged in plaintext
- Missing CSP/HSTS headers
- CORS allows all methods
- Default bind host 0.0.0.0

### Code Quality (9)
- 4 skill definitions reference paid tools (Optimal Workshop, UserTesting, Maze, dscout)
- 94 instances of silent `except Exception: pass`
- Relay LLM TODO dead code
- 2 doc version conflicts (Python, Node.js)
- AGENTIC-ARCHITECTURE.md references old llm_router instead of compute_registry

### Agent System (4)
- Evidence chain IDs stored as JSON strings (no referential integrity)
- Context summarizer lacks error boundary for recursive LLM calls
- Laws of UX auto-tagging only on nuggets, not facts/insights
- Semantic skill matching is dead code (run_until_complete inside async context)

---

## Paid Platform References to Remove

| File | Reference | Action |
|------|-----------|--------|
| `README.md:7` | Dovetail | Replace with generic |
| `istara-ux-eval/SKILLS.md:42` | Dovetail, EnjoyHQ, Optimal Workshop, UserTesting | Replace with "commercial UXR platforms" |
| `usability-testing.json` | "UserTesting, Maze" | Replace with "remote unmoderated platforms" |
| `tree-testing.json` | "Optimal Workshop" (multiple) | Replace with "tree testing platform" |
| `card-sorting.json` | "OptimalSort, UserZoom, Maze" | Replace with "digital card sorting tools" |
| `diary-studies.json` | "dscout, Indeemo" | Replace with "dedicated diary study platforms" |

**Keep**: Academic citations (Intercom Blog, DesignBetter by InVision, Qualtrics XM Institute), test fixtures (synthetic data), Figma (real integration).

---

## Architecture Conflicts

| Issue | Status |
|-------|--------|
| compute_registry backward compat wrappers | ✅ Working correctly |
| Circular imports | ✅ None detected |
| Old+new system mixed imports | ✅ None conflicting |
| Semantic skill matching dead code | ❌ `run_until_complete` inside async = never works |
| Evidence chain JSON storage | ⚠️ Works but no referential integrity |

---

## Documentation Conflicts

| Doc | Issue | Fix |
|-----|-------|-----|
| SETUP-GUIDE.md | Python "3.12+" → should be "3.11+" | Update |
| SETUP-GUIDE.md | Node "20+" vs CLAUDE.md "18+" | Reconcile |
| AGENTIC-ARCHITECTURE.md | References llm_router as routing engine | Update to compute_registry |
| Tech.md | LLM Server + Compute Pool sections describe old separate systems | Add note about compute_registry unification |

---

## Improvement Plan (Priority Order)

### Batch 1: Critical Fixes (Immediate)
1. Fix WebSocket auth race condition (move auth before accept)
2. Fix orchestrator agent ID mismatch
3. Fix priority urgent/critical mismatch
4. Remove paid platform references from source code

### Batch 2: Security Hardening
5. Add password strength validation
6. Add login rate limiting (5/min)
7. Encrypt LLM server API keys
8. Add admin checks to LLM servers, channels, surveys, scheduler, autoresearch routes
9. Fix encryption silent fallback (warn on startup)
10. Fix WebSocket middleware bypass

### Batch 3: Agent System Fixes
11. Fix semantic skill matching (async/await instead of run_until_complete)
12. Add missing SPECIALTY_KEYWORDS for new features
13. Add OllamaClient.chat_stream tools parameter
14. Fix evidence chain cartesian linking

### Batch 4: Documentation Updates
15. Reconcile Python/Node version numbers
16. Update AGENTIC-ARCHITECTURE.md for compute_registry
17. Update Tech.md old sections
18. Add silent exception logging to orchestrator

---

## Positive Findings

- No SQL injection vectors (SQLAlchemy ORM throughout)
- No mutable default arguments in Python
- Proper async cleanup in all frontend hooks
- .env properly gitignored
- PBKDF2 with 100K iterations + timing-safe comparison
- Content guard for prompt injection
- Data directory permissions hardened (700)
- File upload path traversal protection in files.py
- Channel credentials and MCP headers properly encrypted
- Auto-generated JWT secret with cryptographic randomness
- 0 TODO/FIXME in frontend code
- All useEffect hooks have cleanup functions
