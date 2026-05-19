# Istara Documentation Map

This is the source-of-truth map for tracked Markdown in the repository. It
exists so release docs, testing records, security evidence, and agent guidance
do not drift into scattered one-off notes.

## Canonical Entry Points

| File | Purpose |
| --- | --- |
| `README.md` | Public English product overview, install path, release posture, references. |
| `README.pt-BR.md` | Public Portuguese product overview with the same process/security/eval posture. |
| `CONTRIBUTING.md` | Contributor setup and contribution expectations. |
| `AGENTS.md` | Repository-local instructions for Codex and other coding agents. |
| `AGENT_ENTRYPOINT.md` | Agent-facing reading order and generated product-surface snapshot. |
| `CHANGE_CHECKLIST.md` | Change execution checklist tied to Compass Forge. |
| `SYSTEM_CHANGE_MATRIX.md` | Cross-surface impact matrix. |
| `Tech.md` | Narrative technical architecture. |
| `docs/features/README.md` | Living feature documentation system: source docs, generated HTML, manifests, `llms.txt`, glossary, and update workflow. |
| `docs/FEATURE_DOCUMENTATION_PROGRESS.md` | Current handoff/status for the feature documentation system and remaining verification gaps. |

## Testing, Evals, and Benchmarks

| File | Purpose |
| --- | --- |
| `TESTING.md` | Top-level verification guide, command matrix, live LLM contract, and artifact logging rules. |
| `testing/TESTING_STRATEGY.md` | Active release-governance strategy for test layers, eval contracts, mutation/property gates, and metrics. |
| `testing/AI_EVALS_STRATEGY.md` | Academic/industry evaluation strategy for RAG, Prompt RAG, LLMLingua, DAG/ReAct, memory, ReasoningBank, Memento Skills, and Meta Hyperagents. |
| `testing/TEST_HISTORY.md` | Curated historical verification log. Raw run artifacts stay gitignored. |

Ignored runtime and generated artifacts must stay under their ignored result
roots, especially `tests/evals/.results/`, `tests/simulation/.results/`,
`tests/eval-results/`, `tests/simulation-results/`, `backend/data/`, and
`data/`. Do not promote raw run dumps into tracked docs unless they become a
small curated summary in `testing/TEST_HISTORY.md`.

## Security and Release Readiness

| File | Purpose |
| --- | --- |
| `SECURITY.md` | Public vulnerability reporting, incident-response, and security-document index. |
| `security/SECURITY_BENCHMARK.md` | Security benchmark controls, standards mapping, and required gate. |
| `security/RELEASE_SECURITY_READINESS.md` | Release checklist for auth, headers, endpoints, uploads, backups, MCP, LLM providers, and logs. |
| `security/ISTARA_SECURITY_ASSESSMENT_2026-05-08.md` | Current release security assessment and hardening backlog. |
| `security/control_matrix.json` | Machine-readable security benchmark control matrix. |

Security-sensitive changes must update the relevant security doc and run:

```bash
python scripts/security_benchmark.py --fail-on-threshold
python scripts/security_release_readiness.py
```

## Generated or Compatibility Docs

| File | Status |
| --- | --- |
| `AGENT.md` | Generated compact system map. Regenerate with the approved script when product surfaces change. |
| `COMPLETE_SYSTEM.md` | Generated/living system map. Keep as generated architecture evidence. |
| `docs/features/site/` | Generated hostable feature documentation website. Regenerate with `python scripts/feature_docs.py --seed-missing --generate-site --check`. |
| `docs/features/site/manifest.json`, `feature-graph.json`, `search-index.json`, `sitemap.xml`, `llms.txt` | Machine-readable feature indexes for agents and documentation hosting. Do not edit by hand; update `docs/features/inventory.json` and source docs first. |
| `SYSTEM_INTEGRITY_GUIDE.md` | Legacy deep reference. Use only when the current Compass Forge map and `Tech.md` are insufficient. |
| `planner.md` | Legacy compatibility note. Do not use it for new active plans. |
| `CLAUDE.md`, `GEMINI.md`, `QWEN.md` | Agent-wrapper instructions that must stay aligned with `AGENTS.md` and Compass Forge. |

## Living Feature Documentation

`docs/features/inventory.json` mirrors Istara's visible UI organization: menus, tabs, sub-tabs, modal/task surfaces, settings panels, agent/skill surfaces, integrations, and secondary/admin views. Each feature must have two source pages:

- `docs/features/content/<feature-id>/researcher.md`
- `docs/features/content/<feature-id>/architecture.md`

When UI/menu/route/store/agent/skill/model/test behavior changes, update the inventory and the affected feature pages, then run:

```bash
python scripts/feature_docs.py --seed-missing --generate-site --check
pytest tests/test_feature_docs.py -q
```

Use `docs/features/site/index.html` for human-readable hosting, `docs/features/site/manifest.json`, `feature-graph.json`, and `search-index.json` for agent navigation, and `docs/features/llms.txt` as the agent entrypoint. The generated site also includes glossary HTML pages and local-link validation so nested feature pages do not drift into broken navigation.

## Domain Docs

Markdown under `skills/`, `backend/app/agents/`, and active `wiki/` pages is
domain content rather than process clutter. Update it when the related feature,
persona, or skill behavior changes. Do not bulk-delete persona, skill, project,
or runtime markdown just because it is numerous; many of those files are product
data or generated test artifacts.

## Removed Scratch Registers

The root scratch files `CODEX_CLI_HANDOFF.md`, `gotchas.md`,
`current_plans.md`, `old_plans.md`, `current_plans_finetune.md`,
`example.md`, and `COMPASS_INTEGRATION_REPORT_2026_04_17.md` were temporary
handoff/planning/register artifacts. Durable content from those files now lives
in `AGENTS.md`, `planner.md`, this documentation map, or
`testing/TEST_HISTORY.md`.
