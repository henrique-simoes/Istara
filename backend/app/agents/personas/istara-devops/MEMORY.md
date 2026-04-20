# Sentinel -- DevOps Audit Agent Memory

## Learnings Log
_Automatically updated as audit patterns emerge._

### Known Error Patterns
- **Timezone comparison crash**: `can't subtract offset-naive and offset-aware datetimes` -- Always wrap datetime DB values with `ensure_utc()` before arithmetic
- **Orphaned task infinite loop**: Tasks referencing deleted projects get picked up repeatedly. Resolution: mark as DONE with "orphaned" note rather than returning to BACKLOG
- **Vector store table missing**: New projects may not have a vector store table until first document ingestion. Treat missing table as informational, not an error
- **str.get() AttributeError**: LLM responses sometimes return raw strings instead of expected dict objects. Always type-check before calling .get()

### Audit Thresholds
- RAM warning: > 90%
- Disk warning: > 90%
- Stale project threshold: 24 hours with no data
- Stale task threshold: 24 hours in IN_PROGRESS without update
- Finding quality minimum: insights should be >= 20 characters
- Audit log retention: 100 most recent reports

### System Patterns
- Simulation test projects are created and deleted rapidly. Expect orphaned records after test runs and don't over-prioritize them
- Context DAG compaction runs asynchronously after chat messages -- brief spikes in DB writes are normal
- LM Studio model switches may cause brief service interruptions. Allow 10-second grace period after model switch before flagging as "service down"

### Performance Baselines
_Track normal operating ranges to detect anomalies._
- Normal audit cycle time: 2-10 seconds
- Normal issue count per cycle: 0-3
- Normal RAM usage: 40-70%
- Expected vector store sizes: varies by project, typically 100-10000 entries

### Error Patterns & Resolutions
- When encountering '(sqlite3.OperationalError) no such column: tasks.input_document_ids
[SQL: SELECT tasks.id, tasks.project_id, tasks.agent_id, tasks.title, tasks.description, tasks.status, tasks.skill_name, tasks.agent', resolve by: Caught in audit loop, will retry next cycle
- When encountering '(sqlite3.OperationalError) no such column: projects.is_paused
[SQL: SELECT projects.id, projects.name, projects.description, projects.phase, projects.company_context, projects.project_context, project', resolve by: Caught in audit loop, will retry next cycle
- When encountering 'name 'db' is not defined', resolve by: Caught in audit loop, will retry next cycle