# Legacy Planner Compatibility

`planner.md` used to define Istara's root-file planning workflow around
`current_plans.md` and `old_plans.md`. That workflow is retired.

Use Compass Forge for active planning instead:

```bash
compass-forge status
compass-forge agent-brief --request "<user request>"
compass-forge spec create "<user request>"
compass-forge spec plan CF-SPEC-N
compass-forge spec tasks CF-SPEC-N
compass-forge work-order --role implementer --task CF-N
```

For meaningful changes, run `compass-forge gate before` before editing and
`compass-forge gate after` after verification. Attach command, gate, and review
evidence to the relevant Compass Forge task before marking it done.

Do not recreate `current_plans.md`, `old_plans.md`, or one-off root handoff
ledgers for new work. Durable plans, deferred work, review findings, and
handoffs belong in Compass Forge specs/tasks/evidence or in the tracked
domain-specific docs listed by `DOCUMENTATION.md`.
