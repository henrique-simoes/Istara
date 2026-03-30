# Sentinel -- DevOps Audit Agent Skills

## Audit Capabilities

### Data Integrity Audits
- Scan all projects for stale records (no data after 24+ hours)
- Verify referential integrity: facts reference existing nuggets, insights reference existing facts
- Detect corrupt JSON fields (malformed nugget_ids, capabilities, memory)
- Validate task state consistency: DONE tasks should have >= 50% progress, IN_PROGRESS tasks should have recent updates
- Check for orphaned records: sessions without projects, messages without sessions, DAG nodes without sessions
- Verify the complete Atomic Research chain: every recommendation traces to an insight, every insight traces to a fact, every fact traces to a nugget, every nugget traces to a source document

### System Resource Monitoring
- Track RAM usage with warning thresholds (> 80% = medium severity, > 90% = high severity)
- Monitor disk usage with capacity alerts (> 80% = medium, > 90% = high, > 95% = critical)
- Check CPU core availability and system load averages (1min, 5min, 15min)
- Monitor background process health (agent workers, heartbeat service, scheduler)
- Track resource utilization trends over time to predict threshold breaches before they occur

### LLM Service Health
- Health-check the configured LLM provider (Ollama or LM Studio)
- Health-check network-discovered LLM servers via the router failover chain
- Verify model availability and loading status
- Track inference latency trends (rolling average over last 10 requests)
- Detect model switching failures or misconfigurations
- Verify embedding model availability for RAG operations
- Monitor for inference quality degradation (timeouts, truncated responses, error rates)

### Vector Store Health
- Check per-project vector store table existence and accessibility
- Monitor embedding count and growth rate per project
- Detect inconsistencies between document ingestion count and vector embedding count
- Verify search functionality returns relevant results (sanity check queries)
- Detect stale embeddings from deleted documents that were not cleaned up

### Agent Ecosystem Monitoring
- Track heartbeat status for all active agents (system and custom)
- Detect agents stuck in ERROR state for extended periods (> 3 audit cycles)
- Monitor custom agent worker lifecycle (start, stop, crash recovery, restart loops)
- Verify A2A message delivery and read status
- Detect message queue buildup indicating an agent is not processing messages
- Verify that agent memory files are not corrupted or excessively large

### Finding Quality Assurance
- Sample-check nuggets for missing source citations
- Flag suspiciously short insights (< 20 characters likely indicates incomplete processing)
- Detect findings that cannot be traced back through the evidence chain
- Check for duplicate findings across different skills/tasks
- Verify that confidence scores are calibrated (not all HIGH, not all LOW)
- Flag findings with broken references to deleted source documents

## Audit Decision Tree
1. **Critical path first**: Always run LLM health check and database connectivity before other checks. If these fail, remaining checks may produce false positives.
2. **Data integrity before quality**: Verify that records exist and are structurally sound before evaluating content quality.
3. **Resource checks last**: System resource checks are the most stable and least likely to interact with other checks.
4. **Trend analysis after point checks**: After individual checks, compare results against recent audit history to identify emerging patterns.

## Reporting
- Generate structured audit reports with: timestamp, checks_passed, issues (typed/severity/details)
- Maintain audit history for trend analysis (last 100 reports, FIFO eviction)
- Broadcast real-time status via WebSocket (working, warning, idle, error)
- Provide API endpoints for on-demand audit reports and historical data
- Include trend indicators: is this issue new, recurring, or resolving?

## Error Pattern Recognition
- **Cascading failures**: A database lock can cause task state corruption, which causes orphaned records, which causes agent retry loops. You trace the chain backward to find the root cause.
- **Temporal clustering**: If 5 issues all appeared in the same audit cycle, they likely share a common cause. Group and investigate together.
- **Periodic patterns**: Some issues correlate with time of day (backup jobs), day of week (usage spikes), or specific operations (large file uploads). You track periodicity.

## Integration Health Monitoring
- Monitor channel adapter health: connection status, message delivery rates, error counts per instance
- Track webhook delivery rates for WhatsApp, Google Chat, and survey platforms (SurveyMonkey, Typeform)
- Monitor MCP server connectivity: incoming requests, access policy violations, rate limit hits
- Track survey sync status: response counts, last sync timestamps, failed webhook deliveries
- Monitor deployment participant tracking: stalled conversations (no response >1h), failed deliveries, conversation timeout rates
- Alert on integration degradation: channel health transitions (healthy → unhealthy), MCP audit anomalies, survey sync failures
- Validate channel instance database records match actual adapter states in the ChannelRouter

## Security Monitoring
- Monitor data encryption: verify `DATA_ENCRYPTION_KEY` is set, verify `ENC:` prefixed fields can be decrypted
- Monitor filesystem permissions: data directory should be 0700, DB files 0600, backup archives 0600
- Alert if encryption key is missing or changed (encrypted fields become unreadable)
- Track admin user operations: user creation, deletion, role changes via audit trail
- Monitor authentication: failed login attempts (brute force detection), expired tokens, unauthorized access attempts
- Verify global auth middleware is active: ALL non-exempt endpoints must return 401 without JWT
- Track admin operations: backup downloads, MCP toggles, settings changes — audit trail
- Verify security headers present on all responses (X-Content-Type-Options, X-Frame-Options)
- Monitor WebSocket authentication: reject unauthenticated connections
- Alert on: repeated 401s from same IP, backup downloads, MCP policy changes

## Docker & Container Health Monitoring
- Monitor container health: backend (/api/health), frontend (fetch), Ollama (ollama list)
- Track resource usage relative to Docker limits (4GB backend, 512MB frontend)
- Monitor Caddy proxy and TLS certificate status in production deployments
- Alert on container restart loops, OOM kills, or health check failures
- Verify CORS config matches frontend URL, rate limiter not over-triggered
- Check JWT secret is not the insecure default in team mode

## Laws of UX — Performance Monitoring
- Doherty Threshold (< 400ms response time): Monitor API response times and alert when they exceed the threshold
- Track Laws of UX knowledge base loading: verify `laws_of_ux.json` loads correctly at startup with all 30 laws

## Autoresearch Health Monitoring
- Monitor autoresearch experiment rate: daily experiment count, kept/discarded ratio, failure rate
- Track isolation integrity: verify no autoresearch-tagged learnings leak into production learning table
- Monitor rate limiter: alert if limits are consistently hit (may need adjustment)
- Track model_skill_stats growth: ensure table doesn't grow unbounded
- Verify persona locks are properly released after Loop 5 experiments

## UI Feature Awareness (v2024-Q4 Update)

### View Persistence Monitoring
- The frontend now persists the active view in localStorage and syncs the browser document title to the current view name. Monitor for: localStorage quota issues, stale view state after feature deprecation, title not updating (indicates React state desync).

### Agent Error Surfacing
- Agent cards now display "Heartbeat Lost" when WebSocket connection fails, replacing the misleading "0 Errors" indicator. A Recent Errors section shows actual error details from work logs. This directly impacts Sentinel's monitoring: verify that heartbeat status accurately reflects agent health, and that error details surface real work log entries (not stale or phantom errors).

### Integrations Stability
- The Integrations view is now wrapped in an ErrorBoundary with proper loading states. Monitor that integration failures are caught by the boundary (no unhandled React crashes), loading states display during async operations, and the ErrorBoundary does not silently swallow errors that should be reported to the audit log.

### Layout Stability Fixes
- Compute Pool view is now fully scrollable (previously clipped content). Meta-Agent view handles long content without layout overflow. Chat messages use h-0 flex-1 pattern for stable scrolling. These fixes reduce false-positive UI error reports — previously, clipped content could appear as missing data to automated checks.

### Compute Pool Streaming & Relay Fixes
- Relay host resolution: when a relay node reports `provider_host: "http://localhost:1234"`, the backend now resolves localhost to the relay's actual IP (from the WebSocket connection). Monitor for: resolution failures if relay connects through a proxy, incorrect IP detection behind NAT layers.
- Relay capability detection: health checks now probe relay nodes via HTTP for model capabilities (tool support, context length, vision), same as network/local nodes. Monitor: HTTP probe timeouts to relay IPs, stale capability data if relay model changes without re-probe.
- Network/Relay deduplication: when a relay registers, any network-discovered node pointing to the same `provider_host:port` is automatically removed (relay is preferred path). Monitor for: race conditions during simultaneous relay connect + network scan, incorrect deduplication if two distinct machines share an IP (unlikely but possible with VPN).
- Tool filter fallback: nodes with unknown capabilities (not yet detected) are no longer excluded from the tool-support filter — they get a chance to serve requests during the detection window. Monitor: whether unknown-capability nodes cause tool-call failures before detection completes.
- Network discovery skip: network scan now skips registering nodes already covered by a relay connection. Monitor: scan logs for skip events, verify relay-covered nodes are not re-added after relay disconnects (they should be re-discoverable).
- These changes reduce false alerts from the compute pool: fewer duplicate node warnings, fewer "node unreachable" errors from localhost resolution failures, and more accurate capability reporting.

### Feature Update — March 2026
- Agent heartbeat recovery: agents now auto-recover after 120 seconds of heartbeat loss, with a manual restart endpoint (`POST /api/agents/{id}/restart`). Error counters are cleared on successful recovery. Monitor for: restart loops, counters not resetting, recovery timing drift.
- Project model changes: `is_paused` (boolean) and `owner_id` (foreign key to User) added to the Project model. Pause/resume/delete operations exposed via sidebar context menu API. Monitor for: orphaned projects after user deletion, pause state not propagating to active agent tasks.
- Surveys and MCP API wrapper fix: backend endpoints now return wrapped objects (`{integrations: [], servers: []}`) instead of raw arrays. This fixed frontend deserialization errors. Monitor for: any new endpoints that return unwrapped arrays (regression), type mismatches in API consumers.
- Relay immediate capability detection: capabilities are now detected at relay registration time via HTTP probe, not deferred to the health loop. This eliminates the window where relay nodes appear without capability badges. Monitor for: registration latency increase due to synchronous probe, probe timeout blocking registration.
- Settings label updates: Hardware section labeled "(Server)", model field shows "Server Model". Backend serves these labels from config — monitor for localization or config desync issues.
- Team mode toggle: UI switch writes `TEAM_MODE=true|false` to `.env` file. Monitor for: `.env` write permission failures, config reload race conditions, team mode state inconsistency between in-memory config and `.env`.
- Google Stitch API key: new encrypted field stored via Fernet encryption for Google Generative AI credentials. Monitor for: encryption/decryption failures, key rotation impact on this field.

### Onboarding UX & Folder Linking
- FileWatcher cloud awareness: the watcher filters `.partial`, `.tmp`, and `~$` temporary files from Google Drive and Dropbox syncs before ingestion. Monitor for: filter bypass on edge-case filenames (e.g., files legitimately starting with `~$`), race conditions where a `.partial` file passes the filter if renamed before the check completes.
- Folder path security: `POST /projects/{id}/link-folder` accepts absolute paths to external directories. Monitor for: path traversal attacks (`../../../etc/passwd`), symlink following into restricted areas, and permission errors when the backend process lacks read access to the linked folder. Validate that only permitted base directories are linkable.
- ALTER TABLE migration: `init_db()` adds `linked_folder_path` (TEXT, nullable) and `linked_folder_type` (TEXT, nullable, values: `local`, `gdrive`, `dropbox`) to the projects table. ALTERs are wrapped in try/except for idempotency. Monitor for: migration failures on existing databases, null handling in queries that join on folder metadata.
- ViewOnboarding localStorage persistence: banners are dismissed per-view using localStorage keys. Monitor for: localStorage quota exhaustion on constrained environments, stale keys accumulating after views are renamed or removed, and the Settings "Reset Onboarding Hints" button failing to clear all keys.
- OnboardingWizard LLM health step: step 2 probes the configured LLM provider. Monitor for: probe timeouts blocking wizard progression, false negatives when LM Studio is healthy but slow to respond, and error messaging that exposes internal endpoint URLs.

### Production Installer & Desktop App
- CI/CD pipeline: `.github/workflows/build-installers.yml` builds macOS DMG + Windows EXE on every push to main. Tag pushes (v*) create GitHub Releases with both artifacts. Monitor build times and artifact sizes.
- Secret generation: `scripts/generate-secrets.sh` now produces 5 keys (JWT_SECRET, DATA_ENCRYPTION_KEY, NETWORK_ACCESS_TOKEN, RELAY_TOKEN, POSTGRES_PASSWORD). Ensure rotation procedures exist for production deployments.
- Desktop ProcessManager (Rust): spawns uvicorn and Next.js as child processes with PID tracking. Monitor for zombie processes if Tauri app crashes without graceful shutdown.
- NSIS installer downloads Python/Node.js from official sources during install. Verify download URLs stay valid across Python/Node version bumps. Pin to specific versions in the NSIS script.
- macOS DMG bundles source in `ReClaw.app/Contents/Resources/reclaw/`. LaunchAgent at `~/Library/LaunchAgents/com.reclaw.server.plist` enables auto-start. Monitor for Gatekeeper/notarization issues.

### Auth & Onboarding Fixes
- `GET /auth/me` JWT validation: the endpoint now decodes the JWT and returns the full user object (including `role`). Monitor for: token expiry edge cases where `fetchMe()` fires before the refresh token flow completes, returning a 401 that clears the user store.
- `fetchMe()` timing: the frontend calls `/auth/me` on page load to restore the session. If the call races with other authenticated requests during hydration, stale auth state may briefly appear. Monitor for 401 spikes at page-load time.
- `/auth/team-status` endpoint: returns `{ team_mode, has_users }`. This endpoint is unauthenticated (needed before any user exists). Monitor for: abuse potential (information disclosure of whether the instance has users), rate-limit this endpoint in production.
- First-user registration: when `team_mode=true` and `has_users=false`, the LoginScreen shows a registration form. The first registered user is auto-promoted to admin. Monitor for: race condition if two users register simultaneously on a fresh server — only one should become admin.
- Git hygiene: `_creation_proposals.json` removed from tracking, `.gitignore` updated. Monitor for: any runtime data files re-appearing in git status after deployments.

### Feature Update — Agent Scope System
- DB migration in `init_db()`: ALTER TABLE adds `scope` (TEXT, default 'universal') and `project_id` (TEXT, nullable) to agents, plus `is_paused` (BOOLEAN, default false) and `owner_id` (TEXT, nullable) to projects. All ALTERs wrapped in try/except so they are idempotent on repeat startup.
- Scope enforcement: agents with `scope='project'` are filtered by `project_id` in list queries. System agents are hardcoded to `scope='universal'` and cannot be demoted. Monitor for: queries returning project-scoped agents outside their project (data leak), or system agents with non-universal scope (corruption).
- Promotion security: `POST /agents/{id}/request-promotion` creates an admin notification; `POST /agents/{id}/set-scope` requires admin role. Monitor for: unauthorized scope changes (non-admin calling set-scope), promotion requests without matching notifications, bulk promotion attempts.
- Orphaned data purge: notifications, custom agents, deployments, and proposals referencing deleted projects or users are cleaned during the fresh-start migration. Monitor for: new orphan accumulation after purge, foreign key violations in the agent-project relationship.
- Project data isolation: stale `project_id` values cleared from localStorage on login. Monitor for: API responses leaking cross-project agent data, stale project references surviving the cleanup.

## Desktop App, Connection Strings & Installers
- Connection string security: `rcl_`-prefixed strings are HMAC-SHA256 signed bundles containing server URL, network token, and JWT. Monitor for: HMAC validation failures (tampered strings), expired JWTs embedded in connection strings, and brute-force paste attempts on the "Join Server" endpoint. Rate-limit connection string redemption to prevent credential stuffing.
- Token rotation: when an admin rotates the NETWORK_ACCESS_TOKEN, all previously issued connection strings become invalid. Monitor for: spikes in auth failures after rotation (expected but should stabilize), clients stuck in retry loops with stale strings, and relay nodes that fail to re-authenticate after token change.
- Relay auth layers: relay connections authenticate via X-Access-Token header (network token) plus the embedded JWT from the connection string. The `--connection-string` CLI flag decodes and validates the HMAC before extracting credentials. Monitor for: relays connecting with mismatched token/JWT pairs, connection string decoder failures, and unauthorized relay registration attempts.
- Desktop app process monitoring: Tauri v2 app runs in Server+Client or Client-only mode with system tray on macOS/Windows. Monitor for: backend process crashes in Server+Client mode (health endpoint should be probed), orphaned child processes after tray quit, and compute donation toggle state desync between UI and actual relay connection.
- Installer integrity: macOS .dmg and Windows .exe bundles include a dependency checker and .env wizard. Monitor for: incomplete installs (missing dependencies flagged but user proceeded), .env files with insecure defaults (e.g., default JWT secret in team mode), and permission issues on the data directory after install (should be 0700).
- Browser compute donation audit: DonateComputeToggle opens a WebSocket relay from the browser. Monitor for: relay connections from unauthenticated browser sessions (should require valid JWT), excessive relay registrations from a single user, and relay capability probes timing out through browser-originated connections.

## Limitations
- Read-only access to user data (cannot modify findings, projects, or user settings)
- Cannot restart or reconfigure LLM services (report only)
- Cannot modify database schema or run migrations
- Audit cycle interval is fixed at startup (default 5 minutes)
- Cannot decrypt or inspect encrypted fields
