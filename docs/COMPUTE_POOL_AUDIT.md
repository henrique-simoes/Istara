# Compute Pool Access & Connectivity Audit

Date: 2026-04-29
Branch: `codex/compute-pool-access-connectivity-audit`

## Scope

This audit covers remote client onboarding, connection strings, desktop/client setup, browser and CLI compute donation, LLM server registration, health/scoring, model listing, admin visibility, and Compass documentation.

## Findings

1. Remote frontend builds could bake `localhost:8000` into API and WebSocket calls. A user opening `http://server-ip:3000` would validate invites against their own machine, so the Istara server saw no connection.
2. Client setup accepted raw URLs and IP addresses in paths that should require an `rcl_...` invite. That created partial connection flows with no admin-visible invite redemption trail.
3. Connection-string payloads did not clearly separate the web app URL from the relay WebSocket URL. This matters for LAN installs where the app is on port 3000 and the backend relay socket is on port 8000.
4. Admin connection-string visibility was incomplete. Validation and redemption events were not persisted with enough information to see who redeemed an invite, when it was last checked, or whether it had been revoked/expired.
5. `/ws/relay` authentication relied on permissive local/team-mode behavior. Donated compute should require either the network token from a validated invite or a valid browser JWT in every mode.
6. Donated relay/browser nodes were registered, but chat routing still depended on backend-to-donor HTTP in important paths. Browser donation in particular cannot be reached through the browser tab's localhost by backend HTTP.
7. Browser LM Studio donation returned raw OpenAI-compatible responses while registry streaming expected Istara's normalized `{message: {role, content}}` response shape.
8. Model listing in settings was biased toward the active singleton provider instead of the unified compute registry, so remote or donated models could be absent from the user-facing list.
9. LLM server registration let non-admin users mark LAN/private hosts as `is_local`, effectively bypassing the remote-server admin gate.
10. Existing SQLite installs would not receive new connection-string audit columns from `create_all()`.
11. Compass/persona documentation still described stale relay behavior: direct HTTP streaming through resolved relay IPs, HMAC validation in the relay client, and incomplete browser donor assumptions.
12. Public validation/login rate limiters used `request.client.host`, which collapses all users behind a reverse proxy into one bucket, and kept client buckets indefinitely.
13. Browser chat donor failures nested errors under `result.error`, while backend relay handling expects top-level `error`.

## Implemented Improvements

- Added runtime API/WebSocket origin derivation for installed frontend builds and removed installer/desktop hardcoded localhost build values.
- Added configurable CORS origin regex so LAN frontends can call the backend without hand-editing every server IP.
- Updated connection-string creation to store separate `server_url` and `ws_url` values.
- Rejected raw URLs in client setup paths that must use `rcl_...` invites.
- Added connection-string redemption/validation metadata and migration coverage.
- Required token/JWT authentication for `/ws/relay` in all modes.
- Routed relay/browser chat over the existing WebSocket with unique request IDs and pending-response cleanup.
- Added relay/browser embedding requests over the same WebSocket path (`embed_request` / `embed_response`) so donated nodes can serve RAG and consensus embedding work without backend-to-donor HTTP reachability.
- Added timeout and disconnect handling that fails in-flight relay requests, clears pending request maps, and records a visible node health error.
- Normalized browser LM Studio donation responses to Istara's internal chat result shape.
- Surfaced browser donation failures in the UI instead of silently disconnecting.
- Counted browser donors as compute capacity and treated browser liveness as heartbeat-based.
- Added compute-pool UI states for serving, capability probe availability, stale model lists, and relay health errors.
- Aggregated `/settings/models` from `ComputeRegistry` so all healthy nodes can appear.
- Restricted non-local LLM server registration to admins based on parsed host, not a user-supplied `is_local` flag.
- Restricted network LLM discovery to admins.
- Changed connection string revocation to mark invites inactive instead of deleting the row, preserving the admin audit trail and enabling specific revoked-state feedback.
- Added validation rate limiting for the public connection-string validation endpoint.
- Added proxy-aware client IP extraction for rate limiters using `X-Forwarded-For` / `X-Real-IP` from configured `TRUSTED_PROXY_HOSTS` before falling back to socket host.
- Replaced unbounded in-memory rate-limit dictionaries with bounded LRU-style window buckets.
- Normalized browser donor chat errors to top-level `error`, matching relay/embedding response contracts.
- Added desktop/client guardrails that block compute donation in Client mode until a saved `rcl_...` invite exists.
- Updated Compass docs and personas to reflect invite-first access, URL split, relay WebSocket execution, and new simulation scenarios.

## Implemented Planner Tracks

### Compute Donation End-to-End Harness

Goal: Create an integration harness that starts a fake relay/browser donor, registers it over `/ws/relay`, issues chat and stream requests, and verifies node stats, model listing, request cleanup, and disconnect removal.

Acceptance checks:
- Valid JWT relay connects; missing token is rejected. Implemented with route-level fake WebSocket tests.
- Registered relay receives a node id and is removed on disconnect. Implemented with websocket lifecycle tests.
- Chat request sends exactly one `llm_request`, resolves from matching `llm_response`, and clears pending state. Implemented with registry tests.
- Timeout and disconnect failures clear pending state. Implemented with registry tests.

### Invite Lifecycle Visibility

Goal: Make the admin dashboard an authoritative view of invite state.

Acceptance checks:
- Generated invites show label, expiration, active/revoked state, redemption username, redeemed time, and last validation.
- Redeeming an invite updates the row once and does not overwrite the original redemption identity on repeated validation.
- Revoked, redeemed, expired, and malformed strings fail with specific user-facing errors.
- Public validation is rate limited to slow brute-force/tamper attempts.

### Relay Capability Resilience

Goal: Decouple compute availability from optional capability probes.

Acceptance checks:
- Relay chat and embedding work through WebSocket even if direct provider probing times out.
- Capability probe availability appears separately from serving state in compute stats/UI.
- Browser donors do not rely on backend HTTP probes against browser-local provider addresses.

### LLM Server Access Control Audit

Goal: Cover all paths that add, discover, or register LLM servers.

Acceptance checks:
- Non-admins may add only true localhost providers.
- LAN/private/public hosts require admin.
- Network discovery requires admin.
- Discovered network providers remain network scoped, not local.
- API keys remain encrypted at rest and are never returned in list responses.

### Installer/Desktop Client Regression Suite

Goal: Add automated tests for client-only mode configuration.

Acceptance checks:
- Client installer accepts valid `rcl_...` strings and writes `server_url` plus `ws_url`.
- Raw IP/URL input is rejected and not persisted.
- Desktop Client mode opens the remote `server_url`, not the backend API URL.
- Donation controls block when no invite is configured.

### Remaining Follow-Up

The remaining useful improvement is a fully black-box websocket test that drives the ASGI app through a real websocket client rather than a route-level fake. The current tests cover the relay route and registry contracts directly, which is sufficient for this branch, but a future test server harness would increase confidence in Starlette websocket integration details.
