---
stable_id: findings.evidence
title: Findings Evidence
ui_path: Findings > Evidence
audience: architecture
status: documented
related_features: ["findings.phase-tabs", "findings.codebook", "findings.reports"]
related_glossary: ["atomic-research", "triangulation"]
code_references: ["frontend/src/components/findings/FindingsView.tsx", "backend/app/api/routes/findings.py", "backend/app/api/routes/research_validity.py", "backend/app/services/finding_validity_service.py", "backend/app/services/research_validity_service.py", "backend/app/services/research_finding_links.py", "backend/app/core/research_validity.py", "backend/app/models/research_validity.py"]
api_references: ["backend/app/api/routes/findings.py", "backend/app/api/routes/research_validity.py"]
test_references: ["tests/test_findings.py", "tests/test_project_scope_contracts.py", "tests/test_research_validity_contract.py"]
last_verified: 2026-05-22
compass: CF-SPEC-60 / CF-772; CF-SPEC-124 / CF-1590; Research Spine manual Findings batch
---

# Findings Evidence Architecture

## Implementation Summary

The Findings evidence tab lists research insights and recommendations for the active project and supports phase-oriented review. Findings must be traceable back to accepted/reconciled coded evidence units and approved Done tasks before they are eligible for reports.

## Frontend Surface

- `frontend/src/components/findings/FindingsView.tsx`
- `backend/app/api/routes/findings.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/projectStore.ts`

### API And Backend

- `backend/app/api/routes/findings.py`
- Project-facing findings list routes require `project_id` and verify project access before returning nuggets, facts, insights, recommendations, or design decisions.
- `POST /api/findings/nuggets` is a manual source-ingestion path, not a reportability shortcut. It creates a visible provisional nugget, persists stable raw-source `EvidenceUnit` rows from the submitted source text/location, and links them with `ResearchEvidenceEdge` `grounded_in` edges while leaving the task link empty until governed coding, reconciliation, and Done-task approval make the evidence reportable.
- Manual fact, insight, recommendation, and design-decision creation validates every linked upstream artifact id against the active project before persisting the link. Cross-project nugget, fact, insight, recommendation, or screen ids are rejected so hand-built Atomic chains cannot bypass project scope or Research Spine provenance.
- Findings list responses include content-free `research_validity` metadata. The metadata marks each visible finding as `provisional` or `accepted`, reports whether it is currently reportable, and names the active blocker without exposing private source content.
- Design-decision list responses derive `research_validity` from the linked source recommendations/insights. A design decision remains provisional until every linked source finding is accepted/reconciled through a human-approved Done task.
- Evidence-chain traversal filters linked records by the originating finding's project before returning nested nuggets, facts, insights, recommendations, design decisions, or screens.
- Evidence-chain responses include content-free research-validity diagnostics for task-linked findings. The diagnostics show task ids, accepted/reconciled coded-evidence status, Done/approved status, and whether the chain can feed reports; visibility of a chain never means reportability by itself.
- Evidence-chain, link, delete, and design-decision by-id routes also require the active `project_id` and load records by both id and project id. A stale finding id from another project resolves as not found even when the user can access both projects.
- `backend/app/api/routes/research_validity.py` exposes project-scoped evidence units, coding runs, evidence graph edges, reconciliation decisions, traceability answers, and a summary of pending/accepted/blocked research-validity state. Researchers can start governed coding runs through the project-scoped coding-run route; the service selects distinct project-authorized model identities through Compute Manager and stores route evidence/reliability state.
- `backend/app/core/rag.py` emits content-free `retrieval.hybrid` telemetry from `retrieve_context`, including retrieval mode and available evidence-unit/codebook/coding-run handles without storing queries or source text.
- Project Prompt-RAG and protected-block compression paths emit `prompt_rag.context` and `compression.protected_block` telemetry from project-scoped calls. These events are process evidence only; they cannot supply mandatory methodology or promote evidence.

## Architecture Notes

- The feature is mounted through `frontend/src/components/findings/FindingsView.tsx` and the UI navigation path recorded in the inventory.
- The backend retains an explicit admin-only global findings search route for admin/reporting aggregation; project-facing evidence views do not use unscoped list routes.
- Hybrid RAG provides exact evidence retrieval. Evidence Graph / GraphRAG can support synthesis and traceability questions, but graph output cannot bypass qualitative coding, reliability gates, human review, approved Done task state, or report gating.
- The traceability API joins reports, finding ids, task ids, coding runs, code applications, reconciliation decisions, and graph edges so project users can inspect which reports or tasks still depend on low-agreement evidence before synthesis or reporting. Project-level coding runs without a task id are queryable with the optional project-scoped `coding_run_id` filter; the exact run remains visible even when blocked with zero applications, while reportability remains fail-closed.
- The Evidence list renders reportability badges from `research_validity`; agent, skill, or manually created findings remain visible but are clearly provisional until accepted coded evidence and human-approved Done state make them reportable.
- Atomic drilldown uses the evidence-chain diagnostics to show when research-validity gates block promotion, including missing coding, unresolved reliability/reconciliation work, or the task not yet being human-approved Done.
- Code applications created by governed coding runs link back to stable evidence units and carry coding-run, codebook, model, donor, route, reliability, reconciliation, and promotion handles before downstream findings can use them. Disputed applications must be resolved through durable reconciliation decisions rather than silent status changes.
- Agent-created nuggets are converted into task-linked evidence units and evidence-graph edges before governed coding runs. This keeps task findings traceable to coded evidence units instead of keyword-like tags or final-answer summaries.
- Agent-created downstream facts, insights, and recommendations retain explicit candidate-only `derived_from` graph edges to their linked upstream artifacts. These edges preserve the Nugget → Fact → Insight → Recommendation chain for GraphRAG and audit traversal, while pending review, uncoded reliability, and the promotion rule make clear that graph traversal cannot bypass accepted evidence, reconciliation, or human-approved Done gates.
- Model-supplied downstream ids are project-scoped before persistence. Foreign or stale Nugget, Fact, or Insight ids are discarded, the task is flagged for human review, and no cross-project `derived_from` edge is written.
- Manually created nuggets follow the same raw-source-first contract. They remain provisional and non-reportable after creation even though their source text has evidence-unit traceability; downstream acceptance still requires coded evidence, reconciliation where needed, and a human-approved Done task.
- Evidence-unit extraction emits content-free `evidence_unit.extract` telemetry with project, task, evidence-unit, and retrieval-mode handles so Quality Dashboard and audit tools can prove source segmentation occurred without storing quotes or document content in telemetry.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Findings evidence is project content. Every project-facing read or mutation must be bound to the caller's authorized active project, and global aggregation belongs only to dedicated admin surfaces.

## Tests And Verification

- `tests/test_findings.py`
- `tests/test_findings.py::test_nugget_creation_normalizes_integrity_fields`
- `tests/test_findings.py::test_manual_atomic_chain_creation_rejects_cross_project_links`
- `tests/test_research_spine_end_to_end.py` — production-path downstream `derived_from` graph edges remain candidate-only until evidence and human review gates pass.
- `tests/test_research_spine_end_to_end.py::test_agent_findings_drop_cross_project_downstream_links`
- `tests/test_project_scope_contracts.py`

## Related Features

- [findings.phase-tabs](../../findings/phase-tabs/architecture.md)
- [findings.codebook](../../findings/codebook/architecture.md)
- [findings.reports](../../findings/reports/architecture.md)

## Related Concepts

- [atomic-research](../../../glossary/atomic-research.md)
- [triangulation](../../../glossary/triangulation.md)

## Compass Evidence

- Spec/task: CF-SPEC-60 / CF-772; CF-SPEC-124 / CF-1590
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
