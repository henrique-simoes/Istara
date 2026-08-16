# Methodology

The lab uses paired scenarios through engine adapters. Each scenario runs against Istara and
Pi with the same prompt, model policy, tool facade, memory inputs, max steps, and stopping
criteria.

No-model validators run first. Live cloud calls start with one small DeepSeek smoke. The
replacement evaluation then requires an isolated Istara worktree or sidecar harness that
wires Pi into Istara feature contracts through adapters/canonical tools; paired live
metrics from that harness run only after owner budget approval.

The Pi provider path is now validated with `@earendil-works/pi-ai@0.80.10` in library mode:
Pi's built-in `deepseekProvider()` can call `deepseek-v4-pro` with high reasoning and
thinking enabled. Paired benchmark methodology should therefore use the built-in Pi
DeepSeek provider first, with custom provider configuration reserved for later failures or
adapter experiments.

This provider smoke is prerequisite evidence only. It must not be counted as a standalone
Pi replacement test because it does not exercise Istara agentic loops, feature contracts,
memory policy, A2A behavior, channel behavior, or canonical tools through a Pi-owned engine.

Replacement scores must be produced by routing Istara's existing coverage backbone through
the Pi candidate path: `tests/benchmarks/`, `tests/evals/`,
`scripts/run_istara_evals.py`, `tests/agentic_eval_contract.json`,
`tests/real_user_benchmark/`, and `tests/simulation/scenarios/`.

Trace artifacts:

- `manifest.json`
- `scenarios.jsonl`
- `trace.jsonl.gz`
- `outputs.jsonl.gz`
- `scores.json`
- `feature-matrix.json`
- `article-tables/*`

Claims without those artifacts use `TBD-evidence`.
