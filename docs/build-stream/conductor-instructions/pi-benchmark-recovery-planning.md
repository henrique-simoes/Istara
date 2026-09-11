# Pi benchmark recovery-planning brief

This is a clean recovery planning session for the Pi benchmark lifecycle only. Do not
edit the master plan and do not run the benchmark during this recovery stage.

## User-authoritative benchmark contract

1. The DUT comparison is Istara's original agentic loop versus the Pi adaptation on the
   same scenario inputs. Istara remains the system being evaluated.
2. Every live DUT backend call must traverse Istara's API/dispatcher and use the
   configured DeepSeek API route under one cumulative `$1.00` evaluation cap. Do not
   call DeepSeek directly as a substitute for either Istara arm. Do not use Kimi,
   Claude, Codex, local models, or open-source routes as DUT providers in this run.
3. MoA is existing Istara dispatcher/validation and Research Spine behavior to measure:
   requested versus served route identity, ensemble width, output processing, and
   downgrade/degraded evidence. Do not change Istara production routing or defaults.
4. After B0 and B1...B_N are terminal, a separate Build Stream Conductor session may
   judge frozen artifacts. Kimi is the intended judge harness/model for that later
   session. It must emit report.md, report.html, scorecard.json, and per-judgment
   outputs without rerunning the DUT or spending evaluation budget.

## Why recovery is required

The prior correction run `PI-BENCH-ROLE-CORRECTION-20260722` halted with
`HALTED-CONSENSUS-INVALID-PLAN`. It was affected by shared-worktree concurrency:
older fixer activity and correction planners appended lifecycle entries and rewrote
plan slots while the conductor was validating governing artifacts. The run left
historical plan artifacts and ledger entries, but it is not a valid resumable execution
state. All conductors and project-scoped actors were stopped before this recovery run.

## Recovery requirements

- Inspect the existing lifecycle, work-order, correction brief, plan A/B/C artifacts,
  Compass Forge evidence, and current diff before proposing any implementation.
- Treat the prior run as historical evidence, not as an active pipeline. Do not blindly
  resume its halted consensus state or reuse its stale consensus marker.
- Determine the smallest safe path to reconcile the lifecycle and work-order. Preserve
  append-only history; do not rewrite old ledger entries or the master plan.
- Keep recovery scope documentation/planning-only unless a later owner-approved task
  explicitly says otherwise. Do not edit backend, frontend, benchmark Python, tests,
  recipes, manifests, or reports in this recovery stage.
- Verify that the proposed next step can run with exactly one conductor and no shared
  actor writers. Identify any remaining process, active-run, stale marker, or worktree
  collision before implementation is allowed.
- Do not start servers, load models, call DeepSeek/Kimi, run B0/B1...B_N, or spend
  evaluation budget.

## Required planner output

Produce an evidence-backed recovery plan that states whether the existing correction
artifacts can be safely reused, which files (if any) need a new scoped correction, how
the single-conductor invariant will be maintained, and what owner gate must precede any
implementation or live evaluation. Include exact verification commands and a rollback
path. The plan must explicitly retain the DUT, DeepSeek, MoA, and post-run Kimi roles
above.
