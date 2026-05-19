<!-- compass-forge:start -->
# Compass Forge Agent Workflow

Compass Forge is the control plane for this repository.

- Project root: `/Users/studio/Documents/Istara-main`
- Recipe: `istararustgraphtrial`
- MCP server: `python -m compass_forge.cli --workspace /Users/studio/Documents/compass-forge mcp --target /Users/studio/Documents/Istara-main --recipe istararustgraphtrial`

Before editing, run `compass-forge status` and `compass-forge agent-brief --request "<user request>"`.
For Standard, Full, or uncertain changes, create a durable spec first: `compass-forge spec create "<user request>"`, then `spec plan` and `spec tasks`.
Use `compass-forge intelligence impact --request "<user request>"` or `--path <path>` before touching important files.
If tasks exist, use `compass-forge work-order --role implementer --task CF-N`.
Run `compass-forge gate before` and `compass-forge gate after` for meaningful changes.
Attach command, gate, and review evidence before marking tasks done.
UI/menu/route/store/agent/skill/model/test behavior changes must update Istara's living feature documentation under `docs/features/`, regenerate the site/manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`, and attach that output as Compass Forge evidence.
Do not silently mutate external repos, global agent config, or generated integration files.
<!-- compass-forge:end -->

## Security Benchmark Gate

Auth, authorization, session, WebAuthn, connection string, pooled compute, MCP, webhook, LLM-provider, autoresearch, self-evolution, and agentic-memory changes must run the tracked security benchmark:

```bash
python scripts/security_benchmark.py --fail-on-threshold
```

Update `security/control_matrix.json`, `security/SECURITY_BENCHMARK.md`, and `tests/test_security_benchmark.py` when a security control, evidence path, standard version, or trigger pattern changes. Attach the scorecard output as Compass Forge command evidence before finishing security-sensitive tasks.

## Protected Local Artifact Folders

`LLMs/` and `Model_Finetuning/` are local, gitignored model/training artifact folders. Never delete, prune, move, or clean them during agent work.

## Live LLM and Model Loading Safety

Do not start live backend/frontend servers, send chat-completion probes, or trigger model loading without explicit user permission. Passive LLM status/discovery checks must stay passive. Active model loading belongs only on deliberate request paths and must be bounded to one configured target so agent work never loads multiple heavy models at once.

Use gitignored environment files, process environment, or macOS Keychain for live LLM endpoints and tokens. Never commit or paste private LLM server URLs, tokens, connection strings, or endpoint fingerprints that could identify a private server.
