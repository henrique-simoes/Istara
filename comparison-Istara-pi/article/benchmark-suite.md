# Benchmark Suite

## Scenario Families

- Tool calling and invalid-call recovery.
- Research spine quality.
- Memory/RAG loading and contamination resistance.
- Skill and prompt adherence.
- A2A collaboration.
- Channel and SDK/process integration.
- Provider/model management.
- Full feature matrix sweep.

## First-Run Scope

This conductor run only authorizes:

- A no-model schema and article validator.
- One Istara-compatible DeepSeek connectivity smoke.
- One Pi provider dependency smoke through `@earendil-works/pi-ai`.

The next benchmark stage is not standalone Pi execution. It must first build an isolated
Istara worktree or sidecar replacement harness that routes Istara feature scenarios through
Pi-owned agent/provider code. Live paired metrics from that harness are `TBD-evidence`
pending owner budget approval.

Replacement score coverage must come from Istara's existing harness backbone:

- `tests/benchmarks/`
- `tests/evals/`
- `scripts/run_istara_evals.py`
- `tests/agentic_eval_contract.json`
- `tests/real_user_benchmark/`
- `tests/simulation/scenarios/`

Standalone Pi/provider results count only as package-boundary preflight.
