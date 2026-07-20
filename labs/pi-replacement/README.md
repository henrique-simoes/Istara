# Istara Pi Replacement Lab

Lab-only prototype for wiring Pi as the candidate owner of Istara's agentic
management core.

This folder is intentionally isolated from production backend/frontend routes.
It demonstrates the removable boundary:

```text
Istara harness-derived scenario
  -> scenario catalog
  -> CanonicalToolFacade
  -> IstaraPiAdapter
  -> @earendil-works/pi-agent-core Agent
  -> @earendil-works/pi-ai provider/model path
```

## Scenarios

- `npm run smoke:no-model`: deterministic no-model chat/tool-loop scenario. Pi's
  `Agent` owns the loop, event stream, and tool execution; Istara-owned canonical
  tools enforce schemas, policy, and result envelopes.
- `npm run smoke:all-no-model`: runs all representative candidate scenarios through
  Pi-owned Agent loops.
- `npm run paired:no-model`: runs the deterministic Istara contract baseline and Pi
  candidate against the same canonical scenario contracts.
- `npm run collect:artifacts -- --out <dir>`: writes compact `traces.jsonl.gz`,
  `outputs.jsonl.gz`, `scenario-inventory.jsonl`, `coverage-matrix.json`, `scores.json`,
  `paired-run-summary.json`, `surface-map.md`, focused metric files, markdown reports,
  and raw LLM evidence under `raw-llm-calls/`.
- `npm run smoke:deepseek`: minimal DeepSeek provider smoke through Pi's built-in
  `deepseekProvider()` and `deepseek-v4-pro`. The key is read at runtime from
  macOS Keychain and is never printed or stored.
- `npm run role-rounds:deepseek -- --out <dir>`: bounded DeepSeek-only planner,
  architect, plan-reviewer, and code-reviewer lanes with raw prompt/output capture.

Current representative scenario families:

- chat/tool loop
- plan-and-execute/task lifecycle
- documents/tools
- structured outputs/core evals
- memory/RAG
- three skills: `competitive-analysis`, `thematic-analysis`, `research-synthesis`
- A2A delegation/reporting
- channel lifecycle simulated turn
- research-spine step tracking with source spans and provisional Done-gate status
- Autoresearch governed experiment proposal and sandbox measurement
- ReasoningBank and Memento process-memory/skill-memory paths
- webhook/Telegram-like lifecycle with signature and replay envelope
- steering queue and system-prompt policy audit
- benchmark/eval/simulation/real-user contract mapping
- DeepSeek model routing and telemetry metric emission

## Secret Contract

The live smoke retrieves the key only with:

```bash
security find-generic-password -a openclaw -s istara-pi-deepseek -w
```

Only `DEEPSEEK_API_KEY` is set in the process that needs it. Artifacts should
record only `deepseek_key_present`.

## Raw LLM Capture

`collect:artifacts` writes:

- `raw-llm-calls/prompts.jsonl.gz`
- `raw-llm-calls/outputs.jsonl.gz`
- `raw-llm-calls/manifest.json`

The deterministic faux-provider records are reconstructed from the scenario catalog,
because those provider responses are fixed test fixtures. Live DeepSeek provider and
role-lane calls append direct records to the same gzip files when run with `--out`. The
baseline contract runner uses no LLM. Any future live or judging call must be added to
these raw files, preserving normal prompt/output text while excluding secrets,
credentials, auth headers, and huge binary payloads.
