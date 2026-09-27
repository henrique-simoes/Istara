---
stable_id: integrations.surveys
title: Survey Integrations
ui_path: Integrations > Surveys
audience: researcher
status: documented
related_features: ["integrations.deployments", "findings.evidence"]
related_glossary: ["triangulation"]
code_references: ["frontend/src/components/integrations/SurveysTab.tsx", "frontend/src/components/integrations/SurveySetupWizard.tsx", "backend/app/api/routes/surveys.py"]
api_references: ["backend/app/api/routes/surveys.py"]
test_references: ["tests/test_surveys.py", "tests/test_project_scope_contracts.py", "tests/test_deployment_research_ops.py", "tests/simulation/scenarios/89-study-participant-journey.mjs"]
last_verified: 2026-09-26
compass: CF-SPEC-53 / CF-657; CF-SPEC-60 / CF-776
---

# Survey Integrations

## What It Does

Brings answers from SurveyMonkey, Typeform or Google Forms into the project as raw research evidence, and lets you record answers a participant gave another way (a phone call, a paper form) in the Questionnaire Studio.

## Why It Exists

Survey answers are research data like interview transcripts: they need to be stored exactly as given, traceable to the response they came from, and analysed through the same coding and review gates before they appear in a report.

## Where It Lives

- UI path: Integrations > Surveys
- Navigation group: Integrations
- Primary components: `SurveysTab`, `SurveySetupWizard`

## How UX Researchers Use It

1. **Connect** a platform (project admins) and link a survey to the project.
2. **Sync** pulls the survey's responses. Istara reports how many new answers it stored and how many it skipped because they were already stored: syncing again never duplicates answers.
3. **Export** (download icon) gives a CSV of the stored answers with their response IDs and evidence-unit IDs.
4. **Questionnaire Studio**: add the survey's questions, type a real participant's answers, and choose **Record response**. Unanswered questions are skipped; the studio refuses to record an empty response.

## Supported Workflows

- Pull a live survey several times during fieldwork; only new answers are added.
- Record phone or paper responses alongside platform responses.
- Export raw answers for your own analysis or archive.

## Inputs, Outputs, And Expected Outcomes

- Each answered question becomes a provisional nugget and one evidence unit holding the answer; the question is kept as context for coders, not coded as participant data.
- Answers reach a report only after analysis through a task: coding, reconciliation and an approved Done task.

## Caveats

- No active project means connection and sync are disabled.
- Responses a platform returns without an ID cannot be matched on re-sync; they are stored each time they are pulled.
- Never enter invented answers in the Questionnaire Studio: whatever it records is stored as participant evidence.

## Related Features

- [integrations.deployments](../../integrations/deployments/researcher.md)
- [findings.evidence](../../findings/evidence/researcher.md)

## Related Concepts

- [triangulation](../../../glossary/triangulation.md)

## Evidence

- Source files: `frontend/src/components/integrations/SurveysTab.tsx`, `frontend/src/components/integrations/SurveySetupWizard.tsx`, `backend/app/api/routes/surveys.py`, `backend/app/services/survey_ingestion.py`
- API references: `backend/app/api/routes/surveys.py`
- Tests: `tests/test_surveys.py`, `tests/test_deployment_research_ops.py`, scenario `89-study-participant-journey`
