# QA Docker hygiene — one kept install, everything else cleaned up

<!-- STATUS BLOCK -->
```yaml
item: qa-docker-hygiene
branch: chore/docker-hygiene
cf: { spec: CF-SPEC-6, tasks: [CF-59, CF-60, CF-61, CF-62, CF-63, CF-64, CF-65, CF-66, CF-67, CF-68, CF-69] }
phase: "—"
stage: S5-ship
status: done
blocked_on: null
last: { agent: claude-opus-5-5, at: 2026-09-28T03:30:00Z, ledger: L-6 }
next_action: "Owner: approve push + PR of chore/docker-hygiene into testing."
```
<!-- /STATUS BLOCK -->

## Plan overview

**Problem.** The Mac Studio Docker disk (250.9 GB) hit 100% and broke other projects. Istara held
~21 GB in dated QA image variants and five stopped `never-delete-official-*` containers whose
tmpfs data had already been snapshotted to the host.

**Outcome.** One persistent QA install accumulates live-model data (DB, research data, ensemble
health, telemetry, provider keys, endpoints, preferences) on the external volume
`istara-qa-persistent-data`; every other Istara QA resource is removed on success, failure and
kill; records live as files under `~/never-delete-official-data/`.

**Acceptance.**
- Given a QA `cycle`, when it ends by success, failure or signal, then no `istara-qa-*`
  container, network or anonymous volume remains (`docker ps -a`, `docker network ls`).
- Given two consecutive cycles, the Istara footprint (images, containers, networks, volumes, dangling) after the second equals the first (steady state).
- Given `--persistent`, `down -v` never removes `istara-qa-persistent-data`, and `up` backs it up first.
- `up`/`cycle` refuse under 20 GB free. `cleanup` is dry-run by default and touches only `istara-qa-*`.
- `pytest tests/test_qa_stack_contract.py` green; compose renders for every profile.

**Rollback.** Revert the branch; the persistent volume and the record files are unaffected.

## Decision log

DEC-1 | 2026-09-27 | S0 | owner
Context: audit showed the protected containers held no unique data (tmpfs gone on stop; snapshots
and W4 bind-mount data on host). Decision: delete the listed containers/images after exporting
logs and images; protect records instead of containers; keep one persistent install whose data
accumulates; delete `istara-test:1`. Why: owner approval in chat.

DEC-2 | 2026-09-27 | S1 | claude-opus-5-5
Context: the default lanes (CI, contract) must stay credential-free and ephemeral. Decision:
persistence is an opt-in overlay (`docker-compose.qa.persistent.yml`, external volume, fixed
project `istara-qa-persistent`) rather than changing the base file. Why: an external volume can
never be removed by `down -v`; the base contract and CI render stay unchanged. Rejected: a named
volume in the base file (CI would accumulate data; `down -v` would delete it).

DEC-4 | 2026-09-28 | S2 | claude-opus-5-5
Context: `cycle` with seed/collect failed: the seeder gets 403 from the backend network guard
(pre-existing; the seeder sends no credentials). Decision: `cycle` = up -> wait -> qa; seed and
collect remain explicit commands; the 403 is a separate task. Why: fixing it touches the security
middleware (Full risk), out of this plan's scope. Also fixed two pre-existing `run_qa_python` bugs
found by the proof (missing `--profile`; git "dubious ownership" in the uid-999 container).

DEC-3 | 2026-09-27 | S1 | claude-opus-5-5
Context: build cache (38 GB) is shared across projects and cannot be scoped to Istara by label.
Decision: leave build cache out of `cleanup`; report it. Why: pruning it would touch other projects.

## Ledger

### L-1 | 2026-09-27T22:55:00Z | S0-frame | claude-opus-5-5 | framer | —
Did: read-only audit on the Studio (containers, images, tmpfs config, snapshots, logs, labels).
Result: protected containers held no unique data; Istara images ~21 GB.
Verified: `docker ps -a --size`, `docker inspect`, `docker diff`, `du -sh ~/never-delete-official-data/*`.
Next: owner approval.

### L-2 | 2026-09-28T02:05:00Z | S2-execute | claude-opus-5-5 | executor | —
Did: exported logs (+inspect.json) and three images (`docker save | gzip`, 3.4 GB each, `gzip -t` ok)
to `~/never-delete-official-data/`; removed 10 containers and 13 images (owner-approved list).
Result: no Istara containers or images left; images 60.34 GB -> 26.72 GB.
Verified: `docker ps -a | grep -ci istara` = 0; `docker images | grep -ci istara` = 0; `docker system df`.
Next: implement rules.

### L-3 | 2026-09-27T23:30:00Z | S2-execute | claude-opus-5-5 | executor | —
Did: fixed image tags + run labels (`docker-compose.qa.yml`), persistent overlay, `istara-qa.sh`
(`--persistent`, `cycle`, `backup`, `cleanup`, disk guard), AGENTS.md §5, CLAUDE.md, Tech.md, tests.
Result: contract tests and governance checks green; all profiles render on the Studio.
Verified: `pytest tests/test_qa_stack_contract.py tests/test_qa_reset_seed.py tests/test_remote_benchmark_runner_contract.py -q` -> 64 passed, 7 skipped (render, no local Docker);
`check_change_obligations.py`, `check_ci_governance.py`, `check_test_harness.py` passed;
Studio `docker compose ... config --quiet` ok for contract/synthetic/audit/ui and the persistent overlay.
Next: two-cycle proof on the Studio.

### L-4 | 2026-09-28T02:20:00Z | S2-execute | claude-opus-5-5 | executor | —
Did: Studio proof runs a–g (failure paths: port 3000 held by another project, missing --profile,
git safe.directory, unregistered overlay path, seeder 403) and persistent runs p1/p2.
Result: every failed cycle removed its containers, networks and anonymous volumes (0 left each time);
persistent DB `/app/data/istara-qa.db` (1.1 MB) survived two cycles; backups written to
`~/never-delete-official-data/istara-qa-persistent-data/20260928T021029Z` and `…T021202Z`.
Verified: logs `~/cf-remote/eval/istara-hygiene-{proof,persist,d,e,f,g}.log` on the Studio.
Next: success-path proof.

### L-5 | 2026-09-28T02:45:00Z | S5-ship | claude-opus-5-5 | executor | —
Did: two back-to-back ui-profile cycles (runs h, i) on ports 3300/8300 from commit on chore/docker-hygiene.
Result: both exit 0 (feature obligations + QA capabilities passed). Across run i: Images 40 / 39.21 GB
and Build Cache 42.49 GB unchanged; Istara = 4 `:current` images (tags replaced in place), 0
containers, 0 networks, 0 dangling, 1 volume (`istara-qa-persistent-data`). Container/volume deltas
belong to concurrent Kairos runs.
Verified: `scripts/istara-qa.sh cycle --run-id hygiene-20260927-{h,i} --profile ui` rc=0; before/after in
`~/cf-remote/eval/hyg-{before,after}-{h,i}.txt`; local `pytest tests/test_qa_stack_contract.py
tests/test_feature_obligations.py tests/test_qa_reset_seed.py -q` 55 passed, 7 skipped;
`check_feature_obligations.py`, `check_qa_capabilities.py`, `check_change_obligations.py` passed.
Review coverage: self-only (no independent review; owner rule).
Next: owner approval to push and open a PR into testing.

### L-6 | 2026-09-28T03:30:00Z | S5-ship | claude-opus-5-5 | executor | —
Did: fixed the seeder 403 (DEC-4) in QA code only: `qa/scripts/seed_synthetic.py` sends
`X-Access-Token` (local mode, `QA_NETWORK_ACCESS_TOKEN`) or logs in as the disposable QA admin
(team mode); `qa-seeder` gets those env vars; `cycle` generates a random per-cycle token in local
mode and runs seed -> qa -> collect again (persistent runs still never seed). No backend change.
Result: Studio run j exit 0: seed manifest written, obligations passed, `audit_pass: true`, cleanup
on exit 0; Istara footprint before = after (4 images, 0 containers, 0 networks, 0 dangling,
1 volume); token absent from the run log.
Verified: `scripts/istara-qa.sh cycle --run-id hygiene-20260927-j --profile ui` rc=0
(`~/cf-remote/eval/istara-hygiene-j.log`); `pytest tests/test_qa_seed_ingestion.py
tests/test_qa_stack_contract.py tests/test_qa_reset_seed.py tests/test_feature_obligations.py -q`
65 passed, 7 skipped; `security_benchmark.py --fail-on-threshold` pass; change/feature obligations,
QA capabilities, CI governance, public-repo audit passed. Review coverage: self-only.
Next: owner approval to push and open a PR into testing.

## Summary

Outcome met. Residual: build cache (42 GB, shared with other projects) is not scoped by
`cleanup`. The seeder 403 (DEC-4) was fixed in L-6.

Retro: the proof found three pre-existing `istara-qa.sh` bugs that no test covered, because the
container lane had never been run end to end on the Studio. Run `cycle` on the Studio after any
change to the QA script.
