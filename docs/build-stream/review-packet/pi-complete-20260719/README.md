# Pi adaptation review packet

## Credential-free evidence

| Contract | Command | Outcome |
| --- | --- | --- |
| All 15 production scenarios through real Pi worker and Istara services | `python -m pytest tests/pi_production -q` | 21 passed |
| Pi candidate/default-off and deleted-exerciser contracts | `python -m pytest tests/test_pi_replacement_candidate.py -q` | 13 passed |
| Pi runtime worker protocol | `npm --prefix pi-runtime test` | 4 passed |
| Benchmark header propagation | `node --test tests/real_user_benchmark/lib/api-client.test.mjs` | 2 passed |
| Impacted chat/A2A/channel/project seams | `python -m pytest tests/test_chat.py tests/test_a2a_security.py tests/test_a2a_project_claims.py tests/test_channel_inbound.py tests/test_project_scope_contracts.py -q` | 54 passed |
| Feature documentation | `python scripts/feature_docs.py --seed-missing --generate-site --check` | passed; 224 generated artifacts |
| Security controls | `python scripts/security_benchmark.py --fail-on-threshold` | passed; 28/28 controls, 100% |

## Runtime classification

The credential-free tests prove that an explicitly selected Pi request with no registered
Keychain target emits `pi_registration_unavailable` and makes zero provider transport calls.

On 2026-07-20, exactly one owner-approved, bounded request was sent through the production
`PiExecutionService` and real Pi Agent Core worker after metadata-only confirmation that the
configured credential was present. No backend/frontend server or external channel was
started. Durable evidence intentionally retains no prompt, model output, credential, base
URL, or endpoint fingerprint.

| Field | Approved, redaction-first evidence |
| --- | --- |
| Request count | 1 (no retry) |
| Terminal | `done` / `stop`; `max_retries=0`; supervisor stopped |
| Spend control | Stayed under the owner-approved USD 0.50 cumulative cap; exact content remains redacted. |
| Secrets | No Keychain secret, bearer token, endpoint value, provider model identifier, or unredacted authorization material was printed or retained. |

The runtime classification is now **provider-ready for this one bounded Pi production-path
probe only**. It is not a claim about broader load, tool use, or multi-turn provider behavior.

## Model cast and review lineage

| Role | Model | Effort |
| --- | --- | --- |
| Architect A | Fable 5 | medium |
| Architect B / independent reviewer | Sol | medium |
| Architect C | Kimi K3 | max |
| Implementer | Terra | medium |
| Fixer ladder | Kimi K3 → Terra → Opus | high → medium → xhigh |
| Run-specific rate-limit recovery | Terra | medium |

Plan C won 2–1. Kimi and Opus rate limits required the recorded Terra recovery tier; this
did not replace the independent Sol reviewer or alter the accepted architecture.

## Petals-style donation boundary

`tests/pi_production/test_same_model_donor_isolation.py` configures a private Pi API
endpoint and an authorized donated relay node with the same model alias. The Pi request
reaches only the pinned endpoint and emits zero donor frames; an ordinary Istara request in
the same test selects and is served by the donor. Pi endpoint identities never enter the
shared compute registry. Donation remains an independent Istara capability, not a Pi model
routing fallback.

## Scope and rollback

Pi remains default-off. Remove the explicit selection or disable the Pi feature flag to return
to normal Istara routing. `pi_local` remains a local test adapter; this packet contains no
external-channel traffic or credentials.
