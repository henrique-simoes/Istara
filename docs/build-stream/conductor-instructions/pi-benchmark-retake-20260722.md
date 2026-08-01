# Fresh Pi benchmark retake: planning contract

You are in a new, isolated Build Stream Conductor planning run. The prior recovery and
role-correction lineages are historical evidence only. Do not reopen, edit, delete, or
continue their tasks, plans, casts, consensus state, or uncommitted files.

Read first:

- `docs/build-stream/2026-07-22-pi-benchmark.md`
- `docs/build-stream/conductor-instructions/pi-benchmark-deepseek-moa-execution.md`
- `tests/pi_benchmark/`
- `comparison-Istara-pi/` when present

Do not edit `docs/build-stream/plans/2026-07-20-pi-full-replacement-master-plan.md`.
Do not make live benchmark calls, start Istara servers, load models, or use credentials
during this planning stage.

The benchmark compares Istara's original agentic loop with the Pi adaptation through the
Istara API/dispatcher path. Any later live DUT traffic uses only the configured DeepSeek
route and shares a hard USD 1.00 cumulative ledger. Kimi is reserved for a separate,
artifact-only post-run judging/report session; it is not a benchmark provider.

Produce an independent implementation plan in your assigned file. It must:

1. Validate what B0 benchmark apparatus already exists, with exact paths and tests.
2. Define an immutable, strict wave manifest for B0 then B1 through B_N. `N` must be a
   recorded `max_processes` bound; distinguish it from `moa_n` and `repeats`.
3. State explicit owner gates before any live DeepSeek spend, and preserve the closed,
   crash-safe budget ledger and redacted route evidence requirements.
4. Cover self-MoA and full-ensemble routing truthfully; an endpoint/route downgrade is
   degraded or blocked, never an ensemble success.
5. Specify post-run separation: only after all B waves converge, launch a distinct,
   artifact-only Kimi judging/report run that does not rerun the DUT or charge the DUT
   ledger.
6. Include a test/verification matrix, rollback, and a narrow changed-file scope.

The updated conductor pins immutable consensus candidates. Do not edit another architect's
plan, do not create repairs, do not judge, and do not manually finish the task; record real
command evidence and self-report, then let the harness finalizer establish completion.
