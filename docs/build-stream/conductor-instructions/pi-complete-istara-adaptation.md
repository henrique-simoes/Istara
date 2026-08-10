# Complete Pi-to-Istara adaptation — conductor instructions

## Objective

Complete the existing opt-in Pi replacement in this isolated worktree, and prove its behavior at authentic in-process application boundaries. Preserve normal Istara behavior unless Pi is explicitly selected. The final handoff is the local `Review_pi_test` branch and a local review packet; do not push or mutate `origin`.

## Required outcome

- Pi-selected chat uses the registered DeepSeek target and fails closed before transport when Keychain registration is unavailable. It must not silently fall back to Ollama or the default model.
- Exercise real route/service boundaries for chat/SSE, A2A accepted and denial cases, local Pi channel lifecycle, source/evidence governance, memory/RAG/steering scopes, and autoresearch dry-run safety. Direct fixture/helper success is insufficient.
- Channel coverage is local-only. Do not start an external provider, send a webhook/message, or use external-channel credentials.
- After credential-free boundary tests pass, run exactly one bounded DeepSeek production-path target. Redact secrets and retain only approved raw prompt/output evidence; keep cumulative spend below USD 0.50.
- Update the living feature docs for chat, A2A, compute/model routing, and messaging. Regenerate/check them with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
- Run the security benchmark and focused regression suites. Record exact commands/outcomes in the lifecycle and review packet.

## Known defects to remedy

1. Pi chat logs a missing registered DeepSeek node and continues through the default provider. Make this fail closed and prove zero transport fallback.
2. Current Pi tests use direct helpers and permissive mocks. Replace/add adversarial boundary tests, especially A2A project/scope denial with zero Pi span/work.
3. The local channel adapter only has positive injection coverage. Test normal, paused, cross-project denial, and cleanup/ownership behavior without contacting a real channel.
4. Research/evidence, memory/RAG, steering, and autoresearch must use their governed public paths or explicitly remain unavailable—never manufacture accepted outcomes solely for tests.
5. The benchmark client must propagate Pi selection through the real request headers and the bounded DeepSeek production path must capture evidence without printing secrets.

## Safety and process

- Work only in `/Users/user/Documents/Istara-main-pi-replacement`; never touch `/Users/user/Documents/Istara-main` application code, `/Users/user/.config/build-stream-conductor/defaults.json`, `LLMs/`, `Model_Finetuning/`, or origin.
- No live backend/frontend servers and no unbounded model loading. One approved, configured DeepSeek test target is permitted only during its explicit bounded verification task.
- Treat model/API/auth/A2A/channel/memory/research changes as security-sensitive. Run `python scripts/security_benchmark.py --fail-on-threshold` before handoff.
- Keep the Build Stream lifecycle, the Compass Forge CF-SPEC-6 task evidence, and the local review packet accurate. Do not claim production readiness from mocks or local-only channels.
- Do not commit unrelated files. Local commits are allowed only for this branch and its review handoff.

## Review standards

The reviewer must reject fallback on missing Keychain registration, fabricated governance acceptance, missing negative authorization/channel tests, unredacted output/secrets, absent DeepSeek-path evidence, mutation of defaults/origin, or unsupported production-ready claims. The fixer must resolve every actionable finding and re-run the impacted checks.
