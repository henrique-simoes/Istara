# VPS acceptance runbook — Istara Pi model-management migration (2026-08-22 run)

Status: **PREPARED — awaiting owner approval** (see §4). Read-only evidence is
complete; no deployment, no firewall change, and no workload mutation have
happened or will happen before the owner approves the port contract and service
definition (master plan §9, vps skill, finding F-1 of
ISTARA-PI-MODEL-MIGRATION-20260822-WAVE-qa-docs-vps-REVIEW).

## 1. Contract

- Strict single-workload Dokploy Docker Compose service:
  `docker-compose.strict-acceptance.yml` (one service, project-local
  `internal: true` bridge, one published port, no proxy/external network/Docker
  socket/privileged/host namespace, `read_only` + `cap_drop: ALL` +
  `no-new-privileges`, bounded pids/mem/cpu, healthcheck).
- Acceptance image: `qa/Dockerfile` build from the testing-branch head
  (dedicated single-service acceptance image per master plan C5/V12), pinned by
  immutable digest recorded at build time.
- Rendered preview: `compose-rendered-preview.yml` (pre-deploy review checklist
  included; re-render from the exact deploy file and compare).
- Port contract: `port-contract.md` (proposed published host port **18443/tcp**
  → container 8000; no firewall change by default).
- Rollback: `rollback-plan.md` (rollback target captured at deploy; no firewall
  rollback needed because no firewall change is made).

## 2. Procedure (strict order; every remote command via the vps skill's vpsctl.py — never raw SSH)

```bash
VPSCTL=~/.pi/agent/skills/vps/scripts/vpsctl.py
python3 $VPSCTL preflight                                   # 1. preflight (keychain-backed identity, helper integrity, audit DB)
python3 $VPSCTL inventory                                  # 2. inventory (read-only; observed Compose projects/containers/exposure)
# 3. build acceptance image from testing head; record immutable digest;
#    substitute into docker-compose.strict-acceptance.yml
docker compose -f docs/build-stream/vps-acceptance/docker-compose.strict-acceptance.yml config \
  > /tmp/acceptance-rendered.yml                            # 4. preview before deploy (compare with compose-rendered-preview.yml; stop on shared/proxy network or second service)
# 5. create the Dokploy Docker Compose service (strict profile, secrets only in the
#    Dokploy secret/environment UI); capture prior deployment identity as rollback target; deploy
python3 $VPSCTL verify-isolation --container <id> --network istara-pi-model-migration-20260822-acceptance_workload --approved-port 18443   # 6.
python3 $VPSCTL verify-exposure --allowed-port 22 --allowed-port 18443                        # 6. approved port set (IPv4+IPv6)
python3 $VPSCTL ssh -- ufw status numbered && python3 $VPSCTL ssh -- iptables -S DOCKER-USER   # 7. firewall before/after evidence (no change without owner approval)
python3 $VPSCTL audit-verify && python3 $VPSCTL audit-anchor                                  # 8. audit chain anchored
# cleanup of initiative-owned disposable artifacts only, after owner acceptance (rollback-plan.md §4)
```

## 3. Verification evidence required (post-approval)

1. `verify-isolation`: one attached network, one endpoint, `Internal: true`,
   no default route, no host/other-container reachability, exactly the approved
   published port — every check true.
2. `verify-exposure`: approved port set reachable externally on each enabled
   address family; no unapproved port added.
3. Firewall before/after + `DOCKER-USER` chain agree with the approved port
   list; no unapproved new listener or forwarding exception.
4. `audit-verify` passes; `audit-anchor` signs the chain head; audit event IDs
   reported (never secrets or raw output).
5. Rollback state preserved until owner acceptance; cleanup proof after.

## 4. Approval request (routed through the owner approval gate, 2026-08-22)

See `port-contract.md` §5 for the exact approval text. In short, the owner is
asked to approve: the strict single-workload service definition, published host
port **18443/tcp** (or alternative 18444) → container 8000, the `qa/Dockerfile`
acceptance image at the testing-branch head with immutable digest, **no firewall
change**, rollback per `rollback-plan.md`, cleanup of only initiative-owned
artifacts after acceptance, and no touching of the five existing VPS workloads.
Until that approval is recorded, this runbook's post-approval steps remain
**blocked by design** (master plan §9.3, vps skill, owner-approved boundaries:
"no firewall changes without owner approval").
