# Raw LLM Prompt And Output Capture Requirements

Updated: 2026-07-19 13:02 BRT

This requirement applies to the Istara vs Pi replacement candidate tests and article work.

## Owner Requirement

For every LLM call used in tests, evals, judging, or article collaboration, retain the
prompt/input and the model output so the owner can inspect actual behavior later. Aggregate
metrics are not enough.

## Required Raw Evidence Files

Each run that uses live or judged LLM calls should create either a `raw-llm-calls/`
directory or equivalent gzipped JSONL files:

- `prompts.jsonl.gz`
- `outputs.jsonl.gz`

Use one record per LLM call with a stable `call_id`.

## Prompt Record Fields

Each prompt/input record should include:

- `call_id`
- `scenario_id`
- `engine_path`: `baseline_istara`, `pi_candidate`, `judge`, or `article_collaboration`
- `provider`
- `model`
- `timestamp`
- `adapter_mode`
- `settings`: max tokens, reasoning/thinking settings, temperature if set, timeout, retry policy
- `messages` or prompt payload, including system/developer/user/tool messages that were sent
- `tool_schemas` if tool definitions were sent to the model
- `redactions`: list of any fields redacted and why

## Output Record Fields

Each output record should include:

- `call_id`
- `scenario_id`
- `engine_path`
- `provider`
- `model`
- `timestamp`
- raw assistant content blocks or text
- raw tool-call requests
- tool-call results if fed back into the model
- stop reason
- error details if failed
- latency
- token usage
- estimated cost
- `capping`: full length, retained length, cap reason, hash if output was capped

## Redaction Policy

Redact only secrets, credentials, auth headers, tokens, and production/private data that
should not be retained.

Do not redact normal prompt text, normal assistant output, tool names, tool arguments, or
scenario content needed for comparison.

Never store API keys or auth headers. DeepSeek credentials must appear only as environment
variable presence booleans such as `deepseek_key_present`.

## Storage Policy

- Prefer full text for this capped benchmark because the spend is small.
- If an output is too large, cap it and include full length, retained length, cap reason,
  and hash.
- Store JSONL as gzip.
- Do not store screenshots, binaries, local model artifacts, `dist/`, `coverage/`, `.cache/`,
  or temp dependency folders in `comparison-Istara-pi/`.

## Metrics Must Remain Separate

Raw prompts and raw outputs are evidence. Analysis belongs in:

- `scores.json`
- `benchmark-results.md`
- `coverage-matrix.*`
- article tables and notes

The required metric dimensions remain:

- tool calling
- integration with each feature, with criteria for success and adherence
- final output quality
- quality by each research-spine step
- memory load
- tokens by step and total tokens
- number of tool calls versus output quality
- skills adherence
- system prompt adherence
- A2A task success and interaction/tool-call efficiency versus output quality

