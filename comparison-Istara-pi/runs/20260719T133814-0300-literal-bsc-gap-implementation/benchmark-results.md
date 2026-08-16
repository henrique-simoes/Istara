# Benchmark Results

Generated: 2026-07-19T17:06:13.896Z

## Summary

- Scenarios: 10
- Baseline deterministic pass/fail: 10/0
- Pi candidate pass/fail: 10/0
- Pi-owned-loop scenarios: 10
- Candidate tool calls: 36
- DeepSeek added spend estimate: $0.01086299

## Coverage

- tool_calling: covered (3/3)
- feature_integration_adherence: covered (10/10)
- final_output: covered (10/10)
- research_spine_step_quality: covered (3/3)
- memory_load: covered (1/1)
- tokens_by_step_total: covered (10/10)
- tool_calls_vs_output_quality: covered (10/10)
- skills_adherence: covered (1/1)
- system_prompt_adherence: covered (10/10)
- a2a_success: covered (1/1)
- channels: covered (1/1)
- documents: covered (2/2)
- plan_review_state: covered (1/1)
- model_routing: covered (1/1)
- telemetry: covered (1/1)

## Limitation

The literal local Build Stream Conductor watcher was not launched because the active cast routes to Codex CLI probes/workers that previously hung in OpenClaw and violate the DeepSeek-only model constraint for this round. The run proceeds through the recorded OpenClaw durable fallback with DeepSeek role lanes and CF evidence.
