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

## Limitations
- Read-only access to user data (cannot modify findings, projects, or user settings)
- Cannot restart or reconfigure LLM services (report only)
- Cannot modify database schema or run migrations
- Audit cycle interval is fixed at startup (default 5 minutes)
- Cannot decrypt or inspect encrypted fields
