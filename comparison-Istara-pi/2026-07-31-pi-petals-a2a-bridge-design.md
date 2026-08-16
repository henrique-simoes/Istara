# Pi ↔ Petals Bridge over A2A — Design

Date: 2026-07-31
Status: proposal (pre-spec). Grounded in `conductor/pi-bench-retake-20260722` @ L-67.
Author: Kimi (k3), at owner request: *"understand how to route petals with pi … use the
already implemented A2A protocol so they can talk in a common space."*

---

## 1. The problem, precisely

Istara has two compute topologies that fundamentally cannot see each other today:

| | Pi engine (`pi_runtime` + pi-ai) | Petals / donated compute (ComputeRegistry) |
|---|---|---|
| Connection shape | **Outbound HTTP** to an OpenAI-compatible `base_url` | **Inbound reverse WebSocket** — donors dial *into* Istara (`compute_node_transport.py`, `compute_node_invocation.py:57-77,178-191,323-333,362-372`) |
| Identity model | `PiModelManager` catalog, exact-identity, capability-filtered; **relay/browser donor rows are NEVER projected** (`model_manager.py:203`) | Node registry with health, capacity scoring, project-scope authorization (`compute_registry_routing.py`) |
| Ensembles | `engine.run_ensemble(distinct=True)` over identity-distinct HTTP endpoints | `validation.full_ensemble` over distinct healthy nodes (legacy engine only) |
| Hard invariant | `pi_runtime` must never import or mutate ComputeRegistry | Donors are never schedulable Pi endpoints |

The 2026-07-20 independent review called donated compute "structurally not coverable"
by pi-agent-core (opposite connection topology). That verdict is correct **as long as
we try to make pi-ai speak reverse-WebSocket**. This design does not do that.

## 2. Key insight

Pi does not need to speak to donors. Pi needs an **identity-pinned, OpenAI-compatible
HTTP endpoint** that *happens to be served by a donor*. Istara already owns both ends
of that translation:

- The **A2A layer** (`backend/app/api/routes/a2a.py`) is the common space: JSON-RPC,
  agent-card discovery, project scoping, replay protection, rate limiting, and —
  critically — the dispatcher already resolves engines from **A2A envelope metadata**
  (`agentic/dispatcher.py:14`), and Pi already has A2A delegation seams
  (`pi_runtime/seams.py`: `a2a_task` / `pi_delegate`).
- The **ComputeRegistry** is the only allowed talker to donors — leave that untouched.

So the bridge is a **server-side shim**, not a Pi fork.

## 3. Architecture: three planes

```
        ┌─────────────────────────── Istara backend ───────────────────────────┐
        │                                                                      │
 Pi turn│   PiModelManager            PetalsBridge (NEW, outside pi_runtime)    │
 (pi-ai)│   catalog entry:            ┌────────────────────────────┐           │
   ───────► pi-petals-<node_id>  ──►  │ OpenAI-compatible loopback │           │
  HTTP  │   kind=petals,             │ /v1/chat/completions       │           │
  /v1/* │   base_url=loopback        │                            │           │
        │                            │  translate: HTTP → registry│           │
        │                            │  llm_request/stream        │           │
        │                            └───────────┬────────────────┘           │
        │                                        │                            │
        │                            ComputeRegistry (unchanged)              │
        │                             routing · health · project scope        │
        │                                        │ reverse WS                 │
        └────────────────────────────────────────┼────────────────────────────┘
                                                 ▼
                                          donor node (petals)

  CONTROL PLANE (A2A): agent-card advertises `compute.petals.<node>` capabilities,
  health, consent policy, cost class; A2A task envelopes carry project scope,
  budget attestation, and per-slot MoA provenance (record_pi_a2a_event).
```

### 3.1 Data plane — the loopback shim (the missing piece)

A backend service (`backend/app/core/petals_bridge.py`, outside `pi_runtime/`,
preserving the isolation invariant) that:

1. For each healthy, consented donor node, registers a **PiModelManager catalog
   entry**: `pi-petals-<node_id>`, `kind="petals"`, `base_url` = loopback shim URL,
   `model` = the donor's served model id. Registration is one-directional projection
   (registry → read-only catalog entries), exactly like the W8 `LLMServer` projection.
2. Serves an OpenAI-compatible `POST /v1/chat/completions` (+ streaming). Each call:
   - resolves `model`/endpoint identity → donor node id;
   - dispatches through `ComputeRegistry` chat/stream **pinned to that node**
   (no capacity re-scheduling — identity pinning, not donor-style scoring);
   - maps the registry response back to OpenAI wire format, including
   `usage` when the donor reports it, and marks `estimate=True` semantics otherwise.
3. Fail-closed: donor dropout / unhealthy / unconsented → typed 503 with
   `petals_unavailable`; **never** silent fallback to a paid API route.

Pi-side: zero changes to pi-ai. The shim is just another endpoint.

### 3.2 Control plane — A2A as the common space

- **Discovery**: the A2A agent card advertises each bridge capability
  (`compute.petals.<node_id>`: model, context window, cost class `donated`,
  consent scope, health). Pi-side orchestration and the benchmark harness can
  enumerate petals capacity through the same A2A surface used for agent tasks.
- **Task envelope**: bridge executions emit A2A-shaped task records
  (project scope, budget attestation, `engine=pi` + `route=petals` metadata) so
  telemetry, the usage ledger (§5.5 one-row-per-dispatch), and
  `record_pi_a2a_event` stay uniform with the existing Pi A2A seams.
- **Delegation**: A2A tasks addressed to `compute.petals.*` from *other* agents
  (legacy engine, external A2A peers) route through the same bridge — A2A is the
  single rendezvous, per the owner's intent.

### 3.3 Policy plane — consent, privacy, accounting

- **Donor consent**: donors opt into `pi_served` traffic explicitly (new flag on
  the donor registration; default off). Project-scope authorization
  (`compute_registry_routing.py:181-190,206-228`) applies unchanged.
- **Privacy**: prompts on donated nodes are visible to the donor. Projects opt in
  per project (`agentic_engine` / route policy); the bridge stamps
  `route_evidence.route_kind="petals_bridge"` on every record so no report can
  silently mix donated and API traffic.
- **Accounting**: dispatcher contract unchanged — one usage-ledger row per
  dispatch; donor usage is estimate-flagged when the node cannot report tokens;
  bridge calls are `cost_usd=0` but still reserve/commit so budget math stays
  uniform in benchmarks.

## 4. What this unlocks

1. **Pi orchestrating petals**: chat turns, plan-and-execute, research-spine loops
   on the Pi engine served by donated compute — the thing the Jul-20 review said
   was impossible.
2. **True MoA over petals on the Pi engine**:
   `engine.run_ensemble(distinct=True)` over N `pi-petals-*` endpoints gives
   N-distinct-node ensembles with genuine model/hardware diversity — the
   full_ensemble benchmark lane (currently 100% degraded by design on one API
   route) becomes testable, and production research-spine validation gains a
   free-diversity ensemble source.
3. **Mixed ensembles**: API endpoints + petals endpoints in one `distinct=True`
   ensemble, each slot's provenance recorded (route_kind per slot).
4. **No Pi fork**: pi-ai stays vanilla and independently updateable (the owner's
   version-pinning constraint); the bridge is Istara code.

## 5. Deliberately rejected alternatives

- **Inbound-WS provider inside pi-ai**: forks pi-ai, breaks update-on-pin, and
  re-implements registry health/scheduling inside the vendor package. Rejected.
- **Project donors into PiModelManager directly** (like `pi-llm-<id>` rows):
  violates the topology (no HTTP base_url exists) and blurs the isolation
  invariant. Rejected (`model_manager.py:203` stays as-is).
- **Pi talks A2A directly as its LLM transport**: pi-ai's provider contract is
  chat-completions HTTP; wrapping every turn in JSON-RPC tasks would require a
  custom pi provider anyway *and* loses wire compatibility with benchmarks.
  A2A stays control plane, not data plane.

## 6. Rollout (Compass Forge specs)

| Wave | Deliverable | Gate |
|---|---|---|
| P0 | `petals_bridge.py` loopback shim (single node, non-streaming) + catalog projection + isolation tests (`test_same_model_donor_isolation.py` stays green) | offline tests |
| P1 | Streaming, multi-node registry, health/consent enforcement, `route_kind="petals_bridge"` evidence | 503 fail-closed tests |
| P2 | A2A agent-card capabilities + task-envelope telemetry + usage-ledger integration | security benchmark gate |
| P3 | `distinct=True` ensembles over `pi-petals-*`; full_ensemble benchmark lane re-run with real diversity | owner gate, bounded live run |
| P4 | UI: donor consent toggle (`pi_served`), project route policy, per-slot provenance in reports | feature docs regen |

## 7. Open questions for the owner — RESOLVED 2026-07-31 (owner: "yes for all 3, implement now")

1. ~~Should petals-served Pi traffic be allowed for **production research spine**
   runs by default, or benchmark/eval-only at first?~~ → **ALLOWED for production
   research spine by default** (owner decision, supersedes the eval-only
   recommendation; P3 evidence still gathered, but does not gate production use).
2. ~~Do donors see that a Pi engine (vs legacy) served the request?~~ → **YES** —
   engine identity is shown in the donor dashboard (transparency requirement,
   lands with the P2 telemetry work; donor console gets `engine` per request).
3. ~~Mixed ensembles (API + petals in one MoA): allowed, or homogeneous per cost
   class?~~ → **ALLOWED** — mixed-cost-class ensembles are permitted, with
   per-slot provenance (`route_kind`) recorded on every slot so reports can
   separate donated vs API traffic.
