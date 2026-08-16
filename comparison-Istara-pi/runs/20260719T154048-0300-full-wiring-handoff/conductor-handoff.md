# Conductor Handoff: Full Istara Pi Wiring Round

## Mission

Build and test a stronger Pi replacement candidate for Istara's agentic core in the isolated worktree:

`/Users/user/Documents/Istara-main-pi-replacement`

The candidate must move beyond lab-only canonical simulations. It should wire Pi into the real Istara route/service contracts wherever feasible without touching the main checkout. The goal is to make full benchmark comparison meaningful: baseline Istara vs Pi-selected candidate over the same harness backbone.

## Non-Negotiables

- Use Compass Forge as the control plane: status, next, agent-brief, impact maps, spec/tasks, gates, evidence.
- Use Build Stream / Build Stream Conductor lifecycle semantics: S0/S1 framing, role-separated architecture/review/implementation/remediation, append-only ledger, findings register, evidence before done.
- Attempt literal Build Stream Conductor only if it can start honestly. If daemon/preflight hangs or routes to unavailable model CLIs, record the blocker and continue with OpenClaw durable role lanes without claiming literal daemon convergence.
- Keep `/Users/user/Documents/Istara-main` app code untouched. Comparison artifacts may be written under `comparison-Istara-pi/`.
- Modify app code only inside `/Users/user/Documents/Istara-main-pi-replacement`.
- No commits unless the owner explicitly asks.
- No local models.
- DeepSeek only: `deepseek-v4-pro`, base URL `https://api.deepseek.com`.
- Retrieve the DeepSeek key only at runtime from macOS Keychain service `istara-pi-deepseek`, account `openclaw`; never write it to files/logs/messages.
- Hard cumulative spend cap remains USD 0.50. Latest remaining estimate is about USD 0.40564439.
- Capture raw prompts, system prompts, tool schemas, raw LLM outputs, tool calls, errors, stop reason, latency, tokens, and cost as gzipped JSONL for every live call.

## Required Role Rounds

1. Architect round
- 3 architecture lanes: production-route bridge, memory/research-spine bridge, A2A/channel/telemetry bridge.
- Each lane must cite concrete files and tests.
- Architects must propose reversible implementation behind feature flags or dependency injection.

2. Plan review / judge round
- Cross-review architecture for contract breakage, security/RBAC/auth risks, DB/SSE/event breakage, benchmark adequacy, and spend risk.
- Produce a single merged implementation plan and findings list.

3. Implementer round
- Implement the merged plan in the replacement worktree.
- Prefer small adapters/facades over wholesale rewrites.
- Add tests before or alongside changed behavior.

4. Code reviewer round
- Review diff for correctness, route/service contract fidelity, test realism, security, hidden secret leakage, and metrics capture.
- Findings must be stable IDs with severity.

5. Remediator round
- Fix Blocker/Major findings.
- Re-run targeted verification.
- Re-review until no Blocker/Major findings remain or a concrete external blocker is recorded.

6. Benchmark conductor round
- Run deterministic full inventory first.
- Run full local deterministic scenario set against baseline and candidate.
- Run live DeepSeek slices only while remaining below the cap.
- Store raw LLM evidence and separate metrics.

## Implementation Targets

Phase A: production engine boundary
- Add a reversible backend agent-engine abstraction or test-only selection point for `istara` vs `pi`.
- Candidate selection must be possible in tests without breaking existing default behavior.
- Pi path must preserve request/response envelopes for chat, tool calls, streaming events, errors, and telemetry.

Phase B: chat/tool/research-spine route bridge
- Wire `/chat` or an equivalent testable backend path to Pi in candidate mode.
- Preserve auth/project scope/history contracts.
- Map Pi events to Istara SSE/websocket/tool-call events.
- Capture research-spine step quality and final output.

Phase C: tasks/documents/findings/reports bridge
- Pi tools must call real service/route-test paths for task creation, document attach/detach/search, findings/evidence, task review, Done approval, and report gating where credential-free.
- Human Done/report gates may remain test-mode simulated only if the underlying service contracts are exercised and the limitation is recorded.

Phase D: memory/RAG/ReasoningBank/Memento/skills bridge
- Pi tools must exercise actual memory/RAG/ReasoningBank/skill service paths for representative cases.
- Skills fanout cap: at most three representative skills.
- Record memory load count, source ids, tokens, and whether memory is used as process support vs report evidence.

Phase E: autoresearch/meta-governance bridge
- Pi must drive bounded proposal/evaluation steps while preserving existing rate limits, isolation, and governance.
- No unsafe self-modification or production mutation.

Phase F: A2A/channel bridge
- Use credential-free local test adapters for A2A JSON-RPC and channel/webhook lifecycle.
- External credentials remain blocked unless provided.
- Measure A2A success as quality per interaction/tool-call count.

Phase G: telemetry/model-routing bridge
- Route Pi through DeepSeek provider in the same metrics ledger as baseline.
- Record tokens by step, total tokens, cost, latency, tool calls, output quality markers, skill adherence, prompt adherence, and errors.

Phase H: full experiment harness
- Harness backbone: `tests/benchmarks/*`, `tests/evals/*`, `scripts/run_istara_evals.py`, `tests/agentic_eval_contract.json`, `tests/real_user_benchmark/*`, `tests/simulation/run.mjs`, `tests/simulation/scenarios/*.mjs`.
- All scenarios must be inventoried.
- Oversized fanout uses conservative representatives: max three skills or equivalent representative cases.
- Each scenario state must be one of: baseline-run, pi-candidate-run, deterministic-covered, blocked-external, blocked-adapter, deferred-budget.

## Required Artifacts

Create a new run folder:

`/Users/user/Documents/Istara-main/comparison-Istara-pi/runs/<timestamp>-production-pi-wiring-benchmark/`

Required files:
- `status.md`
- `manifest.json`
- `cf-control-plane.md`
- `surface-map.md`
- `implementation-ledger.md`
- `architecture-rounds.md`
- `review-ledger.md`
- `remediation-ledger.md`
- `scenario-inventory.jsonl`
- `coverage-matrix.json`
- `feature-criteria.json`
- `benchmark-results.md`
- `scores.json`
- `tool-call-metrics.json`
- `research-spine-step-quality.json`
- `memory-load-metrics.json`
- `a2a-efficiency.json`
- `token-cost-ledger.json`
- `raw-llm-calls/prompts.jsonl.gz`
- `raw-llm-calls/outputs.jsonl.gz`
- `raw-llm-calls/manifest.json`
- `traces.jsonl.gz`
- `outputs.jsonl.gz`
- `article-notes.md`
- `academic-methodology.md`
- `cleanup-report.md`
- `final-outlook.md`

## Verification Commands

Run at minimum:
- `compass-forge status`
- `compass-forge next`
- `compass-forge gate before`/`after` where task ids exist, or `compass-forge gate after --summary`
- `npm test` or `npm run validate` under `labs/pi-replacement`
- Targeted Python tests for touched backend route/service surfaces
- `pytest tests/test_agentic_eval_contract.py tests/test_istara_eval_runner.py tests/benchmarks/test_orchestration.py -q`
- Relevant channel/A2A/memory/task tests if touched:
  `tests/test_tasks.py`, `tests/test_findings.py`, `tests/test_agents.py`, `tests/test_channels.py`, `tests/test_channel_resilience.py`, `tests/test_webhooks_security.py`, `tests/test_research_validity_contract.py`, `tests/test_agent_skill_tools.py`
- Simulation/real-user harness inventory and representative run commands.
- JSON/gzip validation for all artifacts.
- Secret scan for key-like strings.
- Storage scan for retained `node_modules`, caches, tmp, dist, coverage, and local model artifacts.

## Stop Conditions

Stop only for:
- Exceeding or about to exceed the USD 0.50 cumulative cap.
- Need for external credentials/secrets not already available.
- Destructive or irreversible action.
- Required production deploy/public external call.
- Contradictory owner instruction.
- A technical blocker repeated after three verified attempts with exact logs.

Otherwise decide, log, implement, review, remediate, and keep going.
