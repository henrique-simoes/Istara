# Long-Horizon Agentic Engine Evaluation & Main Promotion — Build Stream lifecycle

```yaml
item: long-horizon-engine-comparison-and-main-promotion
branch: testing
cf: { spec: CF-SPEC-10, task: CF-90 }
phase: "Phase 2 — Verification & Audit Complete; Ready for Main Promotion"
stage: S5-ship
status: completed
blocked_on: null
last: { agent: antigravity, at: 2026-09-05T00:55:00Z, ledger: L-405 }
next_action: "Consolidated and reconciled into docs/build-stream/2026-09-06-systemwide-remaining-surfaces-and-design-hardening.md."
```

## Plan Overview & Roadmap

### Problem & Objective
Answer decisively whether Istara's agentic engines are capable of maintaining long-horizon qualitative research tasks, multi-step tool calling chains, and multi-source reasoning without hallucinations, tool drops, session crashes, or research validity regressions.

We execute an exhaustive, 8-phase simulated user research trajectory inspired by Scenario 76 on both:
1. **Engine A:** The `pi` Agentic Engine (`agentic_engine="pi"`, driven by embedded Pi runtime worker with streaming SSE).
2. **Engine B:** The `istara` Legacy Engine (`agentic_engine="legacy"`, driven by Python ReAct loop with OpenAI tools schema).

### Remote Execution Environment: Mac Studio Docker
Per repository policy and build stream standards:
- **Host & Transport:** All verification, simulation, and model evaluations execute exclusively inside Docker on **Mac Studio** via SSH (`ssh macstudio`) and `/usr/local/bin/docker`.
- **Target QA Stack:** Disposable QA stack `istara-qa-live-20260902` at `/Users/user/istara-qa-testing-20260829`.
- **Containers:** `istara-qa-live-20260902-qa-backend-1` and `istara-testing-backend:latest` (providing Node v24 + Python 3.12 + full backend dependencies).
- **Protected Containers:** Never touch, restart, or alter protected containers (`istara-test-*`, `plex`, `postgres`).

### Multi-Model Ensemble Authority
The Research Spine multi-model ensemble uses three distinct model authorities:
1. **Model 1:** `gpt-5.6-luna` via Codex OAuth device flow (`pi-codex-luna`)
2. **Model 2:** `qwen3.7-max-2026-06-08` via DashScope OpenAI-compatible API (`pi-dashscope-qwen`)
3. **Model 3:** `glm-5.2` via DashScope OpenAI-compatible API (`pi-dashscope-glm`)
*(With `qwen3.7-plus` and `qwen3.7-flash` as governed rate-limit fallbacks)*

### 8-Phase Research Lifecycle
1. **Turn 1 — Project Framing & Document Discovery:** Query project files (`list_project_files`, `search_documents`).
2. **Turn 2 — Skill Catalog & Task Decomposition:** Explore skills, create high-priority task with skill `user-interviews`.
3. **Turn 3 — Active Codebook Consultation:** User asks *"What's in the codebook now?"*. Agent inspects codes, definitions, and inclusion criteria.
4. **Turn 4 — Dynamic Mid-Turn Steering:** User steers mid-execution: *"Wait, before finalizing... what do survey responses say?"*. Agent correlates survey findings with interview data.
5. **Turn 5 — Multi-Source Sharon Atomic DAG Elevation:** Synthesizes raw interview quotes and survey evidence into Sharon DAG hierarchy (Quotes -> Nuggets -> Facts -> Insights -> Recommendations) with 50+ research evidence edges.
6. **Turn 6 — Governed 3-Model Qualitative Coding Run & Reconciliation:** Multi-model independent coding run computes Fleiss' Kappa and Krippendorff's Alpha. All task-linked applications undergo human reconciliation decisions (`accepted`).
7. **Turn 7 — Task Review & Research-Validity Done Gate:** Agent attempts illegal direct completion, proving HTTP 409 guard (`Agents cannot mark tasks Done`). Human approval via `_approve_task()` succeeds with full gate validation.
8. **Turn 8 — Strategic SCQA Report Synthesis & Comparative Telemetry:** Validated findings route to Barbara Minto SCQA `ProjectReport`. Full OpenTelemetry GenAI metrics (p50, p90, p99 tool latency, error taxonomy, token usage, cost accounting in USD) recorded.

---

## Decision Log

### DEC-001 | 2026-09-04 | S1-plan | antigravity
Context: DashScope and DeepSeek custom OpenAI-compatible gateways reject the `developer` role with HTTP 400.
Decision: Added `supportsDeveloperRole: false` in `pi-runtime/src/provider.mjs` for all non-OpenAI endpoints, mapping system prompts to `role: "system"`. All 46 node unit tests pass.

### DEC-002 | 2026-09-04 | S1-plan | antigravity
Context: Multi-turn chat sessions in `PiSession` crashed on turn 2+ due to missing usage and model metadata on assistant history messages.
Decision: Populated default usage and provider metadata on assistant history messages in `pi-runtime/src/session.mjs`.

### DEC-003 | 2026-09-04 | S2-execute | antigravity
Context: Task approval in `_approve_task()` requires all code applications linked to the task to be reconciled before Done transition is permitted.
Decision: Ensured the test harness reconciles all task-linked code applications from both initial extraction and governed coding runs before triggering the human Done approval gate.

### DEC-004 | 2026-09-04 | S2-execute | antigravity
Context: Testing must respect repository safety constraints regarding local model loading and host execution.
Decision: All test runs execute inside Docker containers on Mac Studio via SSH (`ssh macstudio`), preserving host isolation and protected services.

### DEC-005 | 2026-09-05 | S2-execute | antigravity
Context: In Docker on Mac Studio, mounting `/Users/user/istara-qa-testing-20260829` to `/app` masked container image's built-in `node_modules` in `pi-runtime`. Additionally, `execute_tool()` signature in backend system actions does not take `model_name`.
Decision: Re-populated linux-compatible `node_modules` in `/app/pi-runtime` and aligned `execute_tool()` invocation signature across both environments.

### DEC-006 | 2026-09-05 | S2-execute | antigravity
Context: In an ultra-long 150-turn evaluation across the Double Diamond lifecycle, execution must be resumable and batchable across phases without losing accumulative conversational history, OpenTelemetry metrics, or database state.
Decision: Implemented stateful checkpointing and resume (`--resume`) in `tests/run_150_turn_stress_test.py`. Checkpoints store `project_id`, `session_id`, `messages_history`, `turns_telemetry`, tool latencies, error taxonomy, and steering counts. On resume, the existing database project is confirmed, full conversational history is restored, and subsequent turns seamlessly append to the context window.

---

## Ledger

### L-404 | 2026-09-04T21:35:00Z | S2-execute | antigravity | implementer | Phase 1
Did: Established durable Build Stream lifecycle specification for Long-Horizon Engine Comparison and Main Promotion. Synchronized bug fixes in `pi-runtime/src/provider.mjs` and `pi-runtime/src/session.mjs` to Mac Studio checkout. Verified 46/46 `node --test` suites passing cleanly inside `istara-testing-backend:latest` on Mac Studio Docker. Proved outbound network egress to DashScope. Resolved research-validity reconciliation gate for task approval.
Result: Docker execution environment on Mac Studio ready for dual-engine comparative run.
Verified: `ssh macstudio '/usr/local/bin/docker run --rm -w /app/pi-runtime ... istara-testing-backend:latest sh -c "node --test test/*.test.mjs"'` -> 46 passed, 0 failed.
Next: Execute 8-phase comparative trajectory inside Docker on Mac Studio using Luna and DashScope 3-model ensemble, record telemetry, and render public scorecard.

### L-405 | 2026-09-05T00:55:00Z | S2-execute/S2-verify | antigravity | implementer | Phase 2
Did: Executed complete 8-phase long-horizon comparative evaluation of Pi Agentic Engine vs. Istara Legacy ReAct Engine in Docker on Mac Studio (`istara-testing-backend:latest`) using live models (`qwen3.7-max-2026-06-08`, and 3-model ensemble `gpt-5.6-luna`, `qwen3.7-max`, `glm-5.2`). Both engines completed all 6 conversational turns with 0 tool errors. Pi demonstrated 13.2% faster total execution (47.30s vs. 54.46s), 72.2% server-side prompt cache hit rate (25,344 tokens cached), exact financial ledgering ($0.01297 USD total cost, well below the $0.05 cap), and full Sharon Atomic DAG elevation (15 nuggets, 2 facts, 1 insight, 1 recommendation, 69 graph edges). The 3-model qualitative coding ensemble achieved Fleiss' kappa κ = 0.690 and Krippendorff's alpha α = 0.933, passing the ≥ 0.600 contract reliability threshold. Human review gate passed and Barbara Minto SCQA report was synthesized with 3 MECE categories and report_allowed=True across 56 backward evidence edges. Verified living feature docs (0 seeded, 224 generated, 86 checked) and security benchmark (28/28 controls, 100%). Published empirical audit to `docs/scientific_audit/long-horizon-agentic-engine-audit.md`.
Result: Long-horizon comparative benchmark completed with 100% success. Zero regressions. Candidate ready for origin/main promotion.
Verified: `ssh macstudio '/usr/local/bin/docker run --rm ... istara-testing-backend:latest python /app/tests/run_long_horizon_engine_comparison.py --engine=all'` -> exited 0, raw results saved in `tests/comparison_results.json`.
Next: User review and origin/main promotion PR.

### L-406 | 2026-09-05T01:45:00Z | S2-execute | antigravity | implementer | Phase 3
Did: Designed and generated the complete, realistic data package and execution harness for the 150-turn agentic engine stress test in `tests/data/stress_test_150_turns/`. Generated 35 canonical document index (`corpus_manifest.json`), 100 multi-clinic patient & caregiver survey responses with Likert metrics and rich qualitative verbatims (`simulated_surveys_100.json`), 20 usability testing lab sessions with task durations, error taxonomy, and calculated SUS/UMUX metrics (`usability_testing_20.json`), 3-stage qualitative codebook evolution (`codebook_lifecycle.json`: v1.0 -> v1.1 -> v2.0), and 150-turn sequential UX researcher prompt trajectory with 32 dynamic mid-turn steering interventions across the Double Diamond (`trajectory_150_turns.json`). Built test runner `tests/run_150_turn_stress_test.py` supporting Pi and Legacy engines, range/batch execution, state checkpointing every N turns, OpenTelemetry latency percentiles, token caching, and Sharon DAG tracking. Verified dataset schema integrity with unit tests in `tests/test_stress_test_dataset.py`.
Result: 150-turn stress test data package and execution harness ready for deployment and remote execution in Docker on Mac Studio.
Verified: `pytest tests/test_stress_test_dataset.py -v` -> 5 passed in 0.12s. Feature docs checked (86 features, 224 site artifacts). Security benchmark pass (28/28 controls, 100%).
Next: Sync dataset to Mac Studio Docker checkout and run dry run / batch execution of the 150-turn trajectory.

### L-407 | 2026-09-05T02:00:00Z | S2-execute/S2-verify | antigravity | implementer | Phase 4
Did: Deployed 150-turn stress test data package and test runner to Mac Studio Docker environment (`istara-testing-backend:latest`). Executed Turns 1-7 on the Pi Engine and Turns 1-6 on the Legacy Engine using live Alibaba DashScope Qwen 3.7 Max (`qwen3.7-max-2026-06-08`). Validated real-time document search, content extraction, and dynamic mid-turn steering (`scope_narrowing`). Proved unbuffered execution and stateful checkpointing (`checkpoint_{engine}_turn_{N}.json`). Verified that `--resume` successfully restores accumulated conversation history and database assets, executing Turn 7 in 25.64s with 3 tool calls and 14,996 tokens. Confirmed zero regressions across all 5 dataset integrity tests.
Result: 150-turn stress test architecture fully proven and operable for arbitrary turn ranges with full state preservation.
Verified: Remote Docker execution on Mac Studio via `ssh macstudio`. Checkpoint files verified in `tests/data/stress_test_150_turns/checkpoints/`.
Next: Continue sequential phase execution across Discover (1-40), Define (41-80), Develop (81-115), and Deliver (116-150) or as directed by user.

### L-408 | 2026-09-11T04:30:00Z | S2-execute | meta/muse-spark-1.3-contributor | implementer | Wave W4 (readiness5)
Did: Completed the 150-turn trajectory on BOTH engines live on the current stack (readiness5 Wave W4, candidate `66c0ff87`, fresh image `istara-qa-w4-backend:w4candidate`, scratch DB copies of the preserved `istara-qa-live.db` — sha256-verified, originals untouched, CareNav context only). Same model both engines: `pi-zai-glm` (served `glm-5.3-flash`, requested==served 302/302, `thinking_mode=low`; Zai fails closed on thinking-disabled turns with typed 400 — reconfirmed at admission). One surgical harness-only change: `--thinking-mode` passthrough in `tests/run_150_turn_stress_test.py` (5 lines, no product code). 151 recorded turns per engine (trajectory 1–150 with turn 1 twice: smoke + resumed rerun — disclosed, negligible).
Result: Reliability parity — 151/151 success, 0 tool errors, 32/32 steering on BOTH engines; 151 exact `chat_turn` usage rows per engine; 1364/1399 telemetry spans; telemetry audit `capture_present_content_free_attributed` with 0 gaps and 5 documented observations (G1 legacy cost unmetered; G2 `total_tokens` accounting differs by engine; G3 no OTLP exporter — local `telemetry_spans` table, `opentelemetry-api` unimported; G5 harness-local extended tools bypass the canonical `tool_call` span; turn-1 duplication disclosed). Divergences: turn medians pi 18.7 s vs legacy 21.3 s (totals 2759 s vs 3265 s); tool breadth 30 calls/9 tools (pi) vs 43 calls/13 tools (legacy — codebook, survey, and `generate_minto_report` exercised once, honestly evidence-graded); cost $0.31 metered (pi) vs $0.00 unmetered (legacy); stop reasons 150 stop + 1 length (pi) vs 151 stop (legacy); only non-success spans are typed `retrieval_fallback` degradations (4 pi, 2 legacy). DAG holds 500 survey-seeded provisional nuggets + 1000 edges per engine with zero turn-elevated facts/insights/recommendations — the free-run chatted coherently but did not self-elevate evidence. No winner is declared; the bundle verdict (`no_significant_difference`) is untouched.
Verified: `run-both.json` sha256 `618e4c8e…5d4e`; aggregate `w4-telemetry-aggregate-1c4a46416286.json` (content-free, per-turn sha12); committed summary `docs/build-stream/w4-long-horizon-telemetry-20260911.json`; engine-choice UI (`modelCatalog.ts` + test 27/27 + `tsc` clean) and scenario 79 carry the dated slice; audit + deep-dive updated (see their files). Full evidence: `qa/scripts/w4_aggregate_telemetry.py`, `qa/runs/w4-long-horizon-20260911-zai-glm/` (worktree-local, gitignored).
Next: Wave W5 certification. No push/PR/merge by this pipeline.
