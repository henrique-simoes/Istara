# Run Status

Run: `20260719T114723-0300-pi-provider-setup`

Status: complete

## Constraints

- Writes stayed under `comparison-Istara-pi/`.
- Istara application code was not modified.
- No local models were used or loaded.
- DeepSeek key was read from macOS Keychain only inside the smoke process.
- Only the approved Pi provider smoke was run. This is package-boundary preflight evidence,
  not the replacement test or replacement score.
- Full replacement metrics remain gated on an isolated Istara worktree or sidecar harness
  that wires Pi into Istara feature contracts, plus owner token/cost caps for live runs.

## Milestones

- [x] Read required comparison plan, DeepSeek config, cleanup runbook, article protocol, and prior smoke artifacts.
- [x] Ran Compass Forge read-only orientation.
- [x] Created a fresh run folder.
- [x] Installed `@earendil-works/pi-ai@0.80.10` in a temporary run-local dependency folder.
- [x] Located Pi's native `deepseekProvider()` and `deepseek-v4-pro` model catalog entry.
- [x] Ran one minimal Pi provider smoke to DeepSeek through `models.completeSimple()`.
- [x] Captured sanitized latency, token usage, model, adapter mode, and provider configuration evidence.
- [x] Gzipped trace/output JSONL artifacts.
- [x] Deleted the temporary dependency tree and checked retained storage.
- [x] Recorded Compass Forge/context mapping scope for this provider-only run.

## Compass Forge Context Scope

Detailed scope note: `cf-context-scope.md`.

Compass Forge status/next/agent-brief/classify were used for orientation. The compact
agent brief timed out with structured `fallback_authorized: true`, so the follow-up used
focused `intelligence impact` and `context --pack-type lite` commands.

For this provider smoke, the relevant mapped surfaces are limited to comparison artifacts,
Pi package/provider boundary, secret handling, cleanup, and wording that prevents
over-claiming the result. Compass Forge also identified future replacement-harness inputs
such as compute/provider routing, agent lifecycle, tool/skill execution, RAG/memory,
A2A/channel behavior, and product feature contracts. Those Istara surfaces were not wired,
edited, or executed in this run.

Replacement scoring must use Istara's existing coverage backbone: `tests/benchmarks/`,
`tests/evals/`, `scripts/run_istara_evals.py`, `tests/agentic_eval_contract.json`,
`tests/real_user_benchmark/`, and `tests/simulation/scenarios/`.

## Current Outcome

Pi provider smoke passed. `@earendil-works/pi-ai@0.80.10` resolved from npm without a Pi
monorepo clone, and its built-in DeepSeek provider reached `deepseek-v4-pro` with HTTP 200.
The smoke used Pi library adapter mode `library_builtin_deepseek_provider`, requested high
reasoning with thinking enabled, and returned `pong`.

Package-boundary preflight result: pass. Replacement score: not collected.

Next gate: build a separated Istara worktree or sidecar replacement harness where Pi is wired
as the candidate engine for Istara agentic loops through adapters/canonical tools. Live paired
metrics from that harness still require an owner token/cost cap and scenario count.
