# Conductor instructions — complete the Istara Pi production runtime

## Outcome

Deliver the complete opt-in Pi replacement candidate, not another routing shim. The real
`@earendil-works/pi-agent-core` Agent must own production agentic turn progression, tool
execution events, follow-up turns, steering interaction, and provider invocation. Istara
must continue to own product state, authentication and project authorization, canonical
tool implementations and schemas, research-validity policy, human Done/report approval,
telemetry, persistence, and rollback.

The implementation remains on local branch `Review_pi_test`. Do not push or open a remote
pull request. Do not touch `LLMs/` or `Model_Finetuning/`.

## Confirmed audit findings the plan must close

1. The real Pi runtime is confined to `labs/pi-replacement`; production code has no Pi
   Agent Core import or invocation.
2. `POST /api/chat` currently keeps Istara's Python ReAct/native-tool loop and only pins a
   DeepSeek model through `ComputeRegistry`. A Pi header must select a Pi-owned production
   loop, not the old loop under a new label.
3. A2A currently submits through the existing service and adds Pi telemetry only. The plan
   must define and implement the Pi execution/delegation boundary without bypassing A2A
   auth, project scope, replay, rate, or report gates.
4. `pi_local` reaches the real channel router/inbound processor but returns a canned
   response. It must exercise the Pi production loop in-process. External Telegram,
   WhatsApp, Google Chat, or other live channel traffic remains forbidden.
5. Pi Autoresearch is only a dry-run telemetry envelope. Implement the governed Pi path
   needed for the experiment without allowing unreviewed production mutation or promotion.
6. Source/evidence/Done, memory/RAG/ReasoningBank/Memento/ModelSkillStats, and steering
   helpers are credential-free exercisers with no production caller and explicitly report
   `production_test_ready: false`. Integrate them through real governed services; never
   manufacture accepted research, review events, reportability, coding reliability, or
   human approval.
7. Model management is one hardcoded transient DeepSeek OpenAI-compatible node. Complete
   configurable API endpoint routing for OpenAI-compatible and Anthropic-compatible
   providers, explicit endpoint/model identity, session continuity, controlled retry/error
   behavior, and telemetry without leaking credentials or endpoint fingerprints.
8. Pi routing is not behaviorally isolated from donated compute. Existing strict model
   selection prioritizes an authorized relay/browser node when it advertises the same model
   alias. Pin API requests by endpoint/node identity or an equivalent explicit source
   constraint. Add the adversarial test: register a Pi API node and an authorized donated
   node with the same model; Pi must call only the API node, while ordinary Istara donated
   scheduling must still call the donor.
9. The final packet's Pi test count is stale (`8` versus the current `12`). Update living
   documentation and final evidence to exact post-change results.
10. The aggregate compute suite can leak async DB/telemetry work and produce
    `sqlite3.OperationalError: database is locked`. Determine causality and make the
    predefined suite deterministic; an isolated pass is not sufficient final evidence.

## Required production scenario coverage

The same 15 scenario contracts that pass in the lab must pass through the production Pi
adapter, with real Istara canonical services and test-owned persistence:

1. chat tool loop, task, finding, telemetry
2. plan-and-execute lifecycle
3. documents and tools
4. structured outputs/core evals
5. memory and RAG
6. three-skill execution and prompt adherence
7. A2A delegation and reports
8. local channel lifecycle
9. research-spine step tracking, source spans, and provisional Done gate
10. governed Autoresearch
11. ReasoningBank, Memento, and skill-memory/stat paths
12. webhook/Telegram-like lifecycle using local fixtures only
13. steering and system-prompt policy
14. benchmark/eval/simulation/real-user contract mapping
15. model routing, token/tool/cost telemetry

Do not count a faux-provider lab result as production-path evidence. Keep deterministic
lab coverage as a fast contract layer, then prove production adapter coverage separately.

## Non-negotiable Petals/donated-compute boundary

Petals-style compute donation is an independent subsystem. Preserve relay/browser node
registration, connection strings, project authorization, WebSocket request/response,
capacity, telemetry, model advertisement, and ordinary scheduler behavior. Do not route
Pi API/OpenAI/Anthropic-compatible endpoint requests through donated compute. Avoid broad
changes to donation code; express isolation at the API endpoint-routing contract and prove
both sides with negative and positive tests.

## Verification and evidence bar

The architect plans must name exact commands and a phased, reversible architecture. Final
convergence requires, at minimum:

- production Pi adapter tests for all 15 scenarios;
- `python -m pytest tests/test_pi_replacement_candidate.py -q`;
- impacted chat, A2A, channel, Autoresearch, steering, task/document/finding, memory,
  research-validity, provider-contract, model-session, compute, and project-scope tests;
- a clean aggregate compute suite, including same-model API-versus-donor isolation;
- `npm --prefix labs/pi-replacement run validate` and paired deterministic matrix;
- `npm --prefix relay test`;
- `npm --prefix tests/real_user_benchmark run check`;
- `npm --prefix tests/simulation run test:static`;
- orchestration benchmark tests and runner;
- `python scripts/feature_docs.py --seed-missing --generate-site --check`;
- `python scripts/security_benchmark.py --fail-on-threshold`;
- Compass Forge before/after gates with inherited large-file debt separated from new drift.

One or more bounded DeepSeek production-path tests may use the existing macOS Keychain
secret, with raw prompt/output/tool/token/latency/cost evidence redacted for secrets and
kept under the original cumulative USD 0.50 experiment cap. No local model loading, no
live backend/frontend server unless an existing test harness safely owns it, and no live
external channel tests.

## Planning questions the three architects must resolve

- What is the stable process/API boundary between Python Istara and the Node/TypeScript Pi
  Agent runtime, and how is lifecycle, cancellation, streaming, and failure cleanup owned?
- How are canonical Istara tools exposed to Pi without duplicating schemas or bypassing
  auth/project/research governance?
- How are OpenAI-compatible and Anthropic-compatible endpoints represented and pinned by
  identity while secrets remain in existing secure storage?
- How does the solution preserve default-off rollback and baseline Istara behavior?
- How are every scenario and every negative security/isolation case proven without live
  external channel traffic?
- How is process cleanup handled so the new CF spec can be accepted without force and the
  lifecycle file, review packet, and living feature docs agree with the implementation?

Each architect must inspect the current code and prior experiment artifacts, propose a
concrete phased design with migration/rollback and exact tests, and explicitly identify
trade-offs. Cross-judges must reject plans that merely rename the existing Python loop,
leave production Pi in the lab, rely on a model alias as endpoint identity, or treat
telemetry-only hooks as completed loop integration.
