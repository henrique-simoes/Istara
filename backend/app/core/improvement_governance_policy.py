"""Policy and feature-contract logic for governed self-improvement."""

from __future__ import annotations

from copy import deepcopy

from app.core.improvement_governance_contracts import (
    FEATURE_CONTRACT_MATRIX,
    POLICY,
    RISK,
    SURFACES,
    clean_payload,
    clean_string,
    normalize_surfaces,
)


class ImprovementPolicyMixin:
    """Classifies mutation risk and exposes the system-wide evidence matrix."""

    def classify_policy(
        self,
        *,
        affected_surfaces: list[str] | None = None,
        source_system: str = "manual",
        risk_level: str | None = None,
        proposed_change: dict | None = None,
    ) -> dict:
        surfaces = set(normalize_surfaces(affected_surfaces))
        normalized_risk = (risk_level or self.infer_risk_level(list(surfaces))).lower()
        if normalized_risk not in set(RISK.values()):
            normalized_risk = RISK["medium"]

        if surfaces <= SURFACES["auto"] and normalized_risk == RISK["low"]:
            policy = POLICY["auto"]
        elif surfaces & SURFACES["admin"] or normalized_risk in {RISK["high"], RISK["critical"]}:
            policy = POLICY["admin"]
        elif surfaces & SURFACES["behavior"]:
            policy = POLICY["approval"]
        else:
            policy = POLICY["approval"]

        return {
            "source_system": clean_string(source_system, max_chars=60) or "manual",
            "affected_surfaces": sorted(surfaces),
            "risk_level": normalized_risk,
            "approval_policy": policy,
            "requires_human_approval": policy != POLICY["auto"],
            "auto_apply_allowed": policy == POLICY["auto"],
            "behavioral_change": bool(surfaces & SURFACES["behavior"]),
            "proposed_change": clean_payload(proposed_change or {}),
        }

    def infer_risk_level(self, affected_surfaces: list[str]) -> str:
        surfaces = set(normalize_surfaces(affected_surfaces))
        if surfaces & {"backend_code", "security", "connection_strings"}:
            return RISK["critical"]
        if surfaces & {"integrations", "mcp", "compute"}:
            return RISK["high"]
        if surfaces & {"prompts", "configs", "skills", "agents", "ui", "orchestration"}:
            return RISK["medium"]
        return RISK["low"]

    def feature_contract_matrix(self) -> list[dict]:
        return deepcopy(FEATURE_CONTRACT_MATRIX)
