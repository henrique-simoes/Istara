# Pi runtime wire protocol (v1)

One JSON object per line on stdin/stdout. stdout is protocol-only; sanitized
diagnostics go to stderr. Every frame carries `v: 1`, `type`, and `session_key`
(except `hello`/`ready`/`shutdown`/`fatal`). Each side numbers its own outbound
frames with a monotonically increasing `seq`.

Limits: max line size 256 KiB, max tool arguments 64 KiB, max history messages
200, max concurrent sessions 8, max in-flight tool calls per run 4. Malformed
frames are terminal for the affected run, never silently for the process.

## Python → worker

- `hello` — `{v, type:"hello", protocol_version:1}` — first frame; worker must
  answer `ready` within the handshake timeout.
- `session.open` — `{v, type, session_key, system_prompt, history:[{role,content}],
  revision, catalog:[{name, description, parameters}], limits:{max_turns}}`
  `history` is server-persisted transcript; `revision` identifies it. A second
  `session.open` for an existing `session_key` with a different `revision`
  closes and rehydrates instead of appending.
- `provider.bind` — `{v, type, session_key, endpoint:{endpoint_id,
  provider_kind:"openai_compat"|"anthropic_compat", base_url, model, api_key,
  timeout_ms, max_retries}}` — short-lived binding; the worker must never echo,
  persist, or log `api_key` or `base_url`.
- `turn.prompt` — `{v, type, session_key, run_id, text}` — start a run.
- `turn.follow_up` — `{v, type, session_key, run_id, text}` — queue a follow-up
  user message after the active run completes.
- `turn.steer` — `{v, type, session_key, run_id, text}` — steer the active run.
- `turn.abort` — `{v, type, session_key, run_id}` — requires exactly one
  terminal ack (`run.aborted`).
- `tool.result` — `{v, type, session_key, run_id, tool_call_id, ok, result?, error?}`
  — authority response to a `tool.call`.
- `session.close` — `{v, type, session_key}`
- `shutdown` — `{v, type:"shutdown"}` — graceful exit after draining.

## Worker → Python

- `ready` — `{v, type:"ready", protocol_version:1, pi_agent_core, pi_ai}`
- `session.opened` / `session.closed` — `{v, type, session_key}`
- `run.started` — `{v, type, session_key, run_id}`
- `assistant.delta` — `{v, type, session_key, run_id, text}`
- `thinking.delta` — `{v, type, session_key, run_id, text}`
- `tool.call` — `{v, type, session_key, run_id, tool_call_id, name, arguments}`
  — one outstanding call at a time per run (sequential tool execution); the run
  pauses until `tool.result` arrives.
- `run.completed` — `{v, type, session_key, run_id, usage:{input_tokens,
  output_tokens, cost_usd}, stop_reason}` — terminal for the run.
- `run.failed` — `{v, type, session_key, run_id, error}` — terminal.
- `run.aborted` — `{v, type, session_key, run_id}` — terminal ack to abort.
- `fatal` — `{v, type:"fatal", error}` — process-level failure; the supervisor
  treats it as a crash and restarts fail-closed.

## Discipline

- Exactly one of `run.completed` / `run.failed` / `run.aborted` per `run_id`.
- Provider retry (bounded by `max_retries`) is allowed only before any visible
  output or any acknowledged tool result; acknowledged tool calls are never
  replayed.
- Disconnect, EOF, timeout, protocol violation, or authority rejection produce
  exactly one terminal event and release the session lock.
- Secrets travel only inside `provider.bind` on this private pipe.
