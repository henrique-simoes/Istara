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

## Limitations
- Read-only access to user data (cannot modify findings, projects, or user settings)
- Cannot restart or reconfigure LLM services (report only)
- Cannot modify database schema or run migrations
- Audit cycle interval is fixed at startup (default 5 minutes)
- Cannot decrypt or inspect encrypted fields
