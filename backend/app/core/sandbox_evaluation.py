"""Deterministic sandbox checks for governed Istara mutations."""

from __future__ import annotations

from typing import Any

from app.core.improvement_governance_contracts import clean_payload, normalize_surfaces, utcnow

BEHAVIORAL_SURFACES = {"prompts", "configs", "skills", "agents", "ui", "orchestration"}
ADMIN_SURFACES = {
    "backend_code",
    "integrations",
    "mcp",
    "compute",
    "security",
    "connection_strings",
}
REASONING_SURFACES = {"memory", "reasoning"}


class SandboxEvaluationService:
    """Runs cheap, local preflight checks before a proposal is applied."""

    def evaluate_proposal(self, proposal: Any, *, apply_evidence: dict | None = None) -> dict:
        evidence = proposal.get_evidence() if hasattr(proposal, "get_evidence") else []
        evaluation_runs = (
            proposal.get_evaluation_runs() if hasattr(proposal, "get_evaluation_runs") else []
        )
        reasoning_memory_ids = (
            proposal.get_reasoning_memory_ids()
            if hasattr(proposal, "get_reasoning_memory_ids")
            else []
        )
        return self.evaluate_payload(
            proposal_id=str(getattr(proposal, "id", "")),
            status=str(getattr(proposal, "status", "")),
            source_system=str(getattr(proposal, "source_system", "")),
            affected_surfaces=proposal.get_affected_surfaces()
            if hasattr(proposal, "get_affected_surfaces")
            else [],
            risk_level=str(getattr(proposal, "risk_level", "")),
            approval_policy=str(getattr(proposal, "approval_policy", "")),
            requires_human_approval=bool(getattr(proposal, "requires_human_approval", False)),
            proposed_change=proposal.get_proposed_change()
            if hasattr(proposal, "get_proposed_change")
            else {},
            rollback_plan=proposal.get_rollback_plan()
            if hasattr(proposal, "get_rollback_plan")
            else {},
            evidence=evidence,
            evaluation_runs=evaluation_runs,
            reasoning_memory_ids=reasoning_memory_ids,
            metrics_before=proposal.get_metrics_before()
            if hasattr(proposal, "get_metrics_before")
            else {},
            metrics_after=proposal.get_metrics_after()
            if hasattr(proposal, "get_metrics_after")
            else {},
            apply_evidence=apply_evidence,
        )

    def evaluate_payload(
        self,
        *,
        proposal_id: str = "",
        status: str = "",
        source_system: str = "",
        affected_surfaces: list[str] | None = None,
        risk_level: str = "",
        approval_policy: str = "",
        requires_human_approval: bool = False,
        proposed_change: dict | None = None,
        rollback_plan: dict | None = None,
        evidence: list | None = None,
        evaluation_runs: list | None = None,
        reasoning_memory_ids: list[str] | None = None,
        metrics_before: dict | None = None,
        metrics_after: dict | None = None,
        apply_evidence: dict | None = None,
    ) -> dict:
        surfaces = normalize_surfaces(affected_surfaces)
        proposed = clean_payload(proposed_change or {})
        rollback = clean_payload(rollback_plan or {})
        events = clean_payload(evidence or [])
        runs = clean_payload(evaluation_runs or [])
        before = clean_payload(metrics_before or {})
        after = clean_payload(metrics_after or {})
        apply_payload = clean_payload(apply_evidence or {})
        checks: list[dict] = []

        def add_check(
            check_id: str, passed: bool, severity: str, message: str, detail: Any = None
        ) -> None:
            checks.append(
                {
                    "id": check_id,
                    "passed": passed,
                    "severity": severity,
                    "message": message,
                    "detail": clean_payload(detail),
                }
            )

        has_behavioral_surface = bool(set(surfaces) & BEHAVIORAL_SURFACES)
        has_admin_surface = bool(set(surfaces) & ADMIN_SURFACES)
        has_reasoning_surface = bool(set(surfaces) & REASONING_SURFACES)
        rollback_text = (
            " ".join(str(value).lower() for value in rollback.values())
            if isinstance(rollback, dict)
            else ""
        )
        has_evaluation_evidence = bool(
            runs or before or after or apply_payload.get("command") or apply_payload.get("tests")
        )
        has_uncertainty_signal = any(
            key in str({"before": before, "after": after, "events": events}).lower()
            for key in ("stddev", "confidence_interval", "ci95", "p_value", "sample", "percentile")
        )

        add_check(
            "rollback_present",
            bool(rollback),
            "blocker",
            "A rollback plan is required before any governed mutation can be applied.",
        )
        add_check(
            "rollback_actionable",
            bool(
                rollback_text
                and any(
                    token in rollback_text
                    for token in (
                        "restore",
                        "revert",
                        "disable",
                        "delete",
                        "remove",
                        "quarantine",
                        "revoke",
                    )
                )
            ),
            "warning",
            "Rollback plan should identify a concrete restore, revert, disable, revoke, or quarantine action.",
            rollback,
        )
        add_check(
            "human_approval_state",
            not requires_human_approval or status == "approved",
            "blocker",
            "Human-gated proposals must be approved before apply.",
            {"status": status, "approval_policy": approval_policy},
        )
        add_check(
            "evaluation_evidence",
            not (has_behavioral_surface or has_admin_surface) or has_evaluation_evidence,
            "warning",
            "Behavioral and infrastructure mutations should include test, metric, or command evidence.",
            {"evaluation_runs": len(runs), "apply_evidence_keys": sorted(apply_payload.keys())},
        )
        add_check(
            "statistical_rigor",
            "compute" not in surfaces and "orchestration" not in surfaces or has_uncertainty_signal,
            "warning",
            "Compute and orchestration changes should carry uncertainty, sample, or percentile evidence.",
        )
        add_check(
            "reasoning_trace",
            not has_reasoning_surface or bool(reasoning_memory_ids),
            "warning",
            "Reasoning-affecting changes should link the ReasoningBank memories that informed them.",
            reasoning_memory_ids,
        )
        add_check(
            "secret_redaction",
            "[REDACTED]"
            not in str({"proposed": proposed, "rollback": rollback, "apply": apply_payload}),
            "warning",
            "Proposal payload contains redacted secret material; verify the source integration is not emitting credentials.",
        )

        blockers = [
            check for check in checks if check["severity"] == "blocker" and not check["passed"]
        ]
        warnings = [
            check for check in checks if check["severity"] == "warning" and not check["passed"]
        ]
        return {
            "event": "sandbox_evaluation",
            "proposal_id": proposal_id,
            "source_system": source_system,
            "risk_level": risk_level,
            "affected_surfaces": surfaces,
            "passed": not blockers,
            "blockers": blockers,
            "warnings": warnings,
            "checks": checks,
            "evaluated_at": utcnow().isoformat(),
        }


sandbox_evaluation = SandboxEvaluationService()
