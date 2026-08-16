# Adapter Coverage Matrix

| Surface | Verdict | Candidate scenario | Canonical tools | Remaining gap |
|---|---|---|---|---|
| chat/tool loop | prototype-supported | chat.tool_loop.task_and_finding | tasks.create, findings.create | Production SSE route adapter, history persistence, project auth and RAG injection still needed. |
| plan-and-execute/task lifecycle | prototype-supported | task.plan_execute.lifecycle | tasks.create, plans.create, tasks.update_lifecycle | Real Task DB lifecycle, planner execution, review rewards, hooks, and steering remain unwired. |
| documents/tools representative slice | prototype-supported | documents.tools.slice | documents.create, tasks.create, tasks.attach_document, findings.create | Actual document APIs, file storage, attach/detach endpoints and UI actions remain simulated. |
| structured outputs/core evals | prototype-supported | structured_outputs.core_eval | evals.emit_structured | Only deterministic eval artifact; live structured judge via Pi-owned tool loop not run this round. |
| memory/RAG representative slice | prototype-supported | memory.rag.slice | memory.search, findings.create, memory.write | Memory search/write are in-memory; LanceDB/RAG/content guard/citations need adapters. |
| skills representative slice | prototype-supported | skills.three_skill_slice | skills.apply, skills.apply, skills.apply, findings.create | Exactly three skill adapters simulated; full registry/ranking/memento lifecycle is not wired. |
| A2A representative slice | prototype-supported | a2a.debate_report.slice | a2a.delegate, a2a.delegate, a2a.report | Delegation/report envelopes only; A2A service persistence, rate limits and consensus are not wired. |
| channel lifecycle simulated slice | prototype-supported | channel.lifecycle.simulated_slice | channels.create, channels.receive, channels.respond | Simulated channel create/inbound/outbound only; real credentials/lifecycle/auth are intentionally unused. |
| model/provider routing through Pi ai | provider-smoke-supported | - | - | Pi ai reached DeepSeek in adapter package, but live model call was provider smoke, not full scenario scoring. |
| telemetry/token/tool-count trace capture | prototype-supported | - | - | Trace JSONL and scores capture Pi events, token estimates, tool counts; production telemetry redaction/export not wired. |
| real user CareNav benchmark | blocked | - | - | Needs production-like scenario adapter and budgeted live run; prior plan artifacts inventoried only. |
| production route replacement | blocked | - | - | Main Istara app code intentionally untouched; sidecar only. |
