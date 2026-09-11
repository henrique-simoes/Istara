# Plan B — Pi production-test readiness

## Scope and design

Complete a literal, credential-free readiness review of the existing, reversible Pi candidate. The change remains opt-in (`x-istara-agent-engine` or explicit metadata/environment), uses Istara's existing route and service boundaries, and neither starts servers nor loads a live model. Separate two outcomes throughout:

- **Implementation defects:** violated route, authorization, project isolation, replay, SSE, telemetry, research-validity, lifecycle, or documentation contracts. Fix these with focused boundary tests and the smallest compatible change.
- **Runtime/credential blockers:** lack of a Keychain DeepSeek secret, a permitted network endpoint, or third-party channel credentials. Record these as not exercised; do not mask them with a synthetic “production ready” claim.

The key design decision for execution is to make “selected Pi + unavailable candidate credential” fail closed before an outbound chat attempt, with a stable SSE/HTTP error contract chosen to match existing chat error handling. The default Istara path and all non-Pi callers remain byte-for-byte behaviorally compatible. Credential-free tests may fake the model stream only at the network adapter boundary; they must run the actual FastAPI route/SSE consumer, A2A authorization/replay/project gates, and channel lifecycle rather than call helpers directly.

## Task breakdown

1. **Map and baseline the real seams.** Inspect `chat.py`, `a2a.py`, `autoresearch.py`, channel lifecycle/inbound processing, `pi_replacement.py`, config/keychain resolution, telemetry persistence, Done/report routing, Research Spine persistence, ReasoningBank/Memento/stat fanout, benchmark API client, and feature documentation. Capture current targeted test and gate results; classify every existing test as route-boundary, service-boundary, or synthetic helper coverage.

2. **Harden Pi selection and chat/SSE behavior.** Keep selection explicitly opt-in and normalize header/metadata inputs. Ensure a selected Pi chat cannot silently continue toward a network model when the Keychain secret/node registration is unavailable. Preserve normal SSE tool-call/chunk/done behavior when a credentialed candidate is available, and preserve the baseline model and output path when Pi is not selected. Add route-level tests using the actual `chat()` response iterator plus only a fake LLM transport.

3. **Prove side-route gating and observability.** At the actual A2A JSON-RPC entry point, demonstrate that auth, request-size/rate/replay, and project-scope rejections occur before Pi telemetry; on accepted `tasks/send`, assert a project-scoped span with no secret/base URL. For `pi_local`, test create/start/inject/stop through `channel_service`, `ChannelRouter`, and `process_inbound_channel_message`; demonstrate non-Pi metadata yields the normal behavior and that the adapter cannot cross project scope.

4. **Validate governed research and improvement fanout.** Exercise a credential-free fixture project through source → evidence units → coding/reliability/reconciliation → accepted code application/edges → approved Done task → report routing. Verify traceability refers to preserved source spans and no reportable result is produced before approval. Prove ReasoningBank/Memento/skill-stat records remain project-scoped and carry evidence/governance state. Keep Autoresearch restricted to the existing Pi dry-run response: no background task, live mutation, promotion, or report evidence. Verify steering interruption clears only the selected agent/project queue.

5. **Verify benchmark propagation and documentation.** Test the real-user benchmark client carries `x-istara-agent-engine: pi` only when configured, including its chat and relevant A2A request constructors, without changing default headers. Update affected living feature docs and regenerate/check the feature-doc manifest if observable behavior changes. Do not modify dated lifecycle/history documents except the conductor-owned lifecycle entries.

6. **Run release-quality verification and classify readiness.** Run focused Python and Node suites, security benchmark (because auth/keychain/agentic routing surfaces are involved), feature-doc generation/check if docs changed, the full credential-free backend suite appropriate to the touched layer, and CF post-change gate. Publish a matrix: verified credential-free contracts, intentionally unexercised credential/runtime dependencies, and any remaining implementation failures. Do not start a backend/frontend server, invoke a real DeepSeek request, or load models.

## Acceptance criteria

| ID | Given / When / Then | Proof |
|---|---|---|
| AC-1 | Given Pi is not explicitly selected, when chat/A2A/channel/benchmark requests run, then default Istara routing and headers are unchanged. | Focused baseline-vs-Pi-negative tests. |
| AC-2 | Given Pi is selected without a Keychain credential, when chat begins, then it fails closed before an outbound model call and exposes the documented error envelope without persisting a secret. | Route-level SSE/HTTP test with transport spy and missing-secret fixture. |
| AC-3 | Given a selected, transport-faked Pi chat, when it emits native or text tool calls, then SSE tool/chunk/done semantics and persistence are preserved and telemetry has project/model/route metrics only. | Actual chat route/body-iterator tests plus telemetry query. |
| AC-4 | Given A2A requests that fail auth/replay/project gates, when Pi metadata is supplied, then no Pi span exists; accepted requests create only project-scoped telemetry after the gates. | JSON-RPC boundary tests for deny and accept cases. |
| AC-5 | Given a `pi_local` instance, when started/injected/stopped, then normal channel lifecycle/inbound persistence runs, its response is Pi-only, and project isolation holds. | Service/router/inbound integration test. |
| AC-6 | Given the readiness fixture, when it creates research artifacts, then reportable findings pass source evidence, coding/reliability/reconciliation, review, and Done/report gates; memory/stat fanout is project-scoped. | Database assertions plus traceability and negative pre-approval assertion. |
| AC-7 | Given Pi Autoresearch dry-run or steering probe, when invoked, then no background/live mutation/promotion occurs and interruption is scoped. | Actual route/service tests. |
| AC-8 | Given a real-user benchmark client configured for Pi, when it sends chat/A2A calls, then the opt-in header is propagated; absent configuration emits no Pi header. | Node unit tests with captured fetch requests. |
| AC-9 | Given all credential-free verification passes, when readiness is reported, then it names credential/runtime blockers separately and makes no deployment/live-model claim. | Review matrix, command evidence, security benchmark, and CF gate. |

## Exact verification sequence

Run from `backend/` where required, never starting an application server:

```bash
pytest -q tests/test_pi_replacement_candidate.py
pytest -q tests/test_security_benchmark.py tests/test_validation_project_scope.py tests/test_transport_headers.py
(cd tests/real_user_benchmark && npm test -- --test-name-pattern='Pi|agent engine|api client')
python scripts/security_benchmark.py --fail-on-threshold
python scripts/feature_docs.py --seed-missing --generate-site --check
pytest -q
compass-forge gate after --task <implementation-task> --summary
```

Before broad `pytest -q`, run the route/service subset selected from CF impact and record why any unavailable optional dependency is excluded. For each new finding, capture a minimal adversarial test: missing credential must observe zero transport calls; denied A2A must observe zero telemetry writes; non-Pi channel input must observe no Pi response. Record all commands as Compass Forge evidence and attach the final readiness matrix to the review task.

## Risks and rollback

- **Credential availability is not a code defect.** Missing Keychain material or network authorization remains a named release blocker for live Pi testing. Rollback: leave Pi disabled/remove the opt-in header; no default routing changes.
- **Fail-closed behavior can alter callers that previously relied on fallback.** Rollback: revert only the Pi-selected guard and retain the tests; baseline requests are untouched.
- **Fixture data can overstate Research Spine proof.** Mitigate with a negative pre-approval/report test and explicit “credential-free contract proof” labeling. Rollback: delete only test-scoped database records through fixture teardown, never production data.
- **Telemetry can leak sensitive routing data.** Assert no key, base URL, or request secret appears in spans/logs. Rollback: remove the Pi telemetry hook while retaining gate ordering.
- **Full-suite/environment failures can be unrelated.** Preserve focused evidence, report the exact failing command and dependency, and do not reclassify a runtime limitation as a passing implementation result.

## Definition of done / handoff

The implementation reviewer receives: the changed-surface diff, focused boundary evidence, full credential-free suite and security/gate results, feature-doc verification if applicable, a readiness matrix, and any unresolved runtime blockers. Blocker/Major findings become separate remediation tasks; ship only after independent re-review finds no open implementation Blocker/Major items.
