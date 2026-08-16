# Raw LLM Capture Contract

This run must save prompts and raw outputs for every LLM call used in tests, evals,
judging, or article collaboration.

Required files, preferably gzipped JSONL:

- `raw-llm-calls/prompts.jsonl.gz`
- `raw-llm-calls/outputs.jsonl.gz`
- `raw-llm-calls/manifest.json`

One record per call, joined by `call_id`.

Prompt records must include scenario id, engine path, provider/model, timestamp, settings,
messages or payload, tool schemas if sent, adapter mode, and redaction metadata.

Output records must include raw assistant text/content blocks, raw tool-call requests,
tool results if fed back, stop reason, errors, latency, token usage, estimated cost, and
capping metadata when a body is truncated.

Redact only secrets, credentials, auth headers, tokens, and production/private data. Keep
normal prompt text and normal assistant output inspectable.

Never store API keys. Record only booleans such as `deepseek_key_present`.

Metrics and interpretation must stay separate in `scores.json`, `benchmark-results.md`,
coverage files, and article notes.

Current run status:

- `prompts.jsonl.gz`: 22 records.
- `outputs.jsonl.gz`: 22 records.
- Pi deterministic faux-provider calls: 21 reconstructed records from fixed scenario fixtures.
- Pi DeepSeek smoke call: 1 reconstructed record from fixed prompt, prior raw capture, and `live-provider-smoke.json`.
- Baseline Istara deterministic contract runner: 0 LLM calls.
- Missing raw capture: none identified for current-run LLM calls.
- Capping: none.
