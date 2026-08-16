# Model Rounds

All live role/eval calls used DeepSeek `deepseek-v4-pro`. No local models were used.

| Round | Role | Result | Notes |
| --- | --- | --- | --- |
| 1 | provider-smoke | pass | Pi DeepSeek provider returned `pong`; raw captured. |
| 2 | planner | pass | Produced implementation tasks and acceptance checks. |
| 3 | architect | pass | Confirmed lab-only boundary and DeepSeek-only routing constraints. |
| 4 | plan-reviewer | pass | Cleared the lab-only plan for implementation. |
| 5 | code-reviewer | fail | Flagged missing evidence because the review prompt under-described existing coverage. Treated as an evidence-clarity finding. |
| 6 | remediator | pass | Required concrete artifact evidence for memory, skills, A2A, channels, prompt adherence, plan/review, and routing. |
| 7 | code-reviewer-rereview | fail | Re-review before artifacts existed; recovered raw terminal output into raw LLM files. |
| 8 | code-reviewer-rereview | pass | Final re-review after artifact bundle; no remaining blockers. |

## Raw Capture

- Prompts: `raw-llm-calls/prompts.jsonl.gz`
- Outputs: `raw-llm-calls/outputs.jsonl.gz`
- Records: 35 prompt rows and 35 output rows after final collection.

## Spend

- Previous conservative spend: $0.0801
- Added estimated spend this round: $0.01086299
- Estimated cumulative spend: $0.09096299
- Estimated remaining under $0.50 cap: $0.40903701
