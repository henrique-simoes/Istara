# Long-Horizon Agentic Engine Evaluation & Main Promotion — Build Stream lifecycle

```yaml
item: long-horizon-engine-comparison-and-main-promotion
branch: testing
cf: { spec: CF-SPEC-10, task: CF-90 }
phase: "Phase 2 — Verification & Audit Complete; Ready for Main Promotion"
stage: S3-review
status: ready-for-review
blocked_on: null
last: { agent: antigravity, at: 2026-09-05T00:55:00Z, ledger: L-405 }
next_action: "Review scorecard artifact at docs/scientific_audit/long-horizon-agentic-engine-audit.md, commit testing branch changes, and open candidate promotion PR to origin/main."
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
