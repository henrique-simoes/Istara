#!/usr/bin/env python3
"""Fast production rehearsal for Istara's governed agentic contract."""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def record(
    checks: list[dict], name: str, passed: bool, detail: dict | None = None
) -> None:
    checks.append({"name": name, "passed": passed, "detail": detail or {}})


def rehearse() -> dict:
    checks: list[dict] = []

    from app.core.compute_capacity import compute_capacity_envelope
    from app.core.compute_registry import ComputeNode
    from app.core.improvement_governance import improvement_governance
    from app.core.sandbox_evaluation import sandbox_evaluation
    from app.main import app

    # FastAPI >= 0.118 defers include_router into lazy _IncludedRouter
    # wrappers whose .path is "" until materialized. Derive HTTP routes from
    # the OpenAPI schema (forces materialization) and keep WebSocket routes
    # from the raw table.
    from app.core.route_introspection import iter_route_paths

    actual_routes = iter_route_paths(app)
    feature_names = {
        item["feature"] for item in improvement_governance.feature_contract_matrix()
    }
    required_features = {
        "interviews_audio_upload_transcription_tagging_documents",
        "memento_skills_and_agent_creation",
        "hyperagent_meta_tuning",
        "dgmh_archive_evolution",
        "karpathy_autoresearch",
        "reasoning_bank",
        "ensemble_model_and_llm_orchestration",
        "pooled_compute_connection_strings",
        "desktop_tray_installation",
    }
    record(
        checks,
        "feature_contract_matrix_complete",
        required_features <= feature_names,
        {"missing": sorted(required_features - feature_names)},
    )

    agentic_contract_path = ROOT / "tests" / "agentic_eval_contract.json"
    required_agentic_contracts = {
        "autoresearch",
        "reasoning_bank",
        "memento_skills_and_agent_creation",
        "hyperagent_meta_tuning",
        "dgmh_archive_evolution",
        "ensemble_llm_orchestration",
        "tool_calling_react",
        "acceptance_ui_simulation",
    }
    if agentic_contract_path.exists():
        agentic_manifest = json.loads(agentic_contract_path.read_text(encoding="utf-8"))
        agentic_contracts = {
            contract.get("id") for contract in agentic_manifest.get("contracts", [])
        }
    else:
        agentic_contracts = set()
    record(
        checks,
        "agentic_eval_contract_manifest_complete",
        required_agentic_contracts <= agentic_contracts,
        {"missing": sorted(required_agentic_contracts - agentic_contracts)},
    )

    sandbox = sandbox_evaluation.evaluate_payload(
        proposal_id="rehearsal",
        status="approved",
        source_system="rehearsal",
        affected_surfaces=["skills", "prompts"],
        risk_level="medium",
        approval_policy="approval_required",
        requires_human_approval=True,
        proposed_change={"prompt": "tighten bilingual transcription validation"},
        rollback_plan={"strategy": "restore previous prompt"},
        apply_evidence={"tests": "production_rehearsal"},
    )
    record(
        checks,
        "sandbox_allows_approved_rollback_mutation",
        sandbox["passed"] is True,
        {"blockers": sandbox["blockers"], "warnings": sandbox["warnings"]},
    )

    sandbox_blocked = sandbox_evaluation.evaluate_payload(
        proposal_id="rehearsal-blocked",
        status="proposed",
        source_system="rehearsal",
        affected_surfaces=["backend_code"],
        risk_level="critical",
        approval_policy="admin_required",
        requires_human_approval=True,
        proposed_change={"module": "backend/app/core/agent.py"},
        rollback_plan={},
    )
    record(
        checks,
        "sandbox_blocks_unapproved_missing_rollback",
        sandbox_blocked["passed"] is False and len(sandbox_blocked["blockers"]) >= 2,
        {"blockers": sandbox_blocked["blockers"]},
    )

    nodes = [
        ComputeNode(
            node_id="rehearsal-local",
            name="Rehearsal Local",
            host="http://localhost:1234",
            source="local",
            provider_type="lmstudio",
            is_healthy=True,
            active_requests=1,
            max_active_requests=4,
            cpu_load_pct=70,
        ),
        ComputeNode(
            node_id="rehearsal-relay",
            name="Rehearsal Relay",
            host="",
            source="relay",
            provider_type="ollama",
            is_healthy=True,
            active_requests=2,
            max_active_requests=2,
            cpu_load_pct=50,
        ),
    ]
    envelope = compute_capacity_envelope(nodes)
    record(
        checks,
        "compute_capacity_envelope_reports_slots",
        envelope["request_slots_total"] == 6
        and envelope["request_slots_available"] == 3,
        envelope,
    )

    frontend_files = [
        ROOT / "frontend/src/components/settings/GovernedEvolutionView.tsx",
        ROOT / "frontend/src/lib/improvementGovernanceApi.ts",
        ROOT / "frontend/src/stores/computeStore.ts",
    ]
    record(
        checks,
        "frontend_governed_evolution_surface_present",
        all(path.exists() for path in frontend_files),
        {"files": [str(path.relative_to(ROOT)) for path in frontend_files]},
    )

    install_files = [
        ROOT / "scripts/install.sh",
        ROOT / "scripts/install-istara.sh",
        ROOT / "frontend/package.json",
        ROOT / "desktop/package.json",
        ROOT / "desktop/src-tauri/Cargo.toml",
    ]
    record(
        checks,
        "installation_manifests_present",
        all(path.exists() for path in install_files),
        {"files": [str(path.relative_to(ROOT)) for path in install_files]},
    )

    backend_requirements = (ROOT / "backend/requirements.txt").read_text(
        encoding="utf-8"
    )
    installer = (ROOT / "scripts/install-istara.sh").read_text(encoding="utf-8")
    required_dependency_markers = ["webauthn", "openai-whisper", "pydub"]
    missing_dependency_markers = [
        marker
        for marker in required_dependency_markers
        if marker not in backend_requirements
    ]
    ffmpeg_managed = "ensure_ffmpeg" in installer and "ffmpeg" in installer
    record(
        checks,
        "production_dependency_manifests_cover_security_and_audio",
        not missing_dependency_markers and ffmpeg_managed,
        {
            "missing_requirements": missing_dependency_markers,
            "ffmpeg_managed": ffmpeg_managed,
        },
    )

    passed = all(check["passed"] for check in checks)
    return {"passed": passed, "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Emit JSON only.")
    args = parser.parse_args()
    if args.json:
        with contextlib.redirect_stdout(sys.stderr):
            result = rehearse()
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        result = rehearse()
        for check in result["checks"]:
            status = "PASS" if check["passed"] else "FAIL"
            print(f"{status} {check['name']}")
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
