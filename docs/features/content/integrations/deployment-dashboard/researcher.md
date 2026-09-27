---
stable_id: integrations.deployment-dashboard
title: Deployment Dashboard
ui_path: Integrations > Deployments > Dashboard
audience: researcher
status: documented
related_features: ["integrations.deployments", "findings.evidence"]
related_glossary: ["triangulation"]
code_references: ["frontend/src/components/integrations/DeploymentDashboard.tsx", "frontend/src/components/integrations/ConversationTranscript.tsx", "frontend/src/lib/api.ts", "backend/app/api/routes/deployments.py", "backend/app/services/deployment_service.py"]
api_references: ["backend/app/api/routes/deployments.py", "backend/app/services/deployment_service.py"]
test_references: ["tests/test_deployments.py", "tests/test_project_scope_contracts.py", "tests/test_deployment_participant_flow.py", "tests/test_deployment_research_ops.py", "tests/simulation/scenarios/89-study-participant-journey.mjs"]
last_verified: 2026-09-26
compass: CF-SPEC-53 / CF-657; CF-SPEC-60 / CF-767; CF-SPEC-60 / CF-773
---

# Deployment Dashboard

## What It Does

Shows one study while it runs: who is taking part and where each participant is, per-question statistics, and the controls to activate, pause, resume, complete and export it.

## Why It Exists

A researcher running a remote study needs to see at a glance whether people are joining, finishing or dropping out, and to stop or pause the study without losing data.

## Where It Lives

- UI path: Integrations > Deployments > (a study)
- Navigation group: Integrations
- Primary component: `DeploymentDashboard`

## How UX Researchers Use It

- **Live Feed** lists participants currently taking part and recent activity; the dashboard refreshes every 15 seconds while open (or use the refresh button).
- **Participant Tracker** names each outcome in plain words: invited, awaiting consent, screening, answering, follow-up, closing question, completed, declined consent, screened out, withdrew, study full.
- **Question Analytics** shows answers per question.
- The header shows the study state, whether consent is asked first, and how many participants have finished against the target.
- **Activate / Pause / Resume / Complete** confirm what happened; a failure is shown, never swallowed.
- **Export CSV** downloads the raw answers, pseudonymised.

## Supported Workflows

- Watch a study fill, pause it for a fix to a question, resume it, and close it when enough people have finished.
- Open a participant's transcript from the tracker.

## Inputs, Outputs, And Expected Outcomes

- Outputs: a CSV with one row per stored answer (P01, P02, …, consent, screener answers, prompt kind, question, answer, time, evidence-unit ID).
- The Findings Pipeline tab explains that answers are raw evidence; findings come from analysing them through a task.

## Caveats

- Activation does not message participants; they are invited when they write to the study's channel.
- Viewers see the dashboard without the run and export controls.

## Related Features

- [integrations.deployments](../../integrations/deployments/researcher.md)
- [findings.evidence](../../findings/evidence/researcher.md)

## Related Concepts

- [triangulation](../../../glossary/triangulation.md)

## Evidence

- Source files: `frontend/src/components/integrations/DeploymentDashboard.tsx`, `frontend/src/components/integrations/ConversationTranscript.tsx`, `frontend/src/lib/api.ts`, `backend/app/api/routes/deployments.py`, `backend/app/services/deployment_service.py`
- API references: `backend/app/api/routes/deployments.py`, `backend/app/services/deployment_service.py`
- Tests: `tests/test_deployment_research_ops.py`, scenario `89-study-participant-journey`
