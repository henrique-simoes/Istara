# Agentic Engine Evaluation Log — Istara vs Pi, before/after long-horizon changes

Purpose: one append-only registry of every long-horizon/ensemble evaluation run so the agentic
engine's behaviour can be compared **before** and **after** the `CF-SPEC-19` improvement phases,
and against the Pi engine, using the same metrics, the same scenarios, and Istara's own
telemetry. Research-grade: evidence paths and exact numbers, not prose.

Status: initial draft (2026-09-11). Historical baselines captured; W4 (150-turn both engines)
rows are placeholders until its commit; post-`CF-SPEC-19` rows are reserved per phase.

## Ground rules

- **Append-only.** Never rewrite a past run; add a new row/entry. Corrections are new entries.
- **SHA-bound.** Every row names the exact commit the run executed on.
- **Both engines.** Every comparison scenario runs `legacy` and `pi`; a row with only one engine
  says why.
- **Content-free telemetry.** Handles/IDs/counts only — no prompts, quotes, document bodies,
  URLs, tokens (see `docs/architecture/research-validity-contract.md` §Telemetry).
- **No corpus mingling.** CareNav runs use CareNav corpora/projects only; any new public corpus
  gets its own project and its own rows.
- **No Petals inference.** Petals paths are excluded from these runs.
- **Evidence lives outside the repo** for large artifacts: Mac Studio
  `~/w4-scratch-<date>/`, `~/istara-qa-<run>/qa/runs/<run-id>/`, or the worktree's ignored
  `tests/simulation/.results/`; this file records the paths and the numbers.

## Metric framework (industry-standard + Istara-native)

| Metric | Definition | Istara source | Notes |
|---|---|---|---|
| Task completion | % of scenario turns completed; typed stop reason (`stop`, `turn_budget_exceeded`, cost cap, error) | per-turn results JSON; `agentic_usage_rows` | never count a budget stop as success |
| Turns used / budget | turns consumed vs configured budget per question | turn results (`total_turns`); run summary | depth signal from CF-SPEC-19 E1 |
| Tool calls | calls per turn, distinct tools, sequential depth | `pi_tool_executions`; telemetry spans | tool-drop detection |
| Tool success + error taxonomy | success rate; typed errors (timeouts, 4xx/5xx, refusals) | `telemetry_spans`, error rows | zai-glm typed 400/1210 is a known typed refusal |
| Latency | p50/p90/p95/p99 per turn and per tool | run results (`p50_duration_s` …); OTel spans | per engine and per model |
| Tokens + cost | in/out/cache tokens, USD, cache-hit rate | `agentic_usage_rows`, usage ledger | exact only when `estimate=false` |
| Steering responsiveness | mid-run steering events honored; recovery after steering | turn log steering lines; `steering_queue` events | 32 steering interventions in the 150-turn trajectory |
| Grounding / provenance | exact-span quotes; requested==served model identity; route receipts | `code_applications`, `coding_run_coders`, route evidence | identity mismatch is a failure, not a warning |
| Multi-model reliability | Fleiss κ, Krippendorff α, gate outcome (`accepted*`, `needs_reconciliation`, `blocked`) | `coding_runs`; W3 artifacts | small-n runs are labeled operational |
| Ensemble/MoA behaviour | adversarial passes, debate passes, self_moa degradation labels | validation results; W3 Stage D artifacts | degraded modes must be typed |
| Telemetry completeness | spans per turn, attribution coverage, content-free compliance | telemetry audit route / aggregates | audited in W4 |

## Run registry (append new rows at the bottom)

| # | Date (UTC) | SHA | Engine(s) | Endpoints / models | Scenario | Turns | Steering | Result | Reliability / gates | Latency · tokens · cost | Evidence path |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2026-09-04 | (pre-L-404 baseline) | pi + legacy | qwen3.7-max; 3-model ensemble: gpt-5.6-luna, qwen3.7-max, glm-5.2 | 8-phase long-horizon comparison (6 turns) | 6 | — | 100% turns, 0 tool errors | κ 0.690 / α 0.933 (≥0.600) | Pi 47.30s vs legacy 54.46s; 72.2% cache hit; $0.01297 total | `docs/build-stream/2026-09-04-long-horizon-engine-comparison-and-main-promotion.md` L-405 |
| 2 | 2026-09-05 | preserved-run DB `proj-st150-pi-dd6bf277` | pi | (live endpoints of that run) | 150-turn Double Diamond trajectory | checkpoints to **150** | 32 planned; partial recorded | Full-length Pi run checkpointed; results file retained a 30–40 range | n/a (conversational run) | partial | `~/istara-qa-testing-20260829/.qa-shared/istara-qa-150turn-persisted.db` + `tests/stress_test_150_results.json` |
| 3 | 2026-09-11 | `97dbb2ce` | pi (3-model via Pi model management) | pi-zai-glm, pi-codex-luna, pi-codex-terra | W3 live 3-model coding (6 CareNav units) + adversarial/debate/ensemble | n/a | n/a | completed; evidence promoted after reconciliation | **κ −0.102 / α 0.493 → needs_reconciliation** (small-n, live); post-fix D: 3/3 passes with model+served_model, models_used=3; 5/5 fail-closed probes typed; `full_ensemble` → labeled `self_moa` | receipts per pass; run ids `baf9cc41`, `c4f87bfb`, `9a7bb6ee` | `qa/runs/w3-live-ensemble-2026-09-11T02-32-09Z-97dbb2ce/` (Mac Studio + worktree) |
| 4 | 2026-09-11 | `9aa3034a` | legacy + pi (separate runs) | pi-zai-glm (served glm-5.3-flash; requested==served 302/302) | **W4 150-turn both engines** (151 recorded turns = 1–150 + turn-1 warm-up), 32 planned steering each | 151/151 each | 32/32 applied each | both all-success (pi: stop 150 + 1 `length`) | telemetry audit `capture_present_content_free_attributed`; gaps G1/G2/G3/G5 | **pi**: p50 18.7 / p90 25.1 / p99 33.0 s · 2759 s total · **$0.307 metered** · 30 calls / 9 tools · input 2.66 M / output 75 k tokens · spans 1364. **legacy**: p50 21.3 / p90 28.4 / p99 39.0 s · 3265 s total · unmetered (G1) · 43 calls / 13 tools (incl. codebook/survey/report-once) · input 148 k / output 85 k · spans 1399. 0 tool / 0 turn errors both | `docs/build-stream/w4-long-horizon-telemetry-20260911.json`; `qa/runs/w4-long-horizon-20260911-zai-glm/` (worktree) and `~/w4-scratch-20260910/` (Mac Studio) |
| 5 | reserved | post-`CF-SPEC-19` phase N | legacy + pi | same as row 4 | same 150-turn matrix + depth-eval harness | — | — | — | — | — | append per phase (CF-193…CF-202) |

## Entry template (copy for each new run)

```
### <run-id> | <ISO date> | <SHA> | engine=<legacy|pi> | models=<...>
Scenario: <name>  Turns: <completed>/<budget>  Steering: <n>
Completion: <typed stop reason>            Tool calls: <n> (errors: <n by class>)
Latency: p50 <s> p90 <s> p99 <s>           Tokens: in/out/cache  Cost: $<x>
Reliability (if coding): Fleiss κ <x> / Krippendorff α <x>  Gate: <outcome>
Grounding/identity: requested==served <yes/no>  Route receipts: <path>
Telemetry: spans <n>, attribution coverage <n%>, content-free audit <pass/fail>
Evidence: <artifact path(s)>   Notes/residuals: <...>
```

## Known residuals to carry into every future comparison

- **W4 telemetry gaps (audit record)**: G1 legacy cost unmetered; **G2 `total_tokens` accounting
  differs by engine — compare input/output only**; G3 no OTLP exporter (spans are the local
  `telemetry_spans` table; `opentelemetry-api` is an unimported dependency); G5 harness-local
  extended tools bypass the canonical tool-call span.
- Multi-model reliability on small corpora is operational only; formal inference needs a larger
  unit set (the 150-turn corpus provides 1,000+ evidence units — prefer it for κ/α claims).
- Debate passes default to the dispatcher's route (no rotation) unless explicitly configured.
- Secret-less endpoints fail closed at `resolve_distinct`; `full_ensemble` degradation to
  `self_moa` is honest but must always be labeled.
- `desktop-check` and CI evidence are release gates, not engine metrics; keep them out of this
  engine log except where a run itself was blocked by a gate.
