# Benchmark Results

Generated: 2026-07-19T19:03:22.187Z

## Summary

- Scenarios: 15
- Baseline deterministic pass/fail: 15/0
- Pi candidate pass/fail: 15/0
- Pi-owned-loop scenarios: 15
- Candidate tool calls: 56
- DeepSeek added spend estimate: $0.00650856

## Coverage

- tool_calling: covered (3/3)
- feature_integration_adherence: covered (15/15)
- final_output: covered (15/15)
- research_spine_step_quality: covered (3/3)
- memory_load: covered (2/2)
- reasoning_bank_memento: covered (1/1)
- autoresearch_governance: covered (1/1)
- tokens_by_step_total: covered (15/15)
- tool_calls_vs_output_quality: covered (15/15)
- skills_adherence: covered (1/1)
- system_prompt_adherence: covered (15/15)
- a2a_success: covered (1/1)
- channels: covered (2/2)
- webhook_telegram_lifecycle: covered (1/1)
- documents: covered (2/2)
- plan_review_state: covered (1/1)
- steering: covered (1/1)
- benchmark_contracts: covered (1/1)
- model_routing: covered (2/2)
- telemetry: covered (3/3)
- real_surface_map: covered (15/15)

## Limitation

The literal local Build Stream Conductor watcher was not launched because the active cast routes to Codex CLI probes/workers that previously hung in OpenClaw and violate the DeepSeek-only model constraint for this round. The run proceeds through the recorded OpenClaw durable fallback with DeepSeek role lanes and CF evidence.
