# Evaluation Lab Plan: Istara ReAct vs Pi

```yaml
item: comparison-Istara-pi
branch: compass-forge/complete-health-pass
cf: { mode: "status/brief/context/impact mapping used; state stale/unregistered limitation recorded" }
phase: "Phase 0 - lab design"
stage: S3-full-replacement-candidate
status: robust-isolated-candidate-complete-real-service-adapters-next
blocked_on: "full production replacement still requires real Istara service adapters for DB-backed tasks/documents/memory/skills/A2A/channels and broader live scoring; literal Build Stream Conductor evidence requires a fresh watcher/cast run"
last: { agent: "full-replacement-candidate-subagent", at: "2026-07-19T13:15:00-03:00", ledger: L-13 }
next_action: "Implement real service/RPC adapters in the isolated worktree so scenario 31/53/71/73 and selected eval cases call Istara services through the Pi-owned loop instead of in-memory envelopes."
```

## Frame

The goal is to create evidence for whether Pi can replace Istara's full agentic management core while all Istara product features remain available through Pi-facing adapters and canonical tools.

The lab compares complete behavior, not only APIs. The comparison must track tool calls, memory behavior, feature integration, prompt and skill adherence, final research quality, A2A efficiency, channel integration, model routing, and the quality of each research-spine step.

## Non-Goals

- No production code changes in this round.
- No live cloud LLM calls beyond the approved smallest DeepSeek smoke until the owner
  confirms benchmark budget.
- No local model loading.
- No large persistent clones or heavy benchmark artifacts.
- No conclusion that Pi is better or worse until evidence exists.

## Decision Log

DEC-1 | 2026-07-19 | S0-frame | owner
Context: The owner wants three architects to prepare a durable plan and lab for comparing Istara to Pi.
Decision: Planning-only conductor round; all artifacts stay in `comparison-Istara-pi/`; tests wait for cloud LLM instructions.
Why: This preserves Istara code while creating a reusable, auditable evaluation plan.

DEC-2 | 2026-07-19 | S1-plan | katish-main
Context: The org has five pi-named repositories, but the owner said three repos.
Decision: Superseded. The initial pass treated `pi`, `pi-review`, and `pi-chat` as the primary runtime/code comparison set.
Why: `pi` README points to `pi-chat` for chat automation, `pi-review` is an active review extension, and `pi-website` is archived.

DEC-3 | 2026-07-19 | S1-plan | owner + katish-main
Context: The owner clarified that the intended "three" are not three repositories, but three core packages inside the `earendil-works/pi` monorepo.
Decision: The primary comparison targets are `@earendil-works/pi-coding-agent` (`packages/coding-agent`), `@earendil-works/pi-agent-core` (`packages/agent`), and `@earendil-works/pi-ai` (`packages/ai`). `pi-review` and `pi-chat` become optional ecosystem references only.
Why: These are the core harness/runtime/model-management packages relevant to a loose dependency strategy for Istara. Extension repos can inform best practices but should not define the replacement experiment.

DEC-4 | 2026-07-19 | S1-plan | owner + katish-main
Context: The owner clarified that the intended evaluation is not conservative augmentation. The desired hypothesis is that Pi could replace all of Istara's agentic management core.
Decision: The lab's primary hypothesis is full agentic-core replacement: Pi should be tested as the owner of ReAct/tool loops, planning/execution orchestration, model management, SDK/process integration, session/harness mechanics, and channel-facing agent integrations. Istara features remain, but they are reconnected through adapters/canonical tools rather than preserving Istara's current agentic engine.
Why: This matches the migration goal: Pi becomes an independently updateable dependency or sidecar for agentic behavior while Istara keeps product features, data, authorization, and user-facing contracts.

DEC-5 | 2026-07-19 | S1-plan | owner + katish-main
Context: The owner approved DeepSeek as the cloud LLM for testing and requested a durable OpenClaw job that keeps reporting until the lab/article work lands.
Decision: Use DeepSeek model `deepseek-v4-pro`, base URL `https://api.deepseek.com`, high reasoning effort, and thinking enabled where supported. Store only the environment-variable contract (`DEEPSEEK_API_KEY`) in repo artifacts, not the literal key.
Why: This enables cloud-only testing without local models while preserving secret hygiene and reproducible run manifests.

DEC-6 | 2026-07-19 | S2-smoke | owner + pi-provider-smoke-subagent
Context: The owner approved Pi dependency setup/local checkout enough to run the Pi provider smoke, but not unlimited benchmark spending.
Decision: Use a temporary npm install of `@earendil-works/pi-ai@0.80.10` and Pi's built-in DeepSeek provider for one minimal `deepseek-v4-pro` smoke; delete dependency artifacts before finish.
Why: This proves Pi provider viability with the smallest setup and preserves the benchmark budget gate.

DEC-7 | 2026-07-19 | S2-smoke | owner + pi-provider-smoke-subagent
Context: The provider smoke passed, but the owner clarified that standalone Pi/provider
execution must not be treated as the replacement evaluation.
Decision: Treat the Pi provider smoke as prerequisite dependency/provider evidence only.
The next evaluation gate is an isolated Istara worktree or sidecar harness that wires Pi as
the candidate replacement for Istara agentic loops through adapters and canonical tools.
Why: The intended architecture tests full Istara feature behavior through a Pi-owned engine
path while keeping the main Istara worktree untouched.

DEC-8 | 2026-07-19 | S2-smoke | owner + pi-provider-smoke-subagent
Context: The owner clarified that any Pi provider/setup result should be framed as
package-boundary preflight only.
Decision: Replacement scoring must use the existing Istara coverage backbone:
`tests/benchmarks/`, `tests/evals/`, `scripts/run_istara_evals.py`,
`tests/agentic_eval_contract.json`, `tests/real_user_benchmark/`, and
`tests/simulation/scenarios/`.
Why: The replacement question is whether Pi can run Istara feature behavior through Istara's
contracts, not whether Pi can pass standalone/provider primitives.

## Ledger

### L-1 | 2026-07-19T09:48:00-03:00 | S1-plan | katish-main | planner | Phase 0
Did: Loaded Build Stream Conductor, Build Stream, and Compass Forge skills; ran Compass Forge read-only orientation; inspected Istara evaluation docs and Pi repo metadata; spawned three architects for parallel planning.
Result: Planning lab scaffold created under `comparison-Istara-pi/`.
Verified: `compass-forge status`; `compass-forge agent-brief --compact --max-seconds 30`; GitHub repo metadata reads; direct reads of Istara evaluation docs.
Next: Merge architect outputs into this plan and prepare owner testing gate.

### L-2 | 2026-07-19T10:05:00-03:00 | S1-plan | katish-main | conductor | Phase 0
Did: Integrated all three architect readouts into durable artifacts under `comparison-Istara-pi/architects/`.
Result: Lab plan now specifies Istara surfaces, Pi repository scope, adapter methodology, metrics, evidence layout, risks, and live-test gate.
Verified: Architect A, B, and C outputs reconciled; no Istara application code changes made.
Next: Wait for owner cloud LLM/API instructions, then create no-model dry-run lab specs before any live model calls.

### L-3 | 2026-07-19T10:22:00-03:00 | S1-plan | katish-main | conductor | Phase 0
Did: Corrected the Pi scope from three pi-named repositories to three Pi monorepo packages and enriched the lab with a loose dependency/adaptation strategy.
Result: The comparison now targets `packages/coding-agent`, `packages/agent`, and `packages/ai` as the core harnesses, while `pi-review` and `pi-chat` are demoted to optional reference material.
Verified: `rg` over `comparison-Istara-pi`; GitHub API reads of the three package `package.json` files and READMEs; `metrics-schema.json` JSON validation.
Next: Owner gate for cloud LLM settings and permission to create deterministic no-model validators.

### L-4 | 2026-07-19T10:30:00-03:00 | S1-plan | katish-main | conductor | Phase 0
Did: Corrected the migration hypothesis from "adapter-first partial replacement" to "full agentic-core replacement under adapter control."
Result: The plan now tests whether Pi can replace Istara's ReAct loops, agentic orchestration, model management, SDK/process integration, and channel agent harnesses while Istara features are reconnected through Pi-facing adapters.
Verified: `rg` over replacement-scope language; no files outside `comparison-Istara-pi/` edited.
Next: Build deterministic no-model validators and feature reconnection matrix after owner approval.

### L-5 | 2026-07-19T10:55:00-03:00 | S1-plan | katish-main | conductor | Phase 0
Did: Recorded DeepSeek test configuration, collaborative article protocol, storage cleanup policy, and durable OpenClaw job requirements.
Result: The lab now has an approved cloud model target and a job contract for three architects writing and judging the article incrementally.
Verified: No literal API key written to `comparison-Istara-pi/`; `metrics-schema.json` remains valid JSON.
Next: Durable job prepares first-run artifacts, checks secret availability at runtime, and asks before scaling beyond smoke tests.

### L-6 | 2026-07-19T11:02:23-03:00 | S2-smoke | durable-openclaw-conductor | conductor | Phase 0
Did: Created `runs/20260719T105618-0300-deepseek-conductor/`, no-model validators, smoke scripts, article skeleton, feature matrix, full replacement coverage matrix, gzipped trace/output artifacts, and cleanup report.
Result: The Istara-compatible OpenAI base-url shape reached DeepSeek with model `deepseek-v4-pro`; Pi provider smoke was not executed because `@earendil-works/pi-ai` is not installed locally and installing Pi dependencies requires owner approval.
Verified: `validate_no_model.py` passed; `smoke_deepseek_openai_compatible.py` passed with 36 total tokens and 2163 ms latency; `pi_provider_static_probe.sh` found npm latest `0.80.10` but no local package; storage cleanup retained a small comparison folder.
Next: Owner gate for Pi dependency setup/local checkout and a capped paired benchmark budget.

### L-7 | 2026-07-19T11:50:57-03:00 | S2-smoke | pi-provider-smoke-subagent | implementer | Phase 0
Did: Created `runs/20260719T114723-0300-pi-provider-setup/`, installed `@earendil-works/pi-ai@0.80.10` in a temporary run-local dependency folder, and ran Pi's built-in DeepSeek provider against `deepseek-v4-pro`.
Result: Pi provider smoke passed with HTTP 200, 2787 ms latency, 94 total tokens, model `deepseek-v4-pro`, and adapter mode `library_builtin_deepseek_provider`.
Verified: `npm install --no-audit --no-fund @earendil-works/pi-ai@0.80.10`; `pi_deepseek_smoke.mjs`; `gzip -t` for trace/output JSONL; JSON validation; secret scan; storage cleanup retained no dependency folders.
Next: Build a separated Istara worktree or sidecar replacement harness before treating any
Pi result as comparative replacement evidence.

### L-8 | 2026-07-19T11:56:55-03:00 | S2-smoke | pi-provider-smoke-subagent | editor | Phase 0
Did: Recorded owner steering clarification after the Pi provider smoke.
Result: The lab now states that the provider smoke is not the replacement test. The next
gate is a separated Istara worktree or sidecar harness where Pi is wired as the candidate
engine for Istara agentic loops through adapters/canonical tools.
Verified: `rg` over smoke, standalone, replacement, worktree, sidecar, and benchmark-gate language; artifact edits stayed under `comparison-Istara-pi/`.
Next: Owner approves or launches the replacement harness build, then sets token/cost cap
and scenario count before live paired metrics.

### L-9 | 2026-07-19T12:03:00-03:00 | S2-smoke | pi-provider-smoke-subagent | editor | Phase 0
Did: Recorded the Compass Forge/context mapping boundary for the Pi provider setup run.
Result: Added `runs/20260719T114723-0300-pi-provider-setup/cf-context-scope.md` and updated
the run status so provider-smoke scope is separated from future replacement-harness mapping.
Compass Forge impact/context output identified compute/provider routing, agent lifecycle,
tool/skill execution, RAG/memory, A2A/channel behavior, and product feature contracts as
future harness inputs only.
Verified: `compass-forge status`; `compass-forge next`; compact `agent-brief` structured timeout with `fallback_authorized: true`; `compass-forge classify`; `compass-forge intelligence impact`; `compass-forge context --pack-type lite`.
Next: Replacement-worktree conductor follows `replacement-worktree-conductor-brief.md` and
uses Compass Forge for real dependency/impact mapping before implementing adapters or sidecar
wiring.

### L-10 | 2026-07-19T12:08:00-03:00 | S2-replacement-worktree | replacement-worktree-subagent | conductor | Phase 0
Did: Created isolated worktree `/Users/user/Documents/Istara-main-pi-replacement` on `comparison/pi-replacement-core` from `origin/main`; added a removable `labs/pi-replacement/` package with `CanonicalToolFacade`, `IstaraPiAdapter`, scenario runner, and tests.
Result: First replacement-harness scenario passed: Pi `Agent` owned a chat/tool loop and executed canonical Istara `tasks.create` and `findings.create` envelopes. Pi DeepSeek provider smoke also passed from inside the isolated worktree; the latest remediation smoke used 50 total tokens and 2438 ms latency.
Verified: `npm run validate`; `npm run smoke:no-model`; same-process DeepSeek smoke with `envAfter=false`; run artifacts in `runs/20260719T120128-0300-replacement-worktree/`.
Next: Owner gate for token/cost cap and scenario count before paired benchmarks through the replacement sidecar.

### L-11 | 2026-07-19T12:09:28-03:00 | S2-smoke | pi-provider-smoke-subagent | editor | Phase 0
Did: Recorded owner steering that provider/setup results are package-boundary preflight only.
Result: Updated provider-run and article/plan artifacts so the replacement score is tied to
Istara's existing coverage backbone: `tests/benchmarks/`, `tests/evals/`,
`scripts/run_istara_evals.py`, `tests/agentic_eval_contract.json`,
`tests/real_user_benchmark/`, and `tests/simulation/scenarios/`.
Verified: `rg` over package-boundary, preflight, provider smoke, standalone, replacement
score, and Istara harness paths; `compass-forge classify` returned `local_fix` / `lite`.
Next: Replacement harness must route those Istara scenarios/contracts through Pi-owned
agent/provider code before any replacement score is claimed.

### L-12 | 2026-07-19T12:12:49-03:00 | S2-replacement-worktree | replacement-worktree-subagent | conductor | Phase 0
Did: Re-read the updated replacement brief and ran CF status, next, compact agent brief,
standard context pack, and six targeted impact maps for chat/tool loop, task
planning/execution, model/provider routing, memory/RAG, A2A, and channels.
Result: Added `runs/20260719T120128-0300-replacement-worktree/cf-dependency-maps.md`,
recorded CF stale/unregistered state as a limitation, and patched the isolated sidecar so
DeepSeek env cleanup covers provider setup/model lookup as well as completion.
Verified: `compass-forge agent-brief --compact --max-seconds 120`; `compass-forge context
... --pack-type standard`; `compass-forge intelligence impact --path ...` for the six
required surfaces; sidecar validation pending in the final remediation check.
Next: Re-run sidecar validation, secret scan, status checks, and storage report; paired
benchmarks remain owner-gated.

### L-13 | 2026-07-19T13:15:00-03:00 | S3-full-replacement-candidate | full-replacement-candidate-subagent | conductor | Phase 0
Did: Expanded the isolated replacement worktree from one chat/tool smoke into an eight-surface
Pi-owned candidate harness with a scenario catalog, richer canonical facade, deterministic
baseline pairing, artifact collector, raw live-call capture, coverage matrix, and gap list.
Result: Pi candidate now runs representative Istara-derived slices for chat/tool loop,
plan-and-execute, documents/tools, structured outputs, memory/RAG, three skills, A2A,
channel lifecycle, provider routing, and telemetry. It remains a sidecar harness, not a
production route replacement.
Verified: `npm run validate` passed 4 tests; `npm run collect:artifacts -- --out ...`
passed baseline 8/8 and candidate 8/8 deterministic paired scenarios; native baseline
`tests/test_agentic_eval_contract.py`, `tests/test_istara_eval_runner.py`, and
`tests/benchmarks/test_orchestration.py` passed; `npm run smoke:deepseek` passed with
47 tokens and USD 0.00003654 provider-reported cost.
Next: Replace in-memory canonical handlers with real Istara service/RPC adapters in the
isolated worktree, then rerun selected live DeepSeek scenarios under the remaining cap.

### L-14 | 2026-07-19T13:21:48-03:00 | S5-compliance | gpt-5-codex-openclaw | compliance-reviewer | Phase 0
Did: Applied the owner clarification that `/skill build-stream-conductor` was required by
loading the Build Stream Conductor, Build Stream, and Compass Forge skill contracts, running
CF orientation/impact/test-impact, probing conductor routing/status/scorecard helpers, and
adding `build-stream-lifecycle.md` plus `build-stream-conductor-compliance.md`.
Result: Literal Build Stream Conductor pipeline was not used for L-13. The project lacks
`.compass-forge/conductor/cast.json`, `conductor.py status --brief` fails on that missing
cast, and `scorecard.py` returns no model rows. The earlier `conductor` labels in this plan
mean durable OpenClaw conductor/subagent coordination, not the literal Build Stream
Conductor watcher/cast pipeline.
Verified: `compass-forge status`; `compass-forge next`; `compass-forge agent-brief
--compact --max-seconds 45`; targeted `compass-forge intelligence impact`; targeted
`compass-forge intelligence test-impact`; `routing.py show`; `conductor.py status --brief`
missing-cast failure; `scorecard.py` empty model rows.
Next: If conductor-owned evidence is required, run a fresh next implementation round from
a real terminal using `make_pipeline.py`, `make_cast.py`, and `conductor.py spawn`; otherwise
continue adapter hardening from the isolated sidecar gap list.

## Evaluation Questions

1. Can Pi replace Istara's full agentic management core while preserving all user-visible Istara feature behavior?
2. Does Pi provide a cleaner or more reliable ReAct/tool-loop substrate than Istara's current implementation?
3. Does Pi improve model-provider management without losing Istara-specific compute donation, circuit breaker, project isolation, or research-governance behavior when those policies are enforced by Istara adapters?
4. Can Pi preserve or improve Istara's research spine: ingest, extract, structure, synthesize, compose, cite, review?
5. Does Pi reduce tool calls/interactions while maintaining or improving output quality?
6. Does Pi improve skills and system-prompt adherence?
7. Does Pi improve A2A task success and multi-agent coordination?
8. Can Pi-supported channel harness patterns cover Istara's channel integration needs?
9. Which best practices should Istara adopt even if full replacement is not justified?
10. Can Pi be introduced as a loosely coupled dependency or sidecar so Istara can update Pi versions deliberately without merging Pi internals into Istara?

## Scenario Families

### S1 - Tool Calling

Measure tool-name accuracy, argument-schema validity, invalid-call recovery, multi-turn recovery, tool-result grounding, and unnecessary-call rate.

Candidate Istara assets:

- `tests/benchmarks/run_benchmarks.py`
- `tests/benchmarks/test_orchestration.py`
- `tests/agentic_eval_contract.json`
- `tests/simulation/scenarios/31-task-documents-tools.mjs`
- `tests/simulation/scenarios/71-plan-and-execute.mjs`

### S2 - Research Spine Quality

Evaluate each step independently and as an end-to-end chain:

- Ingest corpus.
- Extract evidence.
- Structure facts/findings.
- Synthesize insights.
- Compose final output.
- Cite/source-ground claims.
- Review/revise/approve.

Candidate Istara assets:

- `tests/real_user_benchmark/README.md`
- `tests/real_user_benchmark/benchmark-plan.md`
- `tests/real_user_benchmark/system-prompt.md`
- `tests/evals/README.md`
- `scripts/run_istara_evals.py`

### S3 - Memory Load

Measure context load, retrieved memory relevance, memory contamination, memory persistence, cross-session recall, and token impact.

Candidate Istara assets:

- `tests/agentic_eval_contract.json` entries for `reasoning_bank` and `memento_skills_and_agent_creation`.
- `backend/app/core/agent_memory.py`
- `backend/app/core/context_dag.py`
- `backend/app/core/reasoning_bank.py` if present.

### S4 - Skills And Prompt Adherence

Measure whether the engine obeys system prompts, skill instructions, owner constraints, feature docs, and refusal boundaries.

Checks:

- Constraint preservation across turns.
- Tool/skill selection correctness.
- No hidden mutation when prompt says plan-only.
- Source citation and evidence-chain discipline.
- Respect for no-local-model and API-key boundaries.

### S5 - A2A And Agentic Management

Measure task success with agent-to-agent collaboration, number of interactions, tool calls, latency, and quality.

Candidate Istara assets:

- `tests/simulation/scenarios/73-a2a-debate-and-reports.mjs`
- `Tech.md` A2A collaboration notes.
- Task review and approval flows in `tests/real_user_benchmark`.

### S6 - Channel And SDK Integration

Measure whether Pi can support the channel and process surfaces where Istara currently uses agentic management:

- Telegram/Discord-style message ingestion and response routing.
- Channel identity, project scoping, attachment handling, and remote-control safety.
- SDK/process integration for embedding Pi into Istara.
- Event streaming into Istara's UI/progress surfaces.
- Abort, resume, reconnect, and failure recovery.

### S7 - Model Management

Compare:

- Provider routing.
- Cloud API compatibility.
- Retry/fallback policy.
- Circuit breaker behavior.
- Token accounting.
- Cost accounting.
- Per-step model selection.
- Secrets handling.

## Adapter Lab Design

The comparison should be run through a shared scenario layer, not by letting each engine choose its own affordances.

- `EngineAdapter`
  - `prepare_run(manifest)`: validate git SHA, model policy, no-local-model setting, and scenario registry hash.
  - `start_session(scenario)`: create an isolated engine session for one scenario.
  - `run_step(step)`: execute one research-spine step or ReAct turn.
  - `call_tool(tool_call)`: route through the canonical tool facade and record schema validation.
  - `load_memory(query, scope)`: record memory hits, tokens, and scoping.
  - `finalize()`: emit final artifact, compact trace, and score-ready output.
- `IstaraAdapter`
  - Baseline adapter for Istara's current agentic engine.
  - Drives existing chat, task, A2A, telemetry, benchmark, and feature APIs for comparison.
  - Does not define the desired future boundary; it measures current behavior.
- `PiAdapter`
  - Drives Pi agent/harness/provider/session behavior through `@earendil-works/pi-coding-agent`, `@earendil-works/pi-agent-core`, and `@earendil-works/pi-ai`.
  - Must record exact package version, git SHA, adapter mode (`library`, `CLI`, `RPC`, or `sidecar`), and update boundary.
  - Must expose equivalent operations for all Istara agentic surfaces: chat, tasks, research spine, memory actions, A2A, model management, SDK/process integration, and channel integrations.
  - Must preserve Istara feature criteria through adapter-enforced policy and canonical tools.
- `CanonicalToolFacade`
  - Defines one shared set of tool schemas.
  - Maps Istara tool names and Pi tool names to canonical ids.
  - Separates invalid schema, unsupported capability, failed execution, and unnecessary tool use.
- `JudgeLayer`
  - Runs deterministic checks first.
  - Uses cloud LLM judges only after owner approval.
  - Stores capped judge inputs and hashes large artifacts.

## Research Spine

Each scenario should be scored by these phases:

1. Intent intake and constraint preservation.
2. Context and memory loading.
3. Plan/decomposition.
4. Tool/skill selection.
5. Tool/action execution.
6. Observation integration and recovery.
7. Evidence grounding.
8. Synthesis/final output.
9. Review/reflection/memory update.
10. System/governance adherence.

## Feature Matrix Plan

Generate a feature matrix from `docs/features/inventory.json`. Each feature row should define:

- Feature id and group.
- Reachable surface/API or explicit unsupported marker.
- Project/auth scoping expectation.
- User action or scenario trigger.
- Expected engine behavior.
- Expected tool/memory/A2A behavior when relevant.
- Evidence emitted.
- Graceful failure path.
- Istara score, Pi score, delta, and notes.

Aggregate by groups: Shell, Auth, Chat, Findings, Tasks, Interviews, Documents, Context, Skills, Agents, Memory, Interfaces, Integrations, Loops, Settings, Autoresearch, Compute, Ensemble, Quality, Backup, Meta, Admin, History, Notifications.

## Pi Replacement Hypotheses

- Full agentic core: Pi may be able to replace Istara's current agentic engine, including all ReAct/tool loops, planning/execution orchestration, model/provider management, session/harness mechanics, SDK/process integration, and channel-facing agent behavior.
- ReAct loop: `@earendil-works/pi-agent-core` may be cleaner as the central evented loop for all Istara agentic surfaces, especially for tool validation/execution, streamed events, follow-up/steering queues, and durable session events.
- Model/provider layer: `@earendil-works/pi-ai` may replace Istara's model API abstraction for cloud providers, auth handling, dynamic models, streaming tool-call parsing, reasoning levels, cross-provider handoffs, and cost/token metadata.
- Coding harness layer: `@earendil-works/pi-coding-agent` may provide the SDK/CLI/RPC process boundary and supported agent harness behavior useful for embedding Pi as an independently updateable dependency.
- Feature reconnection: Istara product features should remain, but their agentic entry points should be reconnected to Pi through canonical tools/adapters instead of retaining parallel Istara ReAct loops.
- State boundary: Pi may manage engine sessions/traces, but Istara feature data remains source-of-truth unless a later migration explicitly proves safe replacement for a specific data store.
- Extension repos: `pi-review` and `pi-chat` should be evaluated only for transferable practices around review loops, chat sandboxing, channel memory, and remote controls.

## Full Agentic-Core Replacement Strategy

The migration experiment should not vendor Pi into Istara or rewrite Istara features around Pi. Treat Pi as an independently updateable dependency with a clear adapter boundary whose purpose is to let Pi own the agentic core:

- `IstaraPiAdapter` owns all translation between Istara concepts and Pi concepts.
- Istara remains the source of truth for product data, feature contracts, users, projects, permissions, tasks, findings, documents, existing memory stores, telemetry redaction, and UX/research workflow semantics.
- Pi is tested as owner of the agentic core: ReAct/tool loops, planner/executor behavior, model/provider access, session/harness mechanics, agentic memory operations, A2A orchestration behavior, SDK/process integration, and channel-facing agent behavior.
- Istara features reconnect to Pi through canonical tools, resource adapters, memory adapters, channel adapters, and task/finding/document adapters.
- Version selection is explicit: every run records Pi package versions, Pi git SHA, lockfile hash, adapter version, and Istara SHA.
- Update policy is owner-controlled: upgrade Pi by changing the dependency/version used by the adapter lab, rerun deterministic validators, then rerun paired live evals before any Istara production adoption.
- Runtime shape options are compared before implementation:
  - Library mode: import `@earendil-works/pi-agent-core` and `@earendil-works/pi-ai` from a Node sidecar library.
  - CLI/RPC mode: drive `@earendil-works/pi-coding-agent` as an external process with strict JSONL/RPC framing.
  - HTTP sidecar mode: wrap Pi in a small service that Istara calls through a stable local contract.
- Hard rejection criteria: Pi cannot bypass Istara authorization, directly mutate Istara DB state without adapter policy, store secrets in traces, decide feature eligibility outside Istara policy, or fail to cover existing agentic surfaces.

## Evidence Model

Each later test run should produce small JSONL records:

- `manifest.json`: git SHAs, adapter versions, scenario registry hash, model policy, environment booleans, no secrets.
- `scenarios.jsonl`: scenario metadata and feature ids.
- `trace.jsonl.gz`: compact step trace, tool calls, observations, token counts, errors.
- `outputs.jsonl.gz`: final artifacts and judge inputs, capped per record with SHA for larger content.
- `scores.json`: aggregate metrics and confidence intervals.
- `feature-matrix.json`: per-feature success criteria and pass/fail evidence.
- `article-tables/`: CSV/JSON tables for academic writeup.

No large screenshots, traces, or local model artifacts by default. Screenshots/traces are opt-in only when UI evidence is necessary.

## Token And Tool Accounting

- Prefer provider-reported `usage.prompt_tokens`, `usage.completion_tokens`, and `usage.total_tokens`.
- Use one shared tokenizer estimate when provider usage is unavailable.
- Record token counts per research-spine phase, not only per API call.
- Count memory separately: loaded items, bytes/chars, estimated tokens, scope, relevance.
- Count tools as attempted, valid, executed, successful, repeated, hallucinated, skipped-needed.
- Compute `quality_per_1k_tokens`, `quality_per_tool_call`, and `marginal_tool_gain`.

## Best-Practice Extraction

If Pi wins a category, classify whether it supports the full replacement thesis or only a best-practice extraction:

- Prompt practice.
- Tool schema/execution practice.
- Memory/session practice.
- Model/provider routing practice.
- A2A/orchestration practice.
- Governance/review practice.

Then map it to an Istara surface, define migration risk, and require a benchmark-gated adoption plan.

## Owner Gate For Testing

Before running live tests, ask the owner for:

- Budget/token limit for the first non-smoke paired run.
- Whether Pi should run as CLI, imported library, or harnessed subprocess.
- Whether telemetry/content-retention may store capped prompt/output excerpts or only hashes and scores.
- Whether deterministic no-model validators may be created before live testing.

Resolved for smoke testing:

- Provider: DeepSeek.
- Model: `deepseek-v4-pro`.
- API environment variable: `DEEPSEEK_API_KEY`.
- Base URL: `https://api.deepseek.com`.
- Reasoning: high effort, thinking enabled where supported.
- Local models: disallowed.

## Academic Article Structure

Working title: "Comparing ReAct Engine Architectures for Research-Centric Agentic Systems: Istara and Pi"

Sections:

1. Abstract.
2. Introduction and motivation.
3. System descriptions.
4. Evaluation methodology.
5. Scenario design.
6. Metrics and instrumentation.
7. Results.
8. Comparative analysis.
9. Threats to validity.
10. Best practices and architectural recommendations.
11. Conclusion.

## Initial Risks

- Pi may optimize coding-agent workflows more than research-product workflows.
- Istara has domain-specific research spine and governance that Pi may not model natively.
- Token and tool-call counts are not comparable unless instrumentation normalizes event boundaries.
- Live LLM variability can swamp engine differences; paired prompts and fixed model/provider settings are required.
- Current Istara worktree is dirty; no code changes should be mixed into this lab.
