# Istara — Gemini Wrapper

Start with `SYSTEM_PROMPT.md`. That file is the primary repo contract.

## Gemini-Specific Additions

1. Prefer the generated docs over memory:
   - `AGENT.md` for the compact operating map
   - `COMPLETE_SYSTEM.md` for architecture, integrations, and regression coverage
2. Use `SYSTEM_CHANGE_MATRIX.md` to determine what else must move when a route, model, UI flow, test, updater, or prompt changes.
3. Before finalizing architecture-affecting work, regenerate and verify docs:
   - `python scripts/update_agent_md.py`
   - `python scripts/check_integrity.py`
4. Treat every new route, model, menu, view, store, persona change, or test scenario as a documentation event.
5. Preserve repo doctrine: update `Tech.md` when the system story changes, evolve tests for future regressions, and update Istara persona files when the product's own agents need new understanding.
6. When a feature is hard to describe reliably, improve the generator so the next agent inherits the structure automatically.
7. Use `CHANGE_CHECKLIST.md` and `SYSTEM_INTEGRITY_GUIDE.md` as deeper procedural references after the generated maps establish the current shape of the system.
