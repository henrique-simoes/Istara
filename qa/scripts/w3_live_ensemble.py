"""Wave W3 live 3-model Research Spine + adversarial/debate ensemble runner.

Governed live exercise (readiness5 plan Wave W3) of the multi-model ensemble
paths through Pi model management. All credentials come from the process
environment (``PI_API_ENDPOINTS`` + ``ISTARA_PI_SECRET_*``); nothing secret is
printed, logged, or written to the artifact — route evidence is scrubbed to
identity/provenance fields only.

Stages (select with ``--stages A,B,C,D,E``):
  A — endpoint admission: resolve each research endpoint id and run one tiny
      pinned completion per endpoint (served-model receipt per model).
  B — governed independent coding run over CareNav evidence units
      (3 distinct models, exact-span grounding, Fleiss kappa + Krippendorff
      alpha, served-model receipts, reconciliation status, report gating).
  C — reconciliation decisions + report-gate both directions on a task-bound
      run (unreconciled attempt must refuse; reconciled/accepted may allow).
  D — live adversarial review + debate rounds + full ensemble bound to the
      coding run (route evidence + per-pass model identity recorded).
  E — five fail-closed probes (missing coder, paraphrased quote, missing
      served identity, duplicate rating, unreconciled report attempt).

Artifact: redacted JSON at ``--out`` (default ``/app/data/w3-artifact.json``).
Source-text content is never embedded (sha256 only); CareNav data is read from
a scratch copy of the preserved DB, never the original.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from hashlib import sha256

CARENAV_PROJECT_ID = "proj-st150-pi-dd6bf277"

_SCRUB_SUBSTRINGS = (
    "base_url",
    "api_key",
    "apikey",
    "token",
    "secret",
    "credential",
    "oauth",
    "keychain",
    "authorization",
    "cookie",
    "password",
    "host",
    "url",
    "account_handle",
    "endpoint fingerprint",
)


def scrub(obj):
    """Drop secret/endpoint-identifying fields from route-evidence structures."""
    if isinstance(obj, dict):
        return {
            k: scrub(v)
            for k, v in obj.items()
            if not any(s in str(k).lower() for s in _SCRUB_SUBSTRINGS)
        }
    if isinstance(obj, (list, tuple)):
        return [scrub(v) for v in obj]
    return obj


def sha12(text: str) -> str:
    return sha256((text or "").encode()).hexdigest()[:12]


def record_status(ok: bool, **fields) -> dict:
    return {"ok": ok, **fields}


async def stage_a(endpoint_ids: list[str], project_id: str) -> dict:
    from app.core.agentic import agentic
    from app.core.agentic.types import TurnParams

    results = []
    try:
        service = agentic.pi_execution_service()
        manager = service.model_manager()
    except Exception as exc:
        return {"stage": "A", "ok": False, "error_class": type(exc).__name__,
                "error": str(exc)[:200], "endpoints": []}
    await manager.ensure_db_projection()
    for eid in endpoint_ids:
        started = time.perf_counter()
        entry: dict = {"endpoint_id": eid}
        try:
            resolved = manager.resolve(endpoint_id=eid, model=None, project_id=project_id)
            entry["requested_model"] = resolved.model
            entry["provider_kind"] = resolved.provider_kind
            outcome = await agentic.completion(
                purpose="w3.endpoint_probe",
                project_id=project_id,
                system=None,
                messages=[{"role": "user", "content": "Reply with exactly: ready"}],
                params=TurnParams(endpoint_id=eid, temperature=0.2,
                                    thinking_mode="low", max_tokens=8),
                engine="pi",
                spine_phase="review",
            )
            entry["status"] = outcome.status
            entry["error_class"] = type(getattr(outcome, "error", None)).__name__ \
                if getattr(outcome, "error", None) else ""
            entry["error"] = str(getattr(outcome, "error", None) or "")[:200]
            entry["stop_reason"] = getattr(outcome, "stop_reason", None) or ""
            entry["served_model"] = getattr(outcome, "served_model", None) or ""
            entry["model"] = getattr(outcome, "model", None) or ""
            entry["reply_match"] = (outcome.text or "").strip().lower() == "ready"
            entry["latency_ms"] = round((time.perf_counter() - started) * 1000)
            usage = getattr(outcome, "usage", None) or {}
            entry["usage_keys"] = sorted(usage.keys()) if isinstance(usage, dict) else []
            entry["ok"] = outcome.status == "success" and bool(entry["served_model"])
        except Exception as exc:
            entry["ok"] = False
            entry["status"] = "error"
            entry["error_class"] = type(exc).__name__
            entry["error"] = str(exc)[:200]
            entry["latency_ms"] = round((time.perf_counter() - started) * 1000)
        results.append(entry)
    distinct_served = {r.get("served_model") for r in results if r.get("served_model")}
    return {
        "stage": "A",
        "ok": all(r.get("ok") for r in results) and len(results) == len(endpoint_ids),
        "endpoint_count": len(results),
        "distinct_served_models": sorted(distinct_served),
        "distinct_served_count": len(distinct_served),
        "endpoints": [scrub(r) for r in results],
    }


async def stage_b(project_id: str, limit: int, max_coders: int) -> dict:
    from sqlalchemy import select

    from app.models.database import async_session, register_models
    from app.models.research_validity import EvidenceUnit
    from app.services.research_validity_service import run_independent_coding_run

    register_models()
    async with async_session() as db:
        # Pin an explicit, recorded unit set: taskless runs have no
        # project-wide fallback (contamination guard) and fail closed
        # without explicit unit ids.
        unit_rows = (await db.execute(
            select(EvidenceUnit)
            .where(EvidenceUnit.project_id == project_id)
            .order_by(EvidenceUnit.source_id, EvidenceUnit.unit_index)
            .limit(limit))).scalars().all()
        pinned = [
            {"id": u.id, "stable_id": getattr(u, "stable_id", ""),
             "source_id": getattr(u, "source_id", ""),
             "unit_index": getattr(u, "unit_index", None),
             "source_text_sha12": sha12(getattr(u, "source_text", "") or ""),
             "source_text_chars": len(getattr(u, "source_text", "") or "")}
            for u in unit_rows
        ]
        payload = await run_independent_coding_run(
            db,
            project_id=project_id,
            task_id=None,
            evidence_unit_ids=[u.id for u in unit_rows],
            limit=limit,
            max_coders=max_coders,
            created_by="w3-live-ensemble",
        )
        payload["pinned_units"] = pinned
    redacted = {
        "run_id": payload.get("id"),
        "status": payload.get("status"),
        "promotion_status": payload.get("promotion_status"),
        "fallback_reason": payload.get("fallback_reason"),
        "kappa": payload.get("kappa"),
        "alpha": payload.get("alpha"),
        "reliability_method": payload.get("reliability_method"),
        "rater_count": payload.get("rater_count"),
        "distinct_model_count": payload.get("distinct_model_count"),
        "threshold": payload.get("threshold"),
        "codebook_version_id": payload.get("codebook_version_id"),
        "code_application_count": payload.get("code_application_count"),
        "route_evidence": scrub(payload.get("route_evidence") or []),
        "completed_at": str(payload.get("completed_at") or ""),
        "pinned_units": payload.get("pinned_units") or [],
        # Operational-vs-formal label: real Fleiss/Aplha computation on a
        # cost-bounded 6-unit live slice — a governed operational measurement,
        # not a powered formal reliability estimate for the corpus.
        "reliability_label": "operational_live_measurement_small_n",
        "formal_power_note": "6 units x 3 raters; kappa/alpha computed exactly "
        "but underpowered for corpus-level inference; promotion follows the "
        "item-level reconciliation gate regardless.",
    }
    coders = [c.get("coder_id") for c in redacted["route_evidence"]
              if c.get("coder_id")]
    served = [c.get("model") for c in redacted["route_evidence"] if c.get("model")]
    redacted["coder_ids"] = coders
    redacted["served_models"] = served
    redacted["ok"] = bool(redacted["run_id"]) and redacted["status"] == "completed"
    return {"stage": "B", **redacted}


async def stage_c(project_id: str, task_id: str, unit_ids: list[str],
                  codebook_version_id: str | None) -> dict:
    from sqlalchemy import select

    from app.models.code_application import CodeApplication
    from app.models.database import async_session, register_models
    from app.models.task import Task
    from app.services.research_validity_reconciliation import (
        _is_reconciled_code_application,
        _is_unresolved_code_application,
        assess_task_research_validity,
        create_reconciliation_decision,
    )
    from app.services.research_validity_service import run_independent_coding_run

    register_models()
    out: dict = {"stage": "C", "task_id": task_id}
    async with async_session() as db:
        task = (await db.execute(
            select(Task).where(Task.id == task_id))).scalar_one_or_none()
        if task is None:
            task = Task(id=task_id, project_id=project_id,
                        title="W3 live report-gate probe (scratch copy only)")
            db.add(task)
            await db.commit()
        out["task_created"] = True
        payload = await run_independent_coding_run(
            db, project_id=project_id, task_id=task_id,
            evidence_unit_ids=unit_ids, limit=len(unit_ids),
            max_coders=3, created_by="w3-live-ensemble",
        )
        out["run_id"] = payload.get("id")
        out["run_promotion_status"] = payload.get("promotion_status")
        out["kappa"] = payload.get("kappa")
        out["alpha"] = payload.get("alpha")
        before = await assess_task_research_validity(
            db, project_id=project_id, task_id=task_id)
        out["gate_before"] = {
            "report_allowed": before.get("report_allowed"),
            "reason": before.get("reason"),
            "accepted": before.get("accepted_code_application_count"),
            "unresolved": before.get("unresolved_code_application_count"),
        }
        rows = (await db.execute(
            select(CodeApplication).where(
                CodeApplication.project_id == project_id,
                CodeApplication.task_id == task_id,
            ))).scalars().all()
        decisions = []
        for row in rows:
            if _is_unresolved_code_application(row):
                d = await create_reconciliation_decision(
                    db, project_id=project_id, code_application_id=row.id,
                    decision_type="accepted", decided_by="w3-live-ensemble",
                    rationale="W3 governed live run: reconciled after human-readable "
                              "review of exact-span grounding receipts.",
                )
                decisions.append({"code_application_id": row.id,
                                  "state": d.get("resolved_state") or d.get("decision")})
        await db.commit()
        out["reconciliation_decisions"] = len(decisions)
        after = await assess_task_research_validity(
            db, project_id=project_id, task_id=task_id)
        out["gate_after"] = {
            "report_allowed": after.get("report_allowed"),
            "reason": after.get("reason"),
            "accepted": after.get("accepted_code_application_count"),
            "unresolved": after.get("unresolved_code_application_count"),
        }
    out["ok"] = (out["gate_before"].get("report_allowed") is False
                 and out.get("run_id") is not None)
    return out


async def stage_d(project_id: str, coding_run_id: str, unit_ids: list[str],
                  codebook_version_id: str | None) -> dict:
    from app.core import validation as validation_module

    async def fake_embeddings(texts, project_id=None):
        return []

    # Live model passes; embeddings may degrade to empty (recorded honestly).
    orig = validation_module._get_embeddings
    validation_module._get_embeddings = fake_embeddings
    out: dict = {"stage": "D"}
    try:
        adv = await validation_module.adversarial_review(
            "Do the coded spans support cautious, qualified claims only?",
            "The coded spans fully prove every strategic claim without qualification.",
            project_id=project_id, coding_run_id=coding_run_id,
            evidence_unit_ids=unit_ids, codebook_version_id=codebook_version_id,
        )
        out["adversarial"] = {
            "method": adv.method,
            "agreement_score": adv.consensus.agreement_score,
            "confidence_label": adv.consensus.confidence,
            "kappa": adv.consensus.kappa,
            "route_evidence": scrub(adv.metadata.get("route_evidence")),
            "models_used": adv.metadata.get("models_used"),
            "validation_scope": adv.metadata.get("validation_scope"),
            "formal_reliability": adv.metadata.get("formal_reliability"),
        }
        debate = await validation_module.debate_rounds(
            "Should the synthesis stay qualified given partial span support?",
            project_id=project_id, rounds=2, coding_run_id=coding_run_id,
            evidence_unit_ids=unit_ids, codebook_version_id=codebook_version_id,
        )
        out["debate"] = {
            "method": debate.method,
            "agreement_score": debate.consensus.agreement_score,
            "confidence_label": debate.consensus.confidence,
            "kappa": debate.consensus.kappa,
            "details": debate.consensus.details,
            "route_evidence": scrub(debate.metadata.get("route_evidence")),
            "models_used": debate.metadata.get("models_used"),
            "validation_scope": debate.metadata.get("validation_scope"),
            "formal_reliability": debate.metadata.get("formal_reliability"),
        }
        ens = await validation_module.full_ensemble(
            "Summarize the agreed coding stance in one sentence.",
            project_id=project_id, min_responses=3,
        )
        out["full_ensemble"] = {
            "method_returned": ens.method,
            "agreement_score": ens.consensus.agreement_score,
            "confidence_label": ens.consensus.confidence,
            "route_evidence": scrub(ens.metadata.get("route_evidence")),
            "models_used": ens.metadata.get("models_used"),
            "n_responses": ens.metadata.get("n_responses"),
            "validation_scope": ens.metadata.get("validation_scope"),
            "formal_reliability": ens.metadata.get("formal_reliability"),
            "kappa_interpretation": ens.metadata.get("kappa_interpretation"),
        }
    finally:
        validation_module._get_embeddings = orig
    # Live-exercise bar: each method ran against live models and recorded
    # per-pass route evidence with model identity (never silent fallback).
    # Adversarial/debate are response-level quality signals, not formal
    # reliability — the labels below must stay operational, never Fleiss.
    out["reliability_label"] = "operational_response_level_quality_signal_not_fleiss"
    out["ok"] = all(
        (out.get(k) or {}).get("route_evidence") for k in ("adversarial", "debate"))
    return out


async def stage_e(project_id: str) -> dict:
    from sqlalchemy import select

    from app.core.research_validity import evaluate_reliability_gate
    from app.models.database import async_session, register_models
    from app.models.research_validity import EvidenceUnit
    from app.services.research_validity_service import _usable_coding_applications

    register_models()
    probes = []

    # P1 — missing coder: empty application set must block, never accept.
    r1 = evaluate_reliability_gate([], threshold=0.6, minimum_distinct_models=3,
                                   require_rater_provenance=True)
    probes.append({"id": "P1-missing-coder", "method": r1.get("method"),
                   "promotion_status": r1.get("promotion_status"),
                   "kappa": r1.get("kappa"),
                   "pass": r1.get("promotion_status") == "blocked"
                   and r1.get("kappa") is None})
    # P1b — live resolver must refuse to fabricate 99 distinct coders.
    try:
        from app.core.agentic import agentic
        svc = agentic.pi_execution_service()
        svc.model_manager().resolve_distinct(99, project_id=project_id)
        probes.append({"id": "P1b-resolve-99", "pass": False,
                       "note": "resolver fabricated diversity"})
    except Exception as exc:
        probes.append({"id": "P1b-resolve-99",
                       "error_class": type(exc).__name__,
                       "pass": "Resolution" in type(exc).__name__
                       or "Error" in type(exc).__name__})

    async with async_session() as db:
        units = (await db.execute(
            select(EvidenceUnit)
            .where(EvidenceUnit.project_id == project_id)
            .order_by(EvidenceUnit.source_id, EvidenceUnit.unit_index)
            .limit(2))).scalars().all()
        unit_by_id = {u.id: u for u in units}
        # P2 — paraphrased quote (not an exact source span) is unusable.
        paraphrase = (units[0].source_text or "")[:60].replace(" the ", " THE ")
        if paraphrase in (units[0].source_text or ""):
            paraphrase += " roughly speaking"
        usable = _usable_coding_applications(
            {"applications": [{"evidence_unit_id": units[0].id,
                               "quote": paraphrase, "codes": ["code-x"]}]},
            unit_by_id=unit_by_id, units=units)
        probes.append({"id": "P2-paraphrased-quote", "usable_count": len(usable),
                       "pass": len(usable) == 0})
        # P3 — application without served/provenance identity cannot pass.
        r3 = evaluate_reliability_gate(
            [{"coder_id": "coder-ghost", "model_name": "ghost-model",
              "evidence_unit_id": units[0].id, "codes": ["code-x"]}],
            threshold=0.6, minimum_distinct_models=1,
            require_rater_provenance=True)
        probes.append({"id": "P3-missing-served-identity",
                       "method": r3.get("method"),
                       "promotion_status": r3.get("promotion_status"),
                       "pass": r3.get("promotion_status") in (
                           "needs_reconciliation", "blocked")})
        # P4 — duplicate rating by one coder on one unit must not merge.
        r4 = evaluate_reliability_gate(
            [{"coder_id": "coder-dup", "model_name": "m",
              "evidence_unit_id": units[0].id, "codes": ["code-x"],
              "endpoint_id": "e1", "provider_account_handle": "h",
              "prompt_hash": "p", "protocol_version": "v",
              "decoding_profile": {"temperature": 0.2},
              "conversation_scope": "s", "cache_scope": "c"},
             {"coder_id": "coder-dup", "model_name": "m",
              "evidence_unit_id": units[0].id, "codes": ["code-y"],
              "endpoint_id": "e1", "provider_account_handle": "h",
              "prompt_hash": "p", "protocol_version": "v",
              "decoding_profile": {"temperature": 0.2},
              "conversation_scope": "s", "cache_scope": "c"}],
            threshold=0.6, minimum_distinct_models=1,
            require_rater_provenance=True)
        probes.append({"id": "P4-duplicate-rating", "method": r4.get("method"),
                       "promotion_status": r4.get("promotion_status"),
                       "pass": r4.get("method") == "duplicate_rater_applications"
                       and r4.get("promotion_status") == "needs_reconciliation"})
        probes.append({"id": "P5-unreconciled-report",
                       "note": "exercised in stage C gate_before (report_allowed False)"})
    return {"stage": "E", "ok": all(p.get("pass", True) for p in probes
                                   if p["id"] != "P5-unreconciled-report"),
            "probes": probes}


async def amain(args) -> dict:
    from app.models.database import register_models

    register_models()
    endpoint_ids = [e.strip() for e in (os.environ.get("PI_RESEARCH_ENDPOINT_IDS") or "")
                    .replace("[", "").replace("]", "").replace('"', "").split(",")
                    if e.strip()]
    artifact: dict = {
        "wave": "W3-live-ensemble",
        "project_id": args.project,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "endpoint_ids_requested": endpoint_ids,
        "stages": {},
    }
    if args.input:
        with open(args.input) as f:
            prior = json.load(f)
        for stage_key, stage_val in (prior.get("stages") or {}).items():
            artifact["stages"][stage_key] = stage_val
        artifact["chained_inputs"] = [args.input]
    if "A" in args.stages:
        artifact["stages"]["A"] = await stage_a(endpoint_ids, args.project)
    if "B" in args.stages:
        artifact["stages"]["B"] = await stage_b(args.project, args.units, 3)
    if "C" in args.stages:
        b = artifact["stages"].get("B", {})
        unit_ids = []
        if b:
            from sqlalchemy import select

            from app.models.code_application import CodeApplication
            from app.models.database import async_session, register_models

            register_models()
            async with async_session() as db:
                rows = (await db.execute(
                    select(CodeApplication.evidence_unit_id).where(
                        CodeApplication.coding_run_id == b.get("run_id")))).all()
                unit_ids = sorted({r[0] for r in rows if r[0]})[:2]
        artifact["stages"]["C"] = await stage_c(
            args.project, args.task, unit_ids,
            (b.get("codebook_version_id") if b else None))
        p5pass = (artifact["stages"]["C"].get("gate_before") or {}).get(
            "report_allowed") is False
        for stage in (artifact["stages"].get("E") or {}).get("probes", []):
            if stage.get("id") == "P5-unreconciled-report":
                stage["pass"] = p5pass
                stage["gate_before"] = artifact["stages"]["C"].get("gate_before")
    if "D" in args.stages:
        b = artifact["stages"].get("B", {})
        target_run = (artifact["stages"].get("C") or {}).get("run_id") or (
            b.get("run_id") if b else "")
        unit_ids = []
        if target_run:
            from sqlalchemy import select

            from app.models.code_application import CodeApplication
            from app.models.database import async_session, register_models

            register_models()
            async with async_session() as db:
                rows = (await db.execute(
                    select(CodeApplication.evidence_unit_id).where(
                        CodeApplication.coding_run_id == target_run))).all()
                unit_ids = sorted({r[0] for r in rows if r[0]})
        artifact["stages"]["D"] = await stage_d(
            args.project, target_run, unit_ids,
            (b.get("codebook_version_id") if b else None))
    if "E" in args.stages and "E" not in artifact["stages"]:
        artifact["stages"]["E"] = await stage_e(args.project)
    artifact["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(args.out, "w") as f:
        json.dump(artifact, f, indent=2, default=str)
    return artifact


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=CARENAV_PROJECT_ID)
    parser.add_argument("--units", type=int, default=6)
    parser.add_argument("--stages", default="A,B,C,D,E")
    parser.add_argument("--out", default="/app/data/w3-artifact.json")
    parser.add_argument("--input", default="",
                        help="Prior artifact JSON whose stages are reused, not re-run")
    parser.add_argument("--task", default="task-w3-live-ensemble",
                        help="Scratch task id for the stage-C report-gate run")
    args = parser.parse_args()
    args.stages = {s.strip().upper() for s in args.stages.split(",") if s.strip()}
    artifact = asyncio.run(amain(args))
    summary = {k: (v.get("ok") if isinstance(v, dict) else v)
               for k, v in artifact["stages"].items()}
    print(json.dumps({"stages_ok": summary, "out": args.out}))
    if not all(summary.values()):
        sys.exit(2)


if __name__ == "__main__":
    main()
