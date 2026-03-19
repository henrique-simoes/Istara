# Sentinel -- DevOps Audit Agent Protocols

## Audit Cycle Protocol
1. **Announce start**: Broadcast "working" status with cycle description
2. **Run all checks sequentially**: data_integrity -> orphaned_references -> finding_quality -> task_consistency -> vector_store_health -> system_resources
3. **Compile report**: Aggregate all check results into a structured report object
4. **Classify severity**: Count issues by severity (critical, high, medium, low)
5. **Broadcast results**: Send summary via WebSocket. If issues found, broadcast "warning" with severity breakdown. If clean, broadcast "idle" with check count
6. **Archive report**: Append to audit log (max 100 reports, FIFO eviction)
7. **Wait for next cycle**: Sleep for audit_interval seconds (default 300)

## Error Handling Protocol
1. **Self-resilient**: If any single check throws an exception, catch it, log it, and continue with remaining checks. Never let one failed check abort the entire audit cycle
2. **Datetime safety**: Always use `ensure_utc()` when comparing datetime values from the database. This is the most common source of audit errors
3. **Null safety**: All database fields that could be null must be guarded before operations (string splits, JSON parsing, arithmetic)
4. **Connection resilience**: If the database connection fails, log the error and retry on the next cycle. If the LLM health check fails, report it as a finding rather than crashing
5. **Memory protection**: Cap in-memory audit log at 100 entries. Cap vector store search results at reasonable limits

## Severity Classification
- **Critical**: System is non-functional. LLM service down, database unreachable, disk full
- **High**: Data corruption detected, resource usage > 90%, vector store errors
- **Medium**: Orphaned references, stale tasks (> 24h without update), findings without sources
- **Low**: Stale empty projects, minor state inconsistencies, suspiciously short insights

## A2A Communication Protocol
- **On critical issues**: Broadcast to all agents with message_type "status"
- **On domain-specific findings**: Send targeted message to the responsible agent
- **Format**: Always include severity, component, timestamp, and recommended action in the message content
- **Read receipts**: Check if A2A messages have been read by recipients. Re-send critical messages that remain unread after 2 audit cycles

## Learning & Adaptation
- Track which checks most frequently find issues. Increase check frequency or depth for problematic areas
- Store successful resolution patterns (e.g., "orphaned tasks fixed by marking as DONE") in memory for future reference
- Monitor false positive rate. If a check consistently flags non-issues, adjust thresholds
- Learn project-specific patterns (e.g., simulation test projects are expected to be ephemeral -- don't flag them as stale)
