# Istara — Model-Agnostic System Prompt

You are working inside the Istara repository. Your job is to make safe, architecture-aware changes while keeping the LLM-facing documentation current enough that the next agent can reason from the codebase without guesswork.

## Primary Sources

Read these in this order when the change is non-trivial:

1. `AGENT_ENTRYPOINT.md` for the routing map of all agent-facing docs
2. `AGENT.md` for the compressed operating map
3. `COMPLETE_SYSTEM.md` for the generated architecture and coverage inventory
4. `SYSTEM_CHANGE_MATRIX.md` for cross-surface impact mapping
5. `CHANGE_CHECKLIST.md` for implementation obligations
6. `SYSTEM_INTEGRITY_GUIDE.md` when you need deeper legacy reference detail

## Core Rules

1. Treat code, tests, and docs as one system. If one changes, check whether the other two should change too.
2. Treat `tests/e2e_test.py` and `tests/simulation/scenarios/` as behavioral specifications for UI flows, menus, and end-to-end capabilities.
3. Do not trust memory for architecture. Re-read the current files and generated docs before making structural changes.
4. Use `SYSTEM_CHANGE_MATRIX.md` to expand every local change into its dependent backend, frontend, UX, test, release, and documentation surfaces.
5. When adding or changing a route, model, type, store, view, menu item, skill, persona, background workflow, or integration, update the implementation and then regenerate the living docs in the same change.
6. If the generated docs fail to capture an important architectural fact, improve `scripts/update_agent_md.py` so the fact becomes automatic.
7. Keep the docs drift-resistant. Avoid one-off manual summaries when the information can be scanned from the repository.

## Non-Negotiable Governance Rules

1. If architecture, subsystem boundaries, release/update behavior, installation flow, or operational process changes, update `Tech.md` in the same change.
2. If a feature, workflow, menu, UX path, or backend capability changes, update the testing surface for future regressions. This usually means `tests/simulation/scenarios/`, `tests/e2e_test.py`, or both.
3. Success metric for product changes: if Istara's own agents cannot understand the feature, discuss it accurately, route work around it, or use it safely, the change is incomplete.
4. When a capability changes in a way Istara's own agents should know, update the relevant persona files in `backend/app/agents/personas/`.
5. Documentation and persona updates belong in the same change as the implementation, not in a later cleanup.
6. Release/version/tag behavior must remain internally consistent across scripts, workflows, updater logic, docs, and desktop/server update checks.
7. Regular development pushes are not releases. Releases are created through the tagged/manual release flow.
8. Before preparing a release, run the standardized local release sequence via `scripts/prepare-release.sh`.

## Required Documentation Workflow

Run these after architecture-affecting work:

```bash
python scripts/update_agent_md.py
python scripts/check_integrity.py
```

## Change Awareness

Before editing, ask:

- Which API surface changes?
- Which frontend state or mounted views change?
- Which tests describe or protect this behavior today?
- Which entries in `SYSTEM_CHANGE_MATRIX.md` apply?
- Does `Tech.md` need to change because the architecture or process changed?
- Do Istara's own agents need persona/prompt updates to understand this feature?
- Which LLM-facing docs must reflect this so future agents do not regress it?

## Completion Standard

Work is not complete if the code changed but the generated architecture docs, procedural docs, Tech narrative, personas, or future-facing tests were left behind.
