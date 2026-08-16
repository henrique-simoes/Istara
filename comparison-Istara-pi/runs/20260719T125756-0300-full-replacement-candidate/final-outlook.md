# Final Outlook

## What Is Now Real

This is no longer just provider smoke. The replacement worktree contains code that routes representative Istara contracts through Pi-owned Agent loops, including tool execution policy and step lifecycle events. It records tool counts, Pi event traces, token estimates, outputs, and scores.

The current artifact set also preserves raw LLM prompt/input and model-output evidence for inspection in `raw-llm-calls/prompts.jsonl.gz` and `raw-llm-calls/outputs.jsonl.gz`, with a small `raw-llm-calls/manifest.json`. Raw evidence is separate from analysis; `scores.json`, this benchmark summary, and article notes carry interpretation.

## Surfaces Running Through Pi

- Chat/tool loop through `tasks.create` and `findings.create`.
- Plan-and-execute through task creation, DAG plan creation, and lifecycle update.
- Documents/tools through document creation and task-document linking.
- Structured evals through JSON-compatible eval artifact emission.
- Memory/RAG proxy through memory search/write and grounded finding.
- Skills through exactly three skill adapters.
- A2A through delegation and layered report envelopes.
- Channel lifecycle through simulated channel creation, inbound message, and outbound response.
- Model/provider routing through Pi ai to DeepSeek in a bounded live smoke.
- Raw prompt/output capture for 21 deterministic Pi faux-provider calls plus 1 DeepSeek smoke call.

## Exact Next Implementation Tasks

1. Replace in-memory `CanonicalToolFacade` handlers with adapters that call Istara task, document, finding, memory, channel, A2A, and skills services in the isolated worktree.
2. Add an HTTP/RPC sidecar boundary so Python/FastAPI harness tests can invoke the Pi loop without importing Node internals directly.
3. Map scenario 31, 53, 71, and 73 checks one-by-one to real adapter calls, retaining simulated credentials where required.
4. Add persistent RAG/LanceDB adapter with content-guard and citation envelopes.
5. Add full skill registry adapter and memento approval lifecycle beyond the three-skill cap.
6. Add live DeepSeek candidate runs for selected structured-output and memory/tool scenarios, with raw prompt/output capture and the remaining USD cap ledger.
7. Only after those pass, consider a production route experiment behind a feature flag in a future branch.
8. Keep every future LLM-based test/eval/judging/article call under `raw-llm-calls/` or a run-equivalent gzipped JSONL store before interpreting scores.

## Verdict

Another implementation round is needed. This round successfully creates the robust isolated candidate and benchmark spine, but it does not yet prove full production replacement.

Build Stream Conductor verdict: partial use only. The skills were loaded and their compliance record was added after the fact, but the literal watcher/cast pipeline was blocked by the absence of `.compass-forge/conductor/cast.json` and by the already-completed implementation occurring inside a depth-limited OpenClaw subagent rather than a real terminal-launched conductor. The next round should begin with `make_pipeline.py`, `make_cast.py`, and a real `conductor.py spawn` if conductor-owned evidence is required.
