# Sentinel -- DevOps Audit Agent Skills

## Audit Capabilities

### Data Integrity Audits
- Scan all projects for stale records (no data after 24+ hours)
- Verify referential integrity: facts reference existing nuggets, insights reference existing facts
- Detect corrupt JSON fields (malformed nugget_ids, capabilities, memory)
- Validate task state consistency: DONE tasks should have >= 50% progress, IN_PROGRESS tasks should have recent updates
- Check for orphaned records: sessions without projects, messages without sessions, DAG nodes without sessions

### System Resource Monitoring
- Track RAM usage with warning thresholds (> 90% = high severity)
- Monitor disk usage with capacity alerts (> 90% = high severity)
- Check CPU core availability and system load
- Monitor background process health (agent workers, heartbeat service, scheduler)

### LLM Service Health
- Health-check the configured LLM provider (Ollama or LM Studio)
- Verify model availability and loading status
- Track inference latency trends
- Detect model switching failures or misconfigurations
- Verify embedding model availability for RAG operations

### Vector Store Health
- Check per-project vector store table existence and accessibility
- Monitor embedding count and growth rate
- Detect inconsistencies between document ingestion and vector counts
- Verify search functionality returns relevant results

### Agent Ecosystem Monitoring
- Track heartbeat status for all active agents
- Detect agents stuck in ERROR state for extended periods
- Monitor custom agent worker lifecycle (start, stop, crash recovery)
- Verify A2A message delivery and read status

### Finding Quality Assurance
- Sample-check nuggets for missing source citations
- Flag suspiciously short insights (< 20 characters likely indicates incomplete processing)
- Detect findings that cannot be traced back through the evidence chain
- Check for duplicate findings across different skills/tasks

## Reporting
- Generate structured audit reports with: timestamp, checks_passed, issues (typed/severity/details)
- Maintain audit history for trend analysis (last 100 reports)
- Broadcast real-time status via WebSocket (working, warning, idle, error)
- Provide API endpoints for on-demand audit reports and historical data

## Limitations
- Read-only access to user data (cannot modify findings, projects, or user settings)
- Cannot restart or reconfigure LLM services
- Cannot modify database schema or run migrations
- Audit cycle interval is fixed at startup (default 5 minutes)
