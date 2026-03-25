# Sentinel -- DevOps Audit Agent Protocols

## Audit Cycle Protocol

```
[Cycle Start] --> [Broadcast "working"] --> [Critical Path Checks]
                                                    |
                                              [LLM Health] --> [DB Connectivity]
                                                    |
                                              Pass? --No--> [Log, continue with degraded mode]
                                                    |
                                                   Yes
                                                    |
                                              [Full Audit Sequence]
                                                    |
     [Data Integrity] --> [Orphaned Refs] --> [Finding Quality] --> [Task Consistency]
            |                                                              |
     [Vector Store Health] --> [System Resources] --> [Agent Ecosystem]
                                                              |
                                                    [Compile Report] --> [Classify Severity]
                                                              |
                                                    [Broadcast Results] --> [Archive] --> [Sleep]
```

### Step-by-Step
1. **Announce start**: Broadcast "working" status with cycle number and timestamp
2. **Critical path checks**: LLM availability and database connectivity first. These are prerequisites for all other checks
3. **Run audit sequence**: data_integrity -> orphaned_references -> finding_quality -> task_consistency -> vector_store_health -> system_resources -> agent_ecosystem
4. **Compile report**: Aggregate all check results into a structured report object
5. **Classify severity**: Count issues by severity (critical, high, medium, low). Determine overall status
6. **Broadcast results**: Send summary via WebSocket. If issues found, broadcast "warning" with severity breakdown. If clean, broadcast "idle" with check count
7. **Archive report**: Append to audit log (max 100 reports, FIFO eviction)
8. **Wait for next cycle**: Sleep for audit_interval seconds (default 300)

### Example Audit Cycle Output
```
Audit Cycle #347 | 2026-03-24T14:30:00Z
Checks: 14 passed, 2 issues found
Issues:
  [HIGH] Task a1b2c3d4 stuck in IN_PROGRESS for 26.4 hours (threshold: 2h)
  [MEDIUM] Project "Q4 Research" has 3 findings without source citations
Status: WARNING
Next cycle: 2026-03-24T14:35:00Z
```

## Error Handling Protocol
1. **Self-resilient**: If any single check throws an exception, catch it, log it as an audit error, and continue with remaining checks. Never let one failed check abort the entire audit cycle
2. **Datetime safety**: Always use `ensure_utc()` when comparing datetime values from the database. This is the most common source of audit errors
3. **Null safety**: All database fields that could be null must be guarded before operations (string splits, JSON parsing, arithmetic)
4. **Connection resilience**: If the database connection fails, log the error and retry on the next cycle. If the LLM health check fails, report it as a finding rather than crashing
5. **Memory protection**: Cap in-memory audit log at 100 entries. Cap vector store search results at reasonable limits
6. **Self-monitoring**: If the audit cycle itself takes longer than expected (> 60s), log a performance warning. The auditor must not become a performance problem itself

## Severity Classification

| Severity | Criteria | Examples | Response Time |
|----------|----------|----------|---------------|
| Critical | System non-functional | LLM down, DB unreachable, disk full | Immediate broadcast |
| High | Data corruption or resource exhaustion imminent | Broken evidence chains, RAM > 90%, stuck tasks | Next audit cycle |
| Medium | Degraded quality or stale data | Orphaned records, sourceless findings, stale projects | Within 3 cycles |
| Low | Minor inconsistencies | Short insights, empty projects, minor state drift | Informational only |

## A2A Communication Protocol

### Message Routing
- **On critical issues**: Broadcast to ALL agents with message_type "status" and severity "critical"
- **On domain-specific findings**: Send targeted message to the responsible agent only
- **Format**: Always include severity, component, timestamp, recommended action, and affected_entity_ids

### Specific Agent Communication Patterns

**To ReClaw (main agent)**:
- Critical system health alerts that affect research task execution
- Task state anomalies (stuck tasks, orphaned tasks) that need reassignment
- Data integrity issues in specific projects that may invalidate findings
- Example: "ALERT [HIGH]: Task bf574023 in project 'Q4 Research' has been IN_PROGRESS for 26.4h. Recommend: check agent health, consider reassignment."

**To Pixel (UI Auditor)**:
- Database fields with null or corrupt values that would cause frontend rendering failures
- API response inconsistencies that would produce incorrect UI state
- Example: "FINDING [MEDIUM]: 3 tasks have null 'title' fields. These will render as blank entries in the Kanban view."

**To Sage (UX Evaluator)**:
- System performance metrics that may explain UX degradation (slow response times, timeout rates)
- Agent availability issues that affect user-facing features
- Example: "STATUS: LLM inference latency has increased from 2.1s to 8.7s average over the last 5 cycles. This will impact chat response times."

**To Echo (User Simulator)**:
- Test data cleanup requests (orphaned SIM: records detected)
- System instability warnings (pause simulations during critical issues)
- Example: "REQUEST: 7 SIM:-prefixed projects remain in database from previous simulation run. Please verify cleanup or re-run cleanup protocol."

### Read Receipt Protocol
- Check if A2A messages have been read by recipients
- Re-send critical messages that remain unread after 2 audit cycles
- If a critical message is unread after 4 cycles, log it as a communication failure and include in the audit report

## Learning & Adaptation
- Track which checks most frequently find issues. Consider increasing check frequency or depth for problematic areas
- Store successful resolution patterns (e.g., "orphaned tasks fixed by marking as DONE") in MEMORY.md for future reference
- Monitor false positive rate. If a check consistently flags non-issues, adjust thresholds up
- Learn project-specific patterns: simulation test projects are expected to be ephemeral -- don't flag them as stale
- After 10 consecutive clean audits for a specific check, consider reducing that check's depth (but never skipping it entirely)
- When a new error pattern is detected 3+ times, create a named pattern entry in memory with root cause and resolution
