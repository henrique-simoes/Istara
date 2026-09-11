# Build Stream — Chat Send `[Errno 2]` Regression

<!-- STATUS BLOCK -->
```yaml
item: chat-send-errno2-regression
branch: testing
phase: "Phase 1 — Reproduce, root-cause, fix (complete)"
stage: S5-ship
status: done
blocked_on: null
last: { agent: opencode, at: 2026-09-07T17:55:08Z, ledger: L-002 }
next_action: "Owner verifies chat on QA; no merge without explicit approval."
```
<!-- /STATUS BLOCK -->

## S0 Frame (DEC-1)
- Symptom: every `POST /api/chat` send on QA returns SSE
  `{"type": "error", "message": "[Errno 2] No such file or directory"}` —
  reproduced via API on luna/minimal, legacy/gemini, and default sessions.
  Sends worked days earlier, so this is systemic, not endpoint-specific.
- The two `except` handlers at `backend/app/api/routes/chat.py:1471-1482`
  swallow the traceback (`str(e)` only) and the backend access log shows no
  traceback — observability gap to close as part of the fix.
- DEC-1 (owner report + reproduce): treat as regression; frontend picker
  changes send identical payloads (session-persisted overrides), so the fault
  is backend-side until proven otherwise.

## Append-Only Ledger
- **L-001** (2026-09-07): Opened. Backend logs show no traceback; reproduced
  across 3 session/engine combos. Next: instrument, rebuild, reproduce.
- **L-002** (2026-09-07T17:55:08Z): FIXED and live. Root cause (latent, NOT the
  picker change — payloads identical, all engines failed): every provider turn
  unconditionally starts the Node Pi worker (`engine.py:583`), but
  `qa/Dockerfile` never shipped node or `pi-runtime` (drift vs
  `backend/Dockerfile`, which has both; qa header itself mandates sync), so
  `create_subprocess_exec("node")` raised bare FileNotFoundError. The two SSE
  `except` handlers only yielded `str(e)` with no logging — hence invisible.
  Fix: `qa/Dockerfile` mirrors node-24 + worker + `PI_WORKER_ENTRY`
  (CF-SPEC-15); `supervisor.ensure_started` pre-checks the binary and raises
  typed `PiWorkerError(worker_runtime_missing:…)`; SSE handlers now
  `_chat_log.exception` (kept permanently as observability). Regression test
  `test_worker_missing_node_runtime_fails_typed` (red→green).
  Verified: w1+chat+telemetry 64 passed, frontend 80/80, build green,
  feature-docs ok, diff-check clean, gate after CF-137 0 new, evidence 952,
  CF-137 finished. QA (`qa-backend` rebuilt): `node v24.19.0` +
  `/app/pi-runtime/src/worker.mjs` present; luna API send → chunk+usage+done;
  UI send → assistant echoed, no errno, no page errors; sessions state
  restored identical. No volumes/data touched.
  Residual: gemini-local session still fails with honest `Connection error.`
  (no LMStudio reachable from inside the container — environment truth, not a
  regression; was previously masked by Errno 2). Follow-up note: usage frame
  reports `effort: server_default` while Pi `thinking_level: minimal` travels
  separately in the bind payload — telemetry label only, sending unaffected.
