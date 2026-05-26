# Compute Donation Matrix

Spec: CF-SPEC-123 / CF-1581

| Area | Implementation Surface | Current Behavior | Classification | Action |
| --- | --- | --- | --- | --- |
| Architecture claim | `backend/app/core/compute_registry_*`, `backend/app/core/compute_node.py` | Istara routes whole chat/embedding/model requests to local, network, relay, or browser nodes. | Petals-inspired, not Petals-equivalent sharding | README and feature docs now say whole-request routing, not layer-wise transformer sharding. |
| Project scope | `compute_registry_routing.py`, `compute_node.py` | Relay/browser donors require a concrete `project_id` and matching `allowed_project_ids` before receiving project content. | Security-aligned | Preserve strict backend auth. |
| Local/server-owned capacity | `compute_registry_routing.py` | Local/network server-owned nodes can serve unscoped internal work. | Intended | Keep unscoped internal behavior separated from donor routing. |
| Donor registration | relay/browser node lifecycle | A donor can be registered/visible without having served project work. | Distinct lifecycle state | Benchmarks must not count registration as usage. |
| Donor readiness | registry readiness/model loading | Reachable/no-model-loaded differs from ready/routable. | Correct distinction | Benchmark should record readiness separately. |
| Donor selection | `selected_request_count` | Incremented when a node is selected for a request. | Route evidence | Benchmarks should capture deltas. |
| Donor served | `served_request_count` | Incremented after successful chat/stream service. | Strong usage evidence | Full multi-donor credit requires served deltas or route logs. |
| Donor failure | `failed_request_count` | Incremented on failed request attempts. | Diagnostic evidence | Report failures separately from usage. |
| Strict auto-routing | `compute_registry_invocation.py` | Enforces configured model matching only when strict routing is enabled. | Technical probe mode | Natural benchmark must leave strict routing off unless explicitly testing isolation. |
| Connection strings | `backend/app/core/connection_string.py` | User invites redeem to sessions; compute donation strings include relay/network information and network token where configured/generated. | Current auth contract | README.pt-BR updated away from old JWT URL. |
| Multi-donor benchmark | `tests/real_user_benchmark/*` | Distinguishes registration, readiness, selected, served, failed, and natural orchestration evidence. | Aligned after prior benchmark work | Canonical corpus now supplies representative document workload. |
