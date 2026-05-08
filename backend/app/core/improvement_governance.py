"""System-wide improvement governance for Istara's self-evolving loops."""

from __future__ import annotations

from app.core.improvement_governance_evidence import ImprovementGovernanceEvidenceMixin
from app.core.improvement_governance_lifecycle import ImprovementGovernanceLifecycleMixin
from app.core.improvement_governance_policy import ImprovementPolicyMixin


class ImprovementGovernanceService(
    ImprovementGovernanceLifecycleMixin,
    ImprovementGovernanceEvidenceMixin,
    ImprovementPolicyMixin,
):
    """Create, evaluate, approve, apply, and revert improvement proposals."""

    pass


improvement_governance = ImprovementGovernanceService()

__all__ = ["ImprovementGovernanceService", "improvement_governance"]
