# Evidence Log

## 2026-07-19 Planning Round

Commands and observations:

- `compass-forge status`
  - Active workspace: `/Users/user/Documents/compass-forge`
  - Target: `/Users/user/Documents/Istara-main`
  - Recipe: `istararustgraphtrial`
  - State freshness: unknown, no snapshot recorded.
- `compass-forge next`
  - Suggested init action, indicating this target is not registered in current CF state despite local `.compass-forge/`.
- `compass-forge agent-brief --request "Plan-only comparison lab for Istara ReAct engine versus earendil-works/pi; no code changes; artifacts only under comparison-Istara-pi" --compact --max-seconds 30`
  - Produced compact repo map.
  - Classified request as `local_fix` / lite because this round only creates artifacts.
  - Identified relevant tests including `tests/test_istara_eval_runner.py`, `tests/benchmarks/test_orchestration.py`, and simulation scenarios.
  - Gate warnings were inherited complexity warnings in large docs/test runner files.
- `gh repo view earendil-works/pi`
  - Description: AI agent toolkit, unified LLM API, agent loop, TUI, coding agent CLI.
  - Default branch: `main`.
  - Pushed: 2026-07-17.
- `gh repo list earendil-works`
  - Found pi-named repos: `pi`, `pi-review`, `pi-website`, `pi-tutorial`, `pi-chat`.
  - `pi-website` is archived.
- Read Istara evaluation assets:
  - `tests/real_user_benchmark/README.md`
  - `tests/real_user_benchmark/benchmark-plan.md`
  - `tests/agentic_eval_contract.json`
  - `tests/evals/README.md`
  - `tests/benchmarks/run_benchmarks.py`
  - Targeted sections of `Tech.md`.
- Read Pi source/docs through GitHub API, including:
  - `pi` README and package map.
  - `packages/agent/README.md`
  - `packages/agent/docs/agent-harness.md`
  - `packages/agent/docs/durable-harness.md`
  - `packages/agent/docs/models.md`
  - `packages/agent/src/agent-loop.ts`
  - `packages/agent/src/harness/skills.ts`
  - `packages/agent/src/harness/system-prompt.ts`
  - `packages/ai/README.md`
  - `pi-review` README and review command source.
  - `pi-chat` README and selected source docs.
- Spawned three planning architects:
  - Architect A: Istara internals and existing evaluation assets.
  - Architect B: Pi architecture and replacement feasibility.
  - Architect C: methodology, metrics, evidence collection, and academic article structure.
- Integrated architect outputs into:
  - `architects/architect-a-istara.md`
  - `architects/architect-b-pi.md`
  - `architects/architect-c-methodology.md`
  - `architects/integrated-synthesis.md`

No live LLM calls were made.
No Istara application code was changed.

## 2026-07-19 Scope Correction

Owner clarified that the intended "three" Pi targets are the three core packages inside
`earendil-works/pi`, not the separate `pi-review` and `pi-chat` repositories.

Commands and observations:

- `rg -n "pi-review|pi-chat|pi-tutorial|pi-website|pi-coding-agent|pi-agent-core|pi-ai|packages/coding-agent|packages/agent|packages/ai|earendil-works/pi" comparison-Istara-pi`
  - Confirmed the first architect pass already included `packages/ai`, `packages/agent`, and `packages/coding-agent` in Architect B.
  - Also confirmed the first pass still treated `pi-review` and `pi-chat` as primary repos in several files.
- `gh api repos/earendil-works/pi/contents/packages/coding-agent/package.json --jq '.content | @base64d'`
  - Package: `@earendil-works/pi-coding-agent`, version `0.80.10`, CLI binary `pi`, depends on `@earendil-works/pi-agent-core` and `@earendil-works/pi-ai`.
- `gh api repos/earendil-works/pi/contents/packages/agent/package.json --jq '.content | @base64d'`
  - Package: `@earendil-works/pi-agent-core`, version `0.80.10`, agent runtime with transport abstraction, state management, attachment support, and harness tests.
- `gh api repos/earendil-works/pi/contents/packages/ai/package.json --jq '.content | @base64d'`
  - Package: `@earendil-works/pi-ai`, version `0.80.10`, unified provider/model layer with broad provider dependencies and model catalog generation.
- Read package READMEs for:
  - `packages/coding-agent/README.md`
  - `packages/agent/README.md`
  - `packages/ai/README.md`

Changes made only under `comparison-Istara-pi/`:

- Corrected core scope to `@earendil-works/pi-coding-agent`, `@earendil-works/pi-agent-core`, and `@earendil-works/pi-ai`.
- Demoted `pi-review` and `pi-chat` to optional ecosystem/best-practice references.
- Added loose dependency strategy: Pi should be tested as a pinned/updateable package, CLI/RPC process, or sidecar behind an Istara-owned adapter.
- Updated metrics schema from version 2 to version 3 with `pi_scope` and `adapter_mode`.

## 2026-07-19 Replacement Intent Correction

Owner clarified that the intended experiment is full replacement of Istara's agentic
management core, not conservative augmentation.

Changes made only under `comparison-Istara-pi/`:

- Updated the main research question: can Pi replace Istara's ReAct loops, planner/executor
  behavior, model management, SDK/process integration, session/harness mechanics, and
  channel-facing agent integrations?
- Clarified that Istara features remain and are reconnected to Pi through adapters and
  canonical tools.
- Clarified that Istara product data, authorization, feature contracts, telemetry policy,
  and UX/research workflow semantics remain acceptance criteria, not reasons to preserve
  the old Istara agentic engine.
- Added a required full replacement coverage matrix for every current Istara agentic
  loop/channel/model-management path.

## 2026-07-19 DeepSeek And Durable Job Approval

Owner approved DeepSeek cloud LLM testing and requested a durable OpenClaw job with ongoing
updates.

Recorded run configuration:

- Provider: DeepSeek.
- Model: `deepseek-v4-pro`.
- Base URL: `https://api.deepseek.com`.
- Runtime secret: `DEEPSEEK_API_KEY`.
- Reasoning: high effort; thinking enabled where supported.
- Local models: not allowed.

Secret hygiene:

- Do not write the API key into repo files, run manifests, article drafts, traces, or logs.
- Run manifests may record only `DEEPSEEK_API_KEY` as the env var name and a boolean
  `deepseek_key_present`.
- If a child job cannot access the runtime secret safely, it must pause and ask for secret
  handoff rather than copying the key into artifacts.

## 2026-07-19 Durable DeepSeek Conductor Smoke

Run folder:

- `comparison-Istara-pi/runs/20260719T105618-0300-deepseek-conductor/`

Commands and observations:

- `compass-forge status`
  - Target remained `/Users/user/Documents/Istara-main`, recipe `istararustgraphtrial`.
  - State freshness remained unknown with no snapshot recorded.
  - No Compass Forge state mutation was performed.
- `compass-forge next`
  - Suggested repository initialization; not performed because this comparison job is confined
    to `comparison-Istara-pi/` artifacts.
- `compass-forge agent-brief --request "Durable OpenClaw conductor for Istara vs Pi comparison; artifacts only under comparison-Istara-pi; no Istara application code changes; DeepSeek smoke only" --compact --max-seconds 30`
  - Classified the artifact-only job as lite/local.
  - Reported inherited complexity warnings in large docs/test-runner files.
- `security find-generic-password -a openclaw -s istara-pi-deepseek -w >/dev/null`
  - Confirmed DeepSeek key presence without printing or storing the key.
- `validate_no_model.py`
  - Passed.
  - Checked manifest constraints, article file presence, generated feature coverage for 86
    feature inventory rows, and secret-shaped artifact patterns.
- `smoke_deepseek_openai_compatible.py`
  - Passed.
  - Provider/base/model: DeepSeek, `https://api.deepseek.com`, `deepseek-v4-pro`.
  - Status: 200.
  - Latency: 2163 ms.
  - Usage: 20 prompt tokens, 16 completion tokens, 36 total tokens, including 16 reasoning tokens.
  - Secret value was not written to artifacts or command output.
- `pi_provider_static_probe.sh`
  - Did not install packages or run a Pi live LLM call.
  - `@earendil-works/pi-ai` was not locally resolvable.
  - npm latest version observed: `0.80.10`.
  - Pi provider smoke is blocked on owner approval for a Pi package install or local Pi checkout.

Artifacts created or updated only under `comparison-Istara-pi/`:

- Run manifest/status/article/logs/cleanup placeholders.
- `specs/engine-adapter-spec.md`.
- `specs/first-run-scenarios.jsonl`.
- `feature-matrix.json`.
- `full-replacement-coverage-matrix.md`.
- `architect-lanes.md`.
- `trace.jsonl.gz`, `outputs.jsonl.gz`, and `scores.json`.
- Article files under `article/` per `article-collaboration-protocol.md`.

No Istara application code was changed.
No local models were used or loaded.

## 2026-07-19 Pi Provider Dependency Smoke

Run folder:

- `comparison-Istara-pi/runs/20260719T114723-0300-pi-provider-setup/`

Commands and observations:

- `compass-forge status`, `compass-forge next`, and compact `compass-forge agent-brief`
  - Classified the artifact-only job as lite/local.
  - Reported inherited complexity warnings only; no Compass Forge state mutation was performed.
- `npm install --no-audit --no-fund @earendil-works/pi-ai@0.80.10`
  - Passed inside a temporary run-local `tmp-pi-deps` folder.
  - Installed only `@earendil-works/pi-ai`; no Pi monorepo clone was required.
- `pi_deepseek_smoke.mjs`
  - Passed through Pi's native `deepseekProvider()` and `models.completeSimple()`.
  - Provider/model/API: `deepseek`, `deepseek-v4-pro`, `openai-completions`.
  - Status: 200.
  - Latency: 2787 ms.
  - Usage: 20 input tokens, 74 output tokens, 71 reasoning tokens, 94 total tokens.
  - Pi catalog cost estimate: 0.00007308 USD.
  - Observed sanitized payload used `max_completion_tokens`, `reasoning_effort: high`, and
    `thinking: { type: enabled }`.
- Cleanup
  - Deleted temporary dependency folder after the smoke.
  - Final run folder size: 36K.
  - Final `comparison-Istara-pi` size: 380K.

No Istara application code was changed.
No local models were used or loaded.
No literal DeepSeek key was written to artifacts.

## 2026-07-19 Provider Smoke Scope Clarification

Owner clarified that the passed Pi provider smoke is not the replacement evaluation and
must not be presented as a substitute for the intended architecture test.

Recorded interpretation:

- The Pi provider smoke proves `@earendil-works/pi-ai@0.80.10` can call DeepSeek
  `deepseek-v4-pro`; it does not prove that Pi can replace Istara's agentic loops.
- Full metrics require a separate Istara worktree or isolated lab sidecar where Pi is wired
  as the candidate engine behind Istara adapters/canonical tools.
- The main worktree remains untouched outside `comparison-Istara-pi/`.
- Live paired runs from that replacement harness still require owner token/cost cap and
  scenario-count approval.

Commands and observations:

- `rg -n "standalone|next gate|provider smoke|Pi provider|sidecar|worktree|replacement harness|replacement" comparison-Istara-pi`
  - Confirmed `replacement-worktree-conductor-brief.md` already states that a standalone Pi
    demo is not success.
  - Found newer smoke-result surfaces whose next-gate wording could imply direct paired
    benchmarks before a replacement harness.
- `compass-forge status`, `compass-forge next`, and compact `compass-forge agent-brief`
  - State remained unregistered/unknown; compact brief timed out with structured
    `fallback_authorized: true`.
- `compass-forge classify "Clarify Istara-vs-Pi artifacts: provider smoke is not replacement test; next gate is isolated worktree/sidecar harness"`
  - Classified as `standard_change` because the request changes evaluation architecture
    wording, but implementation remained artifact-only under `comparison-Istara-pi/`.

## 2026-07-19 Replacement Worktree Prototype

Run folder:

- `comparison-Istara-pi/runs/20260719T120128-0300-replacement-worktree/`

Commands and observations:

- `git worktree add /Users/user/Documents/Istara-main-pi-replacement -b comparison/pi-replacement-core origin/main`
  - Created an isolated replacement worktree from `origin/main` at
    `fa6a1a391b5a1089690eb8fed5d179ce146ec9e9`.
  - This avoided inheriting unrelated dirty changes from the current worktree.
- `npm install --no-audit --no-fund`
  - Passed inside `/Users/user/Documents/Istara-main-pi-replacement/labs/pi-replacement`.
  - Installed `@earendil-works/pi-agent-core@0.80.10` and `@earendil-works/pi-ai@0.80.10`.
- `npm run validate`
  - Passed 2 Node tests.
  - Validated canonical facade schema/error envelopes and Pi-owned Agent tool-loop routing.
- `npm run smoke:no-model`
  - Passed.
  - Scenario: `chat.tool_loop.task_and_finding`.
  - Pi `Agent` owned the loop and executed canonical Istara `tasks.create` and
    `findings.create` tools through the facade.
  - Pi faux provider calls: 2.
  - Deterministic no-model token estimate: 1344 total, cost 0.
- Initial `npm run smoke:deepseek`
  - Passed through Pi's built-in `deepseekProvider()` and model `deepseek-v4-pro`.
  - DeepSeek key was read from macOS Keychain only inside the smoke process.
  - Latency: 1886 ms.
  - Usage: 10 input tokens, 24 output tokens, 21 reasoning tokens, 34 total tokens.
  - Pi catalog cost estimate: 0.00002523 USD.

Replacement evidence now exists for one Istara feature scenario path. It is still a lab
sidecar, not production route migration. Research spine, memory persistence, A2A, channel
turns, steering, SDK/process lifecycle, telemetry integration, and autoresearch governance
remain future adapter tasks.

No main worktree application code was changed.
No local models were used or loaded.
No literal DeepSeek key was written to artifacts.

## 2026-07-19 Provider Smoke Compass Forge Scope Boundary

Owner clarified that all active comparison conductors should use Compass Forge thoroughly
for dependency/impact mapping and evidence tracking. For the completed Pi provider setup
scope, the required follow-up was to record what CF/context mapping is relevant and what is
out of scope.

Commands and observations:

- `compass-forge status`
  - Target: `/Users/user/Documents/Istara-main`; recipe: `istararustgraphtrial`.
  - State remained unregistered/unknown with no snapshot recorded.
- `compass-forge next`
  - Recommended `compass-forge init`; not performed because this was an artifact-only
    scope note for a completed provider smoke.
- `compass-forge agent-brief --request "Record Compass Forge/context mapping scope for Pi provider dependency smoke; provider smoke is not replacement wiring; artifacts only under comparison-Istara-pi" --compact --max-seconds 30`
  - Timed out with structured `agent_brief_timeout` and `fallback_authorized: true`.
- `compass-forge classify "Record Compass Forge/context mapping scope for Pi provider dependency smoke; provider smoke is not replacement wiring; artifacts only under comparison-Istara-pi"`
  - Classified as `local_fix` / `lite`.
- `compass-forge intelligence impact --path comparison-Istara-pi/runs/20260719T114723-0300-pi-provider-setup/status.md --request "Record CF/context mapping scope for Pi provider dependency smoke; provider smoke is not replacement wiring"`
  - Mapped future replacement surfaces including compute/provider routing, agent lifecycle,
    tool/skill execution, RAG/memory, A2A/channel behavior, project scope/RBAC, findings,
    tasks, MCP, surveys, and related tests/docs.
- `compass-forge context "Pi provider dependency smoke scope only: summarize relevant Istara surfaces for future replacement harness, but no provider-smoke wiring" --pack-type lite`
  - Selected comparison artifacts, the Pi package-scope strategy, the replacement worktree
    brief, and broader Istara surfaces as context.

Recorded artifact:

- `runs/20260719T114723-0300-pi-provider-setup/cf-context-scope.md`

Interpretation:

- Relevant to provider smoke: artifact scope, `@earendil-works/pi-ai@0.80.10`,
  `deepseekProvider()`, secret handling, cleanup, storage, and claim boundaries.
- Out of scope for provider smoke: Istara replacement wiring, `IstaraPiAdapter`,
  `CanonicalToolFacade`, sidecar/RPC bridge, Pi-owned agent loop execution, paired metrics,
  and any app-code modification.

## 2026-07-19 Provider Setup Package-Boundary Framing

Owner clarified that any Pi provider/setup result should be framed as package-boundary
preflight only. The actual replacement comparison must use Istara's existing test and eval
harnesses as the coverage backbone.

Recorded framing:

- Pi provider/setup pass means dependency resolution and provider runtime feasibility.
- It is not a standalone replacement score.
- Replacement scoring requires Pi to be wired into an isolated Istara worktree or sidecar
  harness and run through Istara coverage:
  - `tests/benchmarks/`
  - `tests/evals/`
  - `scripts/run_istara_evals.py`
  - `tests/agentic_eval_contract.json`
  - `tests/real_user_benchmark/`
  - `tests/simulation/scenarios/`

Commands and observations:

- `rg -n "package-boundary|preflight|provider smoke|standalone|replacement score|tests/benchmarks|tests/evals|run_istara_evals|agentic_eval_contract|real_user_benchmark|simulation/scenarios|coverage backbone" comparison-Istara-pi`
  - Confirmed the replacement brief already includes the core harness list.
  - Found provider-run and article surfaces that needed stronger package-boundary wording.
- `compass-forge classify "Record package-boundary preflight framing and Istara harness backbone for Pi provider setup artifacts"`
  - Classified the artifact wording update as `local_fix` / `lite`.

## 2026-07-19 Replacement Worktree Compass Forge Remediation

Owner steering required the replacement-worktree conductor to use Compass Forge as an
actual dependency/impact map. Follow-up commands were run after re-reading
`replacement-worktree-conductor-brief.md`:

- `compass-forge status`
  - Active target `/Users/user/Documents/Istara-main`; recipe `istararustgraphtrial`.
  - State remained unregistered/unknown with no snapshot recorded.
- `compass-forge next`
  - Recommended repository initialization; not run because the active code work stayed in
    an isolated worktree and this pass recorded maps/evidence under `comparison-Istara-pi`.
- `compass-forge agent-brief --request "Pi replacement worktree: map Istara chat/tool loop, task planning/execution, model/provider routing, memory/RAG, and A2A/channel dependencies for isolated Pi adapter insertion" --compact --max-seconds 120`
  - Completed; classified the work as `standard_change`, recommended specific affected
    tests, and warned that no snapshot was recorded.
- `compass-forge context "Pi replacement dependency map for chat tool loop, task planning execution, model provider routing, memory RAG, A2A channels" --pack-type standard`
  - Completed; selected the replacement brief, coverage matrix, chat route, provider
    setup run, model-provider files, and scenario/test backbone.
- Targeted `compass-forge intelligence impact --path ...` commands completed for:
  - `backend/app/api/routes/chat.py`
  - `backend/app/core/agent_execution.py`
  - `backend/app/core/llm_router.py`
  - `backend/app/core/rag.py`
  - `backend/app/api/routes/a2a.py`
  - `backend/app/api/routes/channels.py`

Recorded artifact:

- `runs/20260719T120128-0300-replacement-worktree/cf-dependency-maps.md`

Remediation:

- Patched `/Users/user/Documents/Istara-main-pi-replacement/labs/pi-replacement/src/istara-pi-adapter.mjs`
  so `DEEPSEEK_API_KEY` cleanup covers provider setup and model lookup as well as the live
  completion call.
- Re-ran the DeepSeek smoke in the same Node process after remediation. Result:
  `envAfter=false`, 2438 ms latency, 10 input tokens, 40 output tokens, 37 reasoning
  tokens, 50 total tokens, and Pi catalog cost estimate 0.00003915 USD.

## 2026-07-19 Full Replacement Candidate Round

Owner clarified that the prior replacement worktree was still too thin. This run created
`runs/20260719T125756-0300-full-replacement-candidate/` and expanded the isolated
candidate code rather than touching main Istara app code.

Code changed in `/Users/user/Documents/Istara-main-pi-replacement/labs/pi-replacement`:

- Expanded `CanonicalToolFacade` to cover task lifecycle, document links, structured eval
  artifacts, memory search/write, three skill adapters, A2A delegation/report envelopes,
  simulated channel turns, and telemetry.
- Added `src/scenario-catalog.mjs` with eight Istara harness-derived scenario families.
- Added generic Pi scenario execution and deterministic `IstaraContractBaseline` pairing.
- Added an artifact collector that writes gzipped traces/outputs and `scores.json`.

Command evidence:

- `npm run validate` -> 4 Node tests passed.
- `npm run collect:artifacts -- --out .../20260719T125756-0300-full-replacement-candidate`
  -> baseline 8/8 and candidate 8/8 deterministic paired scenarios passed.
- `PYTHONDONTWRITEBYTECODE=1 pytest -p no:cacheprovider tests/test_agentic_eval_contract.py tests/test_istara_eval_runner.py`
  -> 12 passed.
- `PYTHONDONTWRITEBYTECODE=1 pytest -p no:cacheprovider tests/benchmarks/test_orchestration.py -q`
  -> 5 passed.
- `npm run smoke:deepseek` -> Pi ai reached DeepSeek `deepseek-v4-pro`, 47 tokens,
  USD 0.00003654 provider-reported cost.

Final interpretation:

- Replacement evidence now covers representative slices for chat/tools, plan-and-execute,
  documents, structured evals, memory/RAG, skills, A2A, channels, provider routing, and
  telemetry through the Pi adapter.
- It is still not full production replacement: real DB/service adapters, persistent RAG,
  full skill/memento lifecycle, real A2A/channel services, production routes, and broad
  live scenario scoring remain next-round work.

## 2026-07-19 Build Stream Conductor Compliance Clarification

Owner clarified after the full replacement candidate run that `/skill build-stream-conductor`
was specifically required, not a generic OpenClaw subagent approximation.

Compliance actions:

- Loaded `build-stream-conductor`, `build-stream`, and `compass-forge` skill contracts.
- Ran CF startup and dependency commands:
  - `compass-forge status`
  - `compass-forge next`
  - `compass-forge agent-brief --request "Pi replacement candidate Build Stream Conductor compliance check and benchmark artifact update" --compact --max-seconds 45`
  - `compass-forge intelligence impact --path comparison-Istara-pi/runs/20260719T125756-0300-full-replacement-candidate/status.md --request "Build Stream Conductor compliance addendum for Pi replacement candidate artifacts"`
  - `compass-forge intelligence test-impact --path comparison-Istara-pi/runs/20260719T125756-0300-full-replacement-candidate/benchmark-results.md`
- Probed conductor tooling:
  - `routing.py show` found global defaults and role/model routing.
  - `conductor.py status --brief` failed because `.compass-forge/conductor/cast.json` does not exist.
  - `scorecard.py` returned no model rows.

Outcome:

- Literal Build Stream Conductor pipeline was not used for `runs/20260719T125756-0300-full-replacement-candidate/`.
- Partial compliance is now documented in:
  - `runs/20260719T125756-0300-full-replacement-candidate/build-stream-lifecycle.md`
  - `runs/20260719T125756-0300-full-replacement-candidate/build-stream-conductor-compliance.md`
- The candidate code and benchmark evidence remain valid as an isolated sidecar candidate, but conductor-owned planner/implementer/reviewer/fixer attribution and convergence require another run from a real terminal watcher.

## 2026-07-19 Raw LLM Evidence Requirement

Owner added a hard requirement that every LLM call used in tests/evals/judging/article work
must save raw prompt/input and model output for later inspection, separate from aggregate
metrics and analysis.

Actions:

- Updated `/Users/user/Documents/Istara-main-pi-replacement/labs/pi-replacement/scenarios/collect-replacement-artifacts.mjs`
  to write required-schema raw prompt/output JSONL under `raw-llm-calls/`.
- Exported the adapter system prompt from `src/istara-pi-adapter.mjs` so reconstructed prompt
  records include the actual system prompt used by the Pi candidate.
- Regenerated current run artifacts without a new live LLM call.
- Added `raw-llm-calls/manifest.json` with counts, redaction/capping policy, reconstruction notes,
  baseline LLM-call count, and missing-capture status.
- Expanded `scores.json.owner_dimensions` to include the owner's required dimensions:
  tool calling, feature integration/adherence, final output quality proxy, research-spine
  steps, memory load, tokens by step and total, tool calls versus quality, skills adherence,
  system prompt adherence, and A2A task success/efficiency.

Current raw evidence:

- `raw-llm-calls/prompts.jsonl.gz`: 22 records.
- `raw-llm-calls/outputs.jsonl.gz`: 22 records.
- 21 Pi candidate deterministic faux-provider records reconstructed from scenario fixtures.
- 1 Pi candidate DeepSeek smoke record reconstructed from the fixed smoke prompt and existing
  live-provider artifact.
- 0 baseline Istara LLM calls in this deterministic contract run.
- Missing raw capture: none identified for current-run LLM calls.
- Additional live spend introduced by this correction: USD 0.00.

## 2026-07-19 Real Istara-Loop Bridge Round

This run created `runs/20260719T145107-0300-real-istara-loop-bridge/` and strengthened
the isolated Pi candidate from representative demo slices into a real Istara-loop bridge
candidate.

Code changed in `/Users/user/Documents/Istara-main-pi-replacement/labs/pi-replacement`:

- Added `src/istara-surface-map.mjs` and `src/istara-service-bridge.mjs` mapping real
  Istara routes/services/tests/docs to lab bridge surfaces and production blockers.
- Extended `src/canonical-tool-facade.mjs` for Autoresearch, ReasoningBank, Memento,
  webhook, steering, system-prompt audit, and benchmark-contract tools.
- Extended `src/scenario-catalog.mjs`, `src/istara-pi-adapter.mjs`, the collector, role
  lanes, tests, and README for 15 bridge scenarios.

Mapped surfaces:

- chat/tool loop; Autoresearch governance; plan/review state; tasks/findings/documents;
  memory/RAG/ReasoningBank/Memento/skills; A2A/reports; channels/webhooks/Telegram-like
  lifecycle; steering/system-prompt; telemetry/tokens/tool metrics; benchmark/eval/
  simulation/real-user contracts.

Command evidence:

- `npm run validate` -> 5 Node tests passed.
- `npm run smoke:no-model`, `npm run smoke:all-no-model`, and `npm run paired:no-model`
  passed against the expanded scenario catalog.
- `npm run smoke:deepseek -- --out <run-folder>` passed with DeepSeek `deepseek-v4-pro`.
- `npm run role-rounds:deepseek -- --out <run-folder> --max-calls 2 --roles code-reviewer,code-reviewer-rereview`
  passed; final re-review returned `{"status":"pass","remaining_blockers":[]}`.
- `npm run collect:artifacts -- --out <run-folder>` generated the required bridge artifacts.
- `python scripts/security_benchmark.py --fail-on-threshold` passed at 100.0 percent.

Metrics:

- 15/15 deterministic baseline scenarios passed.
- 15/15 Pi-owned candidate scenarios passed.
- 56/56 candidate canonical tool calls succeeded.
- 10/10 mandatory real-loop surfaces covered, with 29 canonical bridge tools.
- Raw LLM capture: 44 prompt records and 44 output records; 41 faux-provider records plus
  3 direct DeepSeek records.
- Added DeepSeek spend: USD 0.00339262; remaining cap after this round: USD 0.40564439.

Compass Forge:

- Created and accepted `CF-SPEC-2`.
- Completed `CF-23` through `CF-36`.
- Attached artifact, command, gate, review, and security benchmark evidence.
- After-gate had no new failures; inherited `unexpected_large_files` remained.

Current interpretation:

- Strong enough for broader deterministic benchmarking as a replacement engine.
- Still not production replacement: real FastAPI/DB/service integration, external channel
  credentials, production telemetry rows, human Done/report gates, full multi-model
  reconciliation, and full real-user harness fanout remain explicit gaps.
