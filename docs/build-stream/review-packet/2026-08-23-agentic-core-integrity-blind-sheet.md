# Blind Review Sheet — S3 Phase 1 (Independent Reviewer)

- Repo: /Users/user/Documents/Istara-main, branch `testing`, HEAD `9d7c506e` (= `origin/testing`; the change under review is the **uncommitted working tree**).
- Frozen: reviewer did NOT open `docs/build-stream/2026-08-23-agentic-core-integrity-and-qa.md`. All evidence below is from commands run by this reviewer on 2026-08-23.
- Note: implementer's claims file exists as untracked (`docs/build-stream/2026-08-23-agentic-core-integrity-and-qa.md`) but was not read.

---

## Q1. Engine-resolution precedence for POST /api/chat

Commands: read `backend/app/api/routes/chat.py`; ran covering test.

Key code (chat.py:131–152):

```
async def _resolve_chat_engine(http_request: Request, project_id: str, db: AsyncSession) -> str:
    if settings.pi_replacement_enabled:
        return "pi"
    header_name = (settings.pi_replacement_request_header or "").strip() or "x-istara-agent-engine"
    header_value = ((http_request.headers.get(header_name)) or "").strip().lower()
    if header_value:
        return _engine_choice_from_value(header_value)
    project_engine = await db.scalar(select(Project.agentic_engine).where(Project.id == project_id))
    if str(project_engine or "").strip():
        return _engine_choice_from_value(project_engine)
    return _engine_choice_from_value(getattr(settings, "agentic_engine_default", "legacy"))
```

Called at chat.py:974–976 (`pi_candidate = await _resolve_chat_engine(...) == "pi"`), replacing `pi_replacement_requested(http_request)`.

Answer — precedence (function `_resolve_chat_engine`):
1. `settings.pi_replacement_enabled` → "pi"
2. request header `x-istara-agent-engine` (or configured `settings.pi_replacement_request_header`); any non-empty value recognized in `PI_ENGINE_VALUES = {"pi","pi-candidate","pi-replacement","deepseek-pi"}` → "pi", otherwise → "legacy" (no fall-through)
3. project column `projects.agentic_engine` (same mapping; storage miss/blank falls through)
4. global default `settings.agentic_engine_default` ("legacy")

Covering test: `tests/test_chat.py::test_resolve_chat_engine_precedence`.

```
tests/test_chat.py::test_resolve_chat_engine_precedence PASSED           [ 50%]
============================== 2 passed in 2.94s ===============================
```

PASSED. Precedence verified: flag (scalar_calls==0), header "PI-candidate"→pi, unrecognized header over project="pi"→legacy with scalar_calls==0, no header + project="pi"→pi (1 scalar call), default pi/legacy paths.

## Q2. Stub-guard behavior of POST /api/chat

Code (chat.py:662–672), placed immediately after `get_visible_project_or_404` and BEFORE session resolve/create (chat.py:676–698) and user-message write (chat.py:700–711):

```
if getattr(settings, "llm_provider_contract_stub", False):
    _chat_log.warning("Chat rejected on stub provider plane (project=%s)", request.project_id)
    return StreamingResponse(iter([_provider_stub_chat_blocked_events()]), media_type="text/event-stream")
```

Payload (`_provider_stub_chat_blocked_events`, chat.py:160–180 shape): single SSE frame
`data: {"type": "error", "code": "provider_stub_chat_blocked", "message": "Chat is unavailable: ... QA contract stub, not a real model. ..."}` + blank line.
WHEN: **before** any session or message DB write (verified by code order; auth check still runs first). Returns HTTP 200 SSE.

Test run:

```
$ rm -f /tmp/opencode/blind-review-scratch2.db && DATABASE_URL=... backend/.venv/bin/python -m pytest \
  "tests/test_chat.py::test_resolve_chat_engine_precedence" \
  "tests/test_chat.py::test_chat_blocked_when_provider_is_contract_stub" -v
tests/test_chat.py::test_chat_blocked_when_provider_is_contract_stub PASSED [100%]
============================== 2 passed in 2.94s ===============================
```

Compose wiring:

```
docker-compose.qa.yml:68:      LLM_PROVIDER_CONTRACT_STUB: "true"
docker-compose.vps.yml:73:      - LLM_PROVIDER_CONTRACT_STUB=true
```

Answer: YES both stacks wire it; backend field `llm_provider_contract_stub: bool = False` added (config.py:372); pydantic-settings maps env var case-insensitively (config.py:397–400, no prefix). Test asserts status 200, `"provider_stub_chat_blocked"` present, `"qa-contract-response"` absent. Caveat: test does not assert absence of DB rows; side-effect-free ordering is verified by code inspection only (see F-B5).

## Q3. A11y contrast script + istara-950

```
$ python3 scripts/check_a11y_contrast.py | tail -3 ; echo EXIT=$?
RESULT: PASS
EXIT=0
counts: [light]=23, [dark]=23, PASS lines incl. RESULT = 47
```

Answer: PASSES. 46 color pairs total = 23 light + 23 dark (all PASS; minima 4.5:1 text / 3:0 borders+focus).

tailwind.config.js (working tree, line 21): inside `colors.istara` → `950: "#052e16"`.
Old version: `git show origin/testing:frontend/tailwind.config.js | grep istara-950` → exit 1, palette stops at `900: "#14532d"`. So **old did NOT define istara-950; new adds #052e16**.

## Q4. QA capability / feature-obligation checks

```
$ python3 scripts/check_qa_capabilities.py
QA capabilities check passed.          EXIT=0
$ python3 scripts/check_feature_obligations.py --base origin/testing --head HEAD --json-out /tmp/opencode/blind-feature-obligations.json
Feature-obligation classification passed.   EXIT=0
```

Report content caveat (verbatim): `"base": "9d7c506e…", "head": "9d7c506e…", "changed_paths": [], "spine_touched": false, "pass": true` — base and head are the SAME commit (origin/testing == HEAD), so the obligation checker validated an empty commit range; it does not see the uncommitted working-tree change (see F-B6).

New surface id in qa/runtime_capabilities.json (git diff vs HEAD): **`agentic.core-routing`** (paths include chat.py, dispatcher.py, AgenticCoreSection.tsx, ChatModelControls.tsx, chatStore.ts, check_a11y_contrast.py; deterministic: backend_contracts, frontend_contracts). The pre-existing `provider.chat` surface is preserved unchanged alongside it.

## Q5. Frontend gates (from frontend/)

```
npx tsc --noEmit    → exit 0, no output
npx eslint .        → exit 0, no output
npx vitest run      → Test Files 3 passed (3) / Tests 14 passed (14), exit 0
```

## Q6. Combined pytest run

```
$ rm -f /tmp/opencode/blind-review-scratch.db && DATABASE_URL="sqlite+aiosqlite:////tmp/opencode/blind-review-scratch.db" \
  backend/.venv/bin/python -m pytest tests/test_chat.py tests/test_a11y_contrast.py tests/test_design_tokens.py \
  tests/test_qa_capabilities.py tests/test_feature_obligations.py tests/test_workflow_contracts.py -q
..............................................                           [100%]
46 passed in 4.24s
```

(Note: reviewer used a scratch sqlite URL per the harness convention rather than the literal word `scratch`.)

## Q7. Frontend path for x-istara-agent-engine

- Header added in `frontend/src/lib/chatApi.ts:38`: `...(engine ? { "x-istara-agent-engine": engine } : {})` inside `chat.send(...)`.
- Value source: `engine` param typed `"pi" | "legacy"`; chatStore passes its state: `frontend/src/stores/chatStore.ts:125` (`get().engine`) into `chatApi.send(...)`; store adds `engine: "legacy"` default + `setEngine` (chatStore.ts:16–17, 38–39).
- What sets it: `frontend/src/components/chat/ChatView.tsx:97,102` — from the `/api/chat/model-catalog` response: `setEngine(catalog.engine === "pi" ? "pi" : "legacy")`, error fallback `setEngine("legacy")`.

So: backend model-catalog response → ChatView → chatStore.engine → chatApi.send header. Because the store defaults to "legacy", the header is effectively always sent once initialized (see F-B1).

## Q8. Scope discipline

`git status --short`: 15 modified + 10 untracked paths. Every path maps to an allowed bucket:
chat routing (backend/app/api/routes/chat.py, frontend chatApi.ts/chatStore.ts/ChatView.tsx), stub guard flag (backend/app/config.py, both compose files), a11y (AgenticCoreSection.tsx, scripts/check_a11y_contrast.py, tests/test_a11y_contrast.py), design tokens (tailwind.config.js, DESIGN.md, docs/design/, scripts/export_design_tokens.py, tests/test_design_tokens.py), QA registries (qa/runtime_capabilities.json, testing/feature_coverage.yml, scripts/check_feature_obligations.py — adds only a `pytest_core_routing` catalog entry pointing at the new tests), feature docs artifact (docs/features/site/manifest.json — generated_at timestamp bump ONLY), tests (tests/test_chat.py), process docs (docs/build-stream/*).

Diff secret scan (`git diff | grep -iE "secret|password|api[_-]?key|token=|bearer"`): no secrets found (only prose "token usage" text). No unrelated refactors detected. Nothing suspicious.
Observation: manifest.json regeneration changed only `generated_at`; whether docs/features content needed a substantive update for the store-behavior change was not independently verified.

## Q9. Correctness critique of chat.py diff

Findings (ranked): see FINDINGS table. Highlights:
- Header override short-circuit (chat.py:147–148): any non-empty non-Pi value (including the frontend's ever-present `"legacy"`, or garbage) selects legacy and skips `projects.agentic_engine`; a stale client can silently downgrade a project-persisted "pi". Mirrors `AgenticDispatcher.resolve_engine` (dispatcher.py:91–101), so it is consistent-by-design and covered by the precedence test — Minor.
- Stub-blocked SSE omits the main stream's headers (`Cache-Control`, `Connection`, `X-Accel-Buffering`; compare chat.py:669–672 vs 1193–1200) — proxies may buffer the single error frame — Minor.
- Stub block returns HTTP 200 + `{type:"error", code, message}` instead of a 4xx/5xx; frontend handles it via `event.type === "error"` (chatStore.ts:151–154), and existing in-stream errors use the same 200+SSE convention but without the `code` field — Nit.
- Inline `db.scalar(select(Project.agentic_engine))` (chat.py:149) raises on DB failure unlike dispatcher's exception-swallowing `_project_engine` (dispatcher.py:103–121) — Nit (session already required for the route).
- Empty-string header correctly treated as absent (falls through to project/default) — verified, no defect.
- `pi_replacement_enabled=True` still fails closed under the stub guard because the guard returns before engine resolution matters — correct interaction.

## Q10. Docs / token export

- DESIGN.md: YES — new "Token architecture" section contains a 14-row semantic table with explicit Light and Dark columns (`--ui-surface` … `--ui-success`), plus layer/governance sections. Spot-check vs `frontend/src/app/globals.css`: `--ui-accent #15803d/#4ade80`, `--ui-accent-soft #f0fdf4/#052e16`, `--ui-focus #2563eb/#93c5fd` all match the table.
- tokens.json parses; verbatim probe: top keys `['$description', '$schema', 'primitive', 'semantic']`; `semantic` keys `['dark','light']`; primitive.color.istara includes 950 `$value '#052e16'`. Bonus: `python3 scripts/export_design_tokens.py --check` → "design tokens up to date: docs/design/tokens.json", exit 0.

---

## FINDINGS

| ID | Severity | file:line | Finding |
| --- | --- | --- | --- |
| F-B1 | Minor | backend/app/api/routes/chat.py:147-148 (+ frontend/src/components/chat/ChatView.tsx:102) | Any non-empty unrecognized engine header (incl. frontend's always-sent "legacy" after a failed/slow model-catalog fetch) short-circuits to legacy and skips persisted projects.agentic_engine; stale client state can silently downgrade a project-persisted "pi". Consistent with dispatcher parity and tested intentionally, but cross-client override risk. |
| F-B2 | Minor | backend/app/api/routes/chat.py:669-672 | Stub-blocked StreamingResponse lacks the Cache-Control/Connection/X-Accel-Buffering headers the main SSE response sets (chat.py:1193-1200); intermediaries may buffer/delay the single error frame. |
| F-B3 | Nit | backend/app/api/routes/chat.py:665-672 | Fail-closed returns HTTP 200 + SSE `{type:"error",code,...}` instead of a 4xx/5xx; matches existing in-stream error convention and frontend handling (chatStore.ts:151), but status-code-based clients see success; event shape adds `code` vs other error events' `{type,message}`. |
| F-B4 | Nit | backend/app/api/routes/chat.py:149 | Project engine lookup raises on DB error here while the dispatcher's equivalent swallows exceptions and falls back to default (dispatcher.py:120-121) — divergent failure mode (low impact: session already required). |
| F-B5 | Nit | tests/test_chat.py:238-269 | Stub-block test asserts response text but never asserts absence of ChatSession/Message rows; the "before ANY side effect" claim rests on code order inspection only. |
| F-B6 | Minor | scripts/check_feature_obligations.py (invocation) | With origin/testing == HEAD (uncommitted work), `--base origin/testing --head HEAD` classifies an empty changeset (`changed_paths: []`, pass=true); the obligation gate currently measures nothing about this diff. |
| F-B7 | Nit | qa/runtime_capabilities.json (new agentic.core-routing block) | Indentation (1–2 spaces) inconsistent with the rest of the file; JSON valid, cosmetic only. |
| F-B8 | Info | docs/features/site/manifest.json:1577 | Regeneration bumped only `generated_at`; whether living feature docs needed a substantive content update for the chatStore behavior change was not independently verified. |

No Blocker or Major findings. No secrets, no out-of-scope refactors.
