# Review Instructions

Review the Pi replacement candidate as a possible Istara agentic-core replacement, not as
a standalone Pi demonstration.

## Pass Conditions

- Candidate runs make Pi own the agent/model/tool loop for the scenario.
- Main Istara app code is not modified.
- All major Istara harness categories are covered by candidate code, deterministic
  simulation, live sample, or explicit blocked reason.
- Raw prompts and raw outputs are captured for all live LLM calls.
- Metrics cover tool calling, feature adherence, final output, research-spine step
  quality, memory load, tokens by step and total, tool calls versus quality, skills
  adherence, system prompt adherence, and A2A success.
- Spend ledger stays under USD 0.50.
- No secrets are persisted.

## Review Output

Record findings in Build Stream and comparison artifacts. Findings should be actionable:
file path, scenario/category, risk, expected fix, and whether it blocks replacement
testing.
