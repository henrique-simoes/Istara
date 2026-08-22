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
blocked_on: architect-b/c drafts
last:
  agent: deepseek/deepseek-v4-flash
  at: 2026-08-22T11:49:51Z
  ledger: L-2
next_action: "Architect B and C produce their independent drafts, then the synthesis phase reconciles all three into one MECE master plan; freeze the plan and stop at the owner approval gate before any implementation task is released."
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

