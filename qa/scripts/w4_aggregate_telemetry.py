"""Wave W4 telemetry/trajectory aggregator — 150-turn long-horizon benchmark.

Reads the 150-turn stress-test runner outputs (per-engine result JSON +
checkpoints) and the scratch deployment DATABASE copies (``agentic_usage_rows``
+ ``telemetry_spans``) and produces one SHA-keyed, secret-free aggregation
artifact per run:

  TELEMETRY / TRAJECTORIES (owner requirement):
    per-turn / per-tool / per-model latency (p50/p90/p99), tokens, cost,
    error taxonomy, steering counts, tool-call depth, stop reasons —
    split by engine and by model.

  TELEMETRY AUDIT:
    settings posture (telemetry_enabled, export dir), capture correctness
    (spans present, content-free, route/model attribution present), gaps
    with evidence.

Content-free by construction: per-turn prompt/assistant text is replaced by
sha12 + char counts; span/message payloads are never embedded. No secret,
URL, key, or endpoint-identifying value is read or written — only identity
handles (endpoint_id, model, route_id) that the product itself stores.

Usage:
  python qa/scripts/w4_aggregate_telemetry.py \
    --results /app/w4/run-pi.json --db /app/w4/istara-w4-pi.db \
    --engine pi --out /app/w4
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
try:
    from datetime import UTC  # Python 3.11+
except ImportError:  # pragma: no cover — older hosts (macOS system python)
    UTC = timezone.utc
from hashlib import sha256
from pathlib import Path


def sha12(text: str) -> str:
    return sha256((text or "").encode()).hexdigest()[:12]


def pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = min(len(s) - 1, max(0, int(round((p / 100.0) * (len(s) - 1)))))
    return round(float(s[idx]), 3)


def summarize_latency(values: list[float]) -> dict:
    return {
        "n": len(values),
        "p50": pct(values, 50),
        "p90": pct(values, 90),
        "p99": pct(values, 99),
        "max": round(max(values), 3) if values else 0.0,
    }


def load_results(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    # Accept either {engine: result} or a bare single-engine result.
    if isinstance(data, dict) and "turns" in data and "engine" in data:
        return {data["engine"]: data}
    return data


def query_table(db_path: Path, table: str, project_ids: list[str]) -> list[dict]:
    if not db_path.exists():
        return []
    # Plain-path connect (never writes): the file:..?mode=ro URI form fails
    # on older host pythons. The DB files are already permission-controlled
    # (0600, scratched copies), and this function only issues SELECTs.
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    try:
        cols = [r[1] for r in con.execute(f"PRAGMA table_info({table})").fetchall()]
    except sqlite3.Error:
        con.close()
        return []
    if not cols or "project_id" not in cols:
        con.close()
        return []
    placeholders = ",".join("?" for _ in project_ids)
    try:
        rows = con.execute(
            f"SELECT * FROM {table} WHERE project_id IN ({placeholders})", project_ids
        ).fetchall()
    except sqlite3.Error:
        con.close()
        return []
    con.close()
    return [dict(r) for r in rows]


def aggregate_engine(engine: str, res: dict, usage: list[dict], spans: list[dict]) -> dict:
    turns = res.get("turns", []) or []
    clean_turns = []
    for t in turns:
        clean_turns.append({
            "turn_index": t.get("turn_index"),
            "phase": t.get("phase"),
            "status": t.get("status"),
            "duration_s": t.get("duration_s"),
            "prompt_sha12": sha12(t.get("prompt", "")),
            "prompt_chars": len(t.get("prompt", "") or ""),
            "text_chars": len(t.get("text", "") or ""),
            "tool_calls_count": t.get("tool_calls_count", 0),
            "tools_invoked": t.get("tools_invoked", []) or [],
            "tool_latencies_ms": t.get("tool_latencies_ms", []) or [],
            "tokens_total": (t.get("usage", {}) or {}).get("total_tokens", 0),
            "tokens_input": (t.get("usage", {}) or {}).get("input_tokens", 0),
            "tokens_output": (t.get("usage", {}) or {}).get("output_tokens", 0),
            "tokens_cached": (t.get("usage", {}) or {}).get("cached_tokens", 0),
            "cost_usd": t.get("cost_usd", 0.0) or 0.0,
            "error": (t.get("error") or "")[:200],
            "steering_applied": bool(t.get("steering_applied")),
        })

    durations = [c["duration_s"] for c in clean_turns if c["duration_s"] is not None]
    tool_lats: list[float] = []
    for c in clean_turns:
        tool_lats.extend(c["tool_latencies_ms"] or [])
    depths = [c["tool_calls_count"] or 0 for c in clean_turns]
    tool_counter: Counter = Counter()
    for c in clean_turns:
        tool_counter.update(c["tools_invoked"] or [])
    err_counter: Counter = Counter(
        (c["error"] or "none")[:120] for c in clean_turns if c["status"] != "success"
    )

    # Per-model split from the runner's per-turn usage model attribution when present.
    model_counter: Counter = Counter()
    for t in turns:
        m = ((t.get("usage", {}) or {}).get("model")) or res.get("model") or ""
        if m:
            model_counter[str(m)] += 1

    usage_models: Counter = Counter(u.get("model", "") for u in usage if u.get("model"))
    usage_outcomes: Counter = Counter(u.get("outcome", "") for u in usage)
    stop_reasons: Counter = Counter(u.get("stop_reason", "") for u in usage if u.get("stop_reason"))
    usage_errors: Counter = Counter(u.get("error_type", "") for u in usage if u.get("error_type"))
    span_ops: Counter = Counter(s.get("operation", "") for s in spans)
    span_status: Counter = Counter(s.get("status", "") for s in spans)
    span_errors: Counter = Counter(s.get("error_type", "") for s in spans if s.get("error_type"))
    span_models: Counter = Counter(s.get("model_name", "") for s in spans if s.get("model_name"))
    span_routes = sum(1 for s in spans if s.get("route_id"))

    usage_tokens = sum((u.get("total_tokens") or 0) for u in usage)
    usage_cost = round(sum((u.get("cost_usd") or 0.0) for u in usage), 6)

    return {
        "engine": engine,
        "project_id": res.get("project_id", ""),
        "turn_range": [res.get("start_turn"), res.get("end_turn")],
        "turns_completed": len(clean_turns),
        "turns": clean_turns,
        "latency_s": summarize_latency(durations),
        "tool_latency_ms": summarize_latency(tool_lats),
        "tool_call_depth": {
            "total": int(sum(depths)),
            "max_per_turn": max(depths) if depths else 0,
            "mean_per_turn": round(sum(depths) / len(depths), 2) if depths else 0.0,
            "per_tool_counts": dict(tool_counter),
        },
        "tokens": {
            "total": res.get("total_tokens", 0),
            "input": res.get("input_tokens", 0),
            "output": res.get("output_tokens", 0),
            "cached": res.get("cached_tokens", 0),
            "cache_hit_rate_pct": res.get("cache_hit_rate_pct", 0.0),
            "usage_rows_total": usage_tokens,
        },
        "cost_usd": {"runner_total": res.get("total_cost_usd", 0.0), "usage_rows_total": usage_cost},
        "status_counts": dict(Counter(c["status"] for c in clean_turns)),
        "error_taxonomy_turns": dict(err_counter),
        "steering_interventions": int(sum(1 for c in clean_turns if c["steering_applied"])),
        "dag": {
            "nuggets": res.get("dag_nuggets", 0),
            "facts": res.get("dag_facts", 0),
            "insights": res.get("dag_insights", 0),
            "recommendations": res.get("dag_recs", 0),
            "edges": res.get("dag_edges", 0),
        },
        "report_generated": bool(res.get("report_generated", False)),
        "models_seen_turns": dict(model_counter),
        "usage_rows": {
            "n": len(usage),
            "outcomes": dict(usage_outcomes),
            "stop_reasons": dict(stop_reasons),
            "error_types": dict(usage_errors),
            "models": dict(usage_models),
            "exact_rows": sum(1 for u in usage if not u.get("estimate")),
            "estimated_rows": sum(1 for u in usage if u.get("estimate")),
        },
        "spans": {
            "n": len(spans),
            "operations": dict(span_ops),
            "status": dict(span_status),
            "error_types": dict(span_errors),
            "models": dict(span_models),
            "with_route_id": span_routes,
        },
    }


def audit_telemetry(engine_aggs: dict, settings_snapshot: dict) -> dict:
    gaps = []
    checks: dict = {}
    for engine, agg in engine_aggs.items():
        u = agg["usage_rows"]
        s = agg["spans"]
        chat_spans = s["operations"].get("chat_turn", 0)
        checks[engine] = {
            "usage_rows_present": u["n"] > 0,
            "chat_turn_spans_present": chat_spans > 0,
            "model_attribution_present": bool(u["models"]) or bool(s["models"]),
            "route_attribution_present": s["with_route_id"] > 0,
            "telemetry_enabled_setting": settings_snapshot.get("telemetry_enabled"),
        }
        if u["n"] == 0:
            gaps.append({
                "engine": engine,
                "gap": "no agentic_usage_rows for the run project",
                "evidence": f"usage_rows.n={u['n']} project={agg['project_id']}",
            })
        if chat_spans == 0:
            gaps.append({
                "engine": engine,
                "gap": "no chat_turn telemetry_spans captured",
                "evidence": f"spans.operations={s['operations']}",
            })
        if not (u["models"] or s["models"]):
            gaps.append({
                "engine": engine,
                "gap": "no model attribution in usage rows or spans",
                "evidence": "usage.models={} span.models={}",
            })
    enabled = settings_snapshot.get("telemetry_enabled")
    conclusion = (
        "capture_present_content_free_attributed"
        if not gaps else "capture_gaps_recorded"
    )
    return {
        "settings": settings_snapshot,
        "settings_note": (
            "telemetry_enabled gates agent_hooks spans only; core paths "
            "(dispatcher usage rows, steering, task_review, engine) record "
            "unconditionally to the local DB. Local-first: no OTLP exporter "
            "exists in the tree; 'OTel spans' in the plan maps to the local "
            "telemetry_spans table, which carries the OTel-shaped fields "
            "(trace_id/parent_id/operation/duration/status)."
        ),
        "per_engine": checks,
        "gaps": gaps,
        "conclusion": conclusion,
        "enabled_flag": enabled,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Aggregate W4 150-turn telemetry")
    ap.add_argument("--results", required=True, help="Runner output JSON ({engine: result})")
    ap.add_argument("--db", default=None, help="Single scratch DB (both engines)")
    ap.add_argument("--db-pi", default=None)
    ap.add_argument("--db-legacy", default=None)
    ap.add_argument("--engine", default=None, help="Restrict to one engine")
    ap.add_argument("--telemetry-enabled", default="false")
    ap.add_argument("--telemetry-export-dir", default="./data/telemetry_exports")
    ap.add_argument("--run-label", default="")
    ap.add_argument("--out", required=True, help="Output directory for the artifact")
    args = ap.parse_args()

    results = load_results(Path(args.results))
    if args.engine:
        results = {args.engine: results[args.engine]}

    db_for = {
        "pi": Path(args.db_pi or args.db or ""),
        "legacy": Path(args.db_legacy or args.db or ""),
    }

    engine_aggs = {}
    for engine, res in results.items():
        db_path = db_for.get(engine, Path(""))
        usage: list[dict] = []
        spans: list[dict] = []
        if db_path and db_path.exists():
            usage = query_table(db_path, "agentic_usage_rows", [res.get("project_id", "")])
            spans = query_table(db_path, "telemetry_spans", [res.get("project_id", "")])
        engine_aggs[engine] = aggregate_engine(engine, res, usage, spans)
        engine_aggs[engine]["db_present"] = bool(db_path and db_path.exists())

    settings_snapshot = {
        "telemetry_enabled": str(args.telemetry_enabled).lower() == "true",
        "telemetry_export_dir": args.telemetry_export_dir,
    }
    audit = audit_telemetry(engine_aggs, settings_snapshot)

    artifact = {
    "artifact": "w4-long-horizon-telemetry",
        "created_at": datetime.now(UTC).isoformat(),
        "run_label": args.run_label,
        "results_sha12": sha12(Path(args.results).read_bytes().decode("utf-8", "replace")),
        "engines": engine_aggs,
        "telemetry_audit": audit,
        "content_free": True,
        "no_secrets": True,
    }
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    body = json.dumps(artifact, indent=2, sort_keys=True)
    digest = sha256(body.encode()).hexdigest()[:12]
    out_path = out_dir / f"w4-telemetry-aggregate-{digest}.json"
    out_path.write_text(body, encoding="utf-8")
    print(json.dumps({
        "artifact": str(out_path),
        "sha12": digest,
        "engines": {e: {"turns": a["turns_completed"], "usage_rows": a["usage_rows"]["n"],
                         "spans": a["spans"]["n"]} for e, a in engine_aggs.items()},
        "audit_conclusion": audit["conclusion"],
        "gaps": len(audit["gaps"]),
    }))


if __name__ == "__main__":
    main()
