# Pi Replacement Candidate Explainer

Updated: 2026-07-19 13:21 BRT

## Current State

The conductor created a separate git worktree for the Pi replacement candidate:

- Worktree: `/Users/user/Documents/Istara-main-pi-replacement`
- Branch: `comparison/pi-replacement-core`
- Base: `origin/main` at `fa6a1a391b5a1089690eb8fed5d179ce146ec9e9`
- Candidate code path: `labs/pi-replacement/`
- Main Istara app code: not modified
- Candidate code: uncommitted lab prototype

This is not a production route replacement yet. It is a removable lab sidecar, now expanded
from the first chat/tool smoke into a broader replacement candidate that runs representative
Istara harness slices through Pi-owned loops while Istara-shaped feature contracts stay
behind canonical tools.

Process caveat: the completed implementation was not run by the literal Build Stream
Conductor watcher/cast pipeline. A post-run compliance pass loaded the Build Stream
Conductor, Build Stream, and Compass Forge contracts and added a lifecycle ledger plus
conductor limitation record under the run folder. Treat this as partial conductor
compliance, not conductor-owned multi-model convergence.

## Files Created In The Replacement Worktree

Actual lab files, excluding ignored dependencies:

- `labs/pi-replacement/README.md`
- `labs/pi-replacement/package.json`
- `labs/pi-replacement/package-lock.json`
- `labs/pi-replacement/.gitignore`
- `labs/pi-replacement/src/canonical-tool-facade.mjs`
- `labs/pi-replacement/src/istara-pi-adapter.mjs`
- `labs/pi-replacement/src/scenario-catalog.mjs`
- `labs/pi-replacement/scenarios/collect-replacement-artifacts.mjs`
- `labs/pi-replacement/scenarios/chat-tool-loop.mjs`
- `labs/pi-replacement/test/adapter.test.mjs`

The package pins:

- `@earendil-works/pi-agent-core@0.80.10`
- `@earendil-works/pi-ai@0.80.10`

## Approach

The architecture is:

```text
Istara feature scenario
  -> CanonicalToolFacade
  -> IstaraPiAdapter
  -> @earendil-works/pi-agent-core Agent
  -> @earendil-works/pi-ai provider/model path
```

The idea is not to run Pi standalone. The lab makes Pi sit behind an Istara adapter so
future benchmark scenarios can ask: if Istara sent this workflow into Pi instead of its
native agentic core, would the same feature contract still hold?

## What Each Piece Does

### CanonicalToolFacade

`src/canonical-tool-facade.mjs` is the Istara-facing boundary. It defines canonical tools
that Pi is allowed to call:

- `tasks.create`
- `tasks.attach_document`
- `tasks.update_lifecycle`
- `documents.create`
- `findings.create`
- `memory.search`
- `memory.write`
- `plans.create`
- `skills.apply` for `competitive-analysis`, `thematic-analysis`, and `research-synthesis`
- `a2a.delegate`
- `a2a.report`
- `channels.create`
- `channels.receive`
- `channels.respond`
- `evals.emit_structured`

It validates tool arguments with Pi's schema utilities, records every call, and returns
Istara-shaped result envelopes. In this prototype, task/document/finding/plan/memory/skill
A2A/channel/eval state is in-memory lab state, not real Istara database state.

### IstaraPiAdapter

`src/istara-pi-adapter.mjs` is the replacement candidate boundary. It creates a Pi
`Agent`, gives it the canonical Istara tools, subscribes to Pi loop events, and exposes
four paths:

- `runNoModelChatToolLoop()`: deterministic no-model scenario using Pi's faux provider.
- `runNoModelScenario()`: run one Istara-derived scenario through Pi-owned Agent events.
- `runAllNoModelScenarios()`: run the full deterministic candidate slice.
- `IstaraContractBaseline`: paired deterministic contract baseline without Pi.
- `runDeepSeekProviderSmoke()`: live DeepSeek smoke through Pi's built-in DeepSeek provider.

The adapter system prompt explicitly states the intended ownership split:

- Pi owns the loop and tool execution.
- Istara owns projects, permissions, memory, tasks, findings, and telemetry policy.
- Product actions must go through canonical Istara tools.

### Scenario Runner

`src/scenario-catalog.mjs` defines eight representative Istara-derived scenarios:

- `chat.tool_loop.task_and_finding`
- `task.plan_execute.lifecycle`
- `documents.tools.slice`
- `structured_outputs.core_eval`
- `memory.rag.slice`
- `skills.three_skill_slice`
- `a2a.debate_report.slice`
- `channel.lifecycle.simulated_slice`

`scenarios/chat-tool-loop.mjs` runs:

- `--mode no-model`: proves Pi-owned loop plus canonical task/finding tools.
- `--mode no-model --scenario all --engine pi`: runs all candidate scenarios through Pi.
- `--mode no-model --scenario all --engine both`: pairs deterministic baseline and Pi.
- `--mode deepseek`: proves Pi's provider layer can reach DeepSeek `deepseek-v4-pro`.

`scenarios/collect-replacement-artifacts.mjs` writes the score-ready artifacts used by the
latest run.

### Tests

`test/adapter.test.mjs` verifies:

- canonical tool validation and result envelopes
- Pi-owned agent loop calls `tasks.create` and `findings.create`
- Istara-shaped project state is preserved in facade envelopes
- Pi emits tool execution events
- all eight representative surfaces run through Pi-owned Agent loops
- the deterministic baseline uses the same canonical contracts without Pi

## What It Proves Now

The current prototype proves:

- Pi packages install and resolve in an isolated candidate worktree.
- Pi's `Agent` can own an evented turn loop.
- Pi can execute canonical Istara tool definitions.
- The adapter can preserve Istara-shaped task/document/finding/plan/memory/skill/A2A/channel/eval envelopes.
- Deterministic paired baseline/candidate slices can be run and scored from the lab.
- Pi's DeepSeek provider can reach `deepseek-v4-pro`.
- The DeepSeek key is read from Keychain at runtime and removed from `process.env` in a
  `finally` block.

Current validation:

- `npm run validate`: passed 4 tests
- `npm run collect:artifacts -- --out comparison-Istara-pi/runs/20260719T125756-0300-full-replacement-candidate`: baseline 8/8 and candidate 8/8 deterministic scenarios
- `npm run smoke:deepseek`: passed with 47 total tokens and USD 0.00003654 provider-reported cost
- Raw LLM evidence: `raw-llm-calls/prompts.jsonl.gz`, `raw-llm-calls/outputs.jsonl.gz`,
  and `raw-llm-calls/manifest.json` in the current run folder.

Build Stream Conductor validation:

- `build-stream-lifecycle.md`: added after owner clarification with status block, decisions, and append-only ledger.
- `build-stream-conductor-compliance.md`: records loaded skill contracts, CF commands, routing registry, scorecard output, and the missing-cast block.
- `conductor.py status --brief`: blocked because `.compass-forge/conductor/cast.json` does not exist.
- `scorecard.py`: returned no model rows, confirming no literal conductor stage attribution.

## What It Does Not Prove Yet

This is not yet proof that Pi can fully replace Istara's agentic core.

Still missing:

- production chat route replacement
- real task lifecycle and DB/service adapters
- real research-spine phase execution against Istara services
- durable memory and RAG persistence
- ReasoningBank/Memento/skills behavior
- A2A debate/completion/report quality against the real service
- channel-facing turns and lifecycle behavior against real channel services
- steering queues and follow-up handling
- telemetry integration
- autoresearch governance
- broad live paired benchmarks against Istara's existing test harness
- literal Build Stream Conductor S2-S4 pipeline evidence with planner/implementer/reviewer/fixer workers and model-diverse scorecard rows
- raw prompt/output capture for future live or judge calls beyond the current deterministic faux-provider and DeepSeek smoke records

## How It Scales To Istara's Size

Because Istara is large, the test should not begin by editing every production route.
The safe path is staged:

1. Keep current Istara as baseline.
2. Keep Pi candidate in the separate worktree.
3. Grow `CanonicalToolFacade` from in-memory lab envelopes into real adapters for Istara
   services.
4. Use Istara's existing tests as the scenario source of truth.
5. Count a replacement score only when the same scenario runs through the Pi-wired adapter.
6. Record unsupported surfaces explicitly instead of silently dropping them.

Priority next work:

- if the owner requires conductor-owned evidence, start the next adapter round with `make_pipeline.py`, `make_cast.py`, and `conductor.py spawn` from a real terminal watcher
- bind `tests/simulation/scenarios/31-task-documents-tools.mjs` to real task/document adapters
- bind `tests/simulation/scenarios/71-plan-and-execute.mjs` to real task lifecycle and review state
- bind `tests/simulation/scenarios/23-memory-view.mjs` to persistent RAG/memory adapters
- bind `tests/simulation/scenarios/53-channel-lifecycle.mjs` to simulated-safe channel services
- bind `tests/simulation/scenarios/73-a2a-debate-and-reports.mjs` to real A2A services and reports

## Resource Profile

- Main run artifacts are gzipped and remain small.
- The isolated replacement worktree retains lab dependencies for repeat local smoke runs
  (`labs/pi-replacement/node_modules`, about 130 MB).
- No local models are used.
- Future broad benchmarks should remain gated by scenario count and token/cost cap.
