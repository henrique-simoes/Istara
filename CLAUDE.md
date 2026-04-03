# Istara — Claude Wrapper

Start with `SYSTEM_PROMPT.md`. That file is the model-agnostic operating contract for this repository.

## Claude-Specific Additions

1. Keep context tight: use `AGENT.md` for the compressed map and `COMPLETE_SYSTEM.md` for the broader architecture before touching multiple subsystems.
2. Use `SYSTEM_CHANGE_MATRIX.md` to expand "one-file" changes into the backend, frontend, UX, test, release, and prompt surfaces they actually affect.
3. Treat `tests/e2e_test.py` and `tests/simulation/scenarios/` as part of the product specification, not optional QA extras.
4. When implementation changes architecture, routes, models, views, stores, personas, or regression coverage, run:
   - `python scripts/update_agent_md.py`
   - `python scripts/check_integrity.py`
5. Preserve repo doctrine: update `Tech.md` for architecture/process/release changes, evolve the test suite for future regressions, and update Istara persona files when Istara's own agents need to understand the feature.
6. If generated docs miss an important system fact, improve `scripts/update_agent_md.py` instead of hand-patching the generated files only.
7. Keep `SYSTEM_INTEGRITY_GUIDE.md` coherent for deeper reference work, but treat the generated inventories as the fastest drift-resistant source of truth.
