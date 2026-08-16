# Coverage Delta

## Newly Demonstrated Replacement Evidence

| Surface | Previous verdict | New verdict | Evidence |
|---|---|---|---|
| Chat ReAct loop | TBD-evidence | Prototype-supported | `chat.tool_loop.task_and_finding` traverses Pi `Agent` loop and emits Pi tool execution events. |
| Agent task execution | TBD-evidence | Prototype-supported for task creation envelope | Canonical `tasks.create` executed by Pi tool loop and preserved project id/status envelope. |
| System action tools | TBD-evidence | Prototype-supported for two canonical actions | `CanonicalToolFacade` validates schemas and returns explicit success/error envelopes. |
| Model/provider routing | Pi provider smoke only | Provider path still supported inside replacement worktree | Latest remediation smoke: `deepseekProvider()` reached `deepseek-v4-pro` with 50 total tokens and `envAfter=false`. |
| Memory and A2A | TBD-evidence | Schema-only prototype | `memory.search` and `a2a.delegate` schemas/handlers exist, but no scenario path exercised them yet. |

## Not Yet Counted As Replacement Evidence

- Research spine.
- Design chat.
- Durable memory persistence/RAG.
- A2A multi-agent completion quality.
- Channel-facing turns.
- SDK/process sidecar lifecycle.
- Steering/follow-up queues.
- Autoresearch/meta loops.

## Next Coverage Step

Run a capped paired benchmark batch where at least one existing Istara scenario fixture is
adapted to the Pi sidecar. Recommended first batch:

1. `tests/simulation/scenarios/71-plan-and-execute.mjs`
2. `tests/simulation/scenarios/31-task-documents-tools.mjs`
3. One memory or A2A scenario if the owner approves the extra token budget.
