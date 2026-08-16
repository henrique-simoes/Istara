# Review And Remediation

## Review Passes

Child architect lanes were not spawned because this session is already a depth-limited subagent and no safe child-spawn lane was available. I ran the requested roles as separated passes:

- Architect A - Istara contracts: mapped required harness assets, scenario 31/53/71/73, eval contracts, and native tests.
- Architect B - Pi package/code: expanded the sidecar around Pi Agent and Pi ai with a scenario catalog, canonical facade, baseline runner, and artifact collector.
- Architect C - tests/methodology: added all-scenario tests, paired deterministic run artifacts, raw live call capture, scores, and coverage/gap matrices.

After the owner clarified that `/skill build-stream-conductor` was required, I re-opened this review under the actual Build Stream Conductor contract. Result: the literal conductor pipeline was not used. There is no cast file, no conductor-generated CF task graph, and no conductor stage attribution/review verdict evidence. The review/remediation loop in this run is therefore a manual role-separated approximation, not a multi-model conductor convergence.

## Findings Fixed

- Prior candidate only covered task/finding smoke. Fixed by adding representative document, plan, structured-output, memory/RAG, skills, A2A, channel, and telemetry slices.
- Prior runner could not pair baseline and candidate in one path. Fixed with `IstaraContractBaseline` and `--engine both`/`collect:artifacts`.
- Prior artifacts lacked raw live call prompt/output capture. Fixed with `raw-llm-calls/prompts.jsonl.gz` and `raw-llm-calls/outputs.jsonl.gz` for the DeepSeek smoke.

## Remaining Risks

- In-memory envelopes can drift from production Istara service behavior unless the next round binds each canonical tool to real route/service adapters.
- The live call proves Pi ai provider routing only; the broad eight-scenario candidate run is deterministic/no-model.
- The channel and A2A slices intentionally avoid real credentials and persistence.
- Build Stream Conductor evidence is partial. A fresh run from a real terminal watcher is required for literal planner/implementer/reviewer/fixer attribution and scorecard rows.
