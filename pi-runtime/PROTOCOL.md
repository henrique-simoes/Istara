# Pi runtime wire protocol (v1)

One JSON object per line on stdin/stdout. stdout is protocol-only; sanitized
diagnostics go to stderr. Every frame carries `v: 1`, `type`, and `seq`; every
frame except `hello`/`ready`/`shutdown` also carries `session_key`.

## Sequencing

Each side numbers its own outbound frames with a per-`session_key`
monotonically increasing integer `seq` starting at 1. Frames without a
`session_key` (`hello`, `ready`, `shutdown`) use a connection-level counter.
Each side validates inbound seq monotonicity per key; a missing, non-integer,
or non-increasing seq is a violation and the frame is not processed. A
violation on a session frame terminates the session's active run with
`run.failed{error:"protocol_seq_violation"}` (or emits that frame directly
when no run is active); a violation on a keyless frame is logged to stderr and
dropped. A seq violation is never process-fatal.

## Framing limits and chunking

Max line size is 1 MiB (`MAX_LINE_BYTES` = 1048576 bytes). Any frame whose
serialized line would exceed the bound is split by the sender into
`payload.chunk` frames:

```
{v, type:"payload.chunk", chunk_id, seq, total, data}
```

`data` slices are at most 512 KiB of UTF-8 (never splitting a code point) and
concatenate in `seq` order (1-based) to the original serialized frame JSON
without the trailing newline. The chunk `seq` field is the chunk ordering,
not the protocol-level seq — the reassembled frame carries its own protocol
seq, which the receiver validates after reassembly. The receiver bounds each
chunk set's reassembled size at 16 MiB (`MAX_REASSEMBLED_BYTES`) and the
number of concurrently open chunk sets at 64; over-bound, malformed, or
contradictory chunk frames raise a protocol error (`chunk_over_bound`,
`malformed_chunk_frame`, `chunk_reassembly_overflow`).

A poisoned inbound line — over-long line (`line_exceeds_max_bytes`), invalid
JSON (`malformed_frame_json`), or a chunk-set violation — terminates every
active run with a run-scoped `run.failed{error:<code>}` (a poisoned line
cannot be attributed finer than the pipe, and it is almost certainly the
frame an active run is waiting on). The worker keeps serving all other
sessions; it never emits a process-wide `fatal` frame for malformed input.

Other limits: max tool arguments 64 KiB, max history messages 200, max
in-flight tool calls per run 4, max concurrent sessions per worker 10. The
backend uses a lazy, bounded two-worker pool (20 concurrent sessions total).

## Python → worker

- `hello` — `{v, type:"hello", protocol_version:1, seq}` — first frame; the
  worker answers `ready` within the handshake timeout.
- `session.open` — `{v, type, seq, session_key, system_prompt,
  history:[{role,content}], revision, catalog:[{name, description,
  parameters}], limits:{max_turns,max_wall_clock_ms,max_cost_usd}}`
  `history` is server-persisted transcript; `revision` identifies it. A second
  `session.open` for an existing `session_key` with a different `revision`
  closes and rehydrates instead of appending. `limits.max_turns` is the
  session-level default turn budget. Opening beyond the session cap is
  refused with `session.open_failed{error:"session_capacity_exceeded"}`.
- `provider.bind` — `{v, type, seq, session_key, endpoint:{endpoint_id,
  provider_kind:"openai_compat"|"anthropic_compat", base_url, model, api_key,
  params?, pricing?}, params?}` — short-lived binding; the worker must never
  echo, persist, or log `api_key` or `base_url`. `endpoint.pricing` carries the
  backend-resolved model rates as USD per 1M tokens
  (`{input_per_mtok, output_per_mtok, cache_read_per_mtok?,
  cache_write_per_mtok?}`); pi-ai prices a turn's usage from them so the per-run
  `max_cost_usd` ceiling can fail closed. Unknown or negative pricing keys fail
  the bind with `provider_bind_failed:invalid_provider_pricing:<key>`. pi-ai
  prices each usage category (input/output/cache-read/cache-write) independently,
  so a real binding must price every category it can spend: a budgeted run that
  spends tokens in ANY category left at a $0 rate (an entirely unpriced binding,
  or e.g. a cache-read turn on an endpoint priced only for input/output) settles
  `run.failed{error:"cost_budget_unpriced"}` rather than a fail-open under-count.
  `params` (canonical location
  `endpoint.params`; a top-level `params` object is accepted as an alias)
  carries generation/retry knobs resolved by the backend:
  - `temperature` → pi-ai `StreamOptions.temperature`
  - `max_tokens` → `StreamOptions.maxTokens`
  - `thinking_level` → `SimpleStreamOptions.reasoning` (`"off"` omits it)
  - `timeout_ms` → `StreamOptions.timeoutMs`
  - `max_retries` → `StreamOptions.maxRetries` and the worker-side retry
    budget (see Discipline)
  Unknown or malformed params fail the bind with
  `run.failed{error:"provider_bind_failed:invalid_provider_params:<key>"}`.
- `turn.prompt` — `{v, type, seq, session_key, run_id, text, max_turns?}` —
  start a run. `max_turns` overrides the session-level `limits.max_turns`
  for this run.
- `turn.follow_up` — `{v, type, seq, session_key, run_id, text}` — queue a
  follow-up user message after the active run completes. Handler rejections
  are contained (logged to stderr); they never crash the worker.
- `turn.steer` — `{v, type, seq, session_key, run_id, text}` — steer the
  active run. Same rejection containment as `turn.follow_up`.
- `turn.abort` — `{v, type, seq, session_key, run_id}` — produces exactly one
  terminal ack (`run.aborted`).
- `tool.result` — `{v, type, seq, session_key, run_id, tool_call_id, ok,
  result?, error?}` — authority response to a `tool.call`.
- `session.close` — `{v, type, seq, session_key}`
- `shutdown` — `{v, type:"shutdown", seq}` — graceful exit after draining.

## Worker → Python

- `ready` — `{v, type:"ready", seq, protocol_version:1, pi_agent_core, pi_ai}`
- `session.opened` / `session.closed` — `{v, type, seq, session_key}`
- `session.open_failed` — `{v, type, seq, session_key, error}` — currently
  only `session_capacity_exceeded`.
- `run.started` — `{v, type, seq, session_key, run_id}`
- `assistant.delta` — `{v, type, seq, session_key, run_id, text}`
- `thinking.delta` — `{v, type, seq, session_key, run_id, text}`
- `tool.call` — `{v, type, seq, session_key, run_id, tool_call_id, name,
  arguments}` — one outstanding call at a time per run (sequential tool
  execution); the run pauses until `tool.result` arrives.
- `run.completed` — `{v, type, seq, session_key, run_id, usage:{input_tokens,
  output_tokens, cost_usd}, stop_reason}` — terminal for the run.
- `run.failed` — `{v, type, seq, session_key, run_id?, error}` — terminal.
  Protocol-scoped errors include `protocol_seq_violation`,
  `turn_budget_exceeded`, `wall_clock_budget_exceeded`, `cost_budget_exceeded`,
  `cost_budget_unpriced`, `malformed_frame_json`, `line_exceeds_max_bytes`,
  `malformed_chunk_frame`, `chunk_over_bound`, `chunk_reassembly_overflow`,
  `no_provider_bound`, `unknown_session`, `session_busy`, and
  `provider_bind_failed:<reason>`.
- `run.aborted` — `{v, type, seq, session_key, run_id}` — terminal ack to
  abort.
- `payload.chunk` — `{v, type, seq, total, chunk_id, data}` — transport for
  any oversized frame above; symmetric in both directions.

The worker never emits a process-wide `fatal` frame: every failure it can
attribute to (or isolate from) a session is reported as a run-scoped
`run.failed`, and anything else is logged to stderr.

## Discipline

- Exactly one of `run.completed` / `run.failed` / `run.aborted` per `run_id`.
- Turn budget: the worker counts `turn_start` events within a run; when the
  count exceeds the effective `max_turns` (turn.prompt override, else
  session `limits.max_turns`, else unlimited), it aborts the run and settles
  with `run.failed{error:"turn_budget_exceeded"}`.
- Provider retry, bounded by `params.max_retries`, is allowed only before the
  first visible output of an attempt (any `text_delta`, `thinking_delta`, or
  `toolcall_*` stream event) and only when pi-ai's
  `isRetryableAssistantError` classifies the failure as transient. Retried
  attempts re-issue the identical provider request; acknowledged tool calls
  are never replayed, and visible output is never duplicated.
- The backend supplies a whole-run wall-clock ceiling in
  `limits.max_wall_clock_ms`; expiry settles `run.failed{error:"wall_clock_budget_exceeded"}`.
  The cost ceiling is cumulative over the whole run: the worker sums the priced
  usage of every assistant turn (a tool loop emits several), and a run whose
  total exceeds `limits.max_cost_usd` settles
  `run.failed{error:"cost_budget_exceeded"}` rather than success. Because pi-ai
  prices each usage category independently, a real binding that spends tokens in
  any category left at a $0 rate settles
  `run.failed{error:"cost_budget_unpriced"}` when a cost budget is set, so an
  unpriced (or partially-priced) endpoint fails closed instead of reporting an
  untrusted under-count.
- Disconnect, EOF, timeout, protocol violation, or authority rejection produce
  exactly one terminal event and release the session lock.
- Secrets travel only inside `provider.bind` on this private pipe.

## Steering note

SteeringManager bindings live in the backend process that created them; they
do not propagate across backend processes or pooled workers — steering a
session only works while that process (and its owning pool worker) is alive.
