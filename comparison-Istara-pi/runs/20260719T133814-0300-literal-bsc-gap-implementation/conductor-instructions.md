# Conductor Instructions

You are running the literal Build Stream Conductor round for the Istara vs Pi full
agentic-core replacement candidate.

## Required Skills

- Load and follow Build Stream Conductor.
- Load and follow Build Stream.
- Load and follow Compass Forge.

## Workspaces

- Main Istara repo: `/Users/user/Documents/Istara-main`
- Isolated replacement worktree: `/Users/user/Documents/Istara-main-pi-replacement`
- Candidate code: `/Users/user/Documents/Istara-main-pi-replacement/labs/pi-replacement`
- Comparison artifacts: `/Users/user/Documents/Istara-main/comparison-Istara-pi`
- Current run artifacts:
  `/Users/user/Documents/Istara-main/comparison-Istara-pi/runs/20260719T133814-0300-literal-bsc-gap-implementation`

## Owner Requirements

- Build a real Pi replacement candidate, not a standalone Pi demo.
- Use Pi to own the agentic loop, model routing, tool execution envelope, and trace
  emission for candidate scenarios.
- Use Istara's existing tests/harnesses as the scenario backbone.
- Cover all scenario categories with conservative sampling under the USD 0.50 total
  DeepSeek cap.
- For skill-heavy or fanout-heavy scenarios, run at most three representative slices.
- Save all raw LLM prompts and outputs for all live test/eval/judge/article calls.
- Keep prompts/outputs inspectable; do not summarize instead of storing.
- Redact only secrets/credentials/private production data.
- Do not use local models.
- Do not modify main Istara app code.
- Do not commit unless the owner asks.

## Gap Surfaces To Implement Or Explicitly Block

- plan lifecycle and review-state representative adapter
- document attach/read/search/chat representative adapter
- persistent memory/RAG boundary and deterministic simulation
- A2A delegate/report representative adapter
- channel receive/respond/lifecycle simulation adapter
- skill/memento selection and adherence checks
- research-spine step tracking and quality scoring
- telemetry, token, cost, tool-call, and final-output metrics
- raw LLM prompt/output capture layer
- scenario runner that maps Istara harness categories to baseline and Pi candidate paths

## Raw LLM Capture Contract

For each live LLM call, write gzipped JSONL records:

- `raw-llm-calls/prompts.jsonl.gz`: scenario id, engine path, prompt/messages, tool
  schemas, system prompt, skills/memento context, model, provider, settings, timestamp.
- `raw-llm-calls/outputs.jsonl.gz`: scenario id, engine path, raw text, raw tool calls,
  stop reason, latency, usage tokens, cost estimate, errors, redaction summary.

Also write metric files:

- `scores.json`
- `coverage-matrix.json`
- `scenario-inventory.jsonl`
- `tool-call-metrics.json`
- `research-spine-step-quality.json`
- `feature-adherence.json`
- `article-notes.md`

## Stop Conditions

- Any action would modify main Istara app code.
- The DeepSeek spend cap would be exceeded.
- A secret would be printed or persisted.
- Literal Build Stream Conductor cannot start; record exact command output and ask for
  the next path instead of pretending compliance.
