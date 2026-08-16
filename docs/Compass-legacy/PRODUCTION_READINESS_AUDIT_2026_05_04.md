# Production Readiness Audit - 2026-05-04

Compass Forge spec: `CF-SPEC-5`

Scope: backend autoresearch, meta agents, skill evolution, automatic agent creation, messaging and survey integrations, Aura/Stitch-style research integrations, MCP, ensemble validation, LLM orchestration, pooled compute, security, orphan/broken code, performance, and test harness quality.

## Executive Summary

This codebase has a strong product architecture: local-first operation, approval-first self-improvement, encrypted integration config, explicit MCP policy, a unified compute registry, and broad menu coverage. It is not production-ready yet. The highest-risk problems are not syntax issues; they are route/runtime contract breaks, permissive local-mode security defaults, webhook authenticity gaps, statistical validation that is labeled more rigorously than it behaves, and tests that allow failures to pass.

Recommended release posture: block production exposure until the P0 and P1 items below are fixed and covered by contract tests that do not allow 500 responses.

## Compass Forge Evidence

- `compass-forge status`: repository registered, recipe valid, gate status `warn`, state stale because of existing dirty worktree paths.
- `compass-forge agent-brief --request ...`: classified as `security_or_architecture`, blast radius `full`.
- `compass-forge intelligence impact --request ...`: highlighted hotspots including `backend/app/core/agent.py`, `backend/app/core/compute_registry.py`, `backend/app/main.py`, `backend/app/skills/skill_manager.py`, `backend/app/models/database.py`, `backend/app/agents/orchestrator.py`, and major frontend views.
- `compass-forge spec create ...`: created `CF-SPEC-5`. Planning remained blocked by the generated clarification marker, so this audit is the clarification and hardening map.
- `compass-forge gate before` and `compass-forge gate after`: both `warn`, no new gate issues. Main warnings are route drift, type drift, and oversized modules.

## Verification Run

- `python -m compileall -q backend/app`: passed.
- `pytest tests/test_autoresearch.py tests/test_meta_hyperagent.py tests/test_network_security.py tests/test_client_identity.py tests/test_evaluation_skill.py tests/test_research_integrity.py::TestValidationExecutor tests/test_transcription.py -q`: 41 passed.
- `pytest tests/test_mcp.py tests/test_compute.py tests/test_connections.py tests/test_channels.py tests/test_updates_security.py tests/test_auth_security.py tests/test_proxy_security.py -q`: 41 passed.
- `npm run lint` in `frontend/`: passed with 16 warnings.

Important caveat: several high-risk tests are smoke tests and accept `500`, `502`, or `404`. Passing them does not prove the feature works.

## P0 Production Blockers

### 1. Local-mode network exposure grants admin to remote clients

Files:
- `backend/app/config.py`
- `backend/app/core/security_middleware.py`
- `backend/app/core/network_security.py`

Default settings are `team_mode=False`, `network_access_token=""`, and `bind_host="0.0.0.0"`. In local mode, `SecurityMiddleware` assigns the local admin identity to every non-exempt HTTP request. `NetworkSecurityMiddleware` only protects non-local requests if `NETWORK_ACCESS_TOKEN` is set.

Impact: a default production or LAN deployment can expose admin behavior without credentials.

Fix:
- Refuse startup when `bind_host` is non-local, `team_mode` is false, and no network token is configured.
- Or force network-token middleware on any non-local bind.
- Tighten CORS defaults for production. Current `cors_origin_regex` allows any host on port 3000.
- Add tests for remote-client local-mode denial.

### 2. Autoresearch start/stop route contract is broken

Files:
- `backend/app/api/routes/autoresearch.py`
- `backend/app/core/autoresearch_engine.py`
- `backend/app/core/autoresearch_runners/*`
- `tests/test_autoresearch.py`

The route calls:

```python
await engine.run_loop(loop_type=body.loop_type, target=..., ...)
engine.stop()
engine.get_experiment(experiment_id)
```

The engine exposes:

```python
run_loop(runner, target, max_iterations=20, project_id="")
request_stop()
get_current_experiment()
get_experiments(...)
```

`_get_runner()` returns a module, not a runner instance. Starting an experiment logs an error in the background instead of running. Stopping calls a missing method. Fetching a single experiment calls a missing method.

Impact: Autoresearch can appear enabled in the UI while never running correctly.

Fix:
- Map loop type to runner classes and instantiate them.
- Pass `runner` into `run_loop`.
- Use `request_stop()` or add a real `stop()` alias.
- Add `get_experiment()` backed by DB lookup or remove the route.
- Change tests to assert exact `200/403/409` behavior and fail on `500`.

### 3. Webhook authenticity is missing for WhatsApp and Google Chat

Files:
- `backend/app/api/routes/webhooks.py`
- `backend/app/channels/whatsapp.py`
- `backend/app/channels/google_chat.py`

Webhook POSTs dispatch messages into the agent pipeline without verifying platform signatures. WhatsApp only verifies the GET challenge token. Google Chat POSTs have no token/signature check. Webhook paths are exempt from normal auth.

Impact: any party with an instance id can inject messages into connected agents if the webhook route is internet reachable.

Fix:
- Verify Meta `X-Hub-Signature-256` using app secret.
- Add per-instance inbound webhook secret or Google Chat JWT/token verification.
- Add replay protection beyond in-memory message-id sets where platforms support ids.
- Add negative tests for invalid signatures.

### 4. Connection strings are stored and returned with embedded credentials

Files:
- `backend/app/core/connection_string.py`
- `backend/app/models/connection_string.py`
- `backend/app/api/routes/connections.py`

User invite strings include a pre-minted JWT. Compute donation strings include the network token. The full string is stored in plaintext and returned from `ConnectionString.to_dict()`.

Impact: DB leakage or admin-list exposure leaks live invite JWTs or relay network tokens.

Fix:
- Store hash plus metadata, not the full string.
- Show the full string once on creation only.
- Return preview/redacted strings in list endpoints.
- Consider separate signing secrets for invites and compute donation.

## P1 High-Risk Hardening

### 5. Update auto-apply remains dangerous if local mode is exposed

File: `backend/app/api/routes/updates.py`

The update route has confirmation strings, but local-mode exposure makes admin-only assumptions unsafe. `_run_update` performs `git stash`, `git clean -fd`, `git pull`, dependency install/build, and restart. There is no signed release pinning, branch allowlist, dry-run diff, or protected local file strategy.

Fix: require authenticated admin for update operations regardless of local mode when bound non-locally, disable auto-apply by default in production, and pin updates to signed releases/tags.

### 6. Ensemble validation is integrated, but not statistically rigorous enough for its label

Files:
- `backend/app/core/consensus.py`
- `backend/app/core/validation.py`
- `backend/app/core/adaptive_validation.py`
- `backend/app/core/agent.py`
- `frontend/src/components/common/EnsembleHealthView.tsx`

Issues:
- `adversarial_review(prompt, initial_response, ...)` cannot be called by the agent integration, which invokes `fn(prompt=..., system=output.summary)`. If selected, it raises `TypeError` and is silently skipped.
- Validation calls have no timeout and can block task completion.
- `compute_consensus()` uses keyword categories plus optional embedding similarity. This is useful as a heuristic, not strong Fleiss' Kappa across coded items.
- The UI labels thresholds as kappa while backend exposes composite `agreement_score`.
- Passing validation can replace `output.summary` with a fresh response to the prompt, not a validated version of the skill output.
- Adaptive method selection uses success rate and consensus averages without sample-size penalties, confidence intervals, calibration, or holdout checks.

Fix:
- Separate `agreement_score`, `kappa`, and semantic similarity in UI and storage.
- Add timeouts around validation.
- Fix the adversarial review adapter.
- Introduce minimum sample sizes, uncertainty bounds, and conservative default selection.
- Use task/finding-level labels or human-review outcomes as calibration data.

### 7. Autoresearch scoring is greedy and underpowered

Files:
- `backend/app/core/autoresearch_engine.py`
- `backend/app/core/autoresearch_runners/*`

The engine keeps any mutation with `score > best_score`. There are no repeated trials, variance estimates, confidence intervals, effect sizes, held-out evaluation sets, or sequential test controls.

Impact: noisy LLM judge scores can cause false-positive mutations and prompt/persona drift.

Fix:
- Use repeated evaluations per candidate.
- Require effect-size margin over baseline.
- Track standard error or bootstrap CI.
- Use holdout cases per skill/persona.
- Record experiment seeds, judge model, prompt hash, and input corpus hash.

### 8. Compute registry does not consistently use its own scoring model

File: `backend/app/core/compute_registry.py`

`ComputeNode.score()` includes active requests, latency, priority, and RAM. `_select_candidates()` sorts by score and circuit-breaker availability. Main `chat`, `chat_stream`, `embed`, and `embed_batch` use `_sorted_servers()` instead, sorting mostly by health, priority, and latency. Active request load and RAM are not consistently applied.

Other issues:
- Nodes are marked unhealthy after most transient request errors, often before circuit-breaker thresholds.
- Streaming path does not consistently call circuit-breaker success/failure methods.
- No per-node concurrency semaphore or hard max inflight.
- Relay/browser streaming is buffered as a single non-streaming response.

Fix:
- Route main LLM calls through `_select_candidates()`.
- Add per-node concurrency limits.
- Make health state and circuit breaker state consistent.
- Treat first transient failures as degraded, not immediately unhealthy.

### 9. Meta-hyperagent loop stop is delayed or ineffective

Files:
- `backend/app/core/meta_hyperagent.py`
- `backend/app/main.py`
- `backend/app/api/routes/meta_hyperagent.py`

`MetaHyperagent.stop()` cancels `self._task`, but startup/route code creates tasks externally and `start_observation_loop()` does not store `self._task`. Disabling can set `_running = False`, but a loop sleeping for hours will not stop promptly without cancellation.

Fix: centralize task creation in `meta_hyperagent.start()`, store the task, and cancel it during disable/shutdown.

### 10. MCP toggle and serving lifecycle are disconnected

Files:
- `backend/app/api/routes/mcp.py`
- `backend/app/mcp/server.py`
- `backend/app/main.py`

The MCP policy layer is reasonable, and MCP is off by default. But toggling sets `settings.mcp_server_enabled` in memory and warns that restart may be required. I did not find the FastMCP server being started/stopped by the FastAPI app.

Impact: UI can show "enabled" without the MCP server actually serving, or a separately started server may not be governed by the expected lifecycle.

Fix:
- Define one explicit MCP serving mode.
- Add startup/shutdown lifecycle and health assertions.
- Add contract tests that call the actual MCP server transport, not just the management API.

## P2 Reliability and Maintainability

### 11. Agent and persona diagnostics expose sensitive internals

Files:
- `backend/app/api/routes/agents.py`

Several diagnostic routes expose persona identity, memory, prompt composition, exports, and resource status without route-level role checks. Team mode middleware authenticates, but many routes do not require project access or admin after authentication.

Fix: classify routes as public, authenticated, project-scoped, or admin-only. Apply explicit dependencies.

### 12. Skill and agent creation use approvals, but post-approval failures are often silent

Files:
- `backend/app/api/routes/agents.py`
- `backend/app/skills/skill_manager.py`

Approval flows are present. However persona scaffolding, worker startup, websocket broadcast, and runtime registration frequently swallow exceptions.

Fix: return partial-failure diagnostics and create audit events. A created agent whose worker failed to start should not look fully ready.

### 13. File handling needs production bounds

Files:
- `backend/app/channels/telegram.py`
- `backend/app/api/routes/agents.py`

Telegram document filenames are written directly under `data/channel_files/...`; sanitize names and constrain sizes. Avatar upload validates content type but not file size or dimensions.

Fix: sanitize filenames, cap file size, verify MIME from bytes when possible, and store randomized filenames.

### 14. Mock interfaces should be production-gated

File: `backend/app/api/routes/interfaces.py`

There are `/interfaces/mock/*` endpoints in a very large route module. They may be useful for simulation, but should be hidden or disabled in production profiles unless explicitly enabled.

### 15. Route and type drift are large

Compass Forge reports many backend routes missing from configured API clients and many Pydantic/model shapes missing from frontend type files.

Fix:
- Generate frontend clients/types from OpenAPI, or
- Add contract tests that compare FastAPI route/schema surfaces to `frontend/src/lib/api.ts` and `frontend/src/lib/types.ts`.

### 16. Test coverage allows broken production behavior

Examples:
- `tests/test_autoresearch.py` accepts `200, 404, 500, 502`.
- `tests/test_mcp.py` accepts `200, 404, 500, 502`.
- `tests/test_compute.py` accepts `500` for core API routes.
- `tests/test_meta_hyperagent.py` smoke-tests permissive response sets.

Fix: remove `500` as acceptable from production-route tests. Add exact contract tests for start/stop, webhook rejection, MCP lifecycle, compute routing, and ensemble method selection.

## Hardening Roadmap

### Phase 1: Release blockers

1. Lock down local-mode exposure on non-local bind hosts.
2. Fix Autoresearch route/engine runner contract.
3. Add webhook signature verification.
4. Stop returning/storing full connection strings.
5. Convert permissive smoke tests for these areas into exact contract tests.

### Phase 2: Runtime stability

1. Fix meta-hyperagent task lifecycle.
2. Use score-aware compute routing and add per-node concurrency limits.
3. Add validation timeouts and fix adversarial review invocation.
4. Make MCP serving lifecycle explicit.
5. Gate destructive update behavior behind production-safe checks.

### Phase 3: Statistical rigor

1. Add repeated trials and holdout corpora to Autoresearch.
2. Track variance, CI, and effect-size thresholds.
3. Calibrate ensemble consensus against human review outcomes.
4. Rename UI metrics where they are composite agreement, not kappa.

### Phase 4: Architecture cleanup

1. Split oversized route/core modules.
2. Generate or validate API types.
3. Audit silent exception swallowing in agent/skill lifecycle.
4. Gate mock endpoints and diagnostics by runtime profile.

## Suggested Next Work Orders

1. P0 security hardening: bind-host/local-mode guard, connection string redaction, webhook signatures.
2. P0 Autoresearch repair: runner instantiation, start/stop/get contract, exact tests.
3. P1 compute and ensemble stability: scoring router, circuit breaker consistency, validation timeout, adversarial adapter fix.
4. P1 MCP lifecycle: actual server start/stop contract and transport-level tests.
5. P2 API contract project: OpenAPI-derived frontend client/types or drift gate.
