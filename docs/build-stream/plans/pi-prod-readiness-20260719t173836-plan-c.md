# Pi replacement candidate — credential-free production-test readiness (Plan C)

## Objective and boundary

Make an evidence-backed readiness determination for the existing, opt-in Pi replacement candidate without asserting live-provider or deployment readiness. The implementation must prove the real FastAPI chat/SSE, A2A JSON-RPC, channel, Autoresearch, research-validity, Done/report, memory, steering, and benchmark seams with credential-free tests; it must not start a server, load a model, contact a provider, read a Keychain value, add a fallback secret, or commit/push.

Default Istara behaviour is the compatibility baseline. Pi is selected only by the existing explicit flag, request header, or supported metadata, and remains reversible by disabling the flag/omitting the selection. Existing auth, project scope, body-size, rate-limit, and replay protection must run before any Pi-specific persistence or telemetry.

## Planning evidence and mandatory repair priority

The current narrow candidate suite is green (`7 passed`), as is the benchmark-client header suite (`2 passed`), but the broader credential-free contract bundle is **not** green: `tests/test_research_validity_contract.py::test_static_research_artifact_constructors_stay_inside_approved_boundaries` rejects `backend/app/core/pi_replacement.py`. That file directly constructs `Nugget` and associated research-spine records, then gives a single coder/review fixture accepted statuses. This is a reproducible implementation defect, not a provider, Keychain, or runtime blocker. It is the first remediation task and prevents a readiness classification until the static boundary test and the behavioural report-gate test both pass.

Treat provider access, a nonempty Keychain item, and any owner-authorized one-target live probe as separate runtime blockers. Do not add a test credential, contact the provider, read Keychain during tests, or reclassify those blockers as an implementation failure.

## Design

Retain the candidate as a thin overlay on existing routes and services, not a parallel research workflow:

- `pi_replacement_requested()` remains the sole selection predicate. The unselected path must retain its previous model, event envelope, channel response, and Autoresearch behaviour.
- Chat may choose the Pi model only after the ordinary route has passed project access. Its SSE/tool-loop payload and error semantics remain those of the existing chat route. A missing Keychain item is represented as a content-free `missing_keychain_secret` runtime condition; it must neither reach network code nor become an embedded test credential.
- A2A records Pi telemetry only after a message is successfully authorized, project-scoped, replay-checked, and persisted. Route identifiers and telemetry fields must remain content-free (no prompt, response, raw source, endpoint, or credential).
- `pi_local` stays a local benchmark adapter registered through normal channel lifecycle APIs. It must obey paused-project/deployment/project guards and must never change external-adapter dispatch.
- The readiness probe must not construct `CodingRun`, `CodeApplication`, `ResearchEvidenceEdge`, `Task`, or approved review state directly to manufacture an accepted research artifact. Replace it with a clearly provisional fixture/contract probe, and use existing governed services for evidence-unit, coding/reliability/reconciliation, human task review, and report routing. A single-coder probe is explicitly non-reportable.
- ReasoningBank/Memento/model-skill statistics and Autoresearch can receive only project-scoped, governed process evidence. A Pi dry-run must make no background task, global policy change, production mutation, or raw-success quality promotion.

## Implementation task graph

### T1 — Baseline and contract map

Inspect the dirty Pi candidate diff and the public contracts it crosses: chat route/SSE generation, `a2a_jsonrpc`, channel creation/inbound processing, Autoresearch `/start`, research-validity/report services, ReasoningBank and steering, and `IstaraApiClient` headers. Record three separate categories:

1. implementation defects reproducible without credentials;
2. test-evidence gaps caused by direct helpers or deep mocks; and
3. runtime/owner blockers (Keychain secret, provider availability, and any later authorized live probe).

Definition of ready: the current focused Python and Node suites pass or have a named failure; no live process is started.

### T2 — Repair the governed research-spine probe

Narrow `backend/app/core/pi_replacement.py` and `tests/test_pi_replacement_candidate.py` so credential-free readiness cannot mint reportable evidence. Prefer an existing public service seam; if one is missing, add the smallest explicit test-only/provisional boundary rather than weakening the report gate.

Specifically, remove the direct `Nugget`/`CodingRun`/`CodeApplication`/`ResearchEvidenceEdge` construction from the Pi helper instead of extending the static-test allow-list. The replacement must call the existing evidence-unit, independent coding/reliability/reconciliation, and human review/report services in their prescribed order, or stop at a named provisional state when that full governed path cannot be exercised credential-free. Never synthesize accepted statuses, a perfect reliability score, or an approved reviewer merely to make the readiness probe green.

Required assertions:

- incomplete coding, reliability, reconciliation, or human Done review leaves the artifact provisional and excluded from report routing;
- only the normal accepted/reconciled plus human-approved route can produce a reportable finding and traceability handle;
- source spans/evidence units, rather than synthesized nugget text, remain the grounding source;
- memory and model-skill fanout retain project scope and evidence references but do not promote quality from a dry-run/raw tool success.

### T3 — Replace deep mocks with route/service boundary tests

Extend the focused test module (or the natural existing contract module) with in-process credential-free tests; mock only the external model transport/Keychain boundary.

- **Chat/SSE:** exercise `/api/chat` or its ASGI-level route with a selected Pi request and persisted project/session. Assert normal event order and terminal `done`, selected model and content-free span, plus a non-selected request that takes the default path. Assert missing Keychain status makes no provider/network call and exposes no secret.
- **A2A:** exercise JSON-RPC `tasks/send` at the route boundary. Assert a successful selected request produces the normal message plus Pi span. Assert malformed, unauthenticated, unauthorized/cross-project, rate-limited, and replayed selected requests return their normal error and create neither Pi span nor Pi work.
- **Channel:** start/inject/stop `pi_local` through `channel_service`, `ChannelRouter`, and `process_inbound_channel_message`. Prove lifecycle cleanup, project scope, paused/deployment rejection, and Pi response metadata. Prove an ordinary adapter/message does not receive a Pi response.
- **Autoresearch and steering:** call the scoped dry-run and steering/abort contracts. Assert dry-run has no background task/global mutation/production evidence and abort clears queued work without spilling across projects.
- **Benchmark client:** preserve constructor and per-call selection semantics. Define and test header precedence explicitly so a caller cannot silently cancel the configured Pi selection (or deliberately allow it and document that policy). Do not run the real benchmark runner.

### T4 — Documentation and generated feature artifacts

Only if the final code/test behaviour changes, update the living pages for chat overview, A2A, messaging/channel lifecycle, and compute pool. State default-off selection, security-gate ordering, content-free telemetry, credential-free scope, and the difference between test readiness and live readiness. Generate the feature-doc site/manifests via the required script; do not hand-maintain generated pages.

### T5 — Evidence-led review and readiness classification

Run focused suites, then the bounded full credential-free Python suite and the required security/docs/gate checks. Independently review only the changed surface for default-path regression, gate ordering, telemetry secrecy, research-spine validity, and test realism. Classify the result as one of:

- **credential-free production-test ready** — all acceptance checks pass;
- **implementation blocked** — a reproducible contract/test defect remains; or
- **runtime blocked** — implementation checks pass but a Keychain-backed provider/live route remains untested because no owner authorized the one-target probe.

The last classification is not a defect and must not be resolved by a fake credential or live call.

## Acceptance criteria

1. Given Pi is not selected, when each changed chat, A2A, channel, Autoresearch, and benchmark-client seam runs, then the prior Istara behaviour remains and no Pi-specific work/telemetry is emitted where applicable.
2. Given Pi is explicitly selected, when credential-free chat/SSE, A2A, local-channel, dry-run, and steering flows execute, then their existing authorization, project/replay, SSE, and lifecycle contracts are preserved and content-free Pi telemetry appears only after the applicable gate.
3. Given readiness data has not completed independent coding, reliability, reconciliation, and human Done approval, when report routing is attempted, then it is rejected/non-reportable; given the governed accepted path completes, then report routing has source/evidence traceability.
4. Given the Keychain credential/provider is unavailable, when Pi is selected, then no provider request, secret persistence, or secret log occurs and the outcome remains a named runtime blocker.
5. Given an Autoresearch Pi dry-run or memory/stat fanout, when it completes, then no background loop, global policy mutation, production mutation, or raw-success promotion occurs; project-scoped governance references remain available.
6. Given the final diff, when required focused/full credential-free checks, documentation generation, security benchmark, and architecture gates run, then they pass or any inherited failure is specifically evidenced and distinguished from this work.

## Exact verification

Run from repository root; none may start a backend/frontend server or load a model.

```bash
python -m pytest tests/test_pi_replacement_candidate.py -q
node --test tests/real_user_benchmark/lib/api-client.test.mjs
python -m pytest tests/test_chat.py tests/test_a2a_security.py tests/test_a2a_project_claims.py tests/test_channel_inbound.py tests/test_project_scope_contracts.py tests/test_autoresearch.py tests/test_steering_project_scope_contracts.py tests/test_research_validity_contract.py -q
python -m pytest tests/ -q
python scripts/security_benchmark.py --fail-on-threshold
python scripts/feature_docs.py --seed-missing --generate-site --check
compass-forge gate before --task <implementation-task>
compass-forge gate after --task <implementation-task> --summary
```

If a listed test file is absent, the implementer must use `rg --files tests | rg '<surface>'` to locate its existing equivalent and record that substitution as evidence; no invented empty suite is acceptable. The security benchmark is mandatory because this scope changes A2A/auth-adjacent telemetry and Keychain-backed model routing.

## Risks and rollback

- **Research-validity bypass:** a convenient test helper may accidentally create accepted artifacts. Mitigation: assert provisional and accepted cases separately at public service/route boundaries; never relax report gates.
- **Security-order regression:** instrumentation can run before rejection. Mitigation: negative A2A cases assert absence of span and persisted work, not merely an error response.
- **Default-path regression:** broad header/metadata parsing can select Pi unintentionally. Mitigation: explicit unselected counterpart tests for every changed entry point.
- **Hidden external side effect:** local adapter or dry-run could start work. Mitigation: assert lifecycle cleanup/no background tasks and retain local-only adapter registration.
- **Harness noise:** database teardown warnings must be reproduced, attributed (new versus inherited), and fixed if introduced; a passing test alone is insufficient evidence of clean teardown.

Rollback is surgical: revert only Pi candidate code, associated boundary tests, and regenerated docs, or disable Pi with `PI_REPLACEMENT_ENABLED=false` and omit the selection header. No schema/data migration or global configuration change is permitted, so rollback requires no data repair. Retain any independent report-gate hardening even if a Pi-only probe is removed.
