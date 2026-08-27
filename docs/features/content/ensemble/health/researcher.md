---
stable_id: ensemble.health
title: Ensemble Health
ui_path: Ensemble Health
audience: researcher
status: needs-verification
related_features: ["quality.dashboard", "compute.pool"]
related_glossary: ["fleiss-kappa"]
code_references: ["frontend/src/components/common/EnsembleHealthView.tsx", "backend/app/core/consensus.py", "backend/app/core/validation.py", "backend/app/core/validation_executor.py", "backend/app/services/research_validity_service.py", "backend/app/core/agentic/dispatcher.py"]
api_references: ["backend/app/api/routes/metrics.py"]
test_references: ["tests/pi_production/test_w1_dispatcher_authority.py", "tests/pi_production/test_w7_validation.py", "tests/test_validation_project_scope.py", "tests/test_research_validity_contract.py", "tests/test_metrics.py"]
last_verified: 2026-07-22
compass: CF-SPEC-8 / FIX-pi-full-20260720-w7-REVIEW-r1-docs; CF-SPEC-53 / CF-657
---

# Ensemble Health

## What It Does

Ensemble Health surfaces health and consensus signals for Istara's multi-model or multi-agent ensemble behavior.

## Why It Exists

Ensemble Health exists so the work represented by Ensemble Health has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Ensemble Health
- Navigation group: Secondary
- Primary component: `EnsembleHealthView`

## How UX Researchers Use It

- Open Ensemble Health from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with ensemble health in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Ensemble Health when the current research task needs ensemble health.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: quality.dashboard, compute.pool.

## How Validation Confidence Is Established

- W7's dual-run, full-ensemble, Self-MoA, adversarial review, debate, and structured-judge call sites now use the shared dispatcher unconditionally. The dispatcher resolves the selected engine; a legacy selection remains available for rollback through its permanent legacy executor.
- Full ensemble requests carry the minimum response width plus one optional spare. The legacy route accepts exactly the minimum number of healthy distinct servers and consults the spare only when an earlier server fails; three healthy servers therefore remain a full three-response ensemble rather than degrading to dual-run. If the spare restores the minimum width, the aggregate result and usage/telemetry outcome are successful while the failed sample remains available for diagnostics. The Pi route receives the governed minimum directly because it has no spare-retry loop; a sub-minimum set of valid responses is downgraded instead of being labeled a complete ensemble.
- “Different models” means distinct model identities for independent validation, not merely different endpoint IDs. Replicas may improve availability but cannot provide independent raters; the system does not invent diversity when the required model identities are unavailable.
- When distinct endpoints cannot be selected, validation degrades to the documented lower-assurance path or reports unavailable/blocked. A failed judge is not a pass. These outcomes keep unvalidated work out of accepted research evidence and reports.
- W8 now routes embedding-based comparison through `agentic.embed`: Pi uses the `EmbeddingsGateway`, while legacy keeps the unchanged `ollama.embed*` plane. This preserves the vector-space and fail-closed boundaries for both engines.

## Rollback

Choose the `legacy` engine for the project (or keep the legacy global default) to return validation calls to the dispatcher's preserved legacy route. Engine selection changes the executor, not the product call-site path.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with ensemble health.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [quality.dashboard](../../quality/dashboard/researcher.md)
- [compute.pool](../../compute/pool/researcher.md)

## Related Concepts

- [fleiss-kappa](../../../glossary/fleiss-kappa.md)

## Evidence

- Source files: `frontend/src/components/common/EnsembleHealthView.tsx`, `backend/app/core/consensus.py`, `backend/app/core/validation.py`, `backend/app/core/validation_executor.py`, `backend/app/services/research_validity_service.py`, `backend/app/core/agentic/dispatcher.py`
- API references: `backend/app/api/routes/metrics.py`
- Tests: `tests/pi_production/test_w7_validation.py`, `tests/test_validation_project_scope.py`, `tests/test_research_validity_contract.py`, `tests/test_metrics.py`
