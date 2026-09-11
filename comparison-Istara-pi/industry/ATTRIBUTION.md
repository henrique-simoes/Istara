# Industry Benchmark Data — Attribution & Provenance

Fetched: 2026-07-31 (CF-322 / DEC-9). Dataset content is **gitignored** — only this
attribution file is committed. Re-fetch with the same URLs to reproduce.

## BFCL v4 — Berkeley Function-Calling Leaderboard

- Source: `ShishirPatil/gorilla` GitHub repository,
  `berkeley-function-call-leaderboard/bfcl_eval/data/`
- License: **Apache License 2.0** (gorilla repo LICENSE)
- Files: `BFCL_v4_simple_python.json`, `BFCL_v4_multiple.json`,
  `BFCL_v4_live_simple.json` (+ `answer_*.json` ground truth from `possible_answer/`)
- Usage: subsets = first-N items per category in file order (25/20/15), prompt mode
  (function catalog in context — the official non-function-calling mode).
  Fidelity note: BFCL FC-mode (native tool schemas through the API) is a follow-up;
  prompt mode is an officially scored BFCL mode.
- Citation: Patil et al., "The Berkeley Function Calling Leaderboard (BFCL):
  From Tool Use to Agentic Evaluation of Large Language Models", ICML 2025.

## τ-bench (tau-bench)

- Source: `sierra-research/tau-bench` GitHub repository
- License: **MIT** (Copyright (c) 2024 Sierra)
- Files: `airline_tasks_test.py`, `retail_tasks_test.py` (task instructions +
  expected action sequences)
- Usage: first 8 tasks per domain, **adapted to single-turn** policy tasks.
  Fidelity note: the full τ-bench harness (env simulator + user-simulator LLM +
  multi-turn state) is out of scope for this pack; adapted tasks measure
  policy-action selection, not full conversational success. Records carry
  `fidelity: adapted_single_turn` in scenario metadata.
- Citation: Yao et al., "τ-bench: A Benchmark for Tool-Agent-User Interaction in
  Real-World Domains", Sierra Research, 2024.

## GAIA — NOT INCLUDED (gated)

- `gaia-benchmark/GAIA` on Hugging Face returns 401 without an accepted-terms
  account token. Requires an owner Hugging Face credential to fetch.
- Tracked as a follow-up (DEC-12 candidate): once the owner provides a token,
  add a GAIA subset through the same pack machinery.
