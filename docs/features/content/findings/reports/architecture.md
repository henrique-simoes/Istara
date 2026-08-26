---
stable_id: findings.reports
title: Project Reports
ui_path: Findings > Reports
audience: architecture
status: documented
related_features: ["findings.evidence", "tasks.send-report", "interfaces.handoff"]
related_glossary: ["minto-pyramid", "scr", "triangulation"]
code_references: ["frontend/src/components/findings/FindingsView.tsx", "frontend/src/components/findings/ProjectReportsView.tsx", "backend/app/api/routes/reports.py", "backend/app/api/routes/tasks.py", "backend/app/core/report_manager.py", "backend/app/core/reporting_worker.py", "backend/app/services/research_validity_service.py", "backend/app/core/pi_runtime/idempotency.py", "backend/app/models/pi_tool_execution.py"]
api_references: ["backend/app/api/routes/reports.py", "backend/app/api/routes/tasks.py"]
test_references: ["tests/test_research_integrity_reports.py", "tests/test_research_spine_end_to_end.py", "tests/pi_production/test_chat_pi_asgi.py", "tests/pi_production/test_worker_tool_loop.py", "tests/pi_production/test_pi_tool_idempotency.py", "pi-runtime/test/hardening.test.mjs", "tests/benchmarks/long_horizon_runner.py", "tests/pi_benchmark/test_b0_3_long_horizon_tokens.py", "tests/test_tasks.py", "tests/real_user_benchmark/run.mjs"]
last_verified: 2026-08-26
compass: CF-SPEC-53 / CF-657; CF-SPEC-60 / CF-773; CF-SPEC-121; CF-SPEC-122; CF-SPEC-123 / CF-1581; Research Spine item-level report gate batch
---

# Project Reports Architecture

## Implementation Summary

The Reports tab lets users generate, inspect, and manage project reports produced from findings and research evidence. In the real-user benchmark, report evidence is strongest when the Findings chain is created from approved task outputs rather than synthetic notes created before review.

## Frontend Surface

- `frontend/src/components/findings/FindingsView.tsx`
- `frontend/src/components/findings/ProjectReportsView.tsx`
- `backend/app/api/routes/reports.py`
- `backend/app/core/report_manager.py`
- `backend/app/core/reporting_worker.py`

## State, API, And Backend Contracts

### Stores

- None recorded.

### API And Backend

- `backend/app/api/routes/reports.py`
- `backend/app/core/report_manager.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/findings/FindingsView.tsx` and the UI navigation path recorded in the inventory.
- Report generation and executive-summary calls preserve the report's `project_id` through async database boundaries and pass that project id into LLM routing so summaries cannot lose their project context.
- Task-produced findings carry `task_id` provenance. Reports consume those findings only after the associated task is Done, `review_state=approved`, and the task's research-validity gate confirms accepted/reconciled coded evidence. In Review work and uncoded task findings can remain visible for researcher review, but they are not report evidence at any reporting layer.
- The task research-validity gate is item-level, not aggregate. One accepted code application or one passing coding run never bulk-accepts every finding on the task; each report dependency must trace through accepted/reconciled evidence units, source nuggets, and the fact/insight/recommendation chain before it can appear in a report.
- A high-agreement Fleiss/alpha result is still a candidate state: every coded application remains blocked until its own explicit reconciliation decision is persisted. Review approval or statistical acceptance alone cannot make source evidence reportable.
- A Done task with only task notes, operational description, or other uncoded text is still blocked from Reports; the gate requires at least one Research Spine artifact or accepted/reconciled coded evidence before creating a report draft.
- Higher-level synthesis layers re-run the same Research Spine filter over the finding ids already stored in L2/L3 reports. Stale, taskless, provisional, or legacy-unverified ids are not copied into L3 synthesis or L4 final reports just because an older report referenced them.
- The latest task coding run is authoritative for reportability. If a newer run is blocked, incomplete, or otherwise unaccepted, an older accepted run or code application cannot lend stale assurance to the current task; reporting remains blocked until the current run is accepted or reconciled.
- Accepted document-backed codes are revalidated against the active project source and its exact recorded version at report time. Deleting or changing a source preserves historical evidence rows for audit but immediately blocks their use in new reports until the current source is coded and accepted again.
- Report promotion checks emit content-free research-validity telemetry through `report.promotion_gate`, recording whether task/report evidence was allowed or blocked without storing source text, report prose, prompts, or private document content.
- Findings that pass the approved-Done-task/reportability gate emit `finding.promotion`; raw finding creation and In Review findings do not count as promoted report evidence.
- The real-user benchmark records approved task ids before creating task-backed nuggets, facts, insights, and recommendations, then requests report/brief generation after that chain exists. This keeps Findings/reporting aligned with Istara's human-in-the-loop review process.
- The focused end-to-end contract in `tests/test_research_spine_end_to_end.py` proves the report boundary causally: current raw document and exact evidence units are independently coded by three distinct model identities; numeric Fleiss kappa and Krippendorff alpha, route/coder/application provenance, grounding, explicit human code acceptance, Atomic lineage, human Done approval, ReportManager routing, and graph traceability are all required. The same accepted evidence is asserted to remain absent from reports while the task is still In Review.
- The real-user coding probe must scan paginated evidence, select substantive raw spans, and prove three distinct source identities before a three-model validation can pass. Missing or unit-only source metadata is grouped as unknown and blocks the coding request rather than being counted as source diversity.
- Pi chat continuity is tested over two real authenticated ASGI calls using one persisted ChatSession, with the first worker shut down before the second call. The second worker must rehydrate the exact user/assistant transcript from the database; a memory-only session or manually supplied history is not sufficient evidence.
- The Pi worker's long-horizon contract drives seven authority tool calls plus a terminal assistant response and requires cumulative `usage.turns == 8`, seven persisted tasks, and one terminal completion. This is a bounded execution proof, not a claim that arbitrary live-provider horizons are safe; timeout, cancellation, restart, idempotency, and side-effect recovery remain separate acceptance work.
- The Pi provider retry seam buffers non-visible provider events, retries only classifier-approved transient failures within the configured budget, never retries after visible output, and converts synchronous adapter throws into one terminal error event. This preserves fail-closed Research Spine behavior: a transport/programming exception cannot hang a run or silently replay a side effect.
- Pi authority mutations use a project-scoped durable execution ledger. A completed mutation outcome is replayed for the same request identity; a row left in `started` state by cancellation or worker loss returns `tool_recovery_required` and is never executed again automatically. This is a recovery barrier, not an exactly-once claim: operators must reconcile an unsettled side effect before retrying it.
- The Docker-safe live long-horizon runner now creates an explicit ChatSession, requires every setup/inspection request and both SSE turns to succeed, counts only canonical tool-call frames, requires persisted assistant message ids, and verifies the four-message two-turn transcript. Its process exits non-zero on transport, malformed-stream, provider-error, missing-tool, or missing-history evidence; stdout-only metrics remain observational rather than proof of Research Spine acceptance.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Executive-summary and report-composition LLM calls are project-contextual and must keep the report project id attached to generated content.
- Agentic reporting is based on reviewed project evidence. Benchmark artifacts must distinguish approved-task-backed report generation from fallback baseline report checks, and must not count In Review findings as approved report material.

## Tests And Verification

- `tests/test_research_integrity_reports.py`
- `tests/test_research_integrity_reports.py::TestReportManager::test_synthesis_revalidates_l2_findings_before_layer_3`
- `tests/test_tasks.py::test_task_report_gate_blocks_aggregate_reliability_bulk_acceptance`
- `tests/test_tasks.py::test_task_report_gate_blocks_done_task_without_accepted_evidence`
- `pi-runtime/test/hardening.test.mjs` (guarded retry, visible-output no-retry, synchronous throw terminalization)
- `tests/pi_production/test_pi_tool_idempotency.py` (completed replay, unfinished recovery barrier, cancellation persistence)
- `tests/real_user_benchmark/run.mjs`

## Related Features

- [findings.evidence](../../findings/evidence/architecture.md)
- [tasks.send-report](../../tasks/send-report/architecture.md)
- [interfaces.handoff](../../interfaces/handoff/architecture.md)

## Related Concepts

- [minto-pyramid](../../../glossary/minto-pyramid.md)
- [scr](../../../glossary/scr.md)
- [triangulation](../../../glossary/triangulation.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657; CF-SPEC-60 / CF-773; CF-SPEC-121; CF-SPEC-122; CF-SPEC-123 / CF-1581
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
