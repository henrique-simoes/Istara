# Istara Pi Model-Management Migration (resumed 2026-08-22)

```yaml
item: istara-pi-model-management-migration
branch: conductor/istara-pi-model-management-migration-20260822
base: origin/testing@15260a78df6637c2d1981c74683525cb75ab1a22
cf:
  framing_spec: CF-SPEC-58 (prior run) / CF-SPEC-1 (this run)
  spec: CF-SPEC-1
  tasks: [planning-only until owner approval; CF-SPEC-1 tasks generated at approval]
phase: "Phase 0 — architecture and migration plan (resumed)"
stage: S1-plan
status: in-progress
blocked_on: owner approval gate — consensus vote in progress: architect-b (deepseek/deepseek-v4-pro) voted slot a (ec3a76e7…, master-a.md) in round ef3baec72460f4802e2b; freeze + owner approval still pending; no implementation task released before owner approval
last:
  agent: deepseek/deepseek-v4-pro
  at: 2026-08-22T12:37:59Z
  ledger: L-11
next_action: "Remaining vote slot(s) record plan_vote; conductor tallies round ef3baec72460f4802e2b, freezes the winning consensus plan, and stops at the owner approval gate before any implementation task is generated or released."
```

## Plan overview

### Problem

Istara has two model-management identity planes: legacy Istara `LLMServer` rows and Pi's provider/model catalog and endpoint resolver. Pi owns the agentic runtime seams, but persisted LLM Server CRUD, legacy routing, compute registration, compatibility projection, embeddings, Petals, audio configuration, and UI contracts are not yet one coherent migration. Removing LLM Servers abruptly would risk provider loss, model-ID ambiguity, embedding/vector-space drift, Petals donor isolation regressions, secret exposure, and broken existing projects.

### Outcome

Pi becomes the canonical model-management plane while Istara preserves both explicit agentic engines, research-validity protections, the shared embedding invariant, Petals donation, audio/transcription flows, and deterministic disposable Docker QA. Legacy LLM Servers retire through a reversible compatibility migration with observable deprecation and removal criteria. The resulting branch remains testing-only (everything goes to `testing`, never `main`).

### Resume context (2026-08-18 run, frozen as reference)

The prior run (`ISTARA-PI-MODEL-MIGRATION-20260818`) paused at the planning stage with a Conductor finalization hold. Its three independent architect drafts are carried forward as inputs:

- `docs/build-stream/plans/carried-20260818-plan-a.md` (Architect A, 55.6 KB)
- `docs/build-stream/plans/carried-20260818-plan-b.md` (Architect B repair, 18.2 KB)
- `docs/build-stream/plans/carried-20260818-plan-c.md` (Architect C, 35.1 KB)

These MUST be used as inputs by the new architects; they were authored by independent models (Pi gpt-5.6-luna, Codex, Pi deepseek-flash) under the old roster and are not re-authorizations of the new roster.

### Owner-approved roster (2026-08-22)

| Role | Harness | Model | Effort |
|---|---|---|---|
| Architect A | pi | deepseek/deepseek-v4-flash | max |
| Architect B | pi | deepseek/deepseek-v4-pro | max |
| Architect C | codex | gpt-5.6-luna | low |
| Implementer | codex | gpt-5.6-luna | low |
| Code reviewer | pi | deepseek/deepseek-v4-flash | max |
| Fixer | pi | deepseek/deepseek-v4-flash | max |
| Fallback (unlisted roles) | codex | gpt-5.6-luna | low |

### Owner-approved boundaries

- Work only from the isolated branch/worktree based on `origin/testing` at `15260a78`.
- Use the pinned native Compass Forge binary (`COMPASS_FORGE_BIN`/`COMPASS_FORGE_SHA256` from `resolve-pin.sh`); no Python/PATH fallback.
- Carry the three 2026-08-18 drafts forward as inputs; re-do whatever needs re-doing with the new roster.
- Everything goes to the `testing` branch lineage, including pushes to origin. Never touch `main`.
- Multivac is no longer available. Final acceptance deploys on the managed VPS per the `vps` skill (Dokploy strict single-workload profile, vpsctl.py preflight/inventory/verify-isolation/verify-exposure/audit-anchor, no firewall changes without owner approval).
- Do not start live backend/frontend servers, load models, expose secrets, touch `LLMs/` or `Model_Finetuning/`, weaken gates, or alter unrelated Docker workloads.
- Owner approval remains mandatory at the plan gate, at ship, and for any firewall/VPS exposure change.

## Roadmap

1. **Foundation and inventory** — verify latest Pi release, freeze provider/model/secret contracts, map all legacy LLM Server consumers, capture gates, migration/rollback artifacts, and establish test obligations. Uses the carried-forward drafts.
2. **Pi canonical catalog and secret custody** — remove duplicate model-ID ambiguity, unify provider catalog/endpoints/OAuth/API-key/custom/local configuration, validate encryption against standalone Pi, preserve exact endpoint identity/capability metadata.
3. **Compatibility migration and routing** — migrate/project legacy configuration without silent data loss, route both Pi and legacy Istara engines through Pi-owned resolution, deprecate legacy LLM Server APIs, preserve explicit rollback.
4. **Embeddings and agent controls** — preserve the vector-space invariant, define chat/embedding separation, support temperature/thinking/effort controls, redesign the Pi-vs-Istara selector with honest comparative summaries.
5. **Petals and audio** — preserve donor opt-in, identity/security, scheduling and fail-closed Petals behavior; define unified Whisper/audio/diarized transcription model configuration.
6. **Testing, documentation, and VPS acceptance** — update living feature docs/manifests, Compose contracts and feature coverage, run disposable provider-backed QA on `testing`, then deploy the isolated staging service on the managed VPS per the `vps` skill (Dokploy strict profile, verify-isolation/exposure, firewall evidence, audit-anchor), and remove only initiative-owned disposable artifacts.

## Decision log

### DEC-1 | 2026-08-22 | S0-frame | owner

Context: The prior 2026-08-18 run paused on a Conductor finalization hold; Skills and Compass Forge were subsequently fixed, and the native Rust Compass Forge cutover is now active.

Decision: Freeze the 2026-08-18 run as reference (do not resume or mutate it) and start a fresh matched-release run on the native stack: new worktree/branch, new CF project and spec (CF-SPEC-1), new strict-wave manifest, new cast with the owner-approved roster, drafts carried forward. Keep the same delivery scope and boundaries.

Why: The cutover directive requires a matched release (native binary + current Skills + fresh process configuration) rather than resuming a Python-era run with the new stack.

### DEC-2 | 2026-08-22 | S0-frame | owner

Context: Multivac is no longer available for staging acceptance.

Decision: Replace multivac acceptance with the managed VPS (wildsync) following the `vps` skill: Dokploy Docker Compose strict single-workload profile, vpsctl.py preflight → inventory → deploy → verify-isolation → verify-exposure → audit-anchor, firewall/DOCKER-USER evidence, and owner approval before any port/firewall change.

Why: The vps skill is the maintained, audited deployment path for this host.

## Ledger

### L-1 | 2026-08-22T11:36:00Z | S0-frame | owner | framer | Phase 0

Did: Created fresh isolated worktree `istara-pi-model-management-migration-20260822` (branch `conductor/istara-pi-model-management-migration-20260822`, base `origin/testing@15260a78`); carried forward the three 2026-08-18 architect drafts as `docs/build-stream/plans/carried-20260818-plan-{a,b,c}.md`; initialized the native CF project (recipe `istara-main`, workspace `/Users/user/Documents/compass-forge`); created execution spec `CF-SPEC-1`; wrote the new strict-wave manifest `docs/build-stream/manifests/istara-pi-model-management-migration-20260822.json` (SHA-256 `b9c8ff0ca1c0521fff18e27d3caf53e11fac89c6fb9a44e1656688ac1cf5a8fd`); registered the new run's actor roles in the active recipe; generated the planning-only tasks `ISTARA-PI-MODEL-MIGRATION-20260822-PLAN-A/B/C` and the new cast with the owner-approved roster (see table above; `plan_gate=true`, `ship.auto_pr=false`, pending `wave_binding`).

Result: Fresh matched-release planning stage ready. No implementation/review roots exist; the cast has no executable `waves` state until owner approval binds the winning plan to the manifest. No worker was launched yet, no model preflight probe was sent yet, no source code changed, and no Docker/VPS workload was touched.

Verified: `resolve-pin.sh` (pin `559af310…`); native `compass-forge status --target <wt>` (project/recipe resolved); `make_pipeline.py --wave-manifest …` (3 planning tasks imported, roles verified); `make_cast.py --wave-manifest …` (cast written, roster asserted); manifest SHA-256.

Next: Run conductor preflight (real one-shot probes for the three distinct model routes), spawn the detached conductor, and monitor the three-architect planning stage with status updates every ~5 minutes.

## Phase 0 — architecture and migration plan

### Frame

This is a Full security/architecture change. The plan must cover the complete migration boundary: storage/migrations, encryption, provider catalog provenance, endpoint identity, engine dispatch, embeddings, Petals, audio, UI, tests, docs, CI/Compose, and VPS operations as one dependency graph. The three carried-forward drafts are inputs, not blind re-runs.

### Definition of Ready for implementation

- Winning architect plan is frozen and owner-approved through the Conductor approval gate.
- All CF tasks have explicit scope, dependencies, impacted paths, and verification commands.
- Latest Pi package versions and standalone compatibility contract are recorded.
- Migration/rollback contract and LLM Server deprecation/removal criteria are explicit.
- Testing branch Docker automation and VPS acceptance are represented in the task graph.
- `gate before` baseline and inherited debt are recorded.
- No implementation task is dispatched before these conditions hold.

### Findings register

| ID | Sev | Dim | Where | Finding | CF task | Status |
|---|---|---|---|---|---|---|
| F-1 | High | Architecture | Carried 2026-08-18 drafts reference multivac staging and old-run CF task ids (CF-787..CF-805) | Must be re-baselined to the managed-VPS contract (vps skill, DEC-2) and this run's six-wave manifest; corrected in draft A, must be held through synthesis | ISTARA-PI-MODEL-MIGRATION-20260822-PLAN-A | open — corrected in draft A; bind in master plan |
| — | — | — | — | No independent review has run yet in this run. | — | pending |

## Final summary

Not yet shipped. This lifecycle intentionally stops before implementation until the independent architect consensus plan is frozen and the owner approval gate is passed.

### L-2 | 2026-08-22T11:49:51Z | S1-plan | deepseek/deepseek-v4-flash | executor | draft <!-- bsc-ledger:ISTARA-PI-MODEL-MIGRATION-20260822-PLAN-A -->
Did: Wrote independent architect-A draft `docs/build-stream/plans/istara-pi-model-management-20260822-plan-a.md` (58 KB, 15 sections); carried the three 2026-08-18 drafts forward and independently verified every surface against the tree; re-verified Pi versions, migration ratchet, gate baseline, and test collection.
Result: Draft covers the six manifest waves, canonical identity model (model_id/endpoint_id/credential_ref/embedding+audio profiles), resolver/transport boundary, exact data+secret migration and rollback state machine, feature-flag/deprecation/removal criteria, test ownership, docs/manifest obligations, security benchmark coverage, and isolated VPS acceptance per the vps skill. Corrections C1-C6 recorded: multivac replaced by managed VPS (DEC-2, vpsctl.py preflight/inventory/verify-isolation/verify-exposure/audit-anchor, no firewall changes without owner approval); old-run CF task ids re-baselined to this run's waves; gate debt re-measured (30 inherited / 0 new); Pi latest re-verified at 0.84.2; worker deps prerequisite made explicit.
Verified: `npm view` → 0.84.2 / 0.84.2 (passed); `python3 scripts/pi_migration_inventory.py --json` → 1 allowlisted permanent site, ratchet 0 (passed); `compass-forge gate before --task ISTARA-PI-MODEL-MIGRATION-20260822-PLAN-A --summary` → fail, 30 inherited, 0 new (passed as baseline); `uv run --project backend --with pytest --with pytest-asyncio python -m pytest --collect-only -q` on 6 key surfaces → 62 tests collected (passed).
Next: Architect B and C independent drafts, then synthesis into one MECE master plan with coverage matrix; freeze plan and stop at the owner approval gate. No implementation before owner approval.

### L-3 | 2026-08-22T11:55:00Z | S1-plan | deepseek/deepseek-v4-pro | architect | draft <!-- bsc-ledger:ISTARA-PI-MODEL-MIGRATION-20260822-PLAN-B -->
Did: Independent architect-B draft written to `docs/build-stream/plans/istara-pi-model-management-migration-20260822-plan-b.md` (47 KB; no code touched). Independently re-verified the carried 2026-08-18 drafts A/B/C against the current tree and recorded corrections C1-C6: multivac retired -> managed VPS per vps skill (DEC-2); CF-SPEC-59/CF-787..805 graph superseded by CF-SPEC-1 + this run's six-wave manifest (foundation, pi-catalog-secrets, compat-routing, embeddings-controls, petals-audio, qa-docs-vps); gate baseline refreshed (30 failures / 0 new / 0 actionable, not the stale "80"); settings field corrected to `pi_api_endpoints: list[PiApiEndpoint]` (config.py:304); VPS strict single-workload profile vs 8-service docker-compose.yml reality check (dedicated single-service acceptance image or owner-approved connectivity exception, vps skill §decision-rule); environment prerequisites made explicit (`uv sync --extra dev`; `cd pi-runtime && npm ci` before worker-backed tests).
Result: Draft covers canonical identity model (model_id/endpoint_id/credential_ref/embedding+audio profiles), resolver+transport boundary, engine precedence (per-call > header x-istara-agent-engine > project agentic_engine > settings.agentic_engine_default="legacy"; no silent fallback), reversible retirement state machine S0-S5 with feature-flag registry + deprecation/removal criteria, exact data/secret migration + rollback playbook, per-wave acceptance + commands for all six manifest waves, isolated VPS acceptance/cleanup runbook (vpsctl.py preflight -> inventory -> strict single-workload profile -> rendered-Compose preview -> deploy preserving prior identity -> verify-isolation -> verify-exposure -> firewall/DOCKER-USER evidence -> audit-anchor; no firewall change without owner approval), docs/manifests/security/test-ownership obligations, risk register R1-R11, Definition of Ready/Done + owner gates, coverage matrix vs carried drafts A/B/C. ISTARA-PI-MODEL-MIGRATION-20260822-PLAN-B.
Verified: `compass-forge status/next --target <wt>` (project resolved, runtime rust, python_fallback false); `gate before --summary` (fail, 30 failures secret_flow/unexpected_large_files, new_failures=0, actionable=0, drift route=4 type=2, warnings=188); `npm view @earendil-works/pi-agent-core|pi-ai version` (0.84.2 both; tree pins 0.83.0/0.80.10); `uv run --project backend python -m pytest tests/pi_migration/test_count_to_zero.py -q` (3 passed); `python3 scripts/security_benchmark.py --fail-on-threshold` (28/28 pass, 100.0%); `python3 scripts/feature_docs.py --seed-missing --generate-site --check` (86 features green, 224 artifacts); boundary file sweep + `vpsctl.py --help` (subcommands preflight/inventory/audit-verify/audit-anchor/verify-isolation/verify-exposure/ssh; 3 test paths recorded as new obligations: test_research_spine_donor_routing.py, test_model_management_migration.py, test_model_management_rollback.py). CF evidence rows 28-36 on ISTARA-PI-MODEL-MIGRATION-20260822-PLAN-B.
Next: Architect C draft, then consensus synthesis (A/B/C -> one MECE master plan -> vote); conductor freezes the plan and stops at the owner approval gate before any implementation task is released.

### L-4 | 2026-08-22T12:02:16Z | S1-plan | deepseek/deepseek-v4-flash | architect | draft <!-- bsc-ledger:ISTARA-PI-MODEL-MIGRATION-20260822-REPLAN-A-r1 -->
Did: Repaired the slot-A consensus draft. The L-2 slot-A draft had landed at the misnamed path `docs/build-stream/plans/istara-pi-model-management-20260822-plan-a.md`, which the synthesis phase cannot consume; wrote the full 15-section S1 draft to the task's authoritative `plan_file` `docs/build-stream/plans/istara-pi-model-migration-20260822-plan-a.md` and removed the duplicate in the same commit. Re-verified every current-tree fact at repair time and added correction C7: `vpsctl.py` lives in the vps skill (`~/.pi/agent/skills/vps/scripts/vpsctl.py`), not in repo `scripts/` (subcommands verified: preflight, inventory, audit-verify, audit-anchor, verify-isolation, verify-exposure, ssh).
Result: Authoritative slot-A draft exists at the path the synthesis phase reads; covers the six manifest waves, canonical identity model (model_id/endpoint_id/credential_ref/embedding+audio profiles), resolver/transport boundary, exact data+secret migration and rollback state machine, feature-flag/deprecation/removal criteria, test ownership, docs/manifest obligations, security benchmark coverage, and isolated VPS acceptance per the vps skill (C1/C5/C7). ISTARA-PI-MODEL-MIGRATION-20260822-REPLAN-A-r1.
Verified: `npm view` -> 0.84.2 / 0.84.2 (passed; tree pins 0.83.0 / 0.80.10); `python3 scripts/pi_migration_inventory.py --json` -> 1 allowlisted permanent site, ratchet 0 (passed); `compass-forge gate before --task ISTARA-PI-MODEL-MIGRATION-20260822-REPLAN-A-r1 --summary` -> fail, 30 inherited, 0 new, 0 actionable (passed as baseline); `pytest --collect-only` on six key surfaces -> 62 tests collected (passed); `vpsctl.py --help` -> 7 subcommands (passed); `git diff --check` clean. CF evidence rows on ISTARA-PI-MODEL-MIGRATION-20260822-REPLAN-A-r1.
Next: Architect B and C drafts -> consensus synthesis into one MECE master plan with coverage matrix; freeze plan and stop at the owner approval gate before any implementation task is released.

### L-5 | 2026-08-22T12:18:00Z | S1-plan | gpt-5.6-luna | architect | draft <!-- bsc-ledger:ISTARA-PI-MODEL-MIGRATION-20260822-PLAN-C -->
Did: Updated the authoritative slot-C draft `docs/build-stream/plans/istara-pi-model-migration-20260822-plan-c.md` after rechecking the current tree and all three carried drafts; corrected its focused verification matrix to use the existing `tests/test_llm_servers.py` and frontend `test:unit` script.
Result: Independent plan covers the Pi canonical catalog/resolver and dependency boundary, legacy storage/routing/encryption migration, both explicit engines, embeddings/vector-space invariant, Petals isolation, audio/transcription capability contracts, UI, testing-branch QA, managed VPS/Dokploy/vpsctl acceptance, security/docs obligations, reversible retirement, and owner gates. No implementation or live workload changes.
Verified: pinned native `compass-forge status`, `next`, and compact `agent-brief` (project resolved; Rust runtime); Compass Forge impact/why/test-impact; `python -m pytest tests/pi_migration/test_count_to_zero.py -q` -> 3 passed; `git diff --check` clean; current-tree existence check corrected the stale/nonexistent test path and frontend script.
Next: Synthesize A/B/C into one MECE master plan, freeze it, and stop at the owner approval gate.

### L-6 | 2026-08-22T12:09:26Z | S1-plan | deepseek/deepseek-v4-pro | architect | draft <!-- bsc-ledger:ISTARA-PI-MODEL-MIGRATION-20260822-REPLAN-B-r1 -->
Did: Repaired the slot-B consensus draft. The L-3 slot-B draft had landed at the misnamed path `docs/build-stream/plans/istara-pi-model-management-migration-20260822-plan-b.md`, which the synthesis phase cannot consume; wrote the full S1 draft to the task's authoritative `plan_file` `docs/build-stream/plans/istara-pi-model-migration-20260822-plan-b.md` and removed the misnamed duplicate in the same commit (mirroring REPLAN-A-r1/L-4). Re-verified every current-tree fact at repair time and added: correction C7 (`vpsctl.py` lives in the vps skill at `~/.pi/agent/skills/vps/scripts/vpsctl.py`, not repo `scripts/`; every VPS command in the draft now uses the skill path); V15 (repo QA/governance scripts and extra test anchors present; `scripts/multivac_*` and `tests/llm_servers.py` absent — never cited); V16 (frontend anchor path `frontend/src/components/settings/ProjectSettingsView.tsx`). No code touched.
Result: Authoritative slot-B draft exists at the path the synthesis phase reads; covers the six manifest waves, canonical identity model (model_id/endpoint_id/credential_ref/embedding+audio profiles), resolver/transport boundary, engine precedence (per-call > header x-istara-agent-engine > project agentic_engine > settings.agentic_engine_default="legacy"; no silent fallback), reversible retirement state machine S0-S5 with feature-flag registry + deprecation/removal criteria, exact data/secret migration + rollback playbook, per-wave acceptance + commands, isolated VPS acceptance/cleanup per the vps skill (C1/C5/C7), docs/manifests/security/test-ownership obligations, risk register R1-R11, Definition of Ready/Done + owner gates, coverage matrix vs carried drafts A/B/C. ISTARA-PI-MODEL-MIGRATION-20260822-REPLAN-B-r1.
Verified: `npm view` -> 0.84.2 / 0.84.2 (passed; tree pins 0.83.0 / 0.80.10); `python3 scripts/pi_migration_inventory.py --json` -> 1 allowlisted permanent site (legacy.py:599), ratchet 0 (passed); `compass-forge gate before --task ISTARA-PI-MODEL-MIGRATION-20260822-REPLAN-B-r1 --summary` -> fail, 30 inherited, 0 new, drift route=4/type=2, warnings=188 (passed as baseline); `uv run --project backend python -m pytest tests/pi_migration/test_count_to_zero.py -q` -> 3 passed; `python3 scripts/security_benchmark.py --fail-on-threshold` -> 28/28, 100.0%, pass; `python3 scripts/feature_docs.py --seed-missing --generate-site --check` -> 86 features, 224 artifacts, 0 seeded (passed); `python3 ~/.pi/agent/skills/vps/scripts/vpsctl.py --help` -> 7 subcommands (passed); 38/38 V13 test anchors present, 3/3 V14 absent (passed); `git diff --check` clean. CF evidence rows on ISTARA-PI-MODEL-MIGRATION-20260822-REPLAN-B-r1.
Next: All three authoritative drafts now exist (A repaired, B repaired, C); consensus synthesis reconciles them into one MECE master plan with a coverage matrix, freezes the plan, and stops at the owner approval gate before any implementation task is released.

### L-2 | 2026-08-22T12:10:00Z | S1-plan | owner | cast-manager | Phase 0

Did: Managed the cast during planning. Diagnosed PLAN-C blocked-loop: the architect-a REPLAN worker generated `backend/uv.lock` (1.5MB, untracked) while validating `uv run` commands, and the gate `after --new-only` treated it as a new large file, reopening PLAN-C repeatedly; architect-c had no fallbacks so escalation was inert. Removed the spurious file and added `backend/uv.lock` to `allowed_large_file_globs` + `ignored_file_globs` in the worktree and workspace recipes (config-only, no source code). Reopened PLAN-C and cleared the stale escalation state; architect-c re-dispatched (session 8/9).

Result: Gate `after --new-only` now reports zero new issues with uv.lock present. Architect-c can complete PLAN-C with valid finalization.

Verified: `compass-forge gate after --new-only --report-format json` (new_issues: []); `conductor.py status` (daemon up); sessions 8/9 architect-c active.

Next: Monitor planning to convergence; expect PLAN-C done, then MECE synthesis and owner approval gate.

### L-7 | 2026-08-22T12:15:38Z | S1-plan | gpt-5.6-luna | planner | istara-pi-model-migration-20260822-architect-c <!-- bsc-ledger:ISTARA-PI-MODEL-MIGRATION-20260822-MASTER-C -->
Did: istara-pi-model-migration-20260822-architect-c stage on task ISTARA-PI-MODEL-MIGRATION-20260822-MASTER-C (harness fallback entry; the model did not append one).
Result: task ISTARA-PI-MODEL-MIGRATION-20260822-MASTER-C finished; worktree head 15f26486.
Verified: see Compass Forge evidence rows on ISTARA-PI-MODEL-MIGRATION-20260822-MASTER-C (command + self_report + stage_attribution).
Next: conductor advances the pipeline on evidence.
### L-8 | 2026-08-22T12:17:22Z | S1-plan | deepseek/deepseek-v4-flash | synthesizer | synthesize <!-- bsc-ledger:ISTARA-PI-MODEL-MIGRATION-20260822-MASTER-A -->
Did: Synthesized the three immutable candidate snapshots (slot A `8b084d99…`, slot B `6ca5b84c…`, slot C `a7e88f54…`) into ONE MECE master plan at `docs/build-stream/plans/istara-pi-model-management-20260822-master-a.md` (610 lines, 17 sections). Reconciled overlaps/conflicts: the three drafts' retirement state vocabularies merged into two orthogonal axes (row/endpoint migration state + deployment stage S0–S5) plus the `PI_MODEL_MANAGEMENT_MODE` registry (§6); risk registers merged into R1–R13 (§14); rollback playbooks merged into one sequence (§7.4); per-wave verification command sets consolidated and re-verified against the tree (§8). Closed gaps: C8 (fresh disposable DBs + CF impact/why/test-impact packs before implementation), explicit transition rule with rollback-drill + owner gates (§6), VPS single-service reality check C5 (§9.3), vpsctl skill path C7 (§9), encryption context/version compatibility with standalone Pi. Coverage matrix §15 maps every section to its draft inputs.
Result: Complete slot-A master-plan candidate covering the full task scope: legacy LLM Server storage/routing/encryption consumers, both agentic engines, Pi provider/model catalog + endpoint resolver, embeddings/vector-space invariant, Petals donor bridge, audio/transcription flows, UI contracts, testing-branch Docker QA, VPS deployment per the vps skill, reversible staged LLM Server retirement, exact data/secret migration + rollback, latest verified Pi dependency (0.84.2, re-verify at execution), no duplicate model identity semantics, feature-flag/deprecation/removal criteria, per-wave acceptance + commands, docs/manifest obligations, security benchmark coverage, isolated VPS deployment/cleanup. F-1 (multivac→VPS) bound into the plan (C1). No vote (sole synthesis round). ISTARA-PI-MODEL-MIGRATION-20260822-MASTER-A.
Verified: `npm view` → 0.84.2 / 0.84.2 (passed; tree pins 0.83.0/0.80.10); `python3 scripts/pi_migration_inventory.py --json` → 1 allowlisted permanent site, ratchet 0 (passed); `compass-forge gate before --task …-MASTER-A --summary` → fail, 30 inherited, 0 new, 0 actionable (passed as baseline); `uv run --project backend python -m pytest tests/pi_migration/test_count_to_zero.py -q` → 3 passed; `python3 scripts/security_benchmark.py --fail-on-threshold` → 28/28, 100.0%, pass; `python3 scripts/feature_docs.py --seed-missing --generate-site --check` → 86 features, 224 artifacts, 0 seeded; `pytest --collect-only` six key surfaces → 62 tests collected; `python3 ~/.pi/agent/skills/vps/scripts/vpsctl.py --help` → 7 subcommands; 40/40 V13 anchors present, 3/3 V14 obligations absent (passed); `git diff --check` clean. CF evidence rows (command ×3 + self_report) on …-MASTER-A.
Next: Vote round compares master-plan candidates; conductor freezes the consensus plan and stops at the owner approval gate before any implementation task is generated or released.

### L-9 | 2026-08-22T12:20:03Z | S1-plan | deepseek/deepseek-v4-pro | architect | synthesize <!-- bsc-ledger:ISTARA-PI-MODEL-MIGRATION-20260822-MASTER-B -->
Did: Wrote the slot-B MECE master-plan synthesis candidate to `docs/build-stream/plans/istara-pi-model-migration-20260822-master-b.md` (544 lines). Re-read all three immutable consensus snapshots (SHA-verified against consensus.json: A 830a54b9, B ffa5899f, C fd6fa270) and reconciled them into ONE master plan (not a concatenation): unified retirement model (§6: global mode registry + per-row state machine + S0-S5 phases), 13-item conflict/correction table C1-C13 (multivac->VPS, six-wave re-baselining, 30-inherited gate baseline, `pi_api_endpoints` naming, single-service VPS reality check, environment prerequisites, vpsctl skill path, test-anchor corrections, `uv run --project backend` command canonicalization, state-machine unification, Wave-1 dependency update, frontend path fix, lockstep lab pin), merged per-wave acceptance + exact verification commands for all six manifest waves, unified risk register R1-R14, Definition of Ready/Done + owner gates, and two coverage matrices (§0 draft->section; §15 requirement->section).
Result: Complete MECE master-plan candidate B exists at the authoritative plan_file for synthesis round `0bb85df72bbe6604f51a`; the parallel slot-C candidate (master-c.md) exists in the worktree. Ready for the vote phase. ISTARA-PI-MODEL-MIGRATION-20260822-MASTER-B.
Verified: `npm view` -> 0.84.2 / 0.84.2 (tree pins 0.83.0 / 0.80.10); `uv run --project backend python -m pytest tests/pi_migration/test_count_to_zero.py -q` -> 3 passed; `python3 scripts/pi_migration_inventory.py --json` -> 1 allowlisted permanent site, ratchet 0; pinned-CF `gate before --summary` -> fail, 30 inherited / 0 new / 0 actionable, drift route=4 type=2, warnings=188; `vpsctl.py --help` -> 7 subcommands at the vps skill path; snapshot SHA triple-check -> matches consensus.json; manifest binding hash b9c8ff0c re-derived from canonical JSON; `git diff --check` clean. CF evidence rows 104-111 on ISTARA-PI-MODEL-MIGRATION-20260822-MASTER-B.
Next: Consensus vote phase compares the two master candidates (master-b, master-c) and votes; the conductor freezes the winning plan and stops at the owner approval gate before any implementation task is released. No vote cast in this synthesize phase.

### L-10 | 2026-08-22T12:24:25Z | S1-plan | deepseek/deepseek-v4-flash | synthesizer | synthesize <!-- bsc-ledger:ISTARA-PI-MODEL-MIGRATION-20260822-REMASTER-A-r1 -->
Did: Repaired the slot-A MECE master-plan synthesis. The L-8 synthesis had landed at the misnamed path `docs/build-stream/plans/istara-pi-model-management-20260822-master-a.md`, which the vote phase cannot consume under this task's `plan_file`; wrote the full MECE master plan to the authoritative `plan_file` `docs/build-stream/plans/istara-pi-model-management-migration-20260822-master-a.md` and removed the misnamed duplicate in the same commit (mirroring the REPLAN-A/B-r1 draft repairs). Re-verified every current-tree fact at repair time (2026-08-22).
Result: Authoritative slot-A MECE master-plan candidate exists at the path the vote phase reads; covers the full task scope: legacy LLM Server storage/routing/encryption consumers, both agentic engines, Pi provider/model catalog + endpoint resolver, embeddings/vector-space invariant, Petals donor bridge, audio/transcription flows, UI contracts, testing-branch Docker QA, VPS deployment per the vps skill, reversible staged LLM Server retirement (three orthogonal axes + mode registry), exact data/secret migration + rollback, latest verified Pi dependency (0.84.2, re-verify at execution), no duplicate model identity semantics, feature-flag/deprecation/removal criteria, per-wave acceptance + commands, docs/manifest obligations, security benchmark coverage, isolated VPS deployment/cleanup. ISTARA-PI-MODEL-MIGRATION-20260822-REMASTER-A-r1.
Verified: `npm view` → 0.84.2 / 0.84.2 (passed); `python3 scripts/pi_migration_inventory.py --json` → 1 allowlisted permanent site, ratchet 0 (passed); `compass-forge gate before --task …-REMASTER-A-r1 --summary` → fail, 30 inherited, 0 new, 0 actionable, drift route=4/type=2, warnings=188 (passed as baseline); `pytest --collect-only` six key surfaces → 62 tests collected (passed); `python3 scripts/security_benchmark.py --fail-on-threshold` → pass (passed); `python3 scripts/feature_docs.py --seed-missing --generate-site --check` → 86 features, 224 artifacts, 0 seeded (passed); `python3 ~/.pi/agent/skills/vps/scripts/vpsctl.py --help` → 7 subcommands (passed); `git diff --check` clean. CF evidence rows (command ×4 + self_report) on …-REMASTER-A-r1.
Next: Vote round compares the master-plan candidates (a repaired, b, c); conductor freezes the consensus plan and stops at the owner approval gate before any implementation task is generated or released.

### L-11 | 2026-08-22T12:37:59Z | S1-plan | deepseek/deepseek-v4-pro | voter | vote <!-- bsc-ledger:ISTARA-PI-MODEL-MIGRATION-20260822-VOTE-B -->
Did: Read both master-plan candidates supplied for vote round ef3baec72460f4802e2b — slot a (`docs/build-stream/plans/istara-pi-model-migration-20260822-master-a.md`, candidate ec3a76e7…, 624 lines) and slot c (`docs/build-stream/plans/istara-pi-model-migration-20260822-master-c.md`, candidate a1619826…, 716 lines) — and verified each plan_file is byte-identical to its frozen consensus snapshot. No plan files edited; no code touched.
Result: Voted slot a (candidate ec3a76e75d82e2d4495aec7d0c251f128fda99643de77b1180f56c00f9bc34ed). Rationale: A models retirement as three orthogonal axes (per-row migration state incl. canary_verified + rollback_ready→legacy_compat × S0–S5 deployment stage × PI_MODEL_MANAGEMENT_MODE registry) vs C's single linear S0–S5; A adds C8 (fresh disposable DBs + mandatory CF impact/why/test-impact packs), 17 verified facts (V1–V17) vs 16, risk register R1–R13 vs R1–R11, surface-by-surface test-ownership matrix, 8-item removal criteria, and a security-benchmark/review checklist — while retaining everything C covers (per-wave verification commands, VPS strict-profile acceptance, coverage matrix, owner gates). ISTARA-PI-MODEL-MIGRATION-20260822-VOTE-B.
Verified: `shasum -a 256` snapshots + plan files → a=10096535…, c=85eae608… (both match consensus.json); `diff -q` plan vs snapshot → identical for both (A MATCH, C MATCH); `wc -l` 624/716. CF evidence rows: command (id 138) + plan_vote (id 139) + self_report (id 140) on ISTARA-PI-MODEL-MIGRATION-20260822-VOTE-B.
Next: Remaining vote slot(s) record plan_vote; conductor tallies the round, freezes the winning consensus plan, and stops at the owner approval gate before any implementation task is generated or released.
