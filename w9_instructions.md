# W9: Final ratchet + docs + acceptance

Finalize the migration by enforcing the ratchet, cleaning up dead code, and documenting the architecture.

1. `legacy_allowlist.yaml`: Reduce to permanent entries (e.g., benchmark/donors). Ensure the ratchet number is 0 for product sites. Wire the inventory script into `scripts/check_integrity.py`.
2. Dead Code Cleanup: Delete now-dead legacy-only glue ONLY where the dispatcher made it unreachable from product code. Verify with `CF intelligence dead-code`. DO NOT make blind deletions (as per CLAUDE.md rule). The registry itself must remain for the legacy engine, donors, and benchmarks.
3. Documentation: Write `docs/architecture/agentic_core.md`.
