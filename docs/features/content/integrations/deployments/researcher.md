---
stable_id: integrations.deployments
title: Research Deployments
ui_path: Integrations > Deployments
audience: researcher
status: documented
related_features: ["integrations.deployment-dashboard", "integrations.surveys", "integrations.messaging"]
related_glossary: ["triangulation"]
code_references: ["frontend/src/components/integrations/DeploymentsTab.tsx", "frontend/src/components/integrations/DeploymentWizard.tsx", "frontend/src/components/integrations/DeploymentDashboard.tsx", "frontend/src/components/integrations/ConversationTranscript.tsx", "frontend/src/lib/api.ts", "backend/app/api/routes/deployments.py", "backend/app/services/deployment_service.py"]
api_references: ["backend/app/api/routes/deployments.py", "backend/app/services/deployment_service.py"]
test_references: ["tests/test_deployments.py", "tests/test_project_scope_contracts.py", "tests/test_deployment_participant_flow.py", "tests/test_deployment_research_ops.py", "tests/simulation/scenarios/89-study-participant-journey.mjs"]
last_verified: 2026-09-26
compass: CF-SPEC-60 / CF-767; CF-SPEC-60 / CF-773; CF-SPEC-62 / CF-793
---

# Research Deployments

## What It Does

Runs an interview, survey or diary study through Telegram, Slack or WhatsApp. Each participant who messages one of the study's channels is taken through informed consent, optional screening questions, your questions (with optional AI follow-ups), and an optional closing question. Every answer is stored as raw evidence, attributed to the exact question the participant was shown.

## Why It Exists

Some participants will answer a few questions in the messaging app they already use but will never open a survey link. A deployment lets you collect those answers without losing the rigour of a moderated study: consent before collection, eligibility screening, a participant quota, reminders, and a pseudonymous raw-data export.

## Where It Lives

- UI path: Integrations > Deployments
- Navigation group: Integrations
- Primary components: `DeploymentsTab`, `DeploymentWizard`, `DeploymentDashboard`

## How UX Researchers Use It

1. Start at least one channel in Integrations > Messaging (the wizard lists only running channels).
2. Choose **New Deployment** and pick the study type.
3. Write your questions.
4. **Consent & Screening**: consent is on by default; edit the statement to match your study and ethics approval. Add screening questions with the answers that qualify (for example `yes`); leave the answers empty to accept anything.
5. Decide whether the AI may ask follow-up questions, and how many per question.
6. Pick the channels, name the study, set the number of participants you need, and optionally a closing question, a thank-you message and one reminder after a quiet period.
7. Open the study and choose **Activate**. Activation opens the study; it does not message anyone. Share the bot or channel with your participants; each one is invited when they write to it.
8. Follow progress on the dashboard, **Pause** or **Complete** the study, and **Export CSV** for the raw answers.

## Supported Workflows

- Consent: participants reply YES or NO. A NO, or two unclear replies, ends the conversation and nothing they sent is stored. Anyone can leave at any point by replying STOP.
- Screening: a participant whose answer does not qualify is thanked and not asked your questions; their screening answers are kept on the conversation for your audit, not as evidence.
- Quota: once the target number of participants have finished, new people are told the study is full; anyone already taking part can finish.
- Reminders: a participant who goes quiet gets one reminder repeating the last question.
- Pause: participants who write are told the study is paused and nothing they send is recorded. A study participant never reaches the project's AI agent.

## Inputs, Outputs, And Expected Outcomes

- Inputs: questions, consent statement, screening questions, target, optional closing question, thank-you message and reminder delay.
- Outputs: one provisional nugget and one raw evidence unit per answer (the question is kept as context for coders); a pseudonymous CSV (P01, P02, … with consent status, screener answers, question, answer, time and evidence-unit ID; no chat handles or names).
- Answers are raw evidence, not findings. They reach a report only after analysis through a task: coding, reconciliation and an approved Done task.

## Caveats

- Viewers can follow studies but cannot create, run or export them.
- Channels need their provider credentials (Telegram bot token, Slack app, WhatsApp Business) and, for webhooks, a reachable URL; without them the channel cannot start.
- Diary-study pacing between prompts is not scheduled by Istara; each prompt follows the participant's previous reply.

## Related Features

- [integrations.deployment-dashboard](../../integrations/deployment-dashboard/researcher.md)
- [integrations.surveys](../../integrations/surveys/researcher.md)
- [integrations.messaging](../../integrations/messaging/researcher.md)

## Related Concepts

- [triangulation](../../../glossary/triangulation.md)

## Evidence

- Source files: `frontend/src/components/integrations/DeploymentsTab.tsx`, `frontend/src/components/integrations/DeploymentWizard.tsx`, `frontend/src/components/integrations/DeploymentDashboard.tsx`, `backend/app/services/adaptive_interview.py`, `backend/app/services/inbound_processor.py`, `backend/app/services/deployment_reminders.py`
- API references: `backend/app/api/routes/deployments.py`, `backend/app/services/deployment_service.py`
- Tests: `tests/test_deployment_participant_flow.py`, `tests/test_deployment_research_ops.py`, scenario `89-study-participant-journey` (27/27 on the QA ui lane, 2026-09-27)
