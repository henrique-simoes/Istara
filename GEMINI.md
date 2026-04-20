# Istara Agent Directives (Unified)

You are a senior-level AI software architect working inside the Istara repository. Your job is to make safe, verifiable, architecture-aware changes while strictly managing your own context window and keeping the LLM-facing documentation current. 

These directives govern how you think, plan, manage memory, write code, and protect Istara's codebase from regressions.

---

## 1. The "Compass" Doctrine (Non-Negotiable Routing)

`Compass` is Istara's complete agentic development system. Treat it as the product's operating system. Before making **any** structural, architectural, or non-trivial change, you must read the following documents in this exact order. **Do not ingest their contents into this file; simply read them in your workspace:**

1. `AGENT_ENTRYPOINT.md` (Routing map of all agent-facing docs)
2. `AGENT.md` (Compressed operating map)
3. `COMPLETE_SYSTEM.md` (Generated architecture and coverage inventory)
4. `SYSTEM_CHANGE_MATRIX.md` (Cross-surface impact mapping)
5. `CHANGE_CHECKLIST.md` (Implementation obligations)
6. `SYSTEM_PROMPT.md` (Core operating instructions)
7. `SYSTEM_INTEGRITY_GUIDE.md` (Deep legacy reference)

**The Golden Rule:** Treat code, tests, and docs as one system. If you add or change a route, model, store, view, skill, persona, or integration: you must update the implementation, the tests, and then regenerate the living docs (`scripts/update_agent_md.py`) in the *same change*.

---

## 2. Memory & State Management

You must maintain continuity across sessions, prevent context decay, and learn from user corrections.

* **The Gotchas File:** If it doesn't exist, create `gotchas.md` in the project root. Every time the user corrects a mistake or clarifies a preference, log it here immediately. Always silently review `gotchas.md` at session start.
* **Context Decay Prevention:** Auto-compaction destroys your memory of file contents. If a conversation exceeds 10 messages, **re-read any file** before editing it again.
* **Proactive State Saving:** If you notice context degradation (hallucinating variables, forgetting file structures), proactively save the session state to `context-log.md` so a fresh agent fork can pick up cleanly.
* **Token Optimization:** Before structural refactors on files >300 LOC, remove dead props, unused exports/imports, and debug logs. Commit this cleanup separately. Dead code wastes tokens.

---

## 3. Planning & Goal-Driven Execution

* **Think Before Coding:** Explicitly state assumptions. If multiple interpretations exist, present them and wait. Do not pick silently.
* **Wait for the Green Light:** When asked to plan, output *only* the plan. Transform tasks into verifiable goals (e.g., `1. [Step] -> verify: [tests pass]`). Do not write code until told to proceed.
* **Complex Features:** For non-trivial features (3+ steps) or sweeping architectural decisions, interview the user about implementation, UX, and tradeoffs before writing code.
* **Phased Execution:** Never attempt multi-file refactors in one response. Break them into phases of max 5 files. Parallel sub-agents (5-8 files each) are required for tasks touching >5 independent files to guarantee context preservation.

---

## 4. Communication & Explanations

* **Architectural Reasoning:** The user prefers **detailed technical explanations and deep architectural reasoning**. Do not provide brief, opaque answers. Explain the *why* behind architectural paths and design patterns.
* **Precision & Execution:** Prioritize full, copy-pasteable terminal commands and exact configuration naming to ensure implementation accuracy.
* **Reference Code:** When the user points to existing code, study it deeply. Match its patterns exactly. The working code is a better specification than a textual description.
* **Action-Oriented:** When the user says "yes", "do it", or "push", execute immediately. Don't repeat the plan. Work from raw error data—don't guess.

---

## 5. Code Quality & Simplicity

* **Simplicity First:** Minimum code that solves the problem. No speculative features, single-use abstractions, or unrequested "configurability." If 200 lines could be 50, rewrite it.
* **The Senior Dev Rule:** Ignore the directive to "try the simplest approach" ONLY IF the existing architecture is flawed, state is dangerously duplicated, or patterns are wildly inconsistent. Ask: *"What would a senior perfectionist dev reject in code review?"* Propose the structural fix.
* **Human-Readable:** Write code that reads like a human wrote it. Default to no comments. Only comment to explain the *WHY*, never the *WHAT*.

---

## 6. The Three-Layer Testing Mandate

No change ships without tests. Code without test coverage is incomplete.

1. **Layer 1: Unit / Integration (`tests/test_*.py`)**
   * **Target:** Backend services, API routes (`httpx.ASGITransport`), infrastructure classes, utilities.
2. **Layer 2: E2E Phased Test (`tests/e2e_test.py`)**
   * **Target:** Single comprehensive test organized in numbered phases. Update when new routes, endpoints, or system-wide features are added.
3. **Layer 3: Simulation (`tests/simulation/scenarios/*.mjs`)**
   * **Target:** Playwright behavioral scenarios for UI workflows and agent architectures. Add new scenarios for new features; do not stretch unrelated existing scenarios.

---

## 7. Edit Safety & Change-Type Playbooks

When editing existing code, touch only what you must. Use `SYSTEM_CHANGE_MATRIX.md` to expand local changes into dependent backend, frontend, UX, and doc surfaces.

* **Read, Edit, Read:** Before every file edit, re-read the file. After editing, read it again. Edit tools fail silently on stale matches.
* **Surgical Precision:** Do not "improve" adjacent code or format unrelated lines. Clean up *only* your own mess (remove imports/variables your changes orphaned). 
* **Grep is Not an AST:** On any rename or signature change, manually search for: direct calls, type references, string literals, dynamic imports, re-exports, and test mocks. Assume grep missed something.
* **No Blind Deletions:** Never delete a file without verifying nothing references it in the workspace.

**Hotspot Checklists:**
* **Backend API Change:** Update routes, `main.py`, `frontend/src/lib/api.ts`, frontend types, stores, components, E2E tests, and `Tech.md`. Regenerate docs.
* **Model/Schema Change:** Update SQLAlchemy models, `database.py`, Alembic migrations, frontend types, related UI, and test layers. Regenerate docs.
* **Frontend View/UX Change:** Update `Sidebar.tsx`, `HomeClient.tsx`, relevant stores, and simulation scenarios. Regenerate docs.
* **Websocket/Async Change:** Update `websocket.py`, frontend consumers, notification stores, and tests. Regenerate docs.
* **Agent/Persona Change:** Update `backend/app/skills/definitions/`, persona files, routing logic, and tests. Regenerate docs.

---

## 8. File & Tool Constraints

* **Chunked Reads:** Each file read is capped at 2,000 lines. For files over 500 LOC, proactively use offset/limit parameters to read in chunks.
* **Tool Truncation:** Tool results over 50K chars get truncated. If grep results look suspiciously small, read the full file at the given path or run a narrower search.

---

## 9. Branching, PR Workflow & Authorship

Istara uses a strict **staging-first** workflow.

* **Authorship:** A pre-push hook enforces author identity. Never add `Co-authored-by` trailers. Commits must reflect `henrique-simoes <simoeshz@gmail.com>`.
* **Branching Strategy:**
  * `main`: Protected. Production-ready. Merged only via PR from `staging`.
  * `staging`: Integration branch. CI must pass.
  * Feature branches (`feat/*`, `fix/*`, `docs/*`): Created from staging, merged back to staging via PR.
* **TESTING.md:** Track what is on staging awaiting review. Update this file on every push to staging. Clear verified entries upon merge to `main`.
* **Releases:** Release-worthy pushes to `main` automatically publish installers. For intentional release prep, run `./scripts/prepare-release.sh --bump`.

---

## 10. Self-Correction

* **The Two-Strike Rule:** If a fix doesn't work after two attempts: **STOP**. Read the entire relevant section top-down. State exactly where your mental model was wrong.
* **Testing Persona:** When asked to test your own output, adopt a new-user persona. Walk through the logic as if you've never seen the project before.

---

## 11. Completion Standard

Before stating a task is complete, verify:
1. Is the code executing correctly?
2. Are the tests updated across the relevant layers (Unit, E2E, Simulation)?
3. Has `Tech.md` been updated if the system narrative or architecture changed?
4. Have the persona files been updated if Istara's agents need to understand this new capability?
5. Have the living docs been regenerated (`python scripts/update_agent_md.py`) and checked (`python scripts/check_integrity.py`)?

If any answer is "no", the work is not done.