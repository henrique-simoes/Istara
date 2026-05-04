# Production Hardening Plan - 2026-05-04

Source audit: `docs/PRODUCTION_READINESS_AUDIT_2026_05_04.md`

Compass Forge execution:
- Spec: `CF-SPEC-6`
- Work order: `CF-68`
- Objective: close launch-blocking contract, security, orchestration, statistical-rigor, and compute-management gaps while converting permissive smoke tests into exact regression tests.

## Execution Principles

1. Prefer contract fixes over cosmetic cleanup.
2. Remove `500` as an acceptable outcome for production-critical API tests.
3. Store secrets as one-time material only; keep durable state hashed or redacted.
4. Make background loops observable and cancellable.
5. Route pooled compute with explicit capacity and failure state.
6. Treat LLM consensus and autoresearch scores as noisy measurements, not deterministic truth.

## Phase 1 - P0 Launch Blockers

Status: implemented.

Work:
- Block unsafe local-admin exposure when local mode is bound to non-local interfaces without a network access token.
- Require localhost or authenticated admin for destructive update operations.
- Repair autoresearch API/engine runner contracts for start, stop, status, and experiment lookup.
- Add bounded autoresearch scoring with minimum improvement deltas, repeated measurements, confidence metadata, and exact tests.
- Verify WhatsApp HMAC signatures and Google Chat webhook tokens before dispatching unauthenticated inbound messages.
- Persist connection-string hashes and redacted previews instead of durable full invite/compute strings.

Primary tests:
- `tests/test_network_security.py`
- `tests/test_updates_security.py`
- `tests/test_autoresearch.py`
- `tests/test_webhooks_security.py`
- `tests/test_connections.py`
- `tests/test_project_rbac.py`

## Phase 2 - P1 Runtime Stability

Status: implemented for the launch-critical behavior; deeper transport-level MCP testing remains future work.

Work:
- Fix ensemble validation adapter behavior, especially adversarial review invocation.
- Add validation timeouts and preserve the original task output instead of replacing it with a validator-generated response.
- Expose agreement, kappa, cosine, confidence, and response-count fields separately for downstream inspection.
- Add sample-size weighting to adaptive validation method selection.
- Route LLM calls through score-aware compute selection and account for saturation, degradation, cooldown, and circuit-breaker state.
- Centralize meta-hyperagent task start/stop lifecycle so disabling cancels sleeping loops promptly.
- Expose MCP configured-vs-serving runtime status and mark toggle changes as restart-required until a transport lifecycle is explicitly attached.

Primary tests:
- `tests/test_adaptive_validation.py`
- `tests/test_compute.py`
- `tests/test_meta_hyperagent.py`
- `tests/test_mcp.py`

## Phase 3 - P2 File and Diagnostic Hardening

Status: implemented for externally supplied files covered by the audit.

Work:
- Sanitize Telegram instance ids and remote filenames before writing channel attachments.
- Cap Telegram attachment downloads using declared and actual byte sizes.
- Cap avatar uploads, reject empty files, use content-type-driven server extensions, and keep served avatar paths rooted inside avatar storage.

Primary tests:
- `tests/test_channel_file_security.py`
- `tests/test_agent_avatar_security.py`

## Phase 4 - Verification and Remaining Release Work

Status: completed for this hardening pass.

Verification completed:
- `pytest tests/test_network_security.py tests/test_updates_security.py tests/test_autoresearch.py tests/test_webhooks_security.py tests/test_connections.py tests/test_project_rbac.py::test_connection_strings_split_user_invite_from_compute_donation tests/test_adaptive_validation.py tests/test_compute.py tests/test_meta_hyperagent.py tests/test_mcp.py tests/test_channel_file_security.py tests/test_agent_avatar_security.py -q`: 62 passed.
- `pytest tests/test_auth_security.py tests/test_channels.py tests/test_client_identity.py tests/test_evaluation_skill.py tests/test_research_integrity.py::TestValidationExecutor tests/test_transcription.py tests/test_proxy_security.py tests/test_files.py -q`: 48 passed.
- `pytest tests/test_llm_servers.py -q`: 5 passed after correcting role tests to run in team mode.
- `pytest -q`: 454 passed.
- `python -m compileall -q backend/app`: passed.
- `npm run lint` in `frontend/`: passed with 16 existing warnings and 0 errors.

Final Compass Forge step:
- Run `compass-forge gate after --task CF-68`.

Residual work after this hardening pass:
- Add a true FastMCP transport-level health test once the serving lifecycle is made first-class.
- Gate mock interface endpoints behind a production profile flag.
- Split oversized route modules and generate or enforce frontend API types from OpenAPI.
- Add MIME sniffing or image decoder validation for avatar dimensions and content beyond declared content type.
- Build holdout corpora and human-review calibration for ensemble/autoresearch scoring.

## Menu Audit Continuation - Integrations and Admin

Status: implemented in the Compass Forge CF-91 menu-audit stream.

SDD contracts:
- Messaging channel setup must store canonical adapter config keys, not UI labels, and the setup wizard must not report success until the adapter starts and returns a healthy status.
- Failed channel and MCP connection tests must not leave orphaned registry rows.
- WhatsApp and Google Chat setup must collect inbound webhook secrets required by the authenticated webhook routes.
- MCP client setup must only offer transports that the backend actually supports. Until stdio/WebSocket transports are wired through a real client lifecycle, external MCP clients are HTTP-only.
- MCP audit APIs may return an envelope, but the frontend contract must normalize it before rendering.
- Connection strings must expose separate user-invite and compute-donation flows so pooled compute setup cannot accidentally mint user access.

Primary tests:
- `tests/test_channels.py`
- `tests/test_mcp.py`
- `tests/test_webhooks_security.py`
- `tests/test_connections.py`
- `tests/test_project_rbac.py::test_connection_strings_split_user_invite_from_compute_donation`

## Menu Audit Continuation - Interviews, Audio, and Desktop Tray

Status: implemented for launch-critical transcription and tray behavior in the Compass Forge CF-91 menu-audit stream.

SDD contracts:
- Interview and document audio uploads must create processing documents immediately, store language/ICR/review/tag metadata after transcription, and keep failed transcriptions out of the vector index.
- Audio previews must expose both transcript text and media playback metadata from Files and Documents APIs.
- Server and desktop installation paths must detect FFmpeg as a required dependency for Whisper-backed transcription.
- Tray server management must report occupied Istara ports instead of killing unrelated processes.
- WhatsApp audio webhooks must download bounded media, transcribe locally, and dispatch transcript metadata instead of a permanent pending marker.
- Channel inbound processing must use the current conversation/message schema and persist inbound traffic even when no deployment is active.
- Adaptive interview deployments must advance question indices without repeating the first question after the first answer.

Primary tests:
- `tests/test_transcription.py`
- `tests/test_files.py`
- `tests/test_documents.py`
- `tests/test_channel_inbound.py`
- `tests/test_channel_file_security.py`
- `tests/test_channel_resilience.py`
- `tests/test_webhooks_security.py`

Verification:
- `pytest tests/test_transcription.py tests/test_files.py tests/test_documents.py tests/test_channel_inbound.py tests/test_channels.py tests/test_channel_file_security.py tests/test_channel_resilience.py tests/test_webhooks_security.py`: 52 passed.
- `python -m compileall -q backend/app`: passed.
- `bash -n scripts/install-istara.sh`: passed.
- `cargo check --manifest-path desktop/src-tauri/Cargo.toml`: passed with existing dead-code warnings in desktop path resolver/process helpers.
