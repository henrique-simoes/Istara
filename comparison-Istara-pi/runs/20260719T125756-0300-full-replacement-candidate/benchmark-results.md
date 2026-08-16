# Benchmark Results

## Summary

- Scenario inventory: `114` Istara harness assets/cases inventoried.
- Paired deterministic contract run: baseline `8/8`, candidate `8/8`.
- Candidate Pi-owned loops: `8/8` scenarios.
- Expected tool order matched: `8/8` scenarios.
- Candidate canonical tool calls: `23`.
- Candidate Pi faux provider calls: `21`.
- Candidate faux token total: `30348` with zero live cost.
- Raw LLM prompt/output records: `22` prompts and `22` outputs in `raw-llm-calls/`.
- Baseline LLM calls: `0`; the baseline runner is deterministic contract execution.

## Native Baseline Commands

- `PYTHONDONTWRITEBYTECODE=1 pytest -p no:cacheprovider tests/test_agentic_eval_contract.py tests/test_istara_eval_runner.py` -> 12 passed.
- `PYTHONDONTWRITEBYTECODE=1 pytest -p no:cacheprovider tests/benchmarks/test_orchestration.py -q` -> 5 passed.

## Candidate Commands

- `npm run validate` -> 4 passed.
- `npm run collect:artifacts -- --out /Users/user/Documents/Istara-main/comparison-Istara-pi/runs/20260719T125756-0300-full-replacement-candidate` -> wrote trace/output/scores artifacts and passed 8 paired deterministic scenarios for both engines.
- `npm run smoke:deepseek` -> Pi ai reached DeepSeek `deepseek-v4-pro`; 47 total tokens; USD 0.00003654 provider-reported cost.

## Raw LLM Evidence

Raw evidence is stored separately from analysis:

- Prompt/input records: `raw-llm-calls/prompts.jsonl.gz`.
- Output records: `raw-llm-calls/outputs.jsonl.gz`.
- Manifest and inspection notes: `raw-llm-calls/manifest.json`.

The files contain one record per LLM/provider call with `call_id`, `scenario_id`, `engine_path`,
provider/model, messages or prompt payload, tool schemas when sent, settings, adapter mode,
redaction metadata, raw assistant content blocks, tool-call requests, stop reason, errors,
latency, token usage, and estimated cost.

This run has 21 reconstructed deterministic Pi faux-provider records and 1 reconstructed
DeepSeek smoke record. No records were capped. No secrets, API keys, auth headers, or
production/private data are stored. Normal prompt and output text is preserved for inspection.

To inspect:

```bash
gzip -cd comparison-Istara-pi/runs/20260719T125756-0300-full-replacement-candidate/raw-llm-calls/prompts.jsonl.gz
gzip -cd comparison-Istara-pi/runs/20260719T125756-0300-full-replacement-candidate/raw-llm-calls/outputs.jsonl.gz
```

The owner-required metric dimensions are in `scores.json` under `owner_dimensions`: tool
calling, feature integration/adherence, final output quality proxy, research-spine steps,
memory load, tokens by step/total, tool calls versus quality, skills adherence, system
prompt adherence, and A2A task success/efficiency.

## Surface Results

| Surface | Verdict | Scenario |
|---|---|---|
| chat/tool loop | prototype-supported | chat.tool_loop.task_and_finding |
| plan-and-execute/task lifecycle | prototype-supported | task.plan_execute.lifecycle |
| documents/tools representative slice | prototype-supported | documents.tools.slice |
| structured outputs/core evals | prototype-supported | structured_outputs.core_eval |
| memory/RAG representative slice | prototype-supported | memory.rag.slice |
| skills representative slice | prototype-supported | skills.three_skill_slice |
| A2A representative slice | prototype-supported | a2a.debate_report.slice |
| channel lifecycle simulated slice | prototype-supported | channel.lifecycle.simulated_slice |
| model/provider routing through Pi ai | provider-smoke-supported | - |
| telemetry/token/tool-count trace capture | prototype-supported | - |
| raw prompt/output capture | prototype-supported | raw-llm-calls/*.jsonl.gz |
| real user CareNav benchmark | blocked | - |
| production route replacement | blocked | - |

## Interpretation

This is replacement evidence for a sidecar adapter path, not a claim that production Istara routes have been switched. The candidate now exercises broad representative slices through Pi-owned evented loops and canonical Istara tools, while real service adapters remain the next implementation work.
