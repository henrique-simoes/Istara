# Results Notes

Empirical results are now available for a robust isolated sidecar candidate, but not yet
for full production route replacement.

Current evidence:

- DeepSeek key presence was checked without writing the key value.
- The Istara-compatible OpenAI base-url smoke result is stored in
  `runs/20260719T105618-0300-deepseek-conductor/logs/deepseek-openai-compatible-smoke.json`.
- That smoke passed with status 200, 2163 ms latency, and 36 total tokens.
- The Pi provider smoke result is stored in
  `runs/20260719T114723-0300-pi-provider-setup/logs/pi-provider-deepseek-smoke.json`.
- That smoke passed with status 200, 2787 ms latency, and 94 total tokens.
- These smokes are not replacement results. Full comparative results require a separated
  Istara worktree or sidecar harness that runs Istara feature contracts through a Pi-owned
  engine path.
- Provider/setup passes are package-boundary preflight only. Replacement scores must be
  backed by Istara harness coverage, not standalone Pi/provider execution.

Latest full-candidate run:

- Run folder:
  `runs/20260719T125756-0300-full-replacement-candidate/`.
- Candidate code:
  `/Users/user/Documents/Istara-main-pi-replacement/labs/pi-replacement`.
- Baseline native contract/eval tests passed: 12/12.
- Baseline native orchestration benchmark passed: 5/5.
- Candidate adapter tests passed: 4/4.
- Paired deterministic contract scenarios passed: baseline 8/8, candidate 8/8.
- Pi-owned candidate loops covered chat/tool loop, plan-and-execute, documents/tools,
  structured outputs, memory/RAG, three skills, A2A, channel lifecycle, and telemetry.
- Pi ai live provider smoke reached DeepSeek `deepseek-v4-pro` with 47 tokens and
  USD 0.00003654 provider-reported cost.

Article claim boundary:

- Supported: "A Pi-owned sidecar can execute representative Istara agentic contracts
  through canonical adapters in deterministic paired tests."
- Not supported yet: "Pi fully replaces Istara's production agentic core." Real
  DB/service adapters and broader live scoring remain required.
