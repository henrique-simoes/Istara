# Build Stream: agentic usage as telemetry contract v1 (Ainulindalë H2)

<!-- STATUS BLOCK -->
```yaml
item: telemetry-export
branch: main
cf: { spec: CF-SPEC-31, tasks: [CF-486, CF-487, CF-488, CF-489, CF-490, CF-491, CF-492, CF-493, CF-494, CF-495, CF-496] }
phase: "Phase 1 — apply the prepared exporter"
stage: S2-execute
status: in-progress
blocked_on: null
last: { agent: claude-opus-5-5, at: 2026-09-24T04:58:53Z, ledger: L-1 }
next_action: "Merge; close CF-SPEC-31 on executed rows."
```
<!-- /STATUS BLOCK -->

## Roadmap

| Phase | Work | Status |
|---|---|---|
| 1 | Apply the prepared telemetry v1 exporter with its test | in-progress |

## Phase 1 — apply the prepared exporter

Ainulindalë's telemetry contract v1 (register H1) has one exporter per product; Istara's was prepared on
2026-09-20 and never applied (register H2). `scripts/export_telemetry_v1.py` reads `agentic_usage_rows`
read-only and writes metadata-only contract rows.

## Ledger

### L-1 | 2026-09-24T04:58:53Z | S2-execute | claude-opus-5-5 | executor | Phase 1
Did: applied `docs/ecosystem/ainulindale/patches/istara-telemetry-v1.patch` from Ainulindalë unchanged (`git apply --check` clean).
Result: `1 telemetry export test passed`.
Verified: `python3 scripts/test_export_telemetry_v1.py`.
Next: merge and close.
