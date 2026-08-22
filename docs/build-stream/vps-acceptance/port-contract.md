# Proposed port contract — strict single-workload VPS acceptance service

Status: **PROPOSED — awaiting owner approval.** No deployment and no firewall
change happen until the owner approves this contract through the owner approval
gate (the record of that approval is cited here when it exists).

## 1. Application contract

| Item | Value | Grounding |
|---|---|---|
| Acceptance image | `qa/Dockerfile` build from the testing-branch head (product backend + QA tooling, `USER istara`) | master plan C5/V12; qa/Dockerfile is the dedicated single-service acceptance image |
| Container target port | `8000/tcp` (uvicorn `app.main:app`, `EXPOSE 8000`) | qa/Dockerfile |
| Health check | `curl -f http://localhost:8000/api/health` (`GET /api/health`, backend/app/main.py:894) | qa/Dockerfile HEALTHCHECK |
| Image identity | immutable `@sha256:<digest>` recorded at build time; mutable tags rejected | vps skill strict contract |

## 2. Proposed published host port

| | Proposal |
|---|---|
| Host port | **`18443/tcp`** (IPv4 `0.0.0.0` + IPv6 `::`, `mode: host`) |
| Rationale | Unbound on the host today. Inventory event 608 observed public listeners 22, 80, 443, 2377, 3000, 7946, 8787, 8999 and ufw allow 22, 8787, 8999. `18443` avoids every bound port, sits in the high unprivileged range, and is not adjacent to any existing port. |
| Alternative | `18444/tcp` if the owner prefers (also unbound today). |
| Removal | The published port is initiative-owned and removed with the service at cleanup (master plan §9.4). |

## 3. Firewall / DOCKER-USER plan (default: NO CHANGE)

- Before deploy: record `ufw status numbered`, `ss -ltnH`, `iptables -S DOCKER-USER`
  (baseline already observed in preflight events 591–602 / inventory event 608).
- Docker-published ports bypass ordinary ufw rules; the `DOCKER-USER` chain is
  the deliberate Docker packet-policy point (vps skill).
- Default: **no ufw or DOCKER-USER change** — the approved port is reachable via
  the Docker-published path only; verify-exposure checks it externally on each
  enabled address family.
- If the owner wants the published port restricted (e.g., source-IP scoping),
  that is a **separate, scoped firewall change** requiring its own owner
  approval; it is NOT part of this contract.

## 4. Evidence produced after approval (all via vpsctl.py, audited)

1. `vpsctl.py preflight` and `vpsctl.py inventory` (fresh run; rollback target capture).
2. Build acceptance image from testing head; record immutable digest; substitute
   into the compose file; re-render and re-run the pre-deploy review checklist
   (compose-rendered-preview.yml must match).
3. `vpsctl.py verify-isolation --container <id> --network <project>_workload --approved-port 18443`
   — one attached network, one endpoint, `Internal: true`, no default route, no
   host/other-container reachability, only the approved published port.
4. `vpsctl.py verify-exposure --allowed-port 22 --allowed-port 18443` — external
   smoke test on IPv4 and IPv6 (where enabled).
5. Firewall before/after: `ufw status numbered`, `ss -ltnH`, `iptables -S DOCKER-USER`
   agree with the approved port list (no unapproved new listener/forwarding rule).
6. `vpsctl.py audit-verify` then `vpsctl.py audit-anchor`.
7. Cleanup proof for initiative-owned disposable artifacts (master plan §9.4).

## 5. Approval request (the text the owner is asked to approve)

> Approve the VPS acceptance deployment for the Istara Pi model-management
> migration (2026-08-22 run): the strict single-workload Dokploy Compose service
> defined in `docs/build-stream/vps-acceptance/docker-compose.strict-acceptance.yml`,
> published host port **18443/tcp** (or the chosen alternative) mapped to
> container port 8000, built from the `qa/Dockerfile` acceptance image at the
> testing-branch head with its immutable digest recorded before deploy, with
> **no firewall (ufw / DOCKER-USER) change**, rollback per
> `docs/build-stream/vps-acceptance/rollback-plan.md`, and cleanup of only
> initiative-owned disposable artifacts after acceptance. Existing VPS workloads
> (traefik, dokploy, dokploy-postgres, wildsync-relay, syncplay-server) are not
> touched.
