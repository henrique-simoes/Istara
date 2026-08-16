# Full Replacement Candidate Notes

Run: `runs/20260719T125756-0300-full-replacement-candidate/`

## Result

The isolated worktree now contains a real sidecar candidate, not only provider smoke. Pi
owns the deterministic Agent loops for eight representative Istara harness-derived
scenario families while Istara-shaped contracts remain behind canonical tools.

## Evidence

- Baseline native tests: `tests/test_agentic_eval_contract.py` and
  `tests/test_istara_eval_runner.py` passed 12/12.
- Baseline native orchestration benchmark: `tests/benchmarks/test_orchestration.py`
  passed 5/5.
- Candidate adapter tests: 4/4 passed.
- Paired deterministic contract run: baseline 8/8, candidate 8/8.
- Live provider smoke through Pi ai and DeepSeek `deepseek-v4-pro`: passed, 47 tokens,
  USD 0.00003654 provider-reported cost.
- Raw LLM evidence: `raw-llm-calls/prompts.jsonl.gz` and
  `raw-llm-calls/outputs.jsonl.gz` contain 22 prompt/output records, kept separate from
  `scores.json` and article interpretation.

## Article Framing

This supports a cautiously positive engineering finding: Pi can act as the owner of a
sidecar agentic loop across representative Istara contract slices. It does not yet support
a full-replacement conclusion because the current candidate uses in-memory envelopes
instead of real Istara DB/service adapters for tasks, documents, memory/RAG, skills, A2A,
and channels.

Process caveat: the implementation was not run by the literal Build Stream Conductor
watcher/cast pipeline. A post-run compliance pass loaded the conductor, Build Stream, and
Compass Forge contracts and added a ledger/scorecard limitation record, but conductor-owned
model-diverse planner/implementer/reviewer/fixer evidence is absent. Article claims should
describe this as a robust isolated candidate with partial conductor compliance, not as a
conductor-converged pipeline result.

Raw-evidence caveat: deterministic Pi faux-provider records are reconstructed from fixed
scenario fixtures, while the DeepSeek smoke record is reconstructed from the fixed prompt
and live smoke artifact without another live call. The native baseline slices used in this
run did not perform LLM calls.
