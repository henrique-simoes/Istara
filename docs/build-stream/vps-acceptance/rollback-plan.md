# Rollback plan — strict single-workload VPS acceptance service

Owner-approved master plan §9.5 + vps skill: preserve the prior deployment
identity until the owner accepts; re-deploy prior Compose on verification
failure; record every rollback event in the audit chain. No firewall rollback
is needed if no firewall change was made (the default — this acceptance makes
no firewall change).

## 1. Rollback target capture (before deploy)

- `vpsctl.py inventory` records the current deployment identity of every
  workload on the host (audit DB `workloads` rows). For this acceptance the
  target is a **new** Dokploy Compose service; there is no prior deployment of
  this project to restore.
- The pre-deploy artifacts are themselves the rollback state:
  - `docker-compose.strict-acceptance.yml` (exact service definition)
  - `compose-rendered-preview.yml` (exact rendered configuration)
  - the recorded immutable image digest (substituted at deploy time)
- These stay in the repository until owner acceptance (master plan §9.5).

## 2. Rollback triggers

| Trigger | Action |
|---|---|
| `verify-isolation` reports any check false | Stop the service; remove the initiative-owned service/volumes; record rollback event in the audit chain |
| `verify-exposure` fails (port unreachable, or unapproved port observed) | Same as above; investigate before any second attempt |
| Firewall/DOCKER-USER evidence shows an unapproved listener/forwarding rule | Stop the service; do NOT edit firewall policy; escalate to the owner (no silent firewall change) |
| Health check never passes after deploy | Same as above |

## 3. Rollback procedure (owner-authorized deployer)

1. `vpsctl.py ssh -- docker compose -p istara-pi-model-migration-20260822-acceptance down` (or the Dokploy service stop/delete) — removes only the initiative-owned project resources.
2. Remove only initiative-owned named volumes if any were explicitly approved and created (`docker volume ls` filtered to the project prefix; the default profile creates none).
3. Record the rollback event in the audit chain (`vpsctl.py ssh -- <command>` audited; `audit-anchor` after the event).
4. Leave the host's existing workloads, ufw state, and `DOCKER-USER` chain exactly as found (no change was made by default; verify with a fresh `ufw status numbered` + `iptables -S DOCKER-USER` if the owner asks).

## 4. Acceptance → cleanup

Only after the owner accepts the deployment (master plan §9.4):

1. Remove the initiative-owned Dokploy Compose service (published port `18443`
   or approved alternative disappears with it).
2. Remove only initiative-owned disposable artifacts: this run's service,
   named volumes if created, rendered previews. Local audit rows stay in the
   gitignored audit DB; existing workloads and the audit database are untouched.
3. Record cleanup commands through `vpsctl.py ssh` (audited) and `audit-anchor`.

## 5. State log

| Step | Audit event | Status |
|---|---|---|
| Preflight + inventory (baseline, read-only) | 591–602, 608 | done (2026-08-22) |
| Service definition + rendered preview + port contract committed | — | done (2026-08-22, fix task r1) |
| Owner approval of port set + service definition | pending — routed via owner approval gate | open |
| Build image + record digest + substitute + re-render | — | pending approval |
| Deploy + verify-isolation + verify-exposure + firewall evidence + audit-anchor | — | pending approval |
| Owner acceptance + cleanup proof | — | pending |
