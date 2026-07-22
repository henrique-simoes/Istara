# tests/pi_benchmark — Pi vs Legacy benchmark apparatus

Implements the benchmark assets in master plan §10.3. Execution plan:
`docs/build-stream/2026-07-22-pi-benchmark.md`.

## Delivered (B0-1, schema-first foundation)

- **`schema.py`** — loads and validates run records against
  `comparison-Istara-pi/metrics-schema.json`. `validate_record()` is the one definition
  of "conforms to the schema" shared by every downstream asset. Import-safe at tier T0
  (no backend, DB, network, or model).
- **`fixtures/example_run_record.json`** — a canonical, schema-conformant record used by
  the tests and as living documentation of a run record's shape.
- **`test_metrics_schema.py`** — asserts the schema is a valid JSON Schema, the golden
  record validates, and a battery of malformed records is rejected (the acceptance-A1
  negative test).

## To follow (tracked in the lifecycle file)

`runner.py` (B0-4), `scenarios/` packs (B0-5), `feature_criteria.py` (B0-6), `judge.py`
(B0-7), `probes/` (B0-8), `--engine` plumbing in the two node harnesses (B0-2), legacy
usage capture + long-horizon token fix (B0-3), then the B1–B4 execution phases. T2/T3
runs are blocked behind owner gates G1/G2 (live-model permission and budget approval).

## Verify

```bash
python -m pytest tests/pi_benchmark/ -q
```

Run records and manifests are written to `.results/` (gitignored). Only generated,
secret-scanned report bundles under `comparison-Istara-pi/reports/` are tracked.
