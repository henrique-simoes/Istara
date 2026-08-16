# Conductor Instructions

You are the durable OpenClaw conductor for the next Istara vs Pi implementation round:
build a stronger Pi replacement candidate that bridges Istara's real agentic-loop
touchpoints so full testing can happen later.

## Mandatory Method

1. Load and follow:
   - `/Users/user/Documents/Skills/build-stream-conductor/SKILL.md`
   - `/Users/user/Documents/Skills/build-stream/SKILL.md`
   - `/Users/user/Documents/Skills/compass-forge/SKILL.md`
2. Use Compass Forge thoroughly for dependency and test-impact mapping.
3. Continue from existing lifecycle/spec state when useful:
   - Worktree: `/Users/user/Documents/Istara-main-pi-replacement`
   - Lifecycle: `docs/build-stream/2026-07-19-pi-agentic-core-replacement.md`
   - Existing spec: `CF-SPEC-1`
   - Previous BSC cast prefix: `pi-repl-20260719T133814`
4. If the literal BSC daemon remains blocked, record that exactly and run the role rounds
   through OpenClaw durable sessions instead. Do not pretend daemon convergence.

## Workspaces

- Main Istara repo: `/Users/user/Documents/Istara-main`
- Isolated replacement worktree: `/Users/user/Documents/Istara-main-pi-replacement`
- Candidate code: `/Users/user/Documents/Istara-main-pi-replacement/labs/pi-replacement`
- Run folder:
  `/Users/user/Documents/Istara-main/comparison-Istara-pi/runs/20260719T145107-0300-real-istara-loop-bridge`

## Implementation Goal

Build the bridge candidate so Pi can be tested as a real replacement candidate for
Istara's agentic loop. This means:

- Pi owns the loop/model/tool execution for candidate scenarios.
- Istara product features remain represented through canonical tools/adapters.
- The harness can run representative Istara workflows through baseline and Pi candidate
  paths.
- Unsupported surfaces are explicit blocked reasons, not silent omissions.

## Required Mapping

Use Compass Forge and source inspection to map:

- `backend/app/api/routes/chat.py`
- `backend/app/api/routes/autoresearch.py`
- planning/review-state services and tests
- task/finding/document services and tests
- memory/RAG/ReasoningBank/Memento/skill services and tests
- A2A/delegation/report services and tests
- channel/webhook/Telegram-like lifecycle services and tests
- steering/system-prompt/telemetry services and tests
- `tests/benchmarks`, `tests/evals`, `tests/simulation/scenarios`,
  `tests/real_user_benchmark`, and `tests/agentic_eval_contract.json`

## Candidate Code To Add Or Extend

Prefer lab-only code under `labs/pi-replacement`:

- `src/istara-surface-map.*`
- `src/istara-service-bridge.*`
- `src/scenario-catalog.*`
- `src/canonical-tool-facade.*`
- `src/raw-llm-capture.*`
- `src/istara-pi-adapter.*`
- scenario runner and tests that prove all major surfaces are represented

## Metrics And Raw Evidence

Save all live LLM prompts and raw outputs:

- `raw-llm-calls/prompts.jsonl.gz`
- `raw-llm-calls/outputs.jsonl.gz`

For each live call include scenario id, engine path, system prompt, messages, tool
schemas, skill/memory context, provider/model/settings, output text, tool calls, errors,
stop reason, latency, tokens, cost, and redaction summary.

Also produce:

- `surface-map.md`
- `implementation-ledger.md`
- `coverage-matrix.json`
- `scenario-inventory.jsonl`
- `scores.json`
- `tool-call-metrics.json`
- `research-spine-step-quality.json`
- `feature-adherence.json`
- `benchmark-readiness.md`
- `final-outlook.md`

## Budget And Safety

- DeepSeek only: `deepseek-v4-pro`.
- No local models.
- Total cumulative cap remains USD 0.50.
- Prior conservative spend is USD 0.09096299; remaining cap is about USD 0.40903701.
- Retrieve DeepSeek key only at runtime from Keychain:
  `security find-generic-password -a openclaw -s istara-pi-deepseek -w`
- Never print or store the key.
- Do not modify main Istara app code.
- Do not commit.

## Completion Bar

Complete when:

- The bridge candidate covers every major agentic surface with runnable lab adapters or
  explicit blocked reasons tied to real Istara code/tests.
- Candidate tests pass.
- Raw prompt/output capture validates.
- Comparison artifacts and Build Stream/academic notes are updated.
- Remaining production gaps are listed precisely enough to decide next steps.
