# Pi adaptation review packet

## Credential-free evidence

| Contract | Command | Outcome |
| --- | --- | --- |
| Pi fail-closed routing, governed provisional evidence, local channel, A2A telemetry | `python -m pytest tests/test_pi_replacement_candidate.py -q` | 8 passed |
| Benchmark header propagation | `node --test tests/real_user_benchmark/lib/api-client.test.mjs` | 2 passed |
| Impacted chat/A2A/channel/project seams | `python -m pytest tests/test_chat.py tests/test_a2a_security.py tests/test_a2a_project_claims.py tests/test_channel_inbound.py tests/test_project_scope_contracts.py -q` | 54 passed |
| Feature documentation | `python scripts/feature_docs.py --seed-missing --generate-site --check` | passed; 224 generated artifacts |
| Security controls | `python scripts/security_benchmark.py --fail-on-threshold` | passed; 28/28 controls, 100% |

## Runtime classification

The credential-free tests prove that an explicitly selected Pi request with no registered
Keychain target emits `pi_registration_unavailable` and makes zero provider transport calls.

On 2026-07-20, exactly one approved, bounded production-path request was sent through
`POST /api/chat` with `x-istara-agent-engine: pi`, after metadata-only confirmation that the
configured Keychain item was present. The real route returned HTTP 200 and the SSE stream
completed without errors, which confirms that the Pi-selected route registered and used the
configured DeepSeek candidate rather than taking the fail-closed missing-key path.

| Field | Approved, redaction-first evidence |
| --- | --- |
| Request count | 1 (no retry) |
| Raw prompt | `For the bounded Pi route verification, reply with exactly PI_OK and nothing else. Do not call tools.` |
| Raw SSE output | `data: {"type": "chunk", "content": "PI_OK"}` followed by `data: {"type": "done", "sources": [], "tools_used": []}` |
| Spend estimate | Conservative upper estimate: 50,000 input tokens at USD 0.435/M plus the observed two-token output at USD 0.87/M is less than USD 0.022. This is below the USD 0.50 cumulative cap for this stage. |
| Secrets | No Keychain secret, bearer token, endpoint value, provider model identifier, or unredacted authorization material was printed or retained. |

The runtime classification is now **provider-ready for this one bounded Pi production-path
probe only**. It is not a claim about broader load, tool use, or multi-turn provider behavior.

## Scope and rollback

Pi remains default-off. Remove the explicit selection or disable the Pi feature flag to return
to normal Istara routing. `pi_local` remains a local test adapter; this packet contains no
external-channel traffic or credentials.
