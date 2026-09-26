#!/usr/bin/env python3
"""Export `agentic_usage_rows` as telemetry contract v1 rows (north-star T5.2).

Telemetry contract v1 is `schemas/telemetry.v1.schema.json` in adaptive-product-contracts
(package 0.2.0). Rows are metadata only: no prompt, no completion, no tool payload, and no
`content` key at all. Every number carries its provenance; what the source does not record is
`null` with provenance `unknown`, never 0. `host` is an alias, never a machine name. The source
is opened read-only and immutable. Output is JSON lines on stdout, and a JSON summary (rows
read, emitted, skipped by reason, unknown per measure) on stderr. Standard library only.
"""
import argparse
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path

SEMCONV = {"repository": "open-telemetry/semantic-conventions", "tag": "v1.37.0"}
UNKNOWN = {"value": None, "provenance": "unknown"}
STAMP_RE = re.compile(r"(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})(?:\.(\d+))?(?:Z|\+00:00)?")


def digest(*parts):
    return hashlib.sha256("\x1f".join(str(part) for part in parts).encode("utf-8")).hexdigest()


def stamp(text):
    """ISO 8601 UTC with a 6-digit fraction or none. The source writes UTC; a value with any
    other offset does not match and the row is skipped and counted."""
    match = STAMP_RE.fullmatch(text) if isinstance(text, str) else None
    if not match:
        return None
    fraction = "." + match.group(3)[:6].ljust(6, "0") if match.group(3) else ""
    return "%sT%s%sZ" % (match.group(1), match.group(2), fraction)


def measure(value, provenance, whole=True):
    """Unknown is null with provenance `unknown`, never 0."""
    bad = value is None or isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0
    if bad or (whole and not isinstance(value, int)):
        return dict(UNKNOWN)
    return {"value": value, "provenance": provenance}


def identity(repository, host, harness, **known):
    base = {"repository": repository, "host": host, "harness": harness, "model": None, "effort": None,
            "lifecycle_item": None, "ledger_id": None, "cf_spec": None, "cf_task": None, "actor_session": None}
    base.update(known)
    return base


def text_or_none(value):
    return value if isinstance(value, str) and value else None


def project(database, host):
    rows = read_rows(database, "SELECT * FROM agentic_usage_rows ORDER BY created_at, id")
    events, skipped = [], {}
    for row in rows:
        at = stamp(row.get("created_at"))
        if at is None:
            skipped["unreadable_timestamp"] = skipped.get("unreadable_timestamp", 0) + 1
            continue
        tokens = "estimated" if row.get("estimate") else "provider_recorded"
        parts = [row.get("input_tokens"), row.get("cache_read"), row.get("cache_write")]
        whole = all(isinstance(part, int) and not isinstance(part, bool) and part >= 0 for part in parts)
        spent = (sum(parts) if whole else 0) + (row.get("output_tokens") or 0)
        # The columns default to 0, so a 0 beside real work is a default, not a measurement:
        # cost 0 with tokens spent, and latency 0 on any row, are emitted as unknown.
        cost = row.get("cost_usd") if (row.get("cost_usd") or spent == 0) else None
        latency = row.get("latency_ms") or None
        gen_ai = {"gen_ai.operation.name": "invoke_agent"}
        if text_or_none(row.get("purpose")):
            gen_ai["gen_ai.agent.name"] = row["purpose"]
        events.append({
            "schema_version": "1.0", "event_id": "istara-usage-" + digest(row["id"])[:24],
            "event_kind": "agent_span", "recorded_at_utc": at,
            "trace_id": digest("istara", row.get("session_id") or row.get("task_id") or row["id"])[:32],
            "span_id": digest(row["id"])[:16], "parent_span_id": None,
            "identity": identity("istara", host, "istara-" + (text_or_none(row.get("engine")) or "unknown"),
                                 model=text_or_none(row.get("model")), actor_session=text_or_none(row.get("session_id"))),
            "semconv": dict(SEMCONV), "gen_ai": gen_ai,
            "measures": {
                "gen_ai.usage.input_tokens": measure(sum(parts) if whole else None, tokens),
                "gen_ai.usage.output_tokens": measure(row.get("output_tokens"), tokens),
                "duration_ms": measure(latency, "locally_counted", whole=False),
                "cost_usd": measure(cost, "estimated", whole=False)}})
    return {"rows_read": len(rows), "events": events, "skipped": skipped}


def read_rows(database, query):
    path = Path(database).resolve()
    if not path.is_file():
        raise SystemExit("no database at %s" % path)
    db = sqlite3.connect("file:%s?immutable=1" % path, uri=True)
    db.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in db.execute(query)]
    except sqlite3.DatabaseError as exc:
        raise SystemExit("%s has no readable source table (%s)" % (path, exc))
    finally:
        db.close()


def unknown_counts(events):
    names = sorted({name for event in events for name in event["measures"]})
    return {name: sum(1 for event in events if event["measures"].get(name, {}).get("provenance") == "unknown")
            for name in names}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--database", required=True)
    parser.add_argument("--host", required=True, help="the host alias, e.g. laptop-primary")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[a-z][a-z0-9-]*", args.host):
        raise SystemExit("--host is an alias: lowercase letters, digits and hyphens")
    result = project(args.database, args.host)
    for event in result["events"]:
        sys.stdout.write(json.dumps(event, sort_keys=True) + "\n")
    json.dump({"rows_read": result["rows_read"], "emitted": len(result["events"]), "skipped": result["skipped"],
               "unknown": unknown_counts(result["events"])}, sys.stderr)
    sys.stderr.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
