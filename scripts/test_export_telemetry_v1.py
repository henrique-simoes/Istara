#!/usr/bin/env python3
"""export_telemetry_v1.py: agentic_usage_rows become contract v1 rows; a default 0 is not a measurement. Run: python3 scripts/test_export_telemetry_v1.py (also collected by pytest)."""
import json
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
UNKNOWN = {"value": None, "provenance": "unknown"}
IDENTITY = ["actor_session", "cf_spec", "cf_task", "effort", "harness", "host", "ledger_id", "lifecycle_item",
            "model", "repository"]


def shape_ok(row):
    """The contract's load-bearing rules, checked without a schema library."""
    assert sorted(row["identity"]) == IDENTITY, row["identity"]
    assert "content" not in row and row["schema_version"] == "1.0"
    assert len(row["trace_id"]) == 32 and len(row["span_id"]) == 16 and len(row["event_id"]) >= 8
    for name, value in row["measures"].items():
        assert sorted(value) == ["provenance", "value"], (name, value)
        assert (value["value"] is None) == (value["provenance"] == "unknown"), (name, value)

SCRIPT = HERE / "export_telemetry_v1.py"
DDL = """CREATE TABLE agentic_usage_rows (id VARCHAR(36) PRIMARY KEY, created_at DATETIME, engine VARCHAR(16),
 purpose VARCHAR(120), project_id VARCHAR(36), session_id VARCHAR(36), agent_id VARCHAR(36), task_id VARCHAR(36),
 spine_phase VARCHAR(40), endpoint_id VARCHAR(120), node_id VARCHAR(120), model VARCHAR(200), input_tokens INTEGER,
 output_tokens INTEGER, cache_read INTEGER, cache_write INTEGER, total_tokens INTEGER, cost_usd FLOAT,
 tool_calls INTEGER, turns INTEGER, latency_ms FLOAT, stop_reason VARCHAR(60), outcome VARCHAR(20),
 estimate INTEGER, error_type VARCHAR(80))"""
ROWS = [("row-1", "2026-02-01 10:00:00.123456", "pi", "chat", "sess-1", "example-large", 10, 340, 1000, 100, 0.25, 812.5, 0),
        ("row-2", "2026-02-01 11:00:00", "legacy", "synthesis", None, "", 50, 20, 0, 0, 0.0, 0.0, 1),
        ("row-3", "2026-02-01 12:00:00", "pi", "chat", "sess-1", "example-large", 0, 0, 0, 0, 0.0, 3.0, 0),
        ("row-4", "not a date", "pi", "chat", None, "m", 1, 1, 0, 0, 0.0, 0.0, 0)]


def run(tmp):
    path = Path(tmp) / "istara.db"
    db = sqlite3.connect(path)
    db.execute(DDL)
    db.executemany("INSERT INTO agentic_usage_rows(id, created_at, engine, purpose, session_id, model, input_tokens,"
                   " output_tokens, cache_read, cache_write, cost_usd, latency_ms, estimate)"
                   " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", ROWS)
    db.commit()
    db.close()
    before = path.read_bytes()
    proc = subprocess.run([sys.executable, str(SCRIPT), "--database", str(path), "--host", "laptop-primary"],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert path.read_bytes() == before and sorted(p.name for p in Path(tmp).iterdir()) == ["istara.db"]
    return [json.loads(line) for line in proc.stdout.splitlines()], json.loads(proc.stderr)


def test_rows_are_projected_read_only_and_a_default_zero_is_unknown():
    with tempfile.TemporaryDirectory() as tmp:
        rows, summary = run(tmp)
    assert summary["rows_read"] == 4 and summary["emitted"] == 3 and summary["skipped"] == {"unreadable_timestamp": 1}
    assert summary["unknown"] == {"cost_usd": 1, "duration_ms": 1, "gen_ai.usage.input_tokens": 0,
                                  "gen_ai.usage.output_tokens": 0}, summary
    for row in rows:
        shape_ok(row)
    first, second, third = rows
    assert first["measures"]["gen_ai.usage.input_tokens"] == {"value": 1110, "provenance": "provider_recorded"}
    assert first["measures"]["duration_ms"] == {"value": 812.5, "provenance": "locally_counted"}
    assert first["recorded_at_utc"] == "2026-02-01T10:00:00.123456Z" and first["identity"]["harness"] == "istara-pi"
    assert second["measures"]["gen_ai.usage.input_tokens"] == {"value": 50, "provenance": "estimated"}
    assert second["measures"]["cost_usd"] == UNKNOWN and second["measures"]["duration_ms"] == UNKNOWN
    assert second["identity"]["model"] is None, "an empty model string is null, not a model called ''"
    assert third["measures"]["cost_usd"] == {"value": 0.0, "provenance": "estimated"}, "no tokens spent: 0 is a fact"


if __name__ == "__main__":
    test_rows_are_projected_read_only_and_a_default_zero_is_unknown()
    print("1 telemetry export test passed")
