# W0 conductor packet — Pi full replacement

Governing artifacts:

- `docs/build-stream/plans/2026-07-20-pi-full-replacement-master-plan.md`
- `docs/build-stream/2026-07-20-pi-full-replacement.md`
- `CF-SPEC-8`
- diagnosis: `<repo-root>/comparison-Istara-pi/2026-07-20-pi-replacement-review-diagnosis.md`
- predecessor lifecycle: `docs/build-stream/2026-07-20-pi-production-runtime-completion.md`

This is implementation, not planning. Do not create or dispatch architect tasks. Read the
master plan's Read-this-first contract, §§1–6, §8.6, §§11–12, and the six research files
under `docs/build-stream/plans/pi-full-replacement-research/` before editing. The master
plan wins over any abbreviated work-order wording.

Implement W0 completely:

1. Finish M0's executable bootstrap: add `scripts/pi_migration_inventory.py`,
   `tests/pi_migration/test_count_to_zero.py`, and the complete initial
   `tests/pi_migration/legacy_allowlist.yaml` with all 87 product sites plus permanent
   infrastructure entries. The scanner and ratchet must be deterministic and green before
   migration work. Keep the plan/research, lifecycle, and `cf-spec-8-answers.json` in the
   intentional change set.
2. Implement every W0 hardening item H-1 through H-14 exactly as specified in master plan
   §6, including each named regression test and the append-only correction to the
   CF-SPEC-7 lifecycle history. Do not weaken or omit an item to fit a turn.
3. Run Compass Forge's per-wave protocol: baseline gate before edits, focused impact and
   test-impact checks for every touched production file, context/test suggestions, command
   evidence, post-change gate, and a W0 completion decision containing counts and ladder
   results. The only tolerated inherited gate debt is the plan's pre-recorded large-file
   baseline; introduce zero new failures, drift, or security findings.
4. Update living feature documentation for every changed behavior and run
   `python scripts/feature_docs.py --seed-missing --generate-site --check` as command
   evidence. Because W0 touches model/runtime/security surfaces, run
   `python scripts/security_benchmark.py --fail-on-threshold` and update the tracked matrix,
   benchmark doc, or benchmark tests only if the control/evidence/trigger contract changed.
5. Run the full existing Pi ladder plus all W0 tests and the applicable master-plan §8.6
   subset. Tests must use isolated SQLite URLs and assert no orphan Node processes.
6. Maintain the Build Stream status block, findings register, and append-only ledger. Use
   author `henrique-simoes <simoeshz@gmail.com>`, no `Co-authored-by`, maximum five files per
   commit, and W0-tagged commit messages. Do not push.

Safety and scope:

- Never touch, clean, move, or delete `LLMs/` or `Model_Finetuning/`.
- Never migrate or couple Petals/donated-compute paths.
- Do not start live backend/frontend servers, make chat-completion probes, trigger model
  loading, use private endpoints, or incur API/judge spend. W0 verification is deterministic.
- Preserve user/untracked work. Read-edit-read; if a file was last read more than ten
  messages ago, re-read it.
- No placeholders, silent legacy fallback, fabricated evidence, forced CF acceptance, or
  claims beyond commands actually run.

The implementation task is done only when W0's full exit contract is proven. The reviewer
must independently review correctness, security, donor isolation, concurrency, protocol
compatibility, tests, docs, CF evidence, commit discipline, and every H-1…H-14 item. A fail
verdict must enumerate actionable findings and create fixer work; delta re-review loops
continue until pass.
