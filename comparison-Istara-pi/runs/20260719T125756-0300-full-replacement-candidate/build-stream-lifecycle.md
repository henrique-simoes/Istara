# Build Stream Lifecycle

```yaml
item: pi-full-replacement-candidate
branch: comparison/pi-replacement-core
cf:
  target: /Users/user/Documents/Istara-main
  recipe: istararustgraphtrial
  spec: null
  tasks: []
phase: "Phase 1 - isolated replacement candidate"
stage: S5-ship
status: done-with-limitations
blocked_on: null
last:
  agent: gpt-5-codex-openclaw
  at: 2026-07-19T13:31:31-03:00
  ledger: L-9
next_action: "For the next adapter round, capture raw prompt/output JSONL for every LLM call before running analysis or article judging."
```

## Roadmap

Goal: create a robust isolated Pi replacement candidate that can run representative Istara harness-derived scenarios through Pi-owned loops without modifying main Istara app code outside `comparison-Istara-pi/`.

Acceptance:

- Candidate code exists in `/Users/user/Documents/Istara-main-pi-replacement/labs/pi-replacement`.
- Baseline and candidate representative scenarios both run and emit comparable artifacts.
- DeepSeek is the only live provider used, with spend under USD 0.50.
- Artifacts state claim boundaries and next adapter gaps.
- Build Stream Conductor compliance is explicit: literal, partial, or blocked.

## Decision Log

DEC-1 | 2026-07-19 | S0-frame | owner
Context: Prior Pi provider and replacement runs were insufficient.
Decision: Build a real isolated candidate in the replacement worktree and keep main Istara app code untouched outside comparison artifacts.
Why: The comparison needs candidate code and command evidence, not inventory or provider smoke.

DEC-2 | 2026-07-19 | S2-execute | gpt-5-codex-openclaw
Context: The available session was already a depth-limited OpenClaw subagent.
Decision: Implemented role-separated architect/implementation/review passes manually and recorded the child-lane limitation.
Why: No safe nested child lanes were available from the session.

DEC-3 | 2026-07-19 | S5-ship | gpt-5-codex-openclaw
Context: Owner later clarified that `/skill build-stream-conductor` was specifically required.
Decision: Loaded the Build Stream Conductor, Build Stream, and Compass Forge contracts; ran CF orientation/impact/test-impact and conductor tooling probes; did not fabricate a literal conductor run after implementation had already completed.
Why: `conductor.py status` failed because `.compass-forge/conductor/cast.json` does not exist, there were no conductor-generated CF tasks/evidence rows, and this OpenClaw subagent is not the required real terminal watcher environment for spawning standalone workers.

DEC-4 | 2026-07-19 | S5-ship | gpt-5-codex-openclaw
Context: Owner required raw prompt/input and model-output storage for every LLM call used in tests/evals/judging/article work.
Decision: Regenerated current run raw LLM evidence as gzipped JSONL under `raw-llm-calls/`, kept raw evidence separate from analysis, and added owner metric dimensions under `scores.json.owner_dimensions`.
Why: Aggregate token/tool metrics are not enough for later inspection; normal prompt/output text must remain inspectable while secrets and credentials stay out of artifacts.

## Ledger

### L-1 | 2026-07-19T12:57:56-03:00 | S0-frame | gpt-5-codex-openclaw | framer | Phase 1
Did: Framed the owner requirement, read comparison plan artifacts, and created run folder `comparison-Istara-pi/runs/20260719T125756-0300-full-replacement-candidate/`.
Result: Scope set to isolated replacement worktree code plus comparison artifacts only.
Verified: `git status --short` and artifact folder creation checks.
Next: Build architecture map and implementation plan.

### L-2 | 2026-07-19T13:00:00-03:00 | S1-plan | gpt-5-codex-openclaw | architect-a | Phase 1
Did: Mapped Istara insertion contracts and harness sources: benchmark/eval runner, agentic eval contract, real-user/simulation scenario families, chat/tools, tasks/documents, memory/RAG, skills, A2A, channels, and telemetry.
Result: Eight representative scenario families selected.
Verified: CF impact/test-impact commands recorded in `compass-forge-dependency-map.md`.
Next: Implement the Pi candidate harness.

### L-3 | 2026-07-19T13:04:00-03:00 | S2-execute | gpt-5-codex-openclaw | architect-b-executor | Phase 1
Did: Expanded `/Users/user/Documents/Istara-main-pi-replacement/labs/pi-replacement` with the scenario catalog, canonical facade, generic Pi scenario runner, baseline contract runner, and artifact collector.
Result: Candidate now runs representative Istara-shaped slices through Pi-owned Agent loops.
Verified: `npm run validate` passed 4 tests.
Next: Run paired deterministic baseline/candidate scenarios and native harness slices.

### L-4 | 2026-07-19T13:08:00-03:00 | S2-execute | gpt-5-codex-openclaw | tester | Phase 1
Did: Ran paired scenario artifact collection plus native Istara contract/eval and orchestration benchmark slices.
Result: Baseline 8/8 and candidate 8/8 deterministic scenarios; 12 native eval/contract tests passed; 5 orchestration benchmark tests passed.
Verified: `npm run collect:artifacts -- --out ...`, `pytest tests/test_agentic_eval_contract.py tests/test_istara_eval_runner.py`, and `pytest tests/benchmarks/test_orchestration.py -q`.
Next: Run bounded DeepSeek provider smoke.

### L-5 | 2026-07-19T13:10:00-03:00 | S2-execute | gpt-5-codex-openclaw | tester | Phase 1
Did: Ran Pi ai DeepSeek smoke with runtime-only key retrieval and raw prompt/output capture.
Result: Passed, 47 tokens, USD 0.00003654 provider-reported cost; no local models.
Verified: `npm run smoke:deepseek`.
Next: Review claim boundaries and adapter gaps.

### L-6 | 2026-07-19T13:12:00-03:00 | S3-review | gpt-5-codex-openclaw | architect-c-reviewer | Phase 1
Did: Reviewed methodology, artifacts, and coverage matrix for overclaiming and missing surfaces.
Result: Findings were documented as remaining risks: in-memory envelopes, deterministic broad run, simulated A2A/channel credentials, no production route replacement.
Verified: `adapter-coverage-matrix.md`, `review-remediation.md`, and `final-outlook.md`.
Next: Remediate artifact completeness.

### L-7 | 2026-07-19T13:15:00-03:00 | S4-remediate | gpt-5-codex-openclaw | remediator | Phase 1
Did: Added final artifact set including status, implementation ledger, CF map, coverage matrices, scenario inventory, paired plan, traces/outputs, scores, benchmark results, review/remediation, cleanup, outlook, and root comparison doc updates.
Result: Run artifacts complete for the originally assigned non-conductor implementation round.
Verified: Artifact listing and cleanup/storage checks.
Next: Apply Build Stream Conductor clarification.

### L-8 | 2026-07-19T13:21:48-03:00 | S5-ship | gpt-5-codex-openclaw | compliance-reviewer | Phase 1
Did: Loaded Build Stream Conductor, Build Stream, and Compass Forge skills; ran CF orientation, compact brief, targeted impact, test-impact, conductor status probe, routing registry show, scorecard, and conductor script help probes.
Result: Literal Build Stream Conductor pipeline was not used and is blocked for this completed run because no cast exists and no watcher-owned CF task graph/evidence exists; closest compliant structure is now recorded with model/round attribution and explicit limitation.
Verified: `compass-forge status`, `compass-forge next`, `compass-forge agent-brief --compact --max-seconds 45 --request ...`, `compass-forge intelligence impact ...`, `compass-forge intelligence test-impact ...`, `python3 .../conductor.py status --project-root ... --brief` -> failed missing cast, `python3 .../routing.py show --root ...`, `python3 .../scorecard.py --project-root ...` -> empty models.
Next: Run a fresh literal conductor pipeline from a real terminal for the next implementation round if conductor-owned evidence is mandatory.

### L-9 | 2026-07-19T13:31:31-03:00 | S5-ship | gpt-5-codex-openclaw | evidence-remediator | Phase 1
Did: Updated the isolated collector to emit raw prompt/output JSONL for deterministic Pi faux-provider calls, reconstructed the DeepSeek smoke raw record from existing artifacts, added `raw-llm-calls/manifest.json`, and expanded `scores.json.owner_dimensions`.
Result: `raw-llm-calls/prompts.jsonl.gz` and `raw-llm-calls/outputs.jsonl.gz` now contain 22 records each: 21 Pi faux-provider calls and 1 DeepSeek smoke call. Baseline Istara has 0 LLM calls in this run. No new live LLM call or spend was introduced.
Verified: `npm run validate` -> 4 passed; `npm run collect:artifacts -- --out ...` -> baseline 8/8, candidate 8/8, raw records 22/22; `pytest tests/test_agentic_eval_contract.py tests/test_istara_eval_runner.py tests/benchmarks/test_orchestration.py -q` -> 17 passed; raw JSONL schema/secret-pattern validator -> passed; `compass-forge gate after --summary` -> warn only, failures=0, new_failures=0, security=0.
Next: For future live or judge calls, write raw prompt/output records first, then update scores and article analysis.
